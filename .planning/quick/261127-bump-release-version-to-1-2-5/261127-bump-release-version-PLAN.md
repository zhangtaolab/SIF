---
phase: quick-261127-bump-release-version
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
requirements: [QUICK-RELEASE-1-2-5]
---

<objective>
Ship the v1.2.5 patch-release metadata for the Phase 19 post-ship correctness round.

The `[Unreleased]` changelog held the exact `--min-score` threshold fix and the truthful
`query`/`vsearch` help texts. This task promotes them into a `## [1.2.5] - 2026-11-27`
section and carries 1.2.5 across every release surface in one atomic version unit:
the single literal in `src/sif/_version.py`, `server.json` (top-level and
`packages[0].version`), `.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json`,
the changelog heading and link block, the release-metadata tests, and the documented
`sif --version` sample.

Scope boundaries:
- Do NOT touch `pyproject.toml` (dynamic version), `uv.lock`, or `.github/workflows/**`.
- Do NOT rewrite historical changelog entries; only `[Unreleased]` and the new section change.
- Do NOT tag, push, publish, or edit issues from this task.
</objective>

<verification>
- `src/sif/_version.py`, `server.json` (both fields), plugin manifest, and marketplace manifest all read 1.2.5.
- `tests/test_release_metadata.py` pins 1.2.5 via `test_changelog_has_1_2_5` and `test_version_literal_is_1_2_5`.
- `docs/changelog.md` has one `## [1.2.5] - 2026-11-27` heading, one `[1.2.5]:` tag link, and `[Unreleased]` compares `v1.2.5...HEAD`.
- Target tests (`test_release_metadata.py`, MCP manifest parity) pass; ruff and `ty` at baseline.
</verification>
