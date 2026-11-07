---
phase: 11-live-index-foundation-concurrent-db-incremental-core
plan: 02
subsystem: indexing
tags: [incremental-indexing, sqlite, begin-immediate, per-file-transactions, extraction, click-cli]

requires:
  - phase: 11-01
    provides: shared connection factory (implicit BEGIN IMMEDIATE via with-conn blocks), index_lock wrap on update_cmd, WAL pragma recipe
provides:
  - IncrementalIndexer — the single shared per-file incremental core (roadmap SC3) with IncrementalResult counts, presentation-free progress callback, per-file BEGIN IMMEDIATE transactions (D-04)
  - Delegating update_cmd that renders the identical Added:/Updated:/Removed: block; complexity exemption and inline parse loop removed (grep gates 0 and 0)
  - Reuse entry point for Phases 12-14 watch hosts — IncrementalIndexer(conn).update_collection(coll, force=..., progress=...)
affects: [11-03, 12-watch, 13-daemon-mcp, 14-precommand]

actuals:
  tokens: 13180   # chars/4 over the realized 03f21eb..b3eea96 diff (52721 chars)
  tasks: 2
  commits: 3      # MEASURED: git rev-list --count 03f21eb..HEAD

plan_head_before: 03f21ebd3bee7a022e275ec9567fcf0559c1921f
plan_head_after: b3eea964837543185ba5607092ec3660277b5e81

tech-stack:
  added: []   # stdlib + existing deps only (zero-new-deps lock)
  patterns:
    - "Presentation-free core: the indexer emits 'code payload' progress events; the CLI callback is the only place they become Rich output"
    - "Per-file `with conn:` block = one short BEGIN IMMEDIATE transaction (D-04); removed-file sweep and per-collection stats are their own short transactions"
    - "Pre-update subprocess hook is command policy and stays in the CLI; hosts decide their own pre-behavior"

key-files:
  created:
    - src/sif/indexing/incremental.py
    - tests/unit/indexing/test_incremental.py
    - tests/integration/test_incremental_equivalence.py
  modified:
    - src/sif/cli/commands/index.py
    - tests/unit/cli/test_collection.py

key-decisions:
  - "Progress callback protocol is short 'code payload' events (scan/unchanged/error/indexed): the core imports no rich/click symbols and the CLI's _render_index_event is the only place events become console lines and progress advances"
  - "Per-file loop body split into _process_file/_sweep_removed helpers to hold mccabe complexity <=10 with no noqa exemption; MarkdownParser became indexer instance state to satisfy PLR0913"
  - "RED phase committed an importable zero-behavior skeleton with the failing tests so the suite collects and fails on assertions, not import errors; the giant pre-extraction `with db.connection:` transaction is gone (11-PATTERNS extraction directive)"

patterns-established:
  - "Incremental indexing goes through sif.indexing.incremental.IncrementalIndexer — never re-implement the scan/checksum/parse/write loop"
  - "Indexer cores take a progress callback and stay presentation-free; Rich lives only in the CLI"

requirements-completed: [LIVE-06, LIVE-07]

coverage:
  - id: D1
    description: "IncrementalIndexer per-file incremental core: add/update/unchanged-skip/force, D-04 per-failure durability, removed-file purge-before-delete (WR-01), stats recount, empty scan"
    requirement: LIVE-06
    verification:
      - kind: unit
        ref: "tests/unit/indexing/test_incremental.py#TestIncrementalIndexer"
        status: pass
    human_judgment: false
  - id: D2
    description: "Delegating update_cmd renders the identical Added:/Updated:/Removed: block with lock wrap, pre-update hook, and Rich progress retained in the CLI"
    requirement: LIVE-06
    verification:
      - kind: unit
        ref: "tests/unit/cli/test_collection.py#TestIndexPreUpdateHook (patch target updated, 3/3 pass)"
        status: pass
      - kind: integration
        ref: "tests/integration/test_embed_idempotency.py (unmodified, passing)"
        status: pass
    human_judgment: false
  - id: D3
    description: "Golden equivalence proof (SC3): identical index state and CLI counts across add/modify/delete/idempotent cycles incl. FTS external-content trigger sync"
    verification:
      - kind: integration
        ref: "tests/integration/test_incremental_equivalence.py#TestIncrementalEquivalence"
        status: pass
    human_judgment: false
  - id: D4
    description: "Watch-host reuse entry point for Phases 12-14: IncrementalIndexer(conn).update_collection(collection, force=..., progress=...) with no Rich dependency"
    verification:
      - kind: unit
        ref: "tests/unit/indexing/test_incremental.py (every test exercises the constructor + update_collection signature directly)"
        status: pass
    human_judgment: false

duration: 12 min
completed: 2026-11-07
status: complete
---

# Phase 11 Plan 02: IncrementalIndexer Extraction Summary

**Per-file incremental indexing core (IncrementalIndexer) extracted from update_cmd into one shared presentation-free loop with per-file BEGIN IMMEDIATE transactions (D-04), proven golden-equivalent on index state and CLI output (SC3)**

## Performance

- **Duration:** 12 min (06:22–06:35 UTC)
- **Started:** 2026-11-07T06:22:42Z
- **Completed:** 2026-11-07T06:35:30Z
- **Tasks:** 2/2
- **Files modified:** 5 (3 created, 2 modified)
- **Suite:** 1052 passed @ 96.34% (fail_under=90 honored; +11 tests vs 11-01's 1041); ruff, format, ty all green

## TDD Gate Compliance

Task 1 (`tdd="true"`) ran the full task-scoped RED→GREEN cycle with machine-verified RED evidence (`gsd_run check tdd-red-evidence` → `RED_EVIDENCE_OK`; record in `.planning/tmp/tdd-red-11-02-task1.json`):

| Task | RED commit | RED failure (target test, planned reason) | GREEN commit |
|------|-----------|-------------------------------------------|--------------|
| 1 | `9ceebcb` test(11-02) | `test_new_file_added_and_document_row_exists`: `assert IncrementalResult(0,0,0) == (added=1,...)` — all 8 planned-behavior tests failed on their assertions against the zero-behavior skeleton | `03230cd` feat(11-02) |

REFACTOR: the lint-forced helper extraction (`_process_file`/`_sweep_removed`/`_notify`) landed inside the GREEN commit; no separate changes after GREEN, so no refactor commit. Task 2 is a test-only golden proof (`b3eea96`) and not TDD-marked.

## Accomplishments

- `src/sif/indexing/incremental.py`: the one incremental loop (SC3) — scan, checksum-skip, per-file `with conn:` transaction wrapping chunk purge + embedding purge + document write (D-04), removed-file sweep and stats as their own short transactions; CR-01/WR-01 ordering comments preserved; BM25-only; no rich/click imports
- `update_cmd` rewritten as a delegating renderer: Click shape, lock wrap, pre-update hook (extracted to `_run_pre_update_hook`, still CLI policy), Rich Progress retained via the event callback, identical counts block; the `noqa: C901, PLR0912, PLR0915` exemption and inline `parser.parse` loop are gone (grep gates 0 and 0; recorded baselines 1 and 1)
- Unit proofs incl. D-04 mid-run durability (first file committed durable through a fresh connection, failing file not half-written, third file untouched) and WR-01 purge-before-delete ordering
- Golden equivalence proof: add/modify/delete/idempotent cycles through the real CLI against a real DB — documents/FTS 1:1 (external-content triggers through per-file commits), deleted doc absent from `documents_fts`, CR-01 stale-chunk purge on edit, third run all zeros

## Task Commits

1. **Task 1 RED: failing IncrementalIndexer unit tests + skeleton** - `9ceebcb` (test)
2. **Task 1 GREEN: extract IncrementalIndexer with per-file transactions** - `03230cd` (feat)
3. **Task 2: golden equivalence proof (SC3)** - `b3eea96` (test)

**Plan metadata:** final docs commit (below)

## Files Created/Modified

- `src/sif/indexing/incremental.py` - NEW: IncrementalIndexer + IncrementalResult + private `_embedding_purger`/`_process_file`/`_sweep_removed`; progress-event protocol documented on `update_collection`
- `src/sif/cli/commands/index.py` - update_cmd delegates; `_run_pre_update_hook` + `_render_index_event` helpers; unused imports (Document, FileScanner, MarkdownParser, TYPE_CHECKING VectorSearcher, `_embedding_purger`) removed; embed_cmd untouched (D-05)
- `tests/unit/indexing/test_incremental.py` - NEW: 8 unit proofs (SC3/D-04 row)
- `tests/integration/test_incremental_equivalence.py` - NEW: 3-test golden cycle (SC3 row)
- `tests/unit/cli/test_collection.py` - FileScanner patch targets moved to `sif.indexing.incremental` (3 tests)

## Decisions Made

- See key-decisions in frontmatter (progress-event protocol, complexity-driven helper split, RED skeleton approach).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] FileScanner patch targets moved with the extraction**
- **Found during:** Task 1 (GREEN, running tests/unit/cli)
- **Issue:** The three pre-update-hook tests patch `sif.cli.commands.index.FileScanner`; the extraction moved FileScanner out of the CLI module and ruff F401 required dropping the import, so `patch(...)` would raise AttributeError against a missing module attribute
- **Fix:** The three patch targets now point at `sif.indexing.incremental.FileScanner` (the classes' new import site); assertions unchanged
- **Files modified:** tests/unit/cli/test_collection.py
- **Verification:** All 3 pre-update-hook tests pass; full tests/unit/cli suite 213 passed
- **Committed in:** 03230cd

**2. [Rule 1 - Plan-spec adjustment] Golden-cycle test split into three phase tests**
- **Found during:** Task 2 (ruff gate)
- **Issue:** The plan describes one walkthrough test; as a single method it hit PLR0915 (64 statements > 50), and the initial Task 2 commit briefly carried that violation (pre-commit hooks do not run ruff here)
- **Fix:** Split into `test_first_run_indexes_fixture_tree`, `test_mutation_run_tracks_modify_delete_and_add`, `test_third_run_is_idempotent` sharing `_advance_to_after_first_run`/`_mutate_tree` helpers; fixed a RUF059 unused-unpack; amended into the Task 2 commit
- **Files modified:** tests/integration/test_incremental_equivalence.py
- **Verification:** ruff clean; 3/3 pass; all four plan acceptance criteria still asserted
- **Committed in:** b3eea96

---

**Total deviations:** 2 auto-fixed (1 Rule 3 blocker, 1 plan-spec adjustment)
**Impact on plan:** Both fixes required by the extraction itself (patch-site moves) and project lint gates. No scope creep; plan intent (SC3, D-04) fully preserved.

## Issues Encountered

- Single-file `pytest` runs trip the project-wide coverage addopts (`fail_under=90` over a partial run) — plan `<verify>` commands run with the project-standard `--no-cov` escape for partial suites; the full-suite gate ran on plain `pytest` (96.34%).
- RED-phase note: an importable zero-behavior skeleton was committed with the failing tests so the suite collects (test infrastructure); the classifier validated the target test failing on a real assertion.

## Authentication Gates

None — no external services in this plan.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Ready for Plan 03 (dead-code retirement D-07): the loop now exists in exactly one place, so `DocumentIndexer` (indexer.py), `ConnectionPool`, and the legacy duplicate `DatabaseConnection` can be deleted; watcher TYPE_CHECKING refs repoint to IncrementalIndexer
- Phases 12-14 watch hosts reuse `IncrementalIndexer(conn).update_collection(...)` directly; the progress-event contract is documented on the method docstring
- The pre-update hook remains CLI-side by design — MCP/watch hosts own their pre-behavior

## Self-Check: PASSED

All 5 key files exist on disk; all 3 task commits (9ceebcb, 03230cd, b3eea96) are ancestors of HEAD; `plan_head_before=03f21eb`, `plan_head_after=b3eea96`, commits measured = 3; evaluation-scope resolved 5 changed files on this branch.

---
*Phase: 11-live-index-foundation-concurrent-db-incremental-core*
*Completed: 2026-11-07*
