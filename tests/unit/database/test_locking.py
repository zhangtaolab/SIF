"""flock semantics proofs for ``index_lock`` (LIVE-07, T-11-01 mitigation).

Real files in tmp_path; POSIX-only (skipped where fcntl is absent). Kernel
flock properties under test: contention blocks with EAGAIN/EACCES, release
unblocks within the deadline, expiry proceeds without the lock (D-02),
holder death releases immediately (no stale locks by construction), the lock
file is created 0600, and the context manager releases on exit.
"""

from __future__ import annotations

import errno
import logging
import os
import subprocess
import sys
import threading
import time
from pathlib import Path

import pytest

from sif.database.locking import index_lock


fcntl = pytest.importorskip("fcntl", reason="flock arbitration is POSIX-only (A2)")

# Child that grabs the lock and sleeps: killed by the parent to prove the
# kernel releases flock on holder death.
_HOLD_SCRIPT = """
import fcntl, os, sys, time
fd = os.open(sys.argv[1], os.O_RDWR | os.O_CREAT, 0o600)
fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
print("ACQUIRED", flush=True)
time.sleep(60)
"""


def _lock_path(db_path: Path) -> Path:
    """Derive the lock path exactly as production code does."""
    return db_path.with_name(db_path.name + ".lock")


def _acquire_nb(path: Path) -> int:
    """Open and non-blocking-acquire the lock; returns the fd."""
    fd = os.open(path, os.O_RDWR | os.O_CREAT, 0o600)
    fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    return fd


class TestIndexLock:
    """Winner, contention, wait, expiry, death-release, mode, and release."""

    def test_winner_acquires_immediately_and_try_lock_blocks(self, tmp_path: Path) -> None:
        """The uncontended winner enters at once; a second try-lock gets EAGAIN/EACCES."""
        db_path = tmp_path / "sif.db"
        started = time.monotonic()
        with index_lock(db_path, timeout_s=5.0):
            assert time.monotonic() - started < 1.0
            fd = os.open(_lock_path(db_path), os.O_RDWR | os.O_CREAT, 0o600)
            try:
                with pytest.raises(BlockingIOError) as exc_info:
                    fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                assert exc_info.value.errno in (errno.EAGAIN, errno.EACCES)
            finally:
                os.close(fd)

    def test_lock_file_created_with_mode_0600(self, tmp_path: Path) -> None:
        """T-11-01: the lock file is created with owner-only permissions."""
        db_path = tmp_path / "sif.db"
        with index_lock(db_path, timeout_s=1.0):
            assert os.stat(_lock_path(db_path)).st_mode & 0o777 == 0o600

    def test_context_manager_releases_on_exit(self, tmp_path: Path) -> None:
        """After the with-block, a fresh acquire succeeds immediately."""
        db_path = tmp_path / "sif.db"
        with index_lock(db_path, timeout_s=1.0):
            pass
        fd = _acquire_nb(_lock_path(db_path))
        os.close(fd)

    def test_waiter_acquires_after_holder_releases(self, tmp_path: Path) -> None:
        """A blocked waiter acquires within the deadline once the holder releases."""
        db_path = tmp_path / "sif.db"
        holder_fd = _acquire_nb(_lock_path(db_path))
        acquired = threading.Event()

        def waiter() -> None:
            with index_lock(db_path, timeout_s=5.0):
                acquired.set()

        thread = threading.Thread(target=waiter)
        thread.start()
        time.sleep(0.3)  # the waiter is inside its poll loop now
        assert not acquired.is_set()  # still blocked while the lock is held
        fcntl.flock(holder_fd, fcntl.LOCK_UN)
        assert acquired.wait(timeout=2.0), "waiter did not acquire within ~1s of release"
        thread.join(timeout=5.0)
        assert not thread.is_alive()
        os.close(holder_fd)

    def test_deadline_expiry_proceeds_without_lock_and_notifies_once(
        self, tmp_path: Path
    ) -> None:
        """D-02: expiry is not an error — the body runs unlocked, once-notified, bounded."""
        db_path = tmp_path / "sif.db"
        holder_fd = _acquire_nb(_lock_path(db_path))
        wait_calls: list[int] = []
        body_ran = False
        started = time.monotonic()
        try:
            with index_lock(db_path, timeout_s=0.5, on_wait=lambda: wait_calls.append(1)):
                body_ran = True  # the loser still runs its own pass
        finally:
            os.close(holder_fd)
        elapsed = time.monotonic() - started
        assert body_ran
        assert wait_calls == [1]  # notified exactly once, on first contention
        assert 0.5 <= elapsed < 1.5  # waited out the deadline with bounded overshoot
        # The expired waiter holds nothing: the incumbent still owns the lock.
        fd = os.open(_lock_path(db_path), os.O_RDWR)
        try:
            with pytest.raises(BlockingIOError):
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        finally:
            os.close(fd)

    def test_holder_death_releases_lock_immediately(self, tmp_path: Path) -> None:
        """SIGKILLing the holder releases the kernel lock — no stale locks possible."""
        lock_path = _lock_path(tmp_path / "sif.db")
        holder = subprocess.Popen(
            [sys.executable, "-c", _HOLD_SCRIPT, str(lock_path)],
            stdout=subprocess.PIPE,
            text=True,
        )
        try:
            assert holder.stdout is not None
            assert holder.stdout.readline().strip() == "ACQUIRED"
            holder.kill()
            holder.wait(timeout=10)
        finally:
            if holder.stdout is not None:
                holder.stdout.close()
        started = time.monotonic()
        fd = _acquire_nb(lock_path)  # acquires at once: kernel released on death
        try:
            assert time.monotonic() - started < 1.0
        finally:
            os.close(fd)

    def test_non_posix_degrades_to_warning_and_runs_unlocked(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """Without fcntl the lock warns, runs unlocked, and creates no lock file (A2)."""
        import sif.database.locking as locking_mod

        monkeypatch.setattr(locking_mod, "_FCNTL_AVAILABLE", False)
        db_path = tmp_path / "sif.db"
        body_ran = False
        with caplog.at_level(logging.WARNING, logger="sif.database.locking"):
            with index_lock(db_path, timeout_s=1.0):
                body_ran = True
        assert body_ran
        assert not _lock_path(db_path).exists()
        assert any("fcntl unavailable" in rec.message for rec in caplog.records)
