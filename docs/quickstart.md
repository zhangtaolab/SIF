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
sif search query "python" --json | jq '.[].path'
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

## Prerequisites

Before installing SIF, make sure your system meets these requirements:

- **Python `>= 3.10`** — check your version with `python3 --version`
- **pip** — included with Python; any recent version works
- **SQLite** — nothing to install separately. SIF stores all data locally in a
  SQLite database via Python's built-in `sqlite3` module; the `sqlite-vec`
  dependency for vector tables is installed automatically

Optional, depending on which features you plan to use:

- **Vector and hybrid search** — requires an embedding backend that is not
  installed by default. BM25 keyword search works out of the box; for vector
  search, install one of the extras:

  ```bash
  pip install "sif[embed]"   # sentence-transformers and modelscope backends
  # or
  pip install "sif[all]"     # adds GGUF (llama-cpp-python) and OpenAI API support
  ```

  The first `sif index embed` run downloads the default embedding model
  (`Qwen/Qwen3-Embedding-0.6B`), so it needs network access and may take a
  while on first use.

If `sif index embed` exits with `sentence-transformers not installed`, install
the `embed` (or `all`) extra as shown above and retry.

For platform-specific setup (Linux, macOS, Windows) and deeper install
troubleshooting, see the [Installation Guide](installation.md).

## First Run

The [Your First Collection](#your-first-collection) walkthrough above sets up a
real collection. To confirm a fresh install works end to end first, run this
self-contained smoke test. It uses BM25 keyword search only, so it works with
the base `pip install sif` — no embedding extras, no model downloads.

```bash
# 1. Create a tiny test corpus
mkdir -p ~/sif-demo
printf '# Decorators\n\nDecorators wrap a function to add behavior around it.\n' \
  > ~/sif-demo/decorators.md
printf '# Ideas\n\nA local-first search engine for personal notes.\n' > ~/sif-demo/ideas.md

# 2. Register the directory as a collection and index it
sif collection add ~/sif-demo --name demo
sif index update --collection demo

# 3. Search it
sif search search "decorators"
```

The final command prints a ranked results table (with `Score` and `Snippet`
columns) whose top hit is `~/sif-demo/decorators.md`. The SQLite index database
is created automatically on first use; `sif status` shows where it lives.

Clean up when done — `collection remove` asks for confirmation:

```bash
sif collection remove demo
rm -rf ~/sif-demo
```

If the smoke test passes, continue with [Your First Collection](#your-first-collection)
to index real documents. Vector and hybrid search additionally require an
embedding backend and an embed step (`sif index embed`); see
[Prerequisites](#prerequisites).

## Common Setup Issues

First-launch problems and their fixes. For search quality and indexing issues
after setup, see [Troubleshooting](#troubleshooting) above.

### `sif: command not found` after installation

The `sif` script installed fine, but its directory is not on your `PATH`. This
is common with `pip install --user` (scripts land in `~/.local/bin` on Linux or
`~/Library/Python/<version>/bin` on macOS). Add that directory to your `PATH`,
or invoke the CLI as a module instead:

```bash
python3 -m sif.cli.main --help
```

### Yellow `No index found` message

SIF prints `No index found` when no database exists yet at the resolved index
path — nothing has been indexed. Add a collection and index it:

```bash
sif collection add ~/Documents/notes --name my-notes
sif index update
```

If you expected an existing index, run `sif status` and check the listed
Index Path: it comes from `SIF_DB_PATH`, the `--index`/`-i` option, or the
platform default (see [Configuration](#configuration)).

### Vector or hybrid search exits with `sqlite-vec extension is not available`

`sqlite-vec` ships as a core dependency, but it loads into SQLite as an
extension. When the Python `sqlite3` module cannot load it, SIF skips the load
at the database layer and `VectorSearcher` raises this error on use — while BM25
search (`sif search search <query>`) keeps working. Try reinstalling the extension
first:

```bash
pip install --force-reinstall sqlite-vec
```

If the error persists, the Python interpreter in use was built without SQLite
extension-loading support (some system Pythons are). Reinstall SIF under a
Python from python.org, Homebrew, or pyenv and retry.

### `Embedding backend not installed`

`sif index embed` and vector/hybrid search need an embedding backend, which the
base install does not include. Install the `embed` (or `all`) extra — see
[Prerequisites](#prerequisites) for the exact commands.
