---
phase: 14-freshness-floor-pre-command-refresh-staleness-marking
verified: 2026-11-08T04:44:21Z
status: passed
score: 16/16 must-haves verified
covered_files:
  - .planning/phases/14-freshness-floor-pre-command-refresh-staleness-marking/14-01-PLAN.md
  - .planning/phases/14-freshness-floor-pre-command-refresh-staleness-marking/14-01-SUMMARY.md
  - .planning/phases/14-freshness-floor-pre-command-refresh-staleness-marking/14-02-PLAN.md
  - .planning/phases/14-freshness-floor-pre-command-refresh-staleness-marking/14-02-SUMMARY.md
  - .planning/phases/14-freshness-floor-pre-command-refresh-staleness-marking/14-03-PLAN.md
  - .planning/phases/14-freshness-floor-pre-command-refresh-staleness-marking/14-03-SUMMARY.md
  - docs/cli-reference.md
  - docs/configuration.md
  - scripts/generate_config_ref.py
  - src/sif/cli/commands/search.py
  - src/sif/cli/main.py
  - src/sif/config/settings.py
  - src/sif/core/models.py
  - src/sif/database/repositories.py
  - src/sif/indexing/drift.py
  - src/sif/indexing/incremental.py
  - src/sif/mcp/backend.py
  - src/sif/search/bm25.py
  - src/sif/search/hybrid.py
  - src/sif/search/staleness.py
  - src/sif/search/vector.py
  - tests/unit/cli/test_index_locking.py
  - tests/unit/cli/test_search.py
  - tests/unit/cli/test_status.py
  - tests/unit/indexing/test_drift.py
  - tests/unit/indexing/test_incremental.py
  - tests/unit/mcp/test_backend.py
  - tests/unit/search/test_bm25.py
  - tests/unit/search/test_staleness.py
  - tests/unit/search/test_vector.py
covered_digest: "v4:sha256:68d16be52777aa0009dcfc75629f5fa8af32d0a05c2de833abc5852208d2d128"
behavior_unverified: 0
overrides_applied: 0
unverified_prohibitions:
  - must_have: "Search must NEVER become an error because the index drifted — over-cap and refresh failures surface as stderr warnings and search proceeds (D-05)"
    unverified_leg: "refresh-failure leg: the except branch in _pre_search_refresh (src/sif/cli/commands/search.py:200-210) — no test injects a detect_drift/refresh_drifted failure and asserts the warning + exit 0 + results path"
    enforced_leg: "over-cap leg IS test-enforced (test_over_cap_drift_skips_refresh_and_warns, run green)"
    evidence_status: "code present and wired; no exercising test (suite-wide grep for exception injection on detect_drift/refresh_drifted: zero hits)"
human_verification:
  - test: "Inject a failure into the pre-search refresh (e.g. patch sif.cli.commands.search.refresh_drifted to raise RuntimeError) on a drifted tmp index and run `sif search <term>`"
    expected: "Stderr shows 'Pre-search refresh failed; searching the current index', exit code 0, and stale-index results still render — search never errors because of drift (D-05 refresh-failure leg)"
    why_human: "The except branch at search.py:200-210 is present and wired but no automated test exercises the failure transition; grep/probe checks cannot prove an untested branch's runtime behavior. Closing it needs only a ~5-line test (patch + assert exit 0 + warning) — human decides accept vs. add-test."
  - test: "Run `sif search <real query>` against your real knowledge base with a clean index (no drift) and time it by feel"
    expected: "The pre-command stat walk is imperceptible — no visible delay versus pre-phase behavior, no notices (SC2 'no perceptible latency' half)"
    why_human: "Performance feel on real hardware/data volume is a human judgment; the phase proved SC2 structurally (lockless, silent, writeless — test-green) and deliberately made no latency asserts (RESEARCH Pitfall 11)"
---

# Phase 14: Freshness Floor (Pre-Command Refresh + Staleness Marking) Verification Report

**Phase Goal:** Search results are fresh even when no watch is running, and users can see how fresh their results are.
**Verified:** 2026-11-08T04:44:21Z
**Status:** human_needed
**Re-verification:** No — initial verification

## Goal Achievement

All three ROADMAP success criteria are demonstrably met in the codebase:

- **SC1** (fresh without watch): the search trio stat-walks searched collections and BM25-refreshes drift before searching — proven end-to-end by real-DB tests (run green during this verification).
- **SC2** (near-zero clean cost + capped refresh): clean search is provably lockless/silent/writeless; over-cap drift skips refresh, warns, and still exits 0 with results.
- **SC3** (visible staleness in table and JSON): `SearchResult.vectors_stale` is derived at query time from a real `document_embeddings` scan and renders in all five output formats, MCP metadata, and a `sif status` Vector lag row.

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | [14-01/SC1] No watch running, `sif search` on changed files returns refreshed content (modified findable, new searchable, deleted no longer hits) | ✓ VERIFIED | `TestPreSearchRefresh::test_search_finds_modified_content_and_notifies_on_stderr` and `::test_search_finds_new_file_and_drops_deleted_file` **run green** (real DB + CliRunner: new term found, notice `refreshed 1 files (bm25) before search` on stderr, second search silent) |
| 2 | [14-01/SC2] Clean index search performs zero writes: no `{db}.lock`, no notice, documents unchanged | ✓ VERIFIED | `::test_clean_search_is_lockless_silent_and_writeless` **run green**; recording-lock spy `TestPreSearchRefreshCoexistence::test_clean_search_never_enters_index_lock` enumerated |
| 3 | [14-01/SC2] Over-cap drift: nothing refreshed, stderr warning names count + `sif index update` remedy, exit 0 with stale hits | ✓ VERIFIED | `::test_over_cap_drift_skips_refresh_and_warns` **run green** (snapshot-compare unchanged, no lock file, warning text asserted); boundary + count-first tests enumerated |
| 4 | [14-01/D-01] Drift check exists only in CLI command layer; bench/MCP/searchers never invoke it | ✓ VERIFIED | `git grep -l "sif.indexing.drift" -- src/sif` → `src/sif/cli/commands/search.py` ONLY (sole importer); bench.py, mcp/, search/ absent |
| 5 | [14-01/D-03] Under-cap refresh vs held index lock waits up to lock_wait_timeout then runs (wait-then-run) | ✓ VERIFIED | `TestPreSearchRefreshCoexistence::test_search_refresh_waits_out_held_lock_then_proceeds` **run green** (parent-held flock, deadline lower-bound assert) |
| 6 | [14-01] Same drifted search twice refreshes once (stateless, stat-decides) | ✓ VERIFIED | Second-run `stderr == ""` asserted in the e2e test **run green**; convergence regressions for touch-only drift (CR-01) and predicate-excluded docs (WR-01) enumerated in test_drift.py/test_search.py |
| 7 | [14-02/SC3] BM25-refreshed-without-embed doc carries vectors_stale=true in results and `--json`; fully embedded carries false | ✓ VERIFIED | `TestLagStateEndToEnd::test_bm25_refreshed_after_embed_doc_is_marked_stale` **run green** — lag state produced by REAL `update_paths` purge (not raw SQL): drifted doc True, embedded keeper False |
| 8 | [14-02] Zero-embeddings index: no markers, no nagging (display gate) | ✓ VERIFIED | `TestMarkVectorStaleness::test_display_gate_zero_embeddings_marks_nothing` **run green**; status `none (no vectors indexed)` state **run green** |
| 9 | [14-02] vec0 table missing: degrades to no markers, never raises; status renders n/a | ✓ VERIFIED | `::test_vec0_missing_degrades_to_unmarked` and `TestVectorLag::test_vec0_missing_renders_na` **run green** |
| 10 | [14-02/D-10] `sif status` shows a Vector lag row naming the count of docs without embeddings | ✓ VERIFIED | `TestVectorLag::test_lag_count_renders_documents` **run green**; `_vector_lag_text` renders all three states + degrade-never-fail try/except (cli/main.py:133-156, 202-210) |
| 11 | [14-02/D-11] MCP query response carries the flag via backend.hybrid_search metadata | ✓ VERIFIED | `test_hybrid_search_mocks` **run green** (`metadata.get("vectors_stale") is True` asserted); forwarding line at backend.py:114-118 |
| 12 | [14-02] Marking is idempotent and read-only | ✓ VERIFIED | `::test_marking_is_idempotent` **run green**; staleness.py contains only one read-only SELECT, zero writes |
| 13 | [14-02] Read-only scan needs no lock under concurrent embed; never blocks/crashes | ✓ VERIFIED | Module issues exactly one `SELECT document_id FROM document_embeddings` (code inspection — no write statement exists in the module); crash-degrade tested; concurrent-read non-blocking rests on the Phase 11 WAL + busy_timeout contract (LIVE-06 declared precondition) |
| 14 | [14-03/SC3] Every CLI format shows the marker: table dim annotation (no new column), JSON boolean (incl. --line-numbers dict), CSV column, MD annotation, XML attribute | ✓ VERIFIED | `test_table_marks_stale_result_not_fresh`, `test_json_carries_vectors_stale`, `test_csv_column_carries_true_and_false`, `test_md_annotation_on_stale_title_only`, `test_xml_attribute_true_false_and_parseable` all **run green**; dict-shape variants enumerated (10-test battery) |
| 15 | [14-03/D-13] ≥1 stale result → exactly one stderr line naming count + `sif embed` remedy; `-q` suppresses; stdout clean | ✓ VERIFIED | `test_remedy_hint_one_stderr_line_names_count` **run green** (count, once-only, hint fragments absent from stdout); quiet-suppression and JSON-purity tests enumerated; hint wording appears exactly once in search.py |
| 16 | [14-03/D-12] No format silently drops the signal | ✓ VERIFIED | Per-format battery green across runs; `_field(r, 'vectors_stale')` dual-shape reader used by every explicit renderer (search.py:95, 223, 248, 261, 289) |

**Score:** 16/16 truths verified (0 present, behavior-unverified)

### Unverified Prohibition (flagged — human review recommended)

| Prohibition | Leg | Status | Evidence |
|-------------|-----|--------|----------|
| 14-01 P3: "Search must NEVER become an error because the index drifted (D-05)" | over-cap → warn + exit 0 | ✓ ENFORCED | `test_over_cap_drift_skips_refresh_and_warns` run green |
| 14-01 P3 (same) | refresh failure → stderr warning + search proceeds | ⚠️ UNVERIFIED-PROHIBITION | Except branch at `src/sif/cli/commands/search.py:200-210` present and wired; **no test injects a detect_drift/refresh_drifted failure** (suite-wide grep: zero exception-injection hits). Test-tier item with no wired enforcement for this leg → flagged per fail-closed contract, never silently green |

All other prohibitions verified enforced: 14-01 P1 (never embed — drift.py imports no embedder; sole write path `update_paths` proven embeddings-purging by `test_update_paths_purges_embeddings_of_modified_doc`, run green), 14-01 P2 (stdout clean — direct tests green), 14-02 P1 (never persisted — `schema.py` untouched since Phase 10.1 per git log; module is SELECT-only; idempotency test), 14-02 P2 (no content in notices — f-strings over integer counts only; tests pin counts/commands/stdout purity), 14-02 P3 (no per-result queries — one scan in code; `test_empty_results_never_queries`; exact side_effect call-sequence pins in test_bm25/test_vector), 14-03 P1 (fixed boolean literals — code + XML parseability test).

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `src/sif/indexing/drift.py` | DriftReport / detect_drift / refresh_drifted, presentation-free | ✓ VERIFIED | 153 lines; no click/Console imports; mtime-primary docstring documents the SC1 deviation; index_lock acquired only in refresh_drifted |
| `src/sif/database/repositories.py` | `list_stat_by_collection` content-free snapshot | ✓ VERIFIED | Exact SQL `SELECT path, mtime FROM documents WHERE collection_id = ?`; never calls `_row_to_document` |
| `src/sif/config/settings.py` | `search_refresh_enabled` + `search_refresh_max_files` | ✓ VERIFIED | Defaults True / 100 (ge=1); registered in generator SECTIONS; docs regenerated (grep counts 1/1/3) |
| `tests/unit/indexing/test_drift.py` | Deterministic drift battery | ✓ VERIFIED | 10+ tests: touch/content/delete/new drift, missing-root phantom guard, clean-empty, lock-on-work-only, WR-01 predicate convergence |
| `src/sif/search/staleness.py` | mark_vector_staleness / embedded_document_ids | ✓ VERIFIED | 78 lines; one constant scan row-at-a-time; None-on-OperationalError; display gate; corrected D-08 formula documented |
| `src/sif/core/models.py` | SearchResult.vectors_stale + to_dict key | ✓ VERIFIED | Field at :225 (defaulted), to_dict key at :241 — rides `--json` and survives `--line-numbers` dict copying |
| `src/sif/cli/main.py` | Vector lag status row | ✓ VERIFIED | `_vector_lag_text` (:133-156) with n/a / none / N documents states + degrade try/except; row after Watch row |
| `tests/unit/search/test_staleness.py` | Staleness battery | ✓ VERIFIED | 12 tests incl. real-purge lag e2e, gate, degrade, idempotency, delegation, to_dict |
| `src/sif/cli/commands/search.py` (14-03) | Markers in all formatters + stderr hint | ✓ VERIFIED | `_title_cell` (3 table sites), CSV header `collection,vectors_stale`, MD annotation, XML attribute, `_warn_stale_results` (3 output tails) |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|----|--------|---------|
| cli/commands/search.py | indexing/drift.py | detect_drift/refresh_drifted after resolution, before searcher | ✓ WIRED | Tool-verified; `_pre_search_refresh` called at :384/:566/:712 in all three commands |
| indexing/drift.py | indexing/incremental.py | update_paths inside index_lock | ✓ WIRED | Tool-verified; one lock window, per-collection update_paths (:139-150) |
| indexing/drift.py | database/repositories.py | list_stat_by_collection snapshot | ✓ WIRED | Tool-verified |
| search/bm25.py + vector.py + hybrid.py | search/staleness.py | mark_vector_staleness in each `_attach_contexts` | ✓ WIRED | Manual (tool choked on prose `from:`): 2 occurrences each (import + call); chaining at bm25.py:122, vector.py:135, hybrid.py:115; hybrid early returns (:69/:71) and SearchPipeline delegation (:242) funnel through it — delegation test run green |
| mcp/backend.py | core/models.py | r.vectors_stale into metadata | ✓ WIRED | Tool-verified; explicit forward at :114-118 with B5 rationale comment |
| cli/main.py | search/staleness.py | Vector lag row from embedded_document_ids | ✓ WIRED | Tool-verified; shared scan + documents-id membership count |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|--------------------|--------|
| staleness marker chain | `vectors_stale` | `SELECT document_id FROM document_embeddings` (real vec0 scan) → SearchResult field → to_dict/formatters/MCP/status | Yes — lag-state e2e drives a real purge and real scan | ✓ FLOWING |
| drift chain | `DriftReport.paths_by_collection` | FileScanner stat walk (real filesystem) × `list_stat_by_collection` (real documents table) → update_paths | Yes — e2e tests mutate real files and observe refreshed FTS content | ✓ FLOWING |
| status Vector lag row | `lagging` count | `embedded_document_ids` + `SELECT id FROM documents` | Yes — TestVectorLag seeds/mocks the probe sources and asserts rendered text | ✓ FLOWING |

No static returns, hardcoded data, or mocks in any production path.

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| 23 named phase tests (drift e2e/clean/over-cap/coexistence, lag-state, gate, degrade, idempotency, formats, hint, status, MCP forward, purge invariant, stdout purity) | `pytest <node-ids> --no-cov` (4 batches) | all passed | ✓ PASS |
| Docs drift gate | `pytest tests/test_docs.py` | 13 passed | ✓ PASS |
| Lint / format / types | `ruff check` + `ruff format --check` + `ty check src/sif` | all green | ✓ PASS |
| Full phase acceptance suite (once) | `env -u FORCE_COLOR NO_COLOR=1 python -m pytest` | 1228 passed, 1 skipped, 94.45% ≥ 90 floor | ✓ PASS |
| Settings defaults probe | settings.py read + docs grep | True/100; docs counts 1/1/3 | ✓ PASS |

### Probe Execution

Step 7c: SKIPPED — no `scripts/*/tests/probe-*.sh` declared by the phase or conventional in this project; verification is via the pytest batteries above.

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|---------------------|----------|
| LIVE-10 | 14-01 | 未运行 watch 时，搜索命令前 stat 漂移检测自动刷新（有上限，干净时零成本） | ✓ SATISFIED | Truths 1-6; traceability row "Phase 14 Complete" |
| QUAL-06 | 14-02, 14-03 | 分层更新深度下，向量滞后的搜索结果标记 staleness 状态 | ✓ SATISFIED | Truths 7-16; traceability row "Phase 14 Complete" |

**Orphaned requirements:** none — REQUIREMENTS.md traceability maps exactly LIVE-10 and QUAL-06 to Phase 14, both declared in plan frontmatter. ℹ️ Info: the QUAL-06 bullet line carries no checkbox (LIVE-10 shows `[x]`); the traceability table is consistent — cosmetic normalization only.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| (none — no TBD/FIXME/XXX/TODO/HACK in any phase file) | - | - | - | - |
| src/sif/search/bm25.py, vector.py | 53-67 | "placeholder" matches are SQL `?`-parameter joins | ℹ️ Info | Legitimate SQL, not stubs (pre-existing) |
| src/sif/cli/commands/search.py | 757 | "not available" is the reranker availability warning | ℹ️ Info | Pre-existing user message, not a stub |
| src/sif/database/repositories.py (WR-03), search.py (WR-04, IN-01, IN-02) | - | Open code-review findings | ℹ️ Info | All four documented PRE-EXISTING outside this phase's diff (14-REVIEW.md), recorded open in 14-REVIEW-DISPOSITION.md — tracked, not phase gaps |

### Test Quality Audit

| Test File | Linked Req | Active | Skipped | Circular | Assertion Level | Verdict |
|-----------|-----------|--------|---------|----------|-----------------|---------|
| test_drift.py | LIVE-10 | all | 0 | 0 | Value/behavioral (mtime equality, content, snapshot compares) | PASS |
| test_search.py (TestPreSearchRefresh, TestStalenessFormatMarker) | LIVE-10, QUAL-06 | 33 | 0 | 0 | Behavioral (exit codes, stderr/stdout separation, rendered output) | PASS |
| test_staleness.py | QUAL-06 | all | 1 env-guard* | 0 | Value (flag equality, real purge) | PASS |
| test_index_locking.py | LIVE-10 | 2+ | 0 | 0 | Behavioral (lock wait, zero acquisitions) | PASS |
| test_status.py / test_backend.py / test_incremental.py | QUAL-06 | all | 1 env-guard* | 0 | Value/behavioral | PASS |

*The two `pytest.skip("sqlite-vec not available")` hits are fixture environment guards; sqlite-vec IS present on this machine (real-vec0 tests ran green), so nothing was skipped in practice. No disabled requirement tests, no circular expected-value generation; lag-state e2e uses the real purge path, explicitly avoiding the raw-SQL fabrication the plan prohibited.

### Decision Coverage

All trackable CONTEXT.md decisions are honored by shipped artifacts: **13/13** (gate run, zero not-honored).

### Human Verification Required

### 1. D-05 refresh-failure leg (unverified prohibition)

**Test:** Inject a failure into the pre-search refresh (e.g. patch `sif.cli.commands.search.refresh_drifted` to raise `RuntimeError`) on a drifted tmp index and run `sif search <term>`.
**Expected:** Stderr shows `Pre-search refresh failed; searching the current index`, exit code 0, stale-index results still render — search never errors because of drift.
**Why human:** The except branch at `src/sif/cli/commands/search.py:200-210` is present and wired but no automated test exercises the failure transition (suite-wide grep for exception injection on detect_drift/refresh_drifted: zero hits). Presence checks cannot prove an untested branch's runtime behavior. Closing it needs only a ~5-line test — human decides accept vs. add-test.

### 2. SC2 perceived clean-search latency on a real index

**Test:** Run `sif search <real query>` against your real knowledge base with a clean (undrifted) index and judge the delay by feel.
**Expected:** The pre-command stat walk is imperceptible; no notices.
**Why human:** Performance feel on real hardware/data volume; the phase proved SC2 structurally (lockless/silent/writeless, test-green) and deliberately made no latency asserts (RESEARCH Pitfall 11).

### Gaps Summary

No blocking gaps. All 16 observable truths verified with behavioral evidence, all 9 artifacts exist/substantive/wired/flowing, all 6 key links wired, both requirements satisfied, full suite + quality gates green, decision coverage 13/13. The phase goal — fresh results without watch, and visible freshness — is achieved in the codebase.

Two items route to human verification: (1) the D-05 refresh-failure prohibition leg, which is implemented but has no exercising test (flagged per the test-tier fail-closed contract — the over-cap leg of the same prohibition IS test-enforced), and (2) a perceived-latency sanity check for SC2. Pre-existing defects WR-03/WR-04/IN-01/IN-02 remain recorded open in the disposition ledger, outside this phase's diff.

Documented deviations (both evidence-backed in 14-RESEARCH.md Open Questions RESOLVED, verified consistent with the code): drift compare is mtime-only (`documents.file_size` is never-refreshed body length — a size compare would false-positive forever); the staleness formula is "no rows in document_embeddings" gated on index-has-≥1-embedding (the literal "chunks but no embeddings" never fires given the Phase 12 purge contract — the D-08 invariant regression pins that purge).

---

_Verified: 2026-11-08T04:44:21Z_
_Verifier: Claude (gsd-verifier)_
