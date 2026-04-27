# Quick Start Guide

Get up and running with SIF in minutes.

## Installation

Install SIF from PyPI:

```bash
pip install sif
```

For full functionality including embeddings:

```bash
pip install "sif[all]"
```

Verify installation:

```bash
sif --version
```

## Your First Collection

A collection is a group of documents you want to search together.

### 1. Add a Collection

```bash
sif collection add ~/Documents/notes --name my-notes   --description "My personal notes"
```

The `PATH` argument is the directory to index. Use `--name` to give your
collection a short identifier. You can also set `--pattern` (default `**/*.md`)
and `--ignore` for fine-grained control over which files are included.

### 2. Index Documents

Index all documents in the collection:

```bash
sif index update
```

You will see progress output as documents are scanned and indexed.

To update only one collection:

```bash
sif index update --collection my-notes
```

To force a full reindex:

```bash
sif index update --collection my-notes --force
```

## Searching

### Basic Search

SIF provides three search subcommands under `sif search`:

```bash
# BM25 keyword search
sif search search "python decorators"

# Vector (semantic) search
sif search vsearch "functions that wrap other functions"

# Hybrid search (BM25 + Vector + Rerank) -- recommended for best results
sif search query "python decorators"
```

### Search with Options

```bash
# More results
sif search query "python decorators" --limit 20

# Specific collection
sif search query "python decorators" -c my-notes

# Search all collections (including disabled ones)
sif search query "python decorators" --all

# Show score breakdowns across pipeline stages
sif search query "python decorators" --explain

# Increase candidate pool for reranking
sif search query "python decorators" --candidate-limit 30

# Provide intent hint for query expansion
sif search query "python decorators" --intent "programming tutorial"
```

### Output Formats

```bash
# JSON output
sif search query "python" --json

# Markdown table
sif search query "python" --md

# CSV output
sif search query "python" --csv

# XML output
sif search query "python" --xml

# Just file paths
sif search query "python" --files
```

## Managing Collections

### List Collections

```bash
sif collection list
```

Add `--verbose` for detailed information.

### Show Collection Details

```bash
sif collection show my-notes
```

### Rename Collection

```bash
sif collection rename my-notes personal-notes
```

### Delete Collection

```bash
sif collection remove old-collection
```

### Include / Exclude from Default Searches

```bash
# Exclude from default searches
sif collection exclude my-notes

# Include again
sif collection include my-notes
```

### List Files in a Collection

```bash
sif ls my-notes
```

## Adding Context

Context helps improve search relevance by providing background information.

### Global Context

Applies to all searches:

```bash
sif context add global global   "I am a software engineer working with Python and machine learning."
```

### Collection Context

Applies to searches in a specific collection:

```bash
sif context add collection my-notes   "These are my personal notes about programming and technology."
```

### Path Context

Applies to a specific file or directory:

```bash
sif context add path ~/Documents/notes/project-a   "Notes for the Project Alpha rewrite."
```

### List and Remove Context

```bash
sif context list
sif context remove <context-id>
```

## Checking Status

### Overall Status

```bash
sif status
```

The status command shows index path, collection count, document count, chunk
count, contexts, and total database size.

## Updating Index

### Update Changed Documents

```bash
sif index update
```

### Update a Specific Collection

```bash
sif index update --collection my-notes
```

### Force Full Reindex

```bash
sif index update --collection my-notes --force
```

## Generating Embeddings

After indexing text documents, generate embeddings for vector search:

```bash
sif index embed
```

Or for a specific collection:

```bash
sif index embed --collection my-notes
```

## Retrieving Documents

### Get a Single Document

```bash
sif get get <path-or-doc-id>
```

### Get Multiple Documents

```bash
sif get multi-get "*.md"
```

## MCP Server

Start the MCP server for AI assistant integration:

```bash
# Stdio transport (default)
sif mcp stdio

# HTTP transport
sif mcp http --port 8080
```

## Configuration

Create a `.env` file for persistent configuration:

```bash
# ~/.env or ./.env
SIF_DB_PATH=~/.local/share/sif/sif.db
SIF_MODEL_NAME=Qwen/Qwen3-Embedding-0.6B
SIF_EMBEDDING_DIM=1024
SIF_CHUNK_SIZE=512
SIF_LOG_LEVEL=INFO
```

Environment variables are read automatically when SIF starts.

## Common Workflows

### Daily Notes Workflow

```bash
# Morning: Check status
sif status

# Throughout day: Quick searches
sif search query "meeting notes"
sif search query "project ideas"

# Evening: Update index
sif index update
```

### Research Workflow

```bash
# Add research collection
sif collection add ~/Research --name research   --description "Research papers and notes"

# Index
sif index update --collection research

# Search with hybrid pipeline
sif search query "neural networks"   -c research   --limit 20
```

### Documentation Workflow

```bash
# Add docs collection
sif collection add ~/Projects/docs --name docs   --description "Project documentation"

# Add context
sif context add collection docs   "This is technical documentation for my projects."

# Index
sif index update --collection docs

# Search
sif search query "API reference" -c docs
```

## Tips and Tricks

### Use Shell Aliases

Add to your `.bashrc` or `.zshrc`:

```bash
alias ds='sif'
alias ds-search='sif search query'
alias ds-update='sif index update'
alias ds-status='sif status'
```

### Search History

```bash
# Use shell history
history | grep "sif search"

# Or create a search history file
sif search query "" | tee -a ~/.sif_searches
```

### Export Results

```bash
# Save search results
sif search query "python" --json > results.json

# Process with jq
sif search query "python" --json | jq '.results[].document_path'
```

### Batch Document Retrieval

```bash
# Get multiple documents from search results
sif get multi-get "*.md"
```

## Troubleshooting

### Search Returns No Results

1. Check if collection is indexed:
   ```bash
   sif status
   ```

2. Try different search terms

3. Check if documents exist:
   ```bash
   sif ls my-notes
   ```

4. Verify embeddings are generated (for vector/hybrid search):
   ```bash
   sif index embed --collection my-notes
   ```

### Slow Search

1. Use BM25 for faster results:
   ```bash
   sif search search "query"
   ```

2. Limit results:
   ```bash
   sif search query "query" --limit 5
   ```

3. Search a specific collection instead of all:
   ```bash
   sif search query "query" -c my-notes
   ```

### Indexing Issues

1. Check paths exist:
   ```bash
   sif collection show my-notes
   ```

2. Force reindex:
   ```bash
   sif index update --collection my-notes --force
   ```

3. Check logs:
   ```bash
   export SIF_LOG_LEVEL=DEBUG
   sif index update --collection my-notes
   ```

### Cleaning Up

Remove orphaned chunks, embeddings, and expired cache entries:

```bash
sif cleanup
```

## Next Steps

- Learn about [Search Algorithms](search-algorithms.md)
- Explore the [CLI Reference](cli-reference.md)
- Set up the [MCP Server](mcp-server.md)
- Read the full [Configuration](configuration.md) guide

## Getting Help

- Use `--help` for command help:
  ```bash
  sif search query --help
  ```

- Check the [FAQ](#) (coming soon)

- Open an issue on [GitHub](https://github.com/zhangtaolab/sif/issues)
