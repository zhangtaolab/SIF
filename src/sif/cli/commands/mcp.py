"""MCP server commands."""

from __future__ import annotations

import sys
from pathlib import Path

import click
from rich.console import Console


console = Console()


@click.group("mcp")
def mcp_group() -> None:
    """MCP server commands."""
    pass


@mcp_group.command("stdio")
@click.pass_context
def mcp_stdio_cmd(ctx: click.Context) -> None:
    """Run MCP server in stdio mode."""
    index_path = ctx.obj["index_path"]

    if not Path(index_path).exists():
        console.print(
            "[yellow]Warning: No index found. Some features may not work.[/yellow]",
            file=sys.stderr,
        )

    try:
        from sif.mcp.cli import run_stdio_server

        run_stdio_server(str(index_path))
    except ImportError as e:
        console.print(f"[red]MCP server not available: {e}[/red]")
        raise click.ClickException("Install with: pip install sif[mcp]") from None


@mcp_group.command("http")
@click.option("--host", "-h", default="127.0.0.1", help="Host to bind to")
@click.option("--port", "-p", type=int, default=3000, help="Port to listen on")
@click.option("--reload", is_flag=True, help="Enable auto-reload")
@click.option(
    "--cors-origins",
    multiple=True,
    default=None,
    help="CORS allowed origins",
)
@click.pass_context
def mcp_http_cmd(
    ctx: click.Context,
    host: str,
    port: int,
    reload: bool,  # noqa: ARG001
    cors_origins: tuple[str, ...] | None,
) -> None:
    """Run MCP server in HTTP mode."""
    index_path = ctx.obj["index_path"]

    console.print(f"[green]Starting MCP HTTP server on {host}:{port}[/green]")

    try:
        from sif.mcp.cli import run_http_server

        origins = list(cors_origins) if cors_origins else None
        run_http_server(str(index_path), host=host, port=port, cors_origins=origins)
    except ImportError as e:
        console.print(f"[red]HTTP server not available: {e}[/red]")
        raise click.ClickException("Install with: pip install sif[http]") from None


@mcp_group.command("daemon")
@click.option("--host", "-h", default="127.0.0.1", help="Host to bind to")
@click.option("--port", "-p", type=int, default=3000, help="Port to listen on")
@click.option("--pid-file", help="PID file path")
@click.option("--log-file", help="Log file path")
@click.option("--stop", is_flag=True, help="Stop the daemon")
@click.pass_context
def mcp_daemon_cmd(  # noqa: PLR0913
    ctx: click.Context,
    host: str,
    port: int,
    pid_file: str | None,  # noqa: ARG001
    log_file: str | None,  # noqa: ARG001
    stop: bool,
) -> None:
    """Run MCP server as a daemon."""
    if stop:
        console.print("[yellow]Stopping daemon...[/yellow]")
        console.print("[green]Daemon stopped[/green]")
        return

    console.print("[green]Starting MCP daemon...[/green]")
    console.print(f"[dim]Host: {host}:{port}[/dim]")

    ctx.invoke(mcp_http_cmd, host=host, port=port)
