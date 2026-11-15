"""Tests for index CLI commands."""

import io
import json
import logging
import math
import sqlite3
import types
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from click.testing import CliRunner
from rich.console import Console

from sif.cli.commands.index import embed_cmd, index_group
from sif.config.settings import Settings
from sif.core.models import Collection, Document
from sif.database.database import Database
from sif.database.maintenance import BackupResult, MaintenanceBusyError, VacuumResult
from sif.database.repositories import CollectionRepository, DocumentRepository
from sif.embedding.identity import build_identity, read_identity, write_identity
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


def _streaming_manager(identity, fail_on_call: int | None = None) -> MagicMock:
    """Mock manager with a real identity and per-call vector batches."""
    manager = MagicMock()
    manager.get_model_info.return_value = {"loaded": True, "embedding_dim": identity.dimension}
    manager.get_identity.return_value = identity
    calls: list[list[str]] = []

    def fake_embed_documents(texts: list[str]) -> SimpleNamespace:
        calls.append(list(texts))
        if fail_on_call is not None and len(calls) == fail_on_call:
            raise RuntimeError("injected backend failure")
        return SimpleNamespace(embeddings=[_unit_vector(identity.dimension) for _ in texts])

    manager.embed_documents.side_effect = fake_embed_documents
    manager.embed_documents.calls = calls
    return manager


def _seed_real_index(
    db_path: Path,
    settings: Settings,
    documents: list[tuple[str, str]],
) -> None:
    """Create a real index with one collection and the supplied documents."""
    db = Database(db_path)
    with patch("sif.config.settings.get_settings", return_value=settings):
        db.init_schema()
    with db.connection:
        coll_repo = CollectionRepository(db.connection)
        doc_repo = DocumentRepository(db.connection)
        coll = Collection(name="notes", path="/notes")
        coll_repo.create(coll)
        for path, content in documents:
            doc_repo.create(Document(path=path, collection_id=coll.id, content=content, title=path))
    db.close()


def _invoke_real_embed(
    db_path: Path,
    manager: MagicMock,
    settings: Settings,
    args: list[str],
) -> object:
    """Invoke embed_cmd against a real database with a mocked manager."""
    with (
        patch("sif.config.settings.get_settings", return_value=settings),
        patch("sif.embedding.manager.EmbeddingManager.from_settings", return_value=manager),
    ):
        return CliRunner().invoke(embed_cmd, args, obj={"index_path": db_path})


def _document_ids(db_path: Path) -> dict[str, str]:
    """Map document path to id on a real index."""
    conn = sqlite3.connect(str(db_path))
    try:
        return {row[1]: row[0] for row in conn.execute("SELECT id, path FROM documents")}
    finally:
        conn.close()


def _embedded_chunk_count(db_path: Path, document_id: str) -> int:
    """Count a document's committed chunk rows."""
    conn = sqlite3.connect(str(db_path))
    try:
        return int(
            conn.execute(
                "SELECT COUNT(*) FROM document_chunks WHERE document_id = ?",
                (document_id,),
            ).fetchone()[0]
        )
    finally:
        conn.close()


def _load_sqlite_vec(conn: sqlite3.Connection) -> None:
    """Load the sqlite-vec extension so vec0 tables can be read or written."""
    import sqlite_vec

    conn.enable_load_extension(True)
    sqlite_vec.load(conn)
    conn.enable_load_extension(False)


def _seed_legacy_embedding(db_path: Path, document_id: str) -> None:
    """Insert one pre-Phase-21 chunk + vec0 row (no identity or shadow write)."""
    conn = sqlite3.connect(str(db_path))
    try:
        _load_sqlite_vec(conn)
        chunk_id = f"legacy-chunk-{document_id}"
        conn.execute(
            "INSERT INTO document_chunks (id, document_id, sequence, content, created_at)"
            " VALUES (?, ?, 0, ?, ?)",
            (chunk_id, document_id, "legacy chunk body", "2026-11-16T00:00:00+00:00"),
        )
        conn.execute(
            "INSERT INTO document_embeddings (embedding_id, document_id, chunk_id, embedding)"
            " VALUES (?, ?, ?, vec_f32(?))",
            (f"legacy-vec-{document_id}", document_id, chunk_id, json.dumps(_unit_vector())),
        )
        conn.commit()
    finally:
        conn.close()


def _make_pre_phase_21_index(
    db_path: Path,
    settings: Settings,
    documents: list[tuple[str, str]],
) -> dict[str, str]:
    """Build a pre-Phase-21 index shape: vectors, no identity, no shadow, no markers.

    Documents are seeded through the real schema, then given chunk/vec0 rows and
    stripped of the Phase-21 surfaces — the exact legacy state D-04 upgrades.
    """
    _seed_real_index(db_path, settings, documents)
    ids = _document_ids(db_path)
    for document_id in ids.values():
        _seed_legacy_embedding(db_path, document_id)
    conn = sqlite3.connect(str(db_path))
    try:
        conn.execute(
            "DELETE FROM index_meta"
            " WHERE key IN ('embedder.identity', 'embedded_documents_version')"
        )
        conn.execute("DROP TABLE embedded_documents")
        conn.commit()
    finally:
        conn.close()
    return ids


def _shadow_ids(db_path: Path) -> list[str]:
    """Return the persisted shadow's document ids in sorted order."""
    conn = sqlite3.connect(str(db_path))
    try:
        return [
            row[0]
            for row in conn.execute(
                "SELECT document_id FROM embedded_documents ORDER BY document_id"
            )
        ]
    finally:
        conn.close()


def _vector_count(db_path: Path) -> int:
    """Count stored vec0 rows (the extension is required to read the table)."""
    conn = sqlite3.connect(str(db_path))
    try:
        _load_sqlite_vec(conn)
        return int(conn.execute("SELECT COUNT(*) FROM document_embeddings").fetchone()[0])
    finally:
        conn.close()


def _stored_identity(db_path: Path):
    """Read the persisted embedder identity from a plain connection."""
    conn = sqlite3.connect(str(db_path))
    try:
        return read_identity(conn)
    finally:
        conn.close()


def _fake_openai_module(dim=8):
    """Build a fake openai module recording embeddings.create calls."""
    create_calls = []
    constructor_calls = []
    vec = [0.5] * dim

    class _FakeEmbeddings:
        def create(self, **kwargs):
            create_calls.append(kwargs)
            texts = list(kwargs["input"])
            return SimpleNamespace(
                data=[SimpleNamespace(index=i, embedding=list(vec)) for i, _ in enumerate(texts)]
            )

    class _FakeClient:
        def __init__(self):
            self.embeddings = _FakeEmbeddings()

    def _openai(**kwargs):
        constructor_calls.append(kwargs)
        return _FakeClient()

    module = types.ModuleType("openai")
    module.OpenAI = _openai
    return module, create_calls


class TestEmbedCommand:
    """Tests for embed command."""

    def _make_collection(self, coll_id="coll1", name="notes", path="/notes"):
        from sif.core.models import Collection

        return Collection(id=coll_id, name=name, path=path)

    def _make_document(self, doc_id="doc1", path="/notes/a.md", content="hello world"):
        from sif.core.models import Document

        return Document(
            id=doc_id,
            path=path,
            collection_id="coll1",
            content=content,
            title="A",
        )

    def test_embed_cmd_uses_embedding_manager(self, tmp_path: Path):
        """embed_cmd invokes EmbeddingManager for chunk texts."""
        runner = CliRunner()

        coll = self._make_collection()
        doc = self._make_document(content="hello world")

        mock_coll_repo = MagicMock()
        mock_coll_repo.list_all.return_value = [coll]

        mock_doc_repo = MagicMock()
        mock_doc_repo.list_by_collection.return_value = [doc]

        mock_chunk_repo = MagicMock()
        mock_chunk_repo.get_by_document.return_value = []

        mock_manager = MagicMock()
        mock_manager.embed_documents.return_value = MagicMock(embeddings=[[0.1, 0.2]])
        mock_manager.embed_single.return_value = [0.1, 0.2]

        mock_db = MagicMock()

        with (
            patch("sif.cli.commands.index.Database", return_value=mock_db),
            patch(
                "sif.cli.commands.index.CollectionRepository",
                return_value=mock_coll_repo,
            ),
            patch(
                "sif.cli.commands.index.DocumentRepository",
                return_value=mock_doc_repo,
            ),
            patch(
                "sif.cli.commands.index.DocumentChunkRepository",
                return_value=mock_chunk_repo,
            ),
            patch(
                "sif.cli.commands.index.create_chunker",
                return_value=MagicMock(chunk=lambda text: [MagicMock(content=text, id="c1")]),
            ),
            patch(
                "sif.embedding.manager.EmbeddingManager.from_settings",
                return_value=mock_manager,
            ),
            patch(
                "sif.config.settings.get_settings",
                return_value=MagicMock(
                    model_name="test",
                    batch_size=32,
                    model_dump=lambda: {"model_name": "test"},
                ),
            ),
            patch(
                "sif.search.vector.VectorSearcher",
                return_value=MagicMock(),
            ),
        ):
            result = runner.invoke(
                embed_cmd,
                [],
                obj={"index_path": tmp_path / "sif.db"},
            )

        assert result.exit_code == 0
        mock_manager.embed_documents.assert_called_once()
        call_args = mock_manager.embed_documents.call_args[0][0]
        assert call_args == ["hello world"]

    def test_embed_cmd_embedding_failure_exits_nonzero(self, tmp_path: Path):
        """embed_cmd must exit non-zero when embedding a collection fails."""
        runner = CliRunner()

        coll = self._make_collection()
        doc = self._make_document(content="hello world")

        mock_coll_repo = MagicMock()
        mock_coll_repo.list_all.return_value = [coll]

        mock_doc_repo = MagicMock()
        mock_doc_repo.list_by_collection.return_value = [doc]

        mock_manager = MagicMock()
        mock_manager.embed_documents.side_effect = RuntimeError("simulated backend failure")

        with (
            patch("sif.cli.commands.index.Database", return_value=MagicMock()),
            patch(
                "sif.cli.commands.index.CollectionRepository",
                return_value=mock_coll_repo,
            ),
            patch(
                "sif.cli.commands.index.DocumentRepository",
                return_value=mock_doc_repo,
            ),
            patch(
                "sif.cli.commands.index.DocumentChunkRepository",
                return_value=MagicMock(),
            ),
            patch(
                "sif.cli.commands.index.create_chunker",
                return_value=MagicMock(chunk=lambda text: [MagicMock(content=text, id="c1")]),
            ),
            patch(
                "sif.embedding.manager.EmbeddingManager.from_settings",
                return_value=mock_manager,
            ),
            patch(
                "sif.config.settings.get_settings",
                return_value=MagicMock(model_name="test", batch_size=32),
            ),
        ):
            result = runner.invoke(
                embed_cmd,
                [],
                obj={"index_path": tmp_path / "sif.db"},
            )

        # D-16: an embed-backend error is document-local; the run reports it and
        # exits non-zero without a collection-level failure.
        assert result.exit_code != 0
        assert "Embedding failed for 1 document(s)" in result.output
        assert "simulated backend failure" in result.output
        assert "Error embedding collection" not in result.output

    def test_embed_cmd_backend_load_failure_exits_nonzero(self, tmp_path: Path):
        """Backend load errors must reach the dedicated handler and exit non-zero."""
        runner = CliRunner()

        with (
            patch("sif.cli.commands.index.Database", return_value=MagicMock()),
            patch(
                "sif.embedding.manager.EmbeddingManager.from_settings",
                side_effect=ImportError("openai"),
            ),
            patch(
                "sif.config.settings.get_settings",
                return_value=MagicMock(model_name="test"),
            ),
        ):
            result = runner.invoke(
                embed_cmd,
                ["--model-type", "openai"],
                obj={"index_path": tmp_path / "sif.db"},
            )

        assert result.exit_code != 0
        assert "Embedding backend not installed" in result.output

    def test_embed_cmd_invalid_chunk_strategy_is_usage_error(self, tmp_path: Path):
        """WR-05: an invalid --chunk-strategy is a Click usage error, not a traceback."""
        runner = CliRunner()

        with (
            patch("sif.cli.commands.index.Database", return_value=MagicMock()),
            patch(
                "sif.embedding.manager.EmbeddingManager.from_settings",
                return_value=MagicMock(),
            ),
            patch(
                "sif.config.settings.get_settings",
                return_value=MagicMock(model_name="test"),
            ),
        ):
            result = runner.invoke(
                embed_cmd,
                ["--chunk-strategy", "smrt"],
                obj={"index_path": tmp_path / "sif.db"},
            )

        assert result.exit_code == 2  # Click usage error
        assert "Invalid value" in result.output
        assert isinstance(result.exception, SystemExit)

    def test_embed_cmd_batches_across_documents(self, tmp_path: Path):
        """embed_cmd batches embeddings across documents."""
        runner = CliRunner()

        coll = self._make_collection()
        doc1 = self._make_document(doc_id="doc1", content="hello")
        doc2 = self._make_document(doc_id="doc2", content="world")

        mock_coll_repo = MagicMock()
        mock_coll_repo.list_all.return_value = [coll]

        mock_doc_repo = MagicMock()
        mock_doc_repo.list_by_collection.return_value = [doc1, doc2]

        mock_chunk_repo = MagicMock()
        mock_chunk_repo.get_by_document.return_value = []

        mock_manager = MagicMock()
        mock_manager.embed_documents.side_effect = lambda texts: MagicMock(
            embeddings=[[0.1] for _ in texts]
        )
        mock_manager.embed_single.return_value = [0.1]

        mock_vector_searcher = MagicMock()

        mock_db = MagicMock()

        with (
            patch("sif.cli.commands.index.Database", return_value=mock_db),
            patch(
                "sif.cli.commands.index.CollectionRepository",
                return_value=mock_coll_repo,
            ),
            patch(
                "sif.cli.commands.index.DocumentRepository",
                return_value=mock_doc_repo,
            ),
            patch(
                "sif.cli.commands.index.DocumentChunkRepository",
                return_value=mock_chunk_repo,
            ),
            patch(
                "sif.cli.commands.index.create_chunker",
                return_value=MagicMock(
                    chunk=lambda text: [MagicMock(content=text, id=f"chunk-{text}")],
                ),
            ),
            patch(
                "sif.embedding.manager.EmbeddingManager.from_settings",
                return_value=mock_manager,
            ),
            patch(
                "sif.config.settings.get_settings",
                return_value=MagicMock(
                    model_name="test",
                    batch_size=32,
                    model_dump=lambda: {"model_name": "test"},
                ),
            ),
            patch(
                "sif.search.vector.VectorSearcher",
                return_value=mock_vector_searcher,
            ),
        ):
            result = runner.invoke(
                embed_cmd,
                [],
                obj={"index_path": tmp_path / "sif.db"},
            )

        assert result.exit_code == 0
        # D-15: one model call and one vector batch per document, not one
        # collection-wide batch.
        assert mock_manager.embed_documents.call_count == 2
        assert mock_vector_searcher.add_embeddings_batch.call_count == 2
        batches = [call[0][0] for call in mock_vector_searcher.add_embeddings_batch.call_args_list]
        assert [len(batch) for batch in batches] == [1, 1]

    def test_embed_cmd_respects_model_type_override(self, tmp_path: Path):
        """embed_cmd passes --model-type to settings override."""
        runner = CliRunner()

        coll = self._make_collection()

        mock_coll_repo = MagicMock()
        mock_coll_repo.list_all.return_value = [coll]

        mock_doc_repo = MagicMock()
        mock_doc_repo.list_by_collection.return_value = []

        mock_manager = MagicMock()
        mock_manager.embed_documents.return_value = MagicMock(embeddings=[])
        mock_manager.embed_single.return_value = [0.1]

        captured_updates = {}

        def capture_model_copy(**kwargs):
            if "update" in kwargs:
                captured_updates.update(kwargs["update"])
            return MagicMock(
                model_type=kwargs.get("update", {}).get("model_type", "sentence_transformers"),
            )

        mock_settings = MagicMock()
        mock_settings.model_copy.side_effect = capture_model_copy
        mock_settings.model_type = "sentence_transformers"
        mock_settings.model_name = "test"

        mock_db = MagicMock()

        with (
            patch("sif.cli.commands.index.Database", return_value=mock_db),
            patch(
                "sif.cli.commands.index.CollectionRepository",
                return_value=mock_coll_repo,
            ),
            patch(
                "sif.cli.commands.index.DocumentRepository",
                return_value=mock_doc_repo,
            ),
            patch(
                "sif.cli.commands.index.DocumentChunkRepository",
                return_value=MagicMock(),
            ),
            patch(
                "sif.embedding.manager.EmbeddingManager.from_settings",
                return_value=mock_manager,
            ),
            patch(
                "sif.config.settings.get_settings",
                return_value=mock_settings,
            ),
            patch(
                "sif.search.vector.VectorSearcher",
                return_value=MagicMock(),
            ),
        ):
            result = runner.invoke(
                embed_cmd,
                ["--model-type", "openai"],
                obj={"index_path": tmp_path / "sif.db"},
            )

        assert result.exit_code == 0
        assert captured_updates["model_type"] == "openai"

    def test_embed_cmd_openai_model_type_reaches_endpoint(self, tmp_path: Path):
        """embed_cmd --model-type openai embeds via real manager + fake endpoint."""
        runner = CliRunner()

        coll = self._make_collection()
        doc = self._make_document(content="hello world")

        mock_coll_repo = MagicMock()
        mock_coll_repo.list_all.return_value = [coll]

        mock_doc_repo = MagicMock()
        mock_doc_repo.list_by_collection.return_value = [doc]

        mock_chunk_repo = MagicMock()

        # Real settings; base model_type deliberately differs so the test
        # proves the --model-type flag switches the backend to openai.
        real_settings = Settings(
            model_type="modelscope",
            model_name="test-embed-model",
            api_key="test-key",
            api_base="https://api.example.com/v1",
            cache_embeddings=False,
            embedding_dim=8,
        )

        fake_module, create_calls = _fake_openai_module()

        with (
            patch("sif.cli.commands.index.Database", return_value=MagicMock()),
            patch(
                "sif.cli.commands.index.CollectionRepository",
                return_value=mock_coll_repo,
            ),
            patch(
                "sif.cli.commands.index.DocumentRepository",
                return_value=mock_doc_repo,
            ),
            patch(
                "sif.cli.commands.index.DocumentChunkRepository",
                return_value=mock_chunk_repo,
            ),
            patch(
                "sif.cli.commands.index.create_chunker",
                return_value=MagicMock(chunk=lambda text: [MagicMock(content=text, id="c1")]),
            ),
            patch(
                "sif.config.settings.get_settings",
                return_value=real_settings,
            ),
            patch(
                "sif.search.vector.VectorSearcher",
                return_value=MagicMock(),
            ),
            patch.dict("sys.modules", {"openai": fake_module}),
        ):
            result = runner.invoke(
                embed_cmd,
                ["--model-type", "openai"],
                obj={"index_path": tmp_path / "sif.db"},
            )

        assert result.exit_code == 0
        assert "Failed to load embedding model" not in result.output
        assert "Error embedding collection" not in result.output
        recorded_models = {c["model"] for c in create_calls}
        assert "test-embed-model" in recorded_models

    def _make_embed_mocks(self, coll, docs, embedded_chunk_ids, live_chunk):
        """Build the shared repo/manager/searcher mock set for force-semantics tests."""
        live_chunk_mock = MagicMock()
        live_chunk_mock.id = live_chunk

        mock_coll_repo = MagicMock()
        mock_coll_repo.list_all.return_value = [coll]

        mock_doc_repo = MagicMock()
        mock_doc_repo.list_by_collection.return_value = docs

        mock_chunk_repo = MagicMock()
        mock_chunk_repo.get_by_document.return_value = [live_chunk_mock]

        mock_searcher = MagicMock()
        mock_searcher.get_all_embedded_chunk_ids.return_value = {
            d.id: set(embedded_chunk_ids) for d in docs
        }

        mock_manager = MagicMock()
        mock_manager.embed_documents.return_value = MagicMock(embeddings=[[0.1, 0.2]])
        mock_manager.get_model_info.return_value = {"loaded": True, "embedding_dim": 8}

        return mock_coll_repo, mock_doc_repo, mock_chunk_repo, mock_searcher, mock_manager

    def _invoke_with_mocks(self, runner, mocks, args, db_path: Path):
        """Invoke embed_cmd with the force-semantics mock set wired in."""
        mock_coll_repo, mock_doc_repo, mock_chunk_repo, mock_searcher, mock_manager = mocks
        with (
            patch("sif.cli.commands.index.Database", return_value=MagicMock()),
            patch(
                "sif.cli.commands.index.CollectionRepository",
                return_value=mock_coll_repo,
            ),
            patch(
                "sif.cli.commands.index.DocumentRepository",
                return_value=mock_doc_repo,
            ),
            patch(
                "sif.cli.commands.index.DocumentChunkRepository",
                return_value=mock_chunk_repo,
            ),
            patch(
                "sif.cli.commands.index.create_chunker",
                return_value=MagicMock(chunk=lambda text: [MagicMock(content=text, id="c1")]),
            ),
            # The streaming writer owns its chunk repository; point it at the
            # same mock so the per-document call shape stays observable.
            patch(
                "sif.indexing.embed_writer.DocumentChunkRepository",
                return_value=mock_chunk_repo,
            ),
            patch(
                "sif.embedding.manager.EmbeddingManager.from_settings",
                return_value=mock_manager,
            ),
            patch(
                "sif.config.settings.get_settings",
                return_value=MagicMock(model_name="test", batch_size=32),
            ),
            patch(
                "sif.search.vector.VectorSearcher",
                return_value=mock_searcher,
            ),
        ):
            return runner.invoke(
                embed_cmd,
                args,
                # Real tmp path: embed_cmd's index_lock wraps the loop, and a
                # MagicMock index_path materializes repo-root .lock litter.
                obj={"index_path": db_path},
            )

    def test_embed_cmd_default_skips_fully_embedded_document(self, tmp_path: Path):
        """Default run: a complete chunk/embedding set is skipped with no embed call."""
        runner = CliRunner()

        coll = self._make_collection()
        doc = self._make_document(content="hello world")

        mocks = self._make_embed_mocks(
            coll, [doc], embedded_chunk_ids={"chunk-1"}, live_chunk="chunk-1"
        )

        result = self._invoke_with_mocks(runner, mocks, [], tmp_path / "sif.db")

        _mock_coll_repo, _mock_doc_repo, mock_chunk_repo, mock_searcher, mock_manager = mocks
        assert result.exit_code == 0
        mock_chunk_repo.delete_by_document.assert_not_called()
        mock_searcher.delete_embeddings_by_document.assert_not_called()
        mock_manager.embed_documents.assert_not_called()
        # O(N^2) guard: the loop must batch-read the completeness map once and
        # never fall back to a per-document completeness lookup.
        mock_searcher.get_all_embedded_chunk_ids.assert_called_once()
        mock_searcher.get_embedded_chunk_ids.assert_not_called()
        # The skip line names the document
        assert "Already embedded" in result.output
        assert doc.path in result.output

    def test_embed_cmd_default_heals_stale_embedding_state(self, tmp_path: Path):
        """Default run: an orphaned embedding set (stale rows) is re-embedded."""
        runner = CliRunner()

        coll = self._make_collection()
        doc = self._make_document(content="hello world")

        # Stored set carries an orphaned row from an older run — sets mismatch
        mocks = self._make_embed_mocks(
            coll, [doc], embedded_chunk_ids={"chunk-1", "orphan-chunk"}, live_chunk="chunk-1"
        )

        result = self._invoke_with_mocks(runner, mocks, [], tmp_path / "sif.db")

        _mock_coll_repo, _mock_doc_repo, mock_chunk_repo, mock_searcher, mock_manager = mocks
        assert result.exit_code == 0
        mock_chunk_repo.delete_by_document.assert_called_once_with(doc.id)
        mock_searcher.delete_embeddings_by_document.assert_called_once_with(doc.id)
        mock_manager.embed_documents.assert_called_once()
        mock_searcher.add_embeddings_batch.assert_called_once()
        # O(N^2) guard: the loop must batch-read the completeness map once and
        # never fall back to a per-document completeness lookup.
        mock_searcher.get_all_embedded_chunk_ids.assert_called_once()
        mock_searcher.get_embedded_chunk_ids.assert_not_called()

    def test_embed_cmd_force_reembeds_fully_embedded_document(self, tmp_path: Path):
        """--force re-embeds even when the stored set exactly matches the live chunks."""
        runner = CliRunner()

        coll = self._make_collection()
        doc = self._make_document(content="hello world")

        mocks = self._make_embed_mocks(
            coll, [doc], embedded_chunk_ids={"chunk-1"}, live_chunk="chunk-1"
        )

        result = self._invoke_with_mocks(runner, mocks, ["--force"], tmp_path / "sif.db")

        _mock_coll_repo, _mock_doc_repo, mock_chunk_repo, mock_searcher, mock_manager = mocks
        assert result.exit_code == 0
        mock_chunk_repo.delete_by_document.assert_called_once_with(doc.id)
        mock_searcher.delete_embeddings_by_document.assert_called_once_with(doc.id)
        mock_manager.embed_documents.assert_called_once()
        assert mock_manager.embed_documents.call_args[0][0] == ["hello world"]
        mock_searcher.add_embeddings_batch.assert_called_once()


class TestRenderIndexEvent:
    """WR-01: user data must never be interpreted as Rich markup."""

    def _console(self) -> tuple[Console, io.StringIO]:
        buffer = io.StringIO()
        return Console(file=buffer, force_terminal=False, width=200), buffer

    def test_unchanged_payload_preserves_brackets(self) -> None:
        from sif.cli.commands.index import _render_index_event

        console, buffer = self._console()
        on_event = _render_index_event(console, MagicMock(), 0)

        on_event("unchanged report[v2].md")

        assert "report[v2].md" in buffer.getvalue()

    def test_error_payload_preserves_closing_tag(self) -> None:
        from sif.cli.commands.index import _render_index_event

        console, buffer = self._console()
        on_event = _render_index_event(console, MagicMock(), 0)

        on_event("error report[/dim].md")

        assert "report[/dim].md" in buffer.getvalue()

    def test_migrate_event_renders_one_line_with_count(self) -> None:
        """D-09: the migrate notice is one styled line naming the document count."""
        from sif.cli.commands.index import _render_index_event

        console, buffer = self._console()
        progress = MagicMock()
        on_event = _render_index_event(console, progress, 0)

        on_event("migrate 3")

        lines = buffer.getvalue().strip().splitlines()
        assert len(lines) == 1
        assert "Upgrading index format" in lines[0]
        assert "3" in lines[0]
        assert "[yellow]" not in lines[0]
        progress.advance.assert_called_once()


class TestStreamingEmbed:
    """D-15/D-16/D-02: per-document commits, resume, and stale-identity overwrite."""

    @staticmethod
    def _settings() -> Settings:
        return Settings(embedding_dim=DIM, model_name="test", cache_embeddings=False)

    @staticmethod
    def _delenv(monkeypatch) -> None:
        for var in ("SIF_EMBEDDING_DIM", "SIF_MODEL_TYPE", "SIF_MODEL_NAME"):
            monkeypatch.delenv(var, raising=False)

    def test_per_document_commit_survives_a_later_failure_and_resumes(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        """A mid-run failure leaves prior documents committed; a re-run embeds
        exactly the remainder (D-15/D-16)."""
        self._delenv(monkeypatch)
        db_path = tmp_path / "stream.db"
        settings = self._settings()
        _seed_real_index(
            db_path,
            settings,
            [
                ("/notes/a.md", "# A\n\nfirst document body"),
                ("/notes/b.md", "# B\n\nsecond document body"),
            ],
        )
        manager = _streaming_manager(_identity("model-a"), fail_on_call=2)

        result = _invoke_real_embed(db_path, manager, settings, [])
        assert result.exit_code != 0
        assert "Embedding failed for 1 document(s)" in result.output

        ids = _document_ids(db_path)
        assert _embedded_chunk_count(db_path, ids["/notes/a.md"]) >= 1
        assert _embedded_chunk_count(db_path, ids["/notes/b.md"]) == 0

        resume = _streaming_manager(_identity("model-a"))
        second = _invoke_real_embed(db_path, resume, settings, [])
        assert second.exit_code == 0
        assert len(resume.embed_documents.calls) == 1
        assert _embedded_chunk_count(db_path, ids["/notes/b.md"]) >= 1

        conn = sqlite3.connect(str(db_path))
        try:
            stored = read_identity(conn)
        finally:
            conn.close()
        assert stored is not None
        assert stored.source == "verified"
        assert stored.model_name == "model-a"

    def test_stale_identity_on_empty_index_is_overwritten_by_first_commit(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        """D-02: zero stored vectors accept any embedder, and the first commit
        overwrites a stale identity row as source=verified."""
        self._delenv(monkeypatch)
        db_path = tmp_path / "d02.db"
        settings = self._settings()
        _seed_real_index(db_path, settings, [("/notes/a.md", "# A\n\nbody")])

        seed = Database(db_path)
        try:
            with seed.connection:
                write_identity(seed.connection, _identity("model-a"))
        finally:
            seed.close()

        manager = _streaming_manager(_identity("model-b"))
        result = _invoke_real_embed(db_path, manager, settings, [])
        assert result.exit_code == 0, result.output

        conn = sqlite3.connect(str(db_path))
        try:
            stored = read_identity(conn)
        finally:
            conn.close()
        assert stored is not None
        assert stored.model_name == "model-b"
        assert stored.source == "verified"
        ids = _document_ids(db_path)
        assert _embedded_chunk_count(db_path, ids["/notes/a.md"]) >= 1

    def test_vacuous_full_force_certification_is_replaced_by_the_first_write(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        """An empty-index --force certifies vacuously; D-02 lets the next
        embedder's first commit replace that identity as verified."""
        self._delenv(monkeypatch)
        db_path = tmp_path / "vacuous.db"
        settings = self._settings()
        _seed_real_index(db_path, settings, [])

        first = _invoke_real_embed(
            db_path, _streaming_manager(_identity("model-a")), settings, ["--force"]
        )
        assert first.exit_code == 0, first.output

        conn = sqlite3.connect(str(db_path))
        try:
            vacuous = read_identity(conn)
        finally:
            conn.close()
        assert vacuous is not None
        assert vacuous.model_name == "model-a"
        assert vacuous.source == "verified"

        # A document arrives and a different same-dimension model runs without
        # --force: zero stored vectors keep the accept-any-embedder rule open.
        db = Database(db_path)
        try:
            with db.connection:
                coll = CollectionRepository(db.connection).get_by_name("notes")
                assert coll is not None
                DocumentRepository(db.connection).create(
                    Document(
                        path="/notes/a.md",
                        collection_id=coll.id,
                        content="# A\n\nbody",
                        title="A",
                    )
                )
        finally:
            db.close()

        second = _invoke_real_embed(db_path, _streaming_manager(_identity("model-b")), settings, [])
        assert second.exit_code == 0, second.output

        conn = sqlite3.connect(str(db_path))
        try:
            replaced = read_identity(conn)
        finally:
            conn.close()
        assert replaced is not None
        assert replaced.model_name == "model-b"
        assert replaced.source == "verified"
        ids = _document_ids(db_path)
        assert _embedded_chunk_count(db_path, ids["/notes/a.md"]) >= 1


class TestEmbedIdentityLocking:
    """CR-02: the identity decision is taken under the same flock as the writes."""

    def test_identity_resolution_runs_inside_the_index_lock(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        """A decision taken before the lock can go stale while waiting."""
        import contextlib

        from sif.cli.commands import index as index_module

        events: list[str] = []

        @contextlib.contextmanager
        def recording_lock(*_args, **_kwargs):
            events.append("lock-enter")
            yield
            events.append("lock-exit")

        real_resolve = index_module._resolve_identity

        def recording_resolve(conn, manager):
            events.append("identity")
            return real_resolve(conn, manager)

        monkeypatch.setattr(index_module, "index_lock", recording_lock)
        monkeypatch.setattr(index_module, "_resolve_identity", recording_resolve)

        coll_repo = MagicMock()
        coll_repo.list_all.return_value = []
        with (
            patch("sif.cli.commands.index.Database", return_value=MagicMock()),
            patch("sif.cli.commands.index.CollectionRepository", return_value=coll_repo),
            patch("sif.cli.commands.index.DocumentRepository", return_value=MagicMock()),
            patch("sif.cli.commands.index.DocumentChunkRepository", return_value=MagicMock()),
            patch(
                "sif.embedding.manager.EmbeddingManager.from_settings",
                return_value=MagicMock(),
            ),
            patch(
                "sif.config.settings.get_settings",
                return_value=MagicMock(model_name="test", lock_wait_timeout=1.0),
            ),
        ):
            result = CliRunner().invoke(embed_cmd, [], obj={"index_path": tmp_path / "index.db"})

        assert result.exit_code == 0, result.output
        assert events[:2] == ["lock-enter", "identity"]
        assert events[-1] == "lock-exit"


class TestLegacyUpgradeEndToEnd:
    """D-04/EMB-01: a pre-Phase-21 index upgrades, assumes, then certifies."""

    def test_legacy_upgrade_backfills_shadow_assumes_identity_and_certifies(
        self, tmp_path: Path, monkeypatch, caplog
    ) -> None:
        """First open backfills the shadow, warns once, and stores legacy-assumed;
        a complete unfiltered zero-failure --force rewrites it as verified."""
        TestStreamingEmbed._delenv(monkeypatch)
        db_path = tmp_path / "legacy.db"
        settings = TestStreamingEmbed._settings()
        ids = _make_pre_phase_21_index(db_path, settings, [("/notes/a.md", "# A\n\nalpha body")])
        doc_id = ids["/notes/a.md"]

        with caplog.at_level(logging.WARNING):
            result = _invoke_real_embed(db_path, _streaming_manager(_identity()), settings, [])
        assert result.exit_code == 0, result.output

        assert _shadow_ids(db_path) == [doc_id]
        legacy_warnings = [
            record
            for record in caplog.records
            if "Index predates embedder identity" in record.getMessage()
        ]
        assert len(legacy_warnings) == 1
        assumed = _stored_identity(db_path)
        assert assumed is not None
        assert assumed.source == "legacy-assumed"

        certified = _invoke_real_embed(
            db_path, _streaming_manager(_identity()), settings, ["--force"]
        )
        assert certified.exit_code == 0, certified.output
        verified = _stored_identity(db_path)
        assert verified is not None
        assert verified.source == "verified"

    def test_legacy_scoped_force_does_not_certify(self, tmp_path: Path, monkeypatch) -> None:
        """A --force scoped to one collection is not a certification run."""
        TestStreamingEmbed._delenv(monkeypatch)
        db_path = tmp_path / "legacy-scoped.db"
        settings = TestStreamingEmbed._settings()
        _make_pre_phase_21_index(db_path, settings, [("/notes/a.md", "# A\n\nalpha body")])

        result = _invoke_real_embed(
            db_path,
            _streaming_manager(_identity()),
            settings,
            ["--force", "--collection", "notes"],
        )
        assert result.exit_code == 0, result.output
        stored = _stored_identity(db_path)
        assert stored is not None
        assert stored.source == "legacy-assumed"

    def test_legacy_full_force_with_a_failure_does_not_certify(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        """Any failed document disqualifies certification for the run."""
        TestStreamingEmbed._delenv(monkeypatch)
        db_path = tmp_path / "legacy-failed.db"
        settings = TestStreamingEmbed._settings()
        _make_pre_phase_21_index(db_path, settings, [("/notes/a.md", "# A\n\nalpha body")])

        result = _invoke_real_embed(
            db_path,
            _streaming_manager(_identity(), fail_on_call=1),
            settings,
            ["--force"],
        )
        assert result.exit_code != 0
        stored = _stored_identity(db_path)
        assert stored is not None
        assert stored.source == "legacy-assumed"


class TestEmbedIdentityEnforcement:
    """D-03: an embed-path identity mismatch fails fast and writes no vectors."""

    def test_identity_mismatch_writes_no_vectors_and_names_both_identities(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        """The error carries both identities and the --force remedy; nothing is written."""
        TestStreamingEmbed._delenv(monkeypatch)
        db_path = tmp_path / "mismatch.db"
        settings = TestStreamingEmbed._settings()
        _seed_real_index(db_path, settings, [("/notes/a.md", "# A\n\nbody")])
        doc_id = _document_ids(db_path)["/notes/a.md"]
        _seed_legacy_embedding(db_path, doc_id)

        seed = Database(db_path)
        try:
            with seed.connection:
                write_identity(seed.connection, _identity("model-a"))
        finally:
            seed.close()

        manager = _streaming_manager(_identity("test"))
        result = _invoke_real_embed(db_path, manager, settings, [])

        assert result.exit_code != 0
        assert "Embedder identity mismatch" in result.output
        assert "modelscope:model-a" in result.output
        assert "modelscope:test" in result.output
        assert "sif index embed --force" in result.output
        assert manager.embed_documents.calls == []
        assert _embedded_chunk_count(db_path, doc_id) == 1
        assert _vector_count(db_path) == 1


class TestVacuumCommand:
    """`sif index vacuum` renders the three sizes and retryable errors cleanly."""

    @staticmethod
    def _settings() -> Settings:
        return Settings(embedding_dim=DIM, model_name="test", cache_embeddings=False)

    def test_vacuum_prints_before_after_and_reclaimed_and_exits_zero(self, tmp_path: Path) -> None:
        db_path = tmp_path / "vacuum.db"
        settings = self._settings()
        with (
            patch("sif.config.settings.get_settings", return_value=settings),
            patch(
                "sif.cli.commands.index.vacuum_index",
                return_value=VacuumResult(
                    before_bytes=4096, after_bytes=1024, reclaimed_bytes=3072
                ),
            ),
        ):
            result = CliRunner().invoke(index_group, ["vacuum"], obj={"index_path": db_path})

        assert result.exit_code == 0, result.output
        assert "Vacuum complete" in result.output
        assert "4096 bytes" in result.output
        assert "1024 bytes" in result.output
        assert "3072 bytes" in result.output
        assert "Reclaimed" in result.output

    def test_busy_vacuum_exits_non_zero_with_retry_text_and_no_traceback(
        self, tmp_path: Path
    ) -> None:
        db_path = tmp_path / "busy.db"
        settings = self._settings()
        busy = MaintenanceBusyError(
            "The WAL checkpoint could not complete because another connection is "
            "using the index. Retry once active readers finish."
        )
        with (
            patch("sif.config.settings.get_settings", return_value=settings),
            patch("sif.cli.commands.index.vacuum_index", side_effect=busy),
        ):
            result = CliRunner().invoke(index_group, ["vacuum"], obj={"index_path": db_path})

        assert result.exit_code != 0
        assert "Retry once active readers finish" in result.output
        assert "Traceback" not in result.output


class TestBackupCommand:
    """`sif index backup` prints the verified copy or a clean target error."""

    @staticmethod
    def _settings() -> Settings:
        return Settings(embedding_dim=DIM, model_name="test", cache_embeddings=False)

    def test_backup_prints_output_and_size_and_exits_zero(self, tmp_path: Path) -> None:
        db_path = tmp_path / "backup.db"
        target = tmp_path / "snapshot.db"
        settings = self._settings()
        with (
            patch("sif.config.settings.get_settings", return_value=settings),
            patch(
                "sif.cli.commands.index.backup_index",
                return_value=BackupResult(output=target.resolve(), bytes_written=2048),
            ),
        ):
            result = CliRunner().invoke(
                index_group,
                ["backup", "--output", str(target)],
                obj={"index_path": db_path},
                env={"COLUMNS": "200"},
            )

        assert result.exit_code == 0, result.output
        assert "Backup complete" in result.output
        assert str(target.resolve()) in result.output
        assert "2048 bytes" in result.output

    def test_existing_target_exits_non_zero_with_reason(self, tmp_path: Path) -> None:
        db_path = tmp_path / "backup.db"
        target = tmp_path / "existing.db"
        target.write_bytes(b"do not overwrite")
        settings = self._settings()
        with patch("sif.config.settings.get_settings", return_value=settings):
            result = CliRunner().invoke(
                index_group,
                ["backup", "--output", str(target)],
                obj={"index_path": db_path},
                env={"COLUMNS": "200"},
            )

        assert result.exit_code != 0
        assert "already exists" in result.output
        assert "Traceback" not in result.output
        assert target.read_bytes() == b"do not overwrite"
