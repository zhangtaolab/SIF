# CLI Reference

Complete reference for all DocSift CLI commands.

## Global Options

These options can be used with any command:

| Option | Description |
|--------|-------------|
| `--version` | Show version and exit |
| `--index PATH` | Path to custom index database |
| `-v, --verbose` | Enable verbose output |
| `-q, --quiet` | Suppress non-error output |
| `--format FORMAT` | Output format: table, json, csv, md, xml, files |
| `--help` | Show help message |

## Command Overview

```
docsift
├── collection    Manage document collections
├── context       Manage search context
├── search        Search indexed documents
├── vsearch       Vector search
├── query         Query with natural language
├── update        Update index
├── embed         Generate embeddings
├── status        Show index status
├── cleanup       Clean up index
├── get           Get document by ID
├── multi-get     Get multiple documents
├── mcp           MCP server commands
└── ls            List documents
```

## Collection Commands

### `docsift collection list`

List all collections.

```bash
docsift collection list [OPTIONS]
```

**Options:**
| Option | Description |
|--------|-------------|
| `--format FORMAT` | Output format: table, json, plain |

**Example:**
```bash
# List all collections
docsift collection list

# Output as JSON
docsift collection list --format json
```

**Output:**
```
┌─────────────┬───────────┬─────────────────────┐
│ Name        │ Documents │ Paths               │
├─────────────┼───────────┼─────────────────────┤
│ my-notes    │ 42        │ ~/Documents/notes   │
│ work-docs   │ 156       │ ~/Work/docs         │
└─────────────┴───────────┴─────────────────────┘
```

### `docsift collection create`

Create a new collection.

```bash
docsift collection create NAME [OPTIONS]
```

**Arguments:**
| Argument | Description |
|----------|-------------|
| `NAME` | Unique name for the collection |

**Options:**
| Option | Description |
|--------|-------------|
| `-d, --description TEXT` | Collection description |
| `-p, --path PATH` | Path to include (can be used multiple times) |

**Example:**
```bash
# Create simple collection
docsift collection create my-notes

# Create with description and paths
docsift collection create work-docs \
  --description "Work documentation" \
  --path ~/Work/docs \
  --path ~/Work/projects
```

### `docsift collection delete`

Delete a collection.

```bash
docsift collection delete NAME [OPTIONS]
```

**Arguments:**
| Argument | Description |
|----------|-------------|
| `NAME` | Collection name to delete |

**Options:**
| Option | Description |
|--------|-------------|
| `-f, --force` | Force deletion without confirmation |

**Example:**
```bash
# Delete with confirmation
docsift collection delete old-collection

# Force delete
docsift collection delete old-collection --force
```

### `docsift collection rename`

Rename a collection.

```bash
docsift collection rename OLD_NAME NEW_NAME
```

**Arguments:**
| Argument | Description |
|----------|-------------|
| `OLD_NAME` | Current collection name |
| `NEW_NAME` | New collection name |

**Example:**
```bash
docsift collection rename my-notes personal-notes
```

### `docsift collection add-path`

Add a path to a collection.

```bash
docsift collection add-path NAME PATH
```

**Arguments:**
| Argument | Description |
|----------|-------------|
| `NAME` | Collection name |
| `PATH` | Directory path to add |

**Example:**
```bash
docsift collection add-path my-notes ~/Documents/more-notes
```

### `docsift collection remove-path`

Remove a path from a collection.

```bash
docsift collection remove-path NAME PATH
```

**Arguments:**
| Argument | Description |
|----------|-------------|
| `NAME` | Collection name |
| `PATH` | Directory path to remove |

**Example:**
```bash
docsift collection remove-path my-notes ~/Documents/old-notes
```

### `docsift collection show`

Show collection details.

```bash
docsift collection show NAME
```

**Arguments:**
| Argument | Description |
|----------|-------------|
| `NAME` | Collection name |

**Example:**
```bash
docsift collection show my-notes
```

**Output:**
```
Collection: my-notes
Description: Personal notes and documents
Paths: ~/Documents/notes
Documents: 42
Chunks: 156
Created: 2024-01-15 10:30:00
Last Indexed: 2024-01-20 14:22:00
```

## Context Commands

### `docsift context add`

Add context to improve search relevance.

```bash
docsift context add [OPTIONS] TEXT
```

**Arguments:**
| Argument | Description |
|----------|-------------|
| `TEXT` | Context text to add |

**Options:**
| Option | Description |
|--------|-------------|
| `--collection NAME` | Add to specific collection |
| `--global` | Add as global context |
| `--path PATH` | Add to specific path |
| `--document ID` | Add to specific document |

**Example:**
```bash
# Add global context
docsift context add --global "I am a software engineer interested in Python."

# Add collection context
docsift context add --collection my-notes "These are my personal programming notes."
```

### `docsift context list`

List all context entries.

```bash
docsift context list [OPTIONS]
```

**Options:**
| Option | Description |
|--------|-------------|
| `--collection NAME` | Filter by collection |
| `--format FORMAT` | Output format |

**Example:**
```bash
docsift context list
```

### `docsift context remove`

Remove context.

```bash
docsift context remove [OPTIONS]
```

**Options:**
| Option | Description |
|--------|-------------|
| `--collection NAME` | Remove collection context |
| `--global` | Remove global context |
| `--all` | Remove all context |

**Example:**
```bash
# Remove global context
docsift context remove --global

# Remove collection context
docsift context remove --collection my-notes
```

## Search Commands

### `docsift search`

Search indexed documents.

```bash
docsift search QUERY [OPTIONS]
```

**Arguments:**
| Argument | Description |
|----------|-------------|
| `QUERY` | Search query string |

**Options:**
| Option | Description |
|--------|-------------|
| `-c, --collection NAME` | Search in specific collection |
| `-t, --type TYPE` | Search type: bm25, vector, hybrid |
| `-l, --limit N` | Maximum results (default: 10) |
| `-o, --offset N` | Result offset for pagination |
| `--threshold FLOAT` | Minimum score threshold |
| `--expand` | Enable query expansion |
| `--rerank` | Enable result reranking |
| `--no-chunks` | Don't include matched chunks |
| `--no-metadata` | Don't include metadata |
| `--no-highlight` | Don't highlight matches |

**Example:**
```bash
# Basic search
docsift search "python decorators"

# Search in specific collection
docsift search "python decorators" --collection my-notes

# Hybrid search with more results
docsift search "machine learning" --type hybrid --limit 20

# Vector search with reranking
docsift search "neural networks" --type vector --rerank

# Search with query expansion
docsift search "AI" --expand --limit 15
```

**Output:**
```
Search Results: "python decorators"
Type: hybrid | Time: 45ms | Total: 23

1. [0.89] ~/notes/python/decorators.md
   Python decorators are a powerful feature that allow you to...
   
2. [0.85] ~/notes/python/advanced.md
   Understanding decorators requires knowledge of closures...
```

### `docsift vsearch`

Vector search (semantic similarity).

```bash
docsift vsearch QUERY [OPTIONS]
```

**Options:**
| Option | Description |
|--------|-------------|
| `-c, --collection NAME` | Search in specific collection |
| `-l, --limit N` | Maximum results |
| `--threshold FLOAT` | Minimum similarity threshold |

**Example:**
```bash
docsift vsearch "functions that wrap other functions" --limit 5
```

### `docsift query`

Natural language query with context.

```bash
docsift query TEXT [OPTIONS]
```

**Options:**
| Option | Description |
|--------|-------------|
| `-c, --collection NAME` | Search in specific collection |
| `-l, --limit N` | Maximum results |

**Example:**
```bash
docsift query "What are decorators and how do I use them?"
```

### `docsift search similar`

Find similar documents.

```bash
docsift search similar PATH [OPTIONS]
```

**Arguments:**
| Argument | Description |
|----------|-------------|
| `PATH` | Path to document |

**Options:**
| Option | Description |
|--------|-------------|
| `-l, --limit N` | Maximum results |
| `-c, --collection NAME` | Search in specific collection |

**Example:**
```bash
docsift search similar ~/notes/python/decorators.md --limit 5
```

## Index Commands

### `docsift update`

Update the index for a collection.

```bash
docsift update [COLLECTION] [OPTIONS]
```

**Arguments:**
| Argument | Description |
|----------|-------------|
| `COLLECTION` | Collection name (optional, updates all if omitted) |

**Options:**
| Option | Description |
|--------|-------------|
| `--force` | Force full reindex |
| `--dry-run` | Show what would be indexed |

**Example:**
```bash
# Update all collections
docsift update

# Update specific collection
docsift update my-notes

# Force reindex
docsift update my-notes --force
```

### `docsift embed`

Generate embeddings for documents.

```bash
docsift embed [COLLECTION] [OPTIONS]
```

**Arguments:**
| Argument | Description |
|----------|-------------|
| `COLLECTION` | Collection name |

**Options:**
| Option | Description |
|--------|-------------|
| `--force` | Regenerate all embeddings |
| `--batch-size N` | Batch size for embedding generation |

**Example:**
```bash
# Generate embeddings for collection
docsift embed my-notes

# Force regenerate
docsift embed my-notes --force
```

### `docsift status`

Show index status.

```bash
docsift status [COLLECTION]
```

**Arguments:**
| Argument | Description |
|----------|-------------|
| `COLLECTION` | Collection name (optional) |

**Example:**
```bash
# Show overall status
docsift status

# Show collection status
docsift status my-notes
```

**Output:**
```
Index Status
============

Collections: 3
Total Documents: 523
Total Chunks: 2,456
Total Embeddings: 2,456

Collection: my-notes
  Documents: 42
  Chunks: 156
  Last Indexed: 2024-01-20 14:22:00
  Status: ✓ Up to date
```

### `docsift cleanup`

Clean up the index.

```bash
docsift cleanup [OPTIONS]
```

**Options:**
| Option | Description |
|--------|-------------|
| `--orphaned` | Remove orphaned documents |
| `--expired` | Remove expired entries |
| `--vacuum` | Vacuum database |
| `--force` | Skip confirmation |

**Example:**
```bash
# Clean up orphaned documents
docsift cleanup --orphaned

# Full cleanup
docsift cleanup --orphaned --expired --vacuum
```

## Document Commands

### `docsift get`

Get a document by ID.

```bash
docsift get DOCUMENT_ID [OPTIONS]
```

**Arguments:**
| Argument | Description |
|----------|-------------|
| `DOCUMENT_ID` | Document ID |

**Options:**
| Option | Description |
|--------|-------------|
| `--format FORMAT` | Output format |

**Example:**
```bash
docsift get doc_abc123
```

### `docsift multi-get`

Get multiple documents by ID.

```bash
docsift multi-get DOCUMENT_IDS... [OPTIONS]
```

**Arguments:**
| Argument | Description |
|----------|-------------|
| `DOCUMENT_IDS` | One or more document IDs |

**Example:**
```bash
docsift multi-get doc_abc123 doc_def456 doc_ghi789
```

### `docsift ls`

List documents in a collection.

```bash
docsift ls COLLECTION [SUBPATH] [OPTIONS]
```

**Arguments:**
| Argument | Description |
|----------|-------------|
| `COLLECTION` | Collection name |
| `SUBPATH` | Optional subdirectory |

**Options:**
| Option | Description |
|--------|-------------|
| `-r, --recursive` | List recursively |
| `--format FORMAT` | Output format |

**Example:**
```bash
# List all documents
docsift ls my-notes

# List subdirectory
docsift ls my-notes python/

# Recursive list
docsift ls my-notes --recursive
```

## MCP Commands

### `docsift mcp start`

Start the MCP server.

```bash
docsift mcp start [OPTIONS]
```

**Options:**
| Option | Description |
|--------|-------------|
| `--transport TYPE` | Transport type: stdio, http |
| `--host HOST` | HTTP server host |
| `--port PORT` | HTTP server port |

**Example:**
```bash
# Start with stdio transport (default)
docsift mcp start

# Start with HTTP transport
docsift mcp start --transport http --port 8080
```

### `docsift mcp config`

Show MCP configuration.

```bash
docsift mcp config
```

**Example:**
```bash
docsift mcp config
```

**Output:**
```json
{
  "transport": "stdio",
  "tools": [
    "search",
    "get_document",
    "list_collections"
  ]
}
```

## Output Formats

### Table (default)

Human-readable table format.

### JSON

Machine-readable JSON format.

```bash
docsift collection list --format json
```

Output:
```json
{
  "collections": [
    {
      "name": "my-notes",
      "document_count": 42,
      "paths": ["~/Documents/notes"]
    }
  ]
}
```

### CSV

Comma-separated values.

```bash
docsift collection list --format csv
```

### Markdown

Markdown table format.

```bash
docsift collection list --format md
```

### XML

XML format.

```bash
docsift collection list --format xml
```

### Files

Plain file paths, one per line.

```bash
docsift search "python" --format files
```

## Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | General error |
| 2 | Invalid arguments |
| 3 | Collection not found |
| 4 | Document not found |
| 5 | Index error |
| 6 | Configuration error |

## Environment Variables

See [Configuration](configuration.md) for all environment variables.

## Examples

### Common Workflows

**Setting up a new collection:**
```bash
# Create collection
docsift collection create my-notes --description "Personal notes"

# Add paths
docsift collection add-path my-notes ~/Documents/notes
docsift collection add-path my-notes ~/Documents/ideas

# Add context
docsift context add --collection my-notes "These are my personal notes about programming."

# Index documents
docsift update my-notes

# Search
docsift search "python tips" --collection my-notes
```

**Daily usage:**
```bash
# Quick search
docsift search "meeting notes"

# Search with more results
docsift search "project ideas" --limit 20

# Check status
docsift status

# Update index
docsift update
```

**Batch operations:**
```bash
# Export search results
docsift search "python" --format json > results.json

# Get multiple documents
docsift multi-get $(docsift search "important" --format files)
```
