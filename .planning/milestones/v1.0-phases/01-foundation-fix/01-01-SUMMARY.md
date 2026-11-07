---
phase: 01-foundation-fix
plan: "01"
subsystem: build
requires: []
provides:
  - pyproject.toml with complete runtime dependencies
affects:
  - pip install behavior
  - CLI import success
tags:
  - dependencies
  - pyproject.toml
  - build
key-files:
  created:
    - pyproject.toml
  modified: []
decisions:
  - Kept llama-cpp-python and sentence-transformers as optional extras per D-09
  - Excluded structlog because it is not imported anywhere in src/docsift/
metrics:
  duration_seconds: 53
  completed_date: "2026-04-14T23:04:21Z"
---

# Phase 01 Plan 01: Fix Missing Runtime Dependencies Summary

**One-liner:** Added all missing runtime dependencies to pyproject.toml so `pip install -e .` succeeds and the CLI launches without ModuleNotFoundError.

## What Was Done

1. Replaced the `dependencies` array in `pyproject.toml` with the complete runtime dependency list:
   - `sqlite-vec>=0.1.9`
   - `platformdirs>=3.0.0`
   - `pydantic>=2.0.0`
   - `pydantic-settings>=2.0.0`
   - `fastapi>=0.100.0`
   - `uvicorn>=0.20.0`
   - `watchdog>=3.0.0`
   - `numpy>=1.24.0`
   - Kept existing `click>=8.0.0`, `rich>=13.0.0`, `python-frontmatter>=1.0.0`
2. Verified `pip install -e .` completes successfully.
3. Verified `docsift --help` runs without import errors.

## Deviations from Plan

None - plan executed exactly as written.

## Known Stubs

No stubs introduced.

## Threat Flags

None introduced.

## Self-Check: PASSED

- [x] `pyproject.toml` exists and contains `sqlite-vec>=0.1.9`
- [x] Commit `319762e` exists in git history
- [x] `docsift --help` exits with code 0
