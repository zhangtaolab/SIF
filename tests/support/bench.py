"""Deterministic bench fixture support: concept embedder + direct DB builder.

Shared by unit and CLI bench tests (Phase 16, EVAL-02): ``ConceptEmbedder``
gives the committed pack reproducible vectors without a real embedding
model, and ``build_bench_db`` raises a real SchemaManager database (FTS
triggers + vec0 table) from the committed corpus files, modeled on the
golden fixture in ``tests/unit/search/test_hybrid.py``.
"""

from __future__ import annotations

import hashlib
import json
import math
import random
import re
import sqlite3
from pathlib import Path
from typing import Any

import pytest

from sif.database.schema import SchemaManager
from sif.search.vector import VectorSearcher


EMBEDDING_DIM = 32

# Lowercased text splits on non-alphanumeric boundaries; contiguous CJK
# runs stay whole so a Chinese phrase like 机器学习 is exactly one token,
# mirroring how the FTS porter tokenizer treats it (research Pitfall 3).
_TOKEN_RE = re.compile(r"[a-z0-9]+|[一-鿿]+")


def _tokenize(text: str) -> list[str]:
    """Tokenize lowercased text into ASCII words and whole CJK runs."""
    return _TOKEN_RE.findall(text.lower())


class ConceptEmbedder:
    """Deterministic token-bag embedder satisfying the ``Embedder`` protocol.

    Each token hashes (blake2b) to a seed for ``random.Random``; drawing
    EMBEDDING_DIM floats from that seed and L2-normalizing yields a stable
    unit vector per token. A text embeds to the L2-normalized sum of its
    token vectors, so query/document similarity is driven purely by shared
    tokens — reproducible on every platform, no model download (D-01).
    """

    def __init__(self) -> None:
        self._cache: dict[str, list[float]] = {}
        self._token_cache: dict[str, list[float]] = {}

    @staticmethod
    def _unit_vector(seed_int: int) -> list[float]:
        """Draw EMBEDDING_DIM floats from a seeded RNG and L2-normalize."""
        rng = random.Random(seed_int)
        vec = [rng.random() for _ in range(EMBEDDING_DIM)]
        norm = math.sqrt(sum(v * v for v in vec))
        return [v / norm for v in vec]

    def _token_vector(self, token: str) -> list[float]:
        """Stable unit vector for one token (cached)."""
        if token not in self._token_cache:
            digest = hashlib.blake2b(token.encode("utf-8"), digest_size=8).digest()
            self._token_cache[token] = self._unit_vector(int.from_bytes(digest, "big"))
        return self._token_cache[token]

    def embed(self, text: str) -> list[float]:
        """Embed one text as the normalized sum of its token vectors."""
        if text in self._cache:
            return self._cache[text]
        tokens = _tokenize(text)
        if tokens:
            summed = [0.0] * EMBEDDING_DIM
            for token in tokens:
                token_vec = self._token_vector(token)
                for i, value in enumerate(token_vec):
                    summed[i] += value
            norm = math.sqrt(sum(v * v for v in summed))
            result = [v / norm for v in summed]
        else:
            # All-zero text (no tokens): a deterministic fixed unit vector.
            result = self._unit_vector(0)
        self._cache[text] = result
        return result

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Embed multiple texts, one vector per text."""
        return [self.embed(text) for text in texts]

    @property
    def dimension(self) -> int:
        """Embedding dimensionality (stable across calls)."""
        return EMBEDDING_DIM


def build_bench_db(
    corpus_root: Path,
    embedder: ConceptEmbedder,
    embedding_dim: int = EMBEDDING_DIM,
) -> sqlite3.Connection:
    """Build the deterministic in-memory bench index from committed corpus files.

    Real SchemaManager schema with FTS populated through the insert triggers
    and one vec0 embedding per document chunk; documents carry fixed ids
    (``doc-000`` style) in sorted relative-path order and paths that resolve
    under ``corpus_root``, so path-keyed relevance joins without depending on
    random UUID document ids (research Pitfall 4). Skips the test when the
    sqlite-vec extension is unavailable (same discipline as the hybrid
    golden fixture).
    """
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    try:
        conn.enable_load_extension(True)
        import sqlite_vec

        sqlite_vec.load(conn)
        conn.enable_load_extension(False)
    except Exception:
        conn.close()
        pytest.skip("sqlite-vec not available")

    root = corpus_root.resolve()
    SchemaManager(conn, embedding_dim=embedding_dim).create_all()
    now = "2026-11-08T00:00:00+00:00"
    # include_by_default=1: CollectionRepository.list_enabled filters on that
    # column, so the bench collection must match the default search scope.
    conn.execute(
        "INSERT INTO collections (id, name, path, include_by_default, created_at, updated_at)"
        " VALUES ('bench', 'bench', ?, 1, ?, ?)",
        (str(root), now, now),
    )
    md_files = sorted(root.rglob("*.md"), key=lambda p: p.relative_to(root).as_posix())
    embeddings: list[tuple[str, str, str, list[float]]] = []
    for index, path in enumerate(md_files):
        text = path.read_text(encoding="utf-8")
        title = next(
            (line[2:].strip() for line in text.splitlines() if line.startswith("# ")),
            path.stem,
        )
        doc_id = f"doc-{index:03d}"
        chunk_id = f"chunk-{index:03d}"
        conn.execute(
            "INSERT INTO documents (id, collection_id, path, filename, title, content,"
            " checksum, mtime, created_at, updated_at)"
            " VALUES (?, 'bench', ?, ?, ?, ?, ?, 1.0, ?, ?)",
            (
                doc_id,
                str(path),
                path.name,
                title,
                text,
                hashlib.sha256(text.encode("utf-8")).hexdigest(),
                now,
                now,
            ),
        )
        conn.execute(
            "INSERT INTO document_chunks (id, document_id, sequence, content, created_at)"
            " VALUES (?, ?, 0, ?, ?)",
            (chunk_id, doc_id, text, now),
        )
        embeddings.append((f"embed-{index:03d}", doc_id, chunk_id, embedder.embed(text)))
    VectorSearcher(conn, embedding_dim=embedding_dim).add_embeddings_batch(embeddings)
    return conn


def load_fixture_queries(fixture_path: Path) -> dict[str, Any]:
    """Load a bench fixture JSON file (thin loader used by tests)."""
    with open(fixture_path, encoding="utf-8") as f:
        return json.load(f)
