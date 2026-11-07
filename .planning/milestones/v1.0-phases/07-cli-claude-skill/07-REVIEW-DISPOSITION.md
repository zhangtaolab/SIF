---
phase: 07
review: 07-REVIEW.md
titles: json
findings:
  - id: CR-01
    severity: critical
    disposition: fixed
    title: "Document content printed through Rich markup — silent token consumption, MarkupError crash on unmatched tags, batch abort"
  - id: CR-02
    severity: critical
    disposition: fixed
    title: "--lines/--from-line/--line-numbers silently ignored on the disk-fallback path"
  - id: WR-01
    severity: warning
    disposition: fixed
    title: "Cargo-culted --line-numbers in sif-search JSON templates (always empty without --full)"
  - id: WR-02
    severity: warning
    disposition: open
    title: "--from-line numbering restarts at 1 — agents will cite wrong absolute line numbers"
  - id: WR-03
    severity: warning
    disposition: fixed
    title: "Double-quoted {query}/{path} interpolation with no shell-escaping guidance"
  - id: WR-04
    severity: warning
    disposition: fixed
    title: "No untrusted-content guard for retrieved doc text flowing into the LLM loop"
  - id: WR-05
    severity: warning
    disposition: fixed
    title: "Error-handling covers single-get only; multi-get no-match semantics undocumented"
  - id: IN-01
    severity: info
    disposition: fixed
    title: "-q claim copied from search skill — get/multi-get never read the quiet flag"
  - id: IN-02
    severity: info
    disposition: open
    title: "Bare-filename matching nondeterminism, cwd-relative resolution, Collection: UUID all undocumented"
  - id: IN-03
    severity: info
    disposition: open
    title: "Incomplete JSON field list; snippet is null on the BM25 path"
open: 3
total: 10
recorded: 2026-11-07T00:30:00.000Z
---

# Phase 07: Code Review Disposition

| Finding | Severity | Disposition | Source |
|---------|----------|-------------|--------|
| CR-01 | critical | fixed | fix commit c52f489 — markup=False at all three content-print sites; 2 regression tests (TestMarkupLiteralContent); live-verified literal render |
| CR-02 | critical | fixed | fix commit c52f489 — fallback applies the same line filtering/numbering contract; regression test + live-verified |
| WR-01 | warning | fixed | fix commit c52f489 — --line-numbers removed from sif-search JSON templates |
| WR-02 | warning | open | - |
| WR-03 | warning | fixed | fix commit c52f489 — single-quote interpolation guidance added to both skills |
| WR-04 | warning | fixed | fix commit c52f489 — untrusted-content contract in both skills (also closes P07-T01) |
| WR-05 | warning | fixed | fix commit c52f489 — multi-get no-match (stdout, exit 0) and === headers documented |
| IN-01 | info | fixed | fix commit c52f489 — -q semantics corrected in sif-get |
| IN-02 | info | open | - |
| IN-03 | info | open | - |

Dispositions: `open` (recorded, not yet triaged), `fixed`, `skipped`, `deferred`.

Set `deferred` by hand and put the reason in the Source cell; both are preserved.
