# Installation Guide

## System Requirements

- **Python**: 3.9 or higher
- **Operating System**: Linux, macOS, or Windows
- **Memory**: Minimum 4GB RAM (8GB+ recommended for large collections)
- **Disk Space**: Varies based on document collection size

## Installation Methods

### Method 1: Install from PyPI (Recommended)

The easiest way to install SIF is from PyPI:

```bash
pip install sif
```

For full functionality including embeddings:

```bash
pip install "sif[all]"
```

### Method 2: Install from Source

For development or to get the latest features:

```bash
# Clone the repository
git clone https://github.com/sif/sif.git
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
pipx install sif
```

## Optional Dependencies

SIF has several optional dependency groups:

### Embedding Support

For vector search functionality:

```bash
pip install "sif[embed]"
```

This installs:
- `sentence-transformers>=2.2.0`
- `numpy>=1.24.0`

### Development Dependencies

For contributing to SIF:

```bash
pip install "sif[dev]"
```

This installs:
- `pytest>=7.0.0`
- `pytest-cov>=4.0.0`
- `black>=23.0.0`
- `ruff>=0.1.0`
- `mypy>=1.0.0`

### All Dependencies

To install everything:

```bash
pip install "sif[all]"
```

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
pip3 install sif
```

### Windows

Using PowerShell:

```powershell
# Install Python from python.org or Microsoft Store
# Then install SIF
pip install sif
```

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
SIF version 0.1.0

Usage: sif [OPTIONS] COMMAND [ARGS]...

  SIF - Document indexing and search tool.

Options:
  --version         Show version and exit.
  --index PATH      Path to the index database file.
  -v, --verbose     Enable verbose output.
  -q, --quiet       Suppress non-error output.
  --format FORMAT   Output format.
  --help            Show this message and exit.

Commands:
  collection  Manage document collections.
  context     Manage search context.
  search      Search indexed documents.
  ...
```

## Troubleshooting

### Common Issues

#### ImportError: No module named 'sif'

**Cause**: SIF is not installed or not in PATH

**Solution**:
```bash
# Reinstall
pip install --force-reinstall sif

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
python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2')"

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

1. Check the [GitHub Issues](https://github.com/sif/sif/issues)
2. Run with verbose mode: `sif -v <command>`
3. Check logs: `~/.local/share/sif/logs/sif.log`

## Uninstallation

To remove SIF:

```bash
pip uninstall sif
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
