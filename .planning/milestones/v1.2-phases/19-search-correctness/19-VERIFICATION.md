---
phase: 19-search-correctness
verified: 2026-11-18T11:55:04Z
status: passed
score: 63/63 must-haves verified
covered_files: [".planning/phases/19-search-correctness/19-01-PLAN.md", ".planning/phases/19-search-correctness/19-01-SUMMARY.md", ".planning/phases/19-search-correctness/19-02-PLAN.md", ".planning/phases/19-search-correctness/19-02-SUMMARY.md", ".planning/phases/19-search-correctness/19-03-PLAN.md", ".planning/phases/19-search-correctness/19-03-SUMMARY.md", ".planning/phases/19-search-correctness/19-04-PLAN.md", ".planning/phases/19-search-correctness/19-04-SUMMARY.md", ".planning/phases/19-search-correctness/19-05-PLAN.md", ".planning/phases/19-search-correctness/19-05-SUMMARY.md", ".planning/phases/19-search-correctness/19-06-PLAN.md", ".planning/phases/19-search-correctness/19-06-SUMMARY.md", ".planning/phases/19-search-correctness/19-07-PLAN.md", ".planning/phases/19-search-correctness/19-07-SUMMARY.md", ".planning/phases/19-search-correctness/19-08-PLAN.md", ".planning/phases/19-search-correctness/19-08-SUMMARY.md", ".planning/phases/19-search-correctness/19-09-PLAN.md", ".planning/phases/19-search-correctness/19-09-SUMMARY.md", ".planning/phases/19-search-correctness/bench/b0.json", ".planning/phases/19-search-correctness/bench/b1.json", ".planning/phases/19-search-correctness/bench/d12-verdict.json", "docs/benchmarking.md", "docs/cli-reference.md", "src/sif/cli/commands/eval.py", "src/sif/cli/commands/index.py", "src/sif/cli/commands/search.py", "src/sif/core/models.py", "src/sif/database/database.py", "src/sif/database/repositories.py", "src/sif/database/schema.py", "src/sif/indexing/incremental.py", "src/sif/indexing/parser.py", "src/sif/indexing/watcher.py", "src/sif/mcp/backend.py", "src/sif/mcp/protocol.py", "src/sif/mcp/tools.py", "src/sif/search/bm25.py", "src/sif/search/context_attach.py", "src/sif/search/hybrid.py", "src/sif/search/personal_bench.py", "src/sif/search/rerank.py", "src/sif/search/rrf.py", "src/sif/search/staleness.py", "src/sif/search/vector.py", "tests/fixtures/bench/heldout_defaults.json", "tests/integration/test_embed_idempotency.py", "tests/integration/test_incremental_equivalence.py", "tests/integration/test_search_correctness.py", "tests/unit/cli/test_eval.py", "tests/unit/cli/test_index.py", "tests/unit/cli/test_search.py", "tests/unit/cli/test_search_pagination.py", "tests/unit/database/test_repositories.py", "tests/unit/database/test_schema.py", "tests/unit/database/test_schema_title_fts.py", "tests/unit/indexing/test_incremental.py", "tests/unit/indexing/test_parser.py", "tests/unit/indexing/test_parser_checksum.py", "tests/unit/indexing/test_watcher.py", "tests/unit/mcp/test_backend.py", "tests/unit/search/test_bench_snapshot.py", "tests/unit/search/test_bm25.py", "tests/unit/search/test_collection_filter.py", "tests/unit/search/test_context_attach.py", "tests/unit/search/test_hybrid.py", "tests/unit/search/test_personal_bench.py", "tests/unit/search/test_rrf.py", "tests/unit/search/test_staleness.py", "tests/unit/search/test_vector.py"]
covered_digest: "v4:sha256:a28955b9f4667edfa6c6abe90e3ad9a043a82706c6c042559b57db85389b4ef8"
behavior_unverified: 0
overrides_applied: 0
prohibitions_flagged: 0
prohibition_verdicts: "30/30 hold (judgment tier, LLM judge — non-authoritative)"
re_verification:
  previous_status: passed
  previous_score: 63/63
  gaps_closed: []
  gaps_remaining: []
  regressions: []
advisory: []
---

# Phase 19: Search Correctness Verification Report

**Phase Goal:** Search results are fresh, deduplicated, deterministically paginable, and title-aware — the trust floor that metadata filtering (20) builds on, with every ranking-contract change measured before/after on the Phase 18 instrument.
**Verified:** 2026-11-18T11:55:04Z
**Status:** passed
**Re-verification:** Yes — regeneration at commit `618997c` (v1.2.0 tree). Every must-have was re-derived from the current tree rather than carried forward from the previous report. The delta since the prior pass is `618997c` (`_mean` → `math.fsum`, rounded `strictly_above_noise_floor`, used by `noise_gate`/`embedder_verdict`, plus a regression test); no Phase 19 ranking, pagination, freshness, or enrichment source changed. The fingerprint was recomputed because `src/sif/search/personal_bench.py` is in Phase 19's covered set.

## Goal Achievement

### Roadmap Success Criteria

| # | Success Criterion | Status | Evidence |
| --- | ----------------- | ------ | -------- |
| 1 | Frontmatter-only edits become searchable after the next index update; parser dispatch + metadata-aware checksum in ONE plan with ONE shared forced-reindex migration; Markdown body path byte-identical; YAML `---` empty-body bug fixed | ✓ VERIFIED | `compute_checksum()` hashes body + NUL + canonical full frontmatter (`src/sif/core/models.py:64-72`); all three parsers call it (`src/sif/indexing/parser.py:81,117,184`). `IncrementalIndexer._process_file` dispatches `create_parser(file_path) or TextParser()` and stores `parsed.checksum` (`src/sif/indexing/incremental.py:393,482`). `CONVENTION_VERSION = 2` (`parser.py:19`) + one per-collection `convention:<id>` marker drives exactly one forced re-parse (`incremental.py:150-212`); marker gate requires `failed_stored == 0`. Markdown still uses `frontmatter.loads` and preserves body bytes; `CodeParser` reads `.yaml/.yml` whole (no `---` truncation). Independent checksum check passed (reorder same, frontmatter edit changes, body edit changes, date round-trip). |
| 2 | One result per document by default; dedup inside VectorSearcher pre-fusion; `--per-chunk` escape hatch; ranking-contract change recorded with bench before/after and goldens with rationale | ✓ VERIFIED | `VectorSearcher._candidates` groups by `document_id` after `min_score`, best-distance row wins, `chunk_matches` counts pre-dedup rows (`src/sif/search/vector.py:296-322`); `--per-chunk` on vsearch/query only (`src/sif/cli/commands/search.py:734,1003`) and MCP `per_chunk` on `query`/`vec_search` (signature-derived schema `src/sif/mcp/tools.py:137-139,356-357`; wire goldens). Both RRF fuse sites pass `key=fuse_key_for(options.per_chunk)` (`src/sif/search/hybrid.py:150-155,451-455`). B0/B1 saved runs (100 queries, corpus fingerprint `8c006123784348d1`) + `docs/benchmarking.md` §CORR-02 + regenerated SC1/RRF goldens and held-out rationale. |
| 3 | Deterministic pagination — CLI `--offset` and MCP offset return the correct next page; hybrid owns ONE offset slice; searchers return from rank 0; BM25 min_score order fixed; offset=0 reproduces the recorded contract | ✓ VERIFIED | Three `--offset` flags with `click.IntRange(min=0)` (`src/sif/cli/commands/search.py:516,717,948`); `QueryInput.offset = Field(default=0, ge=0)` (`src/sif/mcp/protocol.py:88,128,155`) and signatures in `tools.py:137,317,356`. `HybridSearcher` calls legs at offset 0 and slices once (`hybrid.py:119-176`); pipeline passes offset=0 and owns the slice (`hybrid.py:410-484`); BM25 binds `rank >= 1 - 1/min_score` inside the FTS CTE before `LIMIT ? OFFSET ?` (`bm25.py:94-97,138-162`); global `rank = offset + position`. Independent B0 rerun: n=100, mean delta 0.0, 100 unchanged. |
| 4 | Title-aware ranking — title-FTS detect-and-rebuild migration + rewritten triggers + bench-measured bm25() column weights + mtime index; `documents_fts_v` vocab shadow survives rebuild on a populated DB | ✓ VERIFIED | `_fts_column_names()` gate + two-column DDL + drop-vocab → drop-triggers/table → single `('rebuild')` → recreate-vocab/triggers under `SAVEPOINT sp_fts_tables` (`src/sif/database/schema.py:451-665`); the old rowid/content seed is absent. Triggers carry `(rowid, content, title)` incl. `old.title`. `bm25(documents_fts, ?, ?)` bound weights in both branches (`src/sif/search/bm25.py:84-97,125,147`); `idx_documents_mtime` created (`schema.py:769`). Populated-DB migration/vocab/DYM tests pass; D-12 sweep measured 2.0/3.0/4.0 against B1 and recorded a rejection (`bench/d12-verdict.json`), pinned `_TITLE_WEIGHT = 1.0`. |
| 5 | Results without redundant attach work — double-attach eliminated; exactly ONE context/staleness attach at pipeline exit | ✓ VERIFIED | `enrich_results` composes `attach_path_contexts` then `mark_vector_staleness` (`src/sif/search/context_attach.py:317-346`); no `_attach_contexts` anywhere under `src/sif` (grep count 0); pipeline enriches exactly once per exit (`hybrid.py:356,367,379,484`); direct CLI search/vsearch enrich once (`search.py:613,872-874`); MCP fallback enriches once and the pipeline path is not re-enriched (`backend.py:490,501,534`). Spy tests pass. |

**Score:** 5/5 roadmap success criteria verified.

### Observable Truths (Plan Must-Haves)

The `UNCLASSIFIED-FLAGGED` lines in PLAN frontmatter are probe-classification flags, not functional must-haves; they are excluded from the score (9 such lines across the nine plans). All 63 functional plan truths are re-verified against the current tree.

#### Plan 19-01 — CORR-01 (parser dispatch, checksum, canonical metadata)

| # | Truth | Status | Evidence |
| --- | ----- | ------ | -------- |
| 1 | `.yaml`/`.yml` starting with `---` is parsed by `CodeParser` as the whole file in all three forms | ✓ VERIFIED | `create_parser` maps `.yaml/.yml` through `CodeParser.LANGUAGE_MAP` (`parser.py:200-213`); `CodeParser.parse` reads whole file (`parser.py:163-193`); `test_yaml_leading_separator_is_parsed_as_whole_file` (all forms incl. `two_blocks.yaml`) passes. |
| 2 | Every parser computes sha256(body + NUL + canonical full frontmatter) with sort_keys/default=str/ensure_ascii=False/compact + recursive key coercion; frontmatter edit changes checksum, key reorder does not, body edit does | ✓ VERIFIED | `canonical_metadata_json()` + `compute_checksum()` (`models.py:19-72`); all parsers call it (`parser.py:81,117,184`). 8-test checksum matrix passes. Independent behavioral check: reorder same True, frontmatter edit changes True, body edit changes True, date round-trip True, nested key coercion `{1:{"2":3}}` → `{"1":{"2":3}}`. |
| 3 | Markdown body extraction stays byte-identical; `frontmatter.loads` still strips frontmatter | ✓ VERIFIED | `MarkdownParser.parse` body path unchanged; checksum added only (`parser.py:57-90`); parser suite passes. |
| 4 | `.md` with `date: 2024-01-01` stores without TypeError and metadata JSON round-trips to the hashed canonical string | ✓ VERIFIED | `canonical_metadata_json(default=str)`; repository create/update persist it (`repositories.py:192,274`); `test_yaml_date_frontmatter_indexes_without_type_error` passes; independent `"date":"2024-01-01"` round-trip check True. |
| 5 | `IncrementalIndexer` stores `parsed.checksum`, not a body-only fallback | ✓ VERIFIED | `incremental.py:482` passes `checksum=parsed.checksum`; incremental suite passes. |
| 6 | An extension outside `create_parser`'s map falls back to `TextParser` | ✓ VERIFIED | `incremental.py:393` `create_parser(file_path) or TextParser()`; `test_per_file_parser_dispatch_with_text_fallback` passes. |

#### Plan 19-02 — CORR-01 (fast path, convention migration, watch signal)

| # | Truth | Status | Evidence |
| --- | ----- | ------ | -------- |
| 7 | `index_meta` exists on fresh/migrated DBs with per-collection `convention:<id>` keys; `drop_all` removes it | ✓ VERIFIED | `schema.py:302-311`; `drop_all` lists `index_meta` (`schema.py:811`); `IndexMetaRepository.get/set` (`repositories.py:731-752`); schema tests pass. |
| 8 | First `update_collection` with absent/old marker forces exactly one re-parse pass; one `migrate <N>` event with documents; empty collection silent; marker written only after a clean pass | ✓ VERIFIED | `incremental.py:150-212`; `TestConventionMigration` + CLI migrate-render test pass. WR-01 refinement retained: only failures on *stored* documents block the marker (`failed_stored`, `incremental.py:189-212`). |
| 9 | Metadata-only edit updates title/metadata/checksum/mtime/file_size, keeps chunks and embeddings | ✓ VERIFIED | `_process_file` fast path `incremental.py:431-446`; `TestMetadataFastPath` + `test_frontmatter_only_cycle_preserves_chunks_and_moves_title` pass. |
| 10 | Body edit deletes that document's chunks and embeddings before update | ✓ VERIFIED | `incremental.py:451-458`; body-edit fast-path tests pass. |
| 11 | `--force` skips checksum skip but unchanged body takes the metadata fast path | ✓ VERIFIED | `incremental.py:413-446`; force test passes. |
| 12 | `update_paths` never starts a migration but uses body-vs-metadata discrimination | ✓ VERIFIED | `update_paths` passes `migrating=False` (`incremental.py:318-322`) and performs no marker read/write; test patches `IndexMetaRepository.get` to raise and passes. |
| 13 | `reindexed_paths` contains only added/body-changed paths; watcher embed leg selects from it; metadata-only edit produces no new chunk/vector rows | ✓ VERIFIED | `incremental.py:167-189,286-329`; watcher `_run_burst/_run_reconcile` feed `reindexed_paths` (`watcher.py:906,924`); `TestEmbedDepth` regressions pass. |
| 14 | Parse failure leaves marker unwritten and counted, so the next pass retries | ✓ VERIFIED | `failed_stored` accounting + marker gate (`incremental.py:165-212`); failure-retry tests pass. |

#### Plan 19-03 — CORR-05 (search-core single attach)

| # | Truth | Status | Evidence |
| --- | ----- | ------ | -------- |
| 15 | BM25/Vector/Hybrid searchers no longer attach contexts/staleness; return raw results | ✓ VERIFIED | No `_attach_contexts` anywhere under `src/sif` (grep count 0); searcher contract tests pass. |
| 16 | `SearchPipeline.search` calls the shared enrichment exactly once on BM25, VECTOR, HYDE, and hybrid exits | ✓ VERIFIED | `hybrid.py:356` (BM25), `:367/:379` (VECTOR/HYDE via `_enrich`), `:484` (hybrid); spy test counts exactly one call per exit; full suite passes. |
| 17 | `enrich_results(db, results)` composes attach then staleness; contexts keep two-sided `normalize_path` with no SQL path prefilter and never clobber on miss; staleness is one batched/derived read with display gate and `None` degradation | ✓ VERIFIED | `context_attach.py:317-346` composes in order; `_CONTEXTS_SQL` filters only `context_type='path'` and normalization is two-sided in Python (`context_attach.py:51-53,109-110,284-315`); staleness reads the `embedded_documents` shadow with display gate; context/staleness tests pass. |
| 18 | A spy test counts exactly one enrichment per exit; searcher tests assert none inside searchers | ✓ VERIFIED | `test_staleness.py` spy tests + `TestBM25SearcherEnrichmentContract`, `TestVectorSearcherEnrichmentContract`, `TestHybridContextAttachment`, `TestSingleEnrichmentOwner` (CLI/MCP) pass. |
| 19 | `staleness.py` D-09 docstring names the single `enrich_results` owner and no searcher `_attach_contexts` reference | ✓ VERIFIED | `staleness.py:11-19` names `enrich_results`; grep for `_attach_contexts` under `src/sif` returns nothing. |

#### Plan 19-04 — CORR-05 (entry points + B0)

| # | Truth | Status | Evidence |
| --- | ----- | ------ | -------- |
| 20 | CLI `sif search` and `sif vsearch` call `enrich_results` exactly once after the direct searcher; output keeps context/staleness | ✓ VERIFIED | `search.py:613,872-874`; `TestSingleEnrichmentOwner` (CLI) passes. |
| 21 | MCP BM25 fallback enriches exactly once; pipeline path is not enriched again at the boundary | ✓ VERIFIED | `backend.py:490,501,534` are the BM25/fallback exits; the pipeline path returns the pipeline's enriched page without a second call; `TestSingleEnrichmentOwner` (MCP) passes. |
| 22 | MCP re-map still forwards `rank`, `collection_name`, `vectors_stale` | ✓ VERIFIED | `backend.py:190-197` explicit metadata dict; re-map set tests pass. |
| 23 | B0 is a saved personal-eval run on the post-CORR-01 engine over the committed 150-doc fixture corpus with `--bm25-only`, ≥50 queries, `--compare` zero mean delta | ✓ VERIFIED | `bench/b0.json`: 100 queries, corpus `{documents:150, sampled:50, fingerprint:8c006123784348d1}`, retrieval `bm25`; independent rerun on the scratch index: n=100, mean delta 0.0, 100 unchanged. |

#### Plan 19-05 — CORR-03 (deterministic pagination)

| # | Truth | Status | Evidence |
| --- | ----- | ------ | -------- |
| 24 | `sif search`/`vsearch`/`query` accept `--offset` (`IntRange(min=0)`, default 0); past-the-end returns an empty page | ✓ VERIFIED | `search.py:516,717,948`; pagination CLI tests pass. |
| 25 | Ranks are global across pages (`rank = offset + position`) | ✓ VERIFIED | BM25 `bm25.py:181`, vector `vector.py:249-251`, hybrid `_paginate` (`hybrid.py:55-67`); tests pass. |
| 26 | `limit=l offset=o` equals the `[o:o+l]` slice of `limit=o+l offset=0` for BM25/vector/hybrid | ✓ VERIFIED | `TestConsistentPagination` integration tests (real schema + vec0) pass (31 focused tests this pass). |
| 27 | BM25 applies `min_score` before LIMIT/OFFSET via bound threshold `1 - 1/min_score`, `rank >= threshold`; omitted when min_score=0 | ✓ VERIFIED | `bm25.py:94-97,138-162`; all params bound; threshold tests pass. |
| 28 | Hybrid calls legs with `offset=0`, `limit+offset`, one slice after fusion, and paginates early single-leg returns | ✓ VERIFIED | `hybrid.py:119-176`; hybrid/pipeline offset tests pass. |
| 29 | Reranker window is `max(candidate_limit, limit+offset)` when offset>0, `candidate_limit` at offset=0; `top_k = limit+offset`; beyond-cap requests get a full page | ✓ VERIFIED | `hybrid.py:459-484`; `TestRerankerWindowPagination` passes. |
| 30 | Pipeline passes offset=0 to hybrid and owns one slice; BM25/VECTOR/HYDE branches let the searcher own the slice | ✓ VERIFIED | `hybrid.py:410-427` call hybrid with offset=0; `hybrid.py:482-484` one `_paginate`; pipeline offset tests pass. |
| 31 | MCP `query` offset `Field(default=0, ge=0)` forwarded into SearchOptions; Lex/Vec inputs validated; query schema lists offset | ✓ VERIFIED | Property holds at the Phase 22 successor path: `protocol.py:88,128,155`; signature-derived schema `tools.py:137,317,356`; wire goldens list `offset` on query/lex_search/vec_search; backend forwards (`backend.py:459,599,663`). The Phase 19 `handlers.py` hand-written schema was replaced in Phase 22 — property verified, not the file. |
| 32 | After attach + pagination, offset=0/min_score=0 personal-eval rerun against B0 reports zero mean delta | ✓ VERIFIED | Independent rerun against `bench/b0.json`: n=100, mean 0.0, unchanged 100 (see Behavioral Spot-Checks). |

#### Plan 19-06 — CORR-02 (dedup, chunk identity, per-chunk fusion)

| # | Truth | Status | Evidence |
| --- | ----- | ------ | -------- |
| 33 | VectorSearcher returns one row per document by default: grouped by document_id in best-distance order after min_score; winner carries `chunk_id`/`sequence`; `chunk_matches` counts pre-dedup rows | ✓ VERIFIED | `vector.py:296-322`; `TestVectorDocumentDedup` passes. |
| 34 | Default target `limit+offset`; `fetch_k` starts `min(max(target*4,50),2048)` and doubles only on a saturated batch while target unmet; past-cap offset returns empty page | ✓ VERIFIED | `vector.py:22-25,187-249`; escalation/ceiling tests pass. |
| 35 | A document with ≥5 matching chunks at limit=10 yields 10 distinct documents on vector and hybrid default paths | ✓ VERIFIED | `TestChunkyDocumentDedup` integration tests pass (`test_vector_limit_ten_returns_ten_distinct_documents`, `test_hybrid_default_limit_ten_returns_ten_distinct_documents`). |
| 36 | Per-chunk mode returns ungrouped chunk rows with identity; both RRF fuses group by `chunk_key` selected via `fuse_key_for`; BM25 rows stay document-keyed; default path unchanged | ✓ VERIFIED | `rrf.py:8-28`; `hybrid.py:150-155,451-455` (exactly two fuse sites, both keyed); per-chunk tests pass. |
| 37 | RRF scoring math unchanged; merge adopts-null chunk fields from the later list and keeps `max(chunk_matches)` | ✓ VERIFIED | `rrf.py:36-47` metadata merge only; score expression untouched; byte-identical score tests pass. |
| 38 | `SearchResult.to_dict()` carries `chunk_id`/`sequence`/`chunk_matches`; SC1 and RRF goldens regenerated with rationale docstrings | ✓ VERIFIED | `models.py:341-343`; golden docstrings record CORR-02/CORR-04 rationale (`test_hybrid.py:765-787`, `test_rrf.py:478-480`); golden tests pass. |
| 39 | Held-out snapshot regenerated for the dedup contract with rationale; verdict keys and defaults lock valid | ✓ VERIFIED | `tests/fixtures/bench/heldout_defaults.json` rationale records dedup + title-column + D-12 evidence; snapshot reproduction tests pass (31 focused tests this pass). |

#### Plan 19-07 — CORR-02 (public surfaces + B1)

| # | Truth | Status | Evidence |
| --- | ----- | ------ | -------- |
| 40 | `sif query`/`sif vsearch` accept `--per-chunk`; `sif search` does not | ✓ VERIFIED | `search.py:734` (vsearch), `:1003` (query); `search_cmd` has no such option; `TestPerChunkSurfaces` includes the search-rejection test. |
| 41 | Default CLI output exposes `chunk_matches` in table and JSON; per-chunk rows show `path#sequence` and JSON `chunk_id`/`sequence` | ✓ VERIFIED | `_title_cell` annotation (`search.py:156-174`), `_chunk_cell` (`search.py:177-190`), `to_dict()`; tests pass. |
| 42 | MCP `query`/`vec_search` inputs accept `per_chunk`; handler schema lists it; backend forwards it | ✓ VERIFIED | Property holds at the Phase 22 successor path: signature-derived schema `tools.py:137-139,356-357`; wire goldens list `per_chunk` on query and vec_search (not on lex_search); backend forwards (`backend.py:460,664`). |
| 43 | MCP re-map explicitly forwards `chunk_id`/`sequence`/`chunk_matches` | ✓ VERIFIED | `backend.py:190-197`; re-map tests pass. |
| 44 | `make docs-generate` clean; CLI reference documents `--offset` and `--per-chunk` | ✓ VERIFIED | Ran both generators this pass: exit 0, no diff (`git status --short docs/` empty); `docs/cli-reference.md` has 3 `--offset` rows (search/vsearch/query) and 2 `--per-chunk` rows (vsearch/query). |
| 45 | B1 recorded after CORR-02 on the same scratch index; `--compare b0.json` reports per-query deltas with ≥50 paired queries; deltas in `docs/benchmarking.md` labeled the BM25 no-drift check; held-out/SC1 old→new numbers cited | ✓ VERIFIED | `bench/b1.json` 100 queries, same fingerprint (`8c006123784348d1`); independent compare n=100, mean 0.0, 100 unchanged; B0 and B1 differ only in `created_at` with identical queries, as expected for `--bm25-only`; `docs/benchmarking.md:206-227` contains the CORR-02 narrative/label and old→new numbers. |

#### Plan 19-08 — CORR-04 (title-FTS migration, triggers, weighted bm25)

| # | Truth | Status | Evidence |
| --- | ----- | ------ | -------- |
| 46 | Populated DB migration drops vocab first, drops FTS/triggers, recreates two-column, runs `'rebuild'`, recreates vocab/triggers; title-only MATCH 0→1 | ✓ VERIFIED | `schema.py:497-665` sequence; `TestTitleFtsMigration::test_title_only_match_flips_from_zero_to_one` passes. |
| 47 | Rebuild populates exactly once (no rowid/content seed); structural assertion; row counts equal; unique token one row; deleted doc not MATCHable | ✓ VERIFIED | Exactly one documents-population statement (`INSERT INTO documents_fts(documents_fts) VALUES('rebuild')`, `schema.py:574`); old seed absent; `test_population_is_structurally_single_and_seed_free` + `test_single_population_row_counts_and_match_cardinality` pass. |
| 48 | `documents_fts_v` still yields vocab after rebuild; suggest works; title UPDATE/DELETE sync; NULL titles clean; integrity_check ok | ✓ VERIFIED | `test_vocab_shadow_survives_and_dym_still_works` + trigger/update/delete/NULL tests pass (`test_schema_title_fts.py`). |
| 49 | Fresh DB creates two-column directly; second `create_all` performs only detection reads | ✓ VERIFIED | `test_fresh_db_creates_two_columns_directly` + `test_second_create_all_pays_only_the_detection_read` pass. |
| 50 | Chunks FTS and its three triggers stay byte-identical | ✓ VERIFIED | `schema.py:634-652` chunks triggers are content-only (no title); trigger test passes. |
| 51 | `bm25(documents_fts, ?, ?)` binds content/title weights left-to-right; 1.0/1.0 reproduces rank; constant starts 1.0; min_score before LIMIT/OFFSET | ✓ VERIFIED | `bm25.py:24-25,84-97,125-164`; `TestWeightedBM25` passes. |
| 52 | `SearchOptions.title_weight` override changes title-vs-body ordering in a behavior test; not a setting/CLI flag | ✓ VERIFIED | `models.py:377`; reorder test passes; grep finds no title-weight knob in CLI/config/docs. |
| 53 | SC1 golden and held-out snapshot regenerated for the title-column effect with rationale; snapshot verdict computable | ✓ VERIFIED | SC1 docstring (`test_hybrid.py:779-787`) + held-out rationale; reproduction tests pass. |
| 54 | No lexical CJK title win claimed or tested; claim scoped to tokenized EN-style titles | ✓ VERIFIED | `docs/benchmarking.md:255-257` scopes the claim; no CJK title assertion in tests. |

#### Plan 19-09 — CORR-04 (mtime index, MCP startup, per-leg gates, D-12 verdict)

| # | Truth | Status | Evidence |
| --- | ----- | ------ | -------- |
| 55 | `idx_documents_mtime` exists on fresh and migrated DBs and is in the expected index set | ✓ VERIFIED | `schema.py:769`; `test_mtime_index_is_created_on_fresh_and_migrated_databases` passes; scratch DB inspection confirms the index. |
| 56 | MCP-only process runs schema migration once in `SearchBackend.__init__` at the backend's own dimension; second construction pays detection reads only | ✓ VERIFIED | `backend.py:290` calls `init_schema(embedding_dim=self.settings.embedding_dim, identity=...)`; `database.py:34-70`; `TestSchemaInitializationAtStartup` (incl. second-construction detection test) passes. |
| 57 | `ComparisonReport` exposes per-leg and per-leg×split noise gates in `--compare` JSON/table; groups <10 suppressed and named; `warrants_default_change` remains the held-out summary gate | ✓ VERIFIED | `personal_bench.py:471-546` (`to_dict` carries `legs`, `leg_splits`, and `gate.warrants_default_change`); `leg_noise_gates` (`personal_bench.py:2033-2048`); live compare output contains `legs` (title n=50, body n=50) and `leg_splits` (title heldout n=23, body heldout n=26), with 3 suppressed groups named on stderr; `warrants_default_change` present under `comparison.gate`. The 618997c `fsum`/rounded-floor change is exercised: the 160 personal-bench/pin tests pass. |
| 58 | Title-weight sweep opens the scratch index through `Database(...).init_schema()` and aborts unless stored `documents_fts` SQL has a title column | ✓ VERIFIED | `.planning/tmp/phase19/sweep_title_weight.py:92-99` calls `db.init_schema(embedding_dim=dim)`; `_require_title_column()` aborts on missing title (`:102-118`); scratch DB inspection shows the two-column DDL. |
| 59 | Sweep evaluates 2.0/3.0/4.0 (refining at band edges) against B1's exact query set through `compare_saved_run` | ✓ VERIFIED | Driver `BASE_CANDIDATES=(2.0,3.0,4.0)`, `REFINEMENTS={2.0:2.5,4.0:3.5}`, `compare_saved_run` (`sweep_title_weight.py:40-42,188`); `bench/d12-verdict.json` has all three candidates with GateResult fields. |
| 60 | D-12 gate applied to title held-out (noise-gate winner) AND body held-out (rounded mean delta ≥ -0.01) | ✓ VERIFIED | `_accepted()` requires `title["winner"]` and body delta ≥ `-0.01` (`sweep_title_weight.py:141-147`); verdict shows title winner=false, body delta 0.0. |
| 61 | Pinned `_TITLE_WEIGHT` is accepted candidate or 1.0 on rejection; `bench/d12-verdict.json` records every candidate's deltas, CI, gate results, decision | ✓ VERIFIED | Artifact: `decision="rejected"`, `pinned_title_weight=1.0`, three candidates each with `title_heldout`/`body_heldout` n=23/26, mean delta 0.0, `sufficient=true`; `bm25.py` constant 1.0; `test_pinned_title_weight_is_the_measured_d12_value` passes. |
| 62 | Goldens/docs reflect pinned weight: snapshot rationale refreshed, SC1 docstring updated, `test_bm25.py` pins constant/behavior, `docs/benchmarking.md` records verdict; rejection valid | ✓ VERIFIED | Rationale/docstrings carry dedup + title-column + D-12 notes; pin test passes; `docs/benchmarking.md:235-253` records the verdict. |
| 63 | Title weight is not a Settings field or CLI flag; option override remains internal and measurement-only | ✓ VERIFIED | `grep title_weight/TITLE_WEIGHT` over `src/sif/cli`, `src/sif/config`, `docs/cli-reference.md`, `docs/configuration.md` returns no hits; only `SearchOptions.title_weight` and `bm25.py` module constants. |

**Score:** 63/63 plan truths verified (0 present-behavior-unverified).

### Deferred Items

None. The deferred Info review findings below are pre-existing/latent issues explicitly outside Phase 19 scope, not unmet phase truths.

### Advisory (New Scope, Unevidenced)

None. No new-scope blockers were found; no finding required the advisory downgrade.

### Required Artifacts

`verify.artifacts` was run for all nine plans. 47/49 declared entries pass. The two non-passing entries are the same path, `src/sif/mcp/handlers.py` (declared by 19-05 and 19-07), which Phase 22 intentionally deleted and replaced with the signature-derived tool schema in `src/sif/mcp/tools.py`. The underlying property (offset/per_chunk exposed and validated) is verified at the successor path, so this is a **superseded path, not a missing deliverable**. Unique artifacts:

| Artifact | Expected | Status | Details |
| -------- | -------- | ------ | ------- |
| `src/sif/core/models.py` | canonical JSON/checksum helpers; chunk result fields; offset/per_chunk/title_weight options | ✓ VERIFIED | Helpers implemented; fields wired into `to_dict()`; internal-only title override. |
| `src/sif/indexing/parser.py` | parser dispatch contract; checksum; `CONVENTION_VERSION`; title-type safety | ✓ VERIFIED | `create_parser` map, all parsers use `compute_checksum`, version = 2, non-string title coercion. |
| `src/sif/indexing/incremental.py` | per-file dispatch, metadata fast path, marker, `reindexed_paths`, per-file write isolation | ✓ VERIFIED | All present; used by CLI/watch/MCP paths. |
| `src/sif/indexing/watcher.py` | embed candidates from `reindexed_paths` | ✓ VERIFIED | Burst + reconcile paths consume it (`watcher.py:906,924`). |
| `src/sif/database/repositories.py` | canonical metadata persistence; `IndexMetaRepository` | ✓ VERIFIED | create/update serialize canonically; get/set parameterized. |
| `src/sif/database/schema.py` | `index_meta`, title-FTS migration, triggers, vocab shadow, savepoint durability, mtime index | ✓ VERIFIED | DDL/rebuild/triggers present; one population statement; commit discipline. |
| `src/sif/database/database.py` | `init_schema(embedding_dim=None)` override | ✓ VERIFIED | Explicit override never consults `get_settings()`; no-arg form unchanged. |
| `src/sif/search/bm25.py` | weighted bound bm25, pre-pagination min_score, global ranks | ✓ VERIFIED | Both branches bound; threshold inside CTE; ranks offset+position. |
| `src/sif/search/vector.py` | KNN chunk join, per-doc dedup, bounded escalation, per-chunk mode, single slice | ✓ VERIFIED | All present; used by vector/hybrid paths. |
| `src/sif/search/hybrid.py` | single offset slice, per-chunk key, pipeline enrichment, rerank window | ✓ VERIFIED | Both fuse sites keyed; pipeline enriches once per exit. |
| `src/sif/search/rrf.py` | optional key callable, chunk key helpers, metadata merge (math unchanged) | ✓ VERIFIED | Two call sites use the helper; score expression untouched. |
| `src/sif/search/context_attach.py` | `enrich_results` composition | ✓ VERIFIED | Used by pipeline, CLI, MCP fallback. |
| `src/sif/search/staleness.py` | D-09 docstring naming `enrich_results` | ✓ VERIFIED | Docstring updated; no `_attach_contexts` references remain. |
| `src/sif/search/personal_bench.py` | per-leg and leg×split gates | ✓ VERIFIED | `legs`/`leg_splits` in JSON; absent combos insufficient; 618997c floor fix keeps rounded-tie semantics. |
| `src/sif/cli/commands/search.py` | `--offset`, `--per-chunk`, one enrichment per direct exit | ✓ VERIFIED | Flags (`516,717,948`; `734,1003`) + rendering + enrichment. |
| `src/sif/cli/commands/index.py` | migrate event rendering | ✓ VERIFIED | One-line `migrate` branch (`index.py:185-190`); CLI test passes. |
| `src/sif/cli/commands/eval.py` | per-leg/leg×split comparison rendering | ✓ VERIFIED | JSON/table wiring (`eval.py:428-478,553-556`); eval tests pass. |
| `src/sif/mcp/protocol.py` | offset/per_chunk input fields; no per_chunk on Lex | ✓ VERIFIED | `QueryInput.offset/per_chunk`, `LexSearchInput.offset`, `VecSearchInput.offset/per_chunk`. |
| `src/sif/mcp/handlers.py` | query schema offset/per_chunk + pass-through | ⚠️ SUPERSEDED | Deleted in Phase 22; property verified at `src/sif/mcp/tools.py` (signature-derived schema) + `backend.py` forwarding + wire goldens. |
| `src/sif/mcp/tools.py` | published tool schemas (Phase 22 successor) | ✓ VERIFIED | `query`/`vec_search` expose offset+per_chunk; `lex_search` exposes offset only; golden schemas match. |
| `src/sif/mcp/backend.py` | offset/per_chunk forwarding, one fallback enrichment, chunk metadata re-map, startup schema init | ✓ VERIFIED | All present; pipeline path not double-enriched. |
| `docs/cli-reference.md` | generated `--offset`/`--per-chunk` docs | ✓ VERIFIED | 3 + 2 generated rows; regenerated this pass with no diff. |
| `docs/benchmarking.md` | CORR-02 and CORR-04 before/after narratives + D-12 verdict | ✓ VERIFIED | Sections present with reproduced numbers/labels. |
| `bench/b0.json` | pre-ranking-change saved run | ✓ VERIFIED | 100 queries, fingerprint `8c006123784348d1`, bm25; independently compared this pass: zero delta. |
| `bench/b1.json` | post-dedup, pre-title saved run | ✓ VERIFIED | 100 queries, same fingerprint, identical query set to B0 (only `created_at` differs). |
| `bench/d12-verdict.json` | candidate sweep + accept/reject decision | ✓ VERIFIED | rejected/pinned 1.0; 3 candidates with full GateResults. |
| `tests/unit/database/test_schema_title_fts.py` | populated-DB migration suite | ✓ VERIFIED | 14 tests incl. durability/reopen tests; all pass. |
| `tests/fixtures/bench/heldout_defaults.json` | regenerated snapshot + rationale | ✓ VERIFIED | Rationale records dedup/title-column/D-12; reproduction tests pass. |

### Key Link Verification

`verify.key-links` still reports "Target not referenced in source" for links whose `to` value is a file path or a DDL object rather than a literal string (the documented false-negative shape). Manual import/DML verification confirms every link:

| From | To | Via | Status | Details |
| ---- | -- | --- | ------ | ------- |
| `src/sif/indexing/parser.py` | `src/sif/core/models.py` | one `compute_checksum` helper | WIRED | Import + all 3 parsers call it (`parser.py:81,117,184`). |
| `src/sif/indexing/incremental.py` | `src/sif/indexing/parser.py` | per-file `create_parser(file_path) or TextParser()` | WIRED | Import + call site at `incremental.py:393`. |
| `src/sif/database/repositories.py` | `src/sif/core/models.py` | canonical metadata serializer on create/update | WIRED | Import `canonical_metadata_json` + both SQL parameter sites (`repositories.py:192,274`). |
| `src/sif/indexing/incremental.py` | `src/sif/database/repositories.py` | `IndexMetaRepository` marker reads/writes; `_doc_repo.update` fast path | WIRED | Import (`incremental.py:29`) + calls at `:91,156,212` and fast-path update. |
| `src/sif/indexing/watcher.py` | `src/sif/indexing/incremental.py` | `result.reindexed_paths` into embed leg | WIRED | `watcher.py:906,924`. |
| `src/sif/search/hybrid.py` | `src/sif/search/context_attach.py` | every pipeline exit calls `enrich_results` once | WIRED | `hybrid.py:19,356,367,379,484`; spy test passes. |
| `src/sif/search/context_attach.py` | `src/sif/search/staleness.py` | `enrich_results` composes staleness after attach | WIRED | `context_attach.py:41` import + composition at `:342`. |
| `src/sif/cli/commands/search.py` | `src/sif/search/context_attach.py` | one call per direct CLI exit | WIRED | `search.py:41,613,872-874`. |
| `src/sif/mcp/backend.py` | `src/sif/search/context_attach.py` | fallback enriches once before re-map | WIRED | `backend.py:30,490,501,534,609,676-678`; pipeline path not re-enriched. |
| `src/sif/cli/commands/search.py` | `src/sif/search/bm25.py` / `hybrid.py` | `SearchOptions(offset=...)`, single slice owner | WIRED | Imports at `search.py:40,42`; offset threaded at `:581,807,1091`; searchers own their slice. |
| `src/sif/mcp/backend.py` | `src/sif/search/hybrid.py` | MCP offset reaches `SearchOptions` and the pipeline slice | WIRED | `backend.py:33` + options construction at `:459-460,599,663-664`; pipeline call. |
| `src/sif/search/vector.py` | `src/sif/search/rrf.py` | deduped rows feed fusion; chunk fields survive | WIRED | Dedup output at `vector.py:296-322`; `hybrid.py:20` fuses with `fuse_key_for`; `rrf.py:36-47` merges chunk fields. |
| `src/sif/search/hybrid.py` | `src/sif/search/rrf.py` | both fuses pass `key=fuse_key_for(options.per_chunk)` | WIRED | Exactly two fuse sites, both keyed (`hybrid.py:150-155,451-455`). |
| `src/sif/search/bm25.py` | `documents_fts` | bound `bm25(documents_fts, ?, ?)`; title column second | WIRED | Both SQL branches bind `[content_weight, title_weight, query]` (`bm25.py:125,147`). |
| `src/sif/search/bm25.py` | `src/sif/core/models.py` | `SearchOptions.title_weight` internal override | WIRED | Field read at `bm25.py:85`; no public knob. |
| `src/sif/database/schema.py` | `documents_fts_v` / documents triggers | drop vocab → rebuild → recreate vocab/triggers | WIRED | DDL sequence at `schema.py:529-665`; structural test. |
| `src/sif/mcp/backend.py` | `src/sif/database/database.py` | startup `init_schema(embedding_dim=...)` | WIRED | `backend.py:290`; tests pass. |
| `src/sif/mcp/tools.py` (Phase 22 successor to `handlers.py`) | `src/sif/mcp/backend.py` | offset/per_chunk validated then forwarded | WIRED | Signature-derived schema (`tools.py:137-139,317,356-357`) + `backend.py:459-460,599,663-664`. |
| `src/sif/mcp/backend.py` | `src/sif/core/models.py` | re-map copies chunk fields/vectors_stale | WIRED | Explicit metadata dict (`backend.py:190-197`); tests assert exact set. |
| `src/sif/cli/commands/eval.py` | `src/sif/search/personal_bench.py` | comparison rendering reads `legs`/`leg_splits` | WIRED | Import (`eval.py:43`) + rendering (`:553-556`); fresh compare output contains both. |
| `bench/d12-verdict.json` | `src/sif/search/bm25.py` | recorded decision selects pinned `_TITLE_WEIGHT` | WIRED | Artifact `pinned_title_weight=1.0`; constant 1.0 + comment + test pin. |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
| -------- | ------------- | ------ | ------------------ | ------ |
| `src/sif/cli/commands/search.py` | `results` | `BM25Searcher.search` / `VectorSearcher.search` / `SearchPipeline.search` | Yes — real SQL/KNN rows, enriched at entry | ✓ FLOWING |
| `src/sif/mcp/backend.py` | `core_results` → re-mapped `SearchResult.metadata` | pipeline search or BM25 fallback | Yes — explicit field copy, no static return | ✓ FLOWING |
| `src/sif/search/vector.py` | `candidates` / `page` | vec0 KNN JOIN to `document_chunks` | Yes — real distance-ordered rows | ✓ FLOWING |
| `src/sif/search/hybrid.py` | `fused_results` / `results` | BM25 + vector legs through RRF | Yes — real leg outputs, one slice | ✓ FLOWING |
| `src/sif/search/bm25.py` | cursor rows | `documents_fts` MATCH with weighted `bm25()` | Yes — real FTS scan | ✓ FLOWING |
| `tests/fixtures/bench/heldout_defaults.json` | static metrics | deterministic `build_bench_db`/`ConceptEmbedder` reproduction | N/A — recorded measurement artifact | N/A |
| `bench/b0.json`, `bench/b1.json`, `bench/d12-verdict.json` | static evidence | saved personal-eval runs / sweep output | N/A — recorded evidence; independently reproduced this pass | N/A |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
| -------- | ------- | ------ | ------ |
| Phase-targeted unit/integration suites | `pytest -q --no-cov tests/unit/{indexing,database,search,cli} tests/unit/cli/test_search*.py tests/unit/cli/test_eval.py tests/unit/cli/test_index.py tests/unit/mcp/test_backend.py tests/unit/mcp/test_tools.py tests/integration/{test_search_correctness,test_incremental_equivalence,test_embed_idempotency}.py` | 1493 passed in 34.12s | ✓ PASS |
| Focused snapshot/migration/pagination groups | `pytest tests/unit/search/test_bench_snapshot.py tests/unit/database/test_schema_title_fts.py::TestTitleFtsMigration tests/integration/test_search_correctness.py::TestConsistentPagination ...::TestChunkyDocumentDedup` | 31 passed in 1.44s | ✓ PASS |
| Full regression gate (CLAUDE.md) | `env -u FORCE_COLOR NO_COLOR=1 pytest -q --no-cov` | 3234 passed, 1 skipped (unrelated live-launchd opt-in) in 124.45s | ✓ PASS |
| 618997c floor/pin behavior | `pytest tests/unit/search/test_bm25.py::TestWeightedBM25::test_pinned_title_weight_is_the_measured_d12_value tests/unit/search/test_personal_bench.py` | 160 passed in 3.86s | ✓ PASS |
| Checksum contract behavior | inline `canonical_metadata_json`/`compute_checksum` check | reorder same True; frontmatter edit changes True; body edit changes True; date round-trip True | ✓ PASS |
| B0 reproduces at offset=0 / min_score=0 | `SIF_DB_PATH=.planning/tmp/phase19/bench.db SIF_CACHE_DIR=.planning/tmp/phase19/cache sif eval --personal --bm25-only -c bench-fixture --compare bench/b0.json --json --no-save` | n=100, mean delta 0.0, helped 0 / hurt 0 / unchanged 100; legs title n=50 / body n=50 delta 0.0; leg_splits title heldout n=23, body heldout n=26, both delta 0.0; 3 suppressed groups named on stderr | ✓ PASS |
| B1 self-comparison + post-title baseline | same command with `--compare bench/b1.json` | n=100, mean 0.0, unchanged 100; title heldout baseline 1.0; body heldout baseline 0.900634933653854; `warrants_default_change` present under `comparison.gate` | ✓ PASS |
| D-12 verdict artifact shape | `python -c` parse of `bench/d12-verdict.json` | `decision=rejected`, `pinned_title_weight=1.0`, candidates 2.0/3.0/4.0 each with title/body held-out n=23/26, mean delta 0.0, `sufficient=true`, `winner=false` | ✓ PASS |
| Title-weight constant is pinned at the measured value | `test_pinned_title_weight_is_the_measured_d12_value` + source read | `_CONTENT_WEIGHT = 1.0`, `_TITLE_WEIGHT = 1.0`; test passes | ✓ PASS |
| Scratch index shape | sqlite inspection of `.planning/tmp/phase19/bench.db` | 150 documents, two-column `documents_fts` DDL, `idx_documents_mtime` present | ✓ PASS |
| Generated docs carry the public flags and are clean | `python scripts/generate_cli_ref.py`; `python scripts/generate_config_ref.py`; grep `--offset`/`--per-chunk` | Generators exit 0 with no diff; 3 `--offset` rows (search/vsearch/query), 2 `--per-chunk` rows (vsearch/query) | ✓ PASS |

### Probe Execution

No probes: no `scripts/*/tests/probe-*.sh` exist (find returned nothing), and no PLAN/SUMMARY declares a probe. Step 7c: SKIPPED (no probes).

### Prohibitions (must-NOT checks)

All 30 plan-declared prohibitions were re-checked against the current code. These plans carry bare `statement` entries (no `status`/`verification` field); they are treated as judgment-tier planner guardrails, and this table is a non-authoritative LLM-judge verdict, not a human resolution. `prohibitions_flagged: 0`.

| Plan | # | Prohibition | Status | Current-code evidence |
| ---- | - | ----------- | ------ | --------------------- |
| 19-01 | 1 | No body-only change-detection hash | ✓ PASS | `compute_checksum` hashes body + NUL + full frontmatter (`models.py:64-72`). |
| 19-01 | 2 | No alteration of the Markdown body path | ✓ PASS | `frontmatter.loads` body extraction unchanged (`parser.py:57-90`); parser tests pass. |
| 19-01 | 3 | No runtime dependency for parsing/serialization | ✓ PASS | stdlib `hashlib`/`json` only. |
| 19-02 | 1 | Marker never cleared before a clean pass | ✓ PASS | Marker written only after the loop and `failed_stored == 0` (`incremental.py:210-212`). |
| 19-02 | 2 | No re-chunk/re-embed when the body did not change | ✓ PASS | Metadata fast path returns before purging chunks/embeddings (`incremental.py:431-446`). |
| 19-02 | 3 | Migration never triggered from drift checks or `update_paths` | ✓ PASS | `update_paths` passes `migrating=False` and never touches the marker (`incremental.py:318-322`). |
| 19-03 | 1 | No persisted staleness flag or per-result embedding query | ✓ PASS | Staleness derived from the `embedded_documents` shadow at query time (`staleness.py` docstring + implementation). |
| 19-03 | 2 | No loss of context descriptions/staleness markers while removing attaches | ✓ PASS | Attach sets only on match, never clobbers (`context_attach.py:284-315`); enrichment recomputes staleness at every exit. |
| 19-03 | 3 | No SQL path pre-filter for context attachment | ✓ PASS | `_CONTEXTS_SQL` filters only `context_type='path'`; both sides normalized in Python (`context_attach.py:51-53,109-110`). |
| 19-04 | 1 | No double attach on the MCP pipeline path | ✓ PASS | Only fallback exits call `enrich_results`; pipeline output is returned as enriched (`backend.py:490,501,534`). |
| 19-04 | 2 | Baseline scratch DB/cache not committed | ✓ PASS | `.planning/tmp/phase19/` is untracked; git status shows no database/cache files. |
| 19-04 | 3 | Baseline not recorded before CORR-01 landed | ✓ PASS | B0 `created_at` 2026-11-15T03:25:51Z after 19-01/19-02; docs describe it as the post-CORR-01 engine. |
| 19-05 | 1 | No interpolation of offset/limit/min_score into SQL | ✓ PASS | All values bound (`bm25.py:95-97,118-164`; vector KNN params; options pass-through). |
| 19-05 | 2 | `min_score` never applied after pagination | ✓ PASS | Threshold inside the FTS CTE before `LIMIT ? OFFSET ?` (`bm25.py:94-97,138-162`). |
| 19-05 | 3 | No double-applied offset between pipeline and hybrid | ✓ PASS | Pipeline calls hybrid with `offset=0` and slices once (`hybrid.py:410-427,482-484`). |
| 19-06 | 1 | RRF scoring math/weights/k unchanged by dedup | ✓ PASS | Score expression untouched; only grouping key/metadata merge added (`rrf.py`); goldens pass. |
| 19-06 | 2 | No duplicate document rows from default vector/hybrid output | ✓ PASS | Vector grouping (`vector.py:296-322`) + hybrid safety-net dedup (`hybrid.py:176`). |
| 19-06 | 3 | `fetch_k` escalation bounded by an independent ceiling | ✓ PASS | `_MAX_FETCH_K = 2048`, clamped every escalation (`vector.py:22-25,231`). |
| 19-06 | 4 | Vector chunk identity not dropped when a doc is in both legs | ✓ PASS | `_merge_chunk_metadata` adopts non-null chunk fields (`rrf.py:36-47`). |
| 19-07 | 1 | No per-chunk flag on document-level surfaces | ✓ PASS | `sif search` has no option; `lex_search` schema has offset only (`tools.py:317-326`). |
| 19-07 | 2 | Chunk fields never silently dropped at the MCP re-map | ✓ PASS | Explicit metadata dict (`backend.py:190-197`); exact-set tests pass. |
| 19-07 | 3 | Generated docs not hand-edited | ✓ PASS | `generate_cli_ref.py`/`generate_config_ref.py` ran clean with no diff. |
| 19-08 | 1 | No reliance on `CREATE VIRTUAL TABLE IF NOT EXISTS` to add the title column | ✓ PASS | `_fts_column_names()` detects and drives drop/recreate/rebuild (`schema.py:451-536`). |
| 19-08 | 2 | `documents_fts_v` dropped before `documents_fts` | ✓ PASS | Drop order at `schema.py:529` then `:536`. |
| 19-08 | 3 | Column weights never interpolated into SQL | ✓ PASS | Bound as `?` parameters (`bm25.py:97,125,147`). |
| 19-08 | 4 | No CJK lexical title win promised or tested | ✓ PASS | Claim scoped to EN-style tokenized titles (`docs/benchmarking.md:255-257`); no CJK title assertion. |
| 19-09 | 1 | Title weight not a Settings field or CLI flag | ✓ PASS | grep over CLI/config/docs returns no hits. |
| 19-09 | 2 | No title-weight win declared inside noise/from tuning-only data | ✓ PASS | Artifact records rejection; `_TITLE_WEIGHT = 1.0`; docs record the rejection. |
| 19-09 | 3 | No shipped title weight regressing body/hybrid held-out beyond the 0.01 tie rule | ✓ PASS | Body held-out mean delta 0.0 (≥ -0.01); candidates rejected. |
| 19-09 | 4 | No MCP-only deployment left on the pre-title schema | ✓ PASS | `SearchBackend.__init__` runs `init_schema` (`backend.py:290`); startup tests pass. |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
| ----------- | ---------- | ----------- | ------ | -------- |
| CORR-01 | 19-01, 19-02 | Frontmatter-only edits become searchable (parser dispatch + metadata-aware checksum, ONE shared forced-reindex migration, md body byte-identical, YAML `---` fixed) | ✓ SATISFIED | Canonical checksum + dispatch + metadata fast path + single `CONVENTION_VERSION=2` migration; tests pass. |
| CORR-02 | 19-06, 19-07 | One result per document by default (pre-fusion dedup, `--per-chunk`, bench before/after, goldens rationale) | ✓ SATISFIED | Vector dedup + chunk identity + per-chunk fusion + surfaces + B0/B1 + snapshot/SC1 evidence. |
| CORR-03 | 19-05 | Deterministic pagination (CLI/MCP offset, single slice, BM25 min_score order, offset=0 contract) | ✓ SATISFIED | Offset surfaces + one slice owner + pre-pagination threshold + global ranks; B0 independently reproduced. |
| CORR-04 | 19-08, 19-09 | Title-aware ranking (title-FTS migration, rewritten triggers, measured bm25 weights, mtime index, vocab survival) | ✓ SATISFIED | Two-column FTS + triggers + weighted bound bm25 + mtime index + populated-DB vocab/DYM tests + D-12 rejection recorded. |
| CORR-05 | 19-03, 19-04 | No redundant attach (ONE context/staleness attach at pipeline exit) | ✓ SATISFIED | Raw searchers + `enrich_results` owners at pipeline/CLI/MCP fallback; spies prove exactly one. |

No orphaned requirements: `.planning/REQUIREMENTS.md` maps exactly CORR-01..CORR-05 to Phase 19, and all five appear in this phase's plan frontmatter. CORR-06 is mapped to Phase 21 and is correctly absent from Phase 19 plans.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
| ---- | ---- | ------- | -------- | ------ |
| — | — | No `TBD`/`FIXME`/`XXX`/`TODO`/`HACK`/`PLACEHOLDER` markers in `src/sif` or `tests` | — | Debt-marker gate clean (grep count 0). |
| — | — | No stub returns in changed code | — | Empty-list returns are exclude-all sentinels (`bm25.py`, `vector.py`) and accumulators, not stubs; all render paths receive real query rows. |
| — | — | No new Phase 19 runtime dependency for parsing or serialization | — | Serialization uses stdlib `json`; parser stack pre-exists. Later-phase dependencies are outside Phase 19's prohibition. |

Deferred Info findings from `19-REVIEW-DISPOSITION.md` (not phase-goal blockers, recorded for completeness):

| Finding | Severity | Impact on Phase 19 |
| ------- | -------- | ------------------ |
| IN-01 vector scores L2-derived but documented as cosine | Info / deferred | Pre-existing metric-label issue; distance ordering (and thus dedup/pagination) is unaffected. |
| IN-02 rerank rebuild drops `vectors_stale` | Info / deferred | Latent; the pipeline enriches after rerank, so `mark_vector_staleness` recomputes the flag on every pipeline exit — CORR-05 marker preservation holds. |
| IN-03 docs mention MCP `vec_search` per-chunk while the tool is unregistered | Info / deferred | Resolved by Phase 22: `vec_search` is now registered and its signature exposes `per_chunk`; wire goldens confirm. |
| IN-05 `BM25Searcher.search_chunks` min_score after LIMIT/OFFSET, no global ranks | Info / deferred | No production caller (`grep src/` finds only tests); user pagination surfaces use `search()`, which is correct. |
| IN-06 MCP backend silently creates an empty index at a nonexistent `SIF_DB_PATH` | Info / deferred | Diagnosability warning, not data loss; outside CORR-01..05. |

### Human Verification Required

N/A — backend/search-infrastructure phase with no user-facing UI surface. Every acceptance criterion is verified programmatically by code inspection plus a passing automated test or an independently reproduced measurement artifact; zero truths remain present-but-behavior-unverified. Prohibitions are the only judgment-tier items and all 30 were checked against current code with no violation found.

### Gaps Summary

No gaps and no regressions. All five roadmap success criteria and all 63 functional plan must-haves hold in the current tree at `618997c`:

- CORR-01: metadata-aware checksums, per-file parser dispatch, the YAML `---` whole-file fix, the D-07 metadata fast path, and one shared per-collection convention migration are implemented and exercised by tests; the Markdown body path is unchanged.
- CORR-02: per-document dedup lives inside `VectorSearcher` before RRF, chunk identity and `chunk_matches` are in the result contract, per-chunk mode survives both fuse sites, and the contract change is recorded with B0/B1, the held-out snapshot rationale, the SC1/RRF goldens, and the chunky-document regression.
- CORR-03: CLI and MCP offsets are validated, each query path has exactly one offset slice owner, BM25 `min_score` is applied before `LIMIT/OFFSET`, ranks are global, and offset=0 reproduces B0 exactly (independently rerun this pass: n=100, mean 0.0).
- CORR-04: the title-FTS detect-and-rebuild migration is durable across reopen, populates exactly once, preserves the vocab shadow/DYM, rewrites the triggers with `title`, and binds measured column weights; the `mtime` index exists; MCP-only hosts migrate at startup. The D-12 2–4× band was measured and rejected with numbers (title held-out already at the 1.0 ceiling; body held-out flat), which CONTEXT D-12 explicitly sanctions; `_TITLE_WEIGHT` is pinned at 1.0.
- CORR-05: the searchers are raw producers and exactly one `enrich_results` composition runs per public exit; no `_attach_contexts` remains.

The only artifact-path deviation is `src/sif/mcp/handlers.py`, intentionally deleted by Phase 22 and replaced by the signature-derived schema in `src/sif/mcp/tools.py`; the underlying offset/per_chunk schema property is verified at the successor path and in the current wire goldens. No override is required because the must-have truth itself holds.

The `618997c` delta (`math.fsum` mean + rounded 1/N noise-floor comparison) strengthens determinism across py3.10/3.11; it changes no Phase 19 ranking, pagination, freshness, or enrichment behavior, and the bench baselines and held-out evidence remain valid (B0/B1 comparisons reproduced exactly; 160 personal-bench/pin tests and the full 3234-test suite pass).

---

_Verified: 2026-11-18T11:55:04Z_
_Verifier: Claude (gsd-verifier)_
