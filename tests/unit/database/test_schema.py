"""Unit tests for SchemaManager dynamic dimension and mismatch detection."""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from unittest.mock import patch

import pytest

from sif.database.schema import SchemaManager


def _load_vec(db: sqlite3.Connection) -> bool:
    try:
        import sqlite_vec

        db.enable_load_extension(True)
        sqlite_vec.load(db)
        db.enable_load_extension(False)
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


class _VectorDropFailureConnection:
    """Real SQLite adapter whose optional vector drop fails as SQLite would."""

    def __init__(self, connection: sqlite3.Connection) -> None:
        self._connection = connection

    def execute(self, sql: str, parameters: tuple = ()) -> sqlite3.Cursor:
        if sql == "DROP TABLE IF EXISTS document_embeddings":
            raise sqlite3.OperationalError("no such table: document_embeddings")
        return self._connection.execute(sql, parameters)

    def commit(self) -> None:
        self._connection.commit()


class TestSchemaRealSQLiteCoverage:
    """Production index, trigger, migration-failure, and reset behavior."""

    def test_create_all_builds_indexes_and_fts_delete_triggers(self):
        """Fresh production DDL indexes relational rows and keeps FTS in sync on delete."""
        conn = sqlite3.connect(":memory:")
        conn.row_factory = sqlite3.Row
        try:
            SchemaManager(conn, embedding_dim=384).create_all()
            indexes = {
                row[0]
                for row in conn.execute(
                    "SELECT name FROM sqlite_master WHERE type = 'index'",
                ).fetchall()
            }
            assert {
                "idx_documents_collection",
                "idx_documents_path",
                "idx_documents_checksum",
                "idx_chunks_document",
                "idx_contexts_target",
                "idx_llm_cache_lookup",
            } <= indexes

            now = datetime.now(timezone.utc).isoformat()
            conn.execute(
                "INSERT INTO collections (id, name, path, created_at, updated_at) "
                "VALUES ('c1', 'notes', '/vault', ?, ?)",
                (now, now),
            )
            conn.execute(
                "INSERT INTO documents (id, collection_id, path, filename, content, checksum, "
                "mtime, created_at, updated_at) VALUES ('d1', 'c1', '/vault/a.md', 'a.md', "
                "'deletemarker', 'checksum', 1.0, ?, ?)",
                (now, now),
            )
            conn.execute(
                "INSERT INTO document_chunks (id, document_id, sequence, content, created_at) "
                "VALUES ('ch1', 'd1', 0, 'chunkdeletemarker', ?)",
                (now,),
            )
            assert (
                conn.execute(
                    "SELECT COUNT(*) FROM documents_fts WHERE documents_fts MATCH 'deletemarker'",
                ).fetchone()[0]
                == 1
            )
            assert (
                conn.execute(
                    "SELECT COUNT(*) FROM chunks_fts WHERE chunks_fts MATCH 'chunkdeletemarker'",
                ).fetchone()[0]
                == 1
            )

            conn.execute("DELETE FROM document_chunks WHERE id = 'ch1'")
            conn.execute("DELETE FROM documents WHERE id = 'd1'")
            assert (
                conn.execute(
                    "SELECT COUNT(*) FROM documents_fts WHERE documents_fts MATCH 'deletemarker'",
                ).fetchone()[0]
                == 0
            )
            assert (
                conn.execute(
                    "SELECT COUNT(*) FROM chunks_fts WHERE chunks_fts MATCH 'chunkdeletemarker'",
                ).fetchone()[0]
                == 0
            )
        finally:
            conn.close()

    def test_misconfigured_fts_tables_are_rebuilt_and_seeded(self):
        """Legacy FTS definitions are replaced and their existing content is reindexed."""
        conn = sqlite3.connect(":memory:")
        conn.row_factory = sqlite3.Row
        try:
            manager = SchemaManager(conn, embedding_dim=384)
            manager._create_collections_table()
            manager._create_documents_table()
            manager._create_document_chunks_table()
            now = datetime.now(timezone.utc).isoformat()
            conn.execute(
                "INSERT INTO documents (id, collection_id, path, filename, content, checksum, "
                "mtime, created_at, updated_at) VALUES ('d1', 'c1', '/a.md', 'a.md', "
                "'legacydocmarker', 'x', 1.0, ?, ?)",
                (now, now),
            )
            conn.execute(
                "INSERT INTO document_chunks (id, document_id, sequence, content, created_at) "
                "VALUES ('ch1', 'd1', 0, 'legacychunkmarker', ?)",
                (now,),
            )
            conn.execute("CREATE VIRTUAL TABLE documents_fts USING fts5(content)")
            conn.execute("CREATE VIRTUAL TABLE chunks_fts USING fts5(content)")

            manager._create_fts_tables()

            assert (
                conn.execute(
                    "SELECT COUNT(*) FROM documents_fts "
                    "WHERE documents_fts MATCH 'legacydocmarker'",
                ).fetchone()[0]
                == 1
            )
            assert (
                conn.execute(
                    "SELECT COUNT(*) FROM chunks_fts WHERE chunks_fts MATCH 'legacychunkmarker'",
                ).fetchone()[0]
                == 1
            )
        finally:
            conn.close()

    def test_path_context_migration_rolls_back_on_failure(self):
        """A migration failure restores the savepoint and leaves the legacy table intact."""
        conn = sqlite3.connect(":memory:")
        conn.row_factory = sqlite3.Row
        try:
            _create_old_path_contexts_table(conn)
            manager = SchemaManager(conn)
            with (
                patch.object(
                    manager,
                    "_create_contexts_table",
                    side_effect=sqlite3.OperationalError("injected migration failure"),
                ),
                pytest.raises(sqlite3.OperationalError, match="injected migration failure"),
            ):
                manager._migrate_path_contexts()

            assert (
                conn.execute(
                    "SELECT name FROM sqlite_master WHERE type = 'table' "
                    "AND name = 'path_contexts'",
                ).fetchone()
                is not None
            )
            conn.execute("SAVEPOINT after_failed_migration")
            conn.execute("RELEASE SAVEPOINT after_failed_migration")
        finally:
            conn.close()

    def test_drop_all_and_stats_use_real_tables(self):
        """Reset suppresses an absent optional vector table and stats aggregate real rows."""
        conn = sqlite3.connect(":memory:")
        conn.row_factory = sqlite3.Row
        try:
            manager = SchemaManager(conn)
            manager.create_all()
            now = datetime.now(timezone.utc).isoformat()
            conn.execute(
                "INSERT INTO collections (id, name, path, created_at, updated_at) "
                "VALUES ('c1', 'notes', '/vault', ?, ?)",
                (now, now),
            )
            conn.execute(
                "INSERT INTO documents (id, collection_id, path, filename, content, checksum, "
                "file_size, mtime, created_at, updated_at) VALUES "
                "('d1', 'c1', '/a.md', 'a.md', 'abc', 'x', 3, 1.0, ?, ?)",
                (now, now),
            )
            conn.execute(
                "INSERT INTO document_chunks (id, document_id, sequence, content, created_at) "
                "VALUES ('ch1', 'd1', 0, 'abc', ?)",
                (now,),
            )
            conn.execute(
                "INSERT INTO contexts (id, target_id, context_type, content, created_at, "
                "updated_at) VALUES ('ctx1', '/a.md', 'path', 'note', ?, ?)",
                (now, now),
            )
            assert manager.get_stats() == {
                "collections": 1,
                "documents": 1,
                "chunks": 1,
                "contexts": 1,
                "total_size_bytes": 3,
            }

            reset_manager = SchemaManager(_VectorDropFailureConnection(conn))
            reset_manager.drop_all()
            assert (
                conn.execute(
                    "SELECT COUNT(*) FROM sqlite_master WHERE type = 'table' "
                    "AND name NOT LIKE 'sqlite_%'",
                ).fetchone()[0]
                == 0
            )
        finally:
            conn.close()


class TestFtsUpdateTrigger:
    """FND-06 / CR-01: external-content FTS5 update triggers must not direct-UPDATE.

    A direct UPDATE on an external-content FTS5 table corrupts the index
    ("database disk image is malformed") on medium+ content edits, so the
    document edit loop (`sif index update` on a changed note) cannot work.
    """

    MEDIUM_CONTENT = "# Title\n\n" + ("Paragraph text here. " * 400)
    EDITED_CONTENT = "# Title changed\n\n" + ("Different paragraph text. " * 400)

    @pytest.fixture
    def fts_db(self):
        conn = sqlite3.connect(":memory:")
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()

    def _insert_document(self, db: sqlite3.Connection) -> None:
        db.execute(
            "INSERT INTO collections (id, name, path, created_at, updated_at) "
            "VALUES ('c1', 'n', '/p', '2020-01-01', '2020-01-01')"
        )
        db.execute(
            "INSERT INTO documents (id, collection_id, path, filename, title, content, "
            "checksum, mtime, created_at, updated_at) "
            "VALUES ('d1', 'c1', '/p/a.md', 'a.md', 'T', ?, 'x1', 1.0, "
            "'2020-01-01', '2020-01-01')",
            (self.MEDIUM_CONTENT,),
        )
        db.commit()

    def test_medium_document_update_keeps_fts_in_sync(self, fts_db):
        """A medium+ content edit through UPDATE documents must not corrupt the index."""
        SchemaManager(fts_db, embedding_dim=384).create_all()
        self._insert_document(fts_db)

        fts_db.execute(
            "UPDATE documents SET content = ?, checksum = 'x2' WHERE id = 'd1'",
            (self.EDITED_CONTENT,),
        )
        fts_db.commit()

        assert (
            fts_db.execute(
                "SELECT COUNT(*) FROM documents_fts WHERE documents_fts MATCH 'different'"
            ).fetchone()[0]
            == 1
        )
        assert (
            fts_db.execute(
                "SELECT COUNT(*) FROM documents_fts WHERE documents_fts MATCH 'here'"
            ).fetchone()[0]
            == 0
        )
        assert fts_db.execute("PRAGMA integrity_check").fetchone()[0] == "ok"

    def test_medium_chunk_update_keeps_fts_in_sync(self, fts_db):
        """The chunks_fts update trigger uses the same safe pattern."""
        SchemaManager(fts_db, embedding_dim=384).create_all()
        self._insert_document(fts_db)
        fts_db.execute(
            "INSERT INTO document_chunks (id, document_id, sequence, content, created_at) "
            "VALUES ('ch1', 'd1', 0, ?, '2020-01-01')",
            (self.MEDIUM_CONTENT,),
        )
        fts_db.commit()

        fts_db.execute(
            "UPDATE document_chunks SET content = ? WHERE id = 'ch1'",
            (self.EDITED_CONTENT,),
        )
        fts_db.commit()

        assert (
            fts_db.execute(
                "SELECT COUNT(*) FROM chunks_fts WHERE chunks_fts MATCH 'different'"
            ).fetchone()[0]
            == 1
        )
        assert fts_db.execute("PRAGMA integrity_check").fetchone()[0] == "ok"

    def test_legacy_direct_update_trigger_is_migrated(self, fts_db):
        """create_all() replaces a pre-existing legacy direct-UPDATE trigger."""
        SchemaManager(fts_db, embedding_dim=384).create_all()

        for trigger, table in (
            ("documents_fts_update", "documents_fts"),
            ("chunks_fts_update", "chunks_fts"),
        ):
            fts_db.execute(f"DROP TRIGGER {trigger}")
            base_table = "documents" if table == "documents_fts" else "document_chunks"
            fts_db.execute(f"""
                CREATE TRIGGER {trigger}
                AFTER UPDATE ON {base_table}
                BEGIN
                    UPDATE {table} SET content = new.content WHERE rowid = old.rowid;
                END
            """)
        fts_db.commit()

        SchemaManager(fts_db, embedding_dim=384).create_all()

        for trigger, table in (
            ("documents_fts_update", "documents_fts"),
            ("chunks_fts_update", "chunks_fts"),
        ):
            sql = fts_db.execute(
                "SELECT sql FROM sqlite_master WHERE type='trigger' AND name=?",
                (trigger,),
            ).fetchone()[0]
            assert f"UPDATE {table} SET" not in sql
            assert "VALUES('delete'" in sql

    def test_modern_trigger_is_left_alone(self, fts_db):
        """create_all() does not churn an already-migrated trigger."""
        SchemaManager(fts_db, embedding_dim=384).create_all()
        trigger_sql = fts_db.execute(
            "SELECT sql FROM sqlite_master WHERE type='trigger' AND name='documents_fts_update'"
        ).fetchone()[0]

        SchemaManager(fts_db, embedding_dim=384).create_all()

        trigger_sql_after = fts_db.execute(
            "SELECT sql FROM sqlite_master WHERE type='trigger' AND name='documents_fts_update'"
        ).fetchone()[0]
        assert trigger_sql_after == trigger_sql
