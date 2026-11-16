"""Citation-grade MCP output battery (Phase 22 D-11/D-12).

Task 2 proves the additive citation contract: snippet line windows, the
stored ``documents.checksum`` as ``content_hash`` fetched in one batched page
lookup, and full/ranged ``get`` line ranges. Task 3 extends this module with
the frozen Phase 20 envelope oracle and the citation edge cases.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from mcp.server import MCPServer

from sif.config.settings import Settings
from sif.core.models import SearchResult as CoreSearchResult
from sif.database.database import Database
from sif.mcp.backend import SearchBackend
from sif.mcp.protocol import (
    Document,
    GetOutput,
    MetadataOutput,
    MultiGetOutput,
    QueryOutput,
    SearchResult,
)
from sif.mcp.tools import register_tools


# 0-based line indexes are 1-based document lines in the assertions below.
_MULTI_CONTENT = "line one\nline two\nline three\nline four\nline five"
_STORED_CHECKSUMS = {
    "multi": "stored-checksum-multi",
    "trailing": "stored-checksum-trailing",
    "second": "stored-checksum-second",
}


def _settings() -> Settings:
    """Hermetic settings: small dimension, no cache side effects."""
    return Settings(
        _env_file=None,
        embedding_dim=8,
        model_name="test",
        cache_embeddings=False,
    )


def _seed_citation_db(tmp_path: Path) -> Path:
    """Real production DDL with multi-line documents and stored checksums."""
    db_path = tmp_path / "mcp-citations.db"
    db = Database(db_path)
    try:
        db.init_schema(embedding_dim=8)
        now = datetime.now(timezone.utc).isoformat()
        with db.connection:
            db.connection.execute(
                "INSERT INTO collections (id, name, path, created_at, updated_at)"
                " VALUES ('c1', 'notes', '/vault', ?, ?)",
                (now, now),
            )
            documents = [
                ("multi", _MULTI_CONTENT),
                ("trailing", "alpha\nbeta\n"),
                ("second", "second body"),
            ]
            db.connection.executemany(
                "INSERT INTO documents (id, collection_id, path, filename, title,"
                " content, checksum, mtime, created_at, updated_at)"
                " VALUES (?, 'c1', ?, ?, ?, ?, ?, 1.0, ?, ?)",
                [
                    (
                        doc_id,
                        f"/vault/{doc_id}.md",
                        f"{doc_id}.md",
                        doc_id,
                        body,
                        _STORED_CHECKSUMS[doc_id],
                        now,
                        now,
                    )
                    for doc_id, body in documents
                ],
            )
    finally:
        db.close()
    return db_path


def _backend(db_path: Path) -> SearchBackend:
    """Construct a model-free backend and seed the lazy path (no model load)."""
    backend = SearchBackend(str(db_path), settings=_settings())
    backend._load_attempted = True
    backend._manager = MagicMock()
    backend._embedder = MagicMock()
    backend._identity = None
    backend._dimension = 8
    return backend


def _core_result(
    doc_id: str,
    *,
    snippet: str | None = None,
    line_start: int | None = None,
    line_end: int | None = None,
    vectors_stale: bool = False,
) -> CoreSearchResult:
    """A core search row shaped like the pipeline's snippet-stage output."""
    return CoreSearchResult(
        document_id=doc_id,
        title=doc_id,
        path=f"/vault/{doc_id}.md",
        collection_name="notes",
        score=0.9,
        snippet=snippet,
        line_start=line_start,
        line_end=line_end,
        vectors_stale=vectors_stale,
        chunk_id=f"chunk-{doc_id}",
        sequence=1,
        chunk_matches=2,
    )


class TestQueryCitationFields:
    """MCP SearchResult carries snippet, stored hash, and the snippet window."""

    @pytest.mark.asyncio
    async def test_query_maps_citation_fields_and_preserves_order(self, tmp_path: Path) -> None:
        backend = _backend(_seed_citation_db(tmp_path))
        cores = [
            _core_result(
                "multi",
                snippet="line three",
                line_start=3,
                line_end=3,
                vectors_stale=True,
            ),
            _core_result("second"),
        ]

        with patch("sif.mcp.backend.SearchPipeline") as pipeline_cls:
            pipeline_cls.return_value.search.return_value = cores
            results = await backend.hybrid_search("anything")

        assert [r.doc_id for r in results] == ["multi", "second"]
        assert results[0].snippet == "line three"
        assert (results[0].line_start, results[0].line_end) == (3, 3)
        assert results[0].content_hash == _STORED_CHECKSUMS["multi"]
        assert results[0].metadata["vectors_stale"] is True
        assert results[0].metadata["chunk_id"] == "chunk-multi"
        assert results[0].metadata["chunk_matches"] == 2
        # A row with no snippet window keeps the fields unset.
        assert results[1].snippet is None
        assert results[1].content_hash == _STORED_CHECKSUMS["second"]
        assert (results[1].line_start, results[1].line_end) == (None, None)

    @pytest.mark.asyncio
    async def test_one_batched_checksum_lookup_per_page(self, tmp_path: Path) -> None:
        backend = _backend(_seed_citation_db(tmp_path))
        cores = [_core_result("multi"), _core_result("second")]

        with (
            patch("sif.mcp.backend.SearchPipeline") as pipeline_cls,
            patch("sif.mcp.backend.DocumentRepository") as repo_cls,
        ):
            pipeline_cls.return_value.search.return_value = cores
            repo_cls.return_value.get_checksums.return_value = {
                "multi": _STORED_CHECKSUMS["multi"],
                "second": _STORED_CHECKSUMS["second"],
            }
            results = await backend.hybrid_search("anything")

        assert repo_cls.return_value.get_checksums.call_count == 1
        assert repo_cls.return_value.get_checksums.call_args.args[0] == ["multi", "second"]
        assert [r.content_hash for r in results] == [
            _STORED_CHECKSUMS["multi"],
            _STORED_CHECKSUMS["second"],
        ]

    @pytest.mark.asyncio
    async def test_direct_lex_route_still_attaches_the_stored_hash(self, tmp_path: Path) -> None:
        """Documented 22-04 deviation: no snippet window, hash still attached."""
        backend = _backend(_seed_citation_db(tmp_path))

        results = await backend.hybrid_search("lex: line three")

        assert results
        assert results[0].doc_id == "multi"
        assert results[0].snippet is None
        assert results[0].line_start is None
        assert results[0].line_end is None
        assert results[0].content_hash == _STORED_CHECKSUMS["multi"]


class TestGetCitationRanges:
    """``get``/``multi_get`` always populate the hash and an inclusive range."""

    @pytest.mark.asyncio
    async def test_full_get_is_one_through_n(self, tmp_path: Path) -> None:
        backend = _backend(_seed_citation_db(tmp_path))

        document = await backend.get_document("multi")

        assert document is not None
        assert document.content == _MULTI_CONTENT
        assert (document.line_start, document.line_end) == (1, 5)
        assert document.content_hash == _STORED_CHECKSUMS["multi"]

    @pytest.mark.asyncio
    async def test_ranged_get_is_inclusive_and_the_next_range_is_adjacent(
        self, tmp_path: Path
    ) -> None:
        backend = _backend(_seed_citation_db(tmp_path))

        first = await backend.get_document("multi", from_line=2, max_lines=3)
        second = await backend.get_document("multi", from_line=5, max_lines=1)

        assert first is not None
        assert second is not None
        assert first.content == "line two\nline three\nline four"
        assert (first.line_start, first.line_end) == (2, 4)
        assert second.content == "line five"
        assert (second.line_start, second.line_end) == (5, 5)

    @pytest.mark.asyncio
    async def test_trailing_newline_does_not_create_an_extra_document_line(
        self, tmp_path: Path
    ) -> None:
        backend = _backend(_seed_citation_db(tmp_path))

        document = await backend.get_document("trailing")

        assert document is not None
        assert document.content == "alpha\nbeta\n"
        assert (document.line_start, document.line_end) == (1, 2)

    @pytest.mark.asyncio
    async def test_multi_get_carries_hashes_and_full_ranges(self, tmp_path: Path) -> None:
        backend = _backend(_seed_citation_db(tmp_path))

        documents, errors = await backend.get_documents_by_pattern("*.md")

        assert errors == []
        by_id = {document.doc_id: document for document in documents}
        assert set(by_id) == {"multi", "trailing", "second"}
        assert by_id["multi"].content_hash == _STORED_CHECKSUMS["multi"]
        assert (by_id["multi"].line_start, by_id["multi"].line_end) == (1, 5)
        assert by_id["second"].content_hash == _STORED_CHECKSUMS["second"]
        assert (by_id["second"].line_start, by_id["second"].line_end) == (1, 1)

    @pytest.mark.asyncio
    async def test_content_hash_is_the_stored_value_not_recomputed(self, tmp_path: Path) -> None:
        backend = _backend(_seed_citation_db(tmp_path))

        document = await backend.get_document("multi")

        assert document is not None
        assert document.content_hash == _STORED_CHECKSUMS["multi"]
        assert document.content_hash != hashlib.sha256(_MULTI_CONTENT.encode()).hexdigest()


class TestCitationSchemas:
    """The generated output models expose the additive citation fields."""

    def test_query_output_schema_includes_the_four_citation_fields(self) -> None:
        properties = QueryOutput.model_json_schema()["$defs"]["SearchResult"]["properties"]
        for field in ("snippet", "content_hash", "line_start", "line_end"):
            assert field in properties

    def test_document_schema_includes_content_hash_and_keeps_line_fields(self) -> None:
        properties = GetOutput.model_json_schema()["$defs"]["Document"]["properties"]
        for field in ("content_hash", "line_start", "line_end"):
            assert field in properties

    def test_metadata_envelope_has_no_citation_fields(self) -> None:
        fields = set(MetadataOutput.model_fields)
        assert not fields & {"snippet", "content_hash", "line_start", "line_end"}

    def test_multi_get_nests_the_citation_document(self) -> None:
        properties = MultiGetOutput.model_json_schema()["$defs"]["Document"]["properties"]
        assert "content_hash" in properties


class TestCitationSerialization:
    """Both MCP channels serialize the same citation payload."""

    @pytest.mark.asyncio
    async def test_query_text_and_structured_content_agree(self, tmp_path: Path) -> None:
        backend = _backend(_seed_citation_db(tmp_path))
        cores = [_core_result("multi", snippet="line three", line_start=3, line_end=3)]
        with patch("sif.mcp.backend.SearchPipeline") as pipeline_cls:
            pipeline_cls.return_value.search.return_value = cores
            results = await backend.hybrid_search("anything")

        server = MCPServer("citation-serialization")
        register_tools(server, backend)
        with patch.object(backend, "hybrid_search", return_value=results):
            result = await server.call_tool("query", {"query": "anything"})

        payload = json.loads(result.content[0].text)
        assert payload == result.structured_content
        assert payload["results"][0]["snippet"] == "line three"
        assert payload["results"][0]["content_hash"] == _STORED_CHECKSUMS["multi"]
        assert payload["results"][0]["line_start"] == 3
        assert payload["results"][0]["line_end"] == 3

    @pytest.mark.asyncio
    async def test_get_text_and_structured_content_agree(self, tmp_path: Path) -> None:
        backend = _backend(_seed_citation_db(tmp_path))
        server = MCPServer("citation-get-serialization")
        register_tools(server, backend)
        result = await server.call_tool("get", {"path_or_docid": "multi"})

        payload = json.loads(result.content[0].text)
        assert payload == result.structured_content
        document = payload["document"]
        assert document["content_hash"] == _STORED_CHECKSUMS["multi"]
        assert document["line_start"] == 1
        assert document["line_end"] == 5


def test_protocol_models_keep_the_pre_existing_fields() -> None:
    """D-12: citation fields are additive; no existing field is renamed/dropped."""
    assert set(SearchResult.model_fields) >= {
        "doc_id",
        "path",
        "title",
        "content",
        "score",
        "highlights",
        "metadata",
    }
    assert set(Document.model_fields) >= {
        "doc_id",
        "path",
        "title",
        "content",
        "metadata",
        "line_start",
        "line_end",
        "collection_id",
    }
