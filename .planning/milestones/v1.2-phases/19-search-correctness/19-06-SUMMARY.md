---
phase: 19-search-correctness
plan: 06
subsystem: search
tags: [dedup, chunk-identity, chunk-matches, per-chunk, rrf, vector-search, hybrid-search, bench-snapshot, corr-02]

# Dependency graph
requires:
  - phase: 19-search-correctness
    provides: "19-05 one offset slice owner per query path and global rank numbering; 19-03 raw searcher outputs with pipeline-exit enrichment; 19-04 B0 baseline"
provides:
  - "VectorSearcher per-document dedup before fusion: best-distance chunk wins, chunk_id/sequence carried, chunk_matches counts pre-dedup rows"
  - "bounded fetch_k escalation (starts min(max(target*4,50),2048); doubles only on a saturated batch while limit+offset is unmet)"
  - "SearchResult.chunk_id/.sequence/.chunk_matches + to_dict entries; SearchOptions.per_chunk"
  - "RRFFusion.fuse(key=...) plus shared chunk_key/fuse_key_for helpers and chunk-metadata merging (score math unchanged)"
  - "per-chunk fusion key at both fuse sites: HybridSearcher source fusion and SearchPipeline cross-query variant fusion"
  - "regenerated hybrid SC1 golden (post-dedup baseline) and regenerated held-out snapshot with the dedup rationale"
  - "chunky-document regression and dedup-aware page continuity integration tests"
affects: [19-07 (CLI JSON/table and MCP surfaces consume chunk fields), 19-08/19-09 (golden and snapshot refreshes append to the rationale), 20 (pagination composes with dedup), 21 (dedup consumes the embedded-at depth signal), 22 (MCP per_chunk parity)]

# Actuals (#2632) — chars/4 over the realized diff (same scale as the plan estimate)
actuals:
  tokens: 16967
  tasks: 3
  commits: 6

commits: 6
plan_head_before: 6ea14008c001f82aaad755ba5c03ea66aa5081b7
plan_head_after: 657ff29c1f83cd023b2d5704b474672c06d810a1

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Dedup lives in the vector leg before fusion: group KNN rows by document in distance order, best row wins, chunk_matches counts the group"
    - "Escalation is saturation-driven: double fetch_k only while the batch returned exactly k rows and the target is unmet, with an independent module ceiling"
    - "One shared fusion grouping key (chunk_key / fuse_key_for) selected at every fuse that can receive chunk rows; None means document-keyed"
    - "RRF merge is metadata-only: adopt non-null chunk identity from later rows, keep max(chunk_matches); scores and ranks are untouched"
    - "Per-chunk mode skips the post-fusion document collapse; the default keeps it as a metadata-merging safety net"

key-files:
  created: []
  modified:
    - src/sif/core/models.py
    - src/sif/search/vector.py
    - src/sif/search/rrf.py
    - src/sif/search/hybrid.py
    - src/sif/search/rerank.py
    - tests/unit/search/test_vector.py
    - tests/unit/search/test_hybrid.py
    - tests/unit/search/test_rrf.py
    - tests/unit/search/test_collection_filter.py
    - tests/unit/search/test_bench_snapshot.py
    - tests/integration/test_search_correctness.py
    - tests/integration/test_embed_idempotency.py
    - tests/fixtures/bench/heldout_defaults.json

key-decisions:
  - "Vector dedup runs inside VectorSearcher after the min_score filter: rows group by document in distance order, the best row wins and carries chunk_id/sequence, and chunk_matches counts the group; per_chunk=True keeps the rows ungrouped with chunk_matches 0."
  - "fetch_k starts at min(max((limit+offset)*4, 50), _MAX_FETCH_K=2048) and doubles only while the batch returned exactly k rows and the distinct target is unmet; the cap is independent of the requested offset, so a past-cap page is empty rather than unbounded KNN work."
  - "RRFFusion.fuse gained an optional key callable; chunk_key returns chunk_id or document_id and fuse_key_for(per_chunk) is the single selector used at both fuse sites (source fusion and cross-query variant fusion). Score expressions, weights, and k are unchanged."
  - "The RRF merge adopts non-null chunk_id/sequence from later rows and keeps max(chunk_matches); the default hybrid path keeps _deduplicate_results as a metadata-merging safety net while per-chunk mode skips it, and the early single-leg returns rely on the legs' own dedup (vector deduped, BM25 document-level)."
  - "The rerank rebuild copies chunk identity (Rule 2 deviation): D-03's public contract would otherwise silently drop chunk fields on the reranked path."
  - "The SC1 hybrid golden was regenerated as the post-dedup baseline (scores byte-identical on the one-chunk fixture; chunk fields added) and the RRF golden is documented as unchanged because the score expression is untouched."
  - "The held-out snapshot was regenerated through the deterministic ConceptEmbedder index; pre-dedup and post-dedup totals and per_category values are identical because the fixture corpus has one chunk per document, so the contract evidence is the SC1 golden plus the chunky-document regression, and the --bm25-only runs are labeled the BM25 no-drift check."

patterns-established:
  - "Contract-change evidence records both the metric snapshot (with rationale) and a behavioral regression that fails under the old contract (chunky document starving a limit=10 page)."
  - "Hand-built minimal test DBs must mirror the KNN join target (document_chunks) or they stop exercising the production SQL shape."

requirements-completed: [CORR-02]

# Coverage metadata (#1602)
coverage:
  - id: D1
    description: "VectorSearcher returns one row per document by default, with the best-distance chunk's identity and chunk_matches counting pre-dedup rows"
    requirement: CORR-02
    verification:
      - kind: unit
        ref: "tests/unit/search/test_vector.py#TestVectorDocumentDedup (collapse, best-distance identity, 5-chunk/limit=10, per-chunk rows, legacy NULL identity, to_dict)"
        status: pass
      - kind: integration
        ref: "tests/integration/test_search_correctness.py#TestChunkyDocumentDedup.test_vector_limit_ten_returns_ten_distinct_documents"
        status: pass
    human_judgment: false
  - id: D2
    description: "fetch_k escalation is saturation-driven and bounded by _MAX_FETCH_K = 2048; no escalation when the first batch meets the target"
    requirement: CORR-02
    verification:
      - kind: unit
        ref: "tests/unit/search/test_vector.py#TestVectorDocumentDedup.test_escalation_stops_at_the_ceiling + test_no_escalation_when_first_batch_satisfies_target + TestVectorOffsetPagination"
        status: pass
    human_judgment: false
  - id: D3
    description: "RRF fuses chunk rows through the shared chunk_key/fuse_key_for helper at both fuse sites, merges chunk metadata, and keeps the scoring math byte-identical"
    requirement: CORR-02
    verification:
      - kind: unit
        ref: "tests/unit/search/test_rrf.py#TestRRFChunkKey (6 tests incl. byte-identical scores) + TestRRFSC1Golden"
        status: pass
      - kind: unit
        ref: "tests/unit/search/test_hybrid.py#TestHybridChunkFusion (dual-leg identity, per-chunk rows, both fuse-site key spies, safety-net merge)"
        status: pass
    human_judgment: false
  - id: D4
    description: "Default hybrid output is per-document with vector chunk metadata; per-chunk mode survives multi-variant pipeline fusion; SC1 golden regenerated as the post-dedup baseline"
    requirement: CORR-02
    verification:
      - kind: unit
        ref: "tests/unit/search/test_hybrid.py#TestHybridSC1PipelineGolden (default + explicit defaults, candidate fetch, pipeline off-path) and TestPerChunkPipelineMultiVariant (2 tests)"
        status: pass
      - kind: integration
        ref: "tests/integration/test_search_correctness.py#TestChunkyDocumentDedup.test_hybrid_default_limit_ten_returns_ten_distinct_documents + test_per_chunk_mode_returns_the_chunky_chunk_rows + test_dedup_aware_page_continuity"
        status: pass
    human_judgment: false
  - id: D5
    description: "The held-out snapshot reproduces from the deterministic index with a rationale recording the dedup contract change and before/after numbers"
    requirement: CORR-02
    verification:
      - kind: unit
        ref: "tests/unit/search/test_bench_snapshot.py#TestHeldoutSnapshotReproduction + TestSnapshotVerdict + TestSweepWinnerEvidence"
        status: pass
    human_judgment: false
  - id: D6
    description: "Embed idempotency probe asserts the new per-document vector contract (one row + chunk_matches; per_chunk one row per live chunk)"
    requirement: CORR-02
    verification:
      - kind: integration
        ref: "tests/integration/test_embed_idempotency.py#TestEmbedIdempotency.test_vector_search_returns_each_chunk_once_after_two_runs"
        status: pass
    human_judgment: false

duration: 13min
completed: 2026-11-15
status: complete
---

# Phase 19 Plan 06: Per-Document Dedup and Chunk Identity Summary

**Default vector and hybrid pages now return one row per document with vector-leg dedup before fusion, `chunk_id`/`sequence`/`chunk_matches` in the result contract, a bounded saturation-driven `fetch_k` escalation, and a chunk-keyed `per_chunk` escape hatch at both RRF fuse sites**

## Performance

- **Duration:** 13 min
- **Started:** 2026-11-15T03:51:17Z
- **Completed:** 2026-11-15T04:04:37Z
- **Tasks:** 3/3
- **Files modified:** 13 (5 source, 8 test/fixture)

## Accomplishments

- `VectorSearcher`'s KNN SELECT now joins `document_chunks` for `chunk_id`/`sequence`; after the `min_score` filter it groups rows by `document_id` in distance order, keeps the best-distance winner with its chunk identity, and sets `chunk_matches` to the group size. `per_chunk=True` keeps the ungrouped rows and leaves `chunk_matches` at 0.
- `fetch_k` starts at `min(max((limit+offset)*4, 50), _MAX_FETCH_K)` and doubles only while the batch returned exactly k rows and the target is unmet, clamped at the independent `_MAX_FETCH_K = 2048`; a past-cap offset is an empty page, and a satisfying first batch never re-queries.
- `SearchResult` gained `chunk_id`, `sequence`, and `chunk_matches` (all defaulted, all in `to_dict()`); `SearchOptions` gained `per_chunk`.
- `RRFFusion.fuse` gained an optional grouping `key` plus module helpers `chunk_key` (chunk id, else document id) and `fuse_key_for(per_chunk)` (the single selector both fuse sites import). The merge adopts non-null chunk identity from later rows and keeps `max(chunk_matches)`; score expressions, weights, and `k` are byte-identical.
- `HybridSearcher.search` selects its source-fusion key through `fuse_key_for(options.per_chunk)`; the default path still runs the post-fusion safety-net dedup (now metadata-merging), while per-chunk mode skips it so chunk rows survive.
- `SearchPipeline.search` selects the same key for its cross-query variant fusion, so a multi-variant per-chunk search keeps both chunk rows of a two-chunk document (proven on a real schema + vec0 DB), while the default multi-variant page is one row per document.
- The `_sort_and_build_results` rerank rebuild copies chunk identity, keeping D-03's contract intact on the reranked path (Rule 2 deviation).
- The SC1 hybrid golden was regenerated as the post-dedup per-document baseline. On this one-chunk-per-document fixture the `bm25_score`/`rrf_score` values are unchanged; the new fields record the contract, and dual-leg rows adopt the vector leg's chunk identity. The RRF golden's docstring now records why its values are unchanged.
- The committed held-out snapshot was regenerated through the deterministic `build_bench_db`/`ConceptEmbedder` harness with a `rationale` that records pre-dedup and post-dedup totals plus `per_category` values, cites the SC1 golden as the granular ranking evidence, and labels the `--bm25-only` runs the BM25 no-drift check. Numbers are identical because the fixture corpus has one chunk per document; the behavioral contract evidence is the chunky-document regression.
- The integration suite now proves a six-chunk document cannot shrink a `limit=10` default page below ten distinct documents on either the vector or hybrid path, that its `chunk_matches` is 6, that all six chunk rows are individually addressable in per-chunk mode, and that dedup-aware page continuity still holds.
- The embed idempotency probe now asserts the per-document default (`chunk_matches == live chunk count`) and uses `per_chunk=True` for the one-row-per-live-chunk proof, preserving its historical-duplicate intent.

## Task Commits

Each task was committed atomically:

1. **Task 1: Per-document dedup and chunk identity in VectorSearcher (tracer)** - `918bc64` (feat)
2. **Task 2: Per-chunk fusion key at both fuse sites, RRF metadata merge, safety-net dedup** - `3946b3f` (feat)
3. **Task 3: Held-out snapshot, chunky-doc regression, page continuity** - `a899370` (test)
4. **Embed idempotency contract alignment** - `6ef3602` (test)
5. **Formatting of the chunky-corpus helper** - `3c3b235` (style)
6. **RRF golden post-dedup rationale** - `657ff29` (test)

**Plan metadata:** committed after this SUMMARY (docs: complete plan)

_Note: Task 1 ran as the plan's tracer; the auto-mode feedback gate re-ran its `<verify>` end-to-end green (33 passed) before expansion._

## Files Created/Modified

- `src/sif/core/models.py` - `SearchResult.chunk_id/.sequence/.chunk_matches` + `to_dict()` entries; `SearchOptions.per_chunk`
- `src/sif/search/vector.py` - KNN chunk join; `_candidates` document grouping + `chunk_matches`; `_row_to_result`; bounded escalation loop; one page slice + global ranks
- `src/sif/search/rrf.py` - `chunk_key`/`fuse_key_for`/`_merge_chunk_metadata`; optional `key` on `fuse`; chunk metadata merge (math unchanged)
- `src/sif/search/hybrid.py` - source-fusion key; per-chunk skip of the safety-net dedup; metadata-merging `_deduplicate_results`; variant-fusion key
- `src/sif/search/rerank.py` - rebuild preserves chunk identity (Rule 2)
- `tests/unit/search/test_vector.py` - `TestVectorDocumentDedup` (8 tests incl. escalation, per-chunk, legacy NULL, to_dict); fixture join target
- `tests/unit/search/test_hybrid.py` - regenerated SC1 snapshot/docstring; `TestHybridChunkFusion` (8 tests); `TestPerChunkPipelineMultiVariant` (2 real-DB tests); variant-fuse kwargs
- `tests/unit/search/test_rrf.py` - `TestRRFChunkKey` (7 tests); SC1 docstring note
- `tests/unit/search/test_collection_filter.py` - fixture gains `document_chunks`
- `tests/unit/search/test_bench_snapshot.py` - provenance + dedup rationale docstring
- `tests/integration/test_search_correctness.py` - `_build_chunky_db` + `TestChunkyDocumentDedup` (4 tests)
- `tests/integration/test_embed_idempotency.py` - per-document vector-contract assertions
- `tests/fixtures/bench/heldout_defaults.json` - regenerated numbers (identical) + dedup rationale + date

## Decisions Made

- Dedup inside the vector leg after `min_score` (not in RRF): keeps the fusion math untouched and makes the default page length independent of chunk density.
- The escalation predicate keys off the raw KNN batch size, not the filtered/grouped count: only a saturated batch can hide more rows, so a short batch never re-queries.
- `fuse_key_for` is a function pair (`chunk_key` / `None`) rather than a boolean threaded into RRF, so both fuse sites share one selection seam and the scoring code stays mode-agnostic.
- Per-chunk mode deliberately skips the post-fusion safety net; the default keeps it as a metadata-merging backstop.
- On the deterministic single-chunk bench corpus, dedup moves no metric; the change is recorded through the contract goldens and the chunky-document behavioral regression rather than fabricated metric movement.
- The `--bm25-only` B0/B1 saved runs are explicitly not dedup evidence (the vector leg is never constructed); their role is the BM25 no-drift check.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Critical] Rerank rebuild dropped chunk identity**
- **Found during:** Task 2
- **Issue:** `_sort_and_build_results` constructs new `SearchResult` objects from the pre-rerank rows; without copying the new fields, the public `chunk_id`/`sequence`/`chunk_matches` contract silently empties on every reranked pipeline path.
- **Fix:** Copy all three fields in the rebuild.
- **Files modified:** `src/sif/search/rerank.py`
- **Verification:** `tests/unit/search/test_rerank.py` and the pipeline suites stay green; chunk identity is now preserved through rebuilds.
- **Committed in:** `3946b3f` (Task 2 commit)

**2. [Rule 3 - Blocking] Hand-built vector fixtures lacked the join target**
- **Found during:** Task 1
- **Issue:** The KNN SELECT now LEFT JOINs `document_chunks`; minimal test DBs in `test_vector.py` and `test_collection_filter.py` did not create that table, so the production SQL shape could not run.
- **Fix:** Add the `document_chunks` DDL to those fixtures (and chunk rows where the fixture seeds vector rows), mirroring the real schema.
- **Files modified:** `tests/unit/search/test_vector.py`, `tests/unit/search/test_collection_filter.py`
- **Verification:** Both files pass; the filtered-recall and offset-pagination contracts remain pinned.
- **Committed in:** `918bc64` (Task 1 commit)

**3. [Rule 3 - Blocking] Embed idempotency probe asserted the superseded per-chunk default**
- **Found during:** the plan-level full-suite gate
- **Issue:** `test_vector_search_returns_each_chunk_once_after_two_runs` asserted `len(results) == chunk_count` for a multi-chunk document — the pre-CORR-02 contract. Under the new default the page is one row per document.
- **Fix:** Assert one default row with `chunk_matches == chunk_count`, and use `per_chunk=True` for the one-row-per-live-chunk proof. The historical-duplicate intent is unchanged.
- **Files modified:** `tests/integration/test_embed_idempotency.py`
- **Verification:** 9/9 idempotency tests pass; full suite green.
- **Committed in:** `6ef3602`

---

**Total deviations:** 3 auto-fixed (1 missing critical, 2 blocking). **Impact:** All three are contract-preservation or test-fixture adaptations required by the planned behavior change; no scope creep and no production behavior beyond the plan.

## Issues Encountered

- The deterministic held-out bench corpus has exactly one chunk per document, so per-document dedup cannot move its metrics. The plan anticipated the possibility ("carry the pre-dedup and post-dedup numbers"); both sets are identical and recorded verbatim, with the contract evidence carried by the SC1 golden and the chunky-document regression instead of a metric delta.
- `ruff` flagged `fuse` complexity after the merge logic landed; the merge was extracted into `_merge_chunk_metadata` (no behavior change) before the Task 2 commit.

## User Setup Required

None - no external service configuration required.

## Verification Results

- Task 1 `<verify>`: `pytest tests/unit/search/test_vector.py -x --no-cov` -> 33 passed (also the tracer gate re-run)
- Task 2 `<verify>`: `pytest tests/unit/search/test_hybrid.py tests/unit/search/test_rrf.py -x --no-cov` -> 95 passed
- Task 3 `<verify>`: `pytest tests/unit/search/test_bench_snapshot.py tests/integration/test_search_correctness.py -x --no-cov` -> 24 passed
- Wider regression sweep: `pytest tests/unit/search tests/unit/cli/test_search.py tests/unit/cli/test_search_pagination.py tests/unit/mcp/test_backend.py -q --no-cov` -> 749 passed
- Plan-level: `pytest tests/unit/search tests/integration/test_search_correctness.py -x --no-cov` -> 539 passed
- Full suite (CLAUDE.md gate): `env -u FORCE_COLOR NO_COLOR=1 pytest` -> 1989 passed, 1 skipped, coverage 95.30% (fail_under=90)
- `ruff check src tests` -> All checks passed; `ruff format --check src tests` -> 197 files already formatted
- `ty check src/sif` -> All checks passed
- Snapshot diff: only the `rationale` string and the `generated` date changed; every recomputed number equals the committed pre-dedup value
- Dependency guard: no `pyproject.toml`/`uv.lock` change in this plan (0 files)
- Fuse-site audit: exactly two `RRFFusion.fuse` call sites in `src/sif`, both pass `key=fuse_key_for(...)`; no hardcoded `document_id` key

## Next Phase Readiness

- CORR-02's core contract is closed: default vector and hybrid pages are one row per document, chunk identity and the collapsed match count are part of `SearchResult`, and per-chunk mode restores chunk rows through every fuse the pipeline runs.
- Plan 19-07 can surface `chunk_id`/`sequence`/`chunk_matches` in CLI table/JSON/CSV and the MCP re-map; the fields already ride `to_dict()`, and the MCP boundary still needs its explicit copy (its `metadata` set assertion remains untouched here).
- Plans 19-08/19-09 refresh the same snapshot and goldens; the rationale is append-style and must not be replaced.
- The `_MAX_FETCH_K` ceiling keeps large `--offset` requests bounded; Phase 20 filters compose with dedup because filtering sits in the same pre-slice position as `min_score`.
- No dependency, schema, or indexing changes; the corpus fingerprint remains untouched.

---

*Phase: 19-search-correctness*
*Completed: 2026-11-15*

## Self-Check: PASSED

- All 13 key files exist on disk (5 source + 8 test/fixture).
- Commits are ancestors of HEAD: `918bc64`, `3946b3f`, `a899370`, `6ef3602`, `3c3b235`, `657ff29` all found.
- Evaluation scope resolved for plan `19-06` (plan-subject scope) with all 6 commits.
- Ledger measurement: `commits: 6`, `plan_head_before: 6ea1400`, `plan_head_after: 657ff29`.
- Plan-level verification re-run green: 539 targeted tests; full suite 1989 passed, 1 skipped at 95.30% coverage; ruff/format/ty clean; dependency guard 0 files.
- Acceptance criteria re-checked: one row per document on vector/hybrid defaults; best-distance chunk identity + `chunk_matches`; 5-chunk document yields 10 distinct docs at `limit=10`; escalation capped at 2048 with no escalation on a satisfying first batch; `to_dict()` carries all three fields; both fuse sites use `fuse_key_for`; RRF scores byte-identical; regenerated goldens/snapshot documented.
