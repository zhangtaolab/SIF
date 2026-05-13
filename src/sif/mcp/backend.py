"""SearchBackend for MCP tool handlers."""

from __future__ import annotations

import asyncio
import fnmatch
from typing import Any, Callable, TypeVar

from sif.config.settings import Settings, get_settings
from sif.core.models import SearchOptions
from sif.database.connection import DatabaseConnection
from sif.database.repositories import CollectionRepository, DocumentRepository
from sif.embedding.factory import EmbeddingModelFactory
from sif.embedding.model import ModelType
from sif.mcp.protocol import CollectionInfo, Document, SearchResult
from sif.search.hybrid import SearchPipeline
from sif.utils.logging import get_logger


logger = get_logger(__name__)


T = TypeVar("T")


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
        try:
            factory = EmbeddingModelFactory()
            model_type = ModelType(self.settings.model_type)
            model_path = str(self.settings.model_path) if self.settings.model_path else None
            self._embedder = factory.create_model(
                model_type,
                model_path,
                self.settings.model_name,
            )
        except Exception:
            logger.warning("Failed to load embedder; vector search will be unavailable")

    async def _run_in_db(self, callback: Callable[[Any], T]) -> T:
        """Run a callback with a fresh database connection in a thread."""

        def _run() -> T:
            with DatabaseConnection(self.db_path).transaction() as conn:
                return callback(conn)

        return await asyncio.to_thread(_run)

    async def hybrid_search(
        self,
        query: str,
        collections: list[str] | None = None,
        limit: int = 10,
        min_score: float = 0.0,
    ) -> list[SearchResult]:
        """Perform hybrid search."""

        def _search(conn: Any) -> list[SearchResult]:
            options = SearchOptions(
                limit=limit,
                min_score=min_score,
                include_content=False,
                include_highlights=True,
            )
            if collections:
                repo = CollectionRepository(conn)
                matched = [c.id for c in (repo.get_by_name(n) for n in collections) if c]
                if not matched:
                    return []
                options.collection_ids = matched
            pipeline = SearchPipeline(
                conn,
                embedder=self._embedder,
                embedding_dim=self.settings.embedding_dim,
            )
            core_results = pipeline.search(query, options)
            return [
                SearchResult(
                    doc_id=r.document_id,
                    path=r.path,
                    title=r.title,
                    content=r.content,
                    score=r.score,
                    highlights=r.highlights,
                    metadata={"rank": r.rank, "collection_name": r.collection_name},
                )
                for r in core_results
            ]

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
                    doc = repo.get_by_path(path_or_docid, coll.id)
                    if doc:
                        break
            if not doc:
                return None
            content = doc.content  # Do NOT truncate yet
            line_start: int | None = None
            line_end: int | None = None
            if from_line is not None:
                lines = content.split("\n")
                start = max(0, from_line - 1)
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
            for coll in coll_repo.list_all():
                for doc in doc_repo.list_by_collection(coll.id):
                    if fnmatch.fnmatch(doc.path, pattern) or fnmatch.fnmatch(doc.filename, pattern):
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
                            )
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
                    )
                )
            total = sum(info.document_count for info in infos)
            return infos, total

        return await self._run_in_db(_status)
