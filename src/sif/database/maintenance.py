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

import shutil
import sqlite3
from dataclasses import dataclass
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
