---
phase: 19-search-correctness
verified: 2026-11-26T05:36:00Z
status: human_needed
score: 85/90 must-haves verified
covered_files: [".planning/milestones/v1.2-phases/19-search-correctness/19-01-PLAN.md",".planning/milestones/v1.2-phases/19-search-correctness/19-01-SUMMARY.md",".planning/milestones/v1.2-phases/19-search-correctness/19-02-PLAN.md",".planning/milestones/v1.2-phases/19-search-correctness/19-02-SUMMARY.md",".planning/milestones/v1.2-phases/19-search-correctness/19-03-PLAN.md",".planning/milestones/v1.2-phases/19-search-correctness/19-03-SUMMARY.md",".planning/milestones/v1.2-phases/19-search-correctness/19-04-PLAN.md",".planning/milestones/v1.2-phases/19-search-correctness/19-04-SUMMARY.md",".planning/milestones/v1.2-phases/19-search-correctness/19-05-PLAN.md",".planning/milestones/v1.2-phases/19-search-correctness/19-05-SUMMARY.md",".planning/milestones/v1.2-phases/19-search-correctness/19-06-PLAN.md",".planning/milestones/v1.2-phases/19-search-correctness/19-06-SUMMARY.md",".planning/milestones/v1.2-phases/19-search-correctness/19-07-PLAN.md",".planning/milestones/v1.2-phases/19-search-correctness/19-07-SUMMARY.md",".planning/milestones/v1.2-phases/19-search-correctness/19-08-PLAN.md",".planning/milestones/v1.2-phases/19-search-correctness/19-08-SUMMARY.md",".planning/milestones/v1.2-phases/19-search-correctness/19-09-PLAN.md",".planning/milestones/v1.2-phases/19-search-correctness/19-09-SUMMARY.md",".planning/milestones/v1.2-phases/19-search-correctness/19-10-PLAN.md",".planning/milestones/v1.2-phases/19-search-correctness/19-10-SUMMARY.md",".planning/milestones/v1.2-phases/19-search-correctness/19-11-PLAN.md",".planning/milestones/v1.2-phases/19-search-correctness/19-11-SUMMARY.md",".planning/milestones/v1.2-phases/19-search-correctness/19-12-PLAN.md",".planning/milestones/v1.2-phases/19-search-correctness/19-12-SUMMARY.md",".planning/milestones/v1.2-phases/19-search-correctness/bench/b0.json",".planning/milestones/v1.2-phases/19-search-correctness/bench/b1.json",".planning/milestones/v1.2-phases/19-search-correctness/bench/d12-verdict.json",".planning/milestones/v1.2-phases/19-search-correctness/bench/g19-2-min-score.json","docs/benchmarking.md","docs/changelog.md","docs/cli-reference.md","src/sif/cli/commands/eval.py","src/sif/cli/commands/index.py","src/sif/cli/commands/search.py","src/sif/core/models.py","src/sif/database/database.py","src/sif/database/repositories.py","src/sif/database/schema.py","src/sif/indexing/incremental.py","src/sif/indexing/parser.py","src/sif/indexing/watcher.py","src/sif/mcp/backend.py","src/sif/mcp/protocol.py","src/sif/mcp/tools.py","src/sif/search/bm25.py","src/sif/search/context_attach.py","src/sif/search/hybrid.py","src/sif/search/personal_bench.py","src/sif/search/rerank.py","src/sif/search/rrf.py","src/sif/search/staleness.py","src/sif/search/vector.py","tests/fixtures/bench/heldout_defaults.json","tests/integration/test_embed_idempotency.py","tests/integration/test_incremental_equivalence.py","tests/integration/test_search_correctness.py","tests/support/__init__.py","tests/unit/cli/test_eval.py","tests/unit/cli/test_index.py","tests/unit/cli/test_search.py","tests/unit/cli/test_search_min_score.py","tests/unit/cli/test_search_pagination.py","tests/unit/database/test_repositories.py","tests/unit/database/test_schema.py","tests/unit/database/test_schema_title_fts.py","tests/unit/indexing/test_incremental.py","tests/unit/indexing/test_parser.py","tests/unit/indexing/test_parser_checksum.py","tests/unit/indexing/test_watcher.py","tests/unit/mcp/test_backend.py","tests/unit/search/test_bench_snapshot.py","tests/unit/search/test_bm25.py","tests/unit/search/test_collection_filter.py","tests/unit/search/test_context_attach.py","tests/unit/search/test_filters_sql.py","tests/unit/search/test_hybrid.py","tests/unit/search/test_personal_bench.py","tests/unit/search/test_rerank.py","tests/unit/search/test_rrf.py","tests/unit/search/test_staleness.py","tests/unit/search/test_vector.py"]
covered_digest: "v4:sha256:313a28a20482758b16477ecd1ba522e58e4940d6a05eeb7d186ade209d34d110"
behavior_unverified: 0
overrides_applied: 0
prohibitions_flagged: 1
prohibition_verdicts: "43/46 hold, 1 flagged (19-03 P1, superseded in letter by Phase 21), 2 not verifiable from the tree (19-10 P5 and 19-11 P4, process-time); all judgment tier, LLM judge, non-authoritative; no human resolution on record for any of the 46"
insufficient_spec: 3
insufficient_spec_items:
  - truth: "19-10 T9: on a real 80-column terminal, against a live index with embedded chunks, every chunk row of both per-chunk tables shows its #sequence and no table line is cropped"
    reason: insufficient_spec
    test: "In a real 80-column terminal, on the operator's own embedded index, run both per-chunk commands as the harvested human check describes"
    expected: "Every chunk row ends with its own #sequence, the table ends at its right border, and rows can be told apart from the table alone"
    why_human: "Tagged backstop by the planner: the look on a real terminal is confirmed by the operator in UAT. The tests and this verifier's pseudo-terminal render cover the measurable half with rows fed to the commands; the operator's embedded index and the readability judgement were not observed by this verifier."
  - truth: "19-11 T6: the operator's choice is recorded in the evidence artifact and on the Decision line of the 19-11 SUMMARY and cannot be re-derived from the tree"
    reason: insufficient_spec
    test: "Confirm that monotone-map is the operator's own answer to the 19-11 checkpoint"
    expected: "The operator states that the choice is theirs, or names another option"
    why_human: "Both records exist and agree (observed). Who gave the answer at a blocking-human checkpoint is attested only by the dispatch statements recorded in the SUMMARY, which a verifier reading the tree cannot confirm."
  - truth: "19-12 T10: the operator's choice at the 19-11 checkpoint is what authorises the change to a published output contract"
    reason: insufficient_spec
    test: "Confirm that the monotone-map decision covers the change to every published BM25 score and to the BM25 leg of sif query --min-score"
    expected: "The operator confirms the scope stated at the checkpoint, including the query --min-score change"
    why_human: "Same evidence gap as 19-11 T6: the tree carries the records, not the decision's provenance."
re_verification:
  previous_status: human_needed
  previous_score: 61/63
  gaps_closed:
    - "UAT gap G-19-1 and Human Verification item 1, automated half: every chunk row of both per-chunk tables shows its path#sequence at 80 columns and each table ends at its right border (plan 19-10, commits 4e258cf, 8cf0ec9, 5e83d6d). The visual half is still the operator's (item 1)."
    - "UAT gap G-19-2 and Human Verification item 2, automated half: sif search search --min-score keeps the strongest BM25 matches and the BM25 leg of sif query --min-score keeps its matches (plans 19-11 and 19-12, commits 043db46 to 38f4551). Whether the change is authorised is the operator's to confirm (item 4)."
    - "Human Verification item 3: chunk identity is carried in per-chunk CSV, Markdown, XML and path-only output under assumption A-19-10-1 (plan 19-10, commit 8cf0ec9). The assumption itself is still the operator's to confirm or amend (item 2)."
  gaps_remaining: []
  regressions: []
advisory: []
human_verification:
  - test: "In a real terminal that is 80 columns wide, on an index with embedded chunks whose paths are 30 or more characters, run `sif search query --per-chunk QUERY -n 12` and then `sif search vsearch --per-chunk QUERY -n 12` with a query that matches several chunks of each of several documents, each also with `--full --line-numbers`."
    expected: "On both tables you can tell the rows apart, which is what UAT test 1 is about: for each row you can say which document it comes from and which chunk of that document it is, using the table alone. The Chunk cell ends with a number sign followed by that row's sequence, and rows of one document differ by that number. The number alone does not always name the document: at 80 columns the hybrid table gives the Chunk column 15 cells, so different documents can show the same file-name tail, such as `…col-notes.md`, and the Title and Collection columns must still tell them apart. The table ends at its right border inside the terminal in every render, also with the Content column; nothing is cut off on the right, and the other columns (rank, score, title, collection) are still visible. A visible number that leaves two rows indistinguishable does not pass this check."
    why_human: "Whether rows stay recognisable at the canonical width on a real terminal is a visual judgement. The automated tests force the same width through the same CLI code and pin that each row shows its own sequence and that the table fits, but they cannot see the terminal or say whether the result is readable, and the UAT tester observed the defect only on a live render."
  - test: "Run `sif search query --per-chunk QUERY --csv`, the same with `--md`, with `--xml` and with `--files`, on a document with several matching chunks; then the same without `--per-chunk`."
    expected: "The CSV header ends with a `sequence` column and a chunk row's path is the path followed by a number sign and the sequence; Markdown and XML chunk rows carry the same address and the bare sequence; a document-level row has the plain path and no sequence. `--files` lists each path once for that page. Without `--per-chunk` the three formats and `--files` look exactly as before, including a page that lists one document twice because it is indexed in two collections. This is UAT test 3, the behaviour assumption A-19-10-1 describes; confirm or amend that assumption here."
    why_human: "UAT test 3 is recorded as a decision row, not a failed test: whether machine formats must carry chunk identity, and in which fields, is the operator's call. The plan implements the assumed behaviour and can be amended if the operator wants another field layout."
  - test: "On an index with embedded chunks run `sif search query QUERY --min-score 0.3 --json` and the same without `--min-score`, with a query that matches documents lexically as well as semantically; compare the `scores` of the returned rows. Then run `sif search vsearch QUERY --min-score 0.3` as before."
    expected: "Without the threshold and with it, rows that match lexically carry a `bm25_score` beside their `vector_score`: the threshold keeps the stronger BM25 matches in the page. Before this plan the same thresholded command returned rows with no `bm25_score` at all, because its BM25 leg had been emptied. `vsearch --min-score` filters on similarity exactly as before."
    why_human: "The evidence artifact and the unit tests read the BM25 leg through the searcher; whether the real `sif query` output reads that way on the operator's own index is what this check confirms."
  - test: "Confirm that monotone-map is the operator's own decision at the 19-11 checkpoint, with the scope stated there"
    expected: "The operator confirms the choice and its scope, or names another option for re-planning"
    why_human: "Two backstop truths (19-11 T6, 19-12 T10) say the authorisation cannot be re-derived from the tree. Both records exist and agree; who answered the blocking-human checkpoint is not observable here."
  - test: "Review prohibition 19-03 P1 ('MUST NOT persist vector staleness as a per-document flag or issue a per-result embedding query') against src/sif/search/staleness.py:44-45,67-98"
    expected: "A recorded decision that the Phase 21 shadow read (one PK lookup per result on embedded_documents) is the accepted successor of the Phase 19 batched scan"
    why_human: "Judgment-tier prohibition with no human resolution on record (UAT test 4 pending); its letter no longer describes HEAD while its intent holds. The file is unchanged since the previous report."
  - test: "Decide whether truths 17 and 34 are accepted for their guarantees (scope notes S2 and S4) or must hold literally"
    expected: "Either record overrides for the Phase 20/21 mechanisms or ask for the Phase 19 literal behaviour back"
    why_human: "Two clauses are literally false on paths a later roadmap phase changed. The verifier cannot accept a deviation on the developer's behalf. No decision since the previous report (UAT test 5 pending)."
  - test: "Decide whether --min-score must keep a row whose displayed score equals the threshold to the last bit (review item IN-09)"
    expected: "Either accept the boundary that plan 19-12 truth 2 records, or ask for an exact threshold"
    why_human: "The plan records the boundary as a property, not as an operator decision; whether it is acceptable for scripts that copy a score from JSON output is a product call. Reproduced here through the real CLI."
  - test: "Decide what sif query --min-score means for the displayed score of a hybrid row (review item IN-10)"
    expected: "A recorded contract for the flag and its help text"
    why_human: "The flag filters each leg on its own scale, while a hybrid row's displayed score is an RRF value near 0.01 to 0.03, so rows shown with a score below the threshold survive it. Predates these plans; plan 19-12 kept the help text on purpose. A product decision."
  - test: "Decide whether the three unguarded behaviours named in 19-VALIDATION.md (V19-26-1, V19-26-2, V19-26-3) get a test before the phase closes"
    expected: "Three tests added, or a recorded acceptance of nyquist_compliant: false"
    why_human: "Each behaviour is right today (checked by direct probe) and no test fails without it. The gap gate was put to the operator and not answered."
  - test: "Resolve the 46 judgment-tier prohibitions of the twelve plans at the end-of-phase checkpoint"
    expected: "A recorded human resolution; at least 19-03 P1 (flagged) and the two process-time items (19-10 P5, 19-11 P4)"
    why_human: "Every prohibition in this phase is judgment tier with no human resolution on record. The table in this report is a non-authoritative LLM verdict."
---

# Phase 19: Search Correctness Verification Report

**Phase Goal:** Search results are fresh, deduplicated, deterministically paginable, and title-aware — the trust floor that metadata filtering (20) builds on, with every ranking-contract change measured before/after on the Phase 18 instrument.
**Verified:** 2026-11-26T05:36:00Z
**Status:** human_needed
**Re-verification:** Yes — after gap closure (plans 19-10, 19-11, 19-12). Previous report verified 2026-11-25T10:38:29Z at `4dbf386` (human_needed, 61/63). This report was regenerated from the tree at HEAD `de6db15`.

Method. The must-haves are the five Success Criteria of `### Phase 19` in `.planning/milestones/v1.2-ROADMAP.md` and the 90 functional truths in the frontmatter of the twelve plans (63 from plans 19-01 to 19-09, numbered 1-63 as in the previous report, plus 27 from the three gap-closure plans). The `UNCLASSIFIED-FLAGGED` lines are probe-classification flags and are excluded. SUMMARY text was used only as a pointer to code. Every value below was taken from the tree, from git history, or from a command this verifier ran: a 2304-test Phase 19 battery, base-module overlays that reproduce the red states, an isolated BM25-only scratch index built from `tests/fixtures/bench/corpus`, renders in an 80-column pseudo-terminal, and the CLI itself. The scratch index and every overlay were removed afterwards.

## Delta Since the Previous Report (`4dbf386..de6db15`)

27 commits, of which 6 touch files outside `.planning/`. 10 implementation files changed; the other 43 implementation files of the previous covered set are byte-identical to `4dbf386` (`git diff --name-only 4dbf386 HEAD`).

| File | Change | Truths that cite it | Effect |
| ---- | ------ | -------------------- | ----- |
| `src/sif/cli/commands/search.py` | `_ChunkAddress`, `_fit_head`, `_chunk_column`, `_unique_paths`; `per_chunk` on CSV/Markdown/XML; unique paths for per-chunk `--files` and `-q`; `search --min-score` help text | 20, 24, 40, 41, 44 | Truth 41 now holds at 80 columns. Default output unchanged (differential check below). |
| `src/sif/search/bm25.py` | `bm25_display_score` (`\|bm25\|/(1+\|bm25\|)`), `bm25_rank_threshold` (`-M/(1-M)`), predicate `AND m.score <= ?` | 25, 27, 51, 61 | Truth 27 is verified against its amended wording. |
| `tests/unit/cli/test_search.py` | 23 tests added to `TestPerChunkSurfaces` | 18, 20, 41 | Strengthens; the shipped `path#sequence` test is byte-identical to the base. |
| `tests/unit/cli/test_search_min_score.py` | New: direction proof through the real CLI on a real temporary index | 19-12 T2 | — |
| `tests/unit/search/test_bm25.py` | Six tests re-pinned, six added | 51 | `TestWeightedBM25` re-pinned and green. |
| `tests/unit/search/test_filters_sql.py` | One assertion names the upper-bound predicate | 27 | — |
| `tests/unit/search/test_hybrid.py` | `TestHybridMinScoreLeg`; two SC1 `bm25_score` values; dated paragraph | 38, 53, 62 | Only the two `bm25_score` values moved in the golden. |
| `docs/cli-reference.md` | One row, regenerated | 44 | Regenerated copy byte-identical. |
| `docs/benchmarking.md` | Score-direction note; SC1 values at line 225 | 45, 53, 62 | — |
| `docs/changelog.md` | Two entries under `[Unreleased]` / `Changed` | 19-10 T11, 19-12 T7 | — |

Planning files: `19-05-PLAN.md` differs in exactly one line (the fourth truth, amended by plan 19-12; `git diff --numstat` is `1 1`); `bench/g19-2-min-score.json` is new; plans and summaries 19-10 to 19-12 are new. No other plan or summary changed. `bench/b0.json`, `bench/b1.json`, `bench/d12-verdict.json`, `tests/fixtures/bench/heldout_defaults.json` and `tests/unit/search/test_bench_snapshot.py` are unchanged. `src/sif/search/vector.py`, `hybrid.py`, `rrf.py`, `rerank.py`, `context_attach.py`, `staleness.py`, and everything under `src/sif/mcp`, `src/sif/indexing`, `src/sif/database` and `src/sif/core` are unchanged.

All 14 commits the summaries name are ancestors of HEAD (`verify.commits`: 14 valid, 0 invalid). The three plan files were committed once (`4ffb19a`) before execution and never modified, so no validator or pinned value was edited while a plan ran.

## Goal Achievement

### Roadmap Success Criteria

| # | Success Criterion | Status | Evidence at `de6db15` |
| --- | ----------------- | ------ | --------------------- |
| 1 | Frontmatter-only edits become searchable; parser dispatch + metadata-aware checksum in one plan and one migration; Markdown body byte-identical; YAML `---` bug fixed | ✓ VERIFIED | Files unchanged since the previous report (`models.py:19-72`, `parser.py:81,117,154-155`, `incremental.py:155-212,393,482`); indexing, database and integration suites green in the 2304-test battery. |
| 2 | One result per document by default; dedup inside `VectorSearcher` pre-fusion; `--per-chunk` escape hatch; ranking-contract change recorded with bench before/after and goldens with rationale | ✓ VERIFIED | `vector.py:296-323` and both keyed fuses (`hybrid.py:150-156,451-455`, the only `.fuse(` call sites under `src/sif`) unchanged. `--per-chunk` identity now also survives an 80-column terminal and is carried in CSV, Markdown, XML and path-only output (plan 19-10). B0 and B1 comparisons reproduced at HEAD: n 100, mean 0.0, 100 unchanged, both. |
| 3 | Deterministic pagination: CLI `--offset` and MCP offset; hybrid owns one slice; searchers return from rank 0; BM25 min_score order fixed; offset=0 reproduces the recorded contract | ✓ VERIFIED | SQL trace on the scratch index: `AND m.score <= ?` sits in the outer WHERE ahead of `LIMIT ? OFFSET ?` in the scoped and the unscoped branch, bound `-0.4285714285714286` for 0.3 and `-inf` for 1.0, omitted at 0, at a negative value and at NaN; `rank=options.offset + position` (`bm25.py:219`). B0 comparison at offset 0 and min_score 0: n 100, mean 0.0. |
| 4 | Title-aware ranking: title-FTS migration, rewritten triggers, measured bm25() column weights, mtime index; `documents_fts_v` survives a rebuild | ✓ VERIFIED | `schema.py:451-666,769` unchanged; `bm25(documents_fts, ?, ?)` bound at `bm25.py:162,184` with weights `1.0, 1.0` first in the parameter list (trace); `TestWeightedBM25` green; D-12 artifacts unchanged. |
| 5 | No redundant attach work: exactly one context/staleness attach at pipeline exit | ✓ VERIFIED | `enrich_results` is called once per direct CLI exit (`search.py:730,989,991`) and once per pipeline exit (`hybrid.py:356`, and `:308-309` behind `:367,379,484`); `_attach_contexts` grep count under `src/sif` is 0; spy tests green. |

**Score:** 5/5 roadmap success criteria verified.

### Observable Truths — Plans 19-01 to 19-09 (truths 1-63)

Wording and numbering are those of the previous report. "Unchanged" means the cited file is byte-identical to `4dbf386`; line numbers were re-resolved for the seven files that moved.

#### Plan 19-01 — CORR-01

| # | Truth | Status | Evidence |
| --- | ----- | ------ | -------- |
| 1 | `.yaml`/`.yml` starting with `---` parsed whole by `CodeParser` | ✓ VERIFIED | `parser.py:154-155,163-193,209` unchanged; test green. |
| 2 | Checksum over body + NUL + canonical full frontmatter; frontmatter or body edit changes it, key reorder does not | ✓ VERIFIED | `models.py:19-72`; `parser.py:81,117,184`; unchanged. |
| 3 | Markdown body path byte-identical | ✓ VERIFIED | `parser.py:57-90`; unchanged. |
| 4 | `date:` frontmatter stores and round-trips as canonical JSON | ✓ VERIFIED | `repositories.py:192,274`; unchanged. |
| 5 | `IncrementalIndexer` stores `parsed.checksum` | ✓ VERIFIED | `incremental.py:482`; unchanged. |
| 6 | Unknown extension falls back to `TextParser` | ✓ VERIFIED | `incremental.py:393`; unchanged. |

#### Plan 19-02 — CORR-01

| # | Truth | Status | Evidence |
| --- | ----- | ------ | -------- |
| 7 | `index_meta` with per-collection convention keys; `drop_all` removes it | ✓ VERIFIED | `schema.py:302-311,811`; `repositories.py:731`; unchanged. |
| 8 | One forced re-parse pass per absent or old marker | ✓ VERIFIED (scope note S1) | `incremental.py:155-212`; unchanged. |
| 9 | Metadata-only edit keeps chunks and embeddings | ✓ VERIFIED | `incremental.py:437-446`; unchanged. |
| 10 | Body edit deletes that document's chunks and embeddings first | ✓ VERIFIED | `incremental.py:451-458`; unchanged. |
| 11 | `--force` still takes the metadata fast path for an unchanged body | ✓ VERIFIED | `incremental.py:413,437`; unchanged. |
| 12 | `update_paths` never starts a migration | ✓ VERIFIED | `incremental.py:318`; unchanged. |
| 13 | `reindexed_paths` holds only added and body-changed paths; the watcher embeds from it | ✓ VERIFIED | `incremental.py:68,179-190,320-329`; `watcher.py:906,924`; unchanged. |
| 14 | A parse failure leaves the marker unwritten and counted | ✓ VERIFIED | `incremental.py:196-200,210`; unchanged. |

#### Plan 19-03 — CORR-05

| # | Truth | Status | Evidence |
| --- | ----- | ------ | -------- |
| 15 | Searchers no longer attach contexts or staleness | ✓ VERIFIED | `_attach_contexts` grep count 0 under `src/sif`. |
| 16 | `SearchPipeline.search` enriches exactly once on every exit | ✓ VERIFIED | `hybrid.py:301-309,356,367,379,484`; unchanged; spy tests green. |
| 17 | `enrich_results` composes attach then staleness; staleness is one batched or derived read | ? UNCERTAIN — human decision requested (scope note S2) | `context_attach.py:317-346`, `staleness.py:44-45,95-97` unchanged. Read literally, "one batched scan" is false at HEAD: Phase 21 reads the `embedded_documents` shadow with one lookup per result. No decision since (UAT test 5 pending). |
| 18 | Spy test counts one enrichment per exit | ✓ VERIFIED | Spy tests green in the battery. |
| 19 | `staleness.py` docstring names `enrich_results` | ✓ VERIFIED | `staleness.py:11-19`; unchanged. |

#### Plan 19-04 — CORR-05

| # | Truth | Status | Evidence |
| --- | ----- | ------ | -------- |
| 20 | CLI `search` and `vsearch` call `enrich_results` exactly once and keep context and staleness in the output | ✓ VERIFIED | `search.py:730` (BM25 exit), `:989,991` (vector exit); `TestSingleEnrichmentOwner` (`test_search.py:4002`) green. |
| 21 | MCP BM25 fallback enriches once; pipeline output is not enriched again | ✓ VERIFIED | `backend.py:490,501,534`; unchanged. |
| 22 | MCP re-map forwards `rank`, `collection_name`, `vectors_stale` | ✓ VERIFIED | `backend.py:189-197`; unchanged. |
| 23 | B0 saved run: 100 queries, bm25, zero mean delta | ✓ VERIFIED | `bench/b0.json` unchanged; comparison reproduced at HEAD (n 100, mean 0.0, unchanged 100). |

#### Plan 19-05 — CORR-03

| # | Truth | Status | Evidence |
| --- | ----- | ------ | -------- |
| 24 | `--offset` (`IntRange(min=0)`, default 0) on `search`, `vsearch`, `query`; past the end is an empty page | ✓ VERIFIED | `search.py:626,834,1070`; CLI probe with `--min-score 0.85 --offset 5` returned `[]`. |
| 25 | `rank = offset + position` | ✓ VERIFIED | `bm25.py:219`; `vector.py:248-251`; `hybrid.py:55-67`. |
| 26 | `limit=l offset=o` equals the `[o:o+l]` slice of one request, on BM25, vector and hybrid | ✓ VERIFIED | `TestConsistentPagination` green; `hybrid.py:119-176` unchanged. |
| 27 | BM25 applies `min_score` before LIMIT/OFFSET. **Amended 2026-11-26 by plan 19-12:** bound `-min_score/(1 - min_score)` with `m.score <= ?`; omitted at 0; 1 or more returns no row | ✓ VERIFIED against the amended wording | SQL trace, both branches: predicate in the outer WHERE (`bm25.py:175,197`) ahead of `LIMIT ? OFFSET ?`; bound `-0.4285714285714286` for 0.3, `-5.666666666666666` for 0.85, `-inf` for 1.0; no predicate and no parameter at 0, at -0.5 and at NaN. CLI: `--min-score 1` and `2` return `[]`. The wording verified on 2026-11-25 (`1 - 1/min_score`, `rank >= threshold`) is superseded by the plan's own dated amendment. |
| 28 | Hybrid calls each leg at offset 0 with `limit+offset` and slices once | ✓ VERIFIED | `hybrid.py:119-176`; unchanged. |
| 29 | Reranker window `max(candidate_limit, limit+offset)`; `top_k = limit+offset` | ✓ VERIFIED | `hybrid.py:417-428,463-477`; unchanged. |
| 30 | Pipeline passes offset 0 to hybrid and owns the one slice | ✓ VERIFIED | `hybrid.py:417-428,482-484`; unchanged. |
| 31 | MCP `query` offset validated and forwarded | ✓ VERIFIED (scope note S3) | `protocol.py:88,128,155`; unchanged. |
| 32 | Offset 0, min_score 0 rerun against B0 reports zero mean delta | ✓ VERIFIED | Reproduced at HEAD: n 100, mean 0.0, unchanged 100. |

#### Plan 19-06 — CORR-02

| # | Truth | Status | Evidence |
| --- | ----- | ------ | -------- |
| 33 | Vector search returns one row per document with the best chunk's identity and `chunk_matches` | ✓ VERIFIED | `vector.py:296-323`; `TestVectorDocumentDedup` (`test_vector.py:770`) green; unchanged. |
| 34 | Default fetch window `min(max(target*4,50),2048)` | ? UNCERTAIN — human decision requested (scope note S4) | `vector.py:25,187-231` unchanged; on scoped and filtered searches Phase 20 seeds the window from a selectivity pre-count (`:193-202,257-294`). No decision since (UAT test 5 pending). |
| 35 | A document with five or more matching chunks yields ten distinct documents at limit 10 | ✓ VERIFIED | `TestChunkyDocumentDedup` green. |
| 36 | Per-chunk mode returns ungrouped chunk rows; both fuses keyed by `fuse_key_for`; BM25 rows document-keyed | ✓ VERIFIED | `rrf.py:8-28`; `hybrid.py:150-156,451-455`; unchanged. |
| 37 | RRF math unchanged; merge adopts null chunk fields | ✓ VERIFIED | `rrf.py:36-47,108`; unchanged. |
| 38 | `to_dict()` carries `chunk_id`, `sequence`, `chunk_matches`; goldens carry a rationale | ✓ VERIFIED | `models.py:341-343`; `rerank.py:68-70` (`TestRebuildChunkIdentity` 3/3); SC1 docstring now also carries the dated 19-12 paragraph (`test_hybrid.py:797-808`). |
| 39 | Held-out snapshot regenerated with rationale | ✓ VERIFIED | `heldout_defaults.json` and its test unchanged; reproduction tests green. |

#### Plan 19-07 — CORR-02

| # | Truth | Status | Evidence |
| --- | ----- | ------ | -------- |
| 40 | `query` and `vsearch` accept `--per-chunk`; `search` does not | ✓ VERIFIED | `search.py:851,1125`; CLI: `search --per-chunk` exits 2 with `No such option: --per-chunk`; `vsearch` exits 2 on `--csv`, `--md`, `--xml`, `--files`. |
| 41 | Default output exposes `chunk_matches`; per-chunk rows display `path#sequence` and expose `chunk_id`/`sequence` | ✓ VERIFIED (was: visibility deferred to a human) | `_title_cell` (`search.py:169-187`), `_chunk_cell` (`:253-260`), `_chunk_column` (`:263-273`), the two Chunk columns (`:1031,1401`). The suffix is no longer deferred: it is kept at 80 columns under Rich 14.3.3 and Rich 15.0.0 and in a real 80-column pseudo-terminal. |
| 42 | MCP `query`/`vec_search` accept and forward `per_chunk` | ✓ VERIFIED (scope note S3) | `protocol.py:97,156`; unchanged. |
| 43 | MCP re-map forwards `chunk_id`, `sequence`, `chunk_matches` | ✓ VERIFIED | `backend.py:194-196`; unchanged. |
| 44 | Generated docs clean; CLI reference documents `--offset` and `--per-chunk` | ✓ VERIFIED | Generators run from an exported copy of HEAD: `docs/cli-reference.md` and `docs/configuration.md` byte-identical. `--offset` rows at `:491,534,569`; `--per-chunk` rows at `:504,575`. |
| 45 | B1 recorded after CORR-02; deltas labelled the BM25 no-drift check | ✓ VERIFIED | `bench/b1.json` unchanged; comparison reproduced at HEAD (n 100, mean 0.0); `docs/benchmarking.md:206-225`. |

#### Plan 19-08 — CORR-04

| # | Truth | Status | Evidence |
| --- | ----- | ------ | -------- |
| 46 | Populated-DB migration drops vocab first, rebuilds two-column, recreates vocab and triggers | ✓ VERIFIED | `schema.py:497-630`; unchanged; `TestTitleFtsMigration` green. |
| 47 | Rebuild populates exactly once; structural assertions hold | ✓ VERIFIED | `schema.py:574,586`; unchanged. |
| 48 | `documents_fts_v` yields after rebuild; triggers sync; integrity ok | ✓ VERIFIED | `schema.py:529,596-599`; 14-test suite green. |
| 49 | Fresh DB creates the two-column table directly | ✓ VERIFIED | Schema tests green. |
| 50 | Chunks FTS and its triggers stay byte-identical | ✓ VERIFIED | `schema.py:555-562,632-656`; unchanged. |
| 51 | `bm25(documents_fts, ?, ?)` binds weights left-to-right; 1.0/1.0 reproduces rank; min_score before LIMIT/OFFSET | ✓ VERIFIED | `bm25.py:24-25,120-121,131-134,162,184`; trace shows `[1.0, 1.0, query, …]`; `TestWeightedBM25` (`test_bm25.py:671`) re-pinned and green; red against the base searcher by name. |
| 52 | `SearchOptions.title_weight` override is internal only | ✓ VERIFIED | `models.py:377`; `bm25.py:121`. |
| 53 | SC1 golden and held-out snapshot carry a rationale | ✓ VERIFIED | `test_hybrid.py:797-808`; regeneration command reproduces both values. |
| 54 | No CJK lexical title win claimed | ✓ VERIFIED | `docs/benchmarking.md:255-257`. |

#### Plan 19-09 — CORR-04

| # | Truth | Status | Evidence |
| --- | ----- | ------ | -------- |
| 55 | `idx_documents_mtime` on fresh and migrated DBs | ✓ VERIFIED | `schema.py:769`; unchanged. |
| 56 | MCP-only process runs the schema migration once at startup | ✓ VERIFIED | `backend.py:290-293`; unchanged. |
| 57 | Per-leg and per-leg×split noise gates in `--compare` | ✓ VERIFIED | `personal_bench.py:471-546` unchanged; this verifier's two compare runs each named the 3 suppressed groups on stderr. |
| 58 | Title-weight sweep opens the index through `init_schema()` and requires a title column | ✓ VERIFIED (not re-run) | `.planning/tmp/phase19/sweep_title_weight.py` present, untracked, modification time still 2026-11-15; not executed this pass. |
| 59 | Sweep evaluates 2.0/3.0/4.0 against B1 | ✓ VERIFIED (not re-run) | `bench/d12-verdict.json` unchanged; ranks do not depend on the display map. |
| 60 | D-12 gate applied to both held-out legs | ✓ VERIFIED | Artifact: title winner false, body delta 0.0; unchanged. |
| 61 | Pinned `_TITLE_WEIGHT` is the accepted candidate or 1.0 | ✓ VERIFIED | `bm25.py:25` still 1.0; pin test green. |
| 62 | Goldens and docs reflect the pinned weight | ✓ VERIFIED | `docs/benchmarking.md:235-253`; docstrings. |
| 63 | Title weight is not a setting or CLI flag | ✓ VERIFIED | `title_weight` grep over `src/sif/cli`, `src/sif/config`, `docs/cli-reference.md`, `docs/configuration.md`: 0 files. |

### Observable Truths — Gap-Closure Plans

#### Plan 19-10 — CORR-02 (G-19-1, UAT test 3)

| # | Truth | Status | Evidence |
| --- | ----- | ------ | -------- |
| 10.1 | At 80 columns every chunk row of both per-chunk tables ends with its own `#sequence` for 31-, 49- and 304-character paths and a CJK name, with and without the Content column; a document-level BM25 row keeps the bare path | ✓ VERIFIED | `TestPerChunkSurfaces` through the real commands: 30/30 green under Rich 14.3.3 (py3.13.9) and under Rich 15.0.0 (py3.10.22). This verifier rendered both layouts, with and without the Content column, through the shipped console at `COLUMNS=80` on two row sets (the plan's rows and rows built from the scratch index's real paths): every chunk row ends with its own suffix, the document-level row is bare, maximum line width 80 cells, every table line at its right border; identical numbers under both Rich versions. Red against the base module: `4 failed, 2 passed`, the four 80-column tests by name. |
| 10.2 | The Chunk cell is a `_ChunkAddress` that measures at full width and shortens the path from the left at render time; the column floor is `min(8, widest address)`; scope: no tab or line break, at most six digits at the floor, console of at least 30 columns | ✓ VERIFIED (one parenthetical number not reproduced) | `search.py:207-273`. Measured on the plan's rows through the real commands: Chunk column 15 cells in the hybrid layout, 37 in the vector layout, 10 and 17 with the Content column, exactly as stated; every layout exactly 80 cells wide; the table fits from width 45, 57, 57 and 66, exactly as stated; the suffix is kept from width 30 upwards in all four layouts. The parenthetical "kept every row's suffix from 22 columns" did not reproduce on the plan's rows (measured 24 to 26); the plan says it was taken on a second row set that is not in the tree. The declared scope limit is accurate: a tab in a path loses the suffix (cell `/notes/a        b/protocol-n…`). |
| 10.3 | At 200 columns a 49-character path renders complete | ✓ VERIFIED | `test_per_chunk_shows_the_full_path_on_a_wide_terminal` green. |
| 10.4 | Per-chunk CSV: header `rank,score,title,path,collection,vectors_stale,sequence`; chunk rows carry the address and the bare number; a document-level row the plain path and an empty `sequence` | ✓ VERIFIED | `search.py:503-529`; probe output on a five-row page; `test_per_chunk_csv_carries_address_and_sequence` green. |
| 10.5 | Per-chunk Markdown shows the address and a `Sequence` line; XML the address and a `sequence` element; document-level rows get neither | ✓ VERIFIED (document-level half by probe only) | `search.py:532-605`. Probe on the five-row page: the document-level row (rank 5) has the plain Path line and no Sequence line in Markdown, children `title, path, collection` in XML; chunk rows `title, path, sequence, collection`. No test covers that half (validation gap V19-26-1). |
| 10.6 | Without `--per-chunk`, CSV, Markdown and XML are unchanged for every row, including rows that carry a sequence | ✓ VERIFIED | `search.py:751-779` call the formatters without `per_chunk`. Differential check of the four formatters between the base module (`147661b`) and HEAD over 216 row sets (object and dict rows, with and without a sequence, with and without line numbers): 864 comparisons, 0 mismatches. |
| 10.7 | `--files` and the quiet path-only output of a per-chunk page list each path once in first-occurrence order; `--limit` and `--offset` count chunk rows; default output is unchanged; `sif search` has no `--per-chunk` | ✓ VERIFIED | `search.py:276-278,1001,1338`. Probe: a three-chunk page of two documents prints two lines with `limit == 3` sent to the search; the same page without `--per-chunk` prints three lines, for `--files` and for `vsearch -q`. |
| 10.8 | `test_per_chunk_table_renders_path_sequence` passes unchanged; the render tests were red against the base source | ✓ VERIFIED | The function text is byte-identical to `147661b` and green. Overlays: whole class over the base module `19 failed, 11 passed`; over the Task 1 commit `4 failed, 26 passed` (CSV, Markdown/XML, files, path-only page), the same figures the SUMMARY records. |
| 10.9 | On a real 80-column terminal, against a live index with embedded chunks, every chunk row shows `#sequence` and no table line is cropped | ⚠️ insufficient_spec (backstop, abstained) | The measurable half was observed directly: the four layouts rendered into a 40×80 pseudo-terminal (`is_terminal` true) through the shipped commands, with the searcher replaced by rows, show every suffix and end at the right border within 80 cells. Not observed: a live embedded index (this verifier may not load an embedding model) and the readability judgement. The orchestrator's own run on an embedded scratch index is on record; the operator has not run it. |
| 10.10 | All four layouts end at their right border within 80 cells with snippet text on every row, with Rich 14.3.3 and with Rich 15.0.0 | ✓ VERIFIED (one word off) | Green under both Rich versions; this verifier's measurements are identical under both. The 34-character token is cut with an ellipsis (`supercalifrag…`), not folded, as the SUMMARY's residual note says; nothing depends on the wording. |
| 10.11 | `docs/changelog.md` carries one entry under `[Unreleased]` / `Changed` | ✓ VERIFIED | `docs/changelog.md:24`; phrase count 1. |

#### Plan 19-11 — CORR-03 (G-19-2 before-evidence and decision)

| # | Truth | Status | Evidence |
| --- | ----- | ------ | -------- |
| 11.1 | The artifact records, from the unchanged tree at the plan base, the probe rows, the two threshold outcomes, the B0 and B1 deltas and the empty hybrid BM25 leg | ✓ VERIFIED | `bench/g19-2-min-score.json` at `043db46`: `probe.before.head` equals the recorded plan base `4ac6262`. Every recorded value was reproduced by this verifier against the base searcher (`0744e83`) on the scratch index through the real CLI: `0.10570305094775757`, `0.1527108535938998`; `--min-score 0.12` keeps `Qelron Protocol Notes` alone at rank 1; `0.23` keeps nothing; the leg returns `[]` at 0.3 and 0.5. |
| 11.2 | No `after` half while the plan ran; the decision is the pending marker, then the id named at the checkpoint | ✓ VERIFIED | Git: `043db46` holds the pending marker and no after half; `dbb82b5` holds `monotone-map` and still no after half; the two revisions differ in one line. |
| 11.3 | No file outside `.planning/` changes in this plan | ✓ VERIFIED | `git diff --name-only 4ac6262 0744e83 -- . ':(exclude).planning'` is empty. |
| 11.4 | A `checkpoint:decision` with the three options, no `auto_select`, gate `blocking-human`, no implementation task; the only later edit is the decision field, gated on the artifact and its committed copy | ✓ VERIFIED | `19-11-PLAN.md:147` carries `type="checkpoint:decision" gate="blocking-human"`; `auto_select` appears only in sentences saying there is none; options `monotone-map`, `describe-current`, `deprecate-flag` at `:162-176`; plan file unmodified since `4ffb19a`. |
| 11.5 | A measurement that differs from the pins stops the plan; nothing is edited to agree | ✓ VERIFIED (as far as observable) | The plan carries the stop rule and a validator with the pinned values (`:119-126`). The plan file was never modified after planning, and the pinned values are what the base tree produces, so no mismatch had to be reconciled. Whether a mismatch would have stopped an executor is a process property no tree can show. |
| 11.6 | The operator's choice is recorded in the artifact and on a `Decision:` line of the SUMMARY and cannot be re-derived from the tree | ⚠️ insufficient_spec (backstop, abstained) | Observed: `decision: "monotone-map"` in the artifact at HEAD and the line `Decision: monotone-map` in `19-11-SUMMARY.md`, first committed in `0744e83`, before plan 19-12 began. Not observable: who answered the checkpoint. The SUMMARY records that the first executor stopped there and a continuation received the answer in its dispatch prompt. |

#### Plan 19-12 — CORR-03 (G-19-2 implementation)

| # | Truth | Status | Evidence |
| --- | ----- | ------ | -------- |
| 12.1 | Displayed score is `\|bm25\|/(1+\|bm25\|)` through `bm25_display_score`, rising with relevance; `search_chunks` uses the same function | ✓ VERIFIED | `bm25.py:47-57,209,269`. Direct calls: -1.0 → 0.5, -5.0 → 0.8333333333333334. `search_chunks` on the SC1 database returns the new map of the raw `rank` values (1.0246564843245888e-06 for -1.0246575342465753e-06), not the old one; no test covers that line (validation gap V19-26-3). |
| 12.2 | `--min-score M` binds `m.score <= ?` with `-M/(1-M)` for 0 < M < 1, before `LIMIT ? OFFSET ?` in both branches; 0, a negative value and NaN omit it; 1 or more returns no row; a row whose displayed score equals M to the last bit is dropped in a fraction of cases | ✓ VERIFIED | `bm25.py:60-77,130-134,175,197`. Threshold table: 0.5 → -1.0, 0.8 → -4.000000000000001, 1.0 and 1.5 → `-inf`, 0, -0.5 and NaN → `None`. SQL trace in the Success Criterion 3 row. CLI at HEAD: no threshold `0.8942969490522424`, `0.8472891464061002`; 0.12 and 0.23 keep both; 0.85 and 0.89 keep the best match alone; 1 and 2 keep nothing. The boundary: 251 of 617 real bench rows (40.7%) are dropped at their own exact score; 42.0% in a synthetic sample; the plan's "about 46%" depends on the sampling, which it does not state. |
| 12.3 | Filter before pagination, bound parameters only, no holes, global ranks, collection and metadata filters compose unchanged | ✓ VERIFIED | Trace: `[1.0, 1.0, query, collection id, -0.4285714285714286, 5, 1]` in the scoped branch and the same without the collection id in the unscoped one. `TestBm25ParamOrder` (`test_filters_sql.py:824-858`) green; `test_min_score_applies_before_offset_with_global_ranks` green and red against the base searcher. |
| 12.4 | Hybrid ranking unchanged without a threshold; B0 and B1 comparisons n 100, mean 0.0 | ✓ VERIFIED | `hybrid.py:121-156` and `rrf.py:100-118` unchanged: RRF ranks by list position and copies `bm25_score`. Both comparisons reproduced at HEAD. Probe titles and ranks identical before and after on the scratch index. |
| 12.5 | SC1 golden's two `bm25_score` values regenerated as `1.3749981093775994e-06` (d3) and `1.313431110717347e-06` (d1); order, RRF and vector scores, and the held-out snapshot, unchanged; dated rationale | ✓ VERIFIED | The plan's regeneration command prints exactly those two values at HEAD and the old two (`0.9999986250018905`, `0.9999986865688892`) against the base searcher. Neither value equals one minus the old one (`1.3749981094823838e-06`, `1.3134311107609875e-06`), so prohibition 6 holds. Held-out snapshot and its test byte-identical to the plan base; docstring at `test_hybrid.py:797-808`. |
| 12.6 | Six tests re-pinned; the zero-threshold test's negative assertion names the new predicate; red runs observed at four points | ✓ VERIFIED | `test_bm25.py:84-152`: `"m.score <= ?` in sql`, `params[3] == approx(-0.3 / 0.7)`, predicate ahead of `LIMIT ? OFFSET ?`, and `"m.score <=" not in sql` with the exact parameter list. All four red points reproduced: 1 and 3 from committed states (`3 failed, 1 passed, 72 deselected` over the base searcher, the CLI direction test and both `TestHybridMinScoreLeg` tests by name); 2 and 4 from the intermediate states reconstructed as the plan describes them (`9 failed, 156 passed`; `5 failed, 69 passed`), because the executor observed point 4 out of order. |
| 12.7 | Help text, regenerated CLI reference, changelog, dated notes and the amended fourth truth of `19-05-PLAN.md`; exactly one line of that plan changed | ✓ VERIFIED | `search.py:641-647`; phrase counts 1 and 2 in the source and in `docs/cli-reference.md:538,495,573`; changelog `:25`; `Score-direction note` once at `docs/benchmarking.md:247` and the SC1 value at `:225`; `Amended 2026-11-26 by plan 19-12` once; `19-05-PLAN.md` numstat `1 1`. |
| 12.8 | `sif query --min-score` changes in its BM25 leg only and keeps its help text; `TestHybridMinScoreLeg` pins it; the artifact's `hybrid_bm25_leg` shows no row before and both after at 0.3 and 0.5; MCP `query` shares the path | ✓ VERIFIED | `hybrid.py:121-128` copies the caller's options into both legs. Probe at HEAD through `HybridSearcher.search`: both rows at 0.3 and at 0.5; `[]` at both against the base searcher. `TestHybridMinScoreLeg` (`test_hybrid.py:2210`) green, red against the base. `backend.py:461,600,665` forward `min_score`. Help text of `query` unchanged (`search.py:1084`). |
| 12.9 | `sif vsearch --min-score` keeps its behaviour and help text; `vector.py` is untouched | ✓ VERIFIED | `vector.py` absent from the plan's changed set (`0744e83..HEAD`) and unchanged since `4dbf386`; help text at `search.py:848`; `TestVectorSearcher::test_search_applies_min_score` green. |
| 12.10 | The operator's choice at the 19-11 checkpoint is what authorises this change | ⚠️ insufficient_spec (backstop, abstained) | Same evidence gap as 11.6. Both records existed before the first commit of this plan (`0744e83` at 10:26, `37b6315` at 10:48). |

**Score:** 85/90 plan truths verified: 85 VERIFIED (61 from plans 19-01 to 19-09 and 24 from the gap-closure plans), 2 UNCERTAIN (17 and 34, unchanged since the previous report), 3 abstained as insufficient_spec (10.9, 11.6, 12.10), 0 failed, 0 present-behavior-unverified. The denominator grew from 63 to 90 with the 27 truths of plans 19-10 to 19-12.

### Scope Notes (literal wording vs HEAD)

| Note | Truth | Clause read literally | What HEAD does | Recorded decision |
| --- | --- | --- | --- | --- |
| S1 | 8 | marker written "only when zero files failed" | written when no stored document failed | Phase's own review fix WR-01 |
| S2 | 17 | "one batched scan" | one lookup per result on `embedded_documents` (Phase 21) | none — UAT test 5 pending |
| S3 | 31, 42 | "hand-written query schema" | signature-derived schema (Phase 22) | previous report's adjudication |
| S4 | 34 | start `min(max(target*4,50),2048)` | selectivity-seeded window on scoped searches (Phase 20) | none — UAT test 5 pending |

Truth 27 is no longer a scope note: its plan wording was amended in place by plan 19-12 and the code matches the amendment. The amendment rests on the 19-11 checkpoint decision, whose provenance is abstained (11.6, 12.10).

### Adjudications

**A. `--min-score` direction (UAT test 2, G-19-2) — fixed in code; authorisation to be confirmed.** The previous report reproduced that `--min-score 0.12` removed the best match. At HEAD the displayed BM25 score rises with relevance and the threshold is an upper bound on the bm25 value; on the scratch index `0.12` and `0.23` keep both matches, and `0.85` keeps the best match alone. The evidence artifact carries both halves, and both reproduce. Open: whether `monotone-map` is the operator's own answer (item 4).

**B. Per-chunk identity (UAT tests 1 and 3, G-19-1) — built under an assumption that is still marked pending.** The table keeps `#sequence` at 80 columns, and the machine formats and path-only output carry the identity as assumption A-19-10-1 describes. `19-10-PLAN.md:19` still reads `status: pending plan review` for that assumption, and UAT test 3 is a decision row. The orchestrator confirmed the layout on the operator's behalf; the operator has not (item 2).

**C. Review item IN-09 — reproduced through the real CLI.** Query `mycology` on the scratch index returns two rows without a threshold. Rank 2, `Mycology Handbook`, has the displayed score `0.8755239505116814`. With `--min-score 0.8755239505116814` the command returns one row and that row is gone. Over 111 single-word queries built from the corpus titles, 251 of 617 distinct (document, bm25) pairs behave this way. Plan 19-12 truth 2 records the boundary; the help text says "at least this value". The boundary does not contradict a must-have, and it does not touch the phase goal. It is a Warning with a decision for the operator (item 7). The file was modified since the previous report, so this finding is in scope for blocking; it is not treated as a blocker because no truth or criterion fails.

**D. Review item IN-10 — carried, not decided.** `sif query --min-score` applies the threshold to each leg on its own scale (BM25 displayed score, vector similarity), while a hybrid row's displayed `score` is its RRF value. Plan 19-12 truth 8 states this and keeps the help text "Minimum score threshold". Predates these plans (item 8).

**E. Validation gaps V19-26-1, V19-26-2, V19-26-3 — behaviour right, guard missing.** Direct probes through the real commands show all three behaviours hold at HEAD: the document-level row gets neither field in per-chunk Markdown or XML; a markup-bearing path renders literally in the Chunk cell (`/notes/[red]evil[/red].md#0`, `/notes/[/3]-review.md#0`, exit 0 both times); `search_chunks` uses the new score map. No test fails without any of them (item 9).

### Deferred Items

None.

### Advisory (New Scope, Unevidenced)

None. Every finding raised this pass is backed by a command and its output, and is reported in the Adjudications or under Human Verification.

## Required Artifacts

`verify.artifacts`: plans 19-10 and 19-11 pass 3/3 and 1/1 entries; plan 19-12 passes 8/9, the one non-passing entry being a tool limit (its `exports` list names `BM25Searcher.search` with a dotted path the tool cannot match; the method is at `bm25.py:87`). Plans 19-01 to 19-09 stay at 44/49 as in the previous report: `src/sif/mcp/handlers.py` was deleted in Phase 22 (property verified at its successor) and the three bench JSON files are declared under the pre-archive prefix and exist at the archived location.

| Artifact | Expected | Status | Details |
| -------- | -------- | ------ | ------- |
| `src/sif/cli/commands/search.py` | Chunk cell and column that keep `path#sequence` at 80 columns; identity in CSV, Markdown, XML; unique paths; new `search --min-score` help | ✓ VERIFIED | Exists (1434 lines), substantive, wired at `:1031` and `:1401` (both tables), `:928` and `:1223` (`per_chunk` into `SearchOptions`), `:1358,1369,1380` (formatters), `:1001,1338` (path-only). Every symbol the plan lists is defined. |
| `tests/unit/cli/test_search.py` | Render, truncation, format and path-only tests | ✓ VERIFIED | 30 items in `TestPerChunkSurfaces`; green under two Rich versions; red against the base module. |
| `tests/unit/cli/test_search_min_score.py` | End-to-end direction proof | ✓ VERIFIED | 136 lines, real temporary index, real CLI; red against the base searcher by name. |
| `src/sif/search/bm25.py` | Monotone score and pre-pagination bound | ✓ VERIFIED | `bm25_display_score`, `bm25_rank_threshold`, predicate in both branches; `ty` and `ruff` clean. |
| `tests/unit/search/test_bm25.py`, `test_filters_sql.py`, `test_hybrid.py` | Re-pinned tests, golden with rationale, `TestHybridMinScoreLeg` | ✓ VERIFIED | Green; red against the base searcher and against the reconstructed intermediates. |
| `bench/g19-2-min-score.json` | Before and after evidence | ✓ VERIFIED | HEAD equals `d08f93c`; SHA-256 `9da7c737…` as the SUMMARY records; before half identical from `043db46` through HEAD; both halves reproduced. |
| `19-05-PLAN.md` | Fourth truth amended in place | ✓ VERIFIED | numstat `1 1`. |
| `docs/changelog.md`, `docs/cli-reference.md`, `docs/benchmarking.md` | Written contract | ✓ VERIFIED | Counts and regenerated copy as under truth 12.7. |
| The 24 artifacts of the previous report that are unchanged: `models.py`, `parser.py`, `incremental.py`, `watcher.py`, `repositories.py`, `schema.py`, `database.py`, `vector.py`, `hybrid.py`, `rrf.py`, `context_attach.py`, `staleness.py`, `rerank.py`, `personal_bench.py`, `index.py`, `eval.py`, `protocol.py`, `tools.py`, `backend.py`, `b0.json`, `b1.json`, `d12-verdict.json`, `test_schema_title_fts.py`, `heldout_defaults.json` | — | ✓ VERIFIED (regression) | Byte-identical to `4dbf386`; suites green. |

**Artifacts:** 57 of the 62 declared entries verified by the tool or by inspection; the other 5 are superseded or relocated as before (`handlers.py`, declared by two plans, and the three bench JSON files under their pre-archive prefix). None is missing or a stub.

## Key Link Verification

`verify.key-links` verifies 2/2 (19-10), 2/2 (19-11) and 3/4 (19-12) by literal match; it reports the same "Target not referenced in source" for file-valued targets in the nine earlier plans as it did for the previous report (1/26 there). Each new link was checked at the call site:

| From | To | Via | Status | Details |
| ---- | -- | --- | ------ | ------- |
| `tests/unit/cli/test_search.py` | `src/sif/cli/commands/search.py` | both tables and three formats rendered through the real commands | ✓ WIRED | Red against the base and the Task 1 module, green at HEAD. |
| `search.py` `_ChunkAddress.__rich_console__` | `search.py` `_fit_head` / `_chunk_column` | fitted to the width Rich hands the cell; floor from every row's address | ✓ WIRED | `:250`, `:272-273`. |
| `bench/g19-2-min-score.json` | `bench/b0.json` | `bench_compare.b0.before` | ✓ WIRED | n 100, mean 0.0 reproduced before and after. |
| `bench/g19-2-min-score.json` | `19-11-SUMMARY.md` | the `Decision:` line | ✓ WIRED | `grep -x` finds `Decision: monotone-map`. |
| `search.py` `search_cmd` | `bm25.py` `BM25Searcher.search` | `min_score=min_score` at `:699`; bound at `:131-134` | ✓ WIRED | Trace and CLI probes. |
| `tests/unit/cli/test_search_min_score.py` | `bm25.py` | reads displayed scores from real `--json` output | ✓ WIRED | Fails against the base searcher. |
| `tests/unit/search/test_hybrid.py` | `hybrid.py` | `TestHybridMinScoreLeg` through `HybridSearcher.search` | ✓ WIRED | `hybrid.py:121-128`; fails against the base searcher. |
| `bench/g19-2-min-score.json` | `hybrid.py` | after half captured on the changed checkout | ✓ WIRED | Leg rows reproduced at HEAD and against the base. |

**Wiring:** 8/8 new connections verified; the 21 links of the previous report are unchanged.

## Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
| -------- | ------------- | ------ | ------------------ | ------ |
| `src/sif/search/bm25.py` | `score` | `bm25(documents_fts, ?, ?)` through `bm25_display_score` | Yes — values match the artifact and the CLI | ✓ FLOWING |
| `src/sif/cli/commands/search.py` | `results` → `paths`, CSV/Markdown/XML rows, Chunk cells | searcher rows enriched at entry | Yes — real rows from the scratch index in the renders; formatters read `_field` per row | ✓ FLOWING |
| `bench/g19-2-min-score.json` | before and after halves | real CLI, `HybridSearcher.search`, `--compare` on both sides | Yes — every value reproduced | ✓ FLOWING |
| `tests/unit/search/test_hybrid.py` `SNAPSHOT` | two `bm25_score` values | regenerated from the searcher by the plan's command | N/A — golden pin; it proves only those two values moved | N/A |

## Behavioral Spot-Checks

| Behavior | Command | Result | Status |
| -------- | ------- | ------ | ------ |
| Gap-closure battery (Rich 14.3.3) | `pytest -p no:cacheprovider --no-cov -q` on `TestPerChunkSurfaces`, `test_search_min_score.py`, `test_bm25.py`, `test_filters_sql.py`, `test_hybrid.py` | 271 passed | ✓ PASS |
| Same class under Rich 15.0.0 | `.venv/bin/python -m pytest … TestPerChunkSurfaces` (py3.10.22) | 30 passed | ✓ PASS |
| Phase 19 battery | `pytest … tests/unit/search` (minus `test_rerank.py`), `tests/unit/{cli,mcp,indexing,database}`, three integration files, docs, hygiene and release-metadata tests | 2304 passed, 0 skipped, exit 0, 50.3 s | ✓ PASS |
| Two named tests | `test_rerank.py::TestRebuildChunkIdentity`, `test_vector.py::TestVectorSearcher::test_search_applies_min_score` | 4 passed | ✓ PASS |
| Red state 1 (plan 19-10, Task 1) | current render tests over base `search.py` (`147661b`) | `4 failed, 2 passed`, the four 80-column tests by name | ✓ PASS |
| Red state 2 (plan 19-10, Task 2) | class over `search.py` at `4e258cf` | `4 failed, 26 passed` | ✓ PASS |
| Red states 1 and 3 (plan 19-12) | CLI test and `test_hybrid.py -k min_score` over base `bm25.py` (`0744e83`) | `3 failed, 1 passed, 72 deselected`, by name | ✓ PASS |
| Red state 2 (plan 19-12, reconstructed) | helpers present, searcher unwired | `9 failed, 156 passed`, the nine named tests | ✓ PASS |
| Red state 4 (plan 19-12, reconstructed) | searcher wired, golden stale | `5 failed, 69 passed`, the five snapshot tests | ✓ PASS |
| B0 and B1 comparisons at HEAD | `sif eval --personal --bm25-only -c bench-fixture --compare … --json --no-save` on the scratch index | both n 100, mean 0.0, helped 0, hurt 0, unchanged 100 | ✓ PASS |
| Before-evidence against the base searcher | CLI and hybrid leg over `bm25.py` at `0744e83` | the artifact's before half, value for value | ✓ PASS |
| Probe after at HEAD | `sif search search "Saltiv Protocol Notes" --json` | `0.8942969490522424`, `0.8472891464061002`, best first | ✓ PASS |
| Threshold edge values through the CLI | `--min-score` 0, -0.5, 0.12, 0.23, 0.85, 0.89, 1, 2; `--min-score 0.85 --offset 5` | both rows; both; both; both; best alone; best alone; `[]`; `[]`; `[]` | ✓ PASS |
| Predicate place and parameter order | recording proxy around the connection, scoped and unscoped | `AND m.score <= ?` ahead of `LIMIT ? OFFSET ?`; no lower-bound predicate | ✓ PASS |
| Golden regeneration | the plan's command at HEAD and against the base | `1.3749981093775994e-06`, `1.313431110717347e-06`; old values against the base | ✓ PASS |
| Render at 80 columns, shipped console | four layouts, two row sets, Rich 14.3.3 and 15.0.0 | every suffix kept; every table line at its right border; max 80 cells | ✓ PASS |
| Render in a real pseudo-terminal | `script`, `stty cols 80`, the shipped commands with the searcher replaced | 8 layouts: all suffixes kept, all lines at the right border within 80 cells | ✓ PASS (measurable half) |
| Column allocation and fit thresholds | width sweep 12 to 90 on the plan's rows | 15 / 37 / 10 / 17 cells; fits from 45 / 57 / 57 / 66 | ✓ PASS |
| Default output unchanged | base module against HEAD, 216 row sets × 4 formatters | 864 comparisons, 0 mismatches | ✓ PASS |
| Per-chunk formats and path-only output | real commands on a five-row page | as truths 10.4 to 10.7 state | ✓ PASS |
| Exact-threshold boundary (IN-09) | `sif search search mycology --min-score 0.8755239505116814 --json` | 1 row; `Mycology Handbook` (that score) absent; 251 of 617 real rows affected | ⚠️ reproduced, open in the ledger |
| Generated docs | generators run from an exported copy of HEAD | `docs/cli-reference.md`, `docs/configuration.md` byte-identical | ✓ PASS |
| Lint, format, types | `ruff check`, `ruff format --check` on the seven changed Python files; `ty check` on the two modules | All checks passed | ✓ PASS |

The full suite was not run by this verifier; the orchestrator ran `make test` on `d5382ae` (3303 passed, 1 skipped). No non-planning file differs between `d5382ae` and HEAD.

## Probe Execution

Step 7c: SKIPPED (no probes). No `scripts/*/tests/probe-*.sh` exists and no PLAN or SUMMARY declares one.

## Prohibitions (must-NOT checks)

All 46 prohibitions (30 from the nine earlier plans, 16 from the gap-closure plans) were re-checked against HEAD. All are judgment tier: the earlier plans carry bare `statement` entries and the new ones carry `status: unresolved` with no `verification` field. This table is a non-authoritative LLM-judge verdict. None has a human resolution on record; item 10 asks for one.

| Plan | # | Prohibition | Status | Current-code evidence |
| ---- | - | ----------- | ------ | --------------------- |
| 19-01 | 1-3 | no body-only hash; Markdown body path unaltered; no new runtime dependency | ✓ PASS | Unchanged files; `pyproject.toml` and `uv.lock` untouched. |
| 19-02 | 1-3 | marker never cleared early; no re-chunk on unchanged body; no migration from drift checks | ✓ PASS | Unchanged files. |
| 19-03 | 1 | No persisted staleness flag or per-result embedding query | ⚠️ FLAGGED — superseded in letter by Phase 21 | `staleness.py:44-45,95-97` unchanged: one lookup per result on `embedded_documents`. The flag itself is still derived at query time. No decision (UAT test 4 pending). |
| 19-03 | 2-3 | no loss of context or staleness markers; no SQL path prefilter | ✓ PASS | Unchanged files; one enrichment per exit. |
| 19-04 | 1-3 | no double attach on MCP; no scratch database committed; B0 recorded after CORR-01 | ✓ PASS | Unchanged; the four bench JSON files are the only tracked non-Markdown files under the phase directory. |
| 19-05 | 1 | No interpolation of offset, limit or min_score into SQL | ✓ PASS | Trace: weights, query, collection ids, threshold, limit and offset are all bound. |
| 19-05 | 2 | `min_score` never applied after pagination | ✓ PASS | Predicate before `LIMIT ? OFFSET ?`; `search_chunks` keeps its post-window filter (recorded deferral IN-05, no production caller). |
| 19-05 | 3 | No double-applied offset | ✓ PASS | `hybrid.py:121-125,417-428` unchanged. |
| 19-06 | 1-4 | RRF math unchanged; no duplicate document rows; fetch ceiling; chunk identity kept across legs | ✓ PASS | `rrf.py`, `vector.py`, `hybrid.py` unchanged; default path-only output prints one line per row. |
| 19-07 | 1-3 | no per-chunk flag on document-level surfaces; chunk fields kept at re-map; generated docs not hand-edited | ✓ PASS | Exit 2 on `search --per-chunk`; `lex_search` schema unchanged; regenerated copy byte-identical. |
| 19-08 | 1-4 | detect-and-rebuild; vocab dropped first; weights bound; no CJK claim | ✓ PASS | Unchanged files. |
| 19-09 | 1-4 | title weight internal; no win declared inside noise; no regression beyond the tie rule; MCP-only schema init | ✓ PASS | Unchanged files; grep 0 files. |
| 19-10 | 1 | Default CSV, Markdown, XML, table and path-only output unchanged; no de-duplication outside per-chunk mode | ✓ PASS | 864 comparisons, 0 mismatches; default table and `search_cmd` loop untouched in the diff; probe prints one line per row by default. |
| 19-10 | 2 | No `--csv`, `--md`, `--xml`, `--files` on `vsearch`; no `--per-chunk` on `search` | ✓ PASS | All five exit 2 through the real CLI. |
| 19-10 | 3 | Chunk column not marked `no_wrap` | ✓ PASS | `_chunk_column` returns `style` and `min_width` only (`search.py:273`); `no_wrap=True` is on the cell's `Text` (`:250`), not the column. |
| 19-10 | 4 | Generated docs not hand-edited | ✓ PASS | Byte-identical across `147661b..5e83d6d`; the one later change is plan 19-12's generator run, in sync. |
| 19-10 | 5 | Real model directory not linked, no `sif index embed`, before `cache.state: valid` | — not verifiable | Process-time; the SUMMARY records the gate ran first. Nothing in the tree can confirm or refute it. |
| 19-11 | 1 | No edit under `src/`, `tests/` or `docs/` | ✓ PASS | Empty diff against the plan base. |
| 19-11 | 2 | Committed bench runs not rewritten; no saved run overwritten | ✓ PASS | Unchanged. |
| 19-11 | 3 | No `auto_select`; no score-map change without the recorded choice | ✓ PASS | No `auto_select` attribute; the source change is in plan 19-12, after both records. |
| 19-11 | 4 | Capture not run against the default database or cache | — not verifiable | Process-time. |
| 19-11 | 5 | No recorded value, pin or baseline edited to agree | ✓ PASS | Artifact before half identical across three revisions; plan file unmodified since planning. |
| 19-12 | 1 | No interpolation | ✓ PASS | Trace. |
| 19-12 | 2 | Not after pagination | ✓ PASS | As 19-05 P2. |
| 19-12 | 3 | `vsearch` behaviour and help, vector score, RRF math, vector threshold, `query` help text, fused order untouched | ✓ PASS | `vector.py`, `hybrid.py`, `rrf.py` unchanged; `Minimum score threshold` twice (`search.py:848,1084`). |
| 19-12 | 4 | Bench runs and held-out snapshot not rewritten | ✓ PASS | Unchanged. |
| 19-12 | 5 | Only the fourth truth of `19-05-PLAN.md`; no other plan or summary | ✓ PASS | numstat `1 1`; no other plan or summary changed since `0744e83`. |
| 19-12 | 6 | New golden values regenerated, not derived by subtraction | ✓ PASS | Regeneration command reproduces them; subtraction gives different digits. |

**Verdict:** 43 hold, 1 flagged, 2 not verifiable from the tree. `prohibitions_flagged: 1`.

## Requirements Coverage

| Requirement | Source plans | Description | Status | Evidence |
| ----------- | ------------ | ----------- | ------ | -------- |
| CORR-01 | 19-01, 19-02 | Frontmatter-only edits become searchable | ✓ SATISFIED | Truths 1-14. |
| CORR-02 | 19-06, 19-07, 19-10 | One result per document; `--per-chunk` escape hatch; recorded ranking-contract change | ✓ SATISFIED — truth 34 UNCERTAIN (S4) | Truths 33-45 and 10.1-10.11. |
| CORR-03 | 19-05, 19-11, 19-12 | Deterministic pagination; BM25 min_score order | ✓ SATISFIED | Truths 24-32 (27 as amended) and 11.1-12.10. |
| CORR-04 | 19-08, 19-09 | Title-aware ranking | ✓ SATISFIED | Truths 46-63. |
| CORR-05 | 19-03, 19-04 | One context/staleness attach | ✓ SATISFIED — truth 17 UNCERTAIN (S2) | Truths 15-23. |

Every requirement ID named in the twelve plans' frontmatter is one of CORR-01 to CORR-05 (CORR-01 twice, CORR-02 three times, CORR-03 three times, CORR-04 twice, CORR-05 twice), and `.planning/milestones/v1.2-REQUIREMENTS.md` maps exactly those five to Phase 19. CORR-06 maps to Phase 21 and is correctly absent. No orphaned requirement.

## Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
| ---- | ---- | ------- | -------- | ------ |
| — | — | `TBD`, `FIXME`, `XXX`: 0 in the 10 changed files and in the other covered source files; `TODO`, `HACK`, `PLACEHOLDER`: 0 | — | Debt-marker gate clean. |
| `src/sif/search/bm25.py` | 131-134, 209 | Exact-threshold drop (IN-09), reproduced | ⚠️ Warning | A row whose displayed score equals `--min-score` to the last bit is dropped in 251 of 617 real rows. Recorded in plan 19-12 truth 2; open in the ledger; operator's call (item 7). |
| `src/sif/cli/commands/search.py` `query_cmd` with `src/sif/search/hybrid.py` | 1084, 121-128 | Threshold applied per leg while the displayed score is RRF (IN-10) | ⚠️ Warning | Predates these plans; plan 19-12 truth 8 states it and keeps the help text (item 8). |
| `tests/unit/cli/test_search.py` | `test_per_chunk_markdown_and_xml_carry_chunk_identity` | No test for the document-level half of truth 10.5 (V19-26-1) | ⚠️ Warning | Behaviour right today (probe); no guard. |
| `tests/unit/cli/test_search.py` | `TestPerChunkSurfaces` | No test renders a markup-bearing path in the Chunk cell (V19-26-2) | ⚠️ Warning | Threat T-19-24 mitigation rests on a manual check; behaviour right today (probe). |
| `tests/unit/search/test_bm25.py` | `test_search_chunks_returns_tuples` | No test pins the score map of `search_chunks` (V19-26-3) | ℹ️ Info | No production caller; behaviour right today (probe). |
| `19-UAT.md` | 65-95 | Record not updated after gap closure | ⚠️ Warning | G-19-1 and G-19-2 still read `status: failed` with `resolved_by: ""`; tests 1 and 2 still `result: issue`; file last modified 2026-11-25. The orchestrator owns this file. |
| `19-10-PLAN.md` | 19 | Assumption A-19-10-1 `status: pending plan review` | ⚠️ Warning | The layout shipped while the assumption is still marked unconfirmed (item 2). |
| `src/sif/search/bm25.py` | 23 | Comment cites the pre-archive path of `d12-verdict.json` | ℹ️ Info | Line untouched by plan 19-12; the file lives under `.planning/milestones/v1.2-phases/…`. |
| `19-05-PLAN.md` | 121 | Task text still derives the old threshold | ℹ️ Info | Historical record; prohibition 19-12 P5 forbids editing it. The truth itself is amended. |
| `19-RESEARCH.md` | 296, 404, 535-540 | Research still states the earlier score map | ℹ️ Info | Historical research document. |
| `tests/unit/cli/test_search.py` | 2097-2100, 2313-2316 | Relaxed title assertions (IN-07) | ℹ️ Info | Carried; open in the ledger. |
| `tests/support/__init__.py` | 26-32 | `symlink_or_skip` on any `OSError` (IN-08) | ℹ️ Info | Carried; open in the ledger; 0 skips in this pass. |
| `src/sif/cli/commands/search.py` | 207-229 | Declared scope limit: a tab in a path loses the suffix | ℹ️ Info | Stated by truth 10.2 and reproduced; outside the guarantee. |

**Test quality audit.** No disabled test is linked to a requirement: the only skip guards in the changed test files are the four `sqlite-vec not available` checks, and the battery skipped nothing. No test writes its own expected values at run time. Expected-value provenance is PARTIAL for the two goldens (the SC1 snapshot and the held-out snapshot are recorded from the system on a deterministic fixture: they pin a contract, ranking quality is not proven by them); the direction of `--min-score` is proved by independent oracles instead (descending-score assertions, thresholds placed between two rows' scores, expected document ids). Assertion strength is value-level. Three stated behaviours have no guard (the V19-26 items above), which is what `19-VALIDATION.md` records with `nyquist_compliant: false`. No blocker comes from this audit.

**Coincidental reliance.** None flagged. The one assumption worth naming is declared: the 80-column fit depends on Rich's table layout, measured by the plan for Rich 14.3.3 and 15.0.0 only, while `pyproject.toml` allows `rich>=13.0.0`. Rich 13.x was not measured by anyone; the render tests would catch a change on whatever Rich a CI cell installs.

## Decision Coverage

All trackable CONTEXT.md decisions are honored by shipped artifacts — 12/12 (`check.decision-coverage-verify`, non-blocking). Plan 19-10 implements D-03 (chunk identity in per-chunk output, display form `path#sequence`) and keeps D-01; plan 19-12 keeps the locked rule that BM25 `min_score` is applied before pagination and D-06's global ranks, and records the score-map change with before and after evidence and a golden rationale as the "every ranking-contract change" rule asks.

## Human Verification Required

Ten items need the operator. For the three harvested `<human-check>` blocks the test and expected text are the plan's, unmodified. Nothing here was run by the operator personally.

### 1. Per-chunk tables on a real 80-column terminal (UAT test 1)

**Test:** In a real terminal that is 80 columns wide, on an index with embedded chunks whose paths are 30 or more characters, run `sif search query --per-chunk QUERY -n 12` and then `sif search vsearch --per-chunk QUERY -n 12` with a query that matches several chunks of each of several documents, each also with `--full --line-numbers`.
**Expected:** On both tables you can tell the rows apart, which is what UAT test 1 is about: for each row you can say which document it comes from and which chunk of that document it is, using the table alone. The Chunk cell ends with a number sign followed by that row's sequence, and rows of one document differ by that number. The number alone does not always name the document: at 80 columns the hybrid table gives the Chunk column 15 cells, so different documents can show the same file-name tail, such as `…col-notes.md`, and the Title and Collection columns must still tell them apart. The table ends at its right border inside the terminal in every render, also with the Content column; nothing is cut off on the right, and the other columns (rank, score, title, collection) are still visible. A visible number that leaves two rows indistinguishable does not pass this check.
**Why human:** Whether rows stay recognisable at the canonical width on a real terminal is a visual judgement. The automated tests force the same width through the same CLI code and pin that each row shows its own sequence and that the table fits, but they cannot see the terminal or say whether the result is readable, and the UAT tester observed the defect only on a live render.
**On record:** performed on 2026-11-26 by the orchestrator on the committed code (isolated scratch index, 26 chunks embedded with the cached model, 80-column pseudo-terminal) and approved on the operator's behalf under this project's auto mode; recorded in `19-10-SUMMARY.md`. This verifier's pseudo-terminal render agrees on the measurable half and shows the case the expected text warns about: in the hybrid layout three different documents display `…col-notes.md#0`, `#3` and `#6`, told apart only by the Title column.

### 2. Per-chunk machine formats and path-only output (UAT test 3)

**Test:** Run `sif search query --per-chunk QUERY --csv`, the same with `--md`, with `--xml` and with `--files`, on a document with several matching chunks; then the same without `--per-chunk`.
**Expected:** The CSV header ends with a `sequence` column and a chunk row's path is the path followed by a number sign and the sequence; Markdown and XML chunk rows carry the same address and the bare sequence; a document-level row has the plain path and no sequence. `--files` lists each path once for that page. Without `--per-chunk` the three formats and `--files` look exactly as before, including a page that lists one document twice because it is indexed in two collections. This is UAT test 3, the behaviour assumption A-19-10-1 describes; confirm or amend that assumption here.
**Why human:** UAT test 3 is recorded as a decision row, not a failed test: whether machine formats must carry chunk identity, and in which fields, is the operator's call. The plan implements the assumed behaviour and can be amended if the operator wants another field layout.
**On record:** performed by the orchestrator on the same scratch index and approved on the operator's behalf; no other field layout was named. The assumption in `19-10-PLAN.md` is still `pending plan review`. The output matches the expected text; whether this is the layout the operator wants is the open question.

### 3. `sif query --min-score` on the operator's own index

**Test:** On an index with embedded chunks run `sif search query QUERY --min-score 0.3 --json` and the same without `--min-score`, with a query that matches documents lexically as well as semantically; compare the `scores` of the returned rows. Then run `sif search vsearch QUERY --min-score 0.3` as before.
**Expected:** Without the threshold and with it, rows that match lexically carry a `bm25_score` beside their `vector_score`: the threshold keeps the stronger BM25 matches in the page. Before this plan the same thresholded command returned rows with no `bm25_score` at all, because its BM25 leg had been emptied. `vsearch --min-score` filters on similarity exactly as before.
**Why human:** The evidence artifact and the unit tests read the BM25 leg through the searcher; whether the real `sif query` output reads that way on the operator's own index is what this check confirms.
**On record:** performed by the orchestrator on 2026-11-26 on an isolated index with real embeddings (base `0744e83` against `d5382ae`) and approved on the operator's behalf. The check's text says "the operator's own index"; it did not run there. This verifier could not run `query` or `vsearch` and verified the leg through `HybridSearcher.search` and the tests.

### 4. Authorisation of the score-map change

**Test:** Confirm that `monotone-map` is the operator's own answer at the 19-11 checkpoint, with the scope stated there.
**Expected:** The operator confirms the choice and its scope, or names another option for re-planning.
**Why human:** Truths 11.6 and 12.10 are tagged backstop: the authorisation cannot be re-derived from the tree. Both records exist and agree; who answered a blocking-human checkpoint is not observable by a verifier. The SUMMARY attributes the answer to the operator through the orchestrator's dispatch.

### 5. Prohibition 19-03 P1

**Test:** Review `src/sif/search/staleness.py:44-45,67-98` against "MUST NOT persist vector staleness as a per-document flag or issue a per-result embedding query".
**Expected:** A recorded decision that the Phase 21 shadow read is the accepted successor of the Phase 19 batched scan.
**Why human:** Judgment-tier prohibition whose letter no longer describes HEAD; its intent holds. No decision since the previous report.

### 6. Truths 17 and 34

**Test:** Decide whether truths 17 and 34 are accepted for their guarantees (scope notes S2 and S4) or must hold literally.
**Expected:** Either record overrides for the Phase 20 and Phase 21 mechanisms, or ask for the Phase 19 literal behaviour back.
**Why human:** Two clauses are literally false on paths a later roadmap phase changed; a verifier cannot accept a deviation on the developer's behalf. No decision since the previous report.

### 7. Exact-threshold boundary (IN-09)

**Test:** Decide whether `--min-score` must keep a row whose displayed score equals the threshold to the last bit.
**Expected:** Either accept the boundary that plan 19-12 truth 2 records, or ask for an exact threshold.
**Why human:** A product call about scripts that copy a score from `--json` output. Reproduced through the real CLI in Adjudication C; the plan records the boundary as a property and not as an operator decision.

### 8. `sif query --min-score` and the displayed score (IN-10)

**Test:** Decide what `sif query --min-score` means for the displayed score of a hybrid row.
**Expected:** A recorded contract for the flag and its help text.
**Why human:** Each leg is filtered on its own scale while the displayed score is an RRF value far below any ordinary threshold; whether that is acceptable is a product decision. It predates these plans.

### 9. The three unguarded behaviours

**Test:** Decide whether V19-26-1, V19-26-2 and V19-26-3 get a test before the phase closes.
**Expected:** Three tests added, or a recorded acceptance of `nyquist_compliant: false`.
**Why human:** The gate was put to the operator and not answered; adding tests re-stales the reports of Phases 19, 20 and 21.

### 10. The judgment-tier prohibitions

**Test:** Resolve the 46 prohibitions at the end-of-phase checkpoint.
**Expected:** A recorded human resolution, at least for 19-03 P1 and the two process-time items.
**Why human:** Every prohibition in this phase is judgment tier and none has a human resolution on record; the table above is a non-authoritative verdict.

## Verifier Process Note

At 05:22:25Z this verifier ran `sif search vsearch "Saltiv Protocol Notes" --no-refresh` against its scratch index to show that the command needs an embedder. With an empty scratch cache the command started a model download from ModelScope (log line: `Got 12 files, start to download`). The process ended about one second later, when its output pipe closed. That call broke the dispatch rules for this verification: no network, no embedding model, no download.

What it left, by inspection about a minute later: inside the scratch directory only — `embeddings_cache.db` (16 KB, created on open), a 0-byte lock file `models/.lock/Qwen___Qwen3-Embedding-0.6B` and an empty `models/Qwen` directory. No file in the scratch directory exceeded 64 KB apart from the scratch index, so no model weights were written. No entry under `~/Library/Caches/sif` or `~/Library/Application Support/sif` had a modification time after 05:21Z (metadata listing only), so the real cache and the default database were not touched. No process was left running. The scratch directory is removed. The coordinator was told as soon as the breach was noticed. Nothing about the ModelScope side is observable from here.

Every other CLI call in this verification was BM25-only: `collection add`, `index update -c bench-fixture`, `search search`, and `eval --personal --bm25-only`, which returns before constructing an embedder (`eval.py:203-204`). The per-chunk renders replaced the searcher. After the breach neither `vsearch` nor `query` was run again.

## Gaps Summary

No must-have failed and no regression was found. All five roadmap success criteria hold at `de6db15`. 85 of the 90 plan truths are verified; truths 17 and 34 remain UNCERTAIN for the same reason as on 2026-11-25; the three backstop truths of the gap-closure plans are abstained because their evidence is a human act this verifier cannot observe.

The two UAT gaps are closed in code and in the automated record. G-19-1: both per-chunk tables keep `#sequence` at 80 columns under two Rich versions and in a real pseudo-terminal. G-19-2: the displayed BM25 score rises with relevance and `--min-score` keeps the best matches, with before and after evidence that reproduces on both sides. Default output is byte-identical to the base. The recorded ranking contract is unchanged (B0 and B1 at n 100, mean 0.0).

The status is `human_needed`, for four reasons, none of them a missing or broken deliverable:

- Three behaviours rest on a human act that has not happened: the operator's own confirmation of the `monotone-map` decision (11.6, 12.10) and of the per-chunk table on a real terminal (10.9). The three harvested human checks were performed by the orchestrator on the operator's behalf, on isolated indexes, and are listed above with that provenance.
- Four decisions carried from the previous report are still open: prohibition 19-03 P1, truths 17 and 34, and now the field layout of the per-chunk machine formats, which shipped under an assumption still marked pending.
- Two review findings on the surface this round changed are reproduced and undecided: the exact-threshold drop (IN-09) and the per-leg meaning of `query --min-score` (IN-10).
- Three stated behaviours have no test that fails without them, and the phase's 46 judgment-tier prohibitions have no recorded human resolution.

Records the orchestrator owns are out of date with the code: `19-UAT.md` still shows both gaps as failed with `resolved_by` empty, and the assumption in `19-10-PLAN.md` is still `pending plan review`. `verification.status` reports `stale` for the reports of Phases 18, 20, 21, 22 and 24 because they cover the files this round changed; no test covering those surfaces failed in this pass.

---

_Verified: 2026-11-26T05:36:00Z_
_Verifier: gsd-verifier agent (ZCode)_
