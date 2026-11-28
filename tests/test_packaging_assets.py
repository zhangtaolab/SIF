"""Static guards: no GGUF weights are shipped or committed (CTR-03).

The LFM3 GGUF is an optional, user-supplied experiment arm. It must never be
packaged into the wheel/sdist, copied under ``src/sif``, or committed to the
repository, so these guards fail the suite if any of those boundaries is
crossed. They inspect only tracked files, so a user's local model directory
outside the repository cannot affect them.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]


def test_no_gguf_files_under_src() -> None:
    """No model weights live under the package source tree."""
    gguf = sorted(
        str(path.relative_to(REPO_ROOT)) for path in (REPO_ROOT / "src/sif").rglob("*.gguf")
    )
    assert gguf == [], f"GGUF weights must not live under src/sif: {gguf}"


def test_pyproject_ships_no_gguf() -> None:
    """The build configuration must not declare or include any ``.gguf`` asset."""
    text = (REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    assert ".gguf" not in text.lower(), "pyproject.toml must not reference .gguf assets"


def test_repo_root_has_no_committed_gguf() -> None:
    """No GGUF file is tracked; a local untracked model is out of scope."""
    if shutil.which("git") is None:
        pytest.skip("git not available")
    completed = subprocess.run(
        ["git", "ls-files", "--", "*.gguf"],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    assert completed.stdout.strip() == "", (
        f"GGUF weights must never be committed: {completed.stdout.strip()}"
    )
