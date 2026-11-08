"""SuggestionEngine battery: vocabulary, prefix completions, degradation.

Phase 15 QUAL-02/04 core (D-06): the engine reads the FTS5 vocab shadow table
(``documents_fts_v`` — fts5vocab row mode, porter STEMS). Every completion is
a vocab term, so running it back through a real BM25 query must return at
least one hit — SC2's structural guarantee, pinned here against the real
searcher on a real DB built from the production DDL.
"""

from __future__ import annotations

import difflib
import sqlite3
import time
from datetime import datetime, timezone

import pytest

from sif.core.models import SearchOptions
from sif.database.schema import SchemaManager
from sif.search.bm25 import BM25Searcher
from sif.search.suggest import SuggestionEngine


def _fixture_db(*docs: tuple[str, str]) -> sqlite3.Connection:
    """Real in-memory DB from the production DDL with one collection + docs.

    Each doc is ``(doc_id, content)``; inserting into ``documents`` fires the
    external-content sync triggers so ``documents_fts`` (and therefore the
    vocab shadow) reflects the corpus without manual FTS writes.
    """
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    SchemaManager(conn, embedding_dim=8).create_all()
    now = datetime.now(timezone.utc).isoformat()
    conn.execute(
        "INSERT INTO collections (id, name, path, created_at, updated_at) "
        "VALUES ('c1', 'notes', '/vault', ?, ?)",
        (now, now),
    )
    conn.executemany(
        "INSERT INTO documents (id, collection_id, path, filename, title, content, "
        "checksum, mtime, created_at, updated_at) "
        "VALUES (?, 'c1', ?, ?, ?, ?, ?, 1.0, ?, ?)",
        [
            (
                doc_id,
                f"/vault/{doc_id}.md",
                f"{doc_id}.md",
                doc_id,
                content,
                f"ck-{doc_id}",
                now,
                now,
            )
            for doc_id, content in docs
        ],
    )
    conn.commit()
    return conn


@pytest.fixture
def vocab_db():
    """Corpus whose porter stems anchor the prefix/DYM assertions below."""
    conn = _fixture_db(
        ("d1", "quantum machine learning algorithms"),
        ("d2", "quantum computing quick quantifiers"),
        ("d3", "studies of machine learning contexts"),
        ("d4", "dreaming machines study patterns"),
    )
    yield conn
    conn.close()


class _ReadOnlyVocabConnection:
    """Adapter failing DDL as a read-only SQLite database would (degrade edge)."""

    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def execute(self, sql: str, parameters: tuple = ()) -> sqlite3.Cursor:
        if sql.lstrip().upper().startswith("CREATE"):
            raise sqlite3.OperationalError("attempt to write a readonly database")
        return self._conn.execute(sql, parameters)


class TestPrefixCompletions:
    """D-06 tracer: prefix completions are real, queryable vocab stems."""

    def test_completions_are_real_queryable_stems(self, vocab_db):
        """Every 'quant' completion starts with the prefix and hits as a query (SC2)."""
        engine = SuggestionEngine(vocab_db)
        completions = engine.prefix_completions("quant", 5)

        assert completions, "expected at least one completion for prefix 'quant'"
        searcher = BM25Searcher(vocab_db)
        for term in completions:
            assert term.startswith("quant")
            results = searcher.search(term, SearchOptions(limit=1))
            assert results, f"completion {term!r} returned zero hits (SC2 violation)"

    def test_completions_rank_by_doc_frequency_then_lexical(self, vocab_db):
        """df desc first, lexical ascending for equal df; ``n`` bounds the section."""
        engine = SuggestionEngine(vocab_db)

        # 'qu' matches quantifi (df 1), quantum (df 2), quick (df 1)
        assert engine.prefix_completions("qu", 3) == ["quantum", "quantifi", "quick"]
        # n=2 collects the first two lexically, then ranks them
        assert engine.prefix_completions("qu", 2) == ["quantum", "quantifi"]

    def test_prefix_matching_is_case_insensitive(self, vocab_db):
        """The prefix lowercases before the scan; vocab terms are lowercase stems."""
        engine = SuggestionEngine(vocab_db)
        assert engine.prefix_completions("QUANT", 5) == engine.prefix_completions("quant", 5)

    def test_prefix_shorter_than_two_returns_empty(self, vocab_db):
        """Min prefix length 2 (pinned discretion): 'q' and '' yield nothing."""
        engine = SuggestionEngine(vocab_db)
        assert engine.prefix_completions("q", 5) == []
        assert engine.prefix_completions("", 5) == []

    def test_no_vocab_match_returns_empty(self, vocab_db):
        """A prefix hitting nothing in the vocab degrades to an empty section."""
        engine = SuggestionEngine(vocab_db)
        assert engine.prefix_completions("zzzz", 5) == []


class TestDidYouMean:
    """D-07: per-word replacement into full rewritten queries; SC2 pinned.

    The vocab stores porter STEMS, so replacements display stems (accepted,
    RESEARCH A1); in-vocab words are kept as typed. The in-vocab predicate is
    prefix-range membership (locked in plan Task 2, Pitfall 4): a token
    "retrieves" when any vocab term starts with it or it starts with a vocab
    term — only tokens whose prefix range hits nothing are DYM candidates.
    """

    def test_rewrites_full_query_per_out_of_vocab_word(self, vocab_db):
        """D-07 shape: typo replaced by its close stem; in-vocab word kept as typed."""
        engine = SuggestionEngine(vocab_db)
        # 'machien' is out-of-vocab; 'quantum' retrieves (kept as typed). The
        # replacement is the vocab stem 'machin' (stem display accepted).
        assert engine.did_you_mean("quantum machien") == ["quantum machin"]

    def test_variant_depth_follows_close_match_order(self):
        """A token with two equal-ratio matches yields two variants, best-first."""
        conn = _fixture_db(
            ("v1", "corner store"),
            ("v2", "cornet music"),
        )
        try:
            engine = SuggestionEngine(conn)
            # corner/cornet tie at ratio 10/12 >= 0.75; the sorted bucket
            # resolves the tie stably (corner before cornet)
            assert engine.did_you_mean("cornex") == ["corner", "cornet"]
        finally:
            conn.close()

    def test_no_dym_when_every_word_retrieves(self, vocab_db):
        """D-07: an all-retrievable query yields [] — never a forced suggestion."""
        engine = SuggestionEngine(vocab_db)
        # 'machines' retrieves: porter matches it to stem 'machin' through the
        # quoted-prefix form, and 'machines' starts with the vocab term
        # 'machin' (prefix-range membership, Pitfall 4)
        assert engine.did_you_mean("quantum machines") == []

    def test_every_suggestion_hits_as_query(self, vocab_db):
        """SC2 pin: every DYM suggestion returns >= 1 result via a real BM25 query."""
        engine = SuggestionEngine(vocab_db)
        searcher = BM25Searcher(vocab_db)
        for query in ("machien", "machien quantom"):
            suggestions = engine.did_you_mean(query)
            assert suggestions, f"expected suggestions for {query!r}"
            for suggestion in suggestions:
                results = searcher.search(suggestion, SearchOptions(limit=1))
                assert results, f"suggestion {suggestion!r} returned zero hits (SC2)"

    def test_uncorrectable_token_yields_no_suggestion(self, vocab_db):
        """An out-of-vocab word with no close match yields [] (never fabricated)."""
        engine = SuggestionEngine(vocab_db)
        assert engine.did_you_mean("quantum xqzjw") == []
        # One uncorrectable candidate poisons the whole rewrite: the emitted
        # query must have every word retrievable (SC2 by construction)
        assert engine.did_you_mean("machien xqzjw") == []

    def test_repeated_calls_are_deterministic(self, vocab_db):
        """Same vocab + query produce identical suggestion lists (tie stability)."""
        engine = SuggestionEngine(vocab_db)
        first = engine.did_you_mean("machien quantom")
        assert first
        for _ in range(3):
            assert engine.did_you_mean("machien quantom") == first

    def test_empty_and_metachar_only_queries_return_empty(self, vocab_db):
        """No usable tokens -> no suggestions, no crash."""
        engine = SuggestionEngine(vocab_db)
        assert engine.did_you_mean("") == []
        assert engine.did_you_mean('""" (( )) ^^') == []


_CHARSET = "0123456789abcdefghijklmnopqrstuvwxyz"


def _big_vocab_conn() -> sqlite3.Connection:
    """Synthetic >= 60k-distinct-term vocab (research A2 recipe).

    300 docs x 220 unique words (66k terms), first characters spread over
    ``0-9a-z`` so the first-letter+-1 bucket is a small, measurable fraction
    of the vocabulary.
    """
    conn = _fixture_db(*_big_vocab_docs())
    return conn


def _big_vocab_docs() -> list[tuple[str, str]]:
    docs: list[tuple[str, str]] = []
    for doc in range(300):
        words = []
        for i in range(220):
            idx = doc * 220 + i
            words.append(f"{_CHARSET[idx % 36]}{idx:05d}")
        docs.append((f"d{doc:03d}", " ".join(words)))
    return docs


class TestCoreBudget:
    """D-14: bucketed matching proven deterministically; generous wall bound."""

    def test_bucketed_dym_under_budget_on_60k_vocab(self, vocab_db, monkeypatch):
        """Core (prefix + DYM incl. vocab scan) < 1.0 s; bucket < 10% of vocab.

        The bucket assertion is deterministic — it catches a full-scan
        regression without timing races (plan Task 2, Test 5).
        """
        conn = _big_vocab_conn()
        try:
            vocab_size = conn.execute("SELECT COUNT(*) FROM documents_fts_v").fetchone()[0]
            assert vocab_size >= 60_000

            calls: list[int] = []
            real = difflib.get_close_matches

            def spy(word, possibilities, n=3, cutoff=0.6):  # type: ignore[no-untyped-def]
                calls.append(len(possibilities))
                return real(word, possibilities, n=n, cutoff=cutoff)

            monkeypatch.setattr(difflib, "get_close_matches", spy)

            engine = SuggestionEngine(conn)
            start = time.perf_counter()
            completions = engine.prefix_completions("m0", 5)
            engine.did_you_mean("mzzzzz9 xzzzzz9")
            elapsed = time.perf_counter() - start

            assert completions, "expected 'm0' completions in the synthetic vocab"
            assert calls, "DYM never consulted difflib"
            assert max(calls) < vocab_size * 0.10
            assert elapsed < 1.0
        finally:
            conn.close()


class TestVocabDegradation:
    """Engine edges: empty vocab, missing vocab, read-only DB — never raise."""

    def test_empty_vocab_returns_empty(self):
        """A schema-complete DB with zero documents has an empty vocab."""
        conn = _fixture_db()
        try:
            engine = SuggestionEngine(conn)
            assert engine.prefix_completions("quant", 5) == []
        finally:
            conn.close()

    def test_missing_vocab_table_degrades_to_empty(self):
        """A bare connection without the FTS schema yields [], not OperationalError."""
        conn = sqlite3.connect(":memory:")
        conn.row_factory = sqlite3.Row
        try:
            engine = SuggestionEngine(conn)
            assert engine.prefix_completions("quant", 5) == []
        finally:
            conn.close()

    def test_read_only_db_degrades_to_empty(self, vocab_db):
        """Vocab creation failing (read-only DB) degrades to empty, never raises."""
        engine = SuggestionEngine(_ReadOnlyVocabConnection(vocab_db))
        assert engine.prefix_completions("quant", 5) == []
