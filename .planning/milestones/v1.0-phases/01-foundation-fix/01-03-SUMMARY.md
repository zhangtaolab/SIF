---
phase: 01-foundation-fix
plan: 03
subsystem: cli
tags: [click, sentence-transformers, checksum, settings]

requires:
  - phase: 01-01
    provides: pyproject.toml dependencies and project structure
  - phase: 01-02
    provides: database schema and repository patterns

provides:
  - Correct checksum comparison in index update command
  - Configurable embedding model in CLI embed command
  - Aligned default model between embedder and Settings

affects:
  - 01-04
  - 01-05

tech-stack:
  added: []
  patterns:
    - "CLI commands read defaults from Settings, allowing --override"
    - "Embedder defaults stay in sync with Settings.model_name"

key-files:
  created: []
  modified:
    - src/docsift/cli/commands/index.py
    - src/docsift/embedding/embedder.py

key-decisions:
  - "Kept get_settings() call local inside embed_cmd to avoid import-time side effects"
  - "Used model or settings.model_name pattern for CLI override precedence"

patterns-established:
  - "CLI override: CLI option takes precedence over Settings default"

requirements-completed:
  - FND-02
  - FND-04

# Metrics
duration: 8min
completed: 2026-04-15
---

# Phase 01 Plan 03: Checksum and Embedding Model Fix Summary

**Fixed inverted checksum logic in index update and removed hardcoded embedding model paths, aligning CLI and embedder defaults with Settings**

## Performance

- **Duration:** 8 min
- **Started:** 2026-04-15T07:08:00Z
- **Completed:** 2026-04-15T07:16:00Z
- **Tasks:** 3
- **Files modified:** 2

## Accomplishments
- Fixed inverted checksum comparison so unchanged documents are skipped and changed documents are updated
- Removed hardcoded `BAAI/bge-small-zh-v1.5` from `embed_cmd` and added `--model` / `-m` CLI override
- Aligned `SentenceTransformerEmbedder` default with `Settings.model_name` (`all-MiniLM-L6-v2`)

## Task Commits

1. **Task 1: Fix inverted checksum comparison in update_cmd** - `dd8defc` (fix)
2. **Task 2: Remove hardcoded model from embed_cmd and add --model override** - `dd8defc` (feat)
3. **Task 3: Align SentenceTransformerEmbedder default with Settings** - `b7c2100` (fix)

_Note: Tasks 1 and 2 were committed together in `dd8defc` because `src/docsift/cli/commands/index.py` was a new untracked file in this worktree._

## Files Created/Modified
- `src/docsift/cli/commands/index.py` - Fixed checksum skip logic; made embed model configurable via Settings with CLI `--model` override
- `src/docsift/embedding/embedder.py` - Changed `SentenceTransformerEmbedder` default model to `all-MiniLM-L6-v2`

## Decisions Made
- Kept `get_settings()` import local inside `embed_cmd` to avoid import-time side effects in the CLI module
- Used `model or settings.model_name` pattern so CLI option takes precedence over the Settings default

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

- The source files (`src/docsift/cli/commands/index.py` and `src/docsift/embedding/embedder.py`) were untracked in this worktree because they were created in prior waves on the main branch but this worktree was based on an earlier commit. Added them as new files and committed the fixes on top of the current HEAD.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- Index update now correctly skips unchanged documents, ready for further CLI command work
- Embedding model is configurable, ready for embedding pipeline enhancements

## Self-Check: PASSED
- `src/docsift/cli/commands/index.py` exists and contains `existing.checksum == parsed.checksum`
- `src/docsift/cli/commands/index.py` contains `model_name = model or settings.model_name`
- `src/docsift/embedding/embedder.py` contains `model_name: str = "all-MiniLM-L6-v2"`
- No occurrences of `BAAI/bge-small-zh-v1.5` remain in `src/`
- Commits `dd8defc` and `b7c2100` exist in git history

---
*Phase: 01-foundation-fix*
*Completed: 2026-04-15*
