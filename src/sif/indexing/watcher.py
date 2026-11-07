"""Host-agnostic filesystem-watch pipeline for live indexing (Phase 12).

observer -> IndexingEventHandler -> EventDebouncer -> fold_events -> queue ->
single worker thread -> per-burst index_lock -> IncrementalIndexer. The
module owns no presentation: hosts pass ``on_event``/``on_batch`` callbacks
and render themselves (D-13). Signal handling and the WAL checkpoint stay
in the CLI host (D-14); the worker's idle wait doubles as the D-12
missing-root re-stat loop.
"""

from __future__ import annotations

import os
import queue
import sqlite3
import threading
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from functools import partial
from pathlib import Path
from typing import cast

from watchdog.events import FileSystemEvent, FileSystemEventHandler
from watchdog.observers import Observer
from watchdog.observers.api import BaseObserver, ObservedWatch
from watchdog.utils.event_debouncer import EventDebouncer

from sif.core.models import Collection
from sif.database.locking import index_lock
from sif.indexing.incremental import IncrementalIndexer, IncrementalResult
from sif.indexing.scanner import FileScanner
from sif.utils.logging import get_logger


logger = get_logger(__name__)

_JOIN_TIMEOUT_SECONDS = 5.0
_WORKER_JOIN_TIMEOUT_SECONDS = 10.0

SettledCallback = Callable[[list[FileSystemEvent]], None]

# Wakes a worker parked on its re-stat-timeout idle wait so shutdown never
# waits out the interval; nothing is enqueued after it (D-14 bounded stop).
_WORKER_STOP_SENTINEL = None


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
    gate; host flags extend this struct without touching call sites.
    """

    debounce_interval: float = 0.5
    lock_timeout: float = 30.0
    depth: str = "bm25"
    restat_interval: float = 5.0
    on_event: Callable[[str], None] | None = None
    on_batch: Callable[[Collection, IncrementalResult], None] | None = None


@dataclass
class _WatchState:
    """Per-collection watch lifecycle state for the D-12 recovery loop."""

    collection: Collection
    root: Path
    handle: ObservedWatch | None = None
    missing: bool = False


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


class FileWatcher:
    """Owns the observer/debouncer/worker pipeline for a set of collections.

    One worker thread performs all database access (sqlite connections must
    not cross threads mid-transaction) and wraps each settled burst in the
    per-DB flock — acquired per burst, never held for the process lifetime
    (D-04).
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
        self._debouncers: list[EventDebouncer] = []
        self._watch_states: dict[str, _WatchState] = {}
        self._queue: queue.Queue[tuple[Collection, FoldResult] | None] = queue.Queue()
        self._worker: threading.Thread | None = None
        self._stop_event = threading.Event()

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
            self._schedule_watch(state, observer)

        self._observer = observer
        observer.start()
        self._worker = threading.Thread(
            target=self._worker_loop, name="sif-watch-worker", daemon=True
        )
        self._worker.start()

    def _schedule_watch(self, state: _WatchState, observer: BaseObserver) -> None:
        """Arm one collection's debouncer and recursive watch on its resolved root."""
        # Positional args (D-05): the first kwarg name differs across
        # watchdog 4.x-7.x; positionally identical on all of them. The
        # upstream annotation says int but the value only flows into
        # Condition.wait(timeout=...), which takes floats (verified
        # against the installed 6.0.0 source) — hence the cast.
        debouncer = EventDebouncer(
            cast(int, self._config.debounce_interval), self._settled_callback(state.collection)
        )
        state.handle = observer.schedule(
            IndexingEventHandler(debouncer), str(state.root), recursive=True
        )
        self._debouncers.append(debouncer)
        debouncer.start()

    def stop(self, *, flush: bool = True) -> None:
        """Stop intake, drain queued work once (bounded), and join threads.

        Args:
            flush: When True, run every job already queued at stop time.
        """
        logger.info("Stopping file watcher (flush=%s)", flush)
        if self._observer is not None:
            self._observer.stop()
        for debouncer in self._debouncers:
            debouncer.stop()
        # The worker exits on the stop flag; queued work is then drained on
        # this thread so no two threads ever share the connection mid-job.
        self._stop_event.set()
        # Wake a worker parked on its re-stat-timeout idle wait so the join
        # below never waits out the interval (D-14 bounded stop).
        self._queue.put(_WORKER_STOP_SENTINEL)
        if self._worker is not None:
            self._worker.join(timeout=_WORKER_JOIN_TIMEOUT_SECONDS)
        if flush:
            self._drain_once()
        if self._observer is not None:
            self._observer.join(timeout=_JOIN_TIMEOUT_SECONDS)
        for debouncer in self._debouncers:
            debouncer.join(timeout=_JOIN_TIMEOUT_SECONDS)

    def recovery_tick(self) -> None:
        """Run one D-12 re-stat pass over tracked roots.

        Called by the worker whenever its idle wait times out (the re-stat
        cadence), or directly from tests with zero timing. A root that
        disappeared is marked missing — one warning per transition, its
        watch handle unscheduled, its documents never touched. A root that
        returned is rescheduled and gets one full-reconcile job enqueued.
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
                    observer.unschedule(state.handle)
                    state.handle = None
                state.missing = True
            elif exists and state.missing:
                logger.warning(
                    "Watched root %s (collection %s) returned — rescheduling watch and reconciling",
                    state.root,
                    state.collection.name,
                )
                self._schedule_watch(state, observer)
                state.missing = False
                self._queue.put((state.collection, FoldResult(needs_reconcile=True)))

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

        The idle wait doubles as the D-12 re-stat cadence: when no burst
        arrives within the re-stat interval, one recovery tick runs.
        """
        while not self._stop_event.is_set():
            try:
                job = self._queue.get(timeout=self._config.restat_interval)
            except queue.Empty:
                self.recovery_tick()
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
        collection pass only when a directory move requires a reconcile.
        """
        collection, folded = job
        paths = folded.index_candidates | folded.remove_candidates
        if folded.needs_reconcile:
            with index_lock(self._db_path, self._config.lock_timeout):
                result = IncrementalIndexer(self._conn).update_collection(
                    collection, progress=self._config.on_event
                )
        elif paths:
            with index_lock(self._db_path, self._config.lock_timeout):
                result = IncrementalIndexer(self._conn).update_paths(
                    collection, paths, progress=self._config.on_event
                )
        else:
            # An empty fold (pure temp-noise burst) never touches the DB.
            return
        if self._config.on_batch is not None:
            self._config.on_batch(collection, result)

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
