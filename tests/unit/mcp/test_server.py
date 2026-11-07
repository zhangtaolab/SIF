"""Behavior tests for MCP server dispatch, resources, and lifecycle state."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from sif.mcp.handlers import QueryToolHandler
from sif.mcp.protocol import (
    Document,
    JsonRpcNotification,
    JsonRpcRequest,
    MCPErrorCode,
    ToolContentItem,
    ToolsCallResult,
)
from sif.mcp.server import MCPServer, ServerState


class TestMCPServerBranches:
    """All requests use in-memory protocol models and mocked backends."""

    @pytest.fixture
    def backend(self) -> MagicMock:
        """Return a backend whose asynchronous API is entirely mocked."""
        backend = MagicMock()
        backend.hybrid_search = AsyncMock(return_value=[])
        backend.get_document = AsyncMock(return_value=None)
        return backend

    @pytest.fixture
    def server(self, backend: MagicMock) -> MCPServer:
        """Return a server in its initialized lifecycle state with a real handler."""
        server = MCPServer(backend)
        server.state = ServerState.INITIALIZED
        server.register_tools([QueryToolHandler()])
        return server

    @pytest.mark.asyncio
    async def test_shutdown_rejects_requests(self, backend: MagicMock) -> None:
        """A shutdown server returns an internal error without dispatching."""
        server = MCPServer(backend)
        server.state = ServerState.SHUTDOWN

        response = await server.handle_request(JsonRpcRequest(id=9, method="tools/list"))

        assert response.error is not None
        assert response.error.code == MCPErrorCode.INTERNAL_ERROR
        assert response.error.message == "Server is shutting down"

    @pytest.mark.asyncio
    async def test_preinitialize_request_is_rejected(self, backend: MagicMock) -> None:
        """Only initialize is valid before the initialized state transition."""
        response = await MCPServer(backend).handle_request(
            JsonRpcRequest(id=1, method="tools/list")
        )

        assert response.error is not None
        assert response.error.code == MCPErrorCode.SERVER_NOT_INITIALIZED

    @pytest.mark.asyncio
    async def test_tools_list_converts_registered_input_schema(self, server: MCPServer) -> None:
        """The registered handler schema becomes a protocol tool definition."""
        response = await server.handle_request(JsonRpcRequest(id=2, method="tools/list"))

        assert response.error is None
        assert len(response.result["tools"]) == 1
        tool = response.result["tools"][0]
        assert tool["name"] == "query"
        assert tool["inputSchema"]["required"] == ["query"]
        assert tool["inputSchema"]["properties"]["limit"]["default"] == 10

    @pytest.mark.asyncio
    async def test_invalid_tool_params_return_invalid_params(self, server: MCPServer) -> None:
        """Pydantic parameter validation errors use INVALID_PARAMS."""
        response = await server.handle_request(
            JsonRpcRequest(id=3, method="tools/call", params={"arguments": {}})
        )

        assert response.error is not None
        assert response.error.code == MCPErrorCode.INVALID_PARAMS
        assert "Invalid params:" in response.error.message

    @pytest.mark.asyncio
    async def test_unknown_tool_is_reported(self, server: MCPServer) -> None:
        """An unregistered tool name is a protocol error, not a handler call."""
        response = await server.handle_request(
            JsonRpcRequest(
                id=4,
                method="tools/call",
                params={"name": "missing", "arguments": {}},
            )
        )

        assert response.error is not None
        assert response.error.code == MCPErrorCode.UNKNOWN_TOOL
        assert response.error.message == "Unknown tool: missing"

    @pytest.mark.asyncio
    async def test_handler_exception_becomes_error_content(
        self, server: MCPServer, backend: MagicMock
    ) -> None:
        """Backend exceptions are converted to isError content in a success envelope."""
        backend.hybrid_search.side_effect = RuntimeError("backend unavailable")

        response = await server.handle_request(
            JsonRpcRequest(
                id=5,
                method="tools/call",
                params={"name": "query", "arguments": {"query": "test"}},
            )
        )

        assert response.error is None
        assert response.result["isError"] is True
        assert response.result["content"][0]["text"] == "Error: backend unavailable"

    @pytest.mark.asyncio
    async def test_successful_handler_payload_is_preserved(self, server: MCPServer) -> None:
        """A controlled handler result is dispatched with its original arguments."""
        handler = MagicMock()
        handler.name = "controlled"
        handler.description = "Controlled handler"
        handler.input_schema = {"type": "object", "properties": {}, "required": []}
        handler.handle = AsyncMock(
            return_value=ToolsCallResult(
                content=[ToolContentItem(type="text", text="payload")],
            )
        )
        server._tools[handler.name] = handler

        response = await server.handle_request(
            JsonRpcRequest(
                id=6,
                method="tools/call",
                params={"name": "controlled", "arguments": {"value": 3}},
            )
        )

        assert response.result["content"][0]["text"] == "payload"
        handler.handle.assert_awaited_once_with({"value": 3}, server.backend)

    @pytest.mark.asyncio
    async def test_unknown_method_is_reported(self, server: MCPServer) -> None:
        """Unknown initialized requests return METHOD_NOT_FOUND."""
        response = await server.handle_request(JsonRpcRequest(id=7, method="unknown/method"))

        assert response.error is not None
        assert response.error.code == MCPErrorCode.METHOD_NOT_FOUND
        assert response.error.message == "Method not found: unknown/method"

    @pytest.mark.asyncio
    async def test_resource_rejects_invalid_scheme(self, server: MCPServer) -> None:
        """Only docs:// URIs are accepted by resources/read."""
        response = await server.handle_request(
            JsonRpcRequest(id=8, method="resources/read", params={"uri": "file:///secret"})
        )

        assert response.error is not None
        assert response.error.code == MCPErrorCode.INVALID_PARAMS
        assert response.error.message == "Invalid URI scheme: file:///secret"

    @pytest.mark.asyncio
    async def test_resource_missing_document_is_reported(
        self, server: MCPServer, backend: MagicMock
    ) -> None:
        """Missing resource IDs produce a useful invalid-params error."""
        backend.get_document.return_value = None

        response = await server.handle_request(
            JsonRpcRequest(
                id=9,
                method="resources/read",
                params={"uri": "docs://missing?ignored=true", "from_line": 2, "max_lines": 5},
            )
        )

        assert response.error is not None
        assert response.error.message == "Document not found: missing"
        backend.get_document.assert_awaited_once_with("missing", 2, 5)

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        ("path", "mime_type"),
        [("notes/today.md", "text/markdown"), ("notes/today.txt", "text/plain")],
    )
    async def test_resource_returns_document_content_and_mime_type(
        self,
        server: MCPServer,
        backend: MagicMock,
        path: str,
        mime_type: str,
    ) -> None:
        """Markdown and plain resources preserve URI and decoded content."""
        backend.get_document.return_value = Document(
            doc_id="doc-1",
            path=path,
            content="你好\nbody",
        )

        response = await server.handle_request(
            JsonRpcRequest(
                id=10,
                method="resources/read",
                params={"uri": "docs://doc-1?collection=notes"},
            )
        )

        assert response.error is None
        assert response.result["contents"] == [
            {
                "uri": "docs://doc-1?collection=notes",
                "mimeType": mime_type,
                "text": "你好\nbody",
            }
        ]

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "method",
        [
            "notifications/initialized",
            "notifications/cancelled",
            "notifications/unknown",
        ],
    )
    async def test_nonshutdown_notifications_do_not_change_state(
        self, server: MCPServer, method: str
    ) -> None:
        """Initialized, cancelled, and unknown notifications are safe no-ops."""
        await server.handle_notification(JsonRpcNotification(method=method))

        assert server.state == ServerState.INITIALIZED

    @pytest.mark.asyncio
    async def test_shutdown_notification_changes_state(self, server: MCPServer) -> None:
        """The shutdown notification drives the server lifecycle state."""
        await server.handle_notification(JsonRpcNotification(method="notifications/shutdown"))

        assert server.state == ServerState.SHUTDOWN
