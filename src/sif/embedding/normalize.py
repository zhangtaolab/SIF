"""Shared float64 L2 normalization for embedding vectors."""

from typing import Any

import numpy as np


def l2_normalize(values: Any) -> np.ndarray:
    """Renormalize encoder output to unit L2 length in float64.

    sentence-transformers applies ``normalize_embeddings`` in the model's
    compute dtype, and some models (e.g. Qwen3-Embedding on CUDA) come back
    off unit by up to ~4e-3. The float64 recomputation here is the point:
    that noise is what trips ``StreamingEmbedWriter.validate_batch``'s
    ``NORM_TOLERANCE`` gate and aborts ``sif index embed``.

    Works through broadcasting for both 1-D (single text) and 2-D (batch)
    inputs. Zero and non-finite vectors are divided by 1.0 and returned
    unchanged, so ``validate_batch``'s zero-norm and finiteness gates remain
    reachable instead of being papered over here.

    Shared by the sentence-transformers-backed embedder encode paths and by
    ``EmbeddingManager``'s cache-hit path, so cache rows written before the
    embedders renormalized in float64 come back unit-length as well. Already
    unit vectors are idempotent under it (within float64 rounding), and zero
    or non-finite vectors are divided by 1.0 and returned unchanged so the
    writer's zero-norm and finiteness gates stay reachable.
    """
    array = np.asarray(values, dtype=np.float64)
    norms = np.linalg.norm(array, axis=-1, keepdims=True)
    usable = np.isfinite(norms) & (norms > 0.0)
    result: np.ndarray = array / np.where(usable, norms, 1.0)
    return result
