---
phase: quick-261118-ib0
plan: 01
subsystem: embedding-models
tags: [sentence-transformers, modelscope, qwen3-embedding, l2-normalization, model-cache, migration]
requires: []
provides:
  - float64 L2 renormalization at the embedder boundary for SentenceTransformerEmbedder and ModelScopeEmbedder on every encode path
  - a single <cache>/models model root shared by the embedder, both downloading rerankers, ModelDownloader's default, and `sif models status`
  - automatic adoption of v1.2.0's <cache>/<owner>/<name> model trees into <cache>/models/<owner>/<name>
affects: [model-management, index-embed-path, reranking, docs/migration]
actuals:
  tokens: 5139
  tasks: 3
  commits: 1
  plan_head_before: 8691c41aa4af92ac3786a6d6be2f2a12bdb0b2d4
  plan_head_after: 5f9c0869034338d684e58c4908a8d2f5cf109886
tech-stack:
  added: []
  patterns:
    - "Float64 renormalization at the embedder boundary: model-dtype normalize_embeddings noise is removed before any consumer sees the vector"
    - "One model cache root (<cache>/models) derived from EmbeddingConfig.cache_dir, never repurposing the embedding-cache root"
key-files:
  created: []
  modified:
    - src/sif/embedding/embedder.py
    - src/sif/embedding/manager.py
    - src/sif/embedding/factory.py
    - src/sif/search/rerank.py
    - src/sif/models/download.py
    - docs/migration.md
    - tests/unit/embedding/test_embedder_impl.py
    - tests/unit/embedding/test_manager.py
    - tests/unit/embedding/test_factory.py
    - tests/unit/inference/test_reranker.py
    - tests/unit/cli/test_models.py
    - tests/unit/models/test_download.py
key-decisions:
  - "Renormalize in float64 at the embedder boundary rather than loosening NORM_TOLERANCE (stays 1e-3) or changing validate_batch"
  - "Zero and non-finite vectors pass through the helper unchanged so validate_batch's zero-norm and finiteness gates remain reachable"
  - "model_cache_dir is a separate factory kwarg derived as <cache>/models; EmbeddingConfig.cache_dir keeps rooting the embedding cache DB and OpenAI dimension cache"
  - "The ModelScope factory falls back to cache_dir when model_cache_dir is absent, preserving direct factory callers"
  - "The pre-fix parent-root legacy probe runs only when the cache root's basename is `models`, so explicit non-models roots stay hermetic"
requirements-completed: [QUICK-ISSUES-4-5]
coverage:
  - id: D1
    description: "Off-unit sentence-transformers output (norms 0.9985 and 1.0036) is renormalized to unit length within 1e-12 on embed, embed_batch, embed_query, embed_queries, and embed_documents for both SentenceTransformerEmbedder and ModelScopeEmbedder"
    requirement: QUICK-ISSUES-4-5
    verification:
      - kind: unit
        ref: "tests/unit/embedding/test_embedder_impl.py#TestUnitRenormalization"
        status: pass
      - kind: unit
        ref: "tests/unit/indexing/test_embed_writer.py#test_norm_tolerance_is_pinned"
        status: pass
    human_judgment: false
  - id: D2
    description: "Embedder, reranker, ModelDownloader default, and `sif models status` all resolve the model root to <cache>/models while the embedding cache DB stays at <cache>/embeddings_cache.db"
    requirement: QUICK-ISSUES-4-5
    verification:
      - kind: unit
        ref: "tests/unit/embedding/test_manager.py#TestEmbeddingManager::test_load_model_derives_model_cache_dir"
        status: pass
      - kind: unit
        ref: "tests/unit/embedding/test_factory.py#TestEmbeddingModelFactoryDispatch::test_modelscope_dispatch_forwards_model_cache_dir"
        status: pass
      - kind: unit
        ref: "tests/unit/inference/test_reranker.py#TestCreateReranker::test_create_reranker_auto_detects_qwen3"
        status: pass
      - kind: unit
        ref: "tests/unit/cli/test_models.py#TestModelsStatusPayload::test_json_has_fixed_sections_and_identity_keys"
        status: pass
    human_judgment: false
  - id: D3
    description: "A v1.2.0 <cache>/<owner>/<name> model tree is adopted into <cache>/models/<owner>/<name> with no network call, and a non-`models` explicit root never probes its parent"
    requirement: QUICK-ISSUES-4-5
    verification:
      - kind: unit
        ref: "tests/unit/models/test_download.py#TestLegacyMigration::test_pre_fix_parent_root_layout_is_migrated"
        status: pass
      - kind: unit
        ref: "tests/unit/models/test_download.py#TestLegacyMigration::test_non_models_root_never_probes_its_parent"
        status: pass
    human_judgment: false
metrics:
  duration: 12min
  completed: 2026-11-18
status: complete
---

# Phase quick-261118-ib0 Plan 01: Fix GitHub issues #4 and #5 Summary

**Float64 L2 renormalization on every sentence-transformers encode path plus one `<cache>/models` model root with automatic adoption of v1.2.0 parent-root caches**

## Performance

- **Duration:** ~12 min
- **Started:** 2026-11-18T13:14Z
- **Completed:** 2026-11-18T13:26Z
- **Tasks:** 3
- **Files modified:** 12 (5 source, 6 test, 1 doc)

## Accomplishments

- Issue #4: `_l2_normalize` renormalizes `SentenceTransformerEmbedder` and `ModelScopeEmbedder` output in float64 on `embed`, `embed_batch`, and `_encode_with_prompt`; off-unit norms of 0.9985/1.0036 now come back unit within 1e-12, so `sif index embed` no longer aborts on the D-17 norm gate. `NORM_TOLERANCE` stays 1e-3 and `validate_batch` is untouched.
- Issue #5 part 1: `EmbeddingManager.load_model` derives `model_cache_dir = <cache>/models` and passes it to the factory; ModelScope dispatch forwards it to `ModelDownloader` (with a `cache_dir` fallback for direct callers); `create_reranker` points both downloading rerankers at `<cache>/models`. `sif models status` and `ModelDownloader`'s default already used that root, so all paths now agree while `<cache>/embeddings_cache.db` stays put.
- Issue #5 part 2: `_legacy_candidates` probes the pre-fix v1.2.0 parent-root layout (`<cache>/<owner>/<name>`, plus the mangled spelling) when the cache root is named `models`, so existing ~2.2 GB model caches are adopted with a verified manifest and zero network calls. A root not named `models` never inspects its parent.
- `docs/migration.md` documents the newly recognized pre-fix layout; regression tests cover off-unit renormalization (all five public paths, both embedders), zero-vector passthrough, cache-root forwarding, status payload root, and parent-root adoption/hermeticity.
- Full quality suite green: `ruff check`, `ruff format --check`, and `pytest` → 3246 passed, 1 skipped, 95.08% coverage.

## Task Commits

The plan specified one atomic commit for all three tasks:

1. **Tasks 1-3: renormalize embedder output and align model cache root** - `5f9c086` (fix)

**Plan metadata:** not committed by this executor (orchestrator handles docs artifacts)

## Files Created/Modified

- `src/sif/embedding/embedder.py` - module-level `_l2_normalize` helper; wired into both ST-backed embedders' three encode paths
- `src/sif/embedding/manager.py` - derives `model_cache_dir` `<cache>/models` and forwards it alongside `cache_dir`
- `src/sif/embedding/factory.py` - ModelScope dispatch prefers `model_cache_dir`, falls back to `cache_dir`
- `src/sif/search/rerank.py` - `create_reranker` passes `<cache>/models` to Qwen3/CrossEncoder rerankers
- `src/sif/models/download.py` - `_legacy_candidates` adds the guarded parent-root layouts and documents all recognized layouts
- `docs/migration.md` - Model cache bullet lists the pre-fix `<cache>/<owner>/<name>` layout
- `tests/unit/embedding/test_embedder_impl.py` - unit-vector mocks plus `TestUnitRenormalization` regression class
- `tests/unit/embedding/test_manager.py` - cache_dir/model_cache_dir forwarding and None-root tests
- `tests/unit/embedding/test_factory.py` - model_cache_dir forwarding and cache_dir fallback tests
- `tests/unit/inference/test_reranker.py` - reranker cache root assertions moved to `<cache>/models`
- `tests/unit/cli/test_models.py` - status payload pins `settings.cache_dir` to `<cache>/models`
- `tests/unit/models/test_download.py` - parent-root adoption and non-models-root hermeticity tests

## Decisions Made

- Kept the D-17 gate strict and fixed the producer: normalize in float64 at the embedder boundary instead of widening `NORM_TOLERANCE` or weakening `validate_batch`.
- Deliberately preserved zero/non-finite vectors through the helper (divide by 1.0) so `validate_batch`'s zero-norm and finiteness gates remain reachable.
- Kept `EmbeddingConfig.cache_dir` as the embedding-cache root (DB, OpenAI dimension cache, HF `cache_folder`) and introduced `model_cache_dir` as a separate derived value, avoiding any cache-DB move.
- Gated the parent-root legacy probe on `Path(cache_root).name == "models"` so explicit roots such as `/tmp/custom` never inspect their parent (T-ib0-01).
- Reused the existing manifest-write/verify/atomic-rename adoption machinery unchanged; only candidate discovery was extended.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

- Authoring-time only: two ruff findings in the new test class (one long decorator line, one unused `**kwargs` in the fake model) were fixed before the final gates. No behavioral deviation.
- `ty check src/sif` reports 14 pre-existing diagnostics in `embedder.py` (deprecated `get_sentence_embedding_dimension`) and `rerank.py` (transformers/sentence-transformers stub typing); none touch lines changed by this plan and they predate it. The CLAUDE.md quality suite (ruff check, ruff format --check, pytest) is green.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Issue #4 and #5 fixes are complete and ready for the v1.2.1 patch release flow.
- No known stubs, skipped tests, or unrun verifications from this plan.

## Self-Check: PASSED
