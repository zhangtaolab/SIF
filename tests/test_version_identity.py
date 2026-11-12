"""Regression tests pinning the single-sourced release version identity."""

from __future__ import annotations

import re
from pathlib import Path

from click.testing import CliRunner

import sif
import sif.cli
from sif import _version
from sif.cli.main import cli
from sif.config.constants import APP_VERSION
from sif.mcp.protocol import InitializeResult


try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - Python 3.10 has no tomllib
    tomllib = None

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src" / "sif"
PYPROJECT = REPO_ROOT / "pyproject.toml"
VERSION_RE = re.compile(r"\d+\.\d+\.\d+")


def _section(text: str, name: str) -> str:
    """Return the raw TOML text of a table section (fallback parser helper)."""
    header = re.compile(rf"^\[{re.escape(name)}\]\s*$", re.MULTILINE).search(text)
    assert header is not None, f"missing [{name}] section in pyproject.toml"
    start = header.end()
    next_header = re.compile(r"^\[", re.MULTILINE).search(text, start)
    end = next_header.start() if next_header is not None else len(text)
    return text[start:end]


def test_pyproject_declares_dynamic_version_from_module() -> None:
    """Packaging takes its version from src/sif/_version.py, not a static key."""
    text = PYPROJECT.read_text(encoding="utf-8")

    if tomllib is None:  # pragma: no cover - Python 3.10 fallback
        project = _section(text, "project")
        assert 'dynamic = ["version"]' in project
        assert re.search(r"^version\s*=", project, re.MULTILINE) is None
        assert 'path = "src/sif/_version.py"' in _section(text, "tool.hatch.version")
        return

    data = tomllib.loads(text)
    assert data["project"]["dynamic"] == ["version"]
    assert "version" not in data["project"]
    assert data["tool"]["hatch"]["version"]["path"] == "src/sif/_version.py"


def test_runtime_version_surfaces_agree() -> None:
    """Every runtime surface derives from the same single literal."""
    surfaces = {
        "sif.__version__": sif.__version__,
        "sif._version.__version__": _version.__version__,
        "sif.cli.__version__": sif.cli.__version__,
        "APP_VERSION": APP_VERSION,
        "MCP serverInfo": InitializeResult().serverInfo["version"],
    }
    distinct = set(surfaces.values())
    assert len(distinct) == 1, f"version surfaces disagree: {surfaces}"
    assert VERSION_RE.fullmatch(next(iter(distinct))) is not None


def test_version_literal_is_single_sourced() -> None:
    """Only _version.py assigns a __version__ literal; APP_VERSION never does."""
    module_literal = re.compile(r'^__version__\s*=\s*["\']', re.MULTILINE)
    app_version_literal = re.compile(r'^APP_VERSION\s*=\s*["\']', re.MULTILINE)
    offenders: list[str] = []
    app_version_offenders: list[str] = []

    for module in sorted(SRC_ROOT.rglob("*.py")):
        text = module.read_text(encoding="utf-8")
        relative = str(module.relative_to(REPO_ROOT))
        if module_literal.search(text):
            offenders.append(relative)
        if app_version_literal.search(text):
            app_version_offenders.append(relative)

    expected = str((SRC_ROOT / "_version.py").relative_to(REPO_ROOT))
    assert offenders == [expected]
    assert app_version_offenders == []


def test_cli_version_option_uses_package_version() -> None:
    """`sif --version` prints the package version, not a hardcoded literal."""
    result = CliRunner().invoke(cli, ["--version"])
    assert result.exit_code == 0
    assert f"sif, version {sif.__version__}" in result.output
