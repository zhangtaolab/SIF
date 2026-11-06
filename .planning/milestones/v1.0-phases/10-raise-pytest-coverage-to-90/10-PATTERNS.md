# Phase 10: Raise pytest coverage to 90% - Pattern Map

**Mapped:** 2026-11-05
**Files analyzed:** ~20 new/modified/deleted artifacts
**Analogs found:** all test artifacts have in-repo analogs (this phase adds zero new technology)

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `tests/unit/database/__init__.py` | test (package marker) | n/a | `tests/unit/cli/__init__.py` | exact |
| `tests/unit/database/test_repositories.py` (extend) | test | CRUD / real SQL | itself (05-09 pattern) | exact |
| `tests/unit/database/test_migrations.py` (new) | test | CRUD / real SQL | `tests/unit/database/test_repositories.py` | exact |
| `tests/unit/cli/test_collection.py` (extend) | test (CliRunner) | request-response | itself + `tests/conftest.py` `docs_test_db` fixture | exact |
| `tests/unit/cli/test_main.py` (extend) | test (CliRunner) | request-response | `tests/unit/cli/test_status.py`, `test_main.py` itself | exact |
| `tests/unit/cli/test_get.py`, `test_search.py`, `test_index.py` (extend) | test (CliRunner) | request-response | `tests/unit/cli/test_collection.py` | exact |
| `tests/unit/search/test_rerank.py` + `tests/unit/inference/test_reranker.py` (extend) | test (mocked ML) | transform | `tests/unit/inference/test_reranker.py` | exact |
| `tests/unit/indexing/test_parser.py`, `test_chunker.py` (new/extend) | test (real temp files) | file-I/O / transform | `tests/unit/indexing/test_indexer.py`, `tests/unit/search/test_rerank.py` (tmp_path style) | exact |
| `tests/unit/core/__init__.py` + `test_context.py`, `test_collection_entity.py` (new) | test (mocked repo Protocol) | CRUD | `tests/unit/indexing/test_indexer.py` (DI-with-MagicMock fixtures) + conftest `mock_repository` | role-match |
| `tests/unit/models/test_download.py` (new) | test (tmp dirs + mocked network) | file-I/O | `tests/unit/search/test_rerank.py` (tmp_path layout tests) + conftest `docs_test_db` (lazy-import style) | role-match |
| `tests/unit/utils/` (new dir: test_text/paths/logging/progress) | test (pure helpers) | transform | `tests/unit/search/test_rerank.py` (pure-function tmp_path classes) | role-match |
| `src/sif/cli/config.py` (DELETE) | dead source | n/a | deletion precedent: `sqlite_repository.py` (D-02) | n/a |
| `src/sif/cli/formatters.py` (reduce to 2 live helpers) | source prune | n/a | — keep only `prepend_line_numbers`, `add_line_numbers_to_results` | n/a |
| `src/sif/utils/text.py` (delete dead fns, update `utils/__init__.py:13` re-export) | source prune | n/a | — | n/a |
| `pyproject.toml` (append `[tool.coverage.report] fail_under = 90` — LAST plan) | config | n/a | existing `[tool.pytest.ini_options]` block (pyproject.toml:202-207) | exact |

**Anti-location:** do NOT put new DB tests in `tests/unit/db/` (legacy mock-based home); the real-SQL home is `tests/unit/database/` (confirmed: it currently has no `__init__.py` — add one).

## Pattern Assignments

### Pattern 1 — CliRunner CLI tests: `tests/unit/cli/test_collection.py` (extend), `test_main.py`, `test_get.py`, `test_search.py`, `test_index.py`

Two complementary in-repo styles; prefer the real-DB style for rendering/error branches.

**1a. Mock-style (existing file, tests/unit/cli/test_collection.py:3-50)** — patch at the *consumer* module, pass `obj={"index_path": ...}`:

```python
from unittest.mock import MagicMock, patch
from click.testing import CliRunner
from sif.cli.commands.collection import collection_update_cmd

mock_repo = MagicMock()
mock_repo.get_by_name.return_value = collection
with (
    patch("sif.cli.commands.collection.Database", mock_db),
    patch("sif.cli.commands.collection.CollectionRepository", return_value=mock_repo),
):
    result = runner.invoke(collection_update_cmd, ["notes", "--cmd", "git pull"],
                           obj={"index_path": MagicMock()})
assert result.exit_code == 0
assert "Set pre-update command" in result.output
```

**1b. Real-DB style (tests/conftest.py:550-613 `docs_test_db` + `docs_runner`)** — seed via production `Database` + repositories, inject via env:

```python
@pytest.fixture
def docs_test_db(tmp_path: Path) -> Generator[Path, None, None]:
    from sif.database.database import Database
    db_path = tmp_path / "docs_test.db"
    db = Database(db_path)
    db.init_schema()
    with db.transaction() as conn:
        coll_repo = CollectionRepository(conn)
        coll_repo.create(DocsCollection(name="test-docs", path=str(tmp_path / "docs"), ...))
    yield db_path
    db.close()

@pytest.fixture
def docs_runner(docs_test_db: Path) -> "CliRunner":
    from click.testing import CliRunner
    return CliRunner(env={"SIF_DB_PATH": str(docs_test_db)})
```

Use style 1b for collection list/show/error branches (`not found` at collection.py:277/297/315) and `main.py` `cleanup` (needs a real DB with orphaned rows). Env injection via `SIF_DB_PATH` is also shown in `tests/unit/cli/test_status.py:49` (`CliRunner(env={"SIF_DB_PATH": "/tmp/test-sif.db"})`).

**Error assertions (click 8.3.2):** streams are independent; `mix_stderr` does not exist. Assert error text on `result.stderr` or `result.exit_code != 0`; `result.output` is the combined view. Force width with `env={"COLUMNS": "80"}` (or 200) for table assertions.

### Pattern 2 — Real in-memory SQLite: `tests/unit/database/test_repositories.py` (extend), `test_migrations.py`, `embedding/cache.py` tests

**Analog:** `tests/unit/database/test_repositories.py:25-34` — copy this exact fixture shape:

```python
@pytest.fixture
def db():
    """Real in-memory SQLite with the production documents/contexts DDL."""
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    manager = SchemaManager(conn)
    manager._create_documents_table()
    manager._create_contexts_table()
    yield conn
    conn.close()
```

Plus module-level row-seeding helpers (`_insert_document`, `_insert_context`, lines 55-80) inserting rows that satisfy every NOT NULL column. Extend with additional `SchemaManager` table creators as needed; for `database.py` `connect()/transaction()` and `migrations.py`, use the conftest `Database(db_path).init_schema()` temp-file variant (conftest:556-557).

### Pattern 3 — Mocked ML objects: `tests/unit/inference/test_reranker.py` (extend for Qwen3Reranker), `tests/unit/search/test_rerank.py`

**Analog:** `tests/unit/inference/test_reranker.py:82-136` — patch the ML class at its top-level module, pin return values on the MagicMock model:

```python
reranker = LlamaCppReranker(model_path="/path/to/model.gguf")
with patch("llama_cpp.Llama") as mock_llama:
    mock_model = MagicMock()
    mock_model.embed.return_value = [0.1, 0.2, 0.3]
    mock_llama.return_value = mock_model
    results = reranker.rerank("query", sample_search_results, top_k=10)
assert len(results) <= 10
```

Same file patches `sentence_transformers.CrossEncoder` (line 223). For Qwen3Reranker, rerank.py imports ML libs **lazily at call time** — read the import site in `src/sif/search/rerank.py` (load ~283-333, rerank ~351-396) first and patch where the name is looked up (possibly via `patch("sif.search.rerank.AutoTokenizer")` after forcing the lazy import, or `sys.modules` injection). Reuse the conftest `sample_search_results` fixture (conftest:398-412).

`tests/unit/search/test_rerank.py:12-23` is also the model for pure-function tests with `tmp_path` (build a fake model dir with `config.json`/weights files, assert resolution).

### Pattern 4 — DI-with-mocks service tests: `tests/unit/core/test_context.py`, `test_collection_entity.py` (new)

**Analog:** `tests/unit/indexing/test_indexer.py:15-68` — one small `MagicMock` fixture per dependency, then a composed fixture injecting them; plus conftest `mock_repository` (conftest:445-453) and `sample_context` (conftest:344-355). Test the service logic (`core/context.py:93-168`) against the mocked repository Protocol.

### Pattern 5 — Dead-code deletion

Not test-pattern work. Delete `src/sif/cli/config.py`; reduce `src/sif/cli/formatters.py` to `prepend_line_numbers` + `add_line_numbers_to_results` (live importers: `src/sif/cli/commands/search.py:15`, `src/sif/cli/commands/get.py:10`); delete dead `utils/text.py` functions (`normalize_text`, `truncate_text`, `split_into_sentences`, `remove_code_blocks`, `slugify`) and update the re-export at `src/sif/utils/__init__.py:13` (keep `count_tokens`; `extract_code_blocks` also live). Precedent: `sqlite_repository.py` deleted under D-02. Guardrail: `ruff check src tests` + full suite + `make docs-generate` diff (docs are generator-owned). Note `tests/unit/cli/test_formatters.py` survives the deletion UNCHANGED — it imports only the two live helpers (`add_line_numbers_to_results`, `prepend_line_numbers`; import block re-verified at plan revision, 2026-11-05), so it tests no dead symbols. Do not prune or modify it (10-01 Task 1 states this explicitly).

### Pattern 6 — `pyproject.toml` gate (FINAL plan only)

No `[tool.coverage]` section currently exists in pyproject.toml — append after the existing `[tool.pytest.ini_options]` block:

```toml
[tool.coverage.report]
fail_under = 90
```

Verified: pytest-cov reads it and exits 1 below threshold. Land only after a full-suite run shows >= 90%, or every intermediate pytest run fails.

## Shared Patterns

### Test file skeleton (all new test files)

From every analog: module docstring, `from __future__ import annotations` (optional), stdlib / third-party / first-party import order, class-per-behavior grouping, one docstring per test. Ruff per-file-ignores for `tests/**` already allow `assert`, prints, local imports, magic-value comparisons (`pyproject.toml:180`).

### Filesystem safety (all tests)

**Source:** `tests/conftest.py` (`temp_dir`, `tmp_path` usage everywhere)
**Apply to:** every new test. Always `tmp_path` / explicit `cache_dir=tmp_path` — `ModelDownloader` defaults to `Path.home() / ".sif" / "models"` (`src/sif/models/download.py:40-44`). Never touch `~/.local/share/sif`.

### Test-runner invocation (planner should embed in verification steps)

```bash
env -u FORCE_COLOR NO_COLOR=1 pytest tests/unit/<dir>/<file>.py -q   # per task
env -u FORCE_COLOR NO_COLOR=1 pytest                                  # full suite
```

`FORCE_COLOR` must be *unset* (`-u`); `FORCE_COLOR=0` still fails. Verify new files with the full suite (order-dependent `test_openai_embedder.py` flakiness precedent).

### No new dependencies

stdlib `unittest.mock` only; no mock library, no new pytest plugins. CliRunner for all CLI invocation (never subprocess).

## No Analog Found

None — every artifact has an in-repo analog. Only genuinely novel detail: Qwen3Reranker patch targets (lazy imports — executor must read `src/sif/search/rerank.py` import sites first; research flags this as A1/ASSUMED).

## Metadata

**Analog search scope:** `tests/conftest.py`, `tests/unit/{cli,database,search,inference,indexing,db,mcp}/`, `src/sif/{cli,search,database,utils,models}/`, `pyproject.toml`
**Analogs verified git-tracked:** yes (`git ls-files` on all named test paths)
**Pattern extraction date:** 2026-11-05
