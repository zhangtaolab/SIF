"""Zero-model rule anchors for the ``anchor:`` search arm.

This module keeps optional model dependencies out of its import graph: it
imports only the standard library plus ``sif.database.repositories`` /
``sif.utils.logging``, and every ``llama_cpp`` / ``jinja2`` import happens at
a generator call site. Importing the module therefore never pulls in a model
runtime, which keeps the Docs Validation job (which installs only ``.[dev]``)
and every prefix-free query free of optional extras.

The anchor table is ported verbatim from the Phase 25 spike artifact at
``.planning/phases/25-contract-freeze-feasibility-spike/bench/anchor-table.json``
(``phrases``/``tokens``/``cjk``/``compounds`` and the four derivation rules).
The probe's RRF parameters (``seed``/``rrf_k``/``lex_weight``) are not ported:
they described the Phase 25 fusion experiment, not this phase's OR injection.

Derivation itself is a pure function of the query string and these constants —
no file read, no database lookup, no model, and no relevance data. That is what
lets ``anchor:`` reproduce Phase 25's directional signal without loading a
model, and what makes the default (no ``anchor:``/``--anchor``) path
construct nothing at all.
"""

from __future__ import annotations

import hashlib
import json
import re
import sqlite3
import unicodedata
from dataclasses import dataclass
from typing import Protocol

from sif.database.repositories import LLMCacheRepository
from sif.utils.logging import get_logger


logger = get_logger(__name__)


ANCHOR_TABLE_VERSION = 1

# GEN-01 freezes the cap as a module constant; it is not a Settings field.
MAX_ANCHORS_PER_QUERY = 6

# Lowercased text splits on non-alphanumeric boundaries; contiguous CJK runs
# stay whole, mirroring how the FTS porter tokenizer treats a Chinese phrase.
_TOKEN_RE = re.compile(r"[a-z0-9]+|[一-鿿]+")

# Phrase substring matches: a query containing the key yields the expansions.
_PHRASES: dict[str, tuple[str, ...]] = {
    "machine learning": ("statistical learning", "机器学习"),
    "deep learning": ("neural networks", "深度学习"),
    "neural networks": ("neural nets", "深度学习"),
    "natural language processing": ("nlp", "自然语言处理"),
    "data mining": ("knowledge discovery", "数据挖掘"),
    "knowledge graphs": ("knowledge graph", "知识图谱"),
    "cloud computing": ("云计算", "distributed computing"),
    "distributed systems": ("分布式系统", "cluster computing"),
    "database indexing": ("数据库索引", "index structures"),
    "route planning": ("path planning", "navigation"),
    "culture starter": ("starter culture", "fermentation"),
    "light recording": ("imaging", "photography"),
    "natural language": ("human language", "text"),
    "phase array": ("phased array", "antenna"),
    "gravity well": ("gravity field", "spacetime"),
}

# Per-token synonym expansions, applied in query token order.
_TOKENS: dict[str, tuple[str, ...]] = {
    "protocol": ("specification", "standard"),
    "navigation": ("map", "path"),
    "route": ("path", "way"),
    "planning": ("strategy", "schedule"),
    "fermentation": ("ferment", "brewing"),
    "culture": ("cultivation", "growth"),
    "starter": ("beginner", "inoculum"),
    "holography": ("hologram", "interference"),
    "light": ("optics", "photon"),
    "recording": ("capture", "imaging"),
    "cartography": ("mapping", "mapmaking"),
    "mapmaking": ("cartography", "mapping"),
    "terrain": ("landscape", "topography"),
    "acoustics": ("sound", "sonic"),
    "sound": ("audio", "acoustic"),
    "vibration": ("oscillation", "resonance"),
    "metallurgy": ("metal", "alloy"),
    "metal": ("alloy", "metallic"),
    "refining": ("smelting", "purification"),
    "botany": ("plant", "flora"),
    "plants": ("vegetation", "flora"),
    "classification": ("taxonomy", "categorization"),
    "astronomy": ("celestial", "astrophysics"),
    "stars": ("stellar", "celestial"),
    "observation": ("telescope", "measurement"),
    "cryptography": ("encryption", "cipher"),
    "encryption": ("cipher", "cryptography"),
    "secrecy": ("privacy", "confidentiality"),
    "machine": ("computer", "automated"),
    "learning": ("training", "education"),
    "deep": ("profound", "layered"),
    "neural": ("neuron", "network"),
    "networks": ("network", "graph"),
    "natural": ("organic", "human"),
    "language": ("linguistic", "text"),
    "processing": ("analysis", "computation"),
    "data": ("information", "dataset"),
    "mining": ("extraction", "discovery"),
    "knowledge": ("information", "understanding"),
    "graphs": ("graph", "network"),
    "cloud": ("remote", "server"),
    "computing": ("computation", "processing"),
    "distributed": ("parallel", "decentralized"),
    "systems": ("system", "infrastructure"),
    "database": ("store", "repository"),
    "indexing": ("index", "lookup"),
    "flux": ("flow", "energy"),
    "capacitor": ("condenser", "storage"),
    "charge": ("energy", "power"),
    "warp": ("distortion", "bend"),
    "coil": ("winding", "solenoid"),
    "plasma": ("ionized", "gas"),
    "phase": ("stage", "offset"),
    "array": ("matrix", "grid"),
    "signal": ("waveform", "transmission"),
    "ion": ("charged", "particle"),
    "thruster": ("propulsion", "engine"),
    "fuel": ("propellant", "energy"),
    "quantum": ("subatomic", "discrete"),
    "lattice": ("grid", "structure"),
    "error": ("fault", "noise"),
    "photon": ("light", "particle"),
    "sieve": ("filter", "mesh"),
    "gravity": ("gravitational", "attraction"),
    "well": ("field", "basin"),
    "trajectory": ("path", "orbit"),
    "muon": ("particle", "lepton"),
    "detector": ("sensor", "instrument"),
    "particle": ("elementary", "atom"),
    "tachyon": ("faster-than-light", "hypothetical"),
    "beacon": ("signal", "transmitter"),
    "temporal": ("time", "chronological"),
}

# CJK query tokens expand to their English form (the reverse of _PHRASES).
_CJK: dict[str, tuple[str, ...]] = {
    "机器学习": ("machine learning",),
    "深度学习": ("deep learning",),
    "神经网络": ("neural networks",),
    "自然语言处理": ("natural language processing",),
    "数据挖掘": ("data mining",),
    "知识图谱": ("knowledge graphs",),
    "云计算": ("cloud computing",),
    "分布式系统": ("distributed systems",),
    "数据库索引": ("database indexing",),
}

# Compound tokens expand into their parts.
_COMPOUNDS: dict[str, tuple[str, ...]] = {
    "pathfinding": ("path", "finding"),
    "mapmaking": ("map", "making"),
}

# Public, inspectable snapshot of the rule table. The derivation rules are
# fixed to the four flags Phase 25 recorded; the probe's fusion weights are not
# part of this phase.
ANCHOR_TABLE: dict[str, object] = {
    "rules": {
        "max_anchors_per_query": MAX_ANCHORS_PER_QUERY,
        "lowercase": True,
        "dedupe": True,
        "exclude_query_terms": True,
    },
    "phrases": _PHRASES,
    "tokens": _TOKENS,
    "cjk": _CJK,
    "compounds": _COMPOUNDS,
}


@dataclass(frozen=True)
class AnchorResolution:
    """Run-level metadata for one anchor resolution.

    ``terms`` and ``backend`` carry the resolved terms and the producing
    backend (``"rules"`` for the zero-model default, ``"injected"`` for
    explicit ``SearchOptions.anchor_terms``, or the configured generator
    backend). The three defaulted counters/reason are run-level cost metadata
    (D-12): they never reach ``SearchResult`` or its ``to_dict`` snapshot.
    """

    terms: list[str]
    backend: str
    generator_calls: int = 0
    cache_hits: int = 0
    fallback_reason: str | None = None


def normalize_query(text: str) -> str:
    """Normalize text to the rule-anchor surface form.

    NFKC folds compatibility characters, casefolding removes case, and
    whitespace collapses to single spaces so ``"  Machine   Learning "`` and
    ``"machine learning"`` derive the same anchors.
    """
    folded = unicodedata.normalize("NFKC", text).casefold()
    return " ".join(folded.split())


def derive_rule_anchors(query: str) -> list[str]:
    """Derive deterministic, query-only rule anchors from the embedded table.

    Candidates come from phrase substring matches first, then per-token
    ``tokens``/``cjk``/``compounds`` lookups in query order. Each candidate is
    normalized, deduplicated with first-occurrence precedence, dropped when
    every one of its tokens already appears in the query
    (``exclude_query_terms``), and the survivors are truncated to
    ``MAX_ANCHORS_PER_QUERY``.
    """
    normalized = normalize_query(query)
    query_tokens = set(_TOKEN_RE.findall(normalized))
    candidates: list[str] = []

    for phrase, expansions in _PHRASES.items():
        if phrase in normalized:
            candidates.extend(expansions)

    for token in _TOKEN_RE.findall(normalized):
        candidates.extend(_TOKENS.get(token, ()))
        candidates.extend(_CJK.get(token, ()))
        candidates.extend(_COMPOUNDS.get(token, ()))

    anchors: list[str] = []
    seen: set[str] = set()
    for candidate in candidates:
        term = normalize_query(candidate)
        if not term or term in seen:
            continue
        term_tokens = set(_TOKEN_RE.findall(term))
        if term_tokens and term_tokens <= query_tokens:
            continue
        seen.add(term)
        anchors.append(term)
        if len(anchors) >= MAX_ANCHORS_PER_QUERY:
            break
    return anchors


# GEN-01 freezes the prompt identity as module constants (D-06): prompt text
# and version are part of the evaluation identity and therefore part of the
# cache key. Any text change MUST bump PROMPT_VERSION, which invalidates every
# cached anchor row.
PROMPT_VERSION = "anchor.v1"
MAX_ANCHOR_TERMS = 10
CACHE_RESPONSE_VERSION = 1

# Task 1 scaffolding prompt; Task 2 replaces it with the frozen template under
# the same PROMPT_VERSION (only the published plan's final text is frozen).
PROMPT_TEMPLATE = "Query: {query}\nTerms:\n"

_ANCHOR_BACKENDS = frozenset({"rules", "gguf", "openai"})
_DEFAULT_MAX_CALLS = 100
_DEFAULT_CACHE_TTL = 2592000
_DEFAULT_TIMEOUT_MS = 5000
_DEFAULT_MAX_TOKENS = 64


class AnchorBackendUnavailable(RuntimeError):  # noqa: N818 - public API name
    """Raised when a configured anchor backend cannot be constructed.

    ``reason`` is a short stable token (``"unconfigured"``,
    ``"model_path_invalid"``, ``"llama_cpp_missing"``, ...) surfaced through
    ``AnchorResolution.fallback_reason``.
    """

    def __init__(self, reason: str) -> None:
        """Record the stable reason token on the exception."""
        self.reason = reason
        super().__init__(reason)


class AnchorGenerationFailed(RuntimeError):  # noqa: N818 - public API name
    """Raised when one generation attempt fails or exceeds its deadline."""

    def __init__(self, reason: str, message: str | None = None) -> None:
        """Record the stable reason token and an optional detail message."""
        self.reason = reason
        super().__init__(message or reason)


class AnchorBudgetExceeded(RuntimeError):  # noqa: N818 - public API name
    """Raised when an anchor resolver exceeds ``SIF_ANCHOR_MAX_CALLS``."""


class AnchorGenerator(Protocol):
    """Structural contract for one anchor term generator.

    ``model_id`` namespaces the cache and is part of the prompt hash; the
    generator never touches ``SearchResult`` and never writes the cache itself.
    """

    model_id: str

    def generate(self, prompt: str) -> str:
        """Return raw model text for ``prompt``."""


def _setting_str(settings: object, name: str, default: str) -> str:
    """Read a string setting, falling back for non-strings (MagicMock guards)."""
    value = getattr(settings, name, default)
    return value if isinstance(value, str) else default


def _setting_int(settings: object, name: str, default: int) -> int:
    """Read an int setting, rejecting bools and non-ints (MagicMock guards)."""
    value = getattr(settings, name, default)
    if isinstance(value, int) and not isinstance(value, bool):
        return value
    return default


def _cache_model_name(backend: str, model_id: str) -> str:
    """Namespace anchor cache rows away from other LLM responses (D-09)."""
    return f"anchor::{backend}::{model_id}"


def _prompt_hash(backend: str, model_id: str, stripped_query: str) -> str:
    """Build the deterministic cache key (D-10).

    The key binds prompt version, model identity, backend, and the normalized
    query, so any change to the frozen prompt/greedy/parser identity
    invalidates the cache.
    """
    material = f"{PROMPT_VERSION}\x00{model_id}\x00{backend}\x00{stripped_query}"
    return hashlib.sha256(material.encode("utf-8")).hexdigest()


def _parse_cached(response: str) -> list[str] | None:
    """Parse a cached anchor response, treating malformed JSON as a miss.

    Only ``{"version": CACHE_RESPONSE_VERSION, "terms": [str, ...]}`` is
    trusted; anything else returns ``None`` so the caller regenerates and
    overwrites the row (T-26-08). This function never raises.
    """
    try:
        data = json.loads(response)
    except (ValueError, TypeError):
        return None
    if not isinstance(data, dict) or data.get("version") != CACHE_RESPONSE_VERSION:
        return None
    terms = data.get("terms")
    if not isinstance(terms, list) or not all(isinstance(term, str) for term in terms):
        return None
    return list(terms)


def parse_terms(text: str, *, limit: int = MAX_ANCHOR_TERMS) -> list[str]:
    """Parse generator output into deduplicated anchor terms.

    Task 1 keeps the line/strip/dedupe/cap shape; Task 2 adds the full
    character, length, and word-count constraints (GEN-01).
    """
    terms: list[str] = []
    seen: set[str] = set()
    for raw in text.splitlines():
        term = raw.strip().strip("\"'`").lower()
        if not term or term in seen:
            continue
        seen.add(term)
        terms.append(term)
        if len(terms) >= limit:
            break
    return terms


class AnchorResolver:
    """Deterministic anchor resolution with an ``llm_cache``-backed cache.

    The zero-model ``rules`` backend is the default and never touches the
    cache (Open Question 3: a pure function of the query has nothing to
    cache). Generator backends are explicit opt-ins; a cache hit avoids any
    generator call, and the SQLite table itself is the cross-process cache
    (D-11) — there is deliberately no in-process LRU.
    """

    def __init__(
        self,
        conn: sqlite3.Connection,
        settings: object,
        *,
        generator: AnchorGenerator | None = None,
    ) -> None:
        """Initialize the resolver around a real connection and settings."""
        self.conn = conn
        self.settings = settings
        backend = _setting_str(settings, "anchor_backend", "rules")
        self.backend = backend if backend in _ANCHOR_BACKENDS else "rules"
        self._generator = generator
        self._unavailable_reason: str | None = None
        self._failed: dict[str, str] = {}
        self._warned_reasons: set[str] = set()
        self._calls = 0

    def resolve(self, query: str) -> AnchorResolution:
        """Resolve anchor terms for ``query`` (fail-open except on budget)."""
        # Observed at ENTRY: ``LLMCacheRepository.set``'s INSERT flips
        # ``in_transaction`` to True under IMMEDIATE isolation, so checking
        # after the write would never commit (research Pitfall 7) and the
        # cross-process hit proof would fail while same-connection tests pass.
        was_in_transaction = self.conn.in_transaction
        stripped = normalize_query(query)
        if self.backend == "rules":
            return AnchorResolution(terms=derive_rule_anchors(stripped), backend="rules")
        if self._unavailable_reason is not None:
            return self._rule_fallback(stripped, self._unavailable_reason)
        try:
            generator = self._ensure_generator()
        except AnchorBackendUnavailable as exc:
            return self._mark_unavailable(stripped, exc.reason)
        model_name = _cache_model_name(self.backend, generator.model_id)
        prompt_hash = _prompt_hash(self.backend, generator.model_id, stripped)
        cached = self._cache_hit(model_name, prompt_hash)
        if cached is not None:
            return AnchorResolution(terms=cached, backend=self.backend, cache_hits=1)
        if prompt_hash in self._failed:
            return AnchorResolution(
                terms=[],
                backend=self.backend,
                fallback_reason=self._failed[prompt_hash],
            )
        self._check_budget()
        return self._generate_and_store(
            generator, stripped, model_name, prompt_hash, was_in_transaction
        )

    def _ensure_generator(self) -> AnchorGenerator:
        """Return the injected generator (Task 2 adds configured backends)."""
        if self._generator is not None:
            return self._generator
        raise AnchorBackendUnavailable("unconfigured")

    def _cache_hit(self, model_name: str, prompt_hash: str) -> list[str] | None:
        """Return cached terms, or ``None`` on a miss/expiry/malformed row."""
        cached = LLMCacheRepository(self.conn).get(model_name, prompt_hash)
        if cached is None:
            return None
        return _parse_cached(cached)

    def _check_budget(self) -> None:
        """Raise before generating when the per-instance call budget is spent."""
        max_calls = _setting_int(self.settings, "anchor_max_calls", _DEFAULT_MAX_CALLS)
        if max_calls > 0 and self._calls >= max_calls:
            raise AnchorBudgetExceeded(
                f"anchor generation budget exceeded (SIF_ANCHOR_MAX_CALLS={max_calls})"
            )

    def _mark_unavailable(self, stripped: str, reason: str) -> AnchorResolution:
        """Latch an unavailable backend and fall back to the rule anchors."""
        self._unavailable_reason = reason
        self._generator = None
        return self._rule_fallback(stripped, reason)

    def _rule_fallback(self, stripped: str, reason: str) -> AnchorResolution:
        """Return rule anchors with a recorded fallback reason (single warning)."""
        self._warn_once(
            reason,
            f"Anchor generator unavailable ({reason}); using rule anchors",
        )
        return AnchorResolution(
            terms=derive_rule_anchors(stripped),
            backend="rules",
            fallback_reason=reason,
        )

    def _warn_once(self, reason: str, message: str) -> None:
        """Warn at most once per failure reason on this resolver instance."""
        if reason in self._warned_reasons:
            return
        self._warned_reasons.add(reason)
        logger.warning(message)

    def _generate_and_store(
        self,
        generator: AnchorGenerator,
        stripped: str,
        model_name: str,
        prompt_hash: str,
        was_in_transaction: bool,
    ) -> AnchorResolution:
        """Generate once, then cache on success only (failures write nothing)."""
        self._calls += 1
        try:
            raw = generator.generate(PROMPT_TEMPLATE.format(query=stripped))
        except AnchorBackendUnavailable as exc:
            return self._mark_unavailable(stripped, exc.reason)
        except Exception as exc:
            reason = getattr(exc, "reason", "generation_failed")
            if not isinstance(reason, str):
                reason = "generation_failed"
            self._failed[prompt_hash] = reason
            self._warn_once(
                reason,
                f"Anchor generation failed ({reason}); falling back to the original query",
            )
            return AnchorResolution(
                terms=[],
                backend=self.backend,
                generator_calls=1,
                fallback_reason=reason,
            )
        terms = parse_terms(raw)
        ttl_seconds = _setting_int(self.settings, "anchor_cache_ttl", _DEFAULT_CACHE_TTL) or None
        LLMCacheRepository(self.conn).set(
            model_name,
            prompt_hash,
            stripped,
            json.dumps(
                {"version": CACHE_RESPONSE_VERSION, "terms": terms},
                ensure_ascii=False,
            ),
            ttl_seconds=ttl_seconds,
        )
        # Never commit a caller's open transaction; only our own write is ours.
        if not was_in_transaction:
            self.conn.commit()
        return AnchorResolution(terms=terms, backend=self.backend, generator_calls=1)
