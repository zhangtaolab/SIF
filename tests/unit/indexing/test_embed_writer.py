"""Tests for the streaming embed writer (SCALE-03, D-15/D-17/D-18).

A real ``Database`` with a real sqlite-vec table backs every test, and a
fake manager records ``conn.in_transaction`` at each model call. The writer
must compute embeddings outside any transaction and persist each document in
exactly one short write transaction.
"""

from __future__ import annotations

import math
import sqlite3
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

import pytest

from sif.core.models import Collection, Document, DocumentChunk
from sif.database.database import Database
from sif.database.repositories import CollectionRepository, DocumentRepository
from sif.embedding.identity import EmbedderIdentity, build_identity, read_identity, write_identity
from sif.embedding.prompts import PromptScheme
from sif.indexing.embed_writer import (
    NORM_TOLERANCE,
    StreamingEmbedWriter,
    SystemicEmbedError,
)
from sif.models.embedding import EmbeddingConfig, ModelType
from sif.search.vector import VectorSearcher


DIM = 8


class _IdentityModel:
    """Loaded-model double exposing only the identity dimension."""

    def __init__(self, dimension: int) -> None:
        self.dimension = dimension


def _unit_vector(dim: int = DIM) -> list[float]:
    """A deterministic unit-L2 vector of ``dim`` dimensions."""
    component = 1.0 / math.sqrt(dim)
    return [component] * dim


def _identity(
    model_name: str = "test",
    dim: int = DIM,
    *,
    normalized: bool = True,
) -> EmbedderIdentity:
    """Build a real embedder identity for the fake loaded model."""
    base = build_identity(
        EmbeddingConfig(
            model_type=ModelType.MODELSCOPE,
            model_name=model_name,
            embedding_dim=dim,
        ),
        _IdentityModel(dim),
        PromptScheme(None, None, True),
    )
    return base if normalized else replace(base, normalized=False)


class _FixedChunker:
    """Return one chunk per supplied text, ignoring the document body."""

    def __init__(self, texts: list[str]) -> None:
        self._texts = texts
        self.last_chunks: list[DocumentChunk] = []

    def chunk(self, text: str) -> list[DocumentChunk]:  # noqa: ARG002
        """Build fresh chunk objects so re-embedding gets fresh ids."""
        self.last_chunks = [
            DocumentChunk(
                content=content,
                sequence=0,
                start_pos=0,
                end_pos=len(content),
            )
            for content in self._texts
        ]
        return self.last_chunks


class _OneChunkChunker:
    """Return exactly one chunk holding the document body."""

    def chunk(self, text: str) -> list[DocumentChunk]:
        """Build one chunk from the text."""
        return [DocumentChunk(content=text, sequence=0, start_pos=0, end_pos=len(text))]


class _RecordingManager:
    """Fake manager that proves embeddings never run inside a transaction."""

    def __init__(self, conn: sqlite3.Connection, vectors_for=None) -> None:
        self._conn = conn
        self._vectors_for = vectors_for or (lambda texts: [_unit_vector() for _ in texts])
        self.calls: list[list[str]] = []
        self.transaction_flags: list[bool] = []

    def embed_documents(self, texts: list[str]) -> SimpleNamespace:
        """Record the call and its transaction state, then return vectors."""
        flag = self._conn.in_transaction
        self.transaction_flags.append(flag)
        if flag:
            raise AssertionError("embedding compute ran inside a database transaction")
        self.calls.append(list(texts))
        return SimpleNamespace(embeddings=self._vectors_for(list(texts)))


def _setup(tmp_path: Path) -> tuple[Database, Collection, Document, VectorSearcher]:
    """Create a real index with one collection and one document."""
    db = Database(tmp_path / "index.db")
    db.init_schema(embedding_dim=DIM)
    with db.connection:
        coll = Collection(name="notes", path="/notes")
        CollectionRepository(db.connection).create(coll)
        doc = Document(
            path="/notes/a.md",
            collection_id=coll.id,
            content="alpha body",
            title="A",
        )
        DocumentRepository(db.connection).create(doc)
    try:
        searcher = VectorSearcher(db.connection, DIM)
    except RuntimeError as e:  # pragma: no cover - host without sqlite-vec
        db.close()
        pytest.skip(f"sqlite-vec unavailable: {e}")
    return db, coll, doc, searcher


def _counts(conn: sqlite3.Connection, document_id: str) -> tuple[int, int, int]:
    """Return (chunks, vectors, shadow rows) for one document."""
    chunks = conn.execute(
        "SELECT COUNT(*) FROM document_chunks WHERE document_id = ?", (document_id,)
    ).fetchone()[0]
    vectors = conn.execute(
        "SELECT COUNT(*) FROM document_embeddings WHERE document_id = ?", (document_id,)
    ).fetchone()[0]
    shadow = conn.execute(
        "SELECT COUNT(*) FROM embedded_documents WHERE document_id = ?", (document_id,)
    ).fetchone()[0]
    return int(chunks), int(vectors), int(shadow)


def test_batches_run_outside_the_transaction_and_commit_once(tmp_path: Path) -> None:
    """Three chunks at batch_size=2: two model batches, one write transaction."""
    db, _coll, doc, searcher = _setup(tmp_path)
    manager = _RecordingManager(db.connection)
    writer = StreamingEmbedWriter(
        db.connection,
        manager,
        _FixedChunker(["one", "two", "three"]),
        searcher,
        _identity(),
        batch_size=2,
        write_identity=False,
    )
    statements: list[str] = []
    db.connection.set_trace_callback(statements.append)
    try:
        written = writer.embed_document(doc)
    finally:
        db.connection.set_trace_callback(None)
        db.close()

    assert written == 3
    assert [len(call) for call in manager.calls] == [2, 1]
    assert manager.transaction_flags == [False, False]
    # Exactly one BEGIN/COMMIT pair for the whole document: every derived row
    # commits together, and no transaction spans a model call.
    begins = [s for s in statements if s.strip().upper().startswith("BEGIN")]
    commits = [s for s in statements if s.strip().upper().startswith("COMMIT")]
    assert len(begins) == 1
    assert len(commits) == 1
    assert _counts(db.connection, doc.id) == (3, 3, 1)


def test_first_vector_write_certifies_the_identity(tmp_path: Path) -> None:
    """An embeddings-empty index writes source=verified on the first commit."""
    db, _coll, doc, searcher = _setup(tmp_path)
    identity = _identity(model_name="model-a")
    writer = StreamingEmbedWriter(
        db.connection,
        _RecordingManager(db.connection),
        _FixedChunker(["one", "two"]),
        searcher,
        identity,
        batch_size=32,
        write_identity=True,
    )

    assert writer.identity_pending is True
    try:
        assert writer.embed_document(doc) == 2
        stored = read_identity(db.connection)
    finally:
        db.close()

    assert stored is not None
    assert stored.source == "verified"
    assert stored.cache_model_id == identity.cache_model_id
    assert stored.dimension == DIM
    assert writer.identity_pending is False


def test_populated_index_keeps_the_stored_identity(tmp_path: Path) -> None:
    """A writer with write_identity=False never rewrites the stored row."""
    db, _coll, doc, searcher = _setup(tmp_path)
    stored_identity = _identity(model_name="stored-model")
    with db.connection:
        searcher.add_embeddings_batch([("c-seed", doc.id, "c-seed", _unit_vector())])
        write_identity(db.connection, stored_identity)

    writer = StreamingEmbedWriter(
        db.connection,
        _RecordingManager(db.connection),
        _FixedChunker(["fresh"]),
        searcher,
        _identity(model_name="current-model"),
        batch_size=32,
        write_identity=False,
    )
    try:
        writer.embed_document(doc)
        stored = read_identity(db.connection)
    finally:
        db.close()

    assert stored is not None
    assert stored.cache_model_id == stored_identity.cache_model_id
    assert stored.source == stored_identity.source


def test_second_embed_of_the_same_document_is_idempotent(tmp_path: Path) -> None:
    """Delete-before-insert replaces rows instead of appending duplicates."""
    db, _coll, doc, searcher = _setup(tmp_path)
    writer = StreamingEmbedWriter(
        db.connection,
        _RecordingManager(db.connection),
        _FixedChunker(["one", "two"]),
        searcher,
        _identity(),
        batch_size=32,
        write_identity=False,
    )

    try:
        writer.embed_document(doc)
        first = _counts(db.connection, doc.id)
        first_ids = {
            row[0] for row in db.connection.execute("SELECT chunk_id FROM document_embeddings")
        }
        writer.embed_document(doc)
        second = _counts(db.connection, doc.id)
        second_ids = {
            row[0] for row in db.connection.execute("SELECT chunk_id FROM document_embeddings")
        }
        live_ids = {
            row[0]
            for row in db.connection.execute(
                "SELECT id FROM document_chunks WHERE document_id = ?", (doc.id,)
            )
        }
    finally:
        db.close()

    assert first == second == (2, 2, 1)
    assert second_ids == live_ids
    assert first_ids.isdisjoint(second_ids)  # freshly re-chunked rows replace the old set


def test_whitespace_only_document_writes_nothing(tmp_path: Path) -> None:
    """Empty/whitespace chunks are rejected before embedding (D-17)."""
    db, _coll, doc, searcher = _setup(tmp_path)
    manager = _RecordingManager(db.connection)
    writer = StreamingEmbedWriter(
        db.connection,
        manager,
        _FixedChunker(["   ", "\n\t", ""]),
        searcher,
        _identity(),
        batch_size=32,
        write_identity=True,
    )

    try:
        written = writer.embed_document(doc)
        counts = _counts(db.connection, doc.id)
        stored = read_identity(db.connection)
    finally:
        db.close()

    assert written == 0
    assert counts == (0, 0, 0)
    assert stored is None
    assert writer.identity_pending is True
    assert manager.calls == []


def test_norm_tolerance_is_pinned() -> None:
    """D-17's unit-norm tolerance is a public constant."""
    assert NORM_TOLERANCE == 1e-3


def _garbage_vectors(kind: str, dim: int = DIM) -> list[list[float]]:
    """Build one batch of model output exercising a D-17 garbage class."""
    if kind == "count":
        return []
    if kind == "dimension":
        return [[0.0] * (dim - 1)]
    if kind == "nan":
        return [[float("nan")] + [0.0] * (dim - 1)]
    if kind == "inf":
        return [[float("inf")] + [0.0] * (dim - 1)]
    if kind == "norm":
        return [[0.5] * dim]
    return [[0.0] * dim]  # zero_norm


@pytest.mark.parametrize("kind", ["count", "dimension", "nan", "inf", "norm", "zero_norm"])
def test_garbage_batch_sanity_aborts_and_persists_nothing(tmp_path: Path, kind: str) -> None:
    """D-17: every garbage class raises systemically and leaves no row."""
    db, _coll, doc, searcher = _setup(tmp_path)
    identity = _identity(normalized=(kind != "zero_norm"))
    chunker = _FixedChunker(["garbage vector"])
    writer = StreamingEmbedWriter(
        db.connection,
        _RecordingManager(db.connection, lambda _texts: _garbage_vectors(kind, identity.dimension)),
        chunker,
        searcher,
        identity,
        batch_size=32,
        write_identity=True,
    )

    with pytest.raises(SystemicEmbedError) as excinfo:
        writer.embed_document(doc)

    message = str(excinfo.value)
    assert identity.display_fingerprint() in message
    assert doc.path in message
    assert "batch 0" in message
    if kind != "count":
        assert "position 0" in message
        assert chunker.last_chunks[0].id in message

    try:
        counts = _counts(db.connection, doc.id)
        stored = read_identity(db.connection)
    finally:
        db.close()

    assert counts == (0, 0, 0)
    assert stored is None
    assert writer.identity_pending is True


def test_garbage_sanity_after_a_committed_document_leaves_it_intact(tmp_path: Path) -> None:
    """An aborted document never rolls back or hides an earlier commit."""
    db, coll, doc_a, searcher = _setup(tmp_path)
    doc_b = Document(
        path="/notes/b.md",
        collection_id=coll.id,
        content="beta body",
        title="B",
    )
    with db.connection:
        DocumentRepository(db.connection).create(doc_b)

    call_count = 0

    def vectors_for(texts: list[str]) -> list[list[float]]:
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return [_unit_vector() for _ in texts]
        return [[float("nan")] * DIM for _ in texts]

    writer = StreamingEmbedWriter(
        db.connection,
        _RecordingManager(db.connection, vectors_for),
        _OneChunkChunker(),
        searcher,
        _identity(),
        batch_size=32,
        write_identity=True,
    )

    try:
        assert writer.embed_document(doc_a) == 1
        with pytest.raises(SystemicEmbedError):
            writer.embed_document(doc_b)
        counts_a = _counts(db.connection, doc_a.id)
        counts_b = _counts(db.connection, doc_b.id)
        stored = read_identity(db.connection)
    finally:
        db.close()

    assert counts_a == (1, 1, 1)
    assert counts_b == (0, 0, 0)
    assert stored is not None
    assert stored.source == "verified"
    assert writer.identity_pending is False
