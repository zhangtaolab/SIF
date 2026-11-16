---
phase: 23-harrier-gated-evaluation
verified: 2026-11-16T15:28:15Z
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
covered_digest: "v4:sha256:3a82e1b80d5a3ebabef843bb2f73f693b6f2238a2df66b2f6e960567d4be5274"
behavior_unverified: 0
overrides_applied: 0
---

# Phase 23: Harrier Gated Evaluation Verification Report

**Phase Goal:** The default embedder changes only on proven EN+ZH held-out evidence — Harrier-OSS-v1-0.6b native vs Qwen3-Embedding-0.6B baseline, measured on the Phase 18 instrument with identity-protected isolated arms. Model arms are MINIMAL (locked decision "d"): no GGUF arm (conditional follow-up MODEL-F1), no bge-reranker arm.
**Verified:** 2026-11-16T15:28:15Z
**Status:** passed
**Re-verification:** No — initial verification

## Roadmap Success Criteria

| # | Success Criterion | Status | Evidence |
|---|-------------------|--------|----------|
| 1 | Evidence-based comparison: EN+ZH held-out A/B of Harrier native vs Qwen3-0.6B, per-arm full re-embed on isolated indexes, per-language × per-leg verdicts, paired deltas + intervals; Harrier query prompt `web_search_query`, never `default_prompt_name` | ✓ VERIFIED | Two arm DBs under `.planning/tmp/phase-23-zh-heavy/` both hold 498 documents / 21,798 chunks / 498 embedded documents; stored identities match the artifact (`source: verified`, 1024-dim, distinct fingerprints); Harrier `query_prompt=web_search_query`, `document_prompt=null`; artifact carries `language_splits` and `leg_language_splits` with paired deltas, CIs, and 1/N floors |
| 2 | Default changes ONLY on a proven win beyond the 0.01 tie rule; a no-win is recorded as a rejection with numbers; Qwen3 path stays byte-identical until a pass | ✓ VERIFIED | Committed artifact records `keep-qwen3` with held-out N=56, Δ +0.009430, CI [-0.029587, +0.048389], floor 0.017857, `min_heldout_for_epsilon_win: 101`; settings/EmbeddingConfig/prompts/manager/identity and `docs/configuration.md` are unchanged across the whole phase (`git diff 7f7ac8c..HEAD` empty for those paths); full suite 3004 passed / 1 skipped |

## Observable Truths

Statuses marked "conditional" are flip-conditional plan truths whose antecedent (`decision: adopt-harrier`) is explicitly false in the committed artifact; the plan's own non-flip branch is the executed contract.

### Plan 23-01 — Instrument additions

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | `--compare` report carries per-language and per-leg × per-language tuning/held-out gates, so D-08 rule (b) is computable without re-deriving baseline metrics | ✓ VERIFIED | `ComparisonReport.language_splits`/`leg_language_splits` (`src/sif/search/personal_bench.py:498-499`), populated in `compare_saved_run` (`:2304-2309`), serialized in `to_dict` (`:534-544`); `TestPerLanguageNoiseGates` passes |
| 2 | An absent language produces no gate key; a present empty split produces a visible n=0 gate, never a fabricated zero winner | ✓ VERIFIED | `language_noise_gates` skips absent languages (`:2052-2055`) and passes empty series for each declared split (`:2057-2061`); `test_an_absent_language_has_no_key_at_all`; artifact shows visible `mixed` tuning n=1 and `body/mixed` tuning n=0 diagnostics |
| 3 | Language-aware widening continues past the total/held-out floors until each required language has ≥10 held-out queries or the cap, then raises a counted error naming per-language counts | ✓ VERIFIED | `_language_floor_unmet` (`:1086-1098`), both widening and cap-guard conditions (`:1140-1159`), `HeldoutFloorError` carries `language_counts` (`:1042-1067`); `TestEnsureHeldout` language cases pass |
| 4 | `sif eval --personal --require-language en --require-language zh` parses, validates against LANGUAGES, forwards to `ensure_heldout`; `--compare` ignores it with one stderr warning | ✓ VERIFIED | `src/sif/cli/commands/eval.py:994-1004` (`click.Choice(LANGUAGES)`, multiple), forwarding at `:728,747`, compare warning at `:925-929`; `TestRequireLanguageCli` (help, invalid language, forwarding, one-warning stdout-clean) passes |
| 5 | Calling `ensure_heldout` without `required_languages` preserves the current behavior byte-for-byte | ✓ VERIFIED | Default is `()` (`:1107`); `_language_floor_unmet` returns False immediately for an empty requirement (`:1095-1096`); `test_empty_required_languages_preserves_the_default_path`; full suite green |

### Plan 23-02 — Pure two-sided verdict rule

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 6 | Default adopted only when the overall held-out gate is a Phase 18 winner AND every required language's held-out mean delta ≥ −0.01 AND every required language has ≥10 held-out pairs | ✓ VERIFIED | `decide_from_gates` (`src/sif/search/embedder_verdict.py:153-228`); adequacy at `n >= SUPPRESS_BELOW`; `per_language_floor_ok` is inclusive `round(mean_delta,6) >= -0.01`; `TestAdoptEndToEnd`, `TestAdequacy` |
| 7 | Δ=0.01 at N=100 is not a winner (strict 1/N floor); N=101 can clear it; a CI containing zero never wins | ✓ VERIFIED | `MIN_HELDOUT_FOR_EPSILON_WIN = 101` (`:38-41`); boundary tests `test_n100_delta_0_01_ties_its_own_noise_floor`, `test_n101_delta_0_02_clears_the_floor`, `test_ci_containing_zero_never_adopts` |
| 8 | A one-language win with the other language below −0.01 is rejected; absent/thin language produces `insufficient-evidence`, never `adopt-harrier` | ✓ VERIFIED | `_language_evidence` (`:111-150`); `test_language_regression_vetoes_a_winning_overall_gate`, `test_absent_required_language_is_insufficient`, `test_thin_language_nine_is_insufficient` |
| 9 | Every decision records literal rule booleans and human-readable reasons | ✓ VERIFIED | `VerdictDecision.to_dict` fixed 16-key order (`:74-93`); `TestReasonAuditability` asserts every rejection is non-anonymous and adopt is clean; committed artifact `rule` block matches |
| 10 | The same pure rule is available from a `ComparisonReport` and the CLI comparison payload | ✓ VERIFIED | `decide` (`:238-269`) and `decide_from_payload` (`:272-306`); `TestAdoptEndToEnd` exercises all three entry points; runbook calls `decide_from_payload` (`scripts/harrier_eval.py:1630`) |

### Plan 23-03 — Two-arm runbook

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 11 | Dry run builds both arms' exact argv/env without a subprocess; every command has `-q` and `--index`; both arms pin the same chunk/batch/token values; Harrier env has no prompt override | ✓ VERIFIED | Executed `python scripts/harrier_eval.py --dry-run --corpus example-corpus`; both arms show identical pinned `SIF_CHUNK_SIZE=512`, `SIF_CHUNK_OVERLAP=128`, `SIF_BATCH_SIZE=32`, `SIF_MAX_TOKENS=512`, `SIF_EMBEDDING_DIM=1024`, removed `SIF_QUERY_PROMPT_NAME`/`SIF_DOCUMENT_PROMPT_NAME`; `TestDryRun` (including subprocess-not-called) passes |
| 12 | Before either eval, each arm's stored identity is `source=verified`, matches model/type/prompt/revision, and loading the arm model under arm env yields `check_identity.status == 'ok'` | ✓ VERIFIED | `verify_arm_identity` checks source/dimension/model/prompt (`:333-390`); probe runs `check_identity(..., mode="search")` (`:651`) and `require_probe_ok` requires `ok`; stage order is probe before each eval (`:1741-1756`); real DB `embedder.identity` rows match the artifact, including Harrier revision `f9b9dc8d...` and `query_prompt=web_search_query`. Revision is matched through the probe's `identity_matches` (which compares revision when both known); the per-arm pre-check omits an explicit revision compare (open IN-02, audit-only) |
| 13 | Resumable stage machine over two isolated scratch DBs; records per-arm documents/chunks/embeddings/wall time/cache deltas; writes committed aggregate artifact with identities, fingerprints, gates, environment, verdict | ✓ VERIFIED | `STAGES` (`:440-455`); real `run-state.json` under `phase-23-zh-heavy` records all 13 stages; artifact matches raw DB counts and saved-run gates; per-arm costs recorded from read-only DB/cache reads |
| 14 | Run state keyed to resolved corpus scope; a changed `--corpus` set invalidates markers; an inadequate preflight is recorded but never marked complete, so a resumed run re-checks before embedding | ✓ VERIFIED | `scope_state`/`scope_key` (`:457-475`), `load_run_state` (`:477+`); tests `test_changed_scope_key_discards_every_marker`, `test_resumed_full_run_rechecks_adequacy_without_embedding`, `test_inadequate_then_adequate_rerun_reaches_the_full_flow` |
| 15 | Duplicate or nested `--corpus` roots are refused before indexing | ✓ VERIFIED | `resolve_corpus_roots` (`:672-689`), invoked in `main` before any command (`:1850-1854`); `TestCorpusRootsGuard` (duplicate, same-dir spelling, parent/child either order, disjoint order, dry-run guard) |
| 16 | Adequacy preflight runs on the baseline arm before the embed budget; inadequate corpus emits `insufficient-evidence` and exits 3 | ✓ VERIFIED | Stage order `_run_adequacy_stage` before `_run_embed_stage` (`:1723,1741`); `_build_insufficient_artifact` (`:1524-1552`); `test_english_only_corpus_is_inadequate_and_incomplete` |
| 17 | Cleanup refuses `/`, home, and paths outside the scratch root; `--keep-arms` disables deletion; only run-owned DB/sidecar files are removed; scratch root is git-ignored | ✓ VERIFIED | `assert_within_scratch` resolves both sides and rejects `/`/home roots (`:1041-1059`); `cleanup_arms` (`:1062-1084`); `.gitignore:49` `.planning/tmp/`; `git check-ignore` confirms; `TestCleanupGuard` (root, home, nested-under-home, symlink, sibling, keep-arms, only-own-files) |

### Plan 23-04 — Real EN+ZH evidence run

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 18 | A real two-arm evidence run is recorded on the EN+ZH corpus: Qwen3 first, then Harrier `--compare`, same snapshot/chunker/config, own file-backed DB, verified identity | ✓ VERIFIED | Retained scratch `.planning/tmp/phase-23-zh-heavy/`: `qwen3.db` and `harrier.db` each 498 documents / 21,798 chunks / 498 embedded documents, identical 7 collections matching run-state roots; both `embedder.identity` rows `source=verified`, distinct fingerprints; `saved-runs/qwen3.json` and `harrier.json` both present |
| 19 | Committed artifact records adequacy counts, corpus/query-set fingerprints, environment, exactly one decision, and (when compared) both full identities, per-leg × per-language gates with N/CIs, per-arm cost/provenance | ✓ VERIFIED | `bench/harrier-verdict.json` has `decision: keep-qwen3`, `corpus.fingerprint b5d50ce0c696ab3d`, adequacy en=42/zh=11/mixed=3, `query_set_fingerprint b71a4be84d2a8724`, both identities and costs, `gates.overall/splits/language_splits/leg_splits/leg_language_splits`; raw `harrier-comparison.json` gates compare byte-equal |
| 20 | Corpus adequacy is checked before the embed budget; either required language <10 held-out at the cap records `insufficient-evidence` and keeps Qwen3 | ✓ VERIFIED | `run-state.json` records `adequacy` before `arm_a_embed`; code path exits 3 without verdict markers (`:1727-1740`); `TestPreflight`; recorded run was adequate and proceeded |
| 21 | `docs/benchmarking.md` Phase 23 section records the evidence in held-out/rejection style, names the artifact path, and contains no personal query text or absolute personal paths | ✓ VERIFIED | `docs/benchmarking.md:259-...` (`### Harrier gated evaluation (Phase 23)`); names artifact path, decision, corpus/query fingerprints, adequacy, 101-query implication, identities, gates, suppressed groups, costs; `grep -E "/Users/\|/home/\|/private/"` returns nothing; artifact has no query text |
| 22 | No default embedder setting changes in this plan, regardless of decision | ✓ VERIFIED | Commit `0b9c143` touches only artifact + `docs/benchmarking.md` + `23-VALIDATION.md`; `git diff 7f7ac8c..HEAD` for `src/sif/config/settings.py` and `src/sif/models/embedding.py` is empty; defaults remain Qwen3/modelscope (`settings.py:115-137`, `models/embedding.py:21-25`) |

### Plan 23-05 — Conditional default flip (non-flip branch executed)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 23 | Default embedder changes only when the committed artifact decision is `adopt-harrier`; `keep-qwen3`/`insufficient-evidence` records `default_flip: not-applicable` and changes no code or docs | ✓ VERIFIED | Artifact `default_flip {decision: not-applicable, artifact: ..., reason: "verdict did not authorize a change"}`; commit `9f68808` modifies only the artifact; `git diff` of settings/embedding/docs clean; decision is `keep-qwen3` |
| 24 | On a pass, Settings and EmbeddingConfig default to `microsoft/harrier-oss-v1-0.6b` with `sentence_transformers`, prompts None so the known-model table supplies `web_search_query` | ✓ VERIFIED (conditional — flip branch not selected) | Antecedent false: `decision: keep-qwen3`; the non-flip branch is authoritative. Current defaults remain Qwen3/modelscope with both prompt fields None; the Harrier table row exists (`src/sif/embedding/prompts.py:29`) |
| 25 | Qwen3 remains explicitly selectable and prompt-free; tests prove the explicit-Qwen3 path resolves to no role prompts | ✓ VERIFIED | `test_shipped_defaults_are_prompt_free_modelscope_qwen3` (`tests/unit/search/test_bench_snapshot.py:361-386`) asserts `query_prompt_name is None`, `document_prompt_name is None`, and `resolve_prompt_scheme` returns no prompts; `test_qwen3_default_has_no_prompt` (`tests/unit/embedding/test_identity.py:572-575`); Qwen3 is absent from the known-model table |
| 26 | On a pass, every hand-maintained default claim is updated, generator-owned docs regenerated, changelog records the flip + re-embed requirement | ✓ VERIFIED (conditional — flip branch not selected) | Non-flip branch: no docs, generated docs, or changelog changed; `docs/cli-reference.md` only carries the earlier `--require-language` regeneration; `docs/configuration.md` unchanged across the phase |
| 27 | On a pass, the artifact gains a `default_flip` block recording old/new defaults, docs touched, re-embed requirement, and a pending zero-delta proof for 23-06 | ✓ VERIFIED (conditional — flip branch not selected) | Non-flip contract recorded instead: `default_flip` carries decision/artifact/reason and `zero_delta_proof {status: not-applicable}`; the plan's non-flip branch explicitly skips the flip-shape fields |

### Plan 23-06 — Explicit-Qwen3 zero-delta proof (non-flip branch executed)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 28 | After a default flip, explicit-Qwen3 reproduces the pre-flip baseline with every overall/split/language/leg/leg×split delta exactly 0.0 | ✓ VERIFIED (conditional — flip branch not selected) | No flip occurred; `--verify-qwen3`/`verify_zero_delta`/`write_zero_delta_proof` are intentionally absent, and the proof run is not applicable. The retained Qwen3 arm DB and saved run exist for a future flip audit |
| 29 | The proof is written into `default_flip.zero_delta_proof` by the runbook with the unchanged Qwen3 fingerprint and timestamp; no hand-transcribed numbers | ✓ VERIFIED (conditional — flip branch not selected) | Flip path not authorized; non-flip branch records `{"status": "not-applicable"}` only; no hand-written proof numbers exist |
| 30 | A non-zero delta, missing gate block, wrong model env, or missing arm DB/saved run fails loudly | ✓ VERIFIED (conditional — flip branch not selected) | Applicable only to the unbuilt flip proof mode; no proof ran. The strictness contract in plan 23-06 is not contradicted |
| 31 | When plan 23-05 recorded `not-applicable`, this plan records `zero_delta_proof: not-applicable` and performs no real-model run | ✓ VERIFIED | Artifact `default_flip.zero_delta_proof == {"status": "not-applicable"}`; commit `7fb9b6e` only touches the artifact; scratch saved-run mtimes (22:12) predate the commit (22:46); no verify command exists |

**Score:** 31/31 truths verified (0 present-but-behavior-unverified). Six truths (#24, #26, #27, #28, #29, #30) are flip-conditional; their antecedent is explicitly false under the recorded `keep-qwen3` decision, and the plans' non-flip branches are the executed, satisfied contract.

## Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `src/sif/search/personal_bench.py` | per-language gate helpers, widening, additive report fields | ✓ VERIFIED | Exists, substantive, wired into `compare_saved_run`; 205-line phase diff |
| `src/sif/cli/commands/eval.py` | additive `--require-language` pass-through | ✓ VERIFIED | Option + forwarding + compare warning; wired and tested |
| `tests/support/eval.py` | deterministic bilingual fixture helper | ✓ VERIFIED | `bilingual_titles_and_bodies`; used by `TestBilingualFixture` |
| `tests/unit/search/test_personal_bench.py` | language/leg-language gate and widening coverage | ✓ VERIFIED | New `TestPerLanguageNoiseGates`, `TestHeldoutLanguageCounts`, widening cases; pass |
| `tests/unit/cli/test_eval.py` | repeatable flag parsing/forwarding + compare warning | ✓ VERIFIED | `TestRequireLanguageCli`, `TestBilingualFixture`; pass |
| `docs/cli-reference.md` | regenerated CLI reference with `--require-language` | ✓ VERIFIED | Line 711/729 document the option; matches `click` help |
| `src/sif/search/embedder_verdict.py` | pure two-sided verdict policy and constants | ✓ VERIFIED | All declared exports present; no Click/Rich/embedding/DB imports; constants and `MIN_HELDOUT_FOR_EPSILON_WIN = 101` |
| `tests/unit/search/test_embedder_verdict.py` | table-driven boundary/rejection coverage | ✓ VERIFIED | 20 tests, all pass. Note: `verify.artifacts` reports "Missing pattern: insufficient-evidence" because the test uses the `DECISION_INSUFFICIENT` constant, which equals that literal in the module; behavior is present, not a stub |
| `scripts/harrier_eval.py` | two-arm runbook, identity gate, stage machine, preflight, artifact writer, cleanup guard | ✓ VERIFIED | All declared exports present (1888 lines); stdlib-only at import; exercised by dry run + real scratch evidence |
| `.gitignore` | `.planning/tmp/` ignore rule | ✓ VERIFIED | Line 49; `git check-ignore` confirms arm DBs/saved runs/state cannot be staged |
| `tests/unit/scripts/__init__.py` | test package marker | ✓ VERIFIED | Exists |
| `tests/unit/scripts/test_harrier_eval.py` | dry-run/identity/stage/artifact/preflight/cleanup coverage | ✓ VERIFIED | 57+ tests including post-review regressions; all pass (one platform-conditional symlink skip) |
| `.planning/.../bench/harrier-verdict.json` | committed aggregate verdict artifact | ✓ VERIFIED | Tracked in git; exactly one decision `keep-qwen3`; raw comparison gates equal; cache counts match (modelscope 21,342; Harrier bucket 20,346) |
| `docs/benchmarking.md` | hand-maintained Phase 23 evidence section + artifact cross-reference | ✓ VERIFIED | Section present; artifact path, decision, fingerprints, gates, costs; no absolute paths/query text |
| `.planning/.../23-VALIDATION.md` | recorded manual-only verification outcome | ✓ VERIFIED (artifact), debt noted | Real-run and adequacy rows recorded; file remains `status: draft`, `nyquist_compliant: false` (verification debt, below) |
| `src/sif/config/settings.py` | Harrier defaults on a pass | ✓ N/A (conditional) | Flip branch not selected; file intentionally unchanged and still defaults to `Qwen/Qwen3-Embedding-0.6B` / `modelscope` |
| `src/sif/models/embedding.py` | consistent EmbeddingConfig defaults on a pass | ✓ N/A (conditional) | Flip branch not selected; file intentionally unchanged |
| `tests/unit/config/test_settings.py` | updated default pin + explicit-Qwen3 selection on a pass | ✓ N/A (conditional) | Flip branch not selected; existing tests still pin modelscope default |
| `tests/unit/search/test_bench_snapshot.py` | updated D-19 lock for Harrier on a pass | ✓ N/A (conditional) | Flip branch not selected; D-19 lock still asserts the Qwen3 default and prompt-free path |
| `scripts/harrier_eval.py` (`--verify-qwen3` exports) | proof mode on a flip | ✓ N/A (conditional) | Plan 23-06 non-flip branch explicitly records not-applicable without a model run; no unused proof code added |
| `tests/unit/scripts/test_harrier_eval.py` (`TestVerifyQwen3`) | proof coverage on a flip | ✓ N/A (conditional) | Same non-flip branch |

## Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `personal_bench.py` | `personal_bench.py` | `compare_saved_run` wires language gates into `ComparisonReport` | ✓ WIRED | Pattern `language_splits=language_splits` present |
| `personal_bench.py` | `cli/commands/eval.py` | `_run_fresh` calls `ensure_heldout(required_languages=require_language)` | ✓ WIRED | Pattern present in target |
| `embedder_verdict.py` | `personal_bench.py` | consumes `GateResult` fields and `SUPPRESS_BELOW` verbatim | ✓ WIRED | Imports and field reads present; tests use real `noise_gate` gates |
| `scripts/harrier_eval.py` | `embedder_verdict.py` | `decide_from_payload` on the CLI comparison object | ✓ WIRED | `scripts/harrier_eval.py:1630` |
| `scripts/harrier_eval.py` | `embedding/identity.py` | `read_identity` + `check_identity` before each eval | ✓ WIRED | Probe at `:651`; real DB identity rows match artifact |
| `scripts/harrier_eval.py` | `embedder_verdict.py` | verdict stage consumes payload | ✓ WIRED | Same as above |
| `scripts/harrier_eval.py` | `personal_bench.py` | `preflight_adequacy` → `ensure_heldout(required_languages=('en','zh'))`, catches `HeldoutFloorError` | ✓ WIRED | `:703-729` |
| `scripts/harrier_eval.py` | artifact JSON | full run writes through `build_artifact`/`write_artifact`/`write_committed_artifact` | ✓ WIRED | `ARTIFACT_PATH`; raw comparison matches committed gates |
| `docs/benchmarking.md` | artifact JSON | section names artifact path and reproduces aggregate numbers | ✓ WIRED | Phrase `harrier-verdict.json` present; numbers match |
| `settings.py` | `embed/prompts.py` | known-model table maps Harrier to `web_search_query`, no document prompt | ✓ WIRED | Table row present (`prompts.py:29`); current default remains Qwen3 (non-flip) |
| `test_bench_snapshot.py` | `settings.py` | D-19 lock asserts live default | ✓ WIRED (non-flip) | Lock uses `DEFAULT_QWEN3_MODEL_NAME`/`DEFAULT_MODEL_TYPE` and asserts the Qwen3/prompt-free default; the flip-only `DEFAULT_MODEL_NAME` literal expected by the link text does not exist because the flip branch was not selected |
| `docs/benchmarking.md` | artifact JSON | evidence section names the authorizing artifact | ✓ WIRED | Present |
| `scripts/harrier_eval.py` | `embedding/identity.py` | proof records Qwen3 fingerprint and requires verified identity | ✓ WIRED | `read_identity` present; non-flip proof not run |
| `scripts/harrier_eval.py` | artifact JSON | `write_zero_delta_proof` extends `default_flip.zero_delta_proof` | ✓ WIRED (non-flip) | Artifact block present as `not-applicable`; writer is flip-only and intentionally absent |

## Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|--------------------|--------|
| `bench/harrier-verdict.json` `decision`/`rule` | `VerdictDecision` | `decide_from_payload(raw harrier-comparison.json)` | Yes — recomputed independently from the retained raw comparison; identical decision and 16-key rule | ✓ FLOWING |
| `gates.*` | comparison gate leaves | `ComparisonReport.to_dict()` from the real paired evaluation | Yes — raw `harrier-comparison.json` `overall`/`splits`/`legs`/`leg_splits`/`language_splits`/`leg_language_splits` compare exactly equal to the artifact | ✓ FLOWING |
| `arms.*.identity` | probe identity payload | `EmbeddingManager.get_identity()` + stored `index_meta` | Yes — both retained arm DBs' `embedder.identity` rows match the artifact fields and fingerprints | ✓ FLOWING |
| `arms.*.costs` | read-only DB/cache counts | `documents`/`document_chunks`/`embedded_documents` + cache bucket rows | Yes — arm DBs are 498/21,798/498; shared cache holds 21,342 modelscope-Qwen3 rows and 20,346 Harrier-revision rows, matching `cache_rows_after` | ✓ FLOWING |
| `corpus.adequacy` / `query_set_fingerprint` | preflight + saved-run hashes | `ensure_heldout(required_languages=('en','zh'))` + `query_set_fingerprint` | Yes — run-state adequacy en=42/zh=11/mixed=3, sampled 50; both saved runs hash to `b71a4be84d2a8724`; corpus fingerprints `b5d50ce0c696ab3d` | ✓ FLOWING |

## Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Phase 23 targeted tests | `env -u FORCE_COLOR NO_COLOR=1 pytest tests/unit/search/test_embedder_verdict.py tests/unit/search/test_personal_bench.py tests/unit/cli/test_eval.py tests/unit/scripts/test_harrier_eval.py -x --no-cov -q` | 329 passed in 19.48 s | ✓ PASS |
| Full suite + coverage gate | `env -u FORCE_COLOR NO_COLOR=1 pytest` | 3004 passed, 1 skipped, 95.13% coverage (gate 90%) in 186.87 s | ✓ PASS |
| Lint/format/type | `ruff check src tests`; `ruff format --check src tests`; `ruff check scripts`; `ruff format --check scripts`; `ty check src/sif` | All pass; 228 src/test files and 7 scripts formatted | ✓ PASS |
| Dry run without subprocess | `python scripts/harrier_eval.py --dry-run --corpus example-corpus` | Both arms, exact `-q --index` argv, pinned chunk/batch/token/ranking env, removed prompt/API keys | ✓ PASS |
| Verdict recomputation from committed artifact | `decide_from_payload({splits, language_splits})` against `bench/harrier-verdict.json` | `keep-qwen3`; 16-key `rule` identical | ✓ PASS |
| Verdict + gates from raw run evidence | `decide_from_payload(saved-runs/harrier-comparison.json)`; compare gate leaves | `keep-qwen3`; all gates byte-equal to artifact; top_k 10; replay false | ✓ PASS |
| Query-set/corpus fingerprints | `query_set_fingerprint` on both saved runs | Both `b71a4be84d2a8724`; corpus `b5d50ce0c696ab3d`; match artifact | ✓ PASS |
| Arm identity evidence | read `index_meta.embedder.identity` from both arm DBs | Both `source: verified`, 1024-dim, distinct fingerprints; Harrier `web_search_query` + revision `f9b9dc8d...`; Qwen3 prompt-free | ✓ PASS |
| Cache cost evidence | `SELECT model_id, COUNT(*) FROM embeddings GROUP BY model_id` (read-only) | Qwen3 bucket 21,342; Harrier bucket `...|rev@f9b9dc8d...` 20,346; match artifact `cache_rows_after` | ✓ PASS |

## Probe Execution

| Probe | Command | Result | Status |
|-------|---------|--------|--------|
| — | — | No probe scripts declared in any PLAN/SUMMARY; `find scripts -path '*/tests/probe-*.sh'` is empty | N/A |

## Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| MODEL-01 | 23-01, 23-03, 23-04 | Evidence-based EN+ZH held-out A/B; per-arm full re-embed; isolated indexes; per-language × per-leg verdict; paired deltas + intervals; Harrier query prompt `web_search_query`, never `default_prompt_name` | ✓ SATISFIED | Real two-arm DBs + saved runs + committed artifact; language/leg-language gates; Harrier identity prompt; docs evidence section |
| MODEL-02 | 23-02, 23-03, 23-04, 23-05, 23-06 | Default changes only on a proven EN+ZH win beyond the 0.01 tie rule; recorded rejection with numbers if no win; Qwen3 byte-identical until the gate passes | ✓ SATISFIED | Pure two-sided rule with boundary tests; `keep-qwen3` recorded with N/Δ/CI/floor/reasons; settings/EmbeddingConfig/prompts unchanged across the phase |

**Orphaned requirements:** None. REQUIREMENTS.md maps MODEL-01/02 to Phase 23 and marks both Complete; every plan declares at least one of the two IDs. No other requirement maps to Phase 23. MODEL-F1 (GGUF) remains a conditional future follow-up; no GGUF or bge-reranker arm exists in the runbook (only `qwen3` and `harrier` arms), consistent with locked decision "d".

## Decision Coverage

All 13 trackable CONTEXT.md decisions are honored by shipped artifacts (13/13, `not_honored: []`), per the decision-coverage gate. No decision drift found.

## Test Quality Audit

| Test File | Linked Req | Active | Skipped | Circular | Assertion Level | Verdict |
|-----------|-----------|--------|---------|----------|-----------------|---------|
| `tests/unit/search/test_embedder_verdict.py` | MODEL-02 | 20 | 0 | none | value + boundary + behavioral | ✓ PASS |
| `tests/unit/scripts/test_harrier_eval.py` | MODEL-01/02 | all | 1 platform-conditional symlink skip (not requirement-linked) | none | value + behavioral (stage machine, artifact, cleanup) | ✓ PASS |
| `tests/unit/search/test_personal_bench.py` | MODEL-01 | new cases active | 0 | none | value + behavioral | ✓ PASS |
| `tests/unit/cli/test_eval.py` | MODEL-01 | new cases active | 0 | none | behavioral (forwarding, warning) | ✓ PASS |

**Disabled tests on requirements:** 0. **Circular patterns detected:** 0. **Insufficient assertions:** 0. The real-run artifact's values were independently re-derived from the retained raw saved runs and arm DBs, so the evidence is not self-referential.

## Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `docs/benchmarking.md` | 278 | Says the Qwen3 saved run is retained "for plan 23-06's explicit-Qwen3 zero-delta proof", but the artifact records `zero_delta_proof: not-applicable` (open IN-05) | ℹ️ Info | Stale sentence; no must-have impact, no ranking claim affected |
| `scripts/harrier_eval.py` | cleanup | `cleanup_arms` leaves Harrier saved run/comparison JSON behind on a non-`--keep-arms` run (open IN-06) | ℹ️ Info | Files are under gitignored scratch and contain no committed data |
| `scripts/harrier_eval.py` | identity gate | Per-arm gate omits an explicit revision compare (open IN-02); revision is still matched by the probe's `check_identity` when both sides know it | ℹ️ Info | Auditable; the artifact records the actual revision |
| `src/sif/cli/commands/eval.py` | saved-run path | Saved-run path interpolated into Rich markup unescaped (open IN-01) | ℹ️ Info | Local path display only; not a goal blocker |
| `docs/benchmarking.md` | — | Phase 23 section does not mention `--require-language` (open IN-04) | ℹ️ Info | `docs/cli-reference.md` documents the flag; evidence doc completeness only |

No `TBD`/`FIXME`/`XXX` debt markers, no placeholder/stub implementations, and no hardcoded-empty data paths were found in any phase-modified file.

### Verification Debt (non-blocking)

- `23-VALIDATION.md` is still `status: draft`, `nyquist_compliant: false`, with the Validation Sign-Off unchecked, although the real-run and adequacy rows are recorded with the correct artifact/decision. This is a validation-process debt, not a must-have failure.
- No `23-SECURITY.md` exists; the per-plan STRIDE threat registers were implemented and the code review fixed 2 Critical + 6 Warning findings, but no standalone security audit artifact was produced.
- `.planning/tmp/phase-23/` contains a stale preliminary Qwen3 DB (6,213 documents, 8 collections including `Obsidian`, zero embeddings) from an earlier scope. The real evidence lives under `.planning/tmp/phase-23-zh-heavy/` and matches the artifact exactly. Both roots are gitignored; cleanup of the stale scratch is optional housekeeping.

## Human Verification Required

None. The plan's three blocking-human checkpoints (corpus scope/adequacy, real two-arm run, verdict review) were resolved and recorded; the adequacy and real-run outcomes are independently corroborated by retained arm DBs, saved runs, and cache rows. There is no visual, real-time, or external-service behavior left unverified, and no truth is present-but-behavior-unverified.

## Gaps Summary

No gaps. Both roadmap success criteria and all 31 plan must-have truths are verified.

The phase goal is achieved: the Phase 18 instrument was extended with per-language and per-leg-language held-out gates and language-aware widening; a pure two-sided rule implements the `adopt-harrier` gate (overall held-out winner + inclusive −0.01 per-language floor + N ≥ 10 per required language); the two-arm runbook builds isolated, identity-gated scratch arms, preflights EN+ZH adequacy before embedding, and writes the aggregate artifact; the real run on the approved 498-document curated bilingual scope recorded `keep-qwen3` with full numbers; and the non-flip branches of the conditional flip and zero-delta-proof plans are recorded as `not-applicable`. The default embedder remains Qwen3-Embedding-0.6B with a byte-identical prompt path, and no GGUF or bge-reranker arm was added.

The open Info findings and the validation/security artifact debt are recorded above; none affects goal achievement.

---

_Verified: 2026-11-16T15:28:15Z_
_Verifier: Claude (gsd-verifier)_
