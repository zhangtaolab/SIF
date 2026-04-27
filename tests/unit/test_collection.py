"""Unit tests for collection management."""

from datetime import datetime

import pytest

from sif.core.collection import Collection, CollectionManager
from sif.models.collection import CollectionCreate, CollectionResponse


class MockCollectionRepository:
    """Mock repository for testing."""

    def __init__(self):
        self._collections = {}

    def get_by_id(self, collection_id: str):
        return self._collections.get(collection_id)

    def get_by_name(self, name: str):
        for c in self._collections.values():
            if c.name == name:
                return c
        return None

    def list_all(self):
        return list(self._collections.values())

    def create(self, collection):
        self._collections[collection.id] = collection
        return collection

    def update(self, collection):
        self._collections[collection.id] = collection
        return collection

    def delete(self, collection_id: str):
        return self._collections.pop(collection_id, None) is not None

    def exists(self, name: str):
        return any(c.name == name for c in self._collections.values())


class TestCollection:
    """Tests for Collection entity."""

    def test_collection_creation(self):
        """Test creating a collection."""
        collection = Collection(
            id="test-id",
            name="test-collection",
            description="Test description",
        )

        assert collection.id == "test-id"
        assert collection.name == "test-collection"
        assert collection.description == "Test description"
        assert collection.paths == []

    def test_add_path(self):
        """Test adding a path to a collection."""
        collection = Collection(id="test-id", name="test")

        collection.add_path("/path/one")
        collection.add_path("/path/two")

        assert "/path/one" in collection.paths
        assert "/path/two" in collection.paths

    def test_add_duplicate_path(self):
        """Test adding a duplicate path is ignored."""
        collection = Collection(id="test-id", name="test")

        collection.add_path("/path/one")
        collection.add_path("/path/one")

        assert len(collection.paths) == 1

    def test_remove_path(self):
        """Test removing a path from a collection."""
        collection = Collection(id="test-id", name="test", paths=["/path/one"])

        collection.remove_path("/path/one")

        assert "/path/one" not in collection.paths


class TestCollectionManager:
    """Tests for CollectionManager."""

    @pytest.fixture
    def manager(self):
        """Create a collection manager with mock repository."""
        return CollectionManager(MockCollectionRepository())

    def test_create_collection(self, manager):
        """Test creating a collection."""
        collection = manager.create_collection(
            name="my-collection",
            description="My test collection",
        )

        assert collection.name == "my-collection"
        assert collection.description == "My test collection"

    def test_create_duplicate_collection(self, manager):
        """Test creating a duplicate collection raises error."""
        manager.create_collection(name="my-collection")

        with pytest.raises(ValueError, match="already exists"):
            manager.create_collection(name="my-collection")

    def test_get_collection(self, manager):
        """Test getting a collection by ID."""
        created = manager.create_collection(name="my-collection")
        retrieved = manager.get_collection(created.id)

        assert retrieved is not None
        assert retrieved.id == created.id

    def test_list_collections(self, manager):
        """Test listing all collections."""
        manager.create_collection(name="collection-1")
        manager.create_collection(name="collection-2")

        collections = manager.list_collections()

        assert len(collections) == 2

    def test_delete_collection(self, manager):
        """Test deleting a collection."""
        created = manager.create_collection(name="my-collection")

        result = manager.delete_collection(created.id)

        assert result is True
        assert manager.get_collection(created.id) is None


class TestCollectionModels:
    """Tests for collection Pydantic models."""

    def test_collection_create_validation(self):
        """Test CollectionCreate validation."""
        data = {
            "name": "test-collection",
            "description": "Test description",
            "paths": ["/path/one"],
        }

        model = CollectionCreate(**data)

        assert model.name == "test-collection"
        assert model.description == "Test description"

    def test_collection_create_name_required(self):
        """Test that name is required."""
        with pytest.raises(Exception):
            CollectionCreate(name="")

    def test_collection_response(self):
        """Test CollectionResponse model."""
        data = {
            "id": "test-id",
            "name": "test-collection",
            "paths": ["/path/one"],
            "document_count": 10,
            "chunk_count": 50,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
        }

        model = CollectionResponse(**data)

        assert model.id == "test-id"
        assert model.document_count == 10
