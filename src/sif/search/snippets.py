"""Smart snippet extraction from document chunks."""

from __future__ import annotations

import re

from docsift.utils.logging import get_logger


logger = get_logger(__name__)


class SmartSnippetExtractor:
    """Extract the most relevant snippet from a chunk based on query term frequency."""

    def __init__(self, max_length: int = 300, context_radius: int = 80) -> None:
        """Initialize snippet extractor.

        Args:
            max_length: Maximum snippet length in characters
            context_radius: Context radius around best sentence (unused, kept for API compat)
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

        # Split into sentences
        sentences = self._split_sentences(text)
        if len(sentences) <= 1:
            return self._truncate(text)

        # Score each sentence by query term frequency
        scored = []
        for i, sentence in enumerate(sentences):
            score = self._score_sentence(sentence, query_terms)
            scored.append((i, score, sentence))

        # Find the highest-scoring sentence
        scored.sort(key=lambda x: x[1], reverse=True)
        best_idx, best_score, _best_sentence = scored[0]

        if best_score == 0:
            return self._fallback_snippet(text)

        # Build a window around the best sentence
        return self._build_window(sentences, best_idx, query_terms)

    def _split_sentences(self, text: str) -> list[str]:
        """Split text into sentences."""
        # Simple sentence splitting on .!? followed by space or end
        sentences = re.split(r"(?<=[.!?])\s+", text.strip())
        return [s.strip() for s in sentences if s.strip()]

    def _score_sentence(self, sentence: str, query_terms: list[str]) -> float:
        """Score a sentence by weighted query term frequency."""
        sentence_lower = sentence.lower()
        score = 0.0
        for term in query_terms:
            count = sentence_lower.count(term.lower())
            # Longer matches get higher weight
            score += count * len(term)
        return score

    def _build_window(self, sentences: list[str], center_idx: int, _query_terms: list[str]) -> str:
        """Build a contiguous window of sentences around the center."""
        # Start with center sentence
        window = [sentences[center_idx]]
        total_len = len(window[0])

        # Expand outward
        left = center_idx - 1
        right = center_idx + 1

        while True:
            added = False
            # Try adding from left
            if left >= 0:
                candidate = sentences[left]
                if total_len + len(candidate) + 1 <= self.max_length:
                    window.insert(0, candidate)
                    total_len += len(candidate) + 1
                    left -= 1
                    added = True

            # Try adding from right
            if right < len(sentences):
                candidate = sentences[right]
                if total_len + len(candidate) + 1 <= self.max_length:
                    window.append(candidate)
                    total_len += len(candidate) + 1
                    right += 1
                    added = True

            if not added:
                break

        snippet = " ".join(window)

        # Add ellipsis if truncated
        if left >= 0:
            snippet = "..." + snippet
        if right < len(sentences):
            snippet = snippet + "..."

        return snippet.strip()

    def _fallback_snippet(self, text: str) -> str:
        """Return the beginning of text when no query terms match."""
        return self._truncate(text)

    def _truncate(self, text: str) -> str:
        """Truncate text to max_length with ellipsis."""
        if len(text) <= self.max_length:
            return text.strip()
        return text[: self.max_length].strip() + "..."
