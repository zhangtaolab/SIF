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
    settings-baseline assertion would pass for the wrong reason. The rerank
    fields are enumerated too: bench's rerank states (16-04) read them, and a
    wide-open mock would leak MagicMock values into SearchOptions.
    """
    fields: dict[str, object] = {
        "rrf_k": 60,
        "bm25_weight": 1.0,
        "vector_weight": 1.0,
        "rerank_enabled": False,
        "rerank_candidate_limit": 20,
        "rerank_relative_threshold": 0.5,
    }
    fields.update(overrides)
    return MagicMock(**fields)


def _graded_split_fixture(tmp_path: Path) -> tuple[Path, Path]:
    """Graded path-keyed fixture with two tuning and one held-out query."""
    corpus = tmp_path / "corpus"
    fixture = {
        "corpus_root": "corpus",
        "relevance_key": "path",
        "queries": [
            {
                "query": "tuning one",
                "category": "keyword",
                "split": "tuning",
                "relevance": {"keyword/a.md": 3},
            },
            {
                "query": "tuning two",
                "category": "synonym",
                "split": "tuning",
                "relevance": {"synonym/b.md": 2},
            },
            {
                "query": "heldout sentinel",
                "category": "rival",
                "split": "heldout",
                "relevance": {"rival/c.md": 3},
            },
        ],
    }
    fixture_path = tmp_path / "fixture.json"
    fixture_path.write_text(json.dumps(fixture))
    return fixture_path, corpus


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

    def test_bench_malformed_fixture_exits_nonzero(self, tmp_path: Path) -> None:
        """Malformed fixture JSON surfaces as a ClickException (T-16-02)."""
        runner = CliRunner()

        fixture_path = tmp_path / "fixture.json"
        fixture_path.write_text("{not valid json")

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
        assert "Benchmark failed" in result.output

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

    def test_cli_bench_committed_pack_nonzero_ndcg(self) -> None:
        """CLI-level join proof: bench_cmd on the EXACT committed pack file
        (no tmp_path copy, no explicit corpus root) resolves the fixture's
        declared corpus_root, runs the deterministic index end to end, and
        reports non-zero ndcg_at_10 and hit_at_10.

        Skips when sqlite-vec is unavailable (build_bench_db's discipline).
        Flag-minimal by design: no --sweep/--rerank, so this stays a pure
        no-sweep join proof even when bench gains flags in later plans.
        """
        from tests.support.bench import EMBEDDING_DIM, ConceptEmbedder, build_bench_db

        embedder = ConceptEmbedder()
        conn = build_bench_db(Path("tests/fixtures/bench/corpus"), embedder)
        try:
            mock_db = MagicMock()
            mock_db.__enter__.return_value.connection = conn
            mock_manager = MagicMock()
            mock_manager._model = embedder
            mock_manager.embed_single.return_value = [0.0] * EMBEDDING_DIM

            runner = CliRunner()
            with (
                patch("sif.cli.commands.bench.Database", return_value=mock_db),
                patch(
                    "sif.cli.commands.bench.EmbeddingManager.from_settings",
                    return_value=mock_manager,
                ),
                patch(
                    "sif.cli.commands.bench.get_settings",
                    return_value=_settings_mock(),
                ),
            ):
                result = runner.invoke(
                    bench_cmd,
                    [str(Path("tests/fixtures/bench/queries.json")), "--json"],
                    obj={"index_path": MagicMock(exists=lambda: True)},
                )

            assert result.exit_code == 0, result.output
            output = json.loads(result.output.strip())
            assert output["ndcg_at_10"] > 0.0
            assert output["hit_at_10"] > 0.0
        finally:
            conn.close()

    def test_bench_sweep_json_shape(self, tmp_path: Path) -> None:
        """--sweep --json emits configs/tie_group/winner_declared, every config
        carrying the four-category breakdown in declared order (D-06)."""
        runner = CliRunner()
        fixture_path, corpus = _graded_split_fixture(tmp_path)

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
                [str(fixture_path), "--sweep", "--json"],
                obj={"index_path": MagicMock(exists=lambda: True)},
            )

        assert result.exit_code == 0, result.output
        output = json.loads(result.output.strip())
        assert {"configs", "tie_group", "winner_declared"} <= set(output)
        # All 45 declared configurations are measured.
        assert len(output["configs"]) == 45
        # The mocked pipeline returns identical results for every config, so
        # the whole grid ties and no single winner may be declared (D-08).
        assert len(output["tie_group"]) == 45
        assert output["winner_declared"] is False
        for config in output["configs"]:
            assert {
                "rrf_k",
                "bm25_weight",
                "vector_weight",
                "ndcg_at_10",
                "hit_at_10",
            } <= set(config)
            assert list(config["categories"].keys()) == [
                "keyword",
                "synonym",
                "multilingual",
                "rival",
            ]
            for metrics in config["categories"].values():
                assert "ndcg_at_10" in metrics
                assert "hit_at_10" in metrics

    def test_bench_sweep_table_renders_tie_honesty(self, tmp_path: Path) -> None:
        """--sweep (no --json) renders the sweep table plus the tie note."""
        runner = CliRunner()
        fixture_path, _corpus = _graded_split_fixture(tmp_path)

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
                [str(fixture_path), "--sweep"],
                obj={"index_path": MagicMock(exists=lambda: True)},
            )

        assert result.exit_code == 0, result.output
        assert "Parameter Sweep" in result.output
        # Identical (zero) metrics across the grid -> full tie group, no winner.
        # (Rich may wrap the footer at the terminal width, so assert on
        # wrap-safe fragments.)
        assert "Tie group of 45 configurations" in result.output
        assert "no single winner" in result.output
