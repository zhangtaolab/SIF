---
phase: quick-261111-pqy
plan: 01
subsystem: cli
tags: [click, pathlib, collection-ls, path-filter, pytest, code-review-closure]

requires:
  - phase: 10-raise-pytest-coverage-to-90
    provides: "10-REVIEW.md finding WR-05 and the 10-REVIEW-DISPOSITION.md ledger"
  - phase: quick-261111-nj0
    provides: "Shipped WR-04 collection-relative segment-aligned predicate in ls.py:53-57 (reference mirrored here)"
provides:
  - "collection ls subpath filter resolves collection-relative subpaths against the collection root and matches whole path segments"
  - "Five-test regression contract in tests/unit/cli/test_collection.py (relative, absolute, exact-file, trailing-slash, no-match) plus a no-subpath preservation leg"
  - "Phase 10 WR-05 recorded fixed in both ledger representations; open count 19 -> 18"
affects: [future-collection-ls-or-path-filter-work, phase-10-review-backlog]

actuals:
  tokens: 1884
  tasks: 2
  commits: 4
plan_head_before: d86bb8a60d47413c44117fb18d0922db58d1732a
plan_head_after: 1ac9f2454838406bd7254474a602261da3e54b2c

tech-stack:
  added: []
  patterns:
    - "Path-predicate matching on resolved absolute scan paths: join relative input onto the collection root, keep the leading slash, compare equality-or-prefix-with-separator (same predicate as shipped WR-04 ls.py:53-57, str(Path) adaptation)"

key-files:
  created: []
  modified:
    - src/sif/cli/commands/collection.py
    - tests/unit/cli/test_collection.py
    - .planning/milestones/v1.0-phases/10-raise-pytest-coverage-to-90/10-REVIEW-DISPOSITION.md

key-decisions:
  - "Mirrored the shipped WR-04 predicate exactly (keep leading slash, rstrip trailing separators, equality-or-prefix + '/'), comparing str(f) because FileScanner.scan yields Path objects"
  - "No resolve()/normpath added: collection_add stores resolved roots and FileScanner.scan resolves before rglob; extra normalization would change symlink/.. semantics beyond the finding"
  - "Filter applied BEFORE the existing empty check so a non-matching subpath reuses the existing 'No files found in collection.' message (exit 0); tree rendering stays collection-root-relative"
  - "New sibling_notes_dir fixture and five tests follow the file's established real-SQLite/real-tmp_path convention; all 19 existing tests unmodified (diff vs baseline is purely additive: 74 insertions, 0 deletions)"

requirements-completed: [PHASE10-WR-05]

coverage:
  - id: D1
    description: "sif collection ls subpath resolves collection-relative and matches whole segments; absolute, exact-file, and trailing-slash forms agree; no-match exits 0 with the existing no-files message; no-subpath listing unchanged"
    requirement: "PHASE10-WR-05"
    verification:
      - kind: unit
        ref: "tests/unit/cli/test_collection.py#TestCollectionRealDatabase::test_ls_subpath_is_segment_aligned"
        status: pass
      - kind: unit
        ref: "tests/unit/cli/test_collection.py#TestCollectionRealDatabase::test_ls_subpath_absolute_is_segment_aligned"
        status: pass
      - kind: unit
        ref: "tests/unit/cli/test_collection.py#TestCollectionRealDatabase::test_ls_subpath_exact_file"
        status: pass
      - kind: unit
        ref: "tests/unit/cli/test_collection.py#TestCollectionRealDatabase::test_ls_subpath_trailing_slash"
        status: pass
      - kind: unit
        ref: "tests/unit/cli/test_collection.py#TestCollectionRealDatabase::test_ls_subpath_no_match_reports_no_files"
        status: pass
      - kind: unit
        ref: "tests/unit/cli/test_collection.py#TestCollectionRealDatabase::test_ls_with_subpath_and_without_files"
        status: pass
    human_judgment: false
  - id: D2
    description: "WR-05 alone fixed in the Phase 10 disposition ledger (YAML + table), open count 18/22, every other record byte-identical"
    requirement: "PHASE10-WR-05"
    verification:
      - kind: other
        ref: "python -I exact-baseline reconstruction gate (Task 2 verify): printed WR-05-fixed; all-other-ledger-content-unchanged"
        status: pass
    human_judgment: false

duration: 11min
completed: 2026-11-11
status: complete
---

# Quick 261111-pqy Plan 01: Phase 10 WR-05 — collection ls subpath filter Summary

**`collection ls <name> <subpath>` now filters the disk scan collection-relative and segment-aligned (mirroring the shipped WR-04 predicate), pinned by five real-SQLite regression tests, with WR-05 closed in the Phase 10 ledger (open 19 -> 18)**

## Performance

- **Duration:** 11 min
- **Started:** 2026-11-11T10:47:55Z
- **Completed:** 2026-11-11T10:58:30Z
- **Tasks:** 2
- **Files modified:** 3

## Selected Finding and Per-Finding Selection Assessment

**Selected: Phase 10 WR-05** — `collection_ls` (collection.py:334) declared `subpath`, silenced it with `# noqa: ARG001`, and never used it: `sif collection ls notes python` returned the full listing. Live-reproduced at planning time (HEAD d86bb8a) against a real temporary SQLite index and a real on-disk root with `python/a.md` and `python2/b.md`. Smallest safe live item: one production file, a pure filter over the existing read-only disk scan, mirroring an already-shipped and tested predicate, no interface/protocol/documentation change.

Per-finding assessment (all re-verified live at HEAD d86bb8a during planning):

| Finding | Assessment | Disposition this task |
|---------|-----------|----------------------|
| WR-05 | SELECTED — live (noqa + unused subpath); unblocked by the shipped WR-04 predicate (quick 261111-nj0, commit 68f4101) | Fixed |
| WR-02 | STALE — Phase 11 retired the whole-run transaction; `update_cmd` (index.py:44-111) delegates to `IncrementalIndexer`, one short BEGIN IMMEDIATE transaction per file (incremental.py:5-6, 332-335, D-04 "earlier files stay durable") — stronger than the requested fix | Record stays open; staleness triage is a separate task |
| WR-06 | STALE — bench.py:622-627 wraps fixture json.load in ClickException, 631-635 wraps evaluator construction, 671-681 wraps evaluation | Record stays open |
| WR-08 | Convention-conflicting — contradicts the documented fail-fast vector posture (CLAUDE.md: VectorSearcher fails fast; HybridSearcher vector exceptions propagate uncaught) | Not smallest-safe; untouched |
| WR-01 | Broader — embedding purge needs index.py's purger helper or a new shared module plus repositories.py purge and sqlite-vec availability handling (multi-file); lives in collection_remove, not touched | Untouched |
| WR-07 | Broader — handling max_lines alone changes MCP line_start/line_end metadata from None/None to 1/N (protocol-contract decision) | Untouched |
| WR-09 | Broader — fix spans read side (main.py:257-263) and write side (repositories.py:551) in two production files plus tests | Untouched |

## Accomplishments

- `collection ls` subpath argument now actually filters: relative subpaths resolve against the collection root, matching is segment-aligned (`python` selects `python/a.md`, never `python2/b.md`), and absolute / exact-file / trailing-slash forms agree
- Non-matching subpath exits 0 with the existing "No files found in collection." message (filter applied before the empty check; no new message or second empty branch)
- Five new regression tests in the file's established real-SQLite style, demonstrably red at baseline and green after the fix; no-subpath preservation leg and all 19 existing tests pass unmodified
- WR-05 closed in both ledger representations (YAML disposition + markdown row), open count 19 -> 18, exact baseline reconstruction proves every other record byte-identical
- Full quality suite green: 1519 passed, 1 skipped, 95.02% coverage (fail_under=90 reached)

## Task Commits

Each task was committed atomically (TDD Task 1 produced RED -> GREEN -> style commits):

1. **Task 1 RED: failing regression tests** - `d92240a` (test)
2. **Task 1 GREEN: collection ls subpath filter** - `0eee1e4` (feat)
3. **Task 1 formatting: ruff format collapse of the new test signature** - `af162a5` (style)
4. **Task 2: close WR-05 in the Phase 10 disposition ledger** - `1ac9f24` (docs)

_No REFACTOR commit: the implementation is a minimal mirror of the shipped WR-04 predicate; no cleanup was needed. Plan metadata commit is handled by the orchestrator (quick-task docs/state commit)._

## TDD Evidence (Task 1, red-to-green)

**RED** (before any production edit, at baseline d86bb8a + new tests):
`env -u FORCE_COLOR NO_COLOR=1 python -m pytest tests/unit/cli/test_collection.py -q --no-cov --junitxml=.../red-task1.xml` -> exit 1, **5 failed, 19 passed in 1.55s**.

- The four selection tests failed on `assert "b.md" not in result.output` — the ignored subpath listed both `python/a.md` and `python2/b.md` (defect confirmed: argument ignored).
- `test_ls_subpath_no_match_reports_no_files` failed on `assert "No files found in collection." in result.output` — the full listing was printed instead of the message.
- All failures were planned output assertions; no collection, setup, fixture, import, or unrelated failures. The preservation leg and all 19 existing tests passed at baseline.
- Machine validation: five per-target evidence records (`red-task1-test_*.json`, JUnit XML adapter) each returned `RED_EVIDENCE_OK` from `gsd_run check tdd-red-evidence`; semantic assessment recorded per target (target executed through the real top-level CLI / real SQLite / real tmp_path root and failed on the planned assertion for the intended reason).
- Evidence artifacts (this directory): `red-task1-start.txt`, `red-task1-console.txt`, `red-task1.xml`, five `red-task1-test_*.json` records.

**GREEN** (after the filter edit): `python -m pytest tests/unit/cli/test_collection.py -q --no-cov` -> **24 passed in 0.75s**; ruff check and ruff format --check clean on both task files.

## Files Created/Modified

- `src/sif/cli/commands/collection.py` - `collection_ls` only: removed `# noqa: ARG001`; added the subpath filter block (bind `files`, resolve relative subpaths against `Path(collection.path)`, segment-aligned equality-or-prefix on `str(f)`); empty check and tree loop now consume `files`. Scan call, no-files message, missing-collection error, tree rendering, and every other command byte-identical.
- `tests/unit/cli/test_collection.py` - added `sibling_notes_dir` fixture (sibling `python/` and `python2/` subtrees) and five regression tests to `TestCollectionRealDatabase`; purely additive vs baseline (74 insertions, 0 deletions).
- `.planning/milestones/v1.0-phases/10-raise-pytest-coverage-to-90/10-REVIEW-DISPOSITION.md` - exactly three scoped edits: WR-05 YAML `disposition: open -> fixed`, aggregate `open: 19 -> 18`, WR-05 markdown row names quick 261111-pqy. Total 22 and recorded timestamp unchanged; all other records byte-identical (gate-proven).

## Decisions Made

- Mirrored the shipped WR-04 predicate exactly (ls.py:53-57), with the single type adaptation `str(f)` for `Path` scan entries; no resolve()/normpath (stored roots and scan paths are already resolved; extra normalization would change symlink/`..` semantics beyond the finding).
- Filter before the empty check, reusing the existing no-files message for a non-matching subpath (decided in plan; no new message, no second empty branch).
- Kept the `if subpath:` truthiness guard and collection-root-relative tree rendering (`python/a.md`), consistent with the existing test assertion and ls_cmd.
- No docs regeneration: the fix changes no signature, option, or help text; generator-owned docs untouched (gate-proven).

## Deviations from Plan

None - plan executed exactly as written. The plan anticipated the formatting step ("If the formatting check complains, run ruff format on the two task files only"); the resulting one-line signature collapse was committed separately as `style` (`af162a5`) to keep the RED and GREEN commits atomic. No scope creep: WR-01/02/06..09 and all IN/CR records untouched; pre-existing `.planning/` churn never staged.

## Issues Encountered

- `ruff format --check` flagged the new `test_ls_subpath_is_segment_aligned` multi-line signature (fits on one line under the 100-char limit). Resolved by running `ruff format` on the two task files only; the collapse is formatting-only, tests still 24 passed, committed as `af162a5`.

## Verification (final gates, all from checkout root)

1. `python -m pytest tests/unit/cli/test_collection.py -q --no-cov` -> **24 passed**
2. `ruff check src tests` -> **All checks passed!**
3. `ruff format --check src tests` -> **188 files already formatted**
4. `python -m pytest` (full run with coverage gate, PATH miniconda pytest) -> **1519 passed, 1 skipped in 68.98s; Required test coverage of 90.0% reached. Total coverage: 95.02%**
5. `git diff --exit-code -- src/sif/cli/commands/ls.py tests/unit/cli/test_ls.py src/sif/mcp/backend.py src/sif/cli/commands/index.py src/sif/indexing/incremental.py src/sif/cli/commands/bench.py src/sif/cli/main.py src/sif/database/repositories.py docs/cli-reference.md docs/configuration.md` -> **exit 0 (every other finding's files, the shipped WR-04 reference, and generator-owned docs untouched)**
6. Scoped diff review: `git diff --stat d86bb8a..HEAD` shows exactly the three task-scoped files (87 insertions, 6 deletions); four commits touch only those paths; pre-existing `.planning/` churn preserved unstaged.

Threat model: T-pqy-01 (subpath filter silently ignoring the requested subtree / leaking sibling subtrees) mitigated by the collection-relative segment-aligned predicate and pinned by the five regression tests. No new network, package, authentication, or external-service boundary introduced; no threat flags.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Phase 10 review ledger now 18/22 open (WR-03, WR-04, WR-05, WR-10 fixed). Remaining live candidates: WR-01 (multi-file embedding purge), WR-07 (MCP metadata protocol decision), WR-09 (two-file timestamp fix); WR-02 and WR-06 are stale (records stay open pending a separate staleness-triage task); WR-08 conflicts with the documented fail-fast vector posture.
- Alternatively `/gsd-complete-milestone v1.1` remains available (all 6 phases complete and verified).

---
*Phase: quick-261111-pqy*
*Completed: 2026-11-11*

## Self-Check: PASSED

- FOUND: src/sif/cli/commands/collection.py
- FOUND: tests/unit/cli/test_collection.py
- FOUND: .planning/milestones/v1.0-phases/10-raise-pytest-coverage-to-90/10-REVIEW-DISPOSITION.md
- FOUND: .planning/quick/261111-pqy-next-phase-10-item-address-the-smallest-/261111-pqy-SUMMARY.md
- FOUND: d92240a (test / RED)
- FOUND: 0eee1e4 (feat / GREEN)
- FOUND: af162a5 (style / format)
- FOUND: 1ac9f24 (docs / ledger closure)
- Ledger consistency: plan_head_before d86bb8a60d47413c44117fb18d0922db58d1732a, measured commits 4, plan_head_after 1ac9f2454838406bd7254474a602261da3e54b2c — all match frontmatter.