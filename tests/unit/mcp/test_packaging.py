"""Runtime-dependency gate for the MCP SDK adoption (Phase 22 D-03).

The runtime list is frozen at 13 entries: the 12 pre-phase dependencies plus
``mcp>=2.3.0,<3``. Any additional runtime entry fails the gate, and the two
legacy extras stay thin uvicorn-only compatibility aliases. ``mcp-types`` is
transitive and must never be declared directly.
"""

from __future__ import annotations

import re
from pathlib import Path


PYPROJECT = Path(__file__).resolve().parents[3] / "pyproject.toml"
_EXPECTED_RUNTIME_ENTRIES = 12  # pre-phase count, plus mcp below

_MCP_DEPENDENCY = "mcp>=2.3.0,<3"
_UVICORN_ALIAS = ["uvicorn>=0.20.0"]


def _section(text: str, name: str) -> str:
    """Return the body of one TOML section (text parsing, no tomllib on 3.10)."""
    match = re.search(
        rf"^\[{re.escape(name)}\]\s*$(.*?)(?=^\[|\Z)",
        text,
        re.MULTILINE | re.DOTALL,
    )
    assert match is not None, f"missing [{name}] section in pyproject.toml"
    return match.group(1)


def _array(section: str, key: str) -> list[str]:
    """Extract the quoted entries of one ``key = [...]`` array."""
    match = re.search(
        rf"^{re.escape(key)}\s*=\s*\[(.*?)\]",
        section,
        re.MULTILINE | re.DOTALL,
    )
    assert match is not None, f"missing {key} array"
    return re.findall(r'"([^"]*)"', match.group(1))


def _dependencies() -> list[str]:
    return _array(_section(PYPROJECT.read_text(encoding="utf-8"), "project"), "dependencies")


def _extras() -> str:
    return _section(PYPROJECT.read_text(encoding="utf-8"), "project.optional-dependencies")


def test_runtime_dependency_list_is_frozen_at_thirteen_entries() -> None:
    """Freezing the count makes any additional runtime entry fail the gate."""
    assert len(_dependencies()) == _EXPECTED_RUNTIME_ENTRIES + 1


def test_only_mcp_was_added_and_mcp_types_is_never_declared() -> None:
    """The sole mcp-named runtime entry is exactly the locked pin."""
    dependencies = _dependencies()

    assert [entry for entry in dependencies if entry.startswith("mcp")] == [_MCP_DEPENDENCY]
    assert not any("mcp-types" in entry for entry in dependencies)


def test_mcp_and_http_extras_stay_uvicorn_only_aliases() -> None:
    """Both legacy extras remain installable with exactly the old contents."""
    extras = _extras()

    assert _array(extras, "mcp") == _UVICORN_ALIAS
    assert _array(extras, "http") == _UVICORN_ALIAS
