---
phase: 08-project-rename-from-docsift-to-sif
plan: "01"
subsystem: infrastructure
tags: [rename, packaging, pyproject.toml]
dependency_graph:
  requires: []
  provides: ["08-02", "08-03", "08-04", "08-05", "08-06", "08-07", "08-08"]
  affects: [pyproject.toml, src/sif/]
tech-stack:
  added: []
  patterns: [git-mv for history preservation]
key-files:
  created: []
  modified:
    - src/sif/ (renamed from src/docsift/)
    - pyproject.toml
decisions: []
metrics:
  duration: "~5 minutes"
  completed_date: "2026-04-27"
---

# Phase 08 Plan 01: Rename Package Directory and Update pyproject.toml Summary

**One-liner:** Renamed Python package directory from `src/docsift/` to `src/sif/` and updated all `pyproject.toml` metadata, scripts, URLs, and tool configs.

## What Was Done

### Task 1: Rename src/docsift/ to src/sif/
- Used `git mv src/docsift src/sif` to preserve git history
- 81 files tracked as renames (not delete+add)
- All 79 Python files + 2 non-Python files preserved

### Task 2: Update pyproject.toml
Updated these fields from `docsift` to `sif`:
- `[project]` name, description, authors, keywords
- `[project.scripts]` entry point: `sif = "sif.cli.main:main"`
- `[project.urls]` Homepage, Documentation, Repository → `zhangtaolab/sif`
- `[tool.hatch.build.targets.wheel]` packages → `["src/sif"]`
- `[tool.ruff.lint.isort]` known-first-party → `["sif"]`
- `[tool.ruff.lint.per-file-ignores]` path → `src/sif/cli/*.py`
- `[tool.pytest.ini_options]` coverage path → `--cov=src/sif`

## Verification Results

| Check | Result |
|-------|--------|
| `src/sif/` exists with 79 Python files | PASS |
| `src/docsift/` no longer exists | PASS |
| `pyproject.toml` is valid TOML | PASS |
| `docsift` count in `pyproject.toml` = 0 | PASS |
| `sif` count in `pyproject.toml` = 11 | PASS |
| Git tracks renames (not delete+add) | PASS |

## Deviations from Plan

None — plan executed exactly as written.

## Auth Gates

None.

## Known Stubs

No new stubs introduced. All files are exact renames with no content changes.

## Threat Flags

No new threat surface introduced. This is a pure rename with no functional code changes.

## Self-Check: PASSED

- [x] `src/sif/` exists
- [x] `src/docsift/` does not exist
- [x] `pyproject.toml` valid TOML
- [x] Commit `76e9538` exists (directory rename)
- [x] Commit `3da0978` exists (pyproject.toml update)
