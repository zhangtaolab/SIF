---
phase: quick-261111-r2f
plan: 01
subsystem: cli
tags: [bench, encoding, utf-8, click, tdd, code-review-closure]

requires:
  - phase: 16-bench-expansion-reranker-tuning
    provides: "T-16-02 ClickException wrapping of bench fixture load and evaluation (the primary WR-06 defect, already shipped)"
provides:
  - "Explicit encoding='utf-8' on the bench fixture open (bench.py:624) — locale-independent fixture decoding"
  - "Locale-independent builtins.open contract regression test pinning the fixture-open encoding kwarg"
  - "Phase 10 WR-06 closed in 10-REVIEW-DISPOSITION.md (open 17 -> 16, total 22)"
affects: [phase-10-review-ledger, bench, future-encoding-findings]

actuals:
  tokens: 1352
  tasks: 2
  commits: 3
plan_head_before: 42c931f020b14631b06ce1ecd8d252a3b4162a35
plan_head_after: 15343bbf9ae872143a94dd9821c8ac2e8f62b111

tech-stack:
  added: []
  patterns:
    - "Delegating builtins.open spy: record kwargs only for the target path, forward every call to the captured real open — locale-independent open-contract pinning immune to UTF-8 mode"

key-files:
  created: []
  modified:
    - src/sif/cli/commands/bench.py
    - tests/unit/cli/test_bench.py
    - .planning/milestones/v1.0-phases/10-raise-pytest-coverage-to-90/10-REVIEW-DISPOSITION.md

key-decisions:
  - "WR-06 selected as the smallest safe live Phase 10 item: one production line, one contract test; primary raw-traceback defect already wrapped by Phase 16 T-16-02"
  - "Kwarg-contract spy instead of a functional non-ASCII fixture test (vacuous on UTF-8 locales) or locale simulation (bypassed by UTF-8 mode)"
  - "IN-08 (read_text encoding, different file) deliberately NOT swept — separate open finding, stays open"

requirements-completed: [PHASE10-WR-06]

coverage:
  - id: D1
    description: "Bench fixture open pinned to explicit UTF-8 encoding, guarded by a locale-independent open-contract regression test"
    requirement: "PHASE10-WR-06"
    verification:
      - kind: unit
        ref: "tests/unit/cli/test_bench.py#TestBenchCommand::test_bench_fixture_open_pins_utf8_encoding"
        status: pass
      - kind: unit
        ref: "python -m pytest tests/unit/cli/test_bench.py -q --no-cov (35 passed)"
        status: pass
    human_judgment: false
  - id: D2
    description: "Phase 10 WR-06 closed in the disposition ledger (YAML fixed, open 17 -> 16, Source cell names this task and the T-16-02 precedent) with every other record byte-identical"
    requirement: "PHASE10-WR-06"
    verification:
      - kind: other
        ref: "python -I byte-equality gate: ledger == git show HEAD:ledger + exactly three scoped replacements; WR-01/07/08/09 open and WR-02/03/04/05/10 fixed rows preserved"
        status: pass
    human_judgment: false

duration: 9min
completed: 2026-11-11
status: complete
---

# Quick 261111-r2f Plan 01: Close Phase 10 WR-06 (bench fixture UTF-8 encoding) Summary

**One-line `encoding="utf-8"` pin on the bench fixture open plus a locale-independent builtins.open contract regression test, closing Phase 10 WR-06 (ledger open 17 -> 16) with the T-16-02 error wrappers untouched**

## Performance

- **Duration:** 9 min
- **Started:** 2026-11-11T11:41:14Z
- **Completed:** 2026-11-11T11:50:21Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments

- `bench_cmd` now opens the user-supplied fixture with `open(fixture, encoding="utf-8")` (bench.py:624) — UTF-8 fixtures decode identically on every host locale instead of the locale default (threat T-r2f-01 mitigated).
- New contract test `test_bench_fixture_open_pins_utf8_encoding` pins the encoding kwarg via a delegating `builtins.open` spy: red at baseline on any platform/locale, green after the one-line fix; non-vacuity guarded (exactly one fixture open must be recorded).
- Phase 10 WR-06 marked fixed in both ledger representations (YAML + markdown row), aggregate open 17 -> 16 with total still 22; a byte-equality gate against the HEAD baseline proved every other record unchanged.
- Full quality suite green: ruff check, ruff format, and pytest with coverage (results below).

## Selected Finding and Per-Candidate Assessment

Selected: **Phase 10 WR-06** — encoding sub-item only. The finding's primary defect (fixture load/validation and evaluator errors escaping as raw tracebacks) was already shipped by Phase 16 T-16-02: bench.py:623-627 wraps the fixture `json.load` in `(OSError, ValueError)` -> ClickException, and bench.py:661-681 wraps evaluation with a ClickException re-raise passthrough. The sole live sub-item was the missing `encoding="utf-8"` on the file's only `open()` site (line 624).

Live re-assessment of all candidates at HEAD 42c931f (per plan):
- **WR-06 SELECTED** — one production line in one file, one contract test, no interface/protocol/documentation change.
- **WR-01** (collection remove orphans vec0 embeddings) — multi-file: needs index.py purger helper or shared module plus repositories.py purge and sqlite-vec availability handling.
- **WR-07** (MCP get ignores max_lines without from_line) — handling max_lines alone changes MCP line_start/line_end metadata: a protocol-contract decision, broader than a one-line fix.
- **WR-08** (hybrid_search cannot degrade to BM25) — contradicts the documented fail-fast vector posture (CLAUDE.md); needs a user decision.
- **WR-09** (cleanup naive-local vs aware-UTC timestamps) — spans read side (main.py) and write side (repositories.py): multi-file.
- **WR-02/03/04/05/10** — already closed by prior quick tasks; their ledger records untouched.
- **IN-08** (disk-fallback read_text without encoding) — separate open finding in a different file; explicitly NOT swept, stays open.

## TDD Evidence (RED -> GREEN)

**Planning-time prototype (HEAD 42c931f, unmodified bench.py):** exit_code 0, exactly one fixture open recorded with kwargs `{}` — the encoding assertion fails at baseline on any platform/locale/UTF-8 mode. A functional non-ASCII test would be vacuous on this UTF-8-locale host; locale simulation via `locale.getpreferredencoding` is bypassed by UTF-8 mode — the kwarg contract is the only deterministic RED.

**Executor RED (before any production edit):**
- Command: `python -m pytest tests/unit/cli/test_bench.py -q --no-cov -l -k test_bench_fixture_open_pins_utf8_encoding` -> exit 1.
- Target failed on the planned assertion: `assert fixture_opens[0].get("encoding") == "utf-8"` -> `AssertionError: assert None == 'utf-8'` (tests/unit/cli/test_bench.py:586).
- Showlocals proof that the earlier assertions passed at baseline: `result = <Result okay>` (exit_code 0) and `fixture_opens = [{}]` (exactly one fixture open, empty kwargs — non-vacuous).
- Baseline preservation: other 34 tests pass with the new test deselected (`34 passed, 1 deselected`).
- Machine validation: JUnit-XML record classified `RED_EVIDENCE_OK` (`gsd_run check tdd-red-evidence`, reason `target_test_failed`, tests=1/failures=1/errors=0, matched target). Evidence artifacts: `red-run.txt`, `red-report.xml`, `red-console.txt`, `red-evidence.json` in this task directory.
- Semantic assessment: target executed and failed on the planned encoding-kwarg assertion for the intended reason (no encoding keyword at bench.py:624); no setup/import/collection faults. Valid RED; GREEN authorized.

**Executor GREEN (after the one-line fix):** spy-recorded kwargs now carry `encoding="utf-8"` (the passing assertion reads the recorded kwarg directly); full file `35 passed in 1.79s`; ruff check/format clean on both task files. REFACTOR: not needed (single-keyword change, nothing to clean up).

## Task Commits

1. **Task 1 RED: failing open-contract test** — `1751589` (test)
2. **Task 1 GREEN: one-line encoding fix** — `fa6fc09` (feat)
3. **Task 2: WR-06 ledger closure** — `15343bb` (docs)

Plan metadata commit: handled by the orchestrator (quick-task docs/state commit is orchestrator-owned; SUMMARY/STATE not committed by the executor).

## Files Created/Modified

- `src/sif/cli/commands/bench.py` — one line: `open(fixture)` -> `open(fixture, encoding="utf-8")` at line 624; T-16-02 comment, both ClickException wrappers, and every other line byte-identical.
- `tests/unit/cli/test_bench.py` — additive only: `import builtins` / `import os` in the stdlib group (builtins, json, os) and one new test after `test_bench_malformed_fixture_exits_nonzero`; all 34 existing tests, helpers, and fixtures unmodified.
- `.planning/milestones/v1.0-phases/10-raise-pytest-coverage-to-90/10-REVIEW-DISPOSITION.md` — exactly three scoped edits: WR-06 YAML `disposition: open -> fixed`, aggregate `open: 17 -> 16` (total 22 and recorded timestamp unchanged), WR-06 row Source cell naming quick 261111-r2f and the Phase 16 T-16-02 precedent.

## Quality Suite (full, per CLAUDE.md)

- `python -m pytest tests/unit/cli/test_bench.py -q --no-cov` — **35 passed**
- `ruff check src tests` — **All checks passed**
- `ruff format --check src tests` — **188 files already formatted**
- `python -m pytest` (full, with coverage gate; PATH miniconda pytest) — **1520 passed, 1 skipped in 76.59s; coverage 95.02% (fail_under=90 reached)**
- Scope-guard `git diff --exit-code` over collection.py, ls.py, index.py, incremental.py, backend.py, main.py, repositories.py, schema.py, docs/cli-reference.md, docs/configuration.md — **clean (untouched)**
- Scoped diff review: `git diff --stat 42c931f..HEAD` shows exactly the three task files (62 insertions, 4 deletions); commits staged only task-scoped paths.

## Decisions Made

- Followed the plan's locked RED design (delegating kwarg-contract spy) — no executor-side redesign.
- Ledger closure uses this file's three-edit convention (no `**Status:**` lines — that format belongs to other ledger types); byte-equality gate run before the ledger commit, as planned.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

- The TDD evidence classifier first returned `INVALID_RED (invalid_record)` because the record's `output` field concatenated console text after the XML document ("Malformed XML"). Fixed by placing the pure JUnit XML document in `output` and the console transcript in a separate `consoleOutput` field; revalidation returned `RED_EVIDENCE_OK`. Evidence-record formatting only — no code or scope impact.

## Scope Preservation

- IN-08 and all other open findings (WR-01/07/08/09, IN-01..IN-10, CR-01/02) remain open and byte-identical in the ledger.
- Pre-existing uncommitted `.planning/` churn (config.json, state.json, agent-history.json, PATTERNS files, 16-REVIEW iter2 files, research cache, tmp/) was never staged, committed, or reverted; working-tree untracked entry count unchanged (20). Coverage artifacts (htmlcov/, coverage.xml, .coverage) are gitignored.
- Generator-owned docs (docs/cli-reference.md, docs/configuration.md) untouched.

## Known Stubs

None — no stubs, placeholders, skipped tests, or unrun verification in the changed files.

## Threat Flags

None — no new network, auth, file-access, or schema surface beyond the planned T-r2f-01 mitigation (explicit UTF-8 decoding of the user fixture), which is implemented and test-pinned.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Phase 10 review ledger now 16/22 open. Remaining WR candidates: WR-01/09 (multi-file), WR-07 (protocol decision), WR-08 (convention-conflicting, needs user decision); IN-08 is the next smallest encoding-style item if a one-file sweep is wanted.
- No blockers.

---
*Phase: quick-261111-r2f*
*Completed: 2026-11-11*

## Self-Check: PASSED

- FOUND: src/sif/cli/commands/bench.py (exactly one `encoding="utf-8"` site)
- FOUND: tests/unit/cli/test_bench.py (contract test present)
- FOUND: .planning/milestones/v1.0-phases/10-raise-pytest-coverage-to-90/10-REVIEW-DISPOSITION.md
- FOUND: 261111-r2f-SUMMARY.md
- FOUND: commits 1751589, fa6fc09, 15343bb (all ancestors of HEAD)
