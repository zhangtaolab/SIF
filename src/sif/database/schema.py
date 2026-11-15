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
        """Create all database tables and indexes.

        CR-01 (19 REVIEW): schema writes are self-committing. pysqlite
        auto-commits DDL but leaves DML in the connection's implicit
        transaction, so a read-only host that opens the index, initializes
        the schema, and closes without ever starting a command transaction
        (``sif status``, ``sif index status``) would roll the FTS
        ``'rebuild'`` population back while keeping the migrated DDL — the
        detection gate would then never rebuild and BM25 search would stay
        silently empty. ``_create_fts_tables`` commits its own migration with
        an explicit savepoint (so a later failure here cannot roll the
        population back either); this final commit covers every other write.
        """
        self._create_collections_table()
        self._create_documents_table()
        self._create_metadata_tables()
        self._create_document_chunks_table()
        self._migrate_path_contexts()
        self._create_contexts_table()
        self._create_llm_cache_table()
        self._create_query_log_table()
        self._create_index_meta_table()
        self._create_fts_tables()
        self._create_vector_tables()
        self._create_indexes()
        self.db.commit()

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

    def _create_metadata_tables(self) -> None:
        """Create the typed frontmatter key-value store (Phase 20, D-05/D-07).

        One row per scalar value; array elements become successive ``ordinal``
        rows so arrays are sets without JSON1. Typed columns plus the
        ``value_type`` CHECK give typed exact match, and the partial covering
        indexes serve the compiler's ``(key, typed column, document_id)``
        probes. ``document_metadata_skips`` is the D-07 sidecar: a per-key
        record (nested/null/mixed_array) so discovery can report skipped keys
        without polluting ``exists``/``type`` with sentinel value rows.

        Both tables cascade from ``documents``; ``create_connection`` enables
        ``PRAGMA foreign_keys = ON`` (factory.py), so document/collection
        deletes need no extra kv cleanup. Callers create both in the same
        transaction as the document row (D-05).
        """
        self.db.execute("""
            CREATE TABLE IF NOT EXISTS document_metadata_values (
                document_id TEXT NOT NULL,
                key TEXT NOT NULL,
                ordinal INTEGER NOT NULL,
                value_type TEXT NOT NULL,
                text_value TEXT,
                number_value REAL,
                boolean_value INTEGER,
                PRIMARY KEY (document_id, key, ordinal),
                FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE,
                CHECK (value_type IN ('string', 'number', 'boolean')),
                CHECK (
                    (value_type = 'string' AND text_value IS NOT NULL
                        AND number_value IS NULL AND boolean_value IS NULL)
                    OR (value_type = 'number' AND number_value IS NOT NULL
                        AND text_value IS NULL AND boolean_value IS NULL)
                    OR (value_type = 'boolean' AND boolean_value IN (0, 1)
                        AND text_value IS NULL AND number_value IS NULL)
                )
            )
        """)
        self.db.execute("""
            CREATE INDEX IF NOT EXISTS idx_metadata_text_lookup
            ON document_metadata_values(key, text_value, document_id)
            WHERE value_type = 'string'
        """)
        self.db.execute("""
            CREATE INDEX IF NOT EXISTS idx_metadata_number_lookup
            ON document_metadata_values(key, number_value, document_id)
            WHERE value_type = 'number'
        """)
        self.db.execute("""
            CREATE INDEX IF NOT EXISTS idx_metadata_boolean_lookup
            ON document_metadata_values(key, boolean_value, document_id)
            WHERE value_type = 'boolean'
        """)
        self.db.execute("""
            CREATE TABLE IF NOT EXISTS document_metadata_skips (
                document_id TEXT NOT NULL,
                key TEXT NOT NULL,
                reason TEXT NOT NULL,
                PRIMARY KEY (document_id, key),
                FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE
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

    def _create_query_log_table(self) -> None:
        """Create the local query-history table (Phase 15, D-08/D-09).

        Stores executed-search metadata only — query string, result count,
        collections searched — never document content (T-15-04). Writers trim
        to the most-recent ``SIF_QUERY_HISTORY_LIMIT`` rows in the same
        transaction (trim-in-write, D-09), so the table never grows
        unboundedly; ``created_at`` is aware-UTC ISO text.
        """
        self.db.execute("""
            CREATE TABLE IF NOT EXISTS query_log (
                id TEXT PRIMARY KEY,
                query TEXT NOT NULL,
                result_count INTEGER NOT NULL DEFAULT 0,
                collections TEXT NOT NULL DEFAULT '[]',
                created_at TEXT NOT NULL
            )
        """)
        self.db.execute("""
            CREATE INDEX IF NOT EXISTS idx_query_log_created
            ON query_log(created_at DESC)
        """)

    def _create_index_meta_table(self) -> None:
        """Create the key/value index metadata table (D-09 convention marker).

        Namespaced keys (``convention:<collection_id>``) let every
        index-writing host record per-collection state — the parser/checksum
        convention today, embedder identity in Phase 21 — without a global
        marker that one migrated collection could strand for the others.
        """
        self.db.execute("""
            CREATE TABLE IF NOT EXISTS index_meta (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )
        """)

    def _fts_trigger_is_legacy(self, trigger_name: str, fts_table: str) -> bool:
        """Check if an existing FTS sync trigger writes directly to the FTS table.

        Two broken legacy forms exist, both issuing a direct write to the
        external-content FTS5 table instead of the documented commands: a
        direct UPDATE corrupts the index ("database disk image is malformed")
        once the edit spans internal node boundaries (FND-06), and a direct
        DELETE silently leaves the removed content MATCHable (CR-01). The
        documented remedy for both is the 'delete'-command trigger form
        created in _create_fts_tables.
        """
        cursor = self.db.execute(
            "SELECT sql FROM sqlite_master WHERE type='trigger' AND name=?",
            (trigger_name,),
        )
        row = cursor.fetchone()
        if not row or not row[0]:
            return False
        sql = row[0]
        return f"UPDATE {fts_table} SET" in sql or f"DELETE FROM {fts_table}" in sql

    def _drop_legacy_fts_triggers(self) -> tuple[bool, bool]:
        """Drop legacy FTS sync triggers; report which DELETE triggers were legacy.

        Legacy triggers write directly to the external-content FTS5 tables
        (FND-06 / CR-01): a direct UPDATE corrupts the index once an edit
        spans internal node boundaries ("database disk image is malformed"),
        and a direct DELETE silently leaves the removed content MATCHable.
        CREATE TRIGGER IF NOT EXISTS cannot replace either form, so each
        legacy trigger is dropped here; _create_fts_tables then recreates
        the documented 'delete'-command forms. The returned booleans tell
        the caller which FTS indexes may carry entries orphaned by past
        deletes that ran under a broken trigger.
        """
        legacy_delete_docs = self._fts_trigger_is_legacy("documents_fts_delete", "documents_fts")
        if legacy_delete_docs:
            self.db.execute("DROP TRIGGER documents_fts_delete")
        legacy_delete_chunks = self._fts_trigger_is_legacy("chunks_fts_delete", "chunks_fts")
        if legacy_delete_chunks:
            self.db.execute("DROP TRIGGER chunks_fts_delete")
        if self._fts_trigger_is_legacy("documents_fts_update", "documents_fts"):
            self.db.execute("DROP TRIGGER documents_fts_update")
        if self._fts_trigger_is_legacy("chunks_fts_update", "chunks_fts"):
            self.db.execute("DROP TRIGGER chunks_fts_update")
        return legacy_delete_docs, legacy_delete_chunks

    def _fts_column_names(self, table_name: str) -> list[str] | None:
        """Return an FTS5 table's indexed column names, or None when absent.

        FTS5 cannot ALTER a column list and ``CREATE VIRTUAL TABLE IF NOT
        EXISTS`` is a no-op for an existing table, so the stored
        ``sqlite_master.sql`` is the only way to tell a one-column index from
        the two-column (content, title) form. The indexed column list ends at
        the first ``content=`` option clause; names are returned normalized
        (whitespace and surrounding quotes stripped).
        """
        cursor = self.db.execute(
            "SELECT sql FROM sqlite_master WHERE type='table' AND name=?",
            (table_name,),
        )
        row = cursor.fetchone()
        if not row or not row[0]:
            return None
        match = re.search(r"USING\s+fts5\s*\((.*?)\)", row[0], re.IGNORECASE | re.DOTALL)
        if not match:
            return None
        columns_clause = re.split(r"\bcontent\s*=", match.group(1), maxsplit=1)[0]
        return [
            column.strip().strip("'\"") for column in columns_clause.split(",") if column.strip()
        ]

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

        # CORR-04: an existing single-column documents_fts cannot gain the
        # title column in place (Pitfall 8). Parse the stored DDL and rebuild
        # when the column list is missing ``title``; a missing table is a
        # fresh database and is created two-column directly below. Either
        # condition drives the same drop/recreate path as a misconfigured
        # content= table.
        column_names = self._fts_column_names("documents_fts")
        needs_title_rebuild = column_names is not None and "title" not in [
            name.lower() for name in column_names
        ]
        needs_rebuild_docs = (
            _fts_is_misconfigured("documents_fts", "documents") or needs_title_rebuild
        )
        needs_rebuild_chunks = _fts_is_misconfigured("chunks_fts", "document_chunks")

        # CR-01 (19 REVIEW): the legacy-trigger repair and the
        # drop/recreate/rebuild sequence are one atomic unit. pysqlite
        # auto-commits DDL but leaves the INSERT 'rebuild'/seed DML in the
        # connection's implicit transaction, so before this savepoint a close,
        # crash, or later create_all failure (the embedding-dimension
        # RuntimeError) could persist the two-column DDL and roll back only
        # the population — the detection gate then reports "already migrated"
        # forever and BM25 search stays silently empty. Wrapping the whole
        # sequence (trigger drops included) in a savepoint means a failure
        # rolls the DDL back too, restoring the legacy shape so the next open
        # re-detects and retries; a successful migration commits the
        # population before the rest of create_all runs. SAVEPOINT nests
        # safely when a caller already holds a transaction.
        self.db.execute("SAVEPOINT sp_fts_tables")
        try:
            legacy_delete_docs, legacy_delete_chunks = self._drop_legacy_fts_triggers()

            if needs_rebuild_docs:
                # Drop the vocab shadow FIRST (Pitfall 6): dropping the parent
                # while the vocab exists succeeds but leaves a dangling shadow
                # that serves stale terms until it is recreated. Then drop the
                # three document triggers explicitly — CREATE TRIGGER IF NOT
                # EXISTS cannot replace the one-column bodies — and the table.
                self.db.execute("DROP TABLE IF EXISTS documents_fts_v")
                for trigger in (
                    "documents_fts_insert",
                    "documents_fts_update",
                    "documents_fts_delete",
                ):
                    self.db.execute(f"DROP TRIGGER IF EXISTS {trigger}")
                self.db.execute("DROP TABLE IF EXISTS documents_fts")
            if needs_rebuild_chunks:
                self.db.execute("DROP TABLE IF EXISTS chunks_fts")

            # Documents FTS table with external content. The title column is
            # declared second; bm25() weights map left-to-right by this order.
            self.db.execute("""
                CREATE VIRTUAL TABLE IF NOT EXISTS documents_fts USING fts5(
                    content,
                    title,
                    content='documents',
                    content_rowid='rowid',
                    tokenize='porter'
                )
            """)

            # Chunks FTS table with external content (chunks have no title
            # column; this table and its triggers stay byte-identical to the
            # pre-CORR-04 form).
            self.db.execute("""
                CREATE VIRTUAL TABLE IF NOT EXISTS chunks_fts USING fts5(
                    content,
                    content='document_chunks',
                    content_rowid='rowid',
                    tokenize='porter'
                )
            """)

            # The FTS5 'rebuild' bulk command is the WHOLE documents-side
            # population: it re-derives every row's content and title from the
            # external-content table. A separate INSERT ... SELECT seed would run
            # under the same gate and index every document twice — BM25 ranks
            # shift and a deleted document stays MATCHable through its duplicate
            # entry — while PRAGMA integrity_check and the FTS integrity-check
            # command both still report OK. Keep exactly one population
            # statement, gated on the rebuild or the legacy-delete repair; fresh
            # and already-migrated databases pay nothing.
            if needs_rebuild_docs or legacy_delete_docs:
                self.db.execute("INSERT INTO documents_fts(documents_fts) VALUES('rebuild')")
            if needs_rebuild_chunks:
                self.db.execute("""
                    INSERT INTO chunks_fts(rowid, content)
                    SELECT rowid, content FROM document_chunks
                """)

            # CR-01: purge chunks FTS entries orphaned by deletes that ran while a
            # legacy direct-DELETE trigger was active — replacing the trigger
            # repairs future deletes, not past ones. 'rebuild' re-derives the
            # whole index from the content table, so live entries survive.
            if legacy_delete_chunks:
                self.db.execute("INSERT INTO chunks_fts(chunks_fts) VALUES('rebuild')")

            # FTS5 vocab shadow (Phase 15, D-06): row mode = one row per distinct
            # porter-stem term with its document frequency — the suggestion
            # engine's term source, derived from the index (no sync maintenance).
            # MUST live in the main schema: a temp-schema vocab cannot reference a
            # main-schema FTS table (RESEARCH Pitfall 8). Recreated AFTER the
            # documents rebuild so no stale-terms window exists (Pitfall 6).
            # Idempotent; the suggest engine re-ensures it for connections that
            # never ran init_schema.
            self.db.execute("""
                CREATE VIRTUAL TABLE IF NOT EXISTS documents_fts_v
                USING fts5vocab(documents_fts, 'row')
            """)

            # Triggers for documents_fts. Every indexed column must carry its
            # value — including old.title on the 'delete' command — or external
            # content desynchronizes (Pitfall 7); documents.title is nullable and
            # NULL values index/delete cleanly.
            self.db.execute("""
                CREATE TRIGGER IF NOT EXISTS documents_fts_insert
                AFTER INSERT ON documents
                BEGIN
                    INSERT INTO documents_fts(rowid, content, title)
                    VALUES (new.rowid, new.content, new.title);
                END
            """)
            self.db.execute("""
                CREATE TRIGGER IF NOT EXISTS documents_fts_update
                AFTER UPDATE ON documents
                BEGIN
                    INSERT INTO documents_fts(documents_fts, rowid, content, title)
                    VALUES('delete', old.rowid, old.content, old.title);
                    INSERT INTO documents_fts(rowid, content, title)
                    VALUES(new.rowid, new.content, new.title);
                END
            """)
            self.db.execute("""
                CREATE TRIGGER IF NOT EXISTS documents_fts_delete
                AFTER DELETE ON documents
                BEGIN
                    INSERT INTO documents_fts(documents_fts, rowid, content, title)
                    VALUES('delete', old.rowid, old.content, old.title);
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
                    INSERT INTO chunks_fts(chunks_fts, rowid, content)
                    VALUES('delete', old.rowid, old.content);
                    INSERT INTO chunks_fts(rowid, content) VALUES(new.rowid, new.content);
                END
            """)
            self.db.execute("""
                CREATE TRIGGER IF NOT EXISTS chunks_fts_delete
                AFTER DELETE ON document_chunks
                BEGIN
                    INSERT INTO chunks_fts(chunks_fts, rowid, content)
                    VALUES('delete', old.rowid, old.content);
                END
            """)
            self.db.execute("RELEASE SAVEPOINT sp_fts_tables")
        except BaseException:
            # Roll the DDL back with the population so the legacy shape (and
            # its detection gate) survives a failed migration. A rollback can
            # itself fail on a closing/broken connection; never mask the
            # original error.
            with contextlib.suppress(sqlite3.Error):
                self.db.execute("ROLLBACK TO SAVEPOINT sp_fts_tables")
                self.db.execute("RELEASE SAVEPOINT sp_fts_tables")
            raise

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
                        f"Restore the model and SIF_EMBEDDING_DIM that match "
                        f"FLOAT[{existing_dim}], or delete the database file "
                        "and rebuild the index.",
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
        # CORR-04: Phase 20's mtime filter scans this column; IF NOT EXISTS
        # makes the create a no-op on already-migrated databases.
        self.db.execute("""
            CREATE INDEX IF NOT EXISTS idx_documents_mtime
            ON documents(mtime)
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
            "documents_fts_v",
            "documents_fts",
            "document_chunks",
            "document_metadata_values",
            "document_metadata_skips",
            "documents",
            "contexts",
            "llm_cache",
            "query_log",
            "index_meta",
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
