"""MCP (Model Context Protocol) server implementation for DocSift.

This package provides MCP server functionality:
- stdio transport for CLI integration
- HTTP/SSE transport for web integration
- MCP protocol handlers
- Tool and resource definitions
"""

from docsift.mcp_server.server import MCPServer
from docsift.mcp_server.transport import Transport, StdioTransport, HTTPTransport
from docsift.mcp_server.handlers import ToolHandler, ResourceHandler
from docsift.mcp_server.tools import SearchTool, IndexTool, CollectionTool

__all__ = [
    "MCPServer",
    "Transport",
    "StdioTransport",
    "HTTPTransport",
    "ToolHandler",
    "ResourceHandler",
    "SearchTool",
    "IndexTool",
    "CollectionTool",
]
