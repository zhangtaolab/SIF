---
phase: 14-freshness-floor-pre-command-refresh-staleness-marking
fixed_at: 2026-11-08T05:15:31Z
review_path: .planning/phases/14-freshness-floor-pre-command-refresh-staleness-marking/14-REVIEW.md
iteration: 2
findings_in_scope: 4
fixed: 4
skipped: 0
status: all_fixed
---

# Phase 14: Code Review Fix Report

**Fixed at:** 2026-11-08T05:15:31Z
**Source review:** `.planning/phases/14-freshness-floor-pre-command-refresh-staleness-marking/14-REVIEW.md`
**Iteration:** 2 (iteration 1 fixed CR-01, WR-01, WR-02 of the initial review; this iteration appends WR-01 of the 2026-11-08 incremental re-review)

**Summary:**
- Findings in scope: 4 (CR-01, WR-01, WR-02 — per iteration-1 fix directive; plus the re-review's new WR-01)
- Fixed: 4
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

### WR-01: Parse-failed drifted files never converge and their errors are silently swallowed — every search re-locks, re-fails, and prints "refreshed 0 files (bm25) before search" forever

**Files modified:** `src/sif/indexing/incremental.py`, `src/sif/indexing/drift.py`, `src/sif/cli/commands/search.py`, `tests/unit/indexing/test_drift.py`, `tests/unit/cli/test_search.py`
**Commit:** this report rides the fix commit itself — `fix(14): WR-01 surface parse failures in refresh notice and count them`
**Applied fix (iteration 2, re-review WR-01):** Parse failures are now counted
and visible end to end instead of silently swallowed:

- `IncrementalResult` gains a `failed` count, propagated through both
  `update_collection` and `update_paths` (and accumulated by
  `refresh_drifted`'s totals). `_process_file`'s except branch returns a
  distinct `"error"` outcome — no longer folded into `"skipped"`/`unchanged` —
  and adds `logger.warning("Error parsing %s: %s", ...)`, which matters most
  on the callback-less pre-search host where `_notify` alone no-opped.
- `_refresh_notice` names the failures (`..., M failed to parse (bm25) before
  search`), and `_pre_search_refresh` renders that notice as a **yellow
  warning** (instead of dim) when `result.failed > 0` — still exactly one
  stderr line via `console_err` (D-07: stdout clean for `--json`/`--csv`,
  `-q` suppresses, silent when clean). The per-file detail rides the
  logger.warning; the notice carries the count.
- **Mtime decision, made explicit:** a parse-failed file deliberately does
  NOT converge its stored mtime — the stored content is genuinely stale, and
  pretending fresh would hide an unreadable file behind a checksum the
  parser can never recompute. The file stays drift-visible and re-warns on
  every search until it is fixed or removed; what the fix removes is the
  *silence* (and the misleading "refreshed 0 files" that read as a clean
  refresh), so the budget burn toward `search_refresh_max_files` is now
  visible. Documented in the `update_paths` docstring, the `_process_file`
  except-branch comment, and both regression test names/docstrings.
- `parser.py` untouched: its unguarded `read_text` is the failure surface,
  and the chosen mechanism surfaces the failure at the loop/notice level
  rather than special-casing the reader.

**Regression tests:**
- `tests/unit/indexing/test_drift.py::TestRefreshDrifted::test_unparseable_drift_counts_failed_and_stays_drift_visible`
  — invalid-UTF-8 drift (content-based `write_bytes(b"\xff\xfe...")`, no
  chmod platform flakiness) refreshes to
  `IncrementalResult(unchanged=0, failed=1)` with the stored row untouched
  (stale content, unconverged mtime) and drift still 1 — deliberate, and now
  counted rather than silent.
- `tests/unit/cli/test_search.py::TestPreSearchRefresh::test_unparseable_drift_warns_each_search_and_never_converges`
  — CLI end-to-end: first search shows the yellow-counted warning
  (`refreshed 0 files, 1 failed to parse (bm25) before search`), exit 0,
  stale results still served; the SECOND search warns again (the loop is
  visible, not converged away); the stored mtime/content are untouched; and
  `-q` suppresses the notice line (the underlying logger.warning may still
  ride stderr — logging is error output).

## Verification

**Where verification ran:** the main checkout (`.planning/config.json` has
`workflow.use_worktrees: false`, so edits and commits landed directly on
`dev` — no isolated worktree was created).

- Per fix: targeted batteries (`tests/unit/indexing/`, `tests/unit/cli/test_search.py`,
  `tests/unit/cli/test_index_locking.py`), `ast.parse` syntax checks, and
  `ruff check`/`ruff format --check` on the touched files — all green at each
  atomic commit.
- Iteration-2 fix: targeted battery over `test_drift.py`, `test_search.py`,
  `test_incremental.py` (148 passed) including the five protected
  convergence/failure tests (touch-only, predicate-excluded, refresh-failure
  — all still green), then full gates below.
- Final full gates (all four fixes in place):
  - `env -u FORCE_COLOR NO_COLOR=1 python -m pytest` — 1231 passed, 1 skipped,
    coverage 94.55% (fail_under=90 met)
  - `ruff check src tests` — clean
  - `ruff format --check src tests` — clean
  - `ty check src/sif` — clean

## Skipped Issues

None — all four in-scope findings were fixed. No conflicts with locked
CONTEXT decisions were encountered: all fixes honor D-02 (stateless walk),
D-05/D-06 (count-first cap), D-07 (stderr/stdout/-q contract), and the
12-D06/12-D07 `update_paths` seam and single-predicate principles.

---

_Fixed: 2026-11-08T05:15:31Z_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 2_
