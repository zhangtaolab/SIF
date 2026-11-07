---
phase: 10-raise-pytest-coverage-to-90
plan: 06
subsystem: testing
tags: [pytest, coverage, indexing, mcp, parser]

requires:
  - phase: 10-raise-pytest-coverage-to-90
    plan: 01
    provides: Post-deletion coverage baseline and isolation conventions.
provides:
  - Real-file parser/scanner and exact-boundary chunker behavioral coverage.
  - In-memory MCP server, HTTP, stdio, and handler behavioral coverage with isolated sessions.
  - Regression fixes for chunker forward progress and bounded MCP session registries.
affects:
  - Phase 10 plan 10-07 coverage tollgate.
  - Fixed-size and section-subdivision chunk boundaries for excessive overlap configurations.
  - HTTP MCP process-global session count enforcement.

actuals:
  tokens: 12266
  tasks: 3
  commits: 3
plan_head_before: bf60e985c63e4ce76658420fc2597b451f74837c
plan_head_after: 5bbdacdfcf026d0520b01ae62ed5911e72af71

tech-stack:
  added: []
  patterns: [real Unicode file parsing, MCP session fixtures]

key-files:
  created:
    - tests/unit/indexing/test_parser.py
    - tests/unit/indexing/test_scanner.py
    - tests/unit/indexing/test_chunker.py
    - tests/unit/mcp/test_server.py
  modified:
    - src/sif/indexing/chunker.py
    - src/sif/mcp/transports/http.py
    - tests/unit/mcp/test_transports_http.py
    - tests/unit/mcp/test_transports_stdio.py
    - tests/unit/mcp/test_integration.py

key-decisions:
  - "Preserve decoded Unicode code points and Python string offsets; no normalization, grapheme, or UTF-8 byte semantics were introduced."
  - "Enforce fixed-size forward progress and stop before reprocessing a suffix already wholly covered; subdivide oversized sections with zero overlap to guarantee termination."
  - "Evict MCP sessions after insertion so the configured maximum is enforced, and clear global sessions around every HTTP/integration test."

patterns-established:
  - "Assert chunk content, sequence, and offsets independently of generated entity identities."
  - "Use direct async protocol helpers and FastAPI TestClient with mocked uvicorn; never bind a socket."

requirements-completed: [T-10-1]

coverage:
  - id: D1
    description: Markdown/Text/Code parsers and FileScanner execute against real temporary files, including empty and CJK/Unicode inputs.
    requirement: T-10-1
    verification:
      - kind: integration
        ref: "tests/unit/indexing/test_parser.py + test_scanner.py: 25 passed; tracer gates rerun before expansion"
        status: pass
      - kind: other
        ref: ".planning/tmp/10-06-parser.xml and 10-06-scanner.xml: both line-rate=1; full suite 100%"
        status: pass
    human_judgment: false
  - id: D2
    description: Every concrete chunker and factory branch asserts content, sequence, and Python code-point boundaries, including oversize/fallback paths.
    requirement: T-10-1
    verification:
      - kind: integration
        ref: "tests/unit/indexing/test_chunker.py: 23 passed; excessive-overlap and subdivision termination asserted"
        status: pass
      - kind: other
        ref: ".planning/tmp/10-06-chunker.xml line-rate=0.9899; threshold >= 0.85"
        status: pass
    human_judgment: false
  - id: D3
    description: MCP dispatch/resources/notifications, HTTP session/error/SSE/run paths, stdio, and handlers run in memory with mocked external transports.
    requirement: T-10-1
    verification:
      - kind: integration
        ref: "tests/unit/mcp: 77 passed; no listeners/subprocesses; autouse session setup/teardown"
        status: pass
      - kind: other
        ref: ".planning/tmp/10-06-server.xml line-rate=0.9610 and 10-06-http.xml line-rate=0.9386; full suite server/stdio 100%, handlers 98%"
        status: pass
    human_judgment: false
  - id: D4
    description: The full quality suite remains green and total coverage improves without coverage configuration changes.
    requirement: T-10-1
    verification:
      - kind: other
        ref: "ruff check src tests; ruff format --check src tests: PASS (150 files)"
        status: pass
      - kind: integration
        ref: "env -u FORCE_COLOR NO_COLOR=1 pytest --cov=src/sif: 958 passed, 0 failed; .planning/tmp/10-06-full.xml TOTAL line-rate=0.9616"
        status: pass
    human_judgment: false

duration: 20min
completed: 2026-11-05
status: complete
---

# Phase 10 Plan 06: Indexing and MCP Coverage Summary

**Raised full-suite coverage from 93.48% to 96.16% with 83 new behavior tests, reached 100% parser/scanner/server/stdio coverage, and fixed chunker non-termination plus MCP session-limit defects exposed by the new edge cases.**

## Performance

- **Duration:** 20 minutes (1,177 seconds)
- **Started:** 2026-11-05T19:54:09Z
- **Completed:** 2026-11-05T20:13:46Z
- **Tasks:** 3/3
- **Files modified:** 7 test files plus 2 production modules (9 code/test files), plus planning state.
- **Realized code/test diff:** 49,065 characters (12,266 chars/4 actual tokens); 1,070 insertions and 11 deletions.
- **Full suite:** 958 passed, 0 failed in 10.65 seconds.

## Accomplishments

- Added 20 parser tests through real `tmp_path` files, including exact CJK/Unicode content, byte-based SHA-256, metadata/title precedence, malformed frontmatter fallback, language mappings, and factory behavior.
- Added 5 scanner tests using only synthetic temporary trees for nested discovery, ignore globs, non-files, outside-root behavior, defaults, and size/extension statistics.
- Added 23 chunker tests for exact content, sequence, code-point offsets, overlap, whitespace, Unicode, heading/code boundaries, subdivision, auto routing, and every factory branch.
- Added 16 server branch tests for lifecycle, dispatch, schema conversion, tool failures, resources, and all notification branches.
- Expanded HTTP, stdio, and integration suites by 39 tests for session LRU behavior, protocol errors, SSE, startup composition, cancellation, and handler payload serialization.
- Reran the tracer verification end-to-end before expansion; parser/scanner both passed at 100%.
- Repaired fixed-size chunker progress and MCP session bounds, then passed all focused thresholds and the complete quality suite.

## Measured Coverage Movement

| File | 10-05 full suite | 10-06 full suite | Missed change |
|---|---:|---:|---:|
| `src/sif/indexing/parser.py` | 51% (38 missed / 78) | **100%** (0 missed / 78) | -38 |
| `src/sif/indexing/scanner.py` | 73% (13 missed / 48) | **100%** (0 missed / 48) | -13 |
| `src/sif/indexing/chunker.py` | 71% (28 missed / 98) | **98.99%** (1 missed / 99) | -27 |
| `src/sif/mcp/server.py` | 71% (22 missed / 77) | **100%** (0 missed / 77) | -22 |
| `src/sif/mcp/transports/http.py` | 77% (26 missed / 114) | **93.86%** (7 missed / 114) | -19 |
| `src/sif/mcp/transports/stdio.py` | 84% (13 missed / 81) | **100%** (0 missed / 81) | -13 |
| `src/sif/mcp/handlers.py` | 77% (12 missed / 53) | **98.11%** (1 missed / 53) | -11 |
| **TOTAL** | **93.48%** (348 missed / 5340) | **96.16%** (205 missed / 5341) | **-143** |

The canonical XML records 5,341 valid lines, 5,136 covered lines, and `line-rate=0.9616`; terminal output displays TOTAL as 96%. Focused gates measured parser/scanner at 100%, chunker at 98.99%, server at 96.10%, and HTTP at 93.86%; full-suite server coverage reached 100% through the additional integration flows. The remaining HTTP lines are the optional-import fallback; chunker's remaining line is the abstract method body.

## Task Commits

1. **Task 1: Prove real-file parsing and expand scanner/factory edge behavior** — `4fc7e44` (test)
2. **Task 2: Exercise chunker boundaries and every factory branch** — `f39c0e9` (test, including a narrow production progress repair)
3. **Task 3: Cover MCP server and transport/handler branches without listeners** — `5bbdacd` (test, including a narrow production session-bound repair)

## Files Created/Modified

- `tests/unit/indexing/test_parser.py` — real Unicode/Markdown/Text/Code parsing and factory selection.
- `tests/unit/indexing/test_scanner.py` — temporary-tree discovery, ignores, defaults, and statistics.
- `tests/unit/indexing/test_chunker.py` — exact chunk boundaries and factory/strategy behavior without identity comparisons.
- `src/sif/indexing/chunker.py` — guarantees start-position progress, avoids redundant suffix chunks, and terminates small-section subdivision.
- `tests/unit/mcp/test_server.py` — lifecycle, dispatch, resource, and notification behavior with async backend doubles.
- `tests/unit/mcp/test_transports_http.py` — global-session cleanup plus session/error/SSE/CORS/startup branches.
- `src/sif/mcp/transports/http.py` — enforces `SESSION_MAX_COUNT` after new-session insertion.
- `tests/unit/mcp/test_transports_stdio.py` — malformed notifications, cancellation/error handling, and mocked composition.
- `tests/unit/mcp/test_integration.py` — handler payload/error behavior and global HTTP session cleanup.

## Decisions Made

- Treated Unicode parsing as decoded Python strings with exact code-point equality; SHA-256 remains based on the original UTF-8 bytes.
- Treated chunk offsets as Python string/code-point positions, not UTF-8 bytes or grapheme clusters.
- Compared delegated chunker results through content, sequence, and offsets rather than random entity IDs.
- Used non-overlapping subdivision for oversized Markdown/code sections so small configured sizes cannot produce one-character sliding windows or loops.
- Kept all network entry points mocked and restored the process-global MCP session registry in setup and teardown.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Guaranteed chunker forward progress and bounded suffix processing**
- **Found during:** Task 2.
- **Issue:** `FixedSizeChunker` could restart at the same position when overlap exceeded chunk size, and small-section subdivision used a default overlap of 100, causing non-termination or one-character sliding windows.
- **Fix:** Force start-position advancement, stop when the final window already covers the remaining suffix, and use zero overlap for oversized-section subdivision.
- **Files modified:** `src/sif/indexing/chunker.py`, `tests/unit/indexing/test_chunker.py`.
- **Verification:** Exact-fit, ordinary overlap, excessive overlap, Unicode, Markdown oversize, and code oversize tests all terminate with asserted content/boundaries; 23 focused tests and the full suite pass.
- **Commit:** `f39c0e9`.

**2. [Rule 1 - Bug] Enforced MCP session limit after insertion**
- **Found during:** Task 3.
- **Issue:** Eviction ran before insertion using `len(_sessions) > SESSION_MAX_COUNT`, allowing a new session to leave the registry above its configured bound.
- **Fix:** Create/reuse the session first, then evict least-recently-used entries until the registry is within the configured maximum.
- **Files modified:** `src/sif/mcp/transports/http.py`, `tests/unit/mcp/test_transports_http.py`.
- **Verification:** The small-limit regression asserts reuse, timestamps, LRU eviction, and a final one-entry registry; all 77 MCP tests and the full suite pass.
- **Commit:** `5bbdacd`.

**Total deviations:** 2 auto-fixed production behavior defects.
**Impact on plan:** Both repairs were necessary to complete the required edge coverage safely. No API redesign, coverage suppression, dependencies, real listeners, or architectural changes were introduced.

## Issues Encountered

- The full suite emitted 57 warnings, predominantly existing SQLite `ResourceWarning` messages; they did not fail the suite and were outside this plan's scope.
- No authentication gates, package installs, blockers, known stubs, skipped tests, unrun verification commands, generator-owned doc edits, or user setup occurred.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

The next measured starting point is **96.16% (205 missed / 5341 statements)** with **958 passing tests**. All focused thresholds passed: parser/scanner 100%, chunker 98.99%, server 96.10% focused and 100% full-suite, HTTP 93.86%. `requirements.ready-ids` returned `ready: []`; `T-10-1` remains unmarked because the seven-plan shared-ID gate has not released it. `pyproject.toml` remains untouched and the permanent `fail_under=90` gate remains reserved for plan 10-07.

## Self-Check: PASSED

- Required classes and files exist: `TestDocumentParsers`, `TestFileScanner`, `TestChunkerStrategies`, `TestMCPServerBranches`, and `TestHTTPTransportBranches`.
- Task commits `4fc7e44`, `f39c0e9`, and `5bbdacd` are ancestors of HEAD; the measured ledger records exactly 3 commits from `bf60e98` through `5bbdacd`.
- The automatic tracer feedback gate reran parser/scanner behavior and both focused coverage gates before expansion: PASS.
- Task acceptance checks: parser/scanner 25 passed; chunker 23 passed; MCP 77 passed; all focused XML thresholds passed.
- `ruff check src tests`: PASS; `ruff format --check src tests`: PASS (150 files).
- Canonical `env -u FORCE_COLOR NO_COLOR=1 pytest --cov=src/sif`: PASS (958 passed, 0 failed; TOTAL 96.16%).
- `pyproject.toml` unchanged; no business-logic pragmas, coverage exclusions, generator-owned doc edits, dependencies, real trees, listeners, or subprocesses were added.
- Requirement readiness returned `ready: []`; `T-10-1` was not prematurely marked complete.

---
*Phase: 10-raise-pytest-coverage-to-90*
*Completed: 2026-11-05*
