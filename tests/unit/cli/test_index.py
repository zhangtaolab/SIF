"""Tests for index CLI commands."""

import io
import math
import sqlite3
import types
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from click.testing import CliRunner
from rich.console import Console

from sif.cli.commands.index import embed_cmd
from sif.config.settings import Settings
from sif.core.models import Collection, Document
from sif.database.database import Database
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
