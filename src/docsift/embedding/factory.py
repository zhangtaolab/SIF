"""Embedding model factory."""

from docsift.embedding.embedder import (
    LlamaCppEmbedder,
    ModelScopeEmbedder,
    SentenceTransformerEmbedder,
)
from docsift.embedding.model import EmbeddingModel, ModelType
from docsift.utils.logging import get_logger


logger = get_logger(__name__)


class EmbeddingModelFactory:
    """Factory for creating embedding model instances."""

    def create_model(
        self,
        model_type: ModelType,
        model_path: str | None,
        model_name: str,
        **kwargs: dict[str, any],
    ) -> EmbeddingModel:
        """Create an embedding model instance."""
        if model_type == ModelType.SENTENCE_TRANSFORMERS:
            return self._create_sentence_transformers_model(model_name, **kwargs)
        if model_type == ModelType.GGUF:
            return self._create_gguf_model(model_path, **kwargs)
        if model_type == ModelType.OPENAI:
            return self._create_openai_model(model_name, **kwargs)
        if model_type == ModelType.HUGGINGFACE:
            return self._create_huggingface_model(model_name, **kwargs)
        if model_type == ModelType.MODELSCOPE:
            return self._create_modelscope_model(model_name, **kwargs)
        raise ValueError(f"Unsupported model type: {model_type}")

    def _create_gguf_model(
        self,
        model_path: str | None,
        **kwargs: dict[str, any],
    ) -> EmbeddingModel:
        """Create a GGUF model using llama-cpp-python."""
        if not model_path:
            raise ValueError("model_path is required for GGUF models")

        return LlamaCppEmbedder(
            model_path=model_path,
            n_ctx=kwargs.get("n_ctx", 2048),
            n_threads=kwargs.get("n_threads"),
            verbose=kwargs.get("verbose", False),
        )

    def _create_sentence_transformers_model(
        self,
        model_name: str,
        **kwargs: dict[str, any],
    ) -> EmbeddingModel:
        """Create a Sentence Transformers model."""
        return SentenceTransformerEmbedder(
            model_name=model_name,
            device=kwargs.get("device"),
            cache_dir=kwargs.get("cache_dir"),
        )

    def _create_openai_model(
        self,
        model_name: str,
        **kwargs: dict[str, any],
    ) -> EmbeddingModel:
        """Create an OpenAI API model."""
        raise NotImplementedError("OpenAI models not yet implemented")

    def _create_huggingface_model(
        self,
        model_name: str,
        **kwargs: dict[str, any],
    ) -> EmbeddingModel:
        """Create a HuggingFace Transformers model."""
        raise NotImplementedError("HuggingFace models not yet implemented")

    def _create_modelscope_model(
        self,
        model_name: str,
        **kwargs: dict[str, any],
    ) -> EmbeddingModel:
        """Create a ModelScope embedder."""
        return ModelScopeEmbedder(
            model_id=model_name,
            device=kwargs.get("device"),
            cache_dir=kwargs.get("cache_dir"),
        )
