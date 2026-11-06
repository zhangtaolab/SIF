# Phase 06 — UI Review (Docs-as-Surface Audit)

**Audited:** 2026-11-06 (milestone v1.0 close, retroactive)
**Baseline:** Abstract 6-pillar standards — phase's user-facing surface is README.md + docs/ tree (15 files, 6,936 lines), no UI-SPEC.md exists
**Screenshots:** not captured (CLI/docs project — no web server; the only listening port, 8080, is an unrelated SearXNG instance via OrbStack)
**Interaction captures:** off (workflow.ui_interaction_capture is false)

---

## Pillar Scores

| Pillar | Score | Key Finding |
|--------|-------|-------------|
| 1. Copywriting | 3/4 | Copy accuracy is excellent (validator 13/13, live CLI spot-checks pass, zero phantom flags/commands found); README Roadmap diverges from architecture.md Future Enhancements and models.md lists the non-selectable `HUGGINGFACE` enum member uncaveated |
| 2. Visuals | 3/4 | Clean structure: exactly one H1 per file, zero heading-level skips, 431 table rows, ASCII arch diagram (README) + derived Mermaid (architecture.md), mkdocs-material nav cards in index.md; trailing whitespace in 3 files |
| 3. Color (emphasis) | 3/4 | Emphasis used sparingly and consistently (bold for key terms, single `> **Note:**` blockquote convention); no over-emphasis found; minor mechanical typos dilute polish (double space quickstart.md:22) |
| 4. Typography (hierarchy/format) | 3/4 | Heading hierarchy uniformly clean across all 16 files; 372 untagged code fences are all output/display blocks by design (D-03) but render without highlighting on GitHub |
| 5. Spacing (whitespace consistency) | 3/4 | No tabs, no unbalanced fences, consistent blank-line structure; 28 trailing-whitespace lines across api-reference.md (13), development.md (10), contributing.md (5) |
| 6. Experience Design (navigation/flow) | 3/4 | Getting-started flow is strong (quickstart → install → first collection → search, all commands live-verified, blocking CI drift gate); migration.md has zero inbound links anywhere — an undiscoverable doc; README docs list omits 5 of 15 docs |

**Overall: 18/24**

---

## Top 3 Priority Fixes

1. **docs/migration.md is orphaned** — users upgrading from `docsift` can never find it: no README, docs/index.md, or cross-doc link points to it (grep for inbound `migration.md` links returns zero hits) — add it to README's Documentation list and to docs/installation.md's upgrade note.
2. **README Roadmap (lines 310-317) contradicts architecture.md Future Enhancements** — README still lists "Multi-language support" as future although CJK-aware term matching shipped in phase 04 (06-10 explicitly dropped it from architecture.md for exactly that reason), and lists "REST API" which architecture.md's future list omits — align both lists so the docs don't disagree about the product's future.
3. **Trailing whitespace (28 lines) + mechanical typos** — api-reference.md:13 lines, development.md:10, contributing.md:5 carry trailing whitespace, and quickstart.md:22 has a double space inside a command (`my-notes   --description`) that invites copy-paste confusion — one `sed`/editor sweep closes it.

---

## Detailed Findings

### Pillar 1: Copywriting (3/4)

Strengths (verified this audit):
- `tests/test_docs.py` passes 13/13 against the committed docs.
- Live CLI spot-checks match docs exactly: top-level command set (`bench`, `cleanup`, `collection`, `context`, `get`, `index`, `ls`, `mcp`, `pull`, `search`, `status`), `collection` subcommands incl. `list`/`update-cmd`, `search query|search|vsearch` trio, `context add {path|collection|global} TARGET CONTENT` arity.
- No phantom content anywhere: zero hits for `sif config show`, `SIF_ENV_FILE`, `index.sqlite`, `docsift` outside migration.md (where it is intentional old-vs-new contrast), `--force` on `collection remove` (the G-06-4 fix holds).
- jq example in quickstart.md:359 is `jq '.[].path'`, matching the emitted top-level array (G-06-3 holds).

Findings:
- **WARNING** README.md:314 — Roadmap lists "Multi-language support" as a future item; phase 04 shipped CJK-aware term matching (`search/term_match.py`) and 06-10 deliberately removed this item from architecture.md. The two docs now disagree.
- **WARNING** README.md:315 vs docs/architecture.md — "REST API" appears only in README's roadmap; architecture.md's Future Enhancements list (watcher wiring, plugin system, web UI, query suggestions) is exhaustive and omits it.
- **WARNING** docs/models.md:272 — the `ModelType` enum listing includes `HUGGINGFACE = "huggingface"` verbatim from source (truthful) but with no note that `Settings.validate_model_type` rejects it and the backend raises `NotImplementedError`; a reader of models.md alone would conclude five backends are configurable when only four are.
- **MINOR** docs/search-algorithms.md:152 — "Model Sources: HuggingFace Hub" is fine for GGUF downloads (README `sif pull` tries HF first) but sits in the vector-search section without that framing.
- **MINOR** docs/quickstart.md:22 — `my-notes   --description` (triple space) inside the first add-a-collection command a new user copy-pastes.

### Pillar 2: Visuals (3/4)

- Exactly one H1 per file across all 16 files (README + 15 docs) after stripping fenced blocks; zero heading-level skips anywhere (e.g., no H1→H3 jumps).
- Visual hierarchy is real: README leads with badges → tagline → features → quick start; docs/index.md uses mkdocs-material grid cards (`:material-rocket:` etc., 8 icon references) — mkdocs.yml exists, so the material syntax is intentional and renders.
- Diagrams: README keeps the hand-maintained ASCII layered-architecture box drawing (lines 192-217); architecture.md carries the script-derived Mermaid graph (1 mermaid fence) whose output is byte-identical to `generate_arch_diagram.py` (per 06-10 and the blocking drift gate).
- 431 table rows across the tree; cli-reference.md option tables derive from live Click introspection.
- **WARNING** trailing whitespace (see Pillar 5) and zero inbound links to migration.md weaken the overall document-map picture.

### Pillar 3: Color — mapped to emphasis/accent (3/4)

- Bold is used as the accent sparingly: feature bullets and key terms; no wall-of-bold sections found.
- Blockquote convention consistent: `> **Note:**` in README; admonition-style usage elsewhere matches mkdocs conventions.
- Code ticks used uniformly for commands, flags, env vars, paths.
- **MINOR** No emphasis-system defects found; score capped by the mechanical typos (Pillar 1 findings) that break the polish the emphasis system otherwise provides. No hardcoded-color/overuse analog exists in a docs surface.

### Pillar 4: Typography — mapped to hierarchy/format (3/4)

- Heading depth distribution is consistent: every file's heading tree steps by exactly one level (verified programmatically with fences stripped).
- Code fence language tags: 316 tagged (`bash` 175, `python` 112, `json` 10, `sql` 12, others 4) vs 372 untagged.
- **WARNING (accepted-by-design, informational)** All 372 untagged fences were classified as output/display blocks (`output/other`), never runnable commands — this matches decision D-03 (`text`/no tag → display-only, skipped by validator). Cost: on GitHub (no mkdocs) these render without a language hint; tagging them `text` explicitly would be cosmetic improvement only.
- Inline code vs block usage is disciplined; no mixed bullet styles (dash-only, zero star bullets).

### Pillar 5: Spacing — mapped to whitespace consistency (3/4)

- No tab-indented lines anywhere; all 16 files have balanced code fences; blank-line separation between headings/fences/tables is uniform.
- **WARNING** trailing whitespace: docs/api-reference.md 13 lines, docs/development.md 10 lines, docs/contributing.md 5 lines (28 total). Some markdown linters/renderers preserve these as hard breaks; at minimum they are inconsistent with the other 13 files which are clean.

### Pillar 6: Experience Design — mapped to navigation/getting-started flow (3/4)

Strengths:
- Getting-started flow is complete and truthful: quickstart.md walks install → verify (`sif --version`) → first collection → index → search → export/jq, every command live-verified by the validator; the two reference docs are generator-owned with a blocking CI drift gate (docs.yml, no `|| true`), so the docs cannot silently rot again (G-06-8 closed).
- Error/troubleshooting coverage exists where users hit it: configuration.md troubleshooting (truthful `.env` precedence), mcp-server.md documents `mcp daemon`'s exact live failure mode with redirection to `mcp http`, testing.md documents the FORCE_COLOR failure mode with the exact remedy.
- docs/index.md provides a card-based hub linking installation, cli-reference, api-reference, mcp-server, architecture, search-algorithms, configuration, contributing.

Findings:
- **WARNING** docs/migration.md is fully orphaned — zero inbound links from README.md, docs/index.md, or any other doc (verified by repo-wide grep). A docsift-era user has no path to it.
- **WARNING** README's Documentation list (lines 225-234) covers 10 of 16 files; missing: models.md, migration.md, testing.md, changelog.md, index.md. models.md and testing.md are reachable via development.md/search-algorithms.md deep links, but not from the README hub.
- **MINOR** docs/development.md:705 correctly discloses which docs are outside the validated set — good honesty; no action needed.

---

## Files Audited

- README.md (406 lines)
- docs/: api-reference.md, architecture.md, changelog.md, cli-reference.md, configuration.md, contributing.md, development.md, index.md, installation.md, mcp-server.md, migration.md, models.md, quickstart.md, search-algorithms.md, testing.md
- Live verification: `python -m sif.cli.main --help` (top-level, collection, search, context add), `pytest tests/test_docs.py` (13 passed)
- Planning context: 06-CONTEXT.md, 06-08/09/10-PLAN.md and SUMMARY.md

*Registry safety audit: skipped — no components.json (not a shadcn/frontend project).*
