"""MCP server implementation."""

from sif.mcp_server.transport import Transport
from sif.utils.logging import get_logger


logger = get_logger(__name__)


class MCPServer:
    """Model Context Protocol server for SIF.

    Provides MCP-compliant endpoints for integration with
    AI assistants and other MCP-compatible tools.

    Supports both stdio and HTTP transports.
    """

    def __init__(
        self,
        transport: Transport,
        # tool_handlers: list[ToolHandler] | None = None,
        # resource_handlers: list[ResourceHandler] | None = None,
    ) -> None:
        """Initialize MCP server.

        Args:
            transport: Transport layer (stdio or HTTP)
            tool_handlers: Tool request handlers
            resource_handlers: Resource request handlers
        """
        self._transport = transport
        # self._tool_handlers = tool_handlers or []
        # self._resource_handlers = resource_handlers or []
        self._running = False

    def start(self) -> None:
        """Start the MCP server."""
        logger.info("Starting MCP server")
        self._running = True

        try:
            self._transport.start()
        except KeyboardInterrupt:
            logger.info("Received interrupt signal")
        finally:
            self.stop()

    def stop(self) -> None:
        """Stop the MCP server."""
        logger.info("Stopping MCP server")
        self._running = False
        self._transport.stop()

    @property
    def is_running(self) -> bool:
        """Check if server is running."""
        return self._running
