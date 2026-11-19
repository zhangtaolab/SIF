---
phase: quick-261119-juo
plan: 01
subsystem: release
tags: [release, version-bump, changelog, uv-lock]

# Dependency graph
requires: []
provides:
  - v1.2.2 release metadata across the single version literal, server.json, plugin/marketplace manifests, changelog, release-metadata tests, and the documented `sif --version` sample
  - Proven lock neutrality for the version bump (`uv lock --check` exits 0, `uv.lock` unchanged)
affects: [v1.2.2 tagging/publishing by the maintainer]

# Actuals (#2632) — chars/4 over the realized diff (5508 chars / 4 ≈ 1377).
actuals:
  tokens: 1377
  tasks: 2
  commits: 1

plan_head_before: abef400d23518aad21ea234328ae78507a80a347
plan_head_after: 9f6a227793a79ae4f03272c0481d7c341a3b3b88

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
    - docs/changelog.md
    - tests/test_release_metadata.py
    - docs/installation.md

key-decisions:
  - "Kept `src/sif/_version.py` as the only version literal; all four parity surfaces, the changelog, the release-metadata tests, and the installation sample were changed in one atomic unit so no intermediate state fails parity"
  - "Moved the `torch>=2.11` bullet out of `[Unreleased] ### Changed` into `[1.2.2] ### Changed` (replacing the Unreleased entry with `- N/A`) so it is recorded exactly once against the release that shipped it"
  - "Left the historical `## [1.2.1]` heading, its version bullet, and the `[1.2.1]:` tag link byte-unchanged; only the `[Unreleased]` compare link moved to v1.2.2...HEAD"

requirements-completed: [QUICK-RELEASE-1-2-2]

# Metrics
duration: 15min
completed: 2026-11-19
status: complete
---

# Quick Task 261119-juo: Release v1.2.2 Version Bump Summary

**docsif 1.2.2 is consistent across the single version literal, all three parity manifests, the changelog, the release-metadata tests, and the documented `sif --version` output, with the lock proven version-neutral and the full quality suite green.**

## Performance

- **Duration:** 15 min
- **Started:** 2026-11-19T06:23:24Z
- **Completed:** 2026-11-19T06:38:19Z (approx.)
- **Tasks:** 2/2
- **Files modified:** 7

## Accomplishments

- Bumped `src/sif/_version.py` to `1.2.2` and mirrored it in `server.json` (top-level and `packages[0].version`), `.claude-plugin/plugin.json`, and `.claude-plugin/marketplace.json`; `sif.__version__` and `APP_VERSION` both read `1.2.2` without separate edits.
- Added the `## [1.2.2] - 2026-11-19` changelog section between Unreleased and 1.2.1: Added (Intel XPU auto-selection via `_auto_device`), Changed (version bump plus the moved `torch>=2.11` bullet), and Fixed (Windows subpath separator filter and Windows test-suite guards).
- Moved the `torch>=2.11` bullet out of `[Unreleased] ### Changed` (replaced with `- N/A`) into the 1.2.2 section — recorded once, not duplicated.
- Updated the link block: `[Unreleased]` now compares `v1.2.2...HEAD` and a `[1.2.2]:` tag link was added before the untouched `[1.2.1]:` line.
- Renamed and re-pinned `test_changelog_has_1_2_2` and `test_version_literal_is_1_2_2`; updated the `docs/installation.md` `sif --version` sample to `sif, version 1.2.2`.
- Audit proved no stale `1.2.1` current-version assertion remains outside the historical changelog lines, and the lock is version-neutral.

## Task Commits

1. **Task 1: Bump to 1.2.2 across every parity surface, the changelog, the release-metadata tests, and the installation sample** — `9f6a227` (chore)
2. **Task 2: Audit for stray current-version references, prove the lock is version-neutral, and run the full quality gates** — no code changes (read-only audit + gates)

Measured: `git rev-list --count abef400..HEAD` = 1 commit.

## Gate Results

| Gate | Command | Result |
|------|---------|--------|
| Targeted tests | `pytest tests/test_release_metadata.py tests/unit/mcp/test_plugin.py tests/unit/mcp/test_registry_script.py -q --no-cov` | 59 passed |
| Stray-reference audit | `grep -rn "1\.2\.1" ... \| grep -v docs/changelog.md` | 0 hits |
| Changelog region gates | heading / `[1.2.2]:` / compare link / torch counts | 1 / 1 / 1 / Unreleased=0, 1.2.2=1 |
| Installation sample | `grep -c 'sif, version 1\.2\.2' docs/installation.md` | 1 |
| Lock neutrality | `uvx --from uv==0.13.8 uv lock --check` | exit 0; `uv.lock` unmodified |
| Ruff check | `ruff check src tests` | All checks passed |
| Ruff format | `ruff format --check src tests` | 237 files already formatted |
| Type gate | `ty check src/sif` | 22 diagnostics (baseline unchanged; ty exits 1 by design) |
| Full pytest | `pytest -q` with coverage gate | **3165 passed, 84 skipped, 0 failed, 0 errors**, coverage **94.02%** (gate 90%), exit 0 |

## Files Created/Modified

- `src/sif/_version.py` — the single version literal is now `1.2.2`
- `server.json` — top-level and `packages[0].version` are 1.2.2
- `.claude-plugin/plugin.json` — version 1.2.2
- `.claude-plugin/marketplace.json` — `plugins[0].version` 1.2.2
- `docs/changelog.md` — new 1.2.2 section, Unreleased Changed bullet replaced with `- N/A`, Unreleased compare link moved to v1.2.2...HEAD, `[1.2.2]:` link added
- `tests/test_release_metadata.py` — `test_changelog_has_1_2_2` and `test_version_literal_is_1_2_2`
- `docs/installation.md` — the `sif --version` sample reads 1.2.2

## Deviations from Plan

### Auto-fixed Issues

None. The plan executed as written; no bug or blocking issue required a fix.

### Observations (non-code)

**1. [Observation] Planning-time HEAD vs execution HEAD**
- **Found during:** Task 1 precondition check
- **Detail:** The plan records the planning-time HEAD as `240ff51`; execution ran from `abef400` (the commit that added the plan document). The tree was clean, `uv` was on PATH, and no release surface differed, so the precondition held in substance.
- **Impact:** None — the delivery is unchanged.

**2. [Observation] Flaky watcher test on the first full-suite run**
- **Found during:** Task 2, first full pytest run
- **Detail:** `tests/unit/indexing/test_watcher.py::TestRecoveryTick::test_disappear_return_cycle_stops_each_debouncer` failed once under full-suite load (1 failed, 3164 passed, 84 skipped, coverage 94.02%). It is a thread-liveness/rename timing test unrelated to this metadata-only plan; it passed 6/6 times in isolation (one rerun plus five repeats).
- **Resolution:** A clean full-suite rerun produced 3165 passed, 84 skipped, 0 failed, 0 errors, coverage 94.02%, exit 0. No test was modified or skipped.
- **Files modified:** None

## Issues Encountered

The single flaky watcher-test failure above. No other issues.

## User Setup Required

None.

## Next Phase Readiness

- The tree reads 1.2.2 on every release surface; the maintainer can tag `v1.2.2` and publish when ready. No tag, push, publish, GitHub release, issue edit, or workflow change was performed.
- `pyproject.toml`, `uv.lock`, `[tool.uv.sources]`, `.github/workflows/**`, and every changelog entry older than the new 1.2.2 section are unmodified.
- `.planning/` artifacts (this SUMMARY, STATE.md) are left uncommitted for the orchestrator.

## Threat Surface Notes

- No new security-relevant surface: only release metadata, changelog text, and test literals changed. T-juo-01 (version-surface tampering) is mitigated by the atomic bump and the parity tests; T-juo-02 (history integrity) by inserting only between Unreleased and 1.2.1 with region-scoped counts; T-juo-03 by not claiming the recorded Windows `signal.SIGKILL` daemon defect as fixed; T-juo-SC was not exercised (no installs, lock unchanged).

---

## Self-Check: PASSED

- All 7 modified files exist on disk and were committed in `9f6a227`
- Commit `9f6a227` is an ancestor of HEAD and is the only commit after the plan ledger base
- `uv.lock`, `pyproject.toml`, and `.github/workflows/` are unmodified; no tag exists at HEAD

---
*Quick task: 261119-juo*
*Completed: 2026-11-19*
