"""Real-SQL tests for MigrationManager and its script application."""

from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from typing import Any

import pytest

from sif.config.constants import CURRENT_SCHEMA_VERSION
from sif.database.migrations import MigrationManager


class RealSQLiteAdapter:
    """Small real-SQLite adapter exposing MigrationManager's execute/fetchone API."""

    def __init__(self, connection: sqlite3.Connection) -> None:
        self.connection = connection

    def execute(self, query: str, parameters: tuple[Any, ...] | None = None) -> sqlite3.Cursor:
        return self.connection.execute(query, parameters or ())

    def executescript(self, script: str) -> sqlite3.Cursor:
        return self.connection.executescript(script)

    def fetchone(self, query: str, parameters: tuple[Any, ...] | None = None) -> sqlite3.Row | None:
        return self.connection.execute(query, parameters or ()).fetchone()


@pytest.fixture
def sqlite_adapter() -> Iterator[RealSQLiteAdapter]:
    """Yield a real in-memory connection through the migration adapter."""
    connection = sqlite3.connect(":memory:")
    connection.row_factory = sqlite3.Row
    try:
        yield RealSQLiteAdapter(connection)
    finally:
        connection.close()


class TestMigrationManager:
    """Fresh, current, failing, and reset migration behavior on real SQLite."""

    def test_missing_schema_version_table_returns_zero(self, sqlite_adapter: RealSQLiteAdapter):
        """An absent version table is interpreted as version zero."""
        manager = MigrationManager(sqlite_adapter)

        assert manager.get_current_version() == 0

    def test_fresh_migrate_applies_scripts_and_records_custom_dimension(
        self,
        sqlite_adapter: RealSQLiteAdapter,
    ):
        """Fresh migration creates actual tables and records the current version."""
        manager = MigrationManager(sqlite_adapter)
        executed_scripts: list[str] = []
        original_execute = sqlite_adapter.execute
        original_executescript = sqlite_adapter.executescript

        def recording_execute(
            query: str,
            parameters: tuple[Any, ...] | None = None,
        ) -> sqlite3.Cursor:
            if query.lstrip().startswith("CREATE VIRTUAL TABLE IF NOT EXISTS chunk_embeddings"):
                assert "FLOAT[768]" in query
                return sqlite_adapter.execute(
                    "CREATE TABLE IF NOT EXISTS chunk_embeddings "
                    "(embedding_id TEXT PRIMARY KEY, embedding BLOB)",
                )
            return original_execute(query, parameters)

        def recording_executescript(script: str) -> sqlite3.Cursor:
            executed_scripts.append(script)
            return original_executescript(script)

        sqlite_adapter.execute = recording_execute
        sqlite_adapter.executescript = recording_executescript
        manager.migrate(embedding_dim=768)

        assert manager.get_current_version() == CURRENT_SCHEMA_VERSION
        tables = {
            row[0]
            for row in sqlite_adapter.connection.execute(
                "SELECT name FROM sqlite_master WHERE type IN ('table', 'view')",
            ).fetchall()
        }
        assert {
            "collections",
            "documents",
            "chunks",
            "contexts",
            "schema_version",
            "documents_fts",
            "chunk_embeddings",
        } <= tables
        assert len(executed_scripts) == 2
        assert "CREATE TABLE IF NOT EXISTS collections" in executed_scripts[0]
        assert "CREATE VIRTUAL TABLE IF NOT EXISTS documents_fts" in executed_scripts[1]

    def test_current_version_migrate_is_noop(self, sqlite_adapter: RealSQLiteAdapter):
        """A current schema performs no schema or version writes."""
        sqlite_adapter.execute("CREATE TABLE schema_version (version INTEGER PRIMARY KEY)")
        sqlite_adapter.execute(
            "INSERT INTO schema_version (version) VALUES (?)",
            (CURRENT_SCHEMA_VERSION,),
        )
        manager = MigrationManager(sqlite_adapter)

        manager.migrate(embedding_dim=1024)

        assert (
            sqlite_adapter.connection.execute("SELECT COUNT(*) FROM schema_version").fetchone()[0]
            == 1
        )
        assert (
            sqlite_adapter.connection.execute(
                "SELECT 1 FROM sqlite_master WHERE name = 'collections'",
            ).fetchone()
            is None
        )

    def test_schema_sql_failure_propagates_without_version_row(
        self,
        sqlite_adapter: RealSQLiteAdapter,
    ):
        """An SQL failure is not swallowed and cannot report a completed migration."""
        manager = MigrationManager(sqlite_adapter)

        def fail_schema(script: str) -> sqlite3.Cursor:
            if "CREATE TABLE IF NOT EXISTS collections" in script:
                raise sqlite3.OperationalError("injected schema failure")
            return sqlite_adapter.connection.executescript(script)

        sqlite_adapter.executescript = fail_schema
        with pytest.raises(sqlite3.OperationalError, match="injected schema failure"):
            manager.migrate()

        assert (
            sqlite_adapter.connection.execute(
                "SELECT 1 FROM sqlite_master WHERE name = 'schema_version'",
            ).fetchone()
            is None
        )

    def test_reset_drops_named_tables_and_preserves_unrelated_data(
        self,
        sqlite_adapter: RealSQLiteAdapter,
    ):
        """Reset removes migration-owned tables without touching an unrelated table."""
        manager = MigrationManager(sqlite_adapter)
        sqlite_adapter.execute("CREATE TABLE schema_version (version INTEGER PRIMARY KEY)")
        sqlite_adapter.execute("CREATE TABLE documents (id TEXT PRIMARY KEY)")
        sqlite_adapter.execute("CREATE TABLE collections (id TEXT PRIMARY KEY)")
        sqlite_adapter.execute("CREATE TABLE unrelated_fixture (value TEXT)")
        sqlite_adapter.execute("INSERT INTO unrelated_fixture VALUES ('survives')")

        manager.reset()

        remaining = {
            row[0]
            for row in sqlite_adapter.connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'",
            ).fetchall()
        }
        assert "schema_version" not in remaining
        assert "documents" not in remaining
        assert "collections" not in remaining
        assert "unrelated_fixture" in remaining
        assert (
            sqlite_adapter.connection.execute(
                "SELECT value FROM unrelated_fixture",
            ).fetchone()[0]
            == "survives"
        )

        sqlite_adapter.execute("CREATE TABLE schema_version (version INTEGER PRIMARY KEY)")
        sqlite_adapter.execute(
            "INSERT INTO schema_version VALUES (?)",
            (CURRENT_SCHEMA_VERSION,),
        )
        assert manager.get_current_version() == CURRENT_SCHEMA_VERSION
