# Phase 23 — UI Review

**Audited:** 2026-11-18
**Baseline:** No UI-SPEC.md — abstract 6-pillar standards adapted to a Click/Rich + stdlib terminal interface. No web frontend exists (no `.tsx`/`.jsx`/`.css` in the phase; no `components.json`). The contract for this phase is the plan must-haves (23-01..23-06), decisions D-01..D-13 in `23-CONTEXT.md`, and the Phase 19 adapted terminal-audit precedent. Audited surface: `sif eval --compare` text tables and JSON, `--require-language` / `--min-heldout` help and errors, the compare-mode stderr warning, `scripts/harrier_eval.py` help/dry-run/guard/outcome lines, the committed `bench/harrier-verdict.json`, and the Phase 23 `docs/benchmarking.md` section.
**Screenshots:** not captured — no web UI exists. Ports 3000 and 5173 were closed; port 8080 answered 200 but serves an unrelated SearXNG 2026.11.1 page, not a SIF surface. No browser capture was attempted. Visual pillars were scored on real CLI text renders at 80/100/120 columns (`/tmp/23-ui-captures/`).
**Interaction captures:** off (`workflow.ui_interaction_capture` false). CLI states were exercised manually instead: `sif eval --help` at 80/100/120; `--require-language fr` rejection; the real phase-23 comparison payload rendered through the production table functions at 80/100/120; `harrier_eval.py --help` at 80/100; `--dry-run --json`; duplicate-corpus-root refusal. The compare-mode stderr warning was verified from source (`eval.py:930-934`), not captured live: the retained 23-04 scratch saved-run directory (`.planning/tmp/phase-23/saved-runs/`) is empty, so there is no live saved-run/DB pair for that exact scope. That absence is itself finding C-2.

**Scope note:** Pillars that assume a rendered screen (breakpoints, icon buttons, font scales, 60/30/10 color) are adapted to terminal equivalents: table hierarchy and width responsiveness, Rich style semantics, terminal typography, layout density/rhythm, and CLI state coverage. Pre-existing defects that Phase 23 did not change (e.g. `Tuning (diagno…)` truncation, `Helped/H…` headers, table wrapping at 80, all-cyan comparison tables) are recorded as carried-forward context, not re-scored as new findings.

**Registry audit:** skipped — no `components.json` (not a shadcn/frontend project).

---

## Pillar Scores

| Pillar | Score | Key Finding |
|--------|-------|-------------|
| 1. Copywriting | 2/4 | The runbook's only human outcome line says `PASS decision=keep-qwen3`; `SHORT insufficient-evidence` is jargon and neither line gives the reasons. Phase 23's benchmark docs still promise a retained pre-flip saved run for a zero-delta proof that was recorded `not-applicable`. |
| 2. Visuals | 2/4 | `sif eval --compare` never renders the new per-language or leg × language gates; the phase's central EN+ZH evidence has no visual surface in the default human mode. The verdict artifact leads with Harrier costs and buries `decision` at line 81 of 645. |
| 3. Color | 3/4 | No hardcoded colors; the compare-mode warning is semantic yellow and `NO_COLOR` renders a complete report. The new language evidence has no visual encoding because it is not rendered at all. |
| 4. Typography | 3/4 | Help wraps cleanly at 80 (max 78 columns) and runbook help at 80/100; but the artifact stores full float precision while docs round, and the new docs repeat `nDCG@10` against the CLI's `NDCG@10`. |
| 5. Spacing | 3/4 | No new tables or arbitrary spacing, but the runbook's 131/134-character outcome line soft-wraps mid-path at the canonical 80 columns (`harrier-gated-` / `evaluation`). |
| 6. Experience Design | 2/4 | The two-sided EN+ZH rule is computable only from `--json`/the artifact; a successful `--require-language` fresh run confirms no per-language counts, and the runbook's success word is ambiguous. Guard/validation/exit-code behavior is otherwise strong. |

**Overall: 15/24**

---

## Top 3 Priority Fixes

1. **The runbook's only human-readable result line is ambiguous and wraps mid-path** — `scripts/harrier_eval.py:1784` prints `PASS decision=keep-qwen3 artifact=<abs path>` (131 chars; 134 for the `SHORT` variant at `:1738`). At 80 columns it wraps between `harrier-gated-` and `evaluation`, and `PASS` reads as "the candidate passed" even when the decision is a rejection. A user can run a multi-hour evaluation and get one word that contradicts the verdict. Replace both lines with a short block on separate lines: decision (`keep-qwen3`), the named rule reasons, per-language held-out N/delta, and the artifact path on its own line; rename `PASS`/`SHORT` to outcome words that cannot be misread (`VERDICT`, `INSUFFICIENT EVIDENCE`).
2. **`sif eval --compare` text output omits the per-language and leg × language gates entirely** — `_render_comparison` (`src/sif/cli/commands/eval.py:549-564`) prints summary, legs, leg × split, context, and groups only; `language_splits` and `leg_language_splits` are serialized in JSON (`personal_bench.py:531-543`) but have no table and no reference anywhere in `eval.py`. The real phase-23 payload carries `en`/`zh`/`mixed` held-out gates, yet the default human mode shows none of them, so the two-sided rule that justified `keep-qwen3` is invisible without `--json` and manual arithmetic. Add a compact "Required-language held-out" table (language, N, baseline→current, delta, CI, floor, winner) and state the two-sided rule booleans next to the held-out row.
3. **The human summary of the verdict is buried in the artifact and stale in the docs** — the committed artifact is written with `sort_keys=True` (`harrier_eval.py:520-529`), so it opens with `arms`/Harrier costs, puts `decision` at line 81 of 645, and puts `rule`/`reasons` at line 612; the documented envelope order (`version`, `decision`, `rule`, …) is not what a reader sees. Meanwhile `docs/benchmarking.md:278` still says the Qwen3 pre-flip saved run "is retained locally … for plan 23-06's explicit-Qwen3 zero-delta proof", but 23-06 recorded `default_flip.zero_delta_proof: {status: "not-applicable"}` and `.planning/tmp/phase-23/saved-runs/` is empty; the docs never mention `default_flip` or the not-applicable proof at all. Write the artifact in the documented order (or add a `summary` block at the top) and correct the docs sentence to record the `keep-qwen3` → no flip → not-applicable proof outcome so readers are not sent after evidence that does not exist.

---

## Detailed Findings

### Pillar 1: Copywriting (2/4)

**WARNING — `PASS decision=keep-qwen3` contradicts itself.** `scripts/harrier_eval.py:1784` prints the success word `PASS` for every completed run, including a rejection. The decision token is correct, but the leading word asserts the opposite outcome. A reader skimming the last line of a multi-hour run can conclude Harrier passed. The insufficient path (`:1738`) is worse: `SHORT insufficient-evidence artifact=…` uses an unexplained abbreviation as the outcome label. Fix both labels and add the rule reasons that are already computed (`VerdictDecision.reasons`, `embedder_verdict.py:122-149, 198-211`).

**WARNING — the Phase 23 benchmark section documents evidence that no longer exists.** `docs/benchmarking.md:278` states the Qwen3 pre-flip saved run is retained for plan 23-06's explicit-Qwen3 zero-delta proof. Plan 23-06 completed with `default_flip.zero_delta_proof: {"status": "not-applicable"}` (artifact lines 83-88) and the 23-04 scratch saved-run directory is empty. `grep -c "default_flip\|zero_delta" docs/benchmarking.md` is 0, so the human evidence section never records the final not-applicable outcome. This is the phase's human-readable summary; it should end with the flip/proof disposition.

**WARNING — the counted widening error names counts but not the rule or the flag.** `personal_bench.py:1165-1179` raises a message ending `held-out by language en=<n>, zh=<n>. Index more documents with 'sif index update' and retry.` It never says which languages were requested, that each needs at least 10 held-out queries, or that `--require-language` caused the widening. A user who sees `zh=6` has to remember the help text to know why 6 is a failure. Name the requirement (`--require-language needs ≥10 held-out per language`) in the message.

**Minor — `mixed` is a first-class required language.** `LANGUAGES` includes `mixed` (`personal_bench.py:53`), so `--require-language mixed` is accepted and the help/error/artifact treat it like `en`/`zh`, while the two-sided verdict only requires `en` and `zh` (`embedder_verdict.py:157`). The flag is a sampling instrument, so accepting `mixed` is defensible, but the option help and docs should say mixed is diagnostic for the verdict.

**Pass — the new flag copy is otherwise specific and accurate.** `--require-language` help names the 10-query floor and repeatability (`eval.py:1007-1017`), the long description explains the compare-mode ignore (`eval.py:1057-1059`), the generated reference matches (`docs/cli-reference.md:770-771`), the compare-mode warning names the flag and the saved query set (`eval.py:930-934`), and the corpus guard names the offending root (`REFUSED: duplicate corpus root: …`, exit 2). No generic `Submit`/`No data`/`went wrong` placeholders appear on the phase surface.

### Pillar 2: Visuals (2/4)

**WARNING — the new evidence has no table or row in the primary human renderer.** The real phase-23 comparison payload contains `language_splits` = `{en, mixed, zh}` with tuning/held-out gates and `leg_language_splits` = `{title, body}`, but `_render_comparison` (`eval.py:549-564`) renders only summary, legs, leg × split, context, and groups. There is no "language" table and no mention of the required-language rule. At 80/100/120 columns the per-language held-out deltas (`en +0.0138`, `zh -0.0049`) that decided the verdict are nowhere on screen. The JSON path is correct and complete; the human path is not.

**WARNING the verdict artifact's focal point is buried.** `write_json` sorts keys (`harrier_eval.py:520-529`), so `harrier-verdict.json` opens with `arms` → Harrier costs; `decision` is at line 81 of 645 and `rule` (the actual reasoning) at line 612. The documented envelope order from 23-03/23-04 (`version`, `decision`, `rule`, `arms`, `corpus`, …) is not what the file shows, and the 23-03 summary's "emits the documented key order" claim describes `build_artifact`, not the written file. For an aggregate artifact meant to be audited, the decision and reasons should lead.

**Minor — the sole runbook result is a single 131-character line.** At 80 columns it wraps inside the artifact path; the reader sees a broken path fragment on the last line of output. Put the path on its own line and the decision/reasons above it.

**Pass — the surviving comparison tables keep a consistent structure.** Columns are right-aligned, tables have titles, and the leg × split table correctly exposes `Sufficient` (a Phase 19 fix), so an under-floor gate is not rendered as a valid one. Carried forward, not re-scored: the 8-column summary still ellipsizes `Tuning (diagno…)` and `Helped/H…` at 80/100, and the groups table still ellipsizes every metric at 80 (`eval.py:380-546`); Phase 23 did not change these.

### Pillar 3: Color (3/4)

**Pass — semantic styles only, no hardcoded colors.** The phase files contain no hex/rgb literals; the compare-mode warning is `[yellow]` (`eval.py:930-934`), notes are `[dim]`, and the comparison tables keep the established cyan palette. All captures were made under `NO_COLOR=1` and the report is complete and readable, so no meaning is carried by color alone.

**Minor — the new language evidence gets no semantic emphasis because it is not rendered.** If a language table is added (top fix #2), use the existing label/value split and a text-backed winner/floor marker rather than a new palette entry; the all-cyan comparison tables already lose the winner/regression distinction.

**Minor — carried forward, not new:** the comparison summary/legs tables remain all-cyan (`eval.py:393, 441`) while the context table uses cyan labels/green values (`:488-489`), so adjacent tables in one render switch visual systems. Phase 23 did not change these.

### Pillar 4: Typography (3/4)

**Minor — the artifact mixes float precisions.** `rule.language_mean_deltas` stores full float precision (`0.013848238095238094`) while `docs/benchmarking.md` rounds to 6 and the tables to 4 decimals. Machine JSON tolerates this, but the artifact is the audit record; rounding the display values (and keeping full precision under a separate raw field) would make the summary legible.

**Minor — new docs repeat the `nDCG@10` spelling.** `docs/benchmarking.md:280-298` uses `nDCG@10` in the Phase 23 tables while the CLI consistently prints `NDCG@10` (`eval.py:383-390, 431-440`). This is a new occurrence in new text, even though the inconsistency predates the phase.

**Minor — carried forward, not new:** `Leg x split gates` (`eval.py:460`) and `leg x language x length` (`:562`) use ASCII `x` instead of `×`; the new benchmark tables correctly use `×`, so the two surfaces still disagree.

**Pass — width behavior is clean where the phase added copy.** `sif eval --help` wraps at 78 columns for all of 80/100/120, the new option block is aligned, the invalid-choice error is a single readable line, and the runbook help wraps correctly at 80/100.

### Pillar 5: Spacing (3/4)

**WARNING — the new outcome line does not respond to the canonical width.** The success/short lines are 131/134 characters (`harrier_eval.py:1738, 1784`); at 80 columns the path breaks after `harrier-gated-`, splitting a hyphenated directory name. This is the terminal analog of a component that overflows its smallest breakpoint. Use one field per line.

**Minor — the artifact's sorted-key layout destroys block rhythm.** Related evidence (`arms`, `corpus`, `decision`, `default_flip`, …) is alphabetical, not ordered by the reading task; `version` lands last. The JSON is valid either way, but a reader scanning for the verdict sees costs first and reasons last.

**Pass — no new tables or arbitrary spacing.** Phase 23 added no Rich tables and no padding overrides; the only new multiline surfaces are help and argparse output, both of which use standard wrapping. Carried forward, not re-scored: `_render_comparison` still prints its tables back-to-back with no blank line (`eval.py:552-559`).

### Pillar 6: Experience Design (2/4)

**WARNING — the default human mode cannot verify the two-sided rule.** `sif eval --compare` exposes `language_splits` only in JSON; a successful fresh `--require-language` run shows no per-language held-out counts in either the summary or groups table (the report has totals and suppressed group names, not language totals). The widening floor is therefore observable only on failure (`HeldoutFloorError`) or through the runbook's `--preflight-only`. For a phase whose acceptance criterion is "each required language has ≥10 held-out queries", the success state is silent about the thing that was checked.

**WARNING — the runbook's success/insufficient states are not distinguishable at a glance.** `PASS decision=keep-qwen3` and `SHORT insufficient-evidence` are the only terminal outcomes; neither states the rule reasons, the per-language evidence, or the next action (open the artifact, do not flip the default). The artifact and docs carry this information, but the terminal does not.

**Minor — destructive `--force` is not described as discarding the prior proof.** `write_committed_artifact` intentionally drops `default_flip`/`zero_delta_proof` on a forced replacement (`harrier_eval.py:1007-1035`), but the `--force` help (`:1823-1829`) says only that the artifact is overwritten. Add "the prior `default_flip`/proof block is discarded."

**Minor — the docs promise a proof path that was resolved as not-applicable.** Same evidence as C-2; from the experience side it is a dead end for a reader following the Phase 23 narrative.

**Pass — the new interaction/guard states are otherwise strong.** `--require-language` is `click.Choice`-validated and rejects `fr` with the valid set (exit 2); compare mode emits exactly one stderr warning and keeps stdout JSON clean; the warning names the flag and the saved-set rationale; `HeldoutFloorError` carries structured counts and subclasses `ValueError`, preserving the CLI translation; the runbook refuses duplicate/nested corpus roots before building commands (one line, exit 2), uses scope-keyed resumable stages, refuses inadequate corpora before the embed budget (exit 3), and guards artifact replacement with a named `--force` remedy.

---

## Minor Recommendations (not in top 3)

1. Name the required-language floor and the flag in `HeldoutFloorError` (`personal_bench.py:1165-1179`).
2. State in the `--require-language` help/docs that `mixed` is diagnostic for the verdict, or exclude it from the choice (`personal_bench.py:53`; `docs/cli-reference.md:770`).
3. Add a per-language held-out table (or a compact required-language summary line) to `_render_comparison` (`eval.py:549-564`).
4. Render the two-sided rule result in the comparison footer/context when required-language evidence is present (e.g. `Required languages: en 42, zh 11 · floor ok · overall winner no`).
5. Print the runbook result as multiple lines and put the artifact path on its own line (`harrier_eval.py:1738, 1784`).
6. Write the artifact in documented envelope order, or add a leading `summary` block with decision, reasons, and required-language evidence (`harrier_eval.py:520-529`).
7. Correct `docs/benchmarking.md:278` and add the `default_flip` / `zero_delta_proof: not-applicable` outcome to the Phase 23 section (`docs/benchmarking.md`, currently 0 mentions).
8. Round display floats in the artifact's `rule` block while retaining raw values separately.
9. Unify `NDCG@10` / `nDCG@10` and `×` / `x` across the new docs and CLI tables.
10. Document `--preflight-only` output and the 0/1/2/3 exit codes in the runbook `--help` (`harrier_eval.py:1792-1836`).
11. Document that `--force` discards the prior `default_flip`/`zero_delta_proof` block (`harrier_eval.py:1007-1035, 1823-1829`).
12. Consider a `sif eval verdict --compare <payload>` (or a `--verdict` flag) so the two-sided rule is a first-class CLI output rather than a runbook-only policy; today `embedder_verdict.decide_from_payload` has no user-facing CLI entry point.

---

## Files Audited

- `src/sif/cli/commands/eval.py` — `--require-language` option/threading and compare-mode warning (`:930-934`, `:1007-1017`); comparison summary/legs/leg-split/context/groups renderers (`:380-546`); `_render_comparison` (`:549-564`).
- `src/sif/search/personal_bench.py` — `LANGUAGES` (`:53`); `HeldoutFloorError` and `heldout_language_counts` (`:1042-1082`); `ensure_heldout(required_languages=…)` and the counted error (`:1115-1184`); `language_noise_gates` / `leg_language_noise_gates`; `ComparisonReport.language_splits` / `leg_language_splits` and `to_dict` (`:495-543`).
- `src/sif/search/embedder_verdict.py` — decision constants, `VerdictDecision.to_dict`, reasons, `decide_from_gates` / `decide` / `decide_from_payload`.
- `scripts/harrier_eval.py` — argparse help (`:1792-1836`); `write_json`/`write_committed_artifact` (`:520-529`, `:1000-1035`); preflight/insufficient and success output (`:1725-1738`, `:1780-1786`); corpus-root guard and stage machine.
- `.planning/phases/23-harrier-gated-evaluation/bench/harrier-verdict.json` — envelope, `decision` (line 81), `default_flip` (lines 83-88), `rule` (line 612), 645 lines.
- `docs/benchmarking.md` — `## Embedder Substitution Evidence` / `### Harrier gated evaluation (Phase 23)` (lines 259-319; stale retained-run claim at 278).
- `docs/cli-reference.md` — generated `sif eval` rows (`:748-771`).
- `.planning/phases/23-harrier-gated-evaluation/23-01-PLAN.md` … `23-06-PLAN.md` and `23-01-SUMMARY.md` … `23-06-SUMMARY.md` — must-haves, acceptance criteria, recorded outcomes.
- `.planning/phases/23-harrier-gated-evaluation/23-CONTEXT.md` — D-01..D-13 (contract for the verdict and privacy).
- `.planning/phases/19-search-correctness/19-UI-REVIEW.md` — adapted terminal pillar precedent and carried-forward findings.
- Text captures: `/tmp/23-ui-captures/compare_real.txt` (real phase-23 comparison payload rendered through production tables at 80/100/120), `eval-help-80|100|120.txt`, `runbook-help-80|100.txt`, `runbook-dryrun.json`, `guard.err`.
- Live inputs: `.planning/tmp/phase-23-zh-heavy/saved-runs/harrier-comparison.json` (real comparison payload matching the committed numbers: overall n=99, held-out n=56, en=42/zh=11/mixed=3), `.planning/tmp/phase-23/saved-runs/` (empty), `.planning/tmp/phase-23/qwen3.db` (retained baseline arm, 112 MB).
