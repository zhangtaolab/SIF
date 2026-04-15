"""Tests for CLI formatters."""

from docsift.cli.formatters import (
    add_line_numbers_to_results,
    prepend_line_numbers,
)


class TestPrependLineNumbers:
    """Tests for prepend_line_numbers helper."""

    def test_prepend_line_numbers(self):
        """Test that line numbers are prepended correctly."""
        result = prepend_line_numbers("a\nb\nc")
        lines = result.split("\n")
        assert lines[0] == "   1: a"
        assert lines[1] == "   2: b"
        assert lines[2] == "   3: c"


class TestAddLineNumbersToResults:
    """Tests for add_line_numbers_to_results helper."""

    def test_add_line_numbers_to_results(self):
        """Test that line_numbers field is added based on content."""
        data = [{"content": "x\ny"}]
        result = add_line_numbers_to_results(data)
        assert result[0]["line_numbers"] == "1\n2"

    def test_add_line_numbers_to_results_empty_content(self):
        """Test that empty content produces empty line_numbers."""
        data = [{"content": ""}]
        result = add_line_numbers_to_results(data)
        assert result[0]["line_numbers"] == ""
