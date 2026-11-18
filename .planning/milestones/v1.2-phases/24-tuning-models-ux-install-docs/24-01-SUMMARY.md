---
phase: 24-tuning-models-ux-install-docs
plan: 01
subsystem: search-tuning
tags: [chunking, sweep, held-out-gate, runbook, quality]
requires:
  - "Phase 18 personal-bench instrument (noise_gate/GateResult, corpus_fingerprint, load_saved_run)"
  - "Phase 23 harrier-eval runbook helpers (scope key, atomic JSON, cost capture, scratch guards)"
provides:
  - "src/sif/search/tuning_verdict.py: six-arm grid plus tuning-select/held-out-confirm decision core"
  - "scripts/chunk_sweep.py: resumable isolated-arm sweep runbook with per-arm identity gate and artifact guard"
affects:
  - "Plan 24-06 (real chunk-sweep evidence run and committed verdict)"
  - "docs/benchmarking.md chunk-sweep section (plan 24-06)"
tech-stack:
  added: []
  patterns:
    - "Pure policy module over Phase 18 gate values (embedder_verdict.py precedent)"
    - "Scope-keyed resumable stage machine with argv-only subprocesses"
    - "Aggregate-only committed artifact with decision/fingerprint overwrite guard"
key-files:
  created:
    - src/sif/search/tuning_verdict.py
    - scripts/chunk_sweep.py
    - tests/unit/search/test_tuning_verdict.py
    - tests/unit/scripts/test_chunk_sweep.py
  modified: []
decisions:
  - "Selection rule is tuning-select then held-out-confirm; only a strict held-out winner of a non-baseline candidate adopts."
  - "Every arm pins modelscope Qwen/Qwen3-Embedding-0.6B, dim 1024, SIF_MAX_TOKENS=512; only chunk_size/overlap vary."
  - "A baseline saved run is usable only when its corpus fingerprint matches and its model_type/model_name equal the pinned modelscope Qwen3 pair; rejection reasons are path-free."
  - "The artifact refuses a differing decision or corpus fingerprint without --force; insufficient evidence exits 3 and still writes a countable artifact."
metrics:
  duration: "~15 min"
  completed: "2026-11-17"
  tasks: 2
  files: 4
status: complete
actuals:
  tokens: 20711
  tasks: 2
  commits: 2
commits: 2
plan_head_before: 77c86b864e3ee4d7cfb7c4479f688c4d9ee495f4
plan_head_after: 139b0e37946e036c71b3936db9f6163890690e55
---

# Phase 24 Plan 01: Pure Tuning Verdict + Chunk Sweep Runbook Summary

Pure six-arm chunk-size/overlap sweep policy plus a resumable, identity-gated,
held-out-confirmed runbook that records aggregate evidence and refuses to
publish a default without the Phase 18 warrant.

## What Was Built

- **`src/sif/search/tuning_verdict.py`** — a pure policy module with no Click,
  Rich, embedding, or database imports. Defines `ChunkArm`, the fixed six-arm
  `SWEEP_GRID` (`512/128`, `512/64`, `512/0`, `448/112`, `384/96`, `256/64`),
  `TuningDecision`, `select_tuning_candidate`, and `decide_chunk_default`.
  Adoption requires a strict held-out winner; every other path returns
  `keep-default` or `insufficient-evidence` with named reasons.
- **`scripts/chunk_sweep.py`** — a stdlib-only-at-import runbook. `--dry-run`
  prints the full ordered index/embed/identity/eval plan for all six arms
  without a subprocess. The real run:
  - builds one isolated file-backed DB per arm under a guarded scratch root;
  - pins modelscope Qwen3/1024/512 and varies only `SIF_CHUNK_SIZE`/
    `SIF_CHUNK_OVERLAP`, removing API/base/prompt/model-path/breadcrumb keys;
  - runs each stage as an argv-list subprocess under the arm env;
  - asserts each arm's persisted identity
    (`modelscope:Qwen/Qwen3-Embedding-0.6B`, dim 1024, verified, no prompts)
    after embed and before eval;
  - rejects a baseline saved run with a different corpus fingerprint or
    model identity, regenerating a fresh baseline on the same backend;
  - captures documents/chunks/vectors, embed wall time, and cache deltas;
  - writes an aggregate-only artifact in grid order with
    `min_heldout_for_epsilon_win=101` and the N=56 limitation, refusing a
    differing decision/fingerprint without `--force`.
- **Tests** — 60 unit cases across the two files: gate boundaries (N=100 tie,
  N=101 win, CI-includes-zero), tuning tie-breaks, insufficient/malformed
  paths, grid/env/stage-plan assertions, no-subprocess dry run, scope-key
  resume invalidation, failing-stage recording, identity mismatches, baseline
  rejection categories, artifact schema/privacy, insufficient exit 3, and the
  overwrite guard.

## Verification

- `env -u FORCE_COLOR NO_COLOR=1 pytest tests/unit/search/test_tuning_verdict.py tests/unit/scripts/test_chunk_sweep.py -x --no-cov` — 60 passed.
- `python scripts/chunk_sweep.py --dry-run --json` — six arms, fixed
  modelscope Qwen3/512 contract, ordered stages, expected identity, selection
  rule; no subprocess.
- `ty check src/sif/search/tuning_verdict.py` — passed.
- `ruff check src tests` and `ruff format --check src tests` — passed.
- Full `env -u FORCE_COLOR NO_COLOR=1 pytest` — 3064 passed, 1 skipped,
  coverage 95.13% (gate 90%).

## Deviations from Plan

None - plan executed exactly as written.

## Threat Flags

None. The implementation mitigates the plan's registered threats (T-24-01
scratch/artifact tampering, T-24-05 artifact disclosure, T-24-13 identity
substitution); no new security-relevant surface was introduced. No package
was installed (T-24-SC).

## Known Stubs

None. The real six-arm evidence run and its committed artifact remain plan
24-06 scope by design; this plan deliberately commits machinery only.

## Self-Check: PASSED
