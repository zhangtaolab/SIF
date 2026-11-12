"""The ``sif watch`` command: foreground host (Phase 12) + daemon lifecycle (13-02).

Startup reconcile per collection (D-03) runs BEFORE the observer arms, so
the FSEvents startup created-burst is absorbed by checksum skips
(Pitfall 1). The pass runs through the watcher's embed-aware reconcile, so
at embed depth it re-embeds what its BM25 leg changed. Depth is tiered
(LIVE-05): BM25-only unless ``--embed`` (or
``SIF_WATCH_UPDATE_DEPTH=embed``) explicitly opts into vector updates.
Shutdown is signal-driven (D-14): first SIGINT/SIGTERM runs one bounded
flush plus a WAL truncate checkpoint and exits 0; a second signal exits 130
immediately with no flush.

Phase 13 adds the detached-daemon lifecycle on the SAME host body (D-09):
``--detach`` double-forks before anything threaded exists (Pitfall 2) and
the daemon child runs :func:`run_watch_host` verbatim with the long-lived
opt-ins wired from settings (D-15 live rescope within the ``-c`` filter,
D-16 idle WAL checkpoint); ``--stop`` corroborates the PID file's identity
and escalates SIGTERM -> bounded wait -> SIGKILL (D-05, Pitfall 3); the PID
file itself is management metadata only — flock stays the sole arbitration.

Phase 13-04 adds the OS-supervisor path (SC3): ``--install-service``
generates and installs a launchd LaunchAgent / systemd user unit whose argv
runs this same FOREGROUND command with the install-time flags baked in
(the supervised process never forks); ``--uninstall-service`` stops the
service and removes the artifact (D-11/D-12/D-13).
"""

from __future__ import annotations

import os
import signal
import sqlite3
import sys
import time
from collections.abc import Callable
from dataclasses import dataclass, replace
from pathlib import Path
from types import FrameType

import click
from platformdirs import user_log_dir
from pydantic import ValidationError
from rich.console import Console
from rich.markup import escape
from rich.progress import Progress, SpinnerColumn, TextColumn

from sif.cli.commands.index import _render_index_event
from sif.cli.error_handling import open_initialized_database, open_initialized_database_unmanaged
from sif.config.settings import Settings
from sif.core.models import Collection
from sif.database.database import Database
from sif.database.factory import WAL_CHECKPOINT_TRUNCATE
from sif.database.repositories import CollectionRepository
from sif.indexing.watcher import FileWatcher, WatchConfig
from sif.utils import daemon, service
from sif.utils.logging import get_logger


console = Console()
logger = get_logger(__name__)

_LOOP_INTERVAL_SECONDS = 0.2
_IMMEDIATE_EXIT_AFTER_SIGNALS = 2


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
    never the worker) — but only when the worker actually exited (WR-01):
    a timed-out join means a job legitimately still runs on the same
    connection (flock wait, first-use model load), and a checkpoint there is
    concurrent same-connection use — undefined even under
    ``check_same_thread=False``. A still-live worker skips the checkpoint
    with a warning; a failed flush no longer force-runs it either, for the
    same reason (worker state unknown).
    """
    watcher.stop(flush=True)
    if watcher.worker_joined():
        conn.execute(WAL_CHECKPOINT_TRUNCATE)
    else:
        logger.warning(
            "watch worker still busy at shutdown; skipping WAL checkpoint "
            "(WAL is checkpointed on the next run)"
        )


@dataclass
class WatchHostParams:
    """Resolved parameters for :func:`run_watch_host`.

    Bundled for the argument-count lint gate (the WatchConfig precedent);
    the foreground command fills the watch fields and leaves the long-lived
    opt-ins at their defaults, while the daemon path derives a copy with the
    rescope/checkpoint fields wired from settings (D-15/D-16).
    """

    index_path: str
    debounce_interval: float
    lock_timeout: float
    depth: str
    restat_interval: float
    rescope_provider: Callable[[], list[Collection]] | None = None
    rescope_interval: float = 0.0
    checkpoint_interval: float = 0.0
    verbose: bool = False


def run_watch_host(db: Database, selected: list[Collection], params: WatchHostParams) -> None:
    """Run the shared watch host body (D-09) on an OPEN database.

    The foreground command and the detached daemon execute this exact same
    body: per-collection startup reconcile (D-03), FileWatcher start, the
    D-13 banner, the park loop, and the D-14 graceful teardown. Only the
    long-lived-host opt-ins differ — the daemon wires ``rescope_provider``
    and the rescope/checkpoint intervals from settings (D-15/D-16); the
    foreground MVP passes none of them and keeps its restart-on-change shape.
    The database lifecycle belongs to the caller.
    """
    state = SignalState()
    install_signal_handlers(state)

    index_path = params.index_path
    lock_timeout = params.lock_timeout
    depth = params.depth
    debounce_interval = params.debounce_interval

    watcher: FileWatcher | None = None
    try:
        # D-03: one full reconcile pass per collection BEFORE the observer
        # arms — anything drifted before watch started becomes fresh
        # immediately, and the startup burst lands on matching checksums.
        # The pass runs through the watcher's embed-aware reconcile, so at
        # embed depth it also re-embeds what its BM25 leg changed (IN-04's
        # purged-vector repair applied to the startup seam).
        watcher = FileWatcher(
            selected,
            db.connection,
            Path(index_path),
            WatchConfig(
                debounce_interval=debounce_interval,
                lock_timeout=lock_timeout,
                depth=depth,
                restat_interval=params.restat_interval,
                on_event=lambda event: _render_watch_event(event, verbose=params.verbose),
                on_batch=lambda coll, result: _render_batch(
                    coll.name,
                    result.added,
                    result.updated,
                    result.removed,
                    result.unchanged,
                ),
                rescope_provider=params.rescope_provider,
                rescope_interval=params.rescope_interval,
                checkpoint_interval=params.checkpoint_interval,
            ),
        )
        for coll in selected:
            console.print(f"\n[bold]Reconciling collection: {escape(coll.name)}[/bold]")
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console,
            ) as progress:
                task = progress.add_task(f"Indexing {coll.name}...", total=None)
                watcher.reconcile_now(
                    coll,
                    progress=_render_index_event(console, progress, task),
                    on_wait=lambda: console.print(
                        f"[dim]Another index writer is running; waiting up to "
                        f"{lock_timeout:.0f}s...[/dim]"
                    ),
                )
        watcher.start()

        # D-13 banner — printed after the observer arms, so "Watching" marks
        # the moment live events start flowing.
        depth_label = "embed" if depth == "embed" else "BM25-only"
        console.print(f"\n[bold]Watching {len(selected)} collection(s) — Ctrl-C to stop[/bold]")
        for coll in selected:
            console.print(f"  {escape(coll.name)}: {escape(coll.path)}")
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
    Payloads are user data (file names, collection names) and routinely
    contain brackets, so they are escaped — Rich would otherwise consume
    the ``[v2]`` in ``report[v2].md`` as a style tag (IN-01).
    """
    code, _, payload = event.partition(" ")
    safe_payload = escape(payload)
    if code == "error":
        console.print(f"  [red]{safe_payload}[/red]")
    elif code == "missing":
        console.print(
            f"  [yellow]Collection root missing: {safe_payload} — "
            "skipped, documents preserved[/yellow]"
        )
    elif verbose:
        if code == "scan":
            console.print(f"  [dim]Found {safe_payload} files[/dim]")
        elif code == "unchanged":
            console.print(f"  [dim]Unchanged: {safe_payload}[/dim]")
        elif code == "indexed":
            console.print(f"  [dim]Indexed: {safe_payload}[/dim]")


def _render_batch(name: str, added: int, updated: int, removed: int, unchanged: int) -> None:
    """One concise summary line per settled burst (D-13).

    The collection name is user data and is escaped (IN-01).
    """
    safe_name = escape(name)
    console.print(
        f"[dim]{safe_name}: indexed {added + updated} · removed {removed} · "
        f"unchanged {unchanged}[/dim]"
    )


def _daemon_log_path(log_file: str | None) -> Path:
    """Resolve the daemon log path (D-07): ``--log-file``, else the platform log dir.

    The platformdirs default joins the same log tree the installed service
    will use (launchd StandardOutPath convention), so raw and supervised
    daemons log to one place. The parent directory is created eagerly — the
    grandchild's stdio redirect needs it to exist.
    """
    if log_file is not None:
        path = Path(log_file).expanduser()
    else:
        path = Path(user_log_dir("sif")) / "watch.log"
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def _daemon_rescope_provider(
    db: Database, names: tuple[str, ...]
) -> Callable[[], list[Collection]]:
    """Eligible set for the D-15 rescope poll: rescope WITHIN the ``-c`` filter.

    No names: every registered collection. With names: only the named subset
    — the provider embodies the host's eligible set and rescope is an
    exact-set diff, so a filtered daemon can never gain an excluded
    collection, and a collection removed from the table stops being watched.
    Runs on the worker thread (the tick caller), sharing the watcher's
    connection discipline.
    """

    def _provider() -> list[Collection]:
        registered = CollectionRepository(db.connection).list_all()
        if not names:
            return registered
        wanted = set(names)
        return [coll for coll in registered if coll.name in wanted]

    return _provider


def _run_detach(
    params: WatchHostParams,
    collections: tuple[str, ...],
    log_file: str | None,
    settings: Settings,
) -> None:
    """Detached-daemon path (D-06/D-07/D-09): fork FIRST, arm, then host.

    ``daemon.detach`` must be the first thing this path does — the fork
    happens before any Database, observer, or thread exists (Pitfall 2). The
    grandchild runs the exact foreground host body via :func:`run_watch_host`
    with the long-lived opt-ins wired from settings; the original parent
    prints the armed PID (SC2) or raises the arming failure.
    """
    log_path = _daemon_log_path(log_file)
    pid_file = daemon.pid_path_for(params.index_path)
    armed_db: Database | None = None
    armed_selected: list[Collection] | None = None

    def arm() -> None:
        """Armed means ready: schema open, collections selected, PID file written."""
        nonlocal armed_db, armed_selected
        db = open_initialized_database_unmanaged(params.index_path, Database)
        selected = _select_collections(CollectionRepository(db.connection), collections)
        if not selected:
            raise RuntimeError("no collections found — add one with 'sif collection add'")
        daemon.write_pid_file(pid_file, pid=os.getpid(), mode="daemon", depth=params.depth)
        armed_db = db
        armed_selected = selected

    outcome = daemon.detach(log_path, arm)
    if outcome.daemon:
        assert armed_db is not None
        assert armed_selected is not None
        daemon_params = replace(
            params,
            rescope_provider=_daemon_rescope_provider(armed_db, collections),
            rescope_interval=settings.watch_rescope_interval,
            checkpoint_interval=settings.watch_checkpoint_interval,
        )
        try:
            with armed_db:
                run_watch_host(armed_db, armed_selected, daemon_params)
        finally:
            # A graceful exit takes its PID file with it, so --stop and
            # status stay honest without a cleanup pass (D-05 metadata).
            daemon.remove_pid_file(pid_file)
        return
    if outcome.error is not None:
        raise click.ClickException(f"Watch daemon failed to start: {outcome.error}")
    assert outcome.pid is not None
    console.print(f"[green]Watch daemon running (PID {outcome.pid}).[/green]")
    console.print(f"[dim]Logs: {escape(str(log_path))}[/dim]")


def _run_stop(index_path: str | Path) -> None:
    """Stop path (D-05): corroborated SIGTERM, bounded wait, SIGKILL fallback.

    All outcomes are soft notices per the stop-idempotence contract: not
    running (no PID file), stale (garbage payload or uncorroborated PID —
    cleaned up, never signalled), or stopped.
    """
    outcome = daemon.stop_daemon(daemon.pid_path_for(index_path))
    if outcome.status == "stopped":
        assert outcome.pid is not None
        console.print(f"[green]Watch daemon stopped (PID {outcome.pid}).[/green]")
    elif outcome.status == "not_running":
        console.print("[yellow]Watch daemon is not running.[/yellow]")
    else:
        console.print("[yellow]Watch daemon is not running (stale PID file removed).[/yellow]")


def _service_manager() -> str:
    """Derive the platform's service manager (D-13): launchd on macOS, systemd elsewhere."""
    return service.LAUNCHD_MANAGER if sys.platform == "darwin" else service.SYSTEMD_MANAGER


def _service_argv_tail(params: WatchHostParams, collections: tuple[str, ...]) -> list[str]:
    """The baked tail (D-11): ``-c`` names plus the exact depth pin.

    ``--embed`` is baked when the installed depth embeds. EVERY BM25 install
    bakes ``--no-embed`` — unconditionally (WR-03/IN-01): launchd/systemd
    environments are not the installing shell's, and a later
    ``SIF_WATCH_UPDATE_DEPTH=embed`` in the service's own environment (a
    ``launchctl setenv`` persists for every LaunchAgent) would otherwise
    re-derive embed at service start. The pin is a no-op at the BM25
    runtime default and only bites when the service environment diverges
    from what was installed, so an installed-BM25 service must never start
    computing vectors.

    The service replays exactly what was installed — an absolute interpreter
    and absolute index path come from the service module, so the supervised
    process never depends on a user PATH or cwd.
    """
    tail: list[str] = []
    for name in dict.fromkeys(collections):
        tail.extend(["-c", name])
    if params.depth == "embed":
        tail.append("--embed")
    else:
        tail.append("--no-embed")
    return tail


def _run_install_service(params: WatchHostParams, collections: tuple[str, ...]) -> None:
    """Install path (D-11/D-12/D-13): generate, write, enable, start, verify."""
    abs_db = Path(params.index_path).expanduser().resolve()
    manager = _service_manager()
    try:
        result = service.install_watch_service(
            abs_db,
            _service_argv_tail(params, collections),
            manager=manager,
        )
    except (service.ServiceManagerMissing, service.ServiceCommandError) as e:
        raise click.ClickException(str(e)) from e
    console.print("[green]Watch service installed and running.[/green]")
    console.print(f"[dim]Artifact: {escape(str(result.artifact_path))}[/dim]")
    console.print(f"[dim]Logs: {escape(result.log_location)}[/dim]")
    console.print(f"[dim]Verify: {escape(result.verify_command)}[/dim]")
    if manager == service.SYSTEMD_MANAGER:
        # D-13: survive-logout is surfaced, never silently assumed — the user
        # manager ends with the last session unless linger is enabled.
        console.print(
            "[dim]To keep the service running after your last session ends: "
            "loginctl enable-linger $USER[/dim]"
        )


def _run_uninstall_service() -> None:
    """Uninstall path (D-11/D-12): stop the service, then remove the artifact."""
    try:
        removed = service.uninstall_watch_service(manager=_service_manager())
    except (service.ServiceManagerMissing, service.ServiceCommandError) as e:
        raise click.ClickException(str(e)) from e
    console.print(f"[green]Watch service stopped and removed: {escape(str(removed))}[/green]")


def _check_lifecycle_guards(
    *,
    detach: bool,
    stop: bool,
    log_file: str | None,
    install_service: bool,
    uninstall_service: bool,
) -> None:
    """Flag-combination guards for the lifecycle family (13-02/13-04).

    SC3 pins the important one: the installed service runs the foreground
    watcher under the OS supervisor and never forks, so the detach path
    (double-fork) must never be combined with it.
    """
    if detach and stop:
        raise click.ClickException("--detach and --stop are mutually exclusive.")
    if log_file is not None and not detach:
        raise click.ClickException("--log-file requires --detach.")
    if install_service and uninstall_service:
        raise click.ClickException(
            "--install-service and --uninstall-service are mutually exclusive."
        )
    if (install_service or uninstall_service) and (detach or stop):
        raise click.ClickException(
            "--install-service/--uninstall-service cannot be combined with "
            "--detach/--stop: the installed service runs the foreground watcher "
            "under the OS supervisor (no forking)."
        )


@click.command("watch")
@click.option(
    "--collection",
    "-c",
    "collections",
    multiple=True,
    help="Watch only the named collection(s); repeatable. The detached daemon "
    "picks up collection-set changes live; the foreground watch requires a restart.",
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
@click.option(
    "--detach",
    is_flag=True,
    help="Run the watcher in the background as a detached daemon and print its "
    "PID; logs go to the platform log dir unless --log-file is given",
)
@click.option(
    "--stop",
    is_flag=True,
    help="Stop the detached watch daemon (SIGTERM, bounded wait, SIGKILL fallback)",
)
@click.option(
    "--log-file",
    help="Daemon log file path (requires --detach; default: platform log dir)",
)
@click.option(
    "--install-service",
    is_flag=True,
    help="Generate and install a launchd LaunchAgent (macOS) or systemd user unit "
    "(Linux) running the FOREGROUND watcher under the OS supervisor; the -c and "
    "depth (--embed/--no-embed) flags given now are baked into the service definition",
)
@click.option(
    "--uninstall-service",
    is_flag=True,
    help="Stop the installed watch service and remove its artifact",
)
@click.pass_context
def watch_cmd(  # noqa: PLR0913
    ctx: click.Context,
    collections: tuple[str, ...],
    embed: bool,
    no_embed: bool,
    verbose: bool,
    detach: bool,
    stop: bool,
    log_file: str | None,
    install_service: bool,
    uninstall_service: bool,
) -> None:
    """Watch collections and keep the index current as files change.

    Collection-set changes are picked up live by the detached daemon
    (--detach); the foreground watch still requires a restart in this MVP.
    """
    index_path = ctx.obj["index_path"]

    _check_lifecycle_guards(
        detach=detach,
        stop=stop,
        log_file=log_file,
        install_service=install_service,
        uninstall_service=uninstall_service,
    )

    if stop:
        _run_stop(index_path)
        return
    if uninstall_service:
        _run_uninstall_service()
        return

    from sif.config.settings import get_settings  # noqa: PLC0415

    try:
        settings = get_settings()
    except ValidationError as e:
        # IN-02: the group-level conversion (main._get_default_db_path)
        # only runs when --index is OMITTED — Click never invokes a default
        # callable for a supplied option. With an explicit --index this is
        # the first Settings construction, so an invalid value (e.g.
        # SIF_WATCH_UPDATE_DEPTH=bogus) must surface as a config error
        # naming the field, not a raw pydantic traceback.
        raise click.ClickException(str(e)) from e
    params = WatchHostParams(
        index_path=str(index_path),
        debounce_interval=settings.watch_debounce_interval,
        lock_timeout=settings.lock_wait_timeout,
        depth=_effective_depth(embed=embed, no_embed=no_embed, settings=settings),
        restat_interval=settings.watch_restat_interval,
        verbose=verbose,
    )

    if install_service:
        _run_install_service(params, collections)
        return

    if detach:
        # Pitfall 2: the fork happens before any Database, observer, or
        # thread exists — detaching is the first thing this path does.
        _run_detach(params, collections, log_file, settings)
        return

    with open_initialized_database(index_path, Database) as db:
        selected = _select_collections(CollectionRepository(db.connection), collections)
        if not selected:
            console.print(
                "[yellow]No collections found. Add one with 'sif collection add'.[/yellow]",
            )
            return

        run_watch_host(db, selected, params)
