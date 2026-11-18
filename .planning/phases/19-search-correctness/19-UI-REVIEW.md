# Phase 19 — UI Review

**Audited:** 2026-11-18
**Baseline:** No UI-SPEC.md — abstract 6-pillar standards adapted to a Click/Rich terminal interface. No web frontend exists (no `.tsx`/`.jsx`/`.css` in the phase, no `components.json`). The audited surface is the terminal/MCP surface this phase changed: `sif search search` / `sif search vsearch` / `sif search query` table/JSON/CSV/Markdown/XML output, the `--offset` and `--per-chunk` flags, global rank numbering, chunk identity rendering, the `sif eval --compare` per-leg / leg × split gate tables, the `sif index update` migration notice, and the MCP result metadata.
**Screenshots:** not captured — no web UI exists. Ports 3000/5173 were closed; port 8080 answered but serves an unrelated SearXNG instance, not a SIF surface. Real CLI renders were captured as text at 80/100/120 columns from the phase-19 completion tree (`763753d`), plus help, error, and empty-state captures.
**Interaction captures:** off (`workflow.ui_interaction_capture` false). CLI interaction states were exercised manually instead: `--help` for all three subcommands; `--offset -1` (exit 2), a past-the-end offset (exit 0, empty page), `sif search --per-chunk` rejection (exit 2), per-chunk table/JSON/CSV/Markdown/XML/`--files` output, an eval comparison in text and JSON with stdout/stderr separated, and the migration notice across three `sif index update` passes (fresh marker, simulated legacy marker, marker written).

**Scope note:** Pillars that assume a rendered screen (breakpoints, icon buttons, font scales, 60/30/10 color distribution) are adapted to their terminal equivalents: table hierarchy and width responsiveness, Rich style semantics, terminal typography, layout density/rhythm, and CLI state coverage. Decisions D-01..D-12 in `19-CONTEXT.md` and the plan acceptance criteria are the functional contract for copy and transparency findings. Line references are to the phase-19 completion tree (`763753d`) so later-phase drift does not move them.

**Registry audit:** skipped — no `components.json` (not a shadcn/frontend project).

---

## Pillar Scores

| Pillar | Score | Key Finding |
|--------|-------|-------------|
| 1. Copywriting | 2/4 | `--min-score` help promises the opposite of its behavior; the new gate table title ships the internal ID `D-12`; the 80-char note cap still truncates the comparability statement mid-word |
| 2. Visuals | 2/4 | The per-chunk `Chunk` column ellipsizes the `#sequence` away at 80 and 100 columns; the comparison and group tables ellipsize every metric at 80 |
| 3. Color | 3/4 | Semantic styles and no color-only meaning, but both new comparison tables are all-cyan with no label/value or winner/regression distinction |
| 4. Typography | 3/4 | Consistent 4-decimal numerics, but the non-wrappable `Helped/Hurt/Unchanged` header is ellipsized even at 120 in two tables and `Leg x split` uses a plain `x` |
| 5. Spacing | 2/4 | Two tables were added to `--compare` with no vertical rhythm; the comparison and per-chunk tables wrap every row at the canonical 80 columns |
| 6. Experience Design | 2/4 | BLOCKER: `--min-score` drops the best-ranked match first; per-chunk CSV/Markdown/XML/`--files` lose chunk identity; under-floor and absent gates render as valid-looking zeros |

**Overall: 14/24**

---

## Top 3 Priority Fixes

1. **BLOCKER — `--min-score` and the `Score` column run backwards** — the rank-1 (best) BM25 match gets the *lowest* displayed score, and the documented "minimum score" threshold filters out the strongest matches first. Live evidence: `sif search search "Saltiv Protocol Notes"` shows rank 1 `Saltiv Protocol Notes` at `0.1057` and rank 2 `Qelron Protocol Notes` at `0.1527` (raw FTS bm25 `-8.46` vs `-5.55`), and `--min-score 0.23` on the same query returns `[]`. Every BM25 user sees a relevance score that increases as relevance decreases, and anyone using `--min-score` silently loses the best results. The formula predates this phase, but Plan 19-05 re-derived the pre-pagination predicate from it (`src/sif/search/bm25.py:93-96`, `159`, `216`) and pinned the inverted direction in a test; fix the map (e.g. `1 - 1/(1+|rank|)`), bind the threshold to the same expression, and add a regression asserting `min_score` never removes rank 1 while rank 2 loses to it.
2. **The per-chunk `Chunk` column truncates the `#sequence` away at 80 and 100 columns** — the column exists to make the matched chunk addressable (D-03), yet 80-column output shows `/notes/chunky/protoc…` and 100-column output shows `/notes/chunky/protocol-notes.m…`; only 120 columns renders `path#sequence`. Put the identity where truncation cannot eat it (`#0 · /notes/...`), add a narrow right-aligned `Seq` column, or set `overflow="fold"` on the chunk cell, and pin an 80-column render test (`src/sif/cli/commands/search.py:123-135, 794-810, 1127-1144`).
3. **The D-12/noise-gate evidence in `sif eval --compare` is hard to read and easy to misread** — at 80 columns the new `Legs (D-12 gate input)` table ellipsizes `Helped/H…` and wraps every CI; the carried-over summary truncates `Tuning (diagno…)` and the groups table ellipsizes every metric; the per-leg table has no `Sufficient` column (a body leg with N=5 renders like a valid gate); an absent body/held-out split renders `0 +0.0000 [0.0000, 0.0000]` instead of n/a; and the title exposes the internal decision ID. Make the comparison width-responsive (compact/fold below ~110 columns or gate diagnostics behind `--json`/`--verbose`), add `Sufficient` to the per-leg table, render `n/a` for N=0, and use user-facing wording (`src/sif/cli/commands/eval.py:335-519`).

---

## Detailed Findings

### Pillar 1: Copywriting (2/4)

**BLOCKER — `--min-score` copy contradicts the behavior.** Help and docs say `Minimum score threshold` (`src/sif/cli/commands/search.py:467` for BM25, `652` for vsearch, `842` for query; `docs/cli-reference.md:436, 478, 512`), but the value is a *lower bound on an inverted relevance score*: the rank-1 match displays `0.1057` and is removed by `--min-score 0.23`, while weaker matches at `0.3747` survive. A user following the label loses the best results. This is the most damaging copy defect on the phase surface because it is a behavioral promise, not just wording.

**WARNING — internal decision ID in shipped table output.** The new per-leg comparison table is titled `Legs (D-12 gate input)` (`src/sif/cli/commands/eval.py:385`). `D-12` is a CONTEXT decision number; no user knows what it means. Follow the phase-18 correction of `(Plan 03)` and name the table for the reader (`Per-leg gates (title vs body)`), keeping the decision ID in docs/tests only.

**WARNING — the 80-char cell cap still truncates the comparison notes mid-word.** `_render_footer` routes every note through `_cell()` (`eval.py:310`; cap `_CELL_MAX_LEN = 80` at `76`, `84-89`). The real 80-column capture shows `Comparison run: the saved query set was re-evaluated in saved order with no s...`, discarding "synthesis, overlap filtering, or split reassignment" — the sentence that defines the comparison's comparability. The full note exists in `personal_bench.py:2158-2160` and in JSON. This is the same defect phase 18's top fix #1 identified; it was not fixed while the phase added two more tables to this render.

**WARNING — the new benchmarking section tells users to run commands that do not exist.** The CORR-02 section says `--per-chunk` on `sif vsearch`/`sif query` and "`sif search`" (`docs/benchmarking.md:208`), but the CLI is `sif search vsearch` / `sif search query` / `sif search search` (verified: `sif vsearch` exits 2 with `No such command 'vsearch'`). The generated reference is correct (`docs/cli-reference.md:419, 461, 495`), so the hand-written doc contradicts it. The same line also advertises MCP `vec_search` `per_chunk`, a tool that is not registered (`handlers.py:224-231`; already deferred as IN-03).

**Minor — plain `x` instead of `×`.** `Leg x split gates` (`eval.py:415`) and `No leg x language x length group reached the N >= 10 floor.` (`eval.py:517`) read as code, not prose; the docs correctly use `leg × split`.

**Minor — schema/UI terminology drift.** `Saved top_k` (`eval.py:464`), lowercase `bm25` (`eval.py:312, 462`), and `Retrieval mode` mix internal field/enum names into a Title-Case human table.

**Minor — hand-written docs leak milestone jargon.** `D-11`, `D-12`, `CORR-02`, `CORR-04`, `Plan 08`, `QUAL-03`, and `research Pitfall 16/17` appear in `docs/benchmarking.md:227-253`. The narrative is otherwise specific and evidence-bearing; gloss or drop the IDs.

**Pass — no generic labels.** No `Submit`/`OK`/`No data`/`went wrong` placeholders on the phase surface. The migration line names the count and the once-only behavior (`index.py:165-170`), the `--offset`/`--per-chunk` help is specific and accurate, and existing error/empty copy remains remedy-bearing.

### Pillar 2: Visuals (2/4)

**WARNING — the per-chunk table's only new identity signal is truncated away at 80/100 columns.** `_chunk_cell` renders `escape(f"{path}#{sequence}")` (`src/sif/cli/commands/search.py:123-135`); the column is added only in per-chunk mode (`794-799`, `1127-1131`). Captures with realistic paths:
```
80 cols:  │ 11 │ 0.9000 │ Chunky Document About │ /notes/chunky/protoc… │ personal-notes │
100 cols: │ 11 │ 0.9000 │ Chunky Document About │ /notes/chunky/protocol-notes.m… │ personal-notes │
120 cols: │ 11 │ 0.9000 │ Chunky Document About │ /notes/chunky/protocol-notes.md#0 │ personal-notes │
```
At the canonical terminal width the user cannot tell which chunk of a document each row is, which defeats D-03's addressing contract in the primary human renderer. The sequence must not be the ellipsized tail.

**WARNING — the comparison report is unreadable at 80 columns and the new table inherits the problem.** Real 80-column capture:
- new `Legs (D-12 gate input)`: header `Helped/H…`, every CI wraps (`[0.0000,` / `0.0000]`), every row two lines;
- summary: `Tuning (diagno…` and `Helped…`;
- `Groups (diagnostic)`: `Base…`, `Curr…`, `Leng…`, `Helpe…`, `Winn…` headers and `1.00…`, `[0.0…` values — every metric unreadable.

At 100 the new legs table still wraps its CI and ellipsizes the header; at 120 `Helped/Hurt/Un…` is still cut. The phase's central D-12 evidence is not reliably legible in the default human mode at the canonical width.

**WARNING — the `Score` column is visually anti-monotonic.** In the BM25 table, `Score` increases down the list (rank 1 `0.1057`, rank 2 `0.1527`) because `1/(1+|rank|)` maps a better (more negative) bm25 value to a smaller number (`src/sif/search/bm25.py:159, 216`). The green right-aligned column reads as "higher is better", so the visual hierarchy contradicts the rank order. (Behavioral impact is under Pillar 6.)

**Minor — no focal point in the comparison.** The held-out row, the only gate that can warrant a defaults change, is styled identically to `Overall` and `Tuning (diagnostic)` (`eval.py:335-380`); the new per-leg table gives the title/body split no emphasis, and `yes (regression)` vs `no` is plain text in an all-cyan row.

**Minor — the snippet duplicates the title.** Every captured BM25 snippet begins with the document's H1 (`# Saltiv Protocol Notes`) before the useful sentence, pushing content out of the truncated first line. This is the recorded H1-duplication caveat (Pitfall 16, Phase 24 QUAL-03), but it is visible on every search result at 80 columns.

**Pass — table structure is sound.** Global ranks render correctly (`--offset 1` shows ranks 2–3 in both table and JSON), numeric columns are right-aligned, every table has a title, per-column styles are stable, and the chunk-match annotation is dim and secondary.

### Pillar 3: Color (3/4)

**Minor — the two new comparison tables style every column cyan.** `_comparison_legs_table` and `_comparison_leg_splits_table` use `style="cyan"` for all columns (`eval.py:396, 425`), unlike the summary/context tables' cyan-label/green-value split (`eval.py:348, 443-444`). Adjacent tables in one render still switch visual systems, and the new D-12 input table loses the label/value distinction exactly where a reader scans for the title-vs-body difference.

**Minor — winner/regression has no semantic emphasis.** `_winner_cell` returns plain text (`eval.py:326-332`) and every comparison cell is cyan, so an improvement, a regression, and noise look identical apart from wording. Text-only signaling is accessible; color is simply unused where it would add meaning.

**Minor — magenta is added to the search table palette.** The per-chunk `Chunk` column is `style="magenta"` (`search.py:798, 1131`), making five column colors in one row (`cyan` rank, `green` score, `yellow` title, `magenta` chunk, `blue` collection) with no legend. The choice is stable and not color-only, so this is a palette-expansion note, not a defect.

**Pass — no hardcoded colors and no color-only meaning.** The phase surface uses semantic Rich names only (`cyan`, `green`, `yellow`, `red`, `dim`, `magenta`); no hex/rgb values. Warnings and upgrade notices are yellow, secondary annotations dim, errors red. `NO_COLOR` renders a complete, readable report (all captures above were made under `NO_COLOR=1`).

### Pillar 4: Typography (3/4)

**Minor — `Helped/Hurt/Unchanged` cannot wrap and is ellipsized even at 120 columns.** The header appears in the summary (`eval.py:345`) and, newly, in the per-leg table (`eval.py:393`); real captures show `Helped/Hurt/Un…` at 120. Use spaces around the slashes or `H/H/U` plus a legend. Phase 18's fix #4 was not applied, and the phase duplicated the header into a new table.

**Minor — `Tuning (diagnostic)` still truncates.** At 80/100 it renders `Tuning (diagno…`, losing the word that carries the "not a defaults gate" meaning (`eval.py:357`). At 120 it wraps onto a second line. Shorten the label or move the diagnostic marker to its own column/footnote.

**Minor — NDCG@10 vs nDCG@10.** CLI tables consistently use `NDCG@10`; docs prose mixes `nDCG@10` (`docs/benchmarking.md:222-223, 247, 327`). Pick one spelling.

**Minor — raw lowercase enums in human output.** `Retrieval mode: bm25` (`eval.py:312`) and `saved bm25 / current bm25` (`eval.py:462`) should use display names (`BM25`), matching the prose elsewhere.

**Minor — `Leg x split` / `leg x language x length` use the letter `x`** instead of `×` (`eval.py:415, 517`).

**Pass — numeric typography is consistent.** Four decimals for NDCG/CI/delta, signed deltas (`+0.0000`), integer N/rank, right-aligned numeric columns, and a coherent three-level hierarchy (bold table title, normal values, dim annotations). The `Chunk` cell is plain text with `#sequence`, which is readable when not truncated.

### Pillar 5: Spacing (2/4)

**WARNING — the comparison render has no vertical rhythm and gained two tables.** `_render_comparison` prints summary, legs, leg × split, context, groups, and the footer back-to-back with no blank line (`eval.py:504-519`); the phase added the legs and leg × split tables. Six sections of box-drawing characters merge into one wall at 80 columns. Add one blank line between tables and before the note block (phase 18's fix #7, still open).

**WARNING — density exceeds the canonical width.** The summary has 8 columns (`eval.py:338-348`), the new legs table 8 (`386-396`), and the groups table 10 (`475-487`). Only the 7-column leg × split table and the 2-column context table render cleanly at 80; Rich ellipsizes rather than reflows. This is the terminal analog of a layout that does not respond at the smallest breakpoint.

**WARNING — per-chunk search tables wrap every row at 80.** The vector per-chunk table has 5 columns and the hybrid 6 (`search.py:791-801, 1124-1135`); with title, chunk, collection, and snippet, every result becomes two to three lines and the chunk cell is ellipsized (see Pillar 2). The new escape hatch produces the least readable output at the most common width.

**Minor — CI cells break at every width** (`[0.0000,` / `0.0000]`) because the column is narrower than the value, even at 120 in the groups table. Use `overflow="fold"` or a wider/compact CI format.

**Pass — spacing values are consistent.** Rich default table padding throughout; no arbitrary padding overrides or ad-hoc blank-line counts; `soft_wrap=True` still protects saved paths and long warnings.

### Pillar 6: Experience Design (2/4)

**BLOCKER — `--min-score` breaks the filter's user task.** The threshold is derived as `rank >= 1 - 1/min_score` against a negative bm25 expression (`src/sif/search/bm25.py:75-96`), and the displayed score is `1/(1+|rank|)` (`159`, `216`). Because a better match has a larger absolute bm25 value, the filter keeps *weaker* matches. Verified live on the committed bench index: `sif search search "Saltiv Protocol Notes" -n 10` returns rank 1 `Saltiv Protocol Notes` at `0.1057` and rank 2 `Qelron Protocol Notes` at `0.1527`; `--min-score 0.23` returns `[]`, dropping both, best first. The help says "Minimum score threshold". A one-line display/filter fix is possible without changing ordering (and therefore without re-recording B0), but the current behavior must not ship. (Pre-existing formula, but Plan 19-05 made the threshold pre-pagination and pinned the direction in `TestBM25OffsetPagination`.)

**WARNING — per-chunk mode loses chunk identity in three supported output modes.** `sif search query --per-chunk --csv` emits `rank,score,title,path,collection,vectors_stale` with no chunk column (`search.py:369`), so three chunk rows of one document are identical except rank/score; `--md` and `--xml` likewise carry no `chunk_id`/`sequence` (`385-441`), and `--files` prints the same path once per chunk (`550-553` search, `1072-1075` query). The phase scoped CSV/Markdown/XML headers as "untouched", but D-03 calls chunk identity part of the public result contract; at minimum reject `--per-chunk` with machine formats or append `#sequence`/a `chunk` column. JSON and MCP are covered correctly (`SearchResult.to_dict()` at `models.py:308-326`; MCP re-map at `backend.py:229-241`).

**WARNING — the per-leg gate table hides `Sufficient` and absent splits render as zeros.** `_comparison_legs_table` has no `Sufficient` column (`eval.py:386-396`), so a body leg with N=5 displays like a valid gate; the JSON correctly carries `sufficient: false`. In `_comparison_leg_splits_table`, an absent split renders `body | heldout | 0 | +0.0000 | [0.0000, 0.0000] | no | no` (`eval.py:426-436`) because `noise_gate([])` returns zeroed means (`personal_bench.py:1808-1823`). The plan's "never a fabricated zero" intent is honored in JSON but not in the text table. Render `n/a`/`—` and add the column.

**Minor — a past-the-end page is indistinguishable from a zero-match query.** `--offset 100 -n 5` prints `No results found.` and exits 0 (verified), the same copy as a query with no matches (`search.py:595-599, 784-788, 1117-1121`). Add a page-aware empty state ("No results on this page; fewer matching documents than the offset"), especially since global ranks make paging an advertised interaction.

**Minor — no progress feedback for a potentially long query.** `sif search query` can load/download an embedding model and then run expansion, hybrid search, and optional reranking with no count or spinner (`search.py:1006-1058`); `ProgressTracker` exists in `src/sif/utils/progress.py` but is unused here. Carried from phase 18, not introduced.

**Minor — `sif search search --per-chunk` gives only Click's `No such option`.** The flag is correctly scoped to vsearch/query (D-01), but a user who read the docs is not pointed at the commands that do accept it. A one-line hint in the group help or error is cheap.

**Pass — the new interaction states are otherwise strong.** `--offset` is `IntRange(min=0)` and rejects `-1` with a clear range message (exit 2); a past-end offset is an empty page, never an error; global ranks continue across pages in table and JSON; the migration notice prints once with the document count, stays silent when the marker is written, and retries after a failure; suppressed groups and replay-unavailable reasons go to stderr while `--json` stays parseable; the MCP boundary forwards `chunk_id`/`sequence`/`chunk_matches` explicitly; `--per-chunk` is rejected by `sif search` and absent from `lex_search`.

---

## Minor Recommendations (not in top 3)

1. Add `chunk`/`sequence` to CSV/Markdown/XML output (or reject machine formats in per-chunk mode), and dedupe or annotate `--files` in per-chunk mode (`search.py:369, 385-441, 550-553, 1072-1075`).
2. Replace `Legs (D-12 gate input)` with user-facing wording and keep decision IDs out of shipped table titles (`eval.py:385`).
3. Print comparison notes with normal wrapping instead of the 80-character `_cell` cap (`eval.py:76, 84-89, 310`).
4. Use `×` in `Leg × split` and `leg × language × length` (`eval.py:415, 517`).
5. Make `Helped/Hurt/Unchanged` wrappable (spaces around `/`) or use `H/H/U` plus a legend in both tables (`eval.py:345, 393`).
6. Standardize `NDCG@10` vs `nDCG@10` across CLI output and docs.
7. Map raw retrieval enums to display names (`BM25`, `Hybrid`) in footer/context tables (`eval.py:312, 462`).
8. Add a `Sufficient` column to the per-leg table and render `n/a` for absent leg × split gates (`eval.py:386-436`).
9. Give the held-out row and winner/regression a distinct (still text-backed) emphasis (`eval.py:335-408`).
10. Add one blank line between comparison tables and before the note block (`eval.py:504-519`).
11. Fix the benchmark doc's command names to `sif search vsearch` / `sif search query` and remove the unregistered MCP `vec_search` claim until Phase 22 (`docs/benchmarking.md:208`; IN-03).
12. Add a page-aware empty state for past-the-end offsets (`search.py:595-599, 784-788, 1117-1121`).
13. Add progress/count feedback around the model load and search loop in eval (reuse `ProgressTracker`).
14. Skip the leading H1 when extracting search snippets to stop duplicating the Title column (Phase 24 QUAL-03).
15. Consider a dedicated `Seq` column instead of embedding the sequence in a long path cell (`search.py:123-135`).

---

## Files Audited

- `src/sif/cli/commands/search.py` (phase-19 tree, 1164 lines): flag blocks for `--offset`/`--per-chunk`; `_title_cell`; `_chunk_cell`; vsearch/query per-chunk tables; JSON/CSV/Markdown/XML/`--files` renderers; empty-state and DYM paths.
- `src/sif/cli/commands/eval.py` (971 lines): `_cell`/footer notes; summary, per-leg, leg × split, context, and groups tables; `_render_comparison`; JSON comparison payload consumption.
- `src/sif/cli/commands/index.py`: `_render_index_event` and the `migrate` line.
- `src/sif/core/models.py`: `SearchResult.to_dict()` chunk fields; `SearchOptions.per_chunk`/`offset`.
- `src/sif/search/bm25.py`: score mapping, pre-pagination `min_score` predicate, rank numbering.
- `src/sif/search/personal_bench.py`: comparison notes, `GateResult`, `leg_noise_gates`, `noise_gate` empty-input behavior.
- `src/sif/search/vector.py` / `hybrid.py`: global rank assignment and score semantics (spot-checked).
- `src/sif/mcp/backend.py`, `src/sif/mcp/protocol.py`, `src/sif/mcp/handlers.py`: `per_chunk`/`offset` inputs, schema sync, chunk-field re-map, registered tool set.
- `docs/cli-reference.md`: generated `--offset`/`--per-chunk` rows and min-score rows.
- `docs/benchmarking.md`: CORR-02 and CORR-04 sections, B0/B1 evidence, D-12 verdict narrative.
- `tests/unit/cli/test_search.py`: `TestPerChunkSurfaces` rendering/JSON assertions.
- `tests/unit/cli/test_search_pagination.py`, `tests/integration/test_search_correctness.py`: pagination/rank contract (read for intent).
- Committed evidence artifacts: `bench/b0.json`, `bench/b1.json`, `bench/d12-verdict.json` (shape and decision verified).
- Live text captures (phase-19 tree at `763753d`): `search search|vsearch|query --help`; BM25 table at 80/100/120; `--offset 1` table and JSON (ranks 2–3); past-end table/JSON; `--offset -1`; `--per-chunk` rejection on `sif search`; vector/hybrid per-chunk tables at 80/100/120; per-chunk CSV/Markdown/XML/`--files`; default chunk-match annotation; `eval --compare` text at 80/100/120 and JSON; leg × split table with an absent split; per-leg table with an under-floor leg; migration notice over three index passes; stderr/stdout separation under `NO_COLOR`.
