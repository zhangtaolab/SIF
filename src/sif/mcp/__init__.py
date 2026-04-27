"""DocSift MCP (Model Context Protocol) Server."""

from docsift.mcp.server import MCPServer, run_stdio_server

__all__ = [
    "MCPServer",
    "run_stdio_server",
]
