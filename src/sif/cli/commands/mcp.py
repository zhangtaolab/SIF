"""MCP server commands."""

from __future__ import annotations

from pathlib import Path

import click
from pydantic import ValidationError
from rich.console import Console

from sif.config.settings import get_settings


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
@click.pass_context
def mcp_http_cmd(
    ctx: click.Context,
    host: str | None,
    port: int | None,
    reload: bool,  # noqa: ARG001
    cors_origins: tuple[str, ...] | None,
) -> None:
    """Run MCP server in HTTP mode."""
    index_path = ctx.obj["index_path"]
    host = _default_mcp_host() if host is None else host
    port = _default_mcp_port() if port is None else port

    console.print(f"[green]Starting MCP HTTP server on {host}:{port}[/green]")

    try:
        from sif.mcp.cli import run_http_server  # noqa: PLC0415

        origins = list(cors_origins) if cors_origins else None
        run_http_server(str(index_path), host=host, port=port, cors_origins=origins)
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
@click.pass_context
def mcp_daemon_cmd(  # noqa: PLR0913
    ctx: click.Context,  # noqa: ARG001
    host: str | None,  # noqa: ARG001
    port: int | None,  # noqa: ARG001
    pid_file: str | None,  # noqa: ARG001
    log_file: str | None,  # noqa: ARG001
    stop: bool,  # noqa: ARG001
) -> None:
    """Daemon mode is not implemented; use 'mcp http' instead."""
    raise click.ClickException("Daemon mode is not yet implemented. Use 'mcp http' instead.")
