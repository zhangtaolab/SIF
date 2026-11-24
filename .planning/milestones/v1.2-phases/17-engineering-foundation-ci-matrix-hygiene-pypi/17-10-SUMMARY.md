---
phase: 17-engineering-foundation-ci-matrix-hygiene-pypi
plan: 10
subsystem: ci
tags: [github-actions, ci-matrix, regression-guards, docs, gap-closure]

# Dependency graph
requires:
  - phase: 17-03
    provides: "The 8-cell test matrix workflow, its text guards in tests/test_ci_workflows.py, and the standing prohibition on weakening the coverage gate or dropping a cell"
provides:
  - ".github/workflows/test-matrix.yml restored byte-exact to the 14d7d245^ body: 8 cells (py3.10-3.13 x ubuntu-latest/macos-latest), no skip entries, push on ['**'], pull_request retained"
  - "tests/test_ci_workflows.py: test_matrix_declares_eight_cells and test_matrix_push_trigger_covers_all_branches, both observed red on the six-cell workflow; the reduced-shape guards and MATRIX_EXCLUSION are gone"
  - "docs/development.md, docs/contributing.md, and docs/testing.md agree with the restored workflow in all thirteen statements that described the reduced matrix"
  - "Plan base record left in place so the base-anchored gates can be re-run"
affects: [17]

# Actuals (#2632): tokens are chars/4 over the unified diff of the five changed files.
# commits counts the two task commits measured from the plan ledger; this SUMMARY is committed after them.
actuals:
  tokens: 5276
  tasks: 2
  commits: 2
  plan_head_before: ae1225ebd240a05300f73b571f1ea30b63f79c23
  plan_head_after: a321eaa4f8e9734325e7898215ca2a46459962d7

tech-stack:
  added: []
  patterns:
    - "Contract guards derive the shape they protect: the matrix guard rebuilds the os x python-version product from the declared lists and rejects skip keys, instead of pinning literals that a reduced workflow can still satisfy"

key-files:
  created: []
  modified:
    - .github/workflows/test-matrix.yml
    - tests/test_ci_workflows.py
    - docs/development.md
    - docs/contributing.md
    - docs/testing.md

key-decisions:
  - "Edit forward, never git revert: the workflow was changed in exactly two places until it equaled the 14d7d245^ body, so f665eee1 and 848e6b6a survive in the guard module and 0cdd69de survives at docs/development.md line 626"
  - "The matrix guard derives the product from the declared os and python-version lists and treats exclude, include, if, and continue-on-error in the test job as skip entries; the pre-reduction guard checked literals only and passed on the six-cell workflow"
  - "The trigger guard requires the contiguous on:/push:/branches: ['**'] lines, a bare pull_request: line at the on: child level, and no tags: key; filters nested under either trigger are not examined (see Residual Observations)"
  - "Real GitHub Actions execution of the restored 8 cells is not locally verifiable and is not claimed; the post-push confirmation stays a manual follow-up"

patterns-established:
  - "Observe a rewritten contract guard red before the fix: run it against the known-bad shape in the tree, then re-run it against that shape by a gate after the fix"

requirements-completed: [ENG-01]

coverage:
  - id: D1
    description: "test-matrix.yml declares the full 8-cell cross product (py3.10-3.13 x ubuntu-latest/macos-latest) on every branch push and every pull request, byte-identical to the 14d7d245^ body"
    requirement: ENG-01
    verification:
      - kind: integration
        ref: "git diff --quiet 14d7d245^ -- .github/workflows/test-matrix.yml (exit 0)"
        status: pass
      - kind: unit
        ref: "tests/test_ci_workflows.py#test_matrix_declares_eight_cells"
        status: pass
      - kind: unit
        ref: "tests/test_ci_workflows.py#test_matrix_push_trigger_covers_all_branches"
        status: pass
    human_judgment: false
  - id: D2
    description: "The two rewritten guards reject the reduced shape: both fail on their own assertions against the six-cell workflow and pass against the restored one"
    requirement: ENG-01
    verification:
      - kind: integration
        ref: "red-derivation gate against 14d7d245:.github/workflows/test-matrix.yml (exit 0; inner pytest exit 1, 2 failed, both AssertionError)"
        status: pass
      - kind: integration
        ref: "env -u FORCE_COLOR NO_COLOR=1 pytest tests/test_ci_workflows.py -x -q --no-cov (18 passed)"
        status: pass
      - kind: integration
        ref: "ruff check tests/test_ci_workflows.py && ruff format --check tests/test_ci_workflows.py"
        status: pass
    human_judgment: false
  - id: D3
    description: "docs/development.md, docs/contributing.md, and docs/testing.md state eight cells and the every-branch push plus pull-request trigger, with no residual reduced wording"
    verification:
      - kind: integration
        ref: "Task 2 doc gates 1-11 (three negative greps print nothing; positive counts 4/3/2 and 1/1/1; git diff --quiet e8ab1148^ exit 0)"
        status: pass
      - kind: unit
        ref: "tests/test_docs.py (inside the 67-test phase guard battery)"
        status: pass
    human_judgment: false
  - id: D4
    description: "Scope holds: exactly the five declared paths changed since the plan base, and every line of the guard module outside the two guard slots and the freed constant line is byte-identical to the base"
    verification:
      - kind: integration
        ref: "base-anchored scope gate (changed set equals the five declared files)"
        status: pass
      - kind: integration
        ref: "untouched-module gate (303 remainder lines on both sides, no diff)"
        status: pass
      - kind: integration
        ref: "env -u FORCE_COLOR NO_COLOR=1 pytest (3260 passed, 1 skipped, 95.12%, fail_under=90 reached)"
        status: pass
    human_judgment: false
  - id: D5
    description: "The restored 8 cells plus the lint job run green on GitHub Actions on a real branch push (the runs-green half of SC1/ENG-01)"
    requirement: ENG-01
    verification: []
    human_judgment: true
    rationale: "Not locally verifiable and not claimed: no GitHub Actions run was executed for this change. Settled only by the manual post-push follow-up recorded below."

duration: 16min
completed: 2026-11-24
status: complete
---

# Phase 17 Plan 10: Restore the 8-Cell CI Matrix Summary

**`test-matrix.yml` restored byte-exact to the pre-reduction body (py3.10-3.13 × ubuntu/macos on every branch push and every pull request), re-pinned by two rewritten guards that were observed red on the six-cell workflow, with three docs files brought back into agreement.**

## Performance

- **Duration:** 16 min
- **Started:** 2026-11-24T12:29:33Z
- **Completed:** 2026-11-24T12:45:50Z
- **Tasks:** 2/2
- **Files modified:** 5

## Plan Base and Precondition

- Plan base: `ae1225ebd240a05300f73b571f1ea30b63f79c23`, recorded at Task 1 Step 0 in `.git/gsd-plan-17-10-base` (the path `git rev-parse --git-path gsd-plan-17-10-base` prints). It is the parent of the first `(17-10)` commit and is left in place so the untouched-module and scope gates can be re-run.
- Precondition: `git diff --quiet d3f3b8d6` over the five files exited 0, and `pytest`, `ruff`, and `git` were on PATH.
- Ground truth: `git log --oneline 14d7d245..HEAD -- .github/workflows/test-matrix.yml` printed nothing, so the `14d7d245^` body was the correct target.

## Guard Red Run (Task 1 Step 3)

Run with the workflow still at the six-cell body:

```
env -u FORCE_COLOR NO_COLOR=1 pytest tests/test_ci_workflows.py::test_matrix_declares_eight_cells tests/test_ci_workflows.py::test_matrix_push_trigger_covers_all_branches -q --no-cov
```

Exit code 1. Short test summary, verbatim:

```
FAILED tests/test_ci_workflows.py::test_matrix_declares_eight_cells - Asserti...
FAILED tests/test_ci_workflows.py::test_matrix_push_trigger_covers_all_branches
2 failed in 0.04s
```

- `test_matrix_declares_eight_cells` raised at `tests/test_ci_workflows.py:238`, `assert skip_entries == []`, with `['exclude']`. Every earlier assertion passed, including the product check: the six-cell workflow still declares the full `os` and `python-version` lists, which is why the pre-reduction literal guard passed on it.
- `test_matrix_push_trigger_covers_all_branches` raised at `tests/test_ci_workflows.py:288`, `assert ALL_BRANCH_PUSH_TRIGGER.search(text) is not None`.
- The red-derivation gate re-ran the committed guards against `14d7d245:.github/workflows/test-matrix.yml` in a temp dir: exit 0, inner pytest exit 1, both FAILED lines naming an AssertionError, `2 failed in 0.03s`.

This red run was observed twice with the same outcome. The first observation used a draft of the trigger guard whose `pull_request:` regex was wrong (see Issues Encountered). After the fix, the tree's workflow was put back at the six-cell body for the duration of one command, the run recorded above was taken, and the workflow was restored to the target body. The lines above are from the corrected guard, the one that is committed.

## Accomplishments

- Restored `.github/workflows/test-matrix.yml`: `branches: [main]` back to `branches: ['**']` and the five-line `exclude` block removed. The result is byte-identical to `14d7d245^:.github/workflows/test-matrix.yml` (74 lines): 8 cells, `fail-fast: false`, `cancel-in-progress: true`, `permissions: contents: read`, the SHA-pinned `setup-uv`, `uv sync --frozen --extra dev --extra embed`, the bare pytest step, and the whole `lint` job unchanged.
- Rewrote the two guards in the same slots. `test_matrix_declares_eight_cells` scopes to the `test` job through `_job_block`, extracts the `os:` and `python-version:` bracket lists, builds and compares the 2 × 4 product, and rejects `exclude`, `include`, `if`, and `continue-on-error` anywhere in the job block. `test_matrix_push_trigger_covers_all_branches` pins the contiguous `on:` / `push:` / `branches: ['**']` lines, a bare `pull_request:` line, and the absence of `tags:`. `MATRIX_EXCLUSION` is replaced by five constants on the freed line, and every failure message quotes the offending text.
- Brought the three docs files back to their pre-reduction wording by reverse-applying only the three docs hunks of `e8ab1148` (13 lines each way, byte-identical to the inverse of the reduction). `docs/contributing.md` and `docs/testing.md` equal their `e8ab1148^` bodies; `docs/development.md` equals its `e8ab1148^` body except line 626, which keeps the `0cdd69de` canonical-case attestation example.
- Kept scope exact: the base-anchored gate shows exactly the five declared files, and `.github/workflows/publish.yml`, `pyproject.toml`, `uv.lock`, `src/`, and `tests/conftest.py` are identical to the plan base.

## Task Commits

Each task was committed atomically:

1. **Task 1: Re-derive the guard contract, see it red, restore the 8-cell matrix and all-branch push trigger** - `10a9685` (fix)
2. **Task 2: Bring the three docs files back in line and prove the phase guard battery** - `a321eaa` (docs)

**Plan metadata:** this SUMMARY is committed separately, immediately after it is written (docs: complete 17-10 plan).

## Gate Evidence

Every gate below was run on the final tree at `a321eaa`. The full suite ran on a working tree that is byte-identical to that commit.

| Gate | Outcome |
|------|---------|
| **Task 1** | |
| `pytest tests/test_ci_workflows.py -x -q --no-cov` | 18 passed |
| Red-derivation gate (committed guards vs the reduction commit's workflow) | exit 0; inner pytest exit 1, 2 failed, both AssertionError |
| No reduced-shape guard or `MATRIX_EXCLUSION` constant left | exit 0, no output |
| `git diff --quiet 14d7d245^ -- .github/workflows/test-matrix.yml` | exit 0 |
| All-branch push line declared exactly once | exit 0, count 1 |
| Untouched-module gate | exit 0; 303 remainder lines on both sides, no diff |
| `ruff check` and `ruff format --check` on the guard module | All checks passed; 1 file already formatted |
| Tracer feedback gate (auto mode: verify re-run after the Task 1 commit) | all seven gates green again at `10a9685` |
| **Task 2** | |
| Three negative doc greps: reduced count, main-only snippet, main-only or PR-reliance phrasing | exit 0, no output; positive controls on the reduced bodies found 9, 2, and 5 lines |
| Eight-cell counts | development 4, contributing 3, testing 2 |
| Trigger wording counts | 1 / 1 / 1; PR-CI bullet phrase 1; tag-push sentence 1 |
| `0cdd69de` attestation line kept | count 1 (line 626) |
| `git diff --quiet e8ab1148^ -- docs/contributing.md docs/testing.md` | exit 0 |
| Phase guard battery (four modules) | 67 passed |
| Full suite, `env -u FORCE_COLOR NO_COLOR=1 pytest` | exit 0; 3260 passed, 1 skipped, 27 warnings in 200.91s; coverage 95.12%, fail_under=90 reached |
| Base-anchored scope gate | exit 0 before and after the Task 2 commit; changed set is exactly the five declared files |
| CLAUDE.md quality suite | `ruff check src tests` clean; `ruff format --check src tests` 237 files already formatted |

The 27 warnings are pre-existing `ResourceWarning: unclosed database` messages from unrelated code; none is attributed to the guard module. `ty check src/sif` reports 10 diagnostics under the local py3.13 interpreter; `src/` is identical to the plan base and `17-VERIFICATION.md` already records them as post-phase drift, so they were left alone.

## Files Created/Modified

- `.github/workflows/test-matrix.yml` - trigger line restored to `['**']`; the two macOS `exclude` entries removed
- `tests/test_ci_workflows.py` - five constants on the freed `MATRIX_EXCLUSION` line; `test_matrix_declares_eight_cells` and `test_matrix_push_trigger_covers_all_branches` replace the reduced-shape guards in the same slots
- `docs/development.md` - release step, workflow table row, PR-CI bullet, coverage note
- `docs/contributing.md` - release step, Test Matrix intro, test bullet, trigger note, release gate sentence
- `docs/testing.md` - `test_ci_workflows.py` contract bullet, trigger sentence, test-job matrix sentence

Nothing was created or deleted.

## Decisions Made

- **Edit forward, never `git revert`.** The workflow was changed in exactly two places until it matched the `14d7d245^` body, so the later commits that touched these files survive: `f665eee1` and `848e6b6a` in the guard module, `0cdd69de` in `docs/development.md`.
- **The matrix guard derives the shape it protects.** It rebuilds the product from the declared lists and rejects skip keys. The pre-reduction guard checked literals only, which is why it passed on the six-cell workflow.
- **"Top-level `pull_request:`" means a child of `on:`.** In this workflow the key sits at a two-space indent beside `push:`, so the guard matches that bare line. The plan's wording left the anchoring open; column 0 does not occur in the file.
- **Docs were restored mechanically from the authoritative source.** The target was byte-exact and the lines contain en-dashes and `×`, so the reduction's own docs hunks were reverse-applied instead of retyped. This is neither a revert commit nor a whole-file paste.
- **The GitHub Actions run is not claimed.** See Manual Follow-Up.

## Deviations from Plan

None - plan executed exactly as written. Every gate ran as written and passed; none was weakened or skipped.

## Issues Encountered

1. **Trigger guard draft anchored at the wrong level; fixed before the first commit.** My first draft matched `pull_request:` at column 0. Against the restored workflow the module gate returned `1 failed, 12 passed` at line 292. I changed the regex to the `on:` child level, re-observed the red run, and all seven gates then passed. The faulty form was never committed.
2. **Three mistakes in my own verification harness, each caught and re-run.**
   - A mutation harness ran the whole guard module in a bare temp dir, so unrelated guards errored on the missing `uv.lock` and `pyproject.toml`. It was re-run against the six guards that read only the workflow.
   - A helper passed `!` to grep as a command (exit 127), so three negative gates were not evaluated at all.
   - This shell is zsh, which does not word-split an unquoted variable. grep received one non-existent filename, errored, and `!` turned that error into a false `exit=0` for the same three negative doc gates. The "No such file" warning exposed it; they were re-run with explicit paths and positive controls.
   No result recorded under Gate Evidence comes from a faulty run.
3. `grep` resolves to `ugrep 7.8.4` on this machine; every gate ran with it.

## Residual Observations (not fixed - outside this plan's scope)

- **The trigger guards do not examine filters nested under either trigger.** A temp-dir mutation check against the six workflow-reading guards tested 18 reduced or narrowed shapes and rejected 13 of them: a dropped Python version, a dropped OS, a duplicated version, `exclude`, `include`, a step-level `if`, job-level `continue-on-error`, a flow-style filter on the `pull_request:` line, `branches: [main]`, a removed `pull_request:`, a `tags:` key, `fail-fast: true`, and `--no-cov`. Five passed: a block-style `branches: [main]` or `paths: ['src/**']` under `pull_request:`, and `paths`, `paths-ignore`, or `branches-ignore` under `push:`. This follows from the plan's own wording, which specifies those three trigger assertions and says nothing about filters. Narrowing CI by path would therefore pass the guards silently. Decision for the maintainer: whether a follow-up should pin both triggers as unfiltered. The phase's deferred-items file was not edited, because this run was restricted to the five declared files plus this SUMMARY.
- **T-17-30 is accepted, not mitigated.** The restore brings back both causes recorded for the reduction: hosted macOS arm64 capacity that cancelled PR jobs before, and a double run for a feature-branch commit that has an open pull request. `cancel-in-progress: true` bounds neither.

## Manual Follow-Up (not locally verified)

No GitHub Actions run was executed for this change, and none is claimed. The historical run 43561542242 on c819f67 is history only, not evidence for this change. After the plan is pushed, the orchestrator or maintainer runs:

1. Push a branch to origin, or update an open pull request, and open the Test Matrix run. Expected: 8 `py<version> / <os>` jobs plus the lint job, all successful. Record the run id and the job conclusions.
2. Capacity-cancelled cell: re-run the cancelled job once from the run page. Record the job name and the re-run result.
3. If the cancellation recurs on the re-run: do not remove cells, add skip entries, or narrow the trigger by hand. The recorded fallback is a new recorded decision that returns to the six-cell shape by reversing this plan's three changes together (workflow, guards, docs) and attaching the recurrence evidence. Until that decision exists the workflow stays at eight cells and the confirmation stays open.
4. Red cell: treat it as a regression the reduced matrix was masking, either on the restored macOS 3.11 and 3.12 cells or on a branch push the main-only trigger never ran. Fix forward in a follow-up change; do not drop the cell, add `--no-cov`, or lower `fail_under`.

## Threat Model Disposition

- T-17-30 (denial of service, restored 8-cell matrix): accepted, as the plan records.
- T-17-31 (tampering, workflow configuration integrity): mitigated. The workflow is byte-identical to `14d7d245^`; the untouched-module and scope gates are green; the surviving guards pin `fail-fast`, concurrency, `contents: read`, the `setup-uv` SHA, `uv sync --frozen`, and the absence of `--no-cov`, `secrets.`, and `id-token`. No `git revert` was used.
- T-17-32 (repudiation, guard truthfulness): mitigated. Rejection of the reduced shape was observed in the tree and again by the red-derivation gate.
- T-17-SC-10 (package installs): no package was installed, added, or removed.

No threat flags: this plan adds no endpoint, secret, permission, or OIDC surface beyond what its threat model already records.

## Known Stubs

None.

## Next Phase Readiness

- The declared half of the Phase 17 gap is closed at `a321eaa`: truth 11 (every branch push and every pull request runs the full suite on exactly 8 test cells) holds again as a declaration, and CONTEXT decisions D-01 and D-03 are true again without editing the archived decisions.
- Still open: the "runs green" half, settled only by the manual follow-up above.
- Still open: re-run the Phase 17 verifier so truth 11 and decision coverage (currently 13/15, with D-01 and D-03 reversed) are re-derived from this tree. `17-VERIFICATION.md` was not edited.
- Not done by this executor, by instruction: `STATE.md`, `ROADMAP.md`, and `REQUIREMENTS.md` (the ENG-01 checkbox) are untouched; the orchestrator owns those writes.

## Self-Check: PASSED

Run at `a321eaa`, immediately before this SUMMARY was written:

- Files: all five modified files are present on disk; nothing was created or deleted.
- Commits: `10a9685` and `a321eaa` are ancestors of HEAD, and the ledger-to-HEAD count is 2.
- End states: the workflow equals the `14d7d245^` target; `docs/contributing.md` and `docs/testing.md` equal their `e8ab1148^` counterparts; `docs/development.md` differs from its `e8ab1148^` counterpart only at line 626.
- Plan base record present and equal to the parent of the first `(17-10)` commit.
- Working tree clean outside `.planning/`.

The "runs green" half of SC1/ENG-01 is not covered by this self-check; see Manual Follow-Up.

---
*Phase: 17-engineering-foundation-ci-matrix-hygiene-pypi*
*Completed: 2026-11-24*
