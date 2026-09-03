"""Embedding model implementation."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np

from sif.core.models import Embedder
from sif.models.download import ModelDownloader
from sif.utils.logging import get_logger, is_quiet, suppress_output


logger = get_logger(__name__)

_PROGRESS_BAR_THRESHOLD = 100


class SentenceTransformerEmbedder(Embedder):
    """Embedder using sentence-transformers."""

    def __init__(
        self,
        model_name: str = "all-MiniLM-L6-v2",
        device: str | None = None,
        cache_dir: str | None = None,
    ) -> None:
        """Initialize sentence transformer embedder.

        Args:
            model_name: HuggingFace model name
            device: Device to use (cpu, cuda, etc.)
            cache_dir: Cache directory for models
        """
        try:
            from sentence_transformers import SentenceTransformer  # noqa: PLC0415
        except ImportError:
            logger.error(
                "sentence-transformers not installed. "
                "Install with: pip install sentence-transformers",
            )
            raise

        self.model_name = model_name

        if device is None:
            import torch  # noqa: PLC0415

            if torch.cuda.is_available():
                device = "cuda"
            elif hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
                device = "mps"
            else:
                device = "cpu"

        logger.info(f"Loading embedding model: {model_name} on {device}")

        if is_quiet():
            with suppress_output():
                self.model = SentenceTransformer(
                    model_name,
                    device=device,
                    cache_folder=cache_dir,
                )
        else:
            self.model = SentenceTransformer(
                model_name,
                device=device,
                cache_folder=cache_dir,
            )

        self._dimension = self.model.get_sentence_embedding_dimension()
        logger.info(f"Embedding dimension: {self._dimension}")

    def embed(self, text: str) -> list[float]:
        """Embed a single text.

        Args:
            text: Text to embed

        Returns:
            Embedding vector
        """
        embedding = self.model.encode(text, normalize_embeddings=True)
        return embedding.tolist()

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Embed multiple texts.

        Args:
            texts: List of texts to embed

        Returns:
            List of embedding vectors
        """
        embeddings = self.model.encode(
            texts,
            normalize_embeddings=True,
            show_progress_bar=len(texts) > _PROGRESS_BAR_THRESHOLD,
        )
        return embeddings.tolist()

    @property
    def dimension(self) -> int:
        """Get embedding dimension."""
        return self._dimension


class LlamaCppEmbedder(Embedder):
    """Embedder using llama-cpp-python."""

    def __init__(
        self,
        model_path: str | Path,
        n_ctx: int = 8192,
        n_threads: int | None = None,
        verbose: bool = False,
    ) -> None:
        """Initialize llama.cpp embedder.

        Args:
            model_path: Path to GGUF model file
            n_ctx: Context size
            n_threads: Number of threads (auto if None)
            verbose: Enable verbose output
        """
        try:
            from llama_cpp import Llama  # noqa: PLC0415
        except ImportError:
            logger.error(
                "llama-cpp-python not installed. Install with: pip install llama-cpp-python",
            )
            raise

        self.model_path = Path(model_path)

        if n_threads is None:
            import os  # noqa: PLC0415

            n_threads = os.cpu_count() or 4

        logger.info(f"Loading llama.cpp model: {self.model_path}")

        self.model = Llama(
            model_path=str(self.model_path),
            n_ctx=n_ctx,
            n_threads=n_threads,
            embedding=True,
            verbose=verbose,
        )

        self._dimension = self.model.n_embd()
        logger.info(f"Embedding dimension: {self._dimension}")

    def embed(self, text: str) -> list[float]:
        """Embed a single text."""
        embedding = self.model.embed(text)
        # Normalize
        norm = np.linalg.norm(embedding)
        if norm > 0:
            embedding = embedding / norm
        return embedding.tolist()

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Embed multiple texts."""
        embeddings = []
        for text in texts:
            embedding = self.embed(text)
            embeddings.append(embedding)
        return embeddings

    @property
    def dimension(self) -> int:
        """Get embedding dimension."""
        return self._dimension


class ModelScopeEmbedder(Embedder):
    """Embedder that downloads from ModelScope and uses sentence-transformers."""

    def __init__(
        self,
        model_id: str = "iic/gte_Qwen2-7B-instruct",
        device: str | None = None,
        cache_dir: str | None = None,
        force_download: bool = False,
    ) -> None:
        """Initialize ModelScope embedder.

        Args:
            model_id: ModelScope model ID
            device: Device to use
            cache_dir: Cache directory
            force_download: Force re-download
        """
        # Download model from ModelScope
        downloader = ModelDownloader(cache_dir)
        model_path = downloader.download(model_id, force=force_download)

        # Find the actual model directory (snapshot_download creates subdirectories)
        model_dirs = list(model_path.glob("*"))
        if model_dirs:
            # Use the first subdirectory if exists
            actual_model_path = model_dirs[0] if model_dirs[0].is_dir() else model_path
        else:
            actual_model_path = model_path

        # Initialize with sentence-transformers
        try:
            from sentence_transformers import SentenceTransformer  # noqa: PLC0415
        except ImportError:
            logger.error("sentence-transformers not installed")
            raise

        if device is None:
            import torch  # noqa: PLC0415

            if torch.cuda.is_available():
                device = "cuda"
            elif hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
                device = "mps"
            else:
                device = "cpu"

        logger.info(f"Loading ModelScope model: {model_id} on {device}")

        if is_quiet():
            with suppress_output():
                self.model = SentenceTransformer(
                    str(actual_model_path),
                    device=device,
                )
        else:
            self.model = SentenceTransformer(
                str(actual_model_path),
                device=device,
            )

        self._dimension = self.model.get_sentence_embedding_dimension()
        self.model_id = model_id
        logger.info(f"Embedding dimension: {self._dimension}")

    def embed(self, text: str) -> list[float]:
        """Embed a single text."""
        embedding = self.model.encode(text, normalize_embeddings=True)
        return embedding.tolist()

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Embed multiple texts."""
        embeddings = self.model.encode(
            texts,
            normalize_embeddings=True,
            show_progress_bar=len(texts) > _PROGRESS_BAR_THRESHOLD,
        )
        return embeddings.tolist()

    @property
    def dimension(self) -> int:
        """Get embedding dimension."""
        return self._dimension


class OpenAIEmbedder(Embedder):
    """Embedder using an OpenAI-compatible embeddings API."""

    _DIM_CACHE_FILENAME = "openai_dim_cache.json"
    _DIM_CACHE_TTL_SECONDS = 604800  # 7 days

    def __init__(  # noqa: PLR0913
        self,
        model_name: str = "text-embedding-3-small",
        api_key: str | None = None,
        api_base: str | None = None,
        embedding_dim: int | None = None,
        cache_dir: str | None = None,
        batch_size: int = 64,
    ) -> None:
        """Initialize an OpenAI-compatible embedder.

        Args:
            model_name: Model name as the endpoint knows it.
            api_key: API key; passed only to the client constructor and never
                logged or embedded in exception messages.
            api_base: Base URL of an OpenAI-compatible endpoint; the SDK
                appends the /embeddings path. None uses the SDK default.
            embedding_dim: Caller-supplied embedding dimension. When it
                disagrees with the endpoint-detected dimension, construction
                fails fast (misconfigured SIF_EMBEDDING_DIM).
            cache_dir: Directory for the endpoint dimension cache
                (openai_dim_cache.json, 7-day TTL, keyed by model name).
            batch_size: Number of texts per embeddings.create request.
        """
        try:
            from openai import OpenAI  # noqa: PLC0415
        except ImportError:
            logger.error(
                "openai not installed. Install with: pip install sif[openai]",
            )
            raise

        self.model_name = model_name
        self._batch_size = batch_size
        self._cache_dir = Path(cache_dir) if cache_dir is not None else None
        self._client = OpenAI(api_key=api_key, base_url=api_base)

        resolved_dim = self._resolve_dimension()
        if embedding_dim is not None and embedding_dim != resolved_dim:
            raise RuntimeError(
                f"Embedding dimension mismatch: model '{model_name}' produces "
                f"{resolved_dim}-dimensional embeddings but SIF_EMBEDDING_DIM "
                f"is set to {embedding_dim}. Set SIF_EMBEDDING_DIM to the "
                f"endpoint model's dimension."
            )
        self._dimension = resolved_dim

        logger.info(f"OpenAI embedder ready: {model_name} (dim={self._dimension})")

    def _resolve_dimension(self) -> int:
        """Resolve the endpoint's embedding dimension.

        The API is the source of truth: a cached detection younger than the
        TTL is reused, otherwise a minimal probe detects it and refreshes the
        cache. Cache failures never crash loading — they degrade to a probe.
        """
        cached = self._read_dim_cache()
        if cached is not None:
            return cached
        dimension = self._probe_dimension()
        self._write_dim_cache(dimension)
        return dimension

    def _read_dim_cache(self) -> int | None:
        """Read a fresh cached dimension for this model, if any."""
        if self._cache_dir is None:
            return None
        cache_file = self._cache_dir / self._DIM_CACHE_FILENAME
        try:
            with open(cache_file, encoding="utf-8") as f:
                cache = json.load(f)
            entry = cache.get(self.model_name) if isinstance(cache, dict) else None
            if not isinstance(entry, dict):
                return None
            detected_at = datetime.fromisoformat(str(entry["detected_at"]))
            age = (datetime.now(timezone.utc) - detected_at).total_seconds()
            if age > self._DIM_CACHE_TTL_SECONDS:
                return None
            return int(entry["dimension"])
        except FileNotFoundError:
            return None
        except (OSError, ValueError, KeyError, TypeError) as e:
            logger.warning(f"Ignoring unreadable OpenAI dimension cache ({cache_file}): {e}")
            return None

    def _write_dim_cache(self, dimension: int) -> None:
        """Persist the detected dimension for this model, preserving others."""
        if self._cache_dir is None:
            return
        cache_file = self._cache_dir / self._DIM_CACHE_FILENAME
        try:
            self._cache_dir.mkdir(parents=True, exist_ok=True)
            entries: dict[str, dict[str, Any]] = {}
            try:
                with open(cache_file, encoding="utf-8") as f:
                    loaded = json.load(f)
                if isinstance(loaded, dict):
                    entries = loaded
            except (OSError, ValueError):
                logger.warning(
                    f"Discarding unreadable OpenAI dimension cache before rewrite ({cache_file})"
                )
            entries[self.model_name] = {
                "dimension": dimension,
                "detected_at": datetime.now(timezone.utc).isoformat(),
            }
            with open(cache_file, "w", encoding="utf-8") as f:
                json.dump(entries, f)
        except OSError as e:
            logger.warning(f"Failed to write OpenAI dimension cache ({cache_file}): {e}")

    def _probe_dimension(self) -> int:
        """Detect the embedding dimension with a minimal probe request."""
        response = self._client.embeddings.create(input=["."], model=self.model_name)
        return len(response.data[0].embedding)

    def embed(self, text: str) -> list[float]:
        """Embed a single text."""
        response = self._client.embeddings.create(input=[text], model=self.model_name)
        return self._normalize(response.data[0].embedding)

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Embed multiple texts, one API call per batch_size slice."""
        if not texts:
            return []
        embeddings: list[list[float]] = []
        for start in range(0, len(texts), self._batch_size):
            batch = texts[start : start + self._batch_size]
            response = self._client.embeddings.create(input=batch, model=self.model_name)
            if len(response.data) != len(batch):
                raise RuntimeError(
                    f"Embedding model '{self.model_name}' returned a ragged response: "
                    f"expected {len(batch)} embeddings, got {len(response.data)}"
                )
            embeddings.extend(self._normalize(item.embedding) for item in response.data)
        return embeddings

    @staticmethod
    def _normalize(vector: list[float]) -> list[float]:
        """L2-normalize a vector, consistent with the local backends."""
        arr = np.asarray(vector, dtype=float)
        norm = np.linalg.norm(arr)
        if norm > 0:
            arr = arr / norm
        return arr.tolist()

    @property
    def dimension(self) -> int:
        """Get embedding dimension."""
        return self._dimension


class SimpleEmbedder(Embedder):
    """Simple embedder using TF-IDF (fallback when no ML models available)."""

    def __init__(self, dimension: int = 384) -> None:
        """Initialize simple TF-IDF embedder.

        Args:
            dimension: Embedding dimension
        """
        self._dimension = dimension
        self.vocabulary: dict = {}
        self._doc_count = 0

    def embed(self, text: str) -> list[float]:
        """Embed text using simple hashing."""
        # Simple hash-based embedding

        # Create a deterministic embedding based on text hash
        hash_bytes = hashlib.sha256(text.encode()).digest()

        # Expand to desired dimension
        embedding = []
        for i in range(self._dimension):
            # Use different parts of hash
            idx = i % len(hash_bytes)
            val = (hash_bytes[idx] / 255.0) * 2 - 1  # Scale to [-1, 1]
            embedding.append(val)

        # Normalize
        norm = np.linalg.norm(embedding)
        if norm > 0:
            embedding = [v / norm for v in embedding]

        return embedding

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Embed multiple texts."""
        return [self.embed(text) for text in texts]

    @property
    def dimension(self) -> int:
        """Get embedding dimension."""
        return self._dimension


def create_embedder(
    embedder_type: str = "sentence_transformer",
    **kwargs,
) -> Embedder:
    """Factory function to create embedders.

    Args:
        embedder_type: Type of embedder to create
        **kwargs: Additional arguments for the embedder

    Returns:
        Embedder instance
    """
    if embedder_type == "sentence_transformer":
        return SentenceTransformerEmbedder(**kwargs)
    if embedder_type == "llama_cpp":
        return LlamaCppEmbedder(**kwargs)
    if embedder_type == "modelscope":
        return ModelScopeEmbedder(**kwargs)
    if embedder_type == "simple":
        return SimpleEmbedder(**kwargs)
    raise ValueError(f"Unknown embedder type: {embedder_type}")
