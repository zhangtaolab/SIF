---
phase: 02-cli-core-completion
plan: 03a
subsystem: cli
tags: [click, sqlite, subprocess, repository-pattern]

requires:
  - phase: 02-cli-core-completion
    provides: Collection model and repository infrastructure

provides:
  - Collection.pre_update_cmd field with persistence
  - Schema migration helper for adding columns idempotently
  - collection update-cmd / include / exclude CLI subcommands
  - Pre-update shell command hook in index update with fail-fast behavior
  - Unit tests covering all new commands and the index hook

affects:
  - 02-cli-core-completion

tech-stack:
  added: []
  patterns:
    - "Repository pattern for collection CRUD"
    - "Idempotent schema migrations via PRAGMA table_info"
    - "subprocess.run with shell=True for trusted user input"

key-files:
  created:
    - tests/unit/cli/test_collection.py
  modified:
    - src/docsift/core/models.py
    - src/docsift/database/schema.py
    - src/docsift/database/repositories.py
    - src/docsift/cli/commands/collection.py
    - src/docsift/cli/commands/index.py

key-decisions:
  - "Moved subprocess import to module level in index.py to satisfy PLC0415 and keep inline imports for optional dependencies only"

patterns-established:
  - "SchemaManager._add_column_if_missing: idempotent ALTER TABLE for migrations"
  - "CollectionRepository.list_enabled: filter collections by include_by_default"

requirements-completed:
  - CLI-03
  - CLI-04

duration: 6min
completed: 2026-04-15
---

# Phase 02: Plan 03a — Collection Pre-Update Commands Summary

**Collection update-cmd, include/exclude subcommands, and pre-index shell hook with fail-fast subprocess execution**

## Performance

- **Duration:** 6 min
- **Started:** 2026-04-15T11:14:38Z
- **Completed:** 2026-04-15T11:20:52Z
- **Tasks:** 4
- **Files modified:** 6

## Accomplishments

- Added `pre_update_cmd` to the `Collection` dataclass with `to_dict`/`from_dict` support
- Created `_add_column_if_missing` in `SchemaManager` for safe, idempotent schema migrations
- Extended `CollectionRepository` to persist `pre_update_cmd` and added `list_enabled()`
- Implemented `collection update-cmd`, `collection include`, and `collection exclude` CLI commands
- Injected a pre-update shell command hook into `index update` that fails fast on non-zero exit
- Added comprehensive unit tests for all new behavior

## Task Commits

Each task was committed atomically:

1. **Task 1: Set up Collection model, schema, and repository for pre_update_cmd** — `8777978` (feat)
2. **Task 2: Add collection update-cmd, include, exclude commands** — `d104658` (feat)
3. **Task 3: Inject pre_update_cmd hook into index update** — `3b81ef0` (feat)
4. **Task 4: Add unit tests for collection and index changes** — `adc160e` (test)

**Lint fixes:** `e509abd` (style: move subprocess import to top level and format tests)

## Files Created/Modified

- `src/docsift/core/models.py` — Added `pre_update_cmd: Optional[str] = None` to `Collection`
- `src/docsift/database/schema.py` — Added `_add_column_if_missing` and migration for `pre_update_cmd`
- `src/docsift/database/repositories.py` — Persist `pre_update_cmd` in create/update; added `list_enabled()`
- `src/docsift/cli/commands/collection.py` — Added `update-cmd`, `include`, and `exclude` subcommands
- `src/docsift/cli/commands/index.py` — Added `subprocess.run` pre-update hook with fail-fast error handling
- `tests/unit/cli/test_collection.py` — Unit tests for all new commands and the index hook

## Decisions Made

- Moved `subprocess` import to the top of `index.py` to satisfy PLC0415, reserving inline imports for optional third-party dependencies only.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

- Python was importing from the main worktree (`/Users/forrest/GitHub/docsift/src`) rather than the agent worktree. Resolved by setting `PYTHONPATH` to the agent worktree `src` directory for all Python invocations.
- `subprocess` was originally imported inline in `index.py`, which triggered a PLC0415 lint warning. Moved it to the module level.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Collection pre-update command infrastructure is complete and tested.
- Ready for plans that build on collection management or indexing workflows.

---
*Phase: 02-cli-core-completion*
*Completed: 2026-04-15*
