"""Integration tests for the complete search pipeline."""

from unittest.mock import MagicMock

import pytest

from docsift.models.search import SearchOptions, SearchResult, SearchType
from docsift.search.bm25 import BM25SearchStrategy
from docsift.search.vector import VectorSearchStrategy
from docsift.search.hybrid import HybridSearchStrategy
from docsift.search.rrf import RRFFusion
from docsift.search.strategy import SearchContext
from docsift.search.rerank import Reranker
from docsift.search.expansion import QueryExpansion


class TestSearchPipeline:
    """Integration tests for the complete search pipeline."""
    
    def test_bm25_search_pipeline(
        self,
        mock_search_repository: MagicMock,
    ):
        """Test complete BM25 search pipeline."""
        # Arrange
        strategy = BM25SearchStrategy(mock_search_repository)
        context = SearchContext(query="machine learning")
        options = SearchOptions(search_type=SearchType.BM25)
        
        # Act
        results = strategy.search(context, options)
        
        # Assert
        assert isinstance(results, list)
        assert all(isinstance(r, SearchResult) for r in results)
        assert mock_search_repository.search_fts.called
    
    def test_vector_search_pipeline(
        self,
        mock_search_repository: MagicMock,
        mock_embedding_manager: MagicMock,
    ):
        """Test complete vector search pipeline."""
        # Arrange
        strategy = VectorSearchStrategy(mock_search_repository, mock_embedding_manager)
        context = SearchContext(query="neural networks")
        options = SearchOptions(search_type=SearchType.VECTOR)
        
        # Act
        results = strategy.search(context, options)
        
        # Assert
        assert isinstance(results, list)
        assert all(isinstance(r, SearchResult) for r in results)
        assert mock_search_repository.search_vector.called
    
    def test_hybrid_search_pipeline(
        self,
        mock_search_repository: MagicMock,
        mock_embedding_manager: MagicMock,
    ):
        """Test complete hybrid search pipeline."""
        # Arrange
        bm25 = BM25SearchStrategy(mock_search_repository)
        vector = VectorSearchStrategy(mock_search_repository, mock_embedding_manager)
        hybrid = HybridSearchStrategy(bm25, vector)
        
        context = SearchContext(query="deep learning")
        options = SearchOptions(search_type=SearchType.HYBRID)
        
        # Act
        results = hybrid.search(context, options)
        
        # Assert
        assert isinstance(results, list)
        assert all(isinstance(r, SearchResult) for r in results)
    
    def test_search_with_query_expansion(
        self,
        mock_search_repository: MagicMock,
    ):
        """Test search with query expansion."""
        # Arrange
        expander = QueryExpansion()
        strategy = BM25SearchStrategy(mock_search_repository)
        
        original_query = "python tutorial"
        expanded_query = expander.expand(original_query)
        
        context = SearchContext(query=expanded_query)
        options = SearchOptions(expand_query=True)
        
        # Act
        results = strategy.search(context, options)
        
        # Assert
        assert isinstance(results, list)
    
    def test_search_with_reranking(
        self,
        sample_search_results: list[SearchResult],
    ):
        """Test search with reranking."""
        # Arrange
        reranker = Reranker()
        
        # Act
        reranked = reranker.rerank(
            query="test query",
            results=sample_search_results,
            top_k=5
        )
        
        # Assert
        assert len(reranked) <= 5
        assert all(isinstance(r, SearchResult) for r in reranked)
    
    def test_full_pipeline_with_all_components(
        self,
        mock_search_repository: MagicMock,
        mock_embedding_manager: MagicMock,
    ):
        """Test full search pipeline with all components."""
        # Arrange - Setup hybrid search
        bm25 = BM25SearchStrategy(mock_search_repository)
        vector = VectorSearchStrategy(mock_search_repository, mock_embedding_manager)
        hybrid = HybridSearchStrategy(bm25, vector)
        reranker = Reranker()
        expander = QueryExpansion()
        
        # Step 1: Expand query
        original_query = "machine learning"
        expanded_query = expander.expand(original_query)
        
        # Step 2: Search with hybrid strategy
        context = SearchContext(query=expanded_query)
        options = SearchOptions(
            search_type=SearchType.HYBRID,
            limit=20,
            rerank_top_k=10,
        )
        results = hybrid.search(context, options)
        
        # Step 3: Rerank results
        reranked = reranker.rerank(
            query=expanded_query,
            results=results,
            top_k=options.rerank_top_k,
        )
        
        # Assert
        assert isinstance(reranked, list)
        assert len(reranked) <= options.rerank_top_k


class TestRRFIntegration:
    """Integration tests for RRF fusion."""
    
    def test_rrf_fuses_bm25_and_vector_results(
        self,
        mock_search_repository: MagicMock,
        mock_embedding_manager: MagicMock,
    ):
        """Test that RRF correctly fuses BM25 and vector results."""
        # Arrange
        bm25 = BM25SearchStrategy(mock_search_repository)
        vector = VectorSearchStrategy(mock_search_repository, mock_embedding_manager)
        rrf = RRFFusion()
        
        context = SearchContext(query="test")
        options = SearchOptions()
        
        # Get results from both strategies
        bm25_results = bm25.search(context, options)
        vector_results = vector.search(context, options)
        
        # Act
        fused = rrf.fuse([bm25_results, vector_results])
        
        # Assert
        assert isinstance(fused, list)
        # Fused results should contain documents from both sources
        bm25_ids = {r.document_id for r in bm25_results}
        vector_ids = {r.document_id for r in vector_results}
        fused_ids = {r.document_id for r in fused}
        
        assert fused_ids.issubset(bm25_ids | vector_ids)


class TestSearchBatchIntegration:
    """Integration tests for batch search."""
    
    def test_batch_bm25_search(
        self,
        mock_search_repository: MagicMock,
    ):
        """Test batch BM25 search."""
        # Arrange
        strategy = BM25SearchStrategy(mock_search_repository)
        contexts = [
            SearchContext(query="query 1"),
            SearchContext(query="query 2"),
            SearchContext(query="query 3"),
        ]
        options = SearchOptions()
        
        # Act
        results = strategy.search_batch(contexts, options)
        
        # Assert
        assert len(results) == 3
        assert all(isinstance(r, list) for r in results)
    
    def test_batch_vector_search(
        self,
        mock_search_repository: MagicMock,
        mock_embedding_manager: MagicMock,
    ):
        """Test batch vector search."""
        # Arrange
        strategy = VectorSearchStrategy(mock_search_repository, mock_embedding_manager)
        contexts = [
            SearchContext(query="query 1"),
            SearchContext(query="query 2"),
        ]
        options = SearchOptions()
        
        # Act
        results = strategy.search_batch(contexts, options)
        
        # Assert
        assert len(results) == 2
    
    def test_batch_hybrid_search(
        self,
        mock_search_repository: MagicMock,
        mock_embedding_manager: MagicMock,
    ):
        """Test batch hybrid search."""
        # Arrange
        bm25 = BM25SearchStrategy(mock_search_repository)
        vector = VectorSearchStrategy(mock_search_repository, mock_embedding_manager)
        hybrid = HybridSearchStrategy(bm25, vector)
        
        contexts = [
            SearchContext(query="query 1"),
            SearchContext(query="query 2"),
        ]
        options = SearchOptions()
        
        # Act
        results = hybrid.search_batch(contexts, options)
        
        # Assert
        assert len(results) == 2


class TestSearchOptionsIntegration:
    """Integration tests for search options."""
    
    def test_search_options_propagation(
        self,
        mock_search_repository: MagicMock,
    ):
        """Test that search options propagate correctly."""
        # Arrange
        strategy = BM25SearchStrategy(mock_search_repository)
        context = SearchContext(query="test")
        options = SearchOptions(
            limit=5,
            offset=10,
            threshold=0.5,
            bm25_k1=2.0,
            bm25_b=0.5,
        )
        
        # Act
        strategy.search(context, options)
        
        # Assert
        call_args = mock_search_repository.search_fts.call_args
        assert call_args.kwargs["limit"] == 5
        assert call_args.kwargs["offset"] == 10
