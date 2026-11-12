---
phase: quick-261111-rqr
plan: 01
subsystem: tests/cli
status: complete
tags: [testing, logging, caplog, hermeticity, deferred-D-1]
requires: []
provides: ["D-1 resolved: watch CLI test module hermetic against leaked sif logger state"]
affects: [tests/unit/cli/test_watch_cmd.py, o6y-deferred-ledger]
key-files:
  created: []
  modified:
    - tests/unit/cli/test_watch_cmd.py
    - .planning/quick/261111-o6y-find-and-fix-failing-tests-run-the-quali/deferred-items.md
decisions:
  - "Victim-side autouse fixture (not predecessor fixes): three files leak independently, so isolation belongs in the affected module"
  - "Fixture snapshots/normalizes/restores the sif logger chain + manager.disable; root logger untouched (pytest logging plugin owns it)"
metrics:
  duration: 6 min
  completed: 2026-11-11
  tasks: 2
  commits: 2
---

# Quick 261111-rqr: Fix deferred D-1 caplog cross-test leak in test_watch_cmd.py Summary

Victim-side autouse logging-isolation fixture makes the watch CLI test module hermetic against `setup_logging`'s leaked `propagate=False` wall, turning the .venv 11-file batch green under pytest 9.0.3 with zero production changes.

## What Happened

### Mechanism (re-verified live, not assumed)

The real `cli` group callback (`src/sif/cli/main.py`) runs `setup_logging`, which leaves the `sif` logger with `propagate=False`, a stderr StreamHandler, and a raised level (confirmed in `src/sif/utils/logging.py`: `setLevel` + `addHandler` + `propagate = False`). caplog's capture handler sits on the ROOT logger, so the shutdown WARNING from `sif.cli.commands.watch` stops at the `sif` logger and never reaches `caplog.records` — the assertion at `tests/unit/cli/test_watch_cmd.py:609` fails. pytest 9.1.1 (PATH miniconda) tolerates the same leak; 9.0.3 (.venv) does not.

### Bisect result

Three predecessor files leak individually (each paired with the victim file under .venv): `tests/unit/cli/test_collection.py`, `tests/unit/cli/test_get.py`, `tests/unit/cli/test_main.py` — all invoke the real `cli` group. Because multiple predecessors leak, the fix is victim-side per the plan.

### RED evidence (re-proven live at HEAD 8f16b1e, before the fix)

- Minimal pair (`test_main.py::TestStatusRealDatabase::test_missing_index_returns_guidance` + victim) under `.venv/bin/python` pytest 9.0.3, FORCE_COLOR=1 --no-cov: exit 1, `1 failed, 1 passed in 0.06s`; the only FAILED line is exactly `tests/unit/cli/test_watch_cmd.py::TestShutdownRoutine::test_shutdown_skips_checkpoint_when_worker_still_busy`.
- Full 11-file batch under .venv: `1 failed, 351 passed in 4.20s` — single failure is exactly the D-1 victim (count drifted from planning-time 349 due to sibling batch items rqp/rqq; failing test ID matched exactly, per plan gate).

### GREEN evidence (after the fixture)

| Gate | Interpreter | Result |
|------|-------------|--------|
| Minimal pair | .venv 9.0.3 | 2 passed |
| test_collection.py + victim file | .venv 9.0.3 | 59 passed |
| test_get.py + victim file | .venv 9.0.3 | 67 passed |
| test_main.py + victim file | .venv 9.0.3 | 42 passed |
| Full 11-file batch (FORCE_COLOR=1 --no-cov) | .venv 9.0.3 | 352 passed, exit 0, zero FAILED |
| Full 11-file batch (FORCE_COLOR=1 --no-cov) | PATH 9.1.1 | 352 passed, exit 0, zero FAILED |
| test_watch_cmd.py alone | .venv 9.0.3 | 35 passed |
| `git status --porcelain -- src` | — | empty (production untouched) |

### Fixture contract implemented

`_hermetic_sif_logging` (module-level autouse, `Generator[None, None, None]`): for each of `sif`, `sif.cli`, `sif.cli.commands`, `sif.cli.commands.watch` — snapshot level/propagate/disabled/shallow-copied handlers, normalize to NOTSET/True/False/fresh `[]`; snapshot `logging.Logger.manager.disable` and set NOTSET; yield; restore every snapshot exactly in `finally`. Root logger never touched. Docstring names D-1, the mechanism, and the test-side-only boundary.

### Full quality suite (PATH miniconda interpreter, per CLAUDE.md)

- `ruff check src tests`: All checks passed
- `ruff format --check src tests`: 188 files already formatted (no style follow-up needed)
- `python -m pytest` (coverage addopts active): **1526 passed, 1 skipped in 79.57s; total coverage 95.03%** (fail_under=90 satisfied; baseline at planning time 1514 passed / 95.02% — drift from sibling items)

### Audit closure

Appended two sibling bullets to the D-1 entry in the o6y deferred ledger (`- **Status:** resolved` + resolution note); diff is exactly +2/-0, every other line byte-identical. Real audit parser probe (`uat.cjs parseDeferredItemsWithStatus`) prints `D-1 status: resolved`. 10-REVIEW-DISPOSITION.md untouched per orchestrator directive.

## Commits

| Task | Commit | Scope |
|------|--------|-------|
| 1 — victim-side logging-isolation fixture (RED→GREEN) | `9a354a3` | tests/unit/cli/test_watch_cmd.py only (+37) |
| 2 — resolve D-1 in o6y deferred ledger | `a04af92` | deferred-items.md only (+2) |

## Deviations from Plan

None — plan executed exactly as written. Batch pass-count drift (349→351 RED / 352 GREEN; suite 1514→1526) was anticipated by the plan's exit-code/test-ID gates and accepted.

## Known Stubs

None. No stubs, skipped tests, or unrun verifies.

## Self-Check: PASSED

- FOUND: tests/unit/cli/test_watch_cmd.py
- FOUND: .planning/quick/261111-o6y-find-and-fix-failing-tests-run-the-quali/deferred-items.md
- FOUND: .planning/quick/261111-rqr-fix-deferred-d-1-caplog-cross-test-leak-in-tests-unit-cli-te/261111-rqr-SUMMARY.md
- FOUND: commit 9a354a3 (ancestor of HEAD)
- FOUND: commit a04af92 (ancestor of HEAD)
- Measured commits since base 8f16b1e: 2 (matches plan's two scoped commits)
- `git status --porcelain -- src`: empty