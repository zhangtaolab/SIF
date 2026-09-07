"""Real-SQL tests for ContextRepository prune and update_target (05-09).

REVIEW CR-02 / 05-VERIFICATION root cause: ``delete_orphaned_paths`` compared
raw ``target_id`` strings against ``documents.path`` inside SQL, so a context
stored under a symlink-alias or ``~`` form of an EXISTING document was
classified as orphaned and silently deleted — exactly the rows that search
context attachment (plan 05-08) matches by normalizing both sides with
``normalize_path``. Every test here runs against a real in-memory SQLite
database created from the production DDL (no sqlite-vec extension involved).
"""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone

import pytest

from sif.core.models import PathContext
from sif.database.repositories import ContextRepository
from sif.database.schema import SchemaManager
from sif.utils.paths import normalize_path


@pytest.fixture
def db():
    """Real in-memory SQLite with the production documents/contexts DDL."""
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    manager = SchemaManager(conn)
    manager._create_documents_table()
    manager._create_contexts_table()
    yield conn
    conn.close()


@pytest.fixture
def alias_pair(tmp_path):
    """Create a real symlink alias over a vault directory.

    Returns ``(resolved_doc_path, alias_doc_path)`` — same construction as
    tests/unit/search/test_context_attach.py (plan 05-08). The two forms
    genuinely differ on platforms whose tmp dir is itself symlinked (macOS
    ``/private/tmp``).
    """
    vault = tmp_path / "vault"
    vault.mkdir()
    doc = vault / "doc.md"
    doc.write_text("# Doc\nneedle content\n", encoding="utf-8")
    alias_dir = tmp_path / "alias"
    alias_dir.symlink_to(vault)
    return str(doc), str(alias_dir / "doc.md")


def _insert_document(conn: sqlite3.Connection, doc_id: str, path: str) -> None:
    """Insert a documents row satisfying every NOT NULL column."""
    now = datetime.now(timezone.utc).isoformat()
    conn.execute(
        "INSERT INTO documents (id, collection_id, path, filename, content, checksum, "
        "mtime, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (doc_id, "coll-1", path, "doc.md", "# Doc content", "checksum-1", 1000.0, now, now),
    )
    conn.commit()


def _insert_context(
    conn: sqlite3.Connection,
    ctx_id: str,
    target: str,
    content: str,
    context_type: str = "path",
) -> None:
    """Insert a contexts row."""
    now = datetime.now(timezone.utc).isoformat()
    conn.execute(
        "INSERT INTO contexts (id, target_id, context_type, content, created_at, updated_at) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (ctx_id, target, context_type, content, now, now),
    )
    conn.commit()


class TestDeleteOrphanedPathsRealSQL:
    """Prune alignment with search normalization, proven against real SQL."""

    def test_prune_preserves_symlink_mismatched_context(self, db, alias_pair):
        """THE CR-02 regression: an alias-form context for an existing document survives.

        The document is stored under the resolved path while the context
        carries the user-typed alias form of the SAME file. Prune must return
        0 and leave the row in place — it fails against the old raw-string
        NOT IN comparison, which deleted exactly this row.
        """
        resolved, alias = alias_pair
        _insert_document(db, "doc-1", resolved)
        _insert_context(db, "ctx-1", alias, "Project notes")
        repo = ContextRepository(db)

        deleted = repo.delete_orphaned_paths()

        assert deleted == 0
        survivor = repo.get_by_target(alias, "path")
        assert survivor is not None
        assert survivor.context == "Project notes"

    def test_prune_deletes_true_orphan(self, db, alias_pair, tmp_path):
        """A context for a path matching no document under ANY form is deleted."""
        resolved, _ = alias_pair
        _insert_document(db, "doc-1", resolved)
        missing = str(tmp_path / "vault" / "missing.md")
        _insert_context(db, "ctx-1", missing, "Orphan notes")
        repo = ContextRepository(db)

        deleted = repo.delete_orphaned_paths()

        assert deleted == 1
        assert repo.get_by_target(missing, "path") is None

    def test_prune_empty_contexts_returns_zero(self, db):
        """No path contexts at all: returns 0, no error (CTX-02 empty edge)."""
        _insert_document(db, "doc-1", "/vault/doc.md")
        repo = ContextRepository(db)

        assert repo.delete_orphaned_paths() == 0

    def test_prune_empty_documents_deletes_all_path_contexts(self, db):
        """No documents to match against: every path context is an orphan."""
        _insert_context(db, "ctx-1", "/vault/doc.md", "Notes")
        repo = ContextRepository(db)

        assert repo.delete_orphaned_paths() == 1
        assert repo.get_by_target("/vault/doc.md", "path") is None

    def test_prune_ignores_non_path_types(self, db):
        """Collection and global contexts are never touched by prune."""
        _insert_context(db, "ctx-c", "coll-uuid-1", "Coll desc", context_type="collection")
        _insert_context(db, "ctx-g", "global", "Global desc", context_type="global")
        repo = ContextRepository(db)

        assert repo.delete_orphaned_paths() == 0
        assert repo.get_by_target("coll-uuid-1", "collection") is not None
        assert repo.get_by_target("global", "global") is not None


class TestUpdateTargetRealSQL:
    """update_target round trip against real SQL."""

    def test_update_target_round_trip(self, db, alias_pair):
        """Re-pointing a legacy verbatim row to the canonical form works."""
        _, alias = alias_pair
        canonical = normalize_path(alias)
        ctx = PathContext(path=alias, context="old text")
        ContextRepository(db).create(ctx)

        repo = ContextRepository(db)
        assert repo.update_target(ctx.id, canonical) is True
        assert repo.get_by_target(canonical, "path") is not None
        assert repo.get_by_target(alias, "path") is None

    def test_update_target_unknown_id_returns_false(self, db):
        """An unknown context id returns False instead of raising."""
        repo = ContextRepository(db)

        assert repo.update_target("nonexistent-id", "/x/y.md") is False
