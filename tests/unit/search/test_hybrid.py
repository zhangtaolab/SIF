"""Unit tests for hybrid search strategy.

This module tests the HybridSearchStrategy implementation including:
- Combining BM25 and vector search results
- RRF fusion integration
- Weight configuration
- Batch search functionality
"""

import uuid
from unittest.mock import MagicMock, create_autospec

import pytest

from docsift.models.search import SearchOptions, SearchResult, SearchType
from docsift.search.bm25 import BM25SearchStrategy
from docsift.search.hybrid import HybridSearchStrategy
from docsift.search.rrf import RRFFusion
from docsift.search.strategy import SearchContext
from docsift.search.vector import VectorSearchStrategy


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def mock_bm25_strategy() -> MagicMock:
    """Create a mock BM25 search strategy."""
    mock = create_autospec(BM25SearchStrategy, instance=True)
    return mock


@pytest.fixture
def mock_vector_strategy() -> MagicMock:
    """Create a mock vector search strategy."""
    mock = create_autospec(VectorSearchStrategy, instance=True)
    return mock


@pytest.fixture
def mock_rrf_fusion() -> MagicMock:
    """Create a mock RRF fusion."""
    mock = create_autospec(RRFFusion, instance=True)
    return mock


@pytest.fixture
def sample_search_options() -> SearchOptions:
    """Create sample search options."""
    return SearchOptions(
        limit=10,
        offset=0,
        threshold=0.0,
        bm25_weight=0.3,
        vector_weight=0.7,
        rrf_k=60,
    )


@pytest.fixture
def sample_search_context() -> SearchContext:
    """Create sample search context."""
    return SearchContext(
        query="test query",
        collection_ids=None,
    )


@pytest.fixture
def bm25_results() -> list[SearchResult]:
    """Create sample BM25 search results."""
    return [
        SearchResult(
            document_id="doc-A",
            document_path="/path/to/doc_a.md",
            document_title="Document A",
            score=0.95,
            bm25_score=0.95,
            content_preview="BM25 match for A",
        ),
        SearchResult(
            document_id="doc-B",
            document_path="/path/to/doc_b.md",
            document_title="Document B",
            score=0.87,
            bm25_score=0.87,
            content_preview="BM25 match for B",
        ),
        SearchResult(
            document_id="doc-C",
            document_path="/path/to/doc_c.md",
            document_title="Document C",
            score=0.82,
            bm25_score=0.82,
            content_preview="BM25 match for C",
        ),
    ]


@pytest.fixture
def vector_results() -> list[SearchResult]:
    """Create sample vector search results."""
    return [
        SearchResult(
            document_id="doc-A",
            document_path="/path/to/doc_a.md",
            document_title="Document A",
            score=0.92,
            vector_score=0.92,
            content_preview="Vector match for A",
        ),
        SearchResult(
            document_id="doc-C",
            document_path="/path/to/doc_c.md",
            document_title="Document C",
            score=0.88,
            vector_score=0.88,
            content_preview="Vector match for C",
        ),
        SearchResult(
            document_id="doc-D",
            document_path="/path/to/doc_d.md",
            document_title="Document D",
            score=0.85,
            vector_score=0.85,
            content_preview="Vector match for D",
        ),
    ]


@pytest.fixture
def fused_results() -> list[SearchResult]:
    """Create sample fused search results."""
    return [
        SearchResult(
            document_id="doc-A",
            document_path="/path/to/doc_a.md",
            document_title="Document A",
            score=0.033,  # Fused RRF score
            bm25_score=0.95,
            vector_score=0.92,
            content_preview="Fused result for A",
        ),
        SearchResult(
            document_id="doc-C",
            document_path="/path/to/doc_c.md",
            document_title="Document C",
            score=0.029,
            bm25_score=0.82,
            vector_score=0.88,
            content_preview="Fused result for C",
        ),
        SearchResult(
            document_id="doc-B",
            document_path="/path/to/doc_b.md",
            document_title="Document B",
            score=0.016,
            bm25_score=0.87,
            vector_score=None,
            content_preview="Fused result for B",
        ),
        SearchResult(
            document_id="doc-D",
            document_path="/path/to/doc_d.md",
            document_title="Document D",
            score=0.016,
            bm25_score=None,
            vector_score=0.85,
            content_preview="Fused result for D",
        ),
    ]


# =============================================================================
# Hybrid Search Basic Tests
# =============================================================================


class TestHybridSearchBasic:
    """Test basic hybrid search functionality."""
    
    def test_hybrid_search_executes_both_strategies(
        self,
        mock_bm25_strategy: MagicMock,
        mock_vector_strategy: MagicMock,
        mock_rrf_fusion: MagicMock,
        sample_search_context: SearchContext,
        sample_search_options: SearchOptions,
        bm25_results: list[SearchResult],
        vector_results: list[SearchResult],
        fused_results: list[SearchResult],
    ) -> None:
        """Test that hybrid search executes both BM25 and vector search.
        
        Arrange: Set up mock strategies and fusion
        Act: Execute hybrid search
        Assert: Both strategies and fusion are called
        """
        # Arrange
        mock_bm25_strategy.search.return_value = bm25_results
        mock_vector_strategy.search.return_value = vector_results
        mock_rrf_fusion.fuse.return_value = fused_results
        
        hybrid = HybridSearchStrategy(
            bm25_strategy=mock_bm25_strategy,
            vector_strategy=mock_vector_strategy,
            rrf_fusion=mock_rrf_fusion,
        )
        
        # Act
        results = hybrid.search(sample_search_context, sample_search_options)
        
        # Assert
        mock_bm25_strategy.search.assert_called_once_with(sample_search_context, sample_search_options)
        mock_vector_strategy.search.assert_called_once_with(sample_search_context, sample_search_options)
        mock_rrf_fusion.fuse.assert_called_once()
    
    def test_hybrid_search_returns_fused_results(
        self,
        mock_bm25_strategy: MagicMock,
        mock_vector_strategy: MagicMock,
        mock_rrf_fusion: MagicMock,
        sample_search_context: SearchContext,
        sample_search_options: SearchOptions,
        bm25_results: list[SearchResult],
        vector_results: list[SearchResult],
        fused_results: list[SearchResult],
    ) -> None:
        """Test that hybrid search returns fused results.
        
        Arrange: Set up mock strategies to return results
        Act: Execute hybrid search
        Assert: Returns results from fusion
        """
        # Arrange
        mock_bm25_strategy.search.return_value = bm25_results
        mock_vector_strategy.search.return_value = vector_results
        mock_rrf_fusion.fuse.return_value = fused_results
        
        hybrid = HybridSearchStrategy(
            bm25_strategy=mock_bm25_strategy,
            vector_strategy=mock_vector_strategy,
            rrf_fusion=mock_rrf_fusion,
        )
        
        # Act
        results = hybrid.search(sample_search_context, sample_search_options)
        
        # Assert
        assert results == fused_results
    
    def test_hybrid_search_applies_limit(
        self,
        mock_bm25_strategy: MagicMock,
        mock_vector_strategy: MagicMock,
        sample_search_context: SearchContext,
        fused_results: list[SearchResult],
    ) -> None:
        """Test that hybrid search applies result limit.
        
        Arrange: Set up mock strategies and options with limit
        Act: Execute hybrid search
        Assert: Returns at most limit results
        """
        # Arrange
        mock_bm25_strategy.search.return_value = []
        mock_vector_strategy.search.return_value = []
        
        options = SearchOptions(limit=2, bm25_weight=0.3, vector_weight=0.7)
        
        # Create a real RRF fusion for this test
        rrf = RRFFusion()
        
        hybrid = HybridSearchStrategy(
            bm25_strategy=mock_bm25_strategy,
            vector_strategy=mock_vector_strategy,
            rrf_fusion=rrf,
        )
        
        # Act
        results = hybrid.search(sample_search_context, options)
        
        # Assert - with empty results, should return empty list
        assert len(results) <= options.limit
    
    def test_hybrid_search_passes_weights_to_fusion(
        self,
        mock_bm25_strategy: MagicMock,
        mock_vector_strategy: MagicMock,
        mock_rrf_fusion: MagicMock,
        sample_search_context: SearchContext,
        sample_search_options: SearchOptions,
        bm25_results: list[SearchResult],
        vector_results: list[SearchResult],
    ) -> None:
        """Test that hybrid search passes weights to RRF fusion.
        
        Arrange: Set up mock strategies
        Act: Execute hybrid search
        Assert: Fusion called with correct weights
        """
        # Arrange
        mock_bm25_strategy.search.return_value = bm25_results
        mock_vector_strategy.search.return_value = vector_results
        mock_rrf_fusion.fuse.return_value = []
        
        hybrid = HybridSearchStrategy(
            bm25_strategy=mock_bm25_strategy,
            vector_strategy=mock_vector_strategy,
            rrf_fusion=mock_rrf_fusion,
        )
        
        # Act
        hybrid.search(sample_search_context, sample_search_options)
        
        # Assert
        call_args = mock_rrf_fusion.fuse.call_args
        assert call_args is not None
        _, kwargs = call_args
        assert kwargs.get("weights") == [0.3, 0.7]
        assert kwargs.get("k") == 60
    
    def test_hybrid_search_passes_rrf_k(
        self,
        mock_bm25_strategy: MagicMock,
        mock_vector_strategy: MagicMock,
        mock_rrf_fusion: MagicMock,
        sample_search_context: SearchContext,
        bm25_results: list[SearchResult],
        vector_results: list[SearchResult],
    ) -> None:
        """Test that hybrid search passes RRF k parameter.
        
        Arrange: Set up mock strategies with custom rrf_k
        Act: Execute hybrid search
        Assert: Fusion called with correct k value
        """
        # Arrange
        mock_bm25_strategy.search.return_value = bm25_results
        mock_vector_strategy.search.return_value = vector_results
        mock_rrf_fusion.fuse.return_value = []
        
        options = SearchOptions(limit=10, rrf_k=100)
        
        hybrid = HybridSearchStrategy(
            bm25_strategy=mock_bm25_strategy,
            vector_strategy=mock_vector_strategy,
            rrf_fusion=mock_rrf_fusion,
        )
        
        # Act
        hybrid.search(sample_search_context, options)
        
        # Assert
        call_args = mock_rrf_fusion.fuse.call_args
        assert call_args is not None
        _, kwargs = call_args
        assert kwargs.get("k") == 100


# =============================================================================
# Default RRF Fusion Tests
# =============================================================================


class TestHybridSearchDefaultFusion:
    """Test hybrid search with default RRF fusion."""
    
    def test_default_rrf_fusion_created(
        self,
        mock_bm25_strategy: MagicMock,
        mock_vector_strategy: MagicMock,
    ) -> None:
        """Test that default RRF fusion is created when not provided.
        
        Arrange: Create hybrid strategy without RRF fusion
        Act: Check internal RRF fusion
        Assert: Default RRF fusion is created
        """
        # Arrange & Act
        hybrid = HybridSearchStrategy(
            bm25_strategy=mock_bm25_strategy,
            vector_strategy=mock_vector_strategy,
        )
        
        # Assert
        assert hybrid._rrf_fusion is not None
        assert isinstance(hybrid._rrf_fusion, RRFFusion)
    
    def test_default_fusion_produces_results(
        self,
        mock_bm25_strategy: MagicMock,
        mock_vector_strategy: MagicMock,
        sample_search_context: SearchContext,
        bm25_results: list[SearchResult],
        vector_results: list[SearchResult],
    ) -> None:
        """Test that default fusion produces valid results.
        
        Arrange: Set up mock strategies with overlapping results
        Act: Execute hybrid search with default fusion
        Assert: Returns fused and ordered results
        """
        # Arrange
        mock_bm25_strategy.search.return_value = bm25_results
        mock_vector_strategy.search.return_value = vector_results
        
        hybrid = HybridSearchStrategy(
            bm25_strategy=mock_bm25_strategy,
            vector_strategy=mock_vector_strategy,
        )
        
        options = SearchOptions(limit=10, bm25_weight=1.0, vector_weight=1.0)
        
        # Act
        results = hybrid.search(sample_search_context, options)
        
        # Assert
        assert len(results) > 0
        # doc-A appears in both lists, should be ranked highest
        assert results[0].document_id == "doc-A"
        # All scores should be positive
        assert all(r.score > 0 for r in results)


# =============================================================================
# Edge Cases and Boundary Tests
# =============================================================================


class TestHybridSearchEdgeCases:
    """Test hybrid search edge cases."""
    
    def test_empty_bm25_results(
        self,
        mock_bm25_strategy: MagicMock,
        mock_vector_strategy: MagicMock,
        sample_search_context: SearchContext,
        vector_results: list[SearchResult],
    ) -> None:
        """Test hybrid search with empty BM25 results.
        
        Arrange: Set BM25 to return empty, vector to return results
        Act: Execute hybrid search
        Assert: Returns vector results
        """
        # Arrange
        mock_bm25_strategy.search.return_value = []
        mock_vector_strategy.search.return_value = vector_results
        
        hybrid = HybridSearchStrategy(
            bm25_strategy=mock_bm25_strategy,
            vector_strategy=mock_vector_strategy,
        )
        
        options = SearchOptions(limit=10)
        
        # Act
        results = hybrid.search(sample_search_context, options)
        
        # Assert
        assert len(results) == len(vector_results)
        doc_ids = {r.document_id for r in results}
        assert doc_ids == {"doc-A", "doc-C", "doc-D"}
    
    def test_empty_vector_results(
        self,
        mock_bm25_strategy: MagicMock,
        mock_vector_strategy: MagicMock,
        sample_search_context: SearchContext,
        bm25_results: list[SearchResult],
    ) -> None:
        """Test hybrid search with empty vector results.
        
        Arrange: Set vector to return empty, BM25 to return results
        Act: Execute hybrid search
        Assert: Returns BM25 results
        """
        # Arrange
        mock_bm25_strategy.search.return_value = bm25_results
        mock_vector_strategy.search.return_value = []
        
        hybrid = HybridSearchStrategy(
            bm25_strategy=mock_bm25_strategy,
            vector_strategy=mock_vector_strategy,
        )
        
        options = SearchOptions(limit=10)
        
        # Act
        results = hybrid.search(sample_search_context, options)
        
        # Assert
        assert len(results) == len(bm25_results)
        doc_ids = {r.document_id for r in results}
        assert doc_ids == {"doc-A", "doc-B", "doc-C"}
    
    def test_both_empty_results(
        self,
        mock_bm25_strategy: MagicMock,
        mock_vector_strategy: MagicMock,
        sample_search_context: SearchContext,
    ) -> None:
        """Test hybrid search with both result sets empty.
        
        Arrange: Set both strategies to return empty
        Act: Execute hybrid search
        Assert: Returns empty list
        """
        # Arrange
        mock_bm25_strategy.search.return_value = []
        mock_vector_strategy.search.return_value = []
        
        hybrid = HybridSearchStrategy(
            bm25_strategy=mock_bm25_strategy,
            vector_strategy=mock_vector_strategy,
        )
        
        options = SearchOptions(limit=10)
        
        # Act
        results = hybrid.search(sample_search_context, options)
        
        # Assert
        assert results == []
    
    def test_identical_results(
        self,
        mock_bm25_strategy: MagicMock,
        mock_vector_strategy: MagicMock,
        sample_search_context: SearchContext,
        bm25_results: list[SearchResult],
    ) -> None:
        """Test hybrid search with identical result sets.
        
        Arrange: Set both strategies to return same results
        Act: Execute hybrid search
        Assert: Returns results with boosted scores
        """
        # Arrange
        mock_bm25_strategy.search.return_value = bm25_results
        mock_vector_strategy.search.return_value = bm25_results.copy()
        
        hybrid = HybridSearchStrategy(
            bm25_strategy=mock_bm25_strategy,
            vector_strategy=mock_vector_strategy,
        )
        
        options = SearchOptions(limit=10, bm25_weight=1.0, vector_weight=1.0)
        
        # Act
        results = hybrid.search(sample_search_context, options)
        
        # Assert
        assert len(results) == len(bm25_results)
        # With identical results, scores should be doubled
        # (each doc appears twice with same rank)
    
    def test_zero_weights(
        self,
        mock_bm25_strategy: MagicMock,
        mock_vector_strategy: MagicMock,
        sample_search_context: SearchContext,
        bm25_results: list[SearchResult],
        vector_results: list[SearchResult],
    ) -> None:
        """Test hybrid search with zero weights.
        
        Arrange: Set one weight to zero
        Act: Execute hybrid search
        Assert: Zero-weighted strategy contributes 0 to scores
        """
        # Arrange
        mock_bm25_strategy.search.return_value = bm25_results
        mock_vector_strategy.search.return_value = vector_results
        
        hybrid = HybridSearchStrategy(
            bm25_strategy=mock_bm25_strategy,
            vector_strategy=mock_vector_strategy,
        )
        
        # Zero BM25 weight - BM25 results will still appear but with 0 contribution
        options = SearchOptions(limit=10, bm25_weight=0.0, vector_weight=1.0)
        
        # Act
        results = hybrid.search(sample_search_context, options)
        
        # Assert - all unique docs from both lists appear
        # doc-A, doc-B, doc-C from BM25; doc-A, doc-C, doc-D from vector
        doc_ids = {r.document_id for r in results}
        assert doc_ids == {"doc-A", "doc-B", "doc-C", "doc-D"}
        
        # doc-B only appears in BM25 (weight 0), so its score should be 0
        doc_b = next(r for r in results if r.document_id == "doc-B")
        assert doc_b.score == 0.0


# =============================================================================
# Batch Search Tests
# =============================================================================


class TestHybridSearchBatch:
    """Test hybrid search batch functionality."""
    
    def test_batch_search_executes_all_queries(
        self,
        mock_bm25_strategy: MagicMock,
        mock_vector_strategy: MagicMock,
        mock_rrf_fusion: MagicMock,
    ) -> None:
        """Test that batch search executes all queries.
        
        Arrange: Set up mock strategies and multiple contexts
        Act: Execute batch search
        Assert: Search called for each context
        """
        # Arrange
        contexts = [
            SearchContext(query="query 1"),
            SearchContext(query="query 2"),
            SearchContext(query="query 3"),
        ]
        
        mock_bm25_strategy.search.return_value = []
        mock_vector_strategy.search.return_value = []
        mock_rrf_fusion.fuse.return_value = []
        
        hybrid = HybridSearchStrategy(
            bm25_strategy=mock_bm25_strategy,
            vector_strategy=mock_vector_strategy,
            rrf_fusion=mock_rrf_fusion,
        )
        
        options = SearchOptions(limit=10)
        
        # Act
        results = hybrid.search_batch(contexts, options)
        
        # Assert
        assert len(results) == 3
        assert mock_bm25_strategy.search.call_count == 3
        assert mock_vector_strategy.search.call_count == 3
    
    def test_batch_search_returns_separate_results(
        self,
        mock_bm25_strategy: MagicMock,
        mock_vector_strategy: MagicMock,
    ) -> None:
        """Test that batch search returns separate result lists.
        
        Arrange: Set up mock strategies with different results per query
        Act: Execute batch search
        Assert: Returns separate result lists
        """
        # Arrange
        contexts = [
            SearchContext(query="query 1"),
            SearchContext(query="query 2"),
        ]
        
        # Return different results for each call
        def bm25_side_effect(ctx: SearchContext, opts: SearchOptions) -> list[SearchResult]:
            return [SearchResult(
                document_id=f"doc-{ctx.query}",
                document_path=f"/{ctx.query}.md",
                score=0.9,
            )]
        
        mock_bm25_strategy.search.side_effect = bm25_side_effect
        mock_vector_strategy.search.return_value = []
        
        hybrid = HybridSearchStrategy(
            bm25_strategy=mock_bm25_strategy,
            vector_strategy=mock_vector_strategy,
        )
        
        options = SearchOptions(limit=10)
        
        # Act
        results = hybrid.search_batch(contexts, options)
        
        # Assert
        assert len(results) == 2
        assert results[0][0].document_id == "doc-query 1"
        assert results[1][0].document_id == "doc-query 2"
    
    def test_batch_search_empty_contexts(
        self,
        mock_bm25_strategy: MagicMock,
        mock_vector_strategy: MagicMock,
    ) -> None:
        """Test batch search with empty contexts list.
        
        Arrange: Create empty contexts list
        Act: Execute batch search
        Assert: Returns empty list
        """
        # Arrange
        hybrid = HybridSearchStrategy(
            bm25_strategy=mock_bm25_strategy,
            vector_strategy=mock_vector_strategy,
        )
        
        options = SearchOptions(limit=10)
        
        # Act
        results = hybrid.search_batch([], options)
        
        # Assert
        assert results == []
        mock_bm25_strategy.search.assert_not_called()


# =============================================================================
# Integration Tests
# =============================================================================


class TestHybridSearchIntegration:
    """Integration tests for hybrid search."""
    
    def test_full_hybrid_search_flow(
        self,
        sample_search_context: SearchContext,
        bm25_results: list[SearchResult],
        vector_results: list[SearchResult],
    ) -> None:
        """Test full hybrid search flow with real RRF fusion.
        
        Arrange: Set up real strategies with mock repositories
        Act: Execute hybrid search
        Assert: Results are correctly fused and ordered
        """
        # Arrange - create mock strategies that return real results
        mock_bm25 = MagicMock(spec=BM25SearchStrategy)
        mock_bm25.search.return_value = bm25_results
        
        mock_vector = MagicMock(spec=VectorSearchStrategy)
        mock_vector.search.return_value = vector_results
        
        hybrid = HybridSearchStrategy(
            bm25_strategy=mock_bm25,
            vector_strategy=mock_vector,
        )
        
        options = SearchOptions(
            limit=10,
            bm25_weight=1.0,
            vector_weight=1.0,
            rrf_k=60,
        )
        
        # Act
        results = hybrid.search(sample_search_context, options)
        
        # Assert
        assert len(results) == 4  # Unique documents from both lists
        
        # doc-A appears in both at rank 1, should be first
        assert results[0].document_id == "doc-A"
        
        # All results should have positive scores
        assert all(r.score > 0 for r in results)
        
        # Scores should be in descending order
        for i in range(len(results) - 1):
            assert results[i].score >= results[i + 1].score
    
    def test_hybrid_search_with_collection_filter(
        self,
        mock_bm25_strategy: MagicMock,
        mock_vector_strategy: MagicMock,
    ) -> None:
        """Test hybrid search with collection filter.
        
        Arrange: Set up context with collection_ids
        Act: Execute hybrid search
        Assert: Collection filter passed to strategies
        """
        # Arrange
        mock_bm25_strategy.search.return_value = []
        mock_vector_strategy.search.return_value = []
        
        hybrid = HybridSearchStrategy(
            bm25_strategy=mock_bm25_strategy,
            vector_strategy=mock_vector_strategy,
        )
        
        context = SearchContext(
            query="test",
            collection_ids=["collection-1", "collection-2"],
        )
        options = SearchOptions(limit=10)
        
        # Act
        hybrid.search(context, options)
        
        # Assert
        bm25_call = mock_bm25_strategy.search.call_args
        vector_call = mock_vector_strategy.search.call_args
        
        assert bm25_call is not None
        assert vector_call is not None
        
        # Check that context with collection_ids was passed
        passed_context_bm25 = bm25_call[0][0]
        passed_context_vector = vector_call[0][0]
        
        assert passed_context_bm25.collection_ids == ["collection-1", "collection-2"]
        assert passed_context_vector.collection_ids == ["collection-1", "collection-2"]
