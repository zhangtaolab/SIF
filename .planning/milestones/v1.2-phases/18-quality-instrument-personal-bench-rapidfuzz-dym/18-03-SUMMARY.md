---
phase: 18-quality-instrument-personal-bench-rapidfuzz-dym
plan: 03
subsystem: search/evaluation
tags:
  - personal-bench
  - saved-runs
  - paired-bootstrap
  - noise-gate
  - corpus-fingerprint
  - comparison-report
  - replay-stability

requires:
  - phase: 18-quality-instrument-personal-bench-rapidfuzz-dym
    provides: "Plans 01/02: personal_bench synthesis/split/groups/replay domain module, PersonalReport with rank-aligned retrieved arrays, sif eval CLI, deterministic fixture support"
  - phase: 16-bench-expansion-reranker-tuning
    provides: "percentile(), warrants_default_change(), nDCG@10/Hit@10 metric math, 0.01 tie rule"
provides:
  - "versioned saved-run schema (version 1, 5 MB/10k caps) with full envelope+record validation and content-free records"
  - "auto-save under <cache_dir>/eval with --no-save and run_path in JSON"
  - "--compare: exact saved query set in saved order, corpus-fingerprint refusal, id-first target resolution, both arms graded through document id"
  - "seeded paired percentile bootstrap and overall/tuning/held-out/per-group noise gates with 1/N floor and <10 suppression"
  - "replay stability (Jaccard@10 + top-1) against the saved snapshot"
  - "comparison table/JSON rendering and the personal-bench benchmarking narrative"
affects: [23-harrier-gated-evaluation, 24-tuning-models-ux-install-docs]

tech-stack:
  added: []
  patterns:
    - "Saved runs are untrusted input: cap size and record count before decode, type/range/enum-check the envelope before any record, and name the field path on every defect (no KeyError/TypeError escape)"
    - "One PersonalReport contract feeds both the fresh and compare auto-save paths; created_at is stamped inside run_to_saved"
    - "Comparison pairing is structural: exact saved query set/order, fingerprint match, saved top_k for both arms"
    - "Both arms grade through document id (first-occurrence dedupe); saved paths stay inspection values and a unique-match fallback, never grading keys"
    - "Seeded bootstrap (random.Random(0), 10,000 resamples) + benchmark.percentile; gates report N, 1/N, CI, helped/hurt/unchanged"
    - "Only the held-out summary gate can warrant a defaults change; tuning and per-group gates are labeled diagnostic"
    - "Group suppression names small groups on stderr instead of rendering a zero row"

key-files:
  created: []
  modified:
    - src/sif/search/personal_bench.py
    - src/sif/cli/commands/eval.py
    - tests/support/eval.py
    - tests/unit/search/test_personal_bench.py
    - tests/unit/cli/test_eval.py
    - docs/cli-reference.md
    - docs/benchmarking.md

key-decisions:
  - "Saved-run schema v1 carries query/target ids/paths/leg/language/length/split/grade plus rank-aligned retrieved paths and document ids, top_k, corpus fingerprint, model identity, and replay paths — never document content; 5 MB/10k caps are enforced before decode and every defect names its field path."
  - "The saved `retrieved_doc_ids` list is the comparison identity: first-occurrence dedupe makes at most one grade-1 hit, so baseline nDCG@10 cannot exceed 1.0 and a shared path cannot become a hit for one arm only."
  - "--compare evaluates exactly the saved query set in saved order at saved.top_k with no synthesis/overlap filter/split reassignment; a corpus-fingerprint mismatch refuses, targets resolve by id first with a unique-path fallback, and -n/retrieval/model drift is surfaced on stderr (and recorded in the comparison JSON for retrieval)."
  - "A winner requires the seeded 95% CI to exclude zero AND round(mean_delta, 6) >= 0.01; 0.0099 never wins, 1/N and helped/hurt/unchanged are reported, and only the held-out summary gate sets warrants_default_change."
  - "Replay stability reports Jaccard@10 and top-1 against the saved snapshot, or available:false with the reason when a side is missing; it never enters nDCG/Hit/splits/groups."
  - "build_personal_report gained an optional corpus override so ComparisonReport.current_report can carry the saved sample size and the recomputed current fingerprint without a synthetic sampled-document list."

requirements-completed: [EVAL-02]

coverage:
  - id: D1
    description: "Every personal run auto-saves one validated, content-free, versioned JSON under <cache_dir>/eval (or none with --no-save), announced on stderr with run_path in JSON"
    requirement: EVAL-02
    verification:
      - kind: unit
        ref: "tests/unit/search/test_personal_bench.py#TestSavedRunContract"
        status: pass
      - kind: unit
        ref: "tests/unit/search/test_personal_bench.py#test_envelope_defects_raise_value_error_naming_the_field"
        status: pass
      - kind: unit
        ref: "tests/unit/search/test_personal_bench.py#test_record_defects_raise_value_error_naming_the_field"
        status: pass
      - kind: unit
        ref: "tests/unit/cli/test_eval.py#TestSavedRunsCli"
        status: pass
    human_judgment: false
  - id: D2
    description: "--compare evaluates exactly the saved query set in saved order, refuses a corpus-fingerprint mismatch, resolves targets id-first, and grades both arms by document id at the saved depth"
    requirement: EVAL-02
    verification:
      - kind: unit
        ref: "tests/unit/search/test_personal_bench.py#TestCompareSavedRun"
        status: pass
      - kind: unit
        ref: "tests/unit/cli/test_eval.py#TestCompareCli"
        status: pass
    human_judgment: false
  - id: D3
    description: "Paired bootstrap and noise gates: deterministic seeded CI, 0.01 tie rule, 1/N floor, helped/hurt/unchanged, held-out-only default warrant, suppressed groups named, replay stability or honest unavailable"
    requirement: EVAL-02
    verification:
      - kind: unit
        ref: "tests/unit/search/test_personal_bench.py#TestPairedBootstrap"
        status: pass
      - kind: unit
        ref: "tests/unit/search/test_personal_bench.py#TestNoiseGate"
        status: pass
      - kind: unit
        ref: "tests/unit/search/test_personal_bench.py#TestReplayStability"
        status: pass
    human_judgment: false
  - id: D4
    description: "Comparison tables and JSON expose the contract; CLI docs are generator-owned and current; benchmarking.md documents legs, sampling, privacy, pairing, noise gate, and replay"
    requirement: EVAL-02
    verification:
      - kind: unit
        ref: "tests/unit/cli/test_eval.py#TestCompareRendering"
        status: pass
      - kind: integration
        ref: "make docs-generate && git diff --exit-code -- docs/cli-reference.md docs/configuration.md"
        status: pass
      - kind: unit
        ref: "tests/test_docs.py"
        status: pass
    human_judgment: false

duration: 12min
completed: 2026-11-14
status: complete
plan_head_before: 604e3cd8856cf79d5f3a621fdd8b88892836a931
plan_head_after: e7489c83320f8360fcc8293d3f04c961bdc34ecf
actuals:
  tokens: 32888
  tasks: 3
  commits: 3
---

# Phase 18 Plan 03: Personal Bench Saved Runs, `--compare`, and the Paired-Bootstrap Noise Gate Summary

**Personal eval runs now auto-save as validated, content-free version-1 JSON; `--compare` re-evaluates exactly the saved query set over a fingerprint-matched corpus, grades both arms through document id at the saved depth, and refuses to call a winner inside noise via a seeded paired-bootstrap CI plus the 0.01 tie rule.**

## Performance

- **Duration:** 12 min (11m42s measured from plan start to the final task commit; metadata commit follows)
- **Started:** 2026-11-14T15:20:33Z
- **Completed:** 2026-11-14T15:32:15Z
- **Tasks:** 3 completed
- **Files modified:** 7 (0 created, 7 modified)
- **Estimate vs actual:** plan estimated 65,000 tokens; realized diff measured at 32,888 tokens (chars/4 over the `-U0` diff of src/scripts/tests/docs), 3 commits.

## Accomplishments

- Saved-run contract: `SavedRun`/`SavedQueryRecord` version 1 with a fixed key order, `.get`/`isinstance` envelope validation before any record, per-record enum/type checks, bool-as-int and NaN/Infinity rejection, 5 MB/10k caps, and explicit rejection of `content`/`snippet`. `load_saved_run` enforces the size cap before decode and translates every defect to `ValueError` naming the field path; saved paths are never opened. 37 envelope/record defect cases are parametrized and pinned.
- Auto-save: every fresh run writes `<cache_dir>/eval/eval-<fingerprint12>-<UTC>.json` atomically (sibling temp then `replace`), announces the path on stderr only, adds `run_path` to the JSON payload, and `--no-save` opts out. `run_to_saved` builds the run from `PersonalReport` alone and stamps `created_at` inside the writer.
- `--compare`: loads/validates before any search, recomputes the corpus fingerprint from all in-scope metadata and refuses a mismatch naming both values, resolves every target by document id first with a unique-path fallback (ambiguous/missing paths refuse), and evaluates exactly the saved query set in saved order at `saved.top_k` with no synthesis, overlap filtering, or split reassignment. Both arms grade through document id; first-occurrence dedupe keeps baseline nDCG@10 ≤ 1.0 and a duplicated path cannot become a one-arm hit. `-n`, retrieval-mode, and model-identity drift are reported on stderr; retrieval modes are carried in the comparison JSON.
- Noise gate: `paired_bootstrap` uses `random.Random(0)` and 10,000 resamples with `benchmark.percentile`, so repeated calls are identical. `noise_gate` computes rounded per-query deltas, helped/hurt/unchanged, N, and 1/N, and declares a winner only when the CI excludes zero AND `round(mean_delta, 6) >= 0.01` (exactly 0.01 wins, 0.0099 does not, a zero-containing CI never wins, negative deltas are regression flags only). Gates exist overall, per split, and per leg × language × length group in declared order; groups below 10 are omitted and named. Only the held-out summary gate sets `warrants_default_change`.
- Replay stability: Jaccard@10 plus top-1 match against the saved replay snapshot, with `available: false` and a reason when either side is missing; replay never enters nDCG/Hit/splits/groups.
- Rendering and docs: a summary table (Overall, Tuning (diagnostic), Held-out), a context table (Noise floor (1/N), Corpus fingerprint match, Replay stability, retrieval modes, saved top_k, suppressed count), and a diagnostic per-group table; suppressed names and replay-unavailable notices go to stderr while stdout stays machine-clean. `docs/cli-reference.md` is regenerated with `--compare`/`--no-save`, and `docs/benchmarking.md` documents the three legs, sampling/split floors, saved-run location/privacy, pairing/fingerprint refusal, bootstrap gate, suppression, replay stability, and comparability rules.

## Task Commits

Each task was committed atomically (normal hooks, no `--no-verify`):

1. **Task 1: Versioned saved-run schema, validation, fingerprint, and auto-save** - `8f6f7ee` (feat)
2. **Task 2: `--compare` pairing, fingerprint refusal, paired bootstrap, and the 0.01 noise gate** - `05669db` (feat)
3. **Task 3: Comparison rendering, CLI docs regen, and the personal-bench narrative** - `e7489c8` (feat)

**Plan metadata:** `docs(18-03): complete personal bench comparison plan` (the commit following this SUMMARY)

## Files Created/Modified

- `src/sif/search/personal_bench.py` - saved-run schema/validation/load/write, `run_to_saved`, `BootstrapResult`/`paired_bootstrap`, `GateResult`/`noise_gate`, `GroupGate`/`group_noise_gates`, `ReplayStability`/`replay_stability`, `require_matching_corpus`, `resolve_saved_targets`, id-keyed baseline grading, `ComparisonReport`/`compare_saved_run`; `build_personal_report` gained an optional corpus override.
- `src/sif/cli/commands/eval.py` - `--compare`/`--no-save`, pre-search saved-run loading/validation, fingerprint/target checks before embedder load, saved-depth options, comparison warnings, one save/render path, and the comparison summary/context/group tables.
- `tests/support/eval.py` - `rewrite_saved_run` mutation helper for malformed/envelope CLI fixtures.
- `tests/unit/search/test_personal_bench.py` - saved-run contract + 58 parametrized defect cases, fingerprint, bootstrap/noise-gate/replay-stability, and compare/pairing/group/suppression tests.
- `tests/unit/cli/test_eval.py` - auto-save/`--no-save`/stderr-path tests, compare pairing/refusal/depth/retrieval/model/empty/groups tests, and rendering/JSON-shape tests.
- `docs/cli-reference.md` - regenerated by the generator: `sif eval` now lists `--compare` and `--no-save`.
- `docs/benchmarking.md` - new Personal Bench section plus reproduction commands.

## Decisions Made

- Saved-run records carry rank-aligned `retrieved` paths and `retrieved_doc_ids`; the ids are the comparison identity, while paths remain inspection values, replay data, and the unique-match resolution fallback.
- Validation is deliberately explicit rather than Pydantic-based so bool-as-int and non-finite floats cannot slip through; the whole envelope is checked before any record is trusted.
- Compare-mode target resolution is duplicated at the CLI boundary (before the embedder loads) and inside `compare_saved_run`, so an incompatible corpus or stale target fails before expensive work and the domain stays safe when called directly.
- `build_personal_report` accepts an optional `CorpusSummary`; this keeps one report-assembly path while letting the compare current report carry `saved.corpus.sampled` and `widened=False`.
- Only the held-out gate is allowed to set `warrants_default_change`; the overall and tuning gates remain visible for diagnosis but cannot move defaults.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Long saved-run paths wrapped across lines on stderr**
- **Found during:** Task 1 (auto-save announcement)
- **Issue:** Rich wraps at the console width, splitting the saved-run path across lines; the announced path is meant to be copyable into `--compare`, and the wrapping also made the stderr contract untestable.
- **Fix:** Announce the path with `soft_wrap=True` so it stays on one line; subsequent comparison warnings reuse the same treatment.
- **Files modified:** `src/sif/cli/commands/eval.py`
- **Verification:** `TestSavedRunsCli::test_saved_path_is_announced_on_stderr_only` asserts the full path appears on stderr and not stdout.
- **Committed in:** `8f6f7ee` (Task 1 commit)

---

**Total deviations:** 1 auto-fixed (Rule 1).
**Impact on plan:** No scope change; the fix makes the saved-run handoff actually usable and the stderr contract testable.

## Issues Encountered

- The first Task 3 rendering test expected the `title/en/long` group; the fixture's `Unique title N` queries are three tokens and correctly land in `medium`. The assertion was corrected to the classifier's actual bucket.
- A unique-path fallback test initially set the saved target and retrieved id to the same stale value, which is a baseline hit by definition; it now uses a different retrieved id so the path fallback is the only thing that can make the current arm score.
- Rich table headers wrap at the 80-column test console; rendering tests assert stable labels and values (not contiguous long header strings).

## User Setup Required

None - no external service configuration required. No package was installed (rapidfuzz was already added by Plan 04).

## Threat Surface Scan

No new security-relevant surface beyond the plan's threat model. Mitigations verified by tests: T-18-07 (5 MB/10k caps, version check, exhaustive envelope/record validation, bool/non-finite rejection, no KeyError/TypeError escape), T-18-08 (paths are opaque, never opened; `content`/`snippet` rejected), T-18-09 (fingerprint recomputed from current metadata and mismatch refuses with both values), T-18-10 (winner needs CI excluding zero and the rounded 0.01 rule; held-out only; diagnostic labels; N/1/N/helped-hurt-unchanged reported), T-18-SC (no dependency install in this plan).

## Next Phase Readiness

- Phase 18 is now 4/4 plans executed: EVAL-01, EVAL-02, and QUAL-01 are complete.
- Phase 19 (search correctness) can cite `--compare` before/after on the personal bench; Phase 23 can use the held-out-only gate as the defaults arbiter; Phase 24 sweeps can record personal-bench deltas.
- Saved runs are local-only under the cache directory and refuse a different corpus; comparisons across a budget/threshold change remain intentionally non-comparable and that is documented.
- No blockers. Final gates: full pytest 1858 passed / 1 skipped at 95.17% coverage (fail_under 90), `ruff check` + `ruff format --check`, `ty check src/sif`, `make docs-generate` diff clean, and `python scripts/generate_bench_fixture.py --check` clean.

## Self-Check: PASSED

- FOUND: src/sif/search/personal_bench.py
- FOUND: src/sif/cli/commands/eval.py
- FOUND: tests/support/eval.py
- FOUND: tests/unit/search/test_personal_bench.py
- FOUND: tests/unit/cli/test_eval.py
- FOUND: docs/cli-reference.md
- FOUND: docs/benchmarking.md
- FOUND: 8f6f7ee (Task 1)
- FOUND: 05669db (Task 2)
- FOUND: e7489c8 (Task 3)

---
*Phase: 18-quality-instrument-personal-bench-rapidfuzz-dym*
*Completed: 2026-11-14*
