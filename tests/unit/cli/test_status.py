"""Tests for status CLI command."""

from __future__ import annotations

import json
import sqlite3
from typing import Any, ClassVar
from unittest.mock import MagicMock, patch

from click.testing import CliRunner
from pydantic import ValidationError

from sif.cli.commands.index import index_status_cmd
from sif.cli.main import status_cmd
from sif.config.settings import get_settings


def _mock_stats() -> dict:
    return {
        "collections": 1,
        "documents": 5,
        "chunks": 10,
        "contexts": 0,
        "total_size_bytes": 1024,
    }


class TestStatusCommand:
    """Tests for status command."""

    def test_status_uses_settings_db_path(self) -> None:
        """Test that status respects SIF_DB_PATH via Settings."""
        runner = CliRunner()
        custom_path = "/custom/path/sif.db"

        mock_settings = MagicMock()
        mock_path = MagicMock()
        mock_path.exists.return_value = True
        mock_path.__str__ = MagicMock(return_value=custom_path)
        mock_settings.get_db_path.return_value = mock_path

        with (
            patch("sif.cli.main.get_settings", return_value=mock_settings),
            patch("sif.cli.main.Database") as mock_db_cls,
        ):
            mock_db = MagicMock()
            mock_db.get_stats.return_value = {
                "collections": 1,
                "documents": 5,
                "chunks": 10,
                "contexts": 0,
                "total_size_bytes": 1024,
            }
            # status_cmd owns the Database via `with Database(...) as db:`, so
            # the instance bound in the scope is the __enter__ result.
            mock_db_cls.return_value.__enter__.return_value = mock_db
            result = runner.invoke(status_cmd)

        assert result.exit_code == 0
        # Verify Database was called with the Settings-resolved path
        mock_db_cls.assert_called_once()
        call_path = mock_db_cls.call_args[0][0]
        assert str(call_path) == custom_path

    def test_status_respects_env_var(self) -> None:
        """Test that status command respects SIF_DB_PATH env var."""
        runner = CliRunner(env={"SIF_DB_PATH": "/tmp/test-sif.db"})

        mock_settings = MagicMock()
        mock_path = MagicMock()
        mock_path.exists.return_value = True
        mock_path.__str__ = MagicMock(return_value="/tmp/test-sif.db")
        mock_settings.get_db_path.return_value = mock_path

        with (
            patch("sif.cli.main.get_settings", return_value=mock_settings),
            patch("sif.cli.main.Database") as mock_db_cls,
        ):
            mock_db = MagicMock()
            mock_db.get_stats.return_value = {
                "collections": 0,
                "documents": 0,
                "chunks": 0,
                "contexts": 0,
                "total_size_bytes": 0,
            }
            # Ownership scope binds the __enter__ result (see test above).
            mock_db_cls.return_value.__enter__.return_value = mock_db
            result = runner.invoke(status_cmd)

        # The command should use the env var path
        assert result.exit_code == 0
        mock_db_cls.assert_called_once()
        call_path = mock_db_cls.call_args[0][0]
        assert str(call_path) == "/tmp/test-sif.db"


class TestWatchSection:
    """13-02 D-08: status renders a Watch row from the PID file + corroboration.

    The daemon helpers are patched at the module boundary (sif.utils.daemon);
    the Database stays mocked per the existing CliRunner culture. One code
    path (status_cmd) serves both ``sif status`` and the ``sif index status``
    alias.
    """

    _RUNNING_PAYLOAD: ClassVar[dict] = {
        "pid": 4242,
        "mode": "daemon",
        "depth": "bm25",
        "started": "2026-11-07T00:00:00+00:00",
    }

    def _invoke(self, command: Any, db_path, monkeypatch, payload, corroborate=True) -> Any:
        db_path.touch()
        mock_db = MagicMock()
        mock_db.get_stats.return_value = _mock_stats()
        monkeypatch.setattr(
            "sif.utils.daemon.read_pid_file",
            lambda _path: dict(payload) if payload is not None else None,
        )
        if payload is not None:
            monkeypatch.setattr("sif.utils.daemon.corroborate_pid", lambda _pl: corroborate)
        with patch("sif.cli.main.Database") as mock_db_cls:
            mock_db_cls.return_value.__enter__.return_value = mock_db
            return CliRunner().invoke(command, [], obj={"index_path": db_path})

    def test_running_daemon_renders_pid_mode_depth(self, tmp_path, monkeypatch):
        """Corroborated payload -> a Watch row naming PID, daemon mode, depth."""
        result = self._invoke(
            status_cmd,
            tmp_path / "sif.db",
            monkeypatch,
            payload=self._RUNNING_PAYLOAD,
            corroborate=True,
        )

        assert result.exit_code == 0
        output = result.output
        assert "Watch" in output
        assert "running" in output
        assert "daemon" in output
        assert "PID 4242" in output
        assert "bm25" in output

    def test_corroborate_false_reports_not_running_and_cleans_stale_file(
        self, tmp_path, monkeypatch
    ):
        """A live-looking payload whose identity fails is stale, never running."""
        db_path = tmp_path / "sif.db"
        db_path.touch()
        stale = db_path.with_name(db_path.name + ".watch.pid")
        stale.write_text(json.dumps(self._RUNNING_PAYLOAD), encoding="utf-8")

        result = self._invoke(
            status_cmd, db_path, monkeypatch, payload=self._RUNNING_PAYLOAD, corroborate=False
        )

        assert result.exit_code == 0
        assert "not running" in result.output
        assert "stale PID file removed" in result.output
        assert not stale.exists()

    def test_garbage_payload_reports_not_running_and_cleans_file(self, tmp_path, monkeypatch):
        db_path = tmp_path / "sif.db"
        db_path.touch()
        stale = db_path.with_name(db_path.name + ".watch.pid")
        stale.write_bytes(b"\x00garbage")

        result = self._invoke(status_cmd, db_path, monkeypatch, payload=None)

        assert result.exit_code == 0
        assert "not running" in result.output
        assert "stale PID file removed" in result.output
        assert not stale.exists()

    def test_missing_pid_file_reports_not_running(self, tmp_path, monkeypatch):
        result = self._invoke(status_cmd, tmp_path / "sif.db", monkeypatch, payload=None)

        assert result.exit_code == 0
        assert "not running" in result.output
        assert "stale" not in result.output

    def test_watch_section_renders_for_index_status_alias(self, tmp_path, monkeypatch):
        """``sif index status`` delegates to status_cmd — one code path, same row."""
        result = self._invoke(
            index_status_cmd,
            tmp_path / "sif.db",
            monkeypatch,
            payload=self._RUNNING_PAYLOAD,
            corroborate=True,
        )

        assert result.exit_code == 0
        output = result.output
        assert "Watch" in output
        assert "PID 4242" in output


class TestVectorLag:
    """14-02 D-10: status renders a Vector lag row from the derived scan.

    The Database stays mocked per the TestWatchSection culture; the probe
    source (embedded_document_ids) is patched at the module boundary for the
    armed states, and the documents scan is fed through the mocked
    connection's cursor.
    """

    def _invoke(self, db_path, monkeypatch, *, embedded=None, doc_ids=None, probe=None):
        """Invoke status_cmd with the lag probe's sources controlled.

        embedded: value embedded_document_ids returns (patched only when
            given; use probe for the None / raising cases).
        doc_ids: rows the ``SELECT id FROM documents`` scan yields.
        probe: full replacement for sif.cli.main.embedded_document_ids.
        """
        db_path.touch()
        mock_db = MagicMock()
        mock_db.get_stats.return_value = _mock_stats()
        if probe is not None:
            monkeypatch.setattr("sif.cli.main.embedded_document_ids", probe)
        elif embedded is not None:
            monkeypatch.setattr("sif.cli.main.embedded_document_ids", lambda _conn: embedded)
        if doc_ids is not None:
            mock_db.connection.execute.return_value = iter(doc_ids)
        monkeypatch.setattr("sif.utils.daemon.read_pid_file", lambda _path: None)
        with patch("sif.cli.main.Database") as mock_db_cls:
            mock_db_cls.return_value.__enter__.return_value = mock_db
            return CliRunner().invoke(status_cmd, [], obj={"index_path": db_path})

    def test_lag_count_renders_documents(self, tmp_path, monkeypatch):
        """Index with embeddings and 2 of 3 docs lagging -> '2 documents'."""
        result = self._invoke(
            tmp_path / "sif.db",
            monkeypatch,
            embedded={"d-embedded"},
            doc_ids=[("d-embedded",), ("d-lag-1",), ("d-lag-2",)],
        )

        assert result.exit_code == 0
        assert "Vector lag" in result.output
        assert "2 documents" in result.output

    def test_zero_embeddings_renders_no_vectors_state(self, tmp_path, monkeypatch):
        """Pure-BM25 index (no embeddings at all) -> 'none (no vectors indexed)'."""
        result = self._invoke(
            tmp_path / "sif.db",
            monkeypatch,
            embedded=set(),
            doc_ids=["d-1", "d-2"],
        )

        assert result.exit_code == 0
        assert "Vector lag" in result.output
        assert "none (no vectors indexed)" in result.output

    def test_vec0_missing_renders_na(self, tmp_path, monkeypatch):
        """No vec0 table -> the row reads n/a."""
        result = self._invoke(tmp_path / "sif.db", monkeypatch, probe=lambda _conn: None)

        assert result.exit_code == 0
        assert "Vector lag" in result.output
        assert "n/a" in result.output

    def test_probe_failure_renders_degraded_never_raises(self, tmp_path, monkeypatch):
        """Any unexpected probe failure renders the degraded text; exit stays 0."""
        result = self._invoke(
            tmp_path / "sif.db",
            monkeypatch,
            probe=MagicMock(side_effect=RuntimeError("probe exploded")),
        )

        assert result.exit_code == 0
        assert "Vector lag" in result.output
        assert "n/a" in result.output


class TestStatusFallbackConfigError:
    """Phase 10 IN-06: the index_path-None fallback must guard get_settings().

    Invoking status_cmd with a context obj lacking index_path (obj={}) hits
    the fallback; invalid env config there must render the same one-line
    Click error as _get_default_db_path, not a raw pydantic traceback.
    get_settings is lru_cache'd, so the cache must be cleared AFTER the env
    var is set (a prior cached success would mask the invalid env) and again
    in finally for hygiene (monkeypatch restores the env at teardown, so the
    cache must be empty when it does).
    """

    def test_status_fallback_wraps_validation_error(self, monkeypatch) -> None:
        """Invalid SIF_RERANKER_MODEL_TYPE on the fallback path -> one-line Error."""
        monkeypatch.setenv("SIF_RERANKER_MODEL_TYPE", "cross-encoder")
        get_settings.cache_clear()
        try:
            result = CliRunner().invoke(status_cmd, [], obj={})
        finally:
            get_settings.cache_clear()

        assert result.exit_code == 1
        assert "Error:" in result.output
        assert "reranker_model_type" in result.output
        assert "Traceback" not in result.output
        # click 8.3.2's CliRunner stores SystemExit after Click renders a
        # ClickException, so pin the exception negatively instead of
        # asserting isinstance(result.exception, click.ClickException).
        assert not isinstance(result.exception, ValidationError)


class TestStatusErrorNarrowing:
    """16.1-02 D-04: the outer status handler catches known classes only.

    Unexpected body bugs (ValueError) keep their tracebacks; known-class
    body failures (sqlite3.Error/OSError) render as exit-1 Click errors with
    NO error text on stdout (the old Rich console.print polluted --json pipes).
    """

    def _invoke(self, db_path, side_effect: Exception) -> Any:
        db_path.touch()
        mock_db = MagicMock()
        mock_db.get_stats.side_effect = side_effect
        with patch("sif.cli.main.Database") as mock_db_cls:
            # The shared opener yields the constructed instance; the legacy
            # `with Database(...)` form binds its __enter__ result — wire both
            # so the double works on either side of the conversion.
            mock_db_cls.return_value = mock_db
            mock_db.__enter__.return_value = mock_db
            return CliRunner().invoke(status_cmd, [], obj={"index_path": db_path})

    def test_body_value_error_propagates(self, tmp_path) -> None:
        """An unexpected get_stats bug is not masked as a user error (D-04)."""
        result = self._invoke(tmp_path / "sif.db", ValueError("unexpected status bug"))

        assert isinstance(result.exception, ValueError)

    def test_body_sqlite_error_exits_1_with_pure_stdout(self, tmp_path) -> None:
        """Known-class body failure: exit 1, Error: rendered, stdout untouched."""
        result = self._invoke(
            tmp_path / "sif.db", sqlite3.OperationalError("database disk image is malformed")
        )

        assert result.exit_code == 1
        assert "Error:" in result.output
        # click >=8.2 mixes stderr into .output — purity is asserted on .stdout.
        assert "Error reading index" not in result.stdout
