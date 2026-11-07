"""The ``sif watch`` foreground command (Phase 12 MVP host).

Startup reconcile per collection (D-03) runs BEFORE the observer arms, so
the FSEvents startup created-burst is absorbed by checksum skips
(Pitfall 1). Depth is BM25-only in this plan; ``--embed`` arrives in 12-02.
"""

from __future__ import annotations

import signal
import sys
import time
from pathlib import Path
from types import FrameType

import click
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

from sif.cli.commands.index import _render_index_event
from sif.database.database import Database
from sif.database.locking import index_lock
from sif.database.repositories import CollectionRepository
from sif.indexing.incremental import IncrementalIndexer
from sif.indexing.watcher import FileWatcher, WatchConfig


console = Console()

_LOOP_INTERVAL_SECONDS = 0.2
_IMMEDIATE_EXIT_AFTER_SIGNALS = 2


def _render_watch_event(event: str) -> None:
    """Render live progress events during watching (D-13 subset).

    Per-file ``scan``/``unchanged``/``indexed`` lines stay quiet — the
    per-batch summary carries the counts (``--verbose`` arrives in 12-02).
    Failures and missing roots stay visible.
    """
    code, _, payload = event.partition(" ")
    if code == "error":
        console.print(f"  [red]{payload}[/red]")
    elif code == "missing":
        console.print(
            f"  [yellow]Collection root missing: {payload} — skipped, documents preserved[/yellow]"
        )


def _render_batch(name: str, added: int, updated: int, removed: int, unchanged: int) -> None:
    """One concise summary line per settled burst (D-13)."""
    console.print(
        f"[dim]{name}: indexed {added + updated} · removed {removed} · unchanged {unchanged}[/dim]"
    )


@click.command("watch")
@click.pass_context
def watch_cmd(ctx: click.Context) -> None:
    """Watch collections and keep the index current as files change."""
    index_path = ctx.obj["index_path"]

    from sif.config.settings import get_settings  # noqa: PLC0415

    settings = get_settings()
    lock_timeout = settings.lock_wait_timeout
    debounce_interval = settings.watch_debounce_interval

    state = {"stop": False, "signals": 0}

    def _handle_signal(_signum: int, _frame: FrameType | None) -> None:
        state["signals"] += 1
        if state["signals"] >= _IMMEDIATE_EXIT_AFTER_SIGNALS:
            sys.exit(130)
        state["stop"] = True

    signal.signal(signal.SIGINT, _handle_signal)
    signal.signal(signal.SIGTERM, _handle_signal)

    watcher: FileWatcher | None = None
    try:
        with Database(index_path) as db:
            db.init_schema()
            collections = CollectionRepository(db.connection).list_all()
            if not collections:
                console.print(
                    "[yellow]No collections found. Add one with 'sif collection add'.[/yellow]",
                )
                return

            # D-03: one full reconcile pass per collection BEFORE the
            # observer arms — anything drifted before watch started becomes
            # fresh immediately, and the startup burst lands on matching
            # checksums.
            indexer = IncrementalIndexer(db.connection)
            for coll in collections:
                console.print(f"\n[bold]Reconciling collection: {coll.name}[/bold]")
                with Progress(
                    SpinnerColumn(),
                    TextColumn("[progress.description]{task.description}"),
                    console=console,
                ) as progress:
                    task = progress.add_task(f"Indexing {coll.name}...", total=None)
                    with index_lock(
                        Path(index_path),
                        lock_timeout,
                        on_wait=lambda: console.print(
                            f"[dim]Another index writer is running; waiting up to "
                            f"{lock_timeout:.0f}s...[/dim]"
                        ),
                    ):
                        indexer.update_collection(
                            coll,
                            progress=_render_index_event(console, progress, task),
                        )

            watcher = FileWatcher(
                collections,
                db.connection,
                Path(index_path),
                WatchConfig(
                    debounce_interval=debounce_interval,
                    lock_timeout=lock_timeout,
                    depth="bm25",
                    on_event=_render_watch_event,
                    on_batch=lambda coll, result: _render_batch(
                        coll.name,
                        result.added,
                        result.updated,
                        result.removed,
                        result.unchanged,
                    ),
                ),
            )
            watcher.start()

            # D-13 banner — printed after the observer arms, so "Watching"
            # marks the moment live events start flowing.
            console.print(
                f"\n[bold]Watching {len(collections)} collection(s) — Ctrl-C to stop[/bold]"
            )
            for coll in collections:
                console.print(f"  {coll.name}: {coll.path}")
            console.print(f"  depth: BM25-only · debounce: {debounce_interval}s")

            while not state["stop"]:
                time.sleep(_LOOP_INTERVAL_SECONDS)
    finally:
        if watcher is not None:
            watcher.stop()
