"""Embedding model interface."""

from abc import ABC, abstractmethod
from typing import Protocol

from sif.models.embedding import ModelType


class EmbeddingModel(ABC):
    """Abstract base class for embedding models.

    Implements a common interface for different embedding providers,
    allowing models to be used interchangeably.
    """

    def __init__(
        self,
        model_id: str,
        embedding_dim: int,
        max_tokens: int,
    ) -> None:
        """Initialize the embedding model."""
        self._model_id = model_id
        self._embedding_dim = embedding_dim
        self._max_tokens = max_tokens
        self._loaded = False

    @property
    def model_id(self) -> str:
        """Get the model ID."""
        return self._model_id

    @property
    def embedding_dim(self) -> int:
        """Get the embedding dimension."""
        return self._embedding_dim

    @property
    def max_tokens(self) -> int:
        """Get the maximum token count."""
        return self._max_tokens

    @property
    def loaded(self) -> bool:
        """Check if the model is loaded."""
        return self._loaded

    @abstractmethod
    def load(self) -> None:
        """Load the model into memory."""
        ...

    @abstractmethod
    def unload(self) -> None:
        """Unload the model from memory."""
        ...

    @abstractmethod
    def embed(
        self,
        texts: list[str],
        normalize: bool = True,
    ) -> list[list[float]]:
        """Generate embeddings for a list of texts.

        Args:
            texts: List of texts to embed
            normalize: Whether to normalize embeddings

        Returns:
            List of embeddings, one per input text
        """
        ...

    @abstractmethod
    def embed_single(
        self,
        text: str,
        normalize: bool = True,
    ) -> list[float]:
        """Generate embedding for a single text.

        Args:
            text: Text to embed
            normalize: Whether to normalize the embedding

        Returns:
            Embedding vector
        """
        ...

    def count_tokens(self, text: str) -> int:
        """Count tokens in a text.

        Default implementation uses a rough estimate.
        Subclasses can override for more accurate counts.
        """
        # Rough estimate: 1 token ~= 4 characters
        return len(text) // 4


class EmbeddingModelFactory(Protocol):
    """Protocol for embedding model factories.

    Implements the Factory pattern for creating embedding models.
    """

    def create_model(
        self,
        model_type: ModelType,
        model_path: str | None,
        model_name: str,
        **kwargs: dict[str, any],
    ) -> EmbeddingModel:
        """Create an embedding model instance.

        Args:
            model_type: Type of model to create
            model_path: Path to model file (for local models)
            model_name: Model name or identifier
            **kwargs: Additional model-specific parameters

        Returns:
            Configured embedding model instance
        """
        ...
