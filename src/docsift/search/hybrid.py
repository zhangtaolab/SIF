"""Hybrid search combining BM25 and vector search with RRF."""

from __future__ import annotations

import sqlite3
from typing import List, Optional

from docsift.core.models import Embedder, SearchOptions, SearchResult
from docsift.search.bm25 import BM25Searcher
from docsift.search.rrf import RRFFusion
from docsift.search.vector import VectorSearcher


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
            return bm25_results
        if not bm25_results:
            return vector_results
        
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
        
        return fused_results
    
    def search_with_reranking(
        self,
        query: str,
        options: Optional[SearchOptions] = None,
        reranker=None,
    ) -> List[SearchResult]:
        """Search with optional reranking.
        
        Args:
            query: Search query
            options: Search options
            reranker: Optional reranker for final ranking
            
        Returns:
            Ranked list of search results
        """
        # Get hybrid results
        results = self.search(query, options)
        
        # Apply reranking if available
        if reranker is not None and len(results) > 0:
            try:
                # Get document contents for reranking
                documents = []
                for result in results:
                    content = result.content or self._get_document_content(result.document_id)
                    documents.append(content or "")
                
                # Rerank
                reranked = reranker.rerank(query, documents)
                
                # Reorder results based on reranking
                reordered = []
                for idx, score in reranked:
                    result = results[idx]
                    result.score = score
                    reordered.append(result)
                
                # Update ranks
                for rank, result in enumerate(reordered, 1):
                    result.rank = rank
                
                return reordered
            except Exception as e:
                print(f"Warning: Reranking failed: {e}")
        
        return results
    
    def _get_document_content(self, document_id: str) -> Optional[str]:
        """Get document content."""
        cursor = self.db.execute(
            "SELECT content FROM documents WHERE id = ?",
            (document_id,)
        )
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
    """Complete search pipeline with expansion, search, and reranking."""
    
    def __init__(
        self,
        db: sqlite3.Connection,
        embedder: Optional[Embedder] = None,
        query_expander=None,
        reranker=None,
        embedding_dim: int = 768,
    ) -> None:
        self.db = db
        self.hybrid = HybridSearcher(db, embedder, embedding_dim)
        self.query_expander = query_expander
        self.reranker = reranker
    
    def search(
        self,
        query: str,
        options: Optional[SearchOptions] = None,
    ) -> List[SearchResult]:
        """Execute full search pipeline.
        
        1. Expand query (optional)
        2. Search with each query variant
        3. Fuse results with RRF
        4. Rerank final results (optional)
        """
        if options is None:
            options = SearchOptions()
        
        # Expand query if expander is available
        queries = [query]
        if self.query_expander is not None:
            try:
                expanded = self.query_expander.expand(query)
                queries.extend(expanded)
            except Exception as e:
                print(f"Warning: Query expansion failed: {e}")
        
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
        
        # Apply final reranking
        if self.reranker is not None and len(results) > 0:
            try:
                documents = []
                for result in results:
                    content = result.content or self._get_document_content(result.document_id)
                    documents.append(content or "")
                
                reranked = self.reranker.rerank(query, documents)
                
                reordered = []
                for idx, score in reranked:
                    result = results[idx]
                    result.score = score
                    reordered.append(result)
                
                for rank, result in enumerate(reordered, 1):
                    result.rank = rank
                
                return reordered
            except Exception as e:
                print(f"Warning: Final reranking failed: {e}")
        
        return results
    
    def _get_document_content(self, document_id: str) -> Optional[str]:
        """Get document content."""
        cursor = self.db.execute(
            "SELECT content FROM documents WHERE id = ?",
            (document_id,)
        )
        row = cursor.fetchone()
        return row[0] if row else None
