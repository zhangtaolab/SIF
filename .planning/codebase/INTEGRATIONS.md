# External Integrations

**Analysis Date:** 2026-04-14

## APIs & External Services

**Embedding Model Providers:**
- HuggingFace Hub — Default model source for `sentence-transformers`
  - SDK: `sentence-transformers` (runtime import in `src/docsift/embedding/embedder.py`)
  - Default model: `BAAI/bge-small-zh-v1.5` (configurable via `Settings.model_name`)
- ModelScope (Alibaba) — Chinese model download source
  - SDK: `modelscope` (runtime import in `src/docsift/models/download.py`)
  - Default model: `iic/gte_Qwen2-7B-instruct`
- OpenAI API — Supported in model type enum but not yet implemented (`src/docsift/embedding/factory.py` raises `NotImplementedError`)

**MCP Protocol:**
- Model Context Protocol (MCP) server implementation in `src/docsift/mcp_server/`
  - Transports: stdio (`src/docsift/mcp_server/transport.py`) and HTTP (`src/docsift/mcp_server/transport.py` using FastAPI + uvicorn)
  - Tools: search, index, collection management (`src/docsift/mcp_server/tools.py`)

## Data Storage

**Databases:**
- SQLite — Primary data store
  - Connection: `db_path` setting or auto-generated via `platformdirs.user_data_dir`
  - Client: Python built-in `sqlite3` module in `src/docsift/database/database.py`
  - Schema manager: `src/docsift/database/schema.py`
  - Features: FTS5 virtual tables, optional `sqlite-vec` extension for vector search

**File Storage:**
- Local filesystem only — Document collections, model cache, and database files
- Default model cache: `~/.docsift/models` (configurable)
- Default database: platform-specific data directory via `platformdirs`

**Caching:**
- Embedding cache — `src/docsift/embedding/cache.py` (filesystem-based, keyed by text hash)
- LLM response cache — SQLite table `llm_cache` in schema (`src/docsift/database/schema.py`)

## Authentication & Identity

**Auth Provider:**
- Not applicable — Local-first CLI tool with no user authentication system
- No API keys stored in codebase (OpenAI integration placeholder only)

## Monitoring & Observability

**Error Tracking:**
- None — Standard Python logging only

**Logs:**
- Python `logging` module configured in `src/docsift/utils/logging.py`
- Logs to `sys.stderr` with configurable level via `DOCSIFT_LOG_LEVEL`

## CI/CD & Deployment

**Hosting:**
- PyPI distribution target (wheel + sdist via hatchling)
- Local CLI installation via `pip`, `pipx`, or editable install

**CI Pipeline:**
- Makefile targets for lint (`ruff`), typecheck (`mypy`), test (`pytest`), security (`bandit`)
- No CI configuration files detected in repository

## Environment Configuration

**Required env vars:**
- None strictly required — all settings have defaults
- Common overrides:
  - `DOCSIFT_DB_PATH` — SQLite database location
  - `DOCSIFT_MODEL_NAME` — Embedding model identifier
  - `DOCSIFT_CACHE_DIR` — Model and embedding cache directory
  - `DOCSIFT_MCP_HOST` / `DOCSIFT_MCP_PORT` — MCP HTTP server binding

**Secrets location:**
- `.env` file supported by Pydantic Settings (existence noted, contents not inspected)
- No dedicated secrets manager integration

## Webhooks & Callbacks

**Incoming:**
- None

**Outgoing:**
- None — all network calls are outbound model downloads (HuggingFace / ModelScope)

## Third-Party Libraries (Runtime Imports)

**Conditionally imported (graceful degradation if missing):**
- `sentence_transformers` — Required for transformer-based embeddings
- `llama_cpp` — Required for GGUF embeddings
- `modelscope` — Required for ModelScope model downloads
- `torch` — Used for CUDA detection in `SentenceTransformerEmbedder`
- `fastapi` / `uvicorn` — Required for MCP HTTP transport

**Note:** The application is designed to function in a reduced mode (TF-IDF fallback embedder, stdio MCP transport) when optional ML dependencies are absent.

---

*Integration audit: 2026-04-14*
