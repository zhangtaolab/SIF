"""Tests for graded benchmark metrics (nDCG/Hit/report/corpus-root)."""

from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path

import pytest

from sif.core.models import SearchResult
from sif.search.benchmark import (
    CATEGORIES,
    SearchEvaluator,
    hit_at_k,
    measure_query_times,
    ndcg_at_k,
    percentile,
    precision_at_k,
    recall_at_k,
    resolve_corpus_root,
    result_key,
)


def _result(path: str, document_id: str = "doc-x", score: float = 1.0) -> SearchResult:
    """Build a minimal SearchResult for path-keyed evaluation tests."""
    return SearchResult(
        document_id=document_id,
        title="T",
        path=path,
        collection_name="c",
        score=score,
    )


class TestNdcgAtK:
    def test_pinned_reference_values(self) -> None:
        assert ndcg_at_k([3, 2, 0, 1], [3, 2, 1, 0], 4) == pytest.approx(
            0.9926195041747018,
        )
        assert ndcg_at_k([1, 2, 3], [3, 2, 1], 3) == pytest.approx(0.6806060567602009)

    def test_zero_ideal_dcg_scores_zero(self) -> None:
        assert ndcg_at_k([0, 0, 0], [0, 0], 3) == 0.0

    def test_single_ideal_grade_retrieved_first(self) -> None:
        assert ndcg_at_k([3, 0], [3], 2) == 1.0


class TestHitAtK:
    def test_graded_positive_counts_as_hit(self) -> None:
        assert hit_at_k([0, 2, 0], 10) == 1.0

    def test_all_zero_grades_miss(self) -> None:
        assert hit_at_k([0, 0, 0], 10) == 0.0

    def test_binary_hit(self) -> None:
        assert hit_at_k([1], 10) == 1.0


class TestResolveCorpusRoot:
    def test_relative_declared_root_joins_fixture_directory(self) -> None:
        resolved = resolve_corpus_root(
            {"corpus_root": "corpus"},
            Path("/tmp/pack/queries.json"),
        )
        assert resolved == Path("/tmp/pack/corpus").resolve()

    def test_absolute_declared_root_resolves_as_is(self) -> None:
        resolved = resolve_corpus_root(
            {"corpus_root": "/tmp/abs/corpus"},
            Path("/tmp/pack/queries.json"),
        )
        assert resolved == Path("/tmp/abs/corpus").resolve()
        without_path = resolve_corpus_root({"corpus_root": "/tmp/abs/corpus"}, None)
        assert without_path == Path("/tmp/abs/corpus").resolve()

    def test_relative_declared_root_without_fixture_path_raises(self) -> None:
        with pytest.raises(ValueError, match="corpus_root"):
            resolve_corpus_root({"corpus_root": "corpus"}, None)

    def test_nothing_declared_without_fixture_path_returns_none(self) -> None:
        assert resolve_corpus_root({}, None) is None

    def test_no_declared_root_with_fixture_path_is_fixture_directory(self) -> None:
        resolved = resolve_corpus_root({}, Path("/tmp/pack/queries.json"))
        assert resolved == Path("/tmp/pack").resolve()


class TestResultKey:
    def test_docid_mode_returns_document_id(self) -> None:
        result = _result("/corpus/a.md", document_id="doc-1")
        assert result_key(result, "docid", Path("/corpus")) == "doc-1"

    def test_path_mode_returns_corpus_relative_posix(self, tmp_path: Path) -> None:
        corpus = (tmp_path / "corpus").resolve()
        doc = corpus / "keyword" / "x.md"
        result = _result(str(doc), document_id="doc-1")
        assert result_key(result, "path", corpus) == "keyword/x.md"

    def test_path_mode_falls_back_to_posix_outside_root(self) -> None:
        result = _result("/elsewhere/z.md", document_id="doc-1")
        assert result_key(result, "path", Path("/corpus")) == "/elsewhere/z.md"


def _graded_fixture(tmp_path: Path) -> tuple[dict, Path]:
    """A two-query graded fixture with its on-disk path (corpus need not exist)."""
    fixture = {
        "corpus_root": "corpus",
        "relevance_key": "path",
        "queries": [
            {
                "query": "q1",
                "category": "keyword",
                "split": "tuning",
                "relevance": {"keyword/a.md": 3, "keyword/b.md": 1},
            },
            {
                "query": "q2",
                "category": "synonym",
                "split": "heldout",
                "relevance": {"synonym/c.md": 2},
            },
        ],
    }
    fixture_path = tmp_path / "queries.json"
    fixture_path.write_text(json.dumps(fixture), encoding="utf-8")
    return fixture, fixture_path


class TestSearchEvaluatorCorpusRoot:
    def test_explicit_corpus_root_argument_wins(self, tmp_path: Path) -> None:
        fixture, fixture_path = _graded_fixture(tmp_path)
        evaluator = SearchEvaluator(
            fixture,
            fixture_path=fixture_path,
            corpus_root=tmp_path / "explicit",
        )
        assert evaluator.corpus_root == (tmp_path / "explicit").resolve()

    def test_declared_relative_root_resolves_against_fixture_dir(
        self,
        tmp_path: Path,
    ) -> None:
        fixture, fixture_path = _graded_fixture(tmp_path)
        evaluator = SearchEvaluator(fixture, fixture_path=fixture_path)
        assert evaluator.corpus_root == (tmp_path / "corpus").resolve()

    def test_path_mode_without_resolvable_root_raises(self) -> None:
        fixture = {
            "relevance_key": "path",
            "queries": [
                {
                    "query": "q",
                    "category": "keyword",
                    "split": "tuning",
                    "relevance": {"a.md": 1},
                },
            ],
        }
        with pytest.raises(ValueError, match="corpus_root"):
            SearchEvaluator(fixture)

    def test_unknown_relevance_key_rejected(self) -> None:
        fixture = {
            "relevance_key": "sha256",
            "queries": [{"query": "q", "relevant_docids": ["doc-1"]}],
        }
        with pytest.raises(ValueError, match="relevance_key"):
            SearchEvaluator(fixture)


class TestSearchEvaluatorSchemaValidation:
    def _graded_item(self, **overrides: object) -> dict:
        item: dict = {
            "query": "q",
            "category": "keyword",
            "split": "tuning",
            "relevance": {"a.md": 1},
        }
        item.update(overrides)
        return item

    def test_item_with_both_schemas_rejected(self) -> None:
        fixture = {
            "queries": [
                {
                    "query": "q",
                    "relevant_docids": ["doc-1"],
                    "relevance": {"a.md": 1},
                },
            ],
        }
        with pytest.raises(ValueError, match="both"):
            SearchEvaluator(fixture)

    def test_mixed_schemas_within_fixture_rejected(self) -> None:
        fixture = {
            "queries": [
                {"query": "a", "relevant_docids": ["doc-1"]},
                self._graded_item(),
            ],
        }
        with pytest.raises(ValueError, match="schema"):
            SearchEvaluator(fixture)

    def test_unknown_category_rejected(self) -> None:
        fixture = {"queries": [self._graded_item(category="mystery")]}
        with pytest.raises(ValueError, match="category"):
            SearchEvaluator(fixture)

    def test_unknown_split_rejected(self) -> None:
        fixture = {"queries": [self._graded_item(split="dev")]}
        with pytest.raises(ValueError, match="split"):
            SearchEvaluator(fixture)

    def test_grade_out_of_range_rejected(self) -> None:
        fixture = {"queries": [self._graded_item(relevance={"a.md": 4})]}
        with pytest.raises(ValueError, match="grade"):
            SearchEvaluator(fixture)


class TestReportGradedFixture:
    def test_graded_fixture_reports_end_to_end(self, tmp_path: Path) -> None:
        fixture, fixture_path = _graded_fixture(tmp_path)
        corpus = tmp_path / "corpus"

        def search_fn(query: str) -> list[SearchResult]:
            if query == "q1":
                return [
                    _result(str(corpus / "keyword" / "a.md"), "d1", 0.9),
                    _result(str(corpus / "keyword" / "x.md"), "d2", 0.8),
                ]
            return [_result(str(corpus / "synonym" / "c.md"), "d3", 0.7)]

        evaluator = SearchEvaluator(fixture, fixture_path=fixture_path)
        report = evaluator.report(search_fn)

        assert report.ndcg_at_10 > 0.0
        assert report.hit_at_10 > 0.0
        data = report.to_dict()
        assert list(data["categories"].keys()) == list(CATEGORIES)
        assert data["categories"]["keyword"]["count"] == 1
        assert data["categories"]["synonym"]["count"] == 1
        assert data["categories"]["rival"]["count"] == 0
        assert data["ndcg_at_10"] == pytest.approx(report.ndcg_at_10)

    def test_per_category_breakdown_is_repeatable(self, tmp_path: Path) -> None:
        fixture, fixture_path = _graded_fixture(tmp_path)
        corpus = tmp_path / "corpus"

        def search_fn(_query: str) -> list[SearchResult]:
            return [_result(str(corpus / "keyword" / "a.md"), "d1", 0.9)]

        evaluator = SearchEvaluator(fixture, fixture_path=fixture_path)
        first = evaluator.report(search_fn).to_dict()
        second = evaluator.report(search_fn).to_dict()
        assert first["categories"] == second["categories"]


class TestReportLegacyFixture:
    def test_legacy_item_evaluates_through_report(self) -> None:
        fixture = {"queries": [{"query": "t", "relevant_docids": ["doc-1"]}]}

        def search_fn(_query: str) -> list[SearchResult]:
            return [
                _result("/1", document_id="doc-1", score=0.9),
                _result("/9", document_id="doc-9", score=0.8),
            ]

        report = SearchEvaluator(fixture).report(search_fn)
        data = report.to_dict()
        assert data["mrr"] == 1.0
        assert data["precision@1"] == 1.0
        assert report.num_queries == 1
        # Legacy items carry no category: every category count stays 0 while
        # all four keys remain present in declared order.
        assert [report.categories[c].count for c in CATEGORIES] == [0, 0, 0, 0]
        assert list(data["categories"].keys()) == list(CATEGORIES)


class TestEmptyQueriesGuard:
    def test_empty_queries_list_rejected(self) -> None:
        with pytest.raises(ValueError, match="non-empty 'queries'"):
            SearchEvaluator({"queries": []})


class TestBinaryPrecisionRecall:
    def test_graded_precision_never_exceeds_one(self) -> None:
        assert precision_at_k([3, 3, 3], 3) == 1.0
        assert precision_at_k([3, 2, 0], 3) == pytest.approx(2 / 3)
        assert precision_at_k([3, 3, 3, 3, 3], 10) == 0.5

    def test_graded_recall_never_exceeds_one(self) -> None:
        assert recall_at_k([3, 3], 2, 2) == 1.0
        assert recall_at_k([3, 0], 2, 2) == 0.5

    def test_legacy_zero_one_vectors_unchanged(self) -> None:
        assert precision_at_k([1, 0, 1, 0, 0], 4) == 0.5
        assert recall_at_k([1, 0, 0, 1], 4, 4) == 0.5


class TestEvaluateGradedFixture:
    def test_evaluate_accepts_graded_fixture_flat_keys(self, tmp_path: Path) -> None:
        fixture, fixture_path = _graded_fixture(tmp_path)
        corpus = tmp_path / "corpus"

        def search_fn(query: str) -> list[SearchResult]:
            if query == "q1":
                return [_result(str(corpus / "keyword" / "a.md"), "d1", 0.9)]
            return [_result(str(corpus / "synonym" / "c.md"), "d3", 0.7)]

        results = SearchEvaluator(fixture, fixture_path=fixture_path).evaluate(
            search_fn,
            k_values=[1, 5],
        )
        assert results["num_queries"] == 2.0
        assert results["precision@1"] == 1.0
        # q1 retrieves 1 of its 2 relevant docs; q2 retrieves its only one.
        assert results["recall@5"] == pytest.approx(0.75)
        assert results["mrr"] == 1.0
        assert all(value <= 1.0 for key, value in results.items() if key != "num_queries")


class TestPercentile:
    def test_p50_interpolates_between_closest_ranks(self) -> None:
        values = [float(i) for i in range(1, 11)]
        assert percentile(values, 50) == pytest.approx(5.5)

    def test_p95_interpolates_between_closest_ranks(self) -> None:
        values = [float(i) for i in range(1, 11)]
        assert percentile(values, 95) == pytest.approx(9.55)

    def test_empty_values_return_zero(self) -> None:
        assert percentile([], 50) == 0.0

    def test_single_value_returns_itself(self) -> None:
        assert percentile([3.0], 95) == 3.0


def _stepping_clock(step: float = 0.001) -> Callable[[], float]:
    """Injectable clock advancing a fixed step per call.

    Every clock-delimited span (one search call) therefore measures
    ``step * 1000`` milliseconds, so latency assertions are structural
    rather than wall-clock (research Pitfall 6).
    """
    state = {"now": 0.0}

    def clock() -> float:
        state["now"] += step
        return state["now"]

    return clock


class TestMeasureQueryTimes:
    def test_warmup_pass_contributes_no_samples(self) -> None:
        calls: list[str] = []

        def fake_search(query: str) -> list[SearchResult]:
            calls.append(query)
            return [_result("/1", document_id="d1")]

        times, outputs = measure_query_times(fake_search, ["a", "b"], _stepping_clock())
        # Warm-up pass first (results discarded), then the timed pass.
        assert calls == ["a", "b", "a", "b"]
        assert len(times) == 2
        assert times == pytest.approx([1.0, 1.0])
        assert [len(out) for out in outputs] == [1, 1]


class TestReportLatency:
    def test_report_with_injected_clock(self, tmp_path: Path) -> None:
        fixture, fixture_path = _graded_fixture(tmp_path)
        corpus = tmp_path / "corpus"

        def search_fn(query: str) -> list[SearchResult]:
            if query == "q1":
                return [_result(str(corpus / "keyword" / "a.md"), "d1", 0.9)]
            return [_result(str(corpus / "synonym" / "c.md"), "d3", 0.7)]

        evaluator = SearchEvaluator(fixture, fixture_path=fixture_path)
        report = evaluator.report(search_fn, clock=_stepping_clock())

        assert report.p50_ms <= report.p95_ms
        assert report.p50_ms == pytest.approx(1.0)
        assert report.p95_ms == pytest.approx(1.0)
        # Cold start is the first warm-up call, reported separately and never
        # a p50/p95 sample (D-05).
        assert report.cold_start_ms == pytest.approx(1.0)
        # Metrics still come from the timed pass results.
        assert report.ndcg_at_10 > 0.0
