"""Unit tests for the derived vector-staleness marker (QUAL-06, D-08/D-09/D-11).

Covers the corrected D-08 formula — stale = document has no rows in
``document_embeddings`` (NOT "chunks without embeddings": BM25-only updates
purge chunks AND embeddings together, so the real lag state is
embeddings-free — RESEARCH Pitfall 3), the display gate (markers only once
the index has >= 1 embedding), vec0-missing degradation, the empty-results
no-query contract, the three searcher delegation sites (D-09 one code path),
and the BM25-refreshed-after-embed lag state produced by a REAL
``update_paths`` purge, never raw-SQL fabrication.
"""

from __future__ import annotations

import json
import sqlite3
from unittest.mock import MagicMock, patch

import pytest

from sif.core.models import SearchOptions, SearchResult
from sif.search.bm25 import BM25Searcher
from sif.search.hybrid import HybridSearcher
from sif.search.staleness import embedded_document_ids, mark_vector_staleness
from sif.search.vector import VectorSearcher


def _vec0_conn(dim: int = 2) -> sqlite3.Connection:
    """In-memory connection with a real vec0 ``document_embeddings`` table."""
    import sqlite_vec

    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    try:
        conn.enable_load_extension(True)
        sqlite_vec.load(conn)
        conn.enable_load_extension(False)
    except Exception:
        conn.close()
        pytest.skip("sqlite-vec not available")
    conn.execute(
        f"""
        CREATE VIRTUAL TABLE document_embeddings USING vec0(
            embedding_id TEXT PRIMARY KEY,
            document_id TEXT NOT NULL,
            chunk_id TEXT,
            embedding FLOAT[{dim}]
        )
        """
    )
    return conn


def _seed_embedding(
    conn: sqlite3.Connection,
    doc_id: str,
    embedding_id: str | None = None,
    dim: int = 2,
) -> None:
    """Insert one embedding row via the vec0-native insert path.

    chunk_id is always a real string: sqlite-vec v0.1.9 rejects NULL for a
    TEXT metadata column on INSERT (same note as test_vector.py's real-vec0
    battery).
    """
    conn.execute(
        "INSERT INTO document_embeddings (embedding_id, document_id, chunk_id, embedding) "
        "VALUES (?, ?, ?, vec_f32(?))",
        (embedding_id or f"e-{doc_id}", doc_id, f"c-{doc_id}", json.dumps([0.1] * dim)),
    )
    conn.commit()


def _result(doc_id: str) -> SearchResult:
    return SearchResult(
        document_id=doc_id,
        title="T",
        path=f"/{doc_id}.md",
        collection_name="c",
        score=1.0,
        rank=1,
    )


class TestEmbeddedDocumentIds:
    """The shared derived scan: id set of embedded documents, None without vec0."""

    def test_returns_seeded_document_ids(self) -> None:
        conn = _vec0_conn()
        try:
            _seed_embedding(conn, "d1")
            _seed_embedding(conn, "d2")
            # a second chunk row for d1: same document id, set semantics
            _seed_embedding(conn, "d1", embedding_id="e-d1-b")
            assert embedded_document_ids(conn) == {"d1", "d2"}
        finally:
            conn.close()

    def test_empty_table_returns_empty_set(self) -> None:
        conn = _vec0_conn()
        try:
            assert embedded_document_ids(conn) == set()
        finally:
            conn.close()

    def test_missing_vec0_table_returns_none(self) -> None:
        """A plain connection without the vec0 table degrades to None, never raises."""
        conn = sqlite3.connect(":memory:")
        try:
            assert embedded_document_ids(conn) is None
        finally:
            conn.close()


class TestMarkVectorStaleness:
    """Marking semantics: embedded unmarked, embedding-less marked (gated)."""

    def test_embedded_document_unmarked(self) -> None:
        conn = _vec0_conn()
        try:
            _seed_embedding(conn, "d1")
            results = mark_vector_staleness(conn, [_result("d1")])
            assert results[0].vectors_stale is False
        finally:
            conn.close()

    def test_never_embedded_document_marked_when_index_has_embeddings(self) -> None:
        """Corrected D-08 formula: stale = no rows in document_embeddings.

        The gate is armed by the OTHER document's embedding — a never-embedded
        doc on an index that has embeddings genuinely cannot appear in the
        vector leg, so it is marked.
        """
        conn = _vec0_conn()
        try:
            _seed_embedding(conn, "d-other")
            results = mark_vector_staleness(conn, [_result("d1"), _result("d-other")])
            assert results[0].vectors_stale is True
            assert results[1].vectors_stale is False
        finally:
            conn.close()

    def test_display_gate_zero_embeddings_marks_nothing(self) -> None:
        """Index with ZERO embeddings overall: no markers (pure-BM25 users see none)."""
        conn = _vec0_conn()
        try:
            results = mark_vector_staleness(conn, [_result("d1"), _result("d2")])
            assert all(r.vectors_stale is False for r in results)
        finally:
            conn.close()

    def test_vec0_missing_degrades_to_unmarked(self) -> None:
        """No vec0 table: OperationalError swallowed, results unmarked, no raise."""
        conn = sqlite3.connect(":memory:")
        try:
            results = mark_vector_staleness(conn, [_result("d1")])
            assert results[0].vectors_stale is False
        finally:
            conn.close()

    def test_empty_results_never_queries(self) -> None:
        """An empty results list returns unchanged without touching the DB."""
        mock_db = MagicMock()
        assert mark_vector_staleness(mock_db, []) == []
        mock_db.execute.assert_not_called()

    def test_marking_is_idempotent(self) -> None:
        """Applying the marker twice yields identical flags (derived, never persisted)."""
        conn = _vec0_conn()
        try:
            _seed_embedding(conn, "d-keep")
            once = mark_vector_staleness(conn, [_result("d1"), _result("d-keep")])
            twice = mark_vector_staleness(conn, once)
            assert [r.vectors_stale for r in once] == [True, False]
            assert [r.vectors_stale for r in twice] == [True, False]
        finally:
            conn.close()

    def test_to_dict_carries_vectors_stale_alongside_context_description(self) -> None:
        result = _result("d1")
        result.vectors_stale = True
        payload = result.to_dict()
        assert payload["vectors_stale"] is True
        assert "context_description" in payload


class TestLagStateEndToEnd:
    """The real tiered-depth lag state: BM25 refresh purges embeddings (D-10)."""

    def test_bm25_refreshed_after_embed_doc_is_marked_stale(self, tmp_path, monkeypatch) -> None:
        """Embed → modify → update_paths purge → the doc's BM25 results are marked.

        The lag state is produced by the REAL purge (update_paths), not by
        raw-SQL "chunks without embeddings" fabrication (RESEARCH Pitfall 3
        warning sign).
        """
        for var in ("SIF_EMBEDDING_DIM", "SIF_MODEL_TYPE", "SIF_MODEL_NAME"):
            monkeypatch.delenv(var, raising=False)
        from sif.config.settings import Settings
        from sif.core.models import Collection as Coll
        from sif.database.database import Database
        from sif.database.repositories import CollectionRepository, DocumentRepository
        from sif.indexing.incremental import IncrementalIndexer

        settings = Settings(embedding_dim=2, model_name="test", cache_embeddings=False)
        db_path = tmp_path / "lag.db"
        notes = tmp_path / "notes"
        notes.mkdir()
        doc_file = notes / "a.md"
        doc_file.write_text("# Alpha\n\nalpha needle text\n", encoding="utf-8")
        # A second document that stays embedded: the display gate needs the
        # index to retain >= 1 embedding after a.md's purge, else nothing is
        # marked (the gate is the plan-time resolution of RESEARCH OQ2).
        keeper_file = notes / "b.md"
        keeper_file.write_text("# Beta\n\nbeta other text\n", encoding="utf-8")

        db = Database(db_path)
        with patch("sif.config.settings.get_settings", return_value=settings):
            db.init_schema()
            with db.connection:
                coll = Coll(name="notes", path=str(notes))
                CollectionRepository(db.connection).create(coll)
        try:
            # Index once (BM25), then embed both documents for real.
            indexer = IncrementalIndexer(db.connection)
            assert indexer.update_collection(coll).added == 2
            doc_repo = DocumentRepository(db.connection)
            doc = doc_repo.get_by_path(str(doc_file), coll.id)
            keeper = doc_repo.get_by_path(str(keeper_file), coll.id)
            assert doc is not None
            assert keeper is not None
            with db.connection:
                embedder = VectorSearcher(db.connection, embedding_dim=2)
                embedder.add_embedding(f"e-{doc.id}", doc.id, f"c-{doc.id}", [0.1, 0.2])
                embedder.add_embedding(f"e-{keeper.id}", keeper.id, f"c-{keeper.id}", [0.2, 0.1])
            assert embedded_document_ids(db.connection) == {doc.id, keeper.id}

            # Before drift: embedded documents → unmarked results.
            clean = BM25Searcher(db.connection).search("alpha", SearchOptions(limit=5))
            assert clean
            assert clean[0].vectors_stale is False

            # Drift: modify a.md, BM25-refresh through the per-path seam —
            # the purge removes ITS embedding and produces the real lag state
            # (b.md's embedding survives, arming the display gate).
            doc_file.write_text("# Alpha changed\n\nalpha needle text v2\n", encoding="utf-8")
            counts = indexer.update_paths(coll, [doc_file])
            assert counts.updated == 1
            assert embedded_document_ids(db.connection) == {keeper.id}

            lagging = BM25Searcher(db.connection).search("alpha", SearchOptions(limit=5))
            assert lagging
            assert lagging[0].vectors_stale is True
            keeper_hits = BM25Searcher(db.connection).search("beta", SearchOptions(limit=5))
            assert keeper_hits
            assert keeper_hits[0].vectors_stale is False
        finally:
            db.close()


class TestSearcherDelegation:
    """D-09: every searcher exit invokes mark_vector_staleness via _attach_contexts."""

    def test_all_three_searchers_delegate(self, monkeypatch) -> None:
        calls: list[tuple[str, object, list[SearchResult]]] = []

        def recording_wrapper(tag: str):
            def wrapper(db, results):
                calls.append((tag, db, results))
                return results

            return wrapper

        monkeypatch.setattr("sif.search.bm25.mark_vector_staleness", recording_wrapper("bm25"))
        bm25_searcher = BM25Searcher(MagicMock())
        bm25_results = [_result("d-b")]
        bm25_searcher._attach_contexts(bm25_results)

        monkeypatch.setattr("sif.search.vector.mark_vector_staleness", recording_wrapper("vector"))
        vector_searcher = VectorSearcher(MagicMock())
        vector_results = [_result("d-v")]
        vector_searcher._attach_contexts(vector_results)

        monkeypatch.setattr("sif.search.hybrid.mark_vector_staleness", recording_wrapper("hybrid"))
        hybrid_searcher = HybridSearcher(MagicMock(), embedder=None)
        hybrid_results = [_result("d-h")]
        hybrid_searcher._attach_contexts(hybrid_results)

        assert [c[0] for c in calls] == ["bm25", "vector", "hybrid"]
        assert calls[0][1] is bm25_searcher.db
        assert calls[0][2] is bm25_results
        assert calls[1][1] is vector_searcher.db
        assert calls[1][2] is vector_results
        assert calls[2][1] is hybrid_searcher.db
        assert calls[2][2] is hybrid_results
