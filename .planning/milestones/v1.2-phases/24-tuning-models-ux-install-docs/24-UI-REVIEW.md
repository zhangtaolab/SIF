# Phase 24 — UI Review

**Audited:** 2026-11-24
**Baseline:** No UI-SPEC.md — abstract 6-pillar standards adapted to a Click/Rich + stdlib terminal interface. **No web frontend exists**: the phase adds zero `.tsx`/`.jsx`/`.css`/`.scss`/`.html` files (`find src` returns 0), there is no `package.json`, no `components.json`, and no HTML template or static-asset directory. `fastapi`/`uvicorn` in `pyproject.toml` serve the MCP Streamable-HTTP transport (`src/sif/mcp/app.py:257` mounts the SDK app at `/`), not a rendered page. The audit contract is therefore the plan must-haves (24-01..24-07), decisions D-01..D-12 in `24-CONTEXT.md`, and the Phase 23 adapted-terminal precedent. Audited surface: the `sif models` group, `sif models pull`/`status` (TTY table, plain, and `--json`), the hidden deprecated `sif pull` alias, `sif eval --min-heldout` help, `scripts/chunk_sweep.py`, `scripts/breadcrumb_eval.py`, and the Phase 24 install/model docs.
**Screenshots:** not captured — no web UI exists. Ports 3000 and 5173 were closed; port 8080 answered 200 but serves an unrelated **SearXNG 2026.11.1** page, not a SIF surface, so no browser capture was attempted (capturing it would have been a false positive). Visual pillars were scored on real CLI renders at 80/100/120 columns.
**Interaction captures:** off (`workflow.ui_interaction_capture` is `false`). CLI states were exercised live instead: `sif models status` on a TTY (`script -q /dev/null`) and in a pipe, `--json`, under `NO_COLOR`, and under `-q`; `sif models pull bogus` and `sif pull bogus` for the error/deprecation paths; the production `_render_table` re-rendered from the live payload at 80/100/120; all `--help` surfaces at 80/100/120.

**Registry audit:** skipped — no `components.json` (not a shadcn/frontend project).

**Scope note:** Pillars that assume a rendered screen (breakpoints, icon buttons, font scales, 60/30/10 color) are adapted to terminal equivalents: table hierarchy and width responsiveness, Rich style semantics, terminal typography, layout density/rhythm, and CLI state coverage.

---

## Pillar Scores

| Pillar | Score | Key Finding |
|--------|-------|-------------|
| 1. Copywriting | 3/4 | Error and deprecation copy is specific, but `sif models pull --help` shows a bare `[NAME]` whose accepted values are discoverable only by failing, and both runbooks end with `PASS decision=keep-default …` — "PASS" printed for a rejection. |
| 2. Visuals | 2/4 | `sif models status` renders five declared sections as 23 undifferentiated rows of `section.key` strings — no header, separator, or blank row — so the one actionable field (`identity.status`) has no focal point. |
| 3. Color | 3/4 | No hardcoded colors and `NO_COLOR` produces a complete report, but the only styled element is the low-value key column while `cache.state` and `identity.status` carry no emphasis. |
| 4. Typography | 3/4 | All help wraps cleanly (max 78 of 80 columns), but the runbook outcome line is 124–157 characters against the canonical 80. |
| 5. Spacing | 3/4 | Width-responsive, but at 80 columns `cache.path` ellipsizes away the model-name leaf while its parent `settings.cache_dir` prints in full one row above. |
| 6. Experience Design | 3/4 | State coverage is genuinely strong (five cache states, five identity states, exit 0 on mismatch, no tracebacks), but `--quiet` is documented as suppressing non-error output and does not suppress `models status`. |

**Overall: 17/24**

---

## Top 3 Priority Fixes

1. **Group the status table by section instead of prefixing every row** — `_render_plain`/`_render_table` (`src/sif/cli/commands/models.py:217-232`) iterate `_SECTION_ORDER` (`:39`) but flatten it into 23 rows of `settings.model_name`, `cache.path`, `backend.name`, … with no visual break. A user asking "does my index match my configured model?" must scan 23 rows to find `identity.status` at position 15, past five blank identity fields. Emit a subheader or blank row per section (and keep the dotted key only in `--json`/plain machine output) so the identity verdict is the focal point.
2. **Replace the single `PASS decision=… artifact=…` line in both runbooks with a multi-line, unambiguous outcome block** — `scripts/chunk_sweep.py:845` and `scripts/breadcrumb_eval.py:1017` print one 124–157 character line that (a) soft-wraps mid-path at 80 columns and (b) leads with `PASS` even when `decision=keep-default`, i.e. a rejection. This is the same defect Phase 23 raised as its own top fix; the sibling scripts written in Phase 24 reproduced it rather than carrying the correction across. Print the decision, the rule reasons, and the artifact path on separate lines, and use an outcome word that cannot be misread (`VERDICT`, `INSUFFICIENT EVIDENCE`).
3. **Render nulls explicitly and honour `--quiet` in `models status`** — five of 23 rows are blank (`settings.api_base`, `identity.source`, and four `identity.stored_*`), and `_render_plain` (`:221`) emits `key: ` with a trailing space, so a pipe consumer cannot distinguish null from an empty string. Separately, `-q` reaches only the format branch (`:277`), so `sif -q models status` prints all 23 lines despite `--help` saying "Suppress non-error output". Render `-`/`not set` for nulls and either suppress the dump under `-q` or correct the root flag's description.

---

## Detailed Findings

### Pillar 1: Copywriting (3/4)

**WARNING — `sif models pull --help` does not name its accepted values.** `@click.argument("name", required=False)` (`models.py:104`) carries no `help=`, so help renders a bare `[NAME]`. The vocabulary (`embedding`, `reranker`, `query_expansion`, a ModelScope `owner/name`) lives only in `_ACCEPTED_TARGETS` (`:50`), surfaced exclusively from the failure path (`:77`). The user must call the command wrong to learn how to call it right. `docs/models.md` documents the values well, so the gap is help-surface-only: add `help=` to the argument.

**WARNING — the runbook outcome word asserts the opposite of a rejection.** `chunk_sweep.py:845` and `breadcrumb_eval.py:1017` print `PASS decision={decision} artifact={path}`. With `decision=keep-default` — the phase's actual outcome (`docs/benchmarking.md` records defaults unchanged) — the leading token reads "the sweep passed", which is a different claim from "the evidence says keep the default". Phase 23 flagged this exact pattern as its #1 fix (`23-UI-REVIEW.md:31`) without resolving it, and Phase 24's two new scripts repeat it.

**Minor — `identity.status` and `cache.state` are shown as raw internal enum values.** `no-identity`, `no-index`, `mismatch`, `dimension-mismatch` (`models.py:189, 209, 211, 213`) are printed verbatim with no gloss or next action. The vocabulary *is* documented, but in `docs/machine-migration.md:289,304`, not in the `## Model Management` → `### Inspecting model status` section of `docs/models.md` that a reader reaches first; that section describes the `identity` payload without listing the states.

**Minor — booleans are Python-cased in the human table and JSON-cased in `--json`.** `backend.available: True` / `vector_backend.available: True` in both table and plain modes, `"available": true` in `--json`. Conventional for `str()` passthrough, but it means a reader comparing the two modes sees two spellings.

**Pass — the error, deprecation, and new-option copy is otherwise specific.** `Unknown model target 'bogus'; expected one of embedding, reranker, query_expansion, or a ModelScope id 'owner/name'` (exit 1) names the offending input and all valid shapes; `'sif pull' is deprecated and will be removed; use 'sif models pull'.` names both the old and new command; `--min-heldout` help states the default, the range, and why 101 matters ("makes the 0.01 gate admissible"); the install degradation matrix (`docs/installation.md:212-225`) is specific per situation with no generic "went wrong"/"try again" placeholders anywhere on the phase surface.

### Pillar 2: Visuals (2/4)

**WARNING — the declared section structure is not rendered.** The payload is built as five ordered sections (`_SECTION_ORDER`, `models.py:39`), and `_render_table` (`:224-232`) iterates them — but only to prefix each key with its section name in the first column. The result is 23 rows with no header per section, no separator, and no blank row, so the grouping exists in the data model and in the `--json` shape but is invisible on screen. `backend`, `vector_backend`, and `identity` blur into one another; the reader cannot see where the "what is configured" block ends and "what is persisted" begins.

**WARNING — there is no focal point, and the one consequential row is buried.** The question this command exists to answer — do the configured and persisted embedders agree? — is answered by one field, `identity.status`, which renders 15th of 23, after two backend probes and the first of five blank identity fields. Nothing distinguishes it visually: same cyan key, same unstyled value, no marker for `match` versus `mismatch`/`dimension-mismatch`.

**Minor — five of 23 rows are empty.** `settings.api_base` plus `identity.source`, `stored_model_name`, `stored_cache_model_id`, `stored_dimension`, `stored_fingerprint` render as blank cells (see Pillar 6). Visually this reads as broken output rather than as "not applicable in this state".

**Pass — the surviving structure is consistent.** Two balanced columns, a title, right structure preserved across 80/100/120 (the table is genuinely width-responsive: `cache.path` truncates at 80 and fits fully at 120), box-drawing borders intact, and `--json` provides the complete keyed shape for anyone who needs it.

### Pillar 3: Color (3/4)

**Pass — no hardcoded colors anywhere on the phase surface.** The only style is `table.add_column("Setting", style="cyan")` (`models.py:227`) and the `[dim]` pull confirmation (`:116`); no hex/rgb literals appear in the phase's files. `NO_COLOR=1` renders a complete, fully readable report — the table borders and every value survive, so no meaning is carried by color alone.

**Minor — emphasis is inverted.** The one colored element is the key column (`settings.model_name`), which is the least decision-bearing text on screen; the values a user acts on — `cache.state` and `identity.status` — get no semantic style, so `valid`/`match` and `unverified`/`dimension-mismatch` look identical. If the values are styled, use text-backed markers as well (a state word or symbol), not color alone, consistent with the existing `NO_COLOR` guarantee.

### Pillar 4: Typography (3/4)

**WARNING — the runbook outcome line ignores the canonical width.** Measured at 124–157 characters depending on the artifact path (`PASS decision=keep-default artifact=/Users/…/24-tuning-models-ux-install-docs/bench/breadcrumb-verdict.json` = 157). At 80 columns this soft-wraps inside the directory name, so the last thing a user sees after a multi-hour sweep is a broken path fragment.

**Minor — null values leave a trailing space in machine output.** `_render_plain` (`models.py:221`) interpolates `''` for `None`, producing `settings.api_base: ` (verified at the byte level). For a stated pipe contract ("non-TTY output is plain `section.key: value` lines", `models.py:1-5`), a trailing space where a value should be is a weak signal.

**Pass — every help surface wraps within 80 columns.** Measured maximum line lengths: `sif --help` 77, `sif models --help` 76, `sif models pull --help` 68, `sif models status --help` 56, `sif pull --help` 55, `sif eval --help` 78, `chunk_sweep.py --help` 78, `breadcrumb_eval.py --help` 78. The two runbook helps share an identical option order and phrasing, which reads as one interface rather than two.

### Pillar 5: Spacing (3/4)

**WARNING — the identifying path segment is the first thing 80 columns sacrifices.** At the canonical 80 columns `cache.path` renders `/Users/forrest/Library/Caches/sif/models/…` — the leaf (`Qwen/Qwen3-Embedding-0.6B`), which is the part that says *which* model is cached, is what gets dropped. One row above, `settings.cache_dir` — the same path minus the model — prints in full. The table therefore spends its width on the prefix and truncates the distinguishing suffix; at 100 columns the leaf reappears as `Qwen/Qwen3-Embedding…`, and at 120 it fits entirely. Since the table is width-responsive, this is a prioritization defect, not a fixed-width one: let the value column take the remaining width, or drop the redundant `settings.cache_dir` row in favour of the full `cache.path`.

**WARNING — the runbook outcome line has no layout.** Same evidence as the Pillar 4 warning; from the spacing side it is a single unbroken 124–157 character block with no field separation and no line of its own for the artifact path.

**Minor — the table stretches to fill rather than to content.** At 100 and 120 columns the value column expands to fill the console, so a short key/value list leaves 30–40 columns of trailing padding on every row. `min_width`-bounded columns, or a deliberate full-width layout with the value column left-aligned at a fixed measure, would read better than a stretched two-column grid.

**Pass — no arbitrary padding or ad-hoc spacing.** The phase adds no manual padding overrides, no `Padding`/`box` customization, and no header/footer rules; both runbook helps and all `sif models` help use standard Click/argparse wrapping.

### Pillar 6: Experience Design (3/4)

**WARNING — `--quiet` does not suppress `models status`.** The root flag is documented as "Suppress non-error output" (`sif --help`), but `models_status_cmd` (`models.py:277`) only branches on `is_quiet()` to choose the *format*: on a TTY it falls through from the Rich table to `_render_plain`, and in a pipe it was already plain. Verified live: `sif -q models status` prints all 23 lines in both a TTY and a pipe. Either suppress the dump under `-q` (matching the root description) or correct the description; note that `models pull` also always prints its `model_id: path` result line (`:117`), so this is a project-wide convention conflict rather than a Phase 24-only slip — worth resolving once, deliberately.

**WARNING — null is indistinguishable from empty.** Five fields print as blank cells / `key: ` (see Pillars 2 and 4). For a status command whose whole job is to report what is and is not configured, "this value is not set" deserves an explicit token (`-`, `not set`) rather than an empty cell that reads as a rendering fault.

**Pass — state coverage and failure handling are otherwise strong.** Cache state is fully enumerated (`absent` / `empty` / `unverified` / `legacy` / `valid`, documented as a table in `docs/models.md`); identity state covers `no-index` / `no-identity` / `match` / `mismatch` / `dimension-mismatch` with tests for each (`tests/unit/cli/test_models.py:221+`); a mismatch is reported and the command still exits 0, as documented and verified; the backend probe uses `find_spec` plus distribution metadata and imports nothing; the deprecation notice goes to **stderr** with stdout left empty (verified: `sif pull bogus 2>/dev/null` produces no stdout), so pipes stay clean; `models pull` converts `ImportError`/`OSError`/`RuntimeError`/`ValueError` into `ClickException` with tests asserting no traceback reaches the user; and invalid targets exit 1 with the accepted set named.

---

## Minor Recommendations (not in top 3)

1. Add `help=` to the `sif models pull` `[NAME]` argument naming the registry names and `owner/name` (`models.py:104`).
2. Render `-` or `not set` for `None` in both `_render_plain` and `_render_table` (`models.py:221, 231`).
3. Style `cache.state` and `identity.status` values with text-backed success/warning markers rather than adding a new palette entry (`models.py:227`).
4. List the `identity.status` states in `docs/models.md` `### Inspecting model status`, or link `docs/machine-migration.md` from it.
5. Print the runbook outcome as multiple lines with the artifact path on its own line, and rename `PASS` to a decision-neutral outcome word (`chunk_sweep.py:845`, `breadcrumb_eval.py:1017`).
6. Bound the status table's column widths or suppress the redundant `settings.cache_dir` row so the full `cache.path` survives at 80 columns.
7. Reconcile `--quiet` semantics across `models status` and `models pull` against the root flag description (`models.py:116-117, 277`).
8. Normalise boolean rendering (`True` vs `true`) between the human and `--json` surfaces (`models.py:231`).

---

## Files Audited

- `src/sif/cli/commands/models.py` — `_SECTION_ORDER` (`:39`), `_ACCEPTED_TARGETS` (`:50`), `resolve_model_target` and its error (`:60-77`), `pull` argument/options (`:103-117`), identity status values (`:189, 209, 211, 213`), `_render_plain` (`:217-221`), `_render_table` (`:224-232`), `models_status_cmd` format branch (`:274-280`).
- `src/sif/cli/commands/pull.py` — deprecated alias; stderr `Console` (`:31`), `_DEPRECATION_NOTICE` (`:40`), legacy GGUF/URL path.
- `scripts/chunk_sweep.py` — `--help` at 80/100; outcome line (`:845`); `--dry-run`/`--json`/`--force` surface.
- `scripts/breadcrumb_eval.py` — `--help` at 80/100; outcome line (`:1017`); stage-plan printing (`:291-298`).
- `docs/models.md` — `## Model Management` (pull/status, cache-state table, model-dimension note).
- `docs/installation.md` — `## Degradation Matrix` (`:212-225`) and client-configuration entry point.
- `docs/machine-migration.md` — identity/cache state vocabulary (`:289, 304`).
- `docs/benchmarking.md` — Phase 24 QUAL-02/QUAL-03 sections (referenced for the `keep-default` outcome).
- `tests/unit/cli/test_models.py` — pull argument resolution and error copy; `TestModelsStatusIdentity` state matrix; non-TTY one-line contract.
- `.planning/milestones/v1.2-phases/24-tuning-models-ux-install-docs/24-CONTEXT.md` — D-01..D-12.
- `.planning/milestones/v1.2-phases/24-tuning-models-ux-install-docs/24-0{1..7}-SUMMARY.md` and `24-0{1..7}-PLAN.md` — must-haves and recorded outcomes.
- `.planning/milestones/v1.2-phases/23-harrier-gated-evaluation/23-UI-REVIEW.md` — adapted-terminal precedent and the unresolved single-line outcome fix (`:31`).
- Captures: `/tmp/24-ui-captures/` — `root-help-80|100|120.txt`, `models-help-*`, `models-pull-help-*`, `models-status-help-*`, `pull-alias-help-*`, `chunk-sweep-help-80|100.txt`, `breadcrumb-help-80|100.txt`, `plain.txt` (live plain payload), `payload.json` (live `--json`), `render2.py`/`render_ordered.py` (production `_render_table` at 80/100/120).
