"""OS service-manager install/uninstall for the watch host (Phase 13, SC3).

``sif watch --install-service`` generates a launchd LaunchAgent (macOS) or a
systemd user unit (Linux) whose argv runs the FOREGROUND ``sif watch`` with
the install-time flags baked in — the supervised process never forks
(SC3/D-11); ``--detach`` is a deliberately distinct path (D-06). Generation
is pure text (plistlib for the plist, a fixed template for the unit) so both
artifacts are built and asserted on ANY platform (D-13); live manager
invocation happens only where the manager exists.

Every manager invocation is an explicit argv list — never ``shell=True``,
never a string command line (D-12, T-13-10). Artifacts are written
atomically with mode 0644 into user-owned directories, and only our own
label's filename is ever written or removed (T-13-11).

This is the RED-phase skeleton: importable, zero behavior — the failing
tests in tests/unit/utils/test_service.py define the contract.
"""

from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path

SERVICE_LABEL = "com.docsif.watch"
UNIT_NAME = "sif-watch.service"


class ServiceManagerMissing(RuntimeError):
    """The platform's service-manager binary is not on PATH (friendly remedy)."""


class ServiceCommandError(RuntimeError):
    """A service-manager invocation failed; carries the failing argv + detail."""


@dataclass(frozen=True)
class InstallResult:
    """What the installer hands the CLI so it can point the user at everything."""

    artifact_path: Path
    log_location: str
    verify_command: str


def build_plist(
    python: str,
    db_path: str | Path,
    argv_tail: list[str],
    log_dir: str | Path,
    *,
    label: str = SERVICE_LABEL,
) -> dict[str, object]:
    """Build the launchd LaunchAgent definition (D-13 keys) as a plist dict."""
    return {}


def render_unit(python: str, db_path: str | Path, argv_tail: list[str]) -> str:
    """Render the systemd user unit (D-13 keys) as text."""
    return ""


def launchd_plist_path(label: str = SERVICE_LABEL) -> Path:
    """The LaunchAgent destination: ~/Library/LaunchAgents/<label>.plist."""
    raise NotImplementedError


def systemd_unit_path() -> Path:
    """The user-unit destination: ~/.config/systemd/user/<UNIT_NAME>."""
    raise NotImplementedError


def install_watch_service(
    db_path: str | Path,
    argv_tail: list[str],
    *,
    manager: str,
    label: str = SERVICE_LABEL,
    python: str | None = None,
    dest_dir: str | Path | None = None,
    log_dir: str | Path | None = None,
    runner: object = None,
) -> InstallResult:
    """Generate, write, enable, start, and verify the watch service (D-12)."""
    raise NotImplementedError


def uninstall_watch_service(
    *,
    manager: str,
    label: str = SERVICE_LABEL,
    dest_dir: str | Path | None = None,
    runner: object = None,
) -> Path:
    """Stop the service, then remove the artifact (D-11/D-12 stop-then-remove)."""
    raise NotImplementedError
