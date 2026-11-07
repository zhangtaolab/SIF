---
phase: 260914-vyr-rename-distribution-docsif-to-sif-pyproj
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - pyproject.toml
  - README.md
  - uv.lock
autonomous: true
requirements: [MCP-01]
estimate:
  tokens: 25000
  raw_tokens: 25000
  tasks: 2
  confidence: low

must_haves:
  truths:
    - "pyproject.toml declares `name = \"sif\"`; the `docsif` console-script alias is gone (only `sif = \"sif.cli.main:main\"` remains under [project.scripts]); the keyword list no longer contains \"docsif\" (v1.0 audit BLOCKER 2)"
    - "`pip install sif[mcp]`, `pip install sif[http]`, and `pip install sif[embed]` are all valid extras under the renamed distribution: `mcp` and `http` extras exist in [project.optional-dependencies], `embed` already exists — CLI hints at src/sif/cli/commands/mcp.py:39,72 and src/sif/cli/commands/search.py:509 become truthful with NO src changes"
    - "README.md contains zero `pip install docsif` instructions (lines 27/33/54 now say `sif` / `\"sif[all]\"`)"
    - "uv.lock root package entry (was `[[package]] name = \"docsif\"` at line 589) says `name = \"sif\"`; `uv lock --check` exits 0"
    - "`env -u FORCE_COLOR NO_COLOR=1 python -m pytest` is green at the expected baseline (~675 passed; the 2 order-dependent caplog failures in tests/unit/embedding/test_openai_embedder.py are pre-existing — WINDOWS.md #3/#4)"
    - "A case-sensitive grep for standalone `docsif` (NOT part of `docsift`) across pyproject.toml README.md docs/ src/ tests/ Makefile CONTRIBUTING.md CHANGELOG.md returns ZERO hits"
  artifacts:
    - "pyproject.toml — name=sif; deduped [project.scripts]; keyword list without docsif; new mcp and http extras"
    - "README.md — install instructions reference sif / sif[all]"
    - "uv.lock — regenerated root package name sif, lock-consistent"
  key_links:
    - "src/sif/cli/commands/mcp.py:39 `pip install sif[mcp]` hint -> [project.optional-dependencies].mcp (created this task)"
    - "src/sif/cli/commands/mcp.py:72 `pip install sif[http]` hint -> [project.optional-dependencies].http (created this task)"
    - "src/sif/cli/commands/search.py:509 `pip install -e '.[embed]'` hint and src/sif/embedding/embedder.py:386 `pip install sif[openai]` hint -> existing embed/openai extras (valid once renamed; NO src edits)"
    - "src/sif/mcp/README.md:21 `pip install -e \".[mcp]\"` -> mcp extra (becomes valid; NO edit needed)"
    - "uv.lock [[package]] root entry <- pyproject name (via `uv lock`)"
---

<objective>
Rename the Python distribution `docsif` -> `sif` (v1.0 milestone audit BLOCKER 2, MCP-01 / phase-8 residue). Phase 8 renamed the project but left the distribution metadata wrong: publishing v1.0 would ship a package named `docsif`, a duplicate `docsif` console script, and every self-referential install hint (`sif[mcp]`, `sif[http]`, `sif[embed]`) pointing at extras that either live under the wrong name or do not exist.

Planner-verified inventory of standalone `docsif` (2026-09-14, precise grep `docsif` not followed by `t`):
- pyproject.toml:6 `name = "docsif"`; :15 keyword `"docsif"`; :68 `docsif = "sif.cli.main:main"` console-script alias (line 67 `sif = ...` is correct and stays)
- README.md:27 `pip install docsif`; :33 `pip install "docsif[all]"`; :54 `pip install docsif`
- uv.lock:589 `[[package]] name = "docsif"` (root editable entry)
- NO other standalone `docsif` anywhere in pyproject.toml/README.md/docs/src/tests/Makefile/CONTRIBUTING.md/CHANGELOG.md. Root-level legacy files (PROJECT_SUMMARY.md, quick_test.py, DELIVERY_REPORT.md, REFACTOR_REPORT.md, verify_imports.py, simple_test.py, DESIGN.md, INTEGRATION_STATUS.md) contain only `docsift` (the OLDER project name — different string, historical, untouched).

Verified extras alignment facts:
- Existing extras: `dev`, `embed`, `openai`, `all`. The `mcp` and `http` extras DO NOT exist — the audit's "extras exist only under docsif" is precisely true only for `embed`; `mcp`/`http` must be CREATED so the hints resolve.
- Dependency truth: the MCP server is self-contained — stdio transport is stdlib-only; http transport lazily imports `uvicorn` (src/sif/mcp/transports/http.py:212), which is already a core dependency. `fastapi`/`uvicorn` appear nowhere else in src/. Therefore both new extras reference the already-core `uvicorn` only: zero new packages, zero resolution change, no Package Legitimacy Gate implications.
- Deliberate NON-changes: description `"DocSIF - Local hybrid search engine..."` (pyproject.toml:8) stays — scope says keep everything else; version stays 0.2.1 (v1.0 bump is a milestone-completion action, not this task); core dependencies untouched.

Purpose: publishing v1.0 must ship the package as `sif`, and a user who hits an ImportError on the MCP or embed paths must be able to run the exact `pip install sif[...]` command the CLI tells them.
Output: renamed, self-consistent distribution metadata; regenerated lockfile; green suite.
</objective>

<execution_context>
@~/.claude/gsd-core/workflows/execute-plan.md
@~/.claude/gsd-core/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md
@CLAUDE.md
@.planning/v1.0-MILESTONE-AUDIT.md
@pyproject.toml
@README.md
</context>

<tasks>

<task type="auto">
  <name>Task 1: Rename distribution to sif in pyproject.toml (name, keyword, script, extras) and README.md install hints</name>
  <files>pyproject.toml, README.md</files>
  <action>
Four edits in pyproject.toml:
1. Line 6: `name = "docsif"` -> `name = "sif"`.
2. Line 15 keywords: drop the `"docsif"` entry; keep `"sif"` and all other keywords.
3. [project.scripts] (lines 66-68): delete the `docsif = "sif.cli.main:main"` line; keep `sif = "sif.cli.main:main"`.
4. [project.optional-dependencies]: add two extras so the CLI install hints (mcp.py:39 `sif[mcp]`, mcp.py:72 `sif[http]`) are valid. Both list only the already-core uvicorn — no new packages, matching the verified fact that the stdio transport is stdlib-only and http.py:212 lazily imports uvicorn:
   mcp = ["uvicorn>=0.20.0"]
   http = ["uvicorn>=0.20.0"]
   Place them after the `openai` extra, before `all`. Do NOT touch `dev`/`embed`/`openai`/`all`, core dependencies, description (line 8 "DocSIF - ..." stays), version, or any tool config.

Three edits in README.md: line 27 `pip install docsif` -> `pip install sif`; line 33 `pip install "docsif[all]"` -> `pip install "sif[all]"`; line 54 `pip install docsif` -> `pip install sif`. No other README content changes.

Do NOT touch (out of scope, verified intentional): `docsift` cache-migration code in src/sif/cli/main.py (`docsift` is the older project name, a different string); docs/migration.md; .planning/milestones archives; root-level legacy files (PROJECT_SUMMARY.md, quick_test.py, etc. — historical `docsift` only); src/sif/mcp/README.md:21 (`.[mcp]` becomes valid via the new extra, needs no edit); src/ at all — the hints there are already correct.
  </action>
  <verify>
    <automated>grep -nE "^name = &quot;sif&quot;|^docsif|mcp = \[|http = \[" pyproject.toml && ! grep -nE "docsif([^ta-zA-Z]|$)" pyproject.toml README.md && grep -c "pip install sif" README.md</automated>
  </verify>
  <done>pyproject.toml has name=sif, single sif console script, no docsif keyword, mcp+http extras present; README.md install commands all say sif; standalone docsif count across both files is zero (docsift substring matches excluded by the grep pattern).</done>
</task>

<task type="auto">
  <name>Task 2: Regenerate uv.lock root entry and run full verification gates (import, CLI, ruff, pytest, grep)</name>
  <files>uv.lock</files>
  <action>
Run `uv lock` from the repo root to regenerate the lockfile — the root `[[package]]` entry (was `name = "docsif"` at line 589) becomes `name = "sif"` and the two new extras are recorded. Planner confirmed uv 0.12.12 resolves this project fine (108 packages, ~15ms) — the broken uv venv does not matter because `uv lock` only resolves against pyproject. If `uv lock` unexpectedly fails, fall back to manually editing the uv.lock root entry `name = "docsif"` -> `name = "sif"` (precedent: manual requires-python edit in commit d456cc9), keeping every other line identical.

Then run the full gate set in order:
1. `uv lock --check` (must exit 0)
2. `python -c "import sif; import sif.mcp"` and `python -m sif.cli.main --help` (system/conda python — NOT the uv venv)
3. Attempt `pip install -e .` — if it succeeds, also confirm `sif --help`; if the environment lacks pip/build tooling, record that and rely on gates 2 (the import+CLI checks are the accepted minimum per task requirements)
4. `ruff check src tests` and `ruff format --check src tests` (sanity — no Python source changed, must stay clean)
5. `env -u FORCE_COLOR NO_COLOR=1 python -m pytest` (expect ~675 passed; the 2 order-dependent caplog failures in tests/unit/embedding/test_openai_embedder.py are pre-existing, WINDOWS.md #3/#4 — do NOT chase them)
6. Final grep gate: `grep -rnE "docsif([^ta-zA-Z]|$)" pyproject.toml README.md docs/ src/ tests/ Makefile CONTRIBUTING.md CHANGELOG.md` must return ZERO hits. CRITICAL: the pattern excludes a following `t` because `docsif` is a substring of `docsift` (the old project name whose migration code in src/sif/cli/main.py is intentional and untouched) — a naive `grep -rn docsif` would false-positive on every `docsift`.

Commit via pathspec only (pyproject.toml README.md uv.lock); leave untracked runtime dirs (.gsd/, .planning/state.json, .planning/tmp/, .planning/ui-reviews/) and any other dirty files alone.
  </action>
  <verify>
    <automated>uv lock --check && python -c "import sif" && env -u FORCE_COLOR NO_COLOR=1 python -m pytest -q 2>&1 | tail -3 && [ -z "$(grep -rnE 'docsif([^ta-zA-Z]|$)' pyproject.toml README.md docs/ src/ tests/ Makefile CONTRIBUTING.md CHANGELOG.md 2>/dev/null)" ] && echo GREP-GATE-CLEAN</automated>
  </verify>
  <done>uv.lock root package is sif and `uv lock --check` exits 0; `import sif` and CLI --help work; ruff check + format clean; pytest green at baseline (~675 passed, pre-existing caplog pair excepted); standalone-docsif grep gate across all distribution-facing files returns zero hits.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| (none new) | Metadata/docs rename — no new code paths, no input handling changes |

## STRIDE Threat Register

| Threat ID | Category | Component | Severity | Disposition | Mitigation Plan |
|-----------|----------|-----------|----------|-------------|-----------------|
| T-260914-vyr-01 | Tampering (supply chain) | uv.lock regeneration | low | mitigate | No new packages: both new extras reference uvicorn, already a core dep already present in the lock; diff review of uv.lock must show only the root-name/extras change — any unrelated package churn is a stop-and-inspect signal |
| T-260914-vyr-02 | Repudiation | release identity | low | accept | Publishing under a new name is a PyPI-namespace concern outside this repo; no mitigation possible pre-publish |
</threat_model>

<verification>
- `uv lock --check` exits 0 with root package `sif`
- `python -c "import sif; import sif.mcp"` passes; `python -m sif.cli.main --help` runs
- `ruff check src tests` and `ruff format --check src tests` clean
- `env -u FORCE_COLOR NO_COLOR=1 python -m pytest` green at ~675 baseline (pre-existing caplog pair excepted)
- Standalone-docsif grep gate (with the `docsift`-excluding pattern) returns zero hits across pyproject.toml, README.md, docs/, src/, tests/, Makefile, CONTRIBUTING.md, CHANGELOG.md
- Audit BLOCKER 2 closure condition met: distribution name, console script, keywords, install hints, and lockfile all consistently say `sif`; `sif[mcp]`/`sif[http]`/`sif[embed]` extras all resolve
</verification>

<success_criteria>
- v1.0-MILESTONE-AUDIT.md BLOCKER 2 (MCP-01) is closable: `pip install sif`, `pip install "sif[all]"`, and every CLI error-message hint name a real package and real extras
- No behavior change: zero Python source edits, test suite at baseline, all `docsift` migration/history contexts intact
</success_criteria>

<output>
Create `.planning/quick/260914-vyr-rename-distribution-docsif-to-sif-pyproj/260914-vyr-SUMMARY.md` when done
</output>
