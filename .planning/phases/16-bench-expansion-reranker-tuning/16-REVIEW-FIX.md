---
phase: 16-bench-expansion-reranker-tuning
fixed_at: 2026-11-08T16:34:55Z
review_path: .planning/phases/16-bench-expansion-reranker-tuning/16-REVIEW.md
iteration: 2
findings_in_scope: 0
fixed: 0
skipped: 0
status: all_fixed
---

# Phase 16: Code Review Fix Report

**Fixed at:** 2026-11-08T16:34:55Z
**Source review:** `.planning/phases/16-bench-expansion-reranker-tuning/16-REVIEW.md`
**Iteration:** 2

**Summary:**
- Findings in scope: 0 (fix_scope `critical_warning`; REVIEW.md carries 0 Critical, 0 Warning)
- Fixed: 0
- Skipped: 0

No finding was in scope for this iteration. The iteration-2 re-review confirmed all
four prior blocking findings (CR-01, WR-01, WR-02, WR-03) are resolved by commits
`7d5d788`, `77e6511`, `3562dac`, `62aeacb`, `f3a9700`, and reported 0 Critical / 0
Warning remaining. All six open findings are Info severity, which `critical_warning`
scope excludes; they remain in REVIEW.md for disposition by the human. No code
changes were made and no commits were created this iteration.

## Out-of-Scope Findings (Info)

### IN-01: `_sort_and_build_results` drops `vectors_stale` when rebuilding SearchResult

**File:** `src/sif/search/rerank.py:52-66`
**Disposition:** out of scope (info) — not a live bug on the pipeline path; public-API
hardening for direct `reranker.rerank()` callers.

### IN-02: Stray class docstring inside `TestCrossEncoderRerankerLoad`

**File:** `tests/unit/inference/test_reranker.py:305`
**Disposition:** out of scope (info) — pre-existing missing class header; tests still
collect and pass under the merged class.

### IN-03: `Qwen3Reranker.load` duplicates model-loading body across quiet/non-quiet branches

**File:** `src/sif/search/rerank.py:327-357`
**Disposition:** out of scope (info) — pre-existing duplication, maintenance risk only.

### IN-04: Benchmarking doc gaps (grade-1 legend; `SIF_RERANK_ENABLED=1` scoping)

**File:** `docs/benchmarking.md:56,147`
**Disposition:** out of scope (info) — documentation wording; latent rather than wrong.

### IN-05: `bench` no-index warning prints to stdout and exits 0 under `--json`

**File:** `src/sif/cli/commands/bench.py:617-619`
**Disposition:** out of scope (info) — pre-existing line (predates phase diff base),
matches the established CLI-wide pattern, pinned by `test_bench_no_index`; reviewer
recommends a codebase-wide follow-up rather than a Phase 16 fix.

### IN-06: `query_cmd` reranker-unavailable degradation warning targets stdout `console`

**File:** `src/sif/cli/commands/search.py:917-922`
**Disposition:** out of scope (info) — pre-existing and currently production-unreachable
(no eager optional-backend imports in `create_reranker`); latent trap only.

## Verification

No code was modified this iteration, so no gates were re-run. Verification was limited
to a bounded re-read of the two newly-surfaced finding sites (`src/sif/cli/commands/bench.py:617-619`,
`src/sif/cli/commands/search.py:917-922`) to confirm the reviewer's Info classifications
matched the current code — both confirmed; no misclassified Critical/Warning was found.
All checks ran in the **main checkout** (`workflow.use_worktrees=false` in
`.planning/config.json` — no isolated worktree was created). Phase-gate status is as
reported by the re-review itself: drift gate `OK: 151 files`, ruff/ty clean, full suite
1501 passed / 1 skipped, coverage 94.95%.

---

_Fixed: 2026-11-08T16:34:55Z_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 2_
