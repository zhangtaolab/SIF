# Phase 17: Engineering Foundation (CI Matrix + Hygiene + PyPI) - Pattern Map

**Mapped:** 2026-11-13
**Files analyzed:** 43 (7 new, 23 modified, 13 deleted)
**Analogs found:** 42 / 42 classified (39 with a direct analog, 3 with a partial analog + RESEARCH recipe)
**Tracked-source gate:** every analog path below verified via `git ls-files -- <path>` at HEAD `2f62b95` (dev). No gitignored mirrors are referenced.

## File Classification

| New/Modified/Deleted File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `.github/workflows/test-matrix.yml` (new) | config (CI workflow) | event-driven | `.github/workflows/docs.yml` | role-match |
| `.github/workflows/publish.yml` (new) | config (release workflow) | event-driven | `.github/workflows/docs.yml` + RESEARCH Pattern 2 | partial |
| `scripts/windows_smoke.py` (new) | utility (standalone script) | request-response (subprocess CLI assertions) | `scripts/generate_bench_fixture.py` | role-match |
| `tests/test_ci_workflows.py` (new) | test (file-content guard) | batch/transform | `tests/test_version_identity.py` | role-match |
| `tests/test_hygiene.py` (new) | test (file-content guard) | batch/transform | `tests/test_docs.py` | role-match |
| `tests/test_release_metadata.py` (new) | test (release metadata guard) | batch/transform | `tests/test_version_identity.py` | exact |
| `tests/test_windows_smoke_script.py` (new) | test (unit / message matcher) | request-response | `tests/unit/search/test_bench_fixture.py` + `tests/unit/utils/test_service.py` | partial |
| `Makefile` | config (build targets) | request-response | itself (`docs-test`/`docs-generate` targets) | exact |
| `pyproject.toml` | config (packaging) | transform | itself (`optional-dependencies`, `tool.hatch.version`, `tool.black`) | exact |
| `uv.lock` | config (generated lock) | transform | itself (regenerate, never hand-edit) | exact |
| `README.md` | doc | — | itself (line 1 generator comment placement) | exact |
| `src/sif/_version.py` | config (version literal) | — | itself | exact |
| `src/sif/cli/commands/watch.py` | CLI command | request-response | itself (`_check_lifecycle_guards`, `_run_detach`) | exact |
| `src/sif/utils/daemon.py` | utility | request-response | `src/sif/search/vector.py` RuntimeError guard | role-match |
| `src/sif/models/__init__.py` | package export | — | itself | exact |
| `src/sif/database/__init__.py` | package export | — | itself | exact |
| `src/sif/search/rrf.py` | utility | transform | itself | exact |
| `src/sif/config/constants.py` | config | — | itself | exact |
| `tests/conftest.py` | test fixture | — | itself | exact |
| `tests/test_docs.py` | test (doc guard) | batch/transform | itself (`SKIP_COMMAND_PATTERNS`) | exact |
| `examples/quickstart.py` | example/doc | request-response | itself (existing example shells) | role-match |
| `docs/changelog.md` | doc | — | itself (Keep a Changelog sections + link footer) | exact |
| `docs/installation.md` | doc | — | itself | exact |
| `docs/development.md` | doc | — | itself | exact |
| `docs/contributing.md` | doc | — | itself | exact |
| `docs/testing.md` | doc | — | itself | exact |
| `docs/architecture.md` | doc | — | itself | exact |
| `docs/models.md` | doc | — | itself | exact |
| `docs/api-reference.md` | doc | — | itself | exact |
| `DESIGN.md` | doc | — | itself | exact |
| `src/sif/models/search.py` (delete) | (dead layer) | — | git history | n/a |
| `src/sif/search/strategy.py` (delete) | (dead layer) | — | git history | n/a |
| `src/sif/database/migrations.py` (delete) | (dead layer) | — | git history | n/a |
| `tests/unit/test_search.py` (delete) | test | — | git history | n/a |
| `tests/unit/database/test_migrations.py` (delete) | test | — | git history | n/a |
| `tests/factories.py` (delete) | test helper | — | git history | n/a |
| `MagicMock/mock/{4398091296,4419046432,4419497200,4426075504}` (delete, 4 files) | tracked junk | — | git history | n/a |
| `quick_test.py`, `simple_test.py`, `verify_imports.py` (delete, 3 files) | tracked junk | — | git history | n/a |

## Pattern Assignments

### `.github/workflows/test-matrix.yml` (config, event-driven)

**Analog:** `.github/workflows/docs.yml` (the repo's only workflow). Match is role-only: docs.yml is single-job and uses `--no-cov`; the matrix must be multi-cell and must never disable coverage.

**Workflow skeleton to copy** (docs.yml:1-42):
```yaml
name: Docs Validation

on:
  pull_request:
    paths:
      - 'docs/**'
      - 'README.md'
  push:
    branches: [main]

permissions:
  contents: read

jobs:
  docs-test:
    runs-on: ubuntu-latest
    timeout-minutes: 15
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          pip install --upgrade pip
          pip install -e ".[dev]"

      - name: Run docs tests
        run: pytest tests/test_docs.py -v --no-cov
```

**What to copy vs. deliberately change:**

| docs.yml convention | In `test-matrix.yml` |
|---|---|
| `name:`, `on:`, `permissions: contents: read`, `jobs.<id>.runs-on`, `timeout-minutes`, `steps` with `- name:` + `run:` | Copy verbatim |
| `actions/checkout@v4` | Use `@v7` for the new workflow (docs.yml stays untouched) |
| `actions/setup-python@v5` + `pip install -e` | Replace with `astral-sh/setup-uv@68559e99cc807c1eb7e9238fd43a15bba460eec2` + `uv python install` + `uv sync --frozen --extra dev --extra embed` |
| `pytest ... --no-cov` | **Do not copy** — bare `pytest` so `addopts` and `fail_under=90` apply per cell |

**Matrix + guard pattern** (RESEARCH Pattern 1; pyproject coverage gate at `pyproject.toml:206-214`):
```yaml
permissions:
  contents: read

concurrency:
  group: ${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: true

jobs:
  test:
    name: py${{ matrix.python-version }} / ${{ matrix.os }}
    runs-on: ${{ matrix.os }}
    timeout-minutes: 30
    strategy:
      fail-fast: false
      matrix:
        os: [ubuntu-latest, macos-latest]
        python-version: ['3.10', '3.11', '3.12', '3.13']
    steps:
      - name: Checkout
        uses: actions/checkout@v7

      - name: Install uv
        uses: astral-sh/setup-uv@68559e99cc807c1eb7e9238fd43a15bba460eec2 # v10.3.3
        with:
          python-version: ${{ matrix.python-version }}
          enable-cache: true
          cache-dependency-glob: uv.lock
          cache-suffix: ${{ matrix.python-version }}

      - name: Install Python
        run: uv python install ${{ matrix.python-version }}

      - name: Sync dependencies
        run: uv sync --frozen --extra dev --extra embed

      - name: Run full test suite
        run: env -u FORCE_COLOR NO_COLOR=1 uv run --frozen pytest
```

**Auth/guard pattern:** workflow-level `permissions: contents: read` (same posture as docs.yml:16-17); no secrets, no `pull_request_target`.

**Constraints copied from RESEARCH:** quote `'3.10'`; `cache-dependency-glob: uv.lock`; `cache-suffix` per Python; `env -u FORCE_COLOR` is valid because both hosted runners default to bash.

---

### `.github/workflows/publish.yml` (config, event-driven release)

**Analog:** `.github/workflows/docs.yml` for the workflow skeleton only. There is no release-workflow precedent in the repo; publish mechanics come from RESEARCH Pattern 2 (verified against `pypa/gh-action-pypi-publish@release/v1`).

**Security/permissions pattern** (job-scoped, never workflow-global):
```yaml
permissions:
  contents: read          # workflow level

jobs:
  build:
    runs-on: ubuntu-latest
    timeout-minutes: 15
    # no id-token here
    ...
  publish-testpypi:
    needs: build
    environment:
      name: testpypi
      url: https://test.pypi.org/p/docsif
    permissions:
      id-token: write     # job-scoped only
    ...
  publish-pypi:
    needs: publish-testpypi
    environment:
      name: pypi
      url: https://pypi.org/p/docsif
    permissions:
      id-token: write
```

**Trigger + version gate** (matches `src/sif/_version.py:3` single literal):
```yaml
on:
  push:
    tags: ['v*']
```
```bash
VERSION="$(python3 -c "import runpy; print(runpy.run_path('src/sif/_version.py')['__version__'])")"
test "v${VERSION}" = "${GITHUB_REF_NAME}" || {
  echo "tag ${GITHUB_REF_NAME} does not match version ${VERSION}"
  exit 1
}
```

**Artifact handoff pattern:** `uv build` → `uvx twine check dist/*` → `actions/upload-artifact@v7` (name `dist`, `if-no-files-found: error`) → `actions/download-artifact@v8` into `dist/` → `pypa/gh-action-pypi-publish@release/v1`. Two publish jobs because the action cannot be invoked twice in one job. `skip-existing: true` on TestPyPI only.

---

### `scripts/windows_smoke.py` (utility, request-response)

**Analogs:**
1. `scripts/generate_bench_fixture.py` — standalone script conventions (`main() -> int`, argparse, `if __name__ == "__main__": sys.exit(main())`).
2. `scripts/generate_cli_ref.py` — shebang/docstring/`__future__`/module constants.
3. `src/sif/utils/service.py:206-219` — subprocess invocation with explicit argv list (never a shell).

**Script header pattern** (`scripts/generate_cli_ref.py:1-17`):
```python
#!/usr/bin/env python3
"""Generate CLI reference documentation from Click introspection."""

from __future__ import annotations

import inspect
import sys
from pathlib import Path
from typing import Any

import click


# Ensure sif is importable
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))
```

**Entry-point pattern** (`scripts/generate_bench_fixture.py`, tail):
```python
def main() -> int:
    """Generate (or drift-check) the bench fixture pack."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=int, default=16, help="generation seed")
    ...
    args = parser.parse_args()
    ...
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

**Subprocess pattern** (`src/sif/utils/service.py:206-219`):
```python
def _run(runner: Runner, argv: list[str]) -> subprocess.CompletedProcess[Any]:
    """Invoke a manager binary with an explicit argv list (D-12, never a shell)."""
    try:
        return runner(
            argv,
            capture_output=True,
            text=True,
            check=False,
            timeout=_RUN_TIMEOUT_SECONDS,
        )
```

**Smoke script requirements** (from RESEARCH Pattern 4 + Deletion/assertion table):
- Every invocation is an argv list; `SIF_DB_PATH` pointed at a per-run temp dir via the child `env`.
- Assertions are CLI-level, never `sif search query` (that loads an embedder and would download a model).
- Print `git rev-parse HEAD` and refuse to claim a pass on a dirty tree.
- Message matchers must be importable as pure functions so `tests/test_windows_smoke_script.py` can unit-test them without running `sif`.

**Assertion source-of-truth excerpts to encode:**

`src/sif/database/locking.py:57-63`:
```python
if not _FCNTL_AVAILABLE:
    logger.warning(
        "fcntl unavailable on this platform; index lock disabled "
        "(WAL + busy_timeout still protect database integrity)"
    )
    yield
    return
```

`src/sif/indexing/drift.py:84-89` and `src/sif/indexing/incremental.py:109-115, 200-206`:
```python
if not root.exists():
    logger.warning(
        "Collection root %s does not exist; skipping drift walk (all documents preserved)",
        collection.path,
    )
    continue
```
```python
if not Path(collection.path).exists():
    logger.warning(
        "Collection root %s does not exist; skipping update (all documents preserved)",
        collection.path,
    )
```

`src/sif/utils/service.py:66-85` (the existing honest service refusal):
```python
class ServiceManagerMissing(RuntimeError):  # noqa: N818 — plan-named type (13-04 action text)
    """The platform's service-manager binary is not on PATH (friendly remedy)."""

    def __init__(self, manager: str) -> None:
        """Pick the binary name and remedy for the manager kind."""
        ...
        super().__init__(
            f"{binary} was not found on PATH — required to install the watch service ({remedy})."
        )
```

CLI output strings the smoke asserts (verbatim sources): `sif status` table title `Index Status` + `Documents` row (`src/sif/cli/main.py:186-194`); `sif index update` path (`src/sif/cli/commands/index.py:41-59`); BM25 subcommand `sif search search --json` (`src/sif/cli/commands/search.py:429,470`); collection add positional path + `--name` (`src/sif/cli/commands/collection.py:27-29`).

---

### `tests/test_ci_workflows.py` (test, file-content guard)

**Analog:** `tests/test_version_identity.py` — the repo's established pattern for reading tracked files and asserting invariants with `pathlib` + `re`, including a Py3.10 `tomllib` fallback.

**Header + path constants** (`tests/test_version_identity.py:1-36`):
```python
"""Regression tests pinning the single-sourced release version identity."""

from __future__ import annotations

import re
from pathlib import Path

from click.testing import CliRunner

import sif
import sif.cli
from sif import _version
from sif.cli.main import cli
from sif.config.constants import APP_VERSION
from sif.mcp.protocol import InitializeResult


try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - Python 3.10 has no tomllib
    tomllib = None

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src" / "sif"
PYPROJECT = REPO_ROOT / "pyproject.toml"
VERSION_RE = re.compile(r"\d+\.\d+\.\d+")
```

**TOML section helper fallback** (`tests/test_version_identity.py:29-36`):
```python
def _section(text: str, name: str) -> str:
    """Return the raw TOML text of a table section (fallback parser helper)."""
    header = re.compile(rf"^\[{re.escape(name)}\]\s*$", re.MULTILINE).search(text)
    assert header is not None, f"missing [{name}] section in pyproject.toml"
    start = header.end()
    next_header = re.compile(r"^\[", re.MULTILINE).search(text, start)
    end = next_header.start() if next_header is not None else len(text)
    return text[start:end]
```

**Recursive scan pattern** (`tests/test_version_identity.py:70-87`):
```python
for module in sorted(SRC_ROOT.rglob("*.py")):
    text = module.read_text(encoding="utf-8")
    relative = str(module.relative_to(REPO_ROOT))
    if module_literal.search(text):
        offenders.append(relative)
```

**Guards to write (text-level, dependency-free — do NOT add PyYAML):**
- `.github/workflows/test-matrix.yml` text contains all four `'3.10'`/`'3.11'`/`'3.12'`/`'3.13'` values and both `ubuntu-latest`/`macos-latest`, `fail-fast: false`, `cancel-in-progress: true`, the pinned SHA `68559e99cc807c1eb7e9238fd43a15bba460eec2`, `uv sync --frozen`, `--extra dev`, `--extra embed`.
- The pytest run step does not contain `--no-cov` (Pitfall 12).
- `uv.lock` text contains `source = { registry = "https://download.pytorch.org/whl/cpu" }` for torch and no `nvidia-` / `triton` entries (Pitfall 1/7).

---

### `tests/test_hygiene.py` (test, file-content guard)

**Analog:** `tests/test_docs.py` — the repo's pattern for asserting that stale strings/commands are absent from docs and source.

**Absence-guard pattern** (`tests/test_docs.py:293-311`):
```python
def test_no_removed_commands_in_docs(self) -> None:
    """Docs must not contain removed commands."""
    removed_commands = [
        "sif collection create",
        "sif collection add-path",
        ...
    ]
    for md_file in DOCS_FILES:
        if not md_file.exists():
            continue
        content = md_file.read_text()
        for removed in removed_commands:
            if removed in content:
                pytest.fail(f"Removed command '{removed}' found in {md_file.name}")
```

**Guards to write:**
- `src/sif/models/search.py`, `src/sif/search/strategy.py`, `src/sif/database/migrations.py` do not exist; no `sif.models.search` / `sif.search.strategy` / `MigrationManager` imports remain under `src/`, `tests/`, `examples/` (scan with `rglob`, exclude the test itself by checking exact import string).
- `src/sif/search/rrf.py` has no `compute_rrf_score`.
- `Makefile` contains no `pre-commit` token; `.pre-commit-config.yaml` does not exist.
- `pyproject.toml` has no `black` requirement and no `[tool.black]`; `embed`/`all` floors are `sentence-transformers>=5.4.1`, `llama-cpp-python>=0.3.35`.
- Junk paths absent: `MagicMock/`, `quick_test.py`, `simple_test.py`, `verify_imports.py`.

Use `REPO_ROOT` constants from the `test_version_identity.py` pattern (not relative cwd paths) so the suite is runnable from the matrix at any cwd.

---

### `tests/test_release_metadata.py` (test, release metadata guard)

**Analog:** `tests/test_version_identity.py` (exact role: release-identity invariants).

**Excerpts:** same `REPO_ROOT`/`PYPROJECT`/`tomllib` fallback shown above. Add:
- README contains the exact line `<!-- mcp-name: io.github.zhangtaolab/sif -->` with a valid boundary (own line, no trailing period).
- `docs/changelog.md` contains `## [1.1.2]` and the `[1.1.2]:` link footer; `[Unreleased]` compare link points at `v1.1.2...HEAD`.
- `.github/workflows/publish.yml` contains the version-gate snippet (`src/sif/_version.py` + `GITHUB_REF_NAME`) and `skip-existing: true` under TestPyPI only.
- `tests/test_version_identity.py` remains the authority for runtime surfaces — do not duplicate it.

---

### `tests/test_windows_smoke_script.py` (test, unit / message matcher)

**Analogs:**
1. `tests/unit/search/test_bench_fixture.py:9` — imports a repo script directly:
```python
from scripts.generate_bench_fixture import build_pack, check_pack
```
   This works because pytest runs from the repo root (`tests/conftest.py` also inserts `src` into `sys.path`) and `scripts/` is an implicit namespace package. Use the same import for the smoke script helpers: `from scripts.windows_smoke import <matcher functions>`.
2. `tests/unit/utils/test_service.py:36-59` — the repo's pattern for deterministic subprocess/argv assertions:
```python
def _ok(argv: list[str]) -> subprocess.CompletedProcess[str]:
    """A successful scripted manager result."""
    return subprocess.CompletedProcess(argv, 0, stdout="active", stderr="")


class _RecordingRunner:
    """Fake ``subprocess.run`` recording exact argv lists (never a real manager)."""

    def __init__(self) -> None:
        self.calls: list[list[str]] = []

    def __call__(self, argv: list[str], **_kwargs: Any) -> subprocess.CompletedProcess[str]:
        self.calls.append(list(argv))
        return _ok(argv)
```

**Test style:** plain functions or `Test*` classes, fully annotated, `pytest.fail`/`assert` with the offending output in the message. Cover: flock warning matcher, missing-root matcher (`Removed: 0` + "all documents preserved"), detach refusal matcher (cause + remedy), service refusal matcher (`systemctl` + `watch service`), and a negative case proving the matcher does not accept a raw traceback.

---

### `Makefile` (config, build targets)

**Analog:** itself. New target must match the existing target style (echo line, tab-indented commands, `.PHONY` registration, `help` listing).

**Existing target style** (`Makefile:55-74`):
```make
test:
	@echo "Running tests with coverage..."
	pytest --cov=src/sif --cov-report=term-missing --cov-report=html --cov-report=xml

docs-test:
	@echo "Running docs validation tests..."
	pytest tests/test_docs.py -v --no-cov

docs-generate:
	@echo "Regenerating CLI and configuration reference docs..."
	python scripts/generate_cli_ref.py
	python scripts/generate_config_ref.py
```

**`.PHONY` and help registration** (`Makefile:4`, `:20-21`):
```make
.PHONY: help install ... docs-test docs-generate ... pre-commit security all ci ...
	@echo "  make docs-test    - Run docs validation tests"
	@echo "  make docs-generate - Regenerate CLI and config reference docs"
```

**New target** (RESEARCH Pattern 4):
```make
YOGA_DIR ?= D:\Github\SIF
YOGA_PYTHON ?= 3.12

windows-smoke:
	@echo "Preflight: yoga checkout"
	hc exec --on yoga --timeout 120 --cwd '$(YOGA_DIR)' git rev-parse HEAD
	hc exec --on yoga --timeout 120 --cwd '$(YOGA_DIR)' git status --porcelain
	hc exec --on yoga --timeout 600 --cwd '$(YOGA_DIR)' uv python install $(YOGA_PYTHON)
	hc exec --on yoga --timeout 600 --cwd '$(YOGA_DIR)' uv sync --frozen --extra dev
	hc exec --on yoga --timeout 600 --cwd '$(YOGA_DIR)' uv run --frozen python scripts/windows_smoke.py
```

**Removal edits:** line 4 (`pre-commit` → `windows-smoke` in `.PHONY`), line 29 (help line), lines 47/52 (`pre-commit install`), lines 109-112 (target), line 171 (`pre-commit autoupdate`), line 179 (`black` in the `info` grep).

---

### `pyproject.toml` + `uv.lock` (config)

**Analog:** itself. Preserve section ordering and extras style.

**Extras to edit** (`pyproject.toml:42-71`):
```toml
[project.optional-dependencies]
dev = [
    "pytest>=7.0.0",
    "pytest-cov>=4.0.0",
    "pytest-asyncio>=0.23.0",
    "black>=23.0.0",
    "ruff>=0.1.0",
    "ty>=0.0.1",
]
embed = [
    "sentence-transformers>=2.2.0",
    "modelscope>=1.36.0",
    "numpy>=1.24.0",
]
all = [
    "sentence-transformers>=2.2.0",
    "llama-cpp-python>=0.2.0",
    "modelscope>=1.36.0",
    "numpy>=1.24.0",
    "openai>=2.0.0",
]
```

**New uv source block** (RESEARCH Pattern 3 — no existing analog in this repo):
```toml
[[tool.uv.index]]
name = "pytorch-cpu"
url = "https://download.pytorch.org/whl/cpu"
explicit = true

[tool.uv.sources]
torch = [
  { index = "pytorch-cpu", marker = "sys_platform == 'linux'" },
]
```

**Current reality to change** (`uv.lock:2487-2491` resolves PyPI torch 2.11.0 with 36 `nvidia-` entries; `uv.lock:52`/`:650` carry black). `uv.lock` is generated: run `uv lock` + `uv lock --upgrade-package torch` in the same commit as the pyproject edit, then `uv lock --check` (Pitfall 2). Never hand-edit.

**Remove** `[tool.black]` (`pyproject.toml:87-89`) entirely. Keep `[tool.hatch.version] path = "src/sif/_version.py"` (`:81-82`) unchanged. Add the 3.13 classifier only after the matrix is green.

---

### `README.md` (doc)

**Analog:** itself. Line 1 is `<!-- generated-by: gsd-doc-writer -->`, line 2 `# SIF`.

Insert the exact marker on its own line immediately after line 1 (before the H1 is acceptable; RESEARCH Pattern 5):
```markdown
<!-- mcp-name: io.github.zhangtaolab/sif -->
```
Rules: exact match with `server.json`, own line, no trailing period; a trailing `.` or attached text breaks the Registry match.

---

### `src/sif/_version.py` (config)

**Analog:** itself — the one permitted `__version__` literal (`tests/test_version_identity.py:70-87` enforces single-sourcing).
```python
"""Version information for SIF."""

__version__ = "1.1.1"
```
Change line 3 to `"1.1.2"` only. Do NOT add a literal to `src/sif/__init__.py`, `src/sif/cli/__init__.py`, `src/sif/config/constants.py`, or `src/sif/mcp/protocol.py` — they import/derive (`src/sif/__init__.py:3`, `src/sif/cli/__init__.py:9`, `src/sif/config/constants.py:3,8`).

---

### `src/sif/cli/commands/watch.py` (CLI command)

**Analog:** itself — `_check_lifecycle_guards` is the established flag-guard style.

**Guard style to mirror** (`watch.py:482-509`):
```python
def _check_lifecycle_guards(
    *,
    detach: bool,
    stop: bool,
    log_file: str | None,
    install_service: bool,
    uninstall_service: bool,
) -> None:
    """Flag-combination guards for the lifecycle family (13-02/13-04)."""
    if detach and stop:
        raise click.ClickException("--detach and --stop are mutually exclusive.")
    if log_file is not None and not detach:
        raise click.ClickException("--log-file requires --detach.")
```

**Guard to add** (RESEARCH Pattern 4, user-facing):
```python
# inside _run_detach, before daemon.detach(...)
if not hasattr(os, "fork"):
    raise click.ClickException(
        "--detach requires POSIX fork support and is not available on Windows; "
        "run `sif watch` in the foreground instead."
    )
```
`os` is already imported (`watch.py:28`). The message names the cause (fork/POSIX) and the remedy (foreground watch), per the repo's remedy-hint culture. Add a `CliRunner` test alongside `tests/unit/cli/test_watch_cmd.py:335-355` (the flag-guard test class) that monkeypatches `os.fork` absence and asserts the message.

---

### `src/sif/utils/daemon.py` (utility)

**Analog:** `src/sif/search/vector.py:16-24` — library-level fail-fast `RuntimeError` with a remedy sentence:
```python
def __init__(self, db: sqlite3.Connection, embedding_dim: int = 768) -> None:
    """Initialize vector searcher with sqlite-vec."""
    self.db = db
    self.embedding_dim = embedding_dim
    self._vec_available = self._check_vec_extension()
    if not self._vec_available:
        raise RuntimeError(
            "sqlite-vec extension is not available. Install sqlite-vec to use vector search.",
        )
```

**Guard to add at the very top of `detach()` (before `os.pipe()` at `daemon.py:235`)**:
```python
if not hasattr(os, "fork"):
    raise RuntimeError(
        "detached mode requires POSIX fork (os.fork); use the foreground watch on Windows"
    )
```
Why first: `detach()` calls `os.pipe()` at line 235, `os.fork()` at 236, `os.setsid()` at 261, and a second `os.fork()` at 262; `select.select` on pipes and `os.killpg` at 375 are POSIX-only. Without the guard Windows surfaces a raw `AttributeError`. Existing detach tests (`tests/unit/utils/test_daemon.py:471-513`) already fake `daemon.os.fork`; add one test deleting `os.fork` (monkeypatch delattr) and asserting the `RuntimeError` message.

---

### `src/sif/models/__init__.py` (package export)

**Analog:** itself. Delete the dead import block (`:34-40`):
```python
from sif.models.search import (
    SearchOptions,
    SearchQuery,
    SearchResponse,
    SearchResult,
    SearchType,
)
```
and remove `SearchOptions`, `SearchQuery`, `SearchResponse`, `SearchResult`, `SearchType` from `__all__` (`:60-64`). Keep the remaining imports and `__all__` alphabetized (`pyproject.toml` isort rules; `__all__` is currently sorted).

---

### `src/sif/database/__init__.py` (package export)

**Analog:** itself. Delete line 6:
```python
from sif.database.migrations import MigrationManager
```
and remove `"MigrationManager"` from `__all__` (line 22).

---

### `src/sif/search/rrf.py` (utility)

**Analog:** itself. Delete the orphan function at `:112-122`:
```python
def compute_rrf_score(rank: int, k: int = 60) -> float:
    """Compute RRF score for a single rank."""
    return 1.0 / (k + rank)
```
Keep `RRFFusion` and the in-class scoring logic above it. `docs/api-reference.md:454,477-480` is the only referencing doc.

---

### `src/sif/config/constants.py` (config, optional)

**Analog:** itself. Optional removal of the now-orphaned constant (`:55`):
```python
# Database schema versions
CURRENT_SCHEMA_VERSION = 1
```
Only `migrations.py` and `test_migrations.py` use it; removing it with the dead layer is the research recommendation, but leaving it is harmless (zero config-surface change). Do not touch `APP_VERSION = __version__` (`:8`).

---

### `tests/conftest.py` (test fixture)

**Analog:** itself. Remove the dead import (`:24`):
```python
from sif.models.search import SearchOptions, SearchResult
```
and the three fixtures at `:387-440` (`sample_search_options`, `sample_search_result`, `sample_search_results`). `tests/unit/search/test_rrf.py` defines its own same-named fixture, so no other test depends on them. Preserve the color-hermetic block (`:25-57`) untouched — it is the matrix's determinism contract.

---

### `tests/test_docs.py` (test doc guard)

**Analog:** itself. If the pre-commit references are removed from docs, drop `"pre-commit install"` from `SKIP_COMMAND_PATTERNS` (`:44`) and update the description at `docs/testing.md:186` (RESEARCH says this is conditional). Leave the bandit VERIFY marker note (`docs/testing.md:217`) alone.

---

### `examples/quickstart.py` (example)

**Analog:** itself — existing example shells follow a `try: import ... except ImportError` structure (e.g. `:164-190`).

Replace the dead `MigrationManager` import/use (`:165-178`):
```python
from sif.database import DatabaseConnection, MigrationManager
...
migrations = MigrationManager(db)
migrations.run_migrations()
```
with `Database.init_schema()` (or drop the example section). Replace the dead `BM25SearchStrategy` example (`:246-260`):
```python
from sif.search import BM25SearchStrategy, SearchContext
```
with `sif.search.BM25Searcher` (the current import never resolves). Verify syntax with `python -m py_compile examples/quickstart.py`; `tests/test_docs.py` does not parse `examples/`.

---

### Docs family (doc; no code analog)

**Analogs:** the files themselves. Edit lists (file:line) are locked in RESEARCH "Deletion Inventory":

**Dead-layer docs**
- `docs/architecture.md:6, 298, 301, 685, 728` — remove `SearchStrategy`, `strategy.py`, `migrations.py` tree entries, and the `MigrationManager` paragraph.
- `docs/development.md:471, 495-500` — remove the `MigrationManager`/`CURRENT_SCHEMA_VERSION` bullet and rewrite "New Search Strategy" to `BM25Searcher`.
- `docs/models.md:479` — rewrite the `sif.models.search.SearchOptions` sentence.
- `docs/api-reference.md:230, 378, 397-400, 454, 477-480, 875-879` — remove/replace dead imports, the `SearchStrategy` example, and `compute_rrf_score`.
- `DESIGN.md:58, 106, 109` — remove `strategy.py`/`migrations.py` entries.

**pre-commit docs (clear VERIFY markers exactly where named — 3 markers, not 4)**
- `docs/testing.md:20, 22` (keep `:217` bandit marker).
- `docs/development.md:631, 655-658, 674, 691` (including the `make pre-commit` row and marker).
- `docs/contributing.md:386, 398`.

**Release/version docs**
- `docs/installation.md:78-82` (drop black, floors, add torch), `:148` (version sample → 1.1.2).
- `docs/development.md:575-600` — rewrite "Release Process": bump `_version.py`, changelog, tag push; the workflow builds and publishes (remove `twine upload` as the primary path).
- `docs/changelog.md` — add `## [1.1.2] - <date>`, update `[Unreleased]` compare link to `v1.1.2...HEAD`, add `[1.1.2]` link in the footer (`docs/changelog.md:last lines`).

**Changelog excerpt to mirror** (`docs/changelog.md:46-56`):
```markdown
## [1.1.1] - 2026-11-12

### Changed
- The release version is now single-sourced in `src/sif/_version.py`; ...

### Fixed
- Install, upgrade, and uninstall instructions and in-app remedy hints now name ...
```
Footer style (`docs/changelog.md` tail):
```markdown
[Unreleased]: https://github.com/zhangtaolab/sif/compare/v1.1.1...HEAD
[0.1.0]: https://github.com/zhangtaolab/sif/releases/tag/v0.1.0
[1.1.1]: https://github.com/zhangtaolab/sif/releases/tag/v1.1.1
[1.0.1]: https://github.com/zhangtaolab/sif/releases/tag/v1.0.1
```

**Hard rule:** `docs/cli-reference.md` and `docs/configuration.md` are generator-owned — never hand-edit them and do not run `make docs-generate` unless a CLI/Settings surface changed (it does not here).

---

### Deletions (13 files)

**Analog:** git history. Locked inventory from RESEARCH "Deletion Inventory":

| Path | Required companion edits |
|---|---|
| `src/sif/models/search.py` | `src/sif/models/__init__.py:34-40, 60-64`; `tests/conftest.py:24, 387-440` |
| `src/sif/search/strategy.py` | `tests/unit/test_search.py` (deleted with it) |
| `src/sif/database/migrations.py` | `src/sif/database/__init__.py:6, 22`; `examples/quickstart.py:165-178`; optional `src/sif/config/constants.py:55` |
| `tests/unit/test_search.py` | — |
| `tests/unit/database/test_migrations.py` | — |
| `tests/factories.py` | Verified unused (no `tests.factories` import) |
| `MagicMock/mock/{4398091296,4419046432,4419497200,4426075504}` | 4 identical SQLite blobs; `git rm` all four |
| `quick_test.py`, `simple_test.py`, `verify_imports.py` | Stale `docsift`-era scripts; `git rm` all three |

Delete the dead modules and their tests in the same plan so the suite collects and `fail_under=90` still applies. After deletion run: `ruff check src tests`, `ruff format --check src tests`, `ty check src/sif`, `pytest`.

## Shared Patterns

### Deterministic test environment (all new tests and CI)
**Source:** `tests/conftest.py:25-57`
```python
_COLOR_ENV_VARS = ("FORCE_COLOR", "CLICOLOR_FORCE", "NO_COLOR", "PY_COLORS", "TTY_COMPATIBLE")
for name in _COLOR_ENV_VARS:
    os.environ.pop(name, None)


@pytest.fixture(autouse=True)
def _hermetic_color_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Keep every test's color environment at the known-green baseline."""
    for var in _COLOR_ENV_VARS:
        monkeypatch.delenv(var, raising=False)
```
**Apply to:** the matrix run step (`env -u FORCE_COLOR NO_COLOR=1 uv run --frozen pytest`) and every new test. Do not re-introduce model downloads; CI embeddings use `ConceptEmbedder` (`tests/support/bench.py:40-60`).

### Error handling / remedy-hint culture
**Source:** `src/sif/cli/commands/watch.py:482-509` (CLI) and `src/sif/search/vector.py:16-24` (library).
**Apply to:** the two Windows guards. CLI boundary raises `click.ClickException(str(e))`; library boundary raises `RuntimeError`. Every message names the cause and the fix. No raw tracebacks on Windows.

### Validation (input/guard checks)
**Source:** `tests/test_version_identity.py` (TOML + file scanning) and `tests/test_docs.py:35-46, 293-311` (absence lists).
**Apply to:** all four new test modules. Text-level assertions only; no PyYAML, no new dev deps. Use `REPO_ROOT = Path(__file__).resolve().parents[1]` for cwd independence; use the `tomllib`/`_section` fallback for Python 3.10 cells.

### Release identity
**Source:** `tests/test_version_identity.py:39-94`; `src/sif/_version.py:3`; `src/sif/config/constants.py:3,8`; `src/sif/__init__.py:3`; `src/sif/cli/__init__.py:9`.
**Apply to:** `_version.py` bump, publish workflow tag gate, `tests/test_release_metadata.py`. Only `_version.py` may contain a literal.

### Subprocess invocation
**Source:** `src/sif/utils/service.py:206-219`; `tests/unit/utils/test_service.py:51-59`.
**Apply to:** `scripts/windows_smoke.py` and its unit tests. Explicit argv lists only (never `shell=True`), `capture_output=True, text=True, check=False, timeout=<bounded>`. The one existing `shell=True` call (`src/sif/cli/commands/index.py` pre-update command) is user-configured behavior and must not be used as a model.

### Quality gates and lock discipline
**Source:** `CLAUDE.md` "Common Development Commands"; `pyproject.toml:206-214`.
**Apply to:** every plan. Per task: `env -u FORCE_COLOR NO_COLOR=1 pytest -x -q --no-cov`, `ruff check src tests`, `ruff format --check src tests`. Per wave: full `pytest`, `ty check src/sif`, `uv lock --check`. The matrix must mirror these exactly; no `--no-cov` in CI.

### Generator-owned docs
**Source:** `.github/workflows/docs.yml:38-42` (diff gate) and `Makefile:71-74`.
**Apply to:** docs edits. Never hand-edit `docs/cli-reference.md` / `docs/configuration.md`; run `make docs-generate` only if a generated surface changed.

## No Analog Found

Files with no direct codebase precedent; the planner must use the RESEARCH recipes.

| File / element | Role | Data Flow | Reason | Use instead |
|---|---|---|---|---|
| `.github/workflows/publish.yml` | config (release) | event-driven | No release workflow exists; only `docs.yml` is present | RESEARCH Pattern 2 (verified `gh-action-pypi-publish` README) |
| `Makefile` `windows-smoke` target | config | request-response | No `hc` usage exists anywhere in the repo | RESEARCH Pattern 4 (verified `hc exec --help`) and live yoga probes |
| `pyproject.toml` `[tool.uv.index]` / `[tool.uv.sources]` | config | transform | No uv sources/index section exists yet | RESEARCH Pattern 3 (verified lock experiment) |
| `tests/test_ci_workflows.py` workflow-YAML guards | test | — | No YAML-guard tests exist; no PyYAML dependency | Text-level assertions following `tests/test_version_identity.py` |
| `scripts/windows_smoke.py` CLI smoke flow | utility | request-response | No CLI-smoke script exists; only doc/corpus generators | Script conventions from `scripts/generate_bench_fixture.py` + RESEARCH Pattern 4 assertion table |

## Metadata

**Analog search scope:** `.github/workflows/`, `Makefile`, `pyproject.toml`, `uv.lock`, `README.md`, `scripts/`, `src/sif/{cli,utils,database,indexing,search,models,config}/`, `tests/{,unit/{cli,utils,database,search},support}/`, `docs/`, `DESIGN.md`, `examples/`.
**Files scanned:** 42 target files plus 20 analog/reference files (all git-tracked, verified with `git ls-files`).
**Pattern extraction date:** 2026-11-13
