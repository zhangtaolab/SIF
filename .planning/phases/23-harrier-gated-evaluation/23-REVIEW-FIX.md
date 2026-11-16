---
phase: 23-harrier-gated-evaluation
fixed_at: 2026-11-16T15:18:51Z
review_path: .planning/phases/23-harrier-gated-evaluation/23-REVIEW.md
iteration: 1
findings_in_scope: 8
fixed: 8
skipped: 0
status: all_fixed
---

# Phase 23: Code Review Fix Report

**Fixed at:** 2026-11-16T15:18:51Z
**Source review:** `.planning/phases/23-harrier-gated-evaluation/23-REVIEW.md`
**Iteration:** 1

**Summary:**
- Findings in scope (2 critical + 6 warning): 8
- Fixed: 8
- Skipped: 0
- Additional project-requested cleanup: IN-03 (ruff-clean `scripts/harrier_eval.py`), not counted in the scoped total

## Fixed Issues

### CR-01: Cleanup guard accepts the home directory as a scratch root

**Files modified:** `scripts/harrier_eval.py`, `tests/unit/scripts/test_harrier_eval.py`
**Commit:** 7d7d60a
**Status:** fixed
**Applied fix:** `assert_within_scratch` now resolves both sides and rejects a scratch *root* equal to `/` or the home directory before any target check, so a nested candidate such as `~/qwen3.db` or `~/saved-runs/qwen3.json` can never pass. `run_stage_machine` resolves and validates the root before its first `mkdir`. Tests cover a nested target under a home root, a `/` root, a symlinked home root, `cleanup_arms` with a home root, and the stage-machine entry point.

### CR-02: Verdict stage can return a stale artifact after a full run

**Files modified:** `scripts/harrier_eval.py`, `tests/unit/scripts/test_harrier_eval.py`
**Commit:** 282fb3d
**Status:** fixed: requires human verification (state-machine logic)
**Applied fix:** An existing artifact is returned only when its `artifact` stage marker records the same query-set and corpus fingerprints as the current inputs, the artifact envelope itself agrees, and the current paired saved runs (when still present) hash the same. A stale marker is dropped before recomputation. The insufficient-evidence path no longer marks `verdict`/`artifact` complete; it records the result in `state["adequacy"]` only, so a later adequate resume runs the full flow. Regression tests cover the recorded-artifact fast path, a stale marker with missing inputs, a changed query set, and an inadequate→adequate rerun that reaches the verdict.

### WR-01: Non-idempotent `collection add` breaks resume and scope changes

**Files modified:** `scripts/harrier_eval.py`, `tests/unit/scripts/test_harrier_eval.py`
**Commit:** c207b86
**Status:** fixed: requires human verification (resume-state logic)
**Applied fix:** A changed scope key now clears the run-owned arm DBs before indexing. `_run_index_commands` reads the arm DB's collections, skips an existing `phase23-*` collection with the same resolved root, and removes/re-adds one that points at a different root. Tests now use a DB-backed command fake: a changed `--corpus` set rebuilds against the new root, a partially failed index stage resumes without a duplicate collection, and a stale collection path is replaced.

### WR-02: Resume scope key ignores corpus content changes

**Files modified:** `scripts/harrier_eval.py`, `tests/unit/scripts/test_harrier_eval.py`
**Commit:** c92177d
**Status:** fixed: requires human verification (resume-state logic)
**Applied fix:** The `arm_a_index` marker now persists the corpus fingerprint and document count. On resume, the runbook runs the cheap `index update` and recomputes the fingerprint; when either value differs, the arm-A index marker and every downstream marker (adequacy, both arms' embed/probe/eval, pair identity, verdict, artifact) are dropped, along with the stored adequacy result. A test edits a document under the same root and asserts the downstream markers are invalidated.

### WR-03: Docs "Held-out leg" table mixes all-split and held-out gate values

**Files modified:** `docs/benchmarking.md`
**Commit:** 57c055a
**Status:** fixed
**Applied fix:** The leg table now reports the committed `gates.leg_splits[*].heldout` values — title n=26 (`0.844285 → 0.866380`, +0.022095, CI `[-0.010072, +0.065790]`, floor 0.038462) and body n=30 (`0.766928 → 0.765382`, -0.001545, CI `[-0.067319, +0.061951]`, floor 0.033333) — so the Ns agree with the adjacent leg × language rows. A note states the all-split `gates.legs` values are diagnostic.

### WR-04: Artifact writer cannot reproduce the committed artifact; a rerun drops `default_flip`

**Files modified:** `scripts/harrier_eval.py`, `tests/unit/scripts/test_harrier_eval.py`
**Commit:** cb60e67
**Status:** fixed
**Applied fix:** `build_artifact` accepts an optional `default_flip` block (key-order test updated). Every committed write goes through `write_committed_artifact`: a same-decision, same-corpus-fingerprint rewrite preserves the existing `default_flip` (including `zero_delta_proof`); a different decision or corpus fingerprint is refused unless the new `--force` flag is passed. The committed `bench/harrier-verdict.json` was not modified.

### WR-05: Inherited SIF fusion settings change the measured pipeline and are not recorded

**Files modified:** `scripts/harrier_eval.py`, `tests/unit/scripts/test_harrier_eval.py`
**Commit:** e472feb
**Status:** fixed
**Applied fix:** `SIF_RRF_K`, `SIF_BM25_WEIGHT`, `SIF_VECTOR_WEIGHT`, and `SIF_RERANK_CANDIDATE_LIMIT` are pinned to the shipped defaults in every arm env, included in the env summary's pinned map, and emitted in the artifact `environment.ranking`. A test asserts the pinned table equals the live `Settings` field defaults, so drift fails the suite.

### WR-06: Malformed comparison/payload JSON escapes as a traceback

**Files modified:** `scripts/harrier_eval.py`, `tests/unit/scripts/test_harrier_eval.py`
**Commit:** a1dcd9f
**Status:** fixed
**Applied fix:** `_gates_from_comparison` shape-checks `overall`/`gate`, `splits`, `legs`, `leg_splits`, the optional split maps, `groups`, `suppressed`, and `top_k`, raising `RuntimeError("malformed comparison payload: ...")`. `_run_eval_stage` rejects a non-object stdout payload and a non-string `run_path`. `main` now also maps `AttributeError`/`KeyError`/`TypeError` to the named `FAIL` line. Tests cover `{}`, a missing leg map, a non-object payload, and the `main` handler.

### IN-03 (additional, project-requested): `scripts/harrier_eval.py` was not ruff-clean

**Files modified:** `scripts/harrier_eval.py`, `tests/unit/scripts/test_harrier_eval.py`
**Commit:** 4f782c7
**Status:** fixed
**Applied fix:** `ruff format` applied. `verify_arm_identity` was split into shared/Harrier/Qwen3 helpers (removing `C901`/`PLR0912`), the per-package version lookup was extracted (removing `PERF203`), the unused `BLE001` noqa was removed, and narrow justified `# noqa` directives were added for intentional CLI prints (`T201`), explicit stage-context argument lists (`PLR0913`), and the fingerprint guard chain (`C901`/`PLR0911`). `ruff check scripts` and `ruff format --check scripts` now pass for all scripts.

## Verification

Verification ran in the **main checkout** (branch `dev`), not an isolated worktree: `workflow.use_worktrees` is `false` in `.planning/config.json`, so this run edited and committed in place.

- `env -u FORCE_COLOR NO_COLOR=1 pytest` (PATH pytest): **3004 passed, 1 skipped**, coverage 95.13% (gate 90%).
- `ruff check src tests scripts`: passed.
- `ruff format --check src tests scripts`: passed.
- `ty check src/sif`: passed.
- Protected evidence: `git diff 09f7b52..HEAD -- .planning/phases/23-harrier-gated-evaluation/bench/harrier-verdict.json` is empty; `decision: keep-qwen3`, `default_flip`, and `default_flip.zero_delta_proof` are byte-identical to the committed artifact.
- No default embedder setting or generated doc changed: `src/sif/config/settings.py`, `src/sif/models/embedding.py`, `docs/cli-reference.md`, and `docs/configuration.md` are untouched.

## Skipped Issues

None — all in-scope findings were fixed. The Info findings other than IN-03 remain in `23-REVIEW.md` (outside `fix_scope: critical_warning`).

---

_Fixed: 2026-11-16T15:18:51Z_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_
