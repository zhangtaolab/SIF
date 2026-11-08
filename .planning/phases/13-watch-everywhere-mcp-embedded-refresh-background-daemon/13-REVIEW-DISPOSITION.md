---
phase: 13
review: 13-REVIEW.md
titles: json
findings:
  - id: WR-01
    severity: warning
    disposition: fixed
    title: "`write_pid_file` uses a process-shared temp name — concurrent detaches race on the same inode"
  - id: IN-01
    severity: info
    disposition: fixed
    title: "`_service_argv_tail` half-pins the depth — an unpinned BM25 install can still go embed in a divergent service environment"
  - id: CR-01
    severity: critical
    disposition: fixed
    title: "MCP HTTP transport crashes at startup — lifespan passed as invoked context manager, not a factory"
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
recorded: 2026-11-08T08:30:24.246Z
---

# Phase 13: Code Review Disposition

| Finding | Severity | Disposition | Source |
|---------|----------|-------------|--------|
| WR-01 | warning | fixed | 13-REVIEW-FIX.md |
| IN-01 | info | fixed | 13-REVIEW-FIX.md |
| CR-01 | critical | fixed | 13-REVIEW-FIX.md (not in the current review) |
| WR-02 | warning | fixed | 13-REVIEW-FIX.md (title truncated in fix report; verified: commit 8039a3e) (not in the current review) |
| WR-03 | warning | fixed | 13-REVIEW-FIX.md (not in the current review) |
| WR-04 | warning | fixed | 13-REVIEW-FIX.md (not in the current review) |
| IN-02 | info | fixed | 13-REVIEW-FIX.md (not in the current review) |
| IN-03 | info | fixed | 13-REVIEW-FIX.md (not in the current review) |
| IN-04 | info | fixed | 13-REVIEW-FIX.md (not in the current review) |

Dispositions: `open` (recorded, not yet triaged), `fixed`, `skipped`, `deferred`.
Set `deferred` by hand and put the reason in the Source cell; both are preserved. A `|` in the reason is kept as prose and escaped on the next run.
Re-running the gate keeps every row it can. A row the current review no longer reports is kept and its Source cell flagged, so a finding does not leave this record silently. ONE exception: when a finding id is REUSED by a different finding, the earlier decision cannot keep a row — the id is taken — and it is dropped. A RECORDED decision (anything but `open`) is named on the console when that happens; a row still at `open` is replaced silently, because `open` records no decision to lose.
