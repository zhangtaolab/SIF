---
phase: 05-agent-context-experience
plan: "09"
subsystem: context-write-path
tags: [context, prune, normalization, gap-closure, tdd]
requires:
  phase: 05-08
  provides:
    - "normalize_path shared same-file definition (sif.utils.paths)"
provides:
  - "canonical context add path writes (normalize_path at write time, CTX-01)"
  - "dual-form upsert self-heal merging legacy verbatim rows via ContextRepository.update_target"
  - "normalize_path-aligned delete_orphaned_paths (prune stops deleting valid contexts, CTX-02)"
  - "real-SQL prune/update_target regression suite (tests/unit/database/test_repositories.py)"
affects:
  - src/sif/cli/commands/context.py
  - src/sif/database/repositories.py
  - tests/unit/cli/test_context.py
  - tests/unit/database/test_repositories.py
actuals:
  tokens: 5387
  tasks: 2
  commits: 4
  plan_head_before: 67aad26cf623cebd63cd8b62c421ec4695e246fb
tech-stack:
  added: []
  patterns:
    - "Python-side normalized-set comparison replaces SQL NOT IN where SQL cannot express realpath"
    - "dual-form upsert (canonical lookup, then verbatim lookup + re-point) heals legacy rows without a bulk migration"
key-files:
  created:
    - tests/unit/database/test_repositories.py
  modified:
    - src/sif/cli/commands/context.py
    - src/sif/database/repositories.py
    - tests/unit/cli/test_context.py
    - .planning/phases/05-agent-context-experience/deferred-items.md
key-decisions:
  - "context add path stores normalize_path(target); legacy verbatim rows merge via update_target on explicit re-add — no bulk backfill migration (re-normalize-on-read + merge-on-re-add)"
  - "delete_orphaned_paths compares normalize_path on both sides in Python; raw-string NOT IN SQL removed entirely"
  - "D-09 dual validation and D-02 name-first collection resolution preserved untouched"
patterns-established:
  - "write/prune/read share one same-file definition imported from sif.utils.paths.normalize_path"
requirements-completed:
  - CTX-01
  - CTX-02
coverage:
  - id: cov-1
    description: "ContextRepository.update_target(context_id, target_id) -> bool — parameterized UPDATE re-pointing target_id"
    requirement: CTX-02
    verification:
      - kind: unit
        ref: "tests/unit/database/test_repositories.py::TestUpdateTargetRealSQL::test_update_target_round_trip"
        status: pass
      - kind: unit
        ref: "tests/unit/database/test_repositories.py::TestUpdateTargetRealSQL::test_update_target_unknown_id_returns_false"
        status: pass
    human_judgment: false
  - id: cov-2
    description: "delete_orphaned_paths rewritten with normalize_path on both sides — symlink-mismatched contexts survive prune, true orphans still die, count semantics unchanged"
    requirement: CTX-02
    verification:
      - kind: unit
        ref: "tests/unit/database/test_repositories.py::TestDeleteOrphanedPathsRealSQL (5 tests incl. THE CR-02 regression test_prune_preserves_symlink_mismatched_context)"
        status: pass
      - kind: integration
        ref: "live CLI: alias-form legacy row + canonical row over an indexed symlinked vault -> 'Pruned 0', context list shows both"
        status: pass
    human_judgment: false
  - id: cov-3
    description: "context add path stores canonical resolved form; dual-form upsert self-heals legacy verbatim rows (merge, never duplicate); collection/global untouched"
    requirement: CTX-01
    verification:
      - kind: unit
        ref: "tests/unit/cli/test_context.py::TestContextAddNormalizedPaths (5 tests)"
        status: pass
      - kind: integration
        ref: "live CLI: context add via alias form stored /private/... resolved target and echoed it in the success message"
        status: pass
    human_judgment: false
  - id: cov-4
    description: "Real-SQL prune/update_target test suite against production DDL, no sqlite-vec dependency"
    requirement: CTX-02
    verification:
      - kind: unit
        ref: "env -u FORCE_COLOR NO_COLOR=1 pytest tests/unit/database/test_repositories.py -> 7 passed, 0 failed, 0 skipped"
        status: pass
    human_judgment: false
  - id: cov-5
    description: "CLI normalized-write test class (alias store, home expansion, self-heal merge, canonical re-add, type guard)"
    requirement: CTX-01
    verification:
      - kind: unit
        ref: "env -u FORCE_COLOR NO_COLOR=1 pytest tests/unit/cli/test_context.py -> 21 passed (16 pre-existing + 5 new)"
        status: pass
    human_judgment: false
duration: 13min
started: "2026-09-07T03:59:09Z"
completed: "2026-09-07T04:12:29Z"
status: complete
---

# Phase 05 Plan 09: Write-Side Path Normalization and Prune Alignment Summary

Canonicalized `context add path` targets (normalize_path + dual-form upsert self-heal via new `update_target()`) and rewrote `delete_orphaned_paths()` to compare normalize_path on both sides, closing the CR-02 data-loss defect where prune silently destroyed valid symlink-mismatched contexts.

## Performance

- **Duration:** 13min (started 2026-09-07T03:59:09Z, completed 2026-09-07T04:12:29Z)
- **Tasks:** 2/2 completed
- **Files:** 3 code/test files modified, 1 test file created, 1 planning file updated
- **Commits:** 4 production commits (measured `git rev-list --count 67aad26..HEAD`); plan estimate was 30000 tokens vs 5387 actual — the estimate's low confidence was warranted; the shared-helper groundwork from 05-08 made both tasks smaller than planned.

## Accomplishments

- **Canonical write path (CTX-01 / WR-02):** `context add path` now stores `normalize_path(target)` — the resolved absolute form that byte-matches `documents.path` — through an explicit `elif type == "path":` branch. The success/updated message echoes the canonical form so users see the spelling that will actually match.
- **Dual-form upsert self-heal (CTX-02 adjacency edge):** when the canonical lookup misses but a legacy row holds the verbatim typed form, `repo.update_target(existing.id, actual_target)` re-points it to canonical and content refreshes through the existing update path — one row per file, never a duplicate. Fires only on explicit re-add; no bulk migration ever runs (the 05-VERIFICATION item-2 "re-normalize on read" choice, preserved).
- **Prune alignment (CTX-02 / CR-02):** `delete_orphaned_paths()` reads `SELECT path FROM documents` into a normalized Python set, normalizes each path context's target through the SAME `normalize_path`, and deletes only true orphans through the existing `delete()`. The raw-string `NOT IN` SQL is gone (grep count 0) — SQL cannot call realpath, so any SQL-set comparison would reintroduce the defect.
- **Regression proof:** the CR-02 live-falsified scenario (document stored resolved, context stored alias) now returns 0 deletions and the row survives — proven in unit (real in-memory SQLite with production DDL) AND live (scratch SIF index, symlinked vault, legacy verbatim row injected, `sif context prune` → "Pruned 0", `sif search search --json` shows the description, completing the loop with 05-08's read side).
- **Untouched by design:** D-09 dual validation (click.Choice + CHECK constraint, both grep-verified), D-02 name-first collection-to-UUID resolution, global literal "global" — pinned by a guard test proving `normalize_path` is never invoked for those types.

## TDD Gate Compliance

Both tasks ran strict RED → GREEN with persisted, tool-validated RED evidence (`gsd-tools check tdd-red-evidence` → `RED_EVIDENCE_OK`):

| Task | RED commit | RED evidence | GREEN commit | Refactor |
|------|-----------|--------------|--------------|----------|
| 1 — canonical context add | `2df0ab9` test(05-09) | 4 failed / 1 passed (alias store, home expand, self-heal, canonical re-add) | `551e41f` feat(05-09) | not needed — minimal implementation |
| 2 — prune alignment | `b557877` test(05-09) | 1 failed / 6 passed (CR-02 preserve test) | `2e25ea1` feat(05-09) | not needed — minimal implementation |

Evidence records persisted at `.planning/tmp/05-09-tdd/task1-red-record.json` and `task2-red-record.json`.

## Task Commits

| Task | Commit | Type | Description |
|------|--------|------|-------------|
| 1 | 2df0ab9 | test | failing tests for canonical context add path targets |
| 1 | 551e41f | feat | normalize path targets at context add with dual-form upsert self-heal |
| 2 | b557877 | test | failing real-SQL test for prune symlink-mismatch preservation |
| 2 | 2e25ea1 | feat | align delete_orphaned_paths with search normalization |

## Files Created/Modified

- `src/sif/cli/commands/context.py` — normalize_path import; explicit path branch; dual-form upsert with self-heal; canonical form echoed in messages
- `src/sif/database/repositories.py` — new `update_target()`; `delete_orphaned_paths()` rewritten (normalize_path import at top; no import cycle — utils/paths imports only sif.config.constants)
- `tests/unit/cli/test_context.py` — new `TestContextAddNormalizedPaths` class (5 tests, real symlink fixture, existing 16 tests untouched and passing)
- `tests/unit/database/test_repositories.py` — NEW: 7 real-SQL tests against production DDL (no sqlite-vec)
- `.planning/phases/05-agent-context-experience/deferred-items.md` — logged pre-existing `search --json` control-character quirk

## Decisions Made

1. **Merge-on-re-add over bulk migration** — legacy verbatim rows are re-pointed only when the user explicitly re-adds the same path; read-side re-normalization (05-08) covers everything else. No migration ever rewrites user data at startup.
2. **Python-side set comparison for prune** — the exact shape REVIEW CR-02 recommended; count semantics (`-> int`) and the D-12/D-13 explicit-command contract unchanged.
3. **Canonical echo in CLI messages** — path-type success/updated messages print the resolved form so the stored value is visible; collection/global messages keep showing the user's typed target.

## Deviations from Plan

**1. [Rule 1 - Bug] Brittle output assertion against rich line-wrapping**
- **Found during:** Task 1 GREEN
- **Issue:** `assert canonical in result.output` failed because rich Console wraps long tmp-dir paths across lines inside the captured output — the canonical path WAS printed correctly.
- **Fix:** assert against `result.output.replace("\n", "")` (width-independent substring match); behavior unchanged.
- **Files modified:** tests/unit/cli/test_context.py
- **Verification:** 21/21 CLI context tests pass.
- **Commit:** 551e41f

**2. [Rule 1 - Bug] Ruff RUF059/ARG001 violations in new tests**
- **Found during:** Task 1 GREEN (pre-commit-quality lint pass)
- **Issue:** unused unpacked `resolved` variable (3x) and unused `context_type` side-effect parameter (2x).
- **Fix:** underscore-prefixed the unused names (`_, alias = alias_pair`, `_context_type`).
- **Files modified:** tests/unit/cli/test_context.py
- **Verification:** `ruff check` + `ruff format --check` clean; tests still pass.
- **Commit:** 551e41f

**3. [Process] First RED commit briefly swept in a pre-staged foreign deletion**
- **Found during:** Task 1 RED commit
- **Issue:** the working tree arrived with a prior session's `mypy.ini` deletion already staged in the index; a plain `git commit` included it.
- **Fix:** immediate `git reset --soft HEAD~1` + pathspec-limited re-commit (`2df0ab9` contains only the test file); every subsequent commit in this run was pathspec-limited, leaving the staged deletion and all other pre-existing working-tree changes exactly as found.
- **Verification:** `git show --stat` per commit; final `git status` matches the session-start snapshot.

**Total deviations:** 2 auto-fixed (Rule 1) + 1 process incident (no code impact). **Impact:** none on behavior or scope; all acceptance criteria and verification steps pass.

## Issues Encountered

- **Pre-existing (out of scope, deferred):** `sif search search <term> --json` emits raw control characters (literal newlines) inside the `snippet` field — strict JSON parsers reject the output without `strict=False`. Discovered during the live verification loop; unrelated to this plan's changes. Logged to `deferred-items.md`.
- The 11 skipped tests in `tests/unit/database/test_schema.py` are the known pre-existing sqlite-vec extension skips — explicitly out of scope per the plan; this plan's new test file has 0 skips.

## Authentication Gates

None — all work was local (SQLite + Click CLI); no external auth required.

## User Setup Required

None.

## Next Phase Readiness

- Phase 05 is now 9/9 plans executed; with 05-08 (read side) and 05-09 (write + prune side) both complete, every gap from 05-VERIFICATION.md is closed: new writes are canonical, legacy rows match on read AND merge on re-add, prune uses the one shared normalize_path definition, and the live CR-02 reproduction resolves to "context preserved".
- Full suite: 646 passed, 11 skipped, 0 failed (was 634 passed pre-plan). Ruff check + format clean.
- Suggested next: `/gsd-verify-work 05` or phase close-out toward v1.0 completion (two deferred follow-ups in 04-UAT.md remain, per STATE.md).
