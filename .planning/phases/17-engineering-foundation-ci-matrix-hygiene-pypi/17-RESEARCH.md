# Phase 17: Engineering Foundation (CI Matrix + Hygiene + PyPI) - Research

**Researched:** 2026-11-13
**Domain:** GitHub Actions test matrix, uv/torch CPU dependency resolution, PyPI trusted publishing, Windows degradation smoke, repo hygiene
**Confidence:** HIGH — every recipe below was verified against official docs **and** executed locally (uv 0.13.7 lock experiments, live `hc` probes on yoga, registry/API reads). Manual UI steps (PyPI publisher registration) are the only MEDIUM-confidence part.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

#### CI topology (ENG-01)
- **D-01:** **Every push/PR runs the full 8-cell matrix** — py3.10, py3.11, py3.12, py3.13 × {ubuntu-latest, macos-latest}; full suite per cell, `fail_under=90` per cell. No PR-vs-push split, no nightly-only full runs. Strongest regression net; the 8×~5min cost is accepted. — **Reversibility:** reversible — workflow-file change only.
- **D-02:** **Dependency cache only** — uv/pip caches via `actions/cache`/setup-uv cache; NO HuggingFace model cache. CI tests use `ConceptEmbedder` (deterministic synthetic embeddings, Phase 16 D-01), so no model downloads occur. Linux cells install CPU torch via `--index https://download.pytorch.org/whl/cpu` (multi-GB CUDA default avoided). Do not assert exact transitive versions — py3.10 resolves torch 2.14.1 / rapidfuzz 3.14.5 / httpx2 2.14.0; py3.11+ resolves 2.15.0 / 3.14.6 / 2.16.0.
- **D-03:** **macOS coverage = macos-latest (arm64) only** — 8 cells total. Intel macOS (macos-13) deferred; research did not require it.
- **D-04:** **Concurrency: cancel-in-progress per ref** — superseded runs cancel; `fail-fast: false` so all cells report (Claude's discretion on exact YAML).

#### Windows smoke (ENG-02)
- **D-05:** **Committed script + Makefile target, run via hc** — the smoke is a repo-committed script (Python or PowerShell — Claude's discretion) plus a Makefile target, executed on demand via `hc exec --on yoga` / `hc run --on yoga --cwd 'D:\Github\SIF'`. The Windows project directory on yoga is `D:\Github\SIF`. Python is NOT preinstalled on yoga (Microsoft Store alias only) — `uv python install` first. NOT a GitHub Actions windows-latest job. — **Reversibility:** reversible.
- **D-06:** **CLI-level degradation assertions** — assert `index`/`search`/`status` (and watch/service paths where reachable) give clear errors or safe degradation when `fcntl` / systemd / fork semantics are absent; assert the degradation is honest (no mass-delete on missing root, no silent lock bypass). NOT the full pytest suite, NOT a pytest marker subset. The target is the user-visible surface, not internal semantics.
- **D-07:** **Trigger: manual/on-demand + pre-release** — documented in install/release docs; run before PyPI publishes. No per-PR or weekly schedule (yoga is a user machine).

#### Repo hygiene (ENG-04)
- **D-08:** **Delete dead layers outright** — `MigrationManager`, `src/sif/models/search.py`, `src/sif/search/strategy.py` are deleted; git history is the archive. Their tests are deleted/moved in the same plan so the suite collects. — **Reversibility:** costly — test-only layers referenced by multiple test modules; deletion is recoverable via git but re-wiring later means re-adding files.
- **D-09:** **Hygiene bundle is zero-risk only** — dead layers + orphan `compute_rrf_score` export + phantom Makefile `pre-commit` target + `black` dev dependency. No repo-wide zero-reference scan (false-positive risk); no behavior changes.
- **D-10:** **pre-commit: delete target + doc references, clear VERIFY markers** — `make pre-commit` and its doc mentions are removed; the 4 `<!-- VERIFY: -->` markers about the nonexistent `.pre-commit-config.yaml` are cleared. Do NOT create a `.pre-commit-config.yaml` (make ci already covers format/lint/type/test).
- **D-11:** **Extras/classifier locking (research-locked)** — `embed` floor `sentence-transformers>=5.4.1`; `all` floor `llama-cpp-python>=0.3.35`; `fastapi`/`uvicorn` remain core deps; `dev` drops black; 3.13 classifier added only after the matrix is green.
- **D-12:** **Tracked junk audit** — `git ls-files` audit for junk (current scan found none matching `.DS_Store`/`__pycache__`/coverage/logs); removals limited to genuinely tracked junk, if any.

#### PyPI release (ENG-03)
- **D-13:** **Publish version 1.1.2** — patch release of current behavior (`src/sif/_version.py` is 1.1.1 today); proves the release pipeline without committing to v1.2 API. — **Reversibility:** one-way — a published version number is permanent (yanking is possible but visible and does not free the number).
- **D-14:** **Tag push (v*) auto-triggers publishing** — one workflow: build job (Linux-only, `pypa/gh-action-pypi-publish@release/v1`), TestPyPI upload first, then PyPI upload; trusted publishing (GitHub environment) + PEP 740 attestations. **README `<!-- mcp-name: io.github.zhangtaolab/sif -->` marker lands BEFORE the first publish.** Version single-sourced across `pyproject.toml`, `src/sif/_version.py`, `src/sif/__init__.py`, `src/sif/cli/__init__.py`, `src/sif/config/constants.py`, `src/sif/mcp/protocol.py`. — **Reversibility:** one-way for the published artifact and the mcp-name marker (Registry listing depends on it).
- **D-15:** **TestPyPI on every tag release** — same workflow, sequential TestPyPI → PyPI. No separate manual gate; the tag is the release intent.

### Claude's Discretion
- Workflow YAML structure (job names, matrix include/exclude, concurrency group, setup-uv SHA pin, cache keys)
- Windows smoke script language and exact assertion set/messages; Makefile target name
- Dead-layer test cleanup mechanics (delete vs relocate assertions)
- PyPI workflow environment name, build-job separation, artifact checks
- Exact tracked-junk audit procedure
- Whether `Makefile` `ci` target gains the new test workflow parity

### Deferred Ideas (OUT OF SCOPE)
- Intel macOS runner (macos-13) coverage — revisit if an Intel-only wheel bug appears.
- GitHub-hosted windows-latest smoke job — rejected for v1.2 (yoga hc is the user's stated path); full Windows support is v2.
- Repo-wide zero-reference/private-function scan — deferred (false-positive risk); named zero-risk items only.
- Info-findings sweep remainder (v1.1 ledgers 11-WR-04/IN-05, 14-IN-01/IN-02, 15-IN-01/IN-03..07, 16-IN-01..06) — later cleanup pass, not this phase.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| ENG-01 | Contributor can run the full test suite on a green CI matrix (py3.10–3.13 × ubuntu/macos, full suite per cell, fail_under=90, CPU torch on Linux, tolerant of both py3.10/3.11+ resolution fleets) on every push/PR. | Verified workflow recipe (Pattern 1) + verified `uv.lock` CPU-torch recipe producing the two torch fleets (Pattern 3) + runner facts (`macos-latest` = macOS 26 arm64, `ubuntu-latest` = 24.04 x64) + cache/concurrency settings (Pitfalls 1–4, 16). |
| ENG-02 | Contributor can verify Windows graceful degradation via a CI smoke run on hc remote yoga (uv python install first; assert fork/systemd/flock degrade honestly — not full Windows support). | Live yoga probes (uv 0.13.1, `uv python install 3.12` → 3.12.15 verified, repo at `D:\Github\SIF` on main@7652bb0, clean) + exact degradation sites and messages (`locking.py:57-63`, `drift.py:84-88`, `incremental.py:109-115/200-206`, `daemon.py:236` unguarded `os.fork`, `service.py:84/199-203`) + smoke script/Makefile design (Pattern 4). |
| ENG-03 | Maintainer can publish `docsif` to PyPI via trusted publishing (README `<!-- mcp-name: io.github.zhangtaolab/sif -->` marker before publish; TestPyPI dry run; version single-sourced; PEP 740 attestations). | Publish workflow recipe (Pattern 2), trusted-publisher registration facts (existing PyPI project vs TestPyPI pending; exact fields), attestation verification command, version identity already enforced by `tests/test_version_identity.py`, README marker boundary rules (Pattern 5, Pitfalls 5–11). |
| ENG-04 | Contributor works in a hygienic repo (dead `MigrationManager` + `models/search.py` + `search/strategy.py` quarantined/deleted; tracked junk removed; Makefile/extras/pre-commit cleaned, black dropped, fastapi/uvicorn kept as core deps; 3.13 classifier added only when green). | Complete reference inventory with file:line (Deletion Inventory), tracked-junk audit (`MagicMock/` 4 blobs + 3 stale scripts), exact pyproject/Makefile/doc edit lists, and the 3-not-4 VERIFY-marker correction (Pitfalls 18–20). |
</phase_requirements>

## Summary

This phase is four mostly independent workstreams with one shared dependency: the repo must be hygienic and locally green before the matrix is meaningful, the matrix must be green before the 3.13 classifier claims support, and the release pipeline must carry the README marker before the tag is built. The research below converts the locked decisions into executable recipes and corrects four facts that would otherwise derail the plan:

1. **Version identity is already solved** — all six version surfaces derive from `src/sif/_version.py` and `tests/test_version_identity.py` pins that invariant. Phase 17 only bumps `_version.py` to `1.1.2` and updates changelog/docs; no re-wiring is needed.
2. **The CPU-torch CI requirement needs a `pyproject.toml` change beyond floors**: `[tool.uv.sources]` applies only to *direct* dependencies (verified experimentally — adding the source alone left `uv.lock` resolving CUDA torch from PyPI). Torch must be declared in the `embed`/`all` extras so the marker-scoped CPU index takes effect. With that change the lock resolves exactly the two fleets the milestone names: py3.10 → `torch 2.14.1+cpu`, py3.11+ → `torch 2.15.0+cpu` on Linux, and drops every `nvidia-*`/`triton` package.
3. **`docsif` already exists on PyPI but has no attestations** — 1.0.1 is the latest release (1.1.x was never published) and no provenance is served for its wheel. The trusted publisher must therefore be added to the **existing** project (project → Publishing), not via a pending publisher. TestPyPI returns 404 for `docsif`, so TestPyPI uses the **pending publisher** flow.
4. **Windows degradation is not uniformly honest today**: `sif watch --detach` reaches `os.fork()` unguarded (`src/sif/utils/daemon.py:236`) and dies with `AttributeError`; `--install-service` already fails cleanly through `_gate_manager` (systemctl missing). The smoke needs one small guard (detach) to assert honest messages, plus the already-present flock warning and missing-root guards.

Also corrected from CONTEXT: there are **3** `<!-- VERIFY -->` markers about `pre-commit`, not 4 (the fourth is about `bandit` and is out of scope), and tracked junk is concrete: four identical SQLite blobs under `MagicMock/` plus three stale `docsift`-era root scripts.

**Primary recommendation:** Land in this order: (1) hygiene deletions + extras/lock + local suite green; (2) 8-cell matrix workflow; (3) prove green then add the 3.13 classifier; (4) README marker + 1.1.2 version/changelog; (5) publish workflow + trusted-publisher registration + TestPyPI→PyPI release; (6) Windows smoke script + detach guard + run on yoga. The recipes in `## Architecture Patterns` are copy-ready.



## Project Constraints (from CLAUDE.md)

Directives from `./CLAUDE.md` that constrain this phase:

- Quality gates after every plan: `ruff check src tests`, `ruff format --check src tests`, `pytest` (suite has `fail_under=90`).
- Python 3.10+; `list[str] | None` unions; line length 100; mccabe ≤10; fully annotated; ruff isort order stdlib/third-party/first-party; two blank lines after imports.
- Type check with `ty check src/sif` (not mypy).
- `docs/cli-reference.md` and `docs/configuration.md` are **generator-owned** (`make docs-generate` + CI diff gate) — never hand-edit them.
- Error-handling culture: user-facing failures are `click.ClickException(str(e))`; remedy hints name cause + fix. Windows messages must follow this.
- GSD workflow: use `/gsd-execute-phase` for planned work; run the full quality suite before marking a plan done.
- Logging via `logger = get_logger(__name__)` (stderr), not print.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| 8-cell test execution | CI (GitHub Actions runners) | — | The suite is the product under test; runners own OS/Python provisioning. |
| CPU vs CUDA torch resolution | Packaging config (`pyproject.toml` + `uv.lock`) | CI (consumes `--frozen` lock) | Resolution belongs in the lock; CI must not patch installed packages after sync. |
| Dependency cache | CI (setup-uv cache) | — | Keyed by `uv.lock`; no model cache (tests are model-free). |
| Release artifact build | CI build job (Linux) | — | `gh-action-pypi-publish` is Linux-only; build must be low-privilege and separate. |
| Publishing identity | External: PyPI OIDC + GitHub environment | CI publish jobs | Credentialless; job-scoped `id-token: write`; environment restricts which workflow can mint tokens. |
| Version identity | Package source (`src/sif/_version.py`) | Build job tag check | Single literal; hatchling reads it; all runtime surfaces derive. |
| README ownership marker | Package metadata (README → PyPI description) | Registry (Phase 22 consumes) | The marker must be in the README at build time; PyPI serves it as the description. |
| Windows degradation behavior | Application code (`utils/daemon.py`, `cli/commands/watch.py`, `database/locking.py`) | Smoke script (asserts surface) | Guards belong in product code; the smoke only observes CLI behavior. |
| Windows smoke orchestration | Repo `scripts/` + Makefile | `hc` remote host | Reproducible committed script; yoga is execution infrastructure, not CI. |
| Dead-code/junk removal | Repo source tree + docs | — | No runtime state is involved; git history is the archive. |

## Standard Stack

### Core

| Tool / Action | Version | Purpose | Why Standard |
|---------------|---------|---------|--------------|
| `actions/checkout` | **v7** (`v7.0.1`, 2026-07-20) | Clone repo in job | Current major; `v4` (used by `docs.yml`) is outdated but can stay in the untouched docs workflow. Tag verified via GitHub API. `[VERIFIED: GitHub API releases/latest actions/checkout]` |
| `astral-sh/setup-uv` | **v10.3.3** (2026-10-28), SHA-pin `68559e99cc807c1eb7e9238fd43a15bba460eec2` | Install uv + configure cache | SHA verified by `git ls-remote`; matches prior research. `python-version` only sets `UV_PYTHON` — it does **not** install Python; add `uv python install`. `[VERIFIED: git ls-remote tag v10.3.3 + setup-uv README]` |
| `uv` | 0.13.7 local; 0.13.1 on yoga | Sync, lock, run, build | Lock is tracked (`uv.lock`, 524 KB, `uv lock --check` passed). `uv sync --frozen --extra dev --extra embed` is the CI install. `[VERIFIED: local uv 0.13.7; yoga probe]` |
| `pypa/gh-action-pypi-publish` | `@release/v1` (v1.14.3, 2026-10-20; tag SHA `aef6c9b6e301dc803e1bc9133e9ce67ae9b0906b`) | Trusted publishing to PyPI/TestPyPI | Official documented channel; Docker action, Linux only; one invocation per job; cannot run in reusable workflows; attestations default `true`; `skip-existing` default `false`. `[VERIFIED: raw release/v1 README + action.yml]` |
| `actions/upload-artifact` | **v7** (`v7.0.2`) | Build job → publish jobs | Current major. `[VERIFIED: GitHub API releases/latest]` |
| `actions/download-artifact` | **v8** (`v8.0.2`) | Publish jobs receive `dist/` | Current major. `[VERIFIED: GitHub API releases/latest]` |
| pytest | 9.0.3 (locked) | Test runner | `pyproject.toml` `addopts` includes `--cov=src/sif ...`; `fail_under=90` then applies per cell automatically. `[VERIFIED: uv.lock:1703-1704 + pyproject.toml:206-214]` |
| pytest-cov | 7.1.0 (locked) | Coverage gate | Honors `[tool.coverage.report] fail_under = 90`. `[VERIFIED: uv.lock:1735-1736 + pyproject.toml:213-214]` |

### Supporting

| Tool | Version | Purpose | When to Use |
|------|---------|---------|-------------|
| `hc` (herdr-core) | 0.1.21 local; yoga agent 0.1.20 | Non-interactive remote execution | `hc exec --on yoga --cwd 'D:\Github\SIF' ARGV...` — argv only (no shell), prints output exactly, exits with the program's code, `--timeout` default 60/max 600. `[VERIFIED: hc exec --help + hc machine ls]` |
| `gh` CLI | authed as `forrestzhang`, scopes `repo, workflow, read:org` | Create environments, inspect repo | `gh api repos/zhangtaolab/sif/environments` currently returns `total_count: 0`. `[VERIFIED: local gh]` |
| `twine` | local install present; `uvx twine` in CI | Build metadata check | `uvx twine check dist/*` in the build job. `[VERIFIED: local command -v twine]` |
| `pypi-attestations` | use via `uvx` (do not add as project dep) | Verify PEP 740 attestations | `pypi-attestations verify pypi --repository https://github.com/zhangtaolab/sif pypi:docsif-1.1.2-py3-none-any.whl`. Official PyPI docs command. `[CITED: docs.pypi.org/attestations/consuming-attestations/]` |
| `uv python install` | uv-managed | Bootstrap CI + yoga | Verified on yoga: `uv python install 3.12` → `Installed Python 3.12.15 in 38ms`; `uv run --python 3.12 --no-project python --version` → `Python 3.12.15`. `[VERIFIED: live yoga probe]` |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| setup-uv + `uv sync --frozen` | `actions/setup-python` v7.1.0 + pip | setup-python is fine but ignores `uv.lock`; the project ships a lock and the milestone wants fleet-tolerance proven through it. Keep one style. |
| `[tool.uv.sources]` + direct torch extra + lock | CI step `uv pip install --index https://download.pytorch.org/whl/cpu ...` after sync | The post-sync install would first download CUDA torch (multi-GB) unless `--no-install-package torch` is used — fragile. Lock-level source is deterministic and works with `--frozen`. |
| Two publish jobs (TestPyPI, PyPI) | One job invoking the action twice | Action explicitly does not support multiple invocations per job; one publish job per index. |
| Text-level workflow assertions in pytest | Add PyYAML to `dev` and parse YAML | A new dev dep (lock churn) for a guard that only needs to detect matrix regression; text assertions are sufficient and dependency-free. |
| `pypi-attestations` as a dev dep | `uvx pypi-attestations` on demand | Attestation verification is a release-time human step, not a suite dependency. |
| `skip-existing: true` on PyPI | Unconditional upload | A re-run of a partially failed release would silently no-op on PyPI; only TestPyPI should skip existing files. |

**Installation (Phase 17 pyproject delta — verified with uv 0.13.7):**

```bash
uv lock                                   # after the pyproject edits below
uv lock --upgrade-package torch           # align PyPI torch to the 2.14.1/2.15.0 fleet
uv lock --check                           # CI/executor gate
uv sync --frozen --extra dev --extra embed
```

## Package Legitimacy Audit

> Phase 17 installs **no new external packages**. It removes `black`, raises floors on two existing optional deps, and makes `torch` an explicit (already-transitive) extra. The seam was still run on the affected names.

| Package | Registry | Age (latest release) | Downloads | Source Repo | Verdict | Disposition |
|---------|----------|----------------------|-----------|-------------|---------|-------------|
| `sentence-transformers` | PyPI | 2026-11-11 (latest 6.3.0; floor pins 5.4.1) | unknown | sbert.net | SUS (`too-new`, `unknown-downloads`) | Approved — pre-existing locked dep; floor bump only, no first-time install |
| `torch` | PyPI | 2026-10-28 (latest 2.15.0) | unknown | pytorch.org | SUS (`too-new`, `unknown-downloads`) | Approved — already transitive via ST; becomes a direct extra declaration for uv sources |
| `llama-cpp-python` | PyPI | 2026-10-01 (0.3.36) | unknown | github.com/abetlen/llama-cpp-python | SUS (`unknown-downloads`) | Approved — pre-existing `all` dep; floor bump only |
| `pypi-attestations` | PyPI | 2026-11-02 | unknown | github.com/pypi/pypi-attestations | SUS (`too-new`, `unknown-downloads`) | Approved for `uvx` verification only — never a project dependency |
| `pyyaml` | PyPI | 2025-09-25 | unknown | pyyaml.org | SUS (`unknown-downloads`) | Not used — workflow tests stay dependency-free |

**Packages removed:** `black` (dev), plus its transitive `mypy-extensions`, `pathspec`, `pytokens` — removing it from `dev` + deleting `[tool.black]` and refreshing the lock removes all four (verified: `uv lock` printed `Removed black v26.3.1` etc.).
**Packages flagged suspicious [SUS]:** none require a first-time installation checkpoint because every runtime name is already in the v1.1 environment. The SUS verdicts are driven by missing download metadata and freshly published latest versions, not by unknown provenance; do not add install checkpoints for pre-existing deps, but do not introduce new packages in this phase.

## Architecture Patterns

### System Architecture Diagram

```
                    ┌──────────────────────────────────────────────┐
 push / pull_request│              GitHub Actions                  │
───────────────────▶│  test-matrix.yml                             │
                    │  matrix: 4 pythons × {ubuntu, macos}          │
                    │    checkout ─▶ setup-uv(SHA) ─▶ uv python    │
                    │    install ─▶ uv sync --frozen --extra       │
                    │    dev --extra embed ─▶ pytest (fail_under=90)│
                    │         ▲                                    │
                    │         │ uv.lock (torch source per platform)│
                    └─────────┼────────────────────────────────────┘
                              │
                     uv.lock: linux ← download.pytorch.org/whl/cpu
                              linux py3.10 → torch 2.14.1+cpu
                              linux py3.11+ → torch 2.15.0+cpu
                              mac/win       → PyPI torch (CPU-only)

 tag push v*        ┌──────────────────────────────────────────────┐
───────────────────▶│  publish.yml                                 │
                    │  build (ubuntu, contents:read)               │
                    │    checkout ─▶ setup-uv ─▶ tag↔version check │
                    │    ─▶ uv build ─▶ twine check ─▶ artifact    │
                    │  publish-testpypi (environment testpypi,     │
                    │    id-token:write) ─▶ download artifact      │
                    │    ─▶ gh-action-pypi-publish(repository-url) │
                    │  publish-pypi (environment pypi,             │
                    │    id-token:write)    ─▶ download artifact   │
                    │    ─▶ gh-action-pypi-publish                 │
                    └───────────────┬──────────────────────────────┘
                                    │ OIDC (no tokens)
                                    ▼
                          PyPI / TestPyPI ── PEP 740 attestations
                                    │
                                    ▼
                          PyPI JSON description contains
                          <!-- mcp-name: io.github.zhangtaolab/sif -->
                                    │
                                    ▼
                             MCP Registry (Phase 22)

 manual/pre-release ┌──────────────────────────────────────────────┐
───────────────────▶│  make windows-smoke                          │
                    │  hc exec --on yoga --cwd 'D:\Github\SIF'     │
                    │    uv python install ─▶ uv sync --frozen     │
                    │    ─▶ uv run python scripts/windows_smoke.py │
                    │  asserts: BM25 index/search/status work;     │
                    │    flock warning; missing-root preserved;    │
                    │    detach/service refuse with clear messages │
                    └──────────────────────────────────────────────┘
```

### Recommended Project Structure (new/modified)

```
.github/workflows/
├── docs.yml                 # existing — unchanged (docs gate precedent)
├── test-matrix.yml          # NEW: 8-cell full-suite matrix
└── publish.yml              # NEW: tag-triggered TestPyPI → PyPI
scripts/
└── windows_smoke.py         # NEW: CLI degradation assertions (Python)
tests/
├── test_ci_workflows.py     # NEW: matrix/publish YAML guards (text-level)
├── test_hygiene.py          # NEW: dead imports gone, Makefile/pyproject hygiene
├── test_windows_smoke_script.py  # NEW: message-matcher unit tests
├── test_version_identity.py # existing — already pins single-sourcing
└── unit/...                 # DELETE test_search.py, database/test_migrations.py,
                             #        factories.py (unused)
Makefile                     # remove pre-commit; add windows-smoke
pyproject.toml               # floors, torch direct dep, drop black, uv sources/index
uv.lock                      # refreshed (CPU torch, no black/nvidia/triton)
README.md                    # add mcp-name marker before first publish
docs/                        # changelog + release docs + dead-layer references
```

### Pattern 1: 8-cell test matrix workflow (`.github/workflows/test-matrix.yml`)

Verified inputs: `[VERIFIED: setup-uv v10.3.3 README]`, `[VERIFIED: runner-images README]`, `[VERIFIED: uv sync --help; local uv.lock]`.

```yaml
name: Test Matrix

on:
  push:
  pull_request:

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

Notes:
- `'3.10'` must be quoted or YAML parses it as `3.1`.
- `fail_under=90` comes from `pyproject.toml:213-214`; never pass `--no-cov`.
- `macos-latest` = **macOS 26 Arm64**; `ubuntu-latest` = **Ubuntu 24.04 x64** (locked D-03 satisfies arm64-only coverage). `[VERIFIED: runner-images README]`
- `cache-suffix` prevents concurrent matrix jobs from racing the same cache key (setup-uv FAQ recommends a suffix when resolution differs; also avoids 409 save collisions). `[VERIFIED: setup-uv README]`
- `env -u FORCE_COLOR` is bash syntax; both hosted ubuntu and macOS default to bash.
- Optional (Claude's discretion): add one `lint` job on `ubuntu-latest`/py3.12 running `uv run --frozen ruff check src tests`, `ruff format --check src tests`, `ty check src/sif`. Not required by ENG-01.

### Pattern 2: Publish workflow (`.github/workflows/publish.yml`)

Verified against `[VERIFIED: gh-action-pypi-publish release/v1 README + action.yml]` and `[CITED: packaging.python.org GitHub Actions publishing guide]`.

```yaml
name: Publish

on:
  push:
    tags: ['v*']

permissions:
  contents: read

jobs:
  build:
    name: Build distributions
    runs-on: ubuntu-latest
    timeout-minutes: 15
    steps:
      - uses: actions/checkout@v7

      - name: Install uv
        uses: astral-sh/setup-uv@68559e99cc807c1eb7e9238fd43a15bba460eec2 # v10.3.3
        with:
          python-version: '3.12'
          enable-cache: true
          cache-dependency-glob: uv.lock

      - name: Install Python
        run: uv python install 3.12

      - name: Verify tag matches src/sif/_version.py
        run: |
          VERSION="$(python3 -c "import runpy; print(runpy.run_path('src/sif/_version.py')['__version__'])")"
          test "v${VERSION}" = "${GITHUB_REF_NAME}" || {
            echo "tag ${GITHUB_REF_NAME} does not match version ${VERSION}"
            exit 1
          }

      - name: Build
        run: uv build

      - name: Check metadata
        run: uvx twine check dist/*

      - name: Upload distributions
        uses: actions/upload-artifact@v7
        with:
          name: dist
          path: dist/
          if-no-files-found: error

  publish-testpypi:
    name: Publish to TestPyPI
    needs: build
    runs-on: ubuntu-latest
    environment:
      name: testpypi
      url: https://test.pypi.org/p/docsif
    permissions:
      id-token: write
    steps:
      - uses: actions/download-artifact@v8
        with:
          name: dist
          path: dist
      - name: Publish to TestPyPI
        uses: pypa/gh-action-pypi-publish@release/v1
        with:
          repository-url: https://test.pypi.org/legacy/
          skip-existing: true

  publish-pypi:
    name: Publish to PyPI
    needs: publish-testpypi
    runs-on: ubuntu-latest
    environment:
      name: pypi
      url: https://pypi.org/p/docsif
    permissions:
      id-token: write
    steps:
      - uses: actions/download-artifact@v8
        with:
          name: dist
          path: dist
      - name: Publish to PyPI
        uses: pypa/gh-action-pypi-publish@release/v1
```

Notes:
- `id-token: write` is job-scoped on publish jobs only; the build job stays at `contents: read` (official advice: never workflow-global). `[VERIFIED: gh-action README]`
- Attestations are ON by default for trusted publishing; do not disable.
- Download into `dist/` so the action's default `packages-dir: dist` finds the files.
- Two publish jobs because the action cannot be invoked twice in one job.
- `skip-existing: true` on TestPyPI only (tag re-run after a PyPI failure would otherwise 400 on duplicate files).
- Do **not** add required reviewers to the `pypi` environment if the locked "tag = release intent" (D-15) is to hold; the environment still scopes which workflow may mint tokens.

### Pattern 3: CPU torch via uv index/sources (verified recipe)

`[tool.uv.sources]` does **not** apply to transitive dependencies — verified locally: adding only the index/source left `uv.lock` resolving `torch 2.11.0` from PyPI with all `nvidia-*` deps. Declaring `torch` in the extras fixes it. `[VERIFIED: uv 0.13.7 lock experiments in /tmp; uv PyTorch guide]`

```toml
[project.optional-dependencies]
embed = [
    "sentence-transformers>=5.4.1",
    "torch",
    "modelscope>=1.36.0",
    "numpy>=1.24.0",
]
all = [
    "sentence-transformers>=5.4.1",
    "torch",
    "llama-cpp-python>=0.3.35",
    "modelscope>=1.36.0",
    "numpy>=1.24.0",
    "openai>=2.0.0",
]

[[tool.uv.index]]
name = "pytorch-cpu"
url = "https://download.pytorch.org/whl/cpu"
explicit = true

[tool.uv.sources]
torch = [
  { index = "pytorch-cpu", marker = "sys_platform == 'linux'" },
]
```

Verified lock outcome after `uv lock && uv lock --upgrade-package torch` (temp-dir copy of the real project, uv 0.13.7):

| Platform / Python | Resolved torch | Source |
|---|---|---|
| linux, py3.10 | `2.14.1+cpu` | `https://download.pytorch.org/whl/cpu` |
| linux, py3.11–3.13 | `2.15.0+cpu` | `https://download.pytorch.org/whl/cpu` |
| macOS / Windows, py3.10 | `2.14.1` | PyPI (CPU-only wheels on those platforms) |
| macOS / Windows, py3.11+ | `2.15.0` | PyPI |

The same experiment removed `nvidia-cusparse`, `nvidia-cusparselt-cu13`, `nvidia-nccl-cu13`, `nvidia-nvjitlink`, `nvidia-nvshmem-cu13`, `nvidia-nvtx`, `triton`, and `black` from the lock. CPU-index torch 2.14.1/2.15.0 wheels exist for cp310–cp315 on manylinux x86_64/aarch64 (verified on the index listing). `[VERIFIED: local uv lock experiment + download.pytorch.org/whl/cpu listing]`

**Decision for the planner:** run the source+extras change, then `uv lock --upgrade-package torch`. Without the upgrade step macOS/Windows stay on the stale 2.11.0 while Linux moves to 2.14.1/2.15.0; the milestone explicitly names the 2.14.1/2.15.0 fleets, so aligning is preferable. If the planner prefers minimal churn, keep 2.11.0 everywhere — but then the lock no longer represents the documented fleet, and the "tolerate both fleets" criterion is not actually exercised.

### Pattern 4: Windows smoke script + Makefile target

Verified invocation shape: `hc exec --on yoga --cwd 'D:\Github\SIF' ARGV...` (argv only, no shell; `--timeout` max 600). `[VERIFIED: hc exec --help]`

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

Preflight facts: yoga has `uv 0.13.1`, git at `C:\Program Files\Git\cmd\git.exe`, repo `D:\Github\SIF` (remote `https://github.com/zhangtaolab/SIF.git`, currently `main@7652bb0`, clean). `uv python install 3.12` is verified working (3.12.15). The checkout is **stale relative to the phase branch** — the operator must sync it to the commit under test (or the target must add a `git fetch`/`checkout` step); the script should print `git rev-parse HEAD` and refuse to claim a pass without a clean tree matching the expected commit. `[VERIFIED: live yoga probes 2026-11-13]`

Smoke assertions (CLI-level, all subprocess argv lists, `SIF_DB_PATH` pointed at a temp dir):

| # | Command | Assertion | Source of truth |
|---|---------|-----------|-----------------|
| 1 | `sif --version` | exit 0, contains `sif, version 1.1.2` | `src/sif/cli/main.py:57`, `tests/test_version_identity.py:90-94` |
| 2 | `sif collection add <tmpdir> --name smoke` | exit 0 | `src/sif/cli/commands/collection.py:27-29` (path is positional) |
| 3 | `sif index update` | exit 0; stdout `Index updated:` + `Added: 1`; stderr contains `fcntl unavailable on this platform; index lock disabled` and `WAL + busy_timeout still protect database integrity` | `src/sif/database/locking.py:57-63`; `src/sif/cli/commands/index.py:53-59` |
| 4 | `sif search search needle --json` | exit 0; stdout parses as JSON; one result for the seeded doc | `src/sif/cli/commands/search.py:429,470` (BM25 — **not** `query`) |
| 5 | `sif status` | exit 0; output contains `Index Status`, `Documents`, and the doc count | `src/sif/cli/main.py:165-224` |
| 6 | delete the docs dir → `sif index update` | exit 0; `Removed: 0`; stderr contains `Collection root` + `does not exist; skipping update (all documents preserved)` | `src/sif/indexing/drift.py:84-88`; `incremental.py:109-115, 200-206` |
| 7 | `sif watch --detach` | exit != 0; message names the cause (fork/POSIX) and the fix (run foreground) — **requires the guard below** | `daemon.py:236` (`os.fork` unguarded), `watch.py:623-626` |
| 8 | `sif watch --install-service` | exit != 0; message contains `systemctl` + `watch service` (current behavior is honest via `_gate_manager`) | `service.py:84, 199-203, 251` |

Required guard for assertion 7 — add at the CLI boundary and keep a library guard:

```python
# src/sif/cli/commands/watch.py (inside _run_detach, before daemon.detach)
if not hasattr(os, "fork"):
    raise click.ClickException(
        "--detach requires POSIX fork support and is not available on Windows; "
        "run `sif watch` in the foreground instead."
    )
```

```python
# src/sif/utils/daemon.py (top of detach())
if not hasattr(os, "fork"):
    raise RuntimeError(
        "detached mode requires POSIX fork (os.fork); use the foreground watch on Windows"
    )
```

Why this specific site: `detach()` calls `os.pipe()`, then `os.fork()` at line 236, `os.setsid()` at 261, and a second `os.fork()` at 262; `select.select` on pipes and `os.killpg` (line 375) are also POSIX-only. Without a guard the CLI surfaces a raw `AttributeError` traceback, which violates the "clear platform message" criterion.

Do **not** run `sif search query` in the smoke: the hybrid subcommand loads an embedder (`search.py:767,857`), which would download a model on the user's machine (forbidden by D-02's no-model-cache premise and D-07's user-machine constraint).

### Pattern 5: README marker + release ordering

Marker (exact, from locked D-14 and registry docs): put this on its own line near the top of `README.md` (after line 1's generator comment is fine):

```markdown
<!-- mcp-name: io.github.zhangtaolab/sif -->
```

Verified registry rules: PyPI ownership reads an `mcp-name: $SERVER_NAME` string from the package README (which becomes the PyPI description); it may be hidden in a comment but must match `server.json` exactly and must be followed by a boundary (newline, whitespace, HTML tag, or `-->`); a trailing period breaks the match. `[VERIFIED: MCP registry package-types docs]`

Release order (hard constraints):
1. Land marker + `_version.py` → `1.1.2` + changelog + docs updates on the branch.
2. Merge to the release branch; wait for the 8-cell matrix green on that commit.
3. Add the 3.13 classifier (only now) and re-run the suite.
4. Push tag `v1.1.2` → publish workflow builds from the tagged tree (README marker is baked into the description at build time).
5. TestPyPI publish → PyPI publish.
6. Verify: PyPI page shows 1.1.2 + attestations; `uvx pypi-attestations verify pypi --repository https://github.com/zhangtaolab/sif pypi:docsif-1.1.2-py3-none-any.whl`; scratch-venv install from TestPyPI (`uv pip install --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple docsif==1.1.2`) and from PyPI.

Manual prerequisites (maintainer, cannot be scripted):
- Create GitHub environments `pypi` and `testpypi` (currently none). `gh api --method PUT repos/zhangtaolab/sif/environments/pypi` / `.../testpypi`.
- PyPI **existing project** `docsif` → `https://pypi.org/manage/project/docsif/publishing/`: owner `zhangtaolab`, repository `sif`, workflow `publish.yml`, environment `pypi`. `[VERIFIED: docs.pypi.org/trusted-publishers/adding-a-publisher/]`
- TestPyPI **pending publisher** (project does not exist): `https://test.pypi.org/manage/account/publishing/`: project name `docsif`, owner `zhangtaolab`, repository `sif`, workflow `publish.yml`, environment `testpypi`. A pending publisher does not reserve the name until first use. `[VERIFIED: docs.pypi.org/trusted-publishers/creating-a-project-through-oidc/; TestPyPI 404 for docsif]`

### Anti-Patterns to Avoid

- **Patching torch after sync** (`uv sync` then `pip install --index cpu torch`): downloads CUDA torch first, defeating D-02.
- **Workflow-global `id-token: write`**: grants OIDC to the build job and every step; job-scope only the publish jobs.
- **One publish job calling the action twice**: unsupported; use two jobs.
- **`skip-existing: true` on PyPI**: hides a partial-release retry; keep it TestPyPI-only.
- **Tagging before the matrix is green**: publishes an unverified artifact; the tag is permanent.
- **Hand-editing generated docs** (`docs/cli-reference.md`, `docs/configuration.md`): CI diff gate fails; use `make docs-generate`.
- **A Windows smoke that only exercises the happy path**: it will pass while `watch --detach` crashes; assert the refusal paths.
- **Adding `pyyaml` to parse workflow YAML in tests**: unnecessary dependency; text assertions suffice.
- **Running `sif search query` on yoga**: model download on a user machine.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Python version provisioning in CI | Custom pyenv/apt installs | `uv python install ${{ matrix.python-version }}` (+ setup-uv `python-version` for `UV_PYTHON`) | uv-managed interpreters, cached, arm64-aware; setup-uv's `python-version` alone does not install Python. |
| CPU torch resolution | Post-install reinstall, virtualenv surgery | `[tool.uv.sources]` torch marker + direct extra + `uv lock` | Deterministic, works with `--frozen`, removes CUDA deps from the lock entirely. |
| PyPI auth/token management | Long-lived `PYPI_API_TOKEN` secrets | Trusted publishing (OIDC) + `gh-action-pypi-publish@release/v1` | 15-minute project-scoped tokens, no secret rotation; attestations automatic. |
| Artifact handoff | Rebuilding in the publish job | build job → upload-artifact → download-artifact → publish | Official pattern; identical bytes tested and published. |
| Attestation verification | Custom Sigstore code | `pypi-attestations verify pypi --repository …` | Official PyPI tooling, identity-pinned. |
| Windows platform detection for fork | `try: os.fork except AttributeError` scattered everywhere | `hasattr(os, "fork")` guard at the two boundaries (`cli/commands/watch.py`, `utils/daemon.py`) | One clear message path; avoids partial detach state. |
| Version drift checks | Grepping all files at release time | Existing `tests/test_version_identity.py` + one build-job tag check | The invariant is already tested; the tag check covers the one thing tests can't (tag name). |
| Workflow YAML validation service | Adding actionlint/PyYAML/CI-only tooling | Text-level pytest guard + GitHub's own workflow validation on push | Zero new deps; the matrix running is the real validation. |

## Runtime State Inventory

> This phase deletes code and changes release metadata. No rename/migration of stored user data is involved; the categories below record the external/runtime surfaces that are **not in git** and therefore need manual action.

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| Stored data | None — dead-layer deletion touches no user databases. `CURRENT_SCHEMA_VERSION` (`src/sif/config/constants.py:55`) becomes orphaned once `migrations.py` is deleted; it is not stored anywhere. | Optional removal of the constant; no data migration. |
| Live service config | **PyPI trusted publisher** for `docsif` (external, UI-only) and **TestPyPI pending publisher**; **GitHub environments** `pypi`/`testpypi` (currently `total_count: 0` via `gh api`). | Manual maintainer action before the first tag (Pattern 5). |
| OS-registered state | None on the dev machine. On yoga: no service installed; the smoke only asserts `--install-service` refuses. | None. |
| Secrets/env vars | No new secrets. Trusted publishing removes the need for `PYPI_API_TOKEN`; existing GitHub token scopes are sufficient. `SIF_DB_PATH` is set per-smoke-subprocess to a temp path. | None (do not add token secrets). |
| Build artifacts / installed packages | `uv.lock` changes materially (torch/CPU fleet, black removal); `dist/` is gitignored; `uv.lock` is tracked. Yoga has a stale clone (`main@7652bb0`) and its own `.venv` created by `uv sync`; uv-managed CPython 3.12.15 was installed during this research. | Refresh `uv.lock`; sync yoga to the release commit before the smoke; no cleanup of managed Python required. |
| Tracking junk | `MagicMock/mock/*` (4 identical tracked SQLite blobs), `quick_test.py`, `simple_test.py`, `verify_imports.py`. | `git rm` all seven files (verified unreferenced). |

**Canonical question:** after every file in the repo is updated, what external systems still hold state? Answer: PyPI/TestPyPI publisher registrations and the two GitHub environments — both must be created manually before the tag workflow can succeed.

## Common Pitfalls

### Pitfall 1: `uv.sources` silently does nothing for transitive torch
**What goes wrong:** adding only `[[tool.uv.index]]` + `[tool.uv.sources] torch` leaves the lock resolving `torch 2.11.0` from PyPI with the CUDA stack; CI appears configured for CPU but downloads multi-GB CUDA wheels.
**Why it happens:** uv applies sources to the project's direct dependencies; torch arrives via sentence-transformers.
**How to avoid:** declare `torch` in `embed`/`all`, then relock and assert the lock has `source = { registry = "https://download.pytorch.org/whl/cpu" }` and no `nvidia-*` entries.
**Warning signs:** `uv lock` output does not mention removing nvidia packages; `grep nvidia uv.lock` still hits; Linux sync time balloons.

### Pitfall 2: `--frozen` cannot rescue a stale lock
**What goes wrong:** pyproject floors/classifier/torch changes land but `uv.lock` is not regenerated; CI's `uv sync --frozen` fails with "lockfile is out of date" (correctly), blocking every cell.
**Why it happens:** `--frozen` is a gate, not a resolver.
**How to avoid:** run `uv lock` in the same commit as every pyproject dependency change; add `uv lock --check` to the executor's local gate before pushing.
**Warning signs:** `uv lock --check` fails; sync error names the changed requirement.

### Pitfall 3: TestPyPI duplicate version on workflow re-run
**What goes wrong:** TestPyPI succeeds, PyPI fails (e.g., transient OIDC or upload error), the tag workflow is re-run, and TestPyPI now returns 400 because the same version/files already exist — blocking the retry before it reaches PyPI.
**Why it happens:** PyPI-family indexes are immutable per filename.
**How to avoid:** `skip-existing: true` on the TestPyPI publish job only; never on PyPI.
**Warning signs:** `File already exists` from the TestPyPI step on a re-run.

### Pitfall 4: Trusted publisher registered as "pending" for an existing project
**What goes wrong:** PyPI rejects a pending publisher for an existing project name; or the workflow filename/environment doesn't match the registered values and OIDC mint fails.
**Why it happens:** `docsif` already exists on PyPI (1.0.1); pending publishers only create non-existent projects. The registered **workflow filename** (e.g., `publish.yml`) is not the workflow `name:` field.
**How to avoid:** add a normal publisher to the existing `docsif` project; register the exact file name; environment name must match (`pypi`, `testpypi`); TestPyPI gets the pending publisher.
**Warning signs:** `invalid-publisher` / `OIDC audience` errors; publisher page shows no entry for the project.

### Pitfall 5: README marker missing or malformed in the published description
**What goes wrong:** the first v1.1.2 upload lacks `<!-- mcp-name: io.github.zhangtaolab/sif -->`, so the MCP Registry can never verify PyPI ownership for that release.
**Why it happens:** metadata is baked at build time; editing the README after the tag does not change the published artifact.
**How to avoid:** land the marker before the version bump/tag; keep it on its own line; no trailing period; verify on `https://pypi.org/pypi/docsif/1.1.2/json` that `info.description` contains the marker.
**Warning signs:** registry `mcp-publisher` ownership check fails in Phase 22; PyPI JSON description lacks the marker.

### Pitfall 6: Tag/version mismatch publishes the wrong artifact
**What goes wrong:** tag `v1.1.2` but `_version.py` still 1.1.1 → PyPI rejects the duplicate (or publishes a mislabeled version), and the failure is permanent.
**Why it happens:** two manual edits (version + tag) with no gate.
**How to avoid:** build-job step compares `GITHUB_REF_NAME` with the `_version.py` literal and fails before `uv build`; `tests/test_version_identity.py` already keeps runtime surfaces aligned.
**Warning signs:** build job fails at the version check.

### Pitfall 7: CUDA wheels sneak back through the cache
**What goes wrong:** a CI cache populated before the lock change can satisfy a later CPU-wheel request; or a stale `uv.lock` cache key reuses PyPI torch.
**Why it happens:** caches key on the dependency glob; changing `uv.lock` changes the key, but a wrong `cache-dependency-glob` or a `cache-suffix` collision can cross-wire.
**How to avoid:** keep `cache-dependency-glob: uv.lock`; unique `cache-suffix` per Python version; assert lock contents (no `nvidia-*`) as a test/gate.
**Warning signs:** Linux job install time stays multi-minute after the lock change.

### Pitfall 8: Windows detach crashes instead of degrading
**What goes wrong:** `sif watch --detach` on Win11 raises `AttributeError: module 'os' has no attribute 'fork'` with a traceback; the smoke cannot assert an honest message.
**Why it happens:** `utils/daemon.py:216-286` is an unguarded POSIX double-fork (`os.fork` 236, `os.setsid` 261, second fork 262).
**How to avoid:** add the CLI guard + library guard (Pattern 4), then assert the message.
**Warning signs:** traceback in the smoke output; exit code 1 with no remedy text.

### Pitfall 9: Windows smoke tests a stale checkout
**What goes wrong:** yoga's clone is `main@7652bb0`; running the smoke without syncing tests old code and reports "pass" for behavior that changed.
**Why it happens:** yoga is a user machine, not a CI checkout.
**How to avoid:** print `git rev-parse HEAD` + `git status --porcelain`, document a manual sync step, or add an explicit sync target; the script should record the commit in its output.
**Warning signs:** HEAD differs from the branch under test; dirty tree.

### Pitfall 10: `sif search query` on Windows downloads a model
**What goes wrong:** the hybrid subcommand loads an embedder; on yoga that means a model download (hundreds of MB) and long runtime.
**Why it happens:** `query` is the default human-facing search, but it is not model-free.
**How to avoid:** assert with `sif search search` (BM25) and `--json`; never invoke `query`/`vsearch` in the smoke.
**Warning signs:** smoke hangs on "Loading model"; HF cache dir appears on yoga.

### Pitfall 11: Missing-root mass delete regression
**What goes wrong:** the smoke deletes the docs dir and `sif index update` removes every document.
**Why it happens:** only if the 12-D11 guards regress (`drift.py:84-88`, `incremental.py:109-115/200-206`).
**How to avoid:** assert `Removed: 0` + the "all documents preserved" warning before and after the deletion step; this is a regression lock on an existing guard, not new behavior.
**Warning signs:** `Removed: N` where N = document count.

### Pitfall 12: Coverage gate silently disabled per cell
**What goes wrong:** someone adds `--no-cov` or `-p no:cacheprovider` style flags to speed CI; `fail_under=90` no longer runs per cell.
**Why it happens:** CI speed pressure.
**How to avoid:** keep `pytest` bare (addopts from pyproject); add a workflow text test asserting the run step does not contain `--no-cov`.
**Warning signs:** coverage XML absent; job passes with low coverage.

### Pitfall 13: Docs/generator gates fail after hygiene edits
**What goes wrong:** deleting dead layers changes documented APIs; `tests/test_docs.py` and the generated-docs diff gate fail.
**Why it happens:** docs reference `sif.models.search`, `sif.search.strategy`, `MigrationManager`, `make pre-commit`, and `black`.
**How to avoid:** make the doc edits listed in the Deletion Inventory; never hand-edit the two generator-owned docs; run `make docs-generate` only if a CLI/Settings surface changed (it doesn't here).
**Warning signs:** docs test failures naming the deleted modules; `git diff` on generated docs.

### Pitfall 14: The VERIFY-marker count is wrong in CONTEXT
**What goes wrong:** the plan searches for four pre-commit VERIFY markers and either misses one or deletes the bandit marker (out of scope).
**Why it happens:** the repo has 4 markers total, but only 3 concern pre-commit.
**How to avoid:** clear exactly `docs/testing.md:22`, `docs/development.md:691`, `docs/contributing.md:398`; leave `docs/testing.md:217` (bandit) untouched.
**Warning signs:** a leftover `pre-commit` VERIFY marker; a deleted bandit note.

### Pitfall 15: `MagicMock/` and root scripts remain half-removed
**What goes wrong:** deleting only `_.py` leaves the tracked blobs, or `verify_imports.py` stays and keeps documenting an obsolete `docsift` API.
**Why it happens:** junk is spread across root and a directory.
**How to avoid:** `git rm MagicMock/mock/{4398091296,4419046432,4419497200,4426075504} quick_test.py simple_test.py verify_imports.py`; verify `git ls-files | grep -E 'MagicMock|quick_test|simple_test|verify_imports'` is empty.
**Warning signs:** tracked binary blobs in `git status`.

### Pitfall 16: Release workflow races the matrix on tag pushes
**What goes wrong:** `test-matrix.yml` also triggers on tag pushes; the publish workflow can start before the matrix finishes.
**Why it happens:** GitHub workflows are independent.
**How to avoid:** treat the tag as the human gate (tag only after the branch matrix is green); optionally restrict the test workflow to `push: branches: ['**']` if tag-duplication is undesirable. Do not add cross-workflow `workflow_run` complexity for a single-maintainer repo.
**Warning signs:** a publish job running while the matrix is red.

### Pitfall 17: Python 3.13 binary-wheel assumption breaks a dependency
**What goes wrong:** a dependency without cp313 wheels fails the 3.13 cells at install time.
**Why it happens:** the matrix is the first 3.13 proof.
**How to avoid:** the refreshed lock already resolves every binary dep for 3.13 (torch 2.14.1/2.15.0 cp313 verified; `sqlite-vec 0.1.9` ships `py3-none-<platform>` wheels; the lock itself is universal resolution for all four Pythons). If a future dependency lacks 3.13 wheels, the lock refresh catches it before CI.
**Warning signs:** a cell fails during `uv sync` with "no wheels".

### Pitfall 18 (inherited P21/P24): CUDA bloat and publish mechanics
- Linux default PyPI resolution pulls multi-GB CUDA — solved by Pattern 3.
- PyPI name is `docsif` (CLI `sif`); version/classifier honesty and trusted-publisher wiring are the remaining publish traps — covered by Patterns 2/5 and Pitfalls 3–6.

## Code Examples

### Version/tag gate (build job)
```bash
VERSION="$(python3 -c "import runpy; print(runpy.run_path('src/sif/_version.py')['__version__'])")"
test "v${VERSION}" = "${GITHUB_REF_NAME}" || { echo "tag ${GITHUB_REF_NAME} != ${VERSION}"; exit 1; }
```
Source: derived from `src/sif/_version.py:3` (`__version__ = "1.1.1"`) and `src/sif/config/constants.py:8` (`APP_VERSION = __version__`). `[VERIFIED: src/sif/_version.py:3; src/sif/config/constants.py:3,8; tests/test_version_identity.py:56-94]`

### Attestation verification
```bash
uvx pypi-attestations verify pypi \
  --repository https://github.com/zhangtaolab/sif \
  pypi:docsif-1.1.2-py3-none-any.whl
```
Source: `[CITED: docs.pypi.org/attestations/consuming-attestations/]` — the tool fetches the wheel + provenance via the Integrity API, checks the Trusted Publisher identity against `--repository`, and cryptographically verifies the wheel.

### TestPyPI install proof
```bash
uv pip install --python /tmp/sif-release-venv/bin/python \
  --index-url https://test.pypi.org/simple/ \
  --extra-index-url https://pypi.org/simple \
  'docsif==1.1.2'
```
(TestPyPI does not mirror dependencies; the extra index is required.)

### Windows guard (exact messages)
```python
# src/sif/cli/commands/watch.py — user-facing
if not hasattr(os, "fork"):
    raise click.ClickException(
        "--detach requires POSIX fork support and is not available on Windows; "
        "run `sif watch` in the foreground instead."
    )
```
Source: `src/sif/utils/daemon.py:216-286` (`pid = os.fork()` at 236; `os.setsid()` at 261; `if os.fork() > 0:` at 262; `os.killpg` at 375) and `src/sif/cli/commands/watch.py:623-626` (`_run_detach(...)`). `[VERIFIED: src/sif/utils/daemon.py:216-286; src/sif/cli/commands/watch.py:623-626]`

### Existing degradation messages to assert (verbatim)
```text
fcntl unavailable on this platform; index lock disabled (WAL + busy_timeout still protect database integrity)
Collection root <path> does not exist; skipping update (all documents preserved)
Collection root <path> does not exist; skipping drift walk (all documents preserved)
```
Sources: `src/sif/database/locking.py:57-63`; `src/sif/indexing/incremental.py:109-115` and `:200-206`; `src/sif/indexing/drift.py:84-88`. `[VERIFIED: src/sif/database/locking.py:57-63; src/sif/indexing/incremental.py:109-115,200-206; src/sif/indexing/drift.py:84-88]`

## Deletion Inventory (ENG-04, complete reference map)

### Files to delete outright
| Path | Size | Why safe |
|------|------|----------|
| `src/sif/models/search.py` | 92 LOC | Five Pydantic classes; imported only by `src/sif/models/__init__.py:34-40`, `src/sif/search/strategy.py:7`, and three test files. No production search path uses it (`sif.core.models` dataclasses are the real types). |
| `src/sif/search/strategy.py` | 97 LOC | `SearchStrategy` ABC / `SearchContext` / `Searchable`; imported only by `tests/unit/test_search.py:12`. No searcher inherits it. |
| `src/sif/database/migrations.py` | 233 LOC | Legacy `MigrationManager`; exported by `src/sif/database/__init__.py:6,22` but never invoked by `Database`/`SchemaManager`. |
| `tests/unit/test_search.py` | 153 LOC | Tests only the dead Pydantic models + `SearchContext`. |
| `tests/unit/database/test_migrations.py` | 182 LOC | Tests only `MigrationManager`/`CURRENT_SCHEMA_VERSION`. |
| `tests/factories.py` | — | Unused anywhere (no `tests.factories` import); contains `SearchOptionsFactory`/`SearchResultFactory` bound to the dead models. Deleting is safer than rewiring dead helpers. |
| `MagicMock/mock/4398091296`, `4419046432`, `4419497200`, `4426075504` | 4 × 128 KB | Identical tracked SQLite snapshots (same blob SHA `9e4c5ce…`); test-execution litter. |
| `quick_test.py`, `simple_test.py` | — | Stale `docsift`-era scripts; `simple_test.py` requires nonexistent `.pre-commit-config.yaml` and `.github/workflows/ci.yml`. |
| `verify_imports.py` | — | Stale `docsift` import list incl. `MigrationManager` and removed search classes. |

### Required edits at deletion sites
| File:line | Change |
|-----------|--------|
| `src/sif/models/__init__.py:34-40` | Delete the `sif.models.search` import block. |
| `src/sif/models/__init__.py:53-65` | Remove `SearchOptions`, `SearchQuery`, `SearchResponse`, `SearchResult`, `SearchType` from `__all__`. |
| `src/sif/database/__init__.py:6` | Delete `from sif.database.migrations import MigrationManager`. |
| `src/sif/database/__init__.py:22` | Remove `"MigrationManager"` from `__all__`. |
| `src/sif/search/rrf.py:112-122` | Delete the orphan `compute_rrf_score` function (only referenced by `docs/api-reference.md`). |
| `src/sif/config/constants.py:55` | Optional: remove `CURRENT_SCHEMA_VERSION = 1` — it becomes orphaned (only `migrations.py` + `test_migrations.py` use it). |
| `tests/conftest.py:24` | Delete the `sif.models.search` import. |
| `tests/conftest.py:391-440` | Delete the three unused fixtures (`sample_search_options`, `sample_search_result`, `sample_search_results`); `test_rrf.py` defines its own same-named fixture. |
| `examples/quickstart.py:168,178` | Replace the `MigrationManager.run_migrations()` example with `Database.init_schema()` (or drop the example section). |
| `examples/quickstart.py:246-260` | Replace the dead `BM25SearchStrategy` example with `sif.search.BM25Searcher` (the file is already stale — `from sif.search import BM25SearchStrategy, SearchContext` never resolves today). |

### Documentation edits (dead layers + pre-commit + black)
| File:line | Change |
|-----------|--------|
| `docs/architecture.md:6` | Intro sentence names `SearchStrategy` from `sif/search/strategy.py` — remove. |
| `docs/architecture.md:298` | Tree entry `strategy.py` — remove (and the `migrations.py` entry around line 298-300). |
| `docs/architecture.md:685` | Paragraph starting "`MigrationManager` …" — remove. |
| `docs/architecture.md:728` | Seams-table row for `SearchStrategy` — remove. |
| `docs/development.md:471` | Bullet describing `MigrationManager`/`CURRENT_SCHEMA_VERSION` — remove. |
| `docs/development.md:495-500` | "New Search Strategy" how-to that subclasses the dead ABC — remove or rewrite to `BM25Searcher`. |
| `docs/models.md:479` | Sentence about `sif.models.search.SearchOptions` bounds — rewrite (no Pydantic search models remain). |
| `docs/api-reference.md:230,378,454,477-480,875-879` | Remove/replace dead imports, `SearchStrategy` example, and `compute_rrf_score` docs. |
| `DESIGN.md:58,109` | `src/sif/search/strategy.py` entries — remove. |
| `docs/testing.md:20,22` | Remove the `pre-commit install` sentence + VERIFY marker. |
| `docs/testing.md:186` | Update the `SKIP_COMMAND_PATTERNS` description if `tests/test_docs.py:44` drops `pre-commit install`. |
| `docs/testing.md:217` | Leave the bandit VERIFY marker (out of scope). |
| `docs/development.md:631,655-658,674,691` | Remove the pre-commit caveat, the `pre-commit install`/`autoupdate` table text, and the `make pre-commit` row + VERIFY marker. |
| `docs/contributing.md:386,398` | Remove the `pre-commit install` table text + VERIFY marker. |
| `docs/installation.md:78-82` | Drop `black>=23.0.0`; update the ST floor to `>=5.4.1`; add `torch`. |
| `docs/installation.md:148` | Version sample `sif, version 1.1.1` → `1.1.2`. |
| `docs/development.md:575-600` | Rewrite "Release Process": bump `_version.py`, changelog, tag push; the workflow builds and publishes (remove `twine upload` as the primary path). |
| `docs/changelog.md` | Add `## [1.1.2] - <date>`; update `[Unreleased]` compare link and add `[1.1.2]` link. |

### Makefile edits (`Makefile`)
| Line | Change |
|------|--------|
| 4 | `.PHONY`: remove `pre-commit`, add `windows-smoke`. |
| 29 | Remove the `make pre-commit` help line; add a `make windows-smoke` line. |
| 47, 52 | Remove `pre-commit install` from `install-dev`/`install-all`. |
| 110-112 | Delete the `pre-commit:` target. |
| 171 | Remove `pre-commit autoupdate` from `update-deps`. |
| 179 | Remove `black` from the `info` grep pattern. |
| (new) | Add the `windows-smoke` target (Pattern 4). |

### pyproject edits
| Section | Change |
|---------|--------|
| `[project].classifiers` (16-26) | Add `"Programming Language :: Python :: 3.13"` **only after the matrix is green**. |
| `[project.optional-dependencies].dev` (43-50) | Remove `"black>=23.0.0"`. |
| `[project.optional-dependencies].embed` (51-55) | `sentence-transformers>=5.4.1`; add `"torch"`. |
| `[project.optional-dependencies].all` (65-71) | `sentence-transformers>=5.4.1`, `llama-cpp-python>=0.3.35`; add `"torch"`. |
| `[tool.black]` (87-89) | Delete the section. |
| `[[tool.uv.index]]` / `[tool.uv.sources]` (new) | Add the pytorch-cpu index + torch marker (Pattern 3). |
| `mcp`/`http` extras, `fastapi`/`uvicorn` core deps | **Unchanged** (D-11). |

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `twine upload` with an API token | Trusted publishing (OIDC) + PEP 740 attestations | Trusted publishing GA; action attestations default since v1.11.0 | No long-lived secrets; verifiable provenance. |
| `black` + `ruff` | `ruff format` only | Repo already enforces ruff format; black is redundant | Drop the dep and config. |
| Hand-rolled MCP shell (Phase 22 concern) | Official SDK — not this phase | v1.2 | Dead layers must go first so filters can't be wired into them. |
| Per-OS Python setup scripts | uv-managed Pythons (`uv python install`) | uv 0.13.x | Same recipe on GitHub runners and yoga. |
| Post-sync package patching | Lock-level `[tool.uv.sources]` | uv project sources | `--frozen` CI is deterministic across platforms. |

**Deprecated/outdated:**
- `actions/checkout@v4` in `docs.yml` (leave the docs workflow untouched; new workflows use v7).
- `actions/setup-python@v5` in `docs.yml` (same).
- `make pre-commit`, `.pre-commit-config.yaml`, `black`, `MigrationManager`, `sif.models.search`, `sif.search.strategy`, `compute_rrf_score`.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | The PyPI `docsif` project is controlled by the maintainer account that will register the trusted publisher. | Pattern 5 | Blocked release; needs account recovery/ownership transfer. |
| A2 | The absence of provenance at the Integrity API URL for 1.0.1 means no trusted publisher exists for the existing project (it could also mean the legacy upload path differed). | Summary / Pattern 5 | If a publisher already exists, the manual step is a verification rather than a creation. |
| A3 | `docsif` 1.1.2 is an acceptable direct successor to 1.0.1 on PyPI (1.1.0/1.1.1 were never uploaded). | Pattern 5 | Users see a version jump; upgrade semantics unchanged. |
| A4 | Yoga's clone can be synced manually to the release commit before the smoke; no automation of user-machine git state is desired. | Pattern 4 | Smoke tests stale code; catch via HEAD echo. |
| A5 | The `pypi`/`testpypi` environments need no required reviewers (D-15: tag = release intent). | Pattern 5 / Security | Weaker human gate; mitigated by protected branch/tag creation. |
| A6 | `skip-existing: true` on TestPyPI is acceptable and does not mask a broken build (the build job gates the artifact first). | Pattern 2 | A re-run could skip a newly built file with the same version — version numbers are immutable anyway. |
| A7 | Text-level workflow assertions are sufficient regression guards; no YAML parser is needed. | Validation Architecture | Guards can false-positive on formatting changes; acceptable for a small workflow file. |

## Open Questions (RESOLVED)

1. **Torch fleet alignment (2.11.0 vs 2.14.1/2.15.0).** (RESOLVED — plan 17-02 Task 1 runs `uv lock --upgrade-package torch` after the initial lock, so the lock matches the documented fleets and macOS/Windows do not lag.) Recommendation: `uv lock --upgrade-package torch` so the lock matches the documented fleets and macOS/Windows do not lag. If the user prefers minimal dependency churn, keep 2.11.0 but accept that the lock does not exercise the named split.
2. **Dedicated Windows service-manager guard.** (RESOLVED — plan 17-04 Task 1 adds a `sys.platform == "win32"` guard with a Windows-specific remedy in `watch.py`, and asserts it.) Current behavior (systemctl missing → clear typed error) is honest but mentions Linux. Recommendation: add a `sys.platform == "win32"` guard with a Windows-specific remedy in `watch.py`, and assert that instead; low risk.
3. **Lint/type job in the matrix?** (RESOLVED — plan 17-03 Task 2 adds the optional single ubuntu/py3.12 ruff + format-check + ty job.) Recommendation: optional single ubuntu/py3.12 job running ruff + ty; not required by ENG-01 and duplicates local `make ci`.
4. **Yoga sync automation.** (RESOLVED — plan 17-04 Task 3 precondition documents the manual `git fetch/checkout` and the script prints HEAD; plan 17-04 is non-autonomous for that reason and no destructive git operation is scripted on the user machine.) Recommendation: document the manual `git fetch/checkout` and have the script print HEAD; do not script destructive git operations on a user machine.
5. **`CURRENT_SCHEMA_VERSION` removal.** (RESOLVED — plan 17-01 Task 2 removes it with `migrations.py`.) Recommendation: remove it with `migrations.py`; if the planner wants zero config-surface change, leave it (harmless orphan).
6. **`docs.yml` modernization.** (RESOLVED — left untouched; plan 17-03 Task 1's read-first explicitly preserves `checkout@v4`/`setup-python@v5` in that file.) Out of scope; leave `checkout@v4`/`setup-python@v5` untouched to keep the diff focused.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| uv (local) | lock/sync/build/CI recipe verification | ✓ | 0.13.7 | — |
| uv (yoga) | Windows smoke bootstrap | ✓ | 0.13.1 | `uv self update` on yoga |
| hc CLI | remote smoke execution | ✓ | 0.1.21 | — |
| yoga machine | Windows smoke | ✓ (connected) | Win11, agent 0.1.20 | — |
| Python on yoga | smoke | ✓ (uv-managed after bootstrap) | 3.12.15 installed this session; Store alias remains | `uv python install 3.12` (verified) |
| git on yoga | checkout preflight | ✓ | `C:\Program Files\Git\cmd\git.exe` | — |
| yoga repo `D:\Github\SIF` | smoke | ✓ | git clone of `zhangtaolab/SIF`, `main@7652bb0`, clean | manual sync to release commit |
| gh CLI (authed) | environments, repo checks | ✓ | scopes `repo, workflow, read:org` | GitHub web UI |
| GitHub environments `pypi`/`testpypi` | trusted publishing | ✗ (`total_count: 0`) | — | create via `gh api` or UI (blocking manual step) |
| PyPI trusted publisher for `docsif` | publish | ✗ (no provenance on 1.0.1) | — | add publisher in project settings (blocking manual step) |
| TestPyPI pending publisher | TestPyPI dry run | ✗ (docsif 404) | — | register pending publisher (blocking manual step) |
| twine | build metadata check | ✓ local; `uvx` in CI | — | `uvx twine check` |
| pypi-attestations | attestation verification | via `uvx` | — | PyPI web UI attestation display |
| actionlint | workflow lint | ✗ | — | GitHub's own workflow validation on push |
| Docker | required by gh-action-pypi-publish | not needed locally (actions run on GitHub runners) | — | — |

**Missing dependencies with no fallback:** the PyPI/TestPyPI publisher registrations and the two GitHub environments (maintainer-only UI actions). The planner must include them as explicit manual/checkpoint tasks before the first tag.

**Missing dependencies with fallback:** actionlint (GitHub validation), local `build` (use `uv build`), `pypi-attestations` (use `uvx` or the PyPI UI).

## Validation Architecture

> `workflow.nyquist_validation` is `true` in `.planning/config.json` — this section is required.

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 9.0.3 + pytest-cov 7.1.0 (locked) |
| Config file | `pyproject.toml` `[tool.pytest.ini_options]` (lines 206-211) + `[tool.coverage.report]` (213-214) |
| Quick run command | `env -u FORCE_COLOR NO_COLOR=1 pytest -x -q --no-cov` |
| Full suite command | `env -u FORCE_COLOR NO_COLOR=1 pytest` (1629 tests collected at HEAD `c1d9fb3`) |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| ENG-01 | Matrix workflow declares 4 Python versions × 2 OSes, `fail-fast: false`, per-ref concurrency, SHA-pinned setup-uv, `uv sync --frozen --extra dev --extra embed`, no `--no-cov` | unit (text-level YAML guard) | `pytest tests/test_ci_workflows.py -x` | ❌ Wave 0 |
| ENG-01 | The same matrix actually runs green on every cell | e2e (GitHub Actions) | observe PR/push run; per-cell `fail_under=90` in pytest output | N/A (external) |
| ENG-01 | Lock resolves CPU torch fleets and no CUDA deps | unit | `pytest tests/test_ci_workflows.py::test_lock_has_cpu_torch -x` (parse `uv.lock` text) | ❌ Wave 0 |
| ENG-02 | Smoke message matchers recognize the flock warning, missing-root warning, and detach refusal | unit | `pytest tests/test_windows_smoke_script.py -x` | ❌ Wave 0 |
| ENG-02 | Yoga CLI degradation (real Windows) | manual/e2e (documented) | `make windows-smoke` (pre-release) | N/A (remote) |
| ENG-03 | Version single-sourced across runtime surfaces + hatch path | unit (existing) | `pytest tests/test_version_identity.py -x` | ✅ existing |
| ENG-03 | README marker present with correct boundary; changelog has 1.1.2; tag↔version check text in publish workflow | unit | `pytest tests/test_release_metadata.py -x` | ❌ Wave 0 |
| ENG-03 | Build + TestPyPI + PyPI + attestations | e2e (release) | `uv build`, `uvx twine check`, workflow run, `uvx pypi-attestations verify …` | N/A (external) |
| ENG-04 | Dead modules are not importable; no source/test imports them; `compute_rrf_score` gone | unit | `pytest tests/test_hygiene.py -x` | ❌ Wave 0 |
| ENG-04 | Makefile has no `pre-commit` target/`pre-commit install`; pyproject has no black/`[tool.black]`; extras floors correct; junk paths absent | unit | `pytest tests/test_hygiene.py -x` | ❌ Wave 0 |
| ENG-04 | Full suite + ruff + ty green after deletion | integration | `make ci` (local) / the 8-cell matrix | ✅ existing |

### Sampling Rate
- **Per task commit:** `env -u FORCE_COLOR NO_COLOR=1 pytest -x -q --no-cov` plus `ruff check src tests` and `ruff format --check src tests`.
- **Per wave merge:** full suite (`env -u FORCE_COLOR NO_COLOR=1 pytest`) + `ty check src/sif` + `uv lock --check`.
- **Phase gate:** full suite green locally **and** the 8-cell GitHub matrix green on the release commit before the tag; Windows smoke green on yoga before the tag.

### Wave 0 Gaps
- [ ] `tests/test_ci_workflows.py` — ENG-01 workflow + lock guards (no new dependency).
- [ ] `tests/test_release_metadata.py` — ENG-03 README marker/changelog/publish-workflow guards.
- [ ] `tests/test_hygiene.py` — ENG-04 deletion and config guards.
- [ ] `tests/test_windows_smoke_script.py` — ENG-02 message-matcher tests (import the script via `importlib.util` or a small `scripts/__init__.py`-free helper).
- [ ] Delete `tests/unit/test_search.py`, `tests/unit/database/test_migrations.py`, `tests/factories.py` in the same plan as the module deletions (suite must collect).
- [ ] Framework install: none — pytest/pytest-cov are already locked dev deps.

## Security Domain

> `security_enforcement` is not disabled in `.planning/config.json` — this section is required.

### Applicable ASVS Categories
| ASVS Category | Applies | Standard Control |
|---------------|---------|------------------|
| V2 Authentication | No | No application auth in this phase. |
| V3 Session Management | No | — |
| V4 Access Control | Yes | Job-scoped `id-token: write` only on publish jobs; workflow-level `contents: read`; GitHub environments scope which workflow can mint tokens; no long-lived PyPI tokens. |
| V5 Input Validation | No (workflow inputs are static) | Matrix/tag values are literals; no untrusted input reaches shell steps. |
| V6 Cryptography | Yes | Never hand-roll: PyPI OIDC + Sigstore/PEP 740 via the official action; verify with `pypi-attestations`. |

### Known Threat Patterns for this stack
| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Secret exfiltration via PR workflows | Information Disclosure | Use `pull_request` (not `pull_request_target`); no secrets in the matrix; `contents: read` default. |
| Unauthorized release via tag push | Tampering / Elevation | Protect tag creation/branch; environment-scoped OIDC; build job has no `id-token`; tag↔version gate. |
| TestPyPI/PyPI confusion | Spoofing | Separate environments (`testpypi`, `pypi`), separate `repository-url`; never reuse credentials. |
| Artifact tampering between build and publish | Tampering | Build once, upload-artifact, download into `dist/`, publish the same bytes; never rebuild in publish jobs. |
| Dependency-confusion via extra indexes | Tampering | `explicit = true` on the CPU index; it serves only torch; everything else from PyPI. |
| Cache poisoning across branches | Tampering | GitHub cache scoping + `uv.lock` in the cache key; matrix cache suffix; hosted runners. |
| Unpinned third-party action supply chain | Tampering | SHA-pin `setup-uv` (verified SHA); the PyPI action is pinned to the official `release/v1` channel (or its tag SHA). |
| Publishing a wrong-name package | Spoofing | `name = "docsif"` is fixed and verified by PyPI's first-publish; version/tag gate prevents mislabeled uploads. |

## Sources

### Primary (HIGH confidence — read directly this session)
- Local repo at HEAD `c1d9fb3` (`dev`) — `pyproject.toml`, `Makefile`, `uv.lock`, `.github/workflows/docs.yml`, `src/sif/**`, `tests/**`, `docs/**`, `README.md`, `git ls-files`.
- `[VERIFIED: src/sif/database/locking.py:29-34,57-63]`, `[VERIFIED: src/sif/utils/daemon.py:216-286,375]`, `[VERIFIED: src/sif/cli/commands/watch.py:344-374,416-418,623-626]`, `[VERIFIED: src/sif/utils/service.py:66-85,199-203,251]`, `[VERIFIED: src/sif/cli/main.py:117-136,165-224]`, `[VERIFIED: src/sif/indexing/drift.py:82-88]`, `[VERIFIED: src/sif/indexing/incremental.py:106-115,198-206]`, `[VERIFIED: src/sif/cli/commands/index.py:45-59]`, `[VERIFIED: src/sif/cli/commands/search.py:429,470,767,857]`, `[VERIFIED: src/sif/cli/commands/collection.py:27-29]`.
- `[VERIFIED: src/sif/models/search.py:1-92]`, `[VERIFIED: src/sif/search/strategy.py:1-97]`, `[VERIFIED: src/sif/search/rrf.py:112-122]`, `[VERIFIED: src/sif/database/__init__.py:6,22]`, `[VERIFIED: src/sif/models/__init__.py:34-40,53-65]`, `[VERIFIED: src/sif/config/constants.py:3,8,55]`, `[VERIFIED: src/sif/_version.py:3]`, `[VERIFIED: tests/test_version_identity.py:39-94]`, `[VERIFIED: tests/conftest.py:24,391-440]`, `[VERIFIED: tests/test_docs.py:44]`.
- `[VERIFIED: local uv 0.13.7 experiments]` — temp-dir lock of the real pyproject: (a) source-only change leaves PyPI/CUDA torch; (b) adding `torch` to extras + source yields 2.14.1+cpu/2.15.0+cpu on Linux, PyPI torch elsewhere, and removes nvidia/triton/black. `uv lock --check` passes on the current lock; `uv sync --dry-run --frozen --extra dev --extra embed` resolves torch 2.11.0/sentence-transformers 5.4.1/transformers 5.5.4.
- `[VERIFIED: live hc probes 2026-11-13]` — yoga connected (agent 0.1.20), `uv 0.13.1`, git present, `D:\Github\SIF` = clean clone of `zhangtaolab/SIF` on `main@7652bb0`, `uv python install 3.12` → 3.12.15, `uv run --python 3.12 --no-project python --version` → 3.12.15.
- `[VERIFIED: gh CLI]` — `repos/zhangtaolab/sif/environments` = `total_count: 0`; auth scopes `repo, workflow, read:org`.
- `[VERIFIED: PyPI JSON API + Integrity API]` — `docsif` releases `0.1.0,0.1.1,0.2.0,1.0.0,1.0.1` (latest 1.0.1, uploaded 2026-11-07), wheel `docsif-1.0.1-py3-none-any.whl`; Integrity API provenance URL returns 404; TestPyPI `docsif` returns 404.

### Primary external docs (HIGH confidence — fetched directly)
- `[VERIFIED: https://raw.githubusercontent.com/astral-sh/setup-uv/v10.3.3/README.md]` — `python-version` sets `UV_PYTHON` only; `enable-cache`/`cache-dependency-glob`/`cache-suffix`; SHA-pin pattern. Tag SHA confirmed by `git ls-remote` (`68559e99cc807c1eb7e9238fd43a15bba460eec2`).
- `[VERIFIED: https://raw.githubusercontent.com/pypa/gh-action-pypi-publish/release/v1/README.md + action.yml]` — environment `pypi`, job-scoped `id-token: write`, attestations default true, TestPyPI `repository-url: https://test.pypi.org/legacy/`, Linux-only, build separation, no reusable workflows, one invocation per job, `skip-existing` default false, `packages-dir` default `dist`.
- `[VERIFIED: https://docs.astral.sh/uv/guides/integration/pytorch/]` — `[[tool.uv.index]]` explicit + `[tool.uv.sources]` with `marker`; platform-marker examples.
- `[VERIFIED: https://docs.pypi.org/trusted-publishers/adding-a-publisher/]` — existing-project flow: owner, repository, workflow filename, optional environment; project → Publishing.
- `[VERIFIED: https://docs.pypi.org/trusted-publishers/creating-a-project-through-oidc/]` — pending publisher adds the project name; does not reserve the name; account-level Publishing.
- `[CITED: https://docs.pypi.org/attestations/consuming-attestations/]` — `pypi-attestations verify pypi --repository <repo> <wheel>`; Integrity API fetch + cryptographic verification.
- `[VERIFIED: https://github.com/modelcontextprotocol/registry/blob/main/docs/modelcontextprotocol-io/package-types.mdx]` — `mcp-name: $SERVER_NAME` in the README/description; may be an HTML comment; must match `server.json`; boundary rules; no trailing period.
- `[VERIFIED: https://raw.githubusercontent.com/actions/runner-images/main/README.md]` — `macos-latest` = macOS 26 Arm64; `ubuntu-latest` = Ubuntu 24.04 x64; `macos-14` x64 deprecated.
- `[VERIFIED: https://download.pytorch.org/whl/cpu/torch/]` — torch 2.11.0+cpu and 2.14.1/2.15.0+cpu wheels for cp310–cp315 (manylinux x86_64/aarch64, win_amd64; macOS wheels also listed).
- `[CITED: https://packaging.python.org/en/latest/guides/publishing-package-distribution-releases-using-github-actions-ci-cd-workflows/]` — build job separate, upload/download artifacts, environment `pypi`/`testpypi`, `id-token: write`, TestPyPI URL.
- GitHub API `releases/latest` for `actions/checkout` (v7.0.1), `actions/upload-artifact` (v7.0.2), `actions/download-artifact` (v8.0.2), `astral-sh/setup-uv` (v10.3.3), `pypa/gh-action-pypi-publish` (v1.14.3), `actions/setup-python` (v7.1.0).

### Secondary (MEDIUM confidence)
- `.planning/research/STACK.md`, `PITFALLS.md` (P21–P24), `SUMMARY.md` — prior-session verified facts reused where re-confirmed above (setup-uv SHA, action versions, CPU-index rationale, py3.10/3.11+ fleets).
- WebSearch summaries for pending-publisher fields/URL and `pypi-attestations` usage — cross-checked against the official pages above.

### Tertiary (LOW confidence — do not treat as settled)
- Exact PyPI account UI labels are rendered from screenshots on the docs pages; the field *names* (owner, repository name, workflow filename, environment) are textual and verified, but the UI wording may drift.
- Whether docsif 1.0.1's missing provenance is due to a legacy token upload or simply no trusted publisher — the observation is 404, not an inspection of project settings.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — action versions and SHAs verified via GitHub API/`git ls-remote`; uv/action semantics read from official READMEs.
- Architecture (CI/publish/smoke recipes): HIGH — verified by local lock experiments and live yoga probes; YAML assembled from official examples.
- Hygiene inventory: HIGH — every reference read at HEAD `c1d9fb3` with file:line.
- Pitfalls: HIGH — most are directly observed (lock behavior, yoga state, code paths); publish retry behavior is reasoned from immutable-file semantics (MEDIUM).
- Manual PyPI/GitHub registration: MEDIUM — procedure verified; actual account state must be checked by the maintainer.

**Research date:** 2026-11-13
**Valid until:** 2027-01-12 for the workflow recipes (fast-moving actions); re-verify action majors and PyPI publisher UI if planning slips more than ~60 days.
