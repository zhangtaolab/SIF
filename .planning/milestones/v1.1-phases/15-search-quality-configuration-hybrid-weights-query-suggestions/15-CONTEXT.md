# Phase 15: Search Quality Configuration (Hybrid Weights + Query Suggestions) - Context

**Gathered:** 2026-11-08
**Status:** Ready for planning

<domain>
## Phase Boundary

The search-quality track opens — two coupled capabilities on the Phase 11 DB foundation (independent of the watch hosts):

1. **Hybrid weights configurable (QUAL-01)** — `rrf_k`, `bm25_weight`, `vector_weight` via `SIF_` settings AND per-query CLI flags / MCP query params; with no configuration, search behavior is byte-identical to today (k=60, equal weights).
2. **Did-you-mean + history suggestions (QUAL-02/03/04)** — zero-result searches display DYM built from indexed terms (every suggestion returns ≥1 hit; never silent rewrites); suggestions incorporate local query history (`query_log` with opt-out/clear); `sif suggest` returns prefix completions + DYM + history within 100 ms on a realistic personal-KB vocabulary.

NOT in scope: reranker tuning and bench/sweep (Phase 16 — per-query overrides are its sweep bridge), match-time fuzzy matching (rejected: index bloat), LLM in the DYM path (rejected: local zero-dep principle), spellfix1/symspellpy (v2+ fallbacks only), any watch-host work.

</domain>

<decisions>
## Implementation Decisions

### Hybrid weights (QUAL-01)
- **D-01:** **Weighted-sum RRF** — `fused(d) = w_bm25·1/(k+rank_bm25(d)) + w_vec·1/(k+rank_vec(d))`. Unconfigured (w=1.0, k=60) is byte-identical to today (SC1's literal bar); a missing source contributes 0 naturally, so absolute scores (and `min_score` semantics) stay stable — no normalization.
- **D-02:** **Flags on `sif query` + MCP query tool only** — hybrid fusion is the only place weights mean anything; `search` (pure BM25) and `vsearch` (pure vector) are single-source and get NO weight flags (a flag with no effect misleads tuners). — **Reversibility:** costly — the CLI surface, once shipped, is compatibility.
- **D-03:** **Naming/validation/channel** — CLI: `--rrf-k` (int, default 60, ≥1), `--bm25-weight` / `--vector-weight` (float, default 1.0, >0, NO upper bound — the Phase 16 sweep grid must not be artificially capped). Settings: `SIF_RRF_K` / `SIF_BM25_WEIGHT` / `SIF_VECTOR_WEIGHT`. Transport: NEW `rrf_k` / `bm25_weight` / `vector_weight` fields on `SearchOptions` (the one channel every searcher already receives; `RRFFusion` and `HybridSearcher` read them from options). Precedence: CLI flag > `SIF_` setting > default. MCP: same-named optional fields on the query request.
- **D-04:** **`SIF_` settings are the MCP default too** — the server process picks up the settings; request fields override per query. Symmetric with the CLI precedence structure (request field ≈ CLI flag).

### Did-you-mean (QUAL-02)
- **D-05:** **Zero-result trigger only** — all three search commands + MCP query display DYM when a query returns nothing; low-result does NOT trigger (noise + a threshold nobody tuned). SC2's letter is the zero case.
- **D-06:** **Term source = FTS5 vocab table** (`documents_fts_v`) — every vocab term exists in ≥1 indexed document by construction, so SC2's "every suggestion returns at least one hit" is structurally guaranteed (running the suggested term as a query hits). No new table, no sync maintenance (follows the index automatically), one SQL scan. — **Reversibility:** reversible.
- **D-07:** **Per-word replacement into a full query** — tokenize the query, find near-neighbors per word via `difflib.get_close_matches`, suggest the complete rewritten query (e.g. `quantum machin` → `quantum machine`); if every word is already in the vocab, no DYM (zero results had another cause — don't force a fake suggestion).

### query_log (QUAL-03)
- **D-08:** **Log executed searches only** — the three search commands log (query string, timestamp, result count, collections searched). `get`/`multi-get`/`suggest` do NOT log (suggest is the history consumer, not a producer); MCP queries do NOT log (assistant tool-queries would pollute personal history).
- **D-09:** **Cap at most-recent N** — default ~500 (exact default at Claude's discretion), `SIF_QUERY_HISTORY_LIMIT` adjustable; on insert overflow, delete oldest (trim-in-write). The table never grows unboundedly; no cleanup ritual needed.
- **D-10:** **Opt-out via setting; clear via `sif suggest --clear-history`** — `SIF_QUERY_HISTORY_ENABLED=0` disables both write AND read globally (suggest's history section is empty; DYM is unaffected — different source). Single clear entry point on `suggest` (where history is consumed). NO per-invocation `--no-log` flag.

### `sif suggest` (QUAL-04)
- **D-11:** **Three-section output** — prefix completions / did-you-mean / history, each section independently top-N; JSON mirrors the structure (three arrays). Source transparency: the user sees WHY each suggestion appears.
- **D-12:** **Table + `--json` only** — suggestions are an interactive aid; CSV/MD/XML add pure cost for a list nothing downstream consumes.
- **D-13:** **History ranking = frequency × recency** (count × time-decay via one aggregate SQL); cold start leaves the section empty.
- **D-14:** **100 ms budget: measure, don't pre-optimize** — implementation is one SQL vocab scan + per-word difflib over the loaded vocab + one history aggregate; CLI cold-start (~700 ms, measured in Phase 14 UAT) is NOT part of the budget. Verify by timing the core function in tests plus `--json` end-to-end minus startup baseline; optimize (vocab truncation, prefix narrowing) only if measurement says so.

### Carried forward (pre-decided — do not re-litigate)
- difflib for DYM; symspellpy/spellfix1 are v2+ fallbacks only (FUTR-01/03)
- Suggestions only — queries are NEVER silently rewritten (UX convention; Meilisearch/Typesense-consistent)
- Defaults byte-identical: k=60, equal weights (QUAL-01's compat bar)
- Zero new runtime dependencies (difflib is stdlib)
- Docs are generator-owned (`make docs-generate`; new settings/flags follow the SECTIONS allowlist pattern)
- stdout purity: notices/suggestions on search commands must not corrupt `--json`/`--csv` piping (Phase 14's stderr culture)
- Phase 16's `--sweep` consumes these per-query overrides as its grid bridge (roadmap-stated)

### Claude's Discretion
- Per-section top-N counts and the exact `SIF_QUERY_HISTORY_LIMIT` default
- Time-decay function shape for history ranking
- DYM closeness parameters (difflib n/cutoff) and vocab size handling for very large vocabularies
- `query_log` schema details (columns/types/indexes) — new table in schema.py
- MCP zero-result suggestions response field shape (principle fixed by D-05: MCP query carries them)
- Whether `--explain` gains a fusion-score breakdown (nice-to-have, not required by any SC)
- Prefix-completion matching details (case sensitivity, min prefix length)

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Milestone research
- `.planning/research/FEATURES.md` §table-stakes search-quality rows (hybrid weights; did-you-mean conventions — every suggestion returns results, never silent rewrites; suggestion sources) + §differentiators
- `.planning/research/PITFALLS.md` §search-quality pitfalls (held-out overfitting context — informs why defaults must not move without Phase 16 evidence)
- `.planning/research/STACK.md` — FTS5 vocab table availability (documents_fts_v) if covered; difflib stdlib

### Planning documents
- `.planning/REQUIREMENTS.md` — QUAL-01..QUAL-04 definitions; Out of Scope (match-time fuzzy, silent rewrites, LLM-in-DYM, spellfix1) ; FUTR-01..03 fallbacks
- `.planning/ROADMAP.md` §"Phase 15" — goal and success criteria 1–4; §"Phase 16" — the sweep-bridge dependency
- `.planning/phases/14-freshness-floor-pre-command-refresh-staleness-marking/14-CONTEXT.md` — stderr/stdout purity culture (D-07/D-13) and settings→docs generator pattern
- `.planning/PROJECT.md` §"Key Decisions" — coverage gate, deterministic-test culture

### Project conventions
- `CLAUDE.md` — quality gates (pytest fail_under=90, ruff, ty), CLI conventions, docs regeneration

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `RRFFusion` (`src/sif/search/rrf.py:8`) — `__init__(k=60)`, `fuse(results_lists, limit)`; gains per-list weights (constructor or fuse args) reading from options. Default path must stay byte-identical.
- `HybridSearcher` (`src/sif/search/hybrid.py`) — instantiates `RRFFusion(k=60)` at :39; `SearchPipeline` at :133 (query_cmd builds it at `search.py:777`).
- `SearchOptions` (`src/sif/core/models.py:246`) — the per-query transport; add `rrf_k` / `bm25_weight` / `vector_weight` fields (single channel — bench constructs options directly and gets the knobs for free, the Phase 16 bridge).
- Zero-result hook points — `search.py:448/601/833` ("No results found." prints) for the DYM display; MCP backend query path for its response field.
- Schema pattern (`src/sif/database/schema.py`) — new `query_log` table + repository follow the existing table/repository conventions.
- `--json` output helpers in the search commands — suggest's JSON mirrors the established dict shapes.

### Established Patterns
- Settings → docs via generator SECTIONS allowlist (`watch_*`/`search_refresh_*` precedents); env-var spellings in docs greps
- stderr notices via `console_err` (Phase 14's `_refresh_notice` culture) — DYM display on search commands goes where results went (stdout table context) but must not corrupt `--json` (JSON gains a suggestions key instead)
- Deterministic tests: real-DB tmp_path batteries, CliRunner stderr separation, no timing-race assertions (100 ms asserted on the core function with generous headroom)

### Integration Points
- `src/sif/search/rrf.py` + `hybrid.py` — weighted fusion
- `src/sif/core/models.py` `SearchOptions` — three new fields
- `src/sif/cli/commands/search.py` — query flags; zero-result DYM on all three commands; query_log write hook
- `src/sif/mcp/protocol.py` (QueryRequest ~:221-258) + `backend.py` — optional weight params; suggestions in the zero-result response
- `src/sif/database/schema.py` + `repositories.py` — query_log table + repository
- New `suggest` command module (`src/sif/cli/commands/suggest.py` — structural analogs: `context.py`/`watch.py`); `cli/main.py` registration
- `scripts/generate_config_ref.py` SECTIONS + `make docs-generate`
- `pyproject.toml` — no dependency changes

</code_context>

<specifics>
## Specific Ideas

No external references — decisions are self-contained. Construction notes for the planner:

- **SC1's byte-identical bar is testable**: a golden test asserting fused scores/rankings with default options equal today's output on a fixture corpus (the Phase 11 SC3 golden-equivalence culture).
- **SC2's "every suggestion ≥1 hit"** is guaranteed by construction via the vocab table (D-06) — pin it with a test that runs each emitted suggestion as a real query and asserts ≥1 result.
- **The 100 ms budget excludes CLI cold start** (~700 ms measured in Phase 14's UAT) — assert on the core suggest function directly; a full `--json` end-to-end minus startup baseline is the manual sanity check.
- **query_cmd's SearchPipeline sits inside a try/except (the WR-02 open finding from Phase 14's review)** — the weight plumbing touches this area; do not widen that pre-existing defect, but don't block on it either (it's tracked in the disposition ledger).

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 15-Search Quality Configuration (Hybrid Weights + Query Suggestions)*
*Context gathered: 2026-11-08*
