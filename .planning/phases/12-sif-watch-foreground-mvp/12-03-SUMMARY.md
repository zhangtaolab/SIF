---
phase: 12-sif-watch-foreground-mvp
plan: 03
subsystem: indexing
tags: [watch, e2e, subprocess-testing, os-replace, wal-checkpoint, docs-generation, click-cli]

requires:
  - phase: 12-01
    provides: FileWatcher/WatchConfig pipeline, update_paths, shared predicate, D-11 guard, e2e tracer + subprocess helper pattern
  - phase: 12-02
    provides: full CLI surface (final flags/settings), D-14 shutdown with WAL truncate, D-12 watcher recovery, restat cadence
provides:
  - Real-FS e2e acceptance battery sealing every Phase 12 roadmap SC (edit/delete/atomic-save/temp-noise/recovery/exit-codes/WAL)
  - Regenerated docs: `sif watch` in docs/cli-reference.md + the four watch_* settings in docs/configuration.md (generator-only)
  - Config generator: Watch Settings section registered + default_factory defaults rendered correctly
  - Full quality gate green with NOTHING deselected (docs-gate WINDOWS entry #9 closed)
affects: [13-daemon-mcp, 14-precommand, verification]

actuals:
  tokens: 6436    # chars/4 over the realized 7e46aee..64efc8c diff (25745 chars, src+tests+docs+scripts)
  tasks: 2
  commits: 2      # MEASURED: git rev-list --count 7e46aee..64efc8c

plan_head_before: 7e46aeebba294905657669dd0a84075e3806eb9d
plan_head_after: 64efc8ca0093d543d2804f89bf05ae748879c51d

tech-stack:
  added: []   # zero-new-deps lock held
  patterns:
    - "E2E observability for WAL truncation: the test parent holds an open read connection so the child's close is never the last one — SQLite otherwise DELETES a fully checkpointed -wal, hiding the truncate; with a live second reader only PRAGMA wal_checkpoint(TRUNCATE) explains a 0-byte file"
    - "One capture file merges the child's stdout AND stderr (banner lines are console/stdout; D-12 recovery warnings are logger/stderr records) — both assertable from one artifact"
    - "Noise-absence proofs pair a positive outcome (a control file from the same window IS indexed) with a bounded settle before asserting absence — never a naked negative poll"

key-files:
  created: []
  modified:
    - tests/integration/test_watch_e2e.py
    - docs/cli-reference.md
    - docs/configuration.md
    - scripts/generate_config_ref.py

key-decisions:
  - "E2E WAL assertion holds a parent read connection per signal case and first proves the WAL is NON-empty after a live child write — only then does a post-exit 0-byte file demonstrate the D-14 truncate (SQLite deletes a checkpointed -wal on last-connection close, which would make the plan's literal assertion unobservable)"
  - "Configuration.md ships env-var spellings exclusively (SIF_WATCH_*); the plan's lowercase-field verify grep can never match generator output — verified via the SIF_WATCH_DEBOUNCE_INTERVAL spelling (and case-insensitive grep), count 1"
  - "The watch_* settings reached configuration.md by registering a Watch Settings section in the generator's SECTIONS allowlist — the doc itself is regenerated wholesale, never hand-edited (prohibition honored)"
  - "default_factory settings defaults render by their product ([]) after fixing the generator's PydanticUndefined leak — watch_ignore_patterns is the first such field the doc has carried"
  - "The temp-noise battery adds .#hidden.md to the plan's three noise names: the **/*.md glob alone WOULD index it, so only the shared ignore predicate excludes it — the strongest LIVE-04 shape (the plan's three names are all glob-excluded anyway)"

patterns-established:
  - "Phase-acceptance e2e = real CLI subprocess, own tmp collection per test, outcome polls through fresh sqlite connections, serialized mutations, bounded fixed settle windows only after an observed outcome"

requirements-completed: [LIVE-01, LIVE-02, LIVE-03, LIVE-04, LIVE-11]

coverage:
  - id: D1
    description: "SC1/LIVE-01 e2e: add (tracer), content edit (new content+checksum), and delete (row gone) all land with no manual update; SIGINT exits 0"
    requirement: LIVE-01
    verification:
      - kind: e2e
        ref: "tests/integration/test_watch_e2e.py#test_watch_indexes_new_file_end_to_end"
        status: pass
      - kind: e2e
        ref: "tests/integration/test_watch_e2e.py#test_watch_edit_and_delete_reflected_end_to_end"
        status: pass
    human_judgment: false
  - id: D2
    description: "SC2/LIVE-03 e2e (LIVE-02 outcomes): a real os.replace atomic save over a live note leaves exactly ONE documents row for the final path carrying the new content — row never observed wiped, no duplicate (coalescing mechanics synthetic-proven in 12-01)"
    requirement: LIVE-03
    verification:
      - kind: e2e
        ref: "tests/integration/test_watch_e2e.py#test_watch_atomic_save_leaves_exactly_one_row"
        status: pass
    human_judgment: false
  - id: D3
    description: "SC3/LIVE-04 e2e: .swp/4913/.sb-*/.#lock.md written while watch runs never appear in documents while a control file from the same window does"
    requirement: LIVE-04
    verification:
      - kind: e2e
        ref: "tests/integration/test_watch_e2e.py#test_watch_temp_noise_never_indexed"
        status: pass
    human_judgment: false
  - id: D4
    description: "SC5/LIVE-11 e2e (D-12): root renamed away — every row intact, process alive, 'disappeared' warned exactly once across 2+ re-stat ticks; renamed back — rescheduled, a new file indexed"
    requirement: LIVE-11
    verification:
      - kind: e2e
        ref: "tests/integration/test_watch_e2e.py#test_watch_missing_root_recovery"
        status: pass
    human_judgment: false
  - id: D5
    description: "D-14 e2e: SIGINT and SIGTERM each exit 0 leaving a 0-byte -wal (parent-held reader keeps the file observable; pre-signal non-empty WAL proven first)"
    verification:
      - kind: e2e
        ref: "tests/integration/test_watch_e2e.py#test_watch_clean_exits_truncate_wal"
        status: pass
    human_judgment: false
  - id: D6
    description: "Docs regenerated by make docs-generate only: sif watch command + options in cli-reference.md; all four SIF_WATCH_* settings in configuration.md; the red docs-gate test is green (WINDOWS #9 closed)"
    verification:
      - kind: other
        ref: "grep -c 'sif watch' docs/cli-reference.md → 1; grep -c 'SIF_WATCH_(DEBOUNCE_INTERVAL|IGNORE_PATTERNS|UPDATE_DEPTH|RESTAT_INTERVAL)' docs/configuration.md → 4"
        status: pass
      - kind: unit
        ref: "tests/test_docs.py#TestDocsCodeBlocks::test_cli_reference_has_all_commands"
        status: pass
    human_judgment: false
  - id: D7
    description: "Full phase-sealing gate green with nothing deselected: 1050 passed @ 95.79% (fail_under=90), ruff check, ruff format --check, ty check src/sif all clean"
    verification:
      - kind: other
        ref: "env -u FORCE_COLOR NO_COLOR=1 python -m pytest → 1050 passed, 95.79%; ruff check src tests; ruff format --check src tests; ty check src/sif → all exit 0"
        status: pass
    human_judgment: false

duration: 21 min
completed: 2026-11-07
status: complete
---

# Phase 12 Plan 03: `sif watch` Foreground MVP — E2E Acceptance + Docs Seal Summary

**Real-FS e2e battery proving every Phase 12 SC against the real CLI subprocess (edit/delete, os.replace atomic save, temp-noise exclusion, missing-root recovery, SIGINT/SIGTERM exit 0 with a demonstrated 0-byte WAL), plus generator-only docs regeneration that turns the full quality gate green with nothing deselected**

## Performance

- **Duration:** 21 min (10:39–11:00 UTC)
- **Started:** 2026-11-07T10:39:25Z
- **Completed:** 2026-11-07T11:00:52Z
- **Tasks:** 2/2
- **Files modified:** 4
- **Suite:** 1050 passed @ 95.79% coverage, NOTHING deselected (fail_under=90 honored); ruff, format, ty all green; battery wall-time 18.6s for 6 subprocess tests

## Accomplishments

- E2e battery grew from the single LIVE-01 tracer to six tests, each on its own tmp collection with the real CLI subprocess: edit (new content + changed checksum), delete (row gone), `os.replace` atomic save (exactly one row for the final path, never observed wiped), temp-noise never indexed while a same-window control file is, missing-root recovery (rows intact + process alive + `disappeared` warned exactly once across 2+ re-stat ticks + reindex on return), and clean-exit signal proofs
- D-14 WAL truncate is now DEMONSTRATED at e2e level: each signal case first proves a non-empty `-wal` after a live child write, signals, then asserts a 0-byte `-wal` after exit 0 — observable because the parent holds a read connection (SQLite deletes a checkpointed `-wal` on last-connection close)
- `make docs-generate` output now carries the full `sif watch` surface: command tree entry, section, and the `-c/--collection`, `--embed`, `--no-embed`, `--verbose` options table in cli-reference.md; a new Watch Settings section with all four `SIF_WATCH_*` variables in configuration.md — both files regenerated wholesale, zero hand edits (prohibition honored, CI diff gate stays green)
- The full-suite docs gate `test_cli_reference_has_all_commands` flipped red→green: 1050 passed with no deselection — WINDOWS ledger entry #9 resolved (`fixed`)
- All polling is deadline-bounded outcome polling through fresh sqlite connections; zero watchdog event-type or sequence assertions anywhere in the battery (D-15/A1 — backend-agnostic across FSEvents and inotify)

## Task Commits

1. **Task 1: Real-FS e2e battery — edit/delete, atomic save, temp noise, recovery, exit codes (SC1-5)** - `7af8b81` (test)
2. **Task 2: Regenerate generator-owned docs + full quality gate** - `64efc8c` (docs)

**Plan metadata:** final docs commit (below)

## Files Created/Modified

- `tests/integration/test_watch_e2e.py` - extended 1→6 tests: shared subprocess spawner (output file with merged stderr, SIGINT safety net), `_poll_until` deadline helper, five new scenario proofs
- `docs/cli-reference.md` - regenerated: `sif watch` tree entry + command section + options table
- `docs/configuration.md` - regenerated: Watch Settings section (SIF_WATCH_DEBOUNCE_INTERVAL / _IGNORE_PATTERNS / _UPDATE_DEPTH / _RESTAT_INTERVAL)
- `scripts/generate_config_ref.py` - Watch Settings registered in the SECTIONS allowlist; default_factory defaults render by product (`[]`) instead of the PydanticUndefined sentinel

## Decisions Made

See key-decisions in frontmatter (WAL observability via held reader, env-var grep spelling, generator-allowlist registration, default_factory rendering, .#hidden.md noise addition).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Watch settings were absent from regenerated configuration.md**
- **Found during:** Task 2 (`make docs-generate` diff review)
- **Issue:** The generator emits sections from an explicit `SECTIONS` allowlist; the four `watch_*` fields were never registered, so the first regen produced a configuration.md with no watch content — the plan's must-have and verify command could not pass
- **Fix:** Added a Watch Settings section (all four fields) to `SECTIONS` in `scripts/generate_config_ref.py`, then re-ran `make docs-generate` — the doc itself was only ever generator-written
- **Files modified:** scripts/generate_config_ref.py, docs/configuration.md
- **Verification:** `grep -cE 'SIF_WATCH_(DEBOUNCE_INTERVAL|IGNORE_PATTERNS|UPDATE_DEPTH|RESTAT_INTERVAL)' docs/configuration.md` → 4
- **Committed in:** 64efc8c

**2. [Rule 1 - Bug] Generator leaked `PydanticUndefined` as a default value**
- **Found during:** Task 2 (diff review of the new Watch Settings table)
- **Issue:** `watch_ignore_patterns` uses `default_factory=list`; the generator read `field_info.default` only and rendered the sentinel repr `` `PydanticUndefined` `` into the Default column — factually wrong documentation
- **Fix:** When default is `PydanticUndefined`, render `default_factory()`'s product (here `[]`)
- **Files modified:** scripts/generate_config_ref.py
- **Verification:** regenerated table shows `` `[]` ``; ruff/format clean on the script
- **Committed in:** 64efc8c

**3. [Rule 3 - Blocking] Targeted e2e verify ran with --no-cov (established 12-01/12-02 practice)**
- **Found during:** Task 1 verify
- **Issue:** The plan's literal `python -m pytest tests/integration/test_watch_e2e.py -x` inherits the project-wide `--cov` addopts and `fail_under=90`, so a scoped run fails the coverage floor even with all tests passing
- **Fix:** Scoped runs use `--no-cov` (6/6 passed in 18.6s); the FULL suite with coverage ran green at plan level: 1050 passed @ 95.79%
- **Files modified:** none (execution detail)
- **Verification:** full-suite run above
- **Committed in:** n/a (process)

**4. [Rule 1 - Plan-spec reconciliation] Verify grep spelling cannot match generator output**
- **Found during:** Task 2 verify
- **Issue:** The plan's `grep -c "watch_debounce_interval" docs/configuration.md` uses the lowercase field name, but the generator has always emitted env-var spellings exclusively (`SIF_WATCH_DEBOUNCE_INTERVAL`) — the literal command returns 0 by construction
- **Fix:** Verified the intent (the setting IS documented) via the env-var spelling and case-insensitive grep, both count 1
- **Files modified:** none
- **Verification:** `grep -c 'SIF_WATCH_DEBOUNCE_INTERVAL' docs/configuration.md` → 1; all four settings → 4
- **Committed in:** n/a (verification detail)

**5. [Rule 1 - Determinism] WAL-0-bytes assertion made observable via a parent-held read connection**
- **Found during:** Task 1 (battery authoring)
- **Issue:** The plan's truth "after a clean exit the `<db>-wal` file is 0 bytes" is unobservable as written: SQLite DELETES a fully checkpointed `-wal` when the last connection closes, so the file is normally gone after the child exits — and with an all-unchanged reconcile the child might never write at all
- **Fix:** The test holds an open parent read connection (child close is never last, file survives) and first polls for a NON-empty WAL after a live child write, so the post-exit 0-byte assertion uniquely demonstrates `PRAGMA wal_checkpoint(TRUNCATE)`
- **Files modified:** tests/integration/test_watch_e2e.py
- **Verification:** test_watch_clean_exits_truncate_wal green for both SIGINT and SIGTERM
- **Committed in:** 7af8b81

**6. [Rule 1 - Plan-spec reconciliation] Recovery warnings asserted from a merged capture file**
- **Found during:** Task 1 (battery authoring)
- **Issue:** The plan says "assert the missing-root warning appears exactly once in captured stdout", but D-12 recovery warnings are `logger.warning` records that land on STDERR; a stdout-only capture can never see them
- **Fix:** The shared spawner merges stderr into the single output capture file, so banner lines and recovery warnings are assertable from one artifact
- **Files modified:** tests/integration/test_watch_e2e.py
- **Verification:** test_watch_missing_root_recovery asserts `output.count("disappeared") == 1`
- **Committed in:** 7af8b81

---

**Total deviations:** 6 auto-fixed (2 Rule 3 blockers, 4 Rule 1 bug/determinism/plan-spec reconciliations)
**Impact on plan:** All within task scope; no architectural change. Every must-have truth, artifact, key_link, and prohibition is honored (docs regenerated only, no event-sequence assertions, no unbounded sleeps, zero new dependencies).

## Issues Encountered

- None. The full suite is green with NOTHING deselected for the first time in the phase — the ledgered docs-gate failure (WINDOWS #9) is resolved as `fixed`.

## Authentication Gates

None — no external services in this plan.

## User Setup Required

None - no external service configuration required.

## Known Stubs

None — no placeholder bodies shipped.

## Threat Flags

None — no security-relevant surface beyond the plan's threat model. T-12-09 (hand-edited docs) mitigated by generator-only changes verified in the diff; T-12-10 (suite hang) mitigated by deadline-bounded polling throughout plus the spawner's SIGINT/kill safety net so even a missed outcome cannot leak a watcher process.

## Next Phase Readiness

- Phase 12 is complete: every roadmap SC1-5 has a real-FS e2e outcome proof, docs are current, all quality gates green (1050 passed @ 95.79%) — ready for `/gsd-verify-work 12`
- Phase 13 inherits the e2e battery as the acceptance harness for daemon/MCP hosts; the spawner's env-extra parameter is the seam for host-specific configuration

---
*Phase: 12-sif-watch-foreground-mvp*
*Completed: 2026-11-07*

## Self-Check: PASSED

All 4 key files exist on disk; both task commits (7af8b81, 64efc8c) are ancestors of HEAD; plan_head_before=7e46aee, plan_head_after=64efc8c, commits measured = 2 (matches frontmatter); full suite 1050 passed @ 95.79% with nothing deselected; WINDOWS entry #9 marked fixed.
