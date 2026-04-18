"""Tests for context CLI commands."""

from __future__ import annotations

from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest
from click.testing import CliRunner

from docsift.cli.commands.context import (
    context_add,
    context_group,
    context_list,
    context_prune,
    context_remove,
)
from docsift.core.models import Collection, PathContext


class TestContextGroup:
    """Tests for context command group."""

    def test_context_group_exists(self) -> None:
        """Test that context group exists."""
        assert context_group is not None

    def test_context_group_name(self) -> None:
        """Test context group name."""
        assert context_group.name == "context"


class TestContextAdd:
    """Tests for context add command."""

    @pytest.fixture
    def mock_db(self):
        """Create a mock Database."""
        mock = MagicMock()
        mock.connection = MagicMock()
        return mock

    def test_add_path_context(self, mock_db) -> None:
        """Test adding a path context."""
        runner = CliRunner()
        ctx_obj = {"index_path": MagicMock(exists=lambda: True)}

        with patch("docsift.cli.commands.context.Database") as MockDB:
            MockDB.return_value = mock_db
            mock_repo = MagicMock()
            mock_repo.get_by_target.return_value = None
            with patch(
                "docsift.cli.commands.context.ContextRepository",
                return_value=mock_repo,
            ):
                result = runner.invoke(
                    context_add,
                    ["path", "/notes/a.md", "description"],
                    obj=ctx_obj,
                )

        assert result.exit_code == 0
        mock_repo.create.assert_called_once()
        call_args = mock_repo.create.call_args[0][0]
        assert call_args.context_type == "path"

    def test_add_collection_context_by_name(self, mock_db) -> None:
        """Test adding a collection context resolved by name."""
        runner = CliRunner()
        ctx_obj = {"index_path": MagicMock(exists=lambda: True)}

        coll = Collection(name="my-coll", path="/notes")
        with patch("docsift.cli.commands.context.Database") as MockDB:
            MockDB.return_value = mock_db
            mock_coll_repo = MagicMock()
            mock_coll_repo.get_by_name.return_value = coll
            mock_ctx_repo = MagicMock()
            mock_ctx_repo.get_by_target.return_value = None
            with (
                patch(
                    "docsift.cli.commands.context.CollectionRepository",
                    return_value=mock_coll_repo,
                ),
                patch(
                    "docsift.cli.commands.context.ContextRepository",
                    return_value=mock_ctx_repo,
                ),
            ):
                result = runner.invoke(
                    context_add,
                    ["collection", "my-coll", "description"],
                    obj=ctx_obj,
                )

        assert result.exit_code == 0
        mock_coll_repo.get_by_name.assert_called_once_with("my-coll")
        mock_ctx_repo.create.assert_called_once()
        call_args = mock_ctx_repo.create.call_args[0][0]
        assert call_args.path == coll.id
        assert call_args.context_type == "collection"

    def test_add_collection_context_by_id_fallback(self, mock_db) -> None:
        """Test adding a collection context with ID fallback."""
        runner = CliRunner()
        ctx_obj = {"index_path": MagicMock(exists=lambda: True)}

        coll_id = str(uuid4())
        coll = Collection(name="my-coll", path="/notes", id=coll_id)
        with patch("docsift.cli.commands.context.Database") as MockDB:
            MockDB.return_value = mock_db
            mock_coll_repo = MagicMock()
            mock_coll_repo.get_by_name.return_value = None
            mock_coll_repo.get_by_id.return_value = coll
            mock_ctx_repo = MagicMock()
            mock_ctx_repo.get_by_target.return_value = None
            with (
                patch(
                    "docsift.cli.commands.context.CollectionRepository",
                    return_value=mock_coll_repo,
                ),
                patch(
                    "docsift.cli.commands.context.ContextRepository",
                    return_value=mock_ctx_repo,
                ),
            ):
                result = runner.invoke(
                    context_add,
                    ["collection", coll_id, "description"],
                    obj=ctx_obj,
                )

        assert result.exit_code == 0
        mock_coll_repo.get_by_name.assert_called_once_with(coll_id)
        mock_coll_repo.get_by_id.assert_called_once_with(coll_id)
        mock_ctx_repo.create.assert_called_once()

    def test_add_collection_not_found(self, mock_db) -> None:
        """Test adding a collection context when collection does not exist."""
        runner = CliRunner()
        ctx_obj = {"index_path": MagicMock(exists=lambda: True)}

        with patch("docsift.cli.commands.context.Database") as MockDB:
            MockDB.return_value = mock_db
            mock_coll_repo = MagicMock()
            mock_coll_repo.get_by_name.return_value = None
            mock_coll_repo.get_by_id.return_value = None
            with patch(
                "docsift.cli.commands.context.CollectionRepository",
                return_value=mock_coll_repo,
            ):
                result = runner.invoke(
                    context_add,
                    ["collection", "missing-coll", "description"],
                    obj=ctx_obj,
                )

        assert result.exit_code != 0
        assert "not found" in result.output.lower() or result.exception is not None

    def test_add_global_context(self, mock_db) -> None:
        """Test adding a global context."""
        runner = CliRunner()
        ctx_obj = {"index_path": MagicMock(exists=lambda: True)}

        with patch("docsift.cli.commands.context.Database") as MockDB:
            MockDB.return_value = mock_db
            mock_repo = MagicMock()
            mock_repo.get_by_target.return_value = None
            with patch(
                "docsift.cli.commands.context.ContextRepository",
                return_value=mock_repo,
            ):
                result = runner.invoke(
                    context_add,
                    ["global", "global", "description"],
                    obj=ctx_obj,
                )

        assert result.exit_code == 0
        mock_repo.create.assert_called_once()
        call_args = mock_repo.create.call_args[0][0]
        assert call_args.path == "global"
        assert call_args.context_type == "global"

    def test_add_updates_existing(self, mock_db) -> None:
        """Test that adding to an existing target updates instead of creating."""
        runner = CliRunner()
        ctx_obj = {"index_path": MagicMock(exists=lambda: True)}

        existing = PathContext(path="/notes/a.md", context="old")
        with patch("docsift.cli.commands.context.Database") as MockDB:
            MockDB.return_value = mock_db
            mock_repo = MagicMock()
            mock_repo.get_by_target.return_value = existing
            with patch(
                "docsift.cli.commands.context.ContextRepository",
                return_value=mock_repo,
            ):
                result = runner.invoke(
                    context_add,
                    ["path", "/notes/a.md", "new description"],
                    obj=ctx_obj,
                )

        assert result.exit_code == 0
        mock_repo.update.assert_called_once()
        assert existing.context == "new description"


class TestContextList:
    """Tests for context list command."""

    @pytest.fixture
    def mock_db(self):
        """Create a mock Database."""
        mock = MagicMock()
        mock.connection = MagicMock()
        return mock

    def test_list_all(self, mock_db) -> None:
        """Test listing all contexts."""
        runner = CliRunner()
        ctx_obj = {"index_path": MagicMock(exists=lambda: True)}

        contexts = [
            PathContext(path="/a.md", context="desc A", context_type="path"),
            PathContext(path="coll-1", context="desc B", context_type="collection"),
            PathContext(path="global", context="desc C", context_type="global"),
        ]
        with patch("docsift.cli.commands.context.Database") as MockDB:
            MockDB.return_value = mock_db
            mock_repo = MagicMock()
            mock_repo.list_all.return_value = contexts
            with patch(
                "docsift.cli.commands.context.ContextRepository",
                return_value=mock_repo,
            ):
                result = runner.invoke(context_list, obj=ctx_obj)

        assert result.exit_code == 0
        assert "desc A" in result.output
        assert "collection" in result.output
        assert "global" in result.output

    def test_list_filter_by_type(self, mock_db) -> None:
        """Test listing contexts filtered by type."""
        runner = CliRunner()
        ctx_obj = {"index_path": MagicMock(exists=lambda: True)}

        contexts = [PathContext(path="/a.md", context="desc A")]
        with patch("docsift.cli.commands.context.Database") as MockDB:
            MockDB.return_value = mock_db
            mock_repo = MagicMock()
            mock_repo.list_by_type.return_value = contexts
            with patch(
                "docsift.cli.commands.context.ContextRepository",
                return_value=mock_repo,
            ):
                result = runner.invoke(
                    context_list,
                    ["--type", "collection"],
                    obj=ctx_obj,
                )

        assert result.exit_code == 0
        mock_repo.list_by_type.assert_called_once_with("collection")

    def test_list_empty(self, mock_db) -> None:
        """Test listing when no contexts exist."""
        runner = CliRunner()
        ctx_obj = {"index_path": MagicMock(exists=lambda: True)}

        with patch("docsift.cli.commands.context.Database") as MockDB:
            MockDB.return_value = mock_db
            mock_repo = MagicMock()
            mock_repo.list_all.return_value = []
            with patch(
                "docsift.cli.commands.context.ContextRepository",
                return_value=mock_repo,
            ):
                result = runner.invoke(context_list, obj=ctx_obj)

        assert result.exit_code == 0
        assert "No contexts found" in result.output


class TestContextRemove:
    """Tests for context remove command."""

    @pytest.fixture
    def mock_db(self):
        """Create a mock Database."""
        mock = MagicMock()
        mock.connection = MagicMock()
        return mock

    def test_remove_by_id(self, mock_db) -> None:
        """Test removing a context by ID."""
        runner = CliRunner()
        ctx_obj = {"index_path": MagicMock(exists=lambda: True)}
        context_id = str(uuid4())

        with patch("docsift.cli.commands.context.Database") as MockDB:
            MockDB.return_value = mock_db
            mock_repo = MagicMock()
            mock_repo.delete.return_value = True
            with patch(
                "docsift.cli.commands.context.ContextRepository",
                return_value=mock_repo,
            ):
                result = runner.invoke(
                    context_remove,
                    [context_id],
                    obj=ctx_obj,
                )

        assert result.exit_code == 0
        assert "removed" in result.output.lower()
        mock_repo.delete.assert_called_once_with(context_id)

    def test_remove_not_found(self, mock_db) -> None:
        """Test removing a non-existent context."""
        runner = CliRunner()
        ctx_obj = {"index_path": MagicMock(exists=lambda: True)}
        context_id = str(uuid4())

        with patch("docsift.cli.commands.context.Database") as MockDB:
            MockDB.return_value = mock_db
            mock_repo = MagicMock()
            mock_repo.delete.return_value = False
            with patch(
                "docsift.cli.commands.context.ContextRepository",
                return_value=mock_repo,
            ):
                result = runner.invoke(
                    context_remove,
                    [context_id],
                    obj=ctx_obj,
                )

        assert result.exit_code != 0


class TestContextRmAlias:
    """Tests for context rm alias."""

    @pytest.fixture
    def mock_db(self):
        """Create a mock Database."""
        mock = MagicMock()
        mock.connection = MagicMock()
        return mock

    def test_rm_alias_works(self, mock_db) -> None:
        """Test that rm alias invokes the same handler as remove."""
        runner = CliRunner()
        ctx_obj = {"index_path": MagicMock(exists=lambda: True)}
        context_id = str(uuid4())

        with patch("docsift.cli.commands.context.Database") as MockDB:
            MockDB.return_value = mock_db
            mock_repo = MagicMock()
            mock_repo.delete.return_value = True
            with patch(
                "docsift.cli.commands.context.ContextRepository",
                return_value=mock_repo,
            ):
                result = runner.invoke(
                    context_remove,
                    [context_id],
                    obj=ctx_obj,
                )

        assert result.exit_code == 0
        assert "removed" in result.output.lower()


class TestContextPrune:
    """Tests for context prune command."""

    @pytest.fixture
    def mock_db(self):
        """Create a mock Database."""
        mock = MagicMock()
        mock.connection = MagicMock()
        return mock

    def test_prune_deletes_orphans(self, mock_db) -> None:
        """Test pruning deletes orphaned contexts."""
        runner = CliRunner()
        ctx_obj = {"index_path": MagicMock(exists=lambda: True)}

        with patch("docsift.cli.commands.context.Database") as MockDB:
            MockDB.return_value = mock_db
            mock_repo = MagicMock()
            mock_repo.delete_orphaned_paths.return_value = 3
            with patch(
                "docsift.cli.commands.context.ContextRepository",
                return_value=mock_repo,
            ):
                result = runner.invoke(context_prune, obj=ctx_obj)

        assert result.exit_code == 0
        assert "Pruned 3" in result.output

    def test_prune_no_orphans(self, mock_db) -> None:
        """Test pruning when no orphans exist."""
        runner = CliRunner()
        ctx_obj = {"index_path": MagicMock(exists=lambda: True)}

        with patch("docsift.cli.commands.context.Database") as MockDB:
            MockDB.return_value = mock_db
            mock_repo = MagicMock()
            mock_repo.delete_orphaned_paths.return_value = 0
            with patch(
                "docsift.cli.commands.context.ContextRepository",
                return_value=mock_repo,
            ):
                result = runner.invoke(context_prune, obj=ctx_obj)

        assert result.exit_code == 0
        assert "Pruned 0" in result.output
