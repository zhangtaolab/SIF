"""Regression tests pinning the release metadata surfaces (ENG-03)."""

from __future__ import annotations

import runpy
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
README = REPO_ROOT / "README.md"
CHANGELOG = REPO_ROOT / "docs" / "changelog.md"
VERSION_MODULE = REPO_ROOT / "src" / "sif" / "_version.py"
PYPROJECT = REPO_ROOT / "pyproject.toml"

MCP_NAME_MARKER = "<!-- mcp-name: io.github.zhangtaolab/sif -->"


def test_readme_has_mcp_name_marker() -> None:
    """The Registry ownership marker is one complete README line, no trailing period."""
    lines = README.read_text(encoding="utf-8").splitlines()
    assert MCP_NAME_MARKER in lines, "README is missing the exact mcp-name marker line"


def test_changelog_has_1_1_2() -> None:
    """The changelog records 1.1.2 and its compare/release links."""
    text = CHANGELOG.read_text(encoding="utf-8")
    assert "## [1.1.2]" in text
    assert "[1.1.2]:" in text
    assert "compare/v1.1.2...HEAD" in text


def test_version_literal_is_1_1_2() -> None:
    """The single version literal the publish tag gate reads is 1.1.2."""
    version = runpy.run_path(str(VERSION_MODULE))["__version__"]
    assert version == "1.1.2"


def test_pyproject_readme_is_readme_md() -> None:
    """hatchling bakes README.md into the PyPI description at build time."""
    text = PYPROJECT.read_text(encoding="utf-8")
    assert 'readme = "README.md"' in text
