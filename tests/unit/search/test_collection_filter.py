"""Regression tests for the collection-filter sentinel contract.

v1.0 audit BLOCKER 1 (CLI-04/CLI-05): when a user excludes every collection,
the CLI resolves enabled collections to an empty list and passes
``SearchOptions(collection_ids=[])``. Searchers must treat that as
"exclude everything" (zero results), NOT as "no filter" — otherwise
exclude-all returns every indexed document. ``None`` remains unfiltered
(``--all``) and a non-empty list is a normal collection filter.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Sequence
from unittest.mock import MagicMock

import pytest

from sif.core.models import SearchOptions
from sif.search.bm25 import BM25Searcher
from sif.search.hybrid import HybridSearcher
from sif.search.vector import VectorSearcher


def _build_search_db(with_vec: bool = False) -> sqlite3.Connection:
    """Build an in-memory DB mirroring the searchers' real SQL.

    Two collections: c1 ("one") holds d1+d2, c2 ("two") holds d3; every
    document's content contains the shared term "python". When ``with_vec``
    is True, sqlite-vec is loaded and each document gets a 2-dim embedding
    near [1.0, 0.0] so vector/hybrid searches recall all three.
    """
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    if with_vec:
        try:
            import sqlite_vec

            conn.enable_load_extension(True)
            sqlite_vec.load(conn)
            conn.enable_load_extension(False)
        except Exception:
            conn.close()
            pytest.skip("sqlite-vec not available")

    conn.execute("CREATE TABLE collections (id TEXT PRIMARY KEY, name TEXT)")
    conn.execute(
        "CREATE TABLE documents "
        "(id TEXT PRIMARY KEY, collection_id TEXT, title TEXT, path TEXT, content TEXT)"
    )
    # Real schema (schema.py:391): planner input making the filtered join degenerate.
    conn.execute("CREATE INDEX idx_documents_collection ON documents(collection_id)")
    conn.execute(
        """
        CREATE TABLE contexts (
            id TEXT PRIMARY KEY, target_id TEXT NOT NULL, context_type TEXT NOT NULL,
            content TEXT NOT NULL, created_at TEXT NOT NULL, updated_at TEXT NOT NULL
        )
        """
    )
    # External-content FTS5, exactly as src/sif/database/schema.py creates it.
    conn.execute(
        """
        CREATE VIRTUAL TABLE documents_fts USING fts5(
            content,
            content='documents',
            content_rowid='rowid',
            tokenize='porter'
        )
        """
    )
    if with_vec:
        conn.execute(
            """
            CREATE VIRTUAL TABLE document_embeddings USING vec0(
                embedding_id TEXT PRIMARY KEY,
                document_id TEXT NOT NULL,
                chunk_id TEXT,
                embedding FLOAT[2]
            )
            """
        )

    conn.execute("INSERT INTO collections VALUES ('c1', 'one'), ('c2', 'two')")
    docs = [
        ("d1", "c1", "/d1.md", "python notes for one-a"),
        ("d2", "c1", "/d2.md", "python notes for one-b"),
        ("d3", "c2", "/d3.md", "python notes for two"),
    ]
    for doc_id, coll_id, path, content in docs:
        conn.execute(
            "INSERT INTO documents (id, collection_id, title, path, content)"
            " VALUES (?, ?, ?, ?, ?)",
            (doc_id, coll_id, doc_id, path, content),
        )
    # External-content FTS5 does not index plain INSERTs — rebuild explicitly.
    conn.execute("INSERT INTO documents_fts(documents_fts) VALUES('rebuild')")

    if with_vec:
        # sqlite-vec rejects NULL for the vec0 TEXT metadata column chunk_id,
        # so each document carries a per-document chunk id string.
        VectorSearcher(conn, embedding_dim=2).add_embeddings_batch(
            [
                ("e1", "d1", "ch1", [1.0, 0.1]),
                ("e2", "d2", "ch2", [1.0, 0.2]),
                ("e3", "d3", "ch3", [1.0, 0.3]),
            ]
        )
    return conn


def _mock_embedder() -> MagicMock:
    """Embedder stub whose embed() always yields the near-anchored query vector."""
    embedder = MagicMock()
    embedder.embed.return_value = [1.0, 0.0]
    embedder.dimension = 2
    return embedder


class TestExcludeAllBM25:
    """Exclude-all sentinel on the BM25 path."""

    def test_exclude_all_bm25_returns_nothing(self) -> None:
        """[] must return zero results, not every document."""
        conn = _build_search_db()
        try:
            results = BM25Searcher(conn).search(
                "python", SearchOptions(collection_ids=[], include_highlights=False)
            )
            assert results == []
        finally:
            conn.close()

    def test_bm25_none_unfiltered_returns_all(self) -> None:
        """None stays unfiltered: all three documents are returned."""
        conn = _build_search_db()
        try:
            results = BM25Searcher(conn).search(
                "python", SearchOptions(collection_ids=None, include_highlights=False)
            )
            assert {r.document_id for r in results} == {"d1", "d2", "d3"}
        finally:
            conn.close()

    def test_bm25_collection_filter_returns_only_that_collection(self) -> None:
        """Non-empty list keeps normal filtering: c1 yields only d1+d2."""
        conn = _build_search_db()
        try:
            results = BM25Searcher(conn).search(
                "python", SearchOptions(collection_ids=["c1"], include_highlights=False)
            )
            assert {r.document_id for r in results} == {"d1", "d2"}
        finally:
            conn.close()


class TestExcludeAllVector:
    """Exclude-all sentinel on the vector path."""

    def test_exclude_all_vector_returns_nothing(self) -> None:
        """[] must return zero results, not every document."""
        conn = _build_search_db(with_vec=True)
        try:
            searcher = VectorSearcher(conn, embedding_dim=2)
            results = searcher.search(
                [1.0, 0.0], SearchOptions(collection_ids=[], include_highlights=False)
            )
            assert results == []
        finally:
            conn.close()

    def test_vector_none_unfiltered_returns_all(self) -> None:
        """None stays unfiltered: all three documents are returned."""
        conn = _build_search_db(with_vec=True)
        try:
            searcher = VectorSearcher(conn, embedding_dim=2)
            results = searcher.search(
                [1.0, 0.0], SearchOptions(collection_ids=None, include_highlights=False)
            )
            assert {r.document_id for r in results} == {"d1", "d2", "d3"}
        finally:
            conn.close()

    def test_vector_collection_filter_returns_only_that_collection(self) -> None:
        """Non-empty list keeps normal filtering: c1 yields only d1+d2."""
        conn = _build_search_db(with_vec=True)
        try:
            searcher = VectorSearcher(conn, embedding_dim=2)
            results = searcher.search(
                [1.0, 0.0], SearchOptions(collection_ids=["c1"], include_highlights=False)
            )
            assert {r.document_id for r in results} == {"d1", "d2"}
        finally:
            conn.close()


class TestExcludeAllHybrid:
    """Exclude-all sentinel through HybridSearcher (delegates to both searchers)."""

    def test_exclude_all_hybrid_returns_nothing(self) -> None:
        """[] must return zero results, not every document."""
        conn = _build_search_db(with_vec=True)
        try:
            searcher = HybridSearcher(conn, embedder=_mock_embedder(), embedding_dim=2)
            results = searcher.search(
                "python", SearchOptions(collection_ids=[], include_highlights=False)
            )
            assert results == []
        finally:
            conn.close()

    def test_hybrid_none_unfiltered_returns_all(self) -> None:
        """None stays unfiltered: all three documents are returned."""
        conn = _build_search_db(with_vec=True)
        try:
            searcher = HybridSearcher(conn, embedder=_mock_embedder(), embedding_dim=2)
            results = searcher.search(
                "python", SearchOptions(collection_ids=None, include_highlights=False)
            )
            assert {r.document_id for r in results} == {"d1", "d2", "d3"}
        finally:
            conn.close()


class _RecordingConnection:
    """Connection proxy recording every statement BM25Searcher executes.

    Only ``execute`` is needed: BM25Searcher and the shared context/staleness
    helpers touch the connection solely through that method.
    """

    def __init__(self, conn: sqlite3.Connection) -> None:
        self.conn = conn
        self.calls: list[tuple[str, Sequence[object]]] = []

    def execute(self, sql: str, parameters: Sequence[object] = ()) -> sqlite3.Cursor:
        """Record the statement, then delegate to the wrapped connection."""
        self.calls.append((sql, parameters))
        return self.conn.execute(sql, parameters)


class TestBM25ScopedQueryPlan:
    """Scoped BM25 evaluates the FTS match once without altering scores.

    The default CLI search paths always pass resolved non-empty collection ids
    (only ``--all`` sends None), so the filtered statement is the production
    path. With the real ``idx_documents_collection`` index present, a bare
    join drives from ``documents`` and re-runs the FTS match per candidate
    document; ``AS MATERIALIZED`` pins the match to one evaluation.
    """

    @pytest.mark.parametrize("collection_ids", [["c1"], ["c1", "c2"]])
    def test_scoped_plan_uses_materialized_match_cte(self, collection_ids: list[str]) -> None:
        """The executed scoped SQL is MATERIALIZED and scans FTS exactly once."""
        conn = _build_search_db()
        try:
            recorder = _RecordingConnection(conn)
            BM25Searcher(recorder).search(  # type: ignore[arg-type]
                "python",
                SearchOptions(collection_ids=collection_ids, include_highlights=False),
            )

            # Capture the exact statement the searcher ran BEFORE EXPLAIN:
            # the EXPLAIN output text also contains the word MATCH.
            sql, params = next(call for call in recorder.calls if "MATCH" in call[0])
            assert "MATERIALIZED" in sql.upper()

            plan = conn.execute(f"EXPLAIN QUERY PLAN {sql}", params).fetchall()
            details = [row[3] for row in plan]
            # No per-document FTS scan (`SCAN fts ... INDEX 32:=M1`) may remain.
            assert not any(":=" in detail for detail in details)
            fts_details = [detail for detail in details if "documents_fts" in detail]
            assert fts_details
            assert all("M1" in detail for detail in fts_details)
            assert any("MATERIALIZE" in detail for detail in details)
        finally:
            conn.close()

    @pytest.mark.parametrize(
        ("collection_ids", "expected_names"),
        [(["c1"], {"one"}), (["c1", "c2"], {"one", "two"})],
    )
    def test_scoped_scores_match_unfiltered(
        self, collection_ids: list[str], expected_names: set[str]
    ) -> None:
        """Scoped ids and scores equal unfiltered results restricted to the scope."""
        conn = _build_search_db()
        try:
            scoped = BM25Searcher(conn).search(
                "python",
                SearchOptions(collection_ids=collection_ids, include_highlights=False),
            )
            unfiltered = BM25Searcher(conn).search(
                "python",
                SearchOptions(collection_ids=None, include_highlights=False),
            )

            expected = {
                result.document_id: result.score
                for result in unfiltered
                if result.collection_name in expected_names
            }
            actual = {result.document_id: result.score for result in scoped}

            # FTS rank ties are not order-stable across plan shapes, so compare
            # dictionaries keyed by document id, never list order.
            assert set(actual) == set(expected)
            for document_id, score in actual.items():
                assert score == expected[document_id]
        finally:
            conn.close()
