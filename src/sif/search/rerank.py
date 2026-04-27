"""Result reranking using cross-encoders and LLM-based rerankers."""

from __future__ import annotations

import math
from pathlib import Path
from typing import TYPE_CHECKING

from sif.core.models import SearchResult
from sif.utils.logging import get_logger, is_quiet, suppress_output


if TYPE_CHECKING:
    from sentence_transformers import CrossEncoder  # noqa: F401

logger = get_logger(__name__)


def _sort_and_build_results(
    results: list[SearchResult],
    scores: list[float],
    top_k: int,
) -> list[SearchResult]:
    """Sort results by score descending and rebuild SearchResult objects."""
    scored = list(zip(results, scores))
    scored.sort(key=lambda x: x[1], reverse=True)

    reranked: list[SearchResult] = []
    for rank, (result, score) in enumerate(scored[:top_k], 1):
        new_scores = dict(result.scores) if result.scores else {}
        new_scores["reranker_score"] = score

        reranked.append(
            SearchResult(
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
        )
    return reranked


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
        from llama_cpp import Llama  # noqa: PLC0415

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

        import numpy as np  # noqa: PLC0415

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
            if result.title:
                text = f"{result.title}\n\n{text}" if text else result.title
            doc_emb = self._model.embed(text)
            doc_vec = np.array(doc_emb)
            doc_norm = np.linalg.norm(doc_vec)
            sim = np.dot(query_vec, doc_vec) / (query_norm * doc_norm + 1e-8)
            scored.append((result, float(sim)))

        # Normalize to [0, 1] via sigmoid
        normalized = [1.0 / (1.0 + math.exp(-s)) for _, s in scored]

        return _sort_and_build_results([r for r, _ in scored], normalized, top_k)


class CrossEncoderReranker:
    """Rerank search results using sentence-transformers CrossEncoder."""

    def __init__(
        self,
        model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2",
        model_path: str | None = None,
        device: str | None = None,
        batch_size: int = 32,
        cache_dir: str | None = None,
    ) -> None:
        self._model_name = model_name
        self._model_path = model_path
        self._device = device
        self._batch_size = batch_size
        self._cache_dir = cache_dir
        self._model = None

    def load(self) -> None:
        """Load the cross-encoder model."""
        if self._model is not None:
            return
        from sentence_transformers import CrossEncoder  # noqa: PLC0415

        model_id = self._model_path or self._model_name

        # If model_id looks like a ModelScope ID (contains "/" and not a local path),
        # download from ModelScope first
        local_path = model_id
        if "/" in model_id and not Path(model_id).exists():
            try:
                from sif.models.download import ModelDownloader  # noqa: PLC0415

                downloader = ModelDownloader(self._cache_dir)
                downloaded = downloader.download(model_id)
                # snapshot_download may return a path with subdirectories
                subdirs = [d for d in downloaded.iterdir() if d.is_dir()]
                local_path = str(subdirs[0]) if subdirs else str(downloaded)
                logger.info(f"Loading ModelScope reranker model: {model_id}")
            except Exception:
                logger.info(f"Loading ST reranker model: {model_id}")
        else:
            logger.info(f"Loading ST reranker model: {model_id}")

        if is_quiet():
            with suppress_output():
                self._model = CrossEncoder(local_path, device=self._device, max_length=512)
        else:
            self._model = CrossEncoder(local_path, device=self._device, max_length=512)
        logger.info("Reranker model loaded successfully")

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
            if result.title:
                text = f"{result.title}\n\n{text}" if text else result.title
            pairs.append((query, text))

        # Score all pairs
        raw_scores = self._model.predict(pairs, batch_size=self._batch_size)  # type: ignore[union-attr]

        # Normalize scores to [0, 1] using sigmoid
        normalized = [1.0 / (1.0 + math.exp(-float(s))) for s in raw_scores]

        return _sort_and_build_results(results, normalized, top_k)


class Qwen3Reranker:
    """Reranker for Qwen3-Reranker models using AutoModelForCausalLM.

    Qwen3-Reranker models are Causal LMs that predict "yes"/"no" tokens
    to judge query-document relevance. See:
    https://huggingface.co/Qwen/Qwen3-Reranker-0.6B
    """

    def __init__(  # noqa: PLR0913
        self,
        model_name: str = "Qwen/Qwen3-Reranker-0.6B",
        model_path: str | None = None,
        device: str | None = None,
        batch_size: int = 8,
        cache_dir: str | None = None,
        max_length: int = 8192,
    ) -> None:
        self._model_name = model_name
        self._model_path = model_path
        self._device = device
        self._batch_size = batch_size
        self._cache_dir = cache_dir
        self._max_length = max_length
        self._model = None
        self._tokenizer = None
        self._token_true_id: int | None = None
        self._token_false_id: int | None = None

    def load(self) -> None:
        """Load the Qwen3 reranker model."""
        if self._model is not None:
            return

        import torch  # noqa: PLC0415
        from transformers import AutoModelForCausalLM, AutoTokenizer  # noqa: PLC0415

        model_id = self._model_path or self._model_name
        local_path = model_id

        # Download from ModelScope if needed
        if "/" in model_id and not Path(model_id).exists():
            from sif.models.download import ModelDownloader  # noqa: PLC0415

            downloader = ModelDownloader(self._cache_dir)
            downloaded = downloader.download(model_id)
            subdirs = [d for d in downloaded.iterdir() if d.is_dir()]
            local_path = str(subdirs[0]) if subdirs else str(downloaded)

        logger.info(f"Loading Qwen3 reranker model: {model_id}")

        if is_quiet():
            with suppress_output():
                self._tokenizer = AutoTokenizer.from_pretrained(local_path, padding_side="left")
                self._model = AutoModelForCausalLM.from_pretrained(
                    local_path,
                    torch_dtype=torch.bfloat16 if torch.cuda.is_available() else torch.float32,
                ).eval()

                if self._device:
                    self._model = self._model.to(self._device)
                else:
                    device = "cuda" if torch.cuda.is_available() else "cpu"
                    self._model = self._model.to(device)

                self._token_true_id = self._tokenizer.convert_tokens_to_ids("yes")
                self._token_false_id = self._tokenizer.convert_tokens_to_ids("no")
        else:
            self._tokenizer = AutoTokenizer.from_pretrained(local_path, padding_side="left")
            self._model = AutoModelForCausalLM.from_pretrained(
                local_path,
                torch_dtype=torch.bfloat16 if torch.cuda.is_available() else torch.float32,
            ).eval()

            if self._device:
                self._model = self._model.to(self._device)
            else:
                device = "cuda" if torch.cuda.is_available() else "cpu"
                self._model = self._model.to(device)

            self._token_true_id = self._tokenizer.convert_tokens_to_ids("yes")
            self._token_false_id = self._tokenizer.convert_tokens_to_ids("no")
        logger.info("Qwen3 reranker model loaded successfully")

    @staticmethod
    def _format_prompt(instruction: str | None, query: str, doc: str) -> str:
        """Format query-document pair into Qwen3 reranker prompt."""
        if instruction is None:
            instruction = (
                "Given a web search query, retrieve relevant passages that answer the query"
            )
        return f"<Instruct>: {instruction}\n<Query>: {query}\n<Document>: {doc}"

    def rerank(
        self,
        query: str,
        results: list[SearchResult],
        top_k: int = 10,
    ) -> list[SearchResult]:
        """Rerank search results using Qwen3 Causal LM."""
        if not results:
            return []

        if self._model is None:
            self.load()

        import torch  # noqa: PLC0415

        # Build prompts
        texts: list[str] = []
        for result in results:
            text = result.content or ""
            if not text and result.highlights:
                text = result.highlights[0]
            if result.title:
                text = f"{result.title}\n\n{text}" if text else result.title
            texts.append(self._format_prompt(None, query, text))

        # Score in batches
        all_scores: list[float] = []
        for i in range(0, len(texts), self._batch_size):
            batch = texts[i : i + self._batch_size]
            inputs = self._tokenizer(
                batch,
                padding=True,
                truncation=True,
                max_length=self._max_length,
                return_tensors="pt",
            )
            inputs = {k: v.to(self._model.device) for k, v in inputs.items()}  # type: ignore[union-attr]

            with torch.no_grad():
                outputs = self._model(**inputs)  # type: ignore[operator]

            # Last token logits -> yes/no probabilities
            logits = outputs.logits[:, -1, :]  # type: ignore[union-attr]
            true_scores = logits[:, self._token_true_id]
            false_scores = logits[:, self._token_false_id]
            batch_logits = torch.stack([false_scores, true_scores], dim=1)
            batch_probs = torch.nn.functional.softmax(batch_logits, dim=1)
            scores = batch_probs[:, 1].tolist()
            all_scores.extend(scores)

        return _sort_and_build_results(results, all_scores, top_k)


def create_reranker(
    settings,
) -> LlamaCppReranker | CrossEncoderReranker | Qwen3Reranker:
    """Factory: create a reranker based on settings."""
    model_type = getattr(settings, "reranker_model_type", "gguf")
    model_name = getattr(settings, "reranker_model_name", "")
    cache_dir = str(settings.get_cache_dir()) if hasattr(settings, "get_cache_dir") else None

    # Auto-detect Qwen3 reranker models
    if "qwen3-reranker" in model_name.lower() or "qwen3_reranker" in model_name.lower():
        return Qwen3Reranker(
            model_name=settings.reranker_model_name,
            model_path=str(settings.reranker_model_path) if settings.reranker_model_path else None,
            batch_size=settings.reranker_batch_size,
            cache_dir=cache_dir,
        )

    if model_type == "gguf":
        return LlamaCppReranker(
            model_path=str(settings.reranker_model_path) if settings.reranker_model_path else None,
            model_name=settings.reranker_model_name,
            batch_size=settings.reranker_batch_size,
        )
    if model_type == "sentence_transformers":
        return CrossEncoderReranker(
            model_name=settings.reranker_model_name,
            model_path=str(settings.reranker_model_path) if settings.reranker_model_path else None,
            batch_size=settings.reranker_batch_size,
            cache_dir=cache_dir,
        )
    raise ValueError(f"Unknown reranker model_type: {model_type}")


# Backwards-compatible alias
Reranker = LlamaCppReranker
