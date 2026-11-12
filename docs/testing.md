<!-- generated-by: gsd-doc-writer -->
# Testing

SIF's test suite is built on [pytest](https://docs.pytest.org/) with coverage collected by pytest-cov. Tests live in `tests/` and are organized into unit, integration, and e2e tiers, plus three root-level suites for documentation validation, installed-package smoke tests, and version-identity regression tests — 1610 tests in total (1609 passing and 1 opt-in skip), with a full run taking roughly a minute and a half. This guide covers how to run the suite, how the tiers are laid out, and how to write new tests using the shared fixtures and factories.

## Test framework and setup

The test toolchain is declared in the `dev` extras in `pyproject.toml`:

- `pytest>=7.0.0` — test framework
- `pytest-cov>=4.0.0` — coverage reporting
- `pytest-asyncio>=0.23.0` — plugin for the async MCP tests

Install them together with the package:

```bash
pip install -e ".[dev]"
```

`make install-dev` performs the same install and then runs `pre-commit install` to install the repository's Git hooks.

<!-- VERIFY: make install-dev ends with `pre-commit install`, but no .pre-commit-config.yaml is present in the repository -->

Pytest is configured in the `[tool.pytest.ini_options]` section of `pyproject.toml`:

| Option | Value | Meaning |
|--------|-------|---------|
| `testpaths` | `tests` | Default collection root |
| `python_files` | `test_*.py` | Test module naming convention |
| `python_classes` | `Test*` | Test class naming convention |
| `python_functions` | `test_*` | Test function naming convention |
| `addopts` | `--cov=src/sif --cov-report=term-missing --cov-report=html --cov-report=xml` | Coverage is measured on every run |

Because coverage flags are in `addopts`, they apply to every `pytest` invocation — including `make test-fast` (see below). Append `--no-cov` to any command to skip coverage.

**Async tests:** the MCP tests in `tests/unit/mcp/` use `@pytest.mark.asyncio` and require the `pytest-asyncio` plugin, which is included in the `dev` extras (`pip install -e ".[dev]"` covers it).

## Running tests

### Makefile targets

| Command | What it runs |
|---------|--------------|
| `make test` | Full suite with coverage: `pytest --cov=src/sif --cov-report=term-missing --cov-report=html --cov-report=xml` |
| `make test-verbose` | Full suite with verbose output: `pytest -vvs --tb=short --cov=src/sif --cov-report=term-missing` |
| `make test-fast` | Quiet run that stops at the first failure: `pytest -x -q` (coverage still applies via `addopts`, despite the target's help text) |
| `make docs-test` | Documentation validation only: `pytest tests/test_docs.py -v --no-cov` (the `--no-cov` skips the global coverage `addopts` — a docs-only subset would otherwise fall under the 90% `fail_under` gate) |
| `make docs-generate` | Regenerates the CLI and configuration reference docs (`scripts/generate_cli_ref.py`, `scripts/generate_config_ref.py`) |
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

### Color environment is hermetic

The CLI tests assert on plain-text output, so the suite neutralizes color-forcing environment variables itself. `tests/conftest.py` removes `FORCE_COLOR`, `CLICOLOR_FORCE`, `NO_COLOR`, `PY_COLORS`, and `TTY_COMPATIBLE` at import time — before any `sif.cli` module constructs its module-level Rich `Console` objects and caches a color system — and the autouse `_hermetic_color_env` fixture deletes them again before every test. `tests/unit/cli/test_color_hermeticity.py` pins both properties: no forcing variable is visible at test start, and forcing color mid-test still yields plain output from the real CLI. You do not need to unset anything in your shell for a green run.

## Test suite layout

```text
tests/
├── conftest.py              # Shared pytest fixtures + global color-env scrub
├── factories.py             # Test data factories
├── test_docs.py             # Validates code blocks in documentation (13 tests)
├── test_sif_complete.py     # End-to-end smoke tests over the installed package (9 tests)
├── test_version_identity.py # Pins the single-sourced release version (4 tests)
├── unit/                    # 1538 tests — module-level tests with mocks/temp databases
│   ├── cli/                 #   CLI commands, error conventions, index locking, color hermeticity (434)
│   ├── config/              #   Settings loading and validation (34)
│   ├── core/                #   Core domain entities (Collection, Context) (25)
│   ├── database/            #   Schema, migrations, repositories, locking, query log (90)
│   ├── db/                  #   DatabaseConnection / ConnectionPool tests (58)
│   ├── embedding/           #   Embedder implementations, cache, factory, manager (100)
│   ├── indexing/            #   Chunker, indexer, parser, scanner, watcher, drift, incremental (126)
│   ├── inference/           #   Embedder, query expander, reranker (90)
│   ├── mcp/                 #   MCP backend, server, and transports (120, async)
│   ├── models/              #   Model download helpers (16)
│   ├── search/              #   BM25, vector, hybrid, RRF, rerank, snippets, staleness, suggest, benchmark sweep (334)
│   ├── utils/               #   Logging, paths, progress, daemon/service, text helpers (88)
│   ├── test_collection.py   #   CollectionManager
│   └── test_search.py       #   Search strategy and response models
├── integration/             # 46 tests — cross-component and real-subprocess pipelines
│   ├── test_concurrency.py            # WAL reader/writer concurrency proofs
│   ├── test_embed_idempotency.py      # Repeated `sif index embed` runs stay idempotent
│   ├── test_incremental_equivalence.py # Golden add/modify/delete equivalence proof
│   ├── test_mcp_watch_e2e.py          # Real stdio MCP server with embedded watcher
│   ├── test_search_pipeline.py        # FTS5 + vector + RRF fusion end to end
│   ├── test_service_live_launchd.py   # Opt-in live launchd proof (skipped by default)
│   ├── test_two_writer_subprocess.py  # Two-writer locking across subprocesses
│   ├── test_watch_daemon_e2e.py       # Detached `sif watch` daemon lifecycle
│   └── test_watch_e2e.py              # Foreground `sif watch` indexing battery
├── fixtures/bench/          # Committed synthetic benchmark pack (150 docs, 56 graded queries)
├── support/bench.py         # ConceptEmbedder + build_bench_db helpers for the bench tests
└── e2e/                     # Reserved tier; currently empty
```

- **unit/** tests a single module in isolation, using mocks (`MagicMock`) or the temporary-database fixtures. `database/` mirrors the `sif.database` package (schema, migrations, repositories, locking), while `db/` covers connection management (`DatabaseConnection`, `ConnectionPool`).
- **integration/** exercises multiple layers together: CLI embed idempotency and incremental-index equivalence against real temporary databases, WAL concurrency and two-writer locking across processes, the full search pipeline (FTS5 + vector + RRF fusion), and real-subprocess batteries for foreground `sif watch`, the detached watch daemon, and the MCP server with its embedded watcher. `test_service_live_launchd.py` is skipped unless `SIF_TEST_LIVE_LAUNCHD=1` is set on macOS with `launchctl` on `PATH` — it is the suite's one default skip.
- **e2e/** is a placeholder with no tests yet; add true end-to-end scenarios here.
- **test_docs.py** extracts fenced code blocks from a hardcoded `DOCS_FILES` list (README.md plus `docs/index.md`, `cli-reference.md`, `configuration.md`, `quickstart.md`, `mcp-server.md`, `search-algorithms.md`, `benchmarking.md`, `architecture.md`, and `models.md`) and checks that the documented `sif` commands exist, Python and SQL blocks are valid, and JSON examples match the real output schemas.
- **test_sif_complete.py** is a smoke suite that imports the core modules and runs basic database/collection/search operations against temp directories.
- **test_version_identity.py** pins the release version to a single literal in `src/sif/_version.py`: `pyproject.toml` takes its version dynamically from that module, all runtime surfaces agree, no other module assigns `__version__`, and `sif --version` prints the package version.
- **tests/fixtures/bench/** is the committed synthetic benchmark pack for `sif bench` — 150 generated Markdown documents (keyword, synonym, multilingual, and rival categories) plus 56 graded queries. `tests/support/bench.py` provides `ConceptEmbedder` (a deterministic 32-dimension token-bag embedder that satisfies the `Embedder` protocol without downloading a model) and `build_bench_db()` (an in-memory SchemaManager index with FTS triggers and a `vec0` table built from the corpus). The pack is regenerated with `python scripts/generate_bench_fixture.py`; `python scripts/generate_bench_fixture.py --check` is the drift gate. It is synthetic by design — never commit real personal-knowledge-base content to it.

## Writing new tests

Follow the naming conventions enforced by `pyproject.toml`: files named `test_*.py`, classes prefixed `Test`, functions prefixed `test_`. Place module-level tests under `tests/unit/<area>/` and cross-layer tests under `tests/integration/`. Ruff applies relaxed rules to `tests/**` (docstrings, print, magic values, private-member access, imports outside the top level, and long argument lists are allowed — see the `per-file-ignores` in `pyproject.toml`).

### Shared fixtures (tests/conftest.py)

| Fixture | Purpose |
|---------|---------|
| `_hermetic_color_env` | Autouse fixture that strips color-forcing environment variables before every test |
| `temp_dir`, `temp_db_path` | Temporary directory / database file path |
| `db_connection` | A `DatabaseConnection` on a temp path |
| `temp_db` | A `DatabaseConnection` with collections/documents/chunks/contexts tables created |
| `sample_markdown_file`, `sample_markdown_content` | A realistic Markdown file with frontmatter (and its raw contents) |
| `sample_collection_id`, `sample_document_id`, `sample_chunk_id` | Prebuilt entity IDs |
| `sample_collection(s)`, `sample_document(s)`, `sample_chunk(s)`, `sample_context`, `sample_document_metadata` | Prebuilt domain entities |
| `sample_search_options`, `sample_search_result(s)` | Search options and results |
| `mock_embedder` | Deterministic 384-dim mock embedding model |
| `mock_repository`, `mock_search_repository`, `mock_embedding_manager` | Mocked persistence and search collaborators |
| `event_loop` | Shared event loop for the async MCP tests |
| `docs_test_db`, `docs_runner` | Temp database seeded with a docs collection, and a Click `CliRunner` pointed at it via `SIF_DB_PATH` |

Helper functions `create_test_document()` and `create_test_collection()` are also available for one-off entities inside a test body.

### Test data factories (tests/factories.py)

For entities with varying shapes, prefer the factories over the fixed `sample_*` fixtures:

- `CollectionFactory`, `DocumentFactory` (supports `with_chunks=True`), `DocumentChunkFactory`, `DocumentMetadataFactory`, `ContextFactory` — each has `.create(**overrides)` and `.create_batch(n, **overrides)`
- `SearchOptionsFactory` — plus `.bm25()`, `.vector()`, `.hybrid()` presets
- `SearchResultFactory` — `.create_batch(n)` yields decreasing scores
- `SAMPLE_MARKDOWN_CONTENTS`, `SAMPLE_SEARCH_QUERIES`, `get_sample_embedding(dim)`, `get_sample_embeddings(count, dim)` — shared corpora and deterministic vectors

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

### Benchmark fixture helpers

Tests that need the benchmark corpus without a real embedding model can use `tests/support/bench.py`:

- `ConceptEmbedder` — token-bag embedder with reproducible L2-normalized vectors; similarity is driven purely by shared tokens
- `build_bench_db(corpus_root, embedder)` — builds a real in-memory schema (FTS triggers plus `vec0` embeddings) from the committed corpus, with fixed document ids (`doc-000` style) and path-keyed relevance; it skips the test when `sqlite-vec` is unavailable
- `load_fixture_queries(path)` — loads `queries.json` from the pack

The pack lives in `tests/fixtures/bench/` and its structure and tuning/held-out contract are documented in `tests/fixtures/bench/README.md`.

### Updating documentation tests

`tests/test_docs.py` validates only the files listed in its `DOCS_FILES` constant. If you add a new docs page containing runnable code blocks, add its path to `DOCS_FILES` so its examples are validated too. Commands that must not execute are excluded via `SKIP_COMMAND_PATTERNS` in the same file — currently `mcp http`, `mcp daemon`, `mcp stdio`, `pull `, `index embed`, `pip install`, `git clone`, `git checkout`, `pre-commit install`, and `bench `. The module's 13 tests also guard against removed command names (`sif collection create`, `sif mcp start`, and others), stale default model names, bare `sif search <query>` usage, positional arguments on option-only commands, phantom environment variables in `configuration.md`, and drift between `cli-reference.md` and the live Click command tree.

## Coverage

Coverage is measured over `src/sif` on every run (via `addopts`) and reported three ways:

- `term-missing` — per-file missing lines in the console
- `htmlcov/index.html` — browsable HTML report
- `coverage.xml` — machine-readable report

A minimum threshold **is** enforced: `[tool.coverage.report]` in `pyproject.toml` sets `fail_under = 90`, so any run whose total coverage falls below 90% fails with `Required test coverage of 90.0% not reached`. Note that this applies to partial runs too — running a single file or tier measures only that subset against the same 90% gate, so use `--no-cov` for focused work. At the time of writing, the full suite reports 95.25% coverage (7513 statements, 357 missed) with 1609 passed and 1 skipped.

Artifacts are cleaned by `make clean` (removes `htmlcov/`, `.coverage`, `coverage.xml`).

## CI integration

The only test workflow is `.github/workflows/docs.yml` ("Docs Validation"). It does **not** run the full pytest suite — the full suite is expected to run locally (or via `make test`) before pushing.

The workflow triggers on:

- pull requests touching `docs/**`, `README.md`, `src/sif/cli/**`, `src/sif/config/**`, `scripts/generate_cli_ref.py`, `scripts/generate_config_ref.py`, or `tests/test_docs.py`
- pushes to `main`

The `docs-test` job (ubuntu-latest, Python 3.11) then:

1. Installs the package with `pip install -e ".[dev]"`
2. Runs `pytest tests/test_docs.py -v --no-cov`
3. Regenerates the CLI and configuration reference docs (`scripts/generate_cli_ref.py`, `scripts/generate_config_ref.py`) and fails on any diff (`git diff --exit-code docs/cli-reference.md docs/configuration.md`), ensuring the reference docs stay in sync with the code

To reproduce all local checks in one shot, use `make ci` (format check, lint, typecheck, security scan, and the full test suite). The security step runs `bandit`, which is not declared in the `dev` extras, so install it separately.

<!-- VERIFY: make ci's security step requires bandit, which is not declared in the dev extras in pyproject.toml -->

See [development.md](development.md) for the broader development workflow.
