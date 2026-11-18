"""Content and boundary tests for every document chunking strategy."""

from __future__ import annotations

import pytest

from sif.core.models import DocumentChunk
from sif.indexing.chunker import (
    AutoChunker,
    CodeChunker,
    FixedSizeChunker,
    MarkdownChunker,
    create_chunker,
    token_size_to_chars,
)


def _chunk_fields(chunks: list[DocumentChunk]) -> list[tuple[str, int, int, int]]:
    """Return observable chunk fields without comparing generated identities."""
    return [(chunk.content, chunk.sequence, chunk.start_pos, chunk.end_pos) for chunk in chunks]


class TestChunkerStrategies:
    """Positions are Python string/code-point offsets, not bytes or graphemes."""

    def test_fixed_size_exact_fit_preserves_whole_content_and_boundaries(self) -> None:
        """Input exactly the configured size produces one unsplit chunk."""
        text = "1234567890"

        chunks = FixedSizeChunker(chunk_size=10, overlap=2).chunk(text)

        assert len(chunks) == 1
        assert chunks[0].content == text
        assert chunks[0].sequence == 0
        assert (chunks[0].start_pos, chunks[0].end_pos) == (0, 10)

    @pytest.mark.parametrize(
        ("text", "expected_contents", "expected_bounds"),
        [
            (
                "12345\nabcdef",
                ["12345", "5\nabc", "bcdef"],
                [(0, 6), (4, 9), (7, 12)],
            ),
            (
                "12345 abcdef",
                ["12345", "5 abc", "bcdef"],
                [(0, 6), (4, 9), (7, 12)],
            ),
            (
                "abcdefghijK",
                ["abcde", "defgh", "ghijK"],
                [(0, 5), (3, 8), (6, 11)],
            ),
        ],
    )
    def test_fixed_size_break_search_remainder_and_overlap(
        self,
        text: str,
        expected_contents: list[str],
        expected_bounds: list[tuple[int, int]],
    ) -> None:
        """Newline, space, and hard boundaries advance with exact overlaps."""
        chunks = FixedSizeChunker(chunk_size=5, overlap=2).chunk(text)

        assert [chunk.content for chunk in chunks] == expected_contents
        assert [(chunk.start_pos, chunk.end_pos) for chunk in chunks] == expected_bounds
        assert [chunk.sequence for chunk in chunks] == list(range(len(chunks)))

    def test_fixed_size_overlap_larger_than_size_still_moves_forward(self) -> None:
        """The progress guard forces advancement when overlap exceeds chunk size."""
        chunks = FixedSizeChunker(chunk_size=3, overlap=100).chunk("abcdefgh")

        assert [chunk.content for chunk in chunks] == [
            "abc",
            "bcd",
            "cde",
            "def",
            "efg",
            "fgh",
        ]
        assert [(chunk.start_pos, chunk.end_pos) for chunk in chunks] == [
            (0, 3),
            (1, 4),
            (2, 5),
            (3, 6),
            (4, 7),
            (5, 8),
        ]
        assert [chunk.sequence for chunk in chunks] == list(range(6))

    @pytest.mark.parametrize("text", ["", "  \n\t  "])
    def test_fixed_size_empty_and_whitespace_content_produce_no_chunks(self, text: str) -> None:
        """Empty and stripped-whitespace content produce no chunks."""
        assert FixedSizeChunker(chunk_size=4, overlap=1).chunk(text) == []

    def test_fixed_size_unicode_positions_count_code_points_not_utf8_bytes(self) -> None:
        """CJK code points each occupy one position despite multibyte UTF-8."""
        text = "你好世界"

        chunks = FixedSizeChunker(chunk_size=2, overlap=0).chunk(text)

        assert [chunk.content for chunk in chunks] == ["你好", "世界"]
        assert [(chunk.start_pos, chunk.end_pos) for chunk in chunks] == [(0, 2), (2, 4)]
        assert len(text.encode("utf-8")) == 12

    def test_markdown_without_headings_delegates_to_fixed_size(self) -> None:
        """Heading-free Markdown uses the same fixed-size content and offsets."""
        text = "123456"

        assert _chunk_fields(MarkdownChunker(max_chunk_size=3).chunk(text)) == _chunk_fields(
            FixedSizeChunker(3).chunk(text)
        )

    def test_markdown_splits_on_heading_boundaries(self) -> None:
        """Each heading begins a chunk ending at the following heading or EOF."""
        text = "preamble\n# First\nalpha\n## Second\nbeta\n"

        chunks = MarkdownChunker(max_chunk_size=100).chunk(text)

        assert [chunk.content for chunk in chunks] == ["# First\nalpha", "## Second\nbeta"]
        assert [(chunk.start_pos, chunk.end_pos) for chunk in chunks] == [(9, 23), (23, 38)]
        assert [chunk.sequence for chunk in chunks] == [0, 1]

    def test_markdown_oversized_sections_are_subdivided_and_resequenced(self) -> None:
        """Fixed-size subchunks receive a single sequence across all sections."""
        text = "# Large\nabcdefghij\n## Small\nend"

        chunks = MarkdownChunker(max_chunk_size=10).chunk(text)

        assert [chunk.content for chunk in chunks] == [
            "# Large\nab",
            "cdefghij",
            "## Small\ne",
            "nd",
        ]
        assert [chunk.sequence for chunk in chunks] == [0, 1, 2, 3]
        assert [(chunk.start_pos, chunk.end_pos) for chunk in chunks] == [
            (0, 10),
            (10, 20),
            (0, 10),
            (10, 20),
        ]

    def test_code_splits_python_function_and_class_boundaries(self) -> None:
        """Top-level def and class lines delimit real Python source sections."""
        text = "import os\n\ndef first():\n    return 1\n\nclass Second:\n    pass\n"

        chunks = CodeChunker(max_chunk_size=100).chunk(text)

        assert [chunk.content for chunk in chunks] == [
            "def first():\n    return 1",
            "class Second:\n    pass",
        ]
        assert [(chunk.start_pos, chunk.end_pos) for chunk in chunks] == [(11, 38), (38, 61)]
        assert [chunk.sequence for chunk in chunks] == [0, 1]

    def test_code_without_python_matches_uses_fixed_size(self) -> None:
        """Python source without a top-level definition delegates to fixed size."""
        text = "print('abcdef')"

        assert _chunk_fields(CodeChunker(max_chunk_size=5).chunk(text)) == _chunk_fields(
            FixedSizeChunker(5).chunk(text)
        )

    def test_code_oversized_definition_is_subdivided_and_resequenced(self) -> None:
        """Oversized Python and subsequent definitions share one chunk sequence."""
        text = "def large():\n    return 'abcdefghij'\nclass Small:\n    pass"

        chunks = CodeChunker(max_chunk_size=15).chunk(text)

        assert [chunk.sequence for chunk in chunks] == list(range(len(chunks)))
        assert len(chunks) > 2
        assert chunks[-1].content == "pass"
        assert chunks[0].start_pos == 0
        assert chunks[0].end_pos == 24
        assert chunks[-1].end_pos == 32

    def test_non_python_code_delegates_to_fixed_size(self) -> None:
        """Other languages never use Python definition regular expressions."""
        text = "function first() { return 123456; }"

        assert _chunk_fields(
            CodeChunker(max_chunk_size=10, language="javascript").chunk(text)
        ) == _chunk_fields(FixedSizeChunker(10).chunk(text))

    @pytest.mark.parametrize(
        ("text", "expected_contents"),
        [
            ("# Heading\nbody", ["# Heading\nbody"]),
            ("def function():\n    return 1", ["def function():\n    return 1"]),
            ("plain text", ["plain text"]),
        ],
    )
    def test_auto_routes_markdown_code_and_fixed_content(
        self, text: str, expected_contents: list[str]
    ) -> None:
        """AutoChunker routes content to the appropriate concrete strategy."""
        chunks = AutoChunker(max_chunk_size=100).chunk(text)

        assert [chunk.content for chunk in chunks] == expected_contents
        assert [chunk.sequence for chunk in chunks] == [0]

    @pytest.mark.parametrize(
        ("strategy", "kwargs", "expected_type", "attribute", "expected_value"),
        [
            ("fixed", {"chunk_size": 12, "overlap": 3}, FixedSizeChunker, "chunk_size", 12),
            ("markdown", {"max_chunk_size": 20}, MarkdownChunker, "max_chunk_size", 20),
            (
                "code",
                {"max_chunk_size": 30, "language": "rust"},
                CodeChunker,
                "language",
                "rust",
            ),
            ("auto", {"max_chunk_size": 40}, AutoChunker, "max_chunk_size", 40),
        ],
    )
    def test_factory_forwards_each_strategy_kwargs(
        self,
        strategy: str,
        kwargs: dict[str, int | str],
        expected_type: type,
        attribute: str,
        expected_value: int | str,
    ) -> None:
        """Every create_chunker branch returns and configures its own strategy."""
        chunker = create_chunker(strategy, **kwargs)

        assert isinstance(chunker, expected_type)
        assert getattr(chunker, attribute) == expected_value

    def test_factory_rejects_unknown_strategy(self) -> None:
        """Unknown strategy names fail with an explanatory ValueError."""
        with pytest.raises(ValueError, match="Unknown chunking strategy: semantic"):
            create_chunker("semantic")


def test_create_chunker_forwards_overlap_to_every_strategy() -> None:
    """SIF_CHUNK_OVERLAP reaches fixed, markdown, code, and auto chunkers."""
    assert create_chunker("fixed", chunk_size=12, overlap=3).overlap == 3
    assert create_chunker("markdown", max_chunk_size=20, overlap=4).overlap == 4
    assert create_chunker("code", max_chunk_size=20, overlap=5).overlap == 5
    assert create_chunker("auto", max_chunk_size=20, overlap=6).overlap == 6


def test_token_size_to_chars_converts_token_budget() -> None:
    """The settings' token budgets convert to character budgets at 4 chars/token."""
    assert token_size_to_chars(512) == 2048
    assert token_size_to_chars(0) == 1
