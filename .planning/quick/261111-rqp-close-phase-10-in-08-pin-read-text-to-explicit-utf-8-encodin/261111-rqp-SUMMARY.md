---
phase: quick-261111-rqp
plan: 01
subsystem: cli
tags: [get, encoding, utf-8, click, tdd, code-review-closure]

requires:
  - phase: 10-raise-pytest-coverage-to-90
    provides: "10-REVIEW.md IN-08 finding (disk-fallback read_text without explicit encoding, get.py:84 at review time, line 85 at execution time)"
provides:
  - "Explicit encoding='utf-8' on the get_cmd disk-fallback read (get.py:85) — locale-independent decoding of unindexed UTF-8 notes"
  - "Locale-independent Path.read_text contract regression test pinning the fallback-read encoding kwarg"
  - "Phase 10 IN-08 closed in 10-REVIEW-DISPOSITION.md (open 16 -> 15, total 22)"
affects: [phase-10-review-ledger, get-cli, future-encoding-findings]

actuals:
  tokens: 997
  tasks: 2
  commits: 3
plan_head_before: f68fd282bb3989f850f867f1e84905d002fc2b9d
plan_head_after: 7be1412f08da6e81c68257db4435b5dccfcc5ebe

tech-stack:
  added: []
  patterns:
    - "Delegating Path.read_text spy: record kwargs only for the target file path, forward every call to the captured real read_text — locale-independent read_text-contract pinning immune to UTF-8 mode (WR-06 open-kwarg exemplar adapted to Path.read_text)"

key-files:
  created: []
  modified:
    - src/sif/cli/commands/get.py
    - tests/unit/cli/test_get.py
    - .planning/milestones/v1.0-phases/10-raise-pytest-coverage-to-90/10-REVIEW-DISPOSITION.md

key-decisions:
  - "Followed the plan's locked RED design (delegating read_text kwarg-contract spy) — a functional non-ASCII test would be vacuous on this UTF-8-locale host; locale simulation is bypassed by UTF-8 mode"
  - "Ledger open-count decrement computed from execution-time git show HEAD:ledger (16 -> 15; no sibling items had landed), never a hardcoded planning-time literal — shared-ledger rule"
  - "Scope held to the finding's sole named site (get.py:85); WR-09 (rqq), WR-01 (rqs), caplog leak (rqr) and all other findings untouched"

requirements-completed: [PHASE10-IN-08]

coverage:
  - id: D1
    description: "get_cmd disk-fallback read pinned to explicit UTF-8 encoding, guarded by a locale-independent read_text-contract regression test"
    requirement: "PHASE10-IN-08"
    verification:
      - kind: unit
        ref: "tests/unit/cli/test_get.py#TestGetRetrieval::test_disk_fallback_read_text_pins_utf8_encoding"
        status: pass
      - kind: unit
        ref: "python -m pytest tests/unit/cli/test_get.py -q --no-cov (32 passed)"
        status: pass
    human_judgment: false
  - id: D2
    description: "Phase 10 IN-08 closed in the disposition ledger (YAML fixed, open 16 -> 15 from execution-time HEAD, Source cell names quick 261111-rqp) with every other record byte-identical"
    requirement: "PHASE10-IN-08"
    verification:
      - kind: other
        ref: "python -I byte-equality gate: ledger == git show HEAD:ledger + exactly three scoped replacements (count computed dynamically); WR-07/08, IN-09/10, CR-01/02 open rows preserved"
        status: pass
    human_judgment: false

duration: 8min
completed: 2026-11-11
status: complete
---

# Quick 261111-rqp Plan 01: Close Phase 10 IN-08 (disk-fallback read_text UTF-8 encoding) Summary

**One-line `encoding="utf-8"` pin on the get_cmd disk-fallback read plus a locale-independent Path.read_text contract regression test, closing Phase 10 IN-08 (ledger open 16 -> 15) with the ClickException wrapper, CR-02 line-filter contract, and CR-01 escaping byte-identical**

## Performance

- **Duration:** 8 min
- **Started:** 2026-11-11T12:21:48Z
- **Completed:** 2026-11-11T12:29:20Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments

- `get_cmd` now reads unindexed files with `path.read_text(encoding="utf-8")` (get.py:85) — a UTF-8 note with non-ASCII characters decodes identically on every host locale instead of the locale default (cp1252 on Windows); threat T-rqp-01 mitigated.
- New contract test `test_disk_fallback_read_text_pins_utf8_encoding` pins the encoding kwarg via a delegating `Path.read_text` spy: red at baseline on any platform/locale/UTF-8 mode, green after the one-line fix; non-vacuity guarded (exactly one fallback read must be recorded).
- Phase 10 IN-08 marked fixed in both ledger representations (YAML + markdown row), aggregate open 16 -> 15 with total still 22; a byte-equality gate against the execution-time HEAD baseline proved every other record unchanged.
- Full quality suite green: ruff check, ruff format, and pytest with coverage (results below).

## Closed Finding

**Phase 10 IN-08** — "Disk-fallback `read_text()` without explicit encoding" (10-REVIEW.md:201-205). The finding names exactly one site: the unindexed-file fallback in `get_cmd`, recorded as get.py:84 at review time and at line 85 at execution time (line 84 is the `try:`). Grep confirmed it is the only read_text/read_bytes/open site in get.py and the only unencoded `read_text()` in src/sif/cli/. Sibling-owned findings (WR-09/rqq, WR-01/rqs, caplog leak/rqr) were NOT swept.

## TDD Evidence (RED -> GREEN)

**Planning-time prototype (HEAD 802c08c, unmodified get.py):** exit_code 0, exactly one fallback read recorded with kwargs `{}`, non-ASCII content rendered — the encoding assertion fails at baseline on any platform/locale/UTF-8 mode. A functional non-ASCII test would be vacuous on this UTF-8-locale host; locale simulation via `locale.getpreferredencoding` is bypassed by UTF-8 mode — the kwarg contract is the only deterministic RED.

**Executor RED (before any production edit, HEAD f68fd28):**
- Command: `python -m pytest tests/unit/cli/test_get.py -q --no-cov -l -k test_disk_fallback_read_text_pins_utf8_encoding --junitxml=<task-dir>/red-report.xml` -> exit 1.
- Target failed on the planned assertion: `assert recorded[0].get("encoding") == "utf-8"` -> `AssertionError: assert None == 'utf-8'` (tests/unit/cli/test_get.py:268).
- Showlocals proof that the earlier assertions passed at baseline: `result = <Result okay>` (exit_code 0), non-ASCII content assertion passed, and `recorded = [{}]` (exactly one fallback read, empty kwargs — non-vacuous).
- Baseline preservation: other 31 tests pass with the new test deselected (`31 passed, 1 deselected`).
- Machine validation: JUnit-XML record classified `RED_EVIDENCE_OK` (`gsd_run check tdd-red-evidence`, reason `target_test_failed`, tests=1/failures=1/errors=0, matched target). Evidence artifacts: `red-run.txt`, `red-report.xml`, `red-console.txt`, `red-evidence.json` in this task directory.
- Semantic assessment: target executed and failed on the planned encoding-kwarg assertion for the intended reason (no encoding keyword at get.py:85); no setup/import/collection faults. Valid RED; GREEN authorized.

**Executor GREEN (after the one-line fix):** spy-recorded kwargs now carry `encoding="utf-8"` (the passing assertion reads the recorded kwarg directly); full file `32 passed in 1.02s`; ruff check/format clean on both task files. REFACTOR: not needed (single-keyword change, nothing to clean up).

## Task Commits

1. **Task 1 RED: failing read_text-contract test** — `b5422ba` (test)
2. **Task 1 GREEN: one-line encoding fix** — `865682e` (feat)
3. **Task 2: IN-08 ledger closure** — `7be1412` (docs)

Plan metadata commit: handled by the orchestrator (quick-task docs/state commit is orchestrator-owned; SUMMARY/STATE not committed by the executor).

## Files Created/Modified

- `src/sif/cli/commands/get.py` — one line: `path.read_text()` -> `path.read_text(encoding="utf-8")` at line 85; the ClickException read-error wrapper (84-108), CR-02 line-filter comment/logic, CR-01 escape/raw-print comments and calls, and every other line byte-identical. Exactly one `encoding="utf-8"` site in the file.
- `tests/unit/cli/test_get.py` — additive only: one new test immediately after `test_disk_fallback_honors_line_options` in `TestGetRetrieval`; NO import changes (os, Path, patch already present); all 31 existing tests, helpers, and fixtures unmodified.
- `.planning/milestones/v1.0-phases/10-raise-pytest-coverage-to-90/10-REVIEW-DISPOSITION.md` — exactly three scoped edits: IN-08 YAML `disposition: open -> fixed`, aggregate `open: 16 -> 15` (decremented from the execution-time HEAD value; total 22 and recorded timestamp unchanged), IN-08 row Source cell naming quick 261111-rqp. No `**Status:**` lines introduced.

## Quality Suite (full, per CLAUDE.md)

- `python -m pytest tests/unit/cli/test_get.py -q --no-cov` — **32 passed**
- `ruff check src tests` — **All checks passed**
- `ruff format --check src tests` — **188 files already formatted**
- `python -m pytest` (full, with coverage gate; PATH miniconda pytest) — **1521 passed, 1 skipped in 73.16s; coverage 95.02% (fail_under=90 reached)**
- Scope-guard `git diff --exit-code` over main.py, repositories.py, collection.py, index.py, test_watch_cmd.py, docs/cli-reference.md, docs/configuration.md — **clean (untouched)**
- Scoped diff review: `git diff --stat f68fd28..HEAD` shows exactly the three task files (34 insertions, 4 deletions); commits staged only task-scoped paths.

## Decisions Made

- Followed the plan's locked RED design (delegating kwarg-contract spy) — no executor-side redesign.
- Shared-ledger rule honored: the open-count edit read the CURRENT count from execution-time `git show HEAD:<ledger>` (16 at execution time — siblings rqq/rqs had only plan commits landed, no ledger closures) and decremented dynamically; the Task 2 gate reconstructed the expected file from execution-time HEAD and asserted byte-equality before the ledger commit.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None. (The sibling r2f evidence-record formatting pitfall — console text concatenated into the XML `output` field — was pre-empted: pure JUnit XML in `output`, console transcript in `consoleOutput`; classifier returned `RED_EVIDENCE_OK` on first validation.)

## Scope Preservation

- All other open findings (WR-01/07/08/09, IN-01..IN-07, IN-09/10, CR-01/02) remain open and byte-identical in the ledger; WR-01/WR-09 state not asserted (sibling-owned).
- Pre-existing uncommitted `.planning/` churn (STATE.md, config.json, state.json, agent-history.json, PATTERNS files, 16-REVIEW iter2 files, research cache, quick-batches/, tmp/) was never staged, committed, or reverted. Untracked entry count 24 = 20 pre-existing + 4 RED evidence artifacts in this task directory (orchestrator-owned, left uncommitted). Coverage artifacts (htmlcov/, coverage.xml, .coverage) are gitignored.
- Generator-owned docs (docs/cli-reference.md, docs/configuration.md) untouched; STATE.md/ROADMAP.md not written (orchestrator-owned).

## Known Stubs

None — no stubs, placeholders, skipped tests, or unrun verification in the changed files.

## Threat Flags

None — no new network, auth, file-access, or schema surface beyond the planned T-rqp-01 mitigation (explicit UTF-8 decoding of the user-supplied unindexed file), which is implemented and test-pinned.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Phase 10 review ledger now 15/22 open. Sibling batch items rqq (WR-09) and rqs (WR-01) own their own ledger closures; the shared-ledger dynamic-decrement convention keeps them composable.
- No blockers.

---
*Phase: quick-261111-rqp*
*Completed: 2026-11-11*

## Self-Check: PASSED

- FOUND: src/sif/cli/commands/get.py (exactly one `encoding="utf-8"` site)
- FOUND: tests/unit/cli/test_get.py (contract test present)
- FOUND: .planning/milestones/v1.0-phases/10-raise-pytest-coverage-to-90/10-REVIEW-DISPOSITION.md
- FOUND: red-evidence.json (RED_EVIDENCE_OK)
- FOUND: commits b5422ba, 865682e, 7be1412 (all ancestors of HEAD)