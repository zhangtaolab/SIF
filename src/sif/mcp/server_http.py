"""MCP HTTP server implementation."""

from __future__ import annotations

import json
from typing import Any, Dict

from sif.mcp.server import MCPServer
from sif.utils.logging import get_logger

logger = get_logger(__name__)


def run_http_server(
    index_path: str, host: str = "127.0.0.1", port: int = 3000, reload: bool = False
) -> None:
    """Run MCP server in HTTP mode using FastAPI."""
    try:
        from fastapi import FastAPI, Request
        from fastapi.responses import JSONResponse
        import uvicorn
    except ImportError:
        logger.error("FastAPI not installed. Install with: pip install fastapi uvicorn")
        raise

    app = FastAPI(title="DocSift MCP Server")
    server = MCPServer(index_path)

    @app.post("/mcp/v1/messages")
    async def handle_message(request: Request) -> JSONResponse:
        """Handle MCP message."""
        body = await request.json()
        response = server.handle_request(body)
        return JSONResponse(content=response)

    @app.get("/health")
    async def health() -> Dict[str, str]:
        """Health check endpoint."""
        return {"status": "ok"}

    @app.get("/")
    async def root() -> Dict[str, Any]:
        """Root endpoint."""
        return {
            "name": "DocSift MCP Server",
            "version": "0.1.0",
            "endpoints": [
                "/mcp/v1/messages",
                "/health",
            ],
        }

    logger.info(f"Starting HTTP server on {host}:{port}")
    uvicorn.run(app, host=host, port=port, reload=reload)
