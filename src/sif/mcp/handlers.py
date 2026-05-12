"""MCP ToolHandler ABC."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from sif.mcp.protocol import ToolsCallResult
from sif.utils.logging import get_logger

from .backend import SearchBackend


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
    async def handle(
        self,
        params: dict[str, Any],
        backend: SearchBackend,
    ) -> ToolsCallResult:
        """Handle a tool call.

        Args:
            params: Tool parameters
            backend: Search backend instance

        Returns:
            Tool result
        """
        ...
