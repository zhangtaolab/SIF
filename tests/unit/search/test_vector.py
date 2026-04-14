"""Tests for vector search strategy."""

from unittest.mock import MagicMock

import pytest

from docsift.models.search import SearchOptions, SearchResult
from docsift.search.vector import VectorSearchStrategy
from docsift.search.strategy import SearchContext


class TestVectorSearchStrategy:
    """Tests for VectorSearchStrategy class."""
    
    def test_init_stores_dependencies(
        self,
        mock_search_repository: MagicMock,
        mock_embedding_manager: MagicMock,
    ):
        """Test that init stores repository and embedding manager."""
        # Act
        strategy = VectorSearchStrategy(mock_search_repository, mock_embedding_manager)
        
        # Assert
        assert strategy._repository is mock_search_repository
        assert strategy._embedding_manager is mock_embedding_manager
    
    def test_search_generates_embedding_when_not_provided(
        self,
        mock_search_repository: MagicMock,
        mock_embedding_manager: MagicMock,
    ):
        """Test that search generates embedding when not provided in context."""
        # Arrange
        strategy = VectorSearchStrategy(mock_search_repository, mock_embedding_manager)
        context = SearchContext(query="test query", query_embedding=None)
        options = SearchOptions()
        
        # Act
        strategy.search(context, options)
        
        # Assert
        mock_embedding_manager.embed_single.assert_called_once_with("test query")
    
    def test_search_uses_provided_embedding(
        self,
        mock_search_repository: MagicMock,
        mock_embedding_manager: MagicMock,
    ):
        """Test that search uses provided embedding without generating new one."""
        # Arrange
        strategy = VectorSearchStrategy(mock_search_repository, mock_embedding_manager)
        query_embedding = [0.1, 0.2, 0.3]
        context = SearchContext(query="test query", query_embedding=query_embedding)
        options = SearchOptions()
        
        # Act
        strategy.search(context, options)
        
        # Assert
        mock_embedding_manager.embed_single.assert_not_called()
        mock_search_repository.search_vector.assert_called_once()
    
    def test_search_calls_repository_search_vector(
        self,
        mock_search_repository: MagicMock,
        mock_embedding_manager: MagicMock,
    ):
        """Test that search calls repository search_vector method."""
        # Arrange
        strategy = VectorSearchStrategy(mock_search_repository, mock_embedding_manager)
        context = SearchContext(query="test query")
        options = SearchOptions(limit=10)
        
        # Act
        strategy.search(context, options)
        
        # Assert
        mock_search_repository.search_vector.assert_called_once()
        call_args = mock_search_repository.search_vector.call_args
        assert call_args.kwargs["collection_ids"] is None
        assert call_args.kwargs["limit"] == 10
        assert call_args.kwargs["offset"] == 0
    
    def test_search_returns_search_results(
        self,
        mock_search_repository: MagicMock,
        mock_embedding_manager: MagicMock,
    ):
        """Test that search returns list of SearchResult objects."""
        # Arrange
        strategy = VectorSearchStrategy(mock_search_repository, mock_embedding_manager)
        context = SearchContext(query="test query")
        options = SearchOptions()
        
        # Act
        results = strategy.search(context, options)
        
        # Assert
        assert isinstance(results, list)
        assert len(results) == 3
        assert all(isinstance(r, SearchResult) for r in results)
    
    def test_search_applies_threshold(
        self,
        mock_search_repository: MagicMock,
        mock_embedding_manager: MagicMock,
    ):
        """Test that search applies score threshold."""
        # Arrange
        mock_search_repository.search_vector.return_value = [
            ("doc-1", 0.95),
            ("doc-2", 0.50),
            ("doc-3", 0.30),
        ]
        strategy = VectorSearchStrategy(mock_search_repository, mock_embedding_manager)
        context = SearchContext(query="test query")
        options = SearchOptions(threshold=0.40)
        
        # Act
        results = strategy.search(context, options)
        
        # Assert
        assert len(results) == 2  # Only doc-1 and doc-2 above threshold
        assert all(r.score >= 0.40 for r in results)
    
    def test_search_includes_vector_score(
        self,
        mock_search_repository: MagicMock,
        mock_embedding_manager: MagicMock,
    ):
        """Test that search results include vector score."""
        # Arrange
        strategy = VectorSearchStrategy(mock_search_repository, mock_embedding_manager)
        context = SearchContext(query="test query")
        options = SearchOptions()
        
        # Act
        results = strategy.search(context, options)
        
        # Assert
        assert results[0].vector_score == 0.92
        assert results[0].score == 0.92
    
    def test_search_with_collection_ids(
        self,
        mock_search_repository: MagicMock,
        mock_embedding_manager: MagicMock,
    ):
        """Test search with specific collection IDs."""
        # Arrange
        strategy = VectorSearchStrategy(mock_search_repository, mock_embedding_manager)
        context = SearchContext(
            query="test query",
            collection_ids=["col-1", "col-2"],
        )
        options = SearchOptions()
        
        # Act
        strategy.search(context, options)
        
        # Assert
        call_args = mock_search_repository.search_vector.call_args
        assert call_args.kwargs["collection_ids"] == ["col-1", "col-2"]
    
    def test_search_empty_results(
        self,
        mock_search_repository: MagicMock,
        mock_embedding_manager: MagicMock,
    ):
        """Test search returns empty list when no results."""
        # Arrange
        mock_search_repository.search_vector.return_value = []
        strategy = VectorSearchStrategy(mock_search_repository, mock_embedding_manager)
        context = SearchContext(query="test query")
        options = SearchOptions()
        
        # Act
        results = strategy.search(context, options)
        
        # Assert
        assert results == []
    
    def test_search_skips_missing_documents(
        self,
        mock_search_repository: MagicMock,
        mock_embedding_manager: MagicMock,
    ):
        """Test search skips documents that can't be retrieved."""
        # Arrange
        mock_search_repository.get_document_for_result.return_value = None
        strategy = VectorSearchStrategy(mock_search_repository, mock_embedding_manager)
        context = SearchContext(query="test query")
        options = SearchOptions()
        
        # Act
        results = strategy.search(context, options)
        
        # Assert
        assert results == []
    
    def test_search_batch_executes_multiple_searches(
        self,
        mock_search_repository: MagicMock,
        mock_embedding_manager: MagicMock,
    ):
        """Test search_batch executes multiple searches."""
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
        assert all(isinstance(r, list) for r in results)
        assert mock_search_repository.search_vector.call_count == 2
    
    def test_search_batch_with_precomputed_embeddings(
        self,
        mock_search_repository: MagicMock,
        mock_embedding_manager: MagicMock,
    ):
        """Test search_batch with precomputed embeddings."""
        # Arrange
        strategy = VectorSearchStrategy(mock_search_repository, mock_embedding_manager)
        contexts = [
            SearchContext(query="query 1", query_embedding=[0.1, 0.2]),
            SearchContext(query="query 2", query_embedding=[0.3, 0.4]),
        ]
        options = SearchOptions()
        
        # Act
        strategy.search_batch(contexts, options)
        
        # Assert
        mock_embedding_manager.embed_single.assert_not_called()


class TestVectorSimilarity:
    """Tests for vector similarity concepts."""
    
    def test_vector_weight_configuration(self):
        """Test vector weight configuration in search options."""
        options = SearchOptions(vector_weight=0.8)
        
        assert options.vector_weight == 0.8
    
    def test_default_vector_weight(self):
        """Test default vector weight."""
        options = SearchOptions()
        
        assert options.vector_weight == 0.7
    
    def test_vector_weight_range(self):
        """Test that vector weight is within valid range."""
        # Valid range is 0 to 1
        options_low = SearchOptions(vector_weight=0.0)
        options_high = SearchOptions(vector_weight=1.0)
        
        assert options_low.vector_weight == 0.0
        assert options_high.vector_weight == 1.0
