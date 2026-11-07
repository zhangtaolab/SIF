---
phase: 05-agent-context-experience
plan: 05-07
status: complete
completed: "2026-04-18"
---

# Summary: Fix Status Command to Respect DOCSIFT_DB_PATH

## What Was Built

Fixed the CLI `--index` option default and `status_cmd` to respect the `DOCSIFT_DB_PATH` environment variable. Previously, the `--index` option had a hardcoded default that bypassed Pydantic Settings entirely.

## Changes

### src/docsift/cli/main.py
- Imported `get_settings` from `docsift.config.settings`
- Added `_get_default_db_path()` helper that returns `get_settings().get_db_path()`
- Changed `--index` option default from `str(DEFAULT_INDEX_PATH)` to `_get_default_db_path` (callable — Click calls it when the option is not provided)
- Updated `status_cmd` to call `ctx.ensure_object(dict)` for safety and fall back to `get_settings().get_db_path()` if `index_path` is not in context

### tests/unit/cli/test_status.py (new)
- `test_status_uses_settings_db_path`: verifies that when `get_settings().get_db_path()` returns a custom path, `status_cmd` uses it
- `test_status_respects_env_var`: verifies that `DOCSIFT_DB_PATH` env var is respected via Settings

## Verification

- `pytest tests/unit/cli/test_status.py` — 2 passed
- `python -c "from docsift.cli.main import cli; print('CLI imports OK')"` — OK
- Explicit `--index` still overrides the default

## Deviations

None.
