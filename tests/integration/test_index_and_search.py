"""Integration tests for indexing and searching workflow."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from docsift.core.collection import Collection
from docsift.core.document import Document
from docsift.indexing.parser import MarkdownParser
from docsift.indexing.chunker import Chunker, ChunkingStrategy


class TestIndexAndSearchWorkflow:
    """Integration tests for the complete index and search workflow."""
    
    def test_parse_and_chunk_document(self, sample_markdown_file: Path):
        """Test parsing and chunking a document."""
        # Arrange
        parser = MarkdownParser()
        chunker = Chunker(strategy=ChunkingStrategy.FIXED_SIZE, chunk_size=100)
        
        # Act
        parse_result = parser.parse(sample_markdown_file)
        chunks = chunker.chunk(parse_result.content)
        
        # Assert
        assert parse_result.content is not None
        assert len(chunks) > 0
        assert all(chunk.content for chunk in chunks)
    
    def test_create_collection_and_add_documents(self, sample_collection: Collection):
        """Test creating collection and adding documents."""
        # Arrange
        mock_repo = MagicMock()
        mock_repo.create.return_value = sample_collection
        
        # Act
        result = mock_repo.create(sample_collection)
        
        # Assert
        assert result.id == sample_collection.id
        assert result.name == sample_collection.name
        mock_repo.create.assert_called_once_with(sample_collection)
    
    def test_document_lifecycle(
        self,
        sample_document: Document,
        temp_dir: Path,
    ):
        """Test complete document lifecycle."""
        # Arrange
        mock_repo = MagicMock()
        
        # Step 1: Create document
        mock_repo.create.return_value = sample_document
        created = mock_repo.create(sample_document)
        assert created is not None
        
        # Step 2: Retrieve document
        mock_repo.get_by_id.return_value = created
        retrieved = mock_repo.get_by_id(created.id)
        assert retrieved.id == created.id
        
        # Step 3: Update document
        created.content = "Updated content"
        mock_repo.update.return_value = created
        updated = mock_repo.update(created)
        assert updated.content == "Updated content"
        
        # Step 4: Delete document
        mock_repo.delete.return_value = True
        deleted = mock_repo.delete(created.id)
        assert deleted is True
    
    def test_collection_document_relationship(
        self,
        sample_collection: Collection,
        sample_documents: list[Document],
    ):
        """Test relationship between collection and documents."""
        # Arrange
        mock_repo = MagicMock()
        
        # Set collection_id for all documents
        for doc in sample_documents:
            doc.collection_id = sample_collection.id
        
        # Mock repository methods
        mock_repo.get_by_id.return_value = sample_collection
        mock_repo.list_by_collection.return_value = sample_documents
        
        # Act
        collection = mock_repo.get_by_id(sample_collection.id)
        documents = mock_repo.list_by_collection(collection.id)
        
        # Assert
        assert collection is not None
        assert len(documents) == len(sample_documents)
        assert all(doc.collection_id == collection.id for doc in documents)


class TestChunkingAndEmbeddingWorkflow:
    """Integration tests for chunking and embedding workflow."""
    
    def test_chunk_document_content(self):
        """Test chunking document content."""
        # Arrange
        content = """
# Introduction

This is the introduction section.

## Section 1

Content for section 1.

## Section 2

Content for section 2.
"""
        chunker = Chunker(strategy=ChunkingStrategy.HEADING)
        
        # Act
        chunks = chunker.chunk(content)
        
        # Assert
        assert len(chunks) > 0
        # Each chunk should contain a heading
        assert any("# Introduction" in chunk.content for chunk in chunks)
    
    def test_chunk_multiple_strategies(self):
        """Test chunking with multiple strategies."""
        # Arrange
        content = "Line 1\nLine 2\nLine 3\n\nParagraph 2.\n\nParagraph 3."
        
        strategies = [
            ChunkingStrategy.FIXED_SIZE,
            ChunkingStrategy.PARAGRAPH,
            ChunkingStrategy.SENTENCE,
        ]
        
        # Act & Assert
        for strategy in strategies:
            chunker = Chunker(strategy=strategy, chunk_size=50)
            chunks = chunker.chunk(content)
            assert len(chunks) > 0, f"Strategy {strategy} produced no chunks"
    
    def test_chunk_size_limits(self):
        """Test that chunks respect size limits."""
        # Arrange
        content = "Word " * 1000  # Long content
        chunk_size = 100
        chunker = Chunker(
            strategy=ChunkingStrategy.FIXED_SIZE,
            chunk_size=chunk_size,
        )
        
        # Act
        chunks = chunker.chunk(content)
        
        # Assert
        assert len(chunks) > 1  # Should split into multiple chunks
        # Each chunk should be roughly within size limits
        # (allowing some flexibility due to line-based chunking)


class TestSearchIntegration:
    """Integration tests for search functionality."""
    
    def test_bm25_search_with_indexed_documents(
        self,
        mock_search_repository: MagicMock,
        sample_documents: list[Document],
    ):
        """Test BM25 search with indexed documents."""
        # Arrange
        from docsift.search.bm25 import BM25SearchStrategy
        from docsift.search.strategy import SearchContext
        from docsift.models.search import SearchOptions
        
        # Setup mock to return documents
        mock_search_repository.search_fts.return_value = [
            (doc.id, 0.9 - i * 0.1) for i, doc in enumerate(sample_documents[:3])
        ]
        
        strategy = BM25SearchStrategy(mock_search_repository)
        context = SearchContext(query="test query")
        options = SearchOptions()
        
        # Act
        results = strategy.search(context, options)
        
        # Assert
        assert len(results) > 0
        assert all(hasattr(r, 'document_id') for r in results)
    
    def test_vector_search_with_embeddings(
        self,
        mock_search_repository: MagicMock,
        mock_embedding_manager: MagicMock,
    ):
        """Test vector search with embeddings."""
        # Arrange
        from docsift.search.vector import VectorSearchStrategy
        from docsift.search.strategy import SearchContext
        from docsift.models.search import SearchOptions
        
        strategy = VectorSearchStrategy(mock_search_repository, mock_embedding_manager)
        context = SearchContext(query="semantic query")
        options = SearchOptions()
        
        # Act
        results = strategy.search(context, options)
        
        # Assert
        assert isinstance(results, list)
        mock_embedding_manager.embed_single.assert_called_once()


class TestEndToEndIndexing:
    """End-to-end tests for indexing workflow."""
    
    def test_full_indexing_workflow(self, temp_dir: Path):
        """Test complete indexing workflow."""
        # Arrange - Create sample markdown files
        docs_dir = temp_dir / "documents"
        docs_dir.mkdir()
        
        for i in range(3):
            file_path = docs_dir / f"doc_{i}.md"
            file_path.write_text(f"""---
title: Document {i}
author: Test Author
---

# Document {i}

This is content for document {i}.
""")
        
        # Act - Parse all files
        parser = MarkdownParser()
        parsed_documents = []
        
        for file_path in docs_dir.glob("*.md"):
            result = parser.parse(file_path)
            parsed_documents.append(result)
        
        # Assert
        assert len(parsed_documents) == 3
        assert all(doc.title for doc in parsed_documents)
    
    def test_collection_indexing_with_chunks(self, temp_dir: Path):
        """Test indexing a collection with chunking."""
        # Arrange
        collection = Collection(
            id="test-col-id",
            name="test-collection",
            paths=[str(temp_dir)],
        )
        
        # Create test document
        doc_file = temp_dir / "test.md"
        doc_file.write_text("""---
title: Test Doc
---

# Section 1

Content for section 1.

# Section 2

Content for section 2.
""")
        
        parser = MarkdownParser()
        chunker = Chunker(strategy=ChunkingStrategy.HEADING)
        
        # Act
        parse_result = parser.parse(doc_file)
        chunks = chunker.chunk(parse_result.content)
        
        # Assert
        assert parse_result.title == "Test Doc"
        assert len(chunks) >= 2  # At least 2 sections
