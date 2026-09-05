"""Smart snippet extraction from document chunks."""

from __future__ import annotations

import re

from sif.search import term_match
from sif.utils.logging import get_logger


logger = get_logger(__name__)

# Horizontal rules: runs of -, _ or * only.
_HR_RE = re.compile(r"[-_*]+")

# Table separator rows: pipes, dashes, colons, spaces — and at least one --- run.
_TABLE_SEP_CHARS = set("|-: ")


class SmartSnippetExtractor:
    """Extract the most relevant snippet from text based on query term matching.

    Line-aware: markdown documents are split on newlines and scored per line,
    so the snippet window centers on the matched table row / code line /
    sentence instead of the start of the section block containing it.
    """

    def __init__(self, max_length: int = 300, context_radius: int = 80) -> None:
        """Initialize snippet extractor.

        Args:
            max_length: Maximum snippet length in characters
            context_radius: Kept for API compatibility with existing callers;
                window sizing is driven by max_length alone (line-aware
                windows expand until the joined text reaches max_length).
        """
        self.max_length = max_length
        self.context_radius = context_radius

    def extract(self, text: str, query_terms: list[str]) -> str:
        """Extract the best snippet from text matching query terms.

        Args:
            text: Full chunk or document text
            query_terms: Lowercase query terms to score by

        Returns:
            Best snippet string (may be truncated with ellipsis)
        """
        if not text:
            return ""

        if not query_terms:
            return self._fallback_snippet(text)

        lines = self._split_lines(text)
        best_idx = self._best_line_index(lines, query_terms)
        if best_idx is None:
            return self._fallback_snippet(text)

        if len(lines[best_idx]) > self.max_length:
            return self._cut_long_line(lines[best_idx], query_terms)

        start, end = self._build_window(lines, best_idx)
        return self._render_window(lines, start, end)

    def _split_lines(self, text: str) -> list[str]:
        """Split text into lines, keeping original order."""
        return text.split("\n")

    def _best_line_index(self, lines: list[str], query_terms: list[str]) -> int | None:
        """Return the index of the highest-scoring non-structural line."""
        best_idx: int | None = None
        best_score: tuple[int, float, int] = (0, 0.0, 0)
        for idx, line in enumerate(lines):
            if self._is_structural_line(line):
                continue
            score = self._score_line(line, query_terms)
            if score[0] <= 0:
                continue
            if best_idx is None or score > best_score:
                best_idx = idx
                best_score = score
        return best_idx

    def _score_line(self, line: str, query_terms: list[str]) -> tuple[int, float, int]:
        """Score a line: (distinct terms, weighted counts, negative length).

        Primary key is the number of DISTINCT query terms matched, so a row
        mentioning chunk + overlap + tokens beats a block repeating one term.
        Secondary key weights each match count by term length; the final
        tiebreak prefers shorter (denser) lines.
        """
        distinct = term_match.distinct_terms_matched(line, query_terms)
        if distinct == 0:
            return (0, 0.0, -len(line))
        weighted = sum(term_match.count_matches(line, term) * len(term) for term in query_terms)
        return (distinct, float(weighted), -len(line))

    def _build_window(self, lines: list[str], center_idx: int) -> tuple[int, int]:
        """Build a contiguous line window around the center line.

        Grows alternately upward and downward while the newline-joined window
        stays within max_length, then trims structural lines (fences, blanks,
        separators) from the edges — freeing budget for one more content
        neighbor when it fits.
        """
        start = end = center_idx
        up = center_idx - 1
        down = center_idx + 1
        while True:
            start, end, up, down = self._grow_window(lines, start, end, up, down)
            trimmed_start, trimmed_end = self._trim_window_edges(lines, start, end)
            if (trimmed_start, trimmed_end) == (start, end):
                return start, end
            start, end = trimmed_start, trimmed_end

    def _grow_window(
        self,
        lines: list[str],
        start: int,
        end: int,
        up: int,
        down: int,
    ) -> tuple[int, int, int, int]:
        """Expand the window while it fits max_length; frontiers move outward."""
        added = True
        while added:
            added = False
            if up >= 0 and self._window_length(lines, up, end) <= self.max_length:
                start = up
                up -= 1
                added = True
            if down < len(lines) and self._window_length(lines, start, down) <= (self.max_length):
                end = down
                down += 1
                added = True
        return start, end, up, down

    def _trim_window_edges(self, lines: list[str], start: int, end: int) -> tuple[int, int]:
        """Drop structural lines from the window edges (never the interior)."""
        while start < end and self._is_structural_line(lines[start]):
            start += 1
        while end > start and self._is_structural_line(lines[end]):
            end -= 1
        return start, end

    def _window_length(self, lines: list[str], start: int, end: int) -> int:
        """Length of the newline-joined window lines[start..end] inclusive."""
        total = sum(len(lines[idx]) for idx in range(start, end + 1))
        return total + (end - start)

    def _render_window(self, lines: list[str], start: int, end: int) -> str:
        """Join window lines with newlines and add edge ellipses."""
        snippet = "\n".join(lines[start : end + 1]).strip()
        if start > 0:
            snippet = "..." + snippet
        if end < len(lines) - 1:
            snippet = snippet + "..."
        return snippet

    def _cut_long_line(self, line: str, query_terms: list[str]) -> str:
        """Cut a max_length window centered on the first match in a long line."""
        match = term_match.find_first_match(line, query_terms)
        if match is None:
            return self._truncate(line)
        pos, match_len = match
        start = max(0, pos - self.max_length // 2)
        end = min(len(line), start + self.max_length)
        if end < pos + match_len:
            end = min(len(line), pos + match_len)
            start = max(0, end - self.max_length)
        snippet = line[start:end]
        if start > 0:
            snippet = "..." + snippet
        if end < len(line):
            snippet = snippet + "..."
        return snippet

    def _is_structural_line(self, line: str) -> bool:
        """Classify markdown lines that are structure, not content.

        Structural lines (blank lines, code-fence delimiters, horizontal
        rules, table separator rows) are never window centers and are trimmed
        from window edges, but remain renderable inside windows.
        """
        stripped = line.strip()
        if not stripped:
            return True
        if stripped.startswith(("```", "~~~")):
            return True
        if _HR_RE.fullmatch(stripped):
            return True
        return set(stripped) <= _TABLE_SEP_CHARS and "---" in stripped

    def _fallback_snippet(self, text: str) -> str:
        """Return lead text when no query terms match.

        Skips leading blank lines and code-fence delimiters before
        truncating; headings are legitimate lead content and stay.
        """
        lines = self._split_lines(text)
        idx = 0
        while idx < len(lines) and self._is_leading_skippable(lines[idx]):
            idx += 1
        return self._truncate("\n".join(lines[idx:]))

    def _is_leading_skippable(self, line: str) -> bool:
        """Leading fallback lines to skip: blanks and fence delimiters only."""
        stripped = line.strip()
        return not stripped or stripped.startswith(("```", "~~~"))

    def _truncate(self, text: str) -> str:
        """Truncate text to max_length with ellipsis."""
        if len(text) <= self.max_length:
            return text.strip()
        return text[: self.max_length].strip() + "..."
