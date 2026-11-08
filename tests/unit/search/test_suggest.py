"""SuggestionEngine battery: vocabulary, prefix completions, degradation.

Phase 15 QUAL-02/04 core (D-06): the engine reads the FTS5 vocab shadow table
(``documents_fts_v`` — fts5vocab row mode, porter STEMS). Every completion is
a vocab term, so running it back through a real BM25 query must return at
least one hit — SC2's structural guarantee, pinned here against the real
searcher on a real DB built from the production DDL.
"""

from __future__ import annotations

import sqlite3
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
