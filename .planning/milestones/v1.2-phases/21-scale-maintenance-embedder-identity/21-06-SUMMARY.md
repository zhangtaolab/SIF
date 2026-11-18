---
phase: 21-scale-maintenance-embedder-identity
plan: 06
subsystem: database
tags:
  [
    sqlite,
    vacuum,
    wal-checkpoint,
    online-backup,
    integrity-check,
    index-lock,
    maintenance,
    cleanup-reconcile,
    docs-generate,
    d-13,
    d-14,
  ]

# Dependency graph
requires:
  - phase: 21-scale-maintenance-embedder-identity
    plan: 02
    provides: "reconcile_embedded_documents helper + the derived shadow cleanup/vacuum repair"
  - phase: 21-scale-maintenance-embedder-identity
    plan: 05
    provides: "the streaming writer and CLI index group shape these commands extend"
provides:
  - "src/sif/database/maintenance.py - VacuumResult, BackupResult, MaintenanceBusyError, MaintenanceTargetError, vacuum_index, backup_index, _verify_backup, default_backup_path"
  - "sif index vacuum and sif index backup (CLI-only, index group)"
  - "sif cleanup reconciles embedded_documents inside its existing transaction"
  - "docs/cli-reference.md generated sections for both commands"
affects: [21-07, 22, 24]

# Actuals (#2632) - pairs with the plan's `estimate` (84000 tokens, 3 tasks).
actuals:
  tokens: 12133
  tasks: 3
  commits: 3
plan_head_before: d47c98ec0ac8d0d37061c25f678e88d5598e137a
plan_head_after: 9219da38b951c317d7af080b4677248ed597d944

tech-stack:
  added: []
  patterns:
    - "Maintenance runs on its own connection outside Database.transaction(); the CLI owns the flock so one wait notice covers the window"
    - "Busy/locked is a retryable typed error; target/integrity/OS failures are remedy-bearing typed errors, never partial success"
    - "Backup is Connection.backup on a fresh target connection + PRAGMA integrity_check; target validation precedes every connection"
    - "Conservative 2x (database + WAL) free-space precheck before VACUUM, naming required and available bytes"

key-files:
  created:
    - tests/unit/database/test_maintenance.py
    - tests/integration/test_maintenance.py
  modified:
    - src/sif/database/maintenance.py
    - src/sif/cli/commands/index.py
    - src/sif/cli/main.py
    - tests/unit/cli/test_index.py
    - tests/unit/cli/test_main.py
    - docs/cli-reference.md

key-decisions:
  - "vacuum_index measures (database + WAL) after the reconcile commit, checkpoints with TRUNCATE, prechecks 2x that measurement, then VACUUMs with conn.in_transaction asserted False at execute time."
  - "The final post-VACUUM checkpoint is best-effort: a busy result is logged as a warning because the rewrite already committed, while a busy first checkpoint is the retryable MaintenanceBusyError."
  - "backup_index validates the target before opening any connection (symlink checked before resolve, existing file, DB/WAL/SHM/lock collision, stale target sidecars) and refuses a missing source database."
  - "A backup/OS failure removes the just-created copy; an integrity failure keeps it for inspection and names both the copy path and the integrity rows. Busy/locked maps to the retryable error in both commands."
  - "The successful copy is chmod 0600; a chmod failure warns instead of failing because the snapshot itself is verified and durable."
  - "cleanup calls reconcile inside its existing db.transaction() and prints removed/added counts; no second transaction is introduced and a missing shadow/vec0 stays a no-op."

patterns-established:
  - "Maintenance helper contract: caller owns index_lock and transaction boundaries; the helper owns its connection and never commits the caller's work"
  - "Retryable vs target failure split (MaintenanceBusyError vs MaintenanceTargetError) translated to click.ClickException at the command boundary"

requirements-completed: [SCALE-01, SCALE-02, CORR-06]

coverage:
  - id: D1
    description: "vacuum_index reconciles the shadow, checkpoints TRUNCATE, enforces a 2x (db+WAL) free-space precheck with required/available bytes, runs VACUUM with no open transaction, and reports before/after/reclaimed sizes"
    requirement: SCALE-01
    verification:
      - kind: unit
        ref: "tests/unit/database/test_maintenance.py#TestVacuumIndex"
        status: pass
      - kind: integration
        ref: "tests/integration/test_maintenance.py#TestVacuumUnderConcurrentReader"
        status: pass
    human_judgment: false
  - id: D2
    description: "vacuum failures are retryable click.ClickException with no traceback; a concurrent reader either coexists or gets the documented retryable error and the database still passes integrity_check"
    requirement: SCALE-01
    verification:
      - kind: unit
        ref: "tests/unit/cli/test_index.py#TestVacuumCommand"
        status: pass
      - kind: integration
        ref: "tests/integration/test_maintenance.py#TestVacuumUnderConcurrentReader.test_reader_transaction_yields_success_or_retryable_error"
        status: pass
    human_judgment: false
  - id: D3
    description: "backup_index uses the SQLite online backup API on a fresh target connection, defaults under <db_dir>/backups/<stem>-<UTC stamp>.db, and refuses existing/symlink/DB/sidecar/lock/stale-sidecar targets before any copy"
    requirement: SCALE-02
    verification:
      - kind: unit
        ref: "tests/unit/database/test_maintenance.py#TestBackupTargetRefusals,TestDefaultBackupPath"
        status: pass
    human_judgment: false
  - id: D4
    description: "a backup copy passes PRAGMA integrity_check == [('ok',)], is mode 0600, contains the committed rows, and opens cleanly while writes continue; failures remove the partial copy or keep an integrity-failed copy with an explicit non-zero report"
    requirement: SCALE-02
    verification:
      - kind: unit
        ref: "tests/unit/database/test_maintenance.py#TestBackupIndex; tests/unit/cli/test_index.py#TestBackupCommand"
        status: pass
      - kind: integration
        ref: "tests/integration/test_maintenance.py#TestBackupUnderLiveWrites"
        status: pass
    human_judgment: false
  - id: D5
    description: "cleanup reconciles embedded_documents in its existing transaction: orphan vectors are removed without resurrecting a shadow row, missing markers for existing documents are inserted, and a vec0-free database succeeds as a no-op"
    requirement: CORR-06
    verification:
      - kind: unit
        ref: "tests/unit/cli/test_main.py#TestCleanupReconcile"
        status: pass
    human_judgment: false
  - id: D6
    description: "docs/cli-reference.md carries the generated index vacuum and index backup sections and a second make docs-generate leaves both generated docs byte-identical"
    requirement: SCALE-01
    verification:
      - kind: other
        ref: "make docs-generate && git diff --exit-code docs/cli-reference.md docs/configuration.md"
        status: pass
    human_judgment: false
  - id: D7
    description: "Full quality suite stays green with the configured coverage floor and no new runtime dependency"
    verification:
      - kind: other
        ref: "env -u FORCE_COLOR NO_COLOR=1 pytest (2721 passed, 1 skipped, 95.14%); ruff check; ruff format --check; ty check src/sif"
        status: pass
    human_judgment: false

duration: 8min
completed: 2026-11-16
status: complete
---

# Phase 21 Plan 06: Safe Vacuum, Verified Backup, and Cleanup Shadow Repair

**`sif index vacuum` reclaims space behind a flock, busy timeout, TRUNCATE checkpoint, and a 2x disk precheck; `sif index backup` takes a target-validated, integrity-checked online-API snapshot at 0600; cleanup reconciles the derived shadow in its existing transaction.**

## Performance

- **Duration:** 8 min
- **Started:** 2026-11-15T17:36:28Z
- **Completed:** 2026-11-15T17:44:19Z (2026-11-16 local)
- **Tasks:** 3
- **Files modified:** 8 (6 modified, 2 created)
- **Commits:** 3 task commits

## Accomplishments

- `vacuum_index` opens its own `create_connection` under the caller's `index_lock`, arms the configured busy timeout, asserts `conn.in_transaction is False`, reconciles the shadow in one short `with conn:` block, measures database + WAL, runs `PRAGMA wal_checkpoint(TRUNCATE)`, refuses below `2 * before` free bytes naming required and available counts, runs `VACUUM` outside any transaction, and attempts a best-effort final checkpoint. Busy first checkpoint/database maps to `MaintenanceBusyError`; OS/SQLite failures to `MaintenanceTargetError`.
- `sif index vacuum` opens and closes an initialized database first so migrations run, then takes `index_lock` with the shared waiting line, prints before/after/reclaimed bytes and MiB, and translates busy/target/sqlite/OS failures to `click.ClickException` (no traceback, no partial success).
- `backup_index` validates the target before any connection (symlink before resolve, existing file, DB/WAL/SHM/lock collision, stale target sidecars), refuses a missing source, creates the default `<db_dir>/backups` directory at 0700, copies with `Connection.backup` on a fresh target connection, verifies with `_verify_backup` (`PRAGMA integrity_check` must be exactly `[("ok",)]`), chmods 0600, and returns `BackupResult`. A backup/OS failure removes the just-created copy; an integrity failure keeps it and names the copy plus the integrity rows.
- `sif index backup [--output PATH]` prints the resolved output path and size; the default target is `<db_dir>/backups/<stem>-<UTC timestamp>.db`.
- `sif cleanup` now calls `reconcile_embedded_documents(conn)` inside its existing `db.transaction()` block after the orphan-embedding delete, printing `Reconciled embedded-document markers: N removed, M added`. A document deleted without a vector purge leaves orphan vec0 rows that cleanup removes without resurrecting a shadow row; a raw vec0 write that skipped the shadow is repaired; a vec0-free database stays a no-op through the swallowed `OperationalError` and the helper's table probe.
- `docs/cli-reference.md` was regenerated by `make docs-generate` (never hand-edited); the two commands appear as `index vacuum` and `index backup`, and a second regeneration leaves both generated docs byte-identical.

## Task Commits

Each task was committed atomically:

1. **Task 1: End-to-end `sif index vacuum`** - `cd0871d` (feat)
2. **Task 2: End-to-end `sif index backup`** - `c5c8a2b` (feat)
3. **Task 3: Cleanup reconcile wiring and generated docs** - `9219da3` (feat)

**Plan metadata:** the final docs commit captures this SUMMARY plus STATE/ROADMAP/REQUIREMENTS updates.

## Files Created/Modified

- `src/sif/database/maintenance.py` - `MaintenanceBusyError`, `MaintenanceTargetError`, `VacuumResult`, `BackupResult`, `_set_busy_timeout`, `_index_bytes`, `vacuum_index`, `default_backup_path`, `_validate_backup_target`, `_verify_backup`, `_discard_backup`, `_copy_with_online_backup`, `_finalize_backup_copy`, `backup_index`.
- `src/sif/cli/commands/index.py` - `index vacuum` / `index backup` commands, `_format_bytes`, lock-and-translate boundaries.
- `src/sif/cli/main.py` - cleanup reconcile call and marker-count output line.
- `tests/unit/database/test_maintenance.py` (new) - vacuum result/precheck/busy/transaction battery and backup refusal/integrity/permissions/failure battery.
- `tests/integration/test_maintenance.py` (new) - concurrent-reader vacuum and live-writer backup integration.
- `tests/unit/cli/test_index.py` - vacuum and backup CLI output/error tests.
- `tests/unit/cli/test_main.py` - cleanup reconcile orphan/insertion/vec0-free battery.
- `docs/cli-reference.md` - generated `index vacuum` and `index backup` sections.

## Decisions Made

- **Measurement point:** the disk precheck uses the post-reconcile (database + WAL) size measured immediately before the checkpoint, exactly the scale the plan specifies; the result's `reclaimed_bytes` is always `before - after`.
- **Final checkpoint is advisory:** a busy post-VACUUM checkpoint only logs a warning because the rewrite is already durable; a busy pre-VACUUM checkpoint is the retryable failure.
- **Missing source is a target error:** `backup_index` refuses a nonexistent database instead of letting `create_connection` create an empty one (Rule 2 validation).
- **Integrity-failure retention:** the copy is kept and the message includes both the resolved copy path and the raw integrity rows, so an operator can never mistake it for a valid backup.
- **Target checks precede connections:** symlink detection happens before `resolve()` so a symlinked target cannot be laundered into a normal path.
- **No new transaction in cleanup:** reconcile composes into the existing `db.transaction()` block and the `OperationalError` swallow remains only around the vec0 delete.
- **Test double seam:** `sqlite3.Connection.backup` is an immutable C method, so the forced-failure test patches `maintenance.create_connection` with a failing source double instead.

## Deviations from Plan

None - plan executed exactly as written. The only mid-task refactor was extracting `_copy_with_online_backup`/`_finalize_backup_copy` to satisfy the project's `mccabe` complexity limit of 10 for `backup_index`; behavior and tests are exactly the plan's contract.

## Issues Encountered

- `backup_index` initially exceeded the ruff `C901` complexity limit (11 > 10); the copy and finalize steps were extracted into private helpers with no behavioral change.
- The CLI backup output test needed `COLUMNS=200` because Rich wraps the long resolved temp path; the assertion now checks the unwrapped path.
- `tests/unit/cli/test_main.py`'s first shadow-count helper used a plain `sqlite3.connect`, which cannot read vec0 tables; it now uses `create_connection` (sqlite-vec loaded).

## User Setup Required

None - no external service configuration required. No runtime dependency was added (`pyproject.toml`/`uv.lock` untouched).

## Verification

- Per-task gates:
  - `env -u FORCE_COLOR NO_COLOR=1 pytest tests/unit/database/test_maintenance.py -x -k vacuum --no-cov` - 5 passed.
  - `env -u FORCE_COLOR NO_COLOR=1 pytest tests/integration/test_maintenance.py -x -k vacuum --no-cov` - 1 passed.
  - `env -u FORCE_COLOR NO_COLOR=1 pytest tests/unit/database/test_maintenance.py -x -k backup --no-cov` - 15 passed.
  - `env -u FORCE_COLOR NO_COLOR=1 pytest tests/integration/test_maintenance.py -x -k backup --no-cov` - 1 passed.
  - `env -u FORCE_COLOR NO_COLOR=1 pytest tests/unit/cli/test_main.py -x --no-cov` - 26 passed.
- Plan verification subset: `pytest tests/unit/database/test_maintenance.py tests/unit/cli/test_index.py tests/unit/cli/test_main.py tests/integration/test_maintenance.py -x --no-cov` - 68 passed.
- `ruff check src tests` clean; `ruff format --check src tests` - 218 files already formatted; `ty check src/sif` - all checks passed.
- Full suite: `env -u FORCE_COLOR NO_COLOR=1 pytest` - **2721 passed, 1 skipped**, coverage **95.14%** (fail_under=90).
- Docs gate: `make docs-generate && git diff --exit-code docs/cli-reference.md docs/configuration.md` - clean after staging the generated output; `docs/configuration.md` unchanged.
- Grep gates: `command("vacuum")` = 1, `def vacuum_index` = 1, `command("backup")` = 1, `def backup_index` = 1, `reconcile_embedded_documents` in `cli/main.py` = 2, `index vacuum` in `docs/cli-reference.md` >= 1.
- Prohibitions:
  - Backup is `Connection.backup` on a fresh target connection; a source scan test asserts no `shutil.copy` and no `VACUUM INTO` token in the module.
  - VACUUM asserts `conn.in_transaction is False` and a recording test observes `in_transaction` False at the `VACUUM` execute; `Database.transaction()` is never called by the maintenance path.
  - The low-disk precheck has no bypass flag and raises with required and available byte counts before VACUUM.
  - No MCP tool was registered or modified; only the Click `index` group changed.
  - A failed backup unlinks the just-created target; an integrity failure keeps it with an explicit non-zero report.

## Known Stubs

None.

## Threat Flags

None - no security-relevant surface beyond the plan's `<threat_model>` was introduced. T-21-19 (backup target disclosure) is mitigated by the target refusals + 0600/0700 modes; T-21-20 (live-database tampering) by flock + busy timeout + checkpoint + online backup + integrity_check; T-21-21 (disk exhaustion) by the 2x precheck; T-21-22 (shadow resurrection) by the join-to-documents reconcile and the cleanup orphan test.

## Next Phase Readiness

- 21-07's byte-identical/legacy gate can run against the maintenance surface unchanged; `cleanup` now repairs the shadow, so legacy fixtures reconcile identically.
- Phase 22 owns any MCP exposure of `vacuum`/`backup`; the helpers are presentation-free and the CLI holds the lock, so an MCP host can reuse them with its own error translation.
- Residual accepted risk: VACUUM's temporary database may live on `SQLITE_TMPDIR` on a different filesystem; its disk-full error is mapped to a remedy-bearing ClickException rather than prevented.

## Self-Check: PASSED

- FOUND: src/sif/database/maintenance.py
- FOUND: tests/unit/database/test_maintenance.py
- FOUND: tests/integration/test_maintenance.py
- FOUND: cd0871d
- FOUND: c5c8a2b
- FOUND: 9219da3
