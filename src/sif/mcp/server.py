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
    ToolContentItem,
    ToolInputSchema,
    ToolsCallParams,
    ToolsCallResult,
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
        if self.state == ServerState.SHUTDOWN:
            return create_error_response(
                request.id,
                MCPErrorCode.INTERNAL_ERROR,
                "Server is shutting down",
            )

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
            return await self._handle_tools_call(request)

        if method == "resources/read":
            return await self._handle_resources_read(request)

        return create_error_response(
            request.id,
            MCPErrorCode.METHOD_NOT_FOUND,
            f"Method not found: {method}",
        )

    async def _handle_tools_call(
        self,
        request: JsonRpcRequest,
    ) -> JsonRpcResponse:
        """Handle tools/call request."""
        try:
            params = ToolsCallParams(**(request.params or {}))
        except Exception as e:
            return create_error_response(
                request.id,
                MCPErrorCode.INVALID_PARAMS,
                f"Invalid params: {e}",
            )

        handler = self._tools.get(params.name)
        if handler is None:
            return create_error_response(
                request.id,
                MCPErrorCode.UNKNOWN_TOOL,
                f"Unknown tool: {params.name}",
            )

        try:
            result = await handler.handle(params.arguments, self.backend)
        except Exception as e:
            logger.exception("Tool execution error")
            result = ToolsCallResult(
                content=[ToolContentItem(type="text", text=f"Error: {e}")],
                isError=True,
            )

        return create_success_response(request.id, result.model_dump())

    async def _handle_resources_read(
        self,
        request: JsonRpcRequest,
    ) -> JsonRpcResponse:
        """Handle resources/read request."""
        params = request.params or {}
        uri = params.get("uri", "")

        if not uri.startswith("docs://"):
            return create_error_response(
                request.id,
                MCPErrorCode.INVALID_PARAMS,
                f"Invalid URI scheme: {uri}",
            )

        doc_id = uri[7:].split("?")[0]
        from_line = params.get("from_line")
        max_lines = params.get("max_lines")

        doc = await self.backend.get_document(doc_id, from_line, max_lines)
        if doc is None:
            return create_error_response(
                request.id,
                MCPErrorCode.INVALID_PARAMS,
                f"Document not found: {doc_id}",
            )

        mime_type = "text/markdown" if doc.path.endswith(".md") else "text/plain"
        return create_success_response(
            request.id,
            {
                "contents": [
                    {
                        "uri": uri,
                        "mimeType": mime_type,
                        "text": doc.content,
                    }
                ]
            },
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
        elif method == "notifications/shutdown":
            self.state = ServerState.SHUTDOWN
            logger.debug("Server shutdown requested")
        else:
            logger.debug("Unhandled notification: %s", method)
