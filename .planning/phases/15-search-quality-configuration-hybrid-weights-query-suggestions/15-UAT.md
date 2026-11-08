---
status: testing
phase: 15-Search Quality Configuration (Hybrid Weights + Query Suggestions)
source: [15-VERIFICATION.md]
started: 2026-11-08T11:00:00Z
updated: 2026-11-08T11:00:00Z
---

## Current Test

number: 1
name: Suggestion quality on a real personal KB
expected: |
  Run `sif suggest <prefix>` and a few zero-result `sif search` queries on your
  real knowledge base. Judge: DYM usefulness, acceptance of porter-stem display
  (suggestions read like "quantum machin"), index-global suggestions under
  collection filters, CJK run-level completions.
awaiting: user response

## Tests

### 1. Suggestion quality on a real personal KB
expected: On your real KB, DYM suggestions are useful; porter-stem display is acceptable; collection-filtered searches may suggest terms from other collections (accepted design); CJK queries yield run-level completions.
result: [pending]

### 2. Accept the zero-result-only trigger (CONTEXT D-05)
expected: Confirm the product decision — ROADMAP SC2 says "zero- or low-result", CONTEXT D-05 deliberately narrows to zero-result only (low-result was rejected to avoid noise and an untuned threshold). The implementation honors D-05.
result: [pending]

### 3. Perceived latency on the real index
expected: Time `sif suggest <prefix> --json` on your real KB and compare with `sif --help`. Synthetic measurement (20,003-term index): total 0.69–0.70s vs 0.69–0.70s baseline → ≤ ~10 ms core work; confirm the real KB feels the same.
result: [pending]

### 4. Security follow-up — /gsd-secure-phase 15
expected: Produce 15-SECURITY.md (7 threat-model entries from the plans; ASVS L1 audit). Not a verification failure — the standard post-verification step, run before phase advancement.
result: [pending]

### 5. Terminal rendering of the three Rich sections
expected: `sif suggest <prefix>` renders the three labeled sections (Prefix completions / Did you mean / History) cleanly at your terminal width — no wrapping artifacts.
result: [pending]

## Summary

total: 5
passed: 0
issues: 0
pending: 5
skipped: 0
blocked: 0

## Gaps
