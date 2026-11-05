---
phase: 05
review: 05-REVIEW.md
titles: json
findings:
  - id: CR-02
    severity: critical
    disposition: fixed
    title: "`--line-numbers --md` and `--line-numbers --xml` crash with `AttributeError: 'dict' object has no attribute 'rank'`"
  - id: CR-01
    severity: critical
    disposition: fixed
    title: "`--line-numbers --csv` crashes with `AttributeError: 'dict' object has no attribute 'rank'`"
  - id: WR-01
    severity: warning
    disposition: fixed
    title: "`vsearch_cmd` calls `get_settings()` unguarded — raw pydantic traceback with explicit `--index` and invalid config (WR-09 fix incomplete in same file)"
  - id: IN-01
    severity: info
    disposition: open
    title: "New validator blocks all default-`--index` commands when `SIF_RERANKER_MODEL_TYPE` is invalid"
  - id: IN-02
    severity: info
    disposition: open
    title: "Dead fallback in `status_cmd` calls `get_settings()` unguarded"
  - id: IN-03
    severity: info
    disposition: open
    title: "Code comments cite review-finding IDs that no longer match the disposition ledger"
  - id: IN-04
    severity: info
    disposition: open
    title: "`TestContextRmAlias` never tests the `rm` alias"
  - id: WR-02
    severity: warning
    disposition: fixed
    title: "Self-heal merge only fires on exact historical re-typing — duplicate rows accumulate and prune cannot clean them"
  - id: WR-03
    severity: warning
    disposition: fixed
    title: "`context add` / `context remove` silently create an empty index database when no index exists"
  - id: WR-04
    severity: warning
    disposition: open
    title: "`DatabaseConnection.execute()/executemany()` return a cursor whose connection is already closed"
  - id: WR-05
    severity: warning
    disposition: open
    title: "`FileWatcher` leaks/orphans observers on repeated `start()` and never unschedules on per-collection `stop()`"
  - id: WR-06
    severity: warning
    disposition: open
    title: "`ModelScopeEmbedder` picks the model directory via the first unordered `glob(\"*\")` entry — can point SentenceTransformer at an auxiliary directory"
  - id: WR-07
    severity: warning
    disposition: open
    title: "Docs promise context behaviors the code does not implement (global/collection effects, directory scope)"
  - id: WR-08
    severity: warning
    disposition: open
    title: "`docs/architecture.md` dependency graph is stale relative to its own generator"
  - id: WR-09
    severity: warning
    disposition: fixed
    title: "Reranker construction catches only `ImportError`; an unvalidated `SIF_RERANKER_MODEL_TYPE` crashes `query` with a raw traceback"
  - id: WR-10
    severity: warning
    disposition: open
    title: "CSV and XML formatters do not escape field values — filenames with `\"`, `,`, `<`, `&` produce malformed output"
  - id: WR-11
    severity: warning
    disposition: open
    title: "docs CI job has no `timeout-minutes`"
  - id: IN-05
    severity: info
    disposition: open
    title: "`EmbeddingManager.embed/embed_single` accept a `normalize` parameter that is silently ignored"
  - id: IN-06
    severity: info
    disposition: open
    title: "`create_reranker` phantom-defensive accessors on `Settings`"
  - id: IN-07
    severity: info
    disposition: open
    title: "Defensive `getattr` on the statically-guaranteed `SearchResult` dataclass"
  - id: IN-08
    severity: info
    disposition: open
    title: "Duplicate `DatabaseConnection` classes with different semantics; `ConnectionPool` skips the sqlite-vec extension"
  - id: IN-09
    severity: info
    disposition: open
    title: "Watcher event handlers are log-only stubs; injected indexer is never used"
  - id: IN-10
    severity: info
    disposition: open
    title: "`contexts` table dropped the legacy `UNIQUE(context_type, target_id)` constraint"
  - id: IN-11
    severity: info
    disposition: open
    title: "`docs/installation.md` expected-output block is stale; nonexistent log file path"
  - id: IN-12
    severity: info
    disposition: open
    title: "mcp-server.md overclaims query behavior: content and reranking"
  - id: IN-13
    severity: info
    disposition: open
    title: "`context list` shows raw collection UUIDs; `--line-numbers` default in the search skill is ineffective without `--full`"
  - id: IN-14
    severity: info
    disposition: open
    title: "`Qwen3Reranker.load()` duplicates the entire loading block for quiet/non-quiet"
open: 21
total: 27
recorded: 2026-11-05T10:03:14.525Z
---

# Phase 05: Code Review Disposition

| Finding | Severity | Disposition | Source |
|---------|----------|-------------|--------|
| CR-02 | critical | fixed | 05-REVIEW-FIX.md |
| CR-01 | critical | fixed | 05-REVIEW-FIX.md (not in the current review) |
| WR-01 | warning | fixed | 05-REVIEW-FIX.md (not in the current review) |
| IN-01 | info | open | - (not in the current review) |
| IN-02 | info | open | - (not in the current review) |
| IN-03 | info | open | - (not in the current review) |
| IN-04 | info | open | - (not in the current review) |
| WR-02 | warning | fixed | 05-REVIEW-FIX.md (not in the current review) |
| WR-03 | warning | fixed | quick 261105-g1u (25481d8) (not in the current review) |
| WR-04 | warning | open | - (not in the current review) |
| WR-05 | warning | open | - (not in the current review) |
| WR-06 | warning | open | - (not in the current review) |
| WR-07 | warning | open | - (not in the current review) |
| WR-08 | warning | open | - (not in the current review) |
| WR-09 | warning | fixed | quick 261105-g1u (b8a81e1) (not in the current review) |
| WR-10 | warning | open | - (not in the current review) |
| WR-11 | warning | open | - (not in the current review) |
| IN-05 | info | open | - (not in the current review) |
| IN-06 | info | open | - (not in the current review) |
| IN-07 | info | open | - (not in the current review) |
| IN-08 | info | open | - (not in the current review) |
| IN-09 | info | open | - (not in the current review) |
| IN-10 | info | open | - (not in the current review) |
| IN-11 | info | open | - (not in the current review) |
| IN-12 | info | open | - (not in the current review) |
| IN-13 | info | open | - (not in the current review) |
| IN-14 | info | open | - (not in the current review) |

Dispositions: `open` (recorded, not yet triaged), `fixed`, `skipped`, `deferred`.
Set `deferred` by hand and put the reason in the Source cell; both are preserved. A `|` in the reason is kept as prose and escaped on the next run.
Re-running the gate keeps every row it can. A row the current review no longer reports is kept and its Source cell flagged, so a finding does not leave this record silently. ONE exception: when a finding id is REUSED by a different finding, the earlier decision cannot keep a row — the id is taken — and it is dropped. A RECORDED decision (anything but `open`) is named on the console when that happens; a row still at `open` is replaced silently, because `open` records no decision to lose.
