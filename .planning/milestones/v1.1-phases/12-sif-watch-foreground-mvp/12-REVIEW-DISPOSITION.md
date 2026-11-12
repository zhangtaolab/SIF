---
phase: 12
review: 12-REVIEW.md
titles: json
findings:
  - id: CR-01
    severity: critical
    disposition: fixed
    title: "stop() drains queued jobs after a timed-out worker join — two threads share one connection mid-transaction"
  - id: WR-01
    severity: warning
    disposition: fixed
    title: "Mid-burst embed failure aborts remaining candidates and strands those documents vector-less (checksum change-detection never retries)"
  - id: WR-02
    severity: warning
    disposition: fixed
    title: "Repeated `-c name` schedules duplicate watches and orphans a `_WatchState` entry"
  - id: IN-01
    severity: info
    disposition: open
    title: "Rich markup silently swallows bracketed text in event payloads"
  - id: IN-02
    severity: info
    disposition: open
    title: "Invalid settings surface as a raw pydantic traceback when `--index` is passed explicitly"
  - id: IN-03
    severity: info
    disposition: open
    title: "Generator-owned docs omit the watch exit-130 contract and the new validation rules"
  - id: IN-04
    severity: info
    disposition: open
    title: "Reconcile jobs at embed depth purge vectors without rewriting them — silent vector-coverage regression"
open: 0
total: 7
recorded: 2026-11-07T13:07:41.012717+00:00
---

# Phase 12: Code Review Disposition

| Finding | Severity | Disposition | Source |
|---------|----------|-------------|--------|
| CR-01 | critical | fixed | 12-REVIEW-FIX.md |
| WR-01 | warning | fixed | 12-REVIEW-FIX.md |
| WR-02 | warning | fixed | 12-REVIEW-FIX.md |
| IN | info | fixed | 12-REVIEW-FIX.md |
| IN | info | fixed | 12-REVIEW-FIX.md |
| IN | info | fixed | 12-REVIEW-FIX.md |
| IN | info | fixed | 12-REVIEW-FIX.md |

Dispositions: `open` (recorded, not yet triaged), `fixed`, `skipped`, `deferred`.
Set `deferred` by hand and put the reason in the Source cell; both are preserved.
