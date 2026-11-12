---
phase: quick-261111-rqr
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - tests/unit/cli/test_watch_cmd.py
  - .planning/quick/261111-o6y-find-and-fix-failing-tests-run-the-quali/deferred-items.md
autonomous: true
must_haves:
  truths:
    - "The D-1 victim test (TestShutdownRoutine::test_shutdown_skips_checkpoint_when_worker_still_busy) passes in the 11-file batch under .venv/bin/python (pytest 9.0.3) with FORCE_COLOR=1 --no-cov, even when preceded by tests that invoke the real cli group"
    - "The minimal leaking pair (test_main.py::TestStatusRealDatabase::test_missing_index_returns_guidance then the victim) is green under BOTH the .venv interpreter and the PATH miniconda interpreter"
    - "No production behavior changes: src/ is byte-identical to the pre-task HEAD (test-side-only scope per the D-1 record)"
    - "Full quality suite green under the PATH miniconda interpreter: ruff check src tests, ruff format --check src tests, python -m pytest (coverage fail_under=90 active)"
    - "The D-1 entry in the o6y deferred-items.md parses as status=resolved through the audit parser (uat.cjs parseDeferredItemsWithStatus), so the milestone pre-close audit stops counting it as open"
  artifacts:
    - tests/unit/cli/test_watch_cmd.py
    - .planning/quick/261111-o6y-find-and-fix-failing-tests-run-the-quali/deferred-items.md
  key_links:
    - "module autouse fixture -> sif logger chain normalized (level NOTSET, propagate True, no leaked handlers, manager.disable NOTSET) -> caplog's root-logger handler receives the shutdown WARNING record"
    - "fixture teardown -> snapshot restore -> zero persistent global logging-state change for tests outside this module"
    - "D-1 sibling bullet '- **Status:** resolved' -> uat.cjs parseDeferredItemsWithStatus -> audit three-way split counts D-1 as resolved"
---

<objective>
Fix deferred D-1 only: the caplog cross-test leak that makes `tests/unit/cli/test_watch_cmd.py::TestShutdownRoutine::test_shutdown_skips_checkpoint_when_worker_still_busy` fail in the compressed 11-file batch under `.venv/bin/python` (pytest 9.0.3, FORCE_COLOR=1, --no-cov). Full record: `.planning/quick/261111-o6y-find-and-fix-failing-tests-run-the-quali/deferred-items.md` (D-1).

Root cause (bisected and probed LIVE at planning time, HEAD 08e0c8e — re-verify, do not assume):
- The `cli` group callback (`src/sif/cli/main.py:71`) calls `setup_logging(log_level)`, which leaves the `sif` logger with `propagate=False`, a stderr StreamHandler, and level INFO (`src/sif/utils/logging.py`, setup_logging). Probe confirmed: after `setup_logging('INFO')`, `logging.getLogger('sif').propagate == False`.
- caplog's capture handler sits on the ROOT logger. With `propagate=False` on `sif`, the WARNING record emitted by `shutdown_watcher` (`src/sif/cli/commands/watch.py:115-116`) stops at the `sif` logger and never reaches caplog -> `caplog.records` is empty -> the assertion at `tests/unit/cli/test_watch_cmd.py:609` fails.
- THREE predecessor files leak individually (each run as `predecessor + victim file` under .venv): `tests/unit/cli/test_collection.py`, `tests/unit/cli/test_get.py`, `tests/unit/cli/test_main.py` — all invoke the real `cli` group. Because multiple predecessors leak, the fix MUST be victim-side (a reset fixture in test_watch_cmd.py), not a fix to one predecessor.
- pytest 9.1.1 (PATH miniconda) tolerates the same leak: the minimal pair passes there. The fix must stay green under both interpreters.

Planning-time RED evidence (all commands run from the checkout root):
- Minimal pair: `FORCE_COLOR=1 .venv/bin/python -m pytest "tests/unit/cli/test_main.py::TestStatusRealDatabase::test_missing_index_returns_guidance" "tests/unit/cli/test_watch_cmd.py::TestShutdownRoutine::test_shutdown_skips_checkpoint_when_worker_still_busy" --no-cov -q` -> `1 failed, 1 passed in 0.06s` (the victim fails on the caplog assertion).
- Same pair under PATH `python -m pytest` -> `2 passed`.
- Victim alone under .venv -> `1 passed`.
- Full 11-file batch under .venv (file list in Task 1) -> `1 failed, 349 passed in 3.98s`; the single failure is exactly the D-1 victim.

Purpose: make the watch CLI test module hermetic against leaked logging state so the batch is green under .venv, without touching production logging behavior.
Output: one autouse logging-isolation fixture in test_watch_cmd.py; D-1 marked resolved in the o6y deferred ledger; two scoped commits.
</objective>

<execution_context>
@~/.claude/gsd-core/workflows/execute-plan.md
@~/.claude/gsd-core/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md
@.planning/quick/261111-o6y-find-and-fix-failing-tests-run-the-quali/deferred-items.md
@tests/unit/cli/test_watch_cmd.py
@src/sif/utils/logging.py
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Victim-side logging-isolation fixture in test_watch_cmd.py (RED -> GREEN under .venv)</name>
  <files>tests/unit/cli/test_watch_cmd.py</files>
  <precondition>.venv/bin/python -m pytest --version reports 9.0.3 and PATH python -m pytest --version reports 9.1.1 (both observed at planning time); .venv lacks torch but every file in this batch is pure CLI/MagicMock/caplog and collects fine under .venv. If either interpreter differs, re-confirm the regimes before trusting RED/GREEN.</precondition>
  <behavior>
    - RED (before the fixture): the minimal pair and the 11-file batch under .venv fail on exactly the D-1 victim's caplog assertion (planning-time baseline: 1 failed, 1 passed for the pair; 1 failed, 349 passed for the batch — counts may drift if sibling batch items land first; the failing test ID must match exactly)
    - GREEN (after the fixture): the victim captures the shutdown WARNING via caplog even when a predecessor invoked the real cli group; minimal pair, each of the three leaking predecessor-file pairs, and the full 11-file batch all pass under .venv with FORCE_COLOR=1 --no-cov
    - The fixture restores the exact prior logging state after every test in the module (no persistent global change; tests outside this module see the same logging state they would have without the fixture)
    - All existing tests in test_watch_cmd.py pass unmodified, both in isolation and in the full suite under the PATH interpreter
  </behavior>
  <action>
  First re-prove RED live (do not trust the planning-time output blindly — sibling items may have landed): run the minimal pair and the full 11-file batch under .venv exactly as written in the verify block, and confirm the single failure is the D-1 victim. If RED no longer reproduces, STOP and report — do not invent a fix for a green baseline.

  Then add ONE module-level autouse fixture to tests/unit/cli/test_watch_cmd.py (suggested name `_hermetic_sif_logging`), placed after the existing module helpers and before TestHelpSurface. This is the D-1 fix: victim-side isolation, because three different predecessor files leak (collection, get, main — all invoke the real cli group whose callback runs setup_logging).

  Fixture contract:
  - For each logger name in the chain "sif", "sif.cli", "sif.cli.commands", "sif.cli.commands.watch" (get them via logging.getLogger): snapshot level, propagate, disabled, and a shallow copy of the handlers list; then normalize to level=logging.NOTSET, propagate=True, disabled=False, handlers=[] (assign a fresh empty list). This undoes exactly what setup_logging and _apply_quiet_mode leak: the propagate=False wall, the stderr StreamHandler, and any raised level.
  - Also snapshot logging.Logger.manager.disable and set it to logging.NOTSET (set_quiet can raise it via logging.disable).
  - Do NOT touch the root logger — pytest's caplog/logging plugin owns it.
  - Yield, then restore every snapshot exactly (levels, propagate, disabled, the original handler object lists, manager.disable) so the module leaves global logging state as it found it.
  - Fully typed per CLAUDE.md: return type Generator[None, None, None] imported from collections.abc; logging is already imported in the module. Docstring names D-1 and the mechanism (setup_logging leaves propagate=False on the sif logger, which walls caplog's root-logger handler off from sif.cli.commands.watch records) and states this is test-side isolation, not a production logging change.
  - Keep it under ruff's 100-char lines and complexity 10; a small loop over the chain plus one restore loop is sufficient.

  Scope guards: do NOT modify any file under src/ (production logging behavior stays exactly as shipped — the D-1 record's test-side-only boundary). Do NOT edit the leaking predecessor files or tests/conftest.py — the reset belongs to the affected module per the orchestrator's minimal-scope directive. Do NOT change the victim test's own assertions; the existing test IS the regression contract. Do NOT hand-edit docs/cli-reference.md or docs/configuration.md (generator-owned).

  Prove GREEN: minimal pair under .venv; each leaking predecessor file paired with the victim file under .venv (test_collection.py, test_get.py, test_main.py); the full 11-file batch under .venv with FORCE_COLOR=1 --no-cov; the same batch under PATH python (must stay green); and test_watch_cmd.py alone under .venv. Then confirm src/ is untouched and commit ONLY tests/unit/cli/test_watch_cmd.py with message `fix(quick-261111-rqr): isolate watch CLI tests from leaked sif logger state (D-1)`. Never stage the pre-existing uncommitted .planning/ churn (config.json, state.json, agent-history.json, tmp/, PATTERNS files, research cache, 16-REVIEW iter2 files).
  </action>
  <verify>
    <automated>FORCE_COLOR=1 .venv/bin/python -m pytest tests/integration/test_embed_idempotency.py tests/integration/test_incremental_equivalence.py tests/unit/cli/test_bench.py tests/unit/cli/test_collection.py tests/unit/cli/test_context.py tests/unit/cli/test_get.py tests/unit/cli/test_index.py tests/unit/cli/test_index_locking.py tests/unit/cli/test_main.py tests/unit/cli/test_search.py tests/unit/cli/test_watch_cmd.py --no-cov -q</automated>
    <automated>FORCE_COLOR=1 .venv/bin/python -m pytest "tests/unit/cli/test_main.py::TestStatusRealDatabase::test_missing_index_returns_guidance" "tests/unit/cli/test_watch_cmd.py::TestShutdownRoutine::test_shutdown_skips_checkpoint_when_worker_still_busy" --no-cov -q</automated>
    <automated>FORCE_COLOR=1 python -m pytest tests/integration/test_embed_idempotency.py tests/integration/test_incremental_equivalence.py tests/unit/cli/test_bench.py tests/unit/cli/test_collection.py tests/unit/cli/test_context.py tests/unit/cli/test_get.py tests/unit/cli/test_index.py tests/unit/cli/test_index_locking.py tests/unit/cli/test_main.py tests/unit/cli/test_search.py tests/unit/cli/test_watch_cmd.py --no-cov -q</automated>
    <automated>test -z "$(git status --porcelain -- src)"</automated>
    RED gate (run BEFORE the fix, must fail with exactly the D-1 victim): the first automated command exits 1 and its short summary names tests/unit/cli/test_watch_cmd.py::TestShutdownRoutine::test_shutdown_skips_checkpoint_when_worker_still_busy as the only FAILED line. GREEN gates (after the fix): all three pytest commands exit 0 with zero FAILED lines (planning-time batch baseline: 350 tests total; accept count drift from sibling items, never accept a failure), and the src/ cleanliness gate passes (baseline at planning time: empty).
  </verify>
  <done>
  The 11-file batch and the minimal pair are green under .venv (pytest 9.0.3) with FORCE_COLOR=1 --no-cov; the batch stays green under the PATH interpreter; test_watch_cmd.py passes in isolation; git status --porcelain -- src is empty; exactly one commit lands touching only tests/unit/cli/test_watch_cmd.py.
  </done>
</task>

<task type="auto">
  <name>Task 2: Full quality suite gate + resolve D-1 in the o6y deferred ledger</name>
  <files>.planning/quick/261111-o6y-find-and-fix-failing-tests-run-the-quali/deferred-items.md</files>
  <action>
  Run the full quality suite per CLAUDE.md under the PATH miniconda interpreter (the baseline interpreter with torch; .venv cannot collect the full suite): `ruff check src tests`, `ruff format --check src tests`, then `python -m pytest` (coverage addopts and fail_under=90 are active via pyproject.toml). All three must pass. If ruff format flags the new fixture, run `ruff format tests/unit/cli/test_watch_cmd.py` and amend the Task 1 commit scope cleanly (format-only follow-up commit acceptable: `style(quick-261111-rqr): format logging-isolation fixture`).

  Then record D-1's resolution in .planning/quick/261111-o6y-find-and-fix-failing-tests-run-the-quali/deferred-items.md. This file IS an audit-parsed deferred ledger (uat.cjs parseDeferredItemsWithStatus; verified live at planning time). The D-1 entry is heading-delimited (`## D-1: ...` with sibling `- **Field:** ...` bullets), so append TWO sibling bullets at the end of the D-1 entry, matching the file's existing bullet convention:
  - `- **Status:** resolved`
  - `- Resolved 2026-11-11 by quick task 261111-rqr — victim-side autouse fixture in tests/unit/cli/test_watch_cmd.py snapshots/normalizes/restores the sif logger chain (setup_logging had leaked propagate=False + a stderr handler onto the sif logger, walling caplog's root handler off from the shutdown WARNING). Bisected live: test_collection.py, test_get.py, and test_main.py each leak via the real cli group callback; 11-file batch green under .venv pytest 9.0.3 (FORCE_COLOR=1, --no-cov) and under PATH pytest 9.1.1; full suite green on the baseline interpreter.`
  Keep every other line of the file byte-identical (the D-1 heading and its existing bullets stay unchanged — the resolution is additive). Note: the `  **Status:** resolved` two-space form cited in continuity notes belongs to bullet-form ledgers (e.g. the Phase 16 file closed by 261111-kn2); BOTH forms parse as resolved for this heading-form entry (probed live), but the dash sibling-bullet form is the one consistent with this file's existing fields — use it. Do NOT touch 10-REVIEW-DISPOSITION.md (D-1 is a deferred item, not a WR record — orchestrator directive).

  Verify the resolution parses: run the node probe in the verify block (it loads the real audit parser and asserts the D-1 entry's status is exactly resolved; planning-time probe confirmed the appended dash form yields status=resolved). Commit ONLY the deferred-items.md change with message `docs(quick-261111-rqr): resolve deferred D-1 caplog cross-test leak record`. Never stage the pre-existing uncommitted .planning/ churn.
  </action>
  <verify>
    <automated>ruff check src tests</automated>
    <automated>ruff format --check src tests</automated>
    <automated>python -m pytest</automated>
    <automated>node -e "const u=require(require('os').homedir()+'/.claude/gsd-core/bin/lib/uat.cjs');const fs=require('fs');const c=fs.readFileSync('.planning/quick/261111-o6y-find-and-fix-failing-tests-run-the-quali/deferred-items.md','utf8');const items=u.parseDeferredItemsWithStatus(c);const d1=items.find(i=>i.name.startsWith('D-1:'));if(!d1||d1.status!=='resolved'){console.error('D-1 not resolved:',JSON.stringify(items.map(i=>({n:i.name.slice(0,20),s:i.status}))));process.exit(1)}console.log('D-1 status:',d1.status)"</automated>
    All four commands exit 0. The pytest gate is the full suite with coverage (fail_under=90); planning-time baseline suite was green at 1514 passed / 95.02% cov on the baseline interpreter — accept count drift from sibling items, never accept a failure or a coverage drop below 90. The node probe must print `D-1 status: resolved`.
  </verify>
  <done>
  ruff check, ruff format --check, and the full pytest suite (coverage >= 90) are green under the PATH interpreter; the D-1 entry carries the resolved status bullet and the audit parser reports status=resolved; every other line of deferred-items.md is byte-identical to HEAD; the resolution commit touches only that one file.
  </done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| (none new) | Test-side-only change: a pytest fixture and a planning-ledger note. No production code, no new input surfaces, no network, no installs. |

## STRIDE Threat Register

| Threat ID | Category | Component | Severity | Disposition | Mitigation Plan |
|-----------|----------|-----------|----------|-------------|-----------------|
| T-rqr-01 | Tampering | tests/unit/cli/test_watch_cmd.py fixture | low | accept | Test-only isolation fixture; snapshots and restores all mutated logging state, cannot alter production logging behavior (src/ untouched, gated by `git status --porcelain -- src`). No trust boundary crossed. |
| T-rqr-SC | Tampering | npm/pip/cargo installs | high | mitigate | No package installs in this plan — both interpreters and all dependencies already exist (observed live). Package-legitimacy gate trivially satisfied; no new dependency may be added under this plan's scope. |
</threat_model>

<verification>
- D-1 regression contract: the 11-file batch under .venv (FORCE_COLOR=1, --no-cov) exits 0 with the victim test passing — proven RED at planning time (1 failed, 349 passed) and required GREEN after Task 1.
- Dual-interpreter parity: minimal pair and batch green under both .venv pytest 9.0.3 and PATH pytest 9.1.1.
- Production untouched: `git status --porcelain -- src` empty after Task 1.
- Full quality suite per CLAUDE.md green under the PATH interpreter (ruff check, ruff format --check, pytest with coverage >= 90).
- Audit closure: the real parser (uat.cjs parseDeferredItemsWithStatus) reports the D-1 entry as resolved.
- Commit hygiene: exactly two scoped commits (test file; deferred ledger); pre-existing .planning/ churn never staged.
</verification>

<success_criteria>
- The D-1 victim test no longer fails in the .venv 11-file batch, under either color regime, with no production logging change.
- The o6y deferred ledger records D-1 as resolved in an audit-parseable form.
- Full quality suite green; two clean scoped commits on dev.
</success_criteria>

<output>
Create `.planning/quick/261111-rqr-fix-deferred-d-1-caplog-cross-test-leak-in-tests-unit-cli-te/261111-rqr-SUMMARY.md` when done (include: bisect result — the three leaking predecessor files, the mechanism, RED/GREEN evidence under both interpreters, full-suite result, and the two commit hashes).
</output>