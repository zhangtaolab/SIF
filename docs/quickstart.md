# Quick Start Guide

Get up and running with DocSift in minutes.

## Installation

Install DocSift from PyPI:

```bash
pip install docsift
```

For full functionality including embeddings:

```bash
pip install "docsift[all]"
```

Verify installation:

```bash
docsift --version
```

## Your First Collection

A collection is a group of documents you want to search together.

### 1. Create a Collection

```bash
docsift collection create my-notes \
  --description "My personal notes"
```

### 2. Add Paths

Add directories to your collection:

```bash
docsift collection add-path my-notes ~/Documents/notes
```

### 3. Index Documents

Index all documents in the collection:

```bash
docsift update my-notes
```

You'll see progress output as documents are indexed.

## Searching

### Basic Search

```bash
docsift search "python decorators"
```

### Search with Options

```bash
# More results
docsift search "python decorators" --limit 20

# Specific collection
docsift search "python decorators" --collection my-notes

# Hybrid search (default)
docsift search "python decorators" --type hybrid

# Vector search (semantic)
docsift search "functions that wrap other functions" --type vector

# BM25 search (keyword)
docsift search "python decorators" --type bm25
```

### Output Formats

```bash
# JSON output
docsift search "python" --format json

# Markdown table
docsift search "python" --format md

# Just file paths
docsift search "python" --format files
```

## Managing Collections

### List Collections

```bash
docsift collection list
```

### Show Collection Details

```bash
docsift collection show my-notes
```

### Rename Collection

```bash
docsift collection rename my-notes personal-notes
```

### Delete Collection

```bash
docsift collection delete old-collection
```

## Adding Context

Context helps improve search relevance by providing background information.

### Global Context

Applies to all searches:

```bash
docsift context add --global \
  "I am a software engineer working with Python and machine learning."
```

### Collection Context

Applies to searches in a specific collection:

```bash
docsift context add --collection my-notes \
  "These are my personal notes about programming and technology."
```

## Checking Status

### Overall Status

```bash
docsift status
```

### Collection Status

```bash
docsift status my-notes
```

## Updating Index

### Update Changed Documents

```bash
docsift update my-notes
```

### Force Full Reindex

```bash
docsift update my-notes --force
```

## Advanced Search

### Query Expansion

Automatically expand queries with related terms:

```bash
docsift search "AI" --expand
```

### Result Reranking

Rerank results for better relevance:

```bash
docsift search "python decorators" --rerank
```

### Find Similar Documents

```bash
docsift search similar ~/Documents/notes/python/decorators.md
```

## MCP Server

Start the MCP server for AI assistant integration:

```bash
# Stdio transport (default)
docsift mcp start

# HTTP transport
docsift mcp start --transport http --port 8080
```

## Configuration

Create a `.env` file for persistent configuration:

```bash
# ~/.env or ./.env
DOCSIFT_DB_PATH=~/.local/share/docsift/docsift.db
DOCSIFT_MODEL_NAME=all-MiniLM-L6-v2
DOCSIFT_CHUNK_SIZE=512
DOCSIFT_LOG_LEVEL=INFO
```

## Common Workflows

### Daily Notes Workflow

```bash
# Morning: Check status
docsift status

# Throughout day: Quick searches
docsift search "meeting notes"
docsift search "project ideas"

# Evening: Update index
docsift update
```

### Research Workflow

```bash
# Create research collection
docsift collection create research \
  --description "Research papers and notes"
docsift collection add-path research ~/Research

# Index
docsift update research

# Search with expansion and reranking
docsift search "neural networks" \
  --collection research \
  --expand \
  --rerank \
  --limit 20
```

### Documentation Workflow

```bash
# Create docs collection
docsift collection create docs \
  --description "Project documentation"
docsift collection add-path docs ~/Projects/docs

# Add context
docsift context add --collection docs \
  "This is technical documentation for my projects."

# Index
docsift update docs

# Search
docsift search "API reference" --collection docs
```

## Tips and Tricks

### Use Shell Aliases

Add to your `.bashrc` or `.zshrc`:

```bash
alias ds='docsift'
alias ds-search='docsift search'
alias ds-update='docsift update'
alias ds-status='docsift status'
```

### Search History

```bash
# Use shell history
history | grep "docsift search"

# Or create a search history file
docsift search "$@" | tee -a ~/.docsift_searches
```

### Export Results

```bash
# Save search results
docsift search "python" --format json > results.json

# Process with jq
docsift search "python" --format json | jq '.results[].document_path'
```

### Batch Operations

```bash
# Get multiple documents
docsift multi-get $(docsift search "important" --format files)
```

## Troubleshooting

### Search Returns No Results

1. Check if collection is indexed:
   ```bash
   docsift status my-notes
   ```

2. Try different search terms

3. Check if documents exist:
   ```bash
   docsift ls my-notes
   ```

### Slow Search

1. Enable caching:
   ```bash
   export DOCSIFT_CACHE_SIZE=5000
   ```

2. Use BM25 for faster results:
   ```bash
   docsift search "query" --type bm25
   ```

3. Limit results:
   ```bash
   docsift search "query" --limit 5
   ```

### Indexing Issues

1. Check paths exist:
   ```bash
   docsift collection show my-notes
   ```

2. Force reindex:
   ```bash
   docsift update my-notes --force
   ```

3. Check logs:
   ```bash
   export DOCSIFT_LOG_LEVEL=DEBUG
   docsift update my-notes
   ```

## Next Steps

- Learn about [Search Algorithms](search-algorithms.md)
- Explore the [CLI Reference](cli-reference.md)
- Set up the [MCP Server](mcp-server.md)
- Read the full [Configuration](configuration.md) guide

## Getting Help

- Use `--help` for command help:
  ```bash
  docsift search --help
  ```

- Check the [FAQ](#) (coming soon)

- Open an issue on [GitHub](https://github.com/docsift/docsift/issues)
