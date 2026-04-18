"""Unit tests for search functionality."""

import pytest

from docsift.models.search import (
    SearchQuery,
    SearchOptions,
    SearchType,
    SearchResult,
    SearchResponse,
)
from docsift.search.strategy import SearchContext


class TestSearchQuery:
    """Tests for search query models."""

    def test_basic_search_query(self):
        """Test creating a basic search query."""
        query = SearchQuery(query="machine learning")

        assert query.query == "machine learning"
        assert query.search_type == SearchType.HYBRID
        assert query.collection_ids is None

    def test_search_query_with_collections(self):
        """Test search query with collection filter."""
        query = SearchQuery(
            query="python",
            collection_ids=["collection-1", "collection-2"],
        )

        assert query.collection_ids == ["collection-1", "collection-2"]

    def test_search_query_validation(self):
        """Test search query validation."""
        with pytest.raises(Exception):
            SearchQuery(query="")  # Empty query should fail


class TestSearchOptions:
    """Tests for search options."""

    def test_default_options(self):
        """Test default search options."""
        options = SearchOptions()

        assert options.limit == 10
        assert options.offset == 0
        assert options.threshold == 0.0
        assert options.bm25_k1 == 1.5
        assert options.bm25_b == 0.75

    def test_custom_options(self):
        """Test custom search options."""
        options = SearchOptions(
            limit=20,
            threshold=0.5,
            bm25_k1=2.0,
        )

        assert options.limit == 20
        assert options.threshold == 0.5
        assert options.bm25_k1 == 2.0

    def test_limit_validation(self):
        """Test limit validation."""
        with pytest.raises(Exception):
            SearchOptions(limit=0)  # Should be >= 1

        with pytest.raises(Exception):
            SearchOptions(limit=101)  # Should be <= 100


class TestSearchContext:
    """Tests for search context."""

    def test_search_context_creation(self):
        """Test creating search context."""
        context = SearchContext(
            query="test query",
            query_embedding=[0.1, 0.2, 0.3],
        )

        assert context.query == "test query"
        assert context.query_embedding == [0.1, 0.2, 0.3]

    def test_search_context_without_embedding(self):
        """Test search context without embedding."""
        context = SearchContext(query="test query")

        assert context.query == "test query"
        assert context.query_embedding is None


class TestSearchResult:
    """Tests for search result models."""

    def test_search_result(self):
        """Test search result creation."""
        result = SearchResult(
            document_id="doc-1",
            document_path="/path/to/doc.md",
            score=0.95,
        )

        assert result.document_id == "doc-1"
        assert result.score == 0.95

    def test_search_result_with_scores(self):
        """Test search result with component scores."""
        result = SearchResult(
            document_id="doc-1",
            document_path="/path/to/doc.md",
            score=0.85,
            bm25_score=0.80,
            vector_score=0.90,
        )

        assert result.bm25_score == 0.80
        assert result.vector_score == 0.90


class TestSearchResponse:
    """Tests for search response."""

    def test_search_response(self):
        """Test search response creation."""
        results = [
            SearchResult(
                document_id="doc-1",
                document_path="/path/one.md",
                score=0.95,
            ),
            SearchResult(
                document_id="doc-2",
                document_path="/path/two.md",
                score=0.85,
            ),
        ]

        response = SearchResponse(
            query="test",
            search_type=SearchType.HYBRID,
            total=2,
            results=results,
            search_time_ms=100.5,
        )

        assert response.query == "test"
        assert response.total == 2
        assert len(response.results) == 2
        assert response.search_time_ms == 100.5
