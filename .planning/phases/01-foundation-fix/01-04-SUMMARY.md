---
phase: 01-foundation-fix
plan: 04
type: execute
subsystem: embedding
completed_at: "2026-04-15"
duration_minutes: ~12
key_files:
  created: []
  modified:
    - src/docsift/embedding/model.py
    - src/docsift/embedding/factory.py
deviations: "None - plan executed exactly as written."
---

# Phase 01 Plan 04: Replace Placeholder Embeddings with Real Embedders Summary

**One-liner:** Replaced random/placeholder embedding implementations in the factory with real `sentence-transformers` and `llama-cpp-python` loaders, and unified the `ModelType` enum across modules.

## What Changed

- **`src/docsift/embedding/model.py`**: Removed the local `ModelType` enum definition and now imports it from `docsift.models.embedding`, establishing a single canonical source of truth for model types.
- **`src/docsift/embedding/factory.py`**: Completely rewrote `EmbeddingModelFactory` to delegate to real embedder classes (`SentenceTransformerEmbedder` and `LlamaCppEmbedder`) from `docsift.embedding.embedder`. Removed all inline placeholder classes and `random.random()` fallbacks. Added `ValueError` validation when `model_path` is missing for GGUF models.

## Commits

| Hash | Message | Files |
|------|---------|-------|
| `b32ad39` | `refactor(01-04): unify ModelType by importing from models/embedding.py` | `src/docsift/embedding/model.py` |
| `46be2b7` | `feat(01-04): replace placeholder embedders with real implementations in factory` | `src/docsift/embedding/factory.py`, `src/docsift/embedding/model.py` |

## Verification

- `grep "SentenceTransformerEmbedder" src/docsift/embedding/factory.py` succeeds.
- `grep "LlamaCppEmbedder" src/docsift/embedding/factory.py` succeeds.
- `! grep "random.random()" src/docsift/embedding/factory.py` succeeds.
- Factory branch smoke tests pass: GGUF with `model_path=None` raises `ValueError`, OPENAI and HUGGINGFACE raise `NotImplementedError`.
- `ruff check src/docsift/embedding/factory.py src/docsift/embedding/model.py` passes cleanly.

## Deviations from Plan

None - plan executed exactly as written.

## Known Stubs

None in the modified files. OPENAI and HUGGINGFACE factory branches intentionally raise `NotImplementedError` as specified in the plan.

## Threat Flags

None.

## Self-Check: PASSED

- `src/docsift/embedding/model.py` exists and contains `from docsift.models.embedding import ModelType`.
- `src/docsift/embedding/factory.py` exists and imports `LlamaCppEmbedder` and `SentenceTransformerEmbedder`.
- Commits `b32ad39` and `46be2b7` exist in the repository.
