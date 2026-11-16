"""Tests for SearchBackend."""

from __future__ import annotations

import json
import logging
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import ANY, AsyncMock, MagicMock, patch

import pytest
from pydantic import ValidationError

from sif.config.settings import Settings
from sif.database.database import Database
from sif.mcp import backend as backend_module
from sif.mcp.backend import HybridSearchResults, SearchBackend, _truncate_content
from sif.mcp.protocol import CollectionInfo, Document, QueryInput, SearchResult
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
async def test_search_backend_construction_is_model_free(tmp_path: Path):
    """D-15: construction opens the schema but never builds or loads a model.

    The eager ``EmbeddingModelFactory`` call was removed in Phase 22; the lazy
    manager attaches through ``_embedder``/``_identity`` on the first vector
    need (22-02/22-04), so both stay ``None`` after construction and the
    load-attempt latch is untouched.
    """
    settings = MagicMock(
        model_type="openai",
        model_name="text-embedding-3-small",
        model_path=None,
        api_key="sk-test",
        api_base="https://api.example.com/v1",
        embedding_dim=8,
        cache_embeddings=False,
    )

    with patch("sif.mcp.backend.get_settings", return_value=settings):
        backend = SearchBackend(str(tmp_path / "test.db"))

    assert backend._embedder is None
    assert backend._identity is None
    assert backend._load_attempted is False
    assert backend._load_failed is False


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
    """Construction is model-free (D-15); the pipeline is mocked per test."""
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
        # Construction is model-free (D-15): no embedder warning exists.
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
        with patch("sif.config.settings.get_settings", return_value=process_settings):
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
# Embedder identity at startup (Phase 21, D-04/D-05/D-07)
# =============================================================================


class TestEmbedderIdentityAtStartup:
    """The MCP host records the scheme it applies and adopts legacy indexes.

    T-21-28: the identity's prompt fields must describe the vectors this host
    actually produces, so one resolved scheme feeds the settings-only identity
    at schema open and the lazy manager's loaded-model identity in 22-02/22-04.
    Construction itself stays model-free (D-15).
    """

    @staticmethod
    def _settings(**overrides: object) -> Settings:
        values: dict[str, object] = {
            "embedding_dim": 8,
            "model_name": "test",
            "cache_embeddings": False,
        }
        values.update(overrides)
        return Settings(_env_file=None, **values)

    def test_init_schema_receives_the_settings_only_identity(self, tmp_path: Path) -> None:
        settings = self._settings(query_prompt_name="qry", document_prompt_name="doc")

        with patch.object(Database, "init_schema") as init_schema:
            SearchBackend(str(tmp_path / "identity.db"), settings=settings)

        init_schema.assert_called_once()
        kwargs = init_schema.call_args.kwargs
        assert kwargs["embedding_dim"] == 8
        identity = kwargs["identity"]
        assert identity.dimension == 8
        assert identity.model_name == "test"
        assert identity.query_prompt == "qry"
        assert identity.document_prompt == "doc"
        # Settings-only: no model provenance is known yet.
        assert identity.pooling == "unknown"
        assert identity.revision is None

    def test_construction_leaves_the_loaded_identity_unset(self, tmp_path: Path) -> None:
        """The full identity arrives only after a successful lazy load (D-15)."""
        settings = self._settings(query_prompt_name="qry", document_prompt_name="doc")

        backend = SearchBackend(str(tmp_path / "prompts.db"), settings=settings)

        assert backend._embedder is None
        assert backend._identity is None

    def test_legacy_db_first_opened_by_the_backend_gets_the_assumed_row(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        db_path, settings = _seed_pre_title_db(tmp_path)

        seed = Database(db_path)
        try:
            has_vectors = seed.connection.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' AND name='document_embeddings'"
            ).fetchone()
            if has_vectors is None:
                pytest.skip("sqlite-vec not available")
            seed.connection.execute(
                "INSERT INTO document_embeddings (embedding_id, document_id, chunk_id, embedding) "
                "VALUES ('e1', 'd1', 'c1', vec_f32(?))",
                (json.dumps([0.1] * 8),),
            )
            seed.connection.commit()
        finally:
            seed.close()

        with caplog.at_level(logging.WARNING):
            SearchBackend(str(db_path), settings=settings)

        conn = sqlite3.connect(db_path)
        try:
            raw = conn.execute(
                "SELECT value FROM index_meta WHERE key = 'embedder.identity'"
            ).fetchone()
        finally:
            conn.close()

        assert raw is not None
        payload = json.loads(raw[0])
        assert payload["source"] == "legacy-assumed"
        assert payload["model_name"] == "test"
        assert payload["dimension"] == 8
        warnings = [r for r in caplog.records if "Index predates embedder identity" in r.message]
        assert len(warnings) == 1


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


def _seed_metadata_rows(db_path: Path) -> None:
    """Seed a collection and three typed-row documents on the backend's schema."""
    from sif.core.models import Collection, Document as CoreDocument
    from sif.database.connection import DatabaseConnection
    from sif.database.repositories import CollectionRepository, DocumentRepository

    with DatabaseConnection(db_path).transaction() as conn:
        CollectionRepository(conn).create(Collection(id="c1", name="notes", path="/notes"))
        repo = DocumentRepository(conn)
        repo.create(
            CoreDocument(
                id="d0",
                collection_id="c1",
                path="/notes/a.md",
                content="body",
                mtime=100.0,
                metadata={"tag": "rare", "priority": 1},
            )
        )
        repo.create(
            CoreDocument(
                id="d1",
                collection_id="c1",
                path="/notes/b.md",
                content="body",
                mtime=200.0,
                metadata={"tag": "common", "priority": 2},
            )
        )
        repo.create(
            CoreDocument(
                id="d2",
                collection_id="c1",
                path="/notes/c.md",
                content="body",
                mtime=300.0,
                metadata={"tag": "common"},
            )
        )


class TestMetadataInputValidation:
    """D-15: the discovery input model enforces its documented ranges."""

    def test_defaults_match_the_documented_contract(self) -> None:
        """Every optional input defaults exactly as the tool schema advertises."""
        from sif.mcp.protocol import MetadataInput

        data = MetadataInput()
        assert data.collections is None
        assert data.filter is None
        assert data.match is None
        assert data.min_count == 1
        assert data.sort == "count"
        assert data.limit == 50
        assert data.value_limit == 10

    @pytest.mark.parametrize(
        ("payload", "field"),
        [
            ({"limit": 0}, "limit"),
            ({"min_count": 0}, "min_count"),
            ({"value_limit": -1}, "value_limit"),
            ({"sort": "name"}, "sort"),
        ],
    )
    def test_rejects_out_of_range_inputs(self, payload: dict, field: str) -> None:
        """Model-layer validation rejects the invalid window and sort values."""
        from sif.mcp.protocol import MetadataInput

        with pytest.raises(ValidationError, match=field):
            MetadataInput(**payload)


class TestMetadataToolHandlerSchema:
    """The hand-written input schema stays in sync with MetadataInput (Pitfall 12)."""

    def test_schema_declares_all_seven_properties_in_sync(self) -> None:
        """Every model field is advertised, with matching defaults."""
        from sif.mcp.handlers import MetadataToolHandler
        from sif.mcp.protocol import MetadataInput

        props = MetadataToolHandler.input_schema["properties"]
        assert set(props) == set(MetadataInput.model_fields)
        model = MetadataInput()
        assert props["min_count"]["default"] == model.min_count
        assert props["sort"]["default"] == model.sort
        assert props["sort"]["enum"] == ["count", "value"]
        assert props["limit"]["default"] == model.limit
        assert props["value_limit"]["default"] == model.value_limit

    def test_create_default_tools_registers_metadata(self) -> None:
        """create_default_tools advertises the metadata tool alongside the four."""
        from sif.mcp.handlers import create_default_tools

        names = {handler.name for handler in create_default_tools()}
        assert names == {"query", "get", "multi_get", "status", "metadata"}


class TestMetadataToolHandler:
    """The metadata handler returns the frozen D-15/D-20 envelope (Phase 22 contract)."""

    @pytest.mark.asyncio
    async def test_valid_call_returns_envelope_with_exact_remainders(self, backend) -> None:
        """Windows, remainders, and the built-in section travel in one JSON text item."""
        from sif.mcp.handlers import MetadataToolHandler

        _seed_metadata_rows(Path(backend.db_path))
        result = await MetadataToolHandler().handle({"limit": 1, "value_limit": 1}, backend)

        assert result.isError is False
        payload = json.loads(result.content[0].text)
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
        from sif.mcp.handlers import MetadataToolHandler

        _seed_metadata_rows(Path(backend.db_path))
        result = await MetadataToolHandler().handle(
            {"filter": {"field": "tag", "operator": "eq", "value": "common"}}, backend
        )

        payload = json.loads(result.content[0].text)
        assert payload["documents"] == 3
        assert payload["filteredDocuments"] == 2
        assert [entry["documents"] for entry in payload["builtIns"]] == [2, 2]

    @pytest.mark.asyncio
    async def test_match_only_call_omits_filtered_documents(self, backend) -> None:
        """A match-only call must pass ``None`` (never the empty fragment) as the filter."""
        from sif.mcp.handlers import MetadataToolHandler

        _seed_metadata_rows(Path(backend.db_path))
        result = await MetadataToolHandler().handle(
            {"match": {"field": "key", "operator": "prefix", "value": "ta"}}, backend
        )

        payload = json.loads(result.content[0].text)
        assert "filteredDocuments" not in payload
        assert [entry["key"] for entry in payload["keys"]] == ["tag"]
        assert payload["documents"] == 3

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
    async def test_invalid_filter_or_match_is_a_tool_error(self, backend, payload) -> None:
        """Grammar violations are controlled isError results, not exceptions."""
        from sif.mcp.handlers import MetadataToolHandler

        result = await MetadataToolHandler().handle(payload, backend)
        assert result.isError is True
        assert result.content[0].text
        assert result.content[0].text.startswith("filter")

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
        self, backend, payload: dict, operator: str, field: str
    ) -> None:
        """WR-02: the same rejected forms are controlled isError results over MCP."""
        from sif.mcp.handlers import MetadataToolHandler

        result = await MetadataToolHandler().handle({"filter": payload}, backend)

        assert result.isError is True
        assert result.content[0].text.startswith(f"filter.{operator}:")
        assert field in result.content[0].text

    @pytest.mark.asyncio
    async def test_invalid_match_is_not_a_protocol_error(self) -> None:
        """D-17: the JSON-RPC envelope is a success with ``result.isError`` true."""
        from sif.mcp.handlers import MetadataToolHandler
        from sif.mcp.protocol import JsonRpcRequest
        from sif.mcp.server import MCPServer, ServerState

        backend = MagicMock()
        backend.metadata = AsyncMock()
        server = MCPServer(backend)
        server.state = ServerState.INITIALIZED
        server.register_tools([MetadataToolHandler()])

        response = await server.handle_request(
            JsonRpcRequest(
                id=1,
                method="tools/call",
                params={
                    "name": "metadata",
                    "arguments": {"match": {"field": "nope", "operator": "eq", "value": "x"}},
                },
            )
        )

        assert response.error is None
        assert response.result["isError"] is True
        assert backend.metadata.call_count == 0


class TestSearchBackendMetadata:
    """SearchBackend.metadata compiles only supplied predicates and scopes by name."""

    @pytest.mark.asyncio
    async def test_absent_filter_and_match_compile_to_none(self, backend) -> None:
        """no filter => no ``filteredDocuments``; no match => every key reported."""
        _seed_metadata_rows(Path(backend.db_path))
        discovery = await backend.metadata(
            collections=None,
            filter_node=None,
            match=None,
            min_count=1,
            sort="count",
            limit=50,
            value_limit=10,
        )
        assert "filteredDocuments" not in discovery
        assert {entry["key"] for entry in discovery["keys"]} == {"tag", "priority"}

    @pytest.mark.asyncio
    async def test_collection_scope_narrows_the_denominator(self, backend) -> None:
        """A named collection scopes every count without adding a filter."""
        _seed_metadata_rows(Path(backend.db_path))
        discovery = await backend.metadata(
            collections=["notes"],
            filter_node=None,
            match=None,
            min_count=1,
            sort="count",
            limit=50,
            value_limit=10,
        )
        assert discovery["documents"] == 3
        assert "filteredDocuments" not in discovery

    @pytest.mark.asyncio
    async def test_unknown_collection_raises_for_the_server_iserror_path(self, backend) -> None:
        """An unknown name raises so the server converts it to a tool execution error."""
        _seed_metadata_rows(Path(backend.db_path))
        with pytest.raises(ValueError, match="not found"):
            await backend.metadata(
                collections=["missing"],
                filter_node=None,
                match=None,
                min_count=1,
                sort="count",
                limit=50,
                value_limit=10,
            )


def _identity(model_name: str, *, dimension: int = 8):
    """Deterministic embedder identity for the MCP identity-policy tests."""
    from sif.embedding.identity import EmbedderIdentity

    return EmbedderIdentity(
        schema_version=1,
        cache_model_id=f"sentence_transformers:{model_name}",
        model_name=model_name,
        model_type="sentence_transformers",
        api_base=None,
        dimension=dimension,
        pooling="mean",
        normalized=True,
        query_prompt=None,
        document_prompt=None,
        prompt_supported=False,
        revision=None,
        source="verified",
    )


def _store_identity(db_path: Path, identity) -> None:
    """Write one identity row into a seeded database."""
    from sif.embedding.identity import write_identity

    conn = sqlite3.connect(db_path)
    try:
        with conn:
            write_identity(conn, identity)
    finally:
        conn.close()


def _add_embeddings(db_path: Path, document_ids: list[str], *, dimension: int = 8) -> None:
    """Seed one chunk + vector row per document so search-mode checks see vectors."""
    import sqlite_vec

    from sif.search.vector import VectorSearcher

    now = datetime.now(timezone.utc).isoformat()
    bodies = dict(_SUGGEST_DOCS)
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


class _FixedEmbedder:
    """Protocol-only embedder with an explicit dimension and fixed vectors."""

    def __init__(self, dimension: int = 8) -> None:
        self._dimension = dimension

    def embed(self, _text: str) -> list[float]:
        return [0.1] * self._dimension

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        return [self.embed(text) for text in texts]

    @property
    def dimension(self) -> int:
        return self._dimension


class TestHybridSearchIdentity:
    """EMB-01: MCP warns/marks a swap and degrades a width mismatch to BM25."""

    @pytest.mark.asyncio
    async def test_no_identity_passes_no_closure(self, tmp_path: Path) -> None:
        """A failed embedder load invents no identity and keeps BM25 degradation."""
        db_path, settings = _seed_suggestion_db(tmp_path)
        backend = _suggestion_backend(db_path, settings)
        assert backend._identity is None

        with patch("sif.mcp.backend.SearchPipeline") as mock_pipeline:
            mock_pipeline.return_value.search.return_value = []
            await backend.hybrid_search("quantum")

        assert mock_pipeline.call_args.kwargs["identity_check"] is None

    @pytest.mark.asyncio
    async def test_same_dimension_mismatch_marks_results_and_warns_once(
        self,
        tmp_path: Path,
        caplog,
    ) -> None:
        """One warning for the pair; every mapped result carries vectors_stale."""
        db_path, settings = _seed_suggestion_db(tmp_path)
        _add_embeddings(db_path, ["d1", "d2", "d3"])
        _store_identity(db_path, _identity("stored"))
        backend = _suggestion_backend(db_path, settings)
        backend._embedder = _FixedEmbedder(8)
        backend._identity = _identity("loaded")

        with caplog.at_level(logging.WARNING, logger="sif.embedding.identity"):
            first = await backend.hybrid_search("quantum")
            second = await backend.hybrid_search("quantum")

        assert first
        assert second
        for result in [*first, *second]:
            assert isinstance(result, SearchResult)
            assert result.metadata["vectors_stale"] is True
        warnings = [
            record
            for record in caplog.records
            if "identity mismatch" in record.getMessage().lower()
        ]
        assert len(warnings) == 1

    @pytest.mark.asyncio
    async def test_dimension_mismatch_returns_marked_bm25_without_a_protocol_error(
        self,
        tmp_path: Path,
        caplog,
    ) -> None:
        """A width mismatch can never vector-search: BM25 rows, marked, one warning."""
        db_path, settings = _seed_suggestion_db(tmp_path)
        _add_embeddings(db_path, ["d1", "d2", "d3"])
        _store_identity(db_path, _identity("stored", dimension=8))
        backend = _suggestion_backend(db_path, settings)
        backend._embedder = _FixedEmbedder(4)
        backend._identity = _identity("loaded", dimension=4)

        with caplog.at_level(logging.WARNING, logger="sif.embedding.identity"):
            results = await backend.hybrid_search("quantum")

        assert results
        assert {result.doc_id for result in results} <= {"d1", "d2", "d3"}
        for result in results:
            assert result.metadata["vectors_stale"] is True
        warnings = [
            record
            for record in caplog.records
            if "identity mismatch" in record.getMessage().lower()
        ]
        assert len(warnings) == 1


# =============================================================================
# Direct lex/vec paths and the lazy embedder (Phase 22 D-15/D-17)
# =============================================================================


class _FakeManager:
    """Minimal manager double: records embed calls and returns fixed vectors."""

    def __init__(self, dimension: int = 8, calls: list[str] | None = None) -> None:
        self._dimension = dimension
        self.calls = calls if calls is not None else []

    @property
    def model(self) -> _FixedEmbedder:
        return _FixedEmbedder(self._dimension)

    def embed_query(self, _text: str) -> list[float]:
        self.calls.append("embed")
        return [0.1] * self._dimension


class TestEnsureEmbedder:
    """D-15: one thread-safe lazy load that forwards the backend settings."""

    @staticmethod
    def _settings(**overrides: object) -> Settings:
        values: dict[str, object] = {
            "embedding_dim": 8,
            "model_name": "test",
            "cache_embeddings": False,
        }
        values.update(overrides)
        return Settings(_env_file=None, **values)

    def test_from_settings_receives_the_backend_settings_and_identity_is_stored(
        self, tmp_path: Path
    ) -> None:
        """API key/base/dimension/cache settings flow through the manager."""
        from sif.embedding.manager import EmbeddingManager

        settings = self._settings(
            query_prompt_name="qry",
            document_prompt_name="doc",
            api_key="sk-test",
            api_base="https://api.example.com/v1",
        )
        backend = SearchBackend(str(tmp_path / "lazy.db"), settings=settings)
        fake_embedder = MagicMock()
        fake_embedder.dimension = 8
        real_manager = EmbeddingManager.from_settings(settings)
        assert real_manager._cache is None  # cache_embeddings=False -> no cache dir

        with (
            patch(
                "sif.mcp.backend.EmbeddingManager.from_settings",
                return_value=real_manager,
            ) as from_settings,
            patch.object(real_manager._factory, "create_model", return_value=fake_embedder),
        ):
            manager = backend._ensure_embedder()

        assert manager is real_manager
        assert backend._manager is real_manager
        assert backend._embedder is fake_embedder
        received = from_settings.call_args.args[0]
        assert received is settings
        assert received.api_key == "sk-test"
        assert received.api_base == "https://api.example.com/v1"
        assert received.embedding_dim == 8
        assert received.cache_embeddings is False
        identity = backend._identity
        assert identity is not None
        assert identity.query_prompt == "qry"
        assert identity.document_prompt == "doc"
        assert identity.dimension == 8
        assert identity.cache_model_id == "modelscope:test@https://api.example.com/v1"
        assert backend._load_attempted is True
        assert backend._load_failed is False

    def test_load_is_attempted_once_and_reused(self, tmp_path: Path) -> None:
        settings = self._settings()
        backend = SearchBackend(str(tmp_path / "once.db"), settings=settings)
        manager = _FakeManager()
        with patch(
            "sif.mcp.backend.EmbeddingManager.from_settings", return_value=manager
        ) as from_settings:
            manager.get_identity = MagicMock(return_value=_identity("loaded"))  # type: ignore[method-assign]
            manager.load_model = MagicMock()  # type: ignore[method-assign]
            first = backend._ensure_embedder()
            second = backend._ensure_embedder()

        assert first is manager
        assert second is manager
        assert from_settings.call_count == 1
        assert manager.load_model.call_count == 1
        assert backend._identity == _identity("loaded")

    def test_failed_load_latches_the_no_identity_state(self, tmp_path: Path) -> None:
        settings = self._settings()
        backend = SearchBackend(str(tmp_path / "failed.db"), settings=settings)
        with patch(
            "sif.mcp.backend.EmbeddingManager.from_settings", side_effect=RuntimeError("boom")
        ) as from_settings:
            assert backend._ensure_embedder() is None
            assert backend._ensure_embedder() is None

        assert from_settings.call_count == 1
        assert backend._load_attempted is True
        assert backend._load_failed is True
        assert backend._embedder is None
        assert backend._identity is None

    @pytest.mark.asyncio
    async def test_vec_search_without_an_embedder_names_the_remedy(self, tmp_path: Path) -> None:
        db_path, settings = _seed_suggestion_db(tmp_path)
        backend = _suggestion_backend(db_path, settings)
        backend._load_attempted = True
        backend._load_failed = True

        with pytest.raises(RuntimeError, match='pip install "docsif\\[embed\\]"'):
            await backend.vec_search("quantum")


class TestLexSearchDirectPath:
    """D-17: lex_search mirrors the CLI BM25 one-shot with one enrichment."""

    @pytest.mark.asyncio
    async def test_bm25_options_and_one_enrichment(self, tmp_path: Path) -> None:
        from sif.core.filters import parse_filter

        db_path, settings = _seed_suggestion_db(tmp_path)
        backend = _suggestion_backend(db_path, settings)
        node = parse_filter(_FILTER_PAYLOAD)

        with (
            patch("sif.mcp.backend.BM25Searcher") as mock_bm25_cls,
            patch(
                "sif.mcp.backend.enrich_results",
                side_effect=lambda conn, results: results,  # noqa: ARG005
            ) as enrich,
        ):
            mock_bm25_cls.return_value.search.return_value = [_weight_result()]
            results = await backend.lex_search(
                "quantum",
                collections=["notes"],
                limit=3,
                offset=2,
                min_score=0.25,
                filter_node=node,
            )

        options = mock_bm25_cls.return_value.search.call_args[0][1]
        assert options.limit == 3
        assert options.offset == 2
        assert options.min_score == 0.25
        assert options.filter is node
        assert options.collection_ids == ["c1"]
        assert options.include_content is False
        assert options.include_highlights is True
        assert enrich.call_count == 1
        assert len(results) == 1
        assert results[0].doc_id == "doc1"

    @pytest.mark.asyncio
    async def test_unknown_collection_returns_an_empty_page_without_searching(
        self, tmp_path: Path
    ) -> None:
        db_path, settings = _seed_suggestion_db(tmp_path)
        backend = _suggestion_backend(db_path, settings)

        with patch("sif.mcp.backend.BM25Searcher") as mock_bm25_cls:
            results = await backend.lex_search("quantum", collections=["missing"])

        assert list(results) == []
        assert results.suggestions == []
        mock_bm25_cls.assert_not_called()


class TestVecSearchDirectPath:
    """D-17: vec_search mirrors the CLI vector one-shot with identity first."""

    @staticmethod
    def _backend_with_manager(tmp_path: Path) -> tuple[SearchBackend, _FakeManager, list[str]]:
        db_path, settings = _seed_suggestion_db(tmp_path)
        backend = _suggestion_backend(db_path, settings)
        calls: list[str] = []
        manager = _FakeManager(calls=calls)
        backend._manager = manager
        backend._identity = _identity("loaded")
        backend._load_attempted = True
        return backend, manager, calls

    @pytest.mark.asyncio
    async def test_identity_is_checked_before_embedding_and_enriches_once(
        self, tmp_path: Path
    ) -> None:
        from sif.core.filters import parse_filter
        from sif.embedding.identity import IdentityCheck

        backend, _manager, calls = self._backend_with_manager(tmp_path)
        node = parse_filter(_FILTER_PAYLOAD)
        trusted = IdentityCheck(
            status="ok",
            stored=_identity("loaded"),
            current=_identity("loaded"),
        )

        def _check(_conn: object, _current: object, mode: str = "search") -> IdentityCheck:
            assert mode == "search"
            calls.append("identity")
            return trusted

        with (
            patch("sif.mcp.backend.check_identity", side_effect=_check),
            patch("sif.mcp.backend.VectorSearcher") as mock_vec_cls,
            patch(
                "sif.mcp.backend.enrich_results",
                side_effect=lambda conn, results, **_kwargs: results,  # noqa: ARG005
            ) as enrich,
        ):
            mock_vec_cls.return_value.search.return_value = [_weight_result()]
            results = await backend.vec_search(
                "quantum",
                collections=["notes"],
                limit=2,
                offset=1,
                per_chunk=True,
                min_score=0.3,
                filter_node=node,
            )

        assert calls == ["identity", "embed"]
        options = mock_vec_cls.return_value.search.call_args[0][1]
        assert options.limit == 2
        assert options.offset == 1
        assert options.per_chunk is True
        assert options.min_score == 0.3
        assert options.filter is node
        assert options.collection_ids == ["c1"]
        mock_vec_cls.assert_called_once_with(ANY, 8)
        assert enrich.call_count == 1
        assert len(results) == 1

    @pytest.mark.asyncio
    async def test_untrusted_identity_marks_the_single_enrichment(
        self, tmp_path: Path, caplog
    ) -> None:
        import logging

        from sif.embedding.identity import IdentityCheck

        backend, _manager, _calls = self._backend_with_manager(tmp_path)
        mismatch = IdentityCheck(
            status="mismatch",
            stored=_identity("stored-vec"),
            current=_identity("loaded-vec"),
        )

        with (
            patch("sif.mcp.backend.check_identity", return_value=mismatch),
            patch("sif.mcp.backend.VectorSearcher") as mock_vec_cls,
            patch(
                "sif.mcp.backend.enrich_results",
                side_effect=lambda conn, results, **_kwargs: results,  # noqa: ARG005
            ) as enrich,
            caplog.at_level(logging.WARNING, logger="sif.embedding.identity"),
        ):
            mock_vec_cls.return_value.search.return_value = [_weight_result()]
            await backend.vec_search("quantum")

        assert enrich.call_count == 1
        assert enrich.call_args.kwargs["vectors_untrusted"] is True
        warnings = [
            record
            for record in caplog.records
            if "identity mismatch" in record.getMessage().lower()
        ]
        assert len(warnings) == 1

    @pytest.mark.asyncio
    async def test_dimension_mismatch_refuses_before_embedding(self, tmp_path: Path) -> None:
        from sif.embedding.identity import IdentityCheck, IdentityDimensionError

        backend, _manager, calls = self._backend_with_manager(tmp_path)
        mismatch = IdentityCheck(
            status="dimension_mismatch",
            stored=_identity("stored", dimension=8),
            current=_identity("loaded", dimension=4),
        )

        with (
            patch("sif.mcp.backend.check_identity", return_value=mismatch),
            patch("sif.mcp.backend.VectorSearcher") as mock_vec_cls,
            pytest.raises(IdentityDimensionError, match="Embedding dimension mismatch"),
        ):
            await backend.vec_search("quantum")

        assert calls == []
        mock_vec_cls.assert_not_called()

    @pytest.mark.asyncio
    async def test_unknown_collection_returns_an_empty_page_before_identity(
        self, tmp_path: Path
    ) -> None:
        backend, _manager, calls = self._backend_with_manager(tmp_path)

        with (
            patch("sif.mcp.backend.check_identity") as check,
            patch("sif.mcp.backend.VectorSearcher") as mock_vec_cls,
        ):
            results = await backend.vec_search("quantum", collections=["missing"])

        assert list(results) == []
        assert calls == []
        check.assert_not_called()
        mock_vec_cls.assert_not_called()
