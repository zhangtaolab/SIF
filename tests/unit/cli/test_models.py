"""Tests for the models CLI group (pull and status)."""

from __future__ import annotations

import json
import sqlite3
import sys
from collections.abc import Generator
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

import pytest
from click.testing import CliRunner, Result

from sif.cli.main import cli
from sif.config.settings import get_settings
from sif.embedding.identity import EmbedderIdentity, build_settings_identity
from sif.embedding.prompts import resolve_prompt_scheme
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


_IDENTITY_KEYS = {
    "status",
    "source",
    "stored_model_name",
    "stored_cache_model_id",
    "stored_dimension",
    "stored_fingerprint",
    "schema_dimension",
    "current_cache_model_id",
    "current_fingerprint",
}


def _current_identity() -> EmbedderIdentity:
    """Build the identity the status command builds from the test settings."""
    settings = get_settings()
    scheme = resolve_prompt_scheme(
        settings.model_name,
        settings.model_type,
        settings.query_prompt_name,
        settings.document_prompt_name,
    )
    return build_settings_identity(settings, scheme)


def _make_index(
    path: Path,
    *,
    stored_json: str | None = None,
    schema_dim: int = 1024,
) -> None:
    """Create a minimal index-shaped SQLite file for status to inspect."""
    conn = sqlite3.connect(path)
    try:
        conn.execute("CREATE TABLE index_meta (key TEXT PRIMARY KEY, value TEXT)")
        conn.execute(
            f"CREATE TABLE document_embeddings (document_id INTEGER, embedding FLOAT[{schema_dim}])"
        )
        if stored_json is not None:
            conn.execute(
                "INSERT INTO index_meta (key, value) VALUES (?, ?)",
                ("embedder.identity", stored_json),
            )
        conn.commit()
    finally:
        conn.close()


def _status_json(index_path: Path) -> dict[str, object]:
    """Invoke ``models status --json`` against ``index_path`` and parse it."""
    result = CliRunner().invoke(
        cli,
        ["--index", str(index_path), "models", "status", "--json"],
    )
    assert result.exit_code == 0, result.output
    assert result.exception is None, result.exception
    return json.loads(result.stdout)


class TestModelsStatusIdentity:
    """Identity states reported by ``sif models status``."""

    def test_no_index_reports_no_index(self, tmp_path: Path) -> None:
        index_path = tmp_path / "missing.db"
        payload = _status_json(index_path)
        identity = payload["identity"]
        assert identity["status"] == "no-index"
        assert identity["stored_fingerprint"] is None
        assert identity["source"] is None
        assert identity["schema_dimension"] is None
        assert str(identity["current_fingerprint"]).startswith("sha256:")
        assert not index_path.exists(), "status must never create the index"

    def test_index_without_identity_row_reports_no_identity(self, tmp_path: Path) -> None:
        index_path = tmp_path / "index.db"
        _make_index(index_path)
        identity = _status_json(index_path)["identity"]
        assert identity["status"] == "no-identity"
        assert identity["stored_fingerprint"] is None
        assert identity["stored_dimension"] is None
        assert identity["schema_dimension"] == 1024

    def test_matching_identity_reports_match(self, tmp_path: Path) -> None:
        current = _current_identity()
        index_path = tmp_path / "index.db"
        _make_index(index_path, stored_json=current.to_json())
        identity = _status_json(index_path)["identity"]
        assert identity["status"] == "match"
        assert identity["source"] == "verified"
        assert identity["stored_model_name"] == current.model_name
        assert identity["stored_cache_model_id"] == current.cache_model_id
        assert identity["stored_dimension"] == current.dimension
        assert str(identity["stored_fingerprint"]).startswith("sha256:")
        assert identity["stored_fingerprint"] == identity["current_fingerprint"]

    def test_model_mismatch_is_reported_exit_zero(self, tmp_path: Path) -> None:
        current = _current_identity()
        stored = replace(current, cache_model_id="other/encoder", model_name="other/encoder")
        index_path = tmp_path / "index.db"
        _make_index(index_path, stored_json=stored.to_json())
        result = CliRunner().invoke(
            cli,
            ["--index", str(index_path), "models", "status", "--json"],
        )
        identity = json.loads(result.stdout)["identity"]
        assert result.exit_code == 0, result.output
        assert identity["status"] == "mismatch"
        assert identity["stored_cache_model_id"] == "other/encoder"
        assert identity["stored_fingerprint"] != identity["current_fingerprint"]

    def test_stored_dimension_mismatch(self, tmp_path: Path) -> None:
        current = _current_identity()
        stored = replace(current, dimension=512)
        index_path = tmp_path / "index.db"
        _make_index(index_path, stored_json=stored.to_json(), schema_dim=1024)
        identity = _status_json(index_path)["identity"]
        assert identity["status"] == "dimension-mismatch"
        assert identity["stored_dimension"] == 512
        assert identity["schema_dimension"] == 1024

    def test_schema_width_mismatch(self, tmp_path: Path) -> None:
        current = _current_identity()
        index_path = tmp_path / "index.db"
        _make_index(index_path, stored_json=current.to_json(), schema_dim=512)
        identity = _status_json(index_path)["identity"]
        assert identity["status"] == "dimension-mismatch"
        assert identity["schema_dimension"] == 512

    def test_corrupt_identity_row_degrades_without_traceback(self, tmp_path: Path) -> None:
        index_path = tmp_path / "index.db"
        _make_index(index_path, stored_json="{not valid json")
        result = CliRunner().invoke(
            cli,
            ["--index", str(index_path), "models", "status", "--json"],
        )
        assert result.exit_code == 0, result.output
        assert result.exception is None, result.exception
        assert json.loads(result.stdout)["identity"]["status"] == "no-identity"


class TestModelsStatusPayload:
    """Payload shape, probe behavior, and rendering."""

    def test_json_has_fixed_sections_and_identity_keys(self, tmp_path: Path) -> None:
        payload = _status_json(tmp_path / "missing.db")
        assert list(payload) == [
            "backend",
            "cache",
            "identity",
            "settings",
            "vector_backend",
        ]
        assert set(payload["identity"]) == _IDENTITY_KEYS
        settings = payload["settings"]
        assert set(settings) == {
            "model_name",
            "model_type",
            "api_base",
            "dimension",
            "cache_dir",
        }
        cache = payload["cache"]
        assert set(cache) == {"path", "state", "revision"}
        assert payload["vector_backend"]["name"] == "sqlite_vec"

    def test_backend_probe_uses_find_spec_and_metadata(self, tmp_path: Path) -> None:
        before = set(sys.modules)
        with (
            patch("sif.cli.commands.models.importlib.util.find_spec") as mock_find,
            patch(
                "sif.cli.commands.models.importlib.metadata.version",
                return_value="1.2.3",
            ),
        ):
            mock_find.return_value = object()
            payload = _status_json(tmp_path / "missing.db")

        mock_find.assert_any_call("modelscope")
        mock_find.assert_any_call("sqlite_vec")
        assert payload["backend"] == {
            "name": "modelscope",
            "available": True,
            "version": "1.2.3",
        }
        assert payload["vector_backend"]["available"] is True
        assert payload["vector_backend"]["version"] == "1.2.3"
        backend_modules = {"sentence_transformers", "modelscope", "llama_cpp", "openai"}
        assert not (set(sys.modules) - before) & backend_modules

    def test_missing_backend_reports_unavailable(self, tmp_path: Path) -> None:
        with (
            patch(
                "sif.cli.commands.models.importlib.util.find_spec",
                return_value=None,
            ),
            patch("sif.cli.commands.models.importlib.metadata.version") as mock_version,
        ):
            payload = _status_json(tmp_path / "missing.db")

        assert payload["backend"]["available"] is False
        assert payload["backend"]["version"] is None
        assert payload["vector_backend"]["available"] is False
        mock_version.assert_not_called()

    def test_non_tty_output_is_plain_and_ordered(self) -> None:
        result = CliRunner().invoke(cli, ["models", "status"])
        assert result.exit_code == 0, result.output
        assert "─" not in result.stdout
        assert "│" not in result.stdout
        keys = [line.split(":", 1)[0] for line in result.stdout.splitlines()]
        assert keys[0] == "settings.model_name"
        assert keys.index("cache.path") > keys.index("settings.cache_dir")
        assert keys.index("backend.name") > keys.index("cache.revision")
        assert keys.index("vector_backend.name") > keys.index("backend.version")
        assert keys.index("identity.status") > keys.index("vector_backend.version")

    def test_tty_renders_table(self) -> None:
        with (
            patch("sif.cli.commands.models._stdout_is_tty", return_value=True),
            patch("sif.cli.commands.models.is_quiet", return_value=False),
        ):
            result = CliRunner().invoke(cli, ["models", "status"])

        assert result.exit_code == 0, result.output
        assert "─" in result.stdout
        assert "Model Status" in result.stdout

    def test_api_key_never_appears_in_output(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setenv("SIF_API_KEY", "super-secret-key")
        get_settings.cache_clear()

        plain = CliRunner().invoke(cli, ["models", "status"])
        as_json = CliRunner().invoke(cli, ["models", "status", "--json"])

        for output in (plain.stdout, as_json.stdout):
            assert "super-secret-key" not in output
            assert "SIF_API_KEY" not in output
