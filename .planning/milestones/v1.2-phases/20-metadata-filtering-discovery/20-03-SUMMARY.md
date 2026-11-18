---
phase: 20-metadata-filtering-discovery
plan: "03"
subsystem: search
tags: [sqlite-vec, knn, metadata-filter, hybrid-search, integration-tests]

# Dependency graph
requires:
  - phase: 19-search-correctness
    provides: "single offset slice, global ranks, one attach at pipeline exit, idx_documents_mtime, post-JOIN collection filter"
  - phase: 20-metadata-filtering-discovery
    plan: "01"
    provides: "compile_filter + count_matching_documents/count_documents_in_scope/count_vectors_in_scope, SearchOptions.filter"
  - phase: 20-metadata-filtering-discovery
    plan: "02"
    provides: "fully backfilled typed kv store with qmd.metadata resolution and skip accounting"
provides:
  - "Corrected vector-leg escalation whenever any JOIN filter is present (collection-only included): pre-count, selectivity seeding, distinct-document all-matches stop, empty-match sentinel"
  - "_TOO_SELECTIVE_MSG D-09 notice (three %d placeholders), emitted once on stderr for metadata filters only"
  - "HybridSearcher.search / SearchPipeline.search filter-contract docstrings (pre-RRF, early-return windows, per-chunk chunk_matches)"
  - "tests/integration/test_metadata_filtering.py: containment, admit-all equivalence, 2 % recall, composition, typed exactness, injection, skipped-key, notice/stdout"
affects: [20-04, 20-05, 22]

# Actuals (#2632) — chars/4 over the realized diff, same scale as the plan estimate.
actuals:
  tokens: 13597
  tasks: 3
  commits: 3

# Measured commit ledger (#3968) — base recorded before the first task commit.
plan_head_before: 818d337d2170568e15b0ea809125537150942547
plan_head_after: 3858eeb94f7261ded8721bed55443d652ff7efd4

tech-stack:
  added: []
  patterns:
    - "Two-path escalation: byte-identical unfiltered branch; pre-counted JOIN-filtered branch"
    - "Distinct-document all-matches signal from RAW KNN rows (min_score and chunk dedup cannot end escalation early)"
    - "Global vector count for the 'whole table scanned' stop; scope count only seeds selectivity"
    - "D-09 notice precondition as an exact four-clause guard (metadata filter, enough matches, ceiling, short page)"

key-files:
  created:
    - tests/integration/test_metadata_filtering.py
  modified:
    - src/sif/search/vector.py
    - src/sif/search/hybrid.py
    - tests/unit/search/test_vector.py
    - tests/unit/search/test_hybrid.py

key-decisions:
  - "The 'whole table scanned' stop compares fetch_k to the GLOBAL vector count, not the scoped count: a scoped count is far below the KNN depth needed to reach a selective collection's rows and would end escalation on batch one (breaking the plan's own measured-bug regression)."
  - "The post-KNN filter suffix is AND-prefixed (` AND {clause}`), mirroring the 20-01 BM25 fix; the empty suffix keeps the unfiltered/unscoped statement bytes identical."
  - "Collection-only searches use count_documents_in_scope as both pre_count and the all-matches target, and are structurally incapable of emitting the D-09 metadata notice."
  - "The integration corpus spans two collections (c1 notes, c2 archive) instead of one so D-17's filter x collection composition is exercised by AND rather than tautology."
  - "Integration documents go through DocumentRepository.create so typed rows are written by the production path; chunks/embeddings remain direct inserts (Pitfall 10 satisfied on the metadata side)."

patterns-established:
  - "Filtered-path tests assert both the positive recall case and the suppressed-notice case for every warning branch"
  - "Mocked collection-filter tests answer scoped COUNT(*) queries separately from the KNN statement"

requirements-completed: [FILT-02, FILT-03]

coverage:
  - id: D1
    description: "The measured post-JOIN saturation bug is fixed: collection-only and metadata-filtered vector searches escalate until every matching document is seen or the independent ceiling is reached."
    requirement: FILT-03
    verification:
      - kind: unit
        ref: "tests/unit/search/test_vector.py#TestVectorFilteredRecall::test_collection_only_search_returns_all_matching_documents"
        status: pass
      - kind: unit
        ref: "tests/unit/search/test_vector.py#TestVectorFilteredRecall::test_two_percent_selectivity_returns_every_match"
        status: pass
      - kind: unit
        ref: "tests/unit/search/test_vector.py#TestVectorFilteredRecall::test_per_chunk_mode_sees_every_matching_document"
        status: pass
    human_judgment: false
  - id: D2
    description: "D-09 too-selective notice: fires once with formatted reached/matching/requested counts only when recall is provably incomplete, never for a short honest page or a collection-only search, and never on stdout."
    requirement: FILT-03
    verification:
      - kind: unit
        ref: "tests/unit/search/test_vector.py#TestVectorFilteredRecall::test_too_selective_notice_fires_once_with_formatted_counts"
        status: pass
      - kind: unit
        ref: "tests/unit/search/test_vector.py#TestVectorFilteredRecall::test_short_page_below_page_target_logs_no_notice"
        status: pass
      - kind: unit
        ref: "tests/unit/search/test_vector.py#TestVectorFilteredRecall::test_all_matches_found_logs_no_notice"
        status: pass
      - kind: integration
        ref: "tests/integration/test_metadata_filtering.py#TestNoticeStaysOffStdout"
        status: pass
    human_judgment: false
  - id: D3
    description: "Both hybrid/pipeline legs receive the identical filter AST before RRF; one-leg early returns paginate the filtered window; the single slice and ONE enrichment call are unchanged."
    requirement: FILT-03
    verification:
      - kind: unit
        ref: "tests/unit/search/test_hybrid.py#TestFilterPassthrough"
        status: pass
    human_judgment: false
  - id: D4
    description: "End-to-end filtered pipeline on a real schema: containment, admit-all equivalence, 2 % recall on all three paths, filter x collection x pagination, typed 10/10.0 vs \"10\", injection-shaped operands, skipped-key visibility, empty-match sentinel on both legs."
    requirement: FILT-02
    verification:
      - kind: integration
        ref: "tests/integration/test_metadata_filtering.py"
        status: pass
    human_judgment: false

duration: 10min
completed: 2026-11-15
status: complete
---

# Phase 20 Plan 03: Filtered vector escalation and the end-to-end filter proof

**The measured post-JOIN saturation bug is gone: any JOIN filter (collection-only or metadata) now pre-counts its admitted set, seeds the KNN window from selectivity, escalates until every matching document is seen, and warns once on stderr only when recall is provably incomplete — proven by a real-schema integration battery covering containment, 2 % recall, composition, typed exactness, injection, and the empty-match sentinel.**

## Performance

- **Duration:** 10 min
- **Started:** 2026-11-15T12:32:33Z
- **Completed:** 2026-11-15T12:42:57Z
- **Tasks:** 3
- **Files modified:** 5 (1 created)

## Accomplishments
- `src/sif/search/vector.py` now branches on `has_join_filter`: the unfiltered/unscoped path keeps the pre-change statement bytes, fetch window, and stop condition; the JOIN-filtered path computes `pre_count` (metadata matches or scope documents), returns `[]` before any KNN on a zero count, seeds `fetch_k` from `ceil(page_target * total_in_scope / pre_count)`, and stops on target / ceiling / found >= pre_count / whole table.
- The all-matches signal counts distinct documents from raw KNN rows, so `min_score` and per-chunk duplication cannot end escalation early; the per-chunk fixture (fifth matching document at global rank 51) pins it.
- The D-09 notice has exactly three `%d` placeholders, fires once per metadata-filtered search when `pre_count >= page_target` and `_MAX_FETCH_K` was exhausted with a short page, never for a collection-only search or a genuinely short page, and never reaches stdout.
- `HybridSearcher.search` and `SearchPipeline.search` document and test the filter contract: both legs receive the caller's identical `FilterNode` through `fetch_options` (pre-RRF by construction), one-leg early returns paginate the already-filtered window, every expansion variant carries the AST, and the single slice plus ONE `enrich_results` call are unchanged.
- The integration battery (200 generated documents, two collections, real `SchemaManager` + vec0, documents through `DocumentRepository`) proves containment, admit-all page equality (ids/order/scores), 2 % rare-tag recall through BM25/vsearch/query, filter x collection x pagination AND-composition, built-in `mtime`/`path` through the vector leg, typed `10 == 10.0 != "10"`, injection-shaped operands, skipped nested key visibility, and the empty-match sentinel on every path.
- Quality gates green: `ruff check src tests`, `ruff format --check src tests`, `ty check src/sif` (0 diagnostics), full `pytest` 2316 passed / 1 skipped at 95.19 % coverage (gate 90).

## Task Commits

Each task was committed atomically:

1. **Task 1: Corrected filtered vector escalation with selectivity pre-count** - `bfc1b41` (feat)
2. **Task 2: Hybrid/pipeline filter passthrough and early-return windows** - `b84c67d` (test)
3. **Task 3: Integration battery for filtered search on a real schema** - `3858eeb` (test)

**Plan metadata:** the closing docs commit created after this SUMMARY.

## Files Created/Modified
- `src/sif/search/vector.py` — module logger + `_TOO_SELECTIVE_MSG`; compiled filter in the post-KNN JOIN WHERE; `_filtered_fetch_window` pre-count/seeding; two-path corrected escalation; empty-match short circuit; D-09 notice guard.
- `src/sif/search/hybrid.py` — filter-contract docstrings on `HybridSearcher.search` and `SearchPipeline.search` (no behavior change: `replace()` already carried the field).
- `tests/unit/search/test_vector.py` — `_RecordingConnection`; filtered-recall fixtures (two-collection corpus, tagged corpora, per-chunk corpus); seven new tests covering the measured bug, 2 % recall, empty match, distinct-document stop, both notice branches, and the byte-identical unfiltered statement; updated the collection-filter mock for the new scoped COUNT queries.
- `tests/unit/search/test_hybrid.py` — `TestFilterPassthrough` (6 tests: identity of the AST on both legs, both early returns, filtered fused page, pipeline variant propagation + single enrich, per-chunk rows).
- `tests/integration/test_metadata_filtering.py` (new) — 200-document generated corpus, module-scoped fixture with fixture-scoped sqlite-vec skip, 11 test functions (19 parametrized cases) across eight classes.

## Decisions Made
- **Global vector count for the whole-table stop.** `count_vectors_in_scope(db, None)` is the honest "the KNN has seen every stored vector" signal. The plan's literal scoped count made a 2-document collection over 100 docs stop on batch one and return `[]`, contradicting the plan's own acceptance criterion (recorded as a Rule 1 deviation below).
- **AND-prefixed filter suffix.** `f" AND {clause}"` is required for valid SQL when no collection filter is present; mirrors the 20-01 BM25 fix, and the empty suffix keeps the default statement byte-identical.
- **Collection-only pre-count reuses the scope count.** `pre_count = total_in_scope = count_documents_in_scope(...)`, and the notice is gated on `is_metadata_filtered`, so a collection-only search can never emit a metadata-selectivity warning.
- **Two-collection integration corpus.** A second (archive) collection makes composition an actual AND rather than a tautology; rare documents stay in `c1` so `rare + c2` returns the empty sentinel.
- **Fixture-scoped skip.** `pytest.skip` lives in the corpus builder, so a future repository-level discovery test that does not request this fixture still runs without sqlite-vec.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Scoped vector count ended escalation before a selective collection was reached**
- **Found during:** Task 1 (measured-bug regression fixture)
- **Issue:** The plan specified `total_vectors = count_vectors_in_scope(self.db, options.collection_ids)` for the "KNN returned the whole table" stop. For the required 100-document / 2-document-collection / `limit=10` regression, the scoped count is 2, so `fetch_k (50 or 40) >= total_vectors (2)` stopped on batch one with zero survivors and returned `[]` — the exact under-return the task exists to fix, and a contradiction of the task's own acceptance criterion.
- **Fix:** Compare `fetch_k` against the **global** stored-vector count (`count_vectors_in_scope(self.db, None)`), which is what "the KNN scanned the whole table" actually means; the scoped counts still supply `pre_count`/`total_in_scope` for seeding.
- **Files modified:** `src/sif/search/vector.py`
- **Verification:** `test_collection_only_search_returns_all_matching_documents` returns both `c2` documents; the 2 %, per-chunk, and notice fixtures all pass.
- **Committed in:** `bfc1b41`

**2. [Rule 1 - Bug] Filter suffix needed a leading `AND`**
- **Found during:** Task 1 (SQL construction)
- **Issue:** The plan's `filter_suffix = f" {filter_clause}"` renders `... k = ? EXISTS (...)` (invalid SQLite) when a metadata filter is used without collection scoping; this is the same failure class as 20-01's BM25 `AND` bug.
- **Fix:** `filter_suffix = f" AND {filter_clause}" if filter_clause else ""`; the empty suffix keeps the unfiltered/unscoped statement bytes identical.
- **Files modified:** `src/sif/search/vector.py`
- **Verification:** every filtered recall/composition/injection test executes the joined SQL; the unfiltered recording test asserts the pre-Phase-20 statement set.
- **Committed in:** `bfc1b41`

**3. [Rule 3 - Blocking] Collection-filter mock had no answers for the new D-08 pre-count queries**
- **Found during:** Task 1 (existing `TestVectorSearcher::test_search_with_collection_ids`)
- **Issue:** The old mock queued exactly one KNN response; the collection-only path now issues three scoped `COUNT(*)` statements before the KNN, so the side-effect list ran out (`StopIteration`).
- **Fix:** The mock answers `COUNT(*)` statements with a count cursor and the KNN with the vector cursor; the SQL/params assertions are unchanged.
- **Files modified:** `tests/unit/search/test_vector.py`
- **Verification:** `tests/unit/search/test_vector.py` 41 passed.
- **Committed in:** `bfc1b41`

---

**Total deviations:** 3 auto-fixed (2 bugs, 1 blocking).
**Impact on plan:** Both bugs were required for the plan's stated behavior; deviation 1 is a plan-internal contradiction resolved in favor of the explicit acceptance criterion. No scope creep.

## Issues Encountered
- None beyond the three deviations above.

## Threat Model Compliance
- **T-20-09 (tampering):** only placeholders are interpolated; filter params bind after collection ids; injection-shaped values (`'`, `;`, `--`, `%`, a DROP-shaped string) return the same empty set as a plain non-match and leave the corpus intact on both legs.
- **T-20-10 (DoS):** one cheap pre-count per filtered search, selectivity seeding, and the independent `_MAX_FETCH_K` ceiling; a zero pre-count short-circuits before any KNN; the notice makes bounded recall visible rather than silently scanning.
- **T-20-11 (integrity):** the notice goes through `logger.warning` only; the integration test captures stdout as empty while caplog records the message.
- **T-20-12 (information disclosure):** `filter is None` remains the only unfiltered signal; a non-None AST always compiles a predicate; pre-count 0 returns `[]`; both legs receive the same AST object (identity-asserted).
- **T-20-SC:** no dependency added or installed.

## Known Stubs
None.

## Threat Flags
None — the shipped surface is covered by the plan's threat register.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- **Ready for 20-04:** `SearchOptions.filter` now reaches both legs correctly, so the remaining CLI (`vsearch`/`query`) and MCP surfaces only need to parse/validate and thread the AST; the five output paths inherit the fixed leg behavior.
- **Ready for 20-05:** the discovery tool can reuse the same pre-count helpers and trust that filtering means pre-RRF admission on every leg; `tests/integration/test_metadata_filtering.py` is explicit-builder so a `TestDiscoveryParity` class can join the file without sqlite-vec (the skip is fixture-scoped).
- **Carry-forward:** qmd's AST is still `[Unreleased]`; re-verify before Phase 22 freezes the MCP schema.

---
*Phase: 20-metadata-filtering-discovery*
*Completed: 2026-11-15*

## Self-Check: PASSED

- All five task-related files and this SUMMARY exist on disk.
- All three task commits (`bfc1b41`, `b84c67d`, `3858eeb`) are ancestors of HEAD.
