"""SIF MCP (Model Context Protocol) Server."""

from __future__ import annotations

from sif.mcp.backend import SearchBackend
from sif.mcp.handlers import ToolHandler
from sif.mcp.server import MCPServer


__all__ = [
    "MCPServer",
    "SearchBackend",
    "ToolHandler",
]
