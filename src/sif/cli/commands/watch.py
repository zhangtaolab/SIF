"""The ``sif watch`` foreground command (Phase 12 MVP host).

Startup reconcile per collection (D-03) runs BEFORE the observer arms, so
the FSEvents startup created-burst is absorbed by checksum skips
(Pitfall 1). Depth is tiered (LIVE-05): BM25-only unless ``--embed`` (or
``SIF_WATCH_UPDATE_DEPTH=embed``) explicitly opts into vector updates.
Shutdown is signal-driven (D-14): first SIGINT/SIGTERM runs one bounded
flush plus a WAL truncate checkpoint and exits 0; a second signal exits 130
immediately with no flush.
"""

from __future__ import annotations

import signal
import sqlite3
import sys
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from types import FrameType

import click
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

from sif.cli.commands.index import _render_index_event
from sif.config.settings import Settings
from sif.core.models import Collection
from sif.database.database import Database
from sif.database.locking import index_lock
from sif.database.repositories import CollectionRepository
from sif.indexing.incremental import IncrementalIndexer
from sif.indexing.watcher import FileWatcher, WatchConfig


console = Console()

_LOOP_INTERVAL_SECONDS = 0.2
_IMMEDIATE_EXIT_AFTER_SIGNALS = 2
_WAL_CHECKPOINT_TRUNCATE = "PRAGMA wal_checkpoint(TRUNCATE)"


@dataclass
class SignalState:
    """Mutable stop-flag state shared by the D-14 signal machinery."""

    stop: bool = False
    signal_count: int = 0


def make_signal_handler(state: SignalState) -> Callable[[int, FrameType | None], None]:
    """Build the D-14 SIGINT/SIGTERM handler.

    The first signal sets the stop flag so the run loop exits into the
    graceful teardown (one bounded flush + WAL checkpoint, exit 0). A second
    signal raises SystemExit(130) immediately with no flush — the escape
    hatch when the graceful path is stuck (Pitfall 8).
    """

    def _handle_signal(_signum: int, _frame: FrameType | None) -> None:
        state.signal_count += 1
        if state.signal_count >= _IMMEDIATE_EXIT_AFTER_SIGNALS:
            sys.exit(130)
        state.stop = True

    return _handle_signal


def install_signal_handlers(state: SignalState) -> None:
    """Install the D-14 handler for SIGINT and SIGTERM (one shared routine)."""
    handler = make_signal_handler(state)
    signal.signal(signal.SIGINT, handler)
    signal.signal(signal.SIGTERM, handler)


def shutdown_watcher(watcher: FileWatcher, conn: sqlite3.Connection) -> None:
    """D-14 teardown: ONE bounded flush of the in-flight batch, then the WAL checkpoint.

    The checkpoint executes on the worker's own connection AFTER
    ``watcher.stop`` has quiesced the worker thread (the main thread runs it,
    never the worker), inside try/finally so a failed flush still attempts
    the checkpoint.
    """
    try:
        watcher.stop(flush=True)
    finally:
        conn.execute(_WAL_CHECKPOINT_TRUNCATE)


def _select_collections(
    coll_repo: CollectionRepository, names: tuple[str, ...]
) -> list[Collection]:
    """Resolve ``-c`` names to their collections (D-01).

    No names: every registered collection. An unknown name raises the same
    ClickException wording as ``update_cmd``.
    """
    if not names:
        return coll_repo.list_all()
    by_name = {coll.name: coll for coll in coll_repo.list_all()}
    selected: list[Collection] = []
    # WR-02: order-preserving dedupe — a repeated -c name must not schedule
    # duplicate watches or orphan a _WatchState entry in FileWatcher.start().
    for name in dict.fromkeys(names):
        if name not in by_name:
            raise click.ClickException(f"Collection '{name}' not found")
        selected.append(by_name[name])
    return selected


def _effective_depth(*, embed: bool, no_embed: bool, settings: Settings) -> str:
    """LIVE-05 depth matrix: flags win, then the setting, default BM25-only.

    ``--embed`` forces embed on; ``--no-embed`` forces it off; otherwise the
    ``watch_update_depth`` setting applies. With neither flag nor an
    opting-in setting, embedding never runs.
    """
    if embed:
        return "embed"
    if no_embed:
        return "bm25"
    return settings.watch_update_depth


def _render_watch_event(event: str, *, verbose: bool) -> None:
    """Render live progress events during watching (D-13).

    Failures and missing roots always stay visible. Per-file lines print
    only under ``--verbose``; the default is the per-batch summary.
    """
    code, _, payload = event.partition(" ")
    if code == "error":
        console.print(f"  [red]{payload}[/red]")
    elif code == "missing":
        console.print(
            f"  [yellow]Collection root missing: {payload} — skipped, documents preserved[/yellow]"
        )
    elif verbose:
        if code == "scan":
            console.print(f"  [dim]Found {payload} files[/dim]")
        elif code == "unchanged":
            console.print(f"  [dim]Unchanged: {payload}[/dim]")
        elif code == "indexed":
            console.print(f"  [dim]Indexed: {payload}[/dim]")


def _render_batch(name: str, added: int, updated: int, removed: int, unchanged: int) -> None:
    """One concise summary line per settled burst (D-13)."""
    console.print(
        f"[dim]{name}: indexed {added + updated} · removed {removed} · unchanged {unchanged}[/dim]"
    )


@click.command("watch")
@click.option(
    "--collection",
    "-c",
    "collections",
    multiple=True,
    help="Watch only the named collection(s); repeatable. Collection-set "
    "changes while watch runs require a restart.",
)
@click.option(
    "--embed",
    is_flag=True,
    help="Also write vector embeddings for changed documents (opt-in; default is BM25-only)",
)
@click.option(
    "--no-embed",
    is_flag=True,
    help="Force BM25-only updates even when SIF_WATCH_UPDATE_DEPTH=embed",
)
@click.option(
    "--verbose",
    is_flag=True,
    help="Print per-file event lines instead of per-batch summaries",
)
@click.pass_context
def watch_cmd(
    ctx: click.Context,
    collections: tuple[str, ...],
    embed: bool,
    no_embed: bool,
    verbose: bool,
) -> None:
    """Watch collections and keep the index current as files change.

    Collection-set changes (adding or removing collections) require a watch
    restart in this MVP.
    """
    index_path = ctx.obj["index_path"]

    from sif.config.settings import get_settings  # noqa: PLC0415

    settings = get_settings()
    lock_timeout = settings.lock_wait_timeout
    debounce_interval = settings.watch_debounce_interval
    depth = _effective_depth(embed=embed, no_embed=no_embed, settings=settings)

    state = SignalState()
    install_signal_handlers(state)

    watcher: FileWatcher | None = None
    try:
        with Database(index_path) as db:
            db.init_schema()
            selected = _select_collections(CollectionRepository(db.connection), collections)
            if not selected:
                console.print(
                    "[yellow]No collections found. Add one with 'sif collection add'.[/yellow]",
                )
                return

            # D-03: one full reconcile pass per collection BEFORE the
            # observer arms — anything drifted before watch started becomes
            # fresh immediately, and the startup burst lands on matching
            # checksums.
            indexer = IncrementalIndexer(db.connection)
            for coll in selected:
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
                selected,
                db.connection,
                Path(index_path),
                WatchConfig(
                    debounce_interval=debounce_interval,
                    lock_timeout=lock_timeout,
                    depth=depth,
                    restat_interval=settings.watch_restat_interval,
                    on_event=lambda event: _render_watch_event(event, verbose=verbose),
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
            depth_label = "embed" if depth == "embed" else "BM25-only"
            console.print(f"\n[bold]Watching {len(selected)} collection(s) — Ctrl-C to stop[/bold]")
            for coll in selected:
                console.print(f"  {coll.name}: {coll.path}")
            console.print(f"  depth: {depth_label} · debounce: {debounce_interval}s")

            while not state.stop:
                time.sleep(_LOOP_INTERVAL_SECONDS)

            # Graceful path: ONE bounded flush, then the WAL checkpoint, exit 0.
            shutdown_watcher(watcher, db.connection)
            watcher = None
    finally:
        if watcher is not None:
            # Exception path (including the second signal's SystemExit(130)):
            # stop intake without flushing — the immediate-exit contract.
            watcher.stop(flush=False)
