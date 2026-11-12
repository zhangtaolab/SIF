"""Unit tests for SIF Settings configuration."""

from unittest.mock import MagicMock

import pytest
from pydantic import ValidationError

from sif.config.settings import Settings, resolve_candidate_limit


def test_default_model_type_is_modelscope(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test that default model_type is modelscope."""
    # Hermetic against real env vars / .env files (e.g. a developer who
    # exported SIF_MODEL_TYPE=openai per the README workflow).
    monkeypatch.delenv("SIF_MODEL_TYPE", raising=False)
    settings = Settings(_env_file=None)
    assert settings.model_type == "modelscope"


def test_model_type_validation_accepts_valid_values() -> None:
    """Test that model_type accepts all valid backend values."""
    valid_types = ["sentence_transformers", "gguf", "openai", "modelscope"]
    for type_value in valid_types:
        settings = Settings(model_type=type_value)
        assert settings.model_type == type_value


def test_model_type_validation_rejects_invalid_values() -> None:
    """Test that model_type rejects invalid values."""
    with pytest.raises(ValueError, match="Invalid model_type"):
        Settings(model_type="invalid")


def test_model_type_validation_rejects_unimplemented_huggingface() -> None:
    """WR-07: "huggingface" validates nowhere — every path to it dead-ends."""
    with pytest.raises(ValueError, match="Invalid model_type: huggingface"):
        Settings(model_type="huggingface")


def test_reranker_model_type_validation_accepts_valid_values() -> None:
    """Test that reranker_model_type accepts the two dispatch backends."""
    valid_types = ["gguf", "sentence_transformers"]
    for type_value in valid_types:
        settings = Settings(reranker_model_type=type_value)
        assert settings.reranker_model_type == type_value


def test_reranker_model_type_validation_rejects_invalid_values() -> None:
    """WR-09: an unsupported reranker backend fails at settings-validation time."""
    with pytest.raises(ValueError, match="Invalid reranker_model_type"):
        Settings(reranker_model_type="cross-encoder")


def test_rerank_disabled_by_default(monkeypatch: pytest.MonkeyPatch) -> None:
    """D-12: rerank is opt-in — the default keeps the skip-rerank fast path free."""
    monkeypatch.delenv("SIF_RERANK_ENABLED", raising=False)
    settings = Settings(_env_file=None)
    assert settings.rerank_enabled is False


def test_rerank_enabled_via_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """SIF_RERANK_ENABLED=1 opts into reranker construction (the D-12 channel)."""
    with monkeypatch.context() as m:
        m.setenv("SIF_RERANK_ENABLED", "1")
        settings = Settings(_env_file=None)
        assert settings.rerank_enabled is True


def test_rerank_candidate_limit_defaults_to_20(monkeypatch: pytest.MonkeyPatch) -> None:
    """D-10: the unconfigured cap is 20."""
    monkeypatch.delenv("SIF_RERANK_CANDIDATE_LIMIT", raising=False)
    settings = Settings(_env_file=None)
    assert settings.rerank_candidate_limit == 20


def test_rerank_candidate_limit_accepts_boundaries() -> None:
    """D-10: 5 and 50 are the inclusive bounds."""
    assert Settings(_env_file=None, rerank_candidate_limit=5).rerank_candidate_limit == 5
    assert Settings(_env_file=None, rerank_candidate_limit=50).rerank_candidate_limit == 50


@pytest.mark.parametrize("value", ["4", "51"])
def test_rerank_candidate_limit_rejects_out_of_range(
    value: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    """SIF_RERANK_CANDIDATE_LIMIT outside 5..50 fails validation naming the field (D-10)."""
    with monkeypatch.context() as m:
        m.setenv("SIF_RERANK_CANDIDATE_LIMIT", value)
        with pytest.raises(ValidationError, match="rerank_candidate_limit"):
            Settings(_env_file=None)


def test_rerank_relative_threshold_defaults_to_half(monkeypatch: pytest.MonkeyPatch) -> None:
    """D-11: the unconfigured threshold keeps candidates scoring >= top_score * 0.5."""
    monkeypatch.delenv("SIF_RERANK_RELATIVE_THRESHOLD", raising=False)
    settings = Settings(_env_file=None)
    assert settings.rerank_relative_threshold == 0.5


def test_rerank_relative_threshold_accepts_boundaries() -> None:
    """D-11: the open-lower/closed-upper interval (0, 1] accepts 0.5 and 1.0."""
    assert Settings(_env_file=None, rerank_relative_threshold=0.5).rerank_relative_threshold == 0.5
    assert Settings(_env_file=None, rerank_relative_threshold=1.0).rerank_relative_threshold == 1.0


@pytest.mark.parametrize("value", ["0.0", "1.1"])
def test_rerank_relative_threshold_rejects_out_of_range(
    value: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    """SIF_RERANK_RELATIVE_THRESHOLD outside (0, 1] fails validation naming the field (D-11)."""
    with monkeypatch.context() as m:
        m.setenv("SIF_RERANK_RELATIVE_THRESHOLD", value)
        with pytest.raises(ValidationError, match="rerank_relative_threshold"):
            Settings(_env_file=None)


def test_resolve_candidate_limit_explicit_wins_over_setting() -> None:
    """An explicit -C value bypasses the settings cap entirely (then clamps)."""
    settings = Settings(_env_file=None, rerank_candidate_limit=30)
    assert resolve_candidate_limit(40, settings) == 40


def test_resolve_candidate_limit_omitted_uses_setting() -> None:
    """Without an explicit flag the SIF_RERANK_CANDIDATE_LIMIT value applies."""
    settings = Settings(_env_file=None, rerank_candidate_limit=30)
    assert resolve_candidate_limit(None, settings) == 30


def test_resolve_candidate_limit_clamps_explicit_into_bounds() -> None:
    """D-10: the shipped -C range is 1..200, so -C 200 -> 50 and -C 1 -> 5 at resolution."""
    settings = Settings(_env_file=None)
    assert resolve_candidate_limit(200, settings) == 50
    assert resolve_candidate_limit(1, settings) == 5


def test_resolve_candidate_limit_mock_settings_falls_back_to_20() -> None:
    """Pitfall 10: a MagicMock cap is truthy but not an int — it must resolve to 20."""
    assert resolve_candidate_limit(None, MagicMock()) == 20


def test_api_base_validation_accepts_https_url() -> None:
    """Test that api_base accepts HTTPS URLs."""
    settings = Settings(api_base="https://api.openai.com/v1")
    assert settings.api_base == "https://api.openai.com/v1"


def test_api_base_validation_accepts_http_url() -> None:
    """Test that api_base accepts HTTP URLs."""
    settings = Settings(api_base="http://localhost:8080/v1")
    assert settings.api_base == "http://localhost:8080/v1"


def test_api_base_validation_rejects_non_http_url() -> None:
    """Test that api_base rejects non-HTTP/HTTPS URLs."""
    with pytest.raises(ValueError, match="api_base must be an HTTP or HTTPS URL"):
        Settings(api_base="file:///etc/passwd")


def test_api_key_is_excluded_from_repr() -> None:
    """Test that api_key is excluded from representation."""
    settings = Settings(api_key="sk-secret")
    assert settings.api_key == "sk-secret"
    assert "sk-secret" not in repr(settings)


def test_api_key_is_excluded_from_model_dump(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test that api_key is excluded from serialized settings."""
    monkeypatch.delenv("SIF_API_KEY", raising=False)
    settings = Settings(api_key="sk-secret", _env_file=None)
    assert "api_key" not in settings.model_dump()
    assert "sk-secret" not in str(settings.model_dump())


def test_model_type_env_var_override(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test that SIF_MODEL_TYPE env var overrides model_type."""
    with monkeypatch.context() as m:
        m.setenv("SIF_MODEL_TYPE", "openai")
        settings = Settings()
        assert settings.model_type == "openai"


def test_fusion_defaults_match_prechange_behavior(monkeypatch: pytest.MonkeyPatch) -> None:
    """Phase 15 SC1: unconfigured fusion settings equal the hardcoded past (60/1.0/1.0)."""
    for var in ("SIF_RRF_K", "SIF_BM25_WEIGHT", "SIF_VECTOR_WEIGHT"):
        monkeypatch.delenv(var, raising=False)
    settings = Settings(_env_file=None)
    assert settings.rrf_k == 60
    assert settings.bm25_weight == 1.0
    assert settings.vector_weight == 1.0


def test_rrf_k_env_reaches_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    """SIF_RRF_K=10 loads into the settings field (the D-03 settings channel)."""
    with monkeypatch.context() as m:
        m.setenv("SIF_RRF_K", "10")
        settings = Settings(_env_file=None)
        assert settings.rrf_k == 10


def test_rrf_k_rejects_zero_naming_the_field(monkeypatch: pytest.MonkeyPatch) -> None:
    """SIF_RRF_K=0 fails Pydantic validation with rrf_k named (ge=1, D-03)."""
    with monkeypatch.context() as m:
        m.setenv("SIF_RRF_K", "0")
        with pytest.raises(ValidationError, match="rrf_k"):
            Settings(_env_file=None)


def test_bm25_weight_rejects_negative_naming_the_field(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """SIF_BM25_WEIGHT=-1 fails validation with bm25_weight named (gt=0, D-03)."""
    with monkeypatch.context() as m:
        m.setenv("SIF_BM25_WEIGHT", "-1")
        with pytest.raises(ValidationError, match="bm25_weight"):
            Settings(_env_file=None)


def test_vector_weight_has_no_upper_bound(monkeypatch: pytest.MonkeyPatch) -> None:
    """SIF_VECTOR_WEIGHT=1000 is accepted — the Phase 16 sweep grid is not capped."""
    with monkeypatch.context() as m:
        m.setenv("SIF_VECTOR_WEIGHT", "1000")
        settings = Settings(_env_file=None)
        assert settings.vector_weight == 1000.0


def test_query_history_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    """Phase 15 D-09/D-10: history defaults are enabled with a 500-row cap."""
    for var in ("SIF_QUERY_HISTORY_ENABLED", "SIF_QUERY_HISTORY_LIMIT"):
        monkeypatch.delenv(var, raising=False)
    settings = Settings(_env_file=None)
    assert settings.query_history_enabled is True
    assert settings.query_history_limit == 500


def test_query_history_enabled_env_opt_out(monkeypatch: pytest.MonkeyPatch) -> None:
    """SIF_QUERY_HISTORY_ENABLED=0 reaches the settings (the D-10 read gate)."""
    with monkeypatch.context() as m:
        m.setenv("SIF_QUERY_HISTORY_ENABLED", "0")
        settings = Settings(_env_file=None)
        assert settings.query_history_enabled is False


def test_query_history_limit_rejects_zero_naming_the_field(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """SIF_QUERY_HISTORY_LIMIT=0 fails validation with the field named (ge=1)."""
    with monkeypatch.context() as m:
        m.setenv("SIF_QUERY_HISTORY_LIMIT", "0")
        with pytest.raises(ValidationError, match="query_history_limit"):
            Settings(_env_file=None)


def test_default_search_type_rejects_unknown_value() -> None:
    """SIF_DEFAULT_SEARCH_TYPE is limited to bm25, vector, and hybrid."""
    with pytest.raises(ValidationError, match="default_search_type"):
        Settings(_env_file=None, default_search_type="semantic")


def test_mcp_transport_rejects_unknown_value() -> None:
    """SIF_MCP_TRANSPORT is limited to stdio and http."""
    with pytest.raises(ValidationError, match="mcp_transport"):
        Settings(_env_file=None, mcp_transport="sse")


def test_wired_settings_reach_settings_object() -> None:
    """The formerly-unread settings are accepted and typed by Settings."""
    settings = Settings(
        _env_file=None,
        debug=True,
        log_level="debug",
        chunk_size=256,
        chunk_overlap=32,
        default_search_type="bm25",
        default_limit=5,
        mcp_host="0.0.0.0",
        mcp_port=9000,
        mcp_transport="http",
    )

    assert settings.debug is True
    assert settings.log_level == "DEBUG"
    assert settings.chunk_size == 256
    assert settings.chunk_overlap == 32
    assert settings.default_search_type == "bm25"
    assert settings.default_limit == 5
    assert settings.mcp_host == "0.0.0.0"
    assert settings.mcp_port == 9000
    assert settings.mcp_transport == "http"
