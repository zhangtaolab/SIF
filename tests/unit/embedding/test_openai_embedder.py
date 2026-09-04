"""Tests for OpenAIEmbedder in sif.embedding.embedder."""

from __future__ import annotations

import json
import logging
import math
import types
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import numpy as np
import pytest

from sif.config.settings import Settings
from sif.embedding.embedder import OpenAIEmbedder
from sif.embedding.manager import EmbeddingManager


DIM = 8

# Probe input used by OpenAIEmbedder for dimension detection — embed calls in
# these tests never send exactly this input, so create() calls can be filtered.
_PROBE_INPUT = ["."]


def _unit_vector(values: list[float]) -> list[float]:
    """Return values L2-normalized to unit length."""
    arr = np.asarray(values, dtype=float)
    return (arr / np.linalg.norm(arr)).tolist()


VEC8 = _unit_vector([1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0])


def _make_fake_openai(
    vec: list[float] | None = None,
    *,
    item_count: int | None = None,
    fail_on_texts: frozenset[str] = frozenset(),
    content_aware: bool = False,
    reverse_order: bool = False,
    indices: list[int] | None = None,
) -> tuple[types.ModuleType, list[dict], list[dict]]:
    """Build a fake openai module backed by a recording client.

    Args:
        vec: Default embedding vector returned per requested text.
        item_count: Force every create() response to carry exactly this many
            embedding items regardless of input length (ragged-response test).
        fail_on_texts: Raise when any of these texts appears in a request.
        content_aware: Return vectors derived from each input text's length
            so output ordering is observable from results alone.
        reverse_order: Return response items in reverse request order, each
            still carrying its correct index field.
        indices: Force these index values on the response items
            (misindexed-response test).

    Returns:
        Tuple of (fake module, recorded constructor kwargs, recorded
        create() kwargs lists).
    """
    if vec is None:
        vec = VEC8
    constructor_calls: list[dict] = []
    create_calls: list[dict] = []

    def _vector_for(text: str) -> list[float]:
        if content_aware:
            return [float(len(text)), 1.0] + [0.0] * (len(vec) - 2)
        return list(vec)

    class _FakeEmbeddings:
        def create(self, **kwargs: object) -> SimpleNamespace:
            create_calls.append(kwargs)
            texts = list(kwargs["input"])
            if any(t in fail_on_texts for t in texts):
                raise RuntimeError("simulated endpoint failure")
            if indices is not None:
                order = list(indices)
            else:
                count = len(texts) if item_count is None else item_count
                order = list(range(count))
            if reverse_order:
                order.reverse()
            data = [
                SimpleNamespace(index=i, embedding=_vector_for(texts[i % len(texts)]))
                for i in order
            ]
            return SimpleNamespace(data=data)

    class _FakeClient:
        def __init__(self) -> None:
            self.embeddings = _FakeEmbeddings()

    def _openai_constructor(**kwargs: object) -> _FakeClient:
        constructor_calls.append(kwargs)
        return _FakeClient()

    module = types.ModuleType("openai")
    module.OpenAI = _openai_constructor
    return module, constructor_calls, create_calls


def _embed_calls(create_calls: list[dict]) -> list[dict]:
    """Filter out the dimension-probe call (input == ['.'])."""
    return [c for c in create_calls if list(c["input"]) != _PROBE_INPUT]


class TestOpenAIEmbedderEndToEnd:
    """End-to-end tracer: Settings -> manager -> factory -> OpenAIEmbedder."""

    def test_settings_to_embeddings_end_to_end(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("SIF_MODEL_TYPE", raising=False)
        monkeypatch.delenv("SIF_API_KEY", raising=False)
        monkeypatch.delenv("SIF_API_BASE", raising=False)
        monkeypatch.delenv("SIF_EMBEDDING_DIM", raising=False)
        monkeypatch.delenv("SIF_CACHE_EMBEDDINGS", raising=False)

        fake_module, ctor_calls, _create_calls = _make_fake_openai()

        settings = Settings(
            model_type="openai",
            model_name="text-embedding-3-small",
            api_key="test-key",
            api_base="https://api.example.com/v1",
            cache_embeddings=False,
            embedding_dim=DIM,
        )

        with patch.dict("sys.modules", {"openai": fake_module}):
            manager = EmbeddingManager.from_settings(settings)
            response = manager.embed(["hello world"])

        assert len(response.embeddings) == 1
        assert response.embeddings[0] == pytest.approx(VEC8)
        assert response.dimensions == DIM
        assert len(ctor_calls) == 1
        assert ctor_calls[0]["api_key"] == "test-key"
        assert ctor_calls[0]["base_url"] == "https://api.example.com/v1"


class TestOpenAIEmbedderBehavior:
    """Unit behaviors of OpenAIEmbedder against a mocked endpoint."""

    def test_embed_batch_chunks_at_batch_size(self) -> None:
        fake_module, _ctor, create_calls = _make_fake_openai(content_aware=True)

        with patch.dict("sys.modules", {"openai": fake_module}):
            embedder = OpenAIEmbedder(model_name="test-model", embedding_dim=DIM)
            texts = ["t" * ((i % 7) + 1) for i in range(150)]
            result = embedder.embed_batch(texts)

        embeds = _embed_calls(create_calls)
        assert len(embeds) == 3
        assert [len(e["input"]) for e in embeds] == [64, 64, 22]
        assert len(result) == 150
        for text, vector in zip(texts, result, strict=True):
            expected = _unit_vector([float(len(text)), 1.0] + [0.0] * (DIM - 2))
            assert vector == pytest.approx(expected)

    def test_ragged_response_raises_runtime_error(self) -> None:
        fake_module, _ctor, _create = _make_fake_openai(item_count=1)

        with patch.dict("sys.modules", {"openai": fake_module}):
            embedder = OpenAIEmbedder(model_name="test-model", embedding_dim=DIM)
            with pytest.raises(RuntimeError, match=r"test-model.*expected 3.*got 1"):
                embedder.embed_batch(["a", "b", "c"])

    def test_embed_batch_normalizes_reordered_response(self) -> None:
        fake_module, _ctor, _create = _make_fake_openai(content_aware=True, reverse_order=True)

        with patch.dict("sys.modules", {"openai": fake_module}):
            embedder = OpenAIEmbedder(model_name="test-model", embedding_dim=DIM)
            result = embedder.embed_batch(["a", "bb", "ccc"])

        # Vectors must stay associated with their own text despite the
        # reversed response order.
        expected = [
            _unit_vector([float(len(t)), 1.0] + [0.0] * (DIM - 2)) for t in ("a", "bb", "ccc")
        ]
        for got, want in zip(result, expected, strict=True):
            assert got == pytest.approx(want)

    def test_misindexed_response_raises_runtime_error(self) -> None:
        fake_module, _ctor, _create = _make_fake_openai(indices=[0, 0, 1])

        with patch.dict("sys.modules", {"openai": fake_module}):
            embedder = OpenAIEmbedder(model_name="test-model", embedding_dim=DIM)
            with pytest.raises(RuntimeError, match="misindexed"):
                embedder.embed_batch(["a", "b", "c"])

    def test_import_error_logs_install_hint(self, caplog: pytest.LogCaptureFixture) -> None:
        original_import = __builtins__["__import__"]

        def fail_openai_import(name, *args, **kwargs):
            if name == "openai":
                raise ImportError("No module named 'openai'")
            return original_import(name, *args, **kwargs)

        with (
            patch("builtins.__import__", fail_openai_import),
            caplog.at_level(logging.ERROR, logger="sif.embedding.embedder"),
            pytest.raises(ImportError),
        ):
            OpenAIEmbedder(model_name="test-model")

        assert "sif[openai]" in caplog.text

    def test_embeddings_are_l2_normalized(self) -> None:
        raw = [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0]
        fake_module, _ctor, _create = _make_fake_openai(raw)

        with patch.dict("sys.modules", {"openai": fake_module}):
            embedder = OpenAIEmbedder(model_name="test-model", embedding_dim=DIM)
            single = embedder.embed("hello")
            batch = embedder.embed_batch(["a", "b"])

        for vector in [single, *batch]:
            assert math.isclose(float(np.linalg.norm(vector)), 1.0, abs_tol=1e-9)

    def test_embed_batch_no_partial_result_on_midbatch_failure(self) -> None:
        fake_module, _ctor, _create = _make_fake_openai(fail_on_texts=frozenset({"c"}))

        with patch.dict("sys.modules", {"openai": fake_module}):
            embedder = OpenAIEmbedder(model_name="test-model", embedding_dim=DIM, batch_size=2)
            with pytest.raises(RuntimeError, match="simulated endpoint failure"):
                embedder.embed_batch(["a", "b", "c", "d"])

    def test_embed_batch_empty_input_returns_empty(self) -> None:
        fake_module, _ctor, create_calls = _make_fake_openai()

        with patch.dict("sys.modules", {"openai": fake_module}):
            embedder = OpenAIEmbedder(model_name="test-model", embedding_dim=DIM)
            assert embedder.embed_batch([]) == []

        assert _embed_calls(create_calls) == []


class TestOpenAIEmbedderDimensionCache:
    """Dimension auto-detection with local cache and fail-fast validation (D-05)."""

    def test_probe_once_then_cache_hit(self, tmp_path: Path) -> None:
        fake_module, _ctor, create_calls = _make_fake_openai()

        with patch.dict("sys.modules", {"openai": fake_module}):
            first = OpenAIEmbedder(
                model_name="text-embedding-3-small",
                embedding_dim=None,
                cache_dir=str(tmp_path),
            )
            assert first.dimension == DIM
            assert len(create_calls) == 1
            assert (tmp_path / "openai_dim_cache.json").exists()

            create_calls.clear()
            second = OpenAIEmbedder(
                model_name="text-embedding-3-small",
                embedding_dim=None,
                cache_dir=str(tmp_path),
            )
            assert second.dimension == DIM

        assert len(create_calls) == 0

    def test_cache_file_schema(self, tmp_path: Path) -> None:
        fake_module, _ctor, _calls = _make_fake_openai()

        with patch.dict("sys.modules", {"openai": fake_module}):
            OpenAIEmbedder(model_name="m1", embedding_dim=None, cache_dir=str(tmp_path))

        data = json.loads((tmp_path / "openai_dim_cache.json").read_text())
        entry = data["default::m1"]
        assert entry["dimension"] == DIM
        # detected_at must parse as an ISO-8601 timestamp
        datetime.fromisoformat(entry["detected_at"])

    def test_expired_cache_entry_reprobes(self, tmp_path: Path) -> None:
        stale = datetime.now(timezone.utc) - timedelta(days=8)
        cache_file = tmp_path / "openai_dim_cache.json"
        cache_file.write_text(
            json.dumps({"default::m1": {"dimension": 999, "detected_at": stale.isoformat()}})
        )

        fake_module, _ctor, create_calls = _make_fake_openai()
        with patch.dict("sys.modules", {"openai": fake_module}):
            embedder = OpenAIEmbedder(model_name="m1", embedding_dim=None, cache_dir=str(tmp_path))

        assert len(create_calls) == 1
        assert embedder.dimension == DIM
        data = json.loads(cache_file.read_text())
        assert data["default::m1"]["dimension"] == DIM

    def test_no_cache_dir_probes_per_instance(self) -> None:
        fake_module, _ctor, create_calls = _make_fake_openai()

        with patch.dict("sys.modules", {"openai": fake_module}):
            embedder = OpenAIEmbedder(model_name="m1", embedding_dim=None, cache_dir=None)
            assert embedder.dimension == DIM

        assert len(create_calls) == 1

    def test_per_model_cache_keys(self, tmp_path: Path) -> None:
        fake_module, _ctor, create_calls = _make_fake_openai()

        with patch.dict("sys.modules", {"openai": fake_module}):
            OpenAIEmbedder(model_name="m1", embedding_dim=None, cache_dir=str(tmp_path))

            create_calls.clear()
            OpenAIEmbedder(model_name="m2", embedding_dim=None, cache_dir=str(tmp_path))

        assert len(create_calls) == 1
        data = json.loads((tmp_path / "openai_dim_cache.json").read_text())
        assert set(data) == {"default::m1", "default::m2"}
        assert data["default::m1"]["dimension"] == DIM
        assert data["default::m2"]["dimension"] == DIM

    def test_dim_cache_keys_include_endpoint(self, tmp_path: Path) -> None:
        """Same model name on two endpoints must not share a cache entry."""
        vec6 = _unit_vector([1.0, 2.0, 3.0, 4.0, 5.0, 6.0])
        fake_module, _ctor, create_calls = _make_fake_openai(vec6)

        with patch.dict("sys.modules", {"openai": fake_module}):
            OpenAIEmbedder(
                model_name="m1",
                embedding_dim=None,
                api_base="https://a.example/v1",
                cache_dir=str(tmp_path),
            )

            create_calls.clear()
            second = OpenAIEmbedder(
                model_name="m1",
                embedding_dim=None,
                api_base="https://b.example/v1",
                cache_dir=str(tmp_path),
            )

        # Endpoint B probed instead of reusing endpoint A's entry, and both
        # entries coexist in the cache file.
        assert second.dimension == 6
        assert len(create_calls) == 1
        data = json.loads((tmp_path / "openai_dim_cache.json").read_text())
        assert "https://a.example/v1::m1" in data
        assert "https://b.example/v1::m1" in data

    def test_dimension_mismatch_fails_fast(self, monkeypatch: pytest.MonkeyPatch) -> None:
        for var in (
            "SIF_MODEL_TYPE",
            "SIF_API_KEY",
            "SIF_API_BASE",
            "SIF_EMBEDDING_DIM",
            "SIF_CACHE_EMBEDDINGS",
        ):
            monkeypatch.delenv(var, raising=False)

        vec6 = _unit_vector([1.0, 2.0, 3.0, 4.0, 5.0, 6.0])
        fake_module, _ctor, _calls = _make_fake_openai(vec6)

        settings = Settings(
            model_type="openai",
            model_name="text-embedding-3-small",
            api_key="test-key",
            api_base="https://api.example.com/v1",
            cache_embeddings=False,
            embedding_dim=DIM,
        )

        with patch.dict("sys.modules", {"openai": fake_module}):
            manager = EmbeddingManager.from_settings(settings)
            with pytest.raises(RuntimeError) as excinfo:
                manager.embed(["hello world"])

        message = str(excinfo.value)
        assert "6" in message
        assert str(DIM) in message
        assert "SIF_EMBEDDING_DIM" in message

    def test_corrupt_cache_treated_as_miss(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        cache_file = tmp_path / "openai_dim_cache.json"
        cache_file.write_text("{not valid json")

        fake_module, _ctor, create_calls = _make_fake_openai()
        with (
            patch.dict("sys.modules", {"openai": fake_module}),
            caplog.at_level(logging.WARNING, logger="sif.embedding.embedder"),
        ):
            embedder = OpenAIEmbedder(model_name="m1", embedding_dim=None, cache_dir=str(tmp_path))

        assert embedder.dimension == DIM
        assert len(create_calls) == 1
        assert "cache" in caplog.text.lower()
        data = json.loads(cache_file.read_text())
        assert data["default::m1"]["dimension"] == DIM

    def test_manager_path_probe_matches_settings_dim(self, monkeypatch: pytest.MonkeyPatch) -> None:
        for var in (
            "SIF_MODEL_TYPE",
            "SIF_API_KEY",
            "SIF_API_BASE",
            "SIF_EMBEDDING_DIM",
            "SIF_CACHE_EMBEDDINGS",
        ):
            monkeypatch.delenv(var, raising=False)

        fake_module, _ctor, create_calls = _make_fake_openai()
        settings = Settings(
            model_type="openai",
            model_name="text-embedding-3-small",
            api_key="test-key",
            api_base="https://api.example.com/v1",
            cache_embeddings=False,
            embedding_dim=DIM,
        )

        with patch.dict("sys.modules", {"openai": fake_module}):
            manager = EmbeddingManager.from_settings(settings)
            response = manager.embed(["hello world"])

        probes = [c for c in create_calls if list(c["input"]) == _PROBE_INPUT]
        assert len(probes) == 1
        assert probes[0]["model"] == settings.model_name
        assert response.embeddings[0] == pytest.approx(VEC8)
        assert response.dimensions == DIM
