# Configuration

SIF can be configured through environment variables or a `.env` file. This guide covers all available configuration options.

## Configuration Methods

### Environment Variables

Set configuration directly in your shell:

```bash
export SIF_DB_PATH=/custom/path/sif.db
export SIF_LOG_LEVEL=DEBUG
```

### .env File

Create a `.env` file in your working directory or home directory:

```bash
# ~/.env or ./.env
SIF_DB_PATH=~/.local/share/sif/sif.db
SIF_MODEL_NAME=Qwen/Qwen3-Embedding-0.6B
SIF_LOG_LEVEL=INFO
```

### Configuration Precedence

1. Environment variables (highest priority)
2. `.env` file in current directory
3. `.env` file in home directory
4. Default values (lowest priority)

## Configuration Options

### Application Settings

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `SIF_APP_NAME` | str | `sif` | Application name |
| `SIF_DEBUG` | bool | `False` | Debug mode |
| `SIF_LOG_LEVEL` | str | `INFO` | Logging level (validated by `validate_log_level`) |

### Database Settings

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `SIF_DB_PATH` | pathlib._local.Path | None | `~/.local/share/sif/sif.db (computed)` | Path to SQLite database file (validated by `expand_path`) |

### Embedding Model Settings

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `SIF_MODEL_NAME` | str | `Qwen/Qwen3-Embedding-0.6B` | Embedding model name |
| `SIF_MODEL_PATH` | pathlib._local.Path | None | `None` | Path to embedding model file |
| `SIF_EMBEDDING_DIM` | int | `1024` | Embedding dimension |
| `SIF_MAX_TOKENS` | int | `512` | Maximum tokens per input |
| `SIF_BATCH_SIZE` | int | `32` | Batch size for inference |
| `SIF_MODEL_TYPE` | str | `sentence_transformers` | Embedding model type (gguf, sentence_transformers, openai, huggingface) (validated by `validate_model_type`) |
| `SIF_N_GPU_LAYERS` | int | `0` | Number of GPU layers for GGUF models |

### API Settings

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `SIF_API_KEY` | str | None | `None` | API key for remote embedding models |
| `SIF_API_BASE` | str | None | `None` | Base URL for remote embedding API (validated by `validate_api_base`) |

### Reranker Settings

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `SIF_RERANKER_MODEL_NAME` | str | `Qwen/Qwen3-Reranker-0.6B` | Reranker model name |
| `SIF_RERANKER_MODEL_PATH` | pathlib._local.Path | None | `None` | Path to local reranker model file |
| `SIF_RERANKER_MODEL_TYPE` | str | `transformers` | Reranker model type (gguf, sentence_transformers, transformers) |
| `SIF_RERANKER_BATCH_SIZE` | int | `32` | Batch size for reranker inference |

### Chunking Settings

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `SIF_CHUNK_SIZE` | int | `512` | Default chunk size in tokens |
| `SIF_CHUNK_OVERLAP` | int | `128` | Default chunk overlap in tokens |

### Search Settings

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `SIF_DEFAULT_SEARCH_TYPE` | str | `hybrid` | Default search type (bm25, vector, hybrid) |
| `SIF_DEFAULT_LIMIT` | int | `10` | Default search result limit |

### MCP Server Settings

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `SIF_MCP_HOST` | str | `127.0.0.1` | MCP HTTP server host |
| `SIF_MCP_PORT` | int | `8080` | MCP HTTP server port |
| `SIF_MCP_TRANSPORT` | str | `stdio` | MCP transport type (stdio, http) |

### Cache Settings

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `SIF_CACHE_DIR` | pathlib._local.Path | None | `~/.cache/sif (computed)` | Cache directory path |
| `SIF_CACHE_EMBEDDINGS` | bool | `True` | Whether to cache embeddings |

## Validation Rules

SIF validates configuration on startup. Invalid values will raise errors:

| Field | Rule | Error Example |
|-------|------|---------------|
| `model_type` | Must be one of: `sentence_transformers`, `gguf`, `openai`, `modelscope`, `huggingface` | `Invalid model_type: xyz` |
| `api_base` | Must start with `http://` or `https://` | `api_base must be an HTTP or HTTPS URL` |
| `log_level` | Must be one of: `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL` | `Invalid log level: TRACE` |
| `chunk_size` | Minimum 100 | `ensure this value is greater than or equal to 100` |
| `chunk_overlap` | Minimum 0 | `ensure this value is greater than or equal to 0` |
| `default_limit` | 1 to 100 | `ensure this value is less than or equal to 100` |
| `mcp_port` | 1 to 65535 | `ensure this value is less than or equal to 65535` |

## Complete .env Example

```bash
# Database
SIF_DB_PATH=~/.local/share/sif/sif.db

# Embedding Model
SIF_MODEL_NAME=Qwen/Qwen3-Embedding-0.6B
SIF_EMBEDDING_DIM=1024
SIF_MODEL_TYPE=sentence_transformers
SIF_BATCH_SIZE=32

# Reranker
SIF_RERANKER_MODEL_NAME=Qwen/Qwen3-Reranker-0.6B
SIF_RERANKER_MODEL_TYPE=transformers
SIF_RERANKER_BATCH_SIZE=32

# API (for OpenAI-compatible backends)
# SIF_API_KEY=your-api-key
# SIF_API_BASE=https://api.openai.com/v1

# Chunking
SIF_CHUNK_SIZE=512
SIF_CHUNK_OVERLAP=128

# Search
SIF_DEFAULT_SEARCH_TYPE=hybrid
SIF_DEFAULT_LIMIT=10

# MCP Server
SIF_MCP_HOST=127.0.0.1
SIF_MCP_PORT=8080
SIF_MCP_TRANSPORT=stdio

# Logging
SIF_LOG_LEVEL=INFO

# Cache
SIF_CACHE_EMBEDDINGS=true
```

## Configuration Validation

SIF validates configuration on startup. Invalid configurations will produce errors:

```bash
$ export SIF_MODEL_TYPE=invalid
sif collection list
Error: Invalid model_type: invalid. Must be one of ['gguf', 'huggingface', 'modelscope', 'openai', 'sentence_transformers']
```

## Viewing Current Configuration

To see your current configuration:

```bash
# View effective configuration
sif status

# View with verbose output
sif status --verbose
```

## Best Practices

1. **Use .env files**: Keep configuration in version-controlled `.env.example` files
2. **Separate environments**: Use different databases for dev/staging/production
3. **Monitor logs**: Set appropriate log levels for your environment
4. **Tune chunk size**: Adjust based on your document characteristics
5. **Cache embeddings**: Enable `SIF_CACHE_EMBEDDINGS` for repeated indexing

## Troubleshooting Configuration

### Configuration Not Loading

Check if the `.env` file is being read:

```bash
# Check file location
ls -la .env ~/.env

# Verify file permissions
chmod 644 .env

# Test with explicit path
export SIF_ENV_FILE=/path/to/.env
```

### Environment Variables Not Applied

```bash
# Check if variable is set
echo $SIF_LOG_LEVEL

# Check in Python
python -c "import os; print(os.getenv('SIF_LOG_LEVEL'))"
```

## Related Documentation

- [CLI Reference](cli-reference.md) - Command-line options
- [Architecture](architecture.md) - System architecture
- [Development Guide](development.md) - Development configuration
