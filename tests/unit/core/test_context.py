"""Behavior tests for context entities and manager services."""

from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock

import pytest

from sif.core.context import Context, ContextManager, ContextRepository, ContextType


def make_context(
    context_id: str,
    target_id: str,
    content: str,
    context_type: ContextType,
) -> Context:
    """Build a real context entity for repository-double results."""
    return Context(
        id=context_id,
        target_id=target_id,
        content=content,
        context_type=context_type,
    )


@pytest.fixture
def repository() -> MagicMock:
    """Provide a controlled ContextRepository Protocol double."""
    return MagicMock(spec=ContextRepository)


@pytest.fixture
def manager(repository: MagicMock) -> ContextManager:
    """Inject the repository double into the service under test."""
    return ContextManager(repository)


class TestContextManager:
    """ContextManager coordinates real entities with its repository Protocol."""

    def test_add_context_creates_and_updates_existing_target(
        self, manager: ContextManager, repository: MagicMock
    ) -> None:
        """Adding creates a missing target, then refreshes that target's content."""
        repository.get_by_target.return_value = None
        repository.create.side_effect = lambda context: context

        created = manager.add_context("notes", "Collection guidance", ContextType.COLLECTION)

        assert created.target_id == "notes"
        assert created.content == "Collection guidance"
        assert created.context_type is ContextType.COLLECTION
        assert created.id
        repository.create.assert_called_once_with(created)

        existing = make_context("context-1", "notes", "Old guidance", ContextType.COLLECTION)
        old_timestamp = existing.updated_at - timedelta(seconds=1)
        existing.updated_at = old_timestamp
        repository.get_by_target.return_value = existing
        repository.update.side_effect = lambda context: context

        updated = manager.add_context("notes", "New guidance", ContextType.COLLECTION)

        assert updated is existing
        assert updated.content == "New guidance"
        assert updated.updated_at > old_timestamp
        repository.update.assert_called_once_with(existing)
        repository.create.assert_called_once()

    def test_get_context_and_target_return_repository_entities(
        self, manager: ContextManager, repository: MagicMock
    ) -> None:
        """Lookups expose actual entities and preserve the requested type."""
        expected = make_context("context-1", "/notes", "Path note", ContextType.PATH)
        repository.get_by_id.return_value = expected
        repository.get_by_target.return_value = expected

        assert manager.get_context("context-1") is expected
        assert manager.get_context_for_target("/notes", ContextType.PATH) is expected
        repository.get_by_id.assert_called_once_with("context-1")
        repository.get_by_target.assert_called_once_with("/notes", ContextType.PATH)

    def test_update_context_changes_content_and_timestamp(
        self, manager: ContextManager, repository: MagicMock
    ) -> None:
        """Updating persists the changed real entity and advances its timestamp."""
        context = make_context("context-1", "global", "Before", ContextType.GLOBAL)
        old_timestamp = datetime(2025, 1, 1, tzinfo=timezone.utc)
        context.updated_at = old_timestamp
        repository.get_by_id.return_value = context
        repository.update.side_effect = lambda value: value

        result = manager.update_context("context-1", "After")

        assert result.content == "After"
        assert result.updated_at > old_timestamp
        repository.update.assert_called_once_with(context)

    def test_update_missing_context_raises(
        self, manager: ContextManager, repository: MagicMock
    ) -> None:
        """A missing ID is an error and never reaches repository update."""
        repository.get_by_id.return_value = None

        with pytest.raises(ValueError, match="Context 'missing' not found"):
            manager.update_context("missing", "content")

        repository.update.assert_not_called()

    @pytest.mark.parametrize("deleted", [True, False])
    def test_remove_context_reports_repository_result(
        self, manager: ContextManager, repository: MagicMock, deleted: bool
    ) -> None:
        """Removal returns whether the repository deleted the requested row."""
        repository.delete.return_value = deleted

        assert manager.remove_context("context-1") is deleted
        repository.delete.assert_called_once_with("context-1")

    def test_list_contexts_filtered_and_unfiltered(
        self, manager: ContextManager, repository: MagicMock
    ) -> None:
        """Listing uses the type-specific query only when a filter is supplied."""
        filtered = [make_context("1", "global", "Global", ContextType.GLOBAL)]
        everything = [*filtered, make_context("2", "/a", "Path", ContextType.PATH)]
        repository.list_by_type.return_value = filtered
        repository.list_all.return_value = everything

        assert manager.list_contexts(ContextType.GLOBAL) == filtered
        assert manager.list_contexts() == everything
        repository.list_by_type.assert_called_once_with(ContextType.GLOBAL)
        repository.list_all.assert_called_once_with()

    def test_build_search_context_orders_and_filters_content(
        self, manager: ContextManager, repository: MagicMock
    ) -> None:
        """Global, matching collection, and matching path content join deterministically."""
        global_contexts = [
            make_context("g1", "global", "Global one", ContextType.GLOBAL),
            make_context("g2", "global", "Global two", ContextType.GLOBAL),
        ]
        path_contexts = [
            make_context("p1", "/notes/python/a.md", "Python path", ContextType.PATH),
            make_context("p2", "/other/b.md", "Excluded path", ContextType.PATH),
            make_context("p3", "/notes/rust/c.md", "Rust path", ContextType.PATH),
        ]
        collections = {
            "notes": make_context("c1", "notes", "Notes collection", ContextType.COLLECTION),
            "work": make_context("c2", "work", "Work collection", ContextType.COLLECTION),
        }

        def list_by_type(context_type: ContextType) -> list[Context]:
            if context_type is ContextType.GLOBAL:
                return global_contexts
            if context_type is ContextType.PATH:
                return path_contexts
            return []

        repository.list_by_type.side_effect = list_by_type
        repository.get_by_target.side_effect = lambda target, _kind: collections.get(target)

        result = manager.build_search_context(
            collection_ids=["notes", "missing", "work"],
            path_prefixes=["/notes/"],
        )

        assert result == (
            "Global one\n\nGlobal two\n\nNotes collection\n\nWork collection"
            "\n\nPython path\n\nRust path"
        )
        assert "Excluded path" not in result

    def test_build_search_context_handles_empty_filters_and_no_matches(
        self, manager: ContextManager, repository: MagicMock
    ) -> None:
        """Empty filters produce no queries beyond globals, and no content returns empty."""
        unmatched = make_context("p1", "/other/a.md", "Other", ContextType.PATH)
        repository.list_by_type.side_effect = lambda kind: (
            [unmatched] if kind is ContextType.PATH else []
        )
        repository.get_by_target.return_value = None

        assert manager.build_search_context(collection_ids=[], path_prefixes=[]) == ""
        repository.get_by_target.assert_not_called()
        assert manager.build_search_context(path_prefixes=["/notes/"]) == ""

    def test_update_content_directly_changes_entity(self) -> None:
        """The entity method replaces content and advances its own timestamp."""
        context = make_context("context-1", "global", "Old", ContextType.GLOBAL)
        old_timestamp = datetime(2025, 1, 1, tzinfo=timezone.utc)
        context.updated_at = old_timestamp

        context.update_content("New")

        assert context.content == "New"
        assert context.updated_at > old_timestamp
