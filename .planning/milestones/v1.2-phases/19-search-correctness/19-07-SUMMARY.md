---
phase: 19-search-correctness
plan: 07
subsystem: search
tags: [cli, mcp, per-chunk, chunk-identity, chunk-matches, personal-bench, b1, docs-generate, corr-02]

# Dependency graph
requires:
  - phase: 19-search-correctness
    provides: "19-06 per-document dedup plus the chunk_id/sequence/chunk_matches result contract and SearchOptions.per_chunk; 19-05 CLI/MCP offset surfaces; 19-04 B0 baseline"
provides:
  - "CLI --per-chunk on sif vsearch and sif query only, threaded into SearchOptions"
  - "deduped-title chunk_matches annotation and a per-chunk Chunk column rendering path#sequence"
  - "MCP QueryInput.per_chunk and VecSearchInput.per_chunk (never LexSearchInput), handler schema sync, and backend forwarding into SearchOptions"
  - "the explicit MCP re-map forwards chunk_id/sequence/chunk_matches into result metadata"
  - "regenerated docs/cli-reference.md with --per-chunk on the two chunk-capable commands"
  - "bench/b1.json post-dedup, pre-title saved run (fingerprint 8c006123784348d1) and the CORR-02 BM25 no-drift narrative in docs/benchmarking.md"
affects: [19-08 (title-FTS work measured against B1), 19-09 (weight pin and B1 comparison), 22 (MCP per_chunk parity), 24 (output-format stability)]

# Actuals (#2632) — chars/4 over the realized non-planning diff (same scale as the plan estimate)
actuals:
  tokens: 9080
  tasks: 3
  commits: 3

commits: 3
plan_head_before: cbd513caa49dcd321384f71a56ad3b1fd2ffa831
plan_head_after: 3d098df5a162ac66a2e798e24649c0135ff880fc

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Public surface flags/fields land on chunk-capable surfaces only: --per-chunk/per_chunk on query+vsearch/vec_search, never on document-level search/lex_search"
    - "Deduped rows carry the collapsed count as a constant-markup title annotation; per-chunk identity gets a dedicated Chunk column because the existing tables have no path column"
    - "MCP result fields cross the boundary only through the explicit re-map; a new public field must be added there and asserted by the schema-sync tests"
    - "A saved bench run is a baseline only after a self-compare proves zero mean delta; a no-drift comparison is labeled as such rather than implying the measured path exercised the change"

key-files:
  created:
    - .planning/phases/19-search-correctness/bench/b1.json
  modified:
    - src/sif/cli/commands/search.py
    - src/sif/mcp/protocol.py
    - src/sif/mcp/handlers.py
    - src/sif/mcp/backend.py
    - docs/cli-reference.md
    - docs/benchmarking.md
    - tests/unit/cli/test_search.py
    - tests/unit/cli/test_search_pagination.py
    - tests/unit/mcp/test_backend.py

key-decisions:
  - "The chunk_matches annotation lives in the shared _title_cell, gated on `chunk_matches > 1`; BM25 rows cannot trigger it, so sif search needs no option and no new column."
  - "Per-chunk table identity is a dedicated Chunk column (only in per-chunk mode) showing path#sequence, because no existing search/vsearch/query table has a path column; document-level hybrid rows fall back to the bare path."
  - "MCP chunk identity rides the existing metadata dict rather than new explicit protocol fields, matching the vectors_stale precedent: the boundary copies fields one by one, so the three fields are added to that explicit map and the exact-set tests."
  - "B1 is recorded as an identical-data baseline (same query set, same retrieved ids as B0); the B0->B1 comparison is labeled the BM25 no-drift check because both arms are --bm25-only and never exercise the vector dedup path."
  - "The dedup evidence is cited from the regenerated held-out snapshot (old->new totals and per_category, identical on the one-chunk-per-document fixture) and the SC1 golden's byte-identical scores, never from the BM25 deltas."
  - "No defaults claim is made: dedup is a correctness contract, so the documented verdict stays `unchanged`."

patterns-established:
  - "Schema-sync tests assert the hand-written MCP schema property equals the Pydantic default, so a model/schema drift fails locally rather than hiding the param from tool discovery."
  - "Public-surface wiring is proven end-to-end with mocked searchers/pipelines: the flag reaches SearchOptions, JSON carries the fields, and the table renders the documented display form."

requirements-completed: [CORR-02]

# Coverage metadata (#1602)
coverage:
  - id: D1
    description: "--per-chunk is accepted by sif vsearch/sif query, rejected by sif search, and threaded into SearchOptions"
    requirement: CORR-02
    verification:
      - kind: unit
        ref: "tests/unit/cli/test_search.py#TestPerChunkSurfaces.test_search_command_does_not_accept_per_chunk + test_vsearch_per_chunk_threads_and_counts_chunk_rows + test_query_per_chunk_threads_and_emits_chunk_fields"
        status: pass
    human_judgment: false
  - id: D2
    description: "Default output exposes chunk_matches (JSON + table annotation); per-chunk output exposes chunk_id/sequence in JSON and path#sequence in the table"
    requirement: CORR-02
    verification:
      - kind: unit
        ref: "tests/unit/cli/test_search.py#TestPerChunkSurfaces.test_default_json_rows_carry_chunk_matches + test_default_table_annotates_multi_chunk_matches + test_default_table_omits_annotation_for_single_match + test_per_chunk_table_renders_path_sequence"
        status: pass
    human_judgment: false
  - id: D3
    description: "Per-chunk pages count chunk rows, keep global ranks, and carry chunk ids across a page offset"
    requirement: CORR-02
    verification:
      - kind: unit
        ref: "tests/unit/cli/test_search_pagination.py#TestPerChunkPageContinuity.test_per_chunk_page_continuity"
        status: pass
    human_judgment: false
  - id: D4
    description: "Generated CLI reference documents --per-chunk on the two chunk-capable commands and regenerates clean"
    verification:
      - kind: other
        ref: "make docs-generate && git diff --exit-code docs/ (clean; exactly two new --per-chunk rows in docs/cli-reference.md, docs/configuration.md unchanged)"
        status: pass
    human_judgment: false
  - id: D5
    description: "MCP QueryInput/VecSearchInput accept per_chunk (LexSearchInput does not); the query handler schema lists the model default and forwards it"
    requirement: CORR-02
    verification:
      - kind: unit
        ref: "tests/unit/mcp/test_backend.py#TestPerChunkInputs (3 tests) + TestQueryToolHandlerPerChunk (2 tests)"
        status: pass
    human_judgment: false
  - id: D6
    description: "The MCP re-map copies chunk_id/sequence/chunk_matches and the backend forwards per_chunk into SearchOptions (pipeline and fallback)"
    requirement: CORR-02
    verification:
      - kind: unit
        ref: "tests/unit/mcp/test_backend.py#TestHybridSearchPerChunkForwarding (3 tests) + TestChunkFieldRemap + test_hybrid_search_mocks"
        status: pass
    human_judgment: false
  - id: D7
    description: "bench/b1.json is a valid saved run over the same corpus fingerprint as B0; self-compare and B0 compare both report at least 50 paired queries"
    requirement: CORR-02
    verification:
      - kind: other
        ref: "eval --personal --bm25-only -c bench-fixture --compare bench/b1.json --json --no-save -> n=100, mean=0.0; --compare bench/b0.json -> n=100, mean=0.0, 100 unchanged"
        status: pass
    human_judgment: false
  - id: D8
    description: "docs/benchmarking.md records the CORR-02 contract change, the B0/B1 deltas with CIs labeled the BM25 no-drift check, and the regenerated goldens with the held-out/SC1 old->new evidence"
    requirement: CORR-02
    verification: []
    human_judgment: true
    rationale: "Prose deliverable: its correctness is verified by inspection against the captured comparison JSON (n=100, mean 0.0, CI [0.0, 0.0], split/group values) and the held-out snapshot rationale; no test asserts the narrative's wording or labels."

duration: 7min
completed: 2026-11-15
status: complete
---

# Phase 19 Plan 07: CLI/MCP Per-Chunk Surfaces and the B1 Baseline Summary

**`--per-chunk`/`per_chunk` now reach the four chunk-capable CLI/MCP surfaces, `chunk_matches` and `path#sequence` are visible in table/JSON/MCP output, and B1 is recorded with the B0→B1 comparison explicitly labeled the BM25 no-drift check**

## Performance

- **Duration:** 7 min
- **Started:** 2026-11-15T04:08:53Z
- **Completed:** 2026-11-15T04:16:09Z
- **Tasks:** 3/3
- **Files modified:** 10 (6 source/docs, 3 test, 1 recorded baseline)

## Accomplishments

- `sif vsearch` and `sif query` gained `--per-chunk` (`is_flag`), threaded into `SearchOptions.per_chunk`; `sif search` remains document-level and Click rejects the flag with a parse-time error.
- The shared `_title_cell` appends `(N chunk matches)` for deduped rows with `chunk_matches > 1` beside the existing stale-vectors annotation, using constant markup; the title itself still goes through `escape()`.
- Per-chunk table output gained a `Chunk` column rendering `path#sequence` for chunk rows and falling back to the path for document-level hybrid rows; ranks stay global.
- JSON output inherits `chunk_id`/`sequence`/`chunk_matches` through `SearchResult.to_dict()` with no renderer change; CSV/Markdown/XML headers are untouched.
- `QueryInput` and `VecSearchInput` carry `per_chunk: bool = False`; `LexSearchInput` deliberately does not. The `QueryToolHandler.input_schema` lists the property with the same default and `handle` forwards it.
- `SearchBackend.hybrid_search` accepts `per_chunk` and places it on the `SearchOptions` used by both the pipeline and the sqlite-vec-unavailable BM25 fallback.
- The explicit MCP re-map now copies `chunk_id`, `sequence`, and `chunk_matches` into the result metadata dict, so the boundary no longer silently drops them.
- `make docs-generate` adds exactly two `--per-chunk` rows (vsearch/query) and leaves `docs/configuration.md` unchanged.
- B1 was recorded on the same scratch index as B0 (fingerprint `8c006123784348d1`, 150 documents, 100 queries, `top_k=10`) and copied to `bench/b1.json`; its query set and retrieved ids are identical to B0.
- `docs/benchmarking.md` gained a "CORR-02 Per-Document Dedup" section: the contract change, the B0→B1 overall/split/group deltas with bootstrap intervals labeled the BM25 no-drift check, the held-out snapshot old→new totals and `per_category` values, the SC1 golden's byte-identical scores, and the regenerated-goldens rationale.

## Task Commits

Each task was committed atomically:

1. **Task 1: CLI `--per-chunk` and chunk-field rendering** - `2b3bd00` (feat)
2. **Task 2: MCP `per_chunk` + chunk-field forwarding and schema sync** - `6ca42d8` (feat)
3. **Task 3: Record B1 and the CORR-02 before/after narrative** - `3d098df` (test)

**Plan metadata:** committed after this SUMMARY (docs: complete plan)

## Files Created/Modified

- `src/sif/cli/commands/search.py` - `--per-chunk` on vsearch/query; `per_chunk` into `SearchOptions`; `(N chunk matches)` annotation; per-chunk `Chunk` column via `_chunk_cell`
- `src/sif/mcp/protocol.py` - `QueryInput.per_chunk`, `VecSearchInput.per_chunk` (LexSearchInput unchanged)
- `src/sif/mcp/handlers.py` - query schema `per_chunk` property and handler pass-through
- `src/sif/mcp/backend.py` - `hybrid_search(per_chunk=...)` into `SearchOptions`; chunk fields added to the explicit metadata re-map
- `docs/cli-reference.md` - regenerated; two `--per-chunk` rows
- `docs/benchmarking.md` - CORR-02 dedup contract, B0→B1 no-drift evidence, goldens rationale
- `tests/unit/cli/test_search.py` - `TestPerChunkSurfaces` (7 tests: flag scope, JSON fields, table annotation/identity)
- `tests/unit/cli/test_search_pagination.py` - `TestPerChunkPageContinuity` (chunk rows, global ranks, chunk ids across an offset)
- `tests/unit/mcp/test_backend.py` - per-chunk input/schema/forwarding tests; chunk-field re-map assertions; mock results extended with the newly forwarded fields
- `.planning/phases/19-search-correctness/bench/b1.json` - post-dedup, pre-title saved run (100 query records, fingerprint `8c006123784348d1`)

## Decisions Made

- Put the collapsed-count annotation in the shared `_title_cell` and gate it on `chunk_matches > 1`; BM25 rows always carry `0`, so `sif search` needs no option and cannot show the annotation.
- Added a mode-scoped `Chunk` column rather than a new default column: only per-chunk output needs identity, and the existing default table stays byte-identical for consumers.
- Kept MCP chunk identity in the metadata dict (the `vectors_stale` precedent) and updated the exact-metadata-set tests, so the boundary's explicit re-map remains the single place a public field can be dropped.
- Labeled B0→B1 the BM25 no-drift check and cited the held-out snapshot/SC1 golden as the dedup evidence, because both bench arms are `--bm25-only` and never construct the vector leg.
- Recorded B1 only after a self-compare reported `n=100`, mean delta `0.0`, making it a stable baseline for the title work in 19-08/19-09.

## Deviations from Plan

None - plan executed exactly as written.

Implementation hygiene: the MCP test doubles (`test_hybrid_search_mocks`, `_weight_result`) were extended with explicit `chunk_id`/`sequence`/`chunk_matches` attributes because the boundary now reads and forwards them; without concrete values a `MagicMock` attribute would cross the re-map as a mock object. This is test-contract adaptation to the planned field forwarding, not a production deviation. `ruff format` also reformatted the two touched test files.

## Issues Encountered

None. The fresh B1 run reproduced B0's query set and retrieved ids exactly, so the self-comparison and the B0 comparison both pass without any fixture or index work. The fixture corpus has one chunk per document, so the metric-level dedup evidence is necessarily identical pre/post; the narrative states that explicitly and points at the SC1 golden and the chunky-document regression as the behavioral evidence.

## User Setup Required

None - no external service configuration required.

## Verification Results

- Task 1 `<verify>`: `pytest tests/unit/cli/test_search.py tests/unit/cli/test_search_pagination.py -x --no-cov` -> 187 passed
- Task 1 docs gate: `make docs-generate` produced exactly two new `--per-chunk` rows; post-commit `git diff --exit-code docs/cli-reference.md docs/configuration.md` -> clean (exit 0)
- Task 2 `<verify>`: `pytest tests/unit/mcp/test_backend.py -x --no-cov` -> 51 passed
- Task 3 `<verify>`: `--compare bench/b1.json --json --no-save` -> n=100, mean 0.0 (assertions pass); `--compare bench/b0.json --json --no-save` -> n=100, mean 0.0, helped 0/hurt 0/unchanged 100
- Plan-level: `pytest tests/unit/cli tests/unit/mcp tests/unit/search -x --no-cov` -> 1192 passed
- Plan-level: `ruff check src tests` -> All checks passed; `ruff format --check src tests` -> 197 files already formatted; `make docs-generate && git diff --exit-code docs/` -> clean
- Full suite (CLAUDE.md gate): `env -u FORCE_COLOR NO_COLOR=1 pytest` -> 2006 passed, 1 skipped, coverage 95.28% (fail_under=90)
- `ty check src/sif` -> All checks passed
- Dependency guard: no `pyproject.toml`/`uv.lock` change in this plan
- Scratch hygiene: `.planning/tmp/phase19/` reports, DB, and cache remain untracked; only `bench/b1.json` was committed

## Next Phase Readiness

- CORR-02's public surfaces are complete: the escape hatch is reachable on the two CLI and two MCP chunk-capable commands only, and chunk identity/collapsed count are visible in table, JSON, and MCP metadata without boundary drops.
- `bench/b1.json` is the committed post-dedup, pre-title baseline; 19-08's title-FTS schema/column work can measure against it, and 19-09's weight pin can cite its verdict.
- The generated docs remain clean; new flags flow through `make docs-generate` with no hand edits.
- Phase 22 inherits validated `per_chunk` fields on `VecSearchInput` (registration still owned there) and needs no schema gap filled.
- No dependency, schema, or ranking-default changes; the corpus fingerprint remains `8c006123784348d1`.

---
*Phase: 19-search-correctness*
*Completed: 2026-11-15*

## Self-Check: PASSED

- All 10 key files exist on disk (6 source/docs + 3 tests + `bench/b1.json`).
- Commits are ancestors of HEAD: `2b3bd00`, `6ca42d8`, `3d098df` all found.
- Evaluation scope resolved for plan `19-07` (plan-subjects) with all 3 task commits.
- Ledger measurement: `commits: 3`, `plan_head_before: cbd513c`, `plan_head_after: 3d098df`.
- Plan-level verification re-run green: 1192 targeted tests; full suite 2006 passed, 1 skipped at 95.28% coverage; ruff/format/ty clean; generated docs diff clean.
- Acceptance criteria re-checked: `--per-chunk` accepted on vsearch/query and rejected on search; JSON carries `chunk_matches` and per-chunk rows `chunk_id`/`sequence`; the table shows `(N chunk matches)` and `path#sequence`; per-chunk pagination counts chunk rows with global ranks; MCP inputs/schema/re-map are synced with `LexSearchInput` excluded; `b1.json` is valid on fingerprint `8c006123784348d1`; B0/B1 compares both report n=100; the narrative labels B0→B1 as the BM25 no-drift check and cites the held-out/SC1 old→new evidence; no scratch file was committed.
