---
phase: 16
review: 16-REVIEW.md
titles: json
findings:
  - id: CR-01
    severity: critical
    disposition: open
    title: "Bench soft-fail warnings print to stdout and corrupt `--json` output"
  - id: WR-01
    severity: warning
    disposition: open
    title: "Deleted `class TestMachineOutputNoWrap:` header silently merges two test classes"
  - id: WR-02
    severity: warning
    disposition: open
    title: "Snapshot-lock fixture reads real environment variables — non-hermetic against `SIF_RRF_K`/`SIF_BM25_WEIGHT`/`SIF_VECTOR_WEIGHT`"
  - id: WR-03
    severity: warning
    disposition: open
    title: "`--check` drift gate does not detect unexpected files outside `corpus/**/*.md`, but `docs/benchmarking.md` claims it does"
  - id: IN-01
    severity: info
    disposition: open
    title: "`_sort_and_build_results` drops `vectors_stale` when rebuilding SearchResult"
  - id: IN-02
    severity: info
    disposition: open
    title: "Stray class docstring inside `TestCrossEncoderRerankerLoad` (pre-existing)"
  - id: IN-03
    severity: info
    disposition: open
    title: "`Qwen3Reranker.load` duplicates the whole model-loading body across quiet/non-quiet branches (pre-existing)"
  - id: IN-04
    severity: info
    disposition: open
    title: "Benchmarking doc gaps: grade-1 legend missing; `SIF_RERANK_ENABLED=1` implied to enable bench rerank state"
open: 8
total: 8
recorded: 2026-11-08T16:02:15.234Z
---

# Phase 16: Code Review Disposition

| Finding | Severity | Disposition | Source |
|---------|----------|-------------|--------|
| CR-01 | critical | open | - |
| WR-01 | warning | open | - |
| WR-02 | warning | open | - |
| WR-03 | warning | open | - |
| IN-01 | info | open | - |
| IN-02 | info | open | - |
| IN-03 | info | open | - |
| IN-04 | info | open | - |

Dispositions: `open` (recorded, not yet triaged), `fixed`, `skipped`, `deferred`.
Set `deferred` by hand and put the reason in the Source cell; both are preserved. A `|` in the reason is kept as prose and escaped on the next run.
Re-running the gate keeps every row it can. A row the current review no longer reports is kept and its Source cell flagged, so a finding does not leave this record silently. ONE exception: when a finding id is REUSED by a different finding, the earlier decision cannot keep a row — the id is taken — and it is dropped. A RECORDED decision (anything but `open`) is named on the console when that happens; a row still at `open` is replaced silently, because `open` records no decision to lose.
