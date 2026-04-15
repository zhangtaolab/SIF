---
phase: 02-cli-core-completion
plan: 01
subsystem: cli
requirements:
  - CLI-01
tags:
  - cli
  - multi-get
  - batch-retrieval
  - fnmatch
  - unit-tests
dependency_graph:
  provides:
    - src/docsift/cli/commands/get.py
    - tests/unit/cli/test_get.py
  requires: []
  affects:
    - src/docsift/cli/commands/get.py
tech_stack:
  added: []
  patterns:
    - Click CLI with pass_context
    - Repository pattern for DB access
    - fnmatch for glob matching
key_files:
  created:
    - tests/unit/cli/test_get.py
  modified:
    - src/docsift/cli/commands/get.py
decisions:
  - "D-01 priority preserved: comma-separated detection takes precedence over glob detection"
metrics:
  duration_minutes: 20
  completed_date: "2026-04-15"
---

# Phase 02 Plan 01: Multi-Get Batch Document Retrieval Summary

**One-liner:** Implemented `multi-get` command with auto-detection for comma-separated IDs, glob patterns, and single docid/path fallback, plus full unit test coverage.

## What Was Built

- **`multi_get_cmd`** in `src/docsift/cli/commands/get.py` now supports three input modes:
  1. **Comma-separated** — splits by comma, strips whitespace, looks up each item by ID then by path across all collections, deduplicates by document ID while preserving order.
  2. **Glob pattern** — when `*` or `?` is present, iterates all collections and matches `doc.path` or `doc.filename` using `fnmatch.fnmatch`.
  3. **Single item** — tries `get_by_id` first, then falls back to `get_by_path` across all collections.

- **`tests/unit/cli/test_get.py`** with four `CliRunner` tests covering all three branches plus the no-match case.

## Deviations from Plan

None — plan executed exactly as written.

## Verification Results

- `python -m docsift.cli.main get multi-get --help` shows the command correctly.
- `pytest tests/unit/cli/test_get.py -x` passes all 4 tests.
- New code passes ruff lint/format checks on the test file; pre-existing lint issues in `get.py` (`get_cmd` complexity, trailing whitespace, unused `Syntax` import) were left untouched as they are out of scope.

## Commits

| Commit | Message |
|--------|---------|
| c5d62d2 | feat(02-01): implement multi-get auto-detection logic |
| 802e833 | test(02-01): add unit tests for multi-get command |

## Self-Check: PASSED

- [x] `src/docsift/cli/commands/get.py` exists and contains the three-branch logic
- [x] `tests/unit/cli/test_get.py` exists and contains all 4 required tests
- [x] All commits verified in git log
- [x] SUMMARY.md created at `.planning/phases/02-cli-core-completion/02-01-SUMMARY.md`
- [x] STATE.md and ROADMAP.md updated via gsd-tools
