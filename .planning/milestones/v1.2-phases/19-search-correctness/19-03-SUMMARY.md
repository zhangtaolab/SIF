---
phase: 19-search-correctness
plan: 03
subsystem: search
tags: [search-pipeline, enrichment, context-attach, staleness, single-owner, corr-05]

# Dependency graph
requires:
  - phase: 19-search-correctness
    provides: "wave ordering after 19-02 (no direct code artifact consumed by this search-side plan)"
provides:
  - "enrich_results(db, results) — the single composition of attach_path_contexts + mark_vector_staleness"
  - "BM25Searcher/VectorSearcher/HybridSearcher return raw results; no searcher exposes _attach_contexts"
  - "SearchPipeline.search enriches exactly once on the BM25, VECTOR, HYDE, and hybrid exits"
  - "staleness D-09 docstring names the enrich_results owner (pipeline exit plus direct CLI/MCP entry points)"
  - "single-owner contract tests: per-exit exactly-one spy and a hybrid pipeline marker-parity real-DB test"
affects: [19-04 (CLI/MCP direct entry points and B0 baseline consume enrich_results), 21 (CORR-06 scan elimination reuses the one-owner seam), 22 (MCP pipeline parity)]

# Actuals (#2632) — chars/4 over the realized diff (same scale as the plan estimate)
actuals:
  tokens: 10649
  tasks: 3
  commits: 3

commits: 3
plan_head_before: bdcf3dd16eade9490915d3d4329933926791a477
plan_head_after: 9ea1d4c280035582c670cfe3afd4253fd1e8d8f9

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Single-owner enrichment: searchers are pure result producers; the public entry point owns exactly one enrich_results call per exit"
    - "One composition helper (attach_path_contexts then mark_vector_staleness) replaces three duplicated searcher _attach_contexts methods"

key-files:
  created: []
  modified:
    - src/sif/search/context_attach.py
    - src/sif/search/staleness.py
    - src/sif/search/bm25.py
    - src/sif/search/vector.py
    - src/sif/search/hybrid.py
    - tests/unit/search/test_bm25.py
    - tests/unit/search/test_vector.py
    - tests/unit/search/test_hybrid.py
    - tests/unit/search/test_staleness.py
    - tests/unit/search/test_context_attach.py

key-decisions:
  - "enrich_results lives in context_attach.py and imports mark_vector_staleness from staleness.py; staleness imports only sif.core.models, so the composition has no import cycle."
  - "Every SearchPipeline.search branch returns enrich_results(self.db, self._apply_snippets(...)) exactly once; the hybrid branch enriches after fusion, reranking, and snippets."
  - "Searchers are pure producers: BM25, vector, and hybrid results are raw on both early-return and fused paths, so no path can attach twice."
  - "The end-to-end lag-state test now wraps BM25Searcher.search in enrich_results, matching the entry-point contract instead of the removed searcher attach."
  - "Direct CLI search/vsearch and the MCP BM25 fallback are unenriched until Plan 19-04 lands their single enrich_results call (planned sequencing, not a loss introduced here)."
  - "Marker parity is pinned on a real-DB hybrid pipeline fixture: a verbatim context row matches on read and a purged embedding marks only the BM25-only document."

patterns-established:
  - "Enrichment ownership is asserted by a spy that counts exactly one enrich_results call per pipeline exit and checks result-list identity."
  - "Marker parity tests use the real schema + vec0 path, not raw-SQL fabrication, to prove derived-signal semantics survive an attach refactor."

requirements-completed: [CORR-05]

# Coverage metadata (#1602)
coverage:
  - id: D1
    description: "enrich_results composes attach_path_contexts then mark_vector_staleness on the same list, with the db and list identity preserved"
    requirement: CORR-05
    verification:
      - kind: unit
        ref: "tests/unit/search/test_context_attach.py#TestAttachPathContextsRealSQL.test_enrich_results_composes_both_signals"
        status: pass
      - kind: unit
        ref: "tests/unit/search/test_bm25.py#TestBM25SearcherEnrichmentContract.test_enrich_results_attaches_context_description"
        status: pass
    human_judgment: false
  - id: D2
    description: "BM25, vector, and hybrid searchers return raw results and expose no _attach_contexts method"
    requirement: CORR-05
    verification:
      - kind: unit
        ref: "tests/unit/search/test_staleness.py#TestSearcherDelegation.test_searchers_do_not_expose_attach"
        status: pass
      - kind: unit
        ref: "tests/unit/search/test_bm25.py#TestBM25SearcherEnrichmentContract.test_search_returns_raw_results_without_enrichment"
        status: pass
      - kind: unit
        ref: "tests/unit/search/test_vector.py#TestVectorSearcherEnrichmentContract.test_search_returns_raw_results_without_enrichment"
        status: pass
      - kind: unit
        ref: "tests/unit/search/test_hybrid.py#TestHybridContextAttachment.test_hybrid_search_returns_raw_results"
        status: pass
    human_judgment: false
  - id: D3
    description: "Every SearchPipeline.search exit (BM25, VECTOR, HYDE, hybrid) calls enrich_results exactly once with the same result list"
    requirement: CORR-05
    verification:
      - kind: unit
        ref: "tests/unit/search/test_staleness.py#TestSearcherDelegation.test_each_pipeline_exit_enriches_exactly_once"
        status: pass
      - kind: unit
        ref: "tests/unit/search/test_hybrid.py#TestHybridContextAttachment.test_pipeline_search_attaches_context_after_reranking"
        status: pass
    human_judgment: false
  - id: D4
    description: "The D-09 docstring names the enrich_results owner and no _attach_contexts reference remains under src/sif/search"
    requirement: CORR-05
    verification:
      - kind: other
        ref: "test -z \"$(grep -rn '_attach_contexts' src/sif/search)\" (0 matches)"
        status: pass
    human_judgment: false
  - id: D5
    description: "Hybrid pipeline preserves context descriptions and derived vectors_stale markers: the verbatim context row attaches and one purged embedding marks only that document"
    requirement: CORR-05
    verification:
      - kind: unit
        ref: "tests/unit/search/test_hybrid.py#TestHybridContextAttachment.test_pipeline_hybrid_exit_enriches_contexts_and_staleness"
        status: pass
      - kind: unit
        ref: "tests/unit/search/test_staleness.py#TestMarkVectorStaleness (display gate, None degradation, idempotence)"
        status: pass
    human_judgment: false

duration: 6min
completed: 2026-11-15
status: complete
---

# Phase 19 Plan 03: Single-Owner Context and Staleness Enrichment Summary

**Searchers now return raw results and every search-pipeline exit performs exactly one `enrich_results` composition of path contexts plus derived vector staleness**

## Performance

- **Duration:** 6 min
- **Started:** 2026-11-15T03:14:10Z
- **Completed:** 2026-11-15T03:20:43Z
- **Tasks:** 3/3
- **Files modified:** 10 (5 source, 5 test)
- **Commits:** 3 (one per task)

## Accomplishments

- `context_attach.enrich_results(db, results)` is the one composition of `attach_path_contexts` then `mark_vector_staleness`, returning the same list; it imports staleness (which imports only `sif.core.models`) so no cycle exists.
- `BM25Searcher`, `VectorSearcher`, and `HybridSearcher` are pure result producers: all three `_attach_contexts` methods and their compose imports are gone, and every early-return/fused path returns raw results.
- `SearchPipeline.search` owns the single enrichment on all four exits — BM25, VECTOR, HYDE, and hybrid — each calling `enrich_results(self.db, self._apply_snippets(...))` once; the hybrid exit enriches after fusion, reranking, and snippets.
- `staleness.py`'s D-09 docstring now names the real owner (pipeline exit plus Plan 04's direct CLI/MCP entry points) instead of the removed searcher attach path.
- Contract tests were rewritten rather than relaxed: a spy counts exactly one `enrich_results` call per pipeline exit with list identity, and a real-DB hybrid fixture proves a verbatim context row still attaches while a purged embedding marks only the BM25-only document.
- The real lag-state end-to-end test now enriches at the entry point (`enrich_results(db, BM25Searcher(...).search(...))`), so derived staleness remains proven against a real `update_paths` purge.

## Task Commits

Each task was committed atomically:

1. **Task 1: enrich_results helper + BM25 searcher de-attach + pipeline BM25 exit (tracer)** - `7fb754d` (feat)
2. **Task 2: Vector searcher de-attach + pipeline VECTOR/HYDE exits** - `b6e0923` (feat)
3. **Task 3: Hybrid searcher de-attach + pipeline hybrid exit + one-attach contract test** - `9ea1d4c` (feat)

**Plan metadata:** committed after this SUMMARY (docs: complete plan)

_Note: Task 1 ran as a tracer; the feedback gate re-ran its `<verify>` green (47 passed) before expansion._

## Files Created/Modified

- `src/sif/search/context_attach.py` - added `enrich_results`; `attach_path_contexts` unchanged (constant SQL, two-sided normalize, no clobber)
- `src/sif/search/bm25.py` - `search` returns raw results; `_attach_contexts` and attach/staleness imports removed
- `src/sif/search/vector.py` - `_search_with_vec` returns raw trimmed/ranked results; `_attach_contexts` removed
- `src/sif/search/hybrid.py` - `HybridSearcher.search` returns raw results on all paths; pipeline exits call `enrich_results` once; docstrings updated
- `src/sif/search/staleness.py` - D-09 module docstring rewritten to name the `enrich_results` owner
- `tests/unit/search/test_bm25.py` - dropped context/staleness cursors from `search` mocks; `TestBM25SearcherEnrichmentContract` (raw search + helper composition)
- `tests/unit/search/test_vector.py` - dropped attach cursors; `TestVectorSearcherEnrichmentContract`
- `tests/unit/search/test_hybrid.py` - raw-hybrid and one-enrichment-after-rerank tests; real-DB hybrid marker-parity test
- `tests/unit/search/test_staleness.py` - single-owner spy for all four exits; lag-state test enriches at the entry point
- `tests/unit/search/test_context_attach.py` - real-DB `enrich_results` test and composition-order test

## Decisions Made

- `enrich_results` lives in `context_attach.py` because the composition reads naturally there and staleness only imports `sif.core.models`; no cycle is introduced.
- The pipeline enriches after snippets on the three prefix exits and after fusion/rerank/snippets on the hybrid exit, so the helper always sees the final result list exactly once.
- Searcher docstrings now state they return raw results, making the ownership boundary explicit for future call sites.
- The measured-data contract is preserved: no SQL or normalization changes were made in `attach_path_contexts`, and `mark_vector_staleness` remains a single batched scan with the display gate and `None` degradation.
- Direct CLI `search`/`vsearch` and the MCP BM25 fallback deliberately remain unenriched until Plan 19-04 adds their single `enrich_results` call; the plan sequencing assigns those entry points to 19-04.

## Deviations from Plan

None - plan executed exactly as written.

The only in-scope test adaptation beyond the named classes was `TestLagStateEndToEnd`, which exercised the removed searcher attach; it now wraps `BM25Searcher.search` in `enrich_results`, matching the new entry-point contract (no behavior change to the marker assertions).

## Issues Encountered

None. Ruff's RET504 flagged an intermediate `deduped` assignment introduced by the raw-return change; it was collapsed to a direct `return self._deduplicate_results(fused_results)` before the Task 3 commit.

## Verification Results

- `env -u FORCE_COLOR NO_COLOR=1 pytest tests/unit/search -x --no-cov` -> 489 passed
- `env -u FORCE_COLOR NO_COLOR=1 pytest -q` (CLAUDE.md full gate) -> 1920 passed, 1 skipped, coverage 95.22% (fail_under=90)
- `ruff check src tests` -> All checks passed
- `ruff format --check src tests` -> 195 files already formatted
- `ty check src/sif` -> All checks passed
- `test -z "$(grep -rn '_attach_contexts' src/sif/search)"` -> 0 matches
- Dependency guard: `git diff --name-only <plan_head_before>..HEAD -- pyproject.toml uv.lock` -> 0 files

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- CORR-05 is complete at the search-core seam: one composition helper exists and the pipeline is the single enrichment owner for every exit.
- Plan 19-04 is unblocked and must now add the one `enrich_results` call at the direct CLI `search`/`vsearch` exits and the MCP BM25 fallback, then record B0 on the post-CORR-01 engine.
- Until 19-04 lands, those direct entry points return raw results (no context descriptions or staleness markers) — an expected transitional state from the plan's sequencing, not a regression of this plan's contract.
- No dependency, schema, or public-output changes; `pyproject.toml`/`uv.lock` untouched.

---

*Phase: 19-search-correctness*
*Completed: 2026-11-15*

## Self-Check: PASSED

- Key files exist on disk: 10/10 modified files found.
- Commits are ancestors of HEAD: `7fb754d`, `b6e0923`, `9ea1d4c` all found.
- Evaluation scope resolved for plan `19-03` (commits-only scope) with all 3 commits.
- Plan-level verification re-run: `tests/unit/search` 489 passed; full suite 1920 passed, 1 skipped, 95.22% coverage; ruff/format/ty green; 0 `_attach_contexts` matches under `src/sif/search`.
