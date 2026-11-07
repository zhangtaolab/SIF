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

from sif.config.settings import get_settings
from sif.core.models import Collection
from sif.database.database import Database
from sif.database.repositories import CollectionRepository
from sif.indexing.incremental import IncrementalResult
from sif.indexing.watcher import FileWatcher, FoldResult, WatchConfig
from sif.utils.logging import get_logger


logger = get_logger(__name__)

_WAL_CHECKPOINT_TRUNCATE = "PRAGMA wal_checkpoint(TRUNCATE)"

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

    The enqueue shape is the recovery-return job the worker already drains.
    ``queue.Queue.put`` is thread-safe, so queueing from the host thread
    while the freshly started worker idles is race-free.
    """
    for collection in collections:
        watcher._queue.put((collection, FoldResult(needs_reconcile=True)))  # noqa: SLF001


def start_embedded_watch(db_path: str) -> EmbeddedWatch | None:
    """Start the embedded watcher when ``SIF_MCP_WATCH`` opted in (D-04).

    Returns ``None`` — and never opens a watch ``Database`` — when the flag
    is unset/false or when zero collections are registered (the server keeps
    serving in both cases). Otherwise the watcher starts immediately and the
    per-collection reconcile lands as the worker's first queued jobs, so the
    caller's serving loop (or FastAPI lifespan yield) is never delayed by
    indexing work.
    """
    settings = get_settings()
    if not settings.mcp_watch:
        logger.info("MCP watch disabled (SIF_MCP_WATCH unset/false); serving without a watcher")
        return None

    db = Database(db_path)
    try:
        db.init_schema()
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
            debounce_interval=settings.watch_debounce_interval,
            lock_timeout=settings.lock_wait_timeout,
            depth=_MCP_WATCH_DEPTH,
            restat_interval=settings.watch_restat_interval,
            on_event=_render_event,
            on_batch=_render_batch,
            rescope_provider=_registered_collections,
            rescope_interval=settings.watch_rescope_interval,
            checkpoint_interval=settings.watch_checkpoint_interval,
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
    the WAL truncate checkpoint runs on the host connection in a
    ``finally`` so a failed flush still checkpoints; the ``Database`` closes
    last. Tolerates ``None`` so callers can stop unconditionally.
    """
    if watch is None:
        return
    try:
        try:
            watch.watcher.stop(flush=True)
        finally:
            watch.db.connection.execute(_WAL_CHECKPOINT_TRUNCATE)
    finally:
        watch.db.close()
    logger.info("MCP watch stopped")


def mcp_watch_lifespan(db_path: str) -> Callable[[Any], Any]:
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
        watch = start_embedded_watch(db_path)
        try:
            yield
        finally:
            stop_embedded_watch(watch)

    return _lifespan
