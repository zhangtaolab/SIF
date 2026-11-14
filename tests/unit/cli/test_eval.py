"""Tests for the personal-eval CLI (Phase 18, EVAL-01)."""

from __future__ import annotations

import json
from contextlib import ExitStack
from pathlib import Path
from typing import Any, ClassVar
from unittest.mock import MagicMock, patch

from click.testing import CliRunner, Result

from sif.cli.commands.eval import eval_group
from sif.config.settings import Settings
from sif.core.models import SearchResult
from sif.search.benchmark import SearchEvaluator
from sif.search.personal_bench import (
    DocumentRecord,
    sample_documents,
)
from tests.support.bench import EMBEDDING_DIM, ConceptEmbedder
from tests.support.eval import build_personal_db


_UNSET = object()


def _settings(tmp_path: Path, **overrides: Any) -> Settings:
    """Real Settings pinned to the fixture's embedding dimension.

    ``Database.init_schema`` reads ``sif.config.settings.get_settings`` and
    validates the on-disk vec0 dimension against ``embedding_dim``; the same
    real Settings object is patched at both import sites.
    """
    fields: dict[str, Any] = {
        "cache_dir": tmp_path,
        "embedding_dim": EMBEDDING_DIM,
        "model_type": "sentence_transformers",
    }
    fields.update(overrides)
    return Settings(_env_file=None, **fields)


def _manager(embedder: ConceptEmbedder | None = None) -> MagicMock:
    """EmbeddingManager stand-in exposing the concept embedder and its dim."""
    model = embedder or ConceptEmbedder()
    manager = MagicMock()
    manager.model = model
    manager.get_model_info.return_value = {"loaded": True, "embedding_dim": EMBEDDING_DIM}
    return manager


class _SpyPipeline:
    """SearchPipeline stand-in recording every query in call order."""

    seen: ClassVar[list[str]] = []

    def __init__(
        self,
        _connection: object,
        embedder: object | None = None,
        _embedding_dim: int = EMBEDDING_DIM,
        **_kwargs: object,
    ) -> None:
        self.embedder = embedder

    def search(self, query: str, _options: object) -> list:
        _SpyPipeline.seen.append(query)
        return []


def _invoke(
    db_path: Path,
    args: list[str],
    *,
    settings: Settings,
    manager: object = _UNSET,
    manager_side_effect: BaseException | None = None,
    pipeline: object | None = None,
) -> Result:
    """Invoke eval_group with the eval module's seams patched.

    By default ``EmbeddingManager.from_settings`` raises if constructed, so
    ``--bm25-only`` paths prove they never touch the embedder. Pass
    ``manager`` for hybrid runs or ``manager_side_effect`` for failure paths.
    """
    runner = CliRunner()
    with ExitStack() as stack:
        stack.enter_context(
            patch("sif.cli.commands.eval.get_settings", return_value=settings),
        )
        stack.enter_context(
            patch("sif.config.settings.get_settings", return_value=settings),
        )
        if manager_side_effect is not None:
            stack.enter_context(
                patch(
                    "sif.cli.commands.eval.EmbeddingManager.from_settings",
                    side_effect=manager_side_effect,
                ),
            )
        elif manager is not _UNSET:
            stack.enter_context(
                patch(
                    "sif.cli.commands.eval.EmbeddingManager.from_settings",
                    return_value=manager,
                ),
            )
        else:
            stack.enter_context(
                patch(
                    "sif.cli.commands.eval.EmbeddingManager.from_settings",
                    side_effect=AssertionError("embedder constructed on a bm25-only path"),
                ),
            )
        if pipeline is not None:
            stack.enter_context(
                patch("sif.cli.commands.eval.SearchPipeline", pipeline),
            )
        return runner.invoke(eval_group, args, obj={"index_path": db_path})


def _result(document_id: str, path: str = "/p/result.md") -> SearchResult:
    """Minimal SearchResult for direct evaluator tests."""
    return SearchResult(
        document_id=document_id,
        title="title",
        path=path,
        collection_name="collection",
        score=1.0,
    )


_TWO_QUERY_FIXTURE = {
    "queries": [
        {"query": "first", "relevant_docids": ["doc-1"]},
        {"query": "second", "relevant_docids": ["doc-2"]},
    ],
}


def _two_query_search(query: str) -> list[SearchResult]:
    """Target retrieved at rank 1 for 'first'; absent for 'second'."""
    if query == "first":
        return [_result("doc-1")]
    return [_result("doc-9")]


class TestEvaluatePerQuery:
    def test_two_query_fixture_returns_records_in_fixture_order(self) -> None:
        evaluator = SearchEvaluator(_TWO_QUERY_FIXTURE)
        evaluations = evaluator.evaluate_per_query(_two_query_search, k=1)

        assert [evaluation.query for evaluation in evaluations] == ["first", "second"]
        # Target at rank 1 => perfect nDCG@1 and Hit@1; target absent => 0.0.
        assert evaluations[0].ndcg_at_10 == 1.0
        assert evaluations[0].hit_at_10 == 1.0
        assert evaluations[1].ndcg_at_10 == 0.0
        assert evaluations[1].hit_at_10 == 0.0
        assert evaluations[0].retrieved_keys == ["doc-1"]
        assert evaluations[0].grades == [1]
        assert evaluations[1].retrieved_keys == ["doc-9"]
        assert evaluations[1].grades == [0]

    def test_report_to_dict_keeps_exactly_its_pre_change_keys(self) -> None:
        evaluator = SearchEvaluator(_TWO_QUERY_FIXTURE)
        data = evaluator.report(_two_query_search).to_dict()

        assert set(data) == {
            "ndcg_at_10",
            "hit_at_10",
            "num_queries",
            "cold_start_ms",
            "p50_ms",
            "p95_ms",
            "categories",
            "mrr",
            "precision@1",
            "precision@5",
            "precision@10",
            "recall@1",
            "recall@5",
            "recall@10",
        }
        assert "per_query" not in data
        assert data["ndcg_at_10"] == 0.5
        assert data["hit_at_10"] == 0.5
        assert data["num_queries"] == 2
        assert data["mrr"] == 0.5
        assert data["precision@1"] == 0.5
        assert data["recall@1"] == 0.5


class TestSampling:
    def test_sampling_is_order_independent_and_deterministic(self) -> None:
        docs = [
            DocumentRecord(
                id=f"id-{index}",
                path=f"/corpus/{index % 3}.md",
                title=f"Title {index}",
                checksum=str(index),
                file_size=index,
            )
            for index in range(12)
        ]
        first = sample_documents(docs, limit=6)
        second = sample_documents(list(reversed(docs)), limit=6)

        assert [doc.id for doc in first] == [doc.id for doc in second]
        assert len({doc.id for doc in first}) == 6

    def test_shared_path_documents_get_distinct_stable_positions(self) -> None:
        shared = [
            DocumentRecord(
                id="doc-a",
                path="/corpus/shared.md",
                title="A",
                checksum="same",
                file_size=1,
            ),
            DocumentRecord(
                id="doc-b",
                path="/corpus/shared.md",
                title="B",
                checksum="same",
                file_size=1,
            ),
        ]
        assert [doc.id for doc in sample_documents(shared)] == ["doc-a", "doc-b"]
        assert [doc.id for doc in sample_documents(list(reversed(shared)))] == ["doc-a", "doc-b"]

    def test_load_document_metadata_selects_no_content(self) -> None:
        from sif.search.personal_bench import load_document_metadata

        class _RecordingConnection:
            sql = ""

            def execute(self, sql: str, _params: object = ()) -> list:
                _RecordingConnection.sql = sql
                return []

        assert load_document_metadata(_RecordingConnection(), None) == []  # type: ignore[arg-type]
        assert "content" not in _RecordingConnection.sql.lower()


class TestPersonalEvalCli:
    def test_personal_run_renders_table(self, tmp_path: Path) -> None:
        db_path = build_personal_db(tmp_path / "personal.db", documents=60)

        result = _invoke(
            db_path,
            ["--personal"],
            settings=_settings(tmp_path),
            manager=_manager(),
        )

        assert result.exit_code == 0, result.output
        assert "NDCG@10" in result.output
        assert "Hit@10" in result.output
        assert "Documents" in result.output
        # Bodies never reach output: only counts and metrics are rendered.
        assert "Document body" not in result.output

    def test_personal_json_is_strict_and_shaped(self, tmp_path: Path) -> None:
        db_path = build_personal_db(tmp_path / "personal.db", documents=60)

        result = _invoke(
            db_path,
            ["--personal", "--json"],
            settings=_settings(tmp_path),
            manager=_manager(),
        )

        assert result.exit_code == 0, result.output
        payload = json.loads(result.stdout)
        assert payload["mode"] == "personal"
        assert payload["retrieval"] == "hybrid"
        assert payload["corpus"]["documents"] == 60
        assert payload["corpus"]["sampled"] == 60
        assert len(payload["corpus"]["fingerprint"]) == 16
        assert payload["model"] == {
            "model_name": "Qwen/Qwen3-Embedding-0.6B",
            "model_type": "sentence_transformers",
            "dimension": EMBEDDING_DIM,
        }
        assert payload["queries"] == {
            "accepted": 60,
            "rejected_empty": 0,
            "rejected_duplicate": 0,
        }
        assert payload["metrics"]["num_queries"] == payload["queries"]["accepted"]
        assert isinstance(payload["metrics"]["ndcg_at_10"], float)
        assert isinstance(payload["metrics"]["hit_at_10"], float)
        assert payload["notes"]
        assert "content" not in payload
        assert "Document body" not in result.stdout

    def test_two_runs_emit_the_identical_query_order(self, tmp_path: Path) -> None:
        db_path = build_personal_db(tmp_path / "personal.db", documents=60)
        settings = _settings(tmp_path)

        _SpyPipeline.seen = []
        first = _invoke(
            db_path,
            ["--personal", "--bm25-only"],
            settings=settings,
            pipeline=_SpyPipeline,
        )
        first_queries = list(_SpyPipeline.seen)

        _SpyPipeline.seen = []
        second = _invoke(
            db_path,
            ["--personal", "--bm25-only"],
            settings=settings,
            pipeline=_SpyPipeline,
        )

        assert first.exit_code == 0, first.output
        assert second.exit_code == 0, second.output
        assert len(first_queries) == 60
        assert _SpyPipeline.seen == first_queries

    def test_bm25_only_reports_bm25_and_never_builds_embedder(self, tmp_path: Path) -> None:
        db_path = build_personal_db(tmp_path / "personal.db", documents=60)

        result = _invoke(
            db_path,
            ["--personal", "--bm25-only", "--json"],
            settings=_settings(tmp_path),
            pipeline=_SpyPipeline,
        )

        assert result.exit_code == 0, result.output
        payload = json.loads(result.stdout)
        assert payload["retrieval"] == "bm25"
        assert payload["model"] is None

    def test_eval_without_personal_is_a_usage_error(self) -> None:
        result = CliRunner().invoke(
            eval_group,
            [],
            obj={"index_path": Path("does-not-exist.db")},
        )

        assert result.exit_code == 2
        assert "--personal is required" in result.output

    def test_missing_index_exits_one(self, tmp_path: Path) -> None:
        result = _invoke(
            tmp_path / "missing.db",
            ["--personal"],
            settings=_settings(tmp_path),
        )

        assert result.exit_code == 1
        assert "No index found. Run 'sif index update' first." in result.output


def test_personal_help_lists_options() -> None:
    """The group exposes the declared option surface (docs generator input)."""
    result = CliRunner().invoke(eval_group, ["--help"])
    assert result.exit_code == 0
    for option in (
        "--personal",
        "--bm25-only",
        "--limit",
        "--collection",
        "--all",
        "--json",
    ):
        assert option in result.output
