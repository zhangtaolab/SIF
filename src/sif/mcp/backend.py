"""SearchBackend for MCP tool handlers."""

from __future__ import annotations

import asyncio
import fnmatch
from collections.abc import Callable
from typing import Any, TypeVar

from sif.config.settings import Settings, get_settings
from sif.core.models import SearchOptions
from sif.database.connection import DatabaseConnection
from sif.database.repositories import CollectionRepository, DocumentRepository
from sif.embedding.factory import EmbeddingModelFactory
from sif.embedding.model import ModelType
from sif.mcp.protocol import CollectionInfo, Document, SearchResult
from sif.search.bm25 import BM25Searcher
from sif.search.hybrid import SearchPipeline
from sif.search.suggest import SuggestionEngine
from sif.utils.logging import get_logger
from sif.utils.paths import normalize_path


logger = get_logger(__name__)


T = TypeVar("T")


class HybridSearchResults(list[SearchResult]):
    """Search results carrying zero-result suggestions across the MCP boundary.

    ``hybrid_search`` keeps its ``list[SearchResult]`` contract — every
    caller indexes and iterates it unchanged. The suggestions ride the
    returned collection itself because the MCP boundary re-maps core fields
    one by one; an attribute that is not read explicitly would be silently
    dropped. The query handler reads it with ``getattr`` so mocked or
    third-party list returns keep working with an empty list.
    """

    suggestions: list[str]

    def __init__(
        self,
        results: list[SearchResult],
        suggestions: list[str] | None = None,
    ) -> None:
        """Wrap ``results`` and attach the (display-only) suggestions."""
        super().__init__(results)
        self.suggestions = suggestions or []


def _with_suggestions(
    conn: Any,
    query: str,
    results: list[SearchResult],
) -> HybridSearchResults:
    """Attach D-05 suggestions on the zero-result path only, fail-soft.

    The engine is built on the connection already in scope; only an empty
    result set pays its cost. Any failure degrades to no suggestions — a
    suggestion problem must never fail an MCP query (Pitfall 10 posture).
    """
    if results:
        return HybridSearchResults(results)
    try:
        suggestions = SuggestionEngine(conn).did_you_mean(query)
    except Exception:
        logger.warning("MCP did-you-mean computation failed", exc_info=True)
        suggestions = []
    return HybridSearchResults(results, suggestions)


def _truncate_content(content: str, max_size: int = 100 * 1024) -> str:
    """Truncate content to max_size bytes."""
    suffix = "\n... [truncated]"
    encoded = content.encode("utf-8")
    if len(encoded) <= max_size:
        return content
    truncated = encoded[: max_size - len(suffix.encode("utf-8"))].decode("utf-8", errors="ignore")
    return truncated + suffix


class SearchBackend:
    """Backend for MCP search and retrieval operations."""

    def __init__(self, db_path: str, settings: Settings | None = None) -> None:
        """Initialize SearchBackend."""
        self.db_path = db_path
        self.settings = settings or get_settings()
        self._embedder: Any = None
        self._vec_unavailable_warned = False
        try:
            factory = EmbeddingModelFactory()
            model_type = ModelType(self.settings.model_type)
            model_path = str(self.settings.model_path) if self.settings.model_path else None
            self._embedder = factory.create_model(
                model_type,
                model_path,
                self.settings.model_name,
                api_key=self.settings.api_key,
                api_base=self.settings.api_base,
                embedding_dim=self.settings.embedding_dim,
                cache_dir=(
                    str(self.settings.get_cache_dir()) if self.settings.cache_embeddings else None
                ),
            )
        except Exception:
            logger.warning("Failed to load embedder; vector search will be unavailable")

    async def _run_in_db(self, callback: Callable[[Any], T]) -> T:
        """Run a callback with a fresh database connection in a thread."""

        def _run() -> T:
            with DatabaseConnection(self.db_path).transaction() as conn:
                return callback(conn)

        return await asyncio.to_thread(_run)

    async def hybrid_search(  # noqa: PLR0913 — weight overrides are per-request
        # params by design (D-04: request field ≈ CLI flag); a params object
        # would divorce the signature from the QueryInput fields it mirrors.
        self,
        query: str,
        collections: list[str] | None = None,
        limit: int = 10,
        min_score: float = 0.0,
        rrf_k: int | None = None,
        bm25_weight: float | None = None,
        vector_weight: float | None = None,
    ) -> list[SearchResult]:
        """Perform hybrid search.

        Weight overrides (Phase 15, D-04): each ``None`` falls back to the
        server process's ``SIF_`` settings (request field ≈ CLI flag); the
        resolved values ride SearchOptions into the pipeline.

        When sqlite-vec is unavailable (SearchPipeline construction raises
        ``RuntimeError``), the search degrades to BM25-only with a one-time
        warning (Phase 10 WR-08, user decision); search-time errors still
        propagate.
        """

        def _search(conn: Any) -> list[SearchResult]:
            options = SearchOptions(
                limit=limit,
                min_score=min_score,
                include_content=False,
                include_highlights=True,
                rrf_k=rrf_k if rrf_k is not None else self.settings.rrf_k,
                bm25_weight=(bm25_weight if bm25_weight is not None else self.settings.bm25_weight),
                vector_weight=(
                    vector_weight if vector_weight is not None else self.settings.vector_weight
                ),
            )
            if collections:
                repo = CollectionRepository(conn)
                matched = [c.id for c in (repo.get_by_name(n) for n in collections) if c]
                if not matched:
                    return _with_suggestions(conn, query, [])
                options.collection_ids = matched
            try:
                pipeline = SearchPipeline(
                    conn,
                    embedder=self._embedder,
                    embedding_dim=self.settings.embedding_dim,
                )
            except RuntimeError:
                # WR-08 (user decision): MCP-boundary carve-out — a missing
                # sqlite-vec extension fails SearchPipeline construction, so
                # degrade to BM25-only here; the core HybridSearcher.search
                # stays fail-fast (search-time errors are never caught).
                if not self._vec_unavailable_warned:
                    self._vec_unavailable_warned = True
                    logger.warning(
                        "sqlite-vec unavailable; MCP hybrid search degrades to BM25-only"
                    )
                core_results = BM25Searcher(conn).search(query, options)
            else:
                core_results = pipeline.search(query, options)
            mapped = [
                SearchResult(
                    doc_id=r.document_id,
                    path=r.path,
                    title=r.title,
                    content=r.content,
                    score=r.score,
                    highlights=r.highlights,
                    # vectors_stale forwarded explicitly (D-11 / RESEARCH B5):
                    # this boundary re-maps core fields one by one, so an
                    # unlisted field is silently dropped — the derived
                    # staleness flag must ride the metadata dict to reach MCP
                    # clients (zero protocol change; model_dump() serializes).
                    metadata={
                        "rank": r.rank,
                        "collection_name": r.collection_name,
                        "vectors_stale": r.vectors_stale,
                    },
                )
                for r in core_results
            ]
            # Same boundary rule for D-05: suggestions are attached explicitly
            # on the zero-result path; MCP queries never write query_log (D-08).
            return _with_suggestions(conn, query, mapped)

        return await self._run_in_db(_search)

    async def get_document(
        self,
        path_or_docid: str,
        from_line: int | None = None,
        max_lines: int | None = None,
    ) -> Document | None:
        """Get a document by path or doc_id."""

        def _get(conn: Any) -> Document | None:
            repo = DocumentRepository(conn)
            doc = repo.get_by_id(path_or_docid)
            if not doc:
                coll_repo = CollectionRepository(conn)
                for coll in coll_repo.list_all():
                    # Canonicalized so symlink-alias paths match stored rows.
                    doc = repo.get_by_path(normalize_path(path_or_docid), coll.id)
                    if doc:
                        break
            if not doc:
                return None
            content = doc.content  # Do NOT truncate yet
            line_start: int | None = None
            line_end: int | None = None
            if from_line is not None or max_lines is not None:
                lines = content.split("\n")
                start = max(0, (from_line or 1) - 1)
                end = len(lines) if max_lines is None else start + max_lines
                content = "\n".join(lines[start:end])
                line_start = start + 1
                line_end = start + len(content.split("\n"))
                if content.endswith("\n"):
                    line_end -= 1
            content = _truncate_content(content)
            return Document(
                doc_id=doc.id,
                path=doc.path,
                title=doc.title,
                content=content,
                metadata=doc.metadata,
                line_start=line_start,
                line_end=line_end,
                collection_id=doc.collection_id,
            )

        return await self._run_in_db(_get)

    async def get_documents_by_pattern(
        self,
        pattern: str,
        max_bytes: int | None = None,
    ) -> tuple[list[Document], list[str]]:
        """Get documents matching a pattern."""

        def _get_pattern(conn: Any) -> tuple[list[Document], list[str]]:
            coll_repo = CollectionRepository(conn)
            doc_repo = DocumentRepository(conn)
            documents: list[Document] = []
            errors: list[str] = []
            total_bytes = 0
            max_b = max_bytes or (100 * 1024)
            # Canonicalized pattern: symlinked directory prefixes match the
            # resolved stored paths (non-existent wildcard tails are preserved).
            normalized_pattern = normalize_path(pattern)
            for coll in coll_repo.list_all():
                for doc in doc_repo.list_by_collection(coll.id):
                    if (
                        fnmatch.fnmatch(doc.path, pattern)
                        or fnmatch.fnmatch(doc.filename, pattern)
                        or fnmatch.fnmatch(doc.path, normalized_pattern)
                    ):
                        content = doc.content
                        content_bytes = len(content.encode("utf-8"))
                        if total_bytes + content_bytes > max_b:
                            errors.append(f"Max bytes limit reached, skipping {doc.path}")
                            continue
                        total_bytes += content_bytes
                        documents.append(
                            Document(
                                doc_id=doc.id,
                                path=doc.path,
                                title=doc.title,
                                content=_truncate_content(content),
                                metadata=doc.metadata,
                                collection_id=doc.collection_id,
                            ),
                        )
            return documents, errors

        return await self._run_in_db(_get_pattern)

    async def get_status(self) -> tuple[list[CollectionInfo], int]:
        """Get index status."""

        def _status(conn: Any) -> tuple[list[CollectionInfo], int]:
            coll_repo = CollectionRepository(conn)
            doc_repo = DocumentRepository(conn)
            collections = coll_repo.list_all()
            infos = []
            for coll in collections:
                count = doc_repo.count_by_collection(coll.id)
                infos.append(
                    CollectionInfo(
                        name=coll.name,
                        document_count=count,
                        last_updated=(
                            coll.last_indexed_at.isoformat() if coll.last_indexed_at else None
                        ),
                    ),
                )
            total = sum(info.document_count for info in infos)
            return infos, total

        return await self._run_in_db(_status)
