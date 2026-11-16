---
phase: 23
review: 23-REVIEW.md
titles: json
findings:
  - id: CR-01
    severity: critical
    disposition: fixed
    title: "Cleanup guard accepts the home directory as a scratch root — data loss risk"
  - id: CR-02
    severity: critical
    disposition: fixed
    title: "Verdict stage can return a stale artifact after a full run"
  - id: WR-01
    severity: warning
    disposition: fixed
    title: "Non-idempotent `collection add` breaks documented resume and scope changes"
  - id: WR-02
    severity: warning
    disposition: fixed
    title: "Resume scope key ignores corpus content changes"
  - id: WR-03
    severity: warning
    disposition: fixed
    title: "Docs \"Held-out leg\" table mixes all-split and held-out gate values"
  - id: WR-04
    severity: warning
    disposition: fixed
    title: "Artifact writer cannot reproduce the committed artifact; a rerun drops `default_flip`"
  - id: WR-05
    severity: warning
    disposition: fixed
    title: "Inherited SIF fusion settings change the measured pipeline and are not recorded"
  - id: WR-06
    severity: warning
    disposition: fixed
    title: "Malformed comparison/payload JSON escapes as a traceback"
  - id: IN-01
    severity: info
    disposition: open
    title: "Saved-run path is interpolated into Rich markup unescaped"
  - id: IN-02
    severity: info
    disposition: open
    title: "Identity gate does not check the model revision"
  - id: IN-03
    severity: info
    disposition: fixed
    title: "`scripts/harrier_eval.py` is not ruff-clean or ruff-formatted"
  - id: IN-04
    severity: info
    disposition: open
    title: "Benchmarking docs do not mention `require-language`"
  - id: IN-05
    severity: info
    disposition: open
    title: "Stale zero-delta-proof sentence after the `keep-qwen3` verdict"
  - id: IN-06
    severity: info
    disposition: open
    title: "Cleanup leaves the Harrier saved run and comparison JSON behind"
open: 5
total: 14
recorded: 2026-11-16T15:19:42Z
---

# Phase 23: Code Review Disposition

| Finding | Severity | Disposition | Source |
|---------|----------|-------------|--------|
| CR-01 | critical | fixed | 23-REVIEW-FIX.md |
| CR-02 | critical | fixed | 23-REVIEW-FIX.md |
| WR-01 | warning | fixed | 23-REVIEW-FIX.md |
| WR-02 | warning | fixed | 23-REVIEW-FIX.md |
| WR-03 | warning | fixed | 23-REVIEW-FIX.md |
| WR-04 | warning | fixed | 23-REVIEW-FIX.md |
| WR-05 | warning | fixed | 23-REVIEW-FIX.md |
| WR-06 | warning | fixed | 23-REVIEW-FIX.md |
| IN-01 | info | open | - |
| IN-02 | info | open | - |
| IN-03 | info | fixed | 23-REVIEW-FIX.md |
| IN-04 | info | open | - |
| IN-05 | info | open | - |
| IN-06 | info | open | - |

Dispositions: `open` (recorded, not yet triaged), `fixed`, `skipped`, `deferred`.
2 Critical + 6 Warning fixed with regression tests; IN-03 (runbook ruff/format) fixed as a cleanup. IN-01/02/04/05/06 remain open Info findings.
