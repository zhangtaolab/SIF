---
phase: 23-harrier-gated-evaluation
plan: 03
subsystem: search-eval
tags: [harrier, qwen3, embedder-ab, evaluation-runbook, identity-gate, resumable-stages, adequacy-preflight, verdict-artifact, cleanup-guard]

# Dependency graph
requires:
  - phase: 23-harrier-gated-evaluation
    plan: "01"
    provides: "Per-language held-out gates and HeldoutFloorError with per-language counts"
  - phase: 23-harrier-gated-evaluation
    plan: "02"
    provides: "decide_from_gates/decide_from_payload and MIN_HELDOUT_FOR_EPSILON_WIN"
  - phase: 21-scale-maintenance-embedder-identity
    provides: "EmbedderIdentity/read_identity/check_identity and role-aware prompt table"
  - phase: 18-quality-instrument-personal-bench-rapidfuzz-dym
    provides: "personal-bench synthesis, saved runs, and the paired-bootstrap gates"
provides:
  - "scripts/harrier_eval.py two-arm runbook (dry-run, corpus guard, probe, stage machine)"
  - "Per-arm env pinning with prompt/API/model-path removal"
  - "Identity gate plus pairwise fingerprint/cache-id swap guard"
  - "Scope-keyed resumable stage markers with named timeouts"
  - "EN+ZH adequacy preflight that records insufficient-evidence and exits 3"
  - "Aggregate verdict artifact writer and scratch-only cleanup guard"
affects: [23-04, 23-05, 23-06, 24]

actuals:
  tokens: 23030
  tasks: 3
  commits: 3
  plan_head_before: cd797723902fc4cfcc7b764a170ec0eb2b6a5d3f
  plan_head_after: c1b78929c058580493bdc93b4ac4576599e9df03

tech-stack:
  added: []
  patterns:
    - "Stdlib-only orchestrator: sif imports deferred into probe/identity/preflight helpers; every model/database stage is a -q subprocess under a per-arm env"
    - "Scope-keyed stage machine: sha256(corpus roots + label) invalidates every marker when the corpus changes"
    - "Adequacy is a recorded pre-embed gate, not a skipped stage: only an adequate verdict marks the stage complete"

key-files:
  created:
    - scripts/harrier_eval.py
    - tests/unit/scripts/__init__.py
    - tests/unit/scripts/test_harrier_eval.py
  modified:
    - .gitignore

key-decisions:
  - "Arm env removes SIF_API_BASE/SIF_API_KEY and both prompt keys entirely, so the Qwen3 cache id stays exactly modelscope:Qwen/Qwen3-Embedding-0.6B and the Harrier known-model table supplies web_search_query"
  - "resolve_corpus_roots resolves non-strictly then refuses duplicate or nested roots, because one path in two collections would make saved-target resolution ambiguous"
  - "Run state is keyed to resolved corpus roots plus label; a changed scope discards all markers and re-indexes"
  - "An inadequate preflight is persisted under state['adequacy'] but never marks the adequacy stage complete, so a resumed run re-checks before any embed"
  - "The pairwise identity gate executes at the arm_b_identity stage after arm B's probe, because the Harrier identity is written by its first embedding write"
  - "Insufficient evidence writes the aggregate artifact and exits 3 but keeps the arms; cleanup runs only after a completed verdict"
  - "The artifact maps the comparison payload's 'gate' leaf to the documented 'overall' leaf, since ComparisonReport.to_dict names it gate"

patterns-established:
  - "Dry-run payload is the executable contract: tests pin both arms' argv/env before any model download"
  - "stderr gate fails only on the Embedder identity mismatch guard literal; the expected --compare Model identity differs notice is accepted"
  - "Cleanup resolves every candidate path and refuses /, home, and anything outside the scratch root; .planning/tmp/ is git-ignored"

requirements-completed: [MODEL-01, MODEL-02]

coverage:
  - id: D1
    description: "Dry run builds both arms' exact -q/--index argv and per-arm env with no prompt overrides, and duplicate/nested corpus roots are refused with exit 2"
    requirement: MODEL-01
    verification:
      - kind: unit
        ref: "tests/unit/scripts/test_harrier_eval.py#TestDryRun"
        status: pass
      - kind: unit
        ref: "tests/unit/scripts/test_harrier_eval.py#TestCorpusRootsGuard"
        status: pass
    human_judgment: false
  - id: D2
    description: "Each arm's stored identity and probe check_identity status are gated before eval, with a pairwise fingerprint/cache-id swap guard"
    requirement: MODEL-01
    verification:
      - kind: unit
        ref: "tests/unit/scripts/test_harrier_eval.py#TestIdentityGate"
        status: pass
      - kind: unit
        ref: "tests/unit/scripts/test_harrier_eval.py#TestProbe"
        status: pass
    human_judgment: false
  - id: D3
    description: "Run state is atomic, scope-keyed, resumable, and every stage subprocess is bounded by a named timeout"
    requirement: MODEL-01
    verification:
      - kind: unit
        ref: "tests/unit/scripts/test_harrier_eval.py#TestStageMachine"
        status: pass
    human_judgment: false
  - id: D4
    description: "EN+ZH adequacy runs before the embed budget, records counted shortfalls, and writes an insufficient-evidence artifact with exit 3"
    requirement: MODEL-02
    verification:
      - kind: unit
        ref: "tests/unit/scripts/test_harrier_eval.py#TestPreflight"
        status: pass
      - kind: unit
        ref: "tests/unit/scripts/test_harrier_eval.py#TestArtifact"
        status: pass
    human_judgment: false
  - id: D5
    description: "The aggregate artifact has the documented envelope/order, verbatim gate leaves, basename-only scope labels, and no query text or absolute paths; the query fingerprint ignores per-arm target ids"
    requirement: MODEL-02
    verification:
      - kind: unit
        ref: "tests/unit/scripts/test_harrier_eval.py#TestArtifact"
        status: pass
      - kind: unit
        ref: "tests/unit/scripts/test_harrier_eval.py#TestQueryFingerprint"
        status: pass
    human_judgment: false
  - id: D6
    description: "Cleanup refuses the root/home/outside paths, honors --keep-arms, and removes only the run's own DB files, sidecars, and baseline saved run"
    requirement: MODEL-01
    verification:
      - kind: unit
        ref: "tests/unit/scripts/test_harrier_eval.py#TestCleanupGuard"
        status: pass
    human_judgment: false

duration: 13min
completed: 2026-11-16
status: complete
---

# Phase 23 Plan 03: Two-Arm Evaluation Runbook Summary

**A stdlib-only two-arm runbook now builds both isolated scratch arms, proves each embedder identity before eval, gates EN+ZH adequacy before the embed budget, records cost/provenance, and writes a privacy-safe aggregate verdict artifact with scratch-only cleanup.**

## Performance

- **Duration:** 13 min
- **Started:** 2026-11-16T12:16:23Z
- **Completed:** 2026-11-16T12:29:11Z
- **Tasks:** 3
- **Files modified:** 4 (3 created, 1 modified)

## Accomplishments

- `scripts/harrier_eval.py` (stdlib-only at import time) builds both arms' exact argv/env: every `sif` stage is `-q --index <arm-db>` with `SIF_MODEL_PATH`, `SIF_DB_PATH`, `SIF_API_BASE`, `SIF_API_KEY`, and both prompt keys removed, so Harrier gets `web_search_query` from the known-model table and Qwen3 stays the exact prompt-free baseline.
- `resolve_corpus_roots` resolves non-strictly and refuses duplicates and parent/child pairs before any command is built (`exit 2`, one stderr line); the dry run applies the same guard.
- The identity gate rejects missing/legacy/wrong-model/wrong-dimension identities and Harrier prompt deviations; `verify_arm_pair` rejects identical fingerprints or a shared cache bucket; the probe subprocess loads the arm model, opens the DB read-only with sqlite-vec, and requires `check_identity_status == "ok"`.
- The stage machine is scope-keyed (`sha256(sorted roots + label)[:16]`), atomically persisted, resumable, and bounded by `PROBE_TIMEOUT_SECONDS`/`STAGE_TIMEOUT_SECONDS`; an inadequate adequacy verdict is recorded but never marked complete, so a resumed full run re-checks before embedding.
- `preflight_adequacy` uses Phase 18's language-aware `ensure_heldout`; an inadequate corpus writes an `insufficient-evidence` artifact (null query fingerprint, empty arms/gates, per-language counts) and exits 3.
- `build_artifact` emits the documented key order, verbatim gate leaves, basename-only scope labels, and no query text or absolute paths; `cleanup_arms` refuses `/`, home, and outside paths and deletes only the run's own files.
- `.gitignore` now ignores `.planning/tmp/`, so an ordinary broad `git add` cannot stage arm DBs, saved runs, or run state.

## Task Commits

Each task was committed atomically:

1. **Task 1: Tracer — dry run builds both arms' exact commands and env without a subprocess** - `b2b30d6` (feat)
2. **Task 2: Identity gate, probe mode, and resumable stage machine** - `ece3d50` (feat)
3. **Task 3: Adequacy preflight, cost/provenance capture, artifact writer, and cleanup guard** - `c1b7892` (feat)

**Plan metadata:** pending final docs commit.

## Files Created/Modified

- `scripts/harrier_eval.py` - Two-arm runbook: fixed constants, `ArmSpec`/`ArmCommand`, env/argv builders, dry-run payload, corpus-root guard, identity gate/probe, scope-keyed run state, stage machine, adequacy preflight, cost/environment capture, artifact writer, cleanup guard, argparse `main`.
- `tests/unit/scripts/__init__.py` - Test package marker.
- `tests/unit/scripts/test_harrier_eval.py` - 57 tests across `TestDryRun`, `TestCorpusRootsGuard`, `TestIdentityGate`, `TestProbe`, `TestStageMachine`, `TestPreflight`, `TestDiskHeadroom`, `TestArtifact`, `TestCleanupGuard`, `TestQueryFingerprint`.
- `.gitignore` - `# GSD phase scratch (arm DBs, saved runs, run state)` section ignoring `.planning/tmp/`.

## Decisions Made

- Arm env removes credentials and prompt keys rather than blanking them: `format_cache_model_id` appends `@<api_base>` when set, which would break the exact Qwen3 cache-id assertion, and an empty prompt name disables Harrier's required query prompt.
- Corpus roots are resolved before command construction, and the dry run reuses that guard, so a bad scope can never produce a partial index plan.
- Stage execution places the pairwise identity check (`arm_b_identity`) after `arm_b_probe` (the first point both stored identities exist), while keeping the documented `STAGES` enumeration unchanged.
- The adequacy stage is only complete on `adequate: true`; an inadequate result is itself persisted, making a resume re-run the cheap preflight instead of entering the embed budget.
- Insufficient evidence keeps the arm DBs (cleanup only after a completed verdict) so an operator can curate the scope or rerun without rebuilding.
- The artifact's overall gate reads `comparison["overall"]` when present and falls back to `comparison["gate"]`, because `ComparisonReport.to_dict()` emits `gate`.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Overall gate key mismatch at the verdict stage**
- **Found during:** Task 3 (artifact writer)
- **Issue:** The plan's documented gate-leaf list named `overall`, but `ComparisonReport.to_dict()` emits the overall gate as `gate` (with `warrants_default_change` folded in). Indexing `comparison["overall"]` would raise `KeyError` only at the end of a real multi-hour run, after every stage had succeeded.
- **Fix:** `_gates_from_comparison` now reads `overall` when present and falls back to `gate`, preserving the artifact's documented leaf name while recording the real payload.
- **Files modified:** `scripts/harrier_eval.py`
- **Verification:** `TestArtifact` pins the documented envelope; the full script battery passes.
- **Committed in:** `c1b7892`

---

**Total deviations:** 1 auto-fixed (1 bug)
**Impact on plan:** The fix only affects the artifact mapping at the verdict stage; no scope change and no behavior outside the planned gate data.

## Issues Encountered

- The preflight fixture initially asserted an English body sentence that the overlap budget would reject; the deterministic opening-window/body shape was tuned before pinning the test (bilingual `en=27, zh=25, heldout=52`; English-only `zh=0`).
- Ruff's `PERF401` required list comprehensions in the test fixture builder; no runtime behavior changed.

## Auth Gates

None - the runbook is local-only; the probe/model stages require the existing embed extra but no credentials (API base/key are removed from both arms).

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Plan 23-05 can run the real evidence procedure: `python scripts/harrier_eval.py --corpus <roots> --json`, then commit only `.planning/phases/23-harrier-gated-evaluation/bench/harrier-verdict.json` plus the `docs/benchmarking.md` section. The artifact is intentionally **not** produced by this plan; real-model evidence is manual, not CI.
- Plan 23-04's conditional default flip can read `decision`/`rule` from the artifact; `DECISION_ADOPT` remains the sole authorization and this plan mutates no settings.
- `--keep-arms` preserves both arm DBs for the explicit-Qwen3 zero-delta proof; without it, a completed run auto-cleans the scratch DBs.
- Full suite green at 2981 passed / 1 skipped / 95.13% coverage; `ruff check`, `ruff format --check`, and `ty check src/sif` all pass.

---
*Phase: 23-harrier-gated-evaluation*
*Completed: 2026-11-16*

## Self-Check: PASSED

All three created/modified source files exist; all three task commits are ancestors of HEAD.
