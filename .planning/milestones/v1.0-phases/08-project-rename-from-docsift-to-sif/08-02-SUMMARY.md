---
phase: 08-project-rename-from-docsift-to-sif
plan: 02
subsystem: cli
tags: [sif, branding, migration, constants, metadata]

# Dependency graph
requires:
  - phase: 08-project-rename-from-docsift-to-sif
    provides: "Plan 01 directory rename src/docsift -> src/sif"
provides:
  - "SIF-branded constants with updated XDG paths"
  - "Package metadata (__init__.py, _version.py, config/__init__.py) referencing SIF"
  - "Model cache auto-migration logic in CLI main.py"
  - "Schema error messages referencing sif commands"
affects:
  - "08-03: Update settings.py and environment variable prefix"
  - "08-04: Update all remaining module imports"
  - "08-05: Update tests to use sif imports"

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Centralized constants in constants.py for all path/name references"
    - "Auto-migration pattern: detect old path + new path absent -> rename"

key-files:
  created: []
  modified:
    - "src/sif/config/constants.py - APP_NAME and all default paths updated to sif"
    - "src/sif/__init__.py - Package metadata and imports updated to sif"
    - "src/sif/_version.py - Docstring updated to SIF"
    - "src/sif/config/__init__.py - Docstring and imports updated to sif"
    - "src/sif/cli/main.py - Migration logic, branding, paths, imports updated"
    - "src/sif/database/schema.py - Error message updated to sif cleanup"

key-decisions:
  - "Migration only triggers when old path exists AND new path does not (T-08-02 mitigation)"
  - "Migration message printed via rich console for consistent CLI output"

patterns-established:
  - "All path constants derive from constants.py single source of truth"
  - "Migration logic placed in main() before Click parsing to run on every CLI invocation"

requirements-completed: []

# Metrics
duration: 8min
completed: 2026-04-27
---

# Phase 08 Plan 02: Core Constants, Metadata, and CLI Entry Point Rename Summary

**SIF branding applied to all core constants, package metadata, and CLI entry point with automatic model cache migration from old docsift paths**

## Performance

- **Duration:** 8 min
- **Started:** 2026-04-27T06:00:00Z
- **Completed:** 2026-04-27T06:08:00Z
- **Tasks:** 3
- **Files modified:** 6

## Accomplishments
- Updated all path constants to use sif directories (APP_NAME, DEFAULT_DB_PATH, DEFAULT_MODEL_PATH, DEFAULT_CONFIG_PATH)
- Updated package metadata across __init__.py, _version.py, and config/__init__.py to reference SIF
- Added model cache auto-migration logic per D-02: detects old ~/.local/share/docsift/models/ and renames to ~/.local/share/sif/models/
- Updated CLI branding (prog_name, docstrings, status message) to SIF
- Updated schema.py error message to reference "sif cleanup" command
- All imports in modified files changed from `from docsift...` to `from sif...`

## Task Commits

Each task was committed atomically:

1. **Task 1: Update constants.py with sif branding and paths** - `7f01594` (feat)
2. **Task 2: Update package metadata files (__init__.py, _version.py, config/__init__.py)** - `337cc66` (feat)
3. **Task 3: Add model cache migration logic to CLI main.py** - `b2db8a8` (feat)

## Files Created/Modified
- `src/sif/config/constants.py` - APP_NAME="sif", all default paths updated to ~/.local/share/sif/ and ~/.config/sif
- `src/sif/__init__.py` - Docstring, __author__, __description__, and imports updated to SIF
- `src/sif/_version.py` - Docstring updated to SIF
- `src/sif/config/__init__.py` - Docstring and imports updated to sif
- `src/sif/cli/main.py` - Migration logic, SIF branding, updated default paths, sif imports
- `src/sif/database/schema.py` - Error message references "sif cleanup" instead of "docsift cleanup"

## Decisions Made
- Followed plan exactly for all changes; no additional decisions required
- Migration logic uses `Path.rename()` for atomic directory move, with `mkdir(parents=True)` on parent to ensure target directory exists

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## Threat Flags

| Flag | File | Description |
|------|------|-------------|
| T-08-02 (mitigated) | src/sif/cli/main.py | Migration checks `not new_model_dir.exists()` before rename to prevent overwriting existing data |

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- Constants and metadata are SIF-branded; ready for Plan 03 (settings.py and env var prefix update)
- Migration logic in place for users upgrading from docsift to sif

## Self-Check: PASSED

- [x] `src/sif/config/constants.py` exists and contains `APP_NAME = "sif"`
- [x] `src/sif/__init__.py` exists and contains `__author__ = "SIF Team"`
- [x] `src/sif/cli/main.py` exists and contains migration logic
- [x] `src/sif/database/schema.py` exists and contains "sif cleanup"
- [x] Commit 7f01594 verified in git log
- [x] Commit 337cc66 verified in git log
- [x] Commit b2db8a8 verified in git log

---
*Phase: 08-project-rename-from-docsift-to-sif*
*Completed: 2026-04-27*
