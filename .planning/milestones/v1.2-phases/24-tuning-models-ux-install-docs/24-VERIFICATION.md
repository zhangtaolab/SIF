---
phase: "24"
slug: "tuning-models-ux-install-docs"
verified: "2026-11-24T02:19:28Z"
verified_at: "2026-11-24T02:19:28Z"
verifier: "gsd-verifier (Claude)"
status: passed
score: "5/5 requirements; 43/43 plan must-have truths"
covered_files:
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
covered_digest: "v4:sha256:7b6de1a5e3ce20be4af13c9d7b58d74c43141cd8d63e450cbb8545890f1084ae"
behavior_unverified: 0
overrides_applied: 0
gaps: []
re_verification:
  previous_status: passed
  previous_score: "5/5 requirements; 43/43 plan must-have truths"
  reason: "Regeneration after 48 commits since the previously verified tree (46cb115): four covered inputs changed (docs/configuration.md, docs/installation.md, tests/test_ci_workflows.py, tests/test_docs.py), src/sif/models/download.py gained the pre-fix <cache>/<owner>/<name> adoption, phase artifacts were archived under .planning/milestones/v1.2-phases/, and 24-VALIDATION.md, 24-SECURITY.md, 24-UI-REVIEW.md, 24-REVIEW.md plus 24-REVIEW-DISPOSITION.md were added. Every must-have was re-derived from HEAD 462266e; prior claims were not carried forward."
  gaps_closed: []
  gaps_remaining: []
  regressions: []
---

# Phase 24: Tuning + Models UX + Install Docs Verification Report

**Phase Goal:** Chunking defaults are evidence-gated, model management is reliable, and every platform has a correct install path — the milestone closes on measured defaults and generator-verified docs.

**Verified:** 2026-11-24T02:19:28Z (HEAD `462266e`, branch `gsd/phase-24-reverify`)
**Status:** passed
**Re-verification:** Yes — stale-input regeneration; every must-have re-derived from the current tree.
**Requirements:** QUAL-02, QUAL-03, MODELS-01, MODELS-02, DOCS-01

Method: goal-backward against the archived ROADMAP success criteria (5) and the seven PLAN `must_haves` (43 truths). Every claim below rests on a live file at HEAD, a command run during this verification, or a passing test — not on SUMMARY text or the prior report. No product source, test, or default was modified; nothing was fixed.

## Post-Verification Delta (46cb115..462266e) and Requirement Impact

The prior report verified at `46cb115`. `git diff --stat 46cb115..HEAD` shows 48 commits. The four covered files that went stale, and what changed:

| File | Change | Requirement impact |
|------|--------|--------------------|
| `docs/installation.md` | Backend matrix added (`--torch-backend=auto` for Linux NVIDIA, `--torch-backend=cpu` for Linux CPU, no flag on macOS); "do not pass `--torch-backend=cpu` on macOS" note; `torch>=2.11` floor with 2.14 recommendation; Intel-XPU device prose; version banner raised 1.2.0 → 1.2.3 | **None adverse — strengthens DOCS-01.** uv-first order preserved (`installation.md:17` Method 1, uvx Method 2, pip Method 3); the required Linux CPU `--torch-backend=cpu` recipe and pip CPU index remain; `grep -c pyproject` = 0; llama-cpp wheel-index table (`:167-169`), source builds, and the Python 3.12 `all` path (`:202-206`) intact; degradation matrix now at `:212-225`; client snippets at `:227-274`; banner matches live `sif --version` = 1.2.3 |
| `docs/configuration.md` | Device-selection row now names Intel XPU; XPU-build caveat added | **None.** Generated file; `make docs-generate` reproduced it byte-identically (exit 0, empty `git diff --stat -- docs/ README.md`) |
| `tests/test_ci_workflows.py` | Matrix guard 8 → 6 cells with explicit macOS exclusions; push trigger pinned to `[main]`; torch floor assertion `torch>=2.11`; extra install-doc guards (`auto`, CUDA index, macOS note) | **None adverse — strengthens DOCS-01.** Suite passes |
| `tests/test_docs.py` | uv-first guard now also requires `--torch-backend=auto`; new macOS no-CPU-backend guard; `docs/machine-migration.md` added to the doc inventory | **None adverse — strengthens DOCS-01.** Suite passes |

Other post-verification source change relevant to a Phase-24 artifact: `src/sif/models/download.py` (+21/−4) widens legacy adoption to the pre-fix `<cache>/<owner>/<name>` layout. MODELS-01 truth 5 ("legacy layouts recognized and migrated … source survives until the target verifies") still holds and is now broader; the model tests pass. Remaining source deltas (embedder XPU/renormalization, collection/ls, rerank) are Phase-21/23-era quick-task work and touch no Phase-24 deliverable or default.

## Goal Achievement

### Roadmap Success Criteria

| # | Success Criterion | Status | Evidence |
|---|-------------------|--------|----------|
| 1 | Held-out-gated chunk size/overlap sweep; per-arm re-chunk + re-embed on isolated arms; embed cost reported; defaults change only via the gate | ✓ VERIFIED | `SWEEP_GRID` six arms; live `--dry-run --json` shows only chunk knobs varying and pinned modelscope Qwen3/1024/512; committed artifact `decision: keep-default`; current policy replay on committed gates still yields `keep-default`; `DEFAULT_CHUNK_SIZE=512`, `DEFAULT_CHUNK_OVERLAP=128` unchanged |
| 2 | Title-breadcrumb experiment; per-leg ablation; title-signal duplication checked against Phase 19 title FTS; defaults change only via the gate | ✓ VERIFIED | `decide_breadcrumb_default` body-leg veto; artifact records overall/title/body gates plus duplicate shares (title_share 1.0, in_content_share 0.622955); decision `keep-breadcrumb-off`; replay on current code matches; `Settings().embed_breadcrumb is False` by default |
| 3 | `sif models pull` reliable; DEFAULT_MODELS Qwen3-0.6B family; SHA-256 cache check (no md5); deterministic ModelScope path; canonical cache dir | ✓ VERIFIED | `DEFAULT_MODELS` = Qwen3-Embedding-0.6B / Reranker-0.6B / Qwen2.5-0.5B-Instruct, revision `master`; `verify_manifest` uses SHA-256; no md5 in `download.py`; canonical `<cache>/models/<owner>/<name>`; live `models status --json` cache path/state; 36 model tests pass |
| 4 | `sif models status` shows identity/backend/dims with a backend probe; silent in non-TTY contexts | ✓ VERIFIED | Live run: sections `settings/cache/backend/vector_backend/identity`, exit 0, plain output when piped, no Rich; probe uses `find_spec`/`metadata`; identity states tested. Narrow-path caveat: WR-03 below |
| 5 | uv-first install docs with Linux CPU torch recipe, llama-cpp indexes, degradation matrix, client snippets; every new command/Settings field passes the `make docs-generate` CI diff gate | ✓ VERIFIED | Four install entry points uv-first; `--torch-backend=cpu` + CPU pip index; llama-cpp index table; degradation matrix `:212-225`; client snippets `:227-274`; `make docs-generate` exit 0 with empty docs/README diff; `.github/workflows/test-matrix.yml:79` runs the gate; docs + CI-workflow tests pass |

### Plan Must-Have Truths

All 43 truths declared across the seven PLAN frontmatter files (7+3+7+7+7+6+6) are VERIFIED on the current tree. No truth is FAILED, PRESENT_BEHAVIOR_UNVERIFIED, or overridden.

| # | Plan | Truth (short) | Status | Evidence |
|---|------|---------------|--------|----------|
| 1 | 24-01 | Six-arm fixed grid, shipped default, Qwen3 pins, only chunk knobs vary | ✓ VERIFIED | `SWEEP_GRID`; dry run: 512/128, 512/64, 512/0, 448/112, 384/96, 256/64; every arm modelscope Qwen3, max_tokens 512 |
| 2 | 24-01 | Persisted identity asserted after embed before eval; mismatched baseline rejected/regenerated | ✓ VERIFIED | `STAGE_SUFFIXES` order; identity/baseline-rejection tests pass |
| 3 | 24-01 | Tuning-select then held-out confirm; deterministic tie-break; equal gate never adopts | ✓ VERIFIED | `select_tuning_candidate` / `decide_chunk_default`; boundary tests pass |
| 4 | 24-01 | Empty/zero/sub-floor evidence → insufficient, no default change, countable artifact | ✓ VERIFIED | Insufficient-evidence tests pass |
| 5 | 24-01 | Artifact records per-arm costs, fingerprint, min-heldout, limitation, no query text/paths | ✓ VERIFIED | Arm keys include documents/chunks/embed_wall_seconds/cache deltas; `9ccbf4eea9263ed4`; min 101; `grep -c /Users` = 0 |
| 6 | 24-01 | `--dry-run` full ordered plan, no subprocess; scope change invalidates markers | ✓ VERIFIED | Live dry run exit 0; `test_changed_scope_discards_prior_markers` passes |
| 7 | 24-01 | Overwrite guard refuses differing decision/fingerprint without `--force` | ✓ VERIFIED | Guard code; `test_force_replaces_a_different_run` passes |
| 8 | 24-02 | Builder title+heading dedupe; stored content/FTS/BM25 byte-identical | ✓ VERIFIED | `breadcrumb_embed_texts`; embed-writer overlay; breadcrumb tests pass |
| 9 | 24-02 | `embed_breadcrumb: bool = False` (env), no CLI flag; default-off byte-identical | ✓ VERIFIED | `settings.py:224-226`; no Click option |
| 10 | 24-02 | Only embedding input changes; cache key changes; isolated DB + `--force`; identity not extended | ✓ VERIFIED | `embed_writer.py` overlay; dry-run arm isolates DB + `--force`; identity unchanged |
| 11 | 24-03 | Canonical cache path; explicit cache_dir honored | ✓ VERIFIED | `canonical_model_dir`; live status path; tests |
| 12 | 24-03 | Cache hit requires manifest + size + SHA-256; manifestless re-downloads | ✓ VERIFIED | `verify_manifest`; no md5; state tests pass |
| 13 | 24-03 | Atomic sibling temp download, verify, replace; no partial/leftovers | ✓ VERIFIED | Atomic-install tests pass |
| 14 | 24-03 | DEFAULT_MODELS Qwen3 family with explicit revision; matches Settings | ✓ VERIFIED | Registry printed + parity tests pass |
| 15 | 24-03 | Legacy layouts recognized/migrated; source survives until target verifies | ✓ VERIFIED | Legacy tests pass; post-verify diff widened adoption to the pre-fix layout |
| 16 | 24-03 | `--force` bypass; missing modelscope actionable error naming the embed extra | ✓ VERIFIED | `MODELSCOPE_INSTALL_HINT`; tests pass |
| 17 | 24-03 | `inspect_cache` five states + revision, no download | ✓ VERIFIED | `absent/empty/unverified/legacy/valid`; state tests pass. Caveat: WR-01 (status call site never probes the home tree) |
| 18 | 24-04 | `models pull` no arg / family entry / owner-name variants | ✓ VERIFIED | Help wording; target-resolution tests pass |
| 19 | 24-04 | `--force` bypass; non-interactive; failures are actionable ClickException | ✓ VERIFIED | `test_force_is_forwarded`, `test_missing_modelscope_becomes_click_exception` pass |
| 20 | 24-04 | Status reports configured/cache/identity/backend; probe imports/downloads nothing | ✓ VERIFIED | Live JSON/plain runs; probe test. Caveat: WR-03 (URI-reserved index paths) |
| 21 | 24-04 | Five explicit identity states, mismatch reported, exit 0 | ✓ VERIFIED | Six state tests pass |
| 22 | 24-04 | Non-TTY plain/JSON; Rich only on TTY | ✓ VERIFIED | Live piped output plain; TTY test passes |
| 23 | 24-04 | Hidden deprecated alias delegates; notice stderr-only | ✓ VERIFIED | Live top-level help omits `pull` (0 hits); `pull --help` says deprecated; `hidden=True` |
| 24 | 24-04 | Generator/tests skip hidden commands | ✓ VERIFIED | `generate_cli_ref.py` skip logic; generated reference has no `### sif pull` |
| 25 | 24-05 | Every install entry point leads with uv; pip secondary | ✓ VERIFIED | README:37+, installation:17+, quickstart:31+, index:74+; uv_tool before uvx before pip |
| 26 | 24-05 | Linux CPU `--torch-backend=cpu` recipe; pyproject-index claim removed | ✓ VERIFIED | installation:30, README:46; `grep pyproject` = 0 |
| 27 | 24-05 | llama-cpp wheel indexes, multi-index, source build, py3.12 `all` path | ✓ VERIFIED | installation:167-206 |
| 28 | 24-05 | Honest degradation matrix | ✓ VERIFIED | installation:212-225 (BM25-only, sqlite-vec, Windows rows) |
| 29 | 24-05 | Client snippets link canonical MCP guide | ✓ VERIFIED | installation:229 links `mcp-server.md`; Desktop/Code/plugin snippets follow |
| 30 | 24-05 | models.md Model Management; migration.md canonical cache path | ✓ VERIFIED | `docs/models.md:527`; `docs/migration.md:52` |
| 31 | 24-05 | docs-generate clean; docs guards | ✓ VERIFIED | `make docs-generate` exit 0, empty diff; docs/CI tests pass |
| 32 | 24-06 | Real six-arm artifact with per-arm costs, selection, confirmation, measured N, limitation | ✓ VERIFIED | `chunk-sweep.json`: 6 arms, selected overlap-0, N=194, limitation, decision |
| 33 | 24-06 | Real breadcrumb artifact with overall/leg gates, duplicates, measured N | ✓ VERIFIED | `breadcrumb-verdict.json`: gates, N=194, duplicates |
| 34 | 24-06 | Defaults change only when the artifact decision authorizes | ✓ VERIFIED | Both decisions keep; constants and `embed_breadcrumb` unchanged |
| 35 | 24-06 | Marker code only on a flip; real-embed-path test asserts presence/absence | ✓ VERIFIED | No marker in `src/`; marker test passes |
| 36 | 24-06 | benchmarking.md records both experiments with tables, fingerprint, adequacy, verdicts | ✓ VERIFIED | `docs/benchmarking.md:332-363` |
| 37 | 24-06 | Full suite, docs gate, type check green | ✓ VERIFIED | Full suite 3260 passed/1 skipped @95.12%; docs-generate clean; CI lint job (type check) success at 1.2.3 (run 45135099379). Local `ty` yields 10 environment-dependent diagnostics — see observations |
| 38 | 24-07 | Duplicate metrics per document aggregated per chunk | ✓ VERIFIED | `duplicate_metrics`; artifact shares; tests pass |
| 39 | 24-07 | Body-leg veto: title-only/flat/regressing body rejected; absent body insufficient | ✓ VERIFIED | Policy tests pass |
| 40 | 24-07 | Runbook pins identity, asserts after embed before eval, records model_type + identity | ✓ VERIFIED | Artifact identity; stage order; tests pass |
| 41 | 24-07 | Baseline identity mismatch rejected/regenerated on the same backend | ✓ VERIFIED | Four baseline-rejection tests pass |
| 42 | 24-07 | Artifact aggregate-only, min-heldout 101, N limitation, overwrite guard | ✓ VERIFIED | Artifact; guarded write |
| 43 | 24-07 | `--dry-run` single ordered arm, no subprocess | ✓ VERIFIED | Live dry run: one arm, stages index→embed→identity→eval |

### Requirement Verdicts

- **QUAL-02 — PASS.** Six-arm instrument, isolated arms, per-arm embed cost, held-out gate as the only route to a default change; real committed artifact with keep-default; current-code replay reproduces it.
- **QUAL-03 — PASS.** Breadcrumb builder/default-off switch/writer wiring; per-leg ablation with duplicate metrics; body-leg veto; real artifact keeps the default; replay reproduces it.
- **MODELS-01 — PASS.** Canonical manifest cache with SHA-256 + atomic install + legacy migration + Qwen3 registry; `sif models pull` live and tested.
- **MODELS-02 — PASS.** `sif models status` reports settings/cache/identity/backend/dims, exit 0 in every state, plain non-TTY output; hidden deprecated `sif pull` delegates; generator skips hidden commands. Two open review warnings narrow edge cases (WR-01, WR-03) without falsifying the supported-path truths.
- **DOCS-01 — PASS.** uv-first entry points, Linux CPU torch recipe, llama-cpp indexes, honest degradation matrix, client snippets, model-management/migration sections, clean generator gate at 1.2.3. Post-verification docs hardening was re-checked and preserved every DOCS-01 truth.

## Artifacts and Key Links

Structured verification via `gsd-tools query verify.artifacts` / `verify.key-links` over all seven plans: **27/27 declared artifacts pass, 20/20 key links verified.** (The verb exits 1 on 24-06 only because two artifact paths still read `.planning/phases/24-…`; those two files exist at the archived location and were inspected directly — see WR-04.)

| Artifact | Expected | Status | Evidence |
|----------|----------|--------|----------|
| `src/sif/search/tuning_verdict.py` | sweep grid + gate policy | VERIFIED | `SWEEP_GRID`, `MIN_HELDOUT_FOR_EPSILON_WIN=101`, `select_tuning_candidate`, `decide_chunk_default`, `decide_breadcrumb_default`; exercised by replay |
| `scripts/chunk_sweep.py` | isolated-arm runbook | VERIFIED | live six-arm dry run |
| `scripts/breadcrumb_eval.py` | one-arm runbook | VERIFIED | live single-arm dry run |
| `src/sif/indexing/breadcrumb.py` | builder + duplicate metrics | VERIFIED | imported by `embed_writer.py`; tests |
| `src/sif/models/download.py` | canonical cache + SHA-256 + legacy + registry | VERIFIED | tests + live status |
| `src/sif/cli/commands/models.py` | `models pull`/`status` | VERIFIED | live commands |
| `src/sif/cli/commands/pull.py` | hidden deprecated alias | VERIFIED | live help; delegation tests |
| `scripts/generate_cli_ref.py` | hidden-command skipping | VERIFIED | generated reference |
| `bench/chunk-sweep.json` (archived path) | six-arm evidence + decision | VERIFIED | keep-default, N=194, fingerprint, identity |
| `bench/breadcrumb-verdict.json` (archived path) | breadcrumb per-leg + duplicate evidence | VERIFIED | keep-breadcrumb-off, legs, duplicates |
| `docs/benchmarking.md` | both experiment sections | VERIFIED | `:332-363` |

Key links verified: runbooks → `tuning_verdict`; runbooks → harrier_eval helpers / split gates; identity stages → `read_identity`; `models.py` → `ModelDownloader` + `inspect_cache`; `models.py` → `build_settings_identity`/`read_identity`; `pull.py` → shared models handler; `embed_writer.py` → `breadcrumb_embed_texts`; `index.py`/`watcher.py` → `settings.embed_breadcrumb`; docs → generator scripts.

## Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|--------------------|--------|
| `bench/chunk-sweep.json` | per-arm costs/decision | Real six-arm run over 610 documents, written through the guard | Yes | ✓ FLOWING |
| `bench/breadcrumb-verdict.json` | overall/leg gates/duplicates | Real breadcrumb arm over the same corpus; identity asserted | Yes | ✓ FLOWING |
| `models status` | settings/cache/identity | Live `Settings`, filesystem cache inspection, `index_meta` read | Yes | ✓ FLOWING |
| `docs/benchmarking.md` tables | verdict numbers | Committed artifacts (values re-checked: −0.008605, +0.014104, legs) | Yes | ✓ FLOWING |
| `docs/cli-reference.md` / `docs/configuration.md` | command/field listings | Generator scripts from live Click/Pydantic definitions; clean regeneration | Yes | ✓ FLOWING |

## Behavioral Evidence (run during this verification)

| Check | Command | Result |
|-------|---------|--------|
| Phase-24 targeted suites | `pytest -q --no-cov` over 14 phase test files | **592 passed in 22.01s** |
| Full quality suite | `pytest -q` at HEAD (462266e) | **3260 passed, 1 skipped, 95.12% coverage, 205.08s** |
| Ruff lint / format | `ruff check src tests` / `ruff format --check src tests` | All checks passed; 237 files already formatted |
| Docs generator gate | `make docs-generate` + `git diff --stat -- docs/ README.md` | exit 0; empty diff (both generated files hash-identical) |
| Chunk-sweep dry run | `python3 scripts/chunk_sweep.py --dry-run --json` | exit 0; 6 arms in grid order; pinned identity; no subprocess |
| Breadcrumb dry run | `python3 scripts/breadcrumb_eval.py --dry-run --json` | exit 0; one arm (`embed_breadcrumb: true`); stages index→embed→identity→eval |
| Artifact replay | current `decide_chunk_default` / `decide_breadcrumb_default` on committed gates | `keep-default` / `keep-breadcrumb-off` (matches artifacts) |
| Version banner | `python3 -m sif.cli.main --version` | `sif, version 1.2.3` (matches `docs/installation.md:352`) |
| `models` group / hidden alias | `models --help`, top-level `--help`, `pull --help` | pull+status listed; top-level omits pull; alias says deprecated |
| Status JSON | `models status --json` | exit 0; five sections; cache state reported; identity section present |
| Runtime parity | imports of constants, `Settings`, `DEFAULT_MODELS` | chunk 512/128; `embed_breadcrumb: False`; Settings model = registry entry |
| Privacy grep | `grep -c "/Users" bench/*.json` | 0 in both artifacts |
| Structured checks | `verify.artifacts` / `verify.key-links` per plan | 27/27 artifacts (2 archived-path false negatives resolved), 20/20 links |
| CI at the shipped tree | `gh run view 45135099379` (1.2.3) | All 7 matrix cells + lint/type-check job success |
| State of prior evidence | `24-VALIDATION.md`, `24-SECURITY.md`, `24-REVIEW.md` | validated/nyquist-compliant; threats_open 0; 0 Critical, 4 Warning, 6 Info (all dispositioned open) |

## Probe Execution

No probe scripts apply: `find scripts -path '*/tests/probe-*.sh'` returns nothing and no PLAN/SUMMARY declares a probe path. `--probe-identity` is a runbook CLI flag, not a probe script. Step 7c: N/A.

## Anti-Patterns Found

None. No `TBD`/`FIXME`/`XXX` markers in the phase's key files (tuning_verdict, personal_bench, embedder_verdict, breadcrumb, embed_writer, download, models, pull, chunk_sweep, breadcrumb_eval, installation.md, benchmarking.md). The `placeholders` variables in `personal_bench.py` are SQL bind-parameter builders. The `return None` sites in `download.py` are legitimate not-found/optional-metadata returns covered by tests. No hardcoded-empty rendering; artifacts contain no query text or absolute paths.

## Non-Blocking Observations

These do not violate a roadmap success criterion or a plan must-have as worded, and do not affect the verdict. Items 1-4 are the open code-review findings (`24-REVIEW.md`, dispositioned `open`, 0 Critical); item 5 is the local type-check environment; item 6-7 are carried evidence notes.

1. **WR-01 (warning, open).** `sif models status` always passes an explicit cache path, so `inspect_cache(..., cache_dir=<resolved>)` sets `include_home=False` and never reports `legacy` for the `~/.sif/models` tree that `sif models pull` does adopt. `inspect_cache`'s own five-state contract (must-have 17) still holds when called with the default root; the status surface is narrower than `docs/models.md` implies. Remediation in `24-REVIEW.md`.
2. **WR-02 (warning, open).** `_split_model_id` rejects `.`, `..`, `\`, and NUL but not `:`; on Windows a drive-bearing id can resolve outside `<cache>/models`. Local trust boundary only; no must-have covers it. Security audit remains `threats_open: 0`.
3. **WR-03 (warning, open).** The read-only identity probe builds `file:{path}?mode=ro` without percent-encoding, so an index path containing `?`, `#`, or `%` is reported as `no-identity`. Must-have 20's supported-path behavior is tested and live-verified; this is a narrow-path correctness bug.
4. **WR-04 (warning, open).** Both runbooks and `docs/benchmarking.md:347,363` still name `.planning/phases/24-…` for the two evidence JSON files. They exist under `.planning/milestones/v1.2-phases/24-…`; re-running a runbook would recreate the retired tree. This is the cause of the two 24-06 artifact-path "not found" results above, and of the stale cited paths in the doc — not a missing artifact.
5. **Local `ty` environment.** `ty check src/sif` (local ty 0.0.97 on miniconda py3.13) reports 8 errors + 2 warnings, spanning `embedding/embedder.py`, `models/download.py:545`, and `search/rerank.py`. The lock pins ty 0.0.97 too, but the canonical `uv run --frozen ty check src/sif` lint job passed in CI at 1.2.3; the diagnostics track local site-package stubs (modelscope/sentence-transformers), and `download.py:545`'s `HubApi.get_model_info` line predates Phase 24 (2026-04-15). Not a Phase-24 regression.
6. **Evidence-bookkeeping drift.** `docs/benchmarking.md:334` records en=137/zh=244/mixed=16 while the `24-06-PLAN.md` amendment records en=136/zh=244/mixed=12; the authoritative held-out N=194 agrees everywhere and both artifacts carry it.
7. **Bench artifact schema.** `bench/chunk-sweep.json` records the per-arm vector count implicitly as `chunks` (one vector per chunk); no literal `vectors` key exists, matching the doc's derived column. Unchanged from the prior report.

## Human Verification Required

None. Every behavior-dependent truth (gate-policy boundaries, identity assertion ordering, cache-state machine, atomic install, status states, generator guards, marker iff-flip) is exercised by a passing named test in the 592-test targeted run or the 3260-test full run, and the real-run truths are evidenced by the committed artifacts, the current-code replay, and `docs/benchmarking.md`. The install recipes are documented as hand-verified steps with their verification environment stated (`docs/installation.md:38-39`), exactly as the plan's declared assumption allows.

## Gaps Summary

None. All five phase requirements and all 43 plan must-have truths are delivered and verified against HEAD `462266e`. The committed artifacts survive the current gate policy with their keep-default / keep-breadcrumb-off decisions unchanged; runtime defaults remain 512/128 and `embed_breadcrumb=False`; `sif models pull/status` and the hidden alias work and report honestly on supported inputs; every install entry point is uv-first with a clean generator diff and a 1.2.3 banner. The four post-verification covered changes harden DOCS-01 and the model-cache legacy path without weakening any truth. The full suite is green (3260 passed / 1 skipped @ 95.12%), and CI at the shipped 1.2.3 tree passed all matrix cells plus the lint/type-check job. The four open review Warnings are recorded above as non-blocking observations; none falsifies a roadmap success criterion or a must-have truth.

---

_Verified: 2026-11-24T02:19:28Z_
_Verifier: gsd-verifier (Claude)_
