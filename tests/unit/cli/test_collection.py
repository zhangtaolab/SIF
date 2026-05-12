"""Tests for collection update-cmd and index pre-update hook."""

from unittest.mock import MagicMock, patch

from click.testing import CliRunner

from sif.cli.commands.collection import (
    collection_exclude,
    collection_include,
    collection_update_cmd,
)
from sif.cli.commands.index import update_cmd
from sif.core.models import Collection


class TestCollectionUpdateCmd:
    """Tests for collection update-cmd command."""

    def test_collection_update_cmd_set(self):
        """Test setting pre-update command on a collection."""
        runner = CliRunner()
        collection = Collection(name="notes", path="/tmp/notes")

        mock_db = MagicMock()
        mock_conn = MagicMock()
        mock_db.return_value.transaction.return_value.__enter__ = MagicMock(return_value=mock_conn)
        mock_db.return_value.transaction.return_value.__exit__ = MagicMock(return_value=False)
        mock_db.return_value.init_schema = MagicMock()

        mock_repo = MagicMock()
        mock_repo.get_by_name.return_value = collection

        with (
            patch("sif.cli.commands.collection.Database", mock_db),
            patch(
                "sif.cli.commands.collection.CollectionRepository",
                return_value=mock_repo,
            ),
        ):
            result = runner.invoke(
                collection_update_cmd,
                ["notes", "--cmd", "git pull"],
                obj={"index_path": MagicMock()},
            )

        assert result.exit_code == 0
        assert "Set pre-update command" in result.output
        assert collection.pre_update_cmd == "git pull"
        mock_repo.update.assert_called_once_with(collection)

    def test_collection_update_cmd_clear(self):
        """Test clearing pre-update command on a collection."""
        runner = CliRunner()
        collection = Collection(name="notes", path="/tmp/notes", pre_update_cmd="git pull")

        mock_db = MagicMock()
        mock_conn = MagicMock()
        mock_db.return_value.transaction.return_value.__enter__ = MagicMock(return_value=mock_conn)
        mock_db.return_value.transaction.return_value.__exit__ = MagicMock(return_value=False)
        mock_db.return_value.init_schema = MagicMock()

        mock_repo = MagicMock()
        mock_repo.get_by_name.return_value = collection

        with (
            patch("sif.cli.commands.collection.Database", mock_db),
            patch(
                "sif.cli.commands.collection.CollectionRepository",
                return_value=mock_repo,
            ),
        ):
            result = runner.invoke(
                collection_update_cmd,
                ["notes", "--clear"],
                obj={"index_path": MagicMock()},
            )

        assert result.exit_code == 0
        assert "Cleared pre-update command" in result.output
        assert collection.pre_update_cmd is None
        mock_repo.update.assert_called_once_with(collection)

    def test_collection_update_cmd_missing_collection(self):
        """Test update-cmd on a missing collection."""
        runner = CliRunner()

        mock_db = MagicMock()
        mock_conn = MagicMock()
        mock_db.return_value.transaction.return_value.__enter__ = MagicMock(return_value=mock_conn)
        mock_db.return_value.transaction.return_value.__exit__ = MagicMock(return_value=False)
        mock_db.return_value.init_schema = MagicMock()

        mock_repo = MagicMock()
        mock_repo.get_by_name.return_value = None

        with (
            patch("sif.cli.commands.collection.Database", mock_db),
            patch(
                "sif.cli.commands.collection.CollectionRepository",
                return_value=mock_repo,
            ),
        ):
            result = runner.invoke(
                collection_update_cmd,
                ["missing", "--cmd", "git pull"],
                obj={"index_path": MagicMock()},
            )

        assert result.exit_code != 0
        assert "not found" in result.output


class TestCollectionIncludeExclude:
    """Tests for collection include/exclude commands."""

    def test_collection_include(self):
        """Test including a collection in default searches."""
        runner = CliRunner()
        collection = Collection(name="notes", path="/tmp/notes", include_by_default=False)

        mock_db = MagicMock()
        mock_conn = MagicMock()
        mock_db.return_value.transaction.return_value.__enter__ = MagicMock(return_value=mock_conn)
        mock_db.return_value.transaction.return_value.__exit__ = MagicMock(return_value=False)
        mock_db.return_value.init_schema = MagicMock()

        mock_repo = MagicMock()
        mock_repo.get_by_name.return_value = collection

        with (
            patch("sif.cli.commands.collection.Database", mock_db),
            patch(
                "sif.cli.commands.collection.CollectionRepository",
                return_value=mock_repo,
            ),
        ):
            result = runner.invoke(collection_include, ["notes"], obj={"index_path": MagicMock()})

        assert result.exit_code == 0
        assert collection.include_by_default is True
        assert "included" in result.output
        mock_repo.update.assert_called_once_with(collection)

    def test_collection_exclude(self):
        """Test excluding a collection from default searches."""
        runner = CliRunner()
        collection = Collection(name="notes", path="/tmp/notes", include_by_default=True)

        mock_db = MagicMock()
        mock_conn = MagicMock()
        mock_db.return_value.transaction.return_value.__enter__ = MagicMock(return_value=mock_conn)
        mock_db.return_value.transaction.return_value.__exit__ = MagicMock(return_value=False)
        mock_db.return_value.init_schema = MagicMock()

        mock_repo = MagicMock()
        mock_repo.get_by_name.return_value = collection

        with (
            patch("sif.cli.commands.collection.Database", mock_db),
            patch(
                "sif.cli.commands.collection.CollectionRepository",
                return_value=mock_repo,
            ),
        ):
            result = runner.invoke(collection_exclude, ["notes"], obj={"index_path": MagicMock()})

        assert result.exit_code == 0
        assert collection.include_by_default is False
        assert "excluded" in result.output
        mock_repo.update.assert_called_once_with(collection)


class TestIndexPreUpdateHook:
    """Tests for index update pre-update command hook."""

    def test_index_update_runs_pre_update_cmd(self):
        """Test that index update runs pre-update command."""
        runner = CliRunner()
        collection = Collection(name="notes", path="/tmp/notes", pre_update_cmd="echo hello")

        mock_db = MagicMock()
        mock_db.return_value.connection.__enter__ = MagicMock(
            return_value=mock_db.return_value.connection
        )
        mock_db.return_value.connection.__exit__ = MagicMock(return_value=False)
        mock_db.return_value.init_schema = MagicMock()

        mock_coll_repo = MagicMock()
        mock_coll_repo.get_by_name.return_value = collection

        mock_doc_repo = MagicMock()
        mock_doc_repo.list_by_collection.return_value = []

        mock_scanner = MagicMock()
        mock_scanner.return_value.scan.return_value = MagicMock(file_count=0, files=[])

        with (
            patch("sif.cli.commands.index.Database", mock_db),
            patch(
                "sif.cli.commands.index.CollectionRepository",
                return_value=mock_coll_repo,
            ),
            patch(
                "sif.cli.commands.index.DocumentRepository",
                return_value=mock_doc_repo,
            ),
            patch("sif.cli.commands.index.FileScanner", mock_scanner),
            patch(
                "subprocess.run",
                return_value=MagicMock(returncode=0, stderr="", stdout=""),
            ) as mock_run,
        ):
            result = runner.invoke(
                update_cmd,
                ["--collection", "notes"],
                obj={"index_path": MagicMock()},
            )

        assert result.exit_code == 0
        mock_run.assert_called_once_with(
            "echo hello", shell=True, capture_output=True, text=True, check=False
        )
        assert "Running pre-update command" in result.output

    def test_index_update_fails_fast_on_pre_update_cmd_error(self):
        """Test that index update fails fast on pre-update command error."""
        runner = CliRunner()
        collection = Collection(name="notes", path="/tmp/notes", pre_update_cmd="echo hello")

        mock_db = MagicMock()
        mock_db.return_value.connection.__enter__ = MagicMock(
            return_value=mock_db.return_value.connection
        )
        mock_db.return_value.connection.__exit__ = MagicMock(return_value=False)
        mock_db.return_value.init_schema = MagicMock()

        mock_coll_repo = MagicMock()
        mock_coll_repo.get_by_name.return_value = collection

        mock_doc_repo = MagicMock()

        mock_scanner = MagicMock()

        with (
            patch("sif.cli.commands.index.Database", mock_db),
            patch(
                "sif.cli.commands.index.CollectionRepository",
                return_value=mock_coll_repo,
            ),
            patch(
                "sif.cli.commands.index.DocumentRepository",
                return_value=mock_doc_repo,
            ),
            patch("sif.cli.commands.index.FileScanner", mock_scanner),
            patch(
                "subprocess.run",
                return_value=MagicMock(returncode=1, stderr="failed", stdout=""),
            ),
        ):
            result = runner.invoke(
                update_cmd,
                ["--collection", "notes"],
                obj={"index_path": MagicMock()},
            )

        assert result.exit_code != 0
        assert "Pre-update command failed" in result.output
