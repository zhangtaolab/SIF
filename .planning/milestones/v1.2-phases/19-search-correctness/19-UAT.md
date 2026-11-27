---
status: complete
phase: 19-search-correctness
source: [19-VERIFICATION.md]
started: 2026-11-25T10:51:26Z
updated: 2026-11-27T10:37:01.000Z
---

## Current Test

[testing complete]

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
expected: "Chunk-level rows in machine formats carry chunk identity and --files prints each path once, in the field layout that plan 19-10 shipped under assumption A-19-10-1"
result: pass
evidence: "Plan 19-10 (commit 8cf0ec9). On an isolated index with 30 embedded chunks, 'sif search query \"zorbatic capacitor calibration\" --per-chunk -n 12' in each format. CSV: header rank,score,title,path,collection,vectors_stale,sequence; 8 chunk rows carry path#sequence with the same number in the last column, and 4 document-level rows (ranks 1, 3, 5 and 7, from the BM25 leg) carry the plain path and an empty cell. Markdown: chunk rows carry '- **Path:** …md#0' and '- **Sequence:** 0'; document-level rows have neither line. XML: chunk results carry <path>…md#0</path> and <sequence>0</sequence>; document-level results have no <sequence> element. --files and -q print 4 lines for the 12 rows, each path once. 12 checks pass"
performed_by: "agent (the orchestrator) as tester, at the operator's explicit request on 2026-11-26, on an isolated scratch index. The tester's verdict is that the shipped layout is complete and consistent, and it is recorded as confirmed as shipped; the operator has not confirmed it in their own words and can still amend it"

### 4. Prohibition 19-03 P1 against the Phase 21 shadow read
test: "Review prohibition 19-03 P1 ('MUST NOT persist vector staleness as a per-document flag or issue a per-result embedding query') against src/sif/search/staleness.py:44-45,67-98"
expected: "A recorded decision that the Phase 21 shadow design (one PK lookup per result on embedded_documents) is the accepted successor of the Phase 19 batched scan"
result: pass
evidence: "src/sif/search/staleness.py derives the signal at query time: one display-gate probe (SELECT 1 FROM embedded_documents LIMIT 1) and then one indexed primary-key lookup per result on the embedded_documents shadow; nothing is persisted (no column and no schema object is named for staleness). A SQL trace of one enrich_results call over 5 results on the isolated index shows 8 statements, every one a read: one contexts read, the gate, and 5 lookups; 0 statements touch the vector store document_embeddings; the lookup's plan is SEARCH embedded_documents USING COVERING INDEX sqlite_autoindex_embedded_documents_1 (document_id=?). Through the CLI the one document of that index that was indexed but not embedded shows vectors_stale true and the 4 embedded documents false"
performed_by: "agent (the orchestrator) as tester, at the operator's explicit request on 2026-11-26, by code review and a traced probe on an isolated scratch index. Verdict: the Phase 21 shadow design (CORR-06, decisions D-09 and D-11) is accepted as the successor of the Phase 19 batched scan. It keeps both halves of P1's intent, no persisted flag and no per-result query against the embedding store, and removes the full scan; only its letter, 'issue a per-result embedding query', no longer describes the code. This is the tester's judgment and the operator can reverse it"

### 5. Truths 17 and 34: accept the Phase 20/21 mechanisms or require the literal behaviour
test: "Decide whether truths 17 and 34 are accepted for their guarantees (scope notes S2 and S4 below) or must hold literally"
expected: "Either record overrides for the Phase 20/21 mechanisms or ask for the Phase 19 literal behaviour back"
result: pass
evidence: "Truth 34 (pagination): for sif search search, sif search query and sif search vsearch, unscoped and with -c alpha and with -c beta, page 1 (-n 5 --offset 0) followed by page 2 (-n 5 --offset 5) equals one 10-row page in the same order with no hole or duplicate; ranks are global and contiguous (6 to 10 on page 2); a second run is byte-identical; a scoped page holds only the scoped collection; 'search search --min-score 0.8755 --offset 1 -n 2' returns ranks 2 and 3 of the filtered list with every score at or above the threshold. 31 checks pass. Truth 17 (context attach): enrich_results in src/sif/search/context_attach.py is still the single composition and every search route in src/sif/search/hybrid.py returns through it exactly once; the path-context map is still read once per page; both sides are still normalized (get_context_map normalizes target_id, attach_path_contexts normalizes result.path); the display gate holds, as test 4 shows. Only the staleness half's 'one batched read' became the per-result shadow lookups of Phase 21"
performed_by: "agent (the orchestrator) as tester, at the operator's explicit request on 2026-11-26, on an isolated scratch index with two collections. Verdict: truths 17 and 34 are accepted for their guarantees. Their two clauses that Phase 20 (bfc1b41c, the scoped fetch window) and Phase 21 (the shadow read) changed literally are deliberate successor mechanisms of shipped, verified phases. Path contexts were not exercised live, because the scratch index has none; that half rests on the code. This is the tester's judgment and the operator can reverse it"

### 6. sif query --min-score 0.3 on the operator's own index
test: "On an index with embedded chunks run 'sif search query QUERY --min-score 0.3 --json' and the same without --min-score, with a query that matches documents lexically as well as semantically; compare the scores of the returned rows. Then run 'sif search vsearch QUERY --min-score 0.3'"
expected: "With and without the threshold, rows that match lexically carry a bm25_score beside their vector_score; vsearch --min-score filters on similarity exactly as before"
result: pass
evidence: "On an isolated index with 30 embedded chunks, query 'zorbatic capacitor calibration': 'sif search query --min-score 0.3 --json' is byte-identical to the same command without the threshold, 12 rows; the 4 rows that match lexically carry bm25_score 0.8765, 0.8760, 0.8758 and 0.8750 beside vector_score 0.6367, 0.6362, 0.6118 and 0.6270, and no other row carries a bm25_score; every leg score is at or above 0.3; 'sif search vsearch --min-score 0.3 --json' is byte-identical to the same command without the threshold (12 rows, similarity 0.6367 down to 0.5100, descending). 7 checks pass. Before plan 19-12 the same thresholded query returned 10 rows with no bm25_score (base commit 0744e83, test 2)"
performed_by: "agent (the orchestrator) as tester, at the operator's explicit request on 2026-11-26, on an isolated index with real embeddings, not on the operator's own index as the text asks"

### 7. Confirm that monotone-map is the operator's decision
test: "Confirm that the option recorded for the 19-11 decision checkpoint (bench/g19-2-min-score.json and the Decision line of 19-11-SUMMARY.md) is the one the operator chose"
expected: "A statement that the operator chose monotone-map, which changes every published BM25 score and the BM25 leg of sif query --min-score"
result: pass
evidence: "The operator answered the 19-11 checkpoint by writing 'monotone-map' directly to the orchestrator on 2026-11-26, after the three options and their consequences were presented; nothing was selected automatically. The answer was recorded by the plan 19-11 continuation executor in bench/g19-2-min-score.json (commit dbb82b5) and on the Decision line of 19-11-SUMMARY.md (commit 0744e83)"
performed_by: "operator, in conversation with the orchestrator; the verifier cannot read this from the tree"

### 8. Exact-threshold drop in sif search search --min-score (review item IN-09)
test: "Run 'sif search search QUERY -n 10 --json', then the same with --min-score set to the displayed score of one returned row"
expected: "The row whose score was used is kept, because the help text says 'Keep matches scoring at least this value'"
result: issue
reported: "The row whose score was used as the threshold is dropped in about half of the cases. On an isolated index of tests/fixtures/bench/corpus, over the 56 queries of tests/fixtures/bench/queries.json, 40 of the 84 matching rows disappear when --min-score equals their own displayed score (47.6%; 37 of the 56 queries have at least one such row). Through the CLI: 'sif search search \"kelpri protocol\" -c bench-fixture -n 10' returns Kelpri Protocol Notes with score 0.8942969341194331; the same command with --min-score 0.8942969341194331 returns nothing; with --min-score 0.89 it returns that row. A threshold just below a score works; the exact score does not reliably"
severity: minor
performed_by: "agent (the orchestrator) as tester, at the operator's explicit request on 2026-11-26, on an isolated BM25-only index"

### 9. What sif query --min-score means (review item IN-10)
test: "Run 'sif search query QUERY --min-score M --json' for several values of M and compare the displayed score of the returned rows with M"
expected: "Rows whose displayed score is below M are removed, as the help text 'Minimum score threshold' says"
result: issue
reported: "The displayed score is never compared with the threshold. With --min-score 0.02 the page still holds rows whose displayed score is 0.0139. The threshold is applied to each leg on its own scale: the BM25 leg keeps bm25 scores at or above M (about 0.876 here) and the vector leg keeps cosine similarities at or above M (0.51 to 0.64 here). At 0.63 the vector leg drops two documents while the BM25 leg keeps all four. At 0.876 the vector leg is empty, the two remaining rows display 0.8765 and 0.8760, which are BM25 leg scores and not the RRF values of 0.01 to 0.03 that the same command shows when both legs return rows. The help text of query still reads 'Minimum score threshold'. This predates plans 19-10 to 19-12"
severity: minor
performed_by: "agent (the orchestrator) as tester, at the operator's explicit request on 2026-11-26, on an isolated index with real embeddings"
note: "To be restated when plan 19-14 has run, because under its assumption A-19-9-1 the per-leg behaviour stays by design: run 'sif search query --help' and 'sif search vsearch --help', then 'sif search query QUERY --min-score M --json' for several values of M. Expected: the help texts say the value is a floor for each leg's own score and not for the fused score, and every returned row has each of its leg scores at or above M"

### 10. Three behaviours with no test that fails without them (validation gaps V19-26-1 to V19-26-3)
test: "Probe each behaviour directly: a document-level row in per-chunk Markdown and XML; a path that contains Rich markup characters in the per-chunk Chunk cell; the score map of BM25Searcher.search_chunks"
expected: "Each behaviour holds, and a test fails when it is broken"
result: issue
reported: "Each behaviour holds, and no test guards it. (1) In per-chunk Markdown and XML the 4 document-level rows have no Sequence line and no <sequence> element while the 8 chunk rows do (test 3). (2) A path that Rich parses as markup renders literally in the per-chunk Chunk cell: on an isolated index holding the path /notes/[/3]-review.md (a directory named [ with the file 3]-review.md) and the path /notes/[red]evil[/red].md, the 200-column per-chunk table prints both with their brackets, the first also with its #0 suffix, and exits 0; Rich itself raises MarkupError on the first and swallows the tags of the second. The tester's first probe used r[3]eview-notes (v2).md, which Rich does not parse as markup, so it proved nothing; this run replaced it on 2026-11-26. (3) BM25Searcher.search_chunks returns scores from 0.7030 downward, and 0.7030 equals |b|/(1+|b|) of the best raw bm25 value, -2.3667. The mutation runs recorded in 19-VALIDATION.md show that the test suite stays green when each of the three is broken"
severity: minor
performed_by: "agent (the orchestrator) as tester, at the operator's explicit request on 2026-11-26, on an isolated index; the mutation evidence is the validate-phase audit's"

### 11. Real-terminal readability of the per-chunk tables (19-10 T9 / UAT test 1)
expected: Every chunk row ends with its own `#sequence`, the table ends at its right border within 80 columns, and two rows that show the same short tail are still told apart by Title and Collection. A visible number that leaves two rows indistinguishable does not pass.
result: [pending]

### 12. Confirm or amend assumption A-19-10-1 for per-chunk machine formats (UAT test 3)
expected: Chunk rows carry `path#sequence` and the bare sequence; document-level rows keep the plain path and no sequence; `--files` lists each path once; default output is unchanged. You accept the shipped layout, or name the field layout you want instead.
result: [pending]

### 13. `sif search query --min-score` on the operator's own index (19-12 / UAT test 6)
expected: With and without the threshold, rows that match lexically carry `bm25_score` beside `vector_score`; the threshold keeps the stronger BM25 matches; `vsearch --min-score` filters on similarity exactly as before.
result: [pending]

### 14. Comprehension of the new `query`/`vsearch` `--min-score` help texts (19-14)
expected: The text alone makes the per-leg floor and the never-compared fused score clear.
result: [pending]

### 15. Complete the UAT record for this round
expected: Each test's result and each gap's `resolved_by`/`resolved_at` record this round's outcome; test 9 is restated as the per-leg contract; the `performed_by` caveats are confirmed or replaced by the operator's own runs.
result: [pending]

### 16. Resolve the 71 judgment-tier prohibitions at the end-of-phase checkpoint
expected: A recorded human resolution per item, or a recorded acceptance that the LLM-judge table in the verification report stands; at least the seven process-time items and the 64 judged holds are acknowledged.
result: [pending]

### 17. Re-run the validation audit so 19-VALIDATION.md can close V19-26-1 to V19-26-3
expected: The three gaps become guarded and `nyquist_compliant` is re-certified by the audit's own re-run, not by hand.
result: [pending]

### 18. Disposition the two open code-review findings (WR-01, IN-01)
expected: The changelog text is scoped so a reader of one release's notes is not given contradictory baselines, or the findings are explicitly accepted as written.
result: [pending]

## Summary

total: 18
passed: 7
issues: 3
pending: 8
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
- gap_id: G-19-8
  truth: "With --min-score equal to a row's own displayed score that row is kept, because the help text says 'Keep matches scoring at least this value'"
  status: failed
  reason: "Tester observed: on the bench-fixture index 40 of 84 matching rows are dropped when --min-score equals their own displayed score; 'kelpri protocol' returns nothing at --min-score 0.8942969341194331, the score of its best row"
  severity: minor
  test: 8
  root_cause: "The SQL predicate compares the raw bm25 value with the bound -M/(1-M) (bm25_rank_threshold and 'AND m.score <= ?' in src/sif/search/bm25.py). That bound is not the exact floating-point inverse of the displayed-score map |b|/(1+|b|): for about half of the double values it rounds to just below the row's own raw value, so the comparison is false at what the user sees as equality. Plan 19-12's second truth records this boundary as a property of the bound."
  artifacts:
    - path: src/sif/search/bm25.py
      issue: "The bound -M/(1-M) and the displayed-score map do not invert each other exactly in floating point"
    - path: src/sif/cli/commands/search.py
      issue: "The help text promises 'at least this value', which does not hold at equality"
  missing:
    - "Either compare the mapped score in SQL, abs(m.score) / (1.0 + abs(m.score)) >= ? bound with min_score (the code review's form, checked on 400,000 samples; it re-pins four SQL-text tests, the 0.8 row of the threshold table and the fourth truth of 19-05-PLAN.md a second time), or record the boundary as accepted and say so in the help text"
  debug_session: ""
  resolved_by: ""
  resolved_at: ""
- gap_id: G-19-9
  truth: "sif query --min-score removes the rows whose displayed score is below the value, as its help text 'Minimum score threshold' says"
  status: failed
  reason: "Tester observed: with --min-score 0.02 the query page still holds rows whose displayed score is 0.0139; at 0.876 the two returned rows display 0.8765 and 0.8760, which are BM25 leg scores"
  severity: minor
  test: 9
  root_cause: "HybridSearcher.search copies the caller's min_score into the fetch options of both legs (src/sif/search/hybrid.py), so the BM25 leg keeps bm25 scores at or above M and the vector leg keeps cosine similarities at or above M, on two different scales; the fused page's displayed score is an RRF value and is never compared with M. When one leg returns nothing the method returns the other leg's page, so the displayed score becomes that leg's score. Predates plans 19-10 to 19-12, which recorded it as out of scope."
  artifacts:
    - path: src/sif/search/hybrid.py
      issue: "One threshold value is a floor for two differently scaled legs and is never compared with the displayed score"
    - path: src/sif/cli/commands/search.py
      issue: "The --min-score help text of query still reads 'Minimum score threshold'"
  missing:
    - "A product decision: apply the threshold to the fused score after fusion; or keep the per-leg floor and say so in the help text; or hide the option on query. The MCP query tool shares this path"
  debug_session: ""
  resolved_by: ""
  resolved_at: ""
- gap_id: G-19-10
  truth: "Every behaviour the gap-closure plans claim has a test that fails without it"
  status: failed
  reason: "Tester observed: three behaviours hold by direct probe and none has a test that fails without it (19-VALIDATION.md, V19-26-1 to V19-26-3)"
  severity: minor
  test: 10
  root_cause: "Plan 19-10 and plan 19-12 added no test for three of their behaviours: a document-level row has no Sequence line and no <sequence> element in per-chunk Markdown and XML; a path with Rich markup characters renders literally in the per-chunk Chunk cell (the mitigation of threat T-19-24); BM25Searcher.search_chunks uses the new score map (its only test feeds -1.0, where the old and the new map agree)."
  artifacts:
    - path: tests/unit/cli/test_search.py
      issue: "No test for the document-level row in per-chunk Markdown and XML, and none for a markup-bearing path in the per-chunk Chunk cell"
    - path: tests/unit/search/test_bm25.py
      issue: "No behavioural test of the score map in search_chunks"
  missing:
    - "Three small tests and no source change. Adding them touches two test files that sit in the covered sets of Phases 19, 20 and 21, so their verifications go stale"
  debug_session: ""
  resolved_by: ""
  resolved_at: ""
