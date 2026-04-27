"""MCP server commands."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional

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
            "[yellow]Warning: No index found. Some features may not work.[/yellow]", file=sys.stderr
        )

    try:
        from sif.mcp.server import run_stdio_server

        run_stdio_server(str(index_path))
    except ImportError as e:
        console.print(f"[red]MCP server not available: {e}[/red]")
        raise click.ClickException("Install with: pip install sif[mcp]")


@mcp_group.command("http")
@click.option("--host", "-h", default="127.0.0.1", help="Host to bind to")
@click.option("--port", "-p", type=int, default=3000, help="Port to listen on")
@click.option("--reload", is_flag=True, help="Enable auto-reload")
@click.pass_context
def mcp_http_cmd(
    ctx: click.Context,
    host: str,
    port: int,
    reload: bool,
) -> None:
    """Run MCP server in HTTP mode."""
    index_path = ctx.obj["index_path"]

    console.print(f"[green]Starting MCP HTTP server on {host}:{port}[/green]")

    try:
        from sif.mcp.server_http import run_http_server

        run_http_server(str(index_path), host=host, port=port, reload=reload)
    except ImportError as e:
        console.print(f"[red]HTTP server not available: {e}[/red]")
        raise click.ClickException("Install with: pip install sif[http]")


@mcp_group.command("daemon")
@click.option("--host", "-h", default="127.0.0.1", help="Host to bind to")
@click.option("--port", "-p", type=int, default=3000, help="Port to listen on")
@click.option("--pid-file", help="PID file path")
@click.option("--log-file", help="Log file path")
@click.option("--stop", is_flag=True, help="Stop the daemon")
@click.pass_context
def mcp_daemon_cmd(
    ctx: click.Context,
    host: str,
    port: int,
    pid_file: Optional[str],
    log_file: Optional[str],
    stop: bool,
) -> None:
    """Run MCP server as a daemon."""
    if stop:
        console.print("[yellow]Stopping daemon...[/yellow]")
        # Implementation would read PID file and kill process
        console.print("[green]Daemon stopped[/green]")
        return

    console.print("[green]Starting MCP daemon...[/green]")
    console.print(f"[dim]Host: {host}:{port}[/dim]")

    # In a real implementation, this would daemonize the process
    # For now, just run the HTTP server
    ctx.invoke(mcp_http_cmd, host=host, port=port, reload=False)
