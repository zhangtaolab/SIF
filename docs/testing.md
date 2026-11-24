<!-- generated-by: gsd-doc-writer -->
# Testing

SIF's test suite is built on [pytest](https://docs.pytest.org/) with coverage collected by pytest-cov. Tests live in `tests/` and are organized into unit, integration, and e2e tiers, plus seven root-level regression suites for documentation validation, CI workflow and packaging state, repository hygiene, release metadata, module smoke checks, version identity, and the Windows degradation smoke matchers — 3,234 tests collected in total. The most recent full run (macOS, 2026-11-18) reports **3,233 passed and 1 skipped at 95.03% coverage**, and the Linux run reports **3,232 passed and 2 skipped at 95.04% coverage** (the extra skip is environment- or platform-gated). This guide covers how to run the suite, how the tiers are laid out, and how to write new tests using the shared fixtures and support helpers.

## Test framework and setup

The test toolchain is declared in the `dev` extras in `pyproject.toml`:

- `pytest>=7.0.0` — test framework
- `pytest-cov>=4.0.0` — coverage reporting
- `pytest-asyncio>=0.23.0` — plugin for the async MCP tests

Install them together with the package:

```bash
pip install -e ".[dev]"
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
| `make windows-smoke` | On-demand Windows degradation smoke via `hc exec` on the `hc` yoga Windows host: the target prints HEAD and status, installs Python 3.12 (`YOGA_PYTHON`), syncs the frozen dev environment, then runs `scripts/windows_smoke.py`, which refuses a dirty tree and refuses to run on a non-Windows host. It is not part of the local or CI suite; `tests/test_windows_smoke_script.py` unit-tests the script's matchers. |

### Direct pytest invocations

```bash
# Full suite
pytest

# Refresh the suite size quoted in this guide
pytest --collect-only -q

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

The CLI tests assert on plain-text output, so the suite neutralizes color-forcing environment variables itself. `tests/conftest.py` removes `FORCE_COLOR`, `CLICOLOR_FORCE`, `NO_COLOR`, `PY_COLORS`, and `TTY_COMPATIBLE` at import time — before any `sif.cli` module constructs its module-level Rich `Console` objects and caches a color system — and the autouse `_hermetic_color_env` fixture deletes them again before every test. `tests/unit/cli/test_color_hermeticity.py` pins both properties: no forcing variable is visible at test start, and forcing color mid-test still yields plain output from the real CLI. You do not need to unset anything in your shell for a green run. CI reinforces this by invoking pytest as `env -u FORCE_COLOR NO_COLOR=1 uv run --frozen pytest`.

## Test suite layout

```text
tests/
├── conftest.py                        # Shared pytest fixtures + autouse hermeticity fixtures
├── test_ci_workflows.py               # 18 tests — uv.lock/pyproject/workflow regression guards
├── test_docs.py                       # 20 tests — validates code blocks in documentation
├── test_hygiene.py                    # 15 tests — dead-layer, tracked-junk, and phantom-guidance guards
├── test_release_metadata.py           # 13 tests — version, changelog, and publish-workflow pins
├── test_sif_complete.py               #  9 tests — per-module smoke checks importing source modules directly
├── test_version_identity.py           #  4 tests — pins the single-sourced release version
├── test_windows_smoke_script.py       #  8 tests — pure-function battery for the Windows smoke matchers
├── unit/                              # 3,058 tests — module-level tests with mocks/temp databases
│   ├── cli/                           #   688 — commands, error boundary, index locking, color hermeticity, eval/bench
│   ├── config/                        #    39 — Settings loading and validation
│   ├── core/                          #   138 — domain entities and filter types
│   ├── database/                      #   206 — schema, repositories, locking, maintenance, query log, metadata kv
│   ├── db/                            #    58 — DatabaseConnection and repository tests
│   ├── embedding/                     #   206 — embedder implementations, cache, factory, identity, manager
│   ├── indexing/                      #   214 — chunker, parser, scanner, watcher, drift, incremental, embed writer
│   ├── inference/                     #    92 — embedder, query expander, reranker
│   ├── mcp/                           #   306 — MCP app, backend, tools, transports, daemon, plugin, wire transcripts
│   ├── models/                        #    52 — model download helpers
│   ├── scripts/                       #   165 — dry-run runbooks for eval, chunk sweep, and breadcrumb sweep
│   ├── search/                        #   785 — BM25, vector, hybrid, RRF, rerank, snippets, filters, bench/eval verdicts
│   ├── utils/                         #    97 — logging, paths, progress, daemon/service, text helpers
│   └── test_collection.py             #    12 — CollectionManager
├── integration/                       # 89 tests — cross-component and real-subprocess pipelines
│   ├── test_concurrency.py            #    4 — WAL reader/writer and busy-handler proofs
│   ├── test_embed_idempotency.py      #   15 — repeated `sif index embed` runs stay idempotent
│   ├── test_incremental_equivalence.py #   4 — golden add/modify/delete equivalence proof
│   ├── test_maintenance.py            #    2 — vacuum/backup against a live database
│   ├── test_mcp_watch_e2e.py          #    4 — real stdio MCP server with embedded watcher
│   ├── test_metadata_filtering.py     #   23 — metadata-filter pipeline on a real schema
│   ├── test_search_correctness.py     #   11 — deterministic pagination across every query path
│   ├── test_search_pipeline.py        #   10 — FTS5 + vector + RRF fusion end to end
│   ├── test_service_live_launchd.py   #    1 — opt-in live launchd proof (skipped by default)
│   ├── test_two_writer_subprocess.py  #    3 — two-writer locking across subprocesses
│   ├── test_watch_daemon_e2e.py       #    6 — detached `sif watch` daemon lifecycle
│   └── test_watch_e2e.py              #    6 — foreground `sif watch` indexing battery
├── fixtures/bench/                    # Committed synthetic benchmark pack (150 docs, 56 graded queries)
├── support/bench.py                   # ConceptEmbedder + build_bench_db helpers for the bench tests
├── support/eval.py                    # Deterministic personal-eval index and query-log helpers
└── e2e/                               # Reserved tier; currently empty
```

- **unit/** tests a single module in isolation, using mocks (`MagicMock`) or the temporary-database fixtures. `database/` mirrors the `sif.database` package (schema, repositories, locking, maintenance, query log, typed metadata store), while `db/` covers connection management (`DatabaseConnection`) and repositories. `scripts/` unit-tests the dry-run command planners for the evaluation and sweep runbooks (`breadcrumb_eval`, `chunk_sweep`, `harrier_eval`).
- **integration/** exercises multiple layers together: WAL concurrency and two-writer locking across processes, CLI embed idempotency and incremental-index equivalence against real temporary databases, maintenance (vacuum/backup) against live readers and writers, the full search pipeline (FTS5 + vector + RRF fusion), metadata filtering on a real schema, deterministic pagination on every query path, and real-subprocess batteries for foreground `sif watch`, the detached watch daemon, and the MCP server with its embedded watcher. `test_service_live_launchd.py` is skipped unless `SIF_TEST_LIVE_LAUNCHD=1` is set on macOS with `launchctl` on `PATH`.
- **e2e/** is a placeholder with no tests yet; add true end-to-end scenarios here.
- **test_docs.py** extracts fenced code blocks from a hardcoded `DOCS_FILES` list (README.md plus `docs/index.md`, `cli-reference.md`, `configuration.md`, `quickstart.md`, `mcp-server.md`, `search-algorithms.md`, `benchmarking.md`, `architecture.md`, `models.md`, `installation.md`, and `migration.md`) and checks that the documented `sif` commands exist, Python and SQL blocks are valid, and JSON examples match the real output schemas. Its 20 tests also guard against removed command names (`sif collection create`, `sif mcp start`, and others), stale default model names, bare `sif search <query>` usage, positional arguments on option-only commands, phantom environment variables in `configuration.md`, drift between `cli-reference.md` and the live Click command tree, a retired 7B default, the uv-first install guidance and degradation matrix in `installation.md`, and the deprecated `sif pull` alias.
- **test_ci_workflows.py** reads `uv.lock`, `pyproject.toml`, and the workflow files as text and pins the packaging and CI contract: CPU-only torch resolved from the explicit PyTorch CPU index (no CUDA stack or `black`), the `embed`/`all` dependency floors, the eight-cell test matrix, the frozen-lock full-suite invocation, least-privilege permissions, the SHA-pinned `setup-uv` action, tag-push exclusion, and the lint job's three repo gates.
- **test_hygiene.py** guards the repository cleanup baseline: deleted dead layers and modules, the removed `tests/factories.py`, exactly one docs `VERIFY` marker (the bandit note below), the tracked-junk list, and no advertised tooling targets the repository does not configure.
- **test_release_metadata.py** pins the release surfaces: the README MCP registry marker, the changelog version, the single-sourced version literal, the `pyproject.toml` readme field, the Python 3.13 classifier, and the `publish.yml` workflow's tag gate, OIDC scope, artifact handoff, TestPyPI-first ordering, and version gate.
- **test_sif_complete.py** is a smoke suite that imports the core modules and runs basic database/collection/chunker/RRF/CLI/scanner/parser operations against temp directories.
- **test_version_identity.py** pins the release version to a single literal in `src/sif/_version.py`: `pyproject.toml` takes its version dynamically from that module, all runtime surfaces agree, no other module assigns `__version__`, and `sif --version` prints the package version.
- **test_windows_smoke_script.py** exercises the pure matchers behind `make windows-smoke` (`scripts/windows_smoke.py`): fcntl/missing-root warnings, detach and service refusals, traceback rejection, the fixed eight-invocation argv list, and the non-Windows refusal.
- **tests/fixtures/bench/** is the committed synthetic benchmark pack for `sif bench` — 150 generated Markdown documents (40 keyword, 38 synonym, 36 multilingual, 36 rival) plus 56 graded queries (36 tuning / 20 held-out). `tests/support/bench.py` provides `ConceptEmbedder` (a deterministic 32-dimension token-bag embedder that satisfies the `Embedder` protocol without downloading a model), `build_bench_db()` (an in-memory SchemaManager index with FTS triggers and a `vec0` table built from the corpus), and `load_fixture_queries()`. `heldout_defaults.json` pins the shipped-defaults evidence, and `tests/unit/search/test_bench_snapshot.py` fails if the committed numbers drift. The pack is regenerated with `python scripts/generate_bench_fixture.py`; `python scripts/generate_bench_fixture.py --check` is the drift gate. It is synthetic by design — never commit real personal-knowledge-base content to it. The tuning/held-out contract is documented in `tests/fixtures/bench/README.md`.

## Writing new tests

Follow the naming conventions enforced by `pyproject.toml`: files named `test_*.py`, classes prefixed `Test`, functions prefixed `test_`. Place module-level tests under `tests/unit/<area>/` and cross-layer tests under `tests/integration/`. Ruff applies relaxed rules to `tests/**` (docstrings, print, magic values, private-member access, imports outside the top level, and long argument lists are allowed — see the `per-file-ignores` in `pyproject.toml`).

There is no shared factory module: `tests/factories.py` was removed, and `tests/test_hygiene.py` pins its absence. Build entities from the `sample_*` fixtures below or construct the `sif.core` dataclasses directly inside the test body.

### Shared fixtures (tests/conftest.py)

| Fixture | Purpose |
|---------|---------|
| `_hermetic_color_env` | Autouse fixture that strips color-forcing environment variables before every test |
| `_hermetic_sif_logging` | Autouse fixture that resets the `sif` logger's level, propagation, handlers, and global disable state before every test, so `caplog` assertions cannot be silenced by a prior CLI test (pytest 9.0.x behavior) |
| `reset_identity_state` | Autouse fixture that clears embedder-identity warn-once latches when the identity module is already imported |
| `reset_context_cache` | Autouse fixture that clears the per-process context-map cache before and after each test |
| `temp_dir`, `temp_db_path` | Temporary directory / database file path |
| `db_connection` | A `DatabaseConnection` on a temp path |
| `temp_db` | A `DatabaseConnection` with collections/documents/chunks/contexts tables created |
| `sample_markdown_file`, `sample_markdown_content` | A realistic Markdown file with frontmatter (and its raw contents) |
| `sample_collection_id`, `sample_document_id`, `sample_chunk_id` | Prebuilt entity IDs |
| `sample_collection(s)`, `sample_document(s)`, `sample_chunk(s)`, `sample_context`, `sample_document_metadata` | Prebuilt domain entities |
| `mock_embedder` | Deterministic 384-dim mock embedding model |
| `mock_repository`, `mock_search_repository`, `mock_embedding_manager` | Mocked persistence and search collaborators |
| `event_loop` | Shared event loop for the async MCP tests |
| `docs_test_db`, `docs_runner` | Temp database seeded with a docs collection, and a Click `CliRunner` pointed at it via `SIF_DB_PATH` |

Helper functions `create_test_document()` and `create_test_collection()` are also available for one-off entities inside a test body.

### Async tests

Mark coroutine tests with `@pytest.mark.asyncio` (see `tests/unit/mcp/test_backend.py` for examples) and remember the `pytest-asyncio` plugin requirement noted above.

### Benchmark fixture helpers

Tests that need the benchmark corpus without a real embedding model can use `tests/support/bench.py`:

- `ConceptEmbedder` — token-bag embedder with reproducible L2-normalized vectors; similarity is driven purely by shared tokens
- `build_bench_db(corpus_root, embedder)` — builds a real in-memory schema (FTS triggers plus `vec0` embeddings) from the committed corpus, with fixed document ids (`doc-000` style) and path-keyed relevance; it skips the test when `sqlite-vec` is unavailable
- `load_fixture_queries(path)` — loads `queries.json` from the pack

The pack lives in `tests/fixtures/bench/` and its structure and tuning/held-out contract are documented in `tests/fixtures/bench/README.md`. Tests that change shipped defaults must produce held-out evidence at the committed bar; `tests/unit/search/test_bench_snapshot.py` pins the committed `heldout_defaults.json` numbers.

### Personal-eval helpers

`tests/support/eval.py` builds deterministic personal corpora for the `sif eval --personal` path used by `tests/unit/cli/test_eval.py`:

- `build_personal_db(db_path, documents=60, ...)` — writes a real file-backed index (production schema, FTS triggers, `vec0` embeddings) with a 60-document corpus by default and one chunk per document; it skips when `sqlite-vec` is unavailable. The on-disk vec0 dimension is validated by `Database.init_schema`, so patch `get_settings().embedding_dim` with the same dimension passed here.
- `bilingual_titles_and_bodies(count, zh_count)` — deterministic English plus trailing Chinese fixture text for language-split tests
- `seed_query_log(conn, queries)` — seeds `query_log` rows through the repository's capped write path
- `rewrite_saved_run(path, mutate)` — mutates an auto-saved eval run file in place for comparison/tamper tests

The CLI instrument itself offers `sif eval --min-heldout N` (default 25, range 25–500) to widen a fresh run's sampling until at least `N` held-out queries exist; 101 or more held-out queries is what makes a 0.01 mean-delta win admissible over the strict 1/N noise floor. `--compare` replays a saved run's query set and ignores `--min-heldout` (and `--require-language`) with a stderr warning. `--require-language` provides the analogous per-language floor of 10 held-out queries.

### Updating documentation tests

`tests/test_docs.py` validates only the files listed in its `DOCS_FILES` constant. If you add a new docs page containing runnable code blocks, add its path to `DOCS_FILES` so its examples are validated too. Commands that must not execute are excluded via `SKIP_COMMAND_PATTERNS` in the same file — currently `mcp http`, `mcp daemon`, `mcp stdio`, `pull `, `index embed`, `pip install`, `git clone`, `git checkout`, and `bench `. The module's 20 tests also cover the install and model docs (`installation.md`, `models.md`), including uv-first ordering and the degradation matrix.

## Coverage

Coverage is measured over `src/sif` on every run (via `addopts`) and reported three ways:

- `term-missing` — per-file missing lines in the console
- `htmlcov/index.html` — browsable HTML report
- `coverage.xml` — machine-readable report

A minimum threshold **is** enforced: `[tool.coverage.report]` in `pyproject.toml` sets `fail_under = 90`, so any run whose total coverage falls below 90% fails with `Required test coverage of 90.0% not reached`. This is the only threshold configured — there are no separate per-file, per-type (statements, branches, functions), or branch-coverage settings. Note that the total-coverage gate applies to partial runs too — running a single file or tier measures only that subset against the same 90% gate, so use `--no-cov` for focused work. The most recent full run (macOS, 2026-11-18) reports **95.03% coverage** (3,233 passed, 1 skipped), and the Linux run reports **95.04%** (3,232 passed, 2 skipped) out of 3,234 collected tests. Skips are environment- or platform-gated: a missing `sqlite-vec` extension (vector tests skip rather than fail), the opt-in live launchd proof, `claude` CLI availability in the plugin tests, `tzset` availability, and POSIX fork support all skip rather than fail where unavailable.

Artifacts are cleaned by `make clean` (removes `htmlcov/`, `.coverage`, `coverage.xml`).

## CI integration

Two GitHub Actions workflows run tests:

### `.github/workflows/test-matrix.yml` — Test Matrix

This is the primary test workflow. It triggers on every push to any branch (`push: branches: ['**']`, so tags never trigger it) and on every pull request. `fail-fast: false` makes all cells report, and `cancel-in-progress: true` cancels superseded runs on the same ref.

The `test` job runs an eight-cell matrix — Python 3.10, 3.11, 3.12, and 3.13 on both `ubuntu-latest` and `macos-latest` — with a 30-minute timeout per cell. Each cell:

1. Checks out the repository and installs `uv` via the SHA-pinned `astral-sh/setup-uv` action (v10.3.3), with caching keyed on `uv.lock`
2. Runs `uv sync --frozen --extra dev --extra embed`
3. Runs the full suite with `env -u FORCE_COLOR NO_COLOR=1 uv run --frozen pytest`

Coverage is not disabled, so the `fail_under = 90` gate applies in every cell. The workflow grants only `contents: read`, uses no secrets, and does not expose an OIDC token.

The `lint` job runs once on Ubuntu with Python 3.12 and the frozen `dev` extras, executing:

1. `uv run --frozen ruff check src tests`
2. `uv run --frozen ruff format --check src tests`
3. `uv run --frozen ty check src/sif`

### `.github/workflows/docs.yml` — Docs Validation

This workflow is documentation-only; it does **not** run the full pytest suite. It triggers on pull requests touching `docs/**`, `README.md`, `src/sif/cli/**`, `src/sif/config/**`, `scripts/generate_cli_ref.py`, `scripts/generate_config_ref.py`, or `tests/test_docs.py`, and on pushes to `main`.

The `docs-test` job (ubuntu-latest, Python 3.11) then:

1. Installs the package with `pip install -e ".[dev]"`
2. Runs `pytest tests/test_docs.py -v --no-cov`
3. Regenerates the CLI and configuration reference docs (`scripts/generate_cli_ref.py`, `scripts/generate_config_ref.py`) and fails on any diff (`git diff --exit-code docs/cli-reference.md docs/configuration.md`), ensuring the reference docs stay in sync with the code

`tests/test_ci_workflows.py` and `tests/test_release_metadata.py` pin the workflow properties above (matrix shape, frozen sync, coverage not disabled, action pinning, permissions, release-workflow ordering), so workflow changes that weaken these contracts fail locally and in CI.

To reproduce all local checks in one shot, use `make ci` (format check, lint, typecheck, security scan, and the full test suite). The security step runs `bandit`, which is not declared in the `dev` extras, so install it separately.

<!-- VERIFY: make ci's security step requires bandit, which is not declared in the dev extras in pyproject.toml -->

See [development.md](development.md) for the broader development workflow.
