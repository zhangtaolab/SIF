---
phase: 05-agent-context-experience
plan: 05-05
status: complete
completed: "2026-04-18"
---

# Summary: Fix context_type Storage and Display Bugs

## What Was Built

Fixed data integrity issues where collection and global contexts were incorrectly stored as `context_type='path'` due to hardcoded SQL and missing parameter passing. Also fixed the list command to display actual context types instead of hardcoded `"path"` for all rows.

## Changes

### src/docsift/core/models.py
- Added `context_type: str = "path"` field to `PathContext` dataclass
- Updated `to_dict()` to include `context_type`
- Backward compatible: existing constructors without `context_type` still work

### src/docsift/database/repositories.py
- `ContextRepository.create()` now uses `context.context_type` instead of hardcoded `'path'`
- `_row_to_context()` now reads `context_type` from DB row and passes it to `PathContext`

### src/docsift/cli/commands/context.py
- `context_add()` passes `context_type=type` to `PathContext` constructor
- `context_list()` displays `ctx_item.context_type` instead of hardcoded `"path"`

### tests/unit/cli/test_context.py
- Added assertions verifying `context_type` is passed correctly for path, collection, and global adds
- Updated `test_list_all` to use varied context types and verify they appear in output

## Verification

- `pytest tests/unit/cli/test_context.py` — 16 passed
- `ruff format --check` — clean
- Import verification: `PathContext(context_type="collection")` works correctly

## Deviations

None.
