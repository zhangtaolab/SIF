"""Personal-corpus benchmark synthesis and deterministic sampling (Phase 18, EVAL-01/02).

Pure domain module: no Click or Rich imports. Every stage is deterministic —
normalization is NFC + casefold + whitespace collapse, sampling and
fingerprinting use ``hashlib.sha256`` (never Python's salted builtin hash),
and outputs are ordered by explicit sort keys so the same index yields the
same query set on every machine (research Pitfall 9).

Privacy (EVAL-01): the whole-corpus pass reads metadata columns only
(``id, path, title, checksum, file_size``); document bodies are loaded solely
for the bounded sampled subset (``load_sampled_content``), and nothing here
uploads or serializes document content.

Bias controls (EVAL-02): the title leg is exact-term and unbudgeted, the body
leg rejects candidates whose token Jaccard against the target's title plus
opening text exceeds ``OVERLAP_BUDGET``, and every rejected candidate is
counted per leg — a query set never shrinks silently (research Pitfall 1).
"""

from __future__ import annotations

import hashlib
import re
import sqlite3
import unicodedata
from collections.abc import Callable, Sequence
from dataclasses import dataclass, replace
from typing import Any

from sif.core.models import SearchResult
from sif.search.benchmark import QueryEvaluation, SearchEvaluator


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
        """Serialize with a fixed key order and no document content."""
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
    rejects (exactly 0.60 is accepted). Title queries are exact-term and stay
    unbudgeted, replay is never synthesized, and every rejection is counted
    per leg.
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
        target_tokens = token_set(f"{title} {opening}")
        if jaccard(token_set(query.query), target_tokens) > OVERLAP_BUDGET:
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


def ensure_heldout(
    metadata: Sequence[DocumentRecord],
    conn: sqlite3.Connection,
    *,
    initial: int = INITIAL_SAMPLE_DOCUMENTS,
    cap: int = MAX_SAMPLE_DOCUMENTS,
) -> tuple[list[DocumentRecord], SynthesisResult]:
    """Sample, synthesize, split, and widen until both floors are met (D-06).

    Starts from the first ``initial`` documents in deterministic sample order
    (strictly smaller than the cap whenever the corpus has more documents),
    loads bodies only for that slice, and while accepted queries are below
    ``MIN_QUERIES`` or held-out queries below ``HELDOUT_MIN`` doubles the
    limit toward ``min(len(metadata), cap)``. A widened sample is a superset
    of the previous prefix, so bodies load only for the newly added
    documents. Only a floor still unmet at the cap raises a counted
    ``ValueError`` naming accepted, tuning, held-out, and rejection counts.
    """
    if not metadata:
        raise ValueError(
            "Personal eval needs indexed documents; found 0. "
            "Index documents with 'sif index update' and retry."
        )
    hard_cap = min(len(metadata), cap)
    limit = max(1, min(initial, hard_cap))
    sampled = sample_documents(metadata, limit=limit)
    contents = load_sampled_content(conn, [doc.id for doc in sampled])
    docs = [replace(doc, content=contents.get(doc.id, "")) for doc in sampled]
    synthesis = _synthesize_and_split(docs)
    accepted = synthesis.queries
    heldout = sum(1 for query in accepted if query.split == "heldout")
    while (len(accepted) < MIN_QUERIES or heldout < HELDOUT_MIN) and limit < hard_cap:
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
    if len(accepted) < MIN_QUERIES or heldout < HELDOUT_MIN:
        tuning = len(accepted) - heldout
        empty = sum(synthesis.rejected_empty.values())
        duplicate = sum(synthesis.rejected_duplicate.values())
        overlap = sum(synthesis.rejected_overlap.values())
        raise ValueError(
            f"Personal eval needs at least {MIN_QUERIES} accepted queries with "
            f"{HELDOUT_MIN} held out; accepted {len(accepted)} "
            f"(tuning {tuning}, held-out {heldout}) from {len(sampled)} sampled "
            f"documents; rejected {empty + duplicate + overlap} "
            f"({empty} empty, {duplicate} duplicate, {overlap} overlap). "
            "Index more documents with 'sif index update' and retry."
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
) -> PersonalReport:
    """Assemble the one report contract from synthesis + per-query evaluation.

    Metrics, splits, groups, and records are computed exactly once here; the
    CLI renders ``to_dict()`` and never recomputes a field. Known-item
    metrics are means over title+body records only — replay never enters.
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
    corpus = CorpusSummary(
        documents=len(metadata),
        sampled=len(sampled),
        fingerprint=corpus_fingerprint(metadata),
        widened=len(sampled) > INITIAL_SAMPLE_DOCUMENTS,
    )
    return PersonalReport(
        retrieval=retrieval,
        top_k=top_k,
        corpus=corpus,
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
