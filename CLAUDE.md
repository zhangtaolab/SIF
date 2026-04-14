<!-- GSD:project-start source:PROJECT.md -->
## Project

**DocSift**

DocSift 是 [qmd](https://github.com/tobi/qmd) 的 Python 重构版本，一个面向个人知识库的**本地混合搜索引擎**。它索引 Markdown 笔记、文档和会议纪要，支持关键词搜索（BM25）、语义向量搜索（Vector Search），以及基于 LLM 的重排序（Rerank）和查询扩展。同时提供 CLI 工具和 MCP（Model Context Protocol）服务器两种使用方式，完全在本地运行，无需外部 API。

**Core Value:** 用户可以在自己的笔记和文档库中，用自然语言快速、准确地找到需要的信息——无论关键词是否匹配。

### Constraints

- **Tech Stack**: Python 3.9+、SQLite（FTS5 + 可选 sqlite-vec）、Click CLI、Pydantic Settings
- **Local-First**: 默认所有模型本地运行，不依赖外部 API；API 调用仅作为可选配置
- **Compatibility**: CLI 接口和 MCP Tool Schema 尽量与 qmd 保持一致
- **Build**: hatchling 构建后端，pytest 测试
<!-- GSD:project-end -->

<!-- GSD:stack-start source:codebase/STACK.md -->
## Technology Stack

## Languages
- Python 3.9+ — Entire application codebase
- SQL — SQLite schema definitions and queries in `src/docsift/database/schema.py`
- Markdown — Documentation and parsed content format
## Runtime
- CPython 3.9 / 3.10 / 3.11 / 3.12
- pip (standard)
- Build backend: `hatchling` (defined in `pyproject.toml`)
## Frameworks
- `click>=8.0.0` — CLI framework, entry point at `src/docsift/cli/main.py`
- `rich>=13.0.0` — Terminal formatting and progress indicators
- `pydantic` + `pydantic-settings` — Configuration validation in `src/docsift/config/settings.py`
- `pytest>=7.0.0` — Test runner
- `pytest-cov>=4.0.0` — Coverage reporting
- `hatchling` — PEP 517 build backend
- `ruff>=0.1.0` — Linting and formatting
- `black>=23.0.0` — Code formatting (legacy, ruff now handles formatting)
- `mypy>=1.0.0` — Static type checking
## Key Dependencies
- `click>=8.0.0` — CLI command groups and options in `src/docsift/cli/main.py`
- `rich>=13.0.0` — Tables, progress bars, console output
- `python-frontmatter>=1.0.0` — Markdown YAML frontmatter parsing in `src/docsift/indexing/parser.py`
- `pydantic` + `pydantic-settings` — `Settings` class with env var loading and validators
- `platformdirs` — Cross-platform data/cache directory resolution
- `sentence-transformers>=2.2.0` — Default embedding backend in `src/docsift/embedding/embedder.py`
- `numpy>=1.24.0` — Vector math and embedding normalization
- `torch` (imported at runtime) — Device selection (CPU/CUDA) for sentence-transformers
- `llama-cpp-python` (runtime import) — GGUF local embedding support in `src/docsift/embedding/embedder.py`
- `modelscope` (runtime import) — Chinese model downloading in `src/docsift/models/download.py`
- `fastapi` (runtime import in `src/docsift/mcp_server/transport.py`) — HTTP transport
- `uvicorn` (runtime import) — ASGI server for MCP HTTP mode
- SQLite FTS5 — Built-in full-text search in `src/docsift/search/bm25.py`
- `sqlite-vec` (optional runtime extension) — Vector similarity in `src/docsift/search/vector.py`
## Configuration
- Pydantic Settings loads from `.env` and environment variables prefixed with `DOCSIFT_`
- Key settings defined in `src/docsift/config/settings.py`: `db_path`, `model_name`, `embedding_dim`, `mcp_host`, `mcp_port`, `cache_dir`
- `pyproject.toml` — Project metadata, dependencies, tool configs
- `mypy.ini` — Additional mypy configuration
- `Makefile` — Development task shortcuts
## Platform Requirements
- Python >=3.9
- pip with PEP 517 support
- Optional: pre-commit hooks (referenced in Makefile)
- Local CLI execution target
- SQLite database (local filesystem)
- Optional CUDA for GPU-accelerated embeddings
<!-- GSD:stack-end -->

<!-- GSD:conventions-start source:CONVENTIONS.md -->
## Conventions

## Naming Patterns
- Modules use `snake_case`: `chunker.py`, `test_repositories.py`
- Test files prefixed with `test_`: `test_bm25.py`, `test_chunker.py`
- `__init__.py` for package initialization
- Use `snake_case` for all functions and methods
- Private helpers use leading underscore: `_create_collections_table()`
- CLI commands use descriptive names: `search_cmd`, `query_cmd`
- `snake_case` throughout
- Type variables use single uppercase: `T = TypeVar("T")`
- Private instance variables use leading underscore: `self._collections`
- `PascalCase` for all classes
- Abstract base classes often include `ABC` or are named descriptively: `Repository`, `SearchStrategy`
- Test classes prefixed with `Test`: `TestBM25SearchStrategy`
- Union syntax uses `|` (Python 3.9+): `str | None`, `list[str] | None`
- `Optional[T]` also appears in older code: `Optional[str]`
- Prefer `list[str]` over `List[str]` in newer modules
## Code Style
- **Black** with `line-length = 100`
- Target Python 3.9+
- Double quotes for strings, including docstrings
- **Ruff** with extensive rule set (E, F, W, I, N, D, UP, B, C4, SIM, C90, A, COM, T20, PT, Q, SLF, RET, TID, ARG, FIX, ERA, PL, PERF, RUF)
- Max complexity (mccabe): 10
- Per-file ignores:
- Ruff isort with `combine-as-imports = true`
- Order: stdlib, third-party, first-party (`docsift`)
- Two blank lines after imports
## Docstrings
- Public modules and packages are NOT required to have docstrings (`D100`, `D104` ignored)
- Imperative mood in first line is NOT enforced (`D401` ignored)
- Docstring section formatting is relaxed (`D406`, `D407`, `D413` ignored)
## Type Annotations
- `disallow_untyped_defs = true`
- `disallow_incomplete_defs = true`
- `check_untyped_defs = true`
- `strict = true`
- CLI modules (`src/docsift/cli.*`) relax `disallow_untyped_decorators` for Click decorators
- Third-party libraries without stubs are ignored: `click`, `rich`, `sentence_transformers`, `numpy`, `pytest`
## Error Handling
- Use exceptions for error flow; no heavy use of Result/Either types
- Click exceptions in CLI: `raise click.ClickException(str(e))`
- Graceful degradation with console messages:
- SQLite operational errors caught for optional features (e.g., `sqlite-vec` availability check)
## Logging
- Get module-level logger: `logger = get_logger(__name__)`
- Logger names are prefixed with `docsift`: `docsift.module_name`
- Root logger `docsift` is configured via `setup_logging()`
- Output goes to `stderr` via `StreamHandler`
- Simple format for INFO/WARNING; detailed format for DEBUG/ERROR
## Import Style
## Function Design
- Use dataclasses/option objects for complex parameter groups (e.g., `SearchOptions`)
- CLI options map directly to Click decorators
- Always annotated
- Collections returned as `list[T]`
- Optional returns as `T | None`
## Module Design
- `__all__` defined in package `__init__.py` files (e.g., `src/docsift/__init__.py`)
- Package `__init__.py` re-exports key public types
- No heavy use of `import *`
## CLI Patterns
- Subcommands organized in `src/docsift/cli/commands/`
- Commands registered on a group:
- Shared context object stores `index_path`, `config_path`, `verbose`, `quiet`
<!-- GSD:conventions-end -->

<!-- GSD:architecture-start source:ARCHITECTURE.md -->
## Architecture

## Pattern Overview
- Clean separation between CLI commands, core domain logic, and infrastructure
- Protocol-based abstractions (`Embedder`, `Reranker`, `QueryExpander`) for extensibility
- Repository pattern for database access
- Factory pattern for embedding model creation and chunking strategy selection
- Dual MCP server implementations (legacy `mcp/` and refactored `mcp_server/`)
## Layers
- Purpose: User-facing command-line interface
- Location: `src/docsift/cli/`
- Contains: Click command groups, argument parsing, output formatters
- Depends on: `database`, `search`, `indexing`, `core.models`
- Used by: End users via `docsift` entry point (`pyproject.toml` scripts)
- Purpose: Model Context Protocol server for AI assistant integration
- Location: `src/docsift/mcp/` (legacy functional) and `src/docsift/mcp_server/` (refactored OOP)
- Contains: JSON-RPC request handlers, tool definitions, transport implementations (stdio, HTTP)
- Depends on: `database`, `search`, `core.models`
- Used by: MCP clients (e.g., Claude Desktop)
- Purpose: Domain models, enums, and protocols
- Location: `src/docsift/core/`
- Contains: `Collection`, `Document`, `DocumentChunk`, `PathContext`, `SearchResult`, `SearchOptions`, `Embedder` protocol
- Depends on: Python stdlib only
- Used by: All other layers
- Purpose: Document ingestion pipeline
- Location: `src/docsift/indexing/`
- Contains: `DocumentIndexer` (orchestrator), `FileScanner`, `MarkdownParser`/`TextParser`/`CodeParser`, `Chunker` hierarchy
- Depends on: `core`, `database.repositories`, `embedding.manager`, `utils`
- Used by: CLI (`index` commands), MCP tools
- Purpose: Retrieval and ranking
- Location: `src/docsift/search/`
- Contains: `BM25Searcher`, `VectorSearcher`, `HybridSearcher`, `SearchPipeline`, `RRFFusion`
- Depends on: `core.models`, SQLite (FTS5, optional sqlite-vec)
- Used by: CLI (`search`, `query`, `vsearch` commands), MCP server
- Purpose: Persistence and schema management
- Location: `src/docsift/database/`
- Contains: `Database` connection manager, `SchemaManager`, repository classes (`CollectionRepository`, `DocumentRepository`, `DocumentChunkRepository`, `PathContextRepository`, `LLMCacheRepository`)
- Depends on: `sqlite3`, `core.models`
- Used by: Indexing, search, CLI, MCP
- Purpose: Vector generation and model lifecycle
- Location: `src/docsift/embedding/`
- Contains: `EmbeddingManager`, `EmbeddingModel` ABC, `EmbeddingModelFactory` protocol, `EmbeddingCache`
- Depends on: `config.settings`, `models.embedding`, optional `sentence-transformers`
- Used by: Indexing pipeline, hybrid search
- Purpose: Application configuration
- Location: `src/docsift/config/`
- Contains: `Settings` (Pydantic Settings), constants
- Depends on: `pydantic_settings`, `platformdirs`
- Used by: Embedding manager, CLI context
- Purpose: Cross-cutting concerns
- Location: `src/docsift/utils/`
- Contains: `get_logger`/`setup_logging`, `ProgressTracker`, text/path helpers
- Depends on: `rich`, `logging`
- Used by: All layers
## Data Flow
- All persistent state lives in a single SQLite database (default: `~/.docsift/index.sqlite`)
- No in-memory application state beyond CLI context (`click.Context.obj`)
- Embedding models are loaded on demand and cached in `EmbeddingManager._model`
## Key Abstractions
- Purpose: Decouple search/indexing from specific embedding providers
- Location: `src/docsift/core/models.py`
- Pattern: `Protocol` with `embed()`, `embed_batch()`, `dimension` property
- Purpose: Pluggable document segmentation
- Examples: `src/docsift/indexing/chunker.py` (`FixedSizeChunker`, `MarkdownChunker`, `CodeChunker`, `AutoChunker`)
- Pattern: Abstract base class with `create_chunker()` factory
- Purpose: Encapsulate SQLite CRUD and row mapping
- Examples: `src/docsift/database/repositories.py`
- Pattern: One repository per aggregate root (`Collection`, `Document`, `DocumentChunk`, `PathContext`)
- Purpose: Interchangeable search algorithms
- Examples: `src/docsift/search/bm25.py`, `src/docsift/search/vector.py`, `src/docsift/search/hybrid.py`
- Pattern: Class-per-strategy, each accepts `sqlite3.Connection` and `SearchOptions`
- Purpose: Decouple MCP server from I/O mechanism
- Examples: `src/docsift/mcp_server/transport.py` (`StdioTransport`, `HTTPTransport`)
- Pattern: Abstract base class with `start()`, `stop()`, `send()`, `receive()`
## Entry Points
- Location: `src/docsift/cli/main.py`
- Triggers: `docsift` console script (`pyproject.toml`)
- Responsibilities: Setup logging, parse global options (`--index`, `--config`, `--verbose`), dispatch to subcommand groups
- Location: `src/docsift/mcp/server.py` (`run_stdio_server()`)
- Triggers: `docsift mcp serve` or direct invocation
- Responsibilities: Initialize `MCPServer`, read JSON-RPC from stdin, write responses to stdout
- Location: `src/docsift/mcp_server/transport.py` (`HTTPTransport.start()`)
- Triggers: `docsift mcp serve --transport http`
- Responsibilities: Start FastAPI/uvicorn server on configured host/port
## Error Handling
- Vector search failures fall back to BM25 (`HybridSearcher.search()`)
- Query expansion failures are logged and ignored (`SearchPipeline.search()`)
- Reranking failures return original results (`HybridSearcher.search_with_reranking()`)
- CLI commands raise `click.ClickException` for user-facing errors
- Database transactions use context manager with automatic rollback on exception (`Database.transaction()`)
## Cross-Cutting Concerns
<!-- GSD:architecture-end -->

<!-- GSD:skills-start source:skills/ -->
## Project Skills

No project skills found. Add skills to any of: `.claude/skills/`, `.agents/skills/`, `.cursor/skills/`, or `.github/skills/` with a `SKILL.md` index file.
<!-- GSD:skills-end -->

<!-- GSD:workflow-start source:GSD defaults -->
## GSD Workflow Enforcement

Before using Edit, Write, or other file-changing tools, start work through a GSD command so planning artifacts and execution context stay in sync.

Use these entry points:
- `/gsd-quick` for small fixes, doc updates, and ad-hoc tasks
- `/gsd-debug` for investigation and bug fixing
- `/gsd-execute-phase` for planned phase work

Do not make direct repo edits outside a GSD workflow unless the user explicitly asks to bypass it.

### Quality Gate

After every plan completes within a phase, run the full quality suite before marking it done:

```bash
ruff check src tests
ruff format --check src tests
pytest
```

Fix any failures before continuing to the next plan or phase.
<!-- GSD:workflow-end -->



<!-- GSD:profile-start -->
## Developer Profile

> Profile not yet configured. Run `/gsd-profile-user` to generate your developer profile.
> This section is managed by `generate-claude-profile` -- do not edit manually.
<!-- GSD:profile-end -->
