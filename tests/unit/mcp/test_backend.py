"""Tests for SearchBackend."""

from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pydantic import ValidationError

from sif.mcp.backend import SearchBackend, _truncate_content
from sif.mcp.protocol import CollectionInfo, Document, QueryInput, SearchResult
from sif.models.embedding import ModelType
from sif.utils.paths import normalize_path


@pytest.fixture
def backend():
    """Create a SearchBackend with mocked settings."""
    with patch("sif.mcp.backend.get_settings") as mock_settings:
        mock_settings.return_value = MagicMock(embedding_dim=1024)
        return SearchBackend("/tmp/test.db")


@pytest.mark.asyncio
async def test_search_backend_init(backend):
    """Verify SearchBackend stores db_path and settings."""
    assert backend.db_path == "/tmp/test.db"
    assert backend.settings is not None


@pytest.mark.asyncio
async def test_search_backend_forwards_api_settings_to_factory():
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
        backend = SearchBackend("/tmp/test.db")

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
    return mock_result


def _settings_backend() -> SearchBackend:
    """Backend whose server settings pin rrf_k=7 / 2.0 / 0.5 (D-04 fallback)."""
    settings = MagicMock(
        embedding_dim=1024,
        rrf_k=7,
        bm25_weight=2.0,
        vector_weight=0.5,
    )
    with patch("sif.mcp.backend.get_settings", return_value=settings):
        return SearchBackend("/tmp/test.db")


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
    async def test_absent_fields_fall_back_to_server_settings(self) -> None:
        """No weight params -> the server process's SIF_ settings fill options."""
        backend = _settings_backend()

        with patch("sif.mcp.backend.SearchPipeline") as mock_pipeline:
            mock_pipeline.return_value.search.return_value = [_weight_result()]
            await backend.hybrid_search("test query")

        options = mock_pipeline.return_value.search.call_args[0][1]
        assert options.rrf_k == 7
        assert options.bm25_weight == 2.0
        assert options.vector_weight == 0.5

    @pytest.mark.asyncio
    async def test_request_field_overrides_settings(self) -> None:
        """A request field beats the server setting; unset knobs still fall back."""
        backend = _settings_backend()

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
