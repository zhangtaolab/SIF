"""Test data factories using factory-boy pattern."""

import hashlib
import uuid
from datetime import datetime
from typing import Any

from sif.core.collection import Collection
from sif.core.document import Document, DocumentChunk, DocumentMetadata
from sif.core.context import Context, ContextType
from sif.models.search import SearchOptions, SearchResult, SearchType


class CollectionFactory:
    """Factory for creating test collections."""

    _counter = 0

    @classmethod
    def create(
        cls,
        id: str | None = None,
        name: str | None = None,
        description: str | None = None,
        paths: list[str] | None = None,
        document_count: int = 0,
        chunk_count: int = 0,
        metadata: dict[str, Any] | None = None,
    ) -> Collection:
        """Create a test collection."""
        cls._counter += 1

        return Collection(
            id=id or str(uuid.uuid4()),
            name=name or f"test-collection-{cls._counter}",
            description=description or f"Test collection {cls._counter}",
            paths=paths or [f"/test/path/{cls._counter}"],
            document_count=document_count,
            chunk_count=chunk_count,
            metadata=metadata or {},
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )

    @classmethod
    def create_batch(cls, count: int, **kwargs) -> list[Collection]:
        """Create multiple test collections."""
        return [cls.create(**kwargs) for _ in range(count)]


class DocumentMetadataFactory:
    """Factory for creating test document metadata."""

    _counter = 0

    @classmethod
    def create(
        cls,
        title: str | None = None,
        author: str | None = None,
        date: datetime | None = None,
        tags: list[str] | None = None,
        categories: list[str] | None = None,
        custom: dict[str, Any] | None = None,
    ) -> DocumentMetadata:
        """Create test document metadata."""
        cls._counter += 1

        return DocumentMetadata(
            title=title or f"Test Document {cls._counter}",
            author=author or "Test Author",
            date=date or datetime(2024, 1, 15),
            tags=tags or ["test", "sample"],
            categories=categories or ["documentation"],
            custom=custom or {"version": "1.0"},
        )


class DocumentFactory:
    """Factory for creating test documents."""

    _counter = 0

    @classmethod
    def create(
        cls,
        id: str | None = None,
        collection_id: str | None = None,
        path: str | None = None,
        content: str | None = None,
        metadata: DocumentMetadata | None = None,
        with_chunks: bool = False,
        chunk_count: int = 3,
    ) -> Document:
        """Create a test document."""
        cls._counter += 1

        actual_content = (
            content or f"This is test document content {cls._counter}.\n\nIt has multiple lines."
        )
        checksum = hashlib.sha256(actual_content.encode()).hexdigest()

        doc = Document(
            id=id or str(uuid.uuid4()),
            collection_id=collection_id or str(uuid.uuid4()),
            path=path or f"/test/path/document_{cls._counter}.md",
            content=actual_content,
            checksum=checksum,
            file_size=len(actual_content),
            metadata=metadata or DocumentMetadataFactory.create(),
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )

        if with_chunks:
            doc.chunks = DocumentChunkFactory.create_batch(
                chunk_count,
                document_id=doc.id,
            )

        return doc

    @classmethod
    def create_batch(
        cls,
        count: int,
        collection_id: str | None = None,
        **kwargs,
    ) -> list[Document]:
        """Create multiple test documents."""
        col_id = collection_id or str(uuid.uuid4())
        return [cls.create(collection_id=col_id, **kwargs) for _ in range(count)]


class DocumentChunkFactory:
    """Factory for creating test document chunks."""

    _counter = 0

    @classmethod
    def create(
        cls,
        id: str | None = None,
        document_id: str | None = None,
        content: str | None = None,
        start_line: int | None = None,
        end_line: int | None = None,
        token_count: int | None = None,
        embedding: list[float] | None = None,
    ) -> DocumentChunk:
        """Create a test document chunk."""
        cls._counter += 1

        actual_start = start_line if start_line is not None else (cls._counter - 1) * 5
        actual_end = end_line if end_line is not None else actual_start + 4

        return DocumentChunk(
            id=id or str(uuid.uuid4()),
            document_id=document_id or str(uuid.uuid4()),
            content=content or f"Chunk {cls._counter} content for testing.",
            start_line=actual_start,
            end_line=actual_end,
            token_count=token_count or 10,
            embedding=embedding,
        )

    @classmethod
    def create_batch(
        cls,
        count: int,
        document_id: str | None = None,
        **kwargs,
    ) -> list[DocumentChunk]:
        """Create multiple test chunks."""
        doc_id = document_id or str(uuid.uuid4())
        return [cls.create(document_id=doc_id, **kwargs) for _ in range(count)]


class ContextFactory:
    """Factory for creating test contexts."""

    _counter = 0

    @classmethod
    def create(
        cls,
        id: str | None = None,
        target_id: str | None = None,
        context_type: ContextType = ContextType.COLLECTION,
        content: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> Context:
        """Create a test context."""
        cls._counter += 1

        return Context(
            id=id or str(uuid.uuid4()),
            target_id=target_id or str(uuid.uuid4()),
            context_type=context_type,
            content=content or f"Context content {cls._counter} for testing",
            metadata=metadata or {"source": "test"},
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )

    @classmethod
    def create_batch(cls, count: int, **kwargs) -> list[Context]:
        """Create multiple test contexts."""
        return [cls.create(**kwargs) for _ in range(count)]


class SearchOptionsFactory:
    """Factory for creating test search options."""

    @classmethod
    def create(
        cls,
        limit: int = 10,
        offset: int = 0,
        threshold: float = 0.0,
        include_chunks: bool = True,
        include_metadata: bool = True,
        highlight_matches: bool = True,
        search_type: SearchType = SearchType.HYBRID,
        **kwargs,
    ) -> SearchOptions:
        """Create test search options."""
        options = SearchOptions(
            limit=limit,
            offset=offset,
            threshold=threshold,
            include_chunks=include_chunks,
            include_metadata=include_metadata,
            highlight_matches=highlight_matches,
            **kwargs,
        )
        return options

    @classmethod
    def bm25(cls, **kwargs) -> SearchOptions:
        """Create BM25 search options."""
        return cls.create(search_type=SearchType.BM25, **kwargs)

    @classmethod
    def vector(cls, **kwargs) -> SearchOptions:
        """Create vector search options."""
        return cls.create(search_type=SearchType.VECTOR, **kwargs)

    @classmethod
    def hybrid(cls, **kwargs) -> SearchOptions:
        """Create hybrid search options."""
        return cls.create(search_type=SearchType.HYBRID, **kwargs)


class SearchResultFactory:
    """Factory for creating test search results."""

    _counter = 0

    @classmethod
    def create(
        cls,
        document_id: str | None = None,
        document_path: str | None = None,
        document_title: str | None = None,
        score: float = 0.95,
        bm25_score: float | None = None,
        vector_score: float | None = None,
        content_preview: str | None = None,
        highlights: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> SearchResult:
        """Create a test search result."""
        cls._counter += 1

        return SearchResult(
            document_id=document_id or str(uuid.uuid4()),
            document_path=document_path or f"/test/result_{cls._counter}.md",
            document_title=document_title or f"Test Result {cls._counter}",
            score=score,
            bm25_score=bm25_score or score * 0.95,
            vector_score=vector_score or score * 0.90,
            content_preview=content_preview or f"Preview of result {cls._counter}...",
            matched_chunks=[],
            highlights=highlights or ["matched term"],
            metadata=metadata or {"author": "Test"},
        )

    @classmethod
    def create_batch(cls, count: int, **kwargs) -> list[SearchResult]:
        """Create multiple test search results with decreasing scores."""
        results = []
        base_score = kwargs.get("score", 0.95)

        for i in range(count):
            result_kwargs = kwargs.copy()
            result_kwargs["score"] = base_score - (i * 0.05)
            results.append(cls.create(**result_kwargs))

        return results


# =============================================================================
# Predefined Test Data
# =============================================================================

SAMPLE_MARKDOWN_CONTENTS = [
    """---
title: Getting Started
author: Doc Team
date: 2024-01-01
tags: [tutorial, beginner]
---

# Getting Started

Welcome to the getting started guide.

## Installation

Install the package using pip.

## Configuration

Edit the config file.
""",
    """---
title: API Reference
author: Dev Team
tags: [api, reference]
---

# API Reference

Complete API documentation.

## Endpoints

### GET /api/v1/users

Returns a list of users.

### POST /api/v1/users

Creates a new user.
""",
    """---
title: Troubleshooting
author: Support Team
tags: [help, support]
---

# Troubleshooting

Common issues and solutions.

## Connection Issues

Check your network settings.

## Performance Problems

Optimize your queries.
""",
]

SAMPLE_SEARCH_QUERIES = [
    "getting started",
    "api reference",
    "troubleshooting",
    "installation guide",
    "configuration options",
]


def get_sample_embedding(dim: int = 384) -> list[float]:
    """Get a sample embedding vector."""
    import random

    random.seed(42)
    return [random.random() for _ in range(dim)]


def get_sample_embeddings(count: int, dim: int = 384) -> list[list[float]]:
    """Get multiple sample embedding vectors."""
    import random

    random.seed(42)
    return [[random.random() for _ in range(dim)] for _ in range(count)]
