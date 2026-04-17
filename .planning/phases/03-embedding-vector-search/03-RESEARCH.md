# Phase 3: Embedding & Vector Search - Research

**Researched:** 2026-04-16
**Domain:** Python embedding backends, sqlite-vec vector search, batch insertion
**Confidence:** HIGH

## Summary

Phase 3 enables configurable embedding backends and working semantic vector search in DocSift. The codebase already has the right structural pieces — an `Embedder` protocol, `EmbeddingModelFactory`, `VectorSearcher`, and `sqlite-vec` integration — but several critical integration points are broken or incomplete. `EmbeddingManager` crashes at runtime because it expects an `EmbeddingModel` ABC interface on objects that only implement the `Embedder` protocol. `SchemaManager` hardcodes `FLOAT[768]` despite the default model being 384-dimensional. The CLI's `vsearch_cmd` and `embed_cmd` hardcode `SentenceTransformerEmbedder`, bypassing all backend configuration. Hybrid search currently never uses vectors because `query_cmd` instantiates `HybridSearcher` without an embedder.

The research confirms that `sqlite-vec` fully supports dynamic dimensions (`FLOAT[N]`), batch insertion via `executemany`, and dimension introspection from `sqlite_master`. The OpenAI Python client supports batched embedding requests and a `dimensions` parameter. ModelScope already has a working `ModelScopeEmbedder` but it is not wired into the factory or settings. The primary recommendation is to unify the factory/manager architecture around the existing `Embedder` protocol, add missing settings fields, make `SchemaManager` dimension-aware, and refactor the indexer and CLI commands to use `EmbeddingManager` consistently.

**Primary recommendation:** Unify embedding backend selection through `Settings.model_type` → `EmbeddingManager.from_settings()` → `Embedder` protocol, fix `SchemaManager` to use dynamic dimensions with fail-fast mismatch detection, and implement cross-document batch embedding insertion in `embed_cmd`.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Backend configuration (model_type, api_key, api_base) | API / Backend (`config/settings.py`) | — | Pydantic Settings with `DOCSIFT_` prefix is the canonical source of truth |
| Embedder lifecycle & batch inference | API / Backend (`embedding/manager.py`) | — | `EmbeddingManager` owns model loading, caching, and `embed()` batching |
| Backend instantiation | API / Backend (`embedding/factory.py`) | — | Factory selects implementation based on `model_type` |
| Vector table schema | Database / Storage (`database/schema.py`) | — | `SchemaManager` creates `vec0` tables and must know dimension |
| Vector search execution | API / Backend (`search/vector.py`) | — | `VectorSearcher` executes `sqlite-vec` SQL queries |
| Hybrid search orchestration | API / Backend (`search/hybrid.py`) | — | `HybridSearcher` fuses BM25 and vector results |
| Embedding insertion | API / Backend (`cli/commands/index.py`, `indexing/indexer.py`) | Database (`VectorSearcher.add_embeddings_batch`) | CLI/indexer collect chunks; `VectorSearcher` persists them |
| Search CLI entry points | Browser / Client (`cli/commands/search.py`) | — | Click commands receive user input and delegate to search tiers |

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| sentence-transformers | 5.4.1 | Local embedding inference for `all-MiniLM-L6-v2` | Default backend, well-maintained, ONNX support [VERIFIED: PyPI] |
| llama-cpp-python | 0.3.20 | GGUF model inference | Locked decision D-03 for `gguf` backend [VERIFIED: PyPI] |
| openai | 2.32.0 | OpenAI-compatible API client | Locked decision D-04; supports batch input and `dimensions` param [VERIFIED: PyPI] |
| modelscope | 1.35.4 | China-accessible model download & inference | Locked decision D-06; first-class backend [VERIFIED: PyPI] |
| sqlite-vec | 0.1.6 | SQLite vector extension | Already integrated; supports dynamic `FLOAT[N]` and batch insert [VERIFIED: in-memory experiment] |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| numpy | — | Embedding vector representation | Standard array format across all backends |
| pydantic | — | Settings validation | Already used for `DOCSIFT_` env prefix |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| openai | httpx + manual JSON | More code to maintain; openai client is already a dependency and handles retries, streaming, typing |
| sqlite-vec | faiss / chroma | Would violate local-first, single-file SQLite architecture; sqlite-vec is the locked stack choice |

**Installation:**
```bash
pip install sentence-transformers==5.4.1 llama-cpp-python==0.3.20 openai==2.32.0 modelscope==1.35.4 sqlite-vec==0.1.6
```

**Version verification:** All versions confirmed current on PyPI as of 2026-04-16.

## Architecture Patterns

### System Architecture Diagram

```
User Input (CLI: docsift embed / docsift vsearch / docsift query)
        |
        v
+--------------------------------------------------+
|  Click Commands (search.py, index.py)            |
|  - Parse --model-type, --api-base, --api-key      |
+--------------------------------------------------+
        |
        v
+--------------------------------------------------+
|  Settings (Pydantic)                             |
|  - model_type, model_name, embedding_dim         |
|  - api_base, api_key                             |
+--------------------------------------------------+
        |
        v
+--------------------------------------------------+
|  EmbeddingManager                                |
|  - from_settings() selects factory path          |
|  - Caches model instance                         |
|  - embed(texts) -> List[List[float]]             |
+--------------------------------------------------+
        |
        v
+--------------------------------------------------+
|  EmbeddingModelFactory / create_embedder()       |
|  - sentence_transformers -> SentenceTransformerEmbedder
|  - gguf -> LlamaCppEmbedder                      |
|  - openai -> OpenAIEmbedder (NEW)                |
|  - modelscope -> ModelScopeEmbedder (NEW wiring) |
+--------------------------------------------------+
        |
        v
+--------------------------------------------------+
|  VectorSearcher (sqlite-vec)                     |
|  - Schema validation (dimension check)           |
|  - add_embedding() / add_embeddings_batch()      |
|  - search(embedding, options) -> results         |
+--------------------------------------------------+
        ^
        |
+--------------------------------------------------+
|  HybridSearcher                                  |
|  - BM25Searcher.search()                         |
|  - VectorSearcher.search()                       |
|  - RRFFusion.combine()                           |
+--------------------------------------------------+
```

### Recommended Project Structure
```
src/docsift/
├── config/
│   └── settings.py          # Add model_type, api_key, api_base
├── core/
│   └── models.py            # Embedder protocol (existing)
├── models/
│   └── embedding.py         # Add MODELSCOPE to ModelType
├── embedding/
│   ├── factory.py           # Fix return types, wire modelscope + openai
│   ├── embedder.py          # Add OpenAIEmbedder, fix protocol alignment
│   └── manager.py           # Fix .load() / .model_id assumptions
├── database/
│   ├── schema.py            # Dynamic FLOAT[embedding_dim]
│   └── repositories.py      # Batch create_many, cascade delete embeddings
├── search/
│   ├── vector.py            # Batch insert, dimension introspection
│   ├── hybrid.py            # Already accepts embedder
│   └── pipeline.py          # Already accepts embedder
├── cli/commands/
│   ├── search.py            # Use EmbeddingManager in vsearch/query
│   └── index.py             # Cross-document batch embedding
└── indexing/
    └── indexer.py           # Fix field mismatches, persist embeddings
```

### Pattern 1: Settings-Driven Embedder Selection
**What:** `Settings` fields (`model_type`, `model_name`, `api_base`, `api_key`) flow into `EmbeddingManager.from_settings()`, which delegates to the factory.
**When to use:** Any CLI command or service that needs to load an embedding model.
**Example:**
```python
# Source: src/docsift/config/settings.py pattern + 03-CONTEXT.md D-01
from docsift.config.settings import get_settings
from docsift.embedding.manager import EmbeddingManager

settings = get_settings()
manager = EmbeddingManager.from_settings(settings)
embeddings = manager.embed(["text1", "text2"])
```

### Pattern 2: sqlite-vec Dynamic Dimension & Batch Insert
**What:** Create `vec0` table with `FLOAT[N]` where `N` comes from `Settings.embedding_dim`. Insert multiple embeddings in one `executemany` call using `vec_f32(json.dumps(vec))`.
**When to use:** Schema creation and any embedding persistence path.
**Example:**
```python
# Source: in-memory experimental verification
import json
import sqlite_vec

conn.execute(f"""
    CREATE VIRTUAL TABLE IF NOT EXISTS document_embeddings USING vec0(
        embedding_id TEXT PRIMARY KEY,
        document_id TEXT NOT NULL,
        chunk_id TEXT,
        embedding FLOAT[{dim}]
    )
""")

conn.executemany(
    "INSERT INTO document_embeddings VALUES (?, ?, ?, vec_f32(?))",
    [(eid, doc_id, chunk_id, json.dumps(vec)) for ...]
)
```

### Pattern 3: OpenAI Dimension Auto-Detection & Caching
**What:** On first load, call the OpenAI embeddings API with a probe text, extract dimension from the response, and cache it to a local file (e.g., `~/.docsift/openai_dim_cache.json`) to avoid repeated probing.
**When to use:** `openai` backend initialization when `embedding_dim` is not explicitly set or needs verification.
**Example:**
```python
# Source: openai Python client docs pattern
response = client.embeddings.create(input=["probe"], model=model_name)
detected_dim = len(response.data[0].embedding)
# Cache to file; TTL at discretion per 03-CONTEXT.md
```

### Anti-Patterns to Avoid
- **Calling `.load()` / `.model_id` on `Embedder` instances:** `EmbeddingManager` currently does this and crashes. `Embedder` protocol only guarantees `embed()`, `embed_batch()`, and `dimension`. [VERIFIED: codebase inspection]
- **Hardcoding `FLOAT[768]` in schema:** The default model is 384-dim; this creates a runtime mismatch. [VERIFIED: src/docsift/database/schema.py]
- **Instantiating `SentenceTransformerEmbedder` directly in CLI commands:** Bypasses backend configuration and makes `model_type` meaningless. [VERIFIED: src/docsift/cli/commands/search.py, src/docsift/cli/commands/index.py]
- **One-by-one SQL insertion in loops:** `DocumentChunkRepository.create_many()` and `embed_cmd` both loop over individual inserts. Use `executemany` for batch paths. [VERIFIED: codebase inspection]
- **Python fallback for vector search:** `VectorSearcher` must fail fast if `sqlite-vec` is unavailable. Any remaining fallback logic should be removed. [VERIFIED: 01-CONTEXT.md + vector.py]

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| OpenAI API client | Raw `httpx` requests | `openai.OpenAI()` | Handles auth headers, retries, JSON parsing, batching, and `dimensions` parameter |
| SQLite vector extension | Pure-Python vector similarity | `sqlite-vec` | Optimized C extension with `vec0` virtual tables, `vec_distance_cosine`, and `vec_f32` serialization |
| SentenceTransformer model loading | Manual ONNX Runtime session | `sentence_transformers.SentenceTransformer` | Abstracts tokenization, pooling, normalization, and device placement |
| GGUF inference | Manual `llama.cpp` bindings | `llama-cpp-python` | Provides a clean Python API over `libllama` |
| ModelScope download | Manual HTTP downloads | `modelscope.snapshot_download` | Handles caching, resume, and local path resolution |

**Key insight:** DocSift already depends on all these libraries as optional extras. Building custom wrappers around them adds maintenance burden and reintroduces bugs that the upstream libraries have already solved (e.g., batching, retry logic, model caching).

## Common Pitfalls

### Pitfall 1: EmbeddingManager Runtime Crash
**What goes wrong:** `EmbeddingManager.load_model()` calls `self._model.load()` and later accesses `self._model.model_id`, but the factory returns `SentenceTransformerEmbedder` / `LlamaCppEmbedder` instances that only implement the `Embedder` protocol and lack both methods.
**Why it happens:** The codebase has two parallel abstractions — `Embedder` protocol and `EmbeddingModel` ABC — and the factory return type claims `EmbeddingModel` while actually returning `Embedder` implementations.
**How to avoid:** Align `EmbeddingManager` and `EmbeddingModelFactory` on the `Embedder` protocol. Remove `.load()` / `.unload()` / `.model_id` requirements from the hot path, or ensure every factory product implements them.
**Warning signs:** `AttributeError: 'SentenceTransformerEmbedder' object has no attribute 'load'` on first embed operation.

### Pitfall 2: Dimension Mismatch Between Schema and Model
**What goes wrong:** `SchemaManager` creates `document_embeddings` with `FLOAT[768]`, but the default model (`all-MiniLM-L6-v2`) produces 384-dimensional vectors. Inserting a 384-dim vector into a 768-dim table causes a SQLite error.
**Why it happens:** The dimension was hardcoded during early development and never made dynamic.
**How to avoid:** Pass `embedding_dim` into `SchemaManager.__init__` and use `FLOAT[{self.embedding_dim}]` in the `CREATE VIRTUAL TABLE` statement. Fail fast at startup if an existing table has a mismatched dimension (per D-09).
**Warning signs:** `sqlite3.OperationalError: wrong number of entries in vector` during embedding insertion.

### Pitfall 3: Hybrid Search Silently Degrades to BM25
**What goes wrong:** `query_cmd` constructs `HybridSearcher(db.connection)` without passing an embedder. `HybridSearcher.search()` falls back to BM25-only when `vector_results` is empty or when `self.embedder` is `None`.
**Why it happens:** The embedder was never wired into the CLI command after the hybrid search feature was added.
**How to avoid:** Always instantiate `HybridSearcher` with an `EmbeddingManager` (or embedder) in CLI commands. Remove the silent BM25-only fallback so vector failures surface as errors.
**Warning signs:** `docsift query` returns results but never uses vector search even after `docsift embed`.

### Pitfall 4: Orphaned Embeddings on Document/Collection Delete
**What goes wrong:** `DocumentRepository.delete()` and `delete_by_collection()` delete chunks from `document_chunks` but do not delete corresponding rows from `document_embeddings`. Over time the vector table accumulates stale, unreferenced embeddings.
**Why it happens:** `document_embeddings` was added after the repository layer was written, and cascade logic was never updated.
**How to avoid:** Add `DELETE FROM document_embeddings WHERE document_id = ?` calls in the repository delete methods, or use a SQLite foreign key trigger if feasible with `vec0` tables.
**Warning signs:** Vector search returns results for documents that no longer exist in `documents` or `document_chunks`.

### Pitfall 5: Indexer Field-Mismatch Crashes
**What goes wrong:** `DocumentIndexer._index_file` imports `DocumentChunk` from `docsift.core.document` (expects `start_line`, `end_line`) but chunkers return `docsift.core.models.DocumentChunk` (has `start_pos`, `end_pos`). It also creates `docsift.core.document.Document` which lacks `mtime`, but `DocumentRepository.create()` reads `doc.mtime`.
**Why it happens:** Refactoring renamed/moved models without updating all consumers.
**How to avoid:** Use `docsift.core.models.DocumentChunk` and `docsift.core.models.Document` consistently. Ensure `Document` has `mtime` set before repository persistence.
**Warning signs:** `TypeError: DocumentChunk.__init__() got an unexpected keyword argument 'start_line'` or `AttributeError: 'Document' object has no attribute 'mtime'` during indexing.

## Code Examples

### Verified sqlite-vec Dynamic Dimension + Batch Insert
```python
# Source: in-memory experimental verification
import sqlite3
import sqlite_vec
import json

conn = sqlite3.connect(":memory:")
conn.enable_load_extension(True)
sqlite_vec.load(conn)

dim = 384
conn.execute(f"""
    CREATE VIRTUAL TABLE document_embeddings USING vec0(
        embedding_id TEXT PRIMARY KEY,
        document_id TEXT,
        chunk_id TEXT,
        embedding FLOAT[{dim}]
    )
""")

rows = [
    ("e1", "d1", "c1", json.dumps([0.1] * dim)),
    ("e2", "d1", "c2", json.dumps([0.2] * dim)),
]
conn.executemany(
    "INSERT INTO document_embeddings VALUES (?, ?, ?, vec_f32(?))",
    rows
)
```

### Verified OpenAI Batch Embedding with Dimensions
```python
# Source: openai Python client verification
from openai import OpenAI

client = OpenAI(api_key="sk-...")
response = client.embeddings.create(
    input=["hello", "world"],
    model="text-embedding-3-small",
    dimensions=256,
)
embeddings = [item.embedding for item in response.data]
```

### Recommended VectorSearcher Batch Insert Method
```python
# Source: derived from vector.py + sqlite-vec docs
import json
from typing import List

class VectorSearcher:
    ...
    def add_embeddings_batch(
        self,
        items: List[tuple[str, str, str | None, list[float]]],
    ) -> None:
        """Insert multiple embeddings in one transaction.

        Each item is (embedding_id, document_id, chunk_id, embedding_vector).
        """
        rows = [
            (eid, doc_id, chunk_id, json.dumps(vec))
            for eid, doc_id, chunk_id, vec in items
        ]
        self.db.executemany(
            "INSERT INTO document_embeddings VALUES (?, ?, ?, vec_f32(?))",
            rows,
        )
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Hardcoded `FLOAT[768]` | Dynamic `FLOAT[embedding_dim]` | Phase 3 | Aligns schema with any backend/model |
| Per-document embedding loop in `embed_cmd` | Cross-document batch via `EmbeddingManager.embed()` | Phase 3 | Faster indexing, less DB churn |
| Direct `SentenceTransformerEmbedder` in CLI | `EmbeddingManager.from_settings()` | Phase 3 | All backends work through unified path |
| Python fallback in `VectorSearcher` | Fail fast with `RuntimeError` | Phase 1 | Prevents silent quality degradation |

**Deprecated/outdated:**
- `docsift.core.document.DocumentChunk` (with `start_line`/`end_line`): Stale import in `indexer.py`; use `docsift.core.models.DocumentChunk` instead.
- `docsift.database.sqlite_repository.py`: Already deleted per D-02; do not reintroduce.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `sqlite-vec` `vec0` table dimension can be introspected from `sqlite_master` SQL via regex `FLOAT\[(\d+)\]` | Architecture Patterns | Dimension mismatch detection fails; may require parsing `PRAGMA table_info` or using a metadata table instead |
| A2 | OpenAI `dimensions` parameter works with all OpenAI-compatible endpoints | Standard Stack | Some local endpoints (e.g., llama.cpp server) may ignore `dimensions`; fallback to full-dim response |
| A3 | ModelScope `snapshot_download` cache directory behavior is compatible with `SentenceTransformer` local path loading | Standard Stack | May need explicit cache dir management or symlink handling |

## Open Questions (RESOLVED)

1. **Exact OpenAI dimension cache file location and TTL**
   - What we know: 03-CONTEXT.md leaves this to Claude's discretion.
   - What's unclear: Whether to use `~/.docsift/openai_dim_cache.json` or a SQLite metadata table.
   - Recommendation: Use a JSON file in `Settings.get_db_path().parent` with a 7-day TTL for simplicity.

2. **How to handle `document_embeddings` cascade delete with `vec0` tables**
   - What we know: `vec0` is a virtual table; standard `ON DELETE CASCADE` foreign keys may not work on virtual tables.
   - What's unclear: Whether SQLite allows FK triggers on virtual tables.
   - Recommendation: Implement explicit `DELETE FROM document_embeddings WHERE document_id = ?` in `DocumentRepository.delete()` and `delete_by_collection()` rather than relying on FK cascades.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python | Runtime | ✓ | 3.12 | — |
| sqlite-vec | Vector search | ✓ | 0.1.6 | Fail fast (no fallback per Phase 1) |
| sentence-transformers | Default backend | ✓ | 5.4.1 | — |
| openai | OpenAI backend | ✓ | 2.32.0 | — |
| llama-cpp-python | GGUF backend | ✓ | 0.3.20 | — |
| modelscope | ModelScope backend | ✓ | 1.35.4 | — |

**Missing dependencies with no fallback:** None.

**Missing dependencies with fallback:** None.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 8.x |
| Config file | `pyproject.toml` (tool.pytest.ini_options) |
| Quick run command | `pytest tests/unit/search/test_vector.py -x` |
| Full suite command | `pytest` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| VEC-01 | `Settings` accepts `model_type`, `api_base`, `api_key` | unit | `pytest tests/unit/config/test_settings.py -x` | ❌ Wave 0 |
| VEC-01 | Factory returns correct embedder for each `model_type` | unit | `pytest tests/unit/embedding/test_factory.py -x` | ❌ Wave 0 |
| VEC-01 | `vsearch_cmd` respects `model_type` | unit | `pytest tests/unit/cli/test_search.py::TestVSearchBackend -x` | ❌ Wave 0 |
| VEC-02 | `SchemaManager` uses dynamic dimension | unit | `pytest tests/unit/database/test_schema.py -x` | ❌ Wave 0 |
| VEC-02 | Startup fails fast on dimension mismatch | unit | `pytest tests/unit/database/test_schema.py::TestDimensionMismatch -x` | ❌ Wave 0 |
| VEC-02 | `VectorSearcher` has batch insert | unit | `pytest tests/unit/search/test_vector.py -x` | ❌ Wave 0 |
| VEC-03 | `embed_cmd` batches embeddings cross-document | integration | `pytest tests/unit/cli/test_index.py -x` | ❌ Wave 0 |
| VEC-04 | `ModelScopeEmbedder` wired into factory | unit | `pytest tests/unit/embedding/test_factory.py -x` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `pytest tests/unit/{relevant_module} -x`
- **Per wave merge:** `pytest`
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps
- [ ] `tests/unit/config/test_settings.py` — covers VEC-01 settings fields
- [ ] `tests/unit/embedding/test_factory.py` — covers factory wiring for all backends
- [ ] `tests/unit/database/test_schema.py` — covers dynamic dimension and mismatch detection
- [ ] `tests/unit/search/test_vector.py` — currently has stale import (`VectorSearchStrategy`); must be fixed and extended for batch insert
- [ ] `tests/unit/cli/test_search.py` — needs backend-aware vsearch tests
- [ ] `tests/unit/cli/test_index.py` — needs batch embedding tests; current `test_index_commands.py` has stale imports

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | No | Not in scope for this phase |
| V3 Session Management | No | Not in scope for this phase |
| V4 Access Control | No | Not in scope for this phase |
| V5 Input Validation | Yes | Pydantic validators on `Settings.api_base`, `Settings.api_key`; ensure `api_base` is a valid HTTP(S) URL |
| V6 Cryptography | Yes | `api_key` must never be logged; store only in memory via Pydantic Settings |

### Known Threat Patterns for Embedding Stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| API key leakage in logs | Information Disclosure | Do not log `api_key`; redact in `Settings.__repr__` if necessary |
| SSRF via malicious `api_base` | Spoofing | Validate `api_base` is HTTP/HTTPS and reject file://, gopher://, etc. |
| Prompt injection in embedded documents | Tampering | Out of scope for indexing; document content is user-controlled local data |

## Sources

### Primary (HIGH confidence)
- Codebase inspection of `src/docsift/embedding/factory.py`, `src/docsift/embedding/embedder.py`, `src/docsift/embedding/manager.py`, `src/docsift/config/settings.py`, `src/docsift/database/schema.py`, `src/docsift/search/vector.py`, `src/docsift/search/hybrid.py`, `src/docsift/cli/commands/search.py`, `src/docsift/cli/commands/index.py`, `src/docsift/indexing/indexer.py`, `src/docsift/database/repositories.py`
- In-memory SQLite experiment verifying `sqlite-vec` dynamic dimension and batch insert
- PyPI version queries: `sentence-transformers==5.4.1`, `llama-cpp-python==0.3.20`, `openai==2.32.0`, `modelscope==1.35.4`, `sqlite-vec==0.1.6`

### Secondary (MEDIUM confidence)
- OpenAI Python client documentation pattern for `embeddings.create(input=[...], dimensions=N)`
- sqlite-vec README patterns for `vec_f32` and `vec0` table creation

### Tertiary (LOW confidence)
- None

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — verified via PyPI and local package imports
- Architecture: HIGH — verified via direct codebase inspection and experimental SQLite validation
- Pitfalls: HIGH — all listed pitfalls were reproduced or directly observed in source code

**Research date:** 2026-04-16
**Valid until:** 2026-05-16 (stable stack, low churn expected)
