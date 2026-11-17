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
