"""Tests for markdown document parser."""

from datetime import datetime
from pathlib import Path

import pytest

from docsift.indexing.parser import MarkdownParser, ParseResult
from docsift.core.document import DocumentMetadata


class TestParseResult:
    """Tests for ParseResult dataclass."""
    
    def test_parse_result_creation(self):
        """Test creating a ParseResult."""
        # Arrange & Act
        result = ParseResult(
            content="Test content",
            metadata=DocumentMetadata(),
            title="Test Title",
            frontmatter_raw={},
        )
        
        # Assert
        assert result.content == "Test content"
        assert result.title == "Test Title"


class TestMarkdownParserInit:
    """Tests for MarkdownParser initialization."""
    
    def test_parser_init(self):
        """Test parser initialization."""
        # Act
        parser = MarkdownParser()
        
        # Assert
        assert parser is not None


class TestMarkdownParserParse:
    """Tests for parsing markdown files."""
    
    def test_parse_existing_file(self, sample_markdown_file: Path):
        """Test parsing an existing markdown file."""
        # Arrange
        parser = MarkdownParser()
        
        # Act
        result = parser.parse(sample_markdown_file)
        
        # Assert
        assert isinstance(result, ParseResult)
        assert "Introduction" in result.content
        assert result.title == "Test Document"
    
    def test_parse_nonexistent_file_raises_error(self, temp_dir: Path):
        """Test that parsing nonexistent file raises FileNotFoundError."""
        # Arrange
        parser = MarkdownParser()
        nonexistent = temp_dir / "nonexistent.md"
        
        # Act & Assert
        with pytest.raises(FileNotFoundError):
            parser.parse(nonexistent)
    
    def test_parse_extracts_frontmatter(self, sample_markdown_file: Path):
        """Test that parse extracts frontmatter metadata."""
        # Arrange
        parser = MarkdownParser()
        
        # Act
        result = parser.parse(sample_markdown_file)
        
        # Assert
        assert result.metadata.title == "Test Document"
        assert result.metadata.author == "Test Author"
        assert result.metadata.tags == ["test", "sample"]
        assert result.metadata.categories == ["documentation"]
    
    def test_parse_extracts_date(self, sample_markdown_file: Path):
        """Test that parse extracts date from frontmatter."""
        # Arrange
        parser = MarkdownParser()
        
        # Act
        result = parser.parse(sample_markdown_file)
        
        # Assert
        assert result.metadata.date is not None
        assert result.metadata.date.year == 2024
        assert result.metadata.date.month == 1
        assert result.metadata.date.day == 15
    
    def test_parse_normalizes_content(self, sample_markdown_file: Path):
        """Test that parse normalizes content."""
        # Arrange
        parser = MarkdownParser()
        
        # Act
        result = parser.parse(sample_markdown_file)
        
        # Assert
        # Content should be normalized (no excessive whitespace)
        assert not result.content.startswith(" ")
        assert not result.content.endswith(" ")
    
    def test_parse_extracts_title_from_frontmatter(self, sample_markdown_file: Path):
        """Test that parse extracts title from frontmatter."""
        # Arrange
        parser = MarkdownParser()
        
        # Act
        result = parser.parse(sample_markdown_file)
        
        # Assert
        assert result.title == "Test Document"
        assert result.metadata.title == "Test Document"


class TestMarkdownParserParseString:
    """Tests for parsing markdown content from string."""
    
    def test_parse_string_basic(self):
        """Test parsing basic markdown string."""
        # Arrange
        parser = MarkdownParser()
        content = "# Title\n\nSome content."
        
        # Act
        result = parser.parse_string(content)
        
        # Assert
        assert isinstance(result, ParseResult)
        assert "Title" in result.content
        assert result.title == "Title"
    
    def test_parse_string_with_frontmatter(self):
        """Test parsing markdown string with frontmatter."""
        # Arrange
        parser = MarkdownParser()
        content = """---
title: My Title
author: Test Author
---

# Heading

Content here.
"""
        
        # Act
        result = parser.parse_string(content)
        
        # Assert
        assert result.metadata.title == "My Title"
        assert result.metadata.author == "Test Author"
        assert result.title == "My Title"
    
    def test_parse_string_empty(self):
        """Test parsing empty markdown string."""
        # Arrange
        parser = MarkdownParser()
        
        # Act
        result = parser.parse_string("")
        
        # Assert
        assert isinstance(result, ParseResult)
        assert result.content == ""
    
    def test_parse_string_extracts_title_from_heading(self):
        """Test that parse_string extracts title from H1 heading."""
        # Arrange
        parser = MarkdownParser()
        content = "# My Document Title\n\nContent here."
        
        # Act
        result = parser.parse_string(content)
        
        # Assert
        assert result.title == "My Document Title"


class TestMetadataExtraction:
    """Tests for metadata extraction."""
    
    def test_extract_metadata_with_all_fields(self):
        """Test extracting metadata with all standard fields."""
        # Arrange
        parser = MarkdownParser()
        frontmatter_data = {
            "title": "Test",
            "author": "Author",
            "date": "2024-01-15",
            "tags": ["a", "b"],
            "categories": ["cat1"],
        }
        
        # Act
        metadata = parser._extract_metadata(frontmatter_data)
        
        # Assert
        assert metadata.title == "Test"
        assert metadata.author == "Author"
        assert isinstance(metadata.date, datetime)
        assert metadata.tags == ["a", "b"]
        assert metadata.categories == ["cat1"]
    
    def test_extract_metadata_with_string_tags(self):
        """Test extracting metadata with comma-separated string tags."""
        # Arrange
        parser = MarkdownParser()
        frontmatter_data = {
            "tags": "tag1, tag2, tag3",
        }
        
        # Act
        metadata = parser._extract_metadata(frontmatter_data)
        
        # Assert
        assert metadata.tags == ["tag1", "tag2", "tag3"]
    
    def test_extract_metadata_with_datetime_date(self):
        """Test extracting metadata with datetime date object."""
        # Arrange
        parser = MarkdownParser()
        date_obj = datetime(2024, 1, 15)
        frontmatter_data = {
            "date": date_obj,
        }
        
        # Act
        metadata = parser._extract_metadata(frontmatter_data)
        
        # Assert
        assert metadata.date == date_obj
    
    def test_extract_metadata_stores_custom_fields(self):
        """Test that custom fields are stored in metadata.custom."""
        # Arrange
        parser = MarkdownParser()
        frontmatter_data = {
            "title": "Test",
            "custom_field": "custom_value",
            "another_custom": 123,
        }
        
        # Act
        metadata = parser._extract_metadata(frontmatter_data)
        
        # Assert
        assert metadata.custom["custom_field"] == "custom_value"
        assert metadata.custom["another_custom"] == 123
    
    def test_extract_metadata_empty_frontmatter(self):
        """Test extracting metadata from empty frontmatter."""
        # Arrange
        parser = MarkdownParser()
        
        # Act
        metadata = parser._extract_metadata({})
        
        # Assert
        assert metadata.title is None
        assert metadata.author is None
        assert metadata.date is None
        assert metadata.tags == []
        assert metadata.categories == []


class TestTitleExtraction:
    """Tests for title extraction from content."""
    
    def test_extract_title_from_h1(self):
        """Test extracting title from H1 heading."""
        # Arrange
        parser = MarkdownParser()
        content = "# My Title\n\nSome content."
        
        # Act
        title = parser._extract_title(content)
        
        # Assert
        assert title == "My Title"
    
    def test_extract_title_no_h1_returns_none(self):
        """Test that no H1 heading returns None."""
        # Arrange
        parser = MarkdownParser()
        content = "## H2 Heading\n\nSome content."
        
        # Act
        title = parser._extract_title(content)
        
        # Assert
        assert title is None
    
    def test_extract_title_empty_content(self):
        """Test extracting title from empty content."""
        # Arrange
        parser = MarkdownParser()
        
        # Act
        title = parser._extract_title("")
        
        # Assert
        assert title is None
    
    def test_extract_title_multiple_h1_uses_first(self):
        """Test that first H1 is used when multiple exist."""
        # Arrange
        parser = MarkdownParser()
        content = "# First Title\n\nContent\n\n# Second Title"
        
        # Act
        title = parser._extract_title(content)
        
        # Assert
        assert title == "First Title"


class TestParserEdgeCases:
    """Tests for parser edge cases."""
    
    def test_parse_file_with_only_frontmatter(self, temp_dir: Path):
        """Test parsing file with only frontmatter."""
        # Arrange
        parser = MarkdownParser()
        file_path = temp_dir / "only_frontmatter.md"
        file_path.write_text("---\ntitle: Test\n---\n")
        
        # Act
        result = parser.parse(file_path)
        
        # Assert
        assert result.metadata.title == "Test"
    
    def test_parse_file_with_special_characters(self, temp_dir: Path):
        """Test parsing file with special characters."""
        # Arrange
        parser = MarkdownParser()
        file_path = temp_dir / "special.md"
        file_path.write_text("# Title with émojis 🎉\n\nContent with üñíçödé.")
        
        # Act
        result = parser.parse(file_path)
        
        # Assert
        assert "émojis" in result.content
        assert "üñíçödé" in result.content
    
    def test_parse_invalid_date_format(self):
        """Test parsing frontmatter with invalid date format."""
        # Arrange
        parser = MarkdownParser()
        frontmatter_data = {
            "date": "not-a-valid-date",
        }
        
        # Act
        metadata = parser._extract_metadata(frontmatter_data)
        
        # Assert
        assert metadata.date is None
