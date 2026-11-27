---
phase: 24
review: 24-REVIEW.md
titles: json
findings:
  - id: WR-01
    severity: warning
    disposition: open
    title: "`sif models status` can never report the `legacy` state for the `~/.sif/models` tree that `sif models pull` adopts"
  - id: WR-02
    severity: warning
    disposition: open
    title: "`_split_model_id` lets a drive-relative segment escape `<cache>/models` on Windows"
  - id: WR-03
    severity: warning
    disposition: open
    title: "The read-only identity probe builds a `file:` URI without percent-encoding, so a `?`, `#`, or `%` in the index path silently reports `no-identity`"
  - id: WR-04
    severity: warning
    disposition: fixed
    fixed_in: 879b106e
    title: "The committed-evidence paths still target `.planning/phases/24-…`, which no longer exists after the v1.2 milestone move"
    note: "`scripts/chunk_sweep.py`, `scripts/breadcrumb_eval.py` and `scripts/harrier_eval.py` now default `ARTIFACT_PATH` to `.planning/milestones/v1.2-phases/…`; `docs/benchmarking.md` cites the same paths and all three files exist."
  - id: IN-01
    severity: info
    disposition: open
    title: "Unused module constant `_REGISTRY_TARGETS`"
  - id: IN-02
    severity: info
    disposition: open
    title: "`ModelDownloader.clear_cache()` has no production caller"
  - id: IN-03
    severity: info
    disposition: open
    title: "`load_document_metadata`'s docstring describes lazy iteration the code does not perform"
  - id: IN-04
    severity: info
    disposition: open
    title: "`sif eval --compare FILE` alone fails, although the option's help presents it as a mode"
  - id: IN-05
    severity: info
    disposition: open
    title: "URL downloads derive the local filename from the URL, query string included"
  - id: IN-06
    severity: info
    disposition: open
    title: "`docs/migration.md` labels `sif status` as the configuration check"
open: 10
total: 10
recorded: 2026-11-24T02:13:19.565Z
---

# Phase 24: Code Review Disposition

| Finding | Severity | Disposition | Source |
|---------|----------|-------------|--------|
| WR-01 | warning | open | - |
| WR-02 | warning | open | - |
| WR-03 | warning | open | - |
| WR-04 | warning | fixed | 879b106e |
| IN-01 | info | open | - |
| IN-02 | info | open | - |
| IN-03 | info | open | - |
| IN-04 | info | open | - |
| IN-05 | info | open | - |
| IN-06 | info | open | - |

Dispositions: `open` (recorded, not yet triaged), `fixed`, `skipped`, `deferred`.
Set `deferred` by hand and put the reason in the Source cell; both are preserved. A `|` in the reason is kept as prose and escaped on the next run.
Re-running the gate keeps every row it can. A row the current review no longer reports is kept and its Source cell flagged, so a finding does not leave this record silently. ONE exception: when a finding id is REUSED by a different finding, the earlier decision cannot keep a row — the id is taken — and it is dropped. A RECORDED decision (anything but `open`) is named on the console when that happens; a row still at `open` is replaced silently, because `open` records no decision to lose.
