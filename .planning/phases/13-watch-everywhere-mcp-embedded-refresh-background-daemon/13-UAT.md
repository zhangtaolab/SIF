---
status: testing
phase: 13-Watch Everywhere (MCP-Embedded Refresh + Background Daemon)
source: [13-VERIFICATION.md]
started: 2026-11-08T02:30:00Z
updated: 2026-11-08T02:30:00Z
---

## Current Test

number: 1
name: Burst read-side atomicity (13-03 backstop truth)
expected: |
  During a debounced burst applying multiple files, concurrent readers (CLI/MCP search)
  never observe a partially-applied burst state — each reader sees either the
  pre-burst or post-burst index, never a half-applied one.
awaiting: user response

## Tests

### 1. Burst read-side atomicity
expected: During a burst, concurrent searches never see partially-applied state (backstop-tagged truth in 13-03; no test asserts read-side non-exposure — non-inferable, verifier abstained per honest-verifier contract).
result: [pending]

### 2. Live launchd round-trip
expected: On the macOS dev box run `SIF_TEST_LIVE_LAUNCHD=1 env -u FORCE_COLOR NO_COLOR=1 python -m pytest tests/integration/test_service_live_launchd.py -x` — the real bootstrap/serve/bootout cycle passes and leaves no leaked service (mutates OS service state, so the verifier skipped it; the "passed twice" claim in 13-04-SUMMARY is SUMMARY-only evidence).
result: [pending]

### 3. WR-01 shutdown-checkpoint decision
expected: Confirm that SKIPPING (not attempting) the shutdown `PRAGMA wal_checkpoint(TRUNCATE)` when the worker thread outlives the join window is the intended D-14 behavior — the alternative is attempting the checkpoint on a connection a stuck worker may still hold (flagged "requires human verification" in 13-REVIEW-FIX.md; commit e3156da).
result: [pending]

### 4. WR-04 killpg decision
expected: Confirm `os.killpg` on the intermediate child's pid (the pgid setsid established) is acceptable in the rare PID-recycling window — the theoretical failure is killing an innocent recycled process group after a 30s handshake timeout (flagged in 13-REVIEW-FIX.md; commit cd33b21).
result: [pending]

### 5. Prohibition sign-off
expected: 12 judgment-tier `flagged-unverified` prohibitions (authored descriptor-less from the spec-less probe fallback) were evaluated by the verifier as all honored — evidence per item is in 13-VERIFICATION.md §prohibitions. Human review recommended to make that non-authoritative verdict authoritative.
result: [pending]

## Summary

total: 5
passed: 0
issues: 0
pending: 5
skipped: 0
blocked: 0

## Gaps
