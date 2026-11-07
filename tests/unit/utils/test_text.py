"""Behavior tests for the surviving text helper functions."""

from unittest.mock import MagicMock

from sif.utils.text import count_tokens, extract_code_blocks


class TestTextHelpers:
    """Text helpers document current code-point and regex-text semantics."""

    def test_count_tokens_uses_working_tokenizer(self) -> None:
        """A tokenizer's encoded sequence determines the count when available."""
        tokenizer = MagicMock()
        tokenizer.encode.return_value = [1, 2, 3]

        assert count_tokens("text", tokenizer) == 3
        tokenizer.encode.assert_called_once_with("text")

    def test_count_tokens_tokenizer_exception_uses_estimate(self) -> None:
        """Tokenizer failures fall back to the code-point-length estimate."""
        tokenizer = MagicMock()
        tokenizer.encode.side_effect = RuntimeError("broken tokenizer")

        assert count_tokens("123456789", tokenizer) == 2

    def test_count_tokens_empty_and_short_strings(self) -> None:
        """Empty input returns zero; short nonempty input follows integer division."""
        assert count_tokens("") == 0
        assert count_tokens("abc") == 0
        assert count_tokens("abcd") == 1

    def test_count_tokens_unicode_uses_python_code_points(self) -> None:
        """Unicode fallback counts Python code points, not graphemes or normalized forms."""
        assert len("你好世界") == 4
        assert count_tokens("你好世界") == 1
        assert count_tokens("é") == 0

    def test_extract_code_blocks_language_and_content(self) -> None:
        """Language-tagged fenced blocks return stripped code and their language."""
        text = "Before\n```python\n  print('hello')  \n```\nAfter"

        assert extract_code_blocks(text) == [("python", "print('hello')")]

    def test_extract_code_blocks_without_language_defaults_to_text(self) -> None:
        """An untagged fence uses the text language label."""
        assert extract_code_blocks("```\nplain text\n```") == [("text", "plain text")]

    def test_extract_code_blocks_multiple_and_multiline(self) -> None:
        """Multiple blocks preserve source order and multiline contents."""
        text = """```python
one = 1
two = 2
```
prose
```json
{
  "key": "value"
}
```"""

        assert extract_code_blocks(text) == [
            ("python", "one = 1\ntwo = 2"),
            ("json", '{\n  "key": "value"\n}'),
        ]

    def test_extract_code_blocks_empty_input_and_empty_block(self) -> None:
        """Empty text has no blocks; an empty fenced block has empty content."""
        assert extract_code_blocks("") == []
        assert extract_code_blocks("```text\n\n```") == [("text", "")]

    def test_extract_code_blocks_ignores_unclosed_block(self) -> None:
        """Regex text semantics do not treat an unclosed fence as a complete block."""
        assert extract_code_blocks("```python\nprint('unfinished')") == []
