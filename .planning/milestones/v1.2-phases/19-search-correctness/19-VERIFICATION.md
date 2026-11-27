---
phase: 19-search-correctness
verified: 2026-11-27T12:10:19Z
status: passed
score: 115/115 must-haves verified
covered_files: [".planning/milestones/v1.2-phases/19-search-correctness/19-01-PLAN.md", ".planning/milestones/v1.2-phases/19-search-correctness/19-01-SUMMARY.md", ".planning/milestones/v1.2-phases/19-search-correctness/19-02-PLAN.md", ".planning/milestones/v1.2-phases/19-search-correctness/19-02-SUMMARY.md", ".planning/milestones/v1.2-phases/19-search-correctness/19-03-PLAN.md", ".planning/milestones/v1.2-phases/19-search-correctness/19-03-SUMMARY.md", ".planning/milestones/v1.2-phases/19-search-correctness/19-04-PLAN.md", ".planning/milestones/v1.2-phases/19-search-correctness/19-04-SUMMARY.md", ".planning/milestones/v1.2-phases/19-search-correctness/19-05-PLAN.md", ".planning/milestones/v1.2-phases/19-search-correctness/19-05-SUMMARY.md", ".planning/milestones/v1.2-phases/19-search-correctness/19-06-PLAN.md", ".planning/milestones/v1.2-phases/19-search-correctness/19-06-SUMMARY.md", ".planning/milestones/v1.2-phases/19-search-correctness/19-07-PLAN.md", ".planning/milestones/v1.2-phases/19-search-correctness/19-07-SUMMARY.md", ".planning/milestones/v1.2-phases/19-search-correctness/19-08-PLAN.md", ".planning/milestones/v1.2-phases/19-search-correctness/19-08-SUMMARY.md", ".planning/milestones/v1.2-phases/19-search-correctness/19-09-PLAN.md", ".planning/milestones/v1.2-phases/19-search-correctness/19-09-SUMMARY.md", ".planning/milestones/v1.2-phases/19-search-correctness/19-10-PLAN.md", ".planning/milestones/v1.2-phases/19-search-correctness/19-10-SUMMARY.md", ".planning/milestones/v1.2-phases/19-search-correctness/19-11-PLAN.md", ".planning/milestones/v1.2-phases/19-search-correctness/19-11-SUMMARY.md", ".planning/milestones/v1.2-phases/19-search-correctness/19-12-PLAN.md", ".planning/milestones/v1.2-phases/19-search-correctness/19-12-SUMMARY.md", ".planning/milestones/v1.2-phases/19-search-correctness/19-13-PLAN.md", ".planning/milestones/v1.2-phases/19-search-correctness/19-13-SUMMARY.md", ".planning/milestones/v1.2-phases/19-search-correctness/19-14-PLAN.md", ".planning/milestones/v1.2-phases/19-search-correctness/19-14-SUMMARY.md", ".planning/milestones/v1.2-phases/19-search-correctness/19-15-PLAN.md", ".planning/milestones/v1.2-phases/19-search-correctness/19-15-SUMMARY.md", ".planning/milestones/v1.2-phases/19-search-correctness/19-CONTEXT.md", ".planning/milestones/v1.2-phases/19-search-correctness/19-REVIEW-DISPOSITION.md", ".planning/milestones/v1.2-phases/19-search-correctness/19-REVIEW.md", ".planning/milestones/v1.2-phases/19-search-correctness/19-SECURITY.md", ".planning/milestones/v1.2-phases/19-search-correctness/19-UAT.md", ".planning/milestones/v1.2-phases/19-search-correctness/19-VALIDATION.md", ".planning/milestones/v1.2-phases/19-search-correctness/bench/b0.json", ".planning/milestones/v1.2-phases/19-search-correctness/bench/b1.json", ".planning/milestones/v1.2-phases/19-search-correctness/bench/d12-verdict.json", ".planning/milestones/v1.2-phases/19-search-correctness/bench/g19-2-min-score.json", ".planning/milestones/v1.2-phases/19-search-correctness/bench/g19-8-exact-threshold.json", "docs/benchmarking.md", "docs/changelog.md", "docs/cli-reference.md", "docs/configuration.md", "docs/mcp-server.md", "src/sif/cli/commands/eval.py", "src/sif/cli/commands/index.py", "src/sif/cli/commands/search.py", "src/sif/core/models.py", "src/sif/database/database.py", "src/sif/database/repositories.py", "src/sif/database/schema.py", "src/sif/indexing/incremental.py", "src/sif/indexing/parser.py", "src/sif/indexing/watcher.py", "src/sif/mcp/backend.py", "src/sif/mcp/protocol.py", "src/sif/mcp/tools.py", "src/sif/search/bm25.py", "src/sif/search/context_attach.py", "src/sif/search/hybrid.py", "src/sif/search/personal_bench.py", "src/sif/search/rerank.py", "src/sif/search/rrf.py", "src/sif/search/staleness.py", "src/sif/search/vector.py", "tests/fixtures/bench/heldout_defaults.json", "tests/integration/test_embed_idempotency.py", "tests/integration/test_incremental_equivalence.py", "tests/integration/test_search_correctness.py", "tests/support/__init__.py", "tests/test_docs.py", "tests/unit/cli/test_eval.py", "tests/unit/cli/test_index.py", "tests/unit/cli/test_search.py", "tests/unit/cli/test_search_exact_threshold.py", "tests/unit/cli/test_search_min_score.py", "tests/unit/cli/test_search_pagination.py", "tests/unit/database/test_repositories.py", "tests/unit/database/test_schema.py", "tests/unit/database/test_schema_title_fts.py", "tests/unit/indexing/test_incremental.py", "tests/unit/indexing/test_parser.py", "tests/unit/indexing/test_parser_checksum.py", "tests/unit/indexing/test_watcher.py", "tests/unit/mcp/goldens/2024-11-05.json", "tests/unit/mcp/goldens/2025-03-26.json", "tests/unit/mcp/goldens/2025-06-18.json", "tests/unit/mcp/goldens/2025-11-25.json", "tests/unit/mcp/goldens/2026-07-28.json", "tests/unit/mcp/test_backend.py", "tests/unit/search/test_bench_snapshot.py", "tests/unit/search/test_bm25.py", "tests/unit/search/test_collection_filter.py", "tests/unit/search/test_context_attach.py", "tests/unit/search/test_filters_sql.py", "tests/unit/search/test_hybrid.py", "tests/unit/search/test_personal_bench.py", "tests/unit/search/test_rerank.py", "tests/unit/search/test_rrf.py", "tests/unit/search/test_staleness.py", "tests/unit/search/test_vector.py"]
covered_digest: "v4:sha256:7c9b7f3eb8ae4827f8964e3147b450f08884df8dfedb0b4467c855814f3f4113"
behavior_unverified: 0
overrides_applied: 0
insufficient_spec: 0
insufficient_spec_items: []
prohibitions_flagged: 0
prohibition_verdicts: "71 judgment-tier prohibitions: 64 hold under this LLM judge (including 19-03 P1, resolved by 19-UAT test 4), 7 are process-time claims the tree cannot confirm or refute (19-10 P5, 19-11 P4, 19-13 P8, 19-13 P9, 19-14 P7, 19-15 P3, 19-15 P6); none flagged. End-of-phase acceptance recorded 2026-11-27 in 19-UAT test 16 (operator delegated the check to the orchestrating agent): the LLM-judge table stands, the 64 holds and the 7 process-time items are acknowledged."
re_verification:
  previous_status: human_needed
  previous_score: 114/115
  gaps_closed:
    - "Human item 1 / truth 10.9: 19-UAT test 11 records a direct 80x40 pseudo-terminal observation on an isolated scratch index at the operator's explicit request - 6/6 vsearch chunk rows and 5 query chunk rows each end with their own #0, the five document-level BM25 rows keep the plain path, and all four layouts are at most 80 display cells wide with a right border. The backstop truth is verified on direct observation, not on presence."
    - "Human item 2 / assumption A-19-10-1: 19-UAT test 12 confirms every clause of the shipped per-chunk machine-format layout (CSV, Markdown, XML, --files, unchanged default output) against the JSON of the same page."
    - "Human item 3 / 19-12 human check: 19-UAT test 13 passes on an isolated real-embedding index and on a copy of the operator's default index; the default index's lack of embedded chunks is recorded as an environment limit."
    - "Human item 4 / 19-14 human check: 19-UAT test 14 passes; the query and vsearch --min-score help texts state the per-leg floor and the never-compared fused score."
    - "Human item 5 / UAT record: 19-UAT.md is complete - 18/18 tests carry results (15 pass, 3 issue rows whose gaps G-19-8, G-19-9 and G-19-10 are resolved by plans 19-13, 19-14 and 19-15); no pending or blocked row; G-19-1 and G-19-2 are normalized."
    - "Human item 6 / prohibitions: 19-UAT test 16 accepts this report's LLM-judge table - 64 holds (including 19-03 P1) and the 7 process-time items are acknowledged."
    - "Human item 7 / validation audit: 19-UAT test 17 re-ran the audit; 19-VALIDATION.md now reads status: validated, nyquist_compliant: true, validated: 2026-11-27, with V19-26-1, V19-26-2 and V19-26-3 closed and all three mutation gates reproduced."
    - "Human item 8 / WR-01 and IN-01: 19-UAT test 18 fixes docs/changelog.md:24 per the review's wording; 19-REVIEW.md is clean (0 findings) after the incremental re-review of commit 5268218, and 19-REVIEW-DISPOSITION.md records both findings fixed."
  gaps_remaining: []
  regressions: []
advisory: []
---

# Phase 19: Search Correctness Verification Report

**Phase Goal:** Search results are fresh, deduplicated, deterministically paginable, and title-aware — the trust floor that metadata filtering (20) builds on, with every ranking-contract change measured before/after on the Phase 18 instrument.
**Verified:** 2026-11-27T12:10:19Z at HEAD `78aa088`
**Status:** passed
**Re-verification:** Yes — regeneration after the human checkpoint closed and the WR-01/IN-01 changelog fix landed

Method. The must-haves are the five Success Criteria of `### Phase 19` in `.planning/milestones/v1.2-ROADMAP.md` and the 115 functional truths in the frontmatter of the fifteen plans (63 from plans 19-01 to 19-09, 27 from plans 19-10 to 19-12, 25 from plans 19-13 to 19-15; `UNCLASSIFIED-FLAGGED` entries are excluded). This is a re-verification of the previous report at `b67b5dd` (`human_needed`, 114/115). The only non-planning diff between `b67b5dd` and HEAD is `docs/changelog.md` (1 insertion, 1 deletion, commit `5268218`), so the previously verified truths were regression-checked: every file they cite other than `docs/changelog.md` is byte-identical at HEAD, and the full suite and targeted Phase 19 gates are green. The changelog-citing truths (10.11, 13.7, 14.7 and 14.9) were re-checked against the current file, and the backstop truth 10.9 against 19-UAT test 11. This verifier also read all fifteen plans and summaries, `19-UAT.md`, `19-VALIDATION.md`, `19-REVIEW.md`, `19-REVIEW-DISPOSITION.md`, `19-SECURITY.md`, `19-CONTEXT.md` and `.planning/milestones/v1.2-REQUIREMENTS.md`. It ran the full suite (3320 passed, 1 skipped), the five-file plan-19-13 gate (253 passed), `TestPerChunkSurfaces` (33 passed), the three guard tests (4 passed), the MCP suite (306 passed), the docs/release/hygiene tests (51 passed), the docs tests (23 passed), both docs generators in an exported copy (byte-identical), the artifact and key-link checks, the decision-coverage gate (12/12), an anti-pattern scan over the 97 files of the previous report's covered set, the changelog released-region hash at four commits, the three `--help` texts, and the lint/format/type gates.

## Delta Since the Previous Report

Previous report: `b67b5dd`, 2026-11-27, `human_needed`, 114/115 (one backstop abstention and eight open human items). Since then:

| Range | Change | Effect here |
| ----- | ------ | ----------- |
| `b67b5dd..561b8a3` | Human checkpoint records committed: `cb7e77f` persists the human verification items as UAT, `561b8a3` completes UAT (15 pass, 3 resolved issue rows) | All eight human items are closed; truth 10.9 is verified by direct observation; the 3 issue rows are resolutions, not open gaps. |
| `561b8a3..5268218` | WR-01/IN-01 documentation fix: one `docs/changelog.md` line under `[Unreleased]` / `Changed` | The 19-14 truth-7 literal "value must not be converted" is superseded by a more accurate, scoped correction (scope note S7); the 19-14 artifact pattern is stale, while the artifact's substance is present and correct. |
| `5268218..5c811f1` | `19-VALIDATION.md` re-certified (`nyquist_compliant: true`, `validated: 2026-11-27`) and `19-REVIEW-DISPOSITION.md` updated (WR-01 and IN-01 fixed) | V19-26-1 to V19-26-3 closed; the validation report is no longer PARTIAL. |
| `5c811f1..78aa088` | Incremental code review of the changed changelog line | `19-REVIEW.md` is clean: 0 critical, 0 warning, 0 info. |

Non-planning files changed since the previous report: one (`docs/changelog.md`). The implementation diff is 1 insertion and 1 deletion; `src/`, `tests/`, the generated docs and the five benchmark artifacts are byte-identical to `b67b5dd`. All seven task commits of the second gap-closure round (`1ed9030`, `5ad35b1`, `0902b28`, `475ab82`, `a6412a0`, `0452dfb`, `f844c79`) are ancestors of HEAD, and the plan bases `54acb11`, `f5c0221`, `091d7a4` are recorded in `.git/gsd-plan-19-{13,14,15}-base`.

## Goal Achievement

### Roadmap Success Criteria

| # | Success Criterion | Status | Evidence at `78aa088` |
| --- | ----------------- | ------ | --------------------- |
| 1 | Frontmatter-only edits become searchable; parser dispatch + metadata-aware checksum in one plan and one migration; Markdown body byte-identical; YAML `---` bug fixed | ✓ VERIFIED | `models.py:42-71`, `parser.py:129-155,196-212`, `incremental.py:393`; full suite green. |
| 2 | One result per document by default; dedup inside `VectorSearcher` pre-fusion; `--per-chunk` escape hatch; ranking-contract change recorded with bench before/after and goldens with rationale | ✓ VERIFIED | `vector.py:296-323`, `hybrid.py:150-156,451-455`; `TestPerChunkSurfaces` 33/33 green; the three new guards mutation-gated in the previous pass; B0/B1 record n 100, mean 0.0, unchanged 100. |
| 3 | Deterministic pagination: CLI `--offset` and MCP offset; hybrid owns one slice; searchers return from rank 0; BM25 min_score order fixed; offset=0 reproduces the recorded contract | ✓ VERIFIED | `--offset` is `IntRange(min=0)` on all three commands (`search.py:625-630,833-838,1076-1081`); `rank=options.offset + position` (`bm25.py:202`); the displayed-score predicate is `abs(m.score) / (1.0 + abs(m.score)) >= ?` bound with `min_score` in both branches ahead of `LIMIT ? OFFSET ?` (`bm25.py:114-117,158,180`); five-file gate 253 passed. |
| 4 | Title-aware ranking: title-FTS migration, rewritten triggers, measured `bm25()` column weights, mtime index; `documents_fts_v` survives a rebuild | ✓ VERIFIED | `schema.py:497-630,769,802`; `bm25.py:105-107,145,167`; `TestWeightedBM25` green in the 59-test file; D-12 artifacts unchanged; the SC1 snapshot still passes under the declared 1 ULP tolerance. |
| 5 | No redundant attach work: exactly one context/staleness attach at pipeline exit | ✓ VERIFIED | `enrich_results` is called once per direct CLI exit (`search.py:730,996,998`) and once per pipeline exit (`hybrid.py:308-309,356`); `_attach_contexts` grep count under `src/sif` is 0; spy tests green in the full suite. |

**Score:** 5/5 roadmap success criteria verified.

### Observable Truths — Plans 19-01 to 19-09 (truths 1-63)

Wording and numbering follow the previous report; the files cited here are byte-identical to the previous report's verification point unless a status note says otherwise. The full suite exercises all of these.

#### Plan 19-01 — CORR-01

| # | Truth | Status | Evidence |
| --- | ----- | ------ | -------- |
| 1 | `.yaml`/`.yml` starting with `---` parsed whole by `CodeParser` | ✓ VERIFIED | `parser.py:129-155,196-212`; full suite green. |
| 2 | Checksum over body + NUL + canonical full frontmatter; frontmatter or body edit changes it, key reorder does not | ✓ VERIFIED | `models.py:42-71`; `parser.py` checksum path; tests green. |
| 3 | Markdown body path byte-identical | ✓ VERIFIED | `parser.py` Markdown path; tests green. |
| 4 | `date:` frontmatter stores and round-trips as canonical JSON | ✓ VERIFIED | `repositories.py` metadata bind; tests green. |
| 5 | `IncrementalIndexer` stores `parsed.checksum` | ✓ VERIFIED | `incremental.py:482`; tests green. |
| 6 | Unknown extension falls back to `TextParser` | ✓ VERIFIED | `incremental.py:393`; tests green. |

#### Plan 19-02 — CORR-01

| # | Truth | Status | Evidence |
| --- | ----- | ------ | -------- |
| 7 | `index_meta` with per-collection convention keys; `drop_all` removes it | ✓ VERIFIED | `schema.py` index_meta; `repositories.py`; tests green. |
| 8 | One forced re-parse pass per absent or old marker | ✓ VERIFIED (scope note S1) | `incremental.py:155-212`. |
| 9 | Metadata-only edit keeps chunks and embeddings | ✓ VERIFIED | `incremental.py:437-446`; tests green. |
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
| 20 | CLI `search` and `vsearch` call `enrich_results` exactly once and keep context and staleness in the output | ✓ VERIFIED | `search.py:730,996,998`; `TestSingleEnrichmentOwner` green. |
| 21 | MCP BM25 fallback enriches once; pipeline output is not enriched again | ✓ VERIFIED | `backend.py:490,501,534`. |
| 22 | MCP re-map forwards `rank`, `collection_name`, `vectors_stale` | ✓ VERIFIED | `backend.py:189-197`. |
| 23 | B0 saved run: 100 queries, bm25, zero mean delta | ✓ VERIFIED | `bench/b0.json` unchanged; the zero-threshold path is unchanged and the B0 comparison is recorded identically on both sides of 19-13. |

#### Plan 19-05 — CORR-03

| # | Truth | Status | Evidence |
| --- | ----- | ------ | -------- |
| 24 | `--offset` (`IntRange(min=0)`, default 0) on `search`, `vsearch`, `query`; past the end is an empty page | ✓ VERIFIED | `search.py:625-630,833-838,1076-1081`; CLI probe. |
| 25 | `rank = offset + position` | ✓ VERIFIED | `bm25.py:202`; `vector.py:248-251`; `hybrid.py:55-67`. |
| 26 | `limit=l offset=o` equals the `[o:o+l]` slice of one request, on BM25, vector and hybrid | ✓ VERIFIED | `TestConsistentPagination` green. |
| 27 | BM25 applies `min_score` before LIMIT/OFFSET by comparing the displayed score itself: `AND abs(m.score) / (1.0 + abs(m.score)) >= ?` bound with `min_score` as given; omitted when not above 0; 1+ returns no row (amended 2026-11-27 by plan 19-13) | ✓ VERIFIED | Current `19-05-PLAN.md` truth 4; `bm25.py:114-117,158,180,202`. Trace/parameter order tests green; 84-row sweep (previous pass); five-file gate 253 passed. |
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
| 36 | Per-chunk mode returns ungrouped chunk rows; both fuses keyed by `fuse_key_for`; BM25 rows document-keyed | ✓ VERIFIED | `rrf.py:20-28`; `hybrid.py:150-156,451-455`. |
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
| 44 | Generated docs clean; CLI reference documents `--offset` and `--per-chunk` | ✓ VERIFIED | Both generators run in an exported copy: `docs/cli-reference.md` and `docs/configuration.md` byte-identical. |
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
| 52 | `SearchOptions.title_weight` override is internal only | ✓ VERIFIED | `models.py:377`; `bm25.py:105-107,121`. |
| 53 | SC1 golden and held-out snapshot carry a rationale | ✓ VERIFIED | `test_hybrid.py:797-808` plus the quick-s23 1 ULP tolerance (declared); full suite green. |
| 54 | No CJK lexical title win claimed | ✓ VERIFIED | `docs/benchmarking.md:255-257`. |

#### Plan 19-09 — CORR-04

| # | Truth | Status | Evidence |
| --- | ----- | ------ | -------- |
| 55 | `idx_documents_mtime` on fresh and migrated DBs | ✓ VERIFIED | `schema.py:769`. |
| 56 | MCP-only process runs the schema migration once at startup | ✓ VERIFIED | `backend.py:290-293`. |
| 57 | Per-leg and per-leg×split noise gates in `--compare` | ✓ VERIFIED | `personal_bench.py:471-546`; prior probe reproduced. |
| 58 | Title-weight sweep opens the index through `init_schema()` and requires a title column | ✓ VERIFIED (not re-run) | `.planning/tmp/phase19/sweep_title_weight.py` present, untracked; unchanged by this round. |
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
| 10.5 | Per-chunk Markdown and XML chunk rows carry the address and sequence; document-level rows get neither | ✓ VERIFIED | `search.py:532-605`; guarded by `test_per_chunk_markdown_and_xml_give_a_document_level_row_no_sequence` (V19-26-1); the formatter mutation fails it. |
| 10.6 | Without `--per-chunk`, CSV, Markdown and XML are unchanged | ✓ VERIFIED | Prior differential check (864 comparisons, 0 mismatches); the formatter code is unchanged by this round; full suite green. |
| 10.7 | `--files` and quiet path-only output list each path once; limits count chunk rows; default output unchanged | ✓ VERIFIED | `search.py:276-278,1001,1338`; `test_per_chunk_files_and_quiet_list_each_path_once` and `test_per_chunk_path_only_page_counts_chunk_rows` green. |
| 10.8 | `test_per_chunk_table_renders_path_sequence` passes unchanged; render tests were red against base | ✓ VERIFIED | Function text byte-identical to the base; red derivations recorded and unchanged by 19-15 (which only inserted new tests). |
| 10.9 | On a real 80-column terminal, against a live index with embedded chunks, every chunk row shows `#sequence` and no table line is cropped | ✓ VERIFIED (backstop, directly observed in UAT test 11) | 19-UAT test 11, at the operator's explicit request on 2026-11-27 (delegated verdict): 80x40 pseudo-terminal, isolated scratch index; vsearch 6/6 chunk rows end with `#0`; query shows 5 chunk rows with `#0` plus 5 document-level BM25 rows with the plain path; all four layouts are at most 80 display cells and end at the right border; a rank-by-rank cross-check against `--json` confirms every cell, Title and Collection. The 33 render tests and the prior verifier's PTY render agree. |
| 10.10 | All four layouts end at their right border within 80 cells with snippet text, Rich 14.3.3 and 15.0.0 | ✓ VERIFIED | Green under both Rich versions; prior measurements unchanged. |
| 10.11 | `docs/changelog.md` carries one per-chunk output entry under `[Unreleased]` / `Changed` | ✓ VERIFIED | The entry landed in `[1.2.4]` at release (`docs/changelog.md:44-46`); the released text is intact; the Unreleased entry count is 1. |

#### Plan 19-11 — CORR-03 (G-19-2 before-evidence and decision)

| # | Truth | Status | Evidence |
| --- | ----- | ------ | -------- |
| 11.1 | The artifact records the probe rows, two threshold outcomes, B0/B1 deltas and the empty hybrid BM25 leg from the unchanged base tree | ✓ VERIFIED | `bench/g19-2-min-score.json` unchanged; prior report reproduced every value against the base searcher; file hash unchanged. |
| 11.2 | No `after` half while the plan ran; the decision is the pending marker, then the id named at the checkpoint | ✓ VERIFIED | Git: `043db46` pending marker, `dbb82b5` `monotone-map`, one-line diff. |
| 11.3 | No file outside `.planning/` changes in this plan | ✓ VERIFIED | Empty diff against the plan base. |
| 11.4 | A `checkpoint:decision` with three options, no `auto_select`, `blocking-human`, no implementation task | ✓ VERIFIED | `19-11-PLAN.md`; options `monotone-map`, `describe-current`, `deprecate-flag`; plan unmodified since planning. |
| 11.5 | A measurement that differs from the pins stops the plan; nothing is edited to agree | ✓ VERIFIED (as far as observable) | Stop rule and validator present; artifact before half identical across revisions; plan unmodified. |
| 11.6 | The operator's choice is recorded in the artifact and on a `Decision:` line and cannot be re-derived from the tree | ✓ VERIFIED (19-UAT test 7) | `decision: "monotone-map"` in the artifact and `Decision: monotone-map` in `19-11-SUMMARY.md`; 19-UAT test 7 records the operator's answer and is `performed_by: operator`. |

#### Plan 19-12 — CORR-03 (G-19-2 implementation)

| # | Truth | Status | Evidence |
| --- | ----- | ------ | -------- |
| 12.1 | Displayed score is `|bm25|/(1+|bm25|)` through `bm25_display_score`, rising with relevance; `search_chunks` uses it | ✓ VERIFIED | `bm25.py:47-57,209,252`; `test_search_chunks_scores_use_the_display_map` pins `search_chunks` on a real FTS5 chunk index; guard green. |
| 12.2 | `--min-score M` binds `m.score <= ?` with `-M/(1-M)`; a row at exact equality is dropped in a fraction of cases | ✓ VERIFIED (superseded clause — scope note S5) | Superseded by 19-13: the bound and the equality drop are gone; the rest (0/negative/NaN omit; 1+ returns no row) holds and is tested. 19-13 T8 records the supersession; 19-12 stays unedited. |
| 12.3 | Filter before pagination, bound parameters only, no holes, global ranks, filters compose | ✓ VERIFIED | `test_filters_sql.py` and `test_min_score_applies_before_offset_with_global_ranks` green; parameter order `[weights, query, collection, min_score, filters, limit, offset]`. |
| 12.4 | Hybrid ranking unchanged without a threshold; B0/B1 n 100, mean 0.0 | ✓ VERIFIED | `hybrid.py`/`rrf.py` unchanged; artifacts record the deltas; at min_score 0 the predicate is omitted, so the path is unchanged. |
| 12.5 | SC1 golden's two `bm25_score` values regenerated; order/RRF/vector scores and held-out snapshot unchanged; dated rationale | ✓ VERIFIED | Golden values in `test_hybrid.py`; snapshot unchanged; rationale present; full suite green. |
| 12.6 | Six tests re-pinned; the zero-threshold negative assertion names the new predicate; red runs observed | ✓ VERIFIED | `test_bm25.py` re-pins; the base-searcher mutation fails the five named behavioural tests (previous pass). |
| 12.7 | Help text, regenerated CLI reference, changelog, dated notes and the amended fourth truth of `19-05-PLAN.md`; that plan differs in exactly one line | ✓ VERIFIED (historical; 19-13 added its own one-line amendment) | The 19-12 entry is in the released `[1.2.4]` section; its wording, generated row and dated note are present. `19-05-PLAN.md` differs from 19-12's base by two amendments, the second recorded by 19-13 T7; current numstat `1 1`. |
| 12.8 | `sif query --min-score` changes in its BM25 leg only and keeps its help text; `TestHybridMinScoreLeg` pins it; MCP `query` shares the path | ✓ VERIFIED (help-text clause superseded — scope note S6) | The BM25-leg behaviour and `TestHybridMinScoreLeg` hold; the help text changed on purpose in 19-14, which records the supersession in its T9. |
| 12.9 | `sif vsearch --min-score` keeps its behaviour and help text; `vector.py` untouched | ✓ VERIFIED (help text now names vector similarity, 19-14) | `vector.py` unchanged; `test_search_applies_min_score` green; the behaviour is unchanged and 19-14 T3/T9 record the text update. |
| 12.10 | The operator's choice at the 19-11 checkpoint authorises this change | ✓ VERIFIED (19-UAT test 7) | Same record as 11.6; both records predate the first 19-12 commit. |

### Observable Truths — Second Gap-Closure Round 19-13 to 19-15

#### Plan 19-13 — CORR-03 (G-19-8 / IN-09)

| # | Truth | Status | Evidence |
| --- | ----- | ------ | -------- |
| 13.1 | `sif search search --min-score M` keeps every match whose displayed score is at least M to the last bit; a `--json` score passed back is kept with the same score and rank; MCP `lex_search` and the hybrid BM25 legs behave the same | ✓ VERIFIED | `test_the_cli_keeps_a_row_at_its_own_displayed_score` and `test_every_bench_row_survives_its_own_displayed_score` green in this pass's 253-test five-file gate; live probe and 84-row sweep reproduced in the previous pass; MCP `lex_search` and the hybrid legs call the same `BM25Searcher.search` (`backend.py:600-609,461`; `hybrid.py:121-128`). |
| 13.2 | The predicate compares the displayed score in SQL, bound with `min_score` itself, in the outer WHERE of both branches ahead of filters and `LIMIT ? OFFSET ?`; the expression is the weighted `bm25()` value; nothing is interpolated | ✓ VERIFIED | `bm25.py:114-117,142-183`: `min_score_filter` is the constant fragment, appended after collection ids and before filter params; both branches place it before `LIMIT ? OFFSET ?`. `test_min_score_binding_table` and `TestBm25ParamOrder` green. |
| 13.3 | The predicate is omitted when `min_score` is not above 0 (0, negative, NaN); 1 or more keeps no row by arithmetic; 1, 2.5 and infinity are tested | ✓ VERIFIED | `if options.min_score > 0` (`bm25.py:115`); `test_values_not_above_zero_keep_every_row` (0, -0.5, NaN) and `test_min_score_at_or_above_one_keeps_nothing` (1.0, 2.5, inf) green; live probe (previous pass): NaN keeps both rows, 1 keeps none. |
| 13.4 | The SQL expression and `bm25_display_score` agree bit for bit over 100,189 finite doubles; signed zero and infinity are the only exceptions and cannot come from a matching row | ✓ VERIFIED | `_score_expression_sample()` yields 100,189 finite values; `test_sql_score_expression_matches_the_display_map_bit_for_bit` green; the caveat is stated in the test. |
| 13.5 | Nothing else moves: displayed scores, one-ULP outcomes, fixed-threshold counts and B0/B1 deltas are identical before and after; only the count dropped at own score changes 40 -> 0 | ✓ VERIFIED | `bench/g19-8-exact-threshold.json` pins both sides (heads `54acb11`/`1ed9030`); the previous pass reproduced the after half (84 rows, 84 kept at own score, 84 one float step below, 84 dropped one step above, fixed counts `84/84/84/84/70/70`) and the before half by mutation; `bm25.py` is unchanged since the prior pass; B0/B1 paths unchanged at min_score 0. |
| 13.6 | The threshold helper and its table test are gone; the tests state the contract on SQL text, real rows in both branches at two title weights, and edge values; red runs observed; the base searcher fails the behavioural cases by name | ✓ VERIFIED | `bm25_rank_threshold` grep 0 in `src/` and `tests/`; `_MIN_SCORE_PREDICATE` and `TestExactMinScore` present; the previous pass's base-searcher mutation fails exactly the two CLI tests plus `[scoped]`, `[unfiltered]` and `[weight-10]`; five-file gate 253 passed in this pass. |
| 13.7 | The changelog records the fix under `[Unreleased]`/`Fixed`, names 1.2.4 and the four-decimal limit; released sections are byte-identical; `19-05-PLAN.md` is amended once more, one line, keeping its 19-12 note | ✓ VERIFIED | `docs/changelog.md:33` phrase count 1; the released region from `## [1.2.4]` to EOF hashes identically at `54acb11`, `f5c0221`, `b67b5dd` and HEAD (`2d6ad7dc...`); `19-05-PLAN.md` numstat `1 1`; both dated notes appear once and the predicate once. |
| 13.8 | 19-12's two records stay unedited; the `search --min-score` promise now holds exactly; 19-12's gate 2 reads 250 and this plan's gate 252 at its completion | ✓ VERIFIED | `19-12-PLAN.md` unchanged; help promise true (live probe at exact equality, previous pass); the same gate reads 253 after 19-15, as its T6 records. |
| 13.9 | On an index of the checker's own choosing, a row survives `--min-score` equal to its `--json` score and keeps its rank | ✓ VERIFIED (backstop, directly observed) | The previous pass built a scratch BM25 index from `tests/fixtures/bench/corpus` and ran the real CLI: own score kept rank 1 at the same score; one float step below kept; one float step above dropped. The code is byte-identical at HEAD; the CLI test file is green in this pass. |

#### Plan 19-14 — CORR-03 (G-19-9 / IN-10)

| # | Truth | Status | Evidence |
| --- | ----- | ------ | -------- |
| 14.1 | `sif search query --min-score` behaves exactly as before: `HybridSearcher.search` copies `min_score` into both legs; each leg filters on its own score; the fused score is never compared; one empty leg returns its own page; the three searcher modules are byte-identical to the plan base; tests pass unchanged | ✓ VERIFIED | `git diff f5c0221..HEAD` over `hybrid.py`, `vector.py`, `bm25.py` is empty; `hybrid.py:121-166`; `TestHybridMinScoreLeg` and `test_search_applies_min_score` green; A-19-9-1 is confirmed by the operator on 2026-11-27. |
| 14.2 | The `query` help text is the per-leg statement | ✓ VERIFIED | `search.py:1091-1100`; `sif search query --help` shows it; literal equality test green. |
| 14.3 | The `vsearch` help text names vector similarity; the `search` help is the 19-12 text | ✓ VERIFIED | `search.py:848-855` and `:640-647`; `--help` output confirmed this pass. |
| 14.4 | Both texts are what `--help` shows and what `make docs-generate` writes; only the two `--min-score` rows change; `docs/configuration.md` byte-identical; the old wording appears nowhere in the source or MCP page | ✓ VERIFIED | Both generators run in an exported copy this pass: `docs/cli-reference.md` and `docs/configuration.md` byte-identical; `cli-reference` rows at `:495,538,573`; `Minimum score threshold` count 0 in `search.py` and `docs/mcp-server.md`. |
| 14.5 | `docs/mcp-server.md` names the score each MCP tool's `min_score` filters | ✓ VERIFIED | `docs/mcp-server.md:134` (query), `:188` (lex), `:195` (vec); test green. |
| 14.6 | Two tests pin the texts against the Click commands, the generated reference and the MCP page; each was red before its edit | ✓ VERIFIED | `tests/test_docs.py`; both green (23 docs tests passed this pass); the previous pass mutated the old query text and the old MCP row and each mutation failed its test (1 failed, 22 passed). |
| 14.7 | The changelog records the query behaviour and the conversion correction under Unreleased; the released entry stays as released | ✓ VERIFIED (scope note S7) | `docs/changelog.md:24` now says the per-leg filtering semantics are unchanged, that this release only documents them in the help text, that the exact-equality fix reaches the command's BM25 leg, and scopes the conversion correction to `sif search search` and BM25-only routes (with the hybrid-query caveat). The plan's literal "value must not be converted" was corrected by the WR-01/IN-01 fix (commit `5268218`, UAT test 18; `19-REVIEW.md` clean). The released region from `## [1.2.4]` to EOF hashes identically at `54acb11`, `f5c0221`, `b67b5dd` and HEAD. |
| 14.8 | The MCP wire is untouched: modules and goldens byte-identical; the 306 MCP tests pass; `min_score` publishes no description | ✓ VERIFIED | `git diff f5c0221..HEAD` over `src/sif/mcp` and the five goldens is empty; this pass ran 306 MCP tests, all passed; the golden schema carries no description. |
| 14.9 | 19-12's truth-8 clause and Task-3 gate-1 counts are superseded and stay unedited; after this plan the old wording count is 0 and `stronger match` is 3 | ✓ VERIFIED | `19-12-PLAN.md` unchanged; counts 0 and 3 confirmed this pass. |
| 14.10 | Review item R2-03 is closed in full; R2-04 and R2-01 are unchanged and open | ✓ VERIFIED | The new texts name the compared score; four-decimal display remains (R2-04); the band is still not stated (R2-01). `19-UI-REVIEW.md` remains the historical audit. |

#### Plan 19-15 — CORR-02 / CORR-03 (G-19-10 / V19-26-1 to V19-26-3)

| # | Truth | Status | Evidence |
| --- | ----- | ------ | -------- |
| 15.1 | A test renders the five-row per-chunk page with `--md` and `--xml` and asserts the document-level row keeps the plain path and no sequence, while exactly four chunk rows carry it | ✓ VERIFIED | `test_per_chunk_markdown_and_xml_give_a_document_level_row_no_sequence` green in this pass's guard run; the formatter mutation fails it (previous pass). |
| 15.2 | A test renders `/notes/[red]evil[/red].md` and `/notes/[/3]-review.md` in both per-chunk tables at 200 columns, asserting exit 0 and a Chunk cell of `path#0` | ✓ VERIFIED | Parametrized test green; `Text.from_markup` and plain-string mutations each fail both cases (previous pass). |
| 15.3 | A test runs `search_chunks` on a real FTS5 chunk index with raw values about -4.72 and -0.77 and asserts each score equals `bm25_display_score` and falls with rank | ✓ VERIFIED | `_build_chunk_fts_db()` produces `[-4.716163782783036, -0.7732687035694134]`; test green; reciprocal-map mutation fails only the new test (previous pass). |
| 15.4 | Each test fails without the behaviour, proven by a mutation gate at execution time; the document-level test fails when the formatters give a sequence; the markup test fails under bare string and `Text.from_markup`; the score-map test fails under the earlier reciprocal map | ✓ VERIFIED | All three mutations reproduced in the previous pass with the exact failure modes and counts; this pass re-ran the guards (4 passed) and the validation audit's own re-run records them closed. |
| 15.5 | The UAT example name `r[3]eview-notes (v2).md` is not used; Rich does not parse it as markup | ✓ VERIFIED | Tests use the two markup-bearing paths; the plan's Rich tag rule is correct. |
| 15.6 | No source file changes: outside `.planning/` exactly the two test files differ; `TestPerChunkSurfaces` holds 33 tests and `test_bm25.py` 59; the full suite, lint and docs tests pass; 19-13's gate reports 253 | ✓ VERIFIED | `git diff 091d7a4..HEAD` outside `.planning` is exactly the two files; collect-only reports 33 and 59 this pass; five-file gate 253 passed; full suite 3320 passed, 1 skipped; ruff/format clean. |

**Score:** 115/115 plan truths verified: 115 VERIFIED (63 from plans 19-01 to 19-09, 27 from plans 19-10 to 19-12, 25 from plans 19-13 to 19-15), 0 failed, 0 present-behavior-unverified, 0 insufficient_spec. No truth is UNCERTAIN: truths 17 and 34 are accepted by 19-UAT test 5 (scope notes S2/S4), and the backstop truth 10.9 is verified by 19-UAT test 11's direct observation.

### Scope Notes (literal wording vs HEAD)

| Note | Truth | Clause read literally | What HEAD does | Recorded decision |
| --- | --- | --- | --- | --- |
| S1 | 8 | marker written "only when zero files failed" | written when no stored document failed | Phase's own review fix WR-01 |
| S2 | 17 | "one batched `document_embeddings` scan" | one indexed lookup per result on `embedded_documents` (Phase 21) | 19-UAT test 5 (2026-11-26), at the operator's explicit request; reversible |
| S3 | 31, 42 | "hand-written query schema" | signature-derived schema (Phase 22) | prior report's adjudication |
| S4 | 34 | start `min(max(target*4,50),2048)` | selectivity-seeded window on scoped searches (Phase 20) | 19-UAT test 5 (2026-11-26), at the operator's explicit request; reversible |
| S5 | 12.2 | bound `-M/(1-M)` with `m.score <= ?`; equivalence drops a fraction of rows | displayed-score predicate bound with `min_score`; equality kept | 19-13 T8 supersedes the boundary sentence; 19-12 unedited |
| S6 | 12.8, 12.9 | `query` keeps its "Minimum score threshold" help text; `vsearch` text unchanged | both now name the compared score | 19-14 T9 supersedes the truth-8 clause; T3/T9 record the text updates |
| S7 | 14.7 | "a `sif search query --min-score` value must not be converted" (unconditional) | conversion applies to `sif search search` and to BM25-only routes (`lex:` prefix or a `bm25` default); on a hybrid query, do not convert a value that also thresholds the vector leg | WR-01/IN-01 fix in `5268218`, recorded by 19-UAT test 18; `19-REVIEW.md` clean (0 findings). The corrected text is accurate; the literal was overbroad. |

Truth 27 is no longer a scope note: the fourth truth of `19-05-PLAN.md` was amended twice in place (19-12, then 19-13), and the code matches the current amendment.

### Adjudications

**A. Exact `--min-score` (UAT test 8, G-19-8, IN-09) — fixed and reproduced.** The predicate compares the displayed score itself and binds `min_score` as given (`bm25.py:114-117,158,180`). The previous pass reproduced the contract live (own score kept rank 1 at the same score; one float step below kept; one float step above dropped; `--min-score 1` empty; `--min-score nan` keeps all) and the 84-row after-half sweep (0 rows dropped at their own score; fixed counts `84/84/84/84/70/70`). This pass's five-file gate, which includes `test_search_exact_threshold.py`, passes 253/253; `bm25.py` is byte-identical to the previous pass. The prior blocking boundary item is closed.

**B. Per-chunk identity (UAT tests 1 and 3, G-19-1) — built under an assumption now confirmed.** The table keeps `#sequence` at 80 columns, and the machine formats and path-only output carry the identity as A-19-10-1 describes. The assumption still reads `status: pending plan review` in `19-10-PLAN.md:19` (an info-level planning-record note, not a code gap), but 19-UAT test 12 confirms every clause of the shipped layout against the same page's `--json`: CSV header and rows, Markdown and XML chunk/document rows, `--files` uniqueness, and unchanged default output. Truth 10.9 is verified by UAT test 11's direct 80-column PTY observation at the operator's explicit request.

**C. `sif query --min-score` (UAT test 9, G-19-9, IN-10) — documented, not redesigned.** The operator confirmed A-19-9-1 on 2026-11-27: keep the per-leg floor and describe it. The CLI help (`search.py:1091-1100`), generated reference (`:495`), MCP page (`:134,188,195`) and changelog now say which score each leg filters and that the fused score is never compared. UAT test 9's restatement note is recorded; UAT test 13 passes the operator-index check on an isolated real-embedding index and a copy of the operator's default index (the default index has no embedded chunks, recorded); UAT test 14 passes the help-text comprehension check.

**D. The three unguarded behaviours (UAT test 10, G-19-10, V19-26-1 to V19-26-3) — guarded and mutation-proven.** All three guards are green in this pass (4 cases); the validation audit's 2026-11-27 re-run reproduced every mutation gate on a throwaway worktree: the formatter mutation fails the document-level test, both markup mutations fail both path cases, and the reciprocal-map mutation fails only the new `search_chunks` test. `19-VALIDATION.md` is re-certified with `nyquist_compliant: true` and V19-26-1 to V19-26-3 closed.

**E. Review findings of this round — both documentation wording, both fixed.** WR-01 (the Unreleased Changed entry gave a baseline that contradicted the Fixed entry) and IN-01 (the conversion correction was overbroad for BM25-only `query` routes) were fixed in `docs/changelog.md:24` by `5268218`. `19-REVIEW.md` re-reviewed that file and found 0 issues; its summary verifies each branch against the code (`hybrid.py` `lex:` and `bm25` routing, the hybrid vector-leg caveat, and the unchanged vector scale). `19-REVIEW-DISPOSITION.md` records both fixed. No code or must-have is affected.

**F. Human checkpoint complete — all prior human items closed.** `19-UAT.md` is `status: complete`, 18/18 tests with results (15 pass; tests 8, 9 and 10 remain `result: issue` only because they record the originally observed defects, and their gaps G-19-8, G-19-9 and G-19-10 are `status: resolved` with `resolved_by` 19-13/14/15 and matching summaries). No pending, skipped or blocked row. The operator delegated the remaining checkpoints to the orchestrating agent on 2026-11-27 ("you test it and give the verdict"), so every `performed_by` caveat is confirmed in that form; the operator has not personally run them and can still reverse any verdict. The 71 judgment-tier prohibitions were accepted at the end-of-phase checkpoint in UAT test 16 (64 hold including 19-03 P1; the 7 process-time items acknowledged).

**G. Changelog literal superseded — S7.** The 19-14 plan's truth 7 and artifact `contains: value must not be converted` predate the review finding IN-01. The fix scopes the correction correctly: subtract-from-1 applies to `sif search search` and to BM25-only `query` routes (`lex:` prefix or `bm25` default), and a hybrid `query` value that also thresholds the vector leg should not be converted because the vector similarity scale did not change. The artifact exists and states the correction; `verify.artifacts` reports 4/5 for 19-14 on the stale literal, not on a missing or stub artifact. The released `[1.2.4]` region is byte-identical at four commits.

### Deferred Items

None.

### Advisory (New Scope, Unevidenced)

None. Every finding raised this pass is backed by a command and its output, and no new-scope finding was promoted to a blocker.

## Required Artifacts

`verify.artifacts` passes 7/7 (19-13), 4/5 (19-14) and 2/2 (19-15). The one 19-14 failure is the stale plan literal described in S7, not a missing artifact. The earlier plans' known exceptions are unchanged: `src/sif/mcp/handlers.py` was deleted in Phase 22 (its property verified at its successor), the three bench JSON files of the earlier plans are declared under the pre-archive prefix and exist at `.planning/milestones/v1.2-phases/…/bench/`, one dotted export in 19-12 is a tool-matching limit while the method exists at `bm25.py:67`, and 19-13 deliberately removed `bm25_rank_threshold` and its table test (truth 13.6), so the 19-12 artifact row reports those two exports missing by design. No declared artifact is missing from the tree, and none is a stub or unwired; the one 19-14 tool failure is the superseded literal described above.

| Artifact | Expected | Status | Details |
| -------- | -------- | ------ | ------- |
| `src/sif/search/bm25.py` | Displayed-score predicate bound with `min_score` in both branches; threshold helper removed | ✓ VERIFIED | `bm25_display_score` at `:47-57`; predicate `:114-117`; `bm25_rank_threshold` grep 0; five-file gate green. |
| `tests/unit/cli/test_search_exact_threshold.py` | UAT test 8 through the real CLI and the 56-query sweep | ✓ VERIFIED | Both tests green in the 253-test gate; red against the base-like searcher (previous pass). |
| `tests/unit/search/test_bm25.py` | Re-pinned and new searcher tests, bit-for-bit SQL check | ✓ VERIFIED | 59 tests collected; `TestExactMinScore`; 100,189-value sample; mutation-red (previous pass). |
| `tests/unit/search/test_filters_sql.py` | Parameter order with `min_score` bound as given | ✓ VERIFIED | Green; constant predicate text asserted. |
| `bench/g19-8-exact-threshold.json` | Before/after sweep, probe and B0/B1 deltas | ✓ VERIFIED | Values reproduced on the after side; before side reproduced by mutation (previous pass). |
| `19-05-PLAN.md` | Fourth truth amended a second time | ✓ VERIFIED | Numstat `1 1`; both dated notes. |
| `docs/changelog.md` | Fixed entry for the exact threshold; Unreleased Changed entry and conversion correction | ✓ VERIFIED (substance; S7) | Fixed entry at `:33`; Changed entry at `:24` states the per-leg contract and the scoped conversion correction; the plan's literal `value must not be converted` is superseded, so the tool reports 4/5 for 19-14. Released region byte-identical. |
| `src/sif/cli/commands/search.py` | `query`/`vsearch` help texts; `search` text untouched | ✓ VERIFIED | `:640-647,848-855,1091-1100`; `--help` output matches. |
| `docs/cli-reference.md` | Regenerated rows for both options | ✓ VERIFIED | Generator output byte-identical; rows `:495,538,573`. |
| `docs/mcp-server.md` | Query row and lex/vec sentences name the score | ✓ VERIFIED | `:134,188,195`. |
| `tests/test_docs.py` | Two tests pinning the texts | ✓ VERIFIED | Green (23 docs tests); mutation-red (previous pass). |
| `tests/unit/cli/test_search.py` | Document-level row and markup-bearing Chunk cell guards | ✓ VERIFIED | Two new tests (three cases); green in the 33-test class; mutation-red (previous pass). |
| `tests/unit/search/test_bm25.py` | `search_chunks` score-map guard and builder | ✓ VERIFIED | `_build_chunk_fts_db`; test green; mutation-red (previous pass). |
| The 24 artifacts of the previous report unchanged (`models.py`, `parser.py`, `incremental.py`, `watcher.py`, `repositories.py`, `schema.py`, `database.py`, `vector.py`, `hybrid.py`, `rrf.py`, `context_attach.py`, `staleness.py`, `rerank.py`, `personal_bench.py`, `index.py`, `eval.py`, `protocol.py`, `tools.py`, `backend.py`, `b0.json`, `b1.json`, `d12-verdict.json`, `test_schema_title_fts.py`, `heldout_defaults.json`) | — | ✓ VERIFIED (regression) | Byte-identical to `b67b5dd`; full suite green. |

## Key Link Verification

`verify.key-links` passes 4/4 (19-13), 2/2 (19-14) and 2/2 (19-15). The earlier plans' file-valued tool false positives are unchanged; each was checked at the call site in the previous report and those files are byte-identical at HEAD.

| From | To | Via | Status | Details |
| ---- | -- | --- | ------ | ------- |
| `src/sif/cli/commands/search.py` | `src/sif/search/bm25.py` | `search_cmd` passes `min_score` into `SearchOptions`; the searcher binds it | ✓ WIRED | `min_score=min_score`; live probe (previous pass). |
| `tests/unit/cli/test_search_exact_threshold.py` | `src/sif/search/bm25.py` | reads `--json` scores and passes them back | ✓ WIRED | Green; red on the old bound (previous pass). |
| `tests/unit/search/test_bm25.py` | `src/sif/search/bm25.py` | `_MIN_SCORE_PREDICATE` asserted in SQL and evaluated bit-for-bit | ✓ WIRED | Green. |
| `bench/g19-8-exact-threshold.json` | `bench/b0.json` | B0/B1 comparison deltas | ✓ WIRED | Identical on both sides. |
| `tests/test_docs.py` | `search.py` / `docs/cli-reference.md` | `_option_help` reads the Click option; the test compares it with the generated row | ✓ WIRED | Green; mutation-red (previous pass). |
| `search.py` | `docs/cli-reference.md` | generator writes each option's help | ✓ WIRED | Generator idempotent this pass. |
| `tests/unit/cli/test_search.py` | `search.py` | real per-chunk commands reach the Markdown/XML formatters and `_ChunkAddress` | ✓ WIRED | Green; mutation-red (previous pass). |
| `tests/unit/search/test_bm25.py` | `bm25.py` | `search_chunks` on `_build_chunk_fts_db()` compared with `bm25_display_score` | ✓ WIRED | Green; mutation-red (previous pass). |

**Wiring:** 8/8 new connections verified; the 21 links of the previous report are unchanged.

## Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
| -------- | ------------- | ------ | ------------------ | ------ |
| `src/sif/search/bm25.py` | `score` and the threshold predicate | `bm25(documents_fts, ?, ?)` in the same materialized CTE; `min_score` bound from `SearchOptions` | Yes — live CLI rows match the artifact; 84-row sweep reproduced in the previous pass; five-file gate green | ✓ FLOWING |
| `src/sif/cli/commands/search.py` | `results` -> table, CSV, Markdown, XML, paths | searcher rows enriched at entry | Yes — tests render real stand-in pages through the real commands; live CLI probe (previous pass) | ✓ FLOWING |
| `bench/g19-8-exact-threshold.json` | before and after halves | base-searcher copy and checkout through the real CLI/searcher | Yes — after half reproduced; before half reproduced by mutation (previous pass) | ✓ FLOWING |
| `tests/unit/search/test_bm25.py` `_build_chunk_fts_db` | raw chunk bm25 values | real in-memory FTS5 index | Yes — `[-4.716163782783036, -0.7732687035694134]` | ✓ FLOWING |

## Behavioral Spot-Checks

Checks marked "this pass" were run by this verifier at `78aa088`; checks marked "carried" were run by the previous verifier at `b67b5dd` on files that are byte-identical at HEAD.

| Behavior | Command | Result | Status |
| -------- | ------- | ------ | ------ |
| Full suite | `python3 -m pytest -p no:cacheprovider --no-cov -q` | 3320 passed, 1 skipped in 117.12 s | ✓ PASS (this pass) |
| Five-file plan-19-13 gate | `pytest test_bm25.py test_search_min_score.py test_filters_sql.py test_hybrid.py test_search_exact_threshold.py` | 253 passed in 1.41 s | ✓ PASS (this pass) |
| `TestPerChunkSurfaces` | `pytest tests/unit/cli/test_search.py::TestPerChunkSurfaces` | 33 passed in 0.81 s | ✓ PASS (this pass) |
| Three validation guards | the document-level, markup and `search_chunks` score-map tests | 4 passed in 0.07 s | ✓ PASS (this pass) |
| MCP suite | `pytest tests/unit/mcp` | 306 passed in 17.05 s | ✓ PASS (this pass) |
| Docs/release/hygiene | `pytest tests/test_docs.py tests/test_release_metadata.py tests/test_hygiene.py` | 51 passed in 0.77 s | ✓ PASS (this pass) |
| Docs tests alone | `pytest tests/test_docs.py` | 23 passed in 0.69 s | ✓ PASS (this pass) |
| Docs generator | both generators in an exported copy | `docs/cli-reference.md` and `docs/configuration.md` byte-identical; exit 0 | ✓ PASS (this pass) |
| `--help` texts | `python -m sif.cli.main search query/vsearch/search --help` | all three expected texts shown | ✓ PASS (this pass) |
| Released changelog region | hash `## [1.2.4]`..EOF at `54acb11`, `f5c0221`, `b67b5dd`, HEAD | all four `2d6ad7dc...` | ✓ PASS (this pass) |
| Changelog phrase counts | `Minimum score threshold` in `search.py`/`docs/mcp-server.md`; `stronger match` in `search.py` | 0 and 3 | ✓ PASS (this pass) |
| Artifact checks | `verify.artifacts` for 19-13/14/15 | 7/7, 4/5 (S7 literal), 2/2 | ✓ PASS (with S7 note) |
| Key-link checks | `verify.key-links` for 19-13/14/15 | 4/4, 2/2, 2/2 | ✓ PASS (this pass) |
| Decision coverage | `check.decision-coverage-verify` | 12/12 honored, 0 not honored | ✓ PASS (this pass) |
| Anti-pattern scan | debt markers over the 97 covered files; disabled-test and circular-test scans | 0 TBD/FIXME/XXX/TODO/HACK/PLACEHOLDER; only environmental skips | ✓ PASS (this pass) |
| Collect-only counts | `pytest --collect-only` on the two guarded files | 33 and 59 | ✓ PASS (this pass) |
| Lint / format / types | `ruff check`, `ruff format --check`, `ty check src/sif` | ruff clean; 239 files formatted; ty 1 pre-existing diagnostic in `embedding/embedder.py` (outside this phase) | ✓ PASS (with note) |
| Live exact-threshold probe | scratch index, `--json` score passed back as `--min-score` | own kept rank 1; below kept; above dropped; 1 empty; nan keeps all | ✓ PASS (carried; code byte-identical) |
| 84-row after-half sweep | 56 queries on the scratch bench index | 84/84 kept at own score; 84/84 one ULP below; 84/84 dropped one ULP above; fixed counts `84/84/84/84/70/70` | ✓ PASS (carried; code byte-identical) |
| Old-bound mutation | `-M/(1-M)` with `m.score <= ?` | 5 failed, 2 passed — the two CLI tests and `[scoped]`, `[unfiltered]`, `[weight-10]` | ✓ PASS (carried; code byte-identical) |
| Formatter mutation | `if per_chunk and sequence:` -> `if per_chunk:` | 1 failed — document-level row test | ✓ PASS (carried; files byte-identical) |
| Markup mutations | Chunk cell as a plain string and as `Text.from_markup(...)` | 2 failed each — both path cases | ✓ PASS (carried; files byte-identical) |
| `search_chunks` mutation | displayed map -> reciprocal map | 1 failed, 1 passed — only the score-map test | ✓ PASS (carried; files byte-identical) |
| Docs-text mutations | old `query` help; old MCP row | each `1 failed, 22 passed` | ✓ PASS (carried; files byte-identical) |

## Probe Execution

Step 7c: SKIPPED (no probes). No `scripts/*/tests/probe-*.sh` exists and no PLAN or SUMMARY declares one.

## Prohibitions (must-NOT checks)

All 71 prohibitions (30 from plans 19-01 to 19-09, 16 from 19-10 to 19-12, 11 + 8 + 6 from 19-13 to 19-15) were checked against HEAD. All are judgment tier: the plans carry bare `statement` entries or `status: unresolved` with no `verification` field. This table is a non-authoritative LLM-judge verdict; the end-of-phase acceptance is recorded below and in `prohibition_verdicts`.

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
| 19-10 | 4 | Generated docs not hand-edited | ✓ PASS | Generator idempotent this pass. |
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
| 19-13 | 10 | No released changelog entry edited | ✓ PASS | Released region byte-identical at four commits. |
| 19-13 | 11 | `test_search_min_score.py` not edited | ✓ PASS | Empty diff since `54acb11`. |
| 19-14 | 1 | No behaviour change; three searcher modules byte-identical | ✓ PASS | Diff empty; tests green. |
| 19-14 | 2 | MCP modules and goldens untouched | ✓ PASS | Diff empty; 306 tests green. |
| 19-14 | 3 | No hand-edit of generated docs | ✓ PASS | Generator idempotent this pass. |
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

**Verdict:** 64 hold, 0 flagged, 7 not verifiable from the tree (process-time). Prohibition 19-03 P1 has a recorded resolution in 19-UAT test 4. `prohibitions_flagged: 0`. End-of-phase acceptance recorded 2026-11-27 in 19-UAT test 16: the LLM-judge table stands, the 64 holds are acknowledged, and the 7 process-time items (19-10 P5, 19-11 P4, 19-13 P8, 19-13 P9, 19-14 P7, 19-15 P3, 19-15 P6) are acknowledged as unverifiable from the tree. The operator delegated the check to the orchestrating agent and has not reviewed the 71 rows personally; any item can still be resolved individually.

## Requirements Coverage

| Requirement | Source plans | Description | Status | Evidence |
| ----------- | ------------ | ----------- | ------ | -------- |
| CORR-01 | 19-01, 19-02 | Frontmatter-only edits become searchable | ✓ SATISFIED | Truths 1-14; full suite. |
| CORR-02 | 19-06, 19-07, 19-10, 19-15 | One result per document; `--per-chunk` escape hatch; recorded ranking-contract change | ✓ SATISFIED | Truths 33-45, 10.1-10.11, 15.1-15.6. |
| CORR-03 | 19-05, 19-11, 19-12, 19-13, 19-14, 19-15 | Deterministic pagination; BM25 min_score order and exact threshold; truthful threshold texts | ✓ SATISFIED | Truths 24-32 (27 as amended), 11.1-12.10, 13.1-13.9, 14.1-14.10, 15.3-15.6. |
| CORR-04 | 19-08, 19-09 | Title-aware ranking | ✓ SATISFIED | Truths 46-63. |
| CORR-05 | 19-03, 19-04 | One context/staleness attach | ✓ SATISFIED | Truths 15-23; scope note S2 recorded. |

Every requirement ID named in the fifteen plans' frontmatter is one of CORR-01 to CORR-05. `.planning/milestones/v1.2-REQUIREMENTS.md` maps exactly those five to Phase 19 and CORR-06 to Phase 21, which is correctly absent. No orphaned requirement.

### Decision Coverage

All 12 trackable `<decisions>` entries of `19-CONTEXT.md` are honored by shipped artifacts (`check.decision-coverage-verify`: total 12, honored 12, not honored 0; the gate is non-blocking and reports no drift).

## Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
| ---- | ---- | ------- | -------- | ------ |
| — | — | `TBD`, `FIXME`, `XXX`, `TODO`, `HACK`, `PLACEHOLDER`: 0 in the 97 covered files | — | Debt-marker gate clean. |
| `19-REVIEW-DISPOSITION.md` | 14-33 | IN-07 to IN-12 still show `open`; IN-09 to IN-12 are fixed or guarded by this round | ℹ️ Info | The disposition is a ledger; the code outcomes are verified here and in UAT tests 8-10 and 18. WR-01 and IN-01 are recorded fixed. |
| `19-10-PLAN.md` | 19 | Assumption A-19-10-1 `status: pending plan review` | ℹ️ Info | The layout shipped and is confirmed by 19-UAT test 12; the plan status is a planning-record note, not a code or must-have gap. |
| `19-SECURITY.md` | 1-21 | `verified: 2026-11-26`, 37 rows; the round-2 plans' own registers T-19-37 to T-19-46 are not folded into that report | ℹ️ Info | `threats_open: 0` and no must-have depends on a security re-run; the round-2 mitigations are exercised by the same tests. |
| `src/sif/embedding/embedder.py` | 850 | `ty` diagnostic: `embed()` returns numpy scalars where `list[float]` is declared | ℹ️ Info | Pre-existing; file unchanged since `82df76b0`; outside this phase. |
| `19-05-PLAN.md` | 121 | Task text still describes the historical threshold derivation | ℹ️ Info | Historical record; truth 4 is amended. |
| `19-RESEARCH.md` | 296, 404, 535-540 | Research still states the earlier score map | ℹ️ Info | Historical research document. |

**Test quality audit.** No disabled test is linked to a requirement; the only skips in the full suite are the environmental `sqlite-vec not available` and generated-doc guards (1 skipped in the full run). No test writes its own expected values. Expected-value provenance is PARTIAL only for the two recorded goldens (they pin a contract; ranking quality is not proven by them); the threshold direction is proved by independent oracles (descending scores, thresholds between rows, expected document ids). Assertion strength is value-level. The three previously unguarded behaviours (V19-26-1 to V19-26-3) now each have a mutation-proven guard, re-run by the validation audit on 2026-11-27. No blocker comes from this audit.

**Coincidental reliance.** None flagged. The declared assumptions are named: the 80-column fit depends on Rich's table layout (measured on 14.3.3 and 15.0.0; the render tests pin the behaviour on whatever Rich a CI cell installs), and the SC1 golden tolerates one ULP of platform libm drift by a declared mechanism (quick-s23). The exact-threshold equality rests on IEEE arithmetic for negative finite doubles, which the bit-for-bit test checks on this SQLite build and the probe confirms through the CLI.

## Human Verification (End-of-Phase Checkpoint)

None remain. The eight items the previous report left open are closed by `19-UAT.md`, which is `status: complete` with 18/18 tests carrying results (15 pass; 3 issue rows are verified resolutions of G-19-8, G-19-9 and G-19-10).

| Previous human item | UAT test | Result | Record |
| ------------------- | -------- | ------ | ------ |
| 1. Per-chunk tables on a real 80-column terminal | 11 | pass | 80x40 PTY, isolated scratch index; 6/6 vsearch and 5 query chunk rows show `#0`; document-level rows keep the plain path; all layouts at most 80 cells. |
| 2. Assumption A-19-10-1 for per-chunk machine formats | 12 | pass | Every clause confirmed against the same page's `--json`; default output unchanged; `--files` unique. |
| 3. `sif query --min-score` on the operator's index | 13 | pass | Isolated real-embedding index plus a copy of the operator's default index; the default index has no embedded chunks (environment limit recorded). |
| 4. Read the new help texts | 14 | pass | The per-leg floor and the never-compared fused score are clear from the printed help alone. |
| 5. Complete the UAT record for this round | 15 | pass | 18/18 results; G-19-8, G-19-9 and G-19-10 resolved with plan basenames; G-19-1 and G-19-2 normalized; test 9 restated to the per-leg contract. |
| 6. Resolve the 71 judgment-tier prohibitions | 16 | pass | LLM-judge table accepted; 64 holds including 19-03 P1; 7 process-time items acknowledged. |
| 7. Re-run the validation audit | 17 | pass | `19-VALIDATION.md`: `nyquist_compliant: true`, `validated: 2026-11-27`; V19-26-1 to V19-26-3 closed; all three mutation gates reproduced. |
| 8. Disposition WR-01 and IN-01 | 18 | pass | `docs/changelog.md:24` scoped per the review's wording; `19-REVIEW.md` clean; `19-REVIEW-DISPOSITION.md` records both fixed. |

The operator delegated every remaining checkpoint to the orchestrating agent on 2026-11-27 and asked for a verdict per test and for errors to be reported. Every `performed_by` caveat is confirmed in that form; none of the runs was performed by the operator personally, and the operator can still reverse any verdict. Tests 8, 9 and 10 remain `result: issue` by design because they record the originally observed defects; their gaps are `status: resolved` with `resolved_by` `19-13-PLAN.md`, `19-14-PLAN.md` and `19-15-PLAN.md` and matching summaries. No pending, skipped or blocked row.

## Gaps Summary

No must-have truth failed and no declared artifact is missing, a stub or unwired. The phase goal is achieved in code: results are fresh (CORR-01), deduplicated (CORR-02), deterministically paginable (CORR-03), title-aware (CORR-04) and free of redundant attach work (CORR-05), with every ranking-contract change measured before/after on the Phase 18 instrument (B0/B1 plus `bench/g19-2-min-score.json` and `bench/g19-8-exact-threshold.json`).

The regeneration's two substantive changes from the previous report are both resolved: the backstop truth 10.9 is verified by 19-UAT test 11's direct 80-column observation, so the previous `insufficient_spec` abstention is gone; and the WR-01/IN-01 changelog fix supersedes the 19-14 truth-7 literal (S7), while the corrected text is accurate and the released 1.2.4 region is byte-identical. The 19-14 artifact check's one missing literal is the same supersession, not a missing artifact. The remaining observations - the disposition ledger's open historical rows, the plan's pending assumption status, the security report's pre-round-2 date, and the pre-existing `ty` diagnostic - are informational and do not affect a must-have.

All eight human verification items are closed by `19-UAT.md` (18/18 results), `19-VALIDATION.md` is re-certified (`nyquist_compliant: true`, `validated: 2026-11-27`), `19-REVIEW.md` is clean (0 findings), and the 71 judgment-tier prohibitions are accepted at the end-of-phase checkpoint. The phase is `passed`.

---

_Verified: 2026-11-27T12:10:19Z_
_Verifier: Claude (gsd-verifier)_
