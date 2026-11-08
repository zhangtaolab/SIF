# Phase 15: Search Quality Configuration (Hybrid Weights + Query Suggestions) - Research

**Researched:** 2026-11-08
**Domain:** Hybrid RRF weight plumbing (CLI/MCP/settings) + did-you-mean/suggestion engine on FTS5 vocabulary + query history
**Confidence:** HIGH (code anchors Read this session; load-bearing behavior verified by local experiments on SQLite 3.51.0; costs measured, not estimated)

## Summary

Phase 15 wires three existing seams and adds one new engine. The weight seam is small and surgical: `SearchOptions` (core/models.py:246-261) gains `rrf_k`/`bm25_weight`/`vector_weight`, `HybridSearcher.search` (hybrid.py:74) passes them into `RRFFusion.fuse`, and three construction sites fill them from CLI flags / `SIF_` settings / MCP request fields. The critical compat fact, **verified by float-repr-exact experiment**: a weighted-sum fuse in multiply form (`weight * (1.0 / (k + rank))`) with `w=1.0` is bit-identical to today's `1.0 / (self.k + rank)`, while the *existing* `RRFFusion.fuse_with_weights` **normalizes weights** (`w / total`) and would halve every score at defaults — it must NOT carry the default path (it is dead code today: zero call sites in src and tests).

The suggestion engine rests on a verified structural fact with one sharp edge: `documents_fts` uses `tokenize='porter'` (schema.py:225, 235), so the FTS5 vocab table (`fts5vocab` row mode: columns `term, doc, cnt`, one row per distinct term) contains **porter STEMS, not surface words** — "machine"→`machin`, "studies"→`studi`, "are"→`ar`. Both stem and surface forms MATCH identically through SIF's quoted-prefix query form (`"tok"*`), so SC2's "every suggestion returns ≥1 hit" holds whether suggestions display stems or surface forms; but DYM/prefix suggestions built purely from the vocab will *display* stems. Measured at 73k terms (this machine): vocab SQL scan ≈26 ms, full-vocab `difflib.get_close_matches` ≈46 ms/word (too slow for multi-word queries under the 100 ms core budget), first-letter±1 bucketing ≈11 ms/word, bisect prefix completion ≈free. D-14's "measure, don't pre-optimize" has now been measured: a narrowing prefilter is justified at realistic vocab scale.

`query_log` is a conventional new table + repository following the ContextRepository/LLMCacheRepository pattern, and per the Phase 11 lock contract (11-RESEARCH D-01) its writes are exactly the "short CRUD outside the flock" class that `busy_timeout` + `BEGIN IMMEDIATE` already arbitrate. The known landmine in the weight-plumbing area (WR-02: `query_cmd`'s `SearchPipeline` construction at search.py:777-784 sits outside the `try` → RuntimeError traceback without sqlite-vec) is documented verbatim below so the plan can route around it without widening it.

**Primary recommendation:** Extend `RRFFusion.fuse()` with optional `weights`/`k` parameters (multiply form; `None` defaults preserve today's arithmetic byte-for-byte), route `SearchOptions` → `HybridSearcher.search` → fuse, add a `src/sif/search/suggest.py` engine (vocab scan + bucketed difflib + history aggregate) shared by the three zero-result hooks, `sif suggest`, and the MCP `query` tool, and create the vocab table via `CREATE VIRTUAL TABLE IF NOT EXISTS documents_fts_v USING fts5vocab(documents_fts, 'row')` in `SchemaManager._create_fts_tables` plus a lazy ensure in the engine.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Hybrid weights (QUAL-01)**
- **D-01:** **Weighted-sum RRF** — `fused(d) = w_bm25·1/(k+rank_bm25(d)) + w_vec·1/(k+rank_vec(d))`. Unconfigured (w=1.0, k=60) is byte-identical to today (SC1's literal bar); a missing source contributes 0 naturally, so absolute scores (and `min_score` semantics) stay stable — no normalization.
- **D-02:** **Flags on `sif query` + MCP query tool only** — hybrid fusion is the only place weights mean anything; `search` (pure BM25) and `vsearch` (pure vector) are single-source and get NO weight flags (a flag with no effect misleads tuners). — **Reversibility:** costly — the CLI surface, once shipped, is compatibility.
- **D-03:** **Naming/validation/channel** — CLI: `--rrf-k` (int, default 60, ≥1), `--bm25-weight` / `--vector-weight` (float, default 1.0, >0, NO upper bound — the Phase 16 sweep grid must not be artificially capped). Settings: `SIF_RRF_K` / `SIF_BM25_WEIGHT` / `SIF_VECTOR_WEIGHT`. Transport: NEW `rrf_k` / `bm25_weight` / `vector_weight` fields on `SearchOptions` (the one channel every searcher already receives; `RRFFusion` and `HybridSearcher` read them from options). Precedence: CLI flag > `SIF_` setting > default. MCP: same-named optional fields on the query request.
- **D-04:** **`SIF_` settings are the MCP default too** — the server process picks up the settings; request fields override per query. Symmetric with the CLI precedence structure (request field ≈ CLI flag).

**Did-you-mean (QUAL-02)**
- **D-05:** **Zero-result trigger only** — all three search commands + MCP query display DYM when a query returns nothing; low-result does NOT trigger (noise + a threshold nobody tuned). SC2's letter is the zero case.
- **D-06:** **Term source = FTS5 vocab table** (`documents_fts_v`) — every vocab term exists in ≥1 indexed document by construction, so SC2's "every suggestion returns at least one hit" is structurally guaranteed (running the suggested term as a query hits). No new table, no sync maintenance (follows the index automatically), one SQL scan. — **Reversibility:** reversible.
- **D-07:** **Per-word replacement into a full query** — tokenize the query, find near-neighbors per word via `difflib.get_close_matches`, suggest the complete rewritten query (e.g. `quantum machin` → `quantum machine`); if every word is already in the vocab, no DYM (zero results had another cause — don't force a fake suggestion).

**query_log (QUAL-03)**
- **D-08:** **Log executed searches only** — the three search commands log (query string, timestamp, result count, collections searched). `get`/`multi-get`/`suggest` do NOT log (suggest is the history consumer, not a producer); MCP queries do NOT log (assistant tool-queries would pollute personal history).
- **D-09:** **Cap at most-recent N** — default ~500 (exact default at Claude's discretion), `SIF_QUERY_HISTORY_LIMIT` adjustable; on insert overflow, delete oldest (trim-in-write). The table never grows unboundedly; no cleanup ritual needed.
- **D-10:** **Opt-out via setting; clear via `sif suggest --clear-history`** — `SIF_QUERY_HISTORY_ENABLED=0` disables both write AND read globally (suggest's history section is empty; DYM is unaffected — different source). Single clear entry point on `suggest` (where history is consumed). NO per-invocation `--no-log` flag.

**`sif suggest` (QUAL-04)**
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

### Deferred Ideas (OUT OF SCOPE)
None — discussion stayed within phase scope.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description (REQUIREMENTS.md) | Research Support |
|----|-------------------------------|------------------|
| QUAL-01 | `rrf_k`/`bm25_weight`/`vector_weight` via `SIF_` settings + per-query params; defaults byte-identical (k=60 equal weights) | Weighted-fuse float-exactness experiment (E1); `SearchOptions`/`HybridSearcher`/`fuse` anchor map; CLI-flag-default-None precedence pattern; MCP `QueryInput`/backend/handler extension points; golden-test strategy |
| QUAL-02 | Zero/low-result "Did you mean" suggestions (vocab + history, suggest-only, never silent rewrites) | Zero-result hook anchors (search.py:448/601/833); vocab table mechanics + porter-stem reality; per-word replacement algorithm; ≥1-hit structural guarantee + pin-test design |
| QUAL-03 | Query-history-based suggestions (query_log local storage) | query_log schema/repository/lock-contract analysis; trim-in-write; opt-out/clear wiring; frequency×recency ranking SQL |
| QUAL-04 | `sif suggest` command (prefix completion + DYM + history) | Measured cost model (26 ms scan / 46→11 ms per-word with bucketing / free bisect prefix); command-module precedents; `--json` three-array shape; 100 ms core-function test design |
</phase_requirements>

## Project Constraints (from CLAUDE.md)

- Quality gates: `ruff check src tests`, `ruff format --check src tests`, `pytest` (coverage `fail_under=90`, verified pyproject.toml:203-211) — full suite after every plan completes.
- `ty check src/sif`; new code fully type-annotated (functions take and return typed values).
- Python 3.10+: `list[str] | None` union syntax; line length 100; max complexity (mccabe) 10; ruff isort `combine-as-imports = true`; stdlib → third-party → `sif` import order; two blank lines after imports.
- CLI commands raise `click.ClickException(str(e))` for user-facing errors.
- Transactions via `Database.transaction()` with automatic rollback on exception.
- Module loggers: `logger = get_logger(__name__)` (stderr).
- Click decorators stay as-is (no decorator typing relaxations).
- docs/cli-reference.md and docs/configuration.md are generator-owned (`make docs-generate`) — never hand-edit; new settings must be registered in `scripts/generate_config_ref.py` SECTIONS.
- Environment quirk (project memory): UNSET `FORCE_COLOR` (`env -u FORCE_COLOR`) and set `NO_COLOR=1` when running pytest in agent shells — "0" does not work; tests fail spuriously otherwise.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Weight default values / validation | Settings (config/settings.py) | — | Pydantic Settings is the one `SIF_` surface; validators fail at settings-construction time naming the field (watch_update_depth precedent) |
| Weight per-query transport | Domain models (SearchOptions) | — | D-03: the one channel every searcher already receives; bench constructs options directly and gets the knobs free (Phase 16 bridge) |
| Weighted fusion arithmetic | Search core (rrf.py + hybrid.py) | — | `RRFFusion` owns the formula; `HybridSearcher` owns the source-list assembly; CLI/MCP never touch fusion |
| Weight CLI flags | CLI (search.py query_cmd only) | — | D-02: only `sif query` fuses; flags default None so settings precedence works |
| Weight MCP params | MCP protocol/backend/handlers | — | `QueryInput` fields → `hybrid_search` kwargs → options; settings fill defaults server-side (D-04) |
| DYM computation | Search core (new suggest engine) | Database (vocab read) | One pure-ish engine, three hosts (zero-result hooks, suggest cmd, MCP backend) — LiveIndexService precedent |
| Vocabulary source | Database (FTS5 vocab shadow table) | — | Derived view over the index; zero sync maintenance; must be CREATEd (not auto-created) |
| query_log persistence | Database (schema + repository) | — | Repository pattern per CLAUDE.md; short CRUD outside the flock per Phase 11 D-01 |
| History ranking | Search core (suggest engine) | Database (aggregate SQL) | D-13: one GROUP BY aggregate; decay applied in Python |
| `sif suggest` UX | CLI (new command module) | — | Registered top-level in main.py; table + --json only (D-12) |
| Docs for new settings | Generator (generate_config_ref.py) | Makefile | SECTIONS allowlist + `make docs-generate`; env-var spellings in doc-gate greps |

## Standard Stack

**Zero new runtime dependencies.** Everything is stdlib (`difflib`, `sqlite3`, `bisect`) plus existing code. pyproject.toml dependency sections are untouched by this phase.

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| stdlib `difflib` | Python 3.10+ | near-match per query word | D-locked (carried forward); signature `difflib.get_close_matches(word, possibilities, n=3, cutoff=0.6)` [CITED: docs.python.org/3/library/difflib.html — verbatim signature; ratio = `2.0*M/T`] |
| SQLite `fts5vocab` | SQLite ≥3.34-era FTS5 (3.51.0 verified locally) | vocabulary enumeration (`term, doc, cnt`) | D-06; verified locally this session on SQLite 3.51.0 with SIF's exact DDL |
| stdlib `bisect` | Python 3.10+ | prefix completion over sorted vocab | Measured ≈0.001 ms/word — no SQL LIKE needed |
| Pydantic Settings (existing) | existing | `SIF_RRF_K` / `SIF_BM25_WEIGHT` / `SIF_VECTOR_WEIGHT` / `SIF_QUERY_HISTORY_*` | Milestone STACK.md: all v1.1 tunables are plain Settings fields |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| difflib DYM | symspellpy / spellfix1 | Rejected (FUTR-01/03, v2+ only): spellfix1 not in CPython's bundled sqlite (verified in milestone STACK research); symspellpy is a new runtime dep |
| Full-vocab difflib scan | first-letter±1 bucket prefilter | Full scan = 46.3 ms/word at 73k terms (measured) — a 3-word zero-result query ≈140 ms exceeds SC4's core budget; bucket = 10.9 ms/word with slightly lower recall on first-letter typos (see Pitfall 2) |
| Python-side history decay | pure-SQL decay expression | Pure SQL decay is awkward (julianday exponent math); ≤500 distinct rows make Python decay trivial — D-13's "one aggregate SQL" is satisfied by the GROUP BY |

**Installation:** none (`pip install -e ".[dev]"` already covers everything).

## Package Legitimacy Audit

No external packages are installed or recommended by this phase. All functionality is stdlib (`difflib`, `bisect`) or existing project code. **Packages removed due to [SLOP]:** none. **Packages flagged [SUS]:** none. (symspellpy remains explicitly out of scope per FUTR-03.)

## Architecture Patterns

### System Architecture Diagram

```
                         ┌────────────────────────────────────────────────────────┐
                         │  weight configuration surface (QUAL-01)                │
                         │                                                        │
  SIF_RRF_K /            │   CLI flags (query only)      MCP QueryInput fields    │
  SIF_BM25_WEIGHT / ───► │   --rrf-k/--bm25-weight/      rrf_k/bm25_weight/       │
  SIF_VECTOR_WEIGHT      │   --vector-weight (default    vector_weight (optional) │
  (Pydantic Settings)    │   None → settings → default)  (None → server settings) │
                         └──────────────┬───────────────────────┬─────────────────┘
                                        │ precedence:           │
                                        │ flag > SIF_ > default │
                                        ▼                       ▼
                              SearchOptions.rrf_k /    backend.hybrid_search()
                              bm25_weight /             (mcp/backend.py:73)
                              vector_weight  ─────────────────┐
                                        │                     │
                                        ▼                     ▼
                             HybridSearcher.search ──► SearchPipeline.search
                             (hybrid.py:74 fuse           (hybrid.py:228 second
                              [bm25, vector] with          fuse for expansion
                              weights from options)        variants — k only)
                                        │
                                        ▼
                             RRFFusion.fuse(lists, limit,
                                            weights?, k?)   ◄─ multiply form;
                                                              None defaults =
                                                              today's arithmetic

                         ┌────────────────────────────────────────────────────────┐
                         │  suggestion engine (QUAL-02/03/04)                      │
                         │                                                        │
  zero-result query ───► │  search/vsearch/query "No results found." (448/601/833)│
  (CLI table mode)       │        │                                               │
  zero-result query ───► │  --json mode: results + suggestions key                 │
  zero-result query ───► │  MCP query tool: QueryOutput.suggestions                │
  partial query ───────► │  sif suggest QUERY (prefix + DYM + history, --json)     │
                         └──────────────┬─────────────────────────────────────────┘
                                        ▼
                    suggest engine (new src/sif/search/suggest.py)
                    ├── vocab: SELECT term, doc FROM documents_fts_v
                    │   (fts5vocab row mode; porter STEMS; created via
                    │    CREATE VIRTUAL TABLE IF NOT EXISTS in SchemaManager
                    │    + lazy ensure for old DBs)
                    ├── DYM: per-word difflib.get_close_matches over
                    │   first-letter±1 bucket (46→11 ms/word measured)
                    ├── prefix: bisect over sorted vocab
                    └── history: query_log GROUP BY (count, MAX(created_at))
                                  → frequency × time-decay in Python
                                        ▲
                    query_log writes: search/vsearch/query only (D-08),
                    INSERT + trim-in-write DELETE in one short transaction
                    (outside the flock — Phase 11 D-01 short-CRUD class)
```

### Recommended Project Structure (additions only)

```
src/sif/
├── search/
│   ├── rrf.py            # fuse() gains optional weights/k params (multiply form)
│   ├── hybrid.py         # HybridSearcher reads options → fuse call
│   └── suggest.py        # NEW: SuggestionEngine (vocab + DYM + history core)
├── core/models.py        # SearchOptions += rrf_k/bm25_weight/vector_weight
├── database/
│   ├── schema.py         # _create_fts_tables += documents_fts_v; _create_query_log_table
│   │                     # drop_all += query_log (+ documents_fts_v)
│   └── repositories.py   # NEW QueryLogRepository
├── config/settings.py    # rrf_k, bm25_weight, vector_weight, query_history_*
├── cli/commands/
│   ├── search.py         # query flags; zero-result DYM on all three; query_log hook
│   └── suggest.py        # NEW: suggest command (--json, --clear-history)
├── cli/main.py           # cli.add_command(suggest_cmd)
└── mcp/
    ├── protocol.py       # QueryInput += weight fields; QueryOutput += suggestions
    ├── backend.py        # hybrid_search passes weights; zero-result DYM pass
    └── handlers.py       # input_schema += weight properties (hand-written JSON schema)
```

### Pattern 1: Weighted fuse that is float-exact at defaults

**What:** extend `RRFFusion.fuse()` (rrf.py:20-91) with optional `weights: list[float] | None = None` (and optionally `k: int | None = None`); score line becomes `rrf_score = weight * (1.0 / (self.k + rank))` with `weight = 1.0` when `weights is None`.
**When to use:** every fusion call.
**Why multiply form:** verified by experiment (E1, this session) — `weight * (1.0 / (k + rank))` with `weight == 1.0` produces **repr-exact identical floats** to today's `1.0 / (self.k + rank)` over random 30+30-element inputs, because IEEE-754 `1.0 * x == x` exactly and the accumulation order is unchanged.

```python
# Source: experiment E1 (/tmp/sif15_research/measure2.py, SQLite 3.51.0 / py3.13, this session)
def fuse_weighted(results_lists, weights, k=60, limit=10):
    scores = {}
    for results, w in zip(results_lists, weights, strict=True):
        for rank, result in enumerate(results, 1):
            s = w * (1.0 / (k + rank))
            scores[result.document_id] = scores.get(result.document_id, 0.0) + s
    ...
# fuse_unweighted == fuse_weighted([...], [1.0, 1.0])  -> True (repr-exact)
# fuse_unweighted vs normalized [0.5, 0.5]            -> exactly HALF (normalization breaks SC1)
```

**Do NOT reuse `fuse_with_weights`** (rrf.py:93-175): it normalizes — `normalized_weights = [w / total_weight for w in weights]` (rrf.py:113-114) — so at defaults (1.0, 1.0) it produces exactly half of today's scores (experiment E2), violating SC1. It also has zero call sites in src and tests today (grep-verified) — repurpose or delete per planner preference, but the default path must not route through it.

### Pattern 2: Weights ride `SearchOptions`; readers pull, not push

`SearchOptions` (core/models.py:246-261) currently ends:

```python
# Source: src/sif/core/models.py:249-261 (Read this session)
    limit: int = 10
    offset: int = 0
    # Sentinel contract: None = no collection filter (unfiltered, incl. --all);
    # [] = exclude-all — every collection excluded, searchers return zero results.
    collection_ids: list[str] | None = None
    min_score: float = 0.0
    include_content: bool = False
    include_highlights: bool = True
    max_highlights: int = 3
    explain: bool = False
    candidate_limit: int = 20
    intent: str | None = None
    snippet_max_length: int = 300
```

Add `rrf_k: int = 60`, `bm25_weight: float = 1.0`, `vector_weight: float = 1.0` — defaults equal today's hardcoded behavior, so every existing construction site (bench.py:94, search.py:377/558/701, backend.py:83) stays byte-identical with zero edits. `HybridSearcher.search` passes them at its fuse call (hybrid.py:74):

```python
# Current (hybrid.py:74, Read this session):
        fused_results = self.rrf.fuse([bm25_results, vector_results], options.limit)
# Becomes conceptually:
        fused_results = self.rrf.fuse(
            [bm25_results, vector_results],
            options.limit,
            weights=[options.bm25_weight, options.vector_weight],
            k=options.rrf_k,
        )
```

k-passing alternatives (planner picks one): (a) `fuse(..., k=None)` parameter falling back to `self.k` — least state mutation, most testable (recommended); (b) mutate `self.rrf.k` from options at search() entry — works because MCP backend constructs the pipeline per query (backend.py:95) and the CLI constructs it per invocation, but mutates shared state.

### Pattern 3: CLI flag precedence — Click default MUST be None

For `flag > SIF_ setting > default` to work, the Click option default must be `None`, not the literal default:

```python
@click.option("--rrf-k", type=int, default=None, help="RRF k constant (default: SIF_RRF_K or 60)")
@click.option("--bm25-weight", type=float, default=None, help="BM25 fusion weight (default: SIF_BM25_WEIGHT or 1.0)")
@click.option("--vector-weight", type=float, default=None, help="Vector fusion weight (default: SIF_VECTOR_WEIGHT or 1.0)")
...
    settings = get_settings()  # query_cmd already loads settings at search.py:741
    options = SearchOptions(
        ...,
        rrf_k=rrf_k if rrf_k is not None else settings.rrf_k,
        bm25_weight=bm25_weight if bm25_weight is not None else settings.bm25_weight,
        vector_weight=vector_weight if vector_weight is not None else settings.vector_weight,
    )
```

Validation split: `type=click.IntRange(1, None)` / positive-float check at the flag (D-03: ≥1 for k, >0 for weights, no upper bound); Pydantic `ge`/`gt` constraints on the Settings fields (naming-the-field errors, watch_update_depth validator precedent at settings.py:216-230). `query_cmd` already has its settings touchpoint with a clean ValidationError → ClickException conversion (search.py:740-745) — extend it, don't add a new one.

### Pattern 4: The vocab table — creation, shape, cost

The fts5vocab table is **not auto-created**; nothing in SIF creates it today (grep-verified: no `fts5vocab` anywhere in src). Create it in `SchemaManager._create_fts_tables` (schema.py:194) so every `db.init_schema()` caller gets it, plus a lazy `CREATE VIRTUAL TABLE IF NOT EXISTS` ensure inside the suggest engine (old DBs opened by the MCP backend's `DatabaseConnection.transaction()` never run init_schema):

```sql
-- Verified locally this session (SQLite 3.51.0, SIF's exact DDL):
CREATE VIRTUAL TABLE IF NOT EXISTS documents_fts_v USING fts5vocab(documents_fts, 'row');
-- idempotent (ran twice, no error); row mode = ONE ROW PER DISTINCT TERM:
--   term TEXT, doc INTEGER (= number of docs containing term), cnt INTEGER (total occurrences)
SELECT term, doc FROM documents_fts_v;   -- ≈26 ms at 73k terms (measured)
```

Verified constraints: the vocab table **must live in the main schema** — a temp-schema vocab cannot reference a main-schema FTS table (both `fts5vocab(documents_fts, 'row')` and `fts5vocab(main.documents_fts, 'row')` in temp fail: `no such fts5 table`), so a write is required once per DB. Also add `documents_fts_v` and `query_log` to `drop_all` (schema.py:384-395) for test isolation.

**Porter reality (empirically verified):** with `tokenize='porter'`, vocab terms are stems — for input "The machines are learning quickly; running studies show..." the vocab contained `machin, ar, learn, run, studi, happili, contextu` [VERIFIED: local experiment A2]. Both stem and surface query forms MATCH identically through `_build_fts_query` (bm25.py:160-176), which quotes every token as a prefix phrase `f'"{cleaned}"*'` (bm25.py:21-33): `"machin"*`, `"machine"*`, `"machines"*` all hit (experiment A4).

### Pattern 5: DYM engine (per-word replacement, D-07)

One engine, three hosts — mirror the LiveIndexService "one core, many hosts" precedent:

```python
# Sketch (costs are measured on 73k-term vocab, this machine, this session)
class SuggestionEngine:
    def __init__(self, conn): ...            # ensure vocab table; load terms lazily
    # _load(): SELECT term, doc FROM documents_fts_v  (~26 ms / 73k terms)
    #   -> self._terms (sorted, for bisect), self._term_set, self._df (term -> doc count)

    def did_you_mean(self, query: str, n: int = 3) -> list[str]:
        # tokenize like the searchers do: query.split() + _FTS_METACHARS strip (bm25.py:18)
        # for each token NOT in self._term_set (lowered):
        #   bucket = [t for t in terms if abs(ord(t[0]) - ord(tok[0])) <= 1]   # 46 -> 11 ms/word
        #   difflib.get_close_matches(tok, bucket, n=n, cutoff=0.75)
        # if NO token was out-of-vocab, or no close matches: return []   (D-07)
        # else: return full rewritten queries (in-vocab tokens kept as typed)
```

Design notes:
- **In-vocab membership must compare against STEMS.** A raw user word "machines" is not in the vocab (`machin` is). Since `"machines"*` already MATCHES (A4), an inflected-but-correct word must NOT trigger DYM. Cheapest correct test: the token's own stem is in the set — but SIF has no Python porter stemmer; the pragmatic approximation is prefix-tolerant membership (any vocab term starts with the token, or the token starts with a vocab term — bisect range check, ~free) or accept slight over-triggering (a word whose prefix hits nothing is the true zero-result cause anyway). Flag for planner: the exact in-vocab predicate determines DYM noise.
- **cutoff 0.75 over the default 0.6** — 0.6 is difflib's generic default [CITED: docs.python.org]; typo correction wants higher precision (discretion per CONTEXT).
- **Display gap:** suggestions built from the vocab display STEMS ("quantum machin", not "quantum machine"). D-07's illustrative example implies surface forms, but the vocab cannot produce them without a corpus rescan or a new mapping table (both violate D-06's no-new-maintenance spirit). Recommendation: display the stem; keep tokens the user typed when they already match. This is a real UX trade-off the plan should state explicitly (see Open Questions (RESOLVED) — stem display ships, per 15-02 flagged_assumptions).
- **≥1-hit pin test (SC2):** for every emitted suggestion, run `BM25Searcher.search(suggestion, SearchOptions(limit=1))` and assert non-empty — structurally guaranteed because each suggested term came from the vocab and `"stem"*` matches its contributing doc(s) (A4).

### Pattern 6: query_log — schema, repository, write hook

Follow the repository conventions (repositories.py:381 ContextRepository / :518 LLMCacheRepository — ctor takes `sqlite3.Connection`; `create/get/list/delete` + `_row_to_X`; ids are `str(uuid.uuid4())` default_factory, models.py:44). Suggested schema (details are Claude's discretion per CONTEXT):

```sql
CREATE TABLE IF NOT EXISTS query_log (
    id TEXT PRIMARY KEY,
    query TEXT NOT NULL,
    result_count INTEGER NOT NULL DEFAULT 0,
    collections TEXT NOT NULL DEFAULT '[]',   -- JSON array of names, repo convention (collections.ignore_patterns precedent)
    created_at TEXT NOT NULL                  -- datetime.now(timezone.utc).isoformat()
);
CREATE INDEX IF NOT EXISTS idx_query_log_created ON query_log(created_at DESC);
```

- **Timestamps: aware UTC** — do NOT copy the LLM-cache naive-local-time pattern (open finding WR-03 in Phase 14's ledger).
- **Trim-in-write (D-09):** INSERT then `DELETE FROM query_log WHERE id NOT IN (SELECT id FROM query_log ORDER BY created_at DESC LIMIT ?)` in the same short transaction. Default limit 500 (`SIF_QUERY_HISTORY_LIMIT`, ge=1).
- **Lock contract:** Phase 11 D-01 — "Short CRUD writers (collection add/remove, context writes) stay OUTSIDE the lock — `busy_timeout` + `BEGIN IMMEDIATE` handles them" [VERIFIED: .planning/phases/11-live-index-foundation-concurrent-db-incremental-core/11-RESEARCH.md D-01]. A query_log INSERT+trim is exactly this class; **no flock**. The WAL/busy_timeout/implicit-BEGIN-IMMEDIATE recipe is armed per connection in `create_connection` (factory.py:60-103).
- **Write hook placement:** in each of the three commands, after `results` is obtained, still inside the `with db.connection:` block (search.py:401/582/776); guarded `try/except` + `logger.warning` so a history failure NEVER breaks search (mirrors `_pre_search_refresh`'s D-05 fail-soft); skipped entirely when `SIF_QUERY_HISTORY_ENABLED=0`. `search_cmd` has no settings object in scope today — the hook needs its own best-effort `get_settings()` (the `_pre_search_refresh` try/except-settings precedent, search.py:166-175).
- **History ranking (D-13):** one aggregate SQL — `SELECT query, COUNT(*) AS n, MAX(created_at) AS last FROM query_log GROUP BY query` (≤500 distinct rows, trivial cost) — then decay in Python: `score = n * exp(-ln(2) * age_days / half_life)` with half_life ≈14 days (discretion). Cold start = empty table = empty section (D-13).
- **`sif suggest --clear-history` (D-10):** `DELETE FROM query_log` + confirmation print; `--clear-history` and a QUERY argument should be mutually exclusive (click error) or clear-then-exit.

### Pattern 7: `sif suggest` command shape

Top-level command (like `watch_cmd`/`pull_cmd`), registered in main.py's import+add_command block (main.py:87-108):

```
sif suggest QUERY [--limit N] [--json] [-q]
sif suggest --clear-history
```

- Table mode: three labeled sections (prefix completions / did you mean / history), each independently top-N (D-11); source transparency is the section labels.
- `--json` (D-12: table + json ONLY): `{"completions": [...], "did_you_mean": [...], "history": [...]}` — three arrays (D-11).
- Index-missing guard mirrors the search commands (`if not index_path.exists(): ... return`).
- **100 ms budget (D-14/SC4):** assert on the engine's core function (`time.perf_counter` around a suggest call on a fixture vocab, generous headroom — the measured full pipeline is ≈26 ms scan + ≈11 ms/word bucketed + ≈1 ms history at 73k terms); CLI cold start (~700 ms, Phase 14 UAT) is excluded. Manual sanity: `--json` end-to-end minus startup baseline. No timing-race assertions on wall-clock CLI.

### Pattern 8: MCP extension surface

Three coordinated edits (the boundary has hand-written JSON schema AND pydantic models — both must change):

1. `QueryInput` (protocol.py:238-244) += `rrf_k: int | None`, `bm25_weight: float | None`, `vector_weight: float | None` (None = use server settings, D-04).
2. `QueryToolHandler.input_schema` (handlers.py:53-62) += the three properties in the hand-written dict — forgetting this hides the params from MCP tool discovery while the model still accepts them.
3. `backend.hybrid_search` (backend.py:73-123): extend the signature, fill the option fields — `None` falls back to `self.settings` (backend already holds settings, backend.py:44, satisfying D-04 with zero new machinery). Validate ranges here or let Pydantic (add `ge`/`gt` on QueryInput fields).

Zero-result suggestions on MCP: `QueryOutput` (protocol.py:247-250, currently `results: list[SearchResult]` only) gains e.g. `suggestions: list[str] = Field(default_factory=list)`. `hybrid_search` currently returns `list[SearchResult]`; on the zero-result path it (or the handler) runs the engine and the response carries them. Remember the boundary-remap pitfall documented in the code (backend.py:109-118): "this boundary re-maps core fields one by one, so an unlisted field is silently dropped" — the new field must be explicitly populated. MCP queries do NOT write query_log (D-08).

### Pattern 9: Docs regeneration

New settings must be added to `SECTIONS` in scripts/generate_config_ref.py:150-196 (the "Search Settings" section at :175-182 is the natural home for `rrf_k`/`bm25_weight`/`vector_weight`; query-history fields can join it or get their own section), then `make docs-generate` (Makefile:71-74: `python scripts/generate_cli_ref.py && python scripts/generate_config_ref.py`). The generator renders env vars as `` `SIF_{FIELD_NAME.UPPER()}` `` (generate_config_ref.py:292). Doc-gate test greps must use `SIF_RRF_K`-style spellings, never lowercase field names (Phase 12 lesson). CLI reference for `sif suggest` comes from generate_cli_ref.py automatically once the command exists. Never hand-edit the two docs.

### Anti-Patterns to Avoid

- **Routing the default path through normalizing fusion** — `fuse_with_weights` halves scores at defaults (experiment E2). Byte-identical bar (SC1) fails silently in one line.
- **Click flag defaults of 60/1.0** — a literal default masks `SIF_` settings forever; precedence dies. Default None.
- **Computing DYM before knowing results are zero** — the engine costs tens of ms; only the zero-result path may pay it (D-05).
- **Hand-editing docs/configuration.md** — generator-owned; regen only.
- **Naive local timestamps in query_log** — WR-03 (llm_cache) is the cautionary open finding; use aware UTC isoformat.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Near-string matching | edit-distance implementation | `difflib.get_close_matches` (stdlib) | D-locked; measured adequate with bucketing; `ratio = 2.0*M/T` [CITED: docs.python.org] |
| Term enumeration from the index | parsing FTS5 segments / scanning documents | `fts5vocab` row-mode virtual table | One row per term with doc-frequency; derived, always in sync (D-06) |
| Prefix completion | SQL LIKE scans | `bisect` over the sorted vocab list | 0.001 ms/word measured; LIKE buys nothing |
| Fusion weighting math | bespoke weighted ranker class | extend `RRFFusion.fuse` | Formula is 3 lines; D-01 defines it exactly |
| Settings plumbing | custom env parsing | Pydantic Settings fields + validators | Repo-wide pattern; naming-the-field errors |
| History persistence | ad-hoc sqlite outside repositories | `QueryLogRepository` in repositories.py | CLAUDE.md repository pattern; test isolation via drop_all |

**Key insight:** every hard part of this phase (vocabulary, matching, prefix, persistence) has a verified-cheap primitive already available; the phase's actual risk is surface coordination (three flags, three construction sites, two MCP schemas, one docs generator) and the byte-identical compat bar.

## Common Pitfalls

### Pitfall 1: The existing `fuse_with_weights` normalizes — SC1 trap
**What goes wrong:** Reusing `RRFFusion.fuse_with_weights` (rrf.py:93-175) for weighted fusion silently halves every fused score at default weights.
**Why:** `normalized_weights = [w / total_weight for w in weights]` (rrf.py:113-114); at (1.0, 1.0) each becomes 0.5 — measured exactly-half scores (experiment E2).
**How to avoid:** extend `fuse()` with optional `weights` (multiply form, `None` → today's literal arithmetic). Optionally delete/repurpose `fuse_with_weights` (zero call sites today, grep-verified) — but never let the default path route through it.
**Warning signs:** golden test showing `0.5×` scores; `--explain` output with halved `rrf_score` values.

### Pitfall 2: Full-vocab difflib blows the 100 ms core budget on multi-word queries
**What goes wrong:** `get_close_matches` over the whole vocab costs ≈46 ms/word at 73k terms (measured; 69 ms at cutoff 0.6) — a 3-word query ≈140 ms.
**Why:** `SequenceMatcher.ratio()` runs per candidate; cost scales linearly with vocab size.
**How to avoid:** first-letter±1 bucket prefilter (measured 10.9 ms/word; 3 words ≈33 ms; +26 ms vocab scan + ~1 ms history ≈60 ms total, inside budget with headroom). D-14 explicitly anticipated "prefix narrowing if measurement says so" — the measurement now says so.
**Warning signs:** suggest tests timing out near 100 ms on CI; per-word cost tracking vocab size linearly. Known quality cost: first-letter typos more than one letter away escape the bucket — acceptable, document it.

### Pitfall 3: The vocab table displays porter STEMS
**What goes wrong:** DYM/prefix suggestions render mangled words — "machin", "studi", "ar" (real stems from the experiment) — because `tokenize='porter'` stores stemmed terms in the index (schema.py:225/235) and the vocab enumerates them.
**Why:** fts5vocab reports tokens as stored, post-tokenizer; SIF has no reverse stem→surface map (the vocab is the only cheap source; D-06 forbids new sync-maintained tables).
**How to avoid:** (a) accept stem display (recommendation — suggestions query correctly either way, A4-verified); (b) keep user-typed tokens when they already match (prefix-tolerant membership) so only genuinely-misspelled words get stem replacements. Optionally surface-form mapping is a v2 idea — do not build it now.
**Warning signs:** UAT complaints about "Did you mean: quantum machin"; UX mismatch with D-07's illustrative example.

### Pitfall 4: In-vocab membership test that never fires (or always fires)
**What goes wrong:** comparing raw user words against stem vocab — "machines" looks out-of-vocab (only `machin` exists) → spurious DYM on correct queries; conversely a too-loose prefix test suppresses legitimate corrections.
**Why:** porter stems both sides at query time (that's why `"machines"*` matches) but the vocab stores only one side.
**How to avoid:** test membership the way the searcher does — a token "matches" if its prefix range hits any vocab term (bisect, ~free). D-07's "every word already in vocab → no DYM" then means "every word already retrieves".
**Warning signs:** DYM appearing on queries that return results through `search` (single-source BM25) — note D-05 only triggers on zero results, which mostly masks this; the visible symptom is DYM suggesting a *shorter* stem of a word the user typed correctly.

### Pitfall 5: Zero-result JSON shape change breaks the documented `[]` contract
**What goes wrong:** `format_results_json` (search.py:70-76) returns a top-level ARRAY; the `.claude/skills/sif-search/SKILL.md` contract documents "If output is `[]`: report No results found; if EMPTY: no index exists". Wrapping zero-result output in `{"results": [], "suggestions": [...]}` changes the shape consumers parse.
**Why:** CONTEXT locked "JSON gains a suggestions key" — the wrap decision is ours; an always-object shape is a breaking change to every JSON consumer for a rare case.
**How to avoid (recommendation):** keep the array when results exist; on zero results WITH suggestions, emit `{"query": ..., "results": [], "suggestions": [...]}`; on zero results with NO suggestions keep plain `[]` (skill contract intact for the no-vocab-hit case). Update `.claude/skills/sif-search/SKILL.md` in the same plan. Alternative (cleaner long-term, breaking now): always-object — planner should pick explicitly, not accidentally.
**Warning signs:** sif-search skill misreporting "no index"; MCP/CLI JSON consumers failing on mixed shapes.

### Pitfall 6: The DYM hook must precede the early `return` in table mode
**What goes wrong:** the zero-result table path prints "No results found." and `return`s immediately (search.py:446-449, 599-602, 831-834) — DYM code placed after the output block never runs.
**How to avoid:** hook at each early-return site (or refactor each command's zero-result branch to compute suggestions first). Also mind mode routing: table mode → stdout Rich (`console`), JSON mode → the suggestions key, CSV/MD/XML/files modes → stderr (`console_err`) so machine output stays pure (Phase 14 stdout-purity culture; format batteries read `result.stdout` because click ≥8.2 mixes stderr into `.output`).
**Warning signs:** stdout-purity tests failing on suggestion text in `--csv` output.

### Pitfall 7: WR-02 — the try/except shape around SearchPipeline (do not widen)
**What goes wrong:** `query_cmd` constructs `SearchPipeline` at search.py:777-784 INSIDE `with db.connection:` but OUTSIDE the `try:` at :785 — on machines without sqlite-vec, construction (`HybridSearcher.__init__` → `VectorSearcher.__init__` raises RuntimeError) crashes with a raw traceback instead of ClickException. Verbatim from 14-REVIEW.md (WR-02, disposition open):
> `VectorSearcher.__init__` raises `RuntimeError("sqlite-vec extension is not available...")` by design (`vector.py:20-24`, documented in CLAUDE.md). In `vsearch_cmd` the construction at line 575 has no guard at all, and in `query_cmd` the `SearchPipeline(...)` construction at lines 769-776 sits **outside** the `try: pipeline.search(...) except RuntimeError → ClickException` block

**How to avoid:** weight plumbing rides `options` (built at :701-709, passed to `pipeline.search` at :786 — already inside the try). Do NOT move or restructure the construction in this phase; if a diff touches those lines, moving construction inside the existing try is the one-line shrink of the defect (permitted, not required — it's tracked in the ledger).
**Warning signs:** a plan task that "refactors query_cmd construction ordering" beyond adding option fields.

### Pitfall 8: fts5vocab is not auto-created and cannot be temp
**What goes wrong:** `SELECT FROM documents_fts_v` raises `no such table` on every existing user DB; creating it as a temp table fails (`no such fts5 table: temp.documents_fts` / `temp.main.documents_fts` — both probed).
**Why:** fts5vocab tables must be explicitly CREATEd and live in the same schema as their FTS table; temp-schema vocab cannot see main-schema FTS.
**How to avoid:** add creation to `SchemaManager._create_fts_tables` (idempotent `IF NOT EXISTS`, verified) AND a lazy ensure in the engine (MCP backend connections never run init_schema). Handle the read-only-DB edge: vocab creation needs one write (SIF opens read-write everywhere, so this is theoretical — degrade to "no suggestions" on OperationalError rather than crash).
**Warning signs:** integration tests passing on fresh DBs but failing on seeded old-schema DB fixtures.

### Pitfall 9: Single-source early returns and the second fuse call site
**What goes wrong (two subtleties):** (1) `HybridSearcher.search` early-returns raw single-source lists when one side is empty (hybrid.py:67-71) — weights are a semantic no-op there (today's behavior preserved; document, don't "fix"). (2) `SearchPipeline.search` fuses per-query VARIANT lists at hybrid.py:228 — that is cross-query fusion, not source fusion; applying bm25/vector weights there is wrong (lists aren't sources). Apply weights ONLY at hybrid.py:74.
**How to avoid:** pass weights at exactly one call site; `k` may flow to both (same constant semantics). Test: expansion path (`expand:` prefix or expander present) with non-default weights produces expected ranking.

### Pitfall 10: query_log write failures must never break search
**What goes wrong:** a locked DB (watch daemon mid-burst) turns a history INSERT into a search failure.
**Why:** the write happens on the hot path of every search command.
**How to avoid:** fail-soft try/except + `logger.warning` (the `_pre_search_refresh` D-05 precedent); busy_timeout (5s, factory.py:62) already covers contention; short CRUD outside the flock per Phase 11 D-01.
**Warning signs:** search e2e tests failing intermittently under concurrent-watch fixtures.

### Pitfall 11: CJK corpora tokenize as whole runs
**What goes wrong:** for Chinese notes, unicode61+porter yields unsegmented run terms (verified: `量子机器学习入门`, `笔记` are single vocab terms) — prefix completion works on run prefixes (`量子机*` hits), but DYM near-matching on long runs is low-value and suggestions display whole phrases.
**How to avoid:** nothing to build — the engine is string-generic and the ≥1-hit guarantee holds. Set expectations in UAT (zh-CN personal corpora get run-level completions, not word-level); a CJK segmenter is out of scope.
**Warning signs:** none at runtime; purely a UX-expectation item for the user whose core value statement is Chinese.

## Runtime State Inventory

Not a rename/refactor/migration phase — greenfield feature work on existing tables plus two new schema objects (`documents_fts_v` vocab shadow, `query_log`). The only state-adjacent notes: (1) old user DBs lack `documents_fts_v` until first open post-upgrade (handled by idempotent create, Pitfall 8); (2) no data migration of any kind is required — `query_log` starts empty (D-13 cold start).

## Code Examples

### Golden test pinning SC1 (byte-identical defaults)

```python
# tests/unit/search/test_rrf.py (extend existing module — fixtures already build
# bm25_results / vector_results lists of SearchResult)
def test_fuse_default_weights_byte_identical(bm25_results, vector_results):
    """SC1: weights=[1.0, 1.0] must reproduce plain fuse to the last bit."""
    fusion = RRFFusion(k=60)
    plain = fusion.fuse([bm25_results, vector_results], limit=10)
    weighted = fusion.fuse([bm25_results, vector_results], limit=10, weights=[1.0, 1.0])
    assert [(r.document_id, r.score, r.rank, repr(r.scores["rrf_score"])) for r in plain] == [
        (r.document_id, r.score, r.rank, repr(r.scores["rrf_score"])) for r in weighted
    ]

def test_weighted_fusion_reorders(bm25_results, vector_results):
    """Heavy BM25 weight pulls BM25-only docs up (sanity for actual weighting)."""
    fusion = RRFFusion(k=60)
    baseline = [r.document_id for r in fusion.fuse([bm25_results, vector_results], weights=[1.0, 1.0])]
    bm25_heavy = [r.document_id for r in fusion.fuse([bm25_results, vector_results], weights=[5.0, 0.2])]
    assert baseline and bm25_heavy  # ordering assertions per fixture design
```

(Experiment E1 proved repr-exactness of the multiply form; this test pins it against regressions. A second, pipeline-level golden — fixture corpus + deterministic fake embedder, full `SearchOptions()` defaults, snapshot the `to_dict()` list — captures today's output before any change and asserts equality after; Phase 11's SC3 golden-equivalence culture.)

### Vocab access and DYM core (verified primitives)

```python
# Source: local experiments A1-A5, B1-B7 (SQLite 3.51.0, this session) +
# difflib signature [CITED: docs.python.org/3/library/difflib.html]
import bisect, difflib

conn.execute(
    "CREATE VIRTUAL TABLE IF NOT EXISTS documents_fts_v USING fts5vocab(documents_fts, 'row')"
)
rows = conn.execute("SELECT term, doc FROM documents_fts_v").fetchall()  # ~26 ms @ 73k
terms = [r["term"] for r in rows]          # porter STEMS (machin, studi, ar)
df = dict(rows)                            # term -> doc frequency (completion ranking)
terms.sort()                               # ~1 ms @ 73k

def prefix_completions(p: str, k: int = 5) -> list[str]:
    i = bisect.bisect_left(terms, p.lower())
    out = []
    while i < len(terms) and terms[i].startswith(p.lower()) and len(out) < k:
        out.append(terms[i]); i += 1       # ~0.001 ms/word measured
    return out

def close_words(tok: str, n: int = 3, cutoff: float = 0.75) -> list[str]:
    t = tok.lower()
    bucket = [w for w in terms if abs(ord(w[0]) - ord(t[0])) <= 1]   # 46 -> 11 ms/word
    return difflib.get_close_matches(t, bucket, n=n, cutoff=cutoff)  # stdlib; case-sensitive -> lower both sides
```

### SC2 pin test (every suggestion returns ≥1 hit)

```python
def test_every_dym_suggestion_hits(searcher_with_fixture_corpus, zero_result_query):
    engine = SuggestionEngine(searcher_with_fixture_corpus.db)
    for suggestion in engine.did_you_mean(zero_result_query):
        results = searcher_with_fixture_corpus.search(suggestion, SearchOptions(limit=1))
        assert results, f"suggestion {suggestion!r} returned zero hits (SC2 violation)"
```

Structurally guaranteed: suggested terms come from the vocab, and `_build_fts_query` quotes them as `"stem"*` prefix phrases which match their contributing documents (experiment A4).

### query_log repository skeleton (conventions)

```python
class QueryLogRepository:
    def __init__(self, db: sqlite3.Connection) -> None:
        self.db = db

    def add(self, entry: QueryLogEntry, keep: int) -> None:
        """Insert + trim-in-write in one short transaction (D-09)."""
        self.db.execute(
            "INSERT INTO query_log (id, query, result_count, collections, created_at)"
            " VALUES (?, ?, ?, ?, ?)",
            (entry.id, entry.query, entry.result_count,
             json.dumps(entry.collections), entry.created_at.isoformat()),
        )
        self.db.execute(
            "DELETE FROM query_log WHERE id NOT IN"
            " (SELECT id FROM query_log ORDER BY created_at DESC LIMIT ?)",
            (keep,),
        )

    def history(self) -> list[tuple[str, int, str]]:   # (query, count, last_used) — D-13 one aggregate SQL
        return [tuple(r) for r in self.db.execute(
            "SELECT query, COUNT(*), MAX(created_at) FROM query_log GROUP BY query"
        ).fetchall()]

    def clear(self) -> int: ...
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Hardcoded `RRFFusion(k=60)` equal weights | Weighted RRF per query (ES `rank_constant` 60 + per-retriever weight × 1/(k+rank); Weaviate alpha) | Industry-standard for years (milestone FEATURES.md) | Phase 15 catches up to the hosted-engine convention SIF's peers already expose |
| Spellfix1 / SymSpell for DYM | difflib over FTS5 vocab (SIF choice: zero-dep, local) | Milestone research verdict | spellfix1 unavailable in CPython sqlite (verified in milestone STACK); symspellpy deferred to FUTR-03 |
| Silent auto-rewrite | Suggest-only DYM (Meilisearch/Typesense-consistent) | UX convention | Locked in REQUIREMENTS Out of Scope |

**Deprecated/outdated:** none in-repo; `fuse_with_weights` (rrf.py:93) is currently dead code whose normalization contract conflicts with D-01 — repurpose or remove during this phase rather than leave a trap.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Stem display in suggestions is acceptable UX (D-07's "machine" example cannot be produced from a stem-only vocab without new infrastructure) | Pitfall 3, Pattern 5 | User disappointment in UAT; mitigation is v2 surface mapping, not in-scope |
| A2 | ~73k distinct terms is a realistic upper-personal-KB vocab (synthetic 600×220-word corpus; the user's real default DB holds only 2 docs — stale, uninformative) | Cost model | If real vocabs reach 200k+, bucketed cost ~3× (still ≈33 ms/word-budget-headroom); suggest re-measuring in UAT |
| A3 | First-letter±1 bucketing loses only rare corrections (first-letter typos ≥2 letters away) | Pitfall 2 | Slightly weaker DYM recall; full scan remains correct fallback if 100 ms is exceeded on small vocabs (bucket adaptively by vocab size) |
| A4 | Zero-result JSON wraps to an object only when suggestions exist (recommended shape) — CONTEXT locked "gains a suggestions key" but not the exact wrap | Pitfall 5 | Skill/consumer contract churn; planner should decide explicitly and update `.claude/skills/sif-search/SKILL.md` |
| A5 | `SIF_QUERY_HISTORY_LIMIT` default 500, history half-life ≈14 days, per-section top-N (5 completions / 3 DYM / 5 history), min prefix length 2 | Patterns 5-7 | Pure discretion items — any reasonable value works; confirm at plan review |
| A6 | MCP suggestions field is a flat `suggestions: list[str]` of DYM query strings (not the three-section structure) | Pattern 8 | Assistants get less structure; three-array shape is the alternative at equal cost |
| A7 | `k` (rrf_k) applies to both fuse call sites; weights only to the source fusion (hybrid.py:74) | Pitfall 9 | Semantics judgment call; alternative is options.rrf_k honored only at source fusion |

## Open Questions (RESOLVED)

All three questions were decided during Phase 15 planning — none remain open.

1. **DYM display form (stems vs surface)** — RESOLVED: ship stem display (decided in 15-02 flagged_assumptions, adopting A1); surface-form mapping deferred to v2, limitation surfaced for UAT.
   - What we know: vocab = porter stems (verified); stems query correctly; D-07's example shows a surface form the vocab cannot produce.
   - What was unclear: whether the user accepts "Did you mean: quantum machin".
2. **Exact in-vocab predicate for D-07's "no DYM when every word is in vocab"** — RESOLVED: prefix-range membership via bisect, the recommended option (locked in 15-02 Task 2, action step 2); revisit only if UAT shows noise.
   - What we know: raw-word membership against stems misfires both ways (Pitfall 4).
   - What was unclear: prefix-tolerant membership vs a small python porter-stemming approximation for the predicate only.
3. **Zero-result JSON wrap shape (A4)** — RESOLVED: conditional object (decided in 15-03 Task 2 + 15-03 flagged_assumptions) — plain `[]` when no suggestions, `{"query", "results": [], "suggestions"}` when suggestions exist; `.claude/skills/sif-search/SKILL.md` updated in-plan.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| SQLite FTS5 (+porter) | index/search | ✓ | 3.51.0 (local python3) | — (bundled with CPython) |
| fts5vocab | suggestion engine | ✓ (verified locally) | same | — |
| sqlite-vec | vector side of hybrid search/tests | optional (WR-02) | per-machine | BM25-only paths; engine is vec-free |
| Python ≥3.10 | all | ✓ | py3.13.11 local / repo floor 3.10 | — |
| difflib/bisect (stdlib) | DYM/prefix | ✓ | bundled | — |

**Missing dependencies with no fallback:** none.
**Missing dependencies with fallback:** none applicable.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest + pytest-cov (addopts `--cov=src/sif ...`, pyproject.toml:203-211) |
| Config file | pyproject.toml `[tool.pytest.ini_options]` |
| Quick run command | `env -u FORCE_COLOR NO_COLOR=1 pytest tests/unit/search/test_rrf.py -x` |
| Full suite command | `env -u FORCE_COLOR NO_COLOR=1 pytest` (1015 tests @ 96.2% today; fail_under=90) |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| QUAL-01 | default weights byte-identical (SC1) | unit | `pytest tests/unit/search/test_rrf.py -k byte_identical -x` | ✅ extend (module exists) |
| QUAL-01 | weights reorder fusion; k honored | unit | `pytest tests/unit/search/test_rrf.py -k weighted -x` | ✅ extend |
| QUAL-01 | CLI flags > SIF_ > default precedence | integration (CliRunner) | `pytest tests/unit/cli/test_search.py -k rrf -x` | ✅ extend |
| QUAL-01 | MCP QueryInput weights → options; settings default (D-04) | unit | `pytest tests/unit/mcp/test_handlers.py -k weight -x` (path per existing layout) | ✅ extend existing MCP tests |
| QUAL-02 | zero-result DYM on all three commands; stdout purity per mode | integration | `pytest tests/unit/cli/test_search.py -k did_you_mean -x` | ✅ extend |
| QUAL-02 | every suggestion ≥1 hit (SC2 pin) | integration | `pytest tests/unit/search/test_suggest.py::TestDYM -x` | ❌ Wave 0 |
| QUAL-03 | query_log write/trim/opt-out/clear | unit | `pytest tests/unit/database/test_query_log_repo.py -x` | ❌ Wave 0 |
| QUAL-03 | history ranking (frequency × recency) | unit | `pytest tests/unit/search/test_suggest.py::TestHistory -x` | ❌ Wave 0 |
| QUAL-04 | suggest three sections + --json shape | integration | `pytest tests/unit/cli/test_suggest.py -x` | ❌ Wave 0 |
| QUAL-04 | 100 ms core budget on fixture vocab (SC4) | perf-ish unit (perf_counter, generous headroom, no wall-clock races) | `pytest tests/unit/search/test_suggest.py::TestBudget -x` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** quick run for touched modules (`env -u FORCE_COLOR NO_COLOR=1 pytest tests/unit/search/test_rrf.py tests/unit/search/test_suggest.py -x`)
- **Per wave merge:** `ruff check src tests && ruff format --check src tests && env -u FORCE_COLOR NO_COLOR=1 pytest`
- **Phase gate:** full suite green before `/gsd-verify-work`; docs gate (`make docs-generate` then diff-clean) after settings land.

### Wave 0 Gaps
- [ ] `tests/unit/search/test_suggest.py` — engine: DYM, prefix, history, budget, ≥1-hit pin (QUAL-02/04)
- [ ] `tests/unit/database/test_query_log_repo.py` — repository CRUD + trim-in-write + clear (QUAL-03)
- [ ] `tests/unit/cli/test_suggest.py` — CliRunner table/`--json`/`--clear-history`/no-index guard (QUAL-04)
- [ ] Golden snapshot capture for SC1 — capture today's fused output on a fixture BEFORE implementation lands (red-then-green ordering in the same plan)
- [ ] `.claude/skills/sif-search/SKILL.md` — update the zero-result JSON contract note (A4) once the shape is chosen

## Security Domain

config.json has no `security_enforcement` key → treated as enabled. Phase 15 adds no network surface and no new dependencies.

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | local single-user tool; no auth surface added |
| V3 Session Management | no | — |
| V4 Access Control | no | — |
| V5 Input Validation | yes | Query strings reach SQL only via parameterized statements (repositories) and FTS MATCH via `_sanitize_term` quoting (bm25.py:21-33, metachars `["*():^]` stripped) — suggestions (vocab-derived terms) must pass through the same `_build_fts_query` path when re-queried, never raw string interpolation; new CLI flags validated with click ranges + Pydantic `ge`/`gt`; MCP fields validated by Pydantic on `QueryInput` |
| V6 Cryptography | no | — |
| V12 File Handling | marginal | query_log is local SQLite in the user data dir; no new file paths |

### Known Threat Patterns for this stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| FTS5 query injection via crafted query strings (MATCH syntax) | Tampering | Existing: `_sanitize_term` strips metachars and double-quotes every token (bm25.py:16-33). Suggestion terms flow through the same builder when pinned/re-queried — never build MATCH strings from vocab terms by hand |
| SQL injection via history/suggest paths | Tampering | Parameterized statements only in `QueryLogRepository`/engine (repo convention); `LIKE` prefix params bound, not f-string'd |
| Privacy: query history exfiltration surface | Information Disclosure | History is local-only (query_log in sif.db); MCP queries never log (D-08) precisely so assistant traffic never enters personal history; `SIF_QUERY_HISTORY_ENABLED=0` global opt-out; `--clear-history` single-kill |
| Storage growth DoS (unbounded history) | DoS | Trim-in-write cap (D-09, default 500) |

## Sources

### Primary (HIGH confidence)
- Source files Read this session (all line-anchored claims above): src/sif/search/rrf.py, src/sif/search/hybrid.py, src/sif/core/models.py, src/sif/database/schema.py, src/sif/database/repositories.py, src/sif/database/connection.py, src/sif/database/database.py, src/sif/database/factory.py (pragma grep), src/sif/cli/commands/search.py, src/sif/cli/commands/context.py (shape), src/sif/cli/main.py, src/sif/config/settings.py, src/sif/mcp/protocol.py, src/sif/mcp/backend.py, src/sif/mcp/handlers.py, src/sif/search/bm25.py, scripts/generate_config_ref.py, Makefile, pyproject.toml
- Local experiments (SQLite 3.51.0, python3.13, this machine, this session): /tmp/sif15_research/measure.py (A1-A5, B1-B7), measure2.py (C/D/E1-E2), measure3.py (temp-vocab RO probe), measure4.py (idempotency/qualification probes)
- .planning/phases/11-live-index-foundation-concurrent-db-incremental-core/11-RESEARCH.md (D-01 short-CR lock contract)
- .planning/phases/14-freshness-floor-pre-command-refresh-staleness-marking/14-REVIEW.md + 14-REVIEW-DISPOSITION.md (WR-02 verbatim, open)

### Secondary (MEDIUM confidence)
- docs.python.org/3/library/difflib.html — `get_close_matches(word, possibilities, n=3, cutoff=0.6)` signature quoted verbatim via WebFetch this session
- sqlite.org/fts5.html §8 (fts5vocab) — page truncated before the section on fetch; behavior verified empirically instead (creation syntax, row-mode columns, temp-schema limitation all reproduced locally)
- .planning/research/FEATURES.md + STACK.md (milestone survey — search-quality rows, spellfix1 unavailability, difflib full-scan slowness cross-check)

### Tertiary (LOW confidence)
- None — no claim above rests on web-only or training-only evidence.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — zero new deps; all primitives verified locally (fts5vocab shape, difflib costs, float-exactness)
- Architecture: HIGH — every integration point Read this session with line anchors; three-host engine follows the established one-core-many-hosts precedent
- Pitfalls: HIGH — every pitfall empirically demonstrated or quoted verbatim from the repo/ledger, except A1-A7 which are logged as assumptions

**Research date:** 2026-11-08
**Valid until:** 2026-12-08 (stable domain; re-verify difflib cost model only if vocab assumptions change)
