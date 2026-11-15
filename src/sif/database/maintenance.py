"""Index maintenance helpers (CORR-06, D-10; SCALE-01/02, D-13/D-14).

These helpers may scan: they run only from explicit maintenance paths
(``sif cleanup``, ``sif index vacuum``) inside the caller's transaction, never
from the search path. The search path reads the derived shadow through
display-gate probes plus indexed primary-key lookups and must never
reintroduce a full ``document_embeddings`` scan.

Vacuum and backup run outside ``Database.transaction()`` on their own
connection; the CLI owns the ``index_lock`` around them so a single wait
notice covers the whole maintenance window. Busy/locked failures surface as
``MaintenanceBusyError`` (retryable), invalid targets and verification
failures as ``MaintenanceTargetError``; neither is ever reported as a partial
success.
"""

from __future__ import annotations

import os
import shutil
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING

from sif.database.factory import WAL_CHECKPOINT_TRUNCATE, create_connection
from sif.utils.logging import get_logger


if TYPE_CHECKING:
    from sif.config.settings import Settings


logger = get_logger(__name__)


class MaintenanceBusyError(RuntimeError):
    """A maintenance operation lost the race for the SQLite write lock."""


class MaintenanceTargetError(RuntimeError):
    """A maintenance target is invalid or a maintenance step failed."""


@dataclass(frozen=True)
class VacuumResult:
    """Byte sizes around one vacuum run."""

    before_bytes: int
    after_bytes: int
    reclaimed_bytes: int


@dataclass(frozen=True)
class BackupResult:
    """Where a verified backup copy landed and how large it is."""

    output: Path
    bytes_written: int


_SHADOW_EXISTS_SQL = "SELECT 1 FROM sqlite_master WHERE type='table' AND name='embedded_documents'"
_SHADOW_DELETE_STALE_SQL = (
    "DELETE FROM embedded_documents "
    "WHERE document_id NOT IN (SELECT id FROM documents) "
    "   OR document_id NOT IN (SELECT document_id FROM document_embeddings)"
)
_SHADOW_INSERT_MISSING_SQL = (
    "INSERT OR IGNORE INTO embedded_documents(document_id) "
    "SELECT DISTINCT de.document_id FROM document_embeddings de "
    "JOIN documents d ON d.id = de.document_id"
)


def reconcile_embedded_documents(conn: sqlite3.Connection) -> tuple[int, int]:
    """Reconcile the derived ``embedded_documents`` shadow with its sources.

    Deletes shadow rows whose document or embeddings are gone, then inserts
    missing rows for documents that still exist and still have embeddings
    (the join means a deleted document is never resurrected). Returns
    ``(deleted, inserted)``.

    No commit: the caller owns the transaction, so a cleanup/vacuum failure
    rolls the reconciliation back with the rest of the maintenance work. Both
    statements scan by design — maintenance paths may; the search path must
    not (CORR-06).
    """
    row = conn.execute(_SHADOW_EXISTS_SQL).fetchone()
    if row is None:
        return 0, 0

    deleted = conn.execute(_SHADOW_DELETE_STALE_SQL).rowcount
    inserted = conn.execute(_SHADOW_INSERT_MISSING_SQL).rowcount
    return deleted, inserted


def _set_busy_timeout(conn: sqlite3.Connection, settings: Settings) -> None:
    """Arm the connection's busy handler from the configured lock deadline.

    The value is a typed int (never interpolated user text), and the floor of
    one millisecond keeps a zero-deadline configuration as a busy handler
    rather than SQLite's "no handler" default.
    """
    timeout_ms = max(1, int(settings.lock_wait_timeout * 1000))
    conn.execute(f"PRAGMA busy_timeout = {timeout_ms}")


def _index_bytes(db_path: Path) -> int:
    """Sum the main database file and its WAL when the WAL is present."""
    total = db_path.stat().st_size
    wal_path = db_path.with_name(db_path.name + "-wal")
    if wal_path.exists():
        total += wal_path.stat().st_size
    return total


def vacuum_index(db_path: Path, settings: Settings) -> VacuumResult:
    """Reclaim free pages with a checkpoint-first, transaction-free VACUUM.

    The caller holds ``index_lock``; this function opens its own connection,
    reconciles the derived shadow in one short transaction, checkpoints with
    TRUNCATE, refuses to run when the database directory lacks 2x the current
    (database + WAL) bytes, then runs ``VACUUM`` outside any transaction and
    attempts a final best-effort checkpoint.

    Raises ``MaintenanceBusyError`` when another connection blocks the
    checkpoint (retryable) and ``MaintenanceTargetError`` when the disk
    precheck fails or a step raises an OS/SQLite error. ``Database.transaction``
    is never used: VACUUM fails inside an open transaction.
    """
    db_path = Path(db_path)
    conn = create_connection(db_path)
    try:
        _set_busy_timeout(conn, settings)
        if conn.in_transaction:
            raise RuntimeError(
                f"vacuum_index requires a connection outside any transaction (db_path={db_path})"
            )

        with conn:
            reconcile_embedded_documents(conn)

        before_bytes = _index_bytes(db_path)

        checkpoint = conn.execute(WAL_CHECKPOINT_TRUNCATE).fetchone()
        if checkpoint is not None and checkpoint[0]:
            raise MaintenanceBusyError(
                "The WAL checkpoint could not complete because another connection "
                "is using the index. Retry once active readers finish."
            )

        required_bytes = 2 * before_bytes
        available_bytes = shutil.disk_usage(db_path.parent).free
        if available_bytes < required_bytes:
            raise MaintenanceTargetError(
                f"Not enough free disk space to vacuum {db_path}: required "
                f"{required_bytes} bytes ({required_bytes / (1024 * 1024):.2f} MiB), "
                f"available {available_bytes} bytes "
                f"({available_bytes / (1024 * 1024):.2f} MiB) in {db_path.parent}."
            )

        conn.execute("VACUUM")

        final_checkpoint = conn.execute(WAL_CHECKPOINT_TRUNCATE).fetchone()
        if final_checkpoint is not None and final_checkpoint[0]:
            logger.warning(
                "Final WAL checkpoint after vacuum was busy for %s; the vacuum "
                "itself completed and the WAL will be checkpointed on a later idle open",
                db_path,
            )

        after_bytes = _index_bytes(db_path)
        return VacuumResult(
            before_bytes=before_bytes,
            after_bytes=after_bytes,
            reclaimed_bytes=before_bytes - after_bytes,
        )
    except (sqlite3.Error, OSError) as e:
        if _is_busy_error(e):
            raise MaintenanceBusyError(
                "The database is locked or busy. Retry once the other index "
                f"writer or reader has finished ({e})."
            ) from e
        raise MaintenanceTargetError(f"Vacuum failed for {db_path}: {e}") from e
    finally:
        conn.close()


def _is_busy_error(error: Exception) -> bool:
    """Whether a SQLite/OS error is the retryable locked/busy shape."""
    message = str(error).lower()
    return "locked" in message or "busy" in message


def default_backup_path(db_path: Path) -> Path:
    """Return ``<db_dir>/backups/<stem>-<UTC timestamp>.db``."""
    stem = Path(db_path).stem
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return Path(db_path).parent / "backups" / f"{stem}-{stamp}.db"


def _validate_backup_target(db_path: Path, target: Path) -> None:
    """Refuse unsafe backup targets before any connection is opened.

    A symlink is checked before resolution because resolving would hide it;
    the reserved set names the database itself and its WAL/SHM/lock sidecars;
    stale target sidecars would make the copy indistinguishable from a live DB.
    """
    if target.is_symlink():
        raise MaintenanceTargetError(f"Refusing to back up to {target}: the target is a symlink.")
    if target.exists():
        raise MaintenanceTargetError(
            f"Refusing to back up to {target}: the target already exists. "
            "Choose a new path or remove the existing file."
        )

    resolved = target.resolve()
    reserved = {
        db_path,
        db_path.with_name(db_path.name + "-wal"),
        db_path.with_name(db_path.name + "-shm"),
        db_path.with_name(db_path.name + ".lock"),
    }
    if resolved in reserved:
        raise MaintenanceTargetError(
            f"Refusing to back up to {target}: the target is the index database, "
            "a WAL/SHM sidecar, or the lock file."
        )
    for suffix in ("-wal", "-shm"):
        sidecar = target.with_name(target.name + suffix)
        if sidecar.exists() or sidecar.is_symlink():
            raise MaintenanceTargetError(
                f"Refusing to back up to {target}: a stale sidecar {sidecar} exists."
            )


def _verify_backup(target: Path) -> list[tuple[str, ...]]:
    """Return the copy's ``PRAGMA integrity_check`` rows from a fresh connection.

    This runs on a plain connection (never the source or backup connection) so
    a copy that a later reader could not open is caught before success is
    reported.
    """
    conn = sqlite3.connect(str(target))
    try:
        rows = conn.execute("PRAGMA integrity_check").fetchall()
    finally:
        conn.close()
    return [tuple(str(value) for value in row) for row in rows]


def _discard_backup(target: Path) -> None:
    """Remove a failed, just-created copy; it never existed before this run."""
    try:
        target.unlink(missing_ok=True)
    except OSError:
        logger.warning("Could not remove failed backup copy %s", target)


def _copy_with_online_backup(db_path: Path, target: Path, settings: Settings) -> None:
    """Copy through ``Connection.backup`` and discard any failed partial file."""
    source: sqlite3.Connection | None = None
    try:
        source = create_connection(db_path)
        _set_busy_timeout(source, settings)
        target_conn = sqlite3.connect(str(target))
        try:
            # Connection.backup is the only WAL-safe mechanism; a plain file
            # copy is not consistent under concurrent writers.
            source.backup(target_conn)
        finally:
            target_conn.close()
    except sqlite3.Error as e:
        _discard_backup(target)
        if _is_busy_error(e):
            raise MaintenanceBusyError(
                "The database is locked or busy. Retry once the other index "
                f"writer has finished ({e})."
            ) from e
        raise MaintenanceTargetError(f"Backup to {target} failed: {e}") from e
    except OSError as e:
        _discard_backup(target)
        raise MaintenanceTargetError(f"Backup to {target} failed: {e}") from e
    finally:
        if source is not None:
            source.close()


def _finalize_backup_copy(target: Path) -> int:
    """Return the verified copy's size and restrict it to the owner."""
    try:
        bytes_written = target.stat().st_size
    except OSError as e:
        raise MaintenanceTargetError(
            f"Backup reported success but {target} is unreadable: {e}."
        ) from e
    try:
        # Backups contain full document text: never group/other readable.
        os.chmod(target, 0o600)
    except OSError:
        logger.warning("Could not restrict permissions on backup copy %s", target)
    return bytes_written


def backup_index(db_path: Path, output: Path | None, settings: Settings) -> BackupResult:
    """Create a verified snapshot through the SQLite online backup API.

    The target is validated before any connection exists (no symlink, nothing
    to overwrite, no database/sidecar/lock collision, no stale target
    sidecars), the copy is taken with ``Connection.backup`` on a fresh target
    connection under the caller's ``index_lock``, and success is reported only
    after ``PRAGMA integrity_check`` returns exactly ``ok``.

    A backup/OS failure removes the just-created copy and raises
    ``MaintenanceTargetError``; an integrity failure keeps it for inspection
    and raises naming the copy and the integrity output. Busy/locked failures
    raise the retryable ``MaintenanceBusyError``.
    """
    db_path = Path(db_path).expanduser().resolve()
    if not db_path.exists():
        raise MaintenanceTargetError(
            f"Cannot back up {db_path}: the index database does not exist."
        )

    target = Path(output).expanduser() if output is not None else default_backup_path(db_path)
    _validate_backup_target(db_path, target)
    target = target.resolve()

    try:
        target.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    except OSError as e:
        raise MaintenanceTargetError(
            f"Cannot create the backup directory {target.parent}: {e}."
        ) from e

    _copy_with_online_backup(db_path, target, settings)

    try:
        integrity = _verify_backup(target)
    except (sqlite3.Error, OSError) as e:
        raise MaintenanceTargetError(
            f"Backup copy at {target} could not be verified: {e}. "
            "The file was kept for inspection; do not use it as a backup."
        ) from e
    if integrity != [("ok",)]:
        raise MaintenanceTargetError(
            f"Backup copy at {target} failed PRAGMA integrity_check: {integrity}. "
            "The file was kept for inspection; do not use it as a backup."
        )

    return BackupResult(output=target, bytes_written=_finalize_backup_copy(target))
