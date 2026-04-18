"""Unit tests for repository interfaces and implementations.

This module tests the Repository pattern implementations including:
- CollectionRepository: CRUD operations for collections
- DocumentRepository: CRUD operations for documents
- ContextRepository: CRUD operations for contexts
"""

import uuid
from datetime import datetime
from unittest.mock import MagicMock, create_autospec

import pytest

from docsift.core.collection import Collection, CollectionRepository
from docsift.core.context import Context, ContextRepository, ContextType
from docsift.core.document import Document, DocumentChunk, DocumentMetadata, DocumentRepository
from docsift.database.repository import (
    CollectionRepository as AbstractCollectionRepository,
    ContextRepository as AbstractContextRepository,
    DocumentRepository as AbstractDocumentRepository,
    SearchRepository,
)


# =============================================================================
# CollectionRepository Tests
# =============================================================================


class TestCollectionRepository:
    """Test suite for CollectionRepository interface."""

    @pytest.fixture
    def mock_collection_repo(self) -> MagicMock:
        """Create a mock CollectionRepository."""
        mock = create_autospec(AbstractCollectionRepository, instance=True)
        return mock

    @pytest.fixture
    def sample_collection(self) -> Collection:
        """Create a sample collection for testing."""
        return Collection(
            id=str(uuid.uuid4()),
            name="test-collection",
            description="A test collection",
            paths=["/path/to/docs"],
            document_count=5,
            chunk_count=20,
            metadata={"key": "value"},
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )

    @pytest.fixture
    def sample_collections(self) -> list[Collection]:
        """Create multiple sample collections."""
        return [
            Collection(
                id=str(uuid.uuid4()),
                name=f"collection-{i}",
                description=f"Test collection {i}",
                paths=[f"/path/{i}"],
                document_count=i * 10,
                chunk_count=i * 40,
            )
            for i in range(1, 4)
        ]

    def test_get_by_id_existing(
        self, mock_collection_repo: MagicMock, sample_collection: Collection
    ) -> None:
        """Test retrieving an existing collection by ID.

        Arrange: Set up mock to return a collection
        Act: Call get_by_id with valid ID
        Assert: Returns the expected collection
        """
        # Arrange
        mock_collection_repo.get_by_id.return_value = sample_collection

        # Act
        result = mock_collection_repo.get_by_id(sample_collection.id)

        # Assert
        assert result is not None
        assert result.id == sample_collection.id
        assert result.name == sample_collection.name
        mock_collection_repo.get_by_id.assert_called_once_with(sample_collection.id)

    def test_get_by_id_nonexistent(self, mock_collection_repo: MagicMock) -> None:
        """Test retrieving a non-existent collection by ID.

        Arrange: Set up mock to return None
        Act: Call get_by_id with invalid ID
        Assert: Returns None
        """
        # Arrange
        mock_collection_repo.get_by_id.return_value = None

        # Act
        result = mock_collection_repo.get_by_id("nonexistent-id")

        # Assert
        assert result is None
        mock_collection_repo.get_by_id.assert_called_once_with("nonexistent-id")

    def test_get_by_name_existing(
        self, mock_collection_repo: MagicMock, sample_collection: Collection
    ) -> None:
        """Test retrieving a collection by name.

        Arrange: Set up mock to return a collection
        Act: Call get_by_name with valid name
        Assert: Returns the expected collection
        """
        # Arrange
        mock_collection_repo.get_by_name.return_value = sample_collection

        # Act
        result = mock_collection_repo.get_by_name("test-collection")

        # Assert
        assert result is not None
        assert result.name == "test-collection"
        mock_collection_repo.get_by_name.assert_called_once_with("test-collection")

    def test_get_by_name_nonexistent(self, mock_collection_repo: MagicMock) -> None:
        """Test retrieving a non-existent collection by name.

        Arrange: Set up mock to return None
        Act: Call get_by_name with invalid name
        Assert: Returns None
        """
        # Arrange
        mock_collection_repo.get_by_name.return_value = None

        # Act
        result = mock_collection_repo.get_by_name("nonexistent")

        # Assert
        assert result is None

    def test_create_collection(
        self, mock_collection_repo: MagicMock, sample_collection: Collection
    ) -> None:
        """Test creating a new collection.

        Arrange: Set up mock to return the created collection
        Act: Call create with a new collection
        Assert: Returns the created collection with generated ID
        """
        # Arrange
        mock_collection_repo.create.return_value = sample_collection

        # Act
        result = mock_collection_repo.create(sample_collection)

        # Assert
        assert result is not None
        assert result.id == sample_collection.id
        assert result.name == sample_collection.name
        mock_collection_repo.create.assert_called_once_with(sample_collection)

    def test_update_collection(
        self, mock_collection_repo: MagicMock, sample_collection: Collection
    ) -> None:
        """Test updating an existing collection.

        Arrange: Set up mock to return updated collection
        Act: Call update with modified collection
        Assert: Returns the updated collection
        """
        # Arrange
        sample_collection.description = "Updated description"
        mock_collection_repo.update.return_value = sample_collection

        # Act
        result = mock_collection_repo.update(sample_collection)

        # Assert
        assert result is not None
        assert result.description == "Updated description"
        mock_collection_repo.update.assert_called_once_with(sample_collection)

    def test_delete_collection(self, mock_collection_repo: MagicMock) -> None:
        """Test deleting a collection.

        Arrange: Set up mock to return True
        Act: Call delete with collection ID
        Assert: Returns True indicating success
        """
        # Arrange
        collection_id = str(uuid.uuid4())
        mock_collection_repo.delete.return_value = True

        # Act
        result = mock_collection_repo.delete(collection_id)

        # Assert
        assert result is True
        mock_collection_repo.delete.assert_called_once_with(collection_id)

    def test_delete_nonexistent_collection(self, mock_collection_repo: MagicMock) -> None:
        """Test deleting a non-existent collection.

        Arrange: Set up mock to return False
        Act: Call delete with invalid ID
        Assert: Returns False indicating failure
        """
        # Arrange
        mock_collection_repo.delete.return_value = False

        # Act
        result = mock_collection_repo.delete("nonexistent-id")

        # Assert
        assert result is False

    def test_list_all_collections(
        self, mock_collection_repo: MagicMock, sample_collections: list[Collection]
    ) -> None:
        """Test listing all collections.

        Arrange: Set up mock to return list of collections
        Act: Call list_all
        Assert: Returns all collections
        """
        # Arrange
        mock_collection_repo.list_all.return_value = sample_collections

        # Act
        result = mock_collection_repo.list_all()

        # Assert
        assert len(result) == 3
        assert all(isinstance(c, Collection) for c in result)
        mock_collection_repo.list_all.assert_called_once()

    def test_list_all_empty(self, mock_collection_repo: MagicMock) -> None:
        """Test listing collections when none exist.

        Arrange: Set up mock to return empty list
        Act: Call list_all
        Assert: Returns empty list
        """
        # Arrange
        mock_collection_repo.list_all.return_value = []

        # Act
        result = mock_collection_repo.list_all()

        # Assert
        assert result == []

    def test_exists_true(self, mock_collection_repo: MagicMock) -> None:
        """Test checking if a collection exists (exists).

        Arrange: Set up mock to return True
        Act: Call exists with existing name
        Assert: Returns True
        """
        # Arrange
        mock_collection_repo.exists.return_value = True

        # Act
        result = mock_collection_repo.exists("existing-collection")

        # Assert
        assert result is True

    def test_exists_false(self, mock_collection_repo: MagicMock) -> None:
        """Test checking if a collection exists (doesn't exist).

        Arrange: Set up mock to return False
        Act: Call exists with non-existent name
        Assert: Returns False
        """
        # Arrange
        mock_collection_repo.exists.return_value = False

        # Act
        result = mock_collection_repo.exists("nonexistent")

        # Assert
        assert result is False


# =============================================================================
# DocumentRepository Tests
# =============================================================================


class TestDocumentRepository:
    """Test suite for DocumentRepository interface."""

    @pytest.fixture
    def mock_document_repo(self) -> MagicMock:
        """Create a mock DocumentRepository."""
        mock = create_autospec(AbstractDocumentRepository, instance=True)
        return mock

    @pytest.fixture
    def sample_document(self) -> Document:
        """Create a sample document for testing."""
        return Document(
            id=str(uuid.uuid4()),
            collection_id=str(uuid.uuid4()),
            path="/path/to/document.md",
            content="Test document content",
            checksum="abc123",
            file_size=100,
            metadata=DocumentMetadata(
                title="Test Document",
                author="Test Author",
                tags=["test", "sample"],
            ),
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )

    @pytest.fixture
    def sample_documents(self, sample_document: Document) -> list[Document]:
        """Create multiple sample documents."""
        documents = [sample_document]
        for i in range(2):
            doc = Document(
                id=str(uuid.uuid4()),
                collection_id=sample_document.collection_id,
                path=f"/path/to/document_{i}.md",
                content=f"Content {i}",
                checksum=f"checksum_{i}",
                file_size=50 + i * 10,
            )
            documents.append(doc)
        return documents

    @pytest.fixture
    def sample_chunks(self, sample_document: Document) -> list[DocumentChunk]:
        """Create sample chunks for testing."""
        return [
            DocumentChunk(
                id=str(uuid.uuid4()),
                document_id=sample_document.id,
                content=f"Chunk {i} content",
                start_line=i * 10,
                end_line=i * 10 + 5,
                token_count=20,
            )
            for i in range(3)
        ]

    def test_get_by_id_existing(
        self, mock_document_repo: MagicMock, sample_document: Document
    ) -> None:
        """Test retrieving an existing document by ID.

        Arrange: Set up mock to return a document
        Act: Call get_by_id with valid ID
        Assert: Returns the expected document
        """
        # Arrange
        mock_document_repo.get_by_id.return_value = sample_document

        # Act
        result = mock_document_repo.get_by_id(sample_document.id)

        # Assert
        assert result is not None
        assert result.id == sample_document.id
        assert result.path == sample_document.path
        mock_document_repo.get_by_id.assert_called_once_with(sample_document.id)

    def test_get_by_id_nonexistent(self, mock_document_repo: MagicMock) -> None:
        """Test retrieving a non-existent document by ID.

        Arrange: Set up mock to return None
        Act: Call get_by_id with invalid ID
        Assert: Returns None
        """
        # Arrange
        mock_document_repo.get_by_id.return_value = None

        # Act
        result = mock_document_repo.get_by_id("nonexistent-id")

        # Assert
        assert result is None

    def test_get_by_path_existing(
        self, mock_document_repo: MagicMock, sample_document: Document
    ) -> None:
        """Test retrieving a document by path.

        Arrange: Set up mock to return a document
        Act: Call get_by_path with valid path and collection_id
        Assert: Returns the expected document
        """
        # Arrange
        mock_document_repo.get_by_path.return_value = sample_document

        # Act
        result = mock_document_repo.get_by_path(
            "/path/to/document.md",
            sample_document.collection_id,
        )

        # Assert
        assert result is not None
        assert result.path == "/path/to/document.md"
        mock_document_repo.get_by_path.assert_called_once_with(
            "/path/to/document.md",
            sample_document.collection_id,
        )

    def test_create_document(
        self, mock_document_repo: MagicMock, sample_document: Document
    ) -> None:
        """Test creating a new document.

        Arrange: Set up mock to return the created document
        Act: Call create with a new document
        Assert: Returns the created document
        """
        # Arrange
        mock_document_repo.create.return_value = sample_document

        # Act
        result = mock_document_repo.create(sample_document)

        # Assert
        assert result is not None
        assert result.id == sample_document.id
        mock_document_repo.create.assert_called_once_with(sample_document)

    def test_update_document(
        self, mock_document_repo: MagicMock, sample_document: Document
    ) -> None:
        """Test updating an existing document.

        Arrange: Set up mock to return updated document
        Act: Call update with modified document
        Assert: Returns the updated document
        """
        # Arrange
        sample_document.content = "Updated content"
        mock_document_repo.update.return_value = sample_document

        # Act
        result = mock_document_repo.update(sample_document)

        # Assert
        assert result is not None
        assert result.content == "Updated content"
        mock_document_repo.update.assert_called_once_with(sample_document)

    def test_delete_document(self, mock_document_repo: MagicMock) -> None:
        """Test deleting a document.

        Arrange: Set up mock to return True
        Act: Call delete with document ID
        Assert: Returns True indicating success
        """
        # Arrange
        document_id = str(uuid.uuid4())
        mock_document_repo.delete.return_value = True

        # Act
        result = mock_document_repo.delete(document_id)

        # Assert
        assert result is True
        mock_document_repo.delete.assert_called_once_with(document_id)

    def test_list_by_collection(
        self, mock_document_repo: MagicMock, sample_documents: list[Document]
    ) -> None:
        """Test listing documents by collection.

        Arrange: Set up mock to return list of documents
        Act: Call list_by_collection with collection_id
        Assert: Returns documents in that collection
        """
        # Arrange
        collection_id = sample_documents[0].collection_id
        mock_document_repo.list_by_collection.return_value = sample_documents

        # Act
        result = mock_document_repo.list_by_collection(collection_id)

        # Assert
        assert len(result) == 3
        assert all(d.collection_id == collection_id for d in result)
        mock_document_repo.list_by_collection.assert_called_once_with(collection_id)

    def test_delete_by_collection(self, mock_document_repo: MagicMock) -> None:
        """Test deleting all documents in a collection.

        Arrange: Set up mock to return count of deleted documents
        Act: Call delete_by_collection with collection_id
        Assert: Returns the count of deleted documents
        """
        # Arrange
        collection_id = str(uuid.uuid4())
        mock_document_repo.delete_by_collection.return_value = 5

        # Act
        result = mock_document_repo.delete_by_collection(collection_id)

        # Assert
        assert result == 5
        mock_document_repo.delete_by_collection.assert_called_once_with(collection_id)

    def test_exists_true(self, mock_document_repo: MagicMock) -> None:
        """Test checking if a document exists.

        Arrange: Set up mock to return True
        Act: Call exists with existing path
        Assert: Returns True
        """
        # Arrange
        mock_document_repo.exists.return_value = True

        # Act
        result = mock_document_repo.exists("/path/to/doc.md", "collection-id")

        # Assert
        assert result is True

    def test_get_checksum(self, mock_document_repo: MagicMock) -> None:
        """Test retrieving document checksum.

        Arrange: Set up mock to return checksum
        Act: Call get_checksum with document ID
        Assert: Returns the checksum
        """
        # Arrange
        document_id = str(uuid.uuid4())
        mock_document_repo.get_checksum.return_value = "abc123"

        # Act
        result = mock_document_repo.get_checksum(document_id)

        # Assert
        assert result == "abc123"
        mock_document_repo.get_checksum.assert_called_once_with(document_id)

    def test_get_chunks(
        self, mock_document_repo: MagicMock, sample_chunks: list[DocumentChunk]
    ) -> None:
        """Test retrieving document chunks.

        Arrange: Set up mock to return list of chunks
        Act: Call get_chunks with document ID
        Assert: Returns the chunks
        """
        # Arrange
        document_id = sample_chunks[0].document_id
        mock_document_repo.get_chunks.return_value = sample_chunks

        # Act
        result = mock_document_repo.get_chunks(document_id)

        # Assert
        assert len(result) == 3
        assert all(isinstance(c, DocumentChunk) for c in result)
        mock_document_repo.get_chunks.assert_called_once_with(document_id)

    def test_save_chunks(
        self, mock_document_repo: MagicMock, sample_chunks: list[DocumentChunk]
    ) -> None:
        """Test saving document chunks.

        Arrange: Set up mock to return saved chunks
        Act: Call save_chunks with document ID and chunks
        Assert: Returns the saved chunks
        """
        # Arrange
        document_id = sample_chunks[0].document_id
        mock_document_repo.save_chunks.return_value = sample_chunks

        # Act
        result = mock_document_repo.save_chunks(document_id, sample_chunks)

        # Assert
        assert len(result) == 3
        mock_document_repo.save_chunks.assert_called_once_with(document_id, sample_chunks)


# =============================================================================
# ContextRepository Tests
# =============================================================================


class TestContextRepository:
    """Test suite for ContextRepository interface."""

    @pytest.fixture
    def mock_context_repo(self) -> MagicMock:
        """Create a mock ContextRepository."""
        mock = create_autospec(AbstractContextRepository, instance=True)
        return mock

    @pytest.fixture
    def sample_context(self) -> Context:
        """Create a sample context for testing."""
        return Context(
            id=str(uuid.uuid4()),
            target_id=str(uuid.uuid4()),
            context_type=ContextType.COLLECTION,
            content="This is context content for testing",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )

    @pytest.fixture
    def sample_contexts(self) -> list[Context]:
        """Create multiple sample contexts."""
        contexts = []
        for context_type in [ContextType.COLLECTION, ContextType.PATH, ContextType.DOCUMENT]:
            ctx = Context(
                id=str(uuid.uuid4()),
                target_id=str(uuid.uuid4()),
                context_type=context_type,
                content=f"Context for {context_type.name}",
            )
            contexts.append(ctx)
        return contexts

    def test_get_by_id_existing(
        self, mock_context_repo: MagicMock, sample_context: Context
    ) -> None:
        """Test retrieving an existing context by ID.

        Arrange: Set up mock to return a context
        Act: Call get_by_id with valid ID
        Assert: Returns the expected context
        """
        # Arrange
        mock_context_repo.get_by_id.return_value = sample_context

        # Act
        result = mock_context_repo.get_by_id(sample_context.id)

        # Assert
        assert result is not None
        assert result.id == sample_context.id
        assert result.content == sample_context.content
        mock_context_repo.get_by_id.assert_called_once_with(sample_context.id)

    def test_get_by_id_nonexistent(self, mock_context_repo: MagicMock) -> None:
        """Test retrieving a non-existent context by ID.

        Arrange: Set up mock to return None
        Act: Call get_by_id with invalid ID
        Assert: Returns None
        """
        # Arrange
        mock_context_repo.get_by_id.return_value = None

        # Act
        result = mock_context_repo.get_by_id("nonexistent-id")

        # Assert
        assert result is None

    def test_get_by_target_existing(
        self, mock_context_repo: MagicMock, sample_context: Context
    ) -> None:
        """Test retrieving context by target ID and type.

        Arrange: Set up mock to return a context
        Act: Call get_by_target with valid target_id and context_type
        Assert: Returns the expected context
        """
        # Arrange
        mock_context_repo.get_by_target.return_value = sample_context

        # Act
        result = mock_context_repo.get_by_target(
            sample_context.target_id,
            ContextType.COLLECTION,
        )

        # Assert
        assert result is not None
        assert result.target_id == sample_context.target_id
        mock_context_repo.get_by_target.assert_called_once_with(
            sample_context.target_id,
            ContextType.COLLECTION,
        )

    def test_create_context(self, mock_context_repo: MagicMock, sample_context: Context) -> None:
        """Test creating a new context.

        Arrange: Set up mock to return the created context
        Act: Call create with a new context
        Assert: Returns the created context
        """
        # Arrange
        mock_context_repo.create.return_value = sample_context

        # Act
        result = mock_context_repo.create(sample_context)

        # Assert
        assert result is not None
        assert result.id == sample_context.id
        mock_context_repo.create.assert_called_once_with(sample_context)

    def test_update_context(self, mock_context_repo: MagicMock, sample_context: Context) -> None:
        """Test updating an existing context.

        Arrange: Set up mock to return updated context
        Act: Call update with modified context
        Assert: Returns the updated context
        """
        # Arrange
        sample_context.content = "Updated context content"
        mock_context_repo.update.return_value = sample_context

        # Act
        result = mock_context_repo.update(sample_context)

        # Assert
        assert result is not None
        assert result.content == "Updated context content"
        mock_context_repo.update.assert_called_once_with(sample_context)

    def test_delete_context(self, mock_context_repo: MagicMock) -> None:
        """Test deleting a context.

        Arrange: Set up mock to return True
        Act: Call delete with context ID
        Assert: Returns True indicating success
        """
        # Arrange
        context_id = str(uuid.uuid4())
        mock_context_repo.delete.return_value = True

        # Act
        result = mock_context_repo.delete(context_id)

        # Assert
        assert result is True
        mock_context_repo.delete.assert_called_once_with(context_id)

    def test_list_by_type(
        self, mock_context_repo: MagicMock, sample_contexts: list[Context]
    ) -> None:
        """Test listing contexts by type.

        Arrange: Set up mock to return filtered contexts
        Act: Call list_by_type with context_type
        Assert: Returns contexts of that type
        """
        # Arrange
        collection_contexts = [
            c for c in sample_contexts if c.context_type == ContextType.COLLECTION
        ]
        mock_context_repo.list_by_type.return_value = collection_contexts

        # Act
        result = mock_context_repo.list_by_type(ContextType.COLLECTION)

        # Assert
        assert len(result) == 1
        assert all(c.context_type == ContextType.COLLECTION for c in result)
        mock_context_repo.list_by_type.assert_called_once_with(ContextType.COLLECTION)

    def test_list_all_contexts(
        self, mock_context_repo: MagicMock, sample_contexts: list[Context]
    ) -> None:
        """Test listing all contexts.

        Arrange: Set up mock to return all contexts
        Act: Call list_all
        Assert: Returns all contexts
        """
        # Arrange
        mock_context_repo.list_all.return_value = sample_contexts

        # Act
        result = mock_context_repo.list_all()

        # Assert
        assert len(result) == 3
        mock_context_repo.list_all.assert_called_once()

    def test_delete_by_target(self, mock_context_repo: MagicMock) -> None:
        """Test deleting all contexts for a target.

        Arrange: Set up mock to return True
        Act: Call delete_by_target with target_id
        Assert: Returns True indicating success
        """
        # Arrange
        target_id = str(uuid.uuid4())
        mock_context_repo.delete_by_target.return_value = True

        # Act
        result = mock_context_repo.delete_by_target(target_id)

        # Assert
        assert result is True
        mock_context_repo.delete_by_target.assert_called_once_with(target_id)


# =============================================================================
# SearchRepository Tests
# =============================================================================


class TestSearchRepository:
    """Test suite for SearchRepository interface."""

    @pytest.fixture
    def mock_search_repo(self) -> MagicMock:
        """Create a mock SearchRepository."""
        mock = create_autospec(SearchRepository, instance=True)
        return mock

    def test_search_fts(self, mock_search_repo: MagicMock) -> None:
        """Test full-text search.

        Arrange: Set up mock to return search results
        Act: Call search_fts with query
        Assert: Returns list of (document_id, score) tuples
        """
        # Arrange
        expected_results = [
            ("doc-1", 0.95),
            ("doc-2", 0.87),
            ("doc-3", 0.82),
        ]
        mock_search_repo.search_fts.return_value = expected_results

        # Act
        result = mock_search_repo.search_fts(
            query="test query",
            collection_ids=None,
            limit=10,
            offset=0,
        )

        # Assert
        assert len(result) == 3
        assert all(isinstance(r, tuple) and len(r) == 2 for r in result)
        mock_search_repo.search_fts.assert_called_once()

    def test_search_vector(self, mock_search_repo: MagicMock) -> None:
        """Test vector search.

        Arrange: Set up mock to return search results
        Act: Call search_vector with embedding
        Assert: Returns list of (document_id, score) tuples
        """
        # Arrange
        embedding = [0.1, 0.2, 0.3, 0.4, 0.5]
        expected_results = [
            ("doc-1", 0.92),
            ("doc-3", 0.88),
            ("doc-2", 0.85),
        ]
        mock_search_repo.search_vector.return_value = expected_results

        # Act
        result = mock_search_repo.search_vector(
            embedding=embedding,
            collection_ids=None,
            limit=10,
            offset=0,
        )

        # Assert
        assert len(result) == 3
        mock_search_repo.search_vector.assert_called_once()

    def test_get_document_for_result(self, mock_search_repo: MagicMock) -> None:
        """Test getting document details for search result.

        Arrange: Set up mock to return document data
        Act: Call get_document_for_result with document ID
        Assert: Returns document details
        """
        # Arrange
        doc_data = {
            "path": "/path/to/doc.md",
            "title": "Test Document",
            "content": "Document content",
            "metadata": {"author": "Test"},
        }
        mock_search_repo.get_document_for_result.return_value = doc_data

        # Act
        result = mock_search_repo.get_document_for_result("doc-1")

        # Assert
        assert result is not None
        assert result["path"] == "/path/to/doc.md"
        mock_search_repo.get_document_for_result.assert_called_once_with("doc-1")

    def test_get_highlights(self, mock_search_repo: MagicMock) -> None:
        """Test getting highlighted snippets.

        Arrange: Set up mock to return highlights
        Act: Call get_highlights with document ID and query
        Assert: Returns list of highlighted snippets
        """
        # Arrange
        highlights = ["matched snippet 1", "matched snippet 2"]
        mock_search_repo.get_highlights.return_value = highlights

        # Act
        result = mock_search_repo.get_highlights("doc-1", "test query")

        # Assert
        assert len(result) == 2
        mock_search_repo.get_highlights.assert_called_once_with("doc-1", "test query")


# =============================================================================
# In-Memory Repository Implementation Tests
# =============================================================================


class InMemoryCollectionRepository:
    """In-memory implementation of CollectionRepository for testing."""

    def __init__(self) -> None:
        self._collections: dict[str, Collection] = {}
        self._name_index: dict[str, str] = {}  # name -> id

    def get_by_id(self, entity_id: str) -> Collection | None:
        return self._collections.get(entity_id)

    def get_by_name(self, name: str) -> Collection | None:
        collection_id = self._name_index.get(name)
        if collection_id:
            return self._collections.get(collection_id)
        return None

    def list_all(self) -> list[Collection]:
        return list(self._collections.values())

    def create(self, entity: Collection) -> Collection:
        self._collections[entity.id] = entity
        self._name_index[entity.name] = entity.id
        return entity

    def update(self, entity: Collection) -> Collection:
        # Update name index if name changed
        old_collection = self._collections.get(entity.id)
        if old_collection and old_collection.name != entity.name:
            del self._name_index[old_collection.name]
            self._name_index[entity.name] = entity.id

        entity.updated_at = datetime.utcnow()
        self._collections[entity.id] = entity
        return entity

    def delete(self, entity_id: str) -> bool:
        collection = self._collections.pop(entity_id, None)
        if collection:
            del self._name_index[collection.name]
            return True
        return False

    def exists(self, name: str) -> bool:
        return name in self._name_index


class TestInMemoryCollectionRepository:
    """Test suite for in-memory collection repository implementation."""

    @pytest.fixture
    def repo(self) -> InMemoryCollectionRepository:
        """Create an empty in-memory repository."""
        return InMemoryCollectionRepository()

    @pytest.fixture
    def sample_collection(self) -> Collection:
        """Create a sample collection."""
        return Collection(
            id=str(uuid.uuid4()),
            name="test-collection",
            description="Test description",
            paths=["/path/to/docs"],
        )

    def test_create_and_get(
        self, repo: InMemoryCollectionRepository, sample_collection: Collection
    ) -> None:
        """Test creating and retrieving a collection."""
        # Act
        created = repo.create(sample_collection)
        retrieved = repo.get_by_id(sample_collection.id)

        # Assert
        assert created == sample_collection
        assert retrieved is not None
        assert retrieved.id == sample_collection.id
        assert retrieved.name == sample_collection.name

    def test_get_by_name(
        self, repo: InMemoryCollectionRepository, sample_collection: Collection
    ) -> None:
        """Test retrieving by name."""
        # Arrange
        repo.create(sample_collection)

        # Act
        result = repo.get_by_name("test-collection")

        # Assert
        assert result is not None
        assert result.name == "test-collection"

    def test_update(
        self, repo: InMemoryCollectionRepository, sample_collection: Collection
    ) -> None:
        """Test updating a collection."""
        # Arrange
        repo.create(sample_collection)

        # Act
        sample_collection.description = "Updated description"
        updated = repo.update(sample_collection)
        retrieved = repo.get_by_id(sample_collection.id)

        # Assert
        assert updated.description == "Updated description"
        assert retrieved.description == "Updated description"

    def test_delete(
        self, repo: InMemoryCollectionRepository, sample_collection: Collection
    ) -> None:
        """Test deleting a collection."""
        # Arrange
        repo.create(sample_collection)

        # Act
        deleted = repo.delete(sample_collection.id)
        retrieved = repo.get_by_id(sample_collection.id)

        # Assert
        assert deleted is True
        assert retrieved is None

    def test_exists(
        self, repo: InMemoryCollectionRepository, sample_collection: Collection
    ) -> None:
        """Test exists check."""
        # Act & Assert - before creation
        assert repo.exists("test-collection") is False

        # Arrange
        repo.create(sample_collection)

        # Act & Assert - after creation
        assert repo.exists("test-collection") is True
        assert repo.exists("other-collection") is False

    def test_list_all(self, repo: InMemoryCollectionRepository) -> None:
        """Test listing all collections."""
        # Arrange
        for i in range(3):
            collection = Collection(
                id=str(uuid.uuid4()),
                name=f"collection-{i}",
                description=f"Description {i}",
            )
            repo.create(collection)

        # Act
        result = repo.list_all()

        # Assert
        assert len(result) == 3

    def test_delete_updates_name_index(
        self, repo: InMemoryCollectionRepository, sample_collection: Collection
    ) -> None:
        """Test that deleting removes from name index."""
        # Arrange
        repo.create(sample_collection)

        # Act
        repo.delete(sample_collection.id)

        # Assert
        assert repo.exists("test-collection") is False
        assert repo.get_by_name("test-collection") is None
