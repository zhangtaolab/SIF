"""Tests for benchmark metrics."""

import pytest

from sif.core.models import SearchResult
from sif.search.benchmark import (
    SearchEvaluator,
    mean_reciprocal_rank,
    precision_at_k,
    recall_at_k,
    reciprocal_rank,
)


class TestPrecisionAtK:
    def test_perfect_precision(self) -> None:
        relevance = [1, 1, 1, 1, 1]
        assert precision_at_k(relevance, 3) == 1.0

    def test_zero_precision(self) -> None:
        relevance = [0, 0, 0]
        assert precision_at_k(relevance, 2) == 0.0

    def test_mixed_precision(self) -> None:
        relevance = [1, 0, 1, 0, 0]
        assert precision_at_k(relevance, 4) == 0.5

    def test_k_larger_than_results(self) -> None:
        relevance = [1, 0]
        assert precision_at_k(relevance, 5) == 0.2

    def test_k_zero(self) -> None:
        assert precision_at_k([1, 1], 0) == 0.0


class TestRecallAtK:
    def test_perfect_recall(self) -> None:
        relevance = [1, 1, 1]
        assert recall_at_k(relevance, 3, 3) == 1.0

    def test_partial_recall(self) -> None:
        relevance = [1, 0, 0, 1]
        assert recall_at_k(relevance, 4, 4) == 0.5

    def test_zero_total_relevant(self) -> None:
        assert recall_at_k([0, 0], 0, 2) == 0.0

    def test_k_larger_than_results(self) -> None:
        relevance = [1, 0]
        assert recall_at_k(relevance, 5, 5) == 0.2


class TestReciprocalRank:
    def test_first_relevant(self) -> None:
        assert reciprocal_rank([1, 0, 0]) == 1.0

    def test_second_relevant(self) -> None:
        assert reciprocal_rank([0, 1, 0]) == 0.5

    def test_no_relevant(self) -> None:
        assert reciprocal_rank([0, 0, 0]) == 0.0

    def test_third_relevant(self) -> None:
        assert reciprocal_rank([0, 0, 1]) == pytest.approx(1.0 / 3.0)


class TestMeanReciprocalRank:
    def test_single_query(self) -> None:
        assert mean_reciprocal_rank([[0, 1, 0]]) == 0.5

    def test_multiple_queries(self) -> None:
        assert mean_reciprocal_rank([[1, 0], [0, 1]]) == 0.75

    def test_empty_list(self) -> None:
        assert mean_reciprocal_rank([]) == 0.0


class TestSearchEvaluator:
    def test_evaluate_single_query(self) -> None:
        fixture = {
            "queries": [
                {"query": "test", "relevant_docids": ["doc-1", "doc-2"]},
            ]
        }
        evaluator = SearchEvaluator(fixture)

        def mock_search(query: str) -> list[SearchResult]:
            return [
                SearchResult(
                    document_id="doc-1",
                    title="T1",
                    path="/1",
                    collection_name="c",
                    score=0.9,
                ),
                SearchResult(
                    document_id="doc-3",
                    title="T3",
                    path="/3",
                    collection_name="c",
                    score=0.8,
                ),
                SearchResult(
                    document_id="doc-2",
                    title="T2",
                    path="/2",
                    collection_name="c",
                    score=0.7,
                ),
            ]

        results = evaluator.evaluate(mock_search, k_values=[1, 3])
        assert results["precision@1"] == 1.0
        assert results["recall@3"] == 1.0
        assert results["mrr"] == 1.0

    def test_evaluate_multiple_queries(self) -> None:
        fixture = {
            "queries": [
                {"query": "q1", "relevant_docids": ["doc-a"]},
                {"query": "q2", "relevant_docids": ["doc-b"]},
            ]
        }
        evaluator = SearchEvaluator(fixture)

        def mock_search(query: str) -> list[SearchResult]:
            if query == "q1":
                return [
                    SearchResult(
                        document_id="doc-a",
                        title="A",
                        path="/a",
                        collection_name="c",
                        score=0.9,
                    ),
                ]
            return [
                SearchResult(
                    document_id="doc-x",
                    title="X",
                    path="/x",
                    collection_name="c",
                    score=0.9,
                ),
            ]

        results = evaluator.evaluate(mock_search, k_values=[1])
        assert results["precision@1"] == 0.5
        assert results["mrr"] == 0.5

    def test_validate_fixture_missing_queries(self) -> None:
        with pytest.raises(ValueError, match="queries"):
            SearchEvaluator({})

    def test_validate_fixture_missing_relevant_docids(self) -> None:
        with pytest.raises(ValueError, match="relevant_docids"):
            SearchEvaluator({"queries": [{"query": "test"}]})
