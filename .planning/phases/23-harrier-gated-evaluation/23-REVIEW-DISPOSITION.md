---
phase: 23
review: 23-REVIEW.md
titles: json
findings:
  - id: CR-01
    severity: critical
    disposition: fixed
    title: "Cleanup guard accepts the home directory as a scratch root"
  - id: CR-02
    severity: critical
    disposition: fixed
    title: "Verdict stage can return a stale artifact after a full run"
  - id: WR-01
    severity: warning
    disposition: fixed
    title: "Non-idempotent `collection add` breaks resume and scope changes"
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
unparsed: 14
recorded: 2026-11-18T07:07:43.267Z
---

# Phase 23: Code Review Disposition

| Finding | Severity | Disposition | Source |
|---------|----------|-------------|--------|
| CR-01 | critical | fixed | 23-REVIEW-FIX.md (not in the current review) |
| CR-02 | critical | fixed | 23-REVIEW-FIX.md (not in the current review) |
| WR-01 | warning | fixed | 23-REVIEW-FIX.md (not in the current review) |
| WR-02 | warning | fixed | 23-REVIEW-FIX.md (not in the current review) |
| WR-03 | warning | fixed | 23-REVIEW-FIX.md (not in the current review) |
| WR-04 | warning | fixed | 23-REVIEW-FIX.md (not in the current review) |
| WR-05 | warning | fixed | 23-REVIEW-FIX.md (not in the current review) |
| WR-06 | warning | fixed | 23-REVIEW-FIX.md (not in the current review) |
| IN-01 | info | open | - (not in the current review) |
| IN-02 | info | open | - (not in the current review) |
| IN-03 | info | fixed | 23-REVIEW-FIX.md (not in the current review) |
| IN-04 | info | open | - (not in the current review) |
| IN-05 | info | open | - (not in the current review) |
| IN-06 | info | open | - (not in the current review) |

Dispositions: `open` (recorded, not yet triaged), `fixed`, `skipped`, `deferred`.
Set `deferred` by hand and put the reason in the Source cell; both are preserved. A `|` in the reason is kept as prose and escaped on the next run.
Re-running the gate keeps every row it can. A row the current review no longer reports is kept and its Source cell flagged, so a finding does not leave this record silently. ONE exception: when a finding id is REUSED by a different finding, the earlier decision cannot keep a row — the id is taken — and it is dropped. A RECORDED decision (anything but `open`) is named on the console when that happens; a row still at `open` is replaced silently, because `open` records no decision to lose.
