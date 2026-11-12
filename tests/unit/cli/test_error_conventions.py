"""Contract tests for the shared CLI DB error boundary (Phase 16.1, D-02..D-04).

Pins the helper contract: the caller-supplied Database class is the one
constructed (every command module's test patch seam keeps intercepting),
foreseeable failures become remedy-bearing ClickExceptions, unexpected
exceptions propagate unchanged, and every path closes the handle. End-to-end
legs prove ``sif index update`` / ``sif index embed`` render a real schema
failure as a clean exit-1 Click error with no traceback (11-WR-03).
"""

import sqlite3
from collections.abc import Generator
from pathlib import Path
from typing import ClassVar
from unittest.mock import patch

import click
import pytest
from click.testing import CliRunner

from sif.cli.commands.index import embed_cmd, update_cmd
from sif.cli.error_handling import (
    open_initialized_database,
    open_initialized_database_unmanaged,
    sqlite_vec_remedy,
)
from sif.config.settings import get_settings
from sif.database.database import Database


class TrackingDatabase(Database):
    """Database double recording constructed instances for closure assertions."""

    created: ClassVar[list[Database]] = []

    def __init__(self, db_path: str | Path) -> None:
        """Record each construction so tests can assert every handle closed."""
        super().__init__(db_path)
        TrackingDatabase.created.append(self)


def _schema_failure_cls(error: Exception) -> type[TrackingDatabase]:
    """Build a TrackingDatabase whose init_schema opens a real handle, then fails."""

    class SchemaFailureDatabase(TrackingDatabase):
        def init_schema(self) -> None:
            _ = self.connection  # open a real handle so closure is observable
            raise error

    return SchemaFailureDatabase


@pytest.fixture(autouse=True)
def _isolated_settings() -> Generator[None, None, None]:
    """Database schema creation never inherits cached Settings; reset the tracker."""
    get_settings.cache_clear()
    TrackingDatabase.created.clear()
    yield
    get_settings.cache_clear()


def _assert_all_closed() -> None:
    """Every handle the boundary constructed is closed, on success and failure."""
    for instance in TrackingDatabase.created:
        assert instance._connection is None


class TestOpenInitializedDatabase:
    """The context-manager variant: construction, schema init, translation, closure."""

    def test_constructs_the_supplied_class(self, tmp_path: Path) -> None:
        """The helper constructs the caller's class, never its own import (Pitfall 1)."""
        db_path = tmp_path / "sif.db"
        with open_initialized_database(db_path, TrackingDatabase) as db:
            assert isinstance(db, TrackingDatabase)
            assert db._schema is not None  # init_schema ran inside the boundary
        assert TrackingDatabase.created == [db]
        _assert_all_closed()

    def test_success_closes_handle_on_scope_exit(self, tmp_path: Path) -> None:
        """The yielded handle is open inside the scope and closed after it."""
        db_path = tmp_path / "sif.db"
        with open_initialized_database(db_path, TrackingDatabase) as db:
            assert db._connection is not None
        assert db._connection is None

    def test_constructor_oserror_becomes_click_exception(self, tmp_path: Path) -> None:
        """A parent path that is a file fails mkdir inside the boundary (Pitfall 2)."""
        blocker = tmp_path / "blocker"
        blocker.write_text("not a directory", encoding="utf-8")
        db_path = blocker / "sif.db"
        with pytest.raises(click.ClickException) as excinfo:
            with open_initialized_database(db_path, TrackingDatabase):
                pass
        message = excinfo.value.message
        assert str(db_path) in message
        assert "permissions" in message
        assert "disk" in message
        assert "corrupted" in message
        _assert_all_closed()

    @pytest.mark.parametrize(
        "error",
        [
            sqlite3.OperationalError("database disk image is malformed"),
            sqlite3.DatabaseError("file is not a database"),
            OSError("Permission denied"),
        ],
        ids=["sqlite-operational", "sqlite-database", "oserror"],
    )
    def test_init_schema_known_errors_become_click_exception(
        self, tmp_path: Path, error: Exception
    ) -> None:
        """sqlite3.Error and OSError at schema init translate with the D-03 remedy."""
        db_path = tmp_path / "sif.db"
        with pytest.raises(click.ClickException) as excinfo:
            with open_initialized_database(db_path, _schema_failure_cls(error)):
                pass
        message = excinfo.value.message
        assert str(db_path) in message
        assert "permissions" in message
        assert "disk" in message
        assert "corrupted" in message
        assert TrackingDatabase.created  # the double was constructed through the seam
        _assert_all_closed()

    def test_init_schema_value_error_propagates_and_closes(self, tmp_path: Path) -> None:
        """Unexpected exceptions keep their class and traceback (D-04)."""
        db_path = tmp_path / "sif.db"
        with pytest.raises(ValueError, match="unexpected bug"):
            with open_initialized_database(
                db_path, _schema_failure_cls(ValueError("unexpected bug"))
            ):
                pass
        _assert_all_closed()

    def test_command_body_errors_are_not_translated(self, tmp_path: Path) -> None:
        """The yield sits outside the known-exception handlers (D-04, Pitfall 3)."""
        db_path = tmp_path / "sif.db"
        with pytest.raises(sqlite3.OperationalError, match="later body failure"):
            with open_initialized_database(db_path, TrackingDatabase):
                raise sqlite3.OperationalError("later body failure")
        _assert_all_closed()


class TestOpenInitializedDatabaseUnmanaged:
    """The non-CM core (daemon arm() shape): caller owns close, same translation."""

    def test_returns_open_initialized_db(self, tmp_path: Path) -> None:
        """The unmanaged variant returns an initialized, open handle to the caller."""
        db_path = tmp_path / "sif.db"
        db = open_initialized_database_unmanaged(db_path, TrackingDatabase)
        try:
            assert isinstance(db, TrackingDatabase)
            assert db._schema is not None
            assert db._connection is not None
        finally:
            db.close()
        _assert_all_closed()

    def test_known_error_translates_and_closes(self, tmp_path: Path) -> None:
        """Schema-init failure translates and closes before the caller sees it."""
        db_path = tmp_path / "sif.db"
        error = sqlite3.OperationalError("database disk image is malformed")
        with pytest.raises(click.ClickException) as excinfo:
            open_initialized_database_unmanaged(db_path, _schema_failure_cls(error))
        assert str(db_path) in excinfo.value.message
        assert "permissions" in excinfo.value.message
        _assert_all_closed()

    def test_value_error_propagates_and_closes(self, tmp_path: Path) -> None:
        """An unexpected schema-init error propagates unchanged with the handle closed."""
        db_path = tmp_path / "sif.db"
        with pytest.raises(ValueError, match="unexpected bug"):
            open_initialized_database_unmanaged(
                db_path, _schema_failure_cls(ValueError("unexpected bug"))
            )
        _assert_all_closed()


class TestSqliteVecRemedy:
    """The sqlite-vec remedy builder keeps the cause and adds the install hint."""

    def test_appends_install_remedy(self) -> None:
        error = RuntimeError(
            "sqlite-vec extension is not available. Install sqlite-vec to use vector search."
        )
        message = sqlite_vec_remedy(error)
        assert str(error) in message
        assert "pip install sqlite-vec" in message


class TestIndexCommandsEndToEnd:
    """11-WR-03: real CLI invocations render schema failure as a clean Click error."""

    @pytest.mark.parametrize("command", [update_cmd, embed_cmd], ids=["update", "embed"])
    def test_schema_failure_exits_1_with_remedy(
        self, tmp_path: Path, command: click.Command
    ) -> None:
        """A failing init_schema exits 1 with Error: + remedy text and no traceback."""
        db_path = tmp_path / "sif.db"
        error = sqlite3.OperationalError("database disk image is malformed")
        with patch("sif.cli.commands.index.Database", _schema_failure_cls(error)):
            result = CliRunner().invoke(command, [], obj={"index_path": db_path})
        assert result.exit_code == 1
        assert "Error:" in result.output
        assert str(db_path) in result.output
        assert "permissions" in result.output
        assert "disk" in result.output
        assert "corrupted" in result.output
        assert "Traceback" not in result.output
        assert not isinstance(result.exception, sqlite3.Error)
        _assert_all_closed()
