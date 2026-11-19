"""Unit tests for the maintenance helpers (SCALE-01/02, D-13/D-14).

Vacuum: checkpoint-first, transaction-free VACUUM with a 2x (database + WAL)
disk precheck, a retryable busy error, and a reclaimed-size result.
Backup: the SQLite online backup API, hard target refusals, integrity
verification, 0600 permissions, and no convincing partial file on failure.
"""

from __future__ import annotations

import os
import sqlite3
import sys
from contextlib import closing
from pathlib import Path
from types import SimpleNamespace

import pytest

from sif.config.settings import Settings
from sif.database import maintenance
from sif.database.factory import WAL_CHECKPOINT_TRUNCATE
from sif.database.maintenance import (
    MaintenanceBusyError,
    MaintenanceTargetError,
    backup_index,
    default_backup_path,
    reconcile_embedded_documents,
    vacuum_index,
)
from tests.support import symlink_or_skip


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


class _FailingSource:
    """Source-connection double whose backup call fails on demand."""

    def __init__(self, message: str = "injected backup failure") -> None:
        self.message = message
        self.closed = False

    def execute(self, _sql: str, _parameters: tuple = ()) -> None:
        return None

    def backup(self, _target: sqlite3.Connection) -> None:
        raise sqlite3.OperationalError(self.message)

    def close(self) -> None:
        self.closed = True


class TestReconcileEmbeddedDocuments:
    """WR-01: reconcile tolerates an environment without the vec0 source table."""

    def test_missing_source_table_is_a_no_op_and_vacuum_still_works(self, tmp_path: Path) -> None:
        """Schema creation is extension-conditional: a DB built with sqlite-vec
        keeps the shadow after the extension becomes unavailable. Cleanup and
        vacuum must not fail with "no such table: document_embeddings"."""
        db_path = tmp_path / "stripped.db"
        conn = sqlite3.connect(db_path)
        try:
            conn.execute("CREATE TABLE embedded_documents (document_id TEXT PRIMARY KEY)")
            conn.execute("INSERT INTO embedded_documents(document_id) VALUES ('orphan')")
            conn.commit()

            assert reconcile_embedded_documents(conn) == (0, 0)
        finally:
            conn.close()

        result = vacuum_index(db_path, _settings())

        assert result.reclaimed_bytes == result.before_bytes - result.after_bytes
        with closing(sqlite3.connect(db_path)) as check:
            assert check.execute("SELECT COUNT(*) FROM embedded_documents").fetchone()[0] == 1


class _ModeRecordingSource:
    """Source-connection double that records the target's mode mid-copy."""

    def __init__(self, target: Path) -> None:
        self._target = target
        self.modes: list[int] = []
        self.closed = False

    def execute(self, _sql: str, _parameters: tuple = ()) -> None:
        return None

    def backup(self, _target: sqlite3.Connection) -> None:
        self.modes.append(self._target.stat().st_mode & 0o777)

    def close(self) -> None:
        self.closed = True


class TestDefaultBackupPath:
    """The default target is stem + UTC timestamp under the DB's backups dir."""

    def test_default_path_uses_stem_timestamp_and_backups_directory(self) -> None:
        db_path = Path("/tmp/sif.db")

        target = default_backup_path(db_path)

        assert target.parent == Path("/tmp/backups")
        assert target.name.startswith("sif-")
        assert target.name.endswith("Z.db")
        assert target.suffix == ".db"


class TestBackupTargetRefusals:
    """Every unsafe target is refused before a copy is made."""

    @pytest.mark.parametrize(
        ("kind", "expected"),
        [
            ("exists", "already exists"),
            ("symlink", "symlink"),
            ("db_path", "already exists"),
            ("wal", "index database"),
            ("lock", "index database"),
            ("stale_wal", "stale sidecar"),
        ],
    )
    def test_unsafe_targets_raise_target_error(
        self, tmp_path: Path, kind: str, expected: str
    ) -> None:
        db_path = tmp_path / "sif.db"
        _make_db(db_path, rows=2)
        output = tmp_path / "copy.db"
        if kind == "exists":
            output.write_bytes(b"do not overwrite")
        elif kind == "symlink":
            symlink_or_skip(output, tmp_path / "elsewhere.db")
        elif kind == "db_path":
            output = db_path
        elif kind == "wal":
            output = db_path.with_name(db_path.name + "-wal")
        elif kind == "lock":
            output = db_path.with_name(db_path.name + ".lock")
        elif kind == "stale_wal":
            output.with_name(output.name + "-wal").write_bytes(b"stale")

        with pytest.raises(MaintenanceTargetError) as excinfo:
            backup_index(db_path, output, _settings())

        assert expected in str(excinfo.value)

    def test_existing_target_is_not_modified(self, tmp_path: Path) -> None:
        db_path = tmp_path / "sif.db"
        _make_db(db_path, rows=2)
        output = tmp_path / "copy.db"
        output.write_bytes(b"do not overwrite")

        with pytest.raises(MaintenanceTargetError):
            backup_index(db_path, output, _settings())

        assert output.read_bytes() == b"do not overwrite"

    def test_missing_database_is_refused(self, tmp_path: Path) -> None:
        with pytest.raises(MaintenanceTargetError, match="does not exist"):
            backup_index(tmp_path / "absent.db", tmp_path / "copy.db", _settings())


class TestBackupIndex:
    """A backup is an integrity-checked snapshot with 0600 permissions."""

    def test_backup_opens_verifies_and_contains_committed_rows(self, tmp_path: Path) -> None:
        db_path = tmp_path / "sif.db"
        _make_db(db_path, rows=5, keep=5)
        output = tmp_path / "copy.db"

        result = backup_index(db_path, output, _settings())

        assert result.output == output.resolve()
        assert result.bytes_written == output.stat().st_size
        if sys.platform != "win32":
            # Windows reports 0666 and cannot enforce POSIX permission bits.
            assert output.stat().st_mode & 0o777 == 0o600
        assert maintenance._verify_backup(output) == [("ok",)]
        with closing(sqlite3.connect(output)) as conn:
            assert conn.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
            assert conn.execute("SELECT COUNT(*) FROM notes").fetchone()[0] == 5

    def test_default_target_creates_backups_directory(self, tmp_path: Path) -> None:
        db_path = tmp_path / "sif.db"
        _make_db(db_path, rows=2)

        result = backup_index(db_path, None, _settings())

        assert result.output.parent == tmp_path / "backups"
        assert result.output.parent.is_dir()
        assert result.output.exists()

    def test_backup_failure_removes_the_just_created_target(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        db_path = tmp_path / "sif.db"
        _make_db(db_path, rows=2)
        output = tmp_path / "copy.db"
        fake = _FailingSource()
        monkeypatch.setattr(maintenance, "create_connection", lambda _path: fake)

        with pytest.raises(MaintenanceTargetError) as excinfo:
            backup_index(db_path, output, _settings())

        assert "injected backup failure" in str(excinfo.value)
        assert not output.exists()
        assert fake.closed

    def test_busy_backup_is_retryable(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        db_path = tmp_path / "sif.db"
        _make_db(db_path, rows=2)
        output = tmp_path / "copy.db"
        fake = _FailingSource("database is locked")
        monkeypatch.setattr(maintenance, "create_connection", lambda _path: fake)

        with pytest.raises(MaintenanceBusyError, match="Retry once"):
            backup_index(db_path, output, _settings())

        assert not output.exists()

    def test_integrity_failure_keeps_the_copy_and_names_it(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        db_path = tmp_path / "sif.db"
        _make_db(db_path, rows=2)
        output = tmp_path / "copy.db"
        monkeypatch.setattr(maintenance, "_verify_backup", lambda _target: [("row 3 missing",)])

        with pytest.raises(MaintenanceTargetError) as excinfo:
            backup_index(db_path, output, _settings())

        message = str(excinfo.value)
        assert str(output.resolve()) in message
        assert "row 3 missing" in message
        assert output.exists()

    def test_copy_is_owner_only_before_the_backup_api_writes(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """WR-03: the restrictive mode applies during the copy, not after it.

        The previous code let sqlite3.connect create the target (0o666 & umask)
        and chmod'ed only after backup + integrity_check finished.
        """
        db_path = tmp_path / "sif.db"
        _make_db(db_path, rows=2)
        output = tmp_path / "copy.db"
        source = _ModeRecordingSource(output)
        monkeypatch.setattr(maintenance, "create_connection", lambda _path: source)

        previous_umask = os.umask(0o022)
        try:
            backup_index(db_path, output, _settings())
        finally:
            os.umask(previous_umask)

        if sys.platform != "win32":
            # Windows reports 0666 and cannot enforce POSIX permission bits.
            assert source.modes == [0o600]
            assert output.stat().st_mode & 0o777 == 0o600

    def test_target_is_created_exclusively_without_following_symlinks(self, tmp_path: Path) -> None:
        """WR-04: creation, not a path pre-check, enforces the target contract."""
        target = tmp_path / "copy.db"
        maintenance._create_backup_target(target)
        if sys.platform != "win32":
            # Windows reports 0666 and cannot enforce POSIX permission bits.
            assert target.stat().st_mode & 0o777 == 0o600

        # A file that appeared after validation is refused, never overwritten.
        with pytest.raises(MaintenanceTargetError, match="already exists"):
            maintenance._create_backup_target(target)

        elsewhere = tmp_path / "elsewhere.db"
        link = tmp_path / "link.db"
        symlink_or_skip(link, elsewhere)
        with pytest.raises(MaintenanceTargetError):
            maintenance._create_backup_target(link)
        assert not elsewhere.exists()

    def test_never_uses_a_file_copy_or_vacuum_into(self) -> None:
        source = Path(maintenance.__file__).read_text(encoding="utf-8")

        assert "shutil.copy" not in source
        assert "VACUUM INTO" not in source
