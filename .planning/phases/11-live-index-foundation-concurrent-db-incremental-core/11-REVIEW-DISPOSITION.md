---
phase: 11
review: 11-REVIEW.md
titles: json
findings:
  - id: WR-01
    severity: warning
    disposition: open
    title: "FileWatcher leaks/orphans observers in multi-collection use — stop() is ineffective per collection"
  - id: WR-02
    severity: warning
    disposition: open
    title: "DatabaseConnection.execute()/executemany() return a cursor from an already-closed connection"
  - id: WR-03
    severity: warning
    disposition: open
    title: "update_cmd/embed_cmd let user-facing init_schema errors escape as raw tracebacks"
  - id: WR-04
    severity: warning
    disposition: open
    title: "Impossible-state guard — `if not coll: continue` in both collection loops"
  - id: IN-01
    severity: info
    disposition: open
    title: "Dead variable `doc_chunks_map` in embed_cmd"
  - id: IN-02
    severity: info
    disposition: open
    title: "Progress bar over-advances — the \"scan\" event both sets the total and advances"
  - id: IN-03
    severity: info
    disposition: open
    title: "Database lazy schema-init logic triplicated"
  - id: IN-04
    severity: info
    disposition: open
    title: "Already-defended-elsewhere — PRAGMA busy_timeout duplicates the connect-time timeout"
  - id: IN-05
    severity: info
    disposition: open
    title: "Valid model-type set duplicated between CLI choice list and Settings validator"
open: 9
total: 9
recorded: 2026-11-07T07:13:46.338Z
---

# Phase 11: Code Review Disposition

| Finding | Severity | Disposition | Source |
|---------|----------|-------------|--------|
| WR-01 | warning | open | - |
| WR-02 | warning | open | - |
| WR-03 | warning | open | - |
| WR-04 | warning | open | - |
| IN-01 | info | open | - |
| IN-02 | info | open | - |
| IN-03 | info | open | - |
| IN-04 | info | open | - |
| IN-05 | info | open | - |

Dispositions: `open` (recorded, not yet triaged), `fixed`, `skipped`, `deferred`.
Set `deferred` by hand and put the reason in the Source cell; both are preserved. A `|` in the reason is kept as prose and escaped on the next run.
Re-running the gate keeps every row it can. A row the current review no longer reports is kept and its Source cell flagged, so a finding does not leave this record silently. ONE exception: when a finding id is REUSED by a different finding, the earlier decision cannot keep a row — the id is taken — and it is dropped. A RECORDED decision (anything but `open`) is named on the console when that happens; a row still at `open` is replaced silently, because `open` records no decision to lose.
