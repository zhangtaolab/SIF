"""Unit proofs for the shared connection factory (LIVE-06, D-06).

Pragma audit (busy_timeout / WAL / synchronous / foreign_keys / IMMEDIATE
isolation), WAL persistence, WAL-switch retry under contention, the
network-FS degrade path, the sqlite-vec swallow, and the package exports.
The MCP path (``DatabaseConnection``) must inherit the same recipe through
its ``_create_connection`` delegation.
"""

from __future__ import annotations

import logging
import sqlite3
import time
from collections.abc import Generator
from pathlib import Path

import pytest

from sif.config.settings import get_settings
from sif.database.connection import DatabaseConnection
from sif.database.factory import create_connection


@pytest.fixture(autouse=True)
def isolated_settings() -> Generator[None, None, None]:
    """Factory/delegation tests never inherit cached Settings."""
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def _pragma(conn: sqlite3.Connection, name: str) -> object:
    """Read one pragma value from the connection."""
    return conn.execute(f"PRAGMA {name}").fetchone()[0]


class TestConnectionFactory:
    """Pragma audit, WAL behavior, degrade, swallow, and exports (LIVE-06)."""

    def test_pragma_audit_on_every_connection(self, tmp_path: Path) -> None:
        """Every factory connection carries the locked pragma recipe."""
        conn = create_connection(tmp_path / "audit.db")
        try:
            assert _pragma(conn, "busy_timeout") == 5000
            assert _pragma(conn, "journal_mode") == "wal"
            assert _pragma(conn, "synchronous") == 1  # NORMAL
            assert _pragma(conn, "foreign_keys") == 1
            assert conn.isolation_level == "IMMEDIATE"
            assert conn.row_factory is sqlite3.Row
        finally:
            conn.close()

    def test_wal_mode_persists_across_connections(self, tmp_path: Path) -> None:
        """A second factory connection reads wal without re-setting it."""
        first = create_connection(tmp_path / "persist.db")
        first.close()
        second = create_connection(tmp_path / "persist.db")
        try:
            assert _pragma(second, "journal_mode") == "wal"
        finally:
            second.close()

    def test_wal_switch_retry_absorbs_first_open_contention(self, tmp_path: Path) -> None:
        """The bounded retry absorbs the immediate-BUSY WAL-switch failure.

        The incumbent is a RAW connection so the database is still in DELETE
        journal mode (a factory incumbent would already be WAL, and the
        switch would never contend). Its write transaction is released on
        the factory's first retry backoff, deterministically.
        """
        import sif.database.factory as factory_mod

        db_path = tmp_path / "retry.db"
        incumbent = sqlite3.connect(str(db_path), check_same_thread=False)
        incumbent.execute("CREATE TABLE scratch (x INTEGER)")
        incumbent.commit()
        incumbent.execute("INSERT INTO scratch VALUES (1)")  # write txn held open

        real_sleep = time.sleep
        released = False

        def release_then_sleep(seconds: float) -> None:
            nonlocal released
            if not released:
                released = True
                incumbent.commit()  # release contention on the first backoff
            real_sleep(seconds)

        try:
            with pytest.MonkeyPatch.context() as mp:
                mp.setattr(factory_mod.time, "sleep", release_then_sleep)
                conn = create_connection(db_path)  # must not raise: retry absorbed BUSY
            if not released:
                incumbent.commit()
            try:
                assert _pragma(conn, "journal_mode") == "wal"
                assert conn.execute("SELECT COUNT(*) FROM scratch").fetchone()[0] == 1
            finally:
                conn.close()
        finally:
            incumbent.close()

    def test_non_wal_result_degrades_with_warning(self, caplog: pytest.LogCaptureFixture) -> None:
        """A journal-mode row that is not wal logs a warning and never raises."""
        from sif.database.factory import _set_wal_with_retry

        conn = sqlite3.connect(":memory:")  # PRAGMA journal_mode returns 'memory'
        try:
            with caplog.at_level(logging.WARNING, logger="sif.database.factory"):
                _set_wal_with_retry(conn)  # must not raise
            assert _pragma(conn, "journal_mode") == "memory"
        finally:
            conn.close()
        assert any("WAL journal mode unavailable" in rec.message for rec in caplog.records)

    def test_sqlite_vec_load_failure_is_swallowed(self, tmp_path: Path, monkeypatch) -> None:
        """A failing sqlite-vec load leaves a working connection (OQ3)."""

        def _explode(_conn: sqlite3.Connection) -> None:
            raise OSError("no vec")

        monkeypatch.setattr("sif.database.factory.sqlite_vec.load", _explode)
        conn = create_connection(tmp_path / "no-vec.db")
        try:
            assert conn.execute("SELECT 40 + 2").fetchone()[0] == 42
            assert _pragma(conn, "foreign_keys") == 1
        finally:
            conn.close()

    def test_database_package_exports_factory_and_lock(self) -> None:
        """sif.database exports create_connection and index_lock."""
        from sif.database import create_connection as exported_factory, index_lock as exported_lock

        assert callable(exported_factory)
        assert callable(exported_lock)

    def test_mcp_style_connection_inherits_factory_pragmas(self, tmp_path: Path) -> None:
        """DatabaseConnection (MCP path) gets the full recipe via delegation."""
        connector = DatabaseConnection(tmp_path / "mcp.db")
        with connector.connect() as conn:
            assert _pragma(conn, "journal_mode") == "wal"
            assert _pragma(conn, "busy_timeout") == 5000
            assert _pragma(conn, "synchronous") == 1
            assert conn.isolation_level == "IMMEDIATE"
            assert conn.row_factory is sqlite3.Row
