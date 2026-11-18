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
| 1. Copywriting | 3/4 | Specific, remedy-bearing copy throughout, but default table output truncates the disclosure notes at 80 chars and ships internal "(Plan 03)" jargon |
| 2. Visuals | 2/4 | The comparison per-group table is unreadable at 80 columns (headers and every metric value ellipsized); the headline metric and the decision-bearing held-out row get no emphasis |
| 3. Color | 3/4 | Restrained semantic styles and no color-only meaning, but green marks rejection/unavailable values and two tables drop the label/value distinction |
| 4. Typography | 3/4 | Consistent 4-decimal metrics and three-level hierarchy, but mixed NDCG/nDCG capitalization, raw lowercase `bm25`/`hybrid` labels, and an ellipsized header even at 120 columns |
| 5. Spacing | 2/4 | A 10-column group table overflows the canonical 80-column terminal, stacked tables have no vertical rhythm, and CI cells wrap at every width |
| 6. Experience Design | 3/4 | Strong error/empty/degraded states and clean stdout/stderr separation, but no progress feedback for a long run and a misleading `COMMAND [ARGS]...` usage line |

**Overall: 16/24**

---

## Top 3 Priority Fixes

1. **Disclosure notes are hard-truncated at 80 characters in table mode** — the default (non-JSON) report drops the binary known-item label semantics ("not a graded-relevance score"), the 0.60 Jaccard budget explanation, and "a fresh run has no baseline", weakening the trust contract this phase exists to build — stop routing `notes` through `_cell()` in `_render_footer`; print each note markup-escaped with normal Rich wrapping (or `soft_wrap=True`), and remove the `(Plan 03)` parenthetical.
2. **The comparison per-group table and the diagnostic label are unreadable at 80 columns** — at the canonical terminal/test width every header ("Lang…", "Base…", "Curr…", "Helpe…", "Winn…") and every metric value ("1.00…", "[0.0…") is ellipsized, and "Tuning (diagnostic)" becomes "Tuning (diagno…" — make the comparison output width-responsive (compact one-line-per-group layout below ~110 columns, spaces around "/" in headers so they can wrap, `overflow="fold"` or computed widths for numeric cells, or gate the diagnostic group table behind `--json`/`--verbose`); never ellipsize a number.
3. **`sif eval --help` advertises a nonexistent `COMMAND` and hides that `--personal` is required** — first-run users see `Usage: ... eval [OPTIONS] COMMAND [ARGS]...` with no command list, while `sif eval` without `--personal` exits 2; the generated docs say `sif eval [OPTIONS]` (docs/cli-reference.md:638-640), so help and docs disagree — use a plain Click command, or override the usage/help to state `--personal` is required (or add a real `sif eval personal` subcommand).

---

## Detailed Findings

### Pillar 1: Copywriting (3/4)

**WARNING — disclosure notes truncated at a fixed 80 characters.** `_render_footer` passes every note through `_cell()` (`src/sif/cli/commands/eval.py:256`; `_cell` at 80-84, cap `_CELL_MAX_LEN = 80`). Real 80- and 120-column captures show:
- `Known-item labels: the target document is grade 1 and all other documents gra…` — discards the 159-char note's required conclusion: "NDCG@10 is a rank-sensitive known-item metric, not a graded-relevance score" (note built at `eval.py:590-593`; D-04 requires the report to say so).
- `Title queries are exact-term (unbudgeted); body queries are paraphrased and r…` — discards the 0.60 Jaccard budget (note at `eval.py:594-596`; the per-leg table shows `Jaccard <= 0.60`, so this one is partly recoverable).
- `Replay stability against a saved baseline is computed by --compare (Plan 03);…` — discards "a fresh run has no baseline" (note at `eval.py:597-599`).

This is the same class of defect Plan 02 explicitly fixed for `REPLAY_BIAS_NOTE` ("the 80-char cell cap previously hid the CLI-only half"), but the fix was applied only to `replay.bias`, not to `notes`. JSON output carries the full text, so this is a table-mode-only degradation — but table mode is the default human surface.

**WARNING — internal planning jargon in shipped copy.** The fresh-run footer and JSON say "computed by --compare (Plan 03)" (`src/sif/cli/commands/eval.py:597-598`). "Plan 03" is meaningless to a user; follow the `--compare` help wording instead. All other `Plan NN` references are docstrings, not output.

**Minor — false stderr claim when no groups are suppressed.** `_comparison_context_table` unconditionally renders `Suppressed groups: {N} (names on stderr)` (`eval.py:354-357`). In the real comparison fixture this printed `0 (names on stderr)` while stderr contained no suppressed names. Render "none" when the list is empty.

**Minor — `Saved top_k` exposes the JSON schema key.** `eval.py:353` shows the raw field while the same concept is called "retrieval depth" in the compare warning (`eval.py:650`) and "Number of results per query" in `--limit` help (`eval.py:773`). Use one human term.

**Minor — capitalization drift.** `NDCG@10` appears 13 times and `nDCG@10` 25 times across `src`, `docs`, and tests; the CLI tables/help use `NDCG@10` while docs prose uses `nDCG@10`.

**Pass — no generic labels.** No `Submit`/`OK`/`Cancel`/`No data`/`went wrong` placeholders in the phase surface. Every failure names its cause and a remedy: missing index, fewer than 50 documents, unsolvable held-out floor, missing embed backend, malformed saved run, fingerprint mismatch, and missing/ambiguous targets (`eval.py:499, 559-563, 567-569, 151-157, 510-513, 640-644`).

### Pillar 2: Visuals (2/4)

**WARNING — comparison per-group table fails at 80 columns.** `_comparison_groups_table` builds 10 columns (`eval.py:361-390`). Real 80-column capture:
```
┃       ┃       ┃       ┃    ┃ Base… ┃ Curr… ┃ Mean   ┃ 95%   ┃        ┃       ┃
┃ Leg   ┃ Lang… ┃ Leng… ┃ N  ┃ NDCG… ┃ NDCG… ┃ delta  ┃ CI    ┃ Helpe… ┃ Winn… ┃
│ title │ en    │ long  │ 50 │ 1.00… │ 1.00… │ +0.00… │ [0.0… │ 0/0/50 │ no    │
```
Every metric value is ellipsized; the EVAL-02 per-group diagnostic output is not readable in the default human mode at the standard width. At 100/120 columns it renders.

**WARNING — contract-bearing summary text is also lost at 80 columns.** `_comparison_summary_table` (`eval.py:281-326`) truncates the mandatory "Tuning (diagnostic)" label to "(diagno…" (D-07/T-18-10 require tuning and per-group gates to be labeled diagnostic) and "yes (improvement)" to "yes (impro…". With non-zero CI bounds the low bound is ellipsized (`[0.012…` in the synthetic render); the real all-1.0 fixture wraps `[0.0000,` / `0.0000]` onto two lines. The one number a reader needs to verify "CI excludes zero" is not guaranteed readable.

**Minor — no focal point.** The headline NDCG@10/Hit@10 are rows 4-5 of ten equal-weight rows in `_summary_table` (`eval.py:191-204`); counts such as "Documents" are equally prominent. In the comparison, the held-out row — the only gate allowed to warrant a defaults change — is visually identical to the diagnostic rows. A bold metric row or a small headline panel would establish hierarchy.

**Minor — inconsistent table styling.** `_summary_table`, `_legs_table`, and `_comparison_context_table` use cyan labels + green values; `_groups_table`, `_comparison_summary_table`, and `_comparison_groups_table` style every column cyan (`eval.py:228, 294, 376`). Adjacent tables in one render switch visual systems.

**Pass — no icon-only affordances, clear table titles.** All six tables carry a title; numeric values are right-aligned in the summary/context tables; every user/config-derived cell is truncated then `rich.markup.escape`d (T-18-01/T-18-06). I also verified that bracketed CI strings are not parsed as Rich markup (the first character after `[` is a digit or `-`).

### Pillar 3: Color (3/4)

**Minor — green is applied to non-success values.** `_summary_table` styles the Value column green (`eval.py:193`), including the three "Rejected (...)" counts; `_comparison_context_table` prints "Replay stability: unavailable" through the green Value column (`eval.py:333, 348`). Green conventionally signals success; rejected queries and unavailable measurements are neutral/negative states.

**Minor — no semantic emphasis on winner/regression.** `_winner_cell` returns plain text (`eval.py:272-278`) and the comparison tables style all cells cyan (`eval.py:294, 376`), so an improvement, a regression, and noise look identical apart from wording. Text-only signaling is accessible; color is simply unused where it would carry meaning.

**Minor — the label/value color distinction disappears in group tables.** `_groups_table` and `_comparison_groups_table` set `style="cyan"` for every column (`eval.py:228, 376`), unlike the other tables' cyan/green split.

**Pass — no hardcoded colors.** Style usage is semantic Rich style names only: 6 `cyan`, 6 `[yellow]`, 5 `[dim]`, 2 `green`; no hex/rgb values in the phase surface. Warnings/disclosures are consistently yellow on stderr; secondary notes are consistently dim.

**Pass — color is never the sole signal.** Winner/regression are words; warnings are prefixed text; stdout vs stderr is structural; `NO_COLOR` renders a complete, readable report.

### Pillar 4: Typography (3/4)

**Minor — `NDCG@10` vs `nDCG@10`.** 13 vs 25 occurrences across the repo; the CLI consistently uses the uppercase form while docs prose and the JSON-adjacent notes mix both. Pick the canonical metric spelling and apply it everywhere.

**Minor — raw machine enums in human labels.** `_render_footer` prints `Retrieval mode: bm25` (`eval.py:258`), the context table prints `saved bm25 / current bm25` (`eval.py:351`), and `_model_label` returns `no model (bm25)` (`eval.py:462`), while the surrounding prose says "BM25-only". Use a display-name map (`BM25`, `Hybrid`).

**Minor — non-wrappable header ellipsized even at 120 columns.** `Helped/Hurt/Unchanged` has no space to break at and renders as `Helped/Hurt/…` at 120 columns in a real capture. Use `Helped / Hurt / Unchanged` (or a short `H/H/U` header plus a legend).

**Minor — `Saved top_k` field-name typography** (also a copy issue): mixing snake_case schema into a Title-Case human table (`eval.py:353`).

**Pass — numeric typography is consistent.** 4 decimals for nDCG/Hit/CI/noise floor; signed deltas (`+0.0000`); integer counts; aligned columns. Three-level hierarchy (bold table title/header, normal values, dim annotations) is coherent, with no arbitrary emphasis styles.

### Pillar 5: Spacing (2/4)

**WARNING — density exceeds the canonical terminal width.** The comparison summary has 8 columns and the diagnostic groups table has 10 (`eval.py:281-390`); at 80 columns Rich ellipsizes rather than reflowing. This is the CLI analog of a layout that does not respond at the smallest supported breakpoint.

**WARNING — no vertical rhythm.** `_render_personal` and `_render_comparison` print each table back-to-back with no blank line, and the note block starts immediately below the last table (`eval.py:393-429`). A four-table report reads as a single wall of box-drawing characters; one blank line between sections would restore grouping.

**Minor — CI cells wrap at every width.** The 95% CI column is too narrow, so `[0.0000, 0.0000]` breaks across two lines even at 120 columns (real captures at 80/100/120). Every comparison and group row is consequently two lines tall.

**Pass — spacing values are consistent.** Rich default table padding is used throughout; no arbitrary padding overrides or ad-hoc blank-line counts; `soft_wrap=True` correctly prevents saved paths and long warnings from wrapping (`eval.py:455, 480, 488, 492, 650, 658`).

### Pillar 6: Experience Design (3/4)

**WARNING — no progress feedback for a potentially long measurement.** `run_personal` loads the embedder (a model load can download/initialize) and then runs up to 500 known-item searches plus up to 500 replay searches with no spinner, count, or ETA (`eval.py:547-623, 626-689`). Default INFO logging emits "Loading embedding model: ..." (`src/sif/embedding/manager.py:85`) and then the search phase is silent. The repository already provides `ProgressTracker`/`RichProgressTracker` (`src/sif/utils/progress.py:41-101`) but eval does not use it.

**WARNING — misleading command affordance.** `eval` is a `@click.group(..., invoke_without_command=True)` with no subcommands (`eval.py:756-816`). `sif eval --help` therefore prints `Usage: ... eval [OPTIONS] COMMAND [ARGS]...` with no Commands section, and `--personal` is rendered as optional even though `sif eval` exits 2 with "Error: --personal is required" (verified). The generated docs render `sif eval [OPTIONS]` (`docs/cli-reference.md:638-640`), so the two surfaces disagree.

**Minor — saved path is not markup-escaped.** `console_err.print(f"[dim]Saved run: {path}[/dim]", soft_wrap=True)` (`eval.py:455`) does not `escape()` the path. A cache directory containing markup-like brackets (e.g. `/tmp/[bold]evil[/bold]/…`) renders with the brackets swallowed, so the path the user copies is wrong. Every other user/config-derived cell follows the truncate-then-escape convention (T-18-01/T-18-06); this is an outlier.

**Pass — error states are loud, named, and traceback-free.** Verified: missing index, <50 documents, missing embed backend, unsolvable held-out floor, malformed saved run, fingerprint mismatch, missing/ambiguous target, and Click usage errors all exit non-zero with cause + remedy and no traceback.

**Pass — empty/degraded states are explicit.** Empty `query_log` yields `replay.available: false`, `num_queries: 0`, a bias note, and exit 0; no qualifying groups yields `No leg x language x length group reached the N >= 10 floor`; suppressed groups are named; replay-unavailable is warned on stderr (`eval.py:338-358, 400-403, 489-493`).

**Pass — transparent, safe interaction.** Auto-save is announced on stderr only (and exposed as `run_path` in JSON), `--no-save` opts out, compare-mode depth/mode/model mismatches are surfaced on stderr, and stdout remains strict-JSON-clean (verified with `json.load`). No destructive action is taken without an explicit flag.

**Pass — accessibility.** Color is not the only carrier of meaning; the report is complete under `NO_COLOR`; stdout/stderr separation keeps machine output clean.

---

## Minor Recommendations (not in top 3)

1. Render `Suppressed groups: none` (or omit the stderr parenthetical) when the suppressed list is empty (`eval.py:354-357`).
2. Rename the human label `Saved top_k` to "Retrieval depth" (`eval.py:353`).
3. Standardize on `nDCG@10` (or `NDCG@10`) across CLI, JSON notes, and docs.
4. Map retrieval enums to display names (`BM25`, `Hybrid`) in human-facing text (`eval.py:258, 351, 462`).
5. Make the `Helped / Hurt / Unchanged` header wrappable (spaces around `/`) or use `H/H/U` plus a legend (`eval.py:291`).
6. Replace "unavailable" and rejection-count green with a neutral style; use a semantic style for winner/regression and unify the cyan/green split across tables (`eval.py:193, 228, 294, 333, 348, 376`).
7. Add one blank line between tables and before the note block (`eval.py:393-429`).
8. Add progress/count feedback for the search loop (reuse `ProgressTracker`) (`eval.py:547-623`).
9. `escape()` the saved-run path before printing it (`eval.py:455`).
10. Emphasize the headline NDCG@10/Hit@10 rows and visually distinguish the held-out gate from diagnostic rows (`eval.py:191-204, 295-326`).

---

## Files Audited

- `src/sif/cli/commands/eval.py` — all Rich tables, stderr warnings, help text, JSON payload assembly (816 lines read in full).
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
