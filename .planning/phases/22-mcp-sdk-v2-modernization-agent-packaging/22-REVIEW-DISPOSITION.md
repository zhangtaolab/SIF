---
phase: 22
review: 22-REVIEW.md
titles: json
findings:
  - id: CR-01
    severity: critical
    disposition: fixed
    title: "Lazy embedder fast path treats \"load in progress\" as \"load failed\""
  - id: CR-02
    severity: critical
    disposition: fixed
    title: "`vec_search` performed the lazy model load on the event loop"
  - id: WR-01
    severity: warning
    disposition: fixed
    title: "Fallback snippet line windows counted phantom trailing lines"
  - id: WR-02
    severity: warning
    disposition: fixed
    title: "`get` fabricated lines past EOF and reported ranges its truncated content did not cover"
  - id: WR-03
    severity: warning
    disposition: fixed
    title: "Non-finite metadata diverged between text and structured channels"
  - id: WR-05
    severity: warning
    disposition: fixed
    title: "Partial transport-security overrides dropped the recorded allowlist"
  - id: WR-06
    severity: warning
    disposition: fixed
    title: "Search skill documented an invalid filter AST (`op` instead of `operator`)"
  - id: WR-07
    severity: warning
    disposition: fixed
    title: "MCP rerank ignored `SIF_RERANK_CANDIDATE_LIMIT`"
  - id: WR-08
    severity: warning
    disposition: fixed
    title: "Embedded watch host ignored injected settings and schema dimension"
  - id: WR-09
    severity: warning
    disposition: fixed
    title: "`docs://` resource advertised path lookup it cannot perform"
  - id: WR-10
    severity: warning
    disposition: fixed
    title: "`docs://` accepted non-positive line parameters and silently sliced wrong"
  - id: WR-11
    severity: warning
    disposition: fixed
    title: "Reranker construction was an unlocked check-then-act"
open: 0
total: 12
unparsed: 21
recorded: 2026-11-16T10:15:51.250Z
---

# Phase 22: Code Review Disposition

| Finding | Severity | Disposition | Source |
|---------|----------|-------------|--------|
| CR-01 | critical | fixed | 22-REVIEW-FIX.md (not in the current review) |
| CR-02 | critical | fixed | 22-REVIEW-FIX.md (not in the current review) |
| WR-01 | warning | fixed | 22-REVIEW-FIX.md (not in the current review) |
| WR-02 | warning | fixed | 22-REVIEW-FIX.md (not in the current review) |
| WR-03 | warning | fixed | 22-REVIEW-FIX.md (not in the current review) |
| WR-05 | warning | fixed | 22-REVIEW-FIX.md (not in the current review) |
| WR-06 | warning | fixed | 22-REVIEW-FIX.md (not in the current review) |
| WR-07 | warning | fixed | 22-REVIEW-FIX.md (not in the current review) |
| WR-08 | warning | fixed | 22-REVIEW-FIX.md (not in the current review) |
| WR-09 | warning | fixed | 22-REVIEW-FIX.md (not in the current review) |
| WR-10 | warning | fixed | 22-REVIEW-FIX.md (not in the current review) |
| WR-11 | warning | fixed | 22-REVIEW-FIX.md (not in the current review) |

Dispositions: `open` (recorded, not yet triaged), `fixed`, `skipped`, `deferred`.
Set `deferred` by hand and put the reason in the Source cell; both are preserved. A `|` in the reason is kept as prose and escaped on the next run.
Re-running the gate keeps every row it can. A row the current review no longer reports is kept and its Source cell flagged, so a finding does not leave this record silently. ONE exception: when a finding id is REUSED by a different finding, the earlier decision cannot keep a row — the id is taken — and it is dropped. A RECORDED decision (anything but `open`) is named on the console when that happens; a row still at `open` is replaced silently, because `open` records no decision to lose.
