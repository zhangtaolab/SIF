---
phase: 16-bench-expansion-reranker-tuning
plan: "04"
subsystem: search
tags: [benchmark, sweep, tie-group, rerank, candidate-limit, click, pytest]

# Dependency graph
requires:
  - phase: 16-bench-expansion-reranker-tuning (Plan 01)
    provides: BenchReport/CATEGORIES/CategoryMetrics grouping, _build_options/_measure_state seams, _settings_mock helper
  - phase: 16-bench-expansion-reranker-tuning (Plan 02)
    provides: resolve_candidate_limit shared clamp (5..50) and the rerank_* settings fields
  - phase: 16-bench-expansion-reranker-tuning (Plan 03)
    provides: committed 150-doc pack + 56 graded queries (36 tuning / 20 held-out), tests/support/bench.py
  - phase: 16-bench-expansion-reranker-tuning (Plan 06)
    provides: live pipeline over-fetch (max(limit+offset, candidate_limit)) and relative threshold the bench rerank states exercise
provides:
  - Sweep engine in sif.search.benchmark — GRID_RRF_K/GRID_WEIGHTS/EPSILON, frozen ConfigResult (four-category breakdown + optional rerank states), SweepRanking, iter_grid (45 declared configs in grid order), rank_sweep (strict < 0.01 on the 6-decimal-rounded delta, grid-order tie-break, ValueError on empty)
  - sif bench --sweep — tuning-only ranking (T-16-06), settings baseline row with exact-zero deltas, per-config ndcg/hit/p50/p95 deltas, table with four per-category nDCG@10 columns and a tie marker, JSON configs/tie_group/winner_declared/baseline/epsilon
  - sif bench --rerank — off/on as two measured states; strictly additive states key on the no-sweep --json (every pinned flat key stays top-level); per-config states in sweep mode; fail-soft on missing backend/model load, ClickException on factory ValueError
  - CachedEmbedder — one embed per distinct query text per bench invocation, shared by baseline and sweep (D-07)
  - bench's typed -C (IntRange 1..200, default None) resolving through Plan 02's shared clamp
affects: [16-05 held-out snapshot, future bench/tuning consumers]

# Actuals (#2632) — same estimateTokens scale (chars/4 over the realized diff).
actuals:
  tokens: 16998
  tasks: 3
  commits: 4
plan_head_before: 71b833f0cf27eacba91de6348924988b35380233
plan_head_after: e6baa38cd92931ad6dc9c989ea36d3208d62b325

# Tech tracking
tech-stack:
  added: []  # stdlib only: dataclasses, json, time; click/rich already present
  patterns:
    - "BenchHarness bundling (db, embedder, dim) keeps measurement helpers under the arg-count limit without noqa (Phase 12 house pattern)"
    - "Rounded-delta tie arithmetic in ONE place (rank_sweep) shared by implementation and tests — a representation-noise delta is pinned by repr() in the test"
    - "Baseline-measurement reuse: the settings config's measured ConfigResult is reused for its grid slot, so baseline deltas are exactly zero including latency"
    - "Strictly-additive JSON evolution: new dimensions (states) ride alongside pinned flat keys; a mocked-report pin omits states rather than leaking MagicMock values"

key-files:
  created:
    - tests/unit/search/test_sweep.py
  modified:
    - src/sif/search/benchmark.py
    - src/sif/cli/commands/bench.py
    - tests/unit/cli/test_bench.py
    - docs/cli-reference.md

key-decisions:
  - "Tuning-only by construction: _tuning_evaluator filters split == 'tuning' out of the fixture BEFORE any search call (T-16-06); an empty tuning set (legacy relevant_docids or all-heldout fixtures) raises a ClickException naming the missing split instead of reporting an empty sweep as success"
  - "Tie rule = round(best - ndcg_at_10, 6) < EPSILON, strict: exactly 0.01 is signal (pinned with the 0.29-vs-0.28 raw-0.009999999999999953 case), 0.0099 is noise; ranking is ndcg descending with declared grid order as tie-break so repeated runs are identical"
  - "The settings run is measured FIRST through the same report() path and its ConfigResult is REUSED for the matching grid slot — the baseline row's deltas are exactly zero (research Pitfall 7) and one measurement is saved"
  - "Rerank states are strictly additive: no-sweep --json keeps every pinned flat key top-level mirroring the off state with states added alongside; sweep rows carry states only when --rerank measured the on pipeline (off-only rows carry none — their flat fields ARE the off state); without --rerank create_reranker is never called (zero-cost by construction)"
  - "bench -C is typed click.IntRange(1, 200) with default None and resolves through Plan 02's resolve_candidate_limit — -C 200 puts 50 into SearchOptions, an omitted -C resolves SIF_RERANK_CANDIDATE_LIMIT, and no string ever reaches the dataclass"
  - "No-sweep D-09 reading: the no-sweep run IS the current-settings baseline (16-01's fix — its flat metrics are the settings' metrics), so the explicit baseline row with deltas is rendered on the SWEEP report where deltas are meaningful"

patterns-established:
  - "Pattern: honesty invariants are dataclass fields (winner_declared, epsilon on SweepRanking), not rendering conventions — the JSON cannot lie about a tie"
  - "Pattern: _state_metrics guards numeric-ness so mocked-report pins stay green while real reports always emit states"

requirements-completed: [EVAL-03, QUAL-05]

coverage:
  - id: D1
    description: "Sweep engine: 45-config declared grid (rrf_k x bm25_weight x vector_weight, shipped baseline included) enumerated deterministically; rank_sweep applies the strict < 0.01 tie rule on the 6-decimal-rounded delta with grid-order tie-break and refuses empty input"
    requirement: EVAL-03
    verification:
      - kind: unit
        ref: "tests/unit/search/test_sweep.py#TestIterGrid/TestRankSweep/TestRankSweepTieBoundary"
        status: pass
    human_judgment: false
  - id: D2
    description: "sif bench --sweep end-to-end: tuning-split-only ranking (held-out sentinel never searched), every config row and the baseline carrying the four-category breakdown, table with per-category nDCG@10 columns and tie honesty, JSON configs/tie_group/winner_declared"
    requirement: EVAL-03
    verification:
      - kind: unit
        ref: "tests/unit/cli/test_bench.py#test_bench_sweep_json_shape/test_bench_sweep_table_renders_tie_honesty/test_bench_sweep_never_searches_heldout_queries"
      - kind: unit
        ref: "tests/unit/cli/test_bench.py#TestBenchSweepDiscipline (narrow-width strict parse, legacy/all-heldout split guard)"
        status: pass
    human_judgment: false
  - id: D3
    description: "Embedding reuse (one inner embed per distinct query across all 45 configs), settings baseline row with exact-zero deltas plus per-config ndcg/hit/p50/p95 deltas, typed -C resolving through the shared clamp (-C 200 -> 50, omitted -> SIF_RERANK_CANDIDATE_LIMIT)"
    requirement: QUAL-05
    verification:
      - kind: unit
        ref: "tests/unit/cli/test_bench.py#TestCachedEmbedder/test_bench_sweep_embeds_each_query_once/test_bench_sweep_json_baseline_and_deltas/TestBenchCandidateLimit"
        status: pass
    human_judgment: false
  - id: D4
    description: "Rerank off/on as two measured states: strictly additive states key on no-sweep --json with every pinned flat key preserved (16-01/16-03 tests byte-unmodified and green), per-config states in sweep mode, spy-reranker proof on the real index (top_k=limit, candidates <= rerank_candidate_limit), fail-soft degradation, ValueError -> ClickException"
    requirement: QUAL-05
    verification:
      - kind: unit
        ref: "tests/unit/cli/test_bench.py#TestBenchRerankStates (6 tests)"
        status: pass
    human_judgment: false
  - id: D5
    description: "Regenerated CLI reference matching the new --sweep/--rerank flags and the typed settings-resolving -C"
    verification:
      - kind: other
        ref: "command: make docs-generate && git diff --exit-code docs/cli-reference.md docs/configuration.md (clean after commit)"
        status: pass
    human_judgment: false

# Metrics
duration: 27 min
completed: 2026-11-08
status: complete
---

# Phase 16 Plan 04: Sweep Engine + Rerank States Summary

**45-config declared-grid sweep with the rounded-delta 0.01 tie rule (tuning-only, embedding-once, settings baseline with exact-zero deltas) plus bench rerank off/on states strictly additive to the pinned flat --json contract**

## Performance

- **Duration:** 27 min
- **Started:** 2026-11-08T14:54:56Z
- **Completed:** 2026-11-08T15:22:29Z
- **Tasks:** 3 (Task 1 tracer verified end-to-end then expanded; Task 2 TDD RED -> GREEN, REFACTOR not needed)
- **Files modified:** 5 (1 created, 4 modified)

## Accomplishments

- `sif.search.benchmark` sweep engine: `GRID_RRF_K`/`GRID_WEIGHTS`/`EPSILON` constants, frozen `ConfigResult` (four-category `CategoryMetrics` mapping + optional rerank `states`), `SweepRanking`, `iter_grid()` (45 configs in declared order — the tie-break order), and `rank_sweep()` — sorting by nDCG@10 descending with grid-order tie-break, tie group = strict `round(best - ndcg, 6) < 0.01`, `winner_declared` False for any multi-config group, `ValueError` on empty input
- `sif bench --sweep`: `_tuning_evaluator` filters to `split == "tuning"` before any search (held-out sentinel proven never searched) and raises a `ClickException` naming the missing split for legacy/all-heldout fixtures; one hoisted pipeline, per-config `SearchOptions` via `replace()` on the Plan 01 `_build_options` baseline; settings run measured first and REUSED for its grid slot so baseline deltas are exactly zero; table with baseline row, ΔnDCG/ΔHit columns, four per-category nDCG@10 columns per row, and tie-marker; JSON `configs`/`tie_group`/`winner_declared`/`epsilon`/`baseline` with per-row deltas
- `CachedEmbedder` (Embedder protocol): memoized `embed` per distinct text, `embed_batch` through the cache, `dimension` forwarded — one wrapper per bench invocation shared by baseline and sweep, collapsing 90 embeds/query (45 configs × 2 passes) to 1
- bench's `-C` typed `click.IntRange(1, 200)` with `default=None`, resolving through Plan 02's shared `resolve_candidate_limit` (same int guard and 5..50 bound as `sif search query` — one resolver, two callers)
- `sif bench --rerank`: `_load_reranker` never calls `create_reranker` without the flag (off-only runs provably construct no model); `ImportError`/model-load failure degrade to off-only with a yellow warning (embedder fail-soft parity) while a factory `ValueError` stays a `ClickException`; no-sweep `--json` keeps every pinned flat key top-level with `states.off` (and `states.on` under `--rerank`) added alongside; sweep mode measures the on state per config through a second hoisted rerank pipeline
- Real-index spy-reranker proof on the committed pack: `top_k == limit`, candidate count within `1..rerank_candidate_limit` on every call, both states present with metrics and latency

## Task Commits

Each task was committed atomically:

1. **Task 1: sweep engine + `sif bench --sweep` end-to-end (tracer)** - `55776e1` (feat; tracer verify re-run passed under auto mode -> expanded without checkpoint)
2. **Task 2 RED: failing split-guard/embed-once/baseline-delta/candidate-limit tests + zero-behavior CachedEmbedder skeleton** - `23c4a92` (test; 8 failing on planned-behavior assertions, pinning-green boundary/heldout-spy tests documented in the message)
3. **Task 2 GREEN: cached embedder, tuning guard, settings baseline deltas, typed -C** - `2c2e4fc` (feat; REFACTOR skipped — no cleanup needed beyond GREEN, so no third commit)
4. **Task 3: rerank off/on states + regenerated CLI reference** - `e6baa38` (feat; includes docs/cli-reference.md)

**Plan metadata:** see the docs(16-04) close-out commit (SUMMARY + STATE + ROADMAP + REQUIREMENTS)

## Files Created/Modified

- `src/sif/search/benchmark.py` - grid constants, ConfigResult (categories + optional states), SweepRanking, iter_grid, rank_sweep
- `src/sif/cli/commands/bench.py` - BenchHarness, CachedEmbedder, _load_reranker, _tuning_evaluator (split guard), _measure_config/_run_sweep (baseline reuse, rerank pipeline), _sweep_payload/_config_row (deltas), _render_sweep/_report_table/_rerank_states/_state_metrics, typed -C, --sweep/--rerank flags
- `tests/unit/search/test_sweep.py` - new: 15 tests (grid enumeration/order/baseline membership, ranking, tie boundary incl. representation noise, to_dict shape)
- `tests/unit/cli/test_bench.py` - +26 tests across TestCachedEmbedder/TestBenchSweepDiscipline/TestBenchCandidateLimit/TestBenchRerankStates plus the Task 1 sweep shape/table tests; `_graded_split_fixture`, `_CountingEmbedder`, `_SpyPipeline`, `_SpyReranker` helpers
- `docs/cli-reference.md` - regenerated: --sweep/--rerank rows, typed -C, extended bench docstring (generator-owned; clean diff proven after commit)

## Decisions Made

- Sweep rows in off-only runs carry no `states` key (their flat fields ARE the off state); `states` rides a row only when `--rerank` measured the on pipeline — the plan's strict-additivity truth is honored on the no-sweep output where the pinned contract lives
- The no-sweep report does not duplicate a zero-delta baseline row: 16-01 already made the no-sweep run the current-settings configuration, so its flat metrics ARE the baseline; the explicit baseline row with deltas is rendered on the sweep report (Task 2's action scopes it there)
- `_state_metrics` returns None for non-numeric report fields so the pinned narrow-width test (mocked `to_dict`) stays byte-unmodified and green — states are omitted there instead of leaking MagicMock values into JSON
- Task 2's `_settings_mock` rerank-field extension was already satisfied by 16-03 (fields enumerated, every `get_settings` patch in the file already used the helper) — verified, no churn needed
- `_render_report`/`bench_cmd` complexity splits (`_report_table`, `_load_reranker`) follow the no-noqa house culture the plan's Pitfall 9 anticipated

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

- ruff C901/PLR0912 tripped on `_render_report` (states + comparison rows) and `bench_cmd` (reranker gate) during Task 3 — resolved by extracting `_rerank_states`/`_report_table`/`_load_reranker` (split-helpers pattern), no noqa added
- Rich wraps the sweep table footer at terminal width, so the tie-honesty table assertion uses wrap-safe fragments ("Tie group of 45 configurations", "no single winner")
- ty flagged `manager._model` as `Embedder | None` against `CachedEmbedder(inner: Embedder)` — guarded with an explicit `inner_embedder is not None` check

## Authentication Gates

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- 16-05 (held-out snapshot) consumes the instrument directly: the sweep ranks tuning-only (proven by spy), ordering is deterministic, every config row plus the baseline carries the four-category breakdown, and `iter_grid`/`rank_sweep` are pure so snapshot drift can only come from code
- EVAL-03 flips complete only when 16-05's SUMMARY exists (shared-ID gate held it — 16-05 also declares EVAL-03)
- The rerank states give 16-05's evidence table both off/on columns; `docs/benchmarking.md` (16-05) can cite the p95-off target from the states output

## Verification Results

- `env -u FORCE_COLOR NO_COLOR=1 python -m pytest tests/unit/search/test_sweep.py tests/unit/cli/test_bench.py -x --no-cov` — 46 passed
- `env -u FORCE_COLOR NO_COLOR=1 python -m pytest` (full suite) — 1481 passed, 1 skipped, coverage 94.92% (fail_under=90 gate green)
- `make docs-generate && git diff --exit-code docs/cli-reference.md docs/configuration.md` — clean after commit
- `ruff check src tests && ruff format --check src tests` — clean
- `ty check src/sif` — 0 diagnostics
- Pinned-test check: `git diff` from the plan base touches only imports, new helpers, and appended tests in `tests/unit/cli/test_bench.py` — `test_bench_json_output`, `test_bench_json_parses_at_narrow_width`, `test_cli_bench_committed_pack_nonzero_ndcg` byte-unmodified and green

## TDD Gate Compliance

Task 2 (`tdd="true"`) produced `test(16-04)` (`23c4a92`) before `feat(16-04)` (`2c2e4fc`). RED: 8 tests failing on planned-behavior assertions (KeyError 'baseline'; 90 embeds vs 1; wrong split-guard message; candidate_limit 200 vs 50 and 20 vs 33) with a zero-behavior `CachedEmbedder` skeleton so the suite collects; the tie-boundary/heldout-spy tests were pinning-green at RED because Task 1 landed that behavior (noted in the RED commit message). GREEN passed the full Task 2 verify; REFACTOR was not needed (no separate commit).

## Self-Check: PASSED

All five created/modified key files exist on disk; all four task commits (55776e1, 23c4a92, 2c2e4fc, e6baa38) are ancestors of HEAD; commit count measured from the plan ledger (base 71b833f) is 4, matching the Task Commits section.

---
*Phase: 16-bench-expansion-reranker-tuning*
*Completed: 2026-11-08*
