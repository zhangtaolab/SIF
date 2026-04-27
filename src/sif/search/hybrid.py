"""Hybrid search combining BM25 and vector search with RRF."""

from __future__ import annotations

import os
import sqlite3
from typing import TYPE_CHECKING, List, Optional

from sif.core.models import Embedder, SearchOptions, SearchResult, SearchType
from sif.search.bm25 import BM25Searcher
from sif.search.rrf import RRFFusion
from sif.search.vector import VectorSearcher
from sif.utils.logging import get_logger

if TYPE_CHECKING:
    from sif.search.expansion import QueryExpansion
    from sif.search.rerank import CrossEncoderReranker, LlamaCppReranker
    from sif.search.snippets import SmartSnippetExtractor

logger = get_logger(__name__)


class HybridSearcher:
    """Hybrid search combining multiple search strategies."""

    def __init__(
        self,
        db: sqlite3.Connection,
        embedder: Optional[Embedder] = None,
        embedding_dim: int = 768,
    ) -> None:
        self.db = db
        self.embedder = embedder
        self.bm25 = BM25Searcher(db)
        self.vector = VectorSearcher(db, embedding_dim)
        self.rrf = RRFFusion(k=60)

    def search(
        self,
        query: str,
        options: Optional[SearchOptions] = None,
    ) -> List[SearchResult]:
        """Search using hybrid approach (BM25 + Vector + RRF).

        Args:
            query: Search query
            options: Search options

        Returns:
            Ranked list of search results
        """
        if options is None:
            options = SearchOptions()

        # Get BM25 results
        bm25_results = self.bm25.search(query, options)

        # Get vector results if embedder is available
        vector_results: List[SearchResult] = []
        if self.embedder is not None:
            query_embedding = self.embedder.embed(query)
            vector_results = self.vector.search(query_embedding, options)

        # If only one method returned results, return those
        if not vector_results:
            return self._attach_contexts(bm25_results)
        if not bm25_results:
            return self._attach_contexts(vector_results)

        # Fuse results using RRF
        fused_results = self.rrf.fuse([bm25_results, vector_results], options.limit)

        # Re-fetch content and highlights if needed
        if options.include_content or options.include_highlights:
            for result in fused_results:
                if options.include_content and result.content is None:
                    result.content = self._get_document_content(result.document_id)
                if options.include_highlights and not result.highlights:
                    result.highlights = self._get_highlights(
                        result.document_id, query, options.max_highlights
                    )

        # Deduplicate by document_id, keeping highest score
        deduped = self._deduplicate_results(fused_results)

        return self._attach_contexts(deduped)

    @staticmethod
    def _deduplicate_results(results: list[SearchResult]) -> list[SearchResult]:
        """Deduplicate results by document_id, keeping the highest score.

        Vector search operates at chunk level, so the same document may appear
        multiple times. We keep the best-scoring entry per document and
        reassign sequential ranks.
        """
        best: dict[str, SearchResult] = {}
        for result in results:
            doc_id = result.document_id
            if doc_id not in best or result.score > best[doc_id].score:
                best[doc_id] = result

        deduped = list(best.values())
        deduped.sort(key=lambda r: r.score, reverse=True)
        for rank, result in enumerate(deduped, 1):
            result.rank = rank
        return deduped

    def _attach_contexts(self, results: list[SearchResult]) -> list[SearchResult]:
        """Attach path context descriptions to search results via batch query."""
        if not results:
            return results
        paths = list({r.path for r in results})
        placeholders = ", ".join(["?"] * len(paths))
        sql = f"""
            SELECT target_id, content FROM contexts
            WHERE context_type = 'path' AND target_id IN ({placeholders})
        """
        cursor = self.db.execute(sql, paths)
        rows = cursor.fetchall()
        # Handle both sqlite3.Row (dict-like) and plain tuple rows
        context_map: dict[str, str] = {}
        for row in rows:
            if hasattr(row, "keys") and callable(getattr(row, "keys", None)):
                try:
                    context_map[os.path.realpath(row["target_id"])] = row["content"]
                    continue
                except (KeyError, TypeError):
                    pass
            # Fallback: assume tuple-like access (skip MagicMock rows in tests)
            try:
                key = row[0]
                val = row[1]
                if not isinstance(key, str):
                    continue
                context_map[os.path.realpath(key)] = val
            except (KeyError, IndexError, TypeError):
                continue
        for result in results:
            normalized_path = os.path.realpath(result.path)
            if normalized_path in context_map:
                result.context_description = context_map[normalized_path]
        return results

    def _get_document_content(self, document_id: str) -> Optional[str]:
        """Get document content."""
        cursor = self.db.execute("SELECT content FROM documents WHERE id = ?", (document_id,))
        row = cursor.fetchone()
        return row[0] if row else None

    def _get_highlights(
        self,
        document_id: str,
        query: str,
        max_highlights: int = 3,
    ) -> List[str]:
        """Get highlighted snippets."""
        return self.bm25._get_highlights(document_id, query, max_highlights)


class SearchPipeline:
    """Complete search pipeline with prefix routing, expansion, and reranking."""

    def __init__(
        self,
        db: sqlite3.Connection,
        embedder: Optional[Embedder] = None,
        query_expander: "QueryExpansion | None" = None,
        reranker: "LlamaCppReranker | CrossEncoderReranker | None" = None,
        snippet_extractor: "SmartSnippetExtractor | None" = None,
        embedding_dim: int = 768,
    ) -> None:
        self.db = db
        self.hybrid = HybridSearcher(db, embedder, embedding_dim)
        self.query_expander = query_expander
        self.reranker = reranker
        self.snippet_extractor = snippet_extractor

    def search(
        self,
        query: str,
        options: Optional[SearchOptions] = None,
    ) -> List[SearchResult]:
        """Execute full search pipeline with prefix routing.

        1. Parse query prefix to determine search mode
        2. Route to appropriate search mode (BM25, vector, HyDE, hybrid)
        3. Expand query (optional, for expand: prefix or default hybrid)
        4. Search with each query variant
        5. Fuse results with RRF
        6. Apply reranking with candidate capping
        7. Extract smart snippets
        """
        if options is None:
            options = SearchOptions()

        # Parse query prefix
        parsed_query, search_type = self._parse_query_prefix(query)

        # Apply intent if provided
        if options.intent:
            parsed_query = f"{options.intent}: {parsed_query}"

        # Route to appropriate search mode
        if search_type == SearchType.BM25:
            return self.hybrid.bm25.search(parsed_query, options)
        elif search_type == SearchType.VECTOR:
            if self.hybrid.embedder is None:
                raise RuntimeError("Vector search requires an embedder")
            query_embedding = self.hybrid.embedder.embed(parsed_query)
            return self.hybrid.vector.search(query_embedding, options)
        elif search_type == SearchType.HYDE:
            hyde_doc = self._generate_hypothetical_document(parsed_query)
            if self.hybrid.embedder is None:
                raise RuntimeError("HyDE search requires an embedder")
            hyde_embedding = self.hybrid.embedder.embed(hyde_doc)
            return self.hybrid.vector.search(hyde_embedding, options)

        # Default: hybrid search with optional expansion
        queries = [parsed_query]

        # Expand query if expander is available and prefix is expand: or default
        if self.query_expander is not None and search_type in (
            SearchType.HYBRID,
            SearchType.EXPAND,
        ):
            try:
                expanded = self.query_expander.expand(parsed_query)
                # Deduplicate: keep original first, then unique expanded variants
                seen = {parsed_query.lower()}
                for variant in expanded[1:]:
                    if variant.lower() not in seen:
                        seen.add(variant.lower())
                        queries.append(variant)
            except Exception as e:
                logger.warning(f"Query expansion failed: {e}")

        # Search with each query
        all_results = []
        for q in queries:
            results = self.hybrid.search(q, options)
            if results:
                all_results.append(results)

        # If only one query or no expansion, return results
        if len(all_results) <= 1:
            results = all_results[0] if all_results else []
        else:
            # Fuse results from multiple queries
            results = self.hybrid.rrf.fuse(all_results, options.limit)

        # Apply candidate limit before reranking
        if self.reranker is not None and len(results) > 0:
            candidates = results[: options.candidate_limit]
            try:
                reranked = self.reranker.rerank(parsed_query, candidates, top_k=options.limit)
                results = reranked
            except Exception as e:
                raise RuntimeError(f"Reranking failed: {e}")

        # Extract smart snippets if not already present
        if self.snippet_extractor is not None:
            for result in results:
                if result.snippet is None and result.content:
                    query_terms = parsed_query.lower().split()
                    result.snippet = self.snippet_extractor.extract(result.content, query_terms)

        return self.hybrid._attach_contexts(results)

    def _parse_query_prefix(self, query: str) -> tuple[str, SearchType]:
        """Parse query prefix to determine search mode."""
        PREFIX_MAP = {
            "lex:": SearchType.BM25,
            "vec:": SearchType.VECTOR,
            "hyde:": SearchType.HYDE,
            "expand:": SearchType.EXPAND,
        }
        for prefix, search_type in PREFIX_MAP.items():
            if query.startswith(prefix):
                return query[len(prefix) :].strip(), search_type
        return query, SearchType.HYBRID

    def _generate_hypothetical_document(self, query: str) -> str:
        """Generate a hypothetical ideal answer document for HyDE search.

        Uses a lightweight prompt template approach. If the embedder supports text
        generation (e.g., GGUF models with .generate() or .create_completion()),
        it generates a short answer. Otherwise raises RuntimeError since HyDE
        requires text generation capability.
        """
        if self.hybrid.embedder is None:
            raise RuntimeError("HyDE search requires an embedder")

        # Check if embedder has generate capability
        if hasattr(self.hybrid.embedder, "generate"):
            prompt = (
                f"Answer the following question concisely and directly. "
                f"Provide only the answer, no preamble.\n\n"
                f"Question: {query}\n\nAnswer:"
            )
            return self.hybrid.embedder.generate(prompt)

        # Check for llama-cpp style completion API
        if hasattr(self.hybrid.embedder, "create_completion"):
            prompt = (
                f"Answer the following question concisely and directly. "
                f"Provide only the answer, no preamble.\n\n"
                f"Question: {query}\n\nAnswer:"
            )
            result = self.hybrid.embedder.create_completion(
                prompt,
                max_tokens=256,
                temperature=0.3,
                stop=["\n\n"],
            )
            return result["choices"][0]["text"].strip()

        # No text generation capability available
        raise RuntimeError(
            "HyDE search requires a text-generation-capable model (e.g., GGUF). "
            "The current embedder does not support .generate() or .create_completion(). "
            "Use vec: prefix for vector-only search instead."
        )
