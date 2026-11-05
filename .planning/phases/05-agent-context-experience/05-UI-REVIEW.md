# Phase 5 — UI Review (CLI surface) — Re-audit

**Audited:** 2026-11-05 (re-audit of 2026-09-07 review, overall 10/20)
**Baseline:** Abstract 6-pillar standards (no UI-SPEC.md exists; phase is backend/CLI, not web)
**Screenshots:** Not captured — the only listener on 3000/5173/8080 is SearXNG under OrbStack (port 8080), unrelated to this repo. Code-only audit.
**Interaction captures:** off (workflow.ui_interaction_capture is false)

**Scope note:** Phase 05 (plans 05-01..05-09) delivers a Click CLI (`sif context add/list/remove/rm/prune`) and search output (`--json`/rich table). The applicable presentation surfaces are `src/sif/cli/commands/context.py` and `src/sif/cli/commands/search.py`. Pillars with no terminal analogue are scored N/A with justification rather than invented.

**Re-audit trigger:** quick-task 261105-g1u (commits 25481d8, b8a81e1) — WR-03 missing-index guards in context.py, WR-09 reranker_model_type validation in main.py. Prior top findings re-checked against current tree.

---

## Pillar Scores

| Pillar | Score | Key Finding |
|--------|-------|-------------|
| 1. Copywriting | 3/4 | Specific, stateful messages (canonical path echoed, clean ClickExceptions for bad targets); "No index found." in context.py still lacks the recovery hint search.py has |
| 2. Visuals | 2/4 | `context list` still omits the ID column `context remove` consumes; rich search tables still never show `context_description` |
| 3. Color | 3/4 | Restrained, consistent semantic rich markup (green success / yellow empty-state / red via ClickException / dim meta); no misuse |
| 4. Typography | N/A | Terminal output; rich handles font rendering — no type scale exists to audit |
| 5. Spacing | N/A | Rich-managed table layout; no spacing scale applies |
| 6. Experience Design | 3/4 (up from 2) | Strict-JSON defect FIXED with regression tests; prune still deletes with zero preview/confirmation; missing-index guard on write commands exits 0 as a silent no-op |

**Overall: 11/16** (4 scored pillars; 2 N/A)

---

## Prior-Finding Disposition (re-audit)

| Prior finding (2026-09-07) | Status | Evidence |
|---|---|---|
| BLOCKER — `context list` shows no ID column | **STILL OPEN** | context.py:222-232 — table has Type/Target/Content only; `PathContext.id` exists (core/models.py:188), so the fix remains trivial |
| BLOCKER — `search --json` not strict-JSON parseable | **RESOLVED** | Root cause was rich `console.print` wrapping JSON at terminal width; quick task 260910-kps switched all machine-format branches to `click.echo` (search.py:186, 351, 549; bench too), with COLUMNS=80 strict-parse regression tests (tests/unit/cli/test_search.py:967-1145, test_bench.py:140). deferred-items.md entry marked resolved 2026-09-10 |
| WARNING — `context prune` deletes with no preview/confirmation | **STILL OPEN** | context.py:237-254 — still count-only output after the fact; no itemized list, no `--yes`/confirm despite 05-CONTEXT.md specifics suggesting confirmation for counts >10 |
| Minor — "No index found." without recovery hint in context.py | **STILL OPEN** | context.py:118, 180, 208, 244 — bare "[yellow]No index found.[/yellow]" vs search.py:146 "Run 'sif index update' first." |
| Minor — rich tables never display `context_description` | **STILL OPEN** | search.py:226-250, 589-611 — Snippet column only; the phase's core deliverable is invisible outside `--json` |

**New since quick-task 261105-g1u (verified positive):**
- WR-03: `context add`/`remove` now guard a missing index instead of silently materializing an empty DB (context.py:117-119, 179-181). Error copy on that path: "[yellow]No index found.[/yellow]" — clean, consistent with list/prune, but see Pillar 6 finding on exit code.
- WR-09: invalid `reranker_model_type` surfaces as a clean ClickException, not a traceback — settings validator (config/settings.py:166-179), `get_settings()` ValidationError → ClickException (search.py:493-496), factory ValueError → ClickException (search.py:521-524).
- WR-01/WR-02 (earlier fix commits, present in tree): un-expandable `~user` path targets raise `Cannot resolve path '<target>': ...` (context.py:37-49); self-heal merge collapses legacy alias rows (context.py:52-93).

---

## Top 3 Priority Fixes

1. **BLOCKER — `context list` shows no ID column** (context.py:222-232) — `context remove <ID>` (D-05) requires a UUID no CLI output exposes; users must open SQLite directly. Fix: `table.add_column("ID", style="dim")` and add `ctx_item.id` as the first row value (dim style keeps it subordinate to Target/Content).
2. **WARNING — `context prune` deletes with zero preview or confirmation** (context.py:250-254) — prints only a count after the fact; a normalization edge deletes user-authored data invisibly (this exact surface shipped the CR-02 data-loss bug, fixed only one plan later). Fix: list the orphaned targets before deleting (`--dry-run` flag or an itemized line per deleted target), and add `--yes`/confirmation for counts above a threshold per 05-CONTEXT.md specifics.
3. **WARNING — missing-index guard on write commands is a silent no-op with exit code 0** (context.py:117-119, 179-181) — `sif context add ...` on a machine with no index prints a yellow line and exits 0; scripts and agents cannot distinguish "wrote" from "did nothing". Fix: `raise click.ClickException(...)` (exit 1) or `ctx.exit(1)` on the write paths (add/remove), keeping the soft print for read-only list/prune — and append the recovery hint "Run 'sif index update' first." matching search.py:146.

---

## Detailed Findings

### Pillar 1: Copywriting (3/4)
- Good: success/update messages echo the canonical stored target for path type (context.py:158-159, 167-168) — users see the spelling that will actually match; errors carry the offending value (`Collection '{target}' not found` context.py:136; `No context found with ID '{context_id}'` context.py:190; `Cannot resolve path '{target}': {e}` context.py:48).
- Good: WR-09 invalid reranker config surfaces as a readable one-line ClickException, not a traceback (search.py:495, 524).
- Minor: "No index found." at context.py:118/180/208/244 gives no recovery action, while search.py:146/295/449 say "Run 'sif index update' first." — inconsistent guidance for the identical state (open since prior audit).

### Pillar 2: Visuals (2/4)
- Structure sound: Type/Target/Content table, per-column styles, 50-char "..." truncation (context.py:20, 222-232).
- Defect: no ID column (Priority Fix 1) — the table does not surface the key the sibling remove command consumes. `PathContext.id` is available (core/models.py:188); nothing blocks the fix.
- Defect: rich search tables never display `context_description` (search.py:226-250, 364-386, 589-611) even though attaching it is the phase's core deliverable; only `--json` exposes it. Formatter discretion per 05-CONTEXT.md, so WARNING.

### Pillar 3: Color (3/4)
- Consistent semantic scheme: `[green]` success, `[yellow]` empty/warning, `[red]` via ClickException, `[dim]` meta. Column styles (magenta/cyan/green; cyan/green/yellow/blue/white) uniform across context list and all three search tables. `escape()` applied to snippet text in rich tables (search.py:241, 604). No misuse found.

### Pillar 4: Typography — N/A
Terminal output via rich Console; no font sizes/weights exist to audit. Justified N/A.

### Pillar 5: Spacing — N/A
Rich table layout is renderer-managed; no spacing scale applies. Justified N/A.

### Pillar 6: Experience Design (3/4, up from 2)
- Fixed since prior audit: `--json`/`--csv`/`--md`/`--xml`/`--files` machine output now strict-parseable at any terminal width (click.echo; COLUMNS=80 regression tests in tests/unit/cli/test_search.py:967+). This was the prior audit's agent-consumer blocker.
- Present: empty states (no index / no contexts / no results), typed-error paths, `rm` alias (context.py:258), dual validation (click.Choice context.py:103 + DB CHECK), destructive-action guard rails in the write path (missing-index guard, WR-03).
- Defective: prune without preview/confirmation (Priority Fix 2); write-command no-op exits 0 (Priority Fix 3).
- Minor: no `--json` for `context list` (explicitly deferred as nice-to-have — acceptable); no progress indication for prune (single query — acceptable).

---

## Registry Safety

Not applicable — no `components.json`, no shadcn, no third-party UI registries (Python CLI project). Verified: NO_SHADCN.

## Files Audited
- src/sif/cli/commands/context.py (full read, current tree)
- src/sif/cli/commands/search.py (full read, current tree)
- src/sif/core/models.py (PathContext fields)
- src/sif/config/settings.py (reranker_model_type validator)
- .planning/phases/05-agent-context-experience/: 05-CONTEXT.md, 05-01..05-09 PLAN/SUMMARY, deferred-items.md, prior 05-UI-REVIEW.md
- tests/unit/cli/test_search.py, test_bench.py (strict-JSON regression coverage, grep-level)
