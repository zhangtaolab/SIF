"""Pydantic models for Document operations."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, ConfigDict


class DocumentMetadata(BaseModel):
    """Document metadata extracted from frontmatter."""

    title: str | None = None
    author: str | None = None
    date: datetime | None = None
    tags: list[str] = Field(default_factory=list)
    categories: list[str] = Field(default_factory=list)
    custom: dict[str, Any] = Field(default_factory=dict)


class DocumentBase(BaseModel):
    """Base model for Document data."""

    path: str = Field(..., description="File system path")
    content: str = Field(..., description="Document content")


class DocumentCreate(DocumentBase):
    """Model for creating a new document."""

    collection_id: str = Field(..., description="Parent collection ID")
    metadata: DocumentMetadata = Field(default_factory=DocumentMetadata)


class DocumentUpdate(BaseModel):
    """Model for updating a document."""

    content: str | None = None
    metadata: DocumentMetadata | None = None


class ChunkResponse(BaseModel):
    """Model for document chunk response."""

    model_config = ConfigDict(from_attributes=True)

    id: str = Field(..., description="Chunk ID")
    content: str = Field(..., description="Chunk content")
    start_line: int = Field(..., ge=0)
    end_line: int = Field(..., ge=0)
    token_count: int = Field(..., ge=0)
    embedding_id: str | None = None


class DocumentResponse(DocumentBase):
    """Model for document response data."""

    model_config = ConfigDict(from_attributes=True)

    id: str = Field(..., description="Unique document ID")
    collection_id: str = Field(..., description="Parent collection ID")
    metadata: DocumentMetadata = Field(default_factory=DocumentMetadata)
    chunks: list[ChunkResponse] = Field(default_factory=list)
    checksum: str = Field(..., description="Content checksum")
    file_size: int = Field(..., ge=0)
    created_at: datetime = Field(...)
    updated_at: datetime = Field(...)
    indexed_at: datetime | None = None


class DocumentSearchResult(BaseModel):
    """Model for document search result."""

    document: DocumentResponse
    score: float = Field(..., ge=0, le=1)
    matched_chunks: list[ChunkResponse] = Field(default_factory=list)
    highlights: list[str] = Field(default_factory=list)
