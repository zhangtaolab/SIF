# DocSift

[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Code style: ruff](https://img.shields.io/badge/code%20style-ruff-000000.svg)](https://github.com/astral-sh/ruff)

DocSift is a local CLI search engine for indexing and searching markdown documents. It provides powerful full-text and semantic search capabilities while keeping all data on your machine.

## Features

- **Full-Text Search**: BM25 ranking via SQLite FTS5
- **Semantic Search**: Vector similarity using embeddings
- **Hybrid Search**: Combines BM25 and vector search with RRF fusion
- **Query Expansion**: Automatic query enhancement
- **Result Reranking**: Cross-encoder reranking (optional)
- **MCP Server**: Model Context Protocol support for AI assistants
- **Local-First**: All data stays on your machine

## Quick Start

### Installation

```bash
pip install docsift
```

For full functionality including embeddings:

```bash
pip install "docsift[all]"
```

### Basic Usage

```bash
# Create a collection
docsift collection create my-notes --path ~/Documents/notes

# Index your documents
docsift update my-notes

# Search
docsift search "python decorators"
```

## Installation

### From PyPI (Recommended)

```bash
pip install docsift
```

### From Source

```bash
git clone https://github.com/docsift/docsift.git
cd docsift
pip install -e ".[dev]"
```

### Using pipx

```bash
pipx install docsift
```

## Usage

### Collection Management

```bash
# List all collections
docsift collection list

# Create a new collection
docsift collection create work-docs --description "Work documentation"

# Add paths to a collection
docsift collection add-path work-docs ~/Work/docs

# Show collection details
docsift collection show my-notes

# Rename a collection
docsift collection rename my-notes personal-notes

# Delete a collection
docsift collection delete old-collection --force
```

### Context Management

Add descriptive context to improve search relevance:

```bash
# Add context to a collection
docsift context add --collection my-notes "These are my personal notes about programming and technology."

# Add global context
docsift context add --global "I am a software engineer interested in Python and machine learning."

# List all context
docsift context list
```

### Indexing

```bash
# Update the index
docsift update my-notes

# Force full reindex
docsift update my-notes --force

# Show indexing status
docsift status my-notes

# Clean up index
docsift cleanup --orphaned --vacuum
```

### Search

```bash
# Basic search
docsift search "python decorators"

# Search in specific collection
docsift search "python decorators" --collection my-notes

# Search with type
docsift search "python decorators" --type hybrid

# Limit results
docsift search "python decorators" --limit 20

# Search with query expansion
docsift search "AI" --expand

# Search with reranking
docsift search "machine learning" --rerank

# Find similar documents
docsift search similar path/to/document.md
```

### MCP Server

Start the MCP server for integration with AI assistants:

```bash
# Start with stdio transport (default)
docsift mcp start

# Start with HTTP transport
docsift mcp start --transport http --port 8080

# Show MCP configuration
docsift mcp config
```

Configure in Claude Desktop:

```json
{
  "mcpServers": {
    "docsift": {
      "command": "docsift",
      "args": ["mcp", "start"]
    }
  }
}
```

## Configuration

DocSift can be configured via environment variables or a `.env` file:

```bash
# Database location
DOCSIFT_DB_PATH=~/.local/share/docsift/docsift.db

# Embedding model
DOCSIFT_MODEL_NAME=all-MiniLM-L6-v2
DOCSIFT_MODEL_PATH=~/models/embedding.gguf

# Chunking settings
DOCSIFT_CHUNK_SIZE=512
DOCSIFT_CHUNK_OVERLAP=128

# Logging
DOCSIFT_LOG_LEVEL=INFO

# MCP server
DOCSIFT_MCP_HOST=127.0.0.1
DOCSIFT_MCP_PORT=8080
```

## Architecture

DocSift follows a layered architecture with clean separation of concerns:

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
- OpenAI API (planned)

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
git clone https://github.com/docsift/docsift.git
cd docsift

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
pytest --cov=docsift

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
mypy src/docsift
```

## Roadmap

- [ ] Incremental indexing
- [ ] File system watching for auto-indexing
- [ ] Web UI
- [ ] Plugin system for custom parsers
- [ ] Multi-language support
- [ ] Advanced reranking options
- [ ] Query suggestions
- [ ] REST API

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

DocSift is a Python reimplementation of the original TypeScript QMD (Query Markup Documents) project.

## Support

- GitHub Issues: [github.com/docsift/docsift/issues](https://github.com/docsift/docsift/issues)
- GitHub Discussions: [github.com/docsift/docsift/discussions](https://github.com/docsift/docsift/discussions)

---

**Happy searching!** 🔍
