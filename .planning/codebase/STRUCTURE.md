# Codebase Structure

**Analysis Date:** 2026-04-14

## Directory Layout

```
/Users/forrest/GitHub/docsift/
├── src/docsift/           # Main source package
│   ├── cli/               # Click commands and formatters
│   ├── config/            # Pydantic settings and constants
│   ├── core/              # Domain models and protocols
│   ├── database/          # SQLite schema, connection, repositories
│   ├── embedding/         # Embedding models, manager, cache
│   ├── indexing/          # File scanning, parsing, chunking, indexer
│   ├── mcp/               # Legacy MCP server implementation
│   ├── mcp_server/        # Refactored MCP server (transport, handlers, tools)
│   ├── models/            # Additional model definitions (download, context, etc.)
│   ├── search/            # BM25, vector, hybrid search, RRF, reranking
│   └── utils/             # Logging, progress, text/path helpers
├── tests/                 # Test suite
│   ├── e2e/               # End-to-end tests
│   ├── integration/       # Integration tests
│   └── unit/              # Unit tests (mirrors source structure)
├── docs/                  # Documentation (MkDocs)
├── examples/              # Example configurations or usage
├── pyproject.toml         # Project metadata, dependencies, tool config
├── mypy.ini               # MyPy configuration
└── mkdocs.yml             # MkDocs site configuration
```

## Directory Purposes

**`src/docsift/cli/`:**
- Purpose: Command-line interface implementation
- Contains: Click groups, command handlers, output formatters
- Key files: `src/docsift/cli/main.py`, `src/docsift/cli/commands/index.py`, `src/docsift/cli/commands/search.py`, `src/docsift/cli/commands/collection.py`

**`src/docsift/core/`:**
- Purpose: Domain models shared across all layers
- Contains: Dataclasses (`Collection`, `Document`, `DocumentChunk`, etc.), enums, protocols
- Key files: `src/docsift/core/models.py`

**`src/docsift/database/`:**
- Purpose: Persistence layer
- Contains: Connection management, schema definitions, repository implementations
- Key files: `src/docsift/database/database.py`, `src/docsift/database/schema.py`, `src/docsift/database/repositories.py`

**`src/docsift/indexing/`:**
- Purpose: Document ingestion pipeline
- Contains: Scanner, parsers, chunkers, indexer orchestrator
- Key files: `src/docsift/indexing/indexer.py`, `src/docsift/indexing/scanner.py`, `src/docsift/indexing/parser.py`, `src/docsift/indexing/chunker.py`

**`src/docsift/search/`:**
- Purpose: Retrieval and ranking implementations
- Contains: BM25, vector, hybrid searchers, RRF fusion, query expansion
- Key files: `src/docsift/search/bm25.py`, `src/docsift/search/vector.py`, `src/docsift/search/hybrid.py`, `src/docsift/search/rrf.py`

**`src/docsift/embedding/`:**
- Purpose: Embedding model lifecycle and caching
- Contains: Manager, model ABC, factory protocol, cache
- Key files: `src/docsift/embedding/manager.py`, `src/docsift/embedding/model.py`

**`src/docsift/mcp/`:**
- Purpose: Legacy MCP server (functional style, fully wired)
- Contains: `MCPServer` class with JSON-RPC handling, stdio runner, HTTP transport variant
- Key files: `src/docsift/mcp/server.py`, `src/docsift/mcp/tools.py`

**`src/docsift/mcp_server/`:**
- Purpose: Refactored MCP server (OOP style, partially wired)
- Contains: Transport ABC, `ToolHandler` ABC, server shell
- Key files: `src/docsift/mcp_server/server.py`, `src/docsift/mcp_server/transport.py`, `src/docsift/mcp_server/handlers.py`, `src/docsift/mcp_server/tools.py`

**`tests/`:**
- Purpose: Automated test coverage
- Contains: e2e, integration, and unit tests
- Key files: `tests/unit/db/`, `tests/unit/indexing/`, `tests/unit/search/`, `tests/unit/cli/`, `tests/unit/inference/`

## Key File Locations

**Entry Points:**
- `src/docsift/cli/main.py`: CLI root command (`docsift`)
- `pyproject.toml` `[project.scripts]`: Declares `docsift = "docsift.cli.main:main"`
- `src/docsift/mcp/server.py`: Legacy MCP stdio entry point (`run_stdio_server()`)

**Configuration:**
- `pyproject.toml`: Build system (hatchling), dependencies, optional extras (`dev`, `embed`, `all`), tool configs (black, ruff, mypy, pytest)
- `src/docsift/config/settings.py`: Runtime `Settings` class (Pydantic)
- `src/docsift/config/constants.py`: App-level constants (chunk sizes, app name)

**Core Logic:**
- `src/docsift/core/models.py`: Domain dataclasses and protocols
- `src/docsift/indexing/indexer.py`: `DocumentIndexer` orchestrator
- `src/docsift/search/hybrid.py`: `HybridSearcher` and `SearchPipeline`
- `src/docsift/embedding/manager.py`: `EmbeddingManager`

**Testing:**
- `tests/unit/`: Unit tests organized by domain
- `pyproject.toml` pytest config: `--cov=src/docsift`, HTML/XML/term reports

## Naming Conventions

**Files:**
- Module names use `snake_case`: `bm25.py`, `chunker.py`, `repositories.py`
- Test files use `test_*.py` pattern

**Directories:**
- Package directories use `snake_case`: `mcp_server/`, `cli/commands/`

**Classes:**
- PascalCase for all classes: `DocumentIndexer`, `BM25Searcher`, `EmbeddingManager`
- Abstract classes often end in ABC or use descriptive names: `Chunker`, `Transport`, `ToolHandler`

**Functions/Variables:**
- snake_case for functions and variables
- Private methods prefixed with `_`: `_index_file()`, `_should_ignore()`

## Where to Add New Code

**New CLI Command:**
- Implementation: `src/docsift/cli/commands/<domain>.py`
- Registration: import and `cli.add_command()` in `src/docsift/cli/main.py`
- Tests: `tests/unit/cli/`

**New Search Strategy:**
- Implementation: `src/docsift/search/<strategy_name>.py`
- Integration: wire into `src/docsift/search/hybrid.py` or call directly from CLI/MCP
- Tests: `tests/unit/search/`

**New Chunking Strategy:**
- Implementation: subclass `Chunker` in `src/docsift/indexing/chunker.py`
- Registration: add case to `create_chunker()` factory in same file
- Tests: `tests/unit/indexing/`

**New Database Entity:**
- Schema: `src/docsift/database/schema.py` (`SchemaManager`)
- Model: `src/docsift/core/models.py` (dataclass)
- Repository: `src/docsift/database/repositories.py`
- Tests: `tests/unit/db/`

**New MCP Tool:**
- Legacy server: add handler in `src/docsift/mcp/server.py` (`_tool_*` method) and register in `_handle_tools_list()`
- Refactored server: subclass `ToolHandler` in `src/docsift/mcp_server/tools.py`, register in `src/docsift/mcp_server/server.py`

**Utilities:**
- Shared helpers: `src/docsift/utils/<topic>.py`
- Import via `from docsift.utils.logging import get_logger`

## Special Directories

**`src/docsift/mcp/` (Legacy):**
- Purpose: Functional MCP server that is currently active in CLI (`docsift mcp serve`)
- Generated: No
- Committed: Yes

**`src/docsift/mcp_server/` (Refactored):**
- Purpose: Object-oriented MCP server refactor (not yet fully wired into CLI)
- Generated: No
- Committed: Yes
- Note: Exists alongside legacy `mcp/`; migration in progress

**`tests/`:**
- Purpose: All automated tests
- Generated: No
- Committed: Yes

---

*Structure analysis: 2026-04-14*
