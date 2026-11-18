<!-- generated-by: gsd-doc-writer -->
# Quick Start Guide

Get up and running with SIF in minutes.

## Prerequisites

Before installing SIF, make sure your system meets these requirements:

- **Python `>= 3.10`** — check your version with `python3 --version`
- **uv `>= 0.9.19`** — the recommended installer; `uv tool install` keeps SIF
  isolated and on PATH
- **SQLite** — nothing to install separately. SIF stores all data locally in a
  SQLite database via Python's built-in `sqlite3` module; the `sqlite-vec`
  dependency for vector tables is installed automatically
- **Operating system** — Linux and macOS are fully supported. Windows is
  degradation-only in v1.2: CLI search and indexing, MCP stdio and HTTP, and
  foreground `sif watch` work; detached watch and service installs are refused
  with a clear message, while POSIX index locking is unavailable and degrades
  to a warning — index writes run unlocked, with WAL + `busy_timeout` still
  protecting database integrity. See the
  [Installation Guide](installation.md#windows) for details.

Optional, depending on which features you plan to use:

- **Vector and hybrid search** — requires an embedding backend that is not
  installed by default. BM25 keyword search works out of the box; for vector
  search, install one of the extras:

  ```bash
  uv tool install 'docsif[embed]'   # sentence-transformers and modelscope backends
  # or
  uv tool install --python 3.12 'docsif[all]'   # adds GGUF (llama-cpp-python) and OpenAI API support
  ```

  The first `sif index embed` run downloads the default embedding model, so it
  needs network access and may take a while. Current defaults are the ModelScope
  backend with `Qwen/Qwen3-Embedding-0.6B` at 1024 dimensions, and 512-token
  chunks with 128-token overlap.

If `sif index embed` exits with `sentence-transformers not installed`, install
the `embed` (or `all`) extra as shown above and retry.

For platform-specific setup (Linux, macOS, Windows) and deeper install
troubleshooting, see the [Installation Guide](installation.md).

## Installation

SIF is distributed on PyPI as `docsif`; the installed command is `sif`. Install
it with uv, the recommended installer:

```bash
# Embedding stack: hybrid and vector search (primary install)
uv tool install 'docsif[embed]'

# Linux: resolve CPU-only torch explicitly (uv 0.9.19+, no CUDA stack)
uv tool install --torch-backend=cpu 'docsif[embed]'

# BM25-only base install
uv tool install docsif
```

The `--torch-backend=cpu` recipe was manually verified on Linux with uv 0.13.7; it is not CI-proven.

The `all` extra adds GGUF (llama-cpp-python) and OpenAI-compatible backends.
Use Python 3.12 for this extra: official `llama-cpp-python` wheels list Python
3.10–3.12, while 3.13 falls back to a source build.

```bash
uv tool install --python 3.12 'docsif[all]'
```

Prefer a one-off run? `uvx --from 'docsif[embed]' sif --help` works without
installing anything.

Verify installation:

```bash
sif --version
```

To work from a source checkout instead (for development):

```bash
git clone https://github.com/zhangtaolab/sif.git
cd sif
pip install -e ".[dev]"
```

See the [Installation Guide](installation.md) for the pip method, the
llama-cpp backend indexes, the degradation matrix, and client configuration.

## First Run

The [Your First Collection](#your-first-collection) walkthrough below sets up a
real collection. To confirm a fresh install works end to end first, run this
self-contained smoke test. It uses BM25 keyword search only, so it works with
the base `uv tool install docsif` — no embedding extras, no model downloads.

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
columns) whose top hit is the `decorators.md` document. The SQLite index database
is created automatically on first use; `sif status` shows where it lives.

Clean up when done — `collection remove` asks for confirmation:

```bash
sif collection remove demo
rm -rf ~/sif-demo
```

If the smoke test passes, continue with [Your First Collection](#your-first-collection)
to index real documents. Vector and hybrid search additionally require an
embedding backend and an embed step (`sif index embed`); see
[Prerequisites](#prerequisites) and [Generating Embeddings](#generating-embeddings).

## Your First Collection

A collection is a group of documents you want to search together.

### 1. Add a Collection

```bash
sif collection add ~/Documents/notes --name my-notes --description "My personal notes"
```

The `PATH` argument must be an existing directory to index. Use `--name` to
give your collection a short identifier. You can also set `--pattern`
(default `**/*.md`) and `--ignore` for fine-grained control over which files
are included. Pass `--no-default` to keep the collection out of default
searches.

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
# BM25 keyword search (works on the base install)
sif search search "python decorators"

# Vector (semantic) search (run sif index embed first)
sif search vsearch "functions that wrap other functions"

# Hybrid search (BM25 + Vector + RRF) -- recommended for best results
sif search query "python decorators"
```

`vsearch` and `query` need an embedding backend and chunk embeddings from
`sif index embed`; `search search` uses BM25 and works on the base install.

### Search with Options

```bash
# More results
sif search query "python decorators" --limit 20

# Paginate results
sif search query "python decorators" --offset 10

# Return one row per matched chunk
sif search query "python decorators" --per-chunk

# Specific collection
sif search query "python decorators" -c my-notes

# Search all collections (including excluded ones)
sif search query "python decorators" --all

# Show score breakdowns across pipeline stages
sif search query "python decorators" --explain

# Enable reranking (requires the embed or all extra)
sif search query "python decorators" --rerank

# Reranker candidate pool (takes effect with --rerank; default 20)
sif search query "python decorators" --candidate-limit 30

# Provide intent hint for query expansion
sif search query "python decorators" --intent "programming tutorial"

# Filter on indexed frontmatter metadata
sif search query "release checklist" \
  --filter '{"operator": "eq", "field": "status", "value": "done"}'
```

Reranking is off by default; `--rerank` (or `SIF_RERANK_ENABLED=1`) enables it.
Run `sif collection metadata` to discover which keys are filterable — see
[Discover Filterable Metadata](#discover-filterable-metadata).

### Output Formats

```bash
# JSON output
sif search query "python" --json

# Markdown output
sif search query "python" --md

# CSV output
sif search query "python" --csv

# XML output
sif search query "python" --xml

# Just file paths
sif search query "python" --files
```

`search search` accepts the same output flags. `search vsearch` supports
`--json` only; it has no CSV, Markdown, XML, or file-list flags.

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

### Discover Filterable Metadata

```bash
# Keys, types, document counts, numeric ranges, and value windows
sif collection metadata my-notes

# Machine-readable report
sif collection metadata my-notes --json
```

`path` and `mtime` are always available as built-in filter fields. Metadata
counts narrow with `--filter '<json>'`, using the same filter grammar as
search. Omit the collection name to report every collection.

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

`sif collection disable` and `sif collection enable` do the same thing as
`exclude` and `include`.

### List Files in a Collection

```bash
sif ls my-notes
```

## Adding Context

Context stores background descriptions for paths, collections, and global
scope. Path contexts are attached to matching search results.

### Global Context

Stores an index-wide description:

```bash
sif context add global global "I am a software engineer working with Python and machine learning."
```

### Collection Context

Stores a description for a collection (target is the collection name):

```bash
sif context add collection my-notes "These are my personal notes about programming and technology."
```

### Path Context

Attaches a description to results for one indexed file (target is the file's
indexed path, not a directory):

```bash
sif context add path ~/Documents/notes/project-a.md "Notes for the Project Alpha rewrite."
```

### List, Prune, and Remove Context

```bash
sif context list
sif context list --type path
sif context prune          # remove path contexts whose files are no longer indexed
sif context remove <context-id>
```

## Checking Status

### Overall Status

```bash
sif status

# sif index status is an alias for sif status
sif index status
```

The status command shows index path, collection count, document count, chunk
count, contexts, total database size, watch state, and vector lag.

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

### Back Up or Reclaim Space

```bash
# Verified backup copy of the index database
sif index backup --output ~/sif-backup.db

# Reclaim unused space after large deletions or reindexes
sif index vacuum
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

`sif index embed --force` re-embeds every document, and
`--chunk-strategy [auto|fixed|markdown|code]` selects the chunker for the run.
Re-running `sif index update` after `sif index embed` is not required; new or
changed documents need another embed pass before they appear in vector results.

## Downloading and Inspecting Models

`sif models pull` downloads model artifacts through SIF's verified cache. With
no argument it downloads the configured embedder; pass a registry name
(`embedding`, `reranker`, `query_expansion`) or a ModelScope `owner/name` id to
fetch something else:

```bash
# The configured embedder (default: Qwen/Qwen3-Embedding-0.6B via ModelScope)
sif models pull

# Download the configured reranker (default: Qwen/Qwen3-Reranker-0.6B)
sif models pull reranker

# Re-download even when the cached copy verifies
sif models pull embedding --force

# Inspect configured, cached, and persisted identity
sif models status
sif models status --json
```

`sif models pull` does not pre-warm sentence-transformers snapshots; the first
`sif index embed` may still download its own model files. The old
`sif pull <MODEL_SPEC>` command still works as a hidden deprecated alias and
prints a deprecation notice on stderr — use `sif models pull` instead. See
[Data Models](models.md) for the cache layout and registry names.

## Retrieving Documents

### Get a Single Document

```bash
sif get get <path-or-doc-id>
```

Add `--lines 50 --line-numbers` for a line range of a long document.

### Get Multiple Documents

```bash
sif get multi-get "*.md"
sif get multi-get "doc-id-1,notes/python_guide.md"
```

`multi-get` truncates each document at 100 KB by default; use `--max-bytes` to
change the cap.

## Live Indexing

`sif watch` keeps the index current as files change. It is BM25-only by
default; pass `--embed` to also write vectors for changed documents.

```bash
# Foreground watcher over the default collections
sif watch

# Watch specific collections and update vectors too
sif watch -c my-notes --embed

# Detached background daemon, then stop it
sif watch --detach
sif watch --stop

# Install as a launchd LaunchAgent (macOS) or systemd user unit (Linux)
sif watch --install-service

# Stop and remove the installed service
sif watch --uninstall-service
```

The detached daemon picks up collection-set changes live; the foreground
watcher requires a restart after changing collections.

## Query Suggestions

```bash
# Prefix completions, did-you-mean rewrites, and local query history
sif suggest "python dec"

# Machine-readable output
sif suggest "python dec" --json

# Cap entries per section (default 5)
sif suggest "python dec" --limit 3

# Delete the locally recorded query history
sif suggest --clear-history
```

Executed searches are recorded locally (disable with
`SIF_QUERY_HISTORY_ENABLED=0`) and power the history section of
`sif suggest`.

## Measuring Search Quality

`sif eval --personal` measures search quality on your own indexed corpus. It
needs at least 50 indexed documents in scope and synthesizes deterministic
known-item queries from them. Hybrid retrieval is the default, so it needs the
embedding backend; pass `--bm25-only` on a base install.

```bash
# Hybrid quality report; runs are saved under the cache directory by default
sif eval --personal

# Raise the held-out floor (101+ makes the 0.01 mean-delta gate admissible)
sif eval --personal --min-heldout 101

# Measure BM25 only, without loading an embedder
sif eval --personal --bm25-only

# Machine-readable report
sif eval --personal --json

# Re-evaluate a saved run's query set and report paired deltas
sif eval --personal --compare <saved-run.json>
```

Use `sif bench` for a labeled JSON fixture instead of your own corpus:

```bash
sif bench fixture.json --all --json

# Also measure the rerank-on state
sif bench fixture.json --rerank
```

See [Benchmarking](benchmarking.md) for fixture formats, fusion sweeps, and the
noise gate.

## MCP Server

Start the MCP server for AI assistant integration:

```bash
# Stdio transport
sif mcp stdio

# HTTP transport (Streamable HTTP at /mcp, health check at /health)
sif mcp http --port 8080

# Run the HTTP server as a detached background daemon
sif mcp daemon

# Stop the background daemon
sif mcp daemon --stop
```

The server exposes seven read-only tools: `query`, `get`, `multi_get`,
`status`, `metadata`, `lex_search`, and `vec_search`. None of them mutates the
index. See the [MCP Server](mcp-server.md) guide for client configuration,
`SIF_MCP_WATCH=1`, and transport security.

## Configuration

Create a `.env` file in the directory where you run SIF for persistent
configuration (SIF loads it from the current working directory):

```bash
# ./.env (loaded from the current working directory)
SIF_DB_PATH=~/.local/share/sif/sif.db
SIF_MODEL_NAME=Qwen/Qwen3-Embedding-0.6B
SIF_MODEL_TYPE=modelscope
SIF_EMBEDDING_DIM=1024
SIF_CHUNK_SIZE=512
SIF_CHUNK_OVERLAP=128
SIF_LOG_LEVEL=INFO
```

Current defaults are ModelScope `Qwen/Qwen3-Embedding-0.6B` at 1024
dimensions, 512-token chunks with 128-token overlap, RRF `k=60` with equal
BM25/vector weights, and reranking off. Environment variables use the `SIF_`
prefix and are read automatically when SIF starts; CLI verbosity is controlled
by the group-level `-v`/`--verbose` and `-q`/`--quiet` flags. See the full
[Configuration](configuration.md) reference for every setting, including watch,
reranker, model-cache, and pre-search refresh options.

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
sif collection add ~/Research --name research --description "Research papers and notes"

# Index and embed
sif index update --collection research
sif index embed --collection research

# Search with hybrid pipeline
sif search query "neural networks" -c research --limit 20
```

### Documentation Workflow

```bash
# Add docs collection
sif collection add ~/Projects/docs --name docs --description "Project documentation"

# Add context
sif context add collection docs "This is technical documentation for my projects."

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

SIF records executed searches locally and exposes them through `sif suggest`:

```bash
# History alongside prefix completions and did-you-mean rewrites
sif suggest "python dec"

# Machine-readable output
sif suggest "python dec" --json
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

2. Try different search terms, or ask for suggestions:
   ```bash
   sif suggest "your query"
   ```

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

3. Leave reranking off (the default), or narrow the candidate pool when it is
   enabled:
   ```bash
   sif search query "query" --rerank --candidate-limit 10
   ```

4. Search a specific collection instead of all:
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

3. Re-run with verbose output. The verbose flag is a group option, so it goes
   before the subcommand: `sif -v index update --collection my-notes`

### Personal Eval Fails Before Running

`sif eval --personal` exits non-zero when the corpus is too small (fewer than
50 indexed documents in scope) or when the embedder is unavailable. Index more
documents, or pass `--bm25-only` to measure the BM25 path without an embedding
backend.

### Cleaning Up

Remove orphaned chunks, embeddings, and expired cache entries
(`sif cleanup` asks for confirmation):

```bash
sif cleanup
```

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

Read-only commands such as `sif status`, `sif ls`, and the search subcommands
print `No index found` when no database exists yet at the resolved index path —
nothing has been indexed. Add a collection and index it:

```bash
sif collection add ~/Documents/notes --name my-notes
sif index update
```

If you expected an existing index, check that `SIF_DB_PATH` (or the
`--index`/`-i` option) points at the database you want. When an index exists at
the resolved path, `sif status` lists its Index Path; the path comes from
`SIF_DB_PATH`, the `--index`/`-i` option, or the platform default (see
[Configuration](#configuration)).

### Vector or hybrid search exits with `sqlite-vec extension is not available`

`sqlite-vec` ships as a core dependency, but it loads into SQLite as an
extension. When the Python `sqlite3` module cannot load it, SIF skips the load
at the database layer and `VectorSearcher` raises this error on use — while BM25
search (`sif search search <query>`) keeps working. Try reinstalling the
extension first:

```bash
pip install --force-reinstall sqlite-vec
```

If the error persists, the Python interpreter in use was built without SQLite
extension-loading support (some system Pythons are). Reinstall SIF under a
Python from python.org, Homebrew, or pyenv and retry.

### `Embedding backend not installed`

`sif index embed` and vector/hybrid search need an embedding backend, which the
base install does not include. Install the `embed` (or `all`) extra — see
[Prerequisites](#prerequisites) for the exact commands. The underlying error
may name the specific missing package (for example
`sentence-transformers not installed`).

### `collection add` fails with `Directory ... does not exist`

`collection add` validates the `PATH` argument before it does anything else,
so the directory must already exist. Create it first, then retry:

```bash
mkdir -p ~/Documents/notes
sif collection add ~/Documents/notes --name my-notes
```

The command also requires `--name`; omitting it fails with
`Missing option '--name' / '-n'.`

## Next Steps

- Install options and platform notes: [Installation Guide](installation.md)
- Learn about [Search Algorithms](search-algorithms.md)
- Explore the [CLI Reference](cli-reference.md)
- Set up the [MCP Server](mcp-server.md)
- Read the full [Configuration](configuration.md) guide
- Model cache and backends: [Data Models](models.md)
- Search quality measurement: [Benchmarking](benchmarking.md)
- Contribute: [Development](development.md), [Testing](testing.md), and
  [Contributing](contributing.md)

## Getting Help

- Use `--help` for command help:
  ```bash
  sif search query --help
  ```

- Browse the [documentation index](index.md) for the full guides.

- Open an issue on [GitHub](https://github.com/zhangtaolab/sif/issues)
