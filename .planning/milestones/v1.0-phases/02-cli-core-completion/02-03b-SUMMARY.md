---
phase: 02-cli-core-completion
plan: 03b
type: execute
subsystem: cli
wave: 3
depends_on:
  - 02-03a-PLAN.md
requires:
  - CLI-04
key-files:
  created:
    - tests/unit/cli/test_search.py
  modified:
    - src/docsift/cli/commands/search.py
decisions: []
tech-stack:
  added: []
  patterns:
    - Click CLI option flag
    - CollectionRepository.list_enabled filtering
metrics:
  duration_minutes: 10
  tasks_completed: 2
  files_created: 1
  files_modified: 1
  tests_added: 4
---

# Phase 02 Plan 03b: Wire --all flag into search commands Summary

**One-liner:** Wired `--all` flag into `search`, `query`, and `vsearch` CLI commands so default searches respect `include_by_default` collection setting.

## What Was Done

1. Updated `src/docsift/cli/commands/search.py`:
   - `search_cmd`: added `elif not search_all:` block that resolves enabled collections via `CollectionRepository.list_enabled()`.
   - `query_cmd`: added identical enabled-collection filtering when `--all` is not passed.
   - `vsearch_cmd`: added `--all` option and identical filtering logic.

2. Created `tests/unit/cli/test_search.py` with four unit tests:
   - `test_search_respects_include_by_default`
   - `test_search_all_bypasses_include_by_default`
   - `test_query_respects_include_by_default`
   - `test_vsearch_respects_include_by_default`

## Deviations from Plan

None - plan executed exactly as written.

## Commits

| Hash | Message | Files |
|------|---------|-------|
| 52c94e3 | feat(02-03b): wire --all flag into search, query, and vsearch commands | src/docsift/cli/commands/search.py |
| 1a28366 | test(02-03b): add unit tests for search filtering and --all flag | tests/unit/cli/test_search.py |

## Verification

- `python -c "from docsift.cli.commands.search import search_cmd, query_cmd, vsearch_cmd; print('import ok')"` passed.
- `pytest tests/unit/cli/test_search.py -x` passed (4/4 tests).

## Self-Check: PASSED

- [x] `src/docsift/cli/commands/search.py` modified correctly
- [x] `tests/unit/cli/test_search.py` created and passes
- [x] Commits 52c94e3 and 1a28366 exist in git history
