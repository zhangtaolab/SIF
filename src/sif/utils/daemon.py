"""Detached-daemon process lifecycle utilities (Phase 13, LIVE-09 SC2).

The PID file owned here is MANAGEMENT METADATA ONLY — never arbitration and
never a startup gate (D-05). Single-writer arbitration stays with the
per-burst kernel flock in :mod:`sif.database.locking` (kernel-released on
process death, so two daemons may run simultaneously and a SIGKILLed one
leaves no stale lock — SC4). The PID file is a pointer so ``--stop`` and
``sif status`` can find the daemon; because a PID file can be stale, tampered,
or left by a reboot, every signal decision corroborates the target process's
identity first (Pitfall 3) and refuses — fail-closed — on any mismatch.

The detach is the classic stdlib double-fork (fork -> setsid -> fork) with a
pipe handshake: the daemon grandchild runs ``arm()`` (open the database,
select collections, write the PID file) and only then reports its PID to the
original parent, so the printed PID always refers to an armed daemon — never
a silent maybe-detach (SC2). The fork happens before the caller builds any
thread or observer (Pitfall 2); stdio redirects to ``/dev/null`` and the log
file (D-07), and the working directory is deliberately NOT changed so
relative ``--index`` paths keep resolving.
"""

from __future__ import annotations

import contextlib
import json
import os
import select
import shutil
import signal
import subprocess
import sys
import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from sif.utils.logging import get_logger


logger = get_logger(__name__)

_PID_SUFFIX = ".watch.pid"
_ARM_TIMEOUT_SECONDS = 30.0
_STOP_TERM_TIMEOUT_SECONDS = 10.0
_STOP_KILL_TIMEOUT_SECONDS = 5.0
_POLL_INTERVAL_SECONDS = 0.05
_PS_TIMEOUT_SECONDS = 5.0

# Identity markers (Pitfall 3): the ps command line of a real sif watch
# process contains the CLI module path, and the watch subcommand appears as
# its own whitespace token (a "watch.db" path fragment must not corroborate).
_CLI_MARKER = "sif.cli.main"
_WATCH_MARKER = "watch"


@dataclass
class DetachOutcome:
    """Result of :func:`detach` for the original parent, or the go-ahead for the daemon.

    ``daemon=True`` only ever comes back inside the daemon grandchild: the
    caller must now run the host body on the armed resources. In the original
    parent exactly one of ``pid`` (armed) or ``error`` (failure) is set.
    """

    daemon: bool = False
    pid: int | None = None
    error: str | None = None


@dataclass
class StopOutcome:
    """Result of :func:`stop_daemon` for the CLI's user-facing messaging."""

    status: str  # "stopped" | "not_running" | "stale"
    pid: int | None = None


def pid_path_for(db_path: str | Path) -> Path:
    """Derive the sibling PID file path for an index database (D-05).

    Canonicalizes exactly like :func:`sif.database.locking.index_lock` does
    for the lock file, so equivalent path spellings share one artifact.
    """
    resolved = Path(db_path).expanduser().resolve()
    return resolved.with_name(resolved.name + _PID_SUFFIX)


def write_pid_file(path: Path, *, pid: int, mode: str, depth: str) -> None:
    """Write the one-line JSON PID payload with mode 0600 (T-13-04).

    The payload carries what management needs: pid, host mode, update depth,
    and a UTC start timestamp.
    """
    payload = {
        "pid": pid,
        "mode": mode,
        "depth": depth,
        "started": datetime.now(timezone.utc).isoformat(),
    }
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as handle:
        handle.write(json.dumps(payload) + "\n")


def read_pid_file(path: Path) -> dict[str, object] | None:
    """Defensively parse the PID payload; ANY defect reads back as None.

    A missing file, garbage bytes, empty content, non-dict JSON, or
    wrong-typed/missing fields all return None — a tampered artifact must
    never crash a reader or drive a kill (T-13-04).
    """
    try:
        raw = path.read_bytes()
    except OSError:
        return None
    try:
        payload = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return None
    if not isinstance(payload, dict):
        return None
    pid = payload.get("pid")
    if isinstance(pid, bool) or not isinstance(pid, int):
        return None
    for key in ("mode", "depth", "started"):
        if not isinstance(payload.get(key), str):
            return None
    return payload


def remove_pid_file(path: Path) -> None:
    """Remove the PID file if present (metadata only — safe to be wrong)."""
    try:
        path.unlink(missing_ok=True)
    except OSError:
        logger.warning("Could not remove PID file %s", path, exc_info=True)


def corroborate_pid(payload: dict[str, object]) -> bool:
    """Fail-closed identity check before any signal (Pitfall 3, T-13-03).

    A process is only corroborated when it is alive AND its ps command line
    carries both the sif CLI module marker and the watch subcommand as its
    own token. Process-gone, ps missing, ps failure, or any mismatch returns
    False — an uncorroborated PID is never signalled.
    """
    pid = payload.get("pid")
    if isinstance(pid, bool) or not isinstance(pid, int):
        return False
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except OSError:
        # Alive but not probeable (e.g. another user's process): the argv
        # check below is the identity decision, so fall through to it.
        pass
    ps_path = shutil.which("ps")
    if ps_path is None:
        return False
    try:
        result = subprocess.run(
            [ps_path, "-p", str(pid), "-o", "command="],
            capture_output=True,
            text=True,
            timeout=_PS_TIMEOUT_SECONDS,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return False
    if result.returncode != 0:
        return False
    return _CLI_MARKER in result.stdout and _WATCH_MARKER in result.stdout.split()


def detach(
    log_path: Path, arm: Callable[[], None], *, arm_timeout_s: float = _ARM_TIMEOUT_SECONDS
) -> DetachOutcome:
    """Double-fork into a detached daemon with a deterministic arming handshake.

    The grandchild redirects stdio (/dev/null in, ``log_path`` out/err,
    mode 0644 per the D-07/launchd log-tree contract), then calls ``arm()``,
    which must fully prepare the daemon — database open, schema, collections
    selected, PID file written — before the ``armed <pid>`` pipe message. An
    ``arm()`` failure is reported through the pipe instead, and the original
    parent surfaces it as a non-zero exit (never a silent maybe-detach).
    A handshake TIMEOUT is likewise never a silent maybe-detach (SC2): the
    parent SIGKILLs the detached session before reporting the failure (see
    :func:`_kill_detached_group`).

    Returns:
        In the original parent: the arming outcome (pid or error). In the
        daemon grandchild: ``daemon=True`` — run the host body now.
    """
    read_fd, write_fd = os.pipe()
    pid = os.fork()
    if pid > 0:
        # Original parent: learn the outcome, then return it so the CLI
        # prints the PID line and exits 0 (SC2) — or reports the failure.
        os.close(write_fd)
        try:
            message = _read_pipe_message(read_fd, arm_timeout_s)
        finally:
            os.close(read_fd)
        if message is None:
            # The grandchild may still arm late (slow init_schema under a
            # concurrent reindex, first-use model load, slow storage) and
            # run the host forever after the CLI reports failure — kill the
            # detached session before reporting (SC2: never a silent
            # maybe-detach).
            _kill_detached_group(pid)
        # Reap the short-lived intermediate child (already-reaped cannot
        # happen here — this is the first wait on it).
        with contextlib.suppress(OSError):
            os.waitpid(pid, 0)
        return _parent_outcome(message, arm_timeout_s)

    # First child: new session, then fork again so the daemon is not a
    # session leader and can never re-acquire a controlling terminal.
    with contextlib.suppress(OSError):  # pragma: no cover - fresh child is never a leader
        os.setsid()
    if os.fork() > 0:
        os._exit(0)

    # Grandchild — the daemon. Redirect stdio BEFORE arming (D-07). The
    # working directory is deliberately NOT changed: relative --index paths
    # must keep resolving (research recipe note).
    os.close(read_fd)
    sys.stdout.flush()
    sys.stderr.flush()
    devnull_fd = os.open(os.devnull, os.O_RDONLY)
    log_fd = os.open(log_path, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o644)
    os.dup2(devnull_fd, 0)
    os.dup2(log_fd, 1)
    os.dup2(log_fd, 2)
    os.close(devnull_fd)
    os.close(log_fd)
    try:
        arm()
    except Exception as e:
        _write_pipe_message(write_fd, f"error {type(e).__name__}: {e}")
        os.close(write_fd)
        os._exit(1)
    _write_pipe_message(write_fd, f"armed {os.getpid()}")
    os.close(write_fd)
    return DetachOutcome(daemon=True)


def stop_daemon(
    pid_path: Path,
    *,
    term_timeout_s: float = _STOP_TERM_TIMEOUT_SECONDS,
    kill_timeout_s: float = _STOP_KILL_TIMEOUT_SECONDS,
    poll_interval_s: float = _POLL_INTERVAL_SECONDS,
    now: Callable[[], float] = time.monotonic,
) -> StopOutcome:
    """Stop the daemon behind ``pid_path`` with corroborated escalation (D-05).

    Read -> corroborate -> SIGTERM -> bounded poll -> SIGKILL fallback ->
    remove the file. An unreadable or uncorroborated payload is stale: the
    file is cleaned up and NO signal is ever sent (Pitfall 3, fail-closed).
    """
    payload = read_pid_file(pid_path)
    if payload is None:
        if pid_path.exists():
            remove_pid_file(pid_path)
            return StopOutcome("stale")
        return StopOutcome("not_running")
    pid = payload.get("pid")
    assert isinstance(pid, int)
    assert not isinstance(pid, bool)
    if not corroborate_pid(payload):
        remove_pid_file(pid_path)
        return StopOutcome("stale", pid=pid)
    _terminate_corroborated(pid, term_timeout_s, kill_timeout_s, poll_interval_s, now)
    remove_pid_file(pid_path)
    return StopOutcome("stopped", pid=pid)


def _terminate_corroborated(
    pid: int,
    term_timeout_s: float,
    kill_timeout_s: float,
    poll_interval_s: float,
    now: Callable[[], float],
) -> None:
    """SIGTERM -> bounded poll -> SIGKILL -> bounded poll for a corroborated PID."""
    if _signal_or_confirm_gone(pid, signal.SIGTERM):
        return
    if _wait_gone(pid, term_timeout_s, poll_interval_s, now):
        return
    _signal_or_confirm_gone(pid, signal.SIGKILL)
    if not _wait_gone(pid, kill_timeout_s, poll_interval_s, now):
        logger.warning("Daemon PID %s still present after SIGKILL", pid)


def _signal_or_confirm_gone(pid: int, sig: int) -> bool:
    """Send ``sig``; True when the process had already vanished instead."""
    try:
        os.kill(pid, sig)
    except ProcessLookupError:
        return True
    return False


def _wait_gone(
    pid: int,
    timeout_s: float,
    poll_interval_s: float,
    now: Callable[[], float],
) -> bool:
    """Deadline-bounded poll for process death; True once ProcessLookupError."""
    deadline = now() + timeout_s
    while True:
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            return True
        if now() >= deadline:
            return False
        time.sleep(poll_interval_s)


def _kill_detached_group(pgid: int) -> None:
    """SIGKILL the detached daemon's whole process group (SC2 timeout cleanup).

    The intermediate child became a session and group leader via
    ``setsid()`` before forking the grandchild, so the process group id IS
    that child's pid: one ``killpg`` reaches a late-arming grandchild and
    anything it spawned. Best-effort by design — a group that already
    exited (ProcessLookupError) or cannot be signalled (PermissionError)
    surfaces through the caller's failure report, never as a crash here.
    """
    with contextlib.suppress(OSError):
        os.killpg(pgid, signal.SIGKILL)


def _parent_outcome(message: str | None, timeout_s: float) -> DetachOutcome:
    """Translate the handshake message into the parent-side outcome."""
    if message is None:
        return DetachOutcome(
            error=(
                f"daemon did not report readiness within {timeout_s:.0f}s; "
                "terminated the daemon process group — if a daemon still "
                "survives, stop it with 'sif watch --stop'"
            )
        )
    if message.startswith("armed "):
        try:
            return DetachOutcome(pid=int(message[len("armed ") :]))
        except ValueError:
            return DetachOutcome(error=f"garbled handshake message: {message!r}")
    if message.startswith("error "):
        return DetachOutcome(error=message[len("error ") :])
    return DetachOutcome(error=f"unexpected handshake message: {message!r}")


def _read_pipe_message(read_fd: int, timeout_s: float) -> str | None:
    """Read one pipe message under a deadline; None on timeout or error.

    Returns at EOF (the daemon closes its write end after the message), so
    the parent never blocks past ``timeout_s`` on a hung daemon.
    """
    deadline = time.monotonic() + timeout_s
    chunks: list[bytes] = []
    while True:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            return None
        try:
            ready, _, _ = select.select([read_fd], [], [], remaining)
        except (OSError, ValueError):
            return None
        if not ready:
            return None
        try:
            data = os.read(read_fd, 4096)
        except OSError:
            return None
        if not data:
            return b"".join(chunks).decode("utf-8", errors="replace").strip()
        chunks.append(data)


def _write_pipe_message(write_fd: int, message: str) -> None:
    """Best-effort pipe write; a vanished parent has nothing to report to."""
    with contextlib.suppress(OSError):
        os.write(write_fd, message.encode("utf-8"))
