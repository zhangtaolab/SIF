"""Tests for the derived ``embedded_documents`` shadow (CORR-06, D-09/D-10).

The shadow is a transactionally maintained, rebuildable index of which
documents have at least one stored embedding. These tests pin the schema
surface: the vec0-conditional DDL, the marker-gated one-time backfill
(existing documents only; orphans excluded), the table-absent force rule, a
total no-op on vec0-free databases, ``drop_all`` ordering, and the cleanup /
vacuum reconcile helper. The writer and reader contracts live in
``tests/unit/search/test_staleness.py``.
"""

from __future__ import annotations

import json
import logging
import math
import sqlite3
from pathlib import Path
from types import SimpleNamespace

import pytest

from sif.core.models import Collection, Document, DocumentChunk
from sif.database.database import Database
from sif.database.maintenance import reconcile_embedded_documents
from sif.database.repositories import CollectionRepository, DocumentRepository
from sif.database.schema import SchemaManager
from sif.embedding.identity import build_identity, read_identity, schema_embedding_dim
from sif.embedding.prompts import PromptScheme
from sif.indexing.embed_writer import StreamingEmbedWriter
from sif.models.embedding import EmbeddingConfig, ModelType
from sif.search.vector import VectorSearcher


_NOW = "2026-11-16T00:00:00+00:00"
_DIM = 8


def _load_vec(conn: sqlite3.Connection) -> bool:
    try:
        import sqlite_vec

        conn.enable_load_extension(True)
        sqlite_vec.load(conn)
        conn.enable_load_extension(False)
        return True
    except Exception:
        return False


@pytest.fixture
def vec_conn():
    """In-memory connection with the real sqlite-vec extension loaded."""
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    if not _load_vec(conn):
        conn.close()
        pytest.skip("sqlite-vec not available")
    try:
        yield conn
    finally:
        conn.close()


def _shadow_exists(conn: sqlite3.Connection) -> bool:
    return (
        conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='embedded_documents'"
        ).fetchone()
        is not None
    )


def _marker(conn: sqlite3.Connection) -> str | None:
    row = conn.execute(
        "SELECT value FROM index_meta WHERE key = 'embedded_documents_version'"
    ).fetchone()
    return row[0] if row else None


def _shadow_rows(conn: sqlite3.Connection) -> list[str]:
    return [
        row[0]
        for row in conn.execute(
            "SELECT document_id FROM embedded_documents ORDER BY document_id"
        ).fetchall()
    ]


def _insert_collection(conn: sqlite3.Connection, collection_id: str = "c1") -> None:
    conn.execute(
        "INSERT OR IGNORE INTO collections (id, name, path, created_at, updated_at)"
        " VALUES (?, ?, ?, ?, ?)",
        (collection_id, collection_id, f"/{collection_id}", _NOW, _NOW),
    )


def _insert_document(conn: sqlite3.Connection, document_id: str) -> None:
    conn.execute(
        "INSERT INTO documents (id, collection_id, path, filename, title, content,"
        " checksum, mtime, created_at, updated_at) VALUES (?, 'c1', ?, ?, ?, 'body',"
        " 'x', 1.0, ?, ?)",
        (
            document_id,
            f"/{document_id}.md",
            f"{document_id}.md",
            document_id,
            _NOW,
            _NOW,
        ),
    )


def _insert_vec_row(
    conn: sqlite3.Connection,
    document_id: str,
    embedding_id: str | None = None,
) -> None:
    """Raw vec0 insert (chunk_id is a real string: v0.1.9 rejects NULL text)."""
    conn.execute(
        "INSERT INTO document_embeddings (embedding_id, document_id, chunk_id, embedding)"
        " VALUES (?, ?, ?, vec_f32(?))",
        (
            embedding_id or f"e-{document_id}",
            document_id,
            f"c-{document_id}",
            json.dumps([0.1] * _DIM),
        ),
    )


def _seed_legacy_index(conn: sqlite3.Connection) -> SchemaManager:
    """Build a production-shaped index, then strip the shadow surface.

    Simulates a pre-Phase-21 database: documents and stored vec0 rows exist,
    but the shadow table and its marker do not. A second document gets two
    chunks and one vec row belongs to a deleted document (an orphan).
    """
    manager = SchemaManager(conn, embedding_dim=_DIM)
    manager.create_all()
    _insert_collection(conn)
    _insert_document(conn, "d1")
    _insert_document(conn, "d2")
    _insert_vec_row(conn, "d1")
    _insert_vec_row(conn, "d1", embedding_id="e-d1-b")
    _insert_vec_row(conn, "d2")
    _insert_vec_row(conn, "d-orphan")
    conn.execute("DELETE FROM index_meta WHERE key = 'embedded_documents_version'")
    conn.execute("DROP TABLE embedded_documents")
    conn.commit()
    return manager


class _RecordingConnection:
    """Connection proxy recording every SQL statement (schema-total check)."""

    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn
        self.statements: list[str] = []

    def execute(self, sql: str, params: tuple[object, ...] = ()) -> sqlite3.Cursor:
        self.statements.append(sql)
        return self._conn.execute(sql, params)

    def commit(self) -> None:
        self._conn.commit()

    def __enter__(self) -> _RecordingConnection:
        self._conn.__enter__()
        return self

    def __exit__(self, *exc_info: object) -> object:
        return self._conn.__exit__(*exc_info)

    def __getattr__(self, name: str) -> object:
        return getattr(self._conn, name)


class _IdentityModel:
    """Loaded-model double exposing only the identity dimension."""

    def __init__(self, dimension: int) -> None:
        self.dimension = dimension


def _unit_vector(dim: int = _DIM) -> list[float]:
    """A deterministic unit-L2 vector of ``dim`` dimensions."""
    component = 1.0 / math.sqrt(dim)
    return [component] * dim


def _identity():
    """Build a real embedder identity for the fake loaded model."""
    return build_identity(
        EmbeddingConfig(
            model_type=ModelType.MODELSCOPE,
            model_name="test",
            embedding_dim=_DIM,
        ),
        _IdentityModel(_DIM),
        PromptScheme(None, None, True),
    )


class _OneChunkChunker:
    """Return exactly one chunk holding the document body."""

    def chunk(self, text: str) -> list[DocumentChunk]:
        """Build one chunk from the text."""
        return [DocumentChunk(content=text, sequence=0, start_pos=0, end_pos=len(text))]


class _OneChunkManager:
    """Fake manager returning one unit vector per input text."""

    def __init__(self) -> None:
        self.calls: list[list[str]] = []

    def embed_documents(self, texts: list[str]) -> SimpleNamespace:
        """Record the call and return unit vectors."""
        self.calls.append(list(texts))
        return SimpleNamespace(embeddings=[_unit_vector() for _ in texts])


class TestFreshDatabase:
    """A fresh vec0 index creates the shadow and writes the marker at zero cost."""

    def test_create_all_creates_shadow_and_marker_without_warning(self, vec_conn, caplog) -> None:
        with caplog.at_level(logging.WARNING):
            SchemaManager(vec_conn, embedding_dim=_DIM).create_all()

        assert _shadow_exists(vec_conn)
        assert _marker(vec_conn) == "1"
        assert _shadow_rows(vec_conn) == []
        assert [r for r in caplog.records if r.levelno >= logging.WARNING] == []

    def test_drop_all_drops_shadow_and_parent_under_fk_enforcement(self) -> None:
        """The FK child drops before ``documents``; a populated DB drops cleanly."""
        conn = sqlite3.connect(":memory:")
        conn.row_factory = sqlite3.Row
        if not _load_vec(conn):
            conn.close()
            pytest.skip("sqlite-vec not available")
        try:
            conn.execute("PRAGMA foreign_keys = ON")
            manager = SchemaManager(conn, embedding_dim=_DIM)
            manager.create_all()
            _insert_collection(conn)
            _insert_document(conn, "d1")
            _insert_vec_row(conn, "d1")
            conn.execute("INSERT INTO embedded_documents(document_id) VALUES ('d1')")
            conn.commit()

            manager.drop_all()

            assert not _shadow_exists(conn)
            assert (
                conn.execute(
                    "SELECT 1 FROM sqlite_master WHERE type='table' AND name='documents'"
                ).fetchone()
                is None
            )
        finally:
            conn.close()


class TestFreshIndexOnlyNewWrites:
    """D-19: the first embed adds only the documented Phase 21 side effects."""

    def test_first_embed_writes_only_identity_shadow_and_markers(self, tmp_path: Path) -> None:
        """Beyond the pre-phase writes, a fresh first embed adds exactly the
        identity row, the shadow row, and the two version markers."""
        db = Database(tmp_path / "fresh.db")
        db.init_schema(embedding_dim=_DIM)
        if schema_embedding_dim(db.connection) is None:
            db.close()
            pytest.skip("sqlite-vec not available")
        try:
            with db.connection:
                coll = Collection(name="notes", path="/notes")
                CollectionRepository(db.connection).create(coll)
                doc = Document(
                    path="/notes/a.md",
                    collection_id=coll.id,
                    content="alpha body",
                    title="A",
                )
                DocumentRepository(db.connection).create(doc)

            searcher = VectorSearcher(db.connection, _DIM)
            writer = StreamingEmbedWriter(
                db.connection,
                _OneChunkManager(),
                _OneChunkChunker(),
                searcher,
                _identity(),
                batch_size=32,
                write_identity=True,
            )
            assert writer.embed_document(doc) == 1

            keys = {
                row[0] for row in db.connection.execute("SELECT key FROM index_meta").fetchall()
            }
            assert keys == {
                "embedded_documents_version",
                "metadata_values_version",
                "embedder.identity",
            }
            assert _shadow_rows(db.connection) == [doc.id]
            stored = read_identity(db.connection)
            assert stored is not None
            assert stored.source == "verified"
        finally:
            db.close()


class TestLegacyBackfill:
    """One idempotent pass derives existing documents; orphans never enter."""

    def test_legacy_database_backfills_existing_documents_only(self, vec_conn, caplog) -> None:
        manager = _seed_legacy_index(vec_conn)
        caplog.clear()

        with caplog.at_level(logging.WARNING):
            manager.create_all()

        assert _marker(vec_conn) == "1"
        # d1 (two chunks) and d2 are sealed; the orphan vec row is excluded.
        assert _shadow_rows(vec_conn) == ["d1", "d2"]
        notices = [r for r in caplog.records if r.levelno == logging.WARNING]
        assert len(notices) == 1
        assert "2 documents" in notices[0].getMessage()

    def test_second_create_all_is_a_no_op(self, vec_conn, caplog) -> None:
        manager = _seed_legacy_index(vec_conn)
        manager.create_all()
        caplog.clear()

        with caplog.at_level(logging.WARNING):
            manager.create_all()

        assert _shadow_rows(vec_conn) == ["d1", "d2"]
        assert [r for r in caplog.records if r.levelno >= logging.WARNING] == []

    def test_dropped_table_with_surviving_marker_forces_rebuild(self, vec_conn) -> None:
        """A stale marker must never leave a dropped/recreated table empty."""
        manager = _seed_legacy_index(vec_conn)
        manager.create_all()
        vec_conn.execute("DROP TABLE embedded_documents")
        vec_conn.commit()
        assert _marker(vec_conn) == "1"
        assert not _shadow_exists(vec_conn)

        manager.create_all()

        assert _shadow_exists(vec_conn)
        assert _shadow_rows(vec_conn) == ["d1", "d2"]

    def test_persisted_orphan_vector_row_is_excluded(self, vec_conn) -> None:
        manager = _seed_legacy_index(vec_conn)

        manager.create_all()

        assert _shadow_rows(vec_conn) == ["d1", "d2"]
        assert (
            vec_conn.execute(
                "SELECT COUNT(*) FROM document_embeddings WHERE document_id = 'd-orphan'"
            ).fetchone()[0]
            == 1
        ), "the orphan vec0 row itself is untouched (reconcile's job)"


class TestVec0FreeDatabase:
    """No vec0: no shadow DDL, no marker, and create_all never raises."""

    def test_create_all_is_total_without_vec0(self) -> None:
        conn = sqlite3.connect(":memory:")
        conn.row_factory = sqlite3.Row
        try:
            manager = SchemaManager(conn, embedding_dim=_DIM)
            manager.create_all()

            assert not _shadow_exists(conn)
            assert _marker(conn) is None
            # The explicit "do not touch this database" signal.
            assert manager._create_embedded_documents_table() is None
        finally:
            conn.close()

    def test_backfill_issues_no_statement_against_the_absent_table(self) -> None:
        conn = sqlite3.connect(":memory:")
        conn.row_factory = sqlite3.Row
        try:
            recording = _RecordingConnection(conn)
            SchemaManager(recording, embedding_dim=_DIM).create_all()

            assert not any(
                "FROM embedded_documents" in sql or "INTO embedded_documents" in sql
                for sql in recording.statements
            )
            assert not _shadow_exists(conn)
            assert _marker(conn) is None
        finally:
            conn.close()


class TestReconcileEmbeddedDocuments:
    """Cleanup/vacuum repair: delete stale rows, insert missing existing rows."""

    def _seed_divergence(self, conn: sqlite3.Connection) -> None:
        SchemaManager(conn, embedding_dim=_DIM).create_all()
        _insert_collection(conn)
        _insert_document(conn, "d1")
        _insert_document(conn, "d2")
        _insert_document(conn, "d3")
        _insert_vec_row(conn, "d1")
        _insert_vec_row(conn, "d2")
        _insert_vec_row(conn, "d-gone")  # orphan: document deleted, vectors not purged
        conn.execute("DELETE FROM embedded_documents")
        # d1 is correct; d3 has no embeddings; d-gone has no document.
        conn.execute("INSERT INTO embedded_documents(document_id) VALUES ('d1')")
        conn.execute("INSERT INTO embedded_documents(document_id) VALUES ('d3')")
        conn.execute("INSERT INTO embedded_documents(document_id) VALUES ('d-gone')")
        conn.commit()

    def test_reconcile_repairs_divergence(self, vec_conn) -> None:
        self._seed_divergence(vec_conn)

        deleted, inserted = reconcile_embedded_documents(vec_conn)

        assert (deleted, inserted) == (2, 1)
        assert _shadow_rows(vec_conn) == ["d1", "d2"]

    def test_reconcile_without_table_returns_zero(self) -> None:
        conn = sqlite3.connect(":memory:")
        try:
            assert reconcile_embedded_documents(conn) == (0, 0)
        finally:
            conn.close()

    def test_reconcile_leaves_the_commit_to_the_caller(self, vec_conn) -> None:
        self._seed_divergence(vec_conn)
        before = _shadow_rows(vec_conn)

        reconcile_embedded_documents(vec_conn)

        assert vec_conn.in_transaction
        vec_conn.rollback()
        assert _shadow_rows(vec_conn) == before
