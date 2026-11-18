---
phase: 23-harrier-gated-evaluation
verified: 2026-11-18T07:16:41Z
status: passed
score: 31/31 must-haves verified
covered_files:
  [
    ".gitignore",
    ".planning/phases/23-harrier-gated-evaluation/23-01-PLAN.md",
    ".planning/phases/23-harrier-gated-evaluation/23-01-SUMMARY.md",
    ".planning/phases/23-harrier-gated-evaluation/23-02-PLAN.md",
    ".planning/phases/23-harrier-gated-evaluation/23-02-SUMMARY.md",
    ".planning/phases/23-harrier-gated-evaluation/23-03-PLAN.md",
    ".planning/phases/23-harrier-gated-evaluation/23-03-SUMMARY.md",
    ".planning/phases/23-harrier-gated-evaluation/23-04-PLAN.md",
    ".planning/phases/23-harrier-gated-evaluation/23-04-SUMMARY.md",
    ".planning/phases/23-harrier-gated-evaluation/23-05-PLAN.md",
    ".planning/phases/23-harrier-gated-evaluation/23-05-SUMMARY.md",
    ".planning/phases/23-harrier-gated-evaluation/23-06-PLAN.md",
    ".planning/phases/23-harrier-gated-evaluation/23-06-SUMMARY.md",
    ".planning/phases/23-harrier-gated-evaluation/bench/harrier-verdict.json",
    "docs/benchmarking.md",
    "docs/cli-reference.md",
    "scripts/harrier_eval.py",
    "src/sif/cli/commands/eval.py",
    "src/sif/search/embedder_verdict.py",
    "src/sif/search/personal_bench.py",
    "tests/support/eval.py",
    "tests/unit/cli/test_eval.py",
    "tests/unit/scripts/__init__.py",
    "tests/unit/scripts/test_harrier_eval.py",
    "tests/unit/search/test_embedder_verdict.py",
    "tests/unit/search/test_personal_bench.py",
  ]
covered_digest: "v4:sha256:f0963c536a07cad7ab751caba8acb3f96873c0e9503fa8b018d0fe429c72f1f2"
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

**Phase Goal:** The default embedder changes only on proven EN+ZH held-out evidence — Harrier-OSS-v1-0.6b native vs Qwen3-Embedding-0.6B baseline, measured on the Phase 18 instrument with identity-protected isolated arms. Model arms are MINIMAL (locked decision "d"): no GGUF arm, no bge-reranker arm.
**Verified:** 2026-11-18T07:16:41Z
**Status:** passed
**Re-verification:** Yes — prior report passed 31/31 but predates Phase 24 source changes; properties re-derived against the CURRENT codebase.

## Roadmap Success Criteria

| # | Success Criterion | Status | Evidence |
|---|-------------------|--------|----------|
| 1 | Evidence-based comparison: EN+ZH held-out A/B of Harrier native vs Qwen3-0.6B, per-arm full re-embed on isolated indexes, per-language × per-leg verdicts, paired deltas + intervals; Harrier queries use `prompt_name="web_search_query"`, never `default_prompt_name` | ✓ VERIFIED | `bench/harrier-verdict.json` carries both arm identities (Qwen3 `modelscope:Qwen/Qwen3-Embedding-0.6B`, Harrier `sentence_transformers:microsoft/harrier-oss-v1-0.6b`, `source: verified`, 1024-dim, distinct fingerprints), `gates.language_splits` (en/mixed/zh) and `gates.leg_language_splits` (body/title), paired mean deltas with CIs and 1/N floors; Harrier `query_prompt: web_search_query`, `document_prompt: null`. Retained isolated arm DBs still hold 498 documents each with `embedder.identity` in `index_meta`. |
| 2 | Default changes ONLY on a proven win beyond the 0.01 tie rule; a no-win is recorded as a rejection with numbers; Qwen3 path stays byte-identical until a pass | ✓ VERIFIED | Artifact `decision: keep-qwen3`, `rule` records the literal booleans (`overall_winner: false`, `mean_delta_at_least_epsilon: false`, `above_noise_floor: false`, CI `[-0.029587, +0.048389]` containing zero, held-out N=56, `min_heldout_for_epsilon_win: 101`) and non-anonymous reasons. `src/sif/config/settings.py` still defaults `Qwen/Qwen3-Embedding-0.6B` / `modelscope`; `src/sif/models/embedding.py` still defaults `ModelType.MODELSCOPE` / `Qwen/Qwen3-Embedding-0.6B`; both prompt fields stay `None`; `docs/configuration.md` still documents the Qwen3 default. |

## Observable Truths

Flip-conditional truths (#24, #26, #27, #28, #29, #30) have a false antecedent under the committed `keep-qwen3` artifact; the plans' authored non-flip branches are the executed contract, not gaps.

### Plan 23-01 — Instrument additions

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | `--compare` carries per-language and per-leg × per-language tuning/held-out gates | ✓ VERIFIED | `ComparisonReport.language_splits`/`leg_language_splits` fields (`personal_bench.py:498-499`), populated by `compare_saved_run` (`:2309-2310`), serialized in `to_dict` (`:534-544`) |
| 2 | Absent language → no gate key; present empty split → visible n=0 gate, never a fabricated winner | ✓ VERIFIED | `language_noise_gates` (`:2034`), `leg_language_noise_gates` (`:2071`); language tests pass (17 selected) |
| 3 | Language-aware widening to ≥10 held-out queries per required language or cap, with counted error | ✓ VERIFIED | `HeldoutFloorError` (`:1042`), `heldout_language_counts` (`:1070`), `_language_floor_unmet` (`:1086`); widening tests pass |
| 4 | `--require-language` parses, validates, forwards; `--compare` ignores with one stderr warning | ✓ VERIFIED | `eval.py` option `:1007`, compare warning `:933`; `RequireLanguageCli` tests pass (6 selected) |
| 5 | Omitting `required_languages` preserves prior behavior | ✓ VERIFIED | Empty-requirement short-circuit in `_language_floor_unmet`; default-path tests pass |

### Plan 23-02 — Pure two-sided verdict rule

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 6 | Adopt only on overall held-out winner AND every required language mean delta ≥ −0.01 AND n ≥ 10 | ✓ VERIFIED | `decide_from_gates` (`embedder_verdict.py:153-228`); inclusive rounded floor; adopt/adequacy tests pass |
| 7 | 0.01 at N=100 is not a winner; N=101 can clear; CI containing zero never wins | ✓ VERIFIED | `MIN_HELDOUT_FOR_EPSILON_WIN = 101` (`:40`); boundary tests pass |
| 8 | One-language regression vetoes a winning overall gate; absent/thin language is `insufficient-evidence` | ✓ VERIFIED | `_language_evidence` (`:111-150`); `DECISION_INSUFFICIENT` path; tests pass |
| 9 | Every decision records literal rule booleans and human-readable reasons | ✓ VERIFIED | `VerdictDecision` returns fixed fields incl. `reasons`; artifact `rule` matches |
| 10 | Same rule available from `ComparisonReport` and CLI payload | ✓ VERIFIED | `decide` (`:238`), `decide_from_payload` (`:272`); runbook calls it (`scripts/harrier_eval.py:1630`) |

### Plan 23-03 — Two-arm runbook

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 11 | Dry run builds both arms' argv/env without subprocess; `-q`, `--index`, identical pins; no Harrier prompt override | ✓ VERIFIED | `build_arm_env` (`:159`), `build_arm_commands` (`:190`); `TestDryRun` (part of 100 passing tests) |
| 12 | Per-arm identity gate before either eval (`source=verified`, model/type/prompt/revision, probe `ok`) | ✓ VERIFIED | `verify_arm_identity` (`:373`), `verify_arm_pair` (`:393`), probe calls `check_identity`; artifact identities `source: verified` with Harrier revision `f9b9dc8d…` |
| 13 | Resumable stage machine over two isolated DBs; records costs; writes committed aggregate artifact | ✓ VERIFIED | `STAGES` (`:440`), `build_artifact` (`:925`), `write_artifact` (`:988`), `ARTIFACT_PATH` (`:40`); artifact matches scratch evidence |
| 14 | Run state keyed to resolved corpus scope; changed `--corpus` invalidates markers; inadequate preflight never marked complete | ✓ VERIFIED | `scope_state` (`:457`), `scope_key` (`:470`); scope/resume tests pass |
| 15 | Duplicate/nested `--corpus` roots refused before indexing | ✓ VERIFIED | `resolve_corpus_roots` (`:672`), invoked in `main`; corpus-guard tests pass |
| 16 | Adequacy preflight on baseline before embed; inadequate → `insufficient-evidence`, exit 3 | ✓ VERIFIED | `preflight_adequacy` (`:692`) catches `HeldoutFloorError`; preflight tests pass |
| 17 | Cleanup confined to scratch root; `--keep-arms` disables deletion; only run-owned files removed; scratch git-ignored | ✓ VERIFIED | `assert_within_scratch` (`:1041`), `cleanup_arms` (`:1062`); `.gitignore:49` `.planning/tmp/`; cleanup tests pass |

### Plan 23-04 — Real EN+ZH evidence run

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 18 | Real two-arm run: Qwen3 first, then Harrier `--compare`, same snapshot/chunker/config, own DB, verified identity | ✓ VERIFIED | Retained scratch `.planning/tmp/phase-23-zh-heavy/` with `qwen3.db`, `harrier.db` (498 documents each; `index_meta.embedder.identity` present), saved-runs and run-state |
| 19 | Committed artifact records adequacy, fingerprints, environment, exactly one decision, both identities, per-leg × per-language gates, per-arm costs | ✓ VERIFIED | `bench/harrier-verdict.json`: `decision: keep-qwen3`, corpus `b5d50ce0c696ab3d`, query-set `b71a4be84d2a8724`, adequacy en=42/zh=11/mixed=3, costs and identities, all gate families |
| 20 | Adequacy checked before embed budget; thin language at cap → `insufficient-evidence` | ✓ VERIFIED | Preflight precedes embed in stage order; recorded run adequate and proceeded |
| 21 | `docs/benchmarking.md` Phase 23 section in held-out/rejection style; artifact path named; no query text/absolute personal paths | ✓ VERIFIED | Section at `docs/benchmarking.md:263`; names artifact, decision, fingerprints, adequacy, identities, gate tables, costs; absolute-path grep clean |
| 22 | No default embedder setting changes in this plan | ✓ VERIFIED | Settings/EmbeddingConfig/docs still Qwen3/modelscope (see SC 2) |

### Plan 23-05 — Conditional default flip (non-flip branch executed)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 23 | Default changes only on `adopt-harrier`; `keep-qwen3` records `default_flip: not-applicable` and changes no code/docs | ✓ VERIFIED | Artifact `default_flip {decision: not-applicable, reason: "verdict did not authorize a change"}`; defaults unchanged |
| 24 | On a pass, Settings/EmbeddingConfig default to Harrier with `sentence_transformers`, prompts None | ✓ VERIFIED (conditional — flip branch not selected) | Antecedent false; Harrier known-model row exists (`src/sif/embedding/prompts.py:29`) for a future flip |
| 25 | Qwen3 remains explicitly selectable and prompt-free; tests prove no role prompts | ✓ VERIFIED | `test_shipped_defaults_are_prompt_free_modelscope_qwen3` passes; prompt fields `None` in both defaults |
| 26 | On a pass, all default claims/docs/changelog updated | ✓ VERIFIED (conditional — flip branch not selected) | Non-flip branch: no default claim changed; `docs/configuration.md` still Qwen3 |
| 27 | On a pass, artifact gains flip-shape `default_flip` block | ✓ VERIFIED (conditional — flip branch not selected) | Non-flip block recorded with `zero_delta_proof: {status: not-applicable}` |

### Plan 23-06 — Explicit-Qwen3 zero-delta proof (non-flip branch executed)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 28 | After a flip, explicit-Qwen3 reproduces baseline with all deltas exactly 0.0 | ✓ VERIFIED (conditional — flip branch not selected) | No flip; `verify_zero_delta`/`--verify-qwen3` intentionally absent (`grep` count 0) |
| 29 | Proof written into `default_flip.zero_delta_proof` with unchanged fingerprint/timestamp, no hand transcription | ✓ VERIFIED (conditional — flip branch not selected) | Non-flip `{"status": "not-applicable"}` recorded in artifact; no proof numbers exist |
| 30 | Non-zero delta / missing gate / wrong env / missing arm fails loudly | ✓ VERIFIED (conditional — flip branch not selected) | Proof mode not built because not authorized; strictness contract not contradicted |
| 31 | When 23-05 recorded `not-applicable`, record `zero_delta_proof: not-applicable` and run nothing | ✓ VERIFIED | Artifact block confirmed; no verify command exists |

**Score:** 31/31 truths verified (0 present-but-behavior-unverified, 6 flip-conditional truths satisfied via the authored non-flip branch).

## Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `src/sif/search/personal_bench.py` | per-language gates, widening, report fields | ✓ VERIFIED | Exists, substantive, wired in `compare_saved_run` |
| `src/sif/cli/commands/eval.py` | `--require-language` pass-through | ✓ VERIFIED | Option, forwarding, compare warning; tests pass |
| `tests/support/eval.py` | bilingual fixture helper | ✓ VERIFIED | `bilingual_titles_and_bodies` used by tests |
| `tests/unit/search/test_personal_bench.py` | language/widening coverage | ✓ VERIFIED | 17 selected language tests pass |
| `tests/unit/cli/test_eval.py` | flag parsing/forwarding + warning | ✓ VERIFIED | 6 selected tests pass |
| `docs/cli-reference.md` | regenerated CLI reference | ✓ VERIFIED | Documents `--require-language` |
| `src/sif/search/embedder_verdict.py` | pure verdict policy | ✓ VERIFIED | Exports present; imports only `benchmark.EPSILON`, `personal_bench.SUPPRESS_BELOW` (pure) |
| `tests/unit/search/test_embedder_verdict.py` | boundary/rejection coverage | ✓ VERIFIED | Module passes |
| `scripts/harrier_eval.py` | runbook, identity gate, stage machine, artifact writer, cleanup guard | ✓ VERIFIED | All declared symbols present; 100-module test run passes |
| `.gitignore` | `.planning/tmp/` ignore | ✓ VERIFIED | Line 49 |
| `tests/unit/scripts/__init__.py` | test package marker | ✓ VERIFIED | Exists |
| `tests/unit/scripts/test_harrier_eval.py` | dry-run/identity/stage/artifact/preflight/cleanup | ✓ VERIFIED | Module passes |
| `bench/harrier-verdict.json` | committed aggregate verdict | ✓ VERIFIED | Exactly one decision `keep-qwen3`; all required blocks |
| `docs/benchmarking.md` | Phase 23 evidence section | ✓ VERIFIED | Section present with artifact cross-reference |
| `23-VALIDATION.md` | recorded manual-only outcome | ✓ VERIFIED | `status: validated`, `nyquist_compliant: true` (Phase 24 closed prior debt) |
| `src/sif/config/settings.py` | flip-only Harrier defaults | ✓ N/A (conditional) | Flip branch not selected; Qwen3/modelscope intact |
| `src/sif/models/embedding.py` | flip-only defaults | ✓ N/A (conditional) | Flip branch not selected; Qwen3/modelscope intact |

## Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `personal_bench.py` | `personal_bench.py` | `compare_saved_run` wires gate helpers | ✓ WIRED | `language_splits=language_splits` (`:2371`), `leg_language_splits=` (`:2372`) |
| `personal_bench.py` | `eval.py` | `ensure_heldout(required_languages=...)` | ✓ WIRED | Forwarding present; tests pass |
| `embedder_verdict.py` | `personal_bench.py` | consumes `GateResult`/`SUPPRESS_BELOW` | ✓ WIRED | Direct import of `SUPPRESS_BELOW`; `GateResult` fields read via `_gate_value` |
| `scripts/harrier_eval.py` | `embedder_verdict.py` | `decide_from_payload` | ✓ WIRED | `:1622` import, `:1630` call |
| `scripts/harrier_eval.py` | `identity.py` | `read_identity` + `check_identity` probe | ✓ WIRED | Identity gate before evals |
| `scripts/harrier_eval.py` | `harrier-verdict.json` | `build_artifact`/`write_artifact` | ✓ WIRED | `ARTIFACT_PATH`; artifact committed |
| `docs/benchmarking.md` | `harrier-verdict.json` | section names artifact path and numbers | ✓ WIRED | `:265` cross-reference |
| `settings.py` | `prompts.py` | Harrier known-model row | ✓ WIRED (flip-ready) | `prompts.py:29` maps model → `web_search_query`, no document prompt |

## Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|--------------------|--------|
| `harrier-verdict.json` `gates` | gate results | `compare_saved_run` over real saved runs | Yes — gates match the documented N/deltas/CIs and scratch arms | ✓ FLOWING |
| `harrier-verdict.json` `arms[*].identity` | embedder identity | `read_identity` on real arm DBs | Yes — `index_meta.embedder.identity` present in both scratch DBs | ✓ FLOWING |
| `harrier-verdict.json` `corpus.adequacy` | language counts | synthesis counts on the real corpus | Yes — en=42, zh=11, mixed=3 | ✓ FLOWING |
| `embedder_verdict.Decision` | rule booleans | `GateResult` values | Yes — artifact `rule` block records the same booleans | ✓ FLOWING |

## Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Verdict rule + runbook suites | `python -m pytest -q tests/unit/search/test_embedder_verdict.py tests/unit/scripts/test_harrier_eval.py` | 100 passed | ✓ PASS |
| Language gates/widening | `python -m pytest -q tests/unit/search/test_personal_bench.py -k "language or Language or widening or heldout"` | 17 passed | ✓ PASS |
| `--require-language` CLI | `python -m pytest -q tests/unit/cli/test_eval.py -k "require_language or RequireLanguage or bilingual"` | 6 passed | ✓ PASS |
| Default lock (fresh install) | `python -m pytest -q tests/unit/search/test_bench_snapshot.py -k "shipped_defaults"` | 1 passed | ✓ PASS |
| Retained arm evidence | read-only SQLite over `.planning/tmp/phase-23-zh-heavy/{qwen3,harrier}.db` | 498 documents each; `index_meta.embedder.identity` present | ✓ PASS |

(Coverage-gate failures in filtered runs are an artifact of running a subset; no test failed.)

## Probe Execution

None declared. The project has no `scripts/*/tests/probe-*.sh` probes for this phase.

### Test Quality Audit

| Test File | Linked Req | Active | Skipped | Circular | Assertion Level | Verdict |
|-----------|-----------|--------|---------|----------|-----------------|---------|
| `test_embedder_verdict.py` | MODEL-02 | yes | 0 | no (formula from §rules, not system output) | Value/Behavioral | PASS |
| `test_harrier_eval.py` | MODEL-01, MODEL-02 | yes | 0 (one platform symlink skip in prior run) | no (guards exercised against tmp dirs) | Behavioral | PASS |
| `test_personal_bench.py` (language) | MODEL-01 | yes | 0 | no (fixtures are deterministic inputs, not captured system output) | Value | PASS |
| `test_eval.py` (require-language) | MODEL-01 | yes | 0 | no | Behavioral | PASS |

**Disabled tests on requirements:** 0. **Circular patterns detected:** 0. **Insufficient assertions:** 0.

### Decision Coverage

All trackable CONTEXT.md decisions are honored by shipped artifacts (13/13; `not_honored: []`).

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| MODEL-01 | 23-01, 23-03, 23-04 | Evidence-based EN+ZH A/B, per-arm re-embed, isolated indexes, per-language × per-leg verdicts, paired deltas + intervals, Harrier query prompt | ✓ SATISFIED | Artifact gates/identities/adequacy; runbook + instrument tests pass; scoped docs evidence |
| MODEL-02 | 23-02, 23-03, 23-04, 23-05, 23-06 | Default changes only on proven win; recorded rejection with numbers; Qwen3 path byte-identical until pass | ✓ SATISFIED | Pure two-sided rule; `keep-qwen3` rejection with literal booleans and CIs; defaults unchanged; non-flip `default_flip`/`zero_delta_proof: not-applicable` |

Orphaned requirements mapped to Phase 23: none (REQUIREMENTS.md lists only MODEL-01/MODEL-02, both claimed by plans and marked Complete).

## Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| — | — | None | — | No debt markers, stubs, hollow props, or unwired artifacts in the covered set |

## Human Verification Required

N/A — infrastructure/tooling phase. The evidence run is itself the human-executed step and is recorded in the committed artifact, scratch arms, and run-state; the decision policy is exercised deterministically by tests.

## Gaps Summary

No gaps. The prior `passed 31/31` verdict survives re-derivation against the current tree: Phase 24 touched `personal_bench.py`, `eval.py`, `scripts/harrier_eval.py`, docs, and both default-config files, but all Phase 23 properties still hold and all targeted suites pass. The outcome remains the plan-authored non-flip branch: `keep-qwen3`, `default_flip: not-applicable`, `zero_delta_proof: {status: not-applicable}`. Unflipped defaults are intact (Qwen3 / modelscope, prompt fields None). Security register is 24/24 closed.

---

_Verified: 2026-11-18T07:16:41Z_
_Verifier: Claude (gsd-verifier)_
