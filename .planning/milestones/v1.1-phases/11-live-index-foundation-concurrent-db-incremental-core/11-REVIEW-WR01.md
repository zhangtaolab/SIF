---
phase: 11-live-index-foundation-concurrent-db-incremental-core
reviewed: 2026-11-12T07:46:41Z
depth: standard
files_reviewed: 2
files_reviewed_list:
  - src/sif/database/repositories.py
  - tests/unit/database/test_repositories.py
findings:
  critical: 0
  warning: 1
  info: 0
  total: 1
  necessity: 0
status: issues_found
---

# Phase 11: WR-01 Fix Delta Code Review

**Reviewed:** 2026-11-12T07:46:41Z  
**Depth:** standard  
**Files Reviewed:** 2  
**Delta:** `aa520be` (reviewed at HEAD `b47f55f`)  
**Status:** issues_found

## Summary

The production `clear_expired()` fix is correct. Each `DELETE` binds at most 500 IDs, two batches process the 1,000-row case, `cursor.rowcount` is accumulated across all batches, and an empty expired set still returns zero without issuing a `DELETE`. The method adds no commit or rollback. Production connections use `isolation_level="IMMEDIATE"`, and an explicit rollback probe restored all 1,000 rows after batched deletion, confirming that the batches join the caller's transaction.

The delta leaves `get()` and `set()` untouched. `clear_expired()` still uses `_expiry_instant()`, compares aware UTC instants with the same `<= now` predicate, catches the same `ValueError`/`TypeError`/`OverflowError` tuple, excludes NULL expiries from selection, and retains unparseable values. No production correctness, security, or necessity defect was found.

One test-reliability warning remains: the new regression can produce a false green on supported Python 3.10 environments linked against modern SQLite because it cannot force the 999-variable limit there.

## Warnings

### WR-02: The 1,000-row regression can be vacuous on Python 3.10 with modern SQLite

**File:** `tests/unit/database/test_repositories.py:630-634`  
**Issue:** Python 3.10 is explicitly supported (`pyproject.toml:11,21`), but `sqlite3.Connection.setlimit` is available only from Python 3.11. On Python 3.10, the `hasattr` guard skips the only statement that pins the limit to 999. SQLite 3.32.0 and later default `SQLITE_MAX_VARIABLE_NUMBER` to 32,766 rather than 999, so a Python 3.10 runtime linked against such a library allows the pre-fix single `DELETE` with 1,000 parameters. The test then passes against the buggy implementation despite its comment claiming that Python 3.10 stock SQLite defaults to 999. This does not invalidate the production fix, but it makes the regression's red/green signal runtime-dependent.
**Fix:** Do not silently continue when the limit cannot be controlled. Skip explicitly on runtimes without `setlimit`, or use another reliable mechanism to enforce a limit below 1,000 before running the regression:

```python
if not hasattr(db, "setlimit"):
    pytest.skip("Connection.setlimit is required to force the 999-variable regression")
db.setlimit(sqlite3.SQLITE_LIMIT_VARIABLE_NUMBER, 999)
```

If Python 3.10 must execute rather than skip this test, use a runtime-specific limit-control mechanism and assert the resulting limit; do not infer a 999-variable ceiling from the Python version.

## Verification

- `python -I -m pytest -q --no-cov tests/unit/database/test_repositories.py -k 'LLMCacheClearExpiredWR01 or LLMCacheExpiryWR09 or LLMCacheExpiryEdgePolicy'`: **12 passed, 17 deselected**.
- A direct probe of the old single-statement deletion with the connection pinned to 999 variables raised `sqlite3.OperationalError: too many SQL variables`, confirming the regression is non-vacuous when `setlimit` is available.
- A 1,000-row `BEGIN IMMEDIATE` probe returned a deleted count of 1,000, observed `connection.in_transaction` after `clear_expired()`, and restored all 1,000 rows on rollback.
- `ruff check` and `ruff format --check` passed for both reviewed files.
- `git diff aa520be^ aa520be --check` passed; neither reviewed file has later source changes or uncommitted modifications.

---

_Reviewed: 2026-11-12T07:46:41Z_  
_Reviewer: Claude (gsd-code-reviewer)_  
_Depth: standard_

## Disposition

- **WR-01 (production):** fixed — aa520be, confirmatory review clean (0 Critical).
- **WR-02 (test reliability, Warning):** DEFERRED — on Python 3.10 `sqlite3.setlimit` is unavailable (added 3.11), so the 1000-row regression cannot pin the 999-variable floor there; modern SQLite (3.32+) defaults to 32766, so the test could false-green on 3.10. Non-vacuous on the current runtime (3.13). Follow-up: skip the test when the limit cannot be controlled, or enforce a sub-1000 limit on 3.10. Test-only; production fix is correct and verified.
