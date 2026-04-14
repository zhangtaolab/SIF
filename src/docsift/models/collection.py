"""Pydantic models for Collection operations."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, ConfigDict


class CollectionBase(BaseModel):
    """Base model for Collection data."""
    
    name: str = Field(..., min_length=1, max_length=255, description="Collection name")
    description: str | None = Field(None, description="Collection description")


class CollectionCreate(CollectionBase):
    """Model for creating a new collection."""
    
    paths: list[str] = Field(default_factory=list, description="Initial paths to include")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class CollectionUpdate(BaseModel):
    """Model for updating a collection."""
    
    name: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = None
    paths: list[str] | None = None
    metadata: dict[str, Any] | None = None


class CollectionResponse(CollectionBase):
    """Model for collection response data."""
    
    model_config = ConfigDict(from_attributes=True)
    
    id: str = Field(..., description="Unique collection ID")
    paths: list[str] = Field(default_factory=list, description="Indexed paths")
    document_count: int = Field(0, ge=0, description="Number of documents")
    chunk_count: int = Field(0, ge=0, description="Number of chunks")
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    last_indexed_at: datetime | None = Field(None, description="Last indexing timestamp")


class CollectionListResponse(BaseModel):
    """Model for listing collections."""
    
    collections: list[CollectionResponse]
    total: int = Field(..., ge=0)
