---
phase: 21-scale-maintenance-embedder-identity
verified: 2026-11-18T07:12:30Z
status: passed
score: 63/63 must-haves verified
covered_files:
  - .planning/phases/21-scale-maintenance-embedder-identity/21-01-PLAN.md
  - .planning/phases/21-scale-maintenance-embedder-identity/21-01-SUMMARY.md
  - .planning/phases/21-scale-maintenance-embedder-identity/21-02-PLAN.md
  - .planning/phases/21-scale-maintenance-embedder-identity/21-02-SUMMARY.md
  - .planning/phases/21-scale-maintenance-embedder-identity/21-03-PLAN.md
  - .planning/phases/21-scale-maintenance-embedder-identity/21-03-SUMMARY.md
  - .planning/phases/21-scale-maintenance-embedder-identity/21-04-PLAN.md
  - .planning/phases/21-scale-maintenance-embedder-identity/21-04-SUMMARY.md
  - .planning/phases/21-scale-maintenance-embedder-identity/21-05-PLAN.md
  - .planning/phases/21-scale-maintenance-embedder-identity/21-05-SUMMARY.md
  - .planning/phases/21-scale-maintenance-embedder-identity/21-06-PLAN.md
  - .planning/phases/21-scale-maintenance-embedder-identity/21-06-SUMMARY.md
  - .planning/phases/21-scale-maintenance-embedder-identity/21-07-PLAN.md
  - .planning/phases/21-scale-maintenance-embedder-identity/21-07-SUMMARY.md
  - .planning/phases/21-scale-maintenance-embedder-identity/21-08-PLAN.md
  - .planning/phases/21-scale-maintenance-embedder-identity/21-08-SUMMARY.md
  - docs/architecture.md
  - docs/cli-reference.md
  - docs/configuration.md
  - scripts/generate_config_ref.py
  - src/sif/cli/commands/bench.py
  - src/sif/cli/commands/eval.py
  - src/sif/cli/commands/index.py
  - src/sif/cli/commands/search.py
  - src/sif/cli/main.py
  - src/sif/config/settings.py
  - src/sif/database/database.py
  - src/sif/database/maintenance.py
  - src/sif/database/repositories.py
  - src/sif/database/schema.py
  - src/sif/embedding/embedder.py
  - src/sif/embedding/factory.py
  - src/sif/embedding/identity.py
  - src/sif/embedding/manager.py
  - src/sif/embedding/prompts.py
  - src/sif/embedding/roles.py
  - src/sif/indexing/embed_writer.py
  - src/sif/indexing/watcher.py
  - src/sif/mcp/backend.py
  - src/sif/models/embedding.py
  - src/sif/search/context_attach.py
  - src/sif/search/expansion.py
  - src/sif/search/hybrid.py
  - src/sif/search/staleness.py
  - src/sif/search/vector.py
  - tests/conftest.py
  - tests/integration/test_embed_idempotency.py
  - tests/integration/test_maintenance.py
  - tests/unit/cli/test_bench.py
  - tests/unit/cli/test_eval.py
  - tests/unit/cli/test_index.py
  - tests/unit/cli/test_index_locking.py
  - tests/unit/cli/test_main.py
  - tests/unit/cli/test_search.py
  - tests/unit/cli/test_status.py
  - tests/unit/cli/test_watch_cmd.py
  - tests/unit/database/test_embedded_documents.py
  - tests/unit/database/test_maintenance.py
  - tests/unit/database/test_schema.py
  - tests/unit/embedding/test_embedder_impl.py
  - tests/unit/embedding/test_identity.py
  - tests/unit/embedding/test_manager.py
  - tests/unit/embedding/test_openai_embedder.py
  - tests/unit/indexing/test_embed_writer.py
  - tests/unit/indexing/test_watcher.py
  - tests/unit/inference/test_query_expander.py
  - tests/unit/mcp/test_backend.py
  - tests/unit/search/test_bench_snapshot.py
  - tests/unit/search/test_bm25.py
  - tests/unit/search/test_context_attach.py
  - tests/unit/search/test_hybrid.py
  - tests/unit/search/test_staleness.py
  - tests/unit/search/test_vector.py
covered_digest: "v4:sha256:3dc1f61c4f5d8f24468d21c2040027e53ab293cbc6a9c08fd26bd175d033d460"
behavior_unverified: 0
overrides_applied: 0
re_verification:
  previous_status: passed
  previous_score: 63/63
  gaps_closed: []
  gaps_remaining: []
  regressions: []
---

# Phase 21: Scale, Maintenance + Embedder Identity Verification Report

**Phase Goal:** Large-corpus maintenance is safe and fast, and the index knows which embedder produced its vectors — the locked precondition for the Harrier evaluation (23) and the stable embed contract the MCP layer (22) consumes.
**Verified:** 2026-11-18T07:12:30Z
**Status:** passed
**Re-verification:** Yes — re-checked against the current codebase after Phases 22–24 changed covered source (MCP shell replaced, breadcrumb overlay added, docs regenerated). Properties were re-verified, not original file locations.

## Goal Achievement

### Roadmap Success Criteria

| # | Success Criterion | Status | Evidence (current codebase) |
| - | ----------------- | ------ | --------------------------- |
| 1 | Fast searches without per-query full scans — bounded staleness/context reads via the transactional `embedded_documents` shadow reconciled in cleanup/vacuum; staleness stays derived; contexts keep verbatim two-sided normalization | ✓ VERIFIED | `staleness.embedded_document_ids` reads the shadow; `mark_vector_staleness` uses one display-gate probe + indexed PK lookups (`test_marking_is_bounded_by_the_shadow_not_a_vec0_scan` passes); shadow writes ride `VectorSearcher` write/delete transactions (`_SHADOW_INSERT_SQL` joins `documents`); `reconcile_embedded_documents` invoked from cleanup (`cli/main.py:271`) and vacuum; `context_attach` cache invalidated by generation + `PRAGMA data_version` + inode with the constant verbatim scan (`test_two_attaches_issue_exactly_one_contexts_statement` passes) |
| 2 | Safe maintenance — `sif index vacuum` (flock + quiesce + no open txn + checkpoint + 2× disk check, retryable busy errors, target paths restricted) and a verified backup copy (SQLite online backup API + `integrity_check`) | ✓ VERIFIED | `maintenance.vacuum_index` refuses an open transaction, checkpoints TRUNCATE, enforces `required = 2 * before_bytes`, then `VACUUM`; `backup_index` validates the target (symlink/existing/db/sidecar/stale-sidecar), uses `Connection.backup`, and gates on `PRAGMA integrity_check == [('ok',)]`; both commands run under `index_lock` (`cli/commands/index.py:548,598`); unit + integration tests green |
| 3 | Embed large corpora without giant transactions — streaming batches outside transactions, short per-batch commits, resumable, CR-02 failure reporting preserved, batch-boundary sanity | ✓ VERIFIED | `StreamingEmbedWriter.embed_document` embeds before `with self._conn:` and commits one short per-document block; `validate_batch` pins count/dim/finiteness/norm; `embed_cmd` aborts systemic failures after prior commits (`_EmbedAbortError`); resume/certification tests pass (`test_batches_run_outside_the_transaction_and_commit_once`, `test_mid_run_failure_keeps_committed_documents_and_resumes_remainder`) |
| 4 | Protection from silent bad model swaps — persisted `index_meta` identity; 3 dim guards consolidated; legacy warn-once + backfill; mismatch fail-fast/warn+mark | ✓ VERIFIED | `identity.py` persists `embedder.identity`, field-wise `identity_matches`, mode-aware `check_identity(init|embed|search)`; `schema.py:686-693` delegates the `FLOAT[n]` read to `schema_embedding_dim` + init-mode check; `watcher.py:366` and `embed_cmd` share the read; legacy `ensure_legacy_identity` called from `create_all` (`schema.py:93-95`); CLI/MCP/watcher policy tests green |
| 5 | Correct query-vs-document embeddings — role-aware surface with `prompt_name`, prompt in the cache key; Qwen3 default byte-identical | ✓ VERIFIED | `roles.py` class-level dispatch; `embedder.py` concrete `embed_query(ies)`/`embed_documents` with prompt validation; `manager._cache_bucket` appends `|rev@…` then `|q@…`/`|d@…` only when effective; `_role_model_call` falls back to `embed_batch` for protocol doubles; `test_default_qwen3_buckets_are_the_pre_phase_baseline` and `test_default_no_prompt_query_role_reproduces_the_sc1_golden` pass |

### Observable Truths (Plan Must-Haves)

All 58 plan truths from the eight PLAN frontmatter `must_haves` blocks were re-checked against the current code. Grouped evidence follows; every named test exists and passes in the current suite.

#### Plan 21-01 — identity record, prompt scheme, role-aware cache (EMB-01, EMB-02)

| # | Truth | Status | Evidence |
| - | ----- | ------ | -------- |
| 1 | Identity round-trips through real `index_meta`; fingerprint identical across builds and a subprocess | ✓ VERIFIED | `EmbedderIdentity`, `write_identity`/`read_identity`; `test_round_trip_through_real_index_meta`, `test_two_builds_are_byte_identical`, `test_fingerprint_stable_across_subprocess` |
| 2 | Field-wise comparison with unknown-tolerance | ✓ VERIFIED | `identity_matches`; `TestIdentityMatches` comparison matrix |
| 3 | Default Qwen3: bucket byte-identical, no prompt kwarg, no revision suffix | ✓ VERIFIED | `manager._cache_bucket`; `test_default_qwen3_buckets_are_the_pre_phase_baseline` (literal pre-phase bucket) |
| 4 | Prompted query vs unprompted document use distinct buckets; revision appends to role buckets only | ✓ VERIFIED | `_cache_bucket`; `test_prompts_produce_distinct_role_buckets`, `test_revision_suffix_precedes_role_suffix` |
| 5 | Unknown prompt raises `ValueError` listing keys; unsupported backend warns once and records `prompt_supported=false` | ✓ VERIFIED | `_validate_prompt_names`, `resolve_prompt_scheme`; prompt-validation tests |
| 6 | Corrupt identity JSON treated as absent with one warning | ✓ VERIFIED | `_load_payload`/`_payload_error`/`from_json`; malformed/non-object/missing-field tests |
| 7 | Protocol-only doubles route through `embed`/`embed_batch`; no phantom role method | ✓ VERIFIED | `roles._class_defines`, `manager._role_model_call`; `test_concept_embedder_falls_back_to_embed`, `test_magicmock_falls_back_to_embed_without_phantom_role_call` |

#### Plan 21-02 — `embedded_documents` shadow, bounded reads, status (CORR-06)

| # | Truth | Status | Evidence |
| - | ----- | ------ | -------- |
| 8 | ≥1 vector row ⇒ exactly one shadow row in the same transaction; delete removes it atomically | ✓ VERIFIED | `VectorSearcher._add_embedding_vec`/`add_embeddings_batch`/`delete_embeddings_by_document`; `TestShadowWritePath` |
| 9 | Orphan vector row never creates a shadow row | ✓ VERIFIED | `_SHADOW_INSERT_SQL` joins `documents`; `test_orphan_vector_insert_never_creates_a_shadow_row` |
| 10 | Search path: display-gate probe + PK lookups, no full `document_embeddings` scan; markers byte-identical | ✓ VERIFIED | `staleness.py:44-59`; `test_marking_is_bounded_by_the_shadow_not_a_vec0_scan` asserts zero `FROM document_embeddings` statements |
| 11 | Missing shadow/vec0 ⇒ unmarked (`None`); empty shadow suppresses markers | ✓ VERIFIED | `test_missing_shadow_degrades_to_unmarked`, `test_vec0_missing_degrades_to_unmarked`, `test_display_gate_zero_embeddings_marks_nothing` |
| 12 | Legacy DB gets one-time marker-gated backfill with one warning; fresh DB writes marker at zero cost | ✓ VERIFIED | `schema._backfill_embedded_documents`; `TestLegacyBackfill`, `test_create_all_creates_shadow_and_marker_without_warning` |
| 13 | `create_all` total without vec0: no table, no marker, no statement against the absent table | ✓ VERIFIED | `_create_embedded_documents_table`; `test_create_all_is_total_without_vec0`, `test_backfill_issues_no_statement_against_the_absent_table` |
| 14 | Dropped/recreated shadow rebuilt even when marker survives | ✓ VERIFIED | `test_dropped_table_with_surviving_marker_forces_rebuild` |
| 15 | `sif status` vector-lag strings byte-identical while reading via anti-join | ✓ VERIFIED | `cli/main._vector_lag_text`; `TestVectorLagText` (n/a, none, 1, N) |
| 16 | Reconcile deletes stale and inserts missing rows for existing documents only | ✓ VERIFIED | `reconcile_embedded_documents`; `test_reconcile_repairs_divergence`, `test_reconcile_leaves_the_commit_to_the_caller` |

#### Plan 21-03 — normalized context-map cache (CORR-06)

| # | Truth | Status | Evidence |
| - | ----- | ------ | -------- |
| 17 | Two attachments on one file DB issue exactly one contexts `SELECT` | ✓ VERIFIED | `context_attach.get_context_map`; `test_two_attaches_issue_exactly_one_contexts_statement` |
| 18 | Context write invalidates even with unchanged `data_version` | ✓ VERIFIED | `bump_context_write_generation` in every write; generation-invalidation tests |
| 19 | Commit from another connection invalidates via sentinel `PRAGMA data_version` | ✓ VERIFIED | `_ContextCacheEntry` sampling before build; cross-connection tests |
| 20 | `:memory:` bypasses the cache | ✓ VERIFIED | `_resolved_main_path`; `test_memory_database_requeries_on_every_attach` |
| 21 | Sentinel failure falls back to verbatim scan; no search fails because of the cache | ✓ VERIFIED | `_open_sentinel`/`_store_entry`; sentinel-failure tests |
| 22 | Two-sided normalization and newest-`updated_at`-wins unchanged, including `/tmp` vs `/private/tmp` | ✓ VERIFIED | `attach_path_contexts`; alias/duplicate-target fixtures |
| 23 | `enrich_results` accepts optional `vectors_untrusted`; two-argument callers untouched | ✓ VERIFIED | `context_attach.enrich_results`; three signature/ordering tests |

#### Plan 21-04 — vector-space enforcement across search hosts (EMB-01, EMB-02)

| # | Truth | Status | Evidence |
| - | ----- | ------ | -------- |
| 24 | Same-dimension model B on `sif query`: one warning naming both identities + remedy, results returned, every row `vectors_stale=True` | ✓ VERIFIED | `SearchPipeline._identity_state/_mark_untrusted`; `test_query_hybrid_swap_warns_once_marks_every_row_and_repeats_silently` |
| 25 | BM25-only `sif search` neither warns nor marks | ✓ VERIFIED | `test_search_cmd_stays_identity_silent`; `test_bm25_exit_never_evaluates_identity_and_marks_nothing` |
| 26 | `vsearch` width disagreement warns once + raises remedy-bearing `ClickException`; hybrid degrades to marked BM25 | ✓ VERIFIED | `search.py:820-872`; `test_vsearch_dimension_mismatch_refuses_with_the_remedy`, `test_hybrid_dimension_mismatch_degrades_to_marked_bm25` |
| 27 | Every query-side embed routes through the role helper | ✓ VERIFIED | `hybrid.py:135,365,377`, `expansion.py:88,116`, `search.py:843`, `bench.CachedEmbedder`; role-dispatch tests |
| 28 | MCP hybrid warns once and marks metadata stale without breaking BM25 degradation; matching assumed identity stays silent | ✓ VERIFIED | `mcp/backend.py:509-513` builds the closure from `self._identity` (Phase 22 SDK shell preserves it); `TestHybridSearchIdentity` tests pass |

#### Plan 21-05 — streaming embed, sanity, failure taxonomy, certification (SCALE-03, EMB-01, EMB-02)

| # | Truth | Status | Evidence |
| - | ----- | ------ | -------- |
| 29 | No write transaction open while embeddings are computed | ✓ VERIFIED | `embed_document` calls the manager before `with self._conn:`; `test_batches_run_outside_the_transaction_and_commit_once` records `conn.in_transaction is False` at every model call |
| 30 | One document's chunks/vectors/shadow/identity commit atomically | ✓ VERIFIED | Single `with conn:` block; garbage matrix asserts `(0,0,0)` + no identity; `test_identity_claim_stays_pending_when_the_commit_fails` |
| 31 |-run after mid-run failure embeds exactly the remainder | ✓ VERIFIED | `_needs_embedding` exact-set rule; integration resume tests (one manager call on resume) |
| 32 | Count/dim/finiteness/norm validated per batch; violations systemic and named | ✓ VERIFIED | `validate_batch`; `test_garbage_batch_sanity_aborts_and_persists_nothing`, `test_manager_output_error_is_translated_to_systemic` |
| 33 | Document-local failures recorded; systemic failures abort after prior commits with one final non-zero report | ✓ VERIFIED | `embed_cmd` `_EmbedAbortError` vs `failed_documents`; failure-taxonomy tests |
| 34 | `source=verified` only on embeddings-empty first commit or complete unfiltered zero-failure `--force`; otherwise `legacy-assumed` | ✓ VERIFIED | `embed_cmd` certification gate; `TestLegacyUpgradeEndToEnd`, certification tests |
| 35 | Zero stored vectors accepts any embedder; stale row overwritten by first commit; only `FLOAT[n]` disagreement fails | ✓ VERIFIED | `check_identity` early no-vector path + `_claim_identity_in_transaction`; `test_stale_identity_on_empty_index_is_overwritten_by_first_commit` |
| 36 | Watcher's embed leg uses the same writer | ✓ VERIFIED | `_EmbedSession.ensure_ready` constructs `StreamingEmbedWriter` (`watcher.py:288`); systemic-disable tests pass |
| 37 | Empty/whitespace chunks rejected before embedding; chunkless document writes nothing | ✓ VERIFIED | `_chunk_document` filters `content.strip()`; whitespace-only tests (unit + integration) |

Phase 24's breadcrumb overlay (`embed_writer.py` `embed_texts`) is default-off; the default path remains chunk text, and the phase-21 transaction/sanity/shadow invariants are unchanged (all Phase 21 tests and the byte-identical goldens pass).

#### Plan 21-06 — vacuum, backup, cleanup reconcile, docs (SCALE-01, SCALE-02, CORR-06)

| # | Truth | Status | Evidence |
| - | ----- | ------ | -------- |
| 38 | `sif index vacuum`: flock, busy timeout, outside transaction, reconcile, TRUNCATE checkpoint, 2× precheck, `VACUUM`, size report | ✓ VERIFIED | `maintenance.vacuum_index` + `index.vacuum_cmd`; vacuum tests incl. `test_vacuum_runs_with_no_open_transaction_at_execute_time`, CLI print test |
| 39 | Busy/locked surfaces as retryable `ClickException`; no partial success, no traceback | ✓ VERIFIED | `_is_busy_error` → `MaintenanceBusyError` → CLI translation; `test_busy_checkpoint_is_retryable`, no-traceback CLI test |
| 40 | Vacuum beside a concurrent reader succeeds or returns retryable error; integrity passes; lock released | ✓ VERIFIED | `test_reader_transaction_yields_success_or_retryable_error` (integration) |
| 41 | `sif index backup [--output]` uses online backup API; default path; refuses unsafe targets | ✓ VERIFIED | `backup_index`/`_validate_backup_target`/`_create_backup_target`; target-matrix tests, `test_never_uses_a_file_copy_or_vacuum_into` |
| 42 | Integrity gate exactly `[('ok',)]`; failure keeps copy and names it; backup/OS failure removes target | ✓ VERIFIED | `_verify_backup`, `_discard_backup`; integrity/failure tests |
| 43 | Successful backup mode 0600; live-write backup contains committed rows and opens cleanly | ✓ VERIFIED | Exclusive `O_CREAT|O_EXCL|O_NOFOLLOW` target at `0o600`; live-writer integration test |
| 44 | `sif cleanup` reconciles inside its transaction; missing shadow/vec0 is a no-op | ✓ VERIFIED | `cli/main.py:271` `reconcile_embedded_documents(conn)`; cleanup tests |
| 45 | Both commands on the `index` group, CLI-only, generated docs committed | ✓ VERIFIED | `index_group.command("vacuum"/"backup")`; no MCP match for vacuum/backup; `docs/cli-reference.md:410,465`; generators leave no diff |

#### Plan 21-07 — phase gate: byte-identical baseline, lifecycle, failure/concurrency matrix

| # | Truth | Status | Evidence |
| - | ----- | ------ | -------- |
| 46 | Default vectors/goldens/bench/cache keys byte-identical; fresh embed adds only identity + shadow + two markers | ✓ VERIFIED | `test_default_qwen3_buckets_are_the_pre_phase_baseline`, `test_default_no_prompt_query_role_reproduces_the_sc1_golden`, `test_first_embed_writes_only_identity_shadow_and_markers` (index_meta keys exactly 3), bench snapshot tests |
| 47 | Legacy DB upgrades on first open (backfill, one warning, `legacy-assumed`); full unfiltered zero-failure `--force` rewrites `verified`; scoped/failing keeps assumed | ✓ VERIFIED | `TestLegacyUpgradeEndToEnd`, integration `TestLegacyCertification` |
| 48 | Same-dimension swap caught end-to-end through CLI and MCP; BM25-only silent | ✓ VERIFIED | Identity-mismatch CLI tests, `test_query_hybrid_swap_…`, `test_search_cmd_stays_identity_silent`, MCP `TestHybridSearchIdentity` |
| 49 | Mid-run failure durable/resumable; garbage batch persists nothing; vacuum/backup survive concurrency with integrity intact | ✓ VERIFIED | Integration resume/garbage/reader/writer tests |
| 50 | Docs generators clean; ruff, format, ty, full pytest (fail_under=90) green | ✓ VERIFIED | `python scripts/generate_cli_ref.py` + `generate_config_ref.py` exit 0, `git status` clean; `ruff check` pass, `ruff format --check` 236 files formatted, `ty check` pass; full suite 3233 passed, 1 skipped, 95.03% coverage |

#### Plan 21-08 — legacy identity at open, shared dimension guard, watcher/MCP (EMB-01)

| # | Truth | Status | Evidence |
| - | ----- | ------ | -------- |
| 51 | Legacy index (vectors, no identity) writes `legacy-assumed` once, warns once, never blocks search; later swap detected | ✓ VERIFIED | `create_all` + `check_identity(mode="init")`; legacy-open tests, MCP backend assumed-row test |
| 52 | Fresh embeddings-empty index writes no identity row; second open emits no warning | ✓ VERIFIED | `test_init_writes_nothing_without_vectors`, `TestFreshDatabase` |
| 53 | Three dimension guards share one `FLOAT[n]` read; messages unchanged | ✓ VERIFIED | `schema.py:686-693`, `watcher.py:366`, `embed_cmd` all call `schema_embedding_dim`; verbatim message tests |
| 54 | `check_identity(mode="init")` has a production caller; width mismatch raises the pre-change text; injected dimension is width-only | ✓ VERIFIED | `schema.py` init check; `test_dimension_mismatch_raises_the_existing_runtime_error`, injected-dimension test |
| 55 | Every Settings-constructed host applies the resolved prompt scheme, including MCP | ✓ VERIFIED | `EmbeddingManager.from_settings`; `mcp/backend.py:266-272` resolves the scheme for `build_settings_identity` and `create_model`; forwarding tests |
| 56 | OpenAI endpoint check reuses shared wording, preserves its exact message | ✓ VERIFIED | `dimension_mismatch_text`; `TestDimensionMismatchWording` |
| 57 | Watcher first embed on same-dimension mismatch emits one error event and disables embedding for the session | ✓ VERIFIED | `_EmbedSession.ensure_ready`; `test_same_dimension_identity_mismatch_disables_embed_with_one_error` |
| 58 | MCP init passes a settings-only identity; legacy DB first opened by the backend gets the assumed row | ✓ VERIFIED | `mcp/backend.py:272,292`; `test_init_schema_receives_the_settings_only_identity`, `test_legacy_db_first_opened_by_the_backend_gets_the_assumed_row` |

**Score:** 63/63 truths verified (5 roadmap success criteria + 58 plan must-have truths; 0 present-but-behavior-unverified; 0 overrides).
**Behavior-dependent truths:** the transaction-ordering (29, 30, 34, 35), cancellation/cleanup (8, 16), and cache-invalidation (18–20) invariants are each exercised by a passing named behavioral test — none rests on presence alone.

### Deferred Items

The prior report's single deferred item is now closed, not merely scheduled.

| # | Item | Addressed In | Evidence |
| - | ---- | ------------ | -------- |
| 1 | The real Harrier model exposes `web_search_query` and a 1024-dim vector (consumer-side EMB-02 precondition) | Phase 23 — satisfied | `23-VERIFICATION.md` SC1: both arm identities `source: verified` at 1024 dims, Harrier `query_prompt=web_search_query`, `document_prompt=null`; 21-VALIDATION.md row updated to "verified in Phase 23's real two-arm run". The Phase 21 contract itself (known-model table mapping, identity prompt/dimension fields) is present in `prompts.py:28-31` and `identity.py`. |

### Advisory (New Scope, Unevidenced)

None. Re-verification scanned the covered files for new-scope blockers; no debt markers, stubs, or reproducible defects were found on files changed by Phases 22–24.

### Required Artifacts

| Artifact | Expected | Status | Details |
| -------- | -------- | ------ | ------- |
| `src/sif/embedding/identity.py` | identity record, build/read/write, ensure/certify, matches/check, shared `FLOAT[n]` read | ✓ VERIFIED | All symbols present; wired into schema/CLI/watcher/MCP/writer |
| `src/sif/embedding/prompts.py` | `PromptScheme`, resolver, known-model table | ✓ VERIFIED | Qwen3 absent by design; Harrier query prompt present |
| `src/sif/embedding/roles.py` | Type-aware role helpers | ✓ VERIFIED | Class-level dispatch; no phantom role calls |
| `src/sif/config/settings.py`, `src/sif/models/embedding.py` | prompt settings | ✓ VERIFIED | Fields + docs rows present |
| `src/sif/embedding/embedder.py` | Role methods, pooling/revision, prompt validation, shared OpenAI wording | ✓ VERIFIED | ST/ModelScope role methods; GGUF file-hash revision |
| `src/sif/embedding/manager.py` | Identity, role methods, prompt/revision buckets, cache validation | ✓ VERIFIED | `_cache_bucket`/`_role_model_call`/`get_identity` |
| `src/sif/database/schema.py` | Shadow DDL/backfill/marker, init-mode guard | ✓ VERIFIED | Lines 83-95, 358+, 686-693, 719 |
| `src/sif/database/maintenance.py` | Reconcile, vacuum/backup, errors | ✓ VERIFIED | 399 lines; online-API copy, 0600 target, integrity gate, 2× precheck |
| `src/sif/search/vector.py` | Shadow maintenance in every write/delete | ✓ VERIFIED | Same-transaction insert/delete, join-to-documents |
| `src/sif/search/staleness.py` | Shadow-based bounded marking | ✓ VERIFIED | Display gate + PK lookups |
| `src/sif/cli/main.py` | Status anti-join, cleanup reconcile | ✓ VERIFIED | Byte-identical lag strings; reconcile in cleanup txn |
| `src/sif/search/context_attach.py`, `src/sif/database/repositories.py` | Cache/sentinel/enrichment; write generation | ✓ VERIFIED | Resolved-path key, generation + data_version + inode triggers, atexit; bumps in every write |
| `src/sif/search/hybrid.py`, `expansion.py`, `cli/commands/search.py`, `bench.py`, `eval.py`, `mcp/backend.py` | Identity policy + query-role embeds at every host | ✓ VERIFIED | Phase 22's SDK shell keeps the identity closure and prompt scheme in `mcp/backend.py` |
| `src/sif/indexing/embed_writer.py` | `StreamingEmbedWriter`, `validate_batch`, `SystemicEmbedError`, `NORM_TOLERANCE` | ✓ VERIFIED | Embed outside tx; BEGIN IMMEDIATE revalidation; post-commit flag clear |
| `src/sif/indexing/watcher.py` | Writer routing + identity at first embed | ✓ VERIFIED | One error event; pending-retry preserved |
| `src/sif/cli/commands/index.py` | Streaming `embed`, `vacuum`, `backup` | ✓ VERIFIED | Identity under flock; busy/target translation |
| `docs/cli-reference.md`, `docs/configuration.md`, `docs/architecture.md` | Generated/hand docs | ✓ VERIFIED | Generators reproduce no diff; architecture documents identity/shadow/streaming/maintenance |

### Key Link Verification

| From | To | Via | Status | Details |
| ---- | -- | --- | ------ | ------- |
| `embedding/identity.py` | `database/repositories.py` | `IndexMetaRepository.get/set` | ✓ WIRED | Lazy import; caller-owned transaction |
| `embedding/manager.py` | `embedding/identity.py` | `format_cache_model_id`, `build_identity`, `get_identity` | ✓ WIRED | Buckets and identity share one format |
| `embedding/manager.py` | `embedding/embedder.py` | role dispatch vs `embed_batch` | ✓ WIRED | Prompted role calls; no-prompt fallback |
| `embedding/factory.py` | prompt scheme | `query_prompt_name`/`document_prompt_name` kwargs | ✓ WIRED | Factory forwards both names (`factory.py:73-74,112-113`) |
| `search/vector.py` | `index_meta`/`documents` | `INSERT OR IGNORE ... SELECT id FROM documents` | ✓ WIRED | Join prevents orphan shadow rows |
| `search/staleness.py` | `search/vector.py` | shared shadow rows | ✓ WIRED | Writer-maintained, reader-consumed |
| `database/schema.py` | `search/vector.py` | vec0-conditional shadow DDL | ✓ WIRED | `_create_embedded_documents_table` |
| `database/maintenance.py` | `cli/main.py` | `reconcile_embedded_documents` in cleanup txn | ✓ WIRED | `cli/main.py:271` |
| `search/context_attach.py` | `database/repositories.py` | `context_write_generation()` comparison | ✓ WIRED | Every context write bumps |
| `search/context_attach.py` | `PRAGMA database_list`/`data_version` | resolved path + sentinel connection | ✓ WIRED | Sentinel lifecycle + inode check |
| `search/context_attach.py` | `search/staleness.py` | `enrich_results` composition | ✓ WIRED | Attach then optional untrusted pass |
| `search/hybrid.py` | `embedding/identity.py` | injected `identity_check` | ✓ WIRED | Lazy, once per pipeline, vector exits only |
| `search/hybrid.py` | `embedding/roles.py` | `embed_query` on hybrid/`vec:`/HyDE legs | ✓ WIRED | Class-level role detection |
| `cli/commands/search.py` | `search/context_attach.py` | `enrich_results(..., vectors_untrusted=True)` | ✓ WIRED | vsearch/query identity path |
| `mcp/backend.py` | `embedding/identity.py` | search-mode closure over the full loaded identity | ✓ WIRED | `partial(check_identity, current=identity, mode="search")` |
| `cli/commands/index.py` | `indexing/embed_writer.py` | `StreamingEmbedWriter.embed_document` per document | ✓ WIRED | One writer per collection |
| `indexing/embed_writer.py` | `search/vector.py` | `add_embeddings_batch` / `delete_embeddings_by_document` | ✓ WIRED | Shadow maintained with vectors |
| `indexing/embed_writer.py` | `embedding/identity.py` | `write_identity` on first vector write; sanity fields | ✓ WIRED | In-transaction claim; post-commit flag |
| `indexing/watcher.py` | `indexing/embed_writer.py` | same writer built in `ensure_ready` | ✓ WIRED | Shared completeness/sanity/shadow |
| `cli/commands/index.py` | `database/maintenance.py` | `vacuum_index`/`backup_index` inside `index_lock` | ✓ WIRED | Busy/target errors translated |
| `database/maintenance.py` | `database/factory.py` | `create_connection` + `WAL_CHECKPOINT_TRUNCATE` | ✓ WIRED | Own connection, outside `Database.transaction()` |
| `cli/main.py` | `database/maintenance.py` | `reconcile_embedded_documents` in cleanup | ✓ WIRED | Same transaction |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
| -------- | ------------- | ------ | ------------------ | ------ |
| `staleness.py` → CLI JSON / MCP metadata | `vectors_stale` | `embedded_documents` shadow (transactional) | Yes — real rows from vector writes | ✓ FLOWING |
| `cli/main.py` status | vector-lag text | `documents` anti-join `embedded_documents` | Yes — live counts | ✓ FLOWING |
| `maintenance.vacuum_index` | before/after/reclaimed bytes | `stat()` of db + WAL around `VACUUM` | Yes | ✓ FLOWING |
| `maintenance.backup_index` | output/bytes | `Connection.backup` + `integrity_check` + `stat()` | Yes | ✓ FLOWING |
| `embedding/identity.py` | identity JSON | settings + loaded model + prompt scheme → `index_meta` | Yes | ✓ FLOWING |
| `search/context_attach.py` | `context_description` | `contexts` table, cache invalidated by writes/commits/inode | Yes | ✓ FLOWING |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
| -------- | ------- | ------ | ------ |
| Phase 21 targeted battery (17 files: identity, manager, embedder, writer, watcher, schema/shadow, maintenance, staleness, contexts, hybrid, index/search CLI, main, MCP backend, both integrations) | `NO_COLOR=1 pytest -q --no-cov -p no:cacheprovider <17 files>` | 798 passed in 9.14s | ✓ PASS |
| Full quality gate at current code state | `NO_COLOR=1 pytest -q` | 3233 passed, 1 skipped, 27 warnings in 210.39s; total coverage 95.03% (`fail_under=90`) | ✓ PASS |
| Docs generators leave no diff | `python scripts/generate_cli_ref.py; python scripts/generate_config_ref.py` | both exit 0; `git status --porcelain docs/cli-reference.md docs/configuration.md` empty | ✓ PASS |
| Lint/format/type gates | `ruff check src tests`; `ruff format --check src tests`; `ty check src/sif` | All checks passed; 236 files already formatted; All checks passed | ✓ PASS |
| Maintenance commands remain CLI-only | `grep -rniE "vacuum\|backup_index" src/sif/mcp/` | no match | ✓ PASS |
| Generated docs still document the commands | `docs/cli-reference.md` sections | `sif index backup` (line 410), `sif index vacuum` (line 465) | ✓ PASS |

The suite's single skip is outside the Phase 21 requirement-linked files; sqlite-vec is available in this environment, so the conditional `pytest.skip("sqlite-vec not available")` guards in the phase tests did not fire.

### Probe Execution

N/A — no probe scripts are declared in the Phase 21 plans/summaries and no `scripts/*/tests/probe-*.sh` exists.

### Test Quality Audit

| Test File | Linked Req | Active | Skipped | Circular | Assertion Level | Verdict |
| --------- | ---------- | ------ | ------- | -------- | --------------- | ------- |
| `tests/unit/embedding/test_identity.py` | EMB-01, EMB-02 | 40 | 0 | No | Value + behavioral (round-trip, subprocess, comparison matrix) | PASS |
| `tests/unit/embedding/test_manager.py` | EMB-02 | 45 | 0 | No | Value (literal bucket strings, encode kwargs, cache rows) | PASS |
| `tests/unit/indexing/test_embed_writer.py` | SCALE-03, EMB-01 | 12 | 0 | No | Behavioral (transaction flags, garbage matrix, commit-failure, resume) | PASS |
| `tests/unit/database/test_embedded_documents.py` | CORR-06 | 15 | 0 | No | Behavioral (fresh/legacy/orphan/drop-rebuild/only-new-writes) | PASS |
| `tests/unit/database/test_maintenance.py` | SCALE-01, SCALE-02 | 19 | 0 | No | Behavioral (busy/low-disk/mode/TOCTOU/integrity) | PASS |
| `tests/integration/test_embed_idempotency.py` | SCALE-03, EMB-01 | 15 | 0 | No | Behavioral (real CLI + real DB, resume, certification) | PASS |
| `tests/integration/test_maintenance.py` | SCALE-01, SCALE-02 | 2 | 0 | No | Behavioral (live reader/writer) | PASS |
| `tests/unit/search/test_staleness.py` | CORR-06 | 22 | 0 | No | Behavioral (recording connection asserts bounded SQL) | PASS |
| `tests/unit/search/test_context_attach.py` | CORR-06 | 25 | 0 | No | Behavioral (statement counting, cross-connection invalidation) | PASS |
| `tests/unit/cli/test_index.py` | SCALE-01/02/03, EMB-01 | 30+ | 0 | No | Behavioral (real CLI runs, lock ordering, refusal paths) | PASS |
| `tests/unit/cli/test_search.py`, `test_hybrid.py`, `test_bench.py`, `test_eval.py`, `test_mcp/test_backend.py` | EMB-01, EMB-02 | 100+ | 0 | No | Behavioral (warn-once, all-stale, BM25 silence, role dispatch) | PASS |

**Disabled tests on requirements:** 0 → no blocker.
**Circular patterns detected:** 0 → no blocker.
**Insufficient assertions:** 0 → no warning.

### Requirements Coverage

| Requirement | Source Plan(s) | Description | Status | Evidence |
| ----------- | -------------- | ----------- | ------ | -------- |
| SCALE-01 | 21-06, 21-07 | Reclaim space safely via `sif index vacuum` | ✓ SATISFIED | `vacuum_index`, `vacuum_cmd`, guard tests; no target argument; docs committed |
| SCALE-02 | 21-06, 21-07 | Back up the index safely (online backup API + `integrity_check`) | ✓ SATISFIED | `backup_index`, exclusive 0600 target, `[('ok',)]` gate, live-write integration test |
| SCALE-03 | 21-05, 21-07 | Embed large corpora without giant transactions | ✓ SATISFIED | `StreamingEmbedWriter`, `validate_batch`, failure taxonomy, resume/certification, watcher routing |
| CORR-06 | 21-02, 21-03, 21-06, 21-07 | Fast searches without per-query full scans | ✓ SATISFIED | Shadow maintenance/backfill/reconcile, bounded staleness/status reads, context cache with three invalidation triggers |
| EMB-01 | 21-01, 21-04, 21-05, 21-07, 21-08 | Protection from silent model swaps | ✓ SATISFIED | `identity.py`, schema/watcher/MCP/embed/search wiring, legacy lifecycle + same-dim swap tests |
| EMB-02 | 21-01, 21-04, 21-05, 21-07 | Correct query-vs-document embeddings | ✓ SATISFIED | Role helpers + concrete role methods, prompt/revision buckets, default-baseline and SC1 golden tests |

**Coverage:** 6/6 requirements satisfied. PLAN `requirements:` fields collectively cover every REQUIREMENTS.md ID mapped to Phase 21 (21-01 EMB-01/02; 21-02/03 CORR-06; 21-04 EMB-01/02; 21-05 SCALE-03/EMB-01/02; 21-06 SCALE-01/02/CORR-06; 21-07 all six; 21-08 EMB-01). No orphaned Phase 21 requirements; REQUIREMENTS.md records all six as Complete.

### Anti-Patterns Found

No `TBD`/`FIXME`/`XXX` debt markers exist in any Phase 21-changed file (re-scanned this pass). No stub rendering, hardcoded-empty data, or console-log-only implementation was found in the changed source. The prior review ledger's Info items remain non-blocking and unchanged: prompted-bucket edge for protocol-only embedders (`manager.py`), identity schema-version acceptance (`identity.py`), GGUF hash startup cost (`embedder.py`), pre-existing ModelScope disclosure text (`eval.py`), `list_by_collection` peak memory (`index.py`), chunkless purge docstring (`embed_writer.py`), pre-existing dead branch (`expansion.py:64`), pre-existing HuggingFace `NotImplementedError` (`factory.py:98`, unreachable via settings validation).

**Anti-patterns:** 0 blockers, 0 warnings, 8 info (carried forward; none violates a Phase 21 must-have).

### Human Verification Required

None. Every user-visible surface (vacuum/backup sizes, retry errors, identity warnings, stale markers, status lag text) is asserted by automated CLI tests; there is no UI, real-time behavior, or external-service UX left unverified. The Harrier real-model check previously deferred to Phase 23 is now verified there.

### Gaps Summary

**No gaps found.** All 5 roadmap success criteria and all 58 plan must-have truths remain backed by implementation evidence in the current codebase and by passing behavioral tests after Phases 22–24. The targeted Phase 21 battery is 798/798 green against current code, the full suite is 3233 passed / 1 skipped at 95.03% coverage, both generator-owned docs reproduce byte-identically, and the three dimension guards still share one read.

**Residual notes (non-blocking):** (a) CR-02's live two-process interleaving is still not simulated; the invariant rests on SQLite `BEGIN IMMEDIATE` semantics plus the flock, with the stale-claim refusal/adoption transitions tested; (b) the GGUF hash-time measurement on the real 1.19 GB model remains a manual note in 21-VALIDATION.md; (c) the review ledger's open Info items are advisory hardening, not phase must-haves.

---

_Verified: 2026-11-18T07:12:30Z_
_Verifier: Claude (gsd-verifier)_
