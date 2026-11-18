"""Tests for the CLI main entry point (default index path, group-level guards)."""

from __future__ import annotations

import contextlib
import json
import os
import re
import sqlite3
import time
from collections.abc import Generator
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

import click
import pytest
from click.testing import CliRunner, Result

from sif.cli.main import _get_default_db_path, _vector_lag_text, cli
from sif.config.settings import get_settings
from sif.core.models import Collection, Document, DocumentChunk, PathContext
from sif.database.database import Database
from sif.database.factory import create_connection
from sif.database.repositories import (
    CollectionRepository,
    ContextRepository,
    DocumentChunkRepository,
    DocumentRepository,
    LLMCacheRepository,
)


class RealDatabaseTestCase:
    """Shared production-schema helpers with no access to the user's index."""

    @pytest.fixture(autouse=True)
    def isolated_settings(self) -> Generator[None, None, None]:
        """Keep Settings dimensions and paths independent between tests."""
        get_settings.cache_clear()
        yield
        get_settings.cache_clear()

    @pytest.fixture
    def east_of_utc(self, monkeypatch) -> Generator[None, None, None]:
        """Force a fixed east-of-UTC local zone (WR-09 legacy naive-local rows).

        ``time.tzset`` mutates process-global state, so the prior TZ is
        restored unconditionally in teardown (Asia/Shanghai is fixed UTC+8).
        CliRunner executes in-process, so cleanup_cmd sees the forced zone.
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
        with contextlib.closing(sqlite3.connect(db_path)) as conn:
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

    @pytest.mark.skipif(not hasattr(time, "tzset"), reason="tzset unavailable")
    @pytest.mark.usefixtures("east_of_utc")
    def test_cleanup_removes_legacy_naive_local_expired_cache(self, tmp_path: Path) -> None:
        """WR-09: cleanup deletes legacy naive-local expired rows east of UTC.

        The seeded rows use the exact naive-local form the old ``set`` writer
        produced; the old lexicographic DELETE kept the expired row and
        reported 0 removed. The seeded document/chunk must survive.
        """
        db_path = tmp_path / "sif.db"
        self._seed_document(db_path)
        now = datetime.now(timezone.utc)
        with Database(db_path) as db, db.transaction() as conn:
            for cache_id, instant in (
                ("legacy-expired", (now - timedelta(hours=1)).timestamp()),
                ("legacy-fresh", (now + timedelta(hours=1)).timestamp()),
            ):
                conn.execute(
                    "INSERT INTO llm_cache "
                    "(id, model_name, prompt_hash, prompt, response, created_at, expires_at) "
                    "VALUES (?, 'test-model', ?, 'prompt', 'response', ?, ?)",
                    (
                        cache_id,
                        f"hash-{cache_id}",
                        now.isoformat(),
                        datetime.fromtimestamp(instant).isoformat(),
                    ),
                )

        result = self._invoke(db_path, "cleanup", confirm=True)

        assert result.exit_code == 0, result.output
        assert "Removed 1 expired cache entries" in result.output
        with contextlib.closing(sqlite3.connect(db_path)) as conn:
            assert (
                conn.execute(
                    "SELECT COUNT(*) FROM llm_cache WHERE id = 'legacy-expired'"
                ).fetchone()[0]
                == 0
            )
            assert (
                conn.execute("SELECT COUNT(*) FROM llm_cache WHERE id = 'legacy-fresh'").fetchone()[
                    0
                ]
                == 1
            )
            assert (
                conn.execute("SELECT COUNT(*) FROM documents WHERE id = 'document-1'").fetchone()[0]
                == 1
            )
            assert (
                conn.execute(
                    "SELECT COUNT(*) FROM document_chunks WHERE id = 'chunk-1'"
                ).fetchone()[0]
                == 1
            )


class TestCleanupErrorNarrowing(RealDatabaseTestCase):
    """16.1-02 D-04: the outer cleanup handler catches known classes only.

    The body failure is injected at the repository seam (clear_expired) on a
    real schema-initialized index, so the transaction rollback and handle
    closure run for real. Unexpected bugs (ValueError) keep their tracebacks;
    known-class failures (sqlite3.Error) exit 1 with NO error text on stdout.
    """

    def test_body_value_error_propagates(self, tmp_path: Path) -> None:
        """An unexpected cleanup-body bug is not masked as a user error (D-04)."""
        db_path = tmp_path / "sif.db"
        self._seed_document(db_path)

        with patch.object(
            LLMCacheRepository, "clear_expired", side_effect=ValueError("unexpected cleanup bug")
        ):
            result = self._invoke(db_path, "cleanup", confirm=True)

        assert isinstance(result.exception, ValueError)

    def test_body_sqlite_error_exits_1_with_pure_stdout(self, tmp_path: Path) -> None:
        """Known-class body failure: exit 1, Error: rendered, stdout untouched."""
        db_path = tmp_path / "sif.db"
        self._seed_document(db_path)

        with patch.object(
            LLMCacheRepository,
            "clear_expired",
            side_effect=sqlite3.OperationalError("database is locked"),
        ):
            result = self._invoke(db_path, "cleanup", confirm=True)

        assert result.exit_code == 1
        assert "Error:" in result.output
        # click >=8.2 mixes stderr into .output — purity is asserted on .stdout.
        assert "Error during cleanup" not in result.stdout


class TestIndexPathCreationError:
    """CR-01: a file-parent DB path uses the shared DB-open remedy."""

    def test_regular_file_parent_renders_clean_error(self, tmp_path: Path) -> None:
        """A regular file in the DB parent path must not leak FileExistsError."""
        regular_file = tmp_path / "not-a-directory"
        regular_file.write_text("occupied", encoding="utf-8")

        result = CliRunner().invoke(
            cli,
            ["--index", str(regular_file / "sif.db"), "index", "update"],
        )

        assert result.exit_code == 1
        assert "Cannot open index database at" in result.output
        assert "Check file permissions and free disk space" in result.output
        assert "Traceback" not in result.output
        assert not isinstance(result.exception, FileExistsError)


class TestGroupCallbackDoesNotCreateIndexParent:
    """Ledger 5: the group callback must not materialize the index parent directory.

    Index-parent creation belongs to ``Database.__init__`` inside the shared
    DB-open boundary, so guarded read-only commands that never open the index
    must leave the filesystem untouched.
    """

    def test_guarded_context_commands_create_no_index_parent(self, tmp_path: Path) -> None:
        """Guarded context commands exit early without creating parent or DB."""
        db_path = tmp_path / "never-created" / "sif.db"
        for argv in (
            ["context", "list"],
            ["context", "add", "path", str(tmp_path / "note.md"), "note"],
        ):
            result = CliRunner().invoke(cli, ["--index", str(db_path), *argv])

            assert result.exit_code == 0, result.output
            assert "No index found" in result.output
            assert not db_path.parent.exists()
            assert not db_path.exists()

    def test_db_opening_command_still_creates_index_parent(self, tmp_path: Path) -> None:
        """Positive control: a DB-opening command still creates parent and DB."""
        db_path = tmp_path / "fresh" / "sif.db"

        result = CliRunner().invoke(cli, ["--index", str(db_path), "index", "update"])

        assert result.exit_code == 0, result.output
        assert "No collections found" in result.output
        assert db_path.parent.is_dir()
        assert db_path.exists()


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


class TestConfigOptionRemoved:
    """IN-05: the former global config-path option is removed, not wired.

    The group once accepted the option in long and short form and stored it
    on ctx.obj with zero consumers (configuration comes from SIF_ env vars
    via Pydantic Settings). Per the user decision the option is deleted, so
    Click's parser must reject both spellings and group help must not list
    it. Subcommand-level -c options (--collection/--cmd) are unaffected.
    """

    @pytest.fixture(autouse=True)
    def isolated_settings(self) -> Generator[None, None, None]:
        """Keep Settings caching independent between tests."""
        get_settings.cache_clear()
        yield
        get_settings.cache_clear()

    def test_long_form_config_option_rejected(self, tmp_path: Path) -> None:
        """The long spelling exits 2 with Click's No such option error."""
        result = CliRunner().invoke(
            cli,
            [
                "--config",
                str(tmp_path / "config"),
                "--index",
                str(tmp_path / "sif.db"),
                "status",
            ],
            env={"COLUMNS": "200"},
        )

        assert result.exit_code == 2, result.output
        assert "No such option" in result.output
        assert "--config" in result.output

    def test_short_form_config_option_rejected(self, tmp_path: Path) -> None:
        """The short spelling exits 2 with Click's No such option error."""
        result = CliRunner().invoke(
            cli,
            ["-c", str(tmp_path / "config"), "--index", str(tmp_path / "sif.db"), "status"],
            env={"COLUMNS": "200"},
        )

        assert result.exit_code == 2, result.output
        assert "No such option" in result.output
        assert "-c" in result.output

    def test_help_does_not_list_config_option(self, tmp_path: Path) -> None:
        """Group help succeeds and no longer advertises the removed option."""
        result = CliRunner().invoke(
            cli,
            ["--index", str(tmp_path / "sif.db"), "--help"],
            env={"COLUMNS": "200"},
        )

        assert result.exit_code == 0, result.output
        assert "--config" not in result.output


def test_settings_log_level_controls_cli_logging(monkeypatch) -> None:
    """SIF_LOG_LEVEL reaches setup_logging when no explicit flag is given."""
    from types import SimpleNamespace

    import click

    from sif.cli import main as main_mod

    calls: list[str] = []
    monkeypatch.setattr(main_mod, "setup_logging", calls.append)
    monkeypatch.setattr(
        main_mod, "get_settings", lambda: SimpleNamespace(debug=False, log_level="DEBUG")
    )

    ctx = click.Context(main_mod.cli)
    with ctx:
        main_mod.cli.callback("unused.db", False, False)

    assert calls == ["DEBUG"]


def test_settings_debug_forces_debug_logging(monkeypatch) -> None:
    """SIF_DEBUG=1 takes precedence over the configured log level."""
    from types import SimpleNamespace

    import click

    from sif.cli import main as main_mod

    calls: list[str] = []
    monkeypatch.setattr(main_mod, "setup_logging", calls.append)
    monkeypatch.setattr(
        main_mod, "get_settings", lambda: SimpleNamespace(debug=True, log_level="ERROR")
    )

    ctx = click.Context(main_mod.cli)
    with ctx:
        main_mod.cli.callback("unused.db", False, False)

    assert calls == ["DEBUG"]


def test_explicit_quiet_flag_still_wins_over_settings(monkeypatch) -> None:
    """-q keeps WARNING even when SIF_LOG_LEVEL requests DEBUG."""
    from types import SimpleNamespace

    import click

    from sif.cli import main as main_mod

    calls: list[str] = []
    monkeypatch.setattr(main_mod, "setup_logging", calls.append)
    monkeypatch.setattr(
        main_mod, "get_settings", lambda: SimpleNamespace(debug=False, log_level="DEBUG")
    )

    ctx = click.Context(main_mod.cli)
    with ctx:
        main_mod.cli.callback("unused.db", False, True)

    assert calls == ["WARNING"]


class TestVectorLagText:
    """CORR-06: the status vector-lag text reads the derived shadow.

    The four presentation states are the pre-change contract, asserted
    byte-for-byte. The lagging count comes from one indexed anti-join over
    ``documents``; the helper is exercised directly against a real in-memory
    schema (no vec0 needed — the reader is the shadow).
    """

    @staticmethod
    def _conn(
        *,
        shadow: bool = True,
        shadow_rows: tuple[str, ...] = (),
        document_ids: tuple[str, ...] = (),
    ) -> sqlite3.Connection:
        conn = sqlite3.connect(":memory:")
        conn.execute("CREATE TABLE documents (id TEXT PRIMARY KEY)")
        conn.executemany(
            "INSERT INTO documents (id) VALUES (?)", [(doc_id,) for doc_id in document_ids]
        )
        if shadow:
            conn.execute("CREATE TABLE embedded_documents (document_id TEXT PRIMARY KEY)")
            conn.executemany(
                "INSERT INTO embedded_documents (document_id) VALUES (?)",
                [(doc_id,) for doc_id in shadow_rows],
            )
        return conn

    def test_missing_shadow_renders_na(self) -> None:
        conn = self._conn(shadow=False, document_ids=("d1",))
        try:
            assert _vector_lag_text(conn) == "n/a"
        finally:
            conn.close()

    def test_empty_shadow_renders_no_vectors_state(self) -> None:
        conn = self._conn(document_ids=("d1", "d2"))
        try:
            assert _vector_lag_text(conn) == "none (no vectors indexed)"
        finally:
            conn.close()

    def test_one_lagging_document_is_singular(self) -> None:
        conn = self._conn(shadow_rows=("d1",), document_ids=("d1", "d2"))
        try:
            assert _vector_lag_text(conn) == "1 document"
        finally:
            conn.close()

    def test_multiple_lagging_documents_are_plural(self) -> None:
        conn = self._conn(shadow_rows=("d1",), document_ids=("d1", "d2", "d3"))
        try:
            assert _vector_lag_text(conn) == "2 documents"
        finally:
            conn.close()

    def test_shadow_rows_without_documents_do_not_count(self) -> None:
        """An orphan shadow row cannot produce a negative/zero-document oddity."""
        conn = self._conn(shadow_rows=("d-gone",), document_ids=())
        try:
            assert _vector_lag_text(conn) == "0 documents"
        finally:
            conn.close()


class TestCleanupReconcile(RealDatabaseTestCase):
    """D-10/D-13: cleanup repairs the derived shadow in its existing transaction."""

    def _vector_dim(self, db_path: Path) -> int:
        with contextlib.closing(sqlite3.connect(db_path)) as conn:
            row = conn.execute(
                "SELECT sql FROM sqlite_master WHERE type='table' AND name='document_embeddings'"
            ).fetchone()
        assert row is not None, "the test needs a vec0-bearing database"
        match = re.search(r"float\[(\d+)\]", row[0].lower())
        assert match is not None
        return int(match.group(1))

    def _insert_vector_row(self, db_path: Path) -> None:
        """Insert a raw vec0 row only; the derived shadow is left untouched."""
        dim = self._vector_dim(db_path)
        conn = create_connection(db_path)
        try:
            conn.execute(
                "INSERT INTO document_embeddings "
                "(embedding_id, document_id, chunk_id, embedding) "
                "VALUES ('embedding-1', 'document-1', 'chunk-1', vec_f32(?))",
                (json.dumps([0.1] * dim),),
            )
            conn.commit()
        finally:
            conn.close()

    def _counts(self, db_path: Path) -> tuple[int, int]:
        conn = create_connection(db_path)
        try:
            vectors = conn.execute("SELECT COUNT(*) FROM document_embeddings").fetchone()[0]
            shadow = conn.execute("SELECT COUNT(*) FROM embedded_documents").fetchone()[0]
        finally:
            conn.close()
        return int(vectors), int(shadow)

    def test_cleanup_removes_orphan_vectors_and_never_resurrects_a_shadow_row(
        self, tmp_path: Path
    ) -> None:
        """A document deleted without purging vectors leaves no shadow row."""
        db_path = tmp_path / "sif.db"
        self._seed_document(db_path)
        self._insert_vector_row(db_path)

        conn = create_connection(db_path)
        try:
            conn.execute("DELETE FROM documents WHERE id = 'document-1'")
            conn.commit()
        finally:
            conn.close()
        assert self._counts(db_path) == (1, 0)

        result = self._invoke(db_path, "cleanup", confirm=True)

        assert result.exit_code == 0, result.output
        assert "Removed 1 orphaned embeddings" in result.output
        assert "Reconciled embedded-document markers: 0 removed, 0 added" in result.output
        assert self._counts(db_path) == (0, 0)

    def test_cleanup_inserts_missing_shadow_rows_for_existing_documents(
        self, tmp_path: Path
    ) -> None:
        """A raw vector write that skipped the shadow is repaired by cleanup."""
        db_path = tmp_path / "sif.db"
        self._seed_document(db_path)
        self._insert_vector_row(db_path)
        assert self._counts(db_path) == (1, 0)

        result = self._invoke(db_path, "cleanup", confirm=True)

        assert result.exit_code == 0, result.output
        assert "Reconciled embedded-document markers: 0 removed, 1 added" in result.output
        assert self._counts(db_path) == (1, 1)

    def test_vec0_free_database_runs_cleanup_without_error(self, tmp_path: Path) -> None:
        """A BM25-only database degrades to no markers instead of failing."""
        db_path = tmp_path / "sif.db"
        with patch("sif.database.factory._load_sqlite_vec"):
            self._seed_document(db_path)
            result = self._invoke(db_path, "cleanup", confirm=True)

        assert result.exit_code == 0, result.output
        assert "Reconciled embedded-document markers: 0 removed, 0 added" in result.output
        assert "Removed 0 orphaned embeddings" in result.output
