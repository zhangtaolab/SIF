"""Unit tests for the ``sif watch`` CLI host surface (Phase 12-02).

CLI unit culture (``test_index_locking``): CliRunner invocations against
real tmp-path databases with FileWatcher mocked at the module boundary, and
the D-14 signal/shutdown machinery invoked directly — never real signals
(D-15, zero timing).
"""

from __future__ import annotations

import io
import logging
import sys
from collections.abc import Generator
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
    WatchHostParams,
    _effective_depth,
    _select_collections,
    _service_argv_tail,
    make_signal_handler,
    shutdown_watcher,
)
from sif.config.settings import Settings
from sif.core.models import Collection
from sif.database.database import Database
from sif.database.factory import create_connection
from sif.database.repositories import CollectionRepository
from sif.indexing import watcher as watcher_module
from sif.indexing.incremental import IncrementalIndexer
from sif.indexing.parser import MarkdownParser
from sif.utils import service
from sif.utils.service import InstallResult


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


def _embed_manager_mock(dim: int = 8) -> MagicMock:
    """Build a mocked EmbeddingManager producing deterministic dim-length vectors.

    The same shape ``tests/unit/indexing/test_watcher.py`` proves the worker's
    embed leg with: ``get_model_info`` reports the schema dimension and every
    ``embed()`` call returns a fixed vector per text. The startup-reconcile
    tests use it to observe whether the pre-observer pass really computed
    embeddings at embed depth.
    """
    manager = MagicMock()
    manager.get_model_info.return_value = {
        "loaded": True,
        "model_id": "test-model",
        "embedding_dim": dim,
    }

    def fake_embed(texts: list[str], **_kwargs: object) -> MagicMock:
        vectors = [[0.1] * dim for _ in texts]
        return MagicMock(embeddings=vectors)

    manager.embed.side_effect = fake_embed
    return manager


@pytest.fixture(autouse=True)
def _hermetic_sif_logging() -> Generator[None, None, None]:
    """Isolate this module from leaked sif logger state (deferred D-1).

    The real cli group callback runs setup_logging, which leaves the ``sif``
    logger with propagate=False, a stderr StreamHandler, and a raised level.
    caplog's capture handler sits on the ROOT logger, so that wall stops the
    shutdown WARNING emitted by sif.cli.commands.watch before it ever reaches
    caplog (three predecessor files leak: test_collection, test_get, test_main).
    Test-side isolation only — snapshot, normalize, and restore the sif logger
    chain; the root logger is left to pytest's logging plugin. No production
    logging behavior changes.
    """
    chain = [
        logging.getLogger(name)
        for name in ("sif", "sif.cli", "sif.cli.commands", "sif.cli.commands.watch")
    ]
    snapshots = [(lg, lg.level, lg.propagate, lg.disabled, list(lg.handlers)) for lg in chain]
    manager_disable = logging.Logger.manager.disable
    for lg in chain:
        lg.setLevel(logging.NOTSET)
        lg.propagate = True
        lg.disabled = False
        lg.handlers = []
    logging.Logger.manager.disable = logging.NOTSET
    try:
        yield
    finally:
        for lg, level, propagate, disabled, handlers in snapshots:
            lg.setLevel(level)
            lg.propagate = propagate
            lg.disabled = disabled
            lg.handlers = handlers
        logging.Logger.manager.disable = manager_disable


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

    def test_detach_without_fork_is_refused(self, tmp_path, monkeypatch) -> None:
        """D-06/ENG-02: no os.fork (Windows) refuses with cause+remedy, no traceback."""
        monkeypatch.setattr(watch_mod, "os", SimpleNamespace())

        with patch("sif.config.settings.get_settings", return_value=_test_settings()):
            result = CliRunner().invoke(
                watch_mod.watch_cmd,
                ["--detach"],
                obj={"index_path": tmp_path / "watch.db"},
            )

        assert result.exit_code != 0
        assert "--detach requires POSIX fork" in result.output
        assert "foreground" in result.output
        assert "Traceback" not in result.output

    def test_help_lists_daemon_lifecycle_flags(self) -> None:
        """--help surfaces --detach, --stop, and --log-file."""
        result = CliRunner().invoke(watch_mod.watch_cmd, ["--help"])

        assert result.exit_code == 0
        output = result.output
        assert "--detach" in output
        assert "--stop" in output
        assert "--log-file" in output


class TestServiceFlags:
    """13-04 Test 7: --install-service/--uninstall-service CLI tracer.

    Path.home is patched to tmp_path and the manager-invoking service
    functions are patched at the module boundary, so the CLI wiring is
    exercised without touching real agents or invoking launchctl/systemctl.
    """

    def test_help_lists_service_flags(self) -> None:
        """--help surfaces --install-service and --uninstall-service."""
        result = CliRunner().invoke(watch_mod.watch_cmd, ["--help"])

        assert result.exit_code == 0
        assert "--install-service" in result.output
        assert "--uninstall-service" in result.output

    def test_install_prints_artifact_log_and_verify_and_bakes_tail(
        self, tmp_path, monkeypatch
    ) -> None:
        """Exit 0 with the artifact path, log location, verify command; the
        -c/--embed flags given at install time are baked into the tail (D-11)."""
        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        artifact = tmp_path / "Library" / "LaunchAgents" / "com.docsif.watch.plist"
        fake_result = InstallResult(
            artifact_path=artifact,
            log_location=str(tmp_path / "logs" / "watch.log"),
            verify_command="launchctl print gui/501/com.docsif.watch",
        )
        captured: dict[str, Any] = {}

        def fake_install(db_path, argv_tail, *, manager, **_kwargs):
            captured["db"] = str(db_path)
            captured["tail"] = list(argv_tail)
            captured["manager"] = manager
            return fake_result

        monkeypatch.setattr(watch_mod.service, "install_watch_service", fake_install)

        with patch("sif.config.settings.get_settings", return_value=_test_settings()):
            result = CliRunner().invoke(
                watch_mod.watch_cmd,
                ["--install-service", "-c", "notes", "--embed"],
                obj={"index_path": tmp_path / "watch.db"},
            )

        assert result.exit_code == 0
        # Rich folds the long tmp path across 80-column lines; comparing with
        # newlines stripped keeps the assertion about content, not wrapping.
        flat_output = result.output.replace("\n", "")
        assert str(artifact) in flat_output
        assert fake_result.log_location in flat_output
        assert "launchctl print" in flat_output
        assert captured["tail"] == ["-c", "notes", "--embed"]
        assert captured["manager"] == ("launchd" if sys.platform == "darwin" else "systemd")
        # The service must not depend on a user cwd: the db path is absolute.
        assert Path(captured["db"]).is_absolute()

    def test_install_on_linux_documents_linger(self, tmp_path, monkeypatch) -> None:
        """D-13: the systemd install output surfaces loginctl enable-linger."""
        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        monkeypatch.setattr(watch_mod, "_service_manager", lambda: "systemd")
        fake_result = InstallResult(
            artifact_path=tmp_path / ".config" / "systemd" / "user" / "sif-watch.service",
            log_location="journalctl --user -u sif-watch -f",
            verify_command="systemctl --user status sif-watch",
        )
        monkeypatch.setattr(
            watch_mod.service,
            "install_watch_service",
            lambda *_args, **_kwargs: fake_result,
        )

        with patch("sif.config.settings.get_settings", return_value=_test_settings()):
            result = CliRunner().invoke(
                watch_mod.watch_cmd,
                ["--install-service"],
                obj={"index_path": tmp_path / "watch.db"},
            )

        assert result.exit_code == 0
        assert "loginctl enable-linger" in result.output

    def test_uninstall_reports_stop_then_remove(self, tmp_path, monkeypatch) -> None:
        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        plist = tmp_path / "Library" / "LaunchAgents" / "com.docsif.watch.plist"
        monkeypatch.setattr(watch_mod.service, "uninstall_watch_service", lambda **_kwargs: plist)

        result = CliRunner().invoke(
            watch_mod.watch_cmd,
            ["--uninstall-service"],
            obj={"index_path": tmp_path / "watch.db"},
        )

        assert result.exit_code == 0
        assert str(plist) in result.output.replace("\n", "")
        assert "stopped" in result.output
        assert "removed" in result.output

    def test_install_with_uninstall_is_rejected(self, tmp_path) -> None:
        result = CliRunner().invoke(
            watch_mod.watch_cmd,
            ["--install-service", "--uninstall-service"],
            obj={"index_path": tmp_path / "watch.db"},
        )

        assert result.exit_code != 0
        assert "mutually exclusive" in result.output

    def test_windows_refuses_the_service_with_the_foreground_remedy(
        self, tmp_path, monkeypatch
    ) -> None:
        """D-06/ENG-02: win32 refuses before any systemctl probe, no traceback."""
        monkeypatch.setattr(watch_mod, "sys", SimpleNamespace(platform="win32"))

        with patch("sif.config.settings.get_settings", return_value=_test_settings()):
            result = CliRunner().invoke(
                watch_mod.watch_cmd,
                ["--install-service"],
                obj={"index_path": tmp_path / "watch.db"},
            )

        assert result.exit_code != 0
        assert "not supported on Windows" in result.output
        assert "foreground" in result.output
        assert "Traceback" not in result.output

    def test_argv_tail_pins_the_installed_depth(self) -> None:
        """WR-03/IN-01: embed installs bake --embed; EVERY BM25 install bakes
        --no-embed — unconditionally.

        The BM25 pin is a no-op at the BM25 runtime default and only bites
        when the service's own environment — which is not the installing
        shell's — later carries ``SIF_WATCH_UPDATE_DEPTH=embed`` (a
        ``launchctl setenv`` persists for every LaunchAgent), so an
        installed-BM25 service must never start computing vectors."""
        embed_params = WatchHostParams(
            index_path="/tmp/watch.db",
            debounce_interval=0.5,
            lock_timeout=30.0,
            depth="embed",
            restat_interval=5.0,
        )
        bm25_params = WatchHostParams(
            index_path="/tmp/watch.db",
            debounce_interval=0.5,
            lock_timeout=30.0,
            depth="bm25",
            restat_interval=5.0,
        )

        embed_tail = _service_argv_tail(embed_params, ("notes",))
        bm25_tail = _service_argv_tail(bm25_params, ("notes",))

        assert embed_tail == ["-c", "notes", "--embed"]
        assert bm25_tail == ["-c", "notes", "--no-embed"]

    def test_install_bakes_no_embed_flag_under_ambient_embed_setting(
        self, tmp_path, monkeypatch
    ) -> None:
        """CLI plumbing (WR-03): --install-service --no-embed under
        SIF_WATCH_UPDATE_DEPTH=embed bakes --no-embed into the tail."""
        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        fake_result = InstallResult(
            artifact_path=tmp_path / "Library" / "LaunchAgents" / "com.docsif.watch.plist",
            log_location=str(tmp_path / "logs" / "watch.log"),
            verify_command="launchctl print gui/501/com.docsif.watch",
        )
        captured: dict[str, Any] = {}

        def fake_install(_db_path, argv_tail, **_kwargs):
            captured["tail"] = list(argv_tail)
            return fake_result

        monkeypatch.setattr(watch_mod.service, "install_watch_service", fake_install)

        settings = _test_settings(watch_update_depth="embed")
        with patch("sif.config.settings.get_settings", return_value=settings):
            result = CliRunner().invoke(
                watch_mod.watch_cmd,
                ["--install-service", "-c", "notes", "--no-embed"],
                obj={"index_path": tmp_path / "watch.db"},
            )

        assert result.exit_code == 0
        assert captured["tail"] == ["-c", "notes", "--no-embed"]

    def test_install_plain_bm25_still_bakes_no_embed(self, tmp_path, monkeypatch) -> None:
        """CLI plumbing (IN-01): a plain BM25 install — no depth flags, ambient
        setting bm25 — still bakes --no-embed, so a service environment that
        later carries SIF_WATCH_UPDATE_DEPTH=embed (launchctl setenv persists
        for every LaunchAgent) can never upgrade the service to embed."""
        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        fake_result = InstallResult(
            artifact_path=tmp_path / "Library" / "LaunchAgents" / "com.docsif.watch.plist",
            log_location=str(tmp_path / "logs" / "watch.log"),
            verify_command="launchctl print gui/501/com.docsif.watch",
        )
        captured: dict[str, Any] = {}

        def fake_install(_db_path, argv_tail, **_kwargs):
            captured["tail"] = list(argv_tail)
            return fake_result

        monkeypatch.setattr(watch_mod.service, "install_watch_service", fake_install)

        with patch("sif.config.settings.get_settings", return_value=_test_settings()):
            result = CliRunner().invoke(
                watch_mod.watch_cmd,
                ["--install-service", "-c", "notes"],
                obj={"index_path": tmp_path / "watch.db"},
            )

        assert result.exit_code == 0
        assert captured["tail"] == ["-c", "notes", "--no-embed"]

    def test_install_with_detach_is_rejected(self, tmp_path) -> None:
        """SC3: --detach under the supervisor is the anti-pattern."""
        result = CliRunner().invoke(
            watch_mod.watch_cmd,
            ["--install-service", "--detach"],
            obj={"index_path": tmp_path / "watch.db"},
        )

        assert result.exit_code != 0
        assert "--install-service" in result.output

    def test_install_with_stop_is_rejected(self, tmp_path) -> None:
        result = CliRunner().invoke(
            watch_mod.watch_cmd,
            ["--install-service", "--stop"],
            obj={"index_path": tmp_path / "watch.db"},
        )

        assert result.exit_code != 0
        assert "--install-service" in result.output

    def test_missing_manager_surfaces_as_click_error(self, tmp_path, monkeypatch) -> None:
        """A missing launchctl/systemctl is a friendly ClickException, never a traceback."""
        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        monkeypatch.setattr(service.shutil, "which", lambda _name: None)

        with patch("sif.config.settings.get_settings", return_value=_test_settings()):
            result = CliRunner().invoke(
                watch_mod.watch_cmd,
                ["--install-service"],
                obj={"index_path": tmp_path / "watch.db"},
            )

        assert result.exit_code != 0
        binary = "launchctl" if sys.platform == "darwin" else "systemctl"
        assert binary in result.output
        assert "not found" in result.output


class TestDaemonLogPath:
    """D-07: daemon logs default to the platform log dir; --log-file overrides."""

    def test_default_log_path_is_platform_log_dir(self, tmp_path, monkeypatch) -> None:
        """No --log-file: platformdirs user_log_dir('sif')/watch.log, created."""
        monkeypatch.setattr(watch_mod, "user_log_dir", lambda _app: str(tmp_path / "platlogs"))

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

    def test_shutdown_skips_checkpoint_when_worker_still_busy(self, caplog) -> None:
        """WR-01: a timed-out worker join skips the WAL checkpoint — running
        it on the same connection as a still-live worker is the concurrent
        same-connection use the flush gate already forbids."""
        watcher = MagicMock()
        watcher.worker_joined.return_value = False
        conn = MagicMock()

        with caplog.at_level(logging.WARNING, logger="sif.cli.commands.watch"):
            shutdown_watcher(watcher, conn)

        watcher.stop.assert_called_once_with(flush=True)
        conn.execute.assert_not_called()
        assert any("skipping WAL checkpoint" in r.message for r in caplog.records)

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


class TestStartupReconcileEmbedDepth:
    """qtn: the pre-observer startup pass must be embed-aware at embed depth.

    ``run_watch_host`` reconciles each collection BEFORE ``watcher.start()``
    (D-03). The BM25 update branch purges chunks and embeddings for every
    changed document, so calling ``IncrementalIndexer.update_collection``
    directly leaves the startup pass's changed documents vector-less until a
    later burst or ``sif index embed``. The pass routes through the IN-04
    embed-aware reconcile instead, and these tests pin both halves: the
    embed-depth repair and the unchanged BM25-only behavior.
    """

    def _seed_stale_vectorless_document(self, tmp_path, monkeypatch) -> Path:
        """Seed one BM25-indexed doc, then rewrite it on disk (stale, vector-less).

        Returns the database path. The rewrite changes the body without
        touching any other file, so at HEAD the startup pass takes the
        update branch for exactly this document — the shape that strands it.
        """
        _delenv_settings_vars(monkeypatch)
        db_path = tmp_path / "watch.db"
        _seed_collections(db_path, "notes")
        db = Database(db_path)
        try:
            coll = CollectionRepository(db.connection).get_by_name("notes")
            assert coll is not None
            # BM25-only index: fresh checksum, zero chunks/vectors.
            IncrementalIndexer(db.connection).update_collection(coll)
        finally:
            db.close()
        (tmp_path / "notes" / "a.md").write_text(
            "# Drifted\n\n" + ("Changed paragraph text. " * 40), encoding="utf-8"
        )
        return db_path

    def _install_park_loop(self, monkeypatch) -> dict[int, object]:
        """Stop the host's park loop after its first sleep via the SIGTERM handler.

        The observer is a MagicMock (no real FSEvents), the signal module is a
        fake that captures the installed handlers, and ``time.sleep`` invokes
        the captured SIGTERM handler exactly once — the D-14 graceful path.
        The FileWatcher itself stays REAL: the startup pass under test runs
        through its embed-aware reconcile.
        """
        captured: dict[int, object] = {}

        def fake_signal(sig: int, handler: object) -> None:
            captured[sig] = handler

        monkeypatch.setattr(
            watch_mod,
            "signal",
            SimpleNamespace(signal=fake_signal, SIGINT=2, SIGTERM=15),
        )

        def fake_sleep(_seconds: float) -> None:
            term_handler = captured[15]
            assert callable(term_handler)
            term_handler(15, None)

        monkeypatch.setattr(watch_mod, "time", SimpleNamespace(sleep=fake_sleep))
        monkeypatch.setattr(watcher_module, "Observer", MagicMock())
        return captured

    def test_embed_startup_leaves_no_vectorless_documents(self, tmp_path, monkeypatch) -> None:
        """At --embed depth the startup pass re-embeds what its BM25 leg changed.

        RED at HEAD: the startup pass calls ``update_collection`` directly, the
        update branch purges the stale document's chunks and embeddings, and
        nothing re-embeds them — a fresh connection then sees the document
        without any embedding row.
        """
        db_path = self._seed_stale_vectorless_document(tmp_path, monkeypatch)
        self._install_park_loop(monkeypatch)
        manager = _embed_manager_mock()

        with (
            patch("sif.config.settings.get_settings", return_value=_test_settings()),
            patch(
                "sif.embedding.manager.EmbeddingManager.from_settings",
                return_value=manager,
            ),
        ):
            result = CliRunner().invoke(
                watch_mod.watch_cmd, ["--embed"], obj={"index_path": db_path}
            )

        assert result.exit_code == 0, result.output

        conn = create_connection(db_path)
        try:
            assert conn.execute("SELECT COUNT(*) FROM documents").fetchone()[0] == 1
            vectorless = conn.execute(
                "SELECT d.id FROM documents d WHERE NOT EXISTS ("
                "SELECT 1 FROM document_chunks c "
                "JOIN document_embeddings e ON e.chunk_id = c.id "
                "WHERE c.document_id = d.id)"
            ).fetchall()
        finally:
            conn.close()

        assert vectorless == []
        assert manager.embed.call_count >= 1

    def test_bm25_startup_writes_no_vectors_and_never_loads_model(
        self, tmp_path, monkeypatch
    ) -> None:
        """BM25 depth is byte-behaviour unchanged: same BM25 pass, no model load.

        The embedding factory raises if touched, so any model construction
        fails the test; the stale document still gets its fresh checksum, and
        both chunk and vector tables stay empty.
        """
        db_path = self._seed_stale_vectorless_document(tmp_path, monkeypatch)
        self._install_park_loop(monkeypatch)
        expected_checksum = MarkdownParser().parse(tmp_path / "notes" / "a.md").checksum

        with (
            patch("sif.config.settings.get_settings", return_value=_test_settings()),
            patch(
                "sif.embedding.manager.EmbeddingManager.from_settings",
                side_effect=AssertionError("embedding model must not load at BM25 depth"),
            ),
        ):
            result = CliRunner().invoke(watch_mod.watch_cmd, [], obj={"index_path": db_path})

        assert result.exit_code == 0, result.output

        conn = create_connection(db_path)
        try:
            assert conn.execute("SELECT COUNT(*) FROM documents").fetchone()[0] == 1
            assert conn.execute("SELECT checksum FROM documents").fetchone()[0] == expected_checksum
            assert conn.execute("SELECT COUNT(*) FROM document_chunks").fetchone()[0] == 0
            assert conn.execute("SELECT COUNT(*) FROM document_embeddings").fetchone()[0] == 0
        finally:
            conn.close()
