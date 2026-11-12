---
phase: 11-live-index-foundation-concurrent-db-incremental-core
reviewed: 2026-11-12T07:27:46Z
depth: standard
files_reviewed: 9
files_reviewed_list:
  - src/sif/cli/commands/index.py
  - src/sif/cli/commands/watch.py
  - src/sif/cli/error_handling.py
  - src/sif/cli/main.py
  - src/sif/database/factory.py
  - src/sif/database/repositories.py
  - src/sif/indexing/incremental.py
  - src/sif/indexing/watcher.py
  - src/sif/mcp/watch_host.py
findings:
  critical: 0
  warning: 1
  info: 0
  total: 1
  necessity: 0
status: issues_found
---

# Phase 11: Code Review Report (incremental HEAD re-verification)

**Reviewed:** 2026-11-12T07:27:46Z
**Depth:** standard
**Files Reviewed:** 9
**Status:** issues_found

## Summary

Incrementally reviewed all nine scoped files at HEAD `0899d909d97f95fc9fa4b8c26b0717cb69e78e7c`, using `5be330a59db40bcd4a78078f63c8fd47612d502c` as the prior-review baseline. The previously fixed mkdir-boundary, expiry-overflow, and factory setup-cleanup defects were not re-reported.

The Phase 11 concurrency and locking invariants remain intact:

- `src/sif/database/factory.py:48-77` remains the sole production `sqlite3.connect` site. The `foreign_keys` / `busy_timeout` / WAL / `synchronous` recipe and `isolation_level="IMMEDIATE"` are unchanged; the only factory behavior delta is closing the local handle when setup raises.
- The CLI update/embed paths and watch startup reconcile still hold `index_lock` (`index.py:53-59,275-281`; `watch.py:176-187`). Watcher bursts and full reconciles still acquire the same per-database flock at `watcher.py:800-801,822-833`.
- `FileWatcher.enqueue_reconcile()` (`watcher.py:525-537`) only constructs and enqueues intent. It performs no database work and does not bypass locking: every resulting job flows through `_run_job()` to `_run_reconcile()`, whose flock covers the checksum snapshot, incremental pass, and optional embed leg. MCP startup still calls `start()` before enqueueing (`watch_host.py:154-157`). No new lock ordering was introduced.
- The `IncrementalIndexer` per-file `with self._conn:` commit boundaries are unchanged (`incremental.py:312-316,323-341,353-355,381-384`). The shared `create_embedding_purger()` is behaviorally equivalent to the extracted local helper.

One new Warning was found in the post-baseline LLM-cache cleanup: its single `IN (...)` delete exceeds SQLite's bind-variable limit on sufficiently large expired caches, aborting `sif cleanup`. This is outside the locking path and does not weaken the Phase 11 invariants.

Validation: scoped `ruff check` and `ruff format --check` passed; authoritative `ty check src/sif` passed; 168 focused repository/factory/incremental/watcher/CLI/MCP/integration-concurrency tests passed with `--no-cov`. The caller-provided full-suite HEAD baseline is 1590 passed at 95.18% coverage. The cache-limit defect was independently reproduced as `sqlite3.OperationalError: too many SQL variables` with 1,000 expired rows and SQLite's variable limit set to the widely deployed 999 value.

Necessity review was performed using the standard-depth rubric. Zero necessity findings: the opener's cleanup handles reachable construction/schema failures, and `enqueue_reconcile` has three real producers (MCP startup, recovery-return, and rescope-add), so it is not generality without instantiation.

## Warnings

### WR-01: Cache cleanup exceeds SQLite bind-variable limits

**File:** `src/sif/database/repositories.py:616-632`
**Issue:** `clear_expired()` collects every expired row and emits one `DELETE FROM llm_cache WHERE id IN (?, ?, ...)`. SQLite limits the number of host parameters per statement; 999 is a common supported limit, while this table has no row cap. Once the expired set exceeds the connection's limit, cleanup raises `sqlite3.OperationalError: too many SQL variables`. Through `main.py:230-259`, that aborts and rolls back the entire `sif cleanup` transaction, including orphan removal. Reproduced with 1,000 expired rows and `SQLITE_LIMIT_VARIABLE_NUMBER=999`. The pre-change single SQL expiry predicate did not have this failure mode.
**Fix:** Delete in bounded batches within the caller's existing transaction and return the accumulated row count. For example:

```python
removed = 0
batch_size = 500
for start in range(0, len(expired_ids), batch_size):
    batch = expired_ids[start : start + batch_size]
    placeholders = ",".join("?" for _ in batch)
    cursor = self.db.execute(
        f"DELETE FROM llm_cache WHERE id IN ({placeholders})",
        batch,
    )
    removed += cursor.rowcount
return removed
```

Add a regression with more expired rows than a deliberately lowered SQLite variable limit (or more than the chosen fixed batch size), asserting all expired rows are removed, fresh/malformed rows remain, and the returned count is exact.

---

_Reviewed: 2026-11-12T07:27:46Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
