---
phase: 260914-vyr-rename-distribution-docsif-to-sif-pyproj
plan: 01
type: execute
subsystem: packaging
tags: [packaging, rename, distribution, audit-blocker, mcp]
requires:
  - "v1.0-MILESTONE-AUDIT.md BLOCKER 2 (distribution metadata still says docsif)"
provides:
  - "Distribution named sif with single sif console script (v1.0 audit BLOCKER 2 closed)"
  - "mcp and http extras under [project.optional-dependencies] — CLI hints at mcp.py:39/72 now truthful"
  - "uv.lock root package sif, lock-consistent"
affects:
  - pyproject.toml
  - README.md
  - uv.lock
tech-stack:
  added: []
  patterns:
    - "Extras aliasing already-core deps (uvicorn) to make CLI install hints resolvable with zero new packages"
key-files:
  created: []
  modified:
    - pyproject.toml
    - README.md
    - uv.lock
decisions:
  - "mcp/http extras list only already-core uvicorn — stdio transport is stdlib-only, http.py lazily imports uvicorn; zero new packages, zero resolution change"
  - "Deliberate non-changes: description \"DocSIF - ...\", version 0.2.1, docsift migration code, docs/migration.md, milestone archives, root-level legacy files"
metrics:
  duration: 3min
  completed: "2026-09-14T15:11:42Z"
  tasks: 2
  files: 3
status: complete
actuals:
  tokens: 2425     # chars/4 over the realized diff (9703 chars) vs estimate 25000
  tasks: 2
  commits: 2       # MEASURED: git rev-list --count 5dbdd66..HEAD
plan_head_before: 5dbdd6627ff0cb222552e276f116a16dd5f6454d
---

# Quick Task 260914-vyr: Rename distribution docsif -> sif Summary

Renamed the Python distribution `docsif` -> `sif` in pyproject.toml (name, keyword list, console scripts) and created the missing `mcp`/`http` extras so every CLI `pip install sif[...]` hint resolves; regenerated uv.lock via `uv lock` with zero unrelated package churn. Closes v1.0-MILESTONE-AUDIT BLOCKER 2.

## What Was Done

### Task 1: pyproject.toml + README.md rename (commit 25fff2d)

Four pyproject.toml edits, exactly as planned:
1. `name = "docsif"` -> `name = "sif"` (line 6)
2. Keyword list: dropped `"docsif"`, kept `"sif"` and the rest
3. `[project.scripts]`: deleted the duplicate `docsif = "sif.cli.main:main"` alias; only `sif = "sif.cli.main:main"` remains
4. `[project.optional-dependencies]`: added `mcp = ["uvicorn>=0.20.0"]` and `http = ["uvicorn>=0.20.0"]` after `openai`, before `all`

Three README.md edits: line 27 `pip install sif`, line 33 `pip install "sif[all]"`, line 54 `pip install sif`.

Untouched as required: description `"DocSIF - Local hybrid search engine..."` (line 8), version 0.2.1, `dev`/`embed`/`openai`/`all` extras, core dependencies, all tool config, `docsift` migration code in src/sif/cli/main.py, docs/migration.md, milestone archives, root-level legacy files, src/ at all.

Task 1 verify gate: `name = "sif"` / `mcp = [` / `http = [` present, no `^docsif` script line, `grep -nE "docsif([^ta-zA-Z]|$)" pyproject.toml README.md` returns zero hits, README has 2 bare `pip install sif` + 1 `pip install "sif[all]"`.

### Task 2: uv.lock regeneration + full verification gates (commit 4657ea8)

`uv lock` regenerated cleanly (108 packages). Diff shape exactly as threat-model T-260914-vyr-01 requires: the `docsif` root `[[package]]` entry removed from its old alphabetical slot, an identical `sif` entry added in the correct new slot (same deps/versions/markers), plus the two new uvicorn extras in `[package.optional-dependencies]` and `provides-extras = ["dev", "embed", "openai", "mcp", "http", "all"]`. No unrelated package churn.

All gates passed, in order:

| Gate | Result |
|------|--------|
| `uv lock --check` | exit 0 (resolved in 2ms) |
| `python -c "import sif; import sif.mcp"` | OK (conda python, not uv venv) |
| `python -m sif.cli.main --help` | exit 0 |
| `pip install -e .` | succeeded — sif 0.2.1 editable installed; `sif --help` exit 0 |
| `ruff check src tests` / `ruff format --check` | All checks passed / 132 files already formatted |
| `env -u FORCE_COLOR NO_COLOR=1 python -m pytest` | **675 passed, 0 failed** (16.14s) — baseline hit exactly; the pre-existing order-dependent caplog pair (WINDOWS.md #3/#4) did not trigger in full-suite order |
| Standalone-docsif grep gate (`docsif([^ta-zA-Z]\|$)`) | zero hits across pyproject.toml, README.md, docs/, src/, tests/, Makefile (CHANGELOG.md and CONTRIBUTING.md do not exist in this repo) |

CLI hints now truthful with NO src changes: mcp.py:39 `sif[mcp]`, mcp.py:72 `sif[http]`, search.py:509 `.[embed]`, embedder.py:386 `sif[openai]`, src/sif/mcp/README.md:21 `.[mcp]`.

## Deviations from Plan

None - plan executed exactly as written.

## Observations (no action taken)

- The local conda environment still carries a stale `docsif 0.1.1` dist-info from a pre-rename install (`pip show docsif` finds it). It is an environment artifact, not a repo artifact — harmless, removable at will with `pip uninstall docsif`. Gate 3's editable install also upgraded the local editable `sif` 0.1.0 -> 0.2.1.
- The stale git-status snapshot at execution start (modified `.planning/WINDOWS.md`/`config.json`, staged `mypy.ini` deletion, modified `uv.lock`) had cleared by the time execution began — working tree was clean except the protected untracked runtime dirs, which were left untouched. Nothing unrelated was swept into either commit (pathspec commits, verified via ledger + status).

## Known Stubs

None — metadata/docs rename only; zero Python source changed.

## Self-Check: PASSED

- Files: pyproject.toml FOUND, README.md FOUND, uv.lock FOUND
- Commits: 25fff2d FOUND, 4657ea8 FOUND (ledger base 5dbdd66, measured count 2)
