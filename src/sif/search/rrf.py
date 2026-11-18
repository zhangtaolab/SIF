"""Reciprocal Rank Fusion (RRF) implementation."""

from __future__ import annotations

from collections.abc import Callable

from sif.core.models import SearchResult


def chunk_key(result: SearchResult) -> str:
    """Fusion key for chunk-level rows: chunk identity, else the document id.

    BM25 runs at document level and carries no chunk id, so its rows stay
    document-keyed even in per-chunk mode — a hybrid per-chunk page may carry
    the BM25 document row alongside its vector chunk rows (CORR-02/D-01).
    """
    return result.chunk_id or result.document_id


def fuse_key_for(per_chunk: bool) -> Callable[[SearchResult], str] | None:
    """Return the shared fusion grouping key for a search mode.

    Both fuse sites that can receive chunk rows — ``HybridSearcher.search``'s
    source fusion and ``SearchPipeline.search``'s cross-query variant fusion —
    select their key through this helper. ``None`` means the default
    document-keyed behavior, so RRF scoring math never depends on the mode.
    """
    return chunk_key if per_chunk else None


def _document_key(result: SearchResult) -> str:
    """Default fusion key: one fused row per document."""
    return result.document_id


def _merge_chunk_metadata(existing: SearchResult, later: SearchResult) -> None:
    """Adopt non-null chunk identity from a later row; keep the max count.

    Metadata merging only (T-19-14): a document found by both legs keeps the
    vector leg's chunk_id/sequence even though the stored result object came
    from the first (BM25) list, and chunk_matches never shrinks.
    """
    if later.chunk_id is not None:
        existing.chunk_id = later.chunk_id
    if later.sequence is not None:
        existing.sequence = later.sequence
    existing.chunk_matches = max(existing.chunk_matches, later.chunk_matches)


class RRFFusion:
    """Reciprocal Rank Fusion for combining search results."""

    def __init__(self, k: int = 60) -> None:
        """Initialize RRF with k parameter.

        Args:
            k: Constant to prevent division by zero and dampen
               the impact of low rankings. Default is 60.
        """
        self.k = k

    def fuse(
        self,
        results_lists: list[list[SearchResult]],
        limit: int = 10,
        weights: list[float] | None = None,
        k: int | None = None,
        key: Callable[[SearchResult], str] | None = None,
    ) -> list[SearchResult]:
        """Fuse multiple ranked lists using RRF.

        Args:
            results_lists: List of ranked result lists
            limit: Maximum number of results to return
            weights: Optional per-list weight in multiply form
                (``weight * 1/(k + rank)``). ``None`` means 1.0 for every
                list. Weights are NEVER normalized (Phase 15 D-01/SC1:
                normalizing halves every score at equal weights).
            k: Optional RRF constant for this call; ``None`` falls back to
                ``self.k``.
            key: Optional grouping key. ``None`` groups by ``document_id``;
                per-chunk mode passes ``chunk_key`` so chunk rows survive
                fusion. The key only decides which rows merge — the scoring
                arithmetic is identical in both modes.

        Returns:
            Fused and re-ranked list of results
        """
        if weights is not None and len(results_lists) != len(weights):
            raise ValueError("Number of result lists must match number of weights")

        # Effective k for this call (None -> constructor default)
        k_eff = self.k if k is None else k
        key_fn = _document_key if key is None else key

        # Map grouping key to scores
        scores: dict[str, tuple[float, SearchResult]] = {}

        for list_idx, results in enumerate(results_lists):
            # Effective weight: 1.0 when unconfigured. IEEE ``1.0 * x == x``
            # is exact, so the default path stays byte-identical to the
            # pre-change plain division (SC1 golden pin).
            weight = 1.0 if weights is None else weights[list_idx]
            for rank, result in enumerate(results, 1):
                group_key = key_fn(result)

                # Calculate RRF score: weight / (k + rank) — multiply form only
                rrf_score = weight * (1.0 / (k_eff + rank))

                # Build scores dict
                doc_scores: dict[str, float | None] = {}
                if result.scores:
                    doc_scores.update(result.scores)

                # Track original score from this list
                score_key = "bm25_score" if list_idx == 0 else "vector_score"
                if score_key not in doc_scores:
                    doc_scores[score_key] = result.score

                if group_key in scores:
                    existing_score, existing_result = scores[group_key]
                    # Merge scores from existing result
                    merged_scores: dict[str, float | None] = {}
                    if existing_result.scores:
                        merged_scores.update(existing_result.scores)
                    merged_scores.update(doc_scores)
                    # Metadata merge only (T-19-14); RRF scores are untouched.
                    _merge_chunk_metadata(existing_result, result)
                    scores[group_key] = (existing_score + rrf_score, existing_result)
                    # Update the stored result's scores
                    existing_result.scores = merged_scores
                else:
                    new_result = SearchResult(
                        document_id=result.document_id,
                        title=result.title,
                        path=result.path,
                        collection_name=result.collection_name,
                        score=rrf_score,
                        content=result.content,
                        highlights=result.highlights,
                        rank=rank,
                        scores=doc_scores,
                        snippet=result.snippet,
                        context_description=result.context_description,
                        chunk_id=result.chunk_id,
                        sequence=result.sequence,
                        chunk_matches=result.chunk_matches,
                    )
                    scores[group_key] = (rrf_score, new_result)

        # Sort by RRF score (descending)
        sorted_scores = sorted(scores.items(), key=lambda x: x[1][0], reverse=True)

        # Build final results
        fused_results = []
        for rank, (_doc_id, (score, result)) in enumerate(sorted_scores[:limit], 1):
            result.score = score
            result.rank = rank
            result.scores["rrf_score"] = score
            fused_results.append(result)

        return fused_results
