# Phase 5 — UI Review (CLI surface)

**Audited:** 2026-09-07
**Baseline:** Abstract 6-pillar standards (no UI-SPEC.md exists; phase is backend/CLI, not web)
**Screenshots:** Not captured — no dev server (CLI-only project; nothing to screenshot at localhost:3000)

**Scope note:** Phase 05 (plans 05-08, 05-09) delivers a Click CLI (`sif context add/list/rm/prune`) and search output (`--json`/rich table). The applicable presentation surfaces are `src/sif/cli/commands/context.py` and `src/sif/cli/commands/search.py`. Pillars with no terminal analogue are scored N/A with justification rather than invented.

---

## Pillar Scores

| Pillar | Score | Key Finding |
|--------|-------|-------------|
| 1. Copywriting | 3/4 | Specific, stateful messages (canonical path echoed); "No index found." in context.py lacks the recovery hint search.py has |
| 2. Visuals | 2/4 | `context list` table omits the ID column required by `context remove` — the remove workflow is not completable from listed output |
| 3. Color | 3/4 | Restrained rich markup (green success / yellow empty-state / per-column styles); consistent across commands |
| 4. Typography | N/A | Terminal output; rich handles font rendering — no type scale exists to audit |
| 5. Spacing | N/A | Terminal tables; no spacing scale applies |
| 6. Experience Design | 2/4 | `search --json` emits invalid strict JSON (raw newlines in snippet, open deferred item); `context prune` is destructive with no confirmation and no itemized output |

**Overall: 10/20** (4 scored pillars; 2 N/A)

---

## Top 3 Priority Fixes

1. **BLOCKER — `context list` shows no ID column** (context.py:137-139) — `context remove <ID>` (D-05) requires a UUID the user cannot obtain from any CLI output; they must open SQLite directly. Fix: `table.add_column("ID", style="dim")` and add `ctx_item.id` as the first row value (truncate/dim for width).
2. **BLOCKER — `search --json` output is not strict-JSON parseable** (search.py:44-50; deferred-items.md open item) — literal control characters (newlines) inside the `snippet` field make `json.loads` fail without `strict=False`; agent consumers — the phase's stated audience — cannot machine-read the output this phase exists to serve. Fix: strip/escape control characters in `_display_snippet`/`to_dict` serialization, or `json.dumps(..., default=...)` sanitization of snippet strings.
3. **WARNING — `context prune` deletes with zero preview or confirmation** (context.py:151-168) — prints only a count after the fact; a mis-normalized edge deletes user-authored data invisibly (this exact surface shipped the CR-02 data-loss bug). Fix: list the orphaned targets before deletion, or add `--yes` per 05-CONTEXT.md specifics ("confirm before deleting if the count is high (>10)").

---

## Detailed Findings

### Pillar 1: Copywriting (3/4)
- Good: success/update messages echo the *canonical* stored target for path type (context.py:78-79, 87-88) — users see the form that will actually match; errors carry the offending value (`Collection '{target}' not found`, `No context found with ID '{context_id}'`).
- Good: empty states exist and are specific ("No contexts found.", "No index found.").
- Minor: context.py:122/157 "No index found." gives no recovery action, while search.py:145 says "Run 'sif update' first." — inconsistent guidance for the identical state.

### Pillar 2: Visuals (2/4)
- Structure is sound: Type/Target/Content table, color-differentiated columns, "…" truncation at 50 chars (context.py:17-18, 144-145).
- Defect: no ID column (see Priority Fix 1) — the table does not surface the key the sibling command consumes.
- Defect: search rich table never displays `context_description` (search.py:225-249) even though attaching it to results is the phase's core deliverable; only `--json` exposes it. 05-CONTEXT.md specifics left this "at formatter discretion," so WARNING, not blocker.

### Pillar 3: Color (3/4)
- Consistent semantic scheme: `[green]` success, `[yellow]` empty/warning states, `[red]` via ClickException, dim (`[dim]`) for meta lines. Column styles (magenta/cyan/green) match across `context list` and search tables. No misuse.

### Pillar 4: Typography — N/A
Terminal output via rich Console; no font sizes/weights exist to audit. Justified N/A.

### Pillar 5: Spacing — N/A
Rich table layout is renderer-managed; no spacing scale applies. Justified N/A.

### Pillar 6: Experience Design (2/4)
- Present: empty states (no index / no contexts / no results), typed-error paths via `click.ClickException`, `rm` alias, `--json` machine output, dual validation (click.Choice + CHECK).
- Missing/defective: invalid strict JSON (Priority Fix 2); destructive prune without preview/confirmation (Priority Fix 3); no `--json`/`--format` for `context list` (deferred as nice-to-have, acceptable); no loading/progress indication for prune over large tables (minor — single query).

---

## Registry Safety

Not applicable — no `components.json`, no shadcn, no third-party UI registries (Python CLI project).

## Files Audited
- src/sif/cli/commands/context.py
- src/sif/cli/commands/search.py (output surface consumed by phase)
- src/sif/core/models.py (SearchResult.context_description, to_dict)
- .planning/phases/05-agent-context-experience/{05-08-PLAN,05-09-PLAN,05-08-SUMMARY,05-09-SUMMARY,05-CONTEXT}.md, deferred-items.md
