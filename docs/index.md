# SIF Documentation

Welcome to the SIF documentation! SIF is a local AI-powered document search engine that keeps all your data on your machine.

## What is SIF?

SIF is a CLI tool for indexing and searching markdown documents. It combines traditional full-text search with modern semantic search to provide accurate and relevant results.

```bash
# Index your documents
sif collection add ~/Documents/notes --name my-notes
sif index update --collection my-notes

# Search with AI-powered relevance
sif search query "python decorators"
```

## Key Features

- **Full-Text Search**: BM25 ranking via SQLite FTS5
- **Semantic Search**: Vector similarity using embeddings
- **Hybrid Search**: Combines BM25 and vector search with RRF fusion
- **Query Expansion**: Automatic query enhancement
- **Result Reranking**: Cross-encoder reranking
- **MCP Server**: Model Context Protocol support for AI assistants
- **Local-First**: All data stays on your machine

## Quick Links

<div class="grid cards" markdown>

- :material-rocket: __Getting Started__

    ---

    Install SIF and index your first collection.

    [:octicons-arrow-right-24: Installation](installation.md)

- :material-console: __CLI Reference__

    ---

    Complete reference for all CLI commands.

    [:octicons-arrow-right-24: CLI Reference](cli-reference.md)

- :material-code-braces: __API Reference__

    ---

    Python API documentation for developers.

    [:octicons-arrow-right-24: API Reference](api-reference.md)

- :material-server: __MCP Server__

    ---

    Integrate SIF with AI assistants.

    [:octicons-arrow-right-24: MCP Server](mcp-server.md)

</div>

## Installation

```bash
pip install sif
```

For full functionality:

```bash
pip install "sif[all]"
```

## Quick Start

### 1. Create a Collection

```bash
sif collection add ~/Documents/notes --name my-notes --description "Personal notes"
```

### 2. Index Your Documents

```bash
sif index update --collection my-notes
```

### 3. Search

```bash
# Basic search
sif search query "python decorators"

# Hybrid search with more results
sif search query "machine learning" --limit 20

# Search in specific collection
sif search query "python decorators" --collection my-notes
```

## Architecture

SIF follows a layered architecture:

```
┌─────────────────────────────────────────┐
│         Presentation Layer              │
│  CLI  │  MCP Server  │  API (Future)   │
├─────────────────────────────────────────┤
│         Application Layer               │
│  Collection  │  Index  │  Search       │
├─────────────────────────────────────────┤
│         Domain Layer                    │
│  Collection  │  Document  │  Context   │
├─────────────────────────────────────────┤
│         Infrastructure Layer            │
│  Repository  │  Embedding  │  Database │
└─────────────────────────────────────────┘
```

Learn more in the [Architecture](architecture.md) documentation.

## Search Types

### BM25 (Full-Text)

Best for exact keyword matching:

```bash
sif search search "python decorators"
```

### Vector (Semantic)

Best for conceptual similarity:

```bash
sif search vsearch "functions that wrap other functions"
```

### Hybrid (Combined)

Best overall results:

```bash
sif search query "python decorators"
```

Learn more about [Search Algorithms](search-algorithms.md).

## MCP Server

Integrate SIF with AI assistants like Claude:

```bash
# Start MCP server
sif mcp stdio
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

Learn more about the [MCP Server](mcp-server.md).

## Configuration

Configure SIF via environment variables or `.env` file:

```bash
# Database location
SIF_DB_PATH=~/.local/share/sif/sif.db

# Embedding model
SIF_MODEL_NAME=Qwen/Qwen3-Embedding-0.6B

# Chunking settings
SIF_CHUNK_SIZE=512
SIF_CHUNK_OVERLAP=128

# Logging
SIF_LOG_LEVEL=INFO
```

See [Configuration](configuration.md) for all options.

## Contributing

We welcome contributions! See the [Contributing Guide](contributing.md) to get started.

```bash
# Clone repository
git clone https://github.com/zhangtaolab/sif.git
cd sif

# Install in development mode
pip install -e ".[dev]"

# Run tests
pytest
```

## License

SIF is licensed under the MIT License. See [LICENSE](https://github.com/zhangtaolab/sif/blob/main/LICENSE) for details.

## Support

- GitHub Issues: [github.com/zhangtaolab/sif/issues](https://github.com/zhangtaolab/sif/issues)
- GitHub Discussions: [github.com/zhangtaolab/sif/discussions](https://github.com/zhangtaolab/sif/discussions)

---

**Ready to get started?** Head to the [Installation Guide](installation.md)!
