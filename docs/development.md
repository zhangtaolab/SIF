# Development Guide

Guide for contributing to DocSift development.

## Setup

### Prerequisites

- Python 3.9+
- Git
- Virtual environment tool (venv, conda, or pyenv)

### Clone Repository

```bash
git clone https://github.com/docsift/docsift.git
cd docsift
```

### Create Virtual Environment

```bash
# Using venv
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Using conda
conda create -n docsift python=3.11
conda activate docsift
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
docsift --version

# Run tests
pytest

# Check code style
ruff check .
```

## Project Structure

```
docsift/
├── src/docsift/           # Source code
│   ├── core/              # Domain entities
│   ├── models/            # Pydantic models
│   ├── database/          # Data access
│   ├── search/            # Search algorithms
│   ├── indexing/          # Document indexing
│   ├── embedding/         # Embedding models
│   ├── mcp_server/        # MCP server
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
pytest --cov=docsift

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
mypy src/docsift
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
target-version = "py39"
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
│   ├── test_document.py
│   └── test_search.py
├── integration/          # Integration tests
│   ├── test_indexing.py
│   └── test_search.py
└── e2e/                  # End-to-end tests
    └── test_cli.py
```

### Writing Tests

```python
# tests/unit/test_collection.py
import pytest
from docsift.core.collection import Collection, CollectionManager
from tests.mocks import MockCollectionRepository


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
from docsift.core.collection import Collection


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
    from tests.mocks import MockCollectionRepository
    return MockCollectionRepository()
```

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage report
pytest --cov=docsift --cov-report=html

# Run specific test
pytest tests/unit/test_collection.py::TestCollectionManager::test_create_collection

# Run with markers
pytest -m unit
pytest -m integration
pytest -m "not slow"
```

### Test Markers

```python
import pytest

@pytest.mark.unit
def test_simple_function():
    pass

@pytest.mark.integration
def test_database_interaction():
    pass

@pytest.mark.slow
def test_large_collection():
    pass

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
export DOCSIFT_LOG_LEVEL=DEBUG
docsift search "query"
```

### IDE Setup

#### VS Code

`.vscode/launch.json`:

```json
{
  "version": "0.2.0",
  "configurations": [
    {
      "name": "Python: DocSift CLI",
      "type": "python",
      "request": "launch",
      "module": "docsift.cli.main",
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
3. Set script path to `src/docsift/cli/main.py`
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

1. Create migration in `docsift/database/migrations.py`:

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
export DOCSIFT_DB_PATH=./test.db

# Index test data
docsift collection create test
docsift index add test ./test-data

# Run queries
docsift search "test query"
```

## Adding New Features

### New Search Strategy

1. Create file in `src/docsift/search/`:

```python
# src/docsift/search/custom.py
from docsift.search.strategy import SearchStrategy, SearchContext
from docsift.models.search import SearchOptions, SearchResult

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

1. Create command in `src/docsift/cli/commands/`:

```python
# src/docsift/cli/commands/custom.py
import click

@click.command(name="custom")
@click.argument("input")
def custom_command(input: str) -> None:
    """Custom command description."""
    click.echo(f"Processing: {input}")
```

2. Register in `src/docsift/cli/main.py`:

```python
from docsift.cli.commands.custom import custom_command

cli.add_command(custom_command, name="custom")
```

3. Add tests and documentation

### New Model

1. Create Pydantic model in `src/docsift/models/`:

```python
# src/docsift/models/custom.py
from pydantic import BaseModel, Field

class CustomModel(BaseModel):
    name: str = Field(..., min_length=1)
    value: int = Field(0, ge=0)
```

2. Add corresponding domain entity if needed

3. Update database schema

## Release Process

### Version Bump

1. Update version in `src/docsift/_version.py`

2. Update CHANGELOG.md

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
# Update mypy cache
mypy --clear-cache src/docsift
```

## Resources

- [Python Documentation](https://docs.python.org/3/)
- [Click Documentation](https://click.palletsprojects.com/)
- [Pydantic Documentation](https://docs.pydantic.dev/)
- [Pytest Documentation](https://docs.pytest.org/)
- [Ruff Documentation](https://docs.astral.sh/ruff/)

## Getting Help

- GitHub Issues: [github.com/docsift/docsift/issues](https://github.com/docsift/docsift/issues)
- Discussions: [github.com/docsift/docsift/discussions](https://github.com/docsift/docsift/discussions)

## Related Documentation

- [Contributing](contributing.md) - Contribution guidelines
- [Architecture](architecture.md) - System architecture
- [API Reference](api-reference.md) - Python API
