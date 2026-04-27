"""
MCP (Model Context Protocol) Protocol Definitions

This module defines the message types and protocol structures for MCP,
following the JSON-RPC 2.0 specification.

Reference: https://modelcontextprotocol.io/
"""

from enum import Enum
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field


# ============================================================================
# JSON-RPC Base Types
# ============================================================================


class JsonRpcVersion(str, Enum):
    """JSON-RPC version."""

    V2_0 = "2.0"


class JsonRpcRequest(BaseModel):
    """JSON-RPC 2.0 Request object."""

    jsonrpc: Literal["2.0"] = "2.0"
    id: Optional[str | int] = None
    method: str
    params: Optional[dict[str, Any]] = None


class JsonRpcError(BaseModel):
    """JSON-RPC 2.0 Error object."""

    code: int
    message: str
    data: Optional[Any] = None


class JsonRpcResponse(BaseModel):
    """JSON-RPC 2.0 Response object."""

    jsonrpc: Literal["2.0"] = "2.0"
    id: Optional[str | int] = None
    result: Optional[Any] = None
    error: Optional[JsonRpcError] = None


class JsonRpcNotification(BaseModel):
    """JSON-RPC 2.0 Notification object (no id)."""

    jsonrpc: Literal["2.0"] = "2.0"
    method: str
    params: Optional[dict[str, Any]] = None


# ============================================================================
# MCP Protocol Types
# ============================================================================


class MCPErrorCode(int, Enum):
    """MCP-specific error codes."""

    # Standard JSON-RPC errors
    PARSE_ERROR = -32700
    INVALID_REQUEST = -32600
    METHOD_NOT_FOUND = -32601
    INVALID_PARAMS = -32602
    INTERNAL_ERROR = -32603

    # MCP-specific errors
    SERVER_NOT_INITIALIZED = -32002
    UNKNOWN_TOOL = -32601
    TOOL_EXECUTION_ERROR = -32000


# ============================================================================
# Initialize
# ============================================================================


class InitializeParams(BaseModel):
    """Parameters for initialize request."""

    protocolVersion: str = "2024-11-05"
    capabilities: dict[str, Any] = Field(default_factory=dict)
    clientInfo: dict[str, str] = Field(default_factory=dict)


class ServerCapabilities(BaseModel):
    """Server capabilities."""

    tools: dict[str, Any] = Field(default_factory=lambda: {"listChanged": False})


class InitializeResult(BaseModel):
    """Result for initialize request."""

    protocolVersion: str = "2024-11-05"
    capabilities: ServerCapabilities = Field(default_factory=ServerCapabilities)
    serverInfo: dict[str, str] = Field(
        default_factory=lambda: {"name": "sif-mcp-server", "version": "1.0.0"}
    )


# ============================================================================
# Tools
# ============================================================================


class ToolInputSchema(BaseModel):
    """JSON Schema for tool input."""

    type: str = "object"
    properties: dict[str, Any] = Field(default_factory=dict)
    required: list[str] = Field(default_factory=list)


class MCPTool(BaseModel):
    """MCP Tool definition."""

    name: str
    description: str
    inputSchema: ToolInputSchema = Field(default_factory=ToolInputSchema)


class ToolsListParams(BaseModel):
    """Parameters for tools/list request."""

    cursor: Optional[str] = None


class ToolsListResult(BaseModel):
    """Result for tools/list request."""

    tools: list[MCPTool] = Field(default_factory=list)
    nextCursor: Optional[str] = None


class ToolsCallParams(BaseModel):
    """Parameters for tools/call request."""

    name: str
    arguments: dict[str, Any] = Field(default_factory=dict)


class ToolContentItem(BaseModel):
    """Content item in tool call result."""

    type: Literal["text", "image", "resource"] = "text"
    text: Optional[str] = None
    data: Optional[str] = None  # For image base64 data
    mimeType: Optional[str] = None


class ToolsCallResult(BaseModel):
    """Result for tools/call request."""

    content: list[ToolContentItem] = Field(default_factory=list)
    isError: bool = False


# ============================================================================
# Notifications
# ============================================================================


class InitializedNotification(BaseModel):
    """Client notification after initialization."""

    method: Literal["notifications/initialized"] = "notifications/initialized"
    params: dict[str, Any] = Field(default_factory=dict)


class ProgressNotification(BaseModel):
    """Progress notification."""

    method: Literal["notifications/progress"] = "notifications/progress"
    params: dict[str, Any]


# ============================================================================
# SIF-specific Types
# ============================================================================


class SearchResult(BaseModel):
    """Search result item."""

    doc_id: str
    path: str
    title: Optional[str] = None
    content: Optional[str] = None
    score: float
    highlights: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class Document(BaseModel):
    """Document model."""

    doc_id: str
    path: str
    title: Optional[str] = None
    content: str
    metadata: dict[str, Any] = Field(default_factory=dict)
    line_start: Optional[int] = None
    line_end: Optional[int] = None


class CollectionInfo(BaseModel):
    """Collection information."""

    name: str
    document_count: int
    last_updated: Optional[str] = None
    size_bytes: Optional[int] = None


# ============================================================================
# Tool Input/Output Models
# ============================================================================


class QueryInput(BaseModel):
    """Input for query tool."""

    query: str
    collections: Optional[list[str]] = None
    limit: int = 10
    min_score: float = 0.0


class QueryOutput(BaseModel):
    """Output for query tool."""

    results: list[SearchResult] = Field(default_factory=list)


class LexSearchInput(BaseModel):
    """Input for lex_search tool."""

    query: str
    collections: Optional[list[str]] = None
    limit: int = 10


class LexSearchOutput(BaseModel):
    """Output for lex_search tool."""

    results: list[SearchResult] = Field(default_factory=list)


class VecSearchInput(BaseModel):
    """Input for vec_search tool."""

    query: str
    collections: Optional[list[str]] = None
    limit: int = 10


class VecSearchOutput(BaseModel):
    """Output for vec_search tool."""

    results: list[SearchResult] = Field(default_factory=list)


class GetInput(BaseModel):
    """Input for get tool."""

    path_or_docid: str
    from_line: Optional[int] = None
    max_lines: Optional[int] = None


class GetOutput(BaseModel):
    """Output for get tool."""

    document: Optional[Document] = None


class MultiGetInput(BaseModel):
    """Input for multi_get tool."""

    pattern: str
    max_bytes: Optional[int] = None


class MultiGetOutput(BaseModel):
    """Output for multi_get tool."""

    documents: list[Document] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)


class StatusInput(BaseModel):
    """Input for status tool."""

    pass


class StatusOutput(BaseModel):
    """Output for status tool."""

    collections: list[CollectionInfo] = Field(default_factory=list)
    total_documents: int = 0


# ============================================================================
# Helper Functions
# ============================================================================


def create_success_response(id: str | int | None, result: Any) -> JsonRpcResponse:
    """Create a successful JSON-RPC response."""
    return JsonRpcResponse(id=id, result=result)


def create_error_response(
    id: str | int | None, code: int, message: str, data: Any = None
) -> JsonRpcResponse:
    """Create an error JSON-RPC response."""
    return JsonRpcResponse(id=id, error=JsonRpcError(code=code, message=message, data=data))


def create_notification(method: str, params: dict[str, Any] | None = None) -> JsonRpcNotification:
    """Create a JSON-RPC notification."""
    return JsonRpcNotification(method=method, params=params or {})
