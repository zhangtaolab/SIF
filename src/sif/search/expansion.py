"""Query expansion for improving search recall."""

from __future__ import annotations

import numpy as np

from sif.utils.logging import get_logger

logger = get_logger(__name__)


class QueryExpansion:
    """Query expansion to improve search recall.

    Query expansion adds related terms to the original query
    to help find more relevant documents.

    Methods:
    - Synonym expansion: Add synonyms for query terms
    - Embedding expansion: Find similar terms using embeddings
    - LLM expansion: Use language model to generate related terms
    """

    def __init__(
        self,
        embedding_manager: "EmbeddingManager | None" = None,
        expansion_factor: int = 3,
    ) -> None:
        """Initialize query expansion.

        Args:
            embedding_manager: Optional embedding manager for semantic expansion
            expansion_factor: Number of expansion terms to add per query term
        """
        self._embedding_manager = embedding_manager
        self._expansion_factor = expansion_factor

    def expand(self, query: str, intent: str | None = None) -> list[str]:
        """Expand a query with related terms.

        Args:
            query: Original query
            intent: Optional intent hint to prepend to each variant

        Returns:
            List of query variants: [original_query, expanded_variant_1, ...]
        """
        expansion_terms = self._get_expansion_terms(query)

        variants = [query]
        for term in expansion_terms[: self._expansion_factor]:
            variants.append(f"{query} {term}")

        if intent:
            variants = [f"{intent}: {v}" for v in variants]

        if not variants:
            return [query]

        logger.debug(f"Expanded query: '{query}' -> {variants}")
        return variants

    def _get_expansion_terms(self, query: str) -> list[str]:
        """Get expansion terms using embedding-based pseudo-relevance feedback.

        Args:
            query: Original query

        Returns:
            List of expansion terms sorted by similarity
        """
        if self._embedding_manager is None:
            return []

        try:
            # Embed the query
            query_embedding = self._embedding_manager.embed_single(query)

            # Generate candidate terms: individual words from query + common synonyms
            words = query.split()
            candidates = set(words)

            # Simple synonym map for common terms (expandable)
            synonym_map = {
                "python": ["py", "cpython"],
                "search": ["find", "lookup", "query"],
                "index": ["catalog", "register"],
                "document": ["doc", "file", "page"],
                "config": ["configuration", "settings"],
            }

            for word in words:
                word_lower = word.lower()
                if word_lower in synonym_map:
                    candidates.update(synonym_map[word_lower])

            # Remove query words from candidates (we only want expansion terms)
            query_words_lower = {w.lower() for w in words}
            candidates = candidates - query_words_lower

            if not candidates:
                return []

            candidate_list = list(candidates)
            candidate_embeddings = self._embedding_manager.embed(candidate_list)

            # Compute cosine similarities
            query_vec = np.array(query_embedding)
            similarities = []
            for emb in candidate_embeddings.embeddings:
                cand_vec = np.array(emb)
                sim = np.dot(query_vec, cand_vec) / (
                    np.linalg.norm(query_vec) * np.linalg.norm(cand_vec) + 1e-8
                )
                similarities.append(sim)

            # Return top-k most similar terms that are NOT already in the query
            scored = [
                (term, sim)
                for term, sim in zip(candidate_list, similarities)
                if term.lower() not in query_words_lower
            ]
            scored.sort(key=lambda x: x[1], reverse=True)

            return [term for term, _ in scored[: self._expansion_factor]]
        except Exception as e:
            logger.warning(f"Query expansion failed: {e}")
            return []

    def expand_batch(self, queries: list[str]) -> list[str]:
        """Expand multiple queries and return a flat list of unique variants.

        Args:
            queries: List of queries

        Returns:
            Flat list of unique expanded query variants
        """
        all_variants: list[str] = []
        for query in queries:
            variants = self.expand(query)
            all_variants.extend(variants)

        # Deduplicate while preserving order
        seen: set[str] = set()
        unique_variants: list[str] = []
        for v in all_variants:
            if v not in seen:
                seen.add(v)
                unique_variants.append(v)

        return unique_variants
