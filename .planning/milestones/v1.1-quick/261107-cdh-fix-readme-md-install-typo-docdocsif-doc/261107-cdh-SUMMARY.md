---
phase: quick-261107-cdh
plan: 01
subsystem: docs
tags: [docs, pypi, install-commands, typo-fix, docsif]

requires: []
provides:
  - "Correct docsif install commands in README and docs (all extras resolvable on PyPI)"
affects: []

actuals:
  tokens: 579
  tasks: 1
  commits: 1

tech-stack:
  added: []
  patterns: []

key-files:
  created: []
  modified:
    - README.md
    - docs/quickstart.md
    - docs/index.md
    - docs/installation.md

key-decisions:
  - "Exact-string replacement of the docdocsif token only; quoting, extras suffixes, and inline comments preserved byte-for-byte"

patterns-established: []

requirements-completed: []

coverage:
  - id: D1
    description: "All 9 docdocsif typo occurrences in user-facing pip install commands replaced with the real PyPI package name docsif across README.md and 3 docs files"
    verification:
      - kind: unit
        ref: "tests/test_docs.py (13 passed) + grep gates: zero docdocsif matches in README.md/docs/src/tests; exactly one 'pip install \"docsif[all]\"' line in README.md"
        status: pass
    human_judgment: false

duration: 1min
completed: 2026-11-07
status: complete
---

# Quick Task 261107-cdh: Fix README install typo docdocsif -> docsif Summary

**Replaced all 9 `docdocsif` typo occurrences with the real PyPI package name `docsif` in pip install commands across README.md and 3 docs files, so copy-pasted installs resolve instead of targeting a nonexistent package**

## Performance

- **Duration:** ~1 min (72s)
- **Started:** 2026-11-07T01:00:40Z
- **Completed:** 2026-11-07T01:01:53Z
- **Tasks:** 1
- **Files modified:** 4

## Accomplishments
- Replaced exactly 9 occurrences of `docdocsif` with `docsif` (pyproject.toml `[project] name`): README.md line 33; docs/quickstart.md lines 16, 468, 470; docs/index.md line 75; docs/installation.md lines 23, 60, 74, 89
- Removed the typo-squat-shaped supply-chain confusion hazard (threat T-QT261107-01 mitigated): users copy-pasting install commands from README/docs now target the published package
- All extras referenced in fixed commands (`[all]`, `[embed]`, `[dev]`) verified to exist in pyproject.toml `[project.optional-dependencies]`

## Task Commits

Each task was committed atomically:

1. **Task 1: Replace docdocsif with docsif in all 9 install-command occurrences** - `ef8edc2` (fix)

## Files Created/Modified
- `README.md` - Line 33 install-with-extras command now `pip install "docsif[all]"` (lines 27/54/68 were already correct, untouched)
- `docs/quickstart.md` - Lines 16, 468, 470: `[all]` and `[embed]` install commands corrected; inline comments preserved byte-for-byte
- `docs/index.md` - Line 75: `[all]` install command corrected
- `docs/installation.md` - Lines 23, 60, 74, 89: `[all]`, `[embed]`, `[dev]` install commands corrected

## Decisions Made
- Exact-string replacement of the `docdocsif` token only, via per-file replace of the bare package-name token — guarantees quoting, extras suffixes, and trailing comments stay byte-for-byte identical (plan requirement)

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None

## Verification Results

- Negative grep gate: `grep -rn docdocsif README.md docs/ src tests` returns zero matches (baseline: 9)
- Positive gate: README.md contains exactly one `pip install "docsif[all]"` line (baseline: 0)
- Docs code-block validator: `env -u FORCE_COLOR NO_COLOR=1 pytest tests/test_docs.py -q --no-cov` — 13 passed
- Changed-file scope: `git status` shows exactly the 4 planned files; generator-owned `docs/cli-reference.md` and `docs/configuration.md` untouched
- Commit diffstat: 4 files changed, 9 insertions(+), 9 deletions(-) — exactly 9 line replacements

## Self-Check: PASSED

All 4 modified files exist; commit `ef8edc2` verified as ancestor of HEAD; SUMMARY present at expected path.

## User Setup Required

None - no external service configuration required.

## Next Steps
None - defect closed. No code, tests, or config touched; ruff/full pytest suite unaffected by this docs-only change.

---
*Quick task: 261107-cdh*
*Completed: 2026-11-07*
