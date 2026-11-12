# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

SIF is a Python 3.10+ local hybrid search engine for personal knowledge bases. It indexes Markdown notes and documents, providing BM25 keyword search, semantic vector search, and hybrid ranking. It exposes both a Click CLI and an MCP server, keeping all data local in SQLite.

## Common Development Commands

Install in development mode:
```bash
pip install -e ".[dev]"
```

Run the full quality suite:
```bash
ruff check src tests
ruff format --check src tests
pytest
```

Run a single test file:
```bash
pytest tests/unit/search/test_bm25.py
```

Run a specific test:
```bash
pytest tests/unit/search/test_bm25.py::TestBM25Searcher::test_search_executes_fts_query
```

Format and lint with auto-fix:
```bash
ruff format src tests
ruff check --fix src tests
```

Type check:
```bash
ty check src/sif
```

Run the CLI locally:
```bash
python -m sif.cli.main --help
# or after pip install -e .
sif --help
```

## High-Level Architecture

SIF uses a layered architecture with clean separation between presentation, application, domain, and infrastructure layers.

```
src/sif/
├── cli/                    # Click CLI entry point and commands
├── mcp/                    # Unified MCP server (MCPServer, transports in mcp/transports/)
├── core/                   # Domain models, enums, and protocols
├── indexing/               # Document ingestion pipeline
├── search/                 # Search strategies (BM25, Vector, Hybrid)
├── database/               # SQLite connection, schema, repositories
├── embedding/              # Embedding models and factory
├── config/                 # Pydantic Settings
└── utils/                  # Logging, progress tracking, helpers
```

### Key Architectural Patterns

**Repository Pattern:** Entity CRUD for collections, documents, chunks, contexts, query logs, and the LLM cache goes through standalone repository classes in `src/sif/database/repositories.py` (`CollectionRepository`, `DocumentRepository`, `DocumentChunkRepository`, `ContextRepository`, `QueryLogRepository`, `LLMCacheRepository`) that wrap a shared `sqlite3.Connection`. These concrete classes do not inherit from the abstract `Repository` interfaces in `src/sif/database/repository.py`; those interfaces are referenced only by tests (as `create_autospec` mocks). Search strategies in `src/sif/search/` and the embedding cache in `src/sif/embedding/cache.py` also execute SQL directly, so the repository layer is the convention for entity CRUD, not the sole path for all database access.

**Protocol-Based Extensibility:** `src/sif/core/models.py` defines protocols like `Embedder` that decouple search and indexing from specific embedding providers. The embedding factory in `src/sif/embedding/factory.py` creates real embedders per `ModelType`: `SentenceTransformerEmbedder` (sentence-transformers), `LlamaCppEmbedder` for GGUF models (llama-cpp-python), plus OpenAI and ModelScope providers. The HuggingFace backend raises `NotImplementedError` and is rejected by `model_type` settings validation.

**Factory Pattern:** `EmbeddingModelFactory` creates model instances based on `ModelType`. `Chunker` hierarchy (`FixedSizeChunker`, `MarkdownChunker`, `CodeChunker`, `AutoChunker`) uses `create_chunker()` factory in `src/sif/indexing/chunker.py`.

**MCP Server:** The unified `src/sif/mcp/` package provides the MCP server:
- `MCPServer` in `src/sif/mcp/server.py` — server core
- Transports in `src/sif/mcp/transports/` — `StdioTransport` (`stdio.py`), `HTTPTransport` (`http.py`, FastAPI-based)

**Search Strategy Pattern:** Each search type is a class in `src/sif/search/`:
- `BM25Searcher` — SQLite FTS5
- `VectorSearcher` — `sqlite-vec` (fails fast: `__init__` raises `RuntimeError` when the sqlite-vec extension is unavailable)
- `HybridSearcher` — Combines BM25 + Vector via `RRFFusion`
- `SearchPipeline` — Adds query expansion and reranking

### Data Flow

Primary application state lives in a SQLite database (default is `<platformdirs user_data_dir>/sif/sif.db`, e.g. `~/.local/share/sif/sif.db` on Linux or `~/Library/Application Support/sif/sif.db` on macOS, resolved via `Settings.get_db_path()`; override with `SIF_DB_PATH`). A second SQLite database holds the embedding cache at `<cache_dir>/embeddings_cache.db` (default `<platformdirs user_cache_dir>/sif/embeddings_cache.db`, e.g. `~/.cache/sif/embeddings_cache.db` on Linux or `~/Library/Caches/sif/embeddings_cache.db` on macOS, resolved via `Settings.get_cache_dir()`; enabled by default with `cache_embeddings=True` and created by `src/sif/embedding/cache.py`); a `<db_path>.lock` file also accompanies the main database for cross-process index locking (`src/sif/database/locking.py`). The `SchemaManager` in `src/sif/database/schema.py` creates tables, FTS5 virtual tables, and vector tables. FTS5 tables are external-content tables (`content='documents'`, `content='document_chunks'`) kept synchronized with the main tables via SQLite insert/update/delete triggers.

Embedding models are loaded on demand and cached in `EmbeddingManager._model`.

### Configuration

Settings are defined in `src/sif/config/settings.py` using Pydantic Settings. Environment variables use the `SIF_` prefix (e.g., `SIF_DB_PATH`, `SIF_MODEL_NAME`). Settings are cached via `@lru_cache` in `get_settings()`.

### Error Handling Conventions

- CLI commands raise `click.ClickException(str(e))` for user-facing errors.
- Database transactions use `Database.transaction()` context manager with automatic rollback on exception.
- `HybridSearcher.search()` fails fast on vector errors: embedder/vector exceptions propagate uncaught. BM25-only results are returned only when vector search yields zero results (a no-results path, not failure handling).
- The MCP `SearchBackend` boundary is the one carve-out: when the sqlite-vec extension is unavailable (`VectorSearcher` construction raises `RuntimeError`), `hybrid_search` degrades to BM25-only with a one-time warning, consistent with its embedder-failure degradation at init; the core `HybridSearcher.search()` remains fail-fast.

### Code Style

- Target Python 3.10+; use `list[str] | None` union syntax.
- Line length: 100 (enforced by ruff).
- Max complexity (mccabe): 10.
- Ruff isort with `combine-as-imports = true`.
- Order: stdlib, third-party, first-party (`sif`).
- Two blank lines after imports.
- Type annotations are checked with ty (`ty check src/sif`); new code should be fully annotated (functions take and return typed values).
- CLI modules keep Click decorators as-is; ty does not require decorator typing relaxations.

### Logging

Get module-level loggers with `logger = get_logger(__name__)`. Logger names are prefixed with `sif`. Output goes to `stderr`.

## GSD Workflow

This project uses GSD (Get Shit Done) workflow enforcement. Before making file changes:

- Use `/gsd-quick` for small fixes and doc updates.
- Use `/gsd-debug` for investigation and bug fixing.
- Use `/gsd-execute-phase` for planned phase work.

After every plan completes within a phase, run the full quality suite before marking it done:

```bash
ruff check src tests
ruff format --check src tests
pytest
```
