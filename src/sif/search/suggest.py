"""Query suggestion engine over the FTS5 vocabulary (Phase 15).

D-06: the term source is the FTS5 vocab shadow table (``documents_fts_v``,
fts5vocab row mode) — one row per distinct porter-stem term with its document
frequency, derived from the index so it never needs sync maintenance. D-07:
did-you-mean rewrites the FULL query per out-of-vocab word. Suggestions are
display strings only; when re-queried they flow through BM25Searcher /
``_build_fts_query`` quoting, never hand-built MATCH strings.
"""

from __future__ import annotations

import sqlite3

from sif.utils.logging import get_logger

logger = get_logger(__name__)


class SuggestionEngine:
    """Suggestion engine: prefix completions, did-you-mean, history."""

    def __init__(self, db: sqlite3.Connection) -> None:
        """Initialize with the searcher's connection (BM25Searcher shape)."""
        self.db = db

    def _ensure_vocab(self) -> None:
        """Create the vocab shadow table if an old DB lacks it (idempotent)."""

    def _load(self) -> None:
        """Load the vocabulary from the vocab shadow table."""

    def prefix_completions(self, prefix: str, n: int = 5) -> list[str]:
        """Return up to ``n`` vocab terms starting with ``prefix``."""
        return []
