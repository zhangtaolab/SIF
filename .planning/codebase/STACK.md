# Technology Stack

**Analysis Date:** 2026-04-14

## Languages

**Primary:**
- Python 3.9+ — Entire application codebase

**Secondary:**
- SQL — SQLite schema definitions and queries in `src/docsift/database/schema.py`
- Markdown — Documentation and parsed content format

## Runtime

**Environment:**
- CPython 3.9 / 3.10 / 3.11 / 3.12

**Package Manager:**
- pip (standard)
- Build backend: `hatchling` (defined in `pyproject.toml`)

## Frameworks

**Core:**
- `click>=8.0.0` — CLI framework, entry point at `src/docsift/cli/main.py`
- `rich>=13.0.0` — Terminal formatting and progress indicators
- `pydantic` + `pydantic-settings` — Configuration validation in `src/docsift/config/settings.py`

**Testing:**
- `pytest>=7.0.0` — Test runner
- `pytest-cov>=4.0.0` — Coverage reporting

**Build/Dev:**
- `hatchling` — PEP 517 build backend
- `ruff>=0.1.0` — Linting and formatting
- `black>=23.0.0` — Code formatting (legacy, ruff now handles formatting)
- `mypy>=1.0.0` — Static type checking

## Key Dependencies

**Critical:**
- `click>=8.0.0` — CLI command groups and options in `src/docsift/cli/main.py`
- `rich>=13.0.0` — Tables, progress bars, console output
- `python-frontmatter>=1.0.0` — Markdown YAML frontmatter parsing in `src/docsift/indexing/parser.py`
- `pydantic` + `pydantic-settings` — `Settings` class with env var loading and validators
- `platformdirs` — Cross-platform data/cache directory resolution

**Embedding / ML (optional extras):**
- `sentence-transformers>=2.2.0` — Default embedding backend in `src/docsift/embedding/embedder.py`
- `numpy>=1.24.0` — Vector math and embedding normalization
- `torch` (imported at runtime) — Device selection (CPU/CUDA) for sentence-transformers
- `llama-cpp-python` (runtime import) — GGUF local embedding support in `src/docsift/embedding/embedder.py`
- `modelscope` (runtime import) — Chinese model downloading in `src/docsift/models/download.py`

**MCP Server:**
- `fastapi` (runtime import in `src/docsift/mcp_server/transport.py`) — HTTP transport
- `uvicorn` (runtime import) — ASGI server for MCP HTTP mode

**Search:**
- SQLite FTS5 — Built-in full-text search in `src/docsift/search/bm25.py`
- `sqlite-vec` (optional runtime extension) — Vector similarity in `src/docsift/search/vector.py`

## Configuration

**Environment:**
- Pydantic Settings loads from `.env` and environment variables prefixed with `DOCSIFT_`
- Key settings defined in `src/docsift/config/settings.py`: `db_path`, `model_name`, `embedding_dim`, `mcp_host`, `mcp_port`, `cache_dir`

**Build:**
- `pyproject.toml` — Project metadata, dependencies, tool configs
- `mypy.ini` — Additional mypy configuration
- `Makefile` — Development task shortcuts

## Platform Requirements

**Development:**
- Python >=3.9
- pip with PEP 517 support
- Optional: pre-commit hooks (referenced in Makefile)

**Production:**
- Local CLI execution target
- SQLite database (local filesystem)
- Optional CUDA for GPU-accelerated embeddings

---

*Stack analysis: 2026-04-14*
