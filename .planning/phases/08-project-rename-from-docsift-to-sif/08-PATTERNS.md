# Phase 8: Project rename from DocSift to SIF - Pattern Map

**Mapped:** 2026-04-27
**Files analyzed:** 26 categories of new/modified files
**Analogs found:** 26 / 26 (all have direct analogs in the current codebase)

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `src/sif/` (package dir) | package | N/A | `src/docsift/` | exact |
| `src/sif/__init__.py` | module | N/A | `src/docsift/__init__.py` | exact |
| `src/sif/config/constants.py` | config | static | `src/docsift/config/constants.py` | exact |
| `src/sif/config/settings.py` | config | request-response | `src/docsift/config/settings.py` | exact |
| `src/sif/utils/logging.py` | utility | N/A | `src/docsift/utils/logging.py` | exact |
| `src/sif/cli/main.py` | controller | request-response | `src/docsift/cli/main.py` | exact |
| `src/sif/cli/config.py` | config | static | `src/docsift/cli/config.py` | exact |
| `src/sif/models/download.py` | service | CRUD | `src/docsift/models/download.py` | exact |
| `src/sif/cli/commands/*.py` | controller | request-response | `src/docsift/cli/commands/search.py` | exact |
| `src/sif/mcp/server.py` | service | request-response | `src/docsift/mcp/server.py` | exact |
| `src/sif/mcp_server/server.py` | service | request-response | `src/docsift/mcp_server/server.py` | exact |
| `src/sif/database/database.py` | service | CRUD | `src/docsift/database/database.py` | exact |
| `pyproject.toml` | config | static | `pyproject.toml` | exact |
| `mypy.ini` | config | static | `mypy.ini` | exact |
| `mkdocs.yml` | config | static | `mkdocs.yml` | exact |
| `Makefile` | config | static | `Makefile` | exact |
| `.github/workflows/docs.yml` | config | static | `.github/workflows/docs.yml` | exact |
| `tests/conftest.py` | test | N/A | `tests/conftest.py` | exact |
| `tests/unit/config/test_settings.py` | test | N/A | `tests/unit/config/test_settings.py` | exact |
| `tests/unit/cli/test_status.py` | test | N/A | `tests/unit/cli/test_status.py` | exact |
| `tests/test_docs.py` | test | N/A | `tests/test_docs.py` | exact |
| `tests/test_docsift_complete.py` | test | N/A | `tests/test_docsift_complete.py` | exact |
| `scripts/generate_cli_ref.py` | script | file-I/O | `scripts/generate_cli_ref.py` | exact |
| `scripts/generate_config_ref.py` | script | file-I/O | `scripts/generate_config_ref.py` | exact |
| `examples/quickstart.py` | example | N/A | `examples/quickstart.py` | exact |
| `.claude/skills/sif-search/SKILL.md` | skill | N/A | `.claude/skills/docsift-search/SKILL.md` | exact |
| `.claude/skills/sif-get/SKILL.md` | skill | N/A | `.claude/skills/docsift-get/SKILL.md` | exact |

## Pattern Assignments

### `src/sif/config/constants.py` (config, static)

**Analog:** `src/docsift/config/constants.py`

**Constants pattern** (lines 1-51):
```python
"""Constants for DocSift."""

# Application info
APP_NAME = "docsift"
APP_VERSION = "0.1.0"
APP_DESCRIPTION = "A local CLI search engine for indexing and searching markdown documents"

# Default paths
DEFAULT_DB_PATH = "~/.local/share/docsift/docsift.db"
DEFAULT_MODEL_PATH = "~/.local/share/docsift/models"
DEFAULT_CONFIG_PATH = "~/.config/docsift"
```

**Rename changes:**
- `APP_NAME = "docsift"` -> `APP_NAME = "sif"`
- `DEFAULT_DB_PATH = "~/.local/share/docsift/docsift.db"` -> `DEFAULT_DB_PATH = "~/.local/share/sif/sif.db"`
- `DEFAULT_MODEL_PATH = "~/.local/share/docsift/models"` -> `DEFAULT_MODEL_PATH = "~/.local/share/sif/models"`
- `DEFAULT_CONFIG_PATH = "~/.config/docsift"` -> `DEFAULT_CONFIG_PATH = "~/.config/sif"`

---

### `src/sif/config/settings.py` (config, request-response)

**Analog:** `src/docsift/config/settings.py`

**Imports pattern** (lines 1-11):
```python
"""Configuration settings for DocSift."""

from functools import lru_cache
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from docsift.config.constants import APP_NAME, DEFAULT_CHUNK_OVERLAP, DEFAULT_CHUNK_SIZE
```

**Env prefix pattern** (lines 19-24):
```python
    model_config = SettingsConfigDict(
        env_prefix="DOCSIFT_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )
```

**Database path pattern** (lines 188-197):
```python
    def get_db_path(self) -> Path:
        """Get the database path, creating default if not set."""
        if self.db_path:
            return self.db_path

        from platformdirs import user_data_dir

        data_dir = Path(user_data_dir(self.app_name))
        data_dir.mkdir(parents=True, exist_ok=True)
        return data_dir / "docsift.db"
```

**Rename changes:**
- Import: `from docsift.config.constants` -> `from sif.config.constants`
- `env_prefix="DOCSIFT_"` -> `env_prefix="SIF_"`
- Return value: `data_dir / "docsift.db"` -> `data_dir / "sif.db"`

---

### `src/sif/utils/logging.py` (utility, static)

**Analog:** `src/docsift/utils/logging.py`

**Root logger pattern** (lines 120-127):
```python
    # Configure root logger
    root_logger = logging.getLogger("docsift")
    root_logger.setLevel(getattr(logging, level.upper()))
    root_logger.handlers = []
    root_logger.addHandler(handler)

    # Don't propagate to parent
    root_logger.propagate = False
```

**Get logger pattern** (lines 134-143):
```python
def get_logger(name: str) -> logging.Logger:
    """Get a logger instance.

    Args:
        name: Logger name (typically __name__)

    Returns:
        Logger instance
    """
    return logging.getLogger(f"docsift.{name}")
```

**Rename changes:**
- `logging.getLogger("docsift")` -> `logging.getLogger("sif")`
- `f"docsift.{name}"` -> `f"sif.{name}"`

---

### `src/sif/cli/main.py` (controller, request-response)

**Analog:** `src/docsift/cli/main.py`

**Imports pattern** (lines 1-16):
```python
#!/usr/bin/env python3
"""DocSift CLI - Main entry point."""

from __future__ import annotations

from pathlib import Path

import click
from rich.console import Console
from rich.table import Table

from docsift import __version__
from docsift.config.settings import get_settings
from docsift.database.database import Database
from docsift.utils.logging import get_logger, setup_logging
```

**Default paths pattern** (lines 21-23):
```python
# Default paths
DEFAULT_INDEX_PATH = Path.home() / ".docsift" / "index.sqlite"
DEFAULT_CONFIG_PATH = Path.home() / ".docsift" / "config.yaml"
```

**Version option pattern** (lines 31-32):
```python
@click.group()
@click.version_option(version=__version__, prog_name="docsift")
```

**Subcommand import pattern** (lines 73-83):
```python
# Import and register subcommands
from docsift.cli.commands.collection import collection_group
from docsift.cli.commands.context import context_group
from docsift.cli.commands.get import get_group
from docsift.cli.commands.index import index_group
from docsift.cli.commands.ls import ls_cmd
from docsift.cli.commands.mcp import mcp_group
from docsift.cli.commands.bench import bench_cmd
from docsift.cli.commands.pull import pull_cmd
from docsift.cli.commands.search import search_group
```

**Status message pattern** (lines 105-106):
```python
    if not index_path.exists():
        console.print("[yellow]No index found. Run 'docsift update' to create one.[/yellow]")
        return
```

**Rename changes:**
- All imports: `from docsift...` -> `from sif...`
- `DEFAULT_INDEX_PATH = Path.home() / ".docsift"` -> `Path.home() / ".sif"`
- `DEFAULT_CONFIG_PATH = Path.home() / ".docsift"` -> `Path.home() / ".sif"`
- `prog_name="docsift"` -> `prog_name="sif"`
- `"Run 'docsift update'"` -> `"Run 'sif update'"`

---

### `src/sif/__init__.py` (module, static)

**Analog:** `src/docsift/__init__.py`

**Package init pattern** (lines 1-24):
```python
"""DocSift - Local AI-powered document search engine."""

__version__ = "0.1.0"
__author__ = "DocSift Team"
__description__ = "Local AI-powered document search engine"

from docsift.core.models import (
    Collection,
    Document,
    DocumentChunk,
    PathContext,
    SearchOptions,
    SearchResult,
)
```

**Rename changes:**
- Docstring: `"""DocSift..."""` -> `"""SIF..."""`
- `__author__ = "DocSift Team"` -> `__author__ = "SIF Team"`
- `from docsift.core.models` -> `from sif.core.models`

---

### `src/sif/models/download.py` (service, CRUD)

**Analog:** `src/docsift/models/download.py`

**Cache dir pattern** (lines 33-42):
```python
    def __init__(self, cache_dir: Optional[str | Path] = None) -> None:
        """Initialize model downloader.

        Args:
            cache_dir: Directory to cache downloaded models
        """
        if cache_dir is None:
            cache_dir = Path.home() / ".docsift" / "models"
        self.cache_dir = Path(cache_dir).expanduser().resolve()
        self.cache_dir.mkdir(parents=True, exist_ok=True)
```

**Rename changes:**
- `Path.home() / ".docsift" / "models"` -> `Path.home() / ".sif" / "models"`
- All imports: `from docsift...` -> `from sif...`

---

### `src/sif/cli/config.py` (config, static)

**Analog:** `src/docsift/cli/config.py`

**Default paths pattern** (lines 52-53):
```python
    # Paths
    index_path: str = field(default_factory=lambda: str(Path.home() / ".docsift" / "index.db"))
    config_path: str = field(default_factory=lambda: str(Path.home() / ".docsift" / "config.json"))
```

**Rename changes:**
- `Path.home() / ".docsift"` -> `Path.home() / ".sif"`

---

### `src/sif/cli/commands/*.py` (controller, request-response)

**Analog:** `src/docsift/cli/commands/search.py`

**Import pattern** (lines 1-18):
```python
"""Search commands."""

from __future__ import annotations

import json

import click
from rich.console import Console
from rich.table import Table

from docsift.cli.formatters import add_line_numbers_to_results, prepend_line_numbers
from docsift.core.models import SearchOptions
from docsift.database.database import Database
from docsift.database.repositories import CollectionRepository
from docsift.search.bm25 import BM25Searcher
from docsift.search.hybrid import SearchPipeline
from docsift.utils.logging import set_quiet
```

**Rename changes:**
- All imports: `from docsift...` -> `from sif...`
- All `docsift` strings in docstrings, help text, error messages -> `sif`

---

### `src/sif/mcp/server.py` (service, request-response)

**Analog:** `src/docsift/mcp/server.py`

**Import pattern** (lines 1-13):
```python
"""MCP server implementation."""

from __future__ import annotations

import json
import sys
from typing import Any, Dict, List

from docsift.database.connection import DatabaseConnection
from docsift.search.bm25 import BM25Searcher
from docsift.search.hybrid import HybridSearcher
from docsift.utils.logging import get_logger
```

**Rename changes:**
- All imports: `from docsift...` -> `from sif...`

---

### `src/sif/mcp_server/server.py` (service, request-response)

**Analog:** `src/docsift/mcp_server/server.py`

**Import pattern** (lines 1-6):
```python
"""MCP server implementation."""

from docsift.mcp_server.transport import Transport
from docsift.utils.logging import get_logger
```

**Docstring pattern** (lines 8-16):
```python
class MCPServer:
    """Model Context Protocol server for DocSift.

    Provides MCP-compliant endpoints for integration with
    AI assistants and other MCP-compatible tools.

    Supports both stdio and HTTP transports.
    """
```

**Rename changes:**
- All imports: `from docsift...` -> `from sif...`
- Docstring: `"DocSift"` -> `"SIF"`

---

### `src/sif/database/database.py` (service, CRUD)

**Analog:** `src/docsift/database/database.py`

**Import pattern** (lines 1-14):
```python
"""Database connection and management for DocSift."""

from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Generator, Optional

import sqlite_vec

from docsift.database.schema import SchemaManager
```

**Rename changes:**
- All imports: `from docsift...` -> `from sif...`
- Docstring: `"DocSift"` -> `"SIF"`

---

### `pyproject.toml` (config, static)

**Analog:** `pyproject.toml`

**Project name pattern** (lines 5-7):
```toml
[project]
name = "docsift"
version = "0.1.0"
description = "DocSift - Document indexing and search tool"
```

**Scripts pattern** (lines 63-64):
```toml
[project.scripts]
docsift = "docsift.cli.main:main"
```

**URLs pattern** (lines 66-69):
```toml
[project.urls]
Homepage = "https://github.com/docsift/docsift"
Documentation = "https://docsift.readthedocs.io"
Repository = "https://github.com/docsift/docsift"
```

**Build targets pattern** (lines 71-72):
```toml
[tool.hatch.build.targets.wheel]
packages = ["src/docsift"]
```

**Ruff isort pattern** (lines 159-164):
```toml
[tool.ruff.lint.isort]
known-first-party = ["docsift"]
known-third-party = ["click", "rich", "sentence_transformers", "numpy"]
combine-as-imports = true
split-on-trailing-comma = true
lines-after-imports = 2
```

**Per-file ignores pattern** (lines 171-174):
```toml
[tool.ruff.lint.per-file-ignores]
"tests/**/*" = ["D", "S101", "PLR2004"]
"src/docsift/cli/*.py" = ["T20"]
"__init__.py" = ["D104"]
```

**Pytest pattern** (lines 212-217):
```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py"]
python_classes = ["Test*"]
python_functions = ["test_*"]
addopts = "--cov=src/docsift --cov-report=term-missing --cov-report=html --cov-report=xml"
```

**Rename changes:**
- `name = "docsift"` -> `name = "sif"`
- `description = "DocSift..."` -> `description = "SIF..."`
- `docsift = "docsift.cli.main:main"` -> `sif = "sif.cli.main:main"`
- `Homepage = "https://github.com/docsift/docsift"` -> `Homepage = "https://github.com/zhangtaolab/sif"`
- `Documentation = "https://docsift.readthedocs.io"` -> `Documentation = "https://sif.readthedocs.io"`
- `Repository = "https://github.com/docsift/docsift"` -> `Repository = "https://github.com/zhangtaolab/sif"`
- `packages = ["src/docsift"]` -> `packages = ["src/sif"]`
- `known-first-party = ["docsift"]` -> `known-first-party = ["sif"]`
- `"src/docsift/cli/*.py"` -> `"src/sif/cli/*.py"`
- `addopts = "--cov=src/docsift` -> `addopts = "--cov=src/sif`

---

### `mypy.ini` (config, static)

**Analog:** `mypy.ini`

**Files pattern** (lines 42-48):
```ini
# Module search path
mypy_path = src

# Cache configuration
cache_dir = .mypy_cache

# Files to include/exclude
files = src/docsift
```

**Per-module pattern** (lines 67-69):
```ini
[mypy-src.docsift.cli.*]
# CLI modules may have less strict typing for click decorators
disallow_untyped_decorators = false
```

**Rename changes:**
- `files = src/docsift` -> `files = src/sif`
- `[mypy-src.docsift.cli.*]` -> `[mypy-src.sif.cli.*]`

---

### `mkdocs.yml` (config, static)

**Analog:** `mkdocs.yml`

**Site info pattern** (lines 1-6):
```yaml
# MkDocs configuration for DocSift documentation
site_name: DocSift Documentation
site_description: Local AI-powered document search engine
site_author: DocSift Team
site_url: https://docsift.readthedocs.io
```

**Social links pattern** (lines 107-114):
```yaml
# Extra social links
extra:
  social:
    - icon: fontawesome/brands/github
      link: https://github.com/docsift/docsift
    - icon: fontawesome/brands/python
      link: https://pypi.org/project/docsift/
  version:
    provider: mike
```

**Copyright pattern** (lines 117-122):
```yaml
# Copyright
copyright: Copyright &copy; 2024 DocSift Team

# Repository
repo_name: docsift/docsift
repo_url: https://github.com/docsift/docsift
```

**Rename changes:**
- `site_name: DocSift Documentation` -> `site_name: SIF Documentation`
- `site_author: DocSift Team` -> `site_author: SIF Team`
- `site_url: https://docsift.readthedocs.io` -> `site_url: https://sif.readthedocs.io`
- `link: https://github.com/docsift/docsift` -> `link: https://github.com/zhangtaolab/sif`
- `link: https://pypi.org/project/docsift/` -> `link: https://pypi.org/project/sif/`
- `copyright: Copyright &copy; 2024 DocSift Team` -> `copyright: Copyright &copy; 2024 SIF Team`
- `repo_name: docsift/docsift` -> `repo_name: zhangtaolab/sif`
- `repo_url: https://github.com/docsift/docsift` -> `repo_url: https://github.com/zhangtaolab/sif`

---

### `Makefile` (config, static)

**Analog:** `Makefile`

**Echo messages pattern** (lines 8, 41, 45, 49, 56, etc.):
```makefile
help:
	@echo "DocSift Development Commands"
	@echo "============================"

install:
	@echo "Installing DocSift..."

install-dev:
	@echo "Installing DocSift with development dependencies..."
```

**Coverage paths pattern** (lines 55-62):
```makefile
test:
	@echo "Running tests with coverage..."
	pytest --cov=src/docsift --cov-report=term-missing --cov-report=html --cov-report=xml
```

**Typecheck paths pattern** (lines 94-96):
```makefile
typecheck:
	@echo "Running mypy type checker..."
	mypy src/docsift
```

**Security paths pattern** (lines 104-107):
```makefile
security:
	@echo "Running security scan with bandit..."
	bandit -r src/docsift -c pyproject.toml
```

**Rename changes:**
- All `DocSift` -> `SIF`
- All `src/docsift` -> `src/sif`

---

### `.github/workflows/docs.yml` (config, static)

**Analog:** `.github/workflows/docs.yml`

**Path triggers pattern** (lines 4-12):
```yaml
on:
  pull_request:
    paths:
      - 'docs/**'
      - 'README.md'
      - 'src/docsift/cli/**'
      - 'src/docsift/config/**'
      - 'scripts/generate_cli_ref.py'
      - 'scripts/generate_config_ref.py'
      - 'tests/test_docs.py'
```

**Rename changes:**
- `'src/docsift/cli/**'` -> `'src/sif/cli/**'`
- `'src/docsift/config/**'` -> `'src/sif/config/**'`

---

### `tests/conftest.py` (test, static)

**Analog:** `tests/conftest.py`

**Import pattern** (lines 1-23):
```python
"""Shared pytest fixtures for DocSift tests."""

import hashlib
import tempfile
import uuid
from datetime import datetime
from pathlib import Path
from typing import Generator
from unittest.mock import MagicMock

import pytest

# Add src to path for imports
import sys

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from docsift.core.collection import Collection
from docsift.core.document import Document, DocumentChunk, DocumentMetadata
from docsift.core.context import Context, ContextType
from docsift.database.connection import DatabaseConnection
from docsift.models.search import SearchOptions, SearchResult, SearchType
```

**Docs runner fixture pattern** (lines 608-614):
```python
@pytest.fixture
def docs_runner(docs_test_db: Path) -> Generator["CliRunner", None, None]:
    """Provide a CliRunner with docs test database pre-configured."""
    from click.testing import CliRunner

    runner = CliRunner(env={"DOCSIFT_DB_PATH": str(docs_test_db)})
    yield runner
```

**Rename changes:**
- All imports: `from docsift...` -> `from sif...`
- `"DOCSIFT_DB_PATH"` -> `"SIF_DB_PATH"`

---

### `tests/unit/config/test_settings.py` (test, static)

**Analog:** `tests/unit/config/test_settings.py`

**Import pattern** (lines 1-6):
```python
"""Unit tests for DocSift Settings configuration."""

import pytest

from docsift.config.settings import Settings
```

**Env var test pattern** (lines 53-58):
```python
def test_model_type_env_var_override(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test that DOCSIFT_MODEL_TYPE env var overrides model_type."""
    with monkeypatch.context() as m:
        m.setenv("DOCSIFT_MODEL_TYPE", "openai")
        settings = Settings()
        assert settings.model_type == "openai"
```

**Rename changes:**
- Import: `from docsift.config.settings` -> `from sif.config.settings`
- Docstring: `"""Unit tests for DocSift..."""` -> `"""Unit tests for SIF..."""`
- `"DOCSIFT_MODEL_TYPE"` -> `"SIF_MODEL_TYPE"`

---

### `tests/unit/cli/test_status.py` (test, static)

**Analog:** `tests/unit/cli/test_status.py`

**Import pattern** (lines 1-10):
```python
"""Tests for status CLI command."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from click.testing import CliRunner

from docsift.cli.main import status_cmd
```

**Patch pattern** (lines 26-27):
```python
        with patch("docsift.cli.main.get_settings", return_value=mock_settings):
            with patch("docsift.cli.main.Database") as MockDB:
```

**Env var pattern** (lines 45-47):
```python
    def test_status_respects_env_var(self) -> None:
        """Test that status command respects DOCSIFT_DB_PATH env var."""
        runner = CliRunner(env={"DOCSIFT_DB_PATH": "/tmp/test-docsift.db"})
```

**Rename changes:**
- Import: `from docsift.cli.main` -> `from sif.cli.main`
- Patch: `"docsift.cli.main.get_settings"` -> `"sif.cli.main.get_settings"`
- Patch: `"docsift.cli.main.Database"` -> `"sif.cli.main.Database"`
- `"DOCSIFT_DB_PATH"` -> `"SIF_DB_PATH"`
- `"docsift.db"` -> `"sif.db"`

---

### `tests/test_docs.py` (test, static)

**Analog:** `tests/test_docs.py`

**Import pattern** (lines 1-16):
```python
"""Validate code blocks in documentation."""

from __future__ import annotations

import ast
import json
import re
from pathlib import Path
from typing import Any, ClassVar

import click
import pytest
from click.testing import CliRunner

from docsift.cli.main import cli
```

**Docsift command validation pattern** (lines 227-238):
```python
    def test_shell_commands_exist(self, docs_runner: CliRunner) -> None:
        """Shell commands starting with 'docsift' must be valid CLI commands."""
        for md_file in DOCS_FILES:
            if not md_file.exists():
                continue
            blocks = extract_code_blocks(md_file)
            for block in blocks:
                if block["language"] in ("bash", "shell", "sh", "zsh"):
                    commands = extract_shell_commands(block["content"])
                    for cmd in commands:
                        if cmd.startswith("docsift "):
                            self._verify_docsift_command(cmd, block["file"], docs_runner)
```

**Removed commands pattern** (lines 290-298):
```python
    def test_no_removed_commands_in_docs(self) -> None:
        """Docs must not contain removed commands."""
        removed_commands = [
            "docsift collection create",
            "docsift collection add-path",
```

**Rename changes:**
- Import: `from docsift.cli.main` -> `from sif.cli.main`
- `cmd.startswith("docsift ")` -> `cmd.startswith("sif ")`
- All `"docsift ..."` strings in removed_commands -> `"sif ..."`
- All `"docsift search"` patterns -> `"sif search"`
- All `"docsift collection"` patterns -> `"sif collection"`

---

### `tests/test_docsift_complete.py` (test, static)

**Analog:** `tests/test_docsift_complete.py`

**File rename:** `tests/test_docsift_complete.py` -> `tests/test_sif_complete.py`

**Import pattern** (lines 14-31):
```python
def test_imports() -> bool:
    """Test all core imports."""
    print("Testing imports...")
    try:
        from docsift.core.models import Collection, Document, SearchResult
        from docsift.database.database import Database
        from docsift.database.repositories import (
            CollectionRepository,
            DocumentRepository,
        )
        from docsift.database.schema import SchemaManager
        from docsift.search import BM25Searcher, HybridSearcher, RRFFusion, VectorSearcher
        from docsift.indexing import create_chunker
        from docsift.indexing.parser import MarkdownParser
        from docsift.indexing.scanner import FileScanner
        from docsift.cli.main import cli
        from docsift.mcp.server import MCPServer
```

**CLI test pattern** (lines 238-264):
```python
def test_cli() -> bool:
    """Test CLI."""
    print("\nTesting CLI...")
    try:
        from click.testing import CliRunner
        from docsift.cli.main import cli

        runner = CliRunner()

        # Test --help
        result = runner.invoke(cli, ["--help"])
        assert result.exit_code == 0
        assert "DocSift" in result.output
```

**Rename changes:**
- File: `tests/test_docsift_complete.py` -> `tests/test_sif_complete.py`
- All imports: `from docsift...` -> `from sif...`
- `assert "DocSift" in result.output` -> `assert "SIF" in result.output`
- `"DocSift Complete Test Suite"` -> `"SIF Complete Test Suite"`

---

### `scripts/generate_cli_ref.py` (script, file-I/O)

**Analog:** `scripts/generate_cli_ref.py`

**Import pattern** (lines 13-18):
```python
# Ensure docsift is importable
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from docsift.cli.main import cli  # noqa: E402
```

**Hardcoded docsift pattern** (lines 89, 167, 253-264, etc.):
```python
    section.append(f"```bash\ndocsift {path} [OPTIONS]\n```")

    lines.append("```")
    lines.append("docsift")
    lines.extend(_build_tree_lines(cli))
    lines.append("```")

    lines.append("**Setting up a new collection:**")
    lines.append("```bash")
    lines.append("# Add a collection")
    lines.append(
        'docsift collection add ~/Documents/notes '
        '--name my-notes --description "Personal notes"'
    )
    lines.append("")
    lines.append("# Update index")
    lines.append("docsift index update my-notes")
```

**Rename changes:**
- Import: `from docsift.cli.main` -> `from sif.cli.main`
- All `"docsift "` -> `"sif "`
- All `"DocSift"` -> `"SIF"`

---

### `scripts/generate_config_ref.py` (script, file-I/O)

**Analog:** `scripts/generate_config_ref.py`

**Import pattern** (lines 11-15):
```python
# Ensure the src directory is on the path so we can import docsift
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from docsift.config.settings import Settings  # noqa: E402
```

**Computed defaults pattern** (lines 63-69):
```python
def get_computed_default(field_name: str) -> str | None:
    """Return computed default description for Path fields that default to None."""
    computed = {
        "db_path": "~/.local/share/docsift/docsift.db (computed)",
        "cache_dir": "~/.cache/docsift (computed)",
    }
    return computed.get(field_name)
```

**Hardcoded strings pattern** (lines 106-135):
```python
    lines.append("# Configuration")
    lines.append("")
    lines.append(
        "DocSift can be configured through environment variables or a `.env` file. "
        "This guide covers all available configuration options."
    )
    ...
    lines.append("```bash")
    lines.append("export DOCSIFT_DB_PATH=/custom/path/docsift.db")
    lines.append("export DOCSIFT_LOG_LEVEL=DEBUG")
    lines.append("```")
```

**Rename changes:**
- Import: `from docsift.config.settings` -> `from sif.config.settings`
- `"~/.local/share/docsift/docsift.db"` -> `"~/.local/share/sif/sif.db"`
- `"~/.cache/docsift"` -> `"~/.cache/sif"`
- `"DocSift"` -> `"SIF"`
- `"DOCSIFT_"` -> `"SIF_"`
- `"docsift config show"` -> `"sif config show"`

---

### `examples/quickstart.py` (example, static)

**Analog:** `examples/quickstart.py`

**Docstring pattern** (lines 1-19):
```python
"""
DocSift Quickstart Example

This script demonstrates the basic usage of DocSift for document indexing and search.

Prerequisites:
    pip install docsift

Usage:
    python quickstart.py

This example will:
    1. Initialize a DocSift database
    2. Add a document collection
    3. Index documents
    4. Perform searches
    5. Display results
"""
```

**Import pattern** (lines 168, 204, 244, 313):
```python
        from docsift.database import DatabaseConnection, MigrationManager
        from docsift.core import Collection
        from docsift.search import BM25SearchStrategy, SearchContext
        from docsift.cli.config import Config
```

**CLI examples pattern** (lines 272-303):
```python
    print("""
Common DocSift CLI commands:

# Show help
docsift --help

# Add a collection
docsift collection add /path/to/documents --name mydocs
```

**Rename changes:**
- All `DocSift` -> `SIF`
- All `docsift` -> `sif`
- All imports: `from docsift...` -> `from sif...`

---

### `.claude/skills/sif-search/SKILL.md` (skill, static)

**Analog:** `.claude/skills/docsift-search/SKILL.md`

**Skill metadata pattern** (lines 1-7):
```yaml
---
name: docsift-search
description: "Search documents in DocSift index using BM25, vector, or hybrid search"
argument-hint: "<query> [--strategy query|search|vsearch] [--collection NAME] [--limit N] [--all]"
allowed-tools:
  - Bash
---
```

**CLI command patterns** (lines 34-56):
```bash
   docsift -q search query --json --limit 10 --line-numbers "{query}"
   docsift -q search search --json --limit 10 --line-numbers "{query}"
   docsift -q search vsearch --json --limit 10 --line-numbers "{query}"
   docsift -q search query --json --limit 10 --line-numbers -c "{collection}" "{query}"
   docsift -q search query --json --limit 10 --line-numbers --all "{query}"
```

**Rename changes:**
- `name: docsift-search` -> `name: sif-search`
- `description: "Search documents in DocSift..."` -> `description: "Search documents in SIF..."`
- All `docsift` -> `sif`
- All `DocSift` -> `SIF`

---

### `.claude/skills/sif-get/SKILL.md` (skill, static)

**Analog:** `.claude/skills/docsift-get/SKILL.md`

**Skill metadata pattern** (lines 1-7):
```yaml
---
name: docsift-get
description: "Retrieve document content from DocSift index by path, ID, or pattern"
argument-hint: "<path_or_pattern> [--lines N] [--from-line M]"
allowed-tools:
  - Bash
---
```

**CLI command patterns** (lines 34-61):
```bash
   docsift -q get get --line-numbers "{path}"
   docsift -q get get --line-numbers "{doc_id}"
   docsift -q get get --line-numbers --lines 50 "{path}"
   docsift -q get get --line-numbers --from-line 10 --lines 20 "{path}"
   docsift -q get multi-get --line-numbers "{pattern}"
   docsift -q get multi-get --line-numbers "{path1},{path2},{path3}"
```

**Rename changes:**
- `name: docsift-get` -> `name: sif-get`
- `description: "Retrieve document content from DocSift..."` -> `description: "Retrieve document content from SIF..."`
- All `docsift` -> `sif`
- All `DocSift` -> `SIF`

---

## Shared Patterns

### Import Path Update
**Source:** All Python files under `src/docsift/`, `tests/`, `scripts/`, `examples/`
**Apply to:** Every Python file
```python
# Before
from docsift.config.settings import Settings
from docsift.cli.main import cli
import docsift

# After
from sif.config.settings import Settings
from sif.cli.main import cli
import sif
```

### Patch Target Update in Tests
**Source:** All test files using `unittest.mock.patch`
**Apply to:** Every test file with `patch("docsift...")`
```python
# Before
with patch("docsift.cli.commands.search.Database") as mock_db:
with patch("docsift.cli.main.get_settings") as mock_settings:

# After
with patch("sif.cli.commands.search.Database") as mock_db:
with patch("sif.cli.main.get_settings") as mock_settings:
```

### Environment Variable Prefix Update
**Source:** `src/docsift/config/settings.py`, all test files, docs
**Apply to:** All files referencing `DOCSIFT_*` env vars
```python
# Before
m.setenv("DOCSIFT_MODEL_TYPE", "openai")
runner = CliRunner(env={"DOCSIFT_DB_PATH": "/tmp/test.db"})

# After
m.setenv("SIF_MODEL_TYPE", "openai")
runner = CliRunner(env={"SIF_DB_PATH": "/tmp/test.db"})
```

### Data Path Update
**Source:** `src/docsift/config/constants.py`, `src/docsift/cli/main.py`, `src/docsift/cli/config.py`, `src/docsift/models/download.py`
**Apply to:** All files with hardcoded `~/.docsift/` paths
```python
# Before
DEFAULT_DB_PATH = "~/.local/share/docsift/docsift.db"
DEFAULT_MODEL_PATH = "~/.local/share/docsift/models"
cache_dir = Path.home() / ".docsift" / "models"

# After
DEFAULT_DB_PATH = "~/.local/share/sif/sif.db"
DEFAULT_MODEL_PATH = "~/.local/share/sif/models"
cache_dir = Path.home() / ".sif" / "models"
```

### Logger Namespace Update
**Source:** `src/docsift/utils/logging.py`
**Apply to:** Only this file
```python
# Before
root_logger = logging.getLogger("docsift")
return logging.getLogger(f"docsift.{name}")

# After
root_logger = logging.getLogger("sif")
return logging.getLogger(f"sif.{name}")
```

### CLI Entry Point Update
**Source:** `pyproject.toml`
**Apply to:** Only this file
```toml
# Before
[project.scripts]
docsift = "docsift.cli.main:main"

# After
[project.scripts]
sif = "sif.cli.main:main"
```

### ruff known-first-party Update
**Source:** `pyproject.toml`
**Apply to:** Only this file
```toml
# Before
[tool.ruff.lint.isort]
known-first-party = ["docsift"]

# After
[tool.ruff.lint.isort]
known-first-party = ["sif"]
```

### pytest coverage path Update
**Source:** `pyproject.toml`
**Apply to:** Only this file
```toml
# Before
addopts = "--cov=src/docsift --cov-report=term-missing ..."

# After
addopts = "--cov=src/sif --cov-report=term-missing ..."
```

### Model Cache Auto-Migration (new code)
**Source:** `src/sif/cli/main.py` (new addition per D-02)
**Pattern to follow:** Use `rich.console.Console` for output, `pathlib.Path.rename()` for atomic move
```python
from pathlib import Path
from rich.console import Console

console = Console()

def _migrate_model_cache() -> None:
    """Migrate old model cache directory to new location on first run."""
    old_dir = Path.home() / ".docsift" / "models"
    new_dir = Path.home() / ".sif" / "models"
    if old_dir.exists() and not new_dir.exists():
        old_dir.rename(new_dir)
        console.print(f"[green]Migrated: {old_dir} -> {new_dir}[/green]")
    elif old_dir.exists() and new_dir.exists():
        console.print(
            f"[yellow]Warning: Both old and new model cache dirs exist. "
            f"Old: {old_dir}, New: {new_dir}[/yellow]"
        )
```

## No Analog Found

No files lack analogs. This is a pure rename phase; every file to be modified has an exact analog in the current codebase.

## Metadata

**Analog search scope:** `src/docsift/`, `tests/`, `scripts/`, `docs/`, `.claude/skills/`, `.github/workflows/`, root config files
**Files scanned:** 40+
**Pattern extraction date:** 2026-04-27
