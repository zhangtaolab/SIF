---
phase: 10
review: 10-REVIEW.md
titles: json
findings:
  - id: CR-01
    severity: critical
    disposition: open
    title: "Legacy direct-DELETE triggers not migrated in schema.py:148-163,188-191,236-242,261-267 — deleted content remains searchable on legacy DBs"
  - id: CR-02
    severity: critical
    disposition: open
    title: "XML-forbidden control characters not stripped in cli/commands/search.py:104-121 — title containing \\x0b produces non-well-formed XML"
  - id: WR-01
    severity: warning
    disposition: open
    title: "CLI Database instances not closed (search.py and other real-CLI paths) — SQLite ResourceWarnings in full-suite output"
open: 3
total: 3
recorded: 2026-11-05T20:44:00Z
---

# Phase 10: Code Review Disposition

| Finding | Severity | Disposition | Source |
|---------|----------|-------------|--------|
| CR-01 | critical | open | - |
| CR-02 | critical | open | - |
| WR-01 | warning | open | - |

Dispositions: `open` (recorded, not yet triaged), `fixed`, `skipped`, `deferred`.
Set `deferred` by hand and put the reason in the Source cell; both are preserved. A `|` in the reason is kept as prose and escaped on the next run.
