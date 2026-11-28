"""Anchor generator, frozen prompt/parser, and fail-open (Phase 26, GEN-01/03/04).

The local GGUF path is exercised with injected ``llama_cpp`` modules so the
suite needs no model runtime; the remote path uses an injected transport so it
never touches the network. The default and remote-fake paths are additionally
run under a monkeypatched ``socket.socket`` that raises.
"""

from __future__ import annotations

import logging
import socket
import sqlite3
import sys
import types
from collections.abc import Iterator
from pathlib import Path
from types import SimpleNamespace
from typing import ClassVar

import pytest

from sif.config.settings import Settings
from sif.database.schema import SchemaManager
from sif.search import anchor as anchor_module
from sif.search.anchor import (
    MAX_ANCHOR_TERMS,
    PROMPT_TEMPLATE,
    PROMPT_VERSION,
    AnchorBackendUnavailable,
    AnchorGenerationFailed,
    AnchorResolver,
    LocalGGUFGenerator,
    OpenAICompatibleGenerator,
    derive_rule_anchors,
    parse_terms,
)
from sif.search.hybrid import SearchPipeline
from tests.support.bench import ConceptEmbedder, build_bench_db


BENCH_CORPUS = Path("tests/fixtures/bench/corpus")
QUERY = "machine learning"


@pytest.fixture(autouse=True)
def _reset_egress_latch() -> Iterator[None]:
    """The egress disclosure latch is process-level; isolate each test."""
    anchor_module._EGRESS_WARNED.clear()
    try:
        yield
    finally:
        anchor_module._EGRESS_WARNED.clear()


@pytest.fixture
def conn(tmp_path: Path) -> Iterator[sqlite3.Connection]:
    connection = sqlite3.connect(str(tmp_path / "sif.db"), isolation_level="IMMEDIATE")
    connection.row_factory = sqlite3.Row
    SchemaManager(connection, embedding_dim=8).create_all()
    try:
        yield connection
    finally:
        connection.close()


def _settings(**overrides: object) -> Settings:
    return Settings(_env_file=None, embedding_dim=8, cache_embeddings=False, **overrides)


def _gguf_file(tmp_path: Path) -> Path:
    model = tmp_path / "model.gguf"
    model.write_bytes(b"")
    return model


class FakeCriteriaList(list):
    """Stand-in for ``StoppingCriteriaList``; a plain list is not callable."""

    def __call__(self, tokens: object, logits: object) -> bool:
        return any(bool(criterion(tokens, logits)) for criterion in self)


class FakeLlama:
    """Records the constructor/completion kwargs and drives the criterion."""

    instances: ClassVar[list[FakeLlama]] = []

    def __init__(self, **kwargs: object) -> None:
        self.kwargs = kwargs
        self.completion_kwargs: dict[str, object] | None = None
        self.metadata: dict[str, str] = {"tokenizer.chat_template": "TEMPLATE"}
        FakeLlama.instances.append(self)

    def token_eos(self) -> int:
        return 2

    def token_bos(self) -> int:
        return 1

    def detokenize(self, tokens: list[int]) -> bytes:
        return b"<eos>" if tokens == [2] else b"<bos>"

    def create_completion(self, **kwargs: object) -> dict[str, object]:
        self.completion_kwargs = kwargs
        criteria = kwargs["stopping_criteria"]
        assert isinstance(criteria, FakeCriteriaList)
        criteria[0]([1], None)
        return {"choices": [{"text": "alpha\nbeta"}]}


class FakeFormatter:
    """Stand-in for ``Jinja2ChatFormatter``; records the rendered messages."""

    instances: ClassVar[list[FakeFormatter]] = []

    def __init__(self, **kwargs: object) -> None:
        self.kwargs = kwargs
        self.messages: list[dict[str, str]] | None = None
        FakeFormatter.instances.append(self)

    def __call__(self, messages: list[dict[str, str]]) -> SimpleNamespace:
        self.messages = messages
        return SimpleNamespace(prompt="RENDERED", stop=["</s>"])


def _install_fake_llama(monkeypatch: pytest.MonkeyPatch) -> None:
    FakeLlama.instances = []
    FakeFormatter.instances = []
    llama_cpp = types.ModuleType("llama_cpp")
    llama_cpp.Llama = FakeLlama  # type: ignore[attr-defined]
    llama_cpp.StoppingCriteriaList = FakeCriteriaList  # type: ignore[attr-defined]
    chat_format = types.ModuleType("llama_cpp.llama_chat_format")
    chat_format.Jinja2ChatFormatter = FakeFormatter  # type: ignore[attr-defined]
    llama_cpp.llama_chat_format = chat_format  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "llama_cpp", llama_cpp)
    monkeypatch.setitem(sys.modules, "llama_cpp.llama_chat_format", chat_format)


# --- GEN-01: frozen prompt and parser ---------------------------------------


def test_prompt_identity_is_frozen() -> None:
    assert PROMPT_VERSION == "anchor.v1"
    assert MAX_ANCHOR_TERMS == 10
    assert "{query}" in PROMPT_TEMPLATE
    assert PROMPT_TEMPLATE.endswith("Query: {query}\nTerms:\n")


def test_parse_terms_strips_numbering_and_bullets() -> None:
    assert parse_terms("1. alpha\n- ALPHA\n2) beta\n• gamma") == ["alpha", "beta", "gamma"]


def test_parse_terms_deduplicates_case_insensitively() -> None:
    assert parse_terms("Alpha\nalpha\nALPHA") == ["alpha"]


def test_parse_terms_caps_at_ten() -> None:
    text = "\n".join(f"term{i}" for i in range(15))
    assert len(parse_terms(text)) == MAX_ANCHOR_TERMS == 10


def test_parse_terms_drops_overlong_overworded_and_punctuation() -> None:
    overlong = "x" * 65
    overworded = "a b c d e f g"
    assert parse_terms(f"{overlong}\n{overworded}\n!!!\nkeep") == ["keep"]


def test_parse_terms_keeps_cjk() -> None:
    assert parse_terms("机器学习\n深度学习") == ["机器学习", "深度学习"]


# --- GEN-01/D-06: local GGUF generator --------------------------------------


def test_local_generator_renders_template_with_greedy_params(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _install_fake_llama(monkeypatch)
    model = _gguf_file(tmp_path)
    generator = LocalGGUFGenerator(model, max_tokens=7, timeout_ms=5000)

    assert generator.model_id == "model"
    assert generator.generate("hello") == "alpha\nbeta"

    llama = FakeLlama.instances[-1]
    assert llama.kwargs["embedding"] is False
    assert llama.kwargs["model_path"] == str(model)
    assert llama.completion_kwargs is not None
    kwargs = llama.completion_kwargs
    assert kwargs["prompt"] == "RENDERED"
    assert kwargs["stop"] == ["</s>"]
    assert kwargs["temperature"] == 0.0
    assert kwargs["top_k"] == 1
    assert kwargs["repeat_penalty"] == 1.0
    assert kwargs["max_tokens"] == 7

    formatter = FakeFormatter.instances[-1]
    assert formatter.kwargs["template"] == "TEMPLATE"
    assert formatter.messages == [{"role": "user", "content": "hello"}]


def test_local_generator_without_template_uses_raw_prompt(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _install_fake_llama(monkeypatch)
    python_llama = sys.modules["llama_cpp"].Llama

    class NoTemplateLlama(python_llama):  # type: ignore[misc, valid-type]
        def __init__(self, **kwargs: object) -> None:
            super().__init__(**kwargs)
            self.metadata = {}

    sys.modules["llama_cpp"].Llama = NoTemplateLlama  # type: ignore[attr-defined]
    generator = LocalGGUFGenerator(_gguf_file(tmp_path))

    assert generator.generate("hello") == "alpha\nbeta"
    assert FakeFormatter.instances == []
    assert NoTemplateLlama.instances[-1].completion_kwargs["prompt"] == "hello"


def test_local_generator_deadline_raises_timeout(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _install_fake_llama(monkeypatch)
    generator = LocalGGUFGenerator(_gguf_file(tmp_path), timeout_ms=1)
    ticks = iter([1000.0, 2000.0])
    monkeypatch.setattr("sif.search.anchor.time.monotonic", lambda: next(ticks))

    with pytest.raises(AnchorGenerationFailed) as excinfo:
        generator.generate("hello")
    assert excinfo.value.reason == "timeout"


def test_local_generator_rejects_invalid_paths(tmp_path: Path) -> None:
    with pytest.raises(AnchorBackendUnavailable) as excinfo:
        LocalGGUFGenerator("relative/model.gguf")
    assert excinfo.value.reason == "model_path_invalid"

    with pytest.raises(AnchorBackendUnavailable):
        LocalGGUFGenerator(tmp_path / "missing.gguf")

    wrong_suffix = tmp_path / "model.bin"
    wrong_suffix.write_bytes(b"")
    with pytest.raises(AnchorBackendUnavailable):
        LocalGGUFGenerator(wrong_suffix)


def test_local_generator_reports_missing_llama_cpp(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    generator = LocalGGUFGenerator(_gguf_file(tmp_path))
    monkeypatch.setitem(sys.modules, "llama_cpp", None)

    with pytest.raises(AnchorBackendUnavailable) as excinfo:
        generator._load()
    assert excinfo.value.reason == "llama_cpp_missing"


def test_runtime_missing_backend_falls_back_to_rule_anchors(
    monkeypatch: pytest.MonkeyPatch,
    conn: sqlite3.Connection,
    tmp_path: Path,
) -> None:
    settings = _settings(anchor_backend="gguf", anchor_model_path=_gguf_file(tmp_path))
    resolver = AnchorResolver(conn, settings)
    monkeypatch.setitem(sys.modules, "llama_cpp", None)

    resolution = resolver.resolve(QUERY)

    assert resolution.backend == "rules"
    assert resolution.fallback_reason == "llama_cpp_missing"
    assert resolution.terms == derive_rule_anchors(QUERY)


# --- GEN-04/D-15: remote generator and no-network defaults ------------------


def test_remote_generator_posts_chat_completions() -> None:
    seen: dict[str, object] = {}

    def transport(
        url: str,
        payload: dict[str, object],
        headers: dict[str, str],
        timeout_s: float,
    ) -> dict[str, object]:
        seen.update(url=url, payload=payload, headers=headers, timeout=timeout_s)
        return {"choices": [{"message": {"content": "alpha\nbeta"}}]}

    generator = OpenAICompatibleGenerator(
        "https://api.example.test/v1/",
        "model-x",
        api_key="sk-test",
        timeout_ms=1500,
        max_tokens=32,
        transport=transport,
    )

    assert generator.generate("hello") == "alpha\nbeta"
    assert seen["url"] == "https://api.example.test/v1/chat/completions"
    payload = seen["payload"]
    assert isinstance(payload, dict)
    assert payload["model"] == "model-x"
    assert payload["messages"] == [{"role": "user", "content": "hello"}]
    assert payload["temperature"] == 0
    assert payload["max_tokens"] == 32
    headers = seen["headers"]
    assert isinstance(headers, dict)
    assert headers["Authorization"] == "Bearer sk-test"
    assert seen["timeout"] == 1.5


def test_remote_generator_wraps_bad_responses() -> None:
    bad_shape = OpenAICompatibleGenerator(
        "https://api.example.test", "m", transport=lambda *_args: {"nope": 1}
    )
    with pytest.raises(AnchorGenerationFailed) as excinfo:
        bad_shape.generate("q")
    assert excinfo.value.reason == "invalid_response"

    def boom(*_args: object) -> dict[str, object]:
        raise OSError("down")

    failing = OpenAICompatibleGenerator("https://api.example.test", "m", transport=boom)
    with pytest.raises(AnchorGenerationFailed) as excinfo:
        failing.generate("q")
    assert excinfo.value.reason == "remote_error"


def test_remote_generator_rejects_non_http_base() -> None:
    with pytest.raises(AnchorBackendUnavailable) as excinfo:
        OpenAICompatibleGenerator("ftp://api.example.test", "m")
    assert excinfo.value.reason == "api_base_invalid"


def test_openai_backend_without_config_falls_back_to_rules(
    conn: sqlite3.Connection,
) -> None:
    resolver = AnchorResolver(conn, _settings(anchor_backend="openai"))

    resolution = resolver.resolve(QUERY)

    assert resolution.backend == "rules"
    assert resolution.fallback_reason == "unconfigured"
    assert resolution.terms == derive_rule_anchors(QUERY)


def test_openai_egress_is_disclosed_once_per_base_url(
    monkeypatch: pytest.MonkeyPatch,
    conn: sqlite3.Connection,
    caplog: pytest.LogCaptureFixture,
) -> None:
    def transport(
        _url: str,
        _payload: dict[str, object],
        _headers: dict[str, str],
        _timeout_s: float,
    ) -> dict[str, object]:
        return {"choices": [{"message": {"content": "alpha\nbeta"}}]}

    monkeypatch.setattr(anchor_module, "_post_json", transport)
    settings = _settings(
        anchor_backend="openai",
        anchor_api_base="https://api.example.test/v1",
        anchor_api_model="model-x",
        anchor_api_key="sk-secret",
    )

    with caplog.at_level(logging.WARNING):
        AnchorResolver(conn, settings).resolve("alpha")
        AnchorResolver(conn, settings).resolve("beta")

    egress = [record for record in caplog.records if "sends query text" in record.getMessage()]
    assert len(egress) == 1


def test_default_and_remote_fake_paths_open_no_socket(
    monkeypatch: pytest.MonkeyPatch,
    conn: sqlite3.Connection,
) -> None:
    def blocked(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("network access attempted")

    monkeypatch.setattr(socket, "socket", blocked)

    rules = AnchorResolver(conn, _settings()).resolve(QUERY)
    assert rules.backend == "rules"

    urls: list[str] = []

    def transport(
        url: str,
        _payload: dict[str, object],
        _headers: dict[str, str],
        _timeout_s: float,
    ) -> dict[str, object]:
        urls.append(url)
        return {"choices": [{"message": {"content": "alpha"}}]}

    generator = OpenAICompatibleGenerator("https://api.example.test", "m", transport=transport)
    assert generator.generate("q") == "alpha"
    assert urls == ["https://api.example.test/chat/completions"]


# --- GEN-03/D-13: fail-open against a real pipeline -------------------------


class FailingGenerator:
    """Always fails with a stable reason; counts attempts."""

    model_id = "fake-1"

    def __init__(self, reason: str = "timeout") -> None:
        self.reason = reason
        self.calls = 0

    def generate(self, _prompt: str) -> str:
        self.calls += 1
        raise AnchorGenerationFailed(self.reason)


@pytest.fixture
def bench_db() -> Iterator[sqlite3.Connection]:
    connection = build_bench_db(BENCH_CORPUS, ConceptEmbedder())
    try:
        yield connection
    finally:
        connection.close()


def test_fail_open_matches_lex_and_warns_once(
    bench_db: sqlite3.Connection,
    caplog: pytest.LogCaptureFixture,
) -> None:
    fake = FailingGenerator("timeout")
    resolver = AnchorResolver(bench_db, _settings(anchor_backend="gguf"), generator=fake)
    pipeline = SearchPipeline(bench_db, parse_prefix=True, anchor_resolver=resolver)

    with caplog.at_level(logging.WARNING):
        anchor_results = pipeline.search(f"anchor:{QUERY}")
        first = pipeline.last_anchor_resolution
        second_results = pipeline.search(f"anchor:{QUERY}")
        second = pipeline.last_anchor_resolution

    assert first is not None
    assert first.fallback_reason == "timeout"
    assert second is not None
    assert second.fallback_reason == "timeout"
    assert fake.calls == 1, "the same instance must not retry a failed query"
    warnings = [record for record in caplog.records if record.name.endswith("search.anchor")]
    assert len(warnings) == 1

    lex_results = pipeline.search(f"lex:{QUERY}")
    expected = [(r.document_id, r.score, r.rank) for r in lex_results]
    assert [(r.document_id, r.score, r.rank) for r in anchor_results] == expected
    assert [(r.document_id, r.score, r.rank) for r in second_results] == expected
