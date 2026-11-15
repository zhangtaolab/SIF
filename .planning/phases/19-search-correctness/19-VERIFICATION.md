---
phase: 19-search-correctness
verified: 2026-11-15T05:26:37Z
status: passed
score: 63/63 must-haves verified
covered_files: [".planning/phases/19-search-correctness/19-01-PLAN.md", ".planning/phases/19-search-correctness/19-01-SUMMARY.md", ".planning/phases/19-search-correctness/19-02-PLAN.md", ".planning/phases/19-search-correctness/19-02-SUMMARY.md", ".planning/phases/19-search-correctness/19-03-PLAN.md", ".planning/phases/19-search-correctness/19-03-SUMMARY.md", ".planning/phases/19-search-correctness/19-04-PLAN.md", ".planning/phases/19-search-correctness/19-04-SUMMARY.md", ".planning/phases/19-search-correctness/19-05-PLAN.md", ".planning/phases/19-search-correctness/19-05-SUMMARY.md", ".planning/phases/19-search-correctness/19-06-PLAN.md", ".planning/phases/19-search-correctness/19-06-SUMMARY.md", ".planning/phases/19-search-correctness/19-07-PLAN.md", ".planning/phases/19-search-correctness/19-07-SUMMARY.md", ".planning/phases/19-search-correctness/19-08-PLAN.md", ".planning/phases/19-search-correctness/19-08-SUMMARY.md", ".planning/phases/19-search-correctness/19-09-PLAN.md", ".planning/phases/19-search-correctness/19-09-SUMMARY.md", ".planning/phases/19-search-correctness/bench/b0.json", ".planning/phases/19-search-correctness/bench/b1.json", ".planning/phases/19-search-correctness/bench/d12-verdict.json", "docs/benchmarking.md", "docs/cli-reference.md", "src/sif/cli/commands/eval.py", "src/sif/cli/commands/index.py", "src/sif/cli/commands/search.py", "src/sif/core/models.py", "src/sif/database/database.py", "src/sif/database/repositories.py", "src/sif/database/schema.py", "src/sif/indexing/incremental.py", "src/sif/indexing/parser.py", "src/sif/indexing/watcher.py", "src/sif/mcp/backend.py", "src/sif/mcp/handlers.py", "src/sif/mcp/protocol.py", "src/sif/search/bm25.py", "src/sif/search/context_attach.py", "src/sif/search/hybrid.py", "src/sif/search/personal_bench.py", "src/sif/search/rerank.py", "src/sif/search/rrf.py", "src/sif/search/staleness.py", "src/sif/search/vector.py", "tests/fixtures/bench/heldout_defaults.json", "tests/integration/test_embed_idempotency.py", "tests/integration/test_incremental_equivalence.py", "tests/integration/test_search_correctness.py", "tests/unit/cli/test_eval.py", "tests/unit/cli/test_index.py", "tests/unit/cli/test_search.py", "tests/unit/cli/test_search_pagination.py", "tests/unit/database/test_repositories.py", "tests/unit/database/test_schema.py", "tests/unit/database/test_schema_title_fts.py", "tests/unit/indexing/test_incremental.py", "tests/unit/indexing/test_parser.py", "tests/unit/indexing/test_parser_checksum.py", "tests/unit/indexing/test_watcher.py", "tests/unit/mcp/test_backend.py", "tests/unit/search/test_bench_snapshot.py", "tests/unit/search/test_bm25.py", "tests/unit/search/test_collection_filter.py", "tests/unit/search/test_context_attach.py", "tests/unit/search/test_hybrid.py", "tests/unit/search/test_personal_bench.py", "tests/unit/search/test_rrf.py", "tests/unit/search/test_staleness.py", "tests/unit/search/test_vector.py"]
covered_digest: "v4:sha256:c36ee041eba91759a8d3b20445b4e4b970b6543d81dc2918fa0d6df3844f462b"
behavior_unverified: 0
overrides_applied: 0
---

# Phase 19: Search Correctness Verification Report

**Phase Goal:** Search results are fresh, deduplicated, deterministically paginable, and title-aware — the trust floor that metadata filtering (20) builds on, with every ranking-contract change measured before/after on the Phase 18 instrument.
**Verified:** 2026-11-15T05:26:37Z
**Status:** passed
**Re-verification:** No — initial verification

## Goal Achievement

### Roadmap Success Criteria

| # | Success Criterion | Status | Evidence |
| --- | ----------------- | ------ | -------- |
| 1 | Frontmatter-only edits become searchable after the next index update; parser dispatch + metadata-aware checksum in ONE plan with ONE shared forced-reindex migration; Markdown body path byte-identical; YAML `---` empty-body bug fixed | ✓ VERIFIED | `compute_checksum()` hashes body + NUL + canonical full frontmatter (`src/sif/core/models.py:51-59`); all three parsers call it; `IncrementalIndexer._process_file` dispatches `create_parser(file_path) or TextParser()` and stores `parsed.checksum` (`src/sif/indexing/incremental.py:393,482`); `CONVENTION_VERSION = 2` + one per-collection `convention:<id>` marker drives exactly one forced re-parse (`incremental.py:150-212`); Markdown still uses `frontmatter.loads` and keeps body bytes; `CodeParser` reads `.yaml/.yml` whole (no `---` truncation). |
| 2 | One result per document by default; dedup inside VectorSearcher pre-fusion; `--per-chunk` escape hatch; ranking-contract change recorded with bench before/after and goldens updated with rationale | ✓ VERIFIED | `VectorSearcher._candidates` groups by `document_id` after `min_score`, best-distance wins, `chunk_matches` counts pre-dedup rows (`src/sif/search/vector.py:149-176`); `--per-chunk` on vsearch/query only and MCP `per_chunk` on query/vec inputs; both RRF fuse sites use `fuse_key_for(options.per_chunk)`; B0/B1 saved runs + `docs/benchmarking.md` "CORR-02 Per-Document Dedup" + regenerated SC1/RRF goldens and held-out rationale. |
| 3 | Deterministic pagination — CLI `--offset` and MCP offset return the correct next page; hybrid owns ONE offset slice; searchers return from rank 0; BM25 min_score order fixed; offset=0 reproduces the recorded contract | ✓ VERIFIED | `--offset` (`click.IntRange(min=0)`) on search/vsearch/query (`src/sif/cli/commands/search.py`); `QueryInput.offset = Field(default=0, ge=0)` + hand-written schema; `HybridSearcher` calls legs at offset 0 and slices once, pipeline slices once after rerank/snippets; BM25 binds `rank >= 1 - 1/min_score` inside the FTS CTE before `LIMIT ? OFFSET ?`; global `rank = offset + position`; independent B0/B1 rerun reports n=100, mean delta 0.0, 100 unchanged. |
| 4 | Title-aware ranking — title-FTS detect-and-rebuild migration + rewritten triggers + bench-measured bm25() column weights + mtime index; `documents_fts_v` vocab shadow survives rebuild on a populated DB | ✓ VERIFIED | `_fts_column_names()` gate + two-column DDL + drop-vocab → drop-triggers/table → single `('rebuild')` → recreate-vocab/triggers under `SAVEPOINT sp_fts_tables` (`src/sif/database/schema.py:287-461`); triggers carry `(rowid, content, title)` incl. `old.title`; `bm25(documents_fts, ?, ?)` bound weights in both branches (`src/sif/search/bm25.py`); `idx_documents_mtime` created; populated-DB migration/vocab/DYM tests pass; D-12 sweep measured 2.0/3.0/4.0 against B1 and recorded a rejection with numbers (`bench/d12-verdict.json`), pinned `_TITLE_WEIGHT = 1.0`. |
| 5 | Results without redundant attach work — double-attach eliminated; exactly ONE context/staleness attach at pipeline exit | ✓ VERIFIED | `enrich_results` composes `attach_path_contexts` then `mark_vector_staleness` (`src/sif/search/context_attach.py:66-85`); searchers return raw results (no `_attach_contexts` anywhere under `src/sif/search`); pipeline has exactly 4 enrichment exits; direct CLI search/vsearch add 1 each; MCP fallback adds 1 and the pipeline path adds 0; spy tests pass. |

**Score:** 5/5 roadmap success criteria verified.

### Observable Truths (Plan Must-Haves)

The `UNCLASSIFIED-FLAGGED` lines in PLAN frontmatter are probe-classification flags, not functional must-haves; they are excluded from the score. All 63 functional plan truths are verified.

#### Plan 19-01 — CORR-01 (parser dispatch, checksum, canonical metadata)

| # | Truth | Status | Evidence |
| --- | ----- | ------ | -------- |
| 1 | `.yaml`/`.yml` starting with `---` is parsed by `CodeParser` as the whole file in all three forms | ✓ VERIFIED | `create_parser` maps `.yaml/.yml` to `CodeParser`; `CodeParser.parse` reads whole file (`parser.py:163-193`); `test_yaml_leading_separator_is_parsed_as_whole_file` passes. |
| 2 | Every parser computes sha256(body + NUL + canonical full frontmatter) with sort_keys/default=str/ensure_ascii=False/compact + recursive key coercion; frontmatter edit changes checksum, key reorder does not, body edit does | ✓ VERIFIED | `compute_checksum()` + `canonical_metadata_json()` (`models.py:16-59`); all parsers call it; `test_parser_checksum.py` 8-test matrix passes. |
| 3 | Markdown body extraction stays byte-identical; `frontmatter.loads` still strips frontmatter | ✓ VERIFIED | `MarkdownParser.parse` unchanged in body path; checksum only added; parser tests pass. |
| 4 | `.md` with `date: 2024-01-01` stores without TypeError and metadata JSON round-trips to the hashed canonical string | ✓ VERIFIED | `canonical_metadata_json(default=str)`; repository create/update persist it (`repositories.py:164,233`); `test_yaml_date_frontmatter_indexes_without_type_error` passes. |
| 5 | `IncrementalIndexer` stores `parsed.checksum`, not a body-only fallback | ✓ VERIFIED | `incremental.py:482` passes `checksum=parsed.checksum`; incremental tests pass. |
| 6 | An extension outside `create_parser`'s map falls back to `TextParser` | ✓ VERIFIED | `incremental.py:393` `create_parser(file_path) or TextParser()`; `test_per_file_parser_dispatch_with_text_fallback` passes. |

#### Plan 19-02 — CORR-01 (fast path, convention migration, watch signal)

| # | Truth | Status | Evidence |
| --- | ----- | ------ | -------- |
| 7 | `index_meta` exists on fresh/migrated DBs with per-collection `convention:<id>` keys; `drop_all` removes it | ✓ VERIFIED | `schema.py:186-197`; `drop_all` lists `index_meta`; `IndexMetaRepository.get/set` (`repositories.py:646-672`); schema tests pass. |
| 8 | First `update_collection` with absent/old marker forces exactly one re-parse pass; one `migrate <N>` event with documents; empty collection silent; marker written only after a clean pass | ✓ VERIFIED | `incremental.py:150-212`; `TestConventionMigration` (5 tests) + CLI migrate-render test pass. WR-01 refined "zero files failed" to "zero *stored* files failed" so a permanently unparseable never-stored file cannot strand the migration; stored-data failures still block the marker (`incremental.py:189-212`), preserving the truth's intent. |
| 9 | Metadata-only edit updates title/metadata/checksum/mtime/file_size, keeps chunks and embeddings | ✓ VERIFIED | `_process_file` fast path `incremental.py:431-446`; `TestMetadataFastPath` + `test_frontmatter_only_cycle_preserves_chunks_and_moves_title` pass. |
| 10 | Body edit deletes that document's chunks and embeddings before update | ✓ VERIFIED | `incremental.py:451-458`; body-edit fast-path test passes. |
| 11 | `--force` skips checksum skip but unchanged body takes the metadata fast path | ✓ VERIFIED | `incremental.py:379-383,410-446`; force test passes. |
| 12 | `update_paths` never starts a migration but uses body-vs-metadata discrimination | ✓ VERIFIED | `update_paths` has no marker read/write (`incremental.py:242-352`); test patches `IndexMetaRepository.get` to raise and passes. |
| 13 | `reindexed_paths` contains only added/body-changed paths; watcher embed leg selects from it; metadata-only edit produces no new chunk/vector rows | ✓ VERIFIED | `incremental.py:167-185,287-326`; watcher `_run_burst/_run_reconcile` feed `reindexed_paths`; `TestEmbedDepth` regressions pass. |
| 14 | Parse failure leaves marker unwritten and counted, so the next pass retries | ✓ VERIFIED | `failed_stored` accounting + marker gate (`incremental.py:165-212`); failure-retry tests pass. |

#### Plan 19-03 — CORR-05 (search-core single attach)

| # | Truth | Status | Evidence |
| --- | ----- | ------ | -------- |
| 15 | BM25/Vector/Hybrid searchers no longer attach contexts/staleness; return raw results | ✓ VERIFIED | No `_attach_contexts` in `src/sif/search`; searcher contract tests pass. |
| 16 | `SearchPipeline.search` calls the shared enrichment exactly once on BM25, VECTOR, HYDE, and hybrid exits | ✓ VERIFIED | `hybrid.py:251,257,264,357`; spy test counts exactly one call per exit; full suite passes. |
| 17 | `enrich_results(db, results)` composes attach then staleness; contexts keep two-sided `normalize_path` with no SQL prefilter and never clobber on miss; staleness is one batched scan with display gate and `None` degradation | ✓ VERIFIED | `context_attach.py:25-85`; `staleness.py:36-100`; context/staleness tests pass. |
| 18 | A spy test counts exactly one enrichment per exit; searcher tests assert none inside searchers | ✓ VERIFIED | `test_staleness.py:276-347`; `TestBM25SearcherEnrichmentContract`, `TestVectorSearcherEnrichmentContract`, `TestHybridContextAttachment` pass. |
| 19 | `staleness.py` D-09 docstring names the single `enrich_results` owner and no searcher `_attach_contexts` reference | ✓ VERIFIED | `staleness.py:11-18`; grep for `_attach_contexts` under `src/sif/search` returns nothing. |

#### Plan 19-04 — CORR-05 (entry points + B0)

| # | Truth | Status | Evidence |
| --- | ----- | ------ | -------- |
| 20 | CLI `sif search` and `sif vsearch` call `enrich_results` exactly once after the direct searcher; output keeps context/staleness | ✓ VERIFIED | `search.py:545,767`; `TestSingleEnrichmentOwner` (CLI) passes. |
| 21 | MCP BM25 fallback enriches exactly once; pipeline path is not enriched again at the boundary | ✓ VERIFIED | `backend.py:209-216`; `TestSingleEnrichmentOwner` (MCP) passes. |
| 22 | MCP re-map still forwards `rank`, `collection_name`, `vectors_stale` | ✓ VERIFIED | `backend.py:230-240`; MCP re-map set tests pass. |
| 23 | B0 is a saved personal-eval run on the post-CORR-01 engine over the committed 150-doc fixture corpus with `--bm25-only`, ≥50 queries, `--compare` zero mean delta | ✓ VERIFIED | `bench/b0.json`: 100 queries, fingerprint `8c006123784348d1`, retrieval bm25; independent rerun on the scratch index returns n=100, mean delta 0.0, 100 unchanged. |

#### Plan 19-05 — CORR-03 (deterministic pagination)

| # | Truth | Status | Evidence |
| --- | ----- | ------ | -------- |
| 24 | `sif search`/`vsearch`/`query` accept `--offset` (`IntRange(min=0)`, default 0); past-the-end returns an empty page | ✓ VERIFIED | `search.py:462-465,649-652,841-844`; pagination CLI tests pass. |
| 25 | Ranks are global across pages (`rank = offset + position`) | ✓ VERIFIED | BM25 `bm25.py:169`, vector `vector.py:142-143`, hybrid `_paginate`; tests pass. |
| 26 | `limit=l offset=o` equals the `[o:o+l]` slice of `limit=o+l offset=0` for BM25/vector/hybrid | ✓ VERIFIED | `TestConsistentPagination` integration tests (real schema + vec0) pass. |
| 27 | BM25 applies `min_score` before LIMIT/OFFSET via bound threshold `1 - 1/min_score`, `rank >= threshold`; omitted when min_score=0 | ✓ VERIFIED | `bm25.py:93-96,110-152`; all params bound; BM25 threshold tests pass. |
| 28 | Hybrid calls legs with `offset=0`, `limit+offset`, one slice after fusion, and paginates early single-leg returns | ✓ VERIFIED | `hybrid.py:82-102,133-135`; hybrid/pipeline offset tests pass. |
| 29 | Reranker window is `max(candidate_limit, limit+offset)` when offset>0, `candidate_limit` at offset=0; `top_k = limit+offset`; beyond-cap requests get a full page | ✓ VERIFIED | `hybrid.py:295-348`; `test_search_correctness.py` reranker-window cases pass. |
| 30 | Pipeline passes offset=0 to hybrid and owns one slice; BM25/VECTOR/HYDE branches let the searcher own the slice | ✓ VERIFIED | `hybrid.py:249-264,288-357`; pipeline offset tests pass. |
| 31 | MCP `query` offset `Field(default=0, ge=0)` forwarded into SearchOptions; Lex/Vec inputs validated; query schema lists offset | ✓ VERIFIED | `protocol.py:240-305`; `handlers.py:60-90`; `backend.py:143-176`; MCP offset tests pass. |
| 32 | After attach + pagination, offset=0/min_score=0 personal-eval rerun against B0 reports zero mean delta | ✓ VERIFIED | Independent rerun reproduced n=100, mean 0.0 (see Behavioral Spot-Checks). |

#### Plan 19-06 — CORR-02 (dedup, chunk identity, per-chunk fusion)

| # | Truth | Status | Evidence |
| --- | ----- | ------ | -------- |
| 33 | VectorSearcher returns one row per document by default: grouped by document_id in best-distance order after min_score; winner carries `chunk_id`/`sequence`; `chunk_matches` counts pre-dedup rows | ✓ VERIFIED | `vector.py:149-176`; `TestVectorDocumentDedup` passes. |
| 34 | Default target `limit+offset`; `fetch_k` starts `min(max(target*4,50),2048)` and doubles only on a saturated batch while target unmet; past-cap offset returns empty page | ✓ VERIFIED | `vector.py:122-147`; escalation/ceiling tests pass. |
| 35 | A document with ≥5 matching chunks at limit=10 yields 10 distinct documents on vector and hybrid default paths | ✓ VERIFIED | `TestChunkyDocumentDedup` integration tests pass. |
| 36 | Per-chunk mode returns ungrouped chunk rows with identity; both RRF fuses group by `chunk_key` (chunk_id or document_id) selected via `fuse_key_for`; BM25 rows stay document-keyed; default path unchanged | ✓ VERIFIED | `rrf.py:10-28`; `hybrid.py:109-115,324-329`; exactly two fuse sites, both keyed; per-chunk tests pass. |
| 37 | RRF scoring math unchanged; merge adopts non-null chunk fields from the later list and keeps `max(chunk_matches)` | ✓ VERIFIED | `rrf.py:104-149` score expression untouched; `_merge_chunk_metadata`; byte-identical score tests pass. |
| 38 | `SearchResult.to_dict()` carries `chunk_id`/`sequence`/`chunk_matches`; SC1 and RRF goldens regenerated with rationale docstrings | ✓ VERIFIED | `models.py:319-326`; golden tests + rationale docstrings pass. |
| 39 | Held-out snapshot regenerated for the dedup contract with rationale; verdict keys and defaults lock valid | ✓ VERIFIED | `tests/fixtures/bench/heldout_defaults.json` rationale records pre/post numbers; snapshot reproduction tests pass. |

#### Plan 19-07 — CORR-02 (public surfaces + B1)

| # | Truth | Status | Evidence |
| --- | ----- | ------ | -------- |
| 40 | `sif query`/`sif vsearch` accept `--per-chunk`; `sif search` does not | ✓ VERIFIED | `search.py:659,889`; `TestPerChunkSurfaces` includes the search-rejection test. |
| 41 | Default CLI output exposes `chunk_matches` in table and JSON; per-chunk rows show `path#sequence` and JSON `chunk_id`/`sequence` | ✓ VERIFIED | `_title_cell` annotation + `_chunk_cell`; `to_dict`; tests pass. |
| 42 | MCP `query`/`vec_search` inputs accept `per_chunk`; handler schema lists it; backend forwards it | ✓ VERIFIED | `protocol.py:252,304`; `handlers.py:62-65,89-90`; `backend.py:150,176`; tests pass. |
| 43 | MCP re-map explicitly forwards `chunk_id`/`sequence`/`chunk_matches` | ✓ VERIFIED | `backend.py:234-240`; re-map tests pass. |
| 44 | `make docs-generate` clean; CLI reference documents `--offset` and `--per-chunk` | ✓ VERIFIED | `docs/cli-reference.md` has 3 `--offset` rows (search/vsearch/query) and 2 `--per-chunk` rows (vsearch/query); no hand-edit evidence; generator gate recorded clean. |
| 45 | B1 recorded after CORR-02 on the same scratch index; `--compare b0.json` reports per-query deltas with ≥50 paired queries; deltas written into `docs/benchmarking.md` labeled the BM25 no-drift check; held-out/SC1 old→new numbers cited | ✓ VERIFIED | `bench/b1.json` 100 queries, same fingerprint; independent compare n=100, mean 0.0; benchmarking.md §CORR-02 labels the check and cites the evidence. |

#### Plan 19-08 — CORR-04 (title-FTS migration, triggers, weighted bm25)

| # | Truth | Status | Evidence |
| --- | ----- | ------ | -------- |
| 46 | Populated DB migration drops vocab first, drops FTS/triggers, recreates two-column, runs `'rebuild'`, recreates vocab/triggers; title-only MATCH 0→1 | ✓ VERIFIED | `schema.py:315-453`; `TestTitleFtsMigration::test_title_only_match_flips_from_zero_to_one` passes. |
| 47 | Rebuild populates exactly once (no rowid/content seed); structural assertion; row counts equal; unique token one row; deleted doc not MATCHable | ✓ VERIFIED | One `documents_fts(documents_fts)` population statement; `test_single_population_row_counts_and_match_cardinality` + `test_population_is_structurally_single_and_seed_free` pass. |
| 48 | `documents_fts_v` still yields vocab after rebuild; suggest works; title UPDATE/DELETE sync; NULL titles clean; integrity_check ok | ✓ VERIFIED | Populated-DB suite passes (`test_vocab_shadow_survives_and_dym_still_works`, trigger/update/delete/NULL tests). |
| 49 | Fresh DB creates two-column directly; second `create_all` performs only detection reads | ✓ VERIFIED | `test_fresh_db_creates_two_columns_directly` + `test_second_create_all_pays_only_the_detection_read` pass. |
| 50 | Chunks FTS and its three triggers stay byte-identical | ✓ VERIFIED | Chunks DDL/triggers unchanged (content-only); trigger test asserts no title token in chunks triggers. |
| 51 | `bm25(documents_fts, ?, ?)` binds content/title weights left-to-right; 1.0/1.0 reproduces rank; constant starts 1.0; min_score before LIMIT/OFFSET | ✓ VERIFIED | `bm25.py:23-24,83-96,110-151`; `TestWeightedBM25` passes. |
| 52 | `SearchOptions.title_weight` override changes title-vs-body ordering in a behavior test; not a setting/CLI flag | ✓ VERIFIED | `models.py:354`; reorder test passes; grep finds no title-weight knob in CLI/config/docs. |
| 53 | SC1 golden and held-out snapshot regenerated for the title-column effect with rationale; snapshot verdict computable | ✓ VERIFIED | SC1 docstring + held-out rationale; reproduction tests pass. |
| 54 | No lexical CJK title win claimed or tested; claim scoped to tokenized EN-style titles | ✓ VERIFIED | `docs/benchmarking.md:255-257`; no CJK title assertion in tests. |

#### Plan 19-09 — CORR-04 (mtime index, MCP startup, per-leg gates, D-12 verdict)

| # | Truth | Status | Evidence |
| --- | ----- | ------ | -------- |
| 55 | `idx_documents_mtime` exists on fresh and migrated DBs and is in the expected index set | ✓ VERIFIED | `schema.py:518-521`; `test_mtime_index_is_created_on_fresh_and_migrated_databases` passes. |
| 56 | MCP-only process runs schema migration once in `SearchBackend.__init__` at the backend's own dimension; second construction pays detection reads only | ✓ VERIFIED | `backend.py:92-112`; `database.py:31-45`; `TestSchemaInitializationAtStartup` (4 tests) passes. |
| 57 | `ComparisonReport` exposes per-leg and per-leg×split noise gates in `--compare` JSON/table; groups <10 suppressed and named; `warrants_default_change` remains the held-out summary gate | ✓ VERIFIED | Independent `--compare` output contains `legs` (title n=50, body n=50) and `leg_splits` (title heldout n=23, body heldout n=26), suppressed groups named on stderr, `warrants_default_change` in gate. |
| 58 | Title-weight sweep opens the scratch index through `Database(...).init_schema()` and aborts unless stored `documents_fts` SQL has a title column | ✓ VERIFIED | `.planning/tmp/phase19/sweep_title_weight.py` calls `db.init_schema(embedding_dim=dim)` and `_require_title_column()` aborts on missing title; scratch migration/guard output recorded in SUMMARY. |
| 59 | Sweep evaluates 2.0/3.0/4.0 (refining at band edges) against B1's exact query set through `compare_saved_run` | ✓ VERIFIED | Sweep driver `BASE_CANDIDATES=(2.0,3.0,4.0)`, `REFINEMENTS`; `bench/d12-verdict.json` has all three candidates with GateResult fields; independent B1 compare reproduces the same held-out legs. |
| 60 | D-12 gate applied to title held-out (must be a noise-gate winner) AND body held-out (rounded mean delta ≥ -0.01) | ✓ VERIFIED | `_accepted()` requires `title["winner"]` and `round(body["mean_delta"],6) >= -0.01`; verdict shows title winner=false, body delta 0.0. |
| 61 | Pinned `_TITLE_WEIGHT` is the accepted candidate or 1.0 on rejection; `bench/d12-verdict.json` records every candidate's deltas, CI, gate results, decision | ✓ VERIFIED | Artifact: `decision="rejected"`, `pinned_title_weight=1.0`, three candidates with full `title_heldout`/`body_heldout` GateResults; `bm25.py` constant 1.0 + comment; test pins it. |
| 62 | Goldens/docs reflect the pinned weight: snapshot rationale refreshed, SC1 docstring updated, `test_bm25.py` pins constant/behavior, `docs/benchmarking.md` records the verdict; rejection valid | ✓ VERIFIED | Rationale/docstrings carry dedup + title-column + D-12 notes; `test_pinned_title_weight_is_the_measured_d12_value` passes; benchmarking.md §D-12 records the rejection. |
| 63 | Title weight is not a Settings field or CLI flag; the option override remains internal and measurement-only | ✓ VERIFIED | `grep title_weight/TITLE_WEIGHT src/sif/cli src/sif/config docs/cli-reference.md docs/configuration.md` → no hits; only `SearchOptions.title_weight` internal field and `bm25.py` module constants. |

**Score:** 63/63 plan truths verified (0 present-behavior-unverified).

### Deferred Items

None. No failed item is addressed in a later phase. The deferred Info review findings below are pre-existing/latent issues explicitly outside Phase 19 scope, not unmet phase truths.

### Advisory (New Scope, Unevidenced)

Not applicable — initial verification (advisory is a re-verification-only category). No unevidenced new-scope blockers were found.

### Required Artifacts

All 49 plan-declared artifact entries (`verify.artifacts` on all 9 plans: 4/4, 6/6, 5/5, 3/3, 8/8, 5/5, 7/7, 4/4, 7/7 passed) exist, are substantive, and are wired. Unique artifacts:

| Artifact | Expected | Status | Details |
| -------- | -------- | ------ | ------- |
| `src/sif/core/models.py` | canonical JSON/checksum helpers; chunk result fields; offset/per_chunk/title_weight options | ✓ VERIFIED | Helpers implemented; fields wired into `to_dict()`; internal-only title override. |
| `src/sif/indexing/parser.py` | parser dispatch contract; checksum; `CONVENTION_VERSION`; title-type safety | ✓ VERIFIED | `create_parser` unchanged map, all parsers use `compute_checksum`, version = 2, non-string title coercion. |
| `src/sif/indexing/incremental.py` | per-file dispatch, metadata fast path, marker, `reindexed_paths`, per-file write isolation | ✓ VERIFIED | All present; used by CLI/watch/MCP paths. |
| `src/sif/indexing/watcher.py` | embed candidates from `reindexed_paths` | ✓ VERIFIED | Burst + reconcile paths consume it. |
| `src/sif/database/repositories.py` | canonical metadata persistence; `IndexMetaRepository` | ✓ VERIFIED | create/update serialize canonically; get/set parameterized. |
| `src/sif/database/schema.py` | `index_meta`, title-FTS migration, triggers, vocab shadow, savepoint durability, mtime index | ✓ VERIFIED | DDL/rebuild/triggers present; one population statement; commit discipline. |
| `src/sif/database/database.py` | `init_schema(embedding_dim=None)` override | ✓ VERIFIED | Explicit override skips `get_settings()`; no-arg form unchanged. |
| `src/sif/search/bm25.py` | weighted bound bm25, pre-pagination min_score, global ranks | ✓ VERIFIED | Both branches bound; threshold inside CTE; ranks offset+position. |
| `src/sif/search/vector.py` | KNN chunk join, per-doc dedup, bounded escalation, per-chunk mode, single slice | ✓ VERIFIED | All present; used by vector/hybrid paths. |
| `src/sif/search/hybrid.py` | single offset slice, per-chunk key, pipeline enrichment, rerank window | ✓ VERIFIED | Both fuse sites keyed; pipeline enriches once per exit. |
| `src/sif/search/rrf.py` | optional key callable, chunk key helpers, metadata merge (math unchanged) | ✓ VERIFIED | Two call sites use the helper; score expression untouched. |
| `src/sif/search/context_attach.py` | `enrich_results` composition | ✓ VERIFIED | Used by pipeline, CLI, MCP fallback. |
| `src/sif/search/staleness.py` | D-09 docstring naming `enrich_results` | ✓ VERIFIED | Docstring updated; no `_attach_contexts` references remain. |
| `src/sif/search/personal_bench.py` | per-leg and leg×split gates | ✓ VERIFIED | `legs`/`leg_splits` in JSON; absent combos insufficient. |
| `src/sif/cli/commands/search.py` | `--offset`, `--per-chunk`, one enrichment per direct exit | ✓ VERIFIED | Flags + rendering + enrichment. |
| `src/sif/cli/commands/index.py` | migrate event rendering | ✓ VERIFIED | One-line `migrate` branch; CLI test passes. |
| `src/sif/cli/commands/eval.py` | per-leg/leg×split comparison rendering | ✓ VERIFIED | JSON/table wiring; eval tests pass. |
| `src/sif/mcp/protocol.py` | offset/per_chunk input fields; no per_chunk on Lex | ✓ VERIFIED | `QueryInput.offset/per_chunk`, `LexSearchInput.offset`, `VecSearchInput.offset/per_chunk`. |
| `src/sif/mcp/handlers.py` | query schema offset/per_chunk + pass-through | ✓ VERIFIED | Schema/model sync; handlers forward. |
| `src/sif/mcp/backend.py` | offset/per_chunk forwarding, one fallback enrichment, chunk metadata re-map, startup schema init | ✓ VERIFIED | All present; pipeline path not double-enriched. |
| `docs/cli-reference.md` | generated `--offset`/`--per-chunk` docs | ✓ VERIFIED | 3 + 2 generated rows, no hand-edit evidence. |
| `docs/benchmarking.md` | CORR-02 and CORR-04 before/after narratives + D-12 verdict | ✓ VERIFIED | Sections present with reproduced numbers/labels. |
| `bench/b0.json` | pre-ranking-change saved run | ✓ VERIFIED | 100 queries, fingerprint `8c006123784348d1`, bm25. |
| `bench/b1.json` | post-dedup, pre-title saved run | ✓ VERIFIED | 100 queries, same fingerprint, bm25. |
| `bench/d12-verdict.json` | candidate sweep + accept/reject decision | ✓ VERIFIED | rejected/pinned 1.0; 3 candidates with full GateResults. |
| `tests/unit/database/test_schema_title_fts.py` | populated-DB migration suite | ✓ VERIFIED | 14 tests incl. durability/reopen tests; all pass. |
| `tests/fixtures/bench/heldout_defaults.json` | regenerated snapshot + rationale | ✓ VERIFIED | Rationale records dedup/title-column/D-12; reproduction tests pass. |

### Key Link Verification

Note: `verify.key-links` reported "Target not referenced in source" for links whose `to` value is a file path or a DDL object rather than a literal string. Manual import/DML verification (below) confirms every link; the verb's negative results are false negatives from path-literal matching, not broken wiring.

| From | To | Via | Status | Details |
| ---- | -- | --- | ------ | ------- |
| `src/sif/indexing/parser.py` | `src/sif/core/models.py` | one `compute_checksum` helper | WIRED | `from sif.core.models import compute_checksum`; all 3 parsers call it. |
| `src/sif/indexing/incremental.py` | `src/sif/indexing/parser.py` | per-file `create_parser(file_path) or TextParser()` | WIRED | Import + call site at line 393. |
| `src/sif/database/repositories.py` | `src/sif/core/models.py` | canonical metadata serializer on create/update | WIRED | Import + both SQL parameter sites. |
| `src/sif/indexing/incremental.py` | `src/sif/database/repositories.py` | `IndexMetaRepository` marker reads/writes; `_doc_repo.update` fast path | WIRED | Import + calls at marker/fast-path sites. |
| `src/sif/indexing/watcher.py` | `src/sif/indexing/incremental.py` | `result.reindexed_paths` into embed leg | WIRED | Burst/reconcile use the result field. |
| `src/sif/search/hybrid.py` | `src/sif/search/context_attach.py` | every pipeline exit calls `enrich_results` once | WIRED | 4 pipeline exits; spy test passes. |
| `src/sif/search/context_attach.py` | `src/sif/search/staleness.py` | `enrich_results` composes staleness after attach | WIRED | Import + composition order. |
| `src/sif/cli/commands/search.py` | `src/sif/search/context_attach.py` | one call per direct CLI exit | WIRED | Lines 545, 767. |
| `src/sif/mcp/backend.py` | `src/sif/search/context_attach.py` | fallback enriches once before re-map | WIRED | Line 214; pipeline path not re-enriched. |
| `src/sif/cli/commands/search.py` | `src/sif/search/bm25.py` / `hybrid.py` | `SearchOptions(offset=...)`, single slice owner | WIRED | Options thread offset; searchers own their slice. |
| `src/sif/mcp/backend.py` | `src/sif/search/hybrid.py` | MCP offset reaches `SearchOptions` and the pipeline slice | WIRED | `options = SearchOptions(offset=offset, ...)`; pipeline call. |
| `src/sif/search/vector.py` | `src/sif/search/rrf.py` | deduped rows feed fusion; chunk fields survive | WIRED | Fuse sites + metadata merge. |
| `src/sif/search/hybrid.py` | `src/sif/search/rrf.py` | both fuses pass `key=fuse_key_for(options.per_chunk)` | WIRED | Exactly two fuse sites, both keyed. |
| `src/sif/search/bm25.py` | `documents_fts` | bound `bm25(documents_fts, ?, ?)`; title column second | WIRED | Both SQL branches bind `[content_weight, title_weight, query]`. |
| `src/sif/search/bm25.py` | `src/sif/core/models.py` | `SearchOptions.title_weight` internal override | WIRED | Field read at line 84; no public knob. |
| `src/sif/database/schema.py` | `documents_fts_v` / documents triggers | drop vocab → rebuild → recreate vocab/triggers | WIRED | DDL sequence at lines 315-453; structural test. |
| `src/sif/mcp/backend.py` | `src/sif/database/database.py` | startup `init_schema(embedding_dim=...)` | WIRED | Lines 103-112; tests pass. |
| `src/sif/mcp/handlers.py` | `src/sif/mcp/backend.py` | `per_chunk`/offset validated then forwarded | WIRED | Handler passes both; schema matches model. |
| `src/sif/mcp/backend.py` | `src/sif/core/models.py` | re-map copies chunk fields/vectors_stale | WIRED | Explicit metadata dict; tests assert exact set. |
| `src/sif/cli/commands/eval.py` | `src/sif/search/personal_bench.py` | comparison rendering reads `legs`/`leg_splits` | WIRED | Imports + rendering; fresh compare output contains both. |
| `bench/d12-verdict.json` | `src/sif/search/bm25.py` | recorded decision selects pinned `_TITLE_WEIGHT` | WIRED | Artifact `pinned_title_weight=1.0`; constant 1.0 + comment + test pin. |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
| -------- | ------------- | ------ | ------------------ | ------ |
| `src/sif/cli/commands/search.py` | `results` | `BM25Searcher.search` / `VectorSearcher.search` / `SearchPipeline.search` | Yes — real SQL/KNN rows, enriched at entry | ✓ FLOWING |
| `src/sif/mcp/backend.py` | `core_results` → re-mapped `SearchResult.metadata` | pipeline search or BM25 fallback | Yes — explicit field copy, no static return | ✓ FLOWING |
| `src/sif/search/vector.py` | `candidates` / `page` | vec0 KNN JOIN to `document_chunks` | Yes — real distance-ordered rows | ✓ FLOWING |
| `src/sif/search/hybrid.py` | `fused_results` / `results` | BM25 + vector legs through RRF | Yes — real leg outputs, one slice | ✓ FLOWING |
| `src/sif/search/bm25.py` | `cursor` rows | `documents_fts` MATCH with weighted `bm25()` | Yes — real FTS scan | ✓ FLOWING |
| `tests/fixtures/bench/heldout_defaults.json` | static metrics | deterministic `build_bench_db`/`ConceptEmbedder` reproduction | N/A — recorded measurement artifact | N/A |
| `bench/b0.json`, `bench/b1.json`, `bench/d12-verdict.json` | static evidence | saved personal-eval runs / sweep output | N/A — recorded evidence; independently reproduced | N/A |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
| -------- | ------- | ------ | ------ |
| Phase-targeted unit/integration suites | `pytest tests/unit/indexing tests/unit/database/test_schema.py tests/unit/database/test_schema_title_fts.py tests/unit/search/{test_vector,test_hybrid,test_bm25,test_rrf,test_staleness,test_context_attach,test_personal_bench}.py tests/unit/cli/{test_search,test_search_pagination,test_eval,test_index}.py tests/unit/mcp/test_backend.py tests/integration/{test_search_correctness,test_incremental_equivalence}.py -q --no-cov` | 880 passed in 14.78s | ✓ PASS |
| Full regression gate (CLAUDE.md) | `env -u FORCE_COLOR NO_COLOR=1 pytest` | 2054 passed, 1 skipped, coverage 95.27% (fail_under=90) in 117.67s | ✓ PASS |
| Lint / format / types | `ruff check src tests`; `ruff format --check src tests`; `ty check src/sif` | All checks passed; 198 files formatted; All checks passed | ✓ PASS |
| B0 reproduces at offset=0 / min_score=0 | `SIF_DB_PATH=.planning/tmp/phase19/bench.db ... eval --personal --bm25-only -c bench-fixture --compare bench/b0.json --json --no-save` | n=100, mean delta 0.0, helped 0 / hurt 0 / unchanged 100; splits 51/49 unchanged; suppressed groups named | ✓ PASS |
| B1 self-comparison + post-dedup baseline | same command with `--compare bench/b1.json` | n=100, mean 0.0, unchanged 100; `legs` title n=50 / body n=50, delta 0.0; `leg_splits` title heldout n=23 (baseline 1.0), body heldout n=26 (baseline 0.900634933653854) | ✓ PASS |
| D-12 verdict artifact shape | `python -c` parse of `bench/d12-verdict.json` | `decision=rejected`, `pinned_title_weight=1.0`, candidates 2.0/3.0/4.0 each with title/body held-out n/mean/CI/helped/hurt/unchanged/noise_floor/winner/regression/sufficient | ✓ PASS |
| Title-weight constant is pinned at the measured value | `test_pinned_title_weight_is_the_measured_d12_value` + source read | `_CONTENT_WEIGHT = 1.0`, `_TITLE_WEIGHT = 1.0`; test passes | ✓ PASS |
| Generated docs carry the public flags | `grep -- '--offset|--per-chunk' docs/cli-reference.md` | 3 `--offset` rows (search/vsearch/query), 2 `--per-chunk` rows (vsearch/query) | ✓ PASS |

### Probe Execution

No probes: no `scripts/*/tests/probe-*.sh` exist, and no PLAN/SUMMARY declares a probe. Step 7c: SKIPPED (no probes).

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
| ----------- | ----------- | ----------- | ------ | -------- |
| CORR-01 | 19-01, 19-02 | Frontmatter-only edits become searchable (parser dispatch + metadata-aware checksum, ONE shared forced-reindex migration, md body byte-identical, YAML `---` fixed) | ✓ SATISFIED | Canonical checksum + dispatch + metadata fast path + single `CONVENTION_VERSION=2` migration; tests pass. |
| CORR-02 | 19-06, 19-07 | One result per document by default (pre-fusion dedup, `--per-chunk`, bench before/after, goldens rationale) | ✓ SATISFIED | Vector dedup + chunk identity + per-chunk fusion + surfaces + B0/B1 + snapshot/SC1 evidence. |
| CORR-03 | 19-05 | Deterministic pagination (CLI/MCP offset, single slice, BM25 min_score order, offset=0 contract) | ✓ SATISFIED | Offset surfaces + one slice owner + pre-pagination threshold + global ranks; B0 reproduced. |
| CORR-04 | 19-08, 19-09 | Title-aware ranking (title-FTS migration, rewritten triggers, measured bm25 weights, mtime index, vocab survival) | ✓ SATISFIED | Two-column FTS + triggers + weighted bound bm25 + mtime index + populated-DB vocab/DYM tests + D-12 rejection recorded. |
| CORR-05 | 19-03, 19-04 | No redundant attach (ONE context/staleness attach at pipeline exit) | ✓ SATISFIED | Raw searchers + `enrich_results` owners at pipeline/CLI/MCP fallback; spies prove exactly one. |

No orphaned requirements: `.planning/REQUIREMENTS.md` maps exactly CORR-01..CORR-05 to Phase 19, and all five appear in this phase's plan frontmatter. CORR-06 is mapped to Phase 21 and is correctly absent from Phase 19 plans.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
| ---- | ---- | ------- | -------- | ------ |
| — | — | No `TBD`/`FIXME`/`XXX`/`TODO`/`HACK`/`PLACEHOLDER` markers in `src/sif` | — | Debt-marker gate clean. |
| — | — | No stub returns (`return null`, empty fetch with no data source, hardcoded empty props) in changed code | — | Empty-list returns are the exclude-all sentinel (`bm25.py:71`, `vector.py:59`) and accumulators, not stubs. |
| — | — | No new runtime dependencies | — | `pyproject.toml`/`uv.lock` unchanged across the phase (`git diff` 0 files). |

Deferred Info findings from `19-REVIEW-DISPOSITION.md` (not phase-goal blockers, recorded for completeness):

| Finding | Severity | Impact on Phase 19 |
| ------- | -------- | ------------------ |
| IN-01 vector scores L2-derived but documented as cosine | Info / deferred | Pre-existing metric-label issue; distance ordering (and thus dedup/pagination) is unaffected. |
| IN-02 rerank rebuild drops `vectors_stale` | Info / deferred | Latent; the pipeline enriches after rerank, so `mark_vector_staleness` recomputes the flag on every pipeline exit — CORR-05 marker preservation holds. |
| IN-03 docs mention MCP `vec_search` per-chunk while the tool is unregistered | Info / deferred | Registration is Phase 22 (MCP-06 lex/vec wiring); the input model and backend forwarding are in place here. |
| IN-05 `BM25Searcher.search_chunks` min_score after LIMIT/OFFSET, no global ranks | Info / deferred | No production caller (`grep src/` finds only tests); plans 19-05/19-08 scope it out; user pagination surfaces use `search()`, which is correct. |
| IN-06 MCP backend silently creates an empty index at a nonexistent `SIF_DB_PATH` | Info / deferred | Diagnosability warning, not data loss; outside CORR-01..05. |

### Human Verification Required

None. Every truth is verified by code inspection plus a passing automated test or a reproduced measurement artifact; this phase adds no visual, real-time, or external-service surface. The two prose deliverables (`docs/benchmarking.md` CORR-02/CORR-04 sections) were inspected and their numbers cross-checked against `bench/b0.json`, `bench/b1.json`, `bench/d12-verdict.json`, and a fresh `--compare` run.

### Gaps Summary

No gaps found. All five roadmap success criteria and all 63 functional plan must-haves are achieved in the codebase:

- CORR-01: metadata-aware checksums, per-file parser dispatch, the YAML `---` whole-file fix, the D-07 metadata fast path, and one shared per-collection convention migration are all implemented and exercised by tests; the Markdown body path is unchanged.
- CORR-02: per-document dedup lives inside `VectorSearcher` before RRF, chunk identity and `chunk_matches` are in the result contract, per-chunk mode survives both fuse sites, and the contract change is recorded with B0/B1, the held-out snapshot rationale, the SC1/RRF goldens, and the chunky-document regression.
- CORR-03: CLI and MCP offsets are validated, each query path has exactly one offset slice owner, BM25 `min_score` is applied before `LIMIT/OFFSET`, ranks are global, and offset=0 reproduces B0 exactly (independently rerun: n=100, mean 0.0).
- CORR-04: the title-FTS detect-and-rebuild migration is durable across reopen, populates exactly once, preserves the vocab shadow/DYM, rewrites the triggers with `title`, and binds measured column weights; the `mtime` index exists; MCP-only hosts migrate at startup. The D-12 2–4× band was measured and rejected with numbers (title held-out already at the 1.0 ceiling; body held-out flat), which CONTEXT D-12 explicitly sanctions; `_TITLE_WEIGHT` is pinned at 1.0 and Phase 24 QUAL-03 is the re-measurement point.
- CORR-05: the searchers are raw producers and exactly one `enrich_results` composition runs per public exit; no `_attach_contexts` remains.

The final code-review fixes (CR-01, CR-02, WR-01, WR-02, IN-04) are present in the working tree and covered by passing regression tests (migration durability across reopen, non-string-title isolation, migration convergence with permanently failing files, non-positive `--limit` rejection).

---

_Verified: 2026-11-15T05:26:37Z_
_Verifier: Claude (gsd-verifier)_
