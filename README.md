<!-- generated-by: gsd-doc-writer -->
# SIF

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Code style: ruff](https://img.shields.io/badge/code%20style-ruff-000000.svg)](https://github.com/astral-sh/ruff)

**SIF** = **S**earch / **I**ndex / **F**ind

SIF is a local hybrid search engine for personal knowledge bases. It indexes Markdown notes and documents, combining BM25 keyword search, semantic vector search, and hybrid ranking behind both a `sif` CLI and a Model Context Protocol (MCP) server. All data stays on your machine in a single SQLite database.

## Features

- **Full-Text Search**: BM25 ranking via SQLite FTS5
- **Semantic Search**: Vector similarity using sqlite-vec and configurable embeddings
- **Hybrid Search**: Combines BM25 and vector search with weighted RRF fusion
- **Query Expansion**: Embedding-based pseudo-relevance feedback in hybrid search
- **Reranking (opt-in)**: Qwen3-Reranker, a sentence-transformers cross-encoder, or a llama.cpp GGUF reranker via `--rerank` or `SIF_RERANK_ENABLED=1`
- **MCP Server**: Model Context Protocol support for AI assistants (stdio + HTTP) with `query`, `get`, `multi_get`, and `status` tools
- **Live Indexing**: `sif watch` keeps the index fresh as files change (foreground, detached daemon, or launchd/systemd service; BM25-only unless `--embed` is given)
- **Query Suggestions**: Prefix completions, did-you-mean rewrites, and local query history via `sif suggest`
- **Benchmarking**: `sif bench` evaluates search quality against a fixture and can sweep fusion settings
- **Python API**: Use the search strategies as a library from your own Python code
- **Local-First**: All data stays on your machine
- **Multiple Backends**: sentence-transformers, llama-cpp-python (GGUF), OpenAI-compatible API, ModelScope

## Installation

SIF is distributed on PyPI as `docsif`; the installed command is `sif`. Python 3.10 or newer is required.

### From PyPI (Recommended)

```bash
pip install docsif
```

The base install provides the CLI, the MCP server, BM25 search, and the SQLite vector store. Hybrid and vector search additionally need an embedding backend:

```bash
# sentence-transformers and ModelScope backends
pip install "docsif[embed]"

# every backend, including llama-cpp-python (GGUF) and OpenAI-compatible APIs
pip install "docsif[all]"
```

### From Source

```bash
git clone https://github.com/zhangtaolab/sif.git
cd sif
pip install -e ".[dev]"
```

### Using pipx

```bash
pipx install docsif
```

## Quick Start

1. Install SIF with an embedding backend:

   ```bash
   pip install "docsif[embed]"
   ```

2. Add a collection pointing at your notes:

   ```bash
   sif collection add ~/Documents/notes --name my-notes
   ```

3. Index the collection:

   ```bash
   sif index update --collection my-notes
   ```

4. Search:

   ```bash
   sif search query "python decorators"
   ```

BM25-only search works on the base install without an embedding backend:

```bash
sif search search "python decorators"
```

## Usage

### Collection Management

```bash
# List all collections
sif collection list

# Add a new collection
sif collection add ~/Work/docs --name work-docs --description "Work documentation"

# Show collection details
sif collection show my-notes

# Rename a collection
sif collection rename my-notes personal-notes

# Delete a collection
sif collection remove old-collection --yes
```

Collections added with `--no-default` are excluded from default searches; use `sif collection enable`/`sif collection disable` to toggle that behavior later.

### Context Management

Add descriptive context to improve search relevance. The supported context types are `path`, `collection`, and `global`:

```bash
# Add context to a collection
sif context add collection my-notes "These are my personal notes about programming and technology."

# Add global context
sif context add global global "I am a software engineer interested in Python and machine learning."

# List all context
sif context list

# Remove orphaned path contexts whose files are no longer indexed
sif context prune
```

### Indexing

```bash
# Update the index
sif index update --collection my-notes

# Force full reindex
sif index update --collection my-notes --force

# Show indexing status (documents, chunks, watch state, vector lag)
sif status
```

Vector search also needs chunk embeddings, generated separately with `sif index embed` (see [More CLI Commands](#more-cli-commands)).

### Search

```bash
# Hybrid search: BM25 + vector + optional reranking
sif search query "python decorators"

# Search in a specific collection
sif search query "python decorators" -c my-notes

# BM25 keyword search (works without embeddings)
sif search search "python decorators"

# Vector similarity search (run sif index embed first)
sif search vsearch "functions that wrap other functions" -c my-notes

# Limit results
sif search query "python decorators" --limit 20

# Show score breakdowns across pipeline stages
sif search query "AI" --explain
```

`--json`, `--csv`, `--md`, `--xml`, and `--files` are available on all three search subcommands.

### Live Indexing

`sif watch` updates the index as files change. It is BM25-only by default; pass `--embed` to also write vectors for changed documents.

```bash
# Watch all default collections in the foreground
sif watch

# Watch specific collections and update vectors too
sif watch -c my-notes --embed

# Run as a detached background daemon, then stop it
sif watch --detach
sif watch --stop

# Install as a launchd LaunchAgent (macOS) or systemd user unit (Linux)
sif watch --install-service
```

### Query Suggestions

```bash
# Prefix completions, did-you-mean rewrites, and query history
sif suggest "python dec"

# Machine-readable output
sif suggest "python dec" --json

# Delete the locally recorded query history
sif suggest --clear-history
```

### MCP Server

Start the MCP server for integration with AI assistants:

```bash
# Start with stdio transport (default)
sif mcp stdio

# Start with HTTP transport
sif mcp http --host 127.0.0.1 --port 8080
```

The HTTP transport serves the JSON-RPC endpoint at `/mcp` (POST and SSE GET) and a health check at `/health`.

Configure in Claude Desktop:

```json
{
  "mcpServers": {
    "sif": {
      "command": "sif",
      "args": ["mcp", "stdio"]
    }
  }
}
```

## Configuration

SIF can be configured via environment variables or a `.env` file. All variables use the `SIF_` prefix:

```bash
# Database location (default: platform data dir, e.g. ~/.local/share/sif/sif.db
# on Linux or ~/Library/Application Support/sif/sif.db on macOS)
SIF_DB_PATH=~/.local/share/sif/sif.db

# Embedding model and backend
SIF_MODEL_NAME=Qwen/Qwen3-Embedding-0.6B
SIF_MODEL_TYPE=modelscope
SIF_MODEL_PATH=~/models/embedding.gguf
SIF_EMBEDDING_DIM=1024

# Chunking settings
SIF_CHUNK_SIZE=512
SIF_CHUNK_OVERLAP=128

# Search tuning
SIF_RRF_K=60
SIF_BM25_WEIGHT=1.0
SIF_VECTOR_WEIGHT=1.0
SIF_RERANK_ENABLED=0

# Logging
SIF_LOG_LEVEL=INFO

# MCP server
SIF_MCP_HOST=127.0.0.1
SIF_MCP_PORT=8080
```

See [Configuration](docs/configuration.md) for the full settings reference, including watch, reranker, and pre-search refresh options.

## Architecture

SIF follows a layered architecture with clean separation of concerns:

```
┌─────────────────────────────────────────────────────────────┐
│                      Presentation Layer                      │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐  │
│  │     CLI      │  │  MCP Server  │  │  API (Future)    │  │
│  └──────────────┘  └──────────────┘  └──────────────────┘  │
├─────────────────────────────────────────────────────────────┤
│                      Application Layer                       │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐  │
│  │   Collection │  │    Index     │  │     Search       │  │
│  │   Manager    │  │   Service    │  │    Service       │  │
│  └──────────────┘  └──────────────┘  └──────────────────┘  │
├─────────────────────────────────────────────────────────────┤
│                      Domain Layer                            │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐  │
│  │  Collection  │  │   Document   │  │     Context      │  │
│  │   Entity     │  │   Entity     │  │     Entity       │  │
│  └──────────────┘  └──────────────┘  └──────────────────┘  │
├─────────────────────────────────────────────────────────────┤
│                      Infrastructure Layer                    │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐  │
│  │  Repository  │  │   Embedding  │  │    Database      │  │
│  │  (SQLite)    │  │    Model     │  │   Connection     │  │
│  └──────────────┘  └──────────────┘  └──────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

See [docs/architecture.md](docs/architecture.md) for detailed architecture documentation.

> **Note:** SIF can also be read as **Semantic Intelligence Framework** — reflecting its use of semantic embeddings and AI-assisted retrieval.

## Documentation

- [Installation Guide](docs/installation.md) - Detailed installation instructions
- [Configuration](docs/configuration.md) - Configuration options
- [Quick Start](docs/quickstart.md) - Get started quickly
- [CLI Reference](docs/cli-reference.md) - Complete CLI documentation
- [API Reference](docs/api-reference.md) - Python API documentation
- [Architecture](docs/architecture.md) - System architecture
- [MCP Server](docs/mcp-server.md) - MCP server documentation
- [Search Algorithms](docs/search-algorithms.md) - Search algorithm details
- [Benchmarking](docs/benchmarking.md) - Search quality evaluation and fusion sweeps
- [Data Models](docs/models.md) - Domain model reference
- [Development Guide](docs/development.md) - Development setup
- [Testing](docs/testing.md) - Test suite layout and conventions
- [Contributing](docs/contributing.md) - Contribution guidelines
- [Migration Guide](docs/migration.md) - Breaking changes from DocSift to SIF
- [Changelog](docs/changelog.md) - Release history

## Search Algorithms

### BM25 (Full-Text Search)

BM25 is a probabilistic ranking function that scores documents based on term frequency and inverse document frequency.

**Parameters:** BM25 tuning uses SQLite FTS5's built-in defaults (`k1` = 1.2, `b` = 0.75); SIF does not expose them as configuration. See [Search Algorithms](docs/search-algorithms.md) for details.

### Vector Search

Vector search uses embeddings to find semantically similar documents, even if they don't share exact keywords. Document chunks are embedded by `sif index embed` and stored in a sqlite-vec virtual table.

**Supported Models:**
- Sentence Transformers
- GGUF models via llama-cpp-python
- OpenAI-compatible API
- ModelScope Hub

### Hybrid Search

Hybrid search combines BM25 and vector results using weighted Reciprocal Rank Fusion (RRF):

```
RRF_score(d) = Σ  w_i / (k + rank_i(d))
```

Where `k` is a constant (default: 60), `w_i` is the per-source weight (default: 1.0 for both), and `rank_i(d)` is the rank of document `d` in result set `i`. Tune these with `SIF_RRF_K`, `SIF_BM25_WEIGHT`, and `SIF_VECTOR_WEIGHT`, or per query with `--rrf-k`, `--bm25-weight`, and `--vector-weight` on the hybrid `query` subcommand.

### Search Pipeline

The hybrid `query` subcommand runs the full pipeline: query parsing and routing, optional embedding-based query expansion, BM25 and vector retrieval, weighted RRF fusion, snippet extraction, and optional reranking. Reranking is off by default; enable it with `--rerank` or `SIF_RERANK_ENABLED=1`. When enabled, `SIF_RERANK_CANDIDATE_LIMIT` (default 20, clamped to 5-50) bounds the candidate pool and `SIF_RERANK_RELATIVE_THRESHOLD` (default 0.5) drops candidates scoring below `top_score * alpha`.

## Development

### Setup

```bash
# Clone the repository
git clone https://github.com/zhangtaolab/sif.git
cd sif

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install in development mode
pip install -e ".[dev]"
```

### Quality Suite

Run the same checks CI runs before submitting a change:

```bash
ruff check src tests
ruff format --check src tests
ty check src/sif
pytest
```

### Running Tests

```bash
# Run all tests (coverage is configured in pyproject.toml; fail_under = 90)
pytest

# Run a specific test file
pytest tests/unit/search/test_bm25.py

# Run a specific test
pytest tests/unit/search/test_bm25.py::TestBM25Searcher::test_search_executes_fts_query

# Run a specific test tier
pytest tests/unit/
pytest tests/integration/
```

### Documentation

Regenerate the CLI and configuration reference docs from source:

```bash
make docs-generate
```

This rewrites `docs/cli-reference.md` and `docs/configuration.md`; do not edit those two files by hand. CI verifies they are in sync, and `make docs-test` validates the code blocks in the docs.

## Roadmap

- [ ] Web UI (browser-based search interface)
- [ ] Plugin system for custom parsers
- [ ] Multi-language support
- [ ] REST API

## Contributing

Contributions are welcome! Please see [docs/contributing.md](docs/contributing.md) for guidelines.

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'feat: add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

MIT License - see [LICENSE](LICENSE) for details.

## Acknowledgments

SIF is a Python reimplementation of the original TypeScript QMD (Query Markup Documents) project.

## Support

- GitHub Issues: [github.com/zhangtaolab/sif/issues](https://github.com/zhangtaolab/sif/issues)
- GitHub Discussions: [github.com/zhangtaolab/sif/discussions](https://github.com/zhangtaolab/sif/discussions)

## More CLI Commands

Beyond the commands shown above, the `sif` CLI also provides:

```bash
# Vector similarity search
sif search vsearch "similar documents" -c my-notes

# Generate embeddings for vector search (needed before vsearch works)
sif index embed --collection my-notes
sif index embed --collection my-notes --model-type sentence_transformers --model Qwen/Qwen3-Embedding-0.6B

# Fetch a document by path or document ID, with an optional line range
sif get get notes/python_guide.md --lines 50 --line-numbers

# Fetch multiple documents via a glob pattern or comma-separated IDs/paths
sif get multi-get "docs/*.md"
sif get multi-get "doc-id-1,notes/python_guide.md"

# Browse indexed documents as a virtual file tree
sif ls
sif ls my-notes subfolder

# Download a GGUF embedding model (owner/repo/filename.gguf or a direct URL;
# tries HuggingFace first, falls back to ModelScope; caches in ~/.sif/models)
sif pull owner/repo/model.gguf
sif pull https://example.com/model.gguf --cache-dir ~/models

# Benchmark search quality against a JSON fixture of queries and relevant doc IDs
sif bench fixture.json --all --json

# Query suggestions
sif suggest "python dec"

# Watch collections and keep the index current
sif watch -c my-notes

# Remove orphaned chunks/embeddings and expired cache entries (asks for confirmation)
sif cleanup
```

## Python API

SIF can also be used as a Python library. The top-level package exports the core data models
(`Collection`, `Document`, `DocumentChunk`, `PathContext`, `SearchOptions`, `SearchResult`), and
search strategies live in `sif.search` (`BM25Searcher`, `VectorSearcher`, `HybridSearcher`,
`SearchPipeline`, `RRFFusion`):

```python
from sif import SearchResult
from sif.config.settings import get_settings
from sif.database.database import Database
from sif.search import BM25Searcher

# Open the database configured by SIF_DB_PATH (or the platform default),
# initialized by a previous CLI run such as `sif index update`.
db = Database(get_settings().get_db_path())
db.init_schema()

with db.connection:
    searcher = BM25Searcher(db.connection)
    results: list[SearchResult] = searcher.search("python decorators")

for result in results:
    print(f"{result.score:.3f}  {result.path}")
```

See the [API Reference](docs/api-reference.md) for the full library API.

---

**Happy searching!**
