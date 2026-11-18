"""Title/heading-path breadcrumbs for chunk embedding text.

QUAL-03 (D-04): the breadcrumb is an embed-text-only overlay. It prepends the
document title and the most recent section heading to each chunk's embedding
input while leaving ``DocumentChunk.content`` untouched, so stored chunks,
chunks FTS, snippets, and BM25 stay byte-identical whether the switch is on or
off.

The path is derived from the ordered chunk sequence plus the document title,
never from ``start_pos``: sub-chunks of an oversized section carry positions
relative to that section, not the document (research Pitfall 3).
"""

from __future__ import annotations

import re
from collections.abc import Sequence

from sif.core.models import DocumentChunk


# A heading line: one to six ``#`` characters, whitespace, then a non-empty
# label. CJK labels are matched by the ``#`` run, not by word characters.
HEADING_PATTERN = re.compile(r"^(#{1,6})\s+(\S.*?)\s*$")


def _first_non_empty_line(content: str) -> str | None:
    """Return the first non-blank line, stripped, or None for blank content."""
    for line in content.splitlines():
        stripped = line.strip()
        if stripped:
            return stripped
    return None


def _heading_label(content: str) -> str | None:
    """Return the heading label when a chunk starts with a heading line."""
    line = _first_non_empty_line(content)
    if line is None:
        return None
    match = HEADING_PATTERN.match(line)
    return match.group(2).strip() if match is not None else None


def breadcrumb_embed_texts(
    title: str, chunks: Sequence[DocumentChunk], separator: str = " > "
) -> list[str]:
    """Build one embedding input per chunk from the title and heading path.

    Walks the chunks in document order. A chunk whose first non-empty line is
    a Markdown heading starts a new section; a chunk without a heading
    inherits the most recent heading. The path joins the stripped document
    title (when non-empty) and the current heading (when present and not
    equal to the title, so an H1 that repeats the title is not duplicated).

    Args:
        title: Document title; blank or whitespace-only contributes no path
            segment.
        chunks: Ordered document chunks; never mutated.
        separator: Joiner between path segments.

    Returns:
        A parallel list with exactly one string per chunk. A chunk with no
        path (blank title and no heading yet) keeps its content unchanged.
    """
    title_text = title.strip()
    texts: list[str] = []
    current_heading: str | None = None
    for chunk in chunks:
        heading = _heading_label(chunk.content)
        if heading is not None:
            current_heading = heading
        parts = [title_text] if title_text else []
        if current_heading is not None and current_heading != title_text:
            parts.append(current_heading)
        path = separator.join(parts)
        texts.append(f"{path}\n\n{chunk.content}" if path else chunk.content)
    return texts


def _share(count: int, total: int) -> float:
    """Return ``count / total`` rounded to six decimals, or 0.0 without input."""
    return 0.0 if total == 0 else round(count / total, 6)


def duplicate_metrics(title: str, chunks: Sequence[DocumentChunk]) -> dict[str, object]:
    """Measure how much of the breadcrumb repeats already-indexed text.

    The measured duplicate risk is real: most baseline documents have an H1
    equal to their title, and nearly half of all chunks are headingless
    sub-chunks. This function reports the shares the verdict needs so a
    title-only gain can be rejected with numbers (research Pitfall 5, D-04).

    The section heading is derived exactly as the builder derives it, so a
    headingless continuation chunk inherits the section's most recent heading.

    Args:
        title: Document title; blank or whitespace-only never counts as a
            title-bearing path.
        chunks: Ordered document chunks; never mutated.

    Returns:
        ``chunks``, ``documents`` (1 when any chunk exists, else 0),
        ``title_share`` (path includes a non-empty title), ``in_content_share``
        (the current heading text already occurs in that chunk's content),
        ``subchunk_share`` (the first non-empty line is not a heading), and
        ``title_equals_heading_share`` (the current heading equals the title).
        Shares are rounded to six decimals; an empty chunk list returns zero
        counts and zero shares, and a single chunk is a valid denominator.
    """
    title_text = title.strip()
    total = len(chunks)
    titled = 0
    in_content = 0
    subchunk = 0
    title_equals_heading = 0
    current_heading: str | None = None
    for chunk in chunks:
        heading = _heading_label(chunk.content)
        if heading is not None:
            current_heading = heading
        else:
            subchunk += 1
        if title_text:
            titled += 1
        if current_heading is not None and current_heading in chunk.content:
            in_content += 1
        if title_text and current_heading == title_text:
            title_equals_heading += 1
    return {
        "chunks": total,
        "documents": 1 if total else 0,
        "title_share": _share(titled, total),
        "in_content_share": _share(in_content, total),
        "subchunk_share": _share(subchunk, total),
        "title_equals_heading_share": _share(title_equals_heading, total),
    }
