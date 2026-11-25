---
status: diagnosed
phase: 19-search-correctness
source: [19-VERIFICATION.md]
started: 2026-11-25T10:51:26Z
updated: 2026-11-25T14:26:57Z
---

## Current Test

number: 3
name: "Run 'sif search query --per-chunk QUERY --csv', '--md', '--xml' and '--files' on a document with several matching chunks"
expected: |
  Decide whether chunk-level rows in machine formats must carry chunk identity and whether --files may repeat a path
awaiting: user decision

## Tests

### 1. Per-chunk table shows chunk identity at 80 columns
test: "In an 80-column terminal run 'sif search query --per-chunk QUERY' and 'sif search vsearch --per-chunk QUERY' on a corpus whose paths are 30+ characters"
expected: Every chunk row shows which chunk it is (path#sequence)
result: issue
reported: "At 80 columns neither 'sif search query --per-chunk' nor 'sif search vsearch --per-chunk' shows the '#sequence' suffix on any of 12 chunk rows (0 of 12): the Chunk column is 16 and 25 characters wide and every row is ellipsised before the suffix, so rows of the same document cannot be told apart. The suffix appears only from 120 columns (vsearch) and 200 columns (query), and only for a 44-character path; a 177-character path never showed it in 'query' up to 260 columns. JSON carries chunk_id and sequence."
severity: major
performed_by: "agent, at the user's explicit request, on an isolated scratch index (20 documents, 71 chunks, temporary SIF_DB_PATH and SIF_CACHE_DIR); severity is the tester's inference"

### 2. --min-score keeps the best BM25 matches
test: "Run 'sif search search \"Saltiv Protocol Notes\" -n 10' and then with --min-score 0.12 and --min-score 0.23 on the bench-fixture index"
expected: "Per the help text 'Minimum score threshold', weaker matches are removed and the best match survives"
result: issue
reported: "On the scratch index 'sif search search \"Saltiv Protocol Notes\" -n 10' ranks 'Saltiv Protocol Notes' first with Score 0.1046 and 'Qelron Protocol Notes' second with 0.1212. '--min-score 0.12' removes the rank-1 (best) match and keeps the weaker rank-2 match; 0.23 and above return nothing. A better match shows a lower score, so the threshold removes the strongest matches first."
severity: major
performed_by: "agent, at the user's explicit request, on the same scratch index; severity is the tester's inference"

### 3. Chunk identity in per-chunk CSV, Markdown, XML and --files
test: "Run 'sif search query --per-chunk QUERY --csv', '--md', '--xml' and '--files' on a document with several matching chunks"
expected: "Decide whether chunk-level rows in machine formats must carry chunk identity and whether --files may repeat a path"
result: [pending]
note: "Checked 2026-11-25: --csv, --md and --xml emit rank, score, title, path and collection with no chunk field (0 mentions of sequence or chunk id); --files prints one line per row, so a path with six matching chunks appears six times; 'vsearch' has none of these four options (exit 2). The decision is the user's."

### 4. Prohibition 19-03 P1 against the Phase 21 shadow read
test: "Review prohibition 19-03 P1 ('MUST NOT persist vector staleness as a per-document flag or issue a per-result embedding query') against src/sif/search/staleness.py:44-45,67-98"
expected: "A recorded decision that the Phase 21 shadow design (one PK lookup per result on embedded_documents) is the accepted successor of the Phase 19 batched scan"
result: [pending]
note: "Checked 2026-11-25: staleness.py:44-45,84-98 issues one indexed primary-key lookup per result on the 'embedded_documents' shadow and derives vectors_stale from it; no staleness flag is persisted. The per-result clause of P1 is literally superseded by Phase 21 (CORR-06, decisions D-09 and D-11), recorded there as a deliberate replacement of the full document_embeddings scan. The decision is the user's."

### 5. Truths 17 and 34: accept the Phase 20/21 mechanisms or require the literal behaviour
test: "Decide whether truths 17 and 34 are accepted for their guarantees (scope notes S2 and S4 below) or must hold literally"
expected: "Either record overrides for the Phase 20/21 mechanisms or ask for the Phase 19 literal behaviour back"
result: [pending]
note: "Checked 2026-11-25: truth 34's start formula holds for unscoped searches; Phase 20 commit bfc1b41c (plan 20-03) seeds the fetch window from a selectivity pre-count for collection-scoped and metadata-filtered searches and leaves the unfiltered path unchanged. Truth 17 keeps the single attach at exit, two-sided normalization and the display gate; only 'one batched read' became per-result shadow lookups (Phase 21). The decision is the user's."

## Summary

total: 5
passed: 0
issues: 2
pending: 3
skipped: 0
blocked: 0

## Gaps

<!-- YAML format for plan-phase --gaps consumption -->
- gap_id: G-19-1
  truth: "Every chunk row shows which chunk it is (path#sequence)"
  status: failed
  reason: "Tester observed: at 80 columns 0 of 12 chunk rows show '#sequence' for both 'query --per-chunk' and 'vsearch --per-chunk'"
  severity: major
  test: 1
  root_cause: "The Chunk cell is 'path#sequence' and Rich ellipsises the tail of a narrow cell, so the suffix is cut first: the column is 16 characters wide at 80 columns in 'query' and 25 in 'vsearch'. Observed from rendering at 80-260 columns; the exact build site in src/sif/cli/commands/search.py was not pinned."
  artifacts:
    - path: "src/sif/cli/commands/search.py"
      issue: "Chunk column too narrow at 80 columns, with '#sequence' at the end of the cell"
  missing:
    - "Keep the chunk sequence visible on narrow terminals (its own column, or truncation that preserves the suffix)"
  debug_session: ""
  resolved_by: ""
  resolved_at: ""
- gap_id: G-19-2
  truth: "Per the help text 'Minimum score threshold', weaker matches are removed and the best match survives"
  status: failed
  reason: "Tester observed: '--min-score 0.12' removed the rank-1 match (Score 0.1046) and kept the weaker rank-2 match (0.1212)"
  severity: major
  test: 2
  root_cause: "The displayed BM25 score is 1/(1+|bm25|) (src/sif/search/bm25.py:171, 231), which falls as the match improves, and the filter keeps rows whose displayed score is at least min_score (predicate 'm.score >= 1 - 1/min_score', bm25.py:96-97). The filter is consistent with the displayed score, but both run opposite to relevance."
  artifacts:
    - path: "src/sif/search/bm25.py"
      issue: "Score map decreases with relevance; the threshold therefore drops the strongest matches first"
    - path: "src/sif/cli/commands/search.py"
      issue: "Help text 'Minimum score threshold' promises the opposite behaviour"
  missing:
    - "Product decision: make the displayed score rise with relevance and invert the predicate, or redefine the flag and its help text. A score-map change alters user-visible scores and needs bench before/after."
  debug_session: ""
  resolved_by: ""
  resolved_at: ""
