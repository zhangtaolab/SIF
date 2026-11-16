"""SIF MCP tool I/O models (Phase 22 D-10/D-12).

The JSON-RPC wire types and helper factories were deleted with the hand-rolled
shell in 22-02 Task 3; the official SDK owns the protocol. Everything below is
the preserved SIF tool contract: the input/output Pydantic models whose return
annotations drive ``outputSchema``/``structuredContent``.

``MetadataOutput`` is frozen by Phase 20 D-15/D-20; serialize it with
``exclude_none=True`` so the envelope stays byte-compatible.
"""

from typing import Any, Literal

from pydantic import BaseModel, Field


# ============================================================================
# SIF-specific Types
# ============================================================================


class SearchResult(BaseModel):
    """Search result item.

    Citation fields (Phase 22 D-11) are additive: ``snippet`` is the smart
    snippet bytes, ``content_hash`` is the stored ``documents.checksum``, and
    ``line_start``/``line_end`` are the inclusive 1-based window the snippet
    rendered. They stay ``None`` where the producing route has no snippet
    window (the direct ``lex:``/BM25 route and ``lex_search``).
    """

    doc_id: str
    path: str
    title: str | None = None
    content: str | None = None
    snippet: str | None = None
    content_hash: str | None = None
    line_start: int | None = None
    line_end: int | None = None
    score: float
    highlights: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class Document(BaseModel):
    """Document model.

    ``content_hash`` (Phase 22 D-11) is the stored ``documents.checksum`` so a
    citation can detect drift; ``line_start``/``line_end`` describe the
    content actually returned (full document = 1..N, ranged request = the
    clamped inclusive window). They are ``None`` only when the requested
    window starts past the end of the document and renders no content.
    """

    doc_id: str
    path: str
    title: str | None = None
    content: str
    content_hash: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    line_start: int | None = None
    line_end: int | None = None
    collection_id: str | None = None


class CollectionInfo(BaseModel):
    """Collection information."""

    name: str
    document_count: int
    last_updated: str | None = None
    size_bytes: int | None = None


# ============================================================================
# Tool Input/Output Models
# ============================================================================


class QueryInput(BaseModel):
    """Input for query tool."""

    query: str
    collections: list[str] | None = None
    limit: int = Field(default=10, ge=1)
    # Pagination (CORR-03/D-05): offset is an absolute row skip; a past-the-end
    # offset returns an empty page, never an error.
    offset: int = Field(default=0, ge=0)
    # Metadata filter (Phase 20 D-02): a raw JSON AST validated inside the
    # handler by the shared parse_filter, mirroring Phase 19's offset
    # precedent. Raw dict on purpose — a validation failure must be a tool
    # execution error with a controlled message, never a protocol error.
    filter: dict[str, Any] | None = None
    # Per-chunk escape hatch (CORR-02/D-01): False keeps the per-document dedup
    # contract; True restores the ungrouped chunk rows. Only the chunk-capable
    # surfaces carry it — LexSearchInput is document-level.
    per_chunk: bool = False
    min_score: float = Field(default=0.0, ge=0.0)
    # Fusion overrides (Phase 15, D-03/D-04): None falls back to the server
    # process's SIF_ settings; ranges are enforced here (ASVS V5) so
    # out-of-range requests fail validation before options construction.
    rrf_k: int | None = Field(default=None, ge=1)
    bm25_weight: float | None = Field(default=None, gt=0.0)
    vector_weight: float | None = Field(default=None, gt=0.0)


class QueryOutput(BaseModel):
    """Output for query tool."""

    results: list[SearchResult] = Field(default_factory=list)
    # Phase 15 (D-05/A6): zero-result did-you-mean queries cross the MCP
    # boundary as a flat list of display-only rewritten query strings. Empty
    # for any query that returned results.
    suggestions: list[str] = Field(default_factory=list)


class LexSearchInput(BaseModel):
    """Input for lex_search tool.

    ``offset`` mirrors ``QueryInput`` so Phase 22's lex/vec tool registration
    has no schema gap; the tool itself stays unregistered in Phase 19
    (research Open Q1).
    """

    query: str
    collections: list[str] | None = None
    limit: int = Field(default=10, ge=1)
    offset: int = Field(default=0, ge=0)
    # Phase 22 D-17/Open Q3: additive CLI parity with `sif search search
    # --min-score`; a zero default preserves every existing caller.
    min_score: float = Field(default=0.0, ge=0.0)
    # Metadata filter (Phase 20 D-02): mirrors QueryInput.filter under the
    # same Phase 19 offset precedent. Lex/vec tool registration stays Phase
    # 22; the field is declared now so that registration has no filter gap.
    filter: dict[str, Any] | None = None


class LexSearchOutput(BaseModel):
    """Output for lex_search tool."""

    results: list[SearchResult] = Field(default_factory=list)


class VecSearchInput(BaseModel):
    """Input for vec_search tool.

    ``offset`` mirrors ``QueryInput`` for the same Phase 22 schema parity;
    ``per_chunk`` mirrors its chunk escape hatch (CORR-02/D-01). Registration
    stays Phase 22 (research Open Q1).
    """

    query: str
    collections: list[str] | None = None
    limit: int = Field(default=10, ge=1)
    offset: int = Field(default=0, ge=0)
    per_chunk: bool = False
    # Phase 22 D-17/Open Q3: additive CLI parity with `sif search vsearch
    # --min-score`; a zero default preserves every existing caller.
    min_score: float = Field(default=0.0, ge=0.0)
    # Metadata filter (Phase 20 D-02): mirrors QueryInput.filter for the same
    # Phase 22 schema parity; registration stays Phase 22 (research Open Q1).
    filter: dict[str, Any] | None = None


class VecSearchOutput(BaseModel):
    """Output for vec_search tool."""

    results: list[SearchResult] = Field(default_factory=list)


class GetInput(BaseModel):
    """Input for get tool."""

    path_or_docid: str
    from_line: int | None = Field(default=None, ge=1)
    max_lines: int | None = Field(default=None, ge=1)


class GetOutput(BaseModel):
    """Output for get tool."""

    document: Document | None = None


class MultiGetInput(BaseModel):
    """Input for multi_get tool."""

    pattern: str
    max_bytes: int | None = Field(default=None, ge=0)


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


class MetadataRange(BaseModel):
    """Numeric min/median/max for a key's ``number`` type (D-15)."""

    min: float
    median: float
    max: float


class MetadataValueSummary(BaseModel):
    """One distinct value and the document count that carries it (D-15)."""

    value: str | float | bool
    documents: int


class MetadataTypeSummary(BaseModel):
    """One value type of a key: counts, a windowed value list, optional range."""

    type: Literal["string", "number", "boolean"]
    multiValued: bool  # noqa: N815
    documents: int
    distinctValues: int  # noqa: N815
    values: list[MetadataValueSummary] = Field(default_factory=list)
    remainingValues: int  # noqa: N815
    range: MetadataRange | None = None


class MetadataKeySummary(BaseModel):
    """One reported metadata key: a frontmatter key or a D-03 built-in."""

    key: str
    documents: int
    types: list[MetadataTypeSummary] = Field(default_factory=list)


class MetadataInput(BaseModel):
    """Input for the ``metadata`` discovery tool (D-15, frozen Phase 22 schema).

    Snake_case inputs per D-15; ``limit`` windows the key list (default 50)
    and ``value_limit`` windows each key's value list (default 10). ``filter``
    and ``match`` stay raw dicts so the handler can report a controlled tool
    execution error instead of a protocol error (D-17).
    """

    collections: list[str] | None = None
    filter: dict[str, Any] | None = None
    match: dict[str, Any] | None = None
    min_count: int = Field(default=1, ge=1)
    sort: Literal["count", "value"] = "count"
    limit: int = Field(default=50, ge=1)
    value_limit: int = Field(default=10, ge=0)


class MetadataOutput(BaseModel):
    """Output for the ``metadata`` discovery tool (D-15 + D-20, Phase 22 schema).

    The camelCase names are written verbatim: the mixed casing against SIF's
    snake_case outputs is deliberate and part of the frozen Phase 22 contract.
    Serialize with ``model_dump(exclude_none=True)`` so ``filteredDocuments``
    is absent without a filter and ``range`` is absent on non-numeric types.
    ``builtIns`` always carries exactly ``path`` then ``mtime`` (D-03/D-20) and
    is never counted by ``totalKeys``/``remainingKeys``.
    """

    documents: int
    filteredDocuments: int | None = None  # noqa: N815
    totalKeys: int  # noqa: N815
    remainingKeys: int  # noqa: N815
    skippedKeys: int  # noqa: N815
    builtIns: list[MetadataKeySummary]  # noqa: N815
    keys: list[MetadataKeySummary] = Field(default_factory=list)
