---
phase: "19"
slug: "search-correctness"
status: verified
# threats_open = count of OPEN threats at or above workflow.security_block_on severity (the blocking gate)
threats_open: 0
asvs_level: 1
created: "2026-11-18"
verified: "2026-11-18"
---

# Phase 19 — Security

> Per-phase security contract: threat register, accepted risks, and audit trail.
> Verified by /gsd-secure-phase 19 on 2026-11-18 at HEAD `763753d` (ASVS L1, block_on high).
> Register authored at plan time: all nine PLANs carry STRIDE `<threat_model>` blocks. L1
> grep-depth verification confirmed every mitigation present; `threats_open: 0`.

---

## Trust Boundaries

| Boundary | Description | Data Crossing |
|----------|-------------|---------------|
| user file content → parser → canonical metadata JSON → SQLite | Untrusted frontmatter keys and typed values cross into hash input and persisted JSON | Titles, metadata keys/values, checksums |
| persisted convention marker → index-writing pass | A missing, stale, or forged marker decides whether every document is re-parsed | Collection id, convention version |
| watcher event path → embed leg | Watch events select documents for chunk/vector writes | Paths, reindexed path set |
| indexing progress callback → CLI/watch/MCP hosts | The migrate notice crosses the presentation-free event protocol | Event text, document counts |
| persisted contexts/staleness signals → search results | Trust markers consumed by CLI/MCP renderers and agents | Context descriptions, staleness booleans |
| pipeline exit paths → enrichment helper | Every return path must pass through the same composition | Result list identity |
| CLI flags / MCP request fields → SQL LIMIT/OFFSET | User-controlled pagination values reach SQLite | Integers (offset/limit), booleans |
| MCP input schema → Pydantic model | Two hand-maintained schemas must agree | Field names, types, defaults |
| vec0 KNN rows → result rows | Duplicate chunk rows are collapsed and identity metadata is selected | Chunk id, sequence, match counts |
| vector/BM25 lists → RRF → API results | Fusion keys and metadata merging decide what clients see | Document ids, chunk identity |
| sqlite_master FTS SQL → migration gate | Stored DDL decides whether the index is rebuilt | Table DDL text |
| document rows → FTS triggers | Title and content values cross into the external-content index | Titles, body text |
| title-weight parameters → SQL | Internal constants are bound into the BM25 expression | Numeric weights |
| MCP-only process startup → schema | A host that never runs a CLI command must still migrate | Embedding dimension, DDL |
| saved run → comparison gate | Baseline artifacts and query sets decide a defaults claim | Paths, checksums, ids, metrics |
| internal weight override → shipped constant | A measurement knob must not become a user-facing configuration surface | None (internal only) |

---

## Threat Register

| Threat ID | Category | Component | Severity | Disposition | Mitigation | Status |
|-----------|----------|-----------|----------|-------------|------------|--------|
| T-19-01 | Tampering | `canonical_metadata_json` / `documents.metadata` | medium | mitigate | `src/sif/core/models.py:19-72` recursive key coercion; canonical string bound as a SQL parameter (`repositories.py:192,274`); nested-mixed-key/typed-value tests | closed |
| T-19-02 | Denial of Service | parser selection | low | mitigate | `incremental.py:393` extension dispatch with `TextParser` fallback; `parser.py:99-126` bounded whole-file read | closed |
| T-19-03 | Tampering | `index_meta` convention marker | medium | mitigate | Per-collection `convention:<id>` key; marker written only when stored-document failures are zero (`incremental.py:155-160,210-212`); failure-path tests | closed |
| T-19-04 | Repudiation | metadata fast path | high | mitigate | Fast path only on exact stored-content equality (`incremental.py:437-446`); body change purges chunks/embeddings (`:456-458`); watcher embed set from `reindexed_paths` (`watcher.py:904-907`); count regressions | closed |
| T-19-05 | Denial of Service | forced migration on a large collection | low | accept | Per-file short transactions, resumable marker discipline, notice names the scanned count | closed |
| T-19-06 | Repudiation | context/staleness markers across exit paths | high | mitigate | One `enrich_results` composition (`context_attach.py:317-346`) called once per pipeline exit (`hybrid.py:352-379,484`); spy + marker-parity tests | closed |
| T-19-07 | Tampering | context matching via `normalize_path` | low | mitigate | Constant SQL, no interpolated path (`context_attach.py:51-53`); two-sided normalization (`:110,311`) | closed |
| T-19-08 | Repudiation | CLI/MCP enrichment ownership | high | mitigate | Exactly one enrichment in `search.py:613,871-874`; MCP fallback enriches, pipeline does not (`backend.py:490-678`); exact-set spy tests | closed |
| T-19-09 | Tampering | saved-run baseline integrity (B0) | medium | mitigate | `personal_bench.py:84,1580,1676` rejects `content`/`snippet`; envelope validation `:1697-1790`; fingerprint over path/checksum/size `:1209-1217` | closed |
| T-19-10 | Tampering | BM25/vector SQL | high | mitigate | Weights, threshold, limit, offset bound as parameters (`bm25.py:87,96-97,164`); `IntRange(min=0)` / `Field(ge=0)` reject negatives | closed |
| T-19-11 | Denial of Service | vector `fetch_k` / huge offset | medium | mitigate | `_MAX_FETCH_K = 2048` (`vector.py:25`); bounded seed `:197`; past-end offset returns an empty page | closed |
| T-19-12 | Repudiation | rank numbering and page continuity | medium | mitigate | Global ranks `offset + position` in every path (`bm25.py:181`, `vector.py:251`, `hybrid.py:55-67,484`); continuity tests | closed |
| T-19-13 | Denial of Service | `VectorSearcher` fetch_k escalation | medium | mitigate | Doubles only while the batch is exactly `fetch_k` and target unmet, clamped at `_MAX_FETCH_K` (`vector.py:204-231`); ceiling tests | closed |
| T-19-14 | Tampering | chunk identity metadata at fusion | medium | mitigate | RRF adopts only non-null `chunk_id`/`sequence`, `max(chunk_matches)` (`rrf.py:36-47,127-128`); best-distance winner (`vector.py:296-322`) | closed |
| T-19-15 | Information Disclosure | per-chunk fields in CLI/MCP output | low | accept | `SearchResult.chunk_id/.sequence/.chunk_matches` are index-local identity/count metadata; no content or new path | closed |
| T-19-16 | Tampering | MCP schema / re-map | high | mitigate | Fixed six-key re-map (`backend.py:190-197`) with exact-set assertions; published schema derived from the tool signature (Phase 22 successor, `tools.py`), drift structurally impossible; wire goldens | closed |
| T-19-17 | Repudiation | B0/B1 comparison evidence | medium | mitigate | Fingerprint never trusted as current (`personal_bench.py:2160-2183`); `compare_saved_run` grades only the saved set `:2253-2277` | closed |
| T-19-18 | Tampering | title-FTS rebuild / `documents_fts_v` | high | mitigate | Column-list detection from `sqlite_master` (`schema.py:497-503`); savepoint `:519`; vocab dropped before FTS, triggers dropped explicitly, exactly one `VALUES('rebuild')` `:529-574`; idempotence tests | closed |
| T-19-19 | Tampering | weighted `bm25()` SQL | high | mitigate | Weights and `min_score` appended to bound params (`bm25.py:84-97,122-164`); both branches `bm25(documents_fts, ?, ?)`; `1.0/1.0 == rank` pinned | closed |
| T-19-20 | Denial of Service | `create_all` on a populated database | low | accept | One-time rebuild gated by one `sqlite_master` read; atomic via savepoint | closed |
| T-19-21 | Tampering | MCP-only schema startup | high | mitigate | `SearchBackend.__init__` runs `init_schema` with its own dimension (`backend.py:274-295`); supplied dimension never consults `get_settings()` (`database.py:37-60`) | closed |
| T-19-22 | Repudiation | D-12 title-weight verdict | high | mitigate | Per-leg and per-leg×split noise gates (`personal_bench.py:487-499,1998-2031`); verdict artifact carries full `GateResult`; `bench/d12-verdict.json` (decision `rejected`, pinned 1.0) | closed |
| T-19-23 | Elevation of Privilege | title-weight configuration surface | medium | mitigate | `SearchOptions.title_weight` internal only (`models.py:373-377`); `_TITLE_WEIGHT` module constant (`bm25.py:24-25`); zero CLI/config/docs surface; pinned-value test | closed |
| T-19-SC | Tampering | npm/pip/cargo installs | high | mitigate | No package install in this phase; `pyproject.toml`/`uv.lock` unchanged across the phase commit range | closed |

*Status: open · closed · open — below high threshold (non-blocking)*
*Severity: critical > high > medium > low — only open threats at or above workflow.security_block_on count toward threats_open*
*Disposition: mitigate (implementation required) · accept (documented risk) · transfer (third-party)*

---

## Accepted Risks Log

| Risk ID | Threat Ref | Rationale | Accepted By | Date |
|---------|------------|-----------|-------------|------|
| AR-19-01 | T-19-05 | One-pass forced migration on a large collection: per-file short transactions, resumable marker discipline, notice names the scanned count. | Plan-time risk register (19-02-PLAN.md) | 2026-11-18 |
| AR-19-02 | T-19-15 | Per-chunk fields (`chunk_id`, `sequence`, `chunk_matches`) appear in CLI/MCP output: index-local identity/count metadata, no content or new path disclosure. | Plan-time risk register (19-06-PLAN.md) | 2026-11-18 |
| AR-19-03 | T-19-20 | One-time `create_all` rebuild on a populated database, gated by a `sqlite_master` read; bounded by index size and made atomic by the savepoint. | Plan-time risk register (19-08-PLAN.md) | 2026-11-18 |

*Accepted risks do not resurface in future audit runs.*

---

## Security Audit Trail

| Audit Date | Threats Total | Closed | Open | Run By |
|------------|---------------|--------|------|--------|
| 2026-11-18 | 24 | 24 | 0 | /gsd-secure-phase 19 (gsd-security-auditor, ASVS L1) |

---

## Sign-Off

- [x] All threats have a disposition (mitigate / accept / transfer)
- [x] Accepted risks documented in Accepted Risks Log
- [x] `threats_open: 0` confirmed
- [x] `status: verified` set in frontmatter

**Approval:** verified 2026-11-18 — 24/24 threats closed at L1; 0 open at or above `high`.
