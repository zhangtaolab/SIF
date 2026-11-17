"""Tests for the QUAL-03 embed-text-only breadcrumb builder.

The builder is pure: it derives one embedding input per chunk from the
document title and the ordered chunk sequence, and never mutates the chunk
objects it reads.
"""

from __future__ import annotations

from sif.core.models import DocumentChunk
from sif.indexing.breadcrumb import HEADING_PATTERN, breadcrumb_embed_texts


def _chunks(*contents: str) -> list[DocumentChunk]:
    """Build sequentially numbered chunks from raw content strings."""
    return [
        DocumentChunk(content=content, sequence=index, start_pos=0, end_pos=len(content))
        for index, content in enumerate(contents)
    ]


def test_h1_first_document_prepends_title_and_heading() -> None:
    """An H1-first document gets ``title > heading`` before the content."""
    chunks = _chunks("# Intro\n\nbody")
    assert breadcrumb_embed_texts("Doc", chunks) == ["Doc > Intro\n\n# Intro\n\nbody"]


def test_h2_first_document_uses_the_heading_of_any_level() -> None:
    """Heading depth is irrelevant: the most recent heading seeds the path."""
    chunks = _chunks("## Deep Start\n\nbody")
    assert breadcrumb_embed_texts("Doc", chunks) == ["Doc > Deep Start\n\n## Deep Start\n\nbody"]


def test_each_section_heading_supersedes_the_previous_one() -> None:
    """An H1-per-section document updates the path as the sequence advances."""
    chunks = _chunks("# One\n\nfirst", "# Two\n\nsecond")
    assert breadcrumb_embed_texts("Doc", chunks) == [
        "Doc > One\n\n# One\n\nfirst",
        "Doc > Two\n\n# Two\n\nsecond",
    ]


def test_document_without_headings_gets_the_title_only_path() -> None:
    """No heading anywhere yields a title-only path, not a bare heading slot."""
    chunks = _chunks("plain text", "more text")
    assert breadcrumb_embed_texts("Doc", chunks) == [
        "Doc\n\nplain text",
        "Doc\n\nmore text",
    ]


def test_cjk_heading_is_matched_by_the_hash_run() -> None:
    """CJK labels match through the ``#`` run, not word characters."""
    chunks = _chunks("### 方法\n\n正文")
    assert breadcrumb_embed_texts("文档", chunks) == ["文档 > 方法\n\n### 方法\n\n正文"]


def test_empty_title_yields_content_only() -> None:
    """A blank title contributes no path, so heading-free content is unchanged."""
    chunks = _chunks("plain text")
    assert breadcrumb_embed_texts("", chunks) == ["plain text"]
    assert breadcrumb_embed_texts("   ", chunks) == ["plain text"]


def test_title_equal_to_the_heading_is_deduplicated_once() -> None:
    """A heading equal to the title is not repeated in the path."""
    chunks = _chunks("# Doc\n\nbody")
    assert breadcrumb_embed_texts("Doc", chunks) == ["Doc\n\n# Doc\n\nbody"]


def test_heading_is_compared_after_stripping_both_sides() -> None:
    """Whitespace around the title or heading does not defeat deduplication."""
    chunks = _chunks("#   Doc  \n\nbody")
    assert breadcrumb_embed_texts("  Doc  ", chunks) == ["Doc\n\n#   Doc  \n\nbody"]


def test_sub_chunk_without_a_heading_inherits_the_prior_section_heading() -> None:
    """A headingless continuation chunk keeps the section's last heading."""
    chunks = _chunks("# Section\n\nlead", "continuation without a heading")
    assert breadcrumb_embed_texts("Doc", chunks) == [
        "Doc > Section\n\n# Section\n\nlead",
        "Doc > Section\n\ncontinuation without a heading",
    ]


def test_separator_is_configurable() -> None:
    """The path joiner defaults to ``" > "`` and can be overridden."""
    chunks = _chunks("## Part\n\nbody")
    assert breadcrumb_embed_texts("Doc", chunks, separator=" / ") == [
        "Doc / Part\n\n## Part\n\nbody"
    ]
    assert breadcrumb_embed_texts("Doc", chunks)[0].startswith("Doc > Part")


def test_output_is_parallel_and_inputs_are_not_mutated() -> None:
    """Exactly one string per chunk, and the chunk objects are untouched."""
    chunks = _chunks("# One\n\nfirst", "middle", "# Two\n\nlast")
    before = [(chunk.content, chunk.sequence, chunk.start_pos, chunk.end_pos) for chunk in chunks]
    texts = breadcrumb_embed_texts("Doc", chunks)
    after = [(chunk.content, chunk.sequence, chunk.start_pos, chunk.end_pos) for chunk in chunks]
    assert len(texts) == len(chunks) == 3
    assert before == after


def test_context_lines_before_the_heading_skip_to_the_first_non_empty_line() -> None:
    """Leading blank lines do not hide the heading on the first content line."""
    chunks = _chunks("\n\n   \n# Heading\n\nbody")
    assert breadcrumb_embed_texts("Doc", chunks) == ["Doc > Heading\n\n\n\n   \n# Heading\n\nbody"]


def test_non_heading_hash_lines_do_not_seed_a_section() -> None:
    """Seven hashes, a hashtag, and an empty heading label are not headings."""
    assert HEADING_PATTERN.match("####### seven") is None
    assert HEADING_PATTERN.match("#tag") is None
    assert HEADING_PATTERN.match("#   ") is None
    chunks = _chunks("#tag line", "####### seven")
    assert breadcrumb_embed_texts("Doc", chunks) == [
        "Doc\n\n#tag line",
        "Doc\n\n####### seven",
    ]
