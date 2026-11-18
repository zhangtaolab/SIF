# Phase 20: Metadata Filtering + Discovery - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-11-15
**Phase:** 20-Metadata Filtering + Discovery
**Mode:** `--auto` (fully autonomous — no AskUserQuestion prompts; every area auto-selected and the recommended option chosen, per `workflows/discuss-phase/modes/auto.md`)
**Areas discussed:** Filter surface coverage, Field space and collisions, Typed storage and migration, Vector-leg selectivity, AST semantics and typing, Discovery surface, Error surfaces and composition

---

## Filter surface coverage

| Option | Description | Selected |
|--------|-------------|----------|
| `query` only | Minimal surface; leaves BM25-only users without filters | |
| `search` + `query` | Skips the vector-only command | |
| All three result commands | `search`, `vsearch`, `query` share one flag and grammar, mirroring Phase 19 D-04's offset decision | ✓ |

**Choice:** `--filter <json>` on all three CLI commands; `filter` on all three MCP search inputs (`QueryInput`, `LexSearchInput`, `VecSearchInput`), mirroring D-05's offset precedent even though lex/vec registration lands in Phase 22.
**Notes:** Rationale is consistency with the immediately preceding phase — a user who learned `--offset` on three commands should not have to remember which command lacks `--filter`.

---

## Field space and collisions

| Option | Description | Selected |
|--------|-------------|----------|
| `path` + `mtime` reserved | Exactly what FILT-02 names; frontmatter keys of the same name are shadowed | ✓ |
| + `title` | Would expose filename-derived titles, but the roadmap names only path/mtime | |
| + `collection` | Duplicates the existing `--collection` parameter inside the grammar | |

**Choice:** Two reserved built-ins only. No `tags` alias, no `collection` AST field.
**Notes:** `DocumentMetadata.tags` exists in `src/sif/core/document.py` but is never populated by any parser (verified), so a `tag` built-in would have no backing data without inventing merge semantics across `tags`/`tag`/`keywords`.

---

## Typed storage and migration

| Option | Description | Selected |
|--------|-------------|----------|
| Python backfill from stored canonical JSON | Phase 19 already forced one full re-parse; `documents.metadata` is canonical JSON, so typed rows are derivable from the DB alone | ✓ |
| Second forced reindex | Re-parses every file again for data already in the DB | |

**Choice:** In-process Python backfill, marker-gated, resumable, zero cost on fresh/already-backfilled DBs. Non-indexable frontmatter skipped per key with a visible count rather than qmd's whole-document exclusion.
**Notes:** No JSON1 dependency is introduced — the project has none today and the backfill does not need one.

---

## Vector-leg selectivity

| Option | Description | Selected |
|--------|-------------|----------|
| Reuse the existing doubling loop + `_MAX_FETCH_K` | Phase 19's adaptive escalation already exists; filter selectivity seeds it | ✓ |
| Dedicated higher ceiling for filters | Doubles the work bound for one code path with no evidence it is needed | |
| No ceiling under filters | Violates the T-19-13 invariant that a query cannot request unbounded work | |

**Choice:** Pre-count drives the seed; `_MAX_FETCH_K = 2048` stays the independent ceiling; "too selective" is a one-line stderr warning with a precondition (matching docs ≥ page target AND ceiling exhausted), never an error.
**Notes:** Mirrors qmd's documented "best-effort top-K completeness" caveat rather than inventing a stricter contract than the parity target.

---

## AST semantics and typing

| Option | Description | Selected |
|--------|-------------|----------|
| qmd's 17 operators verbatim | One shared grammar with the parity target; no SIF-only operators | ✓ |
| qmd plus extensions (glob, regex) | Forks the grammar and weakens the "shared AST" claim | |

**Choice:** 17 operators + `caseInsensitive` ASCII folding. Ordering ops numeric-only; `mtime` accepts epoch or ISO-8601 at validation; explicit budgets (depth ≤ 8, nodes ≤ 64, string ≤ 1024 chars, array ≤ 128 elements).
**Notes:** Numeric-only ordering was chosen over lexicographic string ordering because a string `gt` is almost always a user mistake, and adding it later is purely additive.

---

## Discovery surface

| Option | Description | Selected |
|--------|-------------|----------|
| `sif collection metadata [NAME]` | qmd CLI parity; scopes naturally by collection | ✓ |
| Top-level `sif metadata` | Breaks parity; no collection scoping home | |
| Both | Two surfaces for one capability in the first release | |

**Choice:** `sif collection metadata [NAME]` (no NAME = all collections) with `--match`, `--min-count`, `--sort`, `--limit`, `--json`; MCP `metadata` tool with `{filter?, match?, min_count?, sort?, limit?}`. Deterministic ordering (count desc, key asc). Filter-aware coverage when `filter` is supplied.
**Notes:** The MCP schema is frozen as the Phase 22 contract (STATE.md cross-phase contract); discovery reads the same kv store the filters read (Pitfall 13 invariant).

---

## Error surfaces and composition

| Option | Description | Selected |
|--------|-------------|----------|
| `ClickException` + `isError=True` | User-input failure on both surfaces; the model can self-correct | ✓ |
| MCP `INVALID_PARAMS` protocol error | Breaks SEP-1303 self-correction and looks like a server fault | |

**Choice:** CLI names operator + field + AST path; MCP returns a tool execution error with the same message. Filter ANDs with collection, min_score, offset, per_chunk, and rerank; empty match returns an empty page, never "no filter".
**Notes:** Extends the existing exclude-all sentinel contract rather than creating a parallel one.

---

## Claude's Discretion

kv table shape and indexes; module layout (`core/filters.py` + `search/filters.py` recommended); pre-count merge/seeding rule; LIKE escaping and `prefix` index usability; discovery table layout and default limit; exact message wording; whether `search_chunks()` honors filters; property-test fixture design; rerank candidate-window interaction.

## Deferred Ideas

- Glob/regex path operator (PROJECT.md says "path prefix/glob"; glob is not in qmd's 17)
- `title` as a built-in filter field
- Saved filters / presets (already FILT-F1)
- `@file` convention for `--filter`
- Top-level `sif metadata` alias
