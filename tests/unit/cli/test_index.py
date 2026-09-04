"""Tests for index CLI commands."""

import types
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from click.testing import CliRunner

from sif.cli.commands.index import embed_cmd
from sif.config.settings import Settings


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

    def test_embed_cmd_uses_embedding_manager(self):
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
        mock_manager.embed.return_value = MagicMock(embeddings=[[0.1, 0.2]])
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
                obj={"index_path": MagicMock(exists=lambda: True)},
            )

        assert result.exit_code == 0
        mock_manager.embed.assert_called_once()
        call_args = mock_manager.embed.call_args[0][0]
        assert call_args == ["hello world"]

    def test_embed_cmd_embedding_failure_exits_nonzero(self):
        """embed_cmd must exit non-zero when embedding a collection fails."""
        runner = CliRunner()

        coll = self._make_collection()
        doc = self._make_document(content="hello world")

        mock_coll_repo = MagicMock()
        mock_coll_repo.list_all.return_value = [coll]

        mock_doc_repo = MagicMock()
        mock_doc_repo.list_by_collection.return_value = [doc]

        mock_manager = MagicMock()
        mock_manager.embed.side_effect = RuntimeError("simulated backend failure")

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
                return_value=MagicMock(model_name="test"),
            ),
        ):
            result = runner.invoke(
                embed_cmd,
                [],
                obj={"index_path": MagicMock(exists=lambda: True)},
            )

        assert result.exit_code != 0
        assert "Error embedding collection" in result.output
        assert "Embedding failed for 1 collection(s): notes" in result.output

    def test_embed_cmd_backend_load_failure_exits_nonzero(self):
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
                obj={"index_path": MagicMock(exists=lambda: True)},
            )

        assert result.exit_code != 0
        assert "Embedding backend not installed" in result.output

    def test_embed_cmd_batches_across_documents(self):
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
        mock_manager.embed.return_value = MagicMock(embeddings=[[0.1], [0.2]])
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
                obj={"index_path": MagicMock(exists=lambda: True)},
            )

        assert result.exit_code == 0
        mock_vector_searcher.add_embeddings_batch.assert_called_once()
        batch = mock_vector_searcher.add_embeddings_batch.call_args[0][0]
        assert len(batch) == 2

    def test_embed_cmd_respects_model_type_override(self):
        """embed_cmd passes --model-type to settings override."""
        runner = CliRunner()

        coll = self._make_collection()

        mock_coll_repo = MagicMock()
        mock_coll_repo.list_all.return_value = [coll]

        mock_doc_repo = MagicMock()
        mock_doc_repo.list_by_collection.return_value = []

        mock_manager = MagicMock()
        mock_manager.embed.return_value = MagicMock(embeddings=[])
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
                obj={"index_path": MagicMock(exists=lambda: True)},
            )

        assert result.exit_code == 0
        assert captured_updates["model_type"] == "openai"

    def test_embed_cmd_openai_model_type_reaches_endpoint(self):
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
                obj={"index_path": MagicMock(exists=lambda: True)},
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
        mock_searcher.get_embedded_chunk_ids.return_value = set(embedded_chunk_ids)

        mock_manager = MagicMock()
        mock_manager.embed.return_value = MagicMock(embeddings=[[0.1, 0.2]])
        mock_manager.get_model_info.return_value = {"loaded": True, "embedding_dim": 8}

        return mock_coll_repo, mock_doc_repo, mock_chunk_repo, mock_searcher, mock_manager

    def _invoke_with_mocks(self, runner, mocks, args):
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
            patch(
                "sif.embedding.manager.EmbeddingManager.from_settings",
                return_value=mock_manager,
            ),
            patch(
                "sif.config.settings.get_settings",
                return_value=MagicMock(model_name="test"),
            ),
            patch(
                "sif.search.vector.VectorSearcher",
                return_value=mock_searcher,
            ),
        ):
            return runner.invoke(
                embed_cmd,
                args,
                obj={"index_path": MagicMock(exists=lambda: True)},
            )

    def test_embed_cmd_default_skips_fully_embedded_document(self):
        """Default run: a complete chunk/embedding set is skipped with no embed call."""
        runner = CliRunner()

        coll = self._make_collection()
        doc = self._make_document(content="hello world")

        mocks = self._make_embed_mocks(
            coll, [doc], embedded_chunk_ids={"chunk-1"}, live_chunk="chunk-1"
        )

        result = self._invoke_with_mocks(runner, mocks, [])

        _mock_coll_repo, _mock_doc_repo, mock_chunk_repo, mock_searcher, mock_manager = mocks
        assert result.exit_code == 0
        mock_chunk_repo.delete_by_document.assert_not_called()
        mock_searcher.delete_embeddings_by_document.assert_not_called()
        mock_manager.embed.assert_not_called()
        # The skip line names the document
        assert "Already embedded" in result.output
        assert doc.path in result.output

    def test_embed_cmd_default_heals_stale_embedding_state(self):
        """Default run: an orphaned embedding set (stale rows) is re-embedded."""
        runner = CliRunner()

        coll = self._make_collection()
        doc = self._make_document(content="hello world")

        # Stored set carries an orphaned row from an older run — sets mismatch
        mocks = self._make_embed_mocks(
            coll, [doc], embedded_chunk_ids={"chunk-1", "orphan-chunk"}, live_chunk="chunk-1"
        )

        result = self._invoke_with_mocks(runner, mocks, [])

        _mock_coll_repo, _mock_doc_repo, mock_chunk_repo, mock_searcher, mock_manager = mocks
        assert result.exit_code == 0
        mock_chunk_repo.delete_by_document.assert_called_once_with(doc.id)
        mock_searcher.delete_embeddings_by_document.assert_called_once_with(doc.id)
        mock_manager.embed.assert_called_once()
        mock_searcher.add_embeddings_batch.assert_called_once()

    def test_embed_cmd_force_reembeds_fully_embedded_document(self):
        """--force re-embeds even when the stored set exactly matches the live chunks."""
        runner = CliRunner()

        coll = self._make_collection()
        doc = self._make_document(content="hello world")

        mocks = self._make_embed_mocks(
            coll, [doc], embedded_chunk_ids={"chunk-1"}, live_chunk="chunk-1"
        )

        result = self._invoke_with_mocks(runner, mocks, ["--force"])

        _mock_coll_repo, _mock_doc_repo, mock_chunk_repo, mock_searcher, mock_manager = mocks
        assert result.exit_code == 0
        mock_chunk_repo.delete_by_document.assert_called_once_with(doc.id)
        mock_searcher.delete_embeddings_by_document.assert_called_once_with(doc.id)
        mock_manager.embed.assert_called_once()
        assert mock_manager.embed.call_args[0][0] == ["hello world"]
        mock_searcher.add_embeddings_batch.assert_called_once()
