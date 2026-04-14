"""Tests for search CLI commands."""

from click.testing import CliRunner

import pytest

from docsift.cli.commands.search import (
    search_group,
    search_query,
    search_interactive,
    search_similar,
    search_explain,
)


class TestSearchGroup:
    """Tests for search command group."""
    
    def test_search_group_exists(self):
        """Test that search group exists."""
        assert search_group is not None
    
    def test_search_group_name(self):
        """Test search group name."""
        assert search_group.name == "search"


class TestSearchQuery:
    """Tests for search query command."""
    
    def test_query_command_exists(self):
        """Test that query command exists."""
        assert search_query is not None
    
    def test_query_basic(self):
        """Test basic search query."""
        # Arrange
        runner = CliRunner()
        
        # Act
        result = runner.invoke(search_query, ["test query"])
        
        # Assert
        assert result.exit_code == 0
        assert "test query" in result.output
    
    def test_query_with_collection(self):
        """Test search query with collection filter."""
        # Arrange
        runner = CliRunner()
        
        # Act
        result = runner.invoke(search_query, [
            "test query",
            "--collection", "my-collection"
        ])
        
        # Assert
        assert result.exit_code == 0
        assert "my-collection" in result.output
    
    def test_query_with_type(self):
        """Test search query with search type."""
        # Arrange
        runner = CliRunner()
        
        # Act
        result = runner.invoke(search_query, [
            "test query",
            "--type", "bm25"
        ])
        
        # Assert
        assert result.exit_code == 0
        assert "bm25" in result.output
    
    def test_query_with_limit(self):
        """Test search query with limit."""
        # Arrange
        runner = CliRunner()
        
        # Act
        result = runner.invoke(search_query, [
            "test query",
            "--limit", "5"
        ])
        
        # Assert
        assert result.exit_code == 0
    
    def test_query_with_threshold(self):
        """Test search query with threshold."""
        # Arrange
        runner = CliRunner()
        
        # Act
        result = runner.invoke(search_query, [
            "test query",
            "--threshold", "0.5"
        ])
        
        # Assert
        assert result.exit_code == 0
    
    def test_query_json_format(self):
        """Test search query with JSON format."""
        # Arrange
        runner = CliRunner()
        
        # Act
        result = runner.invoke(search_query, [
            "test query",
            "--format", "json"
        ])
        
        # Assert
        assert result.exit_code == 0
        assert "query" in result.output
    
    def test_query_plain_format(self):
        """Test search query with plain format."""
        # Arrange
        runner = CliRunner()
        
        # Act
        result = runner.invoke(search_query, [
            "test query",
            "--format", "plain"
        ])
        
        # Assert
        assert result.exit_code == 0


class TestSearchInteractive:
    """Tests for search interactive command."""
    
    def test_interactive_command_exists(self):
        """Test that interactive command exists."""
        assert search_interactive is not None
    
    def test_interactive_mode(self):
        """Test interactive search mode."""
        # Arrange
        runner = CliRunner()
        
        # Act
        result = runner.invoke(search_interactive, input="test query\nquit\n")
        
        # Assert
        assert result.exit_code == 0
        assert "Interactive Search Mode" in result.output
    
    def test_interactive_with_collection(self):
        """Test interactive mode with collection filter."""
        # Arrange
        runner = CliRunner()
        
        # Act
        result = runner.invoke(search_interactive, [
            "--collection", "my-collection"
        ], input="quit\n")
        
        # Assert
        assert result.exit_code == 0


class TestSearchSimilar:
    """Tests for search similar command."""
    
    def test_similar_command_exists(self):
        """Test that similar command exists."""
        assert search_similar is not None
    
    def test_similar_basic(self):
        """Test basic similar search."""
        # Arrange
        runner = CliRunner()
        
        # Act
        result = runner.invoke(search_similar, ["/path/to/document.md"])
        
        # Assert
        assert result.exit_code == 0
        assert "/path/to/document.md" in result.output
    
    def test_similar_with_limit(self):
        """Test similar search with limit."""
        # Arrange
        runner = CliRunner()
        
        # Act
        result = runner.invoke(search_similar, [
            "/path/to/document.md",
            "--limit", "5"
        ])
        
        # Assert
        assert result.exit_code == 0
        assert "5" in result.output


class TestSearchExplain:
    """Tests for search explain command."""
    
    def test_explain_command_exists(self):
        """Test that explain command exists."""
        assert search_explain is not None
    
    def test_explain_basic(self):
        """Test basic explain command."""
        # Arrange
        runner = CliRunner()
        
        # Act
        result = runner.invoke(search_explain, [
            "test query",
            "/path/to/document.md"
        ])
        
        # Assert
        assert result.exit_code == 0
        assert "test query" in result.output
        assert "/path/to/document.md" in result.output
        assert "Explanation:" in result.output
