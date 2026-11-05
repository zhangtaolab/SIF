<!-- generated-by: gsd-doc-writer -->
# Testing

SIF's test suite is built on [pytest](https://docs.pytest.org/) with coverage collected by pytest-cov. Tests live in `tests/` and are organized into unit, integration, and e2e tiers. This guide covers how to run the suite, how the tiers are laid out, and how to write new tests using the shared fixtures and factories.

## Test framework and setup

The test toolchain is declared in the `dev` extras in `pyproject.toml`:

- `pytest>=7.0.0` — test framework
- `pytest-cov>=4.0.0` — coverage reporting

Install them together with the package:

```bash
pip install -e ".[dev]"
# or, which also installs the pre-commit hooks:
make install-dev
```

Pytest is configured in the `[tool.pytest.ini_options]` section of `pyproject.toml`:

| Option | Value | Meaning |
|--------|-------|---------|
| `testpaths` | `tests` | Default collection root |
| `python_files` | `test_*.py` | Test module naming convention |
| `python_classes` | `Test*` | Test class naming convention |
| `python_functions` | `test_*` | Test function naming convention |
| `addopts` | `--cov=src/sif --cov-report=term-missing --cov-report=html --cov-report=xml` | Coverage is measured on every run |

Because coverage flags are in `addopts`, they apply to every `pytest` invocation — including `make test-fast` (see below). Append `--no-cov` to any command to skip coverage.

**Async tests:** the MCP tests in `tests/unit/mcp/` use `@pytest.mark.asyncio` and require the `pytest-asyncio` plugin. The plugin is not currently listed in the `dev` extras, so if those tests fail with "async def functions are not natively supported", install it explicitly:

```bash
pip install pytest-asyncio
```

## Running tests

### Makefile targets

| Command | What it runs |
|---------|--------------|
| `make test` | Full suite with coverage: `pytest --cov=src/sif --cov-report=term-missing --cov-report=html --cov-report=xml` |
| `make test-verbose` | Full suite with verbose output: `pytest -vvs --tb=short --cov=src/sif --cov-report=term-missing` |
| `make test-fast` | Quiet run that stops at the first failure: `pytest -x -q` (coverage still applies via `addopts`) |
| `make docs-test` | Documentation validation only: `pytest tests/test_docs.py -v` |
| `make coverage` | Full suite with coverage, then prints the HTML report location (`htmlcov/index.html`) |

### Direct pytest invocations

```bash
# Full suite
pytest

# One tier
pytest tests/unit
pytest tests/integration

# One file
pytest tests/unit/search/test_bm25.py

# One test (file::Class::method)
pytest tests/unit/search/test_bm25.py::TestBM25Searcher::test_search_executes_fts_query

# One keyword expression
pytest tests/unit/cli -k "test_search"

# Skip coverage for a faster loop
pytest --no-cov
```

There is no watch-mode command configured. For a tight edit-test loop, combine `--no-cov` with a file or `-k` selector.

### Environment note: FORCE_COLOR

The CLI tests assert on plain-text output. If your shell sets `FORCE_COLOR` (common in some terminal wrappers and agent environments), Click/Rich emit ANSI color codes and those assertions fail spuriously. Setting `FORCE_COLOR=0` is not enough — the variable must be unset, with `NO_COLOR=1` as a belt-and-braces fallback:

```bash
env -u FORCE_COLOR NO_COLOR=1 pytest
```

## Test suite layout

```text
tests/
├── conftest.py              # Shared pytest fixtures (see below)
├── factories.py             # Test data factories
├── test_docs.py             # Validates code blocks in documentation
├── test_sif_complete.py     # End-to-end smoke tests over the installed package
├── unit/                    # 648 tests — module-level tests with mocks/temp databases
│   ├── cli/                 #   CLI commands (index, search, get, pull, bench, ...)
│   ├── config/              #   Settings loading and validation
│   ├── database/            #   SchemaManager and repository tests (sif.database.*)
│   ├── db/                  #   DatabaseConnection / ConnectionPool tests
│   ├── embedding/           #   Embedder implementations, factory, manager
│   ├── indexing/            #   Indexer and file watcher
│   ├── inference/           #   Embedder, query expander, reranker
│   ├── mcp/                 #   MCP backend and transports (async tests)
│   ├── search/              #   BM25, vector, hybrid, RRF, rerank, snippets
│   ├── test_collection.py   #   CollectionManager
│   └── test_search.py       #   Search strategy and response models
├── integration/             # 18 tests — cross-component pipelines
│   ├── test_embed_idempotency.py
│   └── test_search_pipeline.py
└── e2e/                     # Reserved tier; currently empty
```

- **unit/** tests a single module in isolation, using mocks (`MagicMock`) or the temporary-database fixtures.
- **integration/** exercises multiple layers together, such as the CLI embed command against a real temporary database, or the full search pipeline (FTS5 + vector + RRF fusion).
- **e2e/** is a placeholder with no tests yet; add true end-to-end scenarios here.
- **test_docs.py** extracts fenced code blocks from a hardcoded `DOCS_FILES` list (README plus the main docs pages) and checks that the documented commands actually work and that JSON examples match the real output schemas.
- **test_sif_complete.py** is a smoke suite that imports the core modules and runs basic database/collection/search operations against temp directories.

## Writing new tests

Follow the naming conventions enforced by `pyproject.toml`: files named `test_*.py`, classes prefixed `Test`, functions prefixed `test_`. Place module-level tests under `tests/unit/<area>/` and cross-layer tests under `tests/integration/`. Ruff applies relaxed rules to `tests/**` (docstrings, print, magic values, and private-member access are allowed — see the `per-file-ignores` in `pyproject.toml`).

### Shared fixtures (tests/conftest.py)

| Fixture | Purpose |
|---------|---------|
| `temp_dir`, `temp_db_path` | Temporary directory / database file path |
| `db_connection` | A `DatabaseConnection` on a temp path |
| `temp_db` | A `DatabaseConnection` with collections/documents/chunks/contexts tables created |
| `sample_markdown_file`, `sample_markdown_content` | A realistic Markdown file with frontmatter |
| `sample_collection(s)`, `sample_document(s)`, `sample_chunk(s)`, `sample_context` | Prebuilt domain entities |
| `sample_search_options`, `sample_search_result(s)` | Search options and results |
| `mock_embedder` | Deterministic 384-dim mock embedding model |
| `mock_repository`, `mock_search_repository`, `mock_embedding_manager` | Mocked persistence and search collaborators |
| `docs_test_db`, `docs_runner` | Temp database seeded with a docs collection, and a Click `CliRunner` pointed at it via `SIF_DB_PATH` |

Helper functions `create_test_document()` and `create_test_collection()` are also available for one-off entities inside a test body.

### Test data factories (tests/factories.py)

For entities with varying shapes, prefer the factories over the fixed `sample_*` fixtures:

- `CollectionFactory`, `DocumentFactory` (supports `with_chunks=True`), `DocumentChunkFactory`, `DocumentMetadataFactory`, `ContextFactory` — each has `.create(**overrides)` and `.create_batch(n, **overrides)`
- `SearchOptionsFactory` — plus `.bm25()`, `.vector()`, `.hybrid()` presets
- `SearchResultFactory` — `.create_batch(n)` yields decreasing scores
- `SAMPLE_MARKDOWN_CONTENTS`, `SAMPLE_SEARCH_QUERIES`, `get_sample_embedding(dim)` — shared corpora and deterministic vectors

Example:

```python
from tests.factories import DocumentFactory, SearchOptionsFactory

def test_indexer_handles_multi_chunk_documents(temp_db):
    doc = DocumentFactory.create(with_chunks=True, chunk_count=5)
    options = SearchOptionsFactory.hybrid(limit=20)
    ...
```

### Async tests

Mark coroutine tests with `@pytest.mark.asyncio` (see `tests/unit/mcp/test_backend.py` for examples) and remember the `pytest-asyncio` plugin requirement noted above.

### Updating documentation tests

`tests/test_docs.py` validates only the files listed in its `DOCS_FILES` constant. If you add a new docs page containing runnable code blocks, add its path to `DOCS_FILES` so its examples are validated too. Commands that must not execute (server daemons, installs, network pulls) are excluded via `SKIP_COMMAND_PATTERNS` in the same file.

## Coverage

Coverage is measured over `src/sif` on every run (via `addopts`) and reported three ways:

- `term-missing` — per-file missing lines in the console
- `htmlcov/index.html` — browsable HTML report
- `coverage.xml` — machine-readable report

No coverage threshold is configured — the suite reports coverage but does not fail below a minimum. Artifacts are cleaned by `make clean` (removes `htmlcov/`, `.coverage`, `coverage.xml`).

## CI integration

The only test workflow is `.github/workflows/docs.yml` ("Docs Validation"). It does **not** run the full pytest suite — the full suite is expected to run locally (or via `make test`) before pushing.

The workflow triggers on:

- pull requests touching `docs/**`, `README.md`, `src/sif/cli/**`, `src/sif/config/**`, the reference-generation scripts, or `tests/test_docs.py`
- pushes to `main`

The `docs-test` job (ubuntu-latest, Python 3.11) then:

1. Installs the package with `pip install -e ".[dev]"`
2. Runs `pytest tests/test_docs.py -v`
3. Regenerates the CLI and configuration reference docs (`scripts/generate_cli_ref.py`, `scripts/generate_config_ref.py`) and fails on any diff (`git diff --exit-code docs/cli-reference.md docs/configuration.md`), ensuring the reference docs stay in sync with the code

To reproduce all local checks in one shot, use `make ci` (format check, lint, typecheck, security scan, and the full test suite). See [development.md](development.md) for the broader development workflow.
