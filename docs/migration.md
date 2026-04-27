# Migration Guide: DocSift to SIF

This guide documents all breaking changes when migrating from DocSift to SIF.

## Breaking Changes

### CLI Command

- **Old**: `docsift <command>`
- **New**: `sif <command>`
- **Action**: Update all scripts, aliases, and documentation

### Environment Variables

All environment variables changed prefix from `DOCSIFT_` to `SIF_`:

| Old Variable | New Variable |
|--------------|--------------|
| `DOCSIFT_DB_PATH` | `SIF_DB_PATH` |
| `DOCSIFT_MODEL_NAME` | `SIF_MODEL_NAME` |
| `DOCSIFT_MODEL_PATH` | `SIF_MODEL_PATH` |
| `DOCSIFT_EMBEDDING_DIM` | `SIF_EMBEDDING_DIM` |
| `DOCSIFT_MAX_TOKENS` | `SIF_MAX_TOKENS` |
| `DOCSIFT_BATCH_SIZE` | `SIF_BATCH_SIZE` |
| `DOCSIFT_MODEL_TYPE` | `SIF_MODEL_TYPE` |
| `DOCSIFT_N_GPU_LAYERS` | `SIF_N_GPU_LAYERS` |
| `DOCSIFT_API_KEY` | `SIF_API_KEY` |
| `DOCSIFT_API_BASE` | `SIF_API_BASE` |
| `DOCSIFT_RERANKER_MODEL_NAME` | `SIF_RERANKER_MODEL_NAME` |
| `DOCSIFT_RERANKER_MODEL_PATH` | `SIF_RERANKER_MODEL_PATH` |
| `DOCSIFT_RERANKER_MODEL_TYPE` | `SIF_RERANKER_MODEL_TYPE` |
| `DOCSIFT_RERANKER_BATCH_SIZE` | `SIF_RERANKER_BATCH_SIZE` |
| `DOCSIFT_CHUNK_SIZE` | `SIF_CHUNK_SIZE` |
| `DOCSIFT_CHUNK_OVERLAP` | `SIF_CHUNK_OVERLAP` |
| `DOCSIFT_DEFAULT_SEARCH_TYPE` | `SIF_DEFAULT_SEARCH_TYPE` |
| `DOCSIFT_DEFAULT_LIMIT` | `SIF_DEFAULT_LIMIT` |
| `DOCSIFT_MCP_HOST` | `SIF_MCP_HOST` |
| `DOCSIFT_MCP_PORT` | `SIF_MCP_PORT` |
| `DOCSIFT_MCP_TRANSPORT` | `SIF_MCP_TRANSPORT` |
| `DOCSIFT_CACHE_DIR` | `SIF_CACHE_DIR` |
| `DOCSIFT_CACHE_EMBEDDINGS` | `SIF_CACHE_EMBEDDINGS` |
| `DOCSIFT_LOG_LEVEL` | `SIF_LOG_LEVEL` |
| `DOCSIFT_DEBUG` | `SIF_DEBUG` |
| `DOCSIFT_APP_NAME` | `SIF_APP_NAME` |
| `DOCSIFT_DEVICE` | `SIF_DEVICE` |

### Data Paths

- **Old**: `~/.docsift/`
- **New**: `~/.local/share/sif/`
- **Database**: Must re-run `sif index` to rebuild (no automatic DB migration)
- **Model cache**: Auto-migrates on first `sif` run if old directory exists

### Python Package

- **Old**: `pip install docsift`
- **New**: `pip install sif`
- **Imports**: `from docsift...` -> `from sif...`

### GitHub Repository

- **Old**: `https://github.com/docsift/docsift`
- **New**: `https://github.com/zhangtaolab/sif`

### MCP Server Name

- **Old**: `docsift` in `mcpServers` configuration
- **New**: `sif` in `mcpServers` configuration

## Migration Steps

1. **Uninstall old package**:
   ```bash
   pip uninstall docsift
   ```

2. **Install new package**:
   ```bash
   pip install sif
   ```

3. **Update environment variables** in your shell profile:
   ```bash
   # Replace DOCSIFT_ with SIF_ in ~/.bashrc, ~/.zshrc, etc.
   export SIF_DB_PATH=~/.local/share/sif/sif.db
   export SIF_MODEL_NAME=Qwen/Qwen3-Embedding-0.6B
   ```

4. **Rebuild your index**:
   ```bash
   sif index
   ```

5. **Update any scripts or aliases** using `docsift`:
   ```bash
   # Update shell aliases
   alias ds='sif'
   alias ds-search='sif search query'
   ```

6. **Update MCP configuration** (Claude Desktop, etc.):
   ```json
   {
     "mcpServers": {
       "sif": {
         "command": "sif",
         "args": ["mcp", "stdio"]
       }
     }
   }
   ```

## No Backward Compatibility

SIF does **not** provide backward compatibility aliases or dual environment variable support. All references must be updated to use the new `sif` command and `SIF_` prefix.

## Post-Migration Verification

Verify your migration is complete:

```bash
# Check CLI is accessible
sif --version

# Check configuration
sif status

# Test search
sif search query "test query"
```

## Getting Help

- [GitHub Issues](https://github.com/zhangtaolab/sif/issues)
- [GitHub Discussions](https://github.com/zhangtaolab/sif/discussions)
