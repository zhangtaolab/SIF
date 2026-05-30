"""Integration tests for MCP server end-to-end flows."""

from __future__ import annotations

import json
from io import StringIO
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient

from sif.mcp.handlers import (
    GetToolHandler,
    MultiGetToolHandler,
    QueryToolHandler,
    StatusToolHandler,
)
from sif.mcp.protocol import MCPErrorCode, SearchResult
from sif.mcp.server import MCPServer
from sif.mcp.transports.http import create_app
from sif.mcp.transports.stdio import StdioTransport


def _make_backend():
    """Create a mocked SearchBackend with async methods."""
    backend = MagicMock()
    backend.hybrid_search = AsyncMock(return_value=[])
    backend.get_document = AsyncMock(return_value=None)
    backend.get_documents_by_pattern = AsyncMock(return_value=([], []))
    backend.get_status = AsyncMock(return_value=([], 0))
    return backend


class TestStdioIntegration:
    """End-to-end stdio transport integration tests."""

    @pytest.mark.asyncio
    async def test_stdio_full_lifecycle(self) -> None:
        """Verify initialize -> tools/list -> tools/call sequence."""
        backend = _make_backend()
        backend.get_status = AsyncMock(
            return_value=(
                [
                    MagicMock(name="notes", document_count=5, last_updated=None, size_bytes=None),
                ],
                5,
            ),
        )

        server = MCPServer(backend)
        server.register_tools(
            [
                QueryToolHandler(),
                GetToolHandler(),
                MultiGetToolHandler(),
                StatusToolHandler(),
            ],
        )

        messages = [
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {"protocolVersion": "2024-11-05"},
            },
            {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}},
            {
                "jsonrpc": "2.0",
                "id": 3,
                "method": "tools/call",
                "params": {"name": "status", "arguments": {}},
            },
        ]
        stdin = StringIO("\n".join(json.dumps(m) for m in messages) + "\n")
        stdout = StringIO()
        transport = StdioTransport(server, stdin=stdin, stdout=stdout)
        await transport.run()

        stdout.seek(0)
        lines = [line.strip() for line in stdout.readlines() if line.strip()]
        responses = [json.loads(line) for line in lines]

        assert len(responses) == 3

        # initialize response
        assert responses[0]["result"]["protocolVersion"] == "2024-11-05"
        assert responses[0]["id"] == 1
        assert "error" not in responses[0]

        # tools/list response
        assert responses[1]["id"] == 2
        assert len(responses[1]["result"]["tools"]) == 4
        tool_names = {t["name"] for t in responses[1]["result"]["tools"]}
        assert tool_names == {"query", "get", "multi_get", "status"}
        assert "error" not in responses[1]

        # tools/call response
        assert responses[2]["id"] == 3
        assert "content" in responses[2]["result"]
        assert "error" not in responses[2]

    @pytest.mark.asyncio
    async def test_stdio_reject_before_initialize(self) -> None:
        """Verify tools/list before initialize returns SERVER_NOT_INITIALIZED."""
        backend = _make_backend()
        server = MCPServer(backend)
        server.register_tools([StatusToolHandler()])

        stdin = StringIO('{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}}\n')
        stdout = StringIO()
        transport = StdioTransport(server, stdin=stdin, stdout=stdout)
        await transport.run()

        stdout.seek(0)
        line = stdout.readline().strip()
        response = json.loads(line)

        assert response["id"] == 1
        assert response["error"]["code"] == MCPErrorCode.SERVER_NOT_INITIALIZED

    @pytest.mark.asyncio
    async def test_stdio_handles_notification(self) -> None:
        """Verify notifications/initialized produces no response."""
        backend = _make_backend()
        server = MCPServer(backend)

        stdin = StringIO('{"jsonrpc":"2.0","method":"notifications/initialized","params":{}}\n')
        stdout = StringIO()
        transport = StdioTransport(server, stdin=stdin, stdout=stdout)
        await transport.run()

        stdout.seek(0)
        assert stdout.read() == ""

    @pytest.mark.asyncio
    async def test_stdio_tools_call_query(self) -> None:
        """Verify tools/call for query tool returns search results."""
        backend = _make_backend()
        backend.hybrid_search = AsyncMock(
            return_value=[
                SearchResult(
                    doc_id="d1",
                    path="/a.md",
                    title="A",
                    content="hello",
                    score=0.9,
                    highlights=["hi"],
                ),
            ],
        )

        server = MCPServer(backend)
        server.register_tools([QueryToolHandler()])

        messages = [
            {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}},
            {
                "jsonrpc": "2.0",
                "id": 2,
                "method": "tools/call",
                "params": {"name": "query", "arguments": {"query": "hello"}},
            },
        ]
        stdin = StringIO("\n".join(json.dumps(m) for m in messages) + "\n")
        stdout = StringIO()
        transport = StdioTransport(server, stdin=stdin, stdout=stdout)
        await transport.run()

        stdout.seek(0)
        lines = [line.strip() for line in stdout.readlines() if line.strip()]
        responses = [json.loads(line) for line in lines]

        assert len(responses) == 2
        assert responses[1]["id"] == 2
        assert "content" in responses[1]["result"]
        content_text = responses[1]["result"]["content"][0]["text"]
        assert "hello" in content_text

    @pytest.mark.asyncio
    async def test_stdio_unknown_tool(self) -> None:
        """Verify calling an unknown tool returns UNKNOWN_TOOL error."""
        backend = _make_backend()
        server = MCPServer(backend)
        server.register_tools([StatusToolHandler()])

        messages = [
            {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}},
            {
                "jsonrpc": "2.0",
                "id": 2,
                "method": "tools/call",
                "params": {"name": "nonexistent", "arguments": {}},
            },
        ]
        stdin = StringIO("\n".join(json.dumps(m) for m in messages) + "\n")
        stdout = StringIO()
        transport = StdioTransport(server, stdin=stdin, stdout=stdout)
        await transport.run()

        stdout.seek(0)
        lines = [line.strip() for line in stdout.readlines() if line.strip()]
        responses = [json.loads(line) for line in lines]

        assert responses[1]["error"]["code"] == MCPErrorCode.UNKNOWN_TOOL

    @pytest.mark.asyncio
    async def test_stdio_method_not_found(self) -> None:
        """Verify unknown method returns METHOD_NOT_FOUND error."""
        backend = _make_backend()
        server = MCPServer(backend)
        server.register_tools([StatusToolHandler()])

        messages = [
            {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}},
            {"jsonrpc": "2.0", "id": 2, "method": "foo/bar", "params": {}},
        ]
        stdin = StringIO("\n".join(json.dumps(m) for m in messages) + "\n")
        stdout = StringIO()
        transport = StdioTransport(server, stdin=stdin, stdout=stdout)
        await transport.run()

        stdout.seek(0)
        lines = [line.strip() for line in stdout.readlines() if line.strip()]
        responses = [json.loads(line) for line in lines]

        assert responses[1]["error"]["code"] == MCPErrorCode.METHOD_NOT_FOUND


class TestHTTPIntegration:
    """End-to-end HTTP transport integration tests."""

    @pytest.fixture
    def mock_backend(self):
        """Create a mocked SearchBackend."""
        backend = MagicMock()
        backend.hybrid_search = AsyncMock(return_value=[])
        backend.get_document = AsyncMock(return_value=None)
        backend.get_documents_by_pattern = AsyncMock(return_value=([], []))
        backend.get_status = AsyncMock(return_value=([], 0))
        return backend

    @pytest.fixture
    def http_server(self, mock_backend):
        """Create an MCPServer with default tools."""
        server = MCPServer(mock_backend)
        server.register_tools(
            [
                QueryToolHandler(),
                GetToolHandler(),
                MultiGetToolHandler(),
                StatusToolHandler(),
            ],
        )
        return server

    @pytest.fixture
    def client(self, http_server):
        """Create a FastAPI TestClient."""

        app = create_app(http_server, sse_ping_interval=0.01, sse_max_events=1)
        return TestClient(app)

    def test_http_full_lifecycle(self, client, mock_backend) -> None:
        """Verify POST initialize, tools/list, tools/call sequence."""
        mock_backend.get_status = AsyncMock(
            return_value=(
                [
                    MagicMock(name="notes", document_count=5, last_updated=None, size_bytes=None),
                ],
                5,
            ),
        )

        # initialize
        response = client.post(
            "/mcp",
            json={"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["result"]["protocolVersion"] == "2024-11-05"

        session_id = response.headers["mcp-session-id"]

        # tools/list
        response = client.post(
            "/mcp",
            json={"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}},
            headers={"MCP-Session-Id": session_id},
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data["result"]["tools"]) == 4
        tool_names = {t["name"] for t in data["result"]["tools"]}
        assert tool_names == {"query", "get", "multi_get", "status"}

        # tools/call for status
        response = client.post(
            "/mcp",
            json={
                "jsonrpc": "2.0",
                "id": 3,
                "method": "tools/call",
                "params": {"name": "status", "arguments": {}},
            },
            headers={"MCP-Session-Id": session_id},
        )
        assert response.status_code == 200
        data = response.json()
        assert "content" in data["result"]

    def test_http_cors_secure_by_default(self, http_server) -> None:
        """Verify default CORS does not use wildcard."""

        app = create_app(http_server)
        client = TestClient(app)

        response = client.post(
            "/mcp",
            json={"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}},
            headers={"Origin": "http://localhost:3000"},
        )
        assert response.status_code == 200
        assert "access-control-allow-origin" in response.headers
        assert response.headers["access-control-allow-origin"] != "*"

    def test_http_origin_rejection(self, http_server) -> None:
        """Verify POST with disallowed Origin returns 403."""

        app = create_app(http_server)
        client = TestClient(app)

        response = client.post(
            "/mcp",
            json={"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}},
            headers={"Origin": "http://evil.com"},
        )
        assert response.status_code == 403

    def test_http_sse_stream(self, client) -> None:
        """Verify GET /mcp returns SSE stream with ping event."""
        response = client.get("/mcp")
        assert response.status_code == 200
        assert "text/event-stream" in response.headers["content-type"]

        # Read first event
        for line in response.iter_lines():
            if line:
                decoded = line.decode("utf-8") if isinstance(line, bytes) else line
                assert "ping" in decoded
                break
