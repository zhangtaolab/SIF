---
phase: 14-freshness-floor-pre-command-refresh-staleness-marking
plan: 02
subsystem: search
tags: [sqlite-vec, vec0, staleness, search-quality, mcp, click, rich, pytest]

# Dependency graph
requires:
  - phase: 11-live-index-foundation-concurrent-db-incremental-core
    provides: IncrementalIndexer update_paths purge contract, factory connection (sqlite-vec loaded)
  - phase: 12-sif-watch-foreground-mvp
    provides: D-10 BM25-update purges chunks+vectors together (the invariant the derived signal rests on)
  - phase: 14-freshness-floor-pre-command-refresh-staleness-marking/14-01
    provides: stderr-notice culture and shared-helper placement this plan mirrors at the searcher layer
provides:
  - mark_vector_staleness / embedded_document_ids in src/sif/search/staleness.py (presentation-free, derived, idempotent, vec0-missing degrading)
  - SearchResult.vectors_stale boolean riding to_dict() into --json output
  - One-code-path marking at BM25Searcher/VectorSearcher/HybridSearcher _attach_contexts (covers CLI search/query/vsearch, MCP, and benignly bench)
  - MCP backend.hybrid_search metadata carries vectors_stale (explicit forward, D-11/B5)
  - `sif status` Vector lag row with n/a / none (no vectors indexed) / N documents states (D-10)
  - D-08 invariant regression in test_incremental.py (update_paths leaves a BM25-updated doc embeddings-free)
affects: [14-03 (format battery + remedy hint consume the flag), mcp-server clients (new metadata key), 16 (bench sees read-only marking at searcher layer by design)]

# Actuals (#2632) — same estimateTokens scale (chars/4 over the realized diff)
actuals:
  tokens: 10059   # 40,234 diff chars / 4 over src+tests (plan estimate: 45,000)
  tasks: 2
  commits: 4      # MEASURED: git rev-list --count 6dfe8d0..HEAD

plan_head_before: 6dfe8d0d16036fdf8bf99950746af3f58e02bef1
plan_head_after: 337a68ebf6e04d6576f1b880e7ebbe9c2eb75463

# Tech tracking
tech-stack:
  added: []   # zero new runtime dependencies (locked decision; Package Legitimacy Audit empty)
  patterns:
    - "Derived staleness enrichment sibling of attach_path_contexts: one constant vec0 scan, row-at-a-time, mutate-and-return, never per-result queries"
    - "Display gate: markers/status-lag states activate only when the index has >= 1 embedding (pure-BM25 users never nagged)"
    - "MCP field forwarding: backend re-maps core fields explicitly — any new SearchResult field must be forwarded into metadata by hand (B5)"

key-files:
  created:
    - src/sif/search/staleness.py
    - tests/unit/search/test_staleness.py
  modified:
    - src/sif/core/models.py
    - src/sif/search/bm25.py
    - src/sif/search/vector.py
    - src/sif/search/hybrid.py
    - src/sif/mcp/backend.py
    - src/sif/cli/main.py
    - tests/unit/mcp/test_backend.py
    - tests/unit/cli/test_status.py
    - tests/unit/indexing/test_incremental.py
    - tests/unit/search/test_bm25.py   # deviation Rule 3 (side_effect pins)
    - tests/unit/search/test_vector.py # deviation Rule 3 (side_effect pins)

key-decisions:
  - "Corrected D-08 formula implemented and documented: stale = no rows in document_embeddings (BM25 updates purge chunks AND embeddings, so 'chunks without embeddings' never fires for the real lag state)"
  - "Display gate over the honest signal: zero-embedding index marks nothing and renders 'none (no vectors indexed)' in status — RESEARCH OQ2 plan-time resolution"
  - "Lag-state e2e keeps a second (keeper) document embedded so the purge of the drifted doc leaves the gate armed — a single-doc index would correctly mark nothing after its only embedding purges"
  - "Vector lag row counts lag via documents-id scan membership (SELECT id FROM documents), robust to orphan embedding ids, same one-row-at-a-time discipline"
  - "vec0 v0.1.9 rejects NULL for TEXT metadata columns on INSERT — fixtures seed real chunk_id strings (in-repo test_vector.py precedent note)"

patterns-established:
  - "Searcher-exit enrichment contract: _attach_contexts chains attach_path_contexts then mark_vector_staleness — three edits cover every exit including hybrid early returns and SearchPipeline delegation"
  - "Status degrade row: probe helper + Phase 13 try/except + single table.add_row (Watch and Vector lag rows now share the shape)"

requirements-completed: [QUAL-06]

coverage:
  - id: D1
    description: "Staleness module: embedded_document_ids (one scan, None on vec0-missing) + mark_vector_staleness (display gate, empty-results no-query, idempotent)"
    requirement: QUAL-06
    verification:
      - kind: unit
        ref: "tests/unit/search/test_staleness.py#TestEmbeddedDocumentIds"
        status: pass
      - kind: unit
        ref: "tests/unit/search/test_staleness.py#TestMarkVectorStaleness.test_display_gate_zero_embeddings_marks_nothing"
        status: pass
      - kind: unit
        ref: "tests/unit/search/test_staleness.py#TestMarkVectorStaleness.test_vec0_missing_degrades_to_unmarked"
        status: pass
      - kind: unit
        ref: "tests/unit/search/test_staleness.py#TestMarkVectorStaleness.test_marking_is_idempotent"
        status: pass
    human_judgment: false
  - id: D2
    description: "SearchResult.vectors_stale field + to_dict key riding --json automatically"
    requirement: QUAL-06
    verification:
      - kind: unit
        ref: "tests/unit/search/test_staleness.py#TestMarkVectorStaleness.test_to_dict_carries_vectors_stale_alongside_context_description"
        status: pass
    human_judgment: false
  - id: D3
    description: "One-code-path wiring: BM25Searcher/VectorSearcher/HybridSearcher _attach_contexts invoke mark_vector_staleness (hybrid early returns funnel through it; SearchPipeline delegates)"
    requirement: QUAL-06
    verification:
      - kind: unit
        ref: "tests/unit/search/test_staleness.py#TestSearcherDelegation.test_all_three_searchers_delegate"
        status: pass
    human_judgment: false
  - id: D4
    description: "Real tiered-depth lag state proven end-to-end: embed -> modify -> update_paths purge -> BM25 results marked True, keeper doc unmarked"
    requirement: QUAL-06
    verification:
      - kind: unit
        ref: "tests/unit/search/test_staleness.py#TestLagStateEndToEnd.test_bm25_refreshed_after_embed_doc_is_marked_stale"
        status: pass
    human_judgment: false
  - id: D5
    description: "MCP forwarding: backend.hybrid_search metadata carries vectors_stale with the core result's value (D-11/B5)"
    requirement: QUAL-06
    verification:
      - kind: unit
        ref: "tests/unit/mcp/test_backend.py#test_hybrid_search_mocks"
        status: pass
    human_judgment: false
  - id: D6
    description: "sif status Vector lag row: 'N documents' when armed, 'none (no vectors indexed)' on pure-BM25 index, 'n/a' when vec0 missing, degraded render + exit 0 on probe failure"
    requirement: QUAL-06
    verification:
      - kind: unit
        ref: "tests/unit/cli/test_status.py#TestVectorLag"
        status: pass
    human_judgment: false
  - id: D7
    description: "D-08 invariant regression: update_paths on a modified, previously-embedded doc leaves zero document_embeddings AND zero document_chunks rows (fresh connection)"
    requirement: QUAL-06
    verification:
      - kind: unit
        ref: "tests/unit/indexing/test_incremental.py#TestUpdatePathsReplay.test_update_paths_purges_embeddings_of_modified_doc"
        status: pass
    human_judgment: false

# Metrics
duration: 14min
completed: 2026-11-08
status: complete
---

# Phase 14 Plan 02: Staleness Marking Summary

**Derived vector-staleness marking on every search surface: a corrected "no embeddings" D-08 signal computed in the shared searcher enrichment path, forwarded through MCP metadata, plus a `sif status` Vector lag row — zero schema change, zero new dependencies.**

## Performance

- **Duration:** 14 min
- **Started:** 2026-11-08T03:35:19Z
- **Completed:** 2026-11-08T03:49:49Z
- **Tasks:** 2 (both TDD: RED → GREEN)
- **Files modified:** 13 (2 created, 11 modified)

## TDD Gate Compliance

Both tasks executed test-first; RED commits carry importable zero-behavior skeletons so failures are assertion failures, never import errors (11-01 culture).

| Task | RED | GREEN | REFACTOR |
|------|-----|-------|----------|
| 1 (tracer: staleness core + wiring) | `fc8685a` — 5/12 battery tests failed on planned assertions (skeleton returns unmarked/empty set); 7 passed as pins; 182 existing search tests stayed green | `3bbf613` — all 12 green + 12 mock-scaffold extensions | — (see note) |
| 2 (MCP forward + status row + invariant) | `0e58a5f` — 3 fail on planned assertions (metadata forward missing; lag/none states unimplemented); vec0-missing/degrade/invariant passed as regression pins | `337a68e` — all green + full-suite gate | — (see note) |

**REFACTOR note:** no refactor-worthy cleanup existed beyond the RED-phase structural decisions themselves (wiring chained inside the existing `_attach_contexts`, helper sibling of `_watch_status_text`) — `ruff check`/`format`/`ty` stayed green throughout, so no `refactor(14-02)` commit was warranted.

**Tracer feedback gate (auto mode):** verify re-run end-to-end after Task 1 — 12/12 staleness battery, 187/187 search dir, wiring counts 2/2/2 — all green; expanded to Task 2.

## Accomplishments

- Every searcher exit marks consistently: embedded docs unmarked, embedding-less docs marked (once the index has ≥1 embedding — the display gate), vec0-missing degrades silently to no markers, and an empty result list never touches the DB
- The real tiered-depth lag state is proven end-to-end: seed embeddings, modify the file, run `IncrementalIndexer.update_paths` — the purge produces the lag state and the doc's BM25 results carry `vectors_stale: true` (never raw-SQL fabrication)
- The boolean rides `to_dict()` into `--json` automatically and reaches MCP clients through an explicit metadata forward (the backend boundary drops unknown core fields — RESEARCH Pitfall 8)
- `sif status` shows index-level vector lag at a glance (`Vector lag: N documents` / `none (no vectors indexed)` / `n/a`), degrade-never-fail like the Phase 13 Watch row
- The purge invariant the signal rests on is pinned: a BM25-updated doc provably has zero embeddings AND zero chunks through a fresh connection (D-08 invariant regression)

## Task Commits

Each task was committed atomically (TDD: test → feat):

1. **Task 1 RED: failing staleness battery + zero-behavior skeleton** — `fc8685a` (test)
2. **Task 1 GREEN: derived marking implementation + wiring** — `3bbf613` (feat)
3. **Task 2 RED: MCP-forward / Vector-lag / invariant tests + status skeleton** — `0e58a5f` (test)
4. **Task 2 GREEN: backend forward + _vector_lag_text + row** — `337a68e` (feat)

## Files Created/Modified

- `src/sif/search/staleness.py` (NEW) — presentation-free derived signal: `embedded_document_ids` (one constant vec0 scan, row-at-a-time, None on OperationalError) + `mark_vector_staleness` (display gate, empty-results no-query, idempotent mutate-and-return); module docstring cites D-08/D-09, the corrected formula rationale, and the batching rule
- `src/sif/core/models.py` — `SearchResult.vectors_stale: bool = False` after `context_description` + `to_dict()` entry (defaulted — no constructor breakage; `--line-numbers` preserves new keys)
- `src/sif/search/bm25.py`, `vector.py`, `hybrid.py` — `_attach_contexts` chains `mark_vector_staleness(self.db, attach_path_contexts(...))` (one import + one call each; covers hybrid's early returns and SearchPipeline's delegation)
- `src/sif/mcp/backend.py` — `vectors_stale` in the hybrid_search metadata dict beside rank and collection_name
- `src/sif/cli/main.py` — `_vector_lag_text` helper (shared `embedded_document_ids` + documents-id scan) + `Vector lag` row after the Watch row, wrapped in the degrade-never-fail try/except
- `tests/unit/search/test_staleness.py` (NEW) — 12-test battery (formula, gate, degrade, no-query, idempotency, to_dict, real-purge e2e, three-searcher delegation)
- `tests/unit/mcp/test_backend.py` — metadata forward assertion in `test_hybrid_search_mocks`
- `tests/unit/cli/test_status.py` — `TestVectorLag` section (4 states) on the TestWatchSection scaffold
- `tests/unit/indexing/test_incremental.py` — D-08 invariant regression + `_embedding_count` fresh-connection reader (sqlite-vec loaded best-effort)
- `tests/unit/search/test_bm25.py`, `tests/unit/search/test_vector.py` — 12 enumerated `side_effect` mock tests extended with the staleness-scan cursor (deviation 1)

## Decisions Made

- Lag-state e2e design: a keeper document stays embedded so the purge of the drifted doc leaves the display gate armed — without it the single-doc index would have zero embeddings after the purge and correctly mark nothing (the gate working as designed, not a bug)
- Status lag count uses documents-id scan membership (`SELECT id FROM documents` iterated, counting ids not in the embedded set) rather than `N - len(embedded)` — robust to orphan embedding ids, and the plan's named SQL verbatim
- `vec0` seeding in fixtures always uses real `chunk_id` strings: sqlite-vec v0.1.9 rejects NULL for a TEXT metadata column on INSERT (documented in-repo by test_vector.py's real-vec0 battery)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Twelve enumerated side_effect mock tests extended with a staleness-scan cursor**
- **Found during:** Task 1 (GREEN)
- **Issue:** `_attach_contexts` now issues a third execute call (the `document_embeddings` scan); the mock tests in `test_bm25.py` / `test_vector.py` that enumerate `mock_db.execute.side_effect` lists per call exhausted their lists and raised StopIteration — the new enrichment call is legitimate, the call-count pins predate it
- **Fix:** Appended one `staleness_cursor = MagicMock()` (empty iteration → display gate → results unmarked) to each affected side_effect list; comments updated to name the staleness scan; test intent unchanged (these same lists were extended the same way when `attach_path_contexts` was added)
- **Files modified:** tests/unit/search/test_bm25.py (7 tests), tests/unit/search/test_vector.py (5 tests) — neither file is in the plan's `files_modified`
- **Verification:** 187/187 in tests/unit/search; full suite 1208 passed
- **Committed in:** 3bbf613

**2. [Rule 1 - Test-authoring corrections during RED/GREEN (no production impact)**
- **Found during:** Task 1 RED and Task 2 GREEN
- **Issue:** (a) fixtures initially seeded vec0 rows with `chunk_id=None`, which v0.1.9 rejects on INSERT; (b) the e2e lag test initially embedded only the drifted doc, so the purge disarmed the display gate (marked nothing — correctly); (c) `TestVectorLag`'s mocked documents-scan rows were plain strings, so `row[0]` read the first character; (d) three PT018 compound assertions
- **Fix:** Real chunk_id strings; keeper document added; rows as 1-tuples; assertions split. The keeper-document change also strengthened the e2e (asserts both the marked drifted doc AND the unmarked keeper)
- **Files modified:** tests/unit/search/test_staleness.py, tests/unit/cli/test_status.py
- **Verification:** targeted batteries green
- **Committed in:** fc8685a / 3bbf613 / 337a68e

---

**Total deviations:** 2 auto-fixed (1 blocking, 1 test-authoring)
**Impact on plan:** The side_effect extensions are the unavoidable consequence of adding a fourth enrichment query to a mocked path; intent of every affected test is preserved. No scope creep.

## Issues Encountered

None beyond the deviations above.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- QUAL-06 core (SC3 computation half) complete: the flag is derived, consistent across search/query/vsearch exits, idempotent, and visible in `--json` + MCP + `sif status`; vec0-missing degrades everywhere
- Ready for 14-03: the D-12 format battery (Rich table/CSV/MD/XML marker) and the D-13 stderr remedy hint consume `SearchResult.vectors_stale` exactly as `--json` already does
- Full quality suite green at `plan_head_after`: 1208 passed @ 94.41% coverage (fail_under=90), ruff/format/ty green; `src/sif/database/schema.py` untouched (no-schema-change proof)

## Self-Check: PASSED

- All 13 key-files exist on disk (created + modified lists verified via `[ -f ]`)
- All 4 task commits are ancestors of HEAD (`git merge-base --is-ancestor`)
- QUAL-06 is the sole declared requirement; sibling plans 14-01/14-03 declare LIVE-10 and (14-03) the presentation half

---
*Phase: 14-freshness-floor-pre-command-refresh-staleness-marking*
*Completed: 2026-11-08*
