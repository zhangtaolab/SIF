---
phase: "24"
slug: "tuning-models-ux-install-docs"
verified: "2026-11-18T09:57:25Z"
verified_at: "2026-11-18T09:57:25Z"
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
covered_digest: "v4:sha256:33bc92e7621b52a02a863bcd01a093ca0c5efefa7d74b1d004d5bbd38a855dc5"
behavior_unverified: 0
overrides_applied: 0
gaps: []
re_verification:
  previous_status: passed
  previous_score: "5/5 requirements; 43/43 plan must-have truths"
  reason: "Regeneration — the phase-complete bookkeeping never ran, and commit d97838c (2026-11-18) bumped the version 1.1.2 → 1.2.0 after the prior verify, touching this phase's DOCS-01 surface (docs/installation.md banner). Every must-have re-derived from the current tree; prior claims not carried forward."
  gaps_closed: []
  gaps_remaining: []
  regressions: []
---

# Phase 24: Tuning + Models UX + Install Docs Verification Report

**Phase Goal:** Chunking defaults are evidence-gated, model management is reliable, and every platform has a correct install path — the milestone closes on measured defaults and generator-verified docs.

**Verified:** 2026-11-18T09:57:25Z
**Status:** passed
**Re-verification:** Yes — regeneration after version bump d97838c (1.1.2 → 1.2.0); every must-have re-derived from the current tree, not carried forward.
**Requirements:** QUAL-02, QUAL-03, MODELS-01, MODELS-02, DOCS-01

Method: goal-backward. Every claim below is backed by the live file, the committed artifact,
a command run during this verification, or a passing test — not by SUMMARY text or the prior
report. The only tree change since the prior verify is the v1.2.0 version bump (d97838c:
`docs/installation.md` expected-output banner, changelog, `_version.py`, release-manifest
pinned tests) plus planning-only commit 8f38c24. Per the regeneration brief, the regression
gate is NOT re-run: the fresh full-suite evidence at d97838c (3233 passed / 1 skipped @
95.03% coverage, ruff/format green) is cited, and phase-targeted suites were re-executed live.

## Version-Bump Conformance (new evidence, d97838c)

| Check | Evidence | Result |
|-------|----------|--------|
| Installation banner matches the shipped version | `docs/installation.md:325` says `sif, version 1.2.0`; live `python3 -m sif.cli.main --version` printed `sif, version 1.2.0` | MATCH |
| Generator gate clean at 1.2.0 | `make docs-generate` exit 0; `git diff --stat -- docs/ README.md` empty | PASS |
| Release metadata consistent | `tests/test_release_metadata.py` (retargeted to 1.2.0) green inside the cited full-suite run at d97838c | PASS |

## Requirement Verdicts

### QUAL-02 — Held-out-gated chunk size/overlap sweep: PASS

| Check | Evidence |
|-------|----------|
| Six-arm fixed grid including shipped 512/128, in fixed order | `src/sif/search/tuning_verdict.py` `SWEEP_GRID` (module pure: stdlib + `sif.search.benchmark.EPSILON` only, 358 lines); dry-run grid printed (512/128, 512/64, 512/0, 448/112, 384/96, 256/64) |
| Every arm pins modelscope Qwen3, dim 1024, max_tokens 512; only chunk knobs vary | `scripts/chunk_sweep.py:161-167` env pins; live `--dry-run --json` (exit 0) shows `expected_identity` = modelscope:Qwen/Qwen3-Embedding-0.6B, dimension 1024, null query/document prompts, `max_tokens: 512` |
| Per-arm persisted identity asserted after embed, before eval | identity-stage tests in `tests/unit/scripts/test_chunk_sweep.py` pass (incl. `test_identity_stage_uses_the_probe_mode`, refusal of mismatched identity); committed artifact records the identity |
| Baseline with differing fingerprint/model identity rejected and regenerated | `baseline_rejection_reason` in `scripts/chunk_sweep.py`; `tests/unit/scripts/test_breadcrumb_eval.py:377-431` covers backend/model/fingerprint/invalid/missing baselines — all pass |
| Tuning selects, held-out confirms; deterministic tie-break; equal gate never adopts | `select_tuning_candidate` / `decide_chunk_default` in `tuning_verdict.py`; `test_n100_epsilon_tie_keeps_default`, `test_n101_two_epsilon_win_adopts`, `test_ci_including_zero_never_adopts`, `test_equal_deltas_resolve_by_wall_time_then_grid_order` pass |
| Empty/zero-query/sub-floor evidence → insufficient, no default change, countable artifact | `tuning_verdict.py:160-179`; `TestInsufficientEvidence` + `test_empty_results_are_insufficient_and_countable` pass |
| Committed artifact records per-arm cost/fingerprint/identity, no query text or absolute paths | `bench/chunk-sweep.json` re-inspected: 6 arms, `corpus_fingerprint 9ccbf4eea9263ed4`, `corpus_label books-markdown-papers-2026-11`, `min_heldout_for_epsilon_win: 101`, embedding_dim 1024, identity `modelscope:Qwen/Qwen3-Embedding-0.6B`; `grep -c "/Users"` over both bench JSONs = 0 |
| Real six-arm run, decision keep-default | artifact `decision: keep-default`; confirmation `mean_delta -0.008605`, CI [-0.021559, +0.003094], `n: 194`, `winner: false`; documented at `docs/benchmarking.md:334` |
| Defaults unchanged; only the gate can change them | runtime check printed `512 128` for `DEFAULT_CHUNK_SIZE`/`DEFAULT_CHUNK_OVERLAP` (`src/sif/config/constants.py:19-20`); `embed_breadcrumb` runtime default `False` |
| `--dry-run` full ordered plan, no subprocess; overwrite guard | `python3 scripts/chunk_sweep.py --dry-run --json` exit 0, 6 arms × staged command plans (collection add + index update first), no subprocess invoked; guard covered by passing tests |

### QUAL-03 — Title-breadcrumb experiment (embed-text overlay + per-leg ablation): PASS

| Check | Evidence |
|-------|----------|
| Builder: title + latest heading, dedupe, title-only/content-only cases | `src/sif/indexing/breadcrumb.py`; 13 builder tests pass (`tests/unit/indexing/test_breadcrumb.py`) |
| Default-off Settings switch, no CLI flag | `src/sif/config/settings.py:224` (`embed_breadcrumb`, env `SIF_EMBED_BREADCRUMB`); runtime `Settings().embed_breadcrumb is False`; no breadcrumb Click option |
| Changes only embedding input; stored content/FTS/BM25 unchanged | `src/sif/indexing/embed_writer.py:153,165,190` substitutes texts only at the embed call; `tests/unit/indexing/test_embed_writer.py` asserts persisted chunks/FTS identical (in the 327-test run) |
| Wired through `index embed` and watcher | `src/sif/cli/commands/index.py:422` and `src/sif/indexing/watcher.py:296` pass `settings.embed_breadcrumb` |
| Identity not extended; cache-key consequence documented/tested | no identity code change; embed-writer tests assert every embedded string changes with the flag |
| Duplicate metrics per document, aggregated per chunk | `breadcrumb.py` `duplicate_metrics`; artifact records title_share 1.0, in_content_share 0.622955, subchunk_share 0.387919, title_equals_heading_share 0.026364 over 21,886 chunks/610 docs |
| Body-leg veto: title-only/flat/regressing body → keep-breadcrumb-off; absent body → insufficient | `tuning_verdict.py:298-358`; `test_title_only_win_is_rejected`, `test_absent_body_leg_is_insufficient_evidence` pass |
| Real arm, pinned identity, baseline rejection, artifact guard | `scripts/breadcrumb_eval.py` pins `SIF_EMBED_BREADCRUMB` + modelscope Qwen3/1024/512 (confirmed in live dry-run `arm` payload, `embed_breadcrumb: true`); `bench/breadcrumb-verdict.json` identity `modelscope:Qwen/Qwen3-Embedding-0.6B`, no absolute paths |
| Decision keep-breadcrumb-off with numbers | artifact `decision: keep-breadcrumb-off`, `min_heldout_for_epsilon_win: 101`, fingerprint `9ccbf4eea9263ed4`; overall gate winner false, title leg winner true, body leg winner false; `docs/benchmarking.md:349-363` |
| Default unchanged | runtime check `embed_breadcrumb: False`; no `chunking.contract` marker code in `src/` (neither default flipped) |
| `--dry-run` single ordered arm, no subprocess | `python3 scripts/breadcrumb_eval.py --dry-run --json` exit 0; stages in order `arm:index → arm:embed → arm:identity → arm:eval` |

### MODELS-01 — Reliable `sif models pull`: PASS

| Check | Evidence |
|-------|----------|
| Canonical cache `<Settings.get_cache_dir()>/models/<owner>/<name>` | `src/sif/models/download.py` default root + `canonical_model_dir`; live `models status --json` printed `/Users/forrest/Library/Caches/sif/models/Qwen/Qwen3-Embedding-0.6B`, state `absent`, exit 0, no download triggered |
| Cache hit requires manifest + per-file size + SHA-256; manifestless dir re-downloads | `verify_manifest` + hit/force/legacy/miss ordering in `download.py`; no md5 anywhere in the file; state-machine tests pass |
| Atomic download: sibling temp dir, verify, backup/replace, cleanup on failure | `_install_directory`/`_unique_sibling` covered by tests for success, client failure, missing `config.json`, unverified-target replacement |
| DEFAULT_MODELS = Qwen3-0.6B family with explicit revision; matches Settings | `download.py:45-65` re-read: embedding `Qwen/Qwen3-Embedding-0.6B`, reranker `Qwen/Qwen3-Reranker-0.6B`, query expansion `qwen/Qwen2.5-0.5B-Instruct`, revision `master`; live parity check: Settings model is `modelscope Qwen/Qwen3-Embedding-0.6B` = registry `embedding` entry |
| Legacy layouts recognized; source survives until target verifies | `_legacy_candidates`/`_adopt_legacy_model`; tests cover `~/.sif/models`, ModelScope `name___` tree, ignored config-only trees, failed rename |
| `--force` bypass; missing modelscope actionable error | `MODELSCOPE_INSTALL_HINT` names the embed extra; covered by tests |
| `inspect_cache` five states + revision, no download | five-state tests in `tests/unit/models/test_download.py` pass; live status reported `absent` without downloading |

### MODELS-02 — `sif models status`: PASS

| Check | Evidence |
|-------|----------|
| Reports model id/type/backend/dimension, cache path/state/revision, persisted identity | live `models status --json` (exit 0): sections `settings`, `cache`, `backend`, `vector_backend`, `identity`; plain run prints fixed-order `settings.model_type: modelscope`, `settings.dimension: 1024`, `cache.path`, `cache.state: absent`, `backend.available: true` |
| Backend probe imports/downloads nothing | `importlib.util.find_spec` + `importlib.metadata.version`; `test_backend_probe_uses_find_spec_and_metadata` passes |
| Explicit states, always exit 0 | `test_no_index_reports_no_index`, `test_index_without_identity_row_reports_no_identity`, `test_matching_identity_reports_match`, `test_model_mismatch_is_reported_exit_zero`, `test_stored_dimension_mismatch`, `test_schema_width_mismatch` pass |
| Non-TTY plain lines / JSON; Rich only on TTY | live piped runs produced plain `section.key: value` lines and sorted JSON, no box drawing |
| `sif pull` hidden deprecated alias delegates; stderr-only notice | live: top-level `--help` omits `pull` (count 0); `pull --help` shows "deprecated: use 'sif models pull'"; `src/sif/cli/commands/pull.py` `hidden=True`, stderr-only Console |
| Generator and docs tests skip hidden commands | `scripts/generate_cli_ref.py` skip logic; `docs/cli-reference.md` Model Commands lists `models pull`/`models status`, no `### sif pull`; `test_cli_reference_lists_models_and_hides_pull` passes |

### DOCS-01 — uv-first install + degradation + generator gate (re-verified at 1.2.0): PASS

| Check | Evidence |
|-------|----------|
| Every install entry point is uv-first | `README.md` install block; `docs/installation.md:17-25` (Method 1: uv tool install, Recommended); `docs/quickstart.md:54-60` (`uv tool install 'docsif[embed]'`, CPU variant, BM25-only); `docs/index.md:72-78`; pip is Method 3 (secondary, `installation.md:64`) |
| Linux CPU recipe is the verified `--torch-backend=cpu` form; pyproject-index claim gone | `docs/installation.md:33,50`; `README.md:44`; `grep pyproject docs/installation.md` = no hits; guard `test_installation_docs_do_not_claim_pyproject_index_for_tool_installs` passes |
| llama-cpp wheel indexes, multi-index strategy, source build, py3.12 all-extra path | `docs/installation.md:138-148` (CPU/CUDA 12.1/Metal wheel index table), py3.12 `docsif[all]` paths in quickstart:33 and index.md:85 |
| Honest degradation matrix | `docs/installation.md:191-200`: BM25-only base; missing sqlite-vec → CLI vector/hybrid raise the vector-store error while MCP `hybrid_search` degrades to BM25 with a one-time warning; Windows daemon/service refused, foreground watch/MCP still run; guard tests pass |
| Client snippets (Claude Desktop stdio, Claude Code HTTP, plugin) linking canonical guide | `docs/installation.md:208` links `mcp-server.md`; snippets at 211/229/243 |
| Model management + migration documented | `docs/models.md:527` Model Management; `docs/migration.md:52` canonical cache path, automatic legacy migration, hidden `sif pull` alias note |
| `make docs-generate` clean at 1.2.0; CI diff gate exists; docs guards pass | `make docs-generate` exit 0 + empty `git diff` (run this verification); gate in `.github/workflows/docs.yml`; `tests/test_docs.py` + `tests/test_ci_workflows.py` green in the 327-test run; expected-output banner `sif, version 1.2.0` equals live `--version` output |
| Retired model name absent from docs | `grep -E "gte_Qwen2-7B|iic/gte" docs/*.md README.md` = no hits |

## Plan Must-Have Truths

All 43 truths declared across the seven PLAN frontmatter files (7+3+7+7+7+6+6) are VERIFIED
by the requirement evidence above, re-derived on the current tree. No truth is FAILED,
PRESENT_BEHAVIOR_UNVERIFIED, or overridden. Interpretive note (unchanged): the 24-01 artifact
schema records the vector count as `chunks` (one vector per chunk), surfaced as the "Vectors"
column in `docs/benchmarking.md`, rather than a literal `vectors` key.

## Artifacts and Key Links

| Artifact | Expected | Status | Evidence |
|----------|----------|--------|----------|
| `src/sif/search/tuning_verdict.py` | pure sweep grid + gate policy | VERIFIED | 358 lines; pure imports; `SWEEP_GRID`, `select_tuning_candidate`, `decide_chunk_default`, `decide_breadcrumb_default` all present |
| `scripts/chunk_sweep.py` | isolated-arm runbook, dry-run, identity gate, artifact guard | VERIFIED | 1,098 lines; dry-run ran live without subprocess |
| `scripts/breadcrumb_eval.py` | one-arm runbook, per-leg gates, duplicate metrics | VERIFIED | 1,109 lines; dry-run ran live; artifact written through guard |
| `src/sif/indexing/breadcrumb.py` | builder + duplicate metrics | VERIFIED | `breadcrumb_embed_texts`, `duplicate_metrics`; wired from `embed_writer.py` |
| `src/sif/models/download.py` | canonical cache + SHA-256 manifest + legacy migration + registry | VERIFIED | 564 lines; registry re-read; all states exercised by tests |
| `src/sif/cli/commands/models.py` | `models pull`/`status` | VERIFIED | live commands ran; tests pass |
| `src/sif/cli/commands/pull.py` | hidden deprecated alias | VERIFIED | live: hidden from top-level help, deprecation docstring, delegates |
| `scripts/generate_cli_ref.py` | hidden-command skipping | VERIFIED | generated `docs/cli-reference.md` shows models commands, hides `sif pull` |
| `bench/chunk-sweep.json` | six-arm evidence + decision | VERIFIED | 6 arms, identity, costs, min-heldout 101, keep-default, n=194 confirmation |
| `bench/breadcrumb-verdict.json` | breadcrumb per-leg + duplicate evidence | VERIFIED | legs, duplicates, identity, keep-breadcrumb-off |
| `docs/benchmarking.md` | both experiment sections | VERIFIED | sweep section at :334 (fingerprint, N=194, en=137/zh=244/mixed=16) and breadcrumb section; artifact citations |

Key links verified (via passing suites + live behavior): runbooks → `tuning_verdict`
(`decide_*` calls); runbooks → `harrier_eval` helpers (`assert_within_scratch`, scope state,
atomic writes); runbooks → `personal_bench` split gates; identity stages →
`sif.embedding.identity.read_identity`; `models.py` → `ModelDownloader` registry +
`inspect_cache`; `models.py` → `build_settings_identity`/`read_identity`; `pull.py` → shared
models handler; `embed_writer.py` → `breadcrumb_embed_texts`; `index.py:422`/`watcher.py:296`
→ `settings.embed_breadcrumb`; docs → generator scripts.

## Behavioral Evidence (run during this verification)

| Check | Command | Result |
|-------|---------|--------|
| Phase-24 targeted suites | `pytest -q --no-cov` over tuning_verdict, chunk_sweep, breadcrumb, breadcrumb_eval, download, models, pull, settings, embed_writer, test_docs, test_ci_workflows | **327 passed in 5.07s** |
| Chunk-sweep dry run | `python3 scripts/chunk_sweep.py --dry-run --json` | exit 0; 6 arms in grid order; staged command plans; no subprocess |
| Breadcrumb dry run | `python3 scripts/breadcrumb_eval.py --dry-run --json` | exit 0; one arm (`embed_breadcrumb: true`); stages `arm:index → arm:embed → arm:identity → arm:eval` |
| Version banner | `python3 -m sif.cli.main --version` | `sif, version 1.2.0` — matches `docs/installation.md:325` |
| `models` group | `python3 -m sif.cli.main models --help` | `pull` + `status` listed |
| Status non-TTY JSON / plain | `models status --json` / `models status` | exit 0; five sections; canonical cache path; plain fixed-order lines, no Rich |
| Hidden alias | top-level `--help` / `pull --help` | top-level omits `pull`; alias docstring says deprecated |
| Docs gate | `make docs-generate` + `git diff --stat -- docs/ README.md` | exit 0; empty diff at 1.2.0 |
| Runtime parity | Python check of constants/Settings/DEFAULT_MODELS | chunk 512/128; `embed_breadcrumb: False`; Settings model = registry `embedding` entry |
| Privacy grep | `grep -c "/Users" bench/*.json` | 0 hits in both artifacts |
| Full quality suite (cited, not re-run) | at d97838c, per regeneration brief | **3233 passed, 1 skipped, 95.03% coverage; ruff/format green** |

## Requirements Coverage

| Requirement | Source Plans | REQUIREMENTS.md | Status | Evidence |
| ----------- | ------------ | --------------- | ------ | -------- |
| QUAL-02 | 24-01, 24-06 | line 28, mapped Phase 24 | SATISFIED | sweep instrument + real run + keep-default verdict (above) |
| QUAL-03 | 24-02, 24-06, 24-07 | line 29, mapped Phase 24 | SATISFIED | breadcrumb contract + evaluation layer + keep-breadcrumb-off verdict |
| MODELS-01 | 24-03, 24-04 | line 78, mapped Phase 24 | SATISFIED | download rewrite + `sif models pull` |
| MODELS-02 | 24-04 | line 79, mapped Phase 24 | SATISFIED | `sif models status` + hidden alias + generator skip |
| DOCS-01 | 24-05 | line 83, mapped Phase 24 | SATISFIED | uv-first docs + degradation matrix + generator gate at 1.2.0 |

No orphaned requirements: REQUIREMENTS.md maps exactly these five IDs to Phase 24, and the
seven plans declare exactly these five IDs (24-01/06: QUAL-02; 24-02/06/07: QUAL-03;
24-03/04: MODELS-01; 24-04: MODELS-02; 24-05: DOCS-01).

## Anti-Patterns Found

No `TBD`/`FIXME`/`XXX`/`TODO`/`HACK`/`PLACEHOLDER` markers in the phase's key files
(tuning_verdict, breadcrumb, download, models, pull, chunk_sweep, breadcrumb_eval,
generate_cli_ref). The eight `return None` sites in `download.py` are legitimate
not-found/optional-metadata returns in cache inspection and legacy detection, covered by
tests — not stubs. No hardcoded-empty rendering. Artifacts contain no query text or absolute
paths.

## Human Verification Required

None. Every behavior-dependent truth (gate-policy boundaries, identity assertion ordering,
cache-state machine, atomic install, status states, guards) is exercised by a passing named
test in the 327-test run; the real-run truths are evidenced by the committed artifacts and
`docs/benchmarking.md`. The install recipes (`--torch-backend=cpu`, llama-cpp wheel indexes)
are documented in-repo as hand-verified steps with VERIFY comments, exactly as the plan's
declared assumption requires — this honesty is the deliverable, not a verification gap.

## Gaps Summary

None. All five phase requirements are delivered and verified against the current tree, the
committed evidence artifacts, live CLI behavior, and phase-targeted suites (327 passed), with
the fresh full-suite evidence at d97838c (3233 passed / 1 skipped @ 95.03% coverage,
ruff/format green) covering the regression gate. Both tuning experiments legitimately resolved
to keep-default / keep-breadcrumb-off through the held-out gate, so the unchanged defaults are
the phase's intended outcome, not missing work. The v1.2.0 version bump is fully consistent
with this phase's DOCS-01 surface.

## Non-Blocking Observations (carried forward; unchanged in kind)

These do not violate a phase must-have and do not affect the verdict.

1. `bench/chunk-sweep.json` records the per-arm vector count implicitly as `chunks` (each
   chunk yields one vector); no literal `vectors` field exists (docs derive the "Vectors"
   column from chunks). Remediation: add an explicit `vectors` field if literal schema
   compliance is desired.
2. Re-confirmed live: `--dry-run --json` for both runbooks embeds the full inherited process
   environment under each stage's `env`, including unrelated tokens from the invoking shell
   (the breadcrumb dry-run printed env keys including auth-token variables). Nothing is
   committed, but redirecting dry-run output to a file could leak secrets. Remediation:
   filter the dry-run `env` payload to arm-relevant keys.
3. `src/sif/embedding/embedder.py:468` retains a constructor default of the retired
   `iic/gte_Qwen2-7B-instruct`; unreachable from Settings/factory (Settings always supplies
   Qwen3), but the retired name survives as a default. Remediation: require an explicit model
   id or default to the Qwen3 id.
4. `24-VALIDATION.md` remains `status: draft` / `nyquist_compliant: false`, and the 24-06 PLAN
   assumption records the earlier adequacy totals (en=136/mixed=12) while the authoritative
   saved runs and `docs/benchmarking.md:334` record en=137/zh=244/mixed=16 (re-confirmed this
   run). The validation audit owns the status field; the docs value is the correct one.

---

_Verified: 2026-11-18T09:57:25Z_
_Verifier: gsd-verifier (Claude)_
