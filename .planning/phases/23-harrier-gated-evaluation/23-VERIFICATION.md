---
phase: 23-harrier-gated-evaluation
verified: 2026-11-18T11:52:33Z
status: passed
score: 31/31 must-haves verified
covered_files:
  - ".gitignore"
  - ".planning/phases/23-harrier-gated-evaluation/23-01-PLAN.md"
  - ".planning/phases/23-harrier-gated-evaluation/23-01-SUMMARY.md"
  - ".planning/phases/23-harrier-gated-evaluation/23-02-PLAN.md"
  - ".planning/phases/23-harrier-gated-evaluation/23-02-SUMMARY.md"
  - ".planning/phases/23-harrier-gated-evaluation/23-03-PLAN.md"
  - ".planning/phases/23-harrier-gated-evaluation/23-03-SUMMARY.md"
  - ".planning/phases/23-harrier-gated-evaluation/23-04-PLAN.md"
  - ".planning/phases/23-harrier-gated-evaluation/23-04-SUMMARY.md"
  - ".planning/phases/23-harrier-gated-evaluation/23-05-PLAN.md"
  - ".planning/phases/23-harrier-gated-evaluation/23-05-SUMMARY.md"
  - ".planning/phases/23-harrier-gated-evaluation/23-06-PLAN.md"
  - ".planning/phases/23-harrier-gated-evaluation/23-06-SUMMARY.md"
  - ".planning/phases/23-harrier-gated-evaluation/23-VALIDATION.md"
  - ".planning/phases/23-harrier-gated-evaluation/bench/harrier-verdict.json"
  - "docs/benchmarking.md"
  - "docs/cli-reference.md"
  - "scripts/harrier_eval.py"
  - "src/sif/cli/commands/eval.py"
  - "src/sif/search/embedder_verdict.py"
  - "src/sif/search/personal_bench.py"
  - "tests/support/eval.py"
  - "tests/unit/cli/test_eval.py"
  - "tests/unit/scripts/__init__.py"
  - "tests/unit/scripts/test_harrier_eval.py"
  - "tests/unit/search/test_embedder_verdict.py"
  - "tests/unit/search/test_personal_bench.py"
covered_digest: "v4:sha256:ec4855529bfab88fa6ffbe155a18bd5194375175eff45372151537412ed6f2ba"
behavior_unverified: 0
overrides_applied: 0
re_verification:
  previous_status: passed
  previous_score: 31/31
  gaps_closed: []
  gaps_remaining: []
  regressions: []
advisory: []
---

# Phase 23: Harrier Gated Evaluation Verification Report

**Phase Goal:** An EN+ZH held-out A/B evaluation of Harrier-OSS-v1-0.6b native vs Qwen3-Embedding-0.6B gates the default embedder — the default switches ONLY on a proven win (recorded outcome: keep-qwen3). Model arms are MINIMAL (locked decision "d"): no GGUF arm, no bge-reranker arm.
**Verified:** 2026-11-18T11:52:33Z
**Status:** passed
**Re-verification:** Yes — full regeneration against the current tree (HEAD 46cb115). Prior report passed 31/31; every must-have was re-derived from the codebase. Delta since the prior report: commit `618997c` (`math.fsum` mean + shared `strictly_above_noise_floor()` helper); the recorded verdict remains unchanged (see "Delta Re-Check").

## Roadmap Success Criteria

| # | Success Criterion | Status | Evidence |
|---|-------------------|--------|----------|
| 1 | Evidence-based comparison: EN+ZH held-out A/B of Harrier native vs Qwen3-0.6B, per-arm full re-embed on isolated indexes, per-language × per-leg verdicts, paired deltas + intervals; Harrier queries use `prompt_name="web_search_query"`, never `default_prompt_name` | ✓ VERIFIED | `bench/harrier-verdict.json` carries both arm identities (Qwen3 `modelscope:Qwen/Qwen3-Embedding-0.6B`, Harrier `sentence_transformers:microsoft/harrier-oss-v1-0.6b`, both `source: verified`, 1024-dim, distinct fingerprints `d72e733a…`/`dbfc87b7…`), `gates.language_splits` (en/mixed/zh) and `gates.leg_language_splits` (title/body × en/mixed/zh), paired mean deltas with CIs and 1/N floors; Harrier `query_prompt: web_search_query`, `document_prompt: null`. The runbook's per-arm `index embed --force --chunk-strategy auto` re-embedded all 498 documents per arm in separate DBs. Retained scratch arms still hold 498 documents each with `index_meta.embedder.identity`, and both saved runs share corpus fingerprint `b5d50ce0c696ab3d`. |
| 2 | Default changes ONLY on a proven win beyond the 0.01 tie rule; a no-win is recorded as a rejection with numbers; Qwen3 path stays byte-identical until a pass | ✓ VERIFIED | Artifact `decision: keep-qwen3`; `rule` records the literal booleans (`overall_winner: false`, `ci_excludes_zero: false`, `mean_delta_at_least_epsilon: false`, `above_noise_floor: false`, `adequate: true`, `per_language_floor_ok: true`), held-out N=56 mean delta +0.009430, CI [-0.029587, +0.048389], 1/N floor 0.017857, `min_heldout_for_epsilon_win: 101`, and non-anonymous reasons. `Settings` still defaults `Qwen/Qwen3-Embedding-0.6B`/`modelscope` (`src/sif/config/settings.py:115-137`); `EmbeddingConfig` still defaults `ModelType.MODELSCOPE`/`Qwen/Qwen3-Embedding-0.6B` (`src/sif/models/embedding.py:21-25`); `query_prompt_name`/`document_prompt_name` remain `None`; `docs/configuration.md:56` still documents the Qwen3 default. |

## Delta Re-Check (commit 618997c)

The delta commit changed `src/sif/search/personal_bench.py` (`_mean` now uses `math.fsum`; new `strictly_above_noise_floor()`; `paired_bootstrap` and `noise_gate` use them) and `src/sif/search/embedder_verdict.py` (`above_noise_floor` now calls the shared helper instead of a bare `>`). Phase 23's gating rule is unchanged in intent: the 0.01 epsilon tie and the strict 1/N noise floor veto.

| Check | Command / method | Result | Status |
|-------|------------------|--------|--------|
| Recorded verdict unchanged | `decide_from_payload(artifact["gates"])` with current code | `keep-qwen3`; `to_dict()` byte-equal to the artifact's recorded `rule` block | ✓ PASS |
| Every recorded gate winner unchanged | Recomputed `winner` from each stored `n`/`mean_delta`/CI/`noise_floor` using the current helper | 27/27 leaf gates match their recorded `winner`; 0 mismatches | ✓ PASS |
| Committed held-out delta vs floor | Old raw `abs(mean) > floor` vs new rounded comparison on +0.009430 / 0.017857 | Both `False` — tie semantics not reached by this margin | ✓ PASS |
| Boundary behavior preserved | Direct execution + named test `test_float_accumulated_epsilon_tie_never_wins` | N=100 @ 0.01 ties (winner False); N=101 @ 0.02 clears (winner True); test passes | ✓ PASS |

## Observable Truths

Flip-conditional truths (#24, #26, #27, #28, #29, #30) have a false antecedent under the committed `keep-qwen3` artifact; the plans' authored non-flip branches are the executed contract, not gaps.

### Plan 23-01 — Instrument additions

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | `--compare` carries per-language and per-leg × per-language tuning/held-out gates | ✓ VERIFIED | `ComparisonReport.language_splits`/`leg_language_splits` fields (`personal_bench.py:498-499`), populated by `compare_saved_run` (`:2326-2329`, constructor `:2388-2389`), serialized in `to_dict` (`:534-544`); `test_personal_bench.py` suite passes (159 tests) |
| 2 | Absent language → no gate key; present empty split → visible n=0 gate, never a fabricated winner | ✓ VERIFIED | `language_noise_gates` (`personal_bench.py:2051-2085`) omits absent languages and passes empty series for empty splits (`noise_gate` → `n=0, sufficient=False`); `leg_language_noise_gates` (`:2088-2124`) same semantics; tests assert `n == 0`/`sufficient is False` (`test_personal_bench.py:1833`, `:2334-2335`) |
| 3 | Language-aware widening to ≥10 held-out queries per required language or cap, then a counted error | ✓ VERIFIED | `HeldoutFloorError` (`:1059-1084`) with `accepted`/`tuning`/`heldout`/`sampled`/`language_counts`; `heldout_language_counts` (`:1087-1100`); `_language_floor_unmet` (`:1103-1115`); loop condition `:1162-1166` and post-loop cap guard `:1177-1181`; widening/cap-guard tests pass |
| 4 | `--require-language` parses, validates, forwards; `--compare` ignores it with one stderr warning | ✓ VERIFIED | `eval.py:1007-1015` (`click.Choice(LANGUAGES)`, multiple), forwarding `:750` (`required_languages=require_language`), compare warning `:930-935`; live `sif eval --help` shows the option; `TestRequireLanguageCli` passes |
| 5 | Omitting `required_languages` preserves prior behavior | ✓ VERIFIED | Default `()` (`:1124`); `_language_floor_unmet` returns `False` for empty requirements (`:1112-1113`); `ensure_heldout` body otherwise unchanged; full `test_personal_bench.py` passes |

### Plan 23-02 — Pure two-sided verdict rule

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 6 | Adopt only on overall held-out winner AND every required language mean delta ≥ −0.01 AND n ≥ 10 | ✓ VERIFIED | `decide_from_gates` (`embedder_verdict.py:153-230`); `_language_evidence` adequacy/floor (`:111-150`); decision precedence `:200-213`; adopt/adequacy tests pass |
| 7 | 0.01 at N=100 is not a winner; N=101 can clear; CI containing zero never wins | ✓ VERIFIED | `MIN_HELDOUT_FOR_EPSILON_WIN = 101` (`:40`); executed against current code: `noise_gate([0.0]*100,[0.01]*100).winner is False`, `noise_gate([0.0]*101,[0.02]*101).winner is True`; committed CI includes zero and `ci_excludes_zero` recomputes `False`; named tests `test_n100_delta_0_01_ties_its_own_noise_floor`, `test_n101_delta_0_02_clears_the_floor` pass |
| 8 | One-language regression vetoes a winning overall gate; absent/thin language is `insufficient-evidence` | ✓ VERIFIED | Executed: winning overall + `zh` −0.02 → `keep-qwen3` with `per_language_floor_ok False` and a named reason; absent `zh` → `insufficient-evidence` (`language_heldout_n {'en':10,'zh':0}`); inclusive −0.01 → `adopt-harrier`; n=9/n=10 tests pass |
| 9 | Every decision records literal rule booleans and human-readable reasons | ✓ VERIFIED | `VerdictDecision` fixed fields + `reasons` (`:45-93`); artifact `rule` block carries every boolean and four rejection reasons; recompute matches byte-for-byte |
| 10 | Same rule available from `ComparisonReport` and CLI payload | ✓ VERIFIED | `decide` (`:240-271`), `decide_from_payload` (`:274-308`); runbook imports at `scripts/harrier_eval.py:1622` and calls at `:1630`; 20 verdict tests pass |

### Plan 23-03 — Two-arm runbook

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 11 | Dry run builds both arms' argv/env without subprocess; `-q`, `--index`, identical pins; no Harrier prompt override | ✓ VERIFIED | Executed `python3 scripts/harrier_eval.py --dry-run --json` → exit 0, both arms, qwen3 eval has two `--require-language`, harrier eval has `--compare …/qwen3.json`, no prompt flags; `REMOVED_ENV` includes both prompt keys and API keys (`:80-86`); identical pinned chunk/batch/token/ranking env; `TestDryRun` passes |
| 12 | Per-arm identity gate before either eval (source=verified, model/type/prompt, probe `ok`) | ✓ VERIFIED | `verify_arm_identity` + shared/Harrier/Qwen3 failure helpers (`:333-390`), `verify_arm_pair` (`:393-407`), probe JSON + `check_identity_status` gate (`:423-431`, `:614-661`); retained arm DBs store `source: verified`, exact model/type, Harrier `web_search_query`/no document prompt, revision `f9b9dc8d…` recorded in the artifact; `TestIdentityGate`/`TestProbe` pass |
| 13 | Resumable stage machine over two isolated DBs; records costs; writes committed aggregate artifact | ✓ VERIFIED | `STAGES` (`:440-454`), `build_artifact`/`write_artifact` (`:925`, `:988`), `ARTIFACT_PATH` (`:40-48`); run state shows all 13 stages complete; artifact carries per-arm costs (498 docs / 21,798 chunks / 498 embedded each, wall times, cache deltas) and identity/gates/environment; `TestStageMachine`/`TestArtifact` pass |
| 14 | Run state keyed to resolved corpus scope; changed `--corpus` invalidates markers; inadequate preflight never marked complete | ✓ VERIFIED | `scope_state` (`:457`), `scope_key` (`:470`), `load_run_state` resets on key change; `_run_adequacy_stage` marks complete only when `adequate` (`:1299-1315`); resume/scope tests pass |
| 15 | Duplicate/nested `--corpus` roots refused before indexing | ✓ VERIFIED | `resolve_corpus_roots` (`:672-689`) resolves and rejects duplicates/parent-child pairs; dry run applies the same guard; `TestCorpusRootsGuard` passes |
| 16 | Adequacy preflight on baseline before embed; inadequate → `insufficient-evidence`, exit 3 | ✓ VERIFIED | `STAGES` places `adequacy` before `arm_a_embed` (`:440-445`); `preflight_adequacy` (`:692-740`) catches `HeldoutFloorError`; main returns 3 and writes the insufficient-evidence artifact (`:1723-1734`); `TestPreflight` passes |
| 17 | Cleanup confined to scratch root; `--keep-arms` disables deletion; only run-owned files; scratch git-ignored | ✓ VERIFIED | `assert_within_scratch` (`:1041-1059`) refuses `/`, home, outside paths (and refuses home as scratch root); `cleanup_arms` (`:1062-1084`) removes only arm DBs/sidecars/qwen3 saved run; `.gitignore:49` `.planning/tmp/`; `git check-ignore .planning/tmp/phase-23/qwen3.db` exits 0; `git status --porcelain .planning/tmp` empty; `TestCleanupGuard` passes |

### Plan 23-04 — Real EN+ZH evidence run

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 18 | Real two-arm run: Qwen3 first, then Harrier `--compare`, same snapshot/chunker/config, own DB, verified identity | ✓ VERIFIED | Retained scratch `.planning/tmp/phase-23-zh-heavy/{qwen3,harrier}.db` hold 498 documents each with `index_meta.embedder.identity`; saved runs each carry 99 queries and corpus fingerprint `b5d50ce0c696ab3d`; run state records all stages complete; artifact arm order and per-arm DB paths confirm the Qwen3-first/Harrier-compare procedure |
| 19 | Committed artifact records adequacy, fingerprints, environment, exactly one decision, both identities, per-leg × per-language gates, per-arm costs | ✓ VERIFIED | `bench/harrier-verdict.json`: `decision: keep-qwen3`; corpus `b5d50ce0c696ab3d`; query set `b71a4be84d2a8724`; adequacy en=42/zh=11/mixed=3; both identities; `gates` has overall/splits/language_splits/legs/leg_splits/leg_language_splits/groups/suppressed/top_k; costs and environment present; `min_heldout_for_epsilon_win: 101` |
| 20 | Adequacy checked before embed budget; thin language at cap → `insufficient-evidence` | ✓ VERIFIED | Stage order (`:440-445`); preflight implementation and exit-3 path; recorded run adequate and proceeded (state `adequacy: complete`, counts en=42/zh=11); preflight insufficient branch covered by `TestPreflight` |
| 21 | `docs/benchmarking.md` Phase 23 section in held-out/rejection style; artifact path named; no query text/absolute personal paths | ✓ VERIFIED | Section `### Harrier gated evaluation (Phase 23)` at `docs/benchmarking.md:263`, continues through `:318`; names artifact path (`:265`), decision, fingerprints, adequacy, identities, gate tables, costs, environment, replay note; `grep /Users/` and `/home/` count 0; artifact absolute-path count 0 |
| 22 | No default embedder setting changes in this plan | ✓ VERIFIED | Settings/EmbeddingConfig/docs still Qwen3/modelscope (see SC 2) |

### Plan 23-05 — Conditional default flip (non-flip branch executed)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 23 | Default changes only on `adopt-harrier`; `keep-qwen3` records `default_flip: not-applicable` and changes no code/docs | ✓ VERIFIED | Artifact `default_flip {decision: not-applicable, artifact: …, reason: "verdict did not authorize a change", zero_delta_proof: {status: not-applicable}}`; defaults and docs unchanged |
| 24 | On a pass, Settings/EmbeddingConfig default to Harrier with `sentence_transformers`, prompts None | ✓ VERIFIED (conditional — flip branch not selected) | Antecedent false; Harrier known-model row exists (`src/sif/embedding/prompts.py:29`) for a future flip |
| 25 | Qwen3 remains explicitly selectable and prompt-free; tests prove no role prompts | ✓ VERIFIED | `test_shipped_defaults_are_prompt_free_modelscope_qwen3` passes (asserts Qwen3 defaults, prompt fields None, resolved scheme None/None); Settings still accepts `modelscope` |
| 26 | On a pass, all default claims/docs/changelog updated | ✓ VERIFIED (conditional — flip branch not selected) | Non-flip branch: no default claim changed; `docs/configuration.md:56` still Qwen3 |
| 27 | On a pass, artifact gains flip-shape `default_flip` block | ✓ VERIFIED (conditional — flip branch not selected) | Non-flip block recorded with `zero_delta_proof: {status: not-applicable}` |

### Plan 23-06 — Explicit-Qwen3 zero-delta proof (non-flip branch executed)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 28 | After a flip, explicit-Qwen3 reproduces baseline with all deltas exactly 0.0 | ✓ VERIFIED (conditional — flip branch not selected) | No flip; `build_qwen3_verify_command`/`verify_zero_delta`/`write_zero_delta_proof`/`--verify-qwen3` absent (grep count 0) |
| 29 | Proof written into `default_flip.zero_delta_proof` with fingerprint/timestamp, no hand transcription | ✓ VERIFIED (conditional — flip branch not selected) | Non-flip `{"status": "not-applicable"}` recorded in artifact; no proof numbers exist |
| 30 | Non-zero delta / missing gate / wrong env / missing arm fails loudly | ✓ VERIFIED (conditional — flip branch not selected) | Proof mode not built because not authorized; strictness contract not contradicted |
| 31 | When 23-05 recorded `not-applicable`, record `zero_delta_proof: not-applicable` and run nothing | ✓ VERIFIED | Artifact block confirmed; no verify command exists in `scripts/harrier_eval.py` or its tests |

**Score:** 31/31 truths verified (0 present-but-behavior-unverified; 6 flip-conditional truths satisfied via the authored non-flip branch).

## Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `src/sif/search/personal_bench.py` | per-language gates, widening, report fields, shared floor helper | ✓ VERIFIED | Exists, substantive, wired in `compare_saved_run`; `strictly_above_noise_floor` at `:609-617`, used by `noise_gate` `:1951` |
| `src/sif/cli/commands/eval.py` | `--require-language` pass-through | ✓ VERIFIED | Option, forwarding, compare warning; live CLI help confirms |
| `tests/support/eval.py` | bilingual fixture helper | ✓ VERIFIED | `bilingual_titles_and_bodies` (`:81`) used by tests |
| `tests/unit/search/test_personal_bench.py` | language/widening coverage | ✓ VERIFIED | 159 tests pass, including language gate, widening, cap-guard, float-tie cases |
| `tests/unit/cli/test_eval.py` | flag parsing/forwarding + warning | ✓ VERIFIED | `TestRequireLanguageCli` passes |
| `docs/cli-reference.md` | regenerated CLI reference | ✓ VERIFIED | Documents `--require-language` (`:750`, `:770`) |
| `src/sif/search/embedder_verdict.py` | pure verdict policy | ✓ VERIFIED | Exports present; imports only `benchmark.EPSILON` and `personal_bench.SUPPRESS_BELOW, strictly_above_noise_floor` (pure) |
| `tests/unit/search/test_embedder_verdict.py` | boundary/rejection coverage | ✓ VERIFIED | 20 tests pass |
| `scripts/harrier_eval.py` | runbook, identity gate, stage machine, artifact writer, cleanup guard | ✓ VERIFIED | All declared symbols present; dry run executes; 57-module test battery passes |
| `.gitignore` | `.planning/tmp/` ignore | ✓ VERIFIED | Line 49; `git check-ignore` succeeds |
| `tests/unit/scripts/__init__.py` | test package marker | ✓ VERIFIED | Exists |
| `tests/unit/scripts/test_harrier_eval.py` | dry-run/identity/stage/artifact/preflight/cleanup | ✓ VERIFIED | Suite passes |
| `bench/harrier-verdict.json` | committed aggregate verdict | ✓ VERIFIED | Exactly one decision `keep-qwen3`; all required blocks |
| `docs/benchmarking.md` | Phase 23 evidence section | ✓ VERIFIED | Section present with artifact cross-reference |
| `23-VALIDATION.md` | recorded manual-only outcome | ✓ VERIFIED | `status: validated`, `nyquist_compliant: true`, real-run row recorded |
| `src/sif/config/settings.py` | flip-only Harrier defaults | ✓ N/A (conditional) | Flip branch not selected; Qwen3/modelscope intact |
| `src/sif/models/embedding.py` | flip-only defaults | ✓ N/A (conditional) | Flip branch not selected; Qwen3/modelscope intact |
| `build_qwen3_verify_command`/`verify_zero_delta`/`write_zero_delta_proof`/`TestVerifyQwen3` | flip-only proof mode | ✓ N/A (conditional) | Correctly absent under the non-flip branch (grep count 0) |

## Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `personal_bench.py` | `personal_bench.py` | `compare_saved_run` wires gate helpers | ✓ WIRED | `language_splits=language_splits` at `:2388`, `leg_language_splits=` at `:2389`, computed `:2326-2329` |
| `personal_bench.py` | `eval.py` | `_run_fresh` calls `ensure_heldout(required_languages=require_language)` | ✓ WIRED | `eval.py:750`; tests pass |
| `embedder_verdict.py` | `personal_bench.py` | consumes `GateResult` fields, `SUPPRESS_BELOW`, and the shared floor helper | ✓ WIRED | Direct import `:28`; `GateResult` fields read via `_gate_value`; helper call `:197-199` |
| `scripts/harrier_eval.py` | `embedder_verdict.py` | `decide_from_payload` | ✓ WIRED | `:1622` import, `:1630` call |
| `scripts/harrier_eval.py` | `identity.py` | `read_identity` + `check_identity` probe | ✓ WIRED | Deferred imports `:614`, `:637`, `:651`; identity gate before evals |
| `scripts/harrier_eval.py` | `harrier-verdict.json` | `ARTIFACT_PATH`/`build_artifact`/`write_artifact` | ✓ WIRED | `ARTIFACT_PATH` `:40-48`; artifact committed |
| `docs/benchmarking.md` | `harrier-verdict.json` | section names artifact path and numbers | ✓ WIRED | `:265` cross-reference; numbers match artifact |
| `settings.py` | `prompts.py` | Harrier known-model row | ✓ WIRED (flip-ready) | `prompts.py:29` maps model → `web_search_query`, no document prompt |

## Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|--------------------|--------|
| `harrier-verdict.json` `gates` | gate results | `compare_saved_run` over the real saved runs | Yes — held-out gate equals the retained `harrier-comparison.json` held-out gate (n=56, +0.009430) | ✓ FLOWING |
| `harrier-verdict.json` `arms[*].identity` | embedder identity | `read_identity` on real arm DBs | Yes — both scratch DB `index_meta.embedder.identity` fingerprints equal the artifact (`d72e733a…`, `dbfc87b7…`) | ✓ FLOWING |
| `harrier-verdict.json` `corpus.adequacy` / `corpus.fingerprint` | language counts + corpus hash | preflight synthesis on the real corpus | Yes — en=42, zh=11, mixed=3; corpus fingerprint equals both saved runs (`b5d50ce0c696ab3d`) | ✓ FLOWING |
| `embedder_verdict.VerdictDecision` | rule booleans | `GateResult` values | Yes — recomputed `to_dict()` equals the artifact `rule` block exactly under current code | ✓ FLOWING |

## Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Verdict recomputed from committed artifact | `python3 -c "decide_from_payload(json.load(...)['gates'])"` | `keep-qwen3`; `rule` block byte-equal | ✓ PASS |
| Every gate winner under current helper | recompute 27 leaf gates from stored fields | 0 mismatches | ✓ PASS |
| N=100/N=101 boundary + language veto + inclusive floor | direct execution of `noise_gate`/`decide_from_gates` | tie False / clear True / veto keep / −0.01 adopt / absent insufficient | ✓ PASS |
| Float-tie named test | `pytest tests/unit/search/test_personal_bench.py::TestNoiseGate::test_float_accumulated_epsilon_tie_never_wins` | 1 passed | ✓ PASS |
| Verdict + runbook + CLI + defaults suites | `pytest --no-cov tests/unit/search/test_embedder_verdict.py tests/unit/scripts/test_harrier_eval.py tests/unit/cli/test_eval.py tests/unit/search/test_bench_snapshot.py tests/unit/config/test_settings.py` | 229 passed | ✓ PASS |
| Personal-bench suite | `pytest --no-cov tests/unit/search/test_personal_bench.py` | 159 passed | ✓ PASS |
| Runbook dry run | `python3 scripts/harrier_eval.py --dry-run --json` | exit 0; both arms, correct eval args, no prompt overrides | ✓ PASS |
| CLI surface | `python -m sif.cli.main eval --help` | `--require-language [en|zh|mixed]` present | ✓ PASS |
| Retained arm evidence | read-only SQLite over `.planning/tmp/phase-23-zh-heavy/{qwen3,harrier}.db` | 498 documents each; `index_meta.embedder.identity` present and matching | ✓ PASS |
| Task commits | `git merge-base --is-ancestor` for all 10 SUMMARY task commits | all ancestors of HEAD | ✓ PASS |

## Probe Execution

None declared. The project has no `scripts/*/tests/probe-*.sh` probes for this phase.

### Test Quality Audit

| Test File | Linked Req | Active | Skipped | Circular | Assertion Level | Verdict |
|-----------|-----------|--------|---------|----------|-----------------|---------|
| `test_embedder_verdict.py` | MODEL-02 | yes | 0 | no (formula from §rules, not system output) | Value/Behavioral | PASS |
| `test_harrier_eval.py` | MODEL-01, MODEL-02 | yes | 0 (one platform-conditional symlink skip, not executed here) | no (guards exercised against tmp dirs) | Behavioral | PASS |
| `test_personal_bench.py` (language/floor) | MODEL-01 | yes | 0 | no (deterministic fixtures/inputs, no captured system output) | Value | PASS |
| `test_eval.py` (require-language) | MODEL-01 | yes | 0 | no | Behavioral | PASS |

**Disabled tests on requirements:** 0. **Circular patterns detected:** 0. **Insufficient assertions:** 0.

### Decision Coverage

All trackable CONTEXT.md decisions are honored by shipped artifacts (13/13; `not_honored: []`).

## Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| MODEL-01 | 23-01, 23-03, 23-04 | Evidence-based EN+ZH A/B, per-arm re-embed, isolated indexes, per-language × per-leg verdicts, paired deltas + intervals, Harrier query prompt | ✓ SATISFIED | Artifact gates/identities/adequacy; runbook + instrument tests pass; scoped docs evidence |
| MODEL-02 | 23-02, 23-03, 23-04, 23-05, 23-06 | Default changes only on proven win; recorded rejection with numbers; Qwen3 path byte-identical until pass | ✓ SATISFIED | Pure two-sided rule; `keep-qwen3` rejection with literal booleans and CIs; defaults unchanged; non-flip `default_flip`/`zero_delta_proof: not-applicable` |

Orphaned requirements mapped to Phase 23: none (REQUIREMENTS.md lists only MODEL-01/MODEL-02, both claimed by plans and marked Complete).

## Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| — | — | None | — | No debt markers (`TBD`/`FIXME`/`XXX`), no stubs, no hollow props, no unwired artifacts in the covered set. The `placeholder` grep hits in `personal_bench.py`/`eval.py` are SQL bind-parameter names, not stubs. |

### Advisory (New Scope, Unevidenced)

None — re-verification produced no new-scope findings.

### Deferred Items

None.

## Human Verification Required

N/A — infrastructure/tooling phase. The evidence run is itself the human-executed step and is recorded in the committed artifact, retained scratch arms, saved runs, and run-state; the decision policy is exercised deterministically by tests. No behavior-dependent truth lacks a passing test or directly observed evidence.

## Gaps Summary

No gaps. The phase goal is achieved in the current tree: the EN+ZH held-out A/B evaluation ran on the user's corpus and is committed as aggregate evidence; the two-sided gate policy permits a default switch only on a proven win; and the recorded outcome is `keep-qwen3`, with the shipped default, its pinned tests, and every default claim still on Qwen3-Embedding-0.6B. Commit `618997c` (fsum mean + shared rounded noise-floor helper) does not alter the recorded verdict, the recorded rule block, or any recorded gate winner for the committed numbers.

---

_Verified: 2026-11-18T11:52:33Z_
_Verifier: Claude (gsd-verifier)_
