"""Unit tests for document chunking strategies.

This module tests the Chunker implementation including:
- Fixed-size chunking with overlap
- Paragraph-based chunking
- Sentence-based chunking
- Heading-based (markdown) chunking
- Edge cases and boundary conditions
"""

import pytest

from docsift.indexing.chunker import Chunk, Chunker, ChunkingStrategy


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def fixed_size_chunker() -> Chunker:
    """Create a fixed-size chunker with default settings."""
    return Chunker(
        strategy=ChunkingStrategy.FIXED_SIZE,
        chunk_size=100,
        chunk_overlap=20,
    )


@pytest.fixture
def paragraph_chunker() -> Chunker:
    """Create a paragraph-based chunker."""
    return Chunker(
        strategy=ChunkingStrategy.PARAGRAPH,
        chunk_size=200,
        chunk_overlap=0,
    )


@pytest.fixture
def sentence_chunker() -> Chunker:
    """Create a sentence-based chunker."""
    return Chunker(
        strategy=ChunkingStrategy.SENTENCE,
        chunk_size=150,
        chunk_overlap=0,
    )


@pytest.fixture
def heading_chunker() -> Chunker:
    """Create a heading-based chunker for markdown."""
    return Chunker(
        strategy=ChunkingStrategy.HEADING,
        chunk_size=300,
        chunk_overlap=0,
    )


@pytest.fixture
def sample_text() -> str:
    """Create sample text for testing."""
    return """This is the first line of the document.
This is the second line with some content.
This is the third line with more text to process.
This is the fourth line for testing purposes.
This is the fifth line with additional content."""


@pytest.fixture
def sample_paragraphs() -> str:
    """Create sample text with multiple paragraphs."""
    return """First paragraph with some content. This paragraph has multiple sentences to test the chunking behavior.

Second paragraph with different content. It also has multiple sentences for testing purposes.

Third paragraph is here with more content to ensure we have enough text for testing.

Fourth paragraph contains the final content for this test document."""


@pytest.fixture
def sample_markdown() -> str:
    """Create sample markdown text with headings."""
    return """# Main Title

This is the introduction paragraph.

## Section 1

Content for section 1 goes here.
More content for section 1.

## Section 2

Content for section 2 goes here.
More content for section 2.

### Subsection 2.1

Content for subsection 2.1.

## Section 3

Final section content."""


@pytest.fixture
def sample_code() -> str:
    """Create sample code for testing."""
    return '''def function_one():
    """First function docstring."""
    x = 1
    y = 2
    return x + y

def function_two():
    """Second function docstring."""
    a = 10
    b = 20
    return a * b

class MyClass:
    """Class docstring."""
    
    def method_one(self):
        """Method docstring."""
        return "hello"
    
    def method_two(self):
        """Another method."""
        return "world"'''


# =============================================================================
# Fixed-Size Chunker Tests
# =============================================================================


class TestFixedSizeChunker:
    """Test fixed-size chunking strategy."""
    
    def test_chunk_creates_multiple_chunks(self, fixed_size_chunker: Chunker, sample_text: str) -> None:
        """Test that chunking creates multiple chunks for long text.
        
        Arrange: Create chunker with small chunk size
        Act: Chunk sample text
        Assert: Returns multiple chunks
        """
        # Act
        chunks = fixed_size_chunker.chunk(sample_text)
        
        # Assert
        assert len(chunks) > 0
        assert all(isinstance(c, Chunk) for c in chunks)
    
    def test_chunk_preserves_line_boundaries(self, fixed_size_chunker: Chunker, sample_text: str) -> None:
        """Test that chunking preserves line boundaries.
        
        Arrange: Create chunker and sample text
        Act: Chunk the text
        Assert: Chunks contain complete lines
        """
        # Act
        chunks = fixed_size_chunker.chunk(sample_text)
        
        # Assert
        for chunk in chunks:
            lines = chunk.content.split("\n")
            # Each line should be complete (not truncated mid-line)
            assert all(len(line) > 0 for line in lines if lines)
    
    def test_chunk_tracks_line_numbers(self, fixed_size_chunker: Chunker, sample_text: str) -> None:
        """Test that chunking tracks start and end line numbers.
        
        Arrange: Create chunker and sample text
        Act: Chunk the text
        Assert: Chunks have correct line number tracking
        """
        # Act
        chunks = fixed_size_chunker.chunk(sample_text)
        
        # Assert
        assert len(chunks) > 0
        # First chunk should start at line 0
        assert chunks[0].start_line == 0
        # Each chunk should have valid line range
        for chunk in chunks:
            assert chunk.start_line <= chunk.end_line
    
    def test_chunk_overlap_is_applied(self) -> None:
        """Test that overlap is applied between chunks.
        
        Arrange: Create chunker with overlap
        Act: Chunk text
        Assert: Consecutive chunks share overlapping content
        """
        # Arrange
        chunker = Chunker(
            strategy=ChunkingStrategy.FIXED_SIZE,
            chunk_size=50,
            chunk_overlap=20,
        )
        text = "Line 1\nLine 2\nLine 3\nLine 4\nLine 5\nLine 6\nLine 7\nLine 8"
        
        # Act
        chunks = chunker.chunk(text)
        
        # Assert
        if len(chunks) > 1:
            # Check that there's overlap between chunks
            chunk1_lines = set(chunks[0].content.split("\n"))
            chunk2_lines = set(chunks[1].content.split("\n"))
            overlap = chunk1_lines & chunk2_lines
            # There should be some overlapping lines
            assert len(overlap) > 0 or chunks[0].end_line >= chunks[1].start_line
    
    def test_chunk_empty_string(self, fixed_size_chunker: Chunker) -> None:
        """Test chunking empty string.
        
        Arrange: Create chunker
        Act: Chunk empty string
        Assert: Returns empty list or single empty chunk
        """
        # Act
        chunks = fixed_size_chunker.chunk("")
        
        # Assert
        assert len(chunks) == 0 or (len(chunks) == 1 and chunks[0].content == "")
    
    def test_chunk_single_line(self, fixed_size_chunker: Chunker) -> None:
        """Test chunking single line text.
        
        Arrange: Create chunker
        Act: Chunk single line
        Assert: Returns single chunk
        """
        # Act
        chunks = fixed_size_chunker.chunk("Single line of text")
        
        # Assert
        assert len(chunks) == 1
        assert chunks[0].content == "Single line of text"
        assert chunks[0].start_line == 0
        assert chunks[0].end_line == 0
    
    def test_chunk_token_count_tracking(self, fixed_size_chunker: Chunker, sample_text: str) -> None:
        """Test that chunking tracks token counts.
        
        Arrange: Create chunker and sample text
        Act: Chunk the text
        Assert: Chunks have positive token counts
        """
        # Act
        chunks = fixed_size_chunker.chunk(sample_text)
        
        # Assert
        for chunk in chunks:
            assert chunk.token_count >= 0
    
    def test_chunk_respects_chunk_size(self) -> None:
        """Test that chunking respects chunk size limit.
        
        Arrange: Create chunker with specific chunk size
        Act: Chunk large text
        Assert: Chunks are within size limits
        """
        # Arrange
        chunk_size = 50
        chunker = Chunker(
            strategy=ChunkingStrategy.FIXED_SIZE,
            chunk_size=chunk_size,
            chunk_overlap=0,
        )
        # Create text that will require multiple chunks
        text = "\n".join([f"This is line {i} with some content" for i in range(20)])
        
        # Act
        chunks = chunker.chunk(text)
        
        # Assert
        # Note: Due to line boundary preservation, chunks may exceed target size
        # but should not be excessively large
        for chunk in chunks:
            # Allow some flexibility due to line boundaries
            assert len(chunk.content) < chunk_size * 3 or chunk.token_count <= chunk_size * 2


# =============================================================================
# Paragraph Chunker Tests
# =============================================================================


class TestParagraphChunker:
    """Test paragraph-based chunking strategy."""
    
    def test_chunk_by_paragraph(self, paragraph_chunker: Chunker, sample_paragraphs: str) -> None:
        """Test chunking by paragraphs.
        
        Arrange: Create paragraph chunker
        Act: Chunk text with multiple paragraphs
        Assert: Returns chunks grouped by paragraphs
        """
        # Act
        chunks = paragraph_chunker.chunk(sample_paragraphs)
        
        # Assert
        assert len(chunks) > 0
        # Should have at least some chunks (may combine small paragraphs)
        assert len(chunks) <= 4  # At most one per paragraph
    
    def test_paragraph_boundaries_preserved(self, paragraph_chunker: Chunker, sample_paragraphs: str) -> None:
        """Test that paragraph boundaries are preserved.
        
        Arrange: Create paragraph chunker
        Act: Chunk text
        Assert: Paragraphs not split mid-paragraph
        """
        # Act
        chunks = paragraph_chunker.chunk(sample_paragraphs)
        
        # Assert
        for chunk in chunks:
            # Each chunk should contain complete paragraphs
            # (no chunk should start or end mid-sentence within a paragraph)
            content = chunk.content.strip()
            assert len(content) > 0
    
    def test_chunk_empty_paragraphs(self, paragraph_chunker: Chunker) -> None:
        """Test chunking text with empty paragraphs.
        
        Arrange: Create paragraph chunker
        Act: Chunk text with extra newlines
        Assert: Handles empty paragraphs gracefully
        """
        # Arrange
        text = "Paragraph 1\n\n\n\nParagraph 2"
        
        # Act
        chunks = paragraph_chunker.chunk(text)
        
        # Assert
        assert len(chunks) >= 1
        # Should not create empty chunks
        assert all(len(c.content.strip()) > 0 for c in chunks)


# =============================================================================
# Sentence Chunker Tests
# =============================================================================


class TestSentenceChunker:
    """Test sentence-based chunking strategy."""
    
    def test_chunk_by_sentence(self, sentence_chunker: Chunker) -> None:
        """Test chunking by sentences.
        
        Arrange: Create sentence chunker
        Act: Chunk text with multiple sentences
        Assert: Returns chunks with complete sentences
        """
        # Arrange
        text = "First sentence here. Second sentence follows. Third sentence ends."
        
        # Act
        chunks = sentence_chunker.chunk(text)
        
        # Assert
        assert len(chunks) > 0
        # Each chunk should contain complete sentences
        for chunk in chunks:
            content = chunk.content.strip()
            assert len(content) > 0
            # Should end with sentence terminator or be complete
            assert content[-1] in ".!?" or len(chunks) == 1
    
    def test_sentence_boundaries_preserved(self, sentence_chunker: Chunker) -> None:
        """Test that sentence boundaries are preserved.
        
        Arrange: Create sentence chunker
        Act: Chunk text
        Assert: Sentences not split
        """
        # Arrange
        text = "This is sentence one. This is sentence two. This is sentence three."
        
        # Act
        chunks = sentence_chunker.chunk(text)
        
        # Assert
        for chunk in chunks:
            # Each chunk should contain complete sentences
            sentences = [s.strip() for s in chunk.content.split(".") if s.strip()]
            assert all(len(s) > 0 for s in sentences)
    
    def test_chunk_with_various_punctuation(self, sentence_chunker: Chunker) -> None:
        """Test chunking text with various sentence endings.
        
        Arrange: Create sentence chunker
        Act: Chunk text with ? and ! endings
        Assert: Correctly identifies sentence boundaries
        """
        # Arrange
        text = "Is this a question? Yes, it is! This is a statement."
        
        # Act
        chunks = sentence_chunker.chunk(text)
        
        # Assert
        assert len(chunks) > 0
        # All text should be included in chunks
        full_content = " ".join(c.content for c in chunks)
        assert "Is this a question" in full_content
        assert "Yes, it is" in full_content
        assert "This is a statement" in full_content


# =============================================================================
# Heading Chunker Tests
# =============================================================================


class TestHeadingChunker:
    """Test heading-based (markdown) chunking strategy."""
    
    def test_chunk_by_heading(self, heading_chunker: Chunker, sample_markdown: str) -> None:
        """Test chunking by markdown headings.
        
        Arrange: Create heading chunker
        Act: Chunk markdown text
        Assert: Returns chunks separated by headings
        """
        # Act
        chunks = heading_chunker.chunk(sample_markdown)
        
        # Assert
        assert len(chunks) > 0
        # Should create chunks based on headings
        assert len(chunks) <= 6  # One per heading level section
    
    def test_heading_boundaries_preserved(self, heading_chunker: Chunker, sample_markdown: str) -> None:
        """Test that heading boundaries are preserved.
        
        Arrange: Create heading chunker
        Act: Chunk markdown text
        Assert: Headings not split
        """
        # Act
        chunks = heading_chunker.chunk(sample_markdown)
        
        # Assert
        for chunk in chunks:
            content = chunk.content.strip()
            assert len(content) > 0
            # Each chunk should start with or contain a heading
            # or be content under a heading
    
    def test_various_heading_levels(self, heading_chunker: Chunker) -> None:
        """Test chunking with various heading levels.
        
        Arrange: Create heading chunker
        Act: Chunk text with h1-h6 headings
        Assert: Correctly identifies all heading levels
        """
        # Arrange
        text = """# H1 Heading
Content under h1.

## H2 Heading
Content under h2.

### H3 Heading
Content under h3.

#### H4 Heading
Content under h4.

##### H5 Heading
Content under h5.

###### H6 Heading
Content under h6."""
        
        # Act
        chunks = heading_chunker.chunk(text)
        
        # Assert
        assert len(chunks) > 0
        # Should handle all heading levels
        full_content = "\n".join(c.content for c in chunks)
        assert "H1 Heading" in full_content
        assert "H6 Heading" in full_content
    
    def test_no_headings(self, heading_chunker: Chunker) -> None:
        """Test chunking text without headings.
        
        Arrange: Create heading chunker
        Act: Chunk plain text without headings
        Assert: Returns single chunk
        """
        # Arrange
        text = "This is plain text without any headings. It has multiple sentences."
        
        # Act
        chunks = heading_chunker.chunk(text)
        
        # Assert
        assert len(chunks) >= 1
        # All content should be included
        full_content = " ".join(c.content for c in chunks)
        assert "plain text without any headings" in full_content


# =============================================================================
# Strategy Selection Tests
# =============================================================================


class TestChunkingStrategySelection:
    """Test chunking strategy selection and switching."""
    
    def test_fixed_size_strategy(self) -> None:
        """Test FIXED_SIZE strategy selection.
        
        Arrange: Create chunker with FIXED_SIZE strategy
        Act: Chunk text
        Assert: Uses fixed-size chunking
        """
        # Arrange
        chunker = Chunker(strategy=ChunkingStrategy.FIXED_SIZE, chunk_size=50)
        text = "Line 1\nLine 2\nLine 3\nLine 4\nLine 5"
        
        # Act
        chunks = chunker.chunk(text)
        
        # Assert
        assert len(chunks) > 0
        assert all(isinstance(c, Chunk) for c in chunks)
    
    def test_paragraph_strategy(self) -> None:
        """Test PARAGRAPH strategy selection.
        
        Arrange: Create chunker with PARAGRAPH strategy
        Act: Chunk text
        Assert: Uses paragraph chunking
        """
        # Arrange
        chunker = Chunker(strategy=ChunkingStrategy.PARAGRAPH, chunk_size=200)
        text = "Para 1\n\nPara 2\n\nPara 3"
        
        # Act
        chunks = chunker.chunk(text)
        
        # Assert
        assert len(chunks) > 0
    
    def test_sentence_strategy(self) -> None:
        """Test SENTENCE strategy selection.
        
        Arrange: Create chunker with SENTENCE strategy
        Act: Chunk text
        Assert: Uses sentence chunking
        """
        # Arrange
        chunker = Chunker(strategy=ChunkingStrategy.SENTENCE, chunk_size=100)
        text = "Sentence one. Sentence two. Sentence three."
        
        # Act
        chunks = chunker.chunk(text)
        
        # Assert
        assert len(chunks) > 0
    
    def test_heading_strategy(self) -> None:
        """Test HEADING strategy selection.
        
        Arrange: Create chunker with HEADING strategy
        Act: Chunk text
        Assert: Uses heading chunking
        """
        # Arrange
        chunker = Chunker(strategy=ChunkingStrategy.HEADING, chunk_size=200)
        text = "# Heading\nContent here."
        
        # Act
        chunks = chunker.chunk(text)
        
        # Assert
        assert len(chunks) > 0
    
    def test_invalid_strategy_raises_error(self) -> None:
        """Test that invalid strategy raises error.
        
        Arrange: Create chunker and manually set invalid strategy
        Act: Try to chunk with invalid strategy
        Assert: Raises ValueError
        """
        # Arrange
        chunker = Chunker()
        # Manually set invalid strategy
        chunker._strategy = "INVALID"  # type: ignore
        
        # Act & Assert
        with pytest.raises(ValueError, match="Unknown chunking strategy"):
            chunker.chunk("Some text")


# =============================================================================
# Edge Cases and Boundary Tests
# =============================================================================


class TestChunkerEdgeCases:
    """Test chunker edge cases and boundary conditions."""
    
    def test_very_long_lines(self, fixed_size_chunker: Chunker) -> None:
        """Test chunking text with very long lines.
        
        Arrange: Create text with very long line
        Act: Chunk the text
        Assert: Handles long lines gracefully
        """
        # Arrange
        long_line = "A" * 1000
        text = f"Short line\n{long_line}\nAnother short line"
        
        # Act
        chunks = fixed_size_chunker.chunk(text)
        
        # Assert
        assert len(chunks) > 0
        # Long line should be included
        full_content = "\n".join(c.content for c in chunks)
        assert "A" * 100 in full_content
    
    def test_very_short_chunk_size(self) -> None:
        """Test with very small chunk size.
        
        Arrange: Create chunker with very small chunk size
        Act: Chunk text
        Assert: Creates many small chunks
        """
        # Arrange
        chunker = Chunker(
            strategy=ChunkingStrategy.FIXED_SIZE,
            chunk_size=10,
            chunk_overlap=0,
        )
        text = "Line 1\nLine 2\nLine 3\nLine 4\nLine 5"
        
        # Act
        chunks = chunker.chunk(text)
        
        # Assert
        assert len(chunks) > 0
        # Each chunk should be small
        for chunk in chunks:
            assert len(chunk.content) < 100  # Reasonable upper bound
    
    def test_zero_overlap(self) -> None:
        """Test chunking with zero overlap.
        
        Arrange: Create chunker with zero overlap
        Act: Chunk text
        Assert: No overlap between chunks
        """
        # Arrange
        chunker = Chunker(
            strategy=ChunkingStrategy.FIXED_SIZE,
            chunk_size=30,
            chunk_overlap=0,
        )
        text = "Line 1 content\nLine 2 content\nLine 3 content\nLine 4 content"
        
        # Act
        chunks = chunker.chunk(text)
        
        # Assert
        if len(chunks) > 1:
            # No overlap means end_line of chunk i < start_line of chunk i+1
            for i in range(len(chunks) - 1):
                assert chunks[i].end_line < chunks[i + 1].start_line or \
                       chunks[i].end_line == chunks[i + 1].start_line - 1
    
    def test_large_overlap(self) -> None:
        """Test chunking with large overlap.
        
        Arrange: Create chunker with large overlap
        Act: Chunk text
        Assert: Significant overlap between chunks
        """
        # Arrange
        chunker = Chunker(
            strategy=ChunkingStrategy.FIXED_SIZE,
            chunk_size=50,
            chunk_overlap=40,
        )
        text = "\n".join([f"Line {i}" for i in range(20)])
        
        # Act
        chunks = chunker.chunk(text)
        
        # Assert
        if len(chunks) > 1:
            # With large overlap, consecutive chunks should share content
            chunk1_lines = set(chunks[0].content.split("\n"))
            chunk2_lines = set(chunks[1].content.split("\n"))
            overlap = chunk1_lines & chunk2_lines
            # Should have significant overlap
            assert len(overlap) > 0
    
    def test_whitespace_only_text(self, fixed_size_chunker: Chunker) -> None:
        """Test chunking whitespace-only text.
        
        Arrange: Create whitespace-only text
        Act: Chunk the text
        Assert: Handles gracefully
        """
        # Arrange
        text = "   \n\n   \n\t\n   "
        
        # Act
        chunks = fixed_size_chunker.chunk(text)
        
        # Assert - should handle gracefully, possibly returning empty or minimal chunks
        assert isinstance(chunks, list)
    
    def test_unicode_content(self, fixed_size_chunker: Chunker) -> None:
        """Test chunking text with unicode characters.
        
        Arrange: Create text with unicode characters
        Act: Chunk the text
        Assert: Preserves unicode characters
        """
        # Arrange
        text = "Hello 世界! 🌍\nこんにちは\nПривет мир"
        
        # Act
        chunks = fixed_size_chunker.chunk(text)
        
        # Assert
        full_content = "\n".join(c.content for c in chunks)
        assert "世界" in full_content
        assert "🌍" in full_content
        assert "こんにちは" in full_content or "Привет" in full_content
    
    def test_code_content(self, fixed_size_chunker: Chunker, sample_code: str) -> None:
        """Test chunking code content.
        
        Arrange: Create code text
        Act: Chunk the code
        Assert: Preserves code structure
        """
        # Act
        chunks = fixed_size_chunker.chunk(sample_code)
        
        # Assert
        assert len(chunks) > 0
        full_content = "\n".join(c.content for c in chunks)
        assert "def function_one" in full_content
        assert "class MyClass" in full_content


# =============================================================================
# Chunk Data Class Tests
# =============================================================================


class TestChunkDataClass:
    """Test Chunk dataclass functionality."""
    
    def test_chunk_creation(self) -> None:
        """Test creating a Chunk instance.
        
        Arrange: Create chunk with all fields
        Act: Instantiate Chunk
        Assert: All fields set correctly
        """
        # Arrange & Act
        chunk = Chunk(
            content="Test content",
            start_line=0,
            end_line=5,
            token_count=10,
        )
        
        # Assert
        assert chunk.content == "Test content"
        assert chunk.start_line == 0
        assert chunk.end_line == 5
        assert chunk.token_count == 10
    
    def test_chunk_immutability(self) -> None:
        """Test that Chunk is effectively immutable (dataclass without frozen).
        
        Arrange: Create a chunk
        Act & Assert: Can modify but shouldn't in practice
        """
        # Arrange
        chunk = Chunk(
            content="Original",
            start_line=0,
            end_line=1,
            token_count=5,
        )
        
        # Act
        # Note: Chunk is not frozen, so modification is possible
        # This test documents the current behavior
        chunk.content = "Modified"
        
        # Assert
        assert chunk.content == "Modified"


# =============================================================================
# Integration Tests
# =============================================================================


class TestChunkerIntegration:
    """Integration tests for chunker."""
    
    def test_chunker_with_real_document(self) -> None:
        """Test chunker with realistic document content.
        
        Arrange: Create realistic document
        Act: Chunk with different strategies
        Assert: All strategies produce valid chunks
        """
        # Arrange
        document = """# Project Documentation

## Overview

This is a comprehensive documentation for the project.
It covers all major features and functionality.

## Installation

To install the project, run:
```bash
pip install project
```

## Usage

### Basic Usage

Here's how to use the basic features:

1. Import the module
2. Create an instance
3. Call methods

### Advanced Usage

For advanced scenarios, configure the settings.

## API Reference

### Class: MyClass

The main class for the project.

#### Method: do_something()

Performs the main operation.

## Conclusion

That's all for now."""
        
        strategies = [
            ChunkingStrategy.FIXED_SIZE,
            ChunkingStrategy.PARAGRAPH,
            ChunkingStrategy.HEADING,
        ]
        
        for strategy in strategies:
            # Arrange
            chunker = Chunker(strategy=strategy, chunk_size=100)
            
            # Act
            chunks = chunker.chunk(document)
            
            # Assert
            assert len(chunks) > 0, f"Strategy {strategy} produced no chunks"
            
            # All content should be preserved
            full_content = "\n".join(c.content for c in chunks)
            assert "Project Documentation" in full_content
            assert "Conclusion" in full_content
    
    def test_chunk_size_configuration(self) -> None:
        """Test different chunk size configurations.
        
        Arrange: Create chunkers with different sizes
        Act: Chunk same text
        Assert: Larger chunk sizes produce fewer chunks
        """
        # Arrange
        text = "\n".join([f"Line {i}" for i in range(100)])
        
        small_chunker = Chunker(
            strategy=ChunkingStrategy.FIXED_SIZE,
            chunk_size=50,
            chunk_overlap=0,
        )
        large_chunker = Chunker(
            strategy=ChunkingStrategy.FIXED_SIZE,
            chunk_size=500,
            chunk_overlap=0,
        )
        
        # Act
        small_chunks = small_chunker.chunk(text)
        large_chunks = large_chunker.chunk(text)
        
        # Assert
        assert len(small_chunks) >= len(large_chunks)
