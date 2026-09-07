"""Real-SQL regression tests for path-context attachment.

05-VERIFICATION.md gap 1: the SQL ``target_id IN (<result paths>)`` pre-filter
compared raw strings, so a context stored under a symlink-alias form (e.g.
``/tmp/vault/doc.md``) never matched a document stored under the resolved form
(macOS ``/private/tmp/vault/doc.md``). These tests run the real contexts query
against real SQLite — a mocked cursor cannot validate that SQL matching occurs,
which is exactly how the three replaced mock-based tests blessed the broken
pre-filter.
"""

import sqlite3
from unittest.mock import MagicMock

import pytest

from sif.core.models import SearchResult
from sif.database.schema import SchemaManager
from sif.search.bm25 import BM25Searcher


@pytest.fixture
def alias_pair(tmp_path):
    """Create a real symlink alias over a vault directory.

    Returns ``(resolved_doc_path, alias_doc_path)``. The symlink is real, so
    the two forms genuinely differ on platforms whose tmp dir is itself
    symlinked (macOS ``/private/tmp``) and normalize to the same file on every
    platform.
    """
    vault = tmp_path / "vault"
    vault.mkdir()
    doc = vault / "doc.md"
    doc.write_text("# Doc\nneedle content\n", encoding="utf-8")
    alias_dir = tmp_path / "alias"
    alias_dir.symlink_to(vault)
    return str(doc), str(alias_dir / "doc.md")


@pytest.fixture
def db():
    """Real in-memory SQLite with the production contexts table DDL."""
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    SchemaManager(conn)._create_contexts_table()
    yield conn
    conn.close()


def _insert_path_context(
    conn: sqlite3.Connection,
    ctx_id: str,
    target: str,
    content: str,
    updated_at: str = "2026-01-02T00:00:00",
) -> None:
    conn.execute(
        "INSERT INTO contexts (id, target_id, context_type, content, created_at, updated_at) "
        "VALUES (?, ?, 'path', ?, '2026-01-01T00:00:00', ?)",
        (ctx_id, target, content, updated_at),
    )
    conn.commit()


def _result(path: str, description: str | None = None) -> SearchResult:
    result = SearchResult(
        document_id="d1",
        title="T",
        path=path,
        collection_name="c",
        score=1.0,
        rank=1,
    )
    if description is not None:
        result.context_description = description
    return result


class TestAttachPathContextsRealSQL:
    """The mismatch scenario proven against real SQL, not mocked cursors."""

    def test_attach_matches_symlink_alias_target(self, db, alias_pair):
        """A context stored under the alias form attaches to the resolved-form result."""
        resolved, alias = alias_pair
        _insert_path_context(db, "ctx-1", alias, "Project notes")

        results = BM25Searcher(db)._attach_contexts([_result(resolved)])

        assert results[0].context_description == "Project notes"

    def test_unmatched_result_keeps_none(self, db, alias_pair, tmp_path):
        """In a mixed batch, the result with no context keeps context_description None."""
        resolved, alias = alias_pair
        _insert_path_context(db, "ctx-1", alias, "Project notes")
        other_doc = tmp_path / "vault" / "other.md"
        other_doc.write_text("# Other\n", encoding="utf-8")

        results = BM25Searcher(db)._attach_contexts(
            [_result(resolved), _result(str(other_doc))],
        )

        assert results[0].context_description == "Project notes"
        assert results[1].context_description is None

    def test_preserves_existing_description_on_miss(self, db, alias_pair):
        """A result already carrying a description with no DB match keeps it."""
        resolved, _ = alias_pair

        results = BM25Searcher(db)._attach_contexts(
            [_result(resolved, description="Reranked context")],
        )

        assert results[0].context_description == "Reranked context"

    def test_empty_results_no_query(self):
        """An empty results list returns unchanged without touching the DB."""
        mock_db = MagicMock()
        assert BM25Searcher(mock_db)._attach_contexts([]) == []
        mock_db.execute.assert_not_called()
