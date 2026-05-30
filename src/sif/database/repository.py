"""Repository interface definitions."""

from abc import ABC, abstractmethod
from typing import Any, Generic, TypeVar

from sif.core.collection import Collection
from sif.core.context import Context, ContextType
from sif.core.document import Document, DocumentChunk


T = TypeVar("T")


class Repository(ABC, Generic[T]):
    """Abstract base class for repositories.

    Implements the Repository pattern for data access abstraction.
    """

    @abstractmethod
    def get_by_id(self, entity_id: str) -> T | None:
        """Get an entity by ID."""
        ...

    @abstractmethod
    def create(self, entity: T) -> T:
        """Create a new entity."""
        ...

    @abstractmethod
    def update(self, entity: T) -> T:
        """Update an existing entity."""
        ...

    @abstractmethod
    def delete(self, entity_id: str) -> bool:
        """Delete an entity by ID."""
        ...


class CollectionRepository(Repository[Collection]):
    """Repository for Collection entities."""

    @abstractmethod
    def get_by_name(self, name: str) -> Collection | None:
        """Get a collection by name."""
        ...

    @abstractmethod
    def list_all(self) -> list[Collection]:
        """List all collections."""
        ...

    @abstractmethod
    def exists(self, name: str) -> bool:
        """Check if a collection with the given name exists."""
        ...


class DocumentRepository(Repository[Document]):
    """Repository for Document entities."""

    @abstractmethod
    def get_by_path(self, path: str, collection_id: str) -> Document | None:
        """Get a document by path within a collection."""
        ...

    @abstractmethod
    def list_by_collection(self, collection_id: str) -> list[Document]:
        """List all documents in a collection."""
        ...

    @abstractmethod
    def delete_by_collection(self, collection_id: str) -> int:
        """Delete all documents in a collection. Returns count deleted."""
        ...

    @abstractmethod
    def exists(self, path: str, collection_id: str) -> bool:
        """Check if a document exists at the given path."""
        ...

    @abstractmethod
    def get_checksum(self, document_id: str) -> str | None:
        """Get the checksum of a document."""
        ...

    @abstractmethod
    def get_chunks(self, document_id: str) -> list[DocumentChunk]:
        """Get all chunks for a document."""
        ...

    @abstractmethod
    def save_chunks(self, document_id: str, chunks: list[DocumentChunk]) -> list[DocumentChunk]:
        """Save chunks for a document."""
        ...


class ContextRepository(Repository[Context]):
    """Repository for Context entities."""

    @abstractmethod
    def get_by_target(self, target_id: str, context_type: ContextType) -> Context | None:
        """Get context by target ID and type."""
        ...

    @abstractmethod
    def list_by_type(self, context_type: ContextType) -> list[Context]:
        """List all contexts of a specific type."""
        ...

    @abstractmethod
    def list_all(self) -> list[Context]:
        """List all contexts."""
        ...

    @abstractmethod
    def delete_by_target(self, target_id: str) -> bool:
        """Delete all contexts for a target."""
        ...


class SearchRepository(ABC):
    """Repository for search operations."""

    @abstractmethod
    def search_fts(
        self,
        query: str,
        collection_ids: list[str] | None,
        limit: int,
        offset: int,
    ) -> list[tuple[str, float]]:
        """Search using full-text search (BM25).

        Returns:
            List of (document_id, score) tuples
        """
        ...

    @abstractmethod
    def search_vector(
        self,
        embedding: list[float],
        collection_ids: list[str] | None,
        limit: int,
        offset: int,
    ) -> list[tuple[str, float]]:
        """Search using vector similarity.

        Returns:
            List of (document_id, score) tuples
        """
        ...

    @abstractmethod
    def get_document_for_result(
        self,
        document_id: str,
        include_chunks: bool = True,
    ) -> dict[str, Any] | None:
        """Get document details for a search result."""
        ...

    @abstractmethod
    def get_highlights(
        self,
        document_id: str,
        query: str,
        max_highlights: int = 3,
    ) -> list[str]:
        """Get highlighted snippets for a document."""
        ...
