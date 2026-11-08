---
phase: 14
review: 14-REVIEW.md
titles: json
findings:
  - id: CR-01
    severity: critical
    disposition: fixed
    title: "mtime-only drift never converges — every search re-locks, re-refreshes a no-op, and prints a false notice, forever"
  - id: WR-01
    severity: warning
    disposition: fixed
    title: "Drift refresh silently skips stored documents the shared predicate excludes — divergence from `sif index update` produces a second permanent drift loop"
  - id: WR-02
    severity: warning
    disposition: fixed
    title: "\"refreshed N files\" notice reports the pre-refresh drift count and discards the actual refresh result"
  - id: WR-03
    severity: warning
    disposition: open
    title: "LLM cache TTL written as naive local time, compared against aware-UTC ISO strings — TTL semantics broken in every non-UTC timezone"
  - id: WR-04
    severity: warning
    disposition: open
    title: "`vsearch`/`query` crash with a raw RuntimeError traceback when sqlite-vec is absent (ClickException convention violated)"
  - id: IN-01
    severity: info
    disposition: open
    title: "Duplicated mid-function `quiet` recomputation in `search_cmd` and `query_cmd`"
  - id: IN-02
    severity: info
    disposition: open
    title: "Unknown `-c` collection names are silently dropped; an all-unknown `-c` list yields \"No results found\" with no diagnostic"
open: 4
total: 7
recorded: 2026-11-08T04:34:04.053Z
---

# Phase 14: Code Review Disposition

| Finding | Severity | Disposition | Source |
|---------|----------|-------------|--------|
| CR-01 | critical | fixed | 14-REVIEW-FIX.md |
| WR-01 | warning | fixed | 14-REVIEW-FIX.md |
| WR-02 | warning | fixed | 14-REVIEW-FIX.md |
| WR-03 | warning | open | - |
| WR-04 | warning | open | - |
| IN-01 | info | open | - |
| IN-02 | info | open | - |

Dispositions: `open` (recorded, not yet triaged), `fixed`, `skipped`, `deferred`.
Set `deferred` by hand and put the reason in the Source cell; both are preserved. A `|` in the reason is kept as prose and escaped on the next run.
Re-running the gate keeps every row it can. A row the current review no longer reports is kept and its Source cell flagged, so a finding does not leave this record silently. ONE exception: when a finding id is REUSED by a different finding, the earlier decision cannot keep a row — the id is taken — and it is dropped. A RECORDED decision (anything but `open`) is named on the console when that happens; a row still at `open` is replaced silently, because `open` records no decision to lose.
