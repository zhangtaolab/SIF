"""Kernel-flock single-writer arbitration for index writes (D-01..D-03).

One global lock file per database (``{db_path}.lock``, created ``0600`` next
to the DB) is held via ``fcntl.flock`` for the duration of a long-running
index write. Two simultaneous ``sif index update`` processes serialize as
winner + waiting loser; the loser waits up to the configured deadline and
then runs its own pass anyway (D-02: a waiter never silently drops its
distinct work — checksum skipping makes overlapping passes no-ops).

Kernel flock semantics make stale locks impossible by construction: the lock
is released when the holder's process exits, even on SIGKILL. No PID files,
no liveness checks, no per-collection locks. On non-POSIX platforms without
``fcntl`` the lock degrades to a warning and runs unlocked (assumption A2) —
WAL + busy_timeout still protect integrity; only duplicate-work protection
is lost.
"""

from __future__ import annotations

import os
import time
from collections.abc import Callable, Generator
from contextlib import contextmanager
from pathlib import Path

from sif.utils.logging import get_logger


try:
    import fcntl

    _FCNTL_AVAILABLE = True
except ImportError:  # pragma: no cover - non-POSIX platforms (A2)
    _FCNTL_AVAILABLE = False


logger = get_logger(__name__)

_POLL_INTERVAL_SECONDS = 0.05


@contextmanager
def index_lock(
    db_path: Path,
    timeout_s: float,
    on_wait: Callable[[], None] | None = None,
) -> Generator[None, None, None]:
    """Hold the per-database index lock around the enclosed write job.

    The lock file is ``{db_path.name}.lock`` next to the database, created
    with mode 0600 so a pre-existing world-writable file or symlink cannot be
    injected with write access (T-11-01). ``on_wait`` fires once on first
    contention (the CLI's waiting notice). Deadline expiry is NOT an error:
    the block runs without the kernel lock so this writer still completes its
    own pass (D-02).
    """
    if not _FCNTL_AVAILABLE:
        logger.warning(
            "fcntl unavailable on this platform; index lock disabled "
            "(WAL + busy_timeout still protect database integrity)"
        )
        yield
        return

    # Canonicalize like Database does, so equivalent-but-different path
    # spellings (relative, ~, symlinked) share exactly one lock file per DB.
    lock_path = Path(db_path).expanduser().resolve()
    lock_path = lock_path.with_name(lock_path.name + ".lock")

    fd = os.open(lock_path, os.O_RDWR | os.O_CREAT, 0o600)
    deadline = time.monotonic() + timeout_s
    notified = False
    try:
        while True:
            try:
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except BlockingIOError:
                if not notified:
                    notified = True
                    if on_wait is not None:
                        on_wait()
                if time.monotonic() >= deadline:
                    # Availability over exclusion (D-02): run the pass anyway.
                    logger.info(
                        "Index lock wait deadline (%.1fs) expired for %s; proceeding unlocked",
                        timeout_s,
                        lock_path,
                    )
                    return
                time.sleep(_POLL_INTERVAL_SECONDS)
        yield
    finally:
        # Closing the fd releases the flock (locks are per open file
        # description; the fd stays open for the whole hold above).
        os.close(fd)
