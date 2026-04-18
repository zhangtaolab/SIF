# CLI Reference

Complete reference for all DocSift CLI commands.

## Global Options

These options can be used with any command:

| Option | Short | Type | Default | Description |
|--------|-------|------|---------|-------------|
| `--version` | `` | flag | `false` | Show the version and exit. |
| `--index` | `-i` | path | — | Path to the index database |
| `--config` | `-c` | path | `/Users/forrest/.docsift/config.yaml` | Path to the configuration file |
| `--verbose` | `-v` | flag | `false` | Enable verbose output |
| `--quiet` | `-q` | flag | `false` | Suppress non-error output |

## Command Overview

```
docsift
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

This is the recommended search command for best results.

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

├── status          Show index status.
└── cleanup         Clean up the index (remove orphaned entries).
```

## Collection Commands

### `collection add`

Add a new collection.

```bash
docsift collection add [OPTIONS]
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
docsift collection disable [OPTIONS]
```

**Arguments:**

| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `name` | text | Yes |  |

### `collection enable`

Enable a collection for default searches.

```bash
docsift collection enable [OPTIONS]
```

**Arguments:**

| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `name` | text | Yes |  |

### `collection exclude`

Exclude a collection from default searches.

```bash
docsift collection exclude [OPTIONS]
```

**Arguments:**

| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `name` | text | Yes |  |

### `collection include`

Include a collection in default searches.

```bash
docsift collection include [OPTIONS]
```

**Arguments:**

| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `name` | text | Yes |  |

### `collection list`

List all collections.

```bash
docsift collection list [OPTIONS]
```

**Options:**

| Option | Short | Type | Default | Description |
|--------|-------|------|---------|-------------|
| `--verbose` | `-v` | flag | `false` | Show detailed information |

### `collection ls`

List files in a collection.

```bash
docsift collection ls [OPTIONS]
```

**Arguments:**

| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `name` | text | Yes |  |
| `subpath` | text | No |  |

### `collection remove`

Remove a collection.

```bash
docsift collection remove [OPTIONS]
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
docsift collection rename [OPTIONS]
```

**Arguments:**

| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `old_name` | text | Yes |  |
| `new_name` | text | Yes |  |

### `collection show`

Show collection details.

```bash
docsift collection show [OPTIONS]
```

**Arguments:**

| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `name` | text | Yes |  |

### `collection update-cmd`

Set or clear a pre-index shell command for a collection.

```bash
docsift collection update-cmd [OPTIONS]
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
docsift context add [OPTIONS]
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
docsift context list [OPTIONS]
```

**Options:**

| Option | Short | Type | Default | Description |
|--------|-------|------|---------|-------------|
| `--type` | `—` | choice | — | Filter by context type |

### `context prune`

Remove orphaned path contexts (whose target paths no longer exist in the index).

```bash
docsift context prune [OPTIONS]
```

### `context remove`

Remove a context by its ID.

```bash
docsift context remove [OPTIONS]
```

**Arguments:**

| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `context_id` | text | Yes |  |

### `context rm`

Remove a context by its ID.

```bash
docsift context rm [OPTIONS]
```

**Arguments:**

| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `context_id` | text | Yes |  |

## Get Commands

### `get get`

Get a document by path or document ID.

```bash
docsift get get [OPTIONS]
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

```bash
docsift get multi-get [OPTIONS]
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
docsift index embed [OPTIONS]
```

**Options:**

| Option | Short | Type | Default | Description |
|--------|-------|------|---------|-------------|
| `--collection` | `-c` | text | — | Embed specific collection only |
| `--force` | `-f` | flag | `false` | Force re-embed all documents |
| `--chunk-strategy` | `—` | text | `auto` | Chunking strategy |
| `--model` | `-m` | text | — | Embedding model name |
| `--model-type` | `—` | choice | — | Embedding model type override |

### `index status`

Show index status.

```bash
docsift index status [OPTIONS]
```

### `index update`

Update the index by scanning collections.

```bash
docsift index update [OPTIONS]
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
docsift search query [OPTIONS]
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
| `--candidate-limit` | `-C` | integer range | `20` | Reranker candidate pool size |
| `--intent` | `—` | text | — | Search intent hint for query expansion |
| `--line-numbers` | `—` | flag | `false` | Show line numbers in content |
| `--json` | `—` | flag | `false` | Output as JSON |
| `--csv` | `—` | flag | `false` | Output as CSV |
| `--md` | `—` | flag | `false` | Output as Markdown |
| `--xml` | `—` | flag | `false` | Output as XML |
| `--files` | `—` | flag | `false` | Output file paths only |
| `--model-type` | `—` | choice | — | Embedding model type override |

### `search search`

Search documents using BM25.

```bash
docsift search search [OPTIONS]
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

### `search vsearch`

Search documents using vector similarity.

```bash
docsift search vsearch [OPTIONS]
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
| `--model-type` | `—` | choice | — | Embedding model type override |

## MCP Commands

### `mcp daemon`

Run MCP server as a daemon.

```bash
docsift mcp daemon [OPTIONS]
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
docsift mcp http [OPTIONS]
```

**Options:**

| Option | Short | Type | Default | Description |
|--------|-------|------|---------|-------------|
| `--host` | `-h` | text | `127.0.0.1` | Host to bind to |
| `--port` | `-p` | integer | `3000` | Port to listen on |
| `--reload` | `—` | flag | `false` | Enable auto-reload |

### `mcp stdio`

Run MCP server in stdio mode.

```bash
docsift mcp stdio [OPTIONS]
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


```bash
docsift bench [OPTIONS]
```

**Arguments:**

| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `fixture` | path | Yes |  |

**Options:**

| Option | Short | Type | Default | Description |
|--------|-------|------|---------|-------------|
| `--limit` | `-n` | integer | `10` | Number of results per query |
| `--candidate-limit` | `-C` | integer | `20` | Reranker candidate pool size |
| `--collection` | `-c` | text[] | — | Collection to search |
| `--all` | `—` | flag | `false` | Search all collections |
| `--model-type` | `—` | choice | — | Embedding model type override |
| `--json` | `—` | flag | `false` | Output as JSON |

### `cleanup`

Clean up the index (remove orphaned entries).

```bash
docsift cleanup [OPTIONS]
```

**Options:**

| Option | Short | Type | Default | Description |
|--------|-------|------|---------|-------------|
| `--yes` | `—` | flag | `false` | Confirm the action without prompting. |

### `ls`

List indexed documents as a virtual file tree.

```bash
docsift ls [OPTIONS]
```

**Arguments:**

| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `collection` | text | No |  |
| `subpath` | text | No |  |

### `pull`

Download a GGUF model file.

```bash
docsift pull [OPTIONS]
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
docsift status [OPTIONS]
```

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

## Common Workflows

**Setting up a new collection:**
```bash
# Add a collection
docsift collection add ~/Documents/notes --name my-notes --description "Personal notes"

# Update index
docsift index update --collection my-notes

# Search
docsift search query "python tips"
```

**Managing collection visibility:**
```bash
# Exclude from default searches
docsift collection exclude my-notes

# Include again
docsift collection include my-notes

# Set pre-update command
docsift collection update-cmd my-notes --cmd "git pull"
```

**Adding context:**
```bash
# Add global context
docsift context add global global "I am a software engineer."

# Add collection context
docsift context add collection my-notes "These are my programming notes."

# List contexts
docsift context list

# Prune orphaned contexts
docsift context prune
```

**Hybrid search with options:**
```bash
docsift search query "python decorators" --explain --candidate-limit 30 --limit 10
```
