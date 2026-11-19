---
phase: quick-261119-juo
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
  - docs/installation.md
autonomous: true
requirements: [QUICK-RELEASE-1-2-2]
estimate:
  tokens: 24000
  raw_tokens: 24000
  tasks: 2
  confidence: low

must_haves:
  truths:
    - "`sif --version` reports 1.2.2: `src/sif/_version.py` is the only version literal and it reads 1.2.2, with `server.json` (top-level and `packages[0].version`), `.claude-plugin/plugin.json`, and `.claude-plugin/marketplace.json` (`plugins[0].version`) all equal to it; `APP_VERSION` and the MCP `serverInfo` version derive from that literal and need no separate edit."
    - "`docs/changelog.md` carries a `## [1.2.2] - 2026-11-19` section between Unreleased and 1.2.1 with an Added bullet for Intel XPU auto-selection, a Changed block holding the moved `torch>=2.11` bullet (not duplicated) plus the version bullet, and Fixed bullets for the Windows subpath filter and the Windows test-suite guards; the link block points `[Unreleased]` at `compare/v1.2.2...HEAD` and adds `[1.2.2]:`, and every 1.2.1/1.2.0/older entry is byte-unchanged."
    - "`tests/test_release_metadata.py` pins 1.2.2 through renamed tests (`test_changelog_has_1_2_2`, `test_version_literal_is_1_2_2`), and no other file under `tests/`, `README.md`, `docs/`, `.github/`, or `src/` asserts 1.2.1 as the current release version."
    - "`docs/installation.md` shows `sif, version 1.2.2` in the verification sample."
    - "`uvx --from uv==0.13.8 uv lock --check` still exits 0 (the lock records no project version for the editable `docsif` package), and the full quality suite is green: `ruff check`, `ruff format --check`, `ty check src/sif` at the 22 pre-existing diagnostics, and full `pytest` with 0 failed / 0 errors and coverage above the 90% gate."
  artifacts:
    - "src/sif/_version.py — __version__ = \"1.2.2\""
    - "server.json — top-level version and packages[0].version both 1.2.2"
    - ".claude-plugin/plugin.json — version 1.2.2"
    - ".claude-plugin/marketplace.json — plugins[0].version 1.2.2"
    - "docs/changelog.md — new 1.2.2 section plus updated Unreleased/[1.2.2] link targets"
    - "tests/test_release_metadata.py — renamed and re-pinned 1.2.2 release-metadata tests"
    - "docs/installation.md — the sif --version sample reads 1.2.2"
  key_links:
    - "src/sif/_version.py -> server.json, .claude-plugin/plugin.json, .claude-plugin/marketplace.json is enforced by tests/unit/mcp/test_registry_script.py and tests/unit/mcp/test_plugin.py::TestPluginManifest::test_manifest_version_parity, so a partial bump fails"
    - "docs/changelog.md heading and link block -> tests/test_release_metadata.py literal assertions"
    - "src/sif/config/constants.py APP_VERSION = __version__ and the MCP serverInfo version -> src/sif/_version.py, so they move automatically with the bump"
---

<objective>
Ship the v1.2.2 patch-release metadata.

One atomic version unit: the single literal in `src/sif/_version.py` must reach all three parity manifests, the changelog, the release-metadata tests, and the documented `sif --version` sample before anything is verified, because the parity tests fail on any intermediate state. The changelog gains a `[1.2.2]` section covering everything shipped since the `v1.2.1` tag: Intel XPU auto-selection (quick task 261119-bl9), the `torch>=2.11` extra floor (already sitting in `[Unreleased]`), and the Windows portability fixes (quick task 261119-fww). Task 2 then audits the whole tree for stray current-version assertions, proves the lock is version-neutral, and runs the full quality gates.

Purpose: publish `docsif` 1.2.2 from metadata that is consistent everywhere it is observable.
Output: 7 edited files, no new code paths, no dependency, lock, or workflow changes.

Scope boundaries (locked):
- Target 1.2.2 — a patch release, not 1.3.0.
- Do NOT touch `pyproject.toml` (dynamic version via `[tool.hatch.version]`), `uv.lock`, `[tool.uv.sources]`, or the `torch>=2.11` floor.
- Do NOT tag, push, publish, create a GitHub release, edit issues, or change `.github/workflows/**`.
- Do NOT rewrite historical changelog text: the 1.2.1 heading, its "version is now `1.2.1`" bullet, and the `[1.2.1]:` link stay byte-identical; older entries are untouched.
- Do NOT advertise the recorded `signal.SIGKILL` Windows daemon defect (`src/sif/utils/daemon.py:366`, recorded-not-fixed by 261119-fww) as resolved.
- Do NOT edit `docs/development.md`'s `docsif==1.1.2` release-verification examples or `uv.lock`'s unrelated `backports-asyncio-runner` 1.2.0 entry; neither asserts the current release version.
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
@docs/installation.md

Planning-time observations (live, 2026-11-19, HEAD 240ff51, clean tree, repo venv via `uv run --frozen --extra dev --extra embed`):

- Version source: `src/sif/_version.py:3` is `__version__ = "1.2.1"`. It is the only version literal; `pyproject.toml` line 7 is `dynamic = ["version"]` and `[tool.hatch.version]` reads `path = "src/sif/_version.py"`. `src/sif/config/constants.py:8` is `APP_VERSION = __version__`, and the MCP `serverInfo` version derives from the same import.
- Parity surfaces: `server.json:5` (top-level) and `server.json:10` (`packages[0]`); `.claude-plugin/plugin.json:3`; `.claude-plugin/marketplace.json:12` (`plugins[0].version`). `tests/unit/mcp/test_plugin.py::TestPluginManifest::test_manifest_version_parity` (lines 77-82) and `tests/unit/mcp/test_registry_script.py` (lines 85-99) compare them against `sif._version.__version__`, so both modules track the bump automatically and a partial bump fails.
- Non-changelog 1.2.1 surfaces at HEAD (12 matching lines, the gate's baseline): `src/sif/_version.py:3`; `server.json:5`, `:10`; `.claude-plugin/plugin.json:3`; `.claude-plugin/marketplace.json:12`; `tests/test_release_metadata.py:60`, `:62`, `:63`, `:64`, `:68`, `:70`; `docs/installation.md:352`.
- `tests/test_release_metadata.py`: `test_changelog_has_1_2_1` (lines 59-64) asserts `"## [1.2.1]"`, `"[1.2.1]:"`, `"compare/v1.2.1...HEAD"`; `test_version_literal_is_1_2_1` (lines 67-70) asserts `version == "1.2.1"`. No other release-metadata test pins a version literal.
- `docs/changelog.md` structure: `## [Unreleased]` at line 8; its `### Added` still holds the stale v1.0-era "Initial project structure..." bullets (leave them); its `### Changed` holds exactly one bullet, the `torch>=2.11` sentence added by 261119-fww (line 24); `### Deprecated`/`### Removed`/`### Fixed`/`### Security` each contain `- N/A` (lines 26-36); `## [1.2.1] - 2026-11-18` begins at line 38; the link block is at the file tail with `[Unreleased]: .../compare/v1.2.1...HEAD`, `[0.1.0]:`, `[1.2.1]:`, `[1.2.0]:`, `[1.1.2]:`, `[1.1.1]:`, `[1.0.1]:`. At HEAD, `grep -c "1\.2\.1" docs/changelog.md` is 4 (heading, version bullet, Unreleased compare link, `[1.2.1]:` link); after the bump it is 3 (the Unreleased link moves to v1.2.2).
- Changelog content to record (from quick tasks 261119-bl9 and 261119-fww, both after tag v1.2.1): XPU auto-selection via the typed `_auto_device` helper with precedence CUDA > Intel XPU > Apple MPS > CPU, wired into `SentenceTransformerEmbedder` and `ModelScopeEmbedder`, model-free tests, documented in `docs/configuration.md` and `docs/installation.md`; the platform-neutral `sif ls` / `sif collection ls` subpath filter (filter both sides with `Path.as_posix()` and render the `collection ls` tree with `rel_path.as_posix()`); the Windows test-suite guards (index-locking `fcntl` import guarded, POSIX-only service/daemon/signal tests skip on Windows, symlink tests skip only when the host forbids symlink creation, permission-bit and Rich-width assertions made platform-honest).
- `docs/installation.md:352` is inside the "Expected output:" fenced block for `sif --version`; its lines start with `sif,` (comma), so `tests/test_docs.py::test_shell_commands_exist` (which only executes commands starting with `sif `) does not run or assert it. No test pins this sample.
- `uv.lock:495` `[[package]] name = "docsif"` has `source = { editable = "." }` and no `version` field, so the bump is lock-neutral. Verified now at HEAD: `uvx --from uv==0.13.8 uv lock --check` exits 0.
- Windows suite baseline after 261119-fww: 3165 passed, 84 skipped, 0 failed, 0 errors, coverage 94.02%. Run with `PYTHONUTF8=1` and a fresh `--basetemp` (a stale temp dir raises WinError 5).
- `ty` 0.0.97 is in the dev extra and reports 22 pre-existing Windows/POSIX + third-party diagnostics, identical on pristine HEAD 240ff51; `ty check` exits non-zero, so record the count, do not treat the exit code as a gate and do not fix them.
- Tree noise to exclude from the stray-reference audit: `htmlcov/**` (gitignored coverage HTML) and `__pycache__/*.pyc` still contain the old literal.
</context>

<tasks>

<task type="auto">
  <name>Task 1: Bump to 1.2.2 across every parity surface, the changelog, the release-metadata tests, and the installation sample</name>
  <files>src/sif/_version.py, server.json, .claude-plugin/plugin.json, .claude-plugin/marketplace.json, docs/changelog.md, tests/test_release_metadata.py, docs/installation.md</files>
  <precondition>The checkout is at HEAD 240ff51 with a clean tree and `uv` is on PATH; the targeted tests need no network, model weights, or GPU.</precondition>
  <action>
    One atomic version unit: if any surface keeps the old value, the parity tests fail, so edit all seven files before verifying.

    1. src/sif/_version.py: change `__version__ = "1.2.1"` to `__version__ = "1.2.2"`. This stays the only version literal; do not touch `pyproject.toml`, `src/sif/config/constants.py`, or any MCP module.

    2. server.json: change the top-level `"version": "1.2.1"` and the `packages[0]` `"version": "1.2.1"` to `"1.2.2"`. Leave `$schema`, `name`, `description`, `registryType`, `identifier`, and `transport` untouched.

    3. .claude-plugin/plugin.json: change `"version": "1.2.1"` to `"1.2.2"`; leave every other key as-is.

    4. .claude-plugin/marketplace.json: change `plugins[0].version` from `"1.2.1"` to `"1.2.2"`; leave the marketplace `name`, `description`, `owner`, and the plugin `name`/`source`/`description` as-is.

    5. docs/changelog.md, new section: insert it directly before the `## [1.2.1] - 2026-11-18` line and after the Unreleased block's `### Security` / `- N/A` lines, with exactly these lines (plain Markdown, no fences, no issue numbers):

    ## [1.2.2] - 2026-11-19

    ### Added
    - Embedding device detection now auto-selects Intel XPU with CUDA > Intel XPU > Apple MPS > CPU precedence; the typed `_auto_device` helper serves both the sentence-transformers and ModelScope backends, covered by model-free tests and documented in `docs/configuration.md` and `docs/installation.md`.

    ### Changed
    - The release version is now `1.2.2`, still single-sourced in `src/sif/_version.py`.
    - The `embed` and `all` extras now declare `torch>=2.11` (minimum supported; 2.14 or newer recommended); `uv.lock` was regenerated with the same resolved torch builds.

    ### Fixed
    - `sif ls` and `sif collection ls` subpath filters now normalize separators on both sides, so POSIX-style subpaths match on Windows and the `collection ls` tree renders POSIX separators on every platform.
    - The test suite collects on Windows: the index-locking test guards its `fcntl` import, POSIX-only service, daemon, and signal tests skip on Windows with a stated reason, symlink-dependent tests skip only when the host forbids symlink creation, and permission-bit and Rich-width assertions are platform-honest.

    6. docs/changelog.md, Unreleased block: delete the single `torch>=2.11` bullet from `[Unreleased] ### Changed` (it now lives only in the new 1.2.2 section — do not duplicate it) and leave `- N/A` in its place so the heading matches the neighbouring placeholder sections. Do not touch the `[Unreleased] ### Added` stale v1.0 bullets, and do not alter the `## [1.2.1] - 2026-11-18` section or any older entry.

    7. docs/changelog.md, link block: change the `[Unreleased]: https://github.com/zhangtaolab/sif/compare/v1.2.1...HEAD` line to compare `v1.2.2...HEAD`, and insert `[1.2.2]: https://github.com/zhangtaolab/sif/releases/tag/v1.2.2` immediately before the existing `[1.2.1]:` line. Leave `[0.1.0]`, `[1.2.1]`, `[1.2.0]`, `[1.1.2]`, `[1.1.1]`, and `[1.0.1]` byte-unchanged.

    8. tests/test_release_metadata.py: rename `test_changelog_has_1_2_1` to `test_changelog_has_1_2_2`, update its docstring to say 1.2.2, and change its three literals to `"## [1.2.2]"`, `"[1.2.2]:"`, and `"compare/v1.2.2...HEAD"`. Rename `test_version_literal_is_1_2_1` to `test_version_literal_is_1_2_2`, update the docstring, and assert `version == "1.2.2"`. Do not change the other tests in the module (README marker, publish workflow, classifiers, release-process docs).

    9. docs/installation.md line 352: change the sample output line `sif, version 1.2.1` to `sif, version 1.2.2`. Change nothing else in that fenced block.

    Do not run `uv lock`, `uv sync`, or any formatter over these files beyond what Task 2's gates do; keep the changelog diff to the new section, the one moved bullet, and the two link-block lines.
  </action>
  <verify>
    <automated>
      PYTHONUTF8=1 uv run --frozen --extra dev --extra embed python -m pytest tests/test_release_metadata.py tests/unit/mcp/test_plugin.py tests/unit/mcp/test_registry_script.py -q --no-cov --basetemp="C:/Users/forre/AppData/Local/Temp/gsd-juo-t1-$$"
      grep -rn "1\.2\.1" src/sif/_version.py server.json .claude-plugin/plugin.json .claude-plugin/marketplace.json tests/test_release_metadata.py docs/installation.md | wc -l
      grep -c '^## \[1\.2\.2\] - 2026-11-19$' docs/changelog.md
      grep -c '^\[1\.2\.2\]: https://github\.com/zhangtaolab/sif/releases/tag/v1\.2\.2$' docs/changelog.md
      grep -c '^\[Unreleased\]: https://github\.com/zhangtaolab/sif/compare/v1\.2\.2\.\.\.HEAD$' docs/changelog.md
      awk '/^## \[Unreleased\]/,/^## \[1\.2\.2\]/' docs/changelog.md | grep -c 'torch>=2\.11'
      awk '/^## \[1\.2\.2\]/,/^## \[1\.2\.1\]/' docs/changelog.md | grep -c 'torch>=2\.11'
      grep -c 'sif, version 1\.2\.2' docs/installation.md
    </automated>
  </verify>
  <done>
    - src/sif/_version.py reads 1.2.2 and is still the only version literal, with server.json (both fields), plugin.json, and marketplace.json all reading 1.2.2
    - The 12-line non-changelog 1.2.1 gate [HEAD=12 EXPECT=0] returns 0
    - docs/changelog.md has exactly one `## [1.2.2] - 2026-11-19` heading [HEAD=0 EXPECT=1], one `[1.2.2]:` tag link [HEAD=0 EXPECT=1], and one `[Unreleased]` compare link at v1.2.2...HEAD [HEAD=0 EXPECT=1]
    - The `torch>=2.11` bullet count inside `[Unreleased]` is 0 [HEAD=1 EXPECT=0] and inside `[1.2.2]` is 1 [HEAD=0 EXPECT=1] — moved, not duplicated
    - docs/installation.md has exactly one `sif, version 1.2.2` sample line [HEAD=0 EXPECT=1]; the old `1.2.1` line count in docs/changelog.md dropped from 4 to 3 (historical 1.2.1 heading, version bullet, and tag link only) [HEAD=4 EXPECT=3]
    - The targeted pytest run is green, including both manifest-parity modules
    - `git diff` on docs/changelog.md shows only the inserted section, the one replaced Unreleased Changed bullet, the changed Unreleased link line, and the added `[1.2.2]:` line; pyproject.toml, uv.lock, and .github/workflows/** are untouched
  </done>
</task>

<task type="auto">
  <name>Task 2: Audit for stray current-version references, prove the lock is version-neutral, and run the full quality gates</name>
  <files>tests/, docs/, README.md, .github/, src/ (read-only; an audit-found current-version assertion is the only reason to edit, and any such edit is recorded in the SUMMARY)</files>
  <precondition>Task 1 is committed or staged, so the tree already reads 1.2.2 on every release surface and `uv run --frozen --extra dev --extra embed` still resolves.</precondition>
  <action>
    1. Stray-reference audit. Run `grep -rn "1\.2\.1" --exclude-dir=.git --exclude-dir=.venv --exclude-dir=.planning --exclude-dir=htmlcov --exclude-dir=__pycache__ .` from the repo root. Expected remainder: docs/changelog.md only (the historical 1.2.1 heading, its "version is now `1.2.1`" bullet, and the `[1.2.1]:` link — 3 lines). Any other hit means a release-version assertion was missed: update it only when it asserts the CURRENT release version (for example a test literal or a version sample), leave historical changelog prose and the illustrative `docsif==1.1.2` examples in docs/development.md alone, and record the extra file in the SUMMARY.

    2. Lock neutrality. Run `uvx --from uv==0.13.8 uv lock --check` and record the exit status; it must be 0 because `uv.lock` carries no version field for the editable `docsif` package. Do NOT hand-edit `uv.lock`. If uv reports the lock is stale solely because of the project version, follow the prior-release precedent: leave the lock as is and record the uv message verbatim; only regenerate with `uvx --from uv==0.13.8 uv lock` if uv genuinely reports a resolution change, and then report the exact content diff.

    3. Ruff gates, in CLAUDE.md order:
       - `PYTHONUTF8=1 uv run --frozen --extra dev --extra embed ruff check src tests`
       - `PYTHONUTF8=1 uv run --frozen --extra dev --extra embed ruff format --check src tests`
       Both must pass with no file changes. If `ruff format --check` flags an edited file, run `ruff format src tests` and note it.

    4. Type gate: run `PYTHONUTF8=1 uv run --frozen --extra dev --extra embed ty check src/sif` and record the diagnostic count. Expected: 22, identical to pristine HEAD 240ff51 (Windows/POSIX + third-party drift). `ty` exits non-zero on diagnostics, so judge by the count, not the exit code. Do not fix pre-existing diagnostics; if the count grows, fix only the new diagnostics attributable to this plan.

    5. Full suite with the coverage gate active (no `--no-cov`): `PYTHONUTF8=1 uv run --frozen --extra dev --extra embed python -m pytest -q --basetemp="C:/Users/forre/AppData/Local/Temp/gsd-juo-full-$$"`. `PYTHONUTF8=1` and a fresh `--basetemp` are mandatory on this Windows host. Expected: 0 failed, 0 errors, roughly 3165 passed / 84 skipped, coverage at or above the `fail_under = 90` gate (the 1.2.2 baseline was 94.02% before this plan). Record the exact summary line.

    6. Scope audit. Run `git status --porcelain` and confirm it shows only the seven planned files plus `.planning/` artifacts (coverage outputs are gitignored). Confirm by inspection that `pyproject.toml`, `uv.lock`, `[tool.uv.sources]`, `.github/workflows/**`, and every changelog entry older than the new 1.2.2 section are unmodified. Do not tag, push, publish, create a GitHub release, or touch GitHub issues; leave tagging to the maintainer.
  </action>
  <verify>
    <automated>
      grep -rn "1\.2\.1" --exclude-dir=.git --exclude-dir=.venv --exclude-dir=.planning --exclude-dir=htmlcov --exclude-dir=__pycache__ . | grep -v '^\./docs/changelog\.md:' | wc -l
      uvx --from uv==0.13.8 uv lock --check
      PYTHONUTF8=1 uv run --frozen --extra dev --extra embed ruff check src tests
      PYTHONUTF8=1 uv run --frozen --extra dev --extra embed ruff format --check src tests
      PYTHONUTF8=1 uv run --frozen --extra dev --extra embed ty check src/sif  # record the diagnostic count: [HEAD=22 EXPECT=22], baseline exits non-zero
      PYTHONUTF8=1 uv run --frozen --extra dev --extra embed python -m pytest -q --basetemp="C:/Users/forre/AppData/Local/Temp/gsd-juo-full-$$"
    </automated>
  </verify>
  <done>
    - The stray-reference gate returns 0 outside docs/changelog.md [HEAD=12 EXPECT=0]; a nonzero result means each hit was a current-version assertion and was fixed
    - `uvx --from uv==0.13.8 uv lock --check` exits 0 and uv.lock is unmodified
    - `ruff check src tests` and `ruff format --check src tests` pass
    - `ty check src/sif` reports exactly 22 diagnostics [HEAD=22 EXPECT=22], unchanged from HEAD 240ff51, with none introduced by this plan
    - Full pytest reports 0 failed / 0 errors with coverage at or above 90%, and the exact summary line is recorded in the SUMMARY
    - `git status --porcelain` shows only the seven planned files plus .planning artifacts; no tag, push, publish, release, or issue action was performed
  </done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| version literal -> published artifacts | The Publish workflow's tag gate trusts `src/sif/_version.py` to equal the built distribution version; drift between it and the manifests produces a mislabeled release |
| changelog -> release notes | Users and the Registry read the changelog as the record of what shipped; a bullet misplaced into the wrong release or a historical entry rewritten corrupts the release history |
| package indexes -> user environment | No package is added, upgraded, or installed by this plan; the frozen lock is reused as-is |

## STRIDE Threat Register

| Threat ID | Category | Component | Severity | Disposition | Mitigation Plan |
|-----------|----------|-----------|----------|-------------|-----------------|
| T-juo-01 | Tampering | release version surfaces (`_version.py`, `server.json`, plugin/marketplace manifests, changelog links, installation sample) | medium | mitigate | Bump all seven surfaces in one task; keep one literal in `_version.py`; pin with `tests/unit/mcp/test_plugin.py::test_manifest_version_parity`, `tests/unit/mcp/test_registry_script.py`, and the renamed `tests/test_release_metadata.py::test_version_literal_is_1_2_2` / `test_changelog_has_1_2_2`; gate the 12-line non-changelog baseline to 0. |
| T-juo-02 | Tampering (history integrity) | `docs/changelog.md` release history | medium | mitigate | Insert only between Unreleased and 1.2.1; move the `torch>=2.11` bullet with region-scoped counts (Unreleased = 0, 1.2.2 = 1); leave the 1.2.1 section and its tag link byte-unchanged; audit the final diff scope. |
| T-juo-03 | Repudiation | Windows defect disclosure | low | mitigate | Per the locked scope, never claim the recorded `signal.SIGKILL` Windows daemon defect (`src/sif/utils/daemon.py:366`) is fixed; the Fixed bullets describe only the subpath filter and the test-suite guards that actually landed. |
| T-juo-SC | Tampering | npm/pip/cargo installs | low | accept | This plan installs nothing and adds no dependency; `pyproject.toml`, `uv.lock`, and `[tool.uv.sources]` are explicitly out of scope and all gates run inside the frozen lock, with `uv lock --check` proving the lock is unchanged. |
</threat_model>

<verification>
1. Task 1 targeted pytest (`tests/test_release_metadata.py`, `tests/unit/mcp/test_plugin.py`, `tests/unit/mcp/test_registry_script.py`) is green; all four version surfaces read 1.2.2; the non-changelog 1.2.1 gate goes 12 -> 0.
2. Task 1 changelog gates: one `## [1.2.2] - 2026-11-19` heading, one `[1.2.2]:` link, one `[Unreleased]` compare link at `v1.2.2...HEAD`, `torch>=2.11` count 0 inside Unreleased and 1 inside 1.2.2, and the `1.2.1` line count in the file drops from 4 to 3 with the 1.2.1 section byte-unchanged.
3. Task 1 installation sample: exactly one `sif, version 1.2.2`.
4. Task 2 stray-reference audit: no `1.2.1` hit outside docs/changelog.md across `src/`, `tests/`, `docs/`, `README.md`, `.github/`, and the manifests.
5. Task 2 lock: `uvx --from uv==0.13.8 uv lock --check` exits 0 and `uv.lock` is untouched.
6. Task 2 gates: `ruff check src tests`, `ruff format --check src tests`, `ty check src/sif` at exactly 22 pre-existing diagnostics, and full `pytest` (coverage gate active) with 0 failed / 0 errors.
7. Scope: `git status --porcelain` shows only the seven planned files plus `.planning/`; no tag, push, publish, GitHub release, or workflow change occurred.
</verification>

<success_criteria>
- v1.2.2 is consistent everywhere it is observable: the `_version.py` literal, all three parity manifests, the changelog heading and links, the release-metadata tests, and the documented `sif --version` output.
- The changelog records exactly what shipped since `v1.2.1` — XPU auto-selection (Added), the `torch>=2.11` floor plus the version bump (Changed), and the Windows subpath filter plus test-suite guards (Fixed) — with the torch bullet moved rather than duplicated and no historical entry rewritten.
- No stale current-version assertion remains anywhere in `src/`, `tests/`, `docs/`, `README.md`, or `.github/`; the lock is proven version-neutral.
- Full quality suite (ruff check, ruff format --check, ty at baseline, pytest with coverage >= 90%) green with 0 failed / 0 errors; no dependency, lock, workflow, tag, push, or publish change.
</success_criteria>

<output>
Create `.planning/quick/261119-juo-release-version-1-2-2-bump-the-single-ve/261119-juo-SUMMARY.md` when done
</output>
