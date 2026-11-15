"""Embedding manager for model lifecycle and embedding generation."""

import math
import time
from collections.abc import Callable
from typing import Any

from sif.config.settings import Settings
from sif.core.models import Embedder
from sif.embedding.cache import EmbeddingCache
from sif.embedding.factory import EmbeddingModelFactory
from sif.embedding.identity import EmbedderIdentity, build_identity, format_cache_model_id
from sif.embedding.prompts import PromptScheme, resolve_prompt_scheme
from sif.models.embedding import EmbeddingConfig, EmbeddingResponse, ModelType
from sif.utils.logging import get_logger


logger = get_logger(__name__)

# Cache-bucket role markers: a prompted query and an unprompted document of
# the same text must never share a cached vector (D-08).
_ROLE_MARKERS = {"query": "q", "document": "d"}


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
        self._prompt_scheme: PromptScheme = resolve_prompt_scheme(
            self._config.model_name,
            self._config.model_type.value,
            self._config.query_prompt_name,
            self._config.document_prompt_name,
        )
        self._identity: EmbedderIdentity | None = None

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
            query_prompt_name=settings.query_prompt_name,
            document_prompt_name=settings.document_prompt_name,
            cache_embeddings=settings.cache_embeddings,
            cache_dir=str(settings.get_cache_dir()) if settings.cache_embeddings else None,
        )

        cache = None
        if config.cache_embeddings and config.cache_dir:
            cache = EmbeddingCache(config.cache_dir)

        return cls(config=config, cache=cache)

    @property
    def model(self) -> Embedder | None:
        """The loaded embedder, or None when no model is loaded."""
        return self._model

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
            query_prompt_name=self._prompt_scheme.query_prompt,
            document_prompt_name=self._prompt_scheme.document_prompt,
        )
        self._identity = None

        logger.info("Embedding model loaded successfully")

    def unload_model(self) -> None:
        """Unload the embedding model to free memory."""
        if self._model is not None:
            self._model = None
            self._identity = None
            logger.info("Embedding model unloaded")

    def embed(
        self,
        texts: list[str],
        normalize: bool = True,  # noqa: ARG002
        use_cache: bool = True,
    ) -> EmbeddingResponse:
        """Generate embeddings for texts.

        This is the role-less compatibility surface (probe/compat): it keeps
        exactly the pre-Phase-21 cache bucket and encode kwargs.

        Args:
            texts: Texts to embed
            normalize: Whether to normalize embeddings
            use_cache: Whether to use caching

        Returns:
            Embedding response with embeddings and metadata
        """
        self.load_model()
        assert self._model is not None  # guaranteed by load_model()

        start_time = time.time()
        embeddings = self._compute_embeddings(
            texts,
            use_cache,
            self._cache_model_id(),
            self._model.embed_batch,
        )
        return self._build_response(texts, embeddings, start_time)

    def embed_query(self, text: str, use_cache: bool = True) -> list[float]:
        """Generate a query-role embedding for one text."""
        return self.embed_queries([text], use_cache=use_cache).embeddings[0]

    def embed_queries(self, texts: list[str], use_cache: bool = True) -> EmbeddingResponse:
        """Generate query-role embeddings (prompt-aware cache bucket)."""
        return self._embed_role(texts, "query", use_cache=use_cache)

    def embed_documents(self, texts: list[str], use_cache: bool = True) -> EmbeddingResponse:
        """Generate document-role embeddings (prompt-aware cache bucket)."""
        return self._embed_role(texts, "document", use_cache=use_cache)

    def _embed_role(
        self,
        texts: list[str],
        role: str,
        use_cache: bool = True,
    ) -> EmbeddingResponse:
        """Run one role-aware embedding request through the shared path."""
        self.load_model()
        assert self._model is not None  # guaranteed by load_model()

        start_time = time.time()
        bucket = self._cache_bucket(role)
        embeddings = self._compute_embeddings(
            texts,
            use_cache,
            bucket,
            self._role_model_call(role),
        )
        return self._build_response(texts, embeddings, start_time)

    def _build_response(
        self,
        texts: list[str],
        embeddings: list[list[float] | None],
        start_time: float,
    ) -> EmbeddingResponse:
        """Assemble an ``EmbeddingResponse`` with the 1:1 count guard."""
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

    def get_identity(self) -> EmbedderIdentity:
        """Return the effective embedder identity, cached until (un)load."""
        self.load_model()
        if self._identity is None:
            self._identity = build_identity(self._config, self._model, self._prompt_scheme)
        return self._identity

    def _cache_model_id(self) -> str:
        """Build the cache bucket identifier for the configured model.

        The bucket must identify the actual model: different backends /
        model names produce incompatible vectors for the same text, so they
        must never read each other's cached embeddings.
        """
        return format_cache_model_id(
            self._config.model_type.value,
            self._config.model_name,
            self._config.api_base,
        )

    def _cache_bucket(self, role: str) -> str:
        """Extend the model bucket with the revision and effective role prompt."""
        if role not in _ROLE_MARKERS:
            raise ValueError(f"Unknown embedding role: {role}")

        bucket = self._cache_model_id()
        identity = self.get_identity()
        if identity.revision:
            bucket = f"{bucket}|rev@{identity.revision}"
        prompt = identity.query_prompt if role == "query" else identity.document_prompt
        if prompt is not None:
            bucket = f"{bucket}|{_ROLE_MARKERS[role]}@{prompt}"
        return bucket

    def _role_model_call(self, role: str) -> Callable[[list[str]], list[list[float]]]:
        """Pick the model call for a role, falling back for protocol-only doubles."""
        assert self._model is not None  # guaranteed by load_model()
        prompt = (
            self._prompt_scheme.query_prompt
            if role == "query"
            else self._prompt_scheme.document_prompt
        )
        if prompt is None:
            return self._model.embed_batch

        method_name = "embed_queries" if role == "query" else "embed_documents"
        if getattr(type(self._model), method_name, None) is None:
            return self._model.embed_batch
        bound: Callable[[list[str]], list[list[float]]] = getattr(self._model, method_name)
        return bound

    def _is_usable_cached(self, vector: list[float]) -> bool:
        """Whether a cached vector has the identity dimension and finite values."""
        if len(vector) != self.get_identity().dimension:
            return False
        try:
            return all(math.isfinite(float(value)) for value in vector)
        except (TypeError, ValueError):
            return False

    def _validate_vector(self, vector: list[float], position: int, bucket: str) -> None:
        """Reject non-finite or wrong-dimension model output before caching it."""
        expected = self.get_identity().dimension
        if len(vector) != expected:
            raise RuntimeError(
                f"Embedding model '{bucket}' returned a {len(vector)}-dim vector at "
                f"position {position}; expected {expected} dims"
            )
        try:
            finite = all(math.isfinite(float(value)) for value in vector)
        except (TypeError, ValueError):
            finite = False
        if not finite:
            raise RuntimeError(
                f"Embedding model '{bucket}' returned a non-finite vector at position {position}"
            )

    def _lookup_cached(
        self,
        texts: list[str],
        embeddings: list[list[float] | None],
        use_cache: bool,
        model_id: str,
    ) -> list[tuple[int, str]]:
        """Fill embeddings from the cache; return (index, text) pairs left to embed."""
        if not (use_cache and self._cache):
            return list(enumerate(texts))

        texts_to_embed: list[tuple[int, str]] = []
        for i, text in enumerate(texts):
            cached = self._cache.get(text, model_id=model_id)
            if cached is not None and self._is_usable_cached(cached):
                embeddings[i] = cached
            else:
                texts_to_embed.append((i, text))
        return texts_to_embed

    def _compute_embeddings(
        self,
        texts: list[str],
        use_cache: bool,
        model_id: str,
        model_call: Callable[[list[str]], list[list[float]]],
    ) -> list[list[float] | None]:
        """Produce one embedding slot per text, using the cache when allowed."""
        assert self._model is not None  # guaranteed by load_model()
        embeddings: list[list[float] | None] = [None] * len(texts)
        texts_to_embed = self._lookup_cached(texts, embeddings, use_cache, model_id)
        if not texts_to_embed:
            return embeddings

        indices, to_embed = zip(*texts_to_embed, strict=True)
        new_embeddings = model_call(list(to_embed))
        if len(new_embeddings) != len(to_embed):
            raise RuntimeError(
                f"Embedding model returned {len(new_embeddings)} embeddings for "
                f"{len(to_embed)} inputs"
            )
        for position, vector in enumerate(new_embeddings):
            self._validate_vector(vector, position, model_id)

        # Store in cache
        if use_cache and self._cache:
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

    def get_model_info(self) -> dict[str, Any]:
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
