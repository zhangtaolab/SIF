---
phase: 21
review: 21-REVIEW.md
titles: json
findings:
  - id: CR-01
    severity: critical
    disposition: fixed
    title: "Bench embedder soft-fail is converted into an uncaught crash"
  - id: CR-02
    severity: critical
    disposition: fixed
    title: "Identity decision is taken outside the index flock"
  - id: CR-03
    severity: critical
    disposition: fixed
    title: "backup / vacuum silently create an empty index"
  - id: WR-01
    severity: warning
    disposition: fixed
    title: "Reconcile assumes `document_embeddings` exists whenever the shadow does"
  - id: WR-02
    severity: warning
    disposition: fixed
    title: "Systemic model-output failures classified as document-local"
  - id: WR-03
    severity: warning
    disposition: fixed
    title: "Backup copy is group/other-readable during copy and verification"
  - id: WR-04
    severity: warning
    disposition: fixed
    title: "Backup target validation is check-then-use (symlink TOCTOU)"
  - id: WR-05
    severity: warning
    disposition: fixed
    title: "`vsearch` embeds the query before its identity check"
  - id: WR-06
    severity: warning
    disposition: fixed
    title: "Writer clears the identity-write flag before the transaction commits"
  - id: IN-01
    severity: info
    disposition: open
    title: "Prompted cache bucket can be paired with an unprompted encode for protocol-only embedders"
  - id: IN-02
    severity: info
    disposition: open
    title: "Stored identity `schema` is never validated against `IDENTITY_SCHEMA_VERSION`"
  - id: IN-03
    severity: info
    disposition: open
    title: "GGUF revision hashing blocks every process that builds an identity"
  - id: IN-04
    severity: info
    disposition: open
    title: "`eval` labels ModelScope as a remote embedding provider"
  - id: IN-05
    severity: info
    disposition: open
    title: "`embed_cmd` still materializes a whole collection's document bodies"
  - id: IN-06
    severity: info
    disposition: open
    title: "A chunkless document does not purge its existing rows"
  - id: IN-07
    severity: info
    disposition: open
    title: "Unreachable branch in `QueryExpansion.expand`"
open: 7
total: 16
unparsed: 16
recorded: 2026-11-18T07:22:42.675Z
---

# Phase 21: Code Review Disposition

| Finding | Severity | Disposition | Source |
|---------|----------|-------------|--------|
| CR-01 | critical | fixed | 21-REVIEW-FIX.md (not in the current review) |
| CR-02 | critical | fixed | 21-REVIEW-FIX.md (not in the current review) |
| CR-03 | critical | fixed | 21-REVIEW-FIX.md (not in the current review) |
| WR-01 | warning | fixed | 21-REVIEW-FIX.md (not in the current review) |
| WR-02 | warning | fixed | 21-REVIEW-FIX.md (not in the current review) |
| WR-03 | warning | fixed | 21-REVIEW-FIX.md (not in the current review) |
| WR-04 | warning | fixed | 21-REVIEW-FIX.md (not in the current review) |
| WR-05 | warning | fixed | 21-REVIEW-FIX.md (not in the current review) |
| WR-06 | warning | fixed | 21-REVIEW-FIX.md (not in the current review) |
| IN-01 | info | open | - (not in the current review) |
| IN-02 | info | open | - (not in the current review) |
| IN-03 | info | open | - (not in the current review) |
| IN-04 | info | open | - (not in the current review) |
| IN-05 | info | open | - (not in the current review) |
| IN-06 | info | open | - (not in the current review) |
| IN-07 | info | open | - (not in the current review) |

Dispositions: `open` (recorded, not yet triaged), `fixed`, `skipped`, `deferred`.
Set `deferred` by hand and put the reason in the Source cell; both are preserved. A `|` in the reason is kept as prose and escaped on the next run.
Re-running the gate keeps every row it can. A row the current review no longer reports is kept and its Source cell flagged, so a finding does not leave this record silently. ONE exception: when a finding id is REUSED by a different finding, the earlier decision cannot keep a row — the id is taken — and it is dropped. A RECORDED decision (anything but `open`) is named on the console when that happens; a row still at `open` is replaced silently, because `open` records no decision to lose.
