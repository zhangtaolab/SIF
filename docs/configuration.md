# Configuration

DocSift can be configured through environment variables or a `.env` file. This guide covers all available configuration options.

## Configuration Methods

### Environment Variables

Set configuration directly in your shell:

```bash
export DOCSIFT_DB_PATH=/custom/path/docsift.db
export DOCSIFT_LOG_LEVEL=DEBUG
```

### .env File

Create a `.env` file in your working directory or home directory:

```bash
# ~/.env or ./.env
DOCSIFT_DB_PATH=~/.local/share/docsift/docsift.db
DOCSIFT_MODEL_NAME=all-MiniLM-L6-v2
DOCSIFT_LOG_LEVEL=INFO
```

### Configuration Precedence

1. Environment variables (highest priority)
2. `.env` file in current directory
3. `.env` file in home directory
4. Default values (lowest priority)

## Configuration Options

### Database Settings

| Variable | Default | Description |
|----------|---------|-------------|
| `DOCSIFT_DB_PATH` | `~/.local/share/docsift/docsift.db` | Path to SQLite database file |

**Example:**
```bash
export DOCSIFT_DB_PATH=/data/docsift/production.db
```

### Embedding Model Settings

| Variable | Default | Description |
|----------|---------|-------------|
| `DOCSIFT_MODEL_NAME` | `all-MiniLM-L6-v2` | Name of the embedding model |
| `DOCSIFT_MODEL_PATH` | `None` | Path to local model file (GGUF format) |
| `DOCSIFT_EMBEDDING_DIM` | `384` | Embedding dimension |

**Example - Using HuggingFace model:**
```bash
export DOCSIFT_MODEL_NAME=sentence-transformers/all-MiniLM-L6-v2
```

**Example - Using local GGUF model:**
```bash
export DOCSIFT_MODEL_PATH=~/models/embedding-model.gguf
export DOCSIFT_EMBEDDING_DIM=768
```

### Chunking Settings

| Variable | Default | Description |
|----------|---------|-------------|
| `DOCSIFT_CHUNK_SIZE` | `512` | Maximum chunk size in tokens |
| `DOCSIFT_CHUNK_OVERLAP` | `128` | Overlap between chunks in tokens |

**Example:**
```bash
export DOCSIFT_CHUNK_SIZE=1024
export DOCSIFT_CHUNK_OVERLAP=256
```

### Search Settings

| Variable | Default | Description |
|----------|---------|-------------|
| `DOCSIFT_DEFAULT_SEARCH_TYPE` | `hybrid` | Default search type (bm25, vector, hybrid) |
| `DOCSIFT_DEFAULT_LIMIT` | `10` | Default number of results |
| `DOCSIFT_RRF_K` | `60` | RRF fusion parameter |

**Example:**
```bash
export DOCSIFT_DEFAULT_SEARCH_TYPE=vector
export DOCSIFT_DEFAULT_LIMIT=20
export DOCSIFT_RRF_K=40
```

### BM25 Settings

| Variable | Default | Description |
|----------|---------|-------------|
| `DOCSIFT_BM25_K1` | `1.5` | BM25 term frequency saturation parameter |
| `DOCSIFT_BM25_B` | `0.75` | BM25 length normalization parameter |

**Example:**
```bash
export DOCSIFT_BM25_K1=2.0
export DOCSIFT_BM25_B=0.5
```

### Logging Settings

| Variable | Default | Description |
|----------|---------|-------------|
| `DOCSIFT_LOG_LEVEL` | `INFO` | Logging level (DEBUG, INFO, WARNING, ERROR) |
| `DOCSIFT_LOG_FILE` | `~/.local/share/docsift/logs/docsift.log` | Log file path |

**Example:**
```bash
export DOCSIFT_LOG_LEVEL=DEBUG
export DOCSIFT_LOG_FILE=/var/log/docsift/app.log
```

### MCP Server Settings

| Variable | Default | Description |
|----------|---------|-------------|
| `DOCSIFT_MCP_HOST` | `127.0.0.1` | MCP HTTP server host |
| `DOCSIFT_MCP_PORT` | `8080` | MCP HTTP server port |
| `DOCSIFT_MCP_TRANSPORT` | `stdio` | Default transport (stdio, http) |

**Example:**
```bash
export DOCSIFT_MCP_HOST=0.0.0.0
export DOCSIFT_MCP_PORT=3000
export DOCSIFT_MCP_TRANSPORT=http
```

### Performance Settings

| Variable | Default | Description |
|----------|---------|-------------|
| `DOCSIFT_BATCH_SIZE` | `100` | Batch size for indexing operations |
| `DOCSIFT_MAX_WORKERS` | `4` | Maximum number of worker threads |
| `DOCSIFT_CACHE_SIZE` | `1000` | Embedding cache size |

**Example:**
```bash
export DOCSIFT_BATCH_SIZE=500
export DOCSIFT_MAX_WORKERS=8
export DOCSIFT_CACHE_SIZE=5000
```

## Complete Configuration Example

Here's a complete `.env` file example:

```bash
# Database
DOCSIFT_DB_PATH=~/.local/share/docsift/docsift.db

# Embedding Model
DOCSIFT_MODEL_NAME=all-MiniLM-L6-v2
DOCSIFT_EMBEDDING_DIM=384

# Chunking
DOCSIFT_CHUNK_SIZE=512
DOCSIFT_CHUNK_OVERLAP=128

# Search
DOCSIFT_DEFAULT_SEARCH_TYPE=hybrid
DOCSIFT_DEFAULT_LIMIT=10
DOCSIFT_RRF_K=60

# BM25
DOCSIFT_BM25_K1=1.5
DOCSIFT_BM25_B=0.75

# Logging
DOCSIFT_LOG_LEVEL=INFO

# MCP Server
DOCSIFT_MCP_HOST=127.0.0.1
DOCSIFT_MCP_PORT=8080

# Performance
DOCSIFT_BATCH_SIZE=100
DOCSIFT_MAX_WORKERS=4
DOCSIFT_CACHE_SIZE=1000
```

## Configuration Profiles

You can create different configuration profiles for different use cases:

### Development Profile (`~/.docsift/dev.env`)

```bash
DOCSIFT_DB_PATH=~/.local/share/docsift/dev.db
DOCSIFT_LOG_LEVEL=DEBUG
DOCSIFT_CHUNK_SIZE=256
```

### Production Profile (`~/.docsift/prod.env`)

```bash
DOCSIFT_DB_PATH=/data/docsift/production.db
DOCSIFT_LOG_LEVEL=WARNING
DOCSIFT_BATCH_SIZE=500
DOCSIFT_MAX_WORKERS=8
```

### Using Profiles

```bash
# Load development profile
source ~/.docsift/dev.env
docsift collection list

# Load production profile
source ~/.docsift/prod.env
docsift collection list
```

## Configuration Validation

DocSift validates configuration on startup. Invalid configurations will produce errors:

```bash
$ export DOCSIFT_CHUNK_SIZE=invalid
docsift collection list
Error: Invalid configuration: DOCSIFT_CHUNK_SIZE must be an integer
```

## Viewing Current Configuration

To see your current configuration:

```bash
# View effective configuration
docsift config show

# View with defaults
docsift config show --with-defaults
```

## Best Practices

1. **Use .env files**: Keep configuration in version-controlled `.env.example` files
2. **Separate environments**: Use different databases for dev/staging/production
3. **Monitor logs**: Set appropriate log levels for your environment
4. **Tune chunk size**: Adjust based on your document characteristics
5. **Cache embeddings**: Use appropriate cache sizes for your workload

## Troubleshooting Configuration

### Configuration Not Loading

Check if the `.env` file is being read:

```bash
# Check file location
ls -la .env ~/.env

# Verify file permissions
chmod 644 .env

# Test with explicit path
export DOCSIFT_ENV_FILE=/path/to/.env
```

### Environment Variables Not Applied

```bash
# Check if variable is set
echo $DOCSIFT_LOG_LEVEL

# Check in Python
python -c "import os; print(os.getenv('DOCSIFT_LOG_LEVEL'))"
```

## Related Documentation

- [CLI Reference](cli-reference.md) - Command-line options
- [Architecture](architecture.md) - System architecture
- [Development Guide](development.md) - Development configuration
