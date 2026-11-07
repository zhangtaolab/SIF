---
phase: 02-cli-core-completion
plan: 02
subsystem: cli
tags: [click, rich, cli, tree, unittest.mock]

requires:
  - phase: 01-foundation-fix
    provides: Consolidated repository pattern in database/repositories.py

provides:
  - Top-level docsift ls command for browsing indexed documents
  - Virtual file tree rendering via rich.tree.Tree
  - Optional collection and subpath filtering
  - Unit test coverage for all ls branches

affects:
  - 02-cli-core-completion

tech-stack:
  added: []
  patterns:
    - "Click command with optional positional arguments"
    - "Rich Tree for hierarchical CLI output"
    - "unittest.mock.patch for repository isolation in CLI tests"

key-files:
  created:
    - src/docsift/cli/commands/ls.py
    - tests/unit/cli/test_ls.py
  modified:
    - src/docsift/cli/main.py

key-decisions:
  - "Mock index_path.exists on the mock object rather than patching Path.exists in ls.py, since ls.py does not import Path directly"

patterns-established:
  - "CLI tests mock Database and Repository classes at the module boundary (docsift.cli.commands.ls.Database)"

requirements-completed:
  - CLI-02

# Metrics
duration: 18min
completed: 2026-04-15
---

# Phase 02: Plan 02 — Top-level `docsift ls` Command Summary

**Top-level `docsift ls` command displaying indexed documents as a virtual file tree, with optional collection and subpath filtering**

## Performance

- **Duration:** 18 min
- **Started:** 2026-04-15T09:55:00Z
- **Completed:** 2026-04-15T10:13:00Z
- **Tasks:** 3
- **Files modified:** 3

## Accomplishments
- Created `src/docsift/cli/commands/ls.py` with `ls_cmd` using `rich.tree.Tree`
- Registered `ls_cmd` in `src/docsift/cli/main.py`
- Added 5 unit tests covering no-index, all collections, specific collection, subpath filter, and collection-not-found cases

## Task Commits

Each task was committed atomically:

1. **Task 1: Create ls.py command module** - `d01ee21` (feat)
2. **Task 2: Register ls command in main.py** - `b1ca0ef` (feat)
3. **Task 3: Add unit tests for ls command** - `b18d173` (test)

## Files Created/Modified
- `src/docsift/cli/commands/ls.py` - Top-level `ls` command implementation with Tree rendering
- `src/docsift/cli/main.py` - Registered `ls_cmd` import and `cli.add_command(ls_cmd)`
- `tests/unit/cli/test_ls.py` - Unit tests for all `ls` branches

## Decisions Made
- Mocked `index_path.exists` on the mock object passed via `CliRunner(obj=...)` instead of patching `Path.exists` in `ls.py`, because `ls.py` does not import `Path` directly.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
- `ruff` binary was not on PATH; used the conda env binary at `/Users/forrest/miniconda3/envs/mineru/bin/ruff` to run linting and formatting.
- Pre-existing lint issues in `main.py` (E402, B904, F821) were not introduced by this plan and were left unchanged.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- CLI `ls` is ready for use
- `collection ls` behavior remains unchanged
- Ready for subsequent CLI core completion plans

## Self-Check: PASSED
- `src/docsift/cli/commands/ls.py` exists
- `src/docsift/cli/main.py` contains `ls_cmd` registration
- `tests/unit/cli/test_ls.py` exists and passes
- Commits `d01ee21`, `b1ca0ef`, `b18d173` verified in git log
