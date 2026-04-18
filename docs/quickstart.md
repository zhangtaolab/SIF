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

### 1. Add a Collection

```bash
docsift collection add ~/Documents/notes --name my-notes   --description "My personal notes"
```

The `PATH` argument is the directory to index. Use `--name` to give your
collection a short identifier. You can also set `--pattern` (default `**/*.md`)
and `--ignore` for fine-grained control over which files are included.

### 2. Index Documents

Index all documents in the collection:

```bash
docsift index update
```

You will see progress output as documents are scanned and indexed.

To update only one collection:

```bash
docsift index update --collection my-notes
```

To force a full reindex:

```bash
docsift index update --collection my-notes --force
```

## Searching

### Basic Search

DocSift provides three search subcommands under `docsift search`:

```bash
# BM25 keyword search
docsift search search "python decorators"

# Vector (semantic) search
docsift search vsearch "functions that wrap other functions"

# Hybrid search (BM25 + Vector + Rerank) -- recommended for best results
docsift search query "python decorators"
```

### Search with Options

```bash
# More results
docsift search query "python decorators" --limit 20

# Specific collection
docsift search query "python decorators" -c my-notes

# Search all collections (including disabled ones)
docsift search query "python decorators" --all

# Show score breakdowns across pipeline stages
docsift search query "python decorators" --explain

# Increase candidate pool for reranking
docsift search query "python decorators" --candidate-limit 30

# Provide intent hint for query expansion
docsift search query "python decorators" --intent "programming tutorial"
```

### Output Formats

```bash
# JSON output
docsift search query "python" --json

# Markdown table
docsift search query "python" --md

# CSV output
docsift search query "python" --csv

# XML output
docsift search query "python" --xml

# Just file paths
docsift search query "python" --files
```

## Managing Collections

### List Collections

```bash
docsift collection list
```

Add `--verbose` for detailed information.

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

### Include / Exclude from Default Searches

```bash
# Exclude from default searches
docsift collection exclude my-notes

# Include again
docsift collection include my-notes
```

### List Files in a Collection

```bash
docsift ls my-notes
```

## Adding Context

Context helps improve search relevance by providing background information.

### Global Context

Applies to all searches:

```bash
docsift context add global global   "I am a software engineer working with Python and machine learning."
```

### Collection Context

Applies to searches in a specific collection:

```bash
docsift context add collection my-notes   "These are my personal notes about programming and technology."
```

### Path Context

Applies to a specific file or directory:

```bash
docsift context add path ~/Documents/notes/project-a   "Notes for the Project Alpha rewrite."
```

### List and Remove Context

```bash
docsift context list
docsift context remove <context-id>
```

## Checking Status

### Overall Status

```bash
docsift status
```

The status command shows index path, collection count, document count, chunk
count, contexts, and total database size.

## Updating Index

### Update Changed Documents

```bash
docsift index update
```

### Update a Specific Collection

```bash
docsift index update --collection my-notes
```

### Force Full Reindex

```bash
docsift index update --collection my-notes --force
```

## Generating Embeddings

After indexing text documents, generate embeddings for vector search:

```bash
docsift index embed
```

Or for a specific collection:

```bash
docsift index embed --collection my-notes
```

## Retrieving Documents

### Get a Single Document

```bash
docsift get get <path-or-doc-id>
```

### Get Multiple Documents

```bash
docsift get multi-get "*.md"
```

## MCP Server

Start the MCP server for AI assistant integration:

```bash
# Stdio transport (default)
docsift mcp stdio

# HTTP transport
docsift mcp http --port 8080
```

## Configuration

Create a `.env` file for persistent configuration:

```bash
# ~/.env or ./.env
DOCSIFT_DB_PATH=~/.local/share/docsift/docsift.db
DOCSIFT_MODEL_NAME=Qwen/Qwen3-Embedding-0.6B
DOCSIFT_EMBEDDING_DIM=1024
DOCSIFT_CHUNK_SIZE=512
DOCSIFT_LOG_LEVEL=INFO
```

Environment variables are read automatically when DocSift starts.

## Common Workflows

### Daily Notes Workflow

```bash
# Morning: Check status
docsift status

# Throughout day: Quick searches
docsift search query "meeting notes"
docsift search query "project ideas"

# Evening: Update index
docsift index update
```

### Research Workflow

```bash
# Add research collection
docsift collection add ~/Research --name research   --description "Research papers and notes"

# Index
docsift index update --collection research

# Search with hybrid pipeline
docsift search query "neural networks"   -c research   --limit 20
```

### Documentation Workflow

```bash
# Add docs collection
docsift collection add ~/Projects/docs --name docs   --description "Project documentation"

# Add context
docsift context add collection docs   "This is technical documentation for my projects."

# Index
docsift index update --collection docs

# Search
docsift search query "API reference" -c docs
```

## Tips and Tricks

### Use Shell Aliases

Add to your `.bashrc` or `.zshrc`:

```bash
alias ds='docsift'
alias ds-search='docsift search query'
alias ds-update='docsift index update'
alias ds-status='docsift status'
```

### Search History

```bash
# Use shell history
history | grep "docsift search"

# Or create a search history file
docsift search query "" | tee -a ~/.docsift_searches
```

### Export Results

```bash
# Save search results
docsift search query "python" --json > results.json

# Process with jq
docsift search query "python" --json | jq '.results[].document_path'
```

### Batch Document Retrieval

```bash
# Get multiple documents from search results
docsift get multi-get "*.md"
```

## Troubleshooting

### Search Returns No Results

1. Check if collection is indexed:
   ```bash
   docsift status
   ```

2. Try different search terms

3. Check if documents exist:
   ```bash
   docsift ls my-notes
   ```

4. Verify embeddings are generated (for vector/hybrid search):
   ```bash
   docsift index embed --collection my-notes
   ```

### Slow Search

1. Use BM25 for faster results:
   ```bash
   docsift search search "query"
   ```

2. Limit results:
   ```bash
   docsift search query "query" --limit 5
   ```

3. Search a specific collection instead of all:
   ```bash
   docsift search query "query" -c my-notes
   ```

### Indexing Issues

1. Check paths exist:
   ```bash
   docsift collection show my-notes
   ```

2. Force reindex:
   ```bash
   docsift index update --collection my-notes --force
   ```

3. Check logs:
   ```bash
   export DOCSIFT_LOG_LEVEL=DEBUG
   docsift index update --collection my-notes
   ```

### Cleaning Up

Remove orphaned chunks, embeddings, and expired cache entries:

```bash
docsift cleanup
```

## Next Steps

- Learn about [Search Algorithms](search-algorithms.md)
- Explore the [CLI Reference](cli-reference.md)
- Set up the [MCP Server](mcp-server.md)
- Read the full [Configuration](configuration.md) guide

## Getting Help

- Use `--help` for command help:
  ```bash
  docsift search query --help
  ```

- Check the [FAQ](#) (coming soon)

- Open an issue on [GitHub](https://github.com/docsift/docsift/issues)
