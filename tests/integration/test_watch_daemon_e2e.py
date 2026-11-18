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
import textwrap
import time
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import TypeVar

from sif.core.models import Collection
from sif.database.database import Database
from sif.database.repositories import CollectionRepository


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


def _launcher_or_default(launcher: list[str] | None) -> list[str]:
    """Resolve the CLI launcher: the module form unless a caller supplies one."""
    if launcher is None:
        return [sys.executable, "-u", "-m", "sif.cli.main"]
    return list(launcher)


def _console_script(tmp_path: Path) -> Path:
    """Write a stand-in installed console script for the ``sif`` entry point.

    ``[project.scripts] sif = "sif.cli.main:main"`` generates a wrapper whose
    body imports ``main`` from the declared module and exits with its return
    code. Launching ``<python> <prefix>/sif ...`` is the real installed argv
    shape, and its ps command line never contains ``sif.cli.main`` (qtm).
    """
    script = tmp_path / "bin" / "sif"
    script.parent.mkdir(parents=True, exist_ok=True)
    script.write_text(
        f"#!{sys.executable}\n"
        "import sys\n"
        "\n"
        "from sif.cli.main import main\n"
        "\n"
        "if __name__ == '__main__':\n"
        "    sys.exit(main())\n",
        encoding="utf-8",
    )
    script.chmod(0o755)
    return script


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


def _detach(
    db_path: Path,
    cwd: Path,
    log_path: Path,
    launcher: list[str] | None = None,
) -> subprocess.CompletedProcess[str]:
    """Run the real detach parent; the child logs to ``log_path`` (hermetic)."""
    argv = [
        *_launcher_or_default(launcher),
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
        check=False,
    )


def _run_stop(
    db_path: Path,
    cwd: Path,
    launcher: list[str] | None = None,
) -> subprocess.CompletedProcess[str]:
    """Run the real ``watch --stop`` lifecycle command."""
    argv = [
        *_launcher_or_default(launcher),
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
        check=False,
    )


def _run_status(
    db_path: Path,
    cwd: Path,
    launcher: list[str] | None = None,
) -> subprocess.CompletedProcess[str]:
    """Run the real ``status`` command through the given launcher."""
    argv = [*_launcher_or_default(launcher), "--index", str(db_path), "status"]
    return subprocess.run(
        argv,
        cwd=cwd,
        env=_child_env(),
        capture_output=True,
        text=True,
        timeout=_STOP_TIMEOUT_S,
        check=False,
    )


@contextmanager
def _detached_daemon(
    db_path: Path,
    cwd: Path,
    log_path: Path,
    launcher: list[str] | None = None,
) -> Iterator[int]:
    """Detach a real daemon; yield its PID; never leak it past a failure.

    The safety net stops the daemon (``--stop``, fallback SIGKILL) even when
    an assertion inside the ``with`` block fails — a detached daemon must
    never outlive a failing test. ``launcher`` selects the CLI argv shape
    (module form by default, installed console script in the qtm test) and is
    forwarded to the safety net's ``--stop`` so the fallback corroborates the
    very process that was detached.
    """
    result = _detach(db_path, cwd, log_path, launcher)
    assert result.returncode == 0, (
        f"detach parent exited {result.returncode}:\n"
        f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
    )
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
            _run_stop(db_path, cwd, launcher)
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
        live_path = _doc_path(notes, "live-note.md")
        content = _fetch_one(db_path, "SELECT content FROM documents WHERE path = ?", (live_path,))
        assert content is not None
        assert "Live paragraph text" in content[0]

        # --stop exits 0, the daemon process is gone, the PID file is removed.
        stop = _run_stop(db_path, tmp_path)
        assert stop.returncode == 0, (
            f"watch --stop exited {stop.returncode}:\n"
            f"stdout:\n{stop.stdout}\nstderr:\n{stop.stderr}"
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
                f"watch --stop exited {stop.returncode}:\n"
                f"stdout:\n{stop.stdout}\nstderr:\n{stop.stderr}"
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
        f"watch --stop exited {result.returncode}:\n"
        f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
    )
    assert "not running" in result.stdout


def test_sigkill_then_immediate_redetach_succeeds(tmp_path: Path) -> None:
    """SC4: a SIGKILLed daemon leaves no stale lock — re-detach succeeds at once.

    Per-burst flock is kernel-released on process death (locking.py contract),
    so the replacement daemon needs no cleanup step and no lock error
    appears in either daemon's log. The stale PID file is simply overwritten
    (D-05: it is metadata, never a gate).
    """
    db_path = tmp_path / "watch.db"
    notes = tmp_path / "notes"
    log_a = tmp_path / "daemon-a.log"
    log_b = tmp_path / "daemon-b.log"
    pid_file = _pid_file_for(db_path)
    _seed_db(db_path, notes, "seed.md")

    # Daemon A reaches steady state, then dies uncleanly.
    with _detached_daemon(db_path, tmp_path, log_a) as pid_a:
        _wait_for_row(db_path, _doc_path(notes, "seed.md"), _STARTUP_DEADLINE_S)
        _wait_for_marker(log_a, "Watching", _STARTUP_DEADLINE_S)
        assert pid_file.exists()

        os.kill(pid_a, signal.SIGKILL)
        _wait_pid_gone(pid_a, _SHUTDOWN_DEADLINE_S)

    # IMMEDIATE re-detach: the parent must exit 0 with a NEW pid — no lock
    # error, no cleanup (SC4).
    with _detached_daemon(db_path, tmp_path, log_b) as pid_b:
        assert pid_b != pid_a
        payload = json.loads(pid_file.read_text(encoding="utf-8"))
        assert payload["pid"] == pid_b

        # The replacement daemon indexes a subsequent change, then stops
        # cleanly through the D-14 graceful path.
        _wait_for_marker(log_b, "Watching", _STARTUP_DEADLINE_S)
        (notes / "replacement.md").write_text(_NEW_BODY, encoding="utf-8")
        _wait_for_row(db_path, _doc_path(notes, "replacement.md"), _LIVE_DEADLINE_S)

        stop = _run_stop(db_path, tmp_path)
        assert stop.returncode == 0, (
            f"watch --stop exited {stop.returncode}:\n"
            f"stdout:\n{stop.stdout}\nstderr:\n{stop.stderr}"
        )
        _wait_pid_gone(pid_b, _SHUTDOWN_DEADLINE_S)

    # Neither daemon's log shows contention or a crash.
    for log_path in (log_a, log_b):
        log_text = log_path.read_text(encoding="utf-8", errors="replace")
        assert "lock wait deadline" not in log_text, f"stale lock error in {log_path}:\n{log_text}"
        assert "Traceback" not in log_text, f"traceback in {log_path}:\n{log_text}"


def test_detach_arm_timeout_kills_grandchild_session(tmp_path: Path) -> None:
    """SC2/WR-04: a handshake timeout must never leave a silent maybe-daemon.

    ``arm()`` outruns the handshake deadline, so the parent reports failure —
    but the grandchild would still finish arming and run the host forever
    unless the parent kills the detached session first. The runner below is
    a real double-fork in a subprocess; the grandchild records its survival
    in a marker file (its stdio is already redirected, so a file is the only
    channel), which must stay absent after the kill.
    """
    runner = textwrap.dedent(
        """
        import os
        import sys
        import time
        from pathlib import Path

        from sif.utils import daemon

        marker, log_path = Path(sys.argv[1]), Path(sys.argv[2])

        def slow_arm() -> None:
            time.sleep(2.0)

        outcome = daemon.detach(log_path, slow_arm, arm_timeout_s=0.3)
        if outcome.daemon:
            # Grandchild: the parent should have SIGKILLed us mid-arm.
            # Reaching here means the kill failed — record it and leave.
            marker.write_text("alive", encoding="utf-8")
            os._exit(0)

        assert not outcome.daemon
        assert outcome.error is not None
        assert "did not report readiness" in outcome.error
        assert "terminated" in outcome.error
        print(outcome.error)
        """
    )
    marker = tmp_path / "grandchild-survived"
    log_path = tmp_path / "daemon.log"
    result = subprocess.run(
        [sys.executable, "-u", "-c", runner, str(marker), str(log_path)],
        cwd=tmp_path,
        env=_child_env(),
        capture_output=True,
        text=True,
        timeout=_DETACH_TIMEOUT_S,
        check=False,
    )

    assert result.returncode == 0, (
        f"detach runner exited {result.returncode}:\n"
        f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
    )
    assert "terminated" in result.stdout

    # The grandchild's 2s sleep window outlasts the parent's 0.3s deadline
    # plus kill: wait it out, then prove nothing survived to run the host.
    deadline = time.monotonic() + 4.0
    while time.monotonic() < deadline:
        if marker.exists():
            break
        time.sleep(_POLL_INTERVAL_S)
    assert not marker.exists(), (
        "a grandchild survived the timeout kill and armed after the parent "
        "reported failure — silent maybe-detach (SC2 violation)"
    )


def test_console_script_daemon_corroborated_by_status_and_stop(tmp_path: Path) -> None:
    """qtm: status and --stop recognize a console-script-launched daemon.

    The installed entry point runs as ``<python> <prefix>/sif ... watch
    --detach``, whose ps command line never carries the ``sif.cli.main``
    module marker. A false-stale verdict is destructive, not cosmetic:
    ``sif status`` deletes the PID file it cannot corroborate and ``--stop``
    skips the graceful signal entirely. The PID file's survival through
    status is therefore the regression proof, not just the "running" text.
    """
    db_path = tmp_path / "watch.db"
    notes = tmp_path / "notes"
    log_path = tmp_path / "daemon.log"
    pid_file = _pid_file_for(db_path)
    _seed_db(db_path, notes, "seed.md")
    script = _console_script(tmp_path)
    launcher = [sys.executable, "-u", str(script)]

    with _detached_daemon(db_path, tmp_path, log_path, launcher=launcher) as pid:
        # Steady state: the startup reconcile row landed and the observer armed.
        _wait_for_row(db_path, _doc_path(notes, "seed.md"), _STARTUP_DEADLINE_S)
        _wait_for_marker(log_path, "Watching", _STARTUP_DEADLINE_S)
        assert pid_file.exists()

        status = _run_status(db_path, tmp_path, launcher)
        assert status.returncode == 0, (
            f"status exited {status.returncode}:\n"
            f"stdout:\n{status.stdout}\nstderr:\n{status.stderr}"
        )
        status_text = " ".join(status.stdout.split())
        assert "running" in status_text, (
            f"status did not report the daemon as running:\n{status.stdout}"
        )
        assert f"PID {pid}" in status_text, f"status did not name PID {pid}:\n{status.stdout}"
        assert "stale" not in status_text, (
            f"status treated the console-script daemon as stale:\n{status.stdout}"
        )
        assert pid_file.exists(), (
            "status removed a corroborated console-script daemon's PID file (false-stale verdict)"
        )

        stop = _run_stop(db_path, tmp_path, launcher)
        assert stop.returncode == 0, (
            f"watch --stop exited {stop.returncode}:\n"
            f"stdout:\n{stop.stdout}\nstderr:\n{stop.stderr}"
        )
        assert "Watch daemon stopped" in stop.stdout, (
            f"--stop did not report the graceful stop:\n{stop.stdout}"
        )
        assert "stale" not in stop.stdout, (
            f"--stop treated the console-script daemon as stale:\n{stop.stdout}"
        )
        _wait_pid_gone(pid, _SHUTDOWN_DEADLINE_S)
        assert not pid_file.exists(), "PID file survived --stop"
