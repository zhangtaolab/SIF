"""Behavior tests for collection entities and manager services."""

from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest

from sif.core.collection import Collection, CollectionManager, CollectionRepository


@pytest.fixture
def repository() -> MagicMock:
    """Provide a controlled CollectionRepository Protocol double."""
    return MagicMock(spec=CollectionRepository)


@pytest.fixture
def manager(repository: MagicMock) -> CollectionManager:
    """Inject the repository double into the collection service."""
    return CollectionManager(repository)


def make_collection(collection_id: str = "collection-1", name: str = "notes") -> Collection:
    """Build a real collection entity with one initial path."""
    return Collection(
        id=collection_id,
        name=name,
        description="Original description",
        paths=["/notes/original"],
    )


class TestCollectionManager:
    """CollectionManager validates operations and persists real entity changes."""

    def test_create_collection_with_complete_fields(
        self, manager: CollectionManager, repository: MagicMock
    ) -> None:
        """Creation preserves supplied fields and generates an entity ID."""
        repository.exists.return_value = False
        repository.create.side_effect = lambda collection: collection

        result = manager.create_collection(
            "notes",
            description="Personal notes",
            paths=["/notes"],
            metadata={"owner": "me"},
        )

        assert result.id
        assert result.name == "notes"
        assert result.description == "Personal notes"
        assert result.paths == ["/notes"]
        assert result.metadata == {"owner": "me"}
        repository.exists.assert_called_once_with("notes")
        repository.create.assert_called_once_with(result)

    def test_create_collection_defaults_optional_containers(
        self, manager: CollectionManager, repository: MagicMock
    ) -> None:
        """Omitted paths and metadata become independent empty containers."""
        repository.exists.return_value = False
        repository.create.side_effect = lambda collection: collection

        first = manager.create_collection("first")
        second = manager.create_collection("second")

        assert first.description is None
        assert first.paths == []
        assert first.metadata == {}
        assert first.paths is not second.paths
        assert first.metadata is not second.metadata

    def test_create_duplicate_collection_raises(
        self, manager: CollectionManager, repository: MagicMock
    ) -> None:
        """A duplicate name is rejected before repository creation."""
        repository.exists.return_value = True

        with pytest.raises(ValueError, match="Collection 'notes' already exists"):
            manager.create_collection("notes")

        repository.create.assert_not_called()

    def test_get_and_list_return_repository_entities(
        self, manager: CollectionManager, repository: MagicMock
    ) -> None:
        """Read operations return real entities from the repository boundary."""
        collection = make_collection()
        repository.get_by_id.return_value = collection
        repository.list_all.return_value = [collection]

        assert manager.get_collection(collection.id) is collection
        assert manager.list_collections() == [collection]
        repository.get_by_id.assert_called_once_with(collection.id)
        repository.list_all.assert_called_once_with()

    def test_update_collection_applies_partial_changes(
        self, manager: CollectionManager, repository: MagicMock
    ) -> None:
        """Only supplied fields change; update persists the same real entity."""
        collection = make_collection()
        old_timestamp = datetime(2025, 1, 1, tzinfo=timezone.utc)
        collection.updated_at = old_timestamp
        repository.get_by_id.return_value = collection
        repository.update.side_effect = lambda value: value

        renamed = manager.update_collection(collection.id, name="renamed")

        assert renamed.name == "renamed"
        assert renamed.description == "Original description"
        assert renamed.updated_at > old_timestamp

        redescribed = manager.update_collection(collection.id, description="New description")

        assert redescribed.name == "renamed"
        assert redescribed.description == "New description"
        assert repository.update.call_count == 2

    def test_update_missing_collection_raises(
        self, manager: CollectionManager, repository: MagicMock
    ) -> None:
        """Updating a missing ID raises and performs no write."""
        repository.get_by_id.return_value = None

        with pytest.raises(ValueError, match="Collection 'missing' not found"):
            manager.update_collection("missing", name="new")

        repository.update.assert_not_called()

    @pytest.mark.parametrize("deleted", [True, False])
    def test_delete_collection_returns_repository_result(
        self, manager: CollectionManager, repository: MagicMock, deleted: bool
    ) -> None:
        """Deletion exposes the repository's success result."""
        repository.delete.return_value = deleted

        assert manager.delete_collection("collection-1") is deleted
        repository.delete.assert_called_once_with("collection-1")

    def test_add_path_updates_entity_and_ignores_duplicate(
        self, manager: CollectionManager, repository: MagicMock
    ) -> None:
        """Path addition changes state once and remains idempotent for duplicates."""
        collection = make_collection()
        repository.get_by_id.return_value = collection
        repository.update.side_effect = lambda value: value

        result = manager.add_path(collection.id, "/notes/new")
        assert result.paths == ["/notes/original", "/notes/new"]

        timestamp = result.updated_at
        result = manager.add_path(collection.id, "/notes/new")
        assert result.paths == ["/notes/original", "/notes/new"]
        assert result.updated_at == timestamp
        assert repository.update.call_count == 2

    def test_remove_path_updates_entity_and_ignores_absent_path(
        self, manager: CollectionManager, repository: MagicMock
    ) -> None:
        """Removing an existing path changes state; an absent path is a no-op."""
        collection = make_collection()
        repository.get_by_id.return_value = collection
        repository.update.side_effect = lambda value: value

        result = manager.remove_path(collection.id, "/notes/original")
        assert result.paths == []

        timestamp = result.updated_at
        result = manager.remove_path(collection.id, "/notes/absent")
        assert result.paths == []
        assert result.updated_at == timestamp
        assert repository.update.call_count == 2

    @pytest.mark.parametrize("operation", ["add_path", "remove_path"])
    def test_path_operation_missing_collection_raises(
        self, manager: CollectionManager, repository: MagicMock, operation: str
    ) -> None:
        """Both path operations reject missing IDs without repository writes."""
        repository.get_by_id.return_value = None

        with pytest.raises(ValueError, match="Collection 'missing' not found"):
            getattr(manager, operation)("missing", "/notes")

        repository.update.assert_not_called()


class TestCollectionEntity:
    """Collection entity methods own their state transitions."""

    def test_add_and_remove_path_manage_timestamp_and_membership(self) -> None:
        """Only actual path membership changes advance the update timestamp."""
        collection = make_collection()
        collection.paths = []
        old_timestamp = datetime(2025, 1, 1, tzinfo=timezone.utc)
        collection.updated_at = old_timestamp

        collection.add_path("/notes")
        assert collection.paths == ["/notes"]
        assert collection.updated_at > old_timestamp

        added_timestamp = collection.updated_at
        collection.add_path("/notes")
        assert collection.paths == ["/notes"]
        assert collection.updated_at == added_timestamp

        collection.remove_path("/notes")
        assert collection.paths == []
        assert collection.updated_at > added_timestamp

        removed_timestamp = collection.updated_at
        collection.remove_path("/notes")
        assert collection.updated_at == removed_timestamp

    def test_update_metadata_merges_values(self) -> None:
        """Metadata updates retain existing keys and replace matching keys."""
        collection = make_collection()
        collection.metadata = {"keep": True, "replace": "old"}
        old_timestamp = datetime(2025, 1, 1, tzinfo=timezone.utc)
        collection.updated_at = old_timestamp

        collection.update_metadata(replace="new", added=3)

        assert collection.metadata == {"keep": True, "replace": "new", "added": 3}
        assert collection.updated_at > old_timestamp

    def test_mark_indexed_sets_both_timestamps(self) -> None:
        """Marking indexed records an indexing time and refreshes update time."""
        collection = make_collection()
        old_timestamp = datetime(2025, 1, 1, tzinfo=timezone.utc)
        collection.updated_at = old_timestamp

        collection.mark_indexed()

        assert collection.last_indexed_at is not None
        assert collection.last_indexed_at.tzinfo is timezone.utc
        assert collection.updated_at > old_timestamp
