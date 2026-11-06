---
phase: 03-embedding-vector-search
plan: 02
subsystem: embedding
key-files:
  created:
    - tests/unit/embedding/test_openai_embedder.py
    - tests/unit/embedding/test_factory.py
  modified:
    - src/docsift/models/embedding.py
    - src/docsift/embedding/embedder.py
    - src/docsift/embedding/factory.py
decisions:
  - Patched optional ML library imports via builtins.__import__ in unit tests to avoid installing heavy dependencies
  - Added noqa markers for intentional local imports (optional dependency lazy loading)
  - HuggingFace backend remains NotImplementedError as per existing scope
metrics:
  duration: "~15m"
  completed_date: "2026-04-16"
---

# Phase 03 Plan 02: Embedding Factory and OpenAIEmbedder Summary

**One-liner:** Implemented OpenAIEmbedder with dimension auto-detection, added MODELSCOPE to ModelType, refactored the factory to return Embedder protocol instances, and created unit tests for all backends.

## What Was Done

1. **ModelType enum update** — Added `MODELSCOPE = "modelscope"` to `src/docsift/models/embedding.py`.
2. **OpenAIEmbedder implementation** — Added a new `OpenAIEmbedder` class in `src/docsift/embedding/embedder.py` that:
   - Implements the `Embedder` protocol (`embed`, `embed_batch`, `dimension`)
   - Auto-detects embedding dimension via a single API probe
   - Caches detected dimension to a local JSON file to avoid repeated probes
   - Supports custom `api_base` for OpenAI-compatible endpoints
3. **Factory refactor** — Rewrote `src/docsift/embedding/factory.py` to:
   - Import and use the `Embedder` protocol as the return type
   - Wire `OpenAIEmbedder` and `ModelScopeEmbedder` into `create_model`
   - Implement `_create_openai_model` and `_create_modelscope_model`
4. **Unit tests** — Created:
   - `tests/unit/embedding/test_openai_embedder.py` (5 tests covering cache, detection, embed, embed_batch, import error)
   - `tests/unit/embedding/test_factory.py` (5 tests covering all four backends plus unsupported type handling)
   - Tests mock all external API calls and optional imports; no real network requests are made

## Deviations from Plan

None — plan executed exactly as written.

## Auth Gates

None.

## Known Stubs

None in the files modified by this plan. `HuggingFace` backend intentionally raises `NotImplementedError`, which is pre-existing and documented.

## Threat Flags

None beyond what was already registered in the plan's threat model.

## Self-Check: PASSED

- [x] `src/docsift/models/embedding.py` contains `MODELSCOPE = "modelscope"`
- [x] `src/docsift/embedding/embedder.py` contains `class OpenAIEmbedder(Embedder)`
- [x] `src/docsift/embedding/factory.py` imports `Embedder` and returns it from all `_create_*` methods
- [x] `tests/unit/embedding/test_factory.py` exists and passes (5 tests)
- [x] `tests/unit/embedding/test_openai_embedder.py` exists and passes (5 tests)
- [x] ruff check passes on all modified files
