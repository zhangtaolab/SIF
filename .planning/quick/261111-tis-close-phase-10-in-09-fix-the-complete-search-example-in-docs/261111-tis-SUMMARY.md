---
phase: quick-261111-tis
plan: 01
subsystem: docs
tags: [documentation, pathlib, expanduser, sqlite3, api-reference, phase-10-review]

requires: []
provides:
  - "docs/api-reference.md database examples open the user's index through Path.expanduser before sqlite3.connect / DatabaseConnection / SearchBackend (no raw-tilde DB argument remains)"
  - "Phase 10 IN-09 closed in 10-REVIEW-DISPOSITION.md (open 8 -> 7, total 22)"
affects: [phase-10-review-backlog, batch-261111-tio, api-reference-docs]

actuals:
  tokens: 1049    # chars/4 over the realized diff (4199 diff chars)
  tasks: 2
  commits: 2
plan_head_before: 381df0dc49bf983db18b03702c08662abc7206b3
plan_head_after: eb18aa883eca3164cd5ae08041b7bf03b945853e

tech-stack:
  added: []
  patterns:
    - "stdlib pathlib Path(...).expanduser() before any DB-opening call in hand-owned doc examples; wrapper chosen by constructor type (Path | str -> expanded Path; db_path: str -> str(expanded Path))"

key-files:
  created: []
  modified:
    - docs/api-reference.md
    - .planning/milestones/v1.0-phases/10-raise-pytest-coverage-to-90/10-REVIEW-DISPOSITION.md

key-decisions:
  - "Fixed all three raw-tilde DB-open sites (the finding's named Complete Search Example plus the trivially-identical DatabaseConnection and SearchBackend usage patterns) per the item's scope rule; collection-registration ~/Documents literals left untouched (different API surface — stored paths, not DB-open calls)"
  - "Ledger open count read from execution-time git show HEAD (8, siblings tip/tiq/tir already landed) and decremented to 7; never hardcoded"

patterns-established:
  - "Static doc gate (block compile + fixed-form literal counts + raw-tilde negative counts) demonstrably red at baseline and green after fix, paired with a throwaway-HOME subprocess demonstration of the doc's verbatim db_path expression"

requirements-completed: [PHASE10-IN-09]

coverage:
  - id: D1
    description: "All three api-reference.md database examples expand the tilde via pathlib before opening the DB; all 65 python blocks compile; no raw-tilde DB argument remains; every other doc line byte-identical"
    requirement: "PHASE10-IN-09"
    verification:
      - kind: other
        ref: "plan Task 1 static gate (python -I): 65 blocks compile; 4 fixed-form literals each x1; pathlib import x3; raw-tilde DB hits 0 (baseline 3)"
        status: pass
      - kind: other
        ref: "plan Task 1 sandbox gate (throwaway HOME, seeded marker DB): old raw-tilde form rc=1 'unable to open database file'; doc's verbatim db_path expression rc=0 opens intended DB; no literal ~ directory"
        status: pass
    human_judgment: false
  - id: D2
    description: "IN-09 recorded fixed in both ledger representations; open count exactly one less than execution-time HEAD (8 -> 7, total 22); all other records byte-identical"
    requirement: "PHASE10-IN-09"
    verification:
      - kind: other
        ref: "plan Task 2 reconstruction gate (python -I byte-equality vs git show HEAD + three scoped replacements, count computed dynamically) -> IN-09-fixed; open 8 -> 7; all-other-ledger-content-unchanged"
        status: pass
    human_judgment: false

duration: 9min
completed: 2026-11-11
status: complete
---

# Phase quick-261111-tis Plan 01: Close Phase 10 IN-09 Summary

**The three raw-tilde database examples in docs/api-reference.md (Complete Search Example, DatabaseConnection usage, MCPServer/SearchBackend usage) now resolve the path through pathlib Path.expanduser before opening the DB — sandbox-proven to open the intended index under a throwaway HOME — and IN-09 is closed in the Phase 10 disposition ledger (open 8 -> 7)**

## Performance

- **Duration:** ~9 min
- **Started:** 2026-11-11T14:01:58Z
- **Completed:** 2026-11-11T14:10:32Z
- **Tasks:** 2
- **Files modified:** 2 (task files); planning SUMMARY intentionally uncommitted (orchestrator-owned)

## Accomplishments

- Closed Phase 10 IN-09 ("api-reference example uses `sqlite3.connect("~/...")` — tilde is not expanded", 10-REVIEW.md:207-211). The finding's named site — the Complete Search Example (baseline docs/api-reference.md:818) — now builds `db_path = Path("~/.local/share/sif/sif.db").expanduser()` and opens `sqlite3.connect(str(db_path))`, so the example opens the reader's real index instead of failing with "unable to open database file".
- Fixed the two trivially-identical raw-tilde DB-open patterns the finding's defect repeats at, per the item's scope rule: the DatabaseConnection usage example (baseline line 650) and the MCPServer/SearchBackend usage example (baseline line 790). Source-verified reason neither class expands the tilde: `DatabaseConnection.__init__` (src/sif/database/connection.py:19-22) wraps the argument in `Path()` and `parent.mkdir(parents=True, exist_ok=True)` with NO expanduser — a raw tilde argument creates a literal `~/.local/share/sif` directory tree in the reader's cwd; `SearchBackend.__init__` (src/sif/mcp/backend.py:86-88) stores the raw string and `_run_in_db` (backend.py:113) forwards it to DatabaseConnection.
- Wrapper chosen by constructor type: DatabaseConnection takes `Path | str` so the expanded Path is passed directly; SearchBackend takes `db_path: str` so the expanded path is wrapped in `str()`.
- All 65 python blocks still compile; the static gate is demonstrably red at the unmodified baseline (3 raw-tilde hits, 0 fixed forms, 0 pathlib imports) and green after the fix (0 raw-tilde hits, each of the 4 fixed-form literals x1, pathlib import x3). Every other line of api-reference.md is byte-identical.
- Ledger closure via the three-edit convention with an execution-time-robust count decrement (8 -> 7, total 22 unchanged) and a byte-equality reconstruction gate proving no other finding record changed.

## Task Commits

Each task was committed atomically:

1. **Task 1: Expand the tilde in the three api-reference database examples** - `8eb2fc5` (docs)
2. **Task 2: Close only IN-09 in the Phase 10 disposition ledger** - `eb18aa8` (docs)

Planning artifacts (this SUMMARY) are intentionally uncommitted — the orchestrator owns the docs/state commit. The ledger and docs/api-reference.md ARE task work and were committed above.

## Doc Verify Gate Evidence

- **Static gate (red at baseline -> green after fix):** at HEAD 381df0d the doc had 65 compiling python blocks, raw-tilde DB hits `{connect("~: 1, DatabaseConnection("~: 1, SearchBackend("~: 1}` (3 total), 0 fixed-form literals, 0 `from pathlib import Path`. After the fix: 65 blocks compile, 0 raw-tilde DB hits, each of the 4 fixed-form literals appears exactly once, `from pathlib import Path` appears exactly 3 times. The gate can only pass after all three sites are corrected (non-vacuous).
- **Sandboxed demonstration (throwaway HOME, seeded marker DB, never the real user DB):**
  - OLD raw-tilde form `sqlite3.connect("~/.local/share/sif/sif.db")` -> rc=1, `sqlite3.OperationalError: unable to open database file` (sqlite3 neither expands `~` nor creates parent directories); no literal `~` directory created.
  - NEW form running the doc's verbatim `db_path = Path("~/.local/share/sif/sif.db").expanduser()` line under an overridden HOME -> rc=0, opens the seeded intended DB (`SELECT x FROM marker` returns 42), asserts `db_path == Path.home() / ".local/share/sif/sif.db"`, and creates no literal `~` directory in the subprocess cwd.

## Collection-Registration Literals: Checked and Left

The `~/Documents/...` arguments elsewhere in api-reference.md are a DIFFERENT API surface — collection paths stored as given, not DB-opening calls — and are not the defect IN-09 names. All 8 were verified present and deliberately left untouched (post-fix lines 40, 41, 49, 89, 144, 152, 851, 866): `collection.add_path("~/Documents/notes")`, `collection.add_path("~/Documents/ideas")`, `collection.remove_path("~/Documents/old-notes")`, `paths=["~/Documents/notes"]` (x2), `manager.add_path("uuid-string", "~/Documents/more-notes")`, `manager.remove_path("uuid-string", "~/Documents/old-notes")`, `manager.add_path(collection.id, "~/Documents/ideas")`.

## Files Created/Modified

- `docs/api-reference.md` - three example blocks corrected (9 insertions, 3 deletions):
  - Complete Search Example: `from pathlib import Path` added after `import sqlite3` (stdlib-first); `db_path = Path("~/.local/share/sif/sif.db").expanduser()` inserted immediately before the with statement (now line 823); with statement changed to `with sqlite3.connect(str(db_path)) as db:` (line 824). The with body (HybridSearcher construction, SearchOptions, search call, result display loop) is byte-identical.
  - DatabaseConnection usage: `from pathlib import Path` added as the block's first import with a blank line before the sif import (line 648); construction now `conn = DatabaseConnection(Path("~/.local/share/sif/sif.db").expanduser())` (line 652). The connect() usage and query are byte-identical.
  - MCPServer/SearchBackend usage: `from pathlib import Path` added as the block's first import with a blank line before the sif imports (line 787); construction now `server = MCPServer(SearchBackend(str(Path("~/.local/share/sif/sif.db").expanduser())))` (line 794). The register_tools and transport lines are byte-identical.
- `.planning/milestones/v1.0-phases/10-raise-pytest-coverage-to-90/10-REVIEW-DISPOSITION.md` - three scoped edits (3 insertions, 3 deletions): IN-09 YAML `disposition: open -> fixed` (id/severity/title preserved); aggregate `open: 8 -> 7` (execution-time HEAD value); IN-09 markdown row replaced with Source cell naming quick 261111-tis. `total: 22` and the `recorded` timestamp unchanged; no `**Status:**` line introduced.

## Gate Results

| Gate | Result |
|------|--------|
| Task 1 static doc gate (65 blocks compile; 4 fixed-form literals x1; pathlib import x3; 0 raw-tilde DB args) | PASS (red at baseline: 3 raw-tilde hits / 0 fixed forms; green after fix) |
| Task 1 sandboxed demonstration (throwaway HOME) | PASS (old form rc=1 "unable to open database file"; doc's verbatim db_path expression rc=0 opens intended DB; no literal ~ directory) |
| Task 2 reconstruction gate (byte-equality vs execution-time HEAD + 3 edits, dynamic count) | PASS (open 8 -> 7; all-other-ledger-content-unchanged; non-sibling open rows WR-07/WR-08/IN-02/IN-07 preserved) |
| `ruff check src tests` | PASS — All checks passed |
| `ruff format --check src tests` | PASS — 188 files already formatted |
| `python -m pytest` (full, with coverage; PATH miniconda python 3.13.9) | PASS — 1529 passed, 1 skipped, 95.06% coverage (fail_under=90 met); matches execution-time baseline exactly (doc-only item, no test changes) |
| `ty check src/sif` | PASS — All checks passed (regression gate; no src/ changes) |
| Scope guard `git diff --exit-code -- src tests docs/cli-reference.md docs/configuration.md` | PASS — no code, test, or generator-owned doc changed; tests/test_docs.py untouched (api-reference.md NOT added to DOCS_FILES) |
| Scoped diff review | PASS — only the two task files across both commits (12 insertions, 6 deletions); pre-existing .planning/ churn never staged, committed, or reverted |

## Decisions Made

- Followed the plan exactly: the pathlib expanduser pattern the finding prescribes at all three DB-open sites, the constructor-type-driven wrapper (Path directly for DatabaseConnection, str() for SearchBackend), and the three-edit ledger closure with no `**Status:**` lines.
- Ledger open count read from execution-time `git show HEAD:<ledger>` (8 — siblings tip, tiq, and tir had already landed) and decremented to 7. Sibling-owned rows (IN-01/CR-01/CR-02, IN-06, IN-10) were not state-asserted, per the shared-ledger rule.
- Collection-registration `~/Documents` literals checked and deliberately left untouched (different API surface); api-reference.md NOT added to tests/test_docs.py's validated set (scope creep avoided).

## Deviations from Plan

None - plan executed exactly as written.

Notes (not deviations):
- The plan's planning-time full-suite baseline said 1528 passed; the execution-time baseline was 1529 passed / 1 skipped (siblings added tests). Observed 1529 passed / 1 skipped / 95.06% matches the execution-time baseline exactly — planning-time vs execution-time counts, no deviation.
- The sandbox gate script additionally runs the OLD raw-tilde form to capture execution-time rc=1 evidence (the plan's described demonstration: "the OLD raw-tilde connect exits rc=1 ... the NEW expanduser form exits rc=0"). This is the plan's stated demonstration, run against a throwaway HOME; the real user DB was never touched.

## Issues Encountered

None. All three fix sites were located at the plan's pinned baseline lines (650, 790, 818) with no drift; the ledger literals matched the gate exactly at execution-time HEAD.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Phase 10 ledger now open 7 / total 22. This was the LAST item in batch 261111-tio (siblings tip/tiq/tir already landed).
- Remaining open findings after this item: WR-07, WR-08 (both need user decisions per STATE.md), IN-02, IN-03, IN-04, IN-05, IN-07.
- No blockers; the documented database examples now open the reader's index on every platform.

---
*Phase: quick-261111-tis*
*Completed: 2026-11-11*

## Self-Check: PASSED

- FOUND: docs/api-reference.md
- FOUND: .planning/milestones/v1.0-phases/10-raise-pytest-coverage-to-90/10-REVIEW-DISPOSITION.md
- FOUND: .planning/quick/261111-tis-close-phase-10-in-09-fix-the-complete-search-example-in-docs/261111-tis-SUMMARY.md
- FOUND commit: 8eb2fc5 (Task 1), eb18aa8 (Task 2) — both ancestors of HEAD
- SUMMARY frontmatter carries `status: complete`; SUMMARY left uncommitted (orchestrator-owned)
