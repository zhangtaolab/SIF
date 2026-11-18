---
phase: quick-261118-ipu
plan: 01
subsystem: embedding
tags: [l2-normalization, embedding-cache, cache-migration, qwen3, cuda, test-determinism]
requires: []
provides:
  - float64 L2 renormalization of usable embedding-cache hits in EmbeddingManager._lookup_cached, so v1.2.0 cache rows no longer trip validate_batch's norm gate
  - one shared sif/embedding/normalize.py:l2_normalize helper serving both the sentence-transformers-backed encode paths and the manager's cache-read path
  - a deterministic CPU/float32 Qwen3 auto-selection test on CUDA hosts via a pinned torch.cuda.is_available probe
affects: [index-embed-path, search-vector-path, embedding-cache, inference-tests]
actuals:
  tokens: 3122
  tasks: 2
  commits: 2
  plan_head_before: 36b315076a8f1c9a41a25f1a091343191ec71a6a
  plan_head_after: ffad91be0d6886f94f4ff1fcdf37fca61d5469a6
tech-stack:
  added: []
  patterns:
    - "Cache reads cross the same float64 L2 boundary as fresh encoder output, from one shared helper module"
    - "Zero and non-finite cached vectors are divided by 1.0 and returned unchanged so the writer's gates stay reachable"
    - "Host-dependent tensor probes are pinned per-test with unittest.mock.patch next to the branch they select"
key-files:
  created:
    - src/sif/embedding/normalize.py
  modified:
    - src/sif/embedding/embedder.py
    - src/sif/embedding/manager.py
    - tests/unit/embedding/test_manager.py
    - tests/unit/inference/test_reranker.py
key-decisions:
  - "Renormalize cache hits on read in float64 instead of invalidating or rewriting the cache DB; storage format and NORM_TOLERANCE = 1e-3 are unchanged"
  - "Normalize only after _is_usable_cached so wrong-dimension and non-finite rows remain misses and are recomputed; zero vectors are not filtered and pass through unchanged"
  - "One public l2_normalize helper in a new module replaces the private embedder-local copy, imported by both the embedders and the manager"
  - "Pin torch.cuda.is_available False in the Qwen3 CPU-load test while keeping the device-less constructor, so the test still exercises auto device/dtype selection on GPU hosts"
requirements-completed: [QUICK-ISSUES-4-FOLLOWUP]
coverage:
  - id: D1
    description: "Off-unit cached vectors (norms 1.003596 and 0.9985) come back unit-length within 1e-12 from EmbeddingManager with no embedder re-encode"
    requirement: QUICK-ISSUES-4-FOLLOWUP
    verification:
      - kind: unit
        ref: "tests/unit/embedding/test_manager.py#TestCacheSafety::test_off_unit_cached_vector_is_renormalized_on_read"
        status: pass
    human_judgment: false
  - id: D2
    description: "Zero cached vectors pass through unchanged for validate_batch's zero-norm gate, while non-finite and wrong-dimension rows remain cache misses"
    requirement: QUICK-ISSUES-4-FOLLOWUP
    verification:
      - kind: unit
        ref: "tests/unit/embedding/test_manager.py#TestCacheSafety::test_zero_cached_vector_passes_through_unchanged"
        status: pass
      - kind: unit
        ref: "tests/unit/embedding/test_manager.py#TestCacheSafety::test_non_finite_and_wrong_length_entries_are_recomputed"
        status: pass
    human_judgment: false
  - id: D3
    description: "Exactly one L2 normalization implementation exists and is idempotent for unit vectors; both embedder encode paths and the manager cache-hit path import it"
    requirement: QUICK-ISSUES-4-FOLLOWUP
    verification:
      - kind: unit
        ref: "tests/unit/embedding/test_embedder_impl.py#TestUnitRenormalization"
        status: pass
      - kind: unit
        ref: "tests/unit/embedding/test_manager.py#TestCacheSafety::test_already_unit_cached_vector_is_unchanged"
        status: pass
      - kind: unit
        ref: "tests/unit/embedding/test_manager.py#TestEmbeddingManager::test_cache_is_segmented_by_model"
        status: pass
    human_judgment: false
  - id: D4
    description: "Qwen3 CPU auto-selection test passes on CUDA hosts while still asserting to('cpu') and torch.float32 from a device-less constructor"
    requirement: QUICK-ISSUES-4-FOLLOWUP
    verification:
      - kind: unit
        ref: "tests/unit/inference/test_reranker.py#TestQwen3Reranker::test_local_load_cpu_quiet_and_already_loaded"
        status: pass
    human_judgment: false
metrics:
  duration: 13min
  completed: 2026-11-18
status: complete
---

# Phase quick-261118-ipu Plan 01: Normalize cached embeddings on read and pin the Qwen3 CUDA probe Summary

**Issue-#4 gap closed: embedding-cache hits are renormalized in float64 from one shared helper so `sif index embed` succeeds on v1.2.0 caches, and the Qwen3 CPU-load test is now deterministic on GPU hosts**

## Performance

- **Duration:** 13min
- **Started:** 2026-11-18T13:32:45Z
- **Completed:** 2026-11-18T13:45:52Z
- **Tasks:** 2
- **Files modified:** 5 (1 created, 2 source, 2 test)

## Accomplishments

- Issue-#4 follow-up: `EmbeddingManager._lookup_cached` now runs every usable cache hit through `l2_normalize(...).tolist()`, so rows written before v1.2.0's embedder-side renormalization (off unit by up to ~3.6e-3) come back unit-length without a re-encode. `sif index embed` no longer aborts on `L2 norm ... is not 1.0 within 0.001` for users with a populated `embeddings_cache.db`; the storage format and `NORM_TOLERANCE = 1e-3` are unchanged.
- Safety preserved in the same boundary: normalization runs only after `_is_usable_cached` (dimension + finiteness), so wrong-dimension and non-finite rows remain misses and are recomputed; zero vectors are not filtered and pass through unchanged as zeros, keeping `StreamingEmbedWriter.validate_batch`'s zero-norm and finiteness gates reachable.
- One implementation: the float64 L2 helper moved verbatim from `embedder.py` (`_l2_normalize`) into `src/sif/embedding/normalize.py` as the public `l2_normalize`; the six call sites in `SentenceTransformerEmbedder`/`ModelScopeEmbedder` and the manager cache-read path all import it. Already unit vectors are idempotent (the exact `[1.0, 0.0]` cache-segmentation assertions still hold byte-stably). `LlamaCppEmbedder`, `OpenAIEmbedder`, and `SimpleEmbedder` are untouched.
- GPU-host determinism: `test_local_load_cpu_quiet_and_already_loaded` pins `torch.cuda.is_available` to False while keeping the device-less constructor, so the test still exercises the constructor's auto device/dtype selection but deterministically asserts `to("cpu")` and `torch.float32`. The test that previously failed on this CUDA host now passes.
- Full quality suite green under `uv run --frozen --extra dev --extra embed`: `ruff check src tests`, `ruff format --check src tests`, and `pytest` → 3250 passed, 1 skipped, 95.08% coverage (the pre-fix baseline was 1 failed / 3233 passed).

## Task Commits

The plan's output spec suggested one atomic commit; the executor protocol commits each task atomically, so the work landed as two task commits:

1. **Task 1: Renormalize cached embeddings on read and share one float64 L2 helper** - `26ac78c` (fix)
2. **Task 2: Pin the CUDA probe in the Qwen3 CPU-load test and run the full quality suite** - `ffad91b` (test)

**Plan metadata:** not committed by this executor (orchestrator handles docs artifacts)

## Files Created/Modified

- `src/sif/embedding/normalize.py` - new shared `l2_normalize(values)` helper (float64, per-vector norms, zero/non-finite divided by 1.0); docstring records the encode-path and cache-hit consumers
- `src/sif/embedding/embedder.py` - private `_l2_normalize` definition removed; imports `sif.embedding.normalize.l2_normalize`; the six encode call sites now call it
- `src/sif/embedding/manager.py` - imports the shared helper; `_lookup_cached` assigns `l2_normalize(cached).tolist()` with the v1.2.0 cache rationale and the `_is_usable_cached` ordering
- `tests/unit/embedding/test_manager.py` - `import math`; cache-segmentation mock/assertions moved to the exact unit vector `[1.0, 0.0]`; three `TestCacheSafety` regressions: off-unit hits (parametrized 1.003596 / 0.9985), zero pass-through, idempotent unit hits
- `tests/unit/inference/test_reranker.py` - CUDA probe pinned False in `test_local_load_cpu_quiet_and_already_loaded`; assertions and double-load behavior unchanged

## Decisions Made

- Renormalize on read rather than widening `NORM_TOLERANCE`, weakening `validate_batch`, or invalidating the cache DB: the invariant is restored for existing users with no migration and no loss of validation strictness.
- Run normalization strictly after `_is_usable_cached`, preserving the "invalid rows are misses, zero rows pass through" contract (T-ipu-01).
- Make the helper public (`l2_normalize`) in a dedicated module because it now crosses module boundaries; no test or source imported the old private name, so the move is compatible.
- Pin the CUDA probe per-test with `patch("torch.cuda.is_available", ...)`, matching the neighboring `test_local_load_nonquiet_explicit_device_ignores_cuda_probe` convention; no global fixture or environment mutation (T-ipu-03).

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None. The pre-fix 1-failed / 3233-passed baseline on this CUDA host became 0 failures / 3250 passed / 1 skipped as intended.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Issue #4 is now effective for users upgrading with a populated embedding cache; no cache deletion or re-embed migration is required.
- No known stubs, skipped tests, or unrun verifications introduced by this plan.

## Self-Check: PASSED
