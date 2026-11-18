---
phase: quick-261112-qto
plan: 01
subsystem: infra
tags: [broken-windows-ledger, cli, click, caplog, coverage-gate]

# Dependency graph
requires:
  - phase: 261105-g1u
    provides: the deferred-items report that first logged the group-callback mkdir side effect
provides:
  - Broken Windows ledger at 0 open / 3 waived / 7 fixed / 10 total, unblocking the workflow.windows_enforce ship gate
  - CLI group callback that no longer materializes the index parent directory for guarded read-only commands
  - Regression pin proving Database.__init__ is the sole owner of index-parent creation
affects: [261112-qtj batch completion, gsd-ship windows gate]

actuals:
  tokens: 3800
  tasks: 2
  commits: 2

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Filesystem side effects for guarded read commands stay behind the shared DB-open boundary"

key-files:
  created: []
  modified:
    - .planning/WINDOWS.md
    - src/sif/cli/main.py
    - tests/unit/cli/test_main.py

key-decisions:
  - "Removed the unconditional group-callback parent mkdir instead of gating it per command: Database.__init__ already creates the parent inside open_initialized_database's OSError remedy boundary, so index-creating commands keep both behavior and the clean error."
  - "Waived ledger entries 1, 2, and 8 rather than forcing fixes: each is a deliberate scope boundary or structurally unautomatable/historical constraint, re-validated live before waiving."

patterns-established:
  - "Guarded-read side-effect pin: invoke the top-level CLI against an absent nested --index path and assert the parent directory is untouched."

requirements-completed: []

coverage:
  - id: D1
    description: "Broken Windows ledger cleaned to 0 open / 3 waived / 7 fixed / 10 total through its own verbs, with the markdown table regenerated from the authoritative JSON block"
    verification:
      - kind: other
        ref: "node ~/.claude/gsd-core/bin/gsd-tools.cjs windows status (asserted counts, per-id statuses, reasons, resolved_at)"
        status: pass
    human_judgment: false
  - id: D2
    description: "CLI group callback no longer creates the index parent; guarded context add/list leave the filesystem untouched while index update still creates parent and DB"
    verification:
      - kind: unit
        ref: "tests/unit/cli/test_main.py#TestGroupCallbackDoesNotCreateIndexParent"
        status: pass
    human_judgment: false
  - id: D3
    description: "Caplog evidence pair for ledger entries 3 and 4 passes when run together"
    verification:
      - kind: unit
        ref: "python -m pytest tests/test_docs.py tests/unit/embedding/test_openai_embedder.py -q --no-cov (31 passed)"
        status: pass
    human_judgment: false

duration: 5min
completed: 2026-11-12
status: complete
---

# Quick 261112-qto: Clean the Broken Windows Ledger Summary

**Ledger driven to 0 open / 3 waived / 7 fixed / 10 total through its own verbs, plus removal of the CLI group-callback index-parent mkdir pinned by two regression tests**

## Performance

- **Duration:** ~5 min
- **Started:** 2026-11-12T11:51:35Z
- **Completed:** 2026-11-12T11:56:12Z
- **Tasks:** 2/2
- **Files modified:** 3 (`src/sif/cli/main.py`, `tests/unit/cli/test_main.py`, `.planning/WINDOWS.md`)

## Accomplishments

- Removed the unconditional `ctx.obj["index_path"].parent.mkdir(...)` block from the top-level `cli` group callback and narrowed the import to `open_initialized_database`; `Database.__init__` (inside the shared DB-open `OSError` remedy boundary) remains the single owner of index-parent creation.
- Added `TestGroupCallbackDoesNotCreateIndexParent` with a guarded-command side-effect pin (`context list`, `context add path`) and an `index update` positive control; updated the now-stale `TestIndexPathCreationError` docstring.
- Closed all six open ledger entries through `gsd-tools windows fixed/waive`: 3, 4, 5 fixed; 1, 2, 8 waived with explicit, re-validated reasons. The tool regenerated the markdown table so it agrees with the authoritative JSON block.
- Full quality gate green: `ruff check src tests`, `ruff format --check src tests`, and `pytest -q --ignore=tests/unit/cli/test_probe_qtn.py` → 1609 passed, 1 skipped @ 95.25% coverage (fail_under=90).

## Task Commits

Each task was committed atomically:

1. **Task 1: Remove the group-callback mkdir and pin DB-open ownership of parent creation** - `bace245` (fix)
2. **Task 2: Close all six open ledger entries through gsd-tools and run the full quality gate** - `9c8d6b6` (docs)

## Ledger Before / After

| field | before | after |
|-------|--------|-------|
| open_count | 6 | 0 |
| waived_count | 0 | 3 |
| fixed_count | 4 | 7 |
| total_count | 10 | 10 |

Final dispositions:

| id | final status | disposition / reason (verbatim summary) |
|----|--------------|------------------------------------------|
| 1 | waived | Deliberate design boundary re-validated at HEAD: the HuggingFace branch in `src/sif/embedding/factory.py:86-92` is an intentional `NotImplementedError` stub documented in CLAUDE.md and rejected by ModelType/settings validation; not a supported backend, so no fix is planned. |
| 2 | waived | Manual-only verification re-validated: a live OpenAI-compatible endpoint check requires a user-supplied API key and an external endpoint, so it cannot run in this repo or CI; automated tests mock the endpoint and exercise the request/response path. Structurally unautomatable. |
| 3 | fixed | Caplog evidence pair re-run together: `tests/test_docs.py` + `tests/unit/embedding/test_openai_embedder.py` → 31 passed. |
| 4 | fixed | Same 31-passed pair run; the two formerly-polluted caplog tests (`test_import_error_logs_install_hint`, `test_corrupt_cache_treated_as_miss`) are green. |
| 5 | fixed | Group-callback mkdir removed in `bace245`; guarded `context add/list` now create neither the parent nor the DB, verified by the new regression tests. |
| 8 | waived | Historical plan artifact re-validated: the 10.1-01 verify command scoped two test files under the repo-wide `fail_under=90` gate, structurally cannot exit 0 (~38% scoped total); signal verified via `--no-cov` plus full-suite 968-pass at 96.22%, and phase 10.1 is complete with the plan archived under `.planning/milestones/v1.0-phases/`. Waived as a past planning-constraint record. |

The six untouched entries (6, 7, 9, 10 fixed; ids preserved) were verified to keep their original id/kind/phase/file/line/description/recorded_at fields; the diff is 25 insertions / 25 deletions confined to the changed rows, frontmatter counts, and `last_updated`.

## Files Created/Modified

- `src/sif/cli/main.py` - Deleted the group-callback parent mkdir + `_database_remedy` import; two-line ownership comment added.
- `tests/unit/cli/test_main.py` - New `TestGroupCallbackDoesNotCreateIndexParent` (2 tests); stale CR-01 docstring updated.
- `.planning/WINDOWS.md` - Verb-regenerated table, frontmatter counts, and JSON statuses/reasons/resolved_at.

## TDD Gate Compliance

- **RED:** `pytest tests/unit/cli/test_main.py::TestGroupCallbackDoesNotCreateIndexParent -q --no-cov` → 1 failed, 1 passed. The guarded test failed exactly on `assert not db_path.parent.exists()` (the group callback had created `never-created/`); the positive control passed. Failure occurred in assertion, not collection/setup.
- **GREEN:** `pytest tests/unit/cli/test_main.py tests/unit/cli/test_context.py tests/unit/cli/test_error_conventions.py tests/unit/db/test_database.py -q --no-cov` → 75 passed; ruff check and format clean.
- **REFACTOR:** none needed.

## Verification Evidence

- Evidence pair: `python -m pytest tests/test_docs.py tests/unit/embedding/test_openai_embedder.py -q --no-cov` → **31 passed**.
- End-to-end CLI: `--index <tmp>/never-created/sif.db context list` and `context add path ...` both exit 0 with "No index found" and leave the parent absent; `--index <tmp>/fresh/sif.db index update` exits 0, prints the no-collections guidance, creates parent + DB; a regular file in the parent path renders the remedy-bearing "Cannot open index database at ..." message with no traceback.
- Ledger assertion (plan verify script): 0 open / 3 waived / 7 fixed / 10 total; ids 3/4/5 fixed; ids 1/2/8 waived with non-empty reasons; every entry has `resolved_at`.
- Quality gate: ruff check and format clean; `pytest -q --ignore=tests/unit/cli/test_probe_qtn.py` → **1609 passed, 1 skipped, 95.25% coverage** (floor 90%).

## Decisions Made

- Remove rather than guard the group mkdir: the DB-open boundary already owns parent creation (37 call sites through `open_initialized_database`/`_unmanaged`), so gating per command would duplicate ownership and leave a second code path.
- Waive rather than invent fixes for entries 1, 2, and 8: each is deliberate scope, externally blocked (API key), or historical; all were re-validated against HEAD before waiving.

## Deviations from Plan

None - plan executed exactly as written. The plan's `--ignore=tests/unit/cli/test_probe_qtn.py` was harmless because the sibling probe file was already absent.

## Issues Encountered

None. `gsd-tools` is not on PATH in this environment; the plan's documented fallback `node "$HOME/.claude/gsd-core/bin/gsd-tools.cjs" windows ...` was used.

## Sibling-Item Artifacts Left Untouched

Observed untracked/modified sibling state, never staged or reverted: `.planning/agent-history.json`, `.planning/quick/`, `.planning/quick-batches/261112-qtj/`, `.planning/research/.cache/*.json`, `.planning/state.json`, `.planning/tmp/`. `tests/unit/cli/test_probe_qtn.py` (sibling planner probe) was already deleted by its owner before this item ran. `src/sif/search/bm25.py`, `src/sif/utils/daemon.py`, `src/sif/indexing/watcher.py`, and `src/sif/cli/commands/watch.py` were not modified.

## Next Phase Readiness

- `workflow.windows_enforce` ship gate is unblocked (`open_count` is 0).
- The orchestrator still owns committing this SUMMARY and the batch-level STATE/ROADMAP updates.

---
*Quick item: 261112-qto*
*Completed: 2026-11-12*

## Self-Check: PASSED

- All declared files exist (SUMMARY.md, .planning/WINDOWS.md, src/sif/cli/main.py, tests/unit/cli/test_main.py).
- Both task commits (`bace245`, `9c8d6b6`) are ancestors of HEAD.
- No uncommitted changes remain in this item's declared files.
