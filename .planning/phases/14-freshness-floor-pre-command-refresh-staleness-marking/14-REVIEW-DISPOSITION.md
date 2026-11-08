---
phase: 14
review: 14-REVIEW.md
titles: json
findings:
  - id: WR-01
    severity: warning
    disposition: open
    title: "Parse-failed drifted files never converge and their errors are silently swallowed — every search re-locks, re-fails, and prints \"refreshed 0 files (bm25) before search\" forever"
  - id: WR-02
    severity: warning
    disposition: open
    title: "`vsearch`/`query` crash with a raw RuntimeError traceback when sqlite-vec is absent (ClickException convention violated) — carried, re-verified unfixed"
  - id: IN-01
    severity: info
    disposition: open
    title: "Duplicated mid-function `quiet` recomputation in all three trio commands — carried, re-verified"
  - id: IN-02
    severity: info
    disposition: open
    title: "Unknown `-c` collection names are silently dropped; an all-unknown `-c` list yields \"No results found\" with no diagnostic — carried, re-verified"
  - id: CR-01
    severity: critical
    disposition: fixed
    title: "mtime-only drift never converges — every search re-locks, re-refreshes a no-op, and prints a false notice, forever"
  - id: WR-03
    severity: warning
    disposition: open
    title: "LLM cache TTL written as naive local time, compared against aware-UTC ISO strings — TTL semantics broken in every non-UTC timezone"
  - id: WR-04
    severity: warning
    disposition: open
    title: "`vsearch`/`query` crash with a raw RuntimeError traceback when sqlite-vec is absent (ClickException convention violated)"
open: 6
total: 7
recorded: 2026-11-08T05:09:12.146Z
---

# Phase 14: Code Review Disposition

| Finding | Severity | Disposition | Source |
|---------|----------|-------------|--------|
| WR-01 | warning | open | - |
| WR-02 | warning | open | - |
| IN-01 | info | open | - |
| IN-02 | info | open | - |
| CR-01 | critical | fixed | 14-REVIEW-FIX.md (not in the current review) |
| WR-03 | warning | open | - (not in the current review) |
| WR-04 | warning | open | - (not in the current review) |

Dispositions: `open` (recorded, not yet triaged), `fixed`, `skipped`, `deferred`.
Set `deferred` by hand and put the reason in the Source cell; both are preserved. A `|` in the reason is kept as prose and escaped on the next run.
Re-running the gate keeps every row it can. A row the current review no longer reports is kept and its Source cell flagged, so a finding does not leave this record silently. ONE exception: when a finding id is REUSED by a different finding, the earlier decision cannot keep a row — the id is taken — and it is dropped. A RECORDED decision (anything but `open`) is named on the console when that happens; a row still at `open` is replaced silently, because `open` records no decision to lose.
