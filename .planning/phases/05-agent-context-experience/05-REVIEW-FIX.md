---
phase: 05-agent-context-experience
fixed_at: 2026-11-05T10:02:01Z
review_path: .planning/phases/05-agent-context-experience/05-REVIEW.md
iteration: 1
findings_in_scope: 1
fixed: 1
skipped: 0
status: all_fixed
---

# Phase 05: Code Review Fix Report

**Fixed at:** 2026-11-05T10:02:01Z
**Source review:** .planning/phases/05-agent-context-experience/05-REVIEW.md (incremental re-review, 2026-11-05T09:18:46Z)
**Iteration:** 1

**Summary:**
- Findings in scope: 1 (CR-02; fix_scope = critical_warning)
- Fixed: 1
- Skipped: 0

**Environment note:** `workflow.use_worktrees = false` — the fix was applied and
committed directly in the main checkout (`dev`). All verification ran in the
main checkout with `env -u FORCE_COLOR NO_COLOR=1` (FORCE_COLOR breaks CLI
output assertions on this machine), so the numbers are reproducible from the
tree a reader is looking at. This report replaces the previous fix-round report
(CR-01/WR-01, commits `e78fa96`/`7170c08`); those decisions are preserved in
`05-REVIEW-DISPOSITION.md` and git history.

## Fixed Issues

### CR-02: `--line-numbers --md` and `--line-numbers --xml` crash with `AttributeError: 'dict' object has no attribute 'rank'`

**Files modified:** `src/sif/cli/commands/search.py`, `tests/unit/cli/test_search.py`
**Commit:** 0be16d4
**Applied fix:**
- Renamed the CR-01 accessor `_csv_field` → `_field` (module-private, only
  consumer was `format_results_csv`; no other references in `src/` or
  `tests/`) and substituted it for the five mandatory bare-attribute fields in
  both `format_results_md` (`rank`, `title`, `score`, `path`,
  `collection_name`) and `format_results_xml` (same five). Score goes through
  `float(_field(r, 'score')):.4f`, mirroring the CSV path. The optional
  `line_numbers` lines keep their existing `hasattr` guards (unchanged), and
  the object-row (`SearchResult`) output is byte-identical to before.
- This covers both entry points (`search_cmd` and `query_cmd`) since both feed
  the same formatters; `vsearch_cmd` has no `--md`/`--xml` options and was
  already unaffected.
- Adaptations to the reviewer's snippet (guidance, applied to actual code):
  - In `format_results_xml` the score is pre-formatted into a local
    (`score = f"{float(_field(r, 'score')):.4f}"`) before the
    `<result ...>` line rather than inlined in the f-string — the inline form
    exceeded the project's 100-char line limit (CLAUDE.md) and nested quotes
    awkwardly on Python 3.10.
  - Quote styles per line follow `ruff format` (double-quoted unless the
    expression contains double quotes).
- Regression tests `TestSearchLineNumbers::test_search_line_numbers_md` and
  `::test_search_line_numbers_xml`, mirroring the existing `--csv` one:
  real `SearchResult` rows through `add_line_numbers_to_results` → dict rows →
  formatter, asserting exit 0 plus rendered content (`## 1. Test Doc`,
  ``- **Path:** `/notes/test.md` ``, `<path>/notes/test.md</path>`,
  `<result rank="1" score="0.9500">`, etc.).

## Skipped Issues

None — the single in-scope finding was fixed.

## Verification

- Tier 1: modified sections re-read; fix text present, surrounding code
  intact.
- Tier 2: `ast.parse` on both edited files — clean; `ruff check src tests` —
  all checks passed; `ruff format --check src tests` — 133 files already
  formatted (one quote-style normalization applied after the first check).
- Targeted: `env -u FORCE_COLOR NO_COLOR=1 pytest tests/unit/cli/test_search.py`
  — **30 passed** (28 baseline + 2 new CR-02 tests).
- Full suite: **686 passed, 2 failed, 20 warnings**. The 2 failures
  (`tests/unit/embedding/test_openai_embedder.py::test_import_error_logs_install_hint`,
  `test_corrupt_cache_treated_as_miss`) were proven pre-existing and
  order-dependent: the full suite run on the stashed pre-fix tree fails the
  same 2 tests (684 passed there vs 686 with the fix — the delta is exactly
  the 2 new tests), and both tests pass in isolation with and without the
  fix. They are in the embedding module, untouched by this change.
- Commits are pathspec-limited; the unrelated pre-existing working-tree state
  (modified `.planning/WINDOWS.md`; untracked `.planning/state.json`,
  `.planning/tmp/`, `.planning/ui-reviews/`) was left exactly as found.

---

_Fixed: 2026-11-05T10:02:01Z_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_
