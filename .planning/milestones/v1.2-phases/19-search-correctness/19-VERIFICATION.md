---
phase: 19-search-correctness
verified: 2026-11-25T10:38:29Z
status: human_needed
score: 61/63 must-haves verified
covered_files: [".planning/milestones/v1.2-phases/19-search-correctness/19-01-PLAN.md",".planning/milestones/v1.2-phases/19-search-correctness/19-01-SUMMARY.md",".planning/milestones/v1.2-phases/19-search-correctness/19-02-PLAN.md",".planning/milestones/v1.2-phases/19-search-correctness/19-02-SUMMARY.md",".planning/milestones/v1.2-phases/19-search-correctness/19-03-PLAN.md",".planning/milestones/v1.2-phases/19-search-correctness/19-03-SUMMARY.md",".planning/milestones/v1.2-phases/19-search-correctness/19-04-PLAN.md",".planning/milestones/v1.2-phases/19-search-correctness/19-04-SUMMARY.md",".planning/milestones/v1.2-phases/19-search-correctness/19-05-PLAN.md",".planning/milestones/v1.2-phases/19-search-correctness/19-05-SUMMARY.md",".planning/milestones/v1.2-phases/19-search-correctness/19-06-PLAN.md",".planning/milestones/v1.2-phases/19-search-correctness/19-06-SUMMARY.md",".planning/milestones/v1.2-phases/19-search-correctness/19-07-PLAN.md",".planning/milestones/v1.2-phases/19-search-correctness/19-07-SUMMARY.md",".planning/milestones/v1.2-phases/19-search-correctness/19-08-PLAN.md",".planning/milestones/v1.2-phases/19-search-correctness/19-08-SUMMARY.md",".planning/milestones/v1.2-phases/19-search-correctness/19-09-PLAN.md",".planning/milestones/v1.2-phases/19-search-correctness/19-09-SUMMARY.md",".planning/milestones/v1.2-phases/19-search-correctness/bench/b0.json",".planning/milestones/v1.2-phases/19-search-correctness/bench/b1.json",".planning/milestones/v1.2-phases/19-search-correctness/bench/d12-verdict.json","docs/benchmarking.md","docs/cli-reference.md","src/sif/cli/commands/eval.py","src/sif/cli/commands/index.py","src/sif/cli/commands/search.py","src/sif/core/models.py","src/sif/database/database.py","src/sif/database/repositories.py","src/sif/database/schema.py","src/sif/indexing/incremental.py","src/sif/indexing/parser.py","src/sif/indexing/watcher.py","src/sif/mcp/backend.py","src/sif/mcp/protocol.py","src/sif/mcp/tools.py","src/sif/search/bm25.py","src/sif/search/context_attach.py","src/sif/search/hybrid.py","src/sif/search/personal_bench.py","src/sif/search/rerank.py","src/sif/search/rrf.py","src/sif/search/staleness.py","src/sif/search/vector.py","tests/fixtures/bench/heldout_defaults.json","tests/integration/test_embed_idempotency.py","tests/integration/test_incremental_equivalence.py","tests/integration/test_search_correctness.py","tests/support/__init__.py","tests/unit/cli/test_eval.py","tests/unit/cli/test_index.py","tests/unit/cli/test_search.py","tests/unit/cli/test_search_pagination.py","tests/unit/database/test_repositories.py","tests/unit/database/test_schema.py","tests/unit/database/test_schema_title_fts.py","tests/unit/indexing/test_incremental.py","tests/unit/indexing/test_parser.py","tests/unit/indexing/test_parser_checksum.py","tests/unit/indexing/test_watcher.py","tests/unit/mcp/test_backend.py","tests/unit/search/test_bench_snapshot.py","tests/unit/search/test_bm25.py","tests/unit/search/test_collection_filter.py","tests/unit/search/test_context_attach.py","tests/unit/search/test_hybrid.py","tests/unit/search/test_personal_bench.py","tests/unit/search/test_rerank.py","tests/unit/search/test_rrf.py","tests/unit/search/test_staleness.py","tests/unit/search/test_vector.py"]
covered_digest: "v4:sha256:19925987711dbafd76a925814d1e67b765d1163a42bb0c9e037bc7a2283c71b8"
behavior_unverified: 0
overrides_applied: 0
prohibitions_flagged: 1
prohibition_verdicts: "29/30 hold; 1 flagged — 19-03 P1 is superseded in letter by Phase 21 (CORR-06 embedded_documents shadow) and needs human review; judgment tier, LLM judge, non-authoritative; no human resolution on record (no 19-UAT.md)"
re_verification:
  previous_status: passed
  previous_score: 63/63
  gaps_closed: []
  gaps_remaining: []
  regressions: []
advisory: []
human_verification:
  - test: "In an 80-column terminal run 'sif search query --per-chunk QUERY' and 'sif search vsearch --per-chunk QUERY' on a corpus whose paths are 30+ characters"
    expected: "Every chunk row shows which chunk it is (path#sequence)"
    why_human: "The Chunk cell is built as path#sequence, but Rich ellipsizes the tail when the column is narrow; rendered here at 80/100/120 columns the #sequence is cut for realistic paths on both tables (rich 14.3.3). Whether identity is visible is a visual judgement on a real terminal."
  - test: "Run 'sif search search \"Saltiv Protocol Notes\" -n 10' and then with --min-score 0.12 and --min-score 0.23 on the bench-fixture index"
    expected: "Per the help text 'Minimum score threshold', weaker matches are removed and the best match survives"
    why_human: "Observed at HEAD: rank 1 (best BM25 match, displayed Score 0.1057) is removed first and --min-score 0.23 returns nothing. No Phase 19 must-have asserts the direction, so this is a product decision, not a check a script can settle."
  - test: "Run 'sif search query --per-chunk QUERY --csv', '--md', '--xml' and '--files' on a document with several matching chunks"
    expected: "Decide whether chunk-level rows in machine formats must carry chunk identity and whether --files may repeat a path"
    why_human: "At HEAD those formats emit chunk-level rows without chunk_id/sequence and --files prints the path once per row (reproduced). The plan scoped only the Rich table and JSON, so accepting or extending that scope is a human decision."
  - test: "Review prohibition 19-03 P1 ('MUST NOT persist vector staleness as a per-document flag or issue a per-result embedding query') against src/sif/search/staleness.py:44-45,67-98"
    expected: "A recorded decision that the Phase 21 shadow design (one PK lookup per result on embedded_documents) is the accepted successor of the Phase 19 batched scan"
    why_human: "Judgment-tier prohibition with no human resolution on record; its letter no longer describes HEAD while its intent (derived marker, bounded read, no full scan) holds."
  - test: "Decide whether truths 17 and 34 are accepted for their guarantees (scope notes S2 and S4 below) or must hold literally"
    expected: "Either record overrides for the Phase 20/21 mechanisms or ask for the Phase 19 literal behaviour back"
    why_human: "Two clauses are literally false on HEAD paths a later roadmap phase changed (Phase 20 fetch window, Phase 21 shadow read). The verifier cannot accept a deviation on the developer's behalf."
---

# Phase 19: Search Correctness Verification Report

**Phase Goal:** Search results are fresh, deduplicated, deterministically paginable, and title-aware — the trust floor that metadata filtering (20) builds on, with every ranking-contract change measured before/after on the Phase 18 instrument.
**Verified:** 2026-11-25T10:38:29Z
**Status:** human_needed
**Re-verification:** Yes — regenerated from the current tree at HEAD `4dbf386` (not carried forward). Previous report verified 2026-11-18T11:55:04Z (last committed `b817ebb`).

Every must-have was re-derived from the nine plans and from `### Phase 19` of the archived `.planning/milestones/v1.2-ROADMAP.md`, then judged against HEAD by reading the cited code, re-resolving every line citation, running the requirement-linked test battery, and driving the shipped CLI and search functions directly. SUMMARY.md text was used only as a pointer to code, never as evidence. Planning artifacts are cited at their archived location (`.planning/milestones/v1.2-phases/19-search-correctness/`).

## Delta Since the Previous Report (`b817ebb..4dbf386`)

`verification.status` reported `stale` with four moved files. Recomputed with git: 88 commits since `b817ebb`, 59 non-planning files changed, exactly 4 of the 58 previously covered implementation files among them. The 18 PLAN/SUMMARY files and 3 bench artifacts are byte-identical; only their recorded path was wrong (pre-archive prefix), now resolved.

| File | Change in the window | Truth that cites it | Effect | How established |
|------|----------------------|---------------------|--------|-----------------|
| `tests/unit/cli/test_search.py` | `c95d2cee`: two title-cell width assertions in `TestSearchOutputBranches` relaxed from exact lengths (`"A" * 15`, `"B" * 34`) to 10-character prefixes | None. They are title-truncation assertions on `search --line-numbers` / `vsearch --line-numbers` output, not cited by any Phase 19 truth (the per-chunk surface tests are in `TestPerChunkSurfaces`, `:4151`, untouched) | None | Diff read; file 100% green |
| `tests/unit/database/test_repositories.py` | `c95d2cee`: `symlink_or_skip` in the `alias_pair` fixture; one `skipif(not hasattr(time, "tzset"))` on `TestLLMCacheExpiryWR09::test_set_stores_aware_utc_expiry` (three more in that class predate `b817ebb`) | 4 (via `TestDocumentMetadataCanonicalStorage`, which uses neither) | None on Ubuntu/macOS: 0 skips when run here | Diff read; per-test run shows PASSED, not SKIPPED |
| `tests/unit/mcp/test_backend.py` | `c95d2cee`: `symlink_or_skip` in 2 `get_document`/`get_documents_by_pattern` alias tests | 21, 22, 42, 43, 56 (via `TestSingleEnrichmentOwner`, `TestChunkFieldRemap`, `TestSchemaInitializationAtStartup`, untouched) | None | Diff read; both alias tests PASSED |
| `tests/unit/search/test_context_attach.py` | `c95d2cee`: `symlink_or_skip` in the `alias_pair` fixture (10 context/staleness tests depend on it); `skipif(sys.platform == "win32")` on one tilde test | 17, 18 and 19-03 P2/P3 | None on Ubuntu/macOS: all 10 ran and PASSED | Diff read; per-test run |
| `src/sif/search/rerank.py` (covered, NOT flagged by the tool) | `5f9c0869`: one hunk in `create_reranker` — cache dir now `get_cache_dir() / "models"` (`:436-438`) | 38 (rerank rebuild keeps chunk identity) | None. `_sort_and_build_results` is unchanged (`:68-70`) | Full diff read; `TestRebuildChunkIdentity` 3/3 |
| `tests/unit/search/test_rerank.py` (added to the covered set) | `f8ff9bea`: `TestRebuildChunkIdentity`, 3 tests pinning `chunk_id`/`sequence`/`chunk_matches` through the rerank rebuild | 38 | Strengthens it; test-only, `src/` untouched | 18/18 in file |

**Changed outside the covered set but checked:** `src/sif/embedding/normalize.py` (new, `26ac78cd`) renormalizes embeddings on the write/read path; it moves distances, not the dedup/pagination logic, and the vector contracts are exercised with the deterministic `ConceptEmbedder`. `src/sif/cli/commands/collection.py` and `ls.py` (`c95d2cee`, Windows path normalization) are not Phase 19 surfaces. `pyproject.toml`/`uv.lock` changed only for the torch floor.

**Citation re-resolution.** Every line citation below was resolved against the file at HEAD. None of the Phase 19 source citations had moved (`search.py` `--min-score` help at `:530,731,962`, `--offset` at `:517,718,949`, `--per-chunk` at `:734,1003`; `bm25.py:94-97,171,181`; `schema.py:451-666,769`; `incremental.py:155-212,393,437-458,482`).

## Goal Achievement

### Roadmap Success Criteria

| # | Success Criterion | Status | Evidence |
| --- | ----------------- | ------ | -------- |
| 1 | Frontmatter-only edits become searchable after the next index update; parser dispatch + metadata-aware checksum in ONE plan with ONE shared forced-reindex migration; Markdown body path byte-identical; YAML `---` empty-body bug fixed | ✓ VERIFIED | `compute_checksum()` hashes body + NUL + canonical full frontmatter (`src/sif/core/models.py:64-72`); all three parsers call it (`src/sif/indexing/parser.py:81,117,184`). `IncrementalIndexer._process_file` dispatches `create_parser(file_path) or TextParser()` (`src/sif/indexing/incremental.py:393`) and stores `parsed.checksum` (`:482`). `CONVENTION_VERSION = 2` (`parser.py:19`) + per-collection `convention:<id>` marker drives one forced re-parse (`incremental.py:150-212`); the scratch index built by the shipped CLI at HEAD carries `convention:<collection id> = 2`. Markdown still uses `frontmatter.loads` and preserves body bytes; `CodeParser` reads `.yaml/.yml` whole. Independent probe: three `---` forms kept whole, reorder same, frontmatter edit changes, body edit changes, date round-trip. |
| 2 | One result per document by default; dedup inside VectorSearcher pre-fusion; `--per-chunk` escape hatch; ranking-contract change recorded with bench before/after and goldens with rationale | ✓ VERIFIED | `VectorSearcher._candidates` groups by `document_id` after `min_score`, best-distance row wins, `chunk_matches` counts pre-dedup rows (`src/sif/search/vector.py:296-323`). `--per-chunk` on vsearch/query only (`src/sif/cli/commands/search.py:734,1003`) and MCP `per_chunk` on `query`/`vec_search` (`src/sif/mcp/tools.py:139,356-357`; wire goldens). Both RRF fuse sites pass `key=fuse_key_for(options.per_chunk)` (`src/sif/search/hybrid.py:150-155,451-455`). B0/B1 saved runs (100 queries, corpus fingerprint `8c006123784348d1`) + `docs/benchmarking.md` §CORR-02 + regenerated SC1/RRF goldens and held-out rationale. Chunk identity in CSV/Markdown/XML/`--files` is outside this criterion as planned — see Adjudication B. |
| 3 | Deterministic pagination — CLI `--offset` and MCP offset return the correct next page; hybrid owns ONE offset slice; searchers return from rank 0; BM25 min_score order fixed; offset=0 reproduces the recorded contract | ✓ VERIFIED | Three `--offset` flags with `click.IntRange(min=0)` (`search.py:515-520,716-721,947-952`); `QueryInput.offset = Field(default=0, ge=0)` (`src/sif/mcp/protocol.py:88,128,155`). `HybridSearcher` calls legs at offset 0 and slices once (`hybrid.py:119-176`); pipeline passes offset=0 and owns the slice (`hybrid.py:417-428,482-484`); BM25 binds `1 - 1/min_score` as a parameter and applies `m.score >= ?` in the outer WHERE of the materialized match CTE, before `LIMIT ? OFFSET ?` (`bm25.py:94-97,138,160`); global `rank = offset + position`. "min_score order fixed" is specified as filter-before-pagination (`19-CONTEXT.md:13,46,131`) and holds; the threshold direction is a separate finding — see Adjudication A. B0 rerun: n=100, mean delta 0.0, 100 unchanged. |
| 4 | Title-aware ranking — title-FTS detect-and-rebuild migration + rewritten triggers + bench-measured bm25() column weights + mtime index; `documents_fts_v` vocab shadow survives rebuild on a populated DB | ✓ VERIFIED | `_fts_column_names()` gate + two-column DDL + drop-vocab → drop-triggers/table → single `('rebuild')` → recreate-vocab/triggers under `SAVEPOINT sp_fts_tables` (`src/sif/database/schema.py:451-666`). Triggers carry `(rowid, content, title)` incl. `old.title`. `bm25(documents_fts, ?, ?)` bound weights in both branches (`bm25.py:84-97,125,147`); on the scratch index `bm25(documents_fts,1.0,1.0)` equals `rank` row-for-row for three MATCH queries. `idx_documents_mtime` (`schema.py:769`). Independent populated-DB migration probe and the 14-test suite pass. D-12 sweep measured 2.0/3.0/4.0 against B1 and recorded a rejection (`bench/d12-verdict.json`), reproduced at HEAD; `_TITLE_WEIGHT = 1.0`. |
| 5 | Results without redundant attach work — double-attach eliminated; exactly ONE context/staleness attach at pipeline exit | ✓ VERIFIED | `enrich_results` composes `attach_path_contexts` then `mark_vector_staleness` (`src/sif/search/context_attach.py:317-346`); no `_attach_contexts` anywhere under `src/sif` (grep count 0); pipeline enriches exactly once per exit (`hybrid.py:356`, and `:367/:379/:484` through `_enrich`, `:301-309`); direct CLI search/vsearch enrich once (`search.py:613,872-874`); MCP fallback enriches once and the pipeline path is not re-enriched (`src/sif/mcp/backend.py:490,501,534`). Spy tests pass. The staleness read mechanism was replaced by Phase 21 — scope note S2. |

**Score:** 5/5 roadmap success criteria verified.

### Observable Truths (Plan Must-Haves)

The `UNCLASSIFIED-FLAGGED` lines in PLAN frontmatter are probe-classification flags, not functional must-haves; they are excluded from the score (9 such lines across the nine plans). All 63 functional plan truths were re-derived and judged against the tree at `4dbf386`.

#### Plan 19-01 — CORR-01 (parser dispatch, checksum, canonical metadata)

| # | Truth | Status | Evidence |
| --- | ----- | ------ | -------- |
| 1 | `.yaml`/`.yml` starting with `---` is parsed by `CodeParser` as the whole file in all three forms | ✓ VERIFIED | `create_parser` maps `.yaml/.yml` through `CodeParser.LANGUAGE_MAP` (`parser.py:154-155,209`); `CodeParser.parse` reads the whole file (`parser.py:163-193`). `test_yaml_leading_separator_is_parsed_as_whole_file` (`tests/unit/indexing/test_parser.py:222`) passes. Probe: closing, two-block and no-closing forms all kept whole. |
| 2 | Every parser computes sha256(body + NUL + canonical full frontmatter) with sort_keys/default=str/ensure_ascii=False/compact + recursive key coercion; frontmatter edit changes checksum, key reorder does not, body edit does | ✓ VERIFIED | `canonical_metadata_json()` + `compute_checksum()` (`models.py:19-72`); all parsers call it (`parser.py:81,117,184`). 8-test checksum matrix passes. Independent check: `compute_checksum("body", {}) == sha256(b"body\x00{}")`; `{"outer": {1: "a", "b": 2}}` → `{"outer":{"1":"a","b":2}}`; reorder same; frontmatter edit changes; body edit changes. |
| 3 | Markdown body extraction stays byte-identical; `frontmatter.loads` still strips frontmatter | ✓ VERIFIED | `MarkdownParser.parse` body path unchanged, checksum appended after it (`parser.py:57-90`); parser suite passes; probe body is the frontmatter-stripped text. |
| 4 | `.md` with `date: 2024-01-01` stores without TypeError and metadata JSON round-trips to the hashed canonical string | ✓ VERIFIED | `canonical_metadata_json(default=str)`; repository create/update persist it (`src/sif/database/repositories.py:192,274`); `TestDocumentMetadataCanonicalStorage` passes; independent round-trip check True. |
| 5 | `IncrementalIndexer` stores `parsed.checksum`, not a body-only fallback | ✓ VERIFIED | `incremental.py:482` passes `checksum=parsed.checksum`; incremental suite passes. |
| 6 | An extension outside `create_parser`'s map falls back to `TextParser` | ✓ VERIFIED | `incremental.py:393`; `test_per_file_parser_dispatch_with_text_fallback` (`tests/unit/indexing/test_incremental.py:417`) passes; probe: `create_parser("weird.xyz")` is `None`, `.txt` → `TextParser`. |

#### Plan 19-02 — CORR-01 (fast path, convention migration, watch signal)

| # | Truth | Status | Evidence |
| --- | ----- | ------ | -------- |
| 7 | `index_meta` exists on fresh/migrated DBs with per-collection `convention:<id>` keys; `drop_all` removes it | ✓ VERIFIED | `schema.py:302-311`; `drop_all` lists `index_meta` (`schema.py:811`); `IndexMetaRepository` (`repositories.py:731`); scratch index shows the table and the marker; schema tests pass. |
| 8 | First `update_collection` with absent/old marker forces exactly one re-parse pass; one `migrate <N>` event with documents; empty collection silent; marker written only after a clean pass | ✓ VERIFIED (scope note S1) | `incremental.py:155-212`; `TestConventionMigration` (`test_incremental.py:1105`) + CLI migrate-render test pass. Read literally, "only when zero files failed" is false when a never-stored scanned file fails: the gate is `failed_stored == 0` (`:199-212`, in-phase review fix WR-01). No stored document can be stranded on the old convention. |
| 9 | Metadata-only edit updates title/metadata/checksum/mtime/file_size, keeps chunks and embeddings | ✓ VERIFIED | Fast path `incremental.py:437-446`; `TestMetadataFastPath` (`test_incremental.py:847`) + `test_frontmatter_only_cycle_preserves_chunks_and_moves_title` (`tests/integration/test_incremental_equivalence.py:261`) pass. |
| 10 | Body edit deletes that document's chunks and embeddings before update | ✓ VERIFIED | `incremental.py:451-458`; body-edit fast-path tests pass. |
| 11 | `--force` skips checksum skip but unchanged body takes the metadata fast path | ✓ VERIFIED | `incremental.py:413,437`; force test passes. |
| 12 | `update_paths` never starts a migration but uses body-vs-metadata discrimination | ✓ VERIFIED | `update_paths` passes `migrating=False` (`incremental.py:318`) and never touches `_meta_repo` (its only uses are `:156,212`, both in `update_collection`); the drift refresh routes through `update_paths` (`src/sif/indexing/drift.py:146`); test patches `IndexMetaRepository.get` to raise and passes. |
| 13 | `reindexed_paths` contains only added/body-changed paths; watcher embed leg selects from it; metadata-only edit produces no new chunk/vector rows | ✓ VERIFIED | `incremental.py:68,179-190,320-329`; watcher `_run_burst/_run_reconcile` (`src/sif/indexing/watcher.py:906,924`); `TestEmbedDepth` passes. |
| 14 | Parse failure leaves marker unwritten and counted, so the next pass retries | ✓ VERIFIED | `failed_stored` accounting + marker gate (`incremental.py:196-200,210`); failure-retry tests pass. |

#### Plan 19-03 — CORR-05 (search-core single attach)

| # | Truth | Status | Evidence |
| --- | ----- | ------ | -------- |
| 15 | BM25/Vector/Hybrid searchers no longer attach contexts/staleness; return raw results | ✓ VERIFIED | No `_attach_contexts` under `src/sif` (grep count 0); searcher contract tests pass. |
| 16 | `SearchPipeline.search` calls the shared enrichment exactly once on BM25, VECTOR, HYDE, and hybrid exits | ✓ VERIFIED | `hybrid.py:356` (BM25), `:367`/`:379` (VECTOR/HYDE via `_enrich`, `:301-309`), `:484` (hybrid); `TestSearcherDelegation` (`tests/unit/search/test_staleness.py:459`) spy counts exactly one call per exit. |
| 17 | `enrich_results(db, results)` composes attach then staleness; contexts keep two-sided `normalize_path` with no SQL path prefilter and never clobber on miss; staleness is one batched/derived read with display gate and `None` degradation | ? UNCERTAIN — human decision requested (scope note S2) | `context_attach.py:317-346` composes in order (`:342`); `_CONTEXTS_SQL` filters only `context_type='path'` (`:51-52`), two-sided normalization in Python (`:109-110,311`), set-on-match only (`:311-313`). Staleness keeps the display gate and degrade-unmarked (`src/sif/search/staleness.py:84-98`). Read literally, "one batched `document_embeddings` scan" is false at HEAD: Phase 21 reads the `embedded_documents` shadow with one probe plus one indexed lookup per result (`:44-45,95-97`). |
| 18 | A spy test counts exactly one enrichment per exit; searcher tests assert none inside searchers | ✓ VERIFIED | `TestSearcherDelegation` + `TestBM25SearcherEnrichmentContract`, `TestVectorSearcherEnrichmentContract`, `TestHybridContextAttachment`, `TestSingleEnrichmentOwner` (CLI/MCP) pass. |
| 19 | `staleness.py` D-09 docstring names the single `enrich_results` owner and no searcher `_attach_contexts` reference | ✓ VERIFIED | `staleness.py:11-19` names `enrich_results`; grep for `_attach_contexts` under `src/sif` returns nothing. |

#### Plan 19-04 — CORR-05 (entry points + B0)

| # | Truth | Status | Evidence |
| --- | ----- | ------ | -------- |
| 20 | CLI `sif search` and `sif vsearch` call `enrich_results` exactly once after the direct searcher; output keeps context/staleness | ✓ VERIFIED | `search.py:613,872-874`; `TestSingleEnrichmentOwner` (`tests/unit/cli/test_search.py:3998`) passes. The rendering sites are the same set as before the phase (`5b964e1~1`): staleness marker in table/CSV/Markdown/XML, `context_description` in JSON via `to_dict()` — "keeps" is a no-regression claim and holds. |
| 21 | MCP BM25 fallback enriches exactly once; pipeline path is not enriched again at the boundary | ✓ VERIFIED | `backend.py:534` is the sqlite-vec-unavailable fallback enrichment; the Phase 22 prefix-BM25 (`:490`) and embedder-failure (`:501`) exits each enrich exactly once as well; the pipeline path returns the pipeline's enriched page; `TestSingleEnrichmentOwner` (`tests/unit/mcp/test_backend.py:843`) passes. |
| 22 | MCP re-map still forwards `rank`, `collection_name`, `vectors_stale` | ✓ VERIFIED | `backend.py:189-197` explicit metadata dict; re-map set tests pass. |
| 23 | B0 is a saved personal-eval run on the post-CORR-01 engine over the committed 150-doc fixture corpus with `--bm25-only`, ≥50 queries, `--compare` zero mean delta | ✓ VERIFIED | `bench/b0.json` (archived path): 100 queries, corpus `{documents:150, sampled:50, fingerprint:8c006123784348d1}`, retrieval `bm25`. Rerun at HEAD on a scratch index rebuilt from the fixture corpus: n=100, mean delta 0.0, 100 unchanged. |

#### Plan 19-05 — CORR-03 (deterministic pagination)

| # | Truth | Status | Evidence |
| --- | ----- | ------ | -------- |
| 24 | `sif search`/`vsearch`/`query` accept `--offset` (`IntRange(min=0)`, default 0); past-the-end returns an empty page | ✓ VERIFIED | `search.py:515-520,716-721,947-952`; pagination CLI tests pass; probe: vector offset 5000 → `[]` (scoped and unscoped), BM25 `-n 1 --offset 1` → `[]`. |
| 25 | Ranks are global across pages (`rank = offset + position`) | ✓ VERIFIED | BM25 `bm25.py:181`, vector `vector.py:248-251`, hybrid `_paginate` (`hybrid.py:55-67`); probe: limit 10 offset 30 carries ranks 31-40. |
| 26 | `limit=l offset=o` equals the `[o:o+l]` slice of `limit=o+l offset=0` for BM25/vector/hybrid | ✓ VERIFIED | `TestConsistentPagination` (real schema + vec0, collection-scoped) passes. CLI probe on 15 tied BM25 rows: four pages concatenate to the whole request on both the scoped and the `--all` path. |
| 27 | BM25 applies `min_score` before LIMIT/OFFSET via bound threshold `1 - 1/min_score`, `rank >= threshold`; omitted when min_score=0 | ✓ VERIFIED | `bm25.py:94-97,138,160`; SQL trace at HEAD: `... AND m.score >= ? ORDER BY m.score LIMIT ? OFFSET ?` with `-3.3478` bound ahead of `5, 2`, and no predicate/parameter at `min_score=0`. CLI probe: with `--min-score 0.12`, `-n 10` → `[Qelron]`, `-n 1 --offset 0` → `[Qelron]`, `--offset 1` → `[]` — no qualifying row hides behind a filtered one. See Adjudication A for the direction. |
| 28 | Hybrid calls legs with `offset=0`, `limit+offset`, one slice after fusion, and paginates early single-leg returns | ✓ VERIFIED | `hybrid.py:119-176`; hybrid/pipeline offset tests pass. |
| 29 | Reranker window is `max(candidate_limit, limit+offset)` when offset>0, `candidate_limit` at offset=0; `top_k = limit+offset`; beyond-cap requests get a full page | ✓ VERIFIED | `hybrid.py:417-428,463-477` (`top_k` at `:473`, window at `:465`); `TestRerankerWindowPagination` passes. |
| 30 | Pipeline passes offset=0 to hybrid and owns one slice; BM25/VECTOR/HYDE branches let the searcher own the slice | ✓ VERIFIED | `hybrid.py:417-428` call hybrid with offset=0; `:482-484` one `_paginate`; pipeline offset tests pass. |
| 31 | MCP `query` offset `Field(default=0, ge=0)` forwarded into SearchOptions; Lex/Vec inputs validated; query schema lists offset | ✓ VERIFIED (scope note S3) | `protocol.py:88,128,155`; schema derived from the registered signature (`tools.py:137,317,356`); backend forwards (`backend.py:459,599,663`); five wire goldens list `offset` on query/lex_search/vec_search. The Phase 19 hand-written schema (`handlers.py`) was replaced in Phase 22 — property verified, not the file. |
| 32 | After attach + pagination, offset=0/min_score=0 personal-eval rerun against B0 reports zero mean delta | ✓ VERIFIED | Reproduced at HEAD: n=100, mean 0.0, unchanged 100. |

#### Plan 19-06 — CORR-02 (dedup, chunk identity, per-chunk fusion)

| # | Truth | Status | Evidence |
| --- | ----- | ------ | -------- |
| 33 | VectorSearcher returns one row per document by default: grouped by document_id in best-distance order after min_score; winner carries `chunk_id`/`sequence`; `chunk_matches` counts pre-dedup rows | ✓ VERIFIED | `vector.py:296-323`; `TestVectorDocumentDedup` (`tests/unit/search/test_vector.py:770`) passes. Probe on a real vec0 DB: 5 rows for 5 documents with `chunk_matches` 4/1/1/1/3 and the best chunk's identity. |
| 34 | Default target `limit+offset`; `fetch_k` starts `min(max(target*4,50),2048)` and doubles only on a saturated batch while target unmet; past-cap offset returns empty page | ? UNCERTAIN — human decision requested (scope note S4) | `vector.py:25,187-231`. Measured: unscoped start 50 at target 10 and 160 at target 40 (the literal formula); cap 2048; offset 5000 → `[]` on both paths. On collection-scoped and metadata-filtered searches Phase 20 seeds the window from a selectivity pre-count (`:193-202,257-294`): 40 at limit 10, 50 at offset 30, escalating until the target is met or the scope is exhausted. |
| 35 | A document with ≥5 matching chunks at limit=10 yields 10 distinct documents on vector and hybrid default paths | ✓ VERIFIED | `TestChunkyDocumentDedup` (six-chunk document, collection-scoped) passes. |
| 36 | Per-chunk mode returns ungrouped chunk rows with identity; both RRF fuses group by `chunk_key` selected via `fuse_key_for`; BM25 rows stay document-keyed; default path unchanged | ✓ VERIFIED | `src/sif/search/rrf.py:8-28`; `hybrid.py:150-155,451-455` are the only two `.fuse(` call sites under `src/sif`; per-chunk tests pass. Probe: 15 per-chunk hybrid rows = 10 chunk rows + 5 document-keyed BM25 rows. |
| 37 | RRF scoring math unchanged; merge adopts-null chunk fields from the later list and keeps `max(chunk_matches)` | ✓ VERIFIED | `rrf.py:36-47` metadata merge only; score expression (`:108`) untouched; byte-identical score tests pass. |
| 38 | `SearchResult.to_dict()` carries `chunk_id`/`sequence`/`chunk_matches`; SC1 and RRF goldens regenerated with rationale docstrings | ✓ VERIFIED | `models.py:341-343`; golden docstrings (`tests/unit/search/test_hybrid.py:765-791`, `tests/unit/search/test_rrf.py:478-480`). The rerank rebuild copies all three fields (`src/sif/search/rerank.py:68-70`), now pinned by `TestRebuildChunkIdentity` (3/3, `f8ff9bea`). |
| 39 | Held-out snapshot regenerated for the dedup contract with rationale; verdict keys and defaults lock valid | ✓ VERIFIED | `tests/fixtures/bench/heldout_defaults.json` rationale names the dedup change, the title column, D-12 and labels B0/B1 the BM25 no-drift check; `TestHeldoutSnapshotReproduction` passes. |

#### Plan 19-07 — CORR-02 (public surfaces + B1)

| # | Truth | Status | Evidence |
| --- | ----- | ------ | -------- |
| 40 | `sif query`/`sif vsearch` accept `--per-chunk`; `sif search` does not | ✓ VERIFIED | `search.py:734,1003`; `search_cmd` has no such option — probe: exit 2, "No such option: --per-chunk". |
| 41 | Default CLI output exposes `chunk_matches` in the Rich table and in JSON; per-chunk rows display `path#sequence` and expose `chunk_id`/`sequence` in JSON | ✓ VERIFIED (visibility → Human Verification 1) | `_title_cell` annotation (`search.py:156-174`), `_chunk_cell` (`:177-189`), Chunk column (`:905-909,920-921,1267-1271,1283-1284`), `to_dict()`; `TestPerChunkSurfaces` (`tests/unit/cli/test_search.py:4151`) passes; probe shows `(4 chunk matches)` and JSON `chunk_id`/`sequence`. The Chunk cell is `path#sequence`, but at 80 columns Rich ellipsizes the suffix for realistic paths — see Adjudication B. |
| 42 | MCP `query`/`vec_search` inputs accept `per_chunk`; the query handler schema lists it and the backend forwards it | ✓ VERIFIED (scope note S3) | `protocol.py:97,156`; signature-derived schema (`tools.py:139,356-357`); wire goldens list `per_chunk` on query and vec_search, not on lex_search; backend forwards (`backend.py:460,664`). |
| 43 | MCP re-map explicitly forwards `chunk_id`/`sequence`/`chunk_matches` | ✓ VERIFIED | `backend.py:194-196`; `TestChunkFieldRemap` (`tests/unit/mcp/test_backend.py:974`) passes. |
| 44 | `make docs-generate` clean; CLI reference documents `--offset` and `--per-chunk` | ✓ VERIFIED | Both generators run from an exported copy of HEAD (the working tree is untouched): `docs/cli-reference.md` and `docs/configuration.md` byte-identical to HEAD. `docs/cli-reference.md` has 3 `--offset` rows (`:491,534,569`) and 2 `--per-chunk` rows (`:504,575`). |
| 45 | B1 recorded after CORR-02 on the same scratch index as B0; `--compare b0.json` reports per-query deltas with ≥50 paired queries; deltas in `docs/benchmarking.md` labeled the BM25 no-drift check; held-out/SC1 old→new numbers cited | ✓ VERIFIED | `bench/b1.json`: 100 queries, same fingerprint. Reproduced at HEAD: `--compare b1.json` and `--compare b0.json` both n=100, mean 0.0, 100 unchanged. `docs/benchmarking.md:206-225` carries the CORR-02 narrative; the label is at `:212`. |

#### Plan 19-08 — CORR-04 (title-FTS migration, triggers, weighted bm25)

| # | Truth | Status | Evidence |
| --- | ----- | ------ | -------- |
| 46 | Populated DB migration drops vocab first, drops FTS/triggers, recreates two-column, runs `'rebuild'`, recreates vocab/triggers; title-only MATCH 0→1 | ✓ VERIFIED | `schema.py:497-630`; `TestTitleFtsMigration` passes. Independent probe on a hand-built legacy index: title-only MATCH `zebra` 0 → 1. |
| 47 | Rebuild populates exactly once (no rowid/content seed); structural assertion; row counts equal; unique token one row; deleted doc not MATCHable | ✓ VERIFIED | Exactly one documents-population statement (`schema.py:574`; the second `'rebuild'` at `:586` is the chunks table); old seed absent; probe: counts equal, unique token 1 row, not MATCHable after delete. |
| 48 | `documents_fts_v` still yields vocab after rebuild; suggest works; title UPDATE/DELETE sync; NULL titles clean; integrity_check ok | ✓ VERIFIED | `schema.py:529,596-599`; `tests/unit/database/test_schema_title_fts.py` (14 tests) passes; probe: vocab yields `zebra`, `PRAGMA integrity_check` = ok. |
| 49 | Fresh DB creates two-column directly; second `create_all` performs only detection reads | ✓ VERIFIED | `test_fresh_schema_creates_two_column_documents_fts` + second-`create_all` test pass; scratch index DDL is `content, title`; probe: DDL unchanged after a second `create_all`. |
| 50 | Chunks FTS and its three triggers stay byte-identical | ✓ VERIFIED | `schema.py:555-562,632-656` are content-only (no title); trigger test passes. |
| 51 | `bm25(documents_fts, ?, ?)` binds content/title weights left-to-right; 1.0/1.0 reproduces rank; constant starts 1.0; min_score before LIMIT/OFFSET | ✓ VERIFIED | `bm25.py:24-25,84-97,125,147`; `TestWeightedBM25` (`tests/unit/search/test_bm25.py:540`) passes; probe: `bm25(documents_fts,1.0,1.0)` equals `rank` for 40/2/40 rows. |
| 52 | `SearchOptions.title_weight` override changes title-vs-body ordering in a behavior test; not a setting/CLI flag | ✓ VERIFIED | `models.py:377`, `bm25.py:85`; reorder test passes; grep finds no title-weight knob in CLI/config/docs. |
| 53 | SC1 golden and held-out snapshot regenerated for the title-column effect with rationale; snapshot verdict computable | ✓ VERIFIED | SC1 docstring (`test_hybrid.py:779-788`) + held-out rationale; reproduction tests pass. |
| 54 | No lexical CJK title win claimed or tested; claim scoped to tokenized EN-style titles | ✓ VERIFIED | `docs/benchmarking.md:255-257` scopes the claim; the only CJK test in the cited files is a highlight fallback (`test_bm25.py:727`), not a title assertion. |

#### Plan 19-09 — CORR-04 (mtime index, MCP startup, per-leg gates, D-12 verdict)

| # | Truth | Status | Evidence |
| --- | ----- | ------ | -------- |
| 55 | `idx_documents_mtime` exists on fresh and migrated DBs and is in the expected index set | ✓ VERIFIED | `schema.py:769`; `test_mtime_index_is_created_on_fresh_and_migrated_databases` (`tests/unit/database/test_schema.py:451`) passes; scratch index has it. |
| 56 | MCP-only process runs schema migration once in `SearchBackend.__init__` at the backend's own dimension; second construction pays detection reads only | ✓ VERIFIED | `backend.py:290-293` calls `init_schema(embedding_dim=self.settings.embedding_dim, ...)`; `src/sif/database/database.py:36-76`; `TestSchemaInitializationAtStartup` (`tests/unit/mcp/test_backend.py:1084`) passes. |
| 57 | `ComparisonReport` exposes per-leg and per-leg×split noise gates in `--compare` JSON/table; groups <10 suppressed and named; `warrants_default_change` remains the held-out summary gate | ✓ VERIFIED | `src/sif/search/personal_bench.py:471-546` (`to_dict` carries `legs`, `leg_splits`, `gate.warrants_default_change`), `leg_noise_gates` (`:2015-2048`), assignment `:2397`; `src/sif/cli/commands/eval.py:428-485,553-556`. Live compare at HEAD: `legs` title n=50 / body n=50, `leg_splits` title heldout n=23 / body heldout n=26, 3 suppressed groups named on stderr. |
| 58 | Title-weight sweep opens the scratch index through `Database(...).init_schema()` and aborts unless stored `documents_fts` SQL has a title column | ✓ VERIFIED | Throwaway driver on disk, untracked and unchanged since 2026-11-15: `.planning/tmp/phase19/sweep_title_weight.py:90-99` (`_migrate`), `:102-118` (`_require_title_column`). Not executed this pass: `:37-38` hard-code the pre-archive bench paths. |
| 59 | Sweep evaluates 2.0/3.0/4.0 (refining at band edges) against B1's exact query set through `compare_saved_run` | ✓ VERIFIED | Driver `BASE_CANDIDATES=(2.0,3.0,4.0)`, `REFINEMENTS={2.0:2.5, 4.0:3.5}` (`:40-41`), `compare_saved_run` (`:188-195`); `bench/d12-verdict.json` lists all three. Reproduced at HEAD on a copy of the scratch index: 1.0/2.0/2.5/3.0/3.5/4.0 all delta 0.0 on both held-out legs. |
| 60 | D-12 gate applied to title held-out (noise-gate winner) AND body held-out (rounded mean delta ≥ -0.01) | ✓ VERIFIED | Driver `_accepted()` (`:141-147`); verdict shows title winner=false, body delta 0.0. |
| 61 | Pinned `_TITLE_WEIGHT` is accepted candidate or 1.0 on rejection; `bench/d12-verdict.json` records every candidate's deltas, CI, gate results, decision | ✓ VERIFIED | Artifact: `decision="rejected"`, `pinned_title_weight=1.0`, three candidates each with `title_heldout`/`body_heldout` n=23/26, mean delta 0.0, `sufficient=true`; `bm25.py:25` constant 1.0; `test_pinned_title_weight_is_the_measured_d12_value` passes. |
| 62 | Goldens/docs reflect pinned weight: snapshot rationale refreshed, SC1 docstring updated, `test_bm25.py` pins constant/behavior, `docs/benchmarking.md` records verdict; rejection valid | ✓ VERIFIED | Rationale/docstrings carry dedup + title-column + D-12 notes (`test_hybrid.py:789-791`); pin test passes; `docs/benchmarking.md:235-253` records the verdict. |
| 63 | Title weight is not a Settings field or CLI flag; option override remains internal and measurement-only | ✓ VERIFIED | `grep -i title_weight` over `src/sif/cli`, `src/sif/config`, `docs/cli-reference.md`, `docs/configuration.md` returns no hits; only `SearchOptions.title_weight` and `bm25.py`. |

**Score:** 61/63 plan truths verified; 2 UNCERTAIN (truths 17 and 34 — human decision requested, scope notes S2 and S4); 0 present-behavior-unverified.

### Scope Notes (literal wording vs HEAD)

Five truths carry a clause whose literal wording no longer describes HEAD. S1 and S3 are verified for the scope a recorded decision defines: the phase's own review record for S1 (WR-01, disposition fixed), and the previous report's successor-path adjudication for S3. S2 and S4 have no recorded decision — the previous report passed them without noticing — so those two truths are UNCERTAIN until a human accepts the later-phase mechanism (Human Verification item 5).

| Note | Truth | Clause read literally | What HEAD does | Cause | Guarantee that still holds |
| --- | --- | --- | --- | --- | --- |
| S1 | 8 | marker written "only when zero files failed" | written when no **stored** document failed (`incremental.py:199-212`) | in-phase review fix WR-01 (`19-REVIEW-DISPOSITION.md`: fixed) — a never-stored unparseable file otherwise stranded the migration forever | no stored document is stranded on the old convention (19-02 P1) |
| S2 | 17 | "one batched `document_embeddings` scan" | one display-gate probe + one indexed lookup per result on `embedded_documents` (`staleness.py:44-45,95-97`) | Phase 21, CORR-06 (roadmap: "bounded staleness ... via a transactional `embedded_documents` shadow") | derived at query time, display gate, degrade-unmarked, single attach |
| S3 | 31, 42 | "hand-written query schema" | schema derived from the registered tool signature (`tools.py:133-170`) | Phase 22 (`handlers.py` deleted in `48d5a981`) | offset/per_chunk validated and listed |
| S4 | 34 | start `min(max(target*4,50),2048)`; doubles only on a saturated batch | scoped/filtered searches seeded from a selectivity pre-count: 40 at limit 10 (unscoped 50), 50 at offset 30 (unscoped 160); escalates until target met or scope exhausted (`vector.py:193-202,257-294`) | Phase 20, FILT-03 "adaptive over-fetch with a selectivity bound" (`bfc1b41c`) | target `limit+offset`, hard cap 2048, empty page past the cap, full page when the rows exist |

S2 and S4 are the two the previous report passed without disclosing: its Phase 19 evidence for 34 cited `vector.py:187-249`, a range that already contained the Phase 20 branch, and for 17 it substituted "reads the `embedded_documents` shadow" for the truth's batched scan.

### Adjudications

**A. `--min-score` and Success Criterion 3 — no Phase 19 truth is contradicted; the defect is real and predates the phase.**

What the plan specified: "BM25 min_score order fixed" means the *order of operations* — `19-CONTEXT.md:13,46` state it as "BM25 `min_score` applied before pagination" against the pre-phase state "`min_score` filter after pagination" (`:92`). Plan 19-05 Task 1 fixes the predicate exactly (`threshold = 1.0 - 1.0 / options.min_score`, `rank >= threshold`, bound before `LIMIT ? OFFSET ?`) and says "Keep scores as `1.0 / (1.0 + abs(score))`". The predicate is set-equivalent to the pre-phase post-pagination skip `score < min_score`: Phase 19 moved the filter and preserved the row set. The 19-05 SUMMARY records that the executor noticed the negative-rank convention and kept the plan's predicate.

What HEAD does (scratch index, `sif search search "Saltiv Protocol Notes" -n 10`):

| `--min-score` | bound threshold | rows returned |
| --- | --- | --- |
| (none) | — | rank 1 `Saltiv Protocol Notes` 0.1057 (raw bm25 ≈ -8.46); rank 2 `Qelron Protocol Notes` 0.1527 (≈ -5.55) |
| 0.12 | -7.33 | rank 1 `Qelron Protocol Notes` 0.1527 — the best match is gone |
| 0.20, 0.23, 0.30 | -4.00, -3.35, -2.33 | nothing |

The UI-review observation reproduces: the displayed `Score` is `1/(1+|bm25|)` so the best match shows the lowest number, and `--min-score` removes the strongest matches first. Truth 27's four clauses all hold (pre-LIMIT/OFFSET, bound `1 - 1/min_score` with `rank >=`, hole-free pages, omitted at 0), and truth 32's no-drift check runs at `min_score=0`. The behaviour contradicts the help text "Minimum score threshold" (`search.py:530,731,962`; `docs/cli-reference.md:495,538,573`), not any must-have. It is carried to Human Verification item 2 as a product decision.

**B. Per-chunk output formats and Success Criterion 2 — no Phase 19 truth is contradicted; the claim is scoped to the Rich table and JSON.**

What the must-haves claim (19-07 truth 2): `chunk_matches` in the Rich table and JSON; per-chunk rows display `path#sequence` and expose `chunk_id`/`sequence` in JSON. The plan's task text is explicit — "render the path cell as `path#sequence` ... JSON output inherits the new fields ...; leave CSV, Markdown, and XML headers unchanged" — and its acceptance criteria name only "the table" and "JSON rows". SC2's "`--per-chunk` ... restores chunk-level results" holds at row granularity in every format. `19-CONTEXT.md` D-03 enumerates "`--per-chunk` output, JSON, and MCP", which reads as the three surfaces that were delivered.

What HEAD does (real per-chunk rows from a real vec0 database through the shipped renderers):

| Surface | Format | Chunk identity at HEAD |
| --- | --- | --- |
| `sif search query --per-chunk` | Rich table | `Chunk` column is `path#sequence` for chunk rows, bare path for the BM25 document rows; the `#sequence` suffix is ellipsized at 80 columns and still at 120 on the six-column hybrid table for a 31-character path |
| | JSON | `chunk_id`, `sequence`, `chunk_matches` present |
| | CSV | header `rank,score,title,path,collection,vectors_stale`; no chunk field — two rows can differ only by rank |
| | Markdown, XML | no chunk field |
| | `--files`, `-q` | path printed once per row (15 lines, 5 distinct in the probe) |
| `sif search vsearch --per-chunk` | Rich table, JSON | as above; `#sequence` visible at 120 columns, cut at 80 and 100 for the same path |
| | `--csv`, `--md`, `--xml`, `--files` | not options of `vsearch` (exit 2) |
| MCP `query` / `vec_search` | metadata | `chunk_id`/`sequence`/`chunk_matches` forwarded (`backend.py:194-196`) |

The formats the UI review names fall outside the must-have as the plan wrote it, so no truth is falsified. Two residual gaps are real for users: machine formats and `--files` carry chunk-level rows without identity, and the human table loses `#sequence` at the canonical width. Both go to Human Verification (items 1 and 3).

**C. The relaxed and skipped tests — no Phase 19 truth rested on them.**

The two relaxed assertions are title-truncation checks in `TestSearchOutputBranches` (`--line-numbers` output). No Phase 19 truth cites them; the per-chunk rendering contract is pinned by `TestPerChunkSurfaces`, which `c95d2cee` did not touch. The skip guards added in that commit are all conditional on Windows, a missing `tzset`, or symlink capability. On this macOS host the four files ran 360/360 with 0 skips, and every gated test that backs a Phase 19 truth (the 10 `alias_pair` context/staleness tests behind truth 17 and 19-03 P2/P3) reported PASSED. CI is Ubuntu and macOS, where none of those conditions is true. Two review findings remain open and are test-quality issues, not must-have failures: IN-07 (the relaxed assertions lost their lower bound, so `_TITLE_MAX_LEN` can shrink without failing them) and IN-08 (`symlink_or_skip` turns any `OSError`, including a broken fixture on a capable host, into a skip).

### Deferred Items

None. The deferred Info findings listed under Anti-Patterns are pre-existing or latent issues outside Phase 19 scope.

### Advisory (New Scope, Unevidenced)

None. Every finding raised this pass is evidenced by a command and is reported in the Adjudications or under Human Verification.

### Required Artifacts

`verify.artifacts` was run for all nine plans: 44/49 declared entries pass. The 5 non-passing entries are `src/sif/mcp/handlers.py` (declared by 19-05 and 19-07; deleted in Phase 22, property verified at the successor path) and the three bench JSON files, which the plans declare under the pre-archive `.planning/phases/19-...` prefix — they exist, tracked, at the archived location. No entry is missing or a stub.

| Artifact | Expected | Status | Details |
| -------- | -------- | ------ | ------- |
| `src/sif/core/models.py` | canonical JSON/checksum helpers; chunk result fields; offset/per_chunk/title_weight options | ✓ VERIFIED | Helpers at `:19-72`; fields wired into `to_dict()` (`:341-343`); internal-only title override (`:377`). |
| `src/sif/indexing/parser.py` | parser dispatch contract; checksum; `CONVENTION_VERSION` | ✓ VERIFIED | `create_parser` map (`:196-214`), all parsers use `compute_checksum`, version = 2 (`:19`). |
| `src/sif/indexing/incremental.py` | per-file dispatch, metadata fast path, marker, `reindexed_paths` | ✓ VERIFIED | All present; used by CLI/watch/MCP paths. |
| `src/sif/indexing/watcher.py` | embed candidates from `reindexed_paths` | ✓ VERIFIED | Burst + reconcile paths consume it (`:906,924`). |
| `src/sif/database/repositories.py` | canonical metadata persistence; `IndexMetaRepository` | ✓ VERIFIED | create/update serialize canonically (`:192,274`); get/set at `:731`. |
| `src/sif/database/schema.py` | `index_meta`, title-FTS migration, triggers, vocab shadow, savepoint, mtime index | ✓ VERIFIED | DDL/rebuild/triggers at `:451-666`; one population statement (`:574`); commit discipline. |
| `src/sif/database/database.py` | `init_schema(embedding_dim=None)` override | ✓ VERIFIED | `get_settings()` consulted only when no override/identity is supplied (`:56-61`). |
| `src/sif/search/bm25.py` | weighted bound bm25, pre-pagination min_score, global ranks | ✓ VERIFIED | Both branches bound; threshold inside the outer WHERE; ranks offset+position. |
| `src/sif/search/vector.py` | KNN chunk join, per-doc dedup, bounded escalation, per-chunk mode, single slice | ✓ VERIFIED | All present; scoped window is the Phase 20 form (scope note S4). |
| `src/sif/search/hybrid.py` | single offset slice, per-chunk key, pipeline enrichment, rerank window | ✓ VERIFIED | Both fuse sites keyed; pipeline enriches once per exit. |
| `src/sif/search/rrf.py` | optional key callable, chunk key helpers, metadata merge | ✓ VERIFIED | Two call sites use the helper; score expression untouched. |
| `src/sif/search/context_attach.py` | `enrich_results` composition | ✓ VERIFIED | Used by pipeline, CLI, MCP fallback and the Phase 22 lex/vec exits. |
| `src/sif/search/staleness.py` | D-09 docstring naming `enrich_results` | ✓ VERIFIED | Docstring correct; read mechanism is the Phase 21 shadow (scope note S2). |
| `src/sif/search/rerank.py` | rerank rebuild keeps chunk identity | ✓ VERIFIED | `:68-70`; the only post-phase hunk is the cache dir in `create_reranker` (`:436-438`). |
| `src/sif/search/personal_bench.py` | per-leg and leg×split gates | ✓ VERIFIED | `legs`/`leg_splits` in JSON; `math.fsum` mean (`:601-606`). |
| `src/sif/cli/commands/search.py` | `--offset`, `--per-chunk`, one enrichment per direct exit | ✓ VERIFIED | Flags + rendering + enrichment; machine formats carry no chunk field (Adjudication B). |
| `src/sif/cli/commands/index.py` | migrate event rendering | ✓ VERIFIED | `:185-190`; CLI test passes. |
| `src/sif/cli/commands/eval.py` | per-leg/leg×split comparison rendering | ✓ VERIFIED | `:428-485,553-556`; eval tests pass. |
| `src/sif/mcp/protocol.py` | offset/per_chunk input fields; no per_chunk on Lex | ✓ VERIFIED | `QueryInput.offset/per_chunk`, `LexSearchInput.offset`, `VecSearchInput.offset/per_chunk`. |
| `src/sif/mcp/handlers.py` | query schema offset/per_chunk + pass-through | ⚠️ SUPERSEDED | Deleted in Phase 22; property verified at `src/sif/mcp/tools.py` + `backend.py` forwarding + wire goldens. |
| `src/sif/mcp/tools.py` | published tool schemas (Phase 22 successor) | ✓ VERIFIED | `query`/`vec_search` expose offset+per_chunk; `lex_search` exposes offset only. |
| `src/sif/mcp/backend.py` | offset/per_chunk forwarding, one fallback enrichment, chunk metadata re-map, startup schema init | ✓ VERIFIED | All present; pipeline path not double-enriched. |
| `docs/cli-reference.md` | generated `--offset`/`--per-chunk` docs | ✓ VERIFIED | 3 + 2 generated rows; regeneration byte-identical. |
| `docs/benchmarking.md` | CORR-02 and CORR-04 before/after narratives + D-12 verdict | ✓ VERIFIED | `:206-257`; numbers reproduce. |
| `bench/b0.json` (archived path) | pre-ranking-change saved run | ✓ VERIFIED | 100 queries, fingerprint `8c006123784348d1`, bm25; zero delta reproduced. |
| `bench/b1.json` (archived path) | post-dedup, pre-title saved run | ✓ VERIFIED | 100 queries, same fingerprint; zero delta reproduced. |
| `bench/d12-verdict.json` (archived path) | candidate sweep + accept/reject decision | ✓ VERIFIED | rejected/pinned 1.0; 3 candidates with full GateResults; reproduced. |
| `tests/unit/database/test_schema_title_fts.py` | populated-DB migration suite | ✓ VERIFIED | 14 tests; all pass. |
| `tests/fixtures/bench/heldout_defaults.json` | regenerated snapshot + rationale | ✓ VERIFIED | Rationale records dedup/title-column/D-12; reproduction tests pass. |

### Key Link Verification

`verify.key-links` reports "Target not referenced in source" for every link whose `to` value is a file path or a DDL object rather than a literal string (1/26 by the tool). Each was verified by import and call-site inspection at HEAD:

| From | To | Via | Status | Details |
| ---- | -- | --- | ------ | ------- |
| `src/sif/indexing/parser.py` | `src/sif/core/models.py` | one `compute_checksum` helper | WIRED | Import `:13` + all 3 parsers call it (`:81,117,184`). |
| `src/sif/indexing/incremental.py` | `src/sif/indexing/parser.py` | per-file `create_parser(file_path) or TextParser()` | WIRED | Import `:31` + call site `:393`. |
| `src/sif/database/repositories.py` | `src/sif/core/models.py` | canonical metadata serializer on create/update | WIRED | Import `:16` + both SQL parameter sites (`:192,274`). |
| `src/sif/indexing/incremental.py` | `src/sif/database/repositories.py` | marker reads/writes; `_doc_repo.update` fast path | WIRED | Import + calls at `:91,156,212` and fast-path update (`:444`). |
| `src/sif/indexing/watcher.py` | `src/sif/indexing/incremental.py` | `result.reindexed_paths` into embed leg | WIRED | `watcher.py:906,924`. |
| `src/sif/search/hybrid.py` | `src/sif/search/context_attach.py` | every pipeline exit calls `enrich_results` once | WIRED | Import `:19`; `:356`, and `:308-309` behind `:367,379,484`; spy test passes. |
| `src/sif/search/context_attach.py` | `src/sif/search/staleness.py` | `enrich_results` composes staleness after attach | WIRED | Import `:41` + composition at `:342`. |
| `src/sif/cli/commands/search.py` | `src/sif/search/context_attach.py` | one call per direct CLI exit | WIRED | Import `:41`; `:613,872-874`. |
| `src/sif/mcp/backend.py` | `src/sif/search/context_attach.py` | fallback enriches once before re-map | WIRED | Import `:30`; `:490,501,534,609,676-678`; pipeline path not re-enriched. |
| `src/sif/cli/commands/search.py` | `src/sif/search/bm25.py` / `hybrid.py` | `SearchOptions(offset=...)`, single slice owner | WIRED | Imports `:40,42`; offset threaded at `:581,807,1091`. |
| `src/sif/mcp/backend.py` | `src/sif/search/hybrid.py` | MCP offset reaches `SearchOptions` and the pipeline slice | WIRED | Import `:33` + options at `:459-460,599,663-664`. |
| `src/sif/search/vector.py` | `src/sif/search/rrf.py` | deduped rows feed fusion; chunk fields survive | WIRED | Dedup output `vector.py:296-323`; `hybrid.py:20` fuses with `fuse_key_for`; `rrf.py:36-47`. |
| `src/sif/search/hybrid.py` | `src/sif/search/rrf.py` | both fuses pass `key=fuse_key_for(options.per_chunk)` | WIRED | Exactly two fuse sites under `src/sif` (`:150-155,451-455`), both keyed. |
| `src/sif/search/bm25.py` | `documents_fts` | bound `bm25(documents_fts, ?, ?)`; title column second | WIRED | Both branches bind `[content_weight, title_weight, query]` (`:87,125,147`). |
| `src/sif/search/bm25.py` | `src/sif/core/models.py` | `SearchOptions.title_weight` internal override | WIRED | Field read at `bm25.py:85`; no public knob. |
| `src/sif/database/schema.py` | `documents_fts_v` / documents triggers | drop vocab → rebuild → recreate vocab/triggers | WIRED | DDL sequence at `schema.py:519-665`; structural test. |
| `src/sif/mcp/backend.py` | `src/sif/database/database.py` | startup `init_schema(embedding_dim=...)` | WIRED | `backend.py:290`; tests pass. |
| `src/sif/mcp/tools.py` (successor to `handlers.py`) | `src/sif/mcp/backend.py` | offset/per_chunk validated then forwarded | WIRED | Signature-derived schema (`tools.py:133-170`) + `backend.py:459-460`. |
| `src/sif/mcp/backend.py` | `src/sif/core/models.py` | re-map copies chunk fields/vectors_stale | WIRED | Explicit metadata dict (`backend.py:189-197`). |
| `src/sif/cli/commands/eval.py` | `src/sif/search/personal_bench.py` | comparison rendering reads `legs`/`leg_splits` | WIRED | Rendering `eval.py:553-556`; fresh compare output contains both. |
| `bench/d12-verdict.json` | `src/sif/search/bm25.py` | recorded decision selects pinned `_TITLE_WEIGHT` | WIRED | Artifact `pinned_title_weight=1.0`; constant `bm25.py:25` + test pin. |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
| -------- | ------------- | ------ | ------------------ | ------ |
| `src/sif/cli/commands/search.py` | `results` | `BM25Searcher.search` / `VectorSearcher.search` / `SearchPipeline.search` | Yes — real SQL/KNN rows, enriched at entry | ✓ FLOWING |
| `src/sif/mcp/backend.py` | `core_results` → re-mapped `SearchResult.metadata` | pipeline search or BM25 fallback | Yes — explicit field copy, no static return | ✓ FLOWING |
| `src/sif/search/vector.py` | `candidates` / `page` | vec0 KNN JOIN to `document_chunks` | Yes — real distance-ordered rows | ✓ FLOWING |
| `src/sif/search/hybrid.py` | `fused_results` / `results` | BM25 + vector legs through RRF | Yes — real leg outputs, one slice | ✓ FLOWING |
| `src/sif/search/bm25.py` | cursor rows | `documents_fts` MATCH with weighted `bm25()` | Yes — real FTS scan | ✓ FLOWING |
| `src/sif/search/rerank.py` | `reranked` | rebuilt from the pre-rerank rows | Yes — chunk identity copied field by field (`:68-70`) | ✓ FLOWING |
| `tests/fixtures/bench/heldout_defaults.json` | static metrics | deterministic `build_bench_db`/`ConceptEmbedder` reproduction | N/A — recorded measurement artifact | N/A |
| `bench/b0.json`, `bench/b1.json`, `bench/d12-verdict.json` | static evidence | saved personal-eval runs / sweep output | N/A — recorded evidence; independently reproduced this pass | N/A |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
| -------- | ------- | ------ | ------ |
| Full regression gate (local, HEAD `4dbf386`, py3.13.9, macOS) | `env -u FORCE_COLOR HOME=<scratch> NO_COLOR=1 pytest -q --no-cov -rs` | 8 failed, 3255 passed, 1 skipped (live-launchd opt-in) in 122.76s. All 8 are home-vs-scratch-root guard tests under `tests/unit/scripts/` (breadcrumb_eval, chunk_sweep, harrier_eval), unrelated to Phase 19. Cause: my sandbox `HOME` sat under `/tmp`, a symlink to `/private/tmp`, so `Path.home()` and the resolved scratch root compared unequal. The same three files with `HOME` under `/private/tmp`: 165 passed | ⚠️ 8 harness-artifact failures, none at HEAD |
| CI Test Matrix run `45522236981` (push, `a25eb07`) | `gh run view 45522236981` | success on 8/8 cells + lint; 3259 passed, 2 skipped, 95.12% coverage on every cell. Since `a25eb07` the tree differs only under `.planning/` and in `tests/unit/search/test_rerank.py` | ✓ PASS |
| Phase-targeted unit and integration suites | `pytest -q --no-cov tests/unit/{indexing,database,search,cli,mcp} tests/integration/{test_search_correctness,test_incremental_equivalence,test_embed_idempotency}.py` | 2233 passed, 0 skipped in 49.48s | ✓ PASS |
| The four files flagged stale + `test_rerank.py` | `pytest -q --no-cov -rs tests/unit/cli/test_search.py tests/unit/database/test_repositories.py tests/unit/mcp/test_backend.py tests/unit/search/test_context_attach.py tests/unit/search/test_rerank.py` | 360 passed, 0 skipped | ✓ PASS |
| Named tests behind the behaviour-dependent truths | single selection of the classes listed in the truth tables | 226 passed in 2.99s | ✓ PASS |
| B0 reproduces at offset=0 / min_score=0 | `sif eval --personal --bm25-only -c bench-fixture --compare bench/b0.json --json --no-save` on a scratch index rebuilt from the fixture corpus | n=100, mean delta 0.0, unchanged 100; legs title n=50 / body n=50; leg_splits title heldout n=23, body heldout n=26; 3 suppressed groups named on stderr | ✓ PASS |
| B1 self-comparison | same with `--compare bench/b1.json` | n=100, mean 0.0, unchanged 100 | ✓ PASS |
| D-12 sweep reproduces | literal-mode BM25 pipeline per candidate weight, `compare_saved_run` against B1 | 1.0/2.0/2.5/3.0/3.5/4.0: title heldout n=23 delta 0.0 winner=false; body heldout n=26 delta 0.0 regression=false → rejected, pinned 1.0 (matches `d12-verdict.json`) | ✓ PASS |
| Checksum and parser contract | direct calls to `canonical_metadata_json` / `compute_checksum` / `create_parser` | 18/18 checks: NUL-separated hash, nested key coercion, reorder/edit behaviour, YAML `---` forms, date round-trip, `TextParser` fallback | ✓ PASS |
| BM25 `min_score` SQL shape | traced `BM25Searcher.search` on the scratch index | `min_score=0.23`: `AND m.score >= ?` with `-3.3478` bound before `LIMIT ? OFFSET ?`, scoped and unscoped; `min_score=0`: no predicate, no parameter | ✓ PASS |
| `min_score` hole-freedom | `sif search search ... --min-score 0.12` at `-n 10`, `-n 1 --offset 0`, `--offset 1` | `[Qelron]`, `[Qelron]`, `[]` | ✓ PASS |
| Page continuity under tied scores | 15 rows sharing one bm25 score, pages of 4 | four pages concatenate to the `-n 16` request on the scoped and `--all` paths | ✓ PASS |
| `min_score` direction (Adjudication A) | `sif search search "Saltiv Protocol Notes"` with `--min-score` 0 … 0.40 | best match (0.1057) removed at 0.12; nothing at ≥ 0.20 | ⚠️ reproduced defect, pre-existing |
| Per-chunk formats (Adjudication B) | real per-chunk rows through the shipped renderers and commands | JSON carries identity; CSV/Markdown/XML/`--files`/`-q` do not; `#sequence` ellipsized at 80 columns | ⚠️ reproduced, outside the must-have |
| Weighted BM25 equals `rank` | SQL on the scratch index | `bm25(documents_fts,1.0,1.0)` == `rank` for 40/2/40 rows | ✓ PASS |
| Title-FTS migration on a populated legacy index | hand-built one-column `documents_fts`, `create_all()` | MATCH 0 → 1; counts equal; unique token 1 row; vocab yields; deleted doc unmatchable; second `create_all` DDL unchanged; integrity ok; one population statement | ✓ PASS |
| `fetch_k` start (scope note S4) | traced KNN `k` on a real vec0 database | unscoped 50 (target 10), 160 (target 40); scoped 40 and 50; offset 5000 → `[]` on both | ℹ️ literal on unscoped only |
| Scratch index shape | sqlite inspection of the index built by the shipped CLI | 150 documents; `index_meta` with `convention:<id> = 2`; two-column `documents_fts`; three title-carrying triggers; `documents_fts_v`; `idx_documents_mtime` | ✓ PASS |
| Generated docs clean | generators run from an exported copy of HEAD | `docs/cli-reference.md` and `docs/configuration.md` byte-identical | ✓ PASS |
| Lint and format | `ruff check src tests`; `ruff format --check src tests` | All checks passed; 237 files already formatted | ✓ PASS |
| Type check (advisory) | `ty check src/sif` | Exit 1, 10 diagnostics: 5 in `embedding/embedder.py`, 4 in `search/rerank.py` (`:273,406,413,416` — reranker-backend model typing, not the Phase 19 lines `:68-70`), 1 in `models/download.py`. The CI `ty` step passes only because its job installs no `transformers`/`torch` and ignores import-not-found | ℹ️ Info |

### Probe Execution

No probes: no `scripts/*/tests/probe-*.sh` exist and no PLAN/SUMMARY declares one. Step 7c: SKIPPED (no probes). The throwaway D-12 driver under `.planning/tmp/phase19/` was read, not executed; its measurement was reproduced on a copy of a scratch index.

### Prohibitions (must-NOT checks)

All 30 plan-declared prohibitions were re-checked against HEAD. These plans carry bare `statement` entries (no `status`/`verification` field); they are treated as judgment-tier planner guardrails. This table is a non-authoritative LLM-judge verdict. Phase 19 has no UAT record resolving them, so every "hold" is still a human-review item; `prohibitions_flagged: 1`.

| Plan | # | Prohibition | Status | Current-code evidence |
| ---- | - | ----------- | ------ | --------------------- |
| 19-01 | 1 | No body-only change-detection hash | ✓ PASS | `compute_checksum` hashes body + NUL + full frontmatter (`models.py:64-72`). |
| 19-01 | 2 | No alteration of the Markdown body path | ✓ PASS | `frontmatter.loads` body extraction unchanged (`parser.py:57-90`). |
| 19-01 | 3 | No runtime dependency for parsing/serialization | ✓ PASS | `parser.py` imports stdlib plus the pre-existing `frontmatter`. |
| 19-02 | 1 | Marker never cleared before a clean pass | ✓ PASS | Written only after the loop and `failed_stored == 0` (`incremental.py:210-212`). |
| 19-02 | 2 | No re-chunk/re-embed when the body did not change | ✓ PASS | Metadata fast path returns before purging (`incremental.py:437-446`). |
| 19-02 | 3 | Migration never triggered from drift checks or `update_paths` | ✓ PASS | `update_paths` passes `migrating=False` and never reads the marker (`incremental.py:318`). |
| 19-03 | 1 | No persisted staleness flag or per-result embedding query | ⚠️ FLAGGED — superseded in letter by Phase 21 | `embedded_documents` is a persisted per-document embedded-state table and `mark_vector_staleness` issues one lookup per result against it (`staleness.py:44-45,95-97`). The result flag is still derived at query time, the read is bounded, and there is no full scan — the intent holds. Human review requested (item 4). |
| 19-03 | 2 | No loss of context descriptions/staleness markers while removing attaches | ✓ PASS | Attach sets only on match (`context_attach.py:311-313`); enrichment recomputes at every exit. |
| 19-03 | 3 | No SQL path pre-filter for context attachment | ✓ PASS | `_CONTEXTS_SQL` filters only `context_type='path'` (`context_attach.py:51-52`). |
| 19-04 | 1 | No double attach on the MCP pipeline path | ✓ PASS | Only fallback exits call `enrich_results`; pipeline output returned as enriched (`backend.py:490,501,534`). |
| 19-04 | 2 | Baseline scratch database or cache not committed | ✓ PASS | `git ls-files` under the phase dir lists only the three `bench/*.json` files. |
| 19-04 | 3 | Baseline not recorded before CORR-01 landed | ✓ PASS | B0 `created_at` 2026-11-15T03:25:51Z, after 19-01/19-02; the fingerprint hashes D-08 checksums and matches a HEAD-built index. |
| 19-05 | 1 | No interpolation of offset/limit/min_score into SQL | ✓ PASS | All values bound (`bm25.py:87,96,164`); confirmed by the SQL trace. |
| 19-05 | 2 | `min_score` never applied after pagination | ✓ PASS | Threshold inside the outer WHERE before `LIMIT ? OFFSET ?`. `search_chunks` (no production caller) keeps the old post-window filter — recorded deferral IN-05. |
| 19-05 | 3 | No double-applied offset between pipeline and hybrid | ✓ PASS | Pipeline calls hybrid with `offset=0` and slices once (`hybrid.py:417-428,482-484`). |
| 19-06 | 1 | RRF scoring math/weights/k unchanged by dedup | ✓ PASS | Score expression untouched (`rrf.py:108`); goldens pass. |
| 19-06 | 2 | No duplicate document rows from default vector/hybrid output | ✓ PASS | Vector grouping (`vector.py:296-323`) + hybrid safety-net dedup (`hybrid.py:178-210`). |
| 19-06 | 3 | `fetch_k` escalation bounded by an independent ceiling | ✓ PASS | `_MAX_FETCH_K = 2048`, clamped on both paths (`vector.py:25,197,231,293`). |
| 19-06 | 4 | Vector chunk identity not dropped when a doc is in both legs | ✓ PASS | `_merge_chunk_metadata` adopts non-null chunk fields (`rrf.py:36-47`). |
| 19-07 | 1 | No per-chunk flag on document-level surfaces | ✓ PASS | `sif search` rejects the flag (exit 2); `lex_search` schema has offset only (`tools.py:313-337`). |
| 19-07 | 2 | Chunk fields never silently dropped at the MCP re-map | ✓ PASS | Explicit metadata dict (`backend.py:194-196`). |
| 19-07 | 3 | Generated docs not hand-edited | ✓ PASS | Regeneration from an exported copy is byte-identical. |
| 19-08 | 1 | No reliance on `CREATE VIRTUAL TABLE IF NOT EXISTS` to add the title column | ✓ PASS | `_fts_column_names()` detects and drives drop/recreate/rebuild (`schema.py:451-503`). |
| 19-08 | 2 | `documents_fts_v` dropped before `documents_fts` | ✓ PASS | Drop order `schema.py:529` then `:536`. |
| 19-08 | 3 | Column weights never interpolated into SQL | ✓ PASS | Bound as `?` parameters (`bm25.py:87,125,147`). |
| 19-08 | 4 | No CJK lexical title win promised or tested | ✓ PASS | Claim scoped to EN-style tokenized titles (`docs/benchmarking.md:255-257`). |
| 19-09 | 1 | Title weight not a Settings field or CLI flag | ✓ PASS | grep over CLI/config/docs returns no hits. |
| 19-09 | 2 | No title-weight win declared inside noise or from tuning-only data | ✓ PASS | Artifact records rejection; `_TITLE_WEIGHT = 1.0`. |
| 19-09 | 3 | No shipped title weight regressing body/hybrid held-out beyond the 0.01 tie rule | ✓ PASS | Body held-out mean delta 0.0, reproduced at HEAD. |
| 19-09 | 4 | No MCP-only deployment left on the pre-title schema | ✓ PASS | `SearchBackend.__init__` runs `init_schema` (`backend.py:290`); startup tests pass. |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
| ----------- | ---------- | ----------- | ------ | -------- |
| CORR-01 | 19-01, 19-02 | Frontmatter-only edits become searchable (parser dispatch + metadata-aware checksum, ONE shared forced-reindex migration, md body byte-identical, YAML `---` fixed) | ✓ SATISFIED | Truths 1-14: canonical checksum + dispatch + metadata fast path + single `CONVENTION_VERSION=2` migration. |
| CORR-02 | 19-06, 19-07 | One result per document by default (pre-fusion dedup, `--per-chunk`, bench before/after, goldens rationale) | ✓ SATISFIED — truth 34 UNCERTAIN (S4) | Truths 33-45: vector dedup + chunk identity + per-chunk fusion + surfaces + B0/B1 + snapshot/SC1 evidence. |
| CORR-03 | 19-05 | Deterministic pagination (CLI/MCP offset, single slice, BM25 min_score order, offset=0 contract) | ✓ SATISFIED | Truths 24-32: offset surfaces + one slice owner + pre-pagination threshold + global ranks; B0 reproduced. |
| CORR-04 | 19-08, 19-09 | Title-aware ranking (title-FTS migration, rewritten triggers, measured bm25 weights, mtime index, vocab survival) | ✓ SATISFIED | Truths 46-63: two-column FTS + triggers + weighted bound bm25 + mtime index + populated-DB vocab/DYM tests + D-12 rejection reproduced. |
| CORR-05 | 19-03, 19-04 | No redundant attach (ONE context/staleness attach at pipeline exit) | ✓ SATISFIED — truth 17 UNCERTAIN (S2) | Truths 15-23: raw searchers + `enrich_results` owners at pipeline/CLI/MCP fallback; spies prove exactly one. |

No orphaned requirements: `.planning/milestones/v1.2-REQUIREMENTS.md` maps exactly CORR-01..CORR-05 to Phase 19, and all five appear in this phase's plan frontmatter. CORR-06 is mapped to Phase 21 and is correctly absent from Phase 19 plans.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
| ---- | ---- | ------- | -------- | ------ |
| — | — | No `TBD`/`FIXME`/`XXX` and no `TODO`/`HACK`/`PLACEHOLDER` markers in the covered files | — | Debt-marker gate clean (grep count 0). |
| — | — | No stub returns in changed code | — | Empty-list returns are exclude-all sentinels and accumulators; every render path receives real query rows. |
| `tests/unit/cli/test_search.py` | `2097-2100`, `2313-2316` | Relaxed title assertions (IN-07) | ℹ️ Info | Lower bound of the title truncation check is now 10 characters; not a Phase 19 contract. Open in `19-REVIEW-DISPOSITION.md`. |
| `tests/support/__init__.py` | `26-32` | `symlink_or_skip` skips on any `OSError` (IN-08) | ℹ️ Info | A broken fixture on a symlink-capable host would skip instead of fail. None skipped in the local run; CI's 2 skips per cell are not itemised in its log, and the only ambient skip conditions in the suite are the live-launchd opt-in and an absent `claude` CLI. Open. |

Deferred Info findings carried from `19-REVIEW-DISPOSITION.md` (not phase-goal blockers): IN-01 vector scores L2-derived but documented as cosine; IN-02 rerank rebuild drops `vectors_stale` (recomputed by the pipeline enrichment after rerank); IN-03 resolved by Phase 22 (`vec_search` registered); IN-05 `search_chunks` post-window `min_score`, no production caller; IN-06 MCP backend creates an empty index at a nonexistent `SIF_DB_PATH`.

**Test quality.** No disabled test is linked to a Phase 19 requirement: every skip in the covered files is an environment-capability guard (sqlite-vec, symlink, `tzset`, Windows), and 0 skipped in the 2233-test targeted run. The goldens' expected values come from the deterministic `ConceptEmbedder` harness (PARTIAL provenance: they pin the contract, they do not prove ranking quality — that is the held-out snapshot's role). Assertion strength is value-level (exact row ids, ranks, scores).

### Decision Coverage

All trackable CONTEXT.md decisions are honored by shipped artifacts — 12/12 (`check.decision-coverage-verify`, non-blocking).

### Human Verification Required

The previous report recorded "N/A — no user-facing UI surface". That was wrong: this phase ships CLI output a user reads (table columns, annotations, help text, machine formats), and the phase's own UI review exists. Five items need a human decision.

#### 1. Per-chunk table at 80 columns

**Test:** In an 80-column terminal, run `sif search query --per-chunk QUERY` and `sif search vsearch --per-chunk QUERY` on a corpus whose paths are 30+ characters.
**Expected:** Each chunk row shows which chunk it is (`path#sequence`).
**Why human:** The Chunk cell is built as `path#sequence`, but Rich ellipsizes the tail when the column is narrow. Rendered here from the shipped table code with real per-chunk rows (rich 14.3.3): at 80 columns both tables show `/notes/chunk…`; at 120 the vector table shows `…md#1` while the hybrid table still cuts it. Column allocation depends on the other cells, so the exact cut needs a real terminal.

#### 2. `--min-score` removes the best matches first

**Test:** On the bench-fixture index run `sif search search "Saltiv Protocol Notes" -n 10`, then add `--min-score 0.12` and `--min-score 0.23`.
**Expected:** Going by the help text "Minimum score threshold", weaker matches disappear and the best match survives.
**Why human:** Observed at HEAD: rank 1 (best BM25 match) is removed at 0.12 and nothing survives at 0.23, because `Score` is `1/(1+|bm25|)`. Phase 19 specified and pinned this predicate (Adjudication A), so whether to change the score map and threshold, or only the help text, is a product decision.

#### 3. Per-chunk rows in machine formats

**Test:** Run `sif search query --per-chunk QUERY` with `--csv`, `--md`, `--xml` and `--files` on a document with several matching chunks.
**Expected:** Decide whether those rows must carry `chunk_id`/`sequence` and whether `--files` may print a path once per row.
**Why human:** At HEAD they carry chunk-level rows without identity and `--files` repeats the path. The plan scoped only the Rich table and JSON (Adjudication B); accepting or extending that scope is a human call.

#### 4. Prohibition 19-03 P1

**Test:** Review `src/sif/search/staleness.py:44-45,67-98` against "MUST NOT persist vector staleness as a per-document flag or issue a per-result embedding query".
**Expected:** A recorded decision that the Phase 21 shadow read is the accepted successor of the Phase 19 batched scan.
**Why human:** Judgment-tier prohibition with no human resolution on record; its letter no longer describes HEAD while its intent holds.

#### 5. Scope notes S2 and S4

**Test:** Decide whether truths 17 and 34 are accepted for their guarantees or must hold literally.
**Expected:** Either record overrides for the Phase 20/21 mechanisms, or ask for the Phase 19 literal behaviour back.
**Why human:** Two clauses are literally false on paths a later roadmap phase changed. The verifier cannot accept a deviation on the developer's behalf.

### Gaps Summary

No truth failed and no regression was found. All five roadmap success criteria hold at HEAD `4dbf386`; 61 of the 63 functional plan must-haves are verified and the other two (17, 34) hold for their guarantees but are UNCERTAIN because a later phase replaced the mechanism their wording names. The delta since `b817ebb` (four test files, one `rerank.py` hunk, three new tests) changed no Phase 19 behaviour.

The status is `human_needed` rather than `passed` for three reasons, none of which is a missing or broken deliverable:

- Five truths carry a clause whose literal wording no longer describes HEAD (scope notes S1-S4). Each holds for the guarantee it asserts. S2 (truth 17, Phase 21 shadow read) and S4 (truth 34, Phase 20 scoped fetch window) were passed silently by the previous report and are now UNCERTAIN; S2 also puts prohibition 19-03 P1 in tension with its letter, so that prohibition is flagged.
- Two live findings on this phase's CLI surface intersect its success criteria but contradict no must-have as worded: `--min-score` drops the best BM25 matches first (pre-existing score map, predicate specified by Plan 19-05), and per-chunk chunk identity is absent from CSV/Markdown/XML/`--files` and truncated from the Rich table at 80 columns (formats the plan scoped out, plus a rendering limitation).
- Phase 19's 30 judgment-tier prohibitions have no human resolution on record.

Each needs a decision, not a code change recommended by this verification.

---

_Verified: 2026-11-25T10:38:29Z_
_Verifier: Claude (gsd-verifier)_
