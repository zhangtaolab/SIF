# Phase 8: Project rename from DocSift to SIF - Research

**Researched:** 2026-04-27
**Domain:** Python package renaming, CLI entry point migration, environment variable migration, documentation synchronization
**Confidence:** HIGH

## Summary

This phase performs a comprehensive rename of the Python project from `DocSift`/`docsift` to `SIF`/`sif` (Search / Index / Find). The rename is a complete break with no backward compatibility: no CLI aliases, no `DOCSIFT_*` env var recognition, no dual package names. All references across source code, tests, documentation, configuration files, and Claude Skills must be synchronized.

The project uses a `src/` layout with hatchling build backend, Pydantic Settings with `env_prefix`, Click CLI with `console_scripts` entry point, and platformdirs for cross-platform data paths. The rename touches 79 Python source files, 31 test files, 13 documentation markdown files, 2 generation scripts, and multiple configuration files (pyproject.toml, mkdocs.yml, Makefile, mypy.ini, GitHub workflow).

**Primary recommendation:** Execute the 9-step manual replacement sequence defined in CONTEXT.md, using `find` + `sed` for bulk string replacement at each step, followed by immediate validation (pytest collection, ruff, mypy). Clean all `__pycache__` and reinstall the package in editable mode after pyproject.toml changes.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Package import resolution | Python import system | — | `src/docsift/` → `src/sif/` affects all `from docsift...` imports |
| CLI command registration | Click + console_scripts | — | `docsift` entry point in pyproject.toml → `sif` |
| Environment variable loading | Pydantic Settings (API/Backend) | — | `env_prefix="DOCSIFT_"` → `"SIF_"` in Settings class |
| Data path resolution | platformdirs + constants | — | `APP_NAME` and path constants drive `~/.local/share/docsift/` → `~/.local/share/sif/` |
| Model cache auto-migration | CLI startup (main.py) | — | D-02 requires detection + `Path.rename()` on first run |
| Documentation generation | Scripts (generate_cli_ref.py, generate_config_ref.py) | — | Both scripts introspect the package and emit `docsift`/`DOCSIFT_` strings |
| Test patch targets | Test suite | — | 15 unique `patch("docsift...")` target strings across tests |
| Claude Skill execution | Skill files (.claude/skills/) | — | Skills invoke `docsift` CLI via subprocess; must be renamed to `sif-search`/`sif-get` |

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Python | 3.13.9 | Runtime | Project target is 3.9+; dev environment on 3.13 [VERIFIED: `python3 --version`] |
| hatchling | (via pip) | Build backend | Already configured in pyproject.toml [VERIFIED: `pyproject.toml` read] |
| Click | 8.3.2 | CLI framework | Entry point `docsift = "docsift.cli.main:main"` → `sif = "sif.cli.main:main"` [VERIFIED: `import click; click.__version__`] |
| Pydantic Settings | 2.13.1 | Configuration | `env_prefix="DOCSIFT_"` → `"SIF_"` [VERIFIED: `import pydantic_settings`] |
| platformdirs | 4.5.0 | Cross-platform paths | `user_data_dir(app_name)` drives data/cache/config paths [VERIFIED: `import platformdirs`] |
| rich | 14.3.3 | CLI output | Used for migration message styling [VERIFIED: `importlib.metadata.version('rich')`] |
| ruff | 0.15.11 | Lint/format | `known-first-party = ["docsift"]` must update [VERIFIED: `ruff --version`] |
| mypy | 1.20.1 | Type check | `files = src/docsift` must update [VERIFIED: `mypy --version`] |
| pytest | 9.0.2 | Test runner | 377 passed, 11 skipped baseline [VERIFIED: `pytest -q` output] |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| sqlite-vec | 0.1.9+ | Vector search | No rename impact; remains dependency [VERIFIED: `import sqlite_vec`] |
| sentence-transformers | 2.2.0+ | Embedding backend | No rename impact [ASSUMED] |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Manual 9-step replacement | Automated script (find + sed across entire repo) | User explicitly chose manual step-by-step with per-step verification (D-08). Automated bulk replace risks missing edge cases. |
| Keep `docsift` CLI alias | Complete break (selected) | User chose complete break (D-03). Alias would require dual entry_points and dual env_prefix handling. |
| Auto-migrate database | Regenerate (selected) | User chose regenerate (D-01). Auto-migrate would require schema compatibility guarantees and data migration scripts. |

**Installation:** No new packages required. After rename, reinstall:
```bash
pip install -e ".[dev]"
```

**Version verification:** All versions verified against current environment. No new dependencies introduced by this phase.

## Architecture Patterns

### System Architecture Diagram

```
Before Rename:
  [User] --docsift cmd--> [console_scripts: docsift.cli.main:main]
                              |
                              v
                       [Click CLI Group (docsift)]
                              |
          +-------------------+-------------------+
          |                   |                   |
          v                   v                   v
    [DOCSIFT_* env]    [Settings.get_db_path()]   [platformdirs]
          |                   |                       |
          v                   v                       v
    [Pydantic Settings]  [~/.local/share/docsift/]  [~/.cache/docsift/]

After Rename:
  [User] --sif cmd--> [console_scripts: sif.cli.main:main]
                          |
                          v
                   [Click CLI Group (sif)]
                          |
          +---------------+---------------+
          |               |               |
          v               v               v
    [SIF_* env]    [Settings.get_db_path()]   [platformdirs]
          |               |                       |
          v               v                       v
    [Pydantic Settings]  [~/.local/share/sif/]    [~/.cache/sif/]
```

### Recommended Project Structure

Before:
```
src/
├── docsift/           # Python package
│   ├── cli/
│   ├── config/
│   ├── core/
│   ├── database/
│   ├── embedding/
│   ├── indexing/
│   ├── mcp/
│   ├── mcp_server/
│   ├── models/
│   ├── search/
│   └── utils/
└── (package root)
```

After:
```
src/
├── sif/               # Renamed Python package
│   ├── cli/
│   ├── config/
│   ├── core/
│   ├── database/
│   ├── embedding/
│   ├── indexing/
│   ├── mcp/
│   ├── mcp_server/
│   ├── models/
│   ├── search/
│   └── utils/
└── (package root)
```

### Pattern 1: Import Path Update
**What:** All `from docsift...` imports become `from sif...`
**When to use:** Every Python file in `src/`, `tests/`, and `scripts/`
**Example:**
```python
# Before
from docsift.config.settings import Settings
from docsift.cli.main import cli

# After
from sif.config.settings import Settings
from sif.cli.main import cli
```

### Pattern 2: Patch Target Update in Tests
**What:** All `patch("docsift.module.Class")` strings become `patch("sif.module.Class")`
**When to use:** Every test file using `unittest.mock.patch`
**Example:**
```python
# Before
with patch("docsift.cli.commands.search.Database") as mock_db:

# After
with patch("sif.cli.commands.search.Database") as mock_db:
```

### Pattern 3: Logger Name Update
**What:** Logger namespace changes from `docsift` to `sif`
**When to use:** `src/sif/utils/logging.py` only
**Example:**
```python
# Before
root_logger = logging.getLogger("docsift")
return logging.getLogger(f"docsift.{name}")

# After
root_logger = logging.getLogger("sif")
return logging.getLogger(f"sif.{name}")
```

### Pattern 4: Model Cache Auto-Migration
**What:** On first CLI run, detect old model cache dir and rename to new path
**When to use:** `src/sif/cli/main.py` at startup, before Click argument parsing
**Example:**
```python
# In main() or cli() group, before Click processing
def _migrate_model_cache() -> None:
    old_dir = Path.home() / ".docsift" / "models"
    new_dir = Path.home() / ".sif" / "models"
    if old_dir.exists() and not new_dir.exists():
        old_dir.rename(new_dir)
        console.print(f"[green]Migrated: {old_dir} -> {new_dir}[/green]")
```

### Anti-Patterns to Avoid
- **Partial rename (leaving some `docsift` references):** Will cause import errors, broken tests, or confusing user experience. Every reference must change.
- **Renaming `.planning/` files:** These are historical audit trails. GSD convention: do not modify planning docs.
- **Forgetting `__pycache__` cleanup:** Stale `.pyc` files with old import paths will cause cryptic import errors after directory rename.
- **Editing generated docs directly:** `docs/cli-reference.md` and `docs/configuration.md` are auto-generated. Update the scripts, then regenerate.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Bulk string replacement across files | Manual file-by-file editing | `find` + `sed` or `perl -pi` | 800+ references across 100+ files; manual editing is error-prone and slow |
| Cross-platform path computation | Hardcoded `~/.local/share/...` | `platformdirs.user_data_dir(app_name)` | Already used in codebase; handles Windows/macOS/Linux correctly |
| Model cache migration | Custom copy+delete logic | `pathlib.Path.rename()` | Atomic on same filesystem; preserves permissions and metadata |
| Environment variable prefix handling | Custom env var parsing | Pydantic Settings `env_prefix` | Single field change propagates to all settings automatically |
| CLI entry point registration | Custom `sys.argv` parsing | `console_scripts` in pyproject.toml | Standard Python packaging; `pip` handles PATH registration |

**Key insight:** The rename is fundamentally a string substitution problem at scale. The risk is not in any individual change but in missing references. Systematic bulk replacement + comprehensive test verification is the only viable approach.

## Runtime State Inventory

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| Stored data | `~/.docsift/index.sqlite` (118KB, created 2026-04-18) | None — D-01: database regenerates; user re-runs `sif index` |
| Stored data | `~/.docsift/models/` (model cache directory) | Auto-migrate on first CLI run (D-02): `Path.rename()` from `~/.docsift/models` to `~/.sif/models` |
| Stored data | None in `~/.local/share/docsift/` | None — directory does not exist yet |
| Stored data | None in `~/.cache/docsift/` | None — directory does not exist yet |
| Live service config | No running services (MCP server, HTTP server are on-demand) | None |
| OS-registered state | `docsift` console script registered in venv (`/Users/forrest/miniconda3/bin/docsift`) | Will be replaced by `sif` after `pip install -e ".[dev]"` |
| OS-registered state | `docsift-0.1.0.dist-info` in venv site-packages | Will be replaced by `sif-0.1.0.dist-info` after reinstall |
| OS-registered state | Editable install `.pth` file: `_editable_impl_docsift.pth` | Will be regenerated by hatchling as `_editable_impl_sif.pth` |
| Secrets/env vars | No `DOCSIFT_*` env vars detected in current shell | None — code change only; no secrets to migrate |
| Build artifacts | `src/docsift/__pycache__/` and 11 other `__pycache__` dirs under `src/docsift/` | Delete all `__pycache__` after directory rename (`make clean` or `find -name __pycache__ -exec rm -rf {} +`) |
| Build artifacts | `tests/__pycache__/` and 12 `__pycache__` dirs under `tests/` | Delete all `__pycache__` after import changes |
| Build artifacts | `htmlcov/` coverage reports contain `docsift` paths | Regenerate after rename (`pytest --cov=src/sif`) |
| Build artifacts | `.pytest_cache/` may contain stale test node IDs | Clear with `pytest --cache-clear` or delete `.pytest_cache/` |

**Nothing found in category:**
- **OS-registered state (Task Scheduler/systemd/launchd):** None — verified no system-level service registrations.
- **Secrets/env vars (SOPS/CI env):** None — no SOPS or CI env var files in repo.
- **Docker images:** None — no Docker configuration in repo.

## Common Pitfalls

### Pitfall 1: Stale `__pycache__` Causing Import Errors
**What goes wrong:** After renaming `src/docsift/` to `src/sif/`, stale `.pyc` files in `src/docsift/__pycache__/` may still be found by Python's import system, causing `ModuleNotFoundError` or importing old code.
**Why it happens:** Python's import machinery caches compiled bytecode. If the old directory structure partially remains (e.g., `.pyc` files), Python may attempt to load from stale cache.
**How to avoid:** Run `find . -type d -name __pycache__ -exec rm -rf {} +` or `make clean` immediately after the directory rename and before running any tests.
**Warning signs:** `ModuleNotFoundError: No module named 'docsift'` or `ImportError` mentioning old paths after rename.

### Pitfall 2: Forgetting to Reinstall the Package After pyproject.toml Changes
**What goes wrong:** After changing `name = "docsift"` to `name = "sif"` and `packages = ["src/docsift"]` to `packages = ["src/sif"]` in pyproject.toml, running `pytest` or `docsift`/`sif` still uses the old editable install metadata.
**Why it happens:** The editable install `.pth` file (`_editable_impl_docsift.pth`) still points to `src/`. While imports may work, console script entry points and dist-info metadata remain stale.
**How to avoid:** Run `pip install -e ".[dev]"` after pyproject.toml changes. Verify with `pip show sif` and `which sif`.
**Warning signs:** `sif: command not found` or `docsift` still works after rename; `pip show docsift` still returns info.

### Pitfall 3: Missing Patch Target Updates in Tests
**What goes wrong:** Tests pass import checks but fail at runtime because `patch("docsift.cli.commands.search.Database")` no longer matches the actual import path `sif.cli.commands.search.Database`.
**Why it happens:** `unittest.mock.patch` patches by import path string. If the string is not updated, the patch silently fails to intercept the target.
**How to avoid:** After updating all `from docsift...` imports in tests, also update all `patch("docsift...")` strings. Use `grep -r 'patch("docsift' tests/` to find remaining targets.
**Warning signs:** Tests that previously mocked database calls now hit real database code; `MagicMock` assertions fail because the mock was never injected.

### Pitfall 4: Generated Documentation Still References Old Names
**What goes wrong:** `docs/cli-reference.md` and `docs/configuration.md` are regenerated by `scripts/generate_cli_ref.py` and `scripts/generate_config_ref.py`. If the scripts are updated but not re-run, or if the scripts still contain hardcoded `docsift`/`DOCSIFT_` strings, the generated docs will be inconsistent.
**Why it happens:** The generation scripts contain hardcoded strings (e.g., `docsift {path} [OPTIONS]`, `DOCSIFT_DB_PATH`) and introspect the live package.
**How to avoid:** Update both generation scripts first, then run `make docs-generate` (or `python scripts/generate_cli_ref.py && python scripts/generate_config_ref.py`), then verify with `git diff docs/`.
**Warning signs:** `pytest tests/test_docs.py` fails with command validation errors or env var name mismatches.

### Pitfall 5: Environment Variable Tests Fail Due to Hardcoded Prefixes
**What goes wrong:** Tests in `tests/unit/config/test_settings.py` and `tests/unit/cli/test_status.py` set env vars like `DOCSIFT_MODEL_TYPE` and `DOCSIFT_DB_PATH`. After changing `env_prefix` to `"SIF_"`, these tests will fail because Pydantic Settings no longer recognizes the old prefix.
**Why it happens:** Pydantic Settings `env_prefix` is a single configuration field. All env var lookups change simultaneously.
**How to avoid:** Update all `DOCSIFT_` strings in tests to `SIF_`. Use `grep -r 'DOCSIFT_' tests/` to find all occurrences.
**Warning signs:** `tests/unit/config/test_settings.py` fails with assertion that env var override did not apply.

### Pitfall 6: GitHub Workflow Path Triggers Become Stale
**What goes wrong:** `.github/workflows/docs.yml` has path triggers `src/docsift/cli/**` and `src/docsift/config/**`. After renaming the directory, these paths no longer exist, so the workflow will never trigger on CLI or config changes.
**Why it happens:** GitHub Actions `on.pull_request.paths` uses exact path matching (with glob support). Renamed directories break the trigger.
**How to avoid:** Update path triggers to `src/sif/cli/**` and `src/sif/config/**`.
**Warning signs:** PRs modifying CLI commands do not trigger the docs validation workflow.

### Pitfall 7: ruff `known-first-party` Mismatch Causes Import Sorting Errors
**What goes wrong:** ruff's isort rule uses `known-first-party = ["docsift"]` to distinguish first-party from third-party imports. After renaming, `sif` imports may be sorted as third-party, causing lint errors.
**Why it happens:** ruff treats unknown packages as third-party by default. Without updating `known-first-party`, `from sif...` imports may be grouped incorrectly.
**How to avoid:** Update `tool.ruff.lint.isort.known-first-party` from `["docsift"]` to `["sif"]` in pyproject.toml.
**Warning signs:** `ruff check` reports I001 (unsorted imports) errors after rename.

## Code Examples

### Bulk Replacement Commands

**Step 1: Rename directory**
```bash
mv src/docsift src/sif
```

**Step 2: Update all imports in source, tests, and scripts**
```bash
# macOS sed (BSD) — requires empty string after -i
find src tests scripts -name "*.py" -exec sed -i '' 's/from docsift/from sif/g' {} +
find src tests scripts -name "*.py" -exec sed -i '' 's/import docsift/import sif/g' {} +

# Update patch targets in tests
find tests -name "*.py" -exec sed -i '' 's/patch("docsift\./patch("sif./g' {} +
```

**Step 3: Update pyproject.toml**
```bash
sed -i '' 's/name = "docsift"/name = "sif"/g' pyproject.toml
sed -i '' 's/docsift = "docsift.cli.main:main"/sif = "sif.cli.main:main"/g' pyproject.toml
sed -i '' 's/packages = \["src\/docsift"\]/packages = ["src\/sif"]/g' pyproject.toml
sed -i '' 's/known-first-party = \["docsift"\]/known-first-party = ["sif"]/g' pyproject.toml
sed -i '' 's/--cov=src\/docsift/--cov=src\/sif/g' pyproject.toml
sed -i '' 's/"src\/docsift\/cli/"src\/sif\/cli/g' pyproject.toml
sed -i '' 's/"src\/docsift\/config/"src\/sif\/config/g' pyproject.toml
```

**Step 4: Update constants.py**
```bash
sed -i '' 's/APP_NAME = "docsift"/APP_NAME = "sif"/g' src/sif/config/constants.py
sed -i '' 's/\.local\/share\/docsift/.local\/share\/sif/g' src/sif/config/constants.py
sed -i '' 's/\.config\/docsift/.config\/sif/g' src/sif/config/constants.py
sed -i '' 's/docsift\.db/sif.db/g' src/sif/config/constants.py
```

**Step 5: Update settings.py**
```bash
sed -i '' 's/env_prefix="DOCSIFT_"/env_prefix="SIF_"/g' src/sif/config/settings.py
sed -i '' 's/DOCSIFT_/SIF_/g' src/sif/config/settings.py
sed -i '' 's/docsift\.db/sif.db/g' src/sif/config/settings.py
```

**Step 6: Update logging.py**
```bash
sed -i '' 's/logging.getLogger("docsift")/logging.getLogger("sif")/g' src/sif/utils/logging.py
sed -i '' 's/f"docsift\./f"sif./g' src/sif/utils/logging.py
```

**Step 7: Update CLI main.py**
```bash
sed -i '' 's/\.docsift/.sif/g' src/sif/cli/main.py
sed -i '' 's/prog_name="docsift"/prog_name="sif"/g' src/sif/cli/main.py
sed -i '' 's/docsift update/sif update/g' src/sif/cli/main.py
```

**Step 8: Update model download.py**
```bash
sed -i '' 's/\.docsift/.sif/g' src/sif/models/download.py
```

**Step 9: Update cli/config.py**
```bash
sed -i '' 's/\.docsift/.sif/g' src/sif/cli/config.py
```

**Step 10: Update tests**
```bash
find tests -name "*.py" -exec sed -i '' 's/DOCSIFT_/SIF_/g' {} +
find tests -name "*.py" -exec sed -i '' 's/docsift\.db/sif.db/g' {} +
```

**Step 11: Update documentation**
```bash
find docs -name "*.md" -exec sed -i '' 's/docsift/sif/g' {} +
find docs -name "*.md" -exec sed -i '' 's/DocSift/SIF/g' {} +
find docs -name "*.md" -exec sed -i '' 's/DOCSIFT_/SIF_/g' {} +
```

**Step 12: Update README, CLAUDE.md, Makefile, mkdocs.yml, mypy.ini**
```bash
sed -i '' 's/docsift/sif/g' README.md
sed -i '' 's/DocSift/SIF/g' README.md
sed -i '' 's/DOCSIFT_/SIF_/g' README.md

sed -i '' 's/docsift/sif/g' CLAUDE.md
sed -i '' 's/DocSift/SIF/g' CLAUDE.md
sed -i '' 's/DOCSIFT_/SIF_/g' CLAUDE.md

sed -i '' 's/docsift/sif/g' Makefile
sed -i '' 's/DocSift/SIF/g' Makefile

sed -i '' 's/docsift/sif/g' mkdocs.yml
sed -i '' 's/DocSift/SIF/g' mkdocs.yml

sed -i '' 's/src\/docsift/src\/sif/g' mypy.ini
sed -i '' 's/DocSift/SIF/g' mypy.ini
```

**Step 13: Update scripts**
```bash
sed -i '' 's/docsift/sif/g' scripts/generate_cli_ref.py
sed -i '' 's/DocSift/SIF/g' scripts/generate_cli_ref.py
sed -i '' 's/DOCSIFT_/SIF_/g' scripts/generate_cli_ref.py

sed -i '' 's/docsift/sif/g' scripts/generate_config_ref.py
sed -i '' 's/DocSift/SIF/g' scripts/generate_config_ref.py
sed -i '' 's/DOCSIFT_/SIF_/g' scripts/generate_config_ref.py
```

**Step 14: Update GitHub workflow**
```bash
sed -i '' 's/src\/docsift/src\/sif/g' .github/workflows/docs.yml
```

**Step 15: Update example files**
```bash
sed -i '' 's/docsift/sif/g' examples/quickstart.py
sed -i '' 's/DocSift/SIF/g' examples/quickstart.py
```

**Step 16: Rename test file**
```bash
mv tests/test_docsift_complete.py tests/test_sif_complete.py
```

**Step 17: Rename skill directories**
```bash
mv .claude/skills/docsift-search .claude/skills/sif-search
mv .claude/skills/docsift-get .claude/skills/sif-get
```

**Step 18: Update skill files**
```bash
sed -i '' 's/docsift/sif/g' .claude/skills/sif-search/SKILL.md
sed -i '' 's/DocSift/SIF/g' .claude/skills/sif-search/SKILL.md

sed -i '' 's/docsift/sif/g' .claude/skills/sif-get/SKILL.md
sed -i '' 's/DocSift/SIF/g' .claude/skills/sif-get/SKILL.md
```

**Step 19: Clean caches and reinstall**
```bash
find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
find . -type f -name "*.pyc" -delete
rm -rf .pytest_cache/ htmlcov/ .mypy_cache/
pip install -e ".[dev]"
```

**Step 20: Verify**
```bash
ruff check src tests
ruff format --check src tests
mypy src/sif
pytest -x -q
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `docsift` package name | `sif` package name | Phase 8 (now) | All imports, CLI, docs change |
| `DOCSIFT_*` env vars | `SIF_*` env vars | Phase 8 (now) | User must update shell config/env files |
| `~/.docsift/` data dir | `~/.sif/` data dir | Phase 8 (now) | Model cache auto-migrates; DB regenerates |
| `docsift-search`/`docsift-get` skills | `sif-search`/`sif-get` skills | Phase 8 (now) | Skill directory names and content updated |

**Deprecated/outdated:**
- `docsift` CLI command: replaced by `sif` (no alias per D-03)
- `DOCSIFT_DB_PATH`, `DOCSIFT_MODEL_NAME`, etc.: replaced by `SIF_DB_PATH`, `SIF_MODEL_NAME`, etc.
- `github.com/docsift/docsift`: replaced by `github.com/zhangtaolab/sif` (per D-07)
- `docsift.readthedocs.io`: replaced by `sif.readthedocs.io` (deferred to deployment)

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | The `sif` PyPI package name is available and not already taken by another project | Standard Stack | If taken, the package cannot be published to PyPI under this name; would require a different name |
| A2 | `github.com/zhangtaolab/sif` is the target repository URL (inferred from D-07 and existing `zhangtaolab` org) | User Constraints | If wrong, all GitHub URLs in docs/README will be incorrect |
| A3 | `sif.readthedocs.io` will be the documentation URL (inferred from D-07) | User Constraints | If wrong, MkDocs and README URLs will be incorrect |
| A4 | No external systems (CI/CD outside this repo, Docker Hub, etc.) reference `docsift` | Runtime State Inventory | If missed, external integrations may break after rename |
| A5 | The `.planning/` directory and its 2180 `docsift` references should NOT be modified | Architecture Patterns | If modified, historical audit trail is corrupted; GSD convention violated |
| A6 | `tests/test_docsift_complete.py` should be renamed to `tests/test_sif_complete.py` | Code Examples | If missed, test file name is inconsistent with new branding |
| A7 | `htmlcov/`, `.pytest_cache/`, and `.mypy_cache/` can be safely deleted and regenerated | Runtime State Inventory | If preserved, may contain stale paths causing confusion |

## Open Questions (RESOLVED)

1. **PyPI package name availability** — RESOLVED
   - What we know: The target name is `sif` (per D-07).
   - Resolution: Plans use `sif` as the package name. PyPI availability is a deployment concern outside this phase's scope.

2. **Model cache migration edge cases** — RESOLVED
   - What we know: D-02 specifies auto-migration of `~/.docsift/models/` to `~/.sif/models/` on first run.
   - Resolution: Plan 08-02 Task 3 implements guard clause `if old.exists() and not new.exists()`. If both exist, warning is printed and old directory is left for manual cleanup.

3. **CLAUDE.md update scope** — RESOLVED
   - What we know: CLAUDE.md contains 14 `docsift` references including project instructions for Claude Code.
   - Resolution: Plan 08-06 Task 2 explicitly updates CLAUDE.md as part of the documentation rename step.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3.9+ | Runtime, tests, type check | Yes | 3.13.9 | — |
| pip | Package reinstall after rename | Yes | 25.2 | — |
| ruff | Linting | Yes | 0.15.11 | — |
| mypy | Type checking | Yes | 1.20.1 | — |
| pytest | Test execution | Yes | 9.0.2 | — |
| sed (BSD) | Bulk string replacement | Yes | macOS default | Use `perl -pi -e` if needed |
| find | File discovery | Yes | macOS default | — |
| hatchling | Build backend | Yes | (via pip) | — |
| platformdirs | Path computation | Yes | 4.5.0 | — |
| Click | CLI framework | Yes | 8.3.2 | — |
| Pydantic Settings | Config/env vars | Yes | 2.13.1 | — |
| rich | CLI output styling | Yes | 14.3.3 | — |

**Missing dependencies with no fallback:**
- None

**Missing dependencies with fallback:**
- None

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 9.0.2 |
| Config file | `pyproject.toml` (`[tool.pytest.ini_options]`) |
| Quick run command | `pytest -x -q` |
| Full suite command | `pytest` |

### Phase Requirements -> Test Map

Phase 8 has no explicit requirement IDs in REQUIREMENTS.md (it is a project-wide rename phase added to the roadmap after initial requirements definition). The validation strategy is:

| Behavior | Test Type | Automated Command | File Exists? |
|----------|-----------|-------------------|-------------|
| All imports resolve after package rename | unit (collection) | `pytest --collect-only -q` | — |
| Source code passes lint after rename | lint | `ruff check src tests` | — |
| Source code is formatted correctly | format | `ruff format --check src tests` | — |
| Type checking passes after rename | type | `mypy src/sif` | — |
| All tests pass after rename | unit/integration | `pytest -x -q` | — |
| CLI entry point works | smoke | `sif --version` | — |
| Environment variable prefix works | unit | `pytest tests/unit/config/test_settings.py -x` | Yes |
| Model cache migration works | unit | New test needed | No — see Wave 0 Gaps |
| Generated docs are consistent | integration | `pytest tests/test_docs.py -x` | Yes |
| Skill files reference correct CLI | manual | Inspect `.claude/skills/sif-*/SKILL.md` | — |

### Sampling Rate
- **Per task commit:** `pytest -x -q` (fast feedback)
- **Per wave merge:** `ruff check src tests && ruff format --check src tests && mypy src/sif && pytest -x -q`
- **Phase gate:** Full suite green + `sif --version` works + `pip show sif` confirms install

### Wave 0 Gaps
- [ ] `tests/unit/cli/test_migration.py` — covers model cache auto-migration (D-02)
- [ ] `tests/unit/config/test_env_prefix.py` — explicitly verifies `SIF_*` env vars are recognized
- [ ] `tests/test_package_imports.py` — verifies all public modules importable under `sif` namespace

*(Existing test infrastructure covers most rename validation via the full suite, but migration logic and env prefix change lack dedicated tests.)*

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | No | N/A — local CLI tool, no auth |
| V3 Session Management | No | N/A — no sessions |
| V4 Access Control | No | N/A — single-user local tool |
| V5 Input Validation | Yes | Pydantic Settings validators already in place; no change needed |
| V6 Cryptography | No | N/A — no crypto operations in rename |
| V7 Error Handling | Yes | ClickException for CLI errors; no change needed |

### Known Threat Patterns for Rename Operations

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Path traversal during model cache migration | Tampering | Use `Path.home() / ".docsift" / "models"` (resolved) → `Path.rename()` to `Path.home() / ".sif" / "models"`. Both paths are under user home; no external input. |
| Race condition during directory rename | Tampering | `Path.rename()` is atomic on same filesystem. Check `old.exists() and not new.exists()` before rename. |
| Stale package metadata causing import confusion | Information Disclosure | Clean `__pycache__`, `.pytest_cache`, reinstall package. Verify with `pip show sif`. |

## Sources

### Primary (HIGH confidence)
- `pyproject.toml` — verified all 9 `docsift` references, build backend, scripts, tool configs
- `src/docsift/config/constants.py` — verified APP_NAME, DEFAULT_DB_PATH, DEFAULT_MODEL_PATH, DEFAULT_CONFIG_PATH
- `src/docsift/config/settings.py` — verified env_prefix, get_db_path(), docstrings
- `src/docsift/cli/main.py` — verified DEFAULT_INDEX_PATH, DEFAULT_CONFIG_PATH, prog_name, Click group
- `src/docsift/utils/logging.py` — verified root logger namespace
- `src/docsift/__init__.py` — verified __author__, docstring
- `src/docsift/models/download.py` — verified cache_dir default
- `src/docsift/cli/config.py` — verified index_path/config_path defaults
- `mkdocs.yml` — verified site_name, site_author, site_url, social links, copyright, repo info
- `Makefile` — verified all 6 `docsift` references
- `.github/workflows/docs.yml` — verified path triggers
- `mypy.ini` — verified files path and module config
- `tests/` — verified 31 test files with `docsift` references, 12 with `DOCSIFT_` references
- `docs/` — verified 13 markdown files with `docsift`/`DocSift`/`DOCSIFT_` references
- `scripts/` — verified 2 generation scripts with hardcoded strings
- `.claude/skills/docsift-search/SKILL.md` and `docsift-get/SKILL.md` — verified content and directory names
- Environment probe — Python 3.13.9, pip 25.2, ruff 0.15.11, mypy 1.20.1, pytest 9.0.2 all confirmed available
- Runtime state probe — `~/.docsift/` exists with `index.sqlite` and `models/`; `docsift` CLI installed in venv

### Secondary (MEDIUM confidence)
- `examples/quickstart.py` — 27 `docsift` references found via grep
- `DESIGN.md` — 7 `docsift` + 9 `DOCSIFT_` + 2 `DocSift` references
- `PROJECT_SUMMARY.md` — 32 `docsift` + 3 `DocSift` references
- `example_config.yaml` — 6 `docsift` + 2 `DocSift` references
- `verify_imports.py` — 31 `docsift` + 3 `DocSift` references
- `DELIVERY_REPORT.md` — 39 references
- `INTEGRATION_STATUS.md` — 50 references
- `REFACTOR_REPORT.md` — 38 references
- `SIDE_BY_SIDE_TEST_REPORT.md` — 4 references

### Tertiary (LOW confidence)
- PyPI package name `sif` availability — not verified via `pip search` or pypi.org API
- GitHub repository URL `github.com/zhangtaolab/sif` — inferred from D-07 and existing org name
- ReadTheDocs URL `sif.readthedocs.io` — inferred from D-07

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all versions verified against current environment
- Architecture: HIGH — all files read and catalogued; reference counts exact
- Pitfalls: HIGH — based on direct observation of codebase patterns and common Python rename issues
- Runtime state: HIGH — all directories and installed artifacts probed directly

**Research date:** 2026-04-27
**Valid until:** 2026-05-27 (stable domain — Python packaging conventions do not change rapidly)
