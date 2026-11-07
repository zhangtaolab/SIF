"""Unit tests for the ``sif watch`` CLI host surface (Phase 12-02).

CLI unit culture (``test_index_locking``): CliRunner invocations against
real tmp-path databases with FileWatcher mocked at the module boundary, and
the D-14 signal/shutdown machinery invoked directly — never real signals
(D-15, zero timing).
"""

from __future__ import annotations

import io
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from unittest.mock import MagicMock, patch

import click
import pytest
from click.testing import CliRunner
from pydantic import ValidationError
from rich.console import Console

from sif.cli.commands import watch as watch_mod
from sif.cli.commands.watch import (
    SignalState,
    _effective_depth,
    _select_collections,
    make_signal_handler,
    shutdown_watcher,
)
from sif.config.settings import Settings
from sif.core.models import Collection
from sif.database.database import Database
from sif.database.repositories import CollectionRepository


WAL_CHECKPOINT_TRUNCATE = "PRAGMA wal_checkpoint(TRUNCATE)"
BODY = "# Watch Note\n\nBody text for the watch command test. " * 10


def _delenv_settings_vars(monkeypatch: pytest.MonkeyPatch) -> None:
    """Keep Settings construction hermetic against a developer shell."""
    for var in (
        "SIF_EMBEDDING_DIM",
        "SIF_MODEL_TYPE",
        "SIF_MODEL_NAME",
        "SIF_WATCH_UPDATE_DEPTH",
        "SIF_WATCH_RESTAT_INTERVAL",
    ):
        monkeypatch.delenv(var, raising=False)


def _test_settings(**overrides: Any) -> Settings:
    """Build hermetic test settings."""
    return Settings(embedding_dim=8, model_name="test", cache_embeddings=False, **overrides)  # type: ignore[arg-type]


def _seed_collections(db_path: Path, *names: str) -> None:
    """Init schema and register one collection per name, each with one file."""
    db = Database(db_path)
    with patch("sif.config.settings.get_settings", return_value=_test_settings()):
        db.init_schema()
        with db.connection:
            for name in names:
                root = db_path.parent / name
                root.mkdir(exist_ok=True)
                (root / "a.md").write_text(BODY, encoding="utf-8")
                CollectionRepository(db.connection).create(Collection(name=name, path=str(root)))
    db.close()


class TestHelpSurface:
    """Test 1: the flag surface and the D-02 restart note."""

    def test_help_lists_flags_and_restart_note(self) -> None:
        """--help lists -c (repeatable), --embed, --no-embed, --verbose; restart note."""
        result = CliRunner().invoke(watch_mod.watch_cmd, ["--help"])

        assert result.exit_code == 0
        output = result.output
        assert "-c, --collection" in output
        assert "--embed" in output
        assert "--no-embed" in output
        assert "--verbose" in output
        assert "restart" in output


class TestCollectionFilter:
    """Test 2: -c filters to the named subset; unknown names use update_cmd wording."""

    def test_select_collections_filters_to_named_subset(self, tmp_path, monkeypatch) -> None:
        """`-c notes -c docs` selects exactly those collections, in flag order."""
        _delenv_settings_vars(monkeypatch)
        db_path = tmp_path / "watch.db"
        _seed_collections(db_path, "notes", "docs", "journal")
        db = Database(db_path)
        try:
            coll_repo = CollectionRepository(db.connection)
            selected = _select_collections(coll_repo, ("notes", "docs"))
        finally:
            db.close()

        assert [coll.name for coll in selected] == ["notes", "docs"]

    def test_select_collections_dedupes_repeated_names_in_flag_order(
        self, tmp_path, monkeypatch
    ) -> None:
        """WR-02: `-c notes -c docs -c notes` selects notes, docs — once each."""
        _delenv_settings_vars(monkeypatch)
        db_path = tmp_path / "watch.db"
        _seed_collections(db_path, "notes", "docs", "journal")
        db = Database(db_path)
        try:
            coll_repo = CollectionRepository(db.connection)
            selected = _select_collections(coll_repo, ("notes", "docs", "notes"))
        finally:
            db.close()

        assert [coll.name for coll in selected] == ["notes", "docs"]

    def test_select_collections_unknown_name_raises_update_cmd_wording(
        self, tmp_path, monkeypatch
    ) -> None:
        """An unknown -c name raises ClickException with update_cmd's wording."""
        _delenv_settings_vars(monkeypatch)
        db_path = tmp_path / "watch.db"
        _seed_collections(db_path, "notes")
        db = Database(db_path)
        try:
            coll_repo = CollectionRepository(db.connection)
            with pytest.raises(click.ClickException, match="Collection 'missing' not found"):
                _select_collections(coll_repo, ("notes", "missing"))
        finally:
            db.close()


class TestZeroCollections:
    """Test 3: zero registered collections prints the update_cmd notice, exit 0."""

    def test_zero_collections_prints_notice_and_never_starts_watcher(
        self, tmp_path, monkeypatch
    ) -> None:
        _delenv_settings_vars(monkeypatch)
        db_path = tmp_path / "watch.db"
        db = Database(db_path)
        with patch("sif.config.settings.get_settings", return_value=_test_settings()):
            db.init_schema()
        db.close()

        watcher_cls = MagicMock()
        monkeypatch.setattr(watch_mod, "FileWatcher", watcher_cls)
        with patch("sif.config.settings.get_settings", return_value=_test_settings()):
            result = CliRunner().invoke(watch_mod.watch_cmd, [], obj={"index_path": db_path})

        assert result.exit_code == 0
        assert "No collections found" in result.output
        watcher_cls.assert_not_called()


class TestDepthMatrix:
    """Test 4: LIVE-05 depth matrix — flags win, then the setting, default bm25."""

    def test_default_depth_is_bm25(self, monkeypatch) -> None:
        _delenv_settings_vars(monkeypatch)
        assert _effective_depth(embed=False, no_embed=False, settings=_test_settings()) == "bm25"

    def test_embed_flag_forces_embed(self, monkeypatch) -> None:
        _delenv_settings_vars(monkeypatch)
        assert _effective_depth(embed=True, no_embed=False, settings=_test_settings()) == "embed"

    def test_setting_embed_activates_embed(self, monkeypatch) -> None:
        monkeypatch.delenv("SIF_WATCH_UPDATE_DEPTH", raising=False)
        monkeypatch.setenv("SIF_WATCH_UPDATE_DEPTH", "embed")
        assert _effective_depth(embed=False, no_embed=False, settings=Settings()) == "embed"

    def test_no_embed_flag_forces_bm25_over_setting(self, monkeypatch) -> None:
        monkeypatch.setenv("SIF_WATCH_UPDATE_DEPTH", "embed")
        assert _effective_depth(embed=False, no_embed=True, settings=Settings()) == "bm25"

    def test_invalid_depth_value_fails_settings_validation(self, monkeypatch) -> None:
        monkeypatch.delenv("SIF_WATCH_UPDATE_DEPTH", raising=False)
        with pytest.raises(ValidationError):
            Settings(watch_update_depth="bogus")


class TestInvalidSettingsSurfacing:
    """IN-02: with an explicit ``--index``, the group's default-path callable
    never runs, so watch_cmd's own get_settings() is the first Settings
    construction — invalid config must surface as a ClickException there,
    not escape as a raw pydantic traceback."""

    def test_invalid_depth_with_explicit_index_is_a_click_error(
        self, tmp_path, monkeypatch
    ) -> None:
        _delenv_settings_vars(monkeypatch)
        monkeypatch.setenv("SIF_WATCH_UPDATE_DEPTH", "bogus")

        from sif.config.settings import get_settings

        get_settings.cache_clear()
        try:
            result = CliRunner().invoke(
                watch_mod.watch_cmd, [], obj={"index_path": tmp_path / "watch.db"}
            )
        finally:
            get_settings.cache_clear()

        assert result.exit_code == 1
        assert "Invalid watch_update_depth" in result.output
        assert not isinstance(result.exception, ValidationError)


class TestEventRenderingEscapesMarkup:
    """IN-01: payloads (file names, collection names) are user data — Rich
    must render bracketed text like ``report[v2].md`` literally instead of
    consuming ``[v2]`` as a style tag."""

    def _captured_output(self, monkeypatch, render) -> str:
        """Run ``render`` with the module console pointed at a StringIO."""
        buf = io.StringIO()
        monkeypatch.setattr(watch_mod, "console", Console(file=buf, width=200))
        render()
        return buf.getvalue()

    def test_bracketed_filename_renders_literally(self, monkeypatch) -> None:
        """`indexed report[v2].md` keeps its `[v2]` under --verbose."""
        out = self._captured_output(
            monkeypatch,
            lambda: watch_mod._render_watch_event("indexed report[v2].md", verbose=True),
        )

        assert "Indexed: report[v2].md" in out

    def test_error_and_missing_payloads_stay_visible_and_escaped(self, monkeypatch) -> None:
        """Error/missing lines always print (no --verbose) and stay literal."""
        out = self._captured_output(
            monkeypatch,
            lambda: [
                watch_mod._render_watch_event(
                    "error Embedding failed for report[v2].md: boom", verbose=False
                ),
                watch_mod._render_watch_event("missing notes[2024]", verbose=False),
            ],
        )

        assert "Embedding failed for report[v2].md: boom" in out
        assert "Collection root missing: notes[2024]" in out

    def test_batch_summary_escapes_collection_name(self, monkeypatch) -> None:
        """The per-batch summary line keeps a bracketed collection name."""
        out = self._captured_output(
            monkeypatch,
            lambda: watch_mod._render_batch(
                "notes[v1]", added=2, updated=1, removed=0, unchanged=3
            ),
        )

        assert "notes[v1]: indexed 3" in out


class TestDaemonFlagGuards:
    """13-02 Tests 4-5: lifecycle-flag guards, help surface, D-07 log path."""

    def test_detach_with_stop_is_rejected(self, tmp_path) -> None:
        """--detach and --stop are mutually exclusive lifecycle actions."""
        result = CliRunner().invoke(
            watch_mod.watch_cmd,
            ["--detach", "--stop"],
            obj={"index_path": tmp_path / "watch.db"},
        )

        assert result.exit_code != 0
        assert "--detach and --stop are mutually exclusive" in result.output

    def test_log_file_without_detach_is_rejected(self, tmp_path) -> None:
        """--log-file only means something for the detached daemon."""
        result = CliRunner().invoke(
            watch_mod.watch_cmd,
            ["--log-file", str(tmp_path / "daemon.log")],
            obj={"index_path": tmp_path / "watch.db"},
        )

        assert result.exit_code != 0
        assert "--log-file requires --detach" in result.output

    def test_help_lists_daemon_lifecycle_flags(self) -> None:
        """--help surfaces --detach, --stop, and --log-file."""
        result = CliRunner().invoke(watch_mod.watch_cmd, ["--help"])

        assert result.exit_code == 0
        output = result.output
        assert "--detach" in output
        assert "--stop" in output
        assert "--log-file" in output


class TestDaemonLogPath:
    """D-07: daemon logs default to the platform log dir; --log-file overrides."""

    def test_default_log_path_is_platform_log_dir(self, tmp_path, monkeypatch) -> None:
        """No --log-file: platformdirs user_log_dir('sif')/watch.log, created."""
        monkeypatch.setattr(watch_mod, "user_log_dir", lambda app: str(tmp_path / "platlogs"))

        path = watch_mod._daemon_log_path(None)

        assert path == tmp_path / "platlogs" / "watch.log"
        assert path.parent.is_dir()

    def test_explicit_log_file_overrides_default(self, tmp_path) -> None:
        """--log-file wins over the platform default and creates its parent."""
        target = tmp_path / "custom-dir" / "daemon.log"

        path = watch_mod._daemon_log_path(str(target))

        assert path == target
        assert path.parent.is_dir()


class TestSignalMachinery:
    """Test 5: first signal sets the stop flag; second raises SystemExit 130."""

    def test_first_signal_sets_stop_flag(self) -> None:
        state = SignalState()
        handler = make_signal_handler(state)

        handler(2, None)

        assert state.stop is True
        assert state.signal_count == 1

    def test_second_signal_raises_system_exit_130(self) -> None:
        state = SignalState()
        handler = make_signal_handler(state)
        handler(2, None)

        with pytest.raises(SystemExit) as exc_info:
            handler(2, None)

        assert exc_info.value.code == 130


class TestShutdownRoutine:
    """Test 6: D-14 teardown — one bounded flush, then the WAL truncate checkpoint."""

    def test_shutdown_stops_once_with_flush_and_checkpoints(self) -> None:
        watcher = MagicMock()
        conn = MagicMock()

        shutdown_watcher(watcher, conn)

        watcher.stop.assert_called_once_with(flush=True)
        conn.execute.assert_called_once_with(WAL_CHECKPOINT_TRUNCATE)

    def test_graceful_sigterm_exits_zero_and_shares_the_routine(
        self, tmp_path, monkeypatch
    ) -> None:
        """SIGTERM and SIGINT install one handler; TERM mid-loop exits 0 after teardown."""
        _delenv_settings_vars(monkeypatch)
        db_path = tmp_path / "watch.db"
        _seed_collections(db_path, "notes")

        captured: dict[int, object] = {}

        def fake_signal(sig: int, handler: object) -> None:
            captured[sig] = handler

        monkeypatch.setattr(
            watch_mod,
            "signal",
            SimpleNamespace(signal=fake_signal, SIGINT=2, SIGTERM=15),
        )

        sleep_calls = {"count": 0}

        def fake_sleep(_seconds: float) -> None:
            if sleep_calls["count"] == 0:
                sleep_calls["count"] += 1
                term_handler = captured[15]
                assert callable(term_handler)
                term_handler(15, None)

        monkeypatch.setattr(watch_mod, "time", SimpleNamespace(sleep=fake_sleep))

        watcher_cls = MagicMock()
        monkeypatch.setattr(watch_mod, "FileWatcher", watcher_cls)
        watcher_instance = watcher_cls.return_value

        with patch("sif.config.settings.get_settings", return_value=_test_settings()):
            result = CliRunner().invoke(watch_mod.watch_cmd, [], obj={"index_path": db_path})

        assert result.exit_code == 0
        watcher_instance.stop.assert_called_once_with(flush=True)
        # TERM shares the routine: both signals installed the same handler.
        assert captured[2] is captured[15]
