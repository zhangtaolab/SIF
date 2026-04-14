"""End-to-end tests for CLI workflow."""

from pathlib import Path
from click.testing import CliRunner

import pytest

from docsift.cli.main import cli
from docsift.cli.commands.collection import collection_group
from docsift.cli.commands.search import search_group
from docsift.cli.commands.index import index_group


class TestCLIWorkflow:
    """End-to-end tests for complete CLI workflows."""
    
    def test_cli_help(self):
        """Test CLI help command."""
        # Arrange
        runner = CliRunner()
        
        # Act
        result = runner.invoke(cli, ["--help"])
        
        # Assert
        assert result.exit_code == 0
        assert "DocSift" in result.output or "docsift" in result.output.lower()
    
    def test_cli_version(self):
        """Test CLI version command."""
        # Arrange
        runner = CliRunner()
        
        # Act
        result = runner.invoke(cli, ["--version"])
        
        # Assert
        assert result.exit_code == 0


class TestCollectionWorkflow:
    """End-to-end tests for collection management workflow."""
    
    def test_create_list_delete_collection(self):
        """Test complete collection lifecycle."""
        # Arrange
        runner = CliRunner()
        
        # Step 1: Create collection
        result = runner.invoke(cli, [
            "collection", "create",
            "test-workflow-collection",
            "--description", "Test workflow collection"
        ])
        assert result.exit_code == 0
        
        # Step 2: List collections
        result = runner.invoke(cli, ["collection", "list"])
        assert result.exit_code == 0
        
        # Step 3: Show collection details
        result = runner.invoke(cli, [
            "collection", "show",
            "test-workflow-collection"
        ])
        assert result.exit_code == 0
        
        # Step 4: Delete collection
        result = runner.invoke(cli, [
            "collection", "delete",
            "--force",
            "test-workflow-collection"
        ])
        assert result.exit_code == 0
    
    def test_collection_path_management(self, temp_dir: Path):
        """Test collection path management workflow."""
        # Arrange
        runner = CliRunner()
        test_path = str(temp_dir)
        
        # Step 1: Create collection
        result = runner.invoke(cli, [
            "collection", "create",
            "path-test-collection"
        ])
        assert result.exit_code == 0
        
        # Step 2: Add path to collection
        result = runner.invoke(cli, [
            "collection", "add-path",
            "path-test-collection",
            test_path
        ])
        assert result.exit_code == 0
        
        # Step 3: Remove path from collection
        result = runner.invoke(cli, [
            "collection", "remove-path",
            "path-test-collection",
            test_path
        ])
        assert result.exit_code == 0
        
        # Cleanup
        runner.invoke(cli, [
            "collection", "delete",
            "--force",
            "path-test-collection"
        ])


class TestSearchWorkflow:
    """End-to-end tests for search workflow."""
    
    def test_search_query_workflow(self):
        """Test complete search query workflow."""
        # Arrange
        runner = CliRunner()
        
        # Test different search types
        search_types = ["bm25", "vector", "hybrid"]
        
        for search_type in search_types:
            result = runner.invoke(cli, [
                "search", "query",
                "test query",
                "--type", search_type,
                "--limit", "5"
            ])
            assert result.exit_code == 0, f"Search type {search_type} failed"
    
    def test_search_with_collection_filter(self):
        """Test search with collection filter."""
        # Arrange
        runner = CliRunner()
        
        # Act
        result = runner.invoke(cli, [
            "search", "query",
            "test query",
            "--collection", "test-collection",
            "--limit", "10"
        ])
        
        # Assert
        assert result.exit_code == 0
    
    def test_search_output_formats(self):
        """Test search with different output formats."""
        # Arrange
        runner = CliRunner()
        formats = ["rich", "json", "plain"]
        
        for fmt in formats:
            result = runner.invoke(cli, [
                "search", "query",
                "test query",
                "--format", fmt
            ])
            assert result.exit_code == 0, f"Format {fmt} failed"


class TestIndexWorkflow:
    """End-to-end tests for indexing workflow."""
    
    def test_index_status_workflow(self):
        """Test index status workflow."""
        # Arrange
        runner = CliRunner()
        
        # Test global status
        result = runner.invoke(cli, ["index", "status"])
        assert result.exit_code == 0
        
        # Test collection-specific status
        result = runner.invoke(cli, ["index", "status", "test-collection"])
        assert result.exit_code == 0
    
    def test_index_stats_workflow(self):
        """Test index stats workflow."""
        # Arrange
        runner = CliRunner()
        
        # Test global stats
        result = runner.invoke(cli, ["index", "stats"])
        assert result.exit_code == 0
        
        # Test collection-specific stats
        result = runner.invoke(cli, ["index", "stats", "test-collection"])
        assert result.exit_code == 0
    
    def test_index_update_workflow(self):
        """Test index update workflow."""
        # Arrange
        runner = CliRunner()
        
        # Act
        result = runner.invoke(cli, [
            "index", "update",
            "test-collection"
        ])
        
        # Assert
        assert result.exit_code == 0


class TestCompleteWorkflow:
    """Complete end-to-end workflow tests."""
    
    def test_full_document_workflow(self, temp_dir: Path):
        """Test complete document management workflow."""
        # Arrange
        runner = CliRunner()
        collection_name = "e2e-test-collection"
        
        # Create test document
        doc_dir = temp_dir / "docs"
        doc_dir.mkdir()
        doc_file = doc_dir / "test_doc.md"
        doc_file.write_text("""---
title: E2E Test Document
author: Test Author
tags: [e2e, test]
---

# E2E Test Document

This is a test document for end-to-end testing.

## Section 1

Content for section 1.

## Section 2

Content for section 2.
""")
        
        try:
            # Step 1: Create collection
            result = runner.invoke(cli, [
                "collection", "create",
                collection_name,
                "--description", "E2E test collection"
            ])
            assert result.exit_code == 0
            
            # Step 2: Add path to collection
            result = runner.invoke(cli, [
                "collection", "add-path",
                collection_name,
                str(doc_dir)
            ])
            assert result.exit_code == 0
            
            # Step 3: Check collection status
            result = runner.invoke(cli, [
                "collection", "show",
                collection_name
            ])
            assert result.exit_code == 0
            
            # Step 4: Search in collection
            result = runner.invoke(cli, [
                "search", "query",
                "test document",
                "--collection", collection_name
            ])
            assert result.exit_code == 0
            
        finally:
            # Cleanup: Delete collection
            runner.invoke(cli, [
                "collection", "delete",
                "--force",
                collection_name
            ])
    
    def test_multiple_collections_workflow(self, temp_dir: Path):
        """Test workflow with multiple collections."""
        # Arrange
        runner = CliRunner()
        collections = ["col-1", "col-2"]
        
        try:
            # Create multiple collections
            for col in collections:
                result = runner.invoke(cli, [
                    "collection", "create",
                    col
                ])
                assert result.exit_code == 0
            
            # List all collections
            result = runner.invoke(cli, ["collection", "list"])
            assert result.exit_code == 0
            
            # Search across collections
            result = runner.invoke(cli, [
                "search", "query",
                "test",
                "--collection", "col-1",
                "--collection", "col-2"
            ])
            assert result.exit_code == 0
            
        finally:
            # Cleanup
            for col in collections:
                runner.invoke(cli, [
                    "collection", "delete",
                    "--force",
                    col
                ])


class TestCLIErrorHandling:
    """Tests for CLI error handling."""
    
    def test_nonexistent_collection(self):
        """Test handling of nonexistent collection."""
        # Arrange
        runner = CliRunner()
        
        # Act
        result = runner.invoke(cli, [
            "collection", "show",
            "definitely-does-not-exist"
        ])
        
        # Assert - should handle gracefully
        assert result.exit_code == 0
    
    def test_invalid_search_type(self):
        """Test handling of invalid search type."""
        # Arrange
        runner = CliRunner()
        
        # Act
        result = runner.invoke(cli, [
            "search", "query",
            "test",
            "--type", "invalid"
        ])
        
        # Assert - should fail with invalid choice
        assert result.exit_code != 0
    
    def test_missing_required_argument(self):
        """Test handling of missing required argument."""
        # Arrange
        runner = CliRunner()
        
        # Act - search query without query argument
        result = runner.invoke(cli, ["search", "query"])
        
        # Assert
        assert result.exit_code != 0
