"""Embedding manager for model lifecycle and embedding generation."""

from docsift.config.settings import Settings
from docsift.embedding.cache import EmbeddingCache
from docsift.embedding.factory import EmbeddingModelFactory
from docsift.embedding.model import EmbeddingModel, ModelType
from docsift.models.embedding import EmbeddingConfig, EmbeddingResponse
from docsift.utils.logging import get_logger

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
        self._model: EmbeddingModel | None = None
    
    @classmethod
    def from_settings(cls, settings: Settings) -> "EmbeddingManager":
        """Create an embedding manager from settings.
        
        Args:
            settings: Application settings
            
        Returns:
            Configured embedding manager
        """
        config = EmbeddingConfig(
            model_name=settings.model_name,
            model_path=str(settings.model_path) if settings.model_path else None,
            embedding_dim=settings.embedding_dim,
            max_tokens=settings.max_tokens,
            batch_size=settings.batch_size,
            n_gpu_layers=settings.n_gpu_layers,
            cache_embeddings=settings.cache_embeddings,
            cache_dir=str(settings.get_cache_dir()) if settings.cache_embeddings else None,
        )
        
        cache = None
        if config.cache_embeddings and config.cache_dir:
            cache = EmbeddingCache(config.cache_dir)
        
        return cls(config=config, cache=cache)
    
    def load_model(self) -> None:
        """Load the embedding model."""
        if self._model and self._model.loaded:
            return
        
        logger.info(f"Loading embedding model: {self._config.model_name}")
        
        self._model = self._factory.create_model(
            model_type=self._config.model_type,
            model_path=self._config.model_path,
            model_name=self._config.model_name,
            embedding_dim=self._config.embedding_dim,
            max_tokens=self._config.max_tokens,
            n_gpu_layers=self._config.n_gpu_layers,
            n_ctx=self._config.n_ctx,
        )
        
        self._model.load()
        logger.info("Embedding model loaded successfully")
    
    def unload_model(self) -> None:
        """Unload the embedding model to free memory."""
        if self._model:
            self._model.unload()
            self._model = None
            logger.info("Embedding model unloaded")
    
    def embed(
        self,
        texts: list[str],
        normalize: bool = True,
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
        import time
        
        self.load_model()
        
        start_time = time.time()
        
        # Check cache for cached embeddings
        embeddings: list[list[float] | None] = [None] * len(texts)
        texts_to_embed: list[tuple[int, str]] = []
        
        if use_cache and self._cache:
            for i, text in enumerate(texts):
                cached = self._cache.get(text)
                if cached is not None:
                    embeddings[i] = cached
                else:
                    texts_to_embed.append((i, text))
        else:
            texts_to_embed = list(enumerate(texts))
        
        # Generate embeddings for uncached texts
        if texts_to_embed and self._model:
            indices, to_embed = zip(*texts_to_embed)
            new_embeddings = self._model.embed(list(to_embed), normalize=normalize)
            
            # Store in cache
            if use_cache and self._cache:
                for idx, text, emb in zip(indices, to_embed, new_embeddings):
                    self._cache.set(text, emb)
            
            # Fill in results
            for idx, emb in zip(indices, new_embeddings):
                embeddings[idx] = emb
        
        processing_time = (time.time() - start_time) * 1000
        
        # Count tokens (rough estimate)
        total_tokens = sum(len(t) // 4 for t in texts)
        
        return EmbeddingResponse(
            embeddings=[e for e in embeddings if e is not None],
            model_id=self._model.model_id if self._model else "unknown",
            dimensions=self._config.embedding_dim,
            total_tokens=total_tokens,
            processing_time_ms=processing_time,
        )
    
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
            "loaded": self._model.loaded,
            "model_id": self._model.model_id,
            "embedding_dim": self._model.embedding_dim,
            "max_tokens": self._model.max_tokens,
        }
