---
phase: 19-search-correctness
verified: 2026-11-27T10:33:37Z
status: human_needed
score: 114/115 must-haves verified
covered_files: [".planning/milestones/v1.2-phases/19-search-correctness/19-01-PLAN.md",".planning/milestones/v1.2-phases/19-search-correctness/19-01-SUMMARY.md",".planning/milestones/v1.2-phases/19-search-correctness/19-02-PLAN.md",".planning/milestones/v1.2-phases/19-search-correctness/19-02-SUMMARY.md",".planning/milestones/v1.2-phases/19-search-correctness/19-03-PLAN.md",".planning/milestones/v1.2-phases/19-search-correctness/19-03-SUMMARY.md",".planning/milestones/v1.2-phases/19-search-correctness/19-04-PLAN.md",".planning/milestones/v1.2-phases/19-search-correctness/19-04-SUMMARY.md",".planning/milestones/v1.2-phases/19-search-correctness/19-05-PLAN.md",".planning/milestones/v1.2-phases/19-search-correctness/19-05-SUMMARY.md",".planning/milestones/v1.2-phases/19-search-correctness/19-06-PLAN.md",".planning/milestones/v1.2-phases/19-search-correctness/19-06-SUMMARY.md",".planning/milestones/v1.2-phases/19-search-correctness/19-07-PLAN.md",".planning/milestones/v1.2-phases/19-search-correctness/19-07-SUMMARY.md",".planning/milestones/v1.2-phases/19-search-correctness/19-08-PLAN.md",".planning/milestones/v1.2-phases/19-search-correctness/19-08-SUMMARY.md",".planning/milestones/v1.2-phases/19-search-correctness/19-09-PLAN.md",".planning/milestones/v1.2-phases/19-search-correctness/19-09-SUMMARY.md",".planning/milestones/v1.2-phases/19-search-correctness/19-10-PLAN.md",".planning/milestones/v1.2-phases/19-search-correctness/19-10-SUMMARY.md",".planning/milestones/v1.2-phases/19-search-correctness/19-11-PLAN.md",".planning/milestones/v1.2-phases/19-search-correctness/19-11-SUMMARY.md",".planning/milestones/v1.2-phases/19-search-correctness/19-12-PLAN.md",".planning/milestones/v1.2-phases/19-search-correctness/19-12-SUMMARY.md",".planning/milestones/v1.2-phases/19-search-correctness/19-13-PLAN.md",".planning/milestones/v1.2-phases/19-search-correctness/19-13-SUMMARY.md",".planning/milestones/v1.2-phases/19-search-correctness/19-14-PLAN.md",".planning/milestones/v1.2-phases/19-search-correctness/19-14-SUMMARY.md",".planning/milestones/v1.2-phases/19-search-correctness/19-15-PLAN.md",".planning/milestones/v1.2-phases/19-search-correctness/19-15-SUMMARY.md",".planning/milestones/v1.2-phases/19-search-correctness/bench/b0.json",".planning/milestones/v1.2-phases/19-search-correctness/bench/b1.json",".planning/milestones/v1.2-phases/19-search-correctness/bench/d12-verdict.json",".planning/milestones/v1.2-phases/19-search-correctness/bench/g19-2-min-score.json",".planning/milestones/v1.2-phases/19-search-correctness/bench/g19-8-exact-threshold.json","docs/benchmarking.md","docs/changelog.md","docs/cli-reference.md","docs/configuration.md","docs/mcp-server.md","src/sif/cli/commands/eval.py","src/sif/cli/commands/index.py","src/sif/cli/commands/search.py","src/sif/core/models.py","src/sif/database/database.py","src/sif/database/repositories.py","src/sif/database/schema.py","src/sif/indexing/incremental.py","src/sif/indexing/parser.py","src/sif/indexing/watcher.py","src/sif/mcp/backend.py","src/sif/mcp/protocol.py","src/sif/mcp/tools.py","src/sif/search/bm25.py","src/sif/search/context_attach.py","src/sif/search/hybrid.py","src/sif/search/personal_bench.py","src/sif/search/rerank.py","src/sif/search/rrf.py","src/sif/search/staleness.py","src/sif/search/vector.py","tests/fixtures/bench/heldout_defaults.json","tests/integration/test_embed_idempotency.py","tests/integration/test_incremental_equivalence.py","tests/integration/test_search_correctness.py","tests/support/__init__.py","tests/test_docs.py","tests/unit/cli/test_eval.py","tests/unit/cli/test_index.py","tests/unit/cli/test_search.py","tests/unit/cli/test_search_exact_threshold.py","tests/unit/cli/test_search_min_score.py","tests/unit/cli/test_search_pagination.py","tests/unit/database/test_repositories.py","tests/unit/database/test_schema.py","tests/unit/database/test_schema_title_fts.py","tests/unit/indexing/test_incremental.py","tests/unit/indexing/test_parser.py","tests/unit/indexing/test_parser_checksum.py","tests/unit/indexing/test_watcher.py","tests/unit/mcp/goldens/2024-11-05.json","tests/unit/mcp/goldens/2025-03-26.json","tests/unit/mcp/goldens/2025-06-18.json","tests/unit/mcp/goldens/2025-11-25.json","tests/unit/mcp/goldens/2026-07-28.json","tests/unit/mcp/test_backend.py","tests/unit/search/test_bench_snapshot.py","tests/unit/search/test_bm25.py","tests/unit/search/test_collection_filter.py","tests/unit/search/test_context_attach.py","tests/unit/search/test_filters_sql.py","tests/unit/search/test_hybrid.py","tests/unit/search/test_personal_bench.py","tests/unit/search/test_rerank.py","tests/unit/search/test_rrf.py","tests/unit/search/test_staleness.py","tests/unit/search/test_vector.py"]
covered_digest: "v4:sha256:02932417012debac65328a38f0d3e0976d664d67b507f7adebdac2f30a48ac8d"
behavior_unverified: 0
overrides_applied: 0
insufficient_spec: 1
insufficient_spec_items:
  - truth: "19-10 T9: on a real 80-column terminal, against a live index with embedded chunks, every chunk row of both per-chunk tables shows its #sequence and no table line is cropped"
    reason: insufficient_spec
    test: "In a real 80-column terminal, on the operator's own index with embedded chunks, run `sif search query --per-chunk QUERY -n 12` and `sif search vsearch --per-chunk QUERY -n 12`, each also with `--full --line-numbers`, and say whether the rows are distinguishable from the table alone."
    expected: "Every chunk row ends with its own #sequence, the table ends at its right border, and rows can be told apart from the table alone."
    why_human: "The truth is a backstop and its own text says the look on a real terminal is confirmed by the operator in UAT. The measurable half is observed: 33 TestPerChunkSurfaces tests render through the real commands at 80 columns, the prior verifier observed a real pseudo-terminal, and 19-UAT test 1 recorded a live embedded scratch-index run by the orchestrator. The operator has not personally confirmed it, and readability is a human judgement."
re_verification:
  previous_status: human_needed
  previous_score: 85/90
  gaps_closed:
    - "UAT gap G-19-8 / UAT test 8 / review item IN-09: `--min-score` equal to a row's own displayed score now keeps that row, because the SQL predicate compares the displayed score itself (plan 19-13, commits 1ed9030, 5ad35b1, 0902b28). Reproduced live on a scratch index: the row survives at its own score and one float step below, and is dropped one float step above."
    - "UAT gap G-19-9 / UAT test 9 / review item IN-10: the `query` and `vsearch` help texts, the generated CLI reference, the MCP page and the changelog now name the score each `min_score` filters, and the 1.2.4 conversion advice is corrected in a new Unreleased entry without touching a released one (plan 19-14, commits 475ab82, a6412a0)."
    - "UAT gap G-19-10 / UAT test 10 / validation gaps V19-26-1 to V19-26-3: three tests now guard the document-level per-chunk row, the markup-bearing Chunk cell and the `search_chunks` score map, each proven non-vacuous by a mutation gate (plan 19-15, commits 0452dfb, f844c79). The verifier reproduced all three mutations."
    - "Human Verification item 4: the operator answered the 19-11 checkpoint, recorded by the operator in 19-UAT test 7 and on the Decision line of 19-11-SUMMARY.md (truths 11.6 and 12.10)."
    - "Human Verification item 5: prohibition 19-03 P1 is resolved by the recorded decision in 19-UAT test 4 that the Phase 21 shadow read is the accepted successor of the Phase 19 batched scan."
    - "Human Verification item 6: truths 17 and 34 are accepted for their guarantees by 19-UAT test 5; their two literal clauses changed by Phase 20/21 are recorded as scope notes S2 and S4."
    - "Human Verification item 7: IN-09 is resolved by plan 19-13 and independently reproduced (see above)."
    - "Human Verification item 8: IN-10 is resolved by the documented per-leg contract (assumption A-19-9-1, confirmed 2026-11-27; plan 19-14)."
    - "Human Verification item 9: V19-26-1 to V19-26-3 are guarded by plan 19-15; all three mutation gates reproduced."
  gaps_remaining: []
  regressions: []
advisory: []
prohibitions_flagged: 0
prohibition_verdicts: "71 judgment-tier prohibitions: 64 hold under this LLM judge (including 19-03 P1, resolved by 19-UAT test 4), 7 are process-time claims the tree cannot confirm or refute (19-10 P5, 19-11 P4, 19-13 P8, 19-13 P9, 19-14 P7, 19-15 P3, 19-15 P6); none flagged. No per-item human resolution is on record for the 70 beyond 19-03 P1."
human_verification:
  - test: "In a real terminal 80 columns wide, on your own index with embedded chunks and paths of 30 or more characters, run `sif search query --per-chunk QUERY -n 12` and `sif search vsearch --per-chunk QUERY -n 12`, each also with `--full --line-numbers`, and try to tell every row's document and chunk from the table alone."
    expected: "Every chunk row ends with its own `#sequence`, the table ends at its right border within 80 columns, and two rows that show the same short tail are still told apart by Title and Collection. A visible number that leaves two rows indistinguishable does not pass (19-10 T9 / UAT test 1)."
    why_human: "The truth is tagged backstop and its own text asks the operator to confirm the look on a real terminal. The automated render tests and the orchestrator's live scratch-index run cover the measurable half; they cannot see your terminal or judge readability."
  - test: "Run `sif search query --per-chunk QUERY --csv`, `--md`, `--xml` and `--files`, and the same without `--per-chunk`, on a document with several matching chunks; confirm or amend assumption A-19-10-1, which is still marked `status: pending plan review` in 19-10-PLAN.md."
    expected: "Chunk rows carry `path#sequence` and the bare sequence; document-level rows keep the plain path and no sequence; `--files` lists each path once; default output is unchanged. You accept the shipped layout, or name the field layout you want instead (UAT test 3)."
    why_human: "Whether machine formats must carry chunk identity, and in which fields, is the operator's call. The tests pin the shipped layout; the assumption is not yet recorded as confirmed."
  - test: "On your own index with embedded chunks, run `sif search query QUERY --min-score 0.3 --json` and the same without `--min-score`, with a query that matches lexically and semantically; compare the scores of the returned rows, and run `sif search vsearch QUERY --min-score 0.3` as before."
    expected: "With and without the threshold, rows that match lexically carry `bm25_score` beside `vector_score`; the threshold keeps the stronger BM25 matches; `vsearch --min-score` filters on similarity exactly as before (19-12 human check / UAT test 6)."
    why_human: "The plan's check asks for the operator's own index; the UAT run was on an isolated index built by the orchestrator. The code path is pinned by `TestHybridMinScoreLeg` and the vector test."
  - test: "Read `sif search query --help` and `sif search vsearch --help` and judge, as a reader who has not read the code, whether you can tell that a hybrid row's displayed Score (an RRF value near 0.03) is not what `--min-score` compares."
    expected: "The text alone makes the per-leg floor and the never-compared fused score clear (19-14 human check)."
    why_human: "Help-text comprehension is a judgement; the tests pin the words, not the reading."
  - test: "Complete the UAT record for this round: UAT tests 8, 9 and 10 still read `result: issue`, and gaps G-19-8, G-19-9 and G-19-10 still read `status: failed` with no `resolved_by`; test 9 also carries a note to restate it to the per-leg contract."
    expected: "Each test's result and each gap's `resolved_by`/`resolved_at` record this round's outcome; test 9 is restated as the per-leg contract; the `performed_by` caveats (orchestrator on the operator's behalf) are confirmed or replaced by the operator's own runs."
    why_human: "The orchestrator owns 19-UAT.md; a verifier must not edit it. The code outcomes are verified in this report; the human record is not yet written."
  - test: "Resolve the 71 judgment-tier prohibitions of the fifteen plans at the end-of-phase checkpoint."
    expected: "A recorded human resolution per item, or a recorded acceptance that the LLM-judge table in this report stands; at least the seven process-time items and the 64 judged holds are acknowledged."
    why_human: "Every prohibition in this phase is judgment tier. This report's table is a non-authoritative LLM verdict; only 19-03 P1 has a recorded decision (19-UAT test 4)."
  - test: "Re-run the validation audit so 19-VALIDATION.md can close V19-26-1 to V19-26-3 and update its frontmatter."
    expected: "The three gaps become guarded (the tests now exist and this verifier reproduced all three mutation gates), and `nyquist_compliant` is re-certified by the audit's own re-run, not by hand."
    why_human: "19-VALIDATION.md still reads `nyquist_compliant: false` with the three gaps open; plan 19-15 explicitly leaves their closure to that report's own re-run."
  - test: "Disposition the two open findings of this round's code review: WR-01 (the Unreleased changelog says `query --min-score` keeps its behaviour and then says the exact-score fix reaches its BM25 leg) and IN-01 (the conversion correction is overbroad for a BM25-only `query` route)."
    expected: "The changelog text is scoped so a reader of one release's notes is not given contradictory baselines, or the findings are explicitly accepted as written."
    why_human: "Both are documentation-wording calls; the code and the texts are verified, and the disposition file records them as open."
---

# Phase 19: Search Correctness Verification Report

**Phase Goal:** Search results are fresh, deduplicated, deterministically paginable, and title-aware — the trust floor that metadata filtering (20) builds on, with every ranking-contract change measured before/after on the Phase 18 instrument.
**Verified:** 2026-11-27T10:33:37Z at HEAD `b67b5dd`
**Status:** human_needed
**Re-verification:** Yes — after the second gap-closure round (plans 19-13, 19-14, 19-15)

Method. The must-haves are the five Success Criteria of `### Phase 19` in `.planning/milestones/v1.2-ROADMAP.md` and the 115 functional truths in the frontmatter of the fifteen plans (63 from plans 19-01 to 19-09, 27 from plans 19-10 to 19-12, 25 from plans 19-13 to 19-15; `UNCLASSIFIED-FLAGGED` entries are excluded). SUMMARY text was used only as a pointer to code. This verifier ran the full suite (3320 passed, 1 skipped), the five-file plan-19-13 gate (253 passed), the MCP suite (306 passed), the targeted Phase 19 sets (235 passed), the docs generators in an exported copy (byte-identical), a live CLI probe on a scratch index, an 84-row sweep reproduction, and six mutation overlays in `/tmp` copies; it read the diff of every file that changed since the previous report.

## Delta Since the Previous Report

Previous report: `de6db15`, 2026-11-26, human_needed, 85/90. Since then:

| Range | Change | Effect here |
| ----- | ------ | ----------- |
| `de6db15..54acb11` | v1.2.4 release commits (version, plugin/server metadata, installation docs, release-metadata tests) and quick-s23, which replaces exact SC1 snapshot equality with a 1 ULP relative tolerance in `tests/unit/search/test_hybrid.py` | No phase behaviour changes. The SC1 truth is still verified; its golden comparison is now tolerant by a declared mechanism. |
| `54acb11..f5c0221` | Plan 19-13: exact displayed-score predicate in `src/sif/search/bm25.py`; `bm25_rank_threshold` removed; new `tests/unit/cli/test_search_exact_threshold.py`; re-pinned `test_bm25.py`/`test_filters_sql.py`; `bench/g19-8-exact-threshold.json`; changelog Fixed entry; `19-05-PLAN.md` fourth truth amended | Closes G-19-8 / IN-09. |
| `f5c0221..091d7a4` | Plan 19-14: `query` and `vsearch` `--min-score` help texts; regenerated CLI reference rows; MCP page statements; Unreleased Changed entry; two docs tests | Closes G-19-9 / IN-10 as a documented per-leg contract. |
| `091d7a4..f8d784a` | Plan 19-15: three guards in `tests/unit/cli/test_search.py` and `tests/unit/search/test_bm25.py`; no source change | Closes G-19-10 / V19-26-1 to V19-26-3. |
| `f8d784a..b67b5dd` | Code review and disposition | 0 critical, 1 warning, 1 info; both are changelog wording. |

Non-planning files changed since the previous report: 17. The implementation diff of this round outside `.planning/` is 10 files: `docs/changelog.md`, `docs/cli-reference.md`, `docs/mcp-server.md`, `src/sif/cli/commands/search.py`, `src/sif/search/bm25.py`, `tests/test_docs.py`, `tests/unit/cli/test_search.py`, `tests/unit/cli/test_search_exact_threshold.py`, `tests/unit/search/test_bm25.py`, `tests/unit/search/test_filters_sql.py` (557 insertions, 71 deletions). `src/sif/search/hybrid.py`, `vector.py`, `rrf.py`, `rerank.py`, `context_attach.py`, `staleness.py`, everything under `src/sif/mcp`, `src/sif/indexing`, `src/sif/database` and `src/sif/core`, and the three searcher modules since the plan 19-14 base are byte-identical and their suites are green.

All seven task commits and the three plan-metadata commits the summaries name are ancestors of HEAD; the plan bases `54acb11`, `f5c0221`, `091d7a4` are recorded in `.git/gsd-plan-19-{13,14,15}-base`, and each plan's own changed-set gate reproduces (`1 1` numstat on `19-05-PLAN.md`; exactly two test files and 113 insertions for 19-15; exactly five files for 19-14's scope).

## Goal Achievement

### Roadmap Success Criteria

| # | Success Criterion | Status | Evidence at `b67b5dd` |
| --- | ----------------- | ------ | --------------------- |
| 1 | Frontmatter-only edits become searchable; parser dispatch + metadata-aware checksum in one plan and one migration; Markdown body byte-identical; YAML `---` bug fixed | ✓ VERIFIED | `models.py:19-72`, `parser.py:81,117,154-155`, `incremental.py:155-212,393,482` unchanged since the previous report; full suite green. |
| 2 | One result per document by default; dedup inside `VectorSearcher` pre-fusion; `--per-chunk` escape hatch; ranking-contract change recorded with bench before/after and goldens with rationale | ✓ VERIFIED | `vector.py:296-323` and both keyed fuses (`hybrid.py:150-156,451-455`) unchanged. `TestPerChunkSurfaces` now holds 33 tests, all green; the three new guards are mutation-gated. B0/B1 comparisons record n 100, mean 0.0, unchanged 100. |
| 3 | Deterministic pagination: CLI `--offset` and MCP offset; hybrid owns one slice; searchers return from rank 0; BM25 min_score order fixed; offset=0 reproduces the recorded contract | ✓ VERIFIED | `--offset` is `IntRange(min=0)` on all three commands (`search.py:625-630,833-838,1076-1081`); `rank=options.offset + position` (`bm25.py:202`); the displayed-score predicate sits in both branches ahead of `LIMIT ? OFFSET ?` (`bm25.py:114-117,158,180`). The new CLI test, the 84-row sweep and a live probe all pass. |
| 4 | Title-aware ranking: title-FTS migration, rewritten triggers, measured bm25() column weights, mtime index; `documents_fts_v` survives a rebuild | ✓ VERIFIED | `schema.py:451-666,769` unchanged; `TestWeightedBM25` green in the 59-test file; D-12 artifacts unchanged; the SC1 snapshot still passes under the declared 1 ULP tolerance. |
| 5 | No redundant attach work: exactly one context/staleness attach at pipeline exit | ✓ VERIFIED | `enrich_results` is called once per direct CLI exit (`search.py:730,996,998`) and once per pipeline exit (`hybrid.py:308-309,356`); `_attach_contexts` grep count under `src/sif` is 0; spy tests green in the full suite. |

**Score:** 5/5 roadmap success criteria verified.

### Observable Truths — Plans 19-01 to 19-09 (truths 1-63)

Wording and numbering are those of the previous report; the files cited here are byte-identical to the previous report unless a status note says otherwise. The full suite exercises all of these.

#### Plan 19-01 — CORR-01

| # | Truth | Status | Evidence |
| --- | ----- | ------ | -------- |
| 1 | `.yaml`/`.yml` starting with `---` parsed whole by `CodeParser` | ✓ VERIFIED | `parser.py:154-155,163-193,209`; full suite green. |
| 2 | Checksum over body + NUL + canonical full frontmatter; frontmatter or body edit changes it, key reorder does not | ✓ VERIFIED | `models.py:19-72`; `parser.py:81,117,184`. |
| 3 | Markdown body path byte-identical | ✓ VERIFIED | `parser.py:57-90`. |
| 4 | `date:` frontmatter stores and round-trips as canonical JSON | ✓ VERIFIED | `repositories.py:192,274`. |
| 5 | `IncrementalIndexer` stores `parsed.checksum` | ✓ VERIFIED | `incremental.py:482`. |
| 6 | Unknown extension falls back to `TextParser` | ✓ VERIFIED | `incremental.py:393`. |

#### Plan 19-02 — CORR-01

| # | Truth | Status | Evidence |
| --- | ----- | ------ | -------- |
| 7 | `index_meta` with per-collection convention keys; `drop_all` removes it | ✓ VERIFIED | `schema.py:302-311,811`; `repositories.py:731`. |
| 8 | One forced re-parse pass per absent or old marker | ✓ VERIFIED (scope note S1) | `incremental.py:155-212`. |
| 9 | Metadata-only edit keeps chunks and embeddings | ✓ VERIFIED | `incremental.py:437-446`. |
| 10 | Body edit deletes that document's chunks and embeddings first | ✓ VERIFIED | `incremental.py:451-458`. |
| 11 | `--force` still takes the metadata fast path for an unchanged body | ✓ VERIFIED | `incremental.py:413,437`. |
| 12 | `update_paths` never starts a migration | ✓ VERIFIED | `incremental.py:318`. |
| 13 | `reindexed_paths` holds only added and body-changed paths; the watcher embeds from it | ✓ VERIFIED | `incremental.py:68,179-190,320-329`; `watcher.py:906,924`. |
| 14 | A parse failure leaves the marker unwritten and counted | ✓ VERIFIED | `incremental.py:196-200,210`. |

#### Plan 19-03 — CORR-05

| # | Truth | Status | Evidence |
| --- | ----- | ------ | -------- |
| 15 | Searchers no longer attach contexts or staleness | ✓ VERIFIED | `_attach_contexts` grep count 0 under `src/sif`. |
| 16 | `SearchPipeline.search` enriches exactly once on every exit | ✓ VERIFIED | `hybrid.py:301-309,356,367,379,484`; spy tests green. |
| 17 | `enrich_results` composes attach then staleness; staleness is one batched or derived read | ✓ VERIFIED (scope note S2; accepted in 19-UAT test 5) | `context_attach.py:317-346`, `staleness.py:44-45,95-97`. The literal "one batched scan" is Phase 21's per-result indexed shadow lookups; 19-UAT test 5 accepts the guarantee (derived, no persisted flag, no embedding-store query) at the operator's explicit request. |
| 18 | Spy test counts one enrichment per exit | ✓ VERIFIED | Spy tests green. |
| 19 | `staleness.py` docstring names `enrich_results` | ✓ VERIFIED | `staleness.py:11-19`. |

#### Plan 19-04 — CORR-05

| # | Truth | Status | Evidence |
| --- | ----- | ------ | -------- |
| 20 | CLI `search` and `vsearch` call `enrich_results` exactly once and keep context and staleness in the output | ✓ VERIFIED | `search.py:730,996,998`; `TestSingleEnrichmentOwner` green. The line numbers moved by the help-text edit; the calls are unchanged. |
| 21 | MCP BM25 fallback enriches once; pipeline output is not enriched again | ✓ VERIFIED | `backend.py:490,501,534`. |
| 22 | MCP re-map forwards `rank`, `collection_name`, `vectors_stale` | ✓ VERIFIED | `backend.py:189-197`. |
| 23 | B0 saved run: 100 queries, bm25, zero mean delta | ✓ VERIFIED | `bench/b0.json` unchanged; the zero-threshold path is unchanged and the B0 comparison is recorded identically on both sides of 19-13. |

#### Plan 19-05 — CORR-03

| # | Truth | Status | Evidence |
| --- | ----- | ------ | -------- |
| 24 | `--offset` (`IntRange(min=0)`, default 0) on `search`, `vsearch`, `query`; past the end is an empty page | ✓ VERIFIED | `search.py:625-630,833-838,1076-1081`; CLI probe. |
| 25 | `rank = offset + position` | ✓ VERIFIED | `bm25.py:202`; `vector.py:248-251`; `hybrid.py:55-67`. |
| 26 | `limit=l offset=o` equals the `[o:o+l]` slice of one request, on BM25, vector and hybrid | ✓ VERIFIED | `TestConsistentPagination` green. |
| 27 | BM25 applies `min_score` before LIMIT/OFFSET by comparing the displayed score itself: `AND abs(m.score) / (1.0 + abs(m.score)) >= ?` bound with `min_score` as given; omitted when not above 0; 1+ returns no row (amended 2026-11-27 by plan 19-13) | ✓ VERIFIED | Current `19-05-PLAN.md` truth 4; `bm25.py:114-117,158,180,202`. Trace/parameter order tests green; live CLI probe; 84-row sweep. |
| 28 | Hybrid calls each leg at offset 0 with `limit+offset` and slices once | ✓ VERIFIED | `hybrid.py:119-176`. |
| 29 | Reranker window `max(candidate_limit, limit+offset)`; `top_k = limit+offset` | ✓ VERIFIED | `hybrid.py:417-428,463-477`. |
| 30 | Pipeline passes offset 0 to hybrid and owns the one slice | ✓ VERIFIED | `hybrid.py:417-428,482-484`. |
| 31 | MCP `query` offset validated and forwarded | ✓ VERIFIED (scope note S3) | `protocol.py:88,128,155`. |
| 32 | Offset 0, min_score 0 rerun against B0 reports zero mean delta | ✓ VERIFIED | B0 path unchanged; committed comparison records n 100, mean 0.0, unchanged 100. |

#### Plan 19-06 — CORR-02

| # | Truth | Status | Evidence |
| --- | ----- | ------ | -------- |
| 33 | Vector search returns one row per document with the best chunk's identity and `chunk_matches` | ✓ VERIFIED | `vector.py:296-323`; `TestVectorDocumentDedup` green. |
| 34 | Default fetch window `min(max(target*4,50),2048)` | ✓ VERIFIED (scope note S4; accepted in 19-UAT test 5) | `vector.py:25,187-231`. On scoped searches Phase 20 seeds the window from a selectivity pre-count (`:193-202,257-294`); 19-UAT test 5 accepts the guarantee at the operator's explicit request. |
| 35 | A document with five or more matching chunks yields ten distinct documents at limit 10 | ✓ VERIFIED | `TestChunkyDocumentDedup` green. |
| 36 | Per-chunk mode returns ungrouped chunk rows; both fuses keyed by `fuse_key_for`; BM25 rows document-keyed | ✓ VERIFIED | `rrf.py:8-28`; `hybrid.py:150-156,451-455`. |
| 37 | RRF math unchanged; merge adopts null chunk fields | ✓ VERIFIED | `rrf.py:36-47,108`. |
| 38 | `to_dict()` carries `chunk_id`, `sequence`, `chunk_matches`; goldens carry a rationale | ✓ VERIFIED | `models.py:341-343`; `rerank.py:68-70`. |
| 39 | Held-out snapshot regenerated with rationale | ✓ VERIFIED | `heldout_defaults.json` and its test unchanged; reproduction tests green. |

#### Plan 19-07 — CORR-02

| # | Truth | Status | Evidence |
| --- | ----- | ------ | -------- |
| 40 | `query` and `vsearch` accept `--per-chunk`; `search` does not | ✓ VERIFIED | `search.py:858,1141`; CLI exit codes unchanged. |
| 41 | Default output exposes `chunk_matches`; per-chunk rows display `path#sequence` and expose `chunk_id`/`sequence` | ✓ VERIFIED | `search.py:232-273,1038,1417`; `TestPerChunkSurfaces` 33/33 green, including the document-level and markup guards added by 19-15. |
| 42 | MCP `query`/`vec_search` accept and forward `per_chunk` | ✓ VERIFIED (scope note S3) | `protocol.py:97,156`. |
| 43 | MCP re-map forwards `chunk_id`, `sequence`, `chunk_matches` | ✓ VERIFIED | `backend.py:194-196`. |
| 44 | Generated docs clean; CLI reference documents `--offset` and `--per-chunk` | ✓ VERIFIED | Generators run in an exported copy: `docs/cli-reference.md` and `docs/configuration.md` byte-identical; rows at `:491,534,569,504,575` (offset/per-chunk). |
| 45 | B1 recorded after CORR-02; deltas labelled the BM25 no-drift check | ✓ VERIFIED | `bench/b1.json` unchanged; comparison records n 100, mean 0.0; `docs/benchmarking.md:206-225`. |

#### Plan 19-08 — CORR-04

| # | Truth | Status | Evidence |
| --- | ----- | ------ | -------- |
| 46 | Populated-DB migration drops vocab first, rebuilds two-column, recreates vocab and triggers | ✓ VERIFIED | `schema.py:497-630`; `TestTitleFtsMigration` green. |
| 47 | Rebuild populates exactly once; structural assertions hold | ✓ VERIFIED | `schema.py:574,586`. |
| 48 | `documents_fts_v` yields after rebuild; triggers sync; integrity ok | ✓ VERIFIED | `schema.py:529,596-599`; 14-test suite green. |
| 49 | Fresh DB creates the two-column table directly | ✓ VERIFIED | Schema tests green. |
| 50 | Chunks FTS and its triggers stay byte-identical | ✓ VERIFIED | `schema.py:555-562,632-656`. |
| 51 | `bm25(documents_fts, ?, ?)` binds weights left-to-right; 1.0/1.0 reproduces rank; min_score before LIMIT/OFFSET | ✓ VERIFIED | `bm25.py:24-25,120-121,131-134,162,184`; `TestWeightedBM25` green. |
| 52 | `SearchOptions.title_weight` override is internal only | ✓ VERIFIED | `models.py:377`; `bm25.py:121`. |
| 53 | SC1 golden and held-out snapshot carry a rationale | ✓ VERIFIED | `test_hybrid.py:797-808` plus the quick-s23 1 ULP tolerance (declared); full suite green. |
| 54 | No CJK lexical title win claimed | ✓ VERIFIED | `docs/benchmarking.md:255-257`. |

#### Plan 19-09 — CORR-04

| # | Truth | Status | Evidence |
| --- | ----- | ------ | -------- |
| 55 | `idx_documents_mtime` on fresh and migrated DBs | ✓ VERIFIED | `schema.py:769`. |
| 56 | MCP-only process runs the schema migration once at startup | ✓ VERIFIED | `backend.py:290-293`. |
| 57 | Per-leg and per-leg×split noise gates in `--compare` | ✓ VERIFIED | `personal_bench.py:471-546`; prior probe reproduced. |
| 58 | Title-weight sweep opens the index through `init_schema()` and requires a title column | ✓ VERIFIED (not re-run) | `.planning/tmp/phase19/sweep_title_weight.py` present, untracked. |
| 59 | Sweep evaluates 2.0/3.0/4.0 against B1 | ✓ VERIFIED (not re-run) | `bench/d12-verdict.json` unchanged. |
| 60 | D-12 gate applied to both held-out legs | ✓ VERIFIED | Artifact: title winner false, body delta 0.0. |
| 61 | Pinned `_TITLE_WEIGHT` is the accepted candidate or 1.0 | ✓ VERIFIED | `bm25.py:25` still 1.0; pin test green. |
| 62 | Goldens and docs reflect the pinned weight | ✓ VERIFIED | `docs/benchmarking.md:235-253`; docstrings; SC1 snapshot green under the declared tolerance. |
| 63 | Title weight is not a setting or CLI flag | ✓ VERIFIED | `title_weight` grep over `src/sif/cli`, `src/sif/config`, `docs/cli-reference.md`, `docs/configuration.md`: 0 files. |

### Observable Truths — Gap-Closure Plans 19-10 to 19-12

#### Plan 19-10 — CORR-02 (G-19-1, UAT test 3)

| # | Truth | Status | Evidence |
| --- | ----- | ------ | -------- |
| 10.1 | At 80 columns every chunk row of both per-chunk tables ends with its own `#sequence`; a document-level BM25 row keeps the bare path | ✓ VERIFIED | `TestPerChunkSurfaces` 33/33 green; the four 80-column render tests exercise the same CLI code. |
| 10.2 | `_ChunkAddress` measures at full width and shortens from the left; column floor `min(8, widest address)`; declared scope | ✓ VERIFIED | `search.py:207-273`; measurements from the prior report unchanged by this round. |
| 10.3 | At 200 columns a 49-character path renders complete | ✓ VERIFIED | `test_per_chunk_shows_the_full_path_on_a_wide_terminal` green. |
| 10.4 | Per-chunk CSV header and chunk/document-level rows | ✓ VERIFIED | `search.py:503-529`; `test_per_chunk_csv_carries_address_and_sequence` green. |
| 10.5 | Per-chunk Markdown and XML chunk rows carry the address and sequence; document-level rows get neither | ✓ VERIFIED | `search.py:532-605`; **now guarded** by `test_per_chunk_markdown_and_xml_give_a_document_level_row_no_sequence` (V19-26-1), and the formatter mutation fails it. |
| 10.6 | Without `--per-chunk`, CSV, Markdown and XML are unchanged | ✓ VERIFIED | Prior differential check (864 comparisons, 0 mismatches); the formatter code is unchanged by this round; full suite green. |
| 10.7 | `--files` and quiet path-only output list each path once; limits count chunk rows; default output unchanged | ✓ VERIFIED | `search.py:276-278,1001,1338`; `test_per_chunk_files_and_quiet_list_each_path_once` and `test_per_chunk_path_only_page_counts_chunk_rows` green. |
| 10.8 | `test_per_chunk_table_renders_path_sequence` passes unchanged; render tests were red against base | ✓ VERIFIED | Function text byte-identical to `147661b`; red derivations recorded and unchanged by 19-15 (which only inserted new tests). |
| 10.9 | On a real 80-column terminal, against a live index with embedded chunks, every chunk row shows `#sequence` and no table line is cropped | ⚠️ insufficient_spec (backstop) | Measurable half observed by the 33 tests, the prior verifier's pseudo-terminal render, and 19-UAT test 1's live scratch-index run; the truth's own text requires the operator's confirmation, which is not recorded. Human item 1. |
| 10.10 | All four layouts end at their right border within 80 cells with snippet text, Rich 14.3.3 and 15.0.0 | ✓ VERIFIED | Green under both Rich versions; prior measurements unchanged. |
| 10.11 | `docs/changelog.md` carries one per-chunk output entry under `[Unreleased]` / `Changed` | ✓ VERIFIED | The entry landed in `[1.2.4]` at release (`docs/changelog.md:44-47`); the released text is intact. |

#### Plan 19-11 — CORR-03 (G-19-2 before-evidence and decision)

| # | Truth | Status | Evidence |
| --- | ----- | ------ | -------- |
| 11.1 | The artifact records the probe rows, two threshold outcomes, B0/B1 deltas and the empty hybrid BM25 leg from the unchanged base tree | ✓ VERIFIED | `bench/g19-2-min-score.json` unchanged; prior report reproduced every value against the base searcher; file hash unchanged. |
| 11.2 | No `after` half while the plan ran; the decision is the pending marker, then the id named at the checkpoint | ✓ VERIFIED | Git: `043db46` pending marker, `dbb82b5` `monotone-map`, one-line diff. |
| 11.3 | No file outside `.planning/` changes in this plan | ✓ VERIFIED | Empty diff against the plan base. |
| 11.4 | A `checkpoint:decision` with three options, no `auto_select`, `blocking-human`, no implementation task | ✓ VERIFIED | `19-11-PLAN.md:147`; options `monotone-map`, `describe-current`, `deprecate-flag`; plan unmodified since planning. |
| 11.5 | A measurement that differs from the pins stops the plan; nothing is edited to agree | ✓ VERIFIED (as far as observable) | Stop rule and validator present; artifact before half identical across revisions; plan unmodified. |
| 11.6 | The operator's choice is recorded in the artifact and on a `Decision:` line and cannot be re-derived from the tree | ✓ VERIFIED (19-UAT test 7) | `decision: "monotone-map"` in the artifact and `Decision: monotone-map` in 19-11-SUMMARY.md; 19-UAT test 7 records the operator's answer and is `performed_by: operator`. |

#### Plan 19-12 — CORR-03 (G-19-2 implementation)

| # | Truth | Status | Evidence |
| --- | ----- | ------ | -------- |
| 12.1 | Displayed score is `|bm25|/(1+|bm25|)` through `bm25_display_score`, rising with relevance; `search_chunks` uses it | ✓ VERIFIED | `bm25.py:47-57,209,252`; `test_search_chunks_scores_use_the_display_map` now pins `search_chunks` on a real FTS5 chunk index. |
| 12.2 | `--min-score M` binds `m.score <= ?` with `-M/(1-M)`; a row at exact equality is dropped in a fraction of cases | ✓ VERIFIED (superseded clause — scope note S5) | Superseded by 19-13: the bound and the equality drop are gone; the rest (0/negative/NaN omit; 1+ returns no row) holds and is tested. 19-13 T8 records the supersession; 19-12 stays unedited. |
| 12.3 | Filter before pagination, bound parameters only, no holes, global ranks, filters compose | ✓ VERIFIED | `test_filters_sql.py` and `test_min_score_applies_before_offset_with_global_ranks` green; parameter order `[weights, query, collection, min_score, filters, limit, offset]`. |
| 12.4 | Hybrid ranking unchanged without a threshold; B0/B1 n 100, mean 0.0 | ✓ VERIFIED | `hybrid.py`/`rrf.py` unchanged; artifacts record the deltas; at min_score 0 the predicate is omitted, so the path is unchanged. |
| 12.5 | SC1 golden's two `bm25_score` values regenerated; order/RRF/vector scores and held-out snapshot unchanged; dated rationale | ✓ VERIFIED | Golden values in `test_hybrid.py`; snapshot unchanged; rationale present; full suite green. |
| 12.6 | Six tests re-pinned; the zero-threshold negative assertion names the new predicate; red runs observed | ✓ VERIFIED | `test_bm25.py` re-pins; our base-searcher mutation fails the five named behavioural tests (see spot-checks). |
| 12.7 | Help text, regenerated CLI reference, changelog, dated notes and the amended fourth truth of `19-05-PLAN.md`; that plan differs in exactly one line | ✓ VERIFIED (historical; 19-13 added its own one-line amendment) | The 19-12 entry is in the released `[1.2.4]` section; its wording, generated row and dated note are present. `19-05-PLAN.md` differs from 19-12's base by two amendments, the second recorded by 19-13 T7. |
| 12.8 | `sif query --min-score` changes in its BM25 leg only and keeps its help text; `TestHybridMinScoreLeg` pins it; MCP `query` shares the path | ✓ VERIFIED (help-text clause superseded — scope note S6) | The BM25-leg behaviour and `TestHybridMinScoreLeg` hold; the help text changed on purpose in 19-14, which records the supersession in its T9. |
| 12.9 | `sif vsearch --min-score` keeps its behaviour and help text; `vector.py` untouched | ✓ VERIFIED (help text now names vector similarity, 19-14) | `vector.py` unchanged; `test_search_applies_min_score` green; the behaviour is unchanged and 19-14 T3/T9 record the text update. |
| 12.10 | The operator's choice at the 19-11 checkpoint authorises this change | ✓ VERIFIED (19-UAT test 7) | Same record as 11.6; both records predate the first 19-12 commit. |

### Observable Truths — Second Gap-Closure Round 19-13 to 19-15

#### Plan 19-13 — CORR-03 (G-19-8 / IN-09)

| # | Truth | Status | Evidence |
| --- | ----- | ------ | -------- |
| 13.1 | `sif search search --min-score M` keeps every match whose displayed score is at least M to the last bit; a `--json` score passed back is kept with the same score and rank; MCP `lex_search` and the hybrid BM25 legs behave the same | ✓ VERIFIED | `test_the_cli_keeps_a_row_at_its_own_displayed_score` and `test_every_bench_row_survives_its_own_displayed_score` green. Live probe on a scratch bench index: `kelpri protocol` ranks 1/2 at `0.8942969341194331`/`0.8482321063105717`; at the rank-1 score the page is exactly rank 1 at that score. MCP `lex_search` and the hybrid legs call the same `BM25Searcher.search` (`backend.py:600-609,461`; `hybrid.py:121-128`). |
| 13.2 | The predicate compares the displayed score in SQL, bound with `min_score` itself, in the outer WHERE of both branches ahead of filters and `LIMIT ? OFFSET ?`; the expression is the weighted `bm25()` value; nothing is interpolated | ✓ VERIFIED | `bm25.py:114-117,142-183`: `min_score_filter` is the constant fragment, appended after collection ids and before filter params; both branches place it before `LIMIT ? OFFSET ?`. `test_min_score_binding_table` and `TestBm25ParamOrder` green. |
| 13.3 | The predicate is omitted when `min_score` is not above 0 (0, negative, NaN); 1 or more keeps no row by arithmetic; 1, 2.5 and infinity are tested | ✓ VERIFIED | `if options.min_score > 0` (`bm25.py:115`); `test_values_not_above_zero_keep_every_row` (0, -0.5, NaN) and `test_min_score_at_or_above_one_keeps_nothing` (1.0, 2.5, inf) green; live probe: NaN keeps both rows, 1 keeps none. |
| 13.4 | The SQL expression and `bm25_display_score` agree bit for bit over 100,189 finite doubles; signed zero and infinity are the only exceptions and cannot come from a matching row | ✓ VERIFIED | `_score_expression_sample()` yields 100,189 finite values (191 explicit after removing ±inf plus 100,000 seeded); `test_sql_score_expression_matches_the_display_map_bit_for_bit` green; the zero/infinity caveat is stated in the test. |
| 13.5 | Nothing else moves: displayed scores, one-ULP outcomes, fixed-threshold counts and B0/B1 deltas are identical before and after; only the count dropped at own score changes 40 → 0 | ✓ VERIFIED | `bench/g19-8-exact-threshold.json` pins both sides (heads `54acb11`/`1ed9030`). This verifier reproduced the after half on a scratch bench index: 84 rows, 84 kept at their own score, 84 kept one float step below, 84 dropped one float step above, fixed counts `84/84/84/84/70/70` exactly as the artifact. The before half is reproduced by the base-searcher mutation: five new tests fail. `bm25_display_score` is untouched in the diff; B0/B1 comparison paths are unchanged at min_score 0. |
| 13.6 | The threshold helper and its table test are gone; the tests state the contract on SQL text, real rows in both branches at two title weights, and edge values; red runs observed; the base searcher fails the behavioural cases by name | ✓ VERIFIED | `bm25_rank_threshold` grep 0 in `src/` and `tests/`; `_MIN_SCORE_PREDICATE` and `TestExactMinScore` present. Our base-searcher mutation (converted `-M/(1-M)` bound) fails exactly the two CLI tests plus `[scoped]`, `[unfiltered]` and `[weight-10]`, matching the plan's five named cases. Current five-file gate: 253 passed. |
| 13.7 | The changelog records the fix under `[Unreleased]`/`Fixed`, names 1.2.4 and the four-decimal limit; released sections are byte-identical; `19-05-PLAN.md` is amended once more, one line, keeping its 19-12 note | ✓ VERIFIED | `docs/changelog.md:33` phrase count 1; the released region from `## [1.2.4]` to EOF hashes identically at `54acb11`, `f5c0221` and HEAD; `19-05-PLAN.md` numstat `1 1`; both dated notes appear once and the predicate once. |
| 13.8 | 19-12's two records stay unedited; the `search --min-score` promise now holds exactly; 19-12's gate 2 reads 250 and this plan's gate 252 at its completion | ✓ VERIFIED | `19-12-PLAN.md` unchanged; help promise true (live probe at exact equality); at 19-15 the same gate reads 253 (19-15 adds one test), as its T6 records. |
| 13.9 | On an index of the checker's own choosing, a row survives `--min-score` equal to its `--json` score and keeps its rank | ✓ VERIFIED (backstop, directly observed) | This verifier built a scratch BM25 index from `tests/fixtures/bench/corpus` and ran the real CLI: own score kept rank 1 at the same score; one float step below kept; one float step above dropped. |

#### Plan 19-14 — CORR-03 (G-19-9 / IN-10)

| # | Truth | Status | Evidence |
| --- | ----- | ------ | -------- |
| 14.1 | `sif search query --min-score` behaves exactly as before: `HybridSearcher.search` copies `min_score` into both legs; each leg filters on its own score; the fused score is never compared; one empty leg returns its own page; the three searcher modules are byte-identical to the plan base; tests pass unchanged | ✓ VERIFIED | `git diff f5c0221..HEAD` over `hybrid.py`, `vector.py`, `bm25.py` is empty; `hybrid.py:121-166`; `vector.py:296-323`; `TestHybridMinScoreLeg` and `test_search_applies_min_score` green. |
| 14.2 | The `query` help text is the per-leg statement | ✓ VERIFIED | `search.py:1091-1100`; `sif search query --help` shows it; literal equality test green. |
| 14.3 | The `vsearch` help text names vector similarity; the `search` help is the 19-12 text | ✓ VERIFIED | `search.py:848-855` and `:640-647`; `--help` output. |
| 14.4 | Both texts are what `--help` shows and what `make docs-generate` writes; only the two `--min-score` rows change; `docs/configuration.md` byte-identical; the old wording appears nowhere in the source or MCP page | ✓ VERIFIED | Generators run in an exported copy: `docs/cli-reference.md` and `docs/configuration.md` byte-identical; `cli-reference` diff 2/2 rows; `Minimum score threshold` count 0 in `search.py` and `docs/mcp-server.md`. |
| 14.5 | `docs/mcp-server.md` names the score each MCP tool's `min_score` filters | ✓ VERIFIED | `docs/mcp-server.md:134` (query), `:188-190` (lex), `:195-197` (vec); test green. |
| 14.6 | Two tests pin the texts against the Click commands, the generated reference and the MCP page; each was red before its edit | ✓ VERIFIED | `tests/test_docs.py:442-497`; both green; our mutations to the old query text and the old MCP row each fail the corresponding test (1 failed, 22 passed). |
| 14.7 | The changelog records the unchanged behaviour and the conversion correction under Unreleased; the released entry stays as released | ✓ VERIFIED | `docs/changelog.md:24`; released region byte-identical; `value must not be converted` once. |
| 14.8 | The MCP wire is untouched: modules and goldens byte-identical; the 306 MCP tests pass; `min_score` publishes no description | ✓ VERIFIED | `git diff f5c0221..HEAD` over `src/sif/mcp` and `tests/unit/mcp/goldens` is empty; 306 passed; the golden schema is `{default:0.0, minimum:0.0, title:"Min Score", type:"number"}`, and no parameter of the seven tools carries a description. |
| 14.9 | 19-12's truth-8 clause and Task-3 gate-1 counts are superseded and stay unedited; after this plan the old wording count is 0 and `stronger match` is 3 | ✓ VERIFIED | `19-12-PLAN.md` unchanged; counts 0 and 3. |
| 14.10 | Review item R2-03 is closed in full; R2-04 and R2-01 are unchanged and open | ✓ VERIFIED | The new texts name the compared score; four-decimal display remains (R2-04); the band is still not stated (R2-01). `19-UI-REVIEW.md` remains the historical audit. |

#### Plan 19-15 — CORR-02 / CORR-03 (G-19-10 / V19-26-1 to V19-26-3)

| # | Truth | Status | Evidence |
| --- | ----- | ------ | -------- |
| 15.1 | A test renders the five-row per-chunk page with `--md` and `--xml` and asserts the document-level row keeps the plain path and no sequence, while exactly four chunk rows carry it | ✓ VERIFIED | `test_per_chunk_markdown_and_xml_give_a_document_level_row_no_sequence` green; formatter mutation to `if per_chunk:` fails it with `'- **Sequence:** ' == '- **Collection:** notes'`. |
| 15.2 | A test renders `/notes/[red]evil[/red].md` and `/notes/[/3]-review.md` in both per-chunk tables at 200 columns, asserting exit 0 and a Chunk cell of `path#0` | ✓ VERIFIED | Parametrized test green; `Text.from_markup` mutation fails both cases (the second with `MarkupError("closing tag '[/3]'...")`). |
| 15.3 | A test runs `search_chunks` on a real FTS5 chunk index with raw values about -4.72 and -0.77 and asserts each score equals `bm25_display_score` and falls with rank | ✓ VERIFIED | `_build_chunk_fts_db()` produces `[-4.716163782783036, -0.7732687035694134]`; test green; reciprocal-map mutation fails only the new test (1 failed, 1 passed). |
| 15.4 | Each test fails without the behaviour, proven by a mutation gate at execution time; the document-level test fails when the formatters give a sequence; the markup test fails under bare string and `Text.from_markup`; the score-map test fails under the earlier reciprocal map | ✓ VERIFIED | All three mutations reproduced by this verifier in throwaway copies with the exact failure modes and counts. |
| 15.5 | The UAT example name `r[3]eview-notes (v2).md` is not used; Rich does not parse it as markup | ✓ VERIFIED | Test paths are the two markup-bearing ones; the plan's Rich tag rule is correct. |
| 15.6 | No source file changes: outside `.planning/` exactly the two test files differ; `TestPerChunkSurfaces` holds 33 tests and `test_bm25.py` 59; the full suite, lint and docs tests pass; 19-13's gate reports 253 | ✓ VERIFIED | `git diff 091d7a4..HEAD` outside `.planning` is exactly the two files (113 insertions, 0 deletions); collect-only reports 92 = 33 + 59; five-file gate 253 passed; full suite 3320 passed, 1 skipped; ruff/format clean. |

**Score:** 114/115 plan truths verified: 114 VERIFIED (63 from plans 19-01 to 19-09, 26 from plans 19-10 to 19-12, 25 from plans 19-13 to 19-15), 1 insufficient_spec (10.9), 0 failed, 0 present-behavior-unverified. No truth is UNCERTAIN: the two earlier uncertainties (17, 34) are accepted by 19-UAT test 5 and recorded as scope notes S2/S4.

### Scope Notes (literal wording vs HEAD)

| Note | Truth | Clause read literally | What HEAD does | Recorded decision |
| --- | --- | --- | --- | --- |
| S1 | 8 | marker written "only when zero files failed" | written when no stored document failed | Phase's own review fix WR-01 |
| S2 | 17 | "one batched `document_embeddings` scan" | one indexed lookup per result on `embedded_documents` (Phase 21) | 19-UAT test 5 (2026-11-26), at the operator's explicit request; reversible |
| S3 | 31, 42 | "hand-written query schema" | signature-derived schema (Phase 22) | prior report's adjudication |
| S4 | 34 | start `min(max(target*4,50),2048)` | selectivity-seeded window on scoped searches (Phase 20) | 19-UAT test 5 (2026-11-26), at the operator's explicit request; reversible |
| S5 | 12.2 | bound `-M/(1-M)` with `m.score <= ?`; equivalence drops a fraction of rows | displayed-score predicate bound with `min_score`; equality kept | 19-13 T8 supersedes the boundary sentence; 19-12 unedited |
| S6 | 12.8, 12.9 | `query` keeps its "Minimum score threshold" help text; `vsearch` text unchanged | both now name the compared score | 19-14 T9 supersedes the truth-8 clause; T3/T9 record the text updates |

Truth 27 is no longer a scope note: the fourth truth of `19-05-PLAN.md` was amended twice in place (19-12, then 19-13), and the code matches the current amendment.

### Adjudications

**A. Exact `--min-score` (UAT test 8, G-19-8, IN-09) — fixed and reproduced.** On a scratch index of the committed bench corpus, `sif search search "kelpri protocol" -c bench-fixture --json` returns ranks 1 and 2 at `0.8942969341194331` and `0.8482321063105717`; with `--min-score 0.8942969341194331` the page is exactly rank 1 at the same score and rank; one float step below keeps it, one float step above drops it; `--min-score 1` returns nothing and `--min-score nan` keeps all. The full 84-row sweep reproduces 0 rows dropped at their own score and the artifact's fixed-threshold counts. The previous report's blocking boundary item is closed.

**B. Per-chunk identity (UAT tests 1 and 3, G-19-1) — built under an assumption still marked pending.** The table keeps `#sequence` at 80 columns, and the machine formats and path-only output carry the identity as assumption A-19-10-1 describes. `19-10-PLAN.md:19` still reads `status: pending plan review`; UAT test 3 was performed by the orchestrator as confirmed-as-shipped. Human items 1 and 2.

**C. `sif query --min-score` (UAT test 9, G-19-9, IN-10) — documented, not redesigned.** The operator chose the per-leg floor and a truthful description (assumption A-19-9-1, confirmed 2026-11-27; plan 19-14). The CLI help, generated reference, MCP page and changelog now say which score each leg filters and that the fused score is never compared. UAT test 9's note says it is to be restated to this contract; the record still reads `issue`. Human items 4 and 5.

**D. The three unguarded behaviours (UAT test 10, G-19-10, V19-26-1 to V19-26-3) — guarded and mutation-proven.** All three tests are green, and this verifier reproduced every mutation failure: the formatter mutation fails the document-level test, both markup mutations fail both path cases, and the reciprocal-map mutation fails only the new `search_chunks` test. The validation report still records the gaps open; its own re-run is human item 7.

**E. Review findings of this round — both are documentation wording.** WR-01 (the Unreleased Changed entry says `query --min-score` "keeps its behaviour" while the Fixed entry says the exact-score fix reaches its BM25 leg; the two statements use different baselines, 19-13 and 1.2.4) and IN-01 (the conversion correction is overbroad for `lex:`-prefixed or `bm25`-default `query` routes) are open in `19-REVIEW-DISPOSITION.md`. Neither contradicts a must-have or changes code; they are recorded as warnings, not blockers.

### Deferred Items

None.

### Advisory (New Scope, Unevidenced)

None. Every finding raised this pass is backed by a command and its output.

## Required Artifacts

`verify.artifacts` passes all 14 entries declared by the three round-2 plans (19-13 7/7, 19-14 5/5, 19-15 2/2). The earlier plans' five known exceptions are unchanged: `src/sif/mcp/handlers.py` was deleted in Phase 22 (its property verified at its successor), the three bench JSON files of the earlier plans are declared under the pre-archive prefix and exist at `.planning/milestones/v1.2-phases/…/bench/`, and one dotted export in 19-12 is a tool-matching limit while the method exists at `bm25.py:87`. No declared artifact is missing or a stub.

| Artifact | Expected | Status | Details |
| -------- | -------- | ------ | ------- |
| `src/sif/search/bm25.py` | Displayed-score predicate bound with `min_score` in both branches; threshold helper removed | ✓ VERIFIED | `bm25_display_score` at `:47-57`; predicate `:114-117`; `search_chunks` unchanged; `ty` diagnostic is in `embedder.py`, not here. |
| `tests/unit/cli/test_search_exact_threshold.py` | UAT test 8 through the real CLI and the 56-query sweep | ✓ VERIFIED | 153 lines; both tests green; red against the base-like searcher. |
| `tests/unit/search/test_bm25.py` | Re-pinned and new searcher tests, bit-for-bit SQL check | ✓ VERIFIED | 59 tests; `TestExactMinScore`; 100,189-value sample; mutation-red. |
| `tests/unit/search/test_filters_sql.py` | Parameter order with `min_score` bound as given | ✓ VERIFIED | Green; constant predicate text asserted. |
| `bench/g19-8-exact-threshold.json` | Before/after sweep, probe and B0/B1 deltas | ✓ VERIFIED | Values reproduced on the after side; before side reproduced by mutation. |
| `19-05-PLAN.md` | Fourth truth amended a second time | ✓ VERIFIED | Numstat `1 1`; both dated notes. |
| `docs/changelog.md` | Fixed entry for the exact threshold; Unreleased Changed entry and conversion correction | ✓ VERIFIED | Both entries present; released region byte-identical. |
| `src/sif/cli/commands/search.py` | `query`/`vsearch` help texts; `search` text untouched | ✓ VERIFIED | `:640-647,848-855,1091-1100`; `--help` output matches. |
| `docs/cli-reference.md` | Regenerated rows for both options | ✓ VERIFIED | Generator output byte-identical; rows `:495,573`. |
| `docs/mcp-server.md` | Query row and lex/vec sentences name the score | ✓ VERIFIED | `:134,188-197`. |
| `tests/test_docs.py` | Two tests pinning the texts | ✓ VERIFIED | `:442-497`; both mutation-red. |
| `tests/unit/cli/test_search.py` | Document-level row and markup-bearing Chunk cell guards | ✓ VERIFIED | Two new tests (three cases); mutation-red. |
| `tests/unit/search/test_bm25.py` | `search_chunks` score-map guard and builder | ✓ VERIFIED | `_build_chunk_fts_db` at `:711`; test at `:419`. |
| The 24 artifacts of the previous report unchanged (`models.py`, `parser.py`, `incremental.py`, `watcher.py`, `repositories.py`, `schema.py`, `database.py`, `vector.py`, `hybrid.py`, `rrf.py`, `context_attach.py`, `staleness.py`, `rerank.py`, `personal_bench.py`, `index.py`, `eval.py`, `protocol.py`, `tools.py`, `backend.py`, `b0.json`, `b1.json`, `d12-verdict.json`, `test_schema_title_fts.py`, `heldout_defaults.json`) | — | ✓ VERIFIED (regression) | Byte-identical to `4dbf386`; full suite green. |

## Key Link Verification

`verify.key-links` passes 4/4 (19-13), 2/2 (19-14) and 2/2 (19-15). The earlier plans' file-valued tool false positives are unchanged; each was checked at the call site in the previous report and those files are unchanged.

| From | To | Via | Status | Details |
| ---- | -- | --- | ------ | ------- |
| `src/sif/cli/commands/search.py` | `src/sif/search/bm25.py` | `search_cmd` passes `min_score` into `SearchOptions`; the searcher binds it | ✓ WIRED | `min_score=min_score`; live probe. |
| `tests/unit/cli/test_search_exact_threshold.py` | `src/sif/search/bm25.py` | reads `--json` scores and passes them back | ✓ WIRED | Green; red on the old bound. |
| `tests/unit/search/test_bm25.py` | `src/sif/search/bm25.py` | `_MIN_SCORE_PREDICATE` asserted in SQL and evaluated bit-for-bit | ✓ WIRED | Green. |
| `bench/g19-8-exact-threshold.json` | `bench/b0.json` | B0/B1 comparison deltas | ✓ WIRED | Identical on both sides. |
| `tests/test_docs.py` | `search.py` / `docs/cli-reference.md` | `_option_help` reads the Click option; the test compares it with the generated row | ✓ WIRED | Green; mutation-red. |
| `search.py` | `docs/cli-reference.md` | generator writes each option's help | ✓ WIRED | Generator idempotent. |
| `tests/unit/cli/test_search.py` | `search.py` | real per-chunk commands reach the Markdown/XML formatters and `_ChunkAddress` | ✓ WIRED | Green; mutation-red. |
| `tests/unit/search/test_bm25.py` | `bm25.py` | `search_chunks` on `_build_chunk_fts_db()` compared with `bm25_display_score` | ✓ WIRED | Green; mutation-red. |

**Wiring:** 8/8 new connections verified; the 21 links of the previous report are unchanged.

## Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
| -------- | ------------- | ------ | ------------------ | ------ |
| `src/sif/search/bm25.py` | `score` and the threshold predicate | `bm25(documents_fts, ?, ?)` in the same materialized CTE; `min_score` bound from `SearchOptions` | Yes — live CLI rows match the artifact; 84-row sweep reproduced | ✓ FLOWING |
| `src/sif/cli/commands/search.py` | `results` → table, CSV, Markdown, XML, paths | searcher rows enriched at entry | Yes — tests render real stand-in pages through the real commands; live CLI probe | ✓ FLOWING |
| `bench/g19-8-exact-threshold.json` | before and after halves | base-searcher copy and checkout through the real CLI/searcher | Yes — after half reproduced; before half reproduced by mutation | ✓ FLOWING |
| `tests/unit/search/test_bm25.py` `_build_chunk_fts_db` | raw chunk bm25 values | real in-memory FTS5 index | Yes — `[-4.716163782783036, -0.7732687035694134]` | ✓ FLOWING |

## Behavioral Spot-Checks

| Behavior | Command | Result | Status |
| -------- | ------- | ------ | ------ |
| Full suite | `python3 -m pytest -p no:cacheprovider --no-cov -q` | 3320 passed, 1 skipped in 116.60 s | ✓ PASS |
| Five-file plan-19-13 gate | `.venv/bin/python -m pytest … test_bm25.py test_search_min_score.py test_filters_sql.py test_hybrid.py test_search_exact_threshold.py` | 253 passed | ✓ PASS |
| Targeted Phase 19 set | `.venv/bin/python -m pytest … test_search_exact_threshold.py test_bm25.py test_filters_sql.py TestPerChunkSurfaces tests/test_docs.py TestHybridMinScoreLeg` | 235 passed | ✓ PASS |
| MCP suite | `python3 -m pytest … tests/unit/mcp` | 306 passed | ✓ PASS |
| Live exact-threshold probe | scratch index, `sif search search kelpri protocol … --json`, then `--min-score` at own / ±1 ULP / 1 / nan | own kept rank 1; below kept; above dropped; 1 empty; nan keeps all | ✓ PASS |
| 84-row after-half sweep | 56 queries on the scratch bench index | 84 rows; 84/84 kept at own score; 84/84 kept one ULP below; 84/84 dropped one ULP above; fixed counts 84/84/84/84/70/70 | ✓ PASS |
| Old-bound mutation | `-M/(1-M)` with `m.score <= ?` in a throwaway copy | 5 failed, 2 passed — the two CLI tests and `[scoped]`, `[unfiltered]`, `[weight-10]` | ✓ PASS |
| Formatter mutation | `if per_chunk and sequence:` → `if per_chunk:` | 1 failed — document-level row test | ✓ PASS |
| Markup mutation | Chunk cell yields `Text.from_markup(...)` | 2 failed — both path cases, second with `MarkupError` | ✓ PASS |
| `search_chunks` mutation | displayed map → reciprocal map | 1 failed, 1 passed — only the new score-map test | ✓ PASS |
| Docs-text mutations | old `query` help; old MCP row | each `1 failed, 22 passed` | ✓ PASS |
| Docs generator | both generators in an exported copy | `docs/cli-reference.md` and `docs/configuration.md` byte-identical | ✓ PASS |
| `--help` texts | all three commands | the three expected texts | ✓ PASS |
| Lint / format / types | `ruff check`, `ruff format --check`, `ty check src/sif` | ruff clean, 239 files formatted; ty 1 pre-existing diagnostic in `embedding/embedder.py:870` (outside this phase) | ✓ PASS (with note) |

## Probe Execution

Step 7c: SKIPPED (no probes). No `scripts/*/tests/probe-*.sh` exists and no PLAN or SUMMARY declares one.

## Prohibitions (must-NOT checks)

All 71 prohibitions (30 from plans 19-01 to 19-09, 16 from 19-10 to 19-12, 11 + 8 + 6 from 19-13 to 19-15) were checked against HEAD. All are judgment tier: the plans carry bare `statement` entries or `status: unresolved` with no `verification` field. This table is a non-authoritative LLM-judge verdict.

| Plan | # | Prohibition | Status | Current-code evidence |
| ---- | - | ----------- | ------ | --------------------- |
| 19-01 | 1-3 | no body-only hash; Markdown body path unaltered; no new runtime dependency | ✓ PASS | Unchanged files; dependency files untouched. |
| 19-02 | 1-3 | marker never cleared early; no re-chunk on unchanged body; no migration from drift checks | ✓ PASS | Unchanged files. |
| 19-03 | 1 | No persisted staleness flag or per-result embedding query | ✓ RESOLVED (19-UAT test 4) | The shadow read is one indexed lookup per result on `embedded_documents`; the UAT tester accepted it as the Phase 21 successor of the batched scan. |
| 19-03 | 2-3 | no loss of context or staleness markers; no SQL path prefilter | ✓ PASS | Unchanged files; one enrichment per exit. |
| 19-04 | 1-3 | no double attach on MCP; no scratch database committed; B0 recorded after CORR-01 | ✓ PASS | Unchanged; bench JSON files are the only tracked non-Markdown files under the phase directory. |
| 19-05 | 1 | No interpolation of offset, limit or min_score into SQL | ✓ PASS | Trace: all values bound. |
| 19-05 | 2 | `min_score` never applied after pagination | ✓ PASS | Predicate before `LIMIT ? OFFSET ?`; `search_chunks` keeps its post-window filter (IN-05, no production caller). |
| 19-05 | 3 | No double-applied offset | ✓ PASS | `hybrid.py` unchanged; single slice. |
| 19-06 | 1-4 | RRF math unchanged; no duplicate document rows; fetch ceiling; chunk identity kept | ✓ PASS | `rrf.py`, `vector.py`, `hybrid.py` unchanged; 3320-test suite green. |
| 19-07 | 1-3 | no per-chunk flag on document-level surfaces; chunk fields kept at re-map; generated docs not hand-edited | ✓ PASS | Exit 2 on `search --per-chunk`; `lex_search` schema unchanged; generator idempotent. |
| 19-08 | 1-4 | detect-and-rebuild; vocab dropped first; weights bound; no CJK claim | ✓ PASS | Unchanged files. |
| 19-09 | 1-4 | title weight internal; no win declared inside noise; no regression beyond the tie rule; MCP-only schema init | ✓ PASS | Unchanged files; grep 0 files. |
| 19-10 | 1 | Default output unchanged; no de-duplication outside per-chunk mode | ✓ PASS | Prior 864-comparison differential check; formatter code unchanged; tests. |
| 19-10 | 2 | No `--csv`/`--md`/`--xml`/`--files` on `vsearch`; no `--per-chunk` on `search` | ✓ PASS | CLI exit 2. |
| 19-10 | 3 | Chunk column not marked `no_wrap` | ✓ PASS | `_chunk_column` returns style and min_width only. |
| 19-10 | 4 | Generated docs not hand-edited | ✓ PASS | Generator idempotent. |
| 19-10 | 5 | Real model directory not linked, no `sif index embed`, before `cache.state: valid` | — not verifiable | Process-time; the tree cannot confirm or refute it. |
| 19-11 | 1 | No edit under `src/`, `tests/` or `docs/` | ✓ PASS | Empty diff against the plan base. |
| 19-11 | 2 | Committed bench runs not rewritten; no saved run overwritten | ✓ PASS | Unchanged. |
| 19-11 | 3 | No `auto_select`; no score-map change without the recorded choice | ✓ PASS | No `auto_select`; the source change follows both records. |
| 19-11 | 4 | Capture not run against the default database or cache | — not verifiable | Process-time. |
| 19-11 | 5 | No recorded value, pin or baseline edited to agree | ✓ PASS | Artifact before half identical across revisions; plan unmodified. |
| 19-12 | 1-2 | No interpolation; not after pagination | ✓ PASS | Trace. |
| 19-12 | 3 | vector/`vsearch`/RRF/help unchanged | ✓ PASS for vector, RRF and behaviour; the two help texts were changed on purpose by 19-14 (its T9 records the supersession) | Files unchanged; full suite green. |
| 19-12 | 4-6 | Bench files and held-out snapshot not rewritten; only the fourth truth edited; goldens regenerated not derived | ✓ PASS | Unchanged files; numstat; regeneration record. |
| 19-13 | 1-2 | no interpolation; min_score not after pagination | ✓ PASS | Bound constant fragment; predicate before LIMIT/OFFSET; `search_chunks` deferral preserved. |
| 19-13 | 3 | `bm25_display_score`, displayed scores, unfiltered order, `search.py`/`hybrid.py`/`vector.py`, RRF math and vector threshold unchanged | ✓ PASS | The diff changes only the predicate and removes the helper; those files are byte-identical in 19-13's range. |
| 19-13 | 4 | Do not bind the predicate when `min_score` is not above 0 | ✓ PASS | `if options.min_score > 0`. |
| 19-13 | 5 | Do not rewrite the bench files or held-out snapshot | ✓ PASS | Empty diff. |
| 19-13 | 6 | Only the fourth truth of `19-05-PLAN.md`; no other plan/SUMMARY edit | ✓ PASS | Numstat `1 1`; no other shipped plan/SUMMARY changed by 19-13. |
| 19-13 | 7 | Do not edit a recorded value to agree with a pin | ✓ PASS (no evidence of violation) | Artifact values reproduce. |
| 19-13 | 8-9 | No capture against default DB/cache; no embedder commands | — not verifiable | Process-time. |
| 19-13 | 10 | No released changelog entry edited | ✓ PASS | Released region byte-identical. |
| 19-13 | 11 | `test_search_min_score.py` not edited | ✓ PASS | Empty diff since `54acb11`. |
| 19-14 | 1 | No behaviour change; three searcher modules byte-identical | ✓ PASS | Diff empty; tests green. |
| 19-14 | 2 | MCP modules and goldens untouched | ✓ PASS | Diff empty; 306 tests green. |
| 19-14 | 3 | No hand-edit of generated docs | ✓ PASS | Generator idempotent. |
| 19-14 | 4 | `search --min-score` help unchanged | ✓ PASS | Its text is the 19-12 text; only the vsearch/query options changed. |
| 19-14 | 5 | Never call the vector score cosine similarity | ✓ PASS | Texts say "vector similarity". |
| 19-14 | 6 | No plan/SUMMARY edit; supersession recorded in the SUMMARY only | ✓ PASS | `19-12-PLAN.md` and all shipped records unchanged. |
| 19-14 | 7 | No embedding model loaded | — not verifiable | Process-time; no task needs it. |
| 19-14 | 8 | No released changelog entry edited | ✓ PASS | Released region byte-identical. |
| 19-15 | 1 | No source/docs/scripts/dependency change | ✓ PASS | Exactly two test files differ from its base. |
| 19-15 | 2 | Do not weaken, skip or re-flag an existing test | ✓ PASS | 113 insertions, 0 deletions; all previous tests green. |
| 19-15 | 3 | Do not build a mutant in the working tree | — not verifiable | Process-time; no mutant is present; full suite green. |
| 19-15 | 4 | Do not use the UAT example name as the markup path | ✓ PASS | Test uses the two parsed paths. |
| 19-15 | 5 | No plan/SUMMARY/audit edit | ✓ PASS | The audit is unchanged; no shipped plan or SUMMARY was edited. |
| 19-15 | 6 | No embedder commands | — not verifiable | Process-time. |

**Verdict:** 64 hold, 0 flagged, 7 not verifiable from the tree (process-time). Prohibition 19-03 P1 has a recorded resolution in 19-UAT test 4. `prohibitions_flagged: 0`.

## Requirements Coverage

| Requirement | Source plans | Description | Status | Evidence |
| ----------- | ------------ | ----------- | ------ | -------- |
| CORR-01 | 19-01, 19-02 | Frontmatter-only edits become searchable | ✓ SATISFIED | Truths 1-14; full suite. |
| CORR-02 | 19-06, 19-07, 19-10, 19-15 | One result per document; `--per-chunk` escape hatch; recorded ranking-contract change | ✓ SATISFIED | Truths 33-45, 10.1-10.11, 15.1-15.6. |
| CORR-03 | 19-05, 19-11, 19-12, 19-13, 19-14, 19-15 | Deterministic pagination; BM25 min_score order and exact threshold; truthful threshold texts | ✓ SATISFIED | Truths 24-32 (27 as amended), 11.1-12.10, 13.1-13.9, 14.1-14.10, 15.3-15.6. |
| CORR-04 | 19-08, 19-09 | Title-aware ranking | ✓ SATISFIED | Truths 46-63. |
| CORR-05 | 19-03, 19-04 | One context/staleness attach | ✓ SATISFIED | Truths 15-23; scope note S2 recorded. |

Every requirement ID named in the fifteen plans' frontmatter is one of CORR-01 to CORR-05. `.planning/milestones/v1.2-REQUIREMENTS.md` maps exactly those five to Phase 19; CORR-06 maps to Phase 21 and is correctly absent. No orphaned requirement.

## Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
| ---- | ---- | ------- | -------- | ------ |
| — | — | `TBD`, `FIXME`, `XXX`: 0 in the changed files; `TODO`, `HACK`, `PLACEHOLDER`: 0 | — | Debt-marker gate clean. |
| `19-UAT.md` | 64-183 | Record not updated after this round: tests 8/9/10 still `result: issue`; gaps G-19-8, G-19-9, G-19-10 still `status: failed` with no `resolved_by`; test 9's restatement note still pending | ⚠️ Warning | The orchestrator owns this file; the code outcomes are verified here. Human item 5. |
| `19-VALIDATION.md` | 7, 68-74, 213-215, 227 | `nyquist_compliant: false` and V19-26-1..3 still open | ⚠️ Warning | Plan 19-15 added the three guards; the audit needs its own re-run to re-certify. Human item 7. |
| `19-10-PLAN.md` | 19 | Assumption A-19-10-1 `status: pending plan review` | ⚠️ Warning | The layout shipped and is tested; the operator has not confirmed or amended the assumption. Human item 2. |
| `docs/changelog.md` | 24 | WR-01: the Changed entry says `query --min-score` "keeps its behaviour" while the Fixed entry says the exact-score fix reaches its BM25 leg; different baselines in one release's notes | ⚠️ Warning | Open in `19-REVIEW-DISPOSITION.md`; docs wording only, no code or must-have affected. |
| `docs/changelog.md` | 24 | IN-01: the conversion correction says subtract-from-1 holds for `search search` only, but a BM25-only `query` route (`lex:` prefix or `bm25` default) converts the same way | ⚠️ Warning | Open in the disposition; docs wording only. |
| `19-REVIEW-DISPOSITION.md` | 1-18 | IN-09, IN-11 and IN-12 still show `open` although this round fixes/guards them; WR-01 and IN-01 are new and open | ℹ️ Info | The disposition is a ledger; the orchestrator can refresh it. |
| `src/sif/embedding/embedder.py` | 850, 870 | `ty` diagnostic: `embed()` returns numpy scalars where `list[float]` is declared | ℹ️ Info | Pre-existing; file unchanged since `4dbf386`; outside this phase. |
| `19-05-PLAN.md` | 121 | Task text still describes the historical threshold derivation | ℹ️ Info | Historical record; the truth itself is amended. |
| `19-RESEARCH.md` | 296, 404, 535-540 | Research still states the earlier score map | ℹ️ Info | Historical research document. |

**Test quality audit.** No disabled test is linked to a requirement; the only skips in the full suite are the environmental `sqlite-vec not available` guards (1 skipped). No test writes its own expected values. Expected-value provenance is PARTIAL only for the two recorded goldens (they pin a contract; ranking quality is not proven by them); the threshold direction is proved by independent oracles (descending scores, thresholds between rows, expected document ids). Assertion strength is value-level. The three previously unguarded behaviours (V19-26-1 to V19-26-3) now each have a mutation-proven guard. No blocker comes from this audit.

**Coincidental reliance.** None flagged. The declared assumptions are named: the 80-column fit depends on Rich's table layout (measured on 14.3.3 and 15.0.0; the render tests pin the behaviour on whatever Rich a CI cell installs), and the SC1 golden tolerates one ULP of platform libm drift by a declared mechanism (quick-s23). The exact-threshold equality rests on IEEE arithmetic for negative finite doubles, which the bit-for-bit test checks on this SQLite build and the probe confirms through the CLI.

## Human Verification Required

### 1. Per-chunk tables on a real 80-column terminal (19-10 T9 / UAT test 1)

**Test:** In a real terminal 80 columns wide, on your own index with embedded chunks and 30+ character paths, run `sif search query --per-chunk QUERY -n 12` and `sif search vsearch --per-chunk QUERY -n 12`, each also with `--full --line-numbers`.
**Expected:** Every chunk row ends with its own `#sequence`; the table ends at its right border within 80 columns; rows with the same short tail are still told apart by Title and Collection; a visible number that leaves two rows indistinguishable does not pass.
**Why human:** The truth is tagged backstop and its own text asks the operator to confirm the look on a real terminal; readability is a visual judgement.

### 2. Per-chunk machine formats and assumption A-19-10-1 (19-10 / UAT test 3)

**Test:** Run `--per-chunk` with `--csv`, `--md`, `--xml` and `--files`, then without `--per-chunk`, and confirm or amend A-19-10-1.
**Expected:** Chunk rows carry `path#sequence` and the bare sequence; document-level rows keep the plain path and no sequence; `--files` lists each path once; default output is unchanged.
**Why human:** The field layout of machine formats is the operator's call; the assumption is still `pending plan review`.

### 3. `sif query --min-score` on the operator's own index (19-12 / UAT test 6)

**Test:** On your own index with embedded chunks, compare `sif search query QUERY --min-score 0.3 --json` with the same command without the threshold, on a query that matches lexically and semantically; then run `sif search vsearch QUERY --min-score 0.3`.
**Expected:** Lexical rows carry `bm25_score` beside `vector_score`; the threshold keeps the stronger BM25 matches; `vsearch` filters on similarity as before.
**Why human:** The plan asks for the operator's own index; the UAT run was on an isolated index built by the orchestrator.

### 4. Read the new help texts (19-14)

**Test:** Read `sif search query --help` and `sif search vsearch --help` and judge whether the text alone makes clear that each leg is filtered on its own score and that a hybrid row's displayed Score is never compared.
**Expected:** A reader who has not read the code can tell.
**Why human:** Help-text comprehension is a judgement; the tests pin the words.

### 5. Complete the UAT record for this round

**Test:** Update `19-UAT.md`: tests 8, 9 and 10 still read `result: issue`; gaps G-19-8, G-19-9 and G-19-10 still read `status: failed`; test 9 carries a note to restate it to the per-leg contract.
**Expected:** Each result and each gap's `resolved_by`/`resolved_at` records this round; test 9 is restated; the `performed_by` caveats are confirmed or replaced by the operator's own runs.
**Why human:** The orchestrator owns 19-UAT.md; the verifier must not edit it.

### 6. Resolve the judgment-tier prohibitions

**Test:** At the end-of-phase checkpoint, resolve the 71 judgment-tier prohibitions of the fifteen plans.
**Expected:** A recorded resolution per item, or an explicit acceptance of this report's LLM-judge table; at least the seven process-time items and the 64 judged holds are acknowledged.
**Why human:** Only 19-03 P1 has a recorded decision; the table is non-authoritative.

### 7. Re-run the validation audit

**Test:** Re-run the validation audit so `19-VALIDATION.md` can close V19-26-1 to V19-26-3 and update `nyquist_compliant`.
**Expected:** The three gaps become guarded (the tests exist and all three mutation gates reproduced) and the report is re-certified by its own re-run.
**Why human:** Plan 19-15 leaves the closure to that report's own re-run, not a hand edit.

### 8. Disposition the two open review findings

**Test:** Decide on WR-01 and IN-01 in `docs/changelog.md:24`.
**Expected:** The changelog text is scoped so one release's notes do not give contradictory baselines, or the findings are accepted as written.
**Why human:** Documentation-wording calls; the disposition records them as open.

## Gaps Summary

No must-have truth failed and no declared artifact is missing, a stub or unwired. The second gap-closure round does what it claims: the exact `--min-score` predicate compares the displayed score in SQL and is bound with the user's value (live-probed and mutation-proven); the `query`/`vsearch` help texts, generated reference, MCP page and changelog now name the score each threshold filters; and the three validation gaps each have a test that fails under its mutation. The phase goal is achieved in code: results are fresh, deduplicated, deterministically paginable and title-aware, with the score-map and exact-threshold changes measured before/after (B0/B1 plus the two evidence artifacts).

The phase is `human_needed`, not `passed`, for three reasons that are human records rather than code gaps: the operator has not personally confirmed the 80-column look or the machine-format assumption; the UAT and validation records have not been updated to this round; and the judgment-tier prohibitions need an end-of-phase resolution. The two open review findings are documentation wording and are warnings.

---

_Verified: 2026-11-27T10:33:37Z_
_Verifier: Claude (gsd-verifier)_
