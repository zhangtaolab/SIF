"""OS service-manager install/uninstall for the watch host (Phase 13, SC3).

``sif watch --install-service`` generates a launchd LaunchAgent (macOS) or a
systemd user unit (Linux) whose argv runs the FOREGROUND ``sif watch`` with
the install-time flags baked in — the supervised process never forks
(SC3/D-11); ``--detach`` is a deliberately distinct path (D-06). Generation
is pure text (plistlib for the plist, a fixed template for the unit) so both
artifacts are built and asserted on ANY platform (D-13); live manager
invocation happens only where the manager exists.

Every manager invocation is an explicit argv list — never through a shell,
never a string command line (D-12, T-13-10): everything embedded in
ProgramArguments/ExecStart derives from flags and resolved absolute paths,
and plist values go through plistlib (typed, escaped) rather than string
interpolation into XML. Artifacts are written atomically
(write-temp-then-rename) with mode 0644 into user-owned directories, and
only our own label's filename is ever written or removed (T-13-11).
"""

from __future__ import annotations

import os
import plistlib
import shutil
import subprocess
import sys
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from platformdirs import user_log_dir

from sif.utils.logging import get_logger


logger = get_logger(__name__)

SERVICE_LABEL = "com.docsif.watch"
UNIT_NAME = "sif-watch.service"
UNIT_BASENAME = "sif-watch"
LAUNCHD_MANAGER = "launchd"
SYSTEMD_MANAGER = "systemd"

_LOG_BASENAME = "watch"
_THROTTLE_INTERVAL_S = 10
_RESTART_SEC = 5

# The manager binaries are invoked by bare name (resolved through PATH —
# their presence is gated by shutil.which first); never a string command
# line, never a shell (D-12).
_LAUNCHCTL = "launchctl"
_SYSTEMCTL = "systemctl"

Runner = Callable[..., subprocess.CompletedProcess[Any]]


class ServiceManagerMissing(RuntimeError):  # noqa: N818 — plan-named type (13-04 action text)
    """The platform's service-manager binary is not on PATH (friendly remedy)."""

    def __init__(self, manager: str) -> None:
        """Pick the binary name and remedy for the manager kind."""
        if manager == LAUNCHD_MANAGER:
            binary = _LAUNCHCTL
            remedy = (
                "the macOS launchd service is installed through launchctl; verify "
                "you are on macOS with /bin/launchctl available"
            )
        else:
            binary = _SYSTEMCTL
            remedy = (
                "the Linux systemd user service is installed through systemctl; "
                "verify you are on a Linux host with systemd (systemctl --user)"
            )
        super().__init__(
            f"{binary} was not found on PATH — required to install the watch service ({remedy})."
        )


class ServiceCommandError(RuntimeError):
    """A service-manager invocation failed; carries the failing argv + detail."""

    def __init__(self, argv: list[str], detail: str) -> None:
        """Format the failing argv and the manager's own failure detail."""
        self.argv = list(argv)
        super().__init__(f"`{' '.join(argv)}` failed: {detail}")


@dataclass(frozen=True)
class InstallResult:
    """What the installer hands the CLI so it can point the user at everything."""

    artifact_path: Path
    log_location: str
    verify_command: str


def _watch_argv(python: str, abs_db: str, argv_tail: list[str]) -> list[str]:
    """The supervisor argv: absolute interpreter, foreground watch, baked tail."""
    return [python, "-m", "sif.cli.main", "--index", abs_db, "watch", *argv_tail]


def build_plist(
    python: str,
    db_path: str | Path,
    argv_tail: list[str],
    log_dir: str | Path,
    *,
    label: str = SERVICE_LABEL,
) -> dict[str, object]:
    """Build the launchd LaunchAgent definition (D-13 keys) as a plist dict.

    The absolute interpreter + ``-m sif.cli.main`` form means the service
    never depends on a user PATH; ``RunAtLoad``/``KeepAlive`` make it start
    at login and stay alive; ``ThrottleInterval=10`` matches the launchd
    default, stated explicitly as documentation.
    """
    abs_db = str(Path(db_path).expanduser().resolve())
    logs = Path(log_dir).expanduser()
    return {
        "Label": label,
        "ProgramArguments": _watch_argv(python, abs_db, argv_tail),
        "RunAtLoad": True,
        "KeepAlive": True,
        "ThrottleInterval": _THROTTLE_INTERVAL_S,
        "StandardOutPath": str(logs / f"{_LOG_BASENAME}.log"),
        "StandardErrorPath": str(logs / f"{_LOG_BASENAME}.err.log"),
    }


def _systemd_quote(token: str) -> str:
    """Quote an ExecStart token when whitespace/quotes would split it wrongly."""
    if not any(ch in token for ch in ' \t"\\'):
        return token
    escaped = token.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def render_unit(python: str, db_path: str | Path, argv_tail: list[str]) -> str:
    """Render the systemd user unit (D-13 keys) as text.

    ``Type=simple`` + foreground ExecStart (never fork, never ``&``) so
    systemd's exit tracking and ``Restart=on-failure`` see the real watcher.
    """
    abs_db = str(Path(db_path).expanduser().resolve())
    exec_start = " ".join(_systemd_quote(tok) for tok in _watch_argv(python, abs_db, argv_tail))
    return (
        "[Unit]\n"
        "Description=DocSIF watch daemon\n"
        "\n"
        "[Service]\n"
        "Type=simple\n"
        f"ExecStart={exec_start}\n"
        "Restart=on-failure\n"
        f"RestartSec={_RESTART_SEC}\n"
        "\n"
        "[Install]\n"
        "WantedBy=default.target\n"
    )


def launchd_plist_path(label: str = SERVICE_LABEL) -> Path:
    """The LaunchAgent destination: user-owned ~/Library/LaunchAgents/<label>.plist."""
    return Path.home() / "Library" / "LaunchAgents" / f"{label}.plist"


def systemd_unit_path() -> Path:
    """The user-unit destination: ~/.config/systemd/user/<UNIT_NAME>."""
    return Path.home() / ".config" / "systemd" / "user" / UNIT_NAME


def _write_artifact(path: Path, data: bytes) -> None:
    """Write-temp-then-rename with mode 0644 (T-13-11).

    A pre-planted file/symlink at the destination is atomically replaced,
    and the manager (which must be able to read the artifact) sees either
    the old complete file or the new complete one.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.tmp")
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o644)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(data)
        os.replace(tmp, path)
    except BaseException:
        tmp.unlink(missing_ok=True)
        raise


def _gate_manager(manager: str) -> None:
    """Friendly typed error when the manager binary is missing (D-12)."""
    binary = _LAUNCHCTL if manager == LAUNCHD_MANAGER else _SYSTEMCTL
    if shutil.which(binary) is None:
        raise ServiceManagerMissing(manager)


def _run(runner: Runner, argv: list[str]) -> subprocess.CompletedProcess[Any]:
    """Invoke a manager binary with an explicit argv list (D-12, never a shell)."""
    return runner(argv, capture_output=True, text=True, check=False)


def _detail(result: subprocess.CompletedProcess[Any]) -> str:
    """The manager's own words for a failure (stderr preferred)."""
    return (result.stderr or result.stdout or "no output").strip()


def _resolved_dest(dest_dir: str | Path | None, filename: str, default: Path) -> Path:
    return Path(dest_dir) / filename if dest_dir is not None else default


def install_watch_service(  # noqa: PLR0913 — the plan-specified signature: keyword seams for tests
    db_path: str | Path,
    argv_tail: list[str],
    *,
    manager: str,
    label: str = SERVICE_LABEL,
    python: str | None = None,
    dest_dir: str | Path | None = None,
    log_dir: str | Path | None = None,
    runner: Runner = subprocess.run,
) -> InstallResult:
    """Generate, write, enable, start, and verify the watch service (D-12).

    Never forks and never shells out: the artifact runs the FOREGROUND
    ``sif watch`` under the supervisor (SC3), and every manager call is an
    explicit argv list. Returns the artifact path, the log location, and a
    verify command for the CLI to print.
    """
    _gate_manager(manager)
    interpreter = python if python is not None else sys.executable
    if manager == LAUNCHD_MANAGER:
        return _install_launchd(
            db_path,
            argv_tail,
            interpreter=interpreter,
            label=label,
            dest_dir=dest_dir,
            log_dir=log_dir,
            runner=runner,
        )
    if manager == SYSTEMD_MANAGER:
        return _install_systemd(
            db_path, argv_tail, interpreter=interpreter, dest_dir=dest_dir, runner=runner
        )
    raise ValueError(f"unknown service manager: {manager!r}")


def _install_launchd(  # noqa: PLR0913
    db_path: str | Path,
    argv_tail: list[str],
    *,
    interpreter: str,
    label: str,
    dest_dir: str | Path | None,
    log_dir: str | Path | None,
    runner: Runner,
) -> InstallResult:
    """Write the plist, then bootstrap gui/<uid> with conflict retry.

    A conflicting bootstrap (an already-booted label) is booted out and
    retried (Pitfall 5), and the install is verified with launchctl print.
    """
    logs = Path(log_dir) if log_dir is not None else Path(user_log_dir("sif"))
    logs.mkdir(parents=True, exist_ok=True)
    plist = build_plist(interpreter, db_path, argv_tail, logs, label=label)
    dest = _resolved_dest(dest_dir, f"{label}.plist", launchd_plist_path(label))
    _write_artifact(dest, plistlib.dumps(plist, sort_keys=True))

    domain = f"gui/{os.getuid()}"
    bootstrap = [_LAUNCHCTL, "bootstrap", domain, str(dest)]
    result = _run(runner, bootstrap)
    if result.returncode != 0:
        # Pitfall 5: an already-booted label conflicts — boot out, then retry,
        # so a re-install never leaves partial/stale service state (T-13-13).
        logger.info(
            "launchctl bootstrap conflicted (%s); booting out %s/%s and retrying",
            _detail(result),
            domain,
            label,
        )
        _run(runner, [_LAUNCHCTL, "bootout", f"{domain}/{label}"])
        result = _run(runner, bootstrap)
        if result.returncode != 0:
            raise ServiceCommandError(bootstrap, _detail(result))
    verify = [_LAUNCHCTL, "print", f"{domain}/{label}"]
    verified = _run(runner, verify)
    if verified.returncode != 0:
        raise ServiceCommandError(verify, _detail(verified))
    return InstallResult(
        artifact_path=dest,
        log_location=str(logs / f"{_LOG_BASENAME}.log"),
        verify_command=" ".join(verify),
    )


def _install_systemd(
    db_path: str | Path,
    argv_tail: list[str],
    *,
    interpreter: str,
    dest_dir: str | Path | None,
    runner: Runner,
) -> InstallResult:
    """Write the unit, daemon-reload, enable --now, verify with is-active (D-12)."""
    unit = render_unit(interpreter, db_path, argv_tail)
    dest = _resolved_dest(dest_dir, UNIT_NAME, systemd_unit_path())
    _write_artifact(dest, unit.encode("utf-8"))

    reload_argv = [_SYSTEMCTL, "--user", "daemon-reload"]
    result = _run(runner, reload_argv)
    if result.returncode != 0:
        raise ServiceCommandError(reload_argv, _detail(result))
    enable_argv = [_SYSTEMCTL, "--user", "enable", "--now", UNIT_BASENAME]
    result = _run(runner, enable_argv)
    if result.returncode != 0:
        raise ServiceCommandError(enable_argv, _detail(result))
    verify = [_SYSTEMCTL, "--user", "is-active", UNIT_BASENAME]
    result = _run(runner, verify)
    if result.returncode != 0:
        raise ServiceCommandError(verify, _detail(result))
    return InstallResult(
        artifact_path=dest,
        log_location=f"journalctl --user -u {UNIT_BASENAME} -f",
        verify_command=f"systemctl --user status {UNIT_BASENAME}",
    )


def uninstall_watch_service(
    *,
    manager: str,
    label: str = SERVICE_LABEL,
    dest_dir: str | Path | None = None,
    runner: Runner = subprocess.run,
) -> Path:
    """Stop the service, then remove the artifact (D-11/D-12 stop-then-remove).

    launchd: bootout gui/<uid>/<label>, then unlink. systemd: disable --now,
    unlink, daemon-reload. A service that is not loaded is not an error —
    the artifact is still removed so uninstall is idempotent.
    """
    _gate_manager(manager)
    if manager == LAUNCHD_MANAGER:
        dest = _resolved_dest(dest_dir, f"{label}.plist", launchd_plist_path(label))
        # Not-loaded is fine (uninstall after a failed install must succeed).
        _run(runner, [_LAUNCHCTL, "bootout", f"gui/{os.getuid()}/{label}"])
        dest.unlink(missing_ok=True)
        return dest
    if manager == SYSTEMD_MANAGER:
        dest = _resolved_dest(dest_dir, UNIT_NAME, systemd_unit_path())
        _run(runner, [_SYSTEMCTL, "--user", "disable", "--now", UNIT_BASENAME])
        dest.unlink(missing_ok=True)
        reload_argv = [_SYSTEMCTL, "--user", "daemon-reload"]
        result = _run(runner, reload_argv)
        if result.returncode != 0:
            raise ServiceCommandError(reload_argv, _detail(result))
        return dest
    raise ValueError(f"unknown service manager: {manager!r}")
