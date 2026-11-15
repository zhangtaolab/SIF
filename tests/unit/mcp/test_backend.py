"""Tests for SearchBackend."""

from __future__ import annotations

import json
import logging
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pydantic import ValidationError

from sif.config.settings import Settings
from sif.database.database import Database
from sif.mcp import backend as backend_module
from sif.mcp.backend import HybridSearchResults, SearchBackend, _truncate_content
from sif.mcp.protocol import CollectionInfo, Document, QueryInput, SearchResult
from sif.models.embedding import ModelType
from sif.utils.paths import normalize_path


@pytest.fixture
def backend(tmp_path: Path):
    """Create a SearchBackend with mocked settings."""
    with patch("sif.mcp.backend.get_settings") as mock_settings:
        mock_settings.return_value = MagicMock(embedding_dim=1024)
        return SearchBackend(str(tmp_path / "test.db"))


@pytest.mark.asyncio
async def test_search_backend_init(backend, tmp_path: Path):
    """Verify SearchBackend stores db_path and settings."""
    assert backend.db_path == str(tmp_path / "test.db")
    assert backend.settings is not None


@pytest.mark.asyncio
async def test_search_backend_forwards_api_settings_to_factory(tmp_path: Path):
    """Verify SearchBackend passes api_key/api_base/dim/cache_dir to the factory."""
    mock_embedder = MagicMock()
    settings = MagicMock(
        model_type="openai",
        model_name="text-embedding-3-small",
        model_path=None,
        api_key="sk-test",
        api_base="https://api.example.com/v1",
        embedding_dim=8,
        cache_embeddings=False,
    )

    with (
        patch("sif.mcp.backend.get_settings", return_value=settings),
        patch("sif.mcp.backend.EmbeddingModelFactory") as mock_factory_cls,
    ):
        mock_factory_cls.return_value.create_model.return_value = mock_embedder
        backend = SearchBackend(str(tmp_path / "test.db"))

    call = mock_factory_cls.return_value.create_model.call_args
    assert call.args[0] == ModelType.OPENAI
    assert call.kwargs["api_key"] == "sk-test"
    assert call.kwargs["api_base"] == "https://api.example.com/v1"
    assert call.kwargs["embedding_dim"] == 8
    assert call.kwargs["cache_dir"] is None
    assert backend._embedder is mock_embedder


@pytest.mark.asyncio
async def test_hybrid_search_mocks(backend):
    """Mock hybrid search returning results."""
    mock_result = MagicMock()
    mock_result.document_id = "doc1"
    mock_result.path = "/test.md"
    mock_result.title = "Test"
    mock_result.content = None
    mock_result.score = 0.9
    mock_result.highlights = ["highlight"]
    mock_result.rank = 1
    mock_result.collection_name = "default"
    mock_result.vectors_stale = True
    mock_result.chunk_id = "chunk-1"
    mock_result.sequence = 2
    mock_result.chunk_matches = 3

    with patch("sif.mcp.backend.SearchPipeline") as mock_pipeline:
        mock_pipeline.return_value.search.return_value = [mock_result]
        results = await backend.hybrid_search("test query")

    assert len(results) == 1
    assert isinstance(results[0], SearchResult)
    assert results[0].doc_id == "doc1"
    # D-11 / RESEARCH B5: the backend re-maps core fields explicitly, so an
    # unknown field is DROPPED at this boundary unless forwarded — the flag
    # must ride the metadata dict with the core result's value.
    assert results[0].metadata.get("vectors_stale") is True
    assert results[0].metadata["rank"] == 1
    # CORR-02/D-02/D-03: chunk identity and the collapsed count cross the
    # boundary through the same explicit map.
    assert results[0].metadata["chunk_id"] == "chunk-1"
    assert results[0].metadata["sequence"] == 2
    assert results[0].metadata["chunk_matches"] == 3


@pytest.mark.asyncio
async def test_get_document_found(backend):
    """Mock get_document returning a document."""
    mock_doc = MagicMock()
    mock_doc.id = "doc1"
    mock_doc.path = "/test.md"
    mock_doc.title = "Test"
    mock_doc.content = "Hello\nWorld"
    mock_doc.metadata = {}
    mock_doc.collection_id = "coll1"

    with patch("sif.mcp.backend.DocumentRepository") as mock_repo:
        mock_repo.return_value.get_by_id.return_value = mock_doc
        result = await backend.get_document("doc1")

    assert isinstance(result, Document)
    assert result.doc_id == "doc1"
    assert result.content == "Hello\nWorld"


@pytest.mark.asyncio
async def test_get_document_with_line_slicing(backend):
    """Verify line slicing in get_document."""
    mock_doc = MagicMock()
    mock_doc.id = "doc1"
    mock_doc.path = "/test.md"
    mock_doc.title = "Test"
    mock_doc.content = "line1\nline2\nline3\nline4"
    mock_doc.metadata = {}
    mock_doc.collection_id = "coll1"

    with patch("sif.mcp.backend.DocumentRepository") as mock_repo:
        mock_repo.return_value.get_by_id.return_value = mock_doc
        result = await backend.get_document("doc1", from_line=2, max_lines=2)

    assert result.line_start == 2
    assert result.content == "line2\nline3"


@pytest.mark.asyncio
async def test_get_document_max_lines_only(backend):
    """Phase 10 WR-07: max_lines alone slices from line 1 (user decision)."""
    mock_doc = MagicMock()
    mock_doc.id = "doc1"
    mock_doc.path = "/test.md"
    mock_doc.title = "Test"
    mock_doc.content = "line1\nline2\nline3\nline4"
    mock_doc.metadata = {}
    mock_doc.collection_id = "coll1"

    with patch("sif.mcp.backend.DocumentRepository") as mock_repo:
        mock_repo.return_value.get_by_id.return_value = mock_doc
        result = await backend.get_document("doc1", max_lines=2)

    assert result.content == "line1\nline2"
    assert result.line_start == 1
    assert result.line_end == 2


@pytest.mark.asyncio
async def test_get_document_from_line_only(backend):
    """Verify from_line alone slices through the document end."""
    mock_doc = MagicMock()
    mock_doc.id = "doc1"
    mock_doc.path = "/test.md"
    mock_doc.title = "Test"
    mock_doc.content = "line1\nline2\nline3\nline4"
    mock_doc.metadata = {}
    mock_doc.collection_id = "coll1"

    with patch("sif.mcp.backend.DocumentRepository") as mock_repo:
        mock_repo.return_value.get_by_id.return_value = mock_doc
        result = await backend.get_document("doc1", from_line=3)

    assert result.content == "line3\nline4"
    assert result.line_start == 3
    assert result.line_end == 4


@pytest.mark.asyncio
async def test_get_document_no_line_params(backend):
    """Verify omitting both line params returns the full document."""
    mock_doc = MagicMock()
    mock_doc.id = "doc1"
    mock_doc.path = "/test.md"
    mock_doc.title = "Test"
    mock_doc.content = "line1\nline2\nline3\nline4"
    mock_doc.metadata = {}
    mock_doc.collection_id = "coll1"

    with patch("sif.mcp.backend.DocumentRepository") as mock_repo:
        mock_repo.return_value.get_by_id.return_value = mock_doc
        result = await backend.get_document("doc1")

    assert result.content == "line1\nline2\nline3\nline4"
    assert result.line_start is None
    assert result.line_end is None


@pytest.mark.asyncio
async def test_get_document_not_found(backend):
    """Verify get_document returns None when not found."""
    with (
        patch("sif.mcp.backend.DocumentRepository") as mock_repo,
        patch("sif.mcp.backend.CollectionRepository") as mock_coll_repo,
    ):
        mock_repo.return_value.get_by_id.return_value = None
        mock_repo.return_value.get_by_path.return_value = None
        mock_coll_repo.return_value.list_all.return_value = []
        result = await backend.get_document("missing")

    assert result is None


@pytest.mark.asyncio
async def test_get_documents_by_pattern(backend):
    """Mock pattern matching documents."""
    mock_doc = MagicMock()
    mock_doc.id = "doc1"
    mock_doc.path = "/notes/test.md"
    mock_doc.filename = "test.md"
    mock_doc.title = "Test"
    mock_doc.content = "Hello"
    mock_doc.metadata = {}
    mock_doc.collection_id = "coll1"

    with (
        patch("sif.mcp.backend.CollectionRepository") as mock_coll_repo,
        patch("sif.mcp.backend.DocumentRepository") as mock_doc_repo,
    ):
        mock_coll_repo.return_value.list_all.return_value = [MagicMock(id="coll1")]
        mock_doc_repo.return_value.list_by_collection.return_value = [mock_doc]
        docs, errors = await backend.get_documents_by_pattern("*.md")

    assert len(docs) == 1
    assert docs[0].path == "/notes/test.md"
    assert errors == []


@pytest.mark.asyncio
async def test_get_documents_by_pattern_max_bytes(backend):
    """Verify max_bytes truncation."""
    mock_doc = MagicMock()
    mock_doc.id = "doc1"
    mock_doc.path = "/notes/test.md"
    mock_doc.filename = "test.md"
    mock_doc.title = "Test"
    mock_doc.content = "x" * 200
    mock_doc.metadata = {}
    mock_doc.collection_id = "coll1"

    with (
        patch("sif.mcp.backend.CollectionRepository") as mock_coll_repo,
        patch("sif.mcp.backend.DocumentRepository") as mock_doc_repo,
    ):
        mock_coll_repo.return_value.list_all.return_value = [MagicMock(id="coll1")]
        mock_doc_repo.return_value.list_by_collection.return_value = [mock_doc]
        docs, errors = await backend.get_documents_by_pattern("*.md", max_bytes=100)

    assert len(docs) == 0
    assert len(errors) == 1
    assert "Max bytes limit reached" in errors[0]


@pytest.mark.asyncio
async def test_get_document_alias_path_normalized(backend, tmp_path: Path):
    """get_document canonicalizes a symlink-alias path before the path lookup."""
    real_dir = tmp_path / "notes_real"
    real_dir.mkdir()
    (real_dir / "a.md").write_text("hello", encoding="utf-8")
    alias_dir = tmp_path / "notes_alias"
    os.symlink(real_dir, alias_dir)
    alias_arg = str(alias_dir / "a.md")

    mock_doc = MagicMock()
    mock_doc.id = "doc1"
    mock_doc.path = str(real_dir / "a.md")
    mock_doc.title = "Test"
    mock_doc.content = "Hello"
    mock_doc.metadata = {}
    mock_doc.collection_id = "coll1"

    with (
        patch("sif.mcp.backend.DocumentRepository") as mock_repo,
        patch("sif.mcp.backend.CollectionRepository") as mock_coll_repo,
    ):
        mock_repo.return_value.get_by_id.return_value = None
        mock_repo.return_value.get_by_path.return_value = mock_doc
        mock_coll_repo.return_value.list_all.return_value = [MagicMock(id="coll1")]
        result = await backend.get_document(alias_arg)

    assert result is not None
    assert result.doc_id == "doc1"
    get_by_path_args = mock_repo.return_value.get_by_path.call_args.args
    assert get_by_path_args[0] == normalize_path(alias_arg)
    assert get_by_path_args[0] == str(real_dir / "a.md")


@pytest.mark.asyncio
async def test_get_documents_by_pattern_alias_prefix(backend, tmp_path: Path):
    """A glob whose directory prefix is a symlink alias matches stored real paths."""
    real_dir = tmp_path / "notes_real"
    real_dir.mkdir()
    (real_dir / "a.md").write_text("hello", encoding="utf-8")
    alias_dir = tmp_path / "notes_alias"
    os.symlink(real_dir, alias_dir)

    mock_doc = MagicMock()
    mock_doc.id = "doc1"
    mock_doc.path = str(real_dir / "a.md")
    mock_doc.filename = "a.md"
    mock_doc.title = "Test"
    mock_doc.content = "Hello"
    mock_doc.metadata = {}
    mock_doc.collection_id = "coll1"

    with (
        patch("sif.mcp.backend.CollectionRepository") as mock_coll_repo,
        patch("sif.mcp.backend.DocumentRepository") as mock_doc_repo,
    ):
        mock_coll_repo.return_value.list_all.return_value = [MagicMock(id="coll1")]
        mock_doc_repo.return_value.list_by_collection.return_value = [mock_doc]
        docs, errors = await backend.get_documents_by_pattern(str(alias_dir / "*.md"))

    assert len(docs) == 1
    assert docs[0].path == str(real_dir / "a.md")
    assert errors == []


@pytest.mark.asyncio
async def test_get_status(backend):
    """Mock status returning collections."""
    mock_coll = MagicMock()
    mock_coll.id = "coll1"
    mock_coll.name = "notes"
    mock_coll.last_indexed_at = None

    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_cursor.fetchone.return_value = [5]
    mock_conn.execute.return_value = mock_cursor

    with (
        patch("sif.mcp.backend.CollectionRepository") as mock_repo,
        patch("sif.mcp.backend.DatabaseConnection") as mock_db,
    ):
        mock_repo.return_value.list_all.return_value = [mock_coll]
        mock_db.return_value.transaction.return_value.__enter__ = MagicMock(return_value=mock_conn)
        mock_db.return_value.transaction.return_value.__exit__ = MagicMock(return_value=False)
        collections, total = await backend.get_status()

    assert isinstance(collections, list)
    assert isinstance(collections[0], CollectionInfo)
    assert collections[0].name == "notes"
    assert total == 5


def test_content_truncation():
    """Test _truncate_content with >100KB input."""
    large = "x" * (100 * 1024 + 100)
    result = _truncate_content(large)
    assert len(result.encode("utf-8")) <= 100 * 1024 + 20
    assert result.endswith("... [truncated]")


# =============================================================================
# Hybrid fusion weight overrides (Phase 15, D-03/D-04)
# =============================================================================


def _weight_result() -> MagicMock:
    """A mock core result carrying the fields hybrid_search re-maps."""
    mock_result = MagicMock()
    mock_result.document_id = "doc1"
    mock_result.path = "/test.md"
    mock_result.title = "Test"
    mock_result.content = None
    mock_result.score = 0.9
    mock_result.highlights = ["highlight"]
    mock_result.rank = 1
    mock_result.collection_name = "default"
    mock_result.vectors_stale = False
    # CORR-02 boundary fields: the re-map copies all three explicitly.
    mock_result.chunk_id = None
    mock_result.sequence = None
    mock_result.chunk_matches = 0
    return mock_result


def _settings_backend(db_path: Path) -> SearchBackend:
    """Backend whose server settings pin rrf_k=7 / 2.0 / 0.5 (D-04 fallback)."""
    settings = MagicMock(
        embedding_dim=1024,
        rrf_k=7,
        bm25_weight=2.0,
        vector_weight=0.5,
    )
    with patch("sif.mcp.backend.get_settings", return_value=settings):
        return SearchBackend(str(db_path))


class TestHybridSearchWeightOverrides:
    """Request weight fields reach SearchOptions; absent ones hit settings."""

    @pytest.mark.asyncio
    async def test_request_weights_flow_into_options(self, backend) -> None:
        """Explicit rrf_k/bm25_weight/vector_weight ride SearchOptions verbatim."""
        with patch("sif.mcp.backend.SearchPipeline") as mock_pipeline:
            mock_pipeline.return_value.search.return_value = [_weight_result()]
            await backend.hybrid_search(
                "test query",
                rrf_k=5,
                bm25_weight=3.0,
                vector_weight=0.5,
            )

        options = mock_pipeline.return_value.search.call_args[0][1]
        assert options.rrf_k == 5
        assert options.bm25_weight == 3.0
        assert options.vector_weight == 0.5

    @pytest.mark.asyncio
    async def test_absent_fields_fall_back_to_server_settings(self, tmp_path: Path) -> None:
        """No weight params -> the server process's SIF_ settings fill options."""
        backend = _settings_backend(tmp_path / "test.db")

        with patch("sif.mcp.backend.SearchPipeline") as mock_pipeline:
            mock_pipeline.return_value.search.return_value = [_weight_result()]
            await backend.hybrid_search("test query")

        options = mock_pipeline.return_value.search.call_args[0][1]
        assert options.rrf_k == 7
        assert options.bm25_weight == 2.0
        assert options.vector_weight == 0.5

    @pytest.mark.asyncio
    async def test_request_field_overrides_settings(self, tmp_path: Path) -> None:
        """A request field beats the server setting; unset knobs still fall back."""
        backend = _settings_backend(tmp_path / "test.db")

        with patch("sif.mcp.backend.SearchPipeline") as mock_pipeline:
            mock_pipeline.return_value.search.return_value = [_weight_result()]
            await backend.hybrid_search("test query", rrf_k=3)

        options = mock_pipeline.return_value.search.call_args[0][1]
        assert options.rrf_k == 3  # request wins
        assert options.bm25_weight == 2.0  # untouched knob keeps the settings value
        assert options.vector_weight == 0.5


class TestQueryInputWeightValidation:
    """QueryInput enforces the D-03 ranges at the MCP boundary (ASVS V5)."""

    def test_rrf_k_zero_rejected(self) -> None:
        """rrf_k must be >= 1."""
        with pytest.raises(ValidationError, match="rrf_k"):
            QueryInput(query="q", rrf_k=0)

    def test_negative_bm25_weight_rejected(self) -> None:
        """bm25_weight must be > 0."""
        with pytest.raises(ValidationError, match="bm25_weight"):
            QueryInput(query="q", bm25_weight=-1.0)

    def test_zero_vector_weight_rejected(self) -> None:
        """vector_weight must be > 0."""
        with pytest.raises(ValidationError, match="vector_weight"):
            QueryInput(query="q", vector_weight=0.0)

    def test_large_vector_weight_accepted(self) -> None:
        """No upper bound — the Phase 16 sweep grid must not be capped."""
        data = QueryInput(query="q", vector_weight=1000.0)
        assert data.vector_weight == 1000.0

    def test_defaults_are_none(self) -> None:
        """Unset fields are None (the settings-fallback sentinel), not literals."""
        data = QueryInput(query="q")
        assert data.rrf_k is None
        assert data.bm25_weight is None
        assert data.vector_weight is None


class TestQueryToolHandlerWeightPassThrough:
    """The handler forwards weight params into backend.hybrid_search (D-04)."""

    @pytest.mark.asyncio
    async def test_handle_passes_weight_kwargs(self) -> None:
        """QueryToolHandler.handle forwards rrf_k/bm25_weight/vector_weight."""
        from sif.mcp.handlers import QueryToolHandler

        mock_backend = MagicMock()
        mock_backend.hybrid_search = AsyncMock(return_value=[])

        await QueryToolHandler().handle(
            {"query": "q", "rrf_k": 5, "bm25_weight": 3.0, "vector_weight": 0.5},
            mock_backend,
        )

        call = mock_backend.hybrid_search.call_args
        assert call.kwargs["rrf_k"] == 5
        assert call.kwargs["bm25_weight"] == 3.0
        assert call.kwargs["vector_weight"] == 0.5

    @pytest.mark.asyncio
    async def test_input_schema_declares_weight_properties(self) -> None:
        """The hand-written schema lists the weight params (tool discovery)."""
        from sif.mcp.handlers import QueryToolHandler

        props = QueryToolHandler.input_schema["properties"]
        assert props["rrf_k"]["type"] == "integer"
        assert props["bm25_weight"]["type"] == "number"
        assert props["vector_weight"]["type"] == "number"


class TestQueryInputOffsetValidation:
    """CORR-03/D-05: offset is validated at the MCP boundary (ASVS V5)."""

    def test_negative_offset_rejected(self) -> None:
        """offset must be >= 0."""
        with pytest.raises(ValidationError, match="offset"):
            QueryInput(query="q", offset=-1)

    def test_zero_and_positive_offset_accepted(self) -> None:
        assert QueryInput(query="q").offset == 0
        assert QueryInput(query="q", offset=3).offset == 3

    def test_lex_and_vec_inputs_carry_validated_offset(self) -> None:
        """Phase 22's lex/vec tools inherit a validated offset field."""
        from sif.mcp.protocol import LexSearchInput, VecSearchInput

        assert LexSearchInput(query="q").offset == 0
        assert VecSearchInput(query="q", offset=4).offset == 4
        with pytest.raises(ValidationError, match="offset"):
            LexSearchInput(query="q", offset=-1)
        with pytest.raises(ValidationError, match="offset"):
            VecSearchInput(query="q", offset=-1)


class TestQueryToolHandlerOffsetPassThrough:
    """The handler advertises and forwards offset (CORR-03/D-05)."""

    @pytest.mark.asyncio
    async def test_handle_forwards_offset(self) -> None:
        from sif.mcp.handlers import QueryToolHandler

        mock_backend = MagicMock()
        mock_backend.hybrid_search = AsyncMock(return_value=[])

        await QueryToolHandler().handle({"query": "q", "offset": 7}, mock_backend)

        assert mock_backend.hybrid_search.call_args.kwargs["offset"] == 7

    def test_input_schema_declares_offset(self) -> None:
        from sif.mcp.handlers import QueryToolHandler

        props = QueryToolHandler.input_schema["properties"]
        assert props["offset"] == {"type": "integer", "minimum": 0, "default": 0}


class TestHybridSearchOffsetForwarding:
    """offset rides SearchOptions into the pipeline (and the BM25 fallback)."""

    @pytest.mark.asyncio
    async def test_offset_rides_search_options_into_pipeline(self, backend) -> None:
        with patch("sif.mcp.backend.SearchPipeline") as mock_pipeline:
            mock_pipeline.return_value.search.return_value = [_weight_result()]
            await backend.hybrid_search("test query", offset=3)

        options = mock_pipeline.return_value.search.call_args[0][1]
        assert options.offset == 3

    @pytest.mark.asyncio
    async def test_bm25_fallback_receives_the_same_offset(self, backend) -> None:
        with (
            patch("sif.mcp.backend.SearchPipeline", side_effect=RuntimeError("no vec")),
            patch("sif.mcp.backend.BM25Searcher") as mock_bm25_cls,
        ):
            mock_bm25_cls.return_value.search.return_value = []
            await backend.hybrid_search("test query", offset=3)

        options = mock_bm25_cls.return_value.search.call_args[0][1]
        assert options.offset == 3


# =============================================================================
# Zero-result suggestions (Phase 15, D-05/D-08)
# =============================================================================

_SUGGEST_DOCS = [
    ("d1", "quantum machine learning algorithms"),
    ("d2", "quantum computing quick quantifiers"),
    ("d3", "studies of machine learning contexts"),
]


def _seed_suggestion_db(tmp_path: Path) -> tuple[Path, Settings]:
    """Real DB (production DDL) whose porter vocabulary anchors DYM tests."""
    settings = Settings(
        _env_file=None,
        embedding_dim=8,
        model_name="test",
        cache_embeddings=False,
    )
    db_path = tmp_path / "mcp-suggest.db"
    with patch("sif.config.settings.get_settings", return_value=settings):
        db = Database(db_path)
        db.init_schema()
        now = datetime.now(timezone.utc).isoformat()
        with db.connection:
            conn = db.connection
            conn.execute(
                "INSERT INTO collections (id, name, path, created_at, updated_at)"
                " VALUES ('c1', 'notes', '/vault', ?, ?)",
                (now, now),
            )
            conn.executemany(
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
                        f"ck-{doc_id}",
                        now,
                        now,
                    )
                    for doc_id, body in _SUGGEST_DOCS
                ],
            )
        db.close()
    return db_path, settings


def _suggestion_backend(db_path: Path, settings: Settings) -> SearchBackend:
    """Backend with no embedder load (the pipeline is mocked per test)."""
    with patch("sif.mcp.backend.EmbeddingModelFactory", side_effect=RuntimeError("no embedder")):
        return SearchBackend(str(db_path), settings=settings)


def _query_log_count(db_path: Path) -> int:
    conn = sqlite3.connect(db_path)
    try:
        return int(conn.execute("SELECT COUNT(*) FROM query_log").fetchone()[0])
    finally:
        conn.close()


class TestZeroResultSuggestions:
    """QueryOutput.suggestions is populated explicitly on the zero-result path."""

    @pytest.mark.asyncio
    async def test_zero_result_query_carries_suggestions(self, tmp_path: Path) -> None:
        """A zero-result MCP query returns DYM strings built from the vocab."""
        db_path, settings = _seed_suggestion_db(tmp_path)
        backend = _suggestion_backend(db_path, settings)

        with patch("sif.mcp.backend.SearchPipeline") as mock_pipeline:
            mock_pipeline.return_value.search.return_value = []
            results = await backend.hybrid_search("quantm machin")

        assert isinstance(results, HybridSearchResults)
        assert list(results) == []
        assert results.suggestions == ["quantum machin"]

    @pytest.mark.asyncio
    async def test_result_present_query_has_empty_suggestions(self, tmp_path: Path) -> None:
        """Non-zero-result responses carry an empty suggestion list."""
        db_path, settings = _seed_suggestion_db(tmp_path)
        backend = _suggestion_backend(db_path, settings)

        with patch("sif.mcp.backend.SearchPipeline") as mock_pipeline:
            mock_pipeline.return_value.search.return_value = [_weight_result()]
            results = await backend.hybrid_search("quantum")

        assert results
        assert results.suggestions == []

    @pytest.mark.asyncio
    async def test_engine_failure_degrades_to_empty_suggestions(self, tmp_path: Path) -> None:
        """An exploding engine never fails the MCP query (Pitfall 10 posture)."""
        db_path, settings = _seed_suggestion_db(tmp_path)
        backend = _suggestion_backend(db_path, settings)

        with (
            patch("sif.mcp.backend.SearchPipeline") as mock_pipeline,
            patch("sif.mcp.backend.SuggestionEngine", side_effect=RuntimeError("boom")),
        ):
            mock_pipeline.return_value.search.return_value = []
            results = await backend.hybrid_search("quantm machin")

        assert list(results) == []
        assert results.suggestions == []

    @pytest.mark.asyncio
    async def test_mcp_query_never_writes_query_log(self, tmp_path: Path) -> None:
        """D-08: assistant tool-queries never pollute personal history."""
        db_path, settings = _seed_suggestion_db(tmp_path)
        backend = _suggestion_backend(db_path, settings)

        with patch("sif.mcp.backend.SearchPipeline") as mock_pipeline:
            mock_pipeline.return_value.search.return_value = []
            await backend.hybrid_search("quantm machin")
            mock_pipeline.return_value.search.return_value = [_weight_result()]
            await backend.hybrid_search("quantum")

        assert _query_log_count(db_path) == 0

    @pytest.mark.asyncio
    async def test_handler_carries_suggestions_into_query_output(self) -> None:
        """The handler explicitly remaps the list attribute into QueryOutput."""
        from sif.mcp.handlers import QueryToolHandler

        mock_backend = MagicMock()
        mock_backend.hybrid_search = AsyncMock(
            return_value=HybridSearchResults([], ["quantum machin"]),
        )

        result = await QueryToolHandler().handle({"query": "quantm machin"}, mock_backend)

        payload = json.loads(result.content[0].text)
        assert payload["results"] == []
        assert payload["suggestions"] == ["quantum machin"]


# =============================================================================
# sqlite-vec degradation (Phase 10 WR-08, user decision)
# =============================================================================

_VEC_MISSING_MSG = "sqlite-vec extension is not available. Install sqlite-vec to use vector search."


class TestHybridSearchVecDegradation:
    """Phase 10 WR-08 (user decision): the MCP SearchBackend boundary degrades
    to BM25-only when sqlite-vec is unavailable; the core HybridSearcher.search
    stays fail-fast (the carve-out is construction-only)."""

    @pytest.mark.asyncio
    async def test_vec_unavailable_degrades_to_bm25_results(self, tmp_path: Path) -> None:
        """Construction failure yields real BM25 rows with full boundary metadata."""
        db_path, settings = _seed_suggestion_db(tmp_path)
        backend = _suggestion_backend(db_path, settings)

        with patch(
            "sif.mcp.backend.SearchPipeline",
            side_effect=RuntimeError(_VEC_MISSING_MSG),
        ):
            results = await backend.hybrid_search("quantum")

        assert isinstance(results, HybridSearchResults)
        assert {r.doc_id for r in results} == {"d1", "d2"}
        for r in results:
            assert isinstance(r, SearchResult)
            assert r.metadata["collection_name"] == "notes"
            assert isinstance(r.metadata["rank"], int)
            assert "vectors_stale" in r.metadata

    @pytest.mark.asyncio
    async def test_vec_unavailable_warning_emitted_once(self, tmp_path: Path, caplog) -> None:
        """Repeated degraded queries warn exactly once per backend instance."""
        db_path, settings = _seed_suggestion_db(tmp_path)
        # Built before capture: the __init__ embedder warning is unrelated.
        backend = _suggestion_backend(db_path, settings)

        with (
            patch(
                "sif.mcp.backend.SearchPipeline",
                side_effect=RuntimeError(_VEC_MISSING_MSG),
            ),
            caplog.at_level(logging.WARNING, logger=backend_module.logger.name),
        ):
            first = await backend.hybrid_search("quantum")
            second = await backend.hybrid_search("quantum")

        assert list(first)
        assert list(second)
        vec_warnings = [r for r in caplog.records if "sqlite-vec" in r.message]
        assert len(vec_warnings) == 1
        assert vec_warnings[0].levelno == logging.WARNING

    @pytest.mark.asyncio
    async def test_search_time_runtime_error_still_propagates(self, backend) -> None:
        """Preservation pin: search-time RuntimeErrors are never swallowed."""
        with patch("sif.mcp.backend.SearchPipeline") as mock_pipeline:
            mock_pipeline.return_value.search.side_effect = RuntimeError("vector search failed")
            with pytest.raises(RuntimeError, match="vector search failed"):
                await backend.hybrid_search("quantum")


class TestSingleEnrichmentOwner:
    """CORR-05 (Plan 19-04): the MCP boundary enriches exactly once.

    The BM25 fallback bypasses ``SearchPipeline``, so the boundary owns that
    path's single enrichment. The pipeline path is already enriched by
    ``SearchPipeline`` (Plan 19-03) and must not be enriched again here.
    """

    @pytest.mark.asyncio
    async def test_bm25_fallback_enriches_once_and_forwards_vectors_stale(
        self, tmp_path: Path
    ) -> None:
        """Fallback path: one enrich_results call; enriched fields ride the re-map."""
        db_path, settings = _seed_suggestion_db(tmp_path)
        backend = _suggestion_backend(db_path, settings)

        calls: list[list[SearchResult]] = []

        def _enrich(_conn: object, results: list[SearchResult]) -> list[SearchResult]:
            calls.append(results)
            for result in results:
                result.context_description = "chosen context"
                result.vectors_stale = True
            return results

        with (
            patch(
                "sif.mcp.backend.SearchPipeline",
                side_effect=RuntimeError(_VEC_MISSING_MSG),
            ),
            patch("sif.mcp.backend.enrich_results", side_effect=_enrich),
        ):
            results = await backend.hybrid_search("quantum")

        assert calls, "the BM25 fallback must enrich its core results"
        assert len(calls) == 1
        assert len(results) == 2
        for result in results:
            assert result.metadata["vectors_stale"] is True
            # The boundary forwards exactly its existing fields; context
            # descriptions stay CLI-visible only (not a Phase-19 MCP contract).
            assert set(result.metadata) == {
                "rank",
                "collection_name",
                "vectors_stale",
                "chunk_id",
                "sequence",
                "chunk_matches",
            }

    @pytest.mark.asyncio
    async def test_pipeline_path_does_not_enrich_again(self, backend) -> None:
        """Pipeline path: SearchPipeline owns enrichment; the boundary adds none."""
        with (
            patch("sif.mcp.backend.SearchPipeline") as mock_pipeline,
            patch("sif.mcp.backend.enrich_results") as mock_enrich,
        ):
            mock_pipeline.return_value.search.return_value = [_weight_result()]
            results = await backend.hybrid_search("test query")

        mock_enrich.assert_not_called()
        assert results[0].metadata["vectors_stale"] is False
        assert set(results[0].metadata) == {
            "rank",
            "collection_name",
            "vectors_stale",
            "chunk_id",
            "sequence",
            "chunk_matches",
        }


# =============================================================================
# CORR-02 per-chunk escape hatch and chunk-field forwarding (Plan 19-07)
# =============================================================================


class TestPerChunkInputs:
    """D-01: only the two chunk-capable MCP inputs carry per_chunk."""

    def test_query_input_defaults_false_and_accepts_true(self) -> None:
        assert QueryInput(query="q").per_chunk is False
        assert QueryInput(query="q", per_chunk=True).per_chunk is True

    def test_vec_search_input_carries_per_chunk(self) -> None:
        from sif.mcp.protocol import VecSearchInput

        assert VecSearchInput(query="q").per_chunk is False
        assert VecSearchInput(query="q", per_chunk=True).per_chunk is True

    def test_lex_search_input_has_no_per_chunk_field(self) -> None:
        """sif search / MCP lex_search are document-level (D-01 prohibition)."""
        from sif.mcp.protocol import LexSearchInput

        assert "per_chunk" not in LexSearchInput.model_fields


class TestQueryToolHandlerPerChunk:
    """The hand-written schema stays in sync and the handler forwards the flag."""

    def test_input_schema_declares_per_chunk_matching_the_model_default(self) -> None:
        from sif.mcp.handlers import QueryToolHandler

        props = QueryToolHandler.input_schema["properties"]
        assert props["per_chunk"] == {
            "type": "boolean",
            "default": QueryInput(query="q").per_chunk,
        }

    @pytest.mark.asyncio
    async def test_handle_forwards_per_chunk(self) -> None:
        from sif.mcp.handlers import QueryToolHandler

        mock_backend = MagicMock()
        mock_backend.hybrid_search = AsyncMock(return_value=[])

        await QueryToolHandler().handle({"query": "q", "per_chunk": True}, mock_backend)

        assert mock_backend.hybrid_search.call_args.kwargs["per_chunk"] is True


class TestHybridSearchPerChunkForwarding:
    """per_chunk rides SearchOptions into both the pipeline and the fallback."""

    @pytest.mark.asyncio
    async def test_per_chunk_rides_search_options_into_pipeline(self, backend) -> None:
        with patch("sif.mcp.backend.SearchPipeline") as mock_pipeline:
            mock_pipeline.return_value.search.return_value = [_weight_result()]
            await backend.hybrid_search("test query", per_chunk=True)

        options = mock_pipeline.return_value.search.call_args[0][1]
        assert options.per_chunk is True

    @pytest.mark.asyncio
    async def test_per_chunk_defaults_false_on_the_options_object(self, backend) -> None:
        with patch("sif.mcp.backend.SearchPipeline") as mock_pipeline:
            mock_pipeline.return_value.search.return_value = [_weight_result()]
            await backend.hybrid_search("test query")

        options = mock_pipeline.return_value.search.call_args[0][1]
        assert options.per_chunk is False

    @pytest.mark.asyncio
    async def test_bm25_fallback_receives_per_chunk_too(self, backend) -> None:
        with (
            patch("sif.mcp.backend.SearchPipeline", side_effect=RuntimeError("no vec")),
            patch("sif.mcp.backend.BM25Searcher") as mock_bm25_cls,
        ):
            mock_bm25_cls.return_value.search.return_value = []
            await backend.hybrid_search("test query", per_chunk=True)

        options = mock_bm25_cls.return_value.search.call_args[0][1]
        assert options.per_chunk is True


class TestChunkFieldRemap:
    """D-02/D-03: a default MCP result's chunk fields equal the core values."""

    @pytest.mark.asyncio
    async def test_remap_copies_chunk_identity_and_match_count(self, backend) -> None:
        core = _weight_result()
        core.chunk_id = "chunk-9"
        core.sequence = 4
        core.chunk_matches = 7

        with patch("sif.mcp.backend.SearchPipeline") as mock_pipeline:
            mock_pipeline.return_value.search.return_value = [core]
            results = await backend.hybrid_search("test query")

        assert results[0].metadata["chunk_id"] == core.chunk_id
        assert results[0].metadata["sequence"] == core.sequence
        assert results[0].metadata["chunk_matches"] == core.chunk_matches


def _downgrade_documents_fts_to_legacy(conn: sqlite3.Connection) -> None:
    """Replace the two-column FTS with the pre-CORR-04 single-column shape."""
    for trigger in (
        "documents_fts_insert",
        "documents_fts_update",
        "documents_fts_delete",
    ):
        conn.execute(f"DROP TRIGGER IF EXISTS {trigger}")
    conn.execute("DROP TABLE IF EXISTS documents_fts_v")
    conn.execute("DROP TABLE IF EXISTS documents_fts")
    conn.execute(
        "CREATE VIRTUAL TABLE documents_fts USING fts5("
        "content, content='documents', content_rowid='rowid', tokenize='porter')"
    )
    conn.execute("CREATE VIRTUAL TABLE documents_fts_v USING fts5vocab(documents_fts, 'row')")
    conn.execute("INSERT INTO documents_fts(rowid, content) SELECT rowid, content FROM documents")
    conn.execute("""
        CREATE TRIGGER documents_fts_insert
        AFTER INSERT ON documents
        BEGIN
            INSERT INTO documents_fts(rowid, content) VALUES (new.rowid, new.content);
        END
    """)
    conn.execute("""
        CREATE TRIGGER documents_fts_update
        AFTER UPDATE ON documents
        BEGIN
            INSERT INTO documents_fts(documents_fts, rowid, content)
            VALUES('delete', old.rowid, old.content);
            INSERT INTO documents_fts(rowid, content) VALUES(new.rowid, new.content);
        END
    """)
    conn.execute("""
        CREATE TRIGGER documents_fts_delete
        AFTER DELETE ON documents
        BEGIN
            INSERT INTO documents_fts(documents_fts, rowid, content)
            VALUES('delete', old.rowid, old.content);
        END
    """)
    conn.commit()


def _seed_pre_title_db(tmp_path: Path, embedding_dim: int = 8) -> tuple[Path, Settings]:
    """A populated pre-CORR-04 index that only an init_schema call migrates."""
    settings = Settings(
        _env_file=None,
        embedding_dim=embedding_dim,
        model_name="test",
        cache_embeddings=False,
    )
    db_path = tmp_path / "pre-title.db"
    db = Database(db_path)
    try:
        db.init_schema(embedding_dim=embedding_dim)
        now = datetime.now(timezone.utc).isoformat()
        with db.connection:
            db.connection.execute(
                "INSERT INTO collections (id, name, path, created_at, updated_at)"
                " VALUES ('c1', 'notes', '/vault', ?, ?)",
                (now, now),
            )
            db.connection.execute(
                "INSERT INTO documents (id, collection_id, path, filename, title, content,"
                " checksum, mtime, created_at, updated_at)"
                " VALUES ('d1', 'c1', '/vault/a.md', 'a.md', 'Titular Alpha',"
                " 'body words only', 'ck-1', 1.0, ?, ?)",
                (now, now),
            )
        _downgrade_documents_fts_to_legacy(db.connection)
    finally:
        db.close()
    return db_path, settings


def _schema_ddl(db_path: Path) -> dict[str, str]:
    """Stored DDL for every table, trigger, and index in the database."""
    conn = sqlite3.connect(db_path)
    try:
        return {
            row[0]: row[1]
            for row in conn.execute(
                "SELECT name, sql FROM sqlite_master"
                " WHERE type IN ('table', 'trigger', 'index')"
                " AND name NOT LIKE 'sqlite_%'"
            )
        }
    finally:
        conn.close()


class TestSchemaInitializationAtStartup:
    """CORR-04/T-19-21: an MCP-only process migrates the schema on startup.

    ``SearchBackend`` is the only DB entry point an MCP-only deployment has;
    without this one-time ``init_schema`` call a pre-title database keeps its
    single-column FTS forever (RESEARCH Pitfall 13).
    """

    def test_constructor_migrates_a_pre_title_database(self, tmp_path: Path) -> None:
        """Construction applies the title column, triggers, and mtime index."""
        db_path, settings = _seed_pre_title_db(tmp_path)
        with patch(
            "sif.mcp.backend.EmbeddingModelFactory", side_effect=RuntimeError("no embedder")
        ):
            SearchBackend(str(db_path), settings=settings)

        conn = sqlite3.connect(db_path)
        try:
            fts_sql = conn.execute(
                "SELECT sql FROM sqlite_master WHERE type='table' AND name='documents_fts'"
            ).fetchone()[0]
            assert "title" in fts_sql
            # The title-only token was unmatchable before the migration.
            assert (
                conn.execute(
                    "SELECT COUNT(*) FROM documents_fts WHERE documents_fts MATCH '\"titular\"'"
                ).fetchone()[0]
                == 1
            )
            trigger_sql = conn.execute(
                "SELECT sql FROM sqlite_master WHERE type='trigger' AND name='documents_fts_insert'"
            ).fetchone()[0]
            assert "title" in trigger_sql
            index_names = {
                row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='index'")
            }
            assert "idx_documents_mtime" in index_names
        finally:
            conn.close()

    def test_second_construction_is_idempotent_and_leaves_ddl_unchanged(
        self, tmp_path: Path
    ) -> None:
        """A second backend over the migrated DB pays detection reads only."""
        db_path, settings = _seed_pre_title_db(tmp_path)
        with patch(
            "sif.mcp.backend.EmbeddingModelFactory", side_effect=RuntimeError("no embedder")
        ):
            SearchBackend(str(db_path), settings=settings)
            first = _schema_ddl(db_path)
            SearchBackend(str(db_path), settings=settings)
            second = _schema_ddl(db_path)

        assert first == second

    def test_constructor_uses_backend_settings_dimension(self, tmp_path: Path) -> None:
        """The backend's own dimension wins over the process environment.

        The seeded index is FLOAT[8]; a process default of FLOAT[1024] would
        raise the dimension-mismatch RuntimeError, so success proves the
        injected settings dimension was used.
        """
        db_path, settings = _seed_pre_title_db(tmp_path)
        process_settings = settings.model_copy(update={"embedding_dim": 1024})
        with (
            patch("sif.config.settings.get_settings", return_value=process_settings),
            patch("sif.mcp.backend.EmbeddingModelFactory", side_effect=RuntimeError("no embedder")),
        ):
            SearchBackend(str(db_path), settings=settings)

        conn = sqlite3.connect(db_path)
        try:
            sql = conn.execute(
                "SELECT sql FROM sqlite_master WHERE type='table' AND name='document_embeddings'"
            ).fetchone()[0]
            assert "FLOAT[8]" in sql
        finally:
            conn.close()

    def test_dimension_mismatch_raises_the_existing_runtime_error(self, tmp_path: Path) -> None:
        """A wrong width fails loudly instead of silently rebuilding the index."""
        db_path, _settings = _seed_pre_title_db(tmp_path)
        wrong = Settings(
            _env_file=None,
            embedding_dim=384,
            model_name="test",
            cache_embeddings=False,
        )
        with patch(
            "sif.mcp.backend.EmbeddingModelFactory", side_effect=RuntimeError("no embedder")
        ):
            with pytest.raises(RuntimeError, match="Embedding dimension mismatch"):
                SearchBackend(str(db_path), settings=wrong)

    def test_dimension_mismatch_leaves_the_migrated_index_populated(self, tmp_path: Path) -> None:
        """CR-01: the rebuild is durable even when init fails after it.

        The RuntimeError comes from ``_create_vector_tables``, which runs
        after the FTS migration inside ``create_all``. The pre-fix sequence
        committed the two-column DDL but rolled the population back on
        close, leaving a permanently empty index; after the fix the rebuilt
        index survives and a later correct-width open still matches.
        """
        db_path, settings = _seed_pre_title_db(tmp_path)
        wrong = Settings(
            _env_file=None,
            embedding_dim=384,
            model_name="test",
            cache_embeddings=False,
        )
        with patch(
            "sif.mcp.backend.EmbeddingModelFactory", side_effect=RuntimeError("no embedder")
        ):
            with pytest.raises(RuntimeError, match="Embedding dimension mismatch"):
                SearchBackend(str(db_path), settings=wrong)

        conn = sqlite3.connect(db_path)
        try:
            assert (
                conn.execute(
                    "SELECT COUNT(*) FROM documents_fts WHERE documents_fts MATCH '\"titular\"'"
                ).fetchone()[0]
                == 1
            )
            assert (
                conn.execute("SELECT COUNT(*) FROM documents_fts").fetchone()[0]
                == (conn.execute("SELECT COUNT(*) FROM documents").fetchone()[0])
            )
            trigger_sql = conn.execute(
                "SELECT sql FROM sqlite_master WHERE type='trigger' AND name='documents_fts_insert'"
            ).fetchone()[0]
            assert "title" in trigger_sql
        finally:
            conn.close()

        # A later open at the correct width keeps the pre-existing document
        # MATCHable through the title column.
        with patch(
            "sif.mcp.backend.EmbeddingModelFactory", side_effect=RuntimeError("no embedder")
        ):
            SearchBackend(str(db_path), settings=settings)

        conn = sqlite3.connect(db_path)
        try:
            assert (
                conn.execute(
                    "SELECT COUNT(*) FROM documents_fts WHERE documents_fts MATCH '\"titular\"'"
                ).fetchone()[0]
                == 1
            )
            assert (
                conn.execute("SELECT COUNT(*) FROM documents_fts").fetchone()[0]
                == (conn.execute("SELECT COUNT(*) FROM documents").fetchone()[0])
            )
        finally:
            conn.close()


# =============================================================================
# Phase 20 metadata filter surface (D-02/D-17)
# =============================================================================

_FILTER_PAYLOAD = {"field": "status", "operator": "eq", "value": "active"}
_BAD_FILTER_PAYLOAD = {"field": "tags", "operator": "gt", "value": "x"}


class TestFilterInputs:
    """D-02: all three MCP search inputs carry ``filter``, defaulting to None."""

    def test_query_input_accepts_and_retains_filter(self) -> None:
        assert QueryInput(query="q").filter is None
        assert QueryInput(query="q", filter=_FILTER_PAYLOAD).filter == _FILTER_PAYLOAD

    def test_lex_search_input_accepts_and_retains_filter(self) -> None:
        from sif.mcp.protocol import LexSearchInput

        assert LexSearchInput(query="q").filter is None
        assert LexSearchInput(query="q", filter=_FILTER_PAYLOAD).filter == _FILTER_PAYLOAD

    def test_vec_search_input_accepts_and_retains_filter(self) -> None:
        from sif.mcp.protocol import VecSearchInput

        assert VecSearchInput(query="q").filter is None
        assert VecSearchInput(query="q", filter=_FILTER_PAYLOAD).filter == _FILTER_PAYLOAD


class TestQueryToolHandlerFilter:
    """The hand-written schema stays in sync and validation is a tool error."""

    def test_input_schema_declares_filter(self) -> None:
        from sif.mcp.handlers import QueryToolHandler

        props = QueryToolHandler.input_schema["properties"]
        assert props["filter"] == {"type": "object"}
        assert "filter" in QueryInput.model_fields

    @pytest.mark.asyncio
    async def test_handle_forwards_the_parsed_ast(self) -> None:
        from sif.core.filters import parse_filter
        from sif.mcp.handlers import QueryToolHandler

        mock_backend = MagicMock()
        mock_backend.hybrid_search = AsyncMock(return_value=[])

        result = await QueryToolHandler().handle(
            {"query": "q", "filter": _FILTER_PAYLOAD}, mock_backend
        )

        assert result.isError is False
        kwargs = mock_backend.hybrid_search.call_args.kwargs
        assert kwargs["filter_node"] == parse_filter(_FILTER_PAYLOAD)
        assert kwargs["filter_node"] is not None

    @pytest.mark.asyncio
    async def test_handle_forwards_none_when_filter_absent(self) -> None:
        from sif.mcp.handlers import QueryToolHandler

        mock_backend = MagicMock()
        mock_backend.hybrid_search = AsyncMock(return_value=[])

        await QueryToolHandler().handle({"query": "q"}, mock_backend)

        assert mock_backend.hybrid_search.call_args.kwargs["filter_node"] is None

    @pytest.mark.asyncio
    async def test_invalid_filter_returns_iserror_without_raising(self) -> None:
        """D-17: an invalid AST is a controlled tool execution error."""
        from sif.mcp.handlers import QueryToolHandler

        mock_backend = MagicMock()
        mock_backend.hybrid_search = AsyncMock(return_value=[])

        result = await QueryToolHandler().handle(
            {"query": "q", "filter": _BAD_FILTER_PAYLOAD}, mock_backend
        )

        assert result.isError is True
        text = result.content[0].text or ""
        assert text.startswith("filter.")
        assert '"gt" requires a numeric value' in text
        assert "tags" in text
        mock_backend.hybrid_search.assert_not_called()


class TestInvalidFilterIsNotAProtocolError:
    """T-20-13/T-20-14: validation stays inside a successful JSON-RPC envelope."""

    @pytest.mark.asyncio
    async def test_invalid_filter_yields_success_envelope_with_iserror(self) -> None:
        from sif.mcp.handlers import QueryToolHandler
        from sif.mcp.protocol import JsonRpcRequest
        from sif.mcp.server import MCPServer, ServerState

        backend = MagicMock()
        backend.hybrid_search = AsyncMock(return_value=[])
        server = MCPServer(backend)
        server.state = ServerState.INITIALIZED
        server.register_tools([QueryToolHandler()])

        response = await server.handle_request(
            JsonRpcRequest(
                id=1,
                method="tools/call",
                params={
                    "name": "query",
                    "arguments": {"query": "q", "filter": _BAD_FILTER_PAYLOAD},
                },
            )
        )

        assert response.error is None
        assert response.result["isError"] is True
        assert response.result["content"][0]["text"].startswith("filter.")
        assert "error" not in response.model_dump(exclude_none=True)
        assert backend.hybrid_search.call_count == 0


class TestFilterThroughBackend:
    """T-20-16: the parsed AST rides SearchOptions to every leg, or stays None."""

    @pytest.mark.asyncio
    async def test_filter_reaches_search_options_unchanged(self, backend) -> None:
        from sif.core.filters import parse_filter

        node = parse_filter(_FILTER_PAYLOAD)
        with patch("sif.mcp.backend.SearchPipeline") as mock_pipeline:
            mock_pipeline.return_value.search.return_value = [_weight_result()]
            await backend.hybrid_search("test query", filter_node=node)

        options = mock_pipeline.return_value.search.call_args[0][1]
        assert options.filter is node

    @pytest.mark.asyncio
    async def test_bm25_fallback_receives_the_same_filter(self, backend) -> None:
        from sif.core.filters import parse_filter

        node = parse_filter(_FILTER_PAYLOAD)
        with (
            patch("sif.mcp.backend.SearchPipeline", side_effect=RuntimeError("no vec")),
            patch("sif.mcp.backend.BM25Searcher") as mock_bm25_cls,
        ):
            mock_bm25_cls.return_value.search.return_value = []
            await backend.hybrid_search("test query", filter_node=node)

        options = mock_bm25_cls.return_value.search.call_args[0][1]
        assert options.filter is node

    @pytest.mark.asyncio
    async def test_unfiltered_search_keeps_filter_none(self, backend) -> None:
        with patch("sif.mcp.backend.SearchPipeline") as mock_pipeline:
            mock_pipeline.return_value.search.return_value = [_weight_result()]
            await backend.hybrid_search("test query")

        options = mock_pipeline.return_value.search.call_args[0][1]
        assert options.filter is None
