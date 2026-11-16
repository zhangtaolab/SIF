"""Plugin, marketplace, MCP-config, and skill invariants (Phase 22 MCP-08).

Structural checks only: the manifests are JSON assets and the skills are
Markdown assets. ``claude plugin validate`` is the authoritative schema check
and runs as an optional gate when the CLI is installed.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from sif._version import __version__


PROJECT_ROOT = Path(__file__).resolve().parents[3]
PLUGIN_DIR = PROJECT_ROOT / ".claude-plugin"
PLUGIN_MANIFEST = PLUGIN_DIR / "plugin.json"
MARKETPLACE_MANIFEST = PLUGIN_DIR / "marketplace.json"
MCP_CONFIG = PROJECT_ROOT / ".mcp.json"
SKILLS_DIR = PROJECT_ROOT / "skills"
SKILL_NAMES = ("sif-search", "sif-get", "sif-cite")


def _load_json(path: Path) -> dict[str, Any]:
    """Parse a JSON manifest, failing the test with the path in the message."""
    return json.loads(path.read_text(encoding="utf-8"))


def _skill_text(name: str) -> str:
    """Return the skill body, failing if the skill file is missing."""
    path = SKILLS_DIR / name / "SKILL.md"
    assert path.is_file(), f"missing skill file: {path}"
    return path.read_text(encoding="utf-8")


class TestManifests:
    """The repo root is a valid plugin and marketplace named ``sif``."""

    def test_manifests_parse(self) -> None:
        """All three JSON assets parse as objects."""
        for path in (PLUGIN_MANIFEST, MARKETPLACE_MANIFEST, MCP_CONFIG):
            assert isinstance(_load_json(path), dict), f"{path} is not a JSON object"

    def test_manifest_plugin_identity(self) -> None:
        """The plugin manifest names ``sif`` with a one-line description."""
        plugin = _load_json(PLUGIN_MANIFEST)
        assert plugin["name"] == "sif"
        assert plugin["description"]
        assert "\n" not in plugin["description"]
        assert plugin["license"] == "MIT"
        assert plugin["author"]["name"]

    def test_manifest_marketplace_identity(self) -> None:
        """The marketplace names ``sif``, sources ``./``, and describes itself."""
        marketplace = _load_json(MARKETPLACE_MANIFEST)
        assert marketplace["name"] == "sif"
        assert marketplace["description"], "top-level marketplace description is required (C4)"
        assert "\n" not in marketplace["description"]
        assert marketplace["owner"]["name"]

        plugins = marketplace["plugins"]
        assert isinstance(plugins, list)
        assert plugins
        entry = plugins[0]
        assert entry["name"] == "sif"
        assert entry["source"] == "./"
        assert entry["description"], "the plugin entry keeps its own description"

    def test_manifest_version_parity(self) -> None:
        """Plugin and marketplace versions mirror ``src/sif/_version.py``."""
        plugin = _load_json(PLUGIN_MANIFEST)
        marketplace = _load_json(MARKETPLACE_MANIFEST)
        assert plugin["version"] == __version__
        assert marketplace["plugins"][0]["version"] == __version__

    @pytest.mark.parametrize("manifest", [PLUGIN_MANIFEST, MARKETPLACE_MANIFEST])
    def test_manifest_names_carry_no_vendor_prefix(self, manifest: Path) -> None:
        """Plugin/marketplace names never claim vendor ownership."""
        name = _load_json(manifest)["name"]
        assert name == "sif"
        assert not name.startswith(("claude-", "anthropic-"))


class TestMcpJson:
    """The root ``.mcp.json`` runs the installed server with no local paths."""

    def test_mcp_json_runs_installed_stdio_server(self) -> None:
        """Exactly one ``sif`` server running ``sif mcp stdio``."""
        config = _load_json(MCP_CONFIG)
        assert config == {"mcpServers": {"sif": {"command": "sif", "args": ["mcp", "stdio"]}}}

    def test_mcp_json_has_no_paths_or_secrets(self) -> None:
        """No hardcoded database path, env block, or credential-like key."""
        raw = MCP_CONFIG.read_text(encoding="utf-8")
        for forbidden in ("SIF_DB_PATH", "api_key", "apiKey", "token", "password"):
            assert forbidden not in raw, f".mcp.json must not contain {forbidden}"
        config = _load_json(MCP_CONFIG)
        server = config["mcpServers"]["sif"]
        assert "env" not in server
        assert "disabled" not in server
