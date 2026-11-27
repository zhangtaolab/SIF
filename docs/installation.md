# Installation Guide

## Prerequisites

- **Python**: 3.10 or newer
- **uv**: 0.9.19 or newer for the recommended `uv tool` install path (`--torch-backend` applies to `uv tool` commands from that release)
- **Operating System**: Linux, macOS, or Windows (Windows is degradation-only in v1.2; see [Windows](#windows))
- **Memory**: Minimum 4GB RAM (8GB+ recommended for large collections)
- **Disk Space**: Varies based on document collection size; the default embedding model is about 1.2 GB

SIF is distributed on PyPI as `docsif`; the installed command is `sif`.

## Installation Methods

Install methods are listed below in the recommended order.

### Method 1: uv tool install (Recommended)

`uv tool install` keeps SIF in an isolated environment and puts the `sif`
command on PATH.

Install the embedding stack for hybrid and vector search with the backend that
matches the machine:

```bash
# Linux with an NVIDIA GPU (recommended): uv selects the CUDA build for the driver
uv tool install --torch-backend=auto 'docsif[embed]'

# Linux CPU-only: CPU wheels, no CUDA stack
uv tool install --torch-backend=cpu 'docsif[embed]'

# macOS: no backend flag; the macOS wheel includes MPS
uv tool install 'docsif[embed]'
```

`--torch-backend` is resolved by `uv tool install` and `uv pip` commands from
uv 0.9.19 onward, and the `UV_TORCH_BACKEND` environment variable is
equivalent. Without the flag, Linux resolves PyPI's CUDA-enabled `torch` wheel
and pulls the full CUDA stack; `auto` matches the wheel to the driver, and
`cpu` installs CPU-only wheels.

Do not pass `--torch-backend=cpu` on macOS: the macOS wheel already includes MPS, and the CPU backend has no matching macOS wheel for the current torch fleet.

The backend matrix is verified by hand on Linux (uv 0.13.8, torch 2.15.0) and
by uv target resolution for macOS arm64; it is not proven in CI.

Install the BM25-only base (keyword search, retrieval, status, metadata, get,
and the MCP server) when you do not need embeddings:

```bash
uv tool install docsif
```

To upgrade an existing tool install, or to reinstall it in place:

```bash
uv tool upgrade docsif
uv tool install --force 'docsif[embed]'
```

### Method 2: uvx one-off

Run SIF without installing it, for a single invocation:

```bash
uvx --from 'docsif[embed]' sif --help
```

`uvx` resolves the published package into a temporary environment each time;
use `uv tool install` for a persistent command.

### Method 3: pip

pip works but does not isolate SIF from your active environment. pip cannot
auto-detect your GPU, so pick the torch index URL that matches your driver
before installing SIF:

```bash
# Linux CPU-only
pip install torch --index-url https://download.pytorch.org/whl/cpu
pip install "docsif[embed]"

# Linux with an NVIDIA GPU (CUDA 13.2 wheels; match the tag to your driver)
pip install torch --index-url https://download.pytorch.org/whl/cu132
pip install "docsif[embed]"

# macOS: no torch pre-install; the macOS wheel includes MPS
pip install "docsif[embed]"
```

Install the base or every backend:

```bash
# BM25-only base install
pip install docsif

# Every backend, including llama-cpp-python (GGUF) and OpenAI-compatible APIs
pip install "docsif[all]"
```

### Method 4: Install from Source

For development or to get the latest features:

```bash
# Clone the repository
git clone https://github.com/zhangtaolab/sif.git
cd sif

# Create a virtual environment (recommended)
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install in development mode
pip install -e ".[dev]"
```

### Method 5: Using pipx (Isolated Environment)

For an isolated installation built on pip:

```bash
pipx install 'docsif[embed]'
```

## Optional Dependencies

SIF has several optional dependency groups. Each method above installs one of
them; pick the extra that matches the features you need.

| Extra | Installs | Enables |
|-------|----------|---------|
| `embed` | `sentence-transformers>=5.4.1`, `torch>=2.11`, `modelscope>=1.36.0`, `numpy>=1.24.0` | Local embeddings for vector and hybrid search |
| `all` | the `embed` packages plus `llama-cpp-python>=0.3.35` and `openai>=2.0.0` | GGUF (llama.cpp) and OpenAI-compatible backends as well |
| `openai` | `openai>=2.0.0` | OpenAI-compatible API backends only |
| `dev` | `pytest>=7.0.0`, `pytest-cov>=4.0.0`, `pytest-asyncio>=0.23.0`, `ruff>=0.1.0`, `ty>=0.0.1` | Contributing to SIF |

### Embedding Support

For vector search functionality:

```bash
uv tool install 'docsif[embed]'
```

This installs `sentence-transformers>=5.4.1`, `torch>=2.11`, `modelscope>=1.36.0`,
and `numpy>=1.24.0`. torch 2.14 or newer is recommended for the widest backend
compatibility; 2.11 is the minimum supported floor (verified with the vendor cpu,
cu130, and xpu builds).

With the `embed` extra installed, the local embedding backends pick their
compute device automatically at model load — CUDA GPU where torch has it,
Intel XPU where the installed torch is an XPU-enabled build, Apple Metal
(MPS) on arm64 macOS, otherwise CPU. XPU auto-detection requires that
XPU-enabled torch build; the standard wheel does not provide it. No extra
setup or configuration is needed; see [Configuration](configuration.md) for
per-backend details.

### llama-cpp-python (GGUF) backend

GGUF models need `llama-cpp-python`, which ships in the `all` extra but not in
`embed`. Official prebuilt wheels are published per backend and per Python
version (3.10–3.12) at these indexes:

| Backend | Wheel index |
|---------|-------------|
| CPU | `https://abetlen.github.io/llama-cpp-python/whl/cpu` |
| CUDA 12.1 | `https://abetlen.github.io/llama-cpp-python/whl/cu121` |
| Metal (macOS) | `https://abetlen.github.io/llama-cpp-python/whl/metal` |

With uv, point both indexes at the resolver and prefer the best match across
them; otherwise the default first-index strategy can select PyPI's source
distribution:

```bash
# Official prebuilt CPU wheels for the all extra.
# Manually verified recipe, not CI-proven: confirm the wheel you receive is a
# binary (llama_cpp*.whl), not an sdist, before relying on it.
uv tool install \
  --index https://abetlen.github.io/llama-cpp-python/whl/cpu \
  --index-strategy unsafe-best-match \
  'docsif[all]'
```

This multi-index recipe requires human verification on your platform; treat it
as a documented path, not a CI-tested one.

When no wheel matches (for example on Python 3.13), build from source with the
CMake flags for your backend:

```bash
# CPU source build (no GPU flags)
pip install llama-cpp-python --no-binary llama-cpp-python

# Metal (macOS) source build
CMAKE_ARGS="-DGGML_METAL=on" pip install llama-cpp-python --no-binary llama-cpp-python

# CUDA source build
CMAKE_ARGS="-DGGML_CUDA=on" pip install llama-cpp-python --no-binary llama-cpp-python
```

### The `all` extra and the Python 3.12 safe path

Official llama-cpp-python wheels list Python 3.10–3.12. On Python 3.13 the
`all` extra falls back to a source build, which needs a compiler and CMake.
Install the `all` extra under Python 3.12 to stay on the prebuilt wheel path:

```bash
uv tool install --python 3.12 'docsif[all]'
```

## Degradation Matrix

SIF degrades honestly rather than silently returning weaker results:

| Situation | What still works | What degrades |
|-----------|------------------|---------------|
| Base install without the `embed` extra | BM25 keyword search (`sif search search <query>`), indexing, status, metadata, get, MCP BM25 tools | `sif index embed`, `sif search vsearch <query>`, and `sif search query <query>` need an embedding backend and stop with an install message |
| `embed` extra installed but `sqlite-vec` cannot load | BM25 keyword search (`sif search search <query>`) and BM25 indexing (`sif index update`), status, metadata, get | `sif index embed` and the CLI vector and hybrid search commands raise the vector-store error (`sqlite-vec extension is not available`); the MCP `hybrid_search` backend degrades to BM25-only with a one-time warning |
| `embed` extra without the GGUF or OpenAI extra | sentence-transformers and ModelScope backends | `model_type = gguf` and `model_type = openai` are unavailable until `all` (or `openai`) is installed |
| Windows daemon/service installs | Foreground `sif watch`, MCP stdio and HTTP, CLI search and indexing | Detached watch, `--install-service`, and POSIX index locking are refused or degrade with a clear message; Windows is degradation-only in v1.2 |

The MCP `hybrid_search` carve-out is deliberate: a missing `sqlite-vec`
extension degrades the MCP backend to BM25 with one warning, while the core
`HybridSearcher.search()` still fails fast for direct API callers.

## Client Configuration

The canonical client guide is [MCP Server](mcp-server.md); the snippets below
are minimal starting points.

### Claude Desktop (stdio)

Add the server to `claude_desktop_config.json` (`~/Library/Application
Support/Claude/claude_desktop_config.json` on macOS,
`%APPDATA%\Claude\claude_desktop_config.json` on Windows, or
`~/.config/Claude/claude_desktop_config.json` on Linux):

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

### Claude Code (HTTP)

Start the HTTP transport in one terminal:

```bash
sif mcp http --host 127.0.0.1 --port 8080
```

Then register the Streamable HTTP endpoint (`/mcp`) with Claude Code:

```bash
claude mcp add --transport http sif http://127.0.0.1:8080/mcp
```

### Claude Code plugin

The repository root is a Claude Code plugin and marketplace whose `.mcp.json`
starts the installed `sif` command. Install SIF first, then install the
plugin:

```text
/plugin install sif --marketplace zhangtaolab/SIF
```

See [MCP Server](mcp-server.md) for the plugin, the zero-install `uvx`
fallback, the daemon, and the MCP Registry listing.

## Platform-Specific Instructions

### Linux

Most Linux distributions work out of the box. For source builds and native
wheels, install the compiler toolchain:

```bash
# Ubuntu/Debian
sudo apt-get update
sudo apt-get install python3-dev build-essential

# Fedora
sudo dnf install python3-devel gcc

# Arch
sudo pacman -S python base-devel
```

For the embedding stack, `--torch-backend=auto` is the recommended Linux GPU
path (uv selects the CUDA build for the driver), and `--torch-backend=cpu` is
the CPU-only path; see
[Method 1](#method-1-uv-tool-install-recommended).

### macOS

Using Homebrew:

```bash
# Install Python if not already installed
brew install python@3.12

# Install SIF
uv tool install 'docsif[embed]'
```

Do not pass `--torch-backend=cpu` on macOS: the macOS wheel already includes MPS, and the CPU backend has no matching macOS wheel for the current torch fleet.

**Hardware acceleration**: the modelscope and sentence_transformers backends
auto-select CUDA, Intel XPU, Apple Metal (MPS), or CPU. On Apple Silicon Macs
they use the GPU via Metal (MPS); on an Intel XPU host they use XPU when the
installed torch is an XPU-enabled build (the standard wheel does not provide
it). GGUF (llama.cpp) models run on CPU only unless `SIF_N_GPU_LAYERS` is set
above 0, which enables llama.cpp Metal offload (distinct from MPS). See
[Configuration](configuration.md) for the full device-selection behavior.

### Windows

Using PowerShell:

```powershell
# Install Python from python.org or Microsoft Store, then uv, then SIF
uv tool install docsif
```

**Windows (degradation smoke)**: Windows is degradation-only in v1.2 — the CLI
works, but POSIX-only features (detached watch, service install, `fcntl` index
locking) refuse or degrade with clear messages instead of running. Before a
release, maintainers run `make windows-smoke` on a Windows host (hc remote
yoga) to prove the degradation is honest.

## Verifying Installation

After installation, verify SIF is working:

```bash
# Check version
sif --version

# Show help
sif --help
```

Expected output:
```
sif, version 1.2.5

Usage: sif [OPTIONS] COMMAND [ARGS]...

  SIF - Search / Index / Find - Local document search engine.

Options:
  --version         Show the version and exit.
  -i, --index PATH  Path to the index database
  -v, --verbose     Enable verbose output
  -q, --quiet       Suppress non-error output
  --help            Show this message and exit.

Commands:
  bench       Run benchmark evaluation against a fixture file.
  cleanup     Clean up the index (remove orphaned entries).
  collection  Manage document collections.
  context     Manage contextual descriptions for paths, collections, and...
  ...
```

Then check the model surface:

```bash
# Configured identity, cache state, backend availability (no download)
sif models status

# Download the configured embedder through the verified cache
sif models pull
```

## Troubleshooting

### Common Issues

#### `sif: command not found`

**Cause**: SIF is not installed, or the shim directory is not on PATH.

**Solution**:
```bash
# Reinstall the tool and confirm the shim directory
uv tool install --force 'docsif[embed]'
uv tool dir --bin

# Fall back to invoking the module
python -m sif.cli.main --help
```

#### SQLite FTS5 Not Available

**Cause**: SQLite was compiled without FTS5 support

**Solution**:
```bash
# Check SQLite version
python -c "import sqlite3; print(sqlite3.sqlite_version)"

# FTS5 requires SQLite 3.9.0+
# If using an older version, upgrade Python or install a newer SQLite
```

#### Embedding Model Download Fails

**Cause**: Network issues or model not found

**Solution**:
```bash
# Download through the verified canonical cache and inspect its state
sif models pull
sif models status --json

# Or specify a local model path
export SIF_MODEL_PATH=/path/to/local/model
```

#### Permission Denied

**Cause**: Insufficient permissions for database directory

**Solution**:
```bash
# The default database directory is resolved by Settings.get_db_path()
# (platformdirs user_data_dir), so it differs per platform.
# Linux (default: ~/.local/share/sif)
mkdir -p ~/.local/share/sif
chmod 755 ~/.local/share/sif

# macOS (default: ~/Library/Application Support/sif)
mkdir -p "$HOME/Library/Application Support/sif"
chmod 755 "$HOME/Library/Application Support/sif"

# Windows (PowerShell; default is under %LOCALAPPDATA%)
# New-Item -ItemType Directory -Force (Join-Path $env:LOCALAPPDATA 'sif')

# Or change database path
export SIF_DB_PATH=/path/with/write/permission/sif.db
```

### Getting Help

If you encounter issues not covered here:

1. Check the [GitHub Issues](https://github.com/zhangtaolab/sif/issues)
2. Run with verbose mode: `sif -v index update`
3. Logs are written to stderr by default; `sif watch --detach` redirects stdout/stderr to a log file in the platform log directory (default `watch.log`, e.g. `~/Library/Logs/sif/watch.log` on macOS). Installed watch services log there on macOS (launchd); on Linux the systemd unit logs to the journal (`journalctl --user -u <unit> -f`).

## Uninstallation

To remove SIF:

```bash
uv tool uninstall docsif
# or, for a pip install
pip uninstall docsif
```

To also remove data and configuration:

```bash
# Remove the database's platform data directory
# Linux (default: ~/.local/share/sif)
rm -rf ~/.local/share/sif
# macOS (default: ~/Library/Application Support/sif)
rm -rf "$HOME/Library/Application Support/sif"
# Windows (PowerShell; default is under %LOCALAPPDATA%)
# Remove-Item -Recurse -Force (Join-Path $env:LOCALAPPDATA 'sif')

# Remove configuration
rm -rf ~/.config/sif
```

Model files live in the SIF cache directory (`<cache>/models`); remove that
directory only if you do not plan to reinstall.

## Next Steps

After installation, see:
- [Quick Start Guide](quickstart.md) - Get started quickly
- [MCP Server](mcp-server.md) - Client configuration and the plugin
- [Data Models](models.md#model-management) - Model management and the canonical cache
- [Configuration](configuration.md) - Configure SIF
- [CLI Reference](cli-reference.md) - Learn the commands
