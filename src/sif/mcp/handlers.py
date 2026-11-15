"""MCP ToolHandler implementations."""

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from typing import Any, ClassVar

from sif.core.filters import FilterValidationError, parse_filter, parse_match
from sif.mcp.protocol import (
    GetInput,
    GetOutput,
    MetadataInput,
    MetadataOutput,
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

    name: ClassVar[str]
    description: ClassVar[str]
    input_schema: ClassVar[dict[str, Any]]

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
            # CORR-03/D-05 pagination: the hand-written schema and the
            # QueryInput.offset field (Field(ge=0)) must stay in sync.
            "offset": {"type": "integer", "minimum": 0, "default": 0},
            # CORR-02/D-01 chunk escape hatch: mirrors QueryInput.per_chunk.
            # An unlisted property is invisible to MCP tool discovery even
            # though the model accepts it, so the two must stay in sync.
            "per_chunk": {"type": "boolean", "default": False},
            # Phase 20 D-02 metadata filter: mirrors QueryInput.filter. The
            # hand-written schema and the pydantic model must stay in sync —
            # an unlisted property is invisible to MCP tool discovery.
            "filter": {"type": "object"},
            "min_score": {"type": "number", "default": 0.0},
            # Phase 15 fusion overrides (D-04): omitted = server SIF_ settings.
            # The hand-written schema and the pydantic model must stay in
            # sync — omitting these hides the params from MCP tool discovery
            # while the model still accepts them.
            "rrf_k": {"type": "integer"},
            "bm25_weight": {"type": "number"},
            "vector_weight": {"type": "number"},
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
        # Phase 20 D-02/D-17: validate the caller-supplied AST with the one
        # shared grammar. An invalid filter is a TOOL EXECUTION error inside
        # a successful JSON-RPC response (SEP-1303) so the model can
        # self-correct; it is never a JSON-RPC INVALID_PARAMS protocol error.
        try:
            filter_node = None if input_data.filter is None else parse_filter(input_data.filter)
        except FilterValidationError as exc:
            return ToolsCallResult(
                content=[ToolContentItem(type="text", text=str(exc))],
                isError=True,
            )
        results = await backend.hybrid_search(
            query=input_data.query,
            collections=input_data.collections,
            limit=input_data.limit,
            offset=input_data.offset,
            per_chunk=input_data.per_chunk,
            min_score=input_data.min_score,
            rrf_k=input_data.rrf_k,
            bm25_weight=input_data.bm25_weight,
            vector_weight=input_data.vector_weight,
            filter_node=filter_node,
        )
        output = QueryOutput(
            results=results,
            # D-05 boundary remap: hybrid_search attaches the zero-result
            # suggestions to the returned collection; an unlisted field is
            # silently dropped here, so it is read explicitly. getattr keeps
            # mocked/legacy plain-list returns working (empty suggestions).
            suggestions=getattr(results, "suggestions", []),
        )
        return ToolsCallResult(
            content=[
                ToolContentItem(
                    type="text",
                    text=json.dumps(output.model_dump(), ensure_ascii=False),
                ),
            ],
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
                ),
            ],
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
                ),
            ],
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
                ),
            ],
        )


class MetadataToolHandler(ToolHandler):
    """Handler for the metadata discovery tool (Phase 20 D-14/D-15, frozen for Phase 22)."""

    name: ClassVar[str] = "metadata"
    description: ClassVar[str] = (
        "Report filterable metadata keys, value types, document counts, numeric "
        "min/median/max ranges, and exact remaining window counts. Accepts the "
        "same filter grammar as query; path and mtime are reported as built-ins."
    )
    input_schema: ClassVar[dict[str, Any]] = {
        "type": "object",
        "properties": {
            "collections": {"type": "array", "items": {"type": "string"}},
            # The hand-written schema and MetadataInput must stay in sync — an
            # unlisted property is invisible to MCP tool discovery (Pitfall 12).
            "filter": {"type": "object"},
            "match": {"type": "object"},
            "min_count": {"type": "integer", "minimum": 1, "default": 1},
            "sort": {"type": "string", "enum": ["count", "value"], "default": "count"},
            "limit": {"type": "integer", "minimum": 1, "default": 50},
            "value_limit": {"type": "integer", "minimum": 0, "default": 10},
        },
        "required": [],
    }

    async def handle(
        self,
        params: dict[str, Any],
        backend: SearchBackend,
    ) -> ToolsCallResult:
        """Execute the metadata tool."""
        input_data = MetadataInput(**params)
        # D-17: invalid filter/match JSON is a tool execution error inside a
        # successful JSON-RPC response so the model can self-correct — never
        # an INVALID_PARAMS protocol error.
        try:
            filter_node = None if input_data.filter is None else parse_filter(input_data.filter)
            match_node = None if input_data.match is None else parse_match(input_data.match)
        except FilterValidationError as exc:
            return ToolsCallResult(
                content=[ToolContentItem(type="text", text=str(exc))],
                isError=True,
            )
        discovery = await backend.metadata(
            collections=input_data.collections,
            filter_node=filter_node,
            match=match_node,
            min_count=input_data.min_count,
            sort=input_data.sort,
            limit=input_data.limit,
            value_limit=input_data.value_limit,
        )
        output = MetadataOutput(**discovery)
        return ToolsCallResult(
            content=[
                ToolContentItem(
                    type="text",
                    text=json.dumps(output.model_dump(exclude_none=True), ensure_ascii=False),
                ),
            ],
        )


def create_default_tools() -> list[ToolHandler]:
    """Create default tool handlers."""
    return [
        QueryToolHandler(),
        GetToolHandler(),
        MultiGetToolHandler(),
        StatusToolHandler(),
        MetadataToolHandler(),
    ]
