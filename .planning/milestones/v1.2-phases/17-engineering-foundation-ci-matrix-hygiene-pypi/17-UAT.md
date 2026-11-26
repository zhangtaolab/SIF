---
status: complete
phase: 17-engineering-foundation-ci-matrix-hygiene-pypi
source: [17-VERIFICATION.md]
started: 2026-11-24T23:52:31Z
updated: 2026-11-25T01:10:58.768Z
---

## Current Test

[testing complete]

## Tests

### 1. Push a branch carrying the restored 8-cell workflow and confirm the Test Matrix run
expected: Exactly 8 py<version> / <os> jobs (py3.10-3.13 x ubuntu-latest, macos-latest) plus lint / py3.12 / ubuntu-latest, all success, each cell logging the 90% coverage gate passing; record the run id and job conclusions.
result: pass
evidence: "Test Matrix run 45522236981 (push, gsd/phase-24-reverify @ a25eb07, attempt 1, 2026-11-25T00:58Z): lint + 8/8 py jobs success (py3.10-3.13 x ubuntu-latest, macos-latest); every cell logged 'Required test coverage of 90.0% reached. Total coverage: 95.12%' with 3259 passed, 2 skipped; no job cancelled or re-run"
performed_by: "agent, at the user's explicit request; the CI evidence is objective"

### 2. Review the 17 judgment-tier prohibition verdicts
expected: Each verdict in the Prohibitions table is confirmed, or the reviewer names the prohibition that is actually violated.
result: pass
evidence: "All 17 prohibition verdicts independently re-checked at a25eb07: deleted-layer set limited to the three dead modules; one explicit torch-only uv index; fail_under=90 with no --no-cov and no exclude; Windows smoke wording and temp-only paths; tag v1.1.2 -> c819f67 with the tag gate; job-scoped id-token and separate environments with zero secrets references; no rebuild in publish jobs; generated docs in sync; seven junk paths only; no revert commit and later commits remain ancestors; forbidden paths unchanged since ae1225e. Only non-planning literal mentions: docs/changelog.md:90 (history) and the tests/test_hygiene.py guard"
performed_by: "agent, at the user's explicit request; these are reviewer judgments, not test-backed results"

## Summary

total: 2
passed: 2
issues: 0
pending: 0
skipped: 0
blocked: 0

## Gaps
