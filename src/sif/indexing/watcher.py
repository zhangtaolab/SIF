"""Host-agnostic filesystem-watch pipeline for live indexing (Phase 12).

observer -> IndexingEventHandler -> EventDebouncer -> fold_events -> queue ->
single worker thread -> per-burst index_lock -> IncrementalIndexer. The
module owns no presentation: hosts pass ``on_event``/``on_batch`` callbacks
and render themselves (D-13). At embed depth the worker adds an inline
chunk+embed leg that computes embeddings OUTSIDE any write transaction
(D-09). Signal handling and the WAL checkpoint stay in the CLI host (D-14);
the worker's idle wait doubles as the D-12 missing-root re-stat loop.
"""

from __future__ import annotations

import contextlib
import os
import queue
import re
import sqlite3
import threading
import time
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from functools import partial
from pathlib import Path
from typing import TYPE_CHECKING, cast

from watchdog.events import FileSystemEvent, FileSystemEventHandler
from watchdog.observers import Observer
from watchdog.observers.api import BaseObserver, ObservedWatch
from watchdog.utils.event_debouncer import EventDebouncer

from sif.core.models import Collection
from sif.database.locking import index_lock
from sif.database.repositories import DocumentChunkRepository, DocumentRepository
from sif.indexing.incremental import IncrementalIndexer, IncrementalResult
from sif.indexing.scanner import FileScanner
from sif.utils.logging import get_logger


if TYPE_CHECKING:
    from sif.embedding.manager import EmbeddingManager
    from sif.indexing.chunker import Chunker
    from sif.search.vector import VectorSearcher


logger = get_logger(__name__)

_JOIN_TIMEOUT_SECONDS = 5.0
_WORKER_JOIN_TIMEOUT_SECONDS = 10.0

SettledCallback = Callable[[list[FileSystemEvent]], None]

# Wakes a worker parked on its re-stat-timeout idle wait so shutdown never
# waits out the interval; nothing is enqueued after it (D-14 bounded stop).
_WORKER_STOP_SENTINEL = None

# The shutdown-checkpoint spelling (12-D14) reused by the D-16 idle tick.
_WAL_CHECKPOINT_TRUNCATE = "PRAGMA wal_checkpoint(TRUNCATE)"

# D-17 remedy text: the standard Linux fix for inotify watch exhaustion.
_INOTIFY_REMEDY = (
    "on Linux this is usually inotify watch exhaustion — raise "
    "fs.inotify.max_user_watches (e.g. sysctl -w fs.inotify.max_user_watches=524288)"
)


def _event_path(path: bytes | str) -> str:
    """Normalize a watchdog event path to str (T-12-01)."""
    return os.fsdecode(path)


@dataclass
class FoldResult:
    """Candidate paths folded from one settled event burst (D-06).

    Disk is truth and events are hints: candidates are stat-checked by
    ``IncrementalIndexer.update_paths`` before anything is written.
    """

    index_candidates: set[Path] = field(default_factory=set)
    remove_candidates: set[Path] = field(default_factory=set)
    needs_reconcile: bool = False


@dataclass
class WatchConfig:
    """Tunables and host callbacks for :class:`FileWatcher`.

    Bundled so the constructor stays under the project's argument-count lint
    gate; host flags extend this struct without touching call sites. The
    ``rescope_provider``/``rescope_interval``/``checkpoint_interval`` trio is
    the long-lived-host opt-in (D-15/D-16): 13-02's daemon and 13-03's MCP
    watch host wire them, and the foreground MVP host passes none of the
    three, keeping its restart-on-change behavior. ``now`` is the tick clock
    — monotonic in production, injectable for zero-timing tests.
    """

    debounce_interval: float = 0.5
    lock_timeout: float = 30.0
    depth: str = "bm25"
    restat_interval: float = 5.0
    on_event: Callable[[str], None] | None = None
    on_batch: Callable[[Collection, IncrementalResult], None] | None = None
    rescope_provider: Callable[[], list[Collection]] | None = None
    rescope_interval: float = 0.0
    checkpoint_interval: float = 0.0
    now: Callable[[], float] = time.monotonic


@dataclass
class _WatchState:
    """Per-collection watch lifecycle state for the D-12 recovery loop."""

    collection: Collection
    root: Path
    handle: ObservedWatch | None = None
    missing: bool = False
    debouncer: EventDebouncer | None = None
    # D-17 warn-once flag: one schedule-failure warning per failure episode
    # (reset on a successful schedule so a later episode warns again).
    schedule_warned: bool = False


def fold_events(
    events: Iterable[FileSystemEvent],
    should_track: Callable[[Path], bool],
) -> FoldResult:
    """Fold one settled event batch into candidate path sets (D-06/D-07).

    ``created``/``modified`` mark the src path for indexing; ``deleted`` marks
    it for removal; ``moved`` marks dest for indexing and src for removal.
    Directory events are skipped except directory ``moved``, which flags
    ``needs_reconcile`` (children get no individual events — Pitfall 7).
    Every candidate is resolved (FSEvents delivers realpaths — Pitfall 2) and
    predicate-checked via ``should_track``; a path both touched and deleted
    in one burst stays an index candidate only — update_paths stats it and
    disk state decides. The fold is order-independent by construction.

    Args:
        events: Settled batch from the EventDebouncer callback.
        should_track: The collection's shared scanner predicate.

    Returns:
        The folded candidate sets and reconcile flag.
    """
    result = FoldResult()
    for event in events:
        if event.is_directory:
            if event.event_type == "moved":
                result.needs_reconcile = True
            continue
        src = Path(_event_path(event.src_path)).resolve()
        if event.event_type in ("created", "modified"):
            result.index_candidates.add(src)
        elif event.event_type == "deleted":
            result.remove_candidates.add(src)
        elif event.event_type == "moved":
            dest = Path(_event_path(event.dest_path)).resolve()
            result.index_candidates.add(dest)
            result.remove_candidates.add(src)
    result.index_candidates = {p for p in result.index_candidates if should_track(p)}
    result.remove_candidates = {p for p in result.remove_candidates if should_track(p)}
    # A path both touched and deleted in the same burst is an index
    # candidate: the stat inside update_paths lets the disk state decide
    # (the atomic-save trailing delete and delete+create pairs both land
    # here), and a gone index candidate is still removed by that stat.
    result.remove_candidates -= result.index_candidates
    return result


class IndexingEventHandler(FileSystemEventHandler):
    """Thin forwarder: every dispatched event goes to the bound debouncer.

    watchdog's ``dispatch`` invokes ``on_any_event`` before the per-type
    handlers (verified against the installed 6.0.0 source), so this single
    intake override is exactly one forward per event.
    """

    def __init__(self, debouncer: EventDebouncer) -> None:
        """Bind the handler to its debouncer.

        Args:
            debouncer: EventDebouncer receiving every dispatched event.
        """
        self._debouncer = debouncer

    def on_any_event(self, event: FileSystemEvent) -> None:
        """Forward one event into the debounce pipeline."""
        self._debouncer.handle_event(event)


class _EmbedSession:
    """Lazy embed-depth state for the watch worker (D-09/LIVE-05).

    Nothing loads at construction — the model loads on first embed work and
    stays cached, keeping watch startup BM25-cheap. The first use also runs
    embed_cmd's probe-free dimension check against the vec0 schema; any
    first-use failure (backend missing, model load, dimension mismatch,
    sqlite-vec unavailable) is fail-soft: one ``error`` event, embed
    disabled for the session, BM25 freshness continues.
    """

    def __init__(self, conn: sqlite3.Connection) -> None:
        """Initialize with a factory connection; model work stays lazy."""
        self._conn = conn
        self._attempted = False
        self._ready = False
        self._manager: EmbeddingManager | None = None
        self._searcher: VectorSearcher | None = None
        self._chunker: Chunker | None = None
        # Per-collection paths whose embed leg failed (WR-01): the BM25 leg
        # already committed their fresh checksum, so the checksum diff alone
        # never re-selects them — the next burst unions them back in.
        self._pending_retry: dict[str, set[Path]] = {}

    def ensure_ready(self, on_event: Callable[[str], None] | None) -> bool:
        """Load the model once and validate its dimension (fail-soft)."""
        if self._attempted:
            return self._ready
        self._attempted = True
        try:
            from sif.config.settings import get_settings  # noqa: PLC0415
            from sif.embedding.manager import EmbeddingManager  # noqa: PLC0415
            from sif.indexing.chunker import create_chunker  # noqa: PLC0415
            from sif.search.vector import VectorSearcher  # noqa: PLC0415

            manager = EmbeddingManager.from_settings(get_settings())
            # Load eagerly (idempotent, cached) so backend-missing and
            # model-load failures surface here, fail-soft.
            manager.load_model()
            info = manager.get_model_info()
            model_dim = info.get("embedding_dim")
            if not isinstance(model_dim, int):
                raise RuntimeError(f"embedding model reported no dimension: {info!r}")
            schema_dim = self._schema_embedding_dim()
            if schema_dim is not None and schema_dim != model_dim:
                raise RuntimeError(
                    f"Model '{info.get('model_id', 'embedding model')}' produces "
                    f"{model_dim}-dim embeddings but the index stores "
                    f"{schema_dim}-dim vectors"
                )
            self._manager = manager
            self._searcher = VectorSearcher(self._conn, model_dim)
            self._chunker = create_chunker("auto")  # embed_cmd's default strategy
            self._ready = True
        except Exception as e:
            self._notify(on_event, f"error Embedding disabled for this watch session: {e}")
            self._ready = False
        return self._ready

    def embed_documents(
        self,
        collection: Collection,
        paths: Iterable[Path],
        on_event: Callable[[str], None] | None,
    ) -> None:
        """Chunk and embed changed documents (D-09 sequence).

        Chunking and embedding compute with NO write transaction open —
        explicitly NOT embed_cmd's inside-txn shape (Pitfall 5) — then one
        short closing transaction persists chunk rows and batched vectors.
        Candidates also include this collection's pending-retry paths
        (WR-01): a path whose embed failed an earlier burst is retried here
        even though its checksum no longer counts as changed. A per-path
        failure emits one ``error`` event, leaves earlier candidates
        durable, and re-queues only that path for the next burst.
        """
        candidates = sorted(set(paths) | self._pending_retry.pop(collection.id, set()))
        if not candidates:
            return
        if not self.ensure_ready(on_event):
            # Session-level fail-soft (embed disabled for good): retrying can
            # never succeed, so the popped paths are dropped, matching the
            # one-error-event contract.
            return
        manager = self._manager
        searcher = self._searcher
        chunker = self._chunker
        assert manager is not None
        assert searcher is not None
        assert chunker is not None
        doc_repo = DocumentRepository(self._conn)
        chunk_repo = DocumentChunkRepository(self._conn)
        failed: set[Path] = set()
        for path in candidates:
            try:
                doc = doc_repo.get_by_path(str(path), collection.id)
                if doc is None:
                    continue
                chunks = chunker.chunk(doc.content)
                if not chunks:
                    continue
                # Embedding compute never runs inside an open write transaction.
                vectors = manager.embed([chunk.content for chunk in chunks]).embeddings
                # One short vector-write txn: chunk rows + batched vec0 inserts.
                with self._conn:
                    for sequence, chunk in enumerate(chunks):
                        chunk.document_id = doc.id
                        chunk.sequence = sequence
                        chunk_repo.create(chunk)
                    searcher.add_embeddings_batch(
                        [
                            (chunk.id, doc.id, chunk.id, vector)
                            for chunk, vector in zip(chunks, vectors, strict=True)
                        ]
                    )
            except Exception as e:
                failed.add(path)
                logger.exception("Embedding failed for %s; re-queued for next burst", path)
                self._notify(on_event, f"error Embedding failed for {path}: {e}")
        if failed:
            self._pending_retry[collection.id] = failed

    def _schema_embedding_dim(self) -> int | None:
        """Declared FLOAT[n] of the vec0 table, or None when absent/unparsed."""
        row = self._conn.execute(
            "SELECT sql FROM sqlite_master WHERE type='table' AND name='document_embeddings'"
        ).fetchone()
        if not row or not row[0]:
            return None
        match = re.search(r"FLOAT\[(\d+)\]", row[0])
        return int(match.group(1)) if match else None

    @staticmethod
    def _notify(on_event: Callable[[str], None] | None, event: str) -> None:
        """Forward an event to the host's presentation callback, if any."""
        if on_event is not None:
            on_event(event)


class FileWatcher:
    """Owns the observer/debouncer/worker pipeline for a set of collections.

    One worker thread performs all database access (sqlite connections must
    not cross threads mid-transaction) and wraps each settled burst in the
    per-DB flock — acquired per burst, never held for the process lifetime
    (D-04). At embed depth the same lock window also spans the inline
    chunk+embed leg (D-09); the core ``IncrementalIndexer`` stays BM25-only.
    """

    def __init__(
        self,
        collections: list[Collection],
        conn: sqlite3.Connection,
        db_path: Path,
        config: WatchConfig | None = None,
    ) -> None:
        """Initialize the pipeline; nothing starts until :meth:`start`.

        Args:
            collections: Registered collections to watch (D-01).
            conn: Factory connection shared by every indexer run.
            db_path: Database path used to derive the per-DB lock file.
            config: Tunables and host callbacks.
        """
        self._collections = list(collections)
        self._conn = conn
        self._db_path = Path(db_path)
        self._config = config if config is not None else WatchConfig()
        self._observer: BaseObserver | None = None
        self._watch_states: dict[str, _WatchState] = {}
        self._rescope_deadline: float | None = None
        self._checkpoint_deadline: float | None = None
        self._last_job_at: float | None = None
        self._queue: queue.Queue[tuple[Collection, FoldResult] | None] = queue.Queue()
        self._worker: threading.Thread | None = None
        self._stop_event = threading.Event()
        self._doc_repo = DocumentRepository(conn)
        self._embed = _EmbedSession(conn)

    def start(self) -> None:
        """Arm the observer, per-collection debouncers, and the worker thread."""
        observer = Observer()
        for coll in self._collections:
            root = Path(coll.path).resolve()
            state = _WatchState(collection=coll, root=root)
            self._watch_states[coll.name] = state
            if not root.exists():
                logger.warning(
                    "Collection root %s missing; not scheduling a watch (D-11)",
                    root,
                )
                # Missing from the start: still tracked so the D-12 re-stat
                # loop picks the root up when it appears.
                state.missing = True
                continue
            if not self._schedule_watch(state, observer):
                # D-17: the schedule itself failed (e.g. inotify
                # exhaustion) — treat like a missing root so the D-12 loop
                # retries without warning spam.
                state.missing = True

        self._observer = observer
        observer.start()
        self._worker = threading.Thread(
            target=self._worker_loop, name="sif-watch-worker", daemon=True
        )
        self._worker.start()

    def _schedule_watch(self, state: _WatchState, observer: BaseObserver) -> bool:
        """Arm one collection's debouncer and recursive watch on its resolved root.

        Returns False — leaving the state retryable and its debouncer
        unstarted — when ``observer.schedule`` raises OSError (the
        inotify-exhaustion / ENOSPC class, D-17): one warning per failure
        episode carries the cause and remedy, other roots keep watching, and
        the caller treats the failure like a missing root so the D-12 loop
        keeps retrying.
        """
        # Positional args (D-05): the first kwarg name differs across
        # watchdog 4.x-7.x; positionally identical on all of them. The
        # upstream annotation says int but the value only flows into
        # Condition.wait(timeout=...), which takes floats (verified
        # against the installed 6.0.0 source) — hence the cast.
        debouncer = EventDebouncer(
            cast(int, self._config.debounce_interval), self._settled_callback(state.collection)
        )
        try:
            state.handle = observer.schedule(
                IndexingEventHandler(debouncer), str(state.root), recursive=True
            )
        except OSError as e:
            if not state.schedule_warned:
                state.schedule_warned = True
                logger.warning(
                    "Scheduling watch for root %s (collection %s) failed: [%s] %s — "
                    "other roots keep watching; the root stays tracked for retry. "
                    "Remedy: %s",
                    state.root,
                    state.collection.name,
                    e.errno,
                    e.strerror or e,
                    _INOTIFY_REMEDY,
                )
            return False
        state.schedule_warned = False
        state.debouncer = debouncer
        debouncer.start()
        return True

    @staticmethod
    def _unschedule_quietly(observer: BaseObserver, handle: ObservedWatch) -> None:
        """Unschedule one watch, tolerating a registry already cleared by stop().

        ``BaseObserver.unschedule`` indexes its watch->emitter map directly
        and raises ``KeyError`` when ``observer.stop()`` (which synchronously
        unschedules everything) cleared the registration while a tick was
        already in flight — the worker checks the stop flag only at the loop
        top. The watch is already gone, so the miss is a no-op for THIS root,
        never a tick failure that would skip the tick's remaining roots.
        """
        with contextlib.suppress(KeyError):
            observer.unschedule(handle)

    def stop(self, *, flush: bool = True) -> None:
        """Stop intake, drain queued work once (bounded), and join threads.

        Args:
            flush: When True, run every job already queued at stop time.
        """
        logger.info("Stopping file watcher (flush=%s)", flush)
        # Quiesce the worker BEFORE touching worker-owned state (Pitfall 6):
        # rescope/recovery_tick run on the worker thread and mutate
        # ``_watch_states`` and the observer, so stopping the observer or
        # iterating the states first races a tick in flight — a rescope
        # del/insert mid-iteration raises RuntimeError out of stop() into
        # the host's shutdown path, and observer.stop() clearing the
        # registry is the KeyError trigger the unschedule sites tolerate.
        self._stop_event.set()
        # Wake a worker parked on its re-stat-timeout idle wait so the join
        # below never waits out the interval (D-14 bounded stop).
        self._queue.put(_WORKER_STOP_SENTINEL)
        # The worker exits on the stop flag; queued work is then drained on
        # this thread so no two threads ever share the connection mid-job.
        # A timed-out join means a job legitimately still runs (flock wait up
        # to lock_timeout, first-use model load) — the flush is then skipped
        # rather than racing the live worker on the same connection (CR-01).
        if self._worker is not None:
            self._worker.join(timeout=_WORKER_JOIN_TIMEOUT_SECONDS)
            if flush and self._worker.is_alive():
                logger.warning(
                    "watch worker still busy after %.1fs; skipping bounded flush "
                    "(jobs stay queued)",
                    _WORKER_JOIN_TIMEOUT_SECONDS,
                )
                flush = False
        # The worker is quiet now (or, on a timed-out join, past the stop
        # signal): stop intake from a state no tick is iterating. The
        # snapshot also covers the timed-out case — a late worker mutation
        # then leaves a just-armed debouncer to process exit rather than
        # raising "dictionary changed size during iteration" here.
        if self._observer is not None:
            self._observer.stop()
        for state in list(self._watch_states.values()):
            if state.debouncer is not None:
                state.debouncer.stop()
        if flush:
            self._drain_once()
        if self._observer is not None:
            self._observer.join(timeout=_JOIN_TIMEOUT_SECONDS)
        for state in list(self._watch_states.values()):
            if state.debouncer is not None:
                state.debouncer.join(timeout=_JOIN_TIMEOUT_SECONDS)

    def worker_joined(self) -> bool:
        """Whether the worker thread is gone, so its connection is free to use.

        The WR-01 gate for same-connection host work (the shutdown WAL
        checkpoint): True when no worker was ever started or the thread has
        exited — including the bounded join inside :meth:`stop` succeeding —
        and False while it still runs (a timed-out join means a job
        legitimately outlasted the stop deadline). Checked live rather than
        recorded at stop time so a worker that exits late still reports True.
        """
        worker = self._worker
        return worker is None or not worker.is_alive()

    def recovery_tick(self) -> None:
        """Run one D-12 re-stat pass over tracked roots.

        Called by the worker whenever its idle wait times out (the re-stat
        cadence), or directly from tests with zero timing. A root that
        disappeared is marked missing — one warning per transition, its
        watch handle unscheduled and its debouncer stopped and joined
        (WR-02: a leaked live debouncer thread per disappear/return cycle,
        since the return arms a fresh one), its documents never touched. A
        root that returned is rescheduled and gets one full-reconcile job
        enqueued.
        """
        observer = self._observer
        if observer is None:
            return
        for state in self._watch_states.values():
            exists = state.root.exists()
            if not exists and not state.missing:
                logger.warning(
                    "Watched root %s (collection %s) disappeared — documents preserved",
                    state.root,
                    state.collection.name,
                )
                if state.handle is not None:
                    self._unschedule_quietly(observer, state.handle)
                    state.handle = None
                if state.debouncer is not None:
                    # The watch handle is gone, so no further events can
                    # arrive: stop the debouncer now — the return branch arms
                    # a fresh one, and an unstopped old one is a leaked live
                    # thread per cycle (WR-02, _unschedule_removed parity).
                    state.debouncer.stop()
                    state.debouncer.join(timeout=_JOIN_TIMEOUT_SECONDS)
                    state.debouncer = None
                state.missing = True
            elif exists and state.missing:
                if self._schedule_watch(state, observer):
                    # Only a successful (re)schedule clears missing and
                    # enqueues the reconcile — a failed schedule keeps the
                    # retry coming without repeating the transition warning.
                    logger.warning(
                        "Watched root %s (collection %s) returned — "
                        "rescheduling watch and reconciling",
                        state.root,
                        state.collection.name,
                    )
                    state.missing = False
                    self._queue.put((state.collection, FoldResult(needs_reconcile=True)))

    def rescope(self, collections: list[Collection]) -> None:
        """Diff the eligible collection set against the watched set (D-15).

        Worker-thread-only, like :meth:`recovery_tick`: the only production
        caller is the tick in :meth:`_on_tick`, and tests invoke it directly
        with the worker quiesced — mutating ``_watch_states`` or the observer
        from any other thread races the tick's own iteration (Pitfall 6). The
        diff is exact: only collections present in ``collections`` end up
        watched, so a host's provider embodies its eligible set (a ``-c``
        filter simply withholds the excluded names).

        Added collections get their debouncer armed and, when the root
        exists, one full-reconcile job enqueued — the exact recovery-return
        shape; a missing root is marked for the D-12 re-stat loop instead.
        Removed collections are unscheduled and their debouncers stopped;
        documents are never touched (stopping watching never deletes).
        """
        observer = self._observer
        if observer is None:
            return
        wanted = {coll.name: coll for coll in collections}
        self._unschedule_removed(wanted, observer)
        self._schedule_added(wanted, observer)

    def _unschedule_removed(self, wanted: dict[str, Collection], observer: BaseObserver) -> None:
        """Tear down watches for collections absent from the eligible set.

        Documents are never touched — stopping watching never deletes.
        """
        for name, state in list(self._watch_states.items()):
            if name in wanted:
                continue
            if state.handle is not None:
                self._unschedule_quietly(observer, state.handle)
                state.handle = None
            if state.debouncer is not None:
                state.debouncer.stop()
                state.debouncer.join(timeout=_JOIN_TIMEOUT_SECONDS)
                state.debouncer = None
            del self._watch_states[name]
            logger.info("Unscheduled watch for collection %s (documents preserved)", name)

    def _schedule_added(self, wanted: dict[str, Collection], observer: BaseObserver) -> None:
        """Arm watches (and one reconcile job) for newly eligible collections.

        A missing root or a failed schedule (D-17) keeps the state tracked
        with ``missing`` set, so the D-12 loop adopts or retries it; only a
        root that is actually being watched gets the reconcile job.
        """
        for name, coll in wanted.items():
            if name in self._watch_states:
                continue
            root = Path(coll.path).resolve()
            state = _WatchState(collection=coll, root=root)
            self._watch_states[name] = state
            if not root.exists():
                logger.warning(
                    "Collection root %s missing; not scheduling a watch (D-11)",
                    root,
                )
                state.missing = True
                continue
            if self._schedule_watch(state, observer):
                self._queue.put((coll, FoldResult(needs_reconcile=True)))
            else:
                state.missing = True

    def _on_tick(self) -> None:
        """Run one idle-tick body: the D-12 recovery pass, then due opt-ins.

        Called by the worker whenever its idle wait times out, or directly
        from tests with zero timing. Rescope (D-15) and the idle WAL
        checkpoint (D-16) ride the same tick behind their interval guards,
        so a default-configured watcher performs no extra work. Everything
        here runs on the worker thread only.
        """
        self.recovery_tick()
        now = self._config.now()
        self._rescope_if_due(now)
        self._checkpoint_if_due(now)

    def _rescope_if_due(self, now: float) -> None:
        """Consult the rescope provider once its interval has elapsed (D-15).

        The deadline seeds on the first tick (one full interval of grace) and
        resets whether or not the provider run changes anything, keeping the
        cadence fixed even across provider failures.
        """
        provider = self._config.rescope_provider
        if provider is None or self._config.rescope_interval <= 0:
            return
        if self._rescope_deadline is None:
            self._rescope_deadline = now + self._config.rescope_interval
            return
        if now < self._rescope_deadline:
            return
        self._rescope_deadline = now + self._config.rescope_interval
        try:
            wanted = provider()
        except Exception:
            logger.warning("Rescope provider failed; keeping the current watch set", exc_info=True)
            return
        self.rescope(wanted)

    def _checkpoint_if_due(self, now: float) -> None:
        """Run the idle WAL checkpoint when its interval has elapsed (D-16).

        Disabled unless ``checkpoint_interval > 0`` — a default-configured
        watcher performs zero work here, and shutdown checkpointing (12-D14)
        stays the final word. The deadline resets whether or not the
        checkpoint ran: busy and recent-burst skips postpone to the next
        interval rather than retrying inside the tick.
        """
        if self._config.checkpoint_interval <= 0:
            return
        if self._checkpoint_deadline is None:
            self._checkpoint_deadline = now + self._config.checkpoint_interval
            return
        if now < self._checkpoint_deadline:
            return
        self._checkpoint_deadline = now + self._config.checkpoint_interval
        self._checkpoint_if_idle(now)

    def _checkpoint_if_idle(self, now: float) -> None:
        """One TRUNCATE checkpoint on the worker's own connection, if idle.

        A job that completed within the re-stat window means the writer was
        recently active — not idle — so the checkpoint waits a full interval.
        A busy result row means another connection holds the WAL: skip
        silently, never log per tick (Pitfall 7).
        """
        last_job = self._last_job_at
        if last_job is not None and (now - last_job) < self._config.restat_interval:
            return
        try:
            row = self._conn.execute(_WAL_CHECKPOINT_TRUNCATE).fetchone()
        except sqlite3.Error as e:
            logger.warning("Idle WAL checkpoint failed: %s", e)
            return
        if row is not None and row[0]:
            return

    def _settled_callback(self, collection: Collection) -> SettledCallback:
        """Build the debouncer callback for one collection.

        The callback executes while holding the debouncer's condition lock,
        so it only folds and enqueues (Pitfall 3); the worker thread owns
        every database access.
        """
        scanner = FileScanner()
        root = Path(collection.path).resolve()
        should_track = partial(
            scanner.matches,
            root,
            pattern=collection.pattern,
            ignore_patterns=collection.ignore_patterns,
        )

        def _on_settled(events: list[FileSystemEvent]) -> None:
            self._queue.put((collection, fold_events(events, should_track)))

        return _on_settled

    def _worker_loop(self) -> None:
        """Consume settled bursts until stopped; one job per queue item.

        The idle wait doubles as the periodic tick: when no burst arrives
        within the re-stat interval, :meth:`_on_tick` runs the D-12 recovery
        pass plus the due long-lived-host behaviors (rescope, checkpoint).
        """
        while not self._stop_event.is_set():
            try:
                job = self._queue.get(timeout=self._config.restat_interval)
            except queue.Empty:
                try:
                    self._on_tick()
                except Exception:
                    # One tick failure must never kill the worker thread: the
                    # host banner still says "Watching" while nothing consumes
                    # the queue — log and keep the next interval coming.
                    logger.exception("watch tick failed; continuing next interval")
                continue
            if job is None:
                # stop() sentinel: wake immediately instead of parking for
                # the rest of the re-stat interval; nothing follows it.
                self._queue.task_done()
                break
            try:
                self._run_job(job)
            except Exception:
                logger.exception("watch job failed for %s", job[0].name)
            finally:
                self._queue.task_done()

    def _run_job(self, job: tuple[Collection, FoldResult]) -> None:
        """Process one settled burst under the per-DB flock (D-04 per-burst).

        Cost is proportional to the burst: per-path processing, or one full
        collection pass only when a directory move (or a returning missing
        root) requires a reconcile. At embed depth the embed leg runs inside
        the SAME lock window as the BM25 leg (D-09).
        """
        collection, folded = job
        paths = folded.index_candidates | folded.remove_candidates
        if folded.needs_reconcile:
            result = self._run_reconcile(collection)
        elif paths:
            with index_lock(self._db_path, self._config.lock_timeout):
                result = self._run_burst(collection, folded)
        else:
            # An empty fold (pure temp-noise burst) never touches the DB.
            return
        # Completed worker activity: the D-16 idle checkpoint treats any job
        # inside the recent window as "not idle" (burst postponement).
        self._last_job_at = self._config.now()
        if self._config.on_batch is not None:
            self._config.on_batch(collection, result)

    def _run_reconcile(self, collection: Collection) -> IncrementalResult:
        """One full-collection BM25 pass (directory move, returning root).

        The core pass stays BM25-only, but its update branch purges chunks
        and embeddings for every changed document. At embed depth that
        purge must not strand those documents vector-less (IN-04): the
        changed set — computable as a checksum diff around the pass — is
        fed through the embed leg in the SAME lock window (D-09), because
        the burst change detector alone would never re-select paths whose
        fresh checksums the reconcile just committed.
        """
        with index_lock(self._db_path, self._config.lock_timeout):
            before = (
                self._collection_checksums(collection) if self._config.depth == "embed" else None
            )
            result = IncrementalIndexer(self._conn).update_collection(
                collection, progress=self._config.on_event
            )
            if before is not None:
                changed = self._changed_since(collection, before)
                if changed:
                    self._embed.embed_documents(collection, changed, self._config.on_event)
            return result

    def _run_burst(self, collection: Collection, folded: FoldResult) -> IncrementalResult:
        """BM25 leg first, then the inline embed leg for changed paths (D-09)."""
        paths = folded.index_candidates | folded.remove_candidates
        indexer = IncrementalIndexer(self._conn)
        progress = self._config.on_event
        if self._config.depth != "embed":
            return indexer.update_paths(collection, paths, progress=progress)
        before = self._checksums(collection, folded.index_candidates)
        result = indexer.update_paths(collection, paths, progress=progress)
        changed = {
            path for path in folded.index_candidates if self._path_changed(collection, path, before)
        }
        self._embed.embed_documents(collection, changed, progress)
        return result

    def _checksums(self, collection: Collection, paths: Iterable[Path]) -> dict[str, str | None]:
        """Snapshot stored checksums for the index candidates (change detection)."""
        snapshots: dict[str, str | None] = {}
        for path in paths:
            doc = self._doc_repo.get_by_path(str(path), collection.id)
            snapshots[str(path)] = doc.checksum if doc else None
        return snapshots

    def _collection_checksums(self, collection: Collection) -> dict[str, str | None]:
        """Snapshot {path: checksum} for every stored document in the collection."""
        return {doc.path: doc.checksum for doc in self._doc_repo.list_by_collection(collection.id)}

    def _changed_since(self, collection: Collection, before: dict[str, str | None]) -> set[Path]:
        """Paths whose stored checksum appeared or changed since ``before``."""
        return {
            Path(doc.path)
            for doc in self._doc_repo.list_by_collection(collection.id)
            if doc.checksum != before.get(doc.path)
        }

    def _path_changed(
        self, collection: Collection, path: Path, before: dict[str, str | None]
    ) -> bool:
        """True when the BM25 leg added or updated this path's document."""
        doc = self._doc_repo.get_by_path(str(path), collection.id)
        return doc is not None and doc.checksum != before.get(str(path))

    def _drain_once(self) -> None:
        """Run every job already queued at call time (bounded, no waiting)."""
        while True:
            try:
                job = self._queue.get_nowait()
            except queue.Empty:
                return
            try:
                if job is not None:
                    self._run_job(job)
            except Exception:
                logger.exception("watch flush job failed for %s", job[0].name)
            finally:
                self._queue.task_done()
