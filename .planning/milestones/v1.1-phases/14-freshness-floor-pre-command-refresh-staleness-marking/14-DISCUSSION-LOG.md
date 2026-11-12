# Phase 14: Freshness Floor (Pre-Command Refresh + Staleness Marking) - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-11-08
**Phase:** 14-Freshness Floor (Pre-Command Refresh + Staleness Marking)
**Areas discussed:** Check scope & cadence, Over-cap behavior, Staleness signal mechanism, Marker presentation

---

## Check scope & cadence

| Option | Description | Selected |
|--------|-------------|----------|
| Search trio only | SC1's literal contract; check in CLI command layer so bench (calls searchers directly, bench.py:91) and MCP bypass by construction | ✓ |
| Search + get/multi-get | Also refresh before content reads; stat walk cost on every get | |
| All read commands | search/vsearch/query/get/ls/pull — maximal freshness, most of these don't benefit | |

**User's choice:** Search trio only
**Notes:** Placement in the CLI layer (not searchers/pipeline) is the load-bearing part — it keeps bench latency clean for Phase 16 and MCP unchanged.

| Option | Description | Selected |
|--------|-------------|----------|
| Every invocation | Stateless stat walk (~<50ms); simple, no watermark, clean = read-only lock-free | ✓ |
| Time-throttled watermark | Persisted last-check watermark, skip within N sec; adds state + a staleness window that defeats the "edited note, search, find it" case | |
| Setting-selectable mode | SIF_ setting picks always/throttled/off; two code paths to test and document | |

**User's choice:** Every invocation
**Notes:** —

| Option | Description | Selected |
|--------|-------------|----------|
| Always run | Overflow backstop (STACK #99); foreground/MCP watch hosts leave no PID file so detection is unreliable; clean = no-op walk; drift = flock wait-then-run | ✓ |
| Skip when daemon detected | Probe Phase 13 PID file; saves ~50ms but loses the backstop exactly when overflow can happen; can't see foreground/MCP hosts | |
| Run but never wait | Instant stale-pass on lock contention; silently returns stale results when waiting ~1s would land the burst | |

**User's choice:** Always run
**Notes:** —

| Option | Description | Selected |
|--------|-------------|----------|
| Searched collections | Sweep only what the search will query (-c/--all respected); cost ∝ searched scope; matches SC1 (fresh results, not global freshness) | ✓ |
| All collections | Every registered collection on every search; index converges globally but pays N walks when searching one | |

**User's choice:** Searched collections
**Notes:** —

## Over-cap behavior

| Option | Description | Selected |
|--------|-------------|----------|
| Skip refresh + warn | Count first (stat walk already knows); over cap → no refresh, search on stale index, prominent warning to run `sif index update`; avoids half-fresh ranking (research recipe verbatim) | ✓ |
| Partial refresh up to cap | Refresh N drifted files then warn; progresses toward fresh but mixes fresh/stale docs in one ranking | |
| Hard error | Refuse to search; breaks scripting/piping expectations | |

**User's choice:** Skip refresh + warn
**Notes:** —

| Option | Description | Selected |
|--------|-------------|----------|
| File count | SIF_ setting, e.g. SIF_SEARCH_REFRESH_MAX_FILES; deterministic and test-friendly (11-D08/D-09, 12-D15 culture); directly bounds parse/write work | ✓ |
| Time budget | Stop after N seconds; adapts to machine speed but nondeterministic in tests | |
| Count + time budget | Both knobs, whichever hits first; two knobs for marginal gain | |

**User's choice:** File count
**Notes:** Exact field name and default value deferred to Claude.

| Option | Description | Selected |
|--------|-------------|----------|
| stderr notice | One stderr line when refresh happened; stdout clean for --json piping; -q suppresses; over-cap warning also stderr | ✓ |
| Silent unless verbose | Refresh invisible unless --verbose; a multi-second refresh looks like a hang | |
| stdout notice | Breaks --json/--csv consumers | |

**User's choice:** stderr notice
**Notes:** —

## Staleness signal mechanism

| Option | Description | Selected |
|--------|-------------|----------|
| Derived at query | Stale = chunks-without-embeddings (true by construction via 12-D10 purge); SQL existence check in result assembly; no schema change; cannot drift from reality | ✓ |
| Explicit tracked column | embedded_at/vector_state column maintained by 4+ write paths; a missed path silently lies (the Phase 10.1 bug class) | |
| Column + reconcile | Tracked column as fast path reconciled by the derived check; both worlds' costs | |

**User's choice:** Derived at query
**Notes:** —

| Option | Description | Selected |
|--------|-------------|----------|
| All search surfaces | Shared result-assembly path marks search/query/MCP consistently; marker only fires on BM25-leg docs (vsearch can't return a vector-stale doc) | ✓ |
| Hybrid (query) only | Only where stale vectors skew fusion; two code paths, inconsistent signal | |
| BM25-depth collections | Depth is a watch-time choice, not a per-collection property; no reliable collection-level signal exists | |

**User's choice:** All search surfaces
**Notes:** —

| Option | Description | Selected |
|--------|-------------|----------|
| Results + status line | `sif status` gains one "Vector lag: N documents" line; same derived SQL; extends the Phase 13 Watch-section pattern | ✓ |
| Results only | Strict SC3; users must run a search to discover lag | |

**User's choice:** Results + status line
**Notes:** —

## Marker presentation

| Option | Description | Selected |
|--------|-------------|----------|
| Inline by title | Compact dim annotation next to the title; no new column (table width is tight); matches existing title-annotation pattern | ✓ |
| Dedicated column | Scannable but costs width on every search even when nothing is stale | |
| Footer summary only | Least noise but doesn't say WHICH results are stale (SC3 wants per-result) | |

**User's choice:** Inline by title
**Notes:** Exact glyph/wording deferred to Claude.

| Option | Description | Selected |
|--------|-------------|----------|
| Boolean field | e.g. `vectors_stale` on SearchResult.to_dict — CLI --json AND MCP query carry it automatically, one code path | ✓ |
| Staleness object | Nested `staleness: {...}` — extensible but speculative; no second staleness kind scheduled | |
| Inside scores dict | Zero new fields but semantically wrong (scores holds ranking numbers) | |

**User's choice:** Boolean field
**Notes:** Exact field name deferred to Claude.

| Option | Description | Selected |
|--------|-------------|----------|
| All formats | Table inline, JSON boolean, CSV column, Markdown annotation, XML attribute (10.1 sanitizer governs); SC3 is the floor; no format silently drops the signal | ✓ |
| Table + JSON only | Strict SC3 literal; --md (meant for reading) would hide what --json shows | |

**User's choice:** All formats
**Notes:** —

| Option | Description | Selected |
|--------|-------------|----------|
| stderr hint line | One line when ≥1 stale result (e.g. "run 'sif embed'"); -q suppresses; matches the over-cap remedy pattern | ✓ |
| Marker only | No path to the fix without reading docs | |
| First-time hint | Needs cross-invocation state a stateless CLI doesn't have | |

**User's choice:** stderr hint line
**Notes:** —

## Claude's Discretion

- SIF_ settings field names (max-files cap, enable/disable toggle) and cap default value
- Whether opt-out also gets a per-invocation flag (e.g. `--no-refresh`)
- Drift-detection helper placement/shape (indexing service vs CLI helper; FileScanner reuse short of checksums)
- Exact stderr notice/warning/hint wording; marker glyph/wording; exact JSON field name
- Staleness SQL shape (batched for the result set vs per-result) within the one-code-path contract
- Status-line wording/placement; refresh-burst lock-wait deadline; test scaffolding details

## Deferred Ideas

None — discussion stayed within phase scope.
