"""Reciprocal Rank Fusion (RRF) implementation."""

from __future__ import annotations

from sif.core.models import SearchResult


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

        Returns:
            Fused and re-ranked list of results
        """
        if weights is not None and len(results_lists) != len(weights):
            raise ValueError("Number of result lists must match number of weights")

        # Effective k for this call (None -> constructor default)
        k_eff = self.k if k is None else k

        # Map document_id to scores
        scores: dict[str, tuple[float, SearchResult]] = {}

        for list_idx, results in enumerate(results_lists):
            # Effective weight: 1.0 when unconfigured. IEEE ``1.0 * x == x``
            # is exact, so the default path stays byte-identical to the
            # pre-change plain division (SC1 golden pin).
            weight = 1.0 if weights is None else weights[list_idx]
            for rank, result in enumerate(results, 1):
                doc_id = result.document_id

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

                if doc_id in scores:
                    existing_score, existing_result = scores[doc_id]
                    # Merge scores from existing result
                    merged_scores: dict[str, float | None] = {}
                    if existing_result.scores:
                        merged_scores.update(existing_result.scores)
                    merged_scores.update(doc_scores)
                    scores[doc_id] = (existing_score + rrf_score, existing_result)
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
                    )
                    scores[doc_id] = (rrf_score, new_result)

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
