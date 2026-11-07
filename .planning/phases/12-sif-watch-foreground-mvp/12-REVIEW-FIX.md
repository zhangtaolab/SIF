---
phase: 12-sif-watch-foreground-mvp
fixed_at: 2026-11-07T12:35:18Z
review_path: .planning/phases/12-sif-watch-foreground-mvp/12-REVIEW.md
iteration: 1
findings_in_scope: 3
fixed: 3
skipped: 0
status: all_fixed
---

# Phase 12: Code Review Fix Report

**Fixed at:** 2026-11-07T12:35:18Z
**Source review:** .planning/phases/12-sif-watch-foreground-mvp/12-REVIEW.md
**Iteration:** 1

**Summary:**
- Findings in scope: 3 (fix_scope=critical_warning → CR-01, WR-01, WR-02; Info findings IN-01..IN-04 and necessity findings out of scope)
- Fixed: 3
- Skipped: 0

**Verification:** all gates ran in the MAIN CHECKOUT (`workflow.use_worktrees=false` — no worktree was created, so the numbers below are reproducible directly from this tree). After EACH fix: `env -u FORCE_COLOR NO_COLOR=1 python -m pytest -q --tb=short` (final: 1054 passed, coverage 95.82% ≥ 90 floor), `ruff check src tests`, `ruff format --check src tests`, `ty check src/sif` — all green at every commit. No CLI surface (flags/help/settings) changed, so no `make docs-generate` regeneration was required; `tests/test_docs.py` passed in the full suite.

## Fixed Issues

### CR-01: stop() drains queued jobs after a timed-out worker join — two threads share one connection mid-transaction

**Files modified:** `src/sif/indexing/watcher.py`, `tests/unit/indexing/test_watcher.py`
**Commit:** 688da29
**Applied fix:** `stop()` now gates the bounded flush on `self._worker.is_alive()` being False after the timed-out join: when the worker is still busy (flock wait up to `lock_timeout`, first-use model load at embed depth), it logs ONE warning ("watch worker still busy after %.1fs; skipping bounded flush (jobs stay queued)"), sets `flush = False`, and skips `_drain_once()` — the drain never races the live worker on the same `sqlite3.Connection`. The invariant comment above the join was extended to state the timed-out-join behavior. Regression tests: new `TestStopFlushGate` class with synthetic worker fakes (zero timing) — `test_stop_skips_flush_when_worker_join_times_out` (alive worker → no drain, exactly one warning) and `test_stop_flushes_once_worker_exited` (dead worker → drain runs once).

### WR-01: Mid-burst embed failure aborts remaining candidates and strands those documents vector-less (checksum change-detection never retries)

**Files modified:** `src/sif/indexing/watcher.py`, `tests/unit/indexing/test_watcher.py`
**Commit:** 49aeacc
**Applied fix:** Both halves of the review's fix suggestion: (1) the per-candidate body of `_EmbedSession.embed_documents` is wrapped in try/except — on failure it emits `error Embedding failed for {path}: {e}` via `on_event`, logs with `logger.exception`, and CONTINUES with the remaining candidates (earlier candidates stay durable; the failed path's short write-txn rolls back atomically); (2) failed paths are recorded on a new per-collection `_pending_retry: dict[str, set[Path]]` set, and every `embed_documents` call unions its candidates with the popped retry set — so a later burst retries the path even though its checksum no longer counts as changed. A session-level `ensure_ready` failure still drops candidates (embed is disabled for good; retrying cannot succeed — preserves the documented one-error-event fail-soft contract). Regression test: `test_embed_failure_emits_error_continues_and_retries_next_burst` — burst 1 has two changed docs where the first embed call raises ("provider 503"): exactly one error event names the failed path, the second doc still gets chunks+vectors; burst 2 touches the failed doc WITHOUT a content change (empty checksum diff) and the retry set alone heals it to full chunks+vectors.

### WR-02: Repeated `-c name` schedules duplicate watches and orphans a `_WatchState` entry

**Files modified:** `src/sif/cli/commands/watch.py`, `tests/unit/cli/test_watch_cmd.py`
**Commit:** de9854f
**Applied fix:** `_select_collections` iterates `dict.fromkeys(names)` — a stable, order-preserving dedupe — so a repeated `-c` name selects the collection exactly once (no duplicate debouncers/emitters, no `_WatchState` overwrite orphaning the first watch handle). Unknown-name ClickException wording unchanged. Regression test: `test_select_collections_dedupes_repeated_names_in_flag_order` — `("notes", "docs", "notes")` selects exactly `["notes", "docs"]` in flag order.

## Skipped Issues

None — all three in-scope findings were fixed.

**Out of scope (remain open in REVIEW.md):** IN-01 (Rich markup escaping of event payloads), IN-02 (raw pydantic traceback with explicit `--index` + invalid settings), IN-03 (generator-owned docs: exit-130 row + validator-derived rules table), IN-04 (reconcile jobs at embed depth purge vectors without rewrite — the `--embed` help-text gap; note the WR-01 retry set now exists and IN-04's "ideally" suggestion could build on it in a future pass).

---

_Fixed: 2026-11-07T12:35:18Z_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_
