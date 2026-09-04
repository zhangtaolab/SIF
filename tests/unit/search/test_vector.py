"""Tests for vector search."""

import sqlite3
from unittest.mock import MagicMock

import pytest

from sif.core.models import SearchOptions
from sif.search.vector import VectorSearcher


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
        ctx_cursor = MagicMock()
        ctx_cursor.fetchall.return_value = []
        # vec_version() in __init__, search query, context query
        mock_db.execute.side_effect = [MagicMock(), search_cursor, ctx_cursor]

        searcher = VectorSearcher(mock_db)
        searcher._vec_available = True

        results = searcher.search([0.1, 0.2], SearchOptions(limit=-1))

        # call_args is the context query; the search call is the second one
        search_call = mock_db.execute.call_args_list[1]
        params = search_call[0][1]
        assert params[1] == 50  # fetch floor
        assert len(results) == 1  # trim clamped to 1
        assert results[0].rank == 1

    def test_search_with_collection_ids(self):
        """Test search includes collection filter."""
        mock_db = MagicMock()
        vec_cursor = MagicMock()
        doc_cursor = MagicMock()
        doc_cursor.fetchall.return_value = []
        ctx_cursor = MagicMock()
        ctx_cursor.fetchall.return_value = []
        mock_db.execute.side_effect = [vec_cursor, doc_cursor, ctx_cursor]

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
        ctx_cursor = MagicMock()
        ctx_cursor.fetchall.return_value = []
        mock_db.execute.side_effect = [vec_cursor, doc_cursor, ctx_cursor]

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
        ctx_cursor = MagicMock()
        ctx_cursor.fetchall.return_value = []
        mock_db.execute.side_effect = [vec_cursor, doc_cursor, ctx_cursor]

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
        context_cursor = MagicMock()
        context_cursor.fetchall.return_value = []
        # First execute is vec_version() in __init__, second is search query,
        # third is content lookup, fourth is context lookup
        mock_db.execute.side_effect = [MagicMock(), mock_cursor, content_cursor, context_cursor]

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


class TestVectorContextAttachment:
    """Tests for context_description attachment in vector search results."""

    def test_search_attaches_context_description(self) -> None:
        """Test that vector search attaches path context descriptions."""
        context_rows = [{"target_id": "/1.md", "content": "Important project notes"}]
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
        context_cursor = MagicMock()
        context_cursor.fetchall.return_value = context_rows
        # vec_version in __init__, search query, context query
        mock_db.execute.side_effect = [MagicMock(), search_cursor, context_cursor]

        searcher = VectorSearcher(mock_db)
        searcher._vec_available = True

        options = SearchOptions(include_highlights=False)
        results = searcher.search([0.1, 0.2], options)

        assert len(results) == 1
        assert results[0].context_description == "Important project notes"

    def test_search_no_context_returns_none(self) -> None:
        """Test that vector search returns None context_description when no context exists."""
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
        context_cursor = MagicMock()
        context_cursor.fetchall.return_value = []
        # vec_version in __init__, search query, context query
        mock_db.execute.side_effect = [MagicMock(), search_cursor, context_cursor]

        searcher = VectorSearcher(mock_db)
        searcher._vec_available = True

        options = SearchOptions(include_highlights=False)
        results = searcher.search([0.1, 0.2], options)

        assert results[0].context_description is None

    def test_search_attaches_context_with_normalized_path(self) -> None:
        """Test that context matches even with /private/tmp vs /tmp mismatch."""
        # Context stored with user-provided /tmp path
        context_rows = [{"target_id": "/tmp/doc.md", "content": "Project notes"}]
        # Document stored with resolved /private/tmp path (macOS behavior)
        search_rows = [
            {
                "score": 0.0,
                "document_id": "doc-1",
                "title": "T1",
                "path": "/private/tmp/doc.md",
                "collection_name": "c",
            },
        ]
        mock_db = MagicMock()
        search_cursor = MagicMock()
        search_cursor.fetchall.return_value = search_rows
        context_cursor = MagicMock()
        context_cursor.fetchall.return_value = context_rows
        # vec_version in __init__, search query, context query
        mock_db.execute.side_effect = [MagicMock(), search_cursor, context_cursor]

        searcher = VectorSearcher(mock_db)
        searcher._vec_available = True

        options = SearchOptions(include_highlights=False)
        results = searcher.search([0.1, 0.2], options)

        assert len(results) == 1
        assert results[0].context_description == "Project notes"
