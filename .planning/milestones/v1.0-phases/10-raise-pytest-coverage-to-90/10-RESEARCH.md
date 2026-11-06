# Phase 10: Raise pytest coverage to 90% - Research

**Researched:** 2026-11-05
**Domain:** Test engineering (pytest/pytest-cov/coverage.py) + dead-code analysis of `src/sif`
**Confidence:** HIGH

## Summary

This is primarily an in-codebase phase, not a new-technology phase. The entire standard stack is already installed and verified working in this environment: pytest 9.1.1, pytest-cov 7.0.0, coverage 7.13.1, click 8.3.2, Python 3.13.9, with sqlite-vec, transformers 4.57.6, sentence-transformers 5.4.1, and torch 2.7.1 all present (so even the heavy-ML code paths are importable without `sys.modules` tricks in this env). The full suite was re-run this session: **688 passed in 14.92s, TOTAL 5587 stmts / 1220 missed / 78%** — exactly matching the phase description baseline. [VERIFIED: full-suite coverage run 2026-11-05, output in /tmp/phase10-coverage-baseline.txt]

The single highest-leverage discovery is that **~244 of the 1220 missed lines are provably dead code**, so the cheapest "coverage" is deletion, not tests. `src/sif/cli/config.py` (109 stmts, 0%) has zero importers anywhere in src/, tests/, scripts/, or docs/. `src/sif/cli/formatters.py` (157 stmts, 29%) has exactly two live functions — `prepend_line_numbers` and `add_line_numbers_to_results` — while all 19 other symbols (the entire `format_*` family, all `print_*` helpers, `OutputFormatter`, `get_formatter`) have zero usages outside the module, and the full-suite run leaving their bodies missed proves production never calls them either. `src/sif/utils/text.py` additionally has 5 of 7 functions with zero callers. Deleting these shrinks the denominator and removes ~220+ missed lines at near-zero risk (this project has precedent: `sqlite_repository.py` was deleted under decision D-02).

After deletion, coverage lands around 81-82%, leaving roughly 420-480 statements to cover with new tests. The live gap is concentrated: the top 6 live files (`cli/commands/collection.py` 131, `search/rerank.py` 82, `cli/commands/search.py` 76, `database/repositories.py` 47, `indexing/parser.py` 38, `cli/main.py` 38) hold 412 missed lines. Since realistic per-file yield is 75-85% of missed lines, the plan should target the top ~12 live files (~609 missed lines combined). The gate can be made self-enforcing by adding `[tool.coverage.report] fail_under = 90` to pyproject.toml — verified locally that pytest-cov honors it and fails the session with exit 1 below threshold — but this must land in the FINAL plan, after 90% is actually reached, or every intermediate run fails.

**Primary recommendation:** Delete the verified dead code first (config.py wholesale; formatters.py down to its two live helpers; text.py dead functions), then write CliRunner-with-real-temp-DB tests for the collection/main CLI commands, mock-transformers tests for Qwen3Reranker, real in-memory SQLite tests for the database layer (following the 05-09 pattern in `tests/unit/database/`), and add `fail_under = 90` to pyproject.toml last.

## Phase Requirements

The phase description states: "Requirements: TBD (coverage target T-10-1 to be mapped at planning)". No `T-10-1` exists in `.planning/REQUIREMENTS.md` yet — the planner must create that mapping. REQUIREMENTS.md contains no test-infra requirements; Phase 10 was added directly to the roadmap (STATE.md Roadmap Evolution).

| ID | Description | Research Support |
|----|-------------|------------------|
| T-10-1 (TBD, to be created at planning) | Total line coverage of `src/sif` >= 90% via `env -u FORCE_COLOR NO_COLOR=1 pytest --cov=src/sif`, full suite green | Baseline verified this session (78%, 688 passed); gap inventory, deletion targets, and per-file test strategies documented below; `fail_under` gate verified enforceable |

## Project Constraints (from CLAUDE.md)

- **Quality suite after every plan completes:** `ruff check src tests` + `ruff format --check src tests` + `pytest` must all pass.
- **Python 3.10+**, `list[str] | None` union syntax; line length 100; mccabe max-complexity 10; ruff isort with `combine-as-imports = true`; stdlib / third-party / first-party (`sif`) import order; two blank lines after imports.
- **Type annotations:** `ty check src/sif` must stay clean — new *source* changes (deletions are fine) need full annotations; tests are not in ty's include set (`[tool.ty.src] include = ["src/sif"]` [VERIFIED: pyproject.toml:190-191]).
- **Ruff per-file-ignores for tests:** `"tests/**/*" = ["D", "S101", "PLR2004", "SLF001", "T201", "PLC0415", "SIM117", "PLR0913"]` [VERIFIED: pyproject.toml:180] — docstrings not required in tests, `assert` allowed, prints allowed, local imports allowed.
- **Error-handling conventions** apply to any source touched: CLI commands raise `click.ClickException(str(e))`; DB transactions via `Database.transaction()` context manager with rollback.
- **Logging:** module-level `logger = get_logger(__name__)`.
- **Generator-owned docs:** `docs/cli-reference.md` and `docs/configuration.md` are wholesale rewritten by `make docs-generate` under a CI diff gate — never hand-edit them (user memory + `.github/workflows/docs.yml`). Deleting dead CLI modules does not change the Click command tree, so cli-reference should be unaffected, but re-running `make docs-generate` after Plan 1 and checking `git diff` is cheap insurance.

## Architectural Responsibility Map

For a coverage phase, "tiers" are the test layers that own each coverage gap:

| Capability (gap to close) | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| `cli/commands/collection.py` subcommands (131 missed) | Unit CLI tests (CliRunner) | Integration (real temp SQLite DB injected via `--index`) | Commands are thin Click wrappers over Database+repositories; CliRunner with a real temp DB exercises them end-to-end without mocks (existing pattern: `tests/unit/cli/test_collection.py`) |
| `cli/main.py` cleanup/status (38 missed) | Unit CLI tests (CliRunner + temp DB) | — | `cleanup` runs raw SQL against the index DB; needs a real DB with orphaned rows seeded |
| `search/rerank.py` Qwen3Reranker/CrossEncoder (82 missed) | Unit tests with mocked ML objects | — | `load()`/`rerank()` need transformers objects; transformers IS installed here, but mocking `AutoTokenizer`/`AutoModelForCausalLM` keeps tests fast and deterministic (Phase 04 precedent) |
| `cli/commands/search.py` format/explain branches (76 missed) | Unit CLI tests (CliRunner + mocked search pipeline) | — | Output-format branching (`--md`/`--xml`/`--csv`/`--json`, `--explain`, `--min-score`) is pure formatting over mockable results |
| `database/repositories.py` (47 missed) | Unit tests against real in-memory SQLite + production DDL | — | The 05-09 pattern (`tests/unit/database/test_repositories.py`) already proves this works and catches real SQL bugs |
| `database/{database,migrations}.py` (56 missed) | Unit tests, real temp/in-memory SQLite | — | `Database.connect()`/`transaction()` and `MigrationManager` are real-SQLite logic; no mocks needed |
| `core/context.py`, `core/collection.py` (60 missed) | Unit tests with mocked repository Protocol | — | Service classes over repository Protocols — mock the repo, test the service logic |
| `models/download.py` (35 missed) | Unit tests, temp cache dirs + mocked lazy network import | — | Filesystem methods (`list_cached_models`, `clear_cache`, `get_model_info`) are temp-dir testable; `download()` needs its lazily-imported ModelScope client mocked |
| `utils/{logging,paths,progress,text}.py` (77+ missed) | Unit tests, tmp_path/monkeypatch | — | Pure helpers; logging needs env/level matrix via monkeypatch |
| `indexing/{parser,chunker,scanner}.py` (79 missed) | Unit tests with real temp files | — | Real parsing of temp files is the established pattern (no mocks for parsers) |
| Dead-code removal (~244 missed) | Source deletion + suite green | — | Not a test-layer concern; a refactor task |
| >= 90% gate enforcement | pyproject.toml `[tool.coverage.report] fail_under` | Makefile (informational) | Verified: pytest-cov reads it from pyproject and exits 1 below threshold |

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| pytest | 9.1.1 (installed) | Test runner | Project standard; config in `pyproject.toml [tool.pytest.ini_options]` [VERIFIED: pyproject.toml:202-207] |
| pytest-cov | 7.0.0 (installed) | Coverage integration | Already in `addopts`; reads coverage config from pyproject |
| coverage | 7.13.1 (installed) | Measurement + `fail_under` gate | `[tool.coverage.report] fail_under` verified honored (see Code Examples) |
| click.testing.CliRunner | click 8.3.2 (installed) | CLI command invocation in tests | Used throughout `tests/unit/cli/` |
| unittest.mock | stdlib | patch/MagicMock | Project convention — no mock library installed, do not add one |

No new packages are needed. All versions confirmed by import this session [VERIFIED: local `python -c` import probe].

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| sqlite3 (stdlib) | Python 3.13.9 | Real in-memory SQLite in repository/DB tests | Prefer over MagicMock for `database/` coverage — catches real SQL bugs (05-09 lesson) |
| transformers (mocked) | 4.57.6 installed | Import surface for Qwen3Reranker tests | Mock `AutoTokenizer`/`AutoModelForCausalLM` classes; do not load real weights (speed) |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| deletion of dead code | writing tests for it | Tests for dead code are pure waste and perpetuate maintenance burden; phase description explicitly sanctions "cover or delete" |
| `[tool.coverage.report] fail_under` | `--cov-fail-under` in addopts | Equivalent effect but config-file is the pytest-cov-documented route ("For further control of coverage use a coverage config file" [CITED: pytest-cov.readthedocs.io/en/latest/config.html]); no flag duplication |
| branch coverage (`--cov-branch`) | — | Do NOT add: it changes the denominator and the phase gate is defined as *line* coverage >= 90% |

**Installation:** none required — `pip install -e ".[dev]"` already satisfies everything.

**Version verification:** performed via local import probe (click 8.3.2, pytest 9.1.1, coverage 7.13.1, pytest_cov 7.0.0, Python 3.13.9) [VERIFIED: local probe, 2026-11-05].

## Package Legitimacy Audit

**No new packages are installed by this phase.** All tooling is pre-existing dev dependency (`pytest`, `pytest-cov` in `pyproject.toml` dev extra [VERIFIED: pyproject.toml:43-49]). Audit table: not applicable — no installs, no registry lookups needed.

## Architecture Patterns

### System Architecture Diagram

The coverage campaign as a pipeline:

```
Baseline (verified this session)
  688 passed | 5587 stmts | 1220 missed | 78%
        |
        v
[Stage 1: Dead-code deletion]  -- grep-proven zero importers
  cli/config.py (-109 stmts/-109 missed)
  formatters.py dead symbols (-111 missed)
  utils/text.py dead fns (~-15..24 missed)
        |
        v  re-run suite -> expect ~81-82%, denominator ~5320-5340
[Stage 2: New tests, highest-missed live files first]
  CLI group:      collection.py(131) main.py(38) get.py(34)
  Search group:   rerank.py(82) search.py(76)
  Data group:     repositories.py(47) database.py(32) migrations.py(24)
                  core/context.py(37) models/download.py(35)
  Long tail:      parser(38) chunker(28) logging(26) cache(31) ...
        |
        v  running check: env -u FORCE_COLOR NO_COLOR=1 pytest
[Tollgate: TOTAL >= 90% (missed <= ~533 of ~5320)]
        |
        v
[Stage 3: Lock the gate LAST]
  [tool.coverage.report] fail_under = 90  -> pytest exits 1 below 90
  full quality suite: ruff check + ruff format --check + pytest
```

### Recommended Project Structure

New test files go into the existing tree (mirror `src/sif` layout):

```
tests/
├── conftest.py                      # exists — shared fixtures (temp_dir, temp DB, mocks)
├── unit/
│   ├── cli/
│   │   ├── test_collection.py       # EXTEND: add/remove/rename/list/show/enable/disable (currently only update-cmd/include/exclude)
│   │   ├── test_main.py             # EXTEND: cleanup command, status branches (currently 2 tests)
│   │   └── test_get.py, test_search.py, test_index.py  # EXTEND format/error branches
│   ├── database/                    # real-SQL pattern home (05-09); NOTE: missing __init__.py — add it
│   │   ├── test_repositories.py     # EXTEND
│   │   └── test_migrations.py       # NEW
│   ├── db/                          # legacy mock-based location — do not add new files here
│   ├── indexing/test_parser.py, test_chunker.py   # NEW/EXTEND (no parser/chunker test files exist under unit/indexing)
│   ├── models/test_download.py      # NEW
│   ├── core/                        # NEW dir: test_context.py, test_collection_entity.py
│   └── utils/                       # NEW dir: test_text.py, test_paths.py, test_logging.py, test_progress.py
```

### Pattern 1: CliRunner with a real temp database (for collection/main commands)

**What:** Invoke the command group with `--index <temp.db>` so Click's `ctx.obj["index_path"]` points at a real SQLite DB seeded via `SchemaManager`; assert on `result.output` / `result.exit_code`.
**When to use:** For every `cli/commands/collection.py` subcommand and `cli/main.py` `cleanup` — the existing mock-everything style in `tests/unit/cli/test_collection.py` (patching `Database` + `CollectionRepository`) works but only covers the happy path it hardcodes; real-DB invocations cover output rendering and error branches (`click.ClickException` paths at collection.py lines 277, 297, 315) in one shot.
**Why:** 131 missed statements in one file is the biggest live gap; per-subcommand CliRunner tests are mechanical to write.

### Pattern 2: Real in-memory SQLite + production DDL (database layer)

**What:** `sqlite3.connect(":memory:")` + `SchemaManager(conn)` + the real repository class — exactly the 05-09 pattern in `tests/unit/database/test_repositories.py` ("Every test here runs against a real in-memory SQLite database created from the production DDL" [VERIFIED: tests/unit/database/test_repositories.py:9-10]).
**When to use:** `repositories.py` (47), `database.py` `connect()`/`transaction()` (32, incl. the optional sqlite-vec load path at lines 126-131), `migrations.py` (24), `embedding/cache.py` (31 — pure SQLite, temp dir).
**Why:** The 05-09 CR-02 bug (orphaned-context deletion) was only reproducible against real SQL — mocks had green-lit the broken behavior.

### Pattern 3: Mocked ML objects for rerank.py (Qwen3Reranker 283-396)

**What:** `patch` the transformers entry points used inside `Qwen3Reranker.load()` / `.rerank()` (tokenizer/model classes) with MagicMocks returning pinned logits; follow the Phase 04 decision: "Patch `llama_cpp.Llama` and `sentence_transformers.CrossEncoder` at module level, not inside ... rerank" [VERIFIED: STATE.md Phase 04 decisions] — i.e., patch where the name is looked up, and use `sys.modules` injection only for optional deps not installed (none are missing in this env: transformers 4.57.6 is installed, so plain `patch("sif.search.rerank.AutoTokenizer", ...)`-style targets resolve).
**When to use:** `rerank.py` missed ranges 270-279 (init tail), 283-333 (load), 338-342 (prompt format), 351-396 (rerank), 409 (factory branch); plus CrossEncoderReranker branches 205-214 and `create_reranker` dispatch.
**Caution:** exact patch targets depend on how rerank.py imports transformers (lazy, inside methods — "rerank.py defers `ModelDownloader` and its ML-library imports to call time" [VERIFIED: docs/architecture.md:551]); the executor must read the import site before choosing the target. Mock-surface feasibility is [ASSUMED] until first test runs.

### Pattern 4: Dead-code deletion with proven-zero-usage evidence

**What:** Delete `src/sif/cli/config.py` entirely; reduce `src/sif/cli/formatters.py` to `prepend_line_numbers` + `add_line_numbers_to_results` (+ their imports); delete dead `utils/text.py` functions and update the re-export line.
**Evidence (all verified this session):**
- `cli/config.py`: `grep -rn "cli\.config\|from .config import" src/ tests/ scripts/ docs/` returns zero importers. 109 stmts / 109 missed / 0%.
- `formatters.py`: only two live imports exist — `from sif.cli.formatters import add_line_numbers_to_results, prepend_line_numbers` [VERIFIED: src/sif/cli/commands/search.py:15] and `from sif.cli.formatters import prepend_line_numbers` [VERIFIED: src/sif/cli/commands/get.py:10]. All 19 other symbols have 0 usages outside the module (per-symbol grep). The full suite leaving bodies of `format_json` (lines 24-33), `format_csv` (38-45), `format_markdown_table` (50-67), `format_xml` (73-82) missed proves no production path calls them.
- `utils/text.py`: `from sif.utils.text import count_tokens, normalize_text, truncate_text` is the only import [VERIFIED: src/sif/utils/__init__.py:13]; per-symbol grep shows `count_tokens` (5 uses) and `extract_code_blocks` (6 uses) live; `normalize_text`, `truncate_text`, `split_into_sentences`, `remove_code_blocks`, `slugify` have 0 uses.
**Guardrail:** re-run `ruff check src tests` + full suite + `make docs-generate` diff after deletion. Docs do not reference the dead symbols (grep of docs/*.md clean except live `ModelDownloader` mentions) [VERIFIED: grep this session].

### Anti-Patterns to Avoid

- **Writing tests for dead code:** every test written for `cli/config.py` or the dead formatter symbols is wasted effort and blocks future deletion. Delete first, then measure.
- **Adding `fail_under = 90` early:** at the current 78% (and ~81% post-deletion) every `pytest` run would exit 1, breaking all intermediate verification. Land it in the final plan.
- **Adding `--cov-branch`:** changes the metric denominator; the phase gate is line coverage.
- **Putting new repository tests in `tests/unit/db/`:** that is the legacy mock-based location; the real-SQL home is `tests/unit/database/` (05-09). Note the duplicate `test_repositories.py` in both dirs — new work belongs in `database/` and `tests/unit/database/` is missing `__init__.py` (its siblings have it); add it for consistency.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Coverage gate enforcement | Custom script parsing the term report and comparing to 90 | `[tool.coverage.report] fail_under = 90` in pyproject.toml | Verified: pytest-cov reads it and fails with exit 1 + "FAIL Required test coverage of 90.0% not reached" [VERIFIED: local scratch-project probe] |
| CLI invocation in tests | subprocess calls to `sif` binary | `click.testing.CliRunner` | Established pattern across `tests/unit/cli/`; fast, captures output, no path/env setup |
| Mock DB connections for repository tests | Ever-more-elaborate MagicMock return-value trees | Real in-memory SQLite + `SchemaManager` | 05-09 proved mocks hide real SQL bugs (CR-02) |
| Heavy-dependency mocking | Installing sentence-transformers/llama-cpp in CI or loading real weights | `unittest.mock.patch` at the lookup site; `sys.modules` injection only for absent optional deps | Phase 04 decision; transformers already importable in dev env |
| Measuring coverage manually | Running `coverage run` separately | existing `addopts` (coverage on every pytest run) | `addopts = "--cov=src/sif --cov-report=term-missing --cov-report=html --cov-report=xml"` [VERIFIED: pyproject.toml:207] |

**Key insight:** this phase adds zero new technology. Every pattern needed already exists somewhere in this repo's test suite; the work is applying them to the untested files plus deleting provably dead code.

## Common Pitfalls

### Pitfall 1: Spurious test failures under FORCE_COLOR
**What goes wrong:** tests fail in agent/CI shells that export `FORCE_COLOR`, even with `FORCE_COLOR=0` (setting it to "0" does not work — it must be unset).
**Why:** Rich/Click color detection behaves differently when the variable is merely present.
**How to avoid:** always run `env -u FORCE_COLOR NO_COLOR=1 pytest ...` — this is exactly the phase gate command, and a stored user memory ("UNSET FORCE_COLOR (env -u FORCE_COLOR, '0' doesn't work) + NO_COLOR=1 when running pytest in agent shells").
**Warning signs:** failures that mention Rich markup, ANSI codes, or output-matching assertions that pass locally but fail in automation.

### Pitfall 2: Order-dependent test_openai_embedder.py failures
**What goes wrong:** STATE.md's last session notes "2 order-dependent test_openai_embedder.py failures (passed in make-test order this run)".
**Why:** test pollution across files (likely module-level state/env).
**How to avoid:** verify new test batches with the FULL suite in the standard order, not only the new file; if the flaky pair resurfaces when adding embedding tests, treat it as a pre-existing condition to stabilize (or explicitly scope out) rather than blaming new tests.
**Warning signs:** test_openai_embedder.py failures that appear/disappear depending on which files ran before it.

### Pitfall 3: Asserting on error output via result.output only
**What goes wrong:** with click 8.3.2 (>= 8.2), `CliRunner` captures stdout and stderr separately; `mix_stderr` no longer exists. Error messages written via `click.echo(..., err=True)` land in `result.stderr`.
**Why:** Click 8.2.0 changelog: "Keep stdout and stderr streams independent in `CliRunner`" [CITED: click.palletsprojects.com/en/stable/changelog/]. Local probe on 8.3.2 confirmed: `CliRunner.__init__` signature is `(self, charset='utf-8', env=None, echo_stdin=False, catch_exceptions=True)` — no `mix_stderr`; `result.output` = `'to-stdout\nto-stderr\n'` (combined terminal view), `result.stdout` = `'to-stdout\n'`, `result.stderr` = `'to-stderr\n'` [VERIFIED: local probe].
**How to avoid:** assert error text on `result.stderr` (or just `result.exit_code != 0`); `result.output` remains the combined view so existing assertions keep passing.
**Warning signs:** passing locally, failing in CI where stderr/stdout interleaving differs.

### Pitfall 4: Rich word-wrapping makes output assertions brittle
**What goes wrong:** table/panel output wraps at terminal width, so substring assertions fail depending on COLUMNS.
**How to avoid:** for machine-output tests the project already forces `COLUMNS=80` (quick task 260910-kps: "regression tests under forced COLUMNS=80"); for human-format (rich table) assertions, assert on short stable fragments, or set `env={"COLUMNS": "200"}` in the CliRunner invoke.

### Pitfall 5: Landing fail_under before the target is reached
**What goes wrong:** adding `fail_under = 90` while coverage is 81% makes every pytest run exit 1 — breaking all subsequent task verification loops.
**How to avoid:** the gate config lands in the FINAL plan/task of the phase, after the tollgate run shows >= 90%. Optionally ratchet: set `fail_under` to the achieved percentage in intermediate plans only if desired.
**Warning signs:** "FAIL Required test coverage of 90.0% not reached. Total coverage: XX%" in unrelated test runs.

### Pitfall 6: exclude_lines footgun in coverage config
**What goes wrong:** if the plan adds `exclude_lines` to silence unreachable lines, it REPLACES the default regexes — silently un-excluding `pragma: no cover` semantics.
**How to avoid:** use `exclude_also` (appends) instead of `exclude_lines` (replaces) if exclusion config is ever added [CITED: coverage.readthedocs.io/en/latest/config.html].

### Pitfall 7: sqlite-vec optionality assumptions
**What goes wrong:** `Database.connect()` swallows sqlite-vec load failure ("sqlite-vec is optional" — `except Exception: pass` [VERIFIED: src/sif/database/database.py:126-131]) while `VectorSearcher.__init__` raises RuntimeError without it. Tests written on this machine (sqlite-vec present) may fail on machines without it.
**How to avoid:** new tests that exercise vector tables should tolerate both states or skip cleanly; STATE.md notes "suite's 5 conditional skips inactive in sqlite-vec-equipped env" — preserve that discipline. (Current grep shows no `skipif`/`importorskip` in tests; the conditional-skip mechanism referenced by STATE.md is not present as decorators — executor should re-check before relying on it.)

### Pitfall 8: tests/e2e is empty
**What goes wrong:** the old map (TESTING.md in `.planning/codebase/`) references `tests/e2e/test_cli_workflow.py` — it no longer exists (dir contains only `__init__.py`).
**How to avoid:** put CLI workflow coverage in `tests/unit/cli/` (CliRunner) per current convention; do not resurrect the e2e dir for this phase. Also note `.planning/codebase/TESTING.md` still says `docsift` paths — it predates the Phase 08 rename; trust the code, not that doc.

## Code Examples

### Gate configuration (lands in the FINAL plan)

```toml
# pyproject.toml — append. Verified behavior: pytest-cov reads this and
# fails the session (exit 1) below threshold; passes silently at/above.
# Probe output at 75% actual vs fail_under=90:
#   FAIL Required test coverage of 90.0% not reached. Total coverage: 75.00%
[tool.coverage.report]
fail_under = 90
```

Source: [CITED: coverage.readthedocs.io/en/latest/config.html] + [VERIFIED: local scratch-project probe with pytest 9.1.1 / pytest-cov 7.0.0 / coverage 7.13.1, this session]

### CliRunner test with real temp DB (Pattern 1)

```python
# tests/unit/cli/test_collection.py — extend with this shape.
# Existing file already imports CliRunner and the command functions;
# the mock-heavy style there (patch Database + CollectionRepository) covers
# single happy paths; the real-DB style below covers rendering + error branches.
from click.testing import CliRunner
from sif.cli.main import cli  # the Click group: --index option feeds ctx.obj["index_path"]
from sif.database.connection import DatabaseConnection
from sif.database.schema import SchemaManager

def _seed_db(db_path):
    conn = DatabaseConnection(db_path).connect()  # or sqlite3.connect + SchemaManager
    SchemaManager(conn).init_schema()
    # insert a collection row via CollectionRepository(conn).create(...)
    conn.close()

class TestCollectionList:
    def test_list_shows_seeded_collection(self, tmp_path):
        db = tmp_path / "sif.db"
        _seed_db(db)
        result = CliRunner().invoke(cli, ["--index", str(db), "collection", "list"])
        assert result.exit_code == 0
        assert "notes" in result.output
```

Source: adapted from existing `tests/unit/cli/test_collection.py` (CliRunner + `obj={"index_path": ...}` usage [VERIFIED: read this session]) and `tests/conftest.py` temp-DB fixtures. Exact seeding API (`DatabaseConnection.connect` vs `Database(...)`) must be confirmed against `src/sif/database/connection.py` at execution time.

### Real in-memory SQLite repository test (Pattern 2 — copy this exact shape)

```python
# Shape proven by tests/unit/database/test_repositories.py (05-09):
@pytest.fixture
def db():
    """Real in-memory SQLite with the production documents/contexts DDL."""
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    manager = SchemaManager(conn)
    # ... manager.create_tables() etc., yield conn, conn.close()
```

Source: [VERIFIED: tests/unit/database/test_repositories.py:22-30] — module docstring: "Every test here runs against a real in-memory SQLite database created from the production DDL (no sqlite-vec extension involved)."

### Mocked transformers reranker test (Pattern 3 — sketch)

```python
# Qwen3Reranker.load()/rerank() (rerank.py lines 283-396, 82 missed file-wide).
# rerank.py imports ML libs lazily at call time (docs/architecture.md:551), so
# patch at the lookup site inside sif.search.rerank AFTER confirming the exact
# import form in the source. Sketch (patch targets [ASSUMED] — verify first):
def test_qwen3_reranker_scores_via_yes_no_logits(monkeypatch):
    reranker = Qwen3Reranker(model_path=fake_dir)
    # patch tokenizer/model construction; pin softmax("yes") > softmax("no")
    # assert rerank(query, docs) returns descending scores
```

Source: Phase 04 mock precedent [VERIFIED: STATE.md decisions]; patch targets [ASSUMED].

## Verified Coverage Gap Inventory

Baseline re-measured this session [VERIFIED: `env -u FORCE_COLOR NO_COLOR=1 pytest` full run, 2026-11-05 — 688 passed, TOTAL 5587/1220/78%]. Gate math: >= 90% requires missed <= 558 of 5587, i.e. close >= 662 lines — or shrink the denominator via deletion and cover the rest.

**Dead code (delete, do not test):**

| File | Stmts | Missed | Cov | Evidence |
|------|-------|--------|-----|----------|
| `cli/config.py` | 109 | 109 | 0% | zero importers in src/tests/scripts/docs |
| `cli/formatters.py` dead symbols | ~139 of 157 | 111 | — | 19 of 21 symbols zero external usage; only `prepend_line_numbers` + `add_line_numbers_to_results` live (search.py:15, get.py:10) |
| `utils/text.py` dead fns | ~20 of 36 | ~15-24 | — | `normalize_text`, `truncate_text`, `split_into_sentences`, `remove_code_blocks`, `slugify` zero callers; `count_tokens`/`extract_code_blocks` live |

Deletion projection: total ~5320-5340, missed ~975-995, coverage ~81.3-81.8%. Remaining to cover: **~420-480 statements**.

**Live gaps, priority order (missed desc):**

| # | File | Missed | Cov | Suggested approach |
|---|------|--------|-----|--------------------|
| 1 | `cli/commands/collection.py` | 131 | 44% | CliRunner + real temp DB; all subcommands (add 44-68, remove 77-98, rename 107-126, list 134-175, show 183-208, enable 216-231, disable 239-254, errors 277/297/315, exclude 327-360) |
| 2 | `search/rerank.py` | 82 | 62% | Mocked transformers (Pattern 3); Qwen3Reranker 283-396, CrossEncoder 205-214, create_reranker 409 |
| 3 | `cli/commands/search.py` | 76 | 79% | CliRunner + mocked pipeline; format branches 394-416, 498-504, explain/min-score paths |
| 4 | `database/repositories.py` | 47 | 73% | Real in-memory SQLite (Pattern 2) |
| 5 | `indexing/parser.py` | 38 | 51% | Real temp files: plain-text path 87-104, code parse 150-171, edge cases 190-199 |
| 6 | `cli/main.py` | 38 | 69% | CliRunner + temp DB: cleanup 152-199, status branches |
| 7 | `core/context.py` | 37 | 49% | Mock repository; service methods 93-168 |
| 8 | `models/download.py` | 35 | 49% | Temp cache dirs + mocked lazy network import; DEFAULT_MODELS is ModelScope Qwen ids |
| 9 | `cli/commands/get.py` | 34 | 72% | CliRunner; output/error branches 57-106 |
| 10 | `database/database.py` | 32 | 62% | Real SQLite; connect/transaction 66-138 incl. optional sqlite-vec path |
| 11 | `embedding/cache.py` | 31 | 60% | Real SQLite + temp dirs |
| 12 | `indexing/chunker.py` | 28 | 71% | Real chunking of temp content; CodeChunker 143-180 |
| 13 | `utils/logging.py` | 26 | 58% | monkeypatch env/levels; setup_logging branches 50-69 |
| 14 | `mcp/transports/http.py` | 26 | 77% | Extend existing tests/unit/mcp/test_transports_http.py |
| 15 | `database/migrations.py` | 24 | 35% | Real in-memory SQLite; MigrationManager |
| 16 | `cli/commands/index.py` | 24 | 89% | CliRunner error branches |
| 17 | `core/collection.py` | 23 | 69% | Entity methods + mocked repo Protocol |
| 18 | `mcp/server.py` | 22 | 71% | Extend unit/mcp tests |
| 19 | `cli/commands/mcp.py` | 20 | 57% | CliRunner |
| 20 | `utils/paths.py` | 15 | 50% | tmp_path; expand_path/normalize_path/get_relative_path |
| Long tail (each <15) | bench 14, stdio 13, scanner 13, handlers 12, progress 12, schema 12, hybrid 11, core/document 10, settings 9, backend 9, embedder 8, term_match 7, expansion 7, pull 7, bm25 6, context-cmd 6, snippets 5, manager 4, rrf 3, protocol 2, benchmark 1 | ~170 | — | Fill opportunistically to cross 90% |

Realistic yield on targeted files is 75-85% of their missed lines, so targeting rows 1-12 (~609 missed) plus long-tail top-up is the right scope. Rows 1-6 alone = 412.

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| CliRunner(mix_stderr=False) to separate streams | Streams always independent; `mix_stderr` removed | Click 8.2.0 [CITED: changelog] | Existing tests unaffected (`result.output` is now the combined view); new error assertions use `result.stderr` |
| `exclude_lines` config | `exclude_also` preferred (appends vs replaces defaults) | coverage 7.x docs | Only relevant if exclusion config is added |
| coverage gate via CLI flag each run | `fail_under` in coverage config file, honored by pytest-cov | pytest-cov 7.x behavior, verified this session | One-time pyproject addition makes gate permanent |

**Deprecated/outdated:**
- `.planning/codebase/TESTING.md` references pre-rename `docsift` paths and a nonexistent `tests/e2e/test_cli_workflow.py` — superseded by the actual tree inspected this session.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Qwen3Reranker.load()/rerank() are coverable via patched transformers objects (patch targets resolvable despite lazy imports) | Pattern 3, gap #2 | Low — transformers 4.57.6 installed so imports resolve; worst case a few load() lines stay uncovered and long tail compensates |
| A2 | The 2 order-dependent test_openai_embedder.py failures noted in STATE.md (last session) still exist | Pitfall 2 | Low — they passed in this session's baseline run order; may resurface with new embedding-adjacent tests |
| A3 | formatters.py `format_*`/`print_*` symbols have no external consumers outside this repo (safe to delete) | Pattern 4, Open Q1 | Medium — if the `sif` distribution is consumed as a library by external code, deletion is a breaking API change; nothing in repo/docs/skills references them |
| A4 | Per-file yield of 75-85% of missed lines is achievable for targeted files | Scope math | Low-medium — if yield is lower, long-tail files must be pulled in; tollgate check catches it early |
| A5 | `utils/text.py` dead-function deletion is in scope (phase description names `utils/text.py` but as a coverage target, not explicitly as deletion) | Pattern 4, Open Q2 | Low — covering dead functions instead would waste effort; planner should confirm scope |

## Open Questions (RESOLVED)

All four questions were resolved at phase planning (2026-11-05); each resolution is implemented in a committed plan.

1. **Delete vs. cover the dead cluster (~244 stmts)?** — RESOLVED: DELETE. Implemented in 10-01 (config.py deleted wholesale; formatters.py reduced to its two live helpers; utils/text.py dead functions removed; A5 scope question settled as in-scope, no objection surfaced).
   - What we know: phase description says "cover or delete"; evidence for deletion is strong (zero usages, full-suite-missed bodies, project precedent D-02).
   - What's unclear: whether the user considers `formatters.format_*` part of a public API surface worth keeping (A3).
   - Recommendation: delete `cli/config.py` and formatters dead symbols (explicitly sanctioned); treat `utils/text.py` dead functions as included unless the user objects in planning.
2. **Where do new repository/DB tests live — `tests/unit/database/` or `tests/unit/db/`?** — RESOLVED: `tests/unit/database/` for all new DB-layer tests, `__init__.py` added first; `db/` left untouched. Implemented in 10-04 Task 1.
   - What we know: both exist with a duplicate `test_repositories.py`; `database/` is the newer real-SQL home (05-09) but lacks `__init__.py`.
   - Recommendation: `tests/unit/database/` for all new DB-layer tests; add its `__init__.py`; leave `db/` untouched (or note consolidation as out of scope).
3. **Should the 90% gate also gate CI?** — RESOLVED: out of scope for this phase. `fail_under = 90` in pyproject.toml (10-07 Task 2) already enforces the gate on every pytest run anywhere; a full CI workflow is a separate initiative.
   - What we know: CI (`.github/workflows/docs.yml`) only runs docs tests; there is no full-suite CI workflow; the gate is local via Makefile.
   - Recommendation: out of scope for this phase beyond `fail_under` (any pytest run anywhere now enforces it); a full CI workflow is a separate initiative.
4. **T-10-1 requirement mapping** — RESOLVED: T-10-1 created in `.planning/REQUIREMENTS.md` (traceability table, Phase 10, Pending) and mapped to the ROADMAP phase entry; all seven plans carry `requirements: [T-10-1]` in frontmatter.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python | everything | ✓ | 3.13.9 (project floor 3.10) | — |
| pytest | all testing | ✓ | 9.1.1 | — |
| pytest-cov | coverage | ✓ | 7.0.0 | — |
| coverage | fail_under gate | ✓ | 7.13.1 | — |
| click | CLI tests | ✓ | 8.3.2 | — |
| sqlite-vec | vector-path tests | ✓ | loads OK | conditional skip pattern |
| transformers | rerank import surface | ✓ | 4.57.6 | mock via patch |
| sentence-transformers | CrossEncoder import surface | ✓ | 5.4.1 | mock via patch |
| torch | rerank tensors | ✓ | 2.7.1 | mock via patch |

**Missing dependencies with no fallback:** none.
**Missing dependencies with fallback:** none.

All probes run this session [VERIFIED: local import probes].

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 9.1.1 + pytest-cov 7.0.0 (coverage always on via addopts) |
| Config file | `pyproject.toml` `[tool.pytest.ini_options]` [VERIFIED: pyproject.toml:202-207] |
| Quick run command | `env -u FORCE_COLOR NO_COLOR=1 pytest tests/unit/cli/test_collection.py -q` (~seconds) |
| Full suite command | `env -u FORCE_COLOR NO_COLOR=1 pytest` (688 tests, ~15s with coverage) |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| T-10-1 | TOTAL line coverage of src/sif >= 90%, full suite green | gate (whole-suite) | `env -u FORCE_COLOR NO_COLOR=1 pytest --cov=src/sif` then read TOTAL row; after final plan, exit code alone (fail_under) | n/a (aggregate) |
| T-10-1 (support) | deleted dead code leaves suite green | regression | `env -u FORCE_COLOR NO_COLOR=1 pytest` | existing suite |
| T-10-1 (support) | collection CLI subcommands behave | unit (CliRunner) | `env -u FORCE_COLOR NO_COLOR=1 pytest tests/unit/cli/test_collection.py -q` | ✅ extend |
| T-10-1 (support) | repository SQL correct on real SQLite | unit (real DB) | `env -u FORCE_COLOR NO_COLOR=1 pytest tests/unit/database/ -q` | ✅ extend |
| T-10-1 (support) | rerankers score correctly with mocked ML | unit (mocked) | `env -u FORCE_COLOR NO_COLOR=1 pytest tests/unit/search/test_rerank.py tests/unit/inference/test_reranker.py -q` | ✅ extend |

### Sampling Rate

- **Per task commit:** `env -u FORCE_COLOR NO_COLOR=1 pytest <files touched> -q` plus the CLAUDE.md quality trio at plan completion (`ruff check src tests; ruff format --check src tests; pytest`).
- **Per wave merge:** full `env -u FORCE_COLOR NO_COLOR=1 pytest` — check the TOTAL row trending toward 90% (missed <= 558 of 5587, lower after deletions).
- **Phase gate:** full suite green AND `--cov=src/sif` TOTAL >= 90%; then land `fail_under = 90` and re-run to confirm exit 0.

### Wave 0 Gaps

- `tests/unit/database/__init__.py` — missing; add for package consistency before adding files there.
- `tests/unit/core/__init__.py` + test files — directory does not exist yet (core/context.py, core/collection.py coverage).
- `tests/unit/utils/` — directory does not exist yet (text/paths/logging/progress coverage).
- No framework install needed; conftest.py fixture set is sufficient (temp_dir, DB fixtures, mock fixtures already present [VERIFIED: tests/conftest.py read this session]).

## Security Domain

This phase adds tests and deletes dead code; it introduces no new input surfaces, auth, crypto, or network egress. Applicability check:

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | unchanged |
| V3 Session Management | no | unchanged |
| V4 Access Control | no | unchanged |
| V5 Input Validation | no new surfaces | tests must use `tmp_path` for all filesystem fixtures — never write to real `~/.local/share/sif` or `~/.config/sif` (a stray live-DB test would touch user data) |
| V6 Cryptography | no | unchanged |

### Known Threat Patterns for test suites

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Tests hitting network (model downloads in `models/download.py` paths) | Information Disclosure | mock the lazy ModelScope/HF client; never let `download()` tests reach the network |
| Tests writing outside sandbox (ModelDownloader defaults to `~/.sif/models`) | Tampering | always pass explicit `cache_dir=tmp_path` — constructor default creates `Path.home() / ".sif" / "models"` [VERIFIED: src/sif/models/download.py:40-44] |
| Secrets in test assertions | Information Disclosure | none exist; keep it that way |

## Sources

### Primary (HIGH confidence)

- Full-suite coverage baseline run this session (688 passed; per-file table captured) — the authoritative gap inventory
- Local probes: CliRunner stream separation on click 8.3.2; `coverage report --fail-under` exit codes; pytest-cov honoring `[tool.coverage.report] fail_under` in pyproject (scratch project)
- Source reads: `src/sif/cli/{config,formatters,main}.py`, `src/sif/cli/commands/{search,get,collection}.py` (import lines), `src/sif/utils/text.py` symbols, `src/sif/models/download.py`, `src/sif/database/database.py`, `pyproject.toml`, `Makefile`, `tests/conftest.py`, `tests/unit/cli/test_{collection,formatters,main}.py`, `tests/unit/database/test_repositories.py`, `.github/workflows/docs.yml`
- Dead-code greps: per-symbol usage counts across src/, tests/, scripts/, docs/

### Secondary (MEDIUM confidence)

- [CITED: coverage.readthedocs.io/en/latest/config.html] — `[tool.coverage.report]` semantics, exclude_also
- [CITED: pytest-cov.readthedocs.io/en/latest/config.html] — defers to coverage config; addopts persistence
- [CITED: click.palletsprojects.com/en/stable/changelog/] — 8.2.0 stream separation

### Tertiary (LOW confidence)

- None — no claim in this document rests on an unverified web-only source

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all tools installed, versions probed, no new dependencies
- Architecture (gap inventory + dead-code classification): HIGH — every number from a fresh full-suite run this session; every dead-code claim from per-symbol grep + full-suite missed-line corroboration + file reads
- Pitfalls: HIGH — FORCE_COLOR is user-memory-verified and matches the gate command; Click/CliRunner behavior probe-verified; order-dependence is [ASSUMED] (A2) from STATE.md
- Reranker mocking feasibility: MEDIUM (A1) — patch targets not yet read at import-site level

**Research date:** 2026-11-05
**Valid until:** 2026-12-05 (stable tooling; re-baseline if `src/sif` changes materially before planning)
