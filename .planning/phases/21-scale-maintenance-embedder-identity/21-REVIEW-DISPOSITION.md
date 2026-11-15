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
    title: "Identity decision is taken outside the index flock \u2014 concurrent writers can mix vector spaces and falsify the identity"
  - id: CR-03
    severity: critical
    disposition: fixed
    title: "`sif index backup` / `sif index vacuum` silently create an empty index and report success"
  - id: WR-01
    severity: warning
    disposition: fixed
    title: "Reconcile assumes `document_embeddings` exists whenever the shadow does; `cleanup`/`vacuum` fail on stripped environments"
  - id: WR-02
    severity: warning
    disposition: fixed
    title: "Systemic model-output failures are classified as document-local (and retried forever by watch)"
  - id: WR-03
    severity: warning
    disposition: fixed
    title: "Backup copy is group/other-readable for the entire copy + integrity-check window"
  - id: WR-04
    severity: warning
    disposition: fixed
    title: "Backup target validation is check-then-use (symlink TOCTOU)"
  - id: WR-05
    severity: warning
    disposition: fixed
    title: "`vsearch` runs the query embedding (and can call a remote API) before its identity check"
  - id: WR-06
    severity: warning
    disposition: fixed
    title: "`StreamingEmbedWriter` clears the identity-write flag before the transaction commits"
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
recorded: 2026-11-15T18:26:19Z
---

# Phase 21: Code Review Disposition

| Finding | Severity | Disposition | Source |
|---------|----------|-------------|--------|
| CR-01 | critical | fixed | 21-REVIEW-FIX.md |
| CR-02 | critical | fixed | 21-REVIEW-FIX.md |
| CR-03 | critical | fixed | 21-REVIEW-FIX.md |
| WR-01 | warning | fixed | 21-REVIEW-FIX.md |
| WR-02 | warning | fixed | 21-REVIEW-FIX.md |
| WR-03 | warning | fixed | 21-REVIEW-FIX.md |
| WR-04 | warning | fixed | 21-REVIEW-FIX.md |
| WR-05 | warning | fixed | 21-REVIEW-FIX.md |
| WR-06 | warning | fixed | 21-REVIEW-FIX.md |
| IN-01 | info | open | - |
| IN-02 | info | open | - |
| IN-03 | info | open | - |
| IN-04 | info | open | - |
| IN-05 | info | open | - |
| IN-06 | info | open | - |
| IN-07 | info | open | - |

Dispositions: `open` (recorded, not yet triaged), `fixed`, `skipped`, `deferred`.

