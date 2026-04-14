# Architecture

**Analysis Date:** 2026-04-14

## Pattern Overview

**Overall:** Layered modular architecture with a CLI/MCP dual-interface and a pipeline-based indexing/search flow.

**Key Characteristics:**
- Clean separation between CLI commands, core domain logic, and infrastructure
- Protocol-based abstractions (`Embedder`, `Reranker`, `QueryExpander`) for extensibility
- Repository pattern for database access
- Factory pattern for embedding model creation and chunking strategy selection
- Dual MCP server implementations (legacy `mcp/` and refactored `mcp_server/`)

## Layers

**CLI Layer:**
- Purpose: User-facing command-line interface
- Location: `src/docsift/cli/`
- Contains: Click command groups, argument parsing, output formatters
- Depends on: `database`, `search`, `indexing`, `core.models`
- Used by: End users via `docsift` entry point (`pyproject.toml` scripts)

**MCP Layer:**
- Purpose: Model Context Protocol server for AI assistant integration
- Location: `src/docsift/mcp/` (legacy functional) and `src/docsift/mcp_server/` (refactored OOP)
- Contains: JSON-RPC request handlers, tool definitions, transport implementations (stdio, HTTP)
- Depends on: `database`, `search`, `core.models`
- Used by: MCP clients (e.g., Claude Desktop)

**Core Domain Layer:**
- Purpose: Domain models, enums, and protocols
- Location: `src/docsift/core/`
- Contains: `Collection`, `Document`, `DocumentChunk`, `PathContext`, `SearchResult`, `SearchOptions`, `Embedder` protocol
- Depends on: Python stdlib only
- Used by: All other layers

**Indexing Layer:**
- Purpose: Document ingestion pipeline
- Location: `src/docsift/indexing/`
- Contains: `DocumentIndexer` (orchestrator), `FileScanner`, `MarkdownParser`/`TextParser`/`CodeParser`, `Chunker` hierarchy
- Depends on: `core`, `database.repositories`, `embedding.manager`, `utils`
- Used by: CLI (`index` commands), MCP tools

**Search Layer:**
- Purpose: Retrieval and ranking
- Location: `src/docsift/search/`
- Contains: `BM25Searcher`, `VectorSearcher`, `HybridSearcher`, `SearchPipeline`, `RRFFusion`
- Depends on: `core.models`, SQLite (FTS5, optional sqlite-vec)
- Used by: CLI (`search`, `query`, `vsearch` commands), MCP server

**Database Layer:**
- Purpose: Persistence and schema management
- Location: `src/docsift/database/`
- Contains: `Database` connection manager, `SchemaManager`, repository classes (`CollectionRepository`, `DocumentRepository`, `DocumentChunkRepository`, `PathContextRepository`, `LLMCacheRepository`)
- Depends on: `sqlite3`, `core.models`
- Used by: Indexing, search, CLI, MCP

**Embedding Layer:**
- Purpose: Vector generation and model lifecycle
- Location: `src/docsift/embedding/`
- Contains: `EmbeddingManager`, `EmbeddingModel` ABC, `EmbeddingModelFactory` protocol, `EmbeddingCache`
- Depends on: `config.settings`, `models.embedding`, optional `sentence-transformers`
- Used by: Indexing pipeline, hybrid search

**Config Layer:**
- Purpose: Application configuration
- Location: `src/docsift/config/`
- Contains: `Settings` (Pydantic Settings), constants
- Depends on: `pydantic_settings`, `platformdirs`
- Used by: Embedding manager, CLI context

**Utils Layer:**
- Purpose: Cross-cutting concerns
- Location: `src/docsift/utils/`
- Contains: `get_logger`/`setup_logging`, `ProgressTracker`, text/path helpers
- Depends on: `rich`, `logging`
- Used by: All layers

## Data Flow

**Indexing Flow:**

1. CLI `index update` or MCP `index` tool triggers indexing
2. `CollectionRepository` loads target collection(s)
3. `FileScanner.scan()` discovers files on disk
4. `MarkdownParser`/`CodeParser`/`TextParser` extracts content, title, metadata, checksum
5. `DocumentIndexer` checks checksums to skip unchanged files
6. `Chunker` (fixed/markdown/code/auto) splits content into `DocumentChunk`s
7. `EmbeddingManager.embed()` generates vectors (optional, via `sentence-transformers`)
8. `DocumentRepository`, `DocumentChunkRepository` persist to SQLite
9. FTS5 virtual tables (`documents_fts`, `chunks_fts`) and optional `document_embeddings` (sqlite-vec) are updated

**Search Flow:**

1. CLI `search` / `query` or MCP `query` receives query string
2. `SearchOptions` is built with limit, collections filter, content/highlight flags
3. `BM25Searcher` queries `documents_fts` using `MATCH` with Porter tokenizer
4. If embedder available, `VectorSearcher` queries `document_embeddings` (sqlite-vec or fallback cosine similarity)
5. `HybridSearcher` fuses BM25 and vector results via `RRFFusion` (Reciprocal Rank Fusion, k=60)
6. `SearchPipeline` optionally expands queries and applies reranking
7. Results are formatted (rich table, JSON, CSV, Markdown, XML) and returned

**State Management:**
- All persistent state lives in a single SQLite database (default: `~/.docsift/index.sqlite`)
- No in-memory application state beyond CLI context (`click.Context.obj`)
- Embedding models are loaded on demand and cached in `EmbeddingManager._model`

## Key Abstractions

**Embedder Protocol:**
- Purpose: Decouple search/indexing from specific embedding providers
- Location: `src/docsift/core/models.py`
- Pattern: `Protocol` with `embed()`, `embed_batch()`, `dimension` property

**Chunker ABC:**
- Purpose: Pluggable document segmentation
- Examples: `src/docsift/indexing/chunker.py` (`FixedSizeChunker`, `MarkdownChunker`, `CodeChunker`, `AutoChunker`)
- Pattern: Abstract base class with `create_chunker()` factory

**Repository Pattern:**
- Purpose: Encapsulate SQLite CRUD and row mapping
- Examples: `src/docsift/database/repositories.py`
- Pattern: One repository per aggregate root (`Collection`, `Document`, `DocumentChunk`, `PathContext`)

**Search Strategy:**
- Purpose: Interchangeable search algorithms
- Examples: `src/docsift/search/bm25.py`, `src/docsift/search/vector.py`, `src/docsift/search/hybrid.py`
- Pattern: Class-per-strategy, each accepts `sqlite3.Connection` and `SearchOptions`

**Transport ABC (MCP):**
- Purpose: Decouple MCP server from I/O mechanism
- Examples: `src/docsift/mcp_server/transport.py` (`StdioTransport`, `HTTPTransport`)
- Pattern: Abstract base class with `start()`, `stop()`, `send()`, `receive()`

## Entry Points

**CLI Entry Point:**
- Location: `src/docsift/cli/main.py`
- Triggers: `docsift` console script (`pyproject.toml`)
- Responsibilities: Setup logging, parse global options (`--index`, `--config`, `--verbose`), dispatch to subcommand groups

**MCP stdio Entry Point:**
- Location: `src/docsift/mcp/server.py` (`run_stdio_server()`)
- Triggers: `docsift mcp serve` or direct invocation
- Responsibilities: Initialize `MCPServer`, read JSON-RPC from stdin, write responses to stdout

**MCP HTTP Entry Point:**
- Location: `src/docsift/mcp_server/transport.py` (`HTTPTransport.start()`)
- Triggers: `docsift mcp serve --transport http`
- Responsibilities: Start FastAPI/uvicorn server on configured host/port

## Error Handling

**Strategy:** Graceful degradation with warnings printed to stdout.

**Patterns:**
- Vector search failures fall back to BM25 (`HybridSearcher.search()`)
- Query expansion failures are logged and ignored (`SearchPipeline.search()`)
- Reranking failures return original results (`HybridSearcher.search_with_reranking()`)
- CLI commands raise `click.ClickException` for user-facing errors
- Database transactions use context manager with automatic rollback on exception (`Database.transaction()`)

## Cross-Cutting Concerns

**Logging:** `docsift.utils.logging.get_logger(__name__)` returns namespaced loggers under `docsift` root; `setup_logging()` configures `StreamHandler(stderr)` with format based on log level.

**Validation:** Pydantic `Settings` validates env vars and paths; `field_validator` expands `~` in `db_path` and `cache_dir`.

**Authentication:** Not applicable — local-only tool with no auth layer.

---

*Architecture analysis: 2026-04-14*
