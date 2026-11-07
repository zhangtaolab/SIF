"""Real-subprocess end-to-end proof for ``sif watch`` (LIVE-01, D-03/D-15).

One serialized test: a real CLI subprocess (real Observer, real
EventDebouncer) over a seeded tmp collection. Assertions are ordered — the
seed row must appear first (startup reconcile done, D-03), so the NEW file's
row proves the event pipeline, not the reconcile pass. All polling is
deadline-bounded through fresh sqlite connections; never a naked sleep.
"""

from __future__ import annotations

import os
import signal
import sqlite3
import subprocess
import sys
import threading
import time
from pathlib import Path

from sif.core.models import Collection
from sif.database.database import Database
from sif.database.repositories import CollectionRepository


_SEED_BODY = "# Seed Note\n\n" + ("Seed paragraph text. " * 30)
_NEW_BODY = "# Live Note\n\n" + ("Live paragraph text. " * 30)
_STARTUP_DEADLINE_S = 30.0
_LIVE_DEADLINE_S = 30.0
_SHUTDOWN_DEADLINE_S = 20.0


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


def _child_env() -> dict[str, str]:
    """Child environment: SIF_-stripped, FORCE_COLOR unset, NO_COLOR on."""
    env = {k: v for k, v in os.environ.items() if not k.startswith("SIF_")}
    env.pop("FORCE_COLOR", None)
    env["NO_COLOR"] = "1"
    return env


def _wait_for_row(db_path: Path, path: str, deadline_s: float) -> None:
    """Poll a fresh connection until ``path`` exists in documents (deadline-bounded)."""
    deadline = time.monotonic() + deadline_s
    while time.monotonic() < deadline:
        conn = sqlite3.connect(str(db_path))
        try:
            row = conn.execute("SELECT 1 FROM documents WHERE path = ?", (path,)).fetchone()
        finally:
            conn.close()
        if row is not None:
            return
        time.sleep(0.1)
    raise AssertionError(f"document row for {path} not observed within {deadline_s}s")


def _wait_for_stdout(lines: list[str], needle: str, deadline_s: float) -> None:
    """Wait until the child's stdout produced a line containing ``needle``."""
    deadline = time.monotonic() + deadline_s
    while time.monotonic() < deadline:
        if any(needle in line for line in lines):
            return
        time.sleep(0.1)
    raise AssertionError(f"stdout marker {needle!r} not observed within {deadline_s}s")


def _drain_stdout(stream, lines: list[str]) -> None:
    """Append every stdout line the child produces until EOF (reader thread body)."""
    lines.extend(stream)


def test_watch_indexes_new_file_end_to_end(tmp_path: Path) -> None:
    """A file saved after startup becomes indexed with no manual update; SIGINT exits 0."""
    db_path = tmp_path / "watch.db"
    notes = tmp_path / "notes"
    seed_file = notes / "seed.md"
    live_file = notes / "live-note.md"
    _seed_db(db_path, notes, seed_file.name)

    argv = [
        sys.executable,
        "-u",  # unbuffered stdout so the live banner is observable
        "-m",
        "sif.cli.main",
        "--index",
        str(db_path),
        "watch",
    ]
    proc = subprocess.Popen(
        argv,
        env=_child_env(),
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
    )

    stdout_lines: list[str] = []
    reader = threading.Thread(target=_drain_stdout, args=(proc.stdout, stdout_lines), daemon=True)
    reader.start()

    try:
        # 1. Startup reconcile (D-03): the seed row appears before any event.
        _wait_for_row(db_path, str(seed_file), _STARTUP_DEADLINE_S)
        # 2. The observer is armed (banner printed after watcher.start()).
        _wait_for_stdout(stdout_lines, "Watching", _STARTUP_DEADLINE_S)
        # 3. NOW a new file proves the event pipeline (LIVE-01).
        live_file.write_text(_NEW_BODY, encoding="utf-8")
        _wait_for_row(db_path, str(live_file), _LIVE_DEADLINE_S)
        # 4. Content check through a fresh connection.
        conn = sqlite3.connect(str(db_path))
        try:
            content = conn.execute(
                "SELECT content FROM documents WHERE path = ?", (str(live_file),)
            ).fetchone()
        finally:
            conn.close()
        assert content is not None
        assert "Live paragraph text" in content[0]
    finally:
        if proc.poll() is None:
            proc.send_signal(signal.SIGINT)

    returncode = proc.wait(timeout=_SHUTDOWN_DEADLINE_S)
    reader.join(timeout=5.0)
    assert returncode == 0, f"watch exited {returncode}; stdout was: {''.join(stdout_lines)!r}"
