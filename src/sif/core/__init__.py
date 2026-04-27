"""Core domain entities and business logic for SIF.

This package contains the core domain models and business logic
that define the fundamental concepts of the SIF system.
"""

from sif.core.collection import Collection, CollectionManager
from sif.core.context import Context, ContextManager, ContextType
from sif.core.document import Document, DocumentChunk, DocumentMetadata


__all__ = [
    "Collection",
    "CollectionManager",
    "Context",
    "ContextManager",
    "ContextType",
    "Document",
    "DocumentChunk",
    "DocumentMetadata",
]
