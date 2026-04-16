"""Unit tests for SchemaManager dynamic dimension and mismatch detection."""

from __future__ import annotations

import sqlite3

import pytest

from docsift.database.schema import SchemaManager


def _load_vec(db: sqlite3.Connection) -> bool:
    try:
        db.enable_load_extension(True)
        db.load_extension("vec0")
        return True
    except Exception:
        return False


@pytest.fixture
def vec_db():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    try:
        if not _load_vec(conn):
            pytest.skip("sqlite-vec not available")
        yield conn
    finally:
        conn.close()


class TestSchemaManagerVectorTables:
    def test_creates_vector_table_with_default_dimension(self, vec_db):
        manager = SchemaManager(vec_db, embedding_dim=384)
        manager._create_vector_tables()
        cursor = vec_db.execute(
            "SELECT sql FROM sqlite_master WHERE name='document_embeddings'"
        )
        row = cursor.fetchone()
        assert row is not None
        assert "FLOAT[384]" in row[0]

    def test_creates_vector_table_with_custom_dimension(self, vec_db):
        manager = SchemaManager(vec_db, embedding_dim=768)
        manager._create_vector_tables()
        cursor = vec_db.execute(
            "SELECT sql FROM sqlite_master WHERE name='document_embeddings'"
        )
        row = cursor.fetchone()
        assert "FLOAT[768]" in row[0]

    def test_mismatch_detection_fails_fast(self, vec_db):
        manager = SchemaManager(vec_db, embedding_dim=384)
        manager._create_vector_tables()
        manager2 = SchemaManager(vec_db, embedding_dim=768)
        with pytest.raises(RuntimeError, match="Embedding dimension mismatch"):
            manager2._create_vector_tables()

    def test_same_dimension_does_not_raise(self, vec_db):
        manager = SchemaManager(vec_db, embedding_dim=384)
        manager._create_vector_tables()
        manager2 = SchemaManager(vec_db, embedding_dim=384)
        manager2._create_vector_tables()  # should not raise

    def test_no_vec_available_does_not_create_table(self):
        conn = sqlite3.connect(":memory:")
        conn.row_factory = sqlite3.Row
        manager = SchemaManager(conn, embedding_dim=384)
        manager._create_vector_tables()
        cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = {row[0] for row in cursor.fetchall()}
        assert "document_embeddings" not in tables
        conn.close()
