---
phase: 16-bench-expansion-reranker-tuning
plan: "06"
subsystem: search
tags: [rerank, relative-threshold, candidate-limit, over-fetch, rrf, search-pipeline]

# Dependency graph
requires:
  - phase: 16-bench-expansion-reranker-tuning (Plan 02)
    provides: Settings.rerank_relative_threshold (Pydantic (0,1]) and the clamped
      resolve_candidate_limit (5..50) every CLI path routes candidate_limit through;
      rerank is opt-in (D-12), so this plan only shapes the enabled path
provides:
  - relative_threshold kwarg (default 0.0) on LlamaCppReranker, CrossEncoderReranker and
    Qwen3Reranker, forwarded at every _sort_and_build_results call site
  - create_reranker forwards settings.rerank_relative_threshold to every backend with an
    isinstance(float|int) guard (MagicMock settings -> 0.0)
  - SearchPipeline over-fetch to max(limit + offset, candidate_limit) on the rerank-on path
    (fetch_options via dataclasses.replace reaching hybrid.search and the cross-query fuse)
  - Composition proofs pinning cap -> threshold -> top_k ordering and off-path equivalence
affects: [16-04 bench rerank-on state, 16-05 held-out snapshot, docs/search-algorithms.md]

# Actuals (#2632) — same estimateTokens scale (chars/4 over the realized diff).
actuals:
  tokens: 6906  # 27623 diff chars / 4 over base 2222740..HEAD (5 files, +473/-9)
  tasks: 3
  commits: 4
  plan_head_before: 2222740a52ee658f694fe6cc4cc491ab4e8943ac
  plan_head_after: 6bac5bfbd61601f700ff11425ede223c0877f5eb

# Tech tracking
tech-stack:
  added: []  # stdlib dataclasses.replace only; zero new dependencies
  patterns:
    - "Threshold filters live in the shared post-normalization helper (_sort_and_build_results), never per backend"
    - "Over-fetch rides SearchOptions.limit via dataclasses.replace — no searcher signature changes (research Pattern 5)"
    - "Settings -> factory forwarding resolves defensively: isinstance(float|int) after getattr so test mocks never leak (Pitfall 10)"

key-files:
  created: []
  modified:
    - src/sif/search/rerank.py
    - src/sif/search/hybrid.py
    - tests/unit/inference/test_reranker.py
    - tests/unit/search/test_rerank.py
    - tests/unit/search/test_hybrid.py

key-decisions:
  - "Threshold = raw >= on top_score * relative_threshold after the descending stable sort and before [:top_k] — exact half retained, no epsilon, top1 always survives; 0.0 default keeps direct construction byte-identical"
  - "Over-fetch = replace(options, limit=max(limit + offset, candidate_limit)) only when a reranker exists; the off path passes the caller's options object by identity (pinned by an is-assert plus the SC1 golden snapshot)"
  - "create_reranker resolves rerank_relative_threshold with isinstance(value, float | int) after getattr — a wide-open MagicMock settings object falls back to 0.0 instead of leaking into the scoring path"
  - "PLR0913 noqa on LlamaCppReranker.__init__ and CrossEncoderReranker.__init__ matching Qwen3Reranker's existing suppression (sixth constructor parameter)"

patterns-established:
  - "Pattern: enabled-path cost bounds compose as cap (pipeline slice) -> threshold (reranker filter) -> top_k (truncation); each layer pinned by its own test plus one end-to-end ordering proof"
  - "Pattern: identity assertion (`call_args[0][1] is options`) proves a no-copy passthrough where value equality cannot"

requirements-completed: [QUAL-05]

coverage:
  - id: D1
    description: "Relative threshold in the rerank scoring path: >= top1*alpha retention after the descending sort and before top_k truncation (exact half kept, no epsilon); 0.0 reproduces the pre-change output; kwarg on all three backends; create_reranker forwards the setting to every backend with a 0.0 fallback for MagicMock settings"
    requirement: QUAL-05
    verification:
      - kind: unit
        ref: "tests/unit/search/test_rerank.py#TestRelativeThreshold (5 tests incl. end-to-end CrossEncoder + equal-score determinism)"
        status: pass
      - kind: unit
        ref: "tests/unit/inference/test_reranker.py#TestCreateReranker/test_create_reranker_forwards_relative_threshold + test_create_reranker_magic_settings_threshold_falls_back_to_zero"
        status: pass
    human_judgment: false
  - id: D2
    description: "Candidate cap that binds: pipeline over-fetches to max(limit + offset, candidate_limit) reaching hybrid.search and the cross-query rrf.fuse; with 20 indexed docs, limit=3 and candidate_limit=20 the reranker receives 20 candidates with top_k=3"
    requirement: QUAL-05
    verification:
      - kind: unit
        ref: "tests/unit/search/test_hybrid.py#TestCandidateFetch/test_candidate_fetch_reranker_receives_full_cap + test_candidate_fetch_limit_is_max_of_limit_offset_and_cap + test_candidate_fetch_cross_query_fuse_uses_fetch_limit (real 20-doc sqlite-vec DB)"
        status: pass
    human_judgment: false
  - id: D3
    description: "Composition and off-path equivalence: cap -> threshold -> top_k ordering with equal scores and min(top_k, survivors) final count; reranker=None passes the caller's options object by identity and reproduces the SC1 pre-change golden snapshot byte-for-byte"
    requirement: QUAL-05
    verification:
      - kind: unit
        ref: "tests/unit/search/test_hybrid.py#TestRerankComposition (3 tests) + TestCandidateFetch/test_candidate_fetch_off_path_matches_sc1_snapshot + TestHybridSC1PipelineGolden"
        status: pass
    human_judgment: false

# Metrics
duration: 12 min
completed: 2026-11-08
status: complete
---

# Phase 16 Plan 06: Rerank Runtime Scoring Summary

**Enabled-rerank path bounded by a real cap (over-fetch to max(limit+offset, candidate_limit)) and a relative threshold (>= top1*alpha, exact half kept, before top_k) while the off path stays byte-identical to the SC1 golden**

## Performance

- **Duration:** 12 min
- **Started:** 2026-11-08T14:36:56Z
- **Completed:** 2026-11-08T14:48:46Z
- **Tasks:** 3 (Task 2 executed as TDD: RED -> GREEN, REFACTOR not needed)
- **Files modified:** 5

## Accomplishments

- `_sort_and_build_results(results, scores, top_k, relative_threshold=0.0)`: after the descending stable sort, when the threshold is positive and the top score is positive, candidates scoring `>= top1 * alpha` are kept before `[:top_k]`; raw IEEE-754 comparison, no epsilon, so a score exactly equal to the cutoff (an exact half of 0.9) is retained and top1 always survives (D-11)
- `relative_threshold: float = 0.0` kwarg on `LlamaCppReranker`, `CrossEncoderReranker` and `Qwen3Reranker` — stored and forwarded at all three `_sort_and_build_results` call sites; `# noqa: PLR0913` on the two constructors gaining a sixth parameter, matching Qwen3Reranker's existing suppression; every existing init/rerank test passes unchanged
- `create_reranker` forwards `settings.rerank_relative_threshold` to every backend after an `isinstance(value, float | int)` guard, so a wide-open MagicMock settings object resolves to 0.0 rather than leaking a MagicMock into the scoring path (research Pitfall 10)
- `SearchPipeline.search` over-fetches when a reranker exists: `fetch_options = replace(options, limit=max(options.limit + options.offset, options.candidate_limit))` reaches every `hybrid.search(q, ...)` in the variant loop and the cross-query `rrf.fuse(..., fetch_options.limit, ...)`; candidates still slice at `options.candidate_limit` and rerank at `top_k=options.limit` (D-10 / research Pitfall 1 — the cap was a no-op above limit before)
- Off path provably unchanged: with `reranker=None` the searchers receive the caller's options object **by identity** (no replace copy) and the pipeline output reproduces the SC1 pre-change golden snapshot field-for-field; the plan's off-path equivalence contract and 16-02/16-03's tests all stay green
- Composition proofs pin the layer ordering end-to-end: cap hands exactly `candidate_limit` candidates, the threshold keeps `>= top1 * alpha` (with equal scores in the candidate list), the final count is `min(top_k, survivors)`, and equal-score ordering is deterministic across repeated rerank runs

## Task Commits

Each task was committed atomically:

1. **Task 1: Relative threshold end-to-end in the rerank scoring path (tracer)** - `c5f866f` (feat; tracer verify re-run passed under auto mode -> expanded without checkpoint)
2. **Task 2 RED: failing candidate-cap fetch tests** - `73eadce` (test; JUnit RED evidence classified RED_EVIDENCE_OK)
3. **Task 2 GREEN: over-fetch to max(limit + offset, candidate_limit)** - `282e72b` (feat; includes the ARG002 spy fix; REFACTOR skipped — no cleanup needed)
4. **Task 3: cap/threshold/top_k composition and ordering proofs** - `6bac5bf` (test)

**Plan metadata:** see the docs(16-06) close-out commit (SUMMARY + STATE + ROADMAP + REQUIREMENTS)

## Files Created/Modified

- `src/sif/search/rerank.py` - relative_threshold filter in `_sort_and_build_results`; kwarg + storage on all three rerankers; factory forwarding with the isinstance guard
- `src/sif/search/hybrid.py` - `dataclasses.replace` fetch_options over-fetch on the rerank-on path (variant loop + cross-query fuse); off path untouched
- `tests/unit/search/test_rerank.py` - TestRelativeThreshold: exact-half retention, 0.0/1.0 boundaries, byte-identical-at-0.0, before-top_k ordering, end-to-end CrossEncoder, equal-score determinism
- `tests/unit/inference/test_reranker.py` - TestCreateReranker: parametrized forwarding to gguf / sentence_transformers / Qwen3 backends + MagicMock 0.0 fallback
- `tests/unit/search/test_hybrid.py` - TestCandidateFetch (real 20-doc sqlite-vec DB cap proof, fetch-limit observability, fuse limit, off-path SC1 snapshot) + TestRerankComposition (ordering, survivors-below-top_k, off-path identity) + `_SpyReranker`/`_ThresholdRerankSpy`

## Decisions Made

- The threshold filter guards on `scored and relative_threshold > 0.0 and scored[0][1] > 0.0` exactly as planned: a non-positive top score disables the cutoff (unreachable in practice since all three backends sigmoid-normalize to (0,1), but the guard keeps the helper total)
- Test placement followed each file's existing purpose rather than the plan's file-list order: behavior/threshold tests extend `test_rerank.py` (home of `TestRerankerBehavior`) while factory-forwarding tests extend `test_reranker.py` (home of `TestCreateReranker`) — both files were in the plan's files list
- The 20-doc cap proof uses a real in-memory schema+FTS+vec0 DB (SC1 `_build_db` style) because a mocked searcher cannot detect the over-fetch — the mock ignores `limit` and would hand the spy 20 candidates even pre-change; the fetch limit is instead observed on the options object `bm25.search` receives, and end-to-end on the real SQL-LIMIT
- `candidate_limit` is treated as already validated in the pipeline (no duplicated bounds): every CLI construction path resolves through 16-02's clamped `resolve_candidate_limit`, so `-C 200` puts 50 into `SearchOptions` before the pipeline ever runs

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] ruff ARG002 on the spy reranker's `query` parameter**
- **Found during:** Task 2 (GREEN gates)
- **Issue:** `_SpyReranker.rerank(query, results, top_k)` must match the reranker call signature but never read `query`, tripping ruff's unused-argument rule and failing the plan's `ruff check src tests` gate
- **Fix:** The spy records `self.query = query` (genuinely useful spy behavior) instead of suppressing the rule
- **Files modified:** tests/unit/search/test_hybrid.py
- **Verification:** `ruff check src tests` clean; all 6 candidate_fetch/snapshot tests pass
- **Committed in:** 282e72b (Task 2 GREEN commit)

---

**Total deviations:** 1 auto-fixed (1 blocking)
**Impact on plan:** Lint-only fix inside test scaffolding; no behavioral or scope change.

## Issues Encountered

None beyond the deviation above. Task 2's RED failed for exactly the intended reasons (spy.seen 3 != 20 on the real-DB cap proof; bm25.search passed options.limit=3 instead of the fetch limit 20; rrf.fuse positional limit 3 instead of 20) and GREEN passed first try, as did Tasks 1 and 3.

## TDD Gate Compliance

Task 2 (tdd="true") executed RED -> GREEN with REFACTOR skipped (no cleanup needed):

- RED `73eadce` (test) precedes GREEN `282e72b` (feat) in ancestry order; no gate violations
- RED evidence: `.planning/tmp/tdd-red-16-06.json` (JUnit XML embedded, 3 planned assertion failures, exit 1) validated by `gsd_run check tdd-red-evidence` as RED_EVIDENCE_OK with target `test_candidate_fetch_reranker_receives_full_cap`; semantic assessment recorded in the evidence file and in its `actual` field
- The 3 passing tests in the RED run are the SC1 golden pins that must hold pre- and post-change (the off-path regression pin passing pre-change is by design, not unexpected green — the target tests all failed)

## Authentication Gates

None — no external services or credentials involved.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- The enabled rerank path is now bounded: rerank is opt-in (16-02), the candidate cap binds via over-fetch + slice (this plan), and the relative threshold filters before top_k — QUAL-05's runtime semantics are complete pending 16-04/16-05's measurement and evidence plans
- 16-04 (bench) can measure the rerank-on state through the real bounded path; its `-C` resolves through the shared clamp so every rerank invocation stays within 5..50
- 16-05's docs work should describe the cap -> threshold -> top_k ordering in `docs/search-algorithms.md` (narrative, hand-edited)
- No settings or CLI surface changed here, so `docs/configuration.md` / `docs/cli-reference.md` remain current

## Verification Results

- `env -u FORCE_COLOR NO_COLOR=1 python -m pytest tests/unit/search/test_rerank.py tests/unit/inference/test_reranker.py -k "threshold or rerank" -x --no-cov` — 59 passed (Task 1 tracer verify; re-run at the tracer gate: 59 passed, exit 0)
- `env -u FORCE_COLOR NO_COLOR=1 python -m pytest tests/unit/search/test_hybrid.py -k "candidate_fetch or snapshot" -x --no-cov` — 6 passed (Task 2 GREEN verify)
- `env -u FORCE_COLOR NO_COLOR=1 python -m pytest tests/unit/search/test_hybrid.py tests/unit/search/test_rerank.py -x --no-cov` — 51 passed (Task 3 verify)
- `env -u FORCE_COLOR NO_COLOR=1 python -m pytest tests/unit/search/test_hybrid.py tests/unit/search/test_rerank.py tests/unit/inference/test_reranker.py -x --no-cov` — 96 passed (plan verification)
- `env -u FORCE_COLOR NO_COLOR=1 python -m pytest` (full suite) — 1447 passed, 1 skipped (pre-existing platform skip), coverage 94.92% (fail_under=90 gate green)
- `ruff check src tests && ruff format --check src tests` — clean (185 files formatted)
- `ty check src/sif` — 0 diagnostics
- Acceptance criteria per task verified: exact-half retention (`assert [r.document_id ...] == ["top", "half"]` on scores [0.44, 0.9, 0.45]), threshold-before-truncation, 0.0 byte-identical, factory forwarding + MagicMock fallback, `# noqa: PLR0913` on both six-param constructors, spy receives 20 with top_k=3, fetch limit max(limit+offset, cap), off-path golden unchanged, no existing golden assertion relaxed

## Self-Check: PASSED

All five modified files plus the SUMMARY exist on disk; all four task commits (c5f866f, 73eadce, 282e72b, 6bac5bf) are ancestors of HEAD; commit count measured from the plan ledger (base 2222740) is 4, matching the Task Commits section.
