---
phase: 14-freshness-floor-pre-command-refresh-staleness-marking
fixed_at: 2026-11-08T04:33:03Z
review_path: .planning/phases/14-freshness-floor-pre-command-refresh-staleness-marking/14-REVIEW.md
iteration: 1
findings_in_scope: 3
fixed: 3
skipped: 0
status: all_fixed
---

# Phase 14: Code Review Fix Report

**Fixed at:** 2026-11-08T04:33:03Z
**Source review:** `.planning/phases/14-freshness-floor-pre-command-refresh-staleness-marking/14-REVIEW.md`
**Iteration:** 1

**Summary:**
- Findings in scope: 3 (CR-01, WR-01, WR-02 — per fix directive)
- Fixed: 3
- Skipped: 0

Out of scope by directive (pre-existing or advisory; not touched): WR-03, WR-04, IN-01, IN-02.

## Fixed Issues

### CR-01: mtime-only drift never converges — every search re-locks, re-refreshes a no-op, and prints a false notice, forever

**Files modified:** `src/sif/indexing/incremental.py`, `tests/unit/indexing/test_drift.py`, `tests/unit/cli/test_search.py`
**Commit:** bd63c78
**Applied fix:** The checksum-skip branch of `IncrementalIndexer._process_file` now persists
the fresh mtime when `existing.mtime != parsed.mtime` — a targeted single-column
`UPDATE documents SET mtime = ?` in its own short `with self._conn:` transaction.
The write is deliberately mtime-only: the checksum covers the body alone, so a
whole-row repository update could silently persist new frontmatter title/metadata
through this skip. A touched-but-unchanged file (git checkout of identical content,
archive extract, no-op save) now converges on the first refresh instead of being
re-detected as drift on every subsequent search.

**Regression tests:**
- `tests/unit/indexing/test_drift.py::TestRefreshDrifted::test_refresh_converges_touch_only_drift`
  — `os.utime` touch with same content → `refresh_drifted` returns
  `IncrementalResult(unchanged=1)` with the fresh mtime persisted → a second
  `detect_drift` reports zero.
- `tests/unit/cli/test_search.py::TestPreSearchRefresh::test_touch_only_drift_converges_across_searches`
  — CLI end-to-end: first search refreshes and persists the touch mtime; the
  SECOND search is clean (empty stderr, and `refresh_drifted` spied as not
  called — no index_lock window opens on a clean search).

### WR-01: Drift refresh silently skips stored documents the shared predicate excludes — divergence from `sif index update` produces a second permanent drift loop

**Files modified:** `src/sif/indexing/incremental.py`, `tests/unit/indexing/test_drift.py`, `tests/unit/cli/test_search.py`
**Commit:** c30bc22
**Applied fix:** In `IncrementalIndexer.update_paths`, a path that fails the
`scanner.matches` gate is now removed when a STORED document exists at it
(mirroring `_sweep_removed` / `sif index update` semantics), counted as
`removed`; never-indexed paths with no stored row remain harmless no-ops. The
`update_paths` docstring documents the removal semantics. Chosen over the
alternative (making `detect_drift` skip predicate-excluded stored paths when
counting) because removal eliminates the write-path divergence the finding
describes — both write paths now agree — and keeps `FileScanner.matches` the
ONE membership predicate with a single removal semantic everywhere, per
12-D07's single-predicate principle. Drift now converges: the excluded stored
doc is removed on the first refresh instead of being skipped as drift forever.

**Regression tests:**
- `tests/unit/indexing/test_drift.py::TestRefreshDrifted::test_predicate_excluded_stored_doc_removed_and_converges`
  — index two docs, then set `watch_ignore_patterns=["secret*"]`: detect
  reports the excluded doc as drift, refresh removes it
  (`result.removed == 1`), and a re-detect under the same settings regime
  reports zero drift.
- `tests/unit/cli/test_search.py::TestPreSearchRefresh::test_ignored_stored_doc_converges_across_searches`
  — CLI end-to-end under the ignoring settings: first search removes the
  excluded doc (stored paths equal the surviving doc); the SECOND search is
  clean (empty stderr, `refresh_drifted` spied as not called).

### WR-02: "refreshed N files" notice reports the pre-refresh drift count and discards the actual refresh result

**Files modified:** `src/sif/cli/commands/search.py`, `tests/unit/cli/test_search.py`
**Commit:** b39164d
**Applied fix:** `_pre_search_refresh` now consumes the `IncrementalResult`
returned by `refresh_drifted` instead of discarding it. A new
`_refresh_notice(result)` helper builds the line from actual outcomes:
`refreshed {added+updated} files[, removed N] (bm25) before search` — so a
deletion is no longer announced as a "refresh" and a no-op checksum skip is
no longer claimed as work. The D-07 locked shape is preserved: one stderr
line via `console_err` (stdout stays clean for `--json`/`--csv`), `-q`
suppresses, silence on the clean path. The helper extraction also keeps
`_pre_search_refresh` within the mccabe-10 complexity limit.

**Test updates:**
- `test_search_finds_new_file_and_drops_deleted_file` now expects the truthful
  `refreshed 1 files, removed 1 (bm25) before search` (previously asserted the
  buggy "refreshed 2 files" for one add + one delete).
- The CR-01 and WR-01 convergence tests pin the new wording for their
  first-search notices (`refreshed 0 files (bm25) before search` and
  `refreshed 0 files, removed 1 (bm25) before search`).
- Pure-update notice assertions elsewhere (`refreshed 1 files` / `refreshed 3
  files` in test_search.py and test_index_locking.py) are unchanged — that
  wording shape is identical under the new code.

## Verification

**Where verification ran:** the main checkout (`.planning/config.json` has
`workflow.use_worktrees: false`, so edits and commits landed directly on
`dev` — no isolated worktree was created).

- Per fix: targeted batteries (`tests/unit/indexing/`, `tests/unit/cli/test_search.py`,
  `tests/unit/cli/test_index_locking.py`), `ast.parse` syntax checks, and
  `ruff check`/`ruff format --check` on the touched files — all green at each
  atomic commit.
- Final full gates (all three commits in place):
  - `env -u FORCE_COLOR NO_COLOR=1 python -m pytest` — 1228 passed, 1 skipped,
    coverage 94.45% (fail_under=90 met)
  - `ruff check src tests` — clean
  - `ruff format --check src tests` — clean
  - `ty check src/sif` — clean

## Skipped Issues

None — all three in-scope findings were fixed. No conflicts with locked
CONTEXT decisions were encountered: all fixes honor D-02 (stateless walk),
D-05/D-06 (count-first cap), D-07 (stderr/stdout/-q contract), and the
12-D06/12-D07 `update_paths` seam and single-predicate principles.

---

_Fixed: 2026-11-08T04:33:03Z_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_
