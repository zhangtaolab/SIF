"""MCP Server CLI helpers.

Thin wrappers over the composition root in :mod:`sif.mcp.app`. Imports of the
app module are lazy so ``import sif.mcp.cli`` stays cheap (the uvicorn import
inside the HTTP runner follows the same convention).
"""

from __future__ import annotations

from sif.mcp.app import DEFAULT_HOST, DEFAULT_PORT


__all__ = ["DEFAULT_HOST", "DEFAULT_PORT", "run_http_host", "run_http_server", "run_stdio_server"]


def run_stdio_server(db_path: str) -> None:
    """Serve MCP over stdio (blocking)."""
    from sif.mcp.app import run_stdio  # noqa: PLC0415

    run_stdio(db_path)


def run_http_host(
    db_path: str,
    host: str = DEFAULT_HOST,
    port: int = DEFAULT_PORT,
    cors_origins: list[str] | None = None,
    allowed_hosts: list[str] | None = None,
) -> None:
    """Serve the Streamable HTTP host (blocking) — the daemon's host body.

    Kept as a nameable seam so the detached-daemon command can be exercised
    with a host that fails to bind without forking a real uvicorn.
    """
    from sif.mcp.app import run_http  # noqa: PLC0415

    run_http(
        db_path,
        host=host,
        port=port,
        cors_origins=cors_origins,
        allowed_hosts=allowed_hosts,
    )


def run_http_server(
    db_path: str,
    host: str = DEFAULT_HOST,
    port: int = DEFAULT_PORT,
    cors_origins: list[str] | None = None,
    allowed_hosts: list[str] | None = None,
) -> None:
    """Serve MCP over Streamable HTTP (blocking)."""
    run_http_host(
        db_path,
        host=host,
        port=port,
        cors_origins=cors_origins,
        allowed_hosts=allowed_hosts,
    )
