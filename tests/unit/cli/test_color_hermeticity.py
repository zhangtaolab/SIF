"""Regression tests pinning color-env hermeticity of the pytest suite.

The suite must reach the same verdicts regardless of ambient color-forcing
environment variables: every test starts with the forcing vars absent, and
CLI output stays plain even when a test forces color mid-test (module-level
Rich consoles must have been constructed without a cached color system).
"""

from __future__ import annotations

import os
from collections.abc import Generator
from pathlib import Path

import pytest
from click.testing import CliRunner

from sif.cli.main import cli
from sif.config.settings import get_settings


class TestColorEnvHermeticity:
    """Ambient color env vars must never leak into tests or style CLI output."""

    @pytest.fixture(autouse=True)
    def isolated_settings(self) -> Generator[None, None, None]:
        """Keep Settings dimensions and paths independent between tests."""
        get_settings.cache_clear()
        yield
        get_settings.cache_clear()

    def test_color_env_vars_absent_at_test_start(self) -> None:
        """No color-forcing variable may be present when a test body starts."""
        for name in ("FORCE_COLOR", "CLICOLOR_FORCE", "NO_COLOR", "PY_COLORS", "TTY_COMPATIBLE"):
            assert name not in os.environ, f"{name} leaked from the ambient environment"

    def test_cli_output_plain_when_color_forced_mid_test(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """Forcing color mid-test must not style output of the real CLI."""
        monkeypatch.setenv("FORCE_COLOR", "1")
        monkeypatch.setenv("CLICOLOR_FORCE", "1")

        result = CliRunner().invoke(
            cli,
            ["--index", str(tmp_path / "absent.db"), "status"],
            env={"COLUMNS": "200"},
        )

        assert result.exit_code == 0, result.output
        assert "No index found. Run 'sif index update' to create one." in result.output
        assert "\x1b" not in result.output, "CLI output contains ANSI escape sequences"
