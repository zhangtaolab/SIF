---
phase: 17-engineering-foundation-ci-matrix-hygiene-pypi
reviewed: 2026-11-24T14:39:26Z
depth: standard
files_reviewed: 5
files_reviewed_list:
  - .github/workflows/test-matrix.yml
  - docs/contributing.md
  - docs/development.md
  - docs/testing.md
  - tests/test_ci_workflows.py
findings:
  critical: 0
  warning: 0
  info: 1
  total: 1
  necessity: 0
status: issues_found
---

# Phase 17: Code Review Report

**Reviewed:** 2026-11-24T14:39:26Z
**Depth:** standard
**Files Reviewed:** 5
**Status:** issues_found

## Summary

This is an **incremental** review of plan 17-10, the gap-closure restore of the 8-cell CI matrix (`10a9685`, `a321eaa`; `49454bf` touched `17-10-SUMMARY.md` only). Phase 17 itself is archived. The scope is what changed since the last commit touching this report (`18f1e87`). The SUMMARY tier and the evaluation-scope resolver returned the same five files (`status: resolved`, `source: task-commits`). The resolver also reported `17-04`, `17-06` and `17-09` SUMMARYs as having Task Commits sections it could not read; those files are unchanged since `18f1e87` and were not widened into this scope.

No Critical and no Warning findings. One Info finding (IN-12) is new. Everything else this review observed about guard weakness is already recorded in other phase artifacts; it is cited below, not re-reported.

Checked at HEAD `1984c45`:

- **Workflow.** `.github/workflows/test-matrix.yml` is byte-identical to the workflow phase 17 shipped (blob `cb340cbe` at both `6217898c` and HEAD), so the restore is exact and not a re-implementation. The CI/CD checks pass: job-level timeouts on both jobs, a concurrency group, `contents: read`, a SHA-pinned `setup-uv`, a tag-pinned `actions/checkout`, `uv sync --frozen`, and no secrets or `continue-on-error`. The workflow only runs tests, so `cancel-in-progress` is an optimization here rather than a required guard.
- **Guards.** `pytest --no-cov tests/test_ci_workflows.py` reports 18 passed. The real `14d7d245` workflow blob (the recorded six-cell, main-only reduction) now fails `test_matrix_declares_eight_cells` and `test_matrix_push_trigger_covers_all_branches` (2 failed, 4 passed). A dropped OS, an added OS and each skip key are rejected too. `ruff check` and `ruff format --check` (ruff 0.15.11) are clean on the module.
- **Docs.** All 13 changed lines agree with the workflow and the guards: `docs/contributing.md:365,400,402,405,407`, `docs/development.md:609,732,751,769-770`, `docs/testing.md:130,212,214`. No six-cell or main-only wording about the Test Matrix remains in any tracked file outside `.planning`; the surviving `branches: [main]` mentions describe `docs.yml`, which is correct.

Already recorded, reproduced by this review's probe, and not re-reported: the nested trigger filters (`17-VALIDATION.md`, Manual-Only row 8) and the four further shapes in `17-SECURITY.md` (an option appended to the pytest step, job-level `contents: write` on the `test` job, `if: false` or `continue-on-error: true` on the `lint` job). The double run for a branch with an open pull request and hosted macOS capacity are the accepted risk AR-17-03 (T-17-30). No GitHub Actions run exists yet for the restored workflow (Manual-Only row 7), so "runs green" is still unverified and is not claimed here.

Rows of the existing disposition ledger that this review verified as fixed at HEAD:

- **IN-10**: fixed by `10a9685`. The guard derives the 2 × 4 product from both declared lists, which closes both gaps the row named.
- **IN-11**: fixed by `10a9685` as a declaration. The workflow is again the phase's original, so roadmap criterion 1 reads true; the "runs green" half stays open in Manual-Only row 7.
- **WR-02**: fixed by `42e1acd` and `e539795`, which removed the contradictory "only workflow is Docs Validation" sentences from the guides on 2026-11-17; `a321eaa` then re-aligned the cell and trigger wording. The regression guard that row also suggested was never added: the three guides are still outside `DOCS_FILES` in `tests/test_docs.py`.

The same rewrite resolves the first bullet of IN-01; its other bullets were not re-reviewed. Two carried rows were observed in passing, not re-reviewed: IN-09 still holds (`docs/testing.md:4` says 3,234 tests, and 3,261 collect at HEAD), and WR-06 and WR-07 are still visible in `.github/workflows/publish.yml`. Finding ids in this report continue at IN-12, so no earlier ledger row is reused for a different finding.

Necessity was assessed against the rubric and yields no finding. The token-presence pre-check at `tests/test_ci_workflows.py:194-199` is now subsumed by the product assertion at `:231-236`, but it runs first as a fail-fast with a clearer message and does not guard an impossible state. No structural section is included because no structural pre-pass was configured. This review was performed inline from `gsd-code-reviewer.md` by the orchestrator, because this runtime exposes no Agent tool; no external reviewer evidence was supplied.

## Narrative Findings (AI reviewer)

All findings below come from direct code review of the five scoped files. Each cites lines re-read at HEAD `1984c45`.

## Info

### IN-12: Eight-cell guard pins the declared axes but not that the cells run on `matrix.os` and `matrix.python-version`

**File:** `tests/test_ci_workflows.py:190-242` (the guard); `.github/workflows/test-matrix.yml:18`, `:19`, `:32`, `:38` (the lines no guard reads)
**Issue:** `test_matrix_declares_eight_cells` rebuilds the 2 × 4 product from the `os:` and `python-version` lists and rejects `exclude`, `include`, `if` and `continue-on-error` anywhere in the `test` job. That closes IN-10 and the first bullet of IN-01. It does not assert that the job consumes the two axes it declares. No guard reads `runs-on: ${{ matrix.os }}` (`test-matrix.yml:18`), the `setup-uv` `python-version: ${{ matrix.python-version }}` (`:32`) or `uv python install ${{ matrix.python-version }}` (`:38`).

Method: `_workflow_text` was swapped for mutated copies in memory, so no file was touched, and the six guards that read the workflow were run against each. Of 25 altered copies (24 in-memory mutations plus the real `14d7d245` blob), 13 were rejected and 12 passed. The 12 that passed are the seven already-recorded shapes tried as controls (four from `17-SECURITY.md`, three trigger filters from Manual-Only row 8) and five that no artifact records:

- `runs-on: ${{ matrix.os }}` replaced by `runs-on: ubuntu-latest`: all six guards pass.
- `uv python install ${{ matrix.python-version }}` replaced by `uv python install 3.12`, the `setup-uv` `python-version:` replaced by `'3.12'`, or both: all six pass.
- `timeout-minutes: 30` deleted from the `test` job: all six pass.

Combining the first two leaves a single Ubuntu/py3.12 cell run eight times with every guard green. The job `name` (`test-matrix.yml:17`) still reads `matrix.*`, so those eight jobs keep their py3.10-3.13 × ubuntu/macos labels and the loss of macOS and Python-version coverage is silent. The timeout deletion is a missing-timeout regression rather than a narrowing one; it is listed only because the same follow-up guard would cover it.

This shape is not among the 18 the plan's own mutation check tried (`17-10-SUMMARY.md`, Residual Observations) and is in neither recorded list. The workflow is correct at HEAD; this is a gap in the guard. Whether to add it belongs to the open maintainer decision the security note already records.

**Attribution:** pre-existing, not introduced by plan 17-10. The guards at `18f1e87` pass the same single-line mutations against the six-cell workflow. The 17-10 rewrite closed the declared-shape gaps and stopped there.
**Fix:** assert axis consumption inside the `test_job` block, after `cells = declared_cells()` (`tests/test_ci_workflows.py:231`). Checked in memory against the same five mutations: it passes at HEAD and rejects all five.

```python
    for consumed in (
        "runs-on: ${{ matrix.os }}",
        "python-version: ${{ matrix.python-version }}",
        "uv python install ${{ matrix.python-version }}",
    ):
        assert consumed in test_job, f"the test job must consume its matrix axes; missing {consumed!r}"
    assert "timeout-minutes:" in test_job, "the test job must keep a job-level timeout"
```

---

_Reviewed: 2026-11-24T14:39:26Z_
_Reviewer: gsd-code-reviewer, run inline by the orchestrator (this runtime has no Agent tool)_
_Depth: standard_
