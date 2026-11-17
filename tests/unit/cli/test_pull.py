"""Tests for the deprecated hidden ``sif pull`` alias."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from click.testing import CliRunner

from sif.cli.commands.pull import pull_cmd
from sif.config.settings import get_settings


class _FakeResponse:
    """Minimal urlopen response stand-in that yields fixed chunks."""

    def __init__(self, chunks: list[bytes]) -> None:
        self._chunks = list(chunks)

    def __enter__(self) -> _FakeResponse:
        return self

    def __exit__(self, *exc_info: object) -> bool:
        return False

    def read(self, _size: int) -> bytes:
        return self._chunks.pop(0) if self._chunks else b""


class TestPullCommand:
    """Tests for pull_cmd."""

    def test_pull_is_hidden(self) -> None:
        assert pull_cmd.hidden is True

    def test_pull_hf_success(self, tmp_path: Path) -> None:
        """Successful HuggingFace download."""
        runner = CliRunner()
        cache_dir = str(tmp_path / "models")
        fake_path = str(tmp_path / "models" / "model.gguf")
        Path(fake_path).parent.mkdir(parents=True, exist_ok=True)
        Path(fake_path).write_text("gguf")

        with patch(
            "sif.cli.commands.pull.hf_hub_download",
            return_value=fake_path,
        ) as mock_hf:
            result = runner.invoke(
                pull_cmd,
                ["--cache-dir", cache_dir, "owner/repo/model.gguf"],
            )

        assert result.exit_code == 0
        assert result.stdout.strip() == f"owner/repo/model.gguf: {fake_path}"
        assert "deprecated" in result.stderr
        mock_hf.assert_called_once_with(
            repo_id="owner/repo",
            filename="model.gguf",
            cache_dir=cache_dir,
            local_files_only=False,
        )

    def test_pull_hf_falls_back_to_modelscope(self, tmp_path: Path) -> None:
        """HF failure falls back to ModelScope."""
        runner = CliRunner()
        cache_dir = str(tmp_path / "models")
        ms_dir = tmp_path / "models" / "ms_model"
        ms_dir.mkdir(parents=True, exist_ok=True)
        (ms_dir / "model.gguf").write_text("gguf")

        with (
            patch(
                "sif.cli.commands.pull.hf_hub_download",
                side_effect=Exception("HF down"),
            ),
            patch(
                "sif.cli.commands.pull.snapshot_download",
                return_value=str(ms_dir),
            ) as mock_ms,
        ):
            result = runner.invoke(
                pull_cmd,
                ["--cache-dir", cache_dir, "owner/repo/model.gguf"],
            )

        assert result.exit_code == 0
        assert "HuggingFace failed" in result.stderr
        assert "Trying ModelScope fallback" in result.stderr
        assert "model.gguf" in result.stdout
        mock_ms.assert_called_once()

    def test_pull_url_direct_download(self, tmp_path: Path) -> None:
        """Direct URL download uses a bounded, streamed urlopen."""
        runner = CliRunner()
        cache_dir = str(tmp_path / "models")

        with patch(
            "sif.cli.commands.pull.request.urlopen",
            return_value=_FakeResponse([b"gguf", b""]),
        ) as mock_open:
            result = runner.invoke(
                pull_cmd,
                [
                    "--cache-dir",
                    cache_dir,
                    "https://example.com/model.gguf",
                ],
            )

        assert result.exit_code == 0
        mock_open.assert_called_once_with("https://example.com/model.gguf", timeout=60)
        assert (Path(cache_dir) / "model.gguf").read_bytes() == b"gguf"
        assert result.stdout.strip().startswith("https://example.com/model.gguf: ")
        assert result.stdout.strip().endswith("model.gguf")

    def test_pull_url_rejects_empty_download(self, tmp_path: Path) -> None:
        """An empty URL download is rejected."""
        runner = CliRunner()
        with patch(
            "sif.cli.commands.pull.request.urlopen",
            return_value=_FakeResponse([]),
        ):
            result = runner.invoke(
                pull_cmd,
                ["--cache-dir", str(tmp_path / "models"), "https://example.com/empty.gguf"],
            )

        assert result.exit_code != 0
        assert "missing or empty" in result.stderr

    def test_pull_url_failure_is_click_exception(self, tmp_path: Path) -> None:
        """Network failures surface as ClickException without a traceback."""
        runner = CliRunner()
        with patch(
            "sif.cli.commands.pull.request.urlopen",
            side_effect=TimeoutError("timed out"),
        ):
            result = runner.invoke(
                pull_cmd,
                ["--cache-dir", str(tmp_path / "models"), "https://example.com/slow.gguf"],
            )

        assert result.exit_code != 0
        assert "Download failed: timed out" in result.stderr
        assert "Traceback" not in result.stderr

    def test_pull_registry_name_delegates(self, tmp_path: Path) -> None:
        """``sif pull embedding`` delegates to the models pull handler."""
        runner = CliRunner()
        expected_id = get_settings().model_name
        fake_path = Path("/cache/Qwen/Qwen3-Embedding-0.6B")

        with patch(
            "sif.cli.commands.pull.download_model",
            return_value=fake_path,
        ) as mock_download:
            result = runner.invoke(
                pull_cmd,
                ["--cache-dir", str(tmp_path), "embedding"],
            )

        assert result.exit_code == 0, result.output
        mock_download.assert_called_once_with(
            expected_id,
            force=False,
            cache_dir=str(tmp_path),
        )
        assert result.stdout.strip() == f"{expected_id}: {fake_path}"
        assert "deprecated" in result.stderr
        assert "deprecated" not in result.stdout

    def test_pull_modelscope_id_delegates(self, tmp_path: Path) -> None:
        """A single-slash ModelScope id delegates to the models handler."""
        fake_path = Path("/cache/acme/encoder")
        with patch(
            "sif.cli.commands.pull.download_model",
            return_value=fake_path,
        ) as mock_download:
            result = CliRunner().invoke(
                pull_cmd,
                ["--cache-dir", str(tmp_path), "acme/encoder"],
            )

        assert result.exit_code == 0, result.output
        mock_download.assert_called_once_with(
            "acme/encoder",
            force=False,
            cache_dir=str(tmp_path),
        )

    def test_pull_invalid_spec(self) -> None:
        """Invalid model spec shows error."""
        runner = CliRunner()
        result = runner.invoke(pull_cmd, ["invalid_spec"])

        assert result.exit_code != 0
        assert "must be owner/repo/filename.gguf or a direct URL" in result.stderr

    def test_pull_empty_file(self, tmp_path: Path) -> None:
        """Empty downloaded file is rejected."""
        runner = CliRunner()
        cache_dir = str(tmp_path / "models")
        fake_path = str(tmp_path / "models" / "model.gguf")
        Path(fake_path).parent.mkdir(parents=True, exist_ok=True)
        Path(fake_path).write_text("")

        with patch(
            "sif.cli.commands.pull.hf_hub_download",
            return_value=fake_path,
        ):
            result = runner.invoke(
                pull_cmd,
                ["--cache-dir", cache_dir, "owner/repo/model.gguf"],
            )

        assert result.exit_code != 0
        assert "missing or empty" in result.stderr

    def test_pull_modelscope_not_installed(self, tmp_path: Path) -> None:
        """ModelScope ImportError is reported cleanly."""
        runner = CliRunner()
        cache_dir = str(tmp_path / "models")

        with (
            patch(
                "sif.cli.commands.pull.hf_hub_download",
                side_effect=Exception("HF down"),
            ),
            patch(
                "sif.cli.commands.pull.snapshot_download",
                side_effect=ImportError("No modelscope"),
            ),
        ):
            result = runner.invoke(
                pull_cmd,
                ["--cache-dir", cache_dir, "owner/repo/model.gguf"],
            )

        assert result.exit_code != 0
        assert "ModelScope not installed" in result.stderr
