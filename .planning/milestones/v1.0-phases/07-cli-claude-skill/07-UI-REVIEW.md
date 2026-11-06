# Phase 07 — UI Review

**Audited:** 2026-11-07 (retroactive, milestone v1.0 close)
**Baseline:** Abstract 6-pillar standards (no UI-SPEC.md). Product surface = the two agent-facing skill documents: `.claude/skills/sif-search/SKILL.md` and `.claude/skills/sif-get/SKILL.md` (sif-get audited in its current post-phase-10.1 state, commit 8e0db2a).
**Screenshots:** not captured (no browser surface — docs/CLI-only product)
**Interaction captures:** off (workflow.ui_interaction_capture is false)

Pillars were adapted to the skill-document surface: copywriting = instruction clarity/actionability; visuals = structure/formatting of frontmatter + body; color/typography/spacing = structural emphasis, hierarchy, and rhythm of the Markdown; experience design = agent flow from intent to correct command. Every command, flag, and error-path claim was verified against CLI source (`src/sif/cli/main.py`, `src/sif/cli/commands/search.py`, `src/sif/cli/commands/get.py`).

---

## Pillar Scores

| Pillar | Score | Key Finding |
|--------|-------|-------------|
| 1. Copywriting | 4/4 | Instructions are specific, accurate, and verified against CLI source; examples map natural language to exact commands |
| 2. Visuals | 4/4 | Complete frontmatter (name, description, argument-hint, allowed-tools); consistent objective/process/example structure with fenced command blocks |
| 3. Color | 4/4 | No color surface (Markdown docs); emphasis hierarchy used consistently and sparingly |
| 4. Typography | 4/4 | Consistent heading/bold hierarchy across both skills; no stray formatting |
| 5. Spacing | 4/4 | Uniform structural rhythm: numbered steps, one command variant per block, parallel example sections |
| 6. Experience Design | 3/4 | Intent-to-command flow is solid and error paths are documented, but multi-get's silent 100KB truncation is undocumented and the `-q` claim is inaccurate for get commands |

**Overall: 23/24**

---

## Top 3 Priority Fixes

1. **Undocumented multi-get truncation (`sif-get/SKILL.md`)** — `sif get multi-get` truncates each document at 100,000 bytes (`get.py:129` default `--max-bytes`, truncation at `get.py:196-197` appends `... [truncated]`), and the skill never mentions `--max-bytes` — an agent batch-retrieving large files silently loses content and may answer from partial documents. Add a note in step 2/3 and an example: raise via `-b N` when full content matters.
2. **Inaccurate `-q` claim for get commands (`sif-get/SKILL.md:33`)** — step 2 says `-q` "suppresses non-error output", but `get_cmd`/`multi_get_cmd` never read `ctx.obj["quiet"]`; status lines like `Found N matching document(s)` (`get.py:191`) always print to stdout. Harmless but teaches the agent a false model of the CLI. Either correct the wording or note that get commands always print a status/header block.
3. **Stale pre-rename skill directories in `~/.claude/skills/`** — `docsift-get/` and `docsift-search/` (dated Sep 24) still exist alongside the `sif-get`/`sif-search` symlinks. If they contain old `docsift`-command skills they are dead weight at best and a source of wrong-command invocations at worst. Delete them (outside the repo; user-machine cleanup).

---

## Detailed Findings

### Pillar 1: Copywriting (4/4)
- Both skills state prerequisites ("Requires sif CLI to be installed and available in PATH"), default behavior, and override paths — matching decisions D-01..D-05 in `07-CONTEXT.md`.
- Every error-path claim verified against source: `sif index update` is the correct suggestion (`main.py:117`, `search.py:195`); "No index found." on stdout with exit 0 is accurate (`get.py:44-46`); ClickException to stderr with exit 1 is accurate (`get.py:82`).
- sif-search step 5 even documents the subtle `-q`-silences-missing-index case (empty output vs `[]`) — above-contract attention to a real agent failure mode.
- sif-get objective correctly reflects the phase-10.1 canonicalization and disk-fallback semantics (matches `get_cmd` docstring and implementation, `get.py:38-46, 67-77`).

### Pillar 2: Visuals (4/4)
- Frontmatter complete in both: `name`, `description`, `argument-hint`, `allowed-tools: [Bash]` — matches D-05.
- `<objective>` / `<process>` / `<example>` structure is parallel across both skills; each command variant gets its own labeled fenced block, scannable by an agent.
- No icon-only or ambiguous elements; every example pairs a user utterance with the exact command.

### Pillar 3: Color (4/4)
- Not a color surface (Markdown instruction docs; terminal rendering is the CLI's concern). No colored/emphasis overuse; bold is reserved for step titles and mode names. Structural emphasis follows a consistent single-accent pattern. No findings.

### Pillar 4: Typography (4/4)
- Heading hierarchy consistent: top-level tags, bold step titles, indented sub-bullets. Both skills use identical conventions; no broken nesting or stray markers. No findings.

### Pillar 5: Spacing (4/4)
- Structural rhythm uniform: 5 numbered steps in both process sections, one blank-line-separated fenced block per variant, parallel 3-4 item example sections. No dense walls of text. No findings.

### Pillar 6: Experience Design (3/4)
Verified intent-to-command flows:
- Strategy routing (`--strategy search|vsearch` → correct subcommand) is unambiguous; collection filter and `--all` variants both present and match real flags (`search.py:157-158, 457-458`).
- Flag placement is correct and non-obvious: global `-q` before the subcommand (`main.py:59`) — the skill teaches this correctly, a real trap avoided.
- **WARNING:** multi-get truncation at `--max-bytes` default 100000 (`get.py:129, 196-197`) undocumented — silent content loss for the agent (fix 1).
- **WARNING:** `-q` no-op claim for get commands (`get.py` never consults quiet; status lines always print) — fix 2.
- **INFO:** comma-separated multi-get silently drops not-found items and duplicates (`get.py:175-181`) — the skill doesn't say the output can be shorter than the input list; a one-line note would help the agent notice missing documents.
- **INFO:** stale `docsift-*` skill dirs on the user machine (fix 3) — environment hygiene, not a repo defect.

---

## Registry Safety

Not applicable — no `components.json`, no shadcn, no third-party registries.

---

## Files Audited
- `/Users/forrest/GitHub/SIF/.claude/skills/sif-search/SKILL.md`
- `/Users/forrest/GitHub/SIF/.claude/skills/sif-get/SKILL.md`
- `/Users/forrest/GitHub/SIF/src/sif/cli/main.py` (ground truth: global `-q`, "No index found.")
- `/Users/forrest/GitHub/SIF/src/sif/cli/commands/search.py` (ground truth: query/search/vsearch flags)
- `/Users/forrest/GitHub/SIF/src/sif/cli/commands/get.py` (ground truth: get/multi-get behavior, truncation)
- `/Users/forrest/GitHub/SIF/src/sif/cli/commands/index.py` (ground truth: `index update`)
- `/Users/forrest/GitHub/SIF/.planning/phases/07-cli-claude-skill/07-01-SUMMARY.md`, `07-02-SUMMARY.md`, `07-CONTEXT.md`
- `~/.claude/skills/` directory listing (symlink + stale-dir check)
