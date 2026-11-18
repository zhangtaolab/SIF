---
phase: "24"
slug: "tuning-models-ux-install-docs"
verified: "2026-11-18T11:56:18Z"
verified_at: "2026-11-18T11:56:18Z"
verifier: "gsd-verifier (Claude)"
status: passed
score: "5/5 requirements; 43/43 plan must-have truths"
covered_files:
  - ".planning/phases/24-tuning-models-ux-install-docs/24-01-PLAN.md"
  - ".planning/phases/24-tuning-models-ux-install-docs/24-01-SUMMARY.md"
  - ".planning/phases/24-tuning-models-ux-install-docs/24-02-PLAN.md"
  - ".planning/phases/24-tuning-models-ux-install-docs/24-02-SUMMARY.md"
  - ".planning/phases/24-tuning-models-ux-install-docs/24-03-PLAN.md"
  - ".planning/phases/24-tuning-models-ux-install-docs/24-03-SUMMARY.md"
  - ".planning/phases/24-tuning-models-ux-install-docs/24-04-PLAN.md"
  - ".planning/phases/24-tuning-models-ux-install-docs/24-04-SUMMARY.md"
  - ".planning/phases/24-tuning-models-ux-install-docs/24-05-PLAN.md"
  - ".planning/phases/24-tuning-models-ux-install-docs/24-05-SUMMARY.md"
  - ".planning/phases/24-tuning-models-ux-install-docs/24-06-PLAN.md"
  - ".planning/phases/24-tuning-models-ux-install-docs/24-06-SUMMARY.md"
  - ".planning/phases/24-tuning-models-ux-install-docs/24-07-PLAN.md"
  - ".planning/phases/24-tuning-models-ux-install-docs/24-07-SUMMARY.md"
  - ".planning/phases/24-tuning-models-ux-install-docs/bench/breadcrumb-verdict.json"
  - ".planning/phases/24-tuning-models-ux-install-docs/bench/chunk-sweep.json"
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
covered_digest: "v4:sha256:0a9b590675fb57578eef58813390516cf91df8458489d10b7f964b52ad1610d3"
behavior_unverified: 0
overrides_applied: 0
gaps: []
re_verification:
  previous_status: passed
  previous_score: "5/5 requirements; 43/43 plan must-have truths"
  reason: "Regeneration after commit 618997c (2026-11-18) hardened the shared 1/N noise-floor gate: personal_bench._mean switched to math.fsum, a rounded strictly_above_noise_floor helper replaced the raw float comparison in both noise_gate and embedder_verdict.decide_from_gates, and one test was added. Phase 24's tuning and breadcrumb verdicts consume these gates, so the covered digest went stale. Every must-have was re-derived from the current tree (HEAD 46cb115 differs from 618997c only in .planning/STATE.md); prior claims were not carried forward."
  gaps_closed: []
  gaps_remaining: []
  regressions: []
---

# Phase 24: Tuning + Models UX + Install Docs Verification Report

**Phase Goal:** Chunking defaults are evidence-gated, model management is reliable, and every platform has a correct install path — the milestone closes on measured defaults and generator-verified docs.

**Verified:** 2026-11-18T11:56:18Z
**Status:** passed
**Re-verification:** Yes — regeneration after gate-hardening commit 618997c; every must-have re-derived from the current tree.
**Requirements:** QUAL-02, QUAL-03, MODELS-01, MODELS-02, DOCS-01

Method: goal-backward. Every claim below is backed by the live file, the committed artifact, a command run during this verification, or a passing test — not by SUMMARY text or the prior report. The regression gate was re-run in full on the current tree (3234 passed, 1 skipped, 95.03% coverage), and the committed evidence was replayed through the current gate policy.

## Delta Confirmation (commit 618997c)

Commit `618997c` — "fix(search): keep the 1/N noise floor a tie on py3.10/3.11" — changed three files:

| File | Change | Phase-24 impact |
|------|--------|-----------------|
| `src/sif/search/personal_bench.py` | `_mean` uses `math.fsum`; new `strictly_above_noise_floor(mean_delta, noise_floor)` compares `round(abs(delta), 6) > round(floor, 6)`; `noise_gate` uses it; bootstrap resample means use `fsum` | Tightens tie semantics only: a nominal 0.01 delta at its own 1/N floor is now a tie, never a win. Cannot turn a keep verdict into an adopt. |
| `src/sif/search/embedder_verdict.py` | `decide_from_gates` uses the shared `strictly_above_noise_floor` instead of a raw `abs(...) > floor` | The Phase 23 precedent this phase's policy mirrors; same conservative direction. |
| `tests/unit/search/test_personal_bench.py` | Added `test_float_accumulated_epsilon_tie_never_wins` | Passing (see behavioral evidence). |

`git diff --stat 618997c..HEAD` shows only `.planning/STATE.md`; the code tree verified here is identical to the CI-verified commit. The Phase-24 artifacts and policy were replayed through the current code rather than assumed:

| Replay | Current-code result | Committed artifact |
|--------|--------------------|--------------------|
| `decide_chunk_default(selected_arm="overlap-0", tuning_mean_delta=0.000737…, confirmation)` | `keep-default` — reasons: held-out winner false; held-out mean delta −0.008605 is below 0.01 | `decision: keep-default` |
| `decide_breadcrumb_default(confirmation, legs, duplicates)` | `keep-breadcrumb-off` — reason: overall held-out gate winner is false; body winner false, body sufficient true, title winner true | `decision: keep-breadcrumb-off` |

Both committed verdicts remain exactly what the current gate policy produces. The full suite at the current tree is **3234 passed / 1 skipped / 95.03% coverage** (exit 0), and GitHub Actions at 618997c is green: Test Matrix (8 cells: py3.10–3.13 × ubuntu/macos) plus the lint job whose `uv run --frozen ty check src/sif` step succeeded. Docs Validation also succeeded.

## Requirement Verdicts

### QUAL-02 — Held-out-gated chunk size/overlap sweep: PASS

| Check | Evidence |
|-------|----------|
| Six-arm fixed grid including shipped 512/128, in fixed order | `src/sif/search/tuning_verdict.py` `SWEEP_GRID` = 512/128, 512/64, 512/0, 448/112, 384/96, 256/64; live `--dry-run --json` printed the same six arms in order |
| Every arm pins modelscope Qwen3, dim 1024, max_tokens 512; only chunk knobs vary | `scripts/chunk_sweep.py:161-167` env pins; live dry run `expected_identity` = modelscope:Qwen/Qwen3-Embedding-0.6B, dimension 1024, null prompts, `max_tokens: 512` |
| Per-arm persisted identity asserted after embed, before eval; baseline identity mismatch rejected | Stage order `STAGE_SUFFIXES = ("index", "embed", "identity", "eval")`; `test_identity_stage_uses_the_probe_mode`, `test_valid_identity_passes`, and the baseline rejection tests (`test_sentence_transformers_backend_is_rejected`, `test_different_model_name_is_rejected`, `test_fingerprint_mismatch_is_rejected`, `test_missing_saved_run_is_rejected`, `test_unreadable_saved_run_is_rejected`) pass |
| Tuning selects, held-out confirms; deterministic tie-break; equal gate never adopts | `select_tuning_candidate` / `decide_chunk_default`; `test_n100_epsilon_tie_keeps_default`, `test_n101_two_epsilon_win_adopts`, `test_ci_including_zero_never_adopts`, `test_equal_deltas_resolve_by_wall_time_then_grid_order` pass |
| Empty/zero-query/sub-floor evidence → insufficient, no default change, countable artifact | `test_empty_confirmation_is_insufficient`, `test_missing_candidate_is_insufficient`, `test_below_sufficiency_floor_is_insufficient`, `test_no_positive_candidate_returns_none` pass |
| Committed artifact records per-arm costs, fingerprint, min-heldout, limitation, no query text or absolute paths | `bench/chunk-sweep.json`: 6 arms each with documents/chunks/embedded_documents/embed_wall_seconds/cache_rows_before/after/cache_hits, identity block; `corpus_fingerprint 9ccbf4eea9263ed4`, `min_heldout_for_epsilon_win: 101`, measured-N limitation; `grep -c "/Users"` = 0 |
| Real six-arm run, decision keep-default | artifact `decision: keep-default`; confirmation mean_delta −0.008605, CI [−0.021559, +0.003094], n 194, winner false; documented at `docs/benchmarking.md:334-347` |
| Defaults unchanged; only the gate can change them | live imports printed `DEFAULT_CHUNK_SIZE=512`, `DEFAULT_CHUNK_OVERLAP=128` (`src/sif/config/constants.py:19-20`) |
| `--dry-run` full ordered plan, no subprocess; overwrite guard | `python3 scripts/chunk_sweep.py --dry-run --json` exit 0 with all six arm plans; `test_dry_run_json_invokes_no_subprocess`, `test_force_replaces_a_different_run` pass |

### QUAL-03 — Title-breadcrumb experiment (embed-text overlay + per-leg ablation): PASS

| Check | Evidence |
|-------|----------|
| Builder: title + latest heading, dedupe, title-only/content-only cases | `src/sif/indexing/breadcrumb.py` `breadcrumb_embed_texts`; 20 builder/metric tests pass (`tests/unit/indexing/test_breadcrumb.py`) |
| Default-off Settings switch, no CLI flag | `src/sif/config/settings.py:224` (`embed_breadcrumb`, env `SIF_EMBED_BREADCRUMB`); runtime check printed `False`; the only CLI reference is the pass-through at `src/sif/cli/commands/index.py:422` — no Click option exists |
| Changes only embedding input; stored content/FTS/BM25 unchanged | `src/sif/indexing/embed_writer.py:190` substitutes texts only at the embed call; default-off path is exactly `[chunk.content for chunk in chunks]`; `tests/unit/indexing/test_embed_writer.py` passes |
| Wired through `index embed` and watcher | `src/sif/cli/commands/index.py:422`, `src/sif/indexing/watcher.py:296` |
| Identity not extended; cache-key consequence covered | no identity change; embed-writer tests assert every embedded string changes with the flag |
| Duplicate metrics per document, aggregated per chunk | `duplicate_metrics`; artifact records title_share 1.0, in_content_share 0.622955, subchunk_share 0.387919, title_equals_heading_share 0.026364 over 21,886 chunks/610 docs |
| Body-leg veto: title-only/flat/regressing body → keep; absent body → insufficient | `decide_breadcrumb_default`; `test_overall_winner_with_a_flat_body_leg_is_title_leg_only`, `test_regressing_body_leg_is_rejected_with_numbers`, `test_absent_body_leg_is_insufficient_evidence` pass |
| Real arm, pinned identity, baseline rejection, artifact guard | `scripts/breadcrumb_eval.py`; dry run shows one arm with `embed_breadcrumb: true`, identity modelscope Qwen3/1024/512; baseline mismatch tests pass; `bench/breadcrumb-verdict.json` identity `modelscope:Qwen/Qwen3-Embedding-0.6B`, no absolute paths |
| Decision keep-breadcrumb-off with numbers | artifact `decision: keep-breadcrumb-off`, overall mean +0.014104 CI [−0.005664, +0.035548] winner false; title leg winner true, body leg winner false; `docs/benchmarking.md:349-363` |
| Default unchanged | runtime `Settings().embed_breadcrumb is False`; no `chunking.contract` marker code in `src/` |
| `--dry-run` single ordered arm, no subprocess | `python3 scripts/breadcrumb_eval.py --dry-run --json` exit 0; stages `arm:index → arm:embed → arm:identity → arm:eval` |

### MODELS-01 — Reliable `sif models pull`: PASS

| Check | Evidence |
|-------|----------|
| Canonical cache `<Settings.get_cache_dir()>/models/<owner>/<name>` | `src/sif/models/download.py` `canonical_model_dir` + default root; live `models status --json` printed `/Users/forrest/Library/Caches/sif/models/Qwen/Qwen3-Embedding-0.6B`, state `absent`, exit 0, no download |
| Cache hit requires manifest + per-file size + SHA-256; manifestless re-downloads | `verify_manifest` + SHA-256 helpers; no md5 in the file; `test_valid_manifest_returns_without_downloading`, `test_empty_directory_is_not_a_hit`, `test_nonempty_directory_without_manifest_is_not_a_hit`, `test_size_mismatch_is_not_a_hit`, `test_hash_mismatch_is_not_a_hit` pass |
| Atomic download: sibling temp, verify, backup/replace, cleanup | `test_success_leaves_no_temporary_or_backup_directories`, `test_replaces_unverified_target_and_removes_backup`, `test_client_failure_leaves_no_target_or_scratch_directory`, `test_missing_config_json_fails_and_cleans_up` pass |
| DEFAULT_MODELS = Qwen3-0.6B family with explicit revision; matches Settings | live registry print: embedding `Qwen/Qwen3-Embedding-0.6B`, reranker `Qwen/Qwen3-Reranker-0.6B`, query expansion `qwen/Qwen2.5-0.5B-Instruct`, revision `master`; `Settings().model_name` equals the embedding entry; `test_registry_matches_shipped_settings_defaults`, `test_registry_pins_master_revision_for_every_entry` pass |
| Legacy layouts recognized; source survives until target verifies | `_legacy_candidates`/`_adopt_legacy_model`; migration, explicit-root, failed-rename, and ignored-legacy tests pass |
| `--force` bypass; missing modelscope actionable error | `test_force_redownloads_despite_valid_manifest`, `test_missing_modelscope_raises_actionable_import_error` pass |
| `inspect_cache` five states + revision, no download | `test_reports_all_states_without_importing_modelscope`, `test_inspect_reports_legacy_then_valid` pass; live status reported `absent` without downloading |

### MODELS-02 — `sif models status`: PASS

| Check | Evidence |
|-------|----------|
| Reports model id/type/backend/dimension, cache path/state/revision, persisted identity | live `models status --json` (exit 0): sections `settings`, `cache`, `backend`, `vector_backend`, `identity`; plain run prints fixed-order `settings.model_type: modelscope`, `settings.dimension: 1024`, `cache.path`, `cache.state: absent`, `backend.available: True` |
| Backend probe imports/downloads nothing | `importlib.util.find_spec` + `importlib.metadata.version`; `test_backend_probe_uses_find_spec_and_metadata` passes |
| Explicit states, always exit 0 | `test_no_index_reports_no_index`, `test_index_without_identity_row_reports_no_identity`, `test_matching_identity_reports_match`, `test_model_mismatch_is_reported_exit_zero`, `test_stored_dimension_mismatch`, `test_schema_width_mismatch`, `test_corrupt_identity_row_degrades_without_traceback` pass |
| Non-TTY plain lines / JSON; Rich only on TTY | live piped runs produced plain `section.key: value` lines and sorted JSON, no box drawing; `test_non_tty_output_is_plain_and_ordered`, `test_tty_renders_table` pass |
| `sif pull` hidden deprecated alias delegates; stderr-only notice | live top-level `--help` omits `pull`; `pull --help` says "deprecated: use 'sif models pull'"; `src/sif/cli/commands/pull.py:125` `hidden=True`; `tests/unit/cli/test_pull.py` passes |
| Generator and docs tests skip hidden commands | `scripts/generate_cli_ref.py:104,120`; `docs/cli-reference.md` lists `models pull`/`models status`, no `### sif pull`; docs test passes |

### DOCS-01 — uv-first install + degradation + generator gate: PASS

| Check | Evidence |
|-------|----------|
| Every install entry point is uv-first | `README.md:37-78`; `docs/installation.md:17-60` (Method 1 uv tool, Method 2 uvx, pip is Method 3); `docs/quickstart.md:31-73`; `docs/index.md:72-89` |
| Linux CPU recipe is `--torch-backend=cpu`; pyproject-index claim gone | `docs/installation.md:33,50`; `README.md:44,48,53`; `grep pyproject docs/installation.md` = no hits |
| llama-cpp wheel indexes, multi-index strategy, source build, py3.12 all-extra path | `docs/installation.md:138-148` CPU/CUDA 12.1/Metal index table + resolver guidance; py3.12 `docsif[all]` at `docs/quickstart.md:33` and `docs/index.md:85` |
| Honest degradation matrix | `docs/installation.md:191-203`: BM25-only base; missing sqlite-vec → CLI vector/hybrid raise the vector-store error while MCP `hybrid_search` degrades to BM25 with one warning; Windows daemon/service refused, foreground watch/MCP run |
| Client snippets linking canonical guide | `docs/installation.md:208` links `mcp-server.md`; Desktop stdio, Claude Code HTTP, plugin snippets follow |
| Model management + migration documented | `docs/models.md:527` Model Management (pull/status, cache states, manifest, legacy, no ST prewarm); `docs/migration.md:52` canonical cache path, automatic legacy migration, hidden alias note |
| `make docs-generate` clean; CI diff gate; docs guards pass | `make docs-generate` exit 0 with empty `git diff --stat -- docs/ README.md` (run this verification); gate in `.github/workflows/docs.yml`; `tests/test_docs.py` + `tests/test_ci_workflows.py` pass |
| Expected-output banner matches shipped version | `docs/installation.md:325` says `sif, version 1.2.0`; live `python3 -m sif.cli.main --version` printed `sif, version 1.2.0` |
| Retired model name absent from docs | `grep -E "gte_Qwen2-7B|iic/gte" docs/*.md README.md` = no hits |

## Plan Must-Have Truths

All 43 truths declared across the seven PLAN frontmatter files (7+3+7+7+7+6+6) are VERIFIED on the current tree. No truth is FAILED, PRESENT_BEHAVIOR_UNVERIFIED, or overridden.

| # | Plan | Truth (short) | Status | Evidence |
|---|------|---------------|--------|----------|
| 1 | 24-01 | Six-arm fixed grid, shipped default, Qwen3 pins, only chunk knobs vary | ✓ VERIFIED | `SWEEP_GRID`; dry-run identity/grid |
| 2 | 24-01 | Persisted identity asserted after embed before eval; mismatched baseline rejected/regenerated | ✓ VERIFIED | `STAGE_SUFFIXES`; named tests |
| 3 | 24-01 | Tuning-select then held-out confirm; deterministic tie-break; equal gate never adopts | ✓ VERIFIED | policy + boundary tests |
| 4 | 24-01 | Empty/zero/sub-floor evidence → insufficient, no default change, countable artifact | ✓ VERIFIED | insufficient tests; artifact schema |
| 5 | 24-01 | Artifact records per-arm costs, fingerprint, min-heldout, limitation, no query text/paths | ✓ VERIFIED | artifact re-inspected; privacy grep 0 (see note 1) |
| 6 | 24-01 | `--dry-run` full ordered plan, no subprocess; scope change invalidates markers | ✓ VERIFIED | live dry run; `test_changed_scope_discards_prior_markers` |
| 7 | 24-01 | Artifact overwrite guard refuses differing decision/fingerprint without `--force` | ✓ VERIFIED | guard code + `test_force_replaces_a_different_run` |
| 8 | 24-02 | Builder title+heading dedupe; stored content/FTS/BM25 byte-identical | ✓ VERIFIED | 20 tests; writer overlay |
| 9 | 24-02 | `embed_breadcrumb: bool = False` (env), no CLI flag; default-off byte-identical | ✓ VERIFIED | Settings; runtime False; no Click option |
| 10 | 24-02 | Only embedding input changes; cache key changes; isolated DB + `--force`; identity not extended | ✓ VERIFIED | embed_writer tests; runbook arm |
| 11 | 24-03 | Canonical cache path; explicit cache_dir honored | ✓ VERIFIED | code; live status path; tests |
| 12 | 24-03 | Cache hit requires manifest + size + SHA-256; manifestless re-downloads | ✓ VERIFIED | `verify_manifest`; state tests |
| 13 | 24-03 | Atomic sibling temp download, verify, replace; no partial/leftovers | ✓ VERIFIED | atomic-install tests |
| 14 | 24-03 | DEFAULT_MODELS Qwen3 family with explicit revision; matches Settings | ✓ VERIFIED | live parity check; registry tests |
| 15 | 24-03 | Legacy layouts recognized/migrated; source survives until target verifies | ✓ VERIFIED | legacy tests |
| 16 | 24-03 | `--force` bypass; missing modelscope actionable error naming the embed extra | ✓ VERIFIED | `MODELSCOPE_INSTALL_HINT`; tests |
| 17 | 24-03 | `inspect_cache` five states + revision, no download | ✓ VERIFIED | state tests; live absent status |
| 18 | 24-04 | `models pull` with no arg / family entry / owner-name variants | ✓ VERIFIED | help + target-resolution tests |
| 19 | 24-04 | `--force` bypass; non-interactive; failures are actionable ClickException | ✓ VERIFIED | tests `test_force_is_forwarded`, `test_missing_modelscope_becomes_click_exception` |
| 20 | 24-04 | Status reports configured/cache/identity/backend, probe imports/downloads nothing | ✓ VERIFIED | live JSON/plain runs; probe test |
| 21 | 24-04 | Five explicit status states, mismatch reported, exit 0 | ✓ VERIFIED | six state tests |
| 22 | 24-04 | Non-TTY plain/JSON; Rich only on TTY | ✓ VERIFIED | live piped output; TTY test |
| 23 | 24-04 | Hidden deprecated alias delegates; deprecation notice stderr-only | ✓ VERIFIED | live help; `hidden=True`; pull tests |
| 24 | 24-04 | Generator/tests skip hidden commands | ✓ VERIFIED | generator source; generated CLI ref |
| 25 | 24-05 | Every install entry point leads with uv; pip secondary | ✓ VERIFIED | README + three docs |
| 26 | 24-05 | Linux CPU `--torch-backend=cpu` recipe; pyproject-index claim removed | ✓ VERIFIED | docs; no pyproject hits |
| 27 | 24-05 | llama-cpp wheel indexes, multi-index, source build, py3.12 all path | ✓ VERIFIED | installation.md table; quickstart/index py3.12 |
| 28 | 24-05 | Honest degradation matrix | ✓ VERIFIED | installation.md matrix matches behavior |
| 29 | 24-05 | Client snippets link canonical MCP guide | ✓ VERIFIED | installation.md links mcp-server.md |
| 30 | 24-05 | models.md Model Management; migration.md canonical cache path | ✓ VERIFIED | sections present |
| 31 | 24-05 | docs-generate clean; docs guards | ✓ VERIFIED | live generator run; docs tests |
| 32 | 24-06 | Real six-arm artifact with per-arm costs, selection, confirmation, measured N, limitation | ✓ VERIFIED | chunk-sweep.json re-inspected |
| 33 | 24-06 | Real breadcrumb artifact with overall/leg gates, duplicates, measured N | ✓ VERIFIED | breadcrumb-verdict.json re-inspected |
| 34 | 24-06 | Defaults change only when the artifact decision authorizes | ✓ VERIFIED | both decisions keep; defaults unchanged |
| 35 | 24-06 | Marker code only on a flip; test asserts presence/absence through the real embed path | ✓ VERIFIED | no marker in `src/`; `test_embed_writes_chunking_contract_marker_iff_contract_flipped` passes |
| 36 | 24-06 | benchmarking.md records both experiments with tables, fingerprint, adequacy, verdict numbers | ✓ VERIFIED | sections at :332-363 |
| 37 | 24-06 | Full suite, docs gate, type check green after applied change | ✓ VERIFIED | live full suite 3234/1 @95.03%; docs-generate clean; CI type-check step green (see note 5) |
| 38 | 24-07 | Duplicate metrics per document aggregated per chunk | ✓ VERIFIED | `duplicate_metrics`; artifact shares; tests |
| 39 | 24-07 | Body-leg veto: title-only/flat/regressing body rejected; absent body insufficient | ✓ VERIFIED | policy tests |
| 40 | 24-07 | Runbook pins identity, asserts after embed before eval, records model_type + identity | ✓ VERIFIED | artifact identity; stage order; identity tests |
| 41 | 24-07 | Baseline identity mismatch rejected/regenerated on the same backend | ✓ VERIFIED | four baseline rejection tests |
| 42 | 24-07 | Artifact aggregate-only, min-heldout 101, N limitation, overwrite guard | ✓ VERIFIED | artifact; guarded write (see note 2) |
| 43 | 24-07 | `--dry-run` single ordered arm, no subprocess | ✓ VERIFIED | live dry run; dry-run test |

Interpretive notes (unchanged from the prior pass, re-confirmed):
1. The 24-01 artifact records the per-arm vector count through `chunks` (one vector per chunk) plus the cache-row deltas; no literal `vectors` key exists. `docs/benchmarking.md` derives its "Vectors" column from the same equality.
2. The 24-01/24-07 "N=56 limitation" wording was explicitly superseded by the in-plan, user-authorized corpus amendment recorded at `24-06-PLAN.md:116` ("the Phase 23 `N=56` wording no longer applies"), and the runbooks now generate the limitation from the measured held-out N. The committed artifacts record N=194, which is the correct current contract; the N=56 branch remains covered by `TestLimitation`.

## Artifacts and Key Links

Structured verification (`gsd-tools query verify.artifacts` / `verify.key-links`) over all seven plans: **29/29 artifacts passed, 20/20 key links verified**.

| Artifact | Expected | Status | Evidence |
|----------|----------|--------|----------|
| `src/sif/search/tuning_verdict.py` | pure sweep grid + gate policy | VERIFIED | `SWEEP_GRID`, `MIN_HELDOUT_FOR_EPSILON_WIN`, `select_tuning_candidate`, `decide_chunk_default`, `decide_breadcrumb_default`; imported and exercised by the runbooks |
| `scripts/chunk_sweep.py` | isolated-arm runbook | VERIFIED | 6-arm dry run live; artifact replay |
| `scripts/breadcrumb_eval.py` | one-arm runbook | VERIFIED | single-arm dry run live; artifact replay |
| `src/sif/indexing/breadcrumb.py` | builder + duplicate metrics | VERIFIED | imported by `embed_writer.py`; used by the runbook |
| `src/sif/models/download.py` | canonical cache + SHA-256 + legacy + registry | VERIFIED | tests + live status |
| `src/sif/cli/commands/models.py` | `models pull`/`status` | VERIFIED | live commands |
| `src/sif/cli/commands/pull.py` | hidden deprecated alias | VERIFIED | live help; delegates |
| `scripts/generate_cli_ref.py` | hidden-command skipping | VERIFIED | generated CLI reference |
| `bench/chunk-sweep.json` | six-arm evidence + decision | VERIFIED | keep-default, N=194, fingerprint, identity |
| `bench/breadcrumb-verdict.json` | breadcrumb per-leg + duplicate evidence | VERIFIED | keep-breadcrumb-off, legs, duplicates |
| `docs/benchmarking.md` | both experiment sections | VERIFIED | :332-363 |

Key links verified: runbooks → `tuning_verdict` (`decide_*` calls); runbooks → `harrier_eval` helpers (`assert_within_scratch`, scope state, atomic writes); runbooks → `personal_bench` split gates; identity stages → `read_identity`; `models.py` → `ModelDownloader` + `inspect_cache`; `models.py` → `build_settings_identity`/`read_identity`; `pull.py` → shared models handler; `embed_writer.py` → `breadcrumb_embed_texts`; `index.py:422`/`watcher.py:296` → `settings.embed_breadcrumb`; docs → generator scripts.

## Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|--------------------|--------|
| `bench/chunk-sweep.json` | per-arm costs/decision | Real six-arm run over 610 documents, written through the guard | Yes | ✓ FLOWING |
| `bench/breadcrumb-verdict.json` | overall/leg gates/duplicates | Real breadcrumb arm over the same corpus; identity asserted | Yes | ✓ FLOWING |
| `models status` | settings/cache/identity | Live `Settings`, filesystem cache inspection, `index_meta` | Yes | ✓ FLOWING |
| `docs/benchmarking.md` tables | verdict numbers | Committed artifacts (same values re-checked) | Yes | ✓ FLOWING |
| `docs/cli-reference.md` / `docs/configuration.md` | command/field listings | Generator scripts from live Click/Pydantic definitions | Yes | ✓ FLOWING |

## Behavioral Evidence (run during this verification)

| Check | Command | Result |
|-------|---------|--------|
| Phase-24 targeted suites | `pytest -q --no-cov` over 14 phase test files | **589 passed in 22.44s** |
| Delta gate regression | `pytest -q --no-cov tests/unit/search/test_personal_bench.py::TestNoiseGate::test_float_accumulated_epsilon_tie_never_wins` | **1 passed** |
| Full quality suite | `pytest -q` (current tree, HEAD) | **3234 passed, 1 skipped, 95.03% coverage, exit 0** |
| Ruff lint / format | `ruff check src tests` / `ruff format --check src tests` | All checks passed; 236 files already formatted |
| Docs generator gate | `make docs-generate` + `git diff --stat -- docs/ README.md` | exit 0; empty diff |
| Chunk-sweep dry run | `python3 scripts/chunk_sweep.py --dry-run --json` | exit 0; 6 arms in grid order; pinned identity; no subprocess |
| Breadcrumb dry run | `python3 scripts/breadcrumb_eval.py --dry-run --json` | exit 0; one arm (`embed_breadcrumb: true`); stages index→embed→identity→eval |
| Artifact replay | current `decide_chunk_default` / `decide_breadcrumb_default` on committed gates | `keep-default` / `keep-breadcrumb-off` |
| Version banner | `python3 -m sif.cli.main --version` | `sif, version 1.2.0` |
| `models` group / hidden alias | `models --help`, `models pull --help`, top-level `--help`, `pull --help` | pull+status listed; top-level omits pull; alias says deprecated |
| Status non-TTY JSON / plain | `models status --json` / `models status` | exit 0; five sections; fixed-order plain lines, no Rich |
| Runtime parity | Python imports of constants, `Settings`, `DEFAULT_MODELS` | chunk 512/128; `embed_breadcrumb: False`; Settings model = registry embedding entry |
| Privacy grep | `grep -c "/Users" bench/*.json` | 0 in both artifacts |
| CI at 618997c | `gh run view 44286606274` | Test Matrix success: 8/8 cells + lint/type-check job; Docs Validation success |
| Decision coverage | `gsd-tools query check.decision-coverage-verify` | 12/12 trackable CONTEXT.md decisions honored (non-blocking gate) |

## Requirements Coverage

| Requirement | Source Plans | REQUIREMENTS.md | Status | Evidence |
|-------------|--------------|-----------------|--------|----------|
| QUAL-02 | 24-01, 24-06 | line 28, mapped Phase 24 | SATISFIED | sweep instrument + real run + keep-default verdict |
| QUAL-03 | 24-02, 24-06, 24-07 | line 29, mapped Phase 24 | SATISFIED | breadcrumb contract + evaluation layer + keep-breadcrumb-off verdict |
| MODELS-01 | 24-03, 24-04 | line 78, mapped Phase 24 | SATISFIED | canonical manifest cache + `sif models pull` |
| MODELS-02 | 24-04 | line 79, mapped Phase 24 | SATISFIED | `sif models status` + hidden alias + generator skip |
| DOCS-01 | 24-05 | line 83, mapped Phase 24 | SATISFIED | uv-first docs + degradation matrix + generator gate at 1.2.0 |

No orphaned requirements: REQUIREMENTS.md maps exactly these five IDs to Phase 24, and the seven plans declare exactly these five IDs (24-01/06: QUAL-02; 24-02/06/07: QUAL-03; 24-03/04: MODELS-01; 24-04: MODELS-02; 24-05: DOCS-01).

## Anti-Patterns Found

None. No `TBD`/`FIXME`/`XXX`/`TODO`/`HACK`/`PLACEHOLDER` markers in the phase's key files (tuning_verdict, personal_bench, embedder_verdict, breadcrumb, embed_writer, download, models, pull, chunk_sweep, breadcrumb_eval, generate_cli_ref, constants). The `placeholders` variables in `personal_bench.py` are SQL bind-parameter builders, not stub markers. The eight `return None` sites in `download.py` are legitimate not-found/optional-metadata returns in cache inspection and legacy detection, covered by tests. No hardcoded-empty rendering; artifacts contain no query text or absolute paths.

## Human Verification Required

None. Every behavior-dependent truth (gate-policy boundaries, identity assertion ordering, cache-state machine, atomic install, status states, generator guards) is exercised by a passing named test in the 589-test targeted run or the 3234-test full run, and the real-run truths are evidenced by the committed artifacts and `docs/benchmarking.md`. The install recipes (`--torch-backend=cpu`, llama-cpp wheel indexes) are documented in-repo as hand-verified steps with VERIFY comments, exactly as the plan's declared assumption requires.

## Gaps Summary

None. All five phase requirements are delivered and verified against the current tree: the committed artifacts survive the 618997c gate hardening with their keep-default / keep-breadcrumb-off decisions unchanged, the runtime defaults remain 512/128 and `embed_breadcrumb=False`, model pull/status work and report honestly, and every install entry point is uv-first with a clean generator diff. The current-tree full suite is green (3234 passed / 1 skipped @ 95.03% coverage), and CI at 618997c passed all eight matrix cells plus the lint/type-check job.

## Non-Blocking Observations

These do not violate a phase must-have and do not affect the verdict.

1. `bench/chunk-sweep.json` records the per-arm vector count implicitly as `chunks` (each chunk yields one vector); no literal `vectors` field exists. Remediation: add an explicit `vectors` field if literal schema compliance is desired.
2. The `--dry-run --json` breadcrumb payload embeds the full inherited process environment under `env` (108 keys this run, including auth/API-token variable names). Nothing is committed, but redirecting dry-run output to a file could leak secrets. Remediation: filter the dry-run `env` payload to arm-relevant keys.
3. `src/sif/embedding/embedder.py:468` retains a constructor default of the retired `iic/gte_Qwen2-7B-instruct`; unreachable from Settings/factory (Settings always supplies Qwen3), but the retired name survives as a default. Remediation: require an explicit model id or default to the Qwen3 id.
4. `24-VALIDATION.md` remains `status: draft` / `nyquist_compliant: false`; the validation audit owns that status field. The `24-06-PLAN.md` assumption still carries the earlier adequacy totals (en=136/mixed=12) while the authoritative saved runs and `docs/benchmarking.md:334` record en=137/zh=244/mixed=16 (re-confirmed this run).
5. `ty check src/sif` exits 1 in the local Python 3.10/numpy 2.2.6 environment on a pre-existing diagnostic in `src/sif/embedding/embedder.py:842` (a numpy-typed return in code untouched since before Phase 24; `git diff 77c86b8..HEAD -- embedder.py` is empty). CI's canonical lint environment (py3.12, `uv run --frozen ty check src/sif`) passed the Type check step at 618997c. Not introduced by this phase; recorded for transparency.

---

_Verified: 2026-11-18T11:56:18Z_
_Verifier: gsd-verifier (Claude)_
