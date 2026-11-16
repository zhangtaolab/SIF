---
phase: 22
review: 22-REVIEW.md
titles: json
findings:
  - id: CR-01
    severity: critical
    disposition: open
    title: "Lazy embedder fast path treats \"load in progress\" as \"load failed\", silently degrading concurrent first queries"
  - id: CR-02
    severity: critical
    disposition: open
    title: "`vec_search` performs the synchronous lazy model load on the MCP event loop, freezing the whole server"
  - id: WR-01
    severity: warning
    disposition: open
    title: "Fallback snippet line windows count phantom trailing lines"
  - id: WR-02
    severity: warning
    disposition: open
    title: "`get` fabricates a line for past-EOF ranges and reports ranges its truncated content does not cover"
  - id: WR-03
    severity: warning
    disposition: open
    title: "Non-finite document metadata diverges between the text and structured channels"
  - id: WR-04
    severity: warning
    disposition: open
    title: "Impossible-state guard — reranker `ImportError` soft-degrade can never fire"
  - id: WR-05
    severity: warning
    disposition: open
    title: "Partial transport-security overrides drop the recorded allowlist and can silently widen origins"
  - id: WR-06
    severity: warning
    disposition: open
    title: "Shipped search skill documents an invalid filter AST (`op` instead of `operator`)"
  - id: WR-07
    severity: warning
    disposition: open
    title: "MCP rerank ignores `SIF_RERANK_CANDIDATE_LIMIT`, breaking the claimed CLI pipeline parity"
  - id: WR-08
    severity: warning
    disposition: open
    title: "Embedded watch host ignores injected settings and initializes its schema at the process dimension"
  - id: WR-09
    severity: warning
    disposition: open
    title: "`docs://` resource claims path retrieval it cannot perform, and claims full content it truncates"
  - id: WR-10
    severity: warning
    disposition: open
    title: "`docs://` resource accepts non-positive line parameters and silently returns the wrong slice"
  - id: WR-11
    severity: warning
    disposition: open
    title: "Reranker construction is an unlocked check-then-act, allowing duplicate model loads"
  - id: IN-01
    severity: info
    disposition: open
    title: "Dead private helper `_fallback_snippet`"
  - id: IN-02
    severity: info
    disposition: open
    title: "Unused `StatusInput` model"
  - id: IN-03
    severity: info
    disposition: open
    title: "`mcp_watch_lifespan` is no longer used by production code"
  - id: IN-04
    severity: info
    disposition: open
    title: "`sif/mcp/cli.py` module docstring contradicts its eager app import"
  - id: IN-05
    severity: info
    disposition: open
    title: "`multi_get` maps a valid `max_bytes=0` to the 100 KiB default"
  - id: IN-06
    severity: info
    disposition: open
    title: "Architecture introduction still names only four MCP tools"
  - id: IN-07
    severity: info
    disposition: open
    title: "Recorded transport policy is not applied by the exported server object"
  - id: IN-08
    severity: info
    disposition: open
    title: "`lex_search`/`vec_search` descriptions claim CLI matching but default collection scope differs"
open: 21
total: 21
recorded: 2026-11-16T10:16:24.030Z
---

# Phase 22: Code Review Disposition

| Finding | Severity | Disposition | Source |
|---------|----------|-------------|--------|
| CR-01 | critical | open | - |
| CR-02 | critical | open | - |
| WR-01 | warning | open | - |
| WR-02 | warning | open | - |
| WR-03 | warning | open | - |
| WR-04 | warning | open | - |
| WR-05 | warning | open | - |
| WR-06 | warning | open | - |
| WR-07 | warning | open | - |
| WR-08 | warning | open | - |
| WR-09 | warning | open | - |
| WR-10 | warning | open | - |
| WR-11 | warning | open | - |
| IN-01 | info | open | - |
| IN-02 | info | open | - |
| IN-03 | info | open | - |
| IN-04 | info | open | - |
| IN-05 | info | open | - |
| IN-06 | info | open | - |
| IN-07 | info | open | - |
| IN-08 | info | open | - |

Dispositions: `open` (recorded, not yet triaged), `fixed`, `skipped`, `deferred`.
Set `deferred` by hand and put the reason in the Source cell; both are preserved. A `|` in the reason is kept as prose and escaped on the next run.
Re-running the gate keeps every row it can. A row the current review no longer reports is kept and its Source cell flagged, so a finding does not leave this record silently. ONE exception: when a finding id is REUSED by a different finding, the earlier decision cannot keep a row — the id is taken — and it is dropped. A RECORDED decision (anything but `open`) is named on the console when that happens; a row still at `open` is replaced silently, because `open` records no decision to lose.
