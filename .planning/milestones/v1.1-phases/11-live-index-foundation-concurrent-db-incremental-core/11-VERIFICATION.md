---
phase: 11-live-index-foundation-concurrent-db-incremental-core
verified: 2026-11-12T07:27:42Z
status: passed
score: 20/20 must-haves verified
covered_files: [".planning/phases/11-live-index-foundation-concurrent-db-incremental-core/11-01-PLAN.md", ".planning/phases/11-live-index-foundation-concurrent-db-incremental-core/11-01-SUMMARY.md", ".planning/phases/11-live-index-foundation-concurrent-db-incremental-core/11-02-PLAN.md", ".planning/phases/11-live-index-foundation-concurrent-db-incremental-core/11-02-SUMMARY.md", ".planning/phases/11-live-index-foundation-concurrent-db-incremental-core/11-03-PLAN.md", ".planning/phases/11-live-index-foundation-concurrent-db-incremental-core/11-03-SUMMARY.md", "src/sif/cli/commands/index.py", "src/sif/cli/commands/watch.py", "src/sif/cli/error_handling.py", "src/sif/config/settings.py", "src/sif/database/__init__.py", "src/sif/database/connection.py", "src/sif/database/database.py", "src/sif/database/factory.py", "src/sif/database/locking.py", "src/sif/indexing/incremental.py", "src/sif/indexing/watcher.py", "src/sif/mcp/watch_host.py", "tests/integration/test_concurrency.py", "tests/integration/test_incremental_equivalence.py", "tests/integration/test_two_writer_subprocess.py", "tests/unit/cli/test_collection.py", "tests/unit/cli/test_index.py", "tests/unit/cli/test_index_locking.py", "tests/unit/database/test_database.py", "tests/unit/database/test_factory.py", "tests/unit/database/test_locking.py", "tests/unit/db/test_database.py", "tests/unit/indexing/test_incremental.py", "tests/unit/indexing/test_watcher.py", "tests/unit/mcp/test_mcp_watch_host.py"]
covered_digest: "v4:sha256:a70341ba73af8789e63099f981c452bc297a9c197d9cb905f42a5e5bcb95fa21"
behavior_unverified: 0
overrides_applied: 0
re_verification:
  previous_status: passed
  previous_score: 20/20
  gaps_closed: [] # prior report had no gaps; this is a staleness regeneration after Phase 16.1 changed covered source
  gaps_remaining: []
  regressions: [] # pragma recipe and per-file transactions intact; enqueue_reconcile remains inside the worker's per-job flock
advisory: []
decision_coverage:
  honored: 9
  total: 9
  not_honored: []
---

# Phase 11: Live-Index Foundation (Concurrent DB + Incremental Core) Verification Report

**Phase Goal:** The database and indexing core can safely host a resident background writer — watch writes and CLI/MCP reads coexist without lock errors, and exactly one per-file incremental update path exists for all watch hosts to reuse.
**Verified:** 2026-11-12T07:27:42Z
**Status:** passed
**HEAD:** `0899d909d97f95fc9fa4b8c26b0717cb69e78e7c`
**Re-verification:** Yes — staleness regeneration. The previous report passed 20/20 at `e20ce25`; Phase 16.1 and related cleanup subsequently changed `factory.py`, `index.py`, `watch.py`, `incremental.py`, `watcher.py`, and `watch_host.py`. Every roadmap criterion and every merged plan truth was re-evaluated against HEAD rather than carried forward from the prior verdict.

## Goal Achievement

Must-haves were merged from the four ROADMAP success criteria plus all three plans' frontmatter truths, with duplicate checksum, empty-input, and scan-order items deduplicated: 8 truths from 11-01, 5 unique truths from 11-02, and 7 from 11-03 = 20. No overrides were used. All 13 implementation commits documented by the plans are valid commits at HEAD.

### Observable Truths

| # | Truth | Status | Evidence at HEAD `0899d90` |
|---|-------|--------|----------------------------|
| 1 | Every CLI `Database.connection` and MCP `DatabaseConnection._create_connection` reports busy_timeout=5000, WAL, synchronous=1, foreign_keys=1, isolation_level IMMEDIATE (SC1) | ✓ VERIFIED | `factory.py:56-73` is the sole `sqlite3.connect` site in `src/sif`; busy_timeout precedes the WAL helper and synchronous follows it. Both wrappers delegate (`database.py:28`, `connection.py:26`). `test_pragma_audit_on_every_connection` and `test_mcp_style_connection_inherits_factory_pragmas` passed. |
| 2 | CLI-style and MCP-style readers succeed while another connection holds an open BEGIN IMMEDIATE write transaction, with zero "database is locked" (SC1) | ✓ VERIFIED | `test_concurrency.py::TestReaderDuringWriter::test_cli_and_mcp_style_readers_succeed_during_open_write_txn` passed against real file-backed connections; it asserts both readers see the pre-commit snapshot and the committed row afterward. |
| 3 | Two simultaneous `sif index update` processes both exit 0; the loser waits then runs; files are indexed exactly once (SC2) | ✓ VERIFIED | `test_two_writer_subprocess.py` passed 3/3: a real CLI child remains blocked under the parent's flock, exits 0 after release, sequential updates leave exactly three unique paths, and WAL persists. D-02 wait-then-run is the locked interpretation of deferral. |
| 4 | `{db_path}.lock` is created next to the DB with mode 0600; a SIGKILLed holder releases immediately | ✓ VERIFIED | `locking.py:67-70` derives one canonical per-DB path and opens it 0600. All seven `test_locking.py` tests passed, including mode, contention, release, expiry, and holder-death behavior. |
| 5 | Checksum-equal files are skipped unless `--force`; a second update reports Added: 0 / Updated: 0 / Removed: 0 | ✓ VERIFIED | `incremental.py:300-318` implements checksum skip (with the later mtime-only convergence guarded inside the skip). Skip/force tests and `test_third_run_is_idempotent` passed; the idempotent snapshot preserves document and chunk state. |
| 6 | Empty input retains behavior: no-collections notice and exit 0; zero-file scans report zero counts | ✓ VERIFIED | `index.py:71-75` retains the notice/return. `test_empty_scan_reports_zero_counts` passed with `IncrementalResult(0, 0, 0)` and `scan 0`. |
| 7 | Processing follows FileScanner's existing scan order; output and index content remain deterministic | ✓ VERIFIED | `incremental.py:117-152` consumes `scan_result.files` directly without reordering. Golden add/mutate/idempotent CLI cycles passed with independently constructed fixture expectations. |
| 8 | Parallel SQLite writers wait inside busy_timeout; long jobs serialize through flock before DB contention | ✓ VERIFIED | `TestBusyTimeoutWait` and `TestThreadedInterleave` passed: the waiter completes only after release, and 40 interleaved writes finish without OperationalError. CLI update/embed and watcher write paths all call `index_lock`. |
| 9 | `sif index update` produces equivalent documents/chunks/FTS state and the same CLI counts after extraction (SC3) | ✓ VERIFIED | `test_incremental_equivalence.py` passed 3/3: first-run 3/0/0, mutation-run 1/1/1, third-run zeros, FTS/document parity, fresh checksums, stale-chunk purge, and deleted-document FTS removal. |
| 10 | Each file's document/chunk/FTS-trigger writes commit in one short BEGIN IMMEDIATE transaction; removal and stats have separate short transactions (D-04) | ✓ VERIFIED | `incremental.py:323-341` and `353-355` retain the per-file `with self._conn:` boundaries; `_remove_document` uses `381-384`; stats use `155-158` and `260-263`. The factory sets `isolation_level="IMMEDIATE"`. The 16.1 purger refactor changed only construction at `78-80`. |
| 11 | A mid-run failure keeps completed files durable and leaves the failing file not half-written | ✓ VERIFIED | `test_mid_run_failure_keeps_completed_files_durable` passed: a fresh connection sees only the first file, no failing-file rows, and no third-file work. |
| 12 | `update_cmd` contains no indexing loop, delegates to IncrementalIndexer, and has no complexity exemption | ✓ VERIFIED | `index.py:77-101` constructs one indexer and calls `update_collection`; `index.py` has no `parser.parse` or `noqa: C901, PLR0912, PLR0915` match. The separate pre-existing exemption on `embed_cmd` is unrelated. |
| 13 | Rich/console stays in the CLI; IncrementalIndexer is presentation-free and accepts a progress callback | ✓ VERIFIED | `incremental.py` has no rich/click imports; events flow through `_notify`. `index.py::_render_index_event` renders them. Direct core tests passed without CLI presentation. |
| 14 | Retired imports raise ImportError and `sif.database.__all__` contains only surviving names (D-07) | ✓ VERIFIED | `database/__init__.py:16-26` lists exactly nine names. All three `TestRetiredImports` tests passed; no `ConnectionPool`, `DocumentIndexer`, `IndexStatus`, or `IndexResult` reference remains in `src/sif`. |
| 15 | `src/sif/indexing/indexer.py` and its dead orchestrator/test suite are retired | ✓ VERIFIED | Both `src/sif/indexing/indexer.py` and `tests/unit/indexing/test_indexer.py` are absent. Source-wide retired-symbol grep returned no matches. |
| 16 | `watcher.py` uses IncrementalIndexer rather than the deleted class | ✓ VERIFIED | `watcher.py:36` imports the shared core; burst and reconcile paths call `update_paths` and `update_collection` at `838-843` and `826-828`. All 49 watcher tests passed. |
| 17 | `embed_cmd` uses the same per-DB flock around its collection loop, after model loading/dimension checks, without restructuring its transactions (D-01/D-05) | ✓ VERIFIED | `index.py:221-253` loads/checks the model before `index_lock` at `275-281`; per-collection `with db.connection:` remains at `320-362`. Both lock spy tests passed with one enter/release per command. |
| 18 | Concurrent update and embed serialize without BUSY failures; losers wait then proceed | ✓ VERIFIED | `test_index_locking.py` passed 5/5, including update/embed lock spies and held-lock update that waits, prints the notice, indexes its file, and exits 0. Kernel mutual exclusion is covered by `TestIndexLock`. |
| 19 | Dead pool/orchestrator tests are gone | ✓ VERIFIED | `tests/unit/db/test_database.py` has the planned 14 test methods and passed; `tests/unit/indexing/test_indexer.py` is absent. |
| 20 | Existing CLI/MCP behavior remains green under pytest fail_under=90, ruff, format, and ty (SC4) | ✓ VERIFIED | Independent HEAD run: 1590 passed, 1 skipped, coverage 95.18% (90% gate reached); `ruff check src tests`, `ruff format --check src tests` (190 files), and `ty check src/sif` all passed. |

**Score:** 20/20 truths verified (0 present-but-behavior-unverified).

Every behavior-dependent truth has current runtime evidence from the verifier's own 93-test focused run, the 15-test MCP watch-host run, and/or the single full-suite run. No verdict rests solely on symbol presence.

### Phase 16.1 Regression Review

| Change | Verification result |
|--------|---------------------|
| WR-01 close-on-setup-failure in `factory.py` (`46e259b`) | `factory.py:63-76` wraps the complete setup sequence and closes/reraises on BaseException. The pragma recipe remains foreign_keys → busy_timeout → WAL retry → synchronous → vec load. `test_post_connect_pragma_failure_closes_handle_and_reraises` passed and proves the underlying handle is actually closed. |
| Shared CLI DB opener adoption (`f54be6e`, `06020ab`) | `index.py:49` and watch openers still construct the same `Database`; `error_handling.py` only owns construction/schema initialization and closes on failures. It does not alter incremental or embed transaction bodies. |
| Shared embedding purger adoption (`c34a965`) | `incremental.py:78-80` delegates purger construction, while per-file writes, checksum skip, removal, and stats transactions remain in the same locations and passed their behavioral tests. |
| Public `enqueue_reconcile` (`8820965`, `64fc4f1`) | `watcher.py:525-537` only enqueues `(Collection, FoldResult(needs_reconcile=True))`; it performs no DB work. Worker `_run_job` dispatches reconcile to `_run_reconcile`, whose body is inside `index_lock` at `822-833`. MCP and internal producers use the public method. FIFO/payload and producer-routing tests passed. |

### Roadmap Success Criteria Mapping

| SC | Statement | Truths | Status |
|----|-----------|--------|--------|
| 1 | Concurrent writer + CLI/MCP reads complete with zero lock errors; pragma recipe and BEGIN IMMEDIATE | 1, 2, 8, 10 | ✓ VERIFIED |
| 2 | Two index writers arbitrate through flock without duplicated indexing/embedding | 3, 4, 17, 18 | ✓ VERIFIED |
| 3 | Identical update results; one shared IncrementalIndexer; update delegates; dead DocumentIndexer retired | 5, 7, 9-16 | ✓ VERIFIED |
| 4 | Existing CLI/MCP behavior unchanged; full quality suite green | 6, 20 | ✓ VERIFIED |

### Required Artifacts

`gsd-tools query verify.artifacts` returned `all_passed: true` for all plans: 7/7, 3/3, and 2/2.

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `src/sif/database/factory.py` | One shared connection factory | ✓ VERIFIED | 133 substantive lines; sole raw connection site; locked pragma order, WAL retry, vec swallow, close-on-setup-failure; wired to both wrappers. |
| `src/sif/database/locking.py` | Kernel-flock arbitration | ✓ VERIFIED | 98 lines; canonical per-DB 0600 file, wait deadline, expiry-to-yield, fd cleanup; used by CLI, watch, and drift writers. |
| `src/sif/config/settings.py` | `lock_wait_timeout` setting | ✓ VERIFIED | Field at `43-48`; live checks parsed `SIF_LOCK_WAIT_TIMEOUT=7.5` as 7.5 and unset as 30.0. |
| `src/sif/indexing/incremental.py` | Single per-file incremental core | ✓ VERIFIED | 384 lines; one class/loop, no presentation imports, shared by CLI and watcher; real scan and repository data. |
| `src/sif/database/__init__.py` | Final export surface | ✓ VERIFIED | Exactly nine surviving exports, including create_connection/index_lock and excluding ConnectionPool. |
| `tests/unit/database/test_factory.py` | Pragma/retry/degrade/close/export proofs | ✓ VERIFIED | 12 tests passed. |
| `tests/unit/database/test_locking.py` | flock semantics | ✓ VERIFIED | 7 tests passed on POSIX. |
| `tests/integration/test_concurrency.py` | SC1 real-connection proofs | ✓ VERIFIED | 4 tests passed. |
| `tests/integration/test_two_writer_subprocess.py` | SC2 real-CLI proofs | ✓ VERIFIED | 3 tests passed. |
| `tests/unit/indexing/test_incremental.py` | Incremental and durability proofs | ✓ VERIFIED | 10 tests passed. |
| `tests/integration/test_incremental_equivalence.py` | Golden equivalence | ✓ VERIFIED | 3 tests passed. |
| `tests/unit/cli/test_index_locking.py` | CLI lock and wait-then-run proofs | ✓ VERIFIED | 5 tests passed. |

Deleted artifacts confirmed absent: `src/sif/indexing/indexer.py`, `tests/unit/indexing/test_indexer.py`.

### Key Link Verification

`gsd-tools query verify.key-links` returned `all_verified: true` for all plans: 3/3, 2/2, and 2/2.

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `database/database.py` | `database/factory.py` | `Database.connection` | ✓ WIRED | `create_connection(self.db_path)` at line 28. |
| `database/connection.py` | `database/factory.py` | `_create_connection` | ✓ WIRED | Whole-body delegation at line 26. |
| `cli/commands/index.py` | `database/locking.py` | update and embed | ✓ WIRED | `index_lock` at lines 53 and 275. |
| `cli/commands/index.py` | `indexing/incremental.py` | update delegation | ✓ WIRED | Constructor at line 79; update call at 97. |
| `indexing/incremental.py` | factory-created connection | per-file `with self._conn` | ✓ WIRED | CLI and watcher supply Database/factory connections; transaction tests passed. |
| `indexing/watcher.py` | `indexing/incremental.py` | shared core | ✓ WIRED | Import and both update APIs present; 49 tests passed. |
| `mcp/watch_host.py` | `indexing/watcher.py` | public reconcile API | ✓ WIRED | `enqueue_reconcile` at line 100; start/enqueue ordering and FIFO payload tests passed. |

### Data-Flow Trace (Level 4)

This is an infrastructure phase; the equivalent trace follows real connections, files, and DB rows rather than rendered UI state.

| Artifact | Data variable | Source | Produces real data | Status |
|----------|---------------|--------|--------------------|--------|
| `factory.py` | `conn` | `sqlite3.connect(db_path)` plus pragmas | Real per-path SQLite connection; no fallback object | ✓ FLOWING |
| `incremental.py` | `scan_result`, `existing_docs` | `FileScanner.scan` and `DocumentRepository.list_by_collection` | Real filesystem and DB inputs | ✓ FLOWING |
| `index.py` update_cmd | added/updated/removed totals | `IncrementalIndexer.update_collection` results | Real run counts rendered in CLI block | ✓ FLOWING |
| `locking.py` | `lock_path` | Canonicalized caller DB path | One real per-DB lock file | ✓ FLOWING |
| `watcher.py` | reconcile jobs | Public enqueue → worker queue → locked core call | Real queued intents; no direct DB bypass | ✓ FLOWING |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Phase 11 and watcher behavioral regressions | `env -u FORCE_COLOR NO_COLOR=1 pytest <8 phase/watcher test files> --no-cov -q` | 93 passed in 7.26s | ✓ PASS |
| MCP watch-host and public reconcile behavior | `env -u FORCE_COLOR NO_COLOR=1 pytest tests/unit/mcp/test_mcp_watch_host.py -q --no-cov` | 15 passed in 0.11s | ✓ PASS |
| Full quality suite | `env -u FORCE_COLOR NO_COLOR=1 pytest` | 1590 passed, 1 skipped; 95.18% coverage; 90% gate reached | ✓ PASS |
| Lint and formatting | `ruff check src tests && ruff format --check src tests` | All checks passed; 190 files formatted | ✓ PASS |
| Type checking | `ty check src/sif` | All checks passed | ✓ PASS |
| Settings env/default | Live `Settings(_env_file=None)` construction | Override 7.5; default 30.0 | ✓ PASS |
| Retirement/loop/presentation greps | Source-wide symbol and import checks | No retired symbols, update parse loop, core UI imports, or autocommit connection | ✓ PASS |
| Plan artifact/link/commit verbs | `verify.artifacts`, `verify.key-links`, `verify.commits` | 12/12 artifacts, 7/7 links, 13/13 commits | ✓ PASS |

Environment note: PATH-based pytest was used per project convention; `env -u FORCE_COLOR NO_COLOR=1` kept the suite color-hermetic. The full workspace suite was run once.

### Probe Execution

No `scripts/*/tests/probe-*.sh` probes exist or are declared by the Phase 11 plans/SUMMARYs. The phase's proof mechanism is pytest, executed above. Not applicable.

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| LIVE-06 | 11-01, 11-02, 11-03 | Watch writes coexist with CLI/MCP reads without lock errors | ✓ SATISFIED | Truths 1, 2, 8, 10, 11; factory-only connection creation, real concurrent reader/writer tests, short per-file transactions. REQUIREMENTS.md maps it to Phase 11 Complete. |
| LIVE-07 | 11-01, 11-02, 11-03 | flock single-writer arbitration without duplicate index/embed work | ✓ SATISFIED | Truths 3, 4, 17, 18; per-DB flock on CLI and watch writers, wait-then-run proofs, unique-row assertions. REQUIREMENTS.md maps it to Phase 11 Complete. |

Orphaned requirements: none. The traceability matrix maps exactly LIVE-06 and LIVE-07 to Phase 11, and all three plans claim both.

### Prohibition Checks

| Prohibition | Status | Evidence |
|-------------|--------|----------|
| No autocommit `isolation_level=None` connection in `src/sif` | ✓ HELD | Only docstring mention; sole raw connect uses `isolation_level="IMMEDIATE"`. |
| WAL never precedes busy_timeout | ✓ HELD | `factory.py:68` busy_timeout precedes WAL calls at 69 and 102/114; no journal_mode pragma elsewhere. |
| No incremental write transaction across embedding inference | ✓ HELD | Core remains BM25-only; purger performs DML only. Embed command's pre-existing transaction shape is separately locked by D-05. |
| No PID-file/custom liveness scheme for index arbitration | ✓ HELD | `locking.py` uses only kernel flock and fd lifetime. |
| Lock waiter never silently drops work | ✓ HELD | Deadline breaks to yield; expiry and held-lock CLI tests passed. |
| No per-collection locks | ✓ HELD | Single canonical `{db}.lock` derivation. |
| No third incremental loop | ✓ HELD | CLI delegates; dead indexer deleted; only IncrementalIndexer implements update_collection/update_paths. |
| Embed per-collection transactions unchanged | ✓ HELD | Existing `with db.connection:` commit body remains; only opener/lock integration changed around it. |
| No new runtime dependencies | ✓ HELD | Changes use existing stdlib/project dependencies; no dependency file changed. |

### Test Quality Audit

| Test file | Linked req | Active | Skipped | Circular | Assertion level | Verdict |
|-----------|------------|--------|---------|----------|-----------------|---------|
| `test_factory.py` | LIVE-06 | 12 | 0 | No | Value + behavioral (pragma values, contention, real close) | OK |
| `test_locking.py` | LIVE-07 | 7 | 0 on POSIX | No | Behavioral (flock contention, release, death, expiry) | OK |
| `test_concurrency.py` | LIVE-06 | 4 | 0 | No | Behavioral + value (snapshots, elapsed wait, 40 rows) | OK |
| `test_two_writer_subprocess.py` | LIVE-07 | 3 | 0 | No | Behavioral (real CLI exit codes, unique DB rows, WAL) | OK |
| `test_incremental.py` | LIVE-06 | 10 | 0 here | No | Behavioral (fresh-connection durability, purge order, counts) | OK |
| `test_incremental_equivalence.py` | LIVE-06/07 | 3 | 0 | No | Value + behavioral (independent fixtures, FTS/chunk state) | OK |
| `test_index_locking.py` | LIVE-07 | 5 | 0 | No | Behavioral (lock entry, wait/proceed, persisted work) | OK |
| `test_watcher.py` | LIVE-07 reuse | 49 | 0 | No | Behavioral (worker/lock/reconcile invariants) | OK |
| `test_mcp_watch_host.py` | LIVE-07 reuse | 15 | 0 | No | Behavioral (startup order, public enqueue, queue payload) | OK |

**Disabled requirement tests:** 0. `pytest.importorskip("fcntl")` is a platform guard; this POSIX run executed all lock tests. The conditional sqlite-vec skip helper did not skip any test here.

**Circular patterns:** 0. Golden expectations derive from independently constructed fixture trees and direct DB assertions, not output generated by the system under test.

**Assertion strength:** Behavioral/value assertions cover the required state transitions, lock ordering, persistence, and counts; no requirement is supported only by existence/type assertions.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| None | — | No TBD/FIXME/XXX/TODO/HACK/PLACEHOLDER markers or stub implementations in covered production files | — | — |

### Decision Coverage

`check.decision-coverage-verify`: 9/9 trackable CONTEXT.md decisions honored; `not_honored: []`. Non-blocking informational gate.

### Advisory (New Scope, Unevidenced)

Re-verification ran; no new-scope unevidenced findings.

| # | Finding | Category | Why Advisory |
|---|---------|----------|--------------|
| — | None | — | — |

### Human Verification Required

N/A — Infrastructure/foundation phase with no user-facing UX requiring manual judgment. All behavior-dependent acceptance criteria have current passing automated evidence; none remains PRESENT_BEHAVIOR_UNVERIFIED, and no backstop-tagged truths exist.

### Gaps Summary

None. At HEAD `0899d90`, all 20 merged truths are verified, all 12 required artifacts are present/substantive/wired, all seven declared key links are wired, both requirements are satisfied, all nine prohibitions hold, and all 13 documented commits are valid. The Phase 16.1 factory cleanup preserves pragma order and adds proven close-on-failure behavior; opener adoption preserves transaction structure; `enqueue_reconcile` only queues work and cannot bypass the per-reconcile flock. Independent gates are green: 93 focused tests + 15 MCP tests, full suite 1590 passed/1 skipped at 95.18%, ruff/format/ty clean. The phase goal remains achieved.

---

_Verified: 2026-11-12T07:27:42Z_
_Verifier: Claude (gsd-verifier)_
