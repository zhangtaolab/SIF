"""Anchor ``SIF_ANCHOR_*`` settings (Phase 26, CTR-04/D-15).

The coverage assertion at the end is the guard the docs diff gate cannot
provide: a Settings field missing from ``generate_config_ref.SECTIONS`` is
silently dropped from ``docs/configuration.md`` while ``make docs-generate``
still reports zero diff.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from scripts.generate_config_ref import SECTIONS
from sif.config.settings import Settings


def test_anchor_defaults() -> None:
    """D-05/D-14/D-15/D-16: the default surface is the zero-model rules path."""
    settings = Settings(_env_file=None)

    assert settings.anchor_backend == "rules"
    assert settings.anchor_model_path is None
    assert settings.anchor_api_base is None
    assert settings.anchor_api_model is None
    assert settings.anchor_api_key is None
    assert settings.anchor_timeout_ms == 5000
    assert settings.anchor_max_calls == 100
    assert settings.anchor_max_tokens == 64
    assert settings.anchor_cache_ttl == 2592000
    assert settings.anchor_vocab_guard is False


def test_anchor_backend_rejects_unknown_values() -> None:
    with pytest.raises(ValidationError, match="anchor_backend"):
        Settings(_env_file=None, anchor_backend="bogus")


def test_anchor_api_base_must_be_http() -> None:
    with pytest.raises(ValidationError, match="anchor_api_base"):
        Settings(_env_file=None, anchor_api_base="ftp://example.test")


def test_anchor_model_path_expands_user() -> None:
    settings = Settings(_env_file=None, anchor_model_path="~/models/anchor.gguf")
    assert settings.anchor_model_path == Path.home() / "models" / "anchor.gguf"


def test_anchor_api_key_is_excluded_from_repr_and_dump() -> None:
    """The key follows the existing ``api_key`` secret convention."""
    settings = Settings(_env_file=None, anchor_api_key="sk-secret")

    assert "sk-secret" not in repr(settings)
    assert "anchor_api_key" not in settings.model_dump()


def test_every_settings_field_is_in_a_documented_section() -> None:
    """CTR-04: no Settings field may be silently dropped by the generator."""
    documented = {field for _section, fields in SECTIONS for field in fields}
    missing = sorted(set(Settings.model_fields) - documented)

    assert missing == []
