"""Contract battery for the SIF MCP tool surface (Phase 22 D-06/D-07/D-08).

The tests drive the real SDK ``MCPServer`` registration (never a hand-written
schema): ``list_tools`` is the published contract and ``call_tool`` runs the
same function a host invokes. A mocked backend isolates forwarding assertions;
real tmp databases back the envelope, empty-index, and idempotency proofs.
"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from mcp.server import MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from mcp.types import ToolAnnotations

from sif.config.settings import Settings
from sif.core.models import Collection, Document as CoreDocument
from sif.database.connection import DatabaseConnection
from sif.database.repositories import CollectionRepository, DocumentRepository
from sif.mcp.app import create_http_app
from sif.mcp.backend import HybridSearchResults, SearchBackend
from sif.mcp.protocol import CollectionInfo, Document, SearchResult
from sif.mcp.tools import TOOL_DESCRIPTIONS, register_tools
from sif.search.vector import VectorSearcher


_EXPECTED_TOOL_ORDER = [
    "query",
    "get",
    "multi_get",
    "status",
    "metadata",
    "lex_search",
    "vec_search",
]
# D-06: no mutation surface ships in Phase 22; these names must never appear.
_MUTATION_TOOL_NAMES = {"index_update", "index_embed", "vacuum", "backup", "collection_create"}


_FILTER_PAYLOAD = {"field": "status", "operator": "eq", "value": "active"}
_BAD_FILTER_PAYLOAD = {"field": "tags", "operator": "gt", "value": "x"}

_METADATA_ENVELOPE = {
    "documents": 2,
    "totalKeys": 1,
    "remainingKeys": 0,
    "skippedKeys": 0,
    "builtIns": [
        {
            "key": "path",
            "documents": 2,
            "types": [
                {
                    "type": "string",
                    "multiValued": False,
                    "documents": 2,
                    "distinctValues": 2,
                    "values": [],
                    "remainingValues": 2,
                }
            ],
        },
        {
            "key": "mtime",
            "documents": 2,
            "types": [
                {
                    "type": "number",
                    "multiValued": False,
                    "documents": 2,
                    "distinctValues": 2,
                    "values": [],
                    "remainingValues": 2,
                    "range": {"min": 100.0, "median": 150.0, "max": 200.0},
                }
            ],
        },
    ],
    "keys": [
        {
            "key": "tag",
            "documents": 2,
            "types": [
                {
                    "type": "string",
                    "multiValued": False,
                    "documents": 2,
                    "distinctValues": 1,
                    "values": [{"value": "x", "documents": 2}],
                    "remainingValues": 0,
                }
            ],
        }
    ],
}


def _settings(**overrides: object) -> Settings:
    """Hermetic settings: small dimension, no cache side effects."""
    values: dict[str, object] = {
        "embedding_dim": 8,
        "model_name": "test",
        "cache_embeddings": False,
    }
    values.update(overrides)
    return Settings(_env_file=None, **values)


def _make_server(backend: SearchBackend | MagicMock) -> MCPServer:
    """Register the SIF tools on a bare SDK server (no lifespan needed)."""
    mcp = MCPServer("test-tools")
    register_tools(mcp, backend)
    return mcp


def _mock_backend() -> MagicMock:
    """Backend double whose async surface mirrors SearchBackend."""
    backend = MagicMock()
    backend.hybrid_search = AsyncMock(return_value=[])
    backend.lex_search = AsyncMock(return_value=[])
    backend.vec_search = AsyncMock(return_value=[])
    backend.get_document = AsyncMock(return_value=None)
    backend.get_documents_by_pattern = AsyncMock(return_value=([], []))
    backend.get_status = AsyncMock(return_value=([], 0))
    backend.metadata = AsyncMock(return_value=dict(_METADATA_ENVELOPE))
    return backend


def _seed_documents(
    db_path: Path,
    documents: list[tuple[str, str, dict[str, object]]],
) -> None:
    """Seed one collection and repository-created documents on the real DDL.

    ``documents`` entries are ``(doc_id, content, metadata)``. The repository
    path keeps the typed metadata store and FTS index synchronized exactly the
    way production does.
    """
    with DatabaseConnection(db_path).transaction() as conn:
        CollectionRepository(conn).create(Collection(id="c1", name="notes", path="/notes"))
        repo = DocumentRepository(conn)
        for position, (doc_id, content, metadata) in enumerate(documents):
            repo.create(
                CoreDocument(
                    id=doc_id,
                    collection_id="c1",
                    path=f"/notes/{doc_id}.md",
                    title=doc_id,
                    content=content,
                    mtime=100.0 * (position + 1),
                    metadata=metadata,
                )
            )


def _seed_metadata_rows(db_path: Path) -> None:
    """The Phase 20 handler fixture: three documents, two tag values."""
    _seed_documents(
        db_path,
        [
            ("d0", "body", {"tag": "rare", "priority": 1}),
            ("d1", "body", {"tag": "common", "priority": 2}),
            ("d2", "body", {"tag": "common"}),
        ],
    )


def _seed_envelope_rows(db_path: Path) -> None:
    """Two documents carrying the one ``tag=x`` value the envelope oracle pins."""
    _seed_documents(
        db_path,
        [
            ("e0", "body", {"tag": "x"}),
            ("e1", "body", {"tag": "x"}),
        ],
    )


@pytest.fixture
def backend(tmp_path: Path) -> SearchBackend:
    """A real, model-free SearchBackend on a fresh production-schema DB."""
    return SearchBackend(str(tmp_path / "tools.db"), settings=_settings())


# =============================================================================
# Task 1: the five read-capable tools (D-06/D-07/D-08)
# =============================================================================


class TestReviewedDescriptions:
    """D-07: descriptions match backend behavior, never auto-approval."""

    def test_query_description_marks_rerank_as_opt_in(self) -> None:
        text = TOOL_DESCRIPTIONS["query"]
        assert "Reranking is opt-in" in text
        assert "SIF_RERANK_ENABLED" in text
        assert "and reranking" not in text

    @pytest.mark.parametrize(
        "tool_name",
        ["query", "get", "multi_get", "status", "metadata", "lex_search", "vec_search"],
    )
    def test_descriptions_never_overclaim(self, tool_name: str) -> None:
        text = TOOL_DESCRIPTIONS[tool_name].lower()
        for banned in ("auto-approve", "auto approve", "prompt-free", "no permission"):
            assert banned not in text

    def test_metadata_description_keeps_the_reviewed_phase_20_wording(self) -> None:
        assert TOOL_DESCRIPTIONS["metadata"] == (
            "Report filterable metadata keys, value types, document counts, numeric "
            "min/median/max ranges, and exact remaining window counts. Accepts the "
            "same filter grammar as query; path and mtime are reported as built-ins."
        )


class TestQueryTool:
    """The query tool forwards its preserved input and keeps both channels."""

    @pytest.mark.asyncio
    async def test_text_parses_to_structured_content(self) -> None:
        backend = _mock_backend()
        backend.hybrid_search.return_value = [
            SearchResult(doc_id="d1", path="/a.md", score=0.9, highlights=["hi"]),
        ]

        result = await _make_server(backend).call_tool("query", {"query": "hello"})

        assert result.is_error is False
        payload = json.loads(result.content[0].text)
        assert payload == result.structured_content
        assert payload["results"][0]["doc_id"] == "d1"

    @pytest.mark.asyncio
    async def test_forwards_weight_overrides(self) -> None:
        backend = _mock_backend()

        await _make_server(backend).call_tool(
            "query",
            {"query": "q", "rrf_k": 5, "bm25_weight": 3.0, "vector_weight": 0.5},
        )

        kwargs = backend.hybrid_search.call_args.kwargs
        assert kwargs["rrf_k"] == 5
        assert kwargs["bm25_weight"] == 3.0
        assert kwargs["vector_weight"] == 0.5

    @pytest.mark.asyncio
    async def test_forwards_offset_per_chunk_and_min_score(self) -> None:
        backend = _mock_backend()

        await _make_server(backend).call_tool(
            "query",
            {"query": "q", "offset": 7, "per_chunk": True, "min_score": 0.2},
        )

        kwargs = backend.hybrid_search.call_args.kwargs
        assert kwargs["offset"] == 7
        assert kwargs["per_chunk"] is True
        assert kwargs["min_score"] == 0.2

    @pytest.mark.asyncio
    async def test_forwards_the_parsed_filter_ast(self) -> None:
        from sif.core.filters import parse_filter

        backend = _mock_backend()

        result = await _make_server(backend).call_tool(
            "query", {"query": "q", "filter": _FILTER_PAYLOAD}
        )

        assert result.is_error is False
        kwargs = backend.hybrid_search.call_args.kwargs
        assert kwargs["filter_node"] == parse_filter(_FILTER_PAYLOAD)

    @pytest.mark.asyncio
    async def test_absent_filter_forwards_none(self) -> None:
        backend = _mock_backend()

        await _make_server(backend).call_tool("query", {"query": "q"})

        assert backend.hybrid_search.call_args.kwargs["filter_node"] is None

    @pytest.mark.asyncio
    async def test_invalid_filter_is_a_tool_error(self) -> None:
        """D-08/D-17: a controlled ToolError, never a protocol error."""
        backend = _mock_backend()

        with pytest.raises(ToolError) as excinfo:
            await _make_server(backend).call_tool(
                "query", {"query": "q", "filter": _BAD_FILTER_PAYLOAD}
            )

        # The SDK prefixes the tool name; the shared parser's remedy is intact.
        text = str(excinfo.value)
        assert "filter.gt:" in text
        assert '"gt" requires a numeric value' in text
        backend.hybrid_search.assert_not_called()

    @pytest.mark.asyncio
    async def test_suggestions_are_remapped_into_the_output(self) -> None:
        backend = _mock_backend()
        backend.hybrid_search.return_value = HybridSearchResults([], ["quantum machin"])

        result = await _make_server(backend).call_tool("query", {"query": "quantm machin"})

        payload = json.loads(result.content[0].text)
        assert payload["results"] == []
        assert payload["suggestions"] == ["quantum machin"]
        assert payload == result.structured_content

    @pytest.mark.asyncio
    async def test_citation_fields_ride_both_channels(self) -> None:
        """D-11: snippet, stored hash, and line window serialize additively."""
        backend = _mock_backend()
        backend.hybrid_search.return_value = [
            SearchResult(
                doc_id="d1",
                path="/a.md",
                score=0.9,
                snippet="line two",
                content_hash="stored-checksum",
                line_start=2,
                line_end=2,
            ),
        ]

        result = await _make_server(backend).call_tool("query", {"query": "hello"})

        payload = json.loads(result.content[0].text)
        assert payload == result.structured_content
        item = payload["results"][0]
        assert item["snippet"] == "line two"
        assert item["content_hash"] == "stored-checksum"
        assert (item["line_start"], item["line_end"]) == (2, 2)


class TestGetAndMultiGetTools:
    """get/multi_get forward their preserved inputs and map not-found to ToolError."""

    @pytest.mark.asyncio
    async def test_get_serializes_document_and_forwards_line_arguments(self) -> None:
        backend = _mock_backend()
        backend.get_document.return_value = Document(
            doc_id="doc-1",
            path="notes/知识.md",
            content="你好\nsecond line",
            content_hash="stored-checksum",
            line_start=2,
            line_end=3,
        )

        result = await _make_server(backend).call_tool(
            "get", {"path_or_docid": "doc-1", "from_line": 2, "max_lines": 4}
        )

        payload = json.loads(result.content[0].text)
        assert payload == result.structured_content
        assert payload["document"]["path"] == "notes/知识.md"
        assert payload["document"]["line_start"] == 2
        assert payload["document"]["content_hash"] == "stored-checksum"
        backend.get_document.assert_awaited_once_with("doc-1", 2, 4)

    @pytest.mark.asyncio
    async def test_non_finite_metadata_is_identical_across_channels(self) -> None:
        """WR-03: legacy NaN/Infinity stringifies in BOTH channels.

        ``json_dumps_strict`` writes ``"nan"``/``"inf"``; the structured
        channel must not drift to ``null`` via plain ``model_dump(mode="json")``.
        """
        backend = _mock_backend()
        backend.get_document.return_value = Document(
            doc_id="doc-1",
            path="a.md",
            content="x",
            metadata={"score": float("nan"), "inf": float("inf")},
        )

        result = await _make_server(backend).call_tool("get", {"path_or_docid": "doc-1"})

        payload = json.loads(result.content[0].text)
        assert payload == result.structured_content
        assert payload["document"]["metadata"] == {"score": "nan", "inf": "inf"}

    @pytest.mark.asyncio
    async def test_get_missing_document_is_a_tool_error(self) -> None:
        backend = _mock_backend()
        backend.get_document.return_value = None

        with pytest.raises(ToolError, match="Document not found"):
            await _make_server(backend).call_tool("get", {"path_or_docid": "missing"})

    @pytest.mark.asyncio
    async def test_multi_get_serializes_documents_and_errors(self) -> None:
        backend = _mock_backend()
        backend.get_documents_by_pattern.return_value = (
            [Document(doc_id="doc-1", path="a.md", content="alpha")],
            ["b.md: unreadable"],
        )

        result = await _make_server(backend).call_tool(
            "multi_get", {"pattern": "*.md", "max_bytes": 1024}
        )

        payload = json.loads(result.content[0].text)
        assert payload == result.structured_content
        assert payload["documents"][0]["doc_id"] == "doc-1"
        assert payload["errors"] == ["b.md: unreadable"]
        backend.get_documents_by_pattern.assert_awaited_once_with("*.md", 1024)


class TestStatusTool:
    """status keeps the existing output model and dual-channel contract."""

    @pytest.mark.asyncio
    async def test_serializes_collection_totals(self) -> None:
        backend = _mock_backend()
        backend.get_status.return_value = (
            [CollectionInfo(name="notes", document_count=3, last_updated="today")],
            3,
        )

        result = await _make_server(backend).call_tool("status", {})

        payload = json.loads(result.content[0].text)
        assert payload == {
            "collections": [
                {
                    "name": "notes",
                    "document_count": 3,
                    "last_updated": "today",
                    "size_bytes": None,
                }
            ],
            "total_documents": 3,
        }
        assert payload == result.structured_content


class TestMetadataTool:
    """The metadata tool surfaces the frozen Phase 20 envelope unchanged."""

    @pytest.mark.asyncio
    async def test_text_and_structured_content_exclude_none(self) -> None:
        backend = _mock_backend()

        result = await _make_server(backend).call_tool("metadata", {})

        payload = json.loads(result.content[0].text)
        assert payload == result.structured_content
        assert payload == _METADATA_ENVELOPE
        assert "filteredDocuments" not in payload

    @pytest.mark.asyncio
    async def test_unknown_collection_is_a_tool_error(self) -> None:
        backend = _mock_backend()
        backend.metadata.side_effect = ValueError("One or more collections were not found")

        with pytest.raises(ToolError, match="were not found"):
            await _make_server(backend).call_tool("metadata", {"collections": ["missing"]})

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "payload",
        [
            {"filter": {"field": "tags", "operator": "gt", "value": "x"}},
            {"match": {"field": "nope", "operator": "eq", "value": "x"}},
            {"filter": {"field": "tag", "operator": "nope", "value": "x"}},
            # WR-01: an out-of-double-range integer must stay a controlled error.
            {"filter": {"field": "priority", "operator": "gt", "value": 10**400}},
        ],
    )
    async def test_invalid_filter_or_match_is_a_tool_error(self, payload: dict) -> None:
        backend = _mock_backend()

        with pytest.raises(ToolError) as excinfo:
            await _make_server(backend).call_tool("metadata", payload)

        assert "filter" in str(excinfo.value)
        backend.metadata.assert_not_called()

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        ("payload", "operator", "field"),
        [
            ({"field": "path", "operator": "lt", "value": 5}, "lt", "path"),
            ({"field": "path", "operator": "eq", "value": 5}, "eq", "path"),
            ({"field": "path", "operator": "all", "value": ["a"]}, "all", "path"),
            (
                {"field": "path", "operator": "type", "value": "string", "caseInsensitive": True},
                "type",
                "path",
            ),
            ({"field": "mtime", "operator": "prefix", "value": "x"}, "prefix", "mtime"),
            ({"field": "mtime", "operator": "all", "value": [1]}, "all", "mtime"),
            ({"field": "mtime", "operator": "contains", "value": "x"}, "contains", "mtime"),
            (
                {"field": "mtime", "operator": "eq", "value": 1, "caseInsensitive": True},
                "eq",
                "mtime",
            ),
        ],
    )
    async def test_reserved_field_mistakes_are_tool_errors(
        self, payload: dict, operator: str, field: str
    ) -> None:
        """WR-02: the same rejected forms are controlled ToolErrors over MCP."""
        backend = _mock_backend()

        with pytest.raises(ToolError) as excinfo:
            await _make_server(backend).call_tool("metadata", {"filter": payload})

        text = str(excinfo.value)
        assert f"filter.{operator}:" in text
        assert field in text

    @pytest.mark.asyncio
    async def test_valid_call_returns_envelope_with_exact_remainders(self, backend) -> None:
        """Windows, remainders, and the built-in section travel in one payload."""
        _seed_metadata_rows(Path(backend.db_path))

        result = await _make_server(backend).call_tool("metadata", {"limit": 1, "value_limit": 1})

        payload = json.loads(result.content[0].text)
        assert payload == result.structured_content
        assert payload["documents"] == 3
        assert "filteredDocuments" not in payload
        assert payload["totalKeys"] == 2
        assert payload["remainingKeys"] == 1
        assert [entry["key"] for entry in payload["builtIns"]] == ["path", "mtime"]
        assert [entry["documents"] for entry in payload["builtIns"]] == [3, 3]
        assert payload["builtIns"][1]["types"][0]["range"] == {
            "min": 100.0,
            "median": 200.0,
            "max": 300.0,
        }
        assert [entry["key"] for entry in payload["keys"]] == ["tag"]
        tag_type = payload["keys"][0]["types"][0]
        assert len(tag_type["values"]) == 1
        assert tag_type["distinctValues"] == 2
        assert tag_type["remainingValues"] == 1

    @pytest.mark.asyncio
    async def test_filtered_call_includes_filtered_documents(self, backend) -> None:
        """A filter adds ``filteredDocuments`` and narrows the built-in counts."""
        _seed_metadata_rows(Path(backend.db_path))

        result = await _make_server(backend).call_tool(
            "metadata", {"filter": {"field": "tag", "operator": "eq", "value": "common"}}
        )

        payload = json.loads(result.content[0].text)
        assert payload["documents"] == 3
        assert payload["filteredDocuments"] == 2
        assert [entry["documents"] for entry in payload["builtIns"]] == [2, 2]

    @pytest.mark.asyncio
    async def test_match_only_call_omits_filtered_documents(self, backend) -> None:
        """A match-only call must pass ``None`` (never the empty fragment) as the filter."""
        _seed_metadata_rows(Path(backend.db_path))

        result = await _make_server(backend).call_tool(
            "metadata", {"match": {"field": "key", "operator": "prefix", "value": "ta"}}
        )

        payload = json.loads(result.content[0].text)
        assert "filteredDocuments" not in payload
        assert [entry["key"] for entry in payload["keys"]] == ["tag"]
        assert payload["documents"] == 3

    @pytest.mark.asyncio
    async def test_envelope_oracle_matches_both_channels(self, backend) -> None:
        """The Phase 20 oracle: the frozen envelope deep-equals both channels."""
        _seed_envelope_rows(Path(backend.db_path))

        result = await _make_server(backend).call_tool("metadata", {})

        assert result.structured_content == _METADATA_ENVELOPE
        assert json.loads(result.content[0].text) == _METADATA_ENVELOPE
        # No wrapper key, no null keys: the envelope is exactly the frozen set.
        assert set(result.structured_content) == {
            "documents",
            "totalKeys",
            "remainingKeys",
            "skippedKeys",
            "builtIns",
            "keys",
        }


# =============================================================================
# Task 2: direct lex/vec search paths (D-17)
# =============================================================================


class TestLexAndVecSearchTools:
    """Both one-shot search modes mirror the CLI and publish their schema."""

    @pytest.mark.asyncio
    async def test_min_score_is_published_for_both_inputs(self) -> None:
        tools = {tool.name: tool for tool in await _make_server(_mock_backend()).list_tools()}

        for name in ("lex_search", "vec_search"):
            props = tools[name].input_schema["properties"]
            assert props["min_score"]["minimum"] == 0.0
            assert props["min_score"]["default"] == 0.0
            assert tools[name].output_schema["type"] == "object"
            assert "results" in tools[name].output_schema["properties"]

    @pytest.mark.asyncio
    async def test_lex_search_keeps_dual_channel_parity(self) -> None:
        backend = _mock_backend()
        backend.lex_search.return_value = [
            SearchResult(doc_id="d1", path="/a.md", score=0.7),
        ]

        result = await _make_server(backend).call_tool("lex_search", {"query": "q"})

        assert result.is_error is False
        payload = json.loads(result.content[0].text)
        assert payload == result.structured_content
        assert payload["results"][0]["doc_id"] == "d1"

    @pytest.mark.asyncio
    async def test_vec_search_keeps_dual_channel_parity(self) -> None:
        backend = _mock_backend()
        backend.vec_search.return_value = [
            SearchResult(doc_id="d2", path="/b.md", score=0.5),
        ]

        result = await _make_server(backend).call_tool("vec_search", {"query": "q"})

        assert result.is_error is False
        payload = json.loads(result.content[0].text)
        assert payload == result.structured_content
        assert payload["results"][0]["doc_id"] == "d2"

    @pytest.mark.asyncio
    async def test_lex_and_vec_forward_min_score_and_filter(self) -> None:
        from sif.core.filters import parse_filter

        backend = _mock_backend()

        await _make_server(backend).call_tool(
            "lex_search", {"query": "q", "min_score": 0.4, "filter": _FILTER_PAYLOAD}
        )
        await _make_server(backend).call_tool(
            "vec_search",
            {"query": "q", "min_score": 0.6, "per_chunk": True, "filter": _FILTER_PAYLOAD},
        )

        lex_kwargs = backend.lex_search.call_args.kwargs
        assert lex_kwargs["min_score"] == 0.4
        assert lex_kwargs["filter_node"] == parse_filter(_FILTER_PAYLOAD)
        vec_kwargs = backend.vec_search.call_args.kwargs
        assert vec_kwargs["min_score"] == 0.6
        assert vec_kwargs["per_chunk"] is True
        assert vec_kwargs["filter_node"] == parse_filter(_FILTER_PAYLOAD)

    @pytest.mark.asyncio
    async def test_vec_unavailable_is_a_tool_error_with_the_remedy(self) -> None:
        backend = _mock_backend()
        remedy = (
            "Vector search requires an embedding model. Install the embedding "
            'backend with `pip install "docsif[embed]"`, check the SIF_MODEL_* '
            "settings, and retry."
        )
        backend.vec_search.side_effect = RuntimeError(remedy)

        with pytest.raises(ToolError) as excinfo:
            await _make_server(backend).call_tool("vec_search", {"query": "q"})

        assert "docsif[embed]" in str(excinfo.value)
        assert "SIF_MODEL_" in str(excinfo.value)

    @pytest.mark.asyncio
    async def test_invalid_filter_is_a_tool_error_on_both_direct_paths(self) -> None:
        backend = _mock_backend()

        for name in ("lex_search", "vec_search"):
            with pytest.raises(ToolError) as excinfo:
                await _make_server(backend).call_tool(
                    name, {"query": "q", "filter": _BAD_FILTER_PAYLOAD}
                )
            assert "filter.gt:" in str(excinfo.value)

        backend.lex_search.assert_not_called()
        backend.vec_search.assert_not_called()


# =============================================================================
# Task 3: the seven-tool contract battery (D-06/D-07/D-10/D-12)
# =============================================================================

_SEARCH_DOCS = [
    ("d1", "quantum machine learning algorithms"),
    ("d2", "quantum computing quick quantifiers"),
    ("d3", "studies of machine learning contexts"),
]


def _seed_search_rows(db_path: Path) -> None:
    """Seed the deterministic three-document corpus used by the seven tools."""
    _seed_documents(db_path, [(doc_id, body, {"tag": "x"}) for doc_id, body in _SEARCH_DOCS])


def _add_embeddings(db_path: Path, document_ids: list[str], *, dimension: int = 8) -> None:
    """Seed one chunk + vector row per document so vec_search has real rows."""
    import sqlite_vec

    bodies = dict(_SEARCH_DOCS)
    now = datetime.now(timezone.utc).isoformat()
    conn = sqlite3.connect(db_path)
    try:
        conn.enable_load_extension(True)
        sqlite_vec.load(conn)
        conn.enable_load_extension(False)
        with conn:
            conn.executemany(
                "INSERT OR IGNORE INTO document_chunks"
                " (id, document_id, sequence, content, created_at)"
                " VALUES (?, ?, 0, ?, ?)",
                [(f"chunk-{doc_id}", doc_id, bodies[doc_id], now) for doc_id in document_ids],
            )
            VectorSearcher(conn, embedding_dim=dimension).add_embeddings_batch(
                [
                    (f"e-{doc_id}", doc_id, f"chunk-{doc_id}", [0.1] * dimension)
                    for doc_id in document_ids
                ]
            )
    finally:
        conn.close()


class _FakeVectorManager:
    """vec_search manager double: fixed query vectors, no model load."""

    def embed_query(self, _text: str) -> list[float]:
        return [0.1] * 8


def _assert_future_write_tool_policy(annotations: ToolAnnotations) -> None:
    """D-07: a future mutation tool must not claim read-only and must warn.

    Any write-capable tool registered later has to set ``read_only_hint=False``
    and ``destructive_hint=True`` where its effect is destructive. This helper
    is the executable policy the read-only enumeration below is the complement
    of.
    """
    assert annotations.read_only_hint is False
    if annotations.destructive_hint is not None:
        assert annotations.destructive_hint is True


class TestSevenToolEnumeration:
    """The published tools/list surface is exact, ordered, and honest."""

    @pytest.mark.asyncio
    async def test_exact_ordered_tool_set_with_no_mutation_names(self) -> None:
        tools = await _make_server(_mock_backend()).list_tools()

        assert [tool.name for tool in tools] == _EXPECTED_TOOL_ORDER
        assert {tool.name for tool in tools}.isdisjoint(_MUTATION_TOOL_NAMES)

    @pytest.mark.asyncio
    async def test_every_tool_is_read_only_with_truthful_annotations(self) -> None:
        for tool in await _make_server(_mock_backend()).list_tools():
            assert tool.annotations is not None, tool.name
            assert tool.annotations.read_only_hint is True, tool.name
            assert tool.annotations.open_world_hint is False, tool.name
            # D-07: only meaningful for non-read-only tools, so never set here.
            assert tool.annotations.idempotent_hint is None, tool.name
            assert tool.annotations.destructive_hint is None, tool.name

    @pytest.mark.asyncio
    async def test_every_tool_publishes_a_non_empty_output_schema(self) -> None:
        for tool in await _make_server(_mock_backend()).list_tools():
            assert tool.output_schema is not None, tool.name
            assert tool.output_schema["type"] == "object", tool.name
            assert tool.output_schema.get("properties"), tool.name

    @pytest.mark.asyncio
    async def test_descriptions_are_the_reviewed_constants(self) -> None:
        for tool in await _make_server(_mock_backend()).list_tools():
            assert tool.description == TOOL_DESCRIPTIONS[tool.name], tool.name

    def test_future_write_policy_rejects_a_read_only_claim(self) -> None:
        _assert_future_write_tool_policy(
            ToolAnnotations(read_only_hint=False, destructive_hint=True)
        )
        _assert_future_write_tool_policy(
            ToolAnnotations(read_only_hint=False, open_world_hint=False)
        )
        with pytest.raises(AssertionError):
            _assert_future_write_tool_policy(ToolAnnotations(read_only_hint=True))


class TestEmptyIndexAndIdempotency:
    """Read-only tools never write: empty status and repeated reads are stable."""

    @pytest.mark.asyncio
    async def test_status_on_a_real_empty_index(self, tmp_path: Path) -> None:
        backend = SearchBackend(str(tmp_path / "empty.db"), settings=_settings())

        result = await _make_server(backend).call_tool("status", {})

        payload = json.loads(result.content[0].text)
        assert payload == {"collections": [], "total_documents": 0}
        assert payload == result.structured_content

    @pytest.mark.asyncio
    async def test_all_seven_tools_are_dual_channel_and_idempotent(self, tmp_path: Path) -> None:
        """Every tool's text parses to structuredContent; a repeat writes nothing."""
        db_path = tmp_path / "seven.db"
        backend = SearchBackend(str(db_path), settings=_settings())
        _seed_search_rows(db_path)
        _add_embeddings(db_path, ["d1", "d2", "d3"])
        manager = _FakeVectorManager()
        calls: dict[str, dict[str, object]] = {
            "query": {"query": "quantum", "limit": 2},
            "get": {"path_or_docid": "d1"},
            "multi_get": {"pattern": "d1.md"},
            "status": {},
            "metadata": {},
            "lex_search": {"query": "quantum", "limit": 2},
            "vec_search": {"query": "quantum", "limit": 2},
        }

        import sqlite_vec

        monitor = sqlite3.connect(db_path)
        monitor.enable_load_extension(True)
        sqlite_vec.load(monitor)
        monitor.enable_load_extension(False)
        try:
            before_version = monitor.execute("PRAGMA data_version").fetchone()[0]
            tables = ("documents", "document_chunks", "document_embeddings", "query_log")
            before_counts = tuple(
                monitor.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0] for table in tables
            )
            first: dict[str, object] = {}
            second: dict[str, object] = {}
            with patch.object(SearchBackend, "_ensure_embedder", return_value=manager):
                for name, arguments in calls.items():
                    server = _make_server(backend)
                    first[name] = await server.call_tool(name, arguments)
                    second[name] = await server.call_tool(name, arguments)
            after_version = monitor.execute("PRAGMA data_version").fetchone()[0]
            after_counts = tuple(
                monitor.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0] for table in tables
            )
        finally:
            monitor.close()

        assert before_version == after_version
        assert before_counts == after_counts
        for name in calls:
            result = first[name]
            assert result.is_error is False, name
            payload = json.loads(result.content[0].text)
            assert payload == result.structured_content, name
            assert result.structured_content == second[name].structured_content, name


def _initialize_http(client: TestClient) -> str:
    """Complete a 2024-11-05 handshake and return the session id."""
    response = client.post(
        "/mcp",
        json={
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "sif-tools", "version": "1"},
            },
        },
    )
    assert response.status_code == 200
    session_id = response.headers.get("mcp-session-id")
    assert session_id
    client.post(
        "/mcp",
        json={"jsonrpc": "2.0", "method": "notifications/initialized", "params": {}},
        headers={"mcp-session-id": session_id},
    )
    return session_id


def test_expected_errors_are_iserror_results_not_protocol_errors(tmp_path: Path) -> None:
    """D-08: expected tool-input failures ride a successful JSON-RPC envelope."""
    db_path = tmp_path / "errors.db"
    # Migrate the real schema first (the app's lifespan backend would otherwise
    # be the first writer and the handshake would race the seeded rows).
    SearchBackend(str(db_path), settings=_settings())
    _seed_search_rows(db_path)
    app = create_http_app(str(db_path), settings=_settings())

    cases = [
        ("query", {"query": "q", "filter": _BAD_FILTER_PAYLOAD}),
        ("metadata", {"match": {"field": "nope", "operator": "eq", "value": "x"}}),
        ("metadata", {"collections": ["missing"]}),
        ("get", {"path_or_docid": "missing"}),
        ("lex_search", {"query": "q", "filter": _BAD_FILTER_PAYLOAD}),
        ("vec_search", {"query": "q", "filter": _BAD_FILTER_PAYLOAD}),
    ]

    with TestClient(app, base_url="http://localhost") as client:
        session_id = _initialize_http(client)
        for name, arguments in cases:
            response = client.post(
                "/mcp",
                json={
                    "jsonrpc": "2.0",
                    "id": 9,
                    "method": "tools/call",
                    "params": {"name": name, "arguments": arguments},
                },
                headers={"mcp-session-id": session_id},
            )

            assert response.status_code == 200, name
            body = response.json()
            assert "error" not in body, name
            assert body["result"]["isError"] is True, name
            assert body["result"]["content"][0]["text"], name


class TestQueryRerankOption:
    """D-17: the additive rerank parameter is opt-in and forwarded verbatim."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize("value", [True, False, None])
    async def test_forwards_rerank_or_none(self, value: bool | None) -> None:
        backend = _mock_backend()
        arguments: dict[str, object] = {"query": "q"}
        if value is not None:
            arguments["rerank"] = value

        await _make_server(backend).call_tool("query", arguments)

        assert backend.hybrid_search.call_args.kwargs["rerank"] is value

    @pytest.mark.asyncio
    async def test_published_schema_keeps_rerank_optional(self) -> None:
        tools = {tool.name: tool for tool in await _make_server(_mock_backend()).list_tools()}
        schema = tools["query"].input_schema
        rerank = schema["properties"]["rerank"]

        assert any(option.get("type") == "boolean" for option in rerank.get("anyOf", [rerank]))
        assert "rerank" not in schema.get("required", [])
