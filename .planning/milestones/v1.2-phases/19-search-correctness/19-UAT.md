---
status: testing
phase: 19-search-correctness
source: [19-VERIFICATION.md]
started: 2026-11-25T10:51:26Z
updated: 2026-11-25T10:51:26Z
---

## Current Test

number: 1
name: "In an 80-column terminal run 'sif search query --per-chunk QUERY' and 'sif search vsearch --per-chunk QUERY' on a corpus whose paths are 30+ characters"
expected: |
  Every chunk row shows which chunk it is (path#sequence)
awaiting: user response

## Tests

### 1. Per-chunk table shows chunk identity at 80 columns
test: "In an 80-column terminal run 'sif search query --per-chunk QUERY' and 'sif search vsearch --per-chunk QUERY' on a corpus whose paths are 30+ characters"
expected: Every chunk row shows which chunk it is (path#sequence)
result: [pending]

### 2. --min-score keeps the best BM25 matches
test: "Run 'sif search search \"Saltiv Protocol Notes\" -n 10' and then with --min-score 0.12 and --min-score 0.23 on the bench-fixture index"
expected: "Per the help text 'Minimum score threshold', weaker matches are removed and the best match survives"
result: [pending]

### 3. Chunk identity in per-chunk CSV, Markdown, XML and --files
test: "Run 'sif search query --per-chunk QUERY --csv', '--md', '--xml' and '--files' on a document with several matching chunks"
expected: "Decide whether chunk-level rows in machine formats must carry chunk identity and whether --files may repeat a path"
result: [pending]

### 4. Prohibition 19-03 P1 against the Phase 21 shadow read
test: "Review prohibition 19-03 P1 ('MUST NOT persist vector staleness as a per-document flag or issue a per-result embedding query') against src/sif/search/staleness.py:44-45,67-98"
expected: "A recorded decision that the Phase 21 shadow design (one PK lookup per result on embedded_documents) is the accepted successor of the Phase 19 batched scan"
result: [pending]

### 5. Truths 17 and 34: accept the Phase 20/21 mechanisms or require the literal behaviour
test: "Decide whether truths 17 and 34 are accepted for their guarantees (scope notes S2 and S4 below) or must hold literally"
expected: "Either record overrides for the Phase 20/21 mechanisms or ask for the Phase 19 literal behaviour back"
result: [pending]

## Summary

total: 5
passed: 0
issues: 0
pending: 5
skipped: 0
blocked: 0

## Gaps
