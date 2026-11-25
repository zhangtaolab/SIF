---
phase: "24"
slug: "tuning-models-ux-install-docs"
verified: "2026-11-25T02:49:17Z"
verified_at: "2026-11-25T02:49:17Z"
verifier: "gsd-verifier (ZCode subagent)"
status: passed
score: "5/5 requirements; 43/43 plan must-have truths"
covered_files:
  - ".github/workflows/docs.yml"
  - ".planning/milestones/v1.2-phases/24-tuning-models-ux-install-docs/24-01-PLAN.md"
  - ".planning/milestones/v1.2-phases/24-tuning-models-ux-install-docs/24-01-SUMMARY.md"
  - ".planning/milestones/v1.2-phases/24-tuning-models-ux-install-docs/24-02-PLAN.md"
  - ".planning/milestones/v1.2-phases/24-tuning-models-ux-install-docs/24-02-SUMMARY.md"
  - ".planning/milestones/v1.2-phases/24-tuning-models-ux-install-docs/24-03-PLAN.md"
  - ".planning/milestones/v1.2-phases/24-tuning-models-ux-install-docs/24-03-SUMMARY.md"
  - ".planning/milestones/v1.2-phases/24-tuning-models-ux-install-docs/24-04-PLAN.md"
  - ".planning/milestones/v1.2-phases/24-tuning-models-ux-install-docs/24-04-SUMMARY.md"
  - ".planning/milestones/v1.2-phases/24-tuning-models-ux-install-docs/24-05-PLAN.md"
  - ".planning/milestones/v1.2-phases/24-tuning-models-ux-install-docs/24-05-SUMMARY.md"
  - ".planning/milestones/v1.2-phases/24-tuning-models-ux-install-docs/24-06-PLAN.md"
  - ".planning/milestones/v1.2-phases/24-tuning-models-ux-install-docs/24-06-SUMMARY.md"
  - ".planning/milestones/v1.2-phases/24-tuning-models-ux-install-docs/24-07-PLAN.md"
  - ".planning/milestones/v1.2-phases/24-tuning-models-ux-install-docs/24-07-SUMMARY.md"
  - ".planning/milestones/v1.2-phases/24-tuning-models-ux-install-docs/bench/breadcrumb-verdict.json"
  - ".planning/milestones/v1.2-phases/24-tuning-models-ux-install-docs/bench/chunk-sweep.json"
  - "Makefile"
  - "README.md"
  - "docs/benchmarking.md"
  - "docs/cli-reference.md"
  - "docs/configuration.md"
  - "docs/index.md"
  - "docs/installation.md"
  - "docs/migration.md"
  - "docs/models.md"
  - "docs/quickstart.md"
  - "scripts/breadcrumb_eval.py"
  - "scripts/chunk_sweep.py"
  - "scripts/generate_cli_ref.py"
  - "scripts/generate_config_ref.py"
  - "src/sif/cli/commands/eval.py"
  - "src/sif/cli/commands/index.py"
  - "src/sif/cli/commands/models.py"
  - "src/sif/cli/commands/pull.py"
  - "src/sif/cli/main.py"
  - "src/sif/config/constants.py"
  - "src/sif/config/settings.py"
  - "src/sif/indexing/breadcrumb.py"
  - "src/sif/indexing/embed_writer.py"
  - "src/sif/indexing/watcher.py"
  - "src/sif/models/download.py"
  - "src/sif/search/embedder_verdict.py"
  - "src/sif/search/personal_bench.py"
  - "src/sif/search/tuning_verdict.py"
  - "tests/test_ci_workflows.py"
  - "tests/test_docs.py"
  - "tests/unit/cli/test_eval.py"
  - "tests/unit/cli/test_index.py"
  - "tests/unit/cli/test_models.py"
  - "tests/unit/cli/test_pull.py"
  - "tests/unit/config/test_settings.py"
  - "tests/unit/indexing/test_breadcrumb.py"
  - "tests/unit/indexing/test_embed_writer.py"
  - "tests/unit/models/test_download.py"
  - "tests/unit/scripts/test_breadcrumb_eval.py"
  - "tests/unit/scripts/test_chunk_sweep.py"
  - "tests/unit/search/test_personal_bench.py"
  - "tests/unit/search/test_tuning_verdict.py"
covered_digest: "v4:sha256:62dcaa380218a87ee9b639335669e09f2104cc08b6aa8cdd2a36e7145b89db1e"
behavior_unverified: 0
overrides_applied: 0
coincidental_reliance_items:
  - truth: "24-01 truth 4: an empty corpus yields insufficient-evidence and still writes a countable artifact"
    reason: fixture-only
    harden: "Declare the precondition: the countable insufficient-evidence artifact is written when the eval stages complete but yield no admissible evidence. A corpus below the instrument's 50-document adequacy floor aborts with exit 1 and no artifact."
  - truth: "24-04 truth 2: sif models pull emits no prompts or progress bars in a non-TTY context"
    reason: undeclared-precondition
    harden: "Declare that library progress output on a real download is suppressed only under quiet mode (-q), or suppress it whenever stdout is not a TTY. The non-TTY output test replaces ModelDownloader, so the real library path is exercised by no test."
gaps: []
re_verification:
  previous_status: passed
  previous_score: "5/5 requirements; 43/43 plan must-have truths"
  reason: "Stale-input regeneration. verification.status reported stale because the covered file tests/test_ci_workflows.py changed at 10a9685 (plan 17-10 restored the 8-cell CI matrix and the every-branch push trigger). All 43 plan must-have truths and the 5 roadmap success criteria were re-derived from the seven plans and judged against HEAD be244bb on live evidence; no prior claim was carried forward. Six statements in the 2026-11-24 report were wrong or imprecise and are corrected in the delta section. Two advisory reliance items are recorded; neither changes a truth status."
  gaps_closed: []
  gaps_remaining: []
  regressions: []
---

# Phase 24: Tuning + Models UX + Install Docs Verification Report

**Phase Goal:** Chunking defaults are evidence-gated, model management is reliable, and every platform has a correct install path — the milestone closes on measured defaults and generator-verified docs.

**Verified:** 2026-11-25T02:49:17Z (HEAD `be244bb`, branch `gsd/phase-24-reverify`)
**Status:** passed
**Re-verification:** Yes — stale-input regeneration; every must-have re-derived from the current tree.
**Requirements:** QUAL-02, QUAL-03, MODELS-01, MODELS-02, DOCS-01

Method: goal-backward against the archived ROADMAP success criteria (5) and the seven PLAN `must_haves` (43 truths). Every claim below rests on a live file at HEAD, a command run during this verification, or a passing test — not on SUMMARY text or the prior report. No product source, test, doc, workflow, or default was modified; nothing was fixed.

Scope of this run, stated plainly: the full suite was **not** run locally (CI ran it on a byte-identical tree, confirmed below); no real model download and no sweep re-run was performed; the literal `make docs-generate` target was not run (both generator `main()` functions were re-run with only the output directory redirected, then byte-compared).

## Post-Verification Delta (e64c52c..be244bb) and Requirement Impact

`git diff --stat e64c52c..HEAD` outside `.planning/` shows five files. Nothing under `src/`, `scripts/`, `Makefile`, `pyproject.toml`, or `uv.lock` changed.

| File | Change | Requirement impact |
|------|--------|--------------------|
| `tests/test_ci_workflows.py` | Commit `10a9685` (plan 17-10). `MATRIX_EXCLUSION` removed; five matrix/trigger constants added; `test_matrix_declares_six_cells` replaced by `test_matrix_declares_eight_cells`; `test_matrix_push_trigger_is_main_only` replaced by `test_matrix_push_trigger_covers_all_branches`. | **None adverse.** AST comparison against `e64c52c`: 22 of 24 functions identical; only those two replaced. The five `test_installation_docs_*` guards (DOCS-01) are unchanged, shifted by +8 and +39 lines. All 18 tests pass, and each guard still decides its claim: 21 of 21 complete-removal mutations turned it red. |
| `.github/workflows/test-matrix.yml` | Same commit: push trigger `[main]` to `['**']`; the two macOS exclusions removed, restoring 8 cells. | **None.** Not a covered file; evidence only. Truth 36 cites this run's result, not the workflow text. |
| `docs/contributing.md`, `docs/development.md`, `docs/testing.md` | `a321eaa`: eight-cell wording. | **None.** Not Phase 24 deliverables. |

### Corrections to the 2026-11-24 report

1. **`tests/test_ci_workflows.py` row (old line 99).** It described a six-cell matrix guard with macOS exclusions and a `[main]`-only push trigger. That was true when written and is false at HEAD: the module now pins the full 8-cell product with no skip entries, and a push on every branch plus `pull_request`. The row above replaces it.
2. **Success criterion 5 evidence.** It cited "`.github/workflows/test-matrix.yml:79` runs the gate". That was wrong when written: `test-matrix.yml` has zero `docs-generate` references at `462266e`, `e64c52c`, and HEAD, and line 79 was the type-check step. The CI diff gate lives at **`.github/workflows/docs.yml:38-42`** (both generators, then `git diff --exit-code`), unchanged since `92e01502` (2026-11-07).
3. **Artifact count.** "27/27 declared artifacts pass" was imprecise. The verb reports **27 of 29** at their declared path; plan 06's two bench artifacts are reported MISSING there because the plan frontmatter still names `.planning/phases/24-…`. Both exist, tracked, at the archived path — see Artifacts.
4. **CI evidence.** "All 7 matrix cells plus lint, run 45135099379" was a wording slip: that run is 7 jobs in total (6 matrix cells plus lint) at `f9d238e` on `main`. It is superseded by run `45522236981` (8 cells plus lint, `a25eb07`).
5. **Truth 5 evidence** omitted two literal deviations from the must-have wording (no `vectors` key; limitation states N=194, not N=56). They are disclosed below rather than passed silently.
6. **Truth 25 evidence** did not mention that `docs/index.md` carries no `uvx` one-off command of its own. Disclosed below.

## Goal Achievement

### Roadmap Success Criteria

| # | Success Criterion | Status | Evidence |
|---|-------------------|--------|----------|
| 1 | Held-out-gated chunk size/overlap sweep; per-arm re-chunk + re-embed on isolated arms; embed cost reported; defaults change only via the gate | ✓ VERIFIED | Live dry run: six arms, only `SIF_CHUNK_SIZE`/`SIF_CHUNK_OVERLAP` differ, each with its own `--index` DB and `index embed --force`. Committed artifact: six arms over 610 documents with per-arm embed seconds and cache deltas. Committed decision `keep-default`; replay through the current policy reproduces it. `DEFAULT_CHUNK_SIZE=512`, `DEFAULT_CHUNK_OVERLAP=128`. |
| 2 | Title-breadcrumb experiment; per-leg ablation; title-signal duplication checked against Phase 19 title FTS; defaults change only via the gate | ✓ VERIFIED | Artifact: overall held-out +0.014104 (`winner: false`), title leg +0.048521 (`winner: true`), body leg +0.006243 (`winner: false`). The title leg is the comparison against the already-indexed title; the body-leg veto rejects a title-only gain. Decision `keep-breadcrumb-off`; `embed_breadcrumb` is `False`. |
| 3 | `sif models pull` reliable; DEFAULT_MODELS Qwen3-0.6B family; SHA-256 cache check (no md5); deterministic ModelScope path; canonical cache dir | ✓ VERIFIED | Registry: Qwen3-Embedding-0.6B / Qwen3-Reranker-0.6B / Qwen2.5-0.5B-Instruct, all `master`, equal to the shipped Settings defaults. `verify_manifest` uses SHA-256; `md5` appears nowhere in `src/sif/models`. Canonical `<cache>/models/<owner>/<name>`. |
| 4 | `sif models status` shows identity/backend/dims with a backend probe; no Rich output in non-TTY contexts | ✓ VERIFIED | Live plain run: five sections in declared order, zero box-drawing characters, exit 0. "Silent" is read as the plan defines it — plain `section.key: value` or JSON, Rich only on a TTY — since the command must also print its report. |
| 5 | uv-first install docs with Linux CPU torch recipe, llama-cpp indexes, degradation matrix, client snippets; every new command/Settings field passes the `make docs-generate` CI diff gate | ✓ VERIFIED | Four entry points lead with `uv tool install`; `installation.md:30` CPU recipe; llama-cpp `:159-210`; matrix `:212-225`; snippets `:227-275`. Both generators re-run byte-identically. CI gate at `.github/workflows/docs.yml:38-42`. |

### Plan Must-Have Truths

All 43 truths declared across the seven PLAN frontmatter files (7+3+7+7+7+6+6) are VERIFIED on the current tree. No truth is FAILED or PRESENT_BEHAVIOR_UNVERIFIED, and none is overridden. Two carry an advisory reliance note.

| # | Plan | Truth (short) | Status | Evidence |
|---|------|---------------|--------|----------|
| 1 | 24-01 | Six-arm fixed grid, shipped default first, Qwen3 pins, only chunk knobs vary | ✓ VERIFIED | `SWEEP_GRID` (`tuning_verdict.py:53-60`). Live dry run: six arms, 512/128 first; every arm `modelscope`, Qwen3-Embedding-0.6B, dim 1024, `SIF_MAX_TOKENS=512`; the only `SIF_*` keys differing across arms are `SIF_CHUNK_SIZE` and `SIF_CHUNK_OVERLAP`; `SIF_EMBED_BREADCRUMB` stripped |
| 2 | 24-01 | Identity asserted after embed, before eval; recorded; mismatched baseline rejected/regenerated | ✓ VERIFIED | Stage order index, embed, identity, eval. The identity stage re-checks the probe and raises naming the field (`chunk_sweep.py:378-415`, `633-638`); a failure returns 1 before eval. `baseline_rejection_reason` (`:461-488`). Run state shows identity `ok` between embed and eval for all six arms. `test_wrong_backend_cache_id_fails`, `test_other_mismatches_name_the_field` (4 cases), `test_sentence_transformers_backend_is_rejected`, `test_different_model_name_is_rejected`, `test_fingerprint_mismatch_is_rejected` pass |
| 3 | 24-01 | Tuning-select then held-out confirm; deterministic tie-break; equal gate never adopts | ✓ VERIFIED | Replay of the committed artifact gives `overlap-0` then `keep-default`. Real `noise_gate`: N=100 with +0.01 ties its floor and `winner=False`, N=101 with +0.02 wins, so the adopt branch is reachable and the gate is real. `test_n100_epsilon_tie_keeps_default`, `test_n101_two_epsilon_win_adopts`, `test_equal_deltas_resolve_by_wall_time_then_grid_order` pass |
| 4 | 24-01 | Empty, zero-query, or sub-floor evidence gives insufficient-evidence, no default change, a countable artifact | ✓ VERIFIED (coincidental-reliance) | `finalize_sweep(results={})` exits 3 and writes a six-arm `insufficient-evidence` artifact (`test_empty_results_are_insufficient_and_countable`); `test_below_sufficiency_floor_is_insufficient` passes. Reliance: a physically empty corpus never reaches the writer — reliance item 1 |
| 5 | 24-01 | Committed artifact: per-arm costs, fingerprint, min 101, limitation, no query text or paths | ✓ VERIFIED | Per-arm documents, chunks, embedded_documents, embed_wall_seconds, cache rows, cache hits; fingerprint `9ccbf4eea9263ed4`; `min_heldout_for_epsilon_win=101`; no `/Users/`, `/home/`, `query_text`, `document_path`. Literal deviations disclosed: no key named `vectors` (the count is `chunks`); the limitation states the measured N=194, not N=56 (observations 3 and 4) |
| 6 | 24-01 | `--dry-run` prints the full ordered plan with no subprocess; scope change invalidates markers | ✓ VERIFIED | Live dry run with `subprocess.run`, `Popen`, `check_call`, `check_output` stubbed to raise: exit 0, zero spawns, scratch root still empty afterwards. `test_dry_run_json_invokes_no_subprocess`, `test_changed_scope_discards_prior_markers` pass |
| 7 | 24-01 | Overwrite guard refuses a differing decision or fingerprint without `--force` | ✓ VERIFIED | `write_committed_artifact` (`:950-979`) compares `(decision, corpus_fingerprint)`. `test_different_decision_is_refused`, `test_force_replaces_a_different_run` pass |
| 8 | 24-02 | Breadcrumb embed text; stored content, FTS, snippets, BM25 byte-identical | ✓ VERIFIED | `breadcrumb_embed_texts`; all 22 tests in `test_breadcrumb.py` pass. Direct on/off comparison over two real indexes: stored `content`, `chunks_fts` rows, raw `bm25()` scores, and `BM25Searcher` results (score, snippet, highlights) identical. An off/off control shows only per-build `id`, `document_id`, `created_at` differ between any two builds |
| 9 | 24-02 | `embed_breadcrumb: bool = False` (env), no CLI flag | ✓ VERIFIED | `settings.py:224-228`; no Click option for it under `src/sif/cli/`; live `Settings().embed_breadcrumb is False`. `test_embed_breadcrumb_is_off_by_default`, `test_embed_breadcrumb_enabled_via_env` pass |
| 10 | 24-02 | Only the embedding input changes; cache key changes; isolated DB plus `--force`; identity not extended | ✓ VERIFIED | Swap happens only at the embed call (`embed_writer.py:188-198`); both call sites pass the setting (`index.py:422`, `watcher.py:296`); the arm runs `index embed --force` on its own DB; `EmbedderIdentity` has no breadcrumb field. `test_breadcrumb_flag_changes_the_embedded_strings` passes |
| 11 | 24-03 | Canonical cache path; explicit cache_dir honored | ✓ VERIFIED | `canonical_model_dir` (`download.py:97-100`). Live status reports `<cache>/models/Qwen/Qwen3-Embedding-0.6B` |
| 12 | 24-03 | Cache hit requires manifest, size, and SHA-256; manifestless directory re-downloads | ✓ VERIFIED | `verify_manifest` (`:126-155`). `test_nonempty_directory_without_manifest_is_not_a_hit`, `test_hash_mismatch_is_not_a_hit` pass |
| 13 | 24-03 | Atomic sibling temp download, verify, replace; no partial target or leftovers | ✓ VERIFIED | `_install_directory` (`:223-250`). `test_success_leaves_no_temporary_or_backup_directories`, `test_client_failure_leaves_no_target_or_scratch_directory`, `test_missing_config_json_fails_and_cleans_up` pass |
| 14 | 24-03 | DEFAULT_MODELS Qwen3-0.6B family with explicit revision; matches Settings | ✓ VERIFIED | Live registry print; equals `Settings.model_name` and `Settings.reranker_model_name`. `test_registry_matches_shipped_settings_defaults` passes |
| 15 | 24-03 | Legacy layouts recognized and migrated; source survives until the target verifies | ✓ VERIFIED | `_legacy_candidates`, `_adopt_legacy_model` with source restore on failure (`:223-326`). `test_home_sif_models_layout_is_migrated`, `test_failed_rename_falls_back_to_download_and_keeps_source`, `test_legacy_directory_without_weights_is_ignored` pass |
| 16 | 24-03 | `--force` bypass; missing modelscope raises an actionable error naming the embed extra | ✓ VERIFIED | `MODELSCOPE_INSTALL_HINT` (`:37-40`), raised at `:475` before any directory is created. `test_force_redownloads_despite_valid_manifest`, `test_missing_modelscope_raises_actionable_import_error` pass |
| 17 | 24-03 | `inspect_cache` reports five states and the revision without downloading | ✓ VERIFIED | `inspect_cache` (`:396-425`). `test_reports_all_states_without_importing_modelscope` passes; live `absent` on an empty root. Narrowing at the status call site: observation 7 |
| 18 | 24-04 | `models pull` with no argument, a family name, or `owner/name` | ✓ VERIFIED | `resolve_model_target` (`models.py:60-77`); target-resolution tests pass; `sif models --help` lists `pull` and `status` |
| 19 | 24-04 | `--force`; non-interactive; no prompts or progress bars in non-TTY; actionable ClickException | ✓ VERIFIED (coincidental-reliance) | `test_force_is_forwarded`, `test_non_tty_output_is_one_plain_line`, `test_missing_modelscope_becomes_click_exception` pass; the Rich line is TTY-gated. Reliance: the library's own output on a real un-quieted download is exercised by no test — reliance item 2 |
| 20 | 24-04 | `models status [--json]` reports settings, cache, identity with source and fingerprints; probe imports and downloads nothing | ✓ VERIFIED | Live plain and JSON runs. In a fresh subprocess with every embeddable backend import blocked, status exited 0 with zero import attempts during the command and still reported ModelScope available. URI-encoding caveat: observation 9 |
| 21 | 24-04 | Five explicit identity states; a mismatch is reported with exit 0 | ✓ VERIFIED | `test_no_index_reports_no_index`, `test_index_without_identity_row_reports_no_identity`, `test_matching_identity_reports_match`, `test_model_mismatch_is_reported_exit_zero`, `test_stored_dimension_mismatch`, `test_schema_width_mismatch` pass |
| 22 | 24-04 | Non-TTY output is plain lines or JSON; Rich only on a TTY | ✓ VERIFIED | Live piped output: `section.key: value` in declared order, zero box-drawing characters; JSON sorted at every level. `test_tty_renders_table` passes |
| 23 | 24-04 | `sif pull` stays a hidden deprecated alias; notice on stderr only | ✓ VERIFIED | `hidden=True` (`pull.py:125`), stderr-only console (`:31`). Top-level help omits `pull`; `pull --help` says deprecated. `test_pull_is_hidden`, `test_pull_registry_name_delegates`, `test_pull_modelscope_id_delegates` pass |
| 24 | 24-04 | Generator and tests skip hidden commands | ✓ VERIFIED | `generate_cli_ref.py:104,120`; `test_docs.py:455`. Generated reference: `sif models pull` once, `sif models status` once, `### sif pull` zero times; regeneration byte-identical |
| 25 | 24-05 | Every entry-point install doc leads with uv; pip secondary | ✓ VERIFIED | README, installation, quickstart, index: the first install command in each is `uv tool install`, with embed and BM25-only commands in all four. The `uvx` one-off appears in README, installation, and quickstart; `docs/index.md:94` routes `uvx` to the guide by pointer (observation 5) |
| 26 | 24-05 | Linux CPU recipe and uv floor; pyproject-index claim removed | ✓ VERIFIED | `installation.md:6`, `:30`. No stale claim in any entry point. Guard turns red when the claim is removed |
| 27 | 24-05 | llama-cpp wheel indexes, multi-index strategy, source build, Python 3.12 path | ✓ VERIFIED | `installation.md:159-210` |
| 28 | 24-05 | Honest degradation matrix | ✓ VERIFIED | `installation.md:212-225`. The quoted error string matches `src/sif/search/vector.py:56`; the MCP degrade warning is at `src/sif/mcp/backend.py:527`. Guard turns red when any row is removed |
| 29 | 24-05 | Client snippets link the canonical MCP guide | ✓ VERIFIED | `installation.md:227-275` links `mcp-server.md`; `sif mcp stdio` and `sif mcp http --host --port` exist; `/mcp` is the real endpoint (`src/sif/mcp/app.py:234`) |
| 30 | 24-05 | models.md Model Management; migration.md canonical cache path | ✓ VERIFIED | `docs/models.md` has `## Model Management` before Related Documentation with every required anchor; `docs/migration.md` carries `models/`, `SIF_CACHE_DIR`, and the migration note |
| 31 | 24-05 | `make docs-generate` clean; docs tests guard uv-first, the matrix, and the retired model name | ✓ VERIFIED | Both generators re-run byte-identically. `TestInstallAndModelDocs` (7 tests) and the five `test_ci_workflows.py` install guards pass. Old-model-name guard: `test_hand_docs_do_not_name_the_retired_7b_default` |
| 32 | 24-06 | Real six-arm sweep with a fresh Qwen3 baseline produces a committed artifact | ✓ VERIFIED | `chunk-sweep.json` equals the on-disk run state field for field (118 compared, 0 mismatches): 24 stage markers from 06:29:37Z to 08:37:12Z on 2026-11-17, 610 documents per arm, fresh baseline |
| 33 | 24-06 | Real breadcrumb arm on the same corpus produces a committed artifact | ✓ VERIFIED | `breadcrumb-verdict.json` equals its run state (13 compared); markers 08:37:25Z to 09:07:39Z; it reused the sweep's fresh baseline |
| 34 | 24-06 | Defaults change only when an artifact decision authorizes it | ✓ VERIFIED | Both decisions are keep outcomes and the replay reproduces them. Live: 512/128 and `embed_breadcrumb=False` |
| 35 | 24-06 | Marker code only on a flip; real-embed-path test asserts presence or absence | ✓ VERIFIED | Zero `chunking.contract` hits in `src/` and `scripts/`. `test_embed_writes_chunking_contract_marker_iff_contract_flipped` passes, asserting absence |
| 36 | 24-06 | benchmarking.md records both experiments | ✓ VERIFIED | `docs/benchmarking.md:332-363`; 30 automated reconciliation checks pass against the artifacts and the title-leg row matches to six decimals on every value. The citations name the retired path (observation 6) |
| 37 | 24-06 | Full suite, docs diff gate, and type check green | ✓ VERIFIED | CI run `45522236981` on `a25eb07`, whose non-planning tree is byte-identical to HEAD: 8 cells at 3259 passed, 2 skipped, 95.12%; lint job `ty check src/sif` printed "All checks passed!". Local `ty` differs by environment (observation 10) |
| 38 | 24-07 | Duplicate metrics per document, aggregated per chunk | ✓ VERIFIED | `duplicate_metrics`; `aggregate_duplicate_metrics` weights by chunk count. `test_weighting_uses_chunk_counts_not_document_counts` passes |
| 39 | 24-07 | Body-leg veto | ✓ VERIFIED | `decide_breadcrumb_default` (`:298-358`); replay gives `keep-breadcrumb-off`. Seven veto tests pass, including `test_overall_winner_with_a_flat_body_leg_is_title_leg_only` and `test_absent_body_leg_is_insufficient_evidence` |
| 40 | 24-07 | Runbook pins the identity, asserts it after embed and before eval, records it | ✓ VERIFIED | Live dry run: one arm, `SIF_EMBED_BREADCRUMB=1`, pinned Qwen3. `test_identity_mismatch_names_the_failing_field` (3 cases) pass; the artifact carries `model_type` and the identity |
| 41 | 24-07 | Mismatched baseline rejected and regenerated on the same backend | ✓ VERIFIED | `choose_baseline` (`breadcrumb_eval.py:339-354`). `test_backend_or_model_mismatch_regenerates_the_baseline` (2 cases), `test_fingerprint_mismatch_regenerates_the_baseline` pass |
| 42 | 24-07 | Artifact aggregate-only, min 101, limitation, overwrite guard | ✓ VERIFIED | `breadcrumb-verdict.json`: aggregate only, `min_heldout_for_epsilon_win=101`, no paths or text; guard shared with the sweep. `test_artifact_is_aggregate_only`, `test_differing_decision_requires_force`, `test_differing_fingerprint_requires_force` pass. The limitation states N=194, not N=56 (observation 3) |
| 43 | 24-07 | `--dry-run` prints one ordered arm with no subprocess | ✓ VERIFIED | Live dry run with subprocess stubbed: exit 0, zero spawns, no files written; stages `arm:index`, `arm:embed`, `arm:identity`, `arm:eval`. `test_dry_run_invokes_no_subprocess_and_writes_no_file` passes |

### Requirement Verdicts

| Requirement | Plans | Truths | Verdict |
|-------------|-------|--------|---------|
| QUAL-02 | 24-01, 24-06 | 13/13 | PASS — six-arm instrument, isolated arms, per-arm embed cost, held-out gate as the only route to a default change; real committed artifact with keep-default; replay reproduces it |
| QUAL-03 | 24-02, 24-06, 24-07 | 15/15 | PASS — builder, default-off switch, writer wiring; per-leg ablation with duplicate metrics; body-leg veto; real artifact keeps the default; replay reproduces it |
| MODELS-01 | 24-03, 24-04 | 14/14 | PASS — canonical manifest cache with SHA-256, atomic install, legacy migration, Qwen3 registry; `sif models pull` target resolution and error conversion tested |
| MODELS-02 | 24-04 | 7/7 | PASS — status reports settings, cache, identity, backend, dimensions; exit 0 in every state; plain non-TTY output; hidden alias; generator skips hidden commands |
| DOCS-01 | 24-05 | 7/7 | PASS — uv-first entry points, CPU recipe, llama-cpp indexes, degradation matrix, client snippets, model-management and migration sections, clean generator gate |

Plans tagged with two requirements are counted under each; 43 truths are unique. Requirements traceability in `v1.2-REQUIREMENTS.md` maps exactly these five IDs to Phase 24, with none orphaned.

### Advisory (New Scope, Unevidenced)

None. The Step 7 scan over the 40 phase files produced no new findings: no `TBD`, `FIXME`, or `XXX`; no `TODO`, `HACK`, or `PLACEHOLDER` outside tests; the `placeholder` hits are SQL bind-parameter builders and the bare `pass` lines are a Click group body and two `with open_initialized_database(...)` blocks. Carried observations are listed under Non-Blocking Observations.

### Decision Coverage

12 of 12 trackable CONTEXT.md decisions are honored by shipped artifacts (`check.decision-coverage-verify`; non-blocking gate).

## Artifacts and Key Links

`verify.artifacts` over all seven plans: **27 of 29 pass at the declared path.** Plans 01, 02, 03, 04, 05, and 07 pass in full. Plan 06 exits 1 because two declared paths still read `.planning/phases/24-…`.

| Artifact | Declared path status | Resolution |
|----------|----------------------|------------|
| `bench/chunk-sweep.json` | MISSING at `.planning/phases/24-…` (verb) | Present and tracked at the archived path. Git records an `R100` rename at milestone archival; blob `9460046767a1` is identical before, after, and at HEAD |
| `bench/breadcrumb-verdict.json` | MISSING at `.planning/phases/24-…` (verb) | Same: `R100` rename; blob `77177e660c80` identical at all three points |
| Other 27 declared artifacts | VERIFIED | Pass exists, substance, and pattern checks |

`verify.key-links` over all seven plans: **20 of 20 WIRED** (4+2+2+3+3+3+3). The three plan-06 links pass on a textual reference, and the path they reference is the retired one (observation 6).

Wiring confirmed by reading and by the live runs: runbooks to `tuning_verdict` (replay); `models.py` to `ModelDownloader` and `inspect_cache`; `models.py` to `build_settings_identity` and `read_identity`; `pull.py` to the shared handler; `embed_writer.py` to `breadcrumb_embed_texts`; `index.py` and `watcher.py` to `settings.embed_breadcrumb`; `tests/test_ci_workflows.py` to `docs/installation.md` (mutation-tested).

## Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|--------------------|--------|
| `bench/chunk-sweep.json` | per-arm costs, confirmation | On-disk run state of the real six-arm run; 118 fields equal | Yes | ✓ FLOWING |
| `bench/breadcrumb-verdict.json` | gates, legs, duplicates | On-disk run state of the real arm; 13 fields equal | Yes | ✓ FLOWING |
| `docs/benchmarking.md` tables | verdict numbers | Committed artifacts; 30 automated checks pass, the remaining row verified to six decimals | Yes | ✓ FLOWING |
| `docs/cli-reference.md`, `docs/configuration.md` | command and field listings | Generators re-run; byte-identical to committed | Yes | ✓ FLOWING |
| `sif models status` | settings, cache, identity | Live `Settings`, cache inspection, read-only index read | Yes | ✓ FLOWING |

## Behavioral Evidence (run during this verification)

| Check | Command | Result |
|-------|---------|--------|
| CI workflow test module | `pytest tests/test_ci_workflows.py -q --no-cov` | 18 passed |
| Docs and CI-workflow guards | `pytest tests/test_docs.py tests/test_ci_workflows.py -q --no-cov` | 39 passed |
| Twelve phase unit files | `pytest <12 files> -q --no-cov` | 553 passed in 21.55s, 0 skipped (592 across the 14 phase files) |
| Named tests for behavior-dependent truths | `-k` selection over 9 files | 74 passed, 223 deselected |
| Install-guard discrimination | Each guard against a temp copy with its claim removed | 21 of 21 went red; 5 of 5 green on the unmodified copy |
| Artifact replay | Current `select_tuning_candidate`, `decide_chunk_default`, `decide_breadcrumb_default` on committed gates | `overlap-0` / `keep-default` and `keep-breadcrumb-off`; both match the artifacts |
| Gate strictness | `noise_gate` at N=100 +0.01 and N=101 +0.02 | `winner=False` then `winner=True` |
| Chunk-sweep dry run | `main(["--dry-run","--json"])`, subprocess stubbed | Exit 0, zero spawns, no files written |
| Breadcrumb dry run | Same | Exit 0, zero spawns, no files written |
| Breadcrumb byte-identity | Two real indexes, off and on, plus an off/off control | `content`, FTS rows, BM25 scores, snippets, highlights identical |
| Status output | `models status` and `--json`, temp index and cache | Plain lines in declared order; JSON sorted; exit 0; nothing written |
| Probe imports nothing | Fresh subprocess, backend imports blocked | Zero import attempts during status; exit 0 |
| Docs generator gate | Both generator `main()` with output redirected, then `cmp` | `cli-reference.md` (29,561 bytes) and `configuration.md` (13,690 bytes) byte-identical |
| Lint and format | `ruff check src tests`; `ruff format --check src tests` | All checks passed; 237 files already formatted |
| CI at the tested tree | `gh run view 45522236981` and per-job logs | 8 cells: 3259 passed, 2 skipped, 95.12% each (the two 3.13 cells log 27 warnings); lint job: ruff and `ty` "All checks passed!" |
| Source identity | `git diff --stat a25eb07..HEAD` excluding `.planning` | Empty; `a25eb07` is an ancestor of HEAD; working tree clean |

## Probe Execution

No probe scripts apply: `find scripts -path '*/tests/probe-*.sh'` returns nothing and no PLAN or SUMMARY declares a probe path. `--probe-identity` is a runbook CLI flag, not a probe script. Not applicable.

## Test Quality Audit

| Check | Result |
|-------|--------|
| Disabled tests on requirements | None. No `skip`, `skipif`, or `xfail` markers in the 14 phase test files; the conditional `pytest.skip` calls are environment guards that did not fire (592 passed, 0 skipped) |
| Circular patterns | None found. The generator-owned docs are produced by generators and guarded against the live CLI tree by design; the bench artifacts are real-run output, not self-generated expectations |
| Expected-value provenance | VALID — artifact numbers come from a real run and reconcile with the on-disk run state |
| Assertion strength | Value and behavioral level: exact strings, counts, exit codes, and filesystem residue |

## Anti-Patterns Found

None. See Advisory above for the scan result.

## Human Verification Required

None. Every behavior-dependent truth is exercised by a passing named test, by a live command run during this verification, or both. The two reliance items below are advisory by rule and are not human-verification items. No PLAN carries a deferred `<human-check>` block.

## Non-Blocking Observations

None of these falsifies a roadmap success criterion or a must-have truth as delivered, and none affects the verdict.

**Advisory reliance (Step 3c; counted as VERIFIED, advisory only)**

1. **Truth 4 (24-01) — fixture-only.** The countable `insufficient-evidence` artifact is proven by a test that hands `finalize_sweep` empty results. Through the real stage machine a physically empty corpus never reaches that writer: on a temp index built from an empty directory the baseline eval exits 1 ("Personal eval needs at least 50 indexed documents in scope; found 0", gate at `eval.py:734`, ahead of the retrieval-mode branch), and by code the `identity` stage aborts even earlier. The outcome is a loud exit 1 with `failed_stage` recorded and no artifact. No winner is fabricated and no default changes. The untested assumption is that "empty corpus" means empty evidence at the writer.
2. **Truth 19 (24-04) — undeclared precondition.** SIF's own non-TTY output is one plain line. ModelScope's own progress output is wrapped in `suppress_output()` only when `is_quiet()` is true (`download.py:487-491`), which `-q` sets via `setup_logging`. The non-TTY test replaces `ModelDownloader`, so what a real un-quieted download prints is exercised by no test and was not observed here (it needs a network download).

**Literal wording deviations (VERIFIED in substance; disclosed)**

3. **N=56 versus the measured N.** Truths 5 and 42 name "the N=56 limitation". Both committed artifacts state a limitation generated from the measured held-out N (194 at or above the 101 floor). The user-authorized amendment in `24-06-PLAN.md` says the Phase 23 N=56 wording no longer applies.
4. **No `vectors` key.** Truth 5 lists per-arm "vectors". The artifact records the count as `chunks`, with `embedded_documents` equal to `documents` (610) on every arm. The plan's own Task 2 schema and the 24-06 verify assertion enumerate keys without `vectors`.
5. **`docs/index.md` and `uvx`.** Truth 25 names a `uvx` one-off fallback for every entry point. `index.md` carries the embed and BM25-only `uv tool install` commands and points to the guide for `uvx` rather than spelling out the command. D-10 does not list `index.md` among the hand-maintained install docs, and plan 05 Task 1 scopes `index.md` to the embed-primary, BM25-only, and CPU-recipe commands, all present.

**Carried observations (pre-existing; each file unchanged since `e64c52c`)**

6. **Retired paths.** `ARTIFACT_PATH` in both runbooks (`chunk_sweep.py:57-64`, `breadcrumb_eval.py:60-67`), the citations at `docs/benchmarking.md:347,363`, and plan 06's frontmatter all name `.planning/phases/24-…`, which does not exist at HEAD. This causes the two verb MISSING results and the stale key-link targets above. A re-run would write a fresh artifact under the retired tree where the overwrite guard cannot see the archived one. Recorded as WR-04 in the prior report and open in `24-REVIEW.md`.
7. **Status never reports the home legacy tree.** `models status` always passes an explicit cache path, so `inspect_cache` sets `include_home=False` (WR-01).
8. **Model id separator.** `_split_model_id` rejects `.`, `..`, `\`, and NUL but not `:` (WR-02).
9. **Identity probe URI.** `file:{path}?mode=ro` is built without percent-encoding, so a path containing `?`, `#`, or `%` reports `no-identity` (WR-03).
10. **Local type check.** `ty check src/sif` exits 1 locally with 10 diagnostics (5 in `embedding/embedder.py`, 1 at `models/download.py:545`, 4 in `search/rerank.py`). The one line in a Phase 24 file was authored 2026-04-15. The frozen-lock CI job passes on identical source, so this is an environment difference.
11. **Evidence bookkeeping.** `docs/benchmarking.md:334` gives language totals en=137, zh=244, mixed=16 while the plan amendment records en=136, zh=244, mixed=12. The held-out N=194 agrees everywhere. Unchanged from the prior report.
12. **Load-bearing files outside the covered set.** `scripts/harrier_eval.py` (Phase 23; supplies scope keys, atomic writes, cost capture, and scratch guards to both runbooks) and `.github/workflows/test-matrix.yml` (defines the CI jobs truth 37 cites). Neither was changed by this phase. This report adds `.github/workflows/docs.yml` and `Makefile` to the covered set because success criterion 5 rests on them.

## Gaps Summary

None. All five phase requirements and all 43 plan must-have truths are delivered and verified against HEAD `be244bb`. The committed artifacts equal the recorded output of the real runs and survive the current gate policy with their keep decisions unchanged; runtime defaults remain 512/128 and `embed_breadcrumb=False`; `sif models pull`/`status` and the hidden alias behave as specified on supported inputs; every install entry point is uv-first with a clean generator diff.

The one covered file that changed since the prior report, `tests/test_ci_workflows.py`, affects no truth: its DOCS-01 guards are unchanged and still discriminating, and the module passes. Six statements in the prior report were corrected. The twelve non-blocking observations are recorded above; two are advisory reliance items and three are literal-wording deviations that previous reports passed without disclosing.

---

_Verified: 2026-11-25T02:49:17Z_
_Verifier: gsd-verifier (ZCode subagent)_
