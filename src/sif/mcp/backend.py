"""SearchBackend for MCP tool handlers."""

from __future__ import annotations

from sif.config.settings import Settings, get_settings
from sif.mcp.protocol import CollectionInfo, Document, SearchResult


class SearchBackend:
    """Backend for MCP search and retrieval operations."""

    def __init__(self, db_path: str, settings: Settings | None = None) -> None:
        """Initialize SearchBackend."""
        self.db_path = db_path
        self.settings = settings or get_settings()

    async def hybrid_search(
        self,
        query: str,
        collections: list[str] | None = None,
        limit: int = 10,
        min_score: float = 0.0,
    ) -> list[SearchResult]:
        """Perform hybrid search."""
        raise NotImplementedError("Implemented in plan 09-02")

    async def get_document(
        self,
        path_or_docid: str,
        from_line: int | None = None,
        max_lines: int | None = None,
    ) -> Document | None:
        """Get a document by path or doc_id."""
        raise NotImplementedError("Implemented in plan 09-02")

    async def get_documents_by_pattern(
        self,
        pattern: str,
        max_bytes: int | None = None,
    ) -> tuple[list[Document], list[str]]:
        """Get documents matching a pattern."""
        raise NotImplementedError("Implemented in plan 09-02")

    async def get_status(self) -> tuple[list[CollectionInfo], int]:
        """Get index status."""
        raise NotImplementedError("Implemented in plan 09-02")
