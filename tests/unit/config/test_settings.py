"""Unit tests for SIF Settings configuration."""

import pytest

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
