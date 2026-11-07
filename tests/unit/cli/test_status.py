"""Tests for status CLI command."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

from click.testing import CliRunner

from sif.cli.commands.index import index_status_cmd
from sif.cli.main import status_cmd


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

    _RUNNING_PAYLOAD = {
        "pid": 4242,
        "mode": "daemon",
        "depth": "bm25",
        "started": "2026-11-07T00:00:00+00:00",
    }

    def _invoke(self, command, db_path, monkeypatch, payload, corroborate=True):
        db_path.touch()
        mock_db = MagicMock()
        mock_db.get_stats.return_value = _mock_stats()
        monkeypatch.setattr(
            "sif.utils.daemon.read_pid_file",
            lambda path: dict(payload) if payload is not None else None,
        )
        if payload is not None:
            monkeypatch.setattr(
                "sif.utils.daemon.corroborate_pid", lambda pl: corroborate
            )
        with patch("sif.cli.main.Database") as mock_db_cls:
            mock_db_cls.return_value.__enter__.return_value = mock_db
            result = CliRunner().invoke(command, [], obj={"index_path": db_path})
        return result

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

    def test_garbage_payload_reports_not_running_and_cleans_file(
        self, tmp_path, monkeypatch
    ):
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
