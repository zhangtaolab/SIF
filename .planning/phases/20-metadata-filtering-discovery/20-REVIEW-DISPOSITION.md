---
phase: 20
review: 20-REVIEW.md
titles: json
findings:
  - id: CR-01
    severity: critical
    disposition: fixed
    title: "Typed metadata derivation is not total over JSON numbers — a single document aborts indexing and permanently bricks upgrades"
  - id: CR-02
    severity: critical
    disposition: fixed
    title: "`in` filters with 2+ operands duplicate result rows, corrupt pagination, and double-count RRF scores"
  - id: WR-01
    severity: warning
    disposition: fixed
    title: "Unbounded integer operands make the validator raise `OverflowError`, escaping the documented error contract"
  - id: WR-02
    severity: warning
    disposition: fixed
    title: "Compile-time filter rejections bypass the `ClickException` boundary, so reserved-field mistakes print tracebacks"
  - id: WR-03
    severity: warning
    disposition: fixed
    title: "Explicit `caseInsensitive: false` is treated as enabled and rejected"
  - id: WR-04
    severity: warning
    disposition: fixed
    title: "String elements of arrays bypass the 1024-character cap"
  - id: WR-05
    severity: warning
    disposition: fixed
    title: "Empty arrays are silently dropped — no rows, no skip, invisible to `exists` and discovery"
  - id: WR-06
    severity: warning
    disposition: fixed
    title: "Non-finite numbers reach `--json` and MCP output as invalid JSON"
  - id: WR-07
    severity: warning
    disposition: fixed
    title: "The default `collection metadata` table never reports `skippedKeys`"
  - id: IN-01
    severity: info
    disposition: open
    title: "Two operator-set constants are dead code"
  - id: IN-02
    severity: info
    disposition: open
    title: "`_collection_predicate` treats the exclude-all sentinel as \"no scope\""
  - id: IN-03
    severity: info
    disposition: open
    title: "Discovery window sizes have no upper bound"
  - id: IN-04
    severity: info
    disposition: open
    title: "`collection metadata --json` diverges from the established JSON output convention"
  - id: IN-05
    severity: info
    disposition: open
    title: "The half-populated-store rule has no read-side check"
open: 5
total: 14
recorded: 2026-11-15T14:05:00Z
---

# Phase 20: Code Review Disposition

| Finding | Severity | Disposition | Source |
|---------|----------|-------------|--------|
| CR-01 | critical | fixed |  20-REVIEW-FIX.md |
| CR-02 | critical | fixed |  20-REVIEW-FIX.md |
| WR-01 | warning | fixed |  20-REVIEW-FIX.md |
| WR-02 | warning | fixed |  20-REVIEW-FIX.md |
| WR-03 | warning | fixed |  20-REVIEW-FIX.md |
| WR-04 | warning | fixed |  20-REVIEW-FIX.md |
| WR-05 | warning | fixed |  20-REVIEW-FIX.md |
| WR-06 | warning | fixed |  20-REVIEW-FIX.md |
| WR-07 | warning | fixed |  20-REVIEW-FIX.md |
| IN-01 | info | open | - |
| IN-02 | info | open | - |
| IN-03 | info | open | - |
| IN-04 | info | open | - |
| IN-05 | info | open | - |

Dispositions: `open` (recorded, not yet triaged), `fixed`, `skipped`, `deferred`.
Set `deferred` by hand and put the reason in the Source cell; both are preserved. A `|` in the reason is kept as prose and escaped on the next run.
