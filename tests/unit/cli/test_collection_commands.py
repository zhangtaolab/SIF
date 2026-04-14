"""Tests for collection CLI commands."""

from unittest.mock import MagicMock, patch
from click.testing import CliRunner

import pytest

from docsift.cli.commands.collection import (
    collection_group,
    collection_list,
    collection_create,
    collection_delete,
    collection_rename,
    collection_add_path,
    collection_remove_path,
    collection_show,
)


class TestCollectionGroup:
    """Tests for collection command group."""
    
    def test_collection_group_exists(self):
        """Test that collection group exists."""
        assert collection_group is not None
    
    def test_collection_group_name(self):
        """Test collection group name."""
        assert collection_group.name == "collection"


class TestCollectionList:
    """Tests for collection list command."""
    
    def test_list_command_exists(self):
        """Test that list command exists."""
        assert collection_list is not None
    
    def test_list_default_format(self):
        """Test list with default table format."""
        # Arrange
        runner = CliRunner()
        
        # Act
        result = runner.invoke(collection_list)
        
        # Assert
        assert result.exit_code == 0
        assert "Collections" in result.output
    
    def test_list_json_format(self):
        """Test list with JSON format."""
        # Arrange
        runner = CliRunner()
        
        # Act
        result = runner.invoke(collection_list, ["--format", "json"])
        
        # Assert
        assert result.exit_code == 0
        assert "collections" in result.output
    
    def test_list_plain_format(self):
        """Test list with plain format."""
        # Arrange
        runner = CliRunner()
        
        # Act
        result = runner.invoke(collection_list, ["--format", "plain"])
        
        # Assert
        assert result.exit_code == 0


class TestCollectionCreate:
    """Tests for collection create command."""
    
    def test_create_command_exists(self):
        """Test that create command exists."""
        assert collection_create is not None
    
    def test_create_with_name_only(self):
        """Test creating collection with name only."""
        # Arrange
        runner = CliRunner()
        
        # Act
        result = runner.invoke(collection_create, ["test-collection"])
        
        # Assert
        assert result.exit_code == 0
        assert "Creating collection 'test-collection'" in result.output
    
    def test_create_with_description(self):
        """Test creating collection with description."""
        # Arrange
        runner = CliRunner()
        
        # Act
        result = runner.invoke(collection_create, [
            "test-collection",
            "--description", "Test description"
        ])
        
        # Assert
        assert result.exit_code == 0
        assert "Test description" in result.output
    
    def test_create_with_paths(self):
        """Test creating collection with paths."""
        # Arrange
        runner = CliRunner()
        
        # Act
        result = runner.invoke(collection_create, [
            "test-collection",
            "--path", "/path/one",
            "--path", "/path/two"
        ])
        
        # Assert
        assert result.exit_code == 0
        assert "/path/one" in result.output
        assert "/path/two" in result.output


class TestCollectionDelete:
    """Tests for collection delete command."""
    
    def test_delete_command_exists(self):
        """Test that delete command exists."""
        assert collection_delete is not None
    
    def test_delete_with_confirmation(self):
        """Test deleting collection with confirmation."""
        # Arrange
        runner = CliRunner()
        
        # Act
        result = runner.invoke(collection_delete, ["test-collection"], input="y\n")
        
        # Assert
        assert result.exit_code == 0
        assert "Deleting collection" in result.output
    
    def test_delete_with_force(self):
        """Test deleting collection with force flag."""
        # Arrange
        runner = CliRunner()
        
        # Act
        result = runner.invoke(collection_delete, ["--force", "test-collection"])
        
        # Assert
        assert result.exit_code == 0
        assert "Deleting collection" in result.output
    
    def test_delete_cancelled(self):
        """Test deleting collection with cancelled confirmation."""
        # Arrange
        runner = CliRunner()
        
        # Act
        result = runner.invoke(collection_delete, ["test-collection"], input="n\n")
        
        # Assert
        assert result.exit_code == 0
        assert "Deleting collection" not in result.output


class TestCollectionRename:
    """Tests for collection rename command."""
    
    def test_rename_command_exists(self):
        """Test that rename command exists."""
        assert collection_rename is not None
    
    def test_rename_collection(self):
        """Test renaming collection."""
        # Arrange
        runner = CliRunner()
        
        # Act
        result = runner.invoke(collection_rename, ["old-name", "new-name"])
        
        # Assert
        assert result.exit_code == 0
        assert "old-name" in result.output
        assert "new-name" in result.output


class TestCollectionAddPath:
    """Tests for collection add-path command."""
    
    def test_add_path_command_exists(self):
        """Test that add-path command exists."""
        assert collection_add_path is not None
    
    def test_add_path(self, temp_dir):
        """Test adding path to collection."""
        # Arrange
        runner = CliRunner()
        test_path = str(temp_dir)
        
        # Act
        result = runner.invoke(collection_add_path, ["test-collection", test_path])
        
        # Assert
        assert result.exit_code == 0
        assert test_path in result.output
        assert "test-collection" in result.output


class TestCollectionRemovePath:
    """Tests for collection remove-path command."""
    
    def test_remove_path_command_exists(self):
        """Test that remove-path command exists."""
        assert collection_remove_path is not None
    
    def test_remove_path(self):
        """Test removing path from collection."""
        # Arrange
        runner = CliRunner()
        
        # Act
        result = runner.invoke(collection_remove_path, ["test-collection", "/path/to/remove"])
        
        # Assert
        assert result.exit_code == 0
        assert "/path/to/remove" in result.output
        assert "test-collection" in result.output


class TestCollectionShow:
    """Tests for collection show command."""
    
    def test_show_command_exists(self):
        """Test that show command exists."""
        assert collection_show is not None
    
    def test_show_collection(self):
        """Test showing collection details."""
        # Arrange
        runner = CliRunner()
        
        # Act
        result = runner.invoke(collection_show, ["test-collection"])
        
        # Assert
        assert result.exit_code == 0
        assert "test-collection" in result.output
        assert "Documents:" in result.output
