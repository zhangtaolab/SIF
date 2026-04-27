"""Database migration management."""

from pathlib import Path

from sif.config.constants import CURRENT_SCHEMA_VERSION
from sif.utils.logging import get_logger

logger = get_logger(__name__)


# Schema definition
SCHEMA_SQL = """
-- Collections table
CREATE TABLE IF NOT EXISTS collections (
    id TEXT PRIMARY KEY,
    name TEXT UNIQUE NOT NULL,
    description TEXT,
    paths TEXT NOT NULL DEFAULT '[]',
    document_count INTEGER NOT NULL DEFAULT 0,
    chunk_count INTEGER NOT NULL DEFAULT 0,
    metadata TEXT NOT NULL DEFAULT '{}',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    last_indexed_at DATETIME
);

-- Documents table
CREATE TABLE IF NOT EXISTS documents (
    id TEXT PRIMARY KEY,
    collection_id TEXT NOT NULL,
    path TEXT NOT NULL,
    content TEXT NOT NULL,
    checksum TEXT NOT NULL,
    file_size INTEGER NOT NULL,
    metadata TEXT NOT NULL DEFAULT '{}',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    indexed_at DATETIME,
    FOREIGN KEY (collection_id) REFERENCES collections(id) ON DELETE CASCADE,
    UNIQUE(collection_id, path)
);

-- Chunks table
CREATE TABLE IF NOT EXISTS chunks (
    id TEXT PRIMARY KEY,
    document_id TEXT NOT NULL,
    content TEXT NOT NULL,
    start_line INTEGER NOT NULL,
    end_line INTEGER NOT NULL,
    token_count INTEGER NOT NULL,
    embedding_id TEXT,
    FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE
);

-- Contexts table
CREATE TABLE IF NOT EXISTS contexts (
    id TEXT PRIMARY KEY,
    content TEXT NOT NULL,
    context_type TEXT NOT NULL,
    target_id TEXT NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(context_type, target_id)
);

-- Schema version tracking
CREATE TABLE IF NOT EXISTS schema_version (
    version INTEGER PRIMARY KEY,
    applied_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_documents_collection ON documents(collection_id);
CREATE INDEX IF NOT EXISTS idx_documents_path ON documents(path);
CREATE INDEX IF NOT EXISTS idx_chunks_document ON chunks(document_id);
CREATE INDEX IF NOT EXISTS idx_contexts_type ON contexts(context_type);
CREATE INDEX IF NOT EXISTS idx_contexts_target ON contexts(target_id);
"""

# FTS5 virtual table
FTS_SQL = """
CREATE VIRTUAL TABLE IF NOT EXISTS documents_fts USING fts5(
    content,
    content_rowid=rowid,
    tokenize='porter'
);

-- Trigger to keep FTS index in sync
CREATE TRIGGER IF NOT EXISTS documents_fts_insert
AFTER INSERT ON documents
BEGIN
    INSERT INTO documents_fts(rowid, content) VALUES (new.rowid, new.content);
END;

CREATE TRIGGER IF NOT EXISTS documents_fts_update
AFTER UPDATE ON documents
BEGIN
    UPDATE documents_fts SET content = new.content WHERE rowid = old.rowid;
END;

CREATE TRIGGER IF NOT EXISTS documents_fts_delete
AFTER DELETE ON documents
BEGIN
    DELETE FROM documents_fts WHERE rowid = old.rowid;
END;
"""

# Vector table (sqlite-vec)
VECTOR_SQL_TEMPLATE = """
CREATE VIRTUAL TABLE IF NOT EXISTS chunk_embeddings USING vec0(
    embedding_id TEXT PRIMARY KEY,
    embedding FLOAT[{dim}]
);
"""


class MigrationManager:
    """Manages database schema migrations."""

    def __init__(self, connection: "DatabaseConnection") -> None:
        self._connection = connection

    def get_current_version(self) -> int:
        """Get the current schema version."""
        try:
            row = self._connection.fetchone(
                "SELECT version FROM schema_version ORDER BY version DESC LIMIT 1"
            )
            return row["version"] if row else 0
        except Exception:
            return 0

    def migrate(self, embedding_dim: int = 384) -> None:
        """Run all pending migrations."""
        current_version = self.get_current_version()

        if current_version >= CURRENT_SCHEMA_VERSION:
            logger.info("Database schema is up to date")
            return

        logger.info(
            f"Migrating database from version {current_version} to {CURRENT_SCHEMA_VERSION}"
        )

        # Apply schema
        self._apply_schema(embedding_dim)

        # Update version
        self._connection.execute(
            "INSERT INTO schema_version (version) VALUES (?)",
            (CURRENT_SCHEMA_VERSION,),
        )

        logger.info("Database migration completed successfully")

    def _apply_schema(self, embedding_dim: int) -> None:
        """Apply the database schema."""
        # Apply main schema
        self._connection.execute(SCHEMA_SQL)

        # Apply FTS schema
        self._connection.execute(FTS_SQL)

        # Apply vector schema
        vector_sql = VECTOR_SQL_TEMPLATE.format(dim=embedding_dim)
        self._connection.execute(vector_sql)

    def reset(self) -> None:
        """Reset the database (drop all tables)."""
        logger.warning("Resetting database - all data will be lost")

        tables = [
            "documents_fts",
            "chunk_embeddings",
            "chunks",
            "documents",
            "contexts",
            "collections",
            "schema_version",
        ]

        for table in tables:
            try:
                self._connection.execute(f"DROP TABLE IF EXISTS {table}")
            except Exception as e:
                logger.warning(f"Error dropping table {table}: {e}")

        logger.info("Database reset completed")
