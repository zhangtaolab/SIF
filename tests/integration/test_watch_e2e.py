"""Real-subprocess end-to-end battery for ``sif watch`` (Phase 12 SC1-5, D-15).

Every test drives the real CLI subprocess (real Observer, real
EventDebouncer, real DB file) over its own seeded tmp collection and asserts
OUTCOMES — row presence/content, exit codes, WAL size — never raw OS event
sequences, so the suite is backend-agnostic across FSEvents and inotify
(A1). All polling is deadline-bounded through fresh sqlite connections; the
only fixed sleeps are small bounded settle windows after an outcome, never
naked poll loops. Steps inside each test are serialized: the previous
outcome is observed before the next mutation (the 12-01 tracer's ordering
discipline).
"""

from __future__ import annotations

import os
import signal
import sqlite3
import subprocess
import sys
import time
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import TypeVar

from sif.core.models import Collection
from sif.database.database import Database
from sif.database.repositories import CollectionRepository


_SEED_BODY = "# Seed Note\n\n" + ("Seed paragraph text. " * 30)
_NEW_BODY = "# Live Note\n\n" + ("Live paragraph text. " * 30)
_EDITED_BODY = "# Edited Note\n\n" + ("Edited paragraph text. " * 30)
_ATOMIC_BODY = "# Atomic Save\n\n" + ("Atomic paragraph text. " * 30)
_RECOVERY_BODY = "# Recovered Note\n\n" + ("Recovered paragraph text. " * 30)

_STARTUP_DEADLINE_S = 30.0
_LIVE_DEADLINE_S = 30.0
_SHUTDOWN_DEADLINE_S = 20.0
_RECOVERY_DEADLINE_S = 20.0
# Bounded settle windows (D-15): fixed, finite waits for debounced trailing
# work to land AFTER an observed outcome — never part of a poll loop.
_TEMP_SETTLE_S = 2.5
_RECOVERY_SETTLE_S = 2.5
_POLL_INTERVAL_S = 0.1

T = TypeVar("T")


def _seed_db(db_path: Path, notes_dir: Path, seed_name: str) -> None:
    """Build a real index with one collection pointing at a one-file tree."""
    notes_dir.mkdir(parents=True, exist_ok=True)
    (notes_dir / seed_name).write_text(_SEED_BODY, encoding="utf-8")
    db = Database(db_path)
    try:
        db.init_schema()
        with db.connection:
            CollectionRepository(db.connection).create(
                Collection(name="notes", path=str(notes_dir))
            )
    finally:
        db.close()


def _child_env(extra: dict[str, str] | None = None) -> dict[str, str]:
    """Child environment: SIF_-stripped, FORCE_COLOR unset, NO_COLOR on."""
    env = {k: v for k, v in os.environ.items() if not k.startswith("SIF_")}
    env.pop("FORCE_COLOR", None)
    env["NO_COLOR"] = "1"
    if extra is not None:
        env.update(extra)
    return env


@contextmanager
def _watch_process(
    db_path: Path, cwd: Path, extra_env: dict[str, str] | None = None
) -> Iterator[tuple[subprocess.Popen[bytes], Path]]:
    """Run the real ``sif watch`` subprocess with output captured to a file.

    stdout AND stderr share one capture file (merged) so banner lines and
    the D-12 recovery logger warnings are both assertable. The safety-net
    ``finally`` terminates a still-running child, so a failing assertion can
    never leak a watcher process.
    """
    out_path = cwd / "watch-output.log"
    with out_path.open("w", encoding="utf-8") as out:
        argv = [sys.executable, "-u", "-m", "sif.cli.main", "--index", str(db_path), "watch"]
        proc = subprocess.Popen(
            argv,
            cwd=cwd,
            env=_child_env(extra_env),
            stdout=out,
            stderr=subprocess.STDOUT,
        )
        try:
            yield proc, out_path
        finally:
            if proc.poll() is None:
                proc.send_signal(signal.SIGINT)
                try:
                    proc.wait(timeout=_SHUTDOWN_DEADLINE_S)
                except subprocess.TimeoutExpired:
                    proc.kill()
                    proc.wait(timeout=_SHUTDOWN_DEADLINE_S)


def _stop_cleanly(proc: subprocess.Popen[bytes]) -> None:
    """SIGINT + wait for the D-14 graceful exit, inside the with-block.

    Called as the last body statement, the spawner's safety net then sees a
    dead child and never double-signals (a second signal would exit 130).
    """
    proc.send_signal(signal.SIGINT)
    proc.wait(timeout=_SHUTDOWN_DEADLINE_S)


def _output_text(out_path: Path) -> str:
    """Read the child's captured output written so far."""
    return out_path.read_text(encoding="utf-8", errors="replace")


def _fetch_one(db_path: Path, sql: str, params: tuple[str, ...] = ()) -> tuple | None:
    """Fetch one row through a fresh connection (never a cached reader)."""
    conn = sqlite3.connect(str(db_path))
    try:
        return conn.execute(sql, params).fetchone()
    finally:
        conn.close()


def _poll_until(check: Callable[[], T | None], deadline_s: float, description: str) -> T:
    """Poll ``check`` under an explicit deadline; None means "not yet" (D-15)."""
    deadline = time.monotonic() + deadline_s
    while time.monotonic() < deadline:
        result = check()
        if result is not None:
            return result
        time.sleep(_POLL_INTERVAL_S)
    raise AssertionError(f"{description} not observed within {deadline_s}s")


def _doc_path(notes_dir: Path, name: str) -> str:
    """Stored-path spelling for a file under the collection (resolved)."""
    return str((notes_dir / name).resolve())


def _wait_for_row(db_path: Path, path: str, deadline_s: float) -> None:
    """Poll fresh connections until ``path`` exists in documents."""

    def _present() -> tuple | None:
        return _fetch_one(db_path, "SELECT 1 FROM documents WHERE path = ?", (path,))

    _poll_until(_present, deadline_s, f"document row for {path}")


def _wait_for_output(out_path: Path, needle: str, deadline_s: float) -> None:
    """Wait until the child's captured output contains ``needle``."""

    def _seen() -> str | None:
        text = _output_text(out_path)
        return text if needle in text else None

    _poll_until(_seen, deadline_s, f"output marker {needle!r}")


def _assert_none_indexed(db_path: Path, paths: tuple[str, ...]) -> None:
    """Fail immediately if any excluded path has a documents row."""
    for path in paths:
        leaked = _fetch_one(db_path, "SELECT 1 FROM documents WHERE path = ?", (path,))
        assert leaked is None, f"excluded path was indexed: {path}"


def test_watch_indexes_new_file_end_to_end(tmp_path: Path) -> None:
    """LIVE-01 tracer: a post-startup save becomes indexed; SIGINT exits 0."""
    db_path = tmp_path / "watch.db"
    notes = tmp_path / "notes"
    _seed_db(db_path, notes, "seed.md")
    live_path = _doc_path(notes, "live-note.md")

    with _watch_process(db_path, tmp_path) as (proc, out_path):
        # 1. Startup reconcile (D-03): the seed row appears before any event.
        _wait_for_row(db_path, _doc_path(notes, "seed.md"), _STARTUP_DEADLINE_S)
        # 2. The observer is armed (banner printed after watcher.start()).
        _wait_for_output(out_path, "Watching", _STARTUP_DEADLINE_S)
        # 3. NOW a new file proves the event pipeline (LIVE-01).
        (notes / "live-note.md").write_text(_NEW_BODY, encoding="utf-8")
        _wait_for_row(db_path, live_path, _LIVE_DEADLINE_S)
        # 4. Content check through a fresh connection.
        content = _fetch_one(db_path, "SELECT content FROM documents WHERE path = ?", (live_path,))
        assert content is not None
        assert "Live paragraph text" in content[0]
        _stop_cleanly(proc)

    assert proc.returncode == 0, (
        f"watch exited {proc.returncode}; output:\n{_output_text(out_path)}"
    )


def test_watch_edit_and_delete_reflected_end_to_end(tmp_path: Path) -> None:
    """SC1/LIVE-01: an edit's new content+checksum land, then a delete drops the row."""
    db_path = tmp_path / "watch.db"
    notes = tmp_path / "notes"
    seed = notes / "seed.md"
    seed_path = _doc_path(notes, "seed.md")
    _seed_db(db_path, notes, seed.name)

    with _watch_process(db_path, tmp_path) as (proc, out_path):
        _wait_for_row(db_path, seed_path, _STARTUP_DEADLINE_S)
        _wait_for_output(out_path, "Watching", _STARTUP_DEADLINE_S)

        checksum_row = _fetch_one(
            db_path, "SELECT checksum FROM documents WHERE path = ?", (seed_path,)
        )
        assert checksum_row is not None
        old_checksum = checksum_row[0]

        def _edited() -> tuple | None:
            found = _fetch_one(
                db_path, "SELECT checksum FROM documents WHERE path = ?", (seed_path,)
            )
            if found is not None and found[0] != old_checksum:
                return found
            return None

        seed.write_text(_EDITED_BODY, encoding="utf-8")
        _poll_until(_edited, _LIVE_DEADLINE_S, "edited content and checksum")
        content = _fetch_one(db_path, "SELECT content FROM documents WHERE path = ?", (seed_path,))
        assert content is not None
        assert "Edited paragraph text" in content[0]

        def _gone() -> bool | None:
            found = _fetch_one(db_path, "SELECT 1 FROM documents WHERE path = ?", (seed_path,))
            return True if found is None else None

        seed.unlink()
        _poll_until(_gone, _LIVE_DEADLINE_S, "deleted row removal")
        _stop_cleanly(proc)

    assert proc.returncode == 0, (
        f"watch exited {proc.returncode}; output:\n{_output_text(out_path)}"
    )


def test_watch_atomic_save_leaves_exactly_one_row(tmp_path: Path) -> None:
    """SC2/LIVE-03: a real os.replace atomic save re-indexes the final path
    once — no duplicate row, and the row is never observed wiped."""
    db_path = tmp_path / "watch.db"
    notes = tmp_path / "notes"
    _seed_db(db_path, notes, "note.md")
    final_path = _doc_path(notes, "note.md")
    observed_counts: list[int] = []

    def _reindexed() -> tuple | None:
        found = _fetch_one(db_path, "SELECT content FROM documents WHERE path = ?", (final_path,))
        count_row = _fetch_one(db_path, "SELECT COUNT(*) FROM documents")
        assert count_row is not None
        observed_counts.append(int(count_row[0]))
        if found is not None and "Atomic paragraph text" in found[0]:
            return found
        return None

    with _watch_process(db_path, tmp_path) as (proc, out_path):
        _wait_for_row(db_path, final_path, _STARTUP_DEADLINE_S)
        _wait_for_output(out_path, "Watching", _STARTUP_DEADLINE_S)

        temp = notes / "note.md.sb-E2EATOMIC"
        temp.write_text(_ATOMIC_BODY, encoding="utf-8")
        os.replace(temp, notes / "note.md")

        _poll_until(_reindexed, _LIVE_DEADLINE_S, "atomic-save re-index of the final path")
        # The rename chain's trailing delete must never wipe the row, and the
        # final path must own exactly one row in a one-file collection.
        assert min(observed_counts) >= 1, f"documents wiped during atomic save: {observed_counts}"
        row_count = _fetch_one(
            db_path, "SELECT COUNT(*) FROM documents WHERE path = ?", (final_path,)
        )
        assert row_count is not None
        assert row_count[0] == 1
        total = _fetch_one(db_path, "SELECT COUNT(*) FROM documents")
        assert total is not None
        assert total[0] == 1
        _stop_cleanly(proc)

    assert proc.returncode == 0, (
        f"watch exited {proc.returncode}; output:\n{_output_text(out_path)}"
    )


def test_watch_temp_noise_never_indexed(tmp_path: Path) -> None:
    """SC3/LIVE-04: editor/atomic-save temp files never reach documents."""
    db_path = tmp_path / "watch.db"
    notes = tmp_path / "notes"
    _seed_db(db_path, notes, "seed.md")
    # The plan's three noise names plus one glob-matching lock file: the
    # ``**/*.md`` pattern alone WOULD index ``.#hidden.md`` — only the shared
    # ignore predicate keeps it out, which is exactly the LIVE-04 exclusion.
    noise_names = ("note2.md.swp", "4913", "note3.md.sb-XX", ".#hidden.md")
    noise_paths = tuple(_doc_path(notes, name) for name in noise_names)
    control_path = _doc_path(notes, "control.md")

    def _control_indexed() -> tuple | None:
        _assert_none_indexed(db_path, noise_paths)
        return _fetch_one(db_path, "SELECT 1 FROM documents WHERE path = ?", (control_path,))

    with _watch_process(db_path, tmp_path) as (proc, out_path):
        _wait_for_row(db_path, _doc_path(notes, "seed.md"), _STARTUP_DEADLINE_S)
        _wait_for_output(out_path, "Watching", _STARTUP_DEADLINE_S)

        for name in noise_names:
            (notes / name).write_text("# temp noise\n", encoding="utf-8")
        (notes / "control.md").write_text(_NEW_BODY, encoding="utf-8")

        # Outcome proof the pipeline processed this window: the control file
        # IS indexed while the noise (checked on every poll) never is...
        _poll_until(_control_indexed, _LIVE_DEADLINE_S, "control file indexed")
        # ...then one bounded settle for any debounced trailing burst.
        time.sleep(_TEMP_SETTLE_S)
        _assert_none_indexed(db_path, noise_paths)
        _stop_cleanly(proc)

    assert proc.returncode == 0, (
        f"watch exited {proc.returncode}; output:\n{_output_text(out_path)}"
    )


def test_watch_missing_root_recovery(tmp_path: Path) -> None:
    """SC5/LIVE-11/D-12: root renamed away — rows intact, process alive,
    warned exactly once; renamed back — rescheduled, new file indexed."""
    db_path = tmp_path / "watch.db"
    notes = tmp_path / "notes"
    _seed_db(db_path, notes, "seed.md")
    seed_path = _doc_path(notes, "seed.md")
    away = tmp_path / "notes-away"
    recovered_path = _doc_path(notes, "recovered.md")

    with _watch_process(db_path, tmp_path, extra_env={"SIF_WATCH_RESTAT_INTERVAL": "1"}) as (
        proc,
        out_path,
    ):
        _wait_for_row(db_path, seed_path, _STARTUP_DEADLINE_S)
        _wait_for_output(out_path, "Watching", _STARTUP_DEADLINE_S)

        notes.rename(away)
        _wait_for_output(out_path, "disappeared", _RECOVERY_DEADLINE_S)
        # Two more re-stat ticks must pass without a second warning, without
        # the process dying, and without a single row being swept.
        time.sleep(_RECOVERY_SETTLE_S)
        assert proc.poll() is None, "watch died while the collection root was missing"
        rows = _fetch_one(db_path, "SELECT COUNT(*) FROM documents WHERE path = ?", (seed_path,))
        assert rows is not None, "document swept while root was missing"
        assert rows[0] == 1, "document swept while root was missing"

        away.rename(notes)
        _wait_for_output(out_path, "returned", _RECOVERY_DEADLINE_S)
        (notes / "recovered.md").write_text(_RECOVERY_BODY, encoding="utf-8")
        _wait_for_row(db_path, recovered_path, _LIVE_DEADLINE_S)
        content = _fetch_one(
            db_path, "SELECT content FROM documents WHERE path = ?", (recovered_path,)
        )
        assert content is not None
        assert "Recovered paragraph text" in content[0]
        _stop_cleanly(proc)

    assert proc.returncode == 0, (
        f"watch exited {proc.returncode}; output:\n{_output_text(out_path)}"
    )
    output = _output_text(out_path)
    assert output.count("disappeared") == 1, (
        f"missing-root warning not raised exactly once:\n{output}"
    )


def test_watch_clean_exits_truncate_wal(tmp_path: Path) -> None:
    """D-14: SIGINT and SIGTERM each exit 0 and leave a 0-byte ``-wal`` file.

    The parent holds an open read connection per case so the child's close
    is never the last one — SQLite otherwise DELETES a fully checkpointed
    ``-wal`` on last-connection close, making a size-0 file unobservable.
    With a live second connection the file survives, and only the child's
    ``PRAGMA wal_checkpoint(TRUNCATE)`` can leave it at 0 bytes.
    """
    for sig in (signal.SIGINT, signal.SIGTERM):
        case_dir = tmp_path / f"case-{sig.name.lower()}"
        case_dir.mkdir()
        db_path = case_dir / "watch.db"
        notes = case_dir / "notes"
        _seed_db(db_path, notes, "seed.md")
        live_path = _doc_path(notes, "live.md")
        wal_path = Path(str(db_path) + "-wal")

        holder = sqlite3.connect(str(db_path))
        try:
            holder.execute("SELECT COUNT(*) FROM documents").fetchone()
            with _watch_process(db_path, case_dir) as (proc, out_path):
                _wait_for_row(db_path, _doc_path(notes, "seed.md"), _STARTUP_DEADLINE_S)
                _wait_for_output(out_path, "Watching", _STARTUP_DEADLINE_S)
                # One live write guarantees committed WAL frames before the
                # signal — a 0-byte result afterwards is then meaningful.
                (notes / "live.md").write_text(_NEW_BODY, encoding="utf-8")
                _wait_for_row(db_path, live_path, _LIVE_DEADLINE_S)

                def _wal_has_frames(wal: Path = wal_path) -> int | None:
                    size = wal.stat().st_size if wal.exists() else -1
                    return size if size > 0 else None

                _poll_until(_wal_has_frames, _LIVE_DEADLINE_S, "non-empty WAL before shutdown")
                proc.send_signal(sig)
                proc.wait(timeout=_SHUTDOWN_DEADLINE_S)

            assert proc.returncode == 0, (
                f"{sig.name}: watch exited {proc.returncode}; output:\n{_output_text(out_path)}"
            )
            assert wal_path.exists(), f"{sig.name}: -wal vanished with a live reader"
            assert wal_path.stat().st_size == 0, (
                f"{sig.name}: -wal holds {wal_path.stat().st_size} bytes after clean exit"
            )
        finally:
            holder.close()
