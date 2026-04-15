---
phase: 02-cli-core-completion
plan: 05
subsystem: cli
---

# Phase 02 Plan 05: Add --line-numbers Display Flag Summary

## One-Liner
Added `--line-numbers` display flag to `get`, `multi-get`, `search`, `query`, and `vsearch` commands, supporting both rich table and structured output formats.

## What Was Done

- Implemented `prepend_line_numbers()` and `add_line_numbers_to_results()` helpers in `src/docsift/cli/formatters.py`.
- Added `--line-numbers` flag to `get_cmd` and `multi_get_cmd` in `src/docsift/cli/commands/get.py`.
- Added `--line-numbers` flag to `search_cmd`, `query_cmd`, and `vsearch_cmd` in `src/docsift/cli/commands/search.py`.
- Updated `format_results_md` and `format_results_xml` to include `line_numbers` when present.
- Updated `format_results_json` to handle both dataclass objects and dict inputs.
- Created comprehensive unit tests covering formatters, get commands, and search commands.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed format_results_json to handle dict inputs**
- **Found during:** Task 4 (testing search line-numbers with JSON output)
- **Issue:** `format_results_json` assumed all results had `.to_dict()`, but `add_line_numbers_to_results()` returns dicts, causing `AttributeError: 'dict' object has no attribute 'to_dict'`.
- **Fix:** Added `_to_dict` helper inside `format_results_json` that checks `hasattr(r, "to_dict")` and falls back to `dict(r)`.
- **Files modified:** `src/docsift/cli/commands/search.py`
- **Commit:** `1d20c2c`

**2. [Rule 1 - Bug] Fixed SearchResult instantiation in tests**
- **Found during:** Task 4 (testing search line-numbers table output)
- **Issue:** `SearchResult` requires `document_id` as a positional argument; tests were missing it.
- **Fix:** Added `document_id="doc1"` to the `_make_search_result` helper in tests.
- **Files modified:** `tests/unit/cli/test_search.py`
- **Commit:** `746e930`

## Commits

| Hash | Message | Files |
|------|---------|-------|
| `2601d88` | feat(02-05): add line-number formatting helpers to formatters.py | `src/docsift/cli/formatters.py` |
| `6276e41` | feat(02-05): add --line-numbers to get and multi-get commands | `src/docsift/cli/commands/get.py` |
| `1d20c2c` | feat(02-05): add --line-numbers to search, query, and vsearch commands | `src/docsift/cli/commands/search.py` |
| `746e930` | test(02-05): add unit tests for line-numbers formatting and commands | `tests/unit/cli/test_formatters.py`, `tests/unit/cli/test_get.py`, `tests/unit/cli/test_search.py` |

## Files Modified

- `src/docsift/cli/formatters.py`
- `src/docsift/cli/commands/get.py`
- `src/docsift/cli/commands/search.py`
- `tests/unit/cli/test_formatters.py` (created)
- `tests/unit/cli/test_get.py`
- `tests/unit/cli/test_search.py`

## Verification

- `pytest tests/unit/cli/test_formatters.py tests/unit/cli/test_get.py tests/unit/cli/test_search.py -x` passes (17/17 tests).
- `python -m docsift.cli.main get --help` shows `--line-numbers`.
- `python -m docsift.cli.main search --help` shows `--line-numbers`.

## Self-Check: PASSED
