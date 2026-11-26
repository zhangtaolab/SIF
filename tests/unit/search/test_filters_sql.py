"""Byte-identical default and compiler SQL tests for metadata filters (Plan 20-01).

The module constants below were captured from the PRE-CHANGE implementation of
``BM25Searcher.search`` (HEAD ``4f63835``, before the Phase 20 filter slot was
added) through a recording connection. They are the golden: the unfiltered
path must issue exactly this statement and parameter list, so a filtered-only
behavior can never leak into the default path (byte-identical-defaults
culture, D-08/Pitfall 11).
"""

from __future__ import annotations

import sqlite3
from collections.abc import Sequence
from typing import Any

import pytest

from sif.core.filters import (
    All,
    Contains,
    Eq,
    Exists,
    FilterValidationError,
    Gt,
    In,
    Ne,
    Nin,
    Prefix,
    Suffix,
    TypeCondition,
    parse_filter,
    parse_match,
)
from sif.core.models import SearchOptions
from sif.database.schema import SchemaManager
from sif.search.bm25 import BM25Searcher
from sif.search.filters import compile_filter, compile_match


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


def _insert_typed(
    conn: sqlite3.Connection,
    document_id: str,
    key: str,
    ordinal: int,
    value_type: str,
    **columns: Any,
) -> None:
    """Insert one typed kv row with the production column shape."""
    conn.execute(
        "INSERT INTO document_metadata_values "
        "(document_id, key, ordinal, value_type, text_value, number_value, boolean_value) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        (
            document_id,
            key,
            ordinal,
            value_type,
            columns.get("text_value"),
            columns.get("number_value"),
            columns.get("boolean_value"),
        ),
    )


def _build_search_db() -> sqlite3.Connection:
    """Build an in-memory DB mirroring the searchers' real SQL.

    Two collections: c1 ("one") holds d1+d2, c2 ("two") holds d3; every
    document's content contains the shared term "python". The typed metadata
    tables use the production DDL via ``SchemaManager._create_metadata_tables``
    so filter tests execute against the real table shape.

    Typed rows: d1 has status=active, topic=[a,b], priority=3, reviewed=true;
    d2 has status=archived, topic=[b], priority=10; d3 has status=active,
    topic=[c] and no priority (``exists:false`` fixture). d4/d5 carry the
    non-ASCII case pair Ä/ä for the ASCII-folding regression.
    """
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute("CREATE TABLE collections (id TEXT PRIMARY KEY, name TEXT)")
    conn.execute(
        "CREATE TABLE documents "
        "(id TEXT PRIMARY KEY, collection_id TEXT, title TEXT, path TEXT, "
        "content TEXT, mtime REAL NOT NULL DEFAULT 0)"
    )
    conn.execute("CREATE INDEX idx_documents_collection ON documents(collection_id)")
    conn.execute("CREATE INDEX idx_documents_path ON documents(path)")
    conn.execute("CREATE INDEX idx_documents_mtime ON documents(mtime)")
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
        ("d1", "c1", "/d1.md", "python notes for one-a", 100.0),
        ("d2", "c1", "/d2.md", "python notes for one-b", 200.0),
        ("d3", "c2", "/d3.md", "python notes for two", 300.0),
        ("d4", "c1", "/d4.md", "python notes for case-a", 400.0),
        ("d5", "c1", "/d5.md", "python notes for case-b", 500.0),
    ]
    for doc_id, coll_id, path, content, mtime in docs:
        conn.execute(
            "INSERT INTO documents (id, collection_id, title, path, content, mtime)"
            " VALUES (?, ?, ?, ?, ?, ?)",
            (doc_id, coll_id, doc_id, path, content, mtime),
        )
    for document_id, values in (
        ("d1", [("status", "active"), ("topic", "a"), ("topic", "b")]),
        ("d2", [("status", "archived"), ("topic", "b")]),
        ("d3", [("status", "active"), ("topic", "c")]),
        ("d4", [("topic", "Ä")]),
        ("d5", [("topic", "ä")]),
    ):
        for ordinal, (key, text) in enumerate(values):
            _insert_typed(conn, document_id, key, ordinal, "string", text_value=text)
    _insert_typed(conn, "d1", "priority", 0, "number", number_value=3.0)
    _insert_typed(conn, "d2", "priority", 0, "number", number_value=10.0)
    _insert_typed(conn, "d1", "reviewed", 0, "boolean", boolean_value=1)
    # External-content FTS5 does not index plain INSERTs — rebuild explicitly.
    conn.execute("INSERT INTO documents_fts(documents_fts) VALUES('rebuild')")
    return conn


def _build_plan_db(count: int = 400) -> sqlite3.Connection:
    """Populated DB large enough for the planner to pick the built-in indexes."""
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute("CREATE TABLE collections (id TEXT PRIMARY KEY, name TEXT)")
    conn.execute(
        "CREATE TABLE documents "
        "(id TEXT PRIMARY KEY, collection_id TEXT, title TEXT, path TEXT NOT NULL, "
        "content TEXT, mtime REAL NOT NULL)"
    )
    conn.execute("CREATE INDEX idx_documents_collection ON documents(collection_id)")
    conn.execute("CREATE INDEX idx_documents_path ON documents(path)")
    conn.execute("CREATE INDEX idx_documents_mtime ON documents(mtime)")
    SchemaManager(conn)._create_metadata_tables()
    conn.execute("INSERT INTO collections VALUES ('c1', 'one')")
    for index in range(count):
        conn.execute(
            "INSERT INTO documents VALUES (?, ?, ?, ?, ?, ?)",
            (
                f"d{index}",
                "c1",
                f"title {index}",
                f"/notes/{index:04d}.md",
                "needle",
                float(index),
            ),
        )
        _insert_typed(
            conn,
            f"d{index}",
            "status",
            0,
            "string",
            text_value="active" if index % 2 else "archived",
        )
    return conn


def _probe(inner: str, *, negative: bool = False) -> str:
    """Expected candidates-scope EXISTS wrapper (``LIMIT 1`` per CR-02)."""
    prefix = "NOT EXISTS" if negative else "EXISTS"
    return (
        f"{prefix} (SELECT 1 FROM document_metadata_values mv "
        f"WHERE mv.document_id = d.id AND {inner} LIMIT 1)"
    )


def _corpus(inner: str, *, negative: bool = False) -> str:
    """Expected corpus-scope IN wrapper."""
    operator = "NOT IN" if negative else "IN"
    return f"d.id {operator} (SELECT mv.document_id FROM document_metadata_values mv WHERE {inner})"


_PRESENCE = "mv.key = ? AND mv.value_type = ?"
_EQ_TEXT = "mv.key = ? AND mv.value_type = ? AND mv.text_value = ?"


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


_SIMPLE_CASES: list[tuple[dict[str, Any], str, list[Any]]] = [
    (
        {"field": "status", "operator": "eq", "value": "active"},
        _EQ_TEXT,
        ["status", "string", "active"],
    ),
    (
        {"field": "priority", "operator": "eq", "value": 3},
        "mv.key = ? AND mv.value_type = ? AND mv.number_value = ?",
        ["priority", "number", 3],
    ),
    (
        {"field": "reviewed", "operator": "eq", "value": True},
        "mv.key = ? AND mv.value_type = ? AND mv.boolean_value = ?",
        ["reviewed", "boolean", 1],
    ),
    (
        {"field": "priority", "operator": "gt", "value": 3},
        "mv.key = ? AND mv.value_type = ? AND mv.number_value > ?",
        ["priority", "number", 3],
    ),
    (
        {"field": "topic", "operator": "in", "value": ["a", "b"]},
        "mv.key = ? AND mv.value_type = ? AND mv.text_value IN (?, ?)",
        ["topic", "string", "a", "b"],
    ),
    (
        {"field": "topic", "operator": "contains", "value": "a"},
        "mv.key = ? AND mv.value_type = ? AND instr(mv.text_value, ?) > 0",
        ["topic", "string", "a"],
    ),
    (
        {"field": "topic", "operator": "prefix", "value": "a"},
        "mv.key = ? AND mv.value_type = ? AND "
        "substr(CAST(mv.text_value AS BLOB), 1, ?) = CAST(? AS BLOB)",
        ["topic", "string", 1, "a"],
    ),
    (
        {"field": "topic", "operator": "suffix", "value": "a"},
        "mv.key = ? AND mv.value_type = ? AND "
        "substr(CAST(mv.text_value AS BLOB), -?) = CAST(? AS BLOB)",
        ["topic", "string", 1, "a"],
    ),
    (
        {"field": "priority", "operator": "type", "value": "number"},
        _PRESENCE,
        ["priority", "number"],
    ),
    (
        {"field": "priority", "operator": "exists", "value": True},
        "mv.key = ?",
        ["priority"],
    ),
]


class TestCompileFilterPerOperator:
    """Exact ``(sql, params)`` per operator and scope."""

    @pytest.mark.parametrize(("payload", "inner", "params"), _SIMPLE_CASES)
    def test_candidates_scope(self, payload: dict[str, Any], inner: str, params: list[Any]) -> None:
        """Each operator compiles to a correlated EXISTS probe."""
        assert compile_filter(parse_filter(payload)) == (_probe(inner), params)

    @pytest.mark.parametrize(("payload", "inner", "params"), _SIMPLE_CASES)
    def test_corpus_scope(self, payload: dict[str, Any], inner: str, params: list[Any]) -> None:
        """Each operator compiles to an uncorrelated IN probe in corpus scope."""
        assert compile_filter(parse_filter(payload), scope="corpus") == (
            _corpus(inner),
            params,
        )

    def test_ne_is_presence_and_negation(self) -> None:
        """ne = a same-type value exists AND no equal value (never bare NOT IN)."""
        node = parse_filter({"field": "status", "operator": "ne", "value": "active"})
        assert compile_filter(node) == (
            f"{_probe(_PRESENCE)} AND {_probe(_EQ_TEXT, negative=True)}",
            ["status", "string", "status", "string", "active"],
        )
        assert compile_filter(node, scope="corpus") == (
            f"{_corpus(_PRESENCE)} AND {_corpus(_EQ_TEXT, negative=True)}",
            ["status", "string", "status", "string", "active"],
        )

    def test_nin_is_presence_and_negation(self) -> None:
        """nin negates the membership probe behind a presence check."""
        node = parse_filter({"field": "topic", "operator": "nin", "value": ["a", "b"]})
        membership = "mv.key = ? AND mv.value_type = ? AND mv.text_value IN (?, ?)"
        assert compile_filter(node) == (
            f"{_probe(_PRESENCE)} AND {_probe(membership, negative=True)}",
            ["topic", "string", "topic", "string", "a", "b"],
        )

    def test_all_is_and_of_presence_probes(self) -> None:
        """all = one typed equality probe per operand element, AND-ed."""
        node = parse_filter({"field": "topic", "operator": "all", "value": ["a", "b"]})
        assert compile_filter(node) == (
            f"({_probe(_EQ_TEXT)} AND {_probe(_EQ_TEXT)})",
            ["topic", "string", "a", "topic", "string", "b"],
        )

    def test_groups_parenthesize(self) -> None:
        """and/not compile to parenthesized combinators."""
        node = parse_filter(
            {
                "operator": "and",
                "operands": [
                    {"field": "a", "operator": "eq", "value": "x"},
                    {
                        "operator": "not",
                        "operand": {"field": "b", "operator": "exists", "value": True},
                    },
                ],
            }
        )
        assert compile_filter(node) == (
            f"({_probe(_EQ_TEXT)} AND NOT ({_probe('mv.key = ?')}))",
            ["a", "string", "x", "b"],
        )

    def test_none_returns_empty(self) -> None:
        """None is the only unfiltered signal; it returns an empty fragment."""
        assert compile_filter(None) == ("", [])
        assert compile_filter(None, scope="corpus") == ("", [])

    def test_non_none_never_returns_empty(self) -> None:
        """Every non-None AST yields a non-empty predicate."""
        for payload, _, _ in _SIMPLE_CASES:
            sql, _ = compile_filter(parse_filter(payload))
            assert sql
        empty_match = parse_filter({"field": "nope", "operator": "exists", "value": True})
        assert compile_filter(empty_match)[0]

    def test_no_like_token_anywhere(self) -> None:
        """No compiled fragment contains a LIKE token (range/instr/substr only)."""
        for payload, _, _ in _SIMPLE_CASES:
            assert "LIKE" not in compile_filter(parse_filter(payload))[0].upper()
        path_prefix = parse_filter({"field": "path", "operator": "prefix", "value": "a"})
        assert "LIKE" not in compile_filter(path_prefix)[0].upper()
        mtime_range = parse_filter({"field": "mtime", "operator": "gte", "value": 1})
        assert "LIKE" not in compile_filter(mtime_range)[0].upper()

    def test_no_empty_in_list(self) -> None:
        """Placeholders are only emitted for non-empty validated lists."""
        node = parse_filter({"field": "topic", "operator": "in", "value": ["a"]})
        assert "IN (?)" in compile_filter(node)[0]
        assert "IN ()" not in compile_filter(node)[0]

    @pytest.mark.parametrize(
        "node",
        [
            Gt(field="priority", operator="gt", value=10**400),
            In(field="priority", operator="in", value=[10**400]),
        ],
    )
    def test_direct_ast_with_unbounded_integer_is_rejected(self, node: Any) -> None:
        """WR-01: the compiler's finite check is total for directly built ASTs."""
        with pytest.raises(FilterValidationError) as excinfo:
            compile_filter(node)
        assert str(excinfo.value).startswith(f"filter.{node.field}.{node.operator}:")
        assert "finite" in str(excinfo.value)


class TestCaseInsensitive:
    """D-10: ASCII-only case folding on both the column and the operand."""

    def test_eq_folds_both_sides(self) -> None:
        """eq with caseInsensitive wraps the text column in lower()."""
        node = parse_filter(
            {"field": "status", "operator": "eq", "value": "Active", "caseInsensitive": True}
        )
        assert compile_filter(node) == (
            _probe("mv.key = ? AND mv.value_type = ? AND lower(mv.text_value) = ?"),
            ["status", "string", "active"],
        )

    def test_ne_folds_both_sides(self) -> None:
        """ne with caseInsensitive folds the compared column in both probes."""
        node = parse_filter(
            {"field": "status", "operator": "ne", "value": "Active", "caseInsensitive": True}
        )
        sql, params = compile_filter(node)
        assert "lower(mv.text_value) = ?" in sql
        assert params == ["status", "string", "status", "string", "active"]

    def test_in_and_nin_fold(self) -> None:
        """in/nin fold the membership column and each operand."""
        node = parse_filter(
            {"field": "topic", "operator": "in", "value": ["A", "B"], "caseInsensitive": True}
        )
        assert compile_filter(node) == (
            _probe("mv.key = ? AND mv.value_type = ? AND lower(mv.text_value) IN (?, ?)"),
            ["topic", "string", "a", "b"],
        )
        nin = parse_filter(
            {"field": "topic", "operator": "nin", "value": ["A"], "caseInsensitive": True}
        )
        sql, params = compile_filter(nin)
        assert "lower(mv.text_value) IN (?)" in sql
        assert params == ["topic", "string", "topic", "string", "a"]

    def test_all_folds_each_probe(self) -> None:
        """all folds the compared column for every operand element."""
        node = parse_filter(
            {"field": "topic", "operator": "all", "value": ["A", "B"], "caseInsensitive": True}
        )
        sql, params = compile_filter(node)
        assert sql.count("lower(mv.text_value) = ?") == 2
        assert params == ["topic", "string", "a", "topic", "string", "b"]

    def test_contains_folds(self) -> None:
        """contains folds the instr() column and the operand."""
        node = parse_filter(
            {"field": "topic", "operator": "contains", "value": "AB", "caseInsensitive": True}
        )
        assert compile_filter(node) == (
            _probe("mv.key = ? AND mv.value_type = ? AND instr(lower(mv.text_value), ?) > 0"),
            ["topic", "string", "ab"],
        )

    def test_prefix_and_suffix_fold(self) -> None:
        """prefix/suffix fold the BLOB substr column and the operand."""
        prefix = parse_filter(
            {"field": "topic", "operator": "prefix", "value": "AB", "caseInsensitive": True}
        )
        assert compile_filter(prefix) == (
            _probe(
                "mv.key = ? AND mv.value_type = ? AND "
                "substr(CAST(lower(mv.text_value) AS BLOB), 1, ?) = CAST(? AS BLOB)"
            ),
            ["topic", "string", 2, "ab"],
        )
        suffix = parse_filter(
            {"field": "topic", "operator": "suffix", "value": "AB", "caseInsensitive": True}
        )
        assert compile_filter(suffix) == (
            _probe(
                "mv.key = ? AND mv.value_type = ? AND "
                "substr(CAST(lower(mv.text_value) AS BLOB), -?) = CAST(? AS BLOB)"
            ),
            ["topic", "string", 2, "ab"],
        )

    @pytest.mark.parametrize(
        "payload",
        [
            {"field": "status", "operator": "eq", "value": "Active"},
            {"field": "topic", "operator": "contains", "value": "AB"},
            {"field": "topic", "operator": "prefix", "value": "AB"},
            {"field": "topic", "operator": "in", "value": ["A", "B"]},
        ],
    )
    def test_no_lower_without_flag(self, payload: dict[str, Any]) -> None:
        """Without caseInsensitive no lower() is emitted."""
        assert "lower(" not in compile_filter(parse_filter(payload))[0]

    def test_non_ascii_case_pair_does_not_match(self) -> None:
        """Ä/ä differ: folding is ASCII-only, so the pair never cross-matches."""
        conn = _build_search_db()
        try:
            matches = {}
            for operand in ("Ä", "ä"):
                node = parse_filter(
                    {"field": "topic", "operator": "eq", "value": operand, "caseInsensitive": True}
                )
                sql, params = compile_filter(node)
                rows = conn.execute(
                    f"SELECT d.id FROM documents d WHERE 1 = 1 AND {sql}", params
                ).fetchall()
                matches[operand] = {row[0] for row in rows}
            assert matches["Ä"] == {"d4"}
            assert matches["ä"] == {"d5"}
            assert matches["Ä"] != matches["ä"]
        finally:
            conn.close()


class TestCompileMatch:
    """The discovery entry-scope compiler."""

    def test_key_prefix(self) -> None:
        """A key prefix uses the BLOB substr form (no LIKE)."""
        node = parse_match({"field": "key", "operator": "prefix", "value": "tag"})
        assert compile_match(node) == (
            "substr(CAST(mv.key AS BLOB), 1, ?) = CAST(? AS BLOB)",
            [3, "tag"],
        )

    def test_key_eq_and_contains(self) -> None:
        """Key equality and substring forms compile against the key column."""
        assert compile_match(parse_match({"field": "key", "operator": "eq", "value": "a"})) == (
            "mv.key = ?",
            ["a"],
        )
        assert compile_match(
            parse_match({"field": "key", "operator": "contains", "value": "ag"})
        ) == ("instr(mv.key, ?) > 0", ["ag"])

    def test_key_case_insensitive(self) -> None:
        """caseInsensitive folds the key column and the operand."""
        node = parse_match(
            {"field": "key", "operator": "eq", "value": "Tag", "caseInsensitive": True}
        )
        assert compile_match(node) == ("lower(mv.key) = ?", ["tag"])

    def test_value_string_eq(self) -> None:
        """A value equality pins the type and compares the typed column."""
        node = parse_match({"field": "value", "operator": "eq", "value": "active"})
        assert compile_match(node) == (
            "mv.value_type = ? AND mv.text_value = ?",
            ["string", "active"],
        )

    def test_value_numeric_gt(self) -> None:
        """A value ordering compares the numeric column."""
        node = parse_match({"field": "value", "operator": "gt", "value": 3})
        assert compile_match(node) == (
            "mv.value_type = ? AND mv.number_value > ?",
            ["number", 3],
        )

    def test_value_type(self) -> None:
        """A value type condition compares value_type only."""
        node = parse_match({"field": "value", "operator": "type", "value": "number"})
        assert compile_match(node) == ("mv.value_type = ?", ["number"])

    def test_groups(self) -> None:
        """Groups combine entry-scope leaves in order."""
        node = parse_match(
            {
                "operator": "and",
                "operands": [
                    {"field": "key", "operator": "prefix", "value": "t"},
                    {"field": "value", "operator": "eq", "value": "x"},
                ],
            }
        )
        assert compile_match(node) == (
            "(substr(CAST(mv.key AS BLOB), 1, ?) = CAST(? AS BLOB) "
            "AND mv.value_type = ? AND mv.text_value = ?)",
            [1, "t", "string", "x"],
        )

    def test_none_returns_empty(self) -> None:
        """None returns an empty fragment."""
        assert compile_match(None) == ("", [])

    def test_defensive_rejections(self) -> None:
        """Directly-constructed invalid nodes still raise, never compile."""
        for node in (
            Gt(field="key", operator="gt", value=3),
            Exists(field="key", operator="exists", value=True),
            All(field="value", operator="all", value=["a"]),
            Eq(field="topic", operator="eq", value="x"),
        ):
            with pytest.raises(FilterValidationError) as excinfo:
                compile_match(node)
            assert str(excinfo.value).startswith("filter.")

    def test_injection_values_keep_sql_shape(self) -> None:
        """Entry-scope operands are bound, never interpolated."""
        baseline, _ = compile_match(
            parse_match({"field": "key", "operator": "eq", "value": "benign"})
        )
        for evil in ("' OR 1=1 --", "a; DROP TABLE documents; --", "100%"):
            sql, params = compile_match(
                parse_match({"field": "key", "operator": "eq", "value": evil})
            )
            assert sql == baseline
            assert params == [evil]


class TestBuiltInFieldMatrix:
    """Every path/mtime operator has a defined outcome (D-03)."""

    @pytest.mark.parametrize(
        ("payload", "expected_sql", "params"),
        [
            ({"field": "path", "operator": "eq", "value": "/a.md"}, "d.path = ?", ["/a.md"]),
            ({"field": "path", "operator": "ne", "value": "/a.md"}, "d.path != ?", ["/a.md"]),
            (
                {"field": "path", "operator": "in", "value": ["/a.md", "/b.md"]},
                "d.path IN (?, ?)",
                ["/a.md", "/b.md"],
            ),
            (
                {"field": "path", "operator": "nin", "value": ["/a.md"]},
                "d.path NOT IN (?)",
                ["/a.md"],
            ),
            (
                {"field": "path", "operator": "prefix", "value": "/notes/"},
                "d.path >= ? AND d.path < ?",
                ["/notes/", "/notes/\U0010ffff"],
            ),
            (
                {"field": "path", "operator": "contains", "value": "note"},
                "instr(d.path, ?) > 0",
                ["note"],
            ),
            (
                {"field": "path", "operator": "contains", "value": ["a", "b"]},
                "(instr(d.path, ?) > 0 OR instr(d.path, ?) > 0)",
                ["a", "b"],
            ),
            (
                {"field": "path", "operator": "suffix", "value": ".md"},
                "substr(CAST(d.path AS BLOB), -?) = CAST(? AS BLOB)",
                [3, ".md"],
            ),
            ({"field": "path", "operator": "type", "value": "string"}, "1 = 1", []),
            ({"field": "path", "operator": "type", "value": "number"}, "0 = 1", []),
            ({"field": "path", "operator": "exists", "value": True}, "1 = 1", []),
            ({"field": "path", "operator": "exists", "value": False}, "0 = 1", []),
            (
                {"field": "path", "operator": "eq", "value": "/A.md", "caseInsensitive": True},
                "lower(d.path) = ?",
                ["/a.md"],
            ),
            (
                {
                    "field": "path",
                    "operator": "prefix",
                    "value": "/Notes/",
                    "caseInsensitive": True,
                },
                "lower(d.path) >= ? AND lower(d.path) < ?",
                ["/notes/", "/notes/\U0010ffff"],
            ),
            ({"field": "mtime", "operator": "eq", "value": 100}, "d.mtime = ?", [100]),
            ({"field": "mtime", "operator": "ne", "value": 100}, "d.mtime != ?", [100]),
            (
                {"field": "mtime", "operator": "in", "value": [100, 200]},
                "d.mtime IN (?, ?)",
                [100, 200],
            ),
            (
                {"field": "mtime", "operator": "nin", "value": [100]},
                "d.mtime NOT IN (?)",
                [100],
            ),
            ({"field": "mtime", "operator": "gt", "value": 100}, "d.mtime > ?", [100]),
            ({"field": "mtime", "operator": "gte", "value": 100}, "d.mtime >= ?", [100]),
            ({"field": "mtime", "operator": "lt", "value": 100}, "d.mtime < ?", [100]),
            ({"field": "mtime", "operator": "lte", "value": 100}, "d.mtime <= ?", [100]),
            ({"field": "mtime", "operator": "type", "value": "number"}, "1 = 1", []),
            ({"field": "mtime", "operator": "type", "value": "string"}, "0 = 1", []),
            ({"field": "mtime", "operator": "exists", "value": True}, "1 = 1", []),
            ({"field": "mtime", "operator": "exists", "value": False}, "0 = 1", []),
        ],
    )
    def test_valid_forms(
        self, payload: dict[str, Any], expected_sql: str, params: list[Any]
    ) -> None:
        """Built-in comparisons resolve to documents columns, never EXISTS."""
        assert compile_filter(parse_filter(payload)) == (expected_sql, params)

    @pytest.mark.parametrize(
        "node",
        [
            Ne(field="path", operator="ne", value=5),
            Nin(field="path", operator="nin", value=[5]),
            Gt(field="path", operator="gt", value=3),
            All(field="path", operator="all", value=["a"]),
            Ne(field="mtime", operator="ne", value="5"),
            In(field="mtime", operator="in", value=["5"]),
            Gt(field="mtime", operator="gt", value="5"),
            Contains(field="mtime", operator="contains", value="5"),
            Prefix(field="mtime", operator="prefix", value="5"),
            Suffix(field="mtime", operator="suffix", value="5"),
            All(field="mtime", operator="all", value=["a"]),
            Exists(field="mtime", operator="exists", value=True),
        ],
    )
    def test_rejected_forms_name_field_and_operator(self, node: Any) -> None:
        """Type-mismatched or unsupported built-in forms raise, never bind."""
        if isinstance(node, Exists):
            # exists is valid on mtime; only the caseInsensitive flag is not.
            node = Eq(field="mtime", operator="eq", value=1, caseInsensitive=True)
        with pytest.raises(FilterValidationError) as excinfo:
            compile_filter(node)
        message = str(excinfo.value)
        assert message.startswith(f"filter.{node.field}.{node.operator}:")
        assert node.operator in message
        assert node.field in message

    def test_mtime_text_ordering_rejected(self) -> None:
        """A text operand on an mtime comparison names field and operator."""
        with pytest.raises(FilterValidationError) as excinfo:
            compile_filter(Gt(field="mtime", operator="gt", value="5"))
        assert str(excinfo.value).startswith("filter.mtime.gt:")
        assert "requires a numeric value" in str(excinfo.value)

    def test_mtime_case_insensitive_rejected_at_parse_time(self) -> None:
        """WR-02: an ISO mtime operand with caseInsensitive is a parse-time error.

        The pairing used to parse and normalize, then fail inside the compiler
        (after the CLI/MCP error boundary); it now reports the D-17 path.
        """
        with pytest.raises(FilterValidationError) as excinfo:
            parse_filter(
                {
                    "field": "mtime",
                    "operator": "eq",
                    "value": "2026-01-01",
                    "caseInsensitive": True,
                }
            )
        assert str(excinfo.value).startswith("filter.eq:")
        assert "mtime" in str(excinfo.value)
        assert "caseInsensitive" in str(excinfo.value)

    def test_path_type_case_insensitive_rejected(self) -> None:
        """caseInsensitive has no meaning on a type test."""
        with pytest.raises(FilterValidationError):
            compile_filter(
                TypeCondition(field="path", operator="type", value="string", caseInsensitive=True)
            )

    def test_path_boolean_operand_rejected(self) -> None:
        """A boolean operand never binds against the TEXT path column."""
        with pytest.raises(FilterValidationError) as excinfo:
            compile_filter(Eq(field="path", operator="eq", value=True))
        assert str(excinfo.value).startswith("filter.path.eq:")


class TestBm25ParamOrder:
    """Pitfall 9: params follow placeholder order through the BM25 statement."""

    def test_weights_match_collection_min_score_filter_limit_offset(self) -> None:
        """The filter params land after min-score and before limit/offset."""
        conn = _build_search_db()
        try:
            node = parse_filter({"field": "status", "operator": "eq", "value": "active"})
            recorder = _RecordingConnection(conn)
            BM25Searcher(recorder).search(  # type: ignore[arg-type]
                "python",
                SearchOptions(
                    limit=5,
                    offset=2,
                    collection_ids=["c1"],
                    min_score=0.5,
                    filter=node,
                    include_highlights=False,
                ),
            )
            sql, params = recorder.calls[0]
            assert list(params) == [
                1.0,
                1.0,
                '"python"*',
                "c1",
                -1.0,
                "status",
                "string",
                "active",
                5,
                2,
            ]
            assert (
                sql.index("d.collection_id IN (?)")
                < sql.index("m.score <= ?")
                < sql.index("EXISTS (")
                < sql.index("LIMIT ? OFFSET ?")
            )
            # The predicate lives in the OUTER WHERE, never inside the CTE.
            cte, outer = sql.split("JOIN collections c ON d.collection_id = c.id", 1)
            assert "EXISTS (" not in cte
            assert "EXISTS (" in outer
        finally:
            conn.close()


class TestInjectionRegression:
    """T-20-01: operand text never enters the SQL string."""

    @pytest.mark.parametrize(
        "evil",
        [
            "' OR 1=1 --",
            "x'; DROP TABLE documents; --",
            "100%",
            "a_b\\c",
            '"; DELETE FROM documents; --',
        ],
    )
    def test_eq_value_stays_in_params(self, evil: str) -> None:
        """The SQL text is identical to a benign value; params carry the literal."""
        baseline_sql, _ = compile_filter(
            parse_filter({"field": "status", "operator": "eq", "value": "benign"})
        )
        sql, params = compile_filter(
            parse_filter({"field": "status", "operator": "eq", "value": evil})
        )
        assert sql == baseline_sql
        assert params == ["status", "string", evil]

    def test_contains_and_prefix_shape_unchanged(self) -> None:
        """Text operators keep their shape and carry the literal in params."""
        for operator in ("contains", "prefix", "suffix"):
            baseline, _ = compile_filter(
                parse_filter({"field": "topic", "operator": operator, "value": "benign"})
            )
            sql, params = compile_filter(
                parse_filter({"field": "topic", "operator": operator, "value": "x'; --"})
            )
            assert sql == baseline
            assert params[-1] == "x'; --"

    def test_evil_filter_executes_without_side_effects(self) -> None:
        """Executing an injection-shaped filter never mutates the database."""
        conn = _build_search_db()
        try:
            before = conn.execute("SELECT COUNT(*) FROM documents").fetchone()[0]
            sql, params = compile_filter(
                parse_filter({"field": "status", "operator": "eq", "value": "x' OR '1'='1"})
            )
            rows = conn.execute(
                f"SELECT d.id FROM documents d WHERE 1 = 1 AND {sql}", params
            ).fetchall()
            assert rows == []
            after = conn.execute("SELECT COUNT(*) FROM documents").fetchone()[0]
            assert after == before
        finally:
            conn.close()


class TestQueryPlans:
    """Measured plan behavior: built-in ranges use the document indexes."""

    def test_path_prefix_uses_path_index(self) -> None:
        """A path prefix is a half-open range resolved through idx_documents_path."""
        conn = _build_plan_db()
        try:
            node = parse_filter({"field": "path", "operator": "prefix", "value": "/notes/"})
            predicate, params = compile_filter(node, scope="corpus")
            plan = conn.execute(
                f"EXPLAIN QUERY PLAN SELECT COUNT(*) FROM documents d WHERE 1 = 1 AND {predicate}",
                params,
            ).fetchall()
            details = [row[3] for row in plan]
            assert any("idx_documents_path" in detail for detail in details), details
        finally:
            conn.close()

    def test_mtime_range_uses_mtime_index(self) -> None:
        """An mtime range resolves through idx_documents_mtime."""
        conn = _build_plan_db()
        try:
            node = parse_filter(
                {
                    "operator": "and",
                    "operands": [
                        {"field": "mtime", "operator": "gte", "value": 100},
                        {"field": "mtime", "operator": "lt", "value": 200},
                    ],
                }
            )
            predicate, params = compile_filter(node, scope="corpus")
            plan = conn.execute(
                f"EXPLAIN QUERY PLAN SELECT COUNT(*) FROM documents d WHERE 1 = 1 AND {predicate}",
                params,
            ).fetchall()
            details = [row[3] for row in plan]
            assert any("idx_documents_mtime" in detail for detail in details), details
        finally:
            conn.close()


class TestFilterExecutionSemantics:
    """Compiled predicates return the exact expected document sets."""

    def _matching_ids(self, conn: sqlite3.Connection, payload: dict[str, Any]) -> set[str]:
        """Run one compiled filter against the fixture and return document ids."""
        sql, params = compile_filter(parse_filter(payload))
        rows = conn.execute(
            f"SELECT d.id FROM documents d WHERE 1 = 1 AND {sql}", params
        ).fetchall()
        return {row[0] for row in rows}

    def _ordered_ids(self, conn: sqlite3.Connection, payload: dict[str, Any]) -> list[str]:
        """Run one compiled filter and return the ids as an ORDERED list (CR-02).

        A set hides duplicate outer rows; the correlated EXISTS on SQLite
        3.51.0 emitted one row per matching kv row, so this is the shape that
        catches the pagination/RRF corruption.
        """
        sql, params = compile_filter(parse_filter(payload))
        rows = conn.execute(
            f"SELECT d.id FROM documents d WHERE 1 = 1 AND {sql} ORDER BY d.id", params
        ).fetchall()
        return [row[0] for row in rows]

    def test_in_multi_valued_key_emits_each_document_once(self) -> None:
        """CR-02: ``in`` over a multi-valued key never duplicates a document.

        The old candidates probe returned ``d1`` twice for ``topic: [a, b]`` on
        SQLite 3.51.0, consuming an extra LIMIT/OFFSET slot and double-counting
        the RRF leg. The existing battery compared sets and could not see it.
        """
        conn = _build_search_db()
        try:
            _insert_typed(conn, "d1", "scores", 0, "number", number_value=1.0)
            _insert_typed(conn, "d1", "scores", 1, "number", number_value=2.0)
            _insert_typed(conn, "d2", "scores", 0, "number", number_value=2.0)

            topics = {"field": "topic", "operator": "in", "value": ["a", "b"]}
            scores = {"field": "scores", "operator": "in", "value": [1, 2]}

            assert self._ordered_ids(conn, topics) == ["d1", "d2"]
            assert self._ordered_ids(conn, scores) == ["d1", "d2"]
        finally:
            conn.close()

    def test_candidates_probe_is_bounded_to_one_row(self) -> None:
        """CR-02: the EXISTS probe is LIMIT-1 bounded; corpus ``IN`` is not."""
        payload = {"field": "topic", "operator": "in", "value": ["a", "b"]}
        candidates, _ = compile_filter(parse_filter(payload))
        corpus, _ = compile_filter(parse_filter(payload), scope="corpus")

        assert candidates.endswith("LIMIT 1)")
        assert " LIMIT 1" not in corpus

    def test_typed_equality_and_negation(self) -> None:
        """eq/ne/nin follow typed exact match and presence semantics."""
        conn = _build_search_db()
        try:
            eq_active = {"field": "status", "operator": "eq", "value": "active"}
            ne_active = {"field": "status", "operator": "ne", "value": "active"}
            nin_active = {"field": "status", "operator": "nin", "value": ["active"]}
            assert self._matching_ids(conn, eq_active) == {"d1", "d3"}
            assert self._matching_ids(conn, ne_active) == {"d2"}
            # Documents without a status row do not match ne/nin (missing keys).
            assert self._matching_ids(conn, nin_active) == {"d2"}
        finally:
            conn.close()

    def test_bool_is_not_a_number(self) -> None:
        """A boolean row never matches a numeric eq (D-10)."""
        conn = _build_search_db()
        try:
            numeric = {"field": "reviewed", "operator": "eq", "value": 1}
            boolean = {"field": "reviewed", "operator": "eq", "value": True}
            assert self._matching_ids(conn, numeric) == set()
            assert self._matching_ids(conn, boolean) == {"d1"}
        finally:
            conn.close()

    def test_exists_and_type(self) -> None:
        """exists/type see only the typed store, never the raw blob."""
        conn = _build_search_db()
        try:
            exists = {"field": "priority", "operator": "exists", "value": True}
            missing = {"field": "priority", "operator": "exists", "value": False}
            typed = {"field": "priority", "operator": "type", "value": "number"}
            assert self._matching_ids(conn, exists) == {"d1", "d2"}
            assert self._matching_ids(conn, missing) == {"d3", "d4", "d5"}
            assert self._matching_ids(conn, typed) == {"d1", "d2"}
        finally:
            conn.close()

    def test_arrays_are_sets(self) -> None:
        """all/contains evaluate per element over array rows."""
        conn = _build_search_db()
        try:
            all_rows = {"field": "topic", "operator": "all", "value": ["a", "b"]}
            contains = {"field": "topic", "operator": "contains", "value": "b"}
            assert self._matching_ids(conn, all_rows) == {"d1"}
            assert self._matching_ids(conn, contains) == {"d1", "d2"}
        finally:
            conn.close()

    def test_ordering_compares_numbers(self) -> None:
        """Ordering uses the numeric column and is not lexicographic."""
        conn = _build_search_db()
        try:
            over_5 = {"field": "priority", "operator": "gt", "value": 5}
            over_2 = {"field": "priority", "operator": "gt", "value": 2}
            assert self._matching_ids(conn, over_5) == {"d2"}
            assert self._matching_ids(conn, over_2) == {"d1", "d2"}
        finally:
            conn.close()

    def test_builtin_path_and_mtime(self) -> None:
        """Reserved built-ins filter the documents columns directly."""
        conn = _build_search_db()
        try:
            prefix = {"field": "path", "operator": "prefix", "value": "/d1"}
            since = {"field": "mtime", "operator": "gte", "value": 300}
            assert self._matching_ids(conn, prefix) == {"d1"}
            assert self._matching_ids(conn, since) == {"d3", "d4", "d5"}
        finally:
            conn.close()

    def test_empty_match_returns_no_rows(self) -> None:
        """A filter matching nothing never degrades to the unfiltered set."""
        conn = _build_search_db()
        try:
            empty = {"field": "nope", "operator": "exists", "value": True}
            assert self._matching_ids(conn, empty) == set()
        finally:
            conn.close()

    def test_count_matching_documents_agrees(self) -> None:
        """The D-08 pre-count uses corpus scope and agrees with the row set."""
        from sif.search.filters import count_matching_documents

        conn = _build_search_db()
        try:
            node = parse_filter({"field": "status", "operator": "eq", "value": "active"})
            assert count_matching_documents(conn, node, None) == 2
            assert count_matching_documents(conn, node, ["c2"]) == 1
            assert count_matching_documents(conn, node, []) == 0
        finally:
            conn.close()
