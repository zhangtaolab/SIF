# SIF

[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Code style: ruff](https://img.shields.io/badge/code%20style-ruff-000000.svg)](https://github.com/astral-sh/ruff)

SIF is a local CLI search engine for indexing and searching markdown documents. It provides powerful full-text and semantic search capabilities while keeping all data on your machine.

## Features

- **Full-Text Search**: BM25 ranking via SQLite FTS5
- **Semantic Search**: Vector similarity using configurable embeddings
- **Hybrid Search**: Combines BM25 and vector search with RRF fusion
- **Query Expansion**: Automatic query enhancement via pseudo-relevance feedback
- **Result Reranking**: Cross-encoder reranking with Qwen3-Reranker
- **MCP Server**: Model Context Protocol support for AI assistants (stdio + HTTP)
- **Local-First**: All data stays on your machine
- **Multiple Backends**: sentence-transformers, llama-cpp-python, OpenAI-compatible API, ModelScope

## Quick Start

### Installation

```bash
pip install docsif
```

For full functionality including embeddings:

```bash
pip install "docsif[all]"
```

### Basic Usage

```bash
# Add a collection
sif collection add ~/Documents/notes --name my-notes

# Index your documents
sif index update --collection my-notes

# Search
sif search query "python decorators"
```

## Installation

### From PyPI (Recommended)

```bash
pip install docsif
```

### From Source

```bash
git clone https://github.com/zhangtaolab/sif.git
cd sif
pip install -e ".[dev]"
```

### Using pipx

```bash
pipx install sif
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
sif collection remove old-collection --force
```

### Context Management

Add descriptive context to improve search relevance:

```bash
# Add context to a collection
sif context add collection my-notes "These are my personal notes about programming and technology."

# Add global context
sif context add global global "I am a software engineer interested in Python and machine learning."

# List all context
sif context list
```

### Indexing

```bash
# Update the index
sif index update --collection my-notes

# Force full reindex
sif index update --collection my-notes --force

# Show indexing status
sif status
```

### Search

```bash
# Basic search
sif search query "python decorators"

# Search in specific collection
sif search query "python decorators" -c my-notes

# BM25 keyword search
sif search search "python decorators"

# Limit results
sif search query "python decorators" --limit 20

# Search with explanation
sif search query "AI" --explain
```

### MCP Server

Start the MCP server for integration with AI assistants:

```bash
# Start with stdio transport (default)
sif mcp stdio

# Start with HTTP transport
sif mcp http --port 8080
```

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

SIF can be configured via environment variables or a `.env` file:

```bash
# Database location
SIF_DB_PATH=~/.local/share/sif/sif.db

# Embedding model
SIF_MODEL_NAME=Qwen/Qwen3-Embedding-0.6B
SIF_MODEL_PATH=~/models/embedding.gguf

# Chunking settings
SIF_CHUNK_SIZE=512
SIF_CHUNK_OVERLAP=128

# Logging
SIF_LOG_LEVEL=INFO

# MCP server
SIF_MCP_HOST=127.0.0.1
SIF_MCP_PORT=8080
```

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

## Documentation

- [Installation Guide](docs/installation.md) - Detailed installation instructions
- [Configuration](docs/configuration.md) - Configuration options
- [Quick Start](docs/quickstart.md) - Get started quickly
- [CLI Reference](docs/cli-reference.md) - Complete CLI documentation
- [API Reference](docs/api-reference.md) - Python API documentation
- [Architecture](docs/architecture.md) - System architecture
- [MCP Server](docs/mcp-server.md) - MCP server documentation
- [Search Algorithms](docs/search-algorithms.md) - Search algorithm details
- [Development Guide](docs/development.md) - Development setup
- [Contributing](docs/contributing.md) - Contribution guidelines

## Search Algorithms

### BM25 (Full-Text Search)

BM25 is a probabilistic ranking function that scores documents based on term frequency and inverse document frequency.

**Parameters:**
- `k1`: Controls term frequency saturation (default: 1.5)
- `b`: Controls document length normalization (default: 0.75)

### Vector Search

Vector search uses embeddings to find semantically similar documents, even if they don't share exact keywords.

**Supported Models:**
- Sentence Transformers
- GGUF models via llama-cpp-python
- OpenAI-compatible API
- ModelScope Hub

### Hybrid Search

Hybrid search combines BM25 and vector search using Reciprocal Rank Fusion (RRF):

```
RRF_score(d) = Σ 1 / (k + rank_i(d))
```

Where `k` is a constant (default: 60) and `rank_i(d)` is the rank of document `d` in result set `i`.

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

# Install pre-commit hooks
pre-commit install
```

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=sif

# Run specific test category
pytest -m unit
pytest -m integration
```

### Code Quality

```bash
# Format code
ruff format .

# Lint code
ruff check .

# Type checking
mypy src/sif
```

## Roadmap

- [ ] Web UI (browser-based search interface)
- [ ] Plugin system for custom parsers
- [ ] Multi-language support
- [ ] REST API
- [ ] Query suggestions
- [ ] File system watching for auto-indexing

## Contributing

Contributions are welcome! Please see [CONTRIBUTING.md](docs/contributing.md) for guidelines.

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

---

**Happy searching!**
