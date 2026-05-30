"""Unit tests for SchemaManager dynamic dimension and mismatch detection."""

from __future__ import annotations

import sqlite3

import pytest

from sif.database.schema import SchemaManager


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


def _create_old_path_contexts_table(db: sqlite3.Connection) -> None:
    """Create the legacy path_contexts table for migration tests."""
    db.execute("""
        CREATE TABLE path_contexts (
            id TEXT PRIMARY KEY,
            collection_id TEXT,
            path TEXT NOT NULL,
            context TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
    """)


class TestSchemaManagerMigration:
    """Tests for path_contexts -> contexts migration."""

    def test_migrates_path_contexts_to_contexts(self, vec_db):
        """Test that SchemaManager migrates old path_contexts data."""
        _create_old_path_contexts_table(vec_db)
        vec_db.execute(
            "INSERT INTO path_contexts (id, path, context, created_at, updated_at) "
            "VALUES ('ctx-1', '/notes/a.md', 'Important notes', "
            "'2024-01-01T00:00:00', '2024-01-02T00:00:00')",
        )
        vec_db.commit()

        manager = SchemaManager(vec_db, embedding_dim=384)
        manager.create_all()

        # Old table should be gone
        cursor = vec_db.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='path_contexts'",
        )
        assert cursor.fetchone() is None

        # Data should be in contexts with context_type='path'
        cursor = vec_db.execute(
            "SELECT target_id, context_type, content FROM contexts WHERE id='ctx-1'",
        )
        row = cursor.fetchone()
        assert row is not None
        assert row["target_id"] == "/notes/a.md"
        assert row["context_type"] == "path"
        assert row["content"] == "Important notes"

    def test_migration_preserves_data(self, vec_db):
        """Test that migration preserves all records and timestamps."""
        _create_old_path_contexts_table(vec_db)
        vec_db.execute(
            "INSERT INTO path_contexts (id, path, context, created_at, updated_at) "
            "VALUES ('ctx-1', '/a.md', 'desc A', '2024-01-01T10:00:00', '2024-01-02T10:00:00')",
        )
        vec_db.execute(
            "INSERT INTO path_contexts (id, path, context, created_at, updated_at) "
            "VALUES ('ctx-2', '/b.md', 'desc B', '2024-03-01T12:00:00', '2024-03-02T12:00:00')",
        )
        vec_db.commit()

        manager = SchemaManager(vec_db, embedding_dim=384)
        manager.create_all()

        cursor = vec_db.execute("SELECT * FROM contexts ORDER BY target_id")
        rows = cursor.fetchall()
        assert len(rows) == 2
        assert rows[0]["target_id"] == "/a.md"
        assert rows[0]["content"] == "desc A"
        assert rows[0]["created_at"] == "2024-01-01T10:00:00"
        assert rows[1]["target_id"] == "/b.md"
        assert rows[1]["content"] == "desc B"

    def test_migration_creates_index(self, vec_db):
        """Test that migration creates idx_contexts_target index."""
        _create_old_path_contexts_table(vec_db)
        vec_db.execute(
            "INSERT INTO path_contexts (id, path, context, created_at, updated_at) "
            "VALUES ('ctx-1', '/a.md', 'desc', '2024-01-01T00:00:00', '2024-01-02T00:00:00')",
        )
        vec_db.commit()

        manager = SchemaManager(vec_db, embedding_dim=384)
        manager.create_all()

        cursor = vec_db.execute(
            "SELECT name FROM sqlite_master WHERE type='index' AND name='idx_contexts_target'",
        )
        assert cursor.fetchone() is not None

    def test_migration_is_idempotent(self, vec_db):
        """Test that calling create_all twice does not duplicate data."""
        _create_old_path_contexts_table(vec_db)
        vec_db.execute(
            "INSERT INTO path_contexts (id, path, context, created_at, updated_at) "
            "VALUES ('ctx-1', '/a.md', 'desc', '2024-01-01T00:00:00', '2024-01-02T00:00:00')",
        )
        vec_db.commit()

        manager = SchemaManager(vec_db, embedding_dim=384)
        manager.create_all()
        manager.create_all()  # Second call

        cursor = vec_db.execute("SELECT COUNT(*) FROM contexts")
        assert cursor.fetchone()[0] == 1

    def test_no_migration_when_no_old_table(self, vec_db):
        """Test that create_all works on fresh DB without path_contexts."""
        manager = SchemaManager(vec_db, embedding_dim=384)
        manager.create_all()

        cursor = vec_db.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='contexts'",
        )
        assert cursor.fetchone() is not None

        cursor = vec_db.execute("SELECT COUNT(*) FROM contexts")
        assert cursor.fetchone()[0] == 0


class TestSchemaManagerContextsTable:
    """Tests for contexts table schema."""

    def test_contexts_table_has_check_constraint(self, vec_db):
        """Test that contexts table has CHECK constraint on context_type."""
        manager = SchemaManager(vec_db, embedding_dim=384)
        manager.create_all()

        cursor = vec_db.execute(
            "SELECT sql FROM sqlite_master WHERE type='table' AND name='contexts'",
        )
        row = cursor.fetchone()
        assert row is not None
        assert "CHECK" in row[0]
        assert "context_type" in row[0]

    def test_contexts_table_rejects_invalid_type(self, vec_db):
        """Test that INSERT with invalid context_type raises IntegrityError."""
        manager = SchemaManager(vec_db, embedding_dim=384)
        manager.create_all()

        with pytest.raises(sqlite3.IntegrityError):
            vec_db.execute(
                "INSERT INTO contexts (id, target_id, context_type, content, created_at, "
                "updated_at) VALUES ('x', '/a.md', 'invalid', 'desc', '2024-01-01', '2024-01-02')",
            )


class TestSchemaManagerVectorTables:
    def test_creates_vector_table_with_default_dimension(self, vec_db):
        manager = SchemaManager(vec_db, embedding_dim=384)
        manager._create_vector_tables()
        cursor = vec_db.execute("SELECT sql FROM sqlite_master WHERE name='document_embeddings'")
        row = cursor.fetchone()
        assert row is not None
        assert "FLOAT[384]" in row[0]

    def test_creates_vector_table_with_custom_dimension(self, vec_db):
        manager = SchemaManager(vec_db, embedding_dim=768)
        manager._create_vector_tables()
        cursor = vec_db.execute("SELECT sql FROM sqlite_master WHERE name='document_embeddings'")
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
