"""MCP Server CLI helpers."""

from __future__ import annotations

from sif.mcp.transports.http import run_http_server
from sif.mcp.transports.stdio import run_stdio_server_sync as run_stdio_server


__all__ = ["run_http_server", "run_stdio_server"]
