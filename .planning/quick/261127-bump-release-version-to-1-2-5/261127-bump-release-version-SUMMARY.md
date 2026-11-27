---
phase: quick-261127-bump-release-version
plan: 01
subsystem: release
tags: [release, version-bump, changelog]
requires: []
provides:
  - v1.2.5 release metadata across the single version literal, server.json, plugin/marketplace manifests, changelog, release-metadata tests, and the documented sif --version sample
affects: [v1.2.5 tagging/publishing by the maintainer]
actuals:
  tokens: 900
  tasks: 1
  commits: 1
plan_head_before: bbd813aa
plan_head_after: f3e9e443
status: complete
completed: 2026-11-27
---

# Quick Task 261127: Release v1.2.5 Version Bump

**docsif 1.2.5 is consistent across the single version literal, all three parity manifests, the changelog, the release-metadata tests, and the documented `sif --version` output.**

## Accomplishments

- Promoted the `[Unreleased]` `--min-score` entries into `## [1.2.5] - 2026-11-27` (Changed: version bullet plus the per-leg `query --min-score` contract; Fixed: the exact displayed-score threshold), replaced the emptied Unreleased sub-sections with `- N/A`, and moved the compare link to `v1.2.5...HEAD` with a new `[1.2.5]:` tag link.
- Bumped `src/sif/_version.py` to `1.2.5` and mirrored it in `server.json` (top-level and `packages[0].version`), `.claude-plugin/plugin.json`, and `.claude-plugin/marketplace.json`; `sif.__version__` reads 1.2.5 without separate edits.
- Renamed and re-pinned `test_changelog_has_1_2_5` and `test_version_literal_is_1_2_5`; updated the `docs/installation.md` sample to `sif, version 1.2.5`.
- Regenerated `docs/cli-reference.md` and `docs/configuration.md` from source: zero diff, so the generated references were already in sync.

## Gate Results

| Gate | Command | Result |
|------|---------|--------|
| Release metadata + parity | `pytest tests/test_release_metadata.py tests/unit/mcp/test_plugin.py tests/unit/mcp/test_registry_script.py -q --no-cov` | 59 passed |
| Docs/hygiene | `pytest tests/test_docs.py tests/test_hygiene.py -q --no-cov` | 38 passed |
| Ruff | `ruff check src tests` / `ruff format --check src tests` | clean / 239 formatted |
| Type gate | `ty check src/sif` | 1 diagnostic (pre-existing `embedder.py:870`) |
| Full suite | `pytest -q` | not run locally: the dev+embed extra install stalled at 18 min; CI Test Matrix covers it on the push |

## Files Modified

- `src/sif/_version.py` — `__version__ = "1.2.5"`
- `server.json` — top-level and `packages[0].version` 1.2.5
- `.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json` — 1.2.5
- `docs/changelog.md` — new 1.2.5 section, Unreleased Changed/Fixed set to `- N/A`, link block updated
- `tests/test_release_metadata.py` — 1.2.5 test names and literals
- `docs/installation.md` — `sif, version 1.2.5`

## Notes

- `pyproject.toml`, `uv.lock`, and `.github/workflows/**` are untouched.
- Tagging and publishing remain maintainer actions.
