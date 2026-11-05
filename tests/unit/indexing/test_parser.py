"""Real-file behavior tests for document parsers and their factory."""

from __future__ import annotations

import hashlib
from pathlib import Path
from unittest.mock import patch

import pytest

from sif.indexing.parser import CodeParser, MarkdownParser, TextParser, create_parser


class TestDocumentParsers:
    """Parser contracts are exercised using only synthetic temporary files."""

    def test_markdown_preserves_unicode_body_metadata_and_file_identity(
        self, tmp_path: Path
    ) -> None:
        """UTF-8 strings keep their exact code points; no normalization is applied."""
        file_path = tmp_path / "知识库.md"
        content = "---\ntitle: 本地知识库\nauthor: 测试\n---\n# 搜索 🔍\n\n你好世界 Café é\n"
        file_path.write_text(content, encoding="utf-8")

        parser = create_parser(file_path)
        assert isinstance(parser, MarkdownParser)
        result = parser.parse(file_path)

        assert result.path == str(file_path.resolve())
        assert result.content == "# 搜索 🔍\n\n你好世界 Café é"
        assert result.title == "本地知识库"
        assert result.metadata == {"title": "本地知识库", "author": "测试"}
        assert result.checksum == hashlib.sha256(content.encode("utf-8")).hexdigest()
        assert result.mtime == file_path.stat().st_mtime

    @pytest.mark.parametrize(
        ("content", "expected_title"),
        [
            ("# Heading wins\nbody", "Heading wins"),
            ("No heading in this document", "fallback"),
            ("", "fallback"),
        ],
    )
    def test_markdown_title_fallbacks_and_empty_content(
        self, tmp_path: Path, content: str, expected_title: str
    ) -> None:
        """Markdown title precedence ends at H1 and then the file stem."""
        file_path = tmp_path / "fallback.md"
        file_path.write_text(content, encoding="utf-8")

        result = MarkdownParser().parse(file_path)

        assert result.title == expected_title
        assert result.metadata == {}
        assert result.content == content

    def test_markdown_malformed_metadata_falls_back_to_original_content(
        self, tmp_path: Path
    ) -> None:
        """A frontmatter decoder failure retains the entire original document."""
        file_path = tmp_path / "broken.md"
        content = "---\nnot valid metadata\n# Visible title\n"
        file_path.write_text(content, encoding="utf-8")

        with patch("sif.indexing.parser.frontmatter.loads", side_effect=ValueError("bad YAML")):
            result = MarkdownParser().parse(file_path)

        assert result.content == content
        assert result.metadata == {}
        assert result.title == "Visible title"

    def test_text_uses_first_suitable_nonempty_line(self, tmp_path: Path) -> None:
        """Text parsing skips blank and overlong title candidates."""
        file_path = tmp_path / "notes.txt"
        content = f"\n  \n{'x' * 100}\n  Suitable title  \nbody\n"
        file_path.write_text(content, encoding="utf-8")

        result = TextParser().parse(file_path)

        assert result.content == content
        assert result.title == "Suitable title"
        assert result.metadata == {}
        assert result.checksum == hashlib.sha256(content.encode()).hexdigest()

    @pytest.mark.parametrize("content", ["", " \n\t\n", "x" * 100])
    def test_text_without_suitable_title_uses_stem(self, tmp_path: Path, content: str) -> None:
        """Empty, whitespace-only, and uniformly overlong input use the stem."""
        file_path = tmp_path / "plain.rst"
        file_path.write_text(content, encoding="utf-8")

        result = TextParser().parse(file_path)

        assert result.content == content
        assert result.title == "plain"

    def test_python_docstring_title_is_truncated_to_one_hundred_characters(
        self, tmp_path: Path
    ) -> None:
        """The first Python module docstring line is the bounded code title."""
        file_path = tmp_path / "module.py"
        content = f'"""{"D" * 120}\nAdditional details."""\nprint("ok")\n'
        file_path.write_text(content, encoding="utf-8")

        result = CodeParser().parse(file_path)

        assert result.title == "D" * 100
        assert result.content == content
        assert result.metadata == {"language": "python"}

    def test_non_python_code_uses_stem_and_lowercase_language_mapping(self, tmp_path: Path) -> None:
        """Uppercase suffixes are normalized for both factory and code metadata."""
        file_path = tmp_path / "program.PY"
        file_path.write_text("print('hello')\n", encoding="utf-8")

        parser = create_parser(file_path)
        assert isinstance(parser, CodeParser)
        result = parser.parse(file_path)

        assert result.title == "program"
        assert result.metadata == {"language": "python"}

    def test_unknown_code_suffix_maps_to_text(self, tmp_path: Path) -> None:
        """Direct CodeParser use retains its current unknown-language fallback."""
        file_path = tmp_path / "extension.unknown"
        file_path.write_text("some source\n", encoding="utf-8")

        result = CodeParser().parse(file_path)

        assert result.title == "extension"
        assert result.metadata == {"language": "text"}

    @pytest.mark.parametrize(
        ("suffix", "parser_type"),
        [
            (".md", MarkdownParser),
            (".markdown", MarkdownParser),
            (".mdx", MarkdownParser),
            (".js", CodeParser),
            (".txt", TextParser),
            (".rst", TextParser),
            (".adoc", TextParser),
        ],
    )
    def test_factory_selects_parser_by_extension(
        self, tmp_path: Path, suffix: str, parser_type: type
    ) -> None:
        """Every factory parser family is selected from a temporary path."""
        assert isinstance(create_parser(tmp_path / f"document{suffix}"), parser_type)

    def test_factory_returns_none_for_unsupported_extension(self, tmp_path: Path) -> None:
        """Unsupported files are not assigned a parser."""
        assert create_parser(tmp_path / "archive.pdf") is None
