"""Tests for bench CLI command."""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

from click.testing import CliRunner
from pydantic import BaseModel, ValidationError

from sif.cli.commands.bench import bench_cmd


def _settings_mock(**overrides: object) -> MagicMock:
    """Settings mock with REAL numeric fusion fields (research Pitfall 10).

    A bare MagicMock() makes settings.rrf_k/bm25_weight/vector_weight MagicMock
    objects that the plain SearchOptions dataclass accepts, so a
    settings-baseline assertion would pass for the wrong reason.
    """
    fields: dict[str, object] = {
        "rrf_k": 60,
        "bm25_weight": 1.0,
        "vector_weight": 1.0,
    }
    fields.update(overrides)
    return MagicMock(**fields)


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
            ],
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
            patch("sif.cli.commands.bench.get_settings", return_value=_settings_mock()),
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
            ],
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
            patch("sif.cli.commands.bench.get_settings", return_value=_settings_mock()),
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

    def test_bench_json_parses_at_narrow_width(self, tmp_path: Path) -> None:
        """bench --json strict-parses even when a metric string exceeds the width."""
        runner = CliRunner()

        fixture = {
            "queries": [
                {"query": "test", "relevant_docids": ["doc-1"]},
            ],
        }
        fixture_path = tmp_path / "fixture.json"
        fixture_path.write_text(json.dumps(fixture))

        # 120 chars with spaces so Rich word-wrapping bites pre-fix
        long_note = "lorem ipsum " * 10
        # bench consumes the graded report; the stub's to_dict() feeds --json.
        mock_evaluator = MagicMock()
        mock_evaluator.report.return_value.to_dict.return_value = {"mrr": 1.0, "note": long_note}

        mock_pipeline = MagicMock()
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
            patch(
                "sif.cli.commands.bench.SearchEvaluator",
                return_value=mock_evaluator,
            ),
            patch("sif.cli.commands.bench.get_settings", return_value=_settings_mock()),
        ):
            result = runner.invoke(
                bench_cmd,
                [str(fixture_path), "--json"],
                env={"COLUMNS": "80"},
                obj={"index_path": MagicMock(exists=lambda: True)},
            )

        assert result.exit_code == 0
        output = json.loads(result.output)
        assert output["note"] == long_note

    def test_bench_json_graded_metrics(self, tmp_path: Path) -> None:
        """Graded path-keyed fixtures report nDCG/Hit plus all category keys."""
        runner = CliRunner()

        corpus = tmp_path / "corpus"
        fixture = {
            "corpus_root": "corpus",
            "relevance_key": "path",
            "queries": [
                {
                    "query": "q1",
                    "category": "keyword",
                    "split": "tuning",
                    "relevance": {"keyword/a.md": 3},
                },
            ],
        }
        fixture_path = tmp_path / "fixture.json"
        fixture_path.write_text(json.dumps(fixture))

        mock_pipeline = MagicMock()
        mock_pipeline.search.return_value = [
            MagicMock(document_id="d1", path=str(corpus / "keyword" / "a.md")),
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
            patch("sif.cli.commands.bench.get_settings", return_value=_settings_mock()),
        ):
            result = runner.invoke(
                bench_cmd,
                [str(fixture_path), "--json"],
                obj={"index_path": MagicMock(exists=lambda: True)},
            )

        assert result.exit_code == 0
        output = json.loads(result.output.strip())
        assert output["ndcg_at_10"] == 1.0
        assert output["hit_at_10"] == 1.0
        assert list(output["categories"].keys()) == [
            "keyword",
            "synonym",
            "multilingual",
            "rival",
        ]
        assert output["categories"]["keyword"]["count"] == 1
        # Legacy flat keys keep their names beside the graded metrics.
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

    def test_bench_settings_baseline_and_single_pipeline(self, tmp_path: Path) -> None:
        """IN-02 fixed: bench options carry the current SIF_ fusion settings,
        and the pipeline is constructed once per state, not once per query."""
        runner = CliRunner()

        fixture = {
            "queries": [
                {"query": "a", "relevant_docids": ["doc-1"]},
                {"query": "b", "relevant_docids": ["doc-2"]},
            ],
        }
        fixture_path = tmp_path / "fixture.json"
        fixture_path.write_text(json.dumps(fixture))

        mock_pipeline = MagicMock()
        mock_pipeline.search.return_value = []
        pipeline_cls = MagicMock(return_value=mock_pipeline)

        mock_db = MagicMock()
        mock_manager = MagicMock()
        mock_manager.embed_single.return_value = [0.0] * 8
        mock_manager._model = MagicMock()

        with (
            patch("sif.cli.commands.bench.Database", return_value=mock_db),
            patch(
                "sif.cli.commands.bench.EmbeddingManager.from_settings",
                return_value=mock_manager,
            ),
            patch("sif.cli.commands.bench.SearchPipeline", pipeline_cls),
            patch(
                "sif.cli.commands.bench.get_settings",
                return_value=_settings_mock(rrf_k=80, bm25_weight=2.0, vector_weight=0.5),
            ),
        ):
            result = runner.invoke(
                bench_cmd,
                [str(fixture_path)],
                obj={"index_path": MagicMock(exists=lambda: True)},
            )

        assert result.exit_code == 0, result.output
        # One pipeline per measured state (hoisted out of the query loop).
        assert pipeline_cls.call_count == 1
        options = mock_pipeline.search.call_args[0][1]
        assert options.rrf_k == 80
        assert options.bm25_weight == 2.0
        assert options.vector_weight == 0.5

    def test_bench_json_latency_metrics(self, tmp_path: Path) -> None:
        """bench --json reports warmed p50/p95 and a separate cold start."""
        runner = CliRunner()

        fixture = {
            "queries": [
                {"query": "test", "relevant_docids": ["doc-1"]},
            ],
        }
        fixture_path = tmp_path / "fixture.json"
        fixture_path.write_text(json.dumps(fixture))

        mock_pipeline = MagicMock()
        mock_pipeline.search.return_value = [MagicMock(document_id="doc-1")]

        mock_db = MagicMock()
        mock_manager = MagicMock()
        mock_manager.embed_single.return_value = [0.0] * 8
        mock_manager._model = MagicMock()

        with (
            patch("sif.cli.commands.bench.Database", return_value=mock_db),
            patch(
                "sif.cli.commands.bench.EmbeddingManager.from_settings",
                return_value=mock_manager,
            ),
            patch("sif.cli.commands.bench.SearchPipeline", return_value=mock_pipeline),
            patch("sif.cli.commands.bench.get_settings", return_value=_settings_mock()),
        ):
            result = runner.invoke(
                bench_cmd,
                [str(fixture_path), "--json"],
                obj={"index_path": MagicMock(exists=lambda: True)},
            )

        assert result.exit_code == 0
        output = json.loads(result.output.strip())
        assert "p50_ms" in output
        assert "p95_ms" in output
        assert "cold_start_ms" in output
        assert output["p50_ms"] <= output["p95_ms"]
        assert isinstance(output["cold_start_ms"], (int, float))
        assert output["cold_start_ms"] >= 0.0

    def test_bench_empty_queries_exits_nonzero(self, tmp_path: Path) -> None:
        """An empty queries list fails loudly instead of reporting zeros."""
        runner = CliRunner()

        fixture = {"queries": []}
        fixture_path = tmp_path / "fixture.json"
        fixture_path.write_text(json.dumps(fixture))

        mock_pipeline = MagicMock()
        mock_pipeline.search.return_value = []
        mock_db = MagicMock()
        mock_manager = MagicMock()
        mock_manager.embed_single.return_value = [0.0] * 8
        mock_manager._model = MagicMock()

        with (
            patch("sif.cli.commands.bench.Database", return_value=mock_db),
            patch(
                "sif.cli.commands.bench.EmbeddingManager.from_settings",
                return_value=mock_manager,
            ),
            patch("sif.cli.commands.bench.SearchPipeline", return_value=mock_pipeline),
            patch("sif.cli.commands.bench.get_settings", return_value=_settings_mock()),
        ):
            result = runner.invoke(
                bench_cmd,
                [str(fixture_path)],
                obj={"index_path": MagicMock(exists=lambda: True)},
            )

        assert result.exit_code != 0
        assert "non-empty 'queries'" in result.output

    def test_bench_invalid_settings_click_exception(self, tmp_path: Path) -> None:
        """A pydantic ValidationError from get_settings surfaces as a
        ClickException (non-zero exit), never a raw traceback."""
        runner = CliRunner()

        fixture = {"queries": [{"query": "t", "relevant_docids": ["doc-1"]}]}
        fixture_path = tmp_path / "fixture.json"
        fixture_path.write_text(json.dumps(fixture))

        class _Strict(BaseModel):
            value: int

        try:
            _Strict(value="not-an-int")
        except ValidationError as error:
            invalid = error

        with patch(
            "sif.cli.commands.bench.get_settings",
            side_effect=invalid,
        ):
            result = runner.invoke(
                bench_cmd,
                [str(fixture_path)],
                obj={"index_path": MagicMock(exists=lambda: True)},
            )

        assert result.exit_code != 0
        assert "int" in result.output
