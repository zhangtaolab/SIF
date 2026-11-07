"""Tests for collection update-cmd and index pre-update hook."""

import contextlib
import sqlite3
import subprocess
from collections.abc import Generator
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner, Result

from sif.cli.commands.collection import (
    collection_exclude,
    collection_include,
    collection_update_cmd,
)
from sif.cli.commands.index import update_cmd
from sif.cli.main import cli
from sif.config.settings import get_settings
from sif.core.models import Collection
from sif.database.database import Database
from sif.database.repositories import CollectionRepository


class TestCollectionRealDatabase:
    """Exercise collection commands through Click, repositories, and real SQLite."""

    @pytest.fixture(autouse=True)
    def isolated_settings(self) -> Generator[None, None, None]:
        """Database initialization must not inherit another test's settings."""
        get_settings.cache_clear()
        yield
        get_settings.cache_clear()

    @pytest.fixture
    def notes_dir(self, tmp_path: Path) -> Path:
        """A real collection directory with one nested Markdown document."""
        notes = tmp_path / "notes"
        (notes / "projects").mkdir(parents=True)
        (notes / "projects" / "roadmap.md").write_text("# Roadmap\n", encoding="utf-8")
        return notes

    def _invoke(self, db_path: Path, *args: str, stdin: str | None = None) -> Result:
        """Invoke the top-level CLI with every database confined to tmp_path."""
        return CliRunner().invoke(
            cli,
            ["--index", str(db_path), "collection", *args],
            input=stdin,
            env={"COLUMNS": "200"},
        )

    def _seed(self, db_path: Path, name: str, path: Path) -> None:
        """Seed a collection using production DDL and repository code."""
        db = Database(db_path)
        db.init_schema()
        with db.transaction() as conn:
            CollectionRepository(conn).create(Collection(name=name, path=str(path)))
        db.close()

    def _read_collection(self, db_path: Path, name: str) -> sqlite3.Row | None:
        """Read persisted state independently of the command's repository instance."""
        with contextlib.closing(sqlite3.connect(db_path)) as conn:
            conn.row_factory = sqlite3.Row
            return conn.execute("SELECT * FROM collections WHERE name = ?", (name,)).fetchone()

    def test_add_list_show_and_repository_state(self, tmp_path: Path, notes_dir: Path) -> None:
        """A collection added through the CLI persists and is visible to readers."""
        db_path = tmp_path / "sif.db"

        added = self._invoke(
            db_path,
            "add",
            str(notes_dir),
            "--name",
            "notes",
            "--ignore",
            "drafts/**",
            "--description",
            "Personal notes",
        )
        listed = self._invoke(db_path, "list")
        shown = self._invoke(db_path, "show", "notes")
        row = self._read_collection(db_path, "notes")

        assert added.exit_code == 0, added.output
        assert listed.exit_code == 0, listed.output
        assert shown.exit_code == 0, shown.output
        assert "added successfully" in added.output
        assert "notes" in listed.output
        assert "Personal notes" in shown.output
        assert "Ignore Patterns: drafts/**" in shown.output
        assert row is not None
        assert row["path"] == str(notes_dir.resolve())

    def test_add_duplicate_fails_without_changing_row(
        self, tmp_path: Path, notes_dir: Path
    ) -> None:
        """Duplicate names report an error rather than replacing state."""
        db_path = tmp_path / "sif.db"
        self._seed(db_path, "notes", notes_dir)

        result = self._invoke(db_path, "add", str(notes_dir), "--name", "notes")

        assert result.exit_code != 0
        assert "Collection 'notes' already exists" in result.stderr
        assert self._read_collection(db_path, "notes")["description"] is None

    def test_remove_and_missing_remove(self, tmp_path: Path, notes_dir: Path) -> None:
        """Confirmed removal deletes the real row; missing names fail clearly."""
        db_path = tmp_path / "sif.db"
        self._seed(db_path, "notes", notes_dir)

        removed = self._invoke(db_path, "remove", "notes", stdin="y\n")
        missing = self._invoke(db_path, "remove", "notes", stdin="y\n")

        assert removed.exit_code == 0, removed.output
        assert "Collection 'notes' removed" in removed.output
        assert self._read_collection(db_path, "notes") is None
        assert missing.exit_code != 0
        assert "Collection 'notes' not found" in missing.stderr

    def test_rename_missing_and_duplicate(self, tmp_path: Path, notes_dir: Path) -> None:
        """Rename enforces both source existence and destination uniqueness."""
        db_path = tmp_path / "sif.db"
        self._seed(db_path, "notes", notes_dir)
        with Database(db_path) as db, db.transaction() as conn:
            CollectionRepository(conn).create(Collection(name="archive", path=str(notes_dir)))

        renamed = self._invoke(db_path, "rename", "notes", "journal")
        missing = self._invoke(db_path, "rename", "missing", "other")
        duplicate = self._invoke(db_path, "rename", "journal", "archive")

        assert renamed.exit_code == 0, renamed.output
        assert self._read_collection(db_path, "journal") is not None
        assert self._read_collection(db_path, "notes") is None
        assert missing.exit_code != 0
        assert "Collection 'missing' not found" in missing.stderr
        assert duplicate.exit_code != 0
        assert "Collection 'archive' already exists" in duplicate.stderr

    def test_enable_disable_include_and_exclude(self, tmp_path: Path, notes_dir: Path) -> None:
        """All four switches persist their default-search state."""
        db_path = tmp_path / "sif.db"
        self._seed(db_path, "notes", notes_dir)

        disabled = self._invoke(db_path, "disable", "notes")
        assert self._read_collection(db_path, "notes")["include_by_default"] == 0
        enabled = self._invoke(db_path, "enable", "notes")
        assert self._read_collection(db_path, "notes")["include_by_default"] == 1
        excluded = self._invoke(db_path, "exclude", "notes")
        assert self._read_collection(db_path, "notes")["include_by_default"] == 0
        included = self._invoke(db_path, "include", "notes")

        results = [disabled, enabled, excluded, included]
        assert all(result.exit_code == 0 for result in results)
        assert [result.output for result in results] == [
            "Collection 'notes' disabled\n",
            "Collection 'notes' enabled\n",
            "Collection 'notes' excluded from default searches\n",
            "Collection 'notes' included in default searches\n",
        ]
        assert self._read_collection(db_path, "notes")["include_by_default"] == 1

    def test_enable_and_include_missing(self, tmp_path: Path, notes_dir: Path) -> None:
        """Missing names are errors for both default-search enable operations."""
        db_path = tmp_path / "sif.db"
        self._seed(db_path, "other", notes_dir)

        enable = self._invoke(db_path, "enable", "missing")
        include = self._invoke(db_path, "include", "missing")

        assert enable.exit_code != 0
        assert "Collection 'missing' not found" in enable.stderr
        assert include.exit_code != 0
        assert "Collection 'missing' not found" in include.stderr

    def test_update_cmd_set_clear_and_validation(self, tmp_path: Path, notes_dir: Path) -> None:
        """The pre-update hook supports real set/clear writes and rejects no-op input."""
        db_path = tmp_path / "sif.db"
        self._seed(db_path, "notes", notes_dir)

        set_result = self._invoke(db_path, "update-cmd", "notes", "--cmd", "git pull")
        clear_result = self._invoke(db_path, "update-cmd", "notes", "--clear")
        missing = self._invoke(db_path, "update-cmd", "missing", "--cmd", "git pull")
        no_options = self._invoke(db_path, "update-cmd", "notes")

        assert set_result.exit_code == 0, set_result.output
        assert clear_result.exit_code == 0, clear_result.output
        assert self._read_collection(db_path, "notes")["pre_update_cmd"] is None
        assert missing.exit_code != 0
        assert "Collection 'missing' not found" in missing.stderr
        assert no_options.exit_code != 0
        assert "Provide --cmd or --clear" in no_options.stderr

    def test_exclude_missing(self, tmp_path: Path, notes_dir: Path) -> None:
        """Excluding an absent collection is an error, not a silent no-op."""
        db_path = tmp_path / "sif.db"
        self._seed(db_path, "other", notes_dir)

        result = self._invoke(db_path, "exclude", "missing")

        assert result.exit_code != 0
        assert "Collection 'missing' not found" in result.stderr

    def test_ls_with_subpath_and_without_files(self, tmp_path: Path, notes_dir: Path) -> None:
        """File listing accepts a subpath and handles an empty collection."""
        db_path = tmp_path / "sif.db"
        self._seed(db_path, "notes", notes_dir)
        with Database(db_path) as db, db.transaction() as conn:
            CollectionRepository(conn).create(
                Collection(name="empty", path=str(tmp_path / "empty"))
            )

        listed = self._invoke(db_path, "ls", "notes", "projects")
        empty = self._invoke(db_path, "ls", "empty")

        assert listed.exit_code == 0, listed.output
        assert "projects/roadmap.md" in listed.output
        assert empty.exit_code == 0, empty.output
        assert "No files found in collection." in empty.output

    def test_list_missing_empty_and_verbose(self, tmp_path: Path, notes_dir: Path) -> None:
        """List handles absent and empty indexes plus verbose collection details."""
        db_path = tmp_path / "sif.db"

        missing = self._invoke(tmp_path / "absent.db", "list")
        self._seed(db_path, "notes", notes_dir)
        with Database(db_path) as db, db.transaction() as conn:
            CollectionRepository(conn).delete(CollectionRepository(conn).get_by_name("notes").id)
        empty = self._invoke(db_path, "list")
        with Database(db_path) as db, db.transaction() as conn:
            CollectionRepository(conn).create(
                Collection(
                    name="notes",
                    path=str(notes_dir),
                    description="Personal notes",
                    document_count=2,
                    chunk_count=4,
                )
            )
        verbose = self._invoke(db_path, "list", "--verbose")

        assert missing.exit_code == 0, missing.output
        assert "No index found." in missing.output
        assert empty.exit_code == 0, empty.output
        assert "No collections found." in empty.output
        assert verbose.exit_code == 0, verbose.output
        assert "Documents: 2" in verbose.output
        assert "Chunks: 4" in verbose.output
        assert "Description: Personal notes" in verbose.output

    def test_show_and_ls_missing(self, tmp_path: Path, notes_dir: Path) -> None:
        """Read-side commands surface missing collection errors."""
        db_path = tmp_path / "sif.db"
        self._seed(db_path, "other", notes_dir)

        shown = self._invoke(db_path, "show", "missing")
        listed = self._invoke(db_path, "ls", "missing")

        assert shown.exit_code != 0
        assert "Collection 'missing' not found" in shown.stderr
        assert listed.exit_code != 0
        assert "Collection 'missing' not found" in listed.stderr


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

    def test_index_update_runs_pre_update_cmd(self, tmp_path):
        """Test that index update runs pre-update command."""
        runner = CliRunner()
        collection = Collection(name="notes", path="/tmp/notes", pre_update_cmd="echo hello")

        mock_db = MagicMock()
        mock_db.return_value.connection.__enter__ = MagicMock(
            return_value=mock_db.return_value.connection,
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
                obj={"index_path": tmp_path / "sif.db"},
            )

        assert result.exit_code == 0
        mock_run.assert_called_once_with(
            "echo hello",
            shell=True,
            capture_output=True,
            text=True,
            check=False,
            timeout=300,
            stdin=subprocess.DEVNULL,
        )
        assert "Running pre-update command" in result.output

    def test_index_update_times_out_hung_pre_update_cmd(self, tmp_path):
        """WR-06: a hung pre-update command exits with a ClickException, not a hang."""
        runner = CliRunner()
        collection = Collection(name="notes", path="/tmp/notes", pre_update_cmd="sleep 9999")

        mock_db = MagicMock()
        mock_db.return_value.connection.__enter__ = MagicMock(
            return_value=mock_db.return_value.connection,
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
                side_effect=subprocess.TimeoutExpired(cmd="sleep 9999", timeout=300),
            ),
        ):
            result = runner.invoke(
                update_cmd,
                ["--collection", "notes"],
                obj={"index_path": tmp_path / "sif.db"},
            )

        assert result.exit_code != 0
        assert "timed out after 300s" in result.output

    def test_index_update_fails_fast_on_pre_update_cmd_error(self, tmp_path):
        """Test that index update fails fast on pre-update command error."""
        runner = CliRunner()
        collection = Collection(name="notes", path="/tmp/notes", pre_update_cmd="echo hello")

        mock_db = MagicMock()
        mock_db.return_value.connection.__enter__ = MagicMock(
            return_value=mock_db.return_value.connection,
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
                obj={"index_path": tmp_path / "sif.db"},
            )

        assert result.exit_code != 0
        assert "Pre-update command failed" in result.output
