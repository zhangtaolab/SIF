"""Embedding manager for model lifecycle and embedding generation."""

import time

from sif.config.settings import Settings
from sif.core.models import Embedder
from sif.embedding.cache import EmbeddingCache
from sif.embedding.factory import EmbeddingModelFactory
from sif.models.embedding import EmbeddingConfig, EmbeddingResponse, ModelType
from sif.utils.logging import get_logger


logger = get_logger(__name__)


class EmbeddingManager:
    """Manager for embedding model lifecycle and operations.

    This class provides a high-level interface for:
    - Loading and unloading embedding models
    - Generating embeddings for text
    - Caching embeddings for reuse
    - Managing model configuration
    """

    def __init__(
        self,
        config: EmbeddingConfig | None = None,
        factory: EmbeddingModelFactory | None = None,
        cache: EmbeddingCache | None = None,
    ) -> None:
        """Initialize embedding manager.

        Args:
            config: Embedding configuration
            factory: Model factory (uses default if not provided)
            cache: Embedding cache (creates default if not provided)
        """
        self._config = config or EmbeddingConfig()
        self._factory = factory or EmbeddingModelFactory()
        self._cache = cache
        self._model: Embedder | None = None

    @classmethod
    def from_settings(cls, settings: Settings) -> "EmbeddingManager":
        """Create an embedding manager from settings.

        Args:
            settings: Application settings

        Returns:
            Configured embedding manager
        """
        config = EmbeddingConfig(
            model_type=ModelType(settings.model_type),
            model_name=settings.model_name,
            model_path=str(settings.model_path) if settings.model_path else None,
            embedding_dim=settings.embedding_dim,
            max_tokens=settings.max_tokens,
            batch_size=settings.batch_size,
            n_gpu_layers=settings.n_gpu_layers,
            api_key=settings.api_key,
            api_base=settings.api_base,
            cache_embeddings=settings.cache_embeddings,
            cache_dir=str(settings.get_cache_dir()) if settings.cache_embeddings else None,
        )

        cache = None
        if config.cache_embeddings and config.cache_dir:
            cache = EmbeddingCache(config.cache_dir)

        return cls(config=config, cache=cache)

    def load_model(self) -> None:
        """Load the embedding model."""
        if self._model is not None:
            return

        logger.info(f"Loading embedding model: {self._config.model_name}")

        self._model = self._factory.create_model(
            model_type=self._config.model_type,
            model_path=self._config.model_path,
            model_name=self._config.model_name,
            embedding_dim=self._config.embedding_dim,
            max_tokens=self._config.max_tokens,
            batch_size=self._config.batch_size,
            n_gpu_layers=self._config.n_gpu_layers,
            n_ctx=self._config.n_ctx,
            api_key=self._config.api_key,
            api_base=self._config.api_base,
            cache_dir=self._config.cache_dir,
        )

        logger.info("Embedding model loaded successfully")

    def unload_model(self) -> None:
        """Unload the embedding model to free memory."""
        if self._model is not None:
            self._model = None
            logger.info("Embedding model unloaded")

    def embed(
        self,
        texts: list[str],
        normalize: bool = True,  # noqa: ARG002
        use_cache: bool = True,
    ) -> EmbeddingResponse:
        """Generate embeddings for texts.

        Args:
            texts: Texts to embed
            normalize: Whether to normalize embeddings
            use_cache: Whether to use caching

        Returns:
            Embedding response with embeddings and metadata
        """
        self.load_model()

        start_time = time.time()
        embeddings = self._compute_embeddings(texts, use_cache)
        processing_time = (time.time() - start_time) * 1000

        # Count tokens (rough estimate)
        total_tokens = sum(len(t) // 4 for t in texts)

        actual_dim = self._model.dimension if self._model else self._config.embedding_dim

        # Guard the 1:1 texts<->embeddings contract: silently dropping
        # unfilled slots would misalign chunk->vector associations upstream.
        result_embeddings = [e for e in embeddings if e is not None]
        if len(result_embeddings) != len(texts):
            raise RuntimeError(
                f"Embedding model returned {len(result_embeddings)} embeddings for "
                f"{len(texts)} inputs"
            )

        return EmbeddingResponse(
            embeddings=result_embeddings,
            model_id=self._config.model_name,
            dimensions=actual_dim,
            total_tokens=total_tokens,
            processing_time_ms=processing_time,
        )

    def _cache_model_id(self) -> str:
        """Build the cache bucket identifier for the configured model.

        The bucket must identify the actual model: different backends /
        model names produce incompatible vectors for the same text, so they
        must never read each other's cached embeddings.
        """
        model_id = f"{self._config.model_type.value}:{self._config.model_name}"
        if self._config.api_base:
            model_id = f"{model_id}@{self._config.api_base}"
        return model_id

    def _lookup_cached(
        self,
        texts: list[str],
        embeddings: list[list[float] | None],
        use_cache: bool,
    ) -> list[tuple[int, str]]:
        """Fill embeddings from the cache; return (index, text) pairs left to embed."""
        if not (use_cache and self._cache):
            return list(enumerate(texts))

        model_id = self._cache_model_id()
        texts_to_embed: list[tuple[int, str]] = []
        for i, text in enumerate(texts):
            cached = self._cache.get(text, model_id=model_id)
            if cached is not None:
                embeddings[i] = cached
            else:
                texts_to_embed.append((i, text))
        return texts_to_embed

    def _compute_embeddings(
        self,
        texts: list[str],
        use_cache: bool,
    ) -> list[list[float] | None]:
        """Produce one embedding slot per text, using the cache when allowed."""
        assert self._model is not None  # guaranteed by load_model() in embed()
        embeddings: list[list[float] | None] = [None] * len(texts)
        texts_to_embed = self._lookup_cached(texts, embeddings, use_cache)
        if not texts_to_embed:
            return embeddings

        indices, to_embed = zip(*texts_to_embed, strict=True)
        new_embeddings = self._model.embed_batch(list(to_embed))
        if len(new_embeddings) != len(to_embed):
            raise RuntimeError(
                f"Embedding model returned {len(new_embeddings)} embeddings for "
                f"{len(to_embed)} inputs"
            )

        # Store in cache
        if use_cache and self._cache:
            model_id = self._cache_model_id()
            for _idx, text, emb in zip(indices, to_embed, new_embeddings, strict=True):
                self._cache.set(text, emb, model_id=model_id)

        # Fill in results
        for idx, emb in zip(indices, new_embeddings, strict=True):
            embeddings[idx] = emb

        return embeddings

    def embed_single(
        self,
        text: str,
        normalize: bool = True,
        use_cache: bool = True,
    ) -> list[float]:
        """Generate embedding for a single text.

        Args:
            text: Text to embed
            normalize: Whether to normalize the embedding
            use_cache: Whether to use caching

        Returns:
            Embedding vector
        """
        response = self.embed([text], normalize=normalize, use_cache=use_cache)
        return response.embeddings[0]

    def get_model_info(self) -> dict:
        """Get information about the loaded model.

        Returns:
            Model information dictionary
        """
        if not self._model:
            return {
                "loaded": False,
                "model_name": self._config.model_name,
            }

        return {
            "loaded": True,
            "model_id": self._config.model_name,
            "embedding_dim": self._model.dimension,
            "max_tokens": self._config.max_tokens,
        }
