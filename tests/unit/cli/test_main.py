"""Tests for the CLI main entry point (default index path, group-level guards)."""

from __future__ import annotations

import sqlite3
from collections.abc import Generator
from datetime import datetime, timedelta, timezone
from pathlib import Path

import click
import pytest
from click.testing import CliRunner, Result

from sif.cli.main import _get_default_db_path, cli
from sif.config.settings import get_settings
from sif.core.models import Collection, Document, DocumentChunk, PathContext
from sif.database.database import Database
from sif.database.repositories import (
    CollectionRepository,
    ContextRepository,
    DocumentChunkRepository,
    DocumentRepository,
)


class RealDatabaseTestCase:
    """Shared production-schema helpers with no access to the user's index."""

    @pytest.fixture(autouse=True)
    def isolated_settings(self) -> Generator[None, None, None]:
        """Keep Settings dimensions and paths independent between tests."""
        get_settings.cache_clear()
        yield
        get_settings.cache_clear()

    def _invoke(self, db_path: Path, command: str, *, confirm: bool = False) -> Result:
        """Invoke a top-level command against a specific temporary index."""
        return CliRunner().invoke(
            cli,
            ["--index", str(db_path), command],
            input="y\n" if confirm else None,
            env={"COLUMNS": "200"},
        )

    def _seed_document(self, db_path: Path) -> None:
        """Seed one collection/document/chunk/context with real repositories."""
        now = datetime.now(timezone.utc)
        collection = Collection(
            id="collection-1",
            name="notes",
            path="/notes",
            created_at=now,
            updated_at=now,
        )
        document = Document(
            id="document-1",
            collection_id=collection.id,
            path="/notes/one.md",
            title="One",
            content="retained content",
            file_size=1024 * 1024,
            created_at=now,
            updated_at=now,
        )
        chunk = DocumentChunk(
            id="chunk-1",
            document_id=document.id,
            content="retained content",
            sequence=0,
            start_pos=0,
            end_pos=16,
        )
        context = PathContext(
            id="context-1",
            path=document.path,
            context="Project context",
            created_at=now,
            updated_at=now,
        )
        with Database(db_path) as db:
            db.init_schema()
            with db.transaction() as conn:
                CollectionRepository(conn).create(collection)
                DocumentRepository(conn).create(document)
                DocumentChunkRepository(conn).create(chunk)
                ContextRepository(conn).create(context)

    def _seed_cleanup_rows(self, db_path: Path) -> None:
        """Seed valid and orphaned rows using only temporary foreign-key relaxation."""
        self._seed_document(db_path)
        now = datetime.now(timezone.utc)
        with Database(db_path) as db, db.transaction() as conn:
            conn.execute("PRAGMA foreign_keys = OFF")
            conn.execute(
                "INSERT INTO document_chunks "
                "(id, document_id, sequence, content, start_pos, end_pos, token_count, created_at) "
                "VALUES ('orphan-chunk', 'missing-document', 0, 'orphan', 0, 6, 1, ?)",
                (now.isoformat(),),
            )
            conn.execute("PRAGMA foreign_keys = ON")
            for cache_id, prompt_hash, expires_at in (
                ("expired-cache", "expired-hash", now - timedelta(days=1)),
                ("fresh-cache", "fresh-hash", now + timedelta(days=1)),
            ):
                conn.execute(
                    "INSERT INTO llm_cache "
                    "(id, model_name, prompt_hash, prompt, response, created_at, expires_at) "
                    "VALUES (?, 'test-model', ?, 'prompt', 'response', ?, ?)",
                    (cache_id, prompt_hash, now.isoformat(), expires_at.isoformat()),
                )


class TestStatusRealDatabase(RealDatabaseTestCase):
    """Status reads production SQLite statistics instead of mocked counters."""

    def test_missing_index_returns_guidance(self, tmp_path: Path) -> None:
        """An absent temporary index produces the documented early return."""
        result = self._invoke(tmp_path / "absent.db", "status")

        assert result.exit_code == 0, result.output
        assert "No index found. Run 'sif index update' to create one." in result.output

    def test_populated_index_reports_real_metrics(self, tmp_path: Path) -> None:
        """A populated database reports every metric and the total-size branch."""
        db_path = tmp_path / "sif.db"
        self._seed_document(db_path)

        result = self._invoke(db_path, "status")

        assert result.exit_code == 0, result.output
        assert "Index Status" in result.output
        assert "Collections" in result.output
        assert "Documents" in result.output
        assert "Chunks" in result.output
        assert "Contexts" in result.output
        assert "Total Size" in result.output
        assert "1.00 MB" in result.output


class TestCleanupRealDatabase(RealDatabaseTestCase):
    """Cleanup is verified by surviving rows, not only console output."""

    def test_missing_index_returns_without_creating_database(self, tmp_path: Path) -> None:
        """An absent index is not silently created by cleanup."""
        db_path = tmp_path / "absent.db"

        result = self._invoke(db_path, "cleanup", confirm=True)

        assert result.exit_code == 0, result.output
        assert "No index found." in result.output
        assert not db_path.exists()

    def test_cleanup_preserves_valid_rows_and_removes_only_orphans(self, tmp_path: Path) -> None:
        """Valid chunks and fresh cache survive; expired and orphaned rows do not."""
        db_path = tmp_path / "sif.db"
        self._seed_cleanup_rows(db_path)

        result = self._invoke(db_path, "cleanup", confirm=True)

        assert result.exit_code == 0, result.output
        assert "Removed 1 orphaned chunks" in result.output
        assert "Removed 1 expired cache entries" in result.output
        with sqlite3.connect(db_path) as conn:
            assert conn.execute("SELECT COUNT(*) FROM document_chunks").fetchone()[0] == 1
            assert (
                conn.execute(
                    "SELECT COUNT(*) FROM document_chunks WHERE id = 'chunk-1'"
                ).fetchone()[0]
                == 1
            )
            assert (
                conn.execute(
                    "SELECT COUNT(*) FROM document_chunks WHERE id = 'orphan-chunk'"
                ).fetchone()[0]
                == 0
            )
            assert (
                conn.execute(
                    "SELECT COUNT(*) FROM llm_cache WHERE id = 'expired-cache'"
                ).fetchone()[0]
                == 0
            )
            assert (
                conn.execute("SELECT COUNT(*) FROM llm_cache WHERE id = 'fresh-cache'").fetchone()[
                    0
                ]
                == 1
            )
            assert (
                conn.execute("SELECT COUNT(*) FROM documents WHERE id = 'document-1'").fetchone()[0]
                == 1
            )


class TestDefaultDbPathConfigError:
    """WR-09: an invalid SIF_RERANKER_MODEL_TYPE must surface as a clean error.

    ``--index`` is omitted on almost every invocation, so Click evaluates the
    callable default ``_get_default_db_path`` during option parsing; without a
    guard the Settings validator would escape there as a raw pydantic
    traceback for every command. get_settings is lru_cache'd, so the cache
    must be cleared AFTER the env var is set (a prior cached success would
    mask it) and again afterwards for hygiene.
    """

    def test_get_default_db_path_wraps_validation_error(self, monkeypatch) -> None:
        """The callable default raises click.ClickException, not ValidationError."""
        monkeypatch.setenv("SIF_RERANKER_MODEL_TYPE", "cross-encoder")
        get_settings.cache_clear()
        try:
            with pytest.raises(click.ClickException, match="reranker_model_type"):
                _get_default_db_path()
        finally:
            get_settings.cache_clear()

    def test_group_command_renders_clean_error(self, monkeypatch) -> None:
        """Invoking the group without --index renders a one-line error, exit 1."""
        runner = CliRunner()
        monkeypatch.setenv("SIF_RERANKER_MODEL_TYPE", "cross-encoder")
        get_settings.cache_clear()
        try:
            result = runner.invoke(cli, ["status"])
        finally:
            get_settings.cache_clear()

        assert result.exit_code == 1
        assert "Error:" in result.output
        assert "reranker_model_type" in result.output
        assert "Traceback" not in result.output
