"""Tests for the pull CLI command."""

from pathlib import Path
from unittest.mock import patch

from click.testing import CliRunner

from docsift.cli.commands.pull import pull_cmd


class TestPullCommand:
    """Tests for pull_cmd."""

    def test_pull_hf_success(self, tmp_path: Path) -> None:
        """Successful HuggingFace download."""
        runner = CliRunner()
        cache_dir = str(tmp_path / "models")
        fake_path = str(tmp_path / "models" / "model.gguf")
        Path(fake_path).parent.mkdir(parents=True, exist_ok=True)
        Path(fake_path).write_text("gguf")

        with patch(
            "docsift.cli.commands.pull.hf_hub_download",
            return_value=fake_path,
        ) as mock_hf:
            result = runner.invoke(
                pull_cmd,
                ["--cache-dir", cache_dir, "owner/repo/model.gguf"],
            )

        assert result.exit_code == 0
        assert "Downloaded to" in result.output
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
                "docsift.cli.commands.pull.hf_hub_download",
                side_effect=Exception("HF down"),
            ),
            patch(
                "docsift.cli.commands.pull.snapshot_download",
                return_value=str(ms_dir),
            ) as mock_ms,
        ):
            result = runner.invoke(
                pull_cmd,
                ["--cache-dir", cache_dir, "owner/repo/model.gguf"],
            )

        assert result.exit_code == 0
        assert "HuggingFace failed" in result.output
        assert "Trying ModelScope fallback" in result.output
        assert "model.gguf" in result.output
        mock_ms.assert_called_once()

    def test_pull_url_direct_download(self, tmp_path: Path) -> None:
        """Direct URL download path."""
        runner = CliRunner()
        cache_dir = str(tmp_path / "models")

        def fake_urlretrieve(_url: str, filename: Path) -> None:
            Path(filename).parent.mkdir(parents=True, exist_ok=True)
            Path(filename).write_text("gguf")

        with patch(
            "docsift.cli.commands.pull.request.urlretrieve",
            side_effect=fake_urlretrieve,
        ) as mock_retrieve:
            result = runner.invoke(
                pull_cmd,
                [
                    "--cache-dir",
                    cache_dir,
                    "https://example.com/model.gguf",
                ],
            )

        assert result.exit_code == 0
        assert "Downloaded to" in result.output
        mock_retrieve.assert_called_once()

    def test_pull_invalid_spec(self) -> None:
        """Invalid model spec shows error."""
        runner = CliRunner()
        result = runner.invoke(pull_cmd, ["invalid_spec"])

        assert result.exit_code != 0
        assert "must be owner/repo/filename.gguf or a direct URL" in result.output

    def test_pull_empty_file(self, tmp_path: Path) -> None:
        """Empty downloaded file is rejected."""
        runner = CliRunner()
        cache_dir = str(tmp_path / "models")
        fake_path = str(tmp_path / "models" / "model.gguf")
        Path(fake_path).parent.mkdir(parents=True, exist_ok=True)
        Path(fake_path).write_text("")

        with patch(
            "docsift.cli.commands.pull.hf_hub_download",
            return_value=fake_path,
        ):
            result = runner.invoke(
                pull_cmd,
                ["--cache-dir", cache_dir, "owner/repo/model.gguf"],
            )

        assert result.exit_code != 0
        assert "missing or empty" in result.output

    def test_pull_modelscope_not_installed(self, tmp_path: Path) -> None:
        """ModelScope ImportError is reported cleanly."""
        runner = CliRunner()
        cache_dir = str(tmp_path / "models")

        with (
            patch(
                "docsift.cli.commands.pull.hf_hub_download",
                side_effect=Exception("HF down"),
            ),
            patch(
                "docsift.cli.commands.pull.snapshot_download",
                side_effect=ImportError("No modelscope"),
            ),
        ):
            result = runner.invoke(
                pull_cmd,
                ["--cache-dir", cache_dir, "owner/repo/model.gguf"],
            )

        assert result.exit_code != 0
        assert "ModelScope not installed" in result.output
