"""Shared pytest fixtures for DocSift tests."""

import hashlib
import tempfile
import uuid
from datetime import datetime
from pathlib import Path
from typing import Generator
from unittest.mock import MagicMock

import pytest

# Add src to path for imports
import sys

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from docsift.core.collection import Collection
from docsift.core.document import Document, DocumentChunk, DocumentMetadata
from docsift.core.context import Context, ContextType
from docsift.database.connection import DatabaseConnection
from docsift.models.search import SearchOptions, SearchResult, SearchType


# =============================================================================
# Path Fixtures
# =============================================================================


@pytest.fixture
def temp_dir() -> Generator[Path, None, None]:
    """Provide a temporary directory for tests."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        yield Path(tmp_dir)


@pytest.fixture
def sample_markdown_file(temp_dir: Path) -> Path:
    """Create a sample markdown file for testing."""
    file_path = temp_dir / "test_document.md"
    content = """---
title: Test Document
author: Test Author
date: 2024-01-15
tags: [test, sample]
categories: [documentation]
---

# Introduction

This is a test document for DocSift.

## Section 1

Some content here with **bold** and *italic* text.

```python
def hello():
    return "world"
```

## Section 2

More content with a [link](https://example.com).

- List item 1
- List item 2
- List item 3
"""
    file_path.write_text(content, encoding="utf-8")
    return file_path


@pytest.fixture
def sample_markdown_content() -> str:
    """Return sample markdown content."""
    return """---
title: Sample Document
author: Sample Author
---

# Sample Title

This is sample content for testing.

## Subsection

More details here.
"""


# =============================================================================
# Database Fixtures
# =============================================================================


@pytest.fixture
def temp_db_path(temp_dir: Path) -> Path:
    """Provide a temporary database path."""
    return temp_dir / "test.db"


@pytest.fixture
def db_connection(temp_db_path: Path) -> Generator[DatabaseConnection, None, None]:
    """Provide a database connection."""
    conn = DatabaseConnection(temp_db_path)
    yield conn


@pytest.fixture
def temp_db(temp_db_path: Path) -> Generator[DatabaseConnection, None, None]:
    """Provide a temporary database with schema initialized."""
    conn = DatabaseConnection(temp_db_path)

    # Initialize schema
    with conn.connect() as db:
        # Collections table
        db.execute("""
            CREATE TABLE IF NOT EXISTS collections (
                id TEXT PRIMARY KEY,
                name TEXT UNIQUE NOT NULL,
                description TEXT,
                paths TEXT,
                document_count INTEGER DEFAULT 0,
                chunk_count INTEGER DEFAULT 0,
                metadata TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_indexed_at TIMESTAMP
            )
        """)

        # Documents table
        db.execute("""
            CREATE TABLE IF NOT EXISTS documents (
                id TEXT PRIMARY KEY,
                collection_id TEXT NOT NULL,
                path TEXT NOT NULL,
                content TEXT,
                checksum TEXT,
                file_size INTEGER,
                title TEXT,
                metadata TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                indexed_at TIMESTAMP,
                FOREIGN KEY (collection_id) REFERENCES collections(id) ON DELETE CASCADE,
                UNIQUE(collection_id, path)
            )
        """)

        # Chunks table
        db.execute("""
            CREATE TABLE IF NOT EXISTS chunks (
                id TEXT PRIMARY KEY,
                document_id TEXT NOT NULL,
                content TEXT,
                start_line INTEGER,
                end_line INTEGER,
                token_count INTEGER,
                embedding_id TEXT,
                FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE
            )
        """)

        # Contexts table
        db.execute("""
            CREATE TABLE IF NOT EXISTS contexts (
                id TEXT PRIMARY KEY,
                target_id TEXT NOT NULL,
                context_type TEXT NOT NULL,
                content TEXT,
                metadata TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        db.commit()

    yield conn


# =============================================================================
# Entity Fixtures
# =============================================================================


@pytest.fixture
def sample_collection_id() -> str:
    """Return a sample collection ID."""
    return str(uuid.uuid4())


@pytest.fixture
def sample_document_id() -> str:
    """Return a sample document ID."""
    return str(uuid.uuid4())


@pytest.fixture
def sample_chunk_id() -> str:
    """Return a sample chunk ID."""
    return str(uuid.uuid4())


@pytest.fixture
def sample_collection(sample_collection_id: str) -> Collection:
    """Return a sample collection."""
    return Collection(
        id=sample_collection_id,
        name="test-collection",
        description="A test collection",
        paths=["/path/to/docs"],
        document_count=5,
        chunk_count=20,
        metadata={"key": "value"},
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
        last_indexed_at=datetime.utcnow(),
    )


@pytest.fixture
def sample_collections() -> list[Collection]:
    """Return a list of sample collections."""
    return [
        Collection(
            id=str(uuid.uuid4()),
            name="collection-1",
            description="First test collection",
            paths=["/path/one"],
            document_count=10,
            chunk_count=40,
        ),
        Collection(
            id=str(uuid.uuid4()),
            name="collection-2",
            description="Second test collection",
            paths=["/path/two"],
            document_count=20,
            chunk_count=80,
        ),
    ]


@pytest.fixture
def sample_document_metadata() -> DocumentMetadata:
    """Return sample document metadata."""
    return DocumentMetadata(
        title="Test Document",
        author="Test Author",
        date=datetime(2024, 1, 15),
        tags=["test", "sample"],
        categories=["documentation"],
        custom={"version": "1.0"},
    )


@pytest.fixture
def sample_document(
    sample_document_id: str,
    sample_collection_id: str,
    sample_document_metadata: DocumentMetadata,
) -> Document:
    """Return a sample document."""
    content = "This is test document content.\n\nIt has multiple lines."
    checksum = hashlib.sha256(content.encode()).hexdigest()

    return Document(
        id=sample_document_id,
        collection_id=sample_collection_id,
        path="/path/to/document.md",
        content=content,
        checksum=checksum,
        file_size=len(content),
        metadata=sample_document_metadata,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
        indexed_at=datetime.utcnow(),
    )


@pytest.fixture
def sample_documents(
    sample_collection_id: str,
    sample_document_metadata: DocumentMetadata,
) -> list[Document]:
    """Return a list of sample documents."""
    documents = []
    for i in range(3):
        content = f"Content for document {i + 1}"
        checksum = hashlib.sha256(content.encode()).hexdigest()

        doc = Document(
            id=str(uuid.uuid4()),
            collection_id=sample_collection_id,
            path=f"/path/to/document_{i + 1}.md",
            content=content,
            checksum=checksum,
            file_size=len(content),
            metadata=DocumentMetadata(
                title=f"Document {i + 1}",
                author="Test Author",
                tags=["test"],
            ),
        )
        documents.append(doc)

    return documents


@pytest.fixture
def sample_chunk(sample_chunk_id: str, sample_document_id: str) -> DocumentChunk:
    """Return a sample document chunk."""
    return DocumentChunk(
        id=sample_chunk_id,
        document_id=sample_document_id,
        content="This is a chunk of text.",
        start_line=0,
        end_line=5,
        token_count=10,
        embedding_id=None,
        embedding=None,
    )


@pytest.fixture
def sample_chunks(sample_document_id: str) -> list[DocumentChunk]:
    """Return a list of sample chunks."""
    return [
        DocumentChunk(
            id=str(uuid.uuid4()),
            document_id=sample_document_id,
            content=f"Chunk {i} content",
            start_line=i * 5,
            end_line=i * 5 + 4,
            token_count=10,
        )
        for i in range(5)
    ]


@pytest.fixture
def sample_context() -> Context:
    """Return a sample context."""
    return Context(
        id=str(uuid.uuid4()),
        target_id=str(uuid.uuid4()),
        context_type=ContextType.COLLECTION,
        content="Context content for testing",
        metadata={"source": "test"},
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )


# =============================================================================
# Search Fixtures
# =============================================================================


@pytest.fixture
def sample_search_options() -> SearchOptions:
    """Return sample search options."""
    return SearchOptions(
        limit=10,
        offset=0,
        threshold=0.0,
        include_chunks=True,
        include_metadata=True,
        highlight_matches=True,
        bm25_k1=1.5,
        bm25_b=0.75,
        vector_weight=0.7,
        bm25_weight=0.3,
        rrf_k=60,
    )


@pytest.fixture
def sample_search_result() -> SearchResult:
    """Return a sample search result."""
    return SearchResult(
        document_id=str(uuid.uuid4()),
        document_path="/path/to/result.md",
        document_title="Test Result",
        score=0.95,
        bm25_score=0.90,
        vector_score=0.85,
        content_preview="This is a preview of the result...",
        matched_chunks=[],
        highlights=["matched term"],
        metadata={"author": "Test"},
    )


@pytest.fixture
def sample_search_results() -> list[SearchResult]:
    """Return a list of sample search results."""
    return [
        SearchResult(
            document_id=str(uuid.uuid4()),
            document_path=f"/path/to/result_{i}.md",
            document_title=f"Result {i}",
            score=0.95 - (i * 0.05),
            bm25_score=0.90 - (i * 0.03),
            vector_score=0.85 - (i * 0.04),
            content_preview=f"Preview of result {i}...",
        )
        for i in range(5)
    ]


# =============================================================================
# Mock Fixtures
# =============================================================================


@pytest.fixture
def mock_embedder() -> MagicMock:
    """Return a mock embedding model."""
    mock = MagicMock()
    mock.model_id = "test-model"
    mock.embedding_dim = 384
    mock.max_tokens = 512
    mock.loaded = True

    # Mock embed method to return deterministic embeddings
    def mock_embed(texts: list[str], normalize: bool = True) -> list[list[float]]:
        import random

        return [[random.Random(hash(t) & 0xFFFFFFFF).random() for _ in range(384)] for t in texts]

    def mock_embed_single(text: str, normalize: bool = True) -> list[float]:
        return mock_embed([text])[0]

    mock.embed.side_effect = mock_embed
    mock.embed_single.side_effect = mock_embed_single
    mock.count_tokens.return_value = 10

    return mock


@pytest.fixture
def mock_repository() -> MagicMock:
    """Return a mock repository."""
    mock = MagicMock()
    mock.get_by_id.return_value = None
    mock.create.return_value = None
    mock.update.return_value = None
    mock.delete.return_value = True
    return mock


@pytest.fixture
def mock_search_repository() -> MagicMock:
    """Return a mock search repository."""
    mock = MagicMock()
    mock.search_fts.return_value = [
        ("doc-1", 0.95),
        ("doc-2", 0.87),
        ("doc-3", 0.82),
    ]
    mock.search_vector.return_value = [
        ("doc-1", 0.92),
        ("doc-3", 0.88),
        ("doc-2", 0.85),
    ]
    mock.get_document_for_result.return_value = {
        "path": "/path/to/doc.md",
        "title": "Test Document",
        "content": "Document content for testing",
        "metadata": {"author": "Test"},
    }
    mock.get_highlights.return_value = ["matched snippet 1", "matched snippet 2"]
    return mock


@pytest.fixture
def mock_embedding_manager() -> MagicMock:
    """Return a mock embedding manager."""
    mock = MagicMock()

    def mock_embed(texts: list[str]) -> list[list[float]]:
        import random

        return [[random.Random(hash(t) & 0xFFFFFFFF).random() for _ in range(384)] for t in texts]

    def mock_embed_single(text: str) -> list[float]:
        return mock_embed([text])[0]

    mock.embed.side_effect = mock_embed
    mock.embed_single.side_effect = mock_embed_single
    return mock


# =============================================================================
# Async Fixtures
# =============================================================================


@pytest.fixture
def event_loop():
    """Create an instance of the default event loop for async tests."""
    import asyncio

    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


# =============================================================================
# Helper Functions
# =============================================================================


def create_test_document(
    collection_id: str,
    path: str = "/test/path.md",
    content: str = "Test content",
) -> Document:
    """Helper to create a test document."""
    checksum = hashlib.sha256(content.encode()).hexdigest()
    return Document(
        id=str(uuid.uuid4()),
        collection_id=collection_id,
        path=path,
        content=content,
        checksum=checksum,
        file_size=len(content),
    )


def create_test_collection(name: str = "test-collection") -> Collection:
    """Helper to create a test collection."""
    return Collection(
        id=str(uuid.uuid4()),
        name=name,
        description=f"Test collection: {name}",
        paths=["/test/path"],
    )


# =============================================================================
# Docs Test Fixtures
# =============================================================================


@pytest.fixture
def docs_test_db(tmp_path: Path) -> Generator[Path, None, None]:
    """Create a temporary database with minimal test data for docs tests."""
    from docsift.database.database import Database

    db_path = tmp_path / "docs_test.db"
    db = Database(db_path)
    db.init_schema()

    from docsift.database.repositories import CollectionRepository, DocumentRepository

    with db.transaction() as conn:
        coll_repo = CollectionRepository(conn)
        doc_repo = DocumentRepository(conn)

        collection = Collection(
            name="test-docs",
            path=str(tmp_path / "docs"),
            description="Test collection for docs validation",
            include_by_default=True,
        )
        coll_repo.create(collection)

        # Create test document files
        docs_dir = tmp_path / "docs"
        docs_dir.mkdir()
        (docs_dir / "python.md").write_text(
            "# Python Decorators\n\nDecorators are a powerful feature."
        )
        (docs_dir / "machine-learning.md").write_text(
            "# Machine Learning\n\nNeural networks are..."
        )

        # Insert documents
        doc1 = Document(
            path=str(docs_dir / "python.md"),
            collection_id=collection.id,
            content="# Python Decorators\n\nDecorators are a powerful feature.",
            title="Python Decorators",
        )
        doc2 = Document(
            path=str(docs_dir / "machine-learning.md"),
            collection_id=collection.id,
            content="# Machine Learning\n\nNeural networks are...",
            title="Machine Learning",
        )
        doc_repo.create(doc1)
        doc_repo.create(doc2)

    yield db_path

    db.close()


@pytest.fixture
def docs_runner(docs_test_db: Path) -> Generator["CliRunner", None, None]:
    """Provide a CliRunner with docs test database pre-configured."""
    from click.testing import CliRunner

    runner = CliRunner(env={"DOCSIFT_DB_PATH": str(docs_test_db)})
    yield runner
