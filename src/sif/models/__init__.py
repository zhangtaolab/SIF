"""Pydantic models for data validation and serialization.

This package contains all Pydantic models used for:
- Request/response validation
- Configuration management
- Data serialization/deserialization
- API schema definitions
"""

from sif.models.collection import (
    CollectionCreate,
    CollectionUpdate,
    CollectionResponse,
    CollectionListResponse,
)
from sif.models.document import (
    DocumentCreate,
    DocumentUpdate,
    DocumentResponse,
    DocumentSearchResult,
    ChunkResponse,
)
from sif.models.context import (
    ContextCreate,
    ContextUpdate,
    ContextResponse,
)
from sif.models.search import (
    SearchQuery,
    SearchResult,
    SearchResponse,
    SearchOptions,
    SearchType,
)
from sif.models.embedding import (
    EmbeddingConfig,
    EmbeddingModelInfo,
    EmbeddingRequest,
    EmbeddingResponse,
)

__all__ = [
    # Collection models
    "CollectionCreate",
    "CollectionUpdate",
    "CollectionResponse",
    "CollectionListResponse",
    # Document models
    "DocumentCreate",
    "DocumentUpdate",
    "DocumentResponse",
    "DocumentSearchResult",
    "ChunkResponse",
    # Context models
    "ContextCreate",
    "ContextUpdate",
    "ContextResponse",
    # Search models
    "SearchQuery",
    "SearchResult",
    "SearchResponse",
    "SearchOptions",
    "SearchType",
    # Embedding models
    "EmbeddingConfig",
    "EmbeddingModelInfo",
    "EmbeddingRequest",
    "EmbeddingResponse",
]
