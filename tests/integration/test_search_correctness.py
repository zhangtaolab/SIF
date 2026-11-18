"""CORR-03 integration: deterministic pagination on every query path.

Every path runs against one real DB (SchemaManager FTS triggers + vec0), so a
page is compared against the same-window request — ``limit=l offset=o`` must
equal the ``[o:o+l]`` slice of ``limit=o+l offset=0`` (research Pitfall 11) —
and the reranker candidate-cap interaction is proven on real rows.
"""

from __future__ import annotations

import sqlite3

import pytest

from sif.core.models import SearchOptions, SearchResult
from sif.database.schema import SchemaManager
from sif.search.bm25 import BM25Searcher
from sif.search.hybrid import HybridSearcher, SearchPipeline
from sif.search.vector import VectorSearcher
from tests.support.bench import EMBEDDING_DIM, ConceptEmbedder


def _build_search_db() -> sqlite3.Connection:
    """40 distinct single-chunk documents: FTS via triggers, one vec0 row each.

    Content repeats "alpha" 1-5 times plus a unique token, so BM25 ranks are
    distinct and ordered, and the deterministic ConceptEmbedder gives every
    document a distinct cosine similarity to the query. One chunk per
    document means there are no duplicate chunk sets.
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

    SchemaManager(conn, embedding_dim=EMBEDDING_DIM).create_all()
    now = "2026-11-15T00:00:00+00:00"
    conn.execute(
        "INSERT INTO collections (id, name, path, include_by_default, created_at, updated_at)"
        " VALUES ('c1', 'notes', '/notes', 1, ?, ?)",
        (now, now),
    )
    embedder = ConceptEmbedder()
    embeddings: list[tuple[str, str, str, list[float]]] = []
    for i in range(40):
        content = " ".join(["alpha"] * (i % 5 + 1)) + f" unique{i} document body {i}"
        conn.execute(
            "INSERT INTO documents (id, collection_id, path, filename, title, content,"
            " checksum, mtime, created_at, updated_at)"
            " VALUES (?, 'c1', ?, ?, ?, ?, ?, 1.0, ?, ?)",
            (
                f"d{i}",
                f"/notes/n{i}.md",
                f"n{i}.md",
                f"Note {i}",
                content,
                f"checksum-{i}",
                now,
                now,
            ),
        )
        conn.execute(
            "INSERT INTO document_chunks (id, document_id, sequence, content, created_at)"
            " VALUES (?, ?, 0, ?, ?)",
            (f"chunk-{i}", f"d{i}", content, now),
        )
        embeddings.append((f"e{i}", f"d{i}", f"chunk-{i}", embedder.embed(content)))
    VectorSearcher(conn, embedding_dim=EMBEDDING_DIM).add_embeddings_batch(embeddings)
    return conn


def _options(**overrides: object) -> SearchOptions:
    """Page options scoped to the fixture collection, highlights off."""
    fields: dict[str, object] = {
        "include_highlights": False,
        "collection_ids": ["c1"],
    }
    fields.update(overrides)
    return SearchOptions(**fields)


def _assert_page_continuity(search, label: str) -> None:
    """The same-window definition, plus global ranks and the past-end page."""
    page = search(_options(limit=3, offset=1))
    window = search(_options(limit=4, offset=0))

    assert [r.document_id for r in page] == [r.document_id for r in window][1:4], label
    assert [r.rank for r in page] == [2, 3, 4], label
    assert len(page) == 3, label
    assert search(_options(limit=3, offset=1000)) == [], label


def _build_chunky_db() -> sqlite3.Connection:
    """One six-chunk document plus fourteen single-chunk documents.

    Every document matches "alpha"; the chunky document's six chunk rows are
    the nearest vectors, so an undeduped vector page at ``limit=10`` would
    return far fewer than ten distinct documents — CORR-02's regression.
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

    SchemaManager(conn, embedding_dim=EMBEDDING_DIM).create_all()
    now = "2026-11-15T00:00:00+00:00"
    conn.execute(
        "INSERT INTO collections (id, name, path, include_by_default, created_at, updated_at)"
        " VALUES ('c1', 'notes', '/notes', 1, ?, ?)",
        (now, now),
    )
    embedder = ConceptEmbedder()
    embeddings: list[tuple[str, str, str, list[float]]] = []

    def add_document(doc_id: str, content: str, chunks: list[tuple[str, int, str]]) -> None:
        conn.execute(
            "INSERT INTO documents (id, collection_id, path, filename, title, content,"
            " checksum, mtime, created_at, updated_at)"
            " VALUES (?, 'c1', ?, ?, ?, ?, ?, 1.0, ?, ?)",
            (
                doc_id,
                f"/notes/{doc_id}.md",
                f"{doc_id}.md",
                f"Doc {doc_id}",
                content,
                f"checksum-{doc_id}",
                now,
                now,
            ),
        )
        for chunk_id, sequence, chunk_content in chunks:
            conn.execute(
                "INSERT INTO document_chunks (id, document_id, sequence, content, created_at)"
                " VALUES (?, ?, ?, ?, ?)",
                (chunk_id, doc_id, sequence, chunk_content, now),
            )
            embeddings.append((f"e-{chunk_id}", doc_id, chunk_id, embedder.embed(chunk_content)))

    add_document(
        "d-chunky",
        "alpha " * 6 + "chunky document",
        [(f"chunk-chunky-{sequence}", sequence, "alpha") for sequence in range(6)],
    )
    for index in range(14):
        content = f"alpha unique{index} document body {index}"
        add_document(f"d{index}", content, [(f"chunk-{index}", 0, content)])

    VectorSearcher(conn, embedding_dim=EMBEDDING_DIM).add_embeddings_batch(embeddings)
    return conn


class TestConsistentPagination:
    """BM25, vector, and hybrid pages are slices of one ranked window."""

    def test_bm25_page_continuity(self) -> None:
        conn = _build_search_db()
        try:
            searcher = BM25Searcher(conn)
            _assert_page_continuity(lambda opts: searcher.search("alpha", opts), "bm25")
        finally:
            conn.close()

    def test_vector_page_continuity(self) -> None:
        conn = _build_search_db()
        try:
            embedder = ConceptEmbedder()
            query_embedding = embedder.embed("alpha")
            searcher = VectorSearcher(conn, embedding_dim=EMBEDDING_DIM)
            _assert_page_continuity(lambda opts: searcher.search(query_embedding, opts), "vector")
        finally:
            conn.close()

    def test_hybrid_page_continuity(self) -> None:
        conn = _build_search_db()
        try:
            embedder = ConceptEmbedder()
            searcher = HybridSearcher(conn, embedder=embedder, embedding_dim=EMBEDDING_DIM)
            _assert_page_continuity(lambda opts: searcher.search("alpha", opts), "hybrid")
        finally:
            conn.close()


class _RecordingReranker:
    """Order-preserving reranker stub: records the window, returns candidates[:top_k]."""

    def __init__(self) -> None:
        self.seen = 0
        self.top_k = -1

    def rerank(
        self,
        _query: str,
        candidates: list[SearchResult],
        top_k: int = 10,
    ) -> list[SearchResult]:
        self.seen = len(candidates)
        self.top_k = top_k
        return candidates[:top_k]


class TestRerankerWindowPagination:
    """The pre-rerank window must hold offset+limit rows when they exist."""

    @staticmethod
    def _pipeline(conn: sqlite3.Connection) -> tuple[SearchPipeline, _RecordingReranker]:
        reranker = _RecordingReranker()
        pipeline = SearchPipeline(
            conn,
            embedder=ConceptEmbedder(),
            reranker=reranker,
            embedding_dim=EMBEDDING_DIM,
        )
        return pipeline, reranker

    def test_two_pages_are_full_disjoint_and_globally_ranked(self) -> None:
        conn = _build_search_db()
        try:
            pipeline, _ = self._pipeline(conn)
            page1 = pipeline.search("alpha", _options(limit=10, offset=0, candidate_limit=20))
            page2 = pipeline.search("alpha", _options(limit=10, offset=10, candidate_limit=20))

            assert len(page1) == 10
            assert len(page2) == 10
            assert [r.rank for r in page1] == list(range(1, 11))
            assert [r.rank for r in page2] == list(range(11, 21))
            assert {r.document_id for r in page1}.isdisjoint({r.document_id for r in page2})
        finally:
            conn.close()

    def test_page_beyond_candidate_cap_is_full(self) -> None:
        """offset+limit > candidate_limit grows the window instead of starving it."""
        conn = _build_search_db()
        try:
            pipeline, reranker = self._pipeline(conn)
            page = pipeline.search("alpha", _options(limit=10, offset=20, candidate_limit=20))

            assert len(page) == 10
            assert [r.rank for r in page] == list(range(21, 31))
            assert reranker.seen == 30
            assert reranker.top_k == 30
        finally:
            conn.close()

    def test_within_cap_pages_concatenate_to_same_window_request(self) -> None:
        conn = _build_search_db()
        try:
            pipeline, _ = self._pipeline(conn)
            window = pipeline.search("alpha", _options(limit=20, offset=0, candidate_limit=20))
            page1 = pipeline.search("alpha", _options(limit=10, offset=0, candidate_limit=20))
            page2 = pipeline.search("alpha", _options(limit=10, offset=10, candidate_limit=20))

            assert [r.document_id for r in page1 + page2] == [r.document_id for r in window]
        finally:
            conn.close()

    def test_offset_zero_still_caps_reranker_input_at_candidate_limit(self) -> None:
        """Phase 16 cap semantics survive: offset=0 hands exactly candidate_limit."""
        conn = _build_search_db()
        try:
            pipeline, reranker = self._pipeline(conn)
            results = pipeline.search("alpha", _options(limit=100, offset=0, candidate_limit=20))

            assert reranker.seen == 20
            assert reranker.top_k == 100
            assert len(results) == 20
        finally:
            conn.close()


class TestChunkyDocumentDedup:
    """CORR-02: a chunky document cannot eat another document's result slot."""

    @staticmethod
    def _vector_search(
        conn: sqlite3.Connection,
    ) -> tuple[VectorSearcher, list[float]]:
        return VectorSearcher(conn, embedding_dim=EMBEDDING_DIM), ConceptEmbedder().embed("alpha")

    def test_vector_limit_ten_returns_ten_distinct_documents(self) -> None:
        """Six matching chunks of one document leave the page at ten documents."""
        conn = _build_chunky_db()
        try:
            searcher, query_embedding = self._vector_search(conn)
            results = searcher.search(query_embedding, _options(limit=10))

            ids = [r.document_id for r in results]
            assert len(ids) == 10
            assert len(set(ids)) == 10
            chunky = next(r for r in results if r.document_id == "d-chunky")
            assert chunky.chunk_matches >= 5
        finally:
            conn.close()

    def test_hybrid_default_limit_ten_returns_ten_distinct_documents(self) -> None:
        """The hybrid default path dedups too and keeps the vector chunk identity."""
        conn = _build_chunky_db()
        try:
            searcher = HybridSearcher(conn, embedder=ConceptEmbedder(), embedding_dim=EMBEDDING_DIM)
            results = searcher.search("alpha", _options(limit=10))

            ids = [r.document_id for r in results]
            assert len(ids) == 10
            assert len(set(ids)) == 10
            chunky = next(r for r in results if r.document_id == "d-chunky")
            assert chunky.chunk_matches >= 5
            assert chunky.chunk_id is not None
        finally:
            conn.close()

    def test_per_chunk_mode_returns_the_chunky_chunk_rows(self) -> None:
        """per_chunk=True addresses every chunk row of the chunky document."""
        conn = _build_chunky_db()
        try:
            searcher, query_embedding = self._vector_search(conn)
            results = searcher.search(query_embedding, _options(limit=100, per_chunk=True))

            chunky = [r for r in results if r.document_id == "d-chunky"]
            assert len(chunky) == 6
            assert {r.sequence for r in chunky} == set(range(6))
            assert all(r.chunk_matches == 0 for r in results if r.chunk_id is not None)
        finally:
            conn.close()

    def test_dedup_aware_page_continuity(self) -> None:
        """Dedup does not break the same-window page definition on either path."""
        conn = _build_chunky_db()
        try:
            searcher, query_embedding = self._vector_search(conn)
            _assert_page_continuity(
                lambda opts: searcher.search(query_embedding, opts), "vector-chunky"
            )

            hybrid = HybridSearcher(conn, embedder=ConceptEmbedder(), embedding_dim=EMBEDDING_DIM)
            _assert_page_continuity(lambda opts: hybrid.search("alpha", opts), "hybrid-chunky")
        finally:
            conn.close()
