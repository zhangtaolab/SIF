---
status: testing
phase: 18-quality-instrument-personal-bench-rapidfuzz-dym
source: [18-VERIFICATION.md]
started: 2026-11-15T00:00:00Z
updated: 2026-11-15T00:00:00Z
---

## Current Test

number: 1
name: P1 — body-leg query excerpt acceptable under the no-document-body-content prohibition
expected: |
  You agree titles/paths/ids/metrics plus the <=10-token synthesized excerpt
  (WR-05 disclosure) are the intended output.
awaiting: user response

## Tests

### 1. P1 — body-leg query excerpt acceptable under the no-document-body-content prohibition
expected: You agree titles/paths/ids/metrics plus the <=10-token synthesized excerpt (WR-05 disclosure) are the intended output.
result: [pending]

### 2. P2 — remote-provider disclosure plus --bm25-only satisfies the no-personal-data-upload prohibition
expected: No eval-owned upload; disclosure is accurate and visible on stderr and in report notes.
result: [pending]

### 3. P3 — per-leg and total rejected-query counts are sufficient transparency
expected: No silent query-set shrinkage.
result: [pending]

### 4. P4 — suppressed group names are listed and replay is labelled stability, never quality
expected: No zero-valued rendering for a suppressed group.
result: [pending]

### 5. P5 — per-leg rejection counts and the applied budget are always reported
expected: No hidden rejections.
result: [pending]

### 6. P6 — audit report fields for document content/snippets beyond query strings
expected: Query strings, paths, ids, metrics only.
result: [pending]

### 7. P7 — review the winner rule and held-out gating
expected: No winner inside noise and no defaults change from tuning results.
result: [pending]

### 8. P8 — run --compare against a changed corpus
expected: Clear refusal naming both fingerprints; no manufactured delta.
result: [pending]

### 9. P9 — inspect a saved run file from a real corpus
expected: Only query text/paths/ids/metrics; local cache only; short body excerpt acknowledged.
result: [pending]

### 10. P10 — feed a malformed saved run to --compare
expected: Clear ClickException naming the field; no traceback and no path opened.
result: [pending]

### 11. P11 — confirm scorer=fuzz.ratio and cutoff 75.0 on the 0-100 Indel scale, with no WRatio path
expected: Deliberate, documented scorer semantics.
result: [pending]

### 12. P12 — confirm every displayed suggestion re-queries to at least one hit
expected: No fabricated suggestion.
result: [pending]

### 13. P13 — confirm the search path never auto-rewrites a user query
expected: Suggestions remain display-only.
result: [pending]

### 14. Run `sif eval --personal` on a real indexed corpus with >=50 documents, then `--compare` the saved run after re-indexing
expected: Readable per-leg/group table, saved-run path on stderr, and a comparison with CI/winner columns; numbers plausible for the corpus.
result: [pending]

### 15. Run `sif suggest <first-letter-typo>` on a large indexed corpus
expected: Suggestions appear promptly (measured p50 1.376 ms at 73k terms) and include first-letter-typo corrections.
result: [pending]

## Summary

total: 15
passed: 0
issues: 0
pending: 15
skipped: 0
blocked: 0

## Gaps
