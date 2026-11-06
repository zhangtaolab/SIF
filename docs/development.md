# Development Guide

Guide for contributing to SIF development.

## Setup

### Prerequisites

- Python 3.10+
- Git
- Virtual environment tool (venv, conda, or pyenv)

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
# Install in development mode with all dependencies
pip install -e ".[dev,all]"

# Or install specific groups
pip install -e ".[dev]"      # Development only
pip install -e ".[embed]"    # Embedding support
pip install -e ".[all]"      # Everything
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
├── src/sif/           # Source code
│   ├── core/              # Domain entities
│   ├── models/            # Pydantic models
│   ├── database/          # Data access
│   ├── search/            # Search algorithms
│   ├── indexing/          # Document indexing
│   ├── embedding/         # Embedding models
│   ├── mcp/               # MCP server
│   ├── cli/               # Command-line interface
│   └── utils/             # Utilities
├── tests/                 # Test suite
│   ├── unit/              # Unit tests
│   ├── integration/       # Integration tests
│   └── conftest.py        # Test fixtures
├── docs/                  # Documentation
├── pyproject.toml         # Project configuration
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

# Run with coverage
pytest --cov=sif

# Run specific test file
pytest tests/unit/test_collection.py

# Run with verbose output
pytest -v
```

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

### Type Hints

All code must have type hints:

```python
def process_document(
    document: Document,
    options: ProcessingOptions | None = None,
) -> ProcessedDocument:
    """Process a document with options."""
    ...
```

### Docstrings

Use Google-style docstrings:

```python
def search(
    self,
    context: SearchContext,
    options: SearchOptions,
) -> list[SearchResult]:
    """Execute search and return results.
    
    Args:
        context: Search context with query and embeddings
        options: Search options and parameters
        
    Returns:
        List of search results ordered by relevance
        
    Raises:
        ValueError: If query is empty
        SearchError: If search fails
    """
```

## Testing

### Test Structure

```
tests/
├── conftest.py           # Shared fixtures
├── unit/                 # Unit tests
│   ├── test_collection.py
│   ├── test_search.py
│   └── ...               # Per-module subpackages (cli/, search/, database/, ...)
├── integration/          # Integration tests
│   ├── test_embed_idempotency.py
│   └── test_search_pipeline.py
└── e2e/                  # End-to-end tests (placeholder — only __init__.py)
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
            name="test-collection"
        )
        assert collection.name == "test-collection"
    
    def test_add_path(self):
        collection = Collection(id="test-id", name="test")
        collection.add_path("/path/to/docs")
        assert "/path/to/docs" in collection.paths


class TestCollectionManager:
    def test_create_collection(self):
        repo = MockCollectionRepository()
        manager = CollectionManager(repo)
        
        collection = manager.create_collection("my-collection")
        
        assert collection.name == "my-collection"
        assert repo.exists("my-collection")
    
    def test_create_duplicate_raises(self):
        repo = MockCollectionRepository()
        manager = CollectionManager(repo)
        
        manager.create_collection("my-collection")
        
        with pytest.raises(ValueError, match="already exists"):
            manager.create_collection("my-collection")
```

### Fixtures

```python
# tests/conftest.py
import pytest
from sif.core.collection import Collection


@pytest.fixture
def sample_collection():
    return Collection(
        id="test-id",
        name="test-collection",
        description="Test description",
        paths=["/path/to/docs"]
    )


@pytest.fixture
def mock_repository():
    from tests.unit.test_collection import MockCollectionRepository
    return MockCollectionRepository()
```

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage report
pytest --cov=sif --cov-report=html

# Run specific test
pytest tests/unit/test_collection.py::TestCollectionManager::test_create_collection

# Run a subset by directory
pytest tests/unit/
pytest tests/integration/
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

Enable debug logging:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

Or via environment variable:

```bash
export SIF_LOG_LEVEL=DEBUG
sif search search "query"
```

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

# Your code here
results = search_service.search(query)

profiler.disable()
stats = pstats.Stats(profiler)
stats.sort_stats('cumulative')
stats.print_stats(20)
```

## Database Development

### Schema Changes

1. Create migration in `sif/database/migrations.py`:

```python
def migrate_v2_to_v3(conn: sqlite3.Connection) -> None:
    """Add new column to collections table."""
    conn.execute("""
        ALTER TABLE collections
        ADD COLUMN new_field TEXT
    """)
```

2. Update schema version

3. Test migration on sample data

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

1. Create file in `src/sif/search/`:

```python
# src/sif/search/custom.py
from sif.search.strategy import SearchStrategy, SearchContext
from sif.models.search import SearchOptions, SearchResult

class CustomSearchStrategy(SearchStrategy):
    def search(
        self,
        context: SearchContext,
        options: SearchOptions,
    ) -> list[SearchResult]:
        # Implementation
        pass
    
    def search_batch(
        self,
        contexts: list[SearchContext],
        options: SearchOptions,
    ) -> list[list[SearchResult]]:
        pass
```

2. Add tests in `tests/unit/search/test_custom.py`

3. Register in search service

### New CLI Command

1. Create command in `src/sif/cli/commands/`:

```python
# src/sif/cli/commands/custom.py
import click

@click.command(name="custom")
@click.argument("input")
def custom_command(input: str) -> None:
    """Custom command description."""
    click.echo(f"Processing: {input}")
```

2. Register in `src/sif/cli/main.py`:

```python
from sif.cli.commands.custom import custom_command

cli.add_command(custom_command, name="custom")
```

3. Add tests and documentation

### New Model

1. Create Pydantic model in `src/sif/models/`:

```python
# src/sif/models/custom.py
from pydantic import BaseModel, Field

class CustomModel(BaseModel):
    name: str = Field(..., min_length=1)
    value: int = Field(0, ge=0)
```

2. Add corresponding domain entity if needed

3. Update database schema

## Release Process

### Version Bump

1. Update version in `src/sif/_version.py`

2. Update docs/changelog.md

3. Create git tag:

```bash
git tag -a v0.2.0 -m "Release version 0.2.0"
git push origin v0.2.0
```

### Build Package

```bash
# Install build tools
pip install build twine

# Build package
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

# Run with fresh database
rm test.db
pytest
```

**Type checking errors:**
```bash
# Bypass ty's cache and re-check from scratch
ty check --no-cache src/sif
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
| `make install-dev` | Install with development dependencies (`pip install -e ".[dev]"`) and pre-commit hooks |
| `make install-all` | Install with all optional dependencies (`pip install -e ".[dev,all]"`) and pre-commit hooks |
| `make dev-setup` | Alias for `make install-dev` |
| `make update-deps` | Upgrade pip, reinstall all dependencies, run `pre-commit autoupdate` |

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
| `make pre-commit` | Run pre-commit hooks on all files |

### Build and Maintenance

| Command | Description |
|---------|-------------|
| `make build` | Build the sdist and wheel (`python -m build`), then verify them with twine |
| `make clean` | Remove build artifacts, caches, and coverage output |
| `make clean-all` | `make clean` plus removal of `venv/` and `.venv/` |
| `make docs` | Placeholder — prints "Documentation build not yet configured" |
| `make docs-test` | Run the documentation validation tests (`pytest tests/test_docs.py -v --no-cov`) |
| `make docs-generate` | Regenerate `docs/cli-reference.md` and `docs/configuration.md` from source |
| `make all` | Run `lint`, `typecheck`, and `test` |
| `make ci` | Run all CI checks locally: `format-check`, `lint`, `typecheck`, `security`, `test` |
| `make dev-check` | Format, lint with auto-fix, then type check |
| `make info` | Print the Python version and installed tool versions |

The pre-commit targets (`make install-dev`, `make install-all`, `make pre-commit`, `make update-deps`) require a pre-commit configuration file. <!-- VERIFY: make pre-commit / pre-commit install reference .pre-commit-config.yaml, which is not in the repository -->

The `security` target requires `bandit`, and `make build` requires `build` and `twine`; none of these are included in the `[dev]` extras, so install them separately when needed.

## Branch Conventions

- The default branch is `main`: `origin/HEAD` points to `origin/main`, and pull requests are opened against it.
- A `dev` branch carries in-progress work before it lands on `main`.
- Name feature branches `feature/<short-description>` and bug fix branches `fix/<short-description>`, as shown in [Development Workflow](#development-workflow). No additional convention is formally documented.

## PR Process

- Push your branch and open the pull request against `main` on GitHub. There is no `.github/PULL_REQUEST_TEMPLATE.md`; follow the description template in [Contributing](contributing.md) (Description, Type of Change, Testing, Checklist).
- Before requesting review, the [Contributing](contributing.md) checklist expects: `pytest` passes, `ruff format .` applied, `ruff check .` clean, `ty check src/sif` passes, and documentation (including docs/changelog.md) updated.
- Commit messages follow Conventional Commits, as described in Commit Changes above.
- PR CI only validates documentation: the "Docs Validation" workflow (`.github/workflows/docs.yml`) runs `pytest tests/test_docs.py` and regenerates `docs/cli-reference.md` and `docs/configuration.md` whenever a PR touches `docs/**`, `README.md`, `src/sif/cli/**`, `src/sif/config/**`, the generation scripts, or `tests/test_docs.py` — it fails if the committed reference docs are stale. No workflow runs the full test suite or linters on PRs, so run `make ci` locally before pushing.
- Maintainers aim to review pull requests within a week; respond to comments and push follow-up commits to the same branch.

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

The "Docs Validation" workflow (`.github/workflows/docs.yml`) regenerates `docs/cli-reference.md` and `docs/configuration.md` on every PR that touches `docs/**`, `README.md`, `src/sif/cli/**`, `src/sif/config/**`, the generator scripts, or `tests/test_docs.py`, then fails on any diff (`git diff --exit-code`). After changing the CLI or settings, run `make docs-generate` and commit the regenerated docs together with the code change. The architecture diagram script is not wired into `make docs-generate` or CI — regenerate it manually when package-level dependencies change.

### Documentation Tests

`make docs-test` (`pytest tests/test_docs.py -v`) validates the code blocks in `README.md`, `docs/index.md`, `docs/cli-reference.md`, `docs/configuration.md`, `docs/quickstart.md`, `docs/mcp-server.md`, `docs/search-algorithms.md`, `docs/architecture.md`, and `docs/models.md`:

- JSON blocks must parse, and JSON output examples must contain the expected keys.
- Python blocks must be syntactically valid.
- Every `sif` command in shell blocks must exist in the live Click tree — removed or renamed commands fail the suite.
- Stale content is rejected: removed commands (for example `sif collection create`), outdated default model names, and bare `sif search <query>` (use `sif search search`, `sif search query`, or `sif search vsearch`).

This file, `testing.md`, and `contributing.md` are not in the validated set.

### Documentation Site

Docs are wired for MkDocs with the Material theme (`mkdocs.yml`, source directory `docs/`). When you add a page under `docs/`, also list it in the `nav` mapping in `mkdocs.yml` so it appears in the site navigation. There is no configured site build yet — `make docs` prints "Documentation build not yet configured" — and the MkDocs toolchain is not part of any dependency extras in `pyproject.toml`.

## Related Documentation

- [Contributing](contributing.md) - Contribution guidelines
- [Architecture](architecture.md) - System architecture
- [API Reference](api-reference.md) - Python API
