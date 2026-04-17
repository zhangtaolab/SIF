"""Tests for vector search."""

import sqlite3
from unittest.mock import MagicMock

import pytest

from docsift.core.models import SearchOptions
from docsift.search.vector import VectorSearcher


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

    def test_search_with_collection_ids(self):
        """Test search includes collection filter."""
        mock_db = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = []
        mock_db.execute.return_value = mock_cursor

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
        mock_db.execute.return_value = mock_cursor

        searcher = VectorSearcher(mock_db)
        searcher._vec_available = True

        results = searcher.search([0.1, 0.2])

        assert len(results) == 1
        assert results[0].score == pytest.approx(1.0)
        assert results[0].document_id == "doc-1"

    def test_search_applies_min_score(self):
        """Test search filters by min_score."""
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
            {
                "score": 1.8,
                "document_id": "doc-2",
                "title": "Title2",
                "path": "/path2",
                "collection_name": "col",
            },
        ]
        mock_db.execute.return_value = mock_cursor

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
        # First execute is vec_version() in __init__, second is search query, third is content lookup, fourth is context lookup
        mock_db.execute.side_effect = [MagicMock(), mock_cursor, content_cursor, context_cursor]

        searcher = VectorSearcher(mock_db)
        searcher._vec_available = True

        options = SearchOptions(include_content=True)
        results = searcher.search([0.1, 0.2], options)

        assert len(results) == 1
        assert results[0].content == "document content"


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
