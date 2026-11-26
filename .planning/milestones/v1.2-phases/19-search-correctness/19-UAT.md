---
status: diagnosed
phase: 19-search-correctness
source: [19-VERIFICATION.md]
started: 2026-11-25T10:51:26Z
updated: 2026-11-26T05:45:00Z
---

## Current Test

number: 3
name: "Chunk identity in per-chunk CSV, Markdown, XML and --files: confirm or amend the field layout shipped under assumption A-19-10-1"
expected: |
  A recorded confirmation of the field layout of plan 19-10, or an amendment naming another layout
awaiting: user decision

## Tests

### 1. Per-chunk table shows chunk identity at 80 columns
test: "In an 80-column terminal run 'sif search query --per-chunk QUERY' and 'sif search vsearch --per-chunk QUERY' on a corpus whose paths are 30+ characters"
expected: Every chunk row shows which chunk it is (path#sequence)
result: pass
evidence: "Plan 19-10 (commits 4e258cf, 5e83d6d) closes gap G-19-1. On an isolated scratch index with 26 chunks embedded and paths 95-96 characters, rendered in an 80-column pseudo-terminal: vsearch 12 of 12 and hybrid query 10 of 10 chunk rows end with their own #sequence (the other 2 hybrid rows are document-level rows from the BM25 leg and show the plain path); all four layouts (query and vsearch, each plain and with --full --line-numbers) have a maximum line width of 80 display cells and every table line ends with its right border. The 30 tests of tests/unit/cli/test_search.py::TestPerChunkSurfaces pass, and the verifier re-rendered the tables under Rich 14.3.3 and Rich 15.0.0 and in a real pseudo-terminal"
performed_by: "agent (the orchestrator), on an isolated scratch index, approved on the operator's behalf under auto mode on 2026-11-26; recorded in 19-10-SUMMARY.md. The operator has not run it personally"

### 2. --min-score keeps the best BM25 matches
test: "Run 'sif search search \"Saltiv Protocol Notes\" -n 10' and then with --min-score 0.12 and --min-score 0.23 on the bench-fixture index"
expected: "Per the help text, weaker matches are removed and the best match survives"
result: pass
evidence: "Plan 19-12 (commits 37b6315, d08f93c, 38f4551), after the operator's decision monotone-map recorded by plan 19-11, closes gap G-19-2. On the bench-fixture index the best match now shows the highest score (rank 1 'Saltiv Protocol Notes' 0.8943, rank 2 'Qelron Protocol Notes' 0.8473) and --min-score 0.12 and 0.23 both keep the two matches, where before 0.12 removed the best match and 0.23 returned nothing (bench/g19-2-min-score.json). On an isolated index with real embeddings, the base commit 0744e83 against the committed d5382ae: 'sif search search --min-score 0.12' keeps 3 of 3 rows where the base kept the 2 weaker ones; --min-score 0.85 keeps the best match alone and 0.89 keeps nothing; 'sif search query --min-score 0.3' returns JSON byte-identical to the unthresholded page where the base returned 10 rows with no bm25_score; 'sif search vsearch' is byte-identical across the change. 19 programmatic comparisons pass. Ranking without a threshold is unchanged (B0 and B1 comparisons: n 100, mean 0.0)"
performed_by: "agent (the orchestrator), on isolated indexes, on the operator's behalf on 2026-11-26; the bench-fixture half was captured by the plan 19-12 executor and re-checked by the orchestrator and the verifier. The operator has not run it personally"

### 3. Chunk identity in per-chunk CSV, Markdown, XML and --files
test: "Run 'sif search query --per-chunk QUERY --csv', '--md', '--xml' and '--files' on a document with several matching chunks"
expected: "Decide whether chunk-level rows in machine formats must carry chunk identity and whether --files may repeat a path"
result: [pending]
note: "Checked 2026-11-26: implemented in plan 19-10 (commit 8cf0ec9) under assumption A-19-10-1, which the operator has not confirmed in so many words. Chunk rows carry path#sequence in CSV, Markdown and XML and a bare sequence field; document-level rows keep the plain path and an empty sequence; --files and -q print each path once. The orchestrator confirmed that output on an isolated index (human check 2 of plan 19-10, recorded in 19-10-SUMMARY.md). The field layout is still the operator's to confirm or amend; another layout re-plans the machine-format and path-only part of plan 19-10 Task 2."

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

### 6. sif query --min-score 0.3 on the operator's own index
test: "On an index with embedded chunks run 'sif search query QUERY --min-score 0.3 --json' and the same without --min-score, with a query that matches documents lexically as well as semantically; compare the scores of the returned rows. Then run 'sif search vsearch QUERY --min-score 0.3'"
expected: "With and without the threshold, rows that match lexically carry a bm25_score beside their vector_score; vsearch --min-score filters on similarity exactly as before"
result: [pending]
note: "The human check of plan 19-12 Task 3. The orchestrator ran it on 2026-11-26 on an isolated index with real embeddings, not on the operator's own index as the text asks, and approved it on the operator's behalf; the observations are in 19-12-SUMMARY.md. Running it on the operator's own index is a read-only search if --no-refresh is passed"

### 7. Confirm that monotone-map is the operator's decision
test: "Confirm that the option recorded for the 19-11 decision checkpoint (bench/g19-2-min-score.json and the Decision line of 19-11-SUMMARY.md) is the one the operator chose"
expected: "A statement that the operator chose monotone-map, which changes every published BM25 score and the BM25 leg of sif query --min-score"
result: pass
evidence: "The operator answered the 19-11 checkpoint by writing 'monotone-map' directly to the orchestrator on 2026-11-26, after the three options and their consequences were presented; nothing was selected automatically. The answer was recorded by the plan 19-11 continuation executor in bench/g19-2-min-score.json (commit dbb82b5) and on the Decision line of 19-11-SUMMARY.md (commit 0744e83)"
performed_by: "operator, in conversation with the orchestrator; the verifier cannot read this from the tree"

### 8. Exact-threshold drop in sif search search --min-score (review item IN-09)
test: "Decide whether 'Keep matches scoring at least this value' must hold exactly: with --min-score equal to a row's own displayed score, that row is dropped in about 41% of cases (251 of 617 real bench rows, measured by the verifier; 12 of 60 through the real CLI in the code review)"
expected: "Either a follow-up plan that makes the predicate exact (the reviewer's form: abs(m.score) / (1.0 + abs(m.score)) >= ?, bound with min_score) or a recorded acceptance of the boundary"
result: [pending]
note: "Plan 19-12's second truth records the floating-point boundary as a property of the bound -M/(1-M). An exact predicate re-pins four SQL-text tests and the 0.8 row of the threshold table, and amends the fourth truth of 19-05-PLAN.md a second time"

### 9. What sif query --min-score means (review item IN-10)
test: "Decide what 'sif query --min-score' compares: today it filters the BM25 leg and the vector leg each on its own scale and never the displayed score, which is an RRF value around 0.03"
expected: "A product decision recorded before the Phase 22 parity work"
result: [pending]
note: "Predates the three gap-closure plans; plan 19-12 recorded it as out of scope. The help text of query and vsearch still reads 'Minimum score threshold'"

### 10. Three behaviours with no test that fails without them (validation gaps V19-26-1 to V19-26-3)
test: "Decide whether to add the three tests named in 19-VALIDATION.md: a document-level row has no sequence in per-chunk Markdown and XML; a markup-bearing path renders literally in the per-chunk Chunk cell; search_chunks uses the new score map"
expected: "Either the tests are added and the validation is re-run, or the gaps are recorded as manual-only"
result: [pending]
note: "Each behaviour is right today by direct probe. The gate was put to the operator on 2026-11-26 and not answered, so no test was added. Adding them touches tests/unit/cli/test_search.py and tests/unit/search/test_bm25.py, which re-stales the verifications of Phases 19, 20 and 21"

## Summary

total: 10
passed: 3
issues: 0
pending: 7
skipped: 0
blocked: 0

## Gaps

<!-- YAML format for plan-phase --gaps consumption -->
- gap_id: G-19-1
  truth: "Every chunk row shows which chunk it is (path#sequence)"
  status: resolved
  reason: "Tester observed: at 80 columns 0 of 12 chunk rows show '#sequence' for both 'query --per-chunk' and 'vsearch --per-chunk'"
  severity: major
  test: 1
  root_cause: "The Chunk cell is 'path#sequence' and Rich ellipsises the tail of a narrow cell, so the suffix is cut first: the column is 16 characters wide at 80 columns in 'query' and 25 in 'vsearch'. Pinned by plan 19-10 in src/sif/cli/commands/search.py (_fit_head, _chunk_column, _ChunkAddress)."
  artifacts:
    - path: src/sif/cli/commands/search.py
      issue: "Chunk column too narrow at 80 columns, with '#sequence' at the end of the cell"
  missing:
    - "Keep the chunk sequence visible on narrow terminals (its own column, or truncation that preserves the suffix)"
  debug_session: ""
  resolved_by: "19-10 (commits 4e258cf, 5e83d6d, 8cf0ec9)"
  resolved_at: "2026-11-26"
- gap_id: G-19-2
  truth: "Per the help text 'Minimum score threshold', weaker matches are removed and the best match survives"
  status: resolved
  reason: "Tester observed: '--min-score 0.12' removed the rank-1 match (Score 0.1046) and kept the weaker rank-2 match (0.1212)"
  severity: major
  test: 2
  root_cause: "The displayed BM25 score was 1/(1+|bm25|), which fell as the match improved, and the filter kept rows whose displayed score was at least min_score. Replaced by plan 19-12, after the operator's decision monotone-map: the score is |bm25|/(1+|bm25|) and the predicate is an upper bound m.score <= ? bound -M/(1-M)."
  artifacts:
    - path: src/sif/search/bm25.py
      issue: "Score map now rises with relevance; the threshold keeps the strongest matches"
    - path: src/sif/cli/commands/search.py
      issue: "Help text of search --min-score now states the direction"
  missing: []
  debug_session: ""
  resolved_by: "19-11 and 19-12 (commits 043db46 to 38f4551)"
  resolved_at: "2026-11-26"
