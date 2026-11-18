---
phase: quick-261112-qtl
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - pyproject.toml
  - src/sif/_version.py
  - src/sif/__init__.py
  - src/sif/cli/__init__.py
  - src/sif/config/constants.py
  - src/sif/mcp/protocol.py
  - example_config.yaml
  - uv.lock
  - tests/test_version_identity.py
  - docs/installation.md
  - docs/changelog.md
  - docs/configuration.md
  - scripts/generate_config_ref.py
  - examples/quickstart.py
  - src/sif/embedding/embedder.py
  - src/sif/cli/commands/mcp.py
  - src/sif/cli/commands/search.py
  - tests/unit/embedding/test_openai_embedder.py
autonomous: true
must_haves:
  truths:
    - "`python -c \"import sif; print(sif.__version__)\"` prints 1.1.1"
    - "CLI prints exactly `sif, version 1.1.1` and the MCP `InitializeResult().serverInfo[\"version\"]` is 1.1.1"
    - "`src/sif/_version.py` is the only module-level version literal in `src/`; package `__init__`, `sif.cli`, `APP_VERSION`, and the MCP serverInfo all derive from it"
    - "pyproject.toml declares `dynamic = [\"version\"]` sourced from `src/sif/_version.py`, and a wheel built from the tree is named `docsif-1.1.1-py3-none-any.whl`"
    - "Every install/upgrade/uninstall instruction and in-app remedy hint names the `docsif` distribution; the import package and command stay `sif`"
    - "docs/changelog.md contains exactly one `## [1.1.1] - 2026-11-12` section immediately before the 1.0.1 section"
  artifacts:
    - pyproject.toml
    - src/sif/_version.py
    - src/sif/__init__.py
    - src/sif/cli/__init__.py
    - src/sif/config/constants.py
    - src/sif/mcp/protocol.py
    - example_config.yaml
    - uv.lock
    - tests/test_version_identity.py
    - docs/installation.md
    - docs/changelog.md
    - docs/configuration.md
    - scripts/generate_config_ref.py
    - examples/quickstart.py
    - src/sif/embedding/embedder.py
    - src/sif/cli/commands/mcp.py
    - src/sif/cli/commands/search.py
    - tests/unit/embedding/test_openai_embedder.py
  key_links:
    - "src/sif/_version.py -> [tool.hatch.version].path -> built wheel metadata (docsif-1.1.1)"
    - "src/sif/_version.py -> sif.__version__ -> src/sif/cli/main.py `from sif import __version__` -> click.version_option -> docs/installation.md example"
    - "src/sif/_version.py -> InitializeResult serverInfo default -> example_config.yaml documented default"
    - "scripts/generate_config_ref.py -> docs/configuration.md (generator-owned; never hand-edited)"
---

<objective>
Align the project's release identity to 1.1.1 and stop version fragmentation: `src/sif/_version.py` becomes the single version literal, with pyproject packaging, the package `__init__`, `sif.cli`, `APP_VERSION`, and the MCP `serverInfo` all deriving from it. Then correct every user-facing install/upgrade/uninstall instruction and in-app remedy hint to name the published distribution `docsif`, and record the release in the changelog.

Purpose: today six separate places hardcode the same version (last touched by a prior quick task that re-edited each literal), the CLI/MCP/docs can silently drift, and several docs still tell users to install a non-existent distribution. This release makes future bumps a one-line edit and makes the release identity internally coherent.

Design decision (verified during planning): use hatchling's dynamic version source (`[tool.hatch.version] path = "src/sif/_version.py"`) rather than `importlib.metadata` at runtime. A live check showed the current editable install's dist-info still reports an older metadata version, so metadata is not a trustworthy runtime source in developer worktrees; a module constant always resolves correctly. A scratch reproduction confirmed `uv lock` treats a hatch-dynamic project as version-less in `uv.lock` (it drops the editable entry's `version` line) and `uv build` derives `docsif-1.1.1-py3-none-any.whl`.

Output: 18 files edited/created — one version literal, five derived runtime surfaces, dynamic packaging, lock refresh, a regression test, changelog entry, and corrected distribution-name guidance.
</objective>

<execution_context>
@~/.claude/gsd-core/workflows/execute-plan.md
@~/.claude/gsd-core/templates/summary.md
</execution_context>

<context>
@pyproject.toml
@src/sif/_version.py
@src/sif/__init__.py
@src/sif/cli/__init__.py
@src/sif/config/constants.py
@src/sif/mcp/protocol.py
@docs/installation.md
@docs/changelog.md
@src/sif/mcp/server.py
@src/sif/cli/main.py
</context>

<tasks>

<task type="auto">
  <name>Task 1: Single-source the version at 1.1.1 and add a regression test</name>
  <files>pyproject.toml, src/sif/_version.py, src/sif/__init__.py, src/sif/cli/__init__.py, src/sif/config/constants.py, src/sif/mcp/protocol.py, example_config.yaml, uv.lock, tests/test_version_identity.py</files>
  <action>
    Make `src/sif/_version.py` the sole version literal and derive every other identity from it. All edits below are exact; do not change any other line.

    1. `src/sif/_version.py`: set `__version__` to `"1.1.1"`. It must remain the only module-level version assignment in `src/`.

    2. `pyproject.toml`: in `[project]`, replace the static `version` key with `dynamic = ["version"]`; keep `name = "docsif"` and every other key untouched. Add a `[tool.hatch.version]` table containing `path = "src/sif/_version.py"` immediately above `[tool.hatch.build.targets.wheel]`. Do not touch the `python-frontmatter` dependency pin.

    3. `src/sif/__init__.py`: put all imports at the top (module docstring, then `from sif._version import __version__`, then the existing `sif.core.models` import block; isort orders `sif._version` before `sif.core.models`). Keep `__author__`, `__description__`, and the existing `__all__` entries byte-identical otherwise.

    4. `src/sif/cli/__init__.py`: replace the version literal with `from sif._version import __version__` placed after the module docstring; keep `__author__` and `__all__` unchanged.

    5. `src/sif/config/constants.py`: add `from sif._version import __version__` after the module docstring and set `APP_VERSION = __version__` (keep the `# Application info` comment). Every other constant, including `MCP_VERSION` and `CURRENT_SCHEMA_VERSION`, stays untouched.

    6. `src/sif/mcp/protocol.py`: add `from sif._version import __version__` to the first-party import block and use it as the `version` value inside the `InitializeResult.serverInfo` default_factory dict. Keep the server name `sif-mcp-server`, the `protocolVersion`, and every other field unchanged.

    7. `example_config.yaml`: under the `mcp:` block, update both the `# Default:` comment and the `version:` value that document the MCP server version to 1.1.1.

    8. `uv.lock`: in the `[[package]]` entry for `name = "docsif"`, delete its `version` line. Hatch dynamic versioning makes uv omit that field; planning-time verification showed that after this removal `uv lock` is a no-op and `uv lock --check --offline` exits 0. Do not upgrade or re-resolve dependencies; if `uv lock` would produce any other diff, revert to the hand edit.

    9. Add `tests/test_version_identity.py` (module docstring, `from __future__ import annotations`) asserting:
       - pyproject wiring: the `[project]` table declares `dynamic = ["version"]` and has no static `version` key, and `[tool.hatch.version].path` equals `src/sif/_version.py`. Parse with stdlib `tomllib` inside a `try/except ModuleNotFoundError` guard because the project supports Python 3.10, which lacks `tomllib`; on 3.10 fall back to a section-scoped text assertion and add no new dependency.
       - runtime coherence: `sif.__version__`, `sif._version.__version__`, `sif.cli.__version__`, `sif.config.constants.APP_VERSION`, and `sif.mcp.protocol.InitializeResult().serverInfo["version"]` are all equal and match `^\d+\.\d+\.\d+$`. Do not hardcode 1.1.1 in the test — the release literal stays single-sourced in `_version.py`; the task verify asserts the concrete value.
       - literal uniqueness: scan `src/sif/**/*.py`; the only module-level assignment matching the `__version__ = "<literal>"` shape is in `_version.py`, and there is no `APP_VERSION = "<literal>"` assignment anywhere.
       - CLI wiring: `click.testing.CliRunner` invoking the root CLI with `--version` prints a line containing `sif, version ` followed by `sif.__version__`.

    Rationale: the prior release quick task (261107-f5t) re-edited six literals; this wiring makes every future bump one edit and the new test makes re-fragmentation a test failure. No test currently pins any version string, so no existing assertion conflicts.
  </action>
  <verify>
    <automated>PYTHONPATH=src python -c "import sif, sif._version, sif.cli; from sif.config.constants import APP_VERSION; from sif.mcp.protocol import InitializeResult; assert sif.__version__ == sif._version.__version__ == sif.cli.__version__ == APP_VERSION == InitializeResult().serverInfo['version'] == '1.1.1'; print('versions-ok')" && env -u FORCE_COLOR NO_COLOR=1 PYTHONPATH=src python -m sif.cli.main --version | grep -qx 'sif, version 1.1.1' && env -u FORCE_COLOR NO_COLOR=1 python -m pytest tests/test_version_identity.py -q --no-cov && uv lock --check --offline && rm -rf /tmp/sif-version-check && uv build --wheel --out-dir /tmp/sif-version-check >/dev/null && test -f /tmp/sif-version-check/docsif-1.1.1-py3-none-any.whl</automated>
  </verify>
  <done>
    - versions-ok printed; all five runtime surfaces equal 1.1.1
    - CLI prints exactly `sif, version 1.1.1`; MCP serverInfo version is 1.1.1
    - tests/test_version_identity.py passes; pyproject is dynamic-versioned from `src/sif/_version.py`
    - `uv lock --check --offline` exits 0 with no unexpected lock churn
    - `uv build` produces a wheel named `docsif-1.1.1-py3-none-any.whl`
    - `rg -n '__version__\s*=\s*["\x27]' src/sif` shows only `_version.py`
  </done>
</task>

<task type="auto">
  <name>Task 2: Correct install/upgrade/uninstall guidance to the docsif distribution and add the 1.1.1 changelog entry</name>
  <files>docs/installation.md, docs/changelog.md, docs/configuration.md, scripts/generate_config_ref.py, examples/quickstart.py, src/sif/embedding/embedder.py, src/sif/cli/commands/mcp.py, src/sif/cli/commands/search.py, tests/unit/embedding/test_openai_embedder.py</files>
  <action>
    Correct every install, upgrade, and uninstall instruction plus in-app remedy hint that names the package so it names the published distribution `docsif`. Never change the import package or console command `sif`, the `SIF_` environment prefix, data paths, or `docs/migration.md` (historical rename guidance).

    1. `docs/installation.md`: in the macOS Homebrew block, make the install command name `docsif`; in Troubleshooting "ImportError: No module named 'sif'", make the force-reinstall command name `docsif`; in Uninstallation, make the uninstall command name `docsif`; update the `sif --version` expected-output example to `sif, version 1.1.1` so it matches the task 1 CLI output exactly. Leave the import-module name, command name, env prefix, and data directories untouched.

    2. `docs/changelog.md`: insert `## [1.1.1] - 2026-11-12` immediately after the `[Unreleased]` block ends and before the `[1.0.1]` section, in Keep a Changelog style with exactly two subsections. `### Changed`: the release version is now single-sourced in `src/sif/_version.py`, and packaging, `sif.__version__`, `sif.cli.__version__`, `APP_VERSION`, and the MCP `serverInfo` version all derive from it. `### Fixed`: install, upgrade, and uninstall instructions and in-app remedy hints now name the published `docsif` distribution. In the existing Upgrading command example, make the upgrade command name `docsif`. Append `[1.1.1]: https://github.com/zhangtaolab/sif/releases/tag/v1.1.1` above the existing `[1.0.1]:` reference line and retarget the `[Unreleased]` compare link to compare against `v1.1.1`. Do not restructure the `[Unreleased]` content or the Release Notes Template.

    3. `scripts/generate_config_ref.py`: in the backend-selection paragraph that documents the embed extra, make the install hint name `docsif`. This script is the source of truth for generated docs. Then run `python scripts/generate_config_ref.py` from the repo root and confirm the only generated change is that single line in `docs/configuration.md`. Never hand-edit `docs/configuration.md` or `docs/cli-reference.md`; `docs/cli-reference.md` must be byte-identical after the generator run.

    4. `examples/quickstart.py`: replace the bare distribution name with `docsif` in the three install instructions (module docstring, the "not installed" message, and the closing instructions).

    5. In-app hints: in `src/sif/embedding/embedder.py`, the OpenAI ImportError message's extras hint must name `docsif`; in `src/sif/cli/commands/mcp.py`, both optional-dependency ClickException extras hints (MCP and HTTP) must name `docsif`; in `src/sif/cli/commands/search.py`, replace the reranker ImportError warning's editable-source install hint with a published-distribution extras hint naming `docsif` and its embed extra (the current hint assumes a source checkout and is wrong for installed users). Keep every surrounding message and exception type unchanged.

    6. `tests/unit/embedding/test_openai_embedder.py`: tighten the install-hint assertion to require the full `docsif[openai]` fragment instead of the suffix-only fragment, which currently passes even if the distribution prefix regresses.

    Out of scope: historical changelog rows, `docs/migration.md`, the `sif` command name, and third-party dependency names such as sqlite-vec, sentence-transformers, llama-cpp-python, and modelscope.
  </action>
  <verify>
    <automated>python scripts/generate_config_ref.py && git diff --quiet -- docs/cli-reference.md && env -u FORCE_COLOR NO_COLOR=1 python -m pytest tests/unit/embedding/test_openai_embedder.py tests/unit/cli/test_search.py tests/test_docs.py -q --no-cov && ruff check src tests && ruff format --check src tests && test "$(grep -c '^## \[1.1.1\] - 2026-11-12$' docs/changelog.md)" = "1" && rg -q 'docsif\[embed\]' docs/configuration.md && rg -q 'pip install --upgrade docsif' docs/changelog.md && rg -q 'pip uninstall docsif' docs/installation.md && rg -q 'pip install --force-reinstall docsif' docs/installation.md && rg -q 'sif, version 1\.1\.1' docs/installation.md && rg -q 'docsif\[openai\]' src/sif/embedding/embedder.py && rg -q 'docsif\[openai\]' tests/unit/embedding/test_openai_embedder.py && rg -q 'docsif\[mcp\]' src/sif/cli/commands/mcp.py && rg -q 'docsif\[http\]' src/sif/cli/commands/mcp.py && rg -q 'docsif\[embed\]' src/sif/cli/commands/search.py && test -z "$(rg -n --pcre2 '(?<!doc)sif\[(openai|mcp|http|embed|all|dev)\]' src docs examples tests README.md)" && test -z "$(rg -n '((pip3?|pipx)[[:space:]]+(install|uninstall|upgrade)|--force-reinstall|--upgrade)[^#]*[[:space:]]sif([^A-Za-z0-9_-]|$)' docs/installation.md docs/changelog.md examples/quickstart.py)"</automated>
  </verify>
  <done>
    - docs/configuration.md regenerated with the corrected `docsif` embed hint; docs/cli-reference.md unchanged
    - changelog has exactly one `## [1.1.1] - 2026-11-12` section between Unreleased and 1.0.1, with Changed and Fixed subsections and a 1.1.1 reference link
    - installation.md uses `docsif` for install/force-reinstall/uninstall and shows `sif, version 1.1.1`
    - in-app hints in embedder.py, commands/mcp.py, and commands/search.py name `docsif`; the OpenAI test asserts the full fragment
    - negative sweep finds no bare pre-`docsif` extras form and no bare distribution name in pip install/uninstall/upgrade commands
    - targeted tests pass; ruff check and format-check clean
  </done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| MCP client -> server | `serverInfo.version` is returned to MCP clients in the initialize response; the value now derives from the package constant |
| User -> package index | Install/upgrade/uninstall commands are copy-pasted by users against PyPI; a wrong distribution name can fetch or remove the wrong package |
| Build backend -> package metadata | Hatchling reads the version literal from `src/sif/_version.py` at build time |

No new runtime trust boundaries; this change alters version metadata, packaging configuration, and documentation text only.

## STRIDE Threat Register

| Threat ID | Category | Component | Severity | Disposition | Mitigation Plan |
|-----------|----------|-----------|----------|-------------|-----------------|
| T-qtl-01 | Information Disclosure | `src/sif/mcp/protocol.py` serverInfo version in initialize response | low | accept | SIF is a local-first tool and already self-reported a version; the new value is accurate and still only exposes the public release number |
| T-qtl-02 | Tampering | Build metadata derivation via `[tool.hatch.version]` | low | mitigate | The version path is pinned to the in-repo `src/sif/_version.py`; the new test asserts the path and dynamic declaration, and `uv build` verifies the wheel name |
| T-qtl-03 | Spoofing | User-facing install/upgrade/uninstall commands pointing at a wrong distribution | medium | mitigate | All instructions and hints are corrected to the published `docsif` name, with a negative sweep gate preventing bare-name regressions |
| T-qtl-SC | Tampering | `uv lock` / package manager operations | high | accept | No package installs, upgrades, or new dependencies: the lock change removes the project's own editable version line to match hatch dynamic versioning; `uv lock --check --offline` confirms consistency and the diff is inspected for churn |
</threat_model>

<verification>
1. Task 1 gates: five runtime surfaces report 1.1.1, CLI prints `sif, version 1.1.1`, the regression test passes, `uv lock --check --offline` is clean, and a wheel builds as `docsif-1.1.1-py3-none-any.whl`.
2. Task 2 gates: generator run leaves `docs/cli-reference.md` untouched and updates only the hint line in `docs/configuration.md`; changelog ordering/count gate passes; all distribution-name positive and negative sweeps pass; targeted tests and ruff gates pass.
3. Final project quality suite per CLAUDE.md: `ruff check src tests && ruff format --check src tests && pytest -q` (full suite; the FORCE_COLOR hermeticity fix is on this branch, so no env workaround is needed).
4. Scope check: `git diff --stat` (plus untracked `tests/test_version_identity.py`) shows exactly the files listed in `files_modified` and nothing else; no deletions.
</verification>

<success_criteria>
- The release identity is coherent at 1.1.1 across packaging, package `__init__`, `sif.cli`, `APP_VERSION`, and MCP serverInfo, with `src/sif/_version.py` as the only literal.
- A built wheel from the tree is named for version 1.1.1 and the lockfile is consistent (`uv lock --check`).
- `docs/changelog.md` documents the 1.1.1 release in Keep a Changelog format.
- Every install/upgrade/uninstall instruction and in-app remedy hint names `docsif`; the import package and command remain `sif`.
- The regression test prevents re-fragmenting the version and future release bumps become a one-line edit.
- Full quality suite green.
</success_criteria>

<output>
Create `.planning/quick/261112-qtl-align-release-identity-to-1-1-1/261112-qtl-SUMMARY.md` when done
</output>
