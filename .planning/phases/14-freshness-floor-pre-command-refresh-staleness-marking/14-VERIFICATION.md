---
phase: 14-freshness-floor-pre-command-refresh-staleness-marking
verified: 2026-11-12T07:48:33Z
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
covered_digest: "v4:sha256:b705b0d755a82f4c50b0844e8772fc9d6c45f6a556ad02dde30f5cf115f95d27"
behavior_unverified: 0
overrides_applied: 0
decision_coverage:
  honored: 13
  total: 13
  not_honored: []
re_verification:
  previous_status: passed
  previous_score: 16/16
  gaps_closed: []
  gaps_remaining: []
  regressions: []
---

# Phase 14: Freshness Floor (Pre-Command Refresh + Staleness Marking) Verification Report

**Phase Goal:** Search results are fresh even when no watch is running, and users can see how fresh their results are.
**Verified:** 2026-11-12T07:48:33Z at HEAD `b47f55f`
**Status:** passed
**Re-verification:** Yes — the prior passing report became stale after later phases changed covered files. This pass re-checks the full must-have contract at HEAD and recomputes the covered-input fingerprint.

## Why Re-verification Ran

The prior fingerprint no longer represented the current tree. In particular:

- Phase 15 added fusion, suggestions, and query-history behavior to `src/sif/cli/commands/search.py` and query-log storage to `src/sif/database/repositories.py`.
- Phase 16 added reranker options to the hybrid command.
- Phase 16.1 changed the search trio to use `open_initialized_database` and changed cache-expiry handling in `repositories.py`.
- The Phase 11 WR-01 fix changed `LLMCacheRepository.clear_expired` to delete expired rows in batches of 500.

The later opener does not alter the Phase 14 sequence: it still constructs the caller-supplied `Database`, calls `init_schema()`, and yields the same handle. In every search command, collection resolution still precedes `_pre_search_refresh`, and the refresh still precedes searcher/pipeline construction. The cache changes are confined to `LLMCacheRepository`; `DocumentRepository.list_stat_by_collection` and all staleness SQL remain intact.

## Goal Achievement

All three ROADMAP success criteria hold at HEAD:

- **SC1:** The CLI search trio performs a stat-based drift walk and BM25-only refresh before searching. Real-DB CLI tests prove modified content becomes findable, new files become searchable, and deleted files stop hitting without a watch process.
- **SC2:** The clean pre-search path performs no refresh work, acquires no index lock, emits no notice, and leaves documents unchanged. Over-cap drift skips refresh, warns with the count and remedy, and still exits 0. The cap and both opt-outs remain wired.
- **SC3:** The derived no-embeddings signal reaches `SearchResult.vectors_stale`, JSON and the other four CLI formats, MCP metadata, and the `sif status` Vector lag row. The zero-embedding display gate and vec0-missing degradation remain intact.

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | [14-01/SC1] With no watch, changed files are refreshed before `sif search`: modified text is findable, new files searchable, deleted files absent | VERIFIED | `TestPreSearchRefresh::test_search_finds_modified_content_and_notifies_on_stderr` and `::test_search_finds_new_file_and_drops_deleted_file` passed in the 192-test focused run; these use real files, a real SQLite index, and `CliRunner` |
| 2 | [14-01/SC2] A clean search performs no pre-refresh writes: no `{db}.lock`, no notice, documents unchanged | VERIFIED | `::test_clean_search_is_lockless_silent_and_writeless` passed; `TestPreSearchRefreshCoexistence::test_clean_search_never_enters_index_lock` also passed with zero lock events. Phase 15's separate, intentional query-history CRUD does not perform index-refresh work or alter the documents table |
| 3 | [14-01/SC2] Over-cap drift refreshes nothing, warns with count and `sif index update`, and exits 0 with current-index results | VERIFIED | `::test_over_cap_drift_skips_refresh_and_warns`, `::test_cap_boundary_count_equal_to_cap_refreshes`, and `::test_over_cap_never_parses_candidates` passed; document snapshots and lock absence are asserted |
| 4 | [14-01/D-01] Drift checking exists only in the CLI command layer; bench, MCP, and searchers do not invoke it | VERIFIED | `git grep -l 'sif.indexing.drift' -- src/sif` returned only `src/sif/cli/commands/search.py` |
| 5 | [14-01/D-03] Under-cap refresh against a held index lock waits up to `lock_wait_timeout`, then runs | VERIFIED | `TestPreSearchRefreshCoexistence::test_search_refresh_waits_out_held_lock_then_proceeds` passed; it asserts the wait lower bound and refreshed stored content |
| 6 | [14-01] Repeating the same drifted search refreshes once; the second stat walk is clean and write-free | VERIFIED | The modified-content e2e asserts empty second-run stderr; `::test_touch_only_drift_converges_across_searches` additionally spies that the second run never calls `refresh_drifted`. Both passed |
| 7 | [14-02/SC3] A BM25-refreshed-without-embed document has `vectors_stale=true`; a fully embedded document has false | VERIFIED | `TestLagStateEndToEnd::test_bm25_refreshed_after_embed_doc_is_marked_stale` passed using real embedding rows and a real `update_paths` purge; `test_to_dict_carries_vectors_stale_alongside_context_description` passed |
| 8 | [14-02] A zero-embeddings index marks nothing and emits no remedy nag | VERIFIED | `TestMarkVectorStaleness::test_display_gate_zero_embeddings_marks_nothing` passed; `mark_vector_staleness` returns before mutation when the embedded-id set is empty |
| 9 | [14-02] A missing vec0 table degrades to no markers without raising; status renders `n/a` | VERIFIED | `::test_vec0_missing_degrades_to_unmarked`, `TestEmbeddedDocumentIds::test_missing_vec0_table_returns_none`, and `TestVectorLag::test_vec0_missing_renders_na` passed |
| 10 | [14-02/D-10] `sif status` shows a Vector lag row counting documents without embeddings | VERIFIED | `_vector_lag_text` at `src/sif/cli/main.py:131-154` scans real document IDs against the embedded set; the row is added at line 211. `TestVectorLag::test_lag_count_renders_documents` passed |
| 11 | [14-02/D-11] MCP hybrid-search result metadata explicitly carries `vectors_stale` | VERIFIED | `src/sif/mcp/backend.py:189-198` forwards `r.vectors_stale`; `test_hybrid_search_mocks` passed with a true-value assertion |
| 12 | [14-02] Marking is idempotent and read-only | VERIFIED | `TestMarkVectorStaleness::test_marking_is_idempotent` passed. `src/sif/search/staleness.py` contains one `SELECT document_id FROM document_embeddings` scan and no write statement |
| 13 | [14-02] The query-time read-only scan needs no lock under concurrent embed and does not block or crash | VERIFIED | Regression check: `staleness.py` is unchanged since the prior verification and remains SELECT-only; missing-table degradation passed. The declared Phase 11 WAL/`busy_timeout` concurrency precondition remains in force, and no later change touched this path |
| 14 | [14-03/SC3] Every CLI format shows the marker: table annotation, JSON boolean including `--line-numbers`, CSV column, Markdown annotation, XML attribute | VERIFIED | All ten format tests passed. Current render sites are `search.py:86-99` (table), `models.py:253-268` (JSON), `search.py:324-346` (CSV), `349-370` (Markdown), and `373-405` (XML) |
| 15 | [14-03/D-13] At least one stale result produces exactly one stderr hint with count and `sif index embed`; `-q` suppresses it; stdout stays clean | VERIFIED | `_warn_stale_results` at `search.py:223-236` is called at all three output tails (lines 577, 735, 1048). All six hint tests passed, including JSON parsing, quiet suppression, and query/vsearch wiring |
| 16 | [14-03/D-12] No output format silently drops the signal | VERIFIED | The same crafted stale/fresh rows are asserted through all five formats, including dict-shaped `--line-numbers` rows; `_field(r, 'vectors_stale')` is used by every explicit renderer |

**Score:** 16/16 truths verified (0 present, behavior-unverified)

### Prohibition Verification

All seven declared prohibitions are test-tier and have enforcement evidence at HEAD.

| Prohibition | Status | Enforcement Evidence |
|-------------|--------|----------------------|
| 14-01 P1: pre-command refresh never computes embeddings | ENFORCED | `drift.py` imports no embedder and calls only `IncrementalIndexer.update_paths`; `test_update_paths_purges_embeddings_of_modified_doc` passed |
| 14-01 P2: refresh notices never write to stdout | ENFORCED | `test_json_stdout_stays_clean_with_refresh_notice_on_stderr` parses pure stdout JSON while asserting the notice on stderr; quiet-mode tests passed |
| 14-01 P3: drift never makes search fail | ENFORCED | Both the over-cap test and `test_refresh_failure_warns_and_search_proceeds` passed; the latter injects a refresh exception and asserts exit 0 plus stale-index results |
| 14-02 P1: staleness is never persisted or maintained | ENFORCED | `staleness.py` is SELECT-only; idempotency and real-purge tests passed |
| 14-02 P2: markers/notices/status never include document content | ENFORCED | Current code emits only computed booleans, integer counts, and fixed command strings; output tests pin those values |
| 14-02 P3: no per-result embedding queries | ENFORCED | One constant scan per non-empty result set; `test_empty_results_never_queries` passed and no per-result SQL loop exists |
| 14-03 P1: marker rendering never injects document text into XML/CSV | ENFORCED | XML and CSV emit fixed `true`/`false` literals; XML parseability tests passed |

No unverified prohibitions remain.

### Required Artifacts

The declared artifact verifier passed all 9/9 artifacts. Manual wiring and data-flow checks also passed.

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `src/sif/indexing/drift.py` | Presentation-free drift detection and flock-wrapped BM25 refresh | VERIFIED | `DriftReport`, `detect_drift`, and `refresh_drifted` at lines 44, 61, and 120; no CLI/Rich imports; unchanged by later phases |
| `src/sif/database/repositories.py` | Content-free stored stat snapshot | VERIFIED | `list_stat_by_collection` at lines 201-213 executes exactly `SELECT path, mtime FROM documents WHERE collection_id = ?`; cache-expiry edits begin much later at line 519 and do not intersect it |
| `src/sif/config/settings.py` | Refresh enable toggle and file cap | VERIFIED | Fields at lines 95-108; live defaults probe returned `True/100`; generator registration and docs remain present |
| `tests/unit/indexing/test_drift.py` | Deterministic drift battery | VERIFIED | 13 tests passed, covering clean/new/edit/touch/delete/missing-root/refresh/convergence/failure behavior |
| `src/sif/search/staleness.py` | Derived, batched, degrading staleness enrichment | VERIFIED | `embedded_document_ids` and `mark_vector_staleness` at lines 34 and 52; unchanged by later phases; 12 tests passed |
| `src/sif/core/models.py` | `SearchResult.vectors_stale` and `to_dict` key | VERIFIED | Field at line 251 and serialized key at line 267 |
| `src/sif/cli/main.py` | Vector lag status row | VERIFIED | Derived helper and row at lines 131-154 and 203-211; all four status states tested |
| `tests/unit/search/test_staleness.py` | Staleness behavior battery | VERIFIED | 12 tests passed with real vec0 coverage; no test was skipped in this environment |
| `src/sif/cli/commands/search.py` | Trio refresh wiring, all format markers, stderr hint | VERIFIED | Refresh calls at lines 477, 666, and 880 remain before constructors at 487, 680, and 941; all formatter and hint tests passed |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `cli/commands/search.py` | `indexing/drift.py` | `detect_drift` / `refresh_drifted` after collection resolution and before search construction | WIRED | All three call sites and constructor ordering inspected directly |
| `indexing/drift.py` | `indexing/incremental.py` | `update_paths` under one `index_lock` window | WIRED | `refresh_drifted` lines 139-151; purge/convergence tests passed |
| `indexing/drift.py` | `database/repositories.py` | `list_stat_by_collection` snapshot | WIRED | Call at `drift.py:96`, implementation at `repositories.py:201-213` |
| `search/bm25.py`, `vector.py`, `hybrid.py` | `search/staleness.py` | `mark_vector_staleness` in each `_attach_contexts` | WIRED | Calls at `bm25.py:122`, `vector.py:135`, and `hybrid.py:123`; delegation test passed |
| `mcp/backend.py` | `core/models.py` | Explicit metadata forwarding | WIRED | `backend.py:197`; MCP test passed |
| `cli/main.py` | `search/staleness.py` | Shared `embedded_document_ids` scan for Vector lag | WIRED | `main.py:142`; status tests passed |
| CLI formatters/table | `core/models.py` | Dual-shape `_field(r, 'vectors_stale')` reader | WIRED | All explicit renderer sites inspected; both object and dict shapes tested |

The `verify.key-links` verb passed 5/7 machine-parseable declarations. It could not parse two plan `from` values containing parenthetical descriptions (`bm25.py (+ vector.py, hybrid.py)` and `search.py (formatters + table render)`); those are declaration-parser limitations, not missing wiring. Both were manually verified as above.

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|--------------------|--------|
| Drift refresh chain | `DriftReport.paths_by_collection` | Filesystem stat walk plus real `documents.path/mtime` rows, then `update_paths` | Yes — real-file e2e tests passed | FLOWING |
| Staleness marker chain | `vectors_stale` | Real `document_embeddings` scan to `SearchResult`, then serializers/MCP | Yes — real-purge and format/MCP tests passed | FLOWING |
| Status Vector lag row | Lagging document count | `embedded_document_ids` plus real `documents.id` scan | Yes — count and degradation states tested | FLOWING |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Search CLI, staleness, and drift contracts | `env -u FORCE_COLOR NO_COLOR=1 python -m pytest tests/unit/cli/test_search.py tests/unit/search/test_staleness.py tests/unit/indexing/test_drift.py --no-cov` | 192 passed in 1.95s | PASS |
| Lock coexistence, status, MCP, and incremental purge | `env -u FORCE_COLOR NO_COLOR=1 python -m pytest tests/unit/cli/test_index_locking.py tests/unit/cli/test_status.py tests/unit/mcp/test_backend.py tests/unit/indexing/test_incremental.py --no-cov` | 62 passed in 1.52s | PASS |
| Generated documentation consistency | `env -u FORCE_COLOR NO_COLOR=1 python -m pytest tests/test_docs.py --no-cov` | 13 passed in 0.68s | PASS |
| Refresh defaults | Live `Settings` assertion | `search_refresh_enabled=True`, `search_refresh_max_files=100` | PASS |
| Full-suite HEAD gate | Supplied HEAD verification evidence for `b47f55f` | 1591 passed, 1 skipped, coverage 95.18%; ruff, format, and ty clean | PASS (not rerun in this focused pass) |

### Probe Execution

SKIPPED — no phase-declared or conventional `scripts/*/tests/probe-*.sh` probes exist. Verification uses the pytest batteries above.

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| LIVE-10 | 14-01 | Pre-search stat drift detection and bounded automatic refresh without watch | SATISFIED | Truths 1-6; 192-test and lock batteries passed; traceability marks Phase 14 Complete |
| QUAL-06 | 14-02, 14-03 | Mark search results whose vectors lag BM25/FTS | SATISFIED | Truths 7-16; staleness, format, status, and MCP tests passed; traceability marks Phase 14 Complete |

**Orphaned requirements:** None. REQUIREMENTS.md maps exactly LIVE-10 and QUAL-06 to Phase 14, and the plans claim both.

### Anti-Patterns Found

No blocking or warning anti-patterns found. Debt-marker scans over the covered source and test files found no `TBD`, `FIXME`, `XXX`, `TODO`, `HACK`, or placeholder implementation markers. Grep hits for “not available” are installed-backend error messages; `placeholders` identifiers are SQL parameter lists, not stubs.

### Test Quality Audit

| Test File | Linked Req | Active | Skipped | Circular | Assertion Level | Verdict |
|-----------|------------|--------|---------|----------|-----------------|---------|
| `test_search.py` | LIVE-10, QUAL-06 | 167 | 0 | 0 | Behavioral: real DB/files, exit codes, stdout/stderr, exact rendered values | PASS |
| `test_staleness.py` | QUAL-06 | 12 | 0 | 0 | Value and behavioral: exact flags, real purge, delegation | PASS |
| `test_drift.py` | LIVE-10 | 13 | 0 | 0 | Value and behavioral: exact drift sets, stored mtimes/content, convergence | PASS |
| `test_index_locking.py` | LIVE-10 | 5 | 0 | 0 | Behavioral: held-lock wait and zero-acquisition spy | PASS |
| `test_status.py`, `test_backend.py`, `test_incremental.py` | QUAL-06, LIVE-10 | 57 | 0 | 0 | Value and behavioral: rendered states, metadata, persisted purge invariant | PASS |

The `pytest.skip` calls in staleness/incremental fixtures are environment guards for unavailable sqlite-vec, not disabled requirement tests. sqlite-vec is available here and every collected test ran. No expected values are generated by the system under test. Assertions exercise behavior rather than mere symbol existence.

One later-phase interaction was explicitly disconfirmed as a false positive: Phase 15 now writes query-history rows on searches. The Phase 14 clean-refresh assertion remains scoped to index freshness work — no index lock, no refresh, unchanged documents — and does not claim that unrelated, explicitly required history CRUD is absent.

### Decision Coverage

The decision-coverage gate passed: 13/13 trackable CONTEXT.md decisions are honored, with zero not-honored entries. The gate is non-blocking and produced no warnings.

### Human Verification

None outstanding. The prior UAT completed 2/2 items, including the clean-search latency measurement (+105 ms median pre-command walk delta on a 3000-doc corpus). This re-verification found no change to the drift detector or clean-refresh branch; the opener substitution preserves the same initialization sequence, and the current structural and behavioral regression tests all pass. No new visual, external-service, or behavior-unverified item was identified.

### Advisory (New Scope, Unevidenced)

Re-verification ran; this section is included per the evidence-gate contract.

None. No new-scope blocker or unevidenced regression was found.

### Gaps Summary

**No gaps found.** All 16 observable truths are verified at HEAD `b47f55f`; all 9 artifacts are substantive, wired, and data-flowing; all 7 key-link groups are connected; all 7 prohibitions have enforcement evidence; both requirements remain satisfied; and decision coverage is 13/13.

The Phase 16.1 opener adoption did not move or weaken the pre-search refresh check. The WR-01 batched cache deletion did not alter `DocumentRepository.list_stat_by_collection` or any staleness SQL. Later query-history and reranker features remain outside the Phase 14 drift-refresh branch and did not regress its tests.

Fresh covered-input fingerprint computed through `verification.fingerprint`: `v4:sha256:b705b0d755a82f4c50b0844e8772fc9d6c45f6a556ad02dde30f5cf115f95d27` over 30 files.

---

_Verified: 2026-11-12T07:48:33Z_
_Verifier: Claude (gsd-verifier)_
