# Installation Guide

## System Requirements

- **Python**: 3.10 or higher
- **Operating System**: Linux, macOS, or Windows
- **Memory**: Minimum 4GB RAM (8GB+ recommended for large collections)
- **Disk Space**: Varies based on document collection size

## Installation Methods

### Method 1: Install from PyPI (Recommended)

The easiest way to install SIF is from PyPI:

```bash
pip install docsif
```

For full functionality including embeddings:

```bash
pip install "docsif[all]"
```

### Method 2: Install from Source

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

### Method 3: Using pipx (Isolated Environment)

For an isolated installation:

```bash
pipx install docsif
```

## Optional Dependencies

SIF has several optional dependency groups:

### Embedding Support

For vector search functionality:

```bash
pip install "docsif[embed]"
```

This installs:
- `sentence-transformers>=5.4.1`
- `torch`
- `modelscope>=1.36.0`
- `numpy>=1.24.0`

With this extra installed, the local embedding backends pick their compute device automatically at model load — CUDA GPU where torch has it, Apple Metal (MPS) on arm64 macOS, otherwise CPU. No extra setup or configuration is needed; see [Configuration](configuration.md) for per-backend details.

### Development Dependencies

For contributing to SIF:

```bash
pip install "docsif[dev]"
```

This installs:
- `pytest>=7.0.0`
- `pytest-cov>=4.0.0`
- `pytest-asyncio>=0.23.0`
- `ruff>=0.1.0`
- `ty>=0.0.1`

### All Dependencies

To install everything:

```bash
pip install "docsif[all]"
```

This installs every optional dependency group:
- `sentence-transformers>=5.4.1`
- `torch`
- `llama-cpp-python>=0.3.35`
- `modelscope>=1.36.0`
- `numpy>=1.24.0`
- `openai>=2.0.0`

## Platform-Specific Instructions

### Linux

Most Linux distributions work out of the box. For optimal performance:

```bash
# Ubuntu/Debian
sudo apt-get update
sudo apt-get install python3-dev build-essential

# Fedora
sudo dnf install python3-devel gcc

# Arch
sudo pacman -S python base-devel
```

### macOS

Using Homebrew:

```bash
# Install Python if not already installed
brew install python@3.11

# Install SIF
pip3 install docsif
```

**Hardware acceleration**: on Apple Silicon Macs the modelscope and sentence_transformers backends automatically use the GPU via Metal (MPS). GGUF (llama.cpp) models run on CPU only unless `SIF_N_GPU_LAYERS` is set above 0, which enables llama.cpp Metal offload (distinct from MPS). See [Configuration](configuration.md) for the full device-selection behavior.

### Windows

Using PowerShell:

```powershell
# Install Python from python.org or Microsoft Store
# Then install SIF
pip install docsif
```

**Windows (degradation smoke)**: Windows is degradation-only in v1.2 — the CLI works, but POSIX-only features (detached watch, service install, `fcntl` index locking) refuse or degrade with clear messages instead of running. Before a release, maintainers run `make windows-smoke` on a Windows host (hc remote yoga) to prove the degradation is honest.

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
sif, version 1.1.2

Usage: sif [OPTIONS] COMMAND [ARGS]...

  SIF - Search / Index / Find - Local document search engine.

Options:
  --version         Show the version and exit.
  -i, --index PATH  Path to the index database
  -v, --verbose     Enable verbose output
  -q, --quiet       Suppress non-error output
  --help            Show this message and exit.

Commands:
  collection  Manage document collections.
  context     Manage contextual descriptions for paths, collections, and global scope.
  search      Search commands.
  ...
```

## Troubleshooting

### Common Issues

#### ImportError: No module named 'sif'

**Cause**: SIF is not installed or not in PATH

**Solution**:
```bash
# Reinstall
pip install --force-reinstall docsif

# Check if pip is using the correct Python
which python
which pip
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
# Download model manually
python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('Qwen/Qwen3-Embedding-0.6B')"

# Or specify a local model path
export SIF_MODEL_PATH=/path/to/local/model
```

#### Permission Denied

**Cause**: Insufficient permissions for database directory

**Solution**:
```bash
# Create sif directory with proper permissions
mkdir -p ~/.local/share/sif
chmod 755 ~/.local/share/sif

# Or change database path
export SIF_DB_PATH=/path/with/write/permission/sif.db
```

### Getting Help

If you encounter issues not covered here:

1. Check the [GitHub Issues](https://github.com/zhangtaolab/sif/issues)
2. Run with verbose mode: `sif -v <command>`
3. Logs are written to stderr by default; `sif watch --detach` redirects stdout/stderr to a log file in the platform log directory (default `watch.log`, e.g. `~/Library/Logs/sif/watch.log` on macOS). Installed watch services log there on macOS (launchd); on Linux the systemd unit logs to the journal (`journalctl --user -u <unit> -f`).

## Uninstallation

To remove SIF:

```bash
pip uninstall docsif
```

To also remove data and configuration:

```bash
# Remove database
rm -rf ~/.local/share/sif

# Remove configuration
rm -rf ~/.config/sif
```

## Next Steps

After installation, see:
- [Quick Start Guide](../README.md#quick-start) - Get started quickly
- [Configuration](configuration.md) - Configure SIF
- [CLI Reference](cli-reference.md) - Learn the commands
