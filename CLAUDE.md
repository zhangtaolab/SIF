# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

SIF is a Python 3.9+ local hybrid search engine for personal knowledge bases. It indexes Markdown notes and documents, providing BM25 keyword search, semantic vector search, and hybrid ranking. It exposes both a Click CLI and an MCP server, keeping all data local in SQLite.

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
pytest tests/test_bm25.py
```

Run a specific test:
```bash
pytest tests/test_bm25.py::TestBM25SearchStrategy::test_search
```

Format and lint with auto-fix:
```bash
ruff format src tests
ruff check --fix src tests
```

Type check:
```bash
mypy src/sif
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
├── mcp/                    # Legacy functional MCP server
├── mcp_server/             # Refactored OOP MCP server (Transport ABC)
├── core/                   # Domain models, enums, and protocols
├── indexing/               # Document ingestion pipeline
├── search/                 # Search strategies (BM25, Vector, Hybrid)
├── database/               # SQLite connection, schema, repositories
├── embedding/              # Embedding models and factory
├── config/                 # Pydantic Settings
└── utils/                  # Logging, progress tracking, helpers
```

### Key Architectural Patterns

**Repository Pattern:** All database access flows through repository classes in `src/sif/database/repositories.py`. There is also a legacy `src/sif/database/sqlite_repository.py` that should be consolidated and removed. Note: `indexer.py` currently imports `DocumentRepository` from `sif.database.repository` (singular), which may be a stale import.

**Protocol-Based Extensibility:** `src/sif/core/models.py` defines protocols like `Embedder` that decouple search and indexing from specific embedding providers. The embedding factory in `src/sif/embedding/factory.py` currently contains placeholder/random implementations that need to be replaced with real `sentence-transformers` and `llama-cpp-python` loaders.

**Factory Pattern:** `EmbeddingModelFactory` creates model instances based on `ModelType`. `Chunker` hierarchy (`FixedSizeChunker`, `MarkdownChunker`, `CodeChunker`, `AutoChunker`) uses `create_chunker()` factory in `src/sif/indexing/chunker.py`.

**Dual MCP Implementations:** There are two MCP server implementations:
- Legacy: `src/sif/mcp/` — functional style
- Refactored: `src/sif/mcp_server/` — OOP with `Transport` ABC (`StdioTransport`, `HTTPTransport`)

**Search Strategy Pattern:** Each search type is a class in `src/sif/search/`:
- `BM25Searcher` — SQLite FTS5
- `VectorSearcher` — `sqlite-vec` (currently has a Python fallback that should be removed)
- `HybridSearcher` — Combines BM25 + Vector via `RRFFusion`
- `SearchPipeline` — Adds query expansion and reranking

### Data Flow

All persistent state lives in a single SQLite database (default `~/.sif/index.sqlite` or via `Settings.get_db_path()`). The `SchemaManager` in `src/sif/database/schema.py` creates tables, FTS5 virtual tables, and vector tables. FTS5 tables currently lack `content=` configurations and SQLite triggers to keep them synchronized with the main tables.

Embedding models are loaded on demand and cached in `EmbeddingManager._model`.

### Configuration

Settings are defined in `src/sif/config/settings.py` using Pydantic Settings. Environment variables use the `SIF_` prefix (e.g., `SIF_DB_PATH`, `SIF_MODEL_NAME`). Settings are cached via `@lru_cache` in `get_settings()`.

### Error Handling Conventions

- CLI commands raise `click.ClickException(str(e))` for user-facing errors.
- Database transactions use `Database.transaction()` context manager with automatic rollback on exception.
- `HybridSearcher.search()` currently falls back to BM25 on vector search failures — per current phase goals, vector search should fail fast instead of silently falling back.

### Code Style

- Target Python 3.9+; use `list[str] | None` union syntax.
- Line length: 100 (enforced by ruff).
- Max complexity (mccabe): 10.
- Ruff isort with `combine-as-imports = true`.
- Order: stdlib, third-party, first-party (`sif`).
- Two blank lines after imports.
- Type annotations are strict (`disallow_untyped_defs = true`).
- CLI modules relax `disallow_untyped_decorators` for Click decorators.

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
