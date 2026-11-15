"""Integration tests for maintenance commands (SCALE-01/02, D-13/D-14).

Vacuum against a live reader must either succeed or return the documented
retryable error, and the database must stay sound either way. Backup against
live writes must produce an integrity-checked snapshot of the rows committed
before the copy.
"""

from __future__ import annotations

import sqlite3
import threading
from contextlib import closing
from pathlib import Path

from sif.config.settings import Settings
from sif.database.locking import index_lock
from sif.database.maintenance import MaintenanceBusyError, backup_index, vacuum_index


def _settings() -> Settings:
    """Settings double with a short lock deadline and no cache side effects."""
    return Settings(_env_file=None, cache_embeddings=False, lock_wait_timeout=2.0)


def _make_db(path: Path, rows: int = 50) -> None:
    """Create a small WAL database with a notes table."""
    conn = sqlite3.connect(path)
    try:
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("CREATE TABLE notes (id INTEGER PRIMARY KEY, body TEXT)")
        conn.executemany(
            "INSERT INTO notes (body) VALUES (?)",
            [("x" * 1024,) for _ in range(rows)],
        )
        conn.commit()
    finally:
        conn.close()


class TestVacuumUnderConcurrentReader:
    """A concurrent read transaction is retryable, never corruption."""

    def test_reader_transaction_yields_success_or_retryable_error(self, tmp_path: Path) -> None:
        db_path = tmp_path / "sif.db"
        _make_db(db_path)

        reader = sqlite3.connect(str(db_path), isolation_level=None)
        try:
            reader.execute("BEGIN")
            assert reader.execute("SELECT COUNT(*) FROM notes").fetchone()[0] > 0
            # A writer committing beyond the reader's snapshot pins the WAL.
            with closing(sqlite3.connect(str(db_path))) as writer:
                writer.execute("INSERT INTO notes (body) VALUES ('later')")
                writer.commit()
            failure: MaintenanceBusyError | None = None
            result = None
            try:
                result = vacuum_index(db_path, _settings())
            except MaintenanceBusyError as exc:
                failure = exc
            finally:
                reader.execute("ROLLBACK")
            if failure is not None:
                assert "retry" in str(failure).lower()
            else:
                assert result is not None
                assert result.reclaimed_bytes == result.before_bytes - result.after_bytes
        finally:
            reader.close()

        with closing(sqlite3.connect(str(db_path))) as conn:
            assert conn.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
        with index_lock(db_path, 2.0):
            acquired = True
        assert acquired


class TestBackupUnderLiveWrites:
    """The online backup API takes a consistent snapshot while writes continue."""

    def test_copy_passes_integrity_and_contains_pre_snapshot_rows(self, tmp_path: Path) -> None:
        db_path = tmp_path / "sif.db"
        _make_db(db_path, rows=20)
        output = tmp_path / "snapshot.db"

        stop = threading.Event()
        failures: list[BaseException] = []

        def writer() -> None:
            try:
                with closing(sqlite3.connect(str(db_path), timeout=5.0)) as conn:
                    counter = 0
                    while not stop.is_set():
                        conn.execute("INSERT INTO notes (body) VALUES (?)", ("live",))
                        conn.commit()
                        counter += 1
                        if counter % 50 == 0:
                            stop.wait(0.001)
            except BaseException as exc:  # pragma: no cover - surfaced below
                failures.append(exc)

        thread = threading.Thread(target=writer, daemon=True)
        thread.start()
        try:
            result = backup_index(db_path, output, _settings())
        finally:
            stop.set()
            thread.join(timeout=10)
        assert not failures
        assert result.bytes_written == output.stat().st_size

        with closing(sqlite3.connect(str(output))) as copy:
            assert copy.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
            copied = copy.execute("SELECT COUNT(*) FROM notes").fetchone()[0]
        with closing(sqlite3.connect(str(db_path))) as source:
            total = source.execute("SELECT COUNT(*) FROM notes").fetchone()[0]
        assert copied >= 20
        assert copied <= total
