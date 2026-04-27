"""Tests for bench CLI command."""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

from click.testing import CliRunner

from sif.cli.commands.bench import bench_cmd


class TestBenchCommand:
    def test_bench_requires_fixture(self) -> None:
        runner = CliRunner()
        result = runner.invoke(
            bench_cmd,
            [],
            obj={"index_path": MagicMock(exists=lambda: True)},
        )
        assert result.exit_code != 0
        assert "Missing argument" in result.output or "FIXTURE" in result.output

    def test_bench_with_valid_fixture(self, tmp_path: Path) -> None:
        runner = CliRunner()

        fixture = {
            "queries": [
                {"query": "test", "relevant_docids": ["doc-1"]},
            ]
        }
        fixture_path = tmp_path / "fixture.json"
        fixture_path.write_text(json.dumps(fixture))

        mock_pipeline = MagicMock()
        mock_pipeline.search.return_value = [
            MagicMock(document_id="doc-1"),
        ]

        mock_db = MagicMock()
        mock_manager = MagicMock()
        mock_manager.embed_single.return_value = [0.0] * 384
        mock_manager._model = MagicMock()

        with (
            patch("sif.cli.commands.bench.Database", return_value=mock_db),
            patch(
                "sif.cli.commands.bench.EmbeddingManager.from_settings",
                return_value=mock_manager,
            ),
            patch("sif.cli.commands.bench.SearchPipeline", return_value=mock_pipeline),
            patch("sif.cli.commands.bench.get_settings", return_value=MagicMock()),
        ):
            result = runner.invoke(
                bench_cmd,
                [str(fixture_path)],
                obj={"index_path": MagicMock(exists=lambda: True)},
            )

        assert result.exit_code == 0
        assert "MRR" in result.output or "precision" in result.output

    def test_bench_json_output(self, tmp_path: Path) -> None:
        runner = CliRunner()

        fixture = {
            "queries": [
                {"query": "test", "relevant_docids": ["doc-1"]},
            ]
        }
        fixture_path = tmp_path / "fixture.json"
        fixture_path.write_text(json.dumps(fixture))

        mock_pipeline = MagicMock()
        mock_pipeline.search.return_value = [MagicMock(document_id="doc-1")]

        mock_db = MagicMock()
        mock_manager = MagicMock()
        mock_manager.embed_single.return_value = [0.0] * 384
        mock_manager._model = MagicMock()

        with (
            patch("sif.cli.commands.bench.Database", return_value=mock_db),
            patch(
                "sif.cli.commands.bench.EmbeddingManager.from_settings",
                return_value=mock_manager,
            ),
            patch("sif.cli.commands.bench.SearchPipeline", return_value=mock_pipeline),
            patch("sif.cli.commands.bench.get_settings", return_value=MagicMock()),
        ):
            result = runner.invoke(
                bench_cmd,
                [str(fixture_path), "--json"],
                obj={"index_path": MagicMock(exists=lambda: True)},
            )

        assert result.exit_code == 0
        output = json.loads(result.output.strip())
        assert "mrr" in output
        assert "precision@1" in output

    def test_bench_no_index(self) -> None:
        runner = CliRunner()
        fixture = {"queries": [{"query": "test", "relevant_docids": ["doc-1"]}]}
        import tempfile

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(fixture, f)
            fixture_path = Path(f.name)

        result = runner.invoke(
            bench_cmd,
            [str(fixture_path)],
            obj={"index_path": MagicMock(exists=lambda: False)},
        )
        fixture_path.unlink(missing_ok=True)
        assert result.exit_code == 0
        assert "No index found" in result.output
