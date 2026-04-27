"""MCP request handlers."""

from abc import ABC, abstractmethod
from typing import Any

from sif.utils.logging import get_logger

logger = get_logger(__name__)


class ToolHandler(ABC):
    """Abstract base class for MCP tool handlers."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Tool name."""
        ...

    @property
    @abstractmethod
    def description(self) -> str:
        """Tool description."""
        ...

    @property
    @abstractmethod
    def input_schema(self) -> dict[str, Any]:
        """JSON schema for tool input."""
        ...

    @abstractmethod
    def handle(self, params: dict[str, Any]) -> dict[str, Any]:
        """Handle a tool call.

        Args:
            params: Tool parameters

        Returns:
            Tool result
        """
        ...


class ResourceHandler(ABC):
    """Abstract base class for MCP resource handlers."""

    @property
    @abstractmethod
    def uri(self) -> str:
        """Resource URI."""
        ...

    @property
    @abstractmethod
    def mime_type(self) -> str:
        """Resource MIME type."""
        ...

    @abstractmethod
    def handle(self) -> dict[str, Any]:
        """Handle a resource request.

        Returns:
            Resource content
        """
        ...
