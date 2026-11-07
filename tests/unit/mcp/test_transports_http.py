"""Tests for MCP HTTP transport."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from sif.mcp.transports import http
from sif.mcp.transports.http import (
    DEFAULT_CORS_ORIGINS,
    DEFAULT_HOST,
    create_app,
)


@pytest.fixture(autouse=True)
def clear_http_sessions():
    """Restore the process-global session registry around every HTTP test."""
    http._sessions.clear()
    yield
    http._sessions.clear()


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
            },
        ),
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
            },
        ),
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
            },
        ),
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
        content="not json",
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
            },
        ),
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


class TestHTTPTransportBranches:
    """Session, protocol error, SSE, and startup branches stay in memory."""

    def test_session_reuse_updates_lru_access_and_evicts_oldest(self) -> None:
        """A small session limit evicts the least recently reused session."""
        with (
            patch.object(http, "SESSION_MAX_COUNT", 1),
            patch.object(http.time, "time", side_effect=[1.0, 2.0, 3.0]),
            patch.object(http, "_generate_session_id", side_effect=["new-a", "new-b"]),
        ):
            first = http._get_session_id({})
            reused = http._get_session_id({"mcp-session-id": first})
            second = http._get_session_id({})

        assert first == "new-a"
        assert reused == first
        assert second == "new-b"
        assert list(http._sessions) == ["new-b"]
        assert http._sessions["new-b"] == {"created": 3.0, "last_accessed": 3.0}

    @pytest.mark.asyncio
    async def test_invalid_json_returns_session_aware_bad_request(self) -> None:
        """A request JSON decoding failure is a 400 invalid-request response."""
        request = MagicMock()
        request.headers = {"mcp-session-id": "existing"}
        request.json = AsyncMock(side_effect=ValueError("malformed"))
        http._sessions["existing"] = {"created": 1.0, "last_accessed": 1.0}

        response = await http._mcp_post_handler(request, MagicMock())
        payload = response.body.decode()

        assert response.status_code == 400
        assert response.headers["mcp-session-id"] == "existing"
        assert '"code":-32600' in payload
        assert "Invalid request: malformed" in payload

    @pytest.mark.asyncio
    async def test_notification_error_is_contained_and_accepted(self) -> None:
        """Notification failures do not become JSON-RPC responses."""
        request = MagicMock()
        request.headers = {}
        request.json = AsyncMock(return_value={"jsonrpc": "2.0", "method": "bad"})
        server = MagicMock()
        server.handle_notification = AsyncMock(side_effect=RuntimeError("notification failed"))

        response = await http._mcp_post_handler(request, server)

        assert response.status_code == 202
        assert response.body == b"{}"

    @pytest.mark.asyncio
    async def test_request_exception_becomes_internal_error(self) -> None:
        """Server dispatch exceptions use the original request ID in an error."""
        request = MagicMock()
        request.headers = {}
        request.json = AsyncMock(return_value={"jsonrpc": "2.0", "id": 42, "method": "initialize"})
        server = MagicMock()
        server.handle_request = AsyncMock(side_effect=RuntimeError("dispatch failed"))

        response = await http._mcp_post_handler(request, server)
        payload = response.body.decode()

        assert response.status_code == 200
        assert '"id":42' in payload
        assert '"code":-32603' in payload
        assert "Internal error: dispatch failed" in payload

    @pytest.mark.asyncio
    async def test_sse_generator_stops_at_max_events(self) -> None:
        """The direct SSE helper yields only its configured number of pings."""
        request = MagicMock()
        request.headers = {}
        request.is_disconnected = AsyncMock(return_value=False)

        with patch.object(http.asyncio, "sleep", new=AsyncMock()) as sleep:
            response = await http._mcp_get_handler(request, ping_interval=0, max_events=2)
            events = [event async for event in response.body_iterator]

        assert events == [
            'event: ping\ndata: {"ping": true}\n\n',
            'event: ping\ndata: {"ping": true}\n\n',
        ]
        assert sleep.await_count == 2
        assert response.media_type == "text/event-stream"

    @pytest.mark.asyncio
    async def test_sse_generator_stops_when_disconnected(self) -> None:
        """A disconnected request ends the stream before emitting an event."""
        request = MagicMock()
        request.headers = {}
        request.is_disconnected = AsyncMock(return_value=True)

        response = await http._mcp_get_handler(request, max_events=2)

        assert [event async for event in response.body_iterator] == []

    def test_missing_fastapi_raises_helpful_import_error(self) -> None:
        """The optional-dependency guard names the required HTTP dependency."""
        with patch.object(http, "FastAPI", None):
            with pytest.raises(ImportError, match="FastAPI is required for HTTP transport"):
                http.create_app(MagicMock())

    def test_custom_cors_origins_allow_only_configured_origin(self) -> None:
        """Custom origins replace defaults for both middleware and preflight."""
        app = http.create_app(MagicMock(), cors_origins=["https://allowed.example"])

        with TestClient(app) as client:
            allowed = client.get("/health", headers={"Origin": "https://allowed.example"})
            rejected = client.get("/health", headers={"Origin": "http://localhost:3000"})

        assert allowed.status_code == 200
        assert allowed.headers["access-control-allow-origin"] == "https://allowed.example"
        assert rejected.status_code == 403
        assert rejected.json() == {"error": "Origin not allowed"}

    def test_transport_run_constructs_app_and_calls_uvicorn_without_listener(self) -> None:
        """Transport composition delegates to a patched uvicorn entry point."""
        server = MagicMock()
        app = MagicMock()
        transport = http.HTTPTransport(
            server,
            host="0.0.0.0",
            port=8765,
            cors_origins=["https://allowed.example"],
        )
        uvicorn = MagicMock()

        with (
            patch.dict("sys.modules", {"uvicorn": uvicorn}),
            patch.object(http, "create_app", return_value=app) as create,
        ):
            transport.run()

        create.assert_called_once_with(server, ["https://allowed.example"], lifespan=None)
        uvicorn.run.assert_called_once_with(app, host="0.0.0.0", port=8765, log_level="info")

    def test_run_http_server_composes_backend_tools_and_transport(self) -> None:
        """The HTTP convenience entry point wires all collaborators without running."""
        server = MagicMock()
        transport = MagicMock()
        tools = [MagicMock()]
        lifespan_cm = MagicMock()

        with (
            patch.object(http, "SearchBackend", return_value="backend") as backend,
            patch.object(http, "MCPServer", return_value=server) as server_type,
            patch.object(http, "create_default_tools", return_value=tools),
            patch.object(http, "HTTPTransport", return_value=transport) as transport_type,
            patch("sif.mcp.watch_host.mcp_watch_lifespan", return_value=lifespan_cm),
        ):
            http.run_http_server(
                "/tmp/sif-test.db",
                host="localhost",
                port=9999,
                cors_origins=["https://allowed.example"],
            )

        backend.assert_called_once_with("/tmp/sif-test.db")
        server_type.assert_called_once_with("backend")
        server.register_tools.assert_called_once_with(tools)
        transport_type.assert_called_once_with(
            server,
            host="localhost",
            port=9999,
            cors_origins=["https://allowed.example"],
            lifespan=lifespan_cm,
        )
        transport.run.assert_called_once_with()


class TestWatchLifespanThreading:
    """Lifespan parameter threading through create_app/HTTPTransport (13-03 D-01)."""

    def test_create_app_accepts_lifespan_running_it_around_requests(self) -> None:
        """create_app(server, lifespan=cm): start before the app serves, stop after."""
        events: list[str] = []

        @asynccontextmanager
        async def lifespan(app: Any) -> AsyncIterator[None]:
            events.append(f"start:{app is not None}")
            yield
            events.append("stop")

        app = create_app(MagicMock(), lifespan=lifespan)
        with TestClient(app) as client:
            assert events == ["start:True"]
            assert client.get("/health").status_code == 200
        assert events == ["start:True", "stop"]

    def test_create_app_without_lifespan_still_builds_and_serves_health(self) -> None:
        """Compatibility pin: existing create_app(server) call sites keep working."""
        app = create_app(MagicMock())
        with TestClient(app) as client:
            response = client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}

    def test_create_app_has_no_on_event_handlers(self) -> None:
        """Lifespan only — FastAPI forbids mixing on_event with lifespan."""
        app = create_app(MagicMock())
        assert app.router.on_startup == []
        assert app.router.on_shutdown == []

    def test_transport_run_forwards_lifespan_into_create_app(self) -> None:
        """HTTPTransport carries its lifespan parameter into create_app."""
        sentinel = MagicMock()
        transport = http.HTTPTransport(MagicMock(), lifespan=sentinel)

        with (
            patch.dict("sys.modules", {"uvicorn": MagicMock()}),
            patch.object(http, "create_app", return_value=MagicMock()) as create,
        ):
            transport.run()

        assert create.call_args.kwargs["lifespan"] is sentinel

    def test_mcp_watch_lifespan_boots_a_real_app(self, tmp_path) -> None:
        """Regression (CR-01): the lifespan ``run_http_server`` wires must be a
        factory (callable with the app) Starlette can execute. Exercised with
        the REAL mcp_watch_lifespan through create_app + TestClient — the old
        test mocked the lifespan itself and pinned the broken invoked-CM
        shape, hiding the startup TypeError that killed every HTTP-mode
        invocation. Only the start/stop collaborators are patched."""
        from sif.mcp import watch_host
        from sif.mcp.watch_host import mcp_watch_lifespan

        started: list[str] = []
        stopped: list[object] = []

        def _fake_start(db_path: str) -> None:
            started.append(db_path)
            return None

        def _fake_stop(watch: object) -> None:
            stopped.append(watch)

        db_path = str(tmp_path / "watch.db")
        with (
            patch.object(watch_host, "start_embedded_watch", side_effect=_fake_start),
            patch.object(watch_host, "stop_embedded_watch", side_effect=_fake_stop),
        ):
            app = create_app(MagicMock(), lifespan=mcp_watch_lifespan(db_path))
            with TestClient(app) as client:
                assert started == [db_path]
                assert stopped == []
                assert client.get("/health").status_code == 200

        assert stopped == [None]
