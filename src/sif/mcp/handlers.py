"""MCP ToolHandler implementations."""

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from typing import Any, ClassVar

from sif.mcp.protocol import (
    GetInput,
    GetOutput,
    MultiGetInput,
    MultiGetOutput,
    QueryInput,
    QueryOutput,
    StatusOutput,
    ToolContentItem,
    ToolsCallResult,
)
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
        """Handle a tool call."""
        ...


class QueryToolHandler(ToolHandler):
    """Handler for query tool."""

    name: ClassVar[str] = "query"
    description: ClassVar[str] = (
        "Hybrid search combining full-text search (BM25), "
        "vector semantic search, and reranking for the most relevant results."
    )
    input_schema: ClassVar[dict[str, Any]] = {
        "type": "object",
        "properties": {
            "query": {"type": "string"},
            "collections": {"type": "array", "items": {"type": "string"}},
            "limit": {"type": "integer", "default": 10},
            "min_score": {"type": "number", "default": 0.0},
        },
        "required": ["query"],
    }

    async def handle(
        self,
        params: dict[str, Any],
        backend: SearchBackend,
    ) -> ToolsCallResult:
        """Execute query tool."""
        input_data = QueryInput(**params)
        results = await backend.hybrid_search(
            query=input_data.query,
            collections=input_data.collections,
            limit=input_data.limit,
            min_score=input_data.min_score,
        )
        output = QueryOutput(results=results)
        return ToolsCallResult(
            content=[
                ToolContentItem(
                    type="text",
                    text=json.dumps(output.model_dump(), ensure_ascii=False),
                )
            ]
        )


class GetToolHandler(ToolHandler):
    """Handler for get tool."""

    name: ClassVar[str] = "get"
    description: ClassVar[str] = (
        "Get a document by its path or document ID, with optional line range."
    )
    input_schema: ClassVar[dict[str, Any]] = {
        "type": "object",
        "properties": {
            "path_or_docid": {"type": "string"},
            "from_line": {"type": "integer"},
            "max_lines": {"type": "integer"},
        },
        "required": ["path_or_docid"],
    }

    async def handle(
        self,
        params: dict[str, Any],
        backend: SearchBackend,
    ) -> ToolsCallResult:
        """Execute get tool."""
        input_data = GetInput(**params)
        doc = await backend.get_document(
            input_data.path_or_docid,
            input_data.from_line,
            input_data.max_lines,
        )
        if doc is None:
            return ToolsCallResult(
                content=[ToolContentItem(type="text", text="Document not found")],
                isError=True,
            )
        output = GetOutput(document=doc)
        return ToolsCallResult(
            content=[
                ToolContentItem(
                    type="text",
                    text=json.dumps(output.model_dump(), ensure_ascii=False),
                )
            ]
        )


class MultiGetToolHandler(ToolHandler):
    """Handler for multi_get tool."""

    name: ClassVar[str] = "multi_get"
    description: ClassVar[str] = "Batch get documents matching a glob pattern."
    input_schema: ClassVar[dict[str, Any]] = {
        "type": "object",
        "properties": {
            "pattern": {"type": "string"},
            "max_bytes": {"type": "integer"},
        },
        "required": ["pattern"],
    }

    async def handle(
        self,
        params: dict[str, Any],
        backend: SearchBackend,
    ) -> ToolsCallResult:
        """Execute multi_get tool."""
        input_data = MultiGetInput(**params)
        docs, errors = await backend.get_documents_by_pattern(
            input_data.pattern,
            input_data.max_bytes,
        )
        output = MultiGetOutput(documents=docs, errors=errors)
        return ToolsCallResult(
            content=[
                ToolContentItem(
                    type="text",
                    text=json.dumps(output.model_dump(), ensure_ascii=False),
                )
            ]
        )


class StatusToolHandler(ToolHandler):
    """Handler for status tool."""

    name: ClassVar[str] = "status"
    description: ClassVar[str] = "Get the current status of all document collections."
    input_schema: ClassVar[dict[str, Any]] = {
        "type": "object",
        "properties": {},
        "required": [],
    }

    async def handle(
        self,
        params: dict[str, Any],  # noqa: ARG002
        backend: SearchBackend,
    ) -> ToolsCallResult:
        """Execute status tool."""
        collections, total = await backend.get_status()
        output = StatusOutput(collections=collections, total_documents=total)
        return ToolsCallResult(
            content=[
                ToolContentItem(
                    type="text",
                    text=json.dumps(output.model_dump(), ensure_ascii=False),
                )
            ]
        )


def create_default_tools(backend: SearchBackend) -> list[ToolHandler]:  # noqa: ARG001
    """Create default tool handlers."""
    return [
        QueryToolHandler(),
        GetToolHandler(),
        MultiGetToolHandler(),
        StatusToolHandler(),
    ]
