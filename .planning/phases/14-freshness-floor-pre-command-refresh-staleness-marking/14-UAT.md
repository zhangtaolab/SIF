---
status: testing
phase: 14-Freshness Floor (Pre-Command Refresh + Staleness Marking)
source: [14-VERIFICATION.md]
started: 2026-11-08T04:35:00Z
updated: 2026-11-08T04:35:00Z
---

## Current Test

number: 1
name: D-05 refresh-failure leg — decide accept vs. add exercising test
expected: |
  The `except` branch at src/sif/cli/commands/search.py:200-210 (refresh failure →
  stderr warning, exit 0, search proceeds on stale index) is present and wired but
  has NO exercising test (suite-wide grep for exception injection on
  detect_drift/refresh_drifted: zero hits). The over-cap leg of the same
  prohibition IS test-enforced. Human decides: accept the flag as-is, or add the
  ~5-line test (patch refresh_drifted to raise; assert warning + exit 0).
awaiting: user response

## Tests

### 1. D-05 refresh-failure leg — decide accept vs. add exercising test
expected: Decide: accept the flagged (present-but-unexercised) refresh-failure warning path, or add the small exception-injection test the verifier sketched (patch refresh_drifted to raise; assert stderr warning + exit 0 + results still returned).
result: [pending]

### 2. SC2 perceived latency on a real knowledge base
expected: Run `sif search <query>` against your real KB with a clean index (no drift) and confirm the pre-command stat walk is imperceptible. SC2's near-zero cost was proven structurally (no lock, no writes, no notice); this is the performance-feel judgment only a human can make on real hardware/corpus.
result: [pending]

## Summary

total: 2
passed: 0
issues: 0
pending: 2
skipped: 0
blocked: 0

## Gaps
