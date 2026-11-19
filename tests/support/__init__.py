"""Shared test support package for bench fixtures and filesystem helpers."""

from __future__ import annotations

from pathlib import Path

import pytest


def symlink_or_skip(link: Path, target: Path, *, target_is_directory: bool = False) -> None:
    """Create a symlink, or skip the calling test when the host forbids it.

    Skips are per call site (never module-wide), so a privileged Windows host
    with Developer Mode or an elevated shell still runs the test.

    Args:
        link: The symlink path to create.
        target: The path the symlink points at.
        target_is_directory: Whether ``target`` is a directory; Windows needs
            the hint and POSIX ignores it.

    Raises:
        pytest.skip.Exception: The host cannot create symlinks (Windows
            without Developer Mode or elevation reports WinError 1314).
    """
    try:
        link.symlink_to(target, target_is_directory=target_is_directory)
    except (NotImplementedError, OSError) as exc:
        pytest.skip(
            "symlink creation is unavailable on this host (Windows requires "
            f"Developer Mode or elevation; WinError 1314): {exc}"
        )
