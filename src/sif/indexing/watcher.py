"""Host-agnostic filesystem-watch pipeline for live indexing (Phase 12).

observer -> IndexingEventHandler -> EventDebouncer -> fold_events -> queue ->
single worker thread -> per-burst index_lock -> IncrementalIndexer. The
module owns no presentation: hosts pass ``on_event``/``on_batch`` callbacks
and render themselves (D-13). Signal handling and WAL checkpointing stay in
the CLI host (plan 12-02 owns the full D-14 machinery).
"""

from __future__ import annotations

import os
import queue
import sqlite3
import threading
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from pathlib import Path

from watchdog.events import FileSystemEvent, FileSystemEventHandler
from watchdog.observers.api import BaseObserver
from watchdog.utils.event_debouncer import EventDebouncer

from sif.core.models import Collection
from sif.indexing.incremental import IncrementalResult
from sif.utils.logging import get_logger


logger = get_logger(__name__)


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
    gate; Phase 12-02 flags extend this struct without touching call sites.
    """

    debounce_interval: float = 0.5
    lock_timeout: float = 30.0
    depth: str = "bm25"
    on_event: Callable[[str], None] | None = None
    on_batch: Callable[[Collection, IncrementalResult], None] | None = None


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
    predicate-checked via ``should_track``; a path both touched and deleted in
    one burst stays an index candidate only — update_paths stats it and disk
    state decides. The fold is order-independent by construction.

    Args:
        events: Settled batch from the EventDebouncer callback.
        should_track: The collection's shared scanner predicate.

    Returns:
        The folded candidate sets and reconcile flag.
    """
    _ = (events, should_track)
    return FoldResult()


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
        self._queue: queue.Queue[tuple[Collection, FoldResult]] = queue.Queue()
        self._worker: threading.Thread | None = None
        self._stop_event = threading.Event()

    def start(self) -> None:
        """Arm the observer, per-collection debouncers, and the worker thread."""
        logger.info("Starting file watcher over %d collection(s)", len(self._collections))

    def stop(self, *, flush: bool = True) -> None:
        """Stop intake, drain queued work once (bounded), and join threads.

        Args:
            flush: When True, run every job already queued at stop time.
        """
        logger.info("Stopping file watcher (flush=%s)", flush)
