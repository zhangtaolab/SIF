---
phase: 10-raise-pytest-coverage-to-90
plan: 03
subsystem: testing
tags: [pytest, coverage, rerank, search, mocked-ml]

requires:
  - phase: 10-raise-pytest-coverage-to-90
    plan: 01
    provides: Post-deletion coverage baseline and Wave-2 rerank/search gaps.
provides:
  - Deterministic Qwen3 yes/no scoring and CrossEncoder/factory behavior coverage.
  - Search CLI machine-format, diagnostic, missing-index, and error coverage.
  - XML escaping for query attributes and result fields.
affects:
  - Phase 10 plan 10-07 coverage tollgate.
  - Search CLI XML machine-output consumers.

actuals:
  tokens: 12161
  tasks: 2
  commits: 2
plan_head_before: 556a8badbf61b4edc042ca14d44a7b7f1282489e
plan_head_after: 788ca42

tech-stack:
  added: []
  patterns: [mocked ML lazy-import patching (Pattern 3)]

key-files:
  created: []
  modified:
    - tests/unit/inference/test_reranker.py
    - tests/unit/search/test_rerank.py
    - tests/unit/cli/test_search.py
    - src/sif/cli/commands/search.py

key-decisions:
  - "Use real torch tensor math with constructor/downloader mocks for deterministic Qwen3 yes/no scoring; scope ML module injection under D-07."
  - "Escape XML query attributes and result fields so machine output strict-parses markup-sensitive content."

patterns-established:
  - "Pattern 3: fake tokenizers and real tensors preserve Qwen3 indexing, softmax, result construction, batching, and sorting while model constructors and downloads stay patched."

requirements-completed: [T-10-1]

coverage:
  - id: D1
    description: Qwen3 local and mocked-download loading, real yes/no softmax scoring, result ordering, prompt composition, batching, top_k, CrossEncoder branches, and factory dispatch.
    requirement: T-10-1
    verification:
      - kind: unit
        ref: "tests/unit/inference/test_reranker.py#TestQwen3Reranker and #TestCreateReranker; tests/unit/search/test_rerank.py#TestRerankerBehavior (50 passed)"
        status: pass
      - kind: other
        ref: ".planning/tmp/10-03-rerank.xml search/rerank.py line-rate=0.9860; focused threshold >= 0.80"
        status: pass
    human_judgment: false
  - id: D2
    description: Search CLI JSON, CSV, Markdown, XML, files, explain, min-score boundary, line numbers, CJK/empty inputs, quiet/missing-index, vector output, and ClickException paths.
    requirement: T-10-1
    verification:
      - kind: integration
        ref: "tests/unit/cli/test_search.py#TestSearchOutputBranches (64 passed in file)"
        status: pass
      - kind: other
        ref: ".planning/tmp/10-03-search.xml cli/commands/search.py line-rate=0.9916; focused threshold >= 0.88"
        status: pass
    human_judgment: false
  - id: D3
    description: XML output escapes markup-sensitive query attributes and result text without changing parsed content.
    requirement: T-10-1
    verification:
      - kind: integration
        ref: "TestSearchOutputBranches.test_xml_escapes_markup_sensitive_text for search and query commands"
        status: pass
      - kind: integration
        ref: "env -u FORCE_COLOR NO_COLOR=1 pytest --cov=src/sif (764 passed, 0 failed; TOTAL 88.57%)"
        status: pass
    human_judgment: false

duration: 19min
completed: 2026-11-05
status: complete
---

# Phase 10 Plan 03: Reranker and Search Command Coverage Summary

**Raised full-suite line coverage from 85.34% to 88.57% with deterministic reranker tests and 64 search CLI tests; rerank.py reached 98.60%, search.py 99.44%, and XML now safely escapes machine output.**

## Performance

- **Duration:** 19 minutes (1,164 seconds)
- **Started:** 2026-11-05T18:29:38Z
- **Completed:** 2026-11-05T18:49:02Z
- **Tasks:** 2/2
- **Files modified:** 3 test modules and 1 production module, plus planning state.
- **Realized code/test diff:** 48,643 characters (12,161 chars/4 actual tokens).
- **Full suite:** 764 passed, 0 failed.

## Accomplishments

- Added `TestQwen3Reranker` with a local `tmp_path` model, mocked transformer constructors and downloader, real torch yes/no indexing and softmax, ordered `SearchResult` assertions, and `top_k` verification.
- Covered quiet/nonquiet loading, already-loaded no-op, explicit/automatic devices, prompt formatting, content/highlight/title composition, empty results, and per-batch scoring.
- Expanded CrossEncoder loading, scoring, download fallback, metadata preservation, and all `create_reranker` dispatch/cache-dir branches.
- Removed the reranker test module's permanent `sys.modules` injections in favor of scoped patches, satisfying D-07 isolation.
- Added `TestSearchOutputBranches` covering all registered machine formats, CJK and empty queries/results, score traces, explain, exact min-score propagation, line numbers, quiet behavior, missing indexes, collection filtering, model overrides, and clean errors.
- Fixed XML output so query attributes, titles, paths, collections, and line-number text are escaped and strict-parse without content changes.
- Passed the automatic tracer gate by rerunning both reranker verification commands before starting CLI expansion.

## Measured Coverage Movement

| File | 10-01 baseline | 10-03 full suite | Missed change |
|---|---:|---:|---:|
| `src/sif/search/rerank.py` | 62% (82 missed / 214) | **98.60%** (3 missed / 214) | -79 |
| `src/sif/cli/commands/search.py` | 79% (76 missed / 356) | **99.44%** (2 missed / 357) | -74 |
| **TOTAL** | 85.34% after 10-02 (780 missed / 5320) | **88.57%** (608 missed / 5321) | **-172** |

The search denominator increased by one statement because XML field escaping was added. Focused gates independently measured rerank at **98.60%** and search at **99.16%**, exceeding the required 80% and 88%. The canonical full-suite XML records `line-rate=0.8857`, 5,321 statements, 4,713 covered lines, and 608 missed lines; the terminal displays TOTAL as 89%.

## Task Commits

1. **Task 1: Qwen3 load-to-ranked-results and reranker/factory behavior** — `d0efd6a` (test)
2. **Task 2: Search command output, diagnostics, and XML escaping** — `788ca42` (test)

## Files Created/Modified

- `tests/unit/inference/test_reranker.py` — deterministic Qwen3 fixtures/tests, expanded CrossEncoder/factory behavior, and scoped ML module mocks.
- `tests/unit/search/test_rerank.py` — real CrossEncoder/LlamaCpp score construction and content selection assertions.
- `tests/unit/cli/test_search.py` — 34 additional output/diagnostic/error tests plus scoped quiet-state isolation.
- `src/sif/cli/commands/search.py` — XML attribute and text escaping using the standard library.
- `.planning/phases/10-raise-pytest-coverage-to-90/10-03-SUMMARY.md` — measured execution record.

## Decisions Made

- Used real torch operations rather than replacing the target softmax/indexing algorithm; only external model constructors, model inference, and downloads were mocked.
- Restored optional ML modules with `patch.dict` contexts and reset CLI quiet state around the new CLI class; tests touching the Settings cache clear it in `finally`.
- Fixed the existing XML escaping bug because the plan explicitly requires parseable XML with markup-sensitive fixtures; no output contract was relaxed.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Escaped XML-sensitive query and result fields**
- **Found during:** Task 2.
- **Issue:** `format_results_xml` interpolated raw query attributes and result text, so the required CJK/markup-sensitive XML test could not parse.
- **Fix:** Used `xml.sax.saxutils.quoteattr` for the query and `xml_escape` for result text and line numbers.
- **Files modified:** `src/sif/cli/commands/search.py`, `tests/unit/cli/test_search.py`.
- **Verification:** Both search/query XML tests strict-parse and round-trip original values; full suite passed.
- **Commit:** `788ca42`.

**2. [Rule 1 - Incorrect test fixture] Consumed Qwen3 logits per batch**
- **Found during:** Task 1.
- **Issue:** The initial fake model returned the entire two-row logits fixture on each batch, yielding four scores for two inputs.
- **Fix:** Made the tokenizer pin one deterministic logits slice per call; retained real softmax and sorting.
- **Files modified:** `tests/unit/inference/test_reranker.py`.
- **Verification:** 50 focused reranker tests passed; coverage gate and tracer rerun passed.
- **Commit:** `d0efd6a`.

**3. [Rule 3 - Blocking test scaffolding] Corrected lazy-import patch sites and Rich width assertions**
- **Found during:** Task 2.
- **Issue:** `vsearch_cmd` imports database/repository classes at call time, while the initial helper patched only the consumer module; long-word table assertions also assumed Rich would preserve literal ellipsis placement.
- **Fix:** Patched the actual source-module lookup sites and asserted retained title text plus visible content truncation. Passed injected Settings errors through the helper instead of overriding them.
- **Files modified:** `tests/unit/cli/test_search.py`.
- **Verification:** 64 search tests passed; focused coverage gate and full suite passed.
- **Commit:** `788ca42`.

**Total deviations:** 3 auto-fixed (one production output bug, two new-test corrections).
**Impact on plan:** XML output integrity improved; no production search/rerank algorithm changed, no coverage suppression or dependency was introduced.

## Issues Encountered

- The full suite emitted 71 existing `ResourceWarning` messages about unclosed SQLite connections; these did not fail tests and are outside this plan's scope.
- No authentication gates, package installs, blockers, stubs, skipped tests, unrun verification commands, or user setup occurred.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

The next measured starting point is **88.57% (608 missed / 5321 statements)** with **764 passing tests**. Rerank and search exceed their focused thresholds without network/model downloads. `T-10-1` remains unmarked because the shared-ID gate returned `ready: []`; no coverage fail-under or exclusion configuration was added.

## Self-Check: PASSED

- Required classes exist in `tests/unit/inference/test_reranker.py`, `tests/unit/search/test_rerank.py`, and `tests/unit/cli/test_search.py`.
- Task commits `d0efd6a` and `788ca42` are ancestors of HEAD; the measured ledger records exactly 2 plan commits from `556a8ba` through `788ca42`.
- Focused reranker tests: 50 passed; `rerank.py` 98.60% >= 80%; automatic tracer rerun: PASS.
- Focused search tests: 64 passed; `search.py` 99.16% >= 88%; CJK, empty, explain, min-score, line-number, missing-index, and error assertions: PASS.
- `ruff check src tests`: PASS. `ruff format --check src tests`: PASS (132 files).
- Canonical `env -u FORCE_COLOR NO_COLOR=1 pytest --cov=src/sif`: PASS (764 passed, 0 failed; TOTAL 88.57%).
- `pyproject.toml` unchanged; no business-logic pragmas, coverage exclusions, generator-owned doc edits, or new dependencies.
- Requirement readiness returned `ready: []`; `T-10-1` was not prematurely marked complete.

---
*Phase: 10-raise-pytest-coverage-to-90*
*Completed: 2026-11-05*
