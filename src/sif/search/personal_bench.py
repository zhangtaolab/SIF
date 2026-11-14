"""Personal-corpus benchmark synthesis and deterministic sampling (Phase 18, EVAL-01).

Pure domain module: no Click or Rich imports. Every stage is deterministic —
normalization is NFC + casefold + whitespace collapse, sampling and
fingerprinting use ``hashlib.sha256`` (never the salted builtin ``hash()``),
and outputs are ordered by explicit sort keys so the same index yields the
same query set on every machine (research Pitfall 9).

Privacy (EVAL-01): the whole-corpus pass reads metadata columns only
(``id, path, title, checksum, file_size``); document bodies are never loaded
by the title leg, and nothing here uploads or serializes document content.
"""

from __future__ import annotations

import hashlib
import sqlite3
import unicodedata
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Any

from sif.core.models import SearchResult
from sif.search.benchmark import QueryEvaluation, SearchEvaluator


# Declared leg order (D-01). This plan implements the title leg; the body and
# replay legs (18-02/18-03) extend the same report vocabulary.
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
HELDOUT_MIN = 25
SUPPRESS_BELOW = 10
OVERLAP_BUDGET = 0.60
RUN_SCHEMA_VERSION = 1
BOOTSTRAP_RESAMPLES = 10_000


@dataclass(frozen=True)
class DocumentRecord:
    """One in-scope document's metadata (bodies never join the whole pass).

    ``content`` is transient: it stays ``None`` for the metadata-only corpus
    scan and is populated solely for the bounded sampled subset by later
    plans' body leg (T-18-02).
    """

    id: str
    path: str
    title: str
    checksum: str
    file_size: int
    content: str | None = None


@dataclass(frozen=True)
class SynthesizedQuery:
    """One known-item query: the query text plus its single grade-1 target."""

    query: str
    target_doc_id: str
    target_path: str
    leg: str


@dataclass(frozen=True)
class SynthesisResult:
    """Accepted queries plus the rejection tally — never a silent shrink.

    Every rejected title candidate (empty after trimming, or a normalized
    duplicate of an earlier accepted query) is counted here so the CLI can
    report it (EVAL-01 transparency rule).
    """

    queries: list[SynthesizedQuery]
    rejected_empty: int
    rejected_duplicate: int


def normalize_text(text: str) -> str:
    """NFC-normalize, casefold, and collapse whitespace to single spaces.

    The shared normalization for query dedupe and later hash splitting; it
    makes the "same" query hash and compare identically across platforms,
    including macOS NFD input (research Pitfall 9).
    """
    return " ".join(unicodedata.normalize("NFC", text).casefold().split())


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
) -> tuple[list[SynthesizedQuery], int]:
    """Keep the first query per normalized text; count later collisions.

    Queries arrive in deterministic sampled-document order, so the kept
    record is stable. A duplicate is counted, never dropped silently.
    """
    seen: set[str] = set()
    kept: list[SynthesizedQuery] = []
    rejected_duplicate = 0
    for query in queries:
        key = normalize_text(query.query)
        if key in seen:
            rejected_duplicate += 1
            continue
        seen.add(key)
        kept.append(query)
    return kept, rejected_duplicate


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
        candidates.append(
            SynthesizedQuery(
                query=title,
                target_doc_id=doc.id,
                target_path=doc.path,
                leg="title",
            )
        )
    queries, rejected_duplicate = dedupe_queries(candidates)
    return SynthesisResult(
        queries=queries,
        rejected_empty=rejected_empty,
        rejected_duplicate=rejected_duplicate,
    )


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

    The message carries accepted and rejected counts (with the empty-title /
    duplicate split) and the index remedy; the CLI translates it to a
    ``ClickException`` so a too-small corpus fails loudly (D-11).
    """
    accepted = len(synthesis.queries)
    if accepted >= MIN_QUERIES:
        return
    rejected = synthesis.rejected_empty + synthesis.rejected_duplicate
    raise ValueError(
        f"Personal eval needs at least {MIN_QUERIES} accepted queries; "
        f"accepted {accepted}, rejected {rejected} "
        f"({synthesis.rejected_empty} empty title, "
        f"{synthesis.rejected_duplicate} duplicate). "
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
