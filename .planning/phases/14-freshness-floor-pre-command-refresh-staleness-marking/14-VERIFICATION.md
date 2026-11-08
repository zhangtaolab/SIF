---
phase: 14-freshness-floor-pre-command-refresh-staleness-marking
verified: 2026-11-08T05:22:24Z
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
covered_digest: "v4:sha256:249487dcd84f0cd2413d6069fbcda8d77ddf9aee7bc9bc6baf43d54d6f484ac8"
behavior_unverified: 0
overrides_applied: 0
re_verification:
  previous_status: passed
  previous_score: 16/16
  gaps_closed:
    - "D-05 refresh-failure prohibition leg — previously flagged UNVERIFIED-PROHIBITION (no exercising test); now test-enforced by TestPreSearchRefresh::test_refresh_failure_warns_and_search_proceeds (commit 1062afc), run green this pass"
    - "Prior human-verification item 1 (D-05 refresh-failure leg) — closed via UAT (14-UAT.md: resolved by adding the exercising test)"
    - "Prior human-verification item 2 (SC2 perceived clean-search latency) — closed via UAT (14-UAT.md: measured +105 ms median delta on a 3000-doc corpus, silent, exit 0)"
  gaps_remaining: []
  regressions: []
---

# Phase 14: Freshness Floor (Pre-Command Refresh + Staleness Marking) Verification Report

**Phase Goal:** Search results are fresh even when no watch is running, and users can see how fresh their results are.
**Verified:** 2026-11-08T05:22:24Z
**Status:** passed
**Re-verification:** Yes — the prior report (2026-11-08T04:44:21Z) went stale after post-verification source changes; this pass re-verifies the full must-have set against the current tree and recomputes the covered-set fingerprint.

## Why Re-verification Ran

Two source commits landed after the prior report's timestamp, both inside the covered set:

1. **1062afc** — `test_refresh_failure_warns_and_search_proceeds` added (tests/unit/cli/test_search.py): exercises the D-05 except branch that the prior report flagged as present-but-untested.
2. **2307ba8** — WR-01 fix: parse failures surfaced and counted. `IncrementalResult.failed` (incremental.py:55), `error` outcome counted in both `update_collection` (:162) and `update_paths` (:262), `logger.warning` on parse errors (:304 area), `refresh_drifted` accumulates `failed` (drift.py:151), and the refresh notice gains `N failed to parse` with a yellow style when any parse failed (search.py:132-137, 203-209). Deliberate design: parse-failed files stay drift-visible and re-warn rather than silently converge — documented in docstrings and pinned by two new regression tests.

Everything below was re-checked against the current tree, not the prior report's claims.

## Goal Achievement

All three ROADMAP success criteria are demonstrably met in the current codebase:

- **SC1** (fresh without watch): the search trio stat-walks searched collections and BM25-refreshes drift before searching — re-proven green this pass, including the new failure-leg and parse-failure-leg tests.
- **SC2** (near-zero clean cost + capped refresh): clean search is lockless/silent/writeless; over-cap drift skips refresh, warns, exits 0; the D-05 refresh-failure leg is now also test-enforced. UAT measured the clean-index walk delta at +105 ms median on a 3000-doc corpus (2/2 passed).
- **SC3** (visible staleness in table and JSON): `SearchResult.vectors_stale` (models.py:225, to_dict :241) is derived at query time from a real `document_embeddings` scan and renders in all five output formats, MCP metadata, and a `sif status` Vector lag row.

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | [14-01/SC1] No watch running, `sif search` on changed files returns refreshed content (modified findable, new searchable, deleted no longer hits) | ✓ VERIFIED | `TestPreSearchRefresh::test_search_finds_modified_content_and_notifies_on_stderr` and `::test_search_finds_new_file_and_drops_deleted_file` — tests/unit/cli/test_search.py re-run green this pass (real DB + CliRunner) |
| 2 | [14-01/SC2] Clean index search performs zero writes: no `{db}.lock`, no notice, documents unchanged | ✓ VERIFIED | `::test_clean_search_is_lockless_silent_and_writeless` green this pass; zero-lock spy in test_index_locking.py green (153-test batch) |
| 3 | [14-01/SC2] Over-cap drift: nothing refreshed, stderr warning names count + `sif index update` remedy, exit 0 with stale hits | ✓ VERIFIED | `::test_over_cap_drift_skips_refresh_and_warns` green this pass (batch re-run of full test_search.py) |
| 4 | [14-01/D-01] Drift check exists only in CLI command layer; bench/MCP/searchers never invoke it | ✓ VERIFIED | `git grep -l "sif.indexing.drift" -- src/sif` → `src/sif/cli/commands/search.py` ONLY (re-run this pass) |
| 5 | [14-01/D-03] Under-cap refresh vs held index lock waits up to lock_wait_timeout then runs (wait-then-run) | ✓ VERIFIED | `TestPreSearchRefreshCoexistence::test_search_refresh_waits_out_held_lock_then_proceeds` green this pass (test_index_locking.py batch) |
| 6 | [14-01] Same drifted search twice refreshes once (stateless, stat-decides) | ✓ VERIFIED | Second-run `stderr == ""` asserted in the e2e test, green this pass. Scope note: the WR-01 fix deliberately makes **unparseable** drifted files non-convergent (still drift-visible, re-warn every pass) — that is the documented intended design (docstrings + `test_unparseable_drift_warns_each_search_and_never_converges`, green), not a violation: the truth's scenario (a refreshable drift burst) converges exactly as specified |
| 7 | [14-02/SC3] BM25-refreshed-without-embed doc carries vectors_stale=true in results and `--json`; fully embedded carries false | ✓ VERIFIED | `TestLagStateEndToEnd::test_bm25_refreshed_after_embed_doc_is_marked_stale` green this pass (test_staleness.py batch, 76 passed) |
| 8 | [14-02] Zero-embeddings index: no markers, no nagging (display gate) | ✓ VERIFIED | `TestMarkVectorStaleness::test_display_gate_zero_embeddings_marks_nothing` green this pass |
| 9 | [14-02] vec0 table missing: degrades to no markers, never raises; status renders n/a | ✓ VERIFIED | `::test_vec0_missing_degrades_to_unmarked` + `TestVectorLag::test_vec0_missing_renders_na` green this pass |
| 10 | [14-02/D-10] `sif status` shows a Vector lag row naming the count of docs without embeddings | ✓ VERIFIED | `TestVectorLag::test_lag_count_renders_documents` green this pass; `_vector_lag_text` + `table.add_row("Vector lag", ...)` confirmed at main.py:133-156, 210 |
| 11 | [14-02/D-11] MCP query response carries the flag via backend.hybrid_search metadata | ✓ VERIFIED | Explicit forward `metadata["vectors_stale"]: r.vectors_stale` confirmed at backend.py:109-117; test_backend.py green this pass |
| 12 | [14-02] Marking is idempotent and read-only | ✓ VERIFIED | `::test_marking_is_idempotent` green this pass; staleness.py (77 lines) contains only one read-only SELECT, zero writes (re-inspected) |
| 13 | [14-02] Read-only scan needs no lock under concurrent embed; never blocks/crashes | ✓ VERIFIED | Module issues exactly one `SELECT document_id FROM document_embeddings` (re-inspected); crash-degrade tested green; concurrent-read non-blocking rests on the Phase 11 WAL + busy_timeout contract (LIVE-06 — precondition declared in the plan's own truth text) |
| 14 | [14-03/SC3] Every CLI format shows the marker: table dim annotation, JSON boolean (incl. --line-numbers dict), CSV column, MD annotation, XML attribute | ✓ VERIFIED | Format battery green this pass (test_search.py batch); render sites confirmed in current search.py: table `:95`, count `:231`, CSV header `:246`/value `:256`, MD `:269`, XML `:297-299` |
| 15 | [14-03/D-13] ≥1 stale result → exactly one stderr line naming count + `sif embed` remedy; `-q` suppresses; stdout clean | ✓ VERIFIED | `test_remedy_hint_one_stderr_line_names_count` green this pass; `_warn_stale_results` at search.py:222+ |
| 16 | [14-03/D-12] No format silently drops the signal | ✓ VERIFIED | Per-format battery green this pass; `_field(r, 'vectors_stale')` dual-shape reader at all 5 explicit renderer sites (grep re-run: 5 hits) |

**Score:** 16/16 truths verified (0 present, behavior-unverified)

### Prohibition Verification (all 7 test-tier — all enforced)

| Prohibition | Status | Enforcement Evidence |
|-------------|--------|----------------------|
| 14-01 P1: refresh must NEVER embed (13-D02) | ✓ ENFORCED | drift.py imports no embedder; `test_update_paths_purges_embeddings_of_modified_doc` green (test_incremental.py batch this pass) |
| 14-01 P2: notices must NEVER write to stdout (D-07) | ✓ ENFORCED | stderr-purity asserts across TestPreSearchRefresh, green this pass — including the new WR-01 quiet-mode assert (`failed to parse` absent from `-q` stderr) |
| 14-01 P3: search must NEVER error from drift (D-05) | ✓ ENFORCED | **Both legs now test-enforced**: over-cap leg `test_over_cap_drift_skips_refresh_and_warns`; refresh-failure leg `test_refresh_failure_warns_and_search_proceeds` (added 1062afc) — patches `refresh_drifted` to raise, asserts exit 0 + stderr warning + stale results served + recovery refresh. Both run green this pass. The prior report's UNVERIFIED-PROHIBITION flag is closed |
| 14-02 P1: staleness NEVER persisted (D-08) | ✓ ENFORCED | staleness.py SELECT-only (re-inspected); idempotency test green; D-08 invariant regressions in test_incremental.py green this pass |
| 14-02 P2: markers/notices NEVER include content | ✓ ENFORCED | Integer counts + fixed strings only (re-inspected `_refresh_notice`, `_warn_stale_results`, status row); tests pin counts/commands |
| 14-02 P3: NEVER per-result queries | ✓ ENFORCED | One batched scan per result set in code; `test_empty_results_never_queries` green |
| 14-03 P1: marker NEVER interpolates document text into XML/CSV | ✓ ENFORCED | Fixed boolean literal `vectors_stale="{true|false}"` (search.py:297-299, re-inspected); XML parseability test green |

No unverified prohibitions remain.

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `src/sif/indexing/drift.py` | DriftReport / detect_drift / refresh_drifted, presentation-free | ✓ VERIFIED | 153 lines; symbols at :44/:61/:120; no click/Console imports; mtime-primary docstring; WR-01 `failed` accumulation at :151; index_lock only in refresh_drifted |
| `src/sif/database/repositories.py` | `list_stat_by_collection` content-free snapshot | ✓ VERIFIED | Present at :200; test_drift.py snapshot asserts green |
| `src/sif/config/settings.py` | `search_refresh_enabled` + `search_refresh_max_files` | ✓ VERIFIED | Fields at :88/:94; live defaults probe re-run: True/100; docs grep 1/1/3 |
| `tests/unit/indexing/test_drift.py` | Deterministic drift battery | ✓ VERIFIED | 13 tests green this pass, incl. new `test_unparseable_drift_counts_failed_and_stays_drift_visible` |
| `src/sif/search/staleness.py` | mark_vector_staleness / embedded_document_ids | ✓ VERIFIED | 77 lines; one constant scan; None-on-OperationalError; display gate |
| `src/sif/core/models.py` | SearchResult.vectors_stale + to_dict key | ✓ VERIFIED | Field :225, to_dict :241 (re-inspected) |
| `src/sif/cli/main.py` | Vector lag status row | ✓ VERIFIED | `_vector_lag_text` + row add at :210; test_status.py green |
| `tests/unit/search/test_staleness.py` | Staleness battery | ✓ VERIFIED | 12 tests green this pass |
| `src/sif/cli/commands/search.py` (14-03) | Markers in all formatters + stderr hint | ✓ VERIFIED | All 5 renderer sites re-confirmed in current file; format battery green |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|----|--------|---------|
| cli/commands/search.py | indexing/drift.py | detect_drift/refresh_drifted in `_pre_search_refresh`, called from all three commands | ✓ WIRED | Helper present (search.py:132+); trio call sites re-confirmed; sole-importer grep clean (D-01) |
| indexing/drift.py | indexing/incremental.py | update_paths inside index_lock | ✓ WIRED | refresh_drifted wraps update_paths; `failed` now accumulated (drift.py:151) |
| indexing/drift.py | database/repositories.py | list_stat_by_collection snapshot | ✓ WIRED | Present (:200), exercised by green tests |
| search/bm25.py + vector.py + hybrid.py | search/staleness.py | mark_vector_staleness in each `_attach_contexts` | ✓ WIRED | Grep re-run: import + call in all three (bm25.py:10/:122, vector.py:10/:135, hybrid.py:12/:115) |
| mcp/backend.py | core/models.py | r.vectors_stale into metadata | ✓ WIRED | Explicit forward at backend.py:109-117 |
| cli/main.py | search/staleness.py | Vector lag row from embedded_document_ids | ✓ WIRED | Import :17, call :144, row :210 |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|--------------------|--------|
| staleness marker chain | `vectors_stale` | real `document_embeddings` scan → SearchResult → to_dict/formatters/MCP/status | Yes — real-purge e2e green this pass | ✓ FLOWING |
| drift chain | `DriftReport.paths_by_collection` | real filesystem stat walk × real `documents` table → update_paths | Yes — e2e tests mutate real files, green this pass; WR-01 adds honest failed-count flow (real parse errors → counted, named) | ✓ FLOWING |
| status Vector lag row | lagging count | `embedded_document_ids` + `documents` scan | Yes — TestVectorLag green | ✓ FLOWING |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| NEW: D-05 refresh-failure leg (prior gap) | `pytest tests/unit/cli/test_search.py::TestPreSearchRefresh::test_refresh_failure_warns_and_search_proceeds --no-cov` | 1 passed | ✓ PASS |
| NEW: WR-01 unparseable drift — CLI (warn + count + non-convergence + -q) | `pytest ...::test_unparseable_drift_warns_each_search_and_never_converges --no-cov` | 1 passed | ✓ PASS |
| NEW: WR-01 unparseable drift — module (failed=1, stays drift-visible, content untouched) | `pytest tests/unit/indexing/test_drift.py::TestRefreshDrifted::test_unparseable_drift_counts_failed_and_stays_drift_visible --no-cov` | 1 passed | ✓ PASS |
| Phase regression batch 1 (search CLI + drift + incremental + locking) | `pytest tests/unit/cli/test_search.py tests/unit/indexing/test_drift.py tests/unit/indexing/test_incremental.py tests/unit/cli/test_index_locking.py --no-cov` | 153 passed | ✓ PASS |
| Phase regression batch 2 (staleness + searchers + status + MCP) | `pytest tests/unit/search/test_staleness.py tests/unit/search/test_bm25.py tests/unit/search/test_vector.py tests/unit/cli/test_status.py tests/unit/mcp/test_backend.py --no-cov` | 76 passed | ✓ PASS |
| Full suite (once; coverage via addopts, fail_under=90) | `env -u FORCE_COLOR NO_COLOR=1 python -m pytest` | 1231 passed, 1 skipped, 94.55% ≥ 90 | ✓ PASS |
| Quality gates | `ruff check src tests` + `ruff format --check src tests` + `ty check src/sif` | all green | ✓ PASS |
| Settings defaults + docs | live Settings probe + docs greps | True/100; counts 1/1/3 | ✓ PASS |

### Probe Execution

Step 7c: SKIPPED — no `scripts/*/tests/probe-*.sh` declared by the phase or conventional in this project; verification is via the pytest batteries above.

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|---------------------|--------|----------|
| LIVE-10 | 14-01 | 未运行 watch 时，搜索命令前 stat 漂移检测自动刷新（有上限，干净时零成本） | ✓ SATISFIED | Truths 1-6; REQUIREMENTS.md traceability row "Phase 14 Complete"; WR-01 hardens the failure surface (counted, visible, still never a search error) |
| QUAL-06 | 14-02, 14-03 | 分层更新深度下，向量滞后的搜索结果标记 staleness 状态 | ✓ SATISFIED | Truths 7-16; traceability row "Phase 14 Complete" |

**Orphaned requirements:** none — REQUIREMENTS.md traceability maps exactly LIVE-10 and QUAL-06 to Phase 14, both declared in plan frontmatter (14-01: LIVE-10; 14-02/14-03: QUAL-06).

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| (none — debt-marker scan over all 14 covered source files re-run this pass: zero TBD/FIXME/XXX/TODO/HACK/PLACEHOLDER hits) | - | - | - | - |

Both post-verification source commits (1062afc, 2307ba8) touched covered files — those files are in-contract for this re-verification under the evidence gate, and the scan is clean. The pre-existing review findings WR-03/WR-04/IN-01/IN-02 remain documented as outside this phase's diff (14-REVIEW-DISPOSITION.md); WR-01 was fixed by 2307ba8 and is verified above.

### Test Quality Audit

| Test File | Linked Req | Active | Skipped | Circular | Assertion Level | Verdict |
|-----------|-----------|--------|---------|----------|-----------------|---------|
| test_drift.py | LIVE-10 | 13 | 0 | 0 | Value/behavioral (mtime equality, snapshot compares, failed-count equality) | PASS |
| test_search.py (TestPreSearchRefresh + staleness formats) | LIVE-10, QUAL-06 | all | 0 | 0 | Behavioral (exit codes, stderr/stdout separation, rendered output, non-convergence loop asserted twice) | PASS |
| test_staleness.py | QUAL-06 | 12 | 1 env-guard* | 0 | Value (flag equality, real purge) | PASS |
| test_index_locking.py | LIVE-10 | all | 0 | 0 | Behavioral (lock wait, zero acquisitions) | PASS |
| test_status.py / test_backend.py / test_incremental.py | QUAL-06, LIVE-10 | all | 1 env-guard* | 0 | Value/behavioral | PASS |

*`pytest.skip("sqlite-vec not available")` is a fixture environment guard; sqlite-vec is present on this machine (real-vec0 tests ran green; the full suite's single skip is unrelated to phase files). No disabled requirement tests; no circular expected-value generation — the new D-05 test uses patch-based exception injection (a legitimate failure-simulation technique, not self-generated expectations), and the WR-01 tests use deterministic invalid-UTF-8 bytes as input.

### Decision Coverage

All trackable CONTEXT.md decisions are honored by shipped artifacts: **13/13** (gate re-run this pass, zero not-honored).

### Human Verification

None outstanding. Both items from the prior report are discharged with recorded evidence in 14-UAT.md (status: complete, 2/2 passed):

1. D-05 refresh-failure leg — resolved by adding the exercising test (commit 1062afc, verified green this pass).
2. SC2 perceived clean-search latency — resolved by measurement on a 3000-doc corpus: +105 ms median pre-command walk delta, silent, exit 0, no lock file, no notice; startup (~711 ms) dominates total command time.

### Advisory (New Scope, Unevidenced)

Re-verification ran; this section is included per the evidence-gate contract.

| # | Finding | Category | Why Advisory |
|---|---------|----------|--------------|
| 1 | (none) | - | No new-scope findings — both post-verification source changes were in-contract (files in the covered set) and are positively verified by new green tests, not merely unflagged |

### Gaps Summary

No gaps. All 16 observable truths re-verified against the current tree with behavioral evidence, all 9 artifacts exist/substantive/wired/flowing, all 6 key links wired, all 7 test-tier prohibitions now test-enforced (the formerly flagged D-05 refresh-failure leg closed by commit 1062afc), both requirements satisfied, full suite 1231 passed @ 94.55% ≥ 90 floor, ruff/format/ty green, decision coverage 13/13, UAT complete 2/2, SECURITY verified with threats_open 0 (7/7 closed).

The WR-01 post-verification change (2307ba8) strengthens rather than regresses the phase contract: parse failures during a pre-search refresh are now counted (`IncrementalResult.failed`), logged (`logger.warning` on callback-less hosts), surfaced in the one-line stderr notice (`N failed to parse`, yellow), and deliberately never converged away — unparseable drift stays visible and re-warns, so a genuinely stale file can no longer masquerade as refreshed. Its deliberate non-convergence design is documented in docstrings and pinned by two regression tests, both green.

Documented deviations (unchanged, both evidence-backed in 14-RESEARCH.md Open Questions RESOLVED, consistent with the code): drift compare is mtime-only (`documents.file_size` is never-refreshed body length); the staleness formula is "no rows in document_embeddings" gated on index-has-≥1-embedding.

Fresh covered-set fingerprint recomputed over the current tree: `v4:sha256:249487dcd84f0cd2413d6069fbcda8d77ddf9aee7bc9bc6baf43d54d6f484ac8` (30 files) — supersedes the stale `v4:sha256:68d16be5...` from the prior report.

---

_Verified: 2026-11-08T05:22:24Z_
_Verifier: Claude (gsd-verifier)_
