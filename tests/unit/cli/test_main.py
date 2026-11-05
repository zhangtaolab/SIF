"""Tests for the CLI main entry point (default index path, group-level guards)."""

from __future__ import annotations

import click
import pytest
from click.testing import CliRunner

from sif.cli.main import _get_default_db_path, cli
from sif.config.settings import get_settings


class TestDefaultDbPathConfigError:
    """WR-09: an invalid SIF_RERANKER_MODEL_TYPE must surface as a clean error.

    ``--index`` is omitted on almost every invocation, so Click evaluates the
    callable default ``_get_default_db_path`` during option parsing; without a
    guard the Settings validator would escape there as a raw pydantic
    traceback for every command. get_settings is lru_cache'd, so the cache
    must be cleared AFTER the env var is set (a prior cached success would
    mask it) and again afterwards for hygiene.
    """

    def test_get_default_db_path_wraps_validation_error(self, monkeypatch) -> None:
        """The callable default raises click.ClickException, not ValidationError."""
        monkeypatch.setenv("SIF_RERANKER_MODEL_TYPE", "cross-encoder")
        get_settings.cache_clear()
        try:
            with pytest.raises(click.ClickException, match="reranker_model_type"):
                _get_default_db_path()
        finally:
            get_settings.cache_clear()

    def test_group_command_renders_clean_error(self, monkeypatch) -> None:
        """Invoking the group without --index renders a one-line error, exit 1."""
        runner = CliRunner()
        monkeypatch.setenv("SIF_RERANKER_MODEL_TYPE", "cross-encoder")
        get_settings.cache_clear()
        try:
            result = runner.invoke(cli, ["status"])
        finally:
            get_settings.cache_clear()

        assert result.exit_code == 1
        assert "Error:" in result.output
        assert "reranker_model_type" in result.output
        assert "Traceback" not in result.output
