"""Tests for BM25 search strategy."""

from unittest.mock import MagicMock

import pytest

from docsift.models.search import SearchOptions, SearchResult
from docsift.search.bm25 import BM25SearchStrategy
from docsift.search.strategy import SearchContext


class TestBM25SearchStrategy:
    """Tests for BM25SearchStrategy class."""
    
    def test_init_stores_repository(self, mock_search_repository: MagicMock):
        """Test that init stores the repository."""
        # Act
        strategy = BM25SearchStrategy(mock_search_repository)
        
        # Assert
        assert strategy._repository is mock_search_repository
    
    def test_search_calls_repository_search_fts(self, mock_search_repository: MagicMock):
        """Test that search calls repository search_fts method."""
        # Arrange
        strategy = BM25SearchStrategy(mock_search_repository)
        context = SearchContext(query="test query")
        options = SearchOptions(limit=10)
        
        # Act
        results = strategy.search(context, options)
        
        # Assert
        mock_search_repository.search_fts.assert_called_once_with(
            query="test query",
            collection_ids=None,
            limit=10,
            offset=0,
        )
    
    def test_search_returns_search_results(self, mock_search_repository: MagicMock):
        """Test that search returns list of SearchResult objects."""
        # Arrange
        strategy = BM25SearchStrategy(mock_search_repository)
        context = SearchContext(query="test query")
        options = SearchOptions(limit=10)
        
        # Act
        results = strategy.search(context, options)
        
        # Assert
        assert isinstance(results, list)
        assert len(results) == 3
        assert all(isinstance(r, SearchResult) for r in results)
    
    def test_search_applies_threshold(self, mock_search_repository: MagicMock):
        """Test that search applies score threshold."""
        # Arrange
        mock_search_repository.search_fts.return_value = [
            ("doc-1", 0.95),
            ("doc-2", 0.50),
            ("doc-3", 0.30),
        ]
        strategy = BM25SearchStrategy(mock_search_repository)
        context = SearchContext(query="test query")
        options = SearchOptions(limit=10, threshold=0.40)
        
        # Act
        results = strategy.search(context, options)
        
        # Assert
        assert len(results) == 2  # Only doc-1 and doc-2 above threshold
        assert all(r.score >= 0.40 for r in results)
    
    def test_search_includes_bm25_score(self, mock_search_repository: MagicMock):
        """Test that search results include BM25 score."""
        # Arrange
        strategy = BM25SearchStrategy(mock_search_repository)
        context = SearchContext(query="test query")
        options = SearchOptions()
        
        # Act
        results = strategy.search(context, options)
        
        # Assert
        assert results[0].bm25_score == 0.95
        assert results[0].score == 0.95
    
    def test_search_with_collection_ids(self, mock_search_repository: MagicMock):
        """Test search with specific collection IDs."""
        # Arrange
        strategy = BM25SearchStrategy(mock_search_repository)
        context = SearchContext(
            query="test query",
            collection_ids=["col-1", "col-2"],
        )
        options = SearchOptions()
        
        # Act
        strategy.search(context, options)
        
        # Assert
        mock_search_repository.search_fts.assert_called_once_with(
            query="test query",
            collection_ids=["col-1", "col-2"],
            limit=10,
            offset=0,
        )
    
    def test_search_with_pagination(self, mock_search_repository: MagicMock):
        """Test search with offset for pagination."""
        # Arrange
        strategy = BM25SearchStrategy(mock_search_repository)
        context = SearchContext(query="test query")
        options = SearchOptions(limit=5, offset=10)
        
        # Act
        strategy.search(context, options)
        
        # Assert
        mock_search_repository.search_fts.assert_called_once_with(
            query="test query",
            collection_ids=None,
            limit=5,
            offset=10,
        )
    
    def test_search_empty_results(self, mock_search_repository: MagicMock):
        """Test search returns empty list when no results."""
        # Arrange
        mock_search_repository.search_fts.return_value = []
        strategy = BM25SearchStrategy(mock_search_repository)
        context = SearchContext(query="test query")
        options = SearchOptions()
        
        # Act
        results = strategy.search(context, options)
        
        # Assert
        assert results == []
    
    def test_search_skips_missing_documents(self, mock_search_repository: MagicMock):
        """Test search skips documents that can't be retrieved."""
        # Arrange
        mock_search_repository.get_document_for_result.return_value = None
        strategy = BM25SearchStrategy(mock_search_repository)
        context = SearchContext(query="test query")
        options = SearchOptions()
        
        # Act
        results = strategy.search(context, options)
        
        # Assert
        assert results == []
    
    def test_search_batch_executes_multiple_searches(self, mock_search_repository: MagicMock):
        """Test search_batch executes multiple searches."""
        # Arrange
        strategy = BM25SearchStrategy(mock_search_repository)
        contexts = [
            SearchContext(query="query 1"),
            SearchContext(query="query 2"),
        ]
        options = SearchOptions()
        
        # Act
        results = strategy.search_batch(contexts, options)
        
        # Assert
        assert len(results) == 2
        assert all(isinstance(r, list) for r in results)
        assert mock_search_repository.search_fts.call_count == 2
    
    def test_search_batch_empty_contexts(self, mock_search_repository: MagicMock):
        """Test search_batch with empty contexts list."""
        # Arrange
        strategy = BM25SearchStrategy(mock_search_repository)
        contexts: list[SearchContext] = []
        options = SearchOptions()
        
        # Act
        results = strategy.search_batch(contexts, options)
        
        # Assert
        assert results == []


class TestBM25Formula:
    """Tests for BM25 formula understanding."""
    
    def test_bm25_formula_components(self):
        """Test understanding of BM25 formula components."""
        # BM25 formula components:
        # - IDF: Inverse document frequency
        # - TF: Term frequency
        # - k1: Term frequency saturation parameter
        # - b: Length normalization parameter
        
        # These are configuration parameters in SearchOptions
        options = SearchOptions(bm25_k1=1.5, bm25_b=0.75)
        
        assert options.bm25_k1 == 1.5
        assert options.bm25_b == 0.75
    
    def test_bm25_default_parameters(self):
        """Test default BM25 parameters."""
        options = SearchOptions()
        
        # Default values from constants
        assert options.bm25_k1 == 1.5
        assert options.bm25_b == 0.75
