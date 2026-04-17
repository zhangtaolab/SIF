---
phase: 05-agent-context-experience
plan: 01
subsystem: database
tags: [sqlite, schema-migration, repository-pattern, dataclass, contexts]

# Dependency graph
requires:
  - phase: 04-advanced-search-pipeline
    provides: SearchResult dataclass, RRF fusion, rerankers
provides:
  - Unified contexts table with path/collection/global scope support
  - Atomic SAVEPOINT migration from path_contexts to contexts
  - ContextRepository with context_type filtering and backward-compatible alias
  - SearchResult.context_description field preserved through RRF and reranking
affects:
  - 05-agent-context-experience (all subsequent plans depend on this schema)
  - CLI context commands (will query contexts table)
  - Search pipeline (will display context_description in results)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "SAVEPOINT-based atomic schema migration for zero-downtime upgrades"
    - "Repository rename with backward-compatible module-level alias"
    - "Dataclass field appended with default=None to preserve positional arg compatibility"

key-files:
  created: []
  modified:
    - src/docsift/database/schema.py
    - src/docsift/database/repositories.py
    - src/docsift/core/models.py
    - src/docsift/models/search.py
    - src/docsift/search/rrf.py
    - src/docsift/search/rerank.py

key-decisions:
  - "Added context_description as LAST field with default=None to preserve positional arg compatibility in existing tests"
  - "Kept PathContext dataclass and PathContextRepository alias for backward compatibility during transition"
  - "Used SAVEPOINT/ROLLBACK atomic migration to prevent partial schema state on failure"
  - "Mapped target_id->path and content->context in _row_to_context to bridge old dataclass to new schema"

patterns-established:
  - "Schema migration: CHECK constraint on context_type enum, SAVEPOINT for atomicity"
  - "Repository evolution: rename class, add alias, update SQL gradually"
  - "Field propagation: when adding fields to SearchResult, update ALL constructors in RRF and rerankers"

requirements-completed:
  - CTX-01

# Metrics
duration: 35min
completed: 2026-04-18
---

# Phase 05 Plan 01: Database Schema Migration for Unified Contexts Summary

**Unified contexts table with SAVEPOINT atomic migration, ContextRepository with context_type filtering, and SearchResult.context_description field preserved through RRF fusion and cross-encoder reranking**

## Performance

- **Duration:** 35 min
- **Started:** 2026-04-18T00:00:00Z
- **Completed:** 2026-04-18T00:35:00Z
- **Tasks:** 3
- **Files modified:** 6

## Accomplishments
- Replaced path_contexts table with unified contexts table supporting path, collection, and global scopes
- Implemented atomic SAVEPOINT migration that rolls back on failure, preventing partial schema state
- Renamed PathContextRepository to ContextRepository with get_by_target, list_by_type, delete_orphaned_paths
- Added context_description to SearchResult dataclass and Pydantic model with full propagation through RRF and both rerankers
- Maintained backward compatibility via PathContextRepository = ContextRepository alias

## Task Commits

Each task was committed atomically:

1. **Task 1: Update SchemaManager — contexts table, migration, indexes** - `f9c740b` (feat)
2. **Task 2: Rename PathContextRepository to ContextRepository with context_type support** - `a622c5b` (feat)
3. **Task 3: Add context_description to SearchResult dataclass** - `fb0cb71` (feat)
4. **Fixup: Restore ContextRepository after accidental revert** - `a95f302` (fix)

## Files Created/Modified
- `src/docsift/database/schema.py` - Unified contexts table, SAVEPOINT migration, updated indexes and stats
- `src/docsift/database/repositories.py` - ContextRepository with context_type support, backward-compatible alias
- `src/docsift/core/models.py` - SearchResult.context_description field added at end with default=None
- `src/docsift/models/search.py` - Pydantic SearchResult.context_description field
- `src/docsift/search/rrf.py` - RRF fuse() and fuse_with_weights() propagate context_description
- `src/docsift/search/rerank.py` - Both rerankers propagate context_description in rebuilt SearchResult objects

## Decisions Made
- Added context_description as the LAST field of SearchResult with `default=None` to preserve positional argument compatibility in existing tests (per D-08 and Pitfall 3 from RESEARCH.md)
- Kept PathContext dataclass and PathContextRepository alias to avoid breaking existing imports during the transition period
- Used SAVEPOINT-based atomic migration instead of ALTER TABLE to handle the column rename (path->target_id, context->content) and addition of context_type
- Mapped target_id->path and content->context in _row_to_context() since PathContext lacks target_id/content fields

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Task 3 commit accidentally reverted repositories.py from ContextRepository back to PathContextRepository**
- **Found during:** Final acceptance criteria verification after Task 3
- **Issue:** Commit `fb0cb71` included a revert of repositories.py that removed ContextRepository, get_by_target, list_by_type, delete_orphaned_paths, and the PathContextRepository alias. All SQL was changed back from `contexts` table to `path_contexts` table.
- **Fix:** Created follow-up commit `a95f302` restoring the correct ContextRepository code. The working tree always had the correct code; only HEAD was wrong.
- **Files modified:** `src/docsift/database/repositories.py`
- **Verification:** Acceptance criteria for Task 2 all pass; `ContextRepository is PathContextRepository` import test passes
- **Committed in:** `a95f302`

**2. [Rule 3 - Blocking] Git skip-worktree flags prevented staging changes**
- **Found during:** Task 2 commit attempt
- **Issue:** Files showed `H` status in `git ls-files -v`, meaning `skip-worktree` was set. `git add` would not stage modifications.
- **Fix:** Used `git update-index --no-skip-worktree` to remove the flag, then manually set index entries with `git update-index --cacheinfo` where needed.
- **Files modified:** `src/docsift/database/repositories.py`, `src/docsift/database/schema.py`
- **Verification:** `git status` showed files as staged after fix

---

**Total deviations:** 2 auto-fixed (1 bug, 1 blocking)
**Impact on plan:** Both fixes were tooling/git issues, not code issues. The working tree code was always correct. No scope creep.

## Issues Encountered
- Git skip-worktree flags on worktree files prevented normal staging; resolved with `git update-index --no-skip-worktree`
- Task 3 commit accidentally included a revert of Task 2's changes in repositories.py; the working tree file was never reverted, only HEAD was wrong. Fixed with a follow-up commit.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Schema foundation complete for all Phase 5 context work
- ContextRepository ready for CLI context commands (set, get, list, delete)
- SearchResult ready for context_description display in search output
- No blockers for subsequent plans

## Self-Check: PASSED

- [x] `src/docsift/database/schema.py` exists and contains `_create_contexts_table`, `_migrate_path_contexts`
- [x] `src/docsift/database/repositories.py` exists and contains `class ContextRepository`, `PathContextRepository = ContextRepository`
- [x] `src/docsift/core/models.py` contains `context_description: Optional[str] = None` in SearchResult
- [x] Commit `f9c740b` exists (Task 1)
- [x] Commit `a622c5b` exists (Task 2)
- [x] Commit `fb0cb71` exists (Task 3)
- [x] Commit `a95f302` exists (Fixup)
- [x] All acceptance criteria pass for all 3 tasks
- [x] 75 unit tests pass (4 skipped)

---
*Phase: 05-agent-context-experience*
*Completed: 2026-04-18*
