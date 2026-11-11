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

import os
import sqlite3
import time
from datetime import datetime, timedelta, timezone

import pytest

from sif.core.models import Collection, Document, DocumentChunk, PathContext
from sif.database.repositories import (
    CollectionRepository,
    ContextRepository,
    DocumentChunkRepository,
    DocumentRepository,
    LLMCacheRepository,
)
from sif.database.schema import SchemaManager
from sif.utils.paths import normalize_path


@pytest.fixture
def db():
    """Real in-memory SQLite with the production documents/contexts DDL."""
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    manager = SchemaManager(conn)
    manager._create_collections_table()
    manager._create_documents_table()
    manager._create_document_chunks_table()
    manager._create_contexts_table()
    manager._create_llm_cache_table()
    manager._create_fts_tables()
    manager._create_indexes()
    yield conn
    conn.close()


@pytest.fixture
def east_of_utc(monkeypatch):
    """Force a fixed east-of-UTC local zone (WR-09 legacy naive-local rows).

    ``time.tzset`` mutates process-global state, so the prior TZ is restored
    unconditionally in teardown (Asia/Shanghai is fixed UTC+8, no DST).
    """
    prior = os.environ.get("TZ")
    monkeypatch.setenv("TZ", "Asia/Shanghai")
    time.tzset()
    try:
        yield
    finally:
        if prior is None:
            monkeypatch.delenv("TZ", raising=False)
        else:
            monkeypatch.setenv("TZ", prior)
        time.tzset()


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
    if conn.execute("SELECT 1 FROM collections WHERE id = 'coll-1'").fetchone() is None:
        conn.execute(
            "INSERT INTO collections (id, name, path, created_at, updated_at) "
            "VALUES ('coll-1', 'collection-1', '/vault', ?, ?)",
            (now, now),
        )
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

    def test_prune_survives_malformed_tilde_row(self, db, alias_pair):
        """REVIEW WR-01: one malformed '~unknownuser/...' row must not crash prune.

        delete_orphaned_paths normalizes EVERY path-type context row; before
        normalize_path became a total function a single un-expandable row
        raised RuntimeError and crashed the whole prune. The malformed row
        matches no document under any form, so it is a true orphan and is
        deleted — the operation completes instead of raising.
        """
        resolved, alias = alias_pair
        poison = "~sif-no-such-user-7f3a/notes/doc.md"
        _insert_document(db, "doc-1", resolved)
        _insert_context(db, "ctx-poison", poison, "Poison")
        _insert_context(db, "ctx-1", alias, "Project notes")
        repo = ContextRepository(db)

        deleted = repo.delete_orphaned_paths()

        assert deleted == 1
        assert repo.get_by_target(alias, "path") is not None
        assert repo.get_by_target(poison, "path") is None


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


class TestRepositoryCoverage:
    """Repository CRUD and cache behavior against extension-free production DDL."""

    def test_collection_document_chunk_and_context_round_trip(self, db):
        """The tracer: writes and reads real entities, updates them, then deletes them."""
        collection = self._collection_round_trip(db)
        document = self._document_chunk_and_context_round_trip(db, collection)
        collections = CollectionRepository(db)
        documents = DocumentRepository(db)
        chunks = DocumentChunkRepository(db)
        contexts = ContextRepository(db)

        document.title = "Updated title"
        document.content = "Updated uniquemarker"
        document.metadata = {"author": "Grace"}
        assert documents.update(document) is document
        updated_document = documents.get_by_id(document.id)
        assert updated_document is not None
        assert updated_document.title == "Updated title"
        assert updated_document.metadata == {"author": "Grace"}
        assert (
            db.execute(
                "SELECT COUNT(*) FROM documents_fts WHERE documents_fts MATCH 'uniquemarker'",
            ).fetchone()[0]
            == 1
        )

        context = contexts.get_by_path(document.path)
        assert context is not None
        context.context = "Updated context"
        assert contexts.update(context) is context
        updated_context = contexts.get_by_path(document.path)
        assert updated_context is not None
        assert updated_context.context == "Updated context"

        assert documents.delete(document.id) is True
        assert documents.get_by_id(document.id) is None
        assert chunks.get_by_document(document.id) == []
        assert contexts.delete(context.id) is True
        assert contexts.get_by_path(document.path) is None
        assert collections.delete(collection.id) is True
        assert collections.get_by_id(collection.id) is None

    def _collection_round_trip(self, db: sqlite3.Connection) -> Collection:
        """Create, query, and update one collection through real repository calls."""
        collection = Collection(
            id="coll-round-trip",
            name="notes",
            path="/vault",
            ignore_patterns=[".git"],
            description="Original description",
            pre_update_cmd="git pull",
        )
        collections = CollectionRepository(db)
        assert collections.create(collection) is collection
        loaded_collection = collections.get_by_id(collection.id)
        assert loaded_collection == collection
        assert collections.get_by_name("notes") == collection
        assert collections.exists("notes") is True
        assert collections.list_all() == [collection]
        assert collections.list_enabled() == [collection]

        collection.description = "Updated description"
        collection.include_by_default = False
        collection.document_count = 1
        collection.chunk_count = 2
        collection.last_indexed_at = datetime.now(timezone.utc)
        assert collections.update(collection) is collection
        updated_collection = collections.get_by_id(collection.id)
        assert updated_collection is not None
        assert updated_collection.description == "Updated description"
        assert updated_collection.last_indexed_at == collection.last_indexed_at
        assert collections.list_enabled() == []
        return collection

    def _document_chunk_and_context_round_trip(
        self,
        db: sqlite3.Connection,
        collection: Collection,
    ) -> Document:
        """Create and query the document, chunk, and context parts of the tracer."""
        document = Document(
            id="doc-round-trip",
            collection_id=collection.id,
            path="/vault/note.md",
            content="Original needle",
            metadata={"author": "Ada"},
        )
        documents = DocumentRepository(db)
        assert documents.create(document) is document
        assert documents.get_by_id(document.id) == document
        assert documents.get_by_path(document.path, collection.id) == document
        assert documents.get_by_filename("note.md") == document
        assert documents.list_by_collection(collection.id) == [document]
        assert documents.exists(document.path, collection.id) is True
        assert documents.count_by_collection(collection.id) == 1
        assert documents.get_checksum(document.id) == document.checksum

        chunks = DocumentChunkRepository(db)
        chunk = DocumentChunk(
            id="chunk-round-trip",
            document_id=document.id,
            content="Original needle",
            sequence=0,
            start_pos=0,
            end_pos=15,
            token_count=2,
            embedding_id="embedding-1",
        )
        assert chunks.create_many([chunk]) == [chunk]
        assert chunks.get_by_document(document.id) == [chunk]

        context = PathContext(path=document.path, context="Important note")
        contexts = ContextRepository(db)
        assert contexts.create(context) is context
        loaded_context = contexts.get_by_path(document.path)
        assert loaded_context is not None
        assert loaded_context.id == context.id
        assert loaded_context.path == context.path
        assert loaded_context.context == context.context
        assert contexts.get_by_target(document.path) == loaded_context
        assert contexts.list_all() == [loaded_context]
        assert contexts.list_by_type("path") == [loaded_context]
        return document

    def test_collection_missing_rows_and_disabled_filter(self, db):
        """Missing IDs/names return None or False, and disabled collections are filtered."""
        repo = CollectionRepository(db)
        disabled = Collection(name="disabled", path="/disabled", include_by_default=False)
        repo.create(disabled)

        assert repo.get_by_id("missing") is None
        assert repo.get_by_name("missing") is None
        assert repo.exists("missing") is False
        assert repo.delete("missing") is False
        assert repo.list_enabled() == []
        assert repo.list_all() == [disabled]

    def test_document_lookup_missing_and_empty_results(self, db):
        """Document queries return explicit empty results for unknown keys."""
        collection = Collection(id="coll-empty", name="empty", path="/empty")
        CollectionRepository(db).create(collection)
        repo = DocumentRepository(db)

        assert repo.get_by_id("missing") is None
        assert repo.get_by_path("/missing.md", collection.id) is None
        assert repo.get_by_filename("missing.md") is None
        assert repo.list_by_collection(collection.id) == []
        assert repo.get_checksum("missing") is None
        assert repo.exists("/missing.md", collection.id) is False
        assert repo.count_by_collection(collection.id) == 0
        assert repo.delete("missing") is False
        assert repo.delete_by_collection("missing") == 0

    def test_delete_by_collection_removes_documents_and_their_chunks(self, db):
        """Collection deletion uses the real document/chunk relationships and returns counts."""
        collection = Collection(id="coll-delete", name="delete", path="/delete")
        CollectionRepository(db).create(collection)
        repo = DocumentRepository(db)
        first = Document(
            id="doc-first",
            collection_id=collection.id,
            path="/delete/first.md",
            content="first",
        )
        second = Document(
            id="doc-second",
            collection_id=collection.id,
            path="/delete/second.md",
            content="second",
        )
        repo.create(first)
        repo.create(second)
        chunks = DocumentChunkRepository(db)
        for document in (first, second):
            chunks.create(
                DocumentChunk(
                    id=f"chunk-{document.id}",
                    document_id=document.id,
                    content=document.content,
                    sequence=0,
                    start_pos=0,
                    end_pos=len(document.content),
                ),
            )

        assert repo.delete_by_collection(collection.id) == 2
        assert repo.list_by_collection(collection.id) == []
        assert chunks.get_by_document(first.id) == []
        assert chunks.get_by_document(second.id) == []

    def test_create_many_empty_and_chunk_ordering(self, db):
        """Batch creation preserves its input and chunk reads follow sequence order."""
        _insert_document(db, "doc-ordered", "/vault/ordered.md")
        repo = DocumentChunkRepository(db)
        assert repo.create_many([]) == []
        later = DocumentChunk(
            id="chunk-later",
            document_id="doc-ordered",
            content="later",
            sequence=2,
            start_pos=10,
            end_pos=15,
        )
        earlier = DocumentChunk(
            id="chunk-earlier",
            document_id="doc-ordered",
            content="earlier",
            sequence=1,
            start_pos=0,
            end_pos=7,
        )
        repo.create_many([later, earlier])

        assert [chunk.id for chunk in repo.get_by_document("doc-ordered")] == [
            "chunk-earlier",
            "chunk-later",
        ]
        assert repo.get_by_document("missing") == []
        assert repo.delete_by_document("missing") == 0
        assert repo.delete_by_document("doc-ordered") == 2

    def test_context_scopes_updates_and_missing_ids(self, db):
        """Context lookups preserve type scoping and missing IDs do not raise."""
        repo = ContextRepository(db)
        path = PathContext(id="ctx-path", path="/vault/z.md", context="path context")
        collection = PathContext(
            id="ctx-collection",
            path="coll-context",
            context="collection context",
            context_type="collection",
        )
        global_context = PathContext(
            id="ctx-global",
            path="global",
            context="global context",
            context_type="global",
        )
        for context in (path, collection, global_context):
            repo.create(context)

        assert [context.id for context in repo.list_all()] == [
            "ctx-collection",
            "ctx-global",
            "ctx-path",
        ]
        assert [context.id for context in repo.list_by_collection("coll-context")] == [
            "ctx-collection",
        ]
        assert repo.list_by_collection("missing") == []
        assert [context.id for context in repo.list_by_type("global")] == ["ctx-global"]
        assert repo.get_by_target("missing") is None
        assert repo.get_by_path("missing") is None

        missing_update = PathContext(id="missing", path="/missing.md", context="ignored")
        assert repo.update(missing_update) is missing_update
        assert db.execute("SELECT COUNT(*) FROM contexts WHERE id = 'missing'").fetchone()[0] == 0
        assert repo.delete("missing") is False

    def test_llm_cache_hit_expiry_replacement_and_clear(self, db):
        """LLM cache persists responses, replaces entries, and clears only expired rows."""
        repo = LLMCacheRepository(db)
        assert repo.get("model", "missing") is None

        repo.set("model", "persistent", "prompt", "first response")
        assert repo.get("model", "persistent") == "first response"
        repo.set("model", "persistent", "prompt", "replacement")
        assert repo.get("model", "persistent") == "replacement"

        repo.set("model", "short-lived", "prompt", "future response", ttl_seconds=3600)
        assert repo.get("model", "short-lived") == "future response"
        assert repo.clear_expired() == 0

        past = datetime.fromtimestamp(1, timezone.utc).isoformat()
        db.execute("UPDATE llm_cache SET expires_at = ? WHERE prompt_hash = 'persistent'", (past,))
        assert repo.get("model", "persistent") is None
        assert repo.clear_expired() == 1
        assert repo.get("model", "short-lived") == "future response"


class TestLLMCacheExpiryWR09:
    """WR-09: cache expiry must compare parsed instants, not ISO string order."""

    @pytest.mark.usefixtures("east_of_utc")
    def test_set_stores_aware_utc_expiry(self, db):
        """set() writes an aware-UTC (+00:00) expiry at the correct instant."""
        repo = LLMCacheRepository(db)
        repo.set("model", "hash", "prompt", "response", ttl_seconds=3600)

        value = db.execute(
            "SELECT expires_at FROM llm_cache WHERE prompt_hash = 'hash'"
        ).fetchone()["expires_at"]

        assert value.endswith("+00:00")
        assert abs(
            datetime.fromisoformat(value) - (datetime.now(timezone.utc) + timedelta(seconds=3600))
        ) < timedelta(seconds=5)

    @pytest.mark.skipif(not hasattr(time, "tzset"), reason="tzset unavailable")
    @pytest.mark.usefixtures("east_of_utc")
    def test_clear_expired_removes_legacy_naive_local_expired_row(self, db):
        """Legacy naive-local rows expire by instant east of UTC (WR-09 read side).

        The rows use the exact naive-local form the old ``set`` writer
        produced; lexicographic order puts their wall time ahead of the
        aware-UTC now string, so the old predicate kept the expired row.
        """
        now = datetime.now(timezone.utc)
        for row_id, instant in (
            ("legacy-expired", (now - timedelta(hours=1)).timestamp()),
            ("legacy-fresh", (now + timedelta(hours=1)).timestamp()),
        ):
            db.execute(
                "INSERT INTO llm_cache "
                "(id, model_name, prompt_hash, prompt, response, created_at, expires_at) "
                "VALUES (?, 'm', ?, 'p', 'r', ?, ?)",
                (
                    row_id,
                    f"hash-{row_id}",
                    now.isoformat(),
                    datetime.fromtimestamp(instant).isoformat(),
                ),
            )

        repo = LLMCacheRepository(db)
        assert repo.clear_expired() == 1
        assert (
            db.execute("SELECT COUNT(*) FROM llm_cache WHERE id = 'legacy-expired'").fetchone()[0]
            == 0
        )
        assert (
            db.execute("SELECT COUNT(*) FROM llm_cache WHERE id = 'legacy-fresh'").fetchone()[0]
            == 1
        )

    def test_clear_expired_aware_utc_rows(self, db):
        """Aware-UTC expired rows are deleted; aware-UTC fresh rows survive."""
        now = datetime.now(timezone.utc)
        for row_id, expires_at in (
            ("aware-expired", (now - timedelta(hours=1)).isoformat()),
            ("aware-fresh", (now + timedelta(hours=1)).isoformat()),
        ):
            db.execute(
                "INSERT INTO llm_cache "
                "(id, model_name, prompt_hash, prompt, response, created_at, expires_at) "
                "VALUES (?, 'm', ?, 'p', 'r', ?, ?)",
                (row_id, f"hash-{row_id}", now.isoformat(), expires_at),
            )

        repo = LLMCacheRepository(db)
        assert repo.clear_expired() == 1
        assert (
            db.execute("SELECT COUNT(*) FROM llm_cache WHERE id = 'aware-fresh'").fetchone()[0] == 1
        )

    def test_clear_expired_retains_null_and_unparseable(self, db):
        """NULL and unparseable expiries are retained; cleanup never guesses."""
        now = datetime.now(timezone.utc).isoformat()
        for row_id, expires_at in (("null-expiry", None), ("garbage-expiry", "not-a-timestamp")):
            db.execute(
                "INSERT INTO llm_cache "
                "(id, model_name, prompt_hash, prompt, response, created_at, expires_at) "
                "VALUES (?, 'm', ?, 'p', 'r', ?, ?)",
                (row_id, f"hash-{row_id}", now, expires_at),
            )

        repo = LLMCacheRepository(db)
        assert repo.clear_expired() == 0
        assert db.execute("SELECT COUNT(*) FROM llm_cache").fetchone()[0] == 2
