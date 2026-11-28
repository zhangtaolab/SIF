"""Zero-model rule anchors for the ``anchor:`` search arm.

This module is deliberately dependency-free: it imports only the standard
library, so importing it never pulls in ``llama_cpp``, ``jinja2``, or any
embedding backend. That keeps the Docs Validation job (which installs only
``.[dev]``) and every prefix-free query free of optional extras.

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

import re
import unicodedata
from dataclasses import dataclass
from typing import Protocol


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

    Wave 1 carries only the resolved ``terms`` and the producing ``backend``
    (``"rules"`` for the zero-model default, ``"injected"`` for explicit
    ``SearchOptions.anchor_terms``). Later plans append defaulted fields on
    this same class; nothing here ever reaches ``SearchResult``.
    """

    terms: list[str]
    backend: str


class AnchorResolver(Protocol):
    """Structural contract for an injected anchor resolver (26-02 implements).

    The pipeline only calls ``resolve``; the returned ``AnchorResolution``
    carries the terms and the backend identity used for run-level metadata.
    """

    def resolve(self, query: str) -> AnchorResolution:
        """Resolve the anchor terms for ``query``.

        Implementations should be deterministic for a given query and report
        the producing backend on the resolution.
        """


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
