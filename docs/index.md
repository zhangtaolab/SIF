# DocSift Documentation

Welcome to the DocSift documentation! DocSift is a local AI-powered document search engine that keeps all your data on your machine.

## What is DocSift?

DocSift is a CLI tool for indexing and searching markdown documents. It combines traditional full-text search with modern semantic search to provide accurate and relevant results.

```bash
# Index your documents
docsift collection create my-notes --path ~/Documents/notes
docsift update my-notes

# Search with AI-powered relevance
docsift search "python decorators"
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

    Install DocSift and index your first collection.

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

    Integrate DocSift with AI assistants.

    [:octicons-arrow-right-24: MCP Server](mcp-server.md)

</div>

## Installation

```bash
pip install docsift
```

For full functionality:

```bash
pip install "docsift[all]"
```

## Quick Start

### 1. Create a Collection

```bash
docsift collection create my-notes --description "Personal notes"
docsift collection add-path my-notes ~/Documents/notes
```

### 2. Index Your Documents

```bash
docsift update my-notes
```

### 3. Search

```bash
# Basic search
docsift search "python decorators"

# Hybrid search with more results
docsift search "machine learning" --type hybrid --limit 20

# Search in specific collection
docsift search "python decorators" --collection my-notes
```

## Architecture

DocSift follows a layered architecture:

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
docsift search "python decorators" --type bm25
```

### Vector (Semantic)

Best for conceptual similarity:

```bash
docsift search "functions that wrap other functions" --type vector
```

### Hybrid (Combined)

Best overall results:

```bash
docsift search "python decorators" --type hybrid
```

Learn more about [Search Algorithms](search-algorithms.md).

## MCP Server

Integrate DocSift with AI assistants like Claude:

```bash
# Start MCP server
docsift mcp start
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

Learn more about the [MCP Server](mcp-server.md).

## Configuration

Configure DocSift via environment variables or `.env` file:

```bash
# Database location
DOCSIFT_DB_PATH=~/.local/share/docsift/docsift.db

# Embedding model
DOCSIFT_MODEL_NAME=all-MiniLM-L6-v2

# Chunking settings
DOCSIFT_CHUNK_SIZE=512
DOCSIFT_CHUNK_OVERLAP=128

# Logging
DOCSIFT_LOG_LEVEL=INFO
```

See [Configuration](configuration.md) for all options.

## Contributing

We welcome contributions! See the [Contributing Guide](contributing.md) to get started.

```bash
# Clone repository
git clone https://github.com/docsift/docsift.git
cd docsift

# Install in development mode
pip install -e ".[dev]"

# Run tests
pytest
```

## License

DocSift is licensed under the MIT License. See [LICENSE](https://github.com/docsift/docsift/blob/main/LICENSE) for details.

## Support

- GitHub Issues: [github.com/docsift/docsift/issues](https://github.com/docsift/docsift/issues)
- GitHub Discussions: [github.com/docsift/docsift/discussions](https://github.com/docsift/docsift/discussions)

---

**Ready to get started?** Head to the [Installation Guide](installation.md)!
