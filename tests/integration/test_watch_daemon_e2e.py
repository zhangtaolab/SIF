"""Real-subprocess end-to-end battery for the detached watch daemon (13-02).

SC2/D-05..D-09: ``sif watch --detach`` backgrounds the watcher through the
stdlib double-fork and reports the daemon PID before the parent exits 0; the
daemon runs the exact foreground host body (live changes indexed with no
terminal attached); ``sif watch --stop`` ends it through the D-14 graceful
path. SC4: a SIGKILLed daemon leaves no stale lock — an immediate re-detach
succeeds with no lock error (flock is kernel-released on process death).

Culture copied from ``test_watch_e2e``: real CLI subprocesses over seeded tmp
collections, outcome assertions (rows, exit codes, WAL size, PID files),
deadline-bounded polls through fresh sqlite connections, and a safety net
that guarantees a detached daemon never leaks past a failing assertion.
"""

from __future__ import annotations

import json
import os
import re
import signal
import sqlite3
import subprocess
import sys
import time
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import TypeVar

from sif.database.database import Database
from sif.database.repositories import CollectionRepository
from sif.core.models import Collection


_SEED_BODY = "# Seed Note\n\n" + ("Seed paragraph text. " * 30)
_NEW_BODY = "# Live Note\n\n" + ("Live paragraph text. " * 30)

_STARTUP_DEADLINE_S = 30.0
_LIVE_DEADLINE_S = 30.0
_SHUTDOWN_DEADLINE_S = 20.0
_DETACH_TIMEOUT_S = 60.0
_STOP_TIMEOUT_S = 30.0
_POLL_INTERVAL_S = 0.1

# The PID line the detach parent prints before exiting 0 (SC2).
_PID_LINE_RE = re.compile(r"Watch daemon running \(PID (\d+)\)")

T = TypeVar("T")


def _seed_db(db_path: Path, notes_dir: Path, seed_name: str) -> None:
    """Build a real index with one collection pointing at a one-file tree."""
    notes_dir.mkdir(parents=True, exist_ok=True)
    (notes_dir / seed_name).write_text(_SEED_BODY, encoding="utf-8")
    db = Database(db_path)
    try:
        db.init_schema()
        with db.connection:
            CollectionRepository(db.connection).create(
                Collection(name="notes", path=str(notes_dir))
            )
    finally:
        db.close()


def _child_env(extra: dict[str, str] | None = None) -> dict[str, str]:
    """Child environment: SIF_-stripped, FORCE_COLOR unset, NO_COLOR on."""
    env = {k: v for k, v in os.environ.items() if not k.startswith("SIF_")}
    env.pop("FORCE_COLOR", None)
    env["NO_COLOR"] = "1"
    if extra is not None:
        env.update(extra)
    return env


def _pid_file_for(db_path: Path) -> Path:
    """Sibling PID file path next to the DB (the D-05 artifact contract)."""
    resolved = db_path.resolve()
    return resolved.with_name(resolved.name + ".watch.pid")


def _fetch_one(db_path: Path, sql: str, params: tuple[str, ...] = ()) -> tuple | None:
    """Fetch one row through a fresh connection (never a cached reader)."""
    conn = sqlite3.connect(str(db_path))
    try:
        return conn.execute(sql, params).fetchone()
    finally:
        conn.close()


def _poll_until(check: Callable[[], T | None], deadline_s: float, description: str) -> T:
    """Poll ``check`` under an explicit deadline; None means "not yet"."""
    deadline = time.monotonic() + deadline_s
    while time.monotonic() < deadline:
        result = check()
        if result is not None:
            return result
        time.sleep(_POLL_INTERVAL_S)
    raise AssertionError(f"{description} not observed within {deadline_s}s")


def _doc_path(notes_dir: Path, name: str) -> str:
    """Stored-path spelling for a file under the collection (resolved)."""
    return str((notes_dir / name).resolve())


def _wait_for_row(db_path: Path, path: str, deadline_s: float) -> None:
    """Poll fresh connections until ``path`` exists in documents."""

    def _present() -> tuple | None:
        return _fetch_one(db_path, "SELECT 1 FROM documents WHERE path = ?", (path,))

    _poll_until(_present, deadline_s, f"document row for {path}")


def _wait_for_marker(text_path: Path, needle: str, deadline_s: float) -> None:
    """Wait until the file's current content contains ``needle``."""

    def _seen() -> str | None:
        if not text_path.exists():
            return None
        text = text_path.read_text(encoding="utf-8", errors="replace")
        return text if needle in text else None

    _poll_until(_seen, deadline_s, f"marker {needle!r} in {text_path.name}")


def _pid_alive(pid: int) -> bool:
    """os.kill(pid, 0) liveness probe."""
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        return True


def _wait_pid_gone(pid: int, deadline_s: float) -> None:
    """Poll until the process is gone (deadline-bounded, never naked sleep)."""

    def _gone() -> bool | None:
        return True if not _pid_alive(pid) else None

    _poll_until(_gone, deadline_s, f"daemon PID {pid} to exit")


def _detach(db_path: Path, cwd: Path, log_path: Path) -> subprocess.CompletedProcess[str]:
    """Run the real detach parent; the child logs to ``log_path`` (hermetic)."""
    argv = [
        sys.executable,
        "-u",
        "-m",
        "sif.cli.main",
        "--index",
        str(db_path),
        "watch",
        "--detach",
        "--log-file",
        str(log_path),
    ]
    return subprocess.run(
        argv,
        cwd=cwd,
        env=_child_env(),
        capture_output=True,
        text=True,
        timeout=_DETACH_TIMEOUT_S,
    )


def _run_stop(db_path: Path, cwd: Path) -> subprocess.CompletedProcess[str]:
    """Run the real ``watch --stop`` lifecycle command."""
    argv = [
        sys.executable,
        "-u",
        "-m",
        "sif.cli.main",
        "--index",
        str(db_path),
        "watch",
        "--stop",
    ]
    return subprocess.run(
        argv,
        cwd=cwd,
        env=_child_env(),
        capture_output=True,
        text=True,
        timeout=_STOP_TIMEOUT_S,
    )


@contextmanager
def _detached_daemon(db_path: Path, cwd: Path, log_path: Path) -> Iterator[int]:
    """Detach a real daemon; yield its PID; never leak it past a failure.

    The safety net stops the daemon (``--stop``, fallback SIGKILL) even when
    an assertion inside the ``with`` block fails — a detached daemon must
    never outlive a failing test.
    """
    result = _detach(db_path, cwd, log_path)
    match = _PID_LINE_RE.search(result.stdout)
    assert match is not None, (
        f"detach parent printed no daemon PID line (exit {result.returncode}):\n"
        f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
    )
    pid = int(match.group(1))
    try:
        yield pid
    finally:
        if _pid_alive(pid):
            _run_stop(db_path, cwd)
        if _pid_alive(pid):
            os.kill(pid, signal.SIGKILL)
        _wait_pid_gone(pid, _SHUTDOWN_DEADLINE_S)


def test_detach_backgrounds_watcher_and_indexes_live_changes(tmp_path: Path) -> None:
    """SC2: --detach reports the PID, indexes live changes headless, --stop ends it."""
    db_path = tmp_path / "watch.db"
    notes = tmp_path / "notes"
    log_path = tmp_path / "daemon.log"
    pid_file = _pid_file_for(db_path)
    _seed_db(db_path, notes, "seed.md")

    with _detached_daemon(db_path, tmp_path, log_path) as pid:
        # The handshake artifact: PID file next to the DB, parseable payload
        # whose pid matches the PID the parent printed (never a maybe-detach).
        _poll_until(
            lambda: pid_file if pid_file.exists() else None,
            _STARTUP_DEADLINE_S,
            "PID file creation",
        )
        payload = json.loads(pid_file.read_text(encoding="utf-8"))
        assert payload["pid"] == pid
        assert payload["mode"] == "daemon"
        assert payload["depth"] == "bm25"

        # Daemon reaches steady state: startup reconcile, then observer armed.
        _wait_for_row(db_path, _doc_path(notes, "seed.md"), _STARTUP_DEADLINE_S)
        _wait_for_marker(log_path, "Watching", _STARTUP_DEADLINE_S)

        # Live change indexed with no terminal attached (SC2 core).
        (notes / "live-note.md").write_text(_NEW_BODY, encoding="utf-8")
        _wait_for_row(db_path, _doc_path(notes, "live-note.md"), _LIVE_DEADLINE_S)
        content = _fetch_one(
            db_path, "SELECT content FROM documents WHERE path = ?", (_doc_path(notes, "live-note.md"),)
        )
        assert content is not None
        assert "Live paragraph text" in content[0]

        # --stop exits 0, the daemon process is gone, the PID file is removed.
        stop = _run_stop(db_path, tmp_path)
        assert stop.returncode == 0, (
            f"watch --stop exited {stop.returncode}:\nstdout:\n{stop.stdout}\nstderr:\n{stop.stderr}"
        )
        _wait_pid_gone(pid, _SHUTDOWN_DEADLINE_S)
        assert not pid_file.exists(), "PID file survived --stop"


def test_stop_terminates_gracefully_with_wal_truncate(tmp_path: Path) -> None:
    """--stop drives the D-14 graceful path: no traceback, WAL truncated to 0."""
    db_path = tmp_path / "watch.db"
    notes = tmp_path / "notes"
    log_path = tmp_path / "daemon.log"
    wal_path = Path(str(db_path) + "-wal")
    _seed_db(db_path, notes, "seed.md")

    # The parent holds an open read connection so the daemon's close is never
    # the last one — SQLite otherwise DELETES a checkpointed -wal, and the
    # post-exit 0-byte file is the truncate proof (12 e2e precedent).
    holder = sqlite3.connect(str(db_path))
    try:
        holder.execute("SELECT COUNT(*) FROM documents").fetchone()
        with _detached_daemon(db_path, tmp_path, log_path) as pid:
            _wait_for_row(db_path, _doc_path(notes, "seed.md"), _STARTUP_DEADLINE_S)
            _wait_for_marker(log_path, "Watching", _STARTUP_DEADLINE_S)

            (notes / "live.md").write_text(_NEW_BODY, encoding="utf-8")
            _wait_for_row(db_path, _doc_path(notes, "live.md"), _LIVE_DEADLINE_S)

            def _wal_has_frames() -> int | None:
                size = wal_path.stat().st_size if wal_path.exists() else -1
                return size if size > 0 else None

            _poll_until(_wal_has_frames, _LIVE_DEADLINE_S, "non-empty WAL before stop")

            stop = _run_stop(db_path, tmp_path)
            assert stop.returncode == 0, (
                f"watch --stop exited {stop.returncode}:\nstdout:\n{stop.stdout}\nstderr:\n{stop.stderr}"
            )
            _wait_pid_gone(pid, _SHUTDOWN_DEADLINE_S)

        assert wal_path.exists(), "-wal vanished with a live reader"
        assert wal_path.stat().st_size == 0, (
            f"-wal holds {wal_path.stat().st_size} bytes after graceful stop"
        )
        log_text = log_path.read_text(encoding="utf-8", errors="replace")
        assert "Traceback" not in log_text, f"daemon log shows a traceback:\n{log_text}"
    finally:
        holder.close()


def test_stop_without_daemon_prints_not_running(tmp_path: Path) -> None:
    """Stop idempotence: no PID file -> yellow not-running notice, exit 0."""
    db_path = tmp_path / "watch.db"
    notes = tmp_path / "notes"
    _seed_db(db_path, notes, "seed.md")

    result = _run_stop(db_path, tmp_path)

    assert result.returncode == 0, (
        f"watch --stop exited {result.returncode}:\nstdout:\n{result.stdout}\nstderr:\n{result.stderr}"
    )
    assert "not running" in result.stdout
