"""Database schema definitions for SIF."""

from __future__ import annotations

import contextlib
import re
import sqlite3


class SchemaManager:
    """Manages database schema creation and migrations."""

    def __init__(self, db: sqlite3.Connection, embedding_dim: int = 384) -> None:
        """Initialize the schema manager."""
        self.db = db
        self.embedding_dim = embedding_dim

    def create_all(self) -> None:
        """Create all database tables and indexes."""
        self._create_collections_table()
        self._create_documents_table()
        self._create_document_chunks_table()
        self._migrate_path_contexts()
        self._create_contexts_table()
        self._create_llm_cache_table()
        self._create_fts_tables()
        self._create_vector_tables()
        self._create_indexes()

    def _add_column_if_missing(self, table: str, column: str, dtype: str) -> None:
        """Add a column to a table if it does not already exist."""
        cursor = self.db.execute(f"PRAGMA table_info({table})")
        columns = {row["name"] for row in cursor.fetchall()}
        if column not in columns:
            self.db.execute(f"ALTER TABLE {table} ADD COLUMN {column} {dtype}")

    def _create_collections_table(self) -> None:
        """Create collections table."""
        self.db.execute("""
            CREATE TABLE IF NOT EXISTS collections (
                id TEXT PRIMARY KEY,
                name TEXT UNIQUE NOT NULL,
                path TEXT NOT NULL,
                pattern TEXT DEFAULT '**/*.md',
                ignore_patterns TEXT DEFAULT '[]',
                include_by_default INTEGER DEFAULT 1,
                description TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                last_indexed_at TEXT,
                document_count INTEGER DEFAULT 0,
                chunk_count INTEGER DEFAULT 0
            )
        """)
        self._add_column_if_missing("collections", "pre_update_cmd", "TEXT")

    def _create_documents_table(self) -> None:
        """Create documents table."""
        self.db.execute("""
            CREATE TABLE IF NOT EXISTS documents (
                id TEXT PRIMARY KEY,
                collection_id TEXT NOT NULL,
                path TEXT NOT NULL,
                filename TEXT NOT NULL,
                title TEXT,
                content TEXT NOT NULL,
                checksum TEXT NOT NULL,
                file_size INTEGER DEFAULT 0,
                mtime REAL NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                metadata TEXT DEFAULT '{}',
                FOREIGN KEY (collection_id) REFERENCES collections(id) ON DELETE CASCADE
            )
        """)

    def _create_document_chunks_table(self) -> None:
        """Create document chunks table."""
        self.db.execute("""
            CREATE TABLE IF NOT EXISTS document_chunks (
                id TEXT PRIMARY KEY,
                document_id TEXT NOT NULL,
                sequence INTEGER NOT NULL,
                content TEXT NOT NULL,
                start_pos INTEGER DEFAULT 0,
                end_pos INTEGER DEFAULT 0,
                token_count INTEGER DEFAULT 0,
                embedding_id TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE
            )
        """)

    def _create_contexts_table(self) -> None:
        """Create unified contexts table."""
        self.db.execute("""
            CREATE TABLE IF NOT EXISTS contexts (
                id TEXT PRIMARY KEY,
                target_id TEXT NOT NULL,
                context_type TEXT NOT NULL CHECK(context_type IN ('path', 'collection', 'global')),
                content TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)

    def _migrate_path_contexts(self) -> None:
        """Migrate path_contexts -> contexts atomically using SAVEPOINT."""
        cursor = self.db.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='path_contexts'",
        )
        if not cursor.fetchone():
            return

        self.db.execute("SAVEPOINT sp_migration")
        try:
            self._create_contexts_table()
            self.db.execute("""
                INSERT INTO contexts (id, target_id, context_type, content, created_at, updated_at)
                SELECT id, path, 'path', context, created_at, updated_at
                FROM path_contexts
            """)
            self.db.execute("DROP TABLE path_contexts")
            self.db.execute("""
                CREATE INDEX IF NOT EXISTS idx_contexts_target
                ON contexts(target_id, context_type)
            """)
            self.db.execute("RELEASE SAVEPOINT sp_migration")
        except Exception:
            self.db.execute("ROLLBACK TO SAVEPOINT sp_migration")
            raise

    def _create_llm_cache_table(self) -> None:
        """Create LLM cache table."""
        self.db.execute("""
            CREATE TABLE IF NOT EXISTS llm_cache (
                id TEXT PRIMARY KEY,
                model_name TEXT NOT NULL,
                prompt_hash TEXT NOT NULL,
                prompt TEXT NOT NULL,
                response TEXT NOT NULL,
                created_at TEXT NOT NULL,
                expires_at TEXT,
                UNIQUE(model_name, prompt_hash)
            )
        """)

    def _create_fts_tables(self) -> None:
        """Create FTS5 virtual tables for full-text search with triggers."""

        def _fts_is_misconfigured(table_name: str, expected_content: str) -> bool:
            """Check if an existing FTS5 table lacks the correct content= setting."""
            cursor = self.db.execute(
                "SELECT sql FROM sqlite_master WHERE type='table' AND name=?",
                (table_name,),
            )
            row = cursor.fetchone()
            if not row:
                return False  # table does not exist; not misconfigured
            sql = row[0] or ""
            return f"content='{expected_content}'" not in sql

        needs_rebuild_docs = _fts_is_misconfigured("documents_fts", "documents")
        needs_rebuild_chunks = _fts_is_misconfigured("chunks_fts", "document_chunks")

        if needs_rebuild_docs:
            self.db.execute("DROP TABLE IF EXISTS documents_fts")
        if needs_rebuild_chunks:
            self.db.execute("DROP TABLE IF EXISTS chunks_fts")

        # Documents FTS table with external content
        self.db.execute("""
            CREATE VIRTUAL TABLE IF NOT EXISTS documents_fts USING fts5(
                content,
                content='documents',
                content_rowid='rowid',
                tokenize='porter'
            )
        """)

        # Chunks FTS table with external content
        self.db.execute("""
            CREATE VIRTUAL TABLE IF NOT EXISTS chunks_fts USING fts5(
                content,
                content='document_chunks',
                content_rowid='rowid',
                tokenize='porter'
            )
        """)

        # Triggers for documents_fts
        self.db.execute("""
            CREATE TRIGGER IF NOT EXISTS documents_fts_insert
            AFTER INSERT ON documents
            BEGIN
                INSERT INTO documents_fts(rowid, content) VALUES (new.rowid, new.content);
            END
        """)
        self.db.execute("""
            CREATE TRIGGER IF NOT EXISTS documents_fts_update
            AFTER UPDATE ON documents
            BEGIN
                UPDATE documents_fts SET content = new.content WHERE rowid = old.rowid;
            END
        """)
        self.db.execute("""
            CREATE TRIGGER IF NOT EXISTS documents_fts_delete
            AFTER DELETE ON documents
            BEGIN
                DELETE FROM documents_fts WHERE rowid = old.rowid;
            END
        """)

        # Triggers for chunks_fts
        self.db.execute("""
            CREATE TRIGGER IF NOT EXISTS chunks_fts_insert
            AFTER INSERT ON document_chunks
            BEGIN
                INSERT INTO chunks_fts(rowid, content) VALUES (new.rowid, new.content);
            END
        """)
        self.db.execute("""
            CREATE TRIGGER IF NOT EXISTS chunks_fts_update
            AFTER UPDATE ON document_chunks
            BEGIN
                UPDATE chunks_fts SET content = new.content WHERE rowid = old.rowid;
            END
        """)
        self.db.execute("""
            CREATE TRIGGER IF NOT EXISTS chunks_fts_delete
            AFTER DELETE ON document_chunks
            BEGIN
                DELETE FROM chunks_fts WHERE rowid = old.rowid;
            END
        """)

        # Seed existing data only when tables were rebuilt
        if needs_rebuild_docs:
            self.db.execute("""
                INSERT INTO documents_fts(rowid, content)
                SELECT rowid, content FROM documents
            """)
        if needs_rebuild_chunks:
            self.db.execute("""
                INSERT INTO chunks_fts(rowid, content)
                SELECT rowid, content FROM document_chunks
            """)

    def _create_vector_tables(self) -> None:
        """Create vector tables using sqlite-vec."""
        try:
            self.db.execute("SELECT vec_version()")
            vec_available = True
        except sqlite3.OperationalError:
            vec_available = False

        if not vec_available:
            return

        cursor = self.db.execute(
            "SELECT sql FROM sqlite_master WHERE type='table' AND name='document_embeddings'",
        )
        row = cursor.fetchone()
        if row and row[0]:
            match = re.search(r"FLOAT\[(\d+)\]", row[0])
            if match:
                existing_dim = int(match.group(1))
                if existing_dim != self.embedding_dim:
                    raise RuntimeError(
                        f"Embedding dimension mismatch: database has FLOAT[{existing_dim}], "
                        f"but settings require FLOAT[{self.embedding_dim}]. "
                        f"Rebuild the index with 'sif cleanup' or delete the database file.",
                    )

        self.db.execute(f"""
            CREATE VIRTUAL TABLE IF NOT EXISTS document_embeddings USING vec0(
                embedding_id TEXT PRIMARY KEY,
                document_id TEXT NOT NULL,
                chunk_id TEXT,
                embedding FLOAT[{self.embedding_dim}]
            )
        """)

    def _create_indexes(self) -> None:
        """Create database indexes."""
        # Documents indexes
        self.db.execute("""
            CREATE INDEX IF NOT EXISTS idx_documents_collection
            ON documents(collection_id)
        """)
        self.db.execute("""
            CREATE INDEX IF NOT EXISTS idx_documents_path
            ON documents(path)
        """)
        self.db.execute("""
            CREATE INDEX IF NOT EXISTS idx_documents_checksum
            ON documents(checksum)
        """)

        # Chunks indexes
        self.db.execute("""
            CREATE INDEX IF NOT EXISTS idx_chunks_document
            ON document_chunks(document_id)
        """)

        # Contexts indexes
        self.db.execute("""
            CREATE INDEX IF NOT EXISTS idx_contexts_target
            ON contexts(target_id, context_type)
        """)

        # LLM cache index
        self.db.execute("""
            CREATE INDEX IF NOT EXISTS idx_llm_cache_lookup
            ON llm_cache(model_name, prompt_hash)
        """)

    def drop_all(self) -> None:
        """Drop all tables (for testing/reset)."""
        tables = [
            "document_embeddings",
            "chunks_fts",
            "documents_fts",
            "document_chunks",
            "documents",
            "contexts",
            "llm_cache",
            "collections",
        ]
        for table in tables:
            with contextlib.suppress(sqlite3.OperationalError):
                self.db.execute(f"DROP TABLE IF EXISTS {table}")
        self.db.commit()

    def get_stats(self) -> dict:
        """Get database statistics."""
        stats = {}

        # Collection count
        cursor = self.db.execute("SELECT COUNT(*) FROM collections")
        stats["collections"] = cursor.fetchone()[0]

        # Document count
        cursor = self.db.execute("SELECT COUNT(*) FROM documents")
        stats["documents"] = cursor.fetchone()[0]

        # Chunk count
        cursor = self.db.execute("SELECT COUNT(*) FROM document_chunks")
        stats["chunks"] = cursor.fetchone()[0]

        # Context count
        cursor = self.db.execute("SELECT COUNT(*) FROM contexts")
        stats["contexts"] = cursor.fetchone()[0]

        # Total size
        cursor = self.db.execute("SELECT SUM(file_size) FROM documents")
        result = cursor.fetchone()[0]
        stats["total_size_bytes"] = result or 0

        return stats
