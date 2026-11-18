---
phase: "24"
slug: "tuning-models-ux-install-docs"
verified: "2026-11-18T03:07:20Z"
verified_at: "2026-11-18T03:07:20Z"
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
covered_digest: "v4:sha256:344f80c471fc98373b8f65affb98fd8bcb0aee1ec7f42d74e401132b953d32bf"
behavior_unverified: 0
overrides_applied: 0
gaps: []
---

# Phase 24: Tuning + Models UX + Install Docs Verification Report

**Phase Goal:** Chunking defaults are evidence-gated, model management is reliable, and every platform has a correct install path — the milestone closes on measured defaults and generator-verified docs.

**Verified:** 2026-11-18T03:07:20Z
**Status:** passed
**Re-verification:** No — initial verification
**Requirements:** QUAL-02, QUAL-03, MODELS-01, MODELS-02, DOCS-01

Method: goal-backward. Every SUMMARY claim below is backed by the live file, the committed
artifact, a command run during this verification, or a passing test — not by the SUMMARY text.

## Requirement Verdicts

### QUAL-02 — Held-out-gated chunk size/overlap sweep: PASS

| Check | Evidence |
|-------|----------|
| Six-arm fixed grid including shipped 512/128, in fixed order | `src/sif/search/tuning_verdict.py:53-61` (`SWEEP_GRID` = 512/128, 512/64, 512/0, 448/112, 384/96, 256/64); `--dry-run` output lists exactly six arms in that order |
| Every arm pins modelscope Qwen3, dim 1024, max_tokens 512; only chunk knobs vary | `scripts/chunk_sweep.py:161-167` sets `SIF_MODEL_TYPE=modelscope`, `SIF_MODEL_NAME=Qwen/Qwen3-Embedding-0.6B`, `SIF_EMBEDDING_DIM=1024`, `SIF_MAX_TOKENS=512`, then `SIF_CHUNK_SIZE`/`SIF_CHUNK_OVERLAP`; dry-run confirms all six arms carry that contract |
| Per-arm persisted identity asserted after embed, before eval | `scripts/chunk_sweep.py:191-246` orders index → embed → identity → eval; `:378-455` probes, reads `read_identity`, and fails on any non-matching cache id, dimension, source, or prompt; tests `test_identity_stage_uses_the_probe_mode`, `test_probe_payload_with_harrier_identity_is_refused` pass |
| Baseline with differing fingerprint/model identity rejected and regenerated | `scripts/chunk_sweep.py:469` (`baseline_rejection_reason`), regenerated per `:750+`; `tests/unit/scripts/test_breadcrumb_eval.py:377-431` covers backend/model/fingerprint/invalid/missing baselines (shared helper) |
| Tuning selects, held-out confirms; deterministic tie-break; equal gate never adopts | `select_tuning_candidate` at `tuning_verdict.py:119-139` (rounded delta, then lower wall time, then grid order); `decide_chunk_default` at `:143-197`; tests `test_n100_epsilon_tie_keeps_default`, `test_n101_two_epsilon_win_adopts`, `test_ci_including_zero_never_adopts`, `test_equal_deltas_resolve_by_wall_time_then_grid_order` pass |
| Empty/zero-query/sub-floor evidence → insufficient, no default change, countable artifact | `tuning_verdict.py:160-179`; `scripts/chunk_sweep.py:1003-1007` writes then exits 3; tests `TestInsufficientEvidence`, `test_empty_results_are_insufficient_and_countable` pass |
| Committed artifact records per-arm cost/fingerprint/identity, no query text or absolute paths | `bench/chunk-sweep.json`: 6 arms × 610 docs/21,886 baseline chunks/embed seconds/cache deltas/identity; `min_heldout_for_epsilon_win=101`; corpus fingerprint `9ccbf4eea9263ed4`; greps for `/Users` and query text return none |
| Real six-arm run, decision keep-default | `bench/chunk-sweep.json` decision `keep-default`, selected `overlap-0` tuning +0.000737, held-out -0.008605 (CI [-0.021559, +0.003094], n=194, winner false); `docs/benchmarking.md:332-347` |
| Defaults unchanged; only the gate can change them | `src/sif/config/constants.py:19-20` still `DEFAULT_CHUNK_SIZE=512`, `DEFAULT_CHUNK_OVERLAP=128`; runtime check printed `512 128` |
| `--dry-run` full ordered plan, no subprocess; scope change invalidates markers | `python3 scripts/chunk_sweep.py --dry-run --json` exit 0, six arms, ordered stages; `scripts/chunk_sweep.py:508-529,763-767`; test `test_changed_scope_discards_prior_markers` passes |
| Overwrite guard | `scripts/chunk_sweep.py:950-980` refuses a differing decision/fingerprint without `--force`; covered by tests |

### QUAL-03 — Title-breadcrumb experiment (embed-text overlay + per-leg ablation): PASS

| Check | Evidence |
|-------|----------|
| Builder: title + latest heading, dedupe, title-only/content-only cases | `src/sif/indexing/breadcrumb.py:45-82`; 13 builder tests pass (`tests/unit/indexing/test_breadcrumb.py:22-111`) |
| Default-off Settings switch, no CLI flag | `src/sif/config/settings.py:224-228` (`embed_breadcrumb: bool = False`, env `SIF_EMBED_BREADCRUMB`); no breadcrumb Click option anywhere |
| Changes only embedding input; stored content/FTS/BM25 unchanged | `src/sif/indexing/embed_writer.py:184-191` substitutes texts only at the embed call; default-off path is exactly `[chunk.content for chunk in chunks]`; `tests/unit/indexing/test_embed_writer.py` asserts persisted chunks/FTS identical |
| Wired through `index embed` and watcher | `src/sif/cli/commands/index.py:422`, `src/sif/indexing/watcher.py:296` pass `settings.embed_breadcrumb` |
| Identity not extended; cache-key consequence documented/tested | `tests/unit/indexing/test_embed_writer.py` asserts every embedded string changes with the flag; no identity code change |
| Duplicate metrics per document, aggregated per chunk | `src/sif/indexing/breadcrumb.py:86-137` (`duplicate_metrics`); artifact records title_share 1.0, in_content_share 0.622955, subchunk_share 0.387919, title_equals_heading_share 0.026364 over 21,886 chunks/610 docs |
| Body-leg veto: title-only/flat/regressing body → keep-breadcrumb-off; absent body → insufficient | `src/sif/search/tuning_verdict.py:298-358`; tests `test_n101_overall_and_body_win_adopts`, `test_title_only_win_is_rejected`, `test_absent_body_leg_is_insufficient_evidence` pass |
| Real arm, pinned identity, baseline rejection, artifact guard | `scripts/breadcrumb_eval.py:129-150` pins `SIF_EMBED_BREADCRUMB` plus modelscope Qwen3/1024/512; `:334-354` baseline rejection; `:918-1001` guarded write; `bench/breadcrumb-verdict.json` identity `modelscope:Qwen/Qwen3-Embedding-0.6B`, dim 1024, no prompts |
| Decision keep-breadcrumb-off with numbers | Artifact decision `keep-breadcrumb-off`: overall +0.014104 (CI [-0.005664, +0.035548], winner false); title +0.048521 (winner true); body +0.006243 (winner false); `docs/benchmarking.md:349-363` |
| Default unchanged | `Settings().embed_breadcrumb is False` (runtime check); no `chunking.contract` marker code in `src/` |
| `--dry-run` full ordered single-arm plan, no subprocess | `python3 scripts/breadcrumb_eval.py --dry-run --json` exit 0, one arm, ordered `arm:index`/`arm:embed`/`arm:identity`/`arm:eval`; test `test_dry_run_invokes_no_subprocess_and_writes_no_file` passes |

### MODELS-01 — Reliable `sif models pull`: PASS

| Check | Evidence |
|-------|----------|
| Canonical cache `<Settings.get_cache_dir()>/models/<owner>/<name>` | `src/sif/models/download.py:78-84` (default root), `:97-100` (`canonical_model_dir`); `models status --json` printed `/Users/forrest/Library/Caches/sif/models/Qwen/Qwen3-Embedding-0.6B` |
| Cache hit requires manifest + per-file size + SHA-256; manifestless non-empty dir re-downloads | `download.py:126-156` (`verify_manifest`), `:446-456` (hit/force/legacy/miss order); SHA-256 only — no md5 reference anywhere in the file |
| Atomic download: sibling temp dir, verify, backup/replace, cleanup on failure | `download.py:457-490` and `_install_directory`/`_unique_sibling`; tests cover success, client failure, missing `config.json`, unverified target replacement |
| DEFAULT_MODELS = Qwen3-0.6B family with explicit revision; matches Settings | `download.py:45-65`: `Qwen/Qwen3-Embedding-0.6B`, `Qwen/Qwen3-Reranker-0.6B`, `qwen/Qwen2.5-0.5B-Instruct`, revision `master`; runtime parity check: embedding/reranker True |
| Legacy `~/.sif/models` and `owner/name___` recognized; source survives until target verifies | `download.py:265-320` (`_legacy_candidates`, `_find_legacy_model_dir`, `_adopt_legacy_model`); tests cover both layouts, ignored config-only trees, failed rename |
| `--force` bypass; missing modelscope actionable error | `download.py:446-461`; `_import_snapshot_download` at `:312-318` raises `MODELSCOPE_INSTALL_HINT` (names the embed extra) |
| `inspect_cache` states absent/empty/unverified/legacy/valid + revision, no download | `download.py:379-409`; five-state tests in `tests/unit/models/test_download.py` |
| `sif models pull` targets and errors | `src/sif/cli/commands/models.py:60-99` (resolution), `:111-126` (pull); `models pull nonsense` prints the accepted-target message |
| Docs | `docs/models.md:527+` Model Management; `docs/migration.md:52` canonical cache path and automatic migration |

### MODELS-02 — `sif models status`: PASS

| Check | Evidence |
|-------|----------|
| Reports model id/type/backend/dimension, cache path/state/revision, persisted identity with source/fingerprints | `src/sif/cli/commands/models.py:238-280` builds `settings`/`cache`/`backend`/`vector_backend`/`identity`; live `models status --json` exit 0 returned all five sections |
| Backend probe imports/downloads nothing | `models.py:105-134` uses `importlib.util.find_spec` + `importlib.metadata.version`; test `test_backend_probe_uses_find_spec_and_metadata` passes |
| Explicit states no-index/no-identity/match/mismatch/dimension-mismatch, always exit 0 | `models.py:155-221`; live run: default DB `no-identity`, absent temp DB `no-index`, exit 0 both; tests `test_no_index_reports_no_index`, `test_index_without_identity_row_reports_no_identity`, `test_matching_identity_reports_match`, `test_model_mismatch_is_reported_exit_zero`, `test_stored_dimension_mismatch`, `test_schema_width_mismatch` pass |
| Non-TTY plain `section.key: value` / JSON; Rich only on TTY | `models.py:209-218,262-278`; live piped runs produced plain lines and sorted JSON with no box drawing |
| `sif pull` hidden deprecated alias delegates; notice on stderr only | `src/sif/cli/commands/pull.py:31` `Console(stderr=True)`, `:125` `hidden=True`, `:132-141` delegation; live `--help` shows the deprecation docstring; top-level `--help` omits `pull` |
| Generator and docs tests skip hidden commands | `scripts/generate_cli_ref.py:104,120`; `docs/cli-reference.md:635-684` has `Model Commands` with `models pull`/`models status` and no `### sif pull`; `test_cli_reference_lists_models_and_hides_pull` passes |

### DOCS-01 — uv-first install + degradation + generator gate: PASS

| Check | Evidence |
|-------|----------|
| Every install entry point is uv-first | `README.md:37-78`; `docs/installation.md:33`; `docs/quickstart.md:54-73`; `docs/index.md:72-89` — `uv tool install 'docsif[embed]'` first, `uvx` fallback, pip secondary |
| Linux CPU recipe is the verified `--torch-backend=cpu` form; pyproject-index false claim gone | `docs/installation.md:33`; `README.md:44`; `tests/test_ci_workflows.py:325` guard `test_installation_docs_do_not_claim_pyproject_index_for_tool_installs` passes |
| llama-cpp wheel indexes, multi-index strategy, source build, py3.12 all-extra path | `docs/installation.md:138-186` |
| Honest degradation matrix (BM25 base, sqlite-vec CLI fail vs MCP warn, Windows daemon refusal) | `docs/installation.md:191-205`; `test_installation_doc_degradation_matrix` and `test_installation_docs_degradation_matrix` pass |
| Client snippets (Claude Desktop stdio, Claude Code HTTP, plugin) linking canonical guide | `docs/installation.md:206-253`, links `mcp-server.md` |
| Model management + migration documented | `docs/models.md:527+`; `docs/migration.md:52` |
| `make docs-generate` clean; CI diff gate exists; docs guards pass | Ran `make docs-generate` (exit 0) then `git diff --stat -- docs/` → empty; gate in `.github/workflows/docs.yml:38-43`; `pytest tests/test_docs.py tests/test_ci_workflows.py` → 66 passed |

## Plan Must-Have Truths

All 43 truths declared across the seven PLAN frontmatter files (7+3+7+7+7+6+6) are
VERIFIED by the requirement evidence above. No truth is FAILED, PRESENT_BEHAVIOR_UNVERIFIED,
or overridden. The only interpretive note: the 24-01 artifact schema records the vector
count as `chunks` (one vector per chunk), surfaced as the "Vectors" column in
`docs/benchmarking.md:336-344`, rather than a literal `vectors` key.

## Artifacts and Key Links

| Artifact | Expected | Status | Evidence |
|----------|----------|--------|----------|
| `src/sif/search/tuning_verdict.py` | pure sweep grid + gate policy | VERIFIED | 358 lines; `SWEEP_GRID`, `select_tuning_candidate`, `decide_chunk_default`, `decide_breadcrumb_default`; no Click/Rich/DB imports |
| `scripts/chunk_sweep.py` | isolated-arm runbook, dry-run, identity gate, artifact guard | VERIFIED | 1,098 lines; dry-run ran without subprocess; tests pass |
| `scripts/breadcrumb_eval.py` | one-arm runbook, per-leg gates, duplicate metrics | VERIFIED | 1,109 lines; dry-run ran; artifact written through guard |
| `src/sif/indexing/breadcrumb.py` | builder + duplicate metrics | VERIFIED | `breadcrumb_embed_texts`, `duplicate_metrics`; imported by `embed_writer.py:34` |
| `src/sif/models/download.py` | canonical cache + SHA-256 manifest + legacy migration + registry | VERIFIED | 564 lines; all entry points exercised by 52 tests |
| `src/sif/cli/commands/models.py` | `models pull`/`status` | VERIFIED | live commands work; 25 tests |
| `src/sif/cli/commands/pull.py` | hidden deprecated alias | VERIFIED | `hidden=True`; stderr-only notice; delegates |
| `scripts/generate_cli_ref.py` | hidden-command skipping | VERIFIED | lines 104, 120; generated output confirms |
| `bench/chunk-sweep.json` | six-arm evidence + decision | VERIFIED | committed in `ff74458`; 6 arms, identity, costs, min-heldout 101, limitation |
| `bench/breadcrumb-verdict.json` | breadcrumb per-leg + duplicate evidence | VERIFIED | committed in `ff74458`; legs, duplicates, identity, decision |
| `docs/benchmarking.md` | both experiment sections | VERIFIED | lines 332-363 with tables, N, gate, decisions, citations |

Key links verified: runbooks → `tuning_verdict` (deferred import + `decide_*` calls);
runbooks → `harrier_eval` helpers (`assert_within_scratch`, scope state, atomic writes);
runbooks → `personal_bench` split gates; identity stages → `sif.embedding.identity.read_identity`;
`models.py` → `ModelDownloader.download`/`inspect_cache`/`DEFAULT_MODELS`;
`models.py` → `build_settings_identity`/`read_identity`; `pull.py` → shared models handler;
`embed_writer.py` → `breadcrumb_embed_texts`; docs → generator scripts.

## Behavioral Evidence (run during this verification)

| Check | Command | Result |
|-------|---------|--------|
| Full quality suite | `env -u FORCE_COLOR NO_COLOR=1 pytest -q` | **3233 passed, 1 skipped, 95.03% coverage** in 219.24s (exit 0) |
| Phase-24 targeted suites | `pytest -q --no-cov tests/unit/search/test_tuning_verdict.py tests/unit/scripts/test_chunk_sweep.py tests/unit/indexing/test_breadcrumb.py tests/unit/scripts/test_breadcrumb_eval.py tests/unit/models/test_download.py tests/unit/cli/test_models.py tests/unit/cli/test_pull.py tests/unit/config/test_settings.py` | 268 passed in 6.82s |
| Docs/CI/index guards | `pytest -q --no-cov tests/test_docs.py tests/test_ci_workflows.py tests/unit/cli/test_index.py` | 66 passed; marker test 1 passed |
| Chunk-sweep dry run | `python3 scripts/chunk_sweep.py --dry-run --json` | exit 0; 6 ordered arms; no subprocess |
| Breadcrumb dry run | `python3 scripts/breadcrumb_eval.py --dry-run --json` | exit 0; one arm; ordered stages |
| `models` group | `python3 -m sif.cli.main models --help` | `pull` + `status` listed |
| Status non-TTY JSON | `python3 -m sif.cli.main models status --json` | exit 0; `no-identity`; full payload |
| Status non-TTY plain | `python3 -m sif.cli.main models status` | fixed-order `section.key: value` lines, no Rich |
| Hidden alias | `python3 -m sif.cli.main --help` / `... pull --help` | top-level omits `pull`; alias is invocable and hidden |
| Docs gate | `make docs-generate` + `git diff --stat -- docs/` | exit 0; empty diff |
| Lint/format/type | `ruff check src tests scripts`; `ruff format --check src tests scripts`; `ty check src/sif` | all passed (245 files formatted) |
| Registry/Settings parity | runtime Python check | embedding and reranker defaults match; chunk 512/128; breadcrumb False |

## Anti-Patterns Found

No `TBD`/`FIXME`/`XXX` markers in phase-modified files. No stub returns, empty handlers,
or hardcoded-empty rendering introduced by this phase. The committed artifacts contain no
query text, absolute paths, or secrets.

## Non-Blocking Observations

These do not violate a phase must-have and do not affect the verdict; listed with remediation
in case the maintainer wants them addressed before milestone close.

1. `bench/chunk-sweep.json` records the per-arm vector count implicitly as `chunks` (each chunk
   yields one vector) and `embedded_documents`/`cache_rows_*`; there is no literal `vectors`
   field in the JSON (the docs table derives a "Vectors" column equal to chunks).
   Remediation: add an explicit `vectors` field if literal schema compliance is desired.
2. `scripts/chunk_sweep.py --dry-run --json` and `scripts/breadcrumb_eval.py --dry-run --json`
   embed the full inherited process environment under each stage's `env`, including unrelated
   tokens from the invoking shell. Nothing is committed, but redirecting dry-run output to a
   file could leak secrets. Remediation: filter the dry-run `env` payload to arm-relevant keys.
3. `src/sif/embedding/embedder.py:468` still has a constructor default of the retired
   `iic/gte_Qwen2-7B-instruct`; the configured path always supplies Qwen3, so it is unreachable
   from Settings/factory, but the retired name survives as a default.
   Remediation: require an explicit model id or default to the Qwen3 id.
4. `24-VALIDATION.md` remains `status: draft` / `nyquist_compliant: false` and its manual-evidence
   note carries the earlier language totals (en=136/mixed=12) while the authoritative saved runs
   and `docs/benchmarking.md:334` record en=137/mixed=16. The validation audit owns the status
   field; the docs value is the correct one.

## Gaps

None. All five phase requirements (QUAL-02, QUAL-03, MODELS-01, MODELS-02, DOCS-01) are
delivered and verified against the codebase, the committed evidence artifacts, live CLI
behavior, and a green full quality suite. Both tuning experiments legitimately resolved to
keep-default / keep-breadcrumb-off through the held-out gate, so the unchanged defaults are
the phase's intended outcome, not missing work.

---

_Verified: 2026-11-18T03:07:20Z_
_Verifier: gsd-verifier (Claude)_
