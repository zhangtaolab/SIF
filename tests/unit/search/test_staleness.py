"""Unit tests for the derived vector-staleness marker (QUAL-06, D-08/D-09/D-11).

Covers the corrected D-08 formula — stale = document has no rows in
``document_embeddings`` (NOT "chunks without embeddings": BM25-only updates
purge chunks AND embeddings together, so the real lag state is
embeddings-free — RESEARCH Pitfall 3), the display gate (markers only once
the index has >= 1 embedding), vec0/shadow-missing degradation, the
empty-results no-query contract, the single-owner enrichment contract
(searchers return raw results; each pipeline exit calls ``enrich_results``
exactly once — D-09), and the BM25-refreshed-after-embed lag state produced
by a REAL ``update_paths`` purge, never raw-SQL fabrication.

CORR-06 (D-09/D-11): the marker now reads the transactionally maintained
``embedded_documents`` shadow. This module also pins the writer contract
(batch/insert/delete shadow maintenance, the join-to-``documents`` orphan
rule) and asserts the search path issues a display-gate probe plus indexed
primary-key lookups, never a full ``document_embeddings`` scan.
"""

from __future__ import annotations

import json
import sqlite3
from unittest.mock import MagicMock, patch

import pytest

from sif.core.models import SearchOptions, SearchResult
from sif.search.bm25 import BM25Searcher
from sif.search.context_attach import enrich_results
from sif.search.hybrid import HybridSearcher, SearchPipeline
from sif.search.staleness import embedded_document_ids, mark_vector_staleness
from sif.search.vector import VectorSearcher


def _vec0_conn(
    dim: int = 2,
    *,
    shadow: bool = True,
    document_ids: tuple[str, ...] = (),
) -> sqlite3.Connection:
    """In-memory connection with a real vec0 ``document_embeddings`` table.

    The derived ``embedded_documents`` shadow and a minimal ``documents``
    table are built here too (the production DDL arrives with the schema
    task): the writer tests exercise the join-to-``documents`` insert, and
    the reader tests need the shadow to exist. ``shadow=False`` models a
    bare vec0 database for the degradation path.
    """
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
    conn.execute("CREATE TABLE IF NOT EXISTS documents (id TEXT PRIMARY KEY)")
    if shadow:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS embedded_documents (
                document_id TEXT PRIMARY KEY,
                FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE
            )
            """
        )
    for document_id in document_ids:
        conn.execute("INSERT OR IGNORE INTO documents (id) VALUES (?)", (document_id,))
    conn.commit()
    return conn


def _insert_vec_row(
    conn: sqlite3.Connection,
    doc_id: str,
    embedding_id: str | None = None,
    dim: int = 2,
) -> None:
    """Insert one embedding row via the raw vec0-native path (no shadow write)."""
    conn.execute(
        "INSERT INTO document_embeddings (embedding_id, document_id, chunk_id, embedding) "
        "VALUES (?, ?, ?, vec_f32(?))",
        (embedding_id or f"e-{doc_id}", doc_id, f"c-{doc_id}", json.dumps([0.1] * dim)),
    )
    conn.commit()


def _seed_embedding(
    conn: sqlite3.Connection,
    doc_id: str,
    embedding_id: str | None = None,
    dim: int = 2,
) -> None:
    """Seed a vec0 row AND its shadow row (a truthful raw writer).

    chunk_id is always a real string: sqlite-vec v0.1.9 rejects NULL for a
    TEXT metadata column on INSERT (same note as test_vector.py's real-vec0
    battery).
    """
    _insert_vec_row(conn, doc_id, embedding_id=embedding_id, dim=dim)
    conn.execute(
        "INSERT OR IGNORE INTO embedded_documents(document_id) VALUES (?)",
        (doc_id,),
    )
    conn.commit()


class _RecordingConnection:
    """Connection proxy recording every SQL statement it is asked to run."""

    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn
        self.statements: list[str] = []

    def execute(self, sql: str, params: tuple[object, ...] = ()) -> sqlite3.Cursor:
        self.statements.append(sql)
        return self._conn.execute(sql, params)


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

    def test_missing_shadow_table_returns_none(self) -> None:
        """vec0 present but the derived shadow absent: the same None degradation."""
        conn = _vec0_conn(shadow=False)
        try:
            _insert_vec_row(conn, "d1")
            assert embedded_document_ids(conn) is None
        finally:
            conn.close()


class TestShadowWritePath:
    """CORR-06 D-09: VectorSearcher keeps ``embedded_documents`` transactional.

    Every writer path is exercised against a real vec0 table: the batch
    insert writes one row per distinct existing document, the document delete
    removes only that document's row (returning the vec0 rowcount), and a raw
    orphan vec0 row never creates a shadow row because the insert joins
    ``documents``.
    """

    def test_batch_write_creates_one_shadow_row_per_document(self) -> None:
        conn = _vec0_conn(document_ids=("d1", "d2"))
        try:
            searcher = VectorSearcher(conn, embedding_dim=2)
            searcher.add_embeddings_batch(
                [
                    ("e1", "d1", "c1", [0.1, 0.2]),
                    ("e2", "d1", "c1b", [0.2, 0.1]),
                    ("e3", "d2", "c2", [0.3, 0.4]),
                ]
            )

            rows = conn.execute(
                "SELECT document_id FROM embedded_documents ORDER BY document_id"
            ).fetchall()
            assert [row[0] for row in rows] == ["d1", "d2"]
        finally:
            conn.close()

    def test_delete_removes_only_that_documents_shadow_row(self) -> None:
        conn = _vec0_conn(document_ids=("d1", "d2"))
        try:
            searcher = VectorSearcher(conn, embedding_dim=2)
            searcher.add_embeddings_batch(
                [
                    ("e1", "d1", "c1", [0.1, 0.2]),
                    ("e2", "d1", "c1b", [0.2, 0.1]),
                    ("e3", "d2", "c2", [0.3, 0.4]),
                ]
            )

            # The vec0 rowcount is returned unchanged by the shadow delete.
            assert searcher.delete_embeddings_by_document("d1") == 2
            rows = conn.execute("SELECT document_id FROM embedded_documents").fetchall()
            assert [row[0] for row in rows] == ["d2"]
        finally:
            conn.close()

    def test_orphan_vector_insert_never_creates_a_shadow_row(self) -> None:
        """A vec0 row for a document absent from ``documents`` is not shadowed."""
        conn = _vec0_conn()
        try:
            _insert_vec_row(conn, "d-deleted")

            assert embedded_document_ids(conn) == set()
            assert (
                conn.execute(
                    "SELECT COUNT(*) FROM embedded_documents WHERE document_id = 'd-deleted'"
                ).fetchone()[0]
                == 0
            )
        finally:
            conn.close()

    def test_no_shadow_table_is_a_write_no_op(self) -> None:
        """Pre-Phase-21/bare vec0 databases keep working: no shadow statements."""
        conn = _vec0_conn(shadow=False, document_ids=("d1",))
        try:
            searcher = VectorSearcher(conn, embedding_dim=2)
            searcher.add_embedding("e1", "d1", "c1", [0.1, 0.2])
            assert searcher.delete_embeddings_by_document("d1") == 1
            assert (
                conn.execute(
                    "SELECT COUNT(*) FROM sqlite_master"
                    " WHERE type='table' AND name='embedded_documents'"
                ).fetchone()[0]
                == 0
            )
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

    def test_missing_shadow_degrades_to_unmarked(self) -> None:
        """vec0 present but the shadow absent (legacy read path): unmarked, no raise."""
        conn = _vec0_conn(shadow=False)
        try:
            _insert_vec_row(conn, "d1")
            results = mark_vector_staleness(conn, [_result("d1"), _result("d2")])
            assert all(r.vectors_stale is False for r in results)
        finally:
            conn.close()

    def test_marking_is_bounded_by_the_shadow_not_a_vec0_scan(self) -> None:
        """One display-gate probe plus indexed PK lookups; no table scan.

        The recording connection pins the CORR-06 read contract: marking must
        never reintroduce ``SELECT ... FROM document_embeddings`` (the old
        O(vectors) scan). The shadow read is the derived, rebuildable signal.
        """
        conn = _vec0_conn(document_ids=("d1", "d2"))
        try:
            _seed_embedding(conn, "d1")
            recording = _RecordingConnection(conn)

            results = mark_vector_staleness(recording, [_result("d1"), _result("d2")])

            assert [r.vectors_stale for r in results] == [False, True]
            assert not any("FROM document_embeddings" in sql for sql in recording.statements)
            assert any(
                "SELECT 1 FROM embedded_documents LIMIT 1" in sql for sql in recording.statements
            )
            pk_lookups = sum(
                "SELECT 1 FROM embedded_documents WHERE document_id = ?" in sql
                for sql in recording.statements
            )
            assert pk_lookups == 2
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

    def test_bm25_refreshed_after_embed_doc_is_marked_stale(  # noqa: PLR0915
        self, tmp_path, monkeypatch
    ) -> None:
        """Embed → modify → update_paths purge → the enriched BM25 result is marked.

        The lag state is produced by the REAL purge (update_paths), not by
        raw-SQL "chunks without embeddings" fabrication (RESEARCH Pitfall 3
        warning sign). Enrichment is applied at the entry point (enrich_results),
        matching the single-owner contract: BM25Searcher itself returns raw rows.
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
            # Task 1: the production DDL lands with schema init in Task 2;
            # create the shadow here so the real writer/reader path is
            # exercised on a production-shaped database. Idempotent once the
            # schema owns it.
            db.connection.executescript(
                "CREATE TABLE IF NOT EXISTS embedded_documents ("
                " document_id TEXT PRIMARY KEY,"
                " FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE);"
            )
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
            clean = enrich_results(
                db.connection,
                BM25Searcher(db.connection).search("alpha", SearchOptions(limit=5)),
            )
            assert clean
            assert clean[0].vectors_stale is False

            # Drift: modify a.md, BM25-refresh through the per-path seam —
            # the purge removes ITS embedding and produces the real lag state
            # (b.md's embedding survives, arming the display gate).
            doc_file.write_text("# Alpha changed\n\nalpha needle text v2\n", encoding="utf-8")
            counts = indexer.update_paths(coll, [doc_file])
            assert counts.updated == 1
            assert embedded_document_ids(db.connection) == {keeper.id}

            lagging = enrich_results(
                db.connection,
                BM25Searcher(db.connection).search("alpha", SearchOptions(limit=5)),
            )
            assert lagging
            assert lagging[0].vectors_stale is True
            keeper_hits = enrich_results(
                db.connection,
                BM25Searcher(db.connection).search("beta", SearchOptions(limit=5)),
            )
            assert keeper_hits
            assert keeper_hits[0].vectors_stale is False
        finally:
            db.close()


class TestSearcherDelegation:
    """D-09 single-owner contract: searchers produce, entry points enrich once."""

    def test_searchers_do_not_expose_attach(self) -> None:
        """BM25, vector, and hybrid searchers are pure result producers."""
        assert not hasattr(BM25Searcher(MagicMock()), "_attach_contexts")
        assert not hasattr(VectorSearcher(MagicMock()), "_attach_contexts")
        assert not hasattr(HybridSearcher(MagicMock(), embedder=None), "_attach_contexts")

    def test_each_pipeline_exit_enriches_exactly_once(self, monkeypatch) -> None:
        """BM25, VECTOR, HYDE, and hybrid exits each enrich once with the list."""
        calls: list[tuple[object, list[SearchResult]]] = []

        def recording_enrich(db, results):
            calls.append((db, results))
            return results

        monkeypatch.setattr("sif.search.hybrid.enrich_results", recording_enrich)

        def assert_single_enrichment(pipeline, results, expected) -> None:
            assert results is expected
            assert len(calls) == 1
            assert calls[0][0] is pipeline.db
            assert calls[0][1] is expected

        # BM25 exit
        pipeline = SearchPipeline(MagicMock())
        pipeline.hybrid.bm25 = MagicMock()
        bm25_results = [_result("d-b")]
        pipeline.hybrid.bm25.search.return_value = bm25_results
        assert_single_enrichment(pipeline, pipeline.search("lex: needle"), bm25_results)

        # VECTOR exit
        calls.clear()
        embedder = MagicMock()
        embedder.embed.return_value = [0.1, 0.2]
        pipeline = SearchPipeline(MagicMock(), embedder=embedder)
        pipeline.hybrid.vector = MagicMock()
        vector_results = [_result("d-v")]
        pipeline.hybrid.vector.search.return_value = vector_results
        assert_single_enrichment(pipeline, pipeline.search("vec: needle"), vector_results)

        # HYDE exit
        calls.clear()
        embedder.generate.return_value = "hypothetical document"
        hyde_results = [_result("d-h")]
        pipeline.hybrid.vector.search.return_value = hyde_results
        assert_single_enrichment(pipeline, pipeline.search("hyde: needle"), hyde_results)

        # Hybrid exit (after fusion, rerank, snippets, and the CORR-03 slice).
        # CORR-03 makes the pipeline the slice owner, so enrichment sees the
        # page list built by that slice rather than the raw searcher list.
        calls.clear()
        pipeline = SearchPipeline(MagicMock())
        pipeline.hybrid.search = MagicMock()
        hybrid_results = [_result("d-hy")]
        pipeline.hybrid.search.return_value = hybrid_results
        page = pipeline.search("plain query")
        assert [r.document_id for r in page] == ["d-hy"]
        assert len(calls) == 1
        assert calls[0][0] is pipeline.db
        assert calls[0][1] is page
