# Phase 20 — UI Review

**Audited:** 2026-11-18
**Baseline:** No UI-SPEC.md — abstract 6-pillar standards adapted to a Click/Rich terminal and MCP tool surface. No web frontend exists (no `.tsx`/`.jsx`/`.css`/`.scss`, no `components.json`). The audited surface is what Phase 20 changed: `sif search {search,vsearch,query} --filter`, `sif collection metadata` ([NAME], `--filter`, `--match`, `--min-count`, `--sort`, `--limit`, `--value-limit`, `--json`), the table/JSON rendering of the discovery envelope, the filter/match validation and error copy, the D-09 too-selective notice (code-derived), the one-time typed-metadata backfill notice, and the MCP `filter` fields plus `metadata` tool contract. PHASE-20 decisions D-01..D-20 and the five plan acceptance criteria are the functional contract; there is no UI-SPEC.
**Screenshots:** not captured — no web UI exists. Ports 3000/5173 did not answer; port 8080 answered but serves an unrelated SearXNG instance (`generator: searxng/2026.11.1`), not a SIF surface. Real CLI renders were captured as text at 80/100/120 columns against a purpose-built 9-document, two-collection corpus (strings, numbers, booleans, string arrays, nested objects, nulls, mixed arrays, reserved `path`/`mtime` frontmatter keys, a `qmd.metadata` namespace, bracketed keys, and differing file mtimes), plus `--help`, JSON, empty, and error captures.
**Interaction captures:** off (`workflow.ui_interaction_capture` false). CLI interaction states were exercised manually instead: all three `--filter` commands (valid, invalid JSON, invalid AST, unknown operator, budget, non-object root, extra property, empty match), `collection metadata`/filter/match/min-count/sort/limit/value-limit/JSON/empty-index/unknown-collection states, 80/100/120-column renders, stdout/stderr separation under `NO_COLOR`, and a real MCP stdio session (`tools/list` + `metadata` calls with valid, filtered, invalid-filter, invalid-match, and unknown-collection inputs).

**Scope note:** Rendered-screen pillars (breakpoints, icon buttons, font scales, 60/30/10 color distribution) are adapted to terminal equivalents: table hierarchy and width responsiveness, Rich style semantics, terminal typography, layout density/rhythm, and CLI/MCP state coverage. Line references are to current `dev` HEAD `97a09e1` (which includes the Phase 20 WR fixes and the Phase 22 MCP SDK shell that now hosts `metadata` in `src/sif/mcp/tools.py`). Phase 19's carried defects (`--min-score`/`Score` inversion, per-chunk identity truncation, generic past-end copy) are not re-scored as new Phase 20 findings unless this phase changed the surface.

**Registry audit:** skipped — no `components.json` (not a shadcn/frontend project).

---

## Pillar Scores

| Pillar | Score | Key Finding |
|--------|-------|-------------|
| 1. Copywriting | 2/4 | The filter grammar is documented nowhere user-facing; help says only "qmd-compatible"; `--match` semantic errors say `filter.*`; pydantic internals leak (`Input tag`, `discriminator`, `Extra inputs are not permitted`); internal IDs `D-03`/`Phase 20` ship in help/generated/user docs |
| 2. Visuals | 2/4 | The default discovery table hides the actual values, the `multiValued` flag, and the `documents`/`filteredDocuments` denominators; the built-in `mtime` range is epoch and wraps unlabeled at 80 columns |
| 3. Color | 3/4 | Semantic Rich styles only and no color-only meaning, but the palette emphasizes `Source`/`Key` over the decision-bearing `Values`/`Range`, and `magenta` is added without semantics |
| 4. Typography | 2/4 | Fractional mtime medians render as `1.79499e+09`; mtime ranges are epoch; raw lowercase enums; `2 of 5 +3 more` is redundant; `3 / 6.5 / 10` is unlabeled |
| 5. Spacing | 3/4 | Table structure fits 80/100/120, but the `mtime` Range cell wraps across three lines at 80 and again at 100 with wide value windows |
| 6. Experience Design | 2/4 | BLOCKER: unescaped Rich markup in a frontmatter key rewrites the key (`[bold]evil` → `evil`) or crashes `collection metadata` with a `MarkupError` traceback; a zero-match filter and an empty index render the same two zero rows; `skippedKeys` is a mislabeled, reasonless occurrence count; MCP `filter`/`match` schemas are opaque |

**Overall: 14/24**

---

## Top 3 Priority Fixes

1. **BLOCKER — user-derived metadata keys are passed to Rich unescaped and can alter or crash the default discovery table** — `_render_metadata_table` adds `entry["key"]` directly to a Rich `Table` (`src/sif/cli/commands/collection.py:410, 421`); Rich parses markup in table cells. Verified live: a valid YAML key `[bold]evil` renders as `evil` (the exact key silently changes), and a key `[/bold]` or `[/]` aborts the command with a full `rich.errors.MarkupError` traceback (exit 1). This breaks the command's whole purpose ("report filterable metadata keys") for an otherwise valid corpus and violates the project's established truncate-then-`rich.markup.escape` convention used in `eval.py`. Escape every user-derived cell (`escape(str(entry["key"]))`, and audit any future value rendering), add a regression with bracketed keys, and keep JSON (which preserves the key verbatim) as the reference.
2. **The default discovery table cannot answer what metadata exists** — the `Values` column prints only `returned of distinct` counts (`3 of 3`, `0 of 8`), never a value; `multiValued` is absent; `documents` and `filteredDocuments` are never shown, so the `--filter` coverage denominator exists only in `--json`; built-ins report `0 of N` as if no values existed; `--min-count` leaves rows at `0 of 0`; `skippedKeys` is a document-key occurrence count mislabeled "keys" (verified 5 output rows vs 4 distinct keys); and `mtime` is reported as epoch seconds (`1767196800 / …`) rather than the ISO form the filter accepts. Fix: render compact `value (count)` samples, mark arrays, add a scope/coverage line (`N documents · M after filter · collection`), format `mtime` as ISO-8601, label the range `min / median / max`, report distinct skipped keys with reasons (the sidecar stores both), and use a single non-redundant window phrasing.
3. **No user-facing filter or match grammar exists, so the phase's central capability is undiscoverable** — `--filter` help is only "Metadata filter as a JSON AST (qmd-compatible)." on all three commands (`src/sif/cli/commands/search.py:521-527, 722-728, 953-959`); `--match` is one line with no grammar; `docs/quickstart.md:221` shows one `eq` example; `docs/mcp-server.md:132` says "see `metadata`" while `:180` says "the same filter grammar as `query`" (circular); the MCP `filter`/`match` properties are bare `{"type":"object"}` with no description or examples (`src/sif/mcp/tools.py:261-269`; `src/sif/mcp/protocol.py:247-262`); and the only full operator reference is developer-facing `docs/architecture.md:680-694`. Fix: publish a "Filtering and discovery" reference (17 operators, node shapes, typed equality, presence semantics, reserved `path`/`mtime`, ISO mtime, budgets, `--match` restrictions, examples), link it from every help/description, add property descriptions/examples to the MCP schema, and document the stored-path form (resolved absolute paths) so `path prefix` filters do not return silent zeroes.

---

## Detailed Findings

### Pillar 1: Copywriting (2/4)

**WARNING — the grammar is absent from all user-facing entry points.** `sif search {search,vsearch,query} --help` and `sif collection metadata --help` describe `--filter` as a "JSON AST (qmd-compatible)" without an operator list, node shape, example, reserved-field note, or pointer. `--match` is "Narrow reported entries by key or value (JSON AST)" only; the required `field: key|value` restriction and the `exists`/`all`/ordering rejections are never explained. `docs/quickstart.md:219-226` has a single `eq` example; `docs/mcp-server.md:132, 177-183` is circular. The only complete reference is `docs/architecture.md:680-694`, which is developer documentation, not shipped help or MCP tool metadata. An agent sees four tool descriptions that mention `filter` but no schema shape.

**WARNING — `--match` semantic errors name the wrong option.** A `--match` AST violation renders the shared `filter.<path>` prefix: live captures include `Error: filter.gt: "gt" is not available on field 'key'; a key is text` for `sif collection metadata --match ...`, `filter.exists: "exists" is not available in the match grammar`, and `filter: a filter node must be an object` for `--match null`. The user invoked `--match`. `FilterValidationError` always renders `filter.` (`src/sif/core/filters.py:74-86`), and `parse_match_option` passes that string through (`src/sif/cli/filter_options.py:37-44`); Phase 20-05's own SUMMARY recorded this as a shipped convention. Remap the label for match failures or give `FilterValidationError` an option label.

**WARNING — shape errors leak pydantic internals despite a comment claiming otherwise.** `_pydantic_error_to_filter_error` copies pydantic's `msg` verbatim (`src/sif/core/filters.py:292-316`) while its docstring says callers can self-correct "without seeing pydantic internals." Live captures: `{}` → `filter: Unable to extract tag using discriminator 'operator'`; a missing field → `filter.eq.field: "eq" property 'field': Field required`; an unknown key → `filter.eq.extra: "eq" property 'extra': Extra inputs are not permitted`; an empty field → `String should have at least 1 character`; an unknown operator → `Input tag 'bogus' found using 'operator' does not match any of the expected tags: 'eq', …`. The hand-written semantic messages are good; the shape layer is not. Translate these into remedy-bearing copy (`missing "operator"; expected one of …`, `unexpected property 'extra'`, `"field" must not be empty`).

**WARNING — internal planning IDs ship in user-visible copy.** `sif collection metadata --help` and the generated `docs/cli-reference.md:183-186` contain `fields (D-03)`. `docs/mcp-server.md:182` calls the response "the frozen Phase 20 discovery envelope." Users and agents do not know D-03 or Phase 20. This repeats the class of Phase 18/19 finding ("internal decision ID in shipped output") on a new surface.

**Minor — unknown collection on MCP names no collection.** CLI says `Collection 'nope' not found`; the MCP `metadata` tool returns `Error executing tool metadata: One or more collections were not found` (`src/sif/mcp/backend.py:709-716`). With several names, an agent cannot tell which failed. List the missing names.

**Minor — the too-selective notice is awkward and offers no remedy (code-derived).** `src/sif/search/vector.py:31-35` says "Metadata filter is highly selective earlier than the requested page: %d of %d matching documents reached, %d requested; returning best-effort results." "Highly selective earlier than the requested page" is not plain English and there is no action ("narrow the filter or lower --limit"). Not exercised live because no embedding run was made; the text is code-derived.

**Pass — the semantic validation copy is otherwise strong.** Hand-written messages name the operator, field, and dotted path (`filter.and.operands.1.gt: "gt" requires a numeric value; field 'priority' got str`; `filter.in: "in" requires a non-empty homogeneous list`; `filter.gt: "gt" does not support ordering on a text built-in; field 'path'`). Invalid input exits 1 with no traceback (except the Rich markup case above), and validation happens before the database opens on all three commands and before tool execution on MCP.

**Pass — the migration and stream copy is honest.** The one-time backfill emits `WARNING: Upgrading index metadata: deriving typed metadata for N documents (one-time pass, no file re-parse)` on stderr while `--json` stdout stays strict JSON (`src/sif/database/schema.py:344-352`; verified with separated streams). The MCP `metadata` tool description is specific about keys, types, counts, ranges, remainders, and built-ins (`src/sif/mcp/tools.py:74-78`).

### Pillar 2: Visuals (2/4)

**WARNING — the `Values` column shows no values.** The renderer is `_value_window_text` (`src/sif/cli/commands/collection.py:389-394`): `"{len(values)} of {distinctValues}"` plus `"+N more"`. Live 80/100/120 captures show `status: 3 of 3`, `tags: 5 of 5`, `priority: 4 of 4`, `published: 2 of 2` — never `active`, `archived`, `alpha`, `10`, `true`, or a count per value. The envelope's per-value data (`values: [{"value": ..., "documents": ...}]`) is printed only by `--json`. A user cannot answer "which status values can I filter on?" without knowing to switch formats, and the column header "Values" promises content it does not deliver.

**WARNING — the coverage denominators are invisible.** `documents` (scope) and `filteredDocuments` (filter-aware) are computed and present in JSON (`src/sif/database/metadata_repository.py:503-515`) but `_render_metadata_table` never prints either. Under `--filter status=active` the table shows per-key `2` counts and built-in `2` counts with no "2 of 8" context; a reader cannot tell whether the filter reduced the corpus or the corpus is small. D-14/D-15's "filter-aware coverage" is therefore JSON-only.

**WARNING — the built-in rows claim `0 of N`.** Both built-ins render `values: []` with `remainingValues == distinctValues`, and the table prints `0 of 8` for `path`, `0 of 3` for `mtime` (`collection.py:413`). "0 of 8" reads as "no values exist" when the meaning is "eight distinct values exist but none are listed." This is the opposite of the discovery tool's purpose, and it is the only place a user could learn the path format that `path prefix` filters must use (the index stores resolved absolute paths — live `--filter path prefix /tmp/...` returned zero because the stored form was `/private/tmp/...`).

**WARNING — `multiValued` is not shown.** `tags` (array) and `status` (scalar) are visually indistinguishable: both render type `string` and a value count. The JSON carries `"multiValued": true` (`protocol.py:227-236`); the table does not. That flag determines whether `all`/`contains` or `eq`/`in` is the right operator, so its absence is an authoring trap.

**WARNING — the `mtime` range is unreadable.** Live 80-column capture:
```
│ built-in │ mtime  │ number │ 8 │ 0 of 3 │ 1767196800 / │
│          │        │        │   │        │ 1767196800 / │
│          │        │        │   │        │  1774022340  │
```
The three bounds are unlabeled, right-justified into a narrow column, and split across lines; at 100 columns `--value-limit 2` forces the same wrap. A user cannot tell which number is min, median, or max, nor convert an epoch to a date without external work. The filter accepts ISO dates (`mtime gte "2026-03-01"` worked), so the report format should match the input format.

**Minor — no focal point or scope cue.** The title is the generic `Metadata` (`collection.py:399`); it does not name the collection scope, the filter/match state, or the document count. The built-in-vs-frontmatter split is text-only in a `Source` column, and the two decision-bearing columns (`Values`, `Range`) are the only unstyled ones.

**Pass — structure and ordering are sound.** Built-ins always precede frontmatter rows, default key ordering is document-count descending then key ascending, type rows split mixed-type keys, numeric columns are right-aligned, and the `--sort value`/`--limit`/`--value-limit` windows behave deterministically. `NO_COLOR=1` renders a complete table.

### Pillar 3: Color (3/4)

**Minor — color emphasizes metadata provenance over decision data.** `_render_metadata_table` styles `Source` magenta, `Key` cyan, `Types` green, and `Documents` yellow (`collection.py:400-405`); `Values` and `Range` are unstyled. In a discovery table the reader's decisions are driven by values and ranges, so the color hierarchy points at labels instead of data. `magenta` is also a new palette entry for this table without semantic meaning (built-in vs frontmatter is already carried by text).

**Minor — no semantic emphasis for the filter state or built-ins.** A filtered table looks identical in color to an unfiltered one; built-in rows have no distinct style beyond the word "built-in." Text-only signaling is accessible; color is simply unused where it would add meaning.

**Pass — no hardcoded colors and no color-only meaning.** The phase surface uses semantic Rich names only; `grep` found no hex/rgb values in the new CLI/MCP/filter modules. Warnings are yellow (or logger-prefixed on stderr), errors are red via Click, secondary text is dim, and every distinction is text-backed. `NO_COLOR` output is complete and readable.

### Pillar 4: Typography (2/4)

**WARNING — `_format_number` loses precision and switches to scientific notation.** `return str(int(value)) if float(value).is_integer() else f"{value:g}"` (`src/sif/cli/commands/collection.py:376-378`). A fractional mtime median renders `1.79499e+09` in live output; `:g` keeps six significant digits, so the reported range is not exact and looks like a different value. Any large fractional numeric metadata value is affected. Use a fixed/exact decimal formatter (or ISO for mtime) with a documented precision, and never scientific notation in this table.

**WARNING — mtime is printed as epoch seconds.** `range.min/median/max` for the built-in `mtime` are floats of epoch seconds; the table prints them raw. The same command accepts `--filter '{"field":"mtime","operator":"gte","value":"2026-03-01"}'`, so the human surface should render `2026-01-01 / 2026-03-01 / 2026-03-20` (with raw epochs in JSON if needed).

**WARNING — the range is unlabeled.** `3 / 6.5 / 10` and `1 / 3 / 10` have no `min / median / max` header or cell labels. The JSON uses named keys; the table relies on the reader knowing the order. At 80 columns the wrap removes even positional cues.

**WARNING — raw lowercase enums in human output.** `Types` prints `string`, `number`, `boolean` and `Source` prints `built-in`/`frontmatter` (`collection.py:408-425`). This is machine vocabulary in a Title-Case human table; use `String`, `Number`, `Boolean`, `Built-in`, `Frontmatter` (or keep the machine values in JSON only).

**Minor — redundant window arithmetic.** `_value_window_text` produces `2 of 5 +3 more` and, at `--value-limit 0`, `0 of 5 +5 more`; `+N more` duplicates the remainder already implied by `of N`. Use `2 of 5 shown` or `5 distinct (2 shown)` once, not both.

**Minor — `--min-count` rows render `0 of 0`.** Live `--min-count 3` shows `tags 6 │ 0 of 0`, `priority 5 │ 0 of 0`, `published 2 │ 0 of 0`. The key is still filterable, but "0 of 0" does not say "no value has ≥3 documents." Use `no values meet --min-count 3` or suppress the row.

**Minor — `skippedKeys` is called "keys" but counts occurrences.** The sidecar PK is `(document_id, key)` and discovery uses `COUNT(*)` (`src/sif/database/metadata_repository.py:532-535`); after adding the same nested key to a second document, live output became `... 5 keys skipped as non-indexable` while only 4 distinct keys were skipped. Say "5 skipped key entries (4 distinct keys)" or compute the distinct count.

**Pass — numeric typography is otherwise consistent.** Integers omit `.0`, the even-cohort median is correct (`6.5`), numeric columns are right-aligned, counts are integers, and the JSON preserves exact values. The display defects above are formatting/choice issues, not arithmetic bugs (the median and remainders match the JSON envelope).

### Pillar 5: Spacing (3/4)

**WARNING — the canonical 80-column render breaks the `mtime` range.** A six-column table with a right-aligned numeric range does not fit the range on one line at 80; the cell wraps into three lines with a leading double-space on the continuation and no label. At 100 columns `--value-limit 2` widens the `Values` cell enough to wrap the range again (`1767196800 / 1767196800 /` then `1774022340`). This is the terminal analog of a table that does not respond at the smallest supported width: Rich ellipsizes/wraps rather than reflowing the row.

**Minor — continuation alignment is misleading.** The wrapped range's first continuation line is right-aligned but the second is offset differently, so the three bounds do not read as a vertical group. Folding the range into a labeled multi-line cell (`min 1767196800`) or a compact ISO date would fix the rhythm.

**Minor — footers have no separation.** `console.print(table)` is followed immediately by `... N more keys` / `... N keys skipped ...` (`collection.py:426-435`), and the JSON path has no footer. Two adjacent ellipsis lines read as one block; a blank line or a single combined footer would group them.

**Pass — the rest of the layout is disciplined.** Rich default padding is used throughout; the table fits 80 columns; the four footer lines are short; no arbitrary padding overrides or ad-hoc blank-line counts were introduced. Search tables were not changed by this phase.

### Pillar 6: Experience Design (2/4)

**BLOCKER — unescaped Rich markup breaks the default discovery surface.** Detailed in Top Fix 1: a valid YAML key `[bold]evil` is silently rendered as `evil`, and `[/bold]`/`[/]` produce a `rich.errors.MarkupError` traceback and exit 1. The JSON path preserves the key, so the human and machine surfaces disagree about what keys exist. This violates the project's established convention (`eval.py` truncates then `rich.markup.escape`s every user/config-derived cell) and Phase 20's own "discovery never lies" invariant.

**WARNING — a zero-match filter and an empty index are indistinguishable.** The table always prints the two built-in rows. Live empty-filter capture (`--filter status=eq absent`):
```
│ built-in │ path  │ string │ 0 │ 0 of 0 │ │
│ built-in │ mtime │ number │ 0 │ 0 of 0 │ │
```
An empty index produces the identical table; there is no "No documents match this filter (8 in scope)" or "No documents indexed" line. The JSON silently carries `documents: 8, filteredDocuments: 0`, so only JSON users can tell the difference. D-17's empty-match sentinel is behaviorally correct but invisible on the default human surface.

**WARNING — filtered search empty states are generic.** On a zero-match `--filter`, `sif search search needle` prints `No results found.` (verified exit 0), identical to a query with no matches and to a past-the-end page (`src/sif/cli/commands/search.py:664-668, 894-898, 1256-1260`). A user cannot distinguish "the query matched but the filter excluded everything" from "nothing matched the query." Add filter-aware copy naming the filter and, where known, the matched counts.

**WARNING — skipped keys are a count with no key, reason, or remedy.** The sidecar stores `(key, reason)` (`document_metadata_skips`) and the derivation has eight reason codes, but discovery exposes only `skippedKeys` and the CLI footer says "N keys skipped as non-indexable" (`collection.py:429-435`). An agent told "5 skipped" cannot discover which keys to fix, why they were skipped (nested/null/mixed_array/cap_*), or that the document still matches its other keys. Report distinct keys and a reason breakdown (bounded), or at minimum name the first few.

**WARNING — the MCP `filter`/`match` inputs are opaque.** Live `tools/list` shows `query`, `lex_search`, `vec_search`, and `metadata` all declaring `"filter": {"anyOf": [{"additionalProperties": true, "type": "object"}, {"type": "null"}], "title": "Filter"}`, with no `description`, `examples`, or operator reference; `match` is the same. The `metadata` description defers to "the same filter grammar as query," and the `query` description never describes a grammar. A model must infer the entire 17-operator AST from the one quickstart example. Add schema descriptions/examples and link the reference in the tool descriptions.

**Minor — redacted path format makes `path prefix` a silent-zero trap.** Stored paths are resolved absolute paths (verified `/private/tmp/...`), and the built-in `path` values are never listed (`values: []`), so a user filtering `path prefix "/tmp/..."` gets zero results with no hint that the stored form is `/private/tmp/...`. Document the stored form and show a sample path or two (or expose the value window) so the built-in is usable.

**Minor — the discovery table version of "scope" is implicit.** The title says only `Metadata`; `documents`/`filteredDocuments` and the selected collection are not printed. Adding a one-line header would make filtered coverage visible without JSON.

**Pass — input-error experience is strong.** Invalid JSON exits 1 with `filter:`/`match:` labels; semantic violations name operator, field, and dotted path; non-object roots and budgets fail before any DB open; MCP returns a controlled `isError` tool result (verified through a real stdio session) rather than an `INVALID_PARAMS` protocol error; no traceback is emitted for normal bad input. The one-time backfill notice is on stderr and the D-09 notice is logger-only (code-derived), so `--json` and MCP text stay machine-clean. Bounded key/value windows, exact remainders, and `--json`/MCP `exclude_none` consistency are solid.

---

## Minor Recommendations (not in top 3)

1. Escape every user-derived cell in the discovery table with `rich.markup.escape`; add a bracketed-key regression (`collection.py:410, 421`).
2. Remap `--match` semantic failures to a `match.` label instead of the shared `filter.` prefix (`filter_options.py:37-44`; `core/filters.py:74-86`).
3. Translate pydantic shape failures into remedy-bearing copy (`missing "operator"; expected one of …`, `unexpected property …`, `"field" must not be empty`) and add tests (`core/filters.py:292-316`).
4. Make the unknown-operator message user-facing rather than `Input tag … does not match any of the expected tags`.
5. Name the missing collection(s) in the MCP `metadata` error (`backend.py:709-716`).
6. Remove `(D-03)` from the command docstring/generated help (`collection.py:491-497`; `docs/cli-reference.md:184`) and "Phase 20" from `docs/mcp-server.md:182`.
7. Reword the too-selective notice in plain English and add a remedy (`vector.py:31-35`).
8. Report distinct skipped keys with reasons; do not call occurrences "keys" (`metadata_repository.py:532-535`; `collection.py:429-435`).
9. Label the range `min / median / max`; format built-in `mtime` as ISO-8601 (`collection.py:381-386, 397-425`).
10. Fix `_format_number` to preserve precision and never emit scientific notation (`collection.py:376-378`).
11. Replace built-in `0 of N` with `N distinct (not listed)`; drop the redundant `+N more` when `of N` already states it (`collection.py:389-394, 413`).
12. Show `multiValued` (array vs scalar) in the table (`collection.py:400-425`).
13. Add a coverage header (`documents`, `filteredDocuments`, collection scope) to the table and to its title (`collection.py:397-399`).
14. Add filter-aware empty copy to the metadata table and to `sif search`/`vsearch`/`query` (`search.py:664-668, 894-898, 1256-1260`).
15. Render display labels for `string`/`number`/`boolean`/`built-in`/`frontmatter` (`collection.py:408-425`).
16. Add the full filter/match reference to user docs, link it from `--filter`/`--match` help and MCP tool descriptions, and add `description`/`examples` to the MCP `filter`/`match` schema properties (`docs/quickstart.md:219-277`; `docs/mcp-server.md:132, 177-183`; `tools.py:74-78, 261-269`).
17. Document the deliberate camelCase CLI `--json` envelope (`filteredDocuments`, `totalKeys`, …) or offer a snake_case mode, since it differs from every other SIF CLI JSON output (`protocol.py:265-282`; `collection.py:530-531`).

---

## Files Audited

- `src/sif/core/filters.py` — 17-operator AST, `FilterValidationError`, budget walk, pydantic error translation, `parse_filter`/`parse_match`.
- `src/sif/search/filters.py` — parameterized compiler, scopes, built-in `path`/`mtime`, `compile_match`, scope counters (read for behavior behind the filter surfaces).
- `src/sif/database/metadata_repository.py` — derivation, `discover`, key/type/value windows, `skippedKeys`, built-ins, medians.
- `src/sif/database/schema.py` — `_backfill_metadata_values` notice and marker behavior.
- `src/sif/database/repositories.py` — typed-row sync at document create/update (read for the write contract).
- `src/sif/core/models.py` — `SearchOptions.filter` (read for threading).
- `src/sif/search/bm25.py`, `src/sif/search/vector.py`, `src/sif/search/hybrid.py` — filter slots, D-09 notice text, pre-RRF passthrough (read; vector notice is code-derived).
- `src/sif/cli/filter_options.py` — the one JSON/AST error adapter.
- `src/sif/cli/commands/search.py` — `--filter` on all three commands, empty states, JSON/table renderers.
- `src/sif/cli/commands/collection.py` — `collection metadata`, filter-aware discovery, table/JSON renderers, footers.
- `src/sif/mcp/tools.py` — metadata tool registration/description, filter/match parsing, tool error mapping.
- `src/sif/mcp/protocol.py` — `MetadataInput`/`MetadataOutput` and summary models; filter fields on the three search inputs.
- `src/sif/mcp/backend.py` — `hybrid_search`/`lex_search`/`vec_search` filter threading, `metadata` discovery backend, unknown-collection error.
- `docs/cli-reference.md` — generated `--filter` rows and `collection metadata` section (including the `D-03` leak).
- `docs/quickstart.md` — filter example and discovery narrative.
- `docs/mcp-server.md` — filter/`metadata` tool documentation (circular grammar reference; `Phase 20` leak).
- `docs/architecture.md` — the only complete filter/match grammar reference (developer docs).
- `tests/unit/cli/test_collection.py` — `TestCollectionMetadata` render/JSON/window/error expectations.
- `tests/unit/cli/test_search_filter.py`, `tests/unit/cli/test_search.py` — filter option matrix, composition, no-filter regressions.
- `tests/unit/core/test_filters.py`, `tests/unit/search/test_filters_sql.py` — AST/compiler contracts (read for intent).
- `tests/unit/database/test_metadata_values.py`, `tests/integration/test_metadata_filtering.py` — derivation/discovery/parity contracts (read for intent).
- `tests/unit/mcp/test_backend.py`, `tests/unit/mcp/test_integration.py` — MCP filtering/metadata contracts (read for intent).
- Live text captures at HEAD `97a09e1`: `collection metadata` at 80/100/120 (default, `--filter`, `--match`, `--min-count`, `--sort value`, `--limit`, `--value-limit 0/2`, JSON, empty filter, empty index, unknown collection, invalid JSON/AST/match); `search search` filtered/unfiltered/empty/invalid at 80 and JSON; `search vsearch`/`query` invalid filters; all `--help` output; backfill notice with separated stdout/stderr; bracketed-key table renders; and a real MCP stdio session (`tools/list`, `metadata` default/filtered/invalid-filter/invalid-match/unknown-collection).
