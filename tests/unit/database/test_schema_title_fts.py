"""CORR-04: title-FTS detect-and-rebuild migration on a populated database.

The migration is detection-gated: a legacy single-column ``documents_fts`` is
detected from its stored DDL, the vocab shadow is dropped BEFORE the FTS
table, the three document triggers are recreated carrying ``title``, the
external-content index is populated by exactly one FTS5 ``'rebuild'`` (the
old ``INSERT ... SELECT`` seed is gone — it would index every document
twice), and ``documents_fts_v`` is recreated after the rebuild.

``PRAGMA integrity_check`` and the FTS ``integrity-check`` command both report
OK under duplicate population, so the single-population contract is asserted
structurally (one population statement in ``_create_fts_tables``) as well as
at run time (row counts, one-row token cardinality, post-delete
unmatchability). The populated-DB vocabulary survives: title stems join the
vocabulary and ``did_you_mean`` keeps working after the migration.

These tests use real SQLite (``:memory:``) and skip when sqlite-vec is
unavailable, matching the schema suite's discipline.
"""

from __future__ import annotations

import inspect
import sqlite3
from datetime import datetime, timezone

import pytest

from sif.database.schema import SchemaManager
from sif.search.suggest import SuggestionEngine


def _load_vec(db: sqlite3.Connection) -> bool:
    try:
        import sqlite_vec

        db.enable_load_extension(True)
        sqlite_vec.load(db)
        db.enable_load_extension(False)
        return True
    except Exception:
        return False


def _build_legacy_db() -> sqlite3.Connection:
    """A populated database with the pre-CORR-04 single-column FTS shape.

    The tables are the production DDL (via the individual ``SchemaManager``
    creators, as the existing misconfiguration test does), and the FTS table,
    vocab shadow, index rows, and three one-column triggers are hand-built
    exactly as the shipped SchemaManager created them before this plan.
    ``titular`` appears only in d1's title, so it is a title-only probe.
    """
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    manager = SchemaManager(conn, embedding_dim=8)
    manager._create_collections_table()
    manager._create_documents_table()
    manager._create_document_chunks_table()
    manager._create_index_meta_table()

    now = datetime.now(timezone.utc).isoformat()
    conn.execute(
        "INSERT INTO collections (id, name, path, created_at, updated_at) "
        "VALUES ('c1', 'notes', '/notes', ?, ?)",
        (now, now),
    )
    documents = [
        ("d1", "Titular Alpha", "/notes/d1.md", "the body words"),
        ("d2", "Second Entry", "/notes/d2.md", "other body prose"),
    ]
    for doc_id, title, path, content in documents:
        conn.execute(
            "INSERT INTO documents (id, collection_id, path, filename, title, content, "
            "checksum, mtime, created_at, updated_at) VALUES (?, 'c1', ?, ?, ?, ?, ?, 1.0, ?, ?)",
            (doc_id, path, path.rsplit("/", 1)[-1], title, content, f"ck-{doc_id}", now, now),
        )

    # The legacy one-column FTS index, its vocab shadow, and the old triggers.
    conn.execute(
        "CREATE VIRTUAL TABLE documents_fts USING fts5("
        "content, content='documents', content_rowid='rowid', tokenize='porter')"
    )
    conn.execute("CREATE VIRTUAL TABLE documents_fts_v USING fts5vocab(documents_fts, 'row')")
    conn.execute("INSERT INTO documents_fts(rowid, content) SELECT rowid, content FROM documents")
    conn.execute("""
        CREATE TRIGGER documents_fts_insert
        AFTER INSERT ON documents
        BEGIN
            INSERT INTO documents_fts(rowid, content) VALUES (new.rowid, new.content);
        END
    """)
    conn.execute("""
        CREATE TRIGGER documents_fts_update
        AFTER UPDATE ON documents
        BEGIN
            INSERT INTO documents_fts(documents_fts, rowid, content)
            VALUES('delete', old.rowid, old.content);
            INSERT INTO documents_fts(rowid, content) VALUES(new.rowid, new.content);
        END
    """)
    conn.execute("""
        CREATE TRIGGER documents_fts_delete
        AFTER DELETE ON documents
        BEGIN
            INSERT INTO documents_fts(documents_fts, rowid, content)
            VALUES('delete', old.rowid, old.content);
        END
    """)
    conn.commit()
    return conn


@pytest.fixture
def legacy_db():
    """Populated pre-CORR-04 database (sqlite-vec skip guard)."""
    conn = _build_legacy_db()
    try:
        if not _load_vec(conn):
            pytest.skip("sqlite-vec not available")
        yield conn
    finally:
        conn.close()


def _match_count(db: sqlite3.Connection, query: str) -> int:
    return db.execute(
        "SELECT COUNT(*) FROM documents_fts WHERE documents_fts MATCH ?", (query,)
    ).fetchone()[0]


class TestTitleFtsMigration:
    """Detect-and-rebuild on a populated legacy database."""

    def test_title_only_match_flips_from_zero_to_one(self, legacy_db):
        """The migration adds title text to the index without touching rows."""
        assert _match_count(legacy_db, '"titular"') == 0

        SchemaManager(legacy_db, embedding_dim=8).create_all()

        assert _match_count(legacy_db, '"titular"') == 1
        assert SchemaManager(legacy_db)._fts_column_names("documents_fts") == [
            "content",
            "title",
        ]
        stored_sql = legacy_db.execute(
            "SELECT sql FROM sqlite_master WHERE type='table' AND name='documents_fts'"
        ).fetchone()[0]
        assert "title" in stored_sql
        assert "content='documents'" in stored_sql

    def test_vocab_shadow_survives_and_dym_still_works(self, legacy_db):
        """documents_fts_v is dropped before the FTS table and holds title stems."""
        SchemaManager(legacy_db, embedding_dim=8).create_all()

        terms = {row[0] for row in legacy_db.execute("SELECT term FROM documents_fts_v")}
        assert "titular" in terms  # title stem joined the vocabulary
        assert "second" in terms  # title stem from the other document
        assert SuggestionEngine(legacy_db).did_you_mean("titulor") == ["titular"]

    def test_document_triggers_carry_title_and_chunks_triggers_do_not(self, legacy_db):
        """The three document triggers index/delete both columns; chunks are untouched."""
        SchemaManager(legacy_db, embedding_dim=8).create_all()

        for trigger in (
            "documents_fts_insert",
            "documents_fts_update",
            "documents_fts_delete",
        ):
            sql = legacy_db.execute(
                "SELECT sql FROM sqlite_master WHERE type='trigger' AND name=?", (trigger,)
            ).fetchone()[0]
            assert "(rowid, content, title)" in sql or (
                "(documents_fts, rowid, content, title)" in sql
            )

        update_sql = legacy_db.execute(
            "SELECT sql FROM sqlite_master WHERE type='trigger' AND name='documents_fts_update'"
        ).fetchone()[0]
        delete_sql = legacy_db.execute(
            "SELECT sql FROM sqlite_master WHERE type='trigger' AND name='documents_fts_delete'"
        ).fetchone()[0]
        assert "old.title" in update_sql
        assert "old.title" in delete_sql

        chunks_insert = legacy_db.execute(
            "SELECT sql FROM sqlite_master WHERE type='trigger' AND name='chunks_fts_insert'"
        ).fetchone()[0]
        assert "title" not in chunks_insert
        assert "INSERT INTO chunks_fts(rowid, content) VALUES (new.rowid, new.content);" in (
            chunks_insert
        )

    def test_title_only_update_removes_old_terms(self, legacy_db):
        """The rewritten UPDATE trigger deletes old.title and inserts new.title."""
        SchemaManager(legacy_db, embedding_dim=8).create_all()

        legacy_db.execute("UPDATE documents SET title = 'Renewed Gamma' WHERE id = 'd1'")
        legacy_db.commit()

        assert _match_count(legacy_db, '"titular"') == 0
        assert _match_count(legacy_db, '"renew"') == 1
        terms = {row[0] for row in legacy_db.execute("SELECT term FROM documents_fts_v")}
        assert "renew" in terms
        assert "titular" not in terms

    def test_delete_removes_title_matches_and_null_titles_are_safe(self, legacy_db):
        """DELETE clears the row; NULL-title insert/delete stays consistent."""
        SchemaManager(legacy_db, embedding_dim=8).create_all()
        now = datetime.now(timezone.utc).isoformat()

        legacy_db.execute(
            "INSERT INTO documents (id, collection_id, path, filename, content, checksum, "
            "mtime, created_at, updated_at) VALUES ('d3', 'c1', '/notes/d3.md', 'd3.md', "
            "'nullbodytoken', 'ck-d3', 1.0, ?, ?)",
            (now, now),
        )
        legacy_db.commit()
        assert _match_count(legacy_db, "nullbodytoken") == 1

        legacy_db.execute("DELETE FROM documents WHERE id = 'd3'")
        legacy_db.commit()
        assert _match_count(legacy_db, "nullbodytoken") == 0

        legacy_db.execute("DELETE FROM documents WHERE id = 'd2'")
        legacy_db.commit()
        assert _match_count(legacy_db, '"second"') == 0

        legacy_db.execute("PRAGMA integrity_check")
        assert legacy_db.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
        # The FTS command-level check must be clean as well.
        legacy_db.execute("INSERT INTO documents_fts(documents_fts) VALUES('integrity-check')")

    def test_single_population_row_counts_and_match_cardinality(self, legacy_db):
        """One population statement: counts match, tokens match exactly one row."""
        SchemaManager(legacy_db, embedding_dim=8).create_all()

        docs = legacy_db.execute("SELECT COUNT(*) FROM documents").fetchone()[0]
        fts_rows = legacy_db.execute("SELECT COUNT(*) FROM documents_fts").fetchone()[0]
        assert fts_rows == docs == 2
        # `words` is unique to d1: duplicate population would make this 2.
        assert _match_count(legacy_db, "words") == 1

        legacy_db.execute("DELETE FROM documents WHERE id = 'd1'")
        legacy_db.commit()
        assert _match_count(legacy_db, "words") == 0
        assert (
            legacy_db.execute("SELECT COUNT(*) FROM documents_fts").fetchone()[0]
            == legacy_db.execute("SELECT COUNT(*) FROM documents").fetchone()[0]
        )

    def test_population_is_structurally_single_and_seed_free(self):
        """The fix's primary assertion: one rebuild statement, no old seed.

        FTS5 coalesces identical postings for the same rowid, so run-time
        counts can stay green even with a seed+rebuild duplicate. The source
        contract is what makes the duplicate impossible.
        """
        source = inspect.getsource(SchemaManager._create_fts_tables)

        assert source.count("INSERT INTO documents_fts(documents_fts) VALUES('rebuild')") == 1
        assert "INSERT INTO documents_fts(rowid, content) SELECT" not in source
        assert "SELECT rowid, content FROM documents" not in source

    def test_second_create_all_pays_only_the_detection_read(self, legacy_db):
        """A migrated database executes no DROP/rebuild on the next create_all."""
        manager = SchemaManager(legacy_db, embedding_dim=8)
        manager.create_all()

        statements: list[str] = []
        legacy_db.set_trace_callback(statements.append)
        try:
            manager.create_all()
        finally:
            legacy_db.set_trace_callback(None)

        assert any("sqlite_master" in statement for statement in statements)
        assert not any(
            "INSERT INTO documents_fts(documents_fts)" in statement for statement in statements
        )
        assert not any(
            "DROP TABLE" in statement and "documents_fts" in statement for statement in statements
        )

    def test_rebuild_population_command_precedes_vocab_recreation(self):
        """Vocab drop/recreate brackets the FTS table rebuild in source order."""
        source = inspect.getsource(SchemaManager._create_fts_tables)

        assert source.index('DROP TABLE IF EXISTS documents_fts_v"') < source.index(
            'DROP TABLE IF EXISTS documents_fts"'
        )
        assert source.index("INSERT INTO documents_fts(documents_fts) VALUES('rebuild')") < (
            source.index("CREATE VIRTUAL TABLE IF NOT EXISTS documents_fts_v")
        )


class TestFreshTitleFts:
    """A fresh database is created two-column directly and stays idempotent."""

    def test_fresh_db_creates_two_columns_directly(self):
        conn = sqlite3.connect(":memory:")
        conn.row_factory = sqlite3.Row
        try:
            manager = SchemaManager(conn, embedding_dim=8)
            manager.create_all()
            assert manager._fts_column_names("documents_fts") == ["content", "title"]
            stored = conn.execute(
                "SELECT sql FROM sqlite_master WHERE type='table' AND name='documents_fts'"
            ).fetchone()[0]
            conn.execute(
                "INSERT INTO collections (id, name, path, created_at, updated_at) "
                "VALUES ('c1', 'n', '/p', '2020-01-01', '2020-01-01')"
            )
            conn.execute(
                "INSERT INTO documents (id, collection_id, path, filename, title, content, "
                "checksum, mtime, created_at, updated_at) VALUES ("
                "'d1', 'c1', '/p/a.md', 'a.md', 'Fresh Title', 'body words', 'x', 1.0, "
                "'2020-01-01', '2020-01-01')"
            )
            conn.commit()
            assert _match_count(conn, '"fresh"') == 1

            manager.create_all()
            assert (
                conn.execute(
                    "SELECT sql FROM sqlite_master WHERE type='table' AND name='documents_fts'"
                ).fetchone()[0]
                == stored
            )
            assert _match_count(conn, '"fresh"') == 1
        finally:
            conn.close()
