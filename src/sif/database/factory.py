"""Shared SQLite connection factory (D-06).

Every connection the application opens — the CLI ``Database`` wrapper
(``Database.connection``) and the MCP ``DatabaseConnection`` wrapper
(``DatabaseConnection._create_connection``) — is created here, so no
connection site can forget the locked pragma recipe (LIVE-06):

1. ``PRAGMA busy_timeout = 5000`` FIRST, before WAL — the journal-mode switch
   itself needs a write lock and does not honor a busy handler (verified: it
   raises ``OperationalError`` immediately under contention despite the
   timeout), so the timeout must already be armed for everything after it.
2. ``PRAGMA journal_mode = WAL`` behind a bounded retry — the mode persists in
   the database header, so the retry cost is paid at most on the true first
   open (or after an external mode reset).
3. ``PRAGMA synchronous = NORMAL`` — WAL's default remains FULL and
   synchronous is per-connection, so it is set on every connection.

``isolation_level="IMMEDIATE"`` at connect time makes every ``with conn:``
block BEGIN IMMEDIATE with identical commit/rollback semantics. A deferred
transaction that reads and then writes after another writer committed would
otherwise fail instantly with ``database is locked`` despite busy_timeout.
Connections are never opened in autocommit (``isolation_level=None``) mode:
that would silently defuse every existing ``with conn:`` block.
"""

from __future__ import annotations

import sqlite3
import time
from pathlib import Path

import sqlite_vec

from sif.utils.logging import get_logger


logger = get_logger(__name__)

_WAL_RETRY_ATTEMPTS = 4
_WAL_RETRY_BACKOFF_SECONDS = 0.15

# The WAL-checkpoint recipe (12-D14) shared by both watch hosts' shutdown
# paths and the watcher's D-16 idle tick — one spelling, so the checkpoint
# contract (TRUNCATE) can only ever change in one place.
WAL_CHECKPOINT_TRUNCATE = "PRAGMA wal_checkpoint(TRUNCATE)"


def create_connection(db_path: Path) -> sqlite3.Connection:
    """Open one fully configured SQLite connection to ``db_path``.

    Applies the locked pragma recipe (busy_timeout → WAL → synchronous), loads
    the sqlite-vec extension best-effort, and arms implicit BEGIN IMMEDIATE
    transactions via ``isolation_level="IMMEDIATE"``.
    """
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(
        str(db_path),
        timeout=5.0,
        isolation_level="IMMEDIATE",
        detect_types=sqlite3.PARSE_DECLTYPES,
        check_same_thread=False,
    )
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    # busy_timeout must land before the WAL switch (locked pragma order): the
    # switch's lock upgrade ignores the busy handler, everything else honors it.
    conn.execute("PRAGMA busy_timeout = 5000")
    _set_wal_with_retry(conn, attempts=_WAL_RETRY_ATTEMPTS, backoff_s=_WAL_RETRY_BACKOFF_SECONDS)
    conn.execute("PRAGMA synchronous = NORMAL")
    _load_sqlite_vec(conn)
    return conn


def _set_wal_with_retry(
    conn: sqlite3.Connection,
    attempts: int = _WAL_RETRY_ATTEMPTS,
    backoff_s: float = _WAL_RETRY_BACKOFF_SECONDS,
) -> None:
    """Switch the database to WAL journal mode, absorbing first-open contention.

    The switch raises immediately under contention instead of honoring
    busy_timeout (verified), so simultaneous first opens are retried here. A
    pragma that succeeds but returns a mode other than ``wal`` (network-FS
    shape) means WAL is unsupported there: degrade with a warning instead of
    raising (locked network-FS fallback decision).
    """
    row: sqlite3.Row | None = None
    for _attempt in range(attempts - 1):
        row = _wal_switch(conn)
        if row is not None:
            break
        time.sleep(backoff_s)
    else:
        # Final attempt unguarded: persistent contention surfaces as the
        # original OperationalError instead of a synthesized one.
        row = conn.execute("PRAGMA journal_mode=WAL").fetchone()
    if row is None or row[0] != "wal":
        mode = row[0] if row else "unknown"
        logger.warning(
            "WAL journal mode unavailable (journal_mode=%s); continuing with the rollback journal",
            mode,
        )


def _wal_switch(conn: sqlite3.Connection) -> sqlite3.Row | None:
    """Run one WAL-switch attempt; ``None`` means the switch hit contention."""
    try:
        return conn.execute("PRAGMA journal_mode=WAL").fetchone()
    except sqlite3.OperationalError:
        return None


def _load_sqlite_vec(conn: sqlite3.Connection) -> None:
    """Load the sqlite-vec extension, swallowing failure (OQ3).

    Availability is detected lazily by ``SchemaManager``/``VectorSearcher``,
    so a missing extension disables vector features without breaking
    BM25-only installs.
    """
    try:
        conn.enable_load_extension(True)
        try:
            sqlite_vec.load(conn)
        finally:
            conn.enable_load_extension(False)
    except Exception:
        logger.debug("sqlite-vec extension unavailable; vector features stay disabled")
