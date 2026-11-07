---
phase: "11"
slug: "live-index-foundation-concurrent-db-incremental-core"
# status lifecycle: draft (seeded by plan-phase) → validated (set by validate-phase §6)
# audit-milestone §5.5 distinguishes NOT-VALIDATED (draft) from PARTIAL (validated + nyquist_compliant: false) (#2117)
status: draft
nyquist_compliant: true
wave_0_complete: false
created: "2026-11-07"
---

# Phase 11 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.0.3 (+ pytest-asyncio 1.4.0 for MCP async tests) |
| **Config file** | `pyproject.toml` `[tool.pytest.ini_options]` (testpaths=tests; addopts carry --cov=src/sif) |
| **Coverage gate** | `[tool.coverage.report] fail_under = 90` (suite at 1015 passed @ 96.20% today) |
| **Quick run command** | `env -u FORCE_COLOR NO_COLOR=1 pytest tests/unit/db -x` (subset; FORCE_COLOR quirk per project memory) |
| **Full suite command** | `env -u FORCE_COLOR NO_COLOR=1 pytest` (no xdist configured → subprocess tests serialize naturally, satisfying D-09) |
| **Estimated runtime** | full suite ~2-4 min including new subprocess tests |

---

## Sampling Rate

- **After every task commit:** Run `env -u FORCE_COLOR NO_COLOR=1 pytest <touched-area> -x` + `ruff check src tests` + `ruff format --check src tests`
- **After every plan wave:** Run `env -u FORCE_COLOR NO_COLOR=1 pytest` (full, includes subprocess tests) + `ty check src/sif`
- **Before `/gsd-verify-work`:** Full suite green (fail_under=90 honored with new tests inside the default run, per D-09)
- **Max feedback latency:** ~4 minutes (full suite)

---

## Per-Task Verification Map

Task IDs are assigned at planning; rows below are the requirement-level contract from 11-RESEARCH.md § Validation Architecture. The planner MUST map each plan task onto one or more of these rows.

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 11-01-T2 | 01 | 1 | LIVE-06 | — | Factory-created connections: busy_timeout=5000, journal_mode=wal, synchronous=NORMAL, foreign_keys=on | unit | `env -u FORCE_COLOR NO_COLOR=1 pytest tests/unit/database/test_factory.py -x` | ❌ W0 | ⬜ pending |
| 11-01-T3 | 01 | 1 | LIVE-06 | — | Readers (CLI + MCP DatabaseConnection) query during open BEGIN IMMEDIATE write txn, zero "database is locked" | integration | `env -u FORCE_COLOR NO_COLOR=1 pytest tests/integration/test_concurrency.py -x` | ❌ W0 | ⬜ pending |
| 11-01-T2, 11-01-T3 | 01 | 1 | LIVE-06 | — | Second writer waits busy_timeout then proceeds (short holder); WAL switch retries under contention | unit/integration | `env -u FORCE_COLOR NO_COLOR=1 pytest tests/unit/database/test_factory.py -k wal -x` | ❌ W0 | ⬜ pending |
| 11-01-T3 | 01 | 1 | LIVE-07 | T-11-01 (lock-file poisoning) | flock try-lock blocks while held, acquires after release within deadline, times out cleanly, released on holder SIGKILL; lock file 0600 | unit | `env -u FORCE_COLOR NO_COLOR=1 pytest tests/unit/database/test_locking.py -x` | ❌ W0 | ⬜ pending |
| 11-01-T1, 11-03-T2 | 01, 03 | 1, 3 | LIVE-07 | — | update_cmd/embed_cmd acquire lock; loser waits then runs own pass (parent holds/releases; child exit 0) | integration (subprocess) | `env -u FORCE_COLOR NO_COLOR=1 pytest tests/integration/test_two_writer_subprocess.py -x` | ❌ W0 | ⬜ pending |
| 11-01-T1 | 01 | 1 | LIVE-07/SC2 | — | Two `sif index update` on same collection: each file indexed exactly once, no duplicate embedding rows, both exit 0 | integration (subprocess) | `env -u FORCE_COLOR NO_COLOR=1 pytest tests/integration/test_two_writer_subprocess.py -k duplicate -x` | ❌ W0 | ⬜ pending |
| 11-02-T2 | 02 | 2 | SC3 | — | Index state identical before/after extraction (documents/chunks/FTS rows + CLI Added/Updated/Removed output) | integration (golden) | `env -u FORCE_COLOR NO_COLOR=1 pytest tests/integration/test_incremental_equivalence.py -x` | ❌ W0 | ⬜ pending |
| 11-02-T1 | 02 | 2 | SC3/D-04 | — | Per-file commit: mid-run failure keeps completed files, failed file not half-written | unit | `env -u FORCE_COLOR NO_COLOR=1 pytest tests/unit/indexing/test_incremental.py -x` | ❌ W0 | ⬜ pending |
| 11-03-T2 | 03 | 3 | SC4 | — | Full quality suite green | suite | `env -u FORCE_COLOR NO_COLOR=1 pytest && ruff check src tests && ruff format --check src tests && ty check src/sif` | ✅ | ⬜ pending |
| 11-03-T1, 11-03-T2 | 03 | 3 | D-07 | — | Retirement: ConnectionPool/duplicate DatabaseConnection/DocumentIndexer gone, exports updated, watcher repointed, dead tests removed | suite-level | `env -u FORCE_COLOR NO_COLOR=1 pytest tests/unit/database/test_factory.py -x` (import assertions) | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/unit/database/test_factory.py` — stubs for LIVE-06 (pragma audit + WAL retry)
- [ ] `tests/unit/database/test_locking.py` — stubs for LIVE-07 (flock semantics incl. holder-death)
- [ ] `tests/unit/indexing/test_incremental.py` — stubs for SC3/D-04 (IncrementalIndexer incl. per-file failure)
- [ ] `tests/integration/test_concurrency.py` — stubs for SC1 (in-suite multi-connection WAL/BUSY)
- [ ] `tests/integration/test_two_writer_subprocess.py` — stubs for SC2/D-08/D-09 (deterministic parent-holds-lock subprocess proofs)
- [ ] `tests/integration/test_incremental_equivalence.py` — stubs for SC3 (golden index-state comparison)
- [ ] Deletions: `tests/unit/indexing/test_indexer.py` (dead DocumentIndexer suite, ~660 lines), `TestConnectionPool` in `tests/unit/db/test_database.py:219-300`

Existing infrastructure covers the rest (pytest + coverage gate already active; no framework install needed).

---

## Manual-Only Verifications

All phase behaviors have automated verification. (Network-FS WAL degradation is handled by code paths tested via the wrong-mode row shape; no manual step required.)

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 4 min
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
