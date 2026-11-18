---
phase: quick-261111-wh8
plan: 01
subsystem: mcp
tags: [sqlite-vec, bm25, hybrid-search, mcp, degradation, fail-fast]

# Dependency graph
requires:
  - phase: quick-261111-wh7
    provides: "serialized ownership of backend.py get_document region and WR-07 ledger closure (shared-file catalog order)"
provides:
  - "MCP SearchBackend.hybrid_search degrades to BM25-only when sqlite-vec is unavailable (construction-time RuntimeError only), with a one-time per-instance warning"
  - "CLAUDE.md Error Handling Conventions records the user-decided MCP-boundary carve-out; core HybridSearcher.search stays fail-fast"
  - "Phase 10 WR-08 closed in 10-REVIEW-DISPOSITION.md (open 1 -> 0 of 22; all other records byte-identical)"
affects: [mcp, search, phase-10-backlog, v1.1-milestone-close]

# Actuals (#2632) — chars/4 over the realized diff (10549 diff chars), not a harness count.
actuals:
  tokens: 2637
  tasks: 3
  commits: 4
plan_head_before: 46be954fe8e3aacfa7f61a1fb557deb235270bdf
plan_head_after: 27c620d4c3b2c605067629396397dc098e58b954

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "construction-only try/except/else at a boundary: catch wraps ONLY SearchPipeline construction; pipeline.search stays in else so search-time errors are never swallowed"
    - "one-time-warning instance flag (_vec_unavailable_warned) mirroring the __init__ embedder-failure posture"

key-files:
  created: []
  modified:
    - src/sif/mcp/backend.py
    - tests/unit/mcp/test_backend.py
    - CLAUDE.md
    - .planning/milestones/v1.0-phases/10-raise-pytest-coverage-to-90/10-REVIEW-DISPOSITION.md

key-decisions:
  - "USER DECISION (locked, not re-litigated): degrade to BM25-only at the MCP boundary when sqlite-vec is missing; core HybridSearcher.search fail-fast contract unchanged (hybrid.py/vector.py byte-identical)"
  - "Catch is construction-only: pipeline.search lives in the else clause, so rerank/embedder search-time RuntimeErrors still propagate through the MCP boundary"
  - "Fallback is direct BM25Searcher(conn).search(query, options) with the query passed through unchanged (no lex:/vec:/hyde: prefix routing — that is a SearchPipeline feature); shared boundary mapping and _with_suggestions return reused byte-identical"
  - "Warning fires once per SearchBackend instance via _vec_unavailable_warned (set True before logging); benign check-then-set race under to_thread can at worst duplicate a warning, never corrupt results — no lock"

patterns-established:
  - "Boundary carve-outs are documented in CLAUDE.md Error Handling Conventions as explicit exceptions to the core fail-fast rule (user-authorized)"
  - "Shared-ledger closure: open count read from execution-time git show HEAD:<ledger> and decremented dynamically; byte-equality three-edit reconstruction gate proves no unrelated record changed"

requirements-completed: [PHASE10-WR-08]

coverage:
  - id: D1
    description: "hybrid_search degrades to real BM25 results (doc_ids {d1,d2}, mapped rank/collection_name/vectors_stale metadata) when SearchPipeline construction raises the sqlite-vec RuntimeError"
    requirement: "PHASE10-WR-08"
    verification:
      - kind: unit
        ref: "tests/unit/mcp/test_backend.py#TestHybridSearchVecDegradation::test_vec_unavailable_degrades_to_bm25_results"
        status: pass
    human_judgment: false
  - id: D2
    description: "Degradation warning containing 'sqlite-vec' is emitted exactly once per SearchBackend instance across repeated degraded queries; both queries return results"
    requirement: "PHASE10-WR-08"
    verification:
      - kind: unit
        ref: "tests/unit/mcp/test_backend.py#TestHybridSearchVecDegradation::test_vec_unavailable_warning_emitted_once"
        status: pass
    human_judgment: false
  - id: D3
    description: "Core fail-fast preserved: search-time RuntimeError from pipeline.search still propagates; hybrid.py and vector.py byte-identical to execution-time HEAD"
    requirement: "PHASE10-WR-08"
    verification:
      - kind: unit
        ref: "tests/unit/mcp/test_backend.py#TestHybridSearchVecDegradation::test_search_time_runtime_error_still_propagates"
        status: pass
      - kind: other
        ref: "git diff --exit-code -- src/sif/search/hybrid.py src/sif/search/vector.py"
        status: pass
    human_judgment: false
  - id: D4
    description: "CLAUDE.md Error Handling Conventions carries exactly one new carve-out bullet; all other CLAUDE.md bytes unchanged"
    verification:
      - kind: other
        ref: "grep -c 'degrades to BM25-only' / 'remains fail-fast' / 'SearchBackend' CLAUDE.md == 1 each; scoped diff shows single-bullet insertion"
        status: pass
    human_judgment: false
  - id: D5
    description: "WR-08 alone fixed in the Phase 10 disposition ledger; open count 1 -> 0 (total 22); every other record byte-identical including sibling closures"
    verification:
      - kind: other
        ref: "python -I exact three-edit reconstruction gate vs execution-time git show HEAD:<ledger> -> 'WR-08-fixed; open 1->0; all-other-ledger-content-byte-identical'"
        status: pass
    human_judgment: false

# Metrics
duration: 13min
completed: 2026-11-11
status: complete
---

# Quick 261111-wh8: Close Phase 10 WR-08 Summary

**MCP hybrid_search now degrades to real BM25-only results with a one-time sqlite-vec warning when SearchPipeline construction fails, while the core HybridSearcher.search fail-fast contract stays byte-identical — user-decided boundary carve-out recorded in CLAUDE.md and WR-08 closed (ledger open 1 -> 0 of 22).**

## Performance

- **Duration:** 13 min
- **Started:** 2026-11-11T16:12:32Z
- **Completed:** 2026-11-11T16:25:30Z
- **Tasks:** 3
- **Files modified:** 4

## Closed Finding

**Phase 10 WR-08** (10-REVIEW.md:134-138): `SearchPipeline` -> `HybridSearcher` -> `VectorSearcher` is constructed per request inside `hybrid_search`; `VectorSearcher.__init__` raises `RuntimeError("sqlite-vec extension is not available. Install sqlite-vec to use vector search.")` when the extension is missing (vector.py:21-24) — so every MCP `query` tool call failed on machines without sqlite-vec while the same machine's CLI BM25 search worked.

**User decision (locked):** degrade to BM25-only at the MCP boundary, warn once, keep the core search API fail-fast. Live grounding at planning HEAD c8a234b: SearchPipeline construction at backend.py:155-159, `pipeline.search` at :160; re-verified at execution HEAD 46be954 (line numbers held; sibling wh7 had already shifted get_document/tests).

## Accomplishments

- **Construction-only degradation:** `_search` now wraps ONLY the `SearchPipeline(...)` construction in `try`; `except RuntimeError` warns once and assigns `core_results = BM25Searcher(conn).search(query, options)`; `pipeline.search(query, options)` moved into the `else` clause so search-time RuntimeErrors (rerank failure, vec:/hyde: embedder guards) are NEVER swallowed. The collections resolution, boundary mapping comprehension, and `_with_suggestions` return are byte-identical and shared by both paths — BM25Searcher already calls `_attach_contexts` (path contexts + mark_vector_staleness), so fallback rows carry every mapped field (rank, collection_name, vectors_stale).
- **One-time warning:** `self._vec_unavailable_warned = False` in `__init__` (next to `self._embedder`); handler sets it True before `logger.warning("sqlite-vec unavailable; MCP hybrid search degrades to BM25-only")` — instance-scoped, mirroring the `__init__` embedder-failure warning posture; deterministically testable with a fresh backend per test.
- **Three regression tests** appended as `TestHybridSearchVecDegradation` at the END of test_backend.py (wh7's get_document tests untouched): real seeded production-DDL DB via `_seed_suggestion_db`/`_suggestion_backend`, SearchPipeline patched to raise the real vector.py message, BM25Searcher NOT patched (real rows {d1, d2} against the seeded 'notes' collection).
- **CLAUDE.md carve-out:** exactly one new Error Handling Conventions bullet (user-authorized edit) recording the MCP `SearchBackend` boundary degradation with one-time warning; the core fail-fast bullet and every other byte unchanged.
- **Ledger closure:** WR-08 YAML disposition open -> fixed, markdown row names quick 261111-wh8 and the user decision, `open:` decremented from the execution-time HEAD value 1 -> 0 (total 22, recorded timestamp unchanged). Exact three-edit byte-equality reconstruction against `git show HEAD:<ledger>` proved every other record — including sibling closures WR-07 (wh7), IN-05 (wh9), IN-07 (wha) and the earlier v4x closures — byte-identical.

## TDD Evidence (RED -> GREEN)

- **RED (commit d6d4118, tests only):** `python -m pytest tests/unit/mcp/test_backend.py -q --no-cov --junitxml=red-report.xml` at HEAD 46be954 + new tests -> exit 1, **2 failed, 31 passed**. Both degradation tests failed on the genuine `RuntimeError: sqlite-vec extension is not available...` propagating out of `hybrid_search` through the SearchPipeline construction seam (backend.py:155) — never a collection/setup/patch-target error. The preservation pin (search-time propagation) passed at HEAD by design. Machine-validated: `gsd_run check tdd-red-evidence` returned **RED_EVIDENCE_OK** for both targets (records + JUnit report + console kept in this directory: `red-evidence-*.json`, `red-report.xml`, `red-console.txt`). Semantic assessment: targets executed and failed on the planned behavior because HEAD had no construction-time catch.
- **GREEN (commit a768a75):** after the production edit, **33 passed** (30 pre-existing incl. wh7's three + 3 new). Degraded queries return real BM25 rows {d1, d2} with full metadata; exactly one WARNING containing "sqlite-vec" across two degraded calls on the same backend; search-time RuntimeError still propagates.
- **REFACTOR:** none needed beyond the E501 formatting fixes recorded below (minimal plan-shaped edit; `_search` complexity well under limits, no helper extraction, no noqa added).

## Task Commits

1. **Task 1 RED: sqlite-vec degradation regression tests** - `d6d4118` (test)
2. **Task 1 GREEN: MCP-boundary BM25 degradation + one-time warning** - `a768a75` (fix)
3. **Task 2: CLAUDE.md Error Handling carve-out bullet** - `2bbc332` (docs)
4. **Task 3: WR-08 ledger closure (open 1 -> 0)** - `27c620d` (docs)

Plan metadata (SUMMARY/STATE): handled by the batch orchestrator — intentionally NOT committed here.

## Files Created/Modified

- `src/sif/mcp/backend.py` - BM25Searcher import; `_vec_unavailable_warned` flag; construction-only try/except/else in `hybrid_search._search`; docstring sentence + WR-08 comment. get_document and every other method byte-identical.
- `tests/unit/mcp/test_backend.py` - `import logging`, `from sif.mcp import backend as backend_module`, `_VEC_MISSING_MSG` constant, appended `TestHybridSearchVecDegradation` (3 tests). 66 insertions, 0 deletions — no existing test touched.
- `CLAUDE.md` - one new Error Handling Conventions bullet (single-line insertion).
- `.planning/milestones/v1.0-phases/10-raise-pytest-coverage-to-90/10-REVIEW-DISPOSITION.md` - exactly three scoped edits (YAML disposition, open count, markdown row).

## Decisions Made

- Followed the locked user decision exactly; no re-litigation. Implementation decisions are the plan's pins: construction-only catch, else-clause search, direct BM25Searcher fallback without prefix routing, instance-flag one-time warning without a lock.
- Mirrored sibling wh7's commit convention: separate RED (test) and GREEN (fix) commits for the TDD task, then per-task docs commits.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] E501 line-length violations (101 > 100) tripped the Task 1 ruff gate**
- **Found during:** Task 1 GREEN verification
- **Issue:** the single-line `logger.warning(...)` call (backend.py) and the inline sqlite-vec message string in the warning-once test (test_backend.py, deeper nesting indent) each measured 101 chars.
- **Fix:** wrapped the `logger.warning` call across lines (exact message preserved, one call site); hoisted the duplicated test message into module-level `_VEC_MISSING_MSG` used by both degradation tests (exact real vector.py message preserved).
- **Files modified:** src/sif/mcp/backend.py, tests/unit/mcp/test_backend.py
- **Verification:** ruff check + ruff format --check clean; 33 tests still pass; grep gates (message count = 1, flag count >= 2, BM25Searcher count >= 2) hold.
- **Committed in:** a768a75 (GREEN task commit)

### Anticipated Baseline Adjustments (not deviations)

- The plan's planning-time baseline (HEAD c8a234b) was 27 tests in test_backend.py; at execution HEAD 46be954 sibling wh7 had already merged its 3 get_document tests, so the live baseline was 30 and GREEN is 33 (the plan's +3 delta holds; the plan explicitly mandates live re-verification and forbids exact suite totals). Full suite: 1545 passed / 1 skipped (planning baseline 1531 + sibling additions + this item's 3).
- Ledger open count read dynamically from execution-time HEAD: 1 -> 0 (planning-time value was 4; siblings wh7/wh9/wha closed theirs first, exactly as the shared-ledger rule anticipated).

---

**Total deviations:** 1 auto-fixed (Rule 3 formatting gate). **Impact:** none on behavior or scope; message text and catch shape exactly as pinned.

## Issues Encountered

- RED-evidence classifier first rejected the records (`invalid_record`): console text concatenated into `output` broke whole-document XML parsing, and bare method names did not match the JUnit qualified names. Rebuilt records with the pure JUnit XML in `output`, console in a separate field, and fully-qualified `tests.unit.mcp.test_backend.TestHybridSearchVecDegradation#<method>` targets -> RED_EVIDENCE_OK for both. The underlying RED run was never altered.

## Quality Gates (all green, PATH miniconda python)

1. `python -m pytest tests/unit/mcp/test_backend.py -q --no-cov` -> 33 passed
2. `ruff check src tests` -> All checks passed
3. `ruff format --check src tests` -> 188 files already formatted
4. `ty check src/sif` -> All checks passed
5. `python -m pytest` (full, coverage on) -> **1545 passed, 1 skipped, 95.06% cov** (fail_under=90 satisfied)
6. `git diff --exit-code -- src/sif/search/hybrid.py src/sif/search/vector.py docs/cli-reference.md docs/configuration.md` -> clean (core fail-fast files and generator-owned docs untouched)
7. Scoped diff review: only the four files_modified paths changed across 46be954..27c620d; backend.py delta = import + flag + try/except/else + docstring/comment; test file additive-only (66/0); CLAUDE.md single bullet; ledger three edits (reconstruction-proven). Pre-existing `.planning/` churn never staged; coverage artifacts (htmlcov/, coverage.xml, .coverage) gitignored.

## Sibling Boundaries (batch 261111-wh6)

- **wh7 (WR-07):** owns backend.py get_document (~188-232) and its tests — fenced off, byte-identical here; its ledger closure preserved.
- **wh9 (IN-05) / wha (IN-07):** ledger-only overlap — their closures preserved byte-for-byte by the reconstruction gate. This item is the batch's last; the Phase 10 ledger is now **0/22 open**.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Phase 10 review backlog fully closed (0/22 open) — v1.1 milestone audit/close (`/gsd-complete-milestone v1.1`) is unblocked from the review-ledger side.
- Orchestrator owns STATE.md/ROADMAP.md/BATCH.json updates and the planning-artifacts commit.

---
*Phase: quick-261111-wh8*
*Completed: 2026-11-11*

## Self-Check: PASSED

- All 4 modified files + SUMMARY.md exist on disk (FOUND x5).
- All 4 task commits (d6d4118, a768a75, 2bbc332, 27c620d) are ancestors of HEAD; measured `git rev-list --count 46be954..HEAD` = 4, matching frontmatter `actuals.commits`.
- Working tree carries only the pre-existing `.planning/` churn (STATE.md, config.json modified; untracked planning artifacts) — nothing task-scoped left uncommitted; SUMMARY/evidence intentionally uncommitted for the orchestrator.