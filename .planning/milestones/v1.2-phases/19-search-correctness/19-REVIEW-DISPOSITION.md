---
phase: 19
review: 19-REVIEW.md
titles: json
findings:
  - id: WR-01
    severity: warning
    disposition: fixed
    title: "The Unreleased changelog says `query --min-score` \"keeps its behaviour\" and then says the exact-score fix reaches its BM25 leg"
  - id: IN-01
    severity: info
    disposition: fixed
    title: "The conversion correction says subtract-from-1 holds for `search search` only, but a BM25-only `query` route behaves the same way"
  - id: IN-07
    severity: info
    disposition: open
    title: "Relaxed title assertions lost their lower bound, and the `...` check is not about the title"
  - id: IN-08
    severity: info
    disposition: open
    title: "`symlink_or_skip` turns any `OSError` into a host-capability skip, so a broken fixture is skipped, not failed"
  - id: IN-09
    severity: info
    disposition: fixed
    title: "`--min-score` drops a row whose displayed score equals the threshold"
  - id: IN-10
    severity: info
    disposition: fixed
    title: "`sif query --min-score` filters each leg on its own scale and never the displayed score"
  - id: IN-11
    severity: info
    disposition: fixed
    title: "No test pins that a markup-bearing path renders literally in the per-chunk Chunk cell"
  - id: IN-12
    severity: info
    disposition: fixed
    title: "No test pins the score map in `search_chunks`, the one line 19-12 changed there"
  - id: CR-01
    severity: critical
    disposition: fixed
    title: "FTS title migration is not durable — the rebuild is rolled back while its DDL is committed"
  - id: CR-02
    severity: critical
    disposition: fixed
    title: "A non-string frontmatter `title` aborts the entire index update with a raw traceback"
  - id: WR-02
    severity: warning
    disposition: fixed
    title: "`-n/--limit` accepts zero/negative values with three different behaviors"
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
    title: "Migration tests never reopen the database, so rebuild rollbacks are invisible"
  - id: IN-05
    severity: info
    disposition: deferred
    title: "BM25Searcher.search_chunks applies min_score after LIMIT/OFFSET and never numbers ranks globally"
  - id: IN-06
    severity: info
    disposition: deferred
    title: "MCP backend silently creates an empty index at a nonexistent SIF_DB_PATH"
open: 2
total: 16
recorded: 2026-11-27T11:55:56.000Z
---

# Phase 19: Code Review Disposition

| Finding | Severity | Disposition | Source |
|---------|----------|-------------|--------|
| WR-01 | warning | fixed | 19-UAT.md test 18 (docs/changelog.md scoped per the review's suggested wording) |
| IN-01 | info | fixed | 19-UAT.md test 18 (docs/changelog.md scoped per the review's suggested wording) |
| IN-07 | info | open | - (not in the current review) |
| IN-08 | info | open | - (not in the current review) |
| IN-09 | info | fixed | 19-UAT.md test 8; plan 19-13 (exact-threshold predicate) |
| IN-10 | info | fixed | 19-UAT.md test 9; plan 19-14 (per-leg help texts) |
| IN-11 | info | fixed | 19-UAT.md test 10; plan 19-15 (markup-bearing Chunk-cell guard) |
| IN-12 | info | fixed | 19-UAT.md test 10; plan 19-15 (`search_chunks` score-map guard) |
| CR-01 | critical | fixed | 19-REVIEW-FIX.md (not in the current review) |
| CR-02 | critical | fixed | 19-REVIEW-FIX.md (not in the current review) |
| WR-02 | warning | fixed | 19-REVIEW-FIX.md (not in the current review) |
| IN-02 | info | deferred | out of dispatch scope (not in the current review) |
| IN-03 | info | deferred | out of dispatch scope (not in the current review) |
| IN-04 | info | fixed | 19-REVIEW-FIX.md (not in the current review) |
| IN-05 | info | deferred | out of dispatch scope (not in the current review) |
| IN-06 | info | deferred | out of dispatch scope (not in the current review) |

Dispositions: `open` (recorded, not yet triaged), `fixed`, `skipped`, `deferred`.
Set `deferred` by hand and put the reason in the Source cell; both are preserved. A `|` in the reason is kept as prose and escaped on the next run.
Re-running the gate keeps every row it can. A row the current review no longer reports is kept and its Source cell flagged, so a finding does not leave this record silently. ONE exception: when a finding id is REUSED by a different finding, the earlier decision cannot keep a row — the id is taken — and it is dropped. A RECORDED decision (anything but `open`) is named on the console when that happens; a row still at `open` is replaced silently, because `open` records no decision to lose.

Incremental re-review 2026-11-27 (docs/changelog.md after commit 5268218): 0 findings — status clean. WR-01 and IN-01 are confirmed fixed and no row changed; the two rows still `open` (IN-07, IN-08) were not in this review's scope and keep their dispositions. IN-09 to IN-12 were refreshed to `fixed` from this round's UAT tests 8-10 and plans 19-13 to 19-15.
