---
phase: 19-search-correctness
review: 19-REVIEW.md
titles: json
findings:
  - id: CR-01
    severity: critical
    disposition: fixed
    title: "FTS title migration is not durable — the rebuild is rolled back while its DDL is committed"
  - id: CR-02
    severity: critical
    disposition: fixed
    title: "Non-string frontmatter title crashes the whole index update"
  - id: WR-01
    severity: warning
    disposition: fixed
    title: "Convention migration never converges with a permanently unparseable file in scope"
  - id: WR-02
    severity: warning
    disposition: fixed
    title: "-n/--limit accepts zero/negative with three different behaviors"
  - id: IN-01
    severity: info
    disposition: deferred
    title: "Vector scores are L2-derived but converted/documented as cosine"
  - id: IN-02
    severity: info
    disposition: deferred
    title: "Rerank rebuild drops vectors_stale"
  - id: IN-03
    severity: info
    disposition: deferred
    title: "docs/benchmarking.md claims MCP vec_search per_chunk but the tool is unregistered"
  - id: IN-04
    severity: info
    disposition: fixed
    title: "Migration tests only assert on the same open connection and never reopen"
  - id: IN-05
    severity: info
    disposition: deferred
    title: "BM25Searcher.search_chunks applies min_score after LIMIT/OFFSET and never numbers ranks globally"
  - id: IN-06
    severity: info
    disposition: deferred
    title: "MCP backend silently creates an empty index at a nonexistent SIF_DB_PATH"
open: 6
total: 10
recorded: 2026-11-15T05:20:00Z
---

# Phase 19: Code Review Disposition

| Finding | Severity | Disposition | Source |
|---------|----------|-------------|--------|
| CR-01 | critical | fixed | 19-REVIEW-FIX.md (4546047) |
| CR-02 | critical | fixed | 19-REVIEW-FIX.md (a43296e) |
| WR-01 | warning | fixed | 19-REVIEW-FIX.md (dd0bfa5) |
| WR-02 | warning | fixed | 19-REVIEW-FIX.md (340546e) |
| IN-01 | info | deferred | out of dispatch scope |
| IN-02 | info | deferred | out of dispatch scope |
| IN-03 | info | deferred | out of dispatch scope |
| IN-04 | info | fixed | 19-REVIEW-FIX.md (4546047) |
| IN-05 | info | deferred | out of dispatch scope |
| IN-06 | info | deferred | out of dispatch scope |

Dispositions: `open` (recorded, not yet triaged), `fixed`, `skipped`, `deferred`.
The four Critical/Warning findings and the reopen-test gap (IN-04) were fixed in four atomic commits; the remaining Info findings are deferred with their reasons recorded in `19-REVIEW-FIX.md`.
