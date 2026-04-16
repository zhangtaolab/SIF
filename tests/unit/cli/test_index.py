"""Tests for index CLI commands."""

from unittest.mock import MagicMock, patch

from click.testing import CliRunner

from docsift.cli.commands.index import embed_cmd


class TestEmbedCommand:
    """Tests for embed command."""

    def _make_collection(self, coll_id="coll1", name="notes", path="/notes"):
        from docsift.core.models import Collection

        return Collection(id=coll_id, name=name, path=path)

    def _make_document(self, doc_id="doc1", path="/notes/a.md", content="hello world"):
        from docsift.core.models import Document

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
            patch("docsift.cli.commands.index.Database", return_value=mock_db),
            patch(
                "docsift.cli.commands.index.CollectionRepository",
                return_value=mock_coll_repo,
            ),
            patch(
                "docsift.cli.commands.index.DocumentRepository",
                return_value=mock_doc_repo,
            ),
            patch(
                "docsift.cli.commands.index.DocumentChunkRepository",
                return_value=mock_chunk_repo,
            ),
            patch(
                "docsift.cli.commands.index.create_chunker",
                return_value=MagicMock(chunk=lambda text: [MagicMock(content=text, id="c1")]),
            ),
            patch(
                "docsift.embedding.manager.EmbeddingManager.from_settings",
                return_value=mock_manager,
            ),
            patch(
                "docsift.config.settings.get_settings",
                return_value=MagicMock(model_name="test", model_dump=lambda: {"model_name": "test"}),
            ),
            patch(
                "docsift.search.vector.VectorSearcher",
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
            patch("docsift.cli.commands.index.Database", return_value=mock_db),
            patch(
                "docsift.cli.commands.index.CollectionRepository",
                return_value=mock_coll_repo,
            ),
            patch(
                "docsift.cli.commands.index.DocumentRepository",
                return_value=mock_doc_repo,
            ),
            patch(
                "docsift.cli.commands.index.DocumentChunkRepository",
                return_value=mock_chunk_repo,
            ),
            patch(
                "docsift.cli.commands.index.create_chunker",
                return_value=MagicMock(
                    chunk=lambda text: [MagicMock(content=text, id=f"chunk-{text}")]
                ),
            ),
            patch(
                "docsift.embedding.manager.EmbeddingManager.from_settings",
                return_value=mock_manager,
            ),
            patch(
                "docsift.config.settings.get_settings",
                return_value=MagicMock(model_name="test", model_dump=lambda: {"model_name": "test"}),
            ),
            patch(
                "docsift.search.vector.VectorSearcher",
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
            return MagicMock(model_type=kwargs.get("update", {}).get("model_type", "sentence_transformers"))

        mock_settings = MagicMock()
        mock_settings.model_copy.side_effect = capture_model_copy
        mock_settings.model_type = "sentence_transformers"
        mock_settings.model_name = "test"

        mock_db = MagicMock()

        with (
            patch("docsift.cli.commands.index.Database", return_value=mock_db),
            patch(
                "docsift.cli.commands.index.CollectionRepository",
                return_value=mock_coll_repo,
            ),
            patch(
                "docsift.cli.commands.index.DocumentRepository",
                return_value=mock_doc_repo,
            ),
            patch(
                "docsift.cli.commands.index.DocumentChunkRepository",
                return_value=MagicMock(),
            ),
            patch(
                "docsift.embedding.manager.EmbeddingManager.from_settings",
                return_value=mock_manager,
            ),
            patch(
                "docsift.config.settings.get_settings",
                return_value=mock_settings,
            ),
            patch(
                "docsift.search.vector.VectorSearcher",
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
