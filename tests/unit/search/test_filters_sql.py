"""Byte-identical default and compiler SQL tests for metadata filters (Plan 20-01).

The module constants below were captured from the PRE-CHANGE implementation of
``BM25Searcher.search`` (HEAD ``4f63835``, before the Phase 20 filter slot was
added) through a recording connection. They are the golden: the unfiltered
path must issue exactly this statement and parameter list, so a filtered-only
behavior can never leak into the default path (byte-identical-defaults
culture, D-08/Pitfall 11).

Task 3 of plan 20-01 extends this module with the full per-operator compiler
battery; the recording connection and fixture below are shared by both.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Sequence

from sif.core.models import SearchOptions
from sif.database.schema import SchemaManager
from sif.search.bm25 import BM25Searcher


_HEAD_UNFILTERED_SQL = (
    "\n"
    "                WITH matched AS MATERIALIZED (\n"
    "                    SELECT rowid, bm25(documents_fts, ?, ?) AS score\n"
    "                    FROM documents_fts\n"
    "                    WHERE documents_fts MATCH ?\n"
    "                )\n"
    "                SELECT\n"
    "                    d.id as document_id,\n"
    "                    d.title,\n"
    "                    d.path,\n"
    "                    c.name as collection_name,\n"
    "                    m.score as score\n"
    "                FROM matched m\n"
    "                JOIN documents d ON m.rowid = d.rowid\n"
    "                JOIN collections c ON d.collection_id = c.id\n"
    "                WHERE 1 = 1 \n"
    "                ORDER BY m.score\n"
    "                LIMIT ? OFFSET ?\n"
    "            "
)
_HEAD_UNFILTERED_PARAMS = [1.0, 1.0, '"python"*', 10, 0]

_HEAD_SCOPED_SQL = (
    "\n"
    "                WITH matched AS MATERIALIZED (\n"
    "                    SELECT rowid, bm25(documents_fts, ?, ?) AS score\n"
    "                    FROM documents_fts\n"
    "                    WHERE documents_fts MATCH ?\n"
    "                )\n"
    "                SELECT\n"
    "                    d.id as document_id,\n"
    "                    d.title,\n"
    "                    d.path,\n"
    "                    c.name as collection_name,\n"
    "                    m.score as score\n"
    "                FROM matched m\n"
    "                JOIN documents d ON m.rowid = d.rowid\n"
    "                JOIN collections c ON d.collection_id = c.id\n"
    "                WHERE 1 = 1 AND d.collection_id IN (?) \n"
    "                ORDER BY m.score\n"
    "                LIMIT ? OFFSET ?\n"
    "            "
)
_HEAD_SCOPED_PARAMS = [1.0, 1.0, '"python"*', "c1", 10, 0]


class _RecordingConnection:
    """Connection proxy recording every statement BM25Searcher executes."""

    def __init__(self, conn: sqlite3.Connection) -> None:
        """Wrap a real connection and capture ``(sql, params)`` pairs."""
        self.conn = conn
        self.calls: list[tuple[str, Sequence[object]]] = []

    def execute(self, sql: str, parameters: Sequence[object] = ()) -> sqlite3.Cursor:
        """Record the statement, then delegate to the wrapped connection."""
        self.calls.append((sql, parameters))
        return self.conn.execute(sql, parameters)


def _build_search_db() -> sqlite3.Connection:
    """Build an in-memory DB mirroring the searchers' real SQL.

    Two collections: c1 ("one") holds d1+d2, c2 ("two") holds d3; every
    document's content contains the shared term "python". The typed metadata
    tables use the production DDL via ``SchemaManager._create_metadata_tables``
    so later compiler tests execute against the real table shape.
    """
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute("CREATE TABLE collections (id TEXT PRIMARY KEY, name TEXT)")
    conn.execute(
        "CREATE TABLE documents "
        "(id TEXT PRIMARY KEY, collection_id TEXT, title TEXT, path TEXT, content TEXT)"
    )
    conn.execute("CREATE INDEX idx_documents_collection ON documents(collection_id)")
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
    SchemaManager(conn)._create_metadata_tables()

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
    return conn


def test_unfiltered_statement_byte_identical() -> None:
    """collection_ids=None records the captured HEAD golden byte-for-byte.

    Module-level (not classed) so the plan's verify node id
    ``test_filters_sql.py::test_unfiltered_statement_byte_identical`` resolves.
    """
    conn = _build_search_db()
    try:
        recorder = _RecordingConnection(conn)
        BM25Searcher(recorder).search(  # type: ignore[arg-type]
            "python",
            SearchOptions(collection_ids=None, include_highlights=False),
        )
        assert recorder.calls == [(_HEAD_UNFILTERED_SQL, _HEAD_UNFILTERED_PARAMS)]
    finally:
        conn.close()


def test_scoped_statement_byte_identical() -> None:
    """A scoped search records the captured HEAD golden byte-for-byte."""
    conn = _build_search_db()
    try:
        recorder = _RecordingConnection(conn)
        BM25Searcher(recorder).search(  # type: ignore[arg-type]
            "python",
            SearchOptions(collection_ids=["c1"], include_highlights=False),
        )
        assert recorder.calls == [(_HEAD_SCOPED_SQL, _HEAD_SCOPED_PARAMS)]
    finally:
        conn.close()


def test_no_filter_emits_no_extra_statement() -> None:
    """An unfiltered search never pays a filtered-only query (D-08)."""
    conn = _build_search_db()
    try:
        recorder = _RecordingConnection(conn)
        BM25Searcher(recorder).search(  # type: ignore[arg-type]
            "python",
            SearchOptions(collection_ids=None, include_highlights=False),
        )
        assert len(recorder.calls) == 1
    finally:
        conn.close()
