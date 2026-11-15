"""Unit tests for the maintenance helpers (SCALE-01/02, D-13/D-14).

Vacuum: checkpoint-first, transaction-free VACUUM with a 2x (database + WAL)
disk precheck, a retryable busy error, and a reclaimed-size result.
"""

from __future__ import annotations

import sqlite3
from contextlib import closing
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch  # noqa: F401  (used by later tasks' batteries)

import pytest

from sif.config.settings import Settings
from sif.database import maintenance
from sif.database.factory import WAL_CHECKPOINT_TRUNCATE
from sif.database.maintenance import MaintenanceBusyError, MaintenanceTargetError, vacuum_index


def _settings() -> Settings:
    """Settings double with a short lock deadline and no cache side effects."""
    return Settings(_env_file=None, cache_embeddings=False, lock_wait_timeout=1.0)


def _make_db(path: Path, *, rows: int = 200, keep: int = 1) -> None:
    """Create a database whose deleted rows leave reclaimable free pages."""
    conn = sqlite3.connect(path)
    try:
        conn.execute("CREATE TABLE notes (id INTEGER PRIMARY KEY, body TEXT)")
        conn.executemany(
            "INSERT INTO notes (body) VALUES (?)",
            [("x" * 4096,) for _ in range(rows)],
        )
        conn.commit()
        conn.execute("DELETE FROM notes WHERE id > ?", (keep,))
        conn.commit()
    finally:
        conn.close()


class _FakeCursor:
    """Minimal cursor double for a monkeypatched checkpoint result."""

    def __init__(self, row: tuple[int, int, int]) -> None:
        self._row = row

    def fetchone(self) -> tuple[int, int, int]:
        return self._row


class _RecordingConnection:
    """Proxy that records top-level statements and can fake the checkpoint.

    ``with proxy:`` yields the real connection so the reconcile helper runs
    against real SQLite; only the maintenance function's own top-level calls
    are recorded/faked.
    """

    def __init__(
        self,
        conn: sqlite3.Connection,
        checkpoint_row: tuple[int, int, int] | None = None,
    ) -> None:
        self._conn = conn
        self._checkpoint_row = checkpoint_row
        self.statements: list[str] = []

    def execute(self, sql: str, parameters: tuple = ()) -> object:
        self.statements.append(sql)
        if self._checkpoint_row is not None and sql == WAL_CHECKPOINT_TRUNCATE:
            return _FakeCursor(self._checkpoint_row)
        return self._conn.execute(sql, parameters)

    def __getattr__(self, name: str) -> object:
        return getattr(self._conn, name)

    def __enter__(self) -> sqlite3.Connection:
        return self._conn.__enter__()

    def __exit__(self, *args: object) -> object:
        return self._conn.__exit__(*args)


class TestVacuumIndex:
    """`vacuum_index` composes reconcile, checkpoint, precheck, VACUUM, checkpoint."""

    def test_vacuum_reclaims_space_and_preserves_rows(self, tmp_path: Path) -> None:
        db_path = tmp_path / "sif.db"
        _make_db(db_path)

        result = vacuum_index(db_path, _settings())

        assert result.reclaimed_bytes == result.before_bytes - result.after_bytes
        assert result.reclaimed_bytes > 0
        assert result.after_bytes < result.before_bytes
        with closing(sqlite3.connect(db_path)) as conn:
            assert conn.execute("SELECT COUNT(*) FROM notes").fetchone()[0] == 1
            assert conn.execute("PRAGMA integrity_check").fetchone()[0] == "ok"

    def test_low_disk_raises_with_required_and_available_before_vacuum(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        db_path = tmp_path / "sif.db"
        _make_db(db_path)
        real_create = maintenance.create_connection
        recorded: list[_RecordingConnection] = []

        def fake_create(path: Path) -> _RecordingConnection:
            proxy = _RecordingConnection(real_create(path))
            recorded.append(proxy)
            return proxy

        monkeypatch.setattr(maintenance, "create_connection", fake_create)
        monkeypatch.setattr(
            maintenance.shutil,
            "disk_usage",
            lambda _path: SimpleNamespace(total=10, used=9, free=1),
        )

        with pytest.raises(MaintenanceTargetError) as excinfo:
            vacuum_index(db_path, _settings())

        message = str(excinfo.value)
        assert "Not enough free disk space" in message
        assert "required" in message
        assert "available 1 bytes" in message
        assert recorded, "the maintenance connection should have been opened"
        assert "VACUUM" not in recorded[0].statements

    def test_busy_checkpoint_is_retryable(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        db_path = tmp_path / "sif.db"
        _make_db(db_path)
        real_create = maintenance.create_connection

        def fake_create(path: Path) -> _RecordingConnection:
            return _RecordingConnection(real_create(path), checkpoint_row=(1, 4, 0))

        monkeypatch.setattr(maintenance, "create_connection", fake_create)

        with pytest.raises(MaintenanceBusyError) as excinfo:
            vacuum_index(db_path, _settings())

        assert "Retry once active readers finish" in str(excinfo.value)

    def test_open_transaction_is_refused(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        db_path = tmp_path / "sif.db"
        _make_db(db_path)
        real_create = maintenance.create_connection
        conn = real_create(db_path)
        conn.execute("BEGIN IMMEDIATE")
        monkeypatch.setattr(maintenance, "create_connection", lambda _path: conn)

        with pytest.raises(RuntimeError, match="outside any transaction"):
            vacuum_index(db_path, _settings())

    def test_vacuum_runs_with_no_open_transaction_at_execute_time(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        db_path = tmp_path / "sif.db"
        _make_db(db_path)
        real_create = maintenance.create_connection
        observed: list[bool] = []

        class _ObservingConnection(_RecordingConnection):
            def execute(self, sql: str, parameters: tuple = ()) -> object:
                if sql == "VACUUM":
                    observed.append(self._conn.in_transaction)
                return super().execute(sql, parameters)

        def fake_create(path: Path) -> _ObservingConnection:
            return _ObservingConnection(real_create(path))

        monkeypatch.setattr(maintenance, "create_connection", fake_create)

        vacuum_index(db_path, _settings())

        assert observed == [False]
