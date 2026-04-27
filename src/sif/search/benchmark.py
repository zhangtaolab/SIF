"""Benchmark evaluation for search quality."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Callable

from docsift.core.models import SearchResult
from docsift.utils.logging import get_logger


logger = get_logger(__name__)


def precision_at_k(relevance: Sequence[int], k: int) -> float:
    """Precision@K: relevant items in top-K / K."""
    if k == 0:
        return 0.0
    return sum(relevance[:k]) / k


def recall_at_k(relevance: Sequence[int], total_relevant: int, k: int) -> float:
    """Recall@K: relevant items retrieved / total relevant."""
    if total_relevant == 0:
        return 0.0
    return sum(relevance[:k]) / total_relevant


def reciprocal_rank(relevance: Sequence[int]) -> float:
    """Reciprocal rank: 1 / rank of first relevant item."""
    for i, rel in enumerate(relevance, start=1):
        if rel:
            return 1.0 / i
    return 0.0


def mean_reciprocal_rank(all_relevance: list[Sequence[int]]) -> float:
    """Mean Reciprocal Rank across queries."""
    rr_scores = [reciprocal_rank(r) for r in all_relevance]
    return sum(rr_scores) / len(rr_scores) if rr_scores else 0.0


class SearchEvaluator:
    """Evaluate search quality against a benchmark fixture."""

    def __init__(self, fixture: dict) -> None:
        """Initialize with fixture data.

        Args:
            fixture: Dictionary with keys:
                - queries: list of {query: str, relevant_docids: list[str], collections?: list[str]}
        """
        self.fixture = fixture
        self._validate_fixture()

    def _validate_fixture(self) -> None:
        """Validate fixture format."""
        if "queries" not in self.fixture:
            raise ValueError("Fixture must contain 'queries' key")
        for i, item in enumerate(self.fixture["queries"]):
            if "query" not in item:
                raise ValueError(f"Query {i} missing 'query' field")
            if "relevant_docids" not in item:
                raise ValueError(f"Query {i} missing 'relevant_docids' field")

    def evaluate(
        self,
        search_fn: Callable[[str], list[SearchResult]],
        k_values: list[int] | None = None,
    ) -> dict[str, float]:
        """Evaluate search quality.

        Args:
            search_fn: Function that takes a query string and returns SearchResult list
            k_values: List of k values for precision/recall@k. Default: [1, 5, 10]

        Returns:
            Dictionary of averaged metrics
        """
        k_values = k_values or [1, 5, 10]
        metrics: dict[str, list[float]] = {}
        all_relevance: list[Sequence[int]] = []

        for query_item in self.fixture["queries"]:
            query = query_item["query"]
            relevant_ids = set(query_item["relevant_docids"])

            # Run search
            results = search_fn(query)
            result_ids = [r.document_id for r in results]

            # Build relevance vector
            relevance = [1 if rid in relevant_ids else 0 for rid in result_ids]
            all_relevance.append(relevance)

            # Compute metrics for each k
            for k in k_values:
                metrics.setdefault(f"precision@{k}", []).append(precision_at_k(relevance, k))
                metrics.setdefault(f"recall@{k}", []).append(
                    recall_at_k(relevance, len(relevant_ids), k)
                )

        # Average across queries
        averaged: dict[str, float] = {}
        for key, values in metrics.items():
            averaged[key] = sum(values) / len(values) if values else 0.0
        averaged["mrr"] = mean_reciprocal_rank(all_relevance)
        averaged["num_queries"] = float(len(self.fixture["queries"]))

        return averaged
