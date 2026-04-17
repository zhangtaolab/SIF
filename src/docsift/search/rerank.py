"""Result reranking using cross-encoders."""

from __future__ import annotations

import math
from pathlib import Path
from typing import TYPE_CHECKING

from docsift.core.models import SearchResult
from docsift.utils.logging import get_logger

if TYPE_CHECKING:
    from sentence_transformers import CrossEncoder  # noqa: F401

logger = get_logger(__name__)


class LlamaCppReranker:
    """Rerank search results using a GGUF cross-encoder via llama-cpp-python."""

    def __init__(
        self,
        model_path: str | None = None,
        model_name: str = "",
        n_ctx: int = 512,
        n_threads: int | None = None,
        batch_size: int = 32,
    ) -> None:
        self._model_path = model_path
        self._model_name = model_name
        self._n_ctx = n_ctx
        self._n_threads = n_threads
        self._batch_size = batch_size
        self._model = None

    def load(self) -> None:
        """Load the GGUF model."""
        if self._model is not None:
            return
        from llama_cpp import Llama

        path = self._model_path or self._model_name
        if not path:
            raise ValueError("No model_path or model_name provided for LlamaCppReranker")
        logger.info(f"Loading GGUF reranker model: {path}")
        self._model = Llama(
            model_path=str(path),
            n_ctx=self._n_ctx,
            n_threads=self._n_threads,
            embedding=True,
            verbose=False,
        )
        logger.info("GGUF reranker model loaded successfully")

    def rerank(
        self,
        query: str,
        results: list[SearchResult],
        top_k: int = 10,
    ) -> list[SearchResult]:
        """Rerank search results."""
        if not results:
            return []

        if self._model is None:
            self.load()

        import numpy as np

        # Embed query once
        query_emb = self._model.embed(query)
        query_vec = np.array(query_emb)
        query_norm = np.linalg.norm(query_vec)

        # Score each result by embedding similarity
        scored = []
        for result in results:
            text = result.content or ""
            if not text and result.highlights:
                text = result.highlights[0]
            doc_emb = self._model.embed(text)
            doc_vec = np.array(doc_emb)
            doc_norm = np.linalg.norm(doc_vec)
            sim = np.dot(query_vec, doc_vec) / (query_norm * doc_norm + 1e-8)
            scored.append((result, float(sim)))

        # Normalize to [0, 1] via sigmoid
        normalized = [(r, 1.0 / (1.0 + math.exp(-s))) for r, s in scored]
        normalized.sort(key=lambda x: x[1], reverse=True)

        # Rebuild results with new scores and ranks
        reranked: list[SearchResult] = []
        for rank, (result, score) in enumerate(normalized[:top_k], 1):
            new_scores = dict(result.scores) if result.scores else {}
            new_scores["reranker_score"] = score

            new_result = SearchResult(
                document_id=result.document_id,
                title=result.title,
                path=result.path,
                collection_name=result.collection_name,
                score=score,
                content=result.content,
                highlights=result.highlights,
                rank=rank,
                scores=new_scores,
                snippet=result.snippet,
                context_description=result.context_description,
            )
            reranked.append(new_result)

        return reranked


class CrossEncoderReranker:
    """Rerank search results using sentence-transformers CrossEncoder."""

    def __init__(
        self,
        model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2",
        model_path: str | None = None,
        device: str | None = None,
        batch_size: int = 32,
    ) -> None:
        self._model_name = model_name
        self._model_path = model_path
        self._device = device
        self._batch_size = batch_size
        self._model = None

    def load(self) -> None:
        """Load the cross-encoder model."""
        if self._model is not None:
            return
        from sentence_transformers import CrossEncoder

        logger.info(f"Loading ST reranker model: {self._model_name}")
        model_id = self._model_path or self._model_name
        self._model = CrossEncoder(model_id, device=self._device, max_length=512)
        logger.info("ST reranker model loaded successfully")

    def rerank(
        self,
        query: str,
        results: list[SearchResult],
        top_k: int = 10,
    ) -> list[SearchResult]:
        """Rerank search results."""
        if not results:
            return []

        if self._model is None:
            self.load()

        # Build query-document pairs
        pairs: list[tuple[str, str]] = []
        for result in results:
            text = result.content or ""
            if not text and result.highlights:
                text = result.highlights[0]
            pairs.append((query, text))

        # Score all pairs
        raw_scores = self._model.predict(pairs, batch_size=self._batch_size)  # type: ignore[union-attr]

        # Normalize scores to [0, 1] using sigmoid
        normalized = [1.0 / (1.0 + math.exp(-float(s))) for s in raw_scores]

        # Sort by score descending
        scored = list(zip(results, normalized))
        scored.sort(key=lambda x: x[1], reverse=True)

        # Rebuild results with new scores and ranks
        reranked: list[SearchResult] = []
        for rank, (result, score) in enumerate(scored[:top_k], 1):
            new_scores = dict(result.scores) if result.scores else {}
            new_scores["reranker_score"] = score

            new_result = SearchResult(
                document_id=result.document_id,
                title=result.title,
                path=result.path,
                collection_name=result.collection_name,
                score=score,
                content=result.content,
                highlights=result.highlights,
                rank=rank,
                scores=new_scores,
                snippet=result.snippet,
                context_description=result.context_description,
            )
            reranked.append(new_result)

        return reranked


def create_reranker(settings) -> LlamaCppReranker | CrossEncoderReranker:
    """Factory: create a reranker based on settings."""
    model_type = getattr(settings, "reranker_model_type", "gguf")
    if model_type == "gguf":
        return LlamaCppReranker(
            model_path=str(settings.reranker_model_path) if settings.reranker_model_path else None,
            model_name=settings.reranker_model_name,
            batch_size=settings.reranker_batch_size,
        )
    elif model_type == "sentence_transformers":
        return CrossEncoderReranker(
            model_name=settings.reranker_model_name,
            model_path=str(settings.reranker_model_path) if settings.reranker_model_path else None,
            batch_size=settings.reranker_batch_size,
        )
    else:
        raise ValueError(f"Unknown reranker model_type: {model_type}")


# Backwards-compatible alias
Reranker = LlamaCppReranker
