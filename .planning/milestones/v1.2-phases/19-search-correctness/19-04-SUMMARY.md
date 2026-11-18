---
phase: 19-search-correctness
plan: 04
subsystem: search
tags: [enrichment, single-owner, cli, mcp, entry-points, baseline, personal-bench, corr-05]

# Dependency graph
requires:
  - phase: 19-search-correctness
    provides: "19-03 enrich_results helper and pipeline-exit single ownership; 19-01 post-CORR-01 checksum convention that the saved-run corpus fingerprint hashes"
provides:
  - "B0 saved baseline run at .planning/phases/19-search-correctness/bench/b0.json (BM25-only, 100 queries, top_k 10, fingerprint 8c006123784348d1)"
  - "one enrich_results call at each direct CLI search/vsearch exit"
  - "one enrich_results call on the MCP BM25 fallback path; the pipeline path is untouched"
affects: [19-05, 19-07, 19-09 (B0 baseline consumers), 22 (MCP pipeline parity)]

# Actuals (#2632) — chars/4 over the realized diff (same scale as the plan estimate)
actuals:
  tokens: 18748
  tasks: 2
  commits: 2

commits: 2
plan_head_before: 2aec7955a69ce8e051ec9323a7fd3b788239d91e
plan_head_after: 2dedc37bbc114dc626cc251a66965cf26b12e6be

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Direct searcher entry points own exactly one enrich_results call; SearchPipeline remains the single owner on its own path"
    - "MCP boundary enrichment runs before the explicit field re-map so derived fields ride the metadata dict"

key-files:
  created:
    - .planning/phases/19-search-correctness/bench/b0.json
  modified:
    - src/sif/cli/commands/search.py
    - src/sif/mcp/backend.py
    - tests/unit/cli/test_search.py
    - tests/unit/mcp/test_backend.py

key-decisions:
  - "B0 was recorded on a clean scratch index (SIF_DB_PATH=.planning/tmp/phase19/bench.db, SIF_CACHE_DIR=.planning/tmp/phase19/cache) over the committed 150-document fixture corpus: 100 accepted queries (50 title + 50 body), top_k 10, fingerprint 8c006123784348d1, mean self-compare delta 0.0."
  - "Saved personal-eval runs recorded before CORR-01 are invalidated for comparison because corpus_fingerprint hashes path + NUL + checksum + NUL + file_size; B0 is the new pre-ranking-change baseline."
  - "CLI enrichment runs inside the existing `with db.connection:` block immediately after the direct searcher returns and before the DYM/history hooks, so every renderer sees the enriched fields."
  - "The MCP boundary enriches only the sqlite-vec-unavailable BM25 fallback; the pipeline path is already enriched by SearchPipeline and must not double-attach."
  - "Enrichment precedes the explicit MCP re-map, so vectors_stale rides the metadata dict; context_description stays CLI-visible only and is not forwarded to MCP clients."
  - "CORR-05 was returned as `unclassified` by the spec-less edge probe (UNCLASSIFIED-FLAGGED); the entry-point edges above are planner-authored acceptance criteria, verified by the spy tests."

patterns-established:
  - "Entry-point ownership is asserted by a spy over the module-level enrich_results: exactly one call per direct path, zero on the pipeline path, with the spy injecting the enriched fields into the rendered output."
  - "Baseline artifacts are recorded only after a convention change and proven self-comparable via --compare before being committed."

requirements-completed: [CORR-05]

# Coverage metadata (#1602)
coverage:
  - id: D1
    description: "B0 baseline saved run recorded on the post-CORR-01 engine over the committed fixture corpus, proven self-comparable with a zero mean delta"
    verification:
      - kind: other
        ref: "SIF_DB_PATH=.planning/tmp/phase19/bench.db SIF_CACHE_DIR=.planning/tmp/phase19/cache python -m sif.cli.main eval --personal --bm25-only -c bench-fixture --compare .planning/phases/19-search-correctness/bench/b0.json --json --no-save -> n=100, mean=0.0"
        status: pass
    human_judgment: false
  - id: D2
    description: "CLI direct search and vsearch each enrich exactly once; JSON output carries vectors_stale and context_description"
    requirement: CORR-05
    verification:
      - kind: unit
        ref: "tests/unit/cli/test_search.py#TestSingleEnrichmentOwner (bm25, vsearch, empty-result tests)"
        status: pass
    human_judgment: false
  - id: D3
    description: "MCP BM25 fallback enriches exactly once before the re-map; the pipeline path adds no boundary enrichment and forwards exactly rank/collection_name/vectors_stale"
    requirement: CORR-05
    verification:
      - kind: unit
        ref: "tests/unit/mcp/test_backend.py#TestSingleEnrichmentOwner (fallback + pipeline tests)"
        status: pass
    human_judgment: false

duration: 6min
completed: 2026-11-15
status: complete
---

# Phase 19 Plan 04: Entry-Point Single Enrichment and B0 Baseline Summary

**Direct CLI search/vsearch and the MCP BM25 fallback each perform exactly one `enrich_results` composition, and B0 is frozen as a self-comparable post-CORR-01 baseline (100 queries, zero mean delta)**

## Performance

- **Duration:** 6 min
- **Started:** 2026-11-15T03:24:47Z
- **Completed:** 2026-11-15T03:31:00Z
- **Tasks:** 2/2
- **Files modified:** 5 (2 source, 2 test, 1 recorded baseline artifact)

## Accomplishments

- `sif search` now calls `enrich_results(db.connection, results)` once immediately after `BM25Searcher.search`, and `sif vsearch` does the same after `VectorSearcher.search` — both before the DYM/history hooks, so table/JSON/CSV/XML output keeps context descriptions and derived staleness markers.
- `SearchBackend.hybrid_search`'s sqlite-vec-unavailable BM25 fallback enriches its core results exactly once before the explicit boundary re-map; the pipeline branch stays enriched only by `SearchPipeline`.
- The MCP re-map still forwards exactly `rank`, `collection_name`, and `vectors_stale`; enriched `vectors_stale` now rides that metadata, while `context_description` remains CLI-visible only.
- B0 was recorded on a clean scratch index over the committed 150-document fixture corpus (`--bm25-only`): 100 accepted known-item queries, `top_k` 10, corpus fingerprint `8c006123784348d1`, and a `--compare` rerun against it reports `n=100`, mean delta `0.0`.
- New spy tests pin the ownership contract: one enrichment per direct CLI path (BM25 and vector), one on the MCP fallback, zero on the MCP pipeline path, and no error for an empty result list.

## Task Commits

Each task was committed atomically:

1. **Task 1: Record B0 baseline on the post-CORR-01 engine** - `43df901` (feat)
2. **Task 2: One enrichment at the direct CLI and MCP-fallback entry points** - `2dedc37` (feat)

**Plan metadata:** committed after this SUMMARY (docs: complete plan)

## Files Created/Modified

- `.planning/phases/19-search-correctness/bench/b0.json` - saved personal-eval baseline run (version 1, BM25-only, 100 query records, top_k 10, fingerprint `8c006123784348d1`)
- `src/sif/cli/commands/search.py` - imports `enrich_results`; one call each in `search_cmd` and `vsearch_cmd`
- `src/sif/mcp/backend.py` - imports `enrich_results`; one call on the BM25 fallback branch before the re-map
- `tests/unit/cli/test_search.py` - `TestSingleEnrichmentOwner`: spy proves exactly-one enrichment for direct BM25/vector searches, JSON carries both enriched fields, empty results stay a valid empty page
- `tests/unit/mcp/test_backend.py` - `TestSingleEnrichmentOwner`: fallback enriches once and forwards `vectors_stale`; pipeline path adds zero boundary enrichment

Scratch runtime artifacts (`.planning/tmp/phase19/bench.db`, `cache/`, `b0.report.json`, `b0.stderr.txt`) remain untracked and uncommitted by design.

## Decisions Made

- B0 is recorded on the isolated scratch index built from `tests/fixtures/bench/corpus` (150 files), not on any personal index, so the baseline is reproducible and safe to commit.
- Pre-CORR-01 saved runs are invalidated for comparison: `corpus_fingerprint` hashes `path\0checksum\0file_size`, and CORR-01 changed the checksum convention, so B0 is the new pre-ranking-change baseline for CORR-02/03/04 measurement.
- CLI enrichment sits inside the existing `with db.connection:` transaction block directly after the searcher return; this is the earliest point every renderer and the D-13 stale hint can see the enriched rows.
- The MCP boundary enriches the fallback only — enriching after `pipeline.search` would double-attach on the pipeline path, which Plan 19-03 established as pipeline-owned.
- `context_description` is deliberately not forwarded in the MCP metadata dict: the boundary has never forwarded it, and it is not part of the Phase 19 MCP contract.

## Deviations from Plan

None - plan executed exactly as written.

Implementation hygiene only: ruff flagged the spy callbacks' unused `conn` argument (renamed `_conn`) and reformatted one test file; both landed inside the Task 2 commit.

## Issues Encountered

None. The B0 saved-run path was announced on stderr as documented (`<cache>/eval/eval-8c0061237843-20261115T032551085876Z.json`) and copied to `bench/b0.json`; the scratch index was rebuilt from the committed corpus so the fingerprint matched on the first comparison try.

## Verification Results

- `env -u FORCE_COLOR NO_COLOR=1 pytest tests/unit/cli/test_search.py tests/unit/mcp/test_backend.py -x --no-cov` -> 207 passed
- `env -u FORCE_COLOR NO_COLOR=1 pytest tests/unit/cli/test_search.py tests/unit/mcp/test_backend.py tests/unit/search -x --no-cov` -> 696 passed
- Full suite (CLAUDE.md gate): `env -u FORCE_COLOR NO_COLOR=1 pytest` -> 1925 passed, 1 skipped, coverage 95.22% (fail_under=90)
- `ruff check src tests` -> All checks passed
- `ruff format --check src tests` -> 195 files already formatted
- `ty check src/sif` -> All checks passed
- B0 self-comparison (`--compare bench/b0.json --json --no-save`) -> `n=100`, mean delta `0.0`
- `test -z "$(git diff --cached --name-only -- .planning/tmp/)"` -> no scratch file staged
- Dependency guard: no `pyproject.toml`/`uv.lock` changes in this plan

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- CORR-05 is closed at every public entry point: pipeline exits (19-03) plus direct CLI `search`/`vsearch` and the MCP BM25 fallback each enrich exactly once.
- B0 (`bench/b0.json`) is the committed pre-ranking-change baseline; Plans 19-05/19-07/19-09 can run `--compare` against it to prove no unintended drift before/after offset, dedup, and title-weight changes.
- Comparisons against saved runs recorded before CORR-01 will be refused by the corpus fingerprint — expected, documented here, and not a regression.
- No dependency, schema, or public-output-shape changes; the MCP metadata field set is unchanged.

---

*Phase: 19-search-correctness*
*Completed: 2026-11-15*

## Self-Check: PASSED

- Key files exist on disk: `bench/b0.json`, `src/sif/cli/commands/search.py`, `src/sif/mcp/backend.py`, `tests/unit/cli/test_search.py`, `tests/unit/mcp/test_backend.py` all found.
- Commits are ancestors of HEAD: `43df901`, `2dedc37` both found.
- `bench/b0.json` is a valid saved run: `version=1`, `top_k=10`, 100 query records, fingerprint `8c006123784348d1`, retrieval `bm25`.
- Evaluation scope resolved for plan `19-04` (commits-only scope) with both task commits.
- Plan-level verification re-run: 696 targeted tests passed; full suite 1925 passed, 1 skipped at 95.22% coverage; ruff/format/ty green; B0 self-compare `n=100`, mean `0.0`; no `.planning/tmp/` content staged.
