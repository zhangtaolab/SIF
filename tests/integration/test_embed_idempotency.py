"""Integration tests for idempotent `sif index embed` runs (G-03-3).

Reproduces the UAT evidence from 03-UAT.md test 3 inverted: two embed runs on
one collection must leave document_embeddings with exactly one row per live
chunk, and vector search must return each chunk exactly once — never once per
historical run (the observed 21-rows-vs-3-chunks, document-times-7 symptom).
"""

from __future__ import annotations

import sqlite3
from pathlib import Path
from unittest.mock import MagicMock, patch

from click.testing import CliRunner

from sif.cli.commands.index import embed_cmd
from sif.config.settings import Settings
from sif.core.models import SearchOptions


DIM = 8


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
            vectors.append(vec)
        vector_log.append(vectors)
        return MagicMock(embeddings=vectors)

    manager.embed.side_effect = fake_embed
    return manager, vector_log


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
        """The document-times-7 UAT symptom inverted: one result row per live chunk."""
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
        finally:
            db.close()

        assert len(results) == chunk_count
        assert {r.document_id for r in results} == {doc_id}

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
        assert manager.embed.call_count == 1
        state1 = _store_state(db_path)
        assert state1[0] == state1[1]

        # Run 2 without --force: everything complete -> zero embed calls, nothing mutated
        assert _invoke_embed(db_path, manager, settings, []).exit_code == 0
        assert manager.embed.call_count == 1  # no new embed call
        assert _store_state(db_path) == state1  # counts and chunk-id sets unchanged

        # Run 3 with --force: full re-embed, invariants preserved
        assert _invoke_embed(db_path, manager, settings, ["--force"]).exit_code == 0
        assert manager.embed.call_count == 2  # exactly one more batch
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
        assert manager.embed.call_count == 1

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
        assert manager.embed.call_count == 2
        emb, chunks, emb_ids, chunk_ids = _store_state(db_path)
        assert emb == chunks
        assert emb_ids == chunk_ids
        assert emb_ids.isdisjoint(partial[2])  # the healed document was re-chunked
