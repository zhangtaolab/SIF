---
phase: 19-search-correctness
plan: 09
subsystem: search
tags: [title-fts, mcp-startup, schema-migration, mtime-index, personal-bench, noise-gate, d12, corr-04]

# Dependency graph
requires:
  - phase: 19-search-correctness
    provides: "19-08 two-column documents_fts, weighted bm25() and SearchOptions.title_weight; 19-07 B1 saved run; 19-04 scratch bench index; 18-03 per-split noise gate and saved-run comparison"
provides:
  - "idx_documents_mtime index (fresh and migrated databases) for Phase 20's mtime filter"
  - "Database.init_schema(embedding_dim: int | None = None) and SearchBackend startup schema migration with the backend's own dimension"
  - "ComparisonReport.legs and .leg_splits per-leg / per-leg-split GateResults in --compare JSON and text output"
  - "the D-12 title-weight rejection with numbers (2.0/3.0/4.0 all leave the held-out rankings unchanged) and pinned _TITLE_WEIGHT = 1.0"
  - "bench/d12-verdict.json candidate evidence and the accept/reject decision"
  - "D-12 rationale recorded in the held-out snapshot, the SC1 golden docstring, the pinned constant's comment, and docs/benchmarking.md"
affects: [20 (mtime index + leg gates), 22 (MCP-only startup migration), 24 (QUAL-03 title-breadcrumb tuning)]

# Actuals (#2632) — chars/4 over the realized non-planning diff (same scale as the estimate)
actuals:
  tokens: 12020
  tasks: 3
  commits: 3

commits: 3
plan_head_before: 2c8c9077b5a8e83ac33f948dd1a25258d9749d60
plan_head_after: 763753d6af9642a916eed05ba1a3b4ceee26228e

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "A one-shot schema-init host must commit before closing: create_all's FTS rebuild/trigger/vocab statements sit in the implicit transaction, and DDL-only persistence would leave a detected-as-migrated but empty index"
    - "Per-leg and per-leg x split gates are derived exactly like split gates (indices into the same paired series); an absent leg/split pair gets empty series and reports sufficient=false, never a fabricated zero"
    - "D-12 is decided on the held-out per-leg gates; a title leg already at its 1.0 ceiling cannot improve, so a measured rejection is the honest outcome"
    - "The internal weight override is the sweep seam: one literal-mode BM25 pipeline per candidate, SearchOptions.title_weight varied, compare_saved_run grading the exact saved set"

key-files:
  created:
    - .planning/phases/19-search-correctness/bench/d12-verdict.json
  modified:
    - src/sif/database/schema.py
    - src/sif/database/database.py
    - src/sif/mcp/backend.py
    - src/sif/search/personal_bench.py
    - src/sif/cli/commands/eval.py
    - src/sif/search/bm25.py
    - tests/unit/database/test_schema.py
    - tests/unit/mcp/test_backend.py
    - tests/unit/search/test_personal_bench.py
    - tests/unit/cli/test_eval.py
    - tests/unit/search/test_bm25.py
    - tests/unit/search/test_hybrid.py
    - tests/fixtures/bench/heldout_defaults.json
    - tests/unit/search/test_bench_snapshot.py
    - docs/benchmarking.md

key-decisions:
  - "SearchBackend runs Database.init_schema(embedding_dim=self.settings.embedding_dim) before the embedder factory and commits before closing; the commit is required or the FTS rebuild/trigger/vocab statements roll back and a detected-as-migrated index is left empty."
  - "Database.init_schema(embedding_dim=N) never consults get_settings when N is supplied, so an injected-settings backend initializes at its own width; the no-argument form is unchanged and the existing dimension-mismatch RuntimeError still fires."
  - "The D-12 sweep migrated the Plan-04 scratch index through the shipped init_schema path first and aborts unless the stored documents_fts SQL has a title column; a one-column table would silently ignore the weight."
  - "Candidates 2.0/3.0/4.0 were graded against B1's exact 100-query saved set through compare_saved_run: every candidate produced 0 helped / 0 hurt / all unchanged on both held-out legs (title baseline already 1.0; body mean 0.900634933653854). No candidate met the strict per-leg gate, so D-12 rejected the band and _TITLE_WEIGHT stays 1.0. No edge refinement was needed because no candidate qualified."
  - "At the pinned 1.0 the held-out snapshot and the SC1 hybrid golden are unchanged from Plan 08's title-column values; their rationale/docstring records the D-12 rejection rather than pretending new numbers."
  - "per-leg/leg_splits are additive JSON keys and text tables; warrants_default_change remains splits['heldout'].winner only, and suppressed group names stay on stderr."

patterns-established:
  - "Startup schema migration is tested on a hand-downgraded pre-title DB: construction flips a title-only MATCH 0→1, adds idx_documents_mtime, and a second construction leaves the DDL byte-identical."
  - "D-12 evidence is reproducible from a committed artifact: each candidate row carries the full GateResult (n, means, delta, CI, counts, floor, winner, regression, sufficient)."

requirements-completed: [CORR-04]

# Coverage metadata (#1602)
coverage:
  - id: D1
    description: "idx_documents_mtime exists on fresh and migrated databases; Database.init_schema accepts an embedding_dim override that skips process settings; SearchBackend migrates a pre-title DB once at construction, is idempotent, and still raises the dimension-mismatch RuntimeError"
    requirement: CORR-04
    verification:
      - kind: unit
        ref: "tests/unit/database/test_schema.py#TestSchemaRealSQLiteCoverage.test_mtime_index_is_created_on_fresh_and_migrated_databases + TestDatabaseInitSchemaDimension (2 tests)"
        status: pass
      - kind: unit
        ref: "tests/unit/mcp/test_backend.py#TestSchemaInitializationAtStartup (4 tests: migration, idempotence, settings dimension, mismatch)"
        status: pass
    human_judgment: false
  - id: D2
    description: "ComparisonReport.to_dict() carries legs and leg_splits GateResults; per-leg gates use only their leg's records, leg-split gates partition them exactly once, an absent leg/split reports sufficient=false with no winner, warrants_default_change remains the held-out summary gate, and the CLI renders both tables without disturbing existing output"
    requirement: CORR-04
    verification:
      - kind: unit
        ref: "tests/unit/search/test_personal_bench.py#TestPerLegNoiseGates (4 tests)"
        status: pass
      - kind: unit
        ref: "tests/unit/cli/test_eval.py#TestCompareRendering.test_compare_table_renders_per_leg_and_leg_split_gates + test_compare_json_carries_the_full_comparison_object"
        status: pass
    human_judgment: false
  - id: D3
    description: "The D-12 sweep migrated the scratch index through init_schema, proved the title column, graded 2.0/3.0/4.0 against B1, recorded each candidate's title/body held-out GateResult, rejected the band with numbers, and pinned _TITLE_WEIGHT = 1.0; the hybrid SC1 golden is unchanged and a test pins the constant and its behavior"
    requirement: CORR-04
    verification:
      - kind: other
        ref: "python .planning/tmp/phase19/sweep_title_weight.py -> pre-sweep title guard OK; 3 candidates; decision=rejected pinned=1.0; verdict-shape assertion passes"
        status: pass
      - kind: unit
        ref: "tests/unit/search/test_bm25.py#TestWeightedBM25.test_pinned_title_weight_is_the_measured_d12_value + test_default_title_weight_resolves_to_module_constant"
        status: pass
      - kind: unit
        ref: "tests/unit/search/test_hybrid.py#TestHybridSC1PipelineGolden"
        status: pass
      - kind: unit
        ref: "tests/unit/search/test_bench_snapshot.py#TestHeldoutSnapshotReproduction"
        status: pass
    human_judgment: false
  - id: D4
    description: "docs/benchmarking.md gains a CORR-04 section with the migration narrative, the D-12 candidate table, the strict per-leg verdict, the CJK-scope caveat, the H1-duplication caveat, and the pinned 1.0"
    requirement: CORR-04
    verification: []
    human_judgment: true
    rationale: "Prose deliverable: its correctness is verified by inspection against bench/d12-verdict.json and the sweep log; no test asserts the narrative's wording or the candidate table's presentation."

duration: 9min
completed: 2026-11-15
status: complete
---

# Phase 19 Plan 09: MCP Startup Migration, Per-Leg Gates, and the D-12 Verdict Summary

**MCP-only hosts now migrate the title-FTS schema and the mtime index on startup, `--compare` exposes per-leg and per-leg×split gates, and the measured 2–4× title-weight band is rejected with numbers (pinned `_TITLE_WEIGHT = 1.0`)**

## Performance

- **Duration:** 9 min
- **Started:** 2026-11-15T04:32:57Z
- **Completed:** 2026-11-15T04:42:46Z
- **Tasks:** 3/3
- **Files modified:** 16 (6 source/docs, 9 tests/fixture, 1 verdict artifact)

## Accomplishments

- `SchemaManager._create_indexes` now creates `idx_documents_mtime`, and `Database.init_schema(embedding_dim=N)` resolves an explicit override without touching `get_settings()`; the no-argument form is unchanged.
- `SearchBackend.__init__` opens the database, runs `init_schema(embedding_dim=self.settings.embedding_dim)`, commits, and closes in a `finally` before the embedder factory. A hand-downgraded pre-title database is migrated at construction (title-only MATCH 0→1, triggers carry title, mtime index present), a second construction leaves the DDL byte-identical, and a wrong width still raises the existing `RuntimeError`.
- `ComparisonReport` gained `legs` (every leg present in the saved run) and `leg_splits` (each leg × tuning/heldout); both serialize under additive JSON keys and the CLI renders a per-leg table plus a compact leg × split table. Absent combinations report `sufficient: false` with no winner; `warrants_default_change` remains `splits["heldout"].winner`.
- The D-12 sweep opened the Plan-04 scratch index through `Database(...).init_schema()`, guarded that the stored `documents_fts` SQL contains a `title` column, and graded 2.0/3.0/4.0 against B1's exact 100-query saved set through `compare_saved_run`.
- Every candidate left both held-out legs' rankings unchanged: title (n=23, baseline 1.0, delta 0.0, no winner — already at the ceiling) and body (n=26, baseline and current `0.900634933653854`, delta 0.0, no regression). D-12 rejects the band with numbers and pins `_TITLE_WEIGHT = 1.0`; `bench/d12-verdict.json` records every candidate's `GateResult` fields and the decision.
- At the pinned 1.0 the held-out snapshot and SC1 hybrid golden are unchanged from Plan 08's title-column values; their rationale/docstring now records the D-12 rejection while preserving the dedup and title-column notes. `docs/benchmarking.md` documents the migration, the candidate table, the verdict, the CJK scope, and the H1-duplication caveat.
- No Settings field or CLI flag exposes the title weight; `docs/cli-reference.md` and `docs/configuration.md` regenerate with no diff.

## Task Commits

Each task was committed atomically:

1. **Task 1: mtime index + MCP-only schema initialization** - `b29d70b` (feat)
2. **Task 2: Per-leg and per-leg×split noise gates in the comparison report** - `f3bc9e7` (feat)
3. **Task 3: Title-weight sweep, D-12 verdict, pinned constant, and final goldens/docs** - `763753d` (test)

**Plan metadata:** committed after this SUMMARY (docs: complete plan)

## Files Created/Modified

- `src/sif/database/schema.py` - `idx_documents_mtime` created with `IF NOT EXISTS`
- `src/sif/database/database.py` - `init_schema(embedding_dim: int | None = None)` override; settings-free when supplied
- `src/sif/mcp/backend.py` - one startup `init_schema` + commit using the backend settings dimension
- `src/sif/search/personal_bench.py` - `leg_noise_gates` helper, `ComparisonReport.legs/.leg_splits`, additive `to_dict()` keys
- `src/sif/cli/commands/eval.py` - per-leg and leg × split comparison tables
- `src/sif/search/bm25.py` - constant comment records the D-12 rejection; value stays 1.0
- `src/sif/database/test_schema.py` - mtime index (fresh/migrated) and init-schema dimension tests
- `tests/unit/mcp/test_backend.py` - `TestSchemaInitializationAtStartup` (4 tests on a pre-title DB)
- `tests/unit/search/test_personal_bench.py` - `TestPerLegNoiseGates` (partition, empty split, JSON fields, held-out summary gate)
- `tests/unit/cli/test_eval.py` - per-leg rendering and JSON assertions
- `tests/unit/search/test_bm25.py` - pinned-constant test and updated behavior test docstring
- `tests/unit/search/test_hybrid.py` - SC1 docstring records the D-12 outcome (values unchanged)
- `tests/fixtures/bench/heldout_defaults.json` - appended D-12 verdict to the rationale (numbers unchanged)
- `tests/unit/search/test_bench_snapshot.py` - D-12 provenance paragraph
- `docs/benchmarking.md` - new CORR-04 Title-Aware Ranking section
- `.planning/phases/19-search-correctness/bench/d12-verdict.json` - candidate evidence and the reject decision

## Decisions Made

- The startup migration commits before closing: `create_all`'s FTS `rebuild`, trigger, and vocab statements are DML in the connection's implicit transaction, and a close without commit rolls them back while the DDL-created two-column table persists — a subsequent detection pass would then skip the rebuild and leave an empty index.
- The backend uses its own settings dimension, not the process environment, so injected settings and test/embedder overrides cannot trigger a false mismatch; the mismatch error remains the clear existing `RuntimeError`.
- The D-12 gate reads per-leg held-out gates (title must be a noise-gate winner, body mean delta ≥ −0.01). The title leg's baseline is exactly 1.0, so no weight can improve it; the honest outcome is a recorded rejection, not a claim inside noise.
- No edge refinement (2.5/3.5) was evaluated because no candidate was accepted at all; every candidate's held-out ranks were identical.
- `warrants_default_change` remains only `splits["heldout"].winner`; per-leg and per-leg×split gates are additive diagnostics/decision inputs.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Startup schema migration rolled back on close**
- **Found during:** Task 1 (MCP-only schema initialization)
- **Issue:** `create_all()` leaves the external-content `'rebuild'`, trigger creation, and vocab recreation in the connection's implicit transaction. Closing the one-shot `Database` without a commit rolled those statements back while the DDL-created two-column table remained, leaving a database that every later detection pass considers migrated but whose index is empty.
- **Fix:** `SearchBackend` now commits the connection after `init_schema` and before closing it in the `finally`.
- **Files modified:** `src/sif/mcp/backend.py`
- **Verification:** the pre-title DB test's title-only MATCH flips 0→1 after construction, and a second construction leaves the stored DDL byte-identical (both green).
- **Committed in:** `b29d70b` (Task 1 commit)

---

**Total deviations:** 1 auto-fixed (1 bug). **Impact:** Required for the startup migration to have any effect at all; no scope creep and no behavior change beyond the planned migration.

## Issues Encountered

- The D-12 measurement cannot show a title-leg improvement on this fixture: the known-item title leg's pre-change nDCG@10 is already 1.0 for all 23 held-out queries (exact-title queries retrieve the target at rank 1 through body matching), so the ceiling forbids a positive delta. The weighted BM25 scores do move with the weight, but no held-out rank does. This is recorded as a rejection with numbers (CONTEXT D-12 explicitly allows it), not as a failure; Phase 24 QUAL-03's title-breadcrumb work is the natural place to re-measure on a corpus where the title leg is not saturated.
- The sweep was rerun after the first run and produced byte-identical candidate data, confirming the deterministic grading path.

## User Setup Required

None - no external service configuration required.

## Verification Results

- Task 1 `<verify>`: `pytest tests/unit/database/test_schema.py tests/unit/mcp/test_backend.py -x --no-cov` -> 86 passed
- Task 2 `<verify>`: `pytest tests/unit/search/test_personal_bench.py tests/unit/cli/test_eval.py -x --no-cov` -> 208 passed
- Task 3 `<verify>`: `pytest tests/unit/search/test_bm25.py tests/unit/search/test_bench_snapshot.py tests/unit/search/test_hybrid.py -x --no-cov` -> 101 passed
- Task 3 guard probes: `documents_fts` SQL contains `title`; `d12-verdict.json` has `decision=rejected`, `pinned_title_weight=1.0`, and 3 candidates with truthy `title_heldout` objects -> both pass
- Sweep evidence: scratch index migrated through `init_schema(embedding_dim=1024)`, pre-sweep title guard OK, B1 loaded (100 queries, top_k=10, fingerprint `8c006123784348d1`), candidates 2.0/3.0/4.0: title held-out n=23 baseline/current 1.0 delta 0.0 winner=False; body held-out n=26 baseline/current 0.900634933653854 delta 0.0 regression=False -> D-12 rejected, pinned 1.0
- Broader suites: `pytest tests/unit/search tests/unit/cli tests/unit/mcp tests/unit/database -q --no-cov` -> 1311 passed
- Full suite (CLAUDE.md gate): `env -u FORCE_COLOR NO_COLOR=1 pytest` -> 2036 passed, 1 skipped, coverage 95.26% (fail_under=90)
- `ruff check src tests` -> All checks passed; `ruff format --check src tests` -> 198 files already formatted; `ty check src/sif` -> All checks passed
- Docs gate: `make docs-generate` regenerated both generator-owned docs with no diff; only the hand-written `docs/benchmarking.md` changed
- Public-knob audit: no `title_weight`/`TITLE_WEIGHT` occurrence in `src/sif/cli`, `src/sif/config`, `docs/cli-reference.md`, or `docs/configuration.md`
- Dependency guard: no `pyproject.toml`/`uv.lock` change in this plan
- Scratch hygiene: the sweep driver, scratch DB, and cache under `.planning/tmp/phase19/` remain untracked; only `bench/d12-verdict.json` was committed

## Next Phase Readiness

- CORR-04 is complete: existing databases migrate on any host (CLI, watch, MCP startup), titles are matchable, the mtime index is present for Phase 20, and the title-weight posture is a measured, recorded decision.
- `--compare` now exposes the per-leg D-12 inputs, so later tuning claims can be checked without ad-hoc parsing.
- Phase 20's metadata filters can rely on `idx_documents_mtime` and on the per-leg report shape; Phase 22 inherits a working MCP-only startup migration.
- The title-leg saturation finding and the H1-duplication caveat are recorded for Phase 24 QUAL-03; a future weight change must regenerate the snapshot/goldens and record a new verdict.
- No dependency, public-flag, or settings changes.

---

*Phase: 19-search-correctness*
*Completed: 2026-11-15*

## Self-Check: PASSED

- Key files exist on disk: `bench/d12-verdict.json`, the SUMMARY itself, all 6 source/docs files, and the held-out fixture were found.
- Commits are ancestors of HEAD: `b29d70b`, `f3bc9e7`, `763753d` all found.
- Evaluation scope resolved for plan `19-09` (plan-subjects) with all 3 task commits and no missing/outside/unreachable files.
- Acceptance criteria re-checked: mtime index on fresh/migrated DBs; init_schema override skips settings; MCP construction migrates a pre-title DB, is idempotent, and raises on a dimension mismatch; `legs`/`leg_splits` JSON fields with exact partition and insufficient-empty handling; `warrants_default_change` still the held-out summary gate; the sweep migrated before scoring and aborted on a title-less FTS guard (guard observed OK on the migrated DB); verdict artifact has exactly `decision`/`pinned_title_weight`/`candidates` with 2.0/3.0/4.0 and full `GateResult` deltas/CI/winner/sufficient; D-12 rejected on the title-improvement clause with body held-out flat; `_TITLE_WEIGHT` stays 1.0 and is test-pinned; SC1 golden confirmed unchanged at 1.0 with the D-12 docstring; `heldout_defaults.json` reproduces exactly and its rationale preserves dedup/title notes plus the verdict; docs section covers table/verdict/CJK caveat; no public title-weight knob.
- Plan-level verification re-run green: 1311 targeted tests; full suite 2036 passed, 1 skipped at 95.26% coverage; ruff/format/ty clean; generated docs diff clean; no dependency change.
