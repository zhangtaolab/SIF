---
phase: 16
review: 16-REVIEW.md
titles: json
findings:
  - id: IN-01
    severity: info
    disposition: open
    title: "`_sort_and_build_results` drops `vectors_stale` when rebuilding SearchResult (carried forward)"
  - id: IN-02
    severity: info
    disposition: open
    title: "Stray class docstring inside `TestCrossEncoderRerankerLoad` (carried forward, pre-existing)"
  - id: IN-03
    severity: info
    disposition: open
    title: "`Qwen3Reranker.load` duplicates the whole model-loading body across quiet/non-quiet branches (carried forward, pre-existing)"
  - id: IN-04
    severity: info
    disposition: open
    title: "Benchmarking doc gaps: grade-1 legend missing; `SIF_RERANK_ENABLED=1` implied to enable bench rerank state (carried forward)"
  - id: IN-05
    severity: info
    disposition: open
    title: "`bench` no-index warning prints to stdout and exits 0 — `--json` consumers get non-JSON stdout with a success exit code (new this review, pre-existing line)"
  - id: IN-06
    severity: info
    disposition: open
    title: "`query_cmd` reranker-unavailable degradation warning still targets stdout `console` (new this review, pre-existing line; currently unreachable in production)"
  - id: CR-01
    severity: critical
    disposition: fixed
    title: "Bench soft-fail warnings print to stdout and corrupt `--json` output"
  - id: WR-01
    severity: warning
    disposition: fixed
    title: "Deleted `class TestMachineOutputNoWrap:` header silently merges two test classes"
  - id: WR-02
    severity: warning
    disposition: fixed
    title: "Snapshot-lock fixture reads real environment variables — non-hermetic"
  - id: WR-03
    severity: warning
    disposition: fixed
    title: "`--check` drift gate does not detect unexpected files outside `corpus/**/*.md`"
open: 6
total: 10
recorded: 2026-11-08T16:35:58.063Z
---

# Phase 16: Code Review Disposition

| Finding | Severity | Disposition | Source |
|---------|----------|-------------|--------|
| IN-01 | info | open | - |
| IN-02 | info | open | - |
| IN-03 | info | open | - |
| IN-04 | info | open | - |
| IN-05 | info | open | - |
| IN-06 | info | open | - |
| CR-01 | critical | fixed | 16-REVIEW-FIX.iter2.md (not in the current review) |
| WR-01 | warning | fixed | 16-REVIEW-FIX.iter2.md (not in the current review) |
| WR-02 | warning | fixed | 16-REVIEW-FIX.iter2.md (not in the current review) |
| WR-03 | warning | fixed | 16-REVIEW-FIX.iter2.md (not in the current review) |

Dispositions: `open` (recorded, not yet triaged), `fixed`, `skipped`, `deferred`.
Set `deferred` by hand and put the reason in the Source cell; both are preserved. A `|` in the reason is kept as prose and escaped on the next run.
Re-running the gate keeps every row it can. A row the current review no longer reports is kept and its Source cell flagged, so a finding does not leave this record silently. ONE exception: when a finding id is REUSED by a different finding, the earlier decision cannot keep a row — the id is taken — and it is dropped. A RECORDED decision (anything but `open`) is named on the console when that happens; a row still at `open` is replaced silently, because `open` records no decision to lose.
