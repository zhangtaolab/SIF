---
phase: 10-raise-pytest-coverage-to-90
plan: 07
subsystem: testing
tags: [pytest, coverage, tollgate, fail_under]

requires:
  - phase: 10-raise-pytest-coverage-to-90
    plan: 02
    provides: CLI long-tail coverage, D-06 order-independence repair.
  - phase: 10-raise-pytest-coverage-to-90
    plan: 03
    provides: Reranker + search CLI coverage.
  - phase: 10-raise-pytest-coverage-to-90
    plan: 04
    provides: Real-SQLite database coverage.
  - phase: 10-raise-pytest-coverage-to-90
    plan: 05
    provides: Core services, downloader, utils coverage.
  - phase: 10-raise-pytest-coverage-to-90
    plan: 06
    provides: Indexing + MCP coverage at 96.16% (Wave-2 final).
provides:
  - Permanent fail_under=90 gate in pyproject.toml under [tool.coverage.report].
  - Final measured TOTAL: 96.16% (5341 statements, 205 missed, 958 passed).
  - Rehearsed and recorded D-06 both-order OpenAI order independence.
affects:
  - Every future pytest invocation (local and CI) now enforces 90% line coverage on src/sif.
  - Future phases cannot regress below 90% without a failing canonical run.

actuals:
  tokens: 89
  tasks: 2
  commits: 2
plan_head_before: f4ff8fa31913debed66a8eee2ce88f295b3ccb9a
plan_head_after: 3867b87cb28402be869fb515b6b4f50ab2c37bf9

tech-stack:
  added: []
  patterns: [adaptive measured tollgate, permanent coverage gate (Pattern 6)]

key-files:
  created: []
  modified:
    - pyproject.toml

key-decisions:
  - "Zero long-tail tests required: Wave-2 combined TOTAL already 96.16% (>=90%), so D-05 did not trigger and no candidate file was touched."
  - "Landed [tool.coverage.report] fail_under=90 LAST per D-04/Pattern 6, after the gate rehearsal proved >=90% with no config."
  - "Did not add exclude_lines/exclude_also, did not enable --cov-branch, did not introduce any business-logic pragma."

patterns-established:
  - "Pattern 6 confirmed: rehearse the gate numerically, then land fail_under as the only coverage config change."

requirements-completed: [T-10-1]

coverage:
  - id: D1
    description: Canonical full suite and numeric coverage report --fail-under=90 pass before any pyproject change (Task 1 tracer rehearsal).
    requirement: T-10-1
    verification:
      - kind: integration
        ref: "env -u FORCE_COLOR NO_COLOR=1 pytest --cov=src/sif: 958 passed, 0 failed"
        status: pass
      - kind: other
        ref: "python -m coverage report --fail-under=90 exit 0; --format=total reports 96"
        status: pass
      - kind: other
        ref: "pyproject assertion: no fail_under / exclude_lines / exclude_also / --cov-branch present before Task 2"
        status: pass
    human_judgment: false
  - id: D2
    description: D-06 isolated + forward/reverse OpenAI order probes remain green with all Wave-2 tests present.
    requirement: T-10-1
    verification:
      - kind: integration
        ref: "pytest tests/unit/embedding/test_openai_embedder.py -q: 18 passed"
        status: pass
      - kind: integration
        ref: "pytest tests/unit/embedding/test_factory.py tests/unit/embedding/test_openai_embedder.py -q: 27 passed (forward)"
        status: pass
      - kind: integration
        ref: "pytest tests/unit/embedding/test_openai_embedder.py tests/unit/embedding/test_factory.py -q: 27 passed (reverse)"
        status: pass
    human_judgment: false
  - id: D3
    description: Permanent [tool.coverage.report] fail_under=90 gate lands and the canonical run exits 0 under it.
    requirement: T-10-1
    verification:
      - kind: other
        ref: "tomllib parse: report.fail_under == 90; exclude_lines and exclude_also absent"
        status: pass
      - kind: integration
        ref: "env -u FORCE_COLOR NO_COLOR=1 pytest --cov=src/sif exits 0; prints 'Required test coverage of 90.0% reached. Total coverage: 96.16%'"
        status: pass
      - kind: other
        ref: "python -m coverage report --format=total: 96"
        status: pass
    human_judgment: false
  - id: D4
    description: Quality battery (ruff check, ruff format --check) and generator-owned docs drift check are green.
    requirement: T-10-1
    verification:
      - kind: other
        ref: "ruff check src tests: All checks passed!; ruff format --check src tests: 150 files already formatted"
        status: pass
      - kind: other
        ref: "make docs-generate && git status --porcelain -- docs/cli-reference.md docs/configuration.md: empty"
        status: pass
    human_judgment: false

duration: 3min
completed: 2026-11-05
status: complete
---

# Phase 10 Plan 07: Coverage Tollgate and Permanent fail_under Gate Summary

**Rehearsed the 90% gate at TOTAL 96.16% with zero long-tail additions and landed `[tool.coverage.report] fail_under = 90` as the single pyproject coverage config change — the canonical suite now exits 0 only when src/sif line coverage stays at or above 90%.**

## Performance

- **Duration:** 3 minutes (198 seconds)
- **Started:** 2026-11-05T20:22:38Z
- **Completed:** 2026-11-05T20:25:56Z
- **Tasks:** 2/2
- **Files modified:** 1 (`pyproject.toml`); zero test files touched.
- **Realized diff:** 3 insertions, 0 deletions (356 diff characters; ~89 chars/4 actual tokens).
- **Full suite:** 958 passed, 0 failed in 10.83 seconds (under the active gate).

## Accomplishments

- Rehearsed the T-10-1 gate BEFORE any config change: `pytest --cov=src/sif` + `coverage report --fail-under=90` both exited 0 at TOTAL 96.16%.
- Confirmed D-05 did not trigger — Wave-2 combined coverage was already ≥90%, so no long-tail test file was opened, no testability refactor was needed, and no D-02 deletion was considered.
- Re-ran the tracer feedback gate (auto mode) end-to-end before Task 2: full suite + `--fail-under=90` + `--format=total` all green on the second pass.
- Re-ran all three D-06 order probes (isolated OpenAI, forward factory→OpenAI, reverse OpenAI→factory) — all green at 18/27/27 passed.
- Added exactly one TOML section — `[tool.coverage.report]` with `fail_under = 90` — placed immediately after `[tool.pytest.ini_options]`. No `exclude_lines`, no `exclude_also`, no `--cov-branch`, no pragma annotations anywhere.
- Verified the gate is active: pytest output includes `Required test coverage of 90.0% reached. Total coverage: 96.16%`.
- Quality battery: `ruff check src tests` clean; `ruff format --check src tests` reports 150 files already formatted.
- `make docs-generate` regenerated both generator-owned surfaces; `git status --porcelain -- docs/cli-reference.md docs/configuration.md` is empty (no drift).

## Final Measured Coverage

| Metric | Value |
|---|---:|
| Statements (src/sif) | **5341** |
| Missed | **205** |
| TOTAL line coverage | **96.16%** (displayed 96%) |
| Tests passed | **958** |
| Tests failed | **0** |
| Permanent gate | **`fail_under = 90`** (active, satisfied) |

Wave progression for the phase: 78% (pre) → 81.48% (10-01 post-deletion baseline) → 85.34% (10-02) → 89.x (10-03) → 92.x (10-04) → 93.48% (10-05) → 96.16% (10-06) → **96.16% with permanent gate (10-07)**.

## D-05 Long-Tail Decision Record

The plan's tracer action ranks files by the actual Miss column and applies D-05 (refactor → D-02 deletion → meaningful tests) only if `--fail-under=90` fails. It passed on the first rehearsal. Therefore:

- **Files touched for long-tail coverage:** none.
- **Candidate files left untouched** (per plan): `tests/unit/cli/test_index.py`, `test_bench.py`, `test_pull.py`, `test_context.py`, `tests/unit/search/test_hybrid.py`, `test_term_match.py`, `test_rrf.py`, `test_snippets.py`, `test_bm25.py`, `tests/unit/config/test_settings.py`.
- **D-02 deletions considered:** none (no new zero-reference code was identified during this plan; out of scope without a triggering gap).
- **Testability refactors:** none required.
- **Pragma annotations added:** none.

## D-06 Both-Order Re-Run Result

| Probe | Command | Result |
|---|---|---|
| Isolated OpenAI | `pytest tests/unit/embedding/test_openai_embedder.py -q` | **18 passed** |
| Forward (factory → openai) | `pytest tests/unit/embedding/test_factory.py tests/unit/embedding/test_openai_embedder.py -q` | **27 passed** |
| Reverse (openai → factory) | `pytest tests/unit/embedding/test_openai_embedder.py tests/unit/embedding/test_factory.py -q` | **27 passed** |

D-06 closure stands: no order dependence reintroduced by Wave-2 or Wave-3 work.

## Task Commits

1. **Task 1: Rehearse the 90% gate with zero long-tail additions** — `848f68d` (test; empty atomic verification commit because Task 1 changed no files — same precedent as 10-01 Task 2).
2. **Task 2: Land permanent fail_under=90 coverage gate** — `3867b87` (test).

## Files Created/Modified

- `pyproject.toml` — added `[tool.coverage.report]` block with `fail_under = 90` immediately after `[tool.pytest.ini_options]`. No other key touched.
- `.planning/phases/10-raise-pytest-coverage-to-90/10-07-SUMMARY.md` — this summary.

No test files, no source files, no generator-owned documents, no `.coveragerc`, no CI workflow changes.

## Decisions Made

- Skipped all long-tail work because the measured gate already passed at 96.16% (>= 90%); per the plan, this is the success path, not a shortcut.
- Kept `pyproject.toml` strictly minimal: only the `fail_under` key in the new report section. Did not introduce `exclude_lines`, `exclude_also`, or branch coverage — all three would change the metric or replace defaults (Pitfall 6).
- Left the research's out-of-scope CI workflow decision intact: the gate is configured at the pytest layer and therefore already applies wherever `pytest` runs.
- Recorded the gate rehearsal as an empty atomic commit so the per-task commit contract holds even when Task 1 legitimately changes no files.

## Deviations from Plan

None - plan executed exactly as written. Task 1's adaptive action explicitly permits the zero-long-tail outcome when `--fail-under=90` passes on the first rehearsal.

## Issues Encountered

- The full suite emitted 57 warnings (predominantly pre-existing SQLite `ResourceWarning` messages). They do not fail the suite and are outside this plan's scope.
- No authentication gates, no package installs, no blockers, no known stubs, no skipped tests, no unrun verification commands, no generator-owned doc edits, no user setup.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

**Phase 10 complete.** All seven plans (10-01 … 10-07) are landed. T-10-1 is now satisfiable and is being marked complete by this plan's `requirements.mark-complete` step (shared-ID gate releases on the last plan). The 90% line-coverage contract is now permanent: any future PR that drops `src/sif` line coverage below 90% will fail the canonical `env -u FORCE_COLOR NO_COLOR=1 pytest --cov=src/sif` invocation locally and in CI. No follow-up plans, blockers, or deferred items from this phase.

## Self-Check: PASSED

- `pyproject.toml` exists at the repo root and parses cleanly via `tomllib`; `[tool.coverage.report].fail_under == 90`; `exclude_lines` and `exclude_also` are absent.
- Both task commits are ancestors of HEAD: `848f68d` (Task 1) and `3867b87` (Task 2). Measured ledger: 2 commits from `f4ff8fa` through `3867b87`.
- Task 1 acceptance: canonical suite + `--fail-under=90` + `--format=total` PASS before pyproject change; pyproject pre-Task-2 assertion PASS; all three D-06 probes PASS.
- Task 2 acceptance: TOML assertion PASS; canonical suite under active gate PASS with "Required test coverage of 90.0% reached. Total coverage: 96.16%"; `ruff check` PASS; `ruff format --check` PASS (150 files); `make docs-generate` produced no porcelain drift on either generator-owned doc.
- FINAL measured values: TOTAL 96.16% (5341 statements, 205 missed, 958 passed, 0 failed).
- No long-tail test files were modified; the candidate list in the plan remains untouched.
- No business-logic `# pragma: no cover` was added anywhere in this plan.

---
*Phase: 10-raise-pytest-coverage-to-90*
*Completed: 2026-11-05*
