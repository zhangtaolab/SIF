---
phase: "19"
slug: "search-correctness"
status: verified
# threats_open = count of OPEN threats at or above workflow.security_block_on severity (the blocking gate)
threats_open: 0
asvs_level: 1
created: "2026-11-18"
verified: "2026-11-25"
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
| T-19-09 | Tampering | saved-run baseline integrity (B0) | medium | mitigate | `personal_bench.py:84,1597,1693` rejects `content`/`snippet`; envelope validation `:1714-1805`; fingerprint over path/checksum/size `:1226-1235` | closed |
| T-19-10 | Tampering | BM25/vector SQL | high | mitigate | Weights, threshold, limit, offset bound as parameters (`bm25.py:87,96-97,164`); `IntRange(min=0)` / `Field(ge=0)` reject negatives | closed |
| T-19-11 | Denial of Service | vector `fetch_k` / huge offset | medium | mitigate | `_MAX_FETCH_K = 2048` (`vector.py:25`); bounded seed `:197`; past-end offset returns an empty page | closed |
| T-19-12 | Repudiation | rank numbering and page continuity | medium | mitigate | Global ranks `offset + position` in every path (`bm25.py:181`, `vector.py:251`, `hybrid.py:55-67,484`); continuity tests | closed |
| T-19-13 | Denial of Service | `VectorSearcher` fetch_k escalation | medium | mitigate | Doubles only while the batch is exactly `fetch_k` and target unmet, clamped at `_MAX_FETCH_K` (`vector.py:204-231`); ceiling tests | closed |
| T-19-14 | Tampering | chunk identity metadata at fusion | medium | mitigate | RRF adopts only non-null `chunk_id`/`sequence`, `max(chunk_matches)` (`rrf.py:36-47,127-128`); best-distance winner (`vector.py:296-322`) | closed |
| T-19-15 | Information Disclosure | per-chunk fields in CLI/MCP output | low | accept | `SearchResult.chunk_id/.sequence/.chunk_matches` are index-local identity/count metadata; no content or new path | closed |
| T-19-16 | Tampering | MCP schema / re-map | high | mitigate | Fixed six-key re-map (`backend.py:190-197`) with exact-set assertions; published schema derived from the tool signature (Phase 22 successor, `tools.py`), drift structurally impossible; wire goldens | closed |
| T-19-17 | Repudiation | B0/B1 comparison evidence | medium | mitigate | Fingerprint never trusted as current (`personal_bench.py:2184-2201`); `compare_saved_run` grades only the saved set `:2270-2294` | closed |
| T-19-18 | Tampering | title-FTS rebuild / `documents_fts_v` | high | mitigate | Column-list detection from `sqlite_master` (`schema.py:497-503`); savepoint `:519`; vocab dropped before FTS, triggers dropped explicitly, exactly one `VALUES('rebuild')` `:529-574`; idempotence tests | closed |
| T-19-19 | Tampering | weighted `bm25()` SQL | high | mitigate | Weights and `min_score` appended to bound params (`bm25.py:84-97,122-164`); both branches `bm25(documents_fts, ?, ?)`; `1.0/1.0 == rank` pinned | closed |
| T-19-20 | Denial of Service | `create_all` on a populated database | low | accept | One-time rebuild gated by one `sqlite_master` read; atomic via savepoint | closed |
| T-19-21 | Tampering | MCP-only schema startup | high | mitigate | `SearchBackend.__init__` runs `init_schema` with its own dimension (`backend.py:274-295`); supplied dimension never consults `get_settings()` (`database.py:37-60`) | closed |
| T-19-22 | Repudiation | D-12 title-weight verdict | high | mitigate | Per-leg and per-leg×split noise gates (`personal_bench.py:487-499,2015-2048`); verdict artifact carries full `GateResult`; `bench/d12-verdict.json` (decision `rejected`, pinned 1.0) | closed |
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
| 2026-11-25 | 24 | 24 | 0 | ZCode (gsd-secure-phase 19, ASVS L1, block_on high; short-circuit, auditor not spawned — all 24 rows re-verified at HEAD `2808c67`; line references refreshed in T-19-09, T-19-17, T-19-22; no status change) |

---

## Sign-Off

- [x] All threats have a disposition (mitigate / accept / transfer)
- [x] Accepted risks documented in Accepted Risks Log
- [x] `threats_open: 0` confirmed
- [x] `status: verified` set in frontmatter

**Approval:** verified 2026-11-18 — 24/24 threats closed at L1; 0 open at or above `high`.

**Re-verification:** verified 2026-11-25 — 24/24 threats closed at L1; 0 open at or above `high` (delta re-audit at HEAD `2808c67`; no status change; line references refreshed in T-19-09, T-19-17, T-19-22).

## Security Audit 2026-11-25

| Metric | Count |
|---|---|
| Threats found | 24 |
| Closed | 24 |
| Open | 0 |

### Re-audit notes (2026-11-25, HEAD `2808c67`)

- **Scope.** State A re-audit of the existing register against the tree after `b817ebb`, the
  last commit that touched this file. Depth L1, `block_on: high`, ASVS level 1. The register is
  authored at plan time (all nine PLANs carry STRIDE `<threat_model>` blocks) and `threats_open`
  was 0, so the workflow short-circuit applied: Steps 4 and 5 were skipped and
  `gsd-security-auditor` was not spawned. This runtime has no Agent tool either. The orchestrator
  classified every row, and all 24 were read at HEAD rather than only the delta rows. No SUMMARY
  file carries a `## Threat Flags` heading or any threat text, so there are no unregistered flags.
- **Delta outside `.planning/`, `b817ebb..HEAD`: 59 files.** Of the 19 files a mitigation cell
  cites, 17 are byte-identical to `b817ebb`: all 16 under `src/`, and `bench/d12-verdict.json`.
  The two that changed are both cited by `T-19-SC`:
  - `pyproject.toml`: only the two torch extras floors, `"torch"` to `"torch>=2.11"` (`embed`,
    `all`). Two commits produced this: `a13b134c` raised the floor to `>=2.14`, then `848e6b6a`
    lowered it to `>=2.11`.
  - `uv.lock`: 23 lines removed, 23 added. Four are torch `requires-dist` entries gaining
    `specifier = ">=2.11"`; the other 19 are `resolution-markers` strings reordered inside
    package blocks, the same strings on both sides. No line touching a package name, version,
    sdist, wheel, URL, hash or index changed, and the name@version multiset is the same on both
    sides. No commit tagged for this phase touched either file, from the first task commit
    `5b964e18` through `e137ca04`, the four `fix(19)` review fixes included.
  - **`T-19-SC` holds.** A floor on an already-locked optional dependency adds no package,
    version, source or index.
- **Cited tests.** No mitigation cell names a test file by path. Where a cell names tests by
  description, the deciding tests were located. Those in files changed by `c95d2cee` (Windows
  portability):
  - `tests/unit/cli/test_search.py` (+6/-2): `TestSingleEnrichmentOwner` (T-19-08) is untouched.
    The commit relaxes two title-cell literals in `TestSearchOutputBranches`, Phase 10 tests that
    no row cites.
  - `tests/unit/mcp/test_backend.py` (+3/-3): `TestSingleEnrichmentOwner`, the exact-set re-map
    assertions (T-19-16, `:884`, `:905`), the input-model tests (`:923-933`) and
    `TestSchemaInitializationAtStartup` (T-19-21) are untouched; `symlink_or_skip` replaces
    `os.symlink` in two document-get alias tests (`test_get_document_alias_path_normalized`,
    `test_get_documents_by_pattern_alias_prefix`). Net line shift 0.
  - `tests/unit/search/test_context_attach.py` (+7/-1): the `alias_pair` fixture goes through
    `symlink_or_skip`; a `win32` skipif on the un-expandable-tilde test.
  - `tests/unit/database/test_repositories.py` (+3/-1): the `alias_pair` fixture goes through
    `symlink_or_skip`; a `tzset` skipif on an LLM-cache expiry test.
    `TestDocumentMetadataCanonicalStorage` (T-19-01) takes only `db` and is untouched.
  - `symlink_or_skip` still calls `symlink_to` and skips only on `NotImplementedError` or
    `OSError`, so on a host that can create a symlink every one of these tests runs as before.
    On a host that cannot (Windows without Developer Mode or elevation) they now skip instead of
    failing. That covers ten tests in `test_context_attach.py`, seven of them in
    `TestAttachPathContextsRealSQL` behind T-19-07. T-19-07's mitigation is product code
    (`context_attach.py:51-53`, `:110`, `:311`) and is unchanged. CI runs only `ubuntu-latest`
    and `macos-latest` (`.github/workflows/test-matrix.yml:23`), so no CI cell exercises that
    skip path.
  - `tests/unit/search/test_rerank.py` (+76, `f8ff9bea`): `TestRebuildChunkIdentity`, three
    tests pinning that `_sort_and_build_results` (`src/sif/search/rerank.py:24`) keeps
    `chunk_id`, `sequence` and `chunk_matches` through the sort (CORR-02). Additive: the 15
    earlier tests are unchanged. `src/sif/search/rerank.py` differs from `b817ebb` by one hunk
    in `create_reranker` (`:436-438`, the cache path gains `models`; `5f9c0869`) and is
    byte-identical to `fee02316`. No mitigation cell cites that file.
- **Line references.** Every cited range was read at HEAD. Seventeen of the 20 mitigate rows
  that carry one resolve exactly as written. Three did not, all in
  `src/sif/search/personal_bench.py`, and all for one reason outside `b817ebb..HEAD`:
  `618997c1` (2026-11-18 18:33) inserted 17 lines at line 599 after these references were taken
  and before this file was committed at `b817ebb` (20:02). The file is byte-identical to
  `b817ebb`. Each mitigation was re-read at its new range and holds; only the numbers changed.
  - `T-19-09`: `:1580` to `:1597`, `:1676` to `:1693`, `:1697-1790` to `:1714-1805`,
    `:1209-1217` to `:1226-1235`.
  - `T-19-17`: `:2160-2183` to `:2184-2201` (`require_matching_corpus`), `:2253-2277` to
    `:2270-2294`.
  - `T-19-22`: `:1998-2031` to `:2015-2048` (`leg_noise_gates`).
- **Result.** 24/24 closed, 0 open, 0 open below the `high` threshold. **The delta invalidates
  nothing.** No row changed status or ID and no row was added. No accepted risk was added.
- **Evidence.** `pytest` from PATH (9.1.1), 0 failed. The 20 test files the validation map
  cites: 1000 passed in 21.72 s. Per-threat classes: `TestDocumentMetadataCanonicalStorage` 2,
  `TestAttachPathContextsRealSQL` 10, `TestSingleEnrichmentOwner` 3 (CLI), `test_staleness.py`
  20, `TestRebuildChunkIdentity` 3, `TestSchemaInitializationAtStartup` 5, the three
  dimension-injection tests in `test_schema.py` 3, `TestPerLegNoiseGates` 4,
  `TestSavedRunContract` 7, `TestCorpusFingerprint` 2, `TestCompareSavedRun` 13,
  `TestSavedRunsCli` 6, title-weight pins 3. Artifact shape: `bench/d12-verdict.json` is
  `decision: rejected` at `pinned_title_weight: 1.0` with candidates 2.0/3.0/4.0, and
  `bench/b0.json` holds 100 query records under fingerprint `8c006123784348d1` with no `content`
  or `snippet` key. GitHub Actions Test Matrix run `45522236981` on `a25eb07` is green on 8/8
  cells plus lint; `a25eb07..HEAD` differs only under `.planning/` and in
  `tests/unit/search/test_rerank.py`. Its `Type check` step is not counted as evidence. Full
  suite at HEAD, run without coverage: 3263 passed, 1 skipped in 121.47 s.
- **Recorded, not re-triaged.**
  - The header names `763753d` as the verified HEAD. The references in this register were not
    read from that tree: at `763753d` several cited ranges are past end of file, and
    `src/sif/mcp/tools.py` (cited by `T-19-16`) does not exist. They match `618997c1^` exactly.
    The header is left as written.
  - The closing phrase of `T-19-16`'s cell, "wire goldens", names no file, and no test was tied
    to it with confidence. It is left as written; the exact-set re-map assertions in the same
    cell were verified.
  - Threat Ref reconciliation against the 2026-11-25 validation map. `19-VALIDATION.md` was not
    edited by this audit; this is a report for the validate-phase owner, and none of it changes
    a row here.
    - `T-19-21` (MCP-only schema startup): the move off the mtime-index row is correct. It is now
      cited by "19-09 T1 (MCP startup)", whose command runs
      `tests/unit/mcp/test_backend.py::TestSchemaInitializationAtStartup` (5 tests), which
      decides the `backend.py:274-295` half. The stated ground is incomplete, though: the
      `database.py:37-60` half (a supplied dimension never consults `get_settings()`) is decided
      by `TestDatabaseInitSchemaDimension` (`tests/unit/database/test_schema.py:1372`, `:1389`),
      and those two tests run under the mtime-index row's command and under no row that cites
      `T-19-21`. Optional tightening: add `tests/unit/database/test_schema.py` to the MCP-startup
      row's command.
    - `T-19-22` (D-12 verdict): correct. Decided by `TestPerLegNoiseGates` (4 tests) and
      `tests/unit/cli/test_eval.py`, plus the recorded `bench/d12-verdict.json`; nothing in
      `test_schema.py` touches it. Now cited by "19-09 T2", whose command runs both files.
    - `T-19-09` (B0 saved-run integrity): the removal is right, the result is not. The old CORR-05
      row never decided it (`test_staleness.py` and `test_context_attach.py` hold no saved-run
      test; the ID rode on a plan-level `19-04` tag). But no row now cites a `mitigate` threat,
      and the recorded ground "no map command targets it" is inaccurate: the "19-09 T2" command
      already runs `TestSavedRunContract`, `TestCorpusFingerprint`, `TestCompareSavedRun` and
      `TestSavedRunsCli`, 28 green tests. Suggested repair: add a row "19-04 T1 (B0 saved run)"
      (plan 19-04, wave 4, CORR-05, T-19-09) citing that command. Not a security gap: the
      mitigation is present and tested.
    - `T-19-23` (title-weight surface; not part of the change): cited by no row before or after.
      Its three pins sit in `tests/unit/search/test_bm25.py` and run under "19-05 T1" and
      "19-08 T2"; the latter's stated behavior includes the constant pin. Adding `T-19-23` to
      that row's Threat Ref would close it.
