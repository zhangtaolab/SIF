---
phase: 06
review: 06-REVIEW.md
titles: json
findings:
  - id: CR-01
    severity: critical
    disposition: fixed
    title: "Documented command fails — `sif get <path>` is not a valid invocation"
  - id: CR-02
    severity: critical
    disposition: fixed
    title: "Generator writes unescaped `|` into markdown table cells, corrupting six rows of docs/configuration.md"
  - id: CR-03
    severity: critical
    disposition: fixed
    title: "Generator output is Python-version-dependent — CI drift gate cannot reproduce the checked-in artifact"
  - id: WR-01
    severity: warning
    disposition: fixed
    title: "BM25 k1 default contradicts search-algorithms.md and the actual FTS5 behavior"
  - id: WR-02
    severity: warning
    disposition: fixed
    title: "architecture.md Mermaid diagram has drifted from its own generator; nothing regenerates it"
  - id: WR-03
    severity: warning
    disposition: open
    title: "Arch-diagram generator resolves its source tree relative to CWD and silently emits an empty diagram"
  - id: WR-04
    severity: warning
    disposition: open
    title: "Validator scanner records only the first field of multi-field validators"
  - id: WR-05
    severity: warning
    disposition: open
    title: "Validation Rules table omits the enforced `reranker_model_type` rule"
  - id: WR-06
    severity: warning
    disposition: open
    title: "Computed-default paths presented as Linux-only values"
  - id: WR-07
    severity: warning
    disposition: fixed
    title: "\"Weighted Combination\" documents a fusion scheme that does not exist"
  - id: WR-08
    severity: warning
    disposition: open
    title: "Quickstart \"Search History\" tip is non-functional"
  - id: IN-01
    severity: info
    disposition: open
    title: "Template-substitution residue — stray triple spaces in command lines"
  - id: IN-02
    severity: info
    disposition: open
    title: "README Python API example never closes the Database"
  - id: IN-03
    severity: info
    disposition: open
    title: "Config generator silently drops unknown SECTIONS field names"
  - id: IN-04
    severity: info
    disposition: open
    title: "Arch-diagram module keys use \"/\" separators and degenerate for root-level files"
  - id: IN-05
    severity: info
    disposition: open
    title: "Published examples hardcode one user's home directory"
open: 10
total: 16
recorded: 2026-11-06T15:40:45.414Z
---

# Phase 06: Code Review Disposition

| Finding | Severity | Disposition | Source |
|---------|----------|-------------|--------|
| CR-01 | critical | fixed | fix commit b418f7c (hand-triage 2026-11-06, live-verified) |
| CR-02 | critical | fixed | fix commit b418f7c (hand-triage 2026-11-06, live-verified) |
| CR-03 | critical | fixed | fix commit b418f7c (hand-triage 2026-11-06, live-verified) |
| WR-01 | warning | fixed | fix dfafa9e gap-3 (README k1 → FTS5 built-in 1.2, not exposed) |
| WR-02 | warning | fixed | fix dfafa9e gap-1 (generator filters TYPE_CHECKING imports; block re-synced, diff-verified). CI-wiring hardening (arch generator into docs-generate/drift gate) remains a follow-up |
| WR-03 | warning | open | - |
| WR-04 | warning | open | - |
| WR-05 | warning | open | - |
| WR-06 | warning | open | - |
| WR-07 | warning | fixed | fix dfafa9e gap-2 (section rewritten to the real RRF fuse_with_weights semantics) |
| WR-08 | warning | open | - |
| IN-01 | info | open | - |
| IN-02 | info | open | - |
| IN-03 | info | open | - |
| IN-04 | info | open | - |
| IN-05 | info | open | - |

Dispositions: `open` (recorded, not yet triaged), `fixed`, `skipped`, `deferred`.

Set `deferred` by hand and put the reason in the Source cell; both are preserved.

