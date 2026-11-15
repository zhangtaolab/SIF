"""Streaming embed writer: chunk, embed outside transactions, one short commit.

SCALE-03 (D-15/D-16/D-17/D-18): every document is chunked and embedded with
NO database transaction open, then persisted in exactly one short
transaction that carries its chunks, vectors, the ``embedded_documents``
shadow row, and (on an index's first vector write) the embedder identity.
Memory is bounded by one document's chunks plus one model batch, and the
write lock is held only for the inserts.

Batch-boundary validation is the qmd #897 lesson: a model batch whose count,
dimensions, finiteness, or norm is wrong is systemic — nothing from that
batch or document is persisted, and the caller aborts after prior document
commits. Both ``embed_cmd`` and the watcher route through this writer, so
completeness, sanity, and shadow maintenance cannot diverge (D-18).
"""

from __future__ import annotations

import math
import sqlite3
from collections.abc import Iterable
from dataclasses import replace
from typing import TYPE_CHECKING

from sif.core.models import Document, DocumentChunk
from sif.database.repositories import DocumentChunkRepository
from sif.embedding.identity import (
    EmbedderIdentity,
    has_stored_vectors,
    identity_matches,
    read_identity,
    write_identity,
)
from sif.models.embedding import EmbeddingOutputError


if TYPE_CHECKING:
    from sif.embedding.manager import EmbeddingManager
    from sif.indexing.chunker import Chunker
    from sif.search.vector import VectorSearcher


# L2-norm tolerance for a normalized embedder's vectors (D-17).
NORM_TOLERANCE = 1e-3


class SystemicEmbedError(RuntimeError):
    """A batch-boundary validation failure that must abort the embed run."""


def _batches(chunks: list[DocumentChunk], size: int) -> Iterable[list[DocumentChunk]]:
    """Yield contiguous batches of at most ``size`` chunks in order."""
    for start in range(0, len(chunks), size):
        yield chunks[start : start + size]


def _describe(identity: EmbedderIdentity, document_path: str, batch_index: int) -> str:
    """Shared error prefix: identity fingerprint, document, and batch."""
    return (
        f"identity {identity.display_fingerprint()} ({identity.cache_model_id}), "
        f"document {document_path}, batch {batch_index}"
    )


def _chunk_where(chunk: DocumentChunk, position: int) -> str:
    """Name the offending chunk within its batch."""
    return f"position {position}, chunk {chunk.id} (sequence {chunk.sequence})"


def _finite_values(vector: list[float]) -> list[float] | None:
    """Coerce a vector to floats, or None when any value is not numeric."""
    try:
        return [float(value) for value in vector]
    except (TypeError, ValueError):
        return None


def validate_batch(
    vectors: list[list[float]],
    chunks: list[DocumentChunk],
    identity: EmbedderIdentity,
    document_path: str,
    batch_index: int,
) -> None:
    """Reject a structurally invalid model batch before it can persist (D-17).

    Checks output count, per-vector dimension, finiteness, and L2 norm
    (unit when the identity declares normalization, non-zero otherwise).
    Any violation raises :class:`SystemicEmbedError` naming the identity, the
    document, the batch, the position within the batch, and the chunk, so the
    abort is actionable and no garbage vector is ever stored or cached.
    """
    context = _describe(identity, document_path, batch_index)
    if len(vectors) != len(chunks):
        raise SystemicEmbedError(
            "Embedding batch validation failed: model returned "
            f"{len(vectors)} vectors for {len(chunks)} chunks; {context}."
        )

    for position, (vector, chunk) in enumerate(zip(vectors, chunks, strict=True)):
        where = f"{context}, {_chunk_where(chunk, position)}"
        if len(vector) != identity.dimension:
            raise SystemicEmbedError(
                "Embedding batch validation failed: vector has "
                f"{len(vector)} dimensions, expected {identity.dimension}; {where}."
            )
        values = _finite_values(vector)
        if values is None or not all(math.isfinite(value) for value in values):
            raise SystemicEmbedError(
                f"Embedding batch validation failed: non-finite vector value; {where}."
            )
        norm = math.sqrt(sum(value * value for value in values))
        if identity.normalized:
            if abs(norm - 1.0) > NORM_TOLERANCE:
                raise SystemicEmbedError(
                    "Embedding batch validation failed: L2 norm "
                    f"{norm:.6f} is not 1.0 within {NORM_TOLERANCE}; {where}."
                )
        elif norm <= 0.0:
            raise SystemicEmbedError(
                f"Embedding batch validation failed: zero-norm vector; {where}."
            )


class StreamingEmbedWriter:
    """Chunk, embed, and persist one document per short transaction.

    The writer never opens a transaction before or during model calls. The
    single ``with conn:`` block per document deletes the document's previous
    chunks/vectors (delete-before-insert, self-healing re-chunk), inserts the
    fresh rows, maintains the derived shadow through ``VectorSearcher``, and
    writes the identity on the index's first successful vector write — after
    re-validating the stored provenance inside that same transaction, so a
    stale first-write decision cannot mix two models' vectors.

    ``identity`` is optional only to keep injected manager doubles inert:
    every production host hands over a real ``EmbedderIdentity``, while test
    doubles without one keep the pre-Phase-21 write path (no identity row, no
    structural batch validation). A real writer never skips validation.
    """

    def __init__(  # noqa: PLR0913 - one writer owns the index/collaborator set
        self,
        conn: sqlite3.Connection,
        manager: EmbeddingManager,
        chunker: Chunker,
        vector_searcher: VectorSearcher,
        identity: EmbedderIdentity | None,
        *,
        batch_size: int,
        write_identity: bool,
    ) -> None:
        """Bind the writer to one index connection and its collaborators."""
        if batch_size < 1:
            raise ValueError(f"batch_size must be >= 1, got {batch_size}")
        self._conn = conn
        self._manager = manager
        self._chunker = chunker
        self._searcher = vector_searcher
        self._identity = identity
        self._batch_size = batch_size
        self._write_identity = bool(write_identity and identity is not None)
        self._chunk_repo = DocumentChunkRepository(conn)

    @property
    def identity_pending(self) -> bool:
        """Whether the first vector write still owes the index its identity row."""
        return self._write_identity

    def embed_document(self, doc: Document) -> int:
        """Embed and persist one document; return the committed chunk count.

        Chunking and embedding run outside any transaction (the invariant the
        embed tests record as ``conn.in_transaction is False`` at every model
        call). A whitespace-only or chunkless document writes nothing at all,
        including no shadow row, and does not consume the identity-write flag.
        """
        chunks = self._chunk_document(doc)
        if not chunks:
            return 0

        vectors: list[list[float]] = []
        for batch_index, batch in enumerate(_batches(chunks, self._batch_size)):
            try:
                response = self._manager.embed_documents([chunk.content for chunk in batch])
            except EmbeddingOutputError as e:
                # WR-02: the manager validates model output before
                # ``validate_batch`` can see it. That class is systemic — the
                # model, not the document, is broken — so translate it into
                # the host's abort/disable path instead of a document-local
                # failure the watcher would retry forever.
                raise SystemicEmbedError(
                    f"Embedding batch validation failed for document {doc.path}, "
                    f"batch {batch_index}: {e}"
                ) from e
            batch_vectors = list(response.embeddings)
            if self._identity is not None:
                validate_batch(batch_vectors, batch, self._identity, doc.path, batch_index)
            vectors.extend(batch_vectors)

        # ONE short write transaction per document: every derived row
        # (chunks, vectors, shadow, identity) commits or rolls back together.
        claim_identity = self._write_identity
        with self._conn:
            if claim_identity:
                # D-02/CR-02: the host checked the embeddings-empty state
                # under the index flock, but the decision can be stale (a
                # writer that ignored the flock, or one that outlived its
                # wait deadline, may have committed since). BEGIN IMMEDIATE
                # holds SQLite's write lock across the provenance re-read and
                # the identity write, so the claim is atomic against every
                # other writer.
                self._conn.execute("BEGIN IMMEDIATE")
                self._claim_identity_in_transaction()
            self._chunk_repo.delete_by_document(doc.id)
            self._searcher.delete_embeddings_by_document(doc.id)
            for chunk in chunks:
                chunk.document_id = doc.id
                self._chunk_repo.create(chunk)
            self._searcher.add_embeddings_batch(
                [
                    (chunk.id, doc.id, chunk.id, vector)
                    for chunk, vector in zip(chunks, vectors, strict=True)
                ]
            )
        if claim_identity:
            # WR-06: clear the flag only after __exit__ committed. A failed
            # commit rolls the identity row back with the vectors, and the
            # still-pending claim makes the next document retry it instead of
            # silently committing vectors with no provenance.
            self._write_identity = False

        return len(chunks)

    def _claim_identity_in_transaction(self) -> None:
        """Claim the first vector write's identity, re-validating provenance.

        Must run after an explicit ``BEGIN IMMEDIATE`` so the read of the
        stored vectors/identity and the identity write are atomic against
        every other writer. A populated index is adopted only when its
        stored identity matches this writer's; claiming it for a different
        model would put two vector spaces in one vec0 table (the EMB-01
        trap). Anything else aborts systemically so the host reports one
        actionable failure instead of retrying.

        A still-empty index keeps D-02's rule: a stale identity row never
        blocks the first vector write, which overwrites it as
        ``source="verified"``.
        """
        assert self._identity is not None  # guarded by the constructor
        if not has_stored_vectors(self._conn):
            write_identity(self._conn, replace(self._identity, source="verified"))
            return

        stored = read_identity(self._conn)
        if stored is None:
            raise SystemicEmbedError(
                "Refusing to claim the embedder identity: vectors with no identity "
                "appeared concurrently; rerun `sif index embed`."
            )
        if not identity_matches(stored, self._identity):
            raise SystemicEmbedError(
                "Embedder identity mismatch while claiming the first vector write: "
                f"stored {stored.display_fingerprint()} ({stored.cache_model_id}) vs "
                f"current {self._identity.display_fingerprint()} "
                f"({self._identity.cache_model_id}). This index now holds another "
                "model's vectors; restore that model or run `sif index embed --force`."
            )

    def _chunk_document(self, doc: Document) -> list[DocumentChunk]:
        """Chunk a document, dropping empty text and renumbering contiguously."""
        chunks = [chunk for chunk in self._chunker.chunk(doc.content) if chunk.content.strip()]
        for sequence, chunk in enumerate(chunks):
            chunk.sequence = sequence
        return chunks
