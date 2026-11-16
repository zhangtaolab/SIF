"""SIF MCP (Model Context Protocol) Server."""

from __future__ import annotations

from mcp.server import MCPServer

from sif.mcp.app import build_server
from sif.mcp.backend import SearchBackend


__all__ = [
    "MCPServer",
    "SearchBackend",
    "build_server",
]
