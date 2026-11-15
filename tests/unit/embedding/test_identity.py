"""Wave-0 battery for the embedder identity record (EMB-01, D-01/D-02/D-04).

Every test here uses a real on-disk SQLite database: the identity round trip
goes through the real ``index_meta`` table and the mode matrix runs against a
real vec0 ``document_embeddings`` table, because the contract is about
persisted state, not in-memory objects.
"""

from __future__ import annotations

import json
import logging
import os
import sqlite3
import subprocess
import sys
from dataclasses import replace
from pathlib import Path

import pytest

from sif.config.settings import Settings
from sif.database.database import Database
from sif.database.schema import SchemaManager
from sif.embedding.identity import (
    IDENTITY_KEY,
    EmbedderIdentity,
    IdentityCheck,
    build_identity,
    build_settings_identity,
    certify_identity,
    check_identity,
    ensure_legacy_identity,
    format_cache_model_id,
    identity_matches,
    read_identity,
    reset_identity_state,
    schema_embedding_dim,
    warn_identity_mismatch_once,
    write_identity,
)
from sif.embedding.prompts import PromptScheme, resolve_prompt_scheme
from sif.models.embedding import EmbeddingConfig, ModelType


_DIM = 2
_QWEN = "Qwen/Qwen3-Embedding-0.6B"


class _FakeModel:
    """Loadable-model double exposing the provenance properties."""

    def __init__(
        self,
        dimension: int = _DIM,
        pooling_mode: str = "last_token",
        revision: str | None = None,
    ) -> None:
        self.dimension = dimension
        self.pooling_mode = pooling_mode
        self.revision = revision


def _config(
    model_name: str = _QWEN,
    model_type: ModelType = ModelType.MODELSCOPE,
    embedding_dim: int = _DIM,
    **kwargs: object,
) -> EmbeddingConfig:
    return EmbeddingConfig(
        model_type=model_type,
        model_name=model_name,
        embedding_dim=embedding_dim,
        **kwargs,
    )


def _build(
    model: object | None = None,
    scheme: PromptScheme | None = None,
    config: EmbeddingConfig | None = None,
    source: str = "verified",
) -> EmbedderIdentity:
    return build_identity(
        config or _config(),
        model,
        scheme or PromptScheme(None, None, True),
        source=source,
    )


@pytest.fixture
def db(tmp_path: Path):
    """A real schema-managed index at ``FLOAT[2]``; skip without sqlite-vec."""
    database = Database(tmp_path / "index.db")
    database.init_schema(embedding_dim=_DIM)
    if schema_embedding_dim(database.connection) is None:
        database.close()
        pytest.skip("sqlite-vec not available")
    try:
        yield database
    finally:
        database.close()


def _bare_conn(tmp_path: Path, *, with_vectors: bool = False) -> sqlite3.Connection:
    """A connection with the real index_meta DDL and optional vec0 table."""
    conn = sqlite3.connect(tmp_path / "bare.db")
    conn.row_factory = sqlite3.Row
    SchemaManager(conn, embedding_dim=_DIM)._create_index_meta_table()
    if with_vectors:
        import sqlite_vec

        conn.enable_load_extension(True)
        sqlite_vec.load(conn)
        conn.enable_load_extension(False)
        conn.execute(
            f"""
            CREATE VIRTUAL TABLE document_embeddings USING vec0(
                embedding_id TEXT PRIMARY KEY,
                document_id TEXT NOT NULL,
                chunk_id TEXT,
                embedding FLOAT[{_DIM}]
            )
            """
        )
    conn.commit()
    return conn


def _seed_vector(conn: sqlite3.Connection, doc_id: str = "d1") -> None:
    conn.execute(
        "INSERT INTO document_embeddings (embedding_id, document_id, chunk_id, embedding) "
        "VALUES (?, ?, ?, vec_f32(?))",
        (f"e-{doc_id}", doc_id, f"c-{doc_id}", json.dumps([0.1] * _DIM)),
    )
    conn.commit()


def _identity_warning_count(caplog: pytest.LogCaptureFixture, needle: str) -> int:
    return sum(needle in record.message for record in caplog.records)


# =============================================================================
# Round trip + fingerprint stability
# =============================================================================


class TestIdentityPersistence:
    def test_round_trip_through_real_index_meta(self, db: Database) -> None:
        conn = db.connection
        identity = _build(_FakeModel(revision="rev-abc"))
        write_identity(conn, identity)
        conn.commit()

        stored = read_identity(conn)
        assert stored == identity
        assert stored is not None
        assert stored.fingerprint() == identity.fingerprint()
        assert stored.to_json() == identity.to_json()
        assert stored.source == "verified"
        row = conn.execute("SELECT value FROM index_meta WHERE key = ?", (IDENTITY_KEY,)).fetchone()
        assert row is not None
        assert row[0] == identity.to_json()

    def test_two_builds_are_byte_identical(self) -> None:
        model = _FakeModel()
        scheme = PromptScheme("web_search_query", None, True)
        first = _build(model, scheme)
        second = _build(model, scheme)
        assert first.fingerprint() == second.fingerprint()
        assert first.to_json() == second.to_json()

    def test_fingerprint_stable_across_subprocess(self) -> None:
        code = (
            "from sif.embedding.identity import build_identity\n"
            "from sif.embedding.prompts import PromptScheme\n"
            "from sif.models.embedding import EmbeddingConfig\n"
            "cfg = EmbeddingConfig(model_type='modelscope', model_name='QWEN', embedding_dim=2)\n"
            "print(build_identity(cfg, None, PromptScheme(None, None, True)).fingerprint())\n"
        ).replace("QWEN", _QWEN)
        src = Path(__file__).resolve().parents[3] / "src"
        env = dict(os.environ)
        env["PYTHONPATH"] = f"{src}{os.pathsep}{env.get('PYTHONPATH', '')}"
        completed = subprocess.run(
            [sys.executable, "-c", code],
            capture_output=True,
            text=True,
            env=env,
            check=False,
        )
        assert completed.returncode == 0, completed.stderr
        assert completed.stdout.strip() == _build().fingerprint()

    def test_source_is_excluded_from_fingerprint(self) -> None:
        verified = _build(source="verified")
        assumed = _build(source="legacy-assumed")
        assert verified.fingerprint() == assumed.fingerprint()
        assert verified.display_fingerprint() == assumed.display_fingerprint()
        assert verified.to_json() != assumed.to_json()

    def test_format_cache_model_id_matches_manager_format(self) -> None:
        assert format_cache_model_id("modelscope", _QWEN, None) == f"modelscope:{_QWEN}"
        assert (
            format_cache_model_id("openai", "text-embedding-3-small", "https://x/v1")
            == "openai:text-embedding-3-small@https://x/v1"
        )
        assert format_cache_model_id("modelscope", _QWEN, "") == f"modelscope:{_QWEN}"

    def test_build_identity_defensive_against_mock(self) -> None:
        from unittest.mock import MagicMock

        identity = _build(MagicMock())
        assert identity.pooling == "unknown"
        assert identity.revision is None
        assert identity.dimension == _DIM

    def test_build_settings_identity_has_no_model_provenance(self) -> None:
        settings = Settings(
            model_type="modelscope",
            model_name=_QWEN,
            api_base="https://api.example.com/v1",
            embedding_dim=_DIM,
        )
        identity = build_settings_identity(settings, PromptScheme(None, None, True))
        assert identity.pooling == "unknown"
        assert identity.revision is None
        assert identity.api_base == "https://api.example.com/v1"
        assert identity.dimension == _DIM
        assert identity.cache_model_id == f"modelscope:{_QWEN}@https://api.example.com/v1"


# =============================================================================
# Defensive parsing
# =============================================================================


class TestFromJson:
    def test_malformed_json_returns_none_with_warning(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        with caplog.at_level(logging.WARNING):
            assert EmbedderIdentity.from_json("{bad json") is None
        assert _identity_warning_count(caplog, "Ignoring unreadable embedder identity") == 1

    def test_non_object_returns_none_with_warning(self, caplog: pytest.LogCaptureFixture) -> None:
        with caplog.at_level(logging.WARNING):
            assert EmbedderIdentity.from_json("[]") is None
        assert _identity_warning_count(caplog, "expected a JSON object") == 1

    def test_payload_missing_required_field_returns_none(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        payload = json.loads(_build().to_json())
        del payload["dimension"]
        with caplog.at_level(logging.WARNING):
            assert EmbedderIdentity.from_json(json.dumps(payload)) is None
        assert _identity_warning_count(caplog, "missing required field") == 1

    def test_non_string_field_returns_none(self, caplog: pytest.LogCaptureFixture) -> None:
        payload = json.loads(_build().to_json())
        payload["cache_model_id"] = 7
        with caplog.at_level(logging.WARNING):
            assert EmbedderIdentity.from_json(json.dumps(payload)) is None
        assert _identity_warning_count(caplog, "is not a string") == 1

    def test_read_identity_absent_key_returns_none(self, tmp_path: Path) -> None:
        conn = _bare_conn(tmp_path)
        try:
            assert read_identity(conn) is None
        finally:
            conn.close()


# =============================================================================
# Field-wise comparison
# =============================================================================


class TestIdentityMatches:
    @pytest.mark.parametrize(
        ("overrides", "expected"),
        [
            ({}, True),
            ({"cache_model_id": "modelscope:other-model"}, False),
            ({"dimension": 3}, False),
            ({"normalized": False}, False),
            ({"query_prompt": "other-query"}, False),
            ({"document_prompt": "other-document"}, False),
            ({"pooling": "unknown"}, True),
            ({"pooling": "mean"}, False),
            ({"revision": None}, True),
            ({"revision": "rev-other"}, False),
        ],
    )
    def test_comparison_matrix(self, overrides: dict, expected: bool) -> None:
        base = _build(_FakeModel(revision="rev-1"), PromptScheme("q", "d", True))
        current = replace(base, **overrides)
        assert identity_matches(base, current) is expected

    def test_unknown_on_either_side_tolerates_pooling(self) -> None:
        model_side = _build(_FakeModel(pooling_mode="last_token"))
        settings_side = _build()
        assert identity_matches(settings_side, model_side) is True
        assert identity_matches(model_side, settings_side) is True


# =============================================================================
# Legacy assumed identity + certification
# =============================================================================


class TestLegacyIdentity:
    def test_assumed_write_warns_once_and_returns_stored(
        self, db: Database, caplog: pytest.LogCaptureFixture
    ) -> None:
        conn = db.connection
        _seed_vector(conn)
        current = _build()

        with caplog.at_level(logging.WARNING):
            assumed = ensure_legacy_identity(conn, current)
        conn.commit()

        assert assumed.source == "legacy-assumed"
        assert _identity_warning_count(caplog, "Index predates embedder identity") == 1

        with caplog.at_level(logging.WARNING):
            second = ensure_legacy_identity(conn, current)
        assert second == assumed
        assert _identity_warning_count(caplog, "Index predates embedder identity") == 1

    def test_no_vectors_writes_nothing(self, tmp_path: Path) -> None:
        conn = _bare_conn(tmp_path, with_vectors=True)
        try:
            returned = ensure_legacy_identity(conn, _build())
            conn.commit()
            assert returned == _build()
            assert read_identity(conn) is None
        finally:
            conn.close()

    def test_certify_rewrites_as_verified(self, db: Database) -> None:
        conn = db.connection
        assumed = replace(_build(), source="legacy-assumed")
        write_identity(conn, assumed)
        conn.commit()

        certified = certify_identity(conn, _build())
        conn.commit()
        stored = read_identity(conn)
        assert certified.source == "verified"
        assert stored is not None
        assert stored.source == "verified"
        assert stored.fingerprint() == _build().fingerprint()


# =============================================================================
# Schema dimension read
# =============================================================================


class TestSchemaEmbeddingDim:
    def test_reads_real_vec0_width(self, db: Database) -> None:
        assert schema_embedding_dim(db.connection) == _DIM

    def test_absent_table_returns_none(self, tmp_path: Path) -> None:
        conn = _bare_conn(tmp_path)
        try:
            assert schema_embedding_dim(conn) is None
        finally:
            conn.close()

    def test_table_without_float_width_returns_none(self, tmp_path: Path) -> None:
        conn = _bare_conn(tmp_path)
        try:
            conn.execute("CREATE TABLE document_embeddings (embedding_id TEXT PRIMARY KEY)")
            assert schema_embedding_dim(conn) is None
        finally:
            conn.close()


# =============================================================================
# Mode matrix
# =============================================================================


class TestCheckIdentity:
    def test_init_is_width_only_and_never_raises(self, db: Database) -> None:
        check = check_identity(db.connection, _build(config=_config(embedding_dim=3)), mode="init")
        assert check.status == "dimension_mismatch"
        assert check.dimension_mismatch is True
        assert check.untrusted is True

    def test_init_assumes_legacy_identity_when_vectors_exist(
        self, db: Database, caplog: pytest.LogCaptureFixture
    ) -> None:
        conn = db.connection
        _seed_vector(conn)
        with caplog.at_level(logging.WARNING):
            check = check_identity(conn, _build(), mode="init")
        conn.commit()
        assert check.status == "ok"
        assert check.stored is not None
        assert check.stored.source == "legacy-assumed"
        assert _identity_warning_count(caplog, "Index predates embedder identity") == 1

    def test_init_writes_nothing_without_vectors(self, db: Database) -> None:
        conn = db.connection
        check = check_identity(conn, _build(), mode="init")
        assert check.status == "ok"
        assert check.stored is None
        assert read_identity(conn) is None

    def test_embed_assumes_identity_with_vectors(
        self, db: Database, caplog: pytest.LogCaptureFixture
    ) -> None:
        conn = db.connection
        _seed_vector(conn)
        with caplog.at_level(logging.WARNING):
            check = check_identity(conn, _build(), mode="embed")
        conn.commit()
        assert check.status == "ok"
        assert read_identity(conn) is not None
        assert _identity_warning_count(caplog, "Index predates embedder identity") == 1

    def test_search_never_writes_legacy_identity(self, db: Database) -> None:
        conn = db.connection
        _seed_vector(conn)
        check = check_identity(conn, _build(), mode="search")
        assert check.status == "ok"
        assert check.stored is None
        assert read_identity(conn) is None

    def test_search_matching_identity_is_ok(self, db: Database) -> None:
        conn = db.connection
        identity = _build()
        write_identity(conn, identity)
        _seed_vector(conn)
        assert check_identity(conn, identity, mode="search").status == "ok"

    def test_search_mismatched_identity_marks_untrusted(self, db: Database) -> None:
        conn = db.connection
        other = _build(config=_config(model_name="other/model"))
        write_identity(conn, other)
        _seed_vector(conn)

        check = check_identity(conn, _build(), mode="search")
        assert check.status == "mismatch"
        assert check.untrusted is True
        assert check.stored == other

    def test_embed_mismatched_identity_fails_check(self, db: Database) -> None:
        conn = db.connection
        other = _build(config=_config(model_name="other/model"))
        write_identity(conn, other)
        _seed_vector(conn)

        check = check_identity(conn, _build(), mode="embed")
        assert check.status == "mismatch"
        assert check.untrusted is True
        assert read_identity(conn) == other

    def test_stored_identity_dimension_disagreement_is_dimension_mismatch(
        self, db: Database
    ) -> None:
        conn = db.connection
        write_identity(conn, _build(config=_config(embedding_dim=4)))
        _seed_vector(conn)

        check = check_identity(conn, _build(), mode="search")
        assert check.status == "dimension_mismatch"
        assert check.dimension_mismatch is True

    @pytest.mark.parametrize("mode", ["embed", "search"])
    def test_no_stored_vectors_accepts_any_same_dimension_model(
        self, db: Database, mode: str
    ) -> None:
        conn = db.connection
        stale = _build(config=_config(model_name="other/same-dimension-model"))
        write_identity(conn, stale)
        conn.commit()

        check = check_identity(conn, _build(), mode=mode)
        assert check.status == "ok"
        assert read_identity(conn) == stale

    @pytest.mark.parametrize("mode", ["embed", "search"])
    def test_no_stored_vectors_still_guards_schema_width(self, db: Database, mode: str) -> None:
        conn = db.connection
        check = check_identity(conn, _build(config=_config(embedding_dim=3)), mode=mode)
        assert check.status == "dimension_mismatch"
        assert read_identity(conn) is None

    @pytest.mark.parametrize("mode", ["embed", "search", "init"])
    def test_absent_vectors_table_is_no_stored_vectors(self, tmp_path: Path, mode: str) -> None:
        conn = _bare_conn(tmp_path)
        try:
            check = check_identity(conn, _build(), mode=mode)
            assert check.status == "ok"
            assert read_identity(conn) is None
        finally:
            conn.close()

    def test_invalid_mode_raises(self, db: Database) -> None:
        with pytest.raises(ValueError, match="Unknown identity check mode"):
            check_identity(db.connection, _build(), mode="bogus")


# =============================================================================
# Warn-once idempotence
# =============================================================================


class TestWarnIdentityMismatchOnce:
    def test_warns_once_per_pair(self, caplog: pytest.LogCaptureFixture) -> None:
        stored = _build(config=_config(model_name="stored/model"))
        current = _build(config=_config(model_name="current/model"))

        with caplog.at_level(logging.WARNING):
            warn_identity_mismatch_once(stored, current)
            warn_identity_mismatch_once(stored, current)

        assert _identity_warning_count(caplog, "Embedder identity mismatch") == 1
        messages = [r.message for r in caplog.records if "Embedder identity mismatch" in r.message]
        assert stored.display_fingerprint() in messages[0]
        assert current.display_fingerprint() in messages[0]
        assert "sif index embed --force" in messages[0]

    def test_different_pair_warns_again(self, caplog: pytest.LogCaptureFixture) -> None:
        first = _build(config=_config(model_name="one/model"))
        second = _build(config=_config(model_name="two/model"))

        with caplog.at_level(logging.WARNING):
            warn_identity_mismatch_once(first, second)
            warn_identity_mismatch_once(first, _build(config=_config(model_name="three/model")))

        assert _identity_warning_count(caplog, "Embedder identity mismatch") == 2

    def test_reset_clears_latches(self, caplog: pytest.LogCaptureFixture) -> None:
        stored = _build(config=_config(model_name="stored/model"))
        current = _build(config=_config(model_name="current/model"))
        warn_identity_mismatch_once(stored, current)
        caplog.clear()
        reset_identity_state()
        with caplog.at_level(logging.WARNING):
            warn_identity_mismatch_once(stored, current)
        assert _identity_warning_count(caplog, "Embedder identity mismatch") == 1


# =============================================================================
# IdentityCheck convenience surface
# =============================================================================


class TestIdentityCheck:
    def test_status_booleans(self) -> None:
        current = _build()
        assert IdentityCheck("ok", None, current).untrusted is False
        assert IdentityCheck("absent", None, current).untrusted is False
        assert IdentityCheck("mismatch", None, current).untrusted is True
        assert IdentityCheck("dimension_mismatch", None, current).dimension_mismatch is True


# =============================================================================
# Prompt-scheme resolution
# =============================================================================


class TestResolvePromptScheme:
    def test_qwen3_default_has_no_prompt(self) -> None:
        scheme = resolve_prompt_scheme(_QWEN, "modelscope", None, None)
        assert scheme == PromptScheme(None, None, True)

    def test_known_harrier_model_gets_query_prompt(self) -> None:
        scheme = resolve_prompt_scheme("microsoft/harrier-oss-v1-0.6b", "modelscope", None, None)
        assert scheme == PromptScheme("web_search_query", None, True)

    def test_override_wins_over_table(self) -> None:
        scheme = resolve_prompt_scheme(
            "microsoft/harrier-oss-v1-0.6b", "modelscope", "custom", "doc"
        )
        assert scheme == PromptScheme("custom", "doc", True)

    def test_empty_string_disables_table_default(self) -> None:
        scheme = resolve_prompt_scheme("microsoft/harrier-oss-v1-0.6b", "modelscope", "", None)
        assert scheme == PromptScheme(None, None, True)

    def test_unsupported_backend_warns_and_reports_unsupported(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        with caplog.at_level(logging.WARNING):
            scheme = resolve_prompt_scheme("any/model", "openai", "query-prompt", None)
        assert scheme == PromptScheme(None, None, False)
        assert _identity_warning_count(caplog, "does not support prompt names") == 1

    def test_unsupported_backend_without_override_is_quiet(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        with caplog.at_level(logging.WARNING):
            scheme = resolve_prompt_scheme("any/model", "gguf", None, None)
        assert scheme == PromptScheme(None, None, False)
        assert _identity_warning_count(caplog, "does not support prompt names") == 0


# =============================================================================
# The identity key itself
# =============================================================================


def test_identity_key_spelling() -> None:
    assert IDENTITY_KEY == "embedder.identity"
