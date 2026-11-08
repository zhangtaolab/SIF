"""Benchmark evaluation for search quality."""

from __future__ import annotations

import math
import time
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from sif.core.models import SearchResult
from sif.utils.logging import get_logger


logger = get_logger(__name__)

# Fixed reporting categories and splits (Phase 16, D-03/D-06): every report
# carries all four category keys in this declared order so the per-category
# breakdown is byte-identical across runs and consumers can diff it directly.
CATEGORIES: tuple[str, ...] = ("keyword", "synonym", "multilingual", "rival")
SPLITS: tuple[str, ...] = ("tuning", "heldout")
LEGACY_K_VALUES: tuple[int, ...] = (1, 5, 10)
GRADE_MIN = 0
GRADE_MAX = 3
DEFAULT_K = 10


def _mean(values: Sequence[float]) -> float:
    """Arithmetic mean; empty input yields 0.0 (house style)."""
    return sum(values) / len(values) if values else 0.0


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


def dcg_at_k(grades: Sequence[int], k: int) -> float:
    """Discounted cumulative gain with exponential gain (2^rel - 1).

    Position i starts at 1, so the discount is log2(i + 1) over grades[:k].
    """
    return sum((2**grade - 1) / math.log2(i + 1) for i, grade in enumerate(grades[:k], 1))


def ndcg_at_k(retrieved: Sequence[int], ideal: Sequence[int], k: int) -> float:
    """Normalized DCG@K: DCG of the retrieved ranking over the ideal DCG.

    The ideal DCG is computed from the FULL judgment set for the query
    (``ideal`` sorted descending), not the retrieved subset; a query whose
    ideal DCG is 0 scores 0.0 instead of dividing by zero.
    """
    ideal_dcg = dcg_at_k(sorted(ideal, reverse=True), k)
    if ideal_dcg == 0.0:
        return 0.0
    return dcg_at_k(retrieved, k) / ideal_dcg


def hit_at_k(retrieved: Sequence[int], k: int) -> float:
    """Hit@K: 1.0 iff any of the top-K retrieved grades is positive."""
    return 1.0 if any(grade > 0 for grade in retrieved[:k]) else 0.0


def percentile(values: Sequence[float], p: float) -> float:
    """Percentile via linear interpolation between closest ranks; p in [0, 100]."""
    if not values:
        return 0.0
    ordered = sorted(values)
    pos = (len(ordered) - 1) * (p / 100.0)
    lo = math.floor(pos)
    hi = min(lo + 1, len(ordered) - 1)
    return ordered[lo] + (ordered[hi] - ordered[lo]) * (pos - lo)


def measure_query_times(
    search_fn: Callable[[str], list[SearchResult]],
    queries: Sequence[str],
    clock: Callable[[], float] = time.perf_counter,
) -> tuple[list[float], list[list[SearchResult]]]:
    """Warmed per-query latency: discard one warm-up pass, then time each query.

    The warm-up pass (model load, caches hot) is fully discarded so it never
    enters the percentile samples (D-05); each timed sample is one search
    call's wall-clock duration in milliseconds, with the results retained.
    """
    for query in queries:  # warm-up: results discarded
        search_fn(query)
    samples: list[float] = []
    outputs: list[list[SearchResult]] = []
    for query in queries:
        start = clock()
        outputs.append(search_fn(query))
        samples.append((clock() - start) * 1000.0)
    return samples, outputs


def _cold_start_wrapper(
    search_fn: Callable[[str], list[SearchResult]],
    clock: Callable[[], float],
) -> tuple[Callable[[str], list[SearchResult]], list[float]]:
    """Wrap search_fn so the very first call's duration is captured separately.

    The captured sample is the cold start (first warm-up call) and never
    joins the warmed p50/p95 samples.
    """
    samples: list[float] = []

    def wrapped(query: str) -> list[SearchResult]:
        if not samples:
            start = clock()
            results = search_fn(query)
            samples.append((clock() - start) * 1000.0)
            return results
        return search_fn(query)

    return wrapped, samples


def resolve_corpus_root(fixture: dict, fixture_path: Path | None) -> Path | None:
    """Resolve the fixture's corpus root — the single corpus-root rule.

    - Nothing declared, no fixture_path: None (docid-keyed fixtures need none).
    - Absolute declared ``corpus_root``: resolved as-is.
    - Relative declared ``corpus_root``: joined onto the fixture file's
      directory and resolved (never the fixture's parent alone).
    - No declared root but a fixture_path: the fixture's directory.

    Never opens a relevance key or result path; resolution is read-only.
    """
    declared = fixture.get("corpus_root")
    if declared is None:
        if fixture_path is None:
            return None
        return fixture_path.parent.resolve()
    declared_path = Path(declared)
    if declared_path.is_absolute():
        return declared_path.resolve()
    if fixture_path is None:
        raise ValueError(
            "Fixture declares a relative 'corpus_root' but no fixture_path was "
            "provided to resolve it against"
        )
    return (fixture_path.parent / declared_path).resolve()


def result_key(result: SearchResult, mode: str, corpus_root: Path) -> str:
    """Compute the fixture-comparison key for one search result.

    ``docid`` mode returns the document id; any other mode is path-keyed: the
    result path resolved relative to ``corpus_root`` as a POSIX string, falling
    back to the plain POSIX path when the result lies outside the root. Never
    opens the result path.
    """
    if mode == "docid":
        return result.document_id
    try:
        return Path(result.path).resolve().relative_to(corpus_root).as_posix()
    except ValueError:
        return Path(result.path).as_posix()


@dataclass
class QueryItem:
    """One benchmark query and its relevance judgments.

    ``grades`` maps fixture keys (document ids for legacy fixtures, corpus-
    relative POSIX paths for graded fixtures) to grades; legacy items map each
    relevant docid to grade 1 and leave category/split as None.
    """

    query: str
    category: str | None = None
    split: str | None = None
    grades: dict[str, int] = field(default_factory=dict)


@dataclass
class CategoryMetrics:
    """Aggregated graded metrics for one reporting category."""

    ndcg_at_10: float
    hit_at_10: float
    count: int


@dataclass
class BenchReport:
    """Graded benchmark report: nDCG/Hit plus the legacy flat metrics.

    ``legacy_metrics`` carries the pre-change flat keys (``mrr``,
    ``precision@<k>``, ``recall@<k>``) so table and ``--json`` output stay
    backward compatible; ``to_dict`` merges them at the top level.
    """

    ndcg_at_10: float
    hit_at_10: float
    num_queries: int
    categories: dict[str, CategoryMetrics]
    cold_start_ms: float | None = None
    p50_ms: float = 0.0
    p95_ms: float = 0.0
    legacy_metrics: dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Serialize with categories in CATEGORIES order and legacy keys merged."""
        categories: dict[str, Any] = {}
        for category in CATEGORIES:
            metrics = self.categories.get(category)
            if metrics is None:
                continue
            categories[category] = {
                "ndcg_at_10": metrics.ndcg_at_10,
                "hit_at_10": metrics.hit_at_10,
                "count": metrics.count,
            }
        data: dict[str, Any] = {
            "ndcg_at_10": self.ndcg_at_10,
            "hit_at_10": self.hit_at_10,
            "num_queries": self.num_queries,
            "cold_start_ms": self.cold_start_ms,
            "p50_ms": self.p50_ms,
            "p95_ms": self.p95_ms,
            "categories": categories,
        }
        data.update(self.legacy_metrics)
        return data


class SearchEvaluator:
    """Evaluate search quality against a benchmark fixture."""

    def __init__(
        self,
        fixture: dict,
        fixture_path: Path | None = None,
        corpus_root: Path | None = None,
    ) -> None:
        """Initialize with fixture data.

        Args:
            fixture: Dictionary with keys:
                - queries: list of {query, relevant_docids, collections?} (legacy)
                  or {query, category, split, relevance} (graded, Phase 16)
                - relevance_key: "docid" (default) or "path"
                - corpus_root: root for path-keyed relevance
            fixture_path: Path to the fixture file; a relative declared
                corpus_root is resolved against its directory.
            corpus_root: Explicit corpus root; wins over the declared value.

        The root is resolved exactly once here and stored on ``corpus_root``.
        """
        self.fixture = fixture
        self.relevance_key = str(fixture.get("relevance_key", "docid"))
        if self.relevance_key not in ("docid", "path"):
            raise ValueError(
                f"Fixture 'relevance_key' must be 'docid' or 'path', got {self.relevance_key!r}"
            )
        # Explicit corpus_root argument wins; else the fixture-declared rule.
        self.corpus_root = (
            Path(corpus_root).resolve()
            if corpus_root is not None
            else resolve_corpus_root(fixture, fixture_path)
        )
        if self.relevance_key == "path" and self.corpus_root is None:
            raise ValueError(
                "Fixture declares path-keyed relevance but no corpus_root could "
                "be resolved; declare 'corpus_root' or pass fixture_path"
            )
        self.query_items: list[QueryItem] = []
        self._validate_fixture()

    def _validate_fixture(self) -> None:
        """Validate fixture format and parse query items."""
        if "queries" not in self.fixture:
            raise ValueError("Fixture must contain 'queries' key")
        schema: str | None = None
        for i, item in enumerate(self.fixture["queries"]):
            if "query" not in item:
                raise ValueError(f"Query {i} missing 'query' field")
            has_legacy = "relevant_docids" in item
            has_graded = "relevance" in item
            if has_legacy and has_graded:
                raise ValueError(f"Query {i} carries both 'relevant_docids' and 'relevance'")
            if not has_legacy and not has_graded:
                raise ValueError(f"Query {i} missing 'relevant_docids' or 'relevance' field")
            kind = "legacy" if has_legacy else "graded"
            if schema is None:
                schema = kind
            elif schema != kind:
                raise ValueError(
                    f"Query {i} uses the {kind!r} schema but earlier queries "
                    f"used the {schema!r} schema; a fixture must pick one"
                )
            if kind == "graded":
                self.query_items.append(self._parse_graded_item(i, item))
            else:
                # Legacy items: relevance maps docid -> grade 1; no category
                # or split, so they never feed the per-category breakdown.
                grades = {str(docid): 1 for docid in item["relevant_docids"]}
                self.query_items.append(QueryItem(query=str(item["query"]), grades=grades))

    def _parse_graded_item(self, index: int, item: dict[str, Any]) -> QueryItem:
        """Validate one graded query item and build its QueryItem."""
        category = item.get("category")
        if category not in CATEGORIES:
            raise ValueError(
                f"Query {index} has invalid 'category' {category!r}; "
                f"expected one of: {', '.join(CATEGORIES)}"
            )
        split = item.get("split")
        if split not in SPLITS:
            raise ValueError(
                f"Query {index} has invalid 'split' {split!r}; expected one of: {', '.join(SPLITS)}"
            )
        relevance = item.get("relevance")
        if not isinstance(relevance, dict):
            raise ValueError(f"Query {index} 'relevance' must map keys to grades")
        grades: dict[str, int] = {}
        for key, grade in relevance.items():
            if (
                not isinstance(grade, int)
                or isinstance(grade, bool)
                or not GRADE_MIN <= grade <= GRADE_MAX
            ):
                raise ValueError(
                    f"Query {index} 'relevance' grade for {key!r} must be an "
                    f"integer in {GRADE_MIN}..{GRADE_MAX}"
                )
            grades[str(key)] = grade
        return QueryItem(
            query=str(item["query"]),
            category=category,
            split=split,
            grades=grades,
        )

    def _grades_for(self, item: QueryItem, results: list[SearchResult]) -> list[int]:
        """Retrieved grades in rank order for one query's results."""
        root = self.corpus_root if self.corpus_root is not None else Path()
        keys = [result_key(result, self.relevance_key, root) for result in results]
        return [item.grades.get(key, 0) for key in keys]

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
                    recall_at_k(relevance, len(relevant_ids), k),
                )

        # Average across queries
        averaged: dict[str, float] = {}
        for key, values in metrics.items():
            averaged[key] = sum(values) / len(values) if values else 0.0
        averaged["mrr"] = mean_reciprocal_rank(all_relevance)
        averaged["num_queries"] = float(len(self.fixture["queries"]))

        return averaged

    def report(
        self,
        search_fn: Callable[[str], list[SearchResult]],
        k: int = DEFAULT_K,
        k_values: Sequence[int] = LEGACY_K_VALUES,
        clock: Callable[[], float] | None = None,
    ) -> BenchReport:
        """Run every fixture query and produce a graded BenchReport.

        Exactly one ``search_fn`` result list per query supplies both the
        graded metrics (nDCG@k / Hit@k) and the legacy flat metrics. Global
        metrics include every query; the category breakdown aggregates only
        items whose category is one of CATEGORIES, with all four keys always
        present in declared order (legacy items leave every count at 0).

        With a ``clock``, latency is warmed: one discarded warm-up pass runs
        first (its first call is reported separately as the cold start and
        never enters the p50/p95 samples, D-05), then the timed pass supplies
        both the metrics and the percentile samples. Without a clock the
        latency fields keep their defaults.
        """
        queries = [item.query for item in self.query_items]
        times: list[float] = []
        cold_start_ms: float | None = None
        if clock is not None:
            timed_fn, cold_samples = _cold_start_wrapper(search_fn, clock)
            times, results_by_query = measure_query_times(timed_fn, queries, clock)
            cold_start_ms = cold_samples[0] if cold_samples else None
        else:
            results_by_query = [search_fn(query) for query in queries]

        ndcgs: list[float] = []
        hits: list[float] = []
        all_binary: list[Sequence[int]] = []
        legacy: dict[str, list[float]] = {}
        category_values: dict[str, tuple[list[float], list[float]]] = {
            category: ([], []) for category in CATEGORIES
        }

        for item, results in zip(self.query_items, results_by_query, strict=True):
            retrieved = self._grades_for(item, results)
            ideal = list(item.grades.values())
            # Legacy metrics stay binary (grade > 0) so graded fixtures can
            # never push precision/recall above 1.0 (research Pitfall 8).
            binary = [1 if grade > 0 else 0 for grade in retrieved]
            total_relevant = sum(1 for grade in item.grades.values() if grade > 0)
            query_ndcg = ndcg_at_k(retrieved, ideal, k)
            query_hit = hit_at_k(retrieved, k)
            ndcgs.append(query_ndcg)
            hits.append(query_hit)
            all_binary.append(binary)
            for legacy_k in k_values:
                legacy.setdefault(f"precision@{legacy_k}", []).append(
                    precision_at_k(binary, legacy_k),
                )
                legacy.setdefault(f"recall@{legacy_k}", []).append(
                    recall_at_k(binary, total_relevant, legacy_k),
                )
            if item.category in category_values:
                category_ndcg, category_hit = category_values[item.category]
                category_ndcg.append(query_ndcg)
                category_hit.append(query_hit)

        legacy_metrics = {key: _mean(values) for key, values in legacy.items()}
        legacy_metrics["mrr"] = mean_reciprocal_rank(all_binary)
        categories = {
            category: CategoryMetrics(
                ndcg_at_10=_mean(values[0]),
                hit_at_10=_mean(values[1]),
                count=len(values[0]),
            )
            for category, values in category_values.items()
        }
        return BenchReport(
            ndcg_at_10=_mean(ndcgs),
            hit_at_10=_mean(hits),
            num_queries=len(self.query_items),
            categories=categories,
            cold_start_ms=cold_start_ms,
            p50_ms=percentile(times, 50),
            p95_ms=percentile(times, 95),
            legacy_metrics=legacy_metrics,
        )
