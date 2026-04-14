"""
MCP HTTP Transport

This module implements the HTTP transport for MCP using FastAPI.
Supports both JSON-RPC POST endpoints and Server-Sent Events (SSE)
for real-time communication.

Endpoints:
- POST /mcp/v1/messages - JSON-RPC message endpoint
- GET /mcp/v1/sse - SSE endpoint for server-to-client streaming
- GET /health - Health check endpoint
"""

import json
import logging
import asyncio
from typing import Optional, AsyncGenerator, Any
from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import FastAPI, Request, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from .protocol import (
    JsonRpcRequest, JsonRpcResponse, JsonRpcNotification,
    create_error_response, MCPErrorCode
)
from .server import MCPServer, create_server, ServerConfig, ServerState
from .tools import get_tool_registry

logger = logging.getLogger(__name__)


# ============================================================================
# Pydantic Models
# ============================================================================

class MessageRequest(BaseModel):
    """Request body for JSON-RPC messages."""
    jsonrpc: str = "2.0"
    id: Optional[str | int] = None
    method: Optional[str] = None
    params: Optional[dict[str, Any]] = None
    result: Optional[Any] = None
    error: Optional[dict[str, Any]] = None


class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    server: dict[str, str]
    timestamp: str


# ============================================================================
# SSE Manager
# ============================================================================

class SSEManager:
    """
    Manager for Server-Sent Events connections.
    
    Handles multiple client connections and broadcasts messages
    to all connected clients.
    """
    
    def __init__(self):
        self._connections: list[asyncio.Queue] = []
        self._lock = asyncio.Lock()
    
    async def connect(self) -> asyncio.Queue:
        """
        Register a new SSE connection.
        
        Returns:
            Queue for receiving SSE messages
        """
        queue = asyncio.Queue()
        async with self._lock:
            self._connections.append(queue)
        logger.info(f"SSE client connected. Total connections: {len(self._connections)}")
        return queue
    
    async def disconnect(self, queue: asyncio.Queue) -> None:
        """Unregister an SSE connection."""
        async with self._lock:
            if queue in self._connections:
                self._connections.remove(queue)
        logger.info(f"SSE client disconnected. Total connections: {len(self._connections)}")
    
    async def broadcast(self, message: dict[str, Any]) -> None:
        """
        Broadcast a message to all connected clients.
        
        Args:
            message: The message to broadcast
        """
        disconnected = []
        async with self._lock:
            for queue in self._connections:
                try:
                    await queue.put(message)
                except Exception as e:
                    logger.error(f"Error broadcasting to queue: {e}")
                    disconnected.append(queue)
            
            # Remove disconnected clients
            for queue in disconnected:
                if queue in self._connections:
                    self._connections.remove(queue)
    
    async def send_to_client(self, queue: asyncio.Queue, message: dict[str, Any]) -> None:
        """
        Send a message to a specific client.
        
        Args:
            queue: The client's queue
            message: The message to send
        """
        try:
            await queue.put(message)
        except Exception as e:
            logger.error(f"Error sending to client: {e}")


# ============================================================================
# HTTP Transport
# ============================================================================

class HTTPTransport:
    """
    HTTP transport for MCP server using FastAPI.
    
    Provides RESTful endpoints for MCP protocol communication.
    """
    
    def __init__(
        self,
        server: Optional[MCPServer] = None,
        config: Optional[ServerConfig] = None,
        cors_origins: Optional[list[str]] = None
    ):
        self.server = server or create_server(config=config)
        self.sse_manager = SSEManager()
        self.cors_origins = cors_origins or ["*"]
        self.app = self._create_app()
    
    def _create_app(self) -> FastAPI:
        """Create and configure FastAPI application."""
        app = FastAPI(
            title="DocSift MCP Server",
            description="Model Context Protocol server for DocSift",
            version="1.0.0",
            docs_url="/docs",
            redoc_url="/redoc"
        )
        
        # Add CORS middleware
        app.add_middleware(
            CORSMiddleware,
            allow_origins=self.cors_origins,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
        
        # Register routes
        self._register_routes(app)
        
        return app
    
    def _register_routes(self, app: FastAPI) -> None:
        """Register FastAPI routes."""
        
        @app.get("/health", response_model=HealthResponse)
        async def health_check():
            """Health check endpoint."""
            return HealthResponse(
                status="healthy" if self.server.state != ServerState.SHUTDOWN else "shutdown",
                server=self.server.get_server_info(),
                timestamp=datetime.utcnow().isoformat()
            )
        
        @app.get("/mcp/v1/sse")
        async def sse_endpoint(request: Request):
            """
            Server-Sent Events endpoint.
            
            Streams server-to-client messages in real-time.
            """
            queue = await self.sse_manager.connect()
            
            async def event_generator() -> AsyncGenerator[str, None]:
                try:
                    # Send initial connection message
                    yield f"event: connected\ndata: {json.dumps({'message': 'Connected to MCP server'})}\n\n"
                    
                    while True:
                        # Check if client disconnected
                        if await request.is_disconnected():
                            break
                        
                        # Wait for message with timeout
                        try:
                            message = await asyncio.wait_for(queue.get(), timeout=30.0)
                            data = json.dumps(message)
                            yield f"event: message\ndata: {data}\n\n"
                        except asyncio.TimeoutError:
                            # Send keepalive
                            yield f"event: ping\ndata: {json.dumps({'time': datetime.utcnow().isoformat()})}\n\n"
                            
                except asyncio.CancelledError:
                    logger.info("SSE connection cancelled")
                except Exception as e:
                    logger.error(f"SSE error: {e}")
                finally:
                    await self.sse_manager.disconnect(queue)
            
            return StreamingResponse(
                event_generator(),
                media_type="text/event-stream",
                headers={
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                    "X-Accel-Buffering": "no"  # Disable nginx buffering
                }
            )
        
        @app.post("/mcp/v1/messages")
        async def messages_endpoint(request: MessageRequest):
            """
            JSON-RPC message endpoint.
            
            Accepts JSON-RPC requests and returns responses.
            """
            # Validate JSON-RPC version
            if request.jsonrpc != "2.0":
                return JSONResponse(
                    status_code=400,
                    content=create_error_response(
                        request.id,
                        MCPErrorCode.INVALID_REQUEST,
                        "Invalid JSON-RPC version"
                    ).model_dump()
                )
            
            # Check if it's a request or notification
            if request.method is None:
                return JSONResponse(
                    status_code=400,
                    content=create_error_response(
                        request.id,
                        MCPErrorCode.INVALID_REQUEST,
                        "Missing method field"
                    ).model_dump()
                )
            
            if request.id is None:
                # Handle notification
                notification = JsonRpcNotification(
                    jsonrpc="2.0",
                    method=request.method,
                    params=request.params
                )
                await self.server.handle_notification(notification)
                return JSONResponse(status_code=202, content={})
            
            else:
                # Handle request
                rpc_request = JsonRpcRequest(
                    jsonrpc="2.0",
                    id=request.id,
                    method=request.method,
                    params=request.params
                )
                response = await self.server.handle_request(rpc_request)
                return JSONResponse(content=response.model_dump(exclude_none=True))
        
        @app.post("/mcp/v1/batch")
        async def batch_endpoint(requests: list[MessageRequest]):
            """
            Batch JSON-RPC message endpoint.
            
            Processes multiple JSON-RPC requests in a single call.
            """
            responses = []
            
            for request in requests:
                # Skip notifications in batch responses
                if request.id is None:
                    notification = JsonRpcNotification(
                        jsonrpc="2.0",
                        method=request.method,
                        params=request.params
                    )
                    await self.server.handle_notification(notification)
                else:
                    rpc_request = JsonRpcRequest(
                        jsonrpc="2.0",
                        id=request.id,
                        method=request.method,
                        params=request.params
                    )
                    response = await self.server.handle_request(rpc_request)
                    responses.append(response.model_dump(exclude_none=True))
            
            return JSONResponse(content=responses)
        
        @app.get("/mcp/v1/tools")
        async def list_tools():
            """List available tools (non-standard endpoint for convenience)."""
            tools = self.server.tool_registry.list_tools()
            return JSONResponse(content={
                "tools": [tool.model_dump() for tool in tools]
            })
        
        @app.get("/mcp/v1/status")
        async def server_status():
            """Get server status (non-standard endpoint for convenience)."""
            status = await self.server.tool_registry.call_tool("status", {})
            return JSONResponse(content=status)
    
    async def broadcast(self, message: dict[str, Any]) -> None:
        """Broadcast a message to all SSE clients."""
        await self.sse_manager.broadcast(message)
    
    async def shutdown(self) -> None:
        """Shutdown the transport and server."""
        await self.server.shutdown()


# ============================================================================
# FastAPI App Factory
# ============================================================================

_http_transport: Optional[HTTPTransport] = None


def create_http_app(
    server: Optional[MCPServer] = None,
    config: Optional[ServerConfig] = None,
    cors_origins: Optional[list[str]] = None
) -> FastAPI:
    """
    Create FastAPI application for MCP HTTP transport.
    
    Args:
        server: Optional MCPServer instance
        config: Optional server configuration
        cors_origins: Optional CORS allowed origins
        
    Returns:
        Configured FastAPI application
    """
    global _http_transport
    _http_transport = HTTPTransport(
        server=server,
        config=config,
        cors_origins=cors_origins
    )
    return _http_transport.app


def get_http_transport() -> Optional[HTTPTransport]:
    """Get the global HTTP transport instance."""
    return _http_transport


# ============================================================================
# Uvicorn Runner
# ============================================================================

async def run_http_server(
    host: str = "0.0.0.0",
    port: int = 8080,
    server: Optional[MCPServer] = None,
    config: Optional[ServerConfig] = None,
    cors_origins: Optional[list[str]] = None,
    log_level: str = "info"
):
    """
    Run the HTTP server using Uvicorn.
    
    Args:
        host: Host to bind to
        port: Port to bind to
        server: Optional MCPServer instance
        config: Optional server configuration
        cors_origins: Optional CORS allowed origins
        log_level: Uvicorn log level
    """
    import uvicorn
    
    app = create_http_app(
        server=server,
        config=config,
        cors_origins=cors_origins
    )
    
    config = uvicorn.Config(
        app,
        host=host,
        port=port,
        log_level=log_level,
        access_log=True
    )
    
    server_instance = uvicorn.Server(config)
    await server_instance.serve()


# ============================================================================
# Main Entry Point
# ============================================================================

def main():
    """Main entry point for HTTP transport."""
    import argparse
    
    parser = argparse.ArgumentParser(description="DocSift MCP HTTP Server")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind to")
    parser.add_argument("--port", type=int, default=8080, help="Port to bind to")
    parser.add_argument("--log-level", default="info", help="Log level")
    parser.add_argument("--cors-origins", nargs="*", default=["*"], help="CORS allowed origins")
    
    args = parser.parse_args()
    
    # Setup logging
    logging.basicConfig(
        level=getattr(logging, args.log_level.upper()),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    logger.info(f"Starting DocSift MCP HTTP Server on {args.host}:{args.port}")
    
    asyncio.run(run_http_server(
        host=args.host,
        port=args.port,
        cors_origins=args.cors_origins,
        log_level=args.log_level
    ))


if __name__ == "__main__":
    main()
