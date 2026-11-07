"""In-suite SC1 concurrency proofs (LIVE-06, D-08a).

Multiple real sqlite3 connections and threads against a real file DB in
tmp_path: WAL lets CLI-style and MCP-style readers query while a writer
holds an open BEGIN IMMEDIATE transaction with zero "database is locked",
the busy handler waits out a short holder instead of failing instantly, and
interleaved threaded writers on separate factory connections complete
without OperationalError.
"""

from __future__ import annotations

import sqlite3
import threading
import time
from collections.abc import Generator
from pathlib import Path

import pytest

from sif.config.settings import get_settings
from sif.database.connection import DatabaseConnection
from sif.database.database import Database
from sif.database.factory import create_connection


@pytest.fixture(autouse=True)
def isolated_settings() -> Generator[None, None, None]:
    """Concurrency tests never inherit cached Settings."""
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def _pragma(conn: sqlite3.Connection, name: str) -> object:
    """Read one pragma value from the connection."""
    return conn.execute(f"PRAGMA {name}").fetchone()[0]


class TestReaderDuringWriter:
    """WAL SC1: readers coexist with an open write transaction."""

    def test_cli_and_mcp_style_readers_succeed_during_open_write_txn(self, tmp_path: Path) -> None:
        """Both connection styles SELECT cleanly while a write txn is open."""
        db_path = tmp_path / "sc1.db"
        with Database(db_path) as db:
            db.init_schema()

        writer = create_connection(db_path)
        try:
            writer.execute(
                "INSERT INTO collections (id, name, path, created_at, updated_at) "
                "VALUES ('w1', 'w1', '/w1', 'now', 'now')"
            )  # open implicit BEGIN IMMEDIATE write transaction

            # CLI-style reader (Database.connection) succeeds under WAL.
            with Database(db_path) as reader_db:
                count = reader_db.connection.execute("SELECT COUNT(*) FROM collections").fetchone()[
                    0
                ]
            assert count == 0  # WAL snapshot: the open txn stays invisible

            # MCP-style reader (DatabaseConnection.fetchone) succeeds too.
            row = DatabaseConnection(db_path).fetchone("SELECT COUNT(*) FROM collections")
            assert row is not None
            assert row[0] == 0

            writer.commit()

            with Database(db_path) as reader_db:
                after = reader_db.connection.execute("SELECT COUNT(*) FROM collections").fetchone()[
                    0
                ]
            assert after == 1
        finally:
            writer.close()


class TestBusyTimeoutWait:
    """busy_timeout: a second writer waits out a short holder, last-set-wins."""

    def test_second_writer_waits_out_short_holder(self, tmp_path: Path) -> None:
        """B's DML busy-waits until the holder commits instead of failing instantly."""
        db_path = tmp_path / "busy.db"
        setup = create_connection(db_path)
        setup.execute("CREATE TABLE busy_probe (x TEXT)")
        setup.commit()
        setup.close()

        holder = create_connection(db_path)
        waiter = create_connection(db_path)
        result: dict[str, object] = {}
        try:
            holder.execute("INSERT INTO busy_probe VALUES ('held')")  # write txn open

            def waiter_work() -> None:
                start = time.monotonic()
                waiter.execute("INSERT INTO busy_probe VALUES ('waited')")  # busy-waits
                waiter.commit()
                result["elapsed"] = time.monotonic() - start
                result["ok"] = True

            thread = threading.Thread(target=waiter_work)
            thread.start()
            time.sleep(0.3)  # holder still holds; the waiter is inside its busy wait
            assert "ok" not in result  # it cannot complete before the release
            holder.commit()  # release the write lock
            thread.join(timeout=5.0)
            assert not thread.is_alive()
        finally:
            holder.close()
            waiter.close()

        assert result.get("ok") is True
        assert result["elapsed"] >= 0.2  # waited (~0.3s), not an instant failure

    def test_busy_timeout_pragma_is_last_set_wins(self, tmp_path: Path) -> None:
        """A post-creation PRAGMA overrides the factory default."""
        conn = create_connection(tmp_path / "pragma.db")
        try:
            assert _pragma(conn, "busy_timeout") == 5000
            conn.execute("PRAGMA busy_timeout = 200")
            assert _pragma(conn, "busy_timeout") == 200
        finally:
            conn.close()


class TestThreadedInterleave:
    """Two threads with their own factory connections interleave cleanly."""

    def test_two_threads_interleave_without_operational_error(self, tmp_path: Path) -> None:
        db_path = tmp_path / "threads.db"
        setup = create_connection(db_path)
        setup.execute("CREATE TABLE interleaved (worker TEXT, seq INTEGER)")
        setup.commit()
        setup.close()

        conns = [create_connection(db_path), create_connection(db_path)]
        errors: list[tuple[str, str]] = []
        barrier = threading.Barrier(2)

        def worker(name: str, conn: sqlite3.Connection) -> None:
            try:
                barrier.wait(timeout=5.0)
                for i in range(20):
                    conn.execute("INSERT INTO interleaved VALUES (?, ?)", (name, i))
                    conn.commit()
                    conn.execute("SELECT COUNT(*) FROM interleaved").fetchall()
            except sqlite3.OperationalError as e:
                errors.append((name, str(e)))

        threads = [
            threading.Thread(target=worker, args=(f"w{n}", conn)) for n, conn in enumerate(conns)
        ]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=30.0)
        for conn in conns:
            conn.close()

        assert not any(thread.is_alive() for thread in threads)
        assert errors == []  # zero "database is locked"
        check = create_connection(db_path)
        try:
            assert check.execute("SELECT COUNT(*) FROM interleaved").fetchone()[0] == 40
        finally:
            check.close()
