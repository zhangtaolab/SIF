"""Collection domain entity and manager."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Protocol


@dataclass
class Collection:
    """Domain entity representing a document collection.

    A collection is a logical grouping of documents, typically
    corresponding to a directory or set of directories.
    """

    id: str
    name: str
    description: str | None = None
    paths: list[str] = field(default_factory=list)
    document_count: int = 0
    chunk_count: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    last_indexed_at: datetime | None = None

    def add_path(self, path: str) -> None:
        """Add a path to the collection if not already present."""
        if path not in self.paths:
            self.paths.append(path)
            self.updated_at = datetime.utcnow()

    def remove_path(self, path: str) -> None:
        """Remove a path from the collection."""
        if path in self.paths:
            self.paths.remove(path)
            self.updated_at = datetime.utcnow()

    def update_metadata(self, **kwargs: Any) -> None:
        """Update collection metadata."""
        self.metadata.update(kwargs)
        self.updated_at = datetime.utcnow()

    def mark_indexed(self) -> None:
        """Mark the collection as indexed."""
        self.last_indexed_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()


class CollectionRepository(Protocol):
    """Protocol for collection repository operations."""

    def get_by_id(self, collection_id: str) -> Collection | None:
        """Get a collection by ID."""
        ...

    def get_by_name(self, name: str) -> Collection | None:
        """Get a collection by name."""
        ...

    def list_all(self) -> list[Collection]:
        """List all collections."""
        ...

    def create(self, collection: Collection) -> Collection:
        """Create a new collection."""
        ...

    def update(self, collection: Collection) -> Collection:
        """Update an existing collection."""
        ...

    def delete(self, collection_id: str) -> bool:
        """Delete a collection by ID."""
        ...

    def exists(self, name: str) -> bool:
        """Check if a collection with the given name exists."""
        ...


class CollectionManager:
    """Manager for collection operations.

    This class provides high-level operations for managing collections,
    coordinating between repositories and other services.
    """

    def __init__(self, repository: CollectionRepository) -> None:
        self._repository = repository

    def create_collection(
        self,
        name: str,
        description: str | None = None,
        paths: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> Collection:
        """Create a new collection."""
        import uuid

        if self._repository.exists(name):
            raise ValueError(f"Collection '{name}' already exists")

        collection = Collection(
            id=str(uuid.uuid4()),
            name=name,
            description=description,
            paths=paths or [],
            metadata=metadata or {},
        )
        return self._repository.create(collection)

    def get_collection(self, collection_id: str) -> Collection | None:
        """Get a collection by ID."""
        return self._repository.get_by_id(collection_id)

    def list_collections(self) -> list[Collection]:
        """List all collections."""
        return self._repository.list_all()

    def update_collection(
        self,
        collection_id: str,
        name: str | None = None,
        description: str | None = None,
    ) -> Collection:
        """Update a collection."""
        collection = self._repository.get_by_id(collection_id)
        if not collection:
            raise ValueError(f"Collection '{collection_id}' not found")

        if name is not None:
            collection.name = name
        if description is not None:
            collection.description = description

        collection.updated_at = datetime.utcnow()
        return self._repository.update(collection)

    def delete_collection(self, collection_id: str) -> bool:
        """Delete a collection."""
        return self._repository.delete(collection_id)

    def add_path(self, collection_id: str, path: str) -> Collection:
        """Add a path to a collection."""
        collection = self._repository.get_by_id(collection_id)
        if not collection:
            raise ValueError(f"Collection '{collection_id}' not found")

        collection.add_path(path)
        return self._repository.update(collection)

    def remove_path(self, collection_id: str, path: str) -> Collection:
        """Remove a path from a collection."""
        collection = self._repository.get_by_id(collection_id)
        if not collection:
            raise ValueError(f"Collection '{collection_id}' not found")

        collection.remove_path(path)
        return self._repository.update(collection)
