"""Embedding model implementation."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import List, Optional

import numpy as np

from sif.core.models import Embedder
from sif.models.download import ModelDownloader
from sif.utils.logging import get_logger, is_quiet, suppress_output


logger = get_logger(__name__)


class SentenceTransformerEmbedder(Embedder):
    """Embedder using sentence-transformers."""

    def __init__(
        self,
        model_name: str = "all-MiniLM-L6-v2",
        device: Optional[str] = None,
        cache_dir: Optional[str] = None,
    ) -> None:
        """Initialize sentence transformer embedder.

        Args:
            model_name: HuggingFace model name
            device: Device to use (cpu, cuda, etc.)
            cache_dir: Cache directory for models
        """
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError:
            logger.error(
                "sentence-transformers not installed. Install with: pip install sentence-transformers"
            )
            raise

        self.model_name = model_name

        if device is None:
            import torch

            device = "cuda" if torch.cuda.is_available() else "cpu"

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

    def embed(self, text: str) -> List[float]:
        """Embed a single text.

        Args:
            text: Text to embed

        Returns:
            Embedding vector
        """
        embedding = self.model.encode(text, normalize_embeddings=True)
        return embedding.tolist()

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Embed multiple texts.

        Args:
            texts: List of texts to embed

        Returns:
            List of embedding vectors
        """
        embeddings = self.model.encode(
            texts,
            normalize_embeddings=True,
            show_progress_bar=len(texts) > 100,
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
        n_threads: Optional[int] = None,
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
            from llama_cpp import Llama
        except ImportError:
            logger.error(
                "llama-cpp-python not installed. Install with: pip install llama-cpp-python"
            )
            raise

        self.model_path = Path(model_path)

        if n_threads is None:
            import os

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

    def embed(self, text: str) -> List[float]:
        """Embed a single text."""
        embedding = self.model.embed(text)
        # Normalize
        norm = np.linalg.norm(embedding)
        if norm > 0:
            embedding = embedding / norm
        return embedding.tolist()

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
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
        device: Optional[str] = None,
        cache_dir: Optional[str] = None,
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
            from sentence_transformers import SentenceTransformer
        except ImportError:
            logger.error("sentence-transformers not installed")
            raise

        if device is None:
            import torch

            device = "cuda" if torch.cuda.is_available() else "cpu"

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

    def embed(self, text: str) -> List[float]:
        """Embed a single text."""
        embedding = self.model.encode(text, normalize_embeddings=True)
        return embedding.tolist()

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Embed multiple texts."""
        embeddings = self.model.encode(
            texts,
            normalize_embeddings=True,
            show_progress_bar=len(texts) > 100,
        )
        return embeddings.tolist()

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

    def embed(self, text: str) -> List[float]:
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

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
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
