"""SDK tool surface for the SIF MCP server (Phase 22 D-05/D-08/D-09/D-10).

Every tool is annotated with its preserved Pydantic output model and returns
an explicit ``CallToolResult`` carrying BOTH channels:

- the legacy compact JSON text that 2024/2025-era clients parse today, and
- ``structuredContent`` derived from the same model (with the model's
  ``outputSchema`` published next to it).

The explicit builder is mandatory, not an optimization: the SDK's automatic
text channel is pretty-printed (``indent=2``) and unrolls list returns into one
text block per element (22-RESEARCH.md C7/Pitfall 1), which would break the
D-05 backward-compatibility contract.
"""

from __future__ import annotations

from typing import Annotated

from mcp.server import MCPServer
from mcp.server.mcpserver.exceptions import ResourceNotFoundError
from mcp.types import CallToolResult, TextContent, ToolAnnotations
from pydantic import BaseModel

from sif.mcp.backend import SearchBackend
from sif.mcp.protocol import StatusOutput
from sif.utils.json_output import json_dumps_strict


# D-07: read-only tools carry truthful hints; idempotent/destructive hints are
# omitted because they are only meaningful for non-read-only tools.
TOOL_ANNOTATIONS = ToolAnnotations(read_only_hint=True, open_world_hint=False)

# Reviewed description constants (D-07). The six remaining tools are
# registered by 22-02; status is the tracer tool for this plan.
TOOL_DESCRIPTIONS: dict[str, str] = {
    "status": "Get the current status of all document collections.",
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


def register_tools(mcp: MCPServer, backend: SearchBackend) -> None:
    """Register the SIF tool set on ``mcp``.

    This plan registers ``status`` only: the remaining six tools land in
    22-02 after the seven-tool battery, so the intermediate SDK surface is a
    development-branch state and never a release surface.
    """

    @mcp.tool(
        name="status",
        description=TOOL_DESCRIPTIONS["status"],
        annotations=TOOL_ANNOTATIONS,
    )
    async def status() -> Annotated[CallToolResult, StatusOutput]:
        collections, total = await backend.get_status()
        return _result(StatusOutput(collections=collections, total_documents=total))


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
