"""Tests for document indexer in sif.indexing.indexer."""

from __future__ import annotations

import hashlib
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from sif.core.models import Collection, DocumentChunk
from sif.indexing.indexer import DocumentIndexer, IndexResult, IndexStatus


@pytest.fixture
def mock_scanner() -> MagicMock:
    """Return a mock file scanner."""
    return MagicMock()


@pytest.fixture
def mock_parser() -> MagicMock:
    """Return a mock markdown parser."""
    return MagicMock()


@pytest.fixture
def mock_chunker() -> MagicMock:
    """Return a mock document chunker."""
    return MagicMock()


@pytest.fixture
def mock_embedding_manager() -> MagicMock:
    """Return a mock embedding manager."""
    return MagicMock()


@pytest.fixture
def mock_repository() -> MagicMock:
    """Return a mock document repository."""
    return MagicMock()


@pytest.fixture
def mock_progress() -> MagicMock:
    """Return a mock progress tracker."""
    return MagicMock()


@pytest.fixture
def indexer(
    mock_scanner: MagicMock,
    mock_parser: MagicMock,
    mock_chunker: MagicMock,
    mock_embedding_manager: MagicMock,
    mock_repository: MagicMock,
    mock_progress: MagicMock,
) -> DocumentIndexer:
    """Return a DocumentIndexer with all mocked dependencies."""
    return DocumentIndexer(
        scanner=mock_scanner,
        parser=mock_parser,
        chunker=mock_chunker,
        embedding_manager=mock_embedding_manager,
        repository=mock_repository,
        progress_tracker=mock_progress,
    )


@pytest.fixture
def sample_collection() -> Collection:
    """Return a sample collection."""
    return Collection(
        id="coll-1",
        name="test-collection",
        path="/tmp/test-docs",
        pattern="**/*.md",
        ignore_patterns=["*.tmp"],
    )


# =============================================================================
# DocumentIndexer Initialization Tests
# =============================================================================


class TestDocumentIndexerInit:
    """Tests for DocumentIndexer initialization."""

    def test_init_with_all_deps(self, indexer: DocumentIndexer) -> None:
        """Test initialization stores all dependencies."""
        assert indexer._scanner is not None
        assert indexer._parser is not None
        assert indexer._chunker is not None
        assert indexer._embedding_manager is not None
        assert indexer._repository is not None
        assert indexer._progress is not None

    def test_init_default_progress(self, mock_scanner: MagicMock) -> None:
        """Test default progress tracker is created."""
        from sif.utils.progress import RichProgressTracker

        indexer = DocumentIndexer(
            scanner=mock_scanner,
            parser=MagicMock(),
            chunker=MagicMock(),
            embedding_manager=MagicMock(),
            repository=MagicMock(),
        )
        assert isinstance(indexer._progress, RichProgressTracker)


# =============================================================================
# index_collection Tests
# =============================================================================


class TestIndexCollection:
    """Tests for DocumentIndexer.index_collection."""

    def test_index_collection_empty(
        self, indexer: DocumentIndexer, sample_collection: Collection
    ) -> None:
        """Test indexing empty collection returns zero counts."""
        mock_scan_result = MagicMock()
        mock_scan_result.files = []
        mock_scan_result.file_count = 0
        indexer._scanner.scan.return_value = mock_scan_result
        indexer._repository.list_by_collection.return_value = []

        result = indexer.index_collection(sample_collection)

        assert result.files_processed == 0
        assert result.files_added == 0
        assert result.files_updated == 0
        assert result.files_skipped == 0
        assert result.files_failed == 0
        assert result.chunks_created == 0
        assert result.errors == []
        indexer._progress.start.assert_called_once_with("Indexing documents", total=0)
        indexer._progress.finish.assert_called_once()

    def test_index_collection_adds_new_files(
        self,
        indexer: DocumentIndexer,
        sample_collection: Collection,
        tmp_path: Path,
    ) -> None:
        """Test indexing adds new files."""
        # Create a temp file
        test_file = tmp_path / "test.md"
        test_content = "# Test\n\nThis is a test document."
        test_file.write_text(test_content)

        mock_scan_result = MagicMock()
        mock_scan_result.files = [test_file]
        mock_scan_result.file_count = 1
        indexer._scanner.scan.return_value = mock_scan_result
        indexer._repository.get_by_path.return_value = None
        indexer._repository.list_by_collection.return_value = []

        mock_parse_result = MagicMock()
        mock_parse_result.content = test_content
        mock_parse_result.title = "Test"
        mock_parse_result.metadata = {}
        indexer._parser.parse.return_value = mock_parse_result

        mock_chunk = DocumentChunk(
            id="chunk-1",
            document_id="",
            content="This is a test document.",
            sequence=0,
            start_pos=0,
            end_pos=26,
            token_count=10,
        )
        indexer._chunker.chunk.return_value = [mock_chunk]

        mock_embedding_response = MagicMock()
        mock_embedding_response.embeddings = [[0.1, 0.2, 0.3]]
        indexer._embedding_manager.embed.return_value = mock_embedding_response

        result = indexer.index_collection(sample_collection)

        assert result.files_processed == 1
        assert result.files_added == 1
        assert result.files_updated == 0
        assert result.files_skipped == 0
        assert result.files_failed == 0
        assert result.chunks_created == 0  # chunks_created not tracked in result
        indexer._repository.create.assert_called_once()

    def test_index_collection_skips_unchanged(
        self,
        indexer: DocumentIndexer,
        sample_collection: Collection,
        tmp_path: Path,
    ) -> None:
        """Test indexing skips unchanged files."""
        test_file = tmp_path / "test.md"
        test_content = "# Test\n\nThis is a test document."
        test_file.write_text(test_content)
        checksum = hashlib.sha256(test_content.encode()).hexdigest()

        mock_scan_result = MagicMock()
        mock_scan_result.files = [test_file]
        mock_scan_result.file_count = 1
        indexer._scanner.scan.return_value = mock_scan_result
        indexer._repository.list_by_collection.return_value = []

        # File already exists with same checksum
        existing_doc = MagicMock()
        existing_doc.checksum = checksum
        indexer._repository.get_by_path.return_value = existing_doc

        result = indexer.index_collection(sample_collection)

        assert result.files_processed == 1
        assert result.files_added == 0
        assert result.files_updated == 0
        assert result.files_skipped == 1
        assert result.files_failed == 0
        indexer._parser.parse.assert_not_called()

    def test_index_collection_updates_changed(
        self,
        indexer: DocumentIndexer,
        sample_collection: Collection,
        tmp_path: Path,
    ) -> None:
        """Test indexing updates changed files."""
        test_file = tmp_path / "test.md"
        test_content = "# Test\n\nThis is a test document."
        test_file.write_text(test_content)

        mock_scan_result = MagicMock()
        mock_scan_result.files = [test_file]
        mock_scan_result.file_count = 1
        indexer._scanner.scan.return_value = mock_scan_result
        indexer._repository.list_by_collection.return_value = []

        # File exists but with different checksum
        existing_doc = MagicMock()
        existing_doc.checksum = "old_checksum"
        existing_doc.id = "doc-1"
        indexer._repository.get_by_path.return_value = existing_doc

        mock_parse_result = MagicMock()
        mock_parse_result.content = test_content
        mock_parse_result.title = "Test"
        mock_parse_result.metadata = {}
        indexer._parser.parse.return_value = mock_parse_result

        indexer._chunker.chunk.return_value = []
        mock_embedding_response = MagicMock()
        mock_embedding_response.embeddings = []
        indexer._embedding_manager.embed.return_value = mock_embedding_response

        result = indexer.index_collection(sample_collection)

        assert result.files_processed == 1
        assert result.files_added == 0
        assert result.files_updated == 1
        assert result.files_skipped == 0
        indexer._repository.update.assert_called_once()

    def test_index_collection_handles_errors(
        self,
        indexer: DocumentIndexer,
        sample_collection: Collection,
        tmp_path: Path,
    ) -> None:
        """Test indexing handles file errors gracefully."""
        test_file = tmp_path / "test.md"
        test_content = "# Test"
        test_file.write_text(test_content)

        mock_scan_result = MagicMock()
        mock_scan_result.files = [test_file]
        mock_scan_result.file_count = 1
        indexer._scanner.scan.return_value = mock_scan_result
        indexer._repository.list_by_collection.return_value = []

        # Parser raises an error
        indexer._parser.parse.side_effect = ValueError("Parse error")

        result = indexer.index_collection(sample_collection)

        assert result.files_failed == 1
        assert len(result.errors) == 1
        assert "Parse error" in result.errors[0]

    def test_index_collection_updates_document_count(
        self,
        indexer: DocumentIndexer,
        sample_collection: Collection,
    ) -> None:
        """Test collection document count is updated."""
        mock_scan_result = MagicMock()
        mock_scan_result.files = []
        mock_scan_result.file_count = 0
        indexer._scanner.scan.return_value = mock_scan_result
        indexer._repository.list_by_collection.return_value = [MagicMock(), MagicMock()]

        indexer.index_collection(sample_collection)

        assert sample_collection.document_count == 2

    def test_index_collection_marks_indexed(
        self,
        indexer: DocumentIndexer,
        sample_collection: Collection,
    ) -> None:
        """Test collection is marked as indexed."""
        mock_scan_result = MagicMock()
        mock_scan_result.files = []
        mock_scan_result.file_count = 0
        indexer._scanner.scan.return_value = mock_scan_result
        indexer._repository.list_by_collection.return_value = []

        assert sample_collection.last_indexed_at is None

        indexer.index_collection(sample_collection)

        assert sample_collection.last_indexed_at is not None

    def test_index_collection_multiple_files_mixed_results(
        self,
        indexer: DocumentIndexer,
        sample_collection: Collection,
        tmp_path: Path,
    ) -> None:
        """Test indexing multiple files with mixed results."""
        file1 = tmp_path / "file1.md"
        file1.write_text("File 1 content")
        file2 = tmp_path / "file2.md"
        file2.write_text("File 2 content")

        mock_scan_result = MagicMock()
        mock_scan_result.files = [file1, file2]
        mock_scan_result.file_count = 2
        indexer._scanner.scan.return_value = mock_scan_result
        indexer._repository.list_by_collection.return_value = []

        # file1 is new, file2 causes error
        indexer._repository.get_by_path.side_effect = [None, MagicMock(checksum="bad")]
        indexer._parser.parse.side_effect = [
            MagicMock(content="File 1", title="F1", metadata={}),
            Exception("Parse failed"),
        ]
        indexer._chunker.chunk.return_value = []
        mock_embedding_response = MagicMock()
        mock_embedding_response.embeddings = []
        indexer._embedding_manager.embed.return_value = mock_embedding_response

        result = indexer.index_collection(sample_collection)

        assert result.files_processed == 1
        assert result.files_added == 1
        assert result.files_failed == 1
        assert len(result.errors) == 1


# =============================================================================
# _index_file Tests
# =============================================================================


class TestIndexFile:
    """Tests for DocumentIndexer._index_file."""

    def test_index_new_file(
        self,
        indexer: DocumentIndexer,
        sample_collection: Collection,
        tmp_path: Path,
    ) -> None:
        """Test indexing a new file returns ADDED."""
        test_file = tmp_path / "new.md"
        test_content = "# New File\n\nContent here."
        test_file.write_text(test_content)

        indexer._repository.get_by_path.return_value = None

        mock_parse_result = MagicMock()
        mock_parse_result.content = test_content
        mock_parse_result.title = "New File"
        mock_parse_result.metadata = {"author": "Test"}
        indexer._parser.parse.return_value = mock_parse_result

        mock_chunk = DocumentChunk(
            id="chunk-1",
            document_id="",
            content="Content here.",
            sequence=0,
            start_pos=0,
            end_pos=15,
            token_count=5,
        )
        indexer._chunker.chunk.return_value = [mock_chunk]

        mock_embedding_response = MagicMock()
        mock_embedding_response.embeddings = [[0.1, 0.2]]
        indexer._embedding_manager.embed.return_value = mock_embedding_response

        result = indexer._index_file(test_file, sample_collection.id)

        assert result == IndexStatus.ADDED
        indexer._repository.create.assert_called_once()

    def test_index_unchanged_file(
        self,
        indexer: DocumentIndexer,
        sample_collection: Collection,
        tmp_path: Path,
    ) -> None:
        """Test indexing unchanged file returns SKIPPED."""
        test_file = tmp_path / "same.md"
        test_content = "Same content"
        test_file.write_text(test_content)
        checksum = hashlib.sha256(test_content.encode()).hexdigest()

        existing_doc = MagicMock()
        existing_doc.checksum = checksum
        indexer._repository.get_by_path.return_value = existing_doc

        result = indexer._index_file(test_file, sample_collection.id)

        assert result == IndexStatus.SKIPPED
        indexer._parser.parse.assert_not_called()

    def test_index_updated_file(
        self,
        indexer: DocumentIndexer,
        sample_collection: Collection,
        tmp_path: Path,
    ) -> None:
        """Test indexing changed file returns COMPLETED."""
        test_file = tmp_path / "updated.md"
        test_content = "Updated content"
        test_file.write_text(test_content)

        existing_doc = MagicMock()
        existing_doc.checksum = "old_checksum"
        existing_doc.id = "doc-old"
        indexer._repository.get_by_path.return_value = existing_doc

        mock_parse_result = MagicMock()
        mock_parse_result.content = test_content
        mock_parse_result.title = "Updated"
        mock_parse_result.metadata = {}
        indexer._parser.parse.return_value = mock_parse_result

        indexer._chunker.chunk.return_value = []
        mock_embedding_response = MagicMock()
        mock_embedding_response.embeddings = []
        indexer._embedding_manager.embed.return_value = mock_embedding_response

        result = indexer._index_file(test_file, sample_collection.id)

        assert result == IndexStatus.COMPLETED
        indexer._repository.update.assert_called_once()

    def test_index_file_with_chunks(
        self,
        indexer: DocumentIndexer,
        sample_collection: Collection,
        tmp_path: Path,
    ) -> None:
        """Test indexing file generates embeddings for chunks."""
        test_file = tmp_path / "chunked.md"
        test_content = "Chunk 1\n\nChunk 2"
        test_file.write_text(test_content)

        indexer._repository.get_by_path.return_value = None

        mock_parse_result = MagicMock()
        mock_parse_result.content = test_content
        mock_parse_result.title = "Chunked"
        mock_parse_result.metadata = {}
        indexer._parser.parse.return_value = mock_parse_result

        chunk1 = DocumentChunk(
            id="",
            document_id="",
            content="Chunk 1",
            sequence=0,
            start_pos=0,
            end_pos=7,
            token_count=3,
        )
        chunk2 = DocumentChunk(
            id="",
            document_id="",
            content="Chunk 2",
            sequence=1,
            start_pos=9,
            end_pos=16,
            token_count=3,
        )
        indexer._chunker.chunk.return_value = [chunk1, chunk2]

        mock_embedding_response = MagicMock()
        mock_embedding_response.embeddings = [[0.1, 0.2], [0.3, 0.4]]
        indexer._embedding_manager.embed.return_value = mock_embedding_response

        indexer._index_file(test_file, sample_collection.id)

        indexer._embedding_manager.embed.assert_called_once_with(["Chunk 1", "Chunk 2"])
        indexer._repository.create.assert_called_once()

        # Verify document has chunks with embeddings
        created_doc = indexer._repository.create.call_args[0][0]
        assert len(created_doc.chunks) == 2
        assert created_doc.chunks[0].embedding == [0.1, 0.2]
        assert created_doc.chunks[1].embedding == [0.3, 0.4]

    def test_index_file_no_chunks(
        self,
        indexer: DocumentIndexer,
        sample_collection: Collection,
        tmp_path: Path,
    ) -> None:
        """Test indexing file with no chunks does not call embed."""
        test_file = tmp_path / "no_chunks.md"
        test_content = "Short"
        test_file.write_text(test_content)

        indexer._repository.get_by_path.return_value = None

        mock_parse_result = MagicMock()
        mock_parse_result.content = test_content
        mock_parse_result.title = "No Chunks"
        mock_parse_result.metadata = {}
        indexer._parser.parse.return_value = mock_parse_result

        indexer._chunker.chunk.return_value = []

        result = indexer._index_file(test_file, sample_collection.id)

        assert result == IndexStatus.ADDED
        indexer._embedding_manager.embed.assert_not_called()


# =============================================================================
# reindex_collection Tests
# =============================================================================


class TestReindexCollection:
    """Tests for DocumentIndexer.reindex_collection."""

    def test_reindex_clears_and_reindexes(
        self,
        indexer: DocumentIndexer,
        sample_collection: Collection,
    ) -> None:
        """Test reindex deletes existing and reindexes."""
        mock_scan_result = MagicMock()
        mock_scan_result.files = []
        mock_scan_result.file_count = 0
        indexer._scanner.scan.return_value = mock_scan_result
        indexer._repository.list_by_collection.return_value = []

        result = indexer.reindex_collection(sample_collection)

        indexer._repository.delete_by_collection.assert_called_once_with(sample_collection.id)
        assert isinstance(result, IndexResult)

    def test_reindex_returns_result(self, indexer: DocumentIndexer) -> None:
        """Test reindex returns an IndexResult."""
        collection = Collection(
            id="coll-reindex",
            name="reindex-test",
            path="/tmp/reindex",
        )

        mock_scan_result = MagicMock()
        mock_scan_result.files = []
        mock_scan_result.file_count = 0
        indexer._scanner.scan.return_value = mock_scan_result
        indexer._repository.list_by_collection.return_value = []

        result = indexer.reindex_collection(collection)

        assert result.files_processed == 0
        assert result.files_added == 0
        assert result.files_failed == 0


# =============================================================================
# IndexResult Tests
# =============================================================================


class TestIndexResult:
    """Tests for IndexResult dataclass."""

    def test_index_result_creation(self) -> None:
        """Test IndexResult can be created with all fields."""
        result = IndexResult(
            files_processed=10,
            files_added=5,
            files_updated=3,
            files_skipped=2,
            files_failed=0,
            chunks_created=15,
            errors=[],
        )
        assert result.files_processed == 10
        assert result.files_added == 5
        assert result.files_updated == 3
        assert result.files_skipped == 2
        assert result.files_failed == 0
        assert result.chunks_created == 15
        assert result.errors == []

    def test_index_result_with_errors(self) -> None:
        """Test IndexResult can hold errors."""
        result = IndexResult(
            files_processed=5,
            files_added=3,
            files_updated=1,
            files_skipped=0,
            files_failed=1,
            chunks_created=5,
            errors=["/path: some error"],
        )
        assert len(result.errors) == 1
        assert result.files_failed == 1


# =============================================================================
# IndexStatus Tests
# =============================================================================


class TestIndexStatus:
    """Tests for IndexStatus enum."""

    def test_status_values_exist(self) -> None:
        """Test all status values exist."""
        assert IndexStatus.PENDING is not None
        assert IndexStatus.INDEXING is not None
        assert IndexStatus.COMPLETED is not None
        assert IndexStatus.FAILED is not None
        assert IndexStatus.SKIPPED is not None

    def test_status_is_enum(self) -> None:
        """Test IndexStatus is an enum."""
        assert isinstance(IndexStatus.ADDED, IndexStatus)

    def test_status_auto_values(self) -> None:
        """Test auto-generated enum values are unique."""
        values = [s.value for s in IndexStatus]
        assert len(values) == len(set(values))
