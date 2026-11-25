# Phase 18 — UI Review

**Audited:** 2026-11-14
**Baseline:** No UI-SPEC.md — abstract 6-pillar standards adapted to a Click/Rich terminal interface. The phase delivered no frontend surface (no `.tsx`/`.jsx`/`.css`/`.vue`/`.html` files, no `components.json`), so the only user-facing surface audited is `sif eval` table/stderr/help/JSON output plus the unchanged `sif suggest` DYM surface.
**Screenshots:** not captured — no web UI exists for this phase. Ports 3000/5173 were closed; port 8080 answered but is an unrelated SearXNG instance, not a SIF surface. Real CLI renders were captured as text at 80/100/120 columns against a real 60-document fixture (fresh run, saved run, `--compare`, `--json`, `--help`, usage error).
**Interaction captures:** off (`workflow.ui_interaction_capture` false). CLI interaction states were verified manually instead: help, missing-flag usage error (exit 2), fresh run, auto-save, `--compare`, malformed-path error, and strict-JSON output.

**Scope note:** This phase is a Python CLI/library and evaluation instrument. Pillars that assume a rendered screen (breakpoints, icon buttons, font scales, 60/30/10 color distribution) are adapted to their terminal equivalents: table hierarchy and width responsiveness, Rich style semantics, terminal typography, layout density/rhythm, and CLI state coverage. The phase's own decisions D-01..D-17 and the plan acceptance criteria serve as the functional contract for copy and transparency findings.

---

## Pillar Scores

| Pillar | Score | Key Finding |
|--------|-------|-------------|
| 1. Copywriting | 3/4 | Specific, remedy-bearing copy throughout, but default table output truncates the disclosure notes at 80 chars and ships internal "(Plan 03)" and "D-12 gate input" jargon |
| 2. Visuals | 2/4 | The comparison per-group table is unreadable at 80 columns (headers and every metric value ellipsized); the headline metric and the decision-bearing held-out row get no emphasis |
| 3. Color | 3/4 | Restrained semantic styles and no color-only meaning, but green marks rejection/unavailable values and two tables drop the label/value distinction |
| 4. Typography | 3/4 | Consistent 4-decimal metrics and three-level hierarchy, but mixed NDCG/nDCG capitalization, raw lowercase `bm25`/`hybrid` labels, and an ellipsized header even at 120 columns |
| 5. Spacing | 2/4 | A 10-column group table overflows the canonical 80-column terminal, stacked tables have no vertical rhythm, and CI cells wrap at every width |
| 6. Experience Design | 3/4 | Strong error/empty/degraded states and clean stdout/stderr separation, but no progress feedback for a long run and a misleading `COMMAND [ARGS]...` usage line |

**Overall: 16/24**

---

## Top 3 Priority Fixes

1. **Disclosure notes are hard-truncated at 80 characters in table mode** — the default (non-JSON) report drops the binary known-item label semantics ("not a graded-relevance score"), the 0.60 Jaccard budget explanation, and "a fresh run has no baseline", weakening the trust contract this phase exists to build — stop routing `notes` through `_cell()` in `_render_footer`; print each note markup-escaped with normal Rich wrapping (or `soft_wrap=True`), and remove the `(Plan 03)` parenthetical (the post-review `Legs (D-12 gate input)` table title needs the same de-jargonizing).
2. **The comparison per-group table and the diagnostic label are unreadable at 80 columns** — at the canonical terminal/test width every header ("Lang…", "Base…", "Curr…", "Helpe…", "Winn…") and every metric value ("1.00…", "[0.0…") is ellipsized, and "Tuning (diagnostic)" becomes "Tuning (diagno…" — make the comparison output width-responsive (compact one-line-per-group layout below ~110 columns, spaces around "/" in headers so they can wrap, `overflow="fold"` or computed widths for numeric cells, or gate the diagnostic group table behind `--json`/`--verbose`); never ellipsize a number.
3. **`sif eval --help` advertises a nonexistent `COMMAND` and hides that `--personal` is required** — first-run users see `Usage: ... eval [OPTIONS] COMMAND [ARGS]...` with no command list, while `sif eval` without `--personal` exits 2; the generated docs say `sif eval [OPTIONS]` (docs/cli-reference.md:756-758), so help and docs disagree — use a plain Click command, or override the usage/help to state `--personal` is required (or add a real `sif eval personal` subcommand).

---

## Detailed Findings

### Pillar 1: Copywriting (3/4)

**WARNING — disclosure notes truncated at a fixed 80 characters.** `_render_footer` passes every note through `_cell()` (`src/sif/cli/commands/eval.py:355`; `_cell` at 95-99, cap `_CELL_MAX_LEN = 80`). Real 80- and 120-column captures show:
- `Known-item labels: the target document is grade 1 and all other documents gra...` — discards the 159-char note's required conclusion: "NDCG@10 is a rank-sensitive known-item metric, not a graded-relevance score" (note built at `eval.py:785-788`; D-04 requires the report to say so).
- `Title queries are exact-term (unbudgeted); body queries are paraphrased and r...` — discards the 0.60 Jaccard budget (note at `eval.py:789-791`; the per-leg table shows `Jaccard <= 0.60`, so this one is partly recoverable).
- `Replay stability against a saved baseline is computed by --compare (Plan 03);...` — discards "a fresh run has no baseline" (note at `eval.py:792-794`).
- `Embedding provider 'openai' is remote-capable: document titles, body-sentence...` — since the original review, WR-10 (`aea961c2`) lengthened the remote-provider note to 207 characters, so the table footer now keeps only the opening clause and drops the rest of the data list (replay query history) and the `--bm25-only keeps the run local` remedy (note at `eval.py:805-809`; rendered at HEAD from the module's own string, not a fixture run). The full disclosure still reaches stderr untruncated (`eval.py:236-243`) and JSON, so this widens the WARNING without changing its class.

This is the same class of defect Plan 02 explicitly fixed for `REPLAY_BIAS_NOTE` ("the 80-char cell cap previously hid the CLI-only half"), but the fix was applied only to `replay.bias`, not to `notes`. JSON output carries the full text, so this is a table-mode-only degradation — but table mode is the default human surface.

**WARNING — internal planning jargon in shipped copy.** The fresh-run footer and JSON say "computed by --compare (Plan 03)" (`src/sif/cli/commands/eval.py:792-793`). "Plan 03" is meaningless to a user; follow the `--compare` help wording instead. All other `Plan NN` references are docstrings, not output. Added since the original review (19-09, `f3bc9e7e`): the `--compare` table title `Legs (D-12 gate input)` (`eval.py:430`) ships a planning decision ID — Phase 19's per-leg acceptance gate, while in this phase's own CONTEXT "D-12" is the `--compare` entry point. Name it in user terms (e.g. "Per-leg gates (title-vs-body rule)") and move the test pin at `tests/unit/cli/test_eval.py:1818` with it.

**Minor — false stderr claim when no groups are suppressed.** `_comparison_context_table` unconditionally renders `Suppressed groups: {N} (names on stderr)` (`eval.py:510-513`). In the real comparison fixture this printed `0 (names on stderr)` while stderr contained no suppressed names. Render "none" when the list is empty.

**Minor — `Saved top_k` exposes the JSON schema key.** `eval.py:509` shows the raw field while the same concept is called "retrieval depth" in the compare warning (`eval.py:851`) and "Number of results per query" in `--limit` help (`eval.py:998-1004`). Use one human term.

**Minor — capitalization drift.** `NDCG@10` appears 15 times and `nDCG@10` 41 times across `src`, `docs`, and tests; the CLI tables/help use `NDCG@10` while docs prose uses `nDCG@10`.

**Pass — no generic labels.** No `Submit`/`OK`/`Cancel`/`No data`/`went wrong` placeholders in the phase surface. Every failure names its cause and a remedy: missing index, fewer than 50 documents, unsolvable held-out floor, missing embed backend, malformed saved run, fingerprint mismatch, and missing/ambiguous targets (`eval.py:661, 735-739, 747-754, 208-214, 672-675, 839-843`).

### Pillar 2: Visuals (2/4)

**WARNING — comparison per-group table fails at 80 columns.** `_comparison_groups_table` builds 10 columns (`eval.py:517-546`). Real 80-column capture:
```
┃       ┃       ┃       ┃    ┃ Base… ┃ Curr… ┃ Mean   ┃ 95%   ┃        ┃       ┃
┃ Leg   ┃ Lang… ┃ Leng… ┃ N  ┃ NDCG… ┃ NDCG… ┃ delta  ┃ CI    ┃ Helpe… ┃ Winn… ┃
│ title │ en    │ long  │ 50 │ 1.00… │ 1.00… │ +0.00… │ [0.0… │ 0/0/50 │ no    │
```
Every metric value is ellipsized; the EVAL-02 per-group diagnostic output is not readable in the default human mode at the standard width. At 100/120 columns it renders.

**WARNING — contract-bearing summary text is also lost at 80 columns.** `_comparison_summary_table` (`eval.py:380-425`) truncates the mandatory "Tuning (diagnostic)" label to "(diagno…" (D-07/T-18-10 require tuning and per-group gates to be labeled diagnostic) and "yes (improvement)" to "yes (impro…". With non-zero CI bounds the low bound is ellipsized (`[0.012…` in the synthetic render); the real all-1.0 fixture wraps `[0.0000,` / `0.0000]` onto two lines. The one number a reader needs to verify "CI excludes zero" is not guaranteed readable.

**Minor — no focal point.** The headline NDCG@10/Hit@10 are rows 4-5 of ten equal-weight rows in `_summary_table` (`eval.py:290-303`); counts such as "Documents" are equally prominent. In the comparison, the held-out row — the only gate allowed to warrant a defaults change — is visually identical to the diagnostic rows. A bold metric row or a small headline panel would establish hierarchy.

**Minor — inconsistent table styling.** `_summary_table`, `_legs_table`, and `_comparison_context_table` use cyan labels + green values; `_groups_table`, `_comparison_summary_table`, `_comparison_legs_table`, `_comparison_leg_splits_table`, and `_comparison_groups_table` style every column cyan (`eval.py:327, 393, 441, 470, 532`). Adjacent tables in one render switch visual systems.

**Pass — no icon-only affordances, clear table titles.** All eight tables carry a title; numeric values are right-aligned in the summary/context tables; every user/config-derived cell is truncated then `rich.markup.escape`d (T-18-01/T-18-06). I also verified that bracketed CI strings are not parsed as Rich markup (the first character after `[` is a digit or `-`).

### Pillar 3: Color (3/4)

**Minor — green is applied to non-success values.** `_summary_table` styles the Value column green (`eval.py:292`), including the three "Rejected (...)" counts; `_comparison_context_table` prints "Replay stability: unavailable" through the green Value column (`eval.py:489, 504`). Green conventionally signals success; rejected queries and unavailable measurements are neutral/negative states.

**Minor — no semantic emphasis on winner/regression.** `_winner_cell` returns plain text (`eval.py:371-377`) and the comparison tables style all cells cyan (`eval.py:393, 441, 470, 532`), so an improvement, a regression, and noise look identical apart from wording. Text-only signaling is accessible; color is simply unused where it would carry meaning.

**Minor — the label/value color distinction disappears in group tables.** `_groups_table` and `_comparison_groups_table` set `style="cyan"` for every column (`eval.py:327, 532`), unlike the other tables' cyan/green split.

**Pass — no hardcoded colors.** Style usage is semantic Rich style names only: 8 `cyan`, 8 `[yellow]`, 5 `[dim]`, 2 `green`; no hex/rgb values in the phase surface. Warnings/disclosures are consistently yellow on stderr; secondary notes are consistently dim.

**Pass — color is never the sole signal.** Winner/regression are words; warnings are prefixed text; stdout vs stderr is structural; `NO_COLOR` renders a complete, readable report.

### Pillar 4: Typography (3/4)

**Minor — `NDCG@10` vs `nDCG@10`.** 15 vs 41 occurrences across the repo; the CLI consistently uses the uppercase form while docs prose and the JSON-adjacent notes mix both. Pick the canonical metric spelling and apply it everywhere.

**Minor — raw machine enums in human labels.** `_render_footer` prints `Retrieval mode: bm25` (`eval.py:357`), the context table prints `saved bm25 / current bm25` (`eval.py:507`), and `_model_label` returns `no model (bm25)` (`eval.py:624`), while the surrounding prose says "BM25-only". Use a display-name map (`BM25`, `Hybrid`).

**Minor — non-wrappable header ellipsized even at 120 columns.** `Helped/Hurt/Unchanged` (`eval.py:390, 438, 529`) has no space to break at and renders as `Helped/Hurt/…` at 120 columns in a real capture; the 19-09 per-leg table repeats the header. Use `Helped / Hurt / Unchanged` (or a short `H/H/U` header plus a legend).

**Minor — `Saved top_k` field-name typography** (also a copy issue): mixing snake_case schema into a Title-Case human table (`eval.py:509`).

**Pass — numeric typography is consistent.** 4 decimals for nDCG/Hit/CI/noise floor; signed deltas (`+0.0000`); integer counts; aligned columns. Three-level hierarchy (bold table title/header, normal values, dim annotations) is coherent, with no arbitrary emphasis styles.

### Pillar 5: Spacing (2/4)

**WARNING — density exceeds the canonical terminal width.** The comparison summary has 8 columns and the diagnostic groups table has 10 (`eval.py:380-546`; the 19-09 per-leg gate table adds a second 8-column table, `eval.py:428-453`); at 80 columns Rich ellipsizes rather than reflowing. This is the CLI analog of a layout that does not respond at the smallest supported breakpoint.

**WARNING — no vertical rhythm.** `_render_personal` and `_render_comparison` print each table back-to-back with no blank line, and the note block starts immediately below the last table (`eval.py:549-589`). A comparison now stacks up to five tables (two more since 19-09) and reads as a single wall of box-drawing characters; one blank line between sections would restore grouping.

**Minor — CI cells wrap at every width.** The 95% CI column is too narrow, so `[0.0000, 0.0000]` breaks across two lines even at 120 columns (real captures at 80/100/120). Every comparison and group row is consequently two lines tall.

**Pass — spacing values are consistent.** Rich default table padding is used throughout; no arbitrary padding overrides or ad-hoc blank-line counts; `soft_wrap=True` correctly prevents saved paths and long warnings from wrapping (`eval.py:617, 641, 649, 654, 853, 860, 935, 941`).

### Pillar 6: Experience Design (3/4)

**WARNING — no progress feedback for a potentially long measurement.** `run_personal` loads the embedder (a model load can download/initialize) and then runs up to 500 known-item searches plus up to 500 replay searches with no spinner, count, or ETA (`eval.py:721-822, 825-891`). Default INFO logging emits "Loading embedding model: ..." (`src/sif/embedding/manager.py:104`) and then the search phase is silent. The repository already provides `ProgressTracker`/`RichProgressTracker` (`src/sif/utils/progress.py:41-101`) but eval does not use it.

**WARNING — misleading command affordance.** `eval` is a `@click.group(..., invoke_without_command=True)` with no subcommands (`eval.py:981-1078`). `sif eval --help` therefore prints `Usage: ... eval [OPTIONS] COMMAND [ARGS]...` with no Commands section, and `--personal` is rendered as optional even though `sif eval` exits 2 with "Error: --personal is required" (verified). The generated docs render `sif eval [OPTIONS]` (`docs/cli-reference.md:756-758`), so the two surfaces disagree.

**Minor — saved path is not markup-escaped.** `console_err.print(f"[dim]Saved run: {path}[/dim]", soft_wrap=True)` (`eval.py:617`) does not `escape()` the path. A cache directory containing markup-like brackets (e.g. `/tmp/[bold]evil[/bold]/…`) renders with the brackets swallowed, so the path the user copies is wrong. Every other user/config-derived cell follows the truncate-then-escape convention (T-18-01/T-18-06); this is an outlier.

**Pass — error states are loud, named, and traceback-free.** Verified: missing index, <50 documents, missing embed backend, unsolvable held-out floor, malformed saved run, fingerprint mismatch, missing/ambiguous target, and Click usage errors all exit non-zero with cause + remedy and no traceback.

**Pass — empty/degraded states are explicit.** Empty `query_log` yields `replay.available: false`, `num_queries: 0`, a bias note, and exit 0; no qualifying groups yields `No leg x language x length group reached the N >= 10 floor`; suppressed groups are named; replay-unavailable is warned on stderr (`eval.py:494-514, 560-563, 651-655`).

**Pass — transparent, safe interaction.** Auto-save is announced on stderr only (and exposed as `run_path` in JSON), `--no-save` opts out, compare-mode depth/mode/model mismatches are surfaced on stderr, and stdout remains strict-JSON-clean (verified with `json.load`). No destructive action is taken without an explicit flag.

**Pass — accessibility.** Color is not the only carrier of meaning; the report is complete under `NO_COLOR`; stdout/stderr separation keeps machine output clean.

---

## Minor Recommendations (not in top 3)

1. Render `Suppressed groups: none` (or omit the stderr parenthetical) when the suppressed list is empty (`eval.py:510-513`).
2. Rename the human label `Saved top_k` to "Retrieval depth" (`eval.py:509`).
3. Standardize on `nDCG@10` (or `NDCG@10`) across CLI, JSON notes, and docs.
4. Map retrieval enums to display names (`BM25`, `Hybrid`) in human-facing text (`eval.py:357, 507, 624`).
5. Make the `Helped / Hurt / Unchanged` header wrappable (spaces around `/`) or use `H/H/U` plus a legend (`eval.py:390, 438, 529`).
6. Replace "unavailable" and rejection-count green with a neutral style; use a semantic style for winner/regression and unify the cyan/green split across tables (`eval.py:292, 327, 393, 441, 470, 489, 504, 532`).
7. Add one blank line between tables and before the note block (`eval.py:549-589`).
8. Add progress/count feedback for the search loop (reuse `ProgressTracker`) (`eval.py:721-822`).
9. `escape()` the saved-run path before printing it (`eval.py:617`).
10. Emphasize the headline NDCG@10/Hit@10 rows and visually distinguish the held-out gate from diagnostic rows (`eval.py:290-303, 394-425`).

---

## Files Audited

- `src/sif/cli/commands/eval.py` — all Rich tables, stderr warnings, help text, JSON payload assembly (816 lines read in full; re-audited 2026-11-25 against `a5bd186`, now 1078 lines, read in full: every line citation refreshed, `sif eval --help` and the usage error re-run live, table and footer renders re-verified at 80/100/120 columns by feeding synthetic payloads to the renderers instead of re-running the fixture, everything else re-checked by source reading).
- `src/sif/search/personal_bench.py` — `PersonalReport`, `GroupMetrics`, `GateResult`, `ComparisonReport`, `ReplayResult` serialization and the notes passed to the CLI; user-facing note strings.
- `src/sif/search/suggest.py` — `_DYM_CUTOFF` and `_close_matches` (QUAL-01); confirmed no new output surface.
- `src/sif/cli/main.py` — `eval_group` registration.
- `src/sif/cli/commands/bench.py` — output-convention comparison baseline.
- `docs/cli-reference.md` — generated `sif eval` section and usage line.
- `docs/benchmarking.md` — personal-bench narrative (legs, split, saved runs, noise gate, replay, comparability).
- `docs/architecture.md` — DYM and `PersonalBench` narrative.
- `tests/unit/cli/test_eval.py` — rendering/JSON assertions, including the 80-column table expectations.
- `tests/unit/search/test_personal_bench.py` — report/gate payload contract.
- Live CLI captures: `sif eval --help`; `sif eval` usage error; `sif eval --personal --bm25-only --no-save` at 80 and 120 columns; `sif eval --personal --bm25-only --compare <saved>` at 80/100/120 columns; `--json` fresh and comparison runs (strict-parse verified).
