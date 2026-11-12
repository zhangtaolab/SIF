---
phase: quick-261107-cdh
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - README.md
  - docs/quickstart.md
  - docs/index.md
  - docs/installation.md
autonomous: true
estimate:
  tokens: 12000
  raw_tokens: 12000
  tasks: 1
  confidence: low
must_haves:
  truths:
    - "grep for docdocsif across README.md, docs/, src, and tests returns zero matches"
    - 'README.md install-with-extras command reads `pip install "docsif[all]"` (exactly one such line)'
    - "Every fixed pip install command names the real PyPI package docsif (pyproject.toml [project] name) with extras that exist in pyproject.toml [project.optional-dependencies] ([all], [embed], [dev])"
    - "docs/cli-reference.md and docs/configuration.md are untouched (generator-owned via make docs-generate)"
  artifacts:
    - README.md
    - docs/quickstart.md
    - docs/index.md
    - docs/installation.md
  key_links:
    - "README.md/docs install commands <-> pyproject.toml [project] name = docsif"
    - "extras suffixes in fixed commands <-> pyproject.toml [project.optional-dependencies] keys (dev, embed, mcp, all)"
---

<objective>
Fix the PyPI package-name typo `docdocsif` -> `docsif` in user-facing install commands.

A planning-time live grep found 9 occurrences across 4 files — README.md line 33 (the reported defect) plus 8 more of the identical typo in docs/quickstart.md, docs/index.md, and docs/installation.md, all inside `pip install` commands. The correct package name is `docsif` (pyproject.toml `[project] name = "docsif"`, published on PyPI as docsif). Extras used in the typo'd commands — `[all]`, `[embed]`, `[dev]` — all exist in pyproject.toml `[project.optional-dependencies]`.

Purpose: users copying install commands from README or docs currently attempt to install a nonexistent package name.
Output: corrected README.md and 3 docs files; zero `docdocsif` matches in the deliverable scope.
</objective>

<execution_context>
@~/.claude/gsd-core/templates/summary.md
</execution_context>

<context>
@pyproject.toml

Notes:
- Package name source of truth: pyproject.toml line 6, `name = "docsif"`. Extras: `dev`, `embed`, `mcp`, `all` (lines 43-65).
- README.md lines 27, 54, 68 already correctly say `pip install docsif` / `pipx install docsif` — leave them unchanged.
- tests/test_docs.py is the docs code-block validator; `pip install` is on its skip blacklist (line 40), so the changed commands are never executed by tests.
- docs/cli-reference.md and docs/configuration.md are generator-owned (make docs-generate) and contain no occurrences — do not edit them.
</context>

<tasks>

<task type="auto">
  <name>Task 1: Replace docdocsif with docsif in all 9 install-command occurrences</name>
  <files>README.md, docs/quickstart.md, docs/index.md, docs/installation.md</files>
  <action>
  Replace every occurrence of the string `docdocsif` with `docsif` — exactly 9 occurrences across 4 files, enumerated:
  - README.md line 33: pip install "docdocsif[all]"
  - docs/quickstart.md line 16: pip install "docdocsif[all]"
  - docs/quickstart.md line 468: pip install "docdocsif[embed]"
  - docs/quickstart.md line 470: pip install "docdocsif[all]"
  - docs/index.md line 75: pip install "docdocsif[all]"
  - docs/installation.md line 23: pip install "docdocsif[all]"
  - docs/installation.md line 60: pip install "docdocsif[embed]"
  - docs/installation.md line 74: pip install "docdocsif[dev]"
  - docs/installation.md line 89: pip install "docdocsif[all]"
  Only the package-name token changes; preserve surrounding quoting and the extras suffix byte-for-byte (e.g. pip install "docdocsif[all]" becomes pip install "docsif[all]"). Correct name per pyproject.toml [project] name = "docsif". Do not reformat lines, do not touch any other content, and do not edit docs/cli-reference.md or docs/configuration.md (generator-owned). README.md lines 27/54/68 are already correct — leave them. This is a docs-only change: no Python source, tests, or config are modified. Commit the 4-file fix atomically.
  </action>
  <verify>
    <automated>test -z "$(grep -rn docdocsif README.md docs/ src tests 2>/dev/null)" &amp;&amp; [ "$(grep -c 'pip install "docsif\[all\]"' README.md)" = "1" ] &amp;&amp; env -u FORCE_COLOR NO_COLOR=1 pytest tests/test_docs.py -q --no-cov</automated>
  </verify>
  <done>
  Zero `docdocsif` matches across README.md, docs/, src, and tests; README.md contains exactly one pip install "docsif[all]" line; all extras referenced in fixed commands exist in pyproject.toml; docs code-block validator passes (13 tests).
  </done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| none | Docs-only string replacement; no code, no user input, no network, no schema, no dependencies |

## STRIDE Threat Register

| Threat ID | Category | Component | Severity | Disposition | Mitigation Plan |
|-----------|----------|-----------|----------|-------------|-----------------|
| T-QT261107-01 | Tampering | README.md + docs install commands | low | mitigate | Users copy-pasting install commands from docs previously targeted a wrong/nonexistent package name — a typo-squat-shaped supply-chain confusion hazard; this plan's exact-string replacement to the real PyPI artifact name (pyproject.toml [project] name = "docsif") removes it |
| T-QT261107-SC | Tampering | package installs | low | accept | No package-manager install tasks in this docs-only plan; package legitimacy gate not applicable |
</threat_model>

<verification>
- Negative grep gate: `grep -rn docdocsif README.md docs/ src tests` returns nothing (baseline at planning time: 9 matches)
- Positive gate: README.md contains exactly one `pip install "docsif[all]"` line (baseline: 0)
- Docs code-block validator green: `env -u FORCE_COLOR NO_COLOR=1 pytest tests/test_docs.py -q --no-cov` (13 passed at baseline; `--no-cov` required because the repo-wide fail_under=90 gate fails any targeted single-file run)
- Extras referenced in fixed commands ([all], [embed], [dev]) exist in pyproject.toml [project.optional-dependencies]
- ruff / full pytest suite unaffected — no Python source touched
</verification>

<success_criteria>
- All 9 `docdocsif` occurrences replaced with `docsif`; zero remaining matches in deliverable scope
- README.md, docs/quickstart.md, docs/index.md, docs/installation.md are the only files changed
- docs/cli-reference.md and docs/configuration.md untouched
- Atomic commit containing exactly the 4 doc files
</success_criteria>

<output>
Create `.planning/quick/261107-cdh-fix-readme-md-install-typo-docdocsif-doc/261107-cdh-SUMMARY.md` with `status: complete` in SUMMARY frontmatter when done. Do NOT commit docs artifacts (SUMMARY.md, PLAN.md, STATE.md) — the orchestrator handles the docs commit.
</output>
