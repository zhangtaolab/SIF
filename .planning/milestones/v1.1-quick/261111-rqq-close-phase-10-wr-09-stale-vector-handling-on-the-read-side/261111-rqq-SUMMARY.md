---
phase: quick-261111-rqq
plan: 01
subsystem: database/cli
status: complete
tags: [phase10, wr-09, llm-cache, datetime, timezone, cleanup, review-closure]
requires: []
provides:
  - "LLMCacheRepository.clear_expired: instant-based expiry (parsed datetimes, legacy naive-local as system-local)"
  - "LLMCacheRepository.set: aware-UTC (+00:00) expires_at writes"
  - "cleanup_cmd delegates cache expiry to the repository on the same transaction"
affects:
  - src/sif/cli/main.py
  - src/sif/database/repositories.py
tech-stack:
  added: []
  patterns:
    - "parse-and-compare datetime expiry predicate shared by CLI and repository (one SQL dialect for the rule)"
    - "process-global TZ forcing fixture with mandatory teardown restoration (east_of_utc)"
key-files:
  created:
    - .planning/quick/261111-rqq-close-phase-10-wr-09-stale-vector-handling-on-the-read-side/red-console.txt
  modified:
    - src/sif/database/repositories.py
    - src/sif/cli/main.py
    - tests/unit/database/test_repositories.py
    - tests/unit/cli/test_main.py
    - .planning/milestones/v1.0-phases/10-raise-pytest-coverage-to-90/10-REVIEW-DISPOSITION.md
decisions:
  - "Legacy naive-local expires_at strings are interpreted as system-local via astimezone(timezone.utc) — the exact semantics of the old datetime.fromtimestamp writer; fixing the write side does not rewrite existing rows"
  - "NULL and unparseable expires_at rows are retained (cleanup never deletes a row whose expiry it cannot interpret); parameterized DELETE by id, placeholder string the only interpolated part"
  - "LLMCacheRepository.get stays byte-identical (same defect class but NOT named by WR-09 — separate finding); Phase 11 settings-guard WR-09 and WR-01 purge region untouched"
metrics:
  duration: 9 min
  completed: 2026-11-11
  tasks: 2
  files: 5
actuals:
  tokens: 3788
  tasks: 2
  commits: 3
plan_head_before: 7be1412f08da6e81c68257db4435b5dccfcc5ebe
plan_head_after: 8f16b1e60694b479b45560dfb7636d7c4c8093c9
---

# Phase quick-261111-rqq Plan 01: Close Phase 10 WR-09 (stale-vector cache expiry, read + write side) Summary

**LLM cache expiry now compares parsed UTC instants instead of ISO string order: `set` writes aware-UTC (+00:00) expiries, `clear_expired` interprets legacy naive-local rows as system-local, and `cleanup_cmd` delegates to the repository on the same transaction — pinned by five real-SQLite regression tests including a forced TZ=Asia/Shanghai east-of-UTC leg.**

## Closed Finding

**Phase 10 WR-09** (10-REVIEW.md): "`cleanup` compares naive-local ISO timestamps against aware-UTC ISO strings lexicographically." Two production sites plus one reuse, all closed:

1. **Read side** — `cleanup_cmd` (src/sif/cli/main.py) deleted expired `llm_cache` rows with an inline `DELETE ... WHERE expires_at <= ?` bound to `datetime.now(timezone.utc).isoformat()`, re-implementing `clear_expired()` inline with the same lexicographic defect.
2. **Write side** — `LLMCacheRepository.set` (src/sif/database/repositories.py) stored `datetime.fromtimestamp(expires_at).isoformat()` — a naive LOCAL-time string with no offset suffix.
3. **Reuse** — `clear_expired` itself carried the same lexicographic defect; it is now the single parse-and-compare implementation the CLI delegates to.

## Live Reproduction Evidence (planning baseline HEAD 802c08c)

Real in-memory SQLite with the production llm_cache DDL, TZ forced to Asia/Shanghai via `time.tzset`: a legacy naive-local row for an instant 1 hour in the past stored as `2026-11-11T19:07:12.958061` while aware now was `2026-11-11T12:07:12.958061+00:00` — the lexicographic DELETE returned **rowcount 0 (expired row KEPT**, the reported east-of-UTC retention bug). The post-fix predicate (`datetime.fromisoformat(value).astimezone(timezone.utc) <= now`) selects precisely that row. The old writer's string has no `+00:00` suffix; the new writer form produces `2026-11-11T11:07:12.958061+00:00` for the same instant.

## Red-to-Green Regression Evidence

RED captured at execution time in `red-console.txt` (before any production edit, against baseline production code at 7be1412): **3 failed, 31 passed** — all three failures pure assertion failures, never collection/setup errors:

| Test | RED assertion failure |
|------|----------------------|
| `TestLLMCacheExpiryWR09::test_set_stores_aware_utc_expiry` | `'2026-11-11T21:35:21.114062'.endswith('+00:00')` is False (naive local write, wall time +8h) |
| `TestLLMCacheExpiryWR09::test_clear_expired_removes_legacy_naive_local_expired_row` | `clear_expired() == 0` (expired legacy row retained) |
| `TestCleanupRealDatabase::test_cleanup_removes_legacy_naive_local_expired_cache` | CLI printed "Removed 0 expired cache entries" |

The two preservation tests (aware-UTC rows; NULL/unparseable retention) and all 29 existing tests passed in the RED run. GREEN after the production edits: **34 passed** (29 existing unmodified + 5 new), ruff check and format clean on all four code files.

Note: after the RED capture, three lint-driven adjustments were applied to the new tests (see Deviations); `@pytest.mark.usefixtures("east_of_utc")` requests the identical fixture as the former parameter form and no assertion changed, so the red state is preserved by the committed test form.

## Implementation

- **repositories.py `set`**: only the writer line changed — `datetime.fromtimestamp(expires_at, tz=timezone.utc).isoformat()`. TTL guard, timestamp arithmetic, `created_at`, and the INSERT byte-identical.
- **repositories.py `clear_expired`**: signature unchanged (`-> int`); SELECT id/expires_at WHERE NOT NULL, `datetime.fromisoformat` inside try/except ValueError (skip-and-retain on unparseable), `.astimezone(timezone.utc)` normalization (naive presumed system-local — the old writer's exact semantics; aware converts losslessly), collect expired ids, parameterized `DELETE ... WHERE id IN (?,?,...)` (placeholder string the only interpolated part), return rowcount; empty list returns 0. Docstring names WR-09 and the legacy interpretation.
- **main.py**: module-level `from sif.database.repositories import LLMCacheRepository` after the Database import; the cleanup cache block replaced by `cache_removed = LLMCacheRepository(conn).clear_expired()` on the same transaction connection. The function-local datetime import was deleted outright (no other datetime/timezone use in main.py). Console lines, confirmation prompt, missing-index early return, and ClickException wrapper byte-identical.

## Scope Boundaries (explicitly preserved)

- `LLMCacheRepository.get` — same defect class, NOT named by WR-09; byte-identical (a get-side fix is a separate finding).
- Phase 11 settings-guard "WR-09" (`_get_default_db_path` / `TestDefaultDbPathConfigError`) — a DIFFERENT review's finding; byte-identical.
- WR-01 purge region (`DocumentRepository.delete_by_collection`, sibling rqs) — byte-identical; diff gate proved collection.py/index.py/get.py/backend.py/schema.py/generator-owned docs untouched.
- All 29 existing tests in the three touched test files pass unmodified, including `test_llm_cache_hit_expiry_replacement_and_clear`, `test_cleanup_preserves_valid_rows_and_removes_only_orphans`, `test_cleanup_closes_database`.

## Ledger Closure (execution-time-robust)

Exactly three scoped edits to 10-REVIEW-DISPOSITION.md; the reconstruction gate ran BEFORE the commit and compared against execution-time `git show HEAD:<ledger>`:

- WR-09 YAML `disposition: open` → `fixed` (id/severity/title preserved)
- Aggregate `open: 15` → `open: 14` (execution-time value — sibling rqp's IN-08 closure had already landed; never hardcoded 16)
- WR-09 markdown row → `fixed` with Source cell naming quick 261111-rqq

Gate output: `WR-09-fixed; open 15->14; all-other-ledger-content-byte-identical` — every other YAML block, markdown row (including the sibling IN-08 closure), ordering, and trailing newline preserved. `total: 22` and `recorded` unchanged. No `**Status:**` lines introduced.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Ruff ARG002/E501 on the new code**
- **Found during:** Task 1 GREEN verification
- **Issue:** ruff flagged the side-effect-only `east_of_utc` fixture parameters (ARG002, three tests) and one 101-char SELECT line (E501); ARG is not in the tests per-file-ignores.
- **Fix:** switched the three tests to `@pytest.mark.usefixtures("east_of_utc")` (identical fixture request, standard pytest idiom for side-effect fixtures); wrapped the SELECT line; ran `ruff format` on test_repositories.py only (plan-sanctioned when the format check complains). No assertion or fixture semantics changed.
- **Files modified:** tests/unit/database/test_repositories.py, tests/unit/cli/test_main.py, src/sif/database/repositories.py
- **Commit:** 67d8644 (folded into the GREEN commit; RED evidence captured pre-adjustment, semantics unchanged)

No other deviations — production changes match the plan's exact prescriptions.

## Quality Suite (CLAUDE.md full gate, PATH miniconda python)

| Gate | Result |
|------|--------|
| Targeted: test_repositories.py + test_main.py + test_database_lifecycle.py (--no-cov) | 34 passed |
| `ruff check src tests` | All checks passed |
| `ruff format --check src tests` | 188 files already formatted |
| `python -m pytest` (full, with coverage) | **1526 passed, 1 skipped in 77.17s; coverage 95.03% (fail_under=90 reached)** |
| Sibling/schema/docs diff gate (`git diff --exit-code`) | clean — all seven guarded paths untouched |

## Commits

| Hash | Type | Description |
|------|------|-------------|
| 0a143d9 | test | RED: five WR-09 regression tests (3 defect-pinning + 2 preservation) |
| 67d8644 | fix | GREEN: aware-UTC write side + parse-and-compare clear_expired + cleanup delegation |
| 8f16b1e | docs | Ledger closure: WR-09 fixed, open 15→14, reconstruction-gated |

Pre-existing uncommitted `.planning/` churn (config.json, STATE.md, agent-history.json, PATTERNS/research/tmp files) was never staged, committed, or reverted. STATE.md/ROADMAP.md untouched — orchestrator owns those writes.

## Known Stubs

None — no placeholders, TODOs, or unwired data introduced; all five new tests execute on this host (tzset available).

## Self-Check: PASSED

All 7 artifact files FOUND on disk; all 3 commits (0a143d9, 67d8644, 8f16b1e) verified as ancestors of HEAD (8f16b1e).