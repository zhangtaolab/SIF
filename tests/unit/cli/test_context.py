"""Tests for context CLI commands."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest
from click.testing import CliRunner

from sif.cli.commands.context import (
    context_add,
    context_group,
    context_list,
    context_prune,
    context_remove,
)
from sif.core.models import Collection, PathContext
from sif.utils.paths import normalize_path


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

        with patch("sif.cli.commands.context.Database") as mock_db_cls:
            mock_db_cls.return_value = mock_db
            mock_repo = MagicMock()
            mock_repo.get_by_target.return_value = None
            with patch(
                "sif.cli.commands.context.ContextRepository",
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
        with patch("sif.cli.commands.context.Database") as mock_db_cls:
            mock_db_cls.return_value = mock_db
            mock_coll_repo = MagicMock()
            mock_coll_repo.get_by_name.return_value = coll
            mock_ctx_repo = MagicMock()
            mock_ctx_repo.get_by_target.return_value = None
            with (
                patch(
                    "sif.cli.commands.context.CollectionRepository",
                    return_value=mock_coll_repo,
                ),
                patch(
                    "sif.cli.commands.context.ContextRepository",
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
        with patch("sif.cli.commands.context.Database") as mock_db_cls:
            mock_db_cls.return_value = mock_db
            mock_coll_repo = MagicMock()
            mock_coll_repo.get_by_name.return_value = None
            mock_coll_repo.get_by_id.return_value = coll
            mock_ctx_repo = MagicMock()
            mock_ctx_repo.get_by_target.return_value = None
            with (
                patch(
                    "sif.cli.commands.context.CollectionRepository",
                    return_value=mock_coll_repo,
                ),
                patch(
                    "sif.cli.commands.context.ContextRepository",
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

        with patch("sif.cli.commands.context.Database") as mock_db_cls:
            mock_db_cls.return_value = mock_db
            mock_coll_repo = MagicMock()
            mock_coll_repo.get_by_name.return_value = None
            mock_coll_repo.get_by_id.return_value = None
            with patch(
                "sif.cli.commands.context.CollectionRepository",
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

        with patch("sif.cli.commands.context.Database") as mock_db_cls:
            mock_db_cls.return_value = mock_db
            mock_repo = MagicMock()
            mock_repo.get_by_target.return_value = None
            with patch(
                "sif.cli.commands.context.ContextRepository",
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
        with patch("sif.cli.commands.context.Database") as mock_db_cls:
            mock_db_cls.return_value = mock_db
            mock_repo = MagicMock()
            mock_repo.get_by_target.return_value = existing
            with patch(
                "sif.cli.commands.context.ContextRepository",
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


class TestContextAddNormalizedPaths:
    """Write-side normalization for path targets (05-09, REVIEW WR-02).

    ``context add path`` must store the canonical resolved form so new
    contexts byte-match ``documents.path``; re-adding a path whose legacy
    verbatim row already exists must merge (self-heal re-point) instead of
    duplicating; and collection/global targets must stay untouched by path
    normalization.
    """

    @pytest.fixture
    def mock_db(self):
        """Create a mock Database."""
        mock = MagicMock()
        mock.connection = MagicMock()
        return mock

    @pytest.fixture
    def alias_pair(self, tmp_path):
        """Create a real symlink alias over a vault directory.

        Returns ``(resolved_doc_path, alias_doc_path)`` — same construction
        as tests/unit/search/test_context_attach.py (plan 05-08). The two
        forms genuinely differ on platforms whose tmp dir is itself
        symlinked (macOS ``/private/tmp``).
        """
        vault = tmp_path / "vault"
        vault.mkdir()
        doc = vault / "doc.md"
        doc.write_text("# Doc\n", encoding="utf-8")
        alias_dir = tmp_path / "alias"
        alias_dir.symlink_to(vault)
        return str(doc), str(alias_dir / "doc.md")

    def test_add_path_symlink_alias_stores_resolved_form(self, mock_db, alias_pair) -> None:
        """A path added via a symlink alias is stored in resolved form."""
        _, alias = alias_pair
        canonical = normalize_path(alias)
        runner = CliRunner()
        ctx_obj = {"index_path": MagicMock(exists=lambda: True)}

        with patch("sif.cli.commands.context.Database") as mock_db_cls:
            mock_db_cls.return_value = mock_db
            mock_repo = MagicMock()
            mock_repo.get_by_target.return_value = None
            with patch(
                "sif.cli.commands.context.ContextRepository",
                return_value=mock_repo,
            ):
                result = runner.invoke(
                    context_add,
                    ["path", alias, "description"],
                    obj=ctx_obj,
                )

        assert result.exit_code == 0
        mock_repo.create.assert_called_once()
        stored = mock_repo.create.call_args[0][0]
        assert stored.path == canonical
        # rich wraps long paths across lines in captured output; compare the
        # newline-stripped rendering so the assertion is width-independent
        assert canonical in result.output.replace("\n", "")

    def test_add_path_home_relative_expands(self, mock_db) -> None:
        """A ~/-relative path target is stored expanded and absolute."""
        home_form = "~/sif-ctx-home-probe.md"
        canonical = normalize_path(home_form)
        runner = CliRunner()
        ctx_obj = {"index_path": MagicMock(exists=lambda: True)}

        with patch("sif.cli.commands.context.Database") as mock_db_cls:
            mock_db_cls.return_value = mock_db
            mock_repo = MagicMock()
            mock_repo.get_by_target.return_value = None
            with patch(
                "sif.cli.commands.context.ContextRepository",
                return_value=mock_repo,
            ):
                result = runner.invoke(
                    context_add,
                    ["path", home_form, "description"],
                    obj=ctx_obj,
                )

        assert result.exit_code == 0
        mock_repo.create.assert_called_once()
        stored = mock_repo.create.call_args[0][0]
        assert stored.path == canonical
        assert "~" not in stored.path
        assert Path(stored.path).is_absolute()

    def test_readd_legacy_verbatim_row_self_heals(self, mock_db, alias_pair) -> None:
        """Re-adding over a legacy verbatim row re-points it instead of duplicating.

        CTX-02 adjacency edge: the legacy row (stored verbatim before
        write-side normalization) is merged into one canonical row via
        update_target — create must never run.
        """
        _, alias = alias_pair
        canonical = normalize_path(alias)
        legacy = PathContext(path=alias, context="old text")
        runner = CliRunner()
        ctx_obj = {"index_path": MagicMock(exists=lambda: True)}

        with patch("sif.cli.commands.context.Database") as mock_db_cls:
            mock_db_cls.return_value = mock_db
            mock_repo = MagicMock()

            def lookup(target_id, _context_type="path"):
                return legacy if target_id == alias else None

            mock_repo.get_by_target.side_effect = lookup
            with patch(
                "sif.cli.commands.context.ContextRepository",
                return_value=mock_repo,
            ):
                result = runner.invoke(
                    context_add,
                    ["path", alias, "new text"],
                    obj=ctx_obj,
                )

        assert result.exit_code == 0
        mock_repo.update_target.assert_called_once_with(legacy.id, canonical)
        mock_repo.create.assert_not_called()
        mock_repo.update.assert_called_once()
        assert legacy.context == "new text"
        assert canonical in result.output.replace("\n", "")

    def test_readd_canonical_row_updates_without_repoint(self, mock_db, alias_pair) -> None:
        """Re-adding when the canonical row exists only refreshes content."""
        _, alias = alias_pair
        canonical = normalize_path(alias)
        existing = PathContext(path=canonical, context="old text")
        runner = CliRunner()
        ctx_obj = {"index_path": MagicMock(exists=lambda: True)}

        with patch("sif.cli.commands.context.Database") as mock_db_cls:
            mock_db_cls.return_value = mock_db
            mock_repo = MagicMock()

            def lookup(target_id, _context_type="path"):
                return existing if target_id == canonical else None

            mock_repo.get_by_target.side_effect = lookup
            with patch(
                "sif.cli.commands.context.ContextRepository",
                return_value=mock_repo,
            ):
                result = runner.invoke(
                    context_add,
                    ["path", alias, "new text"],
                    obj=ctx_obj,
                )

        assert result.exit_code == 0
        mock_repo.update.assert_called_once()
        mock_repo.update_target.assert_not_called()
        mock_repo.create.assert_not_called()

    def test_collection_and_global_targets_not_normalized(self, mock_db) -> None:
        """normalize_path is never applied to collection or global targets.

        Regression guard: collection still resolves name-first to the
        collection UUID (D-02) and global still stores the literal "global".
        """
        runner = CliRunner()
        ctx_obj = {"index_path": MagicMock(exists=lambda: True)}
        coll = Collection(name="my-coll", path="/notes")

        with (
            patch("sif.cli.commands.context.Database") as mock_db_cls,
            patch("sif.cli.commands.context.CollectionRepository") as mock_coll_cls,
            patch("sif.cli.commands.context.ContextRepository") as mock_ctx_cls,
            patch("sif.cli.commands.context.normalize_path", create=True) as mock_norm,
        ):
            mock_db_cls.return_value = mock_db
            mock_coll_cls.return_value.get_by_name.return_value = coll
            mock_ctx_repo = MagicMock()
            mock_ctx_repo.get_by_target.return_value = None
            mock_ctx_cls.return_value = mock_ctx_repo

            coll_result = runner.invoke(
                context_add,
                ["collection", "my-coll", "description"],
                obj=ctx_obj,
            )
            global_result = runner.invoke(
                context_add,
                ["global", "global", "description"],
                obj=ctx_obj,
            )

        assert coll_result.exit_code == 0
        assert global_result.exit_code == 0
        mock_norm.assert_not_called()
        coll_stored = mock_ctx_repo.create.call_args_list[0][0][0]
        assert coll_stored.path == coll.id
        assert coll_stored.context_type == "collection"
        global_stored = mock_ctx_repo.create.call_args_list[1][0][0]
        assert global_stored.path == "global"
        assert global_stored.context_type == "global"


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
        with patch("sif.cli.commands.context.Database") as mock_db_cls:
            mock_db_cls.return_value = mock_db
            mock_repo = MagicMock()
            mock_repo.list_all.return_value = contexts
            with patch(
                "sif.cli.commands.context.ContextRepository",
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
        with patch("sif.cli.commands.context.Database") as mock_db_cls:
            mock_db_cls.return_value = mock_db
            mock_repo = MagicMock()
            mock_repo.list_by_type.return_value = contexts
            with patch(
                "sif.cli.commands.context.ContextRepository",
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

        with patch("sif.cli.commands.context.Database") as mock_db_cls:
            mock_db_cls.return_value = mock_db
            mock_repo = MagicMock()
            mock_repo.list_all.return_value = []
            with patch(
                "sif.cli.commands.context.ContextRepository",
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

        with patch("sif.cli.commands.context.Database") as mock_db_cls:
            mock_db_cls.return_value = mock_db
            mock_repo = MagicMock()
            mock_repo.delete.return_value = True
            with patch(
                "sif.cli.commands.context.ContextRepository",
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

        with patch("sif.cli.commands.context.Database") as mock_db_cls:
            mock_db_cls.return_value = mock_db
            mock_repo = MagicMock()
            mock_repo.delete.return_value = False
            with patch(
                "sif.cli.commands.context.ContextRepository",
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

        with patch("sif.cli.commands.context.Database") as mock_db_cls:
            mock_db_cls.return_value = mock_db
            mock_repo = MagicMock()
            mock_repo.delete.return_value = True
            with patch(
                "sif.cli.commands.context.ContextRepository",
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

        with patch("sif.cli.commands.context.Database") as mock_db_cls:
            mock_db_cls.return_value = mock_db
            mock_repo = MagicMock()
            mock_repo.delete_orphaned_paths.return_value = 3
            with patch(
                "sif.cli.commands.context.ContextRepository",
                return_value=mock_repo,
            ):
                result = runner.invoke(context_prune, obj=ctx_obj)

        assert result.exit_code == 0
        assert "Pruned 3" in result.output

    def test_prune_no_orphans(self, mock_db) -> None:
        """Test pruning when no orphans exist."""
        runner = CliRunner()
        ctx_obj = {"index_path": MagicMock(exists=lambda: True)}

        with patch("sif.cli.commands.context.Database") as mock_db_cls:
            mock_db_cls.return_value = mock_db
            mock_repo = MagicMock()
            mock_repo.delete_orphaned_paths.return_value = 0
            with patch(
                "sif.cli.commands.context.ContextRepository",
                return_value=mock_repo,
            ):
                result = runner.invoke(context_prune, obj=ctx_obj)

        assert result.exit_code == 0
        assert "Pruned 0" in result.output
