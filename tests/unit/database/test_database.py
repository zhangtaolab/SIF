"""Real-SQL tests for the two Database connection styles."""

from __future__ import annotations

import sqlite3
from collections.abc import Generator
from pathlib import Path
from unittest.mock import patch

import pytest

from sif.config.settings import get_settings
from sif.database.database import Database, DatabaseConnection


@pytest.fixture(autouse=True)
def clear_settings_cache() -> Generator[None, None, None]:
    """Prevent Settings cache state from leaking between real database tests."""
    get_settings.cache_clear()
    try:
        yield
    finally:
        get_settings.cache_clear()


def _insert_then_raise(conn: sqlite3.Connection, error: Exception) -> None:
    """Insert one partial row, then trigger the transaction's error path."""
    conn.execute(
        "INSERT INTO collections (id, name, path, created_at, updated_at) "
        "VALUES ('rolled-back', 'rolled-back', '/rolled-back', 'now', 'now')",
    )
    raise error


def _insert_lightweight_probe_then_raise(conn: sqlite3.Connection) -> None:
    """Insert a lightweight probe row and raise inside its connection context."""
    conn.execute("INSERT INTO probe VALUES ('partial')")
    raise ValueError("lightweight rollback")


class TestDatabaseRealSQLite:
    """Connection, transaction, schema, extension, stats, and reset behavior."""

    def test_connection_reuse_close_and_context_manager(self, tmp_path: Path):
        """A Database reuses its live connection, then closes and can reconnect."""
        db_path = tmp_path / "nested" / "database.db"
        with Database(db_path) as database:
            assert database.db_path == db_path.resolve()
            first = database.connection
            assert database.connection is first
            assert first.row_factory is sqlite3.Row
            assert first.execute("PRAGMA foreign_keys").fetchone()[0] == 1
            first.execute("CREATE TABLE connection_probe (value TEXT)")
            first.execute("INSERT INTO connection_probe VALUES ('kept')")
            first.commit()

        assert database._connection is None
        with pytest.raises(sqlite3.ProgrammingError):
            first.execute("SELECT 1")
        second = database.connection
        assert second is not first
        assert second.execute("SELECT value FROM connection_probe").fetchone()[0] == "kept"
        database.close()
        database.close()

    def test_init_schema_commit_and_rollback(self, tmp_path: Path):
        """Successful writes persist while an exception removes the partial row."""
        database = Database(tmp_path / "transactions.db")
        try:
            database.init_schema()
            with database.transaction() as conn:
                conn.execute(
                    "INSERT INTO collections (id, name, path, created_at, updated_at) "
                    "VALUES ('committed', 'committed', '/committed', 'now', 'now')",
                )
            assert (
                database.connection.execute(
                    "SELECT name FROM collections WHERE id = 'committed'",
                ).fetchone()[0]
                == "committed"
            )

            with pytest.raises(RuntimeError, match="rollback probe"):
                with database.transaction() as conn:
                    _insert_then_raise(conn, RuntimeError("rollback probe"))

            assert (
                database.connection.execute(
                    "SELECT 1 FROM collections WHERE id = 'rolled-back'",
                ).fetchone()
                is None
            )
            assert (
                database.connection.execute(
                    "SELECT 1 FROM collections WHERE id = 'committed'",
                ).fetchone()
                is not None
            )
        finally:
            database.close()

    def test_get_stats_lazily_initializes_schema_and_reset_recreates_it(self, tmp_path: Path):
        """Stats initializes on demand; reset drops old rows and recreates usable tables."""
        database = Database(tmp_path / "stats.db")
        try:
            assert database._schema is None
            assert database.get_stats() == {
                "collections": 0,
                "documents": 0,
                "chunks": 0,
                "contexts": 0,
                "total_size_bytes": 0,
            }
            assert database._schema is not None
            with database.transaction() as conn:
                conn.execute(
                    "INSERT INTO collections (id, name, path, created_at, updated_at) "
                    "VALUES ('old', 'old', '/old', 'now', 'now')",
                )
            assert database.get_stats()["collections"] == 1

            database.reset()

            assert database.get_stats()["collections"] == 0
            assert (
                database.connection.execute(
                    "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'collections'",
                ).fetchone()
                is not None
            )
            with database.transaction() as conn:
                conn.execute(
                    "INSERT INTO collections (id, name, path, created_at, updated_at) "
                    "VALUES ('new', 'new', '/new', 'now', 'now')",
                )
            assert database.get_stats()["collections"] == 1
        finally:
            database.close()

    def test_reset_lazily_initializes_schema_before_recreating(self, tmp_path: Path):
        """Reset on a fresh Database creates its schema manager before dropping tables."""
        database = Database(tmp_path / "fresh-reset.db")
        try:
            assert database._schema is None
            database.reset()
            assert database._schema is not None
            assert database.get_stats()["collections"] == 0
            with database.transaction() as conn:
                conn.execute(
                    "INSERT INTO collections (id, name, path, created_at, updated_at) "
                    "VALUES ('after-reset', 'after-reset', '/after-reset', 'now', 'now')",
                )
            assert database.get_stats()["collections"] == 1
        finally:
            database.close()

    def test_optional_vector_failure_leaves_database_usable(self, tmp_path: Path):
        """Database catches sqlite-vec loader failure without disabling ordinary SQL."""
        database = Database(tmp_path / "no-vec.db")
        try:
            with patch("sif.database.factory.sqlite_vec.load", side_effect=OSError("no vec")):
                conn = database.connection
            assert conn.execute("SELECT 40 + 2").fetchone()[0] == 42
            assert conn.execute("PRAGMA foreign_keys").fetchone()[0] == 1
        finally:
            database.close()

    def test_lightweight_connection_optional_vector_failure_and_commit(self, tmp_path: Path):
        """DatabaseConnection remains usable without sqlite-vec and commits on clean exit."""
        connector = DatabaseConnection(tmp_path / "lightweight.db")
        with patch("sif.database.factory.sqlite_vec.load", side_effect=OSError("no vec")):
            with connector.connect() as conn:
                conn.execute("CREATE TABLE probe (value TEXT)")
                conn.execute("INSERT INTO probe VALUES ('committed')")

        with connector.connect() as conn:
            assert conn.execute("SELECT value FROM probe").fetchone()[0] == "committed"
            assert conn.execute("PRAGMA foreign_keys").fetchone()[0] == 1

    def test_lightweight_connection_rolls_back_and_closes_on_error(self, tmp_path: Path):
        """The lightweight context rolls back partial work and closes on exceptional exit."""
        connector = DatabaseConnection(tmp_path / "lightweight-rollback.db")
        with connector.connect() as conn:
            conn.execute("CREATE TABLE probe (value TEXT)")

        with pytest.raises(ValueError, match="lightweight rollback"):
            with connector.connect() as conn:
                _insert_lightweight_probe_then_raise(conn)

        with connector.connect() as conn:
            assert conn.execute("SELECT COUNT(*) FROM probe").fetchone()[0] == 0
            failing = conn
        with pytest.raises(sqlite3.ProgrammingError):
            failing.execute("SELECT 1")
