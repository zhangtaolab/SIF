---
phase: quick-261118-np7
plan: 01
status: complete
subsystem: release
tags: [versioning, release-metadata, changelog, mcp-registry, claude-plugin]

# Dependency graph
requires:
  - phase: 22-mcp-sdk-v2-agent-packaging
    provides: server.json / plugin.json / marketplace.json manifests and their mirror tests (test_registry_script.py, test_plugin.py)
  - phase: 17-05 single-sourcing
    provides: src/sif/_version.py as the only version literal; every runtime surface derives from it
provides:
  - Coherent 1.2.0 release identity across _version.py, server.json, plugin.json, marketplace.json, changelog, and install docs
  - docs/changelog.md [1.2.0] - 2026-11-18 entry with retargeted Unreleased compare link and [1.2.0] release link
  - Release-metadata pins retargeted to 1.2.0 (test_changelog_has_1_2_0, test_version_literal_is_1_2_0)
affects: [v1.2 milestone close, publish workflow tag gate, windows smoke]

actuals:
  tokens: 725
  tasks: 3
  commits: 1

# Tech tracking
tech-stack:
  added: []
  patterns: []

key-files:
  created: []
  modified:
    - src/sif/_version.py
    - server.json
    - .claude-plugin/plugin.json
    - .claude-plugin/marketplace.json
    - tests/test_release_metadata.py
    - tests/test_windows_smoke_script.py
    - docs/changelog.md
    - docs/installation.md

key-decisions:
  - "One atomic commit for the whole bump (precedent: the 1.0.1 bump); no tag v1.2.0, no publish — the tree is release-ready, not released"
  - "Changelog 1.2.0 entry condenses the v1.2 milestone (phases 18-24) into user-facing Changed/Added/Fixed bullets with no GSD phase numbers"
  - "Fixed section records only the genuine fix: canonical metadata serializer persists YAML dates as ISO text (latent TypeError)"

patterns-established: []

requirements-completed: []

verification:
  - "python -c version chain: sif.__version__ == sif._version.__version__ == sif.cli.__version__ == APP_VERSION == 1.2.0 (versions-ok)"
  - "CLI banner exact: PYTHONPATH=src python -m sif.cli.main --version -> 'sif, version 1.2.0'"
  - "Identity/mirror test net: 71 passed (test_version_identity, test_release_metadata, test_plugin, test_registry_script, test_windows_smoke_script)"
  - "Changelog structure greps: one [1.2.0] - 2026-11-18 heading, release + compare links, section ordered before 1.1.2; tests/test_docs.py 20 passed"
  - "Generator no-op proof: make docs-generate exit 0 with zero diff in docs/cli-reference.md and docs/configuration.md"
  - "Stale-literal sweep: '1.1.2' remains in exactly docs/changelog.md, docs/contributing.md, docs/development.md (the allowed survivors)"
  - "Full suite: ruff check clean, ruff format --check clean (236 files), pytest 3233 passed / 1 skipped @ 95.03% coverage"
  - "Scope: git status shows exactly the 8 planned files; commit d97838c has no deletions; no v1.2* tag exists"
---

# Quick Task 261118-np7: Bump version for the v1.2 milestone release — Summary

Bumped the entire release identity to 1.2.0 in one atomic commit: the single-sourced `_version.py` literal, both server.json version fields, the Claude Code plugin and marketplace manifests, the release-metadata test pins, the `[1.2.0] - 2026-11-18` changelog entry with retargeted links, and the install-doc banner.

## Accomplishments

- **Version identity at 1.2.0 everywhere:** `src/sif/_version.py` literal bumped; `sif.__version__`, `sif.cli.__version__`, `APP_VERSION`, and the MCP `serverInfo` all derive and were asserted equal to `1.2.0`; the CLI banner prints exactly `sif, version 1.2.0`.
- **Manifests:** `server.json` top-level and `packages[0]` (pypi `docsif`) versions, `.claude-plugin/plugin.json`, and `.claude-plugin/marketplace.json` all report `1.2.0`; the phase-22 mirror tests (`test_plugin.py::test_manifest_version_parity`, `test_registry_script.py` server.json pins) stay green — fully mocked, no network.
- **Release-metadata pins:** `test_changelog_has_1_1_2` renamed to `test_changelog_has_1_2_0` (asserts the 1.2.0 heading, `[1.2.0]:` link, and `compare/v1.2.0...HEAD`); `test_version_literal_is_1_1_2` renamed to `test_version_literal_is_1_2_0`; every other test in the file byte-identical.
- **Windows smoke fixture:** `tests/test_windows_smoke_script.py` `build_cli_invocations("python", tmp_path, "1.2.0")` tracks the single-sourced literal per the helper's contract.
- **Changelog:** inserted `## [1.2.0] - 2026-11-18` between the Unreleased block and the 1.1.2 section with dense Keep-a-Changelog Changed/Added/Fixed bullets (new deps `mcp`/`rapidfuzz`, uv-first install docs with Linux CPU-torch recipe, evidence-gated defaults, `sif eval` bench + rapidfuzz DYM, metadata filtering + discovery, search correctness, index maintenance, MCP SDK v2 rebuild, model management, and the metadata-serializer YAML-date fix). `[Unreleased]` compare retargeted to `v1.2.0...HEAD`; `[1.2.0]` release link inserted above `[1.1.2]:`; `[1.1.1]`'s unusual compare form left untouched as historical.
- **Install docs:** `docs/installation.md` expected-output banner now reads `sif, version 1.2.0` (one line only).

## Verification Results

- Task 1 gate: `versions-ok` printed; CLI banner grep exact; identity test net initially 70/71 — the one failure was `test_changelog_has_1_2_0`, which pins the Task 2 changelog entry and passed once that landed (re-run: 71 passed).
- Task 2 gate: changelog structure greps all pass (one heading, correct position, both links); `tests/test_docs.py` 20 passed.
- Task 3 gates: `make docs-generate` exit 0 with `git diff --exit-code` clean on both generator-owned docs; stale-literal sweep matches the exact 3-file allowlist (`docs/changelog.md`, `docs/contributing.md`, `docs/development.md`); `ruff check` + `ruff format --check` clean; full pytest **3233 passed / 1 skipped @ 95.03% coverage**; scope shows exactly the 8 planned files with no deletions; `git tag --list 'v1.2*'` empty.

## Deviations from Plan

None - plan executed exactly as written.

## Non-Goals Honored

- No tag `v1.2.0` created; nothing published; `scripts/publish_registry.py --check`/`--publish` not run (its PyPI-presence check legitimately fails until the real release).
- `pyproject.toml`, `uv.lock`, `README.md`, and both generator-owned docs untouched.
- No Windows smoke run; no package installs.

## Commit

- `d97838c` chore(quick-261118-np7): bump all version identities to 1.2.0 for the v1.2 release (8 files, +36/-16) — parent `4d506ff`

## Self-Check: PASSED

- All 8 modified files committed in `d97838c` (verified via `git show --stat` and `git status --porcelain` clean of modifications).
- Commit `d97838c` is HEAD on `dev` and an ancestor of HEAD (verified via `git show`).
- No v1.2* tag exists; generated coverage artifacts (htmlcov/, coverage.xml) are gitignored, no untracked leakage.
