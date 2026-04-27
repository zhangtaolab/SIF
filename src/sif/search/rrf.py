"""Reciprocal Rank Fusion (RRF) implementation."""

from __future__ import annotations

from typing import Dict, List, Optional, Tuple

from docsift.core.models import SearchResult


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
        results_lists: List[List[SearchResult]],
        limit: int = 10,
    ) -> List[SearchResult]:
        """Fuse multiple ranked lists using RRF.

        Args:
            results_lists: List of ranked result lists
            limit: Maximum number of results to return

        Returns:
            Fused and re-ranked list of results
        """
        # Map document_id to scores
        scores: Dict[str, Tuple[float, SearchResult]] = {}

        for list_idx, results in enumerate(results_lists):
            for rank, result in enumerate(results, 1):
                doc_id = result.document_id

                # Calculate RRF score: 1 / (k + rank)
                rrf_score = 1.0 / (self.k + rank)

                # Build scores dict
                doc_scores: Dict[str, Optional[float]] = {}
                if result.scores:
                    doc_scores.update(result.scores)

                # Track original score from this list
                score_key = "bm25_score" if list_idx == 0 else "vector_score"
                if score_key not in doc_scores:
                    doc_scores[score_key] = result.score

                if doc_id in scores:
                    existing_score, existing_result = scores[doc_id]
                    # Merge scores from existing result
                    merged_scores: Dict[str, Optional[float]] = {}
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
        for rank, (doc_id, (score, result)) in enumerate(sorted_scores[:limit], 1):
            result.score = score
            result.rank = rank
            result.scores["rrf_score"] = score
            fused_results.append(result)

        return fused_results

    def fuse_with_weights(
        self,
        results_lists: List[List[SearchResult]],
        weights: List[float],
        limit: int = 10,
    ) -> List[SearchResult]:
        """Fuse multiple ranked lists with weights.

        Args:
            results_lists: List of ranked result lists
            weights: Weight for each result list (must sum to 1.0)
            limit: Maximum number of results to return

        Returns:
            Fused and re-ranked list of results
        """
        if len(results_lists) != len(weights):
            raise ValueError("Number of result lists must match number of weights")

        # Normalize weights
        total_weight = sum(weights)
        normalized_weights = [w / total_weight for w in weights]

        # Map document_id to weighted scores
        scores: Dict[str, Tuple[float, SearchResult]] = {}

        for list_idx, (results, weight) in enumerate(zip(results_lists, normalized_weights)):
            for rank, result in enumerate(results, 1):
                doc_id = result.document_id

                # Calculate weighted RRF score
                rrf_score = weight * (1.0 / (self.k + rank))

                # Build scores dict
                doc_scores: Dict[str, Optional[float]] = {}
                if result.scores:
                    doc_scores.update(result.scores)

                # Track original score from this list
                score_key = "bm25_score" if list_idx == 0 else "vector_score"
                if score_key not in doc_scores:
                    doc_scores[score_key] = result.score

                if doc_id in scores:
                    existing_score, existing_result = scores[doc_id]
                    # Merge scores from existing result
                    merged_scores: Dict[str, Optional[float]] = {}
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

        # Sort by weighted score (descending)
        sorted_scores = sorted(scores.items(), key=lambda x: x[1][0], reverse=True)

        # Build final results
        fused_results = []
        for rank, (doc_id, (score, result)) in enumerate(sorted_scores[:limit], 1):
            result.score = score
            result.rank = rank
            result.scores["rrf_score"] = score
            fused_results.append(result)

        return fused_results


def compute_rrf_score(rank: int, k: int = 60) -> float:
    """Compute RRF score for a single rank.

    Args:
        rank: The rank position (1-indexed)
        k: RRF constant

    Returns:
        RRF score
    """
    return 1.0 / (k + rank)
