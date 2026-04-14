"""Tests for document indexer."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from docsift.core.document import Document
from docsift.indexing.indexer import DocumentIndexer, IndexStatus


class TestIndexStatus:
    """Tests for IndexStatus enum."""
    
    def test_pending_status(self):
        """Test PENDING status exists."""
        assert IndexStatus.PENDING is not None
    
    def test_indexing_status(self):
        """Test INDEXING status exists."""
        assert IndexStatus.INDEXING is not None
    
    def test_completed_status(self):
        """Test COMPLETED status exists."""
        assert IndexStatus.COMPLETED is not None
    
    def test_failed_status(self):
        """Test FAILED status exists."""
        assert IndexStatus.FAILED is not None


class TestDocumentIndexerInit:
    """Tests for DocumentIndexer initialization."""
    
    def test_init_with_repository(self):
        """Test initialization with repository."""
        # Arrange
        mock_repo = MagicMock()
        
        # Act
        indexer = DocumentIndexer(mock_repo)
        
        # Assert
        assert indexer._repository is mock_repo


class TestDocumentIndexerIndexDocument:
    """Tests for indexing documents."""
    
    def test_index_document_creates_document(self):
        """Test that index_document creates a document."""
        # Arrange
        mock_repo = MagicMock()
        indexer = DocumentIndexer(mock_repo)
        
        # Act
        with patch.object(indexer, '_parse_file') as mock_parse:
            mock_parse.return_value = ("content", {}, "title")
            with patch.object(indexer, '_create_document') as mock_create:
                mock_create.return_value = MagicMock(spec=Document)
                indexer.index_document(Path("/test/file.md"), "collection-1")
        
        # Assert
        mock_parse.assert_called_once()
    
    def test_index_document_checks_existing(self):
        """Test that index_document checks for existing document."""
        # Arrange
        mock_repo = MagicMock()
        mock_repo.exists.return_value = True
        mock_repo.get_checksum.return_value = "old_checksum"
        
        indexer = DocumentIndexer(mock_repo)
        
        # Act
        with patch.object(indexer, '_calculate_checksum') as mock_checksum:
            mock_checksum.return_value = "old_checksum"  # Same checksum
            result = indexer.index_document(Path("/test/file.md"), "collection-1")
        
        # Assert
        # Should skip if checksum matches
        assert result is None or result.status == IndexStatus.COMPLETED


class TestDocumentIndexerChecksum:
    """Tests for checksum calculation."""
    
    def test_calculate_checksum_consistency(self):
        """Test that checksum is consistent for same content."""
        # Arrange
        mock_repo = MagicMock()
        indexer = DocumentIndexer(mock_repo)
        
        # Act
        checksum1 = indexer._calculate_checksum("test content")
        checksum2 = indexer._calculate_checksum("test content")
        
        # Assert
        assert checksum1 == checksum2
    
    def test_calculate_checksum_different_content(self):
        """Test that different content produces different checksums."""
        # Arrange
        mock_repo = MagicMock()
        indexer = DocumentIndexer(mock_repo)
        
        # Act
        checksum1 = indexer._calculate_checksum("content 1")
        checksum2 = indexer._calculate_checksum("content 2")
        
        # Assert
        assert checksum1 != checksum2


class TestDocumentIndexerBatchOperations:
    """Tests for batch indexing operations."""
    
    def test_index_batch_processes_multiple_files(self):
        """Test that index_batch processes multiple files."""
        # Arrange
        mock_repo = MagicMock()
        indexer = DocumentIndexer(mock_repo)
        files = [Path("/test/file1.md"), Path("/test/file2.md")]
        
        # Act
        with patch.object(indexer, 'index_document') as mock_index:
            mock_index.return_value = MagicMock()
            results = indexer.index_batch(files, "collection-1")
        
        # Assert
        assert mock_index.call_count == 2
    
    def test_index_batch_empty_list(self):
        """Test that index_batch handles empty file list."""
        # Arrange
        mock_repo = MagicMock()
        indexer = DocumentIndexer(mock_repo)
        
        # Act
        results = indexer.index_batch([], "collection-1")
        
        # Assert
        assert results == []


class TestDocumentIndexerDeleteOperations:
    """Tests for delete operations."""
    
    def test_delete_document_calls_repository(self):
        """Test that delete_document calls repository delete."""
        # Arrange
        mock_repo = MagicMock()
        mock_repo.delete.return_value = True
        indexer = DocumentIndexer(mock_repo)
        
        # Act
        result = indexer.delete_document("doc-1")
        
        # Assert
        mock_repo.delete.assert_called_once_with("doc-1")
        assert result is True
    
    def test_delete_by_collection_calls_repository(self):
        """Test that delete_by_collection calls repository."""
        # Arrange
        mock_repo = MagicMock()
        mock_repo.delete_by_collection.return_value = 5
        indexer = DocumentIndexer(mock_repo)
        
        # Act
        result = indexer.delete_by_collection("collection-1")
        
        # Assert
        mock_repo.delete_by_collection.assert_called_once_with("collection-1")
        assert result == 5


class TestDocumentIndexerUpdateOperations:
    """Tests for update operations."""
    
    def test_update_document_reindexes(self):
        """Test that update_document reindexes the document."""
        # Arrange
        mock_repo = MagicMock()
        indexer = DocumentIndexer(mock_repo)
        
        # Act
        with patch.object(indexer, '_get_document_path') as mock_get_path:
            mock_get_path.return_value = Path("/test/file.md")
            with patch.object(indexer, 'index_document') as mock_index:
                mock_index.return_value = MagicMock()
                indexer.update_document("doc-1", "collection-1")
        
        # Assert
        mock_index.assert_called_once()


class TestDocumentIndexerStatus:
    """Tests for indexer status methods."""
    
    def test_get_indexing_status(self):
        """Test getting indexing status."""
        # Arrange
        mock_repo = MagicMock()
        mock_repo.list_by_collection.return_value = [
            MagicMock(indexed_at=None),
            MagicMock(indexed_at="2024-01-01"),
        ]
        indexer = DocumentIndexer(mock_repo)
        
        # Act
        status = indexer.get_indexing_status("collection-1")
        
        # Assert
        assert "total" in status
        assert "indexed" in status


class TestDocumentIndexerEdgeCases:
    """Tests for indexer edge cases."""
    
    def test_index_nonexistent_file(self):
        """Test indexing a nonexistent file."""
        # Arrange
        mock_repo = MagicMock()
        indexer = DocumentIndexer(mock_repo)
        
        # Act & Assert
        with pytest.raises(FileNotFoundError):
            indexer.index_document(Path("/nonexistent/file.md"), "collection-1")
    
    def test_index_empty_file(self, temp_dir: Path):
        """Test indexing an empty file."""
        # Arrange
        mock_repo = MagicMock()
        indexer = DocumentIndexer(mock_repo)
        empty_file = temp_dir / "empty.md"
        empty_file.write_text("")
        
        # Act
        with patch.object(indexer, '_create_document') as mock_create:
            mock_create.return_value = MagicMock(spec=Document)
            result = indexer.index_document(empty_file, "collection-1")
        
        # Assert
        # Should handle empty file gracefully
        assert result is not None
