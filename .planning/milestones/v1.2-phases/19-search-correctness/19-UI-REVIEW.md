# Phase 19 — UI Review

**Audited:** 2026-11-18
**Baseline:** No UI-SPEC.md — abstract 6-pillar standards adapted to a Click/Rich terminal interface. No web frontend exists (no `.tsx`/`.jsx`/`.css` in the phase, no `components.json`). The audited surface is the terminal/MCP surface this phase changed: `sif search search` / `sif search vsearch` / `sif search query` table/JSON/CSV/Markdown/XML output, the `--offset` and `--per-chunk` flags, global rank numbering, chunk identity rendering, the `sif eval --compare` per-leg / leg × split gate tables, the `sif index update` migration notice, and the MCP result metadata.
**Screenshots:** not captured — no web UI exists. Ports 3000/5173 were closed; port 8080 answered but serves an unrelated SearXNG instance, not a SIF surface. Real CLI renders were captured as text at 80/100/120 columns from the phase-19 completion tree (`763753d`), plus help, error, and empty-state captures.
**Interaction captures:** off (`workflow.ui_interaction_capture` false). CLI interaction states were exercised manually instead: `--help` for all three subcommands; `--offset -1` (exit 2), a past-the-end offset (exit 0, empty page), `sif search --per-chunk` rejection (exit 2), per-chunk table/JSON/CSV/Markdown/XML/`--files` output, an eval comparison in text and JSON with stdout/stderr separated, and the migration notice across three `sif index update` passes (fresh marker, simulated legacy marker, marker written).

**Scope note:** Pillars that assume a rendered screen (breakpoints, icon buttons, font scales, 60/30/10 color distribution) are adapted to their terminal equivalents: table hierarchy and width responsiveness, Rich style semantics, terminal typography, layout density/rhythm, and CLI state coverage. Decisions D-01..D-12 in `19-CONTEXT.md` and the plan acceptance criteria are the functional contract for copy and transparency findings. Line references are to HEAD (`bd6a8d8`), re-pinned in the 2026-11-25 re-audit from the phase-19 completion tree (`763753d`) where the live captures were taken, so later-phase drift does not move them.

**Registry audit:** skipped — no `components.json` (not a shadcn/frontend project).

---

## Pillar Scores

| Pillar | Score | Key Finding |
|--------|-------|-------------|
| 1. Copywriting | 2/4 | `--min-score` help promises the opposite of its behavior; the new gate table title ships the internal ID `D-12`; the 80-char note cap still truncates the comparability statement mid-word |
| 2. Visuals | 2/4 | The per-chunk `Chunk` column ellipsizes the `#sequence` away at 80 columns (at 100 on pages with longer titles); the comparison and group tables ellipsize every metric at 80 |
| 3. Color | 3/4 | Semantic styles and no color-only meaning, but both new comparison tables are all-cyan with no label/value or winner/regression distinction |
| 4. Typography | 3/4 | Consistent 4-decimal numerics, but the non-wrappable `Helped/Hurt/Unchanged` header is ellipsized at 120 in the summary table and at 100 in both tables, and `Leg x split` uses a plain `x` |
| 5. Spacing | 2/4 | Two tables were added to `--compare` with no vertical rhythm; the comparison and per-chunk tables wrap every row at the canonical 80 columns |
| 6. Experience Design | 2/4 | BLOCKER: `--min-score` drops the best-ranked match first; per-chunk CSV/Markdown/XML/`--files` lose chunk identity; under-floor and absent gates render as valid-looking zeros |

**Overall: 14/24**

---

## Top 3 Priority Fixes

1. **BLOCKER — `--min-score` and the `Score` column run backwards** — the rank-1 (best) BM25 match gets the *lowest* displayed score, and the documented "minimum score" threshold filters out the strongest matches first. Live evidence: `sif search search "Saltiv Protocol Notes"` shows rank 1 `Saltiv Protocol Notes` at `0.1057` and rank 2 `Qelron Protocol Notes` at `0.1527` (raw FTS bm25 `-8.46` vs `-5.55`), and `--min-score 0.23` on the same query returns `[]`. Every BM25 user sees a relevance score that increases as relevance decreases, and anyone using `--min-score` silently loses the best results. The formula predates this phase, but Plan 19-05 re-derived the pre-pagination predicate from it (`src/sif/search/bm25.py:94-97`, `171`, `231`) and pinned the inverted direction in a test; fix the map (e.g. `1 - 1/(1+|rank|)`), bind the threshold to the same expression, and add a regression asserting `min_score` never removes rank 1 while rank 2 loses to it.
2. **The per-chunk `Chunk` column truncates the `#sequence` away at 80 and 100 columns** — the column exists to make the matched chunk addressable (D-03), yet 80-column output shows `/notes/chunky/protoc…` and 100-column output shows `/notes/chunky/protocol-notes.m…`; only 120 columns renders `path#sequence` (the 100-column cut tracks Rich's column allocation — a page with only short titles and collection names fits at 100 — and a legacy Windows console renders one column narrower). Put the identity where truncation cannot eat it (`#0 · /notes/...`), add a narrow right-aligned `Seq` column, or set `overflow="fold"` on the chunk cell, and pin an 80-column render test (`src/sif/cli/commands/search.py:177-189, 905-921, 1267-1284`).
3. **The D-12/noise-gate evidence in `sif eval --compare` is hard to read and easy to misread** — at 80 columns the new `Legs (D-12 gate input)` table ellipsizes `Helped/H…` and wraps every CI; the carried-over summary truncates `Tuning (diagno…)` and the groups table ellipsizes every metric; the per-leg table has no `Sufficient` column (a body leg with N=5 renders like a valid gate); an absent body/held-out split renders `0 +0.0000 [0.0000, 0.0000]` instead of n/a; and the title exposes the internal decision ID. Make the comparison width-responsive (compact/fold below ~110 columns or gate diagnostics behind `--json`/`--verbose`), add `Sufficient` to the per-leg table, render `n/a` for N=0, and use user-facing wording (`src/sif/cli/commands/eval.py:380-564`).

---

## Detailed Findings

### Pillar 1: Copywriting (2/4)

**BLOCKER — `--min-score` copy contradicts the behavior.** Help and docs say `Minimum score threshold` (`src/sif/cli/commands/search.py:530` for BM25, `731` for vsearch, `962` for query; `docs/cli-reference.md:495, 538, 573`), but the value is a *lower bound on an inverted relevance score*: the rank-1 match displays `0.1057` and is removed by `--min-score 0.23`, while weaker matches at `0.3747` survive. A user following the label loses the best results. This is the most damaging copy defect on the phase surface because it is a behavioral promise, not just wording.

**WARNING — internal decision ID in shipped table output.** The new per-leg comparison table is titled `Legs (D-12 gate input)` (`src/sif/cli/commands/eval.py:430`). `D-12` is a CONTEXT decision number; no user knows what it means. Follow the phase-18 correction of `(Plan 03)` and name the table for the reader (`Per-leg gates (title vs body)`), keeping the decision ID in docs/tests only.

**WARNING — the 80-char cell cap still truncates the comparison notes mid-word.** `_render_footer` routes every note through `_cell()` (`eval.py:355`; cap `_CELL_MAX_LEN = 80` at `87`, `95-100`). The real 80-column capture shows `Comparison run: the saved query set was re-evaluated in saved order with no s...`, discarding "synthesis, overlap filtering, or split reassignment" — the sentence that defines the comparison's comparability. The full note exists in `personal_bench.py:2361-2363` and in JSON. This is the same defect phase 18's top fix #1 identified; it was not fixed while the phase added two more tables to this render.

**Resolved at HEAD — the benchmark section no longer names commands that do not exist.** At the phase-19 tree `docs/benchmarking.md:208` said `--per-chunk` on `sif vsearch`/`sif query` and advertised an MCP `vec_search` tool that was not registered (`src/sif/mcp/handlers.py:224-231` at `763753d`; deleted in Phase 22). At HEAD the same line names "the `vsearch` and `query` subcommands of `sif search`" (reworded in `42e1acd6`), and `vec_search` is a registered tool that accepts `per_chunk` (Phase 22; `src/sif/mcp/tools.py:344-407`, `src/sif/mcp/backend.py:618-664`), so the hand-written doc now agrees with the generated reference (`docs/cli-reference.md:477, 520, 555`). Not counted against the pillar.

**Minor — plain `x` instead of `×`.** `Leg x split gates` (`eval.py:460`) and `No leg x language x length group reached the N >= 10 floor.` (`eval.py:562`) read as code, not prose; the docs correctly use `leg × split`.

**Minor — schema/UI terminology drift.** `Saved top_k` (`eval.py:509`), lowercase `bm25` (`eval.py:357, 507`), and `Retrieval mode` mix internal field/enum names into a Title-Case human table.

**Minor — hand-written docs leak milestone jargon.** `D-11`, `D-12`, `CORR-02`, `CORR-04`, `Plan 08`, `QUAL-03`, and `research Pitfall 16/17` appear in `docs/benchmarking.md:206-257`. The narrative is otherwise specific and evidence-bearing; gloss or drop the IDs.

**Pass — no generic labels.** No `Submit`/`OK`/`No data`/`went wrong` placeholders on the phase surface. The migration line names the count and the once-only behavior (`index.py:185-190`), the `--offset`/`--per-chunk` help is specific and accurate, and existing error/empty copy remains remedy-bearing.

### Pillar 2: Visuals (2/4)

**WARNING — the per-chunk table's only new identity signal is truncated away at 80/100 columns.** `_chunk_cell` renders `escape(f"{path}#{sequence}")` (`src/sif/cli/commands/search.py:177-189`); the column is added only in per-chunk mode (`905-910`, `1267-1271`). Captures with realistic paths:
```
80 cols:  │ 11 │ 0.9000 │ Chunky Document About │ /notes/chunky/protoc… │ personal-notes │
100 cols: │ 11 │ 0.9000 │ Chunky Document About │ /notes/chunky/protocol-notes.m… │ personal-notes │
120 cols: │ 11 │ 0.9000 │ Chunky Document About │ /notes/chunky/protocol-notes.md#0 │ personal-notes │
```
At the canonical terminal width the user cannot tell which chunk of a document each row is, which defeats D-03's addressing contract in the primary human renderer. The sequence must not be the ellipsized tail. The exact cut is allocation-dependent: Rich sizes the columns from the widest cells on the page (a longer title or collection name elsewhere on the page is what makes the captured page cut at 100; a page of short titles fits `path#sequence` at 100 columns), and a legacy Windows console renders one column narrower (`/notes/chunky/proto…` at 80), so the capture's exact cell widths are not stable — but the `#sequence` was lost at 80 columns in every variant re-rendered at HEAD.

**WARNING — the comparison report is unreadable at 80 columns and the new table inherits the problem.** Real 80-column capture:
- new `Legs (D-12 gate input)`: header `Helped/H…`, every CI wraps (`[0.0000,` / `0.0000]`), every row two lines;
- summary: `Tuning (diagno…` and `Helped…`;
- `Groups (diagnostic)`: `Base…`, `Curr…`, `Leng…`, `Helpe…`, `Winn…` headers and `1.00…`, `[0.0…` values — every metric unreadable.

At 100 the new legs table still wraps its CI and ellipsizes the header; at 120 the summary still cuts `Helped/Hurt/Un…`, while the per-leg table fits unless a leg name is long or a winner is not `no`. The phase's central D-12 evidence is not reliably legible in the default human mode at the canonical width.

**WARNING — the `Score` column is visually anti-monotonic.** In the BM25 table, `Score` increases down the list (rank 1 `0.1057`, rank 2 `0.1527`) because `1/(1+|rank|)` maps a better (more negative) bm25 value to a smaller number (`src/sif/search/bm25.py:171, 231`). The green right-aligned column reads as "higher is better", so the visual hierarchy contradicts the rank order. (Behavioral impact is under Pillar 6.)

**Minor — no focal point in the comparison.** The held-out row, the only gate that can warrant a defaults change, is styled identically to `Overall` and `Tuning (diagnostic)` (`eval.py:380-425`); the new per-leg table gives the title/body split no emphasis, and `yes (regression)` vs `no` is plain text in an all-cyan row.

**Minor — the snippet duplicates the title.** Every captured BM25 snippet begins with the document's H1 (`# Saltiv Protocol Notes`) before the useful sentence, pushing content out of the truncated first line. This is the recorded H1-duplication caveat (Pitfall 16, Phase 24 QUAL-03), but it is visible on every search result at 80 columns.

**Pass — table structure is sound.** Global ranks render correctly (`--offset 1` shows ranks 2–3 in both table and JSON), numeric columns are right-aligned, every table has a title, per-column styles are stable, and the chunk-match annotation is dim and secondary.

### Pillar 3: Color (3/4)

**Minor — the two new comparison tables style every column cyan.** `_comparison_legs_table` and `_comparison_leg_splits_table` use `style="cyan"` for all columns (`eval.py:441, 470`), unlike the summary/context tables' cyan-label/green-value split (`eval.py:393, 488-489`). Adjacent tables in one render still switch visual systems, and the new D-12 input table loses the label/value distinction exactly where a reader scans for the title-vs-body difference.

**Minor — winner/regression has no semantic emphasis.** `_winner_cell` returns plain text (`eval.py:371-377`) and every comparison cell is cyan, so an improvement, a regression, and noise look identical apart from wording. Text-only signaling is accessible; color is simply unused where it would add meaning.

**Minor — magenta is added to the search table palette.** The per-chunk `Chunk` column is `style="magenta"` (`search.py:909, 1271`), making five column colors in one row (`cyan` rank, `green` score, `yellow` title, `magenta` chunk, `blue` collection) with no legend. The choice is stable and not color-only, so this is a palette-expansion note, not a defect.

**Pass — no hardcoded colors and no color-only meaning.** The phase surface uses semantic Rich names only (`cyan`, `green`, `yellow`, `red`, `dim`, `magenta`); no hex/rgb values. Warnings and upgrade notices are yellow, secondary annotations dim, errors red. `NO_COLOR` renders a complete, readable report (all captures above were made under `NO_COLOR=1`).

### Pillar 4: Typography (3/4)

**Minor — `Helped/Hurt/Unchanged` cannot wrap and is ellipsized at 120 columns in the summary table.** The header appears in the summary (`eval.py:390`) and, newly, in the per-leg table (`eval.py:438`); real captures show `Helped/Hurt/Un…` at 120. A HEAD re-render confirms the cut at 100 in both tables and at 120 in the summary, but the per-leg table fits at 120 with B1's short `title`/`body` leg names and all-`no` winners — a 10-character leg name or a `yes (…)` winner re-cuts it. Phase 18's fix #4 was not applied, and the phase duplicated the header into a new table.

**Minor — `Tuning (diagnostic)` still truncates.** At 80/100 it renders `Tuning (diagno…`, losing the word that carries the "not a defaults gate" meaning (`eval.py:402`). At 120 it wraps onto a second line. Shorten the label or move the diagnostic marker to its own column/footnote.

**Minor — NDCG@10 vs nDCG@10.** CLI tables consistently use `NDCG@10`; docs prose mixes `nDCG@10` (`docs/benchmarking.md:222-223, 241, 421`). Pick one spelling.

**Minor — raw lowercase enums in human output.** `Retrieval mode: bm25` (`eval.py:357`) and `saved bm25 / current bm25` (`eval.py:507`) should use display names (`BM25`), matching the prose elsewhere.

**Minor — `Leg x split` / `leg x language x length` use the letter `x`** instead of `×` (`eval.py:460, 562`).

**Pass — numeric typography is consistent.** Four decimals for NDCG/CI/delta, signed deltas (`+0.0000`), integer N/rank, right-aligned numeric columns, and a coherent three-level hierarchy (bold table title, normal values, dim annotations). The `Chunk` cell is plain text with `#sequence`, which is readable when not truncated.

### Pillar 5: Spacing (2/4)

**WARNING — the comparison render has no vertical rhythm and gained two tables.** `_render_comparison` prints summary, legs, leg × split, context, groups, and the footer back-to-back with no blank line (`eval.py:549-564`); the phase added the legs and leg × split tables. Six sections of box-drawing characters merge into one wall at 80 columns. Add one blank line between tables and before the note block (phase 18's fix #7, still open).

**WARNING — density exceeds the canonical width.** The summary has 8 columns (`eval.py:383-393`), the new legs table 8 (`431-441`), and the groups table 10 (`520-532`). Only the 7-column leg × split table and the 2-column context table render cleanly at 80; Rich ellipsizes rather than reflows. This is the terminal analog of a layout that does not respond at the smallest breakpoint.

**WARNING — per-chunk search tables wrap every row at 80.** The vector per-chunk table has 5 columns and the hybrid 6 (`search.py:902-912, 1264-1275`); with title, chunk, collection, and snippet, every result becomes two to three lines and the chunk cell is ellipsized (see Pillar 2). The new escape hatch produces the least readable output at the most common width.

**Minor — CI cells break at every width** (`[0.0000,` / `0.0000]`) because the column is narrower than the value, even at 120 in the groups table. Use `overflow="fold"` or a wider/compact CI format.

**Pass — spacing values are consistent.** Rich default table padding throughout; no arbitrary padding overrides or ad-hoc blank-line counts; `soft_wrap=True` still protects saved paths and long warnings.

### Pillar 6: Experience Design (2/4)

**BLOCKER — `--min-score` breaks the filter's user task.** The threshold is derived as `rank >= 1 - 1/min_score` against a negative bm25 expression (`src/sif/search/bm25.py:76-97`), and the displayed score is `1/(1+|rank|)` (`171`, `231`). Because a better match has a larger absolute bm25 value, the filter keeps *weaker* matches. Verified live on the committed bench index: `sif search search "Saltiv Protocol Notes" -n 10` returns rank 1 `Saltiv Protocol Notes` at `0.1057` and rank 2 `Qelron Protocol Notes` at `0.1527`; `--min-score 0.23` returns `[]`, dropping both, best first. The help says "Minimum score threshold". A one-line display/filter fix is possible without changing ordering (and therefore without re-recording B0), but the current behavior must not ship. (Pre-existing formula, but Plan 19-05 made the threshold pre-pagination and pinned the direction in `TestBM25OffsetPagination`.)

**WARNING — per-chunk mode loses chunk identity in three supported output modes.** `sif search query --per-chunk --csv` emits `rank,score,title,path,collection,vectors_stale` with no chunk column (`search.py:423`), so three chunk rows of one document are identical except rank/score; `--md` and `--xml` likewise carry no `chunk_id`/`sequence` (`439-495`), and `--files` prints the same path once per chunk (`620-623` search, `1212-1215` query). The phase scoped CSV/Markdown/XML headers as "untouched", but D-03 calls chunk identity part of the public result contract; at minimum reject `--per-chunk` with machine formats or append `#sequence`/a `chunk` column. JSON and MCP are covered correctly (`SearchResult.to_dict()` at `models.py:326-344`; MCP re-map at `backend.py:190-197`).

**WARNING — the per-leg gate table hides `Sufficient` and absent splits render as zeros.** `_comparison_legs_table` has no `Sufficient` column (`eval.py:431-441`), so a body leg with N=5 displays like a valid gate; the JSON correctly carries `sufficient: false`. In `_comparison_leg_splits_table`, an absent split renders `body | heldout | 0 | +0.0000 | [0.0000, 0.0000] | no | no` (`eval.py:471-481`) because `noise_gate([])` returns zeroed means (`personal_bench.py:1928-1943`). The plan's "never a fabricated zero" intent is honored in JSON but not in the text table. Render `n/a`/`—` and add the column.

**Minor — a past-the-end page is indistinguishable from a zero-match query.** `--offset 100 -n 5` prints `No results found.` and exits 0 (verified), the same copy as a query with no matches (`search.py:665-669, 895-899, 1257-1261`). Add a page-aware empty state ("No results on this page; fewer matching documents than the offset"), especially since global ranks make paging an advertised interaction.

**Minor — no progress feedback for a potentially long query.** `sif search query` can load/download an embedding model and then run expansion, hybrid search, and optional reranking with no count or spinner (`search.py:1131-1194`); `ProgressTracker` exists in `src/sif/utils/progress.py` but is unused here. Carried from phase 18, not introduced.

**Minor — `sif search search --per-chunk` gives only Click's `No such option`.** The flag is correctly scoped to vsearch/query (D-01), but a user who read the docs is not pointed at the commands that do accept it. A one-line hint in the group help or error is cheap.

**Pass — the new interaction states are otherwise strong.** `--offset` is `IntRange(min=0)` and rejects `-1` with a clear range message (exit 2); a past-end offset is an empty page, never an error; global ranks continue across pages in table and JSON; the migration notice prints once with the document count, stays silent when the marker is written, and retries after a failure; suppressed groups and replay-unavailable reasons go to stderr while `--json` stays parseable; the MCP boundary forwards `chunk_id`/`sequence`/`chunk_matches` explicitly; `--per-chunk` is rejected by `sif search` and absent from `lex_search`.

---

## Minor Recommendations (not in top 3)

1. Add `chunk`/`sequence` to CSV/Markdown/XML output (or reject machine formats in per-chunk mode), and dedupe or annotate `--files` in per-chunk mode (`search.py:423, 439-495, 620-623, 1212-1215`).
2. Replace `Legs (D-12 gate input)` with user-facing wording and keep decision IDs out of shipped table titles (`eval.py:430`).
3. Print comparison notes with normal wrapping instead of the 80-character `_cell` cap (`eval.py:87, 95-100, 355`).
4. Use `×` in `Leg × split` and `leg × language × length` (`eval.py:460, 562`).
5. Make `Helped/Hurt/Unchanged` wrappable (spaces around `/`) or use `H/H/U` plus a legend in both tables (`eval.py:390, 438`).
6. Standardize `NDCG@10` vs `nDCG@10` across CLI output and docs.
7. Map raw retrieval enums to display names (`BM25`, `Hybrid`) in footer/context tables (`eval.py:357, 507`).
8. Add a `Sufficient` column to the per-leg table and render `n/a` for absent leg × split gates (`eval.py:431-481`).
9. Give the held-out row and winner/regression a distinct (still text-backed) emphasis (`eval.py:380-453`).
10. Add one blank line between comparison tables and before the note block (`eval.py:549-564`).
11. Resolved at HEAD — the benchmark doc now names the `vsearch` and `query` subcommands of `sif search`, and MCP `vec_search` is registered with `per_chunk` (`docs/benchmarking.md:208`; Phase 22, `src/sif/mcp/tools.py:344-407`).
12. Add a page-aware empty state for past-the-end offsets (`search.py:665-669, 895-899, 1257-1261`).
13. Add progress/count feedback around the model load and search loop in eval (reuse `ProgressTracker`).
14. Skip the leading H1 when extracting search snippets to stop duplicating the Title column (Phase 24 QUAL-03).
15. Consider a dedicated `Seq` column instead of embedding the sequence in a long path cell (`search.py:177-189`).

---

## Files Audited

- `src/sif/cli/commands/search.py` (HEAD, 1304 lines; 1164 at the phase-19 tree): flag blocks for `--offset`/`--per-chunk`; `_title_cell`; `_chunk_cell`; vsearch/query per-chunk tables; JSON/CSV/Markdown/XML/`--files` renderers; empty-state and DYM paths.
- `src/sif/cli/commands/eval.py` (HEAD, 1078 lines; 971 at the phase-19 tree): `_cell`/footer notes; summary, per-leg, leg × split, context, and groups tables; `_render_comparison`; JSON comparison payload consumption.
- `src/sif/cli/commands/index.py`: `_render_index_event` and the `migrate` line.
- `src/sif/core/models.py`: `SearchResult.to_dict()` chunk fields; `SearchOptions.per_chunk`/`offset`.
- `src/sif/search/bm25.py`: score mapping, pre-pagination `min_score` predicate, rank numbering.
- `src/sif/search/personal_bench.py`: comparison notes, `GateResult`, `leg_noise_gates`, `noise_gate` empty-input behavior.
- `src/sif/search/vector.py` / `hybrid.py`: global rank assignment and score semantics (spot-checked).
- `src/sif/mcp/backend.py`, `src/sif/mcp/protocol.py`, `src/sif/mcp/tools.py` (the phase-19 tree's `handlers.py` was deleted in Phase 22, `48d5a981`): `per_chunk`/`offset` inputs, schema sync, chunk-field re-map, registered tool set.
- `docs/cli-reference.md`: generated `--offset`/`--per-chunk` rows and min-score rows.
- `docs/benchmarking.md`: CORR-02 and CORR-04 sections, B0/B1 evidence, D-12 verdict narrative.
- `tests/unit/cli/test_search.py`: `TestPerChunkSurfaces` rendering/JSON assertions (unchanged at HEAD, line 4151; its one table assertion checks a short `path#sequence` and is width-agnostic). The exact title-cell width assertions relaxed in `c95d2cee` (`TestSearchOutputBranches`) were never evidence for this review.
- `tests/unit/cli/test_search_pagination.py`, `tests/integration/test_search_correctness.py`: pagination/rank contract (read for intent).
- Committed evidence artifacts: `bench/b0.json`, `bench/b1.json`, `bench/d12-verdict.json` (shape and decision verified).
- Live text captures (phase-19 tree at `763753d`): `search search|vsearch|query --help`; BM25 table at 80/100/120; `--offset 1` table and JSON (ranks 2–3); past-end table/JSON; `--offset -1`; `--per-chunk` rejection on `sif search`; vector/hybrid per-chunk tables at 80/100/120; per-chunk CSV/Markdown/XML/`--files`; default chunk-match annotation; `eval --compare` text at 80/100/120 and JSON; leg × split table with an absent split; per-leg table with an under-floor leg; migration notice over three index passes; stderr/stdout separation under `NO_COLOR`.
- Re-audit renders at HEAD (`bd6a8d8`, rich 15.0.0, no index): the vector and hybrid per-chunk tables and the `--compare` summary, per-leg, leg × split, and groups tables, re-rendered from the shipped table code with synthetic and B1-shaped rows at 79/80, 99/100, and 119/120 columns.

---

## Re-audit — 2026-11-26 (gap-closure plans 19-10, 19-11, 19-12)

**Audited:** 2026-11-26. Everything above is the 2026-11-18 audit as re-pinned on 2026-11-25, kept as written; its score and findings are not edited here. This section is additive. It covers what plans 19-10, 19-11 and 19-12 changed on the user-facing surface, the status of every earlier finding, seven new findings (`R2-01` to `R2-07`) and a new score.
**Baseline:** unchanged — no `UI-SPEC.md`; abstract 6-pillar standards adapted to the Click/Rich terminal surface. The functional contract is still decisions D-01 to D-12 in `19-CONTEXT.md`, the operator's recorded decision `monotone-map` (`19-11-SUMMARY.md`, `Decision:` line) and the two human checks the orchestrator approved on 2026-11-26 (`19-10-SUMMARY.md:327-356`).
**Scope:** only the changed surface: the per-chunk tables of `sif search query --per-chunk` and `sif search vsearch --per-chunk`, and the per-chunk `--csv`, `--md`, `--xml` and `--files` output (19-10); the `--min-score` help text of `sif search search` and the changed score values in every output format, MCP `lex_search` included (19-12). Plan 19-11 changed no behaviour and has no surface of its own. Everything else above is carried, not re-examined.
**Screenshots:** not captured — no web UI exists (no `.tsx`, `.jsx`, `.css` or `.scss` file under `src/`, no `components.json`); ports 3000 and 5173 are closed and 8080 serves an unrelated SearXNG. No screenshot was taken, so the gitignore gate was not run.
**Interaction captures:** off, as on 2026-11-18 (`workflow.ui_interaction_capture` is not set in `.planning/config.json`). CLI states were exercised directly; see Evidence.
**Registry audit:** skipped — no `components.json`.

### Evidence

- **Tree.** Source, tests and docs at `d5382ae`. HEAD moved to `4cf172c` during the audit; the two later commits (`e822b28`, `4cf172c`) touch only `19-12-SUMMARY.md` and `.planning/WINDOWS.md`, so the code and docs read here are HEAD's. `git diff --quiet 2154b75..HEAD` (the last audit's commit) exits 0 for `eval.py`, `index.py`, `core/models.py`, `src/sif/mcp/`, `vector.py`, `hybrid.py`, `rrf.py`, `personal_bench.py`, `docs/mcp-server.md`, `README.md`, `docs/quickstart.md`, `docs/search-algorithms.md` and `docs/models.md`: every earlier finding that lives in those files is unchanged by construction.
- **Environment.** PATH `sif`, `pytest` and `python`: Python 3.13.9, rich 14.3.3, click 8.3.2. The project interpreter `.venv` (Python 3.10.22, rich 15.0.0 as `uv.lock` pins) gave identical per-chunk renders.
- **Live, isolated, BM25-only.** `SIF_DB_PATH` and `SIF_CACHE_DIR` in a `mktemp -d` directory, removed afterwards; no model was loaded and the cache directory was never created. Captured under `NO_COLOR=1`: `--help` of the three subcommands; the `search` table at 80, 100 and 120 columns and `--json`, `--csv`, `--md`, `--xml`, `--files` and `-q`; a 22-value `--min-score` sweep on a 20-document copy of the corpus of `tests/unit/cli/test_search_min_score.py`; the probe query and a threshold sweep over the 56 queries of `tests/fixtures/bench/queries.json` on `tests/fixtures/bench/corpus` (150 documents, indexed as `bench-fixture`).
- **Tests at HEAD.** `pytest tests/unit/cli/test_search.py::TestPerChunkSurfaces tests/unit/cli/test_search_min_score.py -p no:cacheprovider --no-cov -q` gave 32 passed.
- **MCP schema.** `tools/list` was read from `register_tools(server, None)` without entering the lifespan, so no backend, database or cache was constructed.
- **Per-chunk tables — not rendered live.** I did not run `sif search vsearch` or `sif search query` against any index and did not render them live: both need an embedding model, which this audit was barred from loading, and no index was built for them. Their evidence is (1) the 32 tests above; (2) the orchestrator's recorded human checks 1 and 2 (`19-10-SUMMARY.md:327-356`), quoted as its record and not re-run; and (3) the shipped table code re-rendered without an index or a model through the mocked searchers the tests use (`Console(width=…)`, synthetic rows) at 80, 100 and 120 columns, which is the method the 2026-11-25 re-audit used. (3) shows what the code draws for those rows; it is not a capture of real search output. The per-chunk CSV, Markdown, XML and `--files` output was not re-rendered at all: what is said about it below is taken from the tests' exact assertions and from human check 2.
- **Own slips.** Four throwaway capture scripts stopped on a syntax, attribute or value error before writing any output. They were corrected and re-run; no figure in this section comes from a failed run.

### Pillar Scores (2026-11-26)

| Pillar | 2026-11-18 | 2026-11-26 | What moved |
|--------|------------|------------|------------|
| 1. Copywriting | 2/4 | 3/4 | The `--min-score` copy no longer contradicts the behaviour; the two comparison-table warnings are carried untouched; one new minor |
| 2. Visuals | 2/4 | 3/4 | `Score` now falls down the list and `#sequence` survives 80 columns on both tables; the comparison report is still unreadable at 80 (carried); one new warning and one new minor on the hybrid per-chunk table |
| 3. Color | 3/4 | 3/4 | Unchanged; the self-sizing Chunk cell keeps its magenta column style |
| 4. Typography | 3/4 | 3/4 | Unchanged |
| 5. Spacing | 2/4 | 2/4 | Unchanged: the comparison tables and the 12-line hybrid per-chunk rows at 80 columns are as before |
| 6. Experience Design | 2/4 | 3/4 | `--min-score` keeps the best match and chunk identity reaches every format; the band where a threshold bites is undiscoverable (new); the per-leg table warning is carried |

**Overall: 17/24** (2026-11-18 and 2026-11-25: 14/24)

The scores use the calibration the earlier report implies: a pillar that holds a BLOCKER, or three or more open WARNINGs, sits at 2; one or two WARNINGs without a BLOCKER sit at 3. Copywriting, Visuals and Experience Design each lost a BLOCKER or their third WARNING; Spacing kept its three. No pillar is at 4, because each keeps at least one open WARNING or three open Minors.

| Severity | 2026-11-18 | Closed by 19-10 and 19-12 | Carried | New | 2026-11-26 |
|----------|------------|---------------------------|---------|-----|------------|
| BLOCKER | 2 | 2 | 0 | 0 | 0 |
| WARNING | 10 | 3 | 7 | 2 | 9 |
| Minor | 17 | 0 | 17 | 5 | 22 |

### Top 3 Priority Fixes (2026-11-26, whole surface)

1. **Carried — the `sif eval --compare` evidence is still unreadable at 80 columns and still renders under-floor gates like valid ones** (earlier top fix 3; `eval.py:380-564` is byte-identical to the last audit). Plans 19-10 to 19-12 did not touch it, and with the two BLOCKERs closed it is the heaviest open defect.
2. **R2-01 — say where a BM25 threshold bites** — `--min-score` now keeps the best match, but nothing a user reads tells them that values up to about 0.85 remove nothing and that the direction is stated in one help line only — add one clause to the `search --min-score` help, the same sentence to the `lex_search` description and `docs/mcp-server.md`, and make the emptied page name the threshold (`search.py:643-646, 782-786`; `src/sif/mcp/tools.py:318`).
3. **R2-02 — give the hybrid Chunk column its directory back** — at 80 columns the column shows a file-name tail, so two documents with the same file name print the same cell and are told apart only by wrapped Title lines — when the file name repeats on the page, spend the width on the deepest distinguishing directory plus the name, or split out a narrow `Seq` column (`search.py:207-229, 263-273, 1401`).

### Status of the Earlier Findings

Only the findings the three plans touched were re-examined. "Not re-examined" means the file is byte-identical to the last audit's tree (see Evidence).

| Pillar | Earlier finding, as titled above | 2026-11-26 |
|--------|----------------------------------|------------|
| 1 | BLOCKER — `--min-score` copy contradicts the behavior | **Resolved** for `sif search search` (19-12). The same words on `vsearch` and `query` no longer contradict the behaviour; what remains is R2-03 |
| 1 | WARNING — internal decision ID in shipped table output | Open; not re-examined |
| 1 | WARNING — the 80-char cell cap still truncates the comparison notes | Open; not re-examined |
| 1 | Resolved at HEAD — the benchmark section names no missing command | Still resolved (`docs/benchmarking.md:208` unchanged) |
| 1 | Minor — plain `x` instead of `×`; Minor — schema/UI terminology drift | Open; not re-examined |
| 1 | Minor — hand-written docs leak milestone jargon | Open, and 19-12 added one instance (see Pillar 1) |
| 2 | WARNING — the per-chunk table's identity signal is truncated away at 80/100 columns | **Resolved** for the sequence (19-10); a lesser residual is R2-02 |
| 2 | WARNING — the comparison report is unreadable at 80 columns | Open; not re-examined |
| 2 | WARNING — the `Score` column is visually anti-monotonic | **Resolved** (19-12) |
| 2 | Minor — no focal point in the comparison; Minor — the snippet duplicates the title | Open. The leading H1 is still on every row of the live 80-column capture |
| 3 | Minor — all-cyan comparison tables; no winner emphasis; five column colours | Open; not re-examined. The Chunk cell keeps its magenta style (see Pillar 3) |
| 4 | Minor — unwrappable header, `Tuning (diagnostic)`, NDCG spelling, lowercase enums, letter `x` | Open; not re-examined |
| 5 | WARNING — no vertical rhythm; density; per-chunk rows wrap at 80 columns | Open. The per-chunk tables end at their right border at 80, as they did before 19-10, and their rows still wrap (see Pillar 5) |
| 5 | Minor — CI cells break at every width | Open; not re-examined |
| 6 | BLOCKER — `--min-score` breaks the filter's user task | **Resolved** (19-12) |
| 6 | WARNING — per-chunk mode loses chunk identity in three output modes | **Resolved** (19-10); a residual is R2-06 |
| 6 | WARNING — the per-leg gate table hides `Sufficient`; absent splits render as zeros | Open; not re-examined |
| 6 | Minor — a past-the-end page looks like a zero-match query | Open. A threshold that empties the page reaches the same copy (R2-05) |
| 6 | Minor — no progress feedback; `--per-chunk` rejection gives only `No such option` | Open. The rejection was re-run: exit 2, `No such option: --per-chunk` |

The six Pass entries above still hold on their own terms; what they describe was not re-checked beyond the captures listed under Evidence.

### Detailed Findings (2026-11-26)

#### Pillar 1: Copywriting (3/4)

**Resolved — the `--min-score` help no longer contradicts the behaviour.** `sif search search --min-score` now reads "Keep matches scoring at least this value (0-1, higher is a stronger match); 0 keeps all, 1 or more keeps none" (`search.py:643-646`), and its generated row carries the same words (`docs/cli-reference.md:538`). Live: the help's three claims each hold (see R2-01 for the first, and the sweep under Evidence for the other two: `--min-score 1`, `1.5` and `2` returned `[]`; `0` returned every row).

**New, R2-03 (Minor) — `vsearch` and `query` keep "Minimum score threshold": no longer wrong, still not saying which score.** `search.py:848` and `:1084`; `docs/cli-reference.md:495` and `:573`. The text does not mislead on direction any more. Before 19-12 the BM25 leg ran the other way, so "minimum" was false for it; now both legs rise with relevance — BM25 as the magnitude over one plus itself (`src/sif/search/bm25.py:47-57`), vector as one minus half the cosine distance (`src/sif/search/vector.py:335`) — and 19-12 made the old text more true, not less. What it still omits is the referent. Each leg is filtered on its own score (`src/sif/search/hybrid.py:121-143`, `vector.py:308, 315`) and the fused `Score` column, an RRF sum (`src/sif/search/rrf.py:157`), is never compared with the threshold. The orchestrator's recorded human check for 19-12 shows the gap: `sif search query … --min-score 0.3 --json` returned a page byte-identical to the unthresholded one, while its `Score` values were near `0.03` and its `bm25_score` values `0.8873`, `0.8333` and `0.7538` (`19-12-SUMMARY.md`, Human Check). One number therefore has two strengths, and three sibling flags now carry two descriptions with nothing to say whether the `search` contract carries over. The text was kept on purpose because the filters read differently, and the gap predates the plans. One sentence closes it: "Each leg is filtered on its own score; the Score column is not compared."

**Carried and extended — hand-written docs leak milestone jargon.** The new score-direction note (`docs/benchmarking.md:247`) keeps the retired values in its sentence (`0.105703 → 0.0957`) and repairs them in a dated parenthetical of about 900 characters that names "plan 19-12" and cites `.planning/milestones/v1.2-phases/19-search-correctness/bench/g19-2-min-score.json`, a path a reader of the published docs cannot open. Line `:225` points at the same note. State today's values in the sentence, keep the retired ones in the parenthetical, and drop the plan number and the path.

**Pass — the new text is specific and accurate.** Both changelog entries name the flag, the formats, the formula and the migration rule ("to convert a threshold written against the old scores, subtract it from 1", `docs/changelog.md:25`). The 19-12 entry is one bullet of 1,010 characters; a reader who wants that rule must reach its last clause.

#### Pillar 2: Visuals (3/4)

**Resolved — the `Score` column falls down the list.** Live at 80 columns on the bench-fixture index: rank 1 `Saltiv Protocol Notes` at `0.8943`, rank 2 `Qelron Protocol Notes` at `0.8473`, where the earlier audit captured `0.1057` and `0.1527`. The order is fixed by construction (`ORDER BY m.score`, `bm25.py:176, 198`) and pinned by `tests/unit/search/test_bm25.py:560`.

**Resolved — every chunk row keeps its `#sequence` at 80 columns.** Both tables end at their right border there, with and without the Content column (`tests/unit/cli/test_search.py:4441-4498`, 32 passed; re-render at 80, 100 and 120 under both interpreters; human check 1). UAT test 1's criterion, "every chunk row shows which chunk it is", is met.

**New, R2-02 (WARNING) — in the hybrid layout the Chunk column shows a file-name tail, so same-named documents are indistinguishable in it.** The reported defect is closed; the price is the other half of `path#sequence`. `_fit_head` keeps the suffix and the longest tail that begins after a path separator, cutting from the left (`search.py:207-229`), and the hybrid table gives that cell 14 to 15 cells of text at 80 columns, 10 with `--full --line-numbers`, because Snippet takes the rest (`search.py:1392-1405`). Re-rendered from the shipped code with the two same-named files of human check 1 (100-character paths under `corpus/alpha` and `corpus/beta`):

```
query   80:  …ce-notes.md#0  …ce-notes.md#1  …ce-notes.md#0  …ce-notes.md#1   (alpha and beta alike)
query  100:  …aintenance-notes.md#0 …                                       (still alike)
query  120:  …-and-maintenance-notes.md#0 …                                  (still alike)
vsearch 80:  …maintenance-notes.md#0 …                                       (alike; 2-line rows)
```

At 80 columns the Title cell wraps to `Zorbatic` / `Capacitor` / `Calibration` / `Notes` against `Zorbatic` / `Capacitor Field` / `Notes`, so the rows are told apart by lines two and three of the Title, not by the column that exists to address the chunk. That is what human check 1 recorded. With the test file's own three documents, all named `protocol-notes.md`, the cells are `…col-notes.md#0`, `…col-notes.md#3` and `…col-notes.md#6`: the path portion is the same and is cut mid-word. The vector layout is sound at 80 columns (23 to 37 cells of text, for example `…maintenance-notes.md#0` and `/notes/chunky/protocol-notes.md#0`). Fix: when the file name repeats on the page, spend the budget on the deepest directory that tells the rows apart plus the name (`…/beta/…-notes.md#0`), or add a narrow `Seq` column and let the Chunk cell keep the head of the path (earlier recommendation 15). `search.py:207-229, 263-273, 1401`.

**New, R2-07 (Minor) — a per-chunk hybrid page mixes chunk rows with document-level rows, and only the absent `#n` says which is which.** The BM25 leg returns documents, so `sif search query --per-chunk` yields rows without a sequence (the fallback in `_chunk_cell`, `search.py:253-260`). They render `…tocol-notes.md` beside `…col-notes.md#0` and nothing marks them as document-level; the Title cell, where `(stale vectors)` and `(N chunk matches)` already have a dim home (`search.py:169-187`), says nothing. The help's "Return one row per matched chunk instead of one row per document" (`search.py:1127`, `docs/cli-reference.md:575`) promises more than the hybrid page delivers. The formats are consistent with it: an empty `sequence` cell in CSV, no `Sequence:` line in Markdown, no `<sequence>` element in XML, `null` in JSON (`tests/unit/cli/test_search.py:4573-4624`). `19-10-SUMMARY.md:361` records the behaviour as a residual observation. Fix: a dim `(document)` on such rows in per-chunk mode, and half a sentence in the help.

#### Pillar 3: Color (3/4)

**Unchanged.** A re-render with colour forced (truecolor) gave the same column styles as before the change: cyan rank, green score, yellow title, magenta chunk (`\x1b[35m`), blue collection, white snippet. The self-sizing Chunk cell did not lose its column style, and the table still ended at its right border. The earlier palette note (five column colours, no legend) stands; nothing here is colour-only.

#### Pillar 4: Typography (3/4)

**Unchanged.** The Chunk cell is still plain text; when shortened it now begins with `…` and is measured in display cells, so a CJK file name counts double width as Rich does (`tests/unit/cli/test_search.py:4544-4561`). Scores keep four decimals in every format; what that costs the threshold is R2-04, under Pillar 6.

#### Pillar 5: Spacing (2/4)

**Still open — hybrid per-chunk rows wrap at 80 columns.** The tables end at their right border, as they did before 19-10 (`19-10-SUMMARY.md:198`), but the hybrid layout still gives Snippet about 15 cells: 12 to 13 physical lines per row (four rows make 53 to 57 lines), and 20 to 21 with `--full --line-numbers`, where Chunk gets 10 cells, Snippet 11 and Content 10 and the Title cell renders `Document-…`. The vector table is one line per row, two when the title wraps. The column shares are the same as before the change (`19-10-SUMMARY.md:226`), so 19-10 neither caused nor eased this. The comparison-table findings are carried.

#### Pillar 6: Experience Design (3/4)

**Resolved — `--min-score` keeps the best BM25 matches.** Live on the probe index: four matches score `0.8803`, `0.8456`, `0.8456`, `0.8456`; `--min-score 0.85` leaves rank 1 alone, still numbered `1`. That the filter runs before the page is sliced is pinned where it can be seen, in the SQL and its parameters (`bm25.py:130-134, 175-177, 197-199`; `tests/unit/search/test_bm25.py:84, 621`). `--min-score 1` returns `[]`. Through the real CLI: `tests/unit/cli/test_search_min_score.py:108-136`. Ranking without a threshold is unchanged: B0 and B1 each report 100 unchanged, mean delta 0.0 (`bench/g19-2-min-score.json`).

**Resolved — chunk identity reaches the machine formats.** Per-chunk CSV gains a last `sequence` column and carries the `path#sequence` address in `path`; Markdown gains a `Sequence:` line; XML a `<sequence>` element; `--files` and `-q` list each path once (`tests/unit/cli/test_search.py:4573-4687`, human check 2). Output without `--per-chunk` is pinned unchanged by three guards and by 19-10's 3,840-comparison differential. One cost is recorded for the operator's awareness and not counted: in per-chunk CSV, Markdown and XML the `path` field is an address on chunk rows, not a filesystem path, so a consumer that opens `path` must strip `#n` or use `--files`. That is D-03's display form and the layout the orchestrator approved on the operator's behalf (human check 2, a decision row).

**New, R2-01 (WARNING) — the band where a BM25 threshold bites is not discoverable, and the direction is stated in one help line only.** The new help text is true, and it is the only place a user is told the direction. Not stated in: the table header (`Score`, `search.py:790, 1024, 1394`); the CSV, Markdown and XML `score` (`:520, 547, 576`); `--json`, where `score` is a bare number and `scores` is `{}` on BM25 rows; `sif search search --explain`, which prints only `Query:` and `Results: N` (`:814-816`); the MCP schema, where `min_score` is published as `{"default": 0.0, "minimum": 0.0, "title": "Min Score", "type": "number"}` and the result's `score` as `{"title": "Score", "type": "number"}` on all three tools (`src/sif/mcp/tools.py:140, 318, 358`; `src/sif/mcp/protocol.py:40`); `docs/mcp-server.md:134` ("Minimum score threshold (default: 0.0)"), whose `:188` and `:193` only list `min_score`; `docs/models.md:486` ("0.0-1.0 (convention, not enforced)"); and `README.md`, `docs/quickstart.md` and `docs/search-algorithms.md`, which do not mention the flag. The direction appears only in `search.py:643-646`, its generated row, `docs/changelog.md:25` and `docs/benchmarking.md:247`. The Phase 22 review recorded the behaviour this replaces as a BLOCKER on the MCP surface (`22-UI-REVIEW.md`); the behaviour is fixed for `lex_search`, the description is not.

"(0-1)" also describes a scale of which most is dead. Measured on `tests/fixtures/bench/corpus` (56 queries, 42 with a match, 84 rows): every displayed score lies between `0.8473` and `0.9649`, and rank 1 scores `0.8939` to `0.9649` (median `0.9503`). `--min-score` 0.5, 0.7 and 0.80 keep 84 of 84 rows and remove nothing; 0.85 keeps 70 (83%); 0.90 keeps 56 (67%) and empties 14 of the 42 pages; 0.95 keeps 29 and empties 21; 0.99 keeps none. On the 20-document probe index nothing below 0.85 removes a row, and the whole spread is `0.8456` to `0.8803`. So the working band is the top 15% of the advertised scale, and on a query with few matches it is a few hundredths wide. A user who tries 0.5 sees no effect; one who tries 0.9 gets `No results found.` (R2-05). Both corpora are synthetic, so the exact band is theirs. The floor is not: the map gives 0.5 to any match whose bm25 magnitude is 1 (`bm25.py:47-57`), and it compresses hard — the probe's strong document repeats each query word 48 times and scores `0.8803` against `0.8456` for a single mention, so the `Score` column cannot show how much stronger the best match is. The map is the operator's recorded decision and is not re-litigated here. Fix: one more clause in the help that names the band ("BM25 matches mostly score above 0.85; lower values remove nothing"), with the measured band for the operator's own corpus if it differs; "rises with relevance" in the `lex_search` description and `docs/mcp-server.md:188`; and the emptied page of R2-05.

**New, R2-04 (Minor) — a row's displayed score, passed back as `--min-score`, can drop that row.** Every human format prints four decimals (`search.py:800, 1039, 1410`; CSV `:520`; Markdown `:547`; XML `:576`), but the predicate compares the unrounded value (`bm25.py:130-134`). Live on the probe index: rank 1 prints `0.8803` and `--min-score 0.8803` returns `[]`, while `--min-score 0.8802816013881186`, the `--json` value, keeps it. Ranks 2 to 4 print `0.8456` and `--min-score 0.8456` keeps them, because their value rounds down. "Keep matches scoring at least this value" therefore holds or fails by the direction of the rounding, and the natural move of cutting at a row loses that row about half the time. `19-12-SUMMARY.md` records the last-bit boundary in its tests, not this display gap, which is up to 0.00005. Fix: round the threshold down to four decimals before binding it, one line in `bm25_rank_threshold`, or compare the displayed value.

**New, R2-05 (Minor) — a threshold that removes every match looks like a query with no match, and out-of-range values pass silently.** `--min-score 0.9` on the probe's four-match query prints `No results found.`, the same text as a zero-match query (`search.py:782-786`); `--explain` prints nothing on an empty page, because its block at `:814-816` sits after that `return`; CSV, Markdown and XML emit only the header. `-0.5` and `nan` keep everything and `1.5` and `2` keep nothing, each with exit 0 and an empty stderr. The option is a bare `float` (`search.py:641-647`), so `--help` shows `FLOAT` with no range beside `--limit … [x>=1]` and `--offset … [x>=0]`, while MCP rejects a negative value (`Field(ge=0.0)`, `src/sif/mcp/protocol.py:98, 131, 159`). This is the earlier past-the-end minor reached by a second route, and 19-12 makes it the common outcome of a too-high threshold. Fix: `No results found (min score 0.9).` in the empty state, the `explain` lines above the `return`, and a `FloatRange(min=0)` on the option.

**New, R2-06 (Minor) — a path-only per-chunk page is shorter than `--limit`, and nothing says so.** `--per-chunk` with `--files` or `-q` prints each path once (`search.py:276-278, 1001, 1338`) while `--limit` and `--offset` still count chunk rows. So `--per-chunk --files -n 3` printed two lines in `tests/unit/cli/test_search.py:4661-4672`, and 19-10's own live render printed six lines for a twelve-row page (`19-10-SUMMARY.md:287`). The lines are plain paths, without `#sequence`. `--files` says "Output file paths only" (`:1134`), `--limit` "Number of results" (`:1067`), `--per-chunk` "Return one row per matched chunk…" (`:1127`); only `docs/changelog.md:24` states the collapse. Adding `--per-chunk` to a `--files` pipeline therefore shortens its output. The de-duplication is what the earlier report asked for (recommendation 1) and is right for piping. Fix: one clause in the `--per-chunk` help, "with --files each path is listed once".

**Pass — the changed states hold.** The threshold is bound as a parameter in the outer `WHERE` of both SQL branches, ahead of `LIMIT ? OFFSET ?` (`bm25.py:130-134, 175-177, 197-199`); `--min-score 1` returns `[]` as documented; a negative value and NaN keep every row; `sif search search` still rejects `--per-chunk` (exit 2) and `vsearch` still rejects `--csv` and `--files` (exit 2), as D-01 requires.

### The Three Questions Put to This Re-audit

| Question | Answer | Finding |
|----------|--------|---------|
| Is the score's direction stated anywhere a user sees it, other than that one help line? | No. Not in the table header, CSV, Markdown, XML, `--json`, `--explain`, the MCP schema, `docs/mcp-server.md`, `docs/models.md`, the README or the quickstart. Only in the generated `docs/cli-reference.md:538` row (the same text), the changelog and a benchmarking note. The MCP tool description says only that `lex_search` matches `sif search search`. | R2-01 |
| Does `query --min-score` keeping "Minimum score threshold" mislead now that its two legs filter on different scales? | Not on direction: both legs now rise with relevance, so 19-12 made the old text more true. It still does not say that each leg is filtered on its own score and that the fused `Score` column is never compared. | R2-03 |
| Is the 0.85-and-above band where a BM25 threshold bites discoverable? | No. On the bench fixture every score lies in 0.8473 to 0.9649 and thresholds up to 0.80 remove nothing; the help says only "(0-1)". | R2-01, R2-05 |

### Recommended Follow-ups (not done here)

1. R2-01: extend the `search --min-score` help with the band; say "rises with relevance" in the `lex_search` description and `docs/mcp-server.md:188`. Test: pin the documented band against `tests/fixtures/bench/corpus` (every displayed score above the stated floor; a threshold below it keeps every row).
2. R2-02: make `_fit_head` prefer a directory that tells the rows of the page apart when file names repeat, or split out a `Seq` column. Test: a render test with two same-named files asserting that the Chunk cells differ at 80 columns.
3. R2-03: one sentence on `query` and `vsearch` naming the score that is compared.
4. R2-04: round the threshold to the displayed precision. Test: a CLI test that passes each row's printed score back and expects the row to survive.
5. R2-05: a threshold-aware empty state, `--explain` before the `return`, `FloatRange(min=0)` on the three commands.
6. R2-06 and R2-07: one clause each in the `--per-chunk` help; a dim `(document)` on document-level rows of a per-chunk page.
7. `docs/benchmarking.md:247`: today's values in the sentence, no plan number, no `.planning` path.

### Files Audited (2026-11-26)

- `src/sif/cli/commands/search.py` (1434 lines): the three `--min-score` and two `--per-chunk` options; `Score` and `Chunk` columns; `_fit_head`, `_ChunkAddress`, `_chunk_column`, `_unique_paths`; the three formatters with `per_chunk`; the empty-state and `explain` blocks.
- `src/sif/search/bm25.py`: `bm25_display_score`, `bm25_rank_threshold`, the predicate in both SQL branches, `ORDER BY`.
- `src/sif/search/hybrid.py`, `vector.py`, `rrf.py` (read for the `query` and `vsearch` legs; unchanged since the last audit).
- `src/sif/mcp/tools.py`, `protocol.py`: the published `min_score` and `score` schema entries (`tools/list` read without a backend).
- `tests/unit/cli/test_search.py` (`TestPerChunkSurfaces`, 30 items), `tests/unit/cli/test_search_min_score.py` (2 items), `tests/unit/search/test_bm25.py` (test names only).
- `docs/cli-reference.md` (`:495, 504, 538, 573, 575`), `docs/changelog.md` (`:24, 25`), `docs/benchmarking.md` (`:225, 247`), `docs/mcp-server.md` (`:134, 188, 193`), `docs/models.md` (`:486`), `README.md`, `docs/quickstart.md`, `docs/search-algorithms.md` (searched for the flag and for example scores).
- `19-CONTEXT.md`, `19-10-SUMMARY.md`, `19-11-SUMMARY.md`, `19-12-SUMMARY.md` (at `4cf172c`, where its Task 3 human check is recorded as approved), `19-UAT.md`, `bench/g19-2-min-score.json` (as quoted in the 19-12 summary), `22-UI-REVIEW.md` (the `min_score` item).
- Live captures: `sif search --help`; `search`, `vsearch` and `query` `--help`; the `search` table at 80, 100 and 120 columns; `--json`, `--csv`, `--md`, `--xml`, `--files`, `-q`; the 22-value threshold sweep; the empty state in six formats; the fixture threshold sweep (56 queries).
- No-index re-renders of the shipped table code with synthetic rows: both per-chunk tables at 80, 100 and 120 columns, plain and with `--full --line-numbers`, with long paths, with two same-named files and with a document-level row; one colour-forced render for the column styles.
