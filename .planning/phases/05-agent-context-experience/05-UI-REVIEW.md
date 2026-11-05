# Phase 5 — UI Review (CLI surface) — Re-audit refresh (CR-02)

**Audited:** 2026-11-05 (refresh triggered by commit 0be16d4; supersedes the earlier 2026-11-05 re-audit, overall 11/16 over 4 scored pillars + 2 N/A; original 2026-09-07 audit 10/20)
**Baseline:** Abstract 6-pillar standards (no UI-SPEC.md exists; phase is backend/CLI, not web)
**Screenshots:** Not captured — the only listener on 3000/5173/8080 is SearXNG under OrbStack (port 8080; response headers re-confirmed this run: `server-timing`, `x-robots-tag`, `server: granian`), unrelated to this Python CLI repo. Code-only audit.
**Interaction captures:** off (workflow.ui_interaction_capture is false)

**Scope note:** Phase 05 (plans 05-01..05-09) delivers a Click CLI (`sif context add/list/remove/rm/prune`) and search output (`--json`/`--csv`/`--md`/`--xml`/rich table). The applicable presentation surfaces are `src/sif/cli/commands/context.py` and `src/sif/cli/commands/search.py`. Pillars with no terminal analogue are scored N/A with justification rather than invented.

**Refresh trigger:** code-review fix CR-02 (commit 0be16d4 — md/xml formatters handle dict rows via `_field` accessor) in `src/sif/cli/commands/search.py` + `tests/unit/cli/test_search.py`. Same defect class and audited surface as CR-01 (tracked RESOLVED in the prior review). Prior findings re-checked against the current tree.

---

## Pillar Scores

| Pillar | Score | Key Finding |
|--------|-------|-------------|
| 1. Copywriting | 3/4 | Specific, stateful messages; "No index found." in context.py still lacks the recovery hint search.py has |
| 2. Visuals | 2/4 | `context list` still omits the ID column `context remove` consumes; rich search tables still never show `context_description` |
| 3. Color | 3/4 | Restrained, consistent semantic rich markup (green success / yellow empty-state / red via ClickException / dim meta); no misuse |
| 4. Typography | N/A | Terminal output; rich handles font rendering — no type scale exists to audit |
| 5. Spacing | N/A | Rich-managed table layout; no spacing scale applies |
| 6. Experience Design | 3/4 | CR-02 verified fixed with regression tests (tests pass this run); prune still deletes with zero preview/confirmation; missing-index guard on write commands exits 0 as a silent no-op |

**Overall: 11/16** (4 scored pillars; 2 N/A) — unchanged total; the last machine-consumer formatter defect class (CR-02) is now closed, while the four context.py findings remain open (context.py untouched since the prior review).

---

## Prior-Finding Disposition (this refresh)

| Prior finding (2026-11-05 re-audit) | Status | Evidence |
|---|---|---|
| BLOCKER — `context list` shows no ID column | **STILL OPEN** | context.py:222-232 (verified unchanged this run) — table has Type/Target/Content only; `PathContext.id` exists (core/models.py), so the fix remains trivial |
| WARNING — `context prune` deletes with no preview/confirmation | **STILL OPEN** | context.py:237-254 — still count-only output after the fact; no itemized list, no `--yes`/confirm despite 05-CONTEXT.md specifics suggesting confirmation for counts >10 |
| WARNING — missing-index guard on write commands exits 0 silently | **STILL OPEN** | context.py:117-119 (`add`), 179-181 (`remove`) — yellow print + `return`, exit code 0 |
| Minor — "No index found." without recovery hint in context.py | **STILL OPEN** | context.py:118, 180, 208, 244 — bare "[yellow]No index found.[/yellow]" vs search.py:168/317/479 "Run 'sif index update' first." |
| Minor — rich tables never display `context_description` | **STILL OPEN** | search.py rich-table formatters show Snippet only; only `--json` exposes it via `SearchResult.to_dict()` (core/models.py:236). Note: `--csv` header (search.py:69) and md/xml bodies also omit the field — formatter discretion per 05-CONTEXT.md, so WARNING |

**Fixed since the prior review (verified in current tree):**
- **CR-02 (commit 0be16d4) — RESOLVED.** `format_results_md` and `format_results_xml` now read fields via the shared `_field()` accessor (search.py:56-58; md at :88-95, xml at :107-114), so dict rows from `--line-numbers` no longer crash with AttributeError — the same fix CR-01 applied to `format_results_csv` (search.py:74-78). Regression tests: `test_search_line_numbers_md` (test_search.py:334) and `test_search_line_numbers_xml` (test_search.py:374), both asserting exit 0 plus rendered rank/title/path/collection. Executed this run: `pytest tests/unit/cli/test_search.py -k line_numbers` → **7 passed** (covers CR-01 CSV + CR-02 md/xml).
- Carried from prior review, re-confirmed unchanged: CR-01 (`_field` + `csv.writer` QUOTE_ALL, search.py:70), WR-01 (`vsearch_cmd` clean ClickException, search.py:331-335).

---

## Top 3 Priority Fixes

1. **BLOCKER — `context list` shows no ID column** (context.py:222-232) — `context remove <ID>` (D-05) requires a UUID no CLI output exposes; users must open SQLite directly. Fix: `table.add_column("ID", style="dim")` and add `ctx_item.id` as the first row value (dim style keeps it subordinate to Target/Content).
2. **WARNING — `context prune` deletes with zero preview or confirmation** (context.py:250-254) — prints only a count after the fact; a normalization edge deletes user-authored data invisibly (the CR-02-lineage data-loss bug class shipped on exactly this surface). Fix: list the orphaned targets before deleting (`--dry-run` flag or an itemized line per deleted target), and add `--yes`/confirmation for counts above a threshold per 05-CONTEXT.md specifics.
3. **WARNING — missing-index guard on write commands is a silent no-op with exit code 0** (context.py:117-119, 179-181) — `sif context add ...` on a machine with no index prints a yellow line and exits 0; scripts and agents cannot distinguish "wrote" from "did nothing". Fix: `raise click.ClickException(...)` (exit 1) on the write paths (add/remove), keeping the soft print for read-only list/prune — and append the recovery hint "Run 'sif index update' first." matching search.py:168.

---

## Detailed Findings

### Pillar 1: Copywriting (3/4)
- Good: success/update messages echo the canonical stored target for path type (context.py:158-159, 167-168); errors carry the offending value (`Collection '{target}' not found` context.py:136; `No context found with ID '{context_id}'` context.py:190; `Cannot resolve path '{target}': {e}` context.py:48).
- Minor: "No index found." at context.py:118/180/208/244 gives no recovery action, while search.py:168/317/479 say "Run 'sif index update' first." — inconsistent guidance for the identical state (open since original audit).

### Pillar 2: Visuals (2/4)
- Structure sound: Type/Target/Content table, per-column styles, 50-char "..." truncation (context.py:20, 222-232).
- Defect: no ID column (Priority Fix 1) — the table does not surface the key the sibling remove command consumes. `PathContext.id` is available; nothing blocks the fix.
- Defect: `context_description` is invisible outside `--json` — rich tables (Snippet only) and, per this run's check, the `--csv` header (search.py:69) and md/xml bodies omit it too. Attaching descriptions is the phase's core deliverable; formatter discretion per 05-CONTEXT.md, so WARNING.

### Pillar 3: Color (3/4)
- Consistent semantic scheme: `[green]` success, `[yellow]` empty/warning, `[red]` via ClickException, `[dim]` meta. Column styles (magenta/cyan/green) uniform across context list; `escape()` applied to snippet text in rich search tables. No misuse found.

### Pillar 4: Typography — N/A
Terminal output via rich Console; no font sizes/weights exist to audit. Justified N/A.

### Pillar 5: Spacing — N/A
Rich table layout is renderer-managed; no spacing scale applies. Justified N/A.

### Pillar 6: Experience Design (3/4)
- Fixed since prior review: CR-02 — `--line-numbers --md` / `--line-numbers --xml` now render dict rows via `_field` instead of crashing with AttributeError (search.py:56-58, 88-95, 107-114); regression tests at test_search.py:334/:374, and all 7 line-numbers formatter tests pass this run. With CR-01/CR-02 both closed, every machine-consumer formatter handles both row shapes.
- Present: empty states (no index / no contexts / no results), typed-error paths, `rm` alias (context.py:258), dual validation (click.Choice context.py:103 + DB CHECK), destructive-action guard rails in the write path (missing-index guard, WR-03), tz-safe self-heal merge (context.py:23-34).
- Defective: prune without preview/confirmation (Priority Fix 2); write-command no-op exits 0 (Priority Fix 3).
- Minor: no `--json` for `context list` (explicitly deferred as nice-to-have — acceptable); no progress indication for prune (single query — acceptable).

---

## Registry Safety

Not applicable — no `components.json`, no shadcn, no third-party UI registries (Python CLI project). Verified: NO_SHADCN.

## Files Audited
- src/sif/cli/commands/context.py (full read, current tree — unchanged since prior review; all four open findings re-verified at identical line numbers)
- src/sif/cli/commands/search.py (fix sites + formatters read this run — CR-02 `_field` accessor verified at :56-58, md :88-95, xml :107-114; CR-01 csv :70-78; WR-01 :331-335; no-index copy :168/317/479)
- src/sif/core/models.py (SearchResult.context_description :221, to_dict :236)
- tests/unit/cli/test_search.py (CR-02 regressions :334/:374 read; `-k line_numbers` suite executed — 7 passed)
- .planning/phases/05-agent-context-experience/: 05-01..05-09 SUMMARY (read/skimmed), 05-01/05-05/05-09 PLAN (skimmed), 05-CONTEXT.md (read), prior 05-UI-REVIEW.md (read)
