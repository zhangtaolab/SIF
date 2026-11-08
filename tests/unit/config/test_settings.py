"""Unit tests for SIF Settings configuration."""

import pytest
from pydantic import ValidationError

from sif.config.settings import Settings


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
