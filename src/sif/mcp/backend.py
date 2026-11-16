"""SearchBackend for MCP tool handlers."""

from __future__ import annotations

import asyncio
import fnmatch
import threading
from collections.abc import Callable
from functools import partial
from typing import Any, TypeVar

from sif.config.settings import Settings, get_settings
from sif.core.filters import FilterNode
from sif.core.models import SearchOptions
from sif.database.connection import DatabaseConnection
from sif.database.database import Database
from sif.database.metadata_repository import MetadataValueRepository
from sif.database.repositories import CollectionRepository, DocumentRepository
from sif.embedding.identity import (
    EmbedderIdentity,
    build_settings_identity,
    check_identity,
    schema_embedding_dim,
    warn_identity_mismatch_once,
)
from sif.embedding.manager import EmbeddingManager
from sif.embedding.prompts import resolve_prompt_scheme
from sif.mcp.protocol import CollectionInfo, Document, SearchResult
from sif.search.bm25 import BM25Searcher
from sif.search.context_attach import enrich_results
from sif.search.filters import compile_filter, compile_match
from sif.search.hybrid import SearchPipeline, search_dimension_error
from sif.search.suggest import SuggestionEngine
from sif.search.vector import VectorSearcher
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


# D-15: the remedy a vec_search tool error must carry when no embedder loaded.
VECTOR_SEARCH_REMEDY = (
    "Vector search requires an embedding model. Install the embedding backend "
    'with `pip install "docsif[embed]"`, check the SIF_MODEL_* settings, and retry.'
)


def _resolve_collection_ids(conn: Any, names: list[str] | None) -> list[str] | None:
    """Resolve request collection names the way every search path does.

    ``None`` means "no scope requested"; an empty list means names were given
    but none matched (the caller returns an empty page). Resolution is shared
    so hybrid, lex, and vec cannot drift on unknown-name behavior.
    """
    if not names:
        return None
    repo = CollectionRepository(conn)
    return [c.id for c in (repo.get_by_name(name) for name in names) if c]


def _map_core_results(core_results: list[Any]) -> list[SearchResult]:
    """Re-map core search rows onto the MCP result model, field by field.

    ``vectors_stale`` rides the metadata dict (D-11 / RESEARCH B5) and the
    chunk identity fields are explicitly copied (CORR-02/D-02/D-03): this
    boundary re-maps one by one, so an unlisted field is silently dropped.
    """
    return [
        SearchResult(
            doc_id=r.document_id,
            path=r.path,
            title=r.title,
            content=r.content,
            score=r.score,
            highlights=r.highlights,
            metadata={
                "rank": r.rank,
                "collection_name": r.collection_name,
                "vectors_stale": r.vectors_stale,
                "chunk_id": r.chunk_id,
                "sequence": r.sequence,
                "chunk_matches": r.chunk_matches,
            },
        )
        for r in core_results
    ]


class SearchBackend:
    """Backend for MCP search and retrieval operations."""

    def __init__(self, db_path: str, settings: Settings | None = None) -> None:
        """Initialize SearchBackend without loading an embedding model (D-15).

        Construction is deliberately model-free: no ``EmbeddingManager``, no
        ``EmbeddingModelFactory``, and no ``load_model()``/``get_identity()``
        call. A cold ``sif mcp stdio`` start must stay cheap and quiet, and
        ``status``/``get``/``metadata`` must never pay a model load. The lazy
        load path (one thread-safe attempt, failure latched) lands in 22-02/
        22-04 and attaches through the fields initialized below.
        """
        self.db_path = db_path
        self.settings = settings or get_settings()
        self._embedder: Any = None
        self._identity: EmbedderIdentity | None = None
        self._vec_unavailable_warned = False
        # Lazy-load skeleton: one attempt per process, latched on failure.
        self._load_lock = threading.Lock()
        self._load_attempted = False
        self._load_failed = False
        self._manager: EmbeddingManager | None = None

        # D-07/D-04: resolve the prompt scheme ONCE from the backend's own
        # settings. The same scheme feeds the settings-only identity (schema
        # open); the loaded-model identity computed after a successful lazy
        # load consumes the same resolved names (T-21-28), and a legacy DB
        # first opened here gets the assumed row exactly once.
        scheme = resolve_prompt_scheme(
            self.settings.model_name,
            self.settings.model_type,
            self.settings.query_prompt_name,
            self.settings.document_prompt_name,
        )
        settings_identity = build_settings_identity(self.settings, scheme)

        # CORR-04 / RESEARCH Pitfall 13: an MCP-only host never runs a CLI
        # command, so the schema must migrate here or a pre-title database
        # keeps its single-column FTS forever. The backend's own settings
        # dimension is used because injected settings and embedder overrides
        # can legitimately differ from the process environment. Detection is
        # one sqlite_master read once migrated; a dimension mismatch raises
        # the existing clear RuntimeError instead of rebuilding at the wrong
        # width, and the connection is closed on every path.
        db = Database(self.db_path)
        try:
            # ``create_all`` commits every schema write it makes — including
            # the FTS 'rebuild' population, which ``_create_fts_tables``
            # commits through an explicit savepoint (CR-01). An exception
            # raised later in ``create_all`` (the embedding-dimension
            # RuntimeError below comes from ``_create_vector_tables``) can
            # therefore no longer roll the migrated index back.
            db.init_schema(
                embedding_dim=self.settings.embedding_dim,
                identity=settings_identity,
            )
        finally:
            db.close()

    async def _run_in_db(self, callback: Callable[[Any], T]) -> T:
        """Run a callback with a fresh database connection in a thread."""

        def _run() -> T:
            with DatabaseConnection(self.db_path).transaction() as conn:
                return callback(conn)

        return await asyncio.to_thread(_run)

    def _ensure_embedder(self) -> EmbeddingManager | None:
        """Load the embedding manager once per process, latching failure (D-15).

        One thread-safe attempt: ``EmbeddingManager.from_settings`` (which
        creates the cache directory/database) and ``load_model`` run under
        ``_load_lock``, and a failure latches ``_load_failed`` so later
        requests never retry. 22-04 hardens the warning, BM25-degrade, and
        loaded-dimension policy; this plan only guarantees vec_search has a
        manager and the hybrid path keeps its existing BM25 degradation.
        """
        if self._load_attempted and (self._manager is not None or self._load_failed):
            return None if self._load_failed else self._manager
        with self._load_lock:
            # Another thread completed the attempt while we waited.
            if self._load_attempted:
                return None if self._load_failed else self._manager
            self._load_attempted = True
            try:
                manager = EmbeddingManager.from_settings(self.settings)
                manager.load_model()
                # ``get_identity`` itself calls ``load_model``; calling it only
                # after a successful load keeps construction lazy (Pitfall 9).
                identity = manager.get_identity()
            except Exception:
                self._manager = None
                self._embedder = None
                self._identity = None
                self._load_failed = True
                return None
            self._manager = manager
            self._embedder = manager.model
            # A protocol-only double yields no described identity; inventing
            # one would apply a policy the injector never stated (21-04).
            self._identity = identity if isinstance(identity, EmbedderIdentity) else None
            return self._manager

    async def hybrid_search(  # noqa: PLR0913 — weight overrides are per-request
        # params by design (D-04: request field ≈ CLI flag); a params object
        # would divorce the signature from the QueryInput fields it mirrors.
        self,
        query: str,
        collections: list[str] | None = None,
        limit: int = 10,
        offset: int = 0,
        per_chunk: bool = False,
        min_score: float = 0.0,
        rrf_k: int | None = None,
        bm25_weight: float | None = None,
        vector_weight: float | None = None,
        filter_node: FilterNode | None = None,
    ) -> list[SearchResult]:
        """Perform hybrid search.

        Weight overrides (Phase 15, D-04): each ``None`` falls back to the
        server process's ``SIF_`` settings (request field ≈ CLI flag); the
        resolved values ride SearchOptions into the pipeline. ``offset``
        (CORR-03/D-05) rides the same SearchOptions object into the
        pipeline's single offset slice. ``per_chunk`` (CORR-02/D-01) rides it
        into the vector leg's chunk escape hatch. ``filter_node`` (Phase 20
        D-02) is the already-validated metadata AST; the parameter is named
        ``filter_node`` rather than ``filter`` because ruff A002 flags a
        function argument shadowing the builtin (annotated model fields are
        exempt, A003 does not apply).

        When sqlite-vec is unavailable (SearchPipeline construction raises
        ``RuntimeError``), the search degrades to BM25-only with a one-time
        warning (Phase 10 WR-08, user decision); search-time errors still
        propagate.
        """

        def _search(conn: Any) -> list[SearchResult]:
            options = SearchOptions(
                limit=limit,
                offset=offset,
                per_chunk=per_chunk,
                min_score=min_score,
                include_content=False,
                include_highlights=True,
                # Phase 20 D-02/D-17: None is the only unfiltered signal; a
                # non-None AST is compiled pre-RRF on both legs, and the
                # BM25-only fallback below receives this same options object.
                filter=filter_node,
                rrf_k=rrf_k if rrf_k is not None else self.settings.rrf_k,
                bm25_weight=(bm25_weight if bm25_weight is not None else self.settings.bm25_weight),
                vector_weight=(
                    vector_weight if vector_weight is not None else self.settings.vector_weight
                ),
            )
            collection_ids = _resolve_collection_ids(conn, collections)
            if collections and not collection_ids:
                return _with_suggestions(conn, query, [])
            options.collection_ids = collection_ids
            try:
                # EMB-01: the closure is built only from the full identity a
                # successful embedder load recorded (21-08). When the load
                # failed, no check is invented and the existing BM25
                # degradation below is unchanged.
                identity = self._identity
                identity_check = (
                    partial(check_identity, current=identity, mode="search")
                    if identity is not None
                    else None
                )
                pipeline = SearchPipeline(
                    conn,
                    embedder=self._embedder,
                    embedding_dim=self.settings.embedding_dim,
                    default_search_type=self.settings.default_search_type,
                    identity_check=identity_check,
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
                # CORR-05 (Plan 19-04): the fallback bypasses SearchPipeline,
                # so this boundary owns its one enrichment. The pipeline path
                # below is already enriched by SearchPipeline — enriching it
                # again here would double-attach.
                core_results = enrich_results(conn, core_results)
            else:
                core_results = pipeline.search(query, options)
            mapped = _map_core_results(core_results)
            # Same boundary rule for D-05: suggestions are attached explicitly
            # on the zero-result path; MCP queries never write query_log (D-08).
            return _with_suggestions(conn, query, mapped)

        return await self._run_in_db(_search)

    async def lex_search(  # noqa: PLR0913 — one parameter per frozen LexSearchInput field
        self,
        query: str,
        collections: list[str] | None = None,
        limit: int = 10,
        offset: int = 0,
        min_score: float = 0.0,
        filter_node: FilterNode | None = None,
    ) -> list[SearchResult]:
        """Run the CLI ``sif search search`` direct BM25 path (D-17).

        CLI parity by construction: the same ``BM25Searcher`` call with the
        same options (filter, offset, min_score), followed by exactly one
        ``enrich_results``. No expansion, no prefix routing, no reranking.
        """

        def _search(conn: Any) -> list[SearchResult]:
            collection_ids = _resolve_collection_ids(conn, collections)
            if collections and not collection_ids:
                return _with_suggestions(conn, query, [])
            options = SearchOptions(
                limit=limit,
                offset=offset,
                min_score=min_score,
                include_content=False,
                include_highlights=True,
                filter=filter_node,
                collection_ids=collection_ids,
            )
            results = BM25Searcher(conn).search(query, options)
            # CORR-05: the direct exit owns exactly one enrichment; no
            # pipeline is involved on this path.
            results = enrich_results(conn, results)
            return _with_suggestions(conn, query, _map_core_results(results))

        return await self._run_in_db(_search)

    async def vec_search(  # noqa: PLR0913 — one parameter per frozen VecSearchInput field
        self,
        query: str,
        collections: list[str] | None = None,
        limit: int = 10,
        offset: int = 0,
        per_chunk: bool = False,
        min_score: float = 0.0,
        filter_node: FilterNode | None = None,
    ) -> list[SearchResult]:
        """Run the CLI ``sif search vsearch`` direct vector path (D-17).

        Identity is evaluated BEFORE ``embed_query`` (Phase 21 order): a
        dimension mismatch refuses with the shared remedy, a same-width
        untrusted swap warns once and marks the page. The searcher gets the
        query embedding's own length, and exactly one ``enrich_results`` runs
        with the correct untrusted flag. No expansion, no prefix routing, no
        reranking.

        A missing embedder raises ``RuntimeError`` naming the install/model
        remedy; the tool boundary maps it to a ``ToolError`` (D-15).
        """
        manager = self._ensure_embedder()
        if manager is None:
            raise RuntimeError(VECTOR_SEARCH_REMEDY)

        def _search(conn: Any) -> list[SearchResult]:
            collection_ids = _resolve_collection_ids(conn, collections)
            if collections and not collection_ids:
                return _with_suggestions(conn, query, [])
            identity = self._identity
            identity_check = (
                check_identity(conn, identity, mode="search") if identity is not None else None
            )
            if identity_check is not None:
                if identity_check.dimension_mismatch:
                    raise search_dimension_error(identity_check, schema_embedding_dim(conn))
                if identity_check.untrusted and identity_check.stored is not None:
                    warn_identity_mismatch_once(identity_check.stored, identity_check.current)
            options = SearchOptions(
                limit=limit,
                offset=offset,
                per_chunk=per_chunk,
                min_score=min_score,
                include_content=False,
                include_highlights=True,
                filter=filter_node,
                collection_ids=collection_ids,
            )
            query_embedding = manager.embed_query(query)
            searcher = VectorSearcher(conn, len(query_embedding))
            results = searcher.search(query_embedding, options)
            # CORR-05: the direct exit owns exactly one enrichment.
            if identity_check is not None and identity_check.untrusted:
                results = enrich_results(conn, results, vectors_untrusted=True)
            else:
                results = enrich_results(conn, results)
            return _with_suggestions(conn, query, _map_core_results(results))

        return await self._run_in_db(_search)

    async def metadata(  # noqa: PLR0913 — one keyword per the frozen D-15 input model
        self,
        *,
        collections: list[str] | None,
        filter_node: FilterNode | None,
        match: FilterNode | None,
        min_count: int,
        sort: str,
        limit: int,
        value_limit: int,
    ) -> dict[str, Any]:
        """Discover filterable metadata over the same store the filters read (D-16).

        ``filter_node``/``match`` are already-validated ASTs (the handler owns
        the shared grammar). Each predicate is compiled only when its node is
        present and an absent one is passed to ``discover`` as ``None`` —
        never ``compile_filter(None)``'s empty ``("", [])`` fragment, which
        would falsely signal a supplied filter and add ``filteredDocuments``
        to the no-filter envelope (D-15/D-20). An unknown collection name
        raises so the server turns the call into a tool execution error.
        """

        def _discover(conn: Any) -> dict[str, Any]:
            collection_ids: list[str] | None = None
            if collections:
                repo = CollectionRepository(conn)
                resolved = [repo.get_by_name(name) for name in collections]
                if any(collection is None for collection in resolved):
                    raise ValueError("One or more collections were not found")
                collection_ids = [collection.id for collection in resolved if collection]
            filter_predicate = (
                compile_filter(filter_node, alias="d", scope="corpus")
                if filter_node is not None
                else None
            )
            match_predicate = compile_match(match, alias="mv") if match is not None else None
            return MetadataValueRepository(conn).discover(
                collection_ids=collection_ids,
                filter_predicate=filter_predicate,
                match_predicate=match_predicate,
                min_count=min_count,
                sort=sort,
                limit=limit,
                value_limit=value_limit,
            )

        return await self._run_in_db(_discover)

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
