---
phase: 17
review: 17-REVIEW.md
titles: json
findings:
  - id: CR-01
    severity: critical
    disposition: fixed
    title: "Windows smoke has no platform guard — an accidental POSIX run installs a persistent launchd/systemd service and forks a daemon"
  - id: WR-01
    severity: warning
    disposition: fixed
    title: "Shared progress renderer passes user data through Rich markup unescaped — silent text loss and `MarkupError` crashes"
  - id: WR-02
    severity: warning
    disposition: open
    title: "CI documentation states the opposite of the workflow this phase added"
  - id: WR-03
    severity: warning
    disposition: open
    title: "Docs still describe test infrastructure deleted by this phase"
  - id: WR-04
    severity: warning
    disposition: fixed
    title: "`examples/quickstart.py` is broken at runtime and prints commands that do not exist"
  - id: WR-05
    severity: warning
    disposition: fixed
    title: "Documented local quality gates fail on a clean checkout"
  - id: WR-06
    severity: warning
    disposition: open
    title: "Publish jobs have no job-level `timeout-minutes`"
  - id: WR-07
    severity: warning
    disposition: open
    title: "Publish workflow has no concurrency guard"
  - id: WR-08
    severity: warning
    disposition: fixed
    title: "`sif watch --stop` can crash with `PermissionError` instead of failing closed"
  - id: WR-09
    severity: warning
    disposition: open
    title: "Impossible-state guard — unreachable `if not coll: continue` in both index commands"
  - id: IN-01
    severity: info
    disposition: open
    title: "New CI guards assert text, not the properties their names claim"
  - id: IN-02
    severity: info
    disposition: open
    title: "The documentation command guard is blind to most top-level commands and lists a nonexistent group"
  - id: IN-03
    severity: info
    disposition: open
    title: "Stale counts and a stale \"search models\" claim remain in the docs"
  - id: IN-04
    severity: info
    disposition: open
    title: "Release-path inputs are not reproducible or hard-pinned"
  - id: IN-05
    severity: info
    disposition: open
    title: "No automated gate ties the published tag to a green Test Matrix run"
  - id: IN-06
    severity: info
    disposition: open
    title: "`--embed` and `--no-embed` together are accepted; embed silently wins"
open: 11
total: 16
recorded: 2026-11-14T10:12:13Z
---

# Phase 17: Code Review Disposition

| Finding | Severity | Disposition | Source |
|---------|----------|-------------|--------|
| CR-01 | critical | fixed | fix b0d45bf |
| WR-01 | warning | fixed | fix b0d45bf |
| WR-02 | warning | open | - |
| WR-03 | warning | open | - |
| WR-04 | warning | fixed | fix b0d45bf |
| WR-05 | warning | fixed | fix b0d45bf |
| WR-06 | warning | open | - |
| WR-07 | warning | open | - |
| WR-08 | warning | fixed | fix b0d45bf |
| WR-09 | warning | open | - |
| IN-01 | info | open | - |
| IN-02 | info | open | - |
| IN-03 | info | open | - |
| IN-04 | info | open | - |
| IN-05 | info | open | - |
| IN-06 | info | open | - |

Dispositions: `open` (recorded, not yet triaged), `fixed`, `skipped`, `deferred`.
Set `deferred` by hand and put the reason in the Source cell; both are preserved. A `|` in the reason is kept as prose and escaped on the next run.
Re-running the gate keeps every row it can. A row the current review no longer reports is kept and its Source cell flagged, so a finding does not leave this record silently. ONE exception: when a finding id is REUSED by a different finding, the earlier decision cannot keep a row — the id is taken — and it is dropped. A RECORDED decision (anything but `open`) is named on the console when that happens; a row still at `open` is replaced silently, because `open` records no decision to lose.
