"""MCP-embedded watch host: one FileWatcher core, transport-agnostic (D-01).

``start_embedded_watch`` builds the Phase 12 watch pipeline inside the MCP
server process behind the ``SIF_MCP_WATCH`` opt-in (D-04): with the flag off
(or no registered collections) it returns ``None`` and MCP serving stays
byte-identical to the flag-free path. Two invariants are load-bearing:

- **Depth is the literal ``bm25``** (D-02): the update-depth setting is
  deliberately never consulted here — a background host the user did not
  launch with an explicit embed flag must never compute embeddings (the
  billing-surprise guard). Vector catch-up stays ``sif embed`` / foreground
  ``sif watch --embed``.
- **Logger-only callbacks** (Pitfall 1): stdout is the stdio JSON-RPC
  protocol channel, so every watch event/batch renders through
  ``get_logger`` (stderr handlers) — never console/print.

Serving never waits on indexing (Pitfall 4): the watcher starts immediately
and the per-collection startup reconcile is enqueued as the worker's first
jobs (checksum skipping absorbs the startup burst, 12-D03). The rescope
provider returns ALL registered collections on the 13-01 tick seam (D-15) —
MCP context has no ``-c`` filter. Shutdown follows the D-14 ordering adapted
to this host owning its connection: stop(flush=True), then the WAL truncate
checkpoint, then close.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator, Callable
from contextlib import asynccontextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from sif.config.settings import Settings, get_settings
from sif.core.models import Collection
from sif.database.database import Database
from sif.database.factory import WAL_CHECKPOINT_TRUNCATE
from sif.database.repositories import CollectionRepository
from sif.embedding.identity import EmbedderIdentity, build_settings_identity
from sif.embedding.prompts import resolve_prompt_scheme
from sif.indexing.incremental import IncrementalResult
from sif.indexing.watcher import FileWatcher, WatchConfig
from sif.utils.logging import get_logger


logger = get_logger(__name__)

# D-02: the literal depth for every embedded watcher — never read from
# settings, whatever the ambient update-depth configuration says.
_MCP_WATCH_DEPTH = "bm25"


@dataclass
class EmbeddedWatch:
    """Handle for one started embedded watcher: the watcher plus its Database.

    The host owns the connection (the watcher's worker and the checkpoint
    share it), so :func:`stop_embedded_watch` needs both to tear down in the
    D-14 order.
    """

    watcher: FileWatcher
    db: Database


def _render_event(event: str) -> None:
    """Render one watch progress event to the module logger (Pitfall 1).

    stdout is the stdio JSON-RPC channel — the logger's stderr handlers are
    the only safe output. Errors and missing roots stay at warning+; routine
    progress goes to debug so a busy watcher cannot flood the log.
    """
    code, _, payload = event.partition(" ")
    if code == "error":
        logger.error("mcp watch: %s", payload)
    elif code == "missing":
        logger.warning("mcp watch: collection root missing: %s (documents preserved)", payload)
    else:
        logger.debug("mcp watch: %s %s", code, payload)


def _render_batch(collection: Collection, result: IncrementalResult) -> None:
    """Render one settled-batch summary to the module logger (Pitfall 1)."""
    logger.info(
        "mcp watch: %s indexed %s updated %s removed %s unchanged %s",
        collection.name,
        result.added,
        result.updated,
        result.removed,
        result.unchanged,
    )


def _enqueue_startup_reconcile(watcher: FileWatcher, collections: list[Collection]) -> None:
    """Queue one full-reconcile job per collection — serve first (Pitfall 4).

    Delegates to the watcher's public reconcile-intent API (W-3/D-06); the
    job representation stays private to the watcher. ``queue.Queue.put`` is
    thread-safe, so queueing from the host thread while the freshly started
    worker idles is race-free.
    """
    watcher.enqueue_reconcile(collections)


def _settings_identity(settings: Settings) -> EmbedderIdentity:
    """Build the settings-only identity, exactly as ``SearchBackend`` does.

    The watch host opens the index before any search request, so it must
    migrate and check the schema at the *injected* settings' dimension and
    identity — never the process environment's (WR-08).
    """
    scheme = resolve_prompt_scheme(
        settings.model_name,
        settings.model_type,
        settings.query_prompt_name,
        settings.document_prompt_name,
    )
    return build_settings_identity(settings, scheme)


def start_embedded_watch(db_path: str, settings: Settings | None = None) -> EmbeddedWatch | None:
    """Start the embedded watcher when ``SIF_MCP_WATCH`` opted in (D-04).

    ``settings`` is the host's resolved settings (from ``build_server``/
    ``create_http_app``/``run_stdio``); only ``None`` falls back to the process
    environment. The watch opens the schema at those settings' dimension and
    identity so it cannot migrate the index at the environment width before
    the backend does (WR-08).

    Returns ``None`` — and never opens a watch ``Database`` — when the flag
    is unset/false or when zero collections are registered (the server keeps
    serving in both cases). Otherwise the watcher starts immediately and the
    per-collection reconcile lands as the worker's first queued jobs, so the
    caller's serving loop (or FastAPI lifespan yield) is never delayed by
    indexing work.
    """
    resolved = settings if settings is not None else get_settings()
    if not resolved.mcp_watch:
        logger.info("MCP watch disabled (SIF_MCP_WATCH unset/false); serving without a watcher")
        return None

    db = Database(db_path)
    try:
        db.init_schema(
            embedding_dim=resolved.embedding_dim,
            identity=_settings_identity(resolved),
        )
        collections = CollectionRepository(db.connection).list_all()
    except Exception:
        db.close()
        raise
    if not collections:
        logger.info(
            "MCP watch: no registered collections; watcher stays off (server keeps serving)"
        )
        db.close()
        return None

    repo = CollectionRepository(db.connection)

    def _registered_collections() -> list[Collection]:
        """Eligible set for the D-15 rescope poll: every registered collection."""
        return repo.list_all()

    watcher = FileWatcher(
        collections,
        db.connection,
        Path(db_path),
        WatchConfig(
            debounce_interval=resolved.watch_debounce_interval,
            lock_timeout=resolved.lock_wait_timeout,
            depth=_MCP_WATCH_DEPTH,
            restat_interval=resolved.watch_restat_interval,
            on_event=_render_event,
            on_batch=_render_batch,
            rescope_provider=_registered_collections,
            rescope_interval=resolved.watch_rescope_interval,
            checkpoint_interval=resolved.watch_checkpoint_interval,
        ),
    )
    watcher.start()
    # Pitfall 4: reconcile on the worker, never before serving. Checksum
    # skipping absorbs the startup burst either way (12-D03 rationale).
    _enqueue_startup_reconcile(watcher, collections)
    logger.info(
        "MCP watch started: %d collection(s), depth %s (D-02)",
        len(collections),
        _MCP_WATCH_DEPTH,
    )
    return EmbeddedWatch(watcher=watcher, db=db)


def stop_embedded_watch(watch: EmbeddedWatch | None) -> None:
    """Stop the embedded watcher: flush, checkpoint, close (D-14 ordering).

    ``stop(flush=True)`` quiesces the worker and drains queued jobs once;
    the WAL truncate checkpoint runs on the host connection only when the
    worker actually exited (WR-01: a timed-out join means a job still runs
    on the same connection, and a checkpoint there is concurrent
    same-connection use — skipped with a warning instead); the ``Database``
    closes last. Tolerates ``None`` so callers can stop unconditionally.
    """
    if watch is None:
        return
    try:
        watch.watcher.stop(flush=True)
        if watch.watcher.worker_joined():
            watch.db.connection.execute(WAL_CHECKPOINT_TRUNCATE)
        else:
            logger.warning("MCP watch: worker still busy at shutdown; skipping WAL checkpoint")
    finally:
        watch.db.close()
    logger.info("MCP watch stopped")


def mcp_watch_lifespan(db_path: str, settings: Settings | None = None) -> Callable[[Any], Any]:
    """FastAPI lifespan FACTORY hosting the embedded watcher (D-01 HTTP wiring).

    Returns a callable accepting the app that itself returns an async context
    manager — the exact shape Starlette's ``Router.lifespan`` executes
    (``async with self.lifespan_context(app)``). Never hand FastAPI an
    already-invoked context manager: its ``__call__`` is contextlib's
    decorator protocol and startup dies with ``TypeError`` (CR-01). The
    factory still keeps this module free of a fastapi import (import-light,
    no optional-dependency try/except). Before the yield (the app accepts
    requests) the watcher starts; after the yield (serving ended) it stops
    with the full D-14 teardown. The flag check lives inside
    :func:`start_embedded_watch`, so the wiring is unconditional and cheap
    when the opt-in is off.
    """

    @asynccontextmanager
    async def _lifespan(_app: Any) -> AsyncGenerator[None, None]:
        watch = start_embedded_watch(db_path, settings)
        try:
            yield
        finally:
            stop_embedded_watch(watch)

    return _lifespan


def mcp_session_lifespan(
    db_path: str,
    session_manager: Any,
    settings: Settings | None = None,
) -> Callable[[Any], Any]:
    """FastAPI lifespan FACTORY composing the SDK session manager and the watch.

    D-18 ordering: enter ``session_manager.run()`` (which enters the SDK's own
    lifespan), start the embedded watcher, yield, stop the watcher, then exit
    the session manager. ``session_manager`` is duck-typed (the SDK's
    ``StreamableHTTPSessionManager``) so this module keeps no SDK import; the
    caller resolves it after ``streamable_http_app()`` created it. The injected
    ``settings`` govern the watcher's flag and schema width (WR-08); the flag
    check stays inside :func:`start_embedded_watch`, so ``SIF_MCP_WATCH`` off
    leaves serving unchanged.
    """

    @asynccontextmanager
    async def _lifespan(_app: Any) -> AsyncGenerator[None, None]:
        async with session_manager.run():
            watch = start_embedded_watch(db_path, settings)
            try:
                yield
            finally:
                stop_embedded_watch(watch)

    return _lifespan
