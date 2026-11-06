---
phase: 05
review: 05-REVIEW.md
titles: json
findings:
  - id: WR-18
    severity: warning
    disposition: open
    title: "`context add` confirmation prints execute inside the open transaction — any display failure still rolls back a completed write"
  - id: IN-13
    severity: info
    disposition: open
    title: "`context list` shows raw collection UUIDs; `--line-numbers` default in the search skill is ineffective without `--full`"
  - id: IN-19
    severity: info
    disposition: open
    title: "Tautological guard asserts in the new CR-03 tests can never fail"
  - id: IN-20
    severity: info
    disposition: open
    title: "`_seed`/`_path_rows` helpers duplicated near-verbatim across the two real-SQL test classes"
  - id: CR-03
    severity: critical
    disposition: open
    title: "`context add` confirmation prints interpolate the user-derived target into Rich markup unescaped — MarkupError rolls back the write, so bracket-named targets can never be added"
  - id: WR-02
    severity: warning
    disposition: open
    title: "Unknown `-c/--collection` names silently resolve to exclude-all — typo returns \"No results found\" instead of an error"
  - id: WR-03
    severity: warning
    disposition: open
    title: "`vsearch` surfaces embedding-dimension mismatch as a raw sqlite3 traceback"
  - id: IN-05
    severity: info
    disposition: open
    title: "Output cascade and table rendering triplicated across the three search commands"
  - id: IN-17
    severity: info
    disposition: open
    title: "`vsearch_cmd` re-imports `Database`/`CollectionRepository` inside the function, shadowing the module-level imports and splitting the patch surface"
  - id: IN-18
    severity: info
    disposition: open
    title: "`format_results_md` interpolates field values raw into Markdown structure — backticks/newlines/# corrupt the output"
  - id: CR-01
    severity: critical
    disposition: open
    title: "Rich markup injection — unescaped query/title/content crash or silently vanish in all three search commands"
  - id: CR-02
    severity: critical
    disposition: fixed
    title: "`--line-numbers --md` and `--line-numbers --xml` crash with `AttributeError: 'dict' object has no attribute 'rank'`"
  - id: WR-01
    severity: warning
    disposition: open
    title: "LLM cache TTL writes naive local-time expiry compared against aware UTC strings — cache broken west of UTC; in-scope test fails"
  - id: WR-04
    severity: warning
    disposition: open
    title: "Self-heal merge skips duplicate collapsing in the exact-match branch, contradicting its documented contract"
  - id: IN-01
    severity: info
    disposition: open
    title: "Dimension-mismatch error message points users at `sif cleanup`, which cannot fix the problem"
  - id: IN-02
    severity: info
    disposition: open
    title: "Dead `DEFAULT_INDEX_PATH` constant that also disagrees with the real default"
  - id: IN-03
    severity: info
    disposition: open
    title: "Unused module logger in `cli/main.py`"
  - id: IN-04
    severity: info
    disposition: open
    title: "`test_status_respects_env_var` does not exercise the env var"
  - id: WR-10
    severity: warning
    disposition: open
    title: "XML formatter emits unescaped field values and query attribute — malformed XML for `&`, `<`, `\"` (ledger WR-10 carried into the rewritten lines; CSV half now fixed)"
  - id: WR-12
    severity: warning
    disposition: open
    title: "Type-check gate ships red — `make typecheck` / `make all` / `make ci` exit 1 with 19 diagnostics and no baseline mechanism"
  - id: WR-13
    severity: warning
    disposition: open
    title: "md formatter silently drops `highlights` for dict rows — same query renders differently with and without `--line-numbers`"
  - id: WR-14
    severity: warning
    disposition: open
    title: "`docs/development.md` troubleshooting documents a nonexistent ty flag — `ty check --no-cache` exits 2"
  - id: WR-15
    severity: warning
    disposition: open
    title: "`sif mcp stdio` with a missing index crashes — `console.print(..., file=sys.stderr)` is not a valid rich signature (out-of-scope file; verified runtime bug surfaced by the in-scope ty switch)"
  - id: WR-16
    severity: warning
    disposition: open
    title: "`INTEGRATION_STATUS.md` is a stale DocSift artifact whose dependency guidance is now wrong — this delta edited it instead of retiring it"
  - id: WR-17
    severity: warning
    disposition: open
    title: "Impossible-state guard — `_field`'s `\"\"` fallback defaults can never fire"
  - id: IN-15
    severity: info
    disposition: open
    title: "Redundant black configuration survives the tooling-consolidation delta that removed mypy"
  - id: IN-16
    severity: info
    disposition: open
    title: "`docs/development.md` ruff config snippet says `py39`; actual config is `py310`"
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
  - id: WR-11
    severity: warning
    disposition: open
    title: "docs CI job has no `timeout-minutes`"
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
  - id: IN-14
    severity: info
    disposition: open
    title: "`Qwen3Reranker.load()` duplicates the entire loading block for quiet/non-quiet"
open: 39
total: 41
recorded: 2026-11-06T11:07:59.847Z
---

# Phase 05: Code Review Disposition

| Finding | Severity | Disposition | Source |
|---------|----------|-------------|--------|
| WR-18 | warning | open | - |
| IN-13 | info | open | - |
| IN-19 | info | open | - |
| IN-20 | info | open | - |
| CR-03 | critical | open | - (not in the current review) |
| WR-02 | warning | open | - (not in the current review) |
| WR-03 | warning | open | - (not in the current review) |
| IN-05 | info | open | - (not in the current review) |
| IN-17 | info | open | - (not in the current review) |
| IN-18 | info | open | - (not in the current review) |
| CR-01 | critical | open | - (not in the current review) |
| CR-02 | critical | fixed | 05-REVIEW-FIX.md (not in the current review) |
| WR-01 | warning | open | - (not in the current review) |
| WR-04 | warning | open | - (not in the current review) |
| IN-01 | info | open | - (not in the current review) |
| IN-02 | info | open | - (not in the current review) |
| IN-03 | info | open | - (not in the current review) |
| IN-04 | info | open | - (not in the current review) |
| WR-10 | warning | open | - (not in the current review) |
| WR-12 | warning | open | - (not in the current review) |
| WR-13 | warning | open | - (not in the current review) |
| WR-14 | warning | open | - (not in the current review) |
| WR-15 | warning | open | - (not in the current review) |
| WR-16 | warning | open | - (not in the current review) |
| WR-17 | warning | open | - (not in the current review) |
| IN-15 | info | open | - (not in the current review) |
| IN-16 | info | open | - (not in the current review) |
| WR-05 | warning | open | - (not in the current review) |
| WR-06 | warning | open | - (not in the current review) |
| WR-07 | warning | open | - (not in the current review) |
| WR-08 | warning | open | - (not in the current review) |
| WR-09 | warning | fixed | quick 261105-g1u (b8a81e1) (not in the current review) |
| WR-11 | warning | open | - (not in the current review) |
| IN-06 | info | open | - (not in the current review) |
| IN-07 | info | open | - (not in the current review) |
| IN-08 | info | open | - (not in the current review) |
| IN-09 | info | open | - (not in the current review) |
| IN-10 | info | open | - (not in the current review) |
| IN-11 | info | open | - (not in the current review) |
| IN-12 | info | open | - (not in the current review) |
| IN-14 | info | open | - (not in the current review) |

Dispositions: `open` (recorded, not yet triaged), `fixed`, `skipped`, `deferred`.
Set `deferred` by hand and put the reason in the Source cell; both are preserved. A `|` in the reason is kept as prose and escaped on the next run.
Re-running the gate keeps every row it can. A row the current review no longer reports is kept and its Source cell flagged, so a finding does not leave this record silently. ONE exception: when a finding id is REUSED by a different finding, the earlier decision cannot keep a row — the id is taken — and it is dropped. A RECORDED decision (anything but `open`) is named on the console when that happens; a row still at `open` is replaced silently, because `open` records no decision to lose.
