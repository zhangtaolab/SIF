"""Tests for query expansion."""

from unittest.mock import MagicMock

import pytest

from sif.search.expansion import QueryExpansion


class TestQueryExpansionInit:
    """Tests for QueryExpansion initialization."""

    def test_default_init(self):
        """Test default query expansion initialization."""
        # Act
        expander = QueryExpansion()

        # Assert
        assert expander._embedding_manager is None
        assert expander._expansion_factor == 3

    def test_init_with_embedding_manager(self, mock_embedding_manager: MagicMock):
        """Test initialization with embedding manager."""
        # Act
        expander = QueryExpansion(embedding_manager=mock_embedding_manager)

        # Assert
        assert expander._embedding_manager is mock_embedding_manager

    def test_init_with_custom_expansion_factor(self):
        """Test initialization with custom expansion factor."""
        # Act
        expander = QueryExpansion(expansion_factor=5)

        # Assert
        assert expander._expansion_factor == 5


class TestQueryExpansionExpand:
    """Tests for query expansion."""

    def test_expand_returns_list(self):
        """Test that expand returns a list of strings."""
        # Arrange
        expander = QueryExpansion()

        # Act
        result = expander.expand("test query")

        # Assert
        assert isinstance(result, list)
        assert all(isinstance(r, str) for r in result)

    def test_expand_returns_original_when_no_terms(self):
        """Test that expand returns original query when no expansion terms."""
        # Arrange
        expander = QueryExpansion()

        # Act
        result = expander.expand("test query")

        # Assert
        assert result == ["test query"]

    def test_expand_appends_expansion_terms(self):
        """Test that expand appends expansion terms to query."""
        # Arrange
        expander = QueryExpansion()

        # Mock _get_expansion_terms to return some terms
        with pytest.MonkeyPatch.context() as mp:
            mp.setattr(expander, "_get_expansion_terms", lambda _q: ["term1", "term2"])

            # Act
            result = expander.expand("test query")

            # Assert
            assert result[0] == "test query"
            assert "test query term1" in result
            assert "test query term2" in result

    def test_expand_empty_query(self):
        """Test expanding empty query."""
        # Arrange
        expander = QueryExpansion()

        # Act
        result = expander.expand("")

        # Assert
        assert result == [""]

    def test_expand_with_intent(self):
        """Test expanding query with intent hint."""
        # Arrange
        expander = QueryExpansion()

        # Mock _get_expansion_terms to return some terms
        with pytest.MonkeyPatch.context() as mp:
            mp.setattr(expander, "_get_expansion_terms", lambda _q: ["term1"])

            # Act
            result = expander.expand("test query", intent="code")

            # Assert
            assert all(r.startswith("code: ") for r in result)
            assert "code: test query" in result


class TestQueryExpansionGetExpansionTerms:
    """Tests for getting expansion terms."""

    def test_get_expansion_terms_returns_list(self):
        """Test that _get_expansion_terms returns a list."""
        # Arrange
        expander = QueryExpansion()

        # Act
        terms = expander._get_expansion_terms("test query")

        # Assert
        assert isinstance(terms, list)

    def test_get_expansion_terms_no_embedding_manager(self):
        """Test that _get_expansion_terms returns empty without embedding manager."""
        # Arrange
        expander = QueryExpansion()

        # Act
        terms = expander._get_expansion_terms("any query")

        # Assert
        assert terms == []

    def test_get_expansion_terms_with_embedding_manager(self, mock_embedding_manager: MagicMock):
        """Test _get_expansion_terms with embedding manager."""
        # Arrange
        expander = QueryExpansion(embedding_manager=mock_embedding_manager)

        # Act
        terms = expander._get_expansion_terms("python search")

        # Assert
        assert isinstance(terms, list)


class TestQueryExpansionExpandBatch:
    """Tests for batch query expansion."""

    def test_expand_batch_multiple_queries(self):
        """Test expanding multiple queries."""
        # Arrange
        expander = QueryExpansion()

        # Mock _get_expansion_terms to return some terms
        with pytest.MonkeyPatch.context() as mp:
            mp.setattr(expander, "_get_expansion_terms", lambda _q: ["term1"])

            queries = ["query 1", "query 2", "query 3"]

            # Act
            results = expander.expand_batch(queries)

            # Assert
            assert isinstance(results, list)
            assert len(results) == 6  # 2 variants per query (original + 1 term)
            assert all(isinstance(r, str) for r in results)

    def test_expand_batch_deduplicates(self):
        """Test that expand_batch removes duplicate variants."""
        # Arrange
        expander = QueryExpansion()

        # Mock _get_expansion_terms to return same term for all queries
        with pytest.MonkeyPatch.context() as mp:
            mp.setattr(expander, "_get_expansion_terms", lambda _q: ["term1"])

            queries = ["query 1", "query 2"]

            # Act
            results = expander.expand_batch(queries)

            # Assert - deduplication should reduce duplicates
            assert len(results) == len(set(results))

    def test_expand_batch_empty_list(self):
        """Test expanding empty list of queries."""
        # Arrange
        expander = QueryExpansion()

        # Act
        results = expander.expand_batch([])

        # Assert
        assert results == []

    def test_expand_batch_single_query(self):
        """Test expanding single query in batch."""
        # Arrange
        expander = QueryExpansion()

        # Act
        results = expander.expand_batch(["single query"])

        # Assert
        assert len(results) == 1
        assert results[0] == "single query"


class TestQueryExpansionWithEmbeddingManager:
    """Tests for query expansion with embedding manager."""

    def test_expand_with_embedding_manager(self, mock_embedding_manager: MagicMock):
        """Test expansion when embedding manager is provided."""
        # Arrange
        expander = QueryExpansion(embedding_manager=mock_embedding_manager)

        # Act - should not raise
        result = expander.expand("test query")

        # Assert
        assert isinstance(result, list)


class TestQueryExpansionEdgeCases:
    """Tests for query expansion edge cases."""

    def test_expand_whitespace_only_query(self):
        """Test expanding whitespace-only query."""
        # Arrange
        expander = QueryExpansion()

        # Act
        result = expander.expand("   ")

        # Assert
        assert result == ["   "]

    def test_expand_special_characters(self):
        """Test expanding query with special characters."""
        # Arrange
        expander = QueryExpansion()

        # Act
        result = expander.expand("query with @#$% special chars")

        # Assert
        assert result[0] == "query with @#$% special chars"

    def test_expand_very_long_query(self):
        """Test expanding very long query."""
        # Arrange
        expander = QueryExpansion()
        long_query = "word " * 1000

        # Act
        result = expander.expand(long_query)

        # Assert
        assert isinstance(result, list)
