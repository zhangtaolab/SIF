# Phase 19: Search Correctness - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-11-15
**Phase:** 19-Search Correctness
**Areas discussed:** Per-chunk & result shape, Pagination surface, Frontmatter edit cost, Title ranking posture

---

## Per-chunk & result shape

| Option | Description | Selected |
|--------|-------------|----------|
| All chunk-capable surfaces | `--per-chunk` on `sif query` + `sif vsearch`; `per_chunk` on MCP `query` + `vec_search`. `search`/`lex_search` stay doc-level. | ✓ |
| CLI now, MCP in 22 | CLI flags now; MCP param deferred to Phase 22 parity work. | |
| vsearch only | Only `sif vsearch` gets the flag; hybrid stays strictly per-document. | |

**User's choice:** All chunk-capable surfaces.

| Option | Description | Selected |
|--------|-------------|----------|
| Show match count | Default row carries `chunk_matches` (table + JSON/MCP), from pre-dedup vector rows. | ✓ |
| Hidden by default | Clean one-row-per-document; collapsed chunks visible only via `--explain`. | |
| Machine-readable only | `chunk_matches` in JSON/MCP only, not the table. | |

**User's choice:** Show match count.

| Option | Description | Selected |
|--------|-------------|----------|
| Add chunk identity | `chunk_id` + `sequence` on `SearchResult`, shown as `path#sequence` in per-chunk/JSON/MCP. | ✓ |
| Snippet only | Per-chunk rows differ only by snippet; no schema change. | |
| Explain only | Chunk identity only in `--explain`. | |

**User's choice:** Add chunk identity.

**Notes:** The user asked for Chinese explanations of the trade-offs mid-discussion; recommendations were grounded in the current code (vector leg is chunk-level, `SearchResult` has no chunk fields today, MCP boundary re-maps fields one by one).

---

## Pagination surface

| Option | Description | Selected |
|--------|-------------|----------|
| All three commands | `--offset` on `sif search`, `sif vsearch`, `sif query`. | ✓ |
| query only | Offset only on the hybrid/pipeline command. | |
| query + search | Offset on the two doc-level commands; vsearch stays single-page. | |

**User's choice:** All three commands.

| Option | Description | Selected |
|--------|-------------|----------|
| All search tools | Offset on MCP `query` + `lex_search` + `vec_search`. | ✓ |
| query only | Offset only on the primary agent tool. | |
| query + lex | Offset on `query` + `lex_search`; vec waits for per-chunk surface. | |

**User's choice:** All search tools.

| Option | Description | Selected |
|--------|-------------|----------|
| Global ranks | Page 2 carries ranks 11–20 (`rank = offset + position`); JSON rank matches overall ordering. | ✓ |
| Per-page ranks | Every page restarts at rank 1. | |

**User's choice:** Global ranks.

**Notes:** Single offset owner (searchers rank from 0, hybrid slices once) is research-locked and was not re-litigated.

---

## Frontmatter edit cost

| Option | Description | Selected |
|--------|-------------|----------|
| Metadata fast path | Body unchanged + frontmatter changed → update title/metadata/mtime/checksum in place, keep chunks/embeddings. | ✓ |
| Full path always | Any checksum change purges chunks + embeddings and forces re-embed. | |

**User's choice:** Metadata fast path.

| Option | Description | Selected |
|--------|-------------|----------|
| All frontmatter | Hash = body + full frontmatter, canonical serialization (sorted keys, stable types). | ✓ |
| Title + tags | Hash only the fields search consumes today. | |
| Allowlist | Hash an explicit indexed-key allowlist kept in sync with Phase 20. | |

**User's choice:** All frontmatter.

| Option | Description | Selected |
|--------|-------------|----------|
| Auto on next index | Convention version in DB; next update/watch/MCP index pass prints one notice, runs one forced re-parse, clears marker after success; reuses the fast path so unchanged bodies are not re-embedded. | ✓ |
| Explicit --force | Detect and print a notice, but require `sif index update --force`. | |
| Auto and silent | Auto-run with no notice. | |

**User's choice:** Auto on next index.

**Notes:** Discussion surfaced that the current purge-on-change path would drop embeddings on every tag edit (staleness markers + vector recall loss under BM25-only watch), which is why the fast path was recommended. The migration must not be a plain `--force` (which would purge vectors corpus-wide); it re-parses and reuses the fast path.

---

## Title ranking posture

| Option | Description | Selected |
|--------|-------------|----------|
| Balanced title-forward | Title weight ~2–4× body band; bench selects the point; body relevance can still win. | ✓ |
| Title-first | Title dominates (5×+); known-item hits #1 but short common-word titles may bury long docs. | |
| Tie-breaker | Title is a small nudge (≤1.5×); may not move the bench. | |

**User's choice:** Balanced title-forward.

| Option | Description | Selected |
|--------|-------------|----------|
| Internal constant | Bench-pinned constant; no setting or CLI flag (DYM cutoff precedent). | ✓ |
| SIF_TITLE_WEIGHT setting | New setting with bench-pinned default. | |
| CLI --title-weight | New CLI flag plus setting. | |

**User's choice:** Internal constant.

| Option | Description | Selected |
|--------|-------------|----------|
| Strict per-leg | Title/known-item leg must improve AND body/hybrid held-out must not regress beyond the 0.01 tie rule. | ✓ |
| Aggregate win | Overall held-out nDCG improves; one leg may regress. | |
| Title leg only | Only the title leg is gated this phase. | |

**User's choice:** Strict per-leg.

**Notes:** H1 duplication in the body is accepted (Markdown body must stay byte-identical; external-content FTS cannot transform a column), and the column weight absorbs it. ZH lexical gains are not promised (FTS5 CJK tokenization, PITFALLS P5).

---

## Claude's Discretion

- Exact field names (`chunk_matches`, `chunk_id`, `sequence`), table column layout.
- Title column source: whether filename-stem fallback titles are indexed there.
- `--per-chunk` interaction with `--limit`/`--offset`; MCP per-chunk output shape.
- Offset validation (≥0; past-end → empty page, not an error).
- Migration interruption recovery details (marker retained, resumable).
- Metadata fast-path detection mechanics (stored body-hash comparison vs separate metadata hash column).
- Bench measurement procedure details, within the strict D-12 gate.
- YAML `---` fix mechanics and per-parser fixtures.
- Whether `file_size` is refreshed on update.
- Title-FTS migration gate and trigger SQL details.

## Deferred Ideas

None — discussion stayed within phase scope.
