<!-- generated-by: gsd-doc-writer -->
# Development Guide

Guide for contributing to SIF development.

## Setup

### Prerequisites

- Python 3.10+ (`requires-python = ">=3.10"` in `pyproject.toml`)
- Git
- Virtual environment tool (venv, conda, or pyenv)

The distribution is published as `docsif`; the installed command is `sif`.

### Clone Repository

```bash
git clone https://github.com/zhangtaolab/sif.git
cd sif
```

### Create Virtual Environment

```bash
# Using venv
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Using conda
conda create -n sif python=3.11
conda activate sif
```

### Install Dependencies

```bash
# Install in development mode with the dev toolchain
pip install -e ".[dev]"

# Install every optional embedding backend as well
pip install -e ".[dev,all]"

# Or install specific groups
pip install -e ".[dev]"      # Development only (pytest, ruff, ty, ...)
pip install -e ".[embed]"    # sentence-transformers, ModelScope
pip install -e ".[all]"      # Every embedding backend, including llama-cpp-python and OpenAI
```

### Verify Installation

```bash
# Check version
sif --version

# Run tests
pytest

# Check code style
ruff check .
```

## Project Structure

```
sif/
├── src/sif/
│   ├── cli/               # Click CLI (main.py entry; commands/ holds one module per group)
│   ├── mcp/               # MCP server, handlers, and stdio/HTTP transports
│   ├── core/              # Domain entities and protocol seams
│   ├── models/            # Pydantic boundary schemas (search, collection, ...)
│   ├── database/          # Connection, schema, migrations, repositories
│   ├── search/            # BM25, vector, hybrid pipeline, RRF, reranking
│   ├── indexing/          # Chunkers, incremental indexer, drift detection, watcher
│   ├── embedding/         # Embedder factory, managers, cache, providers
│   ├── config/            # Pydantic Settings and constants
│   └── utils/             # Logging, paths, daemon, progress helpers
├── tests/
│   ├── unit/              # Unit tests grouped by module area
│   ├── integration/       # Cross-component and subprocess tests
│   ├── e2e/               # End-to-end tests (placeholder — only __init__.py)
│   ├── fixtures/bench/    # Benchmark corpus and query fixtures
│   ├── support/           # Shared test support (bench harness)
│   ├── conftest.py        # Shared fixtures
│   ├── factories.py       # Reusable test data factories
│   └── test_docs.py       # Documentation validation tests
├── scripts/               # Doc generators and benchmark fixture builder
├── examples/              # Runnable quickstart example
├── docs/                  # Documentation (MkDocs source)
├── pyproject.toml         # Project configuration
├── Makefile               # Convenience targets for common tasks
├── mkdocs.yml             # MkDocs site configuration
└── README.md              # Project readme
```

## Development Workflow

### 1. Create Branch

```bash
git checkout -b feature/my-feature
# or
git checkout -b fix/my-bugfix
```

### 2. Make Changes

Edit code following the style guidelines.

### 3. Run Tests

```bash
# Run all tests
pytest

# Run with an HTML coverage report (coverage is enabled by default)
pytest --cov-report=html

# Run specific test file
pytest tests/unit/test_collection.py

# Run with verbose output
pytest -v
```

Every pytest run collects coverage because the flags live in `addopts`; add `--no-cov` when iterating on a narrow slice (see [Coverage Requirements](#coverage-requirements)).

### 4. Check Code Quality

```bash
# Format code
ruff format .

# Lint code
ruff check .

# Type checking
ty check src/sif
```

### 5. Commit Changes

```bash
git add .
git commit -m "feat: add new feature"
```

Follow [Conventional Commits](https://www.conventionalcommits.org/):

- `feat:` New feature
- `fix:` Bug fix
- `docs:` Documentation
- `style:` Code style (formatting)
- `refactor:` Code refactoring
- `test:` Tests
- `chore:` Maintenance

### 6. Push and Create PR

```bash
git push origin feature/my-feature
```

Create a pull request on GitHub.

## Code Style

### Formatting

We use Ruff for formatting:

```bash
# Format all files
ruff format .

# Check formatting
ruff format --check .
```

Configuration in `pyproject.toml`:

```toml
[tool.ruff]
line-length = 100
target-version = "py310"
```

### Linting

```bash
# Lint all files
ruff check .

# Fix auto-fixable issues
ruff check --fix .
```

The lint configuration selects pycodestyle, Pyflakes, isort, pydocstyle, pyupgrade, bugbear, simplify, mccabe, and related rule families, with `max-complexity = 10` and the Google docstring convention.

### Type Hints

All code must have type hints, checked with ty:

```python
from typing import Any

from sif.core.collection import Collection


class CollectionManager:
    def create_collection(
        self,
        name: str,
        description: str | None = None,
        paths: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> Collection:
        """Create a new collection."""
        ...
```

Use `list[str] | None` union syntax (Python 3.10+), not `Optional[...]`.

### Docstrings

Use Google-style docstrings (enforced by Ruff's pydocstyle rules):

```python
def search(
    self,
    query: str,
    options: SearchOptions | None = None,
) -> list[SearchResult]:
    """Search using hybrid approach (BM25 + Vector + RRF).

    Args:
        query: Search query
        options: Search options

    Returns:
        Ranked list of search results
    """
```

## Testing

### Test Structure

```
tests/
├── conftest.py           # Shared fixtures
├── factories.py          # Test data factories
├── unit/                 # Unit tests grouped by module area
│   ├── test_collection.py
│   ├── test_search.py
│   ├── cli/
│   ├── config/
│   ├── core/
│   ├── database/
│   ├── db/
│   ├── embedding/
│   ├── indexing/
│   ├── inference/
│   ├── mcp/
│   ├── models/
│   ├── search/
│   └── utils/
├── integration/          # Cross-component and subprocess tests
│   ├── test_concurrency.py
│   ├── test_embed_idempotency.py
│   ├── test_search_pipeline.py
│   └── ...               # Watch, MCP, and incremental-equivalence tests
├── e2e/                  # End-to-end tests (placeholder — only __init__.py)
├── fixtures/bench/       # Benchmark corpus and query fixtures
├── support/              # Bench harness helpers
└── test_docs.py          # Documentation validation
```

### Writing Tests

```python
# tests/unit/test_collection.py
import pytest

from sif.core.collection import Collection, CollectionManager

# MockCollectionRepository is defined inline in the real
# tests/unit/test_collection.py as an in-memory fake.


class TestCollection:
    def test_create_collection(self):
        collection = Collection(
            id="test-id",
            name="test-collection",
        )
        assert collection.name == "test-collection"

    def test_add_path(self):
        collection = Collection(id="test-id", name="test")
        collection.add_path("/path/to/docs")
        assert "/path/to/docs" in collection.paths


class TestCollectionManager:
    @pytest.fixture
    def manager(self):
        return CollectionManager(MockCollectionRepository())

    def test_create_collection(self, manager):
        collection = manager.create_collection(name="my-collection")

        assert collection.name == "my-collection"

    def test_create_duplicate_raises(self, manager):
        manager.create_collection(name="my-collection")

        with pytest.raises(ValueError, match="already exists"):
            manager.create_collection(name="my-collection")
```

When the collaborator is a protocol, prefer a spec'd mock over a hand-written fake — for example `MagicMock(spec=CollectionRepository)` in `tests/unit/core/test_collection_entity.py`.

### Fixtures

`tests/conftest.py` provides the shared fixtures used across the suite:

- Path and file fixtures: `temp_dir`, `sample_markdown_file`, `sample_markdown_content`
- Database fixtures: `temp_db_path`, `db_connection`, `temp_db`
- Domain fixtures: `sample_collection`, `sample_collections`, `sample_document`, `sample_documents`, `sample_chunk`, `sample_chunks`, `sample_context`
- Search fixtures: `sample_search_options`, `sample_search_result`, `sample_search_results`
- Mock fixtures: `mock_embedder`, `mock_repository`, `mock_search_repository`, `mock_embedding_manager`
- Docs fixtures: `docs_test_db`, `docs_runner` (used by `test_docs.py`)

`tests/factories.py` adds reusable factories (`CollectionFactory`, `DocumentFactory`, `DocumentChunkFactory`, `ContextFactory`, `SearchOptionsFactory`, `SearchResultFactory`) when a test needs several related objects. See [Testing](testing.md) for the full fixture catalogue and factory usage.

### Running Tests

```bash
# Run all tests
pytest

# Run with an HTML coverage report
pytest --cov-report=html

# Run specific test
pytest tests/unit/test_collection.py::TestCollectionManager::test_create_collection

# Run a subset by directory
pytest tests/unit/
pytest tests/integration/
```

Because coverage flags are in `addopts`, every invocation collects coverage and enforces the 90% gate. Add `--no-cov` when running a narrow slice:

```bash
pytest tests/unit/test_collection.py --no-cov
```

### Test Selection

No custom pytest markers (`unit`, `integration`, `slow`) are registered in `pyproject.toml`
and none are used in the test suite — select tests by directory instead:

```bash
# Unit tests only
pytest tests/unit/

# Integration tests only
pytest tests/integration/
```

Built-in pytest markers such as `skip` are still available:

```python
import pytest

@pytest.mark.skip(reason="Not implemented")
def test_future_feature():
    pass
```

## Debugging

### Logging

The CLI derives its log level from its own flags in `src/sif/cli/main.py`; `--verbose` maps to DEBUG and `--quiet` to WARNING:

```bash
# DEBUG logging
sif --verbose search search "query"

# WARNING logging
sif --quiet search search "query"
```

From Python code, call the same helper:

```python
from sif.utils.logging import setup_logging

setup_logging("DEBUG")
```

`SIF_LOG_LEVEL` is read by the CLI when neither `--verbose` nor `--quiet` is given; the flags win when present.

### IDE Setup

#### VS Code

`.vscode/launch.json`:

```json
{
  "version": "0.2.0",
  "configurations": [
    {
      "name": "Python: SIF CLI",
      "type": "python",
      "request": "launch",
      "module": "sif.cli.main",
      "args": ["search", "python decorators"],
      "console": "integratedTerminal"
    },
    {
      "name": "Python: Current File",
      "type": "python",
      "request": "launch",
      "program": "${file}",
      "console": "integratedTerminal"
    }
  ]
}
```

#### PyCharm

1. Go to Run → Edit Configurations
2. Add new Python configuration
3. Set script path to `src/sif/cli/main.py`
4. Set parameters to your command arguments

### Profiling

```python
import cProfile
import pstats

profiler = cProfile.Profile()
profiler.enable()

# `pipeline` is a SearchPipeline built against an initialized Database
results = pipeline.search(query)

profiler.disable()
stats = pstats.Stats(profiler)
stats.sort_stats("cumulative")
stats.print_stats(20)
```

`SearchPipeline` lives in `src/sif/search/hybrid.py` and is what both the CLI and the MCP backend use for query routing, expansion, RRF, reranking, and snippets.

## Database Development

### Schema Changes

Runtime schema creation lives in `SchemaManager.create_all()` in `src/sif/database/schema.py`, which `Database.init_schema()` calls on first use. Add tables, indexes, FTS/vector DDL, or additive columns there:

- For a new column, follow `_add_column_if_missing` (see `collections.pre_update_cmd` at `src/sif/database/schema.py`), which checks `PRAGMA table_info` before altering the table so existing indexes pick the column up in place.
- For data rewrites, follow `_migrate_path_contexts()`, which moves `path_contexts` rows into `contexts` inside a SAVEPOINT.
- Update the schema tests under `tests/unit/database/` (`test_schema.py`).

`Database.reset()` drops and recreates the schema when you need a clean local index.

### Testing with Real Data

```bash
# Use test database
export SIF_DB_PATH=./test.db

# Add test data as a collection, then index and embed it
sif collection add ./test-data --name test
sif index update
sif index embed

# Run queries
sif search search "test query"
```

## Adding New Features

### New Search Strategy

1. Add a searcher module under `src/sif/search/` that takes a `sqlite3.Connection` (plus any embedder it needs) and exposes a `search` method returning `list[SearchResult]`. Use the `SearchOptions` and `SearchResult` dataclasses from `sif.core.models` — they are the types the live searchers accept and return:

```python
# src/sif/search/custom.py
import sqlite3

from sif.core.models import SearchOptions, SearchResult


class CustomSearcher:
    def __init__(self, db: sqlite3.Connection) -> None:
        self.db = db

    def search(
        self,
        query: str,
        options: SearchOptions | None = None,
    ) -> list[SearchResult]:
        """Execute the custom search and return ranked results."""
        ...
```

2. Add tests in `tests/unit/search/`.

3. Wire it into the live search path in `src/sif/search/hybrid.py`: construct it in `HybridSearcher` and fuse its results, or route a new query prefix from `SearchPipeline.search()`. The CLI (`src/sif/cli/commands/search.py`) and MCP backend (`src/sif/mcp/backend.py`) both construct `SearchPipeline`, so wiring it there covers both front ends.

### New CLI Command

1. Create the command in `src/sif/cli/commands/`:

```python
# src/sif/cli/commands/custom.py
import click


@click.command(name="custom")
@click.argument("input")
def custom_command(input: str) -> None:
    """Custom command description."""
    click.echo(f"Processing: {input}")
```

2. Add the import alongside the other deferred imports at the bottom of `src/sif/cli/main.py` (they run after the `cli` group is defined to avoid circular imports) and register it:

```python
from sif.cli.commands.custom import custom_command  # noqa: E402

cli.add_command(custom_command)
```

3. Add tests under `tests/unit/cli/` and regenerate `docs/cli-reference.md` with `make docs-generate`.

### New Model

Pydantic boundary schemas live in `src/sif/models/`; domain entities and protocols live in `src/sif/core/`.

1. Create the Pydantic model in `src/sif/models/`:

```python
# src/sif/models/custom.py
from pydantic import BaseModel, Field


class CustomModel(BaseModel):
    name: str = Field(..., min_length=1)
    value: int = Field(0, ge=0)
```

2. Add a corresponding domain entity in `src/sif/core/` if the model needs behavior (see `Collection` and `CollectionManager` in `src/sif/core/collection.py`).

3. If the model is persisted, add the schema to `SchemaManager` (see [Database Development](#database-development)) and a repository in `src/sif/database/repositories.py`.

## Release Process

### Version Bump

1. Update `__version__` in `src/sif/_version.py` (currently `1.1.1`)

2. Update `docs/changelog.md`

3. Create a git tag (existing tags use the `vX.Y[.Z]` form):

```bash
git tag -a v1.1.1 -m "Release version 1.1.1"
git push origin v1.1.1
```

### Build Package

```bash
# Install build tools
pip install build twine

# Build package (hatchling backend)
python -m build

# Check package
twine check dist/*

# Upload to PyPI (maintainers only)
twine upload dist/*
```

## Troubleshooting

### Common Issues

**Import errors:**
```bash
# Reinstall in development mode
pip install -e ".[dev]"
```

**Test failures:**
```bash
# Clear pytest cache
pytest --cache-clear

# Run with a fresh database
rm test.db
pytest
```

**Type checking errors:**
```bash
# Re-run the type checker directly
ty check src/sif

# Point ty at the project virtual environment if imports are unresolved
ty check --python .venv/bin/python src/sif
```

## Resources

- [Python Documentation](https://docs.python.org/3/)
- [Click Documentation](https://click.palletsprojects.com/)
- [Pydantic Documentation](https://docs.pydantic.dev/)
- [Pytest Documentation](https://docs.pytest.org/)
- [Ruff Documentation](https://docs.astral.sh/ruff/)

## Getting Help

- GitHub Issues: [github.com/zhangtaolab/sif/issues](https://github.com/zhangtaolab/sif/issues)
- Discussions: [github.com/zhangtaolab/sif/discussions](https://github.com/zhangtaolab/sif/discussions)

## Build Commands

The [Makefile](../Makefile) defines convenience targets for every common development task. Run `make help` to see the full list from the command line.

### Installation and Setup

| Command | Description |
|---------|-------------|
| `make install` | Install the package with basic dependencies (`pip install -e .`) |
| `make install-dev` | Install with development dependencies (`pip install -e ".[dev]"`) |
| `make install-all` | Install with all optional dependencies (`pip install -e ".[dev,all]"`) |
| `make dev-setup` | Alias for `make install-dev` |
| `make update-deps` | Upgrade pip and reinstall all dependencies |

### Testing and Quality

| Command | Description |
|---------|-------------|
| `make test` | Run tests with coverage (terminal, HTML, and XML reports) |
| `make test-verbose` | Run tests verbosely (`pytest -vvs --tb=short`) with coverage |
| `make test-fast` | Run tests stopping at the first failure (`pytest -x -q`); coverage is still collected via `addopts` — the speed comes from `-x` and `-q`, not from skipping coverage |
| `make lint` | Run the ruff linter (`ruff check .`) |
| `make lint-fix` | Lint and auto-fix (`ruff check --fix .`) |
| `make format` | Format code with ruff (`ruff format .`) |
| `make format-check` | Check formatting without modifying files |
| `make typecheck` | Type check with ty (`ty check src/sif`) |
| `make coverage` | Generate an HTML coverage report at `htmlcov/index.html` |
| `make security` | Run a bandit security scan (`bandit -r src/sif -c pyproject.toml`) |

### Build and Maintenance

| Command | Description |
|---------|-------------|
| `make build` | Build the sdist and wheel (`python -m build`); runs `check-wheel-contents` and `twine check` when installed, and skips them with a message otherwise |
| `make clean` | Remove build artifacts, caches, and coverage output |
| `make clean-all` | `make clean` plus removal of `venv/` and `.venv/` |
| `make docs` | Placeholder — prints "Documentation build not yet configured" |
| `make docs-test` | Run the documentation validation tests (`pytest tests/test_docs.py -v --no-cov`) |
| `make docs-generate` | Regenerate `docs/cli-reference.md` and `docs/configuration.md` from source |
| `make all` | Run `lint`, `typecheck`, and `test` |
| `make ci` | Run all CI checks locally: `format-check`, `lint`, `typecheck`, `security`, `test` |
| `make dev-check` | Format, lint with auto-fix, then type check |
| `make info` | Print the Python version and installed tool versions |

The `security` target requires `bandit`, and `make build` requires `build`; none of these are included in the `[dev]` extras, so install them separately when needed. `check-wheel-contents` and `twine` are optional — `make build` skips them with a message when they are missing.

## Branch Conventions

- The default branch is `main`: `origin/HEAD` points to `origin/main`, and pull requests are opened against it.
- A `dev` branch carries in-progress work before it lands on `main`.
- Name feature branches `feature/<short-description>` and bug fix branches `fix/<short-description>`, as shown in [Development Workflow](#development-workflow). No additional convention is formally documented.

## PR Process

- Push your branch and open the pull request against `main` on GitHub. There is no `.github/PULL_REQUEST_TEMPLATE.md`; follow the description template in [Contributing](contributing.md) (Description, Type of Change, Testing, Checklist).
- Before requesting review, the [Contributing](contributing.md) checklist expects: `pytest` passes, `ruff format .` applied, `ruff check .` clean, `ty check src/sif` passes, and documentation (including `docs/changelog.md`) updated.
- Commit messages follow Conventional Commits, as described in Commit Changes above.
- PR CI only validates documentation: the "Docs Validation" workflow (`.github/workflows/docs.yml`) runs `pytest tests/test_docs.py` and regenerates `docs/cli-reference.md` and `docs/configuration.md` whenever a PR touches `docs/**`, `README.md`, `src/sif/cli/**`, `src/sif/config/**`, the generation scripts, or `tests/test_docs.py` — it fails if the committed reference docs are stale. The workflow also runs on pushes to `main`. No workflow runs the full test suite or linters on PRs, so run `make ci` locally before pushing.
- Review turnaround is not documented; maintainers triage pull requests on GitHub. Respond to comments and push follow-up commits to the same branch.

## Coverage Requirements

`pyproject.toml` enforces a coverage minimum on every pytest run:

- `[tool.pytest.ini_options]` sets `addopts = "--cov=src/sif --cov-report=term-missing --cov-report=html --cov-report=xml"`, so coverage is collected on every invocation.
- `[tool.coverage.report]` sets `fail_under = 90`: pytest-cov fails the run when total coverage of `src/sif` falls below 90%.

Because the coverage flags live in `addopts`, they apply to the Makefile targets too — `make test-fast` runs `pytest -x -q`, which still collects coverage. The gate measures coverage across all of `src/sif`, not just the code under test, so a subset run fails even when all of its tests pass:

```bash
# Every test in the file passes, but the run still fails the gate:
pytest tests/unit/test_collection.py -q
# FAIL Required test coverage of 90.0% not reached. Total coverage: 12.96%
```

Append `--no-cov` when iterating on a narrow slice of the suite:

```bash
# Run one file without the coverage gate
pytest tests/unit/test_collection.py --no-cov

# Fast loop on a single test
pytest tests/unit/search/test_bm25.py::TestBM25Searcher::test_search_executes_fts_query --no-cov
```

Before pushing, run the full suite (`pytest` or `make test`) so the 90% gate is evaluated over real totals. See [Testing](testing.md) for the suite layout, shared fixtures, and factories.

## Generated Documentation

Some documentation files are generated from source — edit the source, then regenerate; never edit the generated files by hand.

| File | Generated by | How to refresh |
|------|--------------|----------------|
| `docs/cli-reference.md` | `scripts/generate_cli_ref.py` (Click introspection) | `make docs-generate` |
| `docs/configuration.md` | `scripts/generate_config_ref.py` (Pydantic Settings introspection) | `make docs-generate` |
| Mermaid package diagram in `docs/architecture.md` | `scripts/generate_arch_diagram.py` (source import scan) | Run `python scripts/generate_arch_diagram.py` and replace the diagram block with the printed output |

The "Docs Validation" workflow (`.github/workflows/docs.yml`) regenerates `docs/cli-reference.md` and `docs/configuration.md` on every PR that touches `docs/**`, `README.md`, `src/sif/cli/**`, `src/sif/config/**`, the generator scripts, or `tests/test_docs.py` (and on pushes to `main`), then fails on any diff (`git diff --exit-code`). After changing the CLI or settings, run `make docs-generate` and commit the regenerated docs together with the code change. The architecture diagram script is not wired into `make docs-generate` or CI — regenerate it manually when package-level dependencies change.

### Documentation Tests

`make docs-test` (`pytest tests/test_docs.py -v --no-cov`) validates the code blocks in `README.md`, `docs/index.md`, `docs/cli-reference.md`, `docs/configuration.md`, `docs/quickstart.md`, `docs/mcp-server.md`, `docs/search-algorithms.md`, `docs/benchmarking.md`, `docs/architecture.md`, and `docs/models.md`:

- JSON blocks must parse, and JSON output examples must contain the expected keys.
- Python blocks must be syntactically valid.
- Every `sif` command in shell blocks must exist in the live Click tree — removed or renamed commands fail the suite.
- Stale content is rejected: removed commands (for example `sif collection create`), outdated default model names, and bare `sif search <query>` (use `sif search search`, `sif search query`, or `sif search vsearch`).

This file, `testing.md`, and `contributing.md` are not in the validated set.

### Documentation Site

Docs are wired for MkDocs with the Material theme (`mkdocs.yml`, source directory `docs/`). When you add a page under `docs/`, also list it in the `nav` mapping in `mkdocs.yml` so it appears in the site navigation. There is no configured site build yet — `make docs` prints "Documentation build not yet configured" — and the MkDocs toolchain is not part of any dependency extras in `pyproject.toml`.

## Related Documentation

- [Contributing](contributing.md) - Contribution guidelines
- [Testing](testing.md) - Test suite layout, fixtures, and coverage
- [Architecture](architecture.md) - System architecture
- [API Reference](api-reference.md) - Python API
