---
phase: 13
review: 13-REVIEW.md
titles: json
findings:
  - id: CR-01
    severity: critical
    disposition: fixed
    title: "MCP HTTP transport crashes at startup — lifespan passed as invoked context manager, not a factory"
  - id: WR-01
    severity: warning
    disposition: fixed
    title: "Shutdown WAL checkpoint bypasses the worker-liveness gate — can execute on the same sqlite connection as a still-live worker"
  - id: WR-02
    severity: warning
    disposition: fixed
    title: "Debouncer thread leaked on every missing-root disappear/return cycle (regression vs. the flat-list implementation)"
  - id: WR-03
    severity: warning
    disposition: fixed
    title: "`--install-service` drops `--no-embed` — an installed BM25 service can silently start embedding"
  - id: WR-04
    severity: warning
    disposition: fixed
    title: "Detach handshake timeout produces the \"silent maybe-detach\" SC2 explicitly forbids"
  - id: IN-01
    severity: info
    disposition: fixed
    title: "`SIF_LOCK_WAIT_TIMEOUT` missing from the generated configuration reference; multi-field validators annotated on only their first field"
  - id: IN-02
    severity: info
    disposition: fixed
    title: "Service-manager invocations have no timeout — a wedged launchctl/systemctl hangs the CLI forever"
  - id: IN-03
    severity: info
    disposition: fixed
    title: "`write_pid_file` follows a pre-planted symlink (hardening parity with `service._write_artifact`)"
  - id: IN-04
    severity: info
    disposition: fixed
    title: "`SESSION_MAX_AGE` is dead — sessions never expire by age"
open: 0
total: 9
recorded: 2026-11-08T00:17:24.207Z
---

# Phase 13: Code Review Disposition

| Finding | Severity | Disposition | Source |
|---------|----------|-------------|--------|
| CR-01 | critical | fixed | 13-REVIEW-FIX.md |
| WR-01 | warning | fixed | 13-REVIEW-FIX.md (title truncated in fix report; verified: commit e3156da) |
| WR-02 | warning | fixed | 13-REVIEW-FIX.md (title truncated in fix report; verified: commit 8039a3e) |
| WR-03 | warning | fixed | 13-REVIEW-FIX.md |
| WR-04 | warning | fixed | 13-REVIEW-FIX.md |
| IN-01 | info | fixed | 13-REVIEW-FIX.md |
| IN-02 | info | fixed | 13-REVIEW-FIX.md |
| IN-03 | info | fixed | 13-REVIEW-FIX.md |
| IN-04 | info | fixed | 13-REVIEW-FIX.md |

Dispositions: `open` (recorded, not yet triaged), `fixed`, `skipped`, `deferred`.
Set `deferred` by hand and put the reason in the Source cell; both are preserved.
