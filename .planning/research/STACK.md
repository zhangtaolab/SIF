# Technology Stack

**Project:** DocSift
**Researched:** 2026-04-14

## Recommended Stack

### Core Framework

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| Python | 3.10+ (keep 3.9 syntax compat) | Runtime | `llama-cpp-python` 0.3.20 only provides pre-built wheels for Python 3.10–3.12. Source builds work on 3.9 but require a full C++ toolchain, which is a poor out-of-box experience for a local CLI tool. DocSift should target 3.10+ while keeping 3.9-compatible syntax where possible. |
| `click` | >=8.0.0 | CLI framework | Already integrated; stable, well-documented, and supports command groups nested exactly like qmd's CLI structure. |
| `pydantic` + `pydantic-settings` | >=2.0 | Config validation | Existing codebase uses this for `Settings` class with env-var loading. Pydantic v2 is now the de facto standard. |
| `rich` | >=13.0.0 | Terminal formatting | Powers tables, progress bars, and console output. Already integrated and widely used in the Python CLI ecosystem. |

### Database / Search

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| SQLite (built-in) | — | Relational + FTS5 full-text search | Zero dependencies, single-file database, already used for BM25 via FTS5. |
| `sqlite-vec` | >=0.1.9 | Vector similarity search inside SQLite | The cleanest local-first vector search option for SQLite in 2025. Stores vectors in the same DB file, enables hybrid SQL queries combining FTS5 + vector KNN, and has zero external server requirements. Brute-force KNN is acceptable for personal knowledge-base scale (thousands to low-hundreds-of-thousands of chunks). |

### Embedding / Local ML

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| `sentence-transformers` | >=5.4.0 | Default embedding backend | HuggingFace-maintained, batched inference, GPU auto-acceleration, and supports the best open-source embedding models of 2025 (BGE-M3, Snowflake Arctic-Embed, all-MiniLM-L6-v2). v5.4.0 is the latest stable with no hard deprecations. |
| `llama-cpp-python` | >=0.3.20 | GGUF local embedding + reranking | The canonical Python binding for `llama.cpp`. v0.3.20 adds native reranking support via `LlamaEmbedding` with `LLAMA_POOLING_TYPE_RANK`, which is exactly what DocSift needs to replicate qmd's local LLM rerank behavior. Also supports GGUF-based embeddings for users who prefer that over sentence-transformers. |
| `numpy` | >=1.24.0 | Vector math, normalization | Required by both sentence-transformers and sqlite-vec. Keep at 1.24+ for modern typing support. |

### MCP Server

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| `fastmcp` | >=3.2.4 | High-level MCP server framework | The dominant Python MCP framework in 2025. Decorator-based API (`@mcp.tool`), automatic Pydantic schema generation, async support, and built-in stdio + HTTP+SSE transports. v3.2.4 is the latest stable release under PrefectHQ. Replaces the current low-level MCP scaffolding and unifies the legacy `mcp/` and `mcp_server/` code paths. |
| `mcp` (official SDK) | >=1.25.0 | Underlying protocol implementation | Pulled in as a transitive dependency of `fastmcp`. Needed only if we ever need to drop down to low-level protocol primitives. |

### Supporting Libraries

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `python-frontmatter` | >=1.0.0 | Markdown YAML frontmatter parsing | Already used in the parser. Keep it. |
| `platformdirs` | >=3.0.0 | Cross-platform data/cache directories | Already used for cache and DB path resolution. |
| `huggingface-hub` | >=0.23.0 | Model downloading | Required by sentence-transformers; also useful for explicit model cache management. |

## What NOT to Use and Why

| Technology | Why Avoid | What to Do Instead |
|------------|-----------|-------------------|
| **ChromaDB** | Adds a separate vector database process/file format. Overkill for a local-first, single-user SQLite-based tool. | Use `sqlite-vec` inside the existing SQLite database. |
| **FAISS** | No persistence layer; requires manual serialization and doesn't integrate with SQL queries. | Use `sqlite-vec` for simplicity, or fall back to brute-force numpy only if sqlite-vec is unavailable. |
| **LanceDB** | Excellent for large-scale multimodal RAG, but introduces a second storage engine and query language. Unnecessary complexity for personal note vaults. | Use `sqlite-vec` until scale demands otherwise. |
| **txtai** | All-in-one framework that hides the DB + vector index wiring. DocSift already has its own architecture; adopting txtai would mean rewriting the search layer. | Keep the existing repository/searcher pattern and plug `sqlite-vec` into `vector.py`. |
| **Raw `mcp` SDK without `fastmcp`** | Requires significantly more boilerplate for tool registration, schema generation, and transport wiring. | Use `fastmcp` as the primary framework; drop to raw SDK only for edge cases. |
| **ollama / open-source API-only embedding services** | DocSift's core value is "completely local, no external API." Relying on ollama as a *required* dependency breaks the zero-network promise. | Support ollama/OpenAI-compatible APIs only as *optional* fallbacks; default to `sentence-transformers` and `llama-cpp-python`. |

## Installation

```bash
# Core runtime
pip install click>=8.0.0 rich>=13.0.0 pydantic>=2.0 pydantic-settings>=2.0 \
    python-frontmatter>=1.0.0 platformdirs>=3.0.0 numpy>=1.24.0

# Search
pip install sqlite-vec>=0.1.9

# Embedding (choose one or both)
pip install sentence-transformers>=5.4.0 huggingface-hub>=0.23.0
pip install llama-cpp-python>=0.3.20

# MCP server
pip install fastmcp>=3.2.4

# Dev dependencies
pip install pytest>=7.0.0 pytest-cov>=4.0.0 ruff>=0.1.0 mypy>=1.0.0
```

## Version & Compatibility Notes

- **`llama-cpp-python` 0.3.20**: No pre-built wheels for Python 3.9 (only 3.10–3.12). If the project insists on 3.9, users must compile from source. **Recommendation: bump minimum Python to 3.10.**
- **`fastmcp` 3.2.4**: Major v3 rewrite under PrefectHQ. API surface (`@mcp.tool`, `@mcp.resource`) is largely backward-compatible with v2, but internal imports changed. If existing code imports from old paths, a small migration is needed.
- **`sentence-transformers` 5.4.0**: No hard deprecations vs. 5.2.x. Existing `model.encode()` calls work unchanged.
- **`sqlite-vec` 0.1.9**: Supports Python 3.9+. Requires SQLite 3.41+ for all features. macOS ARM64 and Linux x86_64 wheels are available; Windows users may need to ensure MSVC redistributables are present.

## Confidence Levels

| Recommendation | Confidence | Notes |
|----------------|------------|-------|
| `sqlite-vec` for vector search | **HIGH** | Verified via PyPI (0.1.9), official docs, and dry-run install. Fits the local-first SQLite architecture perfectly. |
| `sentence-transformers` 5.4.0 as default embedder | **HIGH** | Verified via PyPI, dry-run install, and ecosystem consensus. The standard Python embedding library. |
| `llama-cpp-python` 0.3.20 for GGUF + rerank | **HIGH** | Verified via PyPI, dry-run install, and multiple sources confirming `LlamaEmbedding` + `LLAMA_POOLING_TYPE_RANK` in v0.3.19+. |
| `fastmcp` 3.2.4 for MCP server | **HIGH** | Verified via PyPI, dry-run install, and ecosystem consensus. The leading Python MCP framework in 2025. |
| Python 3.10+ minimum | **HIGH** | Verified by attempting `pip install llama-cpp-python==0.3.20` on Python 3.12; only source tarball exists for 3.9, no wheel. |

## Sources

- [llama-cpp-python PyPI](https://pypi.org/project/llama-cpp-python/) — latest version 0.3.20
- [sqlite-vec PyPI](https://pypi.org/project/sqlite-vec/) — latest version 0.1.9
- [fastmcp PyPI](https://pypi.org/project/fastmcp/) — latest version 3.2.4
- [sentence-transformers PyPI](https://pypi.org/project/sentence-transformers/) — latest version 5.4.0
- [sqlite-vec Official Docs](https://alexgarcia.xyz/sqlite-vec/)
- [FastMCP Documentation](https://gofastmcp.com/)
- [llama-cpp-python Changelog / ReadTheDocs](https://llama-cpp-python.readthedocs.io/)
- [Sentence Transformers Documentation](https://sbert.net/)
