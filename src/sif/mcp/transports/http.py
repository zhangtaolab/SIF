"""MCP HTTP transport with FastAPI and Streamable HTTP."""

from __future__ import annotations

import asyncio
import json
import uuid
from typing import Any


try:
    from fastapi import FastAPI, Request, Response
    from fastapi.middleware.cors import CORSMiddleware
    from starlette.responses import JSONResponse, StreamingResponse
except ImportError:
    FastAPI = None  # type: ignore[misc,assignment]
    Request = None  # type: ignore[misc,assignment]
    Response = None  # type: ignore[misc,assignment]
    CORSMiddleware = None  # type: ignore[misc,assignment]
    JSONResponse = None  # type: ignore[misc,assignment]
    StreamingResponse = None  # type: ignore[misc,assignment]

from sif.mcp.backend import SearchBackend
from sif.mcp.handlers import create_default_tools
from sif.mcp.protocol import (
    JsonRpcNotification,
    JsonRpcRequest,
    MCPErrorCode,
    create_error_response,
)
from sif.mcp.server import MCPServer
from sif.utils.logging import get_logger


logger = get_logger(__name__)

DEFAULT_CORS_ORIGINS = ["http://localhost:3000", "http://127.0.0.1:3000"]
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 3000

_sessions: dict[str, Any] = {}


def _generate_session_id() -> str:
    """Generate a new session ID."""
    return uuid.uuid4().hex


def _get_session_id(request_headers: dict[str, str]) -> str:
    """Get or create session ID from request headers."""
    session_id = request_headers.get("mcp-session-id")
    if session_id and session_id in _sessions:
        return session_id
    new_id = _generate_session_id()
    _sessions[new_id] = {}
    return new_id


async def _mcp_post_handler(
    request: Any,
    server: MCPServer,
) -> Any:
    """Handle POST /mcp requests."""
    session_id = _get_session_id(dict(request.headers))

    try:
        body = await request.json()
        msg_id = body.get("id")
    except Exception as e:
        return JSONResponse(
            status_code=400,
            content=create_error_response(
                None,
                MCPErrorCode.INVALID_REQUEST,
                f"Invalid request: {e}",
            ).model_dump(exclude_none=True),
            headers={"MCP-Session-Id": session_id},
        )

    if msg_id is None:
        try:
            notification = JsonRpcNotification(**body)
            await server.handle_notification(notification)
        except Exception:
            logger.exception("Notification handling error")
        return JSONResponse(
            status_code=202,
            content={},
            headers={"MCP-Session-Id": session_id},
        )

    try:
        rpc_request = JsonRpcRequest(**body)
        response = await server.handle_request(rpc_request)
    except Exception as e:
        logger.exception("Request handling error")
        response = create_error_response(
            msg_id,
            MCPErrorCode.INTERNAL_ERROR,
            f"Internal error: {e}",
        )

    return JSONResponse(
        content=response.model_dump(exclude_none=True),
        headers={"MCP-Session-Id": session_id},
    )


async def _mcp_get_handler(
    request: Any,
    ping_interval: float = 30,
    max_events: int | None = None,
) -> Any:
    """Handle GET /mcp SSE requests."""
    session_id = _get_session_id(dict(request.headers))

    async def event_generator() -> Any:
        count = 0
        while not await request.is_disconnected():
            if max_events is not None and count >= max_events:
                break
            yield f"data: {json.dumps({'ping': True})}\n\n"
            count += 1
            await asyncio.sleep(ping_interval)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"MCP-Session-Id": session_id},
    )


def create_app(
    server: MCPServer,
    cors_origins: list[str] | None = None,
    sse_ping_interval: float = 30,
    sse_max_events: int | None = None,
) -> Any:
    """Create FastAPI app for MCP HTTP transport."""
    if FastAPI is None:
        raise ImportError("FastAPI is required for HTTP transport")

    origins = cors_origins if cors_origins is not None else DEFAULT_CORS_ORIGINS

    app = FastAPI()

    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.middleware("http")
    async def validate_origin(request: Request, call_next: Any) -> Response:
        origin = request.headers.get("origin")
        if origin and origin not in origins:
            return JSONResponse(
                status_code=403,
                content={"error": "Origin not allowed"},
            )
        return await call_next(request)

    @app.post("/mcp")
    async def mcp_post(req: Request) -> Response:
        return await _mcp_post_handler(req, server)

    @app.get("/mcp")
    async def mcp_get(req: Request) -> Response:
        return await _mcp_get_handler(
            req,
            ping_interval=sse_ping_interval,
            max_events=sse_max_events,
        )

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


class HTTPTransport:
    """MCP HTTP transport using FastAPI."""

    def __init__(
        self,
        server: MCPServer,
        host: str = DEFAULT_HOST,
        port: int = DEFAULT_PORT,
        cors_origins: list[str] | None = None,
    ) -> None:
        """Initialize HTTP transport."""
        self.server = server
        self.host = host
        self.port = port
        self.cors_origins = cors_origins

    def run(self) -> None:
        """Run the HTTP server."""
        import uvicorn  # noqa: PLC0415

        app = create_app(self.server, self.cors_origins)
        uvicorn.run(app, host=self.host, port=self.port, log_level="info")


def run_http_server(
    db_path: str,
    host: str = DEFAULT_HOST,
    port: int = DEFAULT_PORT,
    cors_origins: list[str] | None = None,
) -> None:
    """Run MCP server in HTTP mode."""
    backend = SearchBackend(db_path)
    server = MCPServer(backend)
    server.register_tools(create_default_tools(backend))
    transport = HTTPTransport(server, host=host, port=port, cors_origins=cors_origins)
    transport.run()
