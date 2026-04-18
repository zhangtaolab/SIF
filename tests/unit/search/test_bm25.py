"""Tests for BM25 search strategy."""

from unittest.mock import MagicMock

from docsift.core.models import SearchOptions, SearchResult
from docsift.search.bm25 import BM25Searcher


class TestBM25Searcher:
    """Tests for BM25Searcher class."""

    def _make_mock_db(self, rows=None):
        mock_db = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = rows or []
        mock_db.execute.return_value = mock_cursor
        return mock_db

    def test_init_stores_db(self) -> None:
        """Test that init stores the db connection."""
        mock_db = MagicMock()
        searcher = BM25Searcher(mock_db)
        assert searcher.db is mock_db

    def test_search_executes_fts_query(self) -> None:
        """Test that search executes FTS query."""
        mock_db = self._make_mock_db(
            [
                {
                    "document_id": "doc-1",
                    "title": "T1",
                    "path": "/1.md",
                    "collection_name": "c",
                    "score": -1.0,
                },
            ]
        )
        # Add a context cursor for the _attach_contexts call
        context_cursor = MagicMock()
        context_cursor.fetchall.return_value = []
        mock_db.execute.side_effect = [
            mock_db.execute.return_value,
            context_cursor,
        ]

        searcher = BM25Searcher(mock_db)
        options = SearchOptions(include_highlights=False)
        results = searcher.search("test query", options)

        assert len(results) == 1
        assert results[0].document_id == "doc-1"
        # The last call is the context query; verify the FTS query was also made
        calls = mock_db.execute.call_args_list
        sqls = [call[0][0] for call in calls]
        assert any("MATCH" in sql for sql in sqls)

    def test_search_returns_search_results(self) -> None:
        """Test that search returns list of SearchResult objects."""
        mock_db = self._make_mock_db(
            [
                {
                    "document_id": "doc-1",
                    "title": "T1",
                    "path": "/1.md",
                    "collection_name": "c",
                    "score": -1.0,
                },
                {
                    "document_id": "doc-2",
                    "title": "T2",
                    "path": "/2.md",
                    "collection_name": "c",
                    "score": -2.0,
                },
            ]
        )
        # Add a context cursor for the _attach_contexts call
        context_cursor = MagicMock()
        context_cursor.fetchall.return_value = []
        mock_db.execute.side_effect = [
            mock_db.execute.return_value,
            context_cursor,
        ]

        searcher = BM25Searcher(mock_db)
        options = SearchOptions(include_highlights=False)
        results = searcher.search("test query", options)

        assert isinstance(results, list)
        assert len(results) == 2
        assert all(isinstance(r, SearchResult) for r in results)

    def test_search_applies_min_score(self) -> None:
        """Test that search applies min_score filtering."""
        # row["score"] is the FTS rank (lower = better), converted to score = 1/(1+|rank|)
        # rank=-1.0 => score=0.5, rank=-5.0 => score=0.167
        mock_db = self._make_mock_db(
            [
                {
                    "document_id": "doc-1",
                    "title": "T1",
                    "path": "/1.md",
                    "collection_name": "c",
                    "score": -1.0,
                },
                {
                    "document_id": "doc-2",
                    "title": "T2",
                    "path": "/2.md",
                    "collection_name": "c",
                    "score": -5.0,
                },
            ]
        )
        # Add a context cursor for the _attach_contexts call
        context_cursor = MagicMock()
        context_cursor.fetchall.return_value = []
        mock_db.execute.side_effect = [
            mock_db.execute.return_value,
            context_cursor,
        ]

        searcher = BM25Searcher(mock_db)
        options = SearchOptions(min_score=0.3, include_highlights=False)
        results = searcher.search("test query", options)

        # Only doc-1 has score >= 0.3 (0.5 >= 0.3, 0.167 < 0.3)
        assert len(results) == 1
        assert results[0].document_id == "doc-1"

    def test_search_with_collection_ids(self) -> None:
        """Test search with specific collection IDs."""
        mock_db = self._make_mock_db([])

        searcher = BM25Searcher(mock_db)
        options = SearchOptions(collection_ids=["col-1", "col-2"], include_highlights=False)
        searcher.search("test query", options)

        sql = mock_db.execute.call_args[0][0]
        assert "collection_id IN" in sql
        params = mock_db.execute.call_args[0][1]
        assert "col-1" in params
        assert "col-2" in params

    def test_search_with_pagination(self) -> None:
        """Test search with offset for pagination."""
        mock_db = self._make_mock_db([])

        searcher = BM25Searcher(mock_db)
        options = SearchOptions(limit=5, offset=10, include_highlights=False)
        searcher.search("test query", options)

        sql = mock_db.execute.call_args[0][1]
        assert sql[-2] == 5  # LIMIT
        assert sql[-1] == 10  # OFFSET

    def test_search_empty_results(self) -> None:
        """Test search returns empty list when no results."""
        mock_db = self._make_mock_db([])

        searcher = BM25Searcher(mock_db)
        options = SearchOptions(include_highlights=False)
        results = searcher.search("test query", options)

        assert results == []

    def test_search_with_content(self) -> None:
        """Test search includes content when requested."""
        mock_db = self._make_mock_db(
            [
                {
                    "document_id": "doc-1",
                    "title": "T1",
                    "path": "/1.md",
                    "collection_name": "c",
                    "score": -1.0,
                },
            ]
        )
        content_cursor = MagicMock()
        content_cursor.fetchone.return_value = ["document content"]
        context_cursor = MagicMock()
        context_cursor.fetchall.return_value = []
        mock_db.execute.side_effect = [
            mock_db.execute.return_value,
            content_cursor,
            context_cursor,
        ]

        searcher = BM25Searcher(mock_db)
        options = SearchOptions(include_content=True, include_highlights=False)
        results = searcher.search("test query", options)

        assert len(results) == 1
        assert results[0].content == "document content"

    def test_search_with_highlights(self) -> None:
        """Test search includes highlights when requested."""
        mock_db = self._make_mock_db(
            [
                {
                    "document_id": "doc-1",
                    "title": "T1",
                    "path": "/1.md",
                    "collection_name": "c",
                    "score": -1.0,
                },
            ]
        )
        chunk_cursor = MagicMock()
        chunk_cursor.fetchall.return_value = []
        content_cursor = MagicMock()
        content_cursor.fetchone.return_value = ["test query content"]
        context_cursor = MagicMock()
        context_cursor.fetchall.return_value = []
        mock_db.execute.side_effect = [
            mock_db.execute.return_value,
            chunk_cursor,
            content_cursor,
            context_cursor,
        ]

        searcher = BM25Searcher(mock_db)
        options = SearchOptions(include_highlights=True)
        results = searcher.search("test query", options)

        assert len(results) == 1
        # Highlights are extracted from content matching query terms
        assert isinstance(results[0].highlights, list)

    def test_search_chunks_returns_tuples(self) -> None:
        """Test search_chunks returns (doc_id, content, score) tuples."""
        mock_db = self._make_mock_db(
            [
                {
                    "document_id": "doc-1",
                    "content": "chunk content",
                    "score": -1.0,
                },
            ]
        )

        searcher = BM25Searcher(mock_db)
        results = searcher.search_chunks("test query")

        assert len(results) == 1
        assert results[0][0] == "doc-1"
        assert results[0][1] == "chunk content"
        assert isinstance(results[0][2], float)

    def test_build_fts_query_single_term(self) -> None:
        """Test FTS query building for single term."""
        searcher = BM25Searcher(MagicMock())
        query = searcher._build_fts_query("hello")
        assert query == "hello*"

    def test_build_fts_query_multiple_terms(self) -> None:
        """Test FTS query building for multiple terms."""
        searcher = BM25Searcher(MagicMock())
        query = searcher._build_fts_query("hello world")
        assert query == "hello* AND world*"

    def test_build_fts_query_empty(self) -> None:
        """Test FTS query building for empty query."""
        searcher = BM25Searcher(MagicMock())
        query = searcher._build_fts_query("")
        assert query == "*"


class TestBM25ContextAttachment:
    """Tests for context_description attachment in BM25 search results."""

    def test_search_attaches_context_description(self) -> None:
        """Test that BM25 search attaches path context descriptions."""
        context_rows = [{"target_id": "/1.md", "content": "Important project notes"}]
        search_rows = [
            {
                "document_id": "doc-1",
                "title": "T1",
                "path": "/1.md",
                "collection_name": "c",
                "score": -1.0,
            },
        ]
        mock_db = MagicMock()
        search_cursor = MagicMock()
        search_cursor.fetchall.return_value = search_rows
        context_cursor = MagicMock()
        context_cursor.fetchall.return_value = context_rows
        mock_db.execute.side_effect = [search_cursor, context_cursor]

        searcher = BM25Searcher(mock_db)
        options = SearchOptions(include_highlights=False)
        results = searcher.search("test", options)

        assert len(results) == 1
        assert results[0].context_description == "Important project notes"

    def test_search_no_context_returns_none(self) -> None:
        """Test that search returns None context_description when no context exists."""
        search_rows = [
            {
                "document_id": "doc-1",
                "title": "T1",
                "path": "/1.md",
                "collection_name": "c",
                "score": -1.0,
            },
        ]
        mock_db = MagicMock()
        search_cursor = MagicMock()
        search_cursor.fetchall.return_value = search_rows
        context_cursor = MagicMock()
        context_cursor.fetchall.return_value = []
        mock_db.execute.side_effect = [search_cursor, context_cursor]

        searcher = BM25Searcher(mock_db)
        options = SearchOptions(include_highlights=False)
        results = searcher.search("test", options)

        assert results[0].context_description is None

    def test_search_attaches_context_with_normalized_path(self) -> None:
        """Test that context matches even with /private/tmp vs /tmp mismatch."""
        # Context stored with user-provided /tmp path
        context_rows = [{"target_id": "/tmp/doc.md", "content": "Project notes"}]
        # Document stored with resolved /private/tmp path (macOS behavior)
        search_rows = [
            {
                "document_id": "doc-1",
                "title": "T1",
                "path": "/private/tmp/doc.md",
                "collection_name": "c",
                "score": -1.0,
            },
        ]
        mock_db = MagicMock()
        search_cursor = MagicMock()
        search_cursor.fetchall.return_value = search_rows
        context_cursor = MagicMock()
        context_cursor.fetchall.return_value = context_rows
        mock_db.execute.side_effect = [search_cursor, context_cursor]

        searcher = BM25Searcher(mock_db)
        options = SearchOptions(include_highlights=False)
        results = searcher.search("test", options)

        assert len(results) == 1
        assert results[0].context_description == "Project notes"
