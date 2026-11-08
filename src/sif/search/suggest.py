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
import difflib
import math
import sqlite3
from datetime import datetime, timezone

from sif.config.settings import Settings, get_settings
from sif.database.repositories import QueryLogRepository
from sif.search.bm25 import _FTS_METACHARS, BM25Searcher
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

# History ranking half-life (planner discretion, D-13): a query's weight
# halves every 14 days of age.
_HISTORY_HALF_LIFE_DAYS = 14.0


class SuggestionEngine:
    """Suggestion engine: prefix completions, did-you-mean, history."""

    def __init__(self, db: sqlite3.Connection) -> None:
        """Initialize with the searcher's connection (BM25Searcher shape)."""
        self.db = db
        self._terms: list[str] = []  # sorted stems (bisect domain)
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

    def did_you_mean(self, query: str, n: int = 3) -> list[str]:
        """Return up to ``n`` full rewritten queries per out-of-vocab word (D-07).

        Tokens that already retrieve are kept as typed; each out-of-vocab
        token is replaced by its best close match (an alternate match per
        additional variant, positional order deterministic via the sorted
        term list). Returns [] when every token retrieves, when any
        out-of-vocab token has no close match (no fabricated suggestion),
        or when the query has no usable tokens.
        """
        self._ensure_loaded()
        slots = self._dym_slots(self._tokens(query))
        if slots is None:
            return []
        return [variant for variant in self._expand_variants(slots, n) if self._hits(variant)]

    def _probe(self, fts_query: str) -> bool:
        """Run one FTS MATCH existence probe; degrade to False on failure.

        Fail-soft: a missing/locked ``documents_fts`` must yield no
        suggestions, never an exception escaping a search command.
        """
        try:
            row = self.db.execute(
                "SELECT 1 FROM documents_fts WHERE documents_fts MATCH ? LIMIT 1",
                (fts_query,),
            ).fetchone()
        except sqlite3.OperationalError:
            logger.warning("suggestion probe unavailable; treating as no match", exc_info=True)
            return False
        return row is not None

    def _hits(self, variant: str) -> bool:
        """Would this rewritten query retrieve at least one document? (CR-01).

        The suggestion is an AND conjunction of quoted-prefix phrases, so
        each replacement term existing *somewhere* is not enough — the terms
        must co-occur in one document. Probes with the searcher's own
        ``_build_fts_query`` so the check is exactly the query
        ``BM25Searcher.search`` will run (SC2: every emitted suggestion
        returns >= 1 hit).
        """
        # SLF001: reuse the searcher's sanitizer so the probe cannot drift
        # from the real query (porter stemming/quoting/AND join).
        return self._probe(BM25Searcher(self.db)._build_fts_query(variant))  # noqa: SLF001

    def _retrievable(self, token: str) -> bool:
        """Would the searcher retrieve this token? Index probe (WR-01).

        The searcher matches a token through the quoted-prefix form after
        porter stemming, so the in-vocab test must ask the index rather than
        compare strings. The old prefix-substring predicate was wrong in
        both directions: ``"resturant".startswith("rest")`` suppressed a
        legitimate correction, and ``"happy"`` was rewritten to the stem
        ``happi`` even though ``"happy"*`` matches. Probing with the
        searcher's own ``_build_fts_query`` makes the predicate exact.
        """
        # SLF001: same sanitizer as ``_hits`` — the exact query form.
        return self._probe(BM25Searcher(self.db)._build_fts_query(token))  # noqa: SLF001

    def _dym_slots(self, tokens: list[str]) -> list[str | list[str]] | None:
        """Per-token plan: the kept token, or its close matches.

        None means no suggestion: no usable tokens, one uncorrectable
        candidate (an emitted query must have every word retrievable, SC2),
        or an all-retrievable query (D-07 — never a forced suggestion).
        """
        if not tokens:
            return None
        slots: list[str | list[str]] = []
        for token in tokens:
            if self._retrievable(token):
                slots.append(token)
                continue
            matches = self._close_matches(token)
            if not matches:
                return None
            slots.append(matches)
        if all(isinstance(slot, str) for slot in slots):
            return None
        return slots

    def _expand_variants(self, slots: list[str | list[str]], n: int) -> list[str]:
        """Full rewritten queries: best match per candidate, then alternates."""
        variants: list[str] = []
        for depth in range(max(n, 1)):
            parts: list[str] = []
            varied = False
            for slot in slots:
                if isinstance(slot, str):
                    parts.append(slot)
                elif depth < len(slot):
                    varied = True
                    parts.append(slot[depth])
                else:
                    parts.append(slot[-1])
            if not varied and variants:
                break
            variants.append(" ".join(parts))
        return variants[:n]

    def history_suggestions(self, prefix: str = "", n: int = 5) -> list[str]:
        """Rank recent queries by frequency x recency decay (D-13).

        Read gate (D-10): ``SIF_QUERY_HISTORY_ENABLED=0`` or a settings
        failure returns []; a missing ``query_log`` table (old DB) degrades to
        [] with a warning. Cold start (empty table) is empty. Ranking is one
        aggregate read: ``count x exp(-ln(2) x age_days / 14)``, ties broken
        count desc, last_used desc, then lexical — deterministic.
        """
        settings = self._history_settings()
        if settings is None or not settings.query_history_enabled:
            return []
        try:
            rows = QueryLogRepository(self.db).history()
        except sqlite3.OperationalError:
            logger.warning("query history unavailable; returning no suggestions", exc_info=True)
            return []
        return _rank_history(rows, prefix, datetime.now(timezone.utc))[:n]

    @staticmethod
    def _history_settings() -> Settings | None:
        """Best-effort settings read for the D-10 read gate (never raises)."""
        try:
            return get_settings()
        except Exception:
            logger.warning("history suggestions skipped: settings unavailable", exc_info=True)
            return None

    def _tokens(self, query: str) -> list[str]:
        """Tokenize like the searcher matches: whitespace split + metachar strip.

        Reuses ``bm25._FTS_METACHARS`` (imported, never re-derived) so the
        DYM in-vocab predicate sees exactly the tokens ``_build_fts_query``
        would quote; both sides lowercased.
        """
        tokens: list[str] = []
        for raw in query.split():
            cleaned = _FTS_METACHARS.sub(" ", raw).strip().lower()
            tokens.extend(piece for piece in cleaned.split() if piece)
        return tokens

    def _close_matches(self, token: str) -> list[str]:
        """Close vocab matches for a candidate token over a first-letter±1 bucket.

        Full-vocab difflib costs ~46 ms/word at 73k terms (measured); the
        bucket prefilter cuts that to ~11 ms at a documented recall cost
        (first-letter typos ≥ 2 letters away escape the bucket — Pitfall 2).
        Equal-ratio matches resolve in sorted-term order: difflib's internal
        ``nlargest`` breaks ties by heap mechanics, so the returned matches
        are re-sorted here by (ratio desc, term asc) for a stable,
        reproducible order across interpreters.
        """
        first = ord(token[0])
        bucket = [term for term in self._terms if abs(ord(term[0]) - first) <= 1]
        matches = difflib.get_close_matches(token, bucket, n=3, cutoff=0.75)
        if len(matches) > 1:
            matches.sort(key=lambda term: (-_ratio(term, token), term))
        return matches


def _ratio(left: str, right: str) -> float:
    """Similarity ratio for two short strings (tie-break ordering)."""
    return difflib.SequenceMatcher(None, left, right).ratio()


def _rank_history(
    rows: list[tuple[str, int, str]],
    prefix: str,
    now: datetime,
) -> list[str]:
    """Order aggregated history rows by frequency x recency decay (D-13).

    ``count x 2^(-age_days / 14)`` — a fresh single use outranks a stale
    burst. Ties break count desc, last_used desc, then lexical asc via
    successive stable sorts (deterministic for a fixed table).
    """
    lowered = prefix.lower()
    scored: list[tuple[float, int, str, str]] = []
    for query, count, last_used in rows:
        if lowered and not query.lower().startswith(lowered):
            continue
        used_at = datetime.fromisoformat(last_used)
        if used_at.tzinfo is None:
            used_at = used_at.replace(tzinfo=timezone.utc)
        age_days = max((now - used_at).total_seconds(), 0.0) / 86400.0
        score = count * math.exp(-math.log(2) * age_days / _HISTORY_HALF_LIFE_DAYS)
        scored.append((score, count, last_used, query))
    scored.sort(key=lambda item: item[3])
    scored.sort(key=lambda item: item[2], reverse=True)
    scored.sort(key=lambda item: item[1], reverse=True)
    scored.sort(key=lambda item: item[0], reverse=True)
    return [query for _, _, _, query in scored]
