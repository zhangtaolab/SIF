"""Integration tests for idempotent `sif index embed` runs (G-03-3).

Reproduces the UAT evidence from 03-UAT.md test 3 inverted: two embed runs on
one collection must leave document_embeddings with exactly one row per live
chunk, and vector search must never surface a chunk once per historical run
(the observed 21-rows-vs-3-chunks, document-times-7 symptom). Since CORR-02
the default vector page is one row per document (chunk_matches counts its
live chunks); per_chunk=True restores one row per live chunk.
"""

from __future__ import annotations

import json
import math
import sqlite3
from pathlib import Path
from unittest.mock import MagicMock, patch

from click.testing import CliRunner

from sif.cli.commands.index import embed_cmd, update_cmd
from sif.config.settings import Settings
from sif.core.models import SearchOptions, compute_checksum
from sif.embedding.identity import build_identity, read_identity
from sif.embedding.prompts import PromptScheme
from sif.models.embedding import EmbeddingConfig, ModelType


DIM = 8


class _IdentityModel:
    """Loaded-model double exposing only the identity dimension."""

    def __init__(self, dimension: int) -> None:
        self.dimension = dimension


def _identity(model_name: str = "test", dim: int = DIM):
    """Build a real embedder identity for the fake loaded model."""
    return build_identity(
        EmbeddingConfig(
            model_type=ModelType.MODELSCOPE,
            model_name=model_name,
            embedding_dim=dim,
        ),
        _IdentityModel(dim),
        PromptScheme(None, None, True),
    )


def _unit_vector(dim: int = DIM) -> list[float]:
    """A deterministic unit-L2 vector of ``dim`` dimensions."""
    component = 1.0 / math.sqrt(dim)
    return [component] * dim


def _make_manager_mock() -> tuple[MagicMock, list[list[list[float]]]]:
    """Build a mocked EmbeddingManager producing deterministic DIM-length vectors.

    Returns the manager mock and a log of per-call vector batches so tests can
    query the store with the exact vectors a specific run inserted.
    """
    manager = MagicMock()
    manager.get_model_info.return_value = {"loaded": True, "embedding_dim": DIM}
    vector_log: list[list[list[float]]] = []

    def fake_embed(texts: list[str], **_kwargs: object) -> MagicMock:
        vectors = []
        for i in range(len(texts)):
            vec = [0.0] * DIM
            vec[i % DIM] = 1.0
            vec[(i + 1) % DIM] = 0.5
            # Per-call offset makes each run's vectors distinguishable.
            vec[DIM - 1] += len(vector_log) * 0.01
            norm = math.sqrt(sum(value * value for value in vec))
            vectors.append([value / norm for value in vec])
        vector_log.append(vectors)
        return MagicMock(embeddings=vectors)

    manager.embed_documents.side_effect = fake_embed
    return manager, vector_log


def _streaming_manager(
    identity,
    *,
    failure_at: int | None = None,
) -> MagicMock:
    """Mock manager with a real identity, unit vectors, and optional failure."""
    manager = MagicMock()
    manager.get_model_info.return_value = {"loaded": True, "embedding_dim": identity.dimension}
    manager.get_identity.return_value = identity
    calls: list[list[str]] = []

    def fake_embed_documents(texts: list[str], **_kwargs: object) -> MagicMock:
        calls.append(list(texts))
        if failure_at is not None and len(calls) == failure_at:
            raise RuntimeError("injected embed failure")
        return MagicMock(embeddings=[_unit_vector(identity.dimension) for _ in texts])

    manager.embed_documents.side_effect = fake_embed_documents
    manager.embed_documents.calls = calls
    return manager


def _seed_collection(db_path: Path, settings: Settings) -> str:
    """Seed one collection with one multi-section document; return the document id."""
    from sif.core.models import Collection, Document
    from sif.database.database import Database
    from sif.database.repositories import CollectionRepository, DocumentRepository

    db = Database(db_path)
    with patch("sif.config.settings.get_settings", return_value=settings):
        db.init_schema()  # creates the vec0 table with the test embedding_dim
        with db.connection:
            coll_repo = CollectionRepository(db.connection)
            doc_repo = DocumentRepository(db.connection)
            coll = Collection(name="notes", path="/notes", description="idempotency test")
            coll_repo.create(coll)
            sections = [
                f"# Section {i}\n\n" + (f"Paragraph text for section {i}. " * 40)
                for i in range(1, 4)
            ]
            doc = Document(
                path="/notes/a.md",
                collection_id=coll.id,
                content="\n\n".join(sections),
                title="A",
            )
            doc_repo.create(doc)
            doc_id = doc.id
    db.close()
    return doc_id


def _store_state(db_path: Path) -> tuple[int, int, set[str], set[str]]:
    """Return (embedding_count, live_chunk_count, embedding_chunk_ids, live_chunk_ids)."""
    import sqlite_vec

    conn = sqlite3.connect(str(db_path))
    try:
        conn.enable_load_extension(True)
        sqlite_vec.load(conn)
        conn.enable_load_extension(False)
        emb_count = conn.execute("SELECT COUNT(*) FROM document_embeddings").fetchone()[0]
        chunk_count = conn.execute("SELECT COUNT(*) FROM document_chunks").fetchone()[0]
        emb_ids = {row[0] for row in conn.execute("SELECT chunk_id FROM document_embeddings")}
        chunk_ids = {row[0] for row in conn.execute("SELECT id FROM document_chunks")}
    finally:
        conn.close()
    return emb_count, chunk_count, emb_ids, chunk_ids


def _test_settings() -> Settings:
    """Build hermetic test settings with the fake embedding dimension."""
    return Settings(embedding_dim=DIM, model_name="test", cache_embeddings=False)


def _invoke_embed(
    db_path: Path,
    manager: MagicMock,
    settings: Settings,
    args: list[str],
) -> object:
    """Invoke embed_cmd against the real database with the mocked manager."""
    runner = CliRunner()
    with (
        patch("sif.config.settings.get_settings", return_value=settings),
        patch("sif.embedding.manager.EmbeddingManager.from_settings", return_value=manager),
    ):
        return runner.invoke(embed_cmd, args, obj={"index_path": db_path})


def _delenv_settings_vars(monkeypatch) -> None:
    """Keep Settings construction hermetic against a developer shell (03-REVIEW WR-10/11)."""
    for var in ("SIF_EMBEDDING_DIM", "SIF_MODEL_TYPE", "SIF_MODEL_NAME"):
        monkeypatch.delenv(var, raising=False)


def _seed_collection_dir(db_path: Path, settings: Settings, coll_path: str) -> str:
    """Seed one collection pointing at a real directory; return the collection id."""
    from sif.core.models import Collection
    from sif.database.database import Database
    from sif.database.repositories import CollectionRepository

    db = Database(db_path)
    with patch("sif.config.settings.get_settings", return_value=settings):
        db.init_schema()
        with db.connection:
            coll_repo = CollectionRepository(db.connection)
            coll = Collection(name="notes", path=coll_path)
            coll_repo.create(coll)
            coll_id = coll.id
    db.close()
    return coll_id


def _invoke_update(db_path: Path, settings: Settings, args: list[str]) -> object:
    """Invoke update_cmd against the real database."""
    runner = CliRunner()
    with patch("sif.config.settings.get_settings", return_value=settings):
        return runner.invoke(update_cmd, args, obj={"index_path": db_path})


def _seed_two_collections(db_path: Path, settings: Settings, good_dir: Path, bad_dir: Path) -> None:
    """Seed two collections ('a-good', 'b-bad') with one document each on disk."""
    from sif.core.models import Collection, Document
    from sif.database.database import Database
    from sif.database.repositories import CollectionRepository, DocumentRepository

    good_dir.mkdir()
    bad_dir.mkdir()
    db = Database(db_path)
    with patch("sif.config.settings.get_settings", return_value=settings):
        db.init_schema()
        with db.connection:
            coll_repo = CollectionRepository(db.connection)
            doc_repo = DocumentRepository(db.connection)
            for name, base in (("a-good", good_dir), ("b-bad", bad_dir)):
                coll = Collection(name=name, path=str(base))
                coll_repo.create(coll)
                doc = Document(
                    path=str(base / "doc.md"),
                    collection_id=coll.id,
                    content=f"{name} document text " * 10,
                    title=name,
                )
                doc_repo.create(doc)
    db.close()


class TestEmbedIdempotency:
    """Two consecutive embed runs on one real sqlite-vec database."""

    def test_two_embed_runs_leave_one_row_per_live_chunk(
        self,
        tmp_path: Path,
        monkeypatch,
    ) -> None:
        """The UAT 21-rows-vs-3-chunks evidence inverted: replace, not append."""
        _delenv_settings_vars(monkeypatch)
        db_path = tmp_path / "embed.db"
        settings = _test_settings()
        _seed_collection(db_path, settings)
        manager, _vector_log = _make_manager_mock()

        result1 = _invoke_embed(db_path, manager, settings, [])
        assert result1.exit_code == 0
        emb1, chunks1, emb_ids1, chunk_ids1 = _store_state(db_path)
        assert chunks1 >= 2  # multi-chunk document keeps the invariant non-trivial
        assert emb1 == chunks1
        assert emb_ids1 == chunk_ids1

        result2 = _invoke_embed(db_path, manager, settings, [])
        assert result2.exit_code == 0
        emb2, chunks2, emb_ids2, chunk_ids2 = _store_state(db_path)
        assert chunks2 == chunks1
        assert emb2 == chunks2  # one row per live chunk — never one per historical run
        assert emb_ids2 == chunk_ids2  # every embedding references a live chunk
        # The completed document is skipped, so the second default run leaves
        # the store byte-identical (stronger than replace: no mutation at all).
        # The replace-not-append re-chunk path is covered by --force and the
        # self-heal tests below, which assert fresh chunk-id sets.
        assert (emb2, emb_ids2) == (emb1, emb_ids1)

    def test_vector_search_returns_each_chunk_once_after_two_runs(
        self,
        tmp_path: Path,
        monkeypatch,
    ) -> None:
        """No historical duplicates: one default row per document, one row per
        live chunk in per-chunk mode (CORR-02's contract)."""
        from sif.database.database import Database
        from sif.search.vector import VectorSearcher

        _delenv_settings_vars(monkeypatch)
        db_path = tmp_path / "embed.db"
        settings = _test_settings()
        doc_id = _seed_collection(db_path, settings)
        manager, vector_log = _make_manager_mock()

        assert _invoke_embed(db_path, manager, settings, []).exit_code == 0
        assert _invoke_embed(db_path, manager, settings, []).exit_code == 0

        emb_count, chunk_count, _, _ = _store_state(db_path)
        assert emb_count == chunk_count

        db = Database(db_path)
        try:
            searcher = VectorSearcher(db.connection, embedding_dim=DIM)
            run2_vectors = vector_log[-1]
            results = searcher.search(run2_vectors[0], SearchOptions(limit=chunk_count))
            per_chunk = searcher.search(
                run2_vectors[0],
                SearchOptions(limit=chunk_count, per_chunk=True),
            )
        finally:
            db.close()

        # Default contract: the one document owns a single row whose match
        # count equals its live chunk count — not one row per historical run.
        assert len(results) == 1
        assert results[0].document_id == doc_id
        assert results[0].chunk_matches == chunk_count
        # Escape hatch: every live chunk is individually addressable, once.
        assert len(per_chunk) == chunk_count
        assert {r.document_id for r in per_chunk} == {doc_id}

    def test_default_run_skips_complete_then_force_reembeds_all(
        self,
        tmp_path: Path,
        monkeypatch,
    ) -> None:
        """Default run: zero embed calls on a complete store; --force re-embeds everything."""
        _delenv_settings_vars(monkeypatch)
        db_path = tmp_path / "embed.db"
        settings = _test_settings()
        _seed_collection(db_path, settings)
        manager, _vector_log = _make_manager_mock()

        # Run 1: embed everything
        assert _invoke_embed(db_path, manager, settings, []).exit_code == 0
        assert manager.embed_documents.call_count == 1
        state1 = _store_state(db_path)
        assert state1[0] == state1[1]

        # Run 2 without --force: everything complete -> zero embed calls, nothing mutated
        assert _invoke_embed(db_path, manager, settings, []).exit_code == 0
        assert manager.embed_documents.call_count == 1  # no new embed call
        assert _store_state(db_path) == state1  # counts and chunk-id sets unchanged

        # Run 3 with --force: full re-embed, invariants preserved
        assert _invoke_embed(db_path, manager, settings, ["--force"]).exit_code == 0
        assert manager.embed_documents.call_count == 2  # exactly one more batch
        emb3, chunks3, emb_ids3, chunk_ids3 = _store_state(db_path)
        assert emb3 == chunks3
        assert emb_ids3 == chunk_ids3
        assert emb_ids3.isdisjoint(state1[2])  # re-chunked rows replaced the old set

    def test_default_run_self_heals_partial_state(
        self,
        tmp_path: Path,
        monkeypatch,
    ) -> None:
        """An interrupted run's partial state is detected and re-embedded (D-10 crash-safety)."""
        import sqlite_vec

        _delenv_settings_vars(monkeypatch)
        db_path = tmp_path / "embed.db"
        settings = _test_settings()
        _seed_collection(db_path, settings)
        manager, _vector_log = _make_manager_mock()

        assert _invoke_embed(db_path, manager, settings, []).exit_code == 0
        assert manager.embed_documents.call_count == 1

        # Simulate an interrupted run: one embedding row vanished mid-state
        conn = sqlite3.connect(str(db_path))
        try:
            conn.enable_load_extension(True)
            sqlite_vec.load(conn)
            conn.enable_load_extension(False)
            conn.execute(
                "DELETE FROM document_embeddings WHERE chunk_id = "
                "(SELECT id FROM document_chunks ORDER BY sequence LIMIT 1)"
            )
            conn.commit()
        finally:
            conn.close()
        partial = _store_state(db_path)
        assert partial[0] == partial[1] - 1  # one chunk lacks its embedding

        # The next default run detects the incomplete set and re-embeds it
        assert _invoke_embed(db_path, manager, settings, []).exit_code == 0
        assert manager.embed_documents.call_count == 2
        emb, chunks, emb_ids, chunk_ids = _store_state(db_path)
        assert emb == chunks
        assert emb_ids == chunk_ids
        assert emb_ids.isdisjoint(partial[2])  # the healed document was re-chunked


class TestUpdateInvalidatesStaleChunks:
    """CR-01: content edits must invalidate chunks/embeddings on `sif index update`.

    Edit note -> update -> embed (no --force) must serve fresh chunk text and
    fresh vectors; before the fix, the chunk-id-set completeness check saw the
    stale (never re-chunked) ids and skipped the document forever.
    """

    ORIGINAL = "# Original\n\n" + ("Original paragraph text. " * 300)
    REWRITTEN = "# Rewritten\n\n" + ("Rewritten paragraph text. " * 300)

    def test_edited_document_reembeds_with_fresh_content(
        self,
        tmp_path: Path,
        monkeypatch,
    ) -> None:
        _delenv_settings_vars(monkeypatch)
        db_path = tmp_path / "edit.db"
        settings = _test_settings()
        notes = tmp_path / "notes"
        notes.mkdir()
        doc_file = notes / "a.md"
        doc_file.write_text(self.ORIGINAL)
        _seed_collection_dir(db_path, settings, str(notes))
        manager, _vector_log = _make_manager_mock()

        # First cycle: update -> embed
        assert _invoke_update(db_path, settings, []).exit_code == 0
        assert _invoke_embed(db_path, manager, settings, []).exit_code == 0
        assert manager.embed_documents.call_count == 1
        _, chunks1, emb_ids1, chunk_ids1 = _store_state(db_path)
        assert chunks1 >= 1
        assert emb_ids1 == chunk_ids1

        # Edit the note (medium+ content), then update + embed without --force
        doc_file.write_text(self.REWRITTEN)
        update_result = _invoke_update(db_path, settings, [])
        assert update_result.exit_code == 0
        embed_result = _invoke_embed(db_path, manager, settings, [])
        assert embed_result.exit_code == 0

        # The edited document was NOT skipped: a fresh embed batch ran
        assert manager.embed_documents.call_count == 2

        conn = sqlite3.connect(str(db_path))
        try:
            contents = [row[0] for row in conn.execute("SELECT content FROM document_chunks")]
            assert contents, "chunks were re-created after the edit"
            assert all("Rewritten paragraph text" in c for c in contents)
            assert not any("Original paragraph text" in c for c in contents)
            # FTS serves the new text (exercises the fixed update trigger)
            assert (
                conn.execute(
                    "SELECT COUNT(*) FROM documents_fts WHERE documents_fts MATCH 'rewritten'"
                ).fetchone()[0]
                == 1
            )
            assert (
                conn.execute(
                    "SELECT COUNT(*) FROM chunks_fts WHERE chunks_fts MATCH 'rewritten'"
                ).fetchone()[0]
                >= 1
            )
        finally:
            conn.close()

        # Embeddings reference exactly the fresh chunk set
        emb2, chunks2, emb_ids2, chunk_ids2 = _store_state(db_path)
        assert emb2 == chunks2
        assert emb_ids2 == chunk_ids2
        assert chunk_ids2.isdisjoint(chunk_ids1)  # re-chunked ids are fresh uuid4s


class TestDimensionMismatchFailsFast:
    """WR-02: a model whose dim disagrees with the vec0 table must fail fast.

    Local backends drop the settings embedding_dim kwarg, so without this
    check the mismatch surfaced as a raw sqlite-vec insert error only after
    chunks were already written — and every later run self-healed into the
    same failure.
    """

    def test_model_dim_mismatch_exits_with_remediation_message(
        self,
        tmp_path: Path,
        monkeypatch,
    ) -> None:
        _delenv_settings_vars(monkeypatch)
        db_path = tmp_path / "mismatch.db"
        settings = _test_settings()  # schema built with FLOAT[8]
        _seed_collection(db_path, settings)
        manager, _vector_log = _make_manager_mock()
        manager.get_model_info.return_value = {"loaded": True, "embedding_dim": 4}

        result = _invoke_embed(db_path, manager, settings, [])

        assert result.exit_code != 0
        assert "produces 4-dim embeddings but the index stores 8-dim vectors" in result.output
        assert "SIF_EMBEDDING_DIM" in result.output

        # Nothing was written: no chunks, no vectors
        emb, chunks, _, _ = _store_state(db_path)
        assert chunks == 0
        assert emb == 0


class TestRemovalPurgesEmbeddings:
    """WR-01: removing a vanished file must purge its embeddings, not orphan them.

    Orphaned vec0 rows are resolved inside the KNN MATCH — before the JOIN
    filters them out — so they occupy top-k slots and crowd live documents
    out of vector search results until a manual `sif cleanup`.
    """

    def test_removed_file_leaves_no_embeddings(
        self,
        tmp_path: Path,
        monkeypatch,
    ) -> None:
        _delenv_settings_vars(monkeypatch)
        db_path = tmp_path / "remove.db"
        settings = _test_settings()
        notes = tmp_path / "notes"
        notes.mkdir()
        doc_file = notes / "b.md"
        doc_file.write_text("# Note\n\n" + ("Removable paragraph text. " * 100))
        _seed_collection_dir(db_path, settings, str(notes))
        manager, _vector_log = _make_manager_mock()

        assert _invoke_update(db_path, settings, []).exit_code == 0
        assert _invoke_embed(db_path, manager, settings, []).exit_code == 0
        emb1, chunks1, _, _ = _store_state(db_path)
        assert emb1 == chunks1
        assert emb1 > 0

        # Delete the file from disk and re-run update
        doc_file.unlink()
        result = _invoke_update(db_path, settings, [])
        assert result.exit_code == 0
        assert "Removed: 1" in result.output

        # No orphaned chunks or vectors remain
        emb2, chunks2, _, _ = _store_state(db_path)
        assert chunks2 == 0
        assert emb2 == 0


class TestPerCollectionTransaction:
    """CR-02: a failing collection must not roll back a successful one.

    The whole-run transaction raised the final ClickException inside its own
    `with db.connection:` block, discarding every successful collection's
    committed work after the CLI had already reported it embedded.
    """

    def test_failed_collection_keeps_successful_collections_work(
        self,
        tmp_path: Path,
        monkeypatch,
    ) -> None:
        _delenv_settings_vars(monkeypatch)
        db_path = tmp_path / "partial.db"
        settings = _test_settings()
        _seed_two_collections(db_path, settings, tmp_path / "good", tmp_path / "bad")

        manager, _vector_log = _make_manager_mock()
        inner_embed = manager.embed_documents.side_effect

        def fail_on_unembeddable(texts: list[str], **kwargs: object) -> object:
            if any("b-bad document text" in t for t in texts):
                raise RuntimeError("simulated backend failure")
            return inner_embed(texts, **kwargs)

        manager.embed_documents.side_effect = fail_on_unembeddable

        result = _invoke_embed(db_path, manager, settings, [])

        # D-16: the backend error is document-local; the run reports it and
        # exits non-zero while the successful collection's work stays durable.
        normalized = " ".join(result.output.split())
        assert result.exit_code != 0
        assert "Embedding failed for 1 document(s)" in normalized
        assert "simulated backend failure" in normalized
        assert "Error embedding collection" not in normalized

        # ...but the successful collection's work is persisted, not rolled back.
        emb, chunks, emb_ids, chunk_ids = _store_state(db_path)
        assert chunks > 0
        assert emb == chunks
        assert emb_ids == chunk_ids

        conn = sqlite3.connect(str(db_path))
        try:
            doc_collections = conn.execute(
                "SELECT DISTINCT d.collection_id FROM document_chunks dc "
                "JOIN documents d ON dc.document_id = d.id"
            ).fetchall()
            coll_names = {
                conn.execute("SELECT name FROM collections WHERE id = ?", (row[0],)).fetchone()[0]
                for row in doc_collections
            }
        finally:
            conn.close()
        assert coll_names == {"a-good"}


class TestUpdateChecksumIdempotency:
    """Zero-change `sif index update` must report 0 updated (t_66218b67).

    Before the fix the update path compared stored checksums (sha256 of the
    body) against whole-file hashes, so every existing document was rewritten
    every run (chunks/embeddings dropped + FTS rebuild). Persisting the fresh
    checksum on the update branch is equally load-bearing: without it a
    changed document would oscillate as "updated" on every later run.

    Since CORR-01/D-08 the checksum convention is body + canonical full
    frontmatter (``sif.core.models.compute_checksum``); the idempotency
    contract — a zero-change rerun reports 0 updated — is unchanged.
    """

    BODY = "# Note\n\n" + ("Stable paragraph text. " * 100)

    def _seed_note(self, db_path: Path, settings: Settings, notes_dir: Path) -> Path:
        from sif.core.models import Collection, Document
        from sif.database.database import Database
        from sif.database.repositories import CollectionRepository, DocumentRepository

        notes_dir.mkdir(parents=True, exist_ok=True)
        doc_file = notes_dir / "a.md"
        doc_file.write_text(self.BODY, encoding="utf-8")
        db = Database(db_path)
        with patch("sif.config.settings.get_settings", return_value=settings):
            db.init_schema()
            with db.connection:
                coll_repo = CollectionRepository(db.connection)
                doc_repo = DocumentRepository(db.connection)
                coll = Collection(name="notes", path=str(notes_dir))
                coll_repo.create(coll)
                doc_repo.create(
                    Document(
                        path=str(doc_file),
                        collection_id=coll.id,
                        content=self.BODY,
                        title="A",
                    )
                )
        db.close()
        return doc_file

    def test_zero_change_rerun_reports_zero_updated(
        self,
        tmp_path: Path,
        monkeypatch,
    ) -> None:
        _delenv_settings_vars(monkeypatch)
        db_path = tmp_path / "update.db"
        settings = _test_settings()
        notes = tmp_path / "notes"
        self._seed_note(db_path, settings, notes)

        # Cycle 1: index the note, then embed to fill chunks/embeddings.
        assert _invoke_update(db_path, settings, []).exit_code == 0
        manager, _vector_log = _make_manager_mock()
        assert _invoke_embed(db_path, manager, settings, []).exit_code == 0
        emb1, chunks1, emb_ids1, chunk_ids1 = _store_state(db_path)
        assert emb1 == chunks1
        assert emb1 > 0

        # Cycle 2: files untouched -> the unchanged short-circuit fires:
        # nothing is rewritten and no chunks/embeddings are destroyed.
        result = _invoke_update(db_path, settings, [])
        assert result.exit_code == 0
        assert "Updated: 0" in result.output
        assert _store_state(db_path) == (emb1, chunks1, emb_ids1, chunk_ids1)

        # Cycle 3: a real edit is still detected...
        doc_file = notes / "a.md"
        doc_file.write_text(self.BODY.replace("Stable", "Edited"), encoding="utf-8")
        result = _invoke_update(db_path, settings, [])
        assert result.exit_code == 0
        assert "Updated: 1" in result.output

        # ...and the fresh checksum is persisted, so the next run converges
        # instead of rewriting the same document again.
        conn = sqlite3.connect(str(db_path))
        try:
            stored_cs, stored_content, stored_metadata = conn.execute(
                "SELECT checksum, content, metadata FROM documents"
            ).fetchone()
        finally:
            conn.close()
        # D-08 retired the body-only convention: the row checksum covers the
        # body plus the canonical full frontmatter (empty for this fixture).
        # The stored string form must reproduce the same hash.
        assert stored_cs == compute_checksum(stored_content, json.loads(stored_metadata))
        assert "Edited paragraph text" in stored_content
        result = _invoke_update(db_path, settings, [])
        assert result.exit_code == 0
        assert "Updated: 0" in result.output


def _seed_two_documents(db_path: Path, settings: Settings) -> dict[str, str]:
    """Seed one collection with two one-chunk documents (a.md, b.md)."""
    from sif.core.models import Collection, Document
    from sif.database.database import Database
    from sif.database.repositories import CollectionRepository, DocumentRepository

    db = Database(db_path)
    with patch("sif.config.settings.get_settings", return_value=settings):
        db.init_schema()
        with db.connection:
            coll_repo = CollectionRepository(db.connection)
            doc_repo = DocumentRepository(db.connection)
            coll = Collection(name="notes", path="/notes")
            coll_repo.create(coll)
            ids: dict[str, str] = {}
            for name, body in (("a.md", "# A\n\nalpha body"), ("b.md", "# B\n\nbeta body")):
                path = f"/notes/{name}"
                doc = Document(path=path, collection_id=coll.id, content=body, title=name)
                doc_repo.create(doc)
                ids[path] = doc.id
    db.close()
    return ids


def _chunk_counts(db_path: Path) -> dict[str, int]:
    """Return {document path: committed chunk rows}."""
    conn = sqlite3.connect(str(db_path))
    try:
        return {
            row[0]: int(row[1])
            for row in conn.execute(
                "SELECT d.path, COUNT(c.id) FROM documents d "
                "LEFT JOIN document_chunks c ON c.document_id = d.id "
                "GROUP BY d.id"
            )
        }
    finally:
        conn.close()


def _shadow_count(db_path: Path, document_id: str) -> int:
    """Count the derived shadow's rows for one document."""
    conn = sqlite3.connect(str(db_path))
    try:
        return int(
            conn.execute(
                "SELECT COUNT(*) FROM embedded_documents WHERE document_id = ?",
                (document_id,),
            ).fetchone()[0]
        )
    finally:
        conn.close()


def _stored_identity(db_path: Path):
    """Read the persisted embedder identity from a plain connection."""
    conn = sqlite3.connect(str(db_path))
    try:
        return read_identity(conn)
    finally:
        conn.close()


def _seed_legacy_vector(db_path: Path, document_id: str) -> None:
    """Insert one vec0 row without an identity row (a pre-Phase-21 index)."""
    import sqlite_vec

    conn = sqlite3.connect(str(db_path))
    try:
        conn.enable_load_extension(True)
        sqlite_vec.load(conn)
        conn.enable_load_extension(False)
        conn.execute(
            "INSERT INTO document_embeddings (embedding_id, document_id, chunk_id, embedding) "
            "VALUES ('legacy-vec', ?, 'legacy-chunk', vec_f32(?))",
            (document_id, json.dumps([0.1] * DIM)),
        )
        conn.commit()
    finally:
        conn.close()


class TestStreamingFailureDurability:
    """D-15/D-16: per-document commits make mid-run failure resumable."""

    def test_mid_run_failure_keeps_committed_documents_and_resumes_remainder(
        self,
        tmp_path: Path,
        monkeypatch,
    ) -> None:
        """Earlier documents survive a failure; a re-run embeds only the rest."""
        _delenv_settings_vars(monkeypatch)
        db_path = tmp_path / "durable.db"
        settings = _test_settings()
        ids = _seed_two_documents(db_path, settings)

        manager = _streaming_manager(_identity("model-a"), failure_at=2)
        result = _invoke_embed(db_path, manager, settings, [])

        assert result.exit_code != 0
        assert "Embedding failed for 1 document(s)" in result.output
        counts = _chunk_counts(db_path)
        assert counts["/notes/a.md"] >= 1
        assert counts["/notes/b.md"] == 0

        # Re-run: the exact-set skip leaves a.md alone and embeds only b.md.
        resume = _streaming_manager(_identity("model-a"))
        second = _invoke_embed(db_path, resume, settings, [])
        assert second.exit_code == 0
        assert len(resume.embed_documents.calls) == 1
        counts = _chunk_counts(db_path)
        assert counts["/notes/a.md"] >= 1
        assert counts["/notes/b.md"] >= 1

        stored = _stored_identity(db_path)
        assert stored is not None
        assert stored.source == "verified"
        assert ids["/notes/a.md"]


class TestGarbageAndWhitespaceIsolation:
    """D-17/D-16: a garbage batch aborts without persistence; whitespace is skipped."""

    def test_garbage_batch_aborts_persists_nothing_and_a_rerun_succeeds(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        """A NaN batch persists no chunk/vector/shadow/identity row, and a
        subsequent normal run embeds the document cleanly (no poisoned state)."""
        _delenv_settings_vars(monkeypatch)
        db_path = tmp_path / "garbage.db"
        settings = _test_settings()
        doc_id = _seed_collection(db_path, settings)

        garbage = MagicMock()
        garbage.get_model_info.return_value = {"loaded": True, "embedding_dim": DIM}
        garbage.get_identity.return_value = _identity()

        def _nan_vectors(texts: list[str], **_kwargs: object) -> MagicMock:
            return MagicMock(embeddings=[[float("nan")] + [0.0] * (DIM - 1) for _ in texts])

        garbage.embed_documents.side_effect = _nan_vectors

        result = _invoke_embed(db_path, garbage, settings, [])
        assert result.exit_code != 0
        assert "Embedding aborted" in result.output
        assert "non-finite" in result.output

        emb_count, chunk_count, _emb_ids, _chunk_ids = _store_state(db_path)
        assert emb_count == 0
        assert chunk_count == 0
        assert _shadow_count(db_path, doc_id) == 0
        assert _stored_identity(db_path) is None

        rerun = _streaming_manager(_identity())
        second = _invoke_embed(db_path, rerun, settings, [])
        assert second.exit_code == 0, second.output
        emb_count, chunk_count, _emb_ids, _chunk_ids = _store_state(db_path)
        assert emb_count >= 1
        assert chunk_count >= 1
        assert _shadow_count(db_path, doc_id) == 1

    def test_whitespace_only_document_is_skipped_without_a_shadow_row(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        """A whitespace-only document never reaches the model and never gains a
        shadow row; the run itself succeeds (D-17/D-16)."""
        _delenv_settings_vars(monkeypatch)
        db_path = tmp_path / "whitespace.db"
        settings = _test_settings()

        from sif.core.models import Collection, Document
        from sif.database.database import Database
        from sif.database.repositories import CollectionRepository, DocumentRepository

        db = Database(db_path)
        with patch("sif.config.settings.get_settings", return_value=settings):
            db.init_schema()
        with db.connection:
            coll = Collection(name="notes", path="/notes")
            CollectionRepository(db.connection).create(coll)
            doc = Document(
                path="/notes/blank.md",
                collection_id=coll.id,
                content="   \n\t  ",
                title="Blank",
            )
            DocumentRepository(db.connection).create(doc)
            doc_id = doc.id
        db.close()

        manager = _streaming_manager(_identity())
        result = _invoke_embed(db_path, manager, settings, [])

        assert result.exit_code == 0, result.output
        assert manager.embed_documents.calls == []
        assert _chunk_counts(db_path)["/notes/blank.md"] == 0
        assert _shadow_count(db_path, doc_id) == 0


class TestIdentityCertification:
    """D-04: source=verified only after a complete unfiltered --force run."""

    def _legacy_index(self, tmp_path: Path, settings: Settings) -> tuple[Path, str]:
        db_path = tmp_path / "certify.db"
        doc_id = _seed_collection(db_path, settings)
        _seed_legacy_vector(db_path, doc_id)
        return db_path, doc_id

    def test_scoped_force_keeps_legacy_assumed(self, tmp_path: Path, monkeypatch) -> None:
        """A --force scoped to one collection is not a certification run."""
        _delenv_settings_vars(monkeypatch)
        db_path, _doc_id = self._legacy_index(tmp_path, _test_settings())
        manager = _streaming_manager(_identity())

        result = _invoke_embed(
            db_path,
            manager,
            _test_settings(),
            ["--force", "--collection", "notes"],
        )

        assert result.exit_code == 0, result.output
        stored = _stored_identity(db_path)
        assert stored is not None
        assert stored.source == "legacy-assumed"

    def test_full_force_with_a_failure_keeps_legacy_assumed(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        """Any failed document disqualifies certification for the run."""
        _delenv_settings_vars(monkeypatch)
        db_path, _doc_id = self._legacy_index(tmp_path, _test_settings())
        manager = _streaming_manager(_identity(), failure_at=1)

        result = _invoke_embed(db_path, manager, _test_settings(), ["--force"])

        assert result.exit_code != 0
        stored = _stored_identity(db_path)
        assert stored is not None
        assert stored.source == "legacy-assumed"

    def test_full_force_zero_failures_certifies_verified(self, tmp_path: Path, monkeypatch) -> None:
        """A complete unfiltered --force run rewrites the identity as verified."""
        _delenv_settings_vars(monkeypatch)
        db_path, _doc_id = self._legacy_index(tmp_path, _test_settings())
        manager = _streaming_manager(_identity())

        result = _invoke_embed(db_path, manager, _test_settings(), ["--force"])

        assert result.exit_code == 0, result.output
        stored = _stored_identity(db_path)
        assert stored is not None
        assert stored.source == "verified"
        assert stored.model_name == "test"
