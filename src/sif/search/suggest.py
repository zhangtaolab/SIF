"""Query suggestion engine over the FTS5 vocabulary (Phase 15).

D-06: the term source is the FTS5 vocab shadow table (``documents_fts_v``,
fts5vocab row mode) — one row per distinct porter-stem term with its document
frequency, derived from the index so it never needs sync maintenance. D-07:
did-you-mean rewrites the FULL query per out-of-vocab word. Suggestions are
display strings only; when re-queried they flow through BM25Searcher /
``_build_fts_query`` quoting, never hand-built MATCH strings.

Every ``sqlite3.OperationalError`` path (read-only DB, missing FTS schema)
degrades to empty suggestions with a warning — a suggestion failure must
never crash a search command.
"""

from __future__ import annotations

import bisect
import sqlite3

from sif.utils.logging import get_logger


logger = get_logger(__name__)

# Same idempotent DDL SchemaManager._create_fts_tables runs, re-executed on
# first use: old DBs opened without init_schema (e.g. MCP backend
# connections) never created the vocab shadow (RESEARCH Pitfall 8).
_VOCAB_DDL = """
    CREATE VIRTUAL TABLE IF NOT EXISTS documents_fts_v
    USING fts5vocab(documents_fts, 'row')
"""

# Prefix completions below this length would enumerate huge ranges for
# near-zero signal (planner discretion, pinned by test).
MIN_PREFIX_LEN = 2


class SuggestionEngine:
    """Suggestion engine: prefix completions, did-you-mean, history."""

    def __init__(self, db: sqlite3.Connection) -> None:
        """Initialize with the searcher's connection (BM25Searcher shape)."""
        self.db = db
        self._terms: list[str] = []  # sorted stems (bisect domain)
        self._term_set: set[str] = set()
        self._df: dict[str, int] = {}  # term -> documents containing it
        self._loaded = False

    def _ensure_vocab(self) -> None:
        """Create the vocab shadow table if an old DB lacks it (idempotent)."""
        self.db.execute(_VOCAB_DDL)

    def _load(self) -> None:
        """Load the vocabulary from the vocab shadow table."""
        rows = self.db.execute("SELECT term, doc FROM documents_fts_v").fetchall()
        terms = [row[0] for row in rows]
        terms.sort()
        self._terms = terms
        self._term_set = set(terms)
        self._df = {row[0]: row[1] for row in rows}

    def _ensure_loaded(self) -> None:
        """Lazily ensure + load the vocabulary; degrade to empty on failure."""
        if self._loaded:
            return
        try:
            self._ensure_vocab()
            self._load()
        except sqlite3.OperationalError:
            logger.warning(
                "suggestion vocabulary unavailable; returning no suggestions",
                exc_info=True,
            )
            self._terms = []
            self._term_set = set()
            self._df = {}
        self._loaded = True

    def prefix_completions(self, prefix: str, n: int = 5) -> list[str]:
        """Return up to ``n`` vocab terms starting with ``prefix``.

        Collects the first ``n`` matches over the sorted term list (bisect,
        ~free — no SQL LIKE), then ranks them by document frequency
        descending with lexical order breaking ties, so output is
        deterministic for a fixed vocabulary.
        """
        self._ensure_loaded()
        lowered = prefix.lower()
        if len(lowered) < MIN_PREFIX_LEN:
            return []
        matches: list[str] = []
        index = bisect.bisect_left(self._terms, lowered)
        while index < len(self._terms) and self._terms[index].startswith(lowered):
            matches.append(self._terms[index])
            index += 1
            if len(matches) >= n:
                break
        matches.sort(key=lambda term: (-self._df.get(term, 0), term))
        return matches
