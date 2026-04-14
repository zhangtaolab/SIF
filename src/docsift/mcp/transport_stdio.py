"""
MCP Stdio Transport

This module implements the stdio transport for MCP, suitable for
use with Claude Desktop and other MCP clients that communicate
via standard input/output.

The transport uses line-delimited JSON-RPC messages.
"""

import sys
import json
import logging
import asyncio
from typing import Optional, TextIO
from contextlib import asynccontextmanager

from .protocol import JsonRpcRequest, JsonRpcResponse, JsonRpcNotification
from .server import MCPServer, create_server, ServerConfig

logger = logging.getLogger(__name__)


# ============================================================================
# Stdio Transport
# ============================================================================

class StdioTransport:
    """
    Stdio transport for MCP server.
    
    Reads JSON-RPC messages from stdin and writes responses to stdout.
    Uses line-delimited JSON format.
    
    Example usage:
        transport = StdioTransport()
        await transport.run()
    """
    
    def __init__(
        self,
        server: Optional[MCPServer] = None,
        stdin: Optional[TextIO] = None,
        stdout: Optional[TextIO] = None,
        encoding: str = "utf-8"
    ):
        self.server = server or create_server()
        self.stdin = stdin or sys.stdin
        self.stdout = stdout or sys.stdout
        self.encoding = encoding
        self._running = False
        self._read_lock = asyncio.Lock()
        self._write_lock = asyncio.Lock()
    
    # -------------------------------------------------------------------------
    # Message I/O
    # -------------------------------------------------------------------------
    
    async def _read_message(self) -> Optional[dict]:
        """
        Read a single JSON-RPC message from stdin.
        
        Returns:
            Parsed JSON object or None if EOF
        """
        async with self._read_lock:
            # Read line from stdin (in executor to avoid blocking)
            loop = asyncio.get_event_loop()
            try:
                line = await loop.run_in_executor(None, self.stdin.readline)
            except Exception as e:
                logger.error(f"Error reading from stdin: {e}")
                return None
            
            if not line:
                # EOF reached
                logger.info("EOF reached on stdin")
                return None
            
            line = line.strip()
            if not line:
                # Empty line, skip
                return None
            
            try:
                message = json.loads(line)
                logger.debug(f"Received: {line[:200]}...")
                return message
            except json.JSONDecodeError as e:
                logger.error(f"Invalid JSON: {e}, line: {line[:100]}")
                # Return error response
                return {
                    "jsonrpc": "2.0",
                    "id": None,
                    "error": {
                        "code": -32700,
                        "message": f"Parse error: {e}"
                    }
                }
    
    async def _write_message(self, message: dict) -> None:
        """
        Write a JSON-RPC message to stdout.
        
        Args:
            message: The message to write
        """
        async with self._write_lock:
            try:
                line = json.dumps(message, ensure_ascii=False)
                logger.debug(f"Sending: {line[:200]}...")
                
                # Write in executor to avoid blocking
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(None, self._write_sync, line)
                
            except Exception as e:
                logger.error(f"Error writing to stdout: {e}")
    
    def _write_sync(self, line: str) -> None:
        """Synchronous write to stdout."""
        self.stdout.write(line + "\n")
        self.stdout.flush()
    
    # -------------------------------------------------------------------------
    # Message Processing
    # -------------------------------------------------------------------------
    
    async def _process_message(self, message: dict) -> Optional[dict]:
        """
        Process a single message.
        
        Args:
            message: The parsed JSON message
            
        Returns:
            Response dict if it's a request, None for notifications
        """
        # Validate JSON-RPC version
        if message.get("jsonrpc") != "2.0":
            return {
                "jsonrpc": "2.0",
                "id": message.get("id"),
                "error": {
                    "code": -32600,
                    "message": "Invalid Request: jsonrpc must be '2.0'"
                }
            }
        
        # Check if it's a request or notification
        msg_id = message.get("id")
        method = message.get("method")
        
        if method is None:
            # This is a response (shouldn't happen in stdio transport)
            logger.warning("Received response message, ignoring")
            return None
        
        if msg_id is None:
            # This is a notification
            notification = JsonRpcNotification(
                jsonrpc="2.0",
                method=method,
                params=message.get("params")
            )
            await self.server.handle_notification(notification)
            return None
        else:
            # This is a request
            request = JsonRpcRequest(
                jsonrpc="2.0",
                id=msg_id,
                method=method,
                params=message.get("params")
            )
            response = await self.server.handle_request(request)
            return response.model_dump(exclude_none=True)
    
    # -------------------------------------------------------------------------
    # Main Loop
    # -------------------------------------------------------------------------
    
    async def run(self) -> None:
        """
        Run the stdio transport main loop.
        
        Continuously reads messages from stdin and processes them
        until EOF is reached or the transport is stopped.
        """
        logger.info("Starting stdio transport")
        self._running = True
        
        try:
            while self._running:
                # Read message
                message = await self._read_message()
                
                if message is None:
                    # EOF or error
                    break
                
                # Process message
                try:
                    response = await self._process_message(message)
                    
                    # Send response if it's a request (not notification)
                    if response is not None:
                        await self._write_message(response)
                        
                except Exception as e:
                    logger.exception("Error processing message")
                    # Send error response if we have an ID
                    msg_id = message.get("id")
                    if msg_id is not None:
                        error_response = {
                            "jsonrpc": "2.0",
                            "id": msg_id,
                            "error": {
                                "code": -32603,
                                "message": f"Internal error: {str(e)}"
                            }
                        }
                        await self._write_message(error_response)
        
        except asyncio.CancelledError:
            logger.info("Transport cancelled")
            raise
        
        finally:
            self._running = False
            logger.info("Stdio transport stopped")
    
    def stop(self) -> None:
        """Stop the transport."""
        logger.info("Stopping stdio transport")
        self._running = False
    
    async def shutdown(self) -> None:
        """Shutdown the transport and server."""
        self.stop()
        await self.server.shutdown()


# ============================================================================
# Context Manager
# ============================================================================

@asynccontextmanager
async def stdio_transport(
    server: Optional[MCPServer] = None,
    config: Optional[ServerConfig] = None
):
    """
    Async context manager for stdio transport.
    
    Example:
        async with stdio_transport() as transport:
            await transport.run()
    
    Args:
        server: Optional MCPServer instance
        config: Optional server configuration
        
    Yields:
        StdioTransport instance
    """
    if server is None:
        server = create_server(config=config)
    
    transport = StdioTransport(server=server)
    try:
        yield transport
    finally:
        await transport.shutdown()


# ============================================================================
# Main Entry Point
# ============================================================================

async def main():
    """Main entry point for stdio transport."""
    # Setup logging to stderr (don't pollute stdout)
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        stream=sys.stderr
    )
    
    logger.info("Starting DocSift MCP Server (stdio mode)")
    
    async with stdio_transport() as transport:
        await transport.run()
    
    logger.info("DocSift MCP Server stopped")


def run_stdio():
    """Run the stdio transport (synchronous entry point)."""
    asyncio.run(main())


if __name__ == "__main__":
    run_stdio()
