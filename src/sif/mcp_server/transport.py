"""MCP transport implementations."""

import sys
from abc import ABC, abstractmethod
from typing import Any

from sif.utils.logging import get_logger


logger = get_logger(__name__)


class Transport(ABC):
    """Abstract base class for MCP transports."""

    @abstractmethod
    def start(self) -> None:
        """Start the transport."""
        ...

    @abstractmethod
    def stop(self) -> None:
        """Stop the transport."""
        ...

    @abstractmethod
    def send(self, message: dict[str, Any]) -> None:
        """Send a message."""
        ...

    @abstractmethod
    def receive(self) -> dict[str, Any] | None:
        """Receive a message."""
        ...


class StdioTransport(Transport):
    """stdio transport for MCP.

    Uses standard input/output for communication.
    Suitable for CLI integration and local tools.
    """

    def __init__(self) -> None:
        """Initialize stdio transport."""
        self._running = False

    def start(self) -> None:
        """Start stdio transport."""
        logger.info("Starting stdio transport")
        self._running = True

        # Send initialization message
        self.send(
            {
                "jsonrpc": "2.0",
                "method": "initialize",
                "params": {
                    "protocolVersion": "1.0",
                    "capabilities": {},
                },
            }
        )

        # Main loop
        while self._running:
            try:
                message = self.receive()
                if message:
                    self._handle_message(message)
            except EOFError:
                break
            except Exception as e:
                logger.error(f"Error handling message: {e}")

    def stop(self) -> None:
        """Stop stdio transport."""
        logger.info("Stopping stdio transport")
        self._running = False

    def send(self, message: dict[str, Any]) -> None:
        """Send a message via stdout."""
        import json  # noqa: PLC0415

        json_str = json.dumps(message)
        print(json_str, flush=True)

    def receive(self) -> dict[str, Any] | None:
        """Receive a message from stdin."""
        import json  # noqa: PLC0415

        try:
            line = sys.stdin.readline()
            if not line:
                raise EOFError()
            return json.loads(line)
        except json.JSONDecodeError:
            logger.error("Invalid JSON received")
            return None

    def _handle_message(self, message: dict[str, Any]) -> None:
        """Handle an incoming message."""
        method = message.get("method")

        if method == "tools/list":
            self._handle_tools_list(message)
        elif method == "tools/call":
            self._handle_tool_call(message)
        elif method == "resources/list":
            self._handle_resources_list(message)
        else:
            logger.warning(f"Unknown method: {method}")

    def _handle_tools_list(self, message: dict[str, Any]) -> None:
        """Handle tools/list request."""
        self.send(
            {
                "jsonrpc": "2.0",
                "id": message.get("id"),
                "result": {
                    "tools": [
                        {
                            "name": "search",
                            "description": "Search indexed documents",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "query": {"type": "string"},
                                    "collection": {"type": "string"},
                                },
                                "required": ["query"],
                            },
                        },
                    ],
                },
            }
        )

    def _handle_tool_call(self, message: dict[str, Any]) -> None:
        """Handle tools/call request."""
        params = message.get("params", {})
        tool_name = params.get("name")

        # Placeholder: actual implementation would call the tool
        self.send(
            {
                "jsonrpc": "2.0",
                "id": message.get("id"),
                "result": {
                    "content": [
                        {"type": "text", "text": f"Tool '{tool_name}' called"},
                    ],
                },
            }
        )

    def _handle_resources_list(self, message: dict[str, Any]) -> None:
        """Handle resources/list request."""
        self.send(
            {
                "jsonrpc": "2.0",
                "id": message.get("id"),
                "result": {
                    "resources": [],
                },
            }
        )


class HTTPTransport(Transport):
    """HTTP transport for MCP.

    Uses HTTP/SSE for communication.
    Suitable for remote access and web integration.
    """

    def __init__(
        self,
        host: str = "127.0.0.1",
        port: int = 8080,
    ) -> None:
        """Initialize HTTP transport.

        Args:
            host: Server host
            port: Server port
        """
        self._host = host
        self._port = port
        self._server: Any | None = None

    def start(self) -> None:
        """Start HTTP transport."""
        import uvicorn  # noqa: PLC0415
        from fastapi import FastAPI  # noqa: PLC0415

        logger.info(f"Starting HTTP transport on {self._host}:{self._port}")

        app = FastAPI(title="SIF MCP Server")

        @app.get("/mcp/v1/tools")
        async def list_tools() -> dict:
            return {"tools": []}

        @app.post("/mcp/v1/tools/{tool_name}")
        async def call_tool(tool_name: str, params: dict) -> dict:
            return {"result": f"Tool '{tool_name}' called with {params}"}

        uvicorn.run(app, host=self._host, port=self._port)

    def stop(self) -> None:
        """Stop HTTP transport."""
        logger.info("Stopping HTTP transport")

    def send(self, message: dict[str, Any]) -> None:
        """Send a message (not applicable for HTTP)."""
        pass

    def receive(self) -> dict[str, Any] | None:
        """Receive a message (not applicable for HTTP)."""
        return None
