"""Embedder identity: persisted provenance for the index's vector space.

One JSON record under ``index_meta['embedder.identity']`` describes the
embedder that produced ``document_embeddings``. The record is built from
settings plus the loaded model, persisted by the index's first vector write,
and compared field-wise at every vector-touching boundary.

Comparison is deliberately *not* fingerprint equality: a legacy-assumed
record knows only settings (``pooling: "unknown"``, ``revision: null``) while
the same model loaded later knows its real pooling mode. Unknown-vs-known is
not evidence of a swap; known-vs-known difference is. That keeps a legacy DB
from warning on every search while still detecting a real model swap.
"""

from __future__ import annotations

import hashlib
import json
import re
import sqlite3
from dataclasses import dataclass, field, replace
from typing import Any

from sif.config.settings import Settings
from sif.embedding.prompts import PromptScheme
from sif.models.embedding import EmbeddingConfig
from sif.utils.logging import get_logger


logger = get_logger(__name__)

IDENTITY_KEY = "embedder.identity"
IDENTITY_SCHEMA_VERSION = 1

_FLOAT_DIM_RE = re.compile(r"FLOAT\[(\d+)\]")

_EMBED_MODE = "embed"
_SEARCH_MODE = "search"
_INIT_MODE = "init"
_MODES = frozenset({_EMBED_MODE, _SEARCH_MODE, _INIT_MODE})

# Fields required for a stored payload to be usable. ``api_base`` and
# ``revision`` are nullable and may be omitted by an older writer.
_REQUIRED_FIELDS = (
    "schema",
    "cache_model_id",
    "model_name",
    "model_type",
    "dimension",
    "pooling",
    "normalized",
    "query_prompt",
    "document_prompt",
    "prompt_supported",
)
_NULLABLE_FIELDS = ("api_base", "revision")


# Process-local idempotence latches. reset_identity_state() clears both; the
# test suite resets them before every test via an autouse fixture.
@dataclass
class _IdentityState:
    """Mutable process-level warn-once state."""

    warnings: set[tuple[str, str]] = field(default_factory=set)
    legacy_warned: bool = False


_STATE = _IdentityState()


def _load_payload(raw: str) -> dict[str, Any] | None:
    """Parse ``raw`` into a JSON object, warning once on a non-object."""
    try:
        payload = json.loads(raw)
    except (TypeError, ValueError) as exc:
        logger.warning("Ignoring unreadable embedder identity: %s", exc)
        return None
    if not isinstance(payload, dict):
        logger.warning(
            "Ignoring embedder identity: expected a JSON object, got %s",
            type(payload).__name__,
        )
        return None
    return payload


def _payload_error(payload: dict[str, Any]) -> str | None:
    """Return why a parsed payload is unusable, or ``None`` when it is valid."""
    missing = [field_name for field_name in _REQUIRED_FIELDS if field_name not in payload]
    if missing:
        return f"missing required field(s) {', '.join(missing)}"

    schema_version = payload["schema"]
    dimension = payload["dimension"]
    types_ok = (
        not isinstance(schema_version, bool)
        and isinstance(schema_version, int)
        and not isinstance(dimension, bool)
        and isinstance(dimension, int)
        and dimension >= 1
        and isinstance(payload["normalized"], bool)
        and isinstance(payload["prompt_supported"], bool)
    )
    if not types_ok:
        return "invalid numeric/boolean field"
    for field_name in ("cache_model_id", "model_name", "model_type", "pooling"):
        if not isinstance(payload[field_name], str):
            return f"field '{field_name}' is not a string"
    for field_name in (*_NULLABLE_FIELDS, "query_prompt", "document_prompt"):
        value = payload.get(field_name)
        if value is not None and not isinstance(value, str):
            return f"field '{field_name}' is not a string"
    return None


@dataclass(frozen=True)
class EmbedderIdentity:
    """The persisted description of the index's vector space."""

    schema_version: int
    cache_model_id: str
    model_name: str
    model_type: str
    api_base: str | None
    dimension: int
    pooling: str
    normalized: bool
    query_prompt: str | None
    document_prompt: str | None
    prompt_supported: bool
    revision: str | None
    source: str

    def _payload(self) -> dict[str, Any]:
        """Every fingerprinted field, excluding ``source``."""
        return {
            "schema": self.schema_version,
            "cache_model_id": self.cache_model_id,
            "model_name": self.model_name,
            "model_type": self.model_type,
            "api_base": self.api_base,
            "dimension": self.dimension,
            "pooling": self.pooling,
            "normalized": self.normalized,
            "query_prompt": self.query_prompt,
            "document_prompt": self.document_prompt,
            "prompt_supported": self.prompt_supported,
            "revision": self.revision,
        }

    def fingerprint(self) -> str:
        """Full hex SHA-256 over the canonical JSON payload."""
        canonical = json.dumps(
            self._payload(),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        )
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    def display_fingerprint(self) -> str:
        """Short ``sha256:`` form used in messages."""
        return f"sha256:{self.fingerprint()[:16]}"

    def to_json(self) -> str:
        """Serialize payload plus ``source`` and ``fingerprint``."""
        payload = self._payload()
        payload["source"] = self.source
        payload["fingerprint"] = self.fingerprint()
        return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)

    @classmethod
    def from_json(cls, raw: str) -> EmbedderIdentity | None:
        """Parse a stored payload defensively.

        A malformed, non-object, or incomplete value is treated as absent
        with one warning; this never raises so a corrupt kv row cannot crash
        a caller or block an embed.
        """
        payload = _load_payload(raw)
        if payload is None:
            return None
        error = _payload_error(payload)
        if error is not None:
            logger.warning("Ignoring embedder identity: %s", error)
            return None

        source = payload.get("source", "verified")
        if not isinstance(source, str) or not source:
            source = "verified"
        return cls(
            schema_version=payload["schema"],
            cache_model_id=payload["cache_model_id"],
            model_name=payload["model_name"],
            model_type=payload["model_type"],
            api_base=payload.get("api_base"),
            dimension=payload["dimension"],
            pooling=payload["pooling"],
            normalized=payload["normalized"],
            query_prompt=payload["query_prompt"],
            document_prompt=payload["document_prompt"],
            prompt_supported=payload["prompt_supported"],
            revision=payload.get("revision"),
            source=source,
        )


@dataclass(frozen=True)
class IdentityCheck:
    """Outcome of comparing the stored identity against the current one."""

    status: str
    stored: EmbedderIdentity | None
    current: EmbedderIdentity

    @property
    def dimension_mismatch(self) -> bool:
        """Whether the current dimension cannot be stored in this index."""
        return self.status == "dimension_mismatch"

    @property
    def untrusted(self) -> bool:
        """Whether the stored vectors are known to come from another model."""
        return self.status in ("mismatch", "dimension_mismatch")


def format_cache_model_id(model_type: str, model_name: str, api_base: str | None) -> str:
    """Build the canonical ``model_type:model_name[@api_base]`` bucket base."""
    model_id = f"{model_type}:{model_name}"
    if api_base:
        model_id = f"{model_id}@{api_base}"
    return model_id


def _model_string(model: object | None, name: str, default: str | None) -> str | None:
    """Read an optional string model property, coercing doubles defensively."""
    value = getattr(model, name, None) if model is not None else None
    return value if isinstance(value, str) and value else default


def _model_dimension(model: object | None, default: int) -> int:
    """Read the loaded model's dimension, falling back to the configured one."""
    value = getattr(model, "dimension", None) if model is not None else None
    if isinstance(value, int) and not isinstance(value, bool) and value > 0:
        return value
    return default


def build_identity(
    config: EmbeddingConfig,
    model: object | None,
    scheme: PromptScheme,
    *,
    source: str = "verified",
) -> EmbedderIdentity:
    """Build the identity for a (possibly loaded) model.

    Optional model properties are read defensively so protocol-only doubles
    and mocks build a valid identity instead of leaking ``MagicMock`` values.
    """
    return EmbedderIdentity(
        schema_version=IDENTITY_SCHEMA_VERSION,
        cache_model_id=format_cache_model_id(
            config.model_type.value, config.model_name, config.api_base
        ),
        model_name=config.model_name,
        model_type=config.model_type.value,
        api_base=config.api_base,
        dimension=_model_dimension(model, config.embedding_dim),
        pooling=_model_string(model, "pooling_mode", "unknown") or "unknown",
        normalized=True,
        query_prompt=scheme.query_prompt,
        document_prompt=scheme.document_prompt,
        prompt_supported=scheme.supported,
        revision=_model_string(model, "revision", None),
        source=source,
    )


def build_settings_identity(settings: Settings, scheme: PromptScheme) -> EmbedderIdentity:
    """Build an identity from settings alone, before a model is loaded."""
    return EmbedderIdentity(
        schema_version=IDENTITY_SCHEMA_VERSION,
        cache_model_id=format_cache_model_id(
            settings.model_type, settings.model_name, settings.api_base
        ),
        model_name=settings.model_name,
        model_type=settings.model_type,
        api_base=settings.api_base,
        dimension=settings.embedding_dim,
        pooling="unknown",
        normalized=True,
        query_prompt=scheme.query_prompt,
        document_prompt=scheme.document_prompt,
        prompt_supported=scheme.supported,
        revision=None,
        source="verified",
    )


def schema_embedding_dim(conn: sqlite3.Connection) -> int | None:
    """Read the index's stored ``FLOAT[n]`` width; ``None`` when unavailable.

    This is the single ``FLOAT[n]`` read every dimension guard delegates to.
    """
    try:
        row = conn.execute(
            "SELECT sql FROM sqlite_master WHERE type='table' AND name='document_embeddings'",
        ).fetchone()
    except sqlite3.Error:
        return None
    if not row or not row[0]:
        return None
    match = _FLOAT_DIM_RE.search(row[0])
    return int(match.group(1)) if match else None


def _has_stored_vectors(conn: sqlite3.Connection) -> bool:
    """Whether any vector row exists; an absent table counts as none."""
    try:
        return conn.execute("SELECT 1 FROM document_embeddings LIMIT 1").fetchone() is not None
    except sqlite3.Error:
        return False


def read_identity(conn: sqlite3.Connection) -> EmbedderIdentity | None:
    """Read the stored identity, or ``None`` when absent/corrupt."""
    from sif.database.repositories import IndexMetaRepository  # noqa: PLC0415

    raw = IndexMetaRepository(conn).get(IDENTITY_KEY)
    if raw is None:
        return None
    return EmbedderIdentity.from_json(raw)


def write_identity(conn: sqlite3.Connection, identity: EmbedderIdentity) -> None:
    """Persist an identity; the caller owns the transaction."""
    from sif.database.repositories import IndexMetaRepository  # noqa: PLC0415

    IndexMetaRepository(conn).set(IDENTITY_KEY, identity.to_json())


def ensure_legacy_identity(
    conn: sqlite3.Connection,
    identity: EmbedderIdentity,
) -> EmbedderIdentity:
    """Return the stored identity, assuming one for a legacy populated index.

    A legacy DB (vectors but no identity key) gets ``source="legacy-assumed"``
    and exactly one warning per process. Without stored vectors nothing is
    written: the first real embed owns the identity.
    """
    stored = read_identity(conn)
    if stored is not None:
        return stored
    if not _has_stored_vectors(conn):
        return identity
    assumed = replace(identity, source="legacy-assumed")
    write_identity(conn, assumed)
    if not _STATE.legacy_warned:
        _STATE.legacy_warned = True
        logger.warning(
            "Index predates embedder identity; assuming %s (%s). "
            "Run `sif index embed --force` to certify.",
            assumed.display_fingerprint(),
            assumed.cache_model_id,
        )
    return assumed


def certify_identity(conn: sqlite3.Connection, identity: EmbedderIdentity) -> EmbedderIdentity:
    """Write the full current identity as ``source="verified"``."""
    verified = replace(identity, source="verified")
    write_identity(conn, verified)
    return verified


def identity_matches(stored: EmbedderIdentity, current: EmbedderIdentity) -> bool:
    """Field-wise comparison with unknown-tolerance, never fingerprint equality."""
    pooling_known = stored.pooling != "unknown" and current.pooling != "unknown"
    revision_known = bool(stored.revision and current.revision)
    return (
        stored.cache_model_id == current.cache_model_id
        and stored.dimension == current.dimension
        and stored.normalized == current.normalized
        and (not pooling_known or stored.pooling == current.pooling)
        and (not revision_known or stored.revision == current.revision)
        and stored.query_prompt == current.query_prompt
        and stored.document_prompt == current.document_prompt
    )


def check_identity(
    conn: sqlite3.Connection,
    current: EmbedderIdentity,
    mode: str = _SEARCH_MODE,
) -> IdentityCheck:
    """Compare the stored identity against ``current`` for a host mode.

    Identity checks apply only while stored vectors exist (D-02): an
    embeddings-empty index accepts any embedder and the first successful
    vector write overwrites the identity. Only the schema width guard still
    applies there. ``init`` is width-only; ``embed`` may write the documented
    legacy-assumed row; ``search`` never writes.
    """
    if mode not in _MODES:
        raise ValueError(f"Unknown identity check mode: {mode}")

    stored = read_identity(conn)
    schema_dim = schema_embedding_dim(conn)
    width_mismatch = schema_dim is not None and schema_dim != current.dimension

    if mode == _INIT_MODE:
        if stored is None and not width_mismatch and _has_stored_vectors(conn):
            stored = ensure_legacy_identity(conn, current)
        status = "dimension_mismatch" if width_mismatch else "ok"
        return IdentityCheck(status=status, stored=stored, current=current)

    if not _has_stored_vectors(conn):
        # D-02: a stale identity row never blocks an index with no vectors.
        status = "dimension_mismatch" if width_mismatch else "ok"
        return IdentityCheck(status=status, stored=stored, current=current)

    if width_mismatch:
        return IdentityCheck(status="dimension_mismatch", stored=stored, current=current)

    if stored is None:
        if mode == _EMBED_MODE:
            stored = ensure_legacy_identity(conn, current)
        return IdentityCheck(status="ok", stored=stored, current=current)

    if stored.dimension != current.dimension:
        return IdentityCheck(status="dimension_mismatch", stored=stored, current=current)
    status = "ok" if identity_matches(stored, current) else "mismatch"
    return IdentityCheck(status=status, stored=stored, current=current)


def warn_identity_mismatch_once(
    stored: EmbedderIdentity,
    current: EmbedderIdentity,
) -> None:
    """Emit one stderr warning per process for a given identity pair."""
    key = (stored.display_fingerprint(), current.display_fingerprint())
    if key in _STATE.warnings:
        return
    _STATE.warnings.add(key)
    logger.warning(
        "Embedder identity mismatch: index vectors were produced by %s (%s) "
        "but the current model is %s (%s). Restore the stored model or run "
        "`sif index embed --force` with the matching model.",
        stored.display_fingerprint(),
        stored.cache_model_id,
        current.display_fingerprint(),
        current.cache_model_id,
    )


def reset_identity_state() -> None:
    """Clear the per-process warning latches (used by tests)."""
    _STATE.legacy_warned = False
    _STATE.warnings.clear()
