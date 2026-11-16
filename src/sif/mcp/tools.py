"""SDK tool surface for the SIF MCP server (Phase 22 D-05/D-07/D-08/D-09/D-10).

Every tool is annotated with its preserved Pydantic output model and returns
an explicit ``CallToolResult`` carrying BOTH channels:

- the legacy compact JSON text that 2024/2025-era clients parse today, and
- ``structuredContent`` derived from the same model (with the model's
  ``outputSchema`` published next to it).

The explicit builder is mandatory, not an optimization: the SDK's automatic
text channel is pretty-printed (``indent=2``) and unrolls list returns into one
text block per element (22-RESEARCH.md C7/Pitfall 1), which would break the
D-05 backward-compatibility contract.

D-07: descriptions are reviewed constants, not prose regenerated from code,
and every tool is read-only. A host must never infer auto-approval or
prompt-free execution from these strings; the documented Claude Code effects
are parallel read-only calls plus one retry only.
"""

from __future__ import annotations

from typing import Annotated, Any, Literal

from mcp.server import MCPServer
from mcp.server.mcpserver.exceptions import ResourceNotFoundError, ToolError
from mcp.types import CallToolResult, TextContent, ToolAnnotations
from pydantic import BaseModel, Field, ValidationError

from sif.core.filters import FilterNode, FilterValidationError, parse_filter, parse_match
from sif.mcp.backend import SearchBackend
from sif.mcp.protocol import (
    GetInput,
    GetOutput,
    LexSearchInput,
    LexSearchOutput,
    MetadataInput,
    MetadataOutput,
    MultiGetInput,
    MultiGetOutput,
    QueryInput,
    QueryOutput,
    StatusOutput,
    VecSearchInput,
    VecSearchOutput,
)
from sif.utils.json_output import json_dumps_strict


# D-07: read-only tools carry truthful hints; idempotent/destructive hints are
# omitted because they are only meaningful for non-read-only tools.
TOOL_ANNOTATIONS = ToolAnnotations(read_only_hint=True, open_world_hint=False)

# Reviewed description constants (D-07/D-12). Every claim must match backend
# behavior: rerank is opt-in, metadata keeps the Phase 20 wording verbatim, and
# nothing promises auto-approval or prompt-free execution.
TOOL_DESCRIPTIONS: dict[str, str] = {
    "query": (
        "Hybrid search combining BM25 full-text search, vector semantic search, "
        "and RRF fusion. Reranking is opt-in: it is off unless SIF_RERANK_ENABLED "
        "is set, and the rerank parameter forces it on or off for one query."
    ),
    "get": (
        "Get a document by path or document ID, optionally limited to a line "
        "range. Returns docid, path, line range, content hash, and content for "
        "citation."
    ),
    "multi_get": (
        "Batch get documents matching a glob pattern. Returns docid, path, line "
        "range, content hash, and content for citation."
    ),
    "status": "Get the current status of all document collections.",
    "metadata": (
        "Report filterable metadata keys, value types, document counts, numeric "
        "min/median/max ranges, and exact remaining window counts. Accepts the "
        "same filter grammar as query; path and mtime are reported as built-ins."
    ),
    "lex_search": (
        "Lexical BM25 search only, matching `sif search search` (filter, offset, "
        "min_score). No expansion or reranking."
    ),
    "vec_search": (
        "Vector semantic search only, matching `sif search vsearch` (filter, "
        "offset, per_chunk, min_score). Requires an embedding model; no expansion "
        "or reranking."
    ),
}


def _result(output: BaseModel, *, exclude_none: bool = False) -> CallToolResult:
    """Emit the legacy text payload and ``structuredContent`` from one model.

    ``exclude_none`` mirrors the tool's historical text dump: ``metadata``
    passes ``True`` so the frozen Phase 20 envelope keeps its exact keys (no
    ``filteredDocuments: null``), every other tool keeps the full schema.
    """
    text = json_dumps_strict(output.model_dump(exclude_none=exclude_none), ensure_ascii=False)
    structured = output.model_dump(mode="json", by_alias=True, exclude_none=exclude_none)
    return CallToolResult(
        content=[TextContent(type="text", text=text)],
        structured_content=structured,
    )


def _parse_filter_node(raw: dict[str, Any] | None) -> FilterNode | None:
    """Parse the shared filter grammar, mapping rejections to ``ToolError``.

    D-08: an invalid AST is an expected tool-input failure, so it becomes a
    model-correctable tool execution error, never a protocol error. The
    message is the shared parser's controlled spelling (``filter.<op>: ...``).
    """
    if raw is None:
        return None
    try:
        return parse_filter(raw)
    except FilterValidationError as exc:
        raise ToolError(str(exc)) from exc


def _register_query_tool(mcp: MCPServer, backend: SearchBackend) -> None:
    """Register ``query`` with its frozen input fields as the schema (D-06)."""

    @mcp.tool(
        name="query",
        description=TOOL_DESCRIPTIONS["query"],
        annotations=TOOL_ANNOTATIONS,
    )
    async def query(  # noqa: PLR0913 — one parameter per frozen QueryInput field
        query: str,
        collections: list[str] | None = None,
        limit: Annotated[int, Field(ge=1)] = 10,
        offset: Annotated[int, Field(ge=0)] = 0,
        filter: dict[str, Any] | None = None,  # noqa: A002 — frozen wire argument name
        per_chunk: bool = False,
        min_score: Annotated[float, Field(ge=0.0)] = 0.0,
        rrf_k: Annotated[int | None, Field(ge=1)] = None,
        bm25_weight: Annotated[float | None, Field(gt=0.0)] = None,
        vector_weight: Annotated[float | None, Field(gt=0.0)] = None,
        rerank: bool | None = None,
    ) -> Annotated[CallToolResult, QueryOutput]:
        try:
            input_data = QueryInput(
                query=query,
                collections=collections,
                limit=limit,
                offset=offset,
                filter=filter,
                per_chunk=per_chunk,
                min_score=min_score,
                rrf_k=rrf_k,
                bm25_weight=bm25_weight,
                vector_weight=vector_weight,
            )
        except ValidationError as exc:
            raise ToolError(str(exc)) from exc
        filter_node = _parse_filter_node(input_data.filter)
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
            rerank=rerank,
        )
        output = QueryOutput(
            results=results,
            # D-05 boundary remap: hybrid_search attaches the zero-result
            # suggestions to the returned collection; an unlisted field is
            # silently dropped here, so it is read explicitly. getattr keeps
            # mocked/legacy plain-list returns working (empty suggestions).
            suggestions=getattr(results, "suggestions", []),
        )
        return _result(output)


def _register_get_tool(mcp: MCPServer, backend: SearchBackend) -> None:
    """Register ``get``: the citation-grade line-range surface (D-06)."""

    @mcp.tool(
        name="get",
        description=TOOL_DESCRIPTIONS["get"],
        annotations=TOOL_ANNOTATIONS,
    )
    async def get(
        path_or_docid: str,
        from_line: Annotated[int | None, Field(ge=1)] = None,
        max_lines: Annotated[int | None, Field(ge=1)] = None,
    ) -> Annotated[CallToolResult, GetOutput]:
        try:
            input_data = GetInput(
                path_or_docid=path_or_docid,
                from_line=from_line,
                max_lines=max_lines,
            )
        except ValidationError as exc:
            raise ToolError(str(exc)) from exc
        document = await backend.get_document(
            input_data.path_or_docid,
            input_data.from_line,
            input_data.max_lines,
        )
        if document is None:
            raise ToolError("Document not found")
        return _result(GetOutput(document=document))


def _register_multi_get_tool(mcp: MCPServer, backend: SearchBackend) -> None:
    """Register ``multi_get``: the batch glob retrieval surface (D-06)."""

    @mcp.tool(
        name="multi_get",
        description=TOOL_DESCRIPTIONS["multi_get"],
        annotations=TOOL_ANNOTATIONS,
    )
    async def multi_get(
        pattern: str,
        max_bytes: Annotated[int | None, Field(ge=0)] = None,
    ) -> Annotated[CallToolResult, MultiGetOutput]:
        try:
            input_data = MultiGetInput(pattern=pattern, max_bytes=max_bytes)
        except ValidationError as exc:
            raise ToolError(str(exc)) from exc
        documents, errors = await backend.get_documents_by_pattern(
            input_data.pattern,
            input_data.max_bytes,
        )
        return _result(MultiGetOutput(documents=documents, errors=errors))


def _register_status_tool(mcp: MCPServer, backend: SearchBackend) -> None:
    """Register ``status``: the tracer tool carried over from 22-01."""

    @mcp.tool(
        name="status",
        description=TOOL_DESCRIPTIONS["status"],
        annotations=TOOL_ANNOTATIONS,
    )
    async def status() -> Annotated[CallToolResult, StatusOutput]:
        collections, total = await backend.get_status()
        return _result(StatusOutput(collections=collections, total_documents=total))


def _register_metadata_tool(mcp: MCPServer, backend: SearchBackend) -> None:
    """Register ``metadata``: the frozen Phase 20 discovery envelope (D-12)."""

    @mcp.tool(
        name="metadata",
        description=TOOL_DESCRIPTIONS["metadata"],
        annotations=TOOL_ANNOTATIONS,
    )
    async def metadata(  # noqa: PLR0913 — one parameter per frozen MetadataInput field
        collections: list[str] | None = None,
        filter: dict[str, Any] | None = None,  # noqa: A002 — frozen wire argument name
        match: dict[str, Any] | None = None,
        min_count: Annotated[int, Field(ge=1)] = 1,
        sort: Literal["count", "value"] = "count",
        limit: Annotated[int, Field(ge=1)] = 50,
        value_limit: Annotated[int, Field(ge=0)] = 10,
    ) -> Annotated[CallToolResult, MetadataOutput]:
        try:
            input_data = MetadataInput(
                collections=collections,
                filter=filter,
                match=match,
                min_count=min_count,
                sort=sort,
                limit=limit,
                value_limit=value_limit,
            )
        except ValidationError as exc:
            raise ToolError(str(exc)) from exc
        filter_node = _parse_filter_node(input_data.filter)
        try:
            match_node = None if input_data.match is None else parse_match(input_data.match)
        except FilterValidationError as exc:
            raise ToolError(str(exc)) from exc
        try:
            discovery = await backend.metadata(
                collections=input_data.collections,
                filter_node=filter_node,
                match=match_node,
                min_count=input_data.min_count,
                sort=input_data.sort,
                limit=input_data.limit,
                value_limit=input_data.value_limit,
            )
        except ValueError as exc:
            # An unknown collection name is a model-correctable input failure
            # (D-08), not an internal error.
            raise ToolError(str(exc)) from exc
        output = MetadataOutput(**discovery)
        return _result(output, exclude_none=True)


def _register_lex_search_tool(mcp: MCPServer, backend: SearchBackend) -> None:
    """Register ``lex_search``: the CLI ``search search`` one-shot path (D-17)."""

    @mcp.tool(
        name="lex_search",
        description=TOOL_DESCRIPTIONS["lex_search"],
        annotations=TOOL_ANNOTATIONS,
    )
    async def lex_search(  # noqa: PLR0913 — one parameter per frozen LexSearchInput field
        query: str,
        collections: list[str] | None = None,
        limit: Annotated[int, Field(ge=1)] = 10,
        offset: Annotated[int, Field(ge=0)] = 0,
        min_score: Annotated[float, Field(ge=0.0)] = 0.0,
        filter: dict[str, Any] | None = None,  # noqa: A002 — frozen wire argument name
    ) -> Annotated[CallToolResult, LexSearchOutput]:
        try:
            input_data = LexSearchInput(
                query=query,
                collections=collections,
                limit=limit,
                offset=offset,
                min_score=min_score,
                filter=filter,
            )
        except ValidationError as exc:
            raise ToolError(str(exc)) from exc
        filter_node = _parse_filter_node(input_data.filter)
        results = await backend.lex_search(
            query=input_data.query,
            collections=input_data.collections,
            limit=input_data.limit,
            offset=input_data.offset,
            min_score=input_data.min_score,
            filter_node=filter_node,
        )
        return _result(LexSearchOutput(results=results))


def _register_vec_search_tool(mcp: MCPServer, backend: SearchBackend) -> None:
    """Register ``vec_search``: the CLI ``search vsearch`` one-shot path (D-17)."""

    @mcp.tool(
        name="vec_search",
        description=TOOL_DESCRIPTIONS["vec_search"],
        annotations=TOOL_ANNOTATIONS,
    )
    async def vec_search(  # noqa: PLR0913 — one parameter per frozen VecSearchInput field
        query: str,
        collections: list[str] | None = None,
        limit: Annotated[int, Field(ge=1)] = 10,
        offset: Annotated[int, Field(ge=0)] = 0,
        per_chunk: bool = False,
        min_score: Annotated[float, Field(ge=0.0)] = 0.0,
        filter: dict[str, Any] | None = None,  # noqa: A002 — frozen wire argument name
    ) -> Annotated[CallToolResult, VecSearchOutput]:
        try:
            input_data = VecSearchInput(
                query=query,
                collections=collections,
                limit=limit,
                offset=offset,
                per_chunk=per_chunk,
                min_score=min_score,
                filter=filter,
            )
        except ValidationError as exc:
            raise ToolError(str(exc)) from exc
        filter_node = _parse_filter_node(input_data.filter)
        try:
            results = await backend.vec_search(
                query=input_data.query,
                collections=input_data.collections,
                limit=input_data.limit,
                offset=input_data.offset,
                per_chunk=input_data.per_chunk,
                min_score=input_data.min_score,
                filter_node=filter_node,
            )
        except RuntimeError as exc:
            # D-15: a missing embedder, a dimension mismatch, or a missing
            # sqlite-vec extension is a model-correctable tool error carrying
            # the install/model remedy, never a protocol error.
            raise ToolError(str(exc)) from exc
        return _result(VecSearchOutput(results=results))


def register_tools(mcp: MCPServer, backend: SearchBackend) -> None:
    """Register the deterministic read-only SIF tool set (D-06).

    Order is part of the contract: ``query, get, multi_get, status, metadata,
    lex_search, vec_search``. Every function's signature IS the published input
    schema; the preserved input models are still constructed inside the body so
    SIF's validators run on the same data the hand-written handlers validated
    (D-08).
    """
    _register_query_tool(mcp, backend)
    _register_get_tool(mcp, backend)
    _register_multi_get_tool(mcp, backend)
    _register_status_tool(mcp, backend)
    _register_metadata_tool(mcp, backend)
    _register_lex_search_tool(mcp, backend)
    _register_vec_search_tool(mcp, backend)


def register_resource(mcp: MCPServer, backend: SearchBackend) -> None:
    """Register the ``docs://`` document resource (D-09).

    The full Markdown document is returned by default; ``from_line`` and
    ``max_lines`` are RFC 6570 query variables honored through
    ``SearchBackend.get_document``. The ``get`` tool remains the citation-grade
    line-range surface. The MIME type is template-level (the high-level API
    cannot vary it per document), so ``text/markdown`` is the honest choice for
    a Markdown-first corpus.
    """

    @mcp.resource(
        "docs://{doc_id}{?from_line,max_lines}",
        name="document",
        description=(
            "Read a SIF document by doc id or path as Markdown, optionally a "
            "1-based inclusive line window."
        ),
        mime_type="text/markdown",
    )
    async def read_document(
        doc_id: str,
        from_line: int | None = None,
        max_lines: int | None = None,
    ) -> str:
        document = await backend.get_document(doc_id, from_line, max_lines)
        if document is None:
            raise ResourceNotFoundError(f"Document not found: {doc_id}")
        return document.content
