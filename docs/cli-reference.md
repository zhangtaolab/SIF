# CLI Reference

Complete reference for all SIF CLI commands.

## Global Options

These options can be used with any command:

| Option | Short | Type | Default | Description |
|--------|-------|------|---------|-------------|
| `--version` | `` | flag | `false` | Show the version and exit. |
| `--index` | `-i` | path | — | Path to the index database |
| `--verbose` | `-v` | flag | `false` | Enable verbose output |
| `--quiet` | `-q` | flag | `false` | Suppress non-error output |

## Command Overview

```
sif
├── collection      Manage document collections.
│   ├── add             Add a new collection.
│   ├── remove          Remove a collection.
│   ├── rename          Rename a collection.
│   ├── list            List all collections.
│   ├── show            Show collection details.
│   ├── enable          Enable a collection for default searches.
│   ├── disable         Disable a collection from default searches.
│   ├── update-cmd      Set or clear a pre-index shell command for a collection.
│   ├── include         Include a collection in default searches.
│   ├── exclude         Exclude a collection from default searches.
│   └── ls              List files in a collection.
├── context         Manage contextual descriptions for paths, collections, and global scope.
│   ├── add             Add context for a path, collection, or global scope.
│   ├── remove          Remove a context by its ID.
│   ├── list            List all contexts.
│   ├── prune           Remove orphaned path contexts (whose target paths no longer exist in the index).
│   └── rm              Remove a context by its ID.
├── index           Index management commands.
│   ├── update          Update the index by scanning collections.
│   ├── embed           Generate embeddings for documents.
│   └── status          Show index status.
├── search          Search commands.
│   ├── search          Search documents using BM25.
│   ├── vsearch         Search documents using vector similarity.
│   └── query           Search documents using hybrid approach (BM25 + Vector + RRF).
├── get             Retrieve documents.
│   ├── get             Get a document by path or document ID.
│   └── multi-get       Get multiple documents matching a pattern.
├── mcp             MCP server commands.
│   ├── stdio           Run MCP server in stdio mode.
│   ├── http            Run MCP server in HTTP mode.
│   └── daemon          Run MCP server as a daemon.
├── ls              List indexed documents as a virtual file tree.
├── pull            Download a GGUF model file.
├── bench           Run benchmark evaluation against a fixture file.
├── suggest         Show prefix completions, did-you-mean rewrites, and query history.
├── watch           Watch collections and keep the index current as files change.
├── status          Show index status.
└── cleanup         Clean up the index (remove orphaned entries).
```

## Collection Commands

### `collection add`

Add a new collection.

```bash
sif collection add [OPTIONS]
```

**Arguments:**

| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `path` | directory | Yes |  |

**Options:**

| Option | Short | Type | Default | Description |
|--------|-------|------|---------|-------------|
| `--name` | `-n` | text | — | Collection name |
| `--pattern` | `-p` | text | `**/*.md` | File pattern to match |
| `--ignore` | `-i` | text[] | — | Patterns to ignore |
| `--description` | `-d` | text | — | Collection description |
| `--no-default` | `—` | flag | `false` | Don't include in default searches |

### `collection disable`

Disable a collection from default searches.

```bash
sif collection disable [OPTIONS]
```

**Arguments:**

| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `name` | text | Yes |  |

### `collection enable`

Enable a collection for default searches.

```bash
sif collection enable [OPTIONS]
```

**Arguments:**

| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `name` | text | Yes |  |

### `collection exclude`

Exclude a collection from default searches.

```bash
sif collection exclude [OPTIONS]
```

**Arguments:**

| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `name` | text | Yes |  |

### `collection include`

Include a collection in default searches.

```bash
sif collection include [OPTIONS]
```

**Arguments:**

| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `name` | text | Yes |  |

### `collection list`

List all collections.

```bash
sif collection list [OPTIONS]
```

**Options:**

| Option | Short | Type | Default | Description |
|--------|-------|------|---------|-------------|
| `--verbose` | `-v` | flag | `false` | Show detailed information |

### `collection ls`

List files in a collection.

```bash
sif collection ls [OPTIONS]
```

**Arguments:**

| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `name` | text | Yes |  |
| `subpath` | text | No |  |

### `collection remove`

Remove a collection.

```bash
sif collection remove [OPTIONS]
```

**Arguments:**

| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `name` | text | Yes |  |

**Options:**

| Option | Short | Type | Default | Description |
|--------|-------|------|---------|-------------|
| `--yes` | `—` | flag | `false` | Confirm the action without prompting. |

### `collection rename`

Rename a collection.

```bash
sif collection rename [OPTIONS]
```

**Arguments:**

| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `old_name` | text | Yes |  |
| `new_name` | text | Yes |  |

### `collection show`

Show collection details.

```bash
sif collection show [OPTIONS]
```

**Arguments:**

| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `name` | text | Yes |  |

### `collection update-cmd`

Set or clear a pre-index shell command for a collection.

```bash
sif collection update-cmd [OPTIONS]
```

**Arguments:**

| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `name` | text | Yes |  |

**Options:**

| Option | Short | Type | Default | Description |
|--------|-------|------|---------|-------------|
| `--cmd` | `-c` | text | — | Shell command to run before indexing |
| `--clear` | `—` | flag | `false` | Clear the pre-update command |

## Context Commands

### `context add`

Add context for a path, collection, or global scope.

```bash
sif context add [OPTIONS]
```

**Arguments:**

| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `type` | choice | Yes |  |
| `target` | text | Yes |  |
| `content` | text | Yes |  |

### `context list`

List all contexts.

```bash
sif context list [OPTIONS]
```

**Options:**

| Option | Short | Type | Default | Description |
|--------|-------|------|---------|-------------|
| `--type` | `—` | choice [path|collection|global] | — | Filter by context type |

### `context prune`

Remove orphaned path contexts (whose target paths no longer exist in the index).

```bash
sif context prune [OPTIONS]
```

### `context remove`

Remove a context by its ID.

```bash
sif context remove [OPTIONS]
```

**Arguments:**

| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `context_id` | text | Yes |  |

### `context rm`

Remove a context by its ID.

```bash
sif context rm [OPTIONS]
```

**Arguments:**

| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `context_id` | text | Yes |  |

## Get Commands

### `get get`

Get a document by path or document ID.

Path arguments are canonicalized (~ expansion and symlink resolution)
before lookup, so alias paths that resolve to the same file as the
indexed path also match. If no indexed document matches, the argument
is treated as a filesystem path: a readable file is printed directly
from disk even if it was never indexed.

```bash
sif get get [OPTIONS]
```

**Arguments:**

| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `path_or_docid` | text | Yes |  |

**Options:**

| Option | Short | Type | Default | Description |
|--------|-------|------|---------|-------------|
| `--from-line` | `-f` | integer | — | Start from line number |
| `--lines` | `-l` | integer | — | Number of lines to show |
| `--line-numbers` | `—` | flag | `false` | Show line numbers |

### `get multi-get`

Get multiple documents matching a pattern.

Absolute glob patterns are canonicalized before path matching, so
symlinked directory prefixes match indexed paths; bare filenames always
match raw.

```bash
sif get multi-get [OPTIONS]
```

**Arguments:**

| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `pattern` | text | Yes |  |

**Options:**

| Option | Short | Type | Default | Description |
|--------|-------|------|---------|-------------|
| `--max-bytes` | `-b` | integer | `100000` | Max bytes per file |
| `--line-numbers` | `—` | flag | `false` | Show line numbers |

## Index Commands

### `index embed`

Generate embeddings for documents.

```bash
sif index embed [OPTIONS]
```

**Options:**

| Option | Short | Type | Default | Description |
|--------|-------|------|---------|-------------|
| `--collection` | `-c` | text | — | Embed specific collection only |
| `--force` | `-f` | flag | `false` | Force re-embed all documents |
| `--chunk-strategy` | `—` | choice [auto|fixed|markdown|code] | `auto` | Chunking strategy |
| `--model` | `-m` | text | — | Embedding model name |
| `--model-type` | `—` | choice [sentence_transformers|gguf|openai|modelscope] | — | Embedding model type override |

### `index status`

Show index status.

```bash
sif index status [OPTIONS]
```

### `index update`

Update the index by scanning collections.

```bash
sif index update [OPTIONS]
```

**Options:**

| Option | Short | Type | Default | Description |
|--------|-------|------|---------|-------------|
| `--collection` | `-c` | text | — | Update specific collection only |
| `--force` | `-f` | flag | `false` | Force re-index all documents |

## Search Commands

### `search query`

Search documents using hybrid approach (BM25 + Vector + RRF).

This is the recommended search command for best results.

```bash
sif search query [OPTIONS]
```

**Arguments:**

| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `query` | text | Yes |  |

**Options:**

| Option | Short | Type | Default | Description |
|--------|-------|------|---------|-------------|
| `--limit` | `-n` | integer | `10` | Number of results |
| `--collection` | `-c` | text[] | — | Collection to search |
| `--all` | `—` | flag | `false` | Search all collections |
| `--min-score` | `—` | float | `0.0` | Minimum score threshold |
| `--full` | `—` | flag | `false` | Include full content |
| `--explain` | `—` | flag | `false` | Show score breakdowns across pipeline stages |
| `--candidate-limit` | `-C` | integer range | — | Reranker candidate pool size (default: SIF_RERANK_CANDIDATE_LIMIT or 20; clamped to 5-50) |
| `--rerank` | `—` | flag | `false` | Rerank results (default: SIF_RERANK_ENABLED or false) |
| `--intent` | `—` | text | — | Search intent hint for query expansion |
| `--rrf-k` | `—` | integer range | — | RRF k constant for hybrid fusion (default: SIF_RRF_K or 60) |
| `--bm25-weight` | `—` | float range | — | BM25 fusion weight (default: SIF_BM25_WEIGHT or 1.0) |
| `--vector-weight` | `—` | float range | — | Vector fusion weight (default: SIF_VECTOR_WEIGHT or 1.0) |
| `--line-numbers` | `—` | flag | `false` | Show line numbers in content |
| `--json` | `—` | flag | `false` | Output as JSON |
| `--csv` | `—` | flag | `false` | Output as CSV |
| `--md` | `—` | flag | `false` | Output as Markdown |
| `--xml` | `—` | flag | `false` | Output as XML |
| `--files` | `—` | flag | `false` | Output file paths only |
| `--model-type` | `—` | choice [sentence_transformers|gguf|openai|modelscope] | — | Embedding model type override |
| `--no-refresh` | `—` | flag | `false` | Skip the pre-search drift refresh check |
| `--quiet` | `-q` | flag | `false` | Suppress non-error output |

### `search search`

Search documents using BM25.

```bash
sif search search [OPTIONS]
```

**Arguments:**

| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `query` | text | Yes |  |

**Options:**

| Option | Short | Type | Default | Description |
|--------|-------|------|---------|-------------|
| `--limit` | `-n` | integer | `10` | Number of results |
| `--collection` | `-c` | text[] | — | Collection to search |
| `--all` | `—` | flag | `false` | Search all collections |
| `--min-score` | `—` | float | `0.0` | Minimum score threshold |
| `--full` | `—` | flag | `false` | Include full content |
| `--explain` | `—` | flag | `false` | Show search explanation |
| `--line-numbers` | `—` | flag | `false` | Show line numbers in content |
| `--json` | `—` | flag | `false` | Output as JSON |
| `--csv` | `—` | flag | `false` | Output as CSV |
| `--md` | `—` | flag | `false` | Output as Markdown |
| `--xml` | `—` | flag | `false` | Output as XML |
| `--files` | `—` | flag | `false` | Output file paths only |
| `--no-refresh` | `—` | flag | `false` | Skip the pre-search drift refresh check |
| `--quiet` | `-q` | flag | `false` | Suppress non-error output |

### `search vsearch`

Search documents using vector similarity.

```bash
sif search vsearch [OPTIONS]
```

**Arguments:**

| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `query` | text | Yes |  |

**Options:**

| Option | Short | Type | Default | Description |
|--------|-------|------|---------|-------------|
| `--limit` | `-n` | integer | `10` | Number of results |
| `--collection` | `-c` | text[] | — | Collection to search |
| `--all` | `—` | flag | `false` | Search all collections |
| `--min-score` | `—` | float | `0.0` | Minimum score threshold |
| `--full` | `—` | flag | `false` | Include full content |
| `--line-numbers` | `—` | flag | `false` | Show line numbers in content |
| `--json` | `—` | flag | `false` | Output as JSON |
| `--model-type` | `—` | choice [sentence_transformers|gguf|openai|modelscope] | — | Embedding model type override |
| `--no-refresh` | `—` | flag | `false` | Skip the pre-search drift refresh check |
| `--quiet` | `-q` | flag | `false` | Suppress non-error output |

## MCP Commands

### `mcp daemon`

Run MCP server as a daemon.

```bash
sif mcp daemon [OPTIONS]
```

**Options:**

| Option | Short | Type | Default | Description |
|--------|-------|------|---------|-------------|
| `--host` | `-h` | text | `127.0.0.1` | Host to bind to |
| `--port` | `-p` | integer | `3000` | Port to listen on |
| `--pid-file` | `—` | text | — | PID file path |
| `--log-file` | `—` | text | — | Log file path |
| `--stop` | `—` | flag | `false` | Stop the daemon |

### `mcp http`

Run MCP server in HTTP mode.

```bash
sif mcp http [OPTIONS]
```

**Options:**

| Option | Short | Type | Default | Description |
|--------|-------|------|---------|-------------|
| `--host` | `-h` | text | `127.0.0.1` | Host to bind to |
| `--port` | `-p` | integer | `3000` | Port to listen on |
| `--reload` | `—` | flag | `false` | Enable auto-reload |
| `--cors-origins` | `—` | text[] | — | CORS allowed origins |

### `mcp stdio`

Run MCP server in stdio mode.

```bash
sif mcp stdio [OPTIONS]
```

## Other Commands

### `bench`

Run benchmark evaluation against a fixture file.

Fixture format (JSON):
    {
        "queries": [
            {
                "query": "search terms",
                "relevant_docids": ["doc-id-1", "doc-id-2"],
                "collections": ["optional-collection-filter"]
            }
        ]
    }

Graded fixtures (Phase 16) instead declare corpus_root/relevance_key and
per-query category/split/relevance; the report layers nDCG@10, Hit@10,
warmed p50/p95 latency and a per-category breakdown over the legacy flat
metrics. With --sweep, the 45-configuration declared grid
(rrf_k x bm25_weight x vector_weight) is measured on the tuning split
only and ranked with the 0.01 tie-group rule. With --rerank, the
rerank-on state is measured beside the always-measured off state.

```bash
sif bench [OPTIONS]
```

**Arguments:**

| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `fixture` | path | Yes |  |

**Options:**

| Option | Short | Type | Default | Description |
|--------|-------|------|---------|-------------|
| `--limit` | `-n` | integer | `10` | Number of results per query |
| `--candidate-limit` | `-C` | integer range | — | Reranker candidate pool size (default: SIF_RERANK_CANDIDATE_LIMIT or 20; clamped to 5-50) |
| `--collection` | `-c` | text[] | — | Collection to search |
| `--all` | `—` | flag | `false` | Search all collections |
| `--sweep` | `—` | flag | `false` | Sweep the declared rrf_k/weight grid |
| `--rerank` | `—` | flag | `false` | Also measure the rerank-on state (default: off only) |
| `--model-type` | `—` | choice [sentence_transformers|gguf|openai|modelscope] | — | Embedding model type override |
| `--json` | `—` | flag | `false` | Output as JSON |

### `cleanup`

Clean up the index (remove orphaned entries).

```bash
sif cleanup [OPTIONS]
```

**Options:**

| Option | Short | Type | Default | Description |
|--------|-------|------|---------|-------------|
| `--yes` | `—` | flag | `false` | Confirm the action without prompting. |

### `ls`

List indexed documents as a virtual file tree.

```bash
sif ls [OPTIONS]
```

**Arguments:**

| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `collection` | text | No |  |
| `subpath` | text | No |  |

### `pull`

Download a GGUF model file.

```bash
sif pull [OPTIONS]
```

**Arguments:**

| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `model_spec` | text | Yes |  |

**Options:**

| Option | Short | Type | Default | Description |
|--------|-------|------|---------|-------------|
| `--cache-dir` | `—` | path | — | Custom cache directory |

### `status`

Show index status.

```bash
sif status [OPTIONS]
```

### `suggest`

Show prefix completions, did-you-mean rewrites, and query history.

```bash
sif suggest [OPTIONS]
```

**Arguments:**

| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `query` | text | No |  |

**Options:**

| Option | Short | Type | Default | Description |
|--------|-------|------|---------|-------------|
| `--limit` | `—` | integer range | `5` | Maximum entries per section |
| `--json` | `—` | flag | `false` | Output as JSON |
| `--quiet` | `-q` | flag | `false` | Suppress table output |
| `--clear-history` | `—` | flag | `false` | Delete all recorded query history |

### `watch`

Watch collections and keep the index current as files change.

Collection-set changes are picked up live by the detached daemon
(--detach); the foreground watch still requires a restart in this MVP.

```bash
sif watch [OPTIONS]
```

**Options:**

| Option | Short | Type | Default | Description |
|--------|-------|------|---------|-------------|
| `--collection` | `-c` | text[] | — | Watch only the named collection(s); repeatable. The detached daemon picks up collection-set changes live; the foreground watch requires a restart. |
| `--embed` | `—` | flag | `false` | Also write vector embeddings for changed documents (opt-in; default is BM25-only) |
| `--no-embed` | `—` | flag | `false` | Force BM25-only updates even when SIF_WATCH_UPDATE_DEPTH=embed |
| `--verbose` | `—` | flag | `false` | Print per-file event lines instead of per-batch summaries |
| `--detach` | `—` | flag | `false` | Run the watcher in the background as a detached daemon and print its PID; logs go to the platform log dir unless --log-file is given |
| `--stop` | `—` | flag | `false` | Stop the detached watch daemon (SIGTERM, bounded wait, SIGKILL fallback) |
| `--log-file` | `—` | text | — | Daemon log file path (requires --detach; default: platform log dir) |
| `--install-service` | `—` | flag | `false` | Generate and install a launchd LaunchAgent (macOS) or systemd user unit (Linux) running the FOREGROUND watcher under the OS supervisor; the -c and depth (--embed/--no-embed) flags given now are baked into the service definition |
| `--uninstall-service` | `—` | flag | `false` | Stop the installed watch service and remove its artifact |

## Output Formats

Several commands support multiple output formats via flags:

| Format | Flag | Description |
|--------|------|-------------|
| Table (default) | — | Rich formatted table |
| JSON | `--json` | Machine-readable JSON |
| CSV | `--csv` | Comma-separated values |
| Markdown | `--md` | Markdown table format |
| XML | `--xml` | XML format |
| Files | `--files` | Plain file paths, one per line |

## Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | General error |
| 2 | Invalid arguments |
| 130 | `sif watch`: second SIGINT/SIGTERM during shutdown — immediate exit without the final flush |

## Common Workflows

**Setting up a new collection:**
```bash
# Add a collection
sif collection add ~/Documents/notes --name my-notes --description "Personal notes"

# Update index
sif index update --collection my-notes

# Search
sif search query "python tips"
```

**Managing collection visibility:**
```bash
# Exclude from default searches
sif collection exclude my-notes

# Include again
sif collection include my-notes

# Set pre-update command
sif collection update-cmd my-notes --cmd "git pull"
```

**Adding context:**
```bash
# Add global context
sif context add global global "I am a software engineer."

# Add collection context
sif context add collection my-notes "These are my programming notes."

# List contexts
sif context list

# Prune orphaned contexts
sif context prune
```

**Hybrid search with options:**
```bash
sif search query "python decorators" --explain --candidate-limit 30 --limit 10
```
