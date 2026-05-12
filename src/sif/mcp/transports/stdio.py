"""MCP stdio transport implementation."""

from __future__ import annotations

import asyncio
import json
import sys
from typing import Any, TextIO

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


class StdioTransport:
    """MCP transport over stdin/stdout."""

    def __init__(
        self,
        server: MCPServer,
        stdin: TextIO | None = None,
        stdout: TextIO | None = None,
    ) -> None:
        """Initialize stdio transport."""
        self.server = server
        self.stdin = stdin or sys.stdin
        self.stdout = stdout or sys.stdout
        self._running = False
        self._read_lock = asyncio.Lock()
        self._write_lock = asyncio.Lock()

    async def _read_message(self) -> dict[str, Any] | None:
        """Read a JSON-RPC message from stdin."""
        async with self._read_lock:
            loop = asyncio.get_event_loop()
            line = await loop.run_in_executor(None, self.stdin.readline)

        if not line:
            return None

        stripped = line.strip()
        if not stripped:
            return None

        try:
            return json.loads(stripped)
        except json.JSONDecodeError as e:
            logger.warning("JSON parse error: %s", e)
            return {
                "jsonrpc": "2.0",
                "id": None,
                "error": {
                    "code": MCPErrorCode.PARSE_ERROR,
                    "message": f"Parse error: {e}",
                },
            }

    async def _write_message(self, message: dict[str, Any]) -> None:
        """Write a JSON-RPC message to stdout."""
        async with self._write_lock:
            loop = asyncio.get_event_loop()
            data = json.dumps(message, ensure_ascii=False) + "\n"
            await loop.run_in_executor(None, self.stdout.write, data)
            await loop.run_in_executor(None, self.stdout.flush)

    async def _process_message(
        self,
        message: dict[str, Any],
    ) -> dict[str, Any] | None:
        """Process a single JSON-RPC message."""
        if "id" not in message:
            try:
                notification = JsonRpcNotification(**message)
                await self.server.handle_notification(notification)
            except Exception:
                logger.exception("Notification handling error")
            return None

        try:
            request = JsonRpcRequest(**message)
            response = await self.server.handle_request(request)
        except Exception as e:
            logger.exception("Request handling error")
            req_id = message.get("id")
            response = create_error_response(
                req_id,
                MCPErrorCode.INTERNAL_ERROR,
                f"Internal error: {e}",
            )

        return response.model_dump(exclude_none=True)

    async def run(self) -> None:
        """Run the stdio transport loop."""
        self._running = True
        logger.info("Stdio transport started")

        try:
            while self._running:
                message = await self._read_message()
                if message is None:
                    break

                response = await self._process_message(message)
                if response is not None:
                    await self._write_message(response)
        except asyncio.CancelledError:
            logger.info("Transport cancelled")
            raise
        except Exception:
            logger.exception("Transport error")
        finally:
            self._running = False
            logger.info("Stdio transport stopped")


async def run_stdio_server(db_path: str) -> None:
    """Run MCP server in stdio mode."""
    backend = SearchBackend(db_path)
    server = MCPServer(backend)
    server.register_tools(create_default_tools(backend))
    transport = StdioTransport(server)
    await transport.run()


def run_stdio_server_sync(db_path: str) -> None:
    """Synchronous wrapper for run_stdio_server."""
    asyncio.run(run_stdio_server(db_path))
