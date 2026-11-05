# Phase 5 — UI Review (CLI surface) — Re-audit refresh

**Audited:** 2026-11-05 (refresh of the 2026-11-05 re-audit, overall 11/16 over 4 scored pillars + 2 N/A; original 2026-09-07 audit 10/20)
**Baseline:** Abstract 6-pillar standards (no UI-SPEC.md exists; phase is backend/CLI, not web)
**Screenshots:** Not captured — the only listener on 3000/5173/8080 is SearXNG under OrbStack (port 8080; SearXNG response headers confirmed: `server-timing`, `x-robots-tag`), unrelated to this Python CLI repo. Code-only audit.
**Interaction captures:** off (workflow.ui_interaction_capture is false)

**Scope note:** Phase 05 (plans 05-01..05-09) delivers a Click CLI (`sif context add/list/remove/rm/prune`) and search output (`--json`/`--csv`/rich table). The applicable presentation surfaces are `src/sif/cli/commands/context.py` and `src/sif/cli/commands/search.py`. Pillars with no terminal analogue are scored N/A with justification rather than invented.

**Refresh trigger:** code-review fixes CR-01 (commit e78fa96 — `format_results_csv` dict-or-object access + `csv.writer` escaping) and WR-01 (commit 7170c08 — `vsearch_cmd` guards `get_settings()` failure with a clean `ClickException`). Both touch search.py, one of the two audited surfaces. Prior findings re-checked against the current tree.

---

## Pillar Scores

| Pillar | Score | Key Finding |
|--------|-------|-------------|
| 1. Copywriting | 3/4 | Specific, stateful messages; WR-01 adds a clean one-line error for invalid config on `vsearch`; "No index found." in context.py still lacks the recovery hint search.py has |
| 2. Visuals | 2/4 | `context list` still omits the ID column `context remove` consumes; rich search tables still never show `context_description` |
| 3. Color | 3/4 | Restrained, consistent semantic rich markup (green success / yellow empty-state / red via ClickException / dim meta); no misuse |
| 4. Typography | N/A | Terminal output; rich handles font rendering — no type scale exists to audit |
| 5. Spacing | N/A | Rich-managed table layout; no spacing scale applies |
| 6. Experience Design | 3/4 | CR-01 and WR-01 both verified fixed with regression tests; prune still deletes with zero preview/confirmation; missing-index guard on write commands exits 0 as a silent no-op |

**Overall: 11/16** (4 scored pillars; 2 N/A) — unchanged total; one machine-consumer defect class (CSV correctness) closed since the prior review, while the four context.py findings remain open.

---

## Prior-Finding Disposition (this refresh)

| Prior finding (2026-11-05 re-audit) | Status | Evidence |
|---|---|---|
| BLOCKER — `context list` shows no ID column | **STILL OPEN** | context.py:222-232 — table has Type/Target/Content only; `PathContext.id` exists (core/models.py), so the fix remains trivial |
| WARNING — `context prune` deletes with no preview/confirmation | **STILL OPEN** | context.py:237-254 — still count-only output after the fact; no itemized list, no `--yes`/confirm despite 05-CONTEXT.md specifics suggesting confirmation for counts >10 |
| WARNING — missing-index guard on write commands exits 0 silently | **STILL OPEN** | context.py:117-119 (`add`), 179-181 (`remove`) — yellow print + `return`, exit code 0 |
| Minor — "No index found." without recovery hint in context.py | **STILL OPEN** | context.py:118, 180, 208, 244 — bare "[yellow]No index found.[/yellow]" vs search.py:167 "Run 'sif index update' first." |
| Minor — rich tables never display `context_description` | **STILL OPEN** | search.py:247-271, 393-415, 618-642 — Snippet column only; the phase's core deliverable is invisible outside `--json` |

**Fixed since the prior review (verified in current tree):**
- **CR-01 (commit e78fa96) — RESOLVED.** `format_results_csv` now reads fields via `_csv_field()` (dict rows from `--line-numbers` or object rows, search.py:56-58) and writes through `csv.writer(..., quoting=csv.QUOTE_ALL, lineterminator="\n")` (search.py:70) — embedded quotes/commas no longer break the CSV, and `--line-numbers --csv` no longer crashes. Regression tests: `test_search_line_numbers_csv` (test_search.py:291) and `test_search_csv_rows_single_line` (test_search.py:1185).
- **WR-01 (commit 7170c08) — RESOLVED.** `vsearch_cmd` wraps `get_settings()` in try/except `ValidationError` → `click.ClickException` (search.py:331-335), matching `query_cmd`'s guard. Regression test: `test_vsearch_env_invalid_reranker_type_clean_error` (test_search.py:970) asserts exit 1, "Error:" present, "Traceback" absent.

---

## Top 3 Priority Fixes

1. **BLOCKER — `context list` shows no ID column** (context.py:222-232) — `context remove <ID>` (D-05) requires a UUID no CLI output exposes; users must open SQLite directly. Fix: `table.add_column("ID", style="dim")` and add `ctx_item.id` as the first row value (dim style keeps it subordinate to Target/Content).
2. **WARNING — `context prune` deletes with zero preview or confirmation** (context.py:250-254) — prints only a count after the fact; a normalization edge deletes user-authored data invisibly (this exact surface shipped the CR-02 data-loss bug, fixed one plan later). Fix: list the orphaned targets before deleting (`--dry-run` flag or an itemized line per deleted target), and add `--yes`/confirmation for counts above a threshold per 05-CONTEXT.md specifics.
3. **WARNING — missing-index guard on write commands is a silent no-op with exit code 0** (context.py:117-119, 179-181) — `sif context add ...` on a machine with no index prints a yellow line and exits 0; scripts and agents cannot distinguish "wrote" from "did nothing". Fix: `raise click.ClickException(...)` (exit 1) on the write paths (add/remove), keeping the soft print for read-only list/prune — and append the recovery hint "Run 'sif index update' first." matching search.py:167.

---

## Detailed Findings

### Pillar 1: Copywriting (3/4)
- Good: success/update messages echo the canonical stored target for path type (context.py:158-159, 167-168); errors carry the offending value (`Collection '{target}' not found` context.py:136; `No context found with ID '{context_id}'` context.py:190; `Cannot resolve path '{target}': {e}` context.py:48).
- Good (WR-01, new): invalid env config on `vsearch` now surfaces as a readable one-line `Error:` with the offending field name instead of a pydantic traceback (search.py:334-335; test_search.py:970-994).
- Minor: "No index found." at context.py:118/180/208/244 gives no recovery action, while search.py:167/316/478 say "Run 'sif index update' first." — inconsistent guidance for the identical state (open since original audit).

### Pillar 2: Visuals (2/4)
- Structure sound: Type/Target/Content table, per-column styles, 50-char "..." truncation (context.py:20, 222-232).
- Defect: no ID column (Priority Fix 1) — the table does not surface the key the sibling remove command consumes. `PathContext.id` is available; nothing blocks the fix.
- Defect: rich search tables never display `context_description` (search.py:247-271, 393-415, 618-642) even though attaching it is the phase's core deliverable; only `--json` exposes it. Formatter discretion per 05-CONTEXT.md, so WARNING.

### Pillar 3: Color (3/4)
- Consistent semantic scheme: `[green]` success, `[yellow]` empty/warning, `[red]` via ClickException, `[dim]` meta. Column styles (magenta/cyan/green; cyan/green/yellow/blue/white) uniform across context list and all three search tables. `escape()` applied to snippet text in rich tables (search.py:262, 633). No misuse found.

### Pillar 4: Typography — N/A
Terminal output via rich Console; no font sizes/weights exist to audit. Justified N/A.

### Pillar 5: Spacing — N/A
Rich table layout is renderer-managed; no spacing scale applies. Justified N/A.

### Pillar 6: Experience Design (3/4)
- Fixed since prior review: CR-01 — `--csv` output is now correctly escaped (`csv.writer`, QUOTE_ALL) and `--line-numbers --csv` works (dict-row access), removing the remaining machine-consumer defect class alongside the earlier strict-JSON fix (regression tests at test_search.py:291, 1185).
- Fixed since prior review: WR-01 — `vsearch` with an explicit `--index` and invalid settings renders a clean ClickException rather than a traceback (search.py:331-335, test at :970).
- Present: empty states (no index / no contexts / no results), typed-error paths, `rm` alias (context.py:258), dual validation (click.Choice context.py:103 + DB CHECK), destructive-action guard rails in the write path (missing-index guard, WR-03).
- Defective: prune without preview/confirmation (Priority Fix 2); write-command no-op exits 0 (Priority Fix 3).
- Minor: no `--json` for `context list` (explicitly deferred as nice-to-have — acceptable); no progress indication for prune (single query — acceptable).

---

## Registry Safety

Not applicable — no `components.json`, no shadcn, no third-party UI registries (Python CLI project). Verified: NO_SHADCN.

## Files Audited
- src/sif/cli/commands/context.py (full read, current tree — unchanged since prior review)
- src/sif/cli/commands/search.py (full read, current tree — CR-01 and WR-01 fix sites verified)
- src/sif/core/models.py (PathContext fields, grep-level)
- .planning/phases/05-agent-context-experience/: 05-CONTEXT.md, 05-01/05-05/05-09 SUMMARY (skimmed; 02-04, 06-08 via prior review), 05-REVIEW-FIX.md lineage (commits e78fa96, 7170c08), prior 05-UI-REVIEW.md
- tests/unit/cli/test_search.py (CR-01 regression :291/:1185, WR-01 regression :970, verified)
