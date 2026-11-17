"""Personal-corpus benchmark synthesis and deterministic sampling (Phase 18, EVAL-01/02).

Pure domain module: no Click or Rich imports. Every stage is deterministic —
normalization is NFC + casefold + whitespace collapse, sampling and
fingerprinting use ``hashlib.sha256`` (never Python's salted builtin hash),
and outputs are ordered by explicit sort keys so the same index yields the
same query set on every machine (research Pitfall 9).

Privacy (EVAL-01): the whole-corpus pass reads metadata columns only
(``id, path, title, checksum, file_size``); document bodies are loaded solely
for the bounded sampled subset (``load_sampled_content``). A saved run stores
the synthesized body-leg query string — a short normalized excerpt of the
sampled document's later prose (at most 10 tokens) — but never a full body,
snippet, or embedding; nothing here uploads document content.

Bias controls (EVAL-02): the title leg is exact-term and unbudgeted, the body
leg rejects candidates whose token Jaccard against the target's title plus
opening text exceeds ``OVERLAP_BUDGET``, and every rejected candidate is
counted per leg — a query set never shrinks silently (research Pitfall 1).
"""

from __future__ import annotations

import hashlib
import json
import math
import random
import re
import sqlite3
import unicodedata
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field, replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, NoReturn

from sif.core.models import SearchResult
from sif.database.repositories import QueryLogRepository
from sif.search.benchmark import (
    DEFAULT_K,
    EPSILON,
    QueryEvaluation,
    SearchEvaluator,
    hit_at_k,
    ndcg_at_k,
    percentile,
)


# Declared leg order (D-01): title and body are known-item synthesis; replay
# is a separate stability leg with its own semantics.
LEGS: tuple[str, ...] = ("title", "body", "replay")
LANGUAGES: tuple[str, ...] = ("en", "zh", "mixed")
LENGTH_BUCKETS: tuple[str, ...] = ("short", "medium", "long")
# D-11 thresholds: a personal measurement is only reported when it is at
# least this large; a smaller corpus gets a loud remedy instead of a noisy
# number.
MIN_DOCUMENTS = 50
MIN_QUERIES = 50
MAX_QUERIES = 500
MAX_SAMPLE_DOCUMENTS = 250
INITIAL_SAMPLE_DOCUMENTS = MIN_DOCUMENTS
HELDOUT_MIN = 25
SUPPRESS_BELOW = 10
OVERLAP_BUDGET = 0.60
RUN_SCHEMA_VERSION = 1
# Versioned saved-run contract (D-10/D-12): every personal run is written
# under the cache directory unless --no-save, and --compare consumes it.
SAVED_RUN_VERSION = 1
MAX_SAVED_RECORDS = 10_000
MAX_SAVED_FILE_BYTES = 5 * 1024 * 1024
# Retrieval-depth ceiling (WR-01/WR-02): compare mode uses a saved run's
# ``top_k`` as its search depth, so an untrusted file must not be able to
# request an arbitrary depth. The CLI's -n/--limit uses the same bound.
MAX_TOP_K = 200
_SAVED_QUERY_MAX_CHARS = 10_000
_SAVED_PATH_MAX_CHARS = 4_096
_SAVED_ID_MAX_CHARS = 512
_SAVED_FINGERPRINT_MAX_CHARS = 64
_SAVED_MODEL_FIELD_MAX_CHARS = 512
_SAVED_RETRIEVAL_MODES = frozenset({"hybrid", "bm25"})
_SAVED_LEGS = frozenset({"title", "body"})
_SAVED_SPLITS = frozenset({"tuning", "heldout"})
_SAVED_FORBIDDEN_KEYS = frozenset({"content", "snippet"})
BOOTSTRAP_RESAMPLES = 10_000
MAX_REPLAY_QUERIES = 500
REPLAY_BIAS_NOTE = (
    "Replay measures stability against a saved baseline, not absolute quality. "
    "Only CLI searches are logged (MCP queries are not logged), so replay is a "
    "CLI-biased sample."
)

# D-05 per-leg budget: the title leg IS the title (exact-term, exempt), the
# body leg is paraphrased and budgeted, and replay synthesizes nothing.
LEG_BUDGETS: dict[str, float | None] = {
    "title": None,
    "body": OVERLAP_BUDGET,
    "replay": None,
}
EXACT_TERM_LEGS: frozenset[str] = frozenset({"title"})

# Tokenization mirrors the FTS porter/CJK seam pinned by the test support:
# ASCII words and whole contiguous CJK runs (research Pitfall 11).
_TOKEN_RE = re.compile(r"[a-z0-9]+|[一-鿿]+")
_CJK_RUN_RE = re.compile(r"[一-鿿]+")
_SENTENCE_RE = re.compile(r"[^.!?。\uff01\uff1f]+")
_FENCED_CODE_RE = re.compile(r"```.*?(?:```|\Z)", re.DOTALL)
_INLINE_CODE_RE = re.compile(r"`[^`\n]*`")
_HTML_COMMENT_RE = re.compile(r"<!--.*?-->", re.DOTALL)
_URL_RE = re.compile(r"(?:https?://|www\.)\S+")
_MARKDOWN_LINK_RE = re.compile(r"!?\[([^\]]*)\]\([^)]*\)")
_HEADING_RE = re.compile(r"^[ \t]{0,3}#{1,6}[ \t]*", re.MULTILINE)
_EMPHASIS_RE = re.compile(r"[*_~]{1,3}")

# Body candidate shape (D-05 / research Open Question 9): a later prose
# sentence, at most 10 tokens, at least 4 tokens, never from the opening.
_OPENING_CHARS = 200
_BODY_MIN_TOKENS = 4
_BODY_MAX_TOKENS = 10
# Language/length thresholds (research A9; EVAL-02 discretion pinned tests).
_ZH_RATIO = 0.5
_EN_RATIO = 0.1
_SPLIT_THRESHOLD = 128  # sha256 digest[0] < 128 -> tuning (stable 50/50)
_SHORT_MAX_UNITS = 2
_MEDIUM_MAX_UNITS = 5
# SQLite's default host-parameter limit is 999; keep well below it.
_CONTENT_CHUNK = 500


@dataclass(frozen=True)
class DocumentRecord:
    """One in-scope document's metadata (bodies never join the whole pass).

    ``content`` is transient: it stays ``None`` for the metadata-only corpus
    scan and is populated solely for the bounded sampled subset
    (``load_sampled_content``), so a whole-corpus pass never materializes
    note bodies (T-18-02).
    """

    id: str
    path: str
    title: str
    checksum: str
    file_size: int
    content: str | None = None


@dataclass(frozen=True)
class SynthesizedQuery:
    """One known-item query: the query text plus its single grade-1 target.

    ``language``/``length_bucket`` are populated at synthesis time; ``split``
    is assigned by the deterministic sha256 split (title/body only — replay
    queries are never split).
    """

    query: str
    target_doc_id: str
    target_path: str
    leg: str
    language: str = "en"
    length_bucket: str = "short"
    split: str | None = None


@dataclass(frozen=True)
class SynthesisResult:
    """Accepted queries plus the per-leg rejection tally — never a silent shrink.

    ``rejected_empty``, ``rejected_duplicate``, and ``rejected_overlap`` are
    dicts keyed by the synthesized leg (``title``, ``body``) so every leg's
    counts and budget are visible independently (EVAL-02 transparency rule).
    """

    queries: list[SynthesizedQuery]
    rejected_empty: dict[str, int]
    rejected_duplicate: dict[str, int]
    rejected_overlap: dict[str, int]


@dataclass(frozen=True)
class CorpusSummary:
    """The corpus identity a report carries (Plan 03's saved-run envelope)."""

    documents: int
    sampled: int
    fingerprint: str
    widened: bool


@dataclass(frozen=True)
class GroupMetrics:
    """One leg x language x length-bucket group (D-08; count >= SUPPRESS_BELOW)."""

    leg: str
    language: str
    length_bucket: str
    count: int
    ndcg_at_10: float
    hit_at_10: float

    def to_dict(self) -> dict[str, Any]:
        """Serialize with a fixed key order (never a tuple-keyed dict)."""
        return {
            "leg": self.leg,
            "language": self.language,
            "length_bucket": self.length_bucket,
            "count": self.count,
            "ndcg_at_10": self.ndcg_at_10,
            "hit_at_10": self.hit_at_10,
        }


@dataclass(frozen=True)
class PersonalQueryRecord:
    """One evaluated known-item query with its identity, split, and ranking.

    ``retrieved_doc_ids`` is rank-aligned with ``retrieved_paths`` (one string
    per retrieved rank, ``""`` when a result carries no document id), so the
    saved-run writer (Plan 03) can grade by document id without re-deriving
    ranks from paths. ``target_path`` is an inspection value, never content.
    """

    query: str
    target_doc_id: str
    target_path: str
    leg: str
    language: str
    length_bucket: str
    split: str
    ndcg_at_10: float
    hit_at_10: float
    retrieved_doc_ids: list[str]
    retrieved_paths: list[str]


@dataclass(frozen=True)
class ReplayResult:
    """The query_log replay leg: stability data only, never quality metrics.

    ``available`` reports whether replay data exists at all;
    ``baseline_available`` whether a saved snapshot exists to compare against
    (always False on a fresh run; Plan 03 computes stability on ``--compare``).
    ``top_k_paths`` maps normalized query text to rank-ordered result paths —
    paths only, never content or snippets (T-18-04).
    """

    available: bool
    num_queries: int
    baseline_available: bool
    top_k_paths: dict[str, list[str]]
    bias: str

    def to_dict(self) -> dict[str, Any]:
        """Serialize the replay section with a fixed key order."""
        return {
            "available": self.available,
            "num_queries": self.num_queries,
            "baseline_available": self.baseline_available,
            "queries": {query: list(paths) for query, paths in self.top_k_paths.items()},
            "bias": self.bias,
        }


@dataclass(frozen=True)
class SavedQueryRecord:
    """One query in a versioned saved run (D-10/D-12; no full document body).

    ``retrieved`` and ``retrieved_doc_ids`` are rank-aligned: index ``i`` is
    the result at rank ``i`` (``""`` when that result carries no document id).
    Document ids are the identity both comparison arms grade through;
    paths remain inspection values and a unique-match fallback.
    """

    query: str
    target_path: str
    target_doc_id: str
    leg: str
    language: str
    length_bucket: str
    split: str
    retrieved: list[str]
    retrieved_doc_ids: list[str]
    grade: int = 1


@dataclass(frozen=True)
class SavedRun:
    """The versioned run envelope ``--compare`` consumes (D-12).

    ``top_k`` records the retrieval depth so both comparison arms evaluate at
    the saved depth; ``corpus`` carries the fingerprint that refuses a
    different corpus; ``replay`` stores rank-ordered paths only.
    """

    version: int
    created_at: str
    top_k: int
    corpus: dict[str, Any]
    retrieval: str
    model: dict[str, Any] | None
    queries: list[SavedQueryRecord]
    replay: dict[str, Any]


@dataclass(frozen=True)
class PersonalReport:
    """The full personal-eval report: identity, metrics, groups, and records.

    Built once by ``build_personal_report`` and rendered by the CLI through
    ``to_dict()``; the Plan 01 keys stay intact while ``top_k``, ``splits``,
    ``groups``, ``suppressed``, and ``replay`` are additive. ``records`` is the
    ordered per-query substrate Plan 03's ``run_to_saved`` consumes.
    """

    retrieval: str
    top_k: int
    corpus: CorpusSummary
    model: dict[str, Any] | None
    metrics: dict[str, float]
    splits: dict[str, int]
    groups: list[GroupMetrics]
    suppressed: list[str]
    queries: dict[str, Any]
    records: list[PersonalQueryRecord]
    replay: ReplayResult
    notes: list[str]
    mode: str = "personal"

    def to_dict(self) -> dict[str, Any]:
        """Serialize with a fixed key order; query text and paths only.

        A body-leg query string is a short synthesized excerpt of the target
        document (documented in ``docs/benchmarking.md``); no full body,
        snippet, or embedding is emitted.
        """
        return {
            "mode": self.mode,
            "retrieval": self.retrieval,
            "top_k": self.top_k,
            "corpus": {
                "documents": self.corpus.documents,
                "sampled": self.corpus.sampled,
                "fingerprint": self.corpus.fingerprint,
                "widened": self.corpus.widened,
            },
            "model": self.model,
            "queries": self.queries,
            "metrics": self.metrics,
            "splits": self.splits,
            "groups": [group.to_dict() for group in self.groups],
            "suppressed": list(self.suppressed),
            "replay": self.replay.to_dict(),
            "notes": list(self.notes),
        }


@dataclass(frozen=True)
class BootstrapResult:
    """Seeded percentile-bootstrap result over paired per-query deltas (D-07).

    ``sufficient`` is False for an empty delta list, in which case the mean
    and both CI bounds are 0.0 — an empty comparison never invents a number.
    """

    mean: float
    ci_low: float
    ci_high: float
    sufficient: bool
    resamples: int = BOOTSTRAP_RESAMPLES
    seed: int = 0


@dataclass(frozen=True)
class GateResult:
    """One noise-gate measurement: paired deltas, CI, counts, and the rule.

    ``sufficient`` requires at least ``SUPPRESS_BELOW`` paired queries — the
    same floor small groups are suppressed at. A winner additionally needs a
    CI excluding zero, a rounded mean delta of at least ``EPSILON`` (0.01),
    and an absolute mean delta strictly above the displayed ``1/N`` noise
    floor; ``regression`` mirrors that for a negative delta. A small or
    below-floor gate stays visible as a diagnostic but can never warrant a
    defaults change. ``noise_floor`` is 1/N (0.0 for an empty series).
    """

    n: int
    baseline_mean: float
    current_mean: float
    mean_delta: float
    ci_low: float
    ci_high: float
    helped: int
    hurt: int
    unchanged: int
    noise_floor: float
    winner: bool
    regression: bool
    sufficient: bool

    def to_dict(self) -> dict[str, Any]:
        """Serialize with a fixed key order."""
        return {
            "n": self.n,
            "baseline_mean": self.baseline_mean,
            "current_mean": self.current_mean,
            "mean_delta": self.mean_delta,
            "ci_low": self.ci_low,
            "ci_high": self.ci_high,
            "helped": self.helped,
            "hurt": self.hurt,
            "unchanged": self.unchanged,
            "noise_floor": self.noise_floor,
            "winner": self.winner,
            "regression": self.regression,
            "sufficient": self.sufficient,
        }


@dataclass(frozen=True)
class GroupGate:
    """One diagnosed leg x language x length group (diagnostic only, D-08)."""

    leg: str
    language: str
    length_bucket: str
    gate: GateResult

    def to_dict(self) -> dict[str, Any]:
        """Serialize the group identity plus its gate, marked diagnostic."""
        data: dict[str, Any] = {
            "leg": self.leg,
            "language": self.language,
            "length_bucket": self.length_bucket,
            "diagnostic": True,
        }
        data.update(self.gate.to_dict())
        return data


@dataclass(frozen=True)
class ReplayStability:
    """Replay stability against the saved snapshot (D-02).

    ``available`` is False when there is no saved snapshot or no current
    top-k to compare; ``baseline_available`` reports whether a saved replay
    snapshot exists at all. Jaccard is order-insensitive, so top-1 stability
    is reported alongside it.
    """

    available: bool
    baseline_available: bool
    num_queries: int
    jaccard_at_10: float
    top1_stability: float
    note: str

    def to_dict(self) -> dict[str, Any]:
        """Serialize with a fixed key order."""
        return {
            "available": self.available,
            "baseline_available": self.baseline_available,
            "num_queries": self.num_queries,
            "jaccard_at_10": self.jaccard_at_10,
            "top1_stability": self.top1_stability,
            "note": self.note,
        }


@dataclass(frozen=True)
class ComparisonReport:
    """The paired saved-vs-current comparison (D-07/D-12).

    ``current_report`` is the single ``PersonalReport`` contract ``--compare``
    auto-saves; ``splits``, ``legs``, ``leg_splits``, ``language_splits``,
    ``leg_language_splits``, and ``groups`` are gate results, and only the
    held-out summary gate can warrant a defaults change
    (``warrants_default_change``). ``legs`` and ``leg_splits`` exist so the
    D-12 clause "the title leg improves while body held-out does not regress"
    is directly readable from ``--compare`` output; the language axes make
    Phase 23's two-sided EN+ZH rule computable from the report alone.
    """

    current_report: PersonalReport
    baseline_metrics: dict[str, float]
    current_metrics: dict[str, float]
    overall: GateResult
    splits: dict[str, GateResult]
    legs: dict[str, GateResult]
    leg_splits: dict[str, dict[str, GateResult]]
    groups: list[GroupGate]
    suppressed: list[str]
    replay: ReplayStability
    retrieval: dict[str, str]
    top_k: int
    warrants_default_change: bool
    model_mismatch: bool
    language_splits: dict[str, dict[str, GateResult]] = field(default_factory=dict)
    leg_language_splits: dict[str, dict[str, dict[str, GateResult]]] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Serialize the comparison object for ``--json`` output."""
        return {
            "baseline": dict(self.baseline_metrics),
            "current": dict(self.current_metrics),
            "delta": {
                "mean": self.overall.mean_delta,
                "helped": self.overall.helped,
                "hurt": self.overall.hurt,
                "unchanged": self.overall.unchanged,
                "n": self.overall.n,
                "noise_floor": self.overall.noise_floor,
            },
            "ci": {"low": self.overall.ci_low, "high": self.overall.ci_high},
            "gate": {
                **self.overall.to_dict(),
                "warrants_default_change": self.warrants_default_change,
            },
            "splits": {
                "tuning": {
                    **self.splits["tuning"].to_dict(),
                    "diagnostic": True,
                },
                "heldout": {
                    **self.splits["heldout"].to_dict(),
                    "diagnostic": False,
                },
            },
            "legs": {leg: gate.to_dict() for leg, gate in self.legs.items()},
            "leg_splits": {
                leg: {split: gate.to_dict() for split, gate in splits.items()}
                for leg, splits in self.leg_splits.items()
            },
            "language_splits": {
                language: {split: gate.to_dict() for split, gate in splits.items()}
                for language, splits in self.language_splits.items()
            },
            "leg_language_splits": {
                leg: {
                    language: {split: gate.to_dict() for split, gate in splits.items()}
                    for language, splits in by_language.items()
                }
                for leg, by_language in self.leg_language_splits.items()
            },
            "groups": [group.to_dict() for group in self.groups],
            "suppressed": list(self.suppressed),
            "replay": self.replay.to_dict(),
            "retrieval": dict(self.retrieval),
            "top_k": self.top_k,
        }


def normalize_text(text: str) -> str:
    """NFC-normalize, casefold, and collapse whitespace to single spaces.

    The shared normalization for query dedupe and later hash splitting; it
    makes the "same" query hash and compare identically across platforms,
    including macOS NFD input (research Pitfall 9).
    """
    return " ".join(unicodedata.normalize("NFC", text).casefold().split())


def token_set(text: str) -> set[str]:
    """Tokenize normalized text into ASCII words and whole CJK runs."""
    return set(_TOKEN_RE.findall(normalize_text(text)))


def _budget_units(text: str) -> set[str]:
    """Comparison units for the overlap budget: CJK bigrams plus ASCII tokens.

    Whole CJK runs stay the FTS matching unit (``token_set``), but they are
    the wrong unit for plagiarism control: a verbatim CJK prefix of the title
    is a different whole-run token and would score zero overlap. The budget
    therefore compares CJK character bigrams (a single character for a
    one-character run) alongside ASCII tokens; search tokenization is
    unchanged (WR-08).
    """
    units: set[str] = set()
    for token in _TOKEN_RE.findall(normalize_text(text)):
        if _CJK_RUN_RE.fullmatch(token):
            if len(token) == 1:
                units.add(token)
            else:
                units.update(token[index : index + 2] for index in range(len(token) - 1))
        else:
            units.add(token)
    return units


def jaccard(left: set[str], right: set[str]) -> float:
    """Set Jaccard similarity; two empty sets are identical by definition."""
    union = left | right
    if not union:
        return 1.0
    return len(left & right) / len(union)


def _mean(values: Sequence[float]) -> float:
    """Arithmetic mean; empty input yields 0.0 (house style)."""
    return sum(values) / len(values) if values else 0.0


def assign_split(query: str) -> str:
    """Deterministic 50/50 split by the sha256 digest of normalized text (D-06).

    ``digest[0] < 128`` is ``tuning``; otherwise ``heldout``. Only
    ``hashlib.sha256`` is stable across processes and machines — the salted
    salted builtin hash is never used (research Pitfall 9).
    """
    digest = hashlib.sha256(normalize_text(query).encode("utf-8")).digest()
    return "tuning" if digest[0] < _SPLIT_THRESHOLD else "heldout"


def split_queries(queries: Sequence[SynthesizedQuery]) -> list[SynthesizedQuery]:
    """Assign a split to title/body queries; replay queries stay splitless.

    Replay measures stability, never a tuning/held-out decision, so it is
    excluded from the split vocabulary by construction (research A6).
    """
    return [
        replace(query, split=assign_split(query.query)) if query.leg in ("title", "body") else query
        for query in queries
    ]


def _is_cjk(character: str) -> bool:
    """True for a CJK Unified Ideograph (the tokenizer's run alphabet)."""
    return "一" <= character <= "鿿"


def classify_language(text: str) -> str:
    """Classify en/zh/mixed by the CJK codepoint ratio (research A9).

    The ratio is over non-whitespace characters: ``>= 0.5`` is ``zh``,
    ``< 0.1`` is ``en``, everything between is ``mixed``. Empty text is
    ``en`` (nothing Chinese was observed).
    """
    characters = [character for character in text if not character.isspace()]
    if not characters:
        return "en"
    ratio = sum(1 for character in characters if _is_cjk(character)) / len(characters)
    if ratio >= _ZH_RATIO:
        return "zh"
    if ratio < _EN_RATIO:
        return "en"
    return "mixed"


def _length_units(text: str) -> int:
    """Length units: one per ASCII token, one per CJK ideograph (Pitfall 11)."""
    units = 0
    for token in _TOKEN_RE.findall(normalize_text(text)):
        units += len(token) if _CJK_RUN_RE.fullmatch(token) else 1
    return units


def length_bucket(text: str) -> str:
    """Bucket query length: each CJK ideograph is one unit, else one per token.

    ``<= 2`` is ``short``, ``3-5`` is ``medium``, ``>= 6`` is ``long``. CJK
    ideographs count individually so a 12-character Chinese query is not
    misclassified as short (research Pitfall 11).
    """
    units = _length_units(text)
    if units <= _SHORT_MAX_UNITS:
        return "short"
    if units <= _MEDIUM_MAX_UNITS:
        return "medium"
    return "long"


def strip_markup(text: str) -> str:
    """Remove fenced code, inline code, URLs, HTML comments, and markdown markers.

    Body text is untrusted for markup: fenced code blocks, inline code,
    inline URLs, markdown links, HTML comments, ATX heading markers, and
    emphasis markers are stripped before a sentence can become a query
    (threat model, body synthesis boundary).
    """
    text = _FENCED_CODE_RE.sub(" ", text)
    text = _INLINE_CODE_RE.sub(" ", text)
    text = _HTML_COMMENT_RE.sub(" ", text)
    text = _MARKDOWN_LINK_RE.sub(r"\1", text)
    text = _URL_RE.sub(" ", text)
    text = _HEADING_RE.sub("", text)
    return _EMPHASIS_RE.sub("", text)


def _candidate_text(sentence: str) -> str | None:
    """Trim one sentence to a query of at most ``_BODY_MAX_TOKENS`` units.

    ASCII tokens are joined with spaces; a contiguous CJK run is kept whole
    (truncated to the remaining unit budget) so the FTS porter/CJK token
    semantics still match a phrase (research Pitfall 11).
    """
    pieces: list[str] = []
    used = 0
    for token in _TOKEN_RE.findall(normalize_text(sentence)):
        if _CJK_RUN_RE.fullmatch(token):
            take = token[: _BODY_MAX_TOKENS - used]
            if not take:
                break
            pieces.append(take)
            used += len(take)
        else:
            if used >= _BODY_MAX_TOKENS:
                break
            pieces.append(token)
            used += 1
    if used < _BODY_MIN_TOKENS:
        return None
    return " ".join(pieces)


def body_candidate(content: str) -> str | None:
    """Pick one deterministic paraphrased body sentence, or ``None``.

    Sentences split on ASCII and full-width sentence terminators. A sentence
    starting inside the opening 200 characters is skipped when a later
    sentence with at least ``_BODY_MIN_TOKENS`` length units exists
    (deterministic first match); otherwise the first long-enough sentence is
    used. The candidate is markup-stripped, capped at ``_BODY_MAX_TOKENS``
    units, and rejected below ``_BODY_MIN_TOKENS`` units. Length units count
    ASCII tokens and CJK ideographs individually, so a Chinese phrase is not
    rejected as one "token".
    """
    stripped = strip_markup(content)
    spans = [(match.start(), match.group()) for match in _SENTENCE_RE.finditer(stripped)]
    chosen: str | None = None
    for start, sentence in spans:
        if start >= _OPENING_CHARS and _length_units(sentence) >= _BODY_MIN_TOKENS:
            chosen = sentence
            break
    if chosen is None:
        for _start, sentence in spans:
            if _length_units(sentence) >= _BODY_MIN_TOKENS:
                chosen = sentence
                break
    if chosen is None:
        return None
    return _candidate_text(chosen)


def _classified(query: str, doc: DocumentRecord, leg: str) -> SynthesizedQuery:
    """Build one query with its language and length classification populated."""
    return SynthesizedQuery(
        query=query,
        target_doc_id=doc.id,
        target_path=doc.path,
        leg=leg,
        language=classify_language(query),
        length_bucket=length_bucket(query),
    )


def _leg_rank(leg: str) -> int:
    """Declared leg order index (title before body before replay)."""
    return LEGS.index(leg) if leg in LEGS else len(LEGS)


def _sample_key(doc: DocumentRecord) -> tuple[bytes, str, str]:
    """Deterministic sample order key: (sha256 digest, path, id).

    The digest is over ``path + NUL + checksum``; path and id are ascending
    tie-breaks so a path shared by two collections still has a unique,
    stable position (the id is the final tie-break, D-03).
    """
    payload = f"{doc.path}\0{doc.checksum}".encode()
    return (hashlib.sha256(payload).digest(), doc.path, doc.id)


def load_document_metadata(
    conn: sqlite3.Connection,
    collection_ids: Sequence[str] | None,
) -> list[DocumentRecord]:
    """Load whole-scope document metadata WITHOUT bodies (T-18-02).

    The SELECT names only metadata columns — never ``content`` — and the
    cursor is iterated row by row; ``fetchall()`` would materialize the
    corpus and is forbidden here. ``collection_ids`` follows the
    ``SearchOptions`` sentinel contract: ``None`` is unfiltered and ``[]``
    excludes every collection.
    """
    if collection_ids is not None and not collection_ids:
        return []
    query = "SELECT id, path, title, checksum, file_size FROM documents"
    params: list[object] = []
    if collection_ids:
        placeholders = ", ".join("?" for _ in collection_ids)
        query += f" WHERE collection_id IN ({placeholders})"
        params.extend(collection_ids)
    query += " ORDER BY path, id"
    # The iteration is lazy over the cursor (never fetchall()) so the
    # whole-corpus pass cannot materialize the corpus in one list of rows.
    return [
        DocumentRecord(
            id=str(row[0]),
            path=str(row[1]),
            title=str(row[2] or ""),
            checksum=str(row[3]),
            file_size=int(row[4] or 0),
        )
        for row in conn.execute(query, params)
    ]


def load_sampled_content(
    conn: sqlite3.Connection,
    doc_ids: Sequence[str],
    chunk_size: int = _CONTENT_CHUNK,
) -> dict[str, str]:
    """Load document bodies for the bounded sampled subset only.

    One parameterized ``SELECT id, content ... WHERE id IN (...)`` per chunk,
    sized below SQLite's host-parameter limit, so a widened sample never
    triggers ``too many SQL variables``; the whole-corpus pass stays
    metadata-only (T-18-02/T-18-05).
    """
    if chunk_size <= 0:
        raise ValueError("chunk_size must be positive")
    ordered = list(dict.fromkeys(str(doc_id) for doc_id in doc_ids))
    contents: dict[str, str] = {}
    for start in range(0, len(ordered), chunk_size):
        chunk = ordered[start : start + chunk_size]
        placeholders = ", ".join("?" for _ in chunk)
        statement = f"SELECT id, content FROM documents WHERE id IN ({placeholders})"
        for row in conn.execute(statement, chunk):
            contents[str(row[0])] = str(row[1])
    return contents


def load_replay_queries(conn: sqlite3.Connection) -> list[str]:
    """Load the replay query set from ``query_log`` — the only replay source.

    ``QueryLogRepository.history()`` returns one ``(query, count, last_used)``
    row per exact query string; the replay set is normalized (NFC/casefold/
    whitespace), deduped, sorted lexicographically ascending (never SQL row
    order), and capped at ``MAX_REPLAY_QUERIES`` (D-02, T-18-05). Only query
    text is read — never document content.
    """
    history = QueryLogRepository(conn).history()
    normalized = {normalize_text(query) for query, _count, _last_used in history}
    normalized.discard("")
    return sorted(normalized)[:MAX_REPLAY_QUERIES]


def replay_leg(
    queries: Sequence[str],
    search_fn: Callable[[str], list[SearchResult]],
    k: int = 10,
) -> ReplayResult:
    """Run one search per unique normalized query; record top-k paths.

    Replay is a stability instrument, not a quality metric: it computes no
    nDCG/Hit/group/split and never invents a baseline. Duplicate query text
    collapses to one record (first occurrence wins), so the dict key is the
    normalized query. Only result paths are stored (T-18-04).
    """
    top_k_paths: dict[str, list[str]] = {}
    seen: set[str] = set()
    for raw in queries:
        query = normalize_text(raw)
        if not query or query in seen:
            continue
        seen.add(query)
        results = search_fn(query)
        top_k_paths[query] = [result.path for result in results[: max(0, k)]]
    return ReplayResult(
        available=bool(top_k_paths),
        num_queries=len(top_k_paths),
        baseline_available=False,
        top_k_paths=top_k_paths,
        bias=REPLAY_BIAS_NOTE,
    )


def sample_documents(
    docs: Sequence[DocumentRecord],
    limit: int = MAX_SAMPLE_DOCUMENTS,
) -> list[DocumentRecord]:
    """Take the first ``limit`` documents in deterministic hash order.

    Sorting is fully explicit so two runs over the same index — and two
    collections indexing the same path — produce identical positions.
    """
    if limit <= 0:
        return []
    return sorted(docs, key=_sample_key)[:limit]


def dedupe_queries(
    queries: Sequence[SynthesizedQuery],
) -> tuple[list[SynthesizedQuery], dict[str, int]]:
    """Keep the first query per normalized text; count later collisions.

    Iteration follows the declared leg order (title before body) and then the
    input order, so the kept record is deterministic regardless of dict/set
    iteration order; each duplicate increments its losing leg's count.
    """
    ordered = sorted(enumerate(queries), key=lambda pair: (_leg_rank(pair[1].leg), pair[0]))
    seen: set[str] = set()
    kept: list[SynthesizedQuery] = []
    rejected_duplicate: dict[str, int] = {}
    for _index, query in ordered:
        key = normalize_text(query.query)
        if key in seen:
            rejected_duplicate[query.leg] = rejected_duplicate.get(query.leg, 0) + 1
            continue
        seen.add(key)
        kept.append(query)
    return kept, rejected_duplicate


def _normalize_counts(counts: dict[str, int]) -> dict[str, int]:
    """Return counts keyed by every synthesized leg (zeros included)."""
    return {leg: int(counts.get(leg, 0)) for leg in ("title", "body")}


def synthesize_title_queries(docs: Sequence[DocumentRecord]) -> SynthesisResult:
    """Synthesize one title/H1 known-item query per document (D-01/D-04).

    The trimmed ``documents.title`` is the query text: a title leg is
    exact-term by construction, so it is exempt from the body overlap budget
    (research Pitfall 1). Empty titles are rejected and counted; normalized
    duplicate titles keep the first in sampled-document order and count each
    later collision.
    """
    candidates: list[SynthesizedQuery] = []
    rejected_empty = 0
    for doc in docs:
        title = doc.title.strip()
        if not title:
            rejected_empty += 1
            continue
        candidates.append(_classified(title, doc, "title"))
    queries, rejected_duplicate = dedupe_queries(candidates)
    return SynthesisResult(
        queries=queries,
        rejected_empty={"title": rejected_empty},
        rejected_duplicate=rejected_duplicate,
        rejected_overlap={},
    )


def synthesize_body_queries(docs: Sequence[DocumentRecord]) -> SynthesisResult:
    """Synthesize one paraphrased body-snippet query per document (D-01/D-05).

    ``body_candidate`` owns the sentence choice, markup stripping, and the
    token floor; documents without a usable candidate are counted as
    ``empty`` and never emitted.
    """
    candidates: list[SynthesizedQuery] = []
    rejected_empty = 0
    for doc in docs:
        candidate = body_candidate(doc.content or "")
        if candidate is None:
            rejected_empty += 1
            continue
        candidates.append(_classified(candidate, doc, "body"))
    queries, rejected_duplicate = dedupe_queries(candidates)
    return SynthesisResult(
        queries=queries,
        rejected_empty={"body": rejected_empty},
        rejected_duplicate=rejected_duplicate,
        rejected_overlap={},
    )


def apply_overlap_budget(
    queries: Sequence[SynthesizedQuery],
    docs_by_id: dict[str, DocumentRecord],
) -> tuple[list[SynthesizedQuery], dict[str, int]]:
    """Apply the per-leg paraphrase budget (D-05).

    Body queries are measured by token Jaccard against the target document's
    title tokens plus the first 200 body characters; ``> OVERLAP_BUDGET``
    rejects (exactly 0.60 is accepted). CJK runs are compared as character
    bigrams so a verbatim Chinese prefix of the title cannot score zero
    overlap (WR-08); ASCII tokens and the FTS matching tokenizer are
    unchanged. Title queries are exact-term and stay unbudgeted, replay is
    never synthesized, and every rejection is counted per leg.
    """
    kept: list[SynthesizedQuery] = []
    rejected_overlap: dict[str, int] = {}
    for query in queries:
        if query.leg != "body":
            kept.append(query)
            continue
        doc = docs_by_id.get(query.target_doc_id)
        title = doc.title if doc is not None else ""
        opening = (doc.content or "")[:_OPENING_CHARS] if doc is not None else ""
        target_units = _budget_units(f"{title} {opening}")
        if jaccard(_budget_units(query.query), target_units) > OVERLAP_BUDGET:
            rejected_overlap["body"] = rejected_overlap.get("body", 0) + 1
            continue
        kept.append(query)
    return kept, rejected_overlap


def synthesize_known_item_queries(
    docs: Sequence[DocumentRecord],
    conn: sqlite3.Connection | None = None,
) -> SynthesisResult:
    """Orchestrate the known-item legs: title -> body -> overlap -> dedupe.

    With ``conn``, bodies are loaded only for ``docs`` (the bounded sampled
    subset); without it, records are expected to carry pre-loaded
    ``content``. The title leg is internal-deduped in its own synthesizer;
    the final dedupe catches cross-leg collisions in declared leg order, so
    a title always wins over a body query with the same normalized text.
    """
    if conn is not None:
        contents = load_sampled_content(conn, [doc.id for doc in docs])
        resolved = [replace(doc, content=contents.get(doc.id, "")) for doc in docs]
    else:
        resolved = list(docs)
    docs_by_id = {doc.id: doc for doc in resolved}
    title_result = synthesize_title_queries(resolved)
    body_result = synthesize_body_queries(resolved)
    combined = [*title_result.queries, *body_result.queries]
    filtered, rejected_overlap = apply_overlap_budget(combined, docs_by_id)
    kept, cross_leg_duplicates = dedupe_queries(filtered)
    duplicates: dict[str, int] = {}
    for counts in (title_result.rejected_duplicate, body_result.rejected_duplicate):
        for leg, count in counts.items():
            duplicates[leg] = duplicates.get(leg, 0) + count
    for leg, count in cross_leg_duplicates.items():
        duplicates[leg] = duplicates.get(leg, 0) + count
    return SynthesisResult(
        queries=kept,
        rejected_empty=_normalize_counts(
            {
                **title_result.rejected_empty,
                **body_result.rejected_empty,
            }
        ),
        rejected_duplicate=_normalize_counts(duplicates),
        rejected_overlap=_normalize_counts(rejected_overlap),
    )


class HeldoutFloorError(ValueError):
    """Raised when the sample cap is reached with a query floor unmet.

    Subclasses ``ValueError`` so the CLI's existing domain-error translation
    and ``pytest.raises(ValueError)`` callers stay valid. ``language_counts``
    carries the per-language held-out counts in declared ``LANGUAGES`` order
    (absent languages 0) so a shortfall is recordable evidence.
    """

    def __init__(  # noqa: PLR0913
        self,
        message: str,
        *,
        accepted: int,
        tuning: int,
        heldout: int,
        sampled: int,
        language_counts: dict[str, int],
    ) -> None:
        """Store the counted shortfall and its per-language evidence."""
        super().__init__(message)
        self.accepted = accepted
        self.tuning = tuning
        self.heldout = heldout
        self.sampled = sampled
        self.language_counts = language_counts


def heldout_language_counts(queries: Sequence[SynthesizedQuery]) -> dict[str, int]:
    """Held-out title/body query counts per language, in ``LANGUAGES`` order.

    Every declared language is present (absent ones count 0) so callers never
    depend on dict iteration order. Replay queries never enter; a query whose
    language is outside ``LANGUAGES`` is ignored.
    """
    counts: dict[str, int] = dict.fromkeys(LANGUAGES, 0)
    for query in queries:
        if query.leg not in ("title", "body") or query.split != "heldout":
            continue
        if query.language in counts:
            counts[query.language] += 1
    return counts


def _language_floor_unmet(
    queries: Sequence[SynthesizedQuery],
    required_languages: Sequence[str],
) -> bool:
    """True when any required language is below ``SUPPRESS_BELOW`` held out.

    An empty requirement list is always satisfied, so the pre-Phase-23
    default path is unchanged.
    """
    if not required_languages:
        return False
    counts = heldout_language_counts(queries)
    return any(counts.get(language, 0) < SUPPRESS_BELOW for language in required_languages)


def ensure_heldout(  # noqa: PLR0913 - explicit sample and floor controls
    metadata: Sequence[DocumentRecord],
    conn: sqlite3.Connection,
    *,
    initial: int = INITIAL_SAMPLE_DOCUMENTS,
    cap: int = MAX_SAMPLE_DOCUMENTS,
    required_languages: Sequence[str] = (),
    min_heldout: int = HELDOUT_MIN,
) -> tuple[list[DocumentRecord], SynthesisResult]:
    """Sample, synthesize, split, and widen until both floors are met (D-06).

    Starts from the first ``initial`` documents in deterministic sample order
    (strictly smaller than the cap whenever the corpus has more documents),
    loads bodies only for that slice, and while accepted queries are below
    ``MIN_QUERIES`` or held-out queries below ``min_heldout`` doubles the
    limit toward ``min(len(metadata), cap)``. A widened sample is a superset
    of the previous prefix, so bodies load only for the newly added
    documents. Only a floor still unmet at the cap raises a counted
    ``HeldoutFloorError`` naming accepted, tuning, held-out, and rejection
    counts.

    ``min_heldout`` defaults to ``HELDOUT_MIN`` (25) and can only raise the
    held-out floor: the epsilon gate's 101-query sample is requested by
    passing 101. ``required_languages`` opts into language-aware widening
    (D-07): while any listed language has fewer than ``SUPPRESS_BELOW``
    held-out queries the same doubling continues, and the cap guard carries
    the same condition so the error fires even when the total floors are
    already met. The default empty tuple preserves the pre-Phase-23 behavior
    byte-for-byte.
    """
    if not metadata:
        raise ValueError(
            "Personal eval needs indexed documents; found 0. "
            "Index documents with 'sif index update' and retry."
        )
    required_heldout = max(HELDOUT_MIN, int(min_heldout))
    hard_cap = min(len(metadata), cap)
    limit = max(1, min(initial, hard_cap))
    sampled = sample_documents(metadata, limit=limit)
    contents = load_sampled_content(conn, [doc.id for doc in sampled])
    docs = [replace(doc, content=contents.get(doc.id, "")) for doc in sampled]
    synthesis = _synthesize_and_split(docs)
    accepted = synthesis.queries
    heldout = sum(1 for query in accepted if query.split == "heldout")
    while (
        len(accepted) < MIN_QUERIES
        or heldout < required_heldout
        or _language_floor_unmet(accepted, required_languages)
    ) and limit < hard_cap:
        new_limit = min(limit * 2, hard_cap)
        previous_ids = {doc.id for doc in sampled}
        sampled = sample_documents(metadata, limit=new_limit)
        added = [doc for doc in sampled if doc.id not in previous_ids]
        contents.update(load_sampled_content(conn, [doc.id for doc in added]))
        docs = [replace(doc, content=contents.get(doc.id, "")) for doc in sampled]
        synthesis = _synthesize_and_split(docs)
        accepted = synthesis.queries
        heldout = sum(1 for query in accepted if query.split == "heldout")
        limit = new_limit
    if (
        len(accepted) < MIN_QUERIES
        or heldout < required_heldout
        or _language_floor_unmet(accepted, required_languages)
    ):
        tuning = len(accepted) - heldout
        empty = sum(synthesis.rejected_empty.values())
        duplicate = sum(synthesis.rejected_duplicate.values())
        overlap = sum(synthesis.rejected_overlap.values())
        language_counts = heldout_language_counts(accepted)
        rendered = ", ".join(f"{language}={count}" for language, count in language_counts.items())
        raise HeldoutFloorError(
            f"Personal eval needs at least {MIN_QUERIES} accepted queries with "
            f"{required_heldout} held out; accepted {len(accepted)} "
            f"(tuning {tuning}, held-out {heldout}) from {len(sampled)} sampled "
            f"documents; rejected {empty + duplicate + overlap} "
            f"({empty} empty, {duplicate} duplicate, {overlap} overlap); "
            f"held-out by language {rendered}. "
            "Index more documents with 'sif index update' and retry.",
            accepted=len(accepted),
            tuning=tuning,
            heldout=heldout,
            sampled=len(sampled),
            language_counts=language_counts,
        )
    return sampled, synthesis


def _synthesize_and_split(docs: Sequence[DocumentRecord]) -> SynthesisResult:
    """Synthesize title+body queries over pre-loaded docs, then split them."""
    synthesis = synthesize_known_item_queries(docs)
    return replace(synthesis, queries=split_queries(synthesis.queries))


def build_legacy_fixture(queries: Sequence[SynthesizedQuery]) -> dict[str, Any]:
    """Build the legacy binary fixture the evaluator already parses (D-04).

    The target document is grade 1 and every other document grade 0; no
    ``category``/``split``/``relevance`` keys are emitted, so
    ``SearchEvaluator`` takes its documented legacy path.
    """
    return {
        "relevance_key": "docid",
        "queries": [
            {"query": query.query, "relevant_docids": [query.target_doc_id]} for query in queries
        ],
    }


def corpus_fingerprint(metadata: Sequence[DocumentRecord]) -> str:
    """Truncated sha256 over the whole in-scope metadata (A11).

    Sorted ``path + NUL + checksum + NUL + file_size`` lines; mtime is
    excluded so a touch-only change never refuses a comparison. Computed over
    ALL in-scope metadata before sampling so the fingerprint identifies the
    corpus, not the sampled subset.
    """
    lines = sorted(f"{doc.path}\0{doc.checksum}\0{doc.file_size}" for doc in metadata)
    return hashlib.sha256("\n".join(lines).encode()).hexdigest()[:16]


def require_minimum_queries(synthesis: SynthesisResult) -> None:
    """Raise ``ValueError`` when accepted queries fall below ``MIN_QUERIES``.

    The message carries accepted and rejected counts (with the empty /
    duplicate / overlap split) and the index remedy; the CLI translates it to
    a ``ClickException`` so a too-small corpus fails loudly (D-11).
    """
    accepted = len(synthesis.queries)
    if accepted >= MIN_QUERIES:
        return
    empty = sum(synthesis.rejected_empty.values())
    duplicate = sum(synthesis.rejected_duplicate.values())
    overlap = sum(synthesis.rejected_overlap.values())
    rejected = empty + duplicate + overlap
    raise ValueError(
        f"Personal eval needs at least {MIN_QUERIES} accepted queries; "
        f"accepted {accepted}, rejected {rejected} "
        f"({empty} empty, {duplicate} duplicate, {overlap} overlap). "
        "Index more documents with 'sif index update' and retry."
    )


def evaluate_known_items(
    queries: Sequence[SynthesizedQuery],
    search_fn: Callable[[str], list[SearchResult]],
) -> list[QueryEvaluation]:
    """Evaluate synthesized known-item queries through the legacy fixture.

    The only metric path: ``SearchEvaluator`` parses the fixture and
    ``evaluate_per_query`` reuses the shared nDCG/Hit math (D-04); nothing
    here reimplements metric arithmetic.
    """
    evaluator = SearchEvaluator(build_legacy_fixture(queries))
    return evaluator.evaluate_per_query(search_fn)


def group_metrics(
    records: Sequence[PersonalQueryRecord],
) -> tuple[list[GroupMetrics], list[str]]:
    """Group known-item records by leg x language x length bucket (D-08).

    Groups are emitted in declared ``LEGS x LANGUAGES x LENGTH_BUCKETS``
    order. Groups with fewer than ``SUPPRESS_BELOW`` queries are omitted and
    their stable names (``leg=.../language=.../length=...``) are returned so
    a small sample is never rendered as a zero row. Replay records never
    enter (they are not known-item records).
    """
    buckets: dict[tuple[str, str, str], list[PersonalQueryRecord]] = {}
    for record in records:
        if record.leg not in ("title", "body"):
            continue
        key = (record.leg, record.language, record.length_bucket)
        buckets.setdefault(key, []).append(record)
    groups: list[GroupMetrics] = []
    suppressed: list[str] = []
    for leg in LEGS:
        if leg not in ("title", "body"):
            continue
        for language in LANGUAGES:
            for length in LENGTH_BUCKETS:
                members = buckets.get((leg, language, length))
                if not members:
                    continue
                name = f"leg={leg}/language={language}/length={length}"
                if len(members) < SUPPRESS_BELOW:
                    suppressed.append(name)
                    continue
                groups.append(
                    GroupMetrics(
                        leg=leg,
                        language=language,
                        length_bucket=length,
                        count=len(members),
                        ndcg_at_10=_mean([member.ndcg_at_10 for member in members]),
                        hit_at_10=_mean([member.hit_at_10 for member in members]),
                    )
                )
    return groups, suppressed


def build_query_records(
    queries: Sequence[SynthesizedQuery],
    evaluations: Sequence[QueryEvaluation],
) -> list[PersonalQueryRecord]:
    """Pair per-query evaluations with their synthesized metadata, in order.

    ``retrieved_doc_ids`` is the evaluator's ``retrieved_keys`` — one string
    per retrieved rank, ``""`` when a result carries no document id — so it
    stays rank-aligned with ``retrieved_paths`` (Plan 03's grading identity).
    """
    if len(queries) != len(evaluations):
        raise ValueError(
            f"Expected one evaluation per synthesized query; "
            f"got {len(queries)} queries and {len(evaluations)} evaluations."
        )
    return [
        PersonalQueryRecord(
            query=query.query,
            target_doc_id=query.target_doc_id,
            target_path=query.target_path,
            leg=query.leg,
            language=query.language,
            length_bucket=query.length_bucket,
            split=query.split or assign_split(query.query),
            ndcg_at_10=evaluation.ndcg_at_10,
            hit_at_10=evaluation.hit_at_10,
            retrieved_doc_ids=list(evaluation.retrieved_keys),
            retrieved_paths=list(evaluation.retrieved_paths),
        )
        for query, evaluation in zip(queries, evaluations, strict=True)
    ]


def _per_leg_queries(records: Sequence[PersonalQueryRecord]) -> dict[str, Any]:
    """Per-leg accepted/rejection counts plus the applied budget (D-05)."""
    by_leg: dict[str, Any] = {}
    for leg in ("title", "body"):
        members = [record for record in records if record.leg == leg]
        by_leg[leg] = {
            "accepted": len(members),
            "rejected_empty": 0,
            "rejected_duplicate": 0,
            "rejected_overlap": 0,
            "budget": LEG_BUDGETS[leg],
            "exact_term": leg in EXACT_TERM_LEGS,
        }
    return by_leg


def build_personal_report(  # noqa: PLR0913
    *,
    retrieval: str,
    top_k: int,
    metadata: Sequence[DocumentRecord],
    sampled: Sequence[DocumentRecord],
    model: dict[str, Any] | None,
    synthesis: SynthesisResult,
    evaluations: Sequence[QueryEvaluation],
    replay: ReplayResult,
    notes: list[str],
    corpus: CorpusSummary | None = None,
) -> PersonalReport:
    """Assemble the one report contract from synthesis + per-query evaluation.

    Metrics, splits, groups, and records are computed exactly once here; the
    CLI renders ``to_dict()`` and never recomputes a field. Known-item
    metrics are means over title+body records only — replay never enters.
    ``corpus`` overrides the computed summary so ``--compare`` can carry the
    saved sample size and the recomputed current fingerprint without a
    synthetic sampled-document list.
    """
    records = build_query_records(synthesis.queries, evaluations)
    groups, suppressed = group_metrics(records)
    splits = {
        split: sum(1 for record in records if record.split == split)
        for split in ("tuning", "heldout")
    }
    by_leg = _per_leg_queries(records)
    for leg, counts in by_leg.items():
        counts["rejected_empty"] = synthesis.rejected_empty.get(leg, 0)
        counts["rejected_duplicate"] = synthesis.rejected_duplicate.get(leg, 0)
        counts["rejected_overlap"] = synthesis.rejected_overlap.get(leg, 0)
    queries = {
        "accepted": len(records),
        "rejected_empty": sum(synthesis.rejected_empty.values()),
        "rejected_duplicate": sum(synthesis.rejected_duplicate.values()),
        "rejected_overlap": sum(synthesis.rejected_overlap.values()),
        "by_leg": by_leg,
    }
    metrics = {
        "ndcg_at_10": _mean([record.ndcg_at_10 for record in records]),
        "hit_at_10": _mean([record.hit_at_10 for record in records]),
        "num_queries": len(records),
    }
    corpus_summary = corpus or CorpusSummary(
        documents=len(metadata),
        sampled=len(sampled),
        fingerprint=corpus_fingerprint(metadata),
        widened=len(sampled) > INITIAL_SAMPLE_DOCUMENTS,
    )
    return PersonalReport(
        retrieval=retrieval,
        top_k=top_k,
        corpus=corpus_summary,
        model=model,
        metrics=metrics,
        splits=splits,
        groups=groups,
        suppressed=suppressed,
        queries=queries,
        records=records,
        replay=replay,
        notes=list(notes),
    )


def run_to_saved(report: PersonalReport) -> SavedRun:
    """Build the versioned saved run from the one report contract (D-10/D-12).

    The fresh path passes its own ``PersonalReport``; ``--compare`` passes
    ``ComparisonReport.current_report``, so both paths share one record
    source and one ``created_at`` stamp (taken here, at call time).
    ``report.records`` map in order to query records; replay paths and the
    corpus identity come from the same report. No document body is read: a
    body-leg query string is the short synthesized excerpt documented in
    ``docs/benchmarking.md``, never the document's full content.
    """
    return SavedRun(
        version=SAVED_RUN_VERSION,
        created_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
        top_k=report.top_k,
        corpus={
            "fingerprint": report.corpus.fingerprint,
            "documents": report.corpus.documents,
            "sampled": report.corpus.sampled,
        },
        retrieval=report.retrieval,
        model=dict(report.model) if report.model is not None else None,
        queries=[
            SavedQueryRecord(
                query=record.query,
                target_path=record.target_path,
                target_doc_id=record.target_doc_id,
                leg=record.leg,
                language=record.language,
                length_bucket=record.length_bucket,
                split=record.split,
                grade=1,
                retrieved=list(record.retrieved_paths[: report.top_k]),
                retrieved_doc_ids=list(record.retrieved_doc_ids[: report.top_k]),
            )
            for record in report.records
        ],
        replay={
            "available": report.replay.available,
            "queries": [
                {"query": query, "top_k_paths": list(paths)}
                for query, paths in report.replay.top_k_paths.items()
            ],
        },
    )


def saved_run_to_dict(run: SavedRun) -> dict[str, Any]:
    """Serialize a saved run with a fixed, versioned key order.

    Every document-derived value is a path, an id, or the synthesized query
    string (whose body-leg excerpt is documented in ``docs/benchmarking.md``);
    no full document body, snippet, or embedding is ever emitted (T-18-08).
    """
    return {
        "version": run.version,
        "created_at": run.created_at,
        "top_k": run.top_k,
        "corpus": {
            "fingerprint": run.corpus["fingerprint"],
            "documents": run.corpus["documents"],
            "sampled": run.corpus["sampled"],
        },
        "retrieval": run.retrieval,
        "model": dict(run.model) if run.model is not None else None,
        "queries": [
            {
                "query": record.query,
                "target_path": record.target_path,
                "target_doc_id": record.target_doc_id,
                "leg": record.leg,
                "language": record.language,
                "length_bucket": record.length_bucket,
                "split": record.split,
                "grade": record.grade,
                "retrieved": list(record.retrieved),
                "retrieved_doc_ids": list(record.retrieved_doc_ids),
            }
            for record in run.queries
        ],
        "replay": {
            "available": run.replay["available"],
            "queries": [
                {
                    "query": entry["query"],
                    "top_k_paths": list(entry["top_k_paths"]),
                }
                for entry in run.replay["queries"]
            ],
        },
    }


def _saved_defect(field: str, detail: str) -> NoReturn:
    """Raise a saved-run validation error naming the offending field path."""
    raise ValueError(f"Invalid saved run field '{field}': {detail}")


def _saved_dict(value: object, field: str) -> dict[str, Any]:
    """Require a JSON object, never escaping as a KeyError/TypeError."""
    if not isinstance(value, dict):
        _saved_defect(field, f"expected a JSON object, got {type(value).__name__}")
    return value


def _saved_str(
    value: object,
    field: str,
    *,
    max_length: int | None = None,
    non_empty: bool = False,
) -> str:
    """Require a string, optionally capped and non-empty."""
    if not isinstance(value, str):
        _saved_defect(field, f"expected a string, got {type(value).__name__}")
    if non_empty and not value:
        _saved_defect(field, "must be a non-empty string")
    if max_length is not None and len(value) > max_length:
        _saved_defect(field, f"must be at most {max_length} characters")
    return value


def _saved_int(
    value: object,
    field: str,
    *,
    minimum: int | None = None,
    maximum: int | None = None,
) -> int:
    """Require a real integer (bool and non-finite floats rejected)."""
    if isinstance(value, float) and not math.isfinite(value):
        _saved_defect(field, f"must be a finite number, got {value!r}")
    if isinstance(value, bool) or not isinstance(value, int):
        _saved_defect(field, f"expected an integer, got {type(value).__name__}")
    if minimum is not None and value < minimum:
        _saved_defect(field, f"must be >= {minimum}, got {value}")
    if maximum is not None and value > maximum:
        _saved_defect(field, f"must be <= {maximum}, got {value}")
    return value


def _saved_str_list(
    value: object,
    field: str,
    *,
    max_length: int,
    max_items: int | None = None,
) -> list[str]:
    """Require a list of capped strings; entry defects name ``field[i]``."""
    if not isinstance(value, list):
        _saved_defect(field, f"expected a list of strings, got {type(value).__name__}")
    if max_items is not None and len(value) > max_items:
        _saved_defect(field, f"must contain at most {max_items} entries")
    return [
        _saved_str(item, f"{field}[{index}]", max_length=max_length)
        for index, item in enumerate(value)
    ]


def _validate_saved_record(item: object, index: int) -> SavedQueryRecord:
    """Validate one query record; every defect names its field path."""
    field = f"queries[{index}]"
    record = _saved_dict(item, field)
    for forbidden in _SAVED_FORBIDDEN_KEYS:
        if forbidden in record:
            _saved_defect(
                f"{field}.{forbidden}",
                "saved runs never store document content or snippets",
            )
    query = _saved_str(
        record.get("query"),
        f"{field}.query",
        max_length=_SAVED_QUERY_MAX_CHARS,
    )
    target_path = _saved_str(
        record.get("target_path"),
        f"{field}.target_path",
        max_length=_SAVED_PATH_MAX_CHARS,
    )
    target_doc_id = _saved_str(
        record.get("target_doc_id"),
        f"{field}.target_doc_id",
        max_length=_SAVED_ID_MAX_CHARS,
    )
    leg = _saved_str(record.get("leg"), f"{field}.leg")
    if leg not in _SAVED_LEGS:
        _saved_defect(f"{field}.leg", f"must be one of {sorted(_SAVED_LEGS)}, got {leg!r}")
    language = _saved_str(record.get("language"), f"{field}.language")
    if language not in LANGUAGES:
        _saved_defect(
            f"{field}.language",
            f"must be one of {list(LANGUAGES)}, got {language!r}",
        )
    length = _saved_str(record.get("length_bucket"), f"{field}.length_bucket")
    if length not in LENGTH_BUCKETS:
        _saved_defect(
            f"{field}.length_bucket",
            f"must be one of {list(LENGTH_BUCKETS)}, got {length!r}",
        )
    split = _saved_str(record.get("split"), f"{field}.split")
    if split not in _SAVED_SPLITS:
        _saved_defect(
            f"{field}.split",
            f"must be one of {sorted(_SAVED_SPLITS)}, got {split!r}",
        )
    grade = record.get("grade")
    if isinstance(grade, bool) or not isinstance(grade, int) or grade != 1:
        _saved_defect(f"{field}.grade", f"must be the integer 1, got {grade!r}")
    retrieved = _saved_str_list(
        record.get("retrieved"),
        f"{field}.retrieved",
        max_length=_SAVED_PATH_MAX_CHARS,
        max_items=MAX_SAVED_RECORDS,
    )
    retrieved_doc_ids = _saved_str_list(
        record.get("retrieved_doc_ids"),
        f"{field}.retrieved_doc_ids",
        max_length=_SAVED_ID_MAX_CHARS,
        max_items=MAX_SAVED_RECORDS,
    )
    if len(retrieved) != len(retrieved_doc_ids):
        _saved_defect(
            f"{field}.retrieved_doc_ids",
            "must be rank-aligned with "
            f"'{field}.retrieved' (got {len(retrieved_doc_ids)} ids for "
            f"{len(retrieved)} paths)",
        )
    return SavedQueryRecord(
        query=query,
        target_path=target_path,
        target_doc_id=target_doc_id,
        leg=leg,
        language=language,
        length_bucket=length,
        split=split,
        grade=1,
        retrieved=retrieved,
        retrieved_doc_ids=retrieved_doc_ids,
    )


def _validate_saved_replay(value: object) -> dict[str, Any]:
    """Validate the replay snapshot: booleans, strings, and path lists only."""
    replay = _saved_dict(value, "replay")
    available = replay.get("available")
    if not isinstance(available, bool):
        _saved_defect("replay.available", "must be a boolean")
    queries = replay.get("queries")
    if not isinstance(queries, list):
        _saved_defect("replay.queries", "must be a list")
    if len(queries) > MAX_SAVED_RECORDS:
        _saved_defect(
            "replay.queries",
            f"must contain at most {MAX_SAVED_RECORDS} entries",
        )
    entries: list[dict[str, Any]] = []
    for index, item in enumerate(queries):
        field = f"replay.queries[{index}]"
        entry = _saved_dict(item, field)
        for forbidden in _SAVED_FORBIDDEN_KEYS:
            if forbidden in entry:
                _saved_defect(
                    f"{field}.{forbidden}",
                    "saved runs never store document content or snippets",
                )
        query = _saved_str(
            entry.get("query"),
            f"{field}.query",
            max_length=_SAVED_QUERY_MAX_CHARS,
        )
        paths = _saved_str_list(
            entry.get("top_k_paths"),
            f"{field}.top_k_paths",
            max_length=_SAVED_PATH_MAX_CHARS,
            max_items=MAX_SAVED_RECORDS,
        )
        entries.append({"query": query, "top_k_paths": paths})
    return {"available": available, "queries": entries}


def validate_saved_run(data: object) -> SavedRun:
    """Validate a whole saved-run envelope before trusting any record (T-18-07).

    The full envelope is type/range-checked with ``.get``/``isinstance`` so a
    malformed file can never escape as a ``KeyError``/``TypeError``; version,
    caps, enums, and rank-aligned arrays are enforced, and every defect raises
    ``ValueError`` naming the offending field path.
    """
    if not isinstance(data, dict):
        raise ValueError(
            f"Invalid saved run root: expected a JSON object, got {type(data).__name__}"
        )
    version = _saved_int(data.get("version"), "version")
    if version != SAVED_RUN_VERSION:
        _saved_defect(
            "version",
            f"unsupported schema version {version!r}; expected {SAVED_RUN_VERSION}",
        )
    created_at = _saved_str(data.get("created_at"), "created_at")
    corpus = _saved_dict(data.get("corpus"), "corpus")
    fingerprint = _saved_str(
        corpus.get("fingerprint"),
        "corpus.fingerprint",
        max_length=_SAVED_FINGERPRINT_MAX_CHARS,
        non_empty=True,
    )
    documents = _saved_int(corpus.get("documents"), "corpus.documents", minimum=0)
    sampled = _saved_int(corpus.get("sampled"), "corpus.sampled", minimum=0)
    if sampled > documents:
        _saved_defect(
            "corpus.sampled",
            f"must not exceed 'corpus.documents' ({documents}), got {sampled}",
        )
    retrieval = _saved_str(data.get("retrieval"), "retrieval")
    if retrieval not in _SAVED_RETRIEVAL_MODES:
        _saved_defect(
            "retrieval",
            f"must be one of {sorted(_SAVED_RETRIEVAL_MODES)}, got {retrieval!r}",
        )
    top_k = _saved_int(
        data.get("top_k"),
        "top_k",
        minimum=1,
        maximum=MAX_TOP_K,
    )
    model_data = data.get("model")
    model: dict[str, Any] | None = None
    if model_data is not None:
        model_dict = _saved_dict(model_data, "model")
        model = {
            "model_name": _saved_str(
                model_dict.get("model_name"),
                "model.model_name",
                max_length=_SAVED_MODEL_FIELD_MAX_CHARS,
            ),
            "model_type": _saved_str(
                model_dict.get("model_type"),
                "model.model_type",
                max_length=_SAVED_MODEL_FIELD_MAX_CHARS,
            ),
            "dimension": _saved_int(
                model_dict.get("dimension"),
                "model.dimension",
                minimum=1,
            ),
        }
    queries_data = data.get("queries")
    if not isinstance(queries_data, list):
        _saved_defect("queries", "must be a list")
    if not queries_data:
        _saved_defect("queries", "must contain at least one query record")
    if len(queries_data) > MAX_SAVED_RECORDS:
        _saved_defect(
            "queries",
            f"must contain at most {MAX_SAVED_RECORDS} query records",
        )
    queries = [_validate_saved_record(item, index) for index, item in enumerate(queries_data)]
    replay = _validate_saved_replay(data.get("replay"))
    return SavedRun(
        version=version,
        created_at=created_at,
        top_k=top_k,
        corpus={
            "fingerprint": fingerprint,
            "documents": documents,
            "sampled": sampled,
        },
        retrieval=retrieval,
        model=model,
        queries=queries,
        replay=replay,
    )


def write_saved_run(run: SavedRun, path: str | Path) -> Path:
    """Write a saved run atomically, refusing anything the loader would reject.

    The serialized payload is size-checked against ``MAX_SAVED_FILE_BYTES``
    before any file is created, so the writer can never emit a file its own
    loader rejects as oversized. The write is a sibling temp file followed by
    ``replace``. No path named inside the run is ever opened: the destination
    is the caller's explicit path.
    """
    payload = json.dumps(saved_run_to_dict(run), indent=2) + "\n"
    encoded = payload.encode("utf-8")
    if len(encoded) > MAX_SAVED_FILE_BYTES:
        raise ValueError(
            f"Saved run is {len(encoded)} bytes; exceeds the "
            f"{MAX_SAVED_FILE_BYTES}-byte cap. Reduce -n/--limit or the "
            "evaluated corpus scope."
        )
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_name(f".{destination.name}.tmp")
    temporary.write_bytes(encoded)
    temporary.replace(destination)
    return destination


def load_saved_run(path: str | Path) -> SavedRun:
    """Load and fully validate a saved run, failing loudly on any defect.

    The 5 MB cap is enforced from the file size before decode; OSError,
    decode errors, and any structural defect become ``ValueError`` with the
    cause retained (the CLI translates it to ``ClickException``). Saved
    paths are opaque values — nothing from the file is ever opened.
    """
    source = Path(path)
    try:
        size = source.stat().st_size
    except OSError as error:
        raise ValueError(f"Cannot read saved run {source}: {error}") from error
    if size > MAX_SAVED_FILE_BYTES:
        raise ValueError(
            f"Saved run {source} is {size} bytes; exceeds the "
            f"{MAX_SAVED_FILE_BYTES}-byte cap. Refusing to load it."
        )
    try:
        data = json.loads(source.read_text(encoding="utf-8"))
    except RecursionError as error:
        # CPython's JSON decoder raises RecursionError for deeply nested
        # input (well under the byte cap); untrusted input must still become
        # the documented ValueError, never a traceback (WR-03).
        raise ValueError(f"Cannot load saved run {source}: JSON is nested too deeply") from error
    except (OSError, ValueError) as error:
        raise ValueError(f"Cannot load saved run {source}: {error}") from error
    try:
        return validate_saved_run(data)
    except ValueError:
        raise
    except (KeyError, TypeError) as error:  # pragma: no cover - defensive
        raise ValueError(f"Invalid saved run {source}: {error}") from error


def paired_bootstrap(
    deltas: Sequence[float],
    resamples: int = BOOTSTRAP_RESAMPLES,
    seed: int = 0,
) -> BootstrapResult:
    """Seeded percentile bootstrap over paired per-query deltas (D-07).

    ``random.Random(seed)`` draws ``rng.randrange(n)`` in a fixed loop order,
    so the same delta list produces the same mean and CI on every run and
    machine. Percentiles reuse ``benchmark.percentile`` (p in 0-100, linear
    interpolation). An empty input is ``sufficient=False`` with zero values.
    """
    if resamples <= 0:
        raise ValueError("resamples must be positive")
    if not deltas:
        return BootstrapResult(
            mean=0.0,
            ci_low=0.0,
            ci_high=0.0,
            sufficient=False,
            resamples=resamples,
            seed=seed,
        )
    rng = random.Random(seed)
    n = len(deltas)
    means = [sum(deltas[rng.randrange(n)] for _ in range(n)) / n for _ in range(resamples)]
    return BootstrapResult(
        mean=_mean(deltas),
        ci_low=percentile(means, 2.5),
        ci_high=percentile(means, 97.5),
        sufficient=True,
        resamples=resamples,
        seed=seed,
    )


def noise_gate(
    baseline_values: Sequence[float],
    current_values: Sequence[float],
) -> GateResult:
    """Paired noise gate: rounded deltas, CI, counts, 1/N, and the tie rule.

    Per-query deltas are ``round(current - baseline, 6)`` (the house rounded
    arithmetic) and the mean is bootstrapped. ``sufficient`` requires at
    least ``SUPPRESS_BELOW`` paired queries. A winner requires all of: the
    N floor, a CI excluding zero, ``round(mean_delta, 6) >= EPSILON``, and an
    absolute mean delta strictly above the displayed 1/N noise floor — so a
    nominal 0.01 win can never outrank its own noise floor (WR-06). A
    negative winner is only a regression flag, never a defaults change.
    Empty input is insufficient with a 0.0 noise floor.
    """
    if len(baseline_values) != len(current_values):
        raise ValueError(
            "baseline and current series must pair one-to-one; got "
            f"{len(baseline_values)} and {len(current_values)} values"
        )
    deltas = [
        round(current - baseline, 6)
        for baseline, current in zip(baseline_values, current_values, strict=True)
    ]
    if not deltas:
        return GateResult(
            n=0,
            baseline_mean=0.0,
            current_mean=0.0,
            mean_delta=0.0,
            ci_low=0.0,
            ci_high=0.0,
            helped=0,
            hurt=0,
            unchanged=0,
            noise_floor=0.0,
            winner=False,
            regression=False,
            sufficient=False,
        )
    bootstrap = paired_bootstrap(deltas)
    mean_delta = bootstrap.mean
    noise_floor = 1.0 / len(deltas)
    excludes_zero = bootstrap.ci_low > 0 or bootstrap.ci_high < 0
    improvement = round(mean_delta, 6) >= EPSILON
    regression = round(mean_delta, 6) <= -EPSILON
    sufficient = len(deltas) >= SUPPRESS_BELOW
    exceeds_floor = abs(mean_delta) > noise_floor
    return GateResult(
        n=len(deltas),
        baseline_mean=_mean(baseline_values),
        current_mean=_mean(current_values),
        mean_delta=mean_delta,
        ci_low=bootstrap.ci_low,
        ci_high=bootstrap.ci_high,
        helped=sum(1 for delta in deltas if delta > 0),
        hurt=sum(1 for delta in deltas if delta < 0),
        unchanged=sum(1 for delta in deltas if delta == 0),
        noise_floor=noise_floor,
        winner=sufficient and excludes_zero and improvement and exceeds_floor,
        regression=sufficient and excludes_zero and regression and exceeds_floor,
        sufficient=sufficient,
    )


def group_noise_gates(
    saved_queries: Sequence[SavedQueryRecord],
    baseline_values: Sequence[float],
    current_values: Sequence[float],
) -> tuple[list[GroupGate], list[str]]:
    """Per-group gates in declared order, with <10 groups named not zeroed.

    Groups are keyed by the saved record's ``(leg, language, length_bucket)``
    and emitted in ``LEGS x LANGUAGES x LENGTH_BUCKETS`` order. Only present
    groups with 1..``SUPPRESS_BELOW``-1 queries are suppressed and named, so
    an unobserved combination never produces a rendered zero row (D-08).
    """
    if not (len(saved_queries) == len(baseline_values) == len(current_values)):
        raise ValueError("saved queries and both metric series must have equal lengths")
    buckets: dict[tuple[str, str, str], list[int]] = {}
    for index, record in enumerate(saved_queries):
        if record.leg not in ("title", "body"):
            continue
        key = (record.leg, record.language, record.length_bucket)
        buckets.setdefault(key, []).append(index)
    groups: list[GroupGate] = []
    suppressed: list[str] = []
    for leg in ("title", "body"):
        for language in LANGUAGES:
            for length in LENGTH_BUCKETS:
                indices = buckets.get((leg, language, length))
                if not indices:
                    continue
                name = f"leg={leg}/language={language}/length={length}"
                if len(indices) < SUPPRESS_BELOW:
                    suppressed.append(name)
                    continue
                groups.append(
                    GroupGate(
                        leg=leg,
                        language=language,
                        length_bucket=length,
                        gate=noise_gate(
                            [baseline_values[index] for index in indices],
                            [current_values[index] for index in indices],
                        ),
                    )
                )
    return groups, suppressed


def leg_noise_gates(
    saved_queries: Sequence[SavedQueryRecord],
    baseline_values: Sequence[float],
    current_values: Sequence[float],
) -> tuple[dict[str, GateResult], dict[str, dict[str, GateResult]]]:
    """Per-leg and per-leg x split paired gates for the D-12 rule.

    Every leg present in the saved run gets a gate over all of its records and
    a gate for each of ``tuning``/``heldout``. A split with no records in that
    leg is passed two empty series, which ``noise_gate`` reports as
    ``sufficient: False`` — never a fabricated zero winner.
    """
    if not (len(saved_queries) == len(baseline_values) == len(current_values)):
        raise ValueError("saved queries and both metric series must have equal lengths")
    indices: dict[str, dict[str, list[int]]] = {}
    for index, record in enumerate(saved_queries):
        per_split = indices.setdefault(record.leg, {"tuning": [], "heldout": []})
        per_split.setdefault(record.split, []).append(index)
    legs: dict[str, GateResult] = {}
    leg_splits: dict[str, dict[str, GateResult]] = {}
    for leg, per_split in indices.items():
        all_indices = [index for split_indices in per_split.values() for index in split_indices]
        legs[leg] = noise_gate(
            [baseline_values[index] for index in all_indices],
            [current_values[index] for index in all_indices],
        )
        leg_splits[leg] = {
            split: noise_gate(
                [baseline_values[index] for index in per_split.get(split, [])],
                [current_values[index] for index in per_split.get(split, [])],
            )
            for split in ("tuning", "heldout")
        }
    return legs, leg_splits


def language_noise_gates(
    saved_queries: Sequence[SavedQueryRecord],
    baseline_values: Sequence[float],
    current_values: Sequence[float],
) -> dict[str, dict[str, GateResult]]:
    """Per-language and per-language x split paired gates (D-06, D-08).

    Every language present in the saved run's title/body records gets one
    gate per split, emitted in declared ``LANGUAGES`` order (never dict
    order). A language with no records at all has no key; a present language
    with no records in one split is passed two empty series, which
    ``noise_gate`` reports as ``n=0, sufficient=False`` — a visible
    diagnostic, never a fabricated zero winner.
    """
    if not (len(saved_queries) == len(baseline_values) == len(current_values)):
        raise ValueError("saved queries and both metric series must have equal lengths")
    indices: dict[str, dict[str, list[int]]] = {}
    for index, record in enumerate(saved_queries):
        if record.leg not in ("title", "body"):
            continue
        per_split = indices.setdefault(record.language, {"tuning": [], "heldout": []})
        per_split.setdefault(record.split, []).append(index)
    languages: dict[str, dict[str, GateResult]] = {}
    for language in LANGUAGES:
        per_split = indices.get(language)
        if per_split is None:
            continue
        languages[language] = {
            split: noise_gate(
                [baseline_values[index] for index in per_split.get(split, [])],
                [current_values[index] for index in per_split.get(split, [])],
            )
            for split in ("tuning", "heldout")
        }
    return languages


def leg_language_noise_gates(
    saved_queries: Sequence[SavedQueryRecord],
    baseline_values: Sequence[float],
    current_values: Sequence[float],
) -> dict[str, dict[str, dict[str, GateResult]]]:
    """Per-leg x per-language x split paired gates for the MODEL-01 report.

    Shape ``{leg: {language: {split: GateResult}}}`` in ``("title", "body")``
    then declared ``LANGUAGES`` order. An absent leg x language pair is
    omitted rather than fabricated; a present pair with no records in one
    split carries an ``n=0, sufficient=False`` gate for that split.
    """
    if not (len(saved_queries) == len(baseline_values) == len(current_values)):
        raise ValueError("saved queries and both metric series must have equal lengths")
    indices: dict[tuple[str, str], dict[str, list[int]]] = {}
    for index, record in enumerate(saved_queries):
        if record.leg not in ("title", "body"):
            continue
        per_split = indices.setdefault(
            (record.leg, record.language),
            {"tuning": [], "heldout": []},
        )
        per_split.setdefault(record.split, []).append(index)
    nested: dict[str, dict[str, dict[str, GateResult]]] = {}
    for leg in ("title", "body"):
        for language in LANGUAGES:
            per_split = indices.get((leg, language))
            if per_split is None:
                continue
            nested.setdefault(leg, {})[language] = {
                split: noise_gate(
                    [baseline_values[index] for index in per_split.get(split, [])],
                    [current_values[index] for index in per_split.get(split, [])],
                )
                for split in ("tuning", "heldout")
            }
    return nested


def replay_stability(
    saved_replay: dict[str, Any],
    current_top_k_paths: dict[str, list[str]],
) -> ReplayStability:
    """Replay stability against the saved snapshot (Jaccard@10 + top-1).

    Only queries present on both sides are compared. ``available`` is False
    when the saved run has no replay snapshot or no current top-k exists for
    its queries; a missing side reports the reason instead of inventing a
    number. Sets are compared order-insensitively, so top-1 stability is
    reported alongside the Jaccard means.
    """
    saved_entries = saved_replay.get("queries", [])
    baseline_available = bool(saved_entries)
    if not baseline_available:
        return ReplayStability(
            available=False,
            baseline_available=False,
            num_queries=0,
            jaccard_at_10=0.0,
            top1_stability=0.0,
            note="No saved replay snapshot; stability is unavailable for this comparison.",
        )
    joined = [entry for entry in saved_entries if entry["query"] in current_top_k_paths]
    if not joined:
        return ReplayStability(
            available=False,
            baseline_available=True,
            num_queries=0,
            jaccard_at_10=0.0,
            top1_stability=0.0,
            note="No current replay results for the saved queries; stability is unavailable.",
        )
    jaccards: list[float] = []
    top1: list[float] = []
    for entry in joined:
        saved_paths = list(entry["top_k_paths"])
        current_paths = list(current_top_k_paths[entry["query"]])
        jaccards.append(jaccard(set(saved_paths[:10]), set(current_paths[:10])))
        top1.append(
            1.0
            if saved_paths[:1] and current_paths[:1] and saved_paths[0] == current_paths[0]
            else 0.0
        )
    return ReplayStability(
        available=True,
        baseline_available=True,
        num_queries=len(joined),
        jaccard_at_10=_mean(jaccards),
        top1_stability=_mean(top1),
        note=(
            "Stability against the saved replay snapshot: Jaccard@10 and "
            "top-1 match over the shared queries."
        ),
    )


def require_matching_corpus(
    saved: SavedRun,
    current_metadata: Sequence[DocumentRecord],
) -> str:
    """Return the current fingerprint or refuse a different corpus (T-18-09).

    The saved fingerprint is never trusted as the current value: it is
    recomputed from ALL in-scope current metadata and compared, naming both
    values on mismatch.
    """
    current = corpus_fingerprint(current_metadata)
    if current != saved.corpus["fingerprint"]:
        raise ValueError(
            "Corpus fingerprint mismatch: saved run has "
            f"{saved.corpus['fingerprint']!r}, current index has {current!r}; "
            "refusing to compare different corpora."
        )
    return current


def resolve_saved_targets(
    saved: SavedRun,
    conn: sqlite3.Connection,
) -> list[str]:
    """Resolve every saved target by document id first, then unique path.

    Ids are looked up with a parameterized ``documents`` query; the path
    fallback is used only when exactly one current document has that path.
    Zero or multiple path matches raise a ``ValueError`` naming the path
    instead of guessing (the same file may be indexed in two collections).
    Saved paths are never opened; they are comparison keys only.
    """
    resolved: list[str] = []
    for index, record in enumerate(saved.queries):
        row = conn.execute(
            "SELECT id FROM documents WHERE id = ? LIMIT 1",
            (record.target_doc_id,),
        ).fetchone()
        if row is not None:
            resolved.append(str(row[0]))
            continue
        rows = conn.execute(
            "SELECT id FROM documents WHERE path = ? LIMIT 2",
            (record.target_path,),
        ).fetchall()
        if len(rows) != 1:
            matches = "no current document" if not rows else f"{len(rows)} current documents"
            raise ValueError(
                f"Saved query {index} target is missing from the current index: "
                f"document id {record.target_doc_id!r} was not found and path "
                f"{record.target_path!r} matches {matches}; refusing to guess."
            )
        resolved.append(str(rows[0][0]))
    return resolved


def _dedupe_first(values: Sequence[str]) -> list[str]:
    """Drop repeated values, keeping each first occurrence's rank."""
    seen: set[str] = set()
    unique: list[str] = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        unique.append(value)
    return unique


def _baseline_query_metrics(record: SavedQueryRecord) -> tuple[float, float]:
    """Recompute one baseline nDCG@10/Hit@10 from saved document ids.

    Grading is id-keyed: grade 1 iff a retrieved id equals the record's
    ``target_doc_id``. Repeated ids are deduped by first occurrence, so at
    most one grade-1 hit exists and baseline nDCG@10 can never exceed 1.0.
    Paths never decide a grade.
    """
    grades = [
        1 if doc_id == record.target_doc_id else 0
        for doc_id in _dedupe_first(record.retrieved_doc_ids)
    ]
    return (
        ndcg_at_k(grades, [1], DEFAULT_K),
        hit_at_k(grades, DEFAULT_K),
    )


def compare_saved_run(  # noqa: PLR0913
    saved: SavedRun,
    current_metadata: Sequence[DocumentRecord],
    search_fn: Callable[[str], list[SearchResult]],
    *,
    conn: sqlite3.Connection,
    retrieval: str,
    model: dict[str, Any] | None,
) -> ComparisonReport:
    """Compare a saved run against the current engine, paired by construction.

    Refuses a corpus-fingerprint mismatch; resolves targets by id (unique-path
    fallback); evaluates exactly the saved query set in saved order through
    ``SearchEvaluator.evaluate_per_query``; grades the saved arm through its
    own ``retrieved_doc_ids`` against ``target_doc_id`` (first-occurrence
    dedupe); and reports the seeded paired-bootstrap gate overall, per split,
    per leg, per leg x split, per language, per leg x language, and per
    group. The returned ``current_report``
    is the single ``PersonalReport`` contract ``run_to_saved`` consumes.
    """
    if not saved.queries:
        raise ValueError(
            "Saved run contains no query records; refusing to compare an empty query set."
        )
    fingerprint = require_matching_corpus(saved, current_metadata)
    resolved_ids = resolve_saved_targets(saved, conn)
    queries = [
        SynthesizedQuery(
            query=record.query,
            target_doc_id=resolved_id,
            target_path=record.target_path,
            leg=record.leg,
            language=record.language,
            length_bucket=record.length_bucket,
            split=record.split,
        )
        for record, resolved_id in zip(saved.queries, resolved_ids, strict=True)
    ]
    evaluations = evaluate_known_items(queries, search_fn)
    baseline_pairs = [_baseline_query_metrics(record) for record in saved.queries]
    baseline_ndcg = [pair[0] for pair in baseline_pairs]
    baseline_hit = [pair[1] for pair in baseline_pairs]
    current_ndcg = [evaluation.ndcg_at_10 for evaluation in evaluations]
    current_hit = [evaluation.hit_at_10 for evaluation in evaluations]
    overall = noise_gate(baseline_ndcg, current_ndcg)
    split_indices: dict[str, list[int]] = {"tuning": [], "heldout": []}
    for index, record in enumerate(saved.queries):
        split_indices[record.split].append(index)
    splits = {
        split: noise_gate(
            [baseline_ndcg[index] for index in indices],
            [current_ndcg[index] for index in indices],
        )
        for split, indices in split_indices.items()
    }
    legs, leg_splits = leg_noise_gates(saved.queries, baseline_ndcg, current_ndcg)
    language_splits = language_noise_gates(saved.queries, baseline_ndcg, current_ndcg)
    leg_language_splits = leg_language_noise_gates(
        saved.queries,
        baseline_ndcg,
        current_ndcg,
    )
    groups, suppressed = group_noise_gates(
        saved.queries,
        baseline_ndcg,
        current_ndcg,
    )
    replay_queries = (
        [entry["query"] for entry in saved.replay["queries"]] if saved.replay["available"] else []
    )
    current_replay = replay_leg(replay_queries, search_fn)
    stability = replay_stability(saved.replay, current_replay.top_k_paths)
    current_replay = replace(
        current_replay,
        baseline_available=stability.baseline_available,
    )
    synthesis = SynthesisResult(
        queries=queries,
        rejected_empty={"title": 0, "body": 0},
        rejected_duplicate={"title": 0, "body": 0},
        rejected_overlap={"title": 0, "body": 0},
    )
    current_report = build_personal_report(
        retrieval=retrieval,
        top_k=saved.top_k,
        metadata=current_metadata,
        sampled=(),
        model=model,
        synthesis=synthesis,
        evaluations=evaluations,
        replay=current_replay,
        notes=[
            "Comparison run: the saved query set was re-evaluated in saved "
            "order with no synthesis, overlap filtering, or split reassignment."
        ],
        corpus=CorpusSummary(
            documents=len(current_metadata),
            sampled=saved.corpus["sampled"],
            fingerprint=fingerprint,
            widened=False,
        ),
    )
    return ComparisonReport(
        current_report=current_report,
        baseline_metrics={
            "ndcg_at_10": _mean(baseline_ndcg),
            "hit_at_10": _mean(baseline_hit),
            "num_queries": len(baseline_ndcg),
        },
        current_metrics={
            "ndcg_at_10": _mean(current_ndcg),
            "hit_at_10": _mean(current_hit),
            "num_queries": len(current_ndcg),
        },
        overall=overall,
        splits=splits,
        legs=legs,
        leg_splits=leg_splits,
        language_splits=language_splits,
        leg_language_splits=leg_language_splits,
        groups=groups,
        suppressed=suppressed,
        replay=stability,
        retrieval={"saved": saved.retrieval, "current": retrieval},
        top_k=saved.top_k,
        # Only the held-out summary gate can warrant a defaults change; the
        # tuning and per-group gates are diagnostic (D-07, T-18-10).
        warrants_default_change=splits["heldout"].winner,
        model_mismatch=(saved.model != model),
    )
