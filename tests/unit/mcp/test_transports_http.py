"""Tests for MCP HTTP transport."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient

from sif.mcp.transports.http import (
    DEFAULT_CORS_ORIGINS,
    DEFAULT_HOST,
    create_app,
)


@pytest.fixture
def mock_server():
    """Create a mock MCPServer."""
    server = MagicMock()
    server.handle_request = AsyncMock(
        return_value=MagicMock(
            model_dump=lambda **_kwargs: {
                "jsonrpc": "2.0",
                "id": 1,
                "result": {"protocolVersion": "2024-11-05"},
            }
        )
    )
    server.handle_notification = AsyncMock()
    return server


@pytest.fixture
def client(mock_server):
    """Create a FastAPI TestClient."""
    app = create_app(mock_server, sse_ping_interval=0.01, sse_max_events=1)
    return TestClient(app)


def test_default_cors_origins() -> None:
    """Test default CORS origins are non-wildcard."""
    assert DEFAULT_CORS_ORIGINS == ["http://localhost:3000", "http://127.0.0.1:3000"]
    assert "*" not in DEFAULT_CORS_ORIGINS


def test_default_host() -> None:
    """Test default host is localhost."""
    assert DEFAULT_HOST == "127.0.0.1"


def test_mcp_post_initialize(client, mock_server) -> None:
    """Test POST /mcp initialize returns protocol version."""
    response = client.post(
        "/mcp",
        json={"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["result"]["protocolVersion"] == "2024-11-05"
    assert "mcp-session-id" in response.headers
    mock_server.handle_request.assert_called_once()


def test_mcp_post_tools_list(client, mock_server) -> None:
    """Test POST /mcp tools/list after initialization."""
    session_id = client.post(
        "/mcp",
        json={"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}},
    ).headers["mcp-session-id"]

    mock_server.handle_request = AsyncMock(
        return_value=MagicMock(
            model_dump=lambda **_: {
                "jsonrpc": "2.0",
                "id": 2,
                "result": {"tools": []},
            }
        )
    )

    response = client.post(
        "/mcp",
        json={"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}},
        headers={"MCP-Session-Id": session_id},
    )
    assert response.status_code == 200
    assert response.headers["mcp-session-id"] == session_id


def test_mcp_post_tools_call(client, mock_server) -> None:
    """Test POST /mcp tools/call."""
    session_id = client.post(
        "/mcp",
        json={"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}},
    ).headers["mcp-session-id"]

    mock_server.handle_request = AsyncMock(
        return_value=MagicMock(
            model_dump=lambda **_: {
                "jsonrpc": "2.0",
                "id": 2,
                "result": {"content": []},
            }
        )
    )

    response = client.post(
        "/mcp",
        json={
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/call",
            "params": {"name": "query", "arguments": {"query": "test"}},
        },
        headers={"MCP-Session-Id": session_id},
    )
    assert response.status_code == 200
    assert "mcp-session-id" in response.headers


def test_mcp_post_notification(client, mock_server) -> None:
    """Test POST /mcp notification returns 202."""
    response = client.post(
        "/mcp",
        json={"jsonrpc": "2.0", "method": "notifications/initialized", "params": {}},
    )
    assert response.status_code == 202
    assert "mcp-session-id" in response.headers
    mock_server.handle_notification.assert_called_once()


def test_mcp_post_invalid_json(client) -> None:
    """Test POST /mcp with invalid JSON returns 400."""
    response = client.post(
        "/mcp",
        data="not json",
    )
    assert response.status_code == 400
    assert "mcp-session-id" in response.headers


def test_mcp_session_persistence(client, mock_server) -> None:
    """Test session ID persists across requests."""
    response1 = client.post(
        "/mcp",
        json={"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}},
    )
    session_id = response1.headers["mcp-session-id"]

    mock_server.handle_request = AsyncMock(
        return_value=MagicMock(
            model_dump=lambda **_: {
                "jsonrpc": "2.0",
                "id": 2,
                "result": {"tools": []},
            }
        )
    )

    response2 = client.post(
        "/mcp",
        json={"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}},
        headers={"MCP-Session-Id": session_id},
    )
    assert response2.headers["mcp-session-id"] == session_id


def test_cors_defaults(client) -> None:
    """Test CORS allows localhost origin."""
    response = client.post(
        "/mcp",
        json={"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}},
        headers={"Origin": "http://localhost:3000"},
    )
    assert response.status_code == 200
    assert "access-control-allow-origin" in response.headers


def test_cors_rejects_invalid_origin(client) -> None:
    """Test CORS rejects invalid origin."""
    response = client.post(
        "/mcp",
        json={"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}},
        headers={"Origin": "http://evil.com"},
    )
    assert response.status_code == 403


def test_get_mcp_sse(client) -> None:
    """Test GET /mcp returns SSE stream."""
    response = client.get("/mcp")
    assert response.status_code == 200
    assert "text/event-stream" in response.headers["content-type"]
    assert "mcp-session-id" in response.headers


def test_health_endpoint(client) -> None:
    """Test /health endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
