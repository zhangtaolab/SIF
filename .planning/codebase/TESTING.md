# Testing Patterns

**Analysis Date:** 2026-04-14

## Test Framework

**Runner:**
- **pytest** (>=7.0.0)
- Config: `pyproject.toml` under `[tool.pytest.ini_options]`

**Coverage:**
- **pytest-cov** (>=4.0.0)
- Default addopts include:
  ```toml
  addopts = "--cov=src/docsift --cov-report=term-missing --cov-report=html --cov-report=xml"
  ```

**Run Commands:**
```bash
pytest                    # Run all tests with coverage
pytest -x                # Stop on first failure
pytest tests/unit        # Run unit tests only
pytest tests/integration # Run integration tests only
pytest tests/e2e         # Run end-to-end tests only
```

## Test File Organization

**Location:**
- Tests live in a top-level `tests/` directory (not co-located with source)
- Source is in `src/docsift/`

**Structure:**
```
tests/
├── conftest.py              # Shared fixtures
├── factories.py             # Test data factories
├── __init__.py
├── test_docsift_complete.py # Cross-cutting complete tests
├── unit/
│   ├── __init__.py
│   ├── test_collection.py
│   ├── test_search.py
│   ├── cli/
│   │   ├── test_search_commands.py
│   │   ├── test_collection_commands.py
│   │   └── test_index_commands.py
│   ├── db/
│   │   ├── test_database.py
│   │   └── test_repositories.py
│   ├── indexing/
│   │   ├── test_parser.py
│   │   ├── test_chunker.py
│   │   └── test_indexer.py
│   ├── inference/
│   │   ├── test_embedder.py
│   │   ├── test_query_expander.py
│   │   └── test_reranker.py
│   └── search/
│       ├── test_bm25.py
│       ├── test_vector.py
│       ├── test_hybrid.py
│       └── test_rrf.py
├── integration/
│   ├── test_index_and_search.py
│   └── test_search_pipeline.py
└── e2e/
    └── test_cli_workflow.py
```

**Naming:**
- Test files: `test_*.py`
- Test classes: `Test*` (e.g., `TestBM25SearchStrategy`)
- Test functions: `test_*` (e.g., `test_search_calls_repository_search_fts`)

## Test Structure

**Suite Organization:**
```python
class TestBM25SearchStrategy:
    """Tests for BM25SearchStrategy class."""

    def test_search_calls_repository_search_fts(self, mock_search_repository: MagicMock):
        """Test that search calls repository search_fts method."""
        # Arrange
        strategy = BM25SearchStrategy(mock_search_repository)
        context = SearchContext(query="test query")
        options = SearchOptions(limit=10)

        # Act
        results = strategy.search(context, options)

        # Assert
        mock_search_repository.search_fts.assert_called_once_with(
            query="test query",
            collection_ids=None,
            limit=10,
            offset=0,
        )
```

**Patterns:**
- Arrange-Act-Assert comments are common
- Docstrings describe the scenario: "Arrange: ..., Act: ..., Assert: ..."
- Type annotations on test fixtures and test methods

## Mocking

**Framework:** `unittest.mock` (standard library)

**Patterns:**
```python
from unittest.mock import MagicMock, create_autospec, patch

@pytest.fixture
def mock_search_repository() -> MagicMock:
    mock = MagicMock()
    mock.search_fts.return_value = [
        ("doc-1", 0.95),
        ("doc-2", 0.87),
    ]
    return mock
```

**Autospec for interfaces:**
```python
mock = create_autospec(AbstractCollectionRepository, instance=True)
```

**What to Mock:**
- External repositories and databases
- Embedding models (`mock_embedder`, `mock_embedding_manager`)
- Search repositories (`mock_search_repository`)

**What NOT to Mock (in integration tests):**
- Real `MarkdownParser`, `Chunker` are instantiated directly
- Temporary directories and files are real (`tempfile.TemporaryDirectory`)

## Fixtures and Factories

**Shared fixtures:** `tests/conftest.py`

**Fixture categories:**
- Path fixtures: `temp_dir`, `sample_markdown_file`
- Database fixtures: `temp_db_path`, `db_connection`, `temp_db`
- Entity fixtures: `sample_collection`, `sample_document`, `sample_chunk`, `sample_context`
- Search fixtures: `sample_search_options`, `sample_search_results`
- Mock fixtures: `mock_embedder`, `mock_repository`, `mock_search_repository`, `mock_embedding_manager`

**Factory classes:** `tests/factories.py`

```python
class CollectionFactory:
    _counter = 0

    @classmethod
    def create(cls, id: str | None = None, ...) -> Collection:
        cls._counter += 1
        return Collection(
            id=id or str(uuid.uuid4()),
            name=name or f"test-collection-{cls._counter}",
            ...
        )

    @classmethod
    def create_batch(cls, count: int, **kwargs) -> list[Collection]:
        return [cls.create(**kwargs) for _ in range(count)]
```

Factories exist for: `CollectionFactory`, `DocumentFactory`, `DocumentChunkFactory`, `DocumentMetadataFactory`, `ContextFactory`, `SearchOptionsFactory`, `SearchResultFactory`.

## Coverage

**Requirements:** Enforced via `pytest-cov` with HTML, XML, and terminal-missing reports

**View Coverage:**
```bash
pytest              # Generates htmlcov/ and coverage.xml automatically
open htmlcov/index.html
```

## Test Types

**Unit Tests:**
- Located in `tests/unit/`
- Heavy use of mocks and fixtures
- Test individual classes/functions in isolation
- Example: `tests/unit/search/test_bm25.py` mocks the repository and tests `BM25SearchStrategy`

**Integration Tests:**
- Located in `tests/integration/`
- Combine real parsers, chunkers, and strategies with mocked repositories
- Example: `tests/integration/test_index_and_search.py` tests `MarkdownParser` + `Chunker` together

**E2E Tests:**
- Located in `tests/e2e/`
- Use `click.testing.CliRunner` to invoke actual CLI commands
- Test complete workflows: create collection -> add path -> search -> delete
- Example: `tests/e2e/test_cli_workflow.py`

## Common Patterns

**Async Testing:**
- `event_loop` fixture provided in `conftest.py` for async tests:
  ```python
  @pytest.fixture
  def event_loop():
      import asyncio
      loop = asyncio.get_event_loop_policy().new_event_loop()
      yield loop
      loop.close()
  ```

**CLI Testing:**
```python
from click.testing import CliRunner

runner = CliRunner()
result = runner.invoke(cli, ["collection", "list"])
assert result.exit_code == 0
```

**Error Testing:**
```python
with pytest.raises(ValueError, match="Unknown chunking strategy"):
    chunker.chunk("Some text")
```

**Database Testing:**
- Use `tempfile.TemporaryDirectory` for isolated SQLite databases
- Schema created inline in fixtures or via `DatabaseConnection`

**In-Memory Implementations:**
- Some unit tests include lightweight in-memory repository implementations inside the test file (e.g., `InMemoryCollectionRepository` in `test_repositories.py`) to test behavior without a real database.

---

*Testing analysis: 2026-04-14*
