"""Pydantic models for Context operations."""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field, ConfigDict


class ContextType(str, Enum):
    """Type of context."""
    
    COLLECTION = "collection"
    PATH = "path"
    DOCUMENT = "document"
    GLOBAL = "global"


class ContextBase(BaseModel):
    """Base model for Context data."""
    
    content: str = Field(..., min_length=1, description="Context content")
    context_type: ContextType = Field(..., description="Type of context")


class ContextCreate(ContextBase):
    """Model for creating a new context."""
    
    target_id: str = Field(..., description="ID of the target (collection, path, etc.)")


class ContextUpdate(BaseModel):
    """Model for updating a context."""
    
    content: str | None = Field(None, min_length=1)


class ContextResponse(ContextBase):
    """Model for context response data."""
    
    model_config = ConfigDict(from_attributes=True)
    
    id: str = Field(..., description="Unique context ID")
    target_id: str = Field(..., description="ID of the target")
    created_at: datetime = Field(...)
    updated_at: datetime = Field(...)
