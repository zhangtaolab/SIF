---
phase: 19-search-correctness
plan: 08
subsystem: search
tags: [title-fts, fts5, schema-migration, bm25, column-weights, triggers, vocab-shadow, corr-04]

# Dependency graph
requires:
  - phase: 19-search-correctness
    provides: "19-07 B1 baseline plus the per-chunk result contract; 19-02 detection-gated migration discipline and the index_meta table"
provides:
  - "SchemaManager._fts_column_names() column-list gate parsing sqlite_master DDL"
  - "two-column documents_fts(content, title, content='documents', content_rowid='rowid', tokenize='porter')"
  - "document triggers carrying (rowid, content, title) with old.title on delete/update"
  - "detection-gated drop-vocab -> drop-FTS -> recreate -> single ('rebuild') -> recreate-vocab sequence (duplicate INSERT ... SELECT seed removed)"
  - "parameter-bound bm25(documents_fts, ?, ?) in both SQL branches with pre-pagination min_score against the weighted expression"
  - "SearchOptions.title_weight internal measurement override (None = _TITLE_WEIGHT 1.0)"
  - "post-title-column SC1 golden and held-out snapshot rationale with the H1-duplication caveat"
  - "frontmatter-only title edit proven title-matchable through the title column while chunks survive"
affects: [19-09 (measures and pins the title weight against B1), 20 (title-aware lexical leg), 22 (MCP-only schema init), 24 (QUAL-03 title-breadcrumb duplication)]

# Actuals (#2632) — chars/4 over the realized non-planning diff (same scale as the plan estimate)
actuals:
  tokens: 13972
  tasks: 3
  commits: 3

commits: 3
plan_head_before: 5498d3be1f0128e421bc7e7d722ab4b7edccdbce
plan_head_after: a0695a1a5585914ced9437f7c245b6cd79775eea

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "FTS5 column-list detection parses the stored sqlite_master DDL; CREATE VIRTUAL TABLE IF NOT EXISTS can never add a column"
    - "One FTS5 'rebuild' command is the whole external-content population; a same-gated INSERT ... SELECT seed is a duplicate-index bug both integrity checks miss"
    - "The vocab shadow is dropped before the FTS table and recreated after the rebuild, eliminating the stale-terms window"
    - "bm25() weights and the min_score threshold are bound parameters; the FTS table name in bm25() is a literal, never an alias"
    - "A ranking-shifting schema change regenerates goldens with an appended (never replaced) rationale so prior evidence survives"

key-files:
  created:
    - tests/unit/database/test_schema_title_fts.py
  modified:
    - src/sif/database/schema.py
    - src/sif/search/bm25.py
    - src/sif/core/models.py
    - tests/unit/database/test_schema.py
    - tests/unit/search/test_bm25.py
    - tests/unit/search/test_hybrid.py
    - tests/unit/search/test_bench_snapshot.py
    - tests/fixtures/bench/heldout_defaults.json
    - tests/integration/test_incremental_equivalence.py

key-decisions:
  - "FTS5 'rebuild' is the only documents-side population statement; the old INSERT ... SELECT seed was removed because it ran under the same gate and indexed every document twice while PRAGMA integrity_check and the FTS integrity-check both still report OK."
  - "The migration drops documents_fts_v before documents_fts and recreates it after the rebuild; the three document triggers are dropped explicitly because CREATE TRIGGER IF NOT EXISTS cannot replace one-column bodies."
  - "Both BM25 branches use a MATERIALIZED weighted-match CTE and apply min_score to m.score in the outer WHERE before LIMIT/OFFSET; the threshold is the same weighted expression, so a raised title weight moves ordering and filtering together."
  - "bm25(documents_fts, ?, ?) names the real table even inside the CTE; weights are module constants (_CONTENT_WEIGHT/_TITLE_WEIGHT = 1.0/1.0) bound as parameters, never interpolated."
  - "SearchOptions.title_weight is an internal measurement-only override (None resolves to _TITLE_WEIGHT): no setting, no CLI flag, per D-11; Plan 19-09 pins the accepted value back into the constant."
  - "At 1.0/1.0 the weighted expression reproduces the rank column exactly; the SC1 golden's two BM25-bearing rows moved (title terms now weight at 1.0) while ordering and RRF scores did not."
  - "The held-out snapshot metrics did not move under the title column, so only the rationale was appended; it names the title-column effect and the observed H1 duplication (all 150 fixture docs) as a Phase 24 QUAL-03 concern."
  - "No lexical CJK title win is claimed or tested: FTS5 porter treats contiguous CJK runs as single tokens, and the title-FTS claim stays scoped to tokenized EN-style titles."

patterns-established:
  - "Schema migrations detect from stored DDL and pay one sqlite_master read on fresh/already-migrated databases; the rebuild path is the only DDL churn."
  - "Single-population contracts are asserted structurally (source contains exactly one population statement, no seed) because FTS5 coalesces identical same-rowid postings and run-time counts can mask duplicates."

requirements-completed: [CORR-04]

# Coverage metadata (#1602)
coverage:
  - id: D1
    description: "A populated legacy single-column documents_fts is detected, rebuilt two-column, and a title-only MATCH flips from zero to one, with vocab/DYM survival, title/delete trigger sync, NULL titles, and an idempotent second create_all"
    requirement: CORR-04
    verification:
      - kind: unit
        ref: "tests/unit/database/test_schema_title_fts.py#TestTitleFtsMigration (7 tests: rebuild, vocab/DYM, triggers, title update, delete/NULL, counts, detection-only second pass, source order)"
        status: pass
      - kind: unit
        ref: "tests/unit/database/test_schema.py#test_fresh_schema_creates_two_column_documents_fts"
        status: pass
    human_judgment: false
  - id: D2
    description: "The documents index is populated exactly once: one FTS5 'rebuild' statement, no INSERT ... SELECT seed, fts row count equals documents count, a unique token matches one row, and a deleted document is not MATCHable"
    requirement: CORR-04
    verification:
      - kind: unit
        ref: "tests/unit/database/test_schema_title_fts.py#test_single_population_row_counts_and_match_cardinality + test_population_is_structurally_single_and_seed_free"
        status: pass
    human_judgment: false
  - id: D3
    description: "BM25 binds bm25(documents_fts, content_weight, title_weight) in both branches; 1.0/1.0 reproduces rank exactly; SearchOptions.title_weight overrides the constant for measurement; a raised weight reorders title-only above body-only; min_score thresholds the weighted expression before pagination; search_chunks is untouched"
    requirement: CORR-04
    verification:
      - kind: unit
        ref: "tests/unit/search/test_bm25.py#TestWeightedBM25 (5 tests) + TestBM25OffsetPagination + test_search_chunks_returns_tuples"
        status: pass
    human_judgment: false
  - id: D4
    description: "Title-column goldens are regenerated with rationale: the SC1 snapshot and docstring record the moved BM25 scores, the held-out snapshot reproduces exactly with its appended title-column rationale and H1 caveat, and a frontmatter-only CLI title edit moves the title column while chunks survive"
    requirement: CORR-04
    verification:
      - kind: unit
        ref: "tests/unit/search/test_hybrid.py#TestHybridSC1PipelineGolden (default and explicit-weight snapshots)"
        status: pass
      - kind: unit
        ref: "tests/unit/search/test_bench_snapshot.py#TestHeldoutSnapshotReproduction + TestSweepWinnerEvidence"
        status: pass
      - kind: integration
        ref: "tests/integration/test_incremental_equivalence.py#test_frontmatter_only_cycle_preserves_chunks_and_moves_title"
        status: pass
    human_judgment: false

duration: 7min
completed: 2026-11-15
status: complete
---

# Phase 19 Plan 08: Title-FTS Migration, Triggers, and Weighted BM25 Summary

**A detection-gated rebuild turns every single-column `documents_fts` into a two-column `(content, title)` index populated by exactly one FTS5 `rebuild`, with title-carrying triggers, a surviving vocab shadow, and parameter-bound BM25 column weights that are byte-identical at 1.0/1.0**

## Performance

- **Duration:** 7 min
- **Started:** 2026-11-15T04:21:36Z
- **Completed:** 2026-11-15T04:28:49Z
- **Tasks:** 3/3
- **Files modified:** 10 (3 source, 6 tests, 1 fixture)

## Accomplishments

- `SchemaManager._fts_column_names()` parses the stored `USING fts5(...)` clause and gates the title rebuild: an existing one-column index is dropped and recreated two-column, while a fresh database gets the two-column DDL directly and a migrated one pays only detection reads.
- The migration follows the verified PITFALLS/Pattern-5 sequence: `documents_fts_v` is dropped before `documents_fts`, the three document triggers are dropped explicitly, the two-column table is recreated, one `INSERT INTO documents_fts(documents_fts) VALUES('rebuild')` populates it, and only then are the vocab shadow and triggers recreated. The duplicate `INSERT ... SELECT` seed is gone; the previous `legacy_delete_docs` rebuild is folded into the same single statement.
- The three document triggers now carry `(rowid, content, title)` and pass `old.title` on the external-content `'delete'` command; chunks FTS and its three triggers are byte-identical.
- `BM25Searcher` binds `bm25(documents_fts, ?, ?)` in both the scoped and unfiltered branches, applies the `min_score` threshold to the same weighted expression before `LIMIT/OFFSET`, and keeps `search_chunks` on the plain rank expression. At 1.0/1.0 the weighted score reproduces the `rank` column exactly.
- `SearchOptions.title_weight` (None = module constant) exists solely for the Plan-09 measurement sweep; D-11's "no setting, no CLI flag" posture holds.
- The new populated-DB suite proves title-only MATCH flipping 0→1, title stems and DYM surviving, title-only UPDATE/DELETE synchronization, NULL-title safety, `PRAGMA integrity_check`/FTS `integrity-check` clean, second-run detection-only cost, and single population both structurally and at run time.
- The SC1 hybrid golden moved exactly its two BM25-bearing scores (d3 `0.9999989753435158`→`0.9999986250018905`, d1 `0.9999990673325406`→`0.9999986865688892`); ordering and RRF/vector scores are unchanged. The held-out snapshot reprocessed through the deterministic index with identical metrics, and its rationale was extended (not replaced) with the title-column effect and the observed H1-duplication caveat.
- The frontmatter-only CLI cycle now proves the CORR-04 end-to-end contract: the old title leaves the title column, the new title matches through it, the unchanged body still matches, and the chunk set survives.

## Task Commits

Each task was committed atomically:

1. **Task 1: Title-FTS detect-and-rebuild migration on a populated database (tracer)** - `6987065` (feat)
2. **Task 2: Weighted bm25() with bound column weights and internal title-weight override** - `665900b` (feat)
3. **Task 3: Regenerate title-column goldens and prove a frontmatter-only title edit becomes searchable** - `a0695a1` (test)

**Plan metadata:** committed after this SUMMARY (docs: complete plan)

_Note: Task 1 ran as a tracer; the feedback gate re-ran its `<verify>` end-to-end green before expansion._

## Files Created/Modified

- `src/sif/database/schema.py` - `_fts_column_names()` gate, two-column DDL, title-carrying document triggers, vocab-drop/rebuild/vocab-recreate sequence with a single `('rebuild')` population
- `src/sif/search/bm25.py` - `_CONTENT_WEIGHT`/`_TITLE_WEIGHT`, bound weighted `bm25()` in both branches, weighted pre-pagination `min_score`
- `src/sif/core/models.py` - `SearchOptions.title_weight` internal measurement override
- `tests/unit/database/test_schema_title_fts.py` - new populated-legacy-DB migration suite (10 tests)
- `tests/unit/database/test_schema.py` - fresh two-column DDL assertion
- `tests/unit/search/test_bm25.py` - `TestWeightedBM25`, weighted param positions, two-column real FTS helper
- `tests/unit/search/test_hybrid.py` - post-title-column SC1 snapshot and provenance docstring
- `tests/unit/search/test_bench_snapshot.py` - title-column provenance paragraph
- `tests/fixtures/bench/heldout_defaults.json` - appended title-column rationale (numbers unchanged, prior dedup note preserved)
- `tests/integration/test_incremental_equivalence.py` - title-column-only match probes across the frontmatter-only CLI cycle

## Decisions Made

- One `('rebuild')` is the sole documents-side population; the seed was removed because FTS5 coalesces identical same-rowid postings and both integrity checks pass under duplicates, so only a structural assertion reliably prevents the double index.
- The vocab shadow is dropped before the FTS table, not merely recreated after it; this removes the dangling-vocab stale-terms window that a drop-parent leaves behind.
- Both BM25 branches share the same MATERIALIZED weighted-match CTE shape so the `min_score` predicate can reference `m.score` (the weighted expression) in the outer WHERE while staying before `LIMIT/OFFSET`; the FTS table name stays literal because `bm25()` rejects aliases.
- At 1.0/1.0 the weighted expression is exactly `rank`, so this plan's default ranking change is limited to title terms becoming matchable; the 2-4x title-forward posture remains Plan 19-09's measurement decision.
- The held-out snapshot needed no numeric regeneration: the deterministic fixture metrics are unchanged, and the rationale records that fact plus the H1-duplication caveat rather than inventing movement.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None. The H1-duplication caveat from research Pitfall 16 was observed on all 150 fixture documents (every title equals its H1), but it did not reorder the held-out top-10; that finding is recorded in the snapshot rationale and remains Phase 24 QUAL-03 scope.

## User Setup Required

None - no external service configuration required.

## Verification Results

- Task 1 `<verify>`: `pytest tests/unit/database/test_schema_title_fts.py tests/unit/database/test_schema.py tests/unit/search/test_suggest.py -x --no-cov` -> 70 passed (tracer gate re-ran it green)
- Task 2 `<verify>`: `pytest tests/unit/search/test_bm25.py -x --no-cov` -> 35 passed
- Task 3 `<verify>`: `pytest tests/unit/search/test_hybrid.py tests/unit/search/test_bench_snapshot.py tests/unit/search/test_bm25.py tests/unit/cli/test_search.py tests/integration/test_incremental_equivalence.py -x --no-cov` -> 283 passed
- Plan-level: `pytest tests/unit/database tests/unit/search tests/unit/cli/test_search.py -q --no-cov` -> 813 passed
- Plan-level schema probe: fresh `documents_fts` columns `['content', 'title']` and DDL stable across a second `create_all`; migrated populated DB columns `['content', 'title']` with `count(documents_fts) == count(documents)`; `_create_fts_tables` contains exactly one documents `('rebuild')` and no `INSERT ... SELECT` seed
- Held-out recomputation: defaults nDCG@10 `0.8120158986791898`, Hit@10 `0.85`, per-category identical; candidate nDCG@10 `0.8186413102772627`, Hit@10 `0.85`, delta `0.00662541159807295`, verdict `unchanged`
- Full suite (CLAUDE.md gate): `env -u FORCE_COLOR NO_COLOR=1 pytest` -> 2023 passed, 1 skipped, coverage 95.28% (fail_under=90)
- `ruff check src tests` -> All checks passed; `ruff format --check src tests` -> 198 files already formatted; `ty check src/sif` -> All checks passed
- Dependency guard: no `pyproject.toml`/`uv.lock` change in this plan (0 files)

## Next Phase Readiness

- CORR-04's schema and ranking plumbing are in place: existing databases migrate on the next `create_all` (CLI/MCP/watch hosts), title terms are matchable, and the default 1.0/1.0 weighted SQL is byte-identical to the old ranking except for the title column itself.
- `SearchOptions.title_weight` gives Plan 19-09 a repeatable harness for the 2-4x band sweep; the accepted value is pinned back as `_TITLE_WEIGHT`, still with no setting or CLI flag.
- The title-column goldens and eligibility evidence are committed, so 19-09 can compare against B1 and regenerate the final-weight snapshot with its own rationale.
- No dependency, public-flag, or settings changes; chunks FTS, `search_chunks`, and the MCP boundary are untouched by this plan.
- Not in this plan and still owned downstream: the `mtime` index and MCP-only schema init (19-09 Task 1), and the final title-weight verdict.

---

*Phase: 19-search-correctness*
*Completed: 2026-11-15*

## Self-Check: PASSED

- Key files exist on disk: `tests/unit/database/test_schema_title_fts.py` found; all 10 diff files present.
- Commits are ancestors of HEAD: `6987065`, `665900b`, `a0695a1` all found.
- Evaluation scope resolved for plan `19-08` (plan-subjects) with all 3 task commits.
- Acceptance criteria re-checked: legacy DB rebuilt with title MATCH 0→1; single population structural + runtime; vocab/DYM survive; triggers carry title; NULL/integrity clean; second create_all detection-only; both BM25 branches bound; 1.0/1.0 equals rank; title_weight override reorders; min_score before pagination; goldens regenerated with rationale; frontmatter-only title edit proven through the title column.
- Plan-level verification re-run green: 813 targeted tests; full suite 2023 passed, 1 skipped at 95.28% coverage; ruff/format/ty clean.
