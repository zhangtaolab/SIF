---
phase: 02-cli-core-completion
plan: 04
subsystem: cli
requirements:
  - CLI-05
tech-stack:
  added:
    - huggingface_hub (optional)
    - modelscope (optional)
  patterns:
    - Click command with argument and option
    - Graceful fallback between download sources
    - File existence and non-empty verification
key-files:
  created:
    - src/docsift/cli/commands/pull.py
    - tests/unit/cli/test_pull.py
  modified:
    - src/docsift/cli/main.py
decisions:
  - Refactored pull_cmd into helper functions to keep mccabe complexity under 10
  - Used module-level optional imports with None fallback so patch targets exist for tests
  - Added `raise ... from err` per ruff B904 for clean exception chaining
metrics:
  duration: 15
  completed_date: "2026-04-15"
---

# Phase 02 Plan 04: Implement `docsift pull` Command Summary

## One-liner
Implemented `docsift pull` to download GGUF models from HuggingFace Hub with ModelScope fallback, direct URL support, and post-download file verification.

## What Was Built

- `src/docsift/cli/commands/pull.py`
  - `pull_cmd` Click command accepting `MODEL_SPEC` positional argument and `--cache-dir` option
  - `_download_from_url` for direct HTTP(S) downloads via `urllib.request`
  - `_download_from_hf` for HuggingFace Hub downloads via `hf_hub_download`
  - `_download_from_modelscope` for ModelScope fallback via `snapshot_download`
  - File verification: raises `click.ClickException` if downloaded file is missing or empty

- `src/docsift/cli/main.py`
  - Registered `pull_cmd` so `docsift pull --help` works

- `tests/unit/cli/test_pull.py`
  - `test_pull_hf_success` — verifies HF download path and call args
  - `test_pull_hf_falls_back_to_modelscope` — verifies fallback path and output
  - `test_pull_url_direct_download` — verifies direct URL download
  - `test_pull_invalid_spec` — verifies error on malformed spec
  - `test_pull_empty_file` — verifies rejection of empty downloaded file
  - `test_pull_modelscope_not_installed` — verifies clean error when ModelScope is unavailable

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Module-level imports needed for patchability**
- **Found during:** Task 3 (unit tests)
- **Issue:** `hf_hub_download` was imported inside `pull_cmd`, so `unittest.mock.patch("docsift.cli.commands.pull.hf_hub_download")` raised `AttributeError`
- **Fix:** Moved optional imports to module level with `None` fallback so patch targets exist even when libraries are not installed
- **Files modified:** `src/docsift/cli/commands/pull.py`
- **Commit:** `def8f33`

**2. [Rule 1 - Bug] Function complexity exceeded max (11 > 10)**
- **Found during:** ruff check
- **Issue:** `pull_cmd` exceeded mccabe complexity of 10
- **Fix:** Refactored into `_download_from_url`, `_download_from_hf`, `_download_from_modelscope`, and `_download_model` helpers
- **Files modified:** `src/docsift/cli/commands/pull.py`
- **Commit:** `def8f33`

**3. [Rule 2 - Missing critical functionality] Exception chaining**
- **Found during:** ruff check
- **Issue:** B904 violations — exceptions raised inside `except` blocks without `from err`
- **Fix:** Added `raise click.ClickException(...) from e/err` for all wrapped exceptions
- **Files modified:** `src/docsift/cli/commands/pull.py`
- **Commit:** `def8f33`

## Verification Results

- `python -m docsift.cli.main pull --help` — exits 0, shows correct usage
- `pytest tests/unit/cli/test_pull.py -x` — 6/6 passed
- `ruff check src/docsift/cli/commands/pull.py tests/unit/cli/test_pull.py` — passed
- `ruff format --check src/docsift/cli/commands/pull.py tests/unit/cli/test_pull.py` — passed

## Self-Check: PASSED

- `src/docsift/cli/commands/pull.py` — FOUND
- `src/docsift/cli/main.py` — FOUND
- `tests/unit/cli/test_pull.py` — FOUND
- Commits `d2dbf22`, `b803f7d`, `38747f6`, `def8f33` — all verified in `git log`
