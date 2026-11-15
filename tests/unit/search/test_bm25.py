"""Tests for BM25 search strategy."""

import contextlib
import sqlite3
from unittest.mock import MagicMock

import pytest

from sif.core.models import SearchOptions, SearchResult
from sif.search.bm25 import _CONTENT_WEIGHT, _TITLE_WEIGHT, BM25Searcher
from sif.search.context_attach import enrich_results


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
            ],
        )
        searcher = BM25Searcher(mock_db)
        options = SearchOptions(include_highlights=False)
        results = searcher.search("test query", options)

        assert len(results) == 1
        assert results[0].document_id == "doc-1"
        # Searchers no longer enrich: the FTS query is the only DB access.
        calls = mock_db.execute.call_args_list
        sqls = [call[0][0] for call in calls]
        assert len(sqls) == 1
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
            ],
        )

        searcher = BM25Searcher(mock_db)
        options = SearchOptions(include_highlights=False)
        results = searcher.search("test query", options)

        assert isinstance(results, list)
        assert len(results) == 2
        assert all(isinstance(r, SearchResult) for r in results)

    def test_search_applies_min_score(self) -> None:
        """min_score is a bound SQL predicate, not a post-pagination Python skip."""
        # row["score"] is the FTS rank (lower = better), converted to
        # score = 1/(1+|rank|). The SQL — not this loop — applies min_score.
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
            ],
        )

        searcher = BM25Searcher(mock_db)
        options = SearchOptions(min_score=0.3, include_highlights=False)
        results = searcher.search("test query", options)

        sql = mock_db.execute.call_args[0][0]
        params = mock_db.execute.call_args[0][1]
        # FTS5: score >= m  <=>  rank >= 1 - 1/m (research Pitfall 4). The
        # naive inverse 1/m - 1 has the wrong direction. Position 0/1 are the
        # bound content/title weights, position 2 the MATCH query, position 3
        # the weighted-expression threshold.
        assert "m.score >= ?" in sql
        assert params[3] == pytest.approx(1.0 - 1.0 / 0.3)
        assert params[:2] == [_CONTENT_WEIGHT, _TITLE_WEIGHT]
        # Both returned rows survive: the threshold travelled to SQL.
        assert [r.document_id for r in results] == ["doc-1", "doc-2"]

    def test_search_min_score_zero_omits_the_threshold_filter(self) -> None:
        """min_score=0 binds no threshold and preserves the pre-change row set."""
        mock_db = self._make_mock_db(
            [
                {
                    "document_id": "doc-1",
                    "title": "T1",
                    "path": "/1.md",
                    "collection_name": "c",
                    "score": -5.0,
                },
            ],
        )

        searcher = BM25Searcher(mock_db)
        options = SearchOptions(min_score=0.0, include_highlights=False)
        results = searcher.search("test query", options)

        sql = mock_db.execute.call_args[0][0]
        params = mock_db.execute.call_args[0][1]
        assert "m.score >=" not in sql
        assert params == [_CONTENT_WEIGHT, _TITLE_WEIGHT, '"test"* AND "query"*', 10, 0]
        assert [r.document_id for r in results] == ["doc-1"]

    def test_search_ranks_are_global_across_pages(self) -> None:
        """Page ranks are options.offset + position (D-06 global numbering)."""
        mock_db = self._make_mock_db(
            [
                {
                    "document_id": "doc-6",
                    "title": "T6",
                    "path": "/6.md",
                    "collection_name": "c",
                    "score": -1.0,
                },
                {
                    "document_id": "doc-7",
                    "title": "T7",
                    "path": "/7.md",
                    "collection_name": "c",
                    "score": -2.0,
                },
            ],
        )

        searcher = BM25Searcher(mock_db)
        options = SearchOptions(limit=2, offset=5, include_highlights=False)
        results = searcher.search("test query", options)

        assert [r.rank for r in results] == [6, 7]

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
            ],
        )
        content_cursor = MagicMock()
        content_cursor.fetchone.return_value = ["document content"]
        mock_db.execute.side_effect = [
            mock_db.execute.return_value,
            content_cursor,
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
            ],
        )
        chunk_cursor = MagicMock()
        chunk_cursor.fetchall.return_value = []
        content_cursor = MagicMock()
        content_cursor.fetchone.return_value = ["test query content"]
        mock_db.execute.side_effect = [
            mock_db.execute.return_value,
            chunk_cursor,
            content_cursor,
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
            ],
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
        assert query == '"hello"*'

    def test_build_fts_query_multiple_terms(self) -> None:
        """Test FTS query building for multiple terms."""
        searcher = BM25Searcher(MagicMock())
        query = searcher._build_fts_query("hello world")
        assert query == '"hello"* AND "world"*'

    def test_build_fts_query_empty(self) -> None:
        """Test FTS query building for queries with no usable terms."""
        searcher = BM25Searcher(MagicMock())
        assert searcher._build_fts_query("") == '""'
        assert searcher._build_fts_query("   ") == '""'
        assert searcher._build_fts_query('":*()"') == '""'

    def test_build_fts_query_sanitizes_metacharacters(self) -> None:
        """Common punctuation must not be parsed as FTS5 syntax."""
        searcher = BM25Searcher(MagicMock())
        assert searcher._build_fts_query("e-mail") == '"e-mail"*'
        assert searcher._build_fts_query("don't") == '"don\'t"*'
        assert searcher._build_fts_query("foo:bar") == '"foo bar"*'
        assert searcher._build_fts_query("a AND") == '"a"* AND "AND"*'

    def test_build_fts_query_output_is_valid_fts5(self) -> None:
        """Built queries must execute against a real FTS5 table."""
        with contextlib.closing(sqlite3.connect(":memory:")) as conn:
            conn.execute(
                "CREATE VIRTUAL TABLE docs_fts_probe USING fts5(content, tokenize='porter')"
            )
            conn.execute(
                "INSERT INTO docs_fts_probe(content) VALUES (?)", ("the e-mail about c++",)
            )
            searcher = BM25Searcher(MagicMock())

            # Every input here previously produced sqlite3.OperationalError.
            for raw in [
                "e-mail",
                "don't",
                "c++",
                "foo:bar",
                "(paren)",
                "a AND",
                '"quote',
                "OR",
                "NEAR",
                "NOT",
                "hello",
                "",
            ]:
                fts_query = searcher._build_fts_query(raw)
                conn.execute(
                    "SELECT rowid FROM docs_fts_probe WHERE docs_fts_probe MATCH ? ORDER BY rank",
                    (fts_query,),
                ).fetchall()

    def test_build_fts_query_metacharacter_input_finds_documents(self) -> None:
        """Sanitized queries still match the documents they should."""
        with contextlib.closing(sqlite3.connect(":memory:")) as conn:
            conn.execute(
                "CREATE VIRTUAL TABLE docs_fts_probe USING fts5(content, tokenize='porter')"
            )
            conn.execute(
                "INSERT INTO docs_fts_probe(content) VALUES (?)",
                ("the e-mail about c++ and don't stop",),
            )
            searcher = BM25Searcher(MagicMock())

            for raw in ("e-mail", "c++", "don't"):
                fts_query = searcher._build_fts_query(raw)
                rows = conn.execute(
                    "SELECT rowid FROM docs_fts_probe WHERE docs_fts_probe MATCH ?",
                    (fts_query,),
                ).fetchall()
                assert rows, f"query {raw!r} -> {fts_query!r} matched nothing"


def _build_real_fts_db() -> sqlite3.Connection:
    """Real FTS5 + documents/collections tables with a non-trivial rank spread.

    Five documents contain "apple" with increasing repetition (1, 2, 4, 8, 16
    occurrences) across a 40-document corpus, so their bm25 ranks span roughly
    -2.9..-3.6 — *not* near zero, which is what makes a threshold-direction
    bug visible (research Pitfall 4). Thirty-five filler documents contain
    unrelated words. Both tables are inserted in the same order so FTS rowids
    line up with ``documents.rowid``.
    """
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute("CREATE TABLE collections (id TEXT PRIMARY KEY, name TEXT)")
    conn.execute(
        "CREATE TABLE documents (id TEXT PRIMARY KEY, collection_id TEXT, title TEXT, path TEXT)"
    )
    conn.execute("CREATE VIRTUAL TABLE documents_fts USING fts5(content, title)")
    conn.execute("INSERT INTO collections VALUES ('c1', 'notes'), ('c2', 'other')")
    for i, repeats in enumerate((1, 2, 4, 8, 16)):
        conn.execute(
            "INSERT INTO documents VALUES (?, 'c1', ?, ?)",
            (f"doc-{i}", f"Note {i}", f"/n{i}.md"),
        )
        conn.execute(
            "INSERT INTO documents_fts(content) VALUES (?)",
            (" ".join(["apple"] * repeats),),
        )
    for i in range(35):
        conn.execute(
            "INSERT INTO documents VALUES (?, 'c2', ?, ?)",
            (f"fill-{i}", f"Filler {i}", f"/f{i}.md"),
        )
        conn.execute(
            "INSERT INTO documents_fts(content) VALUES (?)",
            (f"banana filler document number {i}",),
        )
    return conn


class TestBM25OffsetPagination:
    """CORR-03: offset pages are slices of one filtered, globally ranked list."""

    @staticmethod
    def _options(
        *,
        limit: int = 10,
        offset: int = 0,
        min_score: float = 0.0,
        collection_ids: list[str] | None = None,
    ) -> SearchOptions:
        return SearchOptions(
            limit=limit,
            offset=offset,
            min_score=min_score,
            collection_ids=collection_ids,
            include_highlights=False,
        )

    def test_scoped_and_unfiltered_branches_page_identically(self) -> None:
        """Both SQL branches paginate and number ranks globally (D-06)."""
        conn = _build_real_fts_db()
        try:
            searcher = BM25Searcher(conn)
            scoped = searcher.search(
                "apple", self._options(limit=2, offset=1, collection_ids=["c1"])
            )
            unfiltered = searcher.search("apple", self._options(limit=2, offset=1))

            expected = ["doc-3", "doc-2"]
            assert [r.document_id for r in scoped] == expected
            assert [r.document_id for r in unfiltered] == expected
            assert [r.rank for r in scoped] == [2, 3]
            assert [r.rank for r in unfiltered] == [2, 3]
        finally:
            conn.close()

    def test_page_continuity_against_same_window_request(self) -> None:
        """limit=l offset=o equals the [o:o+l] slice of limit=o+l offset=0."""
        conn = _build_real_fts_db()
        try:
            searcher = BM25Searcher(conn)
            page = searcher.search("apple", self._options(limit=2, offset=1, collection_ids=["c1"]))
            window = searcher.search(
                "apple", self._options(limit=3, offset=0, collection_ids=["c1"])
            )

            assert [r.document_id for r in page] == [r.document_id for r in window][1:3]
            assert [r.rank for r in page] == [2, 3]
        finally:
            conn.close()

    def test_offset_past_end_returns_empty_page(self) -> None:
        """A past-the-end offset is an empty page, never an error."""
        conn = _build_real_fts_db()
        try:
            searcher = BM25Searcher(conn)
            results = searcher.search(
                "apple", self._options(limit=10, offset=1000, collection_ids=["c1"])
            )

            assert results == []
        finally:
            conn.close()

    def test_mid_min_score_keeps_expected_documents_and_direction(self) -> None:
        """A mid min_score filters inside SQL: the highest-score docs survive.

        The code's score convention is 1/(1+|rank|), so rank >= 1 - 1/m is
        what keeps score >= m (not the naive 1/m - 1). FTS5 orders by rank
        ascending, so the surviving rows are the least-repeated "apple" docs;
        the wrong direction keeps all five, so "all" would fail here.
        """
        conn = _build_real_fts_db()
        try:
            searcher = BM25Searcher(conn)
            results = searcher.search("apple", self._options(min_score=0.23, collection_ids=["c1"]))

            assert [r.document_id for r in results] == ["doc-2", "doc-1", "doc-0"]
            assert all(r.score >= 0.23 for r in results)
            assert [r.rank for r in results] == [1, 2, 3]
        finally:
            conn.close()

    def test_min_score_applies_before_offset_with_global_ranks(self) -> None:
        """The page slices the filtered list, so rank 2 is the filtered second row."""
        conn = _build_real_fts_db()
        try:
            searcher = BM25Searcher(conn)
            page = searcher.search(
                "apple",
                self._options(limit=1, offset=1, min_score=0.23, collection_ids=["c1"]),
            )

            # Post-pagination filtering would have returned rank 1 here.
            assert [r.document_id for r in page] == ["doc-1"]
            assert [r.rank for r in page] == [2]
        finally:
            conn.close()


def _build_title_body_db() -> sqlite3.Connection:
    """Two-column FTS corpus where a raised title weight flips the ranking.

    ``d-title`` matches the query only through its title and ``d-body`` only
    through five body repetitions; 48 unrelated fillers raise the term's IDF
    so both weighted ranks are O(1). At the default 1.0/1.0 the body match
    wins (more term occurrences); at a raised title weight the title match
    moves ahead. ``needle``/``needl`` are the query/title stem pair.
    """
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute("CREATE TABLE collections (id TEXT PRIMARY KEY, name TEXT)")
    conn.execute(
        "CREATE TABLE documents (id TEXT PRIMARY KEY, collection_id TEXT, title TEXT, path TEXT)"
    )
    conn.execute("CREATE VIRTUAL TABLE documents_fts USING fts5(content, title, tokenize='porter')")
    conn.execute("INSERT INTO collections VALUES ('c1', 'notes')")
    documents = [
        ("d-title", "Needle", "/t.md", "ordinary words here"),
        ("d-body", "Other Title", "/b.md", " ".join(["needle"] * 5)),
    ]
    documents.extend(
        (f"fill-{i}", f"Filler {i}", f"/f{i}.md", f"unrelated banana filler number {i}")
        for i in range(48)
    )
    # Insert into both tables in the same order so rowids stay aligned.
    for doc_id, title, path, content in documents:
        conn.execute("INSERT INTO documents VALUES (?, 'c1', ?, ?)", (doc_id, title, path))
        conn.execute("INSERT INTO documents_fts(content, title) VALUES (?, ?)", (content, title))
    return conn


class TestWeightedBM25:
    """CORR-04: bound bm25(documents_fts, content_weight, title_weight)."""

    def test_both_sql_branches_bind_weighted_bm25(self) -> None:
        """Scoped and unfiltered branches bind weights; nothing is interpolated."""
        for collection_ids in (["col-1"], None):
            mock_db = MagicMock()
            mock_db.execute.return_value.fetchall.return_value = []
            searcher = BM25Searcher(mock_db)
            searcher.search(
                "test",
                SearchOptions(collection_ids=collection_ids, include_highlights=False),
            )

            sql = mock_db.execute.call_args[0][0]
            params = mock_db.execute.call_args[0][1]
            assert "bm25(documents_fts, ?, ?)" in sql
            assert "rank" not in sql
            assert params[:2] == [_CONTENT_WEIGHT, _TITLE_WEIGHT]

    def test_1_0_1_0_reproduces_rank_exactly_on_real_corpus(self) -> None:
        """bm25(documents_fts, 1.0, 1.0) equals the unweighted rank column."""
        conn = _build_real_fts_db()
        try:
            pairs = conn.execute(
                "SELECT rank, bm25(documents_fts, 1.0, 1.0) AS weighted "
                "FROM documents_fts WHERE documents_fts MATCH ? ORDER BY rank",
                ('"apple"*',),
            ).fetchall()
            assert len(pairs) == 5
            assert all(pair["rank"] == pair["weighted"] for pair in pairs)

            expected_ids = [
                row[0]
                for row in conn.execute(
                    "SELECT d.id FROM documents_fts "
                    "JOIN documents d ON documents_fts.rowid = d.rowid "
                    "WHERE documents_fts MATCH ? ORDER BY rank",
                    ('"apple"*',),
                ).fetchall()
            ]
            expected_scores = [1.0 / (1.0 + abs(pair["rank"])) for pair in pairs]

            searcher = BM25Searcher(conn)
            scoped = searcher.search(
                "apple", SearchOptions(collection_ids=["c1"], include_highlights=False)
            )
            unfiltered = searcher.search("apple", SearchOptions(include_highlights=False))
            for results in (scoped, unfiltered):
                assert [r.document_id for r in results] == expected_ids
                assert [r.score for r in results] == pytest.approx(expected_scores)
        finally:
            conn.close()

    def test_raised_title_weight_reorders_title_only_above_body_only(self) -> None:
        """A title-only match outranks a stronger body-only match once weighted."""
        conn = _build_title_body_db()
        try:
            searcher = BM25Searcher(conn)
            baseline = searcher.search(
                "needle",
                SearchOptions(collection_ids=["c1"], title_weight=1.0, include_highlights=False),
            )
            title_forward = searcher.search(
                "needle",
                SearchOptions(collection_ids=["c1"], title_weight=10.0, include_highlights=False),
            )

            assert [r.document_id for r in baseline] == ["d-body", "d-title"]
            assert [r.document_id for r in title_forward] == ["d-title", "d-body"]
        finally:
            conn.close()

    def test_default_title_weight_resolves_to_module_constant(self) -> None:
        """The pinned constant, None, and an explicit 1.0 all agree."""
        conn = _build_title_body_db()
        try:
            searcher = BM25Searcher(conn)
            implicit = searcher.search(
                "needle",
                SearchOptions(collection_ids=["c1"], include_highlights=False),
            )
            explicit_none = searcher.search(
                "needle",
                SearchOptions(collection_ids=["c1"], title_weight=None, include_highlights=False),
            )
            explicit_constant = searcher.search(
                "needle",
                SearchOptions(
                    collection_ids=["c1"],
                    title_weight=_TITLE_WEIGHT,
                    include_highlights=False,
                ),
            )

            assert _CONTENT_WEIGHT == 1.0
            assert _TITLE_WEIGHT == 1.0
            key = [(r.document_id, r.score) for r in implicit]
            assert [(r.document_id, r.score) for r in explicit_none] == key
            assert [(r.document_id, r.score) for r in explicit_constant] == key
        finally:
            conn.close()

    def test_pinned_title_weight_is_the_measured_d12_value(self) -> None:
        """D-12 rejected the 2-4x band against B1, so the shipped value is 1.0.

        The 19-09 sweep graded 2.0/3.0/4.0 through ``compare_saved_run`` on
        B1's exact saved query set: the held-out title leg was already at its
        bare ``rank`` ceiling (no rank moved) and the body held-out leg stayed
        flat, so no candidate met the strict per-leg gate. Changing this
        constant requires a new recorded verdict, never a source-only edit.
        """
        assert _CONTENT_WEIGHT == 1.0
        assert _TITLE_WEIGHT == 1.0

    def test_min_score_thresholds_the_weighted_expression_before_pagination(self) -> None:
        """The same threshold separates the weighted ranks differently per weight."""
        conn = _build_title_body_db()
        try:
            searcher = BM25Searcher(conn)
            # rank threshold = -5.6: keeps d-body (-5.25) and drops d-title at
            # title_weight=10 (-6.03), while both survive at weight 1.0
            # (-5.25 / -3.59).
            min_score = 1.0 / 6.6
            weighted = searcher.search(
                "needle",
                SearchOptions(
                    collection_ids=["c1"],
                    title_weight=10.0,
                    min_score=min_score,
                    include_highlights=False,
                ),
            )
            baseline = searcher.search(
                "needle",
                SearchOptions(
                    collection_ids=["c1"],
                    title_weight=1.0,
                    min_score=min_score,
                    include_highlights=False,
                ),
            )

            assert [r.document_id for r in weighted] == ["d-body"]
            assert [r.document_id for r in baseline] == ["d-body", "d-title"]
        finally:
            conn.close()

    def test_search_chunks_sql_is_untouched(self) -> None:
        """Chunk BM25 keeps the plain rank expression and no column weights."""
        mock_db = MagicMock()
        mock_db.execute.return_value.fetchall.return_value = []
        searcher = BM25Searcher(mock_db)
        searcher.search_chunks("test")

        sql = mock_db.execute.call_args[0][0]
        assert "bm25(" not in sql
        assert "rank as score" in sql


class TestBM25SharedTermMatcherHighlights:
    """G-04-1 regressions: highlights via the shared stem-tolerant matcher."""

    def _searcher_with_chunks(self, chunks: list[str]) -> BM25Searcher:
        """Build a BM25Searcher whose document_chunks query returns chunks."""
        mock_db = MagicMock()
        chunk_cursor = MagicMock()
        chunk_cursor.fetchall.return_value = [(c,) for c in chunks]
        mock_db.execute.return_value = chunk_cursor
        return BM25Searcher(mock_db)

    def test_stem_variant_document_gets_highlights(self) -> None:
        """FTS matches stems (rank/token); highlights must too, not come back empty."""
        searcher = self._searcher_with_chunks(
            ["The system ranks documents by token frequency"],
        )
        highlights = searcher._get_highlights("doc-1", "ranking tokens")
        assert highlights
        assert "ranks" in highlights[0]
        assert "token" in highlights[0]

    def test_substring_false_positive_yields_no_highlights(self) -> None:
        """Query table must not highlight a chunk containing only notable."""
        searcher = self._searcher_with_chunks(["...introduced a notable change in..."])
        highlights = searcher._get_highlights("doc-1", "table")
        assert highlights == []

    def test_cjk_per_character_fallback_highlight(self) -> None:
        """CJK query 向量搜索 highlights 向量检索 via shared characters."""
        searcher = self._searcher_with_chunks(["支持 向量检索 能力"])
        highlights = searcher._get_highlights("doc-1", "向量搜索")
        assert highlights
        assert "向量" in highlights[0]


class TestBM25SearcherEnrichmentContract:
    """The searcher is a pure result producer; enrichment is owned at the exit."""

    @staticmethod
    def _search_rows() -> list[dict[str, object]]:
        return [
            {
                "document_id": "doc-1",
                "title": "T1",
                "path": "/1.md",
                "collection_name": "c",
                "score": -1.0,
            },
        ]

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
        """search() returns raw results and never touches contexts/embeddings."""
        mock_db = MagicMock()
        search_cursor = MagicMock()
        search_cursor.fetchall.return_value = self._search_rows()
        mock_db.execute.return_value = search_cursor

        searcher = BM25Searcher(mock_db)
        results = searcher.search("test", SearchOptions(include_highlights=False))

        assert results[0].context_description is None
        assert results[0].vectors_stale is False
        assert not hasattr(searcher, "_attach_contexts")
        # Only the FTS query ran: no contexts scan and no embedding scan.
        assert mock_db.execute.call_count == 1

    def test_enrich_results_attaches_context_description(self) -> None:
        """The shared enrichment helper fills context descriptions once."""
        mock_db = MagicMock()
        context_cursor = MagicMock()
        context_cursor.fetchall.return_value = [
            {"target_id": "/1.md", "content": "Important project notes"}
        ]
        staleness_cursor = MagicMock()
        # Empty shadow: the display gate ends marking after the one probe.
        staleness_cursor.fetchone.return_value = None
        mock_db.execute.side_effect = [context_cursor, staleness_cursor]

        results = enrich_results(mock_db, [self._result()])

        assert results[0].context_description == "Important project notes"

    def test_enrich_results_no_context_returns_none(self) -> None:
        """No stored context leaves context_description None."""
        mock_db = MagicMock()
        context_cursor = MagicMock()
        context_cursor.fetchall.return_value = []
        staleness_cursor = MagicMock()
        staleness_cursor.fetchone.return_value = None
        mock_db.execute.side_effect = [context_cursor, staleness_cursor]

        results = enrich_results(mock_db, [self._result()])

        assert results[0].context_description is None
