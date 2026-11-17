"""Tests for the models CLI group (pull)."""

from __future__ import annotations

from collections.abc import Generator
from pathlib import Path
from unittest.mock import patch

import pytest
from click.testing import CliRunner, Result

from sif.cli.main import cli
from sif.config.settings import get_settings
from sif.models.download import DEFAULT_MODELS


@pytest.fixture(autouse=True)
def _isolated_settings(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Generator[None]:
    """Keep Settings off the real user cache, DB, and env-derived defaults."""
    monkeypatch.setenv("SIF_CACHE_DIR", str(tmp_path / "cache"))
    monkeypatch.setenv("SIF_DB_PATH", str(tmp_path / "index.db"))
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def _invoke(args: list[str]) -> Result:
    """Invoke the top-level CLI group in-process."""
    return CliRunner().invoke(cli, args)


class TestModelsPull:
    """Tests for ``sif models pull``."""

    def test_no_argument_uses_configured_embedder(self) -> None:
        fake_path = Path("/cache/Qwen/Qwen3-Embedding-0.6B")
        with patch("sif.cli.commands.models.ModelDownloader") as mock_cls:
            mock_cls.return_value.download.return_value = fake_path
            result = _invoke(["models", "pull"])

        assert result.exit_code == 0, result.output
        args, kwargs = mock_cls.return_value.download.call_args
        assert args[0] == get_settings().model_name
        assert kwargs["force"] is False
        mock_cls.assert_called_once_with(cache_dir=None)
        assert result.output.strip() == f"{get_settings().model_name}: {fake_path}"

    def test_embedding_name_uses_configured_embedder(self) -> None:
        with patch("sif.cli.commands.models.ModelDownloader") as mock_cls:
            mock_cls.return_value.download.return_value = Path("/cache/embed")
            result = _invoke(["models", "pull", "embedding"])

        assert result.exit_code == 0, result.output
        assert mock_cls.return_value.download.call_args.args[0] == get_settings().model_name

    def test_reranker_name_uses_configured_reranker(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setenv("SIF_RERANKER_MODEL_NAME", "Qwen/Custom-Reranker")
        get_settings.cache_clear()
        with patch("sif.cli.commands.models.ModelDownloader") as mock_cls:
            mock_cls.return_value.download.return_value = Path("/cache/rerank")
            result = _invoke(["models", "pull", "reranker"])

        assert result.exit_code == 0, result.output
        assert mock_cls.return_value.download.call_args.args[0] == "Qwen/Custom-Reranker"

    def test_query_expansion_uses_registry_default(self) -> None:
        expected = DEFAULT_MODELS["query_expansion"]["model_id"]
        with patch("sif.cli.commands.models.ModelDownloader") as mock_cls:
            mock_cls.return_value.download.return_value = Path("/cache/qe")
            result = _invoke(["models", "pull", "query_expansion"])

        assert result.exit_code == 0, result.output
        assert mock_cls.return_value.download.call_args.args[0] == expected

    def test_owner_name_modelscope_id_is_accepted(self) -> None:
        with patch("sif.cli.commands.models.ModelDownloader") as mock_cls:
            mock_cls.return_value.download.return_value = Path("/cache/custom")
            result = _invoke(["models", "pull", "acme/encoder"])

        assert result.exit_code == 0, result.output
        assert mock_cls.return_value.download.call_args.args[0] == "acme/encoder"

    def test_unknown_target_fails_with_accepted_values(self) -> None:
        result = _invoke(["models", "pull", "not-a-model"])

        assert result.exit_code != 0
        assert "Unknown model target 'not-a-model'" in result.output
        assert "embedding" in result.output
        assert "reranker" in result.output
        assert "query_expansion" in result.output
        assert "owner/name" in result.output

    def test_force_is_forwarded(self) -> None:
        with patch("sif.cli.commands.models.ModelDownloader") as mock_cls:
            mock_cls.return_value.download.return_value = Path("/cache/forced")
            result = _invoke(["models", "pull", "--force"])

        assert result.exit_code == 0, result.output
        assert mock_cls.return_value.download.call_args.kwargs["force"] is True

    def test_cache_dir_reaches_downloader(self, tmp_path: Path) -> None:
        custom = tmp_path / "custom-cache"
        with patch("sif.cli.commands.models.ModelDownloader") as mock_cls:
            mock_cls.return_value.download.return_value = Path("/cache/x")
            result = _invoke(["models", "pull", "--cache-dir", str(custom)])

        assert result.exit_code == 0, result.output
        mock_cls.assert_called_once_with(cache_dir=str(custom))

    def test_missing_modelscope_becomes_click_exception(self) -> None:
        message = "modelscope is required to download models; install the embed extra"
        with patch("sif.cli.commands.models.ModelDownloader") as mock_cls:
            mock_cls.return_value.download.side_effect = ImportError(message)
            result = _invoke(["models", "pull"])

        assert result.exit_code != 0
        assert message in result.output
        assert "Traceback" not in result.output

    def test_os_error_becomes_click_exception(self) -> None:
        with patch("sif.cli.commands.models.ModelDownloader") as mock_cls:
            mock_cls.return_value.download.side_effect = OSError("disk full")
            result = _invoke(["models", "pull"])

        assert result.exit_code != 0
        assert "disk full" in result.output
        assert "Traceback" not in result.output

    def test_non_tty_output_is_one_plain_line(self) -> None:
        fake_path = Path("/cache/plain/model")
        with patch("sif.cli.commands.models.ModelDownloader") as mock_cls:
            mock_cls.return_value.download.return_value = fake_path
            result = _invoke(["models", "pull"])

        assert result.exit_code == 0, result.output
        lines = result.stdout.strip().splitlines()
        assert len(lines) == 1, lines
        assert lines[0].endswith(str(fake_path))
        assert "─" not in result.stdout
        assert "│" not in result.stdout

    def test_models_help_lists_pull_and_status(self) -> None:
        result = _invoke(["models", "--help"])

        assert result.exit_code == 0, result.output
        assert "pull" in result.output
        assert "status" in result.output
