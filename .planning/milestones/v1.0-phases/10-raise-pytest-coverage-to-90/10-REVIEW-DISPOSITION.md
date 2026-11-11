---
phase: 10
review: 10-REVIEW.md
titles: json
findings:
  - id: WR-01
    severity: warning
    disposition: open
    title: "`collection remove` orphans vec0 embeddings — vector search pollution until `sif cleanup`"
  - id: WR-02
    severity: warning
    disposition: open
    title: "`index update` runs all collections in one implicit transaction — later failure discards earlier collections' work"
  - id: WR-03
    severity: warning
    disposition: fixed
    title: "`multi-get --max-bytes` truncates by characters after a byte-length check — limit can be exceeded up to 4x"
  - id: WR-04
    severity: warning
    disposition: open
    title: "`ls` subpath filter matches the absolute stored path, not collection-relative paths, and is not segment-aligned"
  - id: WR-05
    severity: warning
    disposition: open
    title: "`collection ls` accepts and documents a `subpath` argument but ignores it entirely"
  - id: WR-06
    severity: warning
    disposition: open
    title: "`bench` fixture load and validation errors escape as raw tracebacks"
  - id: WR-07
    severity: warning
    disposition: open
    title: "MCP `get` tool silently ignores `max_lines` when `from_line` is absent"
  - id: WR-08
    severity: warning
    disposition: open
    title: "MCP `hybrid_search` cannot degrade to BM25 when sqlite-vec is unavailable — every `query` tool call fails"
  - id: WR-09
    severity: warning
    disposition: open
    title: "`cleanup` compares naive-local ISO timestamps against aware-UTC ISO strings lexicographically"
  - id: WR-10
    severity: warning
    disposition: fixed
    title: "Embedding-dimension mismatch error recommends `sif cleanup`, which cannot fix the mismatch"
  - id: IN-01
    severity: info
    disposition: open
    title: "Identical if/else branches under a comment promising syntax highlighting that doesn't exist"
  - id: IN-02
    severity: info
    disposition: open
    title: "`vsearch_cmd` function-local imports duplicate module-level imports of the same names"
  - id: IN-03
    severity: info
    disposition: open
    title: "`manager._model` private access in two commands — `EmbeddingManager` has no public model accessor"
  - id: IN-04
    severity: info
    disposition: open
    title: "`quiet` recomputed redundantly after the search completes"
  - id: IN-05
    severity: info
    disposition: open
    title: "`--config` global option is accepted, documented, and never consumed"
  - id: IN-06
    severity: info
    disposition: open
    title: "`status_cmd` fallback calls `get_settings()` without the ValidationError guard used elsewhere"
  - id: IN-07
    severity: info
    disposition: open
    title: "Inconsistent embedding-dim resolution across commands — 384 magic fallback and per-query probe"
  - id: IN-08
    severity: info
    disposition: open
    title: "Disk-fallback `read_text()` without explicit encoding"
  - id: IN-09
    severity: info
    disposition: open
    title: "api-reference example uses `sqlite3.connect(\"~/...\")` — tilde is not expanded"
  - id: IN-10
    severity: info
    disposition: open
    title: "Backend tests construct a real `DatabaseConnection(\"/tmp/test.db\")` outside tmp_path"
  - id: CR-01
    severity: critical
    disposition: open
    title: "Legacy direct-DELETE triggers not migrated in schema.py:148-163,188-191,236-242,261-267 — deleted content remains searchable on legacy DBs"
  - id: CR-02
    severity: critical
    disposition: open
    title: "XML-forbidden control characters not stripped in cli/commands/search.py:104-121 — title containing \\x0b produces non-well-formed XML"
open: 20
total: 22
recorded: 2026-11-06T12:37:58.492Z
---

# Phase 10: Code Review Disposition

| Finding | Severity | Disposition | Source |
|---------|----------|-------------|--------|
| WR-01 | warning | open | - |
| WR-02 | warning | open | - |
| WR-03 | warning | fixed | quick 261111-mlj (multi-get byte-budget truncation plus regression tests) |
| WR-04 | warning | open | - |
| WR-05 | warning | open | - |
| WR-06 | warning | open | - |
| WR-07 | warning | open | - |
| WR-08 | warning | open | - |
| WR-09 | warning | open | - |
| WR-10 | warning | fixed | quick 261111-l7p (dimension-mismatch remediation message plus regression test) |
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
| CR-01 | critical | open | - (not in the current review) |
| CR-02 | critical | open | - (not in the current review) |

Dispositions: `open` (recorded, not yet triaged), `fixed`, `skipped`, `deferred`.
Set `deferred` by hand and put the reason in the Source cell; both are preserved. A `|` in the reason is kept as prose and escaped on the next run.
Re-running the gate keeps every row it can. A row the current review no longer reports is kept and its Source cell flagged, so a finding does not leave this record silently. ONE exception: when a finding id is REUSED by a different finding, the earlier decision cannot keep a row — the id is taken — and it is dropped. A RECORDED decision (anything but `open`) is named on the console when that happens; a row still at `open` is replaced silently, because `open` records no decision to lose.
