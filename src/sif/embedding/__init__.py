"""Embedding generation and management for SIF.

This package provides embedding functionality using the Factory pattern:
- Embedding model management
- Vector generation for documents
- Model loading and caching
- Support for GGUF models via llama-cpp-python
"""

from sif.embedding.cache import EmbeddingCache
from sif.embedding.factory import EmbeddingModelFactory
from sif.embedding.manager import EmbeddingManager
from sif.embedding.model import EmbeddingModel, ModelType


__all__ = [
    "EmbeddingCache",
    "EmbeddingManager",
    "EmbeddingModel",
    "EmbeddingModelFactory",
    "ModelType",
]
