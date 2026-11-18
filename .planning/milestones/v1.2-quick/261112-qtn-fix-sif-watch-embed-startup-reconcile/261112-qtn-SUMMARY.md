---
phase: quick-261112-qtn
plan: 01
subsystem: indexing/watch
tags: [watch, embed-depth, startup-reconcile, incremental-indexer, flock, pytest]

# Dependency graph
requires:
  - phase: 12 (live watch pipeline)
    provides: FileWatcher._run_reconcile checksum-diff embed leg (IN-04), WatchConfig, index_lock-per-pass
  - phase: 13-02 (detached daemon lifecycle)
    provides: run_watch_host shared host body executed verbatim by daemon and installed service
provides:
  - "FileWatcher.reconcile_now — public pre-start reconcile seam delegating to the IN-04 embed-aware _run_reconcile"
  - "_run_reconcile progress/on_wait overrides so the startup pass renders through the CLI and keeps the flock-waiting notice"
  - "run_watch_host startup reconcile no longer strands embed-depth changed documents vector-less"
  - "CLI-level regression + BM25-parity pins for the startup seam"
affects: [watch-host, daemon-hosts, installed-service, embed-depth, live-index]

actuals:
  tokens: 3963
  tasks: 2
  commits: 2
  plan_head_before: 94099ef
  plan_head_after: 7dae754

tech-stack:
  added: []
  patterns:
    - "One embed-aware reconcile path: the startup seam delegates to the existing checksum-diff + embed-leg logic instead of duplicating it"
    - "Optional progress/on_wait overrides default to WatchConfig callbacks, so worker paths (_run_job -> _run_reconcile, _run_burst) stay byte-identical"
    - "CLI startup tests run a REAL FileWatcher with Observer mocked and the park loop stopped by the captured SIGTERM handler"

key-files:
  created: []
  modified:
    - src/sif/indexing/watcher.py
    - src/sif/cli/commands/watch.py
    - tests/unit/cli/test_watch_cmd.py

key-decisions:
  - "reconcile_now is a thin delegation to _run_reconcile(collection, progress=..., on_wait=...) — no second embed implementation, so the startup pass and the worker reconcile can never drift"
  - "FileWatcher is constructed BEFORE the startup loop so the pre-observer pass runs through the same instance the worker then owns; watcher.start() still comes after every collection reconciled (D-03)"
  - "progress/on_wait are keyword-only and default to self._config.on_event + None, preserving worker behaviour exactly; the CLI passes its Rich renderer and the Another-index-writer on_wait notice"
  - "BM25 depth takes before=None, so no checksum diff and no embed call happen — the DB outcome is identical to the old direct update_collection block"
  - "Out of scope by plan: full backfill of documents already vector-less with fresh checksums (sif index embed owns that repair)"
  - "TDD executed as two commits (test RED then feat GREEN), following the canonical TDD commit-scope contract rather than the sibling quick items' single-commit policy"

patterns-established:
  - "Startup-seam regression proof: BM25-index a doc, rewrite it stale on disk, run watch_cmd to completion via the captured SIGTERM park loop, then query a fresh factory connection for documents without an embedded chunk"
  - "BM25 parity proof: patch EmbeddingManager.from_settings with a raising side_effect so any model construction fails the test, and assert the stored checksum matches MarkdownParser plus zero chunk/vector rows"

requirements-completed: []

coverage:
  - id: D1
    description: "An embed-depth `sif watch --embed` startup re-embeds every document its pre-observer BM25 pass changed; a fresh connection sees zero documents without an embedded chunk"
    verification:
      - kind: unit
        ref: "tests/unit/cli/test_watch_cmd.py#TestStartupReconcileEmbedDepth::test_embed_startup_leaves_no_vectorless_documents"
        status: pass
    human_judgment: false
  - id: D2
    description: "BM25-only depth is unchanged: same IncrementalIndexer.update_collection pass, fresh checksum, zero chunk/vector writes, and no embedding-model construction"
    verification:
      - kind: unit
        ref: "tests/unit/cli/test_watch_cmd.py#TestStartupReconcileEmbedDepth::test_bm25_startup_writes_no_vectors_and_never_loads_model"
        status: pass
    human_judgment: false
  - id: D3
    description: "The worker's existing embed-aware reconcile still rewrites purged vectors; _run_reconcile defaults keep worker behaviour"
    verification:
      - kind: unit
        ref: "tests/unit/indexing/test_watcher.py#TestEmbedDepth::test_reconcile_at_embed_depth_rewrites_purged_vectors"
        status: pass
      - kind: unit
        ref: "pytest tests/unit/cli/test_watch_cmd.py tests/unit/indexing/test_watcher.py --no-cov (86 passed)"
        status: pass
    human_judgment: false
  - id: D4
    description: "Daemon and installed-service hosts inherit the fix because they execute run_watch_host verbatim; the reordered host still arms, watches, and shuts down"
    verification:
      - kind: e2e
        ref: "pytest tests/integration/test_watch_e2e.py tests/integration/test_watch_daemon_e2e.py --no-cov (12 passed)"
        status: pass
    human_judgment: false
  - id: D5
    description: "Repo quality contract stays green: ruff check, ruff format --check, full pytest with the 90% coverage gate, three-file scope"
    verification:
      - kind: other
        ref: "ruff check src tests && ruff format --check src tests && pytest -q (1607 passed, 1 skipped, 95.20% coverage); git status --porcelain -- src tests clean"
        status: pass
    human_judgment: false

duration: 8min
completed: 2026-11-12
status: complete
---

# Quick Task 261112-qtn: Fix `sif watch --embed` startup reconcile

**An embed-depth watch startup now re-embeds every document its pre-observer BM25 pass changed, so changed documents can never be left invisible to vector search; BM25-only startup is byte-behaviour unchanged.**

## Performance

- **Duration:** ~8 min
- **Started:** 2026-11-12T11:43:00Z (approx, after the prior batch item's commit)
- **Completed:** 2026-11-12T11:52:00Z (approx)
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments

- Added public `FileWatcher.reconcile_now(collection, *, progress=None, on_wait=None)` in `src/sif/indexing/watcher.py`; it delegates to the existing `_run_reconcile` embed-aware logic (IN-04 shape) — no duplicated checksum-diff/embed code.
- Extended `_run_reconcile` with keyword-only `progress`/`on_wait` overrides. `cb = progress if progress is not None else self._config.on_event`; `on_wait` is passed to the existing per-DB `index_lock`. The before-snapshot, `_changed_since`, and embed-leg logic are otherwise unchanged, and `_run_burst` / `_run_job` / `_EmbedSession` / `start` / `enqueue_reconcile` are untouched.
- `run_watch_host` now constructs the `FileWatcher` before the D-03 startup loop and runs each collection's pre-observer pass through `watcher.reconcile_now(...)`, passing the CLI's `_render_index_event` progress callback and the existing "Another index writer is running" `on_wait` notice; `watcher.start()` still runs after all collections reconcile. At embed depth, the pass's BM25 leg purges and the same lock window's embed leg rewrites the vectors.
- Removed the now-unused `index_lock` and `IncrementalIndexer` imports from `watch.py` and updated the module docstring to state the startup pass is embed-aware at embed depth.
- Added two CLI-level tests on a real `FileWatcher` (Observer mocked, park loop stopped by the captured SIGTERM handler): the embed-depth regression and the BM25 parity pin.

## Task Commits

Each task was committed atomically (code and tests only):

1. **Task 1 RED: pin embed-depth startup reconcile and BM25 parity** - `f4c18ca` (test)
2. **Task 1 GREEN: route watch startup reconcile through embed-aware seam** - `7dae754` (feat)
3. **Task 2: full quality gate and scope conformance** - no commit (verification-only, no edits)

**Plan metadata:** not committed by this executor — the quick-batch orchestrator commits SUMMARY/PLAN artifacts (ADR-1239 single-writer invariant).

_Note: Task 1 carried `tdd="true"`; per the canonical TDD commit-scope contract the RED was committed as `test(...)` before the `feat(...)` GREEN. Sibling quick items used one combined commit per task; the two-commit shape is a strict superset of the atomic requirement and matches the GSD TDD gate grep._

## Files Created/Modified

- `src/sif/indexing/watcher.py` - added `reconcile_now`; extended `_run_reconcile` with keyword-only `progress`/`on_wait` overrides and the `cb` resolution.
- `src/sif/cli/commands/watch.py` - moved `FileWatcher` construction before the startup loop; replaced the direct `IncrementalIndexer` + `index_lock` block with `watcher.reconcile_now(...)`; dropped the unused imports; updated the module docstring and extended the D-03 comment.
- `tests/unit/cli/test_watch_cmd.py` - added `_embed_manager_mock` plus `TestStartupReconcileEmbedDepth` (stale-vector-less seed helper, park-loop helper, embed regression, BM25 parity pin); restored the autouse hermetic-logging fixture decorator accidentally dropped during insertion.

## Decisions Made

- The startup pass reuses `_run_reconcile` verbatim (delegation), so the startup and worker reconcile paths cannot drift apart.
- The CLI progress renderer and flock waiting notice ride the new keyword-only overrides instead of changing the watcher's configured callbacks, keeping worker paths byte-identical.
- `FileWatcher` construction moved before the loop (still before `start()`), so the same instance reconciles then owns the worker. Construction creates no thread or observer.
- No backfill for documents already vector-less with fresh checksums — `sif index embed` remains the catch-up path, per plan.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Restored the autouse fixture decorator dropped while inserting the helper**
- **Found during:** Task 1 GREEN (ruff format pass)
- **Issue:** Inserting the `_embed_manager_mock` helper replaced the text that included `@pytest.fixture(autouse=True)`, silently turning the module's hermetic-logging fixture into a plain function (its isolation would no longer apply).
- **Fix:** Restored the decorator above `_hermetic_sif_logging`; the fixture is autouse again. Formatting was also accepted from `ruff format`.
- **Files modified:** `tests/unit/cli/test_watch_cmd.py`
- **Commit:** `7dae754`

### Plan-Intent Preserved

- The embed-depth regression test fails at HEAD exactly on the planned assertion (`assert vectorless == []`, one remaining `sqlite3.Row`), not on a fixture error.
- The BM25 parity test passes at HEAD and after the fix.
- The "fresh checksum" assertion uses `MarkdownParser().parse(...).checksum` because python-frontmatter strips trailing whitespace; whole-file hashing would compare against the wrong body.

## Issues Encountered

- Fresh factory connections use `sqlite3.Row`; count assertions were switched from tuple equality to `fetchone()[0]`.
- The first chosen "fresh checksum" proof (a second BM25 pass reporting `unchanged`) is invalid because `IncrementalIndexer.update_collection` never populates `unchanged` (it returns added/updated/removed/failed only); replaced with the parser checksum comparison before capturing RED evidence.
- `ruff format` reflowed the new test helper/asserts; `ruff format --check` clean afterwards.

## User Setup Required

None - no configuration, service, or external dependency change. The embedding model still loads only when depth is explicitly `embed`.

## Verification Evidence

- **RED (before production edit):** `pytest tests/unit/cli/test_watch_cmd.py::TestStartupReconcileEmbedDepth -q --no-cov` → 1 failed, 1 passed. `test_embed_startup_leaves_no_vectorless_documents` failed at `assert vectorless == []` with `Left contains one more item: <sqlite3.Row ...>`; `test_bm25_startup_writes_no_vectors_and_never_loads_model` passed.
- **GREEN:** `pytest tests/unit/cli/test_watch_cmd.py tests/unit/indexing/test_watcher.py -q --no-cov` → 86 passed; `test_reconcile_at_embed_depth_rewrites_purged_vectors` passed.
- **Full suite:** `pytest -q` → 1607 passed, 1 skipped, 95.20% coverage (fail_under 90 reached).
- **Real-subprocess e2e:** `pytest tests/integration/test_watch_e2e.py tests/integration/test_watch_daemon_e2e.py -q --no-cov` → 12 passed.
- **Lint/format:** `ruff check src tests` and `ruff format --check src tests` clean.
- **Scope:** `git status --porcelain -- src tests` empty; `git diff --name-only 94099ef..HEAD` lists exactly the three declared files.
- **Generator-owned docs:** `docs/cli-reference.md` and `docs/configuration.md` untouched (no docs change needed for this internal behaviour fix).

## Next Phase Readiness

`sif watch --embed` startup now leaves a fully vectorized index for its changed documents. Daemon and installed-service hosts inherit the fix because they execute `run_watch_host` verbatim. No follow-on work required.

---

*Quick task: 261112-qtn*
*Completed: 2026-11-12*

## Self-Check: PASSED

- SUMMARY.md and the three modified files all present.
- Commits `f4c18ca` (RED) and `7dae754` (GREEN) both ancestors of HEAD; `f4c18ca` touches only the test file, `7dae754` touches the two sources plus the test file.
- Working tree clean under `src/` and `tests/`; no sibling batch work touched or reverted.
