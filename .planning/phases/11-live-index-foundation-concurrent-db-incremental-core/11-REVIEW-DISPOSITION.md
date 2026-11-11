---
phase: 11
review: 11-REVIEW.md
titles: json
findings:
  - id: WR-01
    severity: warning
    disposition: fixed
    title: "Worker tick is not exception-guarded — one tick exception permanently kills live indexing"
  - id: WR-02
    severity: warning
    disposition: fixed
    title: "stop() mutates and iterates worker-owned state before quiescing the worker — races the rescope diff"
  - id: IN-01
    severity: info
    disposition: fixed
    title: "Inert busy-check branch in `_checkpoint_if_idle`"
  - id: IN-02
    severity: info
    disposition: fixed
    title: "WAL-checkpoint PRAGMA constant triplicated across modules"
  - id: IN-03
    severity: info
    disposition: fixed
    title: "\"Bounded\" stop flush is not time-bounded at embed depth"
  - id: WR-03
    severity: warning
    disposition: open
    title: "update_cmd/embed_cmd let user-facing init_schema errors escape as raw tracebacks"
  - id: WR-04
    severity: warning
    disposition: open
    title: "Impossible-state guard — `if not coll: continue` in both collection loops"
  - id: IN-04
    severity: info
    disposition: fixed
    title: "WR-01/WR-02 concurrency fixes have no committed regression test"
  - id: IN-05
    severity: info
    disposition: open
    title: "Valid model-type set duplicated between CLI choice list and Settings validator"
open: 3
total: 9
recorded: 2026-11-11T04:45:14.148Z
---

# Phase 11: Code Review Disposition

| Finding | Severity | Disposition | Source |
|---------|----------|-------------|--------|
| WR-01 | warning | fixed | 11-REVIEW-FIX.md (not in the current review) |
| WR-02 | warning | fixed | 11-REVIEW-FIX.md (not in the current review) |
| IN-01 | info | fixed | 11-REVIEW-FIX.md (not in the current review) |
| IN-02 | info | fixed | 11-REVIEW-FIX.md (not in the current review) |
| IN-03 | info | fixed | 11-REVIEW-FIX.md (not in the current review) |
| WR-03 | warning | open | - (not in the current review) |
| WR-04 | warning | open | - (not in the current review) |
| IN-04 | info | fixed | 11-REVIEW-FIX.md (not in the current review) |
| IN-05 | info | open | - (not in the current review) |

Dispositions: `open` (recorded, not yet triaged), `fixed`, `skipped`, `deferred`.
Set `deferred` by hand and put the reason in the Source cell; both are preserved. A `|` in the reason is kept as prose and escaped on the next run.
Re-running the gate keeps every row it can. A row the current review no longer reports is kept and its Source cell flagged, so a finding does not leave this record silently. ONE exception: when a finding id is REUSED by a different finding, the earlier decision cannot keep a row — the id is taken — and it is dropped. A RECORDED decision (anything but `open`) is named on the console when that happens; a row still at `open` is replaced silently, because `open` records no decision to lose.
