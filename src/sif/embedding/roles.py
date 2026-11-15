"""Type-aware role dispatch for embedders (EMB-02, D-06).

The ``Embedder`` protocol keeps only ``embed``/``embed_batch``/``dimension``.
Concrete sentence-transformers backends add role methods, and protocol-only
doubles must keep working unchanged. The lookup is deliberately class-level:
``MagicMock`` auto-creates instance attributes, so an instance-level check
would route every mock through a phantom role method instead of ``embed``.
"""

from __future__ import annotations

from collections.abc import Callable

from sif.core.models import Embedder


def _class_defines(embedder: Embedder, name: str) -> bool:
    """Whether the embedder's class (not an instance mock) defines ``name``."""
    return getattr(type(embedder), name, None) is not None


def embed_query(embedder: Embedder, text: str) -> list[float]:
    """Embed a query through the role method when the class defines one."""
    if _class_defines(embedder, "embed_query"):
        method: Callable[[str], list[float]] = getattr(embedder, "embed_query")  # noqa: B009
        return method(text)
    return embedder.embed(text)


def embed_queries(embedder: Embedder, texts: list[str]) -> list[list[float]]:
    """Embed query-role texts through the role method when available."""
    if _class_defines(embedder, "embed_queries"):
        method: Callable[[list[str]], list[list[float]]] = getattr(embedder, "embed_queries")  # noqa: B009
        return method(texts)
    return embedder.embed_batch(texts)


def embed_documents(embedder: Embedder, texts: list[str]) -> list[list[float]]:
    """Embed document-role texts through the role method when available."""
    if _class_defines(embedder, "embed_documents"):
        method: Callable[[list[str]], list[list[float]]] = getattr(embedder, "embed_documents")  # noqa: B009
        return method(texts)
    return embedder.embed_batch(texts)
