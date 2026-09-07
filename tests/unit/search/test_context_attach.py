"""Real-SQL regression tests for path-context attachment.

05-VERIFICATION.md gap 1: the SQL membership pre-filter on raw ``target_id``
strings returned zero rows whenever the stored context carried the
user-typed symlink-alias form (e.g. ``/tmp/vault/doc.md``) while
``documents.path`` stores the resolved form (macOS
``/private/tmp/vault/doc.md``). The three mock-based normalized-path tests
this suite replaces never validated that real SQL matching occurs — their
mocked cursors returned rows regardless of the WHERE clause. Every test here
executes the real contexts query against real SQLite.
"""

import sqlite3
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from sif.core.models import SearchResult
from sif.database.schema import SchemaManager
from sif.search.bm25 import BM25Searcher
from sif.search.context_attach import attach_path_contexts
from sif.search.hybrid import HybridSearcher
from sif.search.vector import VectorSearcher
from sif.utils.paths import normalize_path


@pytest.fixture
def alias_pair(tmp_path):
    """Create a real symlink alias over a vault directory.

    Returns ``(resolved_doc_path, alias_doc_path)``. The symlink is real, so
    the two forms genuinely differ on platforms whose tmp dir is itself
    symlinked (macOS ``/private/tmp``) and normalize to the same file on
    every platform — the mismatch is induced by the filesystem, not by a
    hardcoded ``/private/tmp`` string.
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
        """A context stored under the alias form attaches to the resolved-form result.

        This is the test the three replaced mock-based tests pretended to be:
        the SQL itself must return the alias-form row for a resolved-form
        result path. It fails against the pre-fix code because the raw-string
        pre-filter drops the row.
        """
        resolved, alias = alias_pair
        _insert_path_context(db, "ctx-1", alias, "Project notes")

        results = attach_path_contexts(db, [_result(resolved)])

        assert results[0].context_description == "Project notes"

    def test_unmatched_result_keeps_none(self, db, alias_pair, tmp_path):
        """In a mixed batch, the result with no context keeps context_description None."""
        resolved, alias = alias_pair
        _insert_path_context(db, "ctx-1", alias, "Project notes")
        other_doc = tmp_path / "vault" / "other.md"
        other_doc.write_text("# Other\n", encoding="utf-8")

        results = attach_path_contexts(db, [_result(resolved), _result(str(other_doc))])

        assert results[0].context_description == "Project notes"
        assert results[1].context_description is None

    def test_preserves_existing_description_on_miss(self, db, alias_pair):
        """A result already carrying a description with no DB match keeps it."""
        resolved, _ = alias_pair

        results = attach_path_contexts(db, [_result(resolved, description="Reranked context")])

        assert results[0].context_description == "Reranked context"

    def test_newest_updated_at_wins_on_duplicate_targets(self, db, alias_pair):
        """Two contexts normalizing to the same key: newest updated_at wins.

        The newer row is inserted FIRST — without the ORDER BY updated_at the
        dict would take the last-read (older) row, so this pins the
        deterministic newest-wins ordering (CTX-02 ordering edge).
        """
        resolved, alias = alias_pair
        _insert_path_context(db, "ctx-new", resolved, "New notes", updated_at="2026-06-01T00:00:00")
        _insert_path_context(db, "ctx-old", alias, "Old notes", updated_at="2026-01-01T00:00:00")

        results = attach_path_contexts(db, [_result(resolved)])

        assert results[0].context_description == "New notes"

    def test_bm25_searcher_method_on_real_db(self, db, alias_pair):
        """BM25Searcher._attach_contexts behaves identically on a real connection."""
        resolved, alias = alias_pair
        _insert_path_context(db, "ctx-1", alias, "Method-level notes")

        results = BM25Searcher(db)._attach_contexts([_result(resolved)])

        assert results[0].context_description == "Method-level notes"

    def test_vector_and_hybrid_delegate(self, monkeypatch):
        """VectorSearcher and HybridSearcher delegate to the shared helper with self.db.

        Their real-DB construction requires the sqlite-vec extension, so the
        delegation wiring is proven with MagicMock DBs (vec check succeeds on
        mocks) and recording wrappers around the real function.
        """
        calls: list[tuple[str, object, list[SearchResult]]] = []

        def recording_wrapper(tag: str):
            def wrapper(db, results):
                calls.append((tag, db, results))
                return attach_path_contexts(db, results)

            return wrapper

        vector_searcher = VectorSearcher(MagicMock())
        vector_results = [_result("/v.md")]
        monkeypatch.setattr(
            "sif.search.vector.attach_path_contexts",
            recording_wrapper("vector"),
        )
        vector_searcher._attach_contexts(vector_results)

        hybrid_searcher = HybridSearcher(MagicMock(), embedder=None)
        hybrid_results = [_result("/h.md")]
        monkeypatch.setattr(
            "sif.search.hybrid.attach_path_contexts",
            recording_wrapper("hybrid"),
        )
        hybrid_searcher._attach_contexts(hybrid_results)

        assert len(calls) == 2
        assert calls[0][0] == "vector"
        assert calls[0][1] is vector_searcher.db
        assert calls[0][2] is vector_results
        assert calls[1][0] == "hybrid"
        assert calls[1][1] is hybrid_searcher.db
        assert calls[1][2] is hybrid_results

    def test_normalize_path_edges(self, alias_pair, tmp_path):
        """normalize_path expands ~, collapses real symlinks, and keeps missing tails."""
        resolved, alias = alias_pair

        # ~ expands to the real user home and yields an absolute path
        home_form = normalize_path("~/not-a-real-note.md")
        assert Path(home_form).is_absolute()
        assert "~" not in home_form
        assert home_form.startswith(str(Path.home().resolve()))
        assert home_form.endswith("not-a-real-note.md")

        # the alias form collapses onto the resolved form
        assert normalize_path(alias) == normalize_path(resolved)

        # a non-existent tail is preserved (strict=False): the parent resolves,
        # the missing file name survives so not-yet-indexed targets normalize
        missing = str(tmp_path / "vault" / "missing.md")
        normalized_missing = normalize_path(missing)
        assert normalized_missing == str((tmp_path / "vault").resolve() / "missing.md")
        assert not Path(normalized_missing).exists()

    def test_normalize_path_unexpandable_tilde_degrades_to_raw_form(self):
        """REVIEW WR-01: an un-expandable ~user form returns the raw string, never raises.

        Path.expanduser raises RuntimeError for a "~user" prefix whose user
        does not resolve; normalize_path must be total so a stored row of
        that shape cannot crash every search over the contexts table.
        """
        poison = "~sif-no-such-user-7f3a/notes/doc.md"

        assert normalize_path(poison) == poison

    def test_malformed_tilde_row_does_not_crash_attach(self, db, alias_pair):
        """REVIEW WR-01: one malformed '~unknownuser/...' row must not break attachment.

        attach_path_contexts normalizes EVERY path-type context row; before
        the total-form fix a single un-expandable row raised RuntimeError
        and bricked all three searchers. The malformed row simply matches
        nothing while healthy rows still attach.
        """
        resolved, alias = alias_pair
        _insert_path_context(db, "ctx-poison", "~sif-no-such-user-7f3a/notes/doc.md", "Poison")
        _insert_path_context(db, "ctx-1", alias, "Project notes")

        results = attach_path_contexts(db, [_result(resolved)])

        assert results[0].context_description == "Project notes"

    def test_empty_results_no_query(self):
        """An empty results list returns unchanged without touching the DB."""
        mock_db = MagicMock()
        assert attach_path_contexts(mock_db, []) == []
        mock_db.execute.assert_not_called()
