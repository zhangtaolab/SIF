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

import inspect
import logging
import sqlite3
import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from sif.core.models import PathContext, SearchResult
from sif.database.repositories import ContextRepository
from sif.database.schema import SchemaManager
from sif.search import context_attach
from sif.search.context_attach import attach_path_contexts, enrich_results
from sif.utils.paths import normalize_path
from tests.support import symlink_or_skip


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
    symlink_or_skip(alias_dir, vault, target_is_directory=True)
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

    def test_enrich_results_on_real_db(self, db, alias_pair):
        """enrich_results composes context attachment on a real connection.

        The composition helper is the enrichment owner now that searchers are
        pure producers; staleness degrades to unmarked here because this
        fixture DB has no vec0 table.
        """
        resolved, alias = alias_pair
        _insert_path_context(db, "ctx-1", alias, "Method-level notes")

        results = enrich_results(db, [_result(resolved)])

        assert results[0].context_description == "Method-level notes"
        assert results[0].vectors_stale is False

    def test_enrich_results_composes_both_signals(self, monkeypatch):
        """enrich_results runs attach first, then staleness, on the same list.

        The composition helper is the enrichment owner now; searchers no longer
        expose an attach method, so this pins the order and list identity.
        """
        mock_db = MagicMock()
        results = [_result("/v.md")]
        calls: list[tuple[str, object, list[SearchResult]]] = []

        def recording_attach(db, res):
            calls.append(("attach", db, res))
            return res

        def recording_staleness(db, res):
            calls.append(("staleness", db, res))
            return res

        monkeypatch.setattr("sif.search.context_attach.attach_path_contexts", recording_attach)
        monkeypatch.setattr("sif.search.context_attach.mark_vector_staleness", recording_staleness)

        enriched = enrich_results(mock_db, results)

        assert enriched is results
        assert [c[0] for c in calls] == ["attach", "staleness"]
        assert all(c[1] is mock_db for c in calls)
        assert all(c[2] is results for c in calls)

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

    @pytest.mark.skipif(
        sys.platform == "win32",
        reason="ntpath maps an unknown ~user to C:\\Users\\<user> instead of failing",
    )
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


@pytest.fixture
def file_db(tmp_path):
    """Real on-disk SQLite with the production contexts table DDL."""
    path = tmp_path / "index.db"
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    SchemaManager(conn)._create_contexts_table()
    conn.commit()
    yield path, conn
    conn.close()


def _context_statements(statements: list[str]) -> list[str]:
    """Return the traced statements that hit the contexts table."""
    return [statement for statement in statements if "FROM contexts" in statement]


def _cache_key(conn: sqlite3.Connection) -> str:
    """Return the resolved main path the cache keys on (asserting it exists)."""
    key = context_attach._resolved_main_path(conn)
    assert key is not None
    return key


def _attach_description(conn: sqlite3.Connection, path: str = "/vault/doc.md") -> str | None:
    """Attach one result and return its context description."""
    return attach_path_contexts(conn, [_result(path)])[0].context_description


class TestContextMapCache:
    """D-12: per-process map cache with conservative invalidation triggers."""

    def test_two_attaches_issue_exactly_one_contexts_statement(self, file_db):
        """Two attaches on the same file DB run one contexts SELECT and agree."""
        _, conn = file_db
        _insert_path_context(conn, "ctx-1", "/vault/doc.md", "Project notes")

        statements: list[str] = []
        conn.set_trace_callback(statements.append)
        try:
            first = attach_path_contexts(conn, [_result("/vault/doc.md")])
            second = attach_path_contexts(conn, [_result("/vault/doc.md")])
        finally:
            conn.set_trace_callback(None)

        assert first[0].context_description == "Project notes"
        assert second[0].context_description == "Project notes"
        selects = _context_statements(statements)
        assert len(selects) == 1
        assert selects[0] == context_attach._CONTEXTS_SQL

    def test_repository_create_invalidates_and_rebuilds_once(self, file_db):
        """A ContextRepository.create bumps the generation; the next attach rebuilds."""
        _, conn = file_db
        statements: list[str] = []
        conn.set_trace_callback(statements.append)
        try:
            assert _attach_description(conn) is None
            assert len(_context_statements(statements)) == 1

            ContextRepository(conn).create(PathContext(path="/vault/doc.md", context="New notes"))
            conn.commit()

            rebuilt = attach_path_contexts(conn, [_result("/vault/doc.md")])
            assert rebuilt[0].context_description == "New notes"
            assert len(_context_statements(statements)) == 2

            attach_path_contexts(conn, [_result("/vault/doc.md")])
            assert len(_context_statements(statements)) == 2
        finally:
            conn.set_trace_callback(None)

    def test_repository_generation_alone_invalidates(self, file_db, monkeypatch):
        """The generation trigger alone rebuilds even when data_version is constant."""
        _, conn = file_db
        monkeypatch.setattr(context_attach, "_sample_data_version", lambda _sentinel: 7)
        statements: list[str] = []
        conn.set_trace_callback(statements.append)
        try:
            attach_path_contexts(conn, [_result("/vault/doc.md")])
            assert len(_context_statements(statements)) == 1

            ContextRepository(conn).create(PathContext(path="/vault/doc.md", context="Bumped"))
            conn.commit()

            rebuilt = attach_path_contexts(conn, [_result("/vault/doc.md")])
            assert rebuilt[0].context_description == "Bumped"
            assert len(_context_statements(statements)) == 2
        finally:
            conn.set_trace_callback(None)

    def test_separate_connection_commit_invalidates(self, file_db):
        """A commit from another connection invalidates via sentinel data_version."""
        path, conn = file_db
        statements: list[str] = []
        conn.set_trace_callback(statements.append)
        try:
            assert _attach_description(conn) is None
            assert len(_context_statements(statements)) == 1

            other = sqlite3.connect(str(path))
            try:
                _insert_path_context(other, "ctx-1", "/vault/doc.md", "Other connection")
            finally:
                other.close()

            rebuilt = attach_path_contexts(conn, [_result("/vault/doc.md")])
            assert rebuilt[0].context_description == "Other connection"
            assert len(_context_statements(statements)) == 2
        finally:
            conn.set_trace_callback(None)

    def test_same_connection_unrelated_commit_invalidates(self, file_db):
        """Any commit, not only a contexts write, conservatively invalidates."""
        _, conn = file_db
        statements: list[str] = []
        conn.set_trace_callback(statements.append)
        try:
            attach_path_contexts(conn, [_result("/vault/doc.md")])
            assert len(_context_statements(statements)) == 1

            conn.execute("CREATE TABLE unrelated (value TEXT)")
            conn.commit()

            attach_path_contexts(conn, [_result("/vault/doc.md")])
            assert len(_context_statements(statements)) == 2
        finally:
            conn.set_trace_callback(None)

    def test_memory_database_requeries_on_every_attach(self, db):
        """A :memory: database bypasses the cache (no cross-connection view)."""
        _insert_path_context(db, "ctx-1", "/vault/doc.md", "Project notes")
        statements: list[str] = []
        db.set_trace_callback(statements.append)
        try:
            first = attach_path_contexts(db, [_result("/vault/doc.md")])
            second = attach_path_contexts(db, [_result("/vault/doc.md")])
        finally:
            db.set_trace_callback(None)

        assert first[0].context_description == "Project notes"
        assert second[0].context_description == "Project notes"
        assert len(_context_statements(statements)) == 2

    def test_file_db_cached_map_preserves_verbatim_alias_match(self, file_db, alias_pair):
        """The legacy alias fixture still attaches through the cached map."""
        _, conn = file_db
        resolved, alias = alias_pair
        _insert_path_context(conn, "ctx-1", alias, "Project notes")

        first = attach_path_contexts(conn, [_result(resolved)])
        second = attach_path_contexts(conn, [_result(resolved)])

        assert first[0].context_description == "Project notes"
        assert second[0].context_description == "Project notes"

    def test_file_db_newest_updated_at_wins(self, file_db, alias_pair):
        """Newest updated_at still wins when two rows normalize to the same key."""
        _, conn = file_db
        resolved, alias = alias_pair
        _insert_path_context(
            conn, "ctx-new", resolved, "New notes", updated_at="2026-06-01T00:00:00"
        )
        _insert_path_context(conn, "ctx-old", alias, "Old notes", updated_at="2026-01-01T00:00:00")

        results = attach_path_contexts(conn, [_result(resolved)])

        assert results[0].context_description == "New notes"

    def test_sentinel_open_failure_bypasses_with_fresh_scan(self, file_db, monkeypatch, caplog):
        """A sentinel that cannot open degrades to the verbatim scan, no caching."""
        _, conn = file_db
        _insert_path_context(conn, "ctx-1", "/vault/doc.md", "Project notes")
        monkeypatch.setattr(context_attach, "_open_sentinel", lambda _path: None)

        statements: list[str] = []
        conn.set_trace_callback(statements.append)
        with caplog.at_level(logging.DEBUG):
            try:
                first = attach_path_contexts(conn, [_result("/vault/doc.md")])
                second = attach_path_contexts(conn, [_result("/vault/doc.md")])
            finally:
                conn.set_trace_callback(None)

        assert first[0].context_description == "Project notes"
        assert second[0].context_description == "Project notes"
        assert len(_context_statements(statements)) == 2
        assert len(caplog.records) <= 1
        assert _cache_key(conn) not in context_attach._context_cache

    def test_open_sentinel_returns_none_for_missing_directory(self, tmp_path, caplog):
        """A real sqlite3 open failure returns None and logs one debug record."""
        with caplog.at_level(logging.DEBUG):
            sentinel = context_attach._open_sentinel(str(tmp_path / "missing" / "index.db"))

        assert sentinel is None
        assert len(caplog.records) == 1
        assert caplog.records[0].levelno == logging.DEBUG

    def test_file_inode_missing_path_returns_none(self, tmp_path):
        """An unstattable database file degrades to None (cache bypass)."""
        assert context_attach._file_inode(str(tmp_path / "absent.db")) is None


class TestContextCacheLifecycle:
    """Reset, inode replacement, and sentinel-failure lifecycle hardening."""

    def test_empty_map_is_cached_until_first_repository_write(self, file_db):
        """An empty contexts table caches ``{}`` and the first write invalidates."""
        _, conn = file_db
        statements: list[str] = []
        conn.set_trace_callback(statements.append)
        try:
            assert _attach_description(conn) is None
            assert len(_context_statements(statements)) == 1
            assert _attach_description(conn) is None
            assert len(_context_statements(statements)) == 1

            ContextRepository(conn).create(PathContext(path="/vault/doc.md", context="First"))
            conn.commit()

            rebuilt = attach_path_contexts(conn, [_result("/vault/doc.md")])
            assert rebuilt[0].context_description == "First"
            assert len(_context_statements(statements)) == 2
        finally:
            conn.set_trace_callback(None)

    def test_reset_context_cache_forces_rebuild(self, file_db):
        """reset_context_cache closes sentinels, clears the map, keeps the generation."""
        _, conn = file_db
        _insert_path_context(conn, "ctx-1", "/vault/doc.md", "Project notes")
        statements: list[str] = []
        conn.set_trace_callback(statements.append)
        try:
            assert _attach_description(conn) == "Project notes"
            assert len(_context_statements(statements)) == 1
            key = _cache_key(conn)
            assert key in context_attach._context_cache

            context_attach.reset_context_cache()
            assert context_attach._context_cache == {}

            rebuilt = attach_path_contexts(conn, [_result("/vault/doc.md")])
            assert rebuilt[0].context_description == "Project notes"
            assert len(_context_statements(statements)) == 2
        finally:
            conn.set_trace_callback(None)

    def test_inode_change_closes_old_sentinel_and_reopens(self, file_db, monkeypatch):
        """An inode change closes the old handle and reopens a fresh sentinel."""
        _, conn = file_db
        _insert_path_context(conn, "ctx-1", "/vault/doc.md", "Project notes")
        assert _attach_description(conn) == "Project notes"

        key = _cache_key(conn)
        old_sentinel = context_attach._context_cache[key].sentinel
        real_inode = context_attach._file_inode(key)
        assert real_inode is not None
        monkeypatch.setattr(
            context_attach,
            "_file_inode",
            lambda _path: (real_inode[0], real_inode[1] + 1),
        )

        rebuilt = attach_path_contexts(conn, [_result("/vault/doc.md")])

        assert rebuilt[0].context_description == "Project notes"
        assert context_attach._context_cache[key].sentinel is not old_sentinel
        with pytest.raises(sqlite3.ProgrammingError):
            old_sentinel.execute("PRAGMA data_version")

    def test_sentinel_error_during_sampling_bypasses_and_caches_nothing(self, file_db):
        """A broken sentinel is closed, the entry dropped, and the call uncached."""
        _, conn = file_db
        _insert_path_context(conn, "ctx-1", "/vault/doc.md", "Project notes")
        assert _attach_description(conn) == "Project notes"
        key = _cache_key(conn)

        statements: list[str] = []
        conn.set_trace_callback(statements.append)
        try:
            # Simulate the documented sqlite3.Error path: the sentinel is dead.
            context_attach._context_cache[key].sentinel.close()
            bypassed = attach_path_contexts(conn, [_result("/vault/doc.md")])
            assert bypassed[0].context_description == "Project notes"
            assert len(_context_statements(statements)) == 1
            assert key not in context_attach._context_cache

            # The next attach opens a healthy sentinel and caches again.
            recovered = attach_path_contexts(conn, [_result("/vault/doc.md")])
            assert recovered[0].context_description == "Project notes"
            assert len(_context_statements(statements)) == 2
            assert key in context_attach._context_cache
        finally:
            conn.set_trace_callback(None)


class TestVectorsUntrustedSeam:
    """The identity-warning seam: force-mark every result stale after enrichment."""

    def test_vectors_untrusted_marks_every_result_stale(self, db, alias_pair):
        """Contexts still attach; every result is stale when the flag is set."""
        resolved, alias = alias_pair
        _insert_path_context(db, "ctx-1", alias, "Method-level notes")

        results = enrich_results(
            db,
            [_result(resolved), _result("/elsewhere.md")],
            vectors_untrusted=True,
        )

        assert results[0].context_description == "Method-level notes"
        assert all(result.vectors_stale for result in results)

    def test_default_leaves_derived_marking_in_charge(self, db):
        """The two-argument form keeps the derived staleness pass authoritative."""
        results = enrich_results(db, [_result("/v.md")])

        assert results[0].vectors_stale is False

    def test_vectors_untrusted_applies_after_the_normal_pass(self, monkeypatch):
        """The flag overrides the normal pass's derived marks, never before it."""
        results = [_result("/v.md")]
        calls: list[str] = []

        def recording_attach(_db, res):
            calls.append("attach")
            return res

        def recording_staleness(_db, res):
            calls.append("staleness")
            return res

        monkeypatch.setattr(context_attach, "attach_path_contexts", recording_attach)
        monkeypatch.setattr(context_attach, "mark_vector_staleness", recording_staleness)

        enriched = enrich_results(MagicMock(), results, vectors_untrusted=True)

        assert enriched is results
        assert calls == ["attach", "staleness"]
        assert results[0].vectors_stale is True

    def test_two_argument_signature_stays_compatible(self, db):
        """``vectors_untrusted`` is keyword-only and defaults to False."""
        parameter = inspect.signature(enrich_results).parameters["vectors_untrusted"]

        assert parameter.kind is inspect.Parameter.KEYWORD_ONLY
        assert parameter.default is False
        assert enrich_results(db, [_result("/v.md")])[0].vectors_stale is False
