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

import os
import queue
import re
import sqlite3
import threading
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
        self._debouncers: list[EventDebouncer] = []
        self._watch_states: dict[str, _WatchState] = {}
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
        # A timed-out join means a job legitimately still runs (flock wait up
        # to lock_timeout, first-use model load) — the flush is then skipped
        # rather than racing the live worker on the same connection (CR-01).
        self._stop_event.set()
        # Wake a worker parked on its re-stat-timeout idle wait so the join
        # below never waits out the interval (D-14 bounded stop).
        self._queue.put(_WORKER_STOP_SENTINEL)
        if self._worker is not None:
            self._worker.join(timeout=_WORKER_JOIN_TIMEOUT_SECONDS)
            if flush and self._worker.is_alive():
                logger.warning(
                    "watch worker still busy after %.1fs; skipping bounded flush "
                    "(jobs stay queued)",
                    _WORKER_JOIN_TIMEOUT_SECONDS,
                )
                flush = False
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
