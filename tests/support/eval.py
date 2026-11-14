"""Deterministic personal-eval DB support (Phase 18, EVAL-01).

``build_personal_db`` raises a real file-backed index with the production
schema (FTS triggers + vec0 embeddings) from curated deterministic documents
so the CLI can be exercised against a genuine 60-document corpus. It reuses
``ConceptEmbedder`` from the bench support instead of duplicating it, and
skips when ``sqlite-vec`` is unavailable (same discipline as
``build_bench_db``).
"""

from __future__ import annotations

import hashlib
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from sif.core.models import QueryLogEntry
from sif.database.repositories import QueryLogRepository
from sif.database.schema import SchemaManager
from sif.search.vector import VectorSearcher
from tests.support.bench import EMBEDDING_DIM, ConceptEmbedder


COLLECTION_ID = "personal"
_NOW = "2026-11-14T00:00:00+00:00"


def _default_titles(count: int) -> list[str]:
    """One distinct, query-safe title per document."""
    return [f"Personal note {index:03d} about topic {index}" for index in range(count)]


def _body(title: str, index: int) -> str:
    """A deterministic body whose candidate sentence starts beyond 200 chars.

    The opening window (title + introductory context) is deliberately longer
    than 200 characters so the body leg picks the later "Document body"
    sentence instead of echoing the title (research Open Question 9).
    """
    return (
        f"{title}. Introductory context for note {index:03d} spans a range of "
        "personal knowledge management topics, local retrieval workflows, and "
        "evaluation methodology in enough detail to push the candidate prose "
        f"past the opening window. Document body {index:03d} discusses local "
        "search quality, retrieval metrics, deterministic sampling, and "
        "evaluation on a personal corpus."
    )


def build_personal_db(
    db_path: Path,
    *,
    documents: int = 60,
    titles: list[str] | None = None,
    bodies: list[str] | None = None,
    embedder: ConceptEmbedder | None = None,
    embedding_dim: int = EMBEDDING_DIM,
) -> Path:
    """Build a real on-disk personal index with ``documents`` curated docs.

    One collection (enabled by default), unique titles by default, bodies
    long enough for the body leg (or explicit ``bodies`` for split-control
    fixtures), sha256 checksums, one chunk per document, and one vec0
    embedding per chunk through ``ConceptEmbedder``. The on-disk vec0
    dimension matters: ``Database.init_schema`` (called by
    ``open_initialized_database``) validates it against
    ``get_settings().embedding_dim``, so tests must patch settings with the
    same ``embedding_dim`` used here.
    """
    if titles is not None and len(titles) != documents:
        raise ValueError("titles must have exactly one entry per document")
    if bodies is not None and len(bodies) != documents:
        raise ValueError("bodies must have exactly one entry per document")
    resolved_titles = titles if titles is not None else _default_titles(documents)
    model = embedder or ConceptEmbedder()
    db_path = Path(db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    try:
        conn.enable_load_extension(True)
        import sqlite_vec

        sqlite_vec.load(conn)
        conn.enable_load_extension(False)
    except Exception:
        conn.close()
        pytest.skip("sqlite-vec not available")

    corpus_dir = db_path.parent / "corpus"
    try:
        SchemaManager(conn, embedding_dim=embedding_dim).create_all()
        conn.execute(
            "INSERT INTO collections (id, name, path, include_by_default, created_at, updated_at)"
            " VALUES (?, ?, ?, 1, ?, ?)",
            (COLLECTION_ID, COLLECTION_ID, str(corpus_dir), _NOW, _NOW),
        )
        embeddings: list[tuple[str, str, str, list[float]]] = []
        for index in range(documents):
            title = resolved_titles[index]
            body = bodies[index] if bodies is not None else _body(title, index)
            doc_id = f"doc-{index:03d}"
            chunk_id = f"chunk-{index:03d}"
            path = corpus_dir / f"{index:03d}.md"
            conn.execute(
                "INSERT INTO documents (id, collection_id, path, filename, title, content,"
                " checksum, file_size, mtime, created_at, updated_at)"
                " VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1.0, ?, ?)",
                (
                    doc_id,
                    COLLECTION_ID,
                    str(path),
                    path.name,
                    title,
                    body,
                    hashlib.sha256(body.encode()).hexdigest(),
                    len(body.encode()),
                    _NOW,
                    _NOW,
                ),
            )
            conn.execute(
                "INSERT INTO document_chunks (id, document_id, sequence, content, created_at)"
                " VALUES (?, ?, 0, ?, ?)",
                (chunk_id, doc_id, body, _NOW),
            )
            embeddings.append((f"embed-{index:03d}", doc_id, chunk_id, model.embed(body)))
        VectorSearcher(conn, embedding_dim=embedding_dim).add_embeddings_batch(embeddings)
        conn.commit()
    finally:
        conn.close()
    return db_path


def seed_query_log(conn: sqlite3.Connection, queries: list[str]) -> None:
    """Seed ``query_log`` rows through the repository's capped write path.

    ``keep=500`` matches the production trim-in-write cap; timestamps rise
    monotonically so ``history()`` ordering is deterministic. Never stores
    document content (query text only).
    """
    repo = QueryLogRepository(conn)
    base = datetime(2026, 11, 14, tzinfo=timezone.utc)
    for index, query in enumerate(queries):
        repo.add(
            QueryLogEntry(
                id=f"log-{index:03d}",
                query=query,
                result_count=index,
                collections=[],
                created_at=base + timedelta(minutes=index),
            ),
            keep=500,
        )
    conn.commit()
