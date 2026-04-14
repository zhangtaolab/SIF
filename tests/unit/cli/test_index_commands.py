"""Tests for index CLI commands."""

from click.testing import CliRunner

import pytest

from docsift.cli.commands.index import (
    index_group,
    index_add,
    index_update,
    index_remove,
    index_status,
    index_rebuild,
    index_stats,
)


class TestIndexGroup:
    """Tests for index command group."""
    
    def test_index_group_exists(self):
        """Test that index group exists."""
        assert index_group is not None
    
    def test_index_group_name(self):
        """Test index group name."""
        assert index_group.name == "index"


class TestIndexAdd:
    """Tests for index add command."""
    
    def test_add_command_exists(self):
        """Test that add command exists."""
        assert index_add is not None
    
    def test_add_basic(self, temp_dir):
        """Test basic index add."""
        # Arrange
        runner = CliRunner()
        
        # Act
        result = runner.invoke(index_add, [
            "test-collection",
            str(temp_dir)
        ])
        
        # Assert
        assert result.exit_code == 0
        assert "test-collection" in result.output
        assert str(temp_dir) in result.output
    
    def test_add_with_watch(self, temp_dir):
        """Test index add with watch flag."""
        # Arrange
        runner = CliRunner()
        
        # Act
        result = runner.invoke(index_add, [
            "test-collection",
            str(temp_dir),
            "--watch"
        ])
        
        # Assert
        assert result.exit_code == 0
        assert "Watching" in result.output


class TestIndexUpdate:
    """Tests for index update command."""
    
    def test_update_command_exists(self):
        """Test that update command exists."""
        assert index_update is not None
    
    def test_update_basic(self):
        """Test basic index update."""
        # Arrange
        runner = CliRunner()
        
        # Act
        result = runner.invoke(index_update, ["test-collection"])
        
        # Assert
        assert result.exit_code == 0
        assert "test-collection" in result.output
        assert "updated" in result.output.lower()
    
    def test_update_with_force(self):
        """Test index update with force flag."""
        # Arrange
        runner = CliRunner()
        
        # Act
        result = runner.invoke(index_update, [
            "test-collection",
            "--force"
        ])
        
        # Assert
        assert result.exit_code == 0


class TestIndexRemove:
    """Tests for index remove command."""
    
    def test_remove_command_exists(self):
        """Test that remove command exists."""
        assert index_remove is not None
    
    def test_remove_with_confirmation(self):
        """Test index remove with confirmation."""
        # Arrange
        runner = CliRunner()
        
        # Act
        result = runner.invoke(index_remove, ["test-collection"], input="y\n")
        
        # Assert
        assert result.exit_code == 0
        assert "Removing" in result.output
    
    def test_remove_with_force(self):
        """Test index remove with force flag."""
        # Arrange
        runner = CliRunner()
        
        # Act
        result = runner.invoke(index_remove, [
            "--force",
            "test-collection"
        ])
        
        # Assert
        assert result.exit_code == 0
        assert "Removing" in result.output
    
    def test_remove_cancelled(self):
        """Test index remove with cancelled confirmation."""
        # Arrange
        runner = CliRunner()
        
        # Act
        result = runner.invoke(index_remove, ["test-collection"], input="n\n")
        
        # Assert
        assert result.exit_code == 0
        assert "Removing" not in result.output


class TestIndexStatus:
    """Tests for index status command."""
    
    def test_status_command_exists(self):
        """Test that status command exists."""
        assert index_status is not None
    
    def test_status_with_collection(self):
        """Test index status for specific collection."""
        # Arrange
        runner = CliRunner()
        
        # Act
        result = runner.invoke(index_status, ["test-collection"])
        
        # Assert
        assert result.exit_code == 0
        assert "test-collection" in result.output
        assert "Documents:" in result.output
    
    def test_status_all_collections(self):
        """Test index status for all collections."""
        # Arrange
        runner = CliRunner()
        
        # Act
        result = runner.invoke(index_status)
        
        # Assert
        assert result.exit_code == 0
        assert "Total collections:" in result.output


class TestIndexRebuild:
    """Tests for index rebuild command."""
    
    def test_rebuild_command_exists(self):
        """Test that rebuild command exists."""
        assert index_rebuild is not None
    
    def test_rebuild_with_confirmation(self):
        """Test index rebuild with confirmation."""
        # Arrange
        runner = CliRunner()
        
        # Act
        result = runner.invoke(index_rebuild, ["test-collection"], input="y\n")
        
        # Assert
        assert result.exit_code == 0
        assert "Rebuilding" in result.output
        assert "rebuilt" in result.output.lower()
    
    def test_rebuild_cancelled(self):
        """Test index rebuild with cancelled confirmation."""
        # Arrange
        runner = CliRunner()
        
        # Act
        result = runner.invoke(index_rebuild, ["test-collection"], input="n\n")
        
        # Assert
        assert result.exit_code == 0
        assert "Rebuilding" not in result.output


class TestIndexStats:
    """Tests for index stats command."""
    
    def test_stats_command_exists(self):
        """Test that stats command exists."""
        assert index_stats is not None
    
    def test_stats_with_collection(self):
        """Test index stats for specific collection."""
        # Arrange
        runner = CliRunner()
        
        # Act
        result = runner.invoke(index_stats, ["test-collection"])
        
        # Assert
        assert result.exit_code == 0
        assert "Statistics" in result.output
        assert "Documents indexed:" in result.output
    
    def test_stats_all_collections(self):
        """Test index stats for all collections."""
        # Arrange
        runner = CliRunner()
        
        # Act
        result = runner.invoke(index_stats)
        
        # Assert
        assert result.exit_code == 0
        assert "Global" in result.output or "Statistics" in result.output
