"""Tests for bench CLI command."""

import json
from pathlib import Path
from typing import ClassVar
from unittest.mock import MagicMock, patch

import pytest
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


class _CountingEmbedder:
    """Embedder protocol spy counting every inner embed call per text."""

    def __init__(self) -> None:
        self.calls: list[str] = []

    def embed(self, text: str) -> list[float]:
        self.calls.append(text)
        return [0.0] * 8

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        return [self.embed(text) for text in texts]

    @property
    def dimension(self) -> int:
        return 8


class _SpyPipeline:
    """SearchPipeline stand-in recording every query and exercising the embedder."""

    seen: ClassVar[list[str]] = []

    def __init__(
        self,
        _connection: object,
        embedder: object | None = None,
        _embedding_dim: int = 768,
        _reranker: object | None = None,
        **_kwargs: object,
    ) -> None:
        self.embedder = embedder

    def search(self, query: str, _options: object) -> list:
        _SpyPipeline.seen.append(query)
        if self.embedder is not None:
            self.embedder.embed(query)
        return []


class _SpyReranker:
    """Reranker spy: records (candidate count, top_k) per call; reorders and trims."""

    calls: ClassVar[list[tuple[int, int]]] = []

    def rerank(self, _query: str, results: list, top_k: int = 10) -> list:
        _SpyReranker.calls.append((len(results), top_k))
        return list(reversed(results))[:top_k]


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

    def test_bench_embedder_soft_fail_warning_stays_off_json_stdout(
        self, tmp_path: Path
    ) -> None:
        """CR-01: the embedder soft-fail warning goes to stderr (never the
        JSON stdout stream), so the BM25-only degradation path still parses."""
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

        with (
            patch("sif.cli.commands.bench.Database", return_value=mock_db),
            patch(
                "sif.cli.commands.bench.EmbeddingManager.from_settings",
                side_effect=ImportError("No module named 'sentence_transformers'"),
            ),
            patch("sif.cli.commands.bench.SearchPipeline", return_value=mock_pipeline),
            patch("sif.cli.commands.bench.get_settings", return_value=_settings_mock()),
        ):
            result = runner.invoke(
                bench_cmd,
                [str(fixture_path), "--json"],
                obj={"index_path": MagicMock(exists=lambda: True)},
            )

        assert result.exit_code == 0, result.output
        # stdout alone strict-parses: the warning never rode the JSON stream.
        output = json.loads(result.stdout)
        assert "mrr" in output
        assert "Embedding backend not installed" not in result.stdout
        assert "Embedding backend not installed" in result.stderr

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
            # Off-only sweep rows never construct a states mapping: the flat
            # fields ARE the off state (D-12).
            assert "states" not in config
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


class TestCachedEmbedder:
    def test_embed_runs_the_inner_model_once_per_distinct_text(self) -> None:
        from sif.cli.commands.bench import CachedEmbedder

        counting = _CountingEmbedder()
        cached = CachedEmbedder(counting)
        first = cached.embed("query one")
        second = cached.embed("query one")
        assert first is second
        assert counting.calls == ["query one"]
        cached.embed("query two")
        assert counting.calls == ["query one", "query two"]

    def test_embed_batch_delegates_through_the_cache(self) -> None:
        from sif.cli.commands.bench import CachedEmbedder

        counting = _CountingEmbedder()
        cached = CachedEmbedder(counting)
        vectors = cached.embed_batch(["a", "b", "a"])
        assert vectors == [[0.0] * 8] * 3
        assert counting.calls == ["a", "b"]

    def test_dimension_is_forwarded(self) -> None:
        from sif.cli.commands.bench import CachedEmbedder

        cached = CachedEmbedder(_CountingEmbedder())
        assert cached.dimension == 8


class TestBenchSweepDiscipline:
    """Tuning-only ranking, embedding reuse, and the settings baseline (D-03/D-07/D-09)."""

    def _invoke_sweep(
        self, tmp_path: Path, extra_flags: list[str]
    ) -> tuple[object, _CountingEmbedder]:
        """Run bench --sweep over the spy pipeline; caller inspects the spies."""
        fixture_path, _corpus = _graded_split_fixture(tmp_path)
        counting = _CountingEmbedder()
        _SpyPipeline.seen = []

        mock_manager = MagicMock()
        mock_manager.embed_single.return_value = [0.0] * 8
        mock_manager._model = counting

        with (
            patch("sif.cli.commands.bench.Database", return_value=MagicMock()),
            patch(
                "sif.cli.commands.bench.EmbeddingManager.from_settings",
                return_value=mock_manager,
            ),
            patch("sif.cli.commands.bench.SearchPipeline", _SpyPipeline),
            patch("sif.cli.commands.bench.get_settings", return_value=_settings_mock()),
        ):
            result = CliRunner().invoke(
                bench_cmd,
                [str(fixture_path), "--sweep", *extra_flags],
                obj={"index_path": MagicMock(exists=lambda: True)},
            )
        return result, counting

    def test_bench_sweep_never_searches_heldout_queries(self, tmp_path: Path) -> None:
        """T-16-06: the held-out sentinel string never reaches the searcher."""
        result, _counting = self._invoke_sweep(tmp_path, [])
        assert result.exit_code == 0, result.output
        assert "heldout sentinel" not in _SpyPipeline.seen
        assert "tuning one" in _SpyPipeline.seen
        assert "tuning two" in _SpyPipeline.seen

    def test_bench_sweep_embeds_each_query_once(self, tmp_path: Path) -> None:
        """D-07: one inner embed per distinct query text across all 45 configs.

        Without memoization the spy pipeline drives 2 queries x 45 configs x
        2 passes (warm-up + timed) = 180 inner embed calls; the cache must
        collapse that to exactly one per distinct tuning query.
        """
        result, counting = self._invoke_sweep(tmp_path, [])
        assert result.exit_code == 0, result.output
        assert sorted(set(counting.calls)) == ["tuning one", "tuning two"]
        assert counting.calls.count("tuning one") == 1
        assert counting.calls.count("tuning two") == 1

    def test_bench_sweep_json_baseline_and_deltas(self, tmp_path: Path) -> None:
        """D-09: the settings run is the baseline row; config deltas are relative."""
        runner = CliRunner()
        fixture_path, corpus = _graded_split_fixture(tmp_path)

        def config_aware_search(_query: str, options: object) -> list:
            # Only rrf_k == 80 (the mocked settings value) ranks the relevant
            # doc first, so configs measurably differ across the grid.
            if options.rrf_k == 80:
                return [MagicMock(document_id="d1", path=str(corpus / "keyword" / "a.md"))]
            return []

        mock_pipeline = MagicMock()
        mock_pipeline.search.side_effect = config_aware_search

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
            patch(
                "sif.cli.commands.bench.get_settings",
                return_value=_settings_mock(rrf_k=80, bm25_weight=2.0, vector_weight=0.5),
            ),
        ):
            result = runner.invoke(
                bench_cmd,
                [str(fixture_path), "--sweep", "--json"],
                obj={"index_path": MagicMock(exists=lambda: True)},
            )

        assert result.exit_code == 0, result.output
        output = json.loads(result.output.strip())
        baseline = output["baseline"]
        assert (baseline["rrf_k"], baseline["bm25_weight"], baseline["vector_weight"]) == (
            80,
            2.0,
            0.5,
        )
        # The baseline carries the four-category breakdown like every config.
        assert list(baseline["categories"].keys()) == [
            "keyword",
            "synonym",
            "multilingual",
            "rival",
        ]
        for config in output["configs"]:
            assert {"ndcg_delta", "hit_delta", "p50_delta_ms", "p95_delta_ms"} <= set(config)
        # The settings configuration is a grid point, so its row's deltas are
        # exactly zero (the baseline measurement is reused).
        matching = [
            c
            for c in output["configs"]
            if (c["rrf_k"], c["bm25_weight"], c["vector_weight"]) == (80, 2.0, 0.5)
        ]
        assert len(matching) == 1
        assert matching[0]["ndcg_delta"] == 0.0
        assert matching[0]["hit_delta"] == 0.0
        # Deltas are relative to the baseline, not zero-filled: an rrf_k=20
        # config scores 0 ndcg against the baseline's 0.5.
        zero_config = next(c for c in output["configs"] if c["rrf_k"] == 20)
        assert zero_config["ndcg_delta"] == pytest.approx(-baseline["ndcg_at_10"])

    def test_bench_sweep_json_parses_at_narrow_width(self, tmp_path: Path) -> None:
        """--sweep --json strict-parses at COLUMNS=80 (click.echo, never Rich)."""
        result, _counting = self._invoke_sweep(tmp_path, ["--json"])
        assert result.exit_code == 0
        output = json.loads(result.output)
        assert len(output["configs"]) == 45

    def test_bench_sweep_legacy_fixture_names_missing_split(self, tmp_path: Path) -> None:
        """A fixture without split labels exits non-zero naming the split
        requirement instead of reporting an empty sweep as success."""
        runner = CliRunner()
        fixture = {"queries": [{"query": "test", "relevant_docids": ["doc-1"]}]}
        fixture_path = tmp_path / "fixture.json"
        fixture_path.write_text(json.dumps(fixture))

        with (
            patch("sif.cli.commands.bench.Database", return_value=MagicMock()),
            patch(
                "sif.cli.commands.bench.EmbeddingManager.from_settings",
                return_value=MagicMock(
                    embed_single=MagicMock(return_value=[0.0] * 8),
                    _model=MagicMock(),
                ),
            ),
            patch("sif.cli.commands.bench.SearchPipeline", return_value=MagicMock()),
            patch("sif.cli.commands.bench.get_settings", return_value=_settings_mock()),
        ):
            result = runner.invoke(
                bench_cmd,
                [str(fixture_path), "--sweep"],
                obj={"index_path": MagicMock(exists=lambda: True)},
            )

        assert result.exit_code != 0
        assert "Sweep requires fixtures with split labels" in result.output
        assert "split == 'tuning'" in result.output

    def test_bench_sweep_all_heldout_fixture_names_missing_split(self, tmp_path: Path) -> None:
        """A graded fixture whose queries are ALL held-out is just as empty a
        tuning set: non-zero exit naming the split requirement."""
        runner = CliRunner()
        fixture = {
            "corpus_root": "corpus",
            "relevance_key": "path",
            "queries": [
                {
                    "query": "only heldout",
                    "category": "rival",
                    "split": "heldout",
                    "relevance": {"rival/c.md": 3},
                },
            ],
        }
        fixture_path = tmp_path / "fixture.json"
        fixture_path.write_text(json.dumps(fixture))

        with (
            patch("sif.cli.commands.bench.Database", return_value=MagicMock()),
            patch(
                "sif.cli.commands.bench.EmbeddingManager.from_settings",
                return_value=MagicMock(
                    embed_single=MagicMock(return_value=[0.0] * 8),
                    _model=MagicMock(),
                ),
            ),
            patch("sif.cli.commands.bench.SearchPipeline", return_value=MagicMock()),
            patch("sif.cli.commands.bench.get_settings", return_value=_settings_mock()),
        ):
            result = runner.invoke(
                bench_cmd,
                [str(fixture_path), "--sweep"],
                obj={"index_path": MagicMock(exists=lambda: True)},
            )

        assert result.exit_code != 0
        assert "Sweep requires fixtures with split labels" in result.output


class TestBenchCandidateLimit:
    """bench's -C resolves through Plan 02's shared clamp (D-10)."""

    def _options_for(
        self,
        tmp_path: Path,
        flags: list[str],
        settings_overrides: dict[str, object] | None = None,
    ) -> object:
        fixture = {"queries": [{"query": "test", "relevant_docids": ["doc-1"]}]}
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
            patch(
                "sif.cli.commands.bench.get_settings",
                return_value=_settings_mock(**(settings_overrides or {})),
            ),
        ):
            result = CliRunner().invoke(
                bench_cmd,
                [str(fixture_path), *flags],
                obj={"index_path": MagicMock(exists=lambda: True)},
            )
        assert result.exit_code == 0, result.output
        return mock_pipeline.search.call_args[0][1]

    def test_candidate_limit_200_clamps_to_50(self, tmp_path: Path) -> None:
        options = self._options_for(tmp_path, ["-C", "200", "--json"])
        assert options.candidate_limit == 50

    def test_candidate_limit_5_arrives_as_int_five(self, tmp_path: Path) -> None:
        options = self._options_for(tmp_path, ["-C", "5", "--json"])
        assert options.candidate_limit == 5
        assert isinstance(options.candidate_limit, int)

    def test_candidate_limit_omitted_resolves_from_settings(self, tmp_path: Path) -> None:
        options = self._options_for(
            tmp_path,
            ["--json"],
            settings_overrides={"rerank_candidate_limit": 33},
        )
        assert options.candidate_limit == 33


class TestBenchRerankStates:
    """Rerank off/on as two measured states, strictly additive (D-12/D-13)."""

    @classmethod
    def _legacy_fixture(cls, tmp_path: Path) -> Path:
        fixture = {"queries": [{"query": "test", "relevant_docids": ["doc-1"]}]}
        fixture_path = tmp_path / "fixture.json"
        fixture_path.write_text(json.dumps(fixture))
        return fixture_path

    def test_bench_off_only_json_states_additive_no_reranker(self, tmp_path: Path) -> None:
        """Without --rerank: create_reranker is never called, and states.off
        sits ALONGSIDE the untouched flat top-level keys (never a wrapper)."""
        runner = CliRunner()
        fixture_path = self._legacy_fixture(tmp_path)

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
            patch("sif.cli.commands.bench.create_reranker") as create_spy,
        ):
            result = runner.invoke(
                bench_cmd,
                [str(fixture_path), "--json"],
                obj={"index_path": MagicMock(exists=lambda: True)},
            )

        assert result.exit_code == 0, result.output
        create_spy.assert_not_called()
        output = json.loads(result.output.strip())
        # The pinned flat keys stay top-level and unchanged.
        assert "ndcg_at_10" in output
        assert "mrr" in output
        assert "precision@1" in output
        # states.off is added alongside; the on state is never constructed.
        assert set(output["states"]) == {"off"}
        assert set(output["states"]["off"]) == {"ndcg_at_10", "hit_at_10", "p50_ms", "p95_ms"}

    def test_bench_rerank_states_measured_with_spy_reranker(self) -> None:
        """--rerank measures both states through the real pipeline; the spy
        receives top_k=limit and never more than settings.rerank_candidate_limit
        candidates."""
        from tests.support.bench import EMBEDDING_DIM, ConceptEmbedder, build_bench_db

        embedder = ConceptEmbedder()
        conn = build_bench_db(Path("tests/fixtures/bench/corpus"), embedder)
        _SpyReranker.calls = []
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
                patch(
                    "sif.cli.commands.bench.create_reranker",
                    return_value=_SpyReranker(),
                ) as create_spy,
            ):
                result = runner.invoke(
                    bench_cmd,
                    [str(Path("tests/fixtures/bench/queries.json")), "--rerank", "--json"],
                    obj={"index_path": MagicMock(exists=lambda: True)},
                )

            assert result.exit_code == 0, result.output
            create_spy.assert_called_once()
            output = json.loads(result.output.strip())
            assert output["ndcg_at_10"] > 0.0
            # Both states exist with metrics and latency each.
            assert set(output["states"]) == {"off", "on"}
            for state in output["states"].values():
                assert set(state) == {"ndcg_at_10", "hit_at_10", "p50_ms", "p95_ms"}
            # The spy reranker ran (two passes per query on the on pipeline)
            # and the candidate cap + top_k contract held on every call.
            assert len(_SpyReranker.calls) >= 2
            assert all(top_k == 10 for _candidates, top_k in _SpyReranker.calls)
            assert all(1 <= candidates <= 20 for candidates, _top_k in _SpyReranker.calls)
        finally:
            conn.close()

    def test_bench_sweep_rerank_states_per_config(self, tmp_path: Path) -> None:
        """Sweep + --rerank: every config row (and the baseline) carries both
        states with metrics and latency (D-12)."""
        runner = CliRunner()
        fixture_path, corpus = _graded_split_fixture(tmp_path)

        mock_pipeline = MagicMock()
        mock_pipeline.search.return_value = [
            MagicMock(document_id="d1", path=str(corpus / "keyword" / "a.md")),
        ]
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
            patch("sif.cli.commands.bench.create_reranker", return_value=MagicMock()),
        ):
            result = runner.invoke(
                bench_cmd,
                [str(fixture_path), "--sweep", "--rerank", "--json"],
                obj={"index_path": MagicMock(exists=lambda: True)},
            )

        assert result.exit_code == 0, result.output
        output = json.loads(result.output.strip())
        assert len(output["configs"]) == 45
        for row in [*output["configs"], output["baseline"]]:
            assert set(row["states"]) == {"off", "on"}
            for state in row["states"].values():
                assert set(state) == {"ndcg_at_10", "hit_at_10", "p50_ms", "p95_ms"}

    def test_bench_rerank_missing_backend_degrades_to_off_only(self, tmp_path: Path) -> None:
        """A missing reranker backend warns and measures off-only (exit 0)."""
        runner = CliRunner()
        fixture_path = self._legacy_fixture(tmp_path)

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
            patch(
                "sif.cli.commands.bench.create_reranker",
                side_effect=ImportError("No module named 'transformers'"),
            ),
        ):
            result = runner.invoke(
                bench_cmd,
                [str(fixture_path), "--rerank"],
                obj={"index_path": MagicMock(exists=lambda: True)},
            )

        assert result.exit_code == 0, result.output
        assert "Reranker backend not available" in result.output
        assert "MRR" in result.output

    def test_bench_rerank_missing_backend_warning_stays_off_json_stdout(
        self, tmp_path: Path
    ) -> None:
        """CR-01: the soft-fail reranker warning goes to stderr, so
        `sif bench --json | jq` strict-parses on the degradation path."""
        runner = CliRunner()
        fixture_path = self._legacy_fixture(tmp_path)

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
            patch(
                "sif.cli.commands.bench.create_reranker",
                side_effect=ImportError("No module named 'transformers'"),
            ),
        ):
            result = runner.invoke(
                bench_cmd,
                [str(fixture_path), "--rerank", "--json"],
                obj={"index_path": MagicMock(exists=lambda: True)},
            )

        assert result.exit_code == 0, result.output
        # stdout alone strict-parses: the warning never rode the JSON stream.
        output = json.loads(result.stdout)
        assert "ndcg_at_10" in output
        assert "Reranker backend not available" not in result.stdout
        assert "Reranker backend not available" in result.stderr

    def test_bench_rerank_model_load_failure_degrades_to_off_only(self, tmp_path: Path) -> None:
        """A model-load failure warns and measures off-only (fail-soft)."""
        runner = CliRunner()
        fixture_path = self._legacy_fixture(tmp_path)

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
            patch(
                "sif.cli.commands.bench.create_reranker",
                side_effect=RuntimeError("weights download failed"),
            ),
        ):
            result = runner.invoke(
                bench_cmd,
                [str(fixture_path), "--rerank"],
                obj={"index_path": MagicMock(exists=lambda: True)},
            )

        assert result.exit_code == 0, result.output
        assert "Failed to load reranker model" in result.output

    def test_bench_rerank_factory_value_error_is_click_exception(self, tmp_path: Path) -> None:
        """A factory ValueError stays a ClickException (non-zero exit)."""
        runner = CliRunner()
        fixture_path = self._legacy_fixture(tmp_path)

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
            patch(
                "sif.cli.commands.bench.create_reranker",
                side_effect=ValueError("Unknown reranker model type"),
            ),
        ):
            result = runner.invoke(
                bench_cmd,
                [str(fixture_path), "--rerank"],
                obj={"index_path": MagicMock(exists=lambda: True)},
            )

        assert result.exit_code != 0
        assert "Unknown reranker model type" in result.output
