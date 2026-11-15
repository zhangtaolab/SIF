"""Tests for vector search."""

import json
import logging
import sqlite3
from unittest.mock import MagicMock

import pytest

from sif.core.filters import parse_filter
from sif.core.models import SearchOptions, SearchResult, canonical_metadata_json
from sif.database.metadata_repository import MetadataValueRepository
from sif.database.schema import SchemaManager
from sif.search import vector as vector_module
from sif.search.context_attach import enrich_results
from sif.search.filters import count_documents_in_scope
from sif.search.vector import VectorSearcher


class _RecordingConnection:
    """Connection proxy recording every statement the searcher executes."""

    def __init__(self, conn: sqlite3.Connection) -> None:
        """Wrap the real connection without changing its behavior."""
        self._conn = conn
        self.calls: list[tuple[str, tuple[object, ...]]] = []

    def execute(self, sql: str, parameters: tuple[object, ...] = ()) -> sqlite3.Cursor:
        """Record the statement, then delegate to the wrapped connection."""
        self.calls.append((sql, tuple(parameters)))
        return self._conn.execute(sql, parameters)

    def __getattr__(self, name: str):
        """Delegate every other connection attribute."""
        return getattr(self._conn, name)


class TestVectorSearcher:
    """Tests for VectorSearcher class."""

    def test_init_raises_when_vec_unavailable(self):
        """Test that init raises RuntimeError when sqlite-vec is unavailable."""
        mock_db = MagicMock()
        mock_db.execute.side_effect = sqlite3.OperationalError("no such function")

        with pytest.raises(RuntimeError, match="sqlite-vec extension is not available"):
            VectorSearcher(mock_db)

    def test_embedding_to_vec_uses_json(self):
        """Test that _embedding_to_vec returns JSON array format."""
        mock_db = MagicMock()
        mock_db.execute.return_value = MagicMock()

        searcher = VectorSearcher(mock_db)
        searcher._vec_available = True

        embedding = [0.1, 0.2, 0.3]
        result = searcher._embedding_to_vec(embedding)

        assert result == "[0.1, 0.2, 0.3]"

    def test_add_embedding_calls_execute_with_vec_f32(self):
        """Test that add_embedding inserts with vec_f32."""
        mock_db = MagicMock()
        mock_db.execute.return_value = MagicMock()

        searcher = VectorSearcher(mock_db)
        searcher._vec_available = True

        searcher.add_embedding("e1", "d1", "c1", [0.1, 0.2])

        calls = mock_db.execute.call_args_list
        assert len(calls) == 2
        sql = calls[1][0][0]
        assert "vec_f32(?)" in sql

    def test_add_embeddings_batch_executes_many(self):
        """Test that add_embeddings_batch uses executemany."""
        mock_db = MagicMock()
        mock_db.execute.return_value = MagicMock()

        searcher = VectorSearcher(mock_db)
        searcher._vec_available = True

        items = [
            ("e1", "d1", "c1", [0.1, 0.2]),
            ("e2", "d2", None, [0.3, 0.4]),
        ]
        searcher.add_embeddings_batch(items)

        mock_db.executemany.assert_called_once()
        call_args = mock_db.executemany.call_args
        sql = call_args[0][0]
        rows = call_args[0][1]

        assert "vec_f32(?)" in sql
        assert len(rows) == 2
        assert rows[0] == ("e1", "d1", "c1", "[0.1, 0.2]")
        assert rows[1] == ("e2", "d2", None, "[0.3, 0.4]")

    def test_add_embeddings_batch_empty_list(self):
        """Test that add_embeddings_batch is a no-op for empty list."""
        mock_db = MagicMock()
        mock_db.execute.return_value = MagicMock()

        searcher = VectorSearcher(mock_db)
        searcher._vec_available = True

        searcher.add_embeddings_batch([])

        mock_db.executemany.assert_not_called()

    def test_search_binds_k_as_parameter(self):
        """WR-03: the KNN limit is bound, never interpolated into the SQL text."""
        mock_db = MagicMock()
        vec_cursor = MagicMock()
        vec_cursor.fetchall.return_value = []
        mock_db.execute.return_value = vec_cursor

        searcher = VectorSearcher(mock_db)
        searcher._vec_available = True

        searcher.search([0.1, 0.2], SearchOptions(limit=5))

        sql = mock_db.execute.call_args[0][0]
        params = mock_db.execute.call_args[0][1]
        assert "k = ?" in sql
        assert "k = 5" not in sql
        # WR-04 over-fetch: fetch_k = max(limit * 4, 50), trimmed after filter
        assert params[1] == 50

    def test_search_clamps_non_positive_limit(self):
        """WR-03: limit <= 0 never reaches sqlite-vec raw and trims to one row."""
        mock_db = MagicMock()
        search_cursor = MagicMock()
        search_cursor.fetchall.return_value = [
            {
                "score": 0.0,
                "document_id": "doc-1",
                "title": "Title",
                "path": "/path",
                "collection_name": "col",
            },
            {
                "score": 0.2,
                "document_id": "doc-2",
                "title": "Title2",
                "path": "/path2",
                "collection_name": "col",
            },
        ]
        # vec_version() in __init__, then the search query. Rich results
        # would otherwise have triggered the old searcher-level attach.
        mock_db.execute.side_effect = [MagicMock(), search_cursor]

        searcher = VectorSearcher(mock_db)
        searcher._vec_available = True

        results = searcher.search([0.1, 0.2], SearchOptions(limit=-1))

        # search is the second execute call (after the vec_version probe)
        search_call = mock_db.execute.call_args_list[1]
        params = search_call[0][1]
        assert params[1] == 50  # fetch floor
        assert len(results) == 1  # trim clamped to 1
        assert results[0].rank == 1

    def test_search_with_collection_ids(self):
        """Test search includes collection filter."""
        mock_db = MagicMock()
        vec_cursor = MagicMock()
        vec_cursor.fetchall.return_value = []
        count_cursor = MagicMock()
        count_cursor.fetchone.return_value = (5,)

        def _execute(sql: str, _params=()):
            # D-08: a collection-only search issues three scoped COUNT
            # statements (pre-count, denominator, vector count) before KNN.
            return count_cursor if "COUNT(*)" in sql else vec_cursor

        mock_db.execute.side_effect = _execute

        searcher = VectorSearcher(mock_db)
        searcher._vec_available = True

        options = SearchOptions(collection_ids=["col-1", "col-2"])
        searcher.search([0.1, 0.2], options)

        sql = mock_db.execute.call_args[0][0]
        params = mock_db.execute.call_args[0][1]

        assert "collection_id IN" in sql
        assert "col-1" in params
        assert "col-2" in params

    def test_search_converts_distance_to_score(self):
        """Test search converts sqlite-vec distance to 0-1 score."""
        mock_db = MagicMock()
        vec_cursor = MagicMock()
        doc_cursor = MagicMock()
        doc_cursor.fetchall.return_value = [
            {
                "score": 0.0,
                "document_id": "doc-1",
                "title": "Title",
                "path": "/path",
                "collection_name": "col",
            },
        ]
        mock_db.execute.side_effect = [vec_cursor, doc_cursor]

        searcher = VectorSearcher(mock_db)
        searcher._vec_available = True

        results = searcher.search([0.1, 0.2])

        assert len(results) == 1
        assert results[0].score == pytest.approx(1.0)
        assert results[0].document_id == "doc-1"

    def test_search_applies_min_score(self):
        """Test search filters by min_score."""
        mock_db = MagicMock()
        vec_cursor = MagicMock()
        doc_cursor = MagicMock()
        doc_cursor.fetchall.return_value = [
            {
                "score": 0.0,
                "document_id": "doc-1",
                "title": "Title",
                "path": "/path",
                "collection_name": "col",
            },
            {
                "score": 1.8,
                "document_id": "doc-2",
                "title": "Title2",
                "path": "/path2",
                "collection_name": "col",
            },
        ]
        mock_db.execute.side_effect = [vec_cursor, doc_cursor]

        searcher = VectorSearcher(mock_db)
        searcher._vec_available = True

        options = SearchOptions(min_score=0.5)
        results = searcher.search([0.1, 0.2], options)

        assert len(results) == 1
        assert results[0].document_id == "doc-1"

    def test_search_includes_content(self):
        """Test search includes document content when requested."""
        mock_db = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [
            {
                "score": 0.0,
                "document_id": "doc-1",
                "title": "Title",
                "path": "/path",
                "collection_name": "col",
            },
        ]
        content_cursor = MagicMock()
        content_cursor.fetchone.return_value = ("document content",)
        # vec_version() in __init__, search query, then content lookup.
        mock_db.execute.side_effect = [
            MagicMock(),
            mock_cursor,
            content_cursor,
        ]

        searcher = VectorSearcher(mock_db)
        searcher._vec_available = True

        options = SearchOptions(include_content=True)
        results = searcher.search([0.1, 0.2], options)

        assert len(results) == 1
        assert results[0].content == "document content"


class TestVectorFilteredRecall:
    """WR-04: collection-filtered searches must not under-return.

    k bounds the vec0 MATCH, which sqlite-vec resolves before the JOIN applies
    the collection filter — a tight k returns only globally-nearest rows, so
    filtering afterwards can leave a collection's strong matches unseen.
    """

    def _build_db(self) -> sqlite3.Connection:
        import sqlite_vec

        conn = sqlite3.connect(":memory:")
        conn.row_factory = sqlite3.Row
        try:
            conn.enable_load_extension(True)
            sqlite_vec.load(conn)
            conn.enable_load_extension(False)
        except Exception:
            pytest.skip("sqlite-vec not available")

        conn.execute(
            "CREATE TABLE documents "
            "(id TEXT PRIMARY KEY, collection_id TEXT, title TEXT, path TEXT)"
        )
        conn.execute("CREATE TABLE collections (id TEXT PRIMARY KEY, name TEXT)")
        conn.execute("""
            CREATE TABLE contexts (
                id TEXT PRIMARY KEY, target_id TEXT NOT NULL, context_type TEXT NOT NULL,
                content TEXT NOT NULL, created_at TEXT NOT NULL, updated_at TEXT NOT NULL
            )
        """)
        # The KNN SELECT LEFT JOINs document_chunks for chunk identity
        # (CORR-02); these legacy rows have no chunk rows, so both fields
        # resolve to None via the LEFT JOIN.
        conn.execute("""
            CREATE TABLE document_chunks (
                id TEXT PRIMARY KEY, document_id TEXT NOT NULL, sequence INTEGER NOT NULL,
                content TEXT NOT NULL, created_at TEXT NOT NULL
            )
        """)
        conn.execute("""
            CREATE VIRTUAL TABLE document_embeddings USING vec0(
                embedding_id TEXT PRIMARY KEY,
                document_id TEXT NOT NULL,
                chunk_id TEXT,
                embedding FLOAT[2]
            )
        """)
        conn.execute("INSERT INTO collections VALUES ('c1', 'one'), ('c2', 'two')")
        # Three c1 rows closest to the query [1, 0]; the two c2 rows — the
        # filter's target — sit just behind them in global distance order.
        rows = [
            ("e1", "d1", "c1", [1.0, 0.1], "c1"),
            ("e2", "d2", "c1", [1.0, 0.2], "c1"),
            ("e3", "d3", "c1", [1.0, 0.3], "c1"),
            ("e4", "d4", "c2", [1.0, 0.4], "c2"),
            ("e5", "d5", "c2", [1.0, 0.5], "c2"),
        ]
        for _eid, did, _cid, _vec, coll in rows:
            conn.execute("INSERT INTO documents VALUES (?, ?, 'T', ?)", (did, coll, f"/{did}.md"))
        searcher = VectorSearcher(conn, embedding_dim=2)
        searcher.add_embeddings_batch([(eid, did, cid, vec) for eid, did, cid, vec, _ in rows])
        return conn

    def test_collection_filter_returns_matches_beyond_knn_limit(self) -> None:
        """The two c2 matches are globally ranks 4-5; a tight k=2 would hide them."""
        conn = self._build_db()
        try:
            searcher = VectorSearcher(conn, embedding_dim=2)
            results = searcher.search([1.0, 0.0], SearchOptions(limit=2, collection_ids=["c2"]))

            assert [r.document_id for r in results] == ["d4", "d5"]
            assert [r.rank for r in results] == [1, 2]
        finally:
            conn.close()

    def test_unfiltered_search_keeps_top_limit_ordering(self) -> None:
        """Unfiltered searches return the same globally-nearest rows as before."""
        conn = self._build_db()
        try:
            searcher = VectorSearcher(conn, embedding_dim=2)
            results = searcher.search([1.0, 0.0], SearchOptions(limit=3))

            assert [r.document_id for r in results] == ["d1", "d2", "d3"]
            assert [r.rank for r in results] == [1, 2, 3]
        finally:
            conn.close()

    # ------------------------------------------------------------------
    # D-08/D-09: pre-count seeding, the corrected stop condition, and the
    # too-selective notice. Every raw fixture below that a metadata-filtered
    # case uses creates the production kv tables and seeds typed rows; the
    # collection-only fixture needs only documents/embeddings.
    # ------------------------------------------------------------------

    @staticmethod
    def _vec_conn() -> sqlite3.Connection:
        """Minimal real vec0 schema shared by the filtered-recall fixtures."""
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
            "CREATE TABLE documents "
            "(id TEXT PRIMARY KEY, collection_id TEXT, title TEXT, path TEXT)"
        )
        conn.execute("CREATE TABLE collections (id TEXT PRIMARY KEY, name TEXT)")
        conn.execute("""
            CREATE TABLE document_chunks (
                id TEXT PRIMARY KEY, document_id TEXT NOT NULL, sequence INTEGER NOT NULL,
                content TEXT NOT NULL, created_at TEXT NOT NULL
            )
        """)
        conn.execute("""
            CREATE VIRTUAL TABLE document_embeddings USING vec0(
                embedding_id TEXT PRIMARY KEY,
                document_id TEXT NOT NULL,
                chunk_id TEXT,
                embedding FLOAT[2]
            )
        """)
        return conn

    def _build_tagged_db(self, count: int, tagged: set[int]) -> sqlite3.Connection:
        """``count`` single-vector documents; indexes in ``tagged`` carry tag=rare."""
        conn = self._vec_conn()
        SchemaManager(conn)._create_metadata_tables()
        conn.execute("INSERT INTO collections VALUES ('c1', 'one')")
        repo = MetadataValueRepository(conn)
        embeddings: list[tuple[str, str, str, list[float]]] = []
        for index in range(count):
            doc_id = f"d{index}"
            conn.execute(
                "INSERT INTO documents VALUES (?, 'c1', 'T', ?)",
                (doc_id, f"/{doc_id}.md"),
            )
            tag = "rare" if index in tagged else "common"
            repo.replace_from_canonical(doc_id, canonical_metadata_json({"tag": tag}))
            embeddings.append((f"e{index}", doc_id, f"{doc_id}-chunk", [1.0, index * 0.001]))
        VectorSearcher(conn, embedding_dim=2).add_embeddings_batch(embeddings)
        conn.commit()
        return conn

    def _build_two_collection_db(self) -> sqlite3.Connection:
        """100 documents; the two c2 documents sit at the farthest distances."""
        conn = self._vec_conn()
        conn.execute("INSERT INTO collections VALUES ('c1', 'one'), ('c2', 'two')")
        embeddings: list[tuple[str, str, str, list[float]]] = []
        for index in range(100):
            doc_id = f"d{index}"
            collection = "c2" if index >= 98 else "c1"
            conn.execute(
                "INSERT INTO documents VALUES (?, ?, 'T', ?)",
                (doc_id, collection, f"/{doc_id}.md"),
            )
            embeddings.append((f"e{index}", doc_id, f"{doc_id}-chunk", [1.0, index * 0.001]))
        VectorSearcher(conn, embedding_dim=2).add_embeddings_batch(embeddings)
        return conn

    def _build_per_chunk_db(self) -> sqlite3.Connection:
        """Five tagged documents (seven chunks) plus five untagged ones (45 chunks).

        The nearest 50 vectors hold six of the seven tagged chunks; the fifth
        tagged document's only chunk is global rank 51, so a row-count
        saturation test would stop one batch early.
        """
        conn = self._vec_conn()
        SchemaManager(conn)._create_metadata_tables()
        conn.execute("INSERT INTO collections VALUES ('c1', 'one')")
        repo = MetadataValueRepository(conn)
        embeddings: list[tuple[str, str, str, list[float]]] = []
        tagged_chunks = {
            "d-a": [0.01, 0.02],
            "d-b": [0.03, 0.04],
            "d-c": [0.05],
            "d-d": [0.06],
            "d-e": [0.60],
        }
        for doc_id, distances in tagged_chunks.items():
            conn.execute(
                "INSERT INTO documents VALUES (?, 'c1', 'T', ?)",
                (doc_id, f"/{doc_id}.md"),
            )
            repo.replace_from_canonical(doc_id, canonical_metadata_json({"tag": "hit"}))
            for ordinal, distance in enumerate(distances):
                embeddings.append(
                    (f"e-{doc_id}-{ordinal}", doc_id, f"{doc_id}-chunk", [1.0, distance])
                )

        untagged = [f"d-x{index}" for index in range(5)]
        for doc_id in untagged:
            conn.execute(
                "INSERT INTO documents VALUES (?, 'c1', 'T', ?)",
                (doc_id, f"/{doc_id}.md"),
            )
            repo.replace_from_canonical(doc_id, canonical_metadata_json({"tag": "miss"}))
        # Ranks 7-50 are 44 untagged chunks; the 45th untagged chunk is last.
        untagged_distances = [0.10 + 0.01 * index for index in range(44)] + [0.61]
        for index, distance in enumerate(untagged_distances):
            doc_id = untagged[index % len(untagged)]
            embeddings.append((f"e-x{index}", doc_id, f"{doc_id}-chunk{index}", [1.0, distance]))
        VectorSearcher(conn, embedding_dim=2).add_embeddings_batch(embeddings)
        conn.commit()
        return conn

    def test_collection_only_search_returns_all_matching_documents(self, caplog) -> None:
        """The measured bug: a 2-document collection over 100 docs returns both."""
        conn = self._build_two_collection_db()
        try:
            assert count_documents_in_scope(conn, ["c2"]) == 2
            searcher = VectorSearcher(conn, embedding_dim=2)
            with caplog.at_level(logging.WARNING):
                results = searcher.search(
                    [1.0, 0.0], SearchOptions(limit=10, collection_ids=["c2"])
                )

            assert [r.document_id for r in results] == ["d98", "d99"]
            assert [r.rank for r in results] == [1, 2]
            # Collection-only searches are not metadata selectivity; never warn.
            assert "highly selective" not in caplog.text
        finally:
            conn.close()

    def test_two_percent_selectivity_returns_every_match(self) -> None:
        """A 2 % tag filter (4 of 200) returns those four documents, never [].

        The old post-JOIN saturation test stopped on batch one and returned an
        empty page; the pre-count seed and the all-matches target close it.
        """
        conn = self._build_tagged_db(200, {100, 120, 140, 160})
        try:
            searcher = VectorSearcher(conn, embedding_dim=2)
            filter_node = parse_filter({"field": "tag", "operator": "eq", "value": "rare"})
            results = searcher.search([1.0, 0.0], SearchOptions(limit=10, filter=filter_node))

            assert {r.document_id for r in results} == {"d100", "d120", "d140", "d160"}
            assert len(results) == 4
        finally:
            conn.close()

    def test_empty_match_returns_empty_before_any_knn(self) -> None:
        """A filter matching nothing returns [] and never reaches the KNN."""
        conn = self._build_tagged_db(20, {0})
        try:
            searcher = VectorSearcher(conn, embedding_dim=2)
            recorder = _RecordingConnection(conn)
            searcher.db = recorder
            filter_node = parse_filter(
                {"field": "no_such_key", "operator": "exists", "value": True}
            )
            results = searcher.search([1.0, 0.0], SearchOptions(limit=10, filter=filter_node))

            assert results == []
            assert not any("MATCH" in sql for sql, _ in recorder.calls)
            assert any("COUNT(*)" in sql for sql, _ in recorder.calls)
        finally:
            conn.close()

    def test_per_chunk_mode_sees_every_matching_document(self) -> None:
        """Distinct-document counting (not row counting) ends escalation.

        Six of the seven tagged chunks arrive in the first batch; only the
        distinct-document test keeps escalating until the fifth tagged
        document (global rank 51) is seen.
        """
        conn = self._build_per_chunk_db()
        try:
            searcher = VectorSearcher(conn, embedding_dim=2)
            filter_node = parse_filter({"field": "tag", "operator": "eq", "value": "hit"})
            results = searcher.search(
                [1.0, 0.0],
                SearchOptions(limit=20, per_chunk=True, filter=filter_node),
            )

            assert {r.document_id for r in results} == {"d-a", "d-b", "d-c", "d-d", "d-e"}
            assert len(results) == 7
            assert len([r for r in results if r.document_id == "d-a"]) == 2
        finally:
            conn.close()

    def test_too_selective_notice_fires_once_with_formatted_counts(
        self, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Ceiling exhausted with a short page: one notice with reached/of/requested."""
        monkeypatch.setattr(vector_module, "_MAX_FETCH_K", 8)
        conn = self._build_tagged_db(20, {3, 4, 5, 10, 11, 12, 13, 14, 15, 16})
        try:
            searcher = VectorSearcher(conn, embedding_dim=2)
            filter_node = parse_filter({"field": "tag", "operator": "eq", "value": "rare"})
            with caplog.at_level(logging.WARNING):
                results = searcher.search([1.0, 0.0], SearchOptions(limit=10, filter=filter_node))

            notices = [
                record for record in caplog.records if "highly selective" in record.getMessage()
            ]
            assert len(notices) == 1
            # The three %d placeholders must match their arguments: reached
            # (3 nearest tagged docs), matching total (10), requested (10).
            assert "3 of 10 matching documents reached, 10 requested" in caplog.text
            assert len(results) == 3
        finally:
            conn.close()

    def test_short_page_below_page_target_logs_no_notice(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        """A filter matching fewer documents than requested is an honest short page."""
        conn = self._build_tagged_db(200, {100, 120, 140, 160})
        try:
            searcher = VectorSearcher(conn, embedding_dim=2)
            filter_node = parse_filter({"field": "tag", "operator": "eq", "value": "rare"})
            with caplog.at_level(logging.WARNING):
                results = searcher.search([1.0, 0.0], SearchOptions(limit=10, filter=filter_node))

            assert len(results) == 4
            assert "highly selective" not in caplog.text
        finally:
            conn.close()

    def test_all_matches_found_logs_no_notice(self, caplog: pytest.LogCaptureFixture) -> None:
        """Recall is complete even though the page is short: no notice."""
        conn = self._build_tagged_db(30, set(range(20)))
        try:
            searcher = VectorSearcher(conn, embedding_dim=2)
            filter_node = parse_filter({"field": "tag", "operator": "eq", "value": "rare"})
            with caplog.at_level(logging.WARNING):
                results = searcher.search([1.0, 0.0], SearchOptions(limit=10, filter=filter_node))

            assert len(results) == 10
            assert "highly selective" not in caplog.text
        finally:
            conn.close()

    def test_unfiltered_unscoped_path_issues_only_the_pre_change_statement(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        """The byte-identical default: one KNN statement, no pre-count, no warning."""
        conn = self._build_db()
        try:
            searcher = VectorSearcher(conn, embedding_dim=2)
            recorder = _RecordingConnection(conn)
            searcher.db = recorder
            with caplog.at_level(logging.WARNING):
                results = searcher.search([1.0, 0.0], SearchOptions(limit=3))

            assert [r.document_id for r in results] == ["d1", "d2", "d3"]
            assert len(recorder.calls) == 1
            sql, params = recorder.calls[0]
            assert "MATCH" in sql
            assert "COUNT(*)" not in sql
            assert params == (json.dumps([1.0, 0.0]), 50)
            assert "highly selective" not in caplog.text
        finally:
            conn.close()


class TestVectorOffsetPagination:
    """CORR-03: fetch_k scales with limit+offset, one slice, global ranks."""

    @staticmethod
    def _build_db() -> sqlite3.Connection:
        """Real vec0 DB with 6 single-chunk documents at distinct distances."""
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
            "CREATE TABLE documents"
            " (id TEXT PRIMARY KEY, collection_id TEXT, title TEXT, path TEXT)"
        )
        conn.execute("CREATE TABLE collections (id TEXT PRIMARY KEY, name TEXT)")
        # Chunk-identity join target for the KNN SELECT (CORR-02). One chunk
        # row per document (sequence 0), so the dedup path sees single-row
        # groups and ranks stay exactly as before.
        conn.execute("""
            CREATE TABLE document_chunks (
                id TEXT PRIMARY KEY, document_id TEXT NOT NULL, sequence INTEGER NOT NULL,
                content TEXT NOT NULL, created_at TEXT NOT NULL
            )
        """)
        conn.execute("""
            CREATE VIRTUAL TABLE document_embeddings USING vec0(
                embedding_id TEXT PRIMARY KEY,
                document_id TEXT NOT NULL,
                chunk_id TEXT,
                embedding FLOAT[2]
            )
        """)
        conn.execute("INSERT INTO collections VALUES ('c1', 'notes')")
        # Query [1, 0]: L2 distance grows with the y component, so the ids
        # sort d0..d5 by similarity.
        vectors = [[1.0, 0.0], [1.0, 0.1], [1.0, 0.2], [1.0, 0.3], [1.0, 0.4], [1.0, 0.5]]
        for i in range(len(vectors)):
            conn.execute(
                "INSERT INTO documents VALUES (?, 'c1', ?, ?)",
                (f"d{i}", f"Doc {i}", f"/d{i}.md"),
            )
            conn.execute(
                "INSERT INTO document_chunks VALUES (?, ?, 0, 'body', '2026-11-15')",
                (f"c{i}", f"d{i}"),
            )
        searcher = VectorSearcher(conn, embedding_dim=2)
        searcher.add_embeddings_batch(
            [(f"e{i}", f"d{i}", f"c{i}", vec) for i, vec in enumerate(vectors)]
        )
        return conn

    @staticmethod
    def _mock_searcher() -> tuple[VectorSearcher, MagicMock]:
        mock_db = MagicMock()
        cursor = MagicMock()
        cursor.fetchall.return_value = []
        mock_db.execute.return_value = cursor
        searcher = VectorSearcher(mock_db)
        searcher._vec_available = True
        return searcher, mock_db

    def test_fetch_k_scales_with_limit_plus_offset(self) -> None:
        """fetch_k = max((limit+offset)*4, 50), not limit*4."""
        searcher, mock_db = self._mock_searcher()

        searcher.search([0.1, 0.2], SearchOptions(limit=10, offset=10))

        params = mock_db.execute.call_args[0][1]
        assert params[1] == 80

    def test_fetch_k_is_capped_for_huge_offsets(self) -> None:
        """A huge offset is a bounded fetch: _MAX_FETCH_K, then an empty page."""
        searcher, mock_db = self._mock_searcher()

        results = searcher.search([0.1, 0.2], SearchOptions(limit=10, offset=1_000_000))

        params = mock_db.execute.call_args[0][1]
        assert params[1] == 2048
        assert results == []

    def test_page_continuity_and_global_ranks(self) -> None:
        """limit=l offset=o equals [o:o+l] of limit=o+l offset=0; ranks are global."""
        conn = self._build_db()
        try:
            searcher = VectorSearcher(conn, embedding_dim=2)
            page = searcher.search([1.0, 0.0], SearchOptions(limit=2, offset=2))
            window = searcher.search([1.0, 0.0], SearchOptions(limit=4, offset=0))

            assert [r.document_id for r in page] == [r.document_id for r in window][2:4]
            assert [r.document_id for r in page] == ["d2", "d3"]
            assert [r.rank for r in page] == [3, 4]
        finally:
            conn.close()

    def test_offset_past_end_returns_empty_page(self) -> None:
        """A past-the-end offset is an empty page, never an error."""
        conn = self._build_db()
        try:
            searcher = VectorSearcher(conn, embedding_dim=2)

            assert searcher.search([1.0, 0.0], SearchOptions(limit=2, offset=50)) == []
        finally:
            conn.close()


class TestVectorDocumentDedup:
    """CORR-02: default output is one row per document, with chunk identity.

    Vector search operates on chunk embeddings, so one chunky document can
    consume many result slots; before CORR-02 a ``limit=10`` page could return
    fewer than ten distinct documents. The best-distance row now represents
    its document, carries that chunk's ``chunk_id``/``sequence``, and
    ``chunk_matches`` counts the rows that collapsed.
    """

    @staticmethod
    def _build_db(
        documents: list[tuple[str, list[tuple[str, int, list[float]]]]],
    ) -> sqlite3.Connection:
        """Real vec0 DB from (doc_id, [(chunk_id, sequence, vector), ...])."""
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
            "CREATE TABLE documents"
            " (id TEXT PRIMARY KEY, collection_id TEXT, title TEXT, path TEXT)"
        )
        conn.execute("CREATE TABLE collections (id TEXT PRIMARY KEY, name TEXT)")
        conn.execute("""
            CREATE TABLE document_chunks (
                id TEXT PRIMARY KEY, document_id TEXT NOT NULL, sequence INTEGER NOT NULL,
                content TEXT NOT NULL, created_at TEXT NOT NULL
            )
        """)
        conn.execute("""
            CREATE VIRTUAL TABLE document_embeddings USING vec0(
                embedding_id TEXT PRIMARY KEY,
                document_id TEXT NOT NULL,
                chunk_id TEXT,
                embedding FLOAT[2]
            )
        """)
        conn.execute("INSERT INTO collections VALUES ('c1', 'notes')")
        embeddings: list[tuple[str, str, str, list[float]]] = []
        for doc_id, chunks in documents:
            conn.execute(
                "INSERT INTO documents VALUES (?, 'c1', ?, ?)",
                (doc_id, f"Doc {doc_id}", f"/{doc_id}.md"),
            )
            for chunk_id, sequence, vector in chunks:
                conn.execute(
                    "INSERT INTO document_chunks VALUES (?, ?, ?, 'body', '2026-11-15')",
                    (chunk_id, doc_id, sequence),
                )
                embeddings.append((f"e-{chunk_id}", doc_id, chunk_id, vector))
        VectorSearcher(conn, embedding_dim=2).add_embeddings_batch(embeddings)
        return conn

    def test_duplicate_chunks_collapse_to_one_row_with_match_count(self) -> None:
        """Three chunks of one document yield one row with chunk_matches=3."""
        conn = self._build_db(
            [
                (
                    "d1",
                    [
                        ("c0", 0, [1.0, 0.0]),
                        ("c1", 1, [1.0, 0.1]),
                        ("c2", 2, [1.0, 0.2]),
                    ],
                )
            ]
        )
        try:
            results = VectorSearcher(conn, embedding_dim=2).search(
                [1.0, 0.0], SearchOptions(limit=10)
            )

            assert [r.document_id for r in results] == ["d1"]
            assert results[0].chunk_id == "c0"
            assert results[0].sequence == 0
            assert results[0].chunk_matches == 3
        finally:
            conn.close()

    def test_best_distance_chunk_wins_identity(self) -> None:
        """The winning row is the nearest chunk, not the first-inserted one."""
        conn = self._build_db(
            [
                (
                    "d1",
                    [
                        ("c0", 0, [1.0, 0.30]),
                        ("c1", 1, [1.0, 0.10]),
                        ("c2", 2, [1.0, 0.00]),
                    ],
                )
            ]
        )
        try:
            results = VectorSearcher(conn, embedding_dim=2).search(
                [1.0, 0.0], SearchOptions(limit=10)
            )

            assert results[0].chunk_id == "c2"
            assert results[0].sequence == 2
            assert results[0].chunk_matches == 3
        finally:
            conn.close()

    @staticmethod
    def _chunky_corpus() -> list[tuple[str, list[tuple[str, int, list[float]]]]]:
        """One five-chunk document plus twelve single-chunk documents."""
        documents: list[tuple[str, list[tuple[str, int, list[float]]]]] = [
            (
                "d-chunky",
                [(f"chunky-{sequence}", sequence, [1.0, sequence * 0.01]) for sequence in range(5)],
            )
        ]
        documents.extend(
            (f"d{index}", [(f"single-{index}", 0, [1.0, 0.5 + index * 0.1])]) for index in range(12)
        )
        return documents

    def test_five_chunk_document_yields_ten_distinct_documents(self) -> None:
        """A chunky document cannot shrink a limit=10 page below ten documents."""
        conn = self._build_db(self._chunky_corpus())
        try:
            results = VectorSearcher(conn, embedding_dim=2).search(
                [1.0, 0.0], SearchOptions(limit=10)
            )

            ids = [r.document_id for r in results]
            assert len(ids) == 10
            assert len(set(ids)) == 10
            assert "d-chunky" in ids
            chunky = next(r for r in results if r.document_id == "d-chunky")
            assert chunky.chunk_matches == 5
            assert chunky.chunk_id == "chunky-0"
        finally:
            conn.close()

    def test_per_chunk_mode_returns_ungrouped_chunk_rows(self) -> None:
        """per_chunk=True keeps the chunk rows and leaves chunk_matches at 0."""
        conn = self._build_db(self._chunky_corpus())
        try:
            results = VectorSearcher(conn, embedding_dim=2).search(
                [1.0, 0.0], SearchOptions(limit=10, per_chunk=True)
            )

            assert len(results) == 10
            assert all(r.chunk_id is not None for r in results)
            assert all(r.chunk_matches == 0 for r in results)
            chunky = [r for r in results if r.document_id == "d-chunky"]
            assert len(chunky) == 5
            assert {r.chunk_id for r in chunky} == {f"chunky-{i}" for i in range(5)}
            assert {r.sequence for r in chunky} == set(range(5))
        finally:
            conn.close()

    @staticmethod
    def _escalating_searcher(
        requested: list[int], distinct_documents: int = 1
    ) -> tuple[VectorSearcher, MagicMock]:
        """Mock searcher whose KNN batch is always exactly fetch_k rows."""
        mock_db = MagicMock()
        cursor = MagicMock()
        cursor.fetchall.return_value = []
        mock_db.execute.return_value = cursor
        searcher = VectorSearcher(mock_db)
        searcher._vec_available = True

        def _execute(_sql, params):
            fetch_k = params[1]
            requested.append(fetch_k)
            batch = MagicMock()
            batch.fetchall.return_value = [
                {
                    "document_id": f"d{row % distinct_documents}",
                    "title": "T",
                    "path": f"/d{row}.md",
                    "collection_name": "c",
                    "score": 0.0,
                    "chunk_id": f"c{row}",
                    "sequence": row,
                }
                for row in range(fetch_k)
            ]
            return batch

        mock_db.execute.side_effect = _execute
        return searcher, mock_db

    def test_escalation_stops_at_the_ceiling(self) -> None:
        """A saturated batch below target doubles fetch_k up to, never past, 2048."""
        requested: list[int] = []
        searcher, _ = self._escalating_searcher(requested)

        results = searcher.search([0.1, 0.2], SearchOptions(limit=10))

        assert requested == [50, 100, 200, 400, 800, 1600, 2048]
        assert max(requested) == 2048
        # All rows belong to one document, so the page still carries its row.
        assert len(results) == 1
        assert results[0].chunk_matches == 2048

    def test_no_escalation_when_first_batch_satisfies_target(self) -> None:
        """The first batch already yielding the target runs exactly one KNN query."""
        requested: list[int] = []
        searcher, _ = self._escalating_searcher(requested, distinct_documents=10)

        results = searcher.search([0.1, 0.2], SearchOptions(limit=10))

        assert requested == [50]
        assert len(results) == 10

    def test_legacy_null_chunk_identity_is_none(self) -> None:
        """Rows without chunk identity (legacy/dangling) yield None/None."""
        mock_db = MagicMock()
        cursor = MagicMock()
        cursor.fetchall.return_value = []
        mock_db.execute.return_value = cursor
        searcher = VectorSearcher(mock_db)
        searcher._vec_available = True

        batch = MagicMock()
        batch.fetchall.return_value = [
            {
                "document_id": "d1",
                "title": "T",
                "path": "/d1.md",
                "collection_name": "c",
                "score": 0.0,
                "chunk_id": None,
                "sequence": None,
            }
        ]
        mock_db.execute.side_effect = [batch]

        results = searcher.search([0.1, 0.2], SearchOptions(limit=10))

        assert results[0].chunk_id is None
        assert results[0].sequence is None
        assert results[0].chunk_matches == 1

    def test_to_dict_includes_chunk_identity(self) -> None:
        """SearchResult.to_dict() carries all three new fields."""
        payload = SearchResult(
            document_id="d1",
            title="T",
            path="/d1.md",
            collection_name="c",
            score=1.0,
            chunk_id="c1",
            sequence=2,
            chunk_matches=3,
        ).to_dict()

        assert payload["chunk_id"] == "c1"
        assert payload["sequence"] == 2
        assert payload["chunk_matches"] == 3


class TestVectorEmbeddingDeletion:
    """Tests for delete_embeddings_by_document and get_embedded_chunk_ids."""

    def test_delete_embeddings_by_document_executes_parameterized_delete(self) -> None:
        """Test delete runs a DELETE keyed only by the document-id placeholder."""
        mock_db = MagicMock()
        cursor = MagicMock()
        cursor.rowcount = 3
        mock_db.execute.return_value = cursor

        searcher = VectorSearcher(mock_db)
        searcher._vec_available = True

        removed = searcher.delete_embeddings_by_document("d1")

        assert removed == 3
        call = mock_db.execute.call_args
        sql = call[0][0]
        assert "DELETE FROM document_embeddings" in sql
        assert "document_id = ?" in sql
        assert call[0][1] == ("d1",)
        # Threat T-03-08-02: the id is never interpolated into the SQL text.
        assert "d1" not in sql

    def test_get_embedded_chunk_ids_returns_non_none_set(self) -> None:
        """Test get_embedded_chunk_ids returns the set of non-None chunk ids."""
        mock_db = MagicMock()
        cursor = MagicMock()
        cursor.fetchall.return_value = [("c1",), ("c2",), (None,)]
        mock_db.execute.return_value = cursor

        searcher = VectorSearcher(mock_db)
        searcher._vec_available = True

        result = searcher.get_embedded_chunk_ids("d1")

        call = mock_db.execute.call_args
        sql = call[0][0]
        assert "SELECT chunk_id FROM document_embeddings" in sql
        assert "document_id = ?" in sql
        assert call[0][1] == ("d1",)
        assert "d1" not in sql
        assert isinstance(result, set)
        assert result == {"c1", "c2"}

    def test_delete_embeddings_by_document_on_real_vec0(self) -> None:
        """Test on a real vec0 table: exactly the target document's rows are removed."""
        import sqlite_vec

        conn = sqlite3.connect(":memory:")
        conn.row_factory = sqlite3.Row
        try:
            try:
                conn.enable_load_extension(True)
                sqlite_vec.load(conn)
                conn.enable_load_extension(False)
            except Exception:
                pytest.skip("sqlite-vec not available")
            conn.execute(
                """
                CREATE VIRTUAL TABLE document_embeddings USING vec0(
                    embedding_id TEXT PRIMARY KEY,
                    document_id TEXT NOT NULL,
                    chunk_id TEXT,
                    embedding FLOAT[2]
                )
                """,
            )
            searcher = VectorSearcher(conn, embedding_dim=2)
            searcher.add_embeddings_batch(
                [
                    ("e1", "d1", "c1", [1.0, 0.0]),
                    ("e2", "d1", "c2", [0.0, 1.0]),
                    ("e3", "d2", "c3", [1.0, 1.0]),
                ],
            )

            removed = searcher.delete_embeddings_by_document("d1")

            assert removed == 2
            remaining = conn.execute("SELECT document_id FROM document_embeddings").fetchall()
            assert [row["document_id"] for row in remaining] == ["d2"]
            assert searcher.get_embedded_chunk_ids("d1") == set()
            assert searcher.get_embedded_chunk_ids("d2") == {"c3"}
        finally:
            conn.close()

    def test_get_all_embedded_chunk_ids_groups_and_skips_none(self) -> None:
        """Batch read: one unfiltered SELECT grouped by document, NULL chunk ids skipped."""
        mock_db = MagicMock()
        cursor = MagicMock()
        cursor.__iter__.return_value = iter(
            [("d1", "c1"), ("d1", "c2"), ("d1", None), ("d2", "c3")]
        )
        mock_db.execute.return_value = cursor

        searcher = VectorSearcher(mock_db)
        searcher._vec_available = True
        # Drop the constructor's vec_version probe so the call history below
        # is the batch method's alone.
        mock_db.execute.reset_mock()
        mock_db.execute.return_value = cursor

        result = searcher.get_all_embedded_chunk_ids()

        call = mock_db.execute.call_args
        sql = call[0][0]
        assert "SELECT document_id, chunk_id FROM document_embeddings" in sql
        assert "WHERE" not in sql
        assert call[0][1:] == ()
        mock_db.execute.assert_called_once()
        assert result == {"d1": {"c1", "c2"}, "d2": {"c3"}}

    def test_get_all_embedded_chunk_ids_matches_per_document_lookup_on_real_vec0(self) -> None:
        """On a real vec0 table the batch map equals the per-document lookup."""
        import sqlite_vec

        conn = sqlite3.connect(":memory:")
        conn.row_factory = sqlite3.Row
        try:
            try:
                conn.enable_load_extension(True)
                sqlite_vec.load(conn)
                conn.enable_load_extension(False)
            except Exception:
                pytest.skip("sqlite-vec not available")
            conn.execute(
                """
                CREATE VIRTUAL TABLE document_embeddings USING vec0(
                    embedding_id TEXT PRIMARY KEY,
                    document_id TEXT NOT NULL,
                    chunk_id TEXT,
                    embedding FLOAT[2]
                )
                """,
            )
            searcher = VectorSearcher(conn, embedding_dim=2)
            # No NULL chunk_id row here: sqlite-vec v0.1.9 rejects NULL for a
            # TEXT metadata column on both INSERT and UPDATE, so such rows
            # cannot exist in a production table on this version. The NULL-skip
            # contract of both lookup forms is pinned by the mock tests above.
            searcher.add_embeddings_batch(
                [
                    ("e1", "d1", "c1", [1.0, 0.0]),
                    ("e2", "d1", "c2", [0.0, 1.0]),
                    ("e3", "d2", "c3", [0.0, 0.0]),
                ],
            )

            batch_result = searcher.get_all_embedded_chunk_ids()

            assert batch_result == {"d1": {"c1", "c2"}, "d2": {"c3"}}
            for doc_id in ("d1", "d2"):
                assert batch_result[doc_id] == searcher.get_embedded_chunk_ids(doc_id)
        finally:
            conn.close()


class TestVectorSearcherEnrichmentContract:
    """The vector searcher is a pure producer; enrichment happens at the exit."""

    @staticmethod
    def _result() -> SearchResult:
        return SearchResult(
            document_id="doc-1",
            title="T1",
            path="/1.md",
            collection_name="c",
            score=1.0,
            rank=1,
        )

    def test_search_returns_raw_results_without_enrichment(self) -> None:
        """search() returns raw results and never runs a contexts/embedding scan."""
        search_rows = [
            {
                "score": 0.0,
                "document_id": "doc-1",
                "title": "T1",
                "path": "/1.md",
                "collection_name": "c",
            },
        ]
        mock_db = MagicMock()
        search_cursor = MagicMock()
        search_cursor.fetchall.return_value = search_rows
        # vec_version() in __init__, then the search query only.
        mock_db.execute.side_effect = [MagicMock(), search_cursor]

        searcher = VectorSearcher(mock_db)
        searcher._vec_available = True

        results = searcher.search([0.1, 0.2], SearchOptions(include_highlights=False))

        assert len(results) == 1
        assert results[0].context_description is None
        assert results[0].vectors_stale is False
        assert not hasattr(searcher, "_attach_contexts")
        assert mock_db.execute.call_count == 2

    def test_enrich_results_attaches_context_description(self) -> None:
        """The shared enrichment helper fills context descriptions once."""
        mock_db = MagicMock()
        context_cursor = MagicMock()
        context_cursor.fetchall.return_value = [
            {"target_id": "/1.md", "content": "Important project notes"}
        ]
        staleness_cursor = MagicMock()
        mock_db.execute.side_effect = [context_cursor, staleness_cursor]

        results = enrich_results(mock_db, [self._result()])

        assert results[0].context_description == "Important project notes"

    def test_enrich_results_no_context_returns_none(self) -> None:
        """No stored context leaves context_description None."""
        mock_db = MagicMock()
        context_cursor = MagicMock()
        context_cursor.fetchall.return_value = []
        staleness_cursor = MagicMock()
        mock_db.execute.side_effect = [context_cursor, staleness_cursor]

        results = enrich_results(mock_db, [self._result()])

        assert results[0].context_description is None
