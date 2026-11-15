---
phase: 21-scale-maintenance-embedder-identity
verified: 2026-11-15T18:38:39Z
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
covered_digest: "v4:sha256:81f5b76df2e544eacd9b21b0227bb0f401fb92eb3907ba53cb729d13219d5704"
behavior_unverified: 0
overrides_applied: 0
deferred:
  - truth: "The real Harrier model exposes the `web_search_query` prompt key and a 1024-dim vector (the consumer-side EMB-02 precondition)"
    addressed_in: "Phase 23"
    evidence: "Phase 23 success criterion 1: Harrier queries use `prompt_name=\"web_search_query\"`, never `default_prompt_name`; 21-VALIDATION.md marks the model-environment check as performed when Phase 23 loads the real model."
---

# Phase 21: Scale, Maintenance + Embedder Identity Verification Report

**Phase Goal:** Large-corpus maintenance is safe and fast, and the index knows which embedder produced its vectors — the locked precondition for the Harrier evaluation (23) and the stable embed contract the MCP layer (22) consumes.
**Verified:** 2026-11-15T18:38:39Z
**Status:** passed
**Re-verification:** No — initial verification

## Goal Achievement

### Roadmap Success Criteria

| # | Success Criterion | Status | Evidence |
| - | ----------------- | ------ | -------- |
| 1 | Fast searches without per-query full scans — bounded staleness/context reads via the transactional `embedded_documents` shadow reconciled in cleanup/vacuum; staleness stays derived; contexts keep verbatim two-sided normalization | ✓ VERIFIED | `staleness.mark_vector_staleness` issues one display-gate probe + indexed PK lookups (`test_marking_is_bounded_by_the_shadow_not_a_vec0_scan` asserts no `FROM document_embeddings`); shadow writes live in `VectorSearcher` write/delete transactions; `reconcile_embedded_documents` is called from cleanup and vacuum; `context_attach` keeps the constant verbatim scan and two-sided `normalize_path` |
| 2 | Safe maintenance — `sif index vacuum` (flock + quiesce + no open txn + checkpoint + 2× disk check, retryable busy errors, target paths restricted) and a verified backup copy (SQLite online backup API + `integrity_check`) | ✓ VERIFIED | `maintenance.vacuum_index` / `backup_index` + CLI commands under `index_lock`; `tests/unit/database/test_maintenance.py` and `tests/integration/test_maintenance.py` cover busy retry, low disk, no-txn, TRUNCATE checkpoint, 2× precheck, target refusals, online-API copy, integrity gate, 0600, and live-write snapshots |
| 3 | Large-corpus embed without giant transactions — batches outside transactions, short per-batch commits, resumable, CR-02 failure reporting preserved, batch-boundary sanity | ✓ VERIFIED | `StreamingEmbedWriter.embed_document` embeds before `with conn:`; `validate_batch` pins count/dim/finiteness/norm; `embed_cmd` aborts systemic failures after prior commits with one final non-zero report; integration resume/garbage/durability tests pass |
| 4 | Protection from silent bad model swaps — persisted `index_meta` identity (model id + revision/hash + pooling + prompt scheme, reusing `_cache_model_id`), 3 dim guards consolidated, legacy warn-once + backfill, mismatch fail-fast/warn+mark | ✓ VERIFIED | `identity.py` persists `embedder.identity`; `identity_matches` is field-wise with unknown-tolerance; `schema.py`, `watcher.py`, and `embed_cmd` all read width through `schema_embedding_dim`; CLI/MCP/watcher policies covered by identity-mismatch tests |
| 5 | Correct query-vs-document embeddings — role-aware surface with `prompt_name`, prompt in the cache key; Qwen3 default byte-identical | ✓ VERIFIED | `roles.py` + concrete `embed_query(ies)`/`embed_documents`; `manager._cache_bucket` appends `|q@…`/`|d@…` only when a prompt is effective; `test_default_qwen3_buckets_are_the_pre_phase_baseline` pins the literal pre-phase bucket and proves no prompt kwarg/role call; SC1 golden reproduces through the no-prompt role path |

### Observable Truths (Plan Must-Haves)

#### Plan 21-01 — identity record, prompt scheme, role-aware cache (EMB-01, EMB-02)

| # | Truth | Status | Evidence |
| - | ----- | ------ | -------- |
| 1 | Identity round-trips through the real `index_meta` table; fingerprint identical across independent builds and a subprocess | ✓ VERIFIED | `EmbedderIdentity.to_json/from_json` + `write_identity/read_identity` over `IndexMetaRepository`; `TestIdentityPersistence.test_round_trip_through_real_index_meta`, `test_two_builds_are_byte_identical`, `test_fingerprint_stable_across_subprocess` (real subprocess) |
| 2 | Field-wise comparison with unknown-tolerance; known-vs-known differences always mismatch | ✓ VERIFIED | `identity_matches`; `TestIdentityMatches.test_comparison_matrix` and `test_unknown_on_either_side_tolerates_pooling` |
| 3 | Default Qwen3, prompts unset: bucket byte-identical to pre-phase `_cache_model_id()`, no prompt kwarg, no revision suffix | ✓ VERIFIED | `prompts._KNOWN_PROMPT_SCHEMES` omits Qwen3; `manager._cache_bucket`; `test_default_qwen3_buckets_are_the_pre_phase_baseline` (literal `modelscope:Qwen/Qwen3-Embedding-0.6B`, `batch_calls`, empty role calls) |
| 4 | Prompted query vs unprompted document use different buckets; revision appends to role buckets only | ✓ VERIFIED | `manager._cache_bucket`; `test_prompts_produce_distinct_role_buckets`, `test_revision_suffix_precedes_role_suffix`, `test_unknown_role_raises` |
| 5 | Unknown prompt name raises `ValueError` listing available keys; unsupported backend warns once and records `prompt_supported=false` | ✓ VERIFIED | `embedder._validate_prompt_names`; `prompts.resolve_prompt_scheme`; `test_unknown_prompt_raises_with_available_keys`, `test_unsupported_backend_warns_and_reports_unsupported` |
| 6 | Corrupt/unreadable identity JSON is absent with one warning; never crashes or blocks an embed | ✓ VERIFIED | `identity._load_payload/_payload_error/from_json` warn-and-return-None; `TestFromJson` malformed/non-object/missing-field/non-string tests |
| 7 | Protocol-only doubles route through `embed`/`embed_batch`; no phantom role method | ✓ VERIFIED | `roles._class_defines` class-level dispatch; `manager._role_model_call`; `test_concept_embedder_falls_back_to_embed`, `test_magicmock_falls_back_to_embed_without_phantom_role_call` |

#### Plan 21-02 — `embedded_documents` shadow, bounded reads, status (CORR-06)

| # | Truth | Status | Evidence |
| - | ----- | ------ | -------- |
| 8 | A document with ≥1 vector row has exactly one shadow row, maintained in the same transaction; deleting its embeddings removes the row in that transaction | ✓ VERIFIED | `VectorSearcher._add_embedding_vec/add_embeddings_batch/delete_embeddings_by_document`; `TestShadowWritePath.test_batch_write_creates_one_shadow_row_per_document`, `test_delete_removes_only_that_documents_shadow_row` |
| 9 | An orphan vector row whose document no longer exists never creates a shadow row | ✓ VERIFIED | `_SHADOW_INSERT_SQL` joins `documents`; `test_orphan_vector_insert_never_creates_a_shadow_row`, `TestLegacyBackfill.test_persisted_orphan_vector_row_is_excluded` |
| 10 | Search path uses one display-gate probe + indexed PK lookups, no full `document_embeddings` scan; markers byte-identical | ✓ VERIFIED | `staleness.mark_vector_staleness`; `test_marking_is_bounded_by_the_shadow_not_a_vec0_scan` (recording connection asserts zero `FROM document_embeddings` statements); `TestLagStateEndToEnd` and the unchanged SC1 golden |
| 11 | Missing shadow/vec0 degrades to unmarked (`None`); empty shadow suppresses all markers | ✓ VERIFIED | `test_missing_shadow_degrades_to_unmarked`, `test_vec0_missing_degrades_to_unmarked`, `test_display_gate_zero_embeddings_marks_nothing` |
| 12 | Legacy DB with vectors/no shadow gets a one-time marker-gated backfill (existing documents only) with one warning; fresh DB writes the marker at zero cost | ✓ VERIFIED | `schema._backfill_embedded_documents`; `TestLegacyBackfill` tests, `test_create_all_creates_shadow_and_marker_without_warning` |
| 13 | `create_all` is total without vec0: no shadow table, no marker, no statement against the absent table | ✓ VERIFIED | `_create_embedded_documents_table` returns `None`; `test_create_all_is_total_without_vec0`, `test_backfill_issues_no_statement_against_the_absent_table` |
| 14 | A dropped/recreated shadow is rebuilt even when the marker survives | ✓ VERIFIED | `test_dropped_table_with_surviving_marker_forces_rebuild` |
| 15 | `sif status` vector-lag strings are byte-identical across n/a, no-vectors, 1, N states while reading the shadow via anti-join | ✓ VERIFIED | `cli/main._vector_lag_text`; `TestVectorLagText` (`n/a`, `none (no vectors indexed)`, `1 document`, `2 documents`, zero after orphan shadow rows) |
| 16 | Reconciliation deletes stale rows and inserts missing rows only for existing documents; may scan (maintenance only) | ✓ VERIFIED | `reconcile_embedded_documents`; `test_reconcile_repairs_divergence`, `test_reconcile_leaves_the_commit_to_the_caller`, cleanup tests in `test_main.py` |

#### Plan 21-03 — normalized context-map cache (CORR-06)

| # | Truth | Status | Evidence |
| - | ----- | ------ | -------- |
| 17 | Two attachments on one file DB issue exactly one contexts `SELECT` and return the same map | ✓ VERIFIED | `context_attach.get_context_map`; `test_two_attaches_issue_exactly_one_contexts_statement` |
| 18 | A `ContextRepository` write invalidates even when `PRAGMA data_version` is unchanged | ✓ VERIFIED | `repositories.bump_context_write_generation` on every write; `test_repository_create_invalidates_and_rebuilds_once`, `test_repository_generation_alone_invalidates` |
| 19 | A commit from another connection invalidates via the sentinel's `PRAGMA data_version` | ✓ VERIFIED | `_ContextCacheEntry` + sentinel sampling; `test_separate_connection_commit_invalidates`, `test_same_connection_unrelated_commit_invalidates` |
| 20 | `:memory:` bypasses the cache and re-queries every attachment | ✓ VERIFIED | `_resolved_main_path` returns `None`; `test_memory_database_requeries_on_every_attach` |
| 21 | Sentinel open failure falls back to the verbatim scan with a debug log; no search fails because of the cache | ✓ VERIFIED | `_open_sentinel`/`_store_entry`; `test_sentinel_open_failure_bypasses_with_fresh_scan`, `test_open_sentinel_returns_none_for_missing_directory`, `test_sentinel_error_during_sampling_bypasses_and_caches_nothing` |
| 22 | Two-sided normalization and newest-`updated_at`-wins are unchanged, including the verbatim `/tmp` vs `/private/tmp` fixture | ✓ VERIFIED | `attach_path_contexts`; `test_attach_matches_symlink_alias_target`, `test_newest_updated_at_wins_on_duplicate_targets`, `test_file_db_cached_map_preserves_verbatim_alias_match` |
| 23 | `enrich_results` accepts optional `vectors_untrusted`, marking every result after the normal pass; two-argument callers untouched | ✓ VERIFIED | `context_attach.enrich_results`; `test_vectors_untrusted_marks_every_result_stale`, `test_vectors_untrusted_applies_after_the_normal_pass`, `test_two_argument_signature_stays_compatible` |

#### Plan 21-04 — vector-space enforcement across search hosts (EMB-01, EMB-02)

| # | Truth | Status | Evidence |
| - | ----- | ------ | -------- |
| 24 | `sif query` with a same-dimension model B emits exactly one warning naming both identities and the remedy, returns results, and marks every row `vectors_stale=True` | ✓ VERIFIED | `SearchPipeline._identity_state/_mark_untrusted`; `test_query_hybrid_swap_warns_once_marks_every_row_and_repeats_silently`; `test_same_dimension_mismatch_warns_once_and_marks_every_row` |
| 25 | BM25-only `sif search` neither warns nor marks — it never evaluates the check | ✓ VERIFIED | `test_search_cmd_stays_identity_silent`; `test_bm25_exit_never_evaluates_identity_and_marks_nothing` |
| 26 | `vsearch` width disagreement warns once and raises a remedy-bearing `ClickException`; hybrid degrades to marked BM25 | ✓ VERIFIED | `search.vsearch_cmd` pre-embed check; `test_vsearch_dimension_mismatch_refuses_with_the_remedy` (also asserts `embed_query` never called), `test_hybrid_dimension_mismatch_degrades_to_marked_bm25` |
| 27 | Every query-side embed site routes through the role helper; role-capable backends record `embed_query`/`embed_queries`, protocol doubles record plain `embed` | ✓ VERIFIED | `roles.py` used by `hybrid.py`, `expansion.py`, `search.py`, `bench.CachedEmbedder`, eval via the pipeline; `test_hybrid_query_uses_the_query_role_for_every_variant`, `test_vec_prefix_uses_the_query_role`, `test_hyde_prefix_uses_the_query_role_on_the_generated_document`, `test_vsearch_embeds_the_query_through_the_query_role`, `test_role_methods_fall_back_to_plain_embed_for_a_protocol_double` |
| 28 | MCP hybrid search warns once and marks metadata stale on a same-dimension mismatch without breaking BM25 degradation; a matching assumed identity stays silent | ✓ VERIFIED | `mcp/backend.py` builds the closure from `self._identity`; `TestHybridSearchIdentity.test_same_dimension_mismatch_marks_results_and_warns_once`, `test_dimension_mismatch_returns_marked_bm25_without_a_protocol_error`, `test_no_identity_passes_no_closure` |

#### Plan 21-05 — streaming embed, sanity, failure taxonomy, certification (SCALE-03, EMB-01, EMB-02)

| # | Truth | Status | Evidence |
| - | ----- | ------ | -------- |
| 29 | No write transaction is open while embeddings are computed; the write lock is held only for the short per-document inserts | ✓ VERIFIED | `StreamingEmbedWriter.embed_document` calls the manager before `with self._conn:`; `test_batches_run_outside_the_transaction_and_commit_once` records `conn.in_transaction is False` at every model call |
| 30 | One document's chunks, vectors, shadow row, and first-write identity commit atomically; a failure leaves no partial rows | ✓ VERIFIED | Single `with conn:` block; garbage matrix asserts `(0,0,0)` + no identity; `test_identity_claim_stays_pending_when_the_commit_fails` proves rollback leaves nothing visible |
| 31 | A re-run after mid-run failure embeds exactly the remainder and reports already-embedded documents as skipped | ✓ VERIFIED | `_needs_embedding` exact-set rule; `tests/integration/test_embed_idempotency.py::test_mid_run_failure_keeps_committed_documents_and_resumes_remainder` (one manager call on resume), `test_default_run_skips_complete_then_force_reembeds_all` |
| 32 | Count, dimension, finiteness, and identity-declared norm are validated per batch; violations are systemic, persist nothing, and name identity/document/batch/position/chunk | ✓ VERIFIED | `validate_batch`; `test_garbage_batch_sanity_aborts_and_persists_nothing` (NaN/Inf/wrong dim/wrong count/zero-norm matrix), `test_manager_output_error_is_translated_to_systemic` |
| 33 | Document-local failures are recorded and the run continues; systemic failures abort after prior commits and raise one final non-zero report outside any transaction | ✓ VERIFIED | `embed_cmd` `_EmbedAbortError` vs `failed_documents`; `test_failed_collection_keeps_successful_collections_work`, `test_mid_run_failure_keeps_committed_documents_and_resumes_remainder`, `test_garbage_batch_aborts_persists_nothing_and_a_rerun_succeeds` |
| 34 | Identity is written `source=verified` only on an embeddings-empty first document commit or a complete, unfiltered, zero-failure `--force`; otherwise `legacy-assumed` | ✓ VERIFIED | `embed_cmd` certification gate; `TestLegacyUpgradeEndToEnd`, `test_legacy_scoped_force_does_not_certify`, `test_legacy_full_force_with_a_failure_does_not_certify`, `test_full_force_zero_failures_certifies_verified` |
| 35 | With zero stored vectors any embedder is accepted (D-02); a stale identity row is overwritten by the first commit; only a `FLOAT[n]` width disagreement fails | ✓ VERIFIED | `check_identity` early no-vector path + `_claim_identity_in_transaction`; `test_stale_identity_on_empty_index_is_overwritten_by_first_commit`, `test_vacuous_full_force_certification_is_replaced_by_the_first_write`, `test_no_stored_vectors_accepts_any_same_dimension_model` |
| 36 | The watcher's per-path embed leg uses the same streaming writer, so completeness/sanity/shadow cannot diverge | ✓ VERIFIED | `_EmbedSession.ensure_ready` constructs `StreamingEmbedWriter`; `test_systemic_model_output_disables_the_session_without_retry`, `test_systemic_sanity_failure_disables_embed_for_the_session` |
| 37 | Empty/whitespace chunks are rejected before embedding; a chunkless document writes nothing and creates no shadow row | ✓ VERIFIED | `_chunk_document` filters `content.strip()`; `test_whitespace_only_document_writes_nothing`, integration `test_whitespace_only_document_is_skipped_without_a_shadow_row` |

#### Plan 21-06 — vacuum, backup, cleanup reconcile, docs (SCALE-01, SCALE-02, CORR-06)

| # | Truth | Status | Evidence |
| - | ----- | ------ | -------- |
| 38 | `sif index vacuum` takes the flock, arms a busy timeout, runs outside a transaction, reconciles the shadow in a short transaction, checkpoints TRUNCATE, enforces the 2× (db+WAL) precheck, runs `VACUUM`, and prints before/after/reclaimed | ✓ VERIFIED | `maintenance.vacuum_index` + `index.vacuum_cmd`; `test_vacuum_reclaims_space_and_preserves_rows`, `test_low_disk_raises_with_required_and_available_before_vacuum`, `test_open_transaction_is_refused`, `test_vacuum_runs_with_no_open_transaction_at_execute_time`, CLI print test `test_vacuum_prints_before_after_and_reclaimed_and_exits_zero` |
| 39 | Busy/locked checkpoint/database surfaces as a retryable `ClickException`; no partial success, no traceback | ✓ VERIFIED | `_is_busy_error` → `MaintenanceBusyError` → CLI translation; `test_busy_checkpoint_is_retryable`, `test_busy_vacuum_exits_non_zero_with_retry_text_and_no_traceback` |
| 40 | Vacuum beside a concurrent reader succeeds or returns the documented retryable error; integrity passes and the lock is released | ✓ VERIFIED | `tests/integration/test_maintenance.py::test_reader_transaction_yields_success_or_retryable_error` (integrity `ok` + re-acquirable lock) |
| 41 | `sif index backup [--output]` uses the SQLite online backup API; default `<db_dir>/backups/<stem>-<UTC>.db`; refuses existing/symlink/db/sidecar/stale-sidecar targets | ✓ VERIFIED | `backup_index/_validate_backup_target/_create_backup_target`; `test_default_path_uses_stem_timestamp_and_backups_directory`, `test_unsafe_targets_raise_target_error`, `test_never_uses_a_file_copy_or_vacuum_into` |
| 42 | A backup passes `PRAGMA integrity_check` exactly `[('ok',)]` before success; an integrity failure keeps the copy, names it, exits non-zero; a backup/OS failure removes the just-created target | ✓ VERIFIED | `_verify_backup` + `_discard_backup`; `test_integrity_failure_keeps_the_copy_and_names_it`, `test_backup_failure_removes_the_just_created_target` |
| 43 | A successful backup is mode 0600; a backup under live writes contains committed rows and opens cleanly | ✓ VERIFIED | `_create_backup_target` (`O_CREAT|O_EXCL|O_NOFOLLOW`, `0o600`); `test_copy_is_owner_only_before_the_backup_api_writes`, `test_target_is_created_exclusively_without_following_symlinks`; integration `test_copy_passes_integrity_and_contains_pre_snapshot_rows` (live writer thread) |
| 44 | `sif cleanup` reconciles the shadow in its existing transaction; missing shadow/vec0 is a no-op | ✓ VERIFIED | `cli/main.py` cleanup calls `reconcile_embedded_documents(conn)` inside `db.transaction()`; `test_cleanup_removes_orphan_vectors_and_never_resurrects_a_shadow_row`, `test_cleanup_inserts_missing_shadow_rows_for_existing_documents`, `test_vec0_free_database_runs_cleanup_without_error` |
| 45 | Both commands are registered on the `index` group, CLI-only in this phase, with committed generated docs | ✓ VERIFIED | `index_group.command("vacuum"/"backup")`; `grep -rn "vacuum\|backup" src/sif/mcp/` has no match; `docs/cli-reference.md` has both sections; both generator scripts produce no diff |

#### Plan 21-07 — phase gate: byte-identical baseline, lifecycle, failure/concurrency matrix

| # | Truth | Status | Evidence |
| - | ----- | ------ | -------- |
| 46 | With defaults, query/document vectors, SC1 hybrid golden, bench snapshot, and cache keys are byte-identical to pre-Phase-21; a fresh embed adds only the identity row, shadow rows, and the two version markers | ✓ VERIFIED | `test_default_qwen3_buckets_are_the_pre_phase_baseline`, `test_default_no_prompt_query_role_reproduces_the_sc1_golden`, `test_first_embed_writes_only_identity_shadow_and_markers` (`index_meta` keys exactly `embedded_documents_version`, `metadata_values_version`, `embedder.identity`), bench snapshot tests |
| 47 | A simulated pre-Phase-21 DB upgrades on first open (backfill, one warning, `legacy-assumed`); a complete unfiltered zero-failure `--force` rewrites `verified`; scoped/failing runs keep assumed | ✓ VERIFIED | `TestLegacyUpgradeEndToEnd.test_legacy_upgrade_backfills_shadow_assumes_identity_and_certifies`, `test_legacy_scoped_force_does_not_certify`, `test_legacy_full_force_with_a_failure_does_not_certify`, integration `TestLegacyCertification` tests |
| 48 | A same-dimension swap is caught end-to-end through CLI and MCP: embed fails fast naming both identities, search warns once and marks stale, BM25-only commands stay silent | ✓ VERIFIED | `test_identity_mismatch_writes_no_vectors_and_names_both_identities`, `test_query_hybrid_swap_warns_once_marks_every_row_and_repeats_silently`, `test_search_cmd_stays_identity_silent`, `TestHybridSearchIdentity` MCP tests |
| 49 | A mid-run embed failure leaves prior documents durable, a re-run embeds exactly the remainder, a garbage batch persists nothing; vacuum/backup survive concurrency with integrity intact | ✓ VERIFIED | Integration `test_mid_run_failure_keeps_committed_documents_and_resumes_remainder`, `test_garbage_batch_aborts_persists_nothing_and_a_rerun_succeeds`, `test_reader_transaction_yields_success_or_retryable_error`, `test_copy_passes_integrity_and_contains_pre_snapshot_rows` |
| 50 | `make docs-generate` leaves a clean diff on both generator-owned files; ruff, format, ty, and the full pytest suite (fail_under=90) are green | ✓ VERIFIED | `python scripts/generate_cli_ref.py` and `generate_config_ref.py` exit 0 with no diff; `ruff check`/`ruff format --check`/`ty check` clean; full suite 2750 passed, 1 skipped, 95.18% coverage |

#### Plan 21-08 — legacy identity at open, shared dimension guard, watcher/MCP (EMB-01)

| # | Truth | Status | Evidence |
| - | ----- | ------ | -------- |
| 51 | Opening a legacy index (vectors, no identity) writes `legacy-assumed` once, warns once, never blocks search; a later swap is detected against it | ✓ VERIFIED | `SchemaManager.create_all` + `check_identity(mode="init")`; `test_legacy_populated_index_is_assumed_once_and_warns_once`, `TestLegacyUpgradeEndToEnd`, MCP `test_legacy_db_first_opened_by_the_backend_gets_the_assumed_row` |
| 52 | A fresh embeddings-empty index writes no identity row; a second open emits no warning | ✓ VERIFIED | `test_init_writes_nothing_without_vectors`, `test_fresh_index_writes_no_identity`, `TestFreshDatabase.test_create_all_creates_shadow_and_marker_without_warning` |
| 53 | The three index-vs-model dimension guards share one `FLOAT[n]` read from the identity module; existing message texts survive unchanged | ✓ VERIFIED | `schema._create_vector_tables`, `watcher._schema_embedding_dim`, and `embed_cmd` all call `schema_embedding_dim`; schema message pinned verbatim in `test_mismatch_detection_fails_fast` and `test_initial_identity_width_mismatch_raises_the_pre_change_text` |
| 54 | `check_identity(mode="init")` has a production caller at schema open; a width disagreement raises the pre-change `RuntimeError` text exactly; an injected dimension without identity is width-only with no settings read | ✓ VERIFIED | `schema.py` init check; `test_dimension_mismatch_raises_the_existing_runtime_error`, `Database.init_schema` + `test_injected_dimension_without_identity_never_reads_settings_or_writes` |
| 55 | Every host that constructs an embedder from Settings applies the resolved prompt scheme, including MCP, so identity prompt fields describe the produced vectors | ✓ VERIFIED | `EmbeddingManager.from_settings` → `_prompt_scheme` → factory kwargs; `mcp/backend.py` passes the same scheme to `build_settings_identity` and `create_model`; `test_from_settings_forwards_prompt_names`, `test_init_schema_receives_the_settings_only_identity`, `test_factory_receives_the_resolved_prompt_scheme_and_identity_is_stored` |
| 56 | The OpenAI endpoint-vs-`SIF_EMBEDDING_DIM` check reuses the shared wording while preserving its exact message | ✓ VERIFIED | `OpenAIEmbedder.__init__` calls `dimension_mismatch_text`; `TestDimensionMismatchWording.test_shared_wording_matches_the_pre_change_openai_sentence` pins the pre-change sentence |
| 57 | The watcher's first embed use on a same-dimension mismatch emits one error event and disables embedding for the session; BM25 freshness continues | ✓ VERIFIED | `_EmbedSession.ensure_ready` one-transaction assume+check; `test_same_dimension_identity_mismatch_disables_embed_with_one_error` |
| 58 | MCP init passes a settings-only identity; a legacy DB first opened by the backend gets the assumed row | ✓ VERIFIED | `mcp/backend.py` `settings_identity` → `db.init_schema(identity=...)`; `test_init_schema_receives_the_settings_only_identity`, `test_legacy_db_first_opened_by_the_backend_gets_the_assumed_row` |

**Score:** 63/63 truths verified (5 roadmap success criteria + 58 plan must-have truths; 0 present-but-behavior-unverified; 0 overrides).

### Adjudication of "fixed: requires human verification" review findings

The fix report marked CR-02 (concurrency revalidation) and WR-06 (identity-write flag ordering) as requiring human verification. Both properties were inspected in the code and exercised by deterministic regression tests:

| Finding | Verdict | Evidence |
| ------- | ------- | -------- |
| CR-02 — identity decision taken outside the index flock | ✓ VERIFIED, no human test needed | `embed_cmd` now resolves `_resolve_identity`, `check_identity(mode="embed")`, and `--force` certification inside `index_lock` (`test_identity_resolution_runs_inside_the_index_lock` asserts `lock-enter → identity → lock-exit`). `StreamingEmbedWriter.embed_document` executes `BEGIN IMMEDIATE`, then `_claim_identity_in_transaction` re-reads `has_stored_vectors`/`read_identity` and refuses a mismatched stale claim (`test_stale_first_write_claim_is_revalidated_inside_the_transaction`) or adopts a matching one (`test_stale_claim_adopts_a_matching_concurrent_identity`). A live multi-process interleaving is not simulated; the invariant rests on SQLite's documented `BEGIN IMMEDIATE` write-lock semantics plus the flock, both exercised at the state-transition level. |
| WR-06 — writer clears the identity-write flag before commit | ✓ VERIFIED, no human test needed | `embed_document` clears `self._write_identity` only after the `with conn:` block exits successfully. `test_identity_claim_stays_pending_when_the_commit_fails` injects a commit failure, asserts `identity_pending is True`, no identity/rows are visible, and the retry commits the identity together with the vectors. This is the ordering invariant the finding names, tested deterministically. |

### Deferred Items

| # | Item | Addressed In | Evidence |
| - | ---- | ------------ | -------- |
| 1 | The real Harrier model exposes `web_search_query` and 1024 dimensions (consumer-side EMB-02 check) | Phase 23 | Phase 23 SC1: "Harrier queries use `prompt_name=\"web_search_query\"`, never `default_prompt_name`"; 21-VALIDATION.md manual-only row is validated when Phase 23 loads the real model. The Phase 21 contract (known-model table maps Harrier's query prompt; identity carries dimension/prompt fields) is present. |

### Required Artifacts

| Artifact | Expected | Status | Details |
| -------- | -------- | ------ | ------- |
| `src/sif/embedding/identity.py` | `EmbedderIdentity`, `IDENTITY_KEY`/`IDENTITY_SCHEMA_VERSION`, cache-id format, build/read/write, ensure/certify, matches/check, warn/reset, shared `FLOAT[n]` read | ✓ VERIFIED | 521 lines; every symbol present; wired into schema/CLI/watcher/MCP/embed writer; tests exercise round-trip, modes, legacy, warnings |
| `src/sif/embedding/prompts.py` | `PromptScheme`, resolver, known-model table | ✓ VERIFIED | Qwen3 absent by design; Harrier query prompt present; unsupported-backend warning |
| `src/sif/embedding/roles.py` | Type-aware role helpers | ✓ VERIFIED | Class-level dispatch prevents phantom `MagicMock` role calls; used by hybrid/expansion/bench |
| `src/sif/config/settings.py`, `src/sif/models/embedding.py` | `query_prompt_name` / `document_prompt_name` | ✓ VERIFIED | Settings fields + `EmbeddingConfig` mirrors; docs generator rows exist |
| `src/sif/embedding/embedder.py` | Role methods, `pooling_mode`/`revision`, prompt validation, shared OpenAI wording | ✓ VERIFIED | Both ST and ModelScope role methods; GGUF file-hash revision; OpenAI normalized batches |
| `src/sif/embedding/manager.py` | `get_identity`, role methods, prompt/revision buckets, cache validation | ✓ VERIFIED | `EmbeddingOutputError` on count/width/non-finite; cache read validation |
| `src/sif/database/schema.py` | Shadow DDL/backfill/marker, `drop_all`, init-mode width guard | ✓ VERIFIED | vec0-conditional DDL; table-absent force rule; legacy ensure at `create_all` |
| `src/sif/database/maintenance.py` | Reconcile, `VacuumResult`/`BackupResult`, busy/target errors, vacuum/backup | ✓ VERIFIED | 399 lines; online-API copy, exclusive 0600 target, integrity gate, 2× precheck |
| `src/sif/search/vector.py` | Shadow maintenance in every write/delete | ✓ VERIFIED | Same-transaction insert/delete, join-to-documents |
| `src/sif/search/staleness.py` | Shadow-based bounded marking | ✓ VERIFIED | Display gate + PK lookups; no vec0 scan |
| `src/sif/cli/main.py` | Status anti-join, cleanup reconcile | ✓ VERIFIED | Byte-identical lag strings; reconcile inside cleanup transaction |
| `src/sif/search/context_attach.py` | Cache/sentinel/enrichment | ✓ VERIFIED | Resolved-path key, generation + data_version + inode triggers, atexit |
| `src/sif/database/repositories.py` | Context write generation | ✓ VERIFIED | Bumped in create/update/update_target/delete |
| `src/sif/search/hybrid.py`, `expansion.py`, `cli/commands/search.py`, `bench.py`, `eval.py`, `mcp/backend.py` | Identity policy + query-role embed at every host | ✓ VERIFIED | Lazy single check; warn-once + `vectors_untrusted`; vsearch pre-embed refusal; MCP closure |
| `src/sif/indexing/embed_writer.py` | `StreamingEmbedWriter`, `validate_batch`, `SystemicEmbedError`, `NORM_TOLERANCE` | ✓ VERIFIED | 276 lines; embed outside tx; BEGIN IMMEDIATE revalidation; post-commit flag clear |
| `src/sif/indexing/watcher.py` | Writer routing + identity at first embed | ✓ VERIFIED | One error event on systemic/identity failure; pending-retry preserved |
| `src/sif/cli/commands/index.py` | Streaming `embed`, `vacuum`, `backup` | ✓ VERIFIED | Identity under flock; missing-index refusal; busy/target translation; docs |
| `docs/cli-reference.md`, `docs/configuration.md`, `docs/architecture.md` | Generated/hand docs | ✓ VERIFIED | Both generator scripts produce no diff; architecture documents identity/shadow/streaming/maintenance; MCP surface unchanged |

### Key Link Verification

| From | To | Via | Status | Details |
| ---- | -- | --- | ------ | ------- |
| `embedding/identity.py` | `database/repositories.py` | `IndexMetaRepository.get/set` (lazy import, caller-owned txn) | ✓ WIRED | `read_identity`/`write_identity` |
| `embedding/manager.py` | `embedding/identity.py` | `format_cache_model_id`, `build_identity`, `get_identity` | ✓ WIRED | Buckets and identity share one format |
| `embedding/manager.py` | `embedding/embedder.py` | `embed_queries`/`embed_documents` vs `embed_batch` dispatch | ✓ WIRED | Prompted role calls; no-prompt fallback |
| `embedding/factory.py` | prompt scheme / concrete embedder | `query_prompt_name`/`document_prompt_name` kwargs | ✓ WIRED | Factory forwards both names |
| `search/vector.py` | `index_meta`/`documents` | `INSERT OR IGNORE ... SELECT id FROM documents WHERE id = ?` | ✓ WIRED | Join prevents orphan shadow rows |
| `search/staleness.py` | `search/vector.py` | Same shadow rows | ✓ WIRED | Writer-maintained, reader-consumed |
| `database/schema.py` | `search/vector.py` | `embedded_documents` DDL only when vec0 exists | ✓ WIRED | `_create_embedded_documents_table` vec0 probe |
| `database/maintenance.py` | `cli/main.py` | `reconcile_embedded_documents` inside cleanup transaction | ✓ WIRED | Line 266 of `cli/main.py` |
| `search/context_attach.py` | `database/repositories.py` | `context_write_generation()` comparison | ✓ WIRED | Every context write bumps |
| `search/context_attach.py` | `PRAGMA database_list`/`data_version` | Resolved path key + sentinel connection | ✓ WIRED | Sentinel lifecycle + inode check |
| `search/context_attach.py` | `search/staleness.py` | `enrich_results` composition | ✓ WIRED | Attach then mark; optional untrusted override |
| `search/hybrid.py` | `embedding/identity.py` | Injected `identity_check` → `check_identity(mode="search")` | ✓ WIRED | Lazy, once per pipeline, vector exits only |
| `search/hybrid.py` | `embedding/roles.py` | `embed_query` on hybrid/`vec:`/HyDE legs | ✓ WIRED | Class-level role detection |
| `cli/commands/search.py` | `search/context_attach.py` | `enrich_results(..., vectors_untrusted=True)` | ✓ WIRED | vsearch/query identity path |
| `mcp/backend.py` | `embedding/identity.py` | Search-mode closure over the full loaded-model identity | ✓ WIRED | `partial(check_identity, current=identity, mode="search")` |
| `cli/commands/index.py` | `indexing/embed_writer.py` | `StreamingEmbedWriter.embed_document` per document | ✓ WIRED | One writer per collection |
| `indexing/embed_writer.py` | `search/vector.py` | `add_embeddings_batch` / `delete_embeddings_by_document` | ✓ WIRED | Shadow maintained with vectors |
| `indexing/embed_writer.py` | `embedding/identity.py` | `write_identity` on first vector write; dimension/normalized sanity | ✓ WIRED | In-transaction claim; post-commit flag |
| `indexing/watcher.py` | `indexing/embed_writer.py` | Same writer built in `ensure_ready` | ✓ WIRED | Shared completeness/sanity/shadow |
| `cli/commands/index.py` | `database/maintenance.py` | `vacuum_index`/`backup_index` inside `index_lock` | ✓ WIRED | Busy/target errors translated |
| `database/maintenance.py` | `database/factory.py` | `create_connection` + `WAL_CHECKPOINT_TRUNCATE` | ✓ WIRED | Own connection, outside `Database.transaction()` |
| `cli/main.py` | `database/maintenance.py` | `reconcile_embedded_documents` in cleanup | ✓ WIRED | Same transaction |
| `tests/unit/embedding/test_manager.py` | `embedding/manager.py` | Literal pre-phase bucket + encode kwargs | ✓ WIRED | `DEFAULT_QWEN3_CACHE_MODEL_ID` recorded literal |
| `tests/unit/search/test_hybrid.py` | `embedding/roles.py` | No-prompt path reproduces SC1 golden | ✓ WIRED | Default path unchanged |
| `docs/architecture.md` | `embedding/identity.py` | Documented identity/shadow/streaming/maintenance surfaces | ✓ WIRED | Hand-maintained, consistent with code |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
| -------- | ------------- | ------ | ------------------ | ------ |
| `search/staleness.py` → CLI JSON / MCP metadata | `vectors_stale` | `embedded_documents` shadow (transactional) | Yes — real rows from vector writes | ✓ FLOWING |
| `cli/main.py` status | vector-lag text | `documents` anti-join `embedded_documents` | Yes — live counts | ✓ FLOWING |
| `database/maintenance.py` vacuum | before/after/reclaimed bytes | `stat()` of db + WAL around `VACUUM` | Yes | ✓ FLOWING |
| `database/maintenance.py` backup | output/bytes | `Connection.backup` + `integrity_check` + `stat()` | Yes | ✓ FLOWING |
| `embedding/identity.py` | identity JSON | settings + loaded model (`pooling_mode`, `revision`) + prompt scheme → `index_meta` | Yes | ✓ FLOWING |
| `search/context_attach.py` | `context_description` | `contexts` table, cached map invalidated by writes/commits/inode | Yes | ✓ FLOWING |

No static/empty/hardcoded data path was found in the Phase 21 surfaces.

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
| -------- | ------- | ------ | ------ |
| Full quality gate at final code state | `env -u FORCE_COLOR NO_COLOR=1 pytest -q` | 2750 passed, 1 skipped, 22 warnings in 119.41s; total coverage 95.18% (`fail_under=90` reached) | ✓ PASS |
| Phase unit battery (identity, manager, embedder, shadow, maintenance, writer, staleness, contexts) | `pytest -q --no-cov` on 8 files | 266 passed | ✓ PASS |
| Phase integration battery (maintenance, embed idempotency) | `pytest -q --no-cov` on 2 files | 17 passed | ✓ PASS |
| Host/schema battery (CLI index/search/bench/eval/main, hybrid, MCP, watcher, schema, snapshot) | `pytest -q --no-cov` on 10 files | 640 passed | ✓ PASS |
| Docs generators leave no diff | `python scripts/generate_cli_ref.py; python scripts/generate_config_ref.py` | both exit 0; `git status` clean for both generated files | ✓ PASS |
| Maintenance commands exposed on the index group | `python -m sif.cli.main index --help` | `vacuum` and `backup` listed with their help text | ✓ PASS |
| Missing-index refusal (both commands) | `python -m sif.cli.main --index /tmp/sif-verif-nonexistent.db index backup` | exit 1; `Error: No index found at ... Run 'sif index update' first.`; neither the index nor `backups/` created | ✓ PASS |
| Lint/format/type gates | `ruff check src tests`; `ruff format --check src tests`; `ty check src/sif` | clean; 218 files already formatted; clean | ✓ PASS |

The suite's single skip is outside the Phase 21 requirement-linked files (the phase-linked targeted runs reported zero skips; sqlite-vec is available in this environment).

### Probe Execution

N/A — no probe scripts are declared in the Phase 21 plans/summaries and no `scripts/*/tests/probe-*.sh` exists.

### Test Quality Audit

| Test File | Linked Req | Active | Skipped | Circular | Assertion Level | Verdict |
| --------- | ---------- | ------ | ------- | -------- | --------------- | ------- |
| `tests/unit/embedding/test_identity.py` | EMB-01, EMB-02 | 40 | 0 | No | Value + behavioral (round-trip, subprocess, comparison matrix) | PASS |
| `tests/unit/embedding/test_manager.py` | EMB-02 | 45 | 0 | No | Value (literal bucket strings, encode kwargs, cache rows) | PASS |
| `tests/unit/indexing/test_embed_writer.py` | SCALE-03, EMB-01 | 12 | 0 | No | Behavioral (transaction flags, garbage matrix, commit-failure proxy, resume) | PASS |
| `tests/unit/database/test_embedded_documents.py` | CORR-06 | 15 | 0 | No | Behavioral (fresh/legacy/orphan/drop-rebuild/only-new-writes) | PASS |
| `tests/unit/database/test_maintenance.py` | SCALE-01, SCALE-02 | 19 | 0 | No | Behavioral (busy/low-disk/mode/TOCTOU/integrity) | PASS |
| `tests/integration/test_embed_idempotency.py` | SCALE-03, EMB-01 | 15 | 0 | No | Behavioral (real CLI + real DB, mid-run resume, certification) | PASS |
| `tests/integration/test_maintenance.py` | SCALE-01, SCALE-02 | 2 | 0 | No | Behavioral (live reader/writer) | PASS |
| `tests/unit/search/test_staleness.py` | CORR-06 | 22 | 0 | No | Behavioral (recording connection asserts bounded SQL) | PASS |
| `tests/unit/search/test_context_attach.py` | CORR-06 | 25 | 0 | No | Behavioral (statement counting, cross-connection invalidation) | PASS |
| `tests/unit/cli/test_index.py` | SCALE-01/02/03, EMB-01 | 30+ | 0 | No | Behavioral (real CLI runs, lock ordering, refusal paths) | PASS |
| `tests/unit/cli/test_search.py`, `test_hybrid.py`, `test_bench.py`, `test_eval.py`, `test_mcp/test_backend.py` | EMB-01, EMB-02 | 100+ | 0 | No | Behavioral (warn-once, all-stale, BM25 silence, role dispatch) | PASS |

Conditional `pytest.skip` guards exist only for a host without sqlite-vec; the extension is present here, so the tests executed. Goldens are recorded literals (pre-phase bucket/SC1 values), not values generated by the system under test. No circular patterns, no requirement-linked disabled tests, no existence-only assertions on behavioral requirements.
**Disabled tests on requirements:** 0 → no blocker.
**Circular patterns detected:** 0 → no blocker.
**Insufficient assertions:** 0 → no warning.

### Decision Coverage

All trackable CONTEXT.md decisions are honored by shipped artifacts (20/20; `not_honored: []`, non-blocking gate).

### Requirements Coverage

| Requirement | Source Plan(s) | Description | Status | Evidence |
| ----------- | -------------- | ----------- | ------ | -------- |
| SCALE-01 | 21-06, 21-07 | Reclaim space safely via `sif index vacuum` (flock + quiesce + no open txn + checkpoint + 2× disk check; retryable busy; target paths restricted) | ✓ SATISFIED | `maintenance.vacuum_index`, `index.vacuum_cmd`, unit + integration + CLI tests; no target argument; docs committed |
| SCALE-02 | 21-06, 21-07 | Back up the index safely (SQLite online backup API + `integrity_check`) | ✓ SATISFIED | `backup_index`, exclusive 0600 target, `[('ok',)]` gate, live-write integration test, CLI/docs |
| SCALE-03 | 21-05, 21-07 | Embed large corpora without giant transactions (streaming batches; outside txn; short per-batch commits; resumable; CR-02 reporting preserved; batch sanity) | ✓ SATISFIED | `StreamingEmbedWriter`, `validate_batch`, failure taxonomy, resume/certification tests, watcher routing |
| CORR-06 | 21-02, 21-03, 21-06, 21-07 | Fast searches without per-query full scans (bounded staleness/context reads via the transactional shadow; staleness derived; verbatim two-sided contexts) | ✓ SATISFIED | Shadow maintenance/backfill/reconcile, bounded staleness/status reads, context cache with three invalidation triggers |
| EMB-01 | 21-01, 21-04, 21-05, 21-07, 21-08 | Protection from silent model swaps (persisted identity with the cache's `_cache_model_id` format; 3 dim guards consolidated; legacy warn-once + backfill; mismatch fail-fast/warn+mark) | ✓ SATISFIED | `identity.py`, schema/watcher/MCP/embed/search wiring, legacy lifecycle + same-dim swap tests |
| EMB-02 | 21-01, 21-04, 21-05, 21-07 | Correct query-vs-document embeddings (role-aware `prompt_name`; prompt in the cache key; Qwen3 default byte-identical) | ✓ SATISFIED | Role helpers + concrete role methods, prompt/revision buckets, default-baseline and SC1 golden tests |

**Coverage:** 6/6 requirements satisfied. PLAN `requirements:` fields collectively cover every REQUIREMENTS.md ID mapped to Phase 21; no orphaned Phase 21 requirements were found. `REQUIREMENTS.md` records all six as Complete.

### Anti-Patterns Found

No `TBD`/`FIXME`/`XXX` debt markers exist in any Phase 21-changed file. No stub rendering, hardcoded-empty data, or console-log-only implementation was found in the changed source. The table records the review ledger's open Info items and one pre-existing stub-language hit for transparency; none violates a Phase 21 must-have.

| File | Line | Pattern | Severity | Impact |
| ---- | ---- | ------- | -------- | ------ |
| `src/sif/embedding/manager.py` | 258-273 | Prompted bucket can pair with an unprompted encode for protocol-only embedders | ℹ️ Info | Unreachable for production backends (prompt-supported types define role methods); future-backend hardening (IN-01, open) |
| `src/sif/embedding/identity.py` | 88-114 | Stored `schema` accepted without `IDENTITY_SCHEMA_VERSION` validation | ℹ️ Info | Future-payload hardening; current writer always emits v1 (IN-02, open) |
| `src/sif/embedding/embedder.py` | 92-101, 444-450 | GGUF revision hashes the model file when an identity is built | ℹ️ Info | Startup cost for GGUF hosts; not a correctness or phase-criterion issue (IN-03, open; real-model cost listed as a manual note in 21-VALIDATION.md) |
| `src/sif/cli/commands/eval.py` | 79, 233-241 | ModelScope labeled a remote provider | ℹ️ Info | Pre-existing disclosure text; not introduced by Phase 21 (IN-04, open) |
| `src/sif/cli/commands/index.py` | 391 | `list_by_collection` materializes document bodies before the per-document loop | ℹ️ Info | Peak CLI memory is O(collection text); transactions are still per document and SCALE-03's transaction criterion holds (IN-05, open) |
| `src/sif/indexing/embed_writer.py` | 178-180 | Chunkless document returns before purging pre-existing rows | ℹ️ Info | The phase truth "writes nothing and creates no shadow row" holds; the self-healing docstring is narrower than total (IN-06, open) |
| `src/sif/search/expansion.py` | 58-65 | Unreachable `if not variants` branch | ℹ️ Info | Pre-existing dead branch (IN-07, open) |
| `src/sif/embedding/factory.py` | 98 | `NotImplementedError("HuggingFace models not yet implemented")` | ℹ️ Info | Pre-existing and unchanged; `model_type` validation rejects the HuggingFace backend (per CLAUDE.md), so it is not reachable |

**Anti-patterns:** 8 found (0 blockers, 0 warnings, 8 info).

### Human Verification Required

None. This is an infrastructure/foundation phase whose user-visible CLI outputs (vacuum/backup sizes, retry errors, identity mismatch warnings, stale markers) are asserted by automated CLI tests; no user-facing UI, real-time behavior, or external service UX remains unverified. The two review findings previously marked "requires human verification" are verified above by deterministic regression tests.

### Gaps Summary

**No gaps found.** All 5 roadmap success criteria and all 58 plan must-have truths are backed by implementation evidence and passing behavioral tests. The full quality gate is green (2750 passed, 1 skipped, 95.18% coverage), both generator-owned docs reproduce byte-identically, the three dim guards share one read, and the Phase 21 contracts consumed by Phase 22 (stable embed surface + MCP identity policy) and Phase 23 (identity-protected Harrier arms + prompt scheme) are in place.

**Residual notes (non-blocking):** (a) CR-02's live two-process interleaving is not simulated; the invariant relies on SQLite's documented `BEGIN IMMEDIATE` semantics plus the flock, and the stale-claim/refusal/adoption transitions are tested; (b) the GGUF hash-time measurement on the real 1.19 GB model remains the manual note recorded in 21-VALIDATION.md; (c) the seven open Info findings from `21-REVIEW-DISPOSITION.md` are advisory hardening items, not phase must-haves.

---

_Verified: 2026-11-15T18:38:39Z_
_Verifier: Claude (gsd-verifier)_
