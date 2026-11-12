"""Unit battery for the MCP-embedded watch host (LIVE-08, Phase 13).

Patches land at module boundaries (tests/unit/mcp culture); real tmp DBs back
the construction assertions that need real rows. Pins the decision surface:
flag-off byte-identity (D-04 — no Database is ever opened), depth forced to
the literal bm25 even under an embed configuration (D-02, the billing guard),
the zero-collection no-op, serve-first startup reconcile (Pitfall 4 — the
reconcile is queued, never inline), the D-14 stop ordering, logger-only
renderers (Pitfall 1 — stdout is the stdio JSON-RPC channel), rescope wiring
(D-15), and the FastAPI lifespan factory contract (D-01).
"""

from __future__ import annotations

import logging
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from sif.config.settings import Settings
from sif.core.models import Collection
from sif.database.database import Database
from sif.database.repositories import CollectionRepository
from sif.indexing import watcher as watcher_mod
from sif.mcp import watch_host
from sif.mcp.watch_host import EmbeddedWatch, start_embedded_watch, stop_embedded_watch


def _make_db(db_path: Path, *, with_collection: bool) -> Path:
    """Build a real schema; optionally register one collection over a file tree.

    Returns the collection root so callers can create drift inside it.
    """
    root = db_path.parent / "notes"
    if with_collection:
        root.mkdir(parents=True, exist_ok=True)
        (root / "seed.md").write_text("# Seed Note\n\nSeed paragraph text.\n", encoding="utf-8")
    db = Database(db_path)
    try:
        db.init_schema()
        if with_collection:
            with db.connection:
                CollectionRepository(db.connection).create(Collection(name="notes", path=str(root)))
    finally:
        db.close()
    return root


def test_flag_off_returns_none_and_never_opens_database() -> None:
    """D-04: with mcp_watch false, no watcher AND no watch Database — serving
    stays byte-identical to the flag-free path."""
    settings = Settings(mcp_watch=False)
    with (
        patch.object(watch_host, "get_settings", return_value=settings),
        patch.object(watch_host, "Database") as database,
    ):
        result = start_embedded_watch("/tmp/any-index.db")

    assert result is None
    database.assert_not_called()


def test_depth_forced_bm25_even_when_settings_say_embed(tmp_path: Path) -> None:
    """D-02 pin: settings say embed, the constructed watcher still gets bm25 —
    the MCP host never embeds (billing-surprise guard)."""
    db_path = tmp_path / "watch.db"
    _make_db(db_path, with_collection=True)
    settings = Settings(mcp_watch=True, watch_update_depth="embed")

    with (
        patch.object(watch_host, "get_settings", return_value=settings),
        patch.object(watch_host, "FileWatcher") as watcher_cls,
    ):
        result = start_embedded_watch(str(db_path))

    assert result is not None
    config = watcher_cls.call_args[0][3]
    assert config.depth == "bm25"
    # D-15: the rescope provider is wired and returns every registered
    # collection (MCP context has no -c filter).
    assert [coll.name for coll in config.rescope_provider()] == ["notes"]
    stop_embedded_watch(result)


def test_zero_collections_returns_none_with_notice(tmp_path: Path, caplog) -> None:
    """Empty-input edge: flag on but nothing registered — None, a logged
    notice, and no watcher constructed (the server keeps serving)."""
    db_path = tmp_path / "watch.db"
    _make_db(db_path, with_collection=False)
    settings = Settings(mcp_watch=True)

    with (
        patch.object(watch_host, "get_settings", return_value=settings),
        patch.object(watch_host, "FileWatcher") as watcher_cls,
        caplog.at_level(logging.INFO, logger=watch_host.logger.name),
    ):
        result = start_embedded_watch(str(db_path))

    assert result is None
    watcher_cls.assert_not_called()
    assert any("no registered collections" in record.message for record in caplog.records)


def test_startup_reconcile_is_queued_not_inline(tmp_path: Path) -> None:
    """Pitfall 4: the per-collection reconcile lands as a queued worker job —
    the indexer runs only when the queue drains (stop's flush), never inline
    during start, so serving never waits on indexing."""
    db_path = tmp_path / "watch.db"
    _make_db(db_path, with_collection=True)
    settings = Settings(mcp_watch=True)
    real_file_watcher = watcher_mod.FileWatcher

    def _quiesced(collections, conn, db_path_arg, config=None):
        """Build a real watcher whose worker loop is a no-op (13-01 pattern):
        queued jobs stay queued until the flush drain runs them."""
        watcher = real_file_watcher(collections, conn, db_path_arg, config)
        watcher._worker_loop = lambda: None
        return watcher

    with (
        patch.object(watch_host, "get_settings", return_value=settings),
        patch.object(watch_host, "FileWatcher", _quiesced),
        patch.object(watcher_mod, "IncrementalIndexer") as indexer_cls,
    ):
        result = start_embedded_watch(str(db_path))
        assert result is not None
        # Serve-first: the reconcile job sits queued; the indexer never ran.
        indexer_cls.return_value.update_collection.assert_not_called()
        assert result.watcher._queue.qsize() == 1
        job = result.watcher._queue.get_nowait()
        result.watcher._queue.put(job)
        # stop(flush=True) drains the queue on the calling thread: the
        # reconcile runs NOW, at teardown — never during start.
        stop_embedded_watch(result)
        indexer_cls.return_value.update_collection.assert_called_once()


def test_startup_calls_start_then_public_enqueue_with_full_collections(tmp_path: Path) -> None:
    """W-3/D-06: host startup routes through the public reconcile-intent API —
    watcher.start() precedes watcher.enqueue_reconcile(collections), the FULL
    collections list is handed over in one call, and no indexing runs before
    the queue drains (serve-first preserved, 13-D04/Pitfall 4)."""
    db_path = tmp_path / "watch.db"
    _make_db(db_path, with_collection=True)
    more = tmp_path / "more"
    more.mkdir()
    (more / "note.md").write_text("# More\n\nSecond collection text.\n", encoding="utf-8")
    db = Database(db_path)
    try:
        with db.connection:
            CollectionRepository(db.connection).create(Collection(name="more", path=str(more)))
    finally:
        db.close()
    settings = Settings(mcp_watch=True)
    real_file_watcher = watcher_mod.FileWatcher
    calls: list[tuple[str, list[str] | None]] = []

    def _quiesced(collections, conn, db_path_arg, config=None):
        """Real watcher, no-op worker; start/enqueue append to the shared call
        log BEFORE delegating, so the log proves the host's call order."""
        watcher = real_file_watcher(collections, conn, db_path_arg, config)
        watcher._worker_loop = lambda: None
        real_start = watcher.start
        real_enqueue = watcher.enqueue_reconcile

        def _start() -> None:
            calls.append(("start", None))
            real_start()

        def _enqueue(colls) -> None:
            materialized = list(colls)
            calls.append(("enqueue_reconcile", [coll.name for coll in materialized]))
            real_enqueue(materialized)

        watcher.start = _start
        watcher.enqueue_reconcile = _enqueue
        return watcher

    with (
        patch.object(watch_host, "get_settings", return_value=settings),
        patch.object(watch_host, "FileWatcher", _quiesced),
        patch.object(watcher_mod, "IncrementalIndexer") as indexer_cls,
    ):
        result = start_embedded_watch(str(db_path))
        assert result is not None
        # start() first, then ONE public enqueue carrying every collection.
        assert calls == [("start", None), ("enqueue_reconcile", ["more", "notes"])]
        # Serve-first: both reconcile jobs sit queued; the indexer never ran.
        indexer_cls.return_value.update_collection.assert_not_called()
        assert result.watcher._queue.qsize() == 2
        stop_embedded_watch(result)
        # The flush drain at teardown runs both reconciles — never during start.
        assert indexer_cls.return_value.update_collection.call_count == 2


def test_enqueue_reconcile_fifo_order_and_private_payload(tmp_path: Path) -> None:
    """D-06: enqueue_reconcile([alpha, beta]) on a quiesced watcher yields
    exactly two jobs, dequeued FIFO alpha then beta, each a needs_reconcile-only
    FoldResult with empty candidate sets — proven by dequeuing actual jobs,
    never qsize alone (Pitfall 11)."""
    db_path = tmp_path / "watch.db"
    alpha_root = tmp_path / "alpha"
    beta_root = tmp_path / "beta"
    alpha_root.mkdir()
    beta_root.mkdir()
    alpha = Collection(name="alpha", path=str(alpha_root))
    beta = Collection(name="beta", path=str(beta_root))
    db = Database(db_path)
    watcher = None
    try:
        db.init_schema()
        watcher = watcher_mod.FileWatcher([alpha, beta], db.connection, db_path)
        watcher._worker_loop = lambda: None
        watcher.start()

        watcher.enqueue_reconcile([alpha, beta])

        assert watcher._queue.qsize() == 2
        first_collection, first_fold = watcher._queue.get_nowait()
        watcher._queue.task_done()
        second_collection, second_fold = watcher._queue.get_nowait()
        watcher._queue.task_done()
        assert [first_collection.name, second_collection.name] == ["alpha", "beta"]
        for folded in (first_fold, second_fold):
            assert folded.needs_reconcile is True
            assert folded.index_candidates == set()
            assert folded.remove_candidates == set()
        assert watcher._queue.empty()
    finally:
        if watcher is not None:
            watcher.stop(flush=False)
        db.close()


def test_watch_host_exposes_no_foldresult_attribute() -> None:
    """W-3 module boundary: the host import is narrowed to FileWatcher and
    WatchConfig — FoldResult (the private job payload) never enters the host
    namespace (D-06: the job representation stays private to watcher.py)."""
    assert not hasattr(watch_host, "FoldResult")


def test_watch_host_source_contains_no_private_queue_suppression() -> None:
    """W-3/no-noqa culture: the last SLF001 reach-in into the watcher queue is
    gone — zero suppression markers remain in the host source (baseline at
    the pre-fix HEAD: 1)."""
    source = Path(watch_host.__file__).read_text(encoding="utf-8")
    assert source.count("noqa: SLF001") == 0


def test_renderers_log_only_and_never_touch_stdout(caplog, capsys) -> None:
    """Pitfall 1: event/batch renderers emit logger records only — sys.stdout
    (the stdio JSON-RPC channel) receives nothing."""
    batch = SimpleNamespace(added=1, updated=2, removed=0, unchanged=3)
    with caplog.at_level(logging.DEBUG, logger=watch_host.logger.name):
        watch_host._render_event("error embedding went boom")
        watch_host._render_event("missing /gone/root")
        watch_host._render_event("indexed a.md")
        watch_host._render_batch(Collection(name="notes", path="/notes"), batch)

    captured = capsys.readouterr()
    assert captured.out == ""
    messages = [record.message for record in caplog.records]
    assert any("embedding went boom" in message for message in messages)
    assert any("/gone/root" in message for message in messages)
    assert any("indexed a.md" in message for message in messages)
    assert any("notes" in message for message in messages)


def test_stop_embedded_watch_is_none_safe() -> None:
    """Tolerates None so callers can stop unconditionally."""
    stop_embedded_watch(None)


def test_stop_embedded_watch_flushes_checkpoints_then_closes() -> None:
    """D-14 ordering adapted to the host-owned connection: stop(flush=True),
    then PRAGMA wal_checkpoint(TRUNCATE) on the watch connection, then close."""
    calls: list[str] = []
    watcher = MagicMock()
    watcher.stop.side_effect = lambda **_kwargs: calls.append("stop")
    db = MagicMock()
    db.connection.execute.side_effect = lambda sql, *_args, **_kwargs: (
        calls.append(f"execute:{sql}") or MagicMock()
    )
    db.close.side_effect = lambda: calls.append("close")

    stop_embedded_watch(EmbeddedWatch(watcher=watcher, db=db))

    watcher.stop.assert_called_once_with(flush=True)
    assert calls == ["stop", "execute:PRAGMA wal_checkpoint(TRUNCATE)", "close"]


def test_stop_embedded_watch_skips_checkpoint_when_worker_busy(caplog) -> None:
    """WR-01: a timed-out worker join skips the checkpoint — the still-live
    worker owns the same connection mid-job, so a checkpoint there is the
    concurrent use the flush gate forbids. The Database still closes."""
    watcher = MagicMock()
    watcher.worker_joined.return_value = False
    db = MagicMock()
    closed: list[bool] = []
    db.close.side_effect = lambda: closed.append(True)

    with caplog.at_level(logging.WARNING, logger=watch_host.logger.name):
        stop_embedded_watch(EmbeddedWatch(watcher=watcher, db=db))

    watcher.stop.assert_called_once_with(flush=True)
    db.connection.execute.assert_not_called()
    assert closed == [True]
    assert any("skipping WAL checkpoint" in record.message for record in caplog.records)


@pytest.mark.asyncio
async def test_lifespan_factory_starts_before_yield_and_stops_after() -> None:
    """D-01: mcp_watch_lifespan returns a lifespan factory — invoking it with
    the app yields a context manager that starts the watcher before the
    yield (app accepts requests) and stops it after (serving ended)."""
    from sif.mcp.watch_host import mcp_watch_lifespan

    started: list[str] = []
    stopped: list[object] = []
    fake_watch = MagicMock()

    def _start(db_path: str) -> MagicMock:
        started.append(db_path)
        return fake_watch

    def _stop(watch: object) -> None:
        stopped.append(watch)

    with (
        patch.object(watch_host, "start_embedded_watch", side_effect=_start),
        patch.object(watch_host, "stop_embedded_watch", side_effect=_stop),
    ):
        async with mcp_watch_lifespan("/tmp/x.db")(None):
            assert started == ["/tmp/x.db"]
            assert stopped == []

    assert stopped == [fake_watch]


@pytest.mark.asyncio
async def test_lifespan_factory_tolerates_disabled_watch() -> None:
    """Flag off (start returns None) still yields — the lifespan guards the
    None so the app serves watch-free (D-04)."""
    from sif.mcp.watch_host import mcp_watch_lifespan

    with (
        patch.object(watch_host, "start_embedded_watch", return_value=None),
        patch.object(watch_host, "stop_embedded_watch") as stop,
    ):
        async with mcp_watch_lifespan("/tmp/x.db")(None):
            pass

    stop.assert_called_once_with(None)


@pytest.mark.asyncio
async def test_lifespan_factory_stops_even_when_body_raises() -> None:
    """A failing app body still stops the watcher — the stop is in a finally."""
    from sif.mcp.watch_host import mcp_watch_lifespan

    with (
        patch.object(watch_host, "start_embedded_watch", return_value=None),
        patch.object(watch_host, "stop_embedded_watch") as stop,
    ):
        with pytest.raises(RuntimeError, match="app died"):
            async with mcp_watch_lifespan("/tmp/x.db")(None):
                raise RuntimeError("app died")

    stop.assert_called_once_with(None)
