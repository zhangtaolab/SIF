"""Async MCP server with state machine and tool registry."""

from __future__ import annotations

from enum import Enum

from sif.mcp.protocol import (
    InitializeResult,
    JsonRpcNotification,
    JsonRpcRequest,
    JsonRpcResponse,
    MCPErrorCode,
    MCPTool,
    ServerCapabilities,
    ToolInputSchema,
    ToolsListResult,
    create_error_response,
    create_success_response,
)
from sif.utils.logging import get_logger

from .backend import SearchBackend
from .handlers import ToolHandler


logger = get_logger(__name__)


class ServerState(Enum):
    """MCP server lifecycle states."""

    CREATED = "created"
    INITIALIZED = "initialized"
    SHUTDOWN = "shutdown"


class MCPServer:
    """Async Model Context Protocol server."""

    def __init__(self, backend: SearchBackend) -> None:
        """Initialize MCPServer."""
        self.backend = backend
        self.state = ServerState.CREATED
        self._tools: dict[str, ToolHandler] = {}

    def register_tools(self, tools: list[ToolHandler]) -> None:
        """Register tool handlers."""
        for tool in tools:
            self._tools[tool.name] = tool

    async def handle_request(
        self,
        request: JsonRpcRequest,
    ) -> JsonRpcResponse:
        """Handle an MCP request."""
        method = request.method

        if method == "initialize":
            self.state = ServerState.INITIALIZED
            result = InitializeResult(
                protocolVersion="2024-11-05",
                capabilities=ServerCapabilities(),
            )
            return create_success_response(request.id, result.model_dump())

        if self.state != ServerState.INITIALIZED:
            return create_error_response(
                request.id,
                MCPErrorCode.SERVER_NOT_INITIALIZED,
                "Server not initialized",
            )

        if method == "tools/list":
            tools_list = [
                MCPTool(
                    name=h.name,
                    description=h.description,
                    inputSchema=ToolInputSchema(**h.input_schema),
                )
                for h in self._tools.values()
            ]
            result = ToolsListResult(tools=tools_list)
            return create_success_response(request.id, result.model_dump())

        if method == "tools/call":
            return create_error_response(
                request.id,
                MCPErrorCode.METHOD_NOT_FOUND,
                "tools/call not yet implemented",
            )

        if method == "resources/read":
            return create_error_response(
                request.id,
                MCPErrorCode.METHOD_NOT_FOUND,
                "Resources not yet implemented",
            )

        return create_error_response(
            request.id,
            MCPErrorCode.METHOD_NOT_FOUND,
            f"Method not found: {method}",
        )

    async def handle_notification(
        self,
        notification: JsonRpcNotification,
    ) -> None:
        """Handle an MCP notification."""
        method = notification.method
        if method == "notifications/initialized":
            logger.debug("Client initialized")
        elif method == "notifications/cancelled":
            logger.debug("Request cancelled")
        else:
            logger.debug("Unhandled notification: %s", method)
