"""MCP (Model Context Protocol) server implementation for SIF.

This package provides MCP server functionality:
- stdio transport for CLI integration
- HTTP/SSE transport for web integration
- MCP protocol handlers
- Tool and resource definitions
"""

from sif.mcp_server.handlers import ResourceHandler, ToolHandler
from sif.mcp_server.server import MCPServer
from sif.mcp_server.tools import CollectionTool, IndexTool, SearchTool
from sif.mcp_server.transport import HTTPTransport, StdioTransport, Transport


__all__ = [
    "CollectionTool",
    "HTTPTransport",
    "IndexTool",
    "MCPServer",
    "ResourceHandler",
    "SearchTool",
    "StdioTransport",
    "ToolHandler",
    "Transport",
]
