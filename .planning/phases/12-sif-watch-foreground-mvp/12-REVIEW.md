---
phase: 12-sif-watch-foreground-mvp
reviewed: 2026-11-07T11:29:17Z
depth: standard
files_reviewed: 15
files_reviewed_list:
  - src/sif/cli/commands/watch.py
  - src/sif/cli/main.py
  - src/sif/config/settings.py
  - src/sif/indexing/incremental.py
  - src/sif/indexing/scanner.py
  - src/sif/indexing/watcher.py
  - tests/integration/test_watch_e2e.py
  - tests/unit/cli/test_watch_cmd.py
  - tests/unit/indexing/test_incremental.py
  - tests/unit/indexing/test_scanner.py
  - tests/unit/indexing/test_watcher.py
  - pyproject.toml
  - docs/cli-reference.md
  - docs/configuration.md
  - scripts/generate_config_ref.py
findings:
  critical: 1
  warning: 2
  info: 4
  total: 7
  necessity: 0
status: issues_found
---

# Phase 12: Code Review Report

**Reviewed:** 2026-11-07T11:29:17Z
**Depth:** standard
**Files Reviewed:** 15
**Status:** issues_found

## Summary

Adversarial review of the `sif watch` foreground MVP: CLI host (`watch.py`), watch pipeline (`watcher.py`), the incremental core extensions (`update_paths`), the shared scan/watch predicate (`scanner.py`), new settings, tests, docs, and the config-doc generator. Cross-module tracing covered `database/locking.py`, `database/factory.py`, `database/database.py`, `database/repositories.py`, `search/vector.py`, `embedding/manager.py`, `cli/commands/index.py`, and the installed watchdog 6.0.0 sources (plus a watchdog 4.0.0 tarball to validate the `>=4.0.0,<7.0.0` floor — `EventDebouncer` is source-identical on the used surface, so the floor is sound).

The core contracts mostly hold up well under tracing: per-burst flock enter/exit (proven by `test_lock_acquired_per_job_never_held_for_lifetime`), embed compute outside write transactions (proven by the `in_transaction` flag battery), the D-11 missing-root guards on both update paths, the D-06 fold's order-independence and atomic-save trailing-delete absorption, and the D-12/D-14 recovery and signal machinery. The `fold_events` remove-minus-index subtraction, the `**/` zero-directory pattern parity, and the shared ignore predicate are all justified and tested — no necessity findings survived the evidence bar.

One BLOCKER survives: `FileWatcher.stop()` breaks its own single-owner connection invariant whenever the worker join times out (10s) while a job legitimately runs longer (flock wait up to the 30s default, or first-use model load at embed depth — which happens inside the job). The graceful flush then runs queued jobs on the main thread concurrently with the still-live worker on the same `sqlite3.Connection`, interleaving BEGIN IMMEDIATE transactions and breaking per-file atomicity (D-04). Two warnings cover an embed-leg failure mode that permanently strands documents without vectors, and a state-map collision on repeated `-c` names.

## Critical Issues

### CR-01: stop() drains queued jobs after a timed-out worker join — two threads share one connection mid-transaction

**File:** `src/sif/indexing/watcher.py:383-386` (invariant claim at 377-379; timeouts at 47 and 84)
**Issue:** `stop()` joins the worker with `_WORKER_JOIN_TIMEOUT_SECONDS = 10.0` and then unconditionally runs `_drain_once()` on the calling thread:

```python
if self._worker is not None:
    self._worker.join(timeout=_WORKER_JOIN_TIMEOUT_SECONDS)
if flush:
    self._drain_once()
```

The preceding comment states the invariant: "queued work is then drained on this thread so no two threads ever share the connection mid-job." A `Thread.join(timeout=...)` returns silently when the thread is still alive, and a worker job can legitimately exceed 10s:

1. **Flock contention:** `_run_job` wraps every job in `index_lock(self._db_path, self._config.lock_timeout)` (watcher.py:484-490) with `lock_timeout` defaulting to 30.0 (`WatchConfig.lock_timeout`, and `Settings.lock_wait_timeout` feeding it). `index_lock` polls the flock for the full `timeout_s` (locking.py:74-93), so a concurrent `sif index update` holding the lock pins the worker for up to 30s — 3x the join timeout.
2. **Embed depth:** the first embed burst runs `manager.load_model()` inside the job, inside the lock window (watcher.py:216-217 → 239 → 489-490). A cold model cache (download) or a large burst easily exceeds 10s.

When the join times out, `_drain_once()` executes `_run_job` on the main thread while the worker is (or becomes) simultaneously mid-`_run_job`. Both threads then issue `with self._conn:` transactions on the same connection (`check_same_thread=False` at factory.py:56 permits it; nothing serializes it). Interleaved BEGIN IMMEDIATE transactions break per-file atomicity (D-04): the drain thread's context-manager exit can commit the worker's half-finished multi-write job, and an exception-driven rollback in either thread discards the other's writes. Downstream, `shutdown_watcher` (watch.py:85-88) then executes `PRAGMA wal_checkpoint(TRUNCATE)` on that same connection potentially mid-worker-transaction, breaking the D-14 exit-0/WAL-truncate contract (OperationalError propagates → exit 1 with traceback, or a busy result leaves the WAL untruncated).

The e2e battery never hits this because single-file bursts finish well under 10s and no competing writer exists.
**Fix:** Gate the flush on the worker having actually exited, and degrade loudly instead of concurrently:

```python
if self._worker is not None:
    self._worker.join(timeout=_WORKER_JOIN_TIMEOUT_SECONDS)
    if flush and self._worker.is_alive():
        logger.warning(
            "watch worker still busy after %.1fs; skipping bounded flush (jobs stay queued)",
            _WORKER_JOIN_TIMEOUT_SECONDS,
        )
        flush = False
if flush:
    self._drain_once()
```

## Warnings

### WR-01: Mid-burst embed failure aborts remaining candidates and strands those documents vector-less (checksum change-detection never retries)

**File:** `src/sif/indexing/watcher.py:248-268` (embed loop), `504-509` (`_run_burst` changed-set), `src/sif/indexing/incremental.py:279-299` (update branch purges chunks + embeddings)
**Issue:** At embed depth, `_run_burst` detects changed paths by snapshotting checksums before the BM25 leg and diffing after. The BM25 update branch deletes the doc's chunks and embeddings (`_process_file`), then `embed_documents` re-chunks and re-embeds. Any per-path exception inside `embed_documents` (remote embedding API error, one pathological document, batch failure) propagates out of `_run_burst` and is caught only by `_worker_loop`'s blanket handler (watcher.py:464-467) — the remaining candidates in that burst are silently skipped, and unlike first-use failures (which emit a fail-soft `error` event, watcher.py:219), per-path embed failures produce no `on_event` at all, only a log record.

The stranded state is sticky: the BM25 leg already committed the new checksum, so on every later burst `before == stored` → `changed` is empty → the embed leg never runs for those paths. Documents edited during the failure end up chunk-less and vector-less (worse than before the burst) until their content changes again or a manual `sif index embed` heals them (`_needs_embedding` self-heals because live chunk ids are empty). Vector search silently loses coverage for exactly the documents the user just edited.
**Fix:** Wrap the per-candidate body of `embed_documents` in try/except — emit `error Embedding failed for {path}: {e}` via `on_event`, continue with the remaining candidates — and/or record failed paths on the session so the next burst retries them (e.g., union `changed` with a pending-retry set instead of relying solely on the checksum diff).

### WR-02: Repeated `-c name` schedules duplicate watches and orphans a `_WatchState` entry

**File:** `src/sif/cli/commands/watch.py:102-106` (`_select_collections` appends without dedupe), `src/sif/indexing/watcher.py:330-331` (`self._watch_states[coll.name] = state` keyed by name)
**Issue:** `sif watch -c notes -c notes` puts the same collection in `selected` twice. `FileWatcher.start()` then schedules two debouncers/emitters on the same root, and the second `self._watch_states["notes"] = state` overwrites the first — the first watch handle becomes unreachable by `recovery_tick` (watcher.py:404-424), so if the root later disappears only the second handle is unscheduled; the orphaned emitter keeps running. Every burst also folds twice and runs two flock-guarded jobs (the second is a checksum no-op, but it still takes the lock and rewrites collection stats).
**Fix:** Deduplicate in `_select_collections` while preserving flag order:

```python
for name in dict.fromkeys(names):  # stable order-preserving dedupe
    ...
```

## Info

### IN-01: Rich markup silently swallows bracketed text in event payloads

**File:** `src/sif/cli/commands/watch.py:132-143`
**Issue:** Event payloads (file names, collection names) are interpolated into Rich markup strings, e.g. `console.print(f"  [dim]Indexed: {payload}[/dim]")`. Verified empirically: a file named `report[v2].md` renders as `report.md` — Rich consumes `[v2]` as a style tag. Filenames and collection names are user data and routinely contain brackets.
**Fix:** Escape payloads with `rich.markup.escape(payload)` (or pass `markup=False` for payload-bearing lines).

### IN-02: Invalid settings surface as a raw pydantic traceback when `--index` is passed explicitly

**File:** `src/sif/cli/commands/watch.py:192-194`
**Issue:** The group-level ValidationError → ClickException conversion lives in `_get_default_db_path` (main.py:34-39), but Click only invokes a default callable when the option is NOT supplied. With `sif --index /tmp/x.db watch` and `SIF_WATCH_UPDATE_DEPTH=bogus` in the environment, the first `get_settings()` call is inside `watch_cmd`, and the pydantic ValidationError escapes as a raw traceback — contradicting the validator's stated goal of surfacing "as a config error naming the field" (settings.py:184-189). Note the e2e battery always passes `--index` (albeit with SIF_ vars stripped, so it never exercises this path).
**Fix:** Wrap the `get_settings()` call in watch_cmd (or centrally in the group callback) with `except ValidationError as e: raise click.ClickException(str(e)) from e`.

### IN-03: Generator-owned docs omit the watch exit-130 contract and the new validation rules

**File:** `docs/cli-reference.md:681-687`, `docs/configuration.md:127-139` / `scripts/generate_config_ref.py:265-294`
**Issue:** Two completeness gaps in the generated docs (both docs are generator-owned; never hand-edit — fix the generators): (1) the Exit Codes table lists only 0/1/2, but `watch` exits 130 on a second signal (watch.py:63-64), a user-facing contract documented only in the module docstring; (2) the hardcoded Validation Rules table does not include `watch_update_depth` (or `reranker_model_type`) even though the field tables now carry "(validated by `validate_watch_update_depth`)" — the rules table and the field descriptions can drift apart as validators are added.
**Fix:** Add the 130 row and derive validator rows from `get_validators()` in the respective generators.

### IN-04: Reconcile jobs at embed depth purge vectors without rewriting them — silent vector-coverage regression

**File:** `src/sif/indexing/watcher.py:481-487`, `src/sif/indexing/incremental.py:279-299`
**Issue:** By documented design, `needs_reconcile` jobs (directory move, returning missing root) stay BM25-only. But the reconcile's update branch purges chunks and embeddings for every changed document, so with `--embed` (or `SIF_WATCH_UPDATE_DEPTH=embed`), documents touched during a directory rename or a missing-root window permanently lose their vectors: the reconcile commits fresh checksums, so no later burst's `changed` set includes them. The tradeoff is acknowledged in a code comment but not in the user-facing `--embed` help or docs, and the healing path (manual `sif index embed`) is not suggested anywhere the user will see.
**Fix:** At minimum document the gap in the `--embed` help text; ideally enqueue the reconcile's changed paths into the embed session's retry set once one exists (see WR-01).

---

_Reviewed: 2026-11-07T11:29:17Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
