# Phase 3: Embedding & Vector Search - Context

**Gathered:** 2026-04-16
**Status:** Ready for planning

<domain>
## Phase Boundary

Enable configurable embedding backends and working semantic vector search.

This phase delivers:
- Configurable embedding backends (sentence-transformers, llama-cpp-python, OpenAI-compatible API) via Settings and CLI
- Vector search that uses `sqlite-vec` and refuses brute-force Python fallback on large indexes
- Batch embedding insertion for better indexing performance
- ModelScope as a first-class alternative backend for downloading and loading models

</domain>

<decisions>
## Implementation Decisions

### Backend Configuration
- **D-01:** Add an explicit `model_type` field to `Settings`, exposed as `DOCSIFT_MODEL_TYPE` environment variable and `--model-type` CLI option.
- **D-02:** Default `model_type` is `sentence_transformers` to align with the default `model_name` (`all-MiniLM-L6-v2`).
- **D-03:** Valid model types are: `sentence_transformers`, `gguf`, `openai`, `modelscope`.

### OpenAI-Compatible API
- **D-04:** Support generic OpenAI-compatible endpoints with configurable `api_base`, `api_key`, and `model_name`.
- **D-05:** On first model load, auto-detect the embedding dimension from the API and cache it locally to avoid repeated probing on subsequent runs.

### ModelScope Integration
- **D-06:** ModelScope is a first-class backend type (`model_type = "modelscope"`), with integrated download-and-load behavior via `ModelScopeEmbedder`.
- **D-07:** The existing `pull` command's ModelScope fallback for GGUF models remains unchanged.

### Vector Table Dimension
- **D-08:** `SchemaManager` creates the `document_embeddings` table with a dynamic dimension derived from `Settings.embedding_dim` instead of the current hardcoded `FLOAT[768]`.
- **D-09:** If an existing `document_embeddings` table has a mismatched dimension, fail fast at startup with a clear error message instructing the user to rebuild the index. Do NOT auto-delete or recreate the table silently.

### Batch Embedding Insertion
- **D-10:** Batch embedding at the indexer level: collect chunks across documents within a collection, generate embeddings via `EmbeddingManager.embed()` (which already batches inference), and persist them to the database efficiently.

### Claude's Discretion
- Specific error message wording for dimension mismatch and missing optional dependencies.
- Implementation details of dimension caching for OpenAI endpoints (cache file location and TTL).
- Exact internal naming of new Settings fields and validators.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requirements & Roadmap
- `.planning/REQUIREMENTS.md` § Vector Search & Embedding Configurability — VEC-01 through VEC-04
- `.planning/ROADMAP.md` § Phase 3: Embedding & Vector Search

### Existing Code (Patterns to Follow)
- `src/docsift/config/settings.py` — Pydantic Settings with `DOCSIFT_` env prefix
- `src/docsift/embedding/factory.py` — `EmbeddingModelFactory` with backend hooks
- `src/docsift/embedding/embedder.py` — `SentenceTransformerEmbedder`, `LlamaCppEmbedder`, `ModelScopeEmbedder`
- `src/docsift/embedding/manager.py` — `EmbeddingManager` lifecycle and batch inference
- `src/docsift/models/embedding.py` — `EmbeddingConfig`, `ModelType`
- `src/docsift/search/vector.py` — `VectorSearcher` with sqlite-vec integration
- `src/docsift/database/schema.py` — `SchemaManager._create_vector_tables()` (currently hardcodes 768)
- `src/docsift/cli/commands/pull.py` — `pull` command with HF primary / ModelScope fallback
- `src/docsift/cli/commands/index.py` — `embed_cmd` and indexer integration points
- `src/docsift/indexing/indexer.py` — `DocumentIndexer` embedding flow

### Prior Phase Context
- `.planning/phases/01-foundation-fix/01-CONTEXT.md` — Vector search must fail fast; heavy ML libraries remain optional extras
- `.planning/phases/02-cli-core-completion/02-CONTEXT.md` — `pull` HF primary / ModelScope fallback decision

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `EmbeddingModelFactory` already has `create_model` hooks for GGUF, sentence-transformers, OpenAI, and HuggingFace.
- `ModelScopeEmbedder` exists in `embedder.py` but is **not yet wired into the factory** — this wiring is required.
- `VectorSearcher` already uses `sqlite-vec` and fails fast (per Phase 1 decision).
- `EmbeddingManager.embed()` already handles batch inference with caching.

### Established Patterns
- Pydantic Settings with `DOCSIFT_` prefix for environment variables.
- Optional heavy ML libraries are imported at runtime with clear error messages (`sentence-transformers`, `llama-cpp-python`, `modelscope`).
- Repository pattern for all database access.

### Integration Points
- `Settings` → `EmbeddingConfig` → `EmbeddingManager.from_settings()` is the configuration pipeline that needs the new `model_type` field.
- `SchemaManager._create_vector_tables()` must read dimension from settings instead of hardcoding `FLOAT[768]`.
- `DocumentIndexer._index_file()` and `embed_cmd` both generate embeddings; they should reuse `EmbeddingManager` for consistent backend selection.
- `VectorSearcher.add_embedding()` is the canonical path for persisting embeddings to `document_embeddings`.

</code_context>

<specifics>
## Specific Ideas

No specific requirements beyond the decisions above — open to standard approaches.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 03-embedding-vector-search*
*Context gathered: 2026-04-16*
