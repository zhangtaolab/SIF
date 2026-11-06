# Phase 5 — UI Review (CLI surface) — Re-audit after plans 05-10/05-11/05-12

**Audited:** 2026-11-06 (supersedes the 2026-11-05 CR-02 refresh, overall 11/16 over 4 scored pillars + 2 N/A; original 2026-09-07 audit 10/20)
**Baseline:** Abstract 6-pillar standards (no UI-SPEC.md exists; phase is backend/CLI, not web)
**Screenshots:** Not captured — the only listener on 3000/5173/8080 is SearXNG under OrbStack (port 8080; headers re-confirmed this run: `server: granian`, `x-robots-tag`), unrelated to this Python CLI repo. Code-only audit.
**Interaction captures:** off (workflow.ui_interaction_capture is false)

**Scope note:** Phase 05 (now plans 05-01..05-12) delivers a Click CLI (`sif context add/list/remove/rm/prune`) and search output (`--json`/`--csv`/`--md`/`--xml`/rich table). Audited surfaces: `src/sif/cli/commands/context.py` and `src/sif/cli/commands/search.py`. Pillars with no terminal analogue are scored N/A with justification.

**Refresh trigger:** the phase's final three plans — 05-10 (`_collapse_duplicate_path_rows` + `escape()` on all three `context list` cells), 05-11 (12 escape sites across the three search tables, line-numbers cells, and both explain prints), 05-12 (escape at the three context add/remove confirmation prints, closing CR-03's write-rollback defect), plus commit 452ae48 (WR-18 confirmation print moved outside the transaction). All prior findings re-verified against the current tree.

---

## Pillar Scores

| Pillar | Score | Key Finding |
|--------|-------|-------------|
| 1. Copywriting | 3/4 | Specific, stateful messages; "No index found." in context.py still lacks the recovery hint search.py has |
| 2. Visuals | 2/4 | `context list` still omits the ID column `context remove` consumes; rich search tables still never show `context_description` |
| 3. Color | 3/4 | Restrained, consistent semantic rich markup (green success / yellow empty-state / red via ClickException / dim meta); no misuse |
| 4. Typography | N/A | Terminal output; rich handles font rendering — no type scale exists to audit |
| 5. Spacing | N/A | Rich-managed table layout; no spacing scale applies |
| 6. Experience Design | 3/4 | CR-03 fixed and regression-locked (121 CLI tests pass this run); markup-literal rendering now holds at every display site; prune still deletes with zero preview/confirmation; missing-index guard on write commands still exits 0 as a silent no-op |

**Overall: 11/16** (4 scored pillars; 2 N/A) — same total, but the open-defect count dropped from five to four context.py findings and the crash-class display defects (CR-01b/CR-02b/CR-03) are all closed with RED-first regression tests.

---

## Prior-Finding Disposition (this refresh)

| Prior finding (2026-11-05 CR-02 refresh) | Status | Evidence |
|---|---|---|
| BLOCKER — `context list` shows no ID column | **STILL OPEN** | context.py:270-289 — table has Type/Target/Content only; `PathContext.id` exists (core/models.py), fix remains `table.add_column("ID", style="dim")` + `ctx_item.id` first row value |
| WARNING — `context prune` deletes with no preview/confirmation | **STILL OPEN** | context.py:294-311 — still count-only output after the fact; no itemized list, no `--yes`/confirm despite 05-CONTEXT.md specifics suggesting confirmation for counts >10 |
| WARNING — missing-index guard on write commands exits 0 silently | **STILL OPEN** | context.py:153-155 (`add`), 227-229 (`remove`) — yellow print + `return`, exit code 0 |
| Minor — "No index found." without recovery hint in context.py | **STILL OPEN** | context.py:154, 228, 256, 301 — bare "[yellow]No index found.[/yellow]" vs search.py:195/348/514 "Run 'sif index update' first." |
| Minor — rich tables never display `context_description` | **STILL OPEN** | search.py:275-301, 425-449, 654-680 — table columns are #/Score/Title/Collection/Snippet-or-Content only; only `--json` exposes it. Formatter discretion per 05-CONTEXT.md, so WARNING |

**Fixed since the prior review (verified in current tree + executed this run):**
- **CR-03 (05-12, commits 01c2a95/d347974) — RESOLVED.** The confirmation `console.print` inside the open transaction no longer raises `MarkupError` on bracket-named targets (which previously rolled back the write): `escape(display_target)` on both add branches (context.py:216) and `escape(context_id)` on remove (context.py:240). This was a data-loss-class defect — `context add path '<file> [WIP].md' 'text'` persisted zero rows — now locked by `TestContextConfirmationMarkupLiteral` (3 tests, real SQL).
- **CR-02b context-list escaping (05-10, commit ba7e0e4) — RESOLVED.** All three `context list` cells wrapped, escape AFTER truncation so the 50-char cap applies to raw text (context.py:282-289); regression test `test_list_renders_markup_bearing_cells_literally`.
- **CR-01b search-table escaping (05-11, commit 63bca7e) — RESOLVED.** 12 escape sites: 3 Table titles (search.py:275, 425, 654), 3 truncated-title cells (:288, :437, :667), 3 collection cells (:293, :442, :672), 3 line-numbers content appends (:300, :448, :679), plus both explain prints (:306, :690). Five `*markup_literal` regression tests.
- **WR-18 (commit 452ae48) — RESOLVED.** `context add` confirmation print moved outside the transaction (context.py:212-216); a display failure can no longer roll back a committed write.
- **Truth 21 (05-10) — RESOLVED.** Shared `_collapse_duplicate_path_rows` helper (context.py:38-62) funnels every re-add path; re-adding a path under any legacy alias spelling ends with exactly one canonical row (2 real-SQL regression tests).
- Carried from prior review, re-confirmed fixed: CR-01a `_field` csv accessor, CR-02a `_field` md/xml, WR-01 `vsearch_cmd` clean ClickException.

**Verification executed this run:** `env -u FORCE_COLOR NO_COLOR=1 pytest --no-cov tests/unit/cli/test_context.py tests/unit/cli/test_search.py` → **121 passed** (31 context + 90 search, including all 8 markup-literal regressions).

---

## Top 3 Priority Fixes

1. **BLOCKER — `context list` shows no ID column** (context.py:270-289) — `context remove <ID>` (D-05) requires a UUID no CLI output exposes; users must open SQLite directly. Fix: `table.add_column("ID", style="dim")` and add `escape(ctx_item.id)` as the first row value.
2. **WARNING — `context prune` deletes with zero preview or confirmation** (context.py:307-311) — prints only a count after the fact; orphan classification deletes user-authored data invisibly. Fix: list the orphaned targets before deleting (`--dry-run` or itemized lines), and add `--yes`/confirmation above a threshold per 05-CONTEXT.md.
3. **WARNING — missing-index guard on write commands is a silent no-op with exit code 0** (context.py:153-155, 227-229) — scripts and agents cannot distinguish "wrote" from "did nothing". Fix: `raise click.ClickException(...)` (exit 1) on add/remove, soft print for read-only list/prune, and append "Run 'sif index update' first." matching search.py:195 (also closes the Copywriting inconsistency).

---

## Detailed Findings

### Pillar 1: Copywriting (3/4)
- Good: confirmations echo the canonical stored target for path type (context.py:216, now markup-safe); errors carry the offending value (`Collection '{target}' not found` :172; `No context found with ID '{context_id}'` :238; `Cannot resolve path '{target}': {e}` :76).
- Minor: "No index found." at context.py:154/228/256/301 gives no recovery action, while search.py:195/348/514 say "Run 'sif index update' first." — inconsistent guidance for the identical state (open since the original audit).

### Pillar 2: Visuals (2/4)
- Structure sound: Type/Target/Content table, per-column styles, 50-char "..." truncation, escape-after-truncation display contract (:21, :270-289).
- Defect: no ID column (Priority Fix 1) — the table does not surface the key the sibling remove command consumes. Nothing blocks the fix.
- Defect: `context_description` — the phase's core deliverable — is invisible outside `--json` (rich tables show Snippet/Content only; `--csv` header and md/xml bodies omit it too). Formatter discretion per 05-CONTEXT.md, so WARNING.

### Pillar 3: Color (3/4)
- Consistent semantic scheme: `[green]` success, `[yellow]` empty/warning, `[red]` via ClickException, `[dim]` meta. Column styles (magenta/cyan/green) uniform across context list; search tables uniform (cyan/green/yellow/blue/white) across all three commands. `escape()` applied at every user-data interpolation site (context list cells, add/remove confirmations, all three search tables, both explain prints) — no markup-injection or crash surface remains. No misuse found.

### Pillar 4: Typography — N/A
Terminal output via rich Console; no font sizes/weights exist to audit. Justified N/A.

### Pillar 5: Spacing — N/A
Rich table layout is renderer-managed; no spacing scale applies. Justified N/A.

### Pillar 6: Experience Design (3/4)
- Fixed since prior review: CR-03 — bracket-named targets no longer crash the confirmation print inside the transaction, so both write branches persist (05-12, real-SQL regression tests); CR-01b/CR-02b — every Rich display site renders markup-bearing user data literally (12 search sites + 3 context-list cells + 3 confirmation prints); WR-18 — confirmation print outside the transaction; truth-21 — multi-alias re-add always ends with exactly one canonical row.
- Present: empty states (no index / no contexts / no results), typed-error paths, `rm` alias (:315), dual validation (click.Choice :139 + DB CHECK), destructive-action guard rails in the write path (missing-index guard WR-03), tz-safe self-heal merge (:24-35), landed-guard before every destructive collapse (:108-113, :126-128).
- Defective: prune without preview/confirmation (Priority Fix 2); write-command no-op exits 0 (Priority Fix 3).
- Minor: no `--json` for `context list` (explicitly deferred — acceptable); no progress indication for prune (single query — acceptable).

---

## Registry Safety

Not applicable — no `components.json`, no shadcn, no third-party UI registries (Python CLI project). Verified: NO_SHADCN.

## Files Audited
- src/sif/cli/commands/context.py (full read, current tree — 05-10/05-12 changes verified: `_collapse_duplicate_path_rows` :38-62, list-cell escapes :282-289, confirmation escapes :216/:240, WR-18 print placement :212-216)
- src/sif/cli/commands/search.py (grep-verified escape sites :275-306, :425-448, :654-690; `_field` accessor :72+; no-index copy :195/:348/:514)
- tests/unit/cli/test_context.py + tests/unit/cli/test_search.py (executed this run — 121 passed)
- .planning/phases/05-agent-context-experience/: 05-10/05-11/05-12 SUMMARY (full read), prior 05-UI-REVIEW.md (full read), 05-CONTEXT.md (carried from prior review)
