# Phase 04 — UI Review

**Audited:** 2026-09-04
**Baseline:** Abstract 6-pillar standards (no UI-SPEC.md). User-facing surface is Rich terminal output: `src/sif/cli/commands/search.py` (`search`, `vsearch`, `query`) and `src/sif/cli/commands/bench.py`.
**Screenshots:** Not captured — no web frontend and no dev server (CLI-only project). Audit is code-level against the Rich output paths.

---

## Pillar Scores

| Pillar | Score | Key Finding |
|--------|-------|-------------|
| 1. Copywriting | 3/4 | `--explain` on `search search` prints only "Query: X / Results: N" — restates input, explains nothing |
| 2. Visuals | 3/4 | Clear table hierarchy, but `--explain` scores are detached dim footer lines matched only by truncated title |
| 3. Color | 3/4 | Consistent semantic Rich colors, yellow doubles as Title-column style and warning style |
| 4. Typography | 3/4 | Largely N/A for terminal; only `dim` markup used, no bold emphasis on titles/metric names |
| 5. Spacing | 3/4 | Mostly N/A; no column `no_wrap`/`overflow` control, unbounded collection/content widths, 3 duplicated table blocks |
| 6. Experience Design | 2/4 | Empty/quiet states handled, but bench silently continues with no embedder and snippets are never shown |

**Overall: 17/24**

---

## Top 3 Priority Fixes

1. **`search_cmd --explain` is a no-op explanation** (`src/sif/cli/commands/search.py:232-234`) — the flag's help says "Show search explanation" but output only echoes the query and result count, misleading users who expect BM25/RRF breakdowns like `query --explain` provides. Fix: either remove the flag from `search search` (BM25-only has no stages to explain beyond the score already shown) or print term-level FTS match info; do not restate input.
2. **`bench` continues after embedder load failure** (`src/sif/cli/commands/bench.py:86-89`) — on failure it prints a yellow warning, sets `manager = None`, and proceeds; the pipeline silently degrades to a non-vector search, so reported precision/recall/MRR are benchmarking a different configuration than the user thinks. Fix: `raise click.ClickException(...)` on embedder failure (or add an explicit `--allow-no-embedder` opt-in with a nonzero-warning banner in output).
3. **Snippets and highlights are computed but never rendered** (`search.py:493-502` wires `SmartSnippetExtractor`; the table at `search.py:553-575` has no Snippet/Content column unless `--line-numbers` is passed) — SRCH-07 is invisible to table users, and `include_highlights=True` results are only surfaced in `--md` output. Fix: add a truncated Snippet column to the default rich table when `r.snippet` or `r.highlights` exist.

---

## Detailed Findings

### Pillar 1: Copywriting (3/4)
- Good: "No index found. Run 'sif update' first." (search.py:128) and the vsearch variant (search.py:274-276) are actionable with the recovery command; "No results found." (search.py:205, 340, 550) is clear; bench fixture format documented in the docstring (bench.py:48-60).
- WARNING: `search search --explain` footer (search.py:232-234) prints `Query: {query}` and `Results: {len(results)}` — data the user just typed/saw. The flag name and help text promise more.
- WARNING: `query --explain` footer (search.py:577-581) prints full-length titles (`r.title` is not truncated here, unlike the table's 50-char cap), so long titles make score lines wrap and misalign with the table above.
- MINOR: vsearch has no `--explain` while `search` and `query` do — asymmetric surface invites user confusion about which flags exist where.

### Pillar 2: Visuals (3/4)
- Good: every table uses the same column set with per-column color, right-justified numeric columns (`#`, `Score`), and a quoted-query title — consistent, scannable focal hierarchy (search.py:208-212, 343-347, 553-557; bench.py:135-137).
- WARNING: explain scores are printed as detached `[dim]` lines after the table (search.py:577-581), matched to rows only by (untruncated) title. The 04-CONTEXT decision allowed "Explain column or footer"; the footer implementation breaks row association as soon as two results share a title prefix.
- WARNING: the table-building block is duplicated three times nearly verbatim (search.py:201-234, 337-365, 546-581). Drift has already begun (only the first block has the explain footer).

### Pillar 3: Color (3/4)
- Class usage (identical across all three tables): `#`→cyan, Score→green, Title→yellow, Collection→blue, Content→white; warnings/empty states→`[yellow]`; meta→`[dim]`. No hardcoded hex/RGB anywhere in the CLI command modules.
- WARNING: yellow is both the "Title" data color and the warning/empty-state color (search.py:128, 205 vs. 211). In a terminal where the rest of a row is unstyled, a yellow title reads at the same urgency as a warning.
- No accent overuse; 60/30/10 has no strict analog here — base table + colored columns + dim meta is a reasonable terminal equivalent.

### Pillar 4: Typography (3/4)
- Explicitly noting applicability: font family/size are terminal-controlled; the auditable surface is Rich markup. Size hierarchy comes only from the Table title vs. rows (Rich defaults). Weight/emphasis markup used: `dim` only (search.py:233-234, 489-491, 577-581). No `bold` anywhere — table titles and the bench metric names rely on Rich's default header styling alone. Acceptable but flat; one `bold` on the result-count or metric name would aid scanning. No mixed-size violations possible.

### Pillar 5: Spacing (3/4)
- Explicitly noting applicability: padding/gap scales are N/A; Rich handles cell padding. Auditable: column width behavior and duplication.
- WARNING: no `no_wrap`/`overflow="ellipsis"` on any column; truncation is manual (`title[:50] + "..."`, search.py:220/355/565) and collection names and the 200-char content column (search.py:226) are width-unbounded, so narrow terminals will produce wrapped, ragged rows.
- WARNING: three copies of the truncation constants/logic (see Pillar 2) — any spacing/width fix must currently be applied three times.
- No arbitrary magic spacing values beyond the two named display constants (`_TITLE_MAX_LEN`, `_CONTENT_MAX_LEN`), which are at least module-level named.

### Pillar 6: Experience Design (2/4)
- Good: empty results and missing index both handled with distinct messages; `--quiet`/`--files` give clean piping output (search.py:164-166, 509-511); errors raised as `click.ClickException` per project convention (search.py:293-295, 476-478; bench.py:129); `--candidate-limit` validated via `click.IntRange(1, 200)` (search.py:376-382).
- BLOCKER-adjacent WARNING: bench degrades silently with no embedder (bench.py:80-89) — benchmark output does not indicate it ran without vector search; see Top Fix 2. (Not scored 1 because the empty/error paths that break task completion are all handled; this degrades trust rather than breaking the run.)
- WARNING: no loading/progress feedback while the embedding model loads and a probe embed runs (search.py:471-478) — for a local GGUF model this can take tens of seconds with zero terminal feedback.
- WARNING: reranker-unavailable fallback is warning-only (search.py:483-491) which is reasonable, but combined with silent snippet non-display, users cannot tell from output which pipeline stages actually ran — `--explain` only surfaces scores, never stage status (e.g., "reranker: skipped").

---

## Files Audited
- /Users/forrest/GitHub/SIF/src/sif/cli/commands/search.py
- /Users/forrest/GitHub/SIF/src/sif/cli/commands/bench.py
- /Users/forrest/GitHub/SIF/src/sif/core/models.py (to_dict / SearchResult surface)
- /Users/forrest/GitHub/SIF/.planning/phases/04-advanced-search-pipeline/04-01..05-SUMMARY.md, 04-01..05-PLAN.md, 04-CONTEXT.md

Registry audit: skipped — no `components.json` (not a shadcn/web project).
