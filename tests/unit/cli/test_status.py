"""Tests for status CLI command."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from click.testing import CliRunner

from sif.cli.main import status_cmd


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

        with patch("sif.cli.main.get_settings", return_value=mock_settings):
            with patch("sif.cli.main.Database") as MockDB:
                mock_db = MagicMock()
                mock_db.get_stats.return_value = {
                    "collections": 1,
                    "documents": 5,
                    "chunks": 10,
                    "contexts": 0,
                    "total_size_bytes": 1024,
                }
                MockDB.return_value = mock_db
                result = runner.invoke(status_cmd)

        assert result.exit_code == 0
        # Verify Database was called with the Settings-resolved path
        MockDB.assert_called_once()
        call_path = MockDB.call_args[0][0]
        assert str(call_path) == custom_path

    def test_status_respects_env_var(self) -> None:
        """Test that status command respects SIF_DB_PATH env var."""
        runner = CliRunner(env={"SIF_DB_PATH": "/tmp/test-sif.db"})

        mock_settings = MagicMock()
        mock_path = MagicMock()
        mock_path.exists.return_value = True
        mock_path.__str__ = MagicMock(return_value="/tmp/test-sif.db")
        mock_settings.get_db_path.return_value = mock_path

        with patch("sif.cli.main.get_settings", return_value=mock_settings):
            with patch("sif.cli.main.Database") as MockDB:
                mock_db = MagicMock()
                mock_db.get_stats.return_value = {
                    "collections": 0,
                    "documents": 0,
                    "chunks": 0,
                    "contexts": 0,
                    "total_size_bytes": 0,
                }
                MockDB.return_value = mock_db
                result = runner.invoke(status_cmd)

        # The command should use the env var path
        assert result.exit_code == 0
        MockDB.assert_called_once()
        call_path = MockDB.call_args[0][0]
        assert str(call_path) == "/tmp/test-sif.db"
