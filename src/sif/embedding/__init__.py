"""Embedding generation and management for DocSift.

This package provides embedding functionality using the Factory pattern:
- Embedding model management
- Vector generation for documents
- Model loading and caching
- Support for GGUF models via llama-cpp-python
"""

from docsift.embedding.manager import EmbeddingManager
from docsift.embedding.model import EmbeddingModel, ModelType
from docsift.embedding.factory import EmbeddingModelFactory
from docsift.embedding.cache import EmbeddingCache

__all__ = [
    "EmbeddingManager",
    "EmbeddingModel",
    "ModelType",
    "EmbeddingModelFactory",
    "EmbeddingCache",
]
