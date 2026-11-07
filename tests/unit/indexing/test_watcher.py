"""Fold semantics and per-path update proofs for the Phase 12 watch pipeline.

Synthetic-event, zero-timing culture (D-15): watchdog event objects are
constructed positionally and driven directly into ``fold_events`` /
``update_paths`` — no observer threads, no sleeps. The real-observer
end-to-end proof lives in ``tests/integration/test_watch_e2e.py``.
"""

from __future__ import annotations

import logging
import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import MagicMock, patch

from watchdog.events import (
    DirCreatedEvent,
    DirDeletedEvent,
    DirModifiedEvent,
    DirMovedEvent,
    FileCreatedEvent,
    FileDeletedEvent,
    FileModifiedEvent,
    FileMovedEvent,
)

from sif.config.settings import Settings
from sif.core.models import Collection
from sif.database.database import Database
from sif.database.repositories import DocumentChunkRepository, DocumentRepository
from sif.indexing import watcher as watcher_module
from sif.indexing.incremental import IncrementalIndexer, IncrementalResult
from sif.indexing.scanner import FileScanner
from sif.indexing.watcher import FileWatcher, FoldResult, WatchConfig, fold_events


BODY_ALPHA = "# Heading One\n\n" + ("Alpha paragraph text. " * 50)
BODY_BETA = "# Heading Two\n\n" + ("Beta paragraph text. " * 50)


def _delenv_settings_vars(monkeypatch) -> None:
    """Keep Settings construction hermetic against a developer shell."""
    for var in ("SIF_EMBEDDING_DIM", "SIF_MODEL_TYPE", "SIF_MODEL_NAME"):
        monkeypatch.delenv(var, raising=False)


def _test_settings() -> Settings:
    """Build hermetic test settings."""
    return Settings(embedding_dim=8, model_name="test", cache_embeddings=False)


def _seed_collection(db_path: Path, notes: Path) -> str:
    """Init schema and create one collection pointing at ``notes``; return its id."""
    db = Database(db_path)
    with patch("sif.config.settings.get_settings", return_value=_test_settings()):
        db.init_schema()
        with db.connection:
            from sif.database.repositories import CollectionRepository

            coll_repo = CollectionRepository(db.connection)
            coll = Collection(name="notes", path=str(notes))
            coll_repo.create(coll)
            coll_id = coll.id
    db.close()
    return coll_id


def _open_indexer(db_path: Path) -> tuple[IncrementalIndexer, Database, Collection]:
    """Open the DB, load the seeded collection, and build an indexer."""
    db = Database(db_path)
    from sif.database.repositories import CollectionRepository

    coll_repo = CollectionRepository(db.connection)
    coll = coll_repo.get_by_name("notes")
    assert coll is not None
    return IncrementalIndexer(db.connection), db, coll


def _doc_paths(db_path: Path) -> set[str]:
    """Read document paths through a fresh connection (query, not files)."""
    conn = sqlite3.connect(str(db_path))
    try:
        return {row[0] for row in conn.execute("SELECT path FROM documents")}
    finally:
        conn.close()


def _should_track(root: Path, path: Path) -> bool:
    """The collection's shared scanner predicate (D-07)."""
    return FileScanner.matches(root, path, pattern="**/*.md")


class TestFoldEvents:
    """Folding a settled burst into candidate path sets (D-06/D-07/D-08)."""

    def test_temp_noise_dropped_and_real_md_kept(self, tmp_path: Path) -> None:
        """Editor-noise paths never become candidates; real .md paths do."""
        root = tmp_path / "notes"
        real = root / "note.md"
        noise = [
            root / "note.md.sb-ABCD1234",
            root / ".swp.tmp",
            root / "4913",
            root / ".#b.md",
            root / "c.tmp",
            root / "d.swp",
            root / ".DS_Store",
        ]
        events = [FileCreatedEvent(str(p)) for p in [real, *noise]]

        folded = fold_events(events, should_track=lambda p: _should_track(root, p))

        assert folded.index_candidates == {real.resolve()}
        assert folded.remove_candidates == set()
        assert folded.needs_reconcile is False

    def test_atomic_save_chain_folds_to_final_path_only(self, tmp_path: Path) -> None:
        """The probe's 5-event macOS atomic-save chain yields exactly the final path.

        Includes the trailing ``deleted`` on the final path after ``moved`` —
        the trailing delete must NOT turn the burst into a removal (D-06:
        disk is truth; the index candidate's stat decides).
        """
        root = tmp_path / "notes"
        final = root / "file.md"
        temp = root / "file.md.sb-ABCD1234"
        burst = [
            FileCreatedEvent(str(temp)),
            FileModifiedEvent(str(temp)),
            FileMovedEvent(str(temp), str(final)),
            FileModifiedEvent(str(final)),
            FileDeletedEvent(str(final)),
        ]

        folded = fold_events(burst, should_track=lambda p: _should_track(root, p))

        assert folded.index_candidates == {final.resolve()}
        assert folded.remove_candidates == set()
        assert folded.needs_reconcile is False

    def test_moved_event_contributes_dest_index_src_remove(self, tmp_path: Path) -> None:
        """A moved event indexes the dest and removes the src (D-07 dest rule)."""
        root = tmp_path / "notes"
        src = root / "old.md"
        dest = root / "new.md"

        folded = fold_events(
            [FileMovedEvent(str(src), str(dest))],
            should_track=lambda p: _should_track(root, p),
        )

        assert folded.index_candidates == {dest.resolve()}
        assert folded.remove_candidates == {src.resolve()}

    def test_directory_events_ignored_and_dir_moved_flags_reconcile(self, tmp_path: Path) -> None:
        """Dir created/modified/deleted are ignored; dir moved needs a reconcile."""
        root = tmp_path / "notes"
        sub = root / "sub"

        plain = fold_events(
            [
                DirCreatedEvent(str(sub)),
                DirModifiedEvent(str(sub)),
                DirDeletedEvent(str(sub)),
            ],
            should_track=lambda p: _should_track(root, p),
        )
        assert plain == FoldResult()

        moved = fold_events(
            [DirMovedEvent(str(sub), str(root / "renamed"))],
            should_track=lambda p: _should_track(root, p),
        )
        assert moved.needs_reconcile is True
        assert moved.index_candidates == set()
        assert moved.remove_candidates == set()

    def test_fold_is_order_independent(self, tmp_path: Path) -> None:
        """A burst and its reverse fold to identical candidate sets (edge: ordering)."""
        root = tmp_path / "notes"
        final = root / "file.md"
        temp = root / "file.md.sb-ABCD1234"
        other = root / "other.md"
        burst = [
            FileCreatedEvent(str(temp)),
            FileModifiedEvent(str(temp)),
            FileMovedEvent(str(temp), str(final)),
            FileModifiedEvent(str(final)),
            FileDeletedEvent(str(final)),
            FileDeletedEvent(str(other)),
        ]

        def track(path: Path) -> bool:
            return _should_track(root, path)

        forward = fold_events(burst, should_track=track)
        backward = fold_events(list(reversed(burst)), should_track=track)

        assert forward == backward


class TestUpdatePaths:
    """The per-path targeted update API (D-06/D-10/D-11), real DB culture."""

    def test_new_file_added_and_document_row_exists(self, tmp_path, monkeypatch) -> None:
        """A new on-disk path is added: added == 1 and the row is durable."""
        _delenv_settings_vars(monkeypatch)
        db_path = tmp_path / "watch.db"
        notes = tmp_path / "notes"
        notes.mkdir()
        doc_file = notes / "a.md"
        doc_file.write_text(BODY_ALPHA, encoding="utf-8")
        _seed_collection(db_path, notes)

        indexer, db, coll = _open_indexer(db_path)
        try:
            result = indexer.update_paths(coll, [doc_file])
        finally:
            db.close()

        assert result == IncrementalResult(added=1, updated=0, removed=0, unchanged=0)
        assert str(doc_file) in _doc_paths(db_path)

    def test_edited_file_updated_with_fresh_checksum(self, tmp_path, monkeypatch) -> None:
        """A content edit through update_paths reports updated == 1."""
        _delenv_settings_vars(monkeypatch)
        db_path = tmp_path / "watch.db"
        notes = tmp_path / "notes"
        notes.mkdir()
        doc_file = notes / "a.md"
        doc_file.write_text(BODY_ALPHA, encoding="utf-8")
        _seed_collection(db_path, notes)

        indexer, db, coll = _open_indexer(db_path)
        try:
            assert indexer.update_collection(coll) == IncrementalResult(1, 0, 0, 0)
        finally:
            db.close()

        doc_file.write_text(BODY_BETA, encoding="utf-8")
        indexer, db, coll = _open_indexer(db_path)
        try:
            result = indexer.update_paths(coll, [doc_file])
        finally:
            db.close()

        assert result == IncrementalResult(added=0, updated=1, removed=0, unchanged=0)

    def test_deleted_path_removed_with_purge_before_delete(self, tmp_path, monkeypatch) -> None:
        """A vanished path is removed and its embeddings purge BEFORE the row delete (WR-01)."""
        _delenv_settings_vars(monkeypatch)
        db_path = tmp_path / "watch.db"
        notes = tmp_path / "notes"
        notes.mkdir()
        doc_file = notes / "a.md"
        doc_file.write_text(BODY_ALPHA, encoding="utf-8")
        _seed_collection(db_path, notes)

        indexer, db, coll = _open_indexer(db_path)
        try:
            assert indexer.update_collection(coll) == IncrementalResult(1, 0, 0, 0)
        finally:
            db.close()

        doc_file.unlink()

        calls: list[tuple[str, str]] = []
        purger = MagicMock()
        purger.delete_embeddings_by_document.side_effect = lambda doc_id: calls.append(
            ("purge", doc_id)
        )
        original_delete = DocumentRepository.delete

        def recording_delete(self: DocumentRepository, document_id: str) -> bool:
            calls.append(("delete", document_id))
            return original_delete(self, document_id)

        monkeypatch.setattr(DocumentRepository, "delete", recording_delete)

        indexer, db, coll = _open_indexer(db_path)
        try:
            indexer._vector_purger = purger
            result = indexer.update_paths(coll, [doc_file])
        finally:
            db.close()

        assert result == IncrementalResult(added=0, updated=0, removed=1, unchanged=0)
        assert _doc_paths(db_path) == set()
        assert [kind for kind, _ in calls] == ["purge", "delete"]

    def test_missing_root_returns_zero_emits_missing_and_preserves_docs(
        self, tmp_path, monkeypatch
    ) -> None:
        """D-11: a missing collection root never sweeps — both update paths."""
        _delenv_settings_vars(monkeypatch)
        db_path = tmp_path / "watch.db"
        notes = tmp_path / "notes"
        notes.mkdir()
        doc_file = notes / "a.md"
        doc_file.write_text(BODY_ALPHA, encoding="utf-8")
        _seed_collection(db_path, notes)

        indexer, db, coll = _open_indexer(db_path)
        try:
            assert indexer.update_collection(coll) == IncrementalResult(1, 0, 0, 0)
        finally:
            db.close()

        # The collection root disappears (unmounted/renamed drive).
        notes.rename(tmp_path / "notes-gone")

        indexer, db, coll = _open_indexer(db_path)
        try:
            events: list[str] = []
            result = indexer.update_paths(coll, [doc_file], progress=events.append)
            assert result == IncrementalResult(added=0, updated=0, removed=0, unchanged=0)
            assert "missing notes" in events

            events = []
            result = indexer.update_collection(coll, progress=events.append)
            assert result == IncrementalResult(added=0, updated=0, removed=0, unchanged=0)
            assert "missing notes" in events
        finally:
            db.close()

        # Every existing document of that collection survives.
        assert _doc_paths(db_path) == {str(doc_file)}

    def test_unchanged_path_counted_as_unchanged(self, tmp_path, monkeypatch) -> None:
        """A checksum-equal path maps the skip outcome to unchanged += 1."""
        _delenv_settings_vars(monkeypatch)
        db_path = tmp_path / "watch.db"
        notes = tmp_path / "notes"
        notes.mkdir()
        doc_file = notes / "a.md"
        doc_file.write_text(BODY_ALPHA, encoding="utf-8")
        _seed_collection(db_path, notes)

        indexer, db, coll = _open_indexer(db_path)
        try:
            assert indexer.update_collection(coll) == IncrementalResult(1, 0, 0, 0)
            events: list[str] = []
            result = indexer.update_paths(coll, [doc_file], progress=events.append)
        finally:
            db.close()

        assert result == IncrementalResult(added=0, updated=0, removed=0, unchanged=1)
        assert any(e.startswith("unchanged a.md") for e in events)


class TestWatchPipeline:
    """Settled-burst → worker → flock → update_paths, driven synthetically (D-15).

    The settled callback is invoked directly and the queue drained with
    ``_drain_once`` — no observer threads, no timing anywhere.
    """

    def test_save_burst_coalesces_to_one_update_paths_call(self, tmp_path, monkeypatch) -> None:
        """LIVE-02: a 5-event save burst yields exactly one update_paths invocation."""
        _delenv_settings_vars(monkeypatch)
        db_path = tmp_path / "watch.db"
        notes = tmp_path / "notes"
        notes.mkdir()
        (notes / "file.md").write_text(BODY_ALPHA, encoding="utf-8")
        _seed_collection(db_path, notes)

        calls: list[frozenset] = []

        class SpyIndexer:
            """Records update_paths invocations without touching the DB."""

            def __init__(self, conn) -> None:
                self.conn = conn

            def update_paths(self, collection, paths, *, force=False, progress=None):
                _ = (collection, force, progress)
                calls.append(frozenset(paths))
                return IncrementalResult(added=1)

            def update_collection(self, collection, *, force=False, progress=None):
                _ = (collection, force, progress)
                raise AssertionError("burst must not trigger a full reconcile")

        monkeypatch.setattr(watcher_module, "IncrementalIndexer", SpyIndexer)

        db = Database(db_path)
        try:
            from sif.database.repositories import CollectionRepository

            coll = CollectionRepository(db.connection).get_by_name("notes")
            assert coll is not None
            watcher = FileWatcher([coll], db.connection, db_path)
            burst = [
                FileCreatedEvent(str(notes / "file.md")),
                FileModifiedEvent(str(notes / "file.md")),
                FileModifiedEvent(str(notes / "file.md")),
                FileCreatedEvent(str(notes / "file.md")),
                FileModifiedEvent(str(notes / "file.md")),
            ]
            watcher._settled_callback(coll)(burst)
            watcher._drain_once()
        finally:
            db.close()

        assert len(calls) == 1
        assert calls[0] == frozenset({(notes / "file.md").resolve()})
        assert len(calls[0]) == 1

    def test_atomic_save_chain_one_index_op_removed_zero(self, tmp_path, monkeypatch) -> None:
        """LIVE-03: the full probe atomic-save chain indexes once, removes nothing."""
        _delenv_settings_vars(monkeypatch)
        db_path = tmp_path / "watch.db"
        notes = tmp_path / "notes"
        notes.mkdir()
        final = notes / "file.md"
        final.write_text(BODY_ALPHA, encoding="utf-8")
        _seed_collection(db_path, notes)

        indexer, db, coll = _open_indexer(db_path)
        try:
            assert indexer.update_collection(coll) == IncrementalResult(1, 0, 0)
        finally:
            db.close()

        # Real atomic save: new content lands in a .sb- temp, then replaces.
        temp = notes / "file.md.sb-ABCD1234"
        temp.write_text(BODY_BETA, encoding="utf-8")
        os.replace(temp, final)
        burst = [
            FileCreatedEvent(str(temp)),
            FileModifiedEvent(str(temp)),
            FileMovedEvent(str(temp), str(final)),
            FileModifiedEvent(str(final)),
            FileDeletedEvent(str(final)),
        ]

        results: list[IncrementalResult] = []
        db = Database(db_path)
        try:
            from sif.database.repositories import CollectionRepository

            coll = CollectionRepository(db.connection).get_by_name("notes")
            assert coll is not None
            watcher = FileWatcher(
                [coll],
                db.connection,
                db_path,
                WatchConfig(on_batch=lambda _coll, result: results.append(result)),
            )
            watcher._settled_callback(coll)(burst)
            watcher._drain_once()
        finally:
            db.close()

        assert len(results) == 1
        assert results[0].removed == 0
        assert results[0].added + results[0].updated == 1
        conn = sqlite3.connect(str(db_path))
        try:
            row = conn.execute(
                "SELECT content FROM documents WHERE path = ?", (str(final),)
            ).fetchone()
        finally:
            conn.close()
        assert row is not None
        assert "Beta paragraph text" in row[0]

    def test_plain_rename_removes_old_adds_new_only(self, tmp_path, monkeypatch) -> None:
        """LIVE-03: a rename reconciles to removed=1 + added=1, others untouched."""
        _delenv_settings_vars(monkeypatch)
        db_path = tmp_path / "watch.db"
        notes = tmp_path / "notes"
        notes.mkdir()
        old = notes / "old.md"
        other = notes / "other.md"
        old.write_text(BODY_ALPHA, encoding="utf-8")
        other.write_text("# Other\n\n" + ("Other body text. " * 20), encoding="utf-8")
        _seed_collection(db_path, notes)

        indexer, db, coll = _open_indexer(db_path)
        try:
            assert indexer.update_collection(coll) == IncrementalResult(2, 0, 0)
        finally:
            db.close()

        renamed = notes / "renamed.md"
        os.rename(old, renamed)
        burst = [
            FileModifiedEvent(str(old)),
            FileMovedEvent(str(old), str(renamed)),
        ]

        results: list[IncrementalResult] = []
        db = Database(db_path)
        try:
            from sif.database.repositories import CollectionRepository

            coll = CollectionRepository(db.connection).get_by_name("notes")
            assert coll is not None
            watcher = FileWatcher(
                [coll],
                db.connection,
                db_path,
                WatchConfig(on_batch=lambda _coll, result: results.append(result)),
            )
            watcher._settled_callback(coll)(burst)
            watcher._drain_once()
        finally:
            db.close()

        assert len(results) == 1
        assert results[0] == IncrementalResult(added=1, updated=0, removed=1, unchanged=0)
        assert _doc_paths(db_path) == {str(other), str(renamed)}

    def test_empty_fold_never_calls_update_paths_single_event_works(
        self, tmp_path, monkeypatch
    ) -> None:
        """Edge: a pure-noise burst never reaches update_paths; one event does."""
        _delenv_settings_vars(monkeypatch)
        db_path = tmp_path / "watch.db"
        notes = tmp_path / "notes"
        notes.mkdir()
        (notes / "file.md").write_text(BODY_ALPHA, encoding="utf-8")
        _seed_collection(db_path, notes)

        calls: list[frozenset] = []

        class SpyIndexer:
            """Records update_paths invocations without touching the DB."""

            def __init__(self, conn) -> None:
                self.conn = conn

            def update_paths(self, collection, paths, *, force=False, progress=None):
                _ = (collection, force, progress)
                calls.append(frozenset(paths))
                return IncrementalResult()

        monkeypatch.setattr(watcher_module, "IncrementalIndexer", SpyIndexer)

        db = Database(db_path)
        try:
            from sif.database.repositories import CollectionRepository

            coll = CollectionRepository(db.connection).get_by_name("notes")
            assert coll is not None
            watcher = FileWatcher([coll], db.connection, db_path)
            noise_burst = [
                FileCreatedEvent(str(notes / "scratch.tmp")),
                FileDeletedEvent(str(notes / "d.swp")),
            ]
            watcher._settled_callback(coll)(noise_burst)
            watcher._drain_once()
            assert calls == []

            watcher._settled_callback(coll)([FileModifiedEvent(str(notes / "file.md"))])
            watcher._drain_once()
        finally:
            db.close()

        assert len(calls) == 1

    def test_lock_acquired_per_job_never_held_for_lifetime(self, tmp_path, monkeypatch) -> None:
        """Edge/D-04: index_lock enters and exits around EACH job, never the loop."""
        _delenv_settings_vars(monkeypatch)
        db_path = tmp_path / "watch.db"
        notes = tmp_path / "notes"
        notes.mkdir()
        (notes / "file.md").write_text(BODY_ALPHA, encoding="utf-8")
        _seed_collection(db_path, notes)

        lock_events: list[str] = []

        @contextmanager
        def recording_lock(_db_path, _timeout_s, _on_wait=None):
            lock_events.append("enter")
            try:
                yield
            finally:
                lock_events.append("exit")

        monkeypatch.setattr(watcher_module, "index_lock", recording_lock)

        class SpyIndexer:
            """No-op indexer; the lock shape is what this test observes."""

            def __init__(self, conn) -> None:
                self.conn = conn

            def update_paths(self, collection, paths, *, force=False, progress=None):
                _ = (collection, paths, force, progress)
                return IncrementalResult()

        monkeypatch.setattr(watcher_module, "IncrementalIndexer", SpyIndexer)

        db = Database(db_path)
        try:
            from sif.database.repositories import CollectionRepository

            coll = CollectionRepository(db.connection).get_by_name("notes")
            assert coll is not None
            watcher = FileWatcher([coll], db.connection, db_path)
            for _ in range(2):
                watcher._settled_callback(coll)([FileModifiedEvent(str(notes / "file.md"))])
                watcher._drain_once()
        finally:
            db.close()

        assert lock_events == ["enter", "exit", "enter", "exit"]

    def test_startup_created_burst_absorbed_as_unchanged(self, tmp_path, monkeypatch) -> None:
        """Pitfall 1: pre-existing files' created burst is all checksum-skips."""
        _delenv_settings_vars(monkeypatch)
        db_path = tmp_path / "watch.db"
        notes = tmp_path / "notes"
        notes.mkdir()
        files = []
        for name in ("a.md", "b.md"):
            path = notes / name
            path.write_text(f"# {name}\n\nBody text for {name}. ", encoding="utf-8")
            files.append(path)
        _seed_collection(db_path, notes)

        indexer, db, coll = _open_indexer(db_path)
        try:
            assert indexer.update_collection(coll) == IncrementalResult(2, 0, 0)
        finally:
            db.close()

        burst = [FileCreatedEvent(str(p)) for p in files] + [FileModifiedEvent(str(files[0]))]
        results: list[IncrementalResult] = []
        db = Database(db_path)
        try:
            from sif.database.repositories import CollectionRepository

            coll = CollectionRepository(db.connection).get_by_name("notes")
            assert coll is not None
            watcher = FileWatcher(
                [coll],
                db.connection,
                db_path,
                WatchConfig(on_batch=lambda _coll, result: results.append(result)),
            )
            watcher._settled_callback(coll)(burst)
            watcher._drain_once()
        finally:
            db.close()

        assert len(results) == 1
        assert results[0] == IncrementalResult(added=0, updated=0, removed=0, unchanged=2)


class TestStopFlushGate:
    """CR-01: the bounded flush runs only once the worker thread has exited.

    ``Thread.join(timeout=...)`` returns silently when the thread is still
    alive, and a job can legitimately outlast the join (flock wait up to
    lock_timeout, first-use model load at embed depth). Draining then would
    run jobs on the calling thread concurrently with the still-live worker
    on the SAME connection — two threads interleaving BEGIN IMMEDIATE
    transactions breaks per-file atomicity (D-04). Synthetic worker fakes,
    zero timing (D-15).
    """

    def _make_watcher(self, conn: sqlite3.Connection, db_path: Path) -> FileWatcher:
        """Build a FileWatcher over the seeded 'notes' collection (never started)."""
        from sif.database.repositories import CollectionRepository

        coll = CollectionRepository(conn).get_by_name("notes")
        assert coll is not None
        return FileWatcher([coll], conn, db_path)

    def test_stop_skips_flush_when_worker_join_times_out(
        self, tmp_path, monkeypatch, caplog
    ) -> None:
        """A still-alive worker after the join: flush skipped, ONE warning logged."""
        _delenv_settings_vars(monkeypatch)
        db_path = tmp_path / "watch.db"
        notes = tmp_path / "notes"
        notes.mkdir()
        (notes / "a.md").write_text(BODY_ALPHA, encoding="utf-8")
        _seed_collection(db_path, notes)

        drained: list[bool] = []
        db = Database(db_path)
        try:
            watcher = self._make_watcher(db.connection, db_path)
            monkeypatch.setattr(watcher, "_drain_once", lambda: drained.append(True))

            class BusyWorker:
                """join() returns with the thread still 'alive' (timed out)."""

                def join(self, timeout: float | None = None) -> None:  # noqa: ARG002
                    return None

                def is_alive(self) -> bool:
                    return True

            watcher._worker = BusyWorker()  # type: ignore[assignment]
            with caplog.at_level(logging.WARNING, logger="sif.indexing.watcher"):
                watcher.stop(flush=True)
        finally:
            db.close()

        assert drained == []
        busy = [r for r in caplog.records if "still busy" in r.message]
        assert len(busy) == 1

    def test_stop_flushes_once_worker_exited(self, tmp_path, monkeypatch) -> None:
        """A joined (dead) worker: the bounded flush runs exactly once."""
        _delenv_settings_vars(monkeypatch)
        db_path = tmp_path / "watch.db"
        notes = tmp_path / "notes"
        notes.mkdir()
        (notes / "a.md").write_text(BODY_ALPHA, encoding="utf-8")
        _seed_collection(db_path, notes)

        drained: list[bool] = []
        db = Database(db_path)
        try:
            watcher = self._make_watcher(db.connection, db_path)
            monkeypatch.setattr(watcher, "_drain_once", lambda: drained.append(True))

            class DoneWorker:
                """join() returns with the thread exited."""

                def join(self, timeout: float | None = None) -> None:  # noqa: ARG002
                    return None

                def is_alive(self) -> bool:
                    return False

            watcher._worker = DoneWorker()  # type: ignore[assignment]
            watcher.stop(flush=True)
        finally:
            db.close()

        assert drained == [True]


class TestRecoveryTick:
    """D-12 missing-root recovery, zero timing: the tick is invoked directly.

    A watched root that disappears is marked missing with ONE warning per
    transition (never per poll), its watch handle unscheduled, and its
    documents preserved; when the root returns, the watch is rescheduled and
    one full-reconcile job is enqueued.
    """

    def _seed_one_doc(self, tmp_path, monkeypatch) -> Path:
        """Seed db + collection + one indexed document; returns the db path."""
        _delenv_settings_vars(monkeypatch)
        db_path = tmp_path / "watch.db"
        notes = tmp_path / "notes"
        notes.mkdir()
        (notes / "a.md").write_text(BODY_ALPHA, encoding="utf-8")
        _seed_collection(db_path, notes)

        indexer, db, coll = _open_indexer(db_path)
        try:
            assert indexer.update_collection(coll) == IncrementalResult(1, 0, 0)
        finally:
            db.close()
        return db_path

    def test_disappear_marks_missing_warns_once_preserves_docs(
        self, tmp_path, monkeypatch, caplog
    ) -> None:
        db_path = self._seed_one_doc(tmp_path, monkeypatch)
        notes = tmp_path / "notes"
        doc_file = notes / "a.md"

        observer_cls = MagicMock()
        monkeypatch.setattr(watcher_module, "Observer", observer_cls)

        db = Database(db_path)
        watcher = None
        try:
            from sif.database.repositories import CollectionRepository

            coll = CollectionRepository(db.connection).get_by_name("notes")
            assert coll is not None
            watcher = FileWatcher([coll], db.connection, db_path)
            watcher.start()
            observer = observer_cls.return_value
            assert observer.schedule.call_count == 1

            # The root disappears (unmounted/renamed drive); two ticks run.
            notes.rename(tmp_path / "notes-gone")
            with caplog.at_level(logging.WARNING, logger="sif.indexing.watcher"):
                watcher.recovery_tick()
                watcher.recovery_tick()

            # Marked missing: handle unscheduled, exactly ONE warning across
            # two ticks, and every document preserved (never swept).
            assert observer.unschedule.call_count == 1
            observer.unschedule.assert_called_once_with(observer.schedule.return_value)
            disappeared = [r for r in caplog.records if "disappeared" in r.message]
            assert len(disappeared) == 1
            assert _doc_paths(db_path) == {str(doc_file)}
        finally:
            if watcher is not None:
                watcher.stop(flush=False)
            db.close()

    def test_return_reschedules_and_enqueues_full_reconcile(
        self, tmp_path, monkeypatch, caplog
    ) -> None:
        db_path = self._seed_one_doc(tmp_path, monkeypatch)
        notes = tmp_path / "notes"

        observer_cls = MagicMock()
        monkeypatch.setattr(watcher_module, "Observer", observer_cls)

        db = Database(db_path)
        watcher = None
        try:
            from sif.database.repositories import CollectionRepository

            coll = CollectionRepository(db.connection).get_by_name("notes")
            assert coll is not None
            watcher = FileWatcher([coll], db.connection, db_path)
            watcher.start()
            observer = observer_cls.return_value

            # Lose the root, then bring it back.
            notes.rename(tmp_path / "notes-gone")
            watcher.recovery_tick()
            (tmp_path / "notes-gone").rename(notes)
            with caplog.at_level(logging.WARNING, logger="sif.indexing.watcher"):
                watcher.recovery_tick()

            # Rescheduled (second schedule call), warned exactly once on the
            # return transition, and one full-reconcile job enqueued (D-12).
            assert observer.schedule.call_count == 2
            returned = [r for r in caplog.records if "returned" in r.message]
            assert len(returned) == 1
            assert watcher._queue.qsize() == 1
            job_collection, folded = watcher._queue.get_nowait()
            watcher._queue.task_done()
            assert job_collection.name == "notes"
            assert folded.needs_reconcile is True
            assert folded.index_candidates == set()
            assert folded.remove_candidates == set()
        finally:
            if watcher is not None:
                watcher.stop(flush=False)
            db.close()

    def test_burst_for_missing_root_hits_d11_guard_no_sweep(self, tmp_path, monkeypatch) -> None:
        """Edge (adjacency): a burst for a vanished root is a missing event, zero counts."""
        _delenv_settings_vars(monkeypatch)
        db_path = tmp_path / "watch.db"
        notes = tmp_path / "notes"
        notes.mkdir()
        doc_file = notes / "a.md"
        doc_file.write_text(BODY_ALPHA, encoding="utf-8")
        _seed_collection(db_path, notes)

        indexer, db, coll = _open_indexer(db_path)
        try:
            assert indexer.update_collection(coll) == IncrementalResult(1, 0, 0)
        finally:
            db.close()

        notes.rename(tmp_path / "notes-gone")
        events: list[str] = []
        results: list[IncrementalResult] = []
        db = Database(db_path)
        try:
            from sif.database.repositories import CollectionRepository

            coll = CollectionRepository(db.connection).get_by_name("notes")
            assert coll is not None
            watcher = FileWatcher(
                [coll],
                db.connection,
                db_path,
                WatchConfig(on_event=events.append, on_batch=lambda _c, r: results.append(r)),
            )
            watcher._settled_callback(coll)([FileModifiedEvent(str(doc_file))])
            watcher._drain_once()
        finally:
            db.close()

        assert "missing notes" in events
        assert results == [IncrementalResult()]
        assert _doc_paths(db_path) == {str(doc_file)}


DIM = 8


def _embed_manager_mock(
    dim: int = DIM,
    conn: sqlite3.Connection | None = None,
    embed_txn_flags: list[bool] | None = None,
    sequence: list[str] | None = None,
) -> MagicMock:
    """Build a mocked EmbeddingManager producing deterministic dim-length vectors.

    ``conn``/``embed_txn_flags``: when both given, every embed() call records
    ``conn.in_transaction`` at call time (the D-09 boundary proof).
    ``sequence``: when given, every embed() call appends "embed" (lock-order proof).
    """
    manager = MagicMock()
    manager.get_model_info.return_value = {
        "loaded": True,
        "model_id": "test-model",
        "embedding_dim": dim,
    }

    def fake_embed(texts: list[str], **_kwargs: object) -> MagicMock:
        if conn is not None and embed_txn_flags is not None:
            embed_txn_flags.append(conn.in_transaction)
        if sequence is not None:
            sequence.append("embed")
        vectors = [[0.1] * dim for _ in texts]
        return MagicMock(embeddings=vectors)

    manager.embed.side_effect = fake_embed
    return manager


class TestEmbedDepth:
    """The --embed inline depth (D-09/D-10, LIVE-05), mocked at the manager boundary.

    Real tmp DB with a FLOAT[8] vec0 table; chunk/embedding rows are asserted
    through fresh connections. Embedding compute must never run inside an
    open write transaction.
    """

    def _run_burst(
        self,
        watcher: FileWatcher,
        coll: Collection,
        file_path: Path,
    ) -> None:
        """Fold one modified-file burst and drain it on the calling thread."""
        watcher._settled_callback(coll)([FileModifiedEvent(str(file_path))])
        watcher._drain_once()

    @staticmethod
    def _check_conn(db_path: Path) -> sqlite3.Connection:
        """Fresh factory connection (sqlite-vec loaded) for vector-table reads."""
        from sif.database.factory import create_connection

        return create_connection(Path(db_path))

    def test_default_depth_writes_document_but_zero_chunks_and_vectors(
        self, tmp_path, monkeypatch
    ) -> None:
        """LIVE-05/D-10: a burst without embed depth purges/writes nothing vector-side."""
        _delenv_settings_vars(monkeypatch)
        db_path = tmp_path / "watch.db"
        notes = tmp_path / "notes"
        notes.mkdir()
        doc_file = notes / "a.md"
        doc_file.write_text(BODY_ALPHA, encoding="utf-8")
        _seed_collection(db_path, notes)

        db = Database(db_path)
        try:
            from sif.database.repositories import CollectionRepository

            coll = CollectionRepository(db.connection).get_by_name("notes")
            assert coll is not None
            watcher = FileWatcher([coll], db.connection, db_path)
            self._run_burst(watcher, coll, doc_file)
        finally:
            db.close()

        check = self._check_conn(db_path)
        try:
            doc = check.execute(
                "SELECT id FROM documents WHERE path = ?", (str(doc_file.resolve()),)
            ).fetchone()
            assert doc is not None
            assert check.execute("SELECT COUNT(*) FROM document_chunks").fetchone()[0] == 0
            assert check.execute("SELECT COUNT(*) FROM document_embeddings").fetchone()[0] == 0
        finally:
            check.close()

    def test_embed_depth_writes_chunks_and_vectors(self, tmp_path, monkeypatch) -> None:
        """D-09: embed depth chunks the changed doc and persists vectors."""
        _delenv_settings_vars(monkeypatch)
        db_path = tmp_path / "watch.db"
        notes = tmp_path / "notes"
        notes.mkdir()
        doc_file = notes / "a.md"
        doc_file.write_text(BODY_ALPHA, encoding="utf-8")
        _seed_collection(db_path, notes)

        manager = _embed_manager_mock()
        db = Database(db_path)
        try:
            from sif.database.repositories import CollectionRepository

            coll = CollectionRepository(db.connection).get_by_name("notes")
            assert coll is not None
            with (
                patch("sif.config.settings.get_settings", return_value=_test_settings()),
                patch(
                    "sif.embedding.manager.EmbeddingManager.from_settings",
                    return_value=manager,
                ),
            ):
                watcher = FileWatcher([coll], db.connection, db_path, WatchConfig(depth="embed"))
                self._run_burst(watcher, coll, doc_file)
        finally:
            db.close()

        check = self._check_conn(db_path)
        try:
            rows = check.execute(
                """
                SELECT c.document_id, c.sequence, e.chunk_id
                FROM document_chunks c
                LEFT JOIN document_embeddings e ON e.chunk_id = c.id
                WHERE c.document_id = (SELECT id FROM documents WHERE path = ?)
                ORDER BY c.sequence
                """,
                (str(doc_file.resolve()),),
            ).fetchall()
        finally:
            check.close()

        assert len(rows) >= 1
        assert [row[1] for row in rows] == list(range(len(rows)))
        assert all(row[2] is not None for row in rows)

    def test_embed_compute_runs_outside_any_write_transaction(self, tmp_path, monkeypatch) -> None:
        """D-09/Pitfall 5: conn.in_transaction is False at every embed() call.

        The vector-write transaction opens only AFTER embed returns — proven
        by recording in_transaction at chunk-create time and observing it
        True there while the embed-time flags are all False, with the
        transaction closed again once the leg finishes.
        """
        _delenv_settings_vars(monkeypatch)
        db_path = tmp_path / "watch.db"
        notes = tmp_path / "notes"
        notes.mkdir()
        doc_file = notes / "a.md"
        doc_file.write_text(BODY_ALPHA, encoding="utf-8")
        _seed_collection(db_path, notes)

        embed_txn_flags: list[bool] = []
        write_txn_flags: list[bool] = []
        original_create = DocumentChunkRepository.create

        def recording_create(self: DocumentChunkRepository, chunk: object) -> object:
            result = original_create(self, chunk)  # type: ignore[arg-type]
            # Recorded AFTER the insert: the legacy implicit BEGIN fires on
            # the first DML, so pre-insert flags would read autocommit.
            write_txn_flags.append(self.db.in_transaction)
            return result

        monkeypatch.setattr(DocumentChunkRepository, "create", recording_create)

        db = Database(db_path)
        try:
            from sif.database.repositories import CollectionRepository

            coll = CollectionRepository(db.connection).get_by_name("notes")
            assert coll is not None
            manager = _embed_manager_mock(conn=db.connection, embed_txn_flags=embed_txn_flags)
            with (
                patch("sif.config.settings.get_settings", return_value=_test_settings()),
                patch(
                    "sif.embedding.manager.EmbeddingManager.from_settings",
                    return_value=manager,
                ),
            ):
                watcher = FileWatcher([coll], db.connection, db_path, WatchConfig(depth="embed"))
                self._run_burst(watcher, coll, doc_file)
                assert db.connection.in_transaction is False
        finally:
            db.close()

        assert len(embed_txn_flags) >= 1
        assert all(flag is False for flag in embed_txn_flags)
        assert len(write_txn_flags) >= 1
        assert all(flag is True for flag in write_txn_flags)

    def test_dimension_mismatch_fails_soft_and_disables_embed_for_session(
        self, tmp_path, monkeypatch
    ) -> None:
        """First-use check: 768-dim model vs FLOAT[8] schema -> one error event,
        embed disabled for the session, BM25 freshness continues."""
        _delenv_settings_vars(monkeypatch)
        db_path = tmp_path / "watch.db"
        notes = tmp_path / "notes"
        notes.mkdir()
        doc_file = notes / "a.md"
        doc_file.write_text(BODY_ALPHA, encoding="utf-8")
        _seed_collection(db_path, notes)

        manager = _embed_manager_mock(dim=768)
        events: list[str] = []
        results: list[IncrementalResult] = []
        db = Database(db_path)
        try:
            from sif.database.repositories import CollectionRepository

            coll = CollectionRepository(db.connection).get_by_name("notes")
            assert coll is not None
            with (
                patch("sif.config.settings.get_settings", return_value=_test_settings()),
                patch(
                    "sif.embedding.manager.EmbeddingManager.from_settings",
                    return_value=manager,
                ) as from_settings,
            ):
                watcher = FileWatcher(
                    [coll],
                    db.connection,
                    db_path,
                    WatchConfig(
                        depth="embed",
                        on_event=events.append,
                        on_batch=lambda _c, result: results.append(result),
                    ),
                )
                doc_file.write_text(BODY_BETA, encoding="utf-8")
                self._run_burst(watcher, coll, doc_file)
                doc_file.write_text("# Third\n\n" + ("Gamma text. " * 40), encoding="utf-8")
                self._run_burst(watcher, coll, doc_file)
                assert from_settings.call_count == 1
        finally:
            db.close()

        errors = [e for e in events if e.startswith("error ")]
        assert len(errors) == 1
        assert "768" in errors[0]
        assert "8" in errors[0]
        # BM25 freshness continued through both bursts.
        assert [r.added + r.updated for r in results] == [1, 1]
        manager.embed.assert_not_called()
        check = sqlite3.connect(str(db_path))
        try:
            assert check.execute("SELECT COUNT(*) FROM document_chunks").fetchone()[0] == 0
        finally:
            check.close()

    def test_model_lazy_loads_on_first_embed_burst_and_stays_cached(
        self, tmp_path, monkeypatch
    ) -> None:
        """D-09: from_settings/load_model run at first embed work, not at
        construction; one cached load across bursts."""
        _delenv_settings_vars(monkeypatch)
        db_path = tmp_path / "watch.db"
        notes = tmp_path / "notes"
        notes.mkdir()
        doc_file = notes / "a.md"
        doc_file.write_text(BODY_ALPHA, encoding="utf-8")
        _seed_collection(db_path, notes)

        manager = _embed_manager_mock()
        db = Database(db_path)
        try:
            from sif.database.repositories import CollectionRepository

            coll = CollectionRepository(db.connection).get_by_name("notes")
            assert coll is not None
            with (
                patch("sif.config.settings.get_settings", return_value=_test_settings()),
                patch(
                    "sif.embedding.manager.EmbeddingManager.from_settings",
                    return_value=manager,
                ) as from_settings,
            ):
                watcher = FileWatcher([coll], db.connection, db_path, WatchConfig(depth="embed"))
                assert from_settings.call_count == 0
                assert manager.load_model.call_count == 0

                self._run_burst(watcher, coll, doc_file)
                assert from_settings.call_count == 1
                assert manager.load_model.call_count == 1

                doc_file.write_text(BODY_BETA, encoding="utf-8")
                self._run_burst(watcher, coll, doc_file)
                assert from_settings.call_count == 1
                assert manager.load_model.call_count == 1
        finally:
            db.close()

    def test_embed_runs_inside_the_same_per_burst_lock_window(self, tmp_path, monkeypatch) -> None:
        """D-09: one index_lock enter/exit spans the BM25 leg AND the embed leg."""
        _delenv_settings_vars(monkeypatch)
        db_path = tmp_path / "watch.db"
        notes = tmp_path / "notes"
        notes.mkdir()
        doc_file = notes / "a.md"
        doc_file.write_text(BODY_ALPHA, encoding="utf-8")
        _seed_collection(db_path, notes)

        sequence: list[str] = []

        @contextmanager
        def recording_lock(_db_path: Path, _timeout_s: float, _on_wait=None):
            sequence.append("enter")
            try:
                yield
            finally:
                sequence.append("exit")

        monkeypatch.setattr(watcher_module, "index_lock", recording_lock)

        manager = _embed_manager_mock(sequence=sequence)
        db = Database(db_path)
        try:
            from sif.database.repositories import CollectionRepository

            coll = CollectionRepository(db.connection).get_by_name("notes")
            assert coll is not None
            with (
                patch("sif.config.settings.get_settings", return_value=_test_settings()),
                patch(
                    "sif.embedding.manager.EmbeddingManager.from_settings",
                    return_value=manager,
                ),
            ):
                watcher = FileWatcher([coll], db.connection, db_path, WatchConfig(depth="embed"))
                self._run_burst(watcher, coll, doc_file)
        finally:
            db.close()

        assert sequence == ["enter", "embed", "exit"]
