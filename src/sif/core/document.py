"""Document domain entity."""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Protocol


@dataclass
class DocumentMetadata:
    """Metadata extracted from document frontmatter."""

    title: str | None = None
    author: str | None = None
    date: datetime | None = None
    tags: list[str] = field(default_factory=list)
    categories: list[str] = field(default_factory=list)
    custom: dict[str, Any] = field(default_factory=dict)


@dataclass
class DocumentChunk:
    """A chunk of a document with embedding information."""

    id: str
    document_id: str
    content: str
    start_line: int
    end_line: int
    token_count: int
    embedding_id: str | None = None
    embedding: list[float] | None = None

    def __post_init__(self) -> None:
        """Validate chunk data."""
        if self.start_line > self.end_line:
            raise ValueError("start_line cannot be greater than end_line")


@dataclass
class Document:
    """Domain entity representing a document.

    A document is a single markdown file that has been indexed.
    It contains the document content, metadata, and chunks.
    """

    id: str
    collection_id: str
    path: str
    content: str
    checksum: str
    file_size: int
    metadata: DocumentMetadata = field(default_factory=DocumentMetadata)
    chunks: list[DocumentChunk] = field(default_factory=list)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    indexed_at: datetime | None = None

    @property
    def title(self) -> str | None:
        """Get document title from metadata or path."""
        if self.metadata.title:
            return self.metadata.title
        # Extract filename as fallback
        import os  # noqa: PLC0415

        return os.path.splitext(os.path.basename(self.path))[0]

    @property
    def chunk_count(self) -> int:
        """Get the number of chunks."""
        return len(self.chunks)

    def add_chunk(self, chunk: DocumentChunk) -> None:
        """Add a chunk to the document."""
        self.chunks.append(chunk)

    def clear_chunks(self) -> None:
        """Remove all chunks from the document."""
        self.chunks.clear()

    def mark_indexed(self) -> None:
        """Mark the document as indexed."""
        self.indexed_at = datetime.now(timezone.utc)
        self.updated_at = datetime.now(timezone.utc)


class DocumentRepository(Protocol):
    """Protocol for document repository operations."""

    def get_by_id(self, document_id: str) -> Document | None:
        """Get a document by ID."""
        ...

    def get_by_path(self, path: str, collection_id: str) -> Document | None:
        """Get a document by path within a collection."""
        ...

    def list_by_collection(self, collection_id: str) -> list[Document]:
        """List all documents in a collection."""
        ...

    def create(self, document: Document) -> Document:
        """Create a new document."""
        ...

    def update(self, document: Document) -> Document:
        """Update an existing document."""
        ...

    def delete(self, document_id: str) -> bool:
        """Delete a document by ID."""
        ...

    def delete_by_collection(self, collection_id: str) -> int:
        """Delete all documents in a collection. Returns count deleted."""
        ...

    def exists(self, path: str, collection_id: str) -> bool:
        """Check if a document exists at the given path."""
        ...

    def get_checksum(self, document_id: str) -> str | None:
        """Get the checksum of a document."""
        ...
