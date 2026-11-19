---
phase: quick-261118-lmm
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - .github/workflows/test-matrix.yml
  - tests/test_ci_workflows.py
  - docs/development.md
  - docs/contributing.md
  - docs/testing.md
  - tests/conftest.py
autonomous: true
requirements: [QUICK-CI-SIX-CELL]  # quick task: six-cell CI matrix + push CI on main only
estimate:
  tokens: 36000
  raw_tokens: 36000
  tasks: 3
  confidence: low

must_haves:
  truths:
    - "`.github/workflows/test-matrix.yml` triggers on `push` with `branches: [main]` only, plus `pull_request`; the test job matrix keeps `os: [ubuntu-latest, macos-latest]`, all four quoted Python versions, and exactly two `exclude` entries (`os: macos-latest` with `python-version: '3.11'` and `'3.12'`), yielding six cells: Linux 3.10-3.13 and macOS 3.10/3.13."
    - "Every preserved CI invariant is intact: `fail-fast: false`, `cancel-in-progress: true` on the per-ref concurrency group, `timeout-minutes: 30`, `permissions: contents: read`, the SHA-pinned `astral-sh/setup-uv@68559e99cc807c1eb7e9238fd43a15bba460eec2`, `uv sync --frozen --extra dev --extra embed`, `env -u FORCE_COLOR NO_COLOR=1 uv run --frozen pytest`, and the unchanged Python 3.12 lint job."
    - "`tests/test_ci_workflows.py` pins the new shape: a six-cell test that asserts the two macOS exclusions exactly (so dropping them or shrinking the matrix fails), and a main-only push trigger test that still rejects tag triggers."
    - "docs/development.md, docs/contributing.md, docs/testing.md, and the tests/conftest.py logger-comment all state six cells (Linux 3.10-3.13; macOS 3.10 and 3.13) and push-on-main plus every pull request; no stale matrix count or branch-glob trigger claim remains in those files."
    - "Full quality gates are green under `uv run --frozen --extra dev --extra embed`: `ruff check src tests`, `ruff format --check src tests`, and the full pytest suite."
  artifacts:
    - ".github/workflows/test-matrix.yml — push on main only; six-cell matrix via two macOS exclusions"
    - "tests/test_ci_workflows.py — renamed six-cell guard with exact exclusion assertions plus main-only push trigger guard"
    - "docs/development.md — four CI statements updated to the six-cell / main-push shape"
    - "docs/contributing.md — five CI statements updated, including the trigger snippet and release gate"
    - "docs/testing.md — CI contract bullet and Test Matrix section updated to six cells"
    - "tests/conftest.py — caplog comment no longer cites a cell count"
  key_links:
    - ".github/workflows/test-matrix.yml test-job matrix -> tests/test_ci_workflows.py::test_matrix_declares_six_cells, which scans the `test` job block with a regex for exclusion pairs"
    - ".github/workflows/test-matrix.yml on.push.branches -> tests/test_ci_workflows.py::test_matrix_push_trigger_is_main_only, which matches the exact flow-sequence line"
    - "workflow shape -> docs/development.md, docs/contributing.md, docs/testing.md (manual consistency; tests/test_docs.py DOCS_FILES does not include these three files and no test pins their prose)"
    - "workflow triggers -> tests/conftest.py comment semantics (no cell count is asserted, so the comment only needs to stay meaningful)"
---

<objective>
Cut CI cost and macOS-capacity exposure without weakening the test matrix: push CI runs on `main` only (feature branches are covered by their `pull_request` run, so each commit runs once), and macOS runs only the boundary Python versions 3.10 and 3.13 while Linux keeps 3.10-3.13 — six cells instead of eight.

Purpose: stop hosted macOS arm64 runner capacity from repeatedly cancelling boundary jobs on PRs, and stop every feature-branch commit from running the full matrix twice.

Output: one edited workflow, its contract tests re-pinned to the six-cell shape, and every doc/comment that states the matrix shape brought in line. No dependency, lock, packaging, or other-workflow change.

Scope boundaries (locked):
- Do NOT touch `.github/workflows/publish.yml`, `.github/workflows/docs.yml`, `pyproject.toml`, `uv.lock`, or any package metadata.
- Do NOT tag, push, publish, or open/edit GitHub issues.
- Do NOT modify `.planning/milestones/**` (historical records keep their old counts).
- Keep `fail-fast: false`, the per-ref concurrency cancellation, the 30-minute timeout, least-privilege permissions, the SHA-pinned setup-uv action, the frozen sync command, and the full-suite invocation exactly as they are.
</objective>

<execution_context>
@~/.claude/gsd-core/workflows/execute-plan.md
@~/.claude/gsd-core/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md
@.github/workflows/test-matrix.yml
@tests/test_ci_workflows.py
@docs/development.md
@docs/contributing.md
@docs/testing.md
@tests/conftest.py

Planning-time observations (live, 2026-11-18, HEAD 8f13661, tree clean):

- `.github/workflows/test-matrix.yml`: `on.push.branches` is currently a bracket list containing a double-star glob, with `pull_request:` alongside; `permissions: contents: read`; `concurrency.group: ${{ github.workflow }}-${{ github.ref }}` with `cancel-in-progress: true`; test job `timeout-minutes: 30`; `strategy.fail-fast: false`; matrix `os: [ubuntu-latest, macos-latest]` and `python-version: ['3.10', '3.11', '3.12', '3.13']`; steps checkout@v7, SHA-pinned setup-uv (v10.3.3) with python-version/enable-cache/cache-dependency-glob `uv.lock`/cache-suffix, `uv python install`, `uv sync --frozen --extra dev --extra embed`, `env -u FORCE_COLOR NO_COLOR=1 uv run --frozen pytest`; lint job unchanged on Python 3.12.
- `tests/test_ci_workflows.py`: `PYTHON_VERSION_MATRIX = "python-version: ['3.10', '3.11', '3.12', '3.13']"` (line 29); `test_matrix_declares_eight_cells` (lines 181-202) asserts the six matrix literals, `fail-fast: false`, `cancel-in-progress: true`, and exactly one occurrence of the contiguous python-version list; `test_matrix_excludes_tag_pushes` (lines 243-252) requires a `push:` block with `branches:` and forbids `tags:`; `_job_block(text, job_id)` (lines 62-69) returns one top-level job block and is already used by `test_lint_job_runs_repo_gates`.
- Docs matrix-shape sites (all must be updated): docs/development.md line 609 (release step "Commit and confirm CI"), line 732 (workflow table row: trigger cell + cell count), line 751 (PR CI bullet), lines 769-770 (coverage note); docs/contributing.md line 365 (release step 4), line 400 (intro sentence), line 402 (Test bullet cell list), line 405 (trigger-snippet sentence), line 407 (release gate sentence); docs/testing.md line 130 (test_ci_workflows bullet), line 212 (trigger sentence), line 214 (job description); tests/conftest.py lines 61-62 (caplog docstring citing the cell count).
- `tests/test_docs.py` DOCS_FILES covers README.md, docs/index.md, cli-reference.md, configuration.md, quickstart.md, mcp-server.md, search-algorithms.md, benchmarking.md, architecture.md, models.md, installation.md, and migration.md — not development.md, contributing.md, or testing.md. `tests/test_hygiene.py` scans docs/**/*.md only for the bandit VERIFY marker, so these prose edits cannot trip it. No test pins the conftest comment.
- `uv run --frozen python -c "import yaml; print(yaml.__version__)"` prints 6.0.3 at HEAD (transitively locked; no extras needed), so a YAML structural check is available without touching the lock. Note PyYAML parses the YAML 1.1 `on:` key as boolean `True`, so read the trigger mapping with `doc[True]`.
- GitHub Actions matrix `exclude` entries must match on the full combination (both `os` and `python-version`); keeping `macos-latest` in the `os:` list is required for the exclusions to bind.
- Prior quick plans leave the tree for the standard quick commit; no commit step belongs in the tasks below.
</context>

<tasks>

<task type="auto">
  <name>Task 1: Switch push CI to main only and declare the six-cell matrix, then re-pin the contract tests</name>
  <files>.github/workflows/test-matrix.yml, tests/test_ci_workflows.py</files>
  <precondition>The checkout is at HEAD with a clean tree, `uv` is on PATH, and PyYAML imports under `uv run --frozen python` (verified 6.0.3 at HEAD).</precondition>
  <action>
    Both files must change before verifying: the updated test asserts the new workflow shape, so a partial edit is red.

    1. `.github/workflows/test-matrix.yml` trigger: inside the existing `on:` mapping, replace the `push:` block's single branch-list entry (the double-star glob) with the flow-sequence form `branches: [main]` — exactly that spelling, one line, same indentation as now — and leave the empty `pull_request:` trigger in place. Do not add path filters, `tags:`, or `pull_request_target`.

    2. `.github/workflows/test-matrix.yml` matrix: in the test job's `strategy.matrix`, immediately after the `python-version:` line, add an `exclude:` key at the same indentation as `os:` and `python-version:`. Its value is two list items in this order: first `- os: macos-latest` followed on the next line by `python-version: '3.11'`, then `- os: macos-latest` followed on the next line by `python-version: '3.12'`; each `- os:` line is indented two spaces past the `exclude:` key and each `python-version:` line two spaces past the dash. Keep `macos-latest` present in the `os:` list. Rationale: 2 operating systems x 4 Python versions minus the 2 excluded macOS combinations = 6 cells, with both macOS boundary versions retained.

    3. Do not change any other line of the workflow: `name: Test Matrix`, `permissions: contents: read`, the concurrency group and `cancel-in-progress: true`, the test job name/runs-on/`timeout-minutes: 30`, `fail-fast: false`, every step and its commands (checkout@v7, the SHA-pinned setup-uv with `enable-cache`, `cache-dependency-glob: uv.lock`, `cache-suffix: ${{ matrix.python-version }}`, `uv python install`, the frozen sync with both extras, and the color-stripping full-suite run), and the whole lint job.

    4. `tests/test_ci_workflows.py`: add a module-level compiled pattern next to `PYTHON_VERSION_MATRIX` named `MATRIX_EXCLUSION`, matching one exclusion item as a literal `- os: ` capture of non-whitespace followed by a newline and spaces then `python-version: '` capture of digits and dots and a closing quote — e.g. `re.compile(r"- os: (\S+)\n +python-version: '([0-9.]+)'")`.

    5. `tests/test_ci_workflows.py`: rename `test_matrix_declares_eight_cells` to `test_matrix_declares_six_cells` and update its docstring to say the matrix is 4 Python versions x 2 operating systems minus the two non-boundary macOS cells. Keep its existing assertions unchanged (the six required literal values, `fail-fast: false`, `cancel-in-progress: true`, and exactly one occurrence of `PYTHON_VERSION_MATRIX`). Append one assertion that runs `MATRIX_EXCLUSION.findall` over `_job_block(text, "test")` and requires the result to equal the list of two tuples `("macos-latest", "3.11")` and `("macos-latest", "3.12")` in that order, with a failure message that says the exclusions make the matrix six cells and prints what was found.

    6. `tests/test_ci_workflows.py`: rename `test_matrix_excludes_tag_pushes` to `test_matrix_push_trigger_is_main_only`. Keep the `tags:` prohibition assertion and its message. Replace the current push-block regex assertion with one that requires the exact contiguous text `on:` newline two spaces `push:` newline four spaces `branches: [main]` newline, searched with `re.MULTILINE`, and fails with a message stating the push trigger must be exactly `branches: [main]` (so feature branches rely on their pull request run). Update the docstring to say push CI runs on main only and tags never trigger the matrix.
  </action>
  <verify>
    <automated>
      uv run --frozen python -c "import pathlib, yaml; doc = yaml.safe_load(pathlib.Path('.github/workflows/test-matrix.yml').read_text()); strategy = doc['jobs']['test']['strategy']; matrix = strategy['matrix']; triggers = doc[True]; assert triggers['push']['branches'] == ['main'], triggers; assert 'pull_request' in triggers; assert strategy['fail-fast'] is False; cells = {(o, p) for o in matrix['os'] for p in matrix['python-version']} - {(e['os'], e['python-version']) for e in matrix['exclude']}; expected = {(o, p) for o in ('ubuntu-latest', 'macos-latest') for p in ('3.10', '3.11', '3.12', '3.13')} - {('macos-latest', '3.11'), ('macos-latest', '3.12')}; assert cells == expected, sorted(cells); assert len(cells) == 6; print('workflow-yaml-ok: 6 cells, push main only')"
      uv run --frozen --extra dev --extra embed python -m pytest tests/test_ci_workflows.py -q --no-cov
    </automated>
  </verify>
  <done>
    - The workflow parses as YAML; push branches equal `['main']`, `pull_request` is present, `fail-fast` is false, and the derived cell set is exactly Linux 3.10-3.13 plus macOS 3.10 and 3.13 (6 cells)
    - Every preserved invariant (permissions, concurrency/cancel-in-progress, timeout, setup-uv SHA, cache keys, frozen sync, full-suite command, lint job) is byte-unchanged
    - tests/test_ci_workflows.py has `test_matrix_declares_six_cells` asserting the two exact macOS exclusions and `test_matrix_push_trigger_is_main_only` asserting the exact main-only push block while still forbidding `tags:`
    - `pytest tests/test_ci_workflows.py -q --no-cov` is green (it was green at HEAD before the edit and remains green after)
    - No other workflow, pyproject.toml, or uv.lock change is made
  </done>
</task>

<task type="auto">
  <name>Task 2: Bring every doc and code comment in line with the six-cell, main-push shape</name>
  <files>docs/development.md, docs/contributing.md, docs/testing.md, tests/conftest.py</files>
  <precondition>Task 1 is complete, so the workflow and its contract tests already declare the six-cell shape; these edits describe that shape and cannot break the workflow guards.</precondition>
  <action>
    Replace each sentence or table cell named below with the stated new text. Do not touch unrelated prose, and keep en dashes and backticks in the existing style.

    1. docs/development.md, the release step labelled `4. **Commit and confirm CI.**`: replace the whole sentence after the bold label with `Commit the release changes and confirm the Test Matrix is green on that commit: all six cells (py3.10–3.13 on ubuntu-latest; py3.10 and py3.13 on macos-latest) plus the lint job.`

    2. docs/development.md, the Test Matrix row of the workflow table: change the Trigger cell to `Pushes to \`main\` and every pull request` and replace the leading description with `Six test cells (Python 3.10–3.13 on \`ubuntu-latest\`; Python 3.10 and 3.13 on \`macos-latest\`) run \`uv sync --frozen --extra dev --extra embed\` and then \`env -u FORCE_COLOR NO_COLOR=1 uv run --frozen pytest\``, leaving the rest of the cell (the color-hermetic parenthetical and the lint-job sentence) intact.

    3. docs/development.md, the PR CI bullet that begins `- PR CI runs the full Test Matrix`: change the opening to `PR CI runs the full Test Matrix on every push to \`main\` and every pull request: the six cells (py3.10–3.13 on ubuntu-latest; 3.10 and 3.13 on macos-latest) run the complete pytest suite (with the 90% coverage gate)`, leaving the remainder of the bullet untouched.

    4. docs/development.md, the coverage note that begins `CI's Test Matrix runs the full suite in every cell`: replace its wrapped sentence with `CI's Test Matrix runs the full suite in every cell, so the same gate applies in all six` followed by a new line reading `cells: py3.10–3.13 on ubuntu and py3.10/3.13 on macos.`

    5. docs/contributing.md, release step 4 beginning `4. **Commit and confirm the Test Matrix.**`: replace the sentence after the bold label with `Commit the release changes and confirm all six test cells (Python 3.10–3.13 on ubuntu; 3.10 and 3.13 on macos) plus the lint job are green on that commit.`

    6. docs/contributing.md, the intro sentence directly under the `### Test Matrix — \`test-matrix.yml\`` heading (the sentence describing when the workflow runs): replace it with `Runs on every push to \`main\` and on every pull request, with two jobs:`

    7. docs/contributing.md, the Test bullet: replace the cell list with `- **Test** — six cells: Python 3.10, 3.11, 3.12, and 3.13 on \`ubuntu-latest\`, and Python 3.10 and 3.13 on \`macos-latest\` (3.11 and 3.12 are matrix \`exclude\` entries).` and keep the remainder of the bullet (the frozen sync, the full-suite command, and the coverage-floor sentence).

    8. docs/contributing.md, the sentence that begins `There is no Windows runner in the matrix, and`: replace it with `There is no Windows runner in the matrix, and \`push: branches: [main]\` means feature-branch commits are covered by their pull request (one matrix run, not two) and tag pushes never trigger the Test Matrix — tags go to \`Publish\`.`

    9. docs/contributing.md, the sentence that follows the Windows-runner sentence and states how many cells must be green before a release tag: begin it with `All six test cells plus the lint job` and leave the rest (the release-tag gate and the bandit note) unchanged.

    10. docs/testing.md, the test_ci_workflows.py bullet: replace the phrase that names the matrix size with `the six-cell test matrix` and leave the rest of the bullet unchanged.

    11. docs/testing.md, the Test Matrix section opening paragraph that begins `This is the primary test workflow.`: replace its trigger sentence with `It triggers on pushes to \`main\` (\`push: branches: [main]\`, so feature branches rely on their pull request run and tags never trigger it) and on every pull request.` Keep the following fail-fast and cancel-in-progress sentence as-is.

    12. docs/testing.md, the paragraph that begins `The \`test\` job runs an`: replace it with `The \`test\` job runs a six-cell matrix — Python 3.10, 3.11, 3.12, and 3.13 on \`ubuntu-latest\`, and Python 3.10 and 3.13 on \`macos-latest\` (3.11 and 3.12 are matrix \`exclude\` entries) — with a 30-minute timeout per cell. Each cell:` and leave the numbered step list that follows unchanged.

    13. tests/conftest.py, the `_hermetic_sif_logging` docstring: replace the two-line parenthetical that currently cites the CI cell count with `leaked state silently silences every later ``caplog`` assertion (CI runs the` and `locked 9.0.3 in every matrix cell; newer pytest papers over the leak).` Keep the rest of the docstring (the reset-before-every-test purpose and the following sentences) unchanged.
  </action>
  <verify>
    <automated>
      uv run --frozen --extra dev --extra embed python -m pytest tests/test_ci_workflows.py tests/test_docs.py -q --no-cov
      grep -q "six cells" docs/development.md
      grep -q "six test cells" docs/contributing.md
      grep -q "six-cell" docs/testing.md
      ! grep -rn "eight-cell\|eight test cells\|Eight test cells\|all eight\|the eight py\|8-cell\|every push to any branch\|branches: \['\*\*'\]" docs/development.md docs/contributing.md docs/testing.md tests/conftest.py
    </automated>
  </verify>
  <done>
    - All four files describe six cells (Linux 3.10-3.13; macOS 3.10 and 3.13) and push-on-main plus every pull request
    - The negative grep finds no stale cell count, no every-branch-push claim, and no double-star branch-glob trigger snippet in the four files
    - tests/test_ci_workflows.py and tests/test_docs.py are still green
    - No file outside the six planned files is modified
  </done>
</task>

<task type="auto">
  <name>Task 3: Run the full quality gates and audit scope</name>
  <files>docs/development.md, docs/contributing.md, docs/testing.md, tests/conftest.py, .github/workflows/test-matrix.yml, tests/test_ci_workflows.py</files>
  <precondition>Tasks 1 and 2 are complete, so the workflow, its guards, and all prose describe the same six-cell shape.</precondition>
  <action>
    Run the full quality suite in CLAUDE.md order under the frozen lock with both extras: `ruff check src tests`, then `ruff format --check src tests`, then the full `pytest` run. Fix only failures caused by this plan; do not chase pre-existing skips or platform-gated tests.

    Then audit scope: run `git status --porcelain` and `git diff --name-only`, and confirm the only modified paths are the six files in this plan's `files_modified` plus `.planning/` artifacts. Confirm by inspection that `.github/workflows/publish.yml`, `.github/workflows/docs.yml`, `pyproject.toml`, `uv.lock`, and every `.planning/milestones/**` file are untouched.

    Leave the tree for the standard quick commit (`chore(quick-261118-lmm): shrink the CI matrix to six cells and push CI to main`). Do not tag, push, publish, or edit GitHub issues.
  </action>
  <verify>
    <automated>
      uv run --frozen --extra dev --extra embed ruff check src tests
      uv run --frozen --extra dev --extra embed ruff format --check src tests
      uv run --frozen --extra dev --extra embed python -m pytest -q
      status=$(git status --porcelain) || { echo "git status failed"; exit 1; }
      printf '%s' "$status" | grep -v '^.. .planning/' | grep -vE '^.. (\.github/workflows/test-matrix\.yml|tests/test_ci_workflows\.py|docs/development\.md|docs/contributing\.md|docs/testing\.md|tests/conftest\.py)$' | grep -q . && { echo "unexpected modified paths outside the planned scope"; exit 1; }
      echo scope-ok
    </automated>
  </verify>
  <done>
    - ruff check, ruff format --check, and the full pytest suite are green under `uv run --frozen --extra dev --extra embed`
    - `git status --porcelain` shows only the six planned files plus `.planning/` artifacts
    - publish.yml, docs.yml, pyproject.toml, uv.lock, and milestone archives are untouched
    - No tag, push, publish, or issue edit was performed
  </done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| GitHub Actions runner -> test result | The matrix shape decides which OS/Python combinations gate a merge; shrinking it trades coverage for capacity resilience |
| push/pull_request trigger -> verified commits | Which events run CI decides whether a commit is verified before review or merge |
| package indexes -> CI environment | Gates install from the frozen lock only; this plan adds no package |

## STRIDE Threat Register

| Threat ID | Category | Component | Severity | Disposition | Mitigation Plan |
|-----------|----------|-----------|----------|-------------|-----------------|
| T-lmm-01 | Tampering | `.github/workflows/test-matrix.yml` test-job matrix | medium | mitigate | Keep all four Python versions on `ubuntu-latest` and both boundary versions (3.10, 3.13) on `macos-latest`; pin the two macOS exclusions exactly in `tests/test_ci_workflows.py::test_matrix_declares_six_cells` so any further reduction or re-expansion fails the contract test. |
| T-lmm-02 | Repudiation | `on.push.branches` trigger | low | accept | Feature branches are verified by the `pull_request` run of the same commit; only a direct push to a feature branch with no PR would skip CI. The contributing docs require PRs into `main`, and the workflow exposes no secrets, so fork PRs stay read-only under `pull_request`. |
| T-lmm-03 | Denial of service | macOS hosted-runner capacity | low | mitigate | The change removes the two macOS cells that were repeatedly cancelled by arm64 capacity (v1.2.1 PR: two attempts lost py3.10/py3.13 macOS before a third passed), reducing exposure from four macOS cells to two and making PR runs deterministic under the same concurrency policy. |
| T-lmm-SC | Tampering | npm/pip/cargo installs | low | accept | This plan adds no dependency and changes no lock or packaging file; all gates run inside `uv run --frozen` and the workflow sync remains `uv sync --frozen`, so no new install surface exists. |
</threat_model>

<verification>
1. Task 1: the PyYAML check derives exactly six cells (Linux 3.10-3.13 plus macOS 3.10/3.13), confirms `push.branches` is `[main]`, `pull_request` is present, and `fail-fast` is false.
2. Task 1: `pytest tests/test_ci_workflows.py -q --no-cov` is green; the renamed guards fail if the exclusions are removed, if the contiguous python-version list changes, or if the double-star branch glob returns.
3. Task 2: `pytest tests/test_ci_workflows.py tests/test_docs.py -q --no-cov` is green; positive greps find the six-cell wording in development.md, contributing.md, and testing.md; the negative grep finds no stale cell count, every-branch trigger claim, or double-star trigger snippet in the four edited files.
4. Task 3: `ruff check src tests`, `ruff format --check src tests`, and the full `pytest` suite are green under `uv run --frozen --extra dev --extra embed`.
5. Scope: `git status --porcelain` shows only `.github/workflows/test-matrix.yml`, `tests/test_ci_workflows.py`, `docs/development.md`, `docs/contributing.md`, `docs/testing.md`, `tests/conftest.py`, plus `.planning/` artifacts; publish.yml, docs.yml, pyproject.toml, uv.lock, and milestone archives are untouched.
</verification>

<success_criteria>
- The Test Matrix workflow declares six cells — Linux 3.10, 3.11, 3.12, 3.13 and macOS 3.10, 3.13 — through two explicit macOS `exclude` entries, with every preserved invariant (fail-fast, concurrency cancellation, timeout, least privilege, SHA-pinned setup-uv, frozen sync, full-suite run, lint job) intact.
- Push CI runs on `main` only plus every pull request, so each feature-branch commit runs the matrix once.
- The CI contract tests pin the new shape and reject both a re-expanded matrix and a return of the every-branch push glob.
- All developer-facing docs and the conftest comment state the same shape; no stale count or trigger description remains in the edited files.
- Full quality suite (ruff check, ruff format --check, pytest) green; no dependency, lock, packaging, tag, push, or publish change.
</success_criteria>

<output>
Create `.planning/quick/261118-lmm-reduce-the-ci-matrix-to-six-cells-macos-/261118-lmm-SUMMARY.md` when done
</output>
