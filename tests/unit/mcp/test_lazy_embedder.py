"""D-15 lazy-embedder and prefix-first routing matrix (Phase 22).

The embedder must never load at construction or for the no-load tools, must
load once under concurrency, must latch a failure with exactly one warning,
must use the loaded identity's dimension, and must route ``lex:`` queries to
BM25 before any load decision (prefix stripped).
"""

from __future__ import annotations

import logging
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from sif.config.settings import Settings
from sif.database.database import Database
from sif.embedding.identity import EmbedderIdentity
from sif.mcp import backend as backend_module
from sif.mcp.backend import SearchBackend


def _settings(**overrides: object) -> Settings:
    values: dict[str, object] = {
        "embedding_dim": 8,
        "model_name": "test",
        "cache_embeddings": False,
    }
    values.update(overrides)
    return Settings(_env_file=None, **values)


def _identity(dimension: int = 8) -> EmbedderIdentity:
    return EmbedderIdentity(
        schema_version=1,
        cache_model_id="sentence_transformers:test",
        model_name="test",
        model_type="sentence_transformers",
        api_base=None,
        dimension=dimension,
        pooling="mean",
        normalized=True,
        query_prompt=None,
        document_prompt=None,
        prompt_supported=False,
        revision=None,
        source="verified",
    )


def _seed_db(tmp_path: Path, dimension: int = 8) -> tuple[Path, Settings]:
    """Real schema plus one matching document, model-free."""
    settings = _settings(embedding_dim=dimension)
    db_path = tmp_path / "lazy.db"
    db = Database(db_path)
    try:
        db.init_schema(embedding_dim=dimension)
        now = datetime.now(timezone.utc).isoformat()
        with db.connection:
            db.connection.execute(
                "INSERT INTO collections (id, name, path, created_at, updated_at)"
                " VALUES ('c1', 'notes', '/vault', ?, ?)",
                (now, now),
            )
            db.connection.execute(
                "INSERT INTO documents (id, collection_id, path, filename, title,"
                " content, checksum, mtime, created_at, updated_at)"
                " VALUES ('d1', 'c1', '/vault/seed.md', 'seed.md', 'Seed',"
                " 'seed paragraph quantum machine', 'ck-1', 1.0, ?, ?)",
                (now, now),
            )
    finally:
        db.close()
    return db_path, settings


class _StubEmbedder:
    """Protocol-only embedder returning fixed vectors."""

    def __init__(self, dimension: int) -> None:
        self._dimension = dimension

    def embed(self, _text: str) -> list[float]:
        return [0.1] * self._dimension

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        return [self.embed(text) for text in texts]

    @property
    def dimension(self) -> int:
        return self._dimension


class _StubManager:
    """Manager double with a hook so the load can be observed/raced."""

    def __init__(
        self,
        identity: EmbedderIdentity | None = None,
        dimension: int = 8,
        load_hook: object | None = None,
    ) -> None:
        self._identity = identity or _identity(dimension)
        self._embedder = _StubEmbedder(dimension)
        self._load_hook = load_hook
        self.load_calls = 0

    @property
    def model(self) -> _StubEmbedder:
        return self._embedder

    def load_model(self) -> None:
        self.load_calls += 1
        if callable(self._load_hook):
            self._load_hook()

    def get_identity(self) -> EmbedderIdentity:
        return self._identity

    def embed_query(self, text: str) -> list[float]:
        return self._embedder.embed(text)

    def embed_queries(self, texts: list[str]) -> list[list[float]]:
        return [self._embedder.embed(text) for text in texts]


def _core_result() -> MagicMock:
    result = MagicMock()
    result.document_id = "d1"
    result.path = "/vault/seed.md"
    result.title = "Seed"
    result.content = None
    result.score = 0.9
    result.highlights = ["seed"]
    result.rank = 1
    result.collection_name = "notes"
    result.vectors_stale = False
    result.chunk_id = None
    result.sequence = None
    result.chunk_matches = 0
    # D-11 citation fields: the direct BM25 routes have no snippet window.
    result.snippet = None
    result.line_start = None
    result.line_end = None
    return result


class TestNoLoadSurfaces:
    """D-15: status/lex/metadata/get/multi_get and construction never load."""

    @pytest.mark.asyncio
    async def test_no_load_tools_and_construction_never_touch_the_loader(
        self, tmp_path: Path
    ) -> None:
        db_path, settings = _seed_db(tmp_path)
        with patch(
            "sif.mcp.backend.EmbeddingManager.from_settings",
            side_effect=AssertionError("no-load tool touched the embedder"),
        ) as from_settings:
            backend = SearchBackend(str(db_path), settings=settings)
            await backend.get_status()
            await backend.lex_search("seed")
            await backend.metadata(
                collections=None,
                filter_node=None,
                match=None,
                min_count=1,
                sort="count",
                limit=50,
                value_limit=10,
            )
            assert await backend.get_document("missing") is None
            documents, _errors = await backend.get_documents_by_pattern("*.md")
            assert [document.doc_id for document in documents] == ["d1"]

        from_settings.assert_not_called()
        assert backend._load_attempted is False


class TestOneAttempt:
    """D-15: one load, reused; concurrency shares the single attempt."""

    @pytest.mark.asyncio
    async def test_first_query_and_vec_search_load_once_and_reuse(self, tmp_path: Path) -> None:
        db_path, settings = _seed_db(tmp_path)
        backend = SearchBackend(str(db_path), settings=settings)
        manager = _StubManager()

        with (
            patch(
                "sif.mcp.backend.EmbeddingManager.from_settings", return_value=manager
            ) as from_settings,
            patch("sif.mcp.backend.SearchPipeline") as pipeline_cls,
            patch("sif.mcp.backend.VectorSearcher") as vec_cls,
        ):
            pipeline_cls.return_value.search.return_value = []
            vec_cls.return_value.search.return_value = []
            await backend.hybrid_search("quantum")
            await backend.vec_search("quantum")
            await backend.hybrid_search("quantum")

        assert from_settings.call_count == 1
        assert manager.load_calls == 1
        assert backend._load_attempted is True
        assert backend._manager is manager
        assert backend._identity == manager.get_identity()
        assert backend._dimension == 8

    def test_concurrent_first_requests_perform_exactly_one_load(self, tmp_path: Path) -> None:
        db_path, settings = _seed_db(tmp_path)
        backend = SearchBackend(str(db_path), settings=settings)
        manager = _StubManager(load_hook=lambda: time.sleep(0.05))
        barrier = threading.Barrier(2)

        def _attempt() -> object:
            barrier.wait()
            return backend._ensure_embedder()

        with (
            patch(
                "sif.mcp.backend.EmbeddingManager.from_settings", return_value=manager
            ) as from_settings,
            ThreadPoolExecutor(max_workers=2) as pool,
        ):
            results = [pool.submit(_attempt) for _ in range(2)]
            returned = [result.result() for result in results]

        assert from_settings.call_count == 1
        assert manager.load_calls == 1
        # CR-01: the waiting caller must receive the manager, never ``None``
        # (which ``hybrid_search`` would treat as a latched failure).
        assert returned == [manager, manager]
        assert backend._manager is manager

    def test_a_waiter_arriving_mid_load_receives_the_manager(self, tmp_path: Path) -> None:
        """CR-01 regression: "load in progress" is not "load failed".

        Thread A is parked inside ``load_model`` when thread B calls
        ``_ensure_embedder``. Before the fix, B's unlocked fast path saw
        ``_load_attempted=True`` with ``_manager=None`` and answered ``None``
        (BM25 degrade); it must instead block on the lock and receive the
        same manager A is about to publish.
        """
        db_path, settings = _seed_db(tmp_path)
        backend = SearchBackend(str(db_path), settings=settings)
        load_started = threading.Event()
        release_load = threading.Event()

        def _slow_load() -> None:
            load_started.set()
            assert release_load.wait(timeout=5.0)

        manager = _StubManager(load_hook=_slow_load)

        with (
            patch(
                "sif.mcp.backend.EmbeddingManager.from_settings", return_value=manager
            ) as from_settings,
            ThreadPoolExecutor(max_workers=2) as pool,
        ):
            first = pool.submit(backend._ensure_embedder)
            assert load_started.wait(timeout=5.0)
            second = pool.submit(backend._ensure_embedder)
            release_load.set()
            assert first.result(timeout=5.0) is manager
            assert second.result(timeout=5.0) is manager

        assert from_settings.call_count == 1
        assert manager.load_calls == 1


class TestHonestFailure:
    """D-15: a latched failure warns once, degrades query, and refuses vec."""

    @pytest.mark.asyncio
    async def test_failed_load_warns_once_and_query_degrades_to_bm25(
        self, tmp_path: Path, caplog
    ) -> None:
        db_path, settings = _seed_db(tmp_path)
        backend = SearchBackend(str(db_path), settings=settings)

        with (
            patch(
                "sif.mcp.backend.EmbeddingManager.from_settings",
                side_effect=RuntimeError("missing backend"),
            ) as from_settings,
            caplog.at_level(logging.WARNING, logger=backend_module.logger.name),
        ):
            first = await backend.hybrid_search("quantum")
            second = await backend.hybrid_search("quantum")

        assert {result.doc_id for result in first} == {"d1"}
        assert {result.doc_id for result in second} == {"d1"}
        warnings = [
            record
            for record in caplog.records
            if "Embedding model unavailable" in record.getMessage()
        ]
        assert len(warnings) == 1
        assert "docsif[embed]" in warnings[0].getMessage()
        assert from_settings.call_count == 1
        assert backend._load_failed is True

    @pytest.mark.asyncio
    async def test_failed_load_vec_search_raises_the_remedy_without_retry(
        self, tmp_path: Path
    ) -> None:
        db_path, settings = _seed_db(tmp_path)
        backend = SearchBackend(str(db_path), settings=settings)

        with patch(
            "sif.mcp.backend.EmbeddingManager.from_settings",
            side_effect=RuntimeError("missing backend"),
        ) as from_settings:
            await backend.hybrid_search("quantum")
            with pytest.raises(RuntimeError, match='pip install "docsif\\[embed\\]"'):
                await backend.vec_search("quantum")
            context = pytest.raises(RuntimeError, match='pip install "docsif\\[embed\\]"')
            with context:
                await backend.vec_search("quantum")

        assert from_settings.call_count == 1


class TestLoadedDimension:
    """D-15/Pitfall 9: the loaded identity's dimension governs the pipeline."""

    @pytest.mark.asyncio
    async def test_loaded_identity_dimension_overrides_the_settings_value(
        self, tmp_path: Path
    ) -> None:
        db_path, settings = _seed_db(tmp_path, dimension=8)
        backend = SearchBackend(str(db_path), settings=settings)
        manager = _StubManager(identity=_identity(32), dimension=32)

        with (
            patch("sif.mcp.backend.EmbeddingManager.from_settings", return_value=manager),
            patch("sif.mcp.backend.SearchPipeline") as pipeline_cls,
        ):
            pipeline_cls.return_value.search.return_value = []
            await backend.hybrid_search("quantum")

        assert pipeline_cls.call_args.kwargs["embedding_dim"] == 32
        assert backend._dimension == 32


class TestPrefixFirstRouting:
    """D-15: lex: routes to BM25 before any load; failures strip prefixes."""

    @pytest.mark.asyncio
    async def test_lex_prefix_never_loads_and_strips_the_prefix(self, tmp_path: Path) -> None:
        db_path, settings = _seed_db(tmp_path)
        backend = SearchBackend(str(db_path), settings=settings)

        with (
            patch(
                "sif.mcp.backend.EmbeddingManager.from_settings",
                side_effect=AssertionError("lex: must not load"),
            ) as from_settings,
            patch.object(
                SearchBackend,
                "_ensure_embedder",
                side_effect=AssertionError("lex: must not load"),
            ) as ensure,
            patch("sif.mcp.backend.BM25Searcher") as bm25_cls,
            patch(
                "sif.mcp.backend.enrich_results",
                side_effect=lambda conn, results: results,  # noqa: ARG005
            ) as enrich,
        ):
            bm25_cls.return_value.search.return_value = [_core_result()]
            results = await backend.hybrid_search("lex: seed paragraph")

        ensure.assert_not_called()
        from_settings.assert_not_called()
        bm25_cls.return_value.search.assert_called_once()
        assert bm25_cls.return_value.search.call_args[0][0] == "seed paragraph"
        assert enrich.call_count == 1
        assert [result.doc_id for result in results] == ["d1"]

    @pytest.mark.asyncio
    async def test_vec_prefix_on_a_load_failure_strips_the_prefix_for_bm25(
        self, tmp_path: Path, caplog
    ) -> None:
        db_path, settings = _seed_db(tmp_path)
        backend = SearchBackend(str(db_path), settings=settings)

        with (
            patch(
                "sif.mcp.backend.EmbeddingManager.from_settings",
                side_effect=RuntimeError("missing backend"),
            ),
            patch("sif.mcp.backend.BM25Searcher") as bm25_cls,
            caplog.at_level(logging.WARNING, logger=backend_module.logger.name),
        ):
            bm25_cls.return_value.search.return_value = [_core_result()]
            results = await backend.hybrid_search("vec: quantum")

        assert bm25_cls.return_value.search.call_args[0][0] == "quantum"
        assert [result.doc_id for result in results] == ["d1"]
        warnings = [
            record
            for record in caplog.records
            if "Embedding model unavailable" in record.getMessage()
        ]
        assert len(warnings) == 1
