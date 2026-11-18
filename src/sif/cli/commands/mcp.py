"""MCP server commands."""

from __future__ import annotations

import os
from pathlib import Path

import click
from platformdirs import user_log_dir
from pydantic import ValidationError
from rich.console import Console
from rich.markup import escape

from sif.cli.error_handling import open_initialized_database_unmanaged
from sif.config.settings import get_settings
from sif.database.database import Database
from sif.utils import daemon
from sif.utils.logging import set_quiet


console = Console()
console_err = Console(stderr=True)


def _default_mcp_host() -> str:
    """Resolve SIF_MCP_HOST, falling back to loopback on invalid config."""
    try:
        return get_settings().mcp_host
    except ValidationError:
        return "127.0.0.1"


def _default_mcp_port() -> int:
    """Resolve SIF_MCP_PORT, falling back to 8080 on invalid config."""
    try:
        return get_settings().mcp_port
    except ValidationError:
        return 8080


def _daemon_log_path(log_file: str | None) -> Path:
    """Resolve the MCP daemon log path (D-21); create the parent eagerly.

    The grandchild redirects stdio to this file before the arm callback runs,
    so the directory must exist before the fork.
    """
    if log_file is not None:
        path = Path(log_file).expanduser()
    else:
        path = Path(user_log_dir("sif")) / "mcp.log"
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def _print_daemon_stop(outcome: daemon.StopOutcome) -> None:
    """Render the four stop outcomes with MCP-specific wording (D-20)."""
    if outcome.status == "stopped":
        assert outcome.pid is not None
        console.print(f"[green]MCP daemon stopped (PID {outcome.pid}).[/green]")
    elif outcome.status == "not_running":
        console.print("[yellow]MCP daemon is not running.[/yellow]")
    elif outcome.status == "permission_denied":
        assert outcome.pid is not None
        console.print(
            f"[yellow]MCP daemon (PID {outcome.pid}) belongs to another user; "
            "not stopped. Run as its owner to stop it.[/yellow]"
        )
    else:
        console.print("[yellow]MCP daemon is not running (stale PID file removed).[/yellow]")


@click.group("mcp", invoke_without_command=True)
@click.pass_context
def mcp_group(ctx: click.Context) -> None:
    """MCP server commands."""
    if ctx.invoked_subcommand is not None:
        return
    try:
        transport = get_settings().mcp_transport
    except ValidationError:
        transport = "stdio"
    if transport == "http":
        ctx.invoke(mcp_http_cmd)
    else:
        ctx.invoke(mcp_stdio_cmd)


@mcp_group.command("stdio")
@click.pass_context
def mcp_stdio_cmd(ctx: click.Context) -> None:
    """Run MCP server in stdio mode."""
    index_path = ctx.obj["index_path"]

    if not Path(index_path).exists():
        console_err.print(
            "[yellow]Warning: No index found. Some features may not work.[/yellow]",
        )

    try:
        from sif.mcp.cli import run_stdio_server  # noqa: PLC0415

        run_stdio_server(str(index_path))
    except ImportError as e:
        console.print(f"[red]MCP server not available: {e}[/red]")
        raise click.ClickException("Install with: pip install docsif[mcp]") from None


@mcp_group.command("http")
@click.option(
    "--host", "-h", default=None, help="Host to bind to (default: SIF_MCP_HOST or 127.0.0.1)"
)
@click.option(
    "--port", "-p", type=int, default=None, help="Port to listen on (default: SIF_MCP_PORT or 8080)"
)
@click.option("--reload", is_flag=True, help="Accepted for compatibility; currently has no effect")
@click.option(
    "--cors-origins",
    multiple=True,
    default=None,
    help="CORS allowed origins",
)
@click.option(
    "--allowed-hosts",
    multiple=True,
    default=None,
    help=("Additional allowed Host header values (repeatable); loopback hosts are always allowed"),
)
@click.pass_context
def mcp_http_cmd(  # noqa: PLR0913 — one parameter per `mcp http` CLI flag
    ctx: click.Context,
    host: str | None,
    port: int | None,
    reload: bool,  # noqa: ARG001
    cors_origins: tuple[str, ...] | None,
    allowed_hosts: tuple[str, ...] | None,
) -> None:
    """Run MCP server in HTTP mode."""
    index_path = ctx.obj["index_path"]
    host = _default_mcp_host() if host is None else host
    port = _default_mcp_port() if port is None else port

    console.print(f"[green]Starting MCP HTTP server on {host}:{port}[/green]")

    try:
        from sif.mcp.cli import run_http_server  # noqa: PLC0415

        origins = list(cors_origins) if cors_origins else None
        hosts = list(allowed_hosts) if allowed_hosts else None
        run_http_server(
            str(index_path),
            host=host,
            port=port,
            cors_origins=origins,
            allowed_hosts=hosts,
        )
    except ImportError as e:
        console.print(f"[red]HTTP server not available: {e}[/red]")
        raise click.ClickException("Install with: pip install docsif[http]") from None


@mcp_group.command("daemon")
@click.option(
    "--host", "-h", default=None, help="Host to bind to (default: SIF_MCP_HOST or 127.0.0.1)"
)
@click.option(
    "--port", "-p", type=int, default=None, help="Port to listen on (default: SIF_MCP_PORT or 8080)"
)
@click.option("--pid-file", help="PID file path")
@click.option("--log-file", help="Log file path")
@click.option("--stop", is_flag=True, help="Stop the daemon")
@click.option(
    "--allowed-hosts",
    multiple=True,
    default=None,
    help=("Additional allowed Host header values (repeatable); loopback hosts are always allowed"),
)
@click.option(
    "--cors-origins",
    multiple=True,
    default=None,
    help="CORS allowed origins",
)
@click.pass_context
def mcp_daemon_cmd(  # noqa: PLR0913 — one parameter per `mcp daemon` CLI flag
    ctx: click.Context,
    host: str | None,
    port: int | None,
    pid_file: str | None,
    log_file: str | None,
    stop: bool,
    allowed_hosts: tuple[str, ...] | None,
    cors_origins: tuple[str, ...] | None,
) -> None:
    """Run the MCP Streamable HTTP server as a detached daemon.

    The daemon arms on readiness — schema initialized and the model-free
    backend constructed — then binds the HTTP host; a bind failure removes
    the PID file and exits non-zero. Daemon mode serves HTTP only; stdio is
    not a daemon mode (run `sif mcp stdio` from a client instead). Logs
    default to the platform log directory (mcp.log); --log-file overrides.
    --stop targets only the MCP daemon's own <db>.mcp.pid artifact.
    """
    index_path = ctx.obj["index_path"]

    if stop:
        stop_path = (
            Path(pid_file).expanduser()
            if pid_file is not None
            else daemon.pid_path_for_mcp(str(index_path))
        )
        _print_daemon_stop(daemon.stop_daemon(stop_path, marker="mcp"))
        return

    if not hasattr(os, "fork"):
        # D-19: refuse at the CLI boundary before any log/PID work, so a
        # Windows user gets the POSIX cause and the foreground remedy
        # instead of a traceback from the double-fork internals.
        raise click.ClickException(
            "MCP daemon mode requires POSIX fork support and is not available on Windows; "
            "run `sif mcp http` in the foreground instead."
        )

    host = _default_mcp_host() if host is None else host
    port = _default_mcp_port() if port is None else port
    log_path = _daemon_log_path(log_file)
    pid_path = (
        Path(pid_file).expanduser()
        if pid_file is not None
        else daemon.pid_path_for_mcp(str(index_path))
    )
    origins = list(cors_origins) if cors_origins else None
    hosts = list(allowed_hosts) if allowed_hosts else None

    def arm() -> None:
        """Armed means ready: quiet, schema open, model-free backend, PID file."""
        set_quiet(True)
        db = open_initialized_database_unmanaged(str(index_path), Database)
        db.close()
        # Construction side effect: the schema/identity migration at the
        # backend's dimension. No model, no factory, no eager model load (D-21).
        from sif.mcp.backend import SearchBackend  # noqa: PLC0415

        SearchBackend(str(index_path))
        daemon.write_pid_file(pid_path, pid=os.getpid(), mode="mcp", depth="bm25")

    outcome = daemon.detach(log_path, arm)
    if outcome.daemon:
        try:
            from sif.mcp.cli import run_http_host  # noqa: PLC0415

            run_http_host(
                str(index_path),
                host=host,
                port=port,
                cors_origins=origins,
                allowed_hosts=hosts,
            )
        finally:
            # A bind failure exits non-zero after this cleanup; a graceful
            # stop takes the artifact with it (D-21). The watch daemon's
            # <db>.watch.pid is a different path and is never touched.
            daemon.remove_pid_file(pid_path)
        return
    if outcome.error is not None:
        raise click.ClickException(f"MCP daemon failed to start: {outcome.error}")
    assert outcome.pid is not None
    console.print(f"[green]MCP daemon running (PID {outcome.pid}).[/green]")
    console.print(f"[dim]Logs: {escape(str(log_path))}[/dim]")
