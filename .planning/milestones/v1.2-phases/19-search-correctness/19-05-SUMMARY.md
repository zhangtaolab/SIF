---
phase: 19-search-correctness
plan: 05
subsystem: search
tags: [pagination, offset, global-rank, bm25, vector, hybrid, search-pipeline, cli, mcp, corr-03]

# Dependency graph
requires:
  - phase: 19-search-correctness
    provides: "19-01 canonical checksums; 19-02 per-collection convention marker; 19-03 enrich_results at pipeline exits; 19-04 entry-point enrichment and the committed B0 baseline (bench/b0.json)"
provides:
  - "--offset on sif search/vsearch/query (IntRange(min=0), default 0) threaded into SearchOptions"
  - "BM25 min_score as a bound rank predicate inside the FTS scan, before LIMIT/OFFSET"
  - "one offset slice owner per query path (BM25 SQL, vector slice, hybrid slice, pipeline slice)"
  - "global rank numbering (rank = offset + position) on every search surface"
  - "MCP offset fields on QueryInput/LexSearchInput/VecSearchInput plus the query tool schema"
  - "SearchBackend.hybrid_search(offset=0) forwarding and a BM25-fallback-identical options object"
  - "B0 no-drift proof at offset=0/min_score=0 (n=100, mean delta 0.0)"
affects: [19-06 (dedup builds on the slice owner), 19-07/19-08/19-09 (goldens and title-weight measurement), 20 (metadata filters compose with pagination), 22 (lex/vec tool registration)]

# Actuals (#2632) — chars/4 over the realized diff (same scale as the plan estimate)
actuals:
  tokens: 17345
  tasks: 3
  commits: 3

commits: 3
plan_head_before: afd8b42d58c9ab5c6493a7355d0ab0bc5fa7727d
plan_head_after: 294713e3e3ac8671dce65ea72941284b92f578b7

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "One offset slice owner per query path: BM25 SQL OFFSET, vector slice, HybridSearcher slice for direct callers, pipeline slice for its own path"
    - "Global rank numbering: rank = options.offset + position, so pages continue 11-20, 21-30"
    - "min_score is a bound SQL predicate (rank >= 1 - 1/min_score) evaluated inside the FTS scan, never a post-pagination skip"
    - "MCP request fields stay in sync across three places: Pydantic model, hand-written input_schema, backend signature -> SearchOptions"

key-files:
  created:
    - tests/unit/cli/test_search_pagination.py
    - tests/integration/test_search_correctness.py
  modified:
    - src/sif/search/bm25.py
    - src/sif/search/vector.py
    - src/sif/search/hybrid.py
    - src/sif/cli/commands/search.py
    - src/sif/mcp/protocol.py
    - src/sif/mcp/handlers.py
    - src/sif/mcp/backend.py
    - docs/cli-reference.md
    - tests/unit/search/test_bm25.py
    - tests/unit/search/test_vector.py
    - tests/unit/search/test_hybrid.py
    - tests/unit/search/test_staleness.py
    - tests/unit/mcp/test_backend.py

key-decisions:
  - "BM25 min_score keeps the plan's predicate `rank >= 1 - 1/min_score` bound before LIMIT/OFFSET, and the `1/(1+|rank|)` score formula is unchanged (plan constraint); a real-corpus test pins the resulting row set and threshold direction."
  - "The vector fetch window is `min(max((limit+offset)*4, 50), _MAX_FETCH_K=2048)`: a past-the-cap offset yields an empty page instead of unbounded KNN work."
  - "The shared `_paginate` helper clamps the page size to `max(1, limit)`, preserving the WR-03 contract that a non-positive limit returns one row."
  - "HybridSearcher is the single slice owner for direct callers, including the vector-only/BM25-only early returns; both legs are called with offset=0 and limit+offset."
  - "SearchPipeline always calls hybrid with offset=0 and slices once after reranking/snippets; with a reranker the pre-rerank window is max(candidate_limit, limit+offset) for offset>0 and exactly candidate_limit at offset=0 (Phase 16 cap and the byte-identical default path preserved); top_k = limit+offset."
  - "MCP offset lands on QueryInput, LexSearchInput, and VecSearchInput; the lex/vec tools stay unregistered (Phase 22 owns registration, research Open Q1)."
  - "B0 re-measurement ran on the existing scratch index (150 docs, fingerprint 8c006123784348d1): n=100, mean delta 0.0, 100 unchanged, so offset=0/min_score=0 reproduces the baseline exactly."

patterns-established:
  - "Page continuity is proven against a same-window request (limit=o+l offset=0 sliced [o:o+l]), never against a different candidate depth (research Pitfall 11)."
  - "Integration fixtures build 40 distinct single-chunk documents (real SchemaManager + ConceptEmbedder + vec0) so BM25/vector/hybrid paging and reranker windows are deterministic without duplicate chunk sets."
  - "Existing ownership tests were updated to the new slice contract rather than relaxed: enrichment receives the pipeline's sliced page list, which is the CORR-03 ownership boundary."

requirements-completed: [CORR-03]

# Coverage metadata (#1602)
coverage:
  - id: D1
    description: "BM25 filters min_score inside the FTS scan before LIMIT/OFFSET and numbers ranks globally across pages"
    requirement: CORR-03
    verification:
      - kind: unit
        ref: "tests/unit/search/test_bm25.py#TestBM25OffsetPagination (5 tests: both SQL branches, continuity, past-end, threshold direction, threshold-before-offset)"
        status: pass
      - kind: unit
        ref: "tests/unit/search/test_bm25.py#TestBM25Searcher.test_search_applies_min_score + test_search_min_score_zero_omits_the_threshold_filter"
        status: pass
    human_judgment: false
  - id: D2
    description: "sif search/vsearch/query accept --offset (IntRange(min=0)) and render global ranks"
    requirement: CORR-03
    verification:
      - kind: unit
        ref: "tests/unit/cli/test_search_pagination.py#TestSearchCommandOffset/TestVsearchCommandOffset/TestQueryCommandOffset"
        status: pass
    human_judgment: false
  - id: D3
    description: "VectorSearcher fetch_k scales with limit+offset, is capped at 2048, slices once, and ranks globally"
    requirement: CORR-03
    verification:
      - kind: unit
        ref: "tests/unit/search/test_vector.py#TestVectorOffsetPagination (4 tests)"
        status: pass
    human_judgment: false
  - id: D4
    description: "Hybrid and pipeline own exactly one offset slice, paginate early single-leg returns, and grow the reranker window past the candidate cap"
    requirement: CORR-03
    verification:
      - kind: unit
        ref: "tests/unit/search/test_hybrid.py#TestHybridOffsetPagination + TestPipelineOffsetPagination + TestCandidateFetch"
        status: pass
      - kind: integration
        ref: "tests/integration/test_search_correctness.py#TestConsistentPagination + TestRerankerWindowPagination (7 tests)"
        status: pass
    human_judgment: false
  - id: D5
    description: "MCP offset is validated on all three inputs, advertised in the query schema, and forwarded into SearchOptions (pipeline and BM25 fallback)"
    requirement: CORR-03
    verification:
      - kind: unit
        ref: "tests/unit/mcp/test_backend.py#TestQueryInputOffsetValidation/TestQueryToolHandlerOffsetPassThrough/TestHybridSearchOffsetForwarding"
        status: pass
    human_judgment: false
  - id: D6
    description: "Generated CLI reference documents --offset and the B0 baseline reproduces with zero ranking drift at offset=0"
    verification:
      - kind: other
        ref: "make docs-generate && git diff --exit-code docs/ (clean; exactly the three --offset rows changed; configuration.md unchanged)"
        status: pass
      - kind: other
        ref: "SIF_DB_PATH=.planning/tmp/phase19/bench.db SIF_CACHE_DIR=.planning/tmp/phase19/cache python -m sif.cli.main eval --personal --bm25-only -c bench-fixture --compare .planning/phases/19-search-correctness/bench/b0.json --json --no-save -> n=100, mean=0.0, unchanged=100"
        status: pass
    human_judgment: false

duration: 9min
completed: 2026-11-15
status: complete
---

# Phase 19 Plan 05: Deterministic Pagination and Global Ranks Summary

**`--offset` now paginates `search`/`vsearch`/`query` and MCP `query`, with BM25 thresholding inside the FTS scan, one offset slice per query path, and ranks that continue 11-20 across pages while offset=0 reproduces B0 exactly**

## Performance

- **Duration:** 9 min
- **Started:** 2026-11-15T03:37:20Z
- **Completed:** 2026-11-15T03:46:43Z
- **Tasks:** 3/3
- **Files modified:** 15 (8 source/docs, 7 test)

## Accomplishments

- `sif search`, `sif vsearch`, and `sif query` gained `--offset` (`click.IntRange(min=0)`, default 0) threaded into `SearchOptions`; a negative value is rejected at parse time.
- `BM25Searcher.search` binds `1 - 1/min_score` and applies `rank >= ?` inside the FTS scan — both the collection-scoped CTE and the `--all` form — so LIMIT/OFFSET slices the already-filtered ranking and pages have no holes. The post-pagination Python skip is gone.
- Every path numbers ranks globally (`rank = offset + position`): page 2 at offset 5 carries ranks 6-10, matching overall ordering in table/JSON/CSV/XML output.
- `VectorSearcher` scales `fetch_k` with `limit+offset`, clamps it at `_MAX_FETCH_K = 2048` (a huge offset is an empty page, not unbounded KNN work), slices once, and ranks globally.
- `HybridSearcher` calls both legs with `offset=0` and `limit+offset`, fuses at that window, and applies exactly one slice — including its vector-only and BM25-only early returns. The pipeline always calls hybrid with `offset=0` and owns the caller's slice after reranking and snippets; with a reranker the pre-rerank window is `max(candidate_limit, limit+offset)` for paged requests and stays exactly `candidate_limit` at offset=0, so `top_k = limit+offset`.
- MCP `QueryInput`, `LexSearchInput`, and `VecSearchInput` carry `Field(default=0, ge=0)` offset; `QueryToolHandler` advertises it in the hand-written schema and forwards it; `SearchBackend.hybrid_search(offset=...)` places it on the `SearchOptions` used by both the pipeline and the BM25 fallback. Lex/vec tools remain unregistered for Phase 22.
- `make docs-generate` adds exactly three `--offset` rows (search/vsearch/query) and leaves `docs/configuration.md` untouched.
- B0 was re-measured on the existing scratch index: 100 paired queries, mean delta `0.0`, all 100 unchanged — no unintended ranking drift.
- New integration suite (`tests/integration/test_search_correctness.py`) builds 40 distinct single-chunk documents on the real schema + vec0 and proves page continuity for BM25/vector/hybrid plus the reranker-window cases (full/disjoint/global ranks, beyond-cap full page, within-cap concatenation, offset=0 cap preservation).

## Task Commits

Each task was committed atomically:

1. **Task 1: BM25 `--offset` end-to-end with pre-pagination min_score (tracer)** - `7a3cb27` (feat)
2. **Task 2: Vector and hybrid single-slice pagination + vsearch/query flags + continuity test** - `5101ae8` (feat)
3. **Task 3: MCP offset fields, schema sync, docs regen, and B0 no-drift proof** - `294713e` (feat)

**Plan metadata:** committed after this SUMMARY (docs: complete plan)

_Note: Task 1 ran as the plan's tracer; the auto-mode feedback gate re-ran its `<verify>` end-to-end green (32 passed) before expansion._

## Files Created/Modified

- `src/sif/search/bm25.py` - bound `rank >= 1 - 1/min_score` filter inside both FTS branches; removed post-pagination skip; global ranks
- `src/sif/search/vector.py` - `_MAX_FETCH_K = 2048`; window-aware `fetch_k`; one slice; global ranks
- `src/sif/search/hybrid.py` - `_paginate` helper; hybrid is slice owner for direct callers (incl. early returns); pipeline always passes offset=0 and slices once; offset-aware rerank window and `top_k`
- `src/sif/cli/commands/search.py` - `--offset` on search/vsearch/query; offset into `SearchOptions`
- `src/sif/mcp/protocol.py` - `offset` on QueryInput/LexSearchInput/VecSearchInput; validated limit on lex/vec
- `src/sif/mcp/handlers.py` - query schema offset property; forwarding
- `src/sif/mcp/backend.py` - `hybrid_search(offset=...)` into `SearchOptions`
- `docs/cli-reference.md` - regenerated; three `--offset` rows
- `tests/unit/search/test_bm25.py` - min_score SQL contract; real 40-doc FTS corpus pagination/threshold tests
- `tests/unit/search/test_vector.py` - fetch-k scaling/cap; real vec0 page continuity and past-end
- `tests/unit/search/test_hybrid.py` - candidate-window cases; hybrid/pipeline slice ownership tests; updated ownership identity assertions
- `tests/unit/search/test_staleness.py` - hybrid-exit enrichment now asserts the sliced page list
- `tests/unit/cli/test_search_pagination.py` - new file: `--offset` on all three commands, ranks 6-10, negative rejection
- `tests/unit/mcp/test_backend.py` - offset validation, schema, handler pass-through, backend forwarding (pipeline + fallback)
- `tests/integration/test_search_correctness.py` - new file: page continuity and reranker-window proofs

## Decisions Made

- Kept the plan's BM25 score formula `1/(1+|rank|)` and predicate `rank >= 1 - 1/min_score`; the real-corpus test pins the exact surviving rows rather than assuming a monotonic relation to term frequency.
- Clamped the vector fetch depth at 2048 so `--offset` cannot multiply KNN work; a past-the-cap page is empty by design.
- Preserved the WR-03 non-positive-limit clamp in both vector and shared `_paginate` (`max(1, limit)`).
- Kept the Phase 16 rerank semantics byte-identical at offset=0: window = `candidate_limit`, `top_k = limit`, off-path call shape unchanged except that hybrid now receives a value-equal offset-0 copy.
- MCP lex/vec inputs received validated offset fields only; tool registration stays Phase 22 per research Open Q1.
- B0 was compared on the existing scratch index rather than re-indexing: corpus fingerprint and stored checksums are untouched by this plan, and the comparison succeeded first try.

## Deviations from Plan

None - plan executed exactly as written.

Existing tests that pinned superseded ownership identities (candidate-fetch `top_k`, the pipeline rerank-enrichment list identity, and the hybrid-exit enrichment identity) were updated to the planned one-slice contract; no assertions were relaxed.

## Issues Encountered

- Real-corpus testing surfaced SQLite FTS5's rank convention: a better bm25 match is *more negative*, and `ORDER BY rank` is best-first. The plan's threshold direction (`rank >= 1 - 1/min_score`) is consistent with the preserved `1/(1+|rank|)` score formula, so the real-corpus test asserts the concrete surviving document set (`doc-2`, `doc-1`, `doc-0` for `min_score=0.23`) instead of a term-frequency-order assumption. No production behavior changed beyond the plan.

## Verification Results

- Task 1 `<verify>`: `pytest tests/unit/search/test_bm25.py tests/unit/cli/test_search_pagination.py -x --no-cov` -> 32 passed (also the tracer gate re-run)
- Task 2 `<verify>`: `pytest tests/unit/search/test_vector.py tests/unit/search/test_hybrid.py tests/integration/test_search_correctness.py -x --no-cov` -> 75 passed
- Task 3 `<verify>`: `pytest tests/unit/mcp/test_backend.py tests/unit/cli/test_search_pagination.py -x --no-cov` -> 49 passed
- Plan-level: `pytest tests/unit/search tests/unit/cli/test_search.py tests/unit/cli/test_search_pagination.py tests/unit/mcp/test_backend.py tests/integration/test_search_correctness.py -x --no-cov` -> 732 passed
- Full suite (CLAUDE.md gate): `env -u FORCE_COLOR NO_COLOR=1 pytest` -> 1961 passed, 1 skipped, coverage 95.27% (fail_under=90)
- `ruff check src tests` -> All checks passed; `ruff format --check src tests` -> 197 files already formatted
- `ty check src/sif` -> All checks passed
- `make docs-generate && git diff --exit-code docs/` -> clean; only the three `--offset` rows changed; `docs/configuration.md` unchanged
- B0 compare -> `n=100`, mean delta `0.0`, `unchanged=100`
- Dependency guard: no `pyproject.toml`/`uv.lock` change in this plan

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- CORR-03 is closed: every CLI result command and the MCP query tool accept validated offsets, every path has exactly one slice owner, and ranks are global across pages.
- Plan 19-06's per-document dedup lands on this ownership seam: vector dedup runs before the single slice, and the hybrid/pipeline slice helpers already exist.
- Plans 19-07/19-08/19-09 can measure ranking changes against B0; the offset=0 default path is proven byte-identical on the B0 query set.
- Phase 20's metadata filters compose with pagination because filtering belongs in the same pre-slice position as BM25's min_score.
- Phase 22's lex/vec tool registration inherits validated offset fields with no schema gap.
- No dependency, schema, or indexing changes; the corpus fingerprint remains `8c006123784348d1`.

---

*Phase: 19-search-correctness*
*Completed: 2026-11-15*

## Self-Check: PASSED

- All 14 key files exist on disk (8 source/docs + 6 test/verification files; `tests/unit/search/test_staleness.py` also verified).
- Commits are ancestors of HEAD: `7a3cb27`, `5101ae8`, `294713e` all found.
- Evaluation scope resolved for plan `19-05` (commits-only scope) with all three task commits.
- Plan-level verification re-run green (732 targeted; full suite 1961 passed, 1 skipped at 95.27%; ruff/format/ty clean; docs diff clean; B0 n=100, mean 0.0).
