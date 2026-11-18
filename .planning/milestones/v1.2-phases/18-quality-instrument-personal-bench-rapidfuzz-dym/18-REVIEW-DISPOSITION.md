---
phase: 18
review: 18-REVIEW.md
titles: json
findings:
  - id: CR-01
    severity: critical
    disposition: fixed
    title: "Reserved-prefix titles/body/replay queries abort the entire eval"
  - id: WR-01
    severity: warning
    disposition: fixed
    title: "`-n/--limit` accepts zero and negative values — unbounded retrieval and self-invalid saved runs"
  - id: WR-02
    severity: warning
    disposition: fixed
    title: "The saved-run writer never validates what it writes; the CLI can produce runs its own loader refuses"
  - id: WR-03
    severity: warning
    disposition: fixed
    title: "`RecursionError` from a deeply nested saved-run file escapes as a traceback"
  - id: WR-04
    severity: warning
    disposition: fixed
    title: "The replay leg bypasses the `SIF_QUERY_HISTORY_ENABLED=0` read opt-out"
  - id: WR-05
    severity: warning
    disposition: fixed
    title: "Saved runs contain literal document-body text, contradicting the “never contains document content” guarantee"
  - id: WR-06
    severity: warning
    disposition: fixed
    title: "The noise gate can warrant a defaults change from one query, below its own displayed noise floor"
  - id: WR-07
    severity: warning
    disposition: fixed
    title: "`retrieval: \"hybrid\"` is reported without verifying the index has any vectors"
  - id: WR-08
    severity: warning
    disposition: fixed
    title: "The overlap budget is blind to CJK title echoes"
  - id: WR-09
    severity: warning
    disposition: fixed
    title: "Several failure paths escape the CLI's `ClickException` contract as raw tracebacks"
  - id: WR-10
    severity: warning
    disposition: fixed
    title: "The remote-provider disclosure omits replay history (and title/body provenance)"
  - id: IN-01
    severity: info
    disposition: open
    title: "Docs claim the model-identity mismatch is recorded in the comparison JSON; only stderr carries it"
  - id: IN-02
    severity: info
    disposition: open
    title: "Docs say suppressed group names go to stderr; the fresh table prints them to stdout"
  - id: IN-03
    severity: info
    disposition: open
    title: "The saved-run path is not markup-escaped on stderr"
  - id: IN-04
    severity: info
    disposition: open
    title: "Dead/phantom code in the new modules"
  - id: IN-05
    severity: info
    disposition: open
    title: "The document-frequency tie-break in `_close_matches` is unreachable"
  - id: IN-06
    severity: info
    disposition: open
    title: "User-facing report text references an internal planning artifact"
  - id: IN-07
    severity: info
    disposition: open
    title: "`prefix_completions(prefix, n=0)` returns one completion"
  - id: IN-08
    severity: info
    disposition: open
    title: "Replay stability can be computed from a tiny subset and is displayed without N"
  - id: IN-09
    severity: info
    disposition: open
    title: "Architecture layering claim is stale after `personal_bench.py`"
  - id: IN-10
    severity: info
    disposition: open
    title: "Test battery gaps leave the stated edges unpinned"
  - id: IN-11
    severity: info
    disposition: open
    title: "`load_document_metadata` claims it cannot materialize the corpus, but it does"
open: 11
total: 22
recorded: 2026-11-14T16:21:50.449Z
---

# Phase 18: Code Review Disposition

| Finding | Severity | Disposition | Source |
|---------|----------|-------------|--------|
| CR-01 | critical | fixed | 18-REVIEW-FIX.md |
| WR-01 | warning | fixed | 18-REVIEW-FIX.md |
| WR-02 | warning | fixed | 18-REVIEW-FIX.md |
| WR-03 | warning | fixed | 18-REVIEW-FIX.md |
| WR-04 | warning | fixed | 18-REVIEW-FIX.md |
| WR-05 | warning | fixed | 18-REVIEW-FIX.md |
| WR-06 | warning | fixed | 18-REVIEW-FIX.md |
| WR-07 | warning | fixed | 18-REVIEW-FIX.md |
| WR-08 | warning | fixed | 18-REVIEW-FIX.md |
| WR-09 | warning | fixed | 18-REVIEW-FIX.md |
| WR-10 | warning | fixed | 18-REVIEW-FIX.md |
| IN-01 | info | open | - |
| IN-02 | info | open | - |
| IN-03 | info | open | - |
| IN-04 | info | open | - |
| IN-05 | info | open | - |
| IN-06 | info | open | - |
| IN-07 | info | open | - |
| IN-08 | info | open | - |
| IN-09 | info | open | - |
| IN-10 | info | open | - |
| IN-11 | info | open | - |

Dispositions: `open` (recorded, not yet triaged), `fixed`, `skipped`, `deferred`.
Set `deferred` by hand and put the reason in the Source cell; both are preserved. A `|` in the reason is kept as prose and escaped on the next run.
Re-running the gate keeps every row it can. A row the current review no longer reports is kept and its Source cell flagged, so a finding does not leave this record silently. ONE exception: when a finding id is REUSED by a different finding, the earlier decision cannot keep a row — the id is taken — and it is dropped. A RECORDED decision (anything but `open`) is named on the console when that happens; a row still at `open` is replaced silently, because `open` records no decision to lose.
