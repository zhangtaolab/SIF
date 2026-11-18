---
phase: quick-261118-jbj
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - src/sif/_version.py
  - server.json
  - .claude-plugin/plugin.json
  - .claude-plugin/marketplace.json
  - docs/changelog.md
  - tests/test_release_metadata.py
  - README.md
  - docs/installation.md
  - docs/index.md
  - docs/quickstart.md
  - docs/mcp-server.md
  - tests/test_docs.py
  - tests/test_ci_workflows.py
autonomous: true
requirements: [QUICK-RELEASE-1-2-1]  # quick task: release v1.2.1 bump + install backend matrix
estimate:
  tokens: 36000
  raw_tokens: 36000
  tasks: 3
  confidence: low

must_haves:
  truths:
    - "`sif --version` reports 1.2.1: src/sif/_version.py is the only version literal and it now reads 1.2.1, with server.json (top-level and packages[0].version), .claude-plugin/plugin.json, and .claude-plugin/marketplace.json (plugins[0].version) all equal to it."
    - "docs/changelog.md carries a `## [1.2.1] - 2026-11-18` section between Unreleased and 1.2.0, the link block points `[Unreleased]` at compare/v1.2.1...HEAD and adds `[1.2.1]`, and every historical 1.2.0/1.1.x entry is unchanged."
    - "tests/test_release_metadata.py pins 1.2.1 through renamed tests (`test_changelog_has_1_2_1`, `test_version_literal_is_1_2_1`)."
    - "Install guidance in README.md, docs/installation.md, docs/index.md, docs/quickstart.md, and docs/mcp-server.md presents --torch-backend=auto as the recommended Linux GPU path, --torch-backend=cpu as the CPU-only path, macOS with no backend flag, and a pip matrix (CPU index vs CUDA index) that states pip cannot auto-detect the GPU; the uv tool -> uvx -> pip section ordering is unchanged."
    - "docs/installation.md shows `sif, version 1.2.1` in the verification sample, and the docs tests require --torch-backend=auto and the macOS no-flag note while still requiring --torch-backend=cpu, the CPU index URL, and the uv 0.9.19 floor."
    - "The full quality suite is green: ruff check src tests, ruff format --check src tests, and the full pytest run under `uv run --frozen --extra dev --extra embed`."
  artifacts:
    - "src/sif/_version.py — __version__ = \"1.2.1\""
    - "server.json — top-level version and packages[0].version both 1.2.1"
    - ".claude-plugin/plugin.json — version 1.2.1"
    - ".claude-plugin/marketplace.json — plugins[0].version 1.2.1"
    - "docs/changelog.md — new 1.2.1 section plus updated Unreleased/[1.2.1] link targets"
    - "tests/test_release_metadata.py — renamed and re-pinned 1.2.1 release-metadata tests"
    - "README.md — uv tool auto/cpu/macOS matrix and pip CPU-vs-CUDA matrix"
    - "docs/installation.md — Method 1 uv tool matrix, Method 3 pip matrix, Linux and macOS notes, and the 1.2.1 version sample"
    - "docs/index.md, docs/quickstart.md, docs/mcp-server.md — consistent auto/cpu/macOS install snippets"
    - "tests/test_docs.py, tests/test_ci_workflows.py — assertions for auto and the macOS no-flag note, keeping the CPU recipe/index/uv-floor requirements"
  key_links:
    - "src/sif/_version.py -> server.json, .claude-plugin/plugin.json, .claude-plugin/marketplace.json is enforced by tests/unit/mcp/test_registry_script.py and tests/unit/mcp/test_plugin.py::test_manifest_version_parity"
    - "docs/changelog.md heading and link block -> tests/test_release_metadata.py literal assertions"
    - "docs/installation.md backend matrix -> tests/test_docs.py::TestInstallAndModelDocs and tests/test_ci_workflows.py torch-backend assertions"
    - "README.md and the three secondary docs -> docs/installation.md recipe wording (manual consistency; no test pins the secondary files)"
---

<objective>
Ship the v1.2.1 release metadata and the corrected install backend guidance.

This plan is one end-to-end release surface: the single version literal in `src/sif/_version.py` must reach all three parity manifests, the changelog, and the release-metadata tests in one atomic change (Task 1); then the install docs must stop telling every Linux user to force `--torch-backend=cpu` and instead present the verified matrix — `auto` for Linux GPU, `cpu` for CPU-only, no flag on macOS, and a pip CPU-vs-CUDA index matrix (Tasks 2 and 3).

Purpose: publish `docsif` 1.2.1 with accurate, driver-aware install instructions.
Output: 13 edited files, no new code paths, no dependency or workflow changes.

Scope boundaries (locked):
- Do NOT touch `pyproject.toml`, `uv.lock`, `[tool.uv.sources]`, or the `torch>=2.14` floor; the Linux CPU lock contract stays.
- Do NOT tag, push, publish, or close GitHub issues; no `.github/workflows/` changes.
- Do NOT modify historical changelog entries or historical prose about v1.2.0 (`src/sif/embedding/manager.py`, `src/sif/models/download.py`, `docs/migration.md`, `tests/unit/models/test_download.py`).
- The unrelated `1.2.0` in `uv.lock` (backports-asyncio-runner) and the `"1.2.0"` argument fixture in `tests/test_windows_smoke_script.py` are not release surfaces and stay untouched.
</objective>

<execution_context>
@~/.claude/gsd-core/workflows/execute-plan.md
@~/.claude/gsd-core/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md
@src/sif/_version.py
@server.json
@.claude-plugin/plugin.json
@.claude-plugin/marketplace.json
@docs/changelog.md
@tests/test_release_metadata.py
@README.md
@docs/installation.md
@tests/test_docs.py
@tests/test_ci_workflows.py

Planning-time observations (live, 2026-11-18, HEAD c2813c5, tree clean):

- Version source: src/sif/_version.py line 3 is `__version__ = "1.2.0"`. It is the only version literal; pyproject takes `version` dynamically from it.
- Parity surfaces: server.json top-level `version` (line 5) and `packages[0].version` (line 10); .claude-plugin/plugin.json `version` (line 3); .claude-plugin/marketplace.json `plugins[0].version` (line 12). `tests/unit/mcp/test_plugin.py::TestPluginManifest::test_manifest_version_parity` and `tests/unit/mcp/test_registry_script.py` compare them against `sif._version.__version__`, so a partial bump fails.
- `tests/test_release_metadata.py` has `test_changelog_has_1_2_0` (asserts `## [1.2.0]`, `[1.2.0]:`, `compare/v1.2.0...HEAD`) and `test_version_literal_is_1_2_0` (asserts `1.2.0`). The Unreleased link currently targets `compare/v1.2.0...HEAD`, and that literal disappears from docs/changelog.md once Unreleased moves to v1.2.1 — the test must be updated, not just the version test.
- docs/changelog.md: `## [Unreleased]` block runs to line ~36; `## [1.2.0] - 2026-11-18` begins at line 38; the link block is at lines 262-266 (`[Unreleased]`, `[0.1.0]`, `[1.2.0]`, `[1.1.2]`, `[1.1.1]`, `[1.0.1]`).
- Commits since tag v1.2.0 are the 1.2.1 content: a13b134/8691c41 (`torch>=2.14` floor), 5f9c086/36b3150 (issues #4 and #5: embedder L2 renormalization, `<cache>/models` root), 26ac78c/ffad91b/c2813c5 (cache-read renormalization and test/doc follow-ups). Milestone bookkeeping commits (46cb115..5d6fac3) also sit in that range and need no changelog entry.
- docs/installation.md: Method 1 at lines 20-55 (CPU-first framing), Method 2 uvx at 56-65, Method 3 pip at 66-81, Linux section at 256-272 ("Use the CPU torch recipe ... so no CUDA stack is pulled in"), macOS at 274-288, version sample `sif, version 1.2.0` at line 325.
- Secondary snippets to keep consistent: README.md lines 37-90 (uv tool block, VERIFY comment at line 53, pip block at 79-92), docs/index.md lines 68-80, docs/quickstart.md lines 51-64, docs/mcp-server.md lines 262-286.
- Verified uv 0.13.8 behavior (this Linux host, RTX 5090, driver CUDA 13.2): plain `uv pip install torch==2.15.0` resolves the Linux wheel plus the full nvidia-cu13 stack; `--torch-backend=auto` and `--torch-backend=cu132` resolve `torch==2.15.0+cu132`; `--torch-backend=cpu` resolves `2.15.0+cpu`; `--torch-backend=cu130` with torch 2.15.0 has no solution. macOS arm64 resolves one `torch==2.15.0` wheel with MPS and no nvidia dependencies under plain install or auto; `--torch-backend=cpu` has no matching macOS wheel for 2.15.0. `uv --help` confirms `--torch-backend` on `uv tool install`, `uv tool run`/`uvx`, and `uv pip install` (uv 0.9.19+); `UV_TORCH_BACKEND` is the env equivalent. `uv lock`/`uv add`/`uv sync`/`uv run` do not take the flag; the repo's own lock keeps the explicit Linux CPU index.
- Docs test constraints that must survive: `tests/test_docs.py::TestInstallAndModelDocs::test_installation_doc_is_uv_first` requires `uv tool install`, `--torch-backend=cpu`, `uvx`, `llama-cpp-python` and the order uv tool < uvx < pip install (first `text.index("pip install")` — do not put the literal `pip install` in earlier prose). `tests/test_ci_workflows.py` has `TORCH_BACKEND_RECIPE = "--torch-backend=cpu"`, `CPU_INDEX_URL = "https://download.pytorch.org/whl/cpu"`, and requires `uv 0.9.19` in installation.md; `test_installation_docs_do_not_claim_pyproject_index_for_tool_installs` forbids two stale pyproject-index phrases (lowercased).
- `tests/test_hygiene.py::test_bandit_verify_marker_retained` scans only `docs/**/*.md`, so README's `<!-- VERIFY: ... -->` markers are not counted; keep exactly the existing two README markers, updating the torch one's text.
- docs bash blocks are only executed for lines starting with `sif `; `uv` lines are ignored by tests/test_docs.py.
</context>

<tasks>

<task type="auto">
  <name>Task 1: Bump the release version to 1.2.1 across every parity surface, changelog, and release-metadata test</name>
  <files>src/sif/_version.py, server.json, .claude-plugin/plugin.json, .claude-plugin/marketplace.json, docs/changelog.md, tests/test_release_metadata.py</files>
  <precondition>The checkout is at HEAD with a clean tree, and `uv` is on PATH; the targeted tests need no network, model weights, or GPU.</precondition>
  <action>
    One atomic version unit: if any surface is left at 1.2.0, the parity tests fail, so edit all six files before verifying.

    1. src/sif/_version.py: change `__version__ = "1.2.0"` to `__version__ = "1.2.1"`. This stays the only version literal.

    2. server.json: change the top-level `"version": "1.2.0"` and the `packages[0]` `"version": "1.2.0"` to `"1.2.1"`. Do not touch `name`, `description`, `registryType`, `identifier`, or `transport`.

    3. .claude-plugin/plugin.json: change `"version": "1.2.0"` to `"1.2.1"`. Do not touch any other key.

    4. .claude-plugin/marketplace.json: change `plugins[0].version` from `"1.2.0"` to `"1.2.1"`; leave the marketplace `name`, `description`, `owner`, and plugin `name`/`source`/`description` as-is.

    5. docs/changelog.md: insert a new section directly before `## [1.2.0] - 2026-11-18` and after the Unreleased block, exactly:

    ## [1.2.1] - 2026-11-18

    ### Changed
    - The release version is now `1.2.1`, still single-sourced in `src/sif/_version.py`.
    - The `embed` and `all` extras now declare `torch>=2.14`; `uv.lock` was regenerated against the unchanged explicit Linux CPU index.

    ### Fixed
    - Sentence-transformers and ModelScope embedder output is renormalized to unit L2 length, so off-unit model output (Qwen3-Embedding norms 0.9985-1.0036) no longer trips the embedding writer's L2-norm gate (#4).
    - Embedding-cache rows written by earlier versions are renormalized on read, so upgrading with a populated embeddings cache no longer aborts `sif index embed` (#4).
    - Embedders, rerankers, downloads, and `sif models status` now share `<cache>/models/<owner>/<name>`, and the pre-fix v1.2.0 `<cache>/<owner>/<name>` layout migrates automatically (#5).

    Do not alter the existing `## [1.2.0] - 2026-11-18` section, the `## [Unreleased]` body, or any 1.1.x section.

    6. docs/changelog.md link block: change `[Unreleased]: https://github.com/zhangtaolab/sif/compare/v1.2.0...HEAD` to `.../compare/v1.2.1...HEAD`, and insert `[1.2.1]: https://github.com/zhangtaolab/sif/releases/tag/v1.2.1` immediately before the existing `[1.2.0]:` line. Leave `[0.1.0]`, `[1.2.0]`, `[1.1.2]`, `[1.1.1]`, and `[1.0.1]` untouched.

    7. tests/test_release_metadata.py: rename `test_changelog_has_1_2_0` to `test_changelog_has_1_2_1`, update its docstring to say 1.2.1, and change its three literals to `"## [1.2.1]"`, `"[1.2.1]:"`, and `"compare/v1.2.1...HEAD"`. Rename `test_version_literal_is_1_2_0` to `test_version_literal_is_1_2_1`, update the docstring, and assert `version == "1.2.1"`. Do not change the other release-metadata tests (publish workflow, README marker, classifiers, docs process).
  </action>
  <verify>
    <automated>uv run --frozen --extra dev --extra embed python -m pytest tests/test_release_metadata.py tests/unit/mcp/test_plugin.py tests/unit/mcp/test_registry_script.py -q --no-cov</automated>
  </verify>
  <done>
    - src/sif/_version.py reads 1.2.1 and is still the only version literal in the tree
    - server.json (both version fields), plugin.json, and marketplace.json all read 1.2.1
    - docs/changelog.md has `## [1.2.1] - 2026-11-18`, Unreleased targets compare/v1.2.1...HEAD, and `[1.2.1]:` is present; the 1.2.0 section and older entries are byte-unchanged
    - tests/test_release_metadata.py has the two renamed 1.2.1 tests and the targeted pytest run is green (including both parity test modules)
    - pyproject.toml, uv.lock, and .github/workflows/** are untouched
  </done>
</task>

<task type="auto">
  <name>Task 2: Rewrite the primary install guidance (README + installation.md) to the auto/cpu/macOS + pip matrix and pin it in the docs tests</name>
  <files>README.md, docs/installation.md, tests/test_docs.py, tests/test_ci_workflows.py</files>
  <precondition>None beyond the checkout: the docs tests are text-level and the uv behavior matrix is already recorded in the plan context (verified on uv 0.13.8).</precondition>
  <action>
    Replace the unconditional Linux `--torch-backend=cpu` recommendation with the verified matrix while keeping every existing test requirement (`--torch-backend=cpu`, the CPU index URL, the uv 0.9.19 floor, uv tool -> uvx -> pip ordering).

    1. README.md `### Recommended: uv tool install` block (lines ~39-54): replace the two-command block with three labelled commands — `uv tool install --torch-backend=auto 'docsif[embed]'` (Linux with an NVIDIA GPU, recommended; uv selects the CUDA build for the driver), `uv tool install --torch-backend=cpu 'docsif[embed]'` (Linux CPU-only; no CUDA stack), and `uv tool install 'docsif[embed]'` (macOS; no backend flag, the macOS wheel includes MPS). Then replace the following prose and VERIFY comment with: `--torch-backend` is supported by `uv tool` and `uvx` from uv 0.9.19 onward and `UV_TORCH_BACKEND` is the equivalent environment variable; without a flag Linux resolves PyPI's CUDA-enabled torch wheel and pulls the full CUDA stack; `auto` matches the wheel to the driver and `cpu` installs CPU-only wheels. Keep the README's `<!-- VERIFY: ... -->` marker count at exactly two and make the torch marker say the auto/cpu/macOS matrix was verified by hand on Linux (uv 0.13.8, torch 2.15.0) and by uv target resolution for macOS arm64, not CI-proven. Keep the base (`uv tool install docsif`) and `all` blocks unchanged.

    2. README.md `### With pip` block: replace the single CPU-only recipe with a matrix — CPU-only (`pip install torch --index-url https://download.pytorch.org/whl/cpu` then `pip install "docsif[embed]"`), NVIDIA GPU (`pip install torch --index-url https://download.pytorch.org/whl/cu132` for the CUDA 13.2 wheel, then `pip install "docsif[embed]"`), and macOS (no torch pre-install; `pip install "docsif[embed]"`). Add one sentence: pip cannot auto-detect the GPU, so pick the index URL that matches the driver. Keep the BM25-only and `all` lines.

    3. docs/installation.md Method 1 (lines ~20-55): restructure to the same three-command matrix with short comments, then prose stating that `--torch-backend` is resolved by `uv tool install` and `uv pip` commands (uv 0.9.19 or newer), `UV_TORCH_BACKEND` is equivalent, and that without the flag Linux pulls the CUDA stack. Add the exact one-line sentence (keep it on one line, with literal backticks and no backslashes): Do not pass `--torch-backend=cpu` on macOS: the macOS wheel already includes MPS, and the CPU backend has no matching macOS wheel for the current torch fleet. Keep the `uv tool upgrade` / `--force` block, the base install, and the `all` extra content. Replace the "verified by hand on uv 0.13.7" sentence with the uv 0.13.8 / torch 2.15.0 / macOS-arm64-resolution wording. Do not introduce the literal `pip install` before Method 3 (the ordering assertion uses the first occurrence).

    4. docs/installation.md Method 3 (lines ~66-81): replace the CPU-first framing with the pip matrix — CPU-only index, CUDA index (`https://download.pytorch.org/whl/cu132`, labelled "match the tag to your driver"), and a note that pip cannot auto-detect the GPU; keep the `uvx` method untouched between Method 1 and Method 3, and keep the base and `all` install blocks.

    5. docs/installation.md Linux section (lines ~256-272): replace "Use the [CPU torch recipe] ... so no CUDA stack is pulled in" with: for the embedding stack, `--torch-backend=auto` is the recommended Linux GPU path (uv selects the CUDA build for the driver) and `--torch-backend=cpu` is the CPU-only path; keep the distro toolchain commands.

    6. docs/installation.md macOS section (lines ~274-288): keep `uv tool install 'docsif[embed]'` and the existing MPS paragraph, and add the same one-line "Do not pass `--torch-backend=cpu` on macOS: ..." sentence so the literal appears in the macOS section as well.

    7. docs/installation.md version sample (line ~325): change `sif, version 1.2.0` to `sif, version 1.2.1`.

    8. tests/test_docs.py::TestInstallAndModelDocs::test_installation_doc_is_uv_first: extend the required tuple to `("uv tool install", "--torch-backend=auto", "--torch-backend=cpu", "uvx", "llama-cpp-python")` and update the docstring to say the doc leads with uv tool, then uvx, then pip and carries the auto/cpu backend matrix. Keep the ordering assertion unchanged.

    9. tests/test_docs.py: add a new test in the same class, `test_installation_doc_warns_against_cpu_backend_on_macos`, asserting the substring "Do not pass `--torch-backend=cpu` on macOS" is in docs/installation.md, with a docstring explaining the CPU backend has no macOS wheel for the current torch fleet.

    10. tests/test_ci_workflows.py: next to `TORCH_BACKEND_RECIPE`, add `TORCH_BACKEND_AUTO = "--torch-backend=auto"`; in `test_installation_docs_are_uv_first` require `(UV_TOOL_INSTALL, TORCH_BACKEND_AUTO, TORCH_BACKEND_RECIPE, "uvx")` and update the docstring; in `test_installation_docs_cpu_recipe_and_pip_alternative`, keep the `TORCH_BACKEND_RECIPE`, `CPU_INDEX_URL`, and `uv 0.9.19` assertions, add the macOS no-flag literal and a CUDA-index presence check for `"https://download.pytorch.org/whl/cu"`, and update the docstring to state the matrix keeps the CPU recipe and adds auto plus the macOS note.

    Do not edit docs/index.md, docs/quickstart.md, or docs/mcp-server.md in this task; Task 3 owns those. Do not change SKIP_COMMAND_PATTERNS or any command-execution logic in tests/test_docs.py.
  </action>
  <verify>
    <automated>uv run --frozen --extra dev --extra embed python -m pytest tests/test_docs.py tests/test_ci_workflows.py -q --no-cov</automated>
  </verify>
  <done>
    - README and docs/installation.md both present auto (Linux GPU, recommended), cpu (Linux CPU-only), and macOS with no flag, plus a pip CPU-vs-CUDA index matrix stating pip cannot auto-detect
    - docs/installation.md keeps the literal `--torch-backend=cpu`, the CPU index URL, the uv 0.9.19 floor, the `uv tool install` -> `uvx` -> `pip install` order, and shows `sif, version 1.2.1`
    - docs/installation.md contains the one-line "Do not pass `--torch-backend=cpu` on macOS: ..." sentence in the macOS section
    - tests/test_docs.py and tests/test_ci_workflows.py require `--torch-backend=auto` and the macOS note in addition to the retained CPU requirements, and both modules pass
    - No pyproject.toml, uv.lock, workflow, or secondary-doc file is modified by this task
  </done>
</task>

<task type="auto">
  <name>Task 3: Align the secondary install snippets with the same matrix, then run the full quality gates</name>
  <files>docs/index.md, docs/quickstart.md, docs/mcp-server.md</files>
  <precondition>Tasks 1 and 2 are complete, so the canonical wording and the 1.2.1 version live in docs/installation.md and the primary tests already pin it.</precondition>
  <action>
    1. docs/index.md `## Installation` block (lines ~68-80): replace the two-command block with the three-command matrix — `uv tool install --torch-backend=auto 'docsif[embed]'` (Linux with an NVIDIA GPU, recommended), `uv tool install --torch-backend=cpu 'docsif[embed]'` (Linux CPU-only), `uv tool install 'docsif[embed]'` (macOS, no backend flag; the wheel includes MPS) — and keep the BM25-only base and the `all` blocks. Keep the pointer to the Installation Guide.

    2. docs/quickstart.md `## Installation` block (lines ~51-64): apply the identical three-command matrix, then replace the "manually verified on Linux with uv 0.13.7" sentence with the uv 0.13.8 / torch 2.15.0 wording plus "macOS needs no backend flag". Keep the `all` extra Python 3.12 note and the uvx one-off line.

    3. docs/mcp-server.md `### Install SIF` section (lines ~262-286): replace the CUDA-warning plus CPU-only-flag paragraph with the three-command matrix in the same order (auto recommended for Linux GPU, cpu for CPU-only, macOS no flag), keep the base BM25-only install and the note that `uv tool install` is required before the plugin, and keep the sentence that the `UV_TORCH_BACKEND` environment variable is equivalent.

    4. Run the full quality suite in CLAUDE.md order under the frozen lock: `ruff check src tests`, `ruff format --check src tests`, then the full `pytest` run. Fix only failures caused by this plan. Do not chase pre-existing skips or platform-specific failures.

    5. Final scope audit: `git status --porcelain` must show only the 13 files in this plan's `files_modified` plus `.planning/` artifacts. Confirm by inspection that pyproject.toml, uv.lock, .github/workflows/**, src/sif/embedding/manager.py, src/sif/models/download.py, docs/migration.md, and tests/test_windows_smoke_script.py are unmodified. Leave the tree for the standard single commit (`chore(release): bump to 1.2.1 and document the torch backend matrix`); do not tag, push, publish, or touch GitHub issues.
  </action>
  <verify>
    <automated>
      uv run --frozen --extra dev --extra embed ruff check src tests
      uv run --frozen --extra dev --extra embed ruff format --check src tests
      uv run --frozen --extra dev --extra embed python -m pytest -q
    </automated>
  </verify>
  <done>
    - docs/index.md, docs/quickstart.md, and docs/mcp-server.md present the same auto/cpu/macOS matrix as README and docs/installation.md, with no unconditional Linux CPU-only recommendation remaining
    - ruff check, ruff format --check, and the full pytest suite are green under `uv run --frozen --extra dev --extra embed`
    - `git status --porcelain` shows only the 13 planned files plus .planning/ artifacts; pyproject.toml, uv.lock, workflows, and historical v1.2.0 prose are untouched
    - No tag, push, publish, or GitHub action was performed
  </done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| version literal -> published artifacts | The tag gate and publishing workflow trust `src/sif/_version.py` to equal the built distribution version; drift between it and the manifests produces mislabeled releases |
| docs -> user install command | Users copy install commands verbatim; a backend flag that cannot resolve on their platform turns into a failed install or an unexpected multi-GB CUDA download |
| package indexes -> user environment | The docs point at PyPI and the PyTorch index; no package is added or installed by this plan |

## STRIDE Threat Register

| Threat ID | Category | Component | Severity | Disposition | Mitigation Plan |
|-----------|----------|-----------|----------|-------------|-----------------|
| T-jbj-01 | Tampering | release version surfaces (`_version.py`, `server.json`, plugin/marketplace manifests, changelog links) | medium | mitigate | Keep one literal in `_version.py`; bump all four manifests and the changelog link block in Task 1; pin with `tests/unit/mcp/test_plugin.py::test_manifest_version_parity`, `tests/unit/mcp/test_registry_script.py`, and the renamed `tests/test_release_metadata.py::test_version_literal_is_1_2_1` / `test_changelog_has_1_2_1`. |
| T-jbj-02 | Denial of service (user install failure) | macOS install guidance | medium | mitigate | Document "Do not pass `--torch-backend=cpu` on macOS" in docs/installation.md and require the literal in both `tests/test_docs.py` and `tests/test_ci_workflows.py`, using the verified uv 0.13.8 resolution evidence (no macOS CPU wheel for torch 2.15.0; MPS ships in the macOS wheel). |
| T-jbj-03 | Tampering (supply chain inflation) | Linux install guidance pulling an unintended CUDA stack | low | mitigate | Present `auto` as the GPU path and `cpu` as the minimal path, state the no-flag default pulls the Linux CUDA stack, and keep the pip matrix note that pip cannot auto-detect; no package, index, or lock change is introduced. |
| T-jbj-SC | Tampering | npm/pip/cargo installs | low | accept | This plan performs no package installation and adds no dependency; `pyproject.toml`, `uv.lock`, `[tool.uv.sources]`, and the `torch>=2.14` floor are explicitly out of scope, and gates run inside the frozen lock. |
</threat_model>

<verification>
1. Task 1: `pytest tests/test_release_metadata.py tests/unit/mcp/test_plugin.py tests/unit/mcp/test_registry_script.py` is green; all four parity surfaces read 1.2.1; the changelog 1.2.0 section and older entries are unchanged.
2. Task 1: `grep -n "1\.2\.0" src/sif/_version.py server.json .claude-plugin/plugin.json .claude-plugin/marketplace.json` returns no hits; the only remaining 1.2.0 strings are historical changelog/prose, the README-independent fixture in tests/test_windows_smoke_script.py, and the unrelated uv.lock entry.
3. Task 2: `pytest tests/test_docs.py tests/test_ci_workflows.py` is green; docs/installation.md still contains `--torch-backend=cpu`, `https://download.pytorch.org/whl/cpu`, `uv 0.9.19`, and now also `--torch-backend=auto`, a `https://download.pytorch.org/whl/cu` index, the macOS no-flag sentence, and `sif, version 1.2.1`.
4. Task 3: docs/index.md, docs/quickstart.md, and docs/mcp-server.md contain `--torch-backend=auto` and `--torch-backend=cpu` and do not present the CPU flag as the unconditional Linux default.
5. Overall: `ruff check src tests`, `ruff format --check src tests`, and full `pytest` are green under `uv run --frozen --extra dev --extra embed`.
6. Scope: `git status --porcelain` shows only the 13 planned files plus `.planning/` artifacts; no tag, push, publish, or workflow change occurred.
</verification>

<success_criteria>
- v1.2.1 is consistent everywhere it is observable: the literal, all three manifests, the changelog heading and links, the release-metadata tests, and the documented `sif --version` output.
- Install docs are accurate per the verified uv 0.13.8 behavior: Linux GPU uses `auto`, Linux CPU-only uses `cpu`, macOS uses no flag, and pip users get an explicit CPU-vs-CUDA index matrix with the auto-detect limitation stated.
- The existing docs contracts are preserved: `--torch-backend=cpu`, the CPU index URL, the uv 0.9.19 floor, and uv tool -> uvx -> pip ordering all still hold and are still tested, now joined by auto and the macOS note.
- Full quality suite (ruff check, ruff format --check, pytest) green; one atomic commit for the plan; no dependency, lock, workflow, tag, push, or publish change.
</success_criteria>

<output>
Create `.planning/quick/261118-jbj-release-v1-2-1-bump-version-across-all-p/261118-jbj-SUMMARY.md` when done
</output>
