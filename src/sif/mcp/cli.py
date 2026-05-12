"""MCP Server CLI helpers."""

from __future__ import annotations


def run_stdio_server(db_path: str) -> None:
    """Run MCP server in stdio mode."""
    raise NotImplementedError("Implemented in plan 09-04")


def run_http_server(
    db_path: str,
    host: str = "127.0.0.1",
    port: int = 3000,
    cors_origins: list[str] | None = None,
) -> None:
    """Run MCP server in HTTP mode."""
    raise NotImplementedError("Implemented in plan 09-05")
