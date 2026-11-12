---
phase: quick-261111-rqs
plan: 01
subsystem: search/cli
status: complete
tags: [wr-01, vec0, sqlite-vec, collection-remove, embedding-purge, shared-helper, tdd]
requires: []
provides:
  - "create_embedding_purger shared construction point (src/sif/search/vector.py)"
  - "collection remove purges vec0 embeddings before document delete"
affects:
  - src/sif/search/vector.py
  - src/sif/indexing/incremental.py
  - src/sif/cli/commands/collection.py
  - tests/unit/cli/test_collection.py
  - .planning/milestones/v1.0-phases/10-raise-pytest-coverage-to-90/10-REVIEW-DISPOSITION.md
tech-stack:
  added: []
  patterns:
    - "Public factory in the owning layer (create_* convention) with lazy function-local imports at consumers"
    - "vec0 purge BEFORE relational delete inside one db.transaction() (mirrors _remove_document precedent)"
key-files:
  created: []
  modified:
    - src/sif/search/vector.py
    - src/sif/indexing/incremental.py
    - src/sif/cli/commands/collection.py
    - tests/unit/cli/test_collection.py
    - .planning/milestones/v1.0-phases/10-raise-pytest-coverage-to-90/10-REVIEW-DISPOSITION.md
decisions:
  - "D1-D4 executed exactly as planned: shared public helper in vector.py, CLI-side orchestration, id-only parameterized projection, fail-soft None path"
  - "Negative-grep gate read at identifier level (word boundary): create_embedding_purger contains _embedding_purger as a substring"
metrics:
  duration: 6 min
  completed: 2026-11-11
  tasks: 3
  files: 5
actuals:
  tasks: 3
  commits: 3
plan_head_before: a04af9243ab564c0df31b3e8f45026018f65302c
plan_head_after: a43007a25f8fca24db1a7a86419d54f004282ab1
---

# Phase quick-261111-rqs Plan 01: Close Phase 10 WR-01 — share the purger helper, purge vec0 on collection remove Summary

`collection remove` now purges vec0 embeddings per document (parameterized id-only projection) before `delete_by_collection` inside the existing transaction, via one shared public `create_embedding_purger` in search/vector.py consumed by both IncrementalIndexer and the CLI; proven red-to-green on real SQLite with a keeper-collection survival test and a BM25-only fail-soft pin.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | RED — real-SQLite regression tests for collection-remove vec0 purge | 6a5fce9 | tests/unit/cli/test_collection.py |
| 2 | GREEN — share create_embedding_purger and purge on collection remove | c34a965 | src/sif/search/vector.py, src/sif/indexing/incremental.py, src/sif/cli/commands/collection.py |
| 3 | Close WR-01 in disposition ledger + full quality suite | a43007a | .planning/milestones/v1.0-phases/10-raise-pytest-coverage-to-90/10-REVIEW-DISPOSITION.md |

- Task 1 RED evidence: `pytest tests/unit/cli/test_collection.py --no-cov -q` at pre-fix HEAD → `1 failed, 25 passed`; the sole failure was `test_remove_purges_embeddings_chunks_and_fts` on the stored-embedding assertion (`AssertionError: WR-01: orphaned vec0 embedding survived removal` — orphan id present in the vec0 id set). All pre-existing tests and the new degrade test green. No existing test or helper modified (import lines extended only).
- Task 2: helper body moved verbatim (try VectorSearcher(conn) / except RuntimeError → None) with its docstring contract; IncrementalIndexer keeps the lazy function-local import and TYPE_CHECKING annotation; `_remove_document` and both purge call sites byte-identical; repositories.py untouched by this plan (sibling rqq owns its batch changes).
- Task 3: exactly three ledger edits — WR-01 YAML `disposition: open → fixed`, front-matter `open: 14 → 13` (execution-time HEAD value, siblings rqp/rqq had already decremented 16→14), markdown row Source naming quick 261111-rqs. Closure gate ran BEFORE the ledger commit against `git show HEAD:<ledger>` and passed: exactly 3 changed lines, kinds {yaml, count, row}, all other records byte-identical.

## Verification Results

| Check | Result |
|-------|--------|
| Scoped battery (collection/incremental/vector/repositories, --no-cov) | 75 passed (69 planning baseline + 4 sibling-rqq WR-09 tests landed after planning + 2 new) |
| Single shared definition | `grep -c 'def create_embedding_purger' src/sif/search/vector.py` == 1; `grep -rnw '_embedding_purger' src/` empty (see deviation 1) |
| Existing guards unmodified | purge-ordering (test_incremental.py:271), update_paths real-vec0 purge (:432), delete_by_collection relational contract — all green |
| Ledger three-edit gate | PASSED (exactly 3 edits; open decremented once from execution-time HEAD 14→13) |
| ruff check src tests | All checks passed |
| ruff format --check src tests | 188 files already formatted |
| ty check src/sif | All checks passed |
| Full pytest (coverage, fail_under=90) | 1528 passed, 1 skipped, 95.06% coverage in 75.96s |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Negative-grep gate literal matched the new public name as a substring**
- **Found during:** Task 2 verification
- **Issue:** The plan's gate `test -z "$(grep -rn '_embedding_purger' src/)"` can never pass after the fix because `create_embedding_purger` contains `_embedding_purger` as a substring (5 hits, all the new helper's definition/consumption sites).
- **Fix:** Executed the gate at identifier level — the plan's stated intent and baseline ("two occurrences, incremental.py lines 58 and 92") count the private identifier. `grep -rnw '_embedding_purger' src/` (word boundary) returns empty; the private helper is fully removed. No substantive weakening: every substring hit is the intended shared helper.
- **Files modified:** none (verification reading only)
- **Commit:** c34a965 (verified, not changed)

**2. [Rule 3 - Blocking] ruff format flagged the RED test file after the RED commit**
- **Found during:** Task 2 pre-commit lint
- **Issue:** `ruff format --check` would reformat tests/unit/cli/test_collection.py (line-wrapping in the new tests); the RED commit had been made before formatting.
- **Fix:** Ran `ruff format`, re-ran the file (behavior unchanged), and amended the unpushed, plan-owned RED commit (451109b → 6a5fce9) so the planned three-commit shape and per-task file scopes stay exact. RED evidence was captured before any source edit.
- **Files modified:** tests/unit/cli/test_collection.py (formatting only)
- **Commit:** 6a5fce9 (amended RED)

### Execution-time differences (not deviations)

- Scoped battery count is 75, not the plan's projected 71: sibling 261111-rqq landed 4 WR-09 regression tests in tests/unit/database/test_repositories.py after planning (69 + 4 + 2 = 75). All green.
- `git diff 802c08c -- src/sif/database/repositories.py` is non-empty due to sibling rqq's batch changes (the plan explicitly reserves that file to rqq). This plan's commits do not touch it.
- Ledger open count read at execution time: 14 → 13 (planning-time literal 16 never used).

## Threat Flags

None — no new surface. The purge is a per-document parameterized DELETE keyed on ids selected from the removed collection only, inside the existing db.transaction() (T-rqs-01 mitigated as planned; keeper-collection regression proves sibling rows survive). No package installs (T-rqs-SC accept, not applicable).

## Known Stubs

None.

## Self-Check: PASSED

- All 5 plan artifacts + SUMMARY exist on disk (verified with `[ -f ]`).
- All 3 commits (6a5fce9, c34a965, a43007a) are ancestors of HEAD (verified with `git merge-base --is-ancestor`).
- src/ and tests/ working tree clean after commits; no pre-existing .planning/ churn staged or reverted.