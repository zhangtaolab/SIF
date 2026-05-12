"""Tests for SearchBackend."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from sif.mcp.backend import SearchBackend, _truncate_content
from sif.mcp.protocol import CollectionInfo, Document, SearchResult


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

    with patch("sif.mcp.backend.SearchPipeline") as mock_pipeline:
        mock_pipeline.return_value.search.return_value = [mock_result]
        results = await backend.hybrid_search("test query")

    assert len(results) == 1
    assert isinstance(results[0], SearchResult)
    assert results[0].doc_id == "doc1"


@pytest.mark.asyncio
async def test_get_document_found(backend):
    """Mock get_document returning a document."""
    mock_doc = MagicMock()
    mock_doc.id = "doc1"
    mock_doc.path = "/test.md"
    mock_doc.title = "Test"
    mock_doc.content = "Hello\nWorld"
    mock_doc.metadata = {}

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
