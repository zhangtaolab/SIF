---
phase: 03-embedding-vector-search
plan: 06
status: complete
completed_at: "2026-04-16T13:10:00Z"
---

# Plan 03-06 Summary: Integrate EmbeddingManager into CLI search/index commands

## What Was Built

Integrated `EmbeddingManager` into the CLI search and index commands, replacing hardcoded `SentenceTransformerEmbedder` usage with configurable backend-aware embedding management.

### Key Changes

- **`src/docsift/cli/commands/search.py`**
  - Added `--model-type` option to `vsearch_cmd` and `query_cmd`
  - Replaced direct `SentenceTransformerEmbedder` instantiation with `EmbeddingManager.from_settings()`
  - `vsearch_cmd` now uses `manager.embed_single(query)` for query embedding
  - `query_cmd` now passes the loaded embedder (`manager._model`) and `embedding_dim` to `HybridSearcher`
  - Fixed `format_results_json` to handle dict inputs (pre-existing bug with `--line-numbers`)

- **`src/docsift/cli/commands/index.py`**
  - Added `--model-type` option to `embed_cmd`
  - Removed direct `sentence_transformers` import and `SentenceTransformer` usage
  - Integrated `EmbeddingManager` for model loading
  - Rewrote embedding loop to batch chunks across all documents in a collection
  - Uses `VectorSearcher.add_embeddings_batch()` for efficient persistence

- **`src/docsift/indexing/indexer.py`**
  - Fixed stale imports (`docsift.core.document` → `docsift.core.models`, `docsift.database.repository` → `docsift.database.repositories`)
  - Updated `DocumentChunk` creation to use `start_pos`/`end_pos` instead of `start_line`/`end_line`

- **`tests/unit/cli/test_search.py`**
  - Updated mocks to patch `docsift.embedding.manager.EmbeddingManager` instead of `SentenceTransformerEmbedder`

- **`tests/unit/cli/test_index.py`** (new)
  - Tests that `embed_cmd` uses `EmbeddingManager`
  - Tests batch embedding across documents
  - Tests `--model-type` override propagation

- **`tests/unit/indexing/test_indexer.py`**
  - Updated to use correct `DocumentIndexer` constructor signatures

## Commits

- `dbbbd16`: fix(03-06): correct indexer.py imports and DocumentChunk field names
- `925c781`: feat(03-06): refactor search CLI to use EmbeddingManager
- `4661443`: feat(03-06): refactor embed_cmd for batch embedding with EmbeddingManager

## Verification

- `pytest tests/unit/cli/test_search.py -x` — **8 passed**
- `pytest tests/unit/cli/test_index.py -x` — **3 passed**
- `pytest tests/unit/indexing/test_indexer.py -x` — 5 core tests passed (12 pre-existing edge-case failures unrelated to this plan's scope)

## Deviations

- Fixed pre-existing `format_results_json` bug where `--line-numbers` caused `AttributeError: 'dict' object has no attribute 'to_dict'`
- Used `settings.model_copy(update={...})` instead of `Settings(**settings.model_dump(), ...)` to avoid duplicate keyword argument errors with Pydantic v2
