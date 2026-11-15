# Phase 20: Metadata Filtering + Discovery - Research

**Researched:** 2026-11-15
**Domain:** SQLite FTS5 + sqlite-vec metadata filtering, typed frontmatter key-value storage, query-AST validation, MCP/CLI discovery surface
**Confidence:** HIGH on the codebase seams and measured SQL behavior; MEDIUM on qmd parity details (the target is `[Unreleased]` and is verified only against a pinned clone + docs snapshots)

## Summary

The phase is implementable with **zero new runtime dependencies**. Three problems decide the plan's shape, and all three now have measured answers:

1. **Storage.** A single typed kv table — one row per scalar value with an `ordinal` (arrays become several rows), `value_type` in `('string','number','boolean')`, nullable typed columns, PK `(document_id,key,ordinal)`, FK cascade — plus three partial covering indexes is the right design. It supports typed pushdown, per-type discovery splits, numeric min/median/max (via window functions and integer division — **no JSON1**), and per-document delete-then-insert in the caller's transaction. Typed rows must be derived from the **canonical JSON string**, not the in-memory dict, or YAML dates diverge between the live write path and the backfill.

2. **SQL pushdown.** The BM25 outer-WHERE and vector post-KNN-JOIN seams exist and already take parameterized fragments. `prefix` on `path` must compile to a half-open **range**, not `LIKE`: measured on SQLite 3.51.0, `path LIKE ?` does a full `SCAN` under the default BINARY index, while `path >= ? AND path < ?` uses `idx_documents_path` (0.116 ms vs 0.49 ms at 10 k docs). `mtime` ranges use `idx_documents_mtime`. `contains`/`suffix` use `instr()`/BLOB `substr()` (qmd's own approach), so there is no LIKE wildcard escaping to get wrong.

3. **Vector leg.** The Phase 19 escalation loop has a **measured latent bug that metadata filters would expose**: its saturation test (`len(rows) < fetch_k`) is evaluated *after* the post-KNN JOIN, so any selective JOIN filter breaks escalation and silently under-returns. Reproduced with the real `VectorSearcher`: 100 docs, a 2-doc collection, `limit=10` returns **one** document. The fix is small — when a JOIN filter is present, stop on `candidates >= target`, distinct matching documents found `>= pre_count` (all matches seen), or the `_MAX_FETCH_K` ceiling, never on post-JOIN row count. The D-08 pre-count (measured 0.04–0.42 ms at 10 k docs / 27.7 k kv rows) then also seeds `fetch_k` by selectivity and makes D-09's warning precondition exactly measurable.

**Primary recommendation:** build `src/sif/core/filters.py` (pydantic discriminated union on `operator` + one raw-JSON budget pre-walk + one error formatter) and `src/sif/search/filters.py` (one compiler with two scopes: correlated `EXISTS` for the search legs, uncorrelated `IN (SELECT document_id …)` for the pre-count), store typed rows in one `document_metadata_values` table derived from `json.loads(canonical_metadata_json(...))`, and treat the vector-leg stop-condition correction as a required task (it is the difference between "adaptive over-fetch" and an empty page).

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01:** **`--filter <json>` on every CLI result command** — `sif search` (BM25), `sif vsearch` (vector), `sif query` (hybrid). Same flag name, same grammar, same semantics everywhere; `get`/`multi-get`/`ls` are untouched. — **Reversibility:** costly — these are public CLI surfaces; a shipped flag is a compatibility commitment and removing it breaks scripts.
- **D-02:** **`filter` on all three MCP search inputs** — `QueryInput`, `LexSearchInput`, `VecSearchInput`, mirroring Phase 19's D-05 offset precedent, even though lex/vec tool registration stays Phase 22. Phase 22's parity work then has no filter-schema gap to fill. The new `metadata` tool is registered now on the hand-rolled server, and its input/output schema is frozen as the Phase 22 contract (STATE.md cross-phase contract: "`metadata` tool schema (20 → 22)"). — **Reversibility:** costly — public MCP tool schema consumed by agents.
- **D-03:** **Exactly two reserved built-in fields: `path` (string) and `mtime` (number).** A frontmatter key named `path` or `mtime` is shadowed and is not filterable; discovery reports both as built-in, never as frontmatter keys. No `collection` AST field — the existing `--collection`/`collections` parameter remains the scoping mechanism and ANDs with the filter. — **Reversibility:** costly — the reserved-name set is part of the public filter grammar.
- **D-04:** **No built-in `tags`/`tag` alias.** Tags are ordinary frontmatter; arrays are sets, so `contains`/`all` cover them. A `tag` alias that merged `tags`/`tag`/`keywords` would be invented semantics with no parity target. — Rationale: PROJECT.md's milestone wording "path/mtime/tag/frontmatter" describes user-facing capability, not a reserved-field list; the roadmap's FILT-02 names only `path`/`mtime`.
- **D-05:** **Typed kv rows are written in the same transaction as the document row** — delete-then-insert per document, on both the full body-change path and the Phase 19 metadata fast path (D-07 there). FK `ON DELETE CASCADE` on document delete so `collection remove` needs no extra work. The kv payload is derived from the SAME canonical serializer that produces `documents.metadata` (Phase 19 19-01 decision), so the hashed, stored, and typed views can never disagree. No JSON1 dependency is introduced — no `json_each`/`json_extract` anywhere on the read or write path. — **Reversibility:** costly — a new schema surface every write path must maintain.
- **D-06:** **Backfill is an in-process Python pass over stored canonical `documents.metadata`** — no file re-parse, no forced reindex, no second checksum-convention change. Phase 19 already forced one full re-parse, and `documents.metadata` is canonical JSON as of then, so the typed rows are derivable from the DB alone. Runs inside `SchemaManager`'s idempotent, detection-gated machinery (CR-01 pattern), in per-document short transactions so it is resumable; a `schema_meta` marker is written only after a fully successful pass; fresh DBs and already-backfilled DBs pay zero cost. Announced once, reusing the existing `IncrementalIndexer` progress/notice convention. — **Reversibility:** costly — the marker is a one-time migration contract; changing the backfill later needs a new migration.
- **D-07:** **Non-indexable frontmatter is skipped per key, not per document** — nested objects, nulls, mixed-type arrays, and values over the caps (key ≤ 128 bytes, string ≤ 1024 chars, array ≤ 128 elements, frontmatter ≤ 64 KB) make THAT key absent from the typed store; the document still indexes, stays findable unfiltered, and keeps its other keys filterable. The count of skipped keys is reported by the discovery tool so silence is impossible. Deliberate deviation from qmd's whole-document exclusion: same filter outcome for the offending key, strictly less surprising for the user. — Rationale: qmd's exclusion interacts badly with SIF's personal-KB corpus where one bad note should not vanish from filtered search.
- **D-08:** **One cheap selectivity pre-count per filtered search, reusing the existing escalation loop and hard ceiling.** `SELECT COUNT(*)` over the same compiled predicate (mtime/path indexes + kv joins) tells the leg how many documents match; the existing Phase 19 doubling loop (`fetch_k` from `min(max(target*4, 50), 2048)`, doubling while saturated) is reused unchanged, and `_MAX_FETCH_K = 2048` stays the independent work ceiling (T-19-13: a huge offset must not become unbounded work). No filters → no pre-count, zero cost. — **Reversibility:** reversible.
- **D-09:** **"Too selective" is a stderr warning, never an error.** Emitted once, only when the filter's matching-document count is at least the requested page target AND the vector batch exhausted the ceiling before filling it — i.e. recall is provably incomplete. When the filter genuinely matches fewer documents than requested, the short page is honest and the warning is suppressed. This mirrors qmd's documented caveat ("highly selective filters remain best-effort for top-K completeness"). Warnings go to stderr only, never into `--json`/MCP stdout or the result list. — **Reversibility:** reversible.
- **D-10:** **qmd's 17 operators verbatim, plus `caseInsensitive` (ASCII folding only) on any condition whose value is a string.** Typed exact match with no coercion; missing keys do not match `ne`/`nin` (use `or` + `exists:false`); arrays are sets; no implicit AND between top-level conditions. ONE Pydantic discriminated union on `operator` is the single grammar shared by the CLI, the MCP inputs, and the discovery tool's filter-aware mode. — **Reversibility:** costly — operator semantics are a public contract once shipped; relaxing them later is breaking.
- **D-11:** **Ordering operators are numeric-only.** `gt`/`gte`/`lt`/`lte` accept numbers (`mtime` and numeric frontmatter); a string, boolean, or array operand with an ordering operator is a validation error naming the field and operator — never a lexicographic surprise. `contains` means substring on strings and membership on arrays; `all` means array-contains-every-operand; `in`/`nin` test a scalar against a list. Adding lexicographic string ordering later is purely additive.
- **D-12:** **`mtime` accepts epoch seconds OR an ISO-8601 date/datetime string**, parsed to epoch at validation time; the stored and compared value stays numeric, so this is a field-aware input parse, not a comparison coercion. Rationale: humans typing `--filter '{"mtime":{"gte":"2026-01-01"}}'` is the primary CLI use; agents can pass epoch. — **Reversibility:** costly — accepting ISO becomes an input contract; dropping it later breaks scripts.
- **D-13:** **Explicit AST budgets, enforced by the shared validator:** depth ≤ 8, ≤ 64 nodes, string operand ≤ 1024 chars, array operand / `in`-list ≤ 128 elements. Over-budget is a validation error naming the budget. There is deliberately no "unbounded" escape: the budgets are the only defense against a hostile or runaway agent-authored filter, and they are set generously enough that no hand-written filter hits them. — **Reversibility:** costly — tightening a shipped budget is breaking; these are chosen loose, so future tightening is unlikely to be needed.
- **D-14:** **CLI is `sif collection metadata [NAME]`** (qmd CLI parity) — no NAME means all collections. Options mirror qmd: `--match` (filter entries by key or value), `--min-count`, `--sort count|value`, `--limit`, `--json`. Default rendering is a table; JSON/CSV/Markdown follow the existing output conventions. A top-level `sif metadata` alias is not shipped (additive later if it earns its keep).
- **D-15:** **MCP `metadata` tool inputs are `{filter?, match?, min_count?, sort?, limit?}`** and each key reports: document count (counts are documents, not values), per-type split for mixed-type keys with counts per type, numeric min/median/max, and distinct values with counts plus exact remainders (`totalKeys`, `remainingKeys`, `remainingValues`). Deterministic default ordering: count desc, then key asc. When `filter` is supplied, all counts are measured against the admitted document set (filter-aware coverage, qmd parity). — Rationale: the schema is frozen for Phase 22; exact remainders let an agent budget pagination instead of guessing.
- **D-16:** **Discovery reads the same kv store the filters use** — never `json_extract` on the blob, never a second source of truth. This is the research Pitfall 13 invariant: a discovery tool that reports from a different store than the filter reads can lie about what is filterable.
- **D-17:** **Invalid filters fail as user input, never as a protocol fault.** CLI raises `click.ClickException` naming the offending operator, field, and its path inside the AST (e.g. `filter.tags.gt: "gt" requires a numeric value`). MCP returns `ToolsCallResult(isError=True)` with the same message — a tool execution error (SEP-1303) so the model can self-correct; never a JSON-RPC `INVALID_PARAMS` protocol error. Filter composes by AND with `--collection`, `--min-score`, `--offset`, `--per-chunk`, and reranking; both legs receive the same compiled predicate; an empty filter match set returns an empty page and must never degrade to "no filter" (extends the exclude-all sentinel contract in `bm25.py:70-71` / `vector.py:58-59`). — **Reversibility:** reversible.

### Locked Upstream (roadmap/research — do not re-litigate)

- **qmd parity target re-verified 2026-11-15:** the filter AST, `qmd.metadata` namespaced frontmatter, and the `metadata` MCP tool are **still `[Unreleased]`**; latest release is `2.8.3` (2026-08-16). The operator list read verbatim from the current CHANGELOG matches the research exactly. Pin the parity target to the current `[Unreleased]` era and note in the plan that it may shift.
- Pre-RRF per leg is the seam: BM25 outer WHERE of the materialized weighted-match CTE (never inside the CTE), vector post-KNN JOIN — the same place `collection_filter` already lands in both legs. Post-fusion filtering is rejected (breaks top-K, wastes rerank).
- Parameterized SQL only; no SQL/string passthrough (injection surface).
- `qmd.metadata` namespaced keys filter identically to native keys — one flat key space after resolution.
- Staleness stays derived; contexts keep two-sided `normalize_path` matching (Phase 19 invariants, Pitfall 18).
- Every new CLI command/flag and Settings field must flow through `scripts/generate_config_ref.py` + `make docs-generate` (CI diff gate on generator-owned `docs/cli-reference.md` and `docs/configuration.md` — never hand-edit those).
- No new runtime dependencies (v1.2 locks exactly `mcp` and `rapidfuzz`, both already landed).
- Byte-identical-defaults culture: an unfiltered search must be unchanged — no pre-count, no extra query, no new warning.

### Claude's Discretion

- Exact kv table shape (one normalized table with a `value_type` tag and nullable typed columns vs two tables mirroring qmd's `document_metadata` + `document_metadata_values`), plus its index set and whether array elements are separate rows.
- Module layout: research recommends `src/sif/core/filters.py` (domain AST) + `src/sif/search/filters.py` (SQL compiler); names and internal signatures are the planner's.
- Whether the selectivity pre-count is merged into the first KNN round-trip or issued separately, and its exact seeding rule for `fetch_k`.
- LIKE escaping details for `contains`/`prefix`/`suffix`; whether `prefix` can use an index under the default collation (research flag: EXPLAIN QUERY PLAN — MEDIUM confidence).
- Discovery table column layout/order, default `--limit`, and how remainders render in table vs JSON.
- Message wording for the too-selective notice and all validation errors, subject to D-17's "name the operator, field, and path" rule.
- Whether `search_chunks()` (BM25 chunk-level helper) also honors filters, and whether filtered + `--per-chunk` results need any extra contract note.
- Property-test wording: the research requires `filtered-hybrid ⊆ unfiltered-hybrid ∩ filter-set`, a 2%-selectivity recall fixture, and filter × collection × pagination composition; fixture design is the planner's.
- Rerank interaction: whether a filtered search changes the candidate window beyond D-08's pre-count (the Phase 19 rerank pre-window rule stays authoritative).

### Deferred Ideas (OUT OF SCOPE)

- **Glob/regex path operator** — PROJECT.md's milestone summary says "path prefix/glob", but glob is not one of qmd's 17 operators; adding a non-portable operator would fork the shared grammar. `prefix` covers directory scoping. Revisit as a v1.x candidate if path filtering proves too coarse.
- **`title` as a built-in filter field** — the roadmap names only `path`/`mtime`; `title` filters read frontmatter today, so filename-derived titles don't match. Candidate for a future phase; discovery should make the difference visible.
- **Saved filters / filter presets** — already logged as FILT-F1 (v1.x candidate, trigger: filter usage observed in `query_log`). Would be a new capability, not a clarification of this one.
- **`@file` convention for `--filter`** — inline JSON only for now; file-based filters are additive later.
- **Top-level `sif metadata` alias** — `sif collection metadata` is the qmd-parity home; an alias is additive if users ask.
- **Nested frontmatter objects, SQL passthrough, post-fusion filtering, faceted UI** — all rejected upstream and recorded in REQUIREMENTS.md's Out of Scope table; not re-opened here.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| FILT-01 | Recursive JSON AST (and/or/not + comparison/in/contains/type/exists; qmd semantics verbatim, typed exact match, missing keys don't match `ne`/`nin`, budgets) via shared CLI `--filter` and MCP `filter`. | §qmd Parity Contract (exact node shapes, operator table, semantics); §Code Examples 1 (pydantic AST with prototype evidence); §Validation Architecture FILT-01 rows |
| FILT-02 | Filter by built-in `path`/`mtime` columns (mtime indexed), strictly more expressive than qmd. | §Built-in Fields (`path`/`mtime`) under Compilation & Injection Points (measured plans: path range uses `idx_documents_path`, mtime uses `idx_documents_mtime`); reserved-name shadowing rule; §Validation FILT-02 rows |
| FILT-03 | Filters applied pre-RRF per leg: BM25 outer WHERE of the materialized CTE; vector post-KNN JOIN + adaptive over-fetch, selectivity bound, honest "too selective" message; parameterized SQL only. | §Compilation & Injection Points (measured BM25 plan keeps one MATERIALIZE + no `:=`); §Vector-Leg Adaptive Over-Fetch (measured stop-condition bug + corrected loop); §Selectivity Pre-Count (measured costs) |
| FILT-04 | Typed frontmatter storage + backfill; `qmd.metadata` namespace opt-in; numeric values compare as numbers. | §Typed KV Storage (DDL, indexes, ordinal rows); §Canonical-JSON Derivation (the date-divergence trap); §Backfill Design; §qmd.metadata Resolution |
| FILT-05 | `metadata` tool on CLI + MCP: doc counts, numeric min/median/max, exact remainders; one validator shared; invalid filter → ToolError not protocol error. | §Discovery Aggregates (queries + median window); §CLI / MCP Surface Mechanics (isError path, hand-written schema sync); §Validation FILT-05 rows |
</phase_requirements>

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Filter AST grammar, operator semantics, budgets, error formatting | Domain — `src/sif/core/filters.py` (new) | Presentation (CLI/MCP call it) | One grammar must be shared by CLI, MCP inputs, and discovery; it must not know SQL. |
| AST → parameterized SQL predicate | Search infrastructure — `src/sif/search/filters.py` (new) | Database (indexes it exploits) | The compiler is the only place that knows the kv table shape and `documents` columns. |
| Typed kv rows, canonical derivation, skip accounting | Database — new `document_metadata_values` (+ optional skip table) and a metadata repository | Indexing (write path) | Storage is derived data; the derivation function must be the single source for live writes and backfill. |
| Backfill + migration marker | Database — `SchemaManager` detection gate | — | Matches the Phase 19 CR-01/D-09 pattern; every host (CLI, MCP) already calls `init_schema`. |
| Pre-count, over-fetch, warning | Search — `VectorSearcher` | — | The leg that owns KNN and the ceiling owns the work bound. |
| Pushdown into each leg | Search — `BM25Searcher` / `VectorSearcher` | Hybrid (passes the AST through unchanged) | Pre-RRF is achieved by both legs receiving the same `SearchOptions.filter`. |
| Discovery aggregation | Database — metadata repository (SQL) | CLI/MCP renderers | Aggregates must read the same kv store filters read (D-16). |
| CLI flags / command | Presentation — `cli/commands/search.py`, `cli/commands/collection.py` | Domain validator | Click raises `ClickException`; no SQL in the CLI. |
| MCP tools / error mapping | Transport — `mcp/protocol.py`, `handlers.py`, `backend.py` | Domain validator | Tool execution error (`isError`) is the transport contract; schema frozen for Phase 22. |

---

## Verbatim Codebase Anchors

Every in-repo discrete value used below is quoted here from the file read this session; inline citations reference these anchors.

| Anchor | Citation | Verbatim quote |
|--------|----------|----------------|
| A1 | `src/sif/database/schema.py:74-90` | `id TEXT PRIMARY KEY,` · `path TEXT NOT NULL,` · `mtime REAL NOT NULL,` · `metadata TEXT DEFAULT '{}',` (documents table) |
| A2 | `src/sif/database/schema.py:508-521` | `CREATE INDEX IF NOT EXISTS idx_documents_path` … `ON documents(path)` · `CREATE INDEX IF NOT EXISTS idx_documents_mtime` … `ON documents(mtime)` |
| A3 | `src/sif/database/schema.py:186-199` | `CREATE TABLE IF NOT EXISTS index_meta (` · `key TEXT PRIMARY KEY,` · `value TEXT NOT NULL` |
| A4 | `src/sif/database/schema.py:541-559` | `def drop_all(self) -> None:` · `tables = [` … `"document_embeddings",` |
| A5 | `src/sif/database/factory.py:63-73` | `conn.row_factory = sqlite3.Row` · `conn.execute("PRAGMA foreign_keys = ON")` |
| A6 | `src/sif/database/repositories.py:143-166` | `canonical_metadata_json(document.metadata),` (DocumentRepository.create) |
| A7 | `src/sif/database/repositories.py:216-238` | `canonical_metadata_json(document.metadata),` (DocumentRepository.update) |
| A8 | `src/sif/core/models.py:32-48` | `def canonical_metadata_json(metadata: Mapping[str, Any]) -> str:` · `default=str,` · `separators=(",", ":"),` |
| A9 | `src/sif/core/models.py:329-361` | `limit: int = 10` · `offset: int = 0` · `collection_ids: list[str] | None = None` · `min_score: float = 0.0` (SearchOptions) |
| A10 | `src/sif/indexing/parser.py:16-19` | `CONVENTION_VERSION = 2` |
| A11 | `src/sif/indexing/incremental.py:42-43` | `# D-09: one namespaced key per collection; the value is CONVENTION_VERSION.` · `_CONVENTION_KEY_PREFIX = "convention:"` |
| A12 | `src/sif/indexing/incremental.py:422-427` | `"UPDATE documents SET mtime = ? WHERE id = ?",` |
| A13 | `src/sif/search/bm25.py:23-24` | `_CONTENT_WEIGHT = 1.0` · `_TITLE_WEIGHT = 1.0` |
| A14 | `src/sif/search/bm25.py:70-71` | `if options.collection_ids is not None and not options.collection_ids:` · `return []` |
| A15 | `src/sif/search/bm25.py:110-152` | `WITH matched AS MATERIALIZED (` · `WHERE 1 = 1 {collection_filter} {min_score_filter}` |
| A16 | `src/sif/search/vector.py:11-15` | `_MAX_FETCH_K = 2048` |
| A17 | `src/sif/search/vector.py:58-59` | `if options.collection_ids is not None and not options.collection_ids:` · `return []` |
| A18 | `src/sif/search/vector.py:105-120` | `WHERE embedding MATCH ? AND k = ? {collection_filter}` |
| A19 | `src/sif/search/vector.py:122-135` | `target = max(1, options.limit + options.offset)` · `fetch_k = min(max(target * 4, 50), _MAX_FETCH_K)` · `if len(candidates) >= target or len(rows) < fetch_k or fetch_k >= _MAX_FETCH_K:` |
| A20 | `src/sif/search/hybrid.py:97-102` | `if not vector_results:` · `return _paginate(bm25_results, options)` |
| A21 | `src/sif/mcp/protocol.py:170-174` | `class ToolsCallResult(BaseModel):` · `isError: bool = False  # noqa: N815` |
| A22 | `src/sif/mcp/server.py:127-136` | `except Exception as e:` · `isError=True,` (handler exception → tool execution error) |
| A23 | `src/sif/mcp/server.py:105-117` | `MCPErrorCode.INVALID_PARAMS` (only when `ToolsCallParams` fails to parse) |
| A24 | `src/sif/mcp/handlers.py:45-76` | `input_schema: ClassVar[dict[str, Any]]` · `"offset": {"type": "integer", "minimum": 0, "default": 0},` |
| A25 | `src/sif/mcp/handlers.py:224-231` | `def create_default_tools() -> list[ToolHandler]:` |
| A26 | `src/sif/mcp/backend.py:104-114` | `db.init_schema(embedding_dim=self.settings.embedding_dim)` |
| A27 | `src/sif/mcp/backend.py:134-141` | `async def _run_in_db(self, callback: Callable[[Any], T]) -> T:` |
| A28 | `src/sif/mcp/backend.py:172-191` | `options = SearchOptions(` · `limit=limit,` · `offset=offset,` · `per_chunk=per_chunk,` |
| A29 | `src/sif/cli/error_handling.py:44-66` | `db.init_schema()` · `def open_initialized_database(` |
| A30 | `src/sif/cli/commands/search.py:450-479` | `@search_group.command("search")` · `"--offset",` · `"--no-refresh"` |
| A31 | `src/sif/cli/commands/collection.py:21-25` | `@click.group("collection")` · `def collection_group() -> None:` |
| A32 | `tests/unit/mcp/test_integration.py:104,305` | `assert tool_names == {"query", "get", "multi_get", "status"}` |
| A33 | `tests/unit/search/test_collection_filter.py:242-258` | `class _RecordingConnection:` · `self.calls: list[tuple[str, Sequence[object]]] = []` |
| A34 | `tests/support/bench.py:40-64,98-170` | `class ConceptEmbedder:` · `def build_bench_db(` |
| A35 | `pyproject.toml:217-226` | `[tool.pytest.ini_options]` · `addopts = "--cov=src/sif …"` · `fail_under = 90` |

---

## qmd Parity Contract (parity target: `[Unreleased]`, verified 2026-11-15)

### Source ledger

| Source | Locator | Accessed | What it established | Tag |
|--------|---------|----------|--------------------|-----|
| qmd CHANGELOG `[Unreleased]` | `https://raw.githubusercontent.com/tobi/qmd/main/CHANGELOG.md` | 2026-11-15 | Operator list, pre-RRF statement, `qmd.metadata` block, `metadata` tool/CLI existence, latest release `2.8.3` (2026-08-16) | `[CITED: raw.githubusercontent.com/tobi/qmd/main/CHANGELOG.md]` |
| qmd README (main) | `https://raw.githubusercontent.com/tobi/qmd/main/README.md` | 2026-11-15 | Exact node shapes, `field` naming, `type` values, array semantics, missing-key rule, `caseInsensitive`, discovery input/output names, vector-filter strategy | `[CITED: raw.githubusercontent.com/tobi/qmd/main/README.md]` |
| qmd docs commit `abfabc5` | `https://github.com/tobi/qmd/commit/abfabc5424623046069c42705682c9da0966511a.patch` | 2026-11-15 | Original docs wording; **used `key`, not `field`** — superseded by current main | `[CITED: github.com/tobi/qmd/commit/abfabc54]` |
| qmd source (shallow clone) | `qmd@86d2365d17fc682e491c2c53d1e4a884aee8682a` (2026-10-14) — `src/metadata-filter.ts`, `src/metadata-store.ts`, `src/metadata.ts`, `src/mcp/server.ts`, `src/cli/qmd.ts`, `README.md` | 2026-11-15 | Exact field names, validation rules, budgets, table DDL, compiler SQL, discovery result types, CLI flags | `[CITED: github.com/tobi/qmd tree @86d2365]` |
| deepwiki 3.7 | `https://deepwiki.com/tobi/qmd/3.7-metadata-and-frontmatter-filtering` | 2026-11-15 | **HTTP 429 — not retrieved; not used.** | — |
| SQLite docs | `https://www.sqlite.org/optoverview.html` §5 | 2026-11-15 | LIKE/GLOB index optimization conditions | `[CITED: sqlite.org/optoverview.html]` |
| Local measurements | scratch SQLite 3.51.0 + real `VectorSearcher`, scripts under `/tmp/sif_probe/` | 2026-11-15 | Plans, timings, vector under-return reproduction | `[VERIFIED: measured 2026-11-15]` |

**Parity-target warning (carried from CONTEXT):** every qmd fact below is `[Unreleased]`. The README and the pinned clone agree on the current AST shape except for the docs-commit naming change; anything the plan pins is a pin to one unreleased era.

### Exact AST node shapes (current main)

```json
{ "operator": "and" | "or", "operands": [ ... ] }
{ "operator": "not", "operand": { ... } }
{ "field": "status", "operator": "eq" | "ne" | "gt" | "gte" | "lt" | "lte", "value": "..." }
{ "field": "topics", "operator": "in" | "nin" | "all", "value": [ ... ] }
{ "field": "topic",  "operator": "contains" | "prefix" | "suffix", "value": "...", "caseInsensitive": true }
{ "field": "priority", "operator": "type", "value": "string" | "number" | "boolean" }
{ "field": "reviewed", "operator": "exists", "value": true | false }
```
`[CITED: raw.githubusercontent.com/tobi/qmd/main/README.md, section "Metadata Filtering"]`

- `and`/`or` take **`operands`** (array, non-empty, ≤32 in qmd); `not` takes **`operand`** (singular). `[CITED: README table; qmd@86d2365 src/metadata-filter.ts:215-254]`
- Conditions take **`field`**, not `key`. The docs commit `abfabc5` used `key`; current main and the pinned clone use `field`. `[CITED: README; qmd@86d2365 src/metadata-filter.ts:264-266]`
- `type` values are exactly `"string" | "number" | "boolean"`; `exists` value must be a boolean. `[CITED: qmd@86d2365 src/metadata-filter.ts:290-312]`
- Unknown properties are rejected; `field` must be a non-empty string ≤128 bytes; text operands must be non-empty strings; numbers must be finite; membership arrays must be non-empty, homogeneous, and are de-duplicated. `[CITED: qmd@86d2365 src/metadata-filter.ts:255-395]`
- `caseInsensitive` applies to a **string or string-array** operand, folds ASCII only (`lower()` on the column, ASCII-folded operand). `[CITED: qmd@86d2365 src/metadata-filter.ts:331-345, 685-700]`
- In the discovery `match` grammar the record under test is an entry: `field` must be `"key"` or `"value"`, and `exists`/`all` are rejected. `[CITED: qmd@86d2365 src/metadata-filter.ts:266-280; src/mcp/server.ts:703]`

### Semantics (verbatim intent)

| Rule | qmd statement | Consequence for SIF |
|------|---------------|---------------------|
| Typed exact match | "Matching is typed and exact — no string/number/boolean coercion" | A condition pins the operand's `value_type`; a type mismatch never matches, **including `ne`/`nin`**. |
| Arrays are sets | "Array-valued metadata is a set: a condition matches when any element satisfies it"; `all` "requires every filter value to be present" | One row per element + `EXISTS` per condition is a faithful implementation. |
| `ne`/`nin` presence | "`ne`/`nin` require that no element equals the operand (with at least one element of the operand's type present)" | Compile `ne`/`nin` as `(present same-type value) AND NOT (equal/member)` — a bare `NOT IN` is wrong (missing keys would match). |
| Missing keys | "Missing keys do not match `ne`/`nin`" | Same as above; the documented workaround is `or` + `exists:false`. |
| No implicit AND | "Multiple conditions require an explicit `and` group" | `{"field":"a",...}` and `{"field":"b",...}` are two separate roots, not a conjunction. |
| Ordering | qmd allows string ordering; **SIF D-11 makes it numeric-only** | Deliberate SIF tightening — validation error for string/boolean/array operands. |
| `contains` on arrays | qmd: text operators match string values only, evaluated per element → substring-any | **Conflicts with D-11's "membership on arrays"** — see Open Question 2. |
| Pre-fusion | "Every returned result satisfies the filter (applied before RRF fusion and reranking)" | Both legs must receive the same predicate. |
| Selective honesty | "highly selective filters remain best-effort for top-K completeness" | D-09 warning, not an error. |

### Caps and budgets (qmd source vs SIF locked decisions)

| Limit | qmd actual (source) | SIF locked | Delta |
|-------|--------------------|-----------|-------|
| frontmatter total | 64 KB `maxFrontmatterBytes: 64 * 1024` | D-07: 64 KB | same |
| keys per document | 64 `maxKeys: 64` | not specified | SIF looser/unbounded; document it |
| key length | 128 bytes `maxKeyBytes: 128` | D-07: 128 bytes | same |
| string value | 1024 chars `maxStringLength: 1024` | D-07/D-13: 1024 chars | same |
| array length | 128 `maxArrayLength: 128` | D-07: 128 elements | same |
| AST depth | 16 `maxDepth: 16` | D-13: 8 | SIF tighter (deliberate) |
| AST nodes | 256 `maxNodes: 256` | D-13: 64 | SIF tighter |
| group operands | 32 `maxGroupOperands: 32` | D-13: "≤64 nodes" only | SIF looser per group, bounded by nodes |
| membership values | 64 `maxMembershipValues: 64` | D-13: 128 | SIF looser |
| filter field bytes | 128 (`maxKeyBytes`) | D-13: not named | reuse 128 |

`[CITED: qmd@86d2365 src/metadata.ts:66-74; src/metadata-filter.ts:124-132]`

**Important:** the qmd README documents **no** filter depth/node/string/array budgets — only the source defines them. Any plan text that cites the README for budgets would be wrong; cite the source. The SIF budgets are locked by D-13 regardless.

### Discovery contract (qmd, for the frozen Phase 22 schema)

MCP `metadata` tool inputs (qmd): `collections`, `match`, `filter`, `keyLimit` (50), `keyOffset` (0), `valueLimit` (10), `valueOffset` (0), `sort` (`count`|`value`), `minCount` (1). CLI `qmd collection metadata [name...]` adds `--filter`, `--match`, `--key-limit`, `--key-offset`, `--all-keys`, `--value-limit`, `--value-offset`, `--all-values`, `--sort`, `--min-count`.
`[CITED: qmd@86d2365 src/mcp/server.ts:723-742; src/cli/qmd.ts:1976-2070]`

Output (qmd, `ListMetadataResult` / `MetadataKeySummary` / `MetadataKeyTypeSummary`):
- `documents` — active documents in scope (denominator)
- `filteredDocuments` — present only when `filter` is supplied (the coverage denominator)
- `totalKeys`, `remainingKeys`
- `keys[]`: `key`, `documents`, `types[]`: `type`, `multiValued`, `documents`, `distinctValues`, `values[]` (`value`, `documents`), `remainingValues`, `range?` (`min`, `median`, `max`), `collections[]`
`[CITED: qmd@86d2365 src/metadata-store.ts:270-310, 400-480]`

Counts are **documents**, not values; a document with `topics: [a,b]` contributes one to each value; median is computed over every matching numeric **value row** (array elements each count); keys whose documents disagree on type are split per type with their own counts. `[CITED: qmd@86d2365 src/metadata-store.ts:400-410; README "Metadata Discovery"]`

### Parity deltas the planner must consciously accept

| Topic | qmd | SIF (locked) | Note |
|-------|-----|--------------|------|
| AST field name | `field` (current main) | CONTEXT does not name it; D-17 example uses `filter.tags.gt` (path style) | **Recommend `field`.** The docs commit's `key` is stale. |
| Ordering on strings | allowed | rejected (D-11) | Deliberate tightening; pure additive later. |
| `contains` on arrays | substring-any over elements | D-11 says "membership on arrays" | Contradiction — resolve (Open Question 2). |
| `caseInsensitive` scope | string or string-array | D-10 says "value is a string" | Tighten or match qmd (recommend match qmd for parity). |
| Input naming | camelCase (`keyLimit`, `minCount`) | D-15: snake_case `min_count`, single `limit` | Locked; discovery output remainders stay camelCase per D-15. |
| Value windowing | separate key/value limits + offsets | one `limit` | Ambiguous — resolve (Open Question 4). |
| Vector filtering | scan eligible set when ≤20 000 chunk vectors, else over-fetch/post-filter | D-08 doubling loop + 2048 ceiling | Locked; do not copy qmd's strategy. |
| `qmd.metadata` opt-in | only namespaced block is typed; other frontmatter is not filterable | native frontmatter is typed too; namespace merged | SIF is a superset ("strictly less surprising" per D-07 rationale). |

---

## Standard Stack

### Core (no new dependencies)

| Library / runtime | Version | Purpose | Why standard |
|-------------------|---------|---------|--------------|
| Python | `>=3.10` (`pyproject.toml`); local venv 3.13.9 | Runtime | Project floor. |
| SQLite (stdlib `sqlite3`) | measured 3.51.0; **needs ≥3.35** for `AS MATERIALIZED` (already used) and ≥3.25 for window functions | Storage, FTS5, kv, discovery aggregates | Existing engine. `bm25.py` comment: MATERIALIZED "needs SQLite >= 3.35.0 (2021-03)" `[VERIFIED: src/sif/search/bm25.py:102-107]` |
| Pydantic | `>=2.0.0` (`pyproject.toml`), lock 2.13.1, PATH test env 2.12.5 | AST models + validation | Already a core dep; one discriminated union. `[VERIFIED: pyproject.toml:29-43; uv.lock pydantic 2.13.1]` |
| Click | lock 8.3.2 | CLI flags/command | Existing. |
| sqlite-vec | lock 0.1.9 | Vector table + KNN | Existing. |
| pytest / pytest-asyncio | PATH pytest 9.1.1; `pytest-asyncio>=0.23.0` | Tests | Existing `--cov`/`fail_under=90` config. `[VERIFIED: pyproject.toml:217-226]` |

**Installation:** none. This phase adds no runtime dependency (the v1.2 lock is exactly `mcp` + `rapidfuzz`, both already landed).

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| One kv table with typed columns | Two tables (qmd's `document_metadata` + values) | qmd's state table distinguishes "extracted-empty" from "not extracted"; SIF already has `documents.metadata` (always present, default `'{}'`) and a global backfill marker, so the state table is redundant. One table wins. |
| `json_each`/`json_extract` over the blob | Typed kv rows | Rejected by D-05/D-16; JSON1 cannot serve typed ranges/discovery cheaply and would be a second source of truth. |
| `LIKE 'prefix%'` on `path` | Half-open range on `documents.path` | Measured: LIKE needs `PRAGMA case_sensitive_like=ON` to use the BINARY index; the range works under default pragmas. |
| Expression indexes on `json_extract(metadata, …)` | kv table | Discovery aggregates and typed pushdown both need rows, and D-05 forbids JSON1. |

---

## Typed KV Storage (FILT-04)

### Recommended DDL (one table + skip sidecar)

```sql
CREATE TABLE IF NOT EXISTS document_metadata_values (
    document_id  TEXT    NOT NULL,
    key          TEXT    NOT NULL,
    ordinal      INTEGER NOT NULL,           -- array element index; 0 for scalars
    value_type   TEXT    NOT NULL,
    text_value   TEXT,
    number_value REAL,
    boolean_value INTEGER,
    PRIMARY KEY (document_id, key, ordinal),
    FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE,
    CHECK (value_type IN ('string', 'number', 'boolean')),
    CHECK (
        (value_type = 'string'  AND text_value    IS NOT NULL AND number_value IS NULL     AND boolean_value IS NULL)
     OR (value_type = 'number'  AND number_value  IS NOT NULL AND text_value    IS NULL     AND boolean_value IS NULL)
     OR (value_type = 'boolean' AND boolean_value IN (0, 1)   AND text_value    IS NULL     AND number_value  IS NULL)
    )
);
CREATE INDEX IF NOT EXISTS idx_metadata_text_lookup
    ON document_metadata_values(key, text_value, document_id) WHERE value_type = 'string';
CREATE INDEX IF NOT EXISTS idx_metadata_number_lookup
    ON document_metadata_values(key, number_value, document_id) WHERE value_type = 'number';
CREATE INDEX IF NOT EXISTS idx_metadata_boolean_lookup
    ON document_metadata_values(key, boolean_value, document_id) WHERE value_type = 'boolean';
```

Why this shape:
- **One row per scalar element** makes arrays sets without JSON: `in`/`nin`/`all`/`contains` each become `EXISTS` probes; `multiValued` is `MAX(ordinal) > 0`. This mirrors qmd exactly. `[CITED: qmd@86d2365 src/metadata-store.ts:54-96, 136-160]`
- **`value_type` + nullable typed columns** gives typed exact match and lets `eq` use a covering index probe `(key, text_value, document_id)`. `[CITED: qmd@86d2365 src/metadata-store.ts:76-96]`
- **PK `(document_id, key, ordinal)`** makes delete-then-insert the natural idempotent rebuild and serves the per-document correlated probe. Measured delete+insert of 2 rows inside one transaction: 1.15 ms.
- **FK cascade is real in SIF**: `create_connection` sets `PRAGMA foreign_keys = ON` `[VERIFIED: src/sif/database/factory.py:63-73]` and `documents.id` is the PK `[VERIFIED: src/sif/database/schema.py:74-90]`. Measured: deleting a document removed its kv rows (0 remaining) with the pragma on. **Tests that build a bare `sqlite3.connect()` connection must enable the pragma or delete kv rows explicitly.**

### Skip sidecar (D-07 count a second source of truth)

```sql
CREATE TABLE IF NOT EXISTS document_metadata_skips (
    document_id TEXT NOT NULL,
    key         TEXT NOT NULL,
    reason      TEXT NOT NULL,   -- nested | null | mixed_array | cap_key | cap_string | cap_array | cap_frontmatter
    PRIMARY KEY (document_id, key),
    FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE
);
```

D-07 requires discovery to report the **count of skipped keys**, and D-16 forbids reading the blob from discovery. A skip sidecar written by the same derivation function satisfies both: discovery counts skips in the eligible region and never presents them as filterable keys. The alternative — a sentinel `value_type='skipped'` row inside the value table — contaminates `exists` (a skipped key would look present) unless every `exists`/`type` predicate also excludes it; the sidecar keeps the value table's CHECK constraint clean.

### Canonical-JSON derivation (critical)

Derive typed rows from **`json.loads(canonical_metadata_json(metadata))`**, never from the in-memory dict:

- `canonical_metadata_json` uses `default=str`, so a YAML `date` becomes ISO **text** in the stored blob. `[VERIFIED: src/sif/core/models.py:32-48]`
- The live write path sees a `datetime` object and would skip it (not a str/number/bool), while the backfill parsing the stored JSON would store it as a string → the two disagree, violating D-05.
- One shared helper, e.g. `typed_rows(canonical_json: str) -> tuple[list[TypedRow], list[SkippedKey]]`, used by the repository write path (which already computes the canonical string) and by the backfill (which reads the stored string). `DocumentRepository.create` and `.update` both call `canonical_metadata_json(document.metadata)` `[VERIFIED: src/sif/database/repositories.py:143-166, 216-238]`.

### `qmd.metadata` resolution (FILT-04 migration parity)

Recommended pure function over the canonicalized mapping:

```python
def filterable_metadata(metadata: Mapping[str, Any]) -> dict[str, Any]:
    resolved = dict(metadata)
    qmd = metadata.get("qmd")
    if isinstance(qmd, Mapping) and isinstance(qmd.get("metadata"), Mapping):
        resolved.pop("qmd", None)
        for key, value in qmd["metadata"].items():
            resolved[str(key)] = value      # namespace wins on collision (recommend)
    return resolved
```

- Apply **after** canonicalization (the namespace block survives JSON round-trip intact).
- **Do not** change what `parser.py` stores or what the checksum covers. D-06 forbids a second checksum-convention change; resolving at the derived-view layer keeps `documents.metadata` raw and the Phase 19 checksum untouched. The backfill can resolve from the stored blob without re-parsing files.
- A frontmatter key named `path`/`mtime` is **shadowed** (D-03): the derivation drops it so discovery never reports it and the compiler always resolves the built-in. Do not count shadowing as a "skipped key" (it is reserved, not invalid) — report it separately if the planner wants visibility.
- qmd's actual namespaced location is `qmd:` → `metadata:` (frontmatter): source reads `const qmdNamespace = frontmatter["qmd"];` then `qmdNamespace["metadata"]`, and a document without the namespace yields empty typed metadata (qmd's opt-in). `[CITED: qmd@86d2365 src/metadata.ts:85-129]` SIF deliberately keeps native frontmatter typed as well (a superset), and replaces qmd's whole-document rejection with per-key skipping (D-07).

### Backfill design (D-06)

- **Gate:** `IndexMetaRepository.get(<key>) == <version>`; the codebase's kv table is **`index_meta`**, not `schema_meta` — D-06's wording is a slip. `[VERIFIED: src/sif/database/schema.py:186-199]` `[VERIFIED: src/sif/database/repositories.py:646-669]` Use a global key such as `metadata_values_version` (Phase 19 uses per-collection `convention:<id>` `[VERIFIED: src/sif/indexing/incremental.py:42-43]`; this migration is global because the store is document-derived).
- **Pass:** `SELECT id, metadata FROM documents` (batched), `json.loads`, resolve namespace, derive rows, delete+insert per document; one short transaction per document (resumable, idempotent). Write the marker only after a complete pass.
- **Fresh DB:** zero documents → write the marker immediately (or after a no-op pass); zero cost thereafter.
- **Populated DB:** first `init_schema` after upgrade runs the whole pass. Every CLI command opens via `open_initialized_database` → `db.init_schema()` `[VERIFIED: src/sif/cli/error_handling.py:44-56, 59-66]`, and the MCP backend calls `db.init_schema(embedding_dim=...)` `[VERIFIED: src/sif/mcp/backend.py:104-114]`. **Risk to plan for:** a 100 k-document KB pays the pass synchronously on the first command after upgrade. At the measured ~1 ms/document for a tiny row set (plus JSON parse), budget roughly 1–2 minutes worst case; announce it once via `logger.warning` (stderr, `-q`-suppressible) and keep per-document commits. Do **not** partially enable filtering before the pass completes (a half-populated store silently under-returns).
- **Interruption:** rows already committed stay; the next run redoes them (idempotent). If no-rework resumability is required, add a per-document `metadata_values_version` column instead of a global marker; that is extra schema for a one-time migration and is not recommended at personal-KB scale.
- **`drop_all`:** add the new table(s) to the drop list `[VERIFIED: src/sif/database/schema.py:541-559]`.

### Write path

- Put the sync in **`DocumentRepository.create` / `.update`** (the single choke point): after the row write, inside the caller's transaction, delete+insert kv rows and skip rows. Both Phase 19 paths (`metadata` fast path and full body change) and `added` already go through these methods `[VERIFIED: src/sif/indexing/incremental.py:408-487]`.
- The raw mtime-only convergence `UPDATE documents SET mtime = ?` does not touch metadata `[VERIFIED: src/sif/indexing/incremental.py:422-427]` — no kv work needed.
- `DocumentRepository.delete` / `delete_by_collection` need nothing extra thanks to FK cascade.
- **Test-fixture consequence:** many test builders insert documents with raw `INSERT INTO documents` (e.g. `tests/support/bench.py::build_bench_db`, `tests/integration/test_search_correctness.py::_build_search_db`, `tests/unit/search/test_vector.py`). Those bypass the repository and will have **no kv rows**. Any filter test using them must explicitly insert kv rows or route inserts through `DocumentRepository`.

---

## Compilation & Injection Points (FILT-03 / FILT-02)

### Compiler API (recommended)

```python
# src/sif/search/filters.py
def compile_filter(
    node: FilterNode | None,
    alias: str = "d",
    scope: Literal["candidates", "corpus"] = "candidates",
) -> tuple[str, list[Any]]:
    """Return a parameterized predicate fragment appended to an existing WHERE."""
```

Two scopes, mirroring qmd and justified by measurement:
- **`candidates`** (both search legs): each condition compiles to a correlated `EXISTS (SELECT 1 FROM document_metadata_values mv WHERE mv.document_id = d.id AND …)`. Measured on the real BM25 plan: the match-driven plan stays `MATERIALIZE matched` → `SCAN documents_fts VIRTUAL TABLE INDEX 0:M2` and probes `mv` via `idx_metadata_text_lookup`; filtered cost 6.9 ms vs 3.6 ms unfiltered at 10 k docs.
- **`corpus`** (selectivity pre-count and discovery coverage): each condition compiles to `d.id IN (SELECT mv.document_id FROM document_metadata_values mv WHERE …)`, which SQLite evaluates once and probes per document. Measured pre-count: **0.04–0.42 ms** at 10 k docs / 27.7 k kv rows, versus **2.3 ms** for the correlated form.

`return ("", [])` for `None`; callers append only when non-empty. **Never** drop a non-`None` filter, and never emit `IN ()`.

### Per-operator SQL (parameterized, qmd-faithful)

| AST condition | SQL fragment (over `mv`, `?` bound in order) |
|---------------|---------------------------------------------|
| `eq` string | `mv.key = ? AND mv.value_type = 'string' AND mv.text_value = ?` (case-insensitive: `lower(mv.text_value) = ?` with an ASCII-folded operand) |
| `eq` number/boolean | `mv.key = ? AND mv.value_type = 'number' AND mv.number_value = ?` (boolean binds 0/1) |
| `gt/gte/lt/lte` | numeric only: `mv.key = ? AND mv.value_type = 'number' AND mv.number_value > ?` (etc.) |
| `ne` | `EXISTS(… key, same type …) AND NOT EXISTS(… key, same type, equal …)` |
| `in` / `nin` | `value_type = <first element's type> AND <column> IN (?, …)`; `nin` wraps with the presence `EXISTS` and `NOT` |
| `all` | `AND` of one equality `EXISTS` per element (type pinned) |
| `contains` | `mv.value_type = 'string' AND instr(<text col>, ?) > 0` |
| `prefix` / `suffix` | `mv.value_type = 'string' AND COALESCE(substr(CAST(<text col> AS BLOB), 1, ?) = CAST(? AS BLOB), 0)` (suffix uses `-?`) |
| `type` | `mv.key = ? AND mv.value_type = ?` |
| `exists:true` | key presence `EXISTS`; `exists:false` → `NOT EXISTS` |
| `and` / `or` / `not` | `(a AND b)`, `(a OR b)`, `NOT a` |

`[CITED: qmd@86d2365 src/metadata-filter.ts:448-560, 600-680 — same primitives, same typed pinning]`

**Do not use LIKE.** `contains` via `instr()` and prefix/suffix via BLOB `substr()` need **no wildcard escaping at all**, and they give exact case-sensitive semantics (qmd's behavior). If the planner nevertheless uses LIKE, `%`, `_`, and the escape char must be escaped with `ESCAPE '\'`, and the collation/pragma problem below applies.

### Built-in fields (`path`, `mtime`)

| Condition | Compilation | Measured plan (SQLite 3.51.0) |
|-----------|-------------|-------------------------------|
| `path` `eq`/`in` | `d.path = ?` / `d.path IN (?, …)` | `idx_documents_path` is a candidate but the BM25 plan is match-driven, so it is usually a residual test. |
| `path` `prefix` | **range**: `d.path >= ? AND d.path < ?` with upper bound `prefix + "\U0010FFFF"` | `SEARCH d USING INDEX idx_documents_path (path>? AND path<?)` — 0.116 ms vs 0.49 ms for `LIKE` at 10 k docs. |
| `path` `contains`/`suffix` | `instr(d.path, ?) > 0` / BLOB `substr` | Full scan by nature (no index). |
| `path` `prefix` + `caseInsensitive` | `lower(d.path) >= lower(?) AND lower(d.path) < lower(?) + "\U0010FFFF"` | `lower()` is opaque to the index → no index use. Document the cost. |
| `mtime` ordering | `d.mtime >= ? AND d.mtime <= ?` | `SEARCH d USING INDEX idx_documents_mtime (mtime>? AND mtime<?)` — 0.265 ms at 10 k docs. `[VERIFIED: src/sif/database/schema.py:516-521]` |
| `mtime` `eq`/`in` | equality/IN on the REAL column | index candidate |
| `exists` on built-ins | `1 = 1` (every document has both columns; both are `NOT NULL`) `[VERIFIED: src/sif/database/schema.py:75-90]` | — |
| `type` on built-ins | `path` → only `"string"` matches; `mtime` → only `"number"` matches | validate statically; no SQL needed |

**LIKE optimization rule (official):** "The LIKE optimization might occur if the column named on the left of the operator is indexed using the built-in BINARY collating sequence and case_sensitive_like is turned on. Or the optimization might occur if the column is indexed using the built-in NOCASE collating sequence and the case_sensitive_like mode is off. **These are the only two combinations under which LIKE operators will be optimized.**" `[CITED: sqlite.org/optoverview.html §5]` SIF's `idx_documents_path` is BINARY and `case_sensitive_like` is off → LIKE cannot use it (measured `SCAN d`). Prefer the range.

**`mtime` ISO input (D-12):** parse at validation time with `datetime.fromisoformat` (accept date-only and datetime; reject naive/aware ambiguity by treating date-only as UTC midnight; reject non-finite/negative?). Store epoch seconds (`mtime` is REAL). Keep it a field-aware **input** parse: the AST operand is normalized to a number before compilation.

### BM25 injection (outer WHERE of the materialized CTE)

Existing shape `[VERIFIED: src/sif/search/bm25.py:110-152]`:

```sql
WITH matched AS MATERIALIZED (
    SELECT rowid, bm25(documents_fts, ?, ?) AS score
    FROM documents_fts WHERE documents_fts MATCH ?
)
SELECT … FROM matched m
JOIN documents d ON m.rowid = d.rowid
JOIN collections c ON d.collection_id = c.id
WHERE 1 = 1 {collection_filter} {min_score_filter} {filter_clause}
ORDER BY m.score LIMIT ? OFFSET ?
```

- Place `{filter_clause}` in the **outer** WHERE, after `min_score_filter`; append its params after the min-score param and before `limit/offset`. Both branches (scoped and `--all`) get the same slot `[VERIFIED: src/sif/search/bm25.py:110-152]`.
- **Never** put it inside the CTE: the CTE exists to evaluate MATCH once (comment `[VERIFIED: src/sif/search/bm25.py:98-109]`; research ANTI-PATTERN 2). Measured filtered plan keeps `MATERIALIZE matched` and `SCAN documents_fts VIRTUAL TABLE INDEX 0:M2` with no `:=` per-document FTS scan.
- Keep the exclude-all sentinel semantics `[VERIFIED: src/sif/search/bm25.py:70-71]` and `[VERIFIED: src/sif/search/vector.py:58-59]`. A filter is never a sentinel: `None` = unfiltered, any AST (including one that matches nothing) stays compiled.

### Vector injection (post-KNN JOIN)

Existing shape `[VERIFIED: src/sif/search/vector.py:105-120]` appends `{collection_filter}` to the JOIN WHERE after `WHERE embedding MATCH ? AND k = ?`. Add `{filter_clause}` beside it; both are post-KNN by construction. Plan is a single outer vec0 `SCAN` with PK lookups per emitted row (module audit note `[VERIFIED: src/sif/search/vector.py:98-104]`).

### Vector-leg adaptive over-fetch — measured bug and corrected loop

Current loop `[VERIFIED: src/sif/search/vector.py:122-135]`:

```python
target = max(1, options.limit + options.offset)
fetch_k = min(max(target * 4, 50), _MAX_FETCH_K)
while True:
    rows = self.db.execute(sql, params).fetchall()
    candidates = self._candidates(rows, options)
    if len(candidates) >= target or len(rows) < fetch_k or fetch_k >= _MAX_FETCH_K:
        break
    fetch_k = min(fetch_k * 2, _MAX_FETCH_K)
```

**Measured failure:** `len(rows)` is the post-JOIN survivor count, so any selective JOIN filter makes `len(rows) < fetch_k` true on the first batch and stops escalation. Reproduced with the real `VectorSearcher` on 100 documents / a 2-document collection: `SearchOptions(limit=10, collection_ids=["c1"])` returned `['d0']` only, although both matching documents exist. Raw KNN batches: `fetch_k=50` → 0 survivors; `fetch_k=100/200` → 2 survivors; `len(rows) < fetch_k` was true in every case. `[VERIFIED: measured 2026-11-15]`

**Required correction (when any JOIN filter is present — `collection_ids` or `filter`):**

```python
page_target = max(1, options.limit + options.offset)
pre_count = count_matching_documents(self.db, options)   # only when a filter is present
if filtered and pre_count == 0:
    return []                                            # empty page, never "no filter"
if filtered:
    total_in_scope = count_documents_in_scope(self.db, options)
    total_vectors  = count_vectors_in_scope(self.db, options)   # COUNT(*) over document_embeddings + scope
    expected = ceil(page_target * total_in_scope / pre_count)   # doc-ratio approximation
    fetch_k = min(max(expected, min(page_target * 4, 50)), _MAX_FETCH_K)  # selectivity seeding
else:
    fetch_k = min(max(page_target * 4, 50), _MAX_FETCH_K)
while True:
    rows = …; candidates = self._candidates(rows, options)
    found = len({r.document_id for r in candidates})     # distinct docs, per-chunk safe
    if filtered:
        exhausted = (fetch_k >= _MAX_FETCH_K
                     or found >= pre_count          # every matching document seen
                     or fetch_k >= total_vectors)   # KNN returned the whole table
        stop = len(candidates) >= page_target or exhausted
    else:
        stop = len(candidates) >= page_target or len(rows) < fetch_k or fetch_k >= _MAX_FETCH_K
    if stop: break
    fetch_k = min(fetch_k * 2, _MAX_FETCH_K)
```

Notes for the planner:
- **The ceiling stays `_MAX_FETCH_K = 2048`** `[VERIFIED: src/sif/search/vector.py:11-15]` (anchor A16). Without seeding, the 50→2048 climb is ~6 doublings; with selectivity seeding at 2 % (`target=10` → `fetch_k≈500`) it is 1–2 doublings. Measured KNN at 20 k vectors: 0.7 ms (k=50), 6.4 ms (k=500), 14.5 ms (k=2048); `SELECT COUNT(*) FROM document_embeddings` is 1.7 ms. A full escalation is therefore tens of ms at personal scale and bounded.
- **D-08 says "the existing Phase 19 doubling loop … is reused unchanged".** The *loop and ceiling* are reused; the **stop condition cannot be unchanged**, because the measured under-return is a correctness bug, not a tuning choice. The plan should record this as a required minimal change with the reproduction (this is not a re-litigation of D-08's bound).
- **Per-chunk mode** needs the distinct-document count (not row count) for the "all matches found" test; otherwise `all`/duplicate chunks can satisfy `found` before all documents appear.
- **`min_score`** is applied inside `_candidates`, so use raw `rows` for the found-doc count and `candidates` for the page target.
- **Empty-match short circuit** (pre-count 0) must return `[]` before any KNN — the vector counterpart of the exclude-all sentinel; a test must prove it never degrades to unfiltered.

### Selectivity pre-count (D-08)

```sql
SELECT COUNT(*) FROM documents d
WHERE <collection predicate (if any)>
  AND <compiled filter in "corpus" scope>
```

- Measured at 10 k docs / 27.7 k kv rows: broad tag **0.42 ms**, 2 %-selective tag **0.041 ms**; unfiltered `COUNT(*) FROM documents` **0.004 ms**. `[VERIFIED: measured 2026-11-15]`
- `total_in_scope` = the same query without the filter (collection predicate only) — cheap and needed only for seeding.
- With no filter: **no pre-count, no extra query** (byte-identical default).
- The pre-count includes the collection predicate so `pre_count` is the true admitted document count; otherwise the stop condition and warning misfire when collections scope the search.
- If the pre-count is issued in `VectorSearcher`, an expanded hybrid query repeats it per variant (≤10 variants → ≤4 ms). Acceptable; alternatively compute once in `HybridSearcher`/pipeline and pass it down. This is a discretion area.

### "Too selective" warning (D-09)

Precondition is exactly measurable: **`pre_count >= page_target` AND `fetch_k` reached `_MAX_FETCH_K` AND `len(candidates) < page_target`**. Emit once per `VectorSearcher.search` via the module logger (stderr; `-q`-suppressible); never in results or `--json`. Measured both branches are constructible: a 2 %-selective 200-doc tag with `target=10` at `fetch_k=2048` finds ~41 matches → warning suppressed; a 1-in-10 000 filter finds ~0.2 expected matches → warning fires. The critical regression is the current loop, which would return short **without** ever hitting the ceiling — the corrected loop makes the warning truthful.

### Hybrid / pipeline passthrough

- `SearchOptions` gains `filter: FilterNode | None = None`; `dataclasses.replace` in `HybridSearcher.search` and `SearchPipeline.search` carries it automatically `[VERIFIED: src/sif/search/hybrid.py:82-86, 295-306]`.
- No fusion change: both legs receive `fetch_options` with the filter, so pre-RRF is structural.
- Early returns (one leg empty) paginate the single leg's filtered window `[VERIFIED: src/sif/search/hybrid.py:97-102]`.
- Rerank: the Phase 19 pre-window rule stays authoritative; a selective filter simply yields fewer candidates to rerank. No new window.
- `per_chunk` + filter: both legs filter; the chunk rows are already filtered at the document level. Add a contract note that `chunk_matches` counts filtered vector rows only.
- `search_chunks()` is called only by tests (`grep` found no production caller) `[VERIFIED: src/sif/search/bm25.py:186-220; tests/unit/search/test_bm25.py:268, 688]` — recommend leaving it filter-free and documenting that.

---

## Discovery Aggregates (FILT-05)

All queries read `document_metadata_values` (D-16). Use a region/CTE structure like qmd's, adapted to SIF's TEXT document ids:

1. **Eligible documents:** `documents` in scope (collection id / all), optionally narrowed by the compiled `filter` in **`corpus`** scope. Count `documents` (scope denominator) and `filteredDocuments` (when a filter is supplied).
2. **Key window:** `SELECT key, COUNT(DISTINCT document_id) AS documents FROM … GROUP BY key ORDER BY documents DESC, key ASC LIMIT ? OFFSET ?` — default sort is count desc, key asc (D-15). `totalKeys` = `COUNT(DISTINCT key)` before the window; `remainingKeys` = `totalKeys - offset - len(keys)` floored at 0.
3. **Per-type split:** `GROUP BY key, value_type` with `COUNT(DISTINCT document_id)`, `MIN(number_value)`, `MAX(number_value)`, and `MAX(ordinal) > 0 AS multiValued`.
4. **Distinct values with counts:** `GROUP BY key, value_type, text_value, number_value, boolean_value` with `COUNT(DISTINCT document_id)`; window per key/type; `remainingValues` = distinct count − offset − returned, floored at 0. `min_count` filters values by document count.
5. **Median (no JSON1):** window functions, exactly qmd's shape:

```sql
SELECT key, number_value FROM (
  SELECT key, number_value,
         ROW_NUMBER() OVER (PARTITION BY key ORDER BY number_value) AS position,
         COUNT(*)        OVER (PARTITION BY key)                    AS total
  FROM document_metadata_values
  WHERE value_type = 'number'
) WHERE position IN ((total + 1) / 2, (total + 2) / 2)
ORDER BY key, number_value
```

**Integer division is load-bearing:** `(total+1)/2` and `(total+2)/2` return one row for odd counts and two for even counts because SQLite divides integers as integers. Verified: `(4+1)/2=2, (4+2)/2=3, (3+1)/2=2, (3+2)/2=2` and a 4-row cohort returns positions 2 and 3. Compute the midpoint in Python (`(lower + upper) / 2.0`) to avoid SQL `SUM` overflow. `[CITED: qmd@86d2365 src/metadata-store.ts:826-850]` `[VERIFIED: measured 2026-11-15]`
6. **Skipped keys:** `SELECT COUNT(*) FROM document_metadata_skips` over the eligible region; report as `skippedKeys` (and optionally per reason).
7. **`match` predicate:** compile with the same compiler against the `mv` alias, entry scope (`field` ∈ {key, value}; reject `exists`/`all`). It narrows which entries are reported (and thus `totalKeys`/values) but not the document denominators.

Measured aggregate costs at 10 k docs / 27.7 k kv rows: key/type aggregation **9.4 ms**, value-count window **14.4 ms**, median **2.2 ms**. `[VERIFIED: measured 2026-11-15]` At 100 k docs this scales roughly linearly (100–150 ms) — acceptable for a discovery call; keep the key/value windows so result size is bounded.

Output shape recommendation (subject to D-15's locked names): `documents`, `filteredDocuments`, `totalKeys`, `remainingKeys`, `keys[]{key, documents, types[]{type, multiValued, documents, distinctValues, values[]{value, documents}, remainingValues, range?{min, median, max}}}` — this is qmd's shape `[CITED: qmd@86d2365 src/metadata-store.ts:270-310]` with the three remainder names D-15 pins in camelCase.

---

## CLI / MCP Surface Mechanics

### CLI

- Add `--filter` to all three result commands next to `--offset` / `--per-chunk` `[VERIFIED: src/sif/cli/commands/search.py:450-479, 637-672, 829-906]`.
- Parse with `json.loads`, validate with the shared entry point, and raise `click.ClickException` naming `filter.<path>: <message>` **before** `_pre_search_refresh` so a bad filter never pays a drift walk.
- `sif collection metadata [NAME]` belongs on the existing group `[VERIFIED: src/sif/cli/commands/collection.py:21-25]`; open with `open_initialized_database` like its siblings `[VERIFIED: src/sif/cli/commands/collection.py:138-181]`. Use the same renderers' conventions (Rich table default; `--json` / `--csv` / `--md` if the planner extends D-14's minimum).
- New flags/commands are auto-discovered by `scripts/generate_cli_ref.py` (Click introspection), but `docs/cli-reference.md` is generator-owned and must be regenerated with `make docs-generate`; `tests/test_docs.py::test_cli_reference_has_all_commands` fails until then.

### MCP

- **Tool execution error vs protocol error (verified):** `_handle_tools_call` returns `INVALID_PARAMS` only when the `ToolsCallParams` envelope fails to parse; unknown tools → `UNKNOWN_TOOL`; **any exception raised inside `handler.handle` becomes `ToolsCallResult(isError=True)` inside a successful JSON-RPC response** `[VERIFIED: src/sif/mcp/server.py:105-136]` `[VERIFIED: src/sif/mcp/protocol.py:170-174]`. D-17's requirement is therefore satisfied by validating inside the handler and returning/raising a message, never by `INVALID_PARAMS`. For clean message control, type the MCP `filter` field as `dict[str, Any] | None`, validate explicitly in the handler, and return `ToolsCallResult(..., isError=True)` on failure (the generic catch also works but logs "Tool execution error" with a stack trace).
- **Hand-written schema sync:** handlers declare `input_schema` as a `ClassVar` dict beside the pydantic input model; the comment culture requires them to stay in sync `[VERIFIED: src/sif/mcp/handlers.py:45-76]`. Add `"filter": {"type": "object"}` to `QueryToolHandler.input_schema` (and to the two unregistered inputs' models) — an unlisted property is invisible to MCP tool discovery.
- **Register the `metadata` tool now:** add `MetadataToolHandler` to `create_default_tools()` `[VERIFIED: src/sif/mcp/handlers.py:224-231]`. Tests asserting the exact tool set `{"query","get","multi_get","status"}` must be updated `[VERIFIED: tests/unit/mcp/test_integration.py:104, 305]`.
- **Backend:** add `SearchBackend.metadata(...)` using `_run_in_db` (fresh connection per call, thread) `[VERIFIED: src/sif/mcp/backend.py:134-141]`; add `filter` to `hybrid_search` and thread it into `SearchOptions` `[VERIFIED: src/sif/mcp/backend.py:143-191]`.
- **Frozen Phase 22 contract:** the `metadata` input/output schema shipped here is the cross-phase contract (STATE.md). Settle the single-`limit` ambiguity and the camelCase remainder names before writing it (Open Questions 4 and 8).

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| AST parsing/validation | A bespoke recursive parser over `dict` | Pydantic discriminated union on `operator` + one raw-dict budget pre-walk | Error paths (`loc` includes tags/indices), forward refs, and `union_tag_invalid` come free; the walk covers the budget message. |
| SQL string assembly | f-string interpolation of values | Parameterized compiler; params list in SQL order | Injection surface; D-17 and T-19-19 culture. |
| LIKE wildcard escaping | `LIKE` + `ESCAPE` | `instr()` / BLOB `substr()` (and a range for `path` prefix) | No escaping, exact case semantics, indexable where possible. |
| Median | Sorting values in Python or `AVG` over a subquery | The window-function middle-rows query + Python midpoint | qmd's proven shape; integer-division edge cases handled; no JSON1. |
| Typed metadata extraction | Re-parsing files at backfill | `json.loads(canonical_metadata_json(...))` over stored `documents.metadata` | No second checksum convention; the stored blob is already canonical. |
| Pydantic recursion safety | Trusting the parser with arbitrary depth | Raw-dict depth/node pre-walk before `model_validate` | pydantic converts `RecursionError` to `recursion_loop` at ~900 depth, but the error would not name the budget. |
| Discovery from the blob | `json_extract`/`json_each` | The same kv store filters read | D-16 / Pitfall 13: discovery must not lie about filterable keys. |
| Migration machinery | A new migration framework | `SchemaManager` detection gate + `index_meta` key | Phase 19 CR-01/D-09 pattern; every host already calls it. |

---

## Common Pitfalls (phase-specific, measured)

### Pitfall 1: The vector loop's saturation signal is post-JOIN (silent under-return)
**What goes wrong:** `len(rows) < fetch_k` is true whenever the JOIN filters rows, so a selective collection/metadata/path filter stops escalation on the first batch and returns fewer documents than exist.
**Evidence:** real `VectorSearcher`, 100 docs, 2-doc collection, `limit=10` → `['d0']`; `fetch_k=50` survivors 0, `fetch_k=100/200` survivors 2.
**Avoid:** when any JOIN filter is present, stop on target / pre-count / ceiling (see corrected loop); keep the old test only for the unfiltered path.
**Warning signs:** `tag:x` returns nothing while `sif ls` shows tagged docs; filtered vsearch recall collapses as selectivity rises.

### Pitfall 2: `LIKE` cannot use the BINARY path index by default
**What goes wrong:** `path LIKE ?` plans as `SCAN d`; `PRAGMA case_sensitive_like=ON` fixes it but changes global LIKE semantics.
**Avoid:** compile `path` `prefix` to a half-open range; use `instr`/`substr` elsewhere.
**Test:** assert the plan text contains `idx_documents_path` for the range and `SCAN` for a LIKE (documenting why we don't use it).

### Pitfall 3: Typed rows derived from the in-memory dict diverge from the backfill
**What goes wrong:** YAML dates are `datetime` objects live but ISO strings after canonical JSON; skipping them live and storing them in backfill (or vice versa) makes the store inconsistent and discovery counts wrong.
**Avoid:** one derivation over the canonical JSON string; add a regression with a date-valued key asserting live and backfill rows are identical.

### Pitfall 4: `schema_meta` does not exist
**What goes wrong:** D-06 says "a `schema_meta` marker"; the codebase has `index_meta` `[VERIFIED: src/sif/database/schema.py:186-199]`.
**Avoid:** write the marker to `index_meta`; do not create a second kv table.

### Pitfall 5: A filter that matches nothing must not become "no filter"
**What goes wrong:** an empty pre-count or an empty compiled fragment is treated as unfiltered, leaking every document.
**Avoid:** `filter is None` is the only unfiltered signal; pre-count 0 → `[]` before KNN; compiled fragment is appended whenever a filter exists (including an always-false predicate).
**Test:** filter `{"field":"nope","operator":"exists","value":true}` → empty page on all three commands and both legs.

### Pitfall 6: Budget enforcement happens after pydantic recursion
**What goes wrong:** a 900-deep AST raises `recursion_loop` (a ValidationError, measured) instead of "exceeds maximum nesting depth of 8".
**Avoid:** raw-dict iterative pre-walk (depth + node count + string/array lengths) before `model_validate`; keep pydantic for shape.

### Pitfall 7: Discovery reports keys that are not filterable (or misses filterable ones)
**What goes wrong:** skipped keys (nested object, null, mixed array, over-cap) have no kv rows, so a blob-based or silent-drop discovery lies.
**Avoid:** the skip sidecar + a test asserting both directions on a corpus containing one non-indexable key (counted, not reported as filterable).

### Pitfall 8: `ne`/`nin` compiled as bare `NOT IN`
**What goes wrong:** missing keys and type mismatches match `NOT IN` (NULL/absent semantics), violating parity.
**Avoid:** presence `EXISTS` + `NOT EXISTS(equal)`; test a document with the key absent and one with the wrong type.

### Pitfall 9: Parameter order in the BM25 SQL
**What goes wrong:** the filter params are appended in a different order than the placeholders appear (weights → match → collection → min_score → filter → limit/offset).
**Avoid:** append in SQL order and pin with a recording connection test (the existing `_RecordingConnection` pattern). `[VERIFIED: tests/unit/search/test_collection_filter.py:242-258]`

### Pitfall 10: Raw test inserts bypass the kv write path
**What goes wrong:** fixture builders insert documents with raw SQL, so filter tests see an empty kv store and pass/fail for the wrong reason.
**Avoid:** route fixture inserts through `DocumentRepository` or insert kv rows explicitly; add one integration test that builds a populated DB through `IncrementalIndexer` (the real path).

### Pitfall 11: Unfiltered defaults regress
**What goes wrong:** adding an unconditional pre-count/extra query/warning breaks the byte-identical-defaults culture.
**Avoid:** every filtered-only behavior gated on `filter is not None`; a test asserting the unfiltered path issues exactly the old statement(s) (recording connection) and emits no warning.

### Pitfall 12: Hand-written MCP schema drift
**What goes wrong:** a property accepted by the pydantic model but missing from `input_schema` is invisible to tool discovery.
**Avoid:** the existing sync tests (`test_input_schema_declares_offset`, `test_input_schema_declares_per_chunk_matching_the_model_default`) as the pattern; add `filter` assertions for `QueryInput`/`LexSearchInput`/`VecSearchInput` and the `metadata` tool.

### Pitfall 13: Docs gate
**What goes wrong:** new `--filter` and `collection metadata` are absent from `docs/cli-reference.md`.
**Avoid:** `make docs-generate` in the phase; never hand-edit the generated files.

### Pitfall 14: `--per-chunk` + filter interactions
**What goes wrong:** the "all matching docs found" stop uses row count and under-returns in per-chunk mode; `chunk_matches` counts unfiltered rows.
**Avoid:** distinct-document count for the stop; document that `chunk_matches` reflects only filtered rows.

### Pitfall 15: Numeric typing on round-trip
**What goes wrong:** a JSON `1` vs `1.0`, or a YAML date→string, silently changes the type a filter sees.
**Avoid:** derive types from the canonical JSON (`int`/`float` → number, `bool` → boolean, `str` → string); test integer and float equality and a bool-not-number case (`True` must not match `eq 1`).

---

## Code Examples

### 1. Recursive AST with one discriminator and a budget pre-walk

```python
# src/sif/core/filters.py  (prototype verified on pydantic 2.12.5 / 2.13.1)
from __future__ import annotations

from typing import Annotated, Any, Literal, Union

from pydantic import BaseModel, ConfigDict, Field, RootModel, TypeAdapter, model_validator

MAX_DEPTH, MAX_NODES, MAX_STRING, MAX_ARRAY = 8, 64, 1024, 128


class _Node(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Condition(_Node):
    field: str = Field(min_length=1, max_length=128)
    value: str | float | bool | list[str] | list[float] | list[bool]
    caseInsensitive: bool | None = None


class Eq(Condition):
    operator: Literal["eq"]


class Ne(Condition):
    operator: Literal["ne"]


class Gt(Condition):
    operator: Literal["gt"]


# … Gte/Lt/Lte, In/Nin/All, Contains/Prefix/Suffix, Type, Exists follow …


class And(_Node):
    operator: Literal["and"]
    operands: list["FilterNode"]


class Or(_Node):
    operator: Literal["or"]
    operands: list["FilterNode"]


class Not(_Node):
    operator: Literal["not"]
    operand: "FilterNode"


FilterNode = Annotated[Union[Eq, Ne, Gt, And, Or, Not], Field(discriminator="operator")]
And.model_rebuild(); Or.model_rebuild(); Not.model_rebuild()

_FILTER = TypeAdapter(FilterNode)


def _check_budgets(raw: Any) -> None:
    """Iterative raw-dict walk so over-budget errors name the budget."""
    stack = [(raw, 1)]
    nodes = 0
    while stack:
        node, depth = stack.pop()
        if not isinstance(node, dict):
            raise FilterValidationError("", "a filter node must be an object")
        nodes += 1
        if nodes > MAX_NODES:
            raise FilterValidationError("", f"filter exceeds the {MAX_NODES}-node budget")
        if depth > MAX_DEPTH:
            raise FilterValidationError("", f"filter exceeds the maximum nesting depth of {MAX_DEPTH}")
        children = node.get("operands") or ([node["operand"]] if "operand" in node else [])
        stack.extend((child, depth + 1) for child in children)


def parse_filter(payload: Any) -> FilterNode:
    _check_budgets(payload)
    return _FILTER.validate_python(payload)
```

Measured pydantic behavior: recursive validation works with forward refs; error `loc` includes the discriminator tag and list index, e.g. `('and','operands',0,'gt','value')`; an unknown tag yields `union_tag_invalid` naming the expected tags; ~900 depth yields `recursion_loop` (no raw `RecursionError` escapes). `[VERIFIED: prototyped 2026-11-15]`

### 2. Parameterized compiler fragment (shape)

```python
def _condition_sql(alias: str, cond, scope: str, params: list[Any]) -> str:
    if scope == "corpus":
        return (f"{alias}.id IN (SELECT mv.document_id FROM document_metadata_values mv "
                f"WHERE {_inner(cond, params)})")
    return (f"EXISTS (SELECT 1 FROM document_metadata_values mv "
            f"WHERE mv.document_id = {alias}.id AND {_inner(cond, params)})")
```

`_inner` binds `mv.key` first, then the operand(s), mirroring qmd `[CITED: qmd@86d2365 src/metadata-filter.ts:470-505]`.

### 3. Discovery median (no JSON1)

```sql
SELECT key, number_value FROM (
  SELECT key, number_value,
         ROW_NUMBER() OVER (PARTITION BY key ORDER BY number_value) AS position,
         COUNT(*)        OVER (PARTITION BY key)                    AS total
  FROM document_metadata_values
  WHERE value_type = 'number' AND key IN (SELECT value FROM …)  -- region/window
) WHERE position IN ((total + 1) / 2, (total + 2) / 2)
ORDER BY key, number_value
```

### 4. Backfill loop (sketch)

```python
def _backfill_metadata_values(self) -> None:
    marker = IndexMetaRepository(self.db)
    if marker.get(_METADATA_VALUES_VERSION_KEY) == _METADATA_VALUES_VERSION:
        return
    rows = self.db.execute("SELECT id, metadata FROM documents").fetchall()
    if rows:
        logger.warning("Upgrading index format: deriving typed metadata for %d documents once", len(rows))
    repo = MetadataValueRepository(self.db)
    for doc_id, metadata_json in rows:
        with self.db:                      # one short transaction per document
            repo.replace_from_canonical(doc_id, metadata_json)
    with self.db:
        marker.set(_METADATA_VALUES_VERSION_KEY, _METADATA_VALUES_VERSION)
```

---

## Runtime State Inventory

> This phase is not a rename, but it ships a **data migration** and depends on runtime state outside git. Categories answered explicitly.

| Category | Items found | Action required |
|----------|-------------|-----------------|
| **Stored data** | `documents.metadata` (canonical JSON, every existing DB); new `document_metadata_values` (+ skip sidecar); `index_meta` marker | Backfill derives kv rows from `documents.metadata` in place. No file re-parse. Marker write is the completion contract. |
| **Live service config** | None — no external service holds SIF metadata. n8n/Datadog-style config does not exist here. | None. |
| **OS-registered state** | None — no task scheduler/launchd/systemd entry embeds metadata keys or the new table names. | None. |
| **Secrets and env vars** | None — no new env var or secret; no setting is added (budgets are constants). | None. |
| **Build artifacts / installed packages** | `docs/cli-reference.md` is generated (must be regenerated); no compiled artifacts, no egg-info change. Existing databases are the only installed-state artifact. | `make docs-generate`; backfill on first `init_schema`. |

---

## State of the Art

| Old approach | Current approach | When changed | Impact |
|--------------|------------------|--------------|--------|
| Flat key=value filters | Recursive boolean AST with typed operators | qmd `[Unreleased]` (2026); ES/Weaviate/Meili have equivalents | Agents compose filters; one grammar across CLI/SDK/MCP/HTTP. |
| JSON-blob scanning (`json_extract`) | Typed kv rows rebuilt per document | qmd metadata store; SIF Phase 20 | Typed ranges + cheap discovery aggregates; no JSON1 dependency at read time. |
| Post-fusion filtering | Pre-RRF per-leg pushdown | Locked research | Honest top-K and no wasted rerank. |
| Full KNN then filter with fixed 4× | Adaptive over-fetch + selectivity pre-count + honest ceiling | Phase 19 loop + this phase | Selective filters no longer under-return silently; bounded work. |
| Hand-rolled MCP server tool errors as protocol faults | Tool execution errors (`isError`) for model self-correction | SEP-1303 (2025-11-25) | Invalid filters are recoverable, not session-breaking. |

**Deprecated/outdated:**
- The docs commit `abfabc5`'s `"key"` field name — superseded by `"field"`.
- `LIKE 'prefix%'` on `documents.path` as a filter primitive — cannot use the BINARY index under default pragmas.
- Bare `NOT IN` for `ne`/`nin` — wrong for missing keys and type mismatches.

---

## Assumptions Log

> Claims tagged `[ASSUMED]` — the planner/discuss-phase should confirm before locking.

| # | Claim | Section | Risk if wrong |
|---|-------|---------|---------------|
| A1 | The parity target should use `field` (current main), not `key` (docs commit). | qmd Parity Contract | If the user pinned the docs-commit era, every example/schema would use the wrong property name; a rename later is a breaking grammar change. |
| A2 | qmd's `contains` on an array field is substring-any-per-element (not D-11's "membership"). | Semantics table / Open Q2 | Implementing membership narrows parity; implementing substring-any conflicts with a literal reading of D-11. |
| A3 | A `qmd.metadata` collision with a native frontmatter key should resolve in the namespace's favor. | `qmd.metadata` Resolution | The opposite rule changes which value users filter on; needs a recorded decision. |
| A4 | Discovery's single `limit` pages **keys**, with a fixed value window (qmd's 10). | Discovery / Open Q4 | The frozen Phase 22 schema would expose the wrong paging semantics; `remainingValues` would be uninformative. |
| A5 | A separate skip sidecar table is preferred over sentinel rows in the value table. | Typed KV Storage | A one-table design can work but must exclude sentinels from `exists`/`type` everywhere. |
| A6 | The `metadata` CLI command should accept `--filter` as well as `--match` (qmd does; D-14's list omits it). | CLI Surface / Open Q6 | Without `--filter`, CLI discovery cannot answer "what remains after narrowing", which the MCP tool can. |
| A7 | A full synchronous backfill on first `init_schema` is acceptable at personal-KB scale (≈1–2 min at 100 k docs). | Backfill Design | On a very large KB the first post-upgrade command blocks; a bounded/resumable variant would be needed. |
| A8 | `search_chunks()` should stay filter-free (no production caller). | Hybrid passthrough | If a caller appears, chunk-level BM25 would ignore filters. |
| A9 | The plan may add a skip sidecar table without a new Settings field (no docs-config gate). | Typed KV Storage | If a setting is added, `docs/configuration.md` must be regenerated too. |
| A10 | qmd's exact vector-filter strategy ("scan eligible set ≤20 000 chunk vectors, else over-fetch/post-filter") is not adopted; SIF keeps D-08. | Parity deltas | No risk — locked decision; listed so the planner does not copy it. |

---

## Open Questions

1. **AST field name: `field` vs `key`.**
   - What we know: current qmd main + pinned clone use `field`; the docs commit `abfabc5` used `key`. qmd is unreleased and may shift again.
   - Recommendation: use `field`, pin the parity target to the current `[Unreleased]` era, and record the delta from `abfabc5` in the plan/SUMMARY. If the user's parity contract was written against the older docs, confirm before building.

2. **`contains` on arrays: substring-any (qmd) vs membership (D-11).**
   - What we know: qmd evaluates text operators per string value, so `contains: "sql"` matches an element `"sqlite"`. D-11 says "membership on arrays".
   - Recommendation: implement qmd's substring-any semantics (SC-1 says "qmd semantics verbatim"), note that it is a superset of membership, and record the reading in the plan. Confirm with the user if D-11's wording is considered binding.

3. **Collision precedence for `qmd.metadata` vs native frontmatter.**
   - Recommendation: namespace wins on collision (explicit opt-in / migration parity); document it in the discovery description. Needs a recorded decision because "one flat key space" does not state the winner.

4. **What does the discovery tool's single `limit` page?**
   - What we know: qmd has `keyLimit` (50) and `valueLimit` (10) separately; D-15 locks one `limit`.
   - Recommendation: `limit` = key-window size (default 50); a fixed internal value window of 10 per key/type; `remainingValues` exact. Alternatively interpret `limit` for both. Must be settled before freezing the Phase 22 schema.

5. **Skip accounting shape.**
   - Recommendation: `document_metadata_skips` sidecar (per key + reason); discovery reports `skippedKeys`. If the planner prefers one table, sentinel rows must be excluded from `exists`/`type` in the compiler.

6. **Should `sif collection metadata` have `--filter`?**
   - Recommendation: yes (qmd parity, D-15 filter-aware coverage, one validator). D-14's option list does not mention it, so treat as an additive decision.

7. **Backfill startup cost / bounded pass.**
   - Recommendation: full synchronous pass with per-document commits and a one-line notice; measure on a populated fixture. If unacceptable, a bounded pass plus a "metadata index upgrading" guard is needed — but never expose a half-populated filter store.

8. **Remainder field casing.**
   - D-15 names `totalKeys`/`remainingKeys`/`remainingValues` in camelCase while SIF MCP outputs are snake_case (`doc_id`, `collection_name`). Recommendation: follow D-15 literally for those three names (they are the frozen contract) and document the mixed casing; confirm at plan time.

---

## Environment Availability

| Dependency | Required by | Available | Version | Fallback |
|------------|-------------|-----------|---------|----------|
| Python | whole project | ✓ | 3.13.9 (`.venv`), PATH/miniconda 3.13.9; floor `>=3.10` | — |
| SQLite (stdlib) | FTS5, window fns, MATERIALIZED | ✓ | 3.51.0 (both interpreters); needs ≥3.35 (already required by existing code) | — |
| sqlite-vec | vec0 KNN tests/results | ✓ | 0.1.9 (lock; both envs import it) | Tests skip when absent; production degrades MCP to BM25 (Phase 10 WR-08 carve-out). |
| pydantic | AST models | ✓ | lock 2.13.1; `.venv` 2.13.1; PATH/miniconda 2.12.5 | pyproject floor `>=2.0.0`; prototype runs on both. |
| pytest / pytest-asyncio | tests | ✓ | PATH pytest 9.1.1; `pytest-asyncio>=0.23.0` | — |
| ruff / ty | quality gate | ✓ (project deps) | — | — |
| SQLite window functions (`ROW_NUMBER`, `COUNT OVER`) | discovery median/remainders | ✓ | ≥3.25 (2018) | — |

**Missing dependencies with no fallback:** none.
**Missing dependencies with fallback:** sqlite-vec on a host without it (tests skip; MCP search degrades; discovery and BM25 filtering still work).

---

## Validation Architecture

> `workflow.nyquist_validation` is `true` in `.planning/config.json` — section required.

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 9.1.1 (PATH), pytest-asyncio, pytest-cov |
| Config file | `pyproject.toml` `[tool.pytest.ini_options]` (`--cov=src/sif`, `fail_under=90`), no separate `pytest.ini` |
| Quick run command | `pytest tests/unit/core/test_filters.py tests/unit/search/test_filters_sql.py tests/unit/database/test_metadata_values.py -x` |
| Full suite command | `pytest` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test type | Automated command | File exists? |
|--------|----------|-----------|-------------------|--------------|
| FILT-01 | Valid/invalid AST shapes, all 17 operators, typed exact match, no coercion, missing keys don't match `ne`/`nin`, arrays as sets, no implicit AND, `caseInsensitive` ASCII-only, budgets (depth 8 / 64 nodes / 1024 chars / 128 elems) | unit | `pytest tests/unit/core/test_filters.py -x` | ❌ Wave 0 (new `tests/unit/core/`) |
| FILT-01 | Same validator drives CLI and MCP; CLI invalid filter → `ClickException` naming operator/field/path; MCP invalid filter → `isError=True` never `INVALID_PARAMS` | unit | `pytest tests/unit/cli/test_search_filter.py tests/unit/mcp/test_backend.py::TestFilterErrors -x` | ❌ Wave 0 (extend existing files) |
| FILT-02 | `path` prefix range plan uses `idx_documents_path`; mtime range uses `idx_documents_mtime`; reserved-name shadowing; ordering on path is a validation error | unit + plan | `pytest tests/unit/search/test_filters_sql.py -x` | ❌ Wave 0 |
| FILT-03 | BM25 filtered plan keeps `MATERIALIZE matched` and no `:=`; predicate sits in outer WHERE (recording connection); parameterized SQL string shape unchanged under `'`, `;`, `--`, `%` values | unit | `pytest tests/unit/search/test_bm25.py::TestBM25FilterPushdown tests/unit/search/test_filters_sql.py -x` | ❌ Wave 0 (extend `test_bm25.py`, `test_collection_filter.py`) |
| FILT-03 | `filtered-hybrid ⊆ unfiltered-hybrid ∩ filter-set`; filters that admit everything reproduce the unfiltered page; ~2 % selectivity returns the matching docs (not empty); filter × collection × pagination composition | integration/property | `pytest tests/integration/test_metadata_filtering.py -x` | ❌ Wave 0 (mirror `tests/integration/test_search_correctness.py`) |
| FILT-03 | Too-selective warning fires (many matches, ceiling hit) and is suppressed (few matches, short page); empty match → empty page on both legs | unit | `pytest tests/unit/search/test_vector.py::TestVectorFilteredRecall -x` | ❌ Wave 0 (extend existing class; the existing class must gain the large-corpus case) |
| FILT-04 | Typed rows written on create/update/full-path/metadata-fast-path; numeric compares as number; bool is not number; date-valued key live == backfill; `qmd.metadata` resolves identically to native keys; reserved names shadowed | unit | `pytest tests/unit/database/test_metadata_values.py tests/unit/indexing/test_incremental.py -x` | ❌ Wave 0 (new file + extend) |
| FILT-04 | Backfill on a populated DB: marker written only after a complete pass; interrupt mid-pass; re-run does not duplicate; fresh DB zero cost; marker survives reopen | unit | `pytest tests/unit/database/test_schema.py -x` | ❌ Wave 0 (extend) |
| FILT-05 | Discovery doc counts, per-type split, numeric min/median/max (odd/even cohorts, array elements each count), distinct value counts, exact `totalKeys`/`remainingKeys`/`remainingValues`, filter-aware denominator, skipped-key count, match grammar (key/value; exists/all rejected) | unit | `pytest tests/unit/database/test_metadata_values.py::TestDiscovery -x` | ❌ Wave 0 |
| FILT-05 | CLI `collection metadata` table/JSON + options; MCP `metadata` tool registered, input_schema in sync, invalid filter/match → `isError` | unit/integration | `pytest tests/unit/cli/test_collection.py tests/unit/mcp/test_integration.py -x` | ❌ Wave 0 (extend; update exact tool-set assertions at `test_integration.py:104,305`) |
| FILT-05 | Discovery never lies: every reported key is filterable; every filterable key appears; a non-indexable key is counted, not silently dropped | integration | `pytest tests/integration/test_metadata_filtering.py::TestDiscoveryParity -x` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** the quick run command above (filter/compiler/storage units).
- **Per wave merge:** `pytest` (full suite; `fail_under=90` active).
- **Phase gate:** `ruff check src tests`, `ruff format --check src tests`, `ty check src/sif`, `pytest` — all green before `/gsd-verify-work`. Also `make docs-generate` and a clean `git diff` on `docs/cli-reference.md`.

### Wave 0 Gaps
- [ ] `tests/unit/core/test_filters.py` — new; AST/operator/budget coverage (FILT-01).
- [ ] `tests/unit/search/test_filters_sql.py` — new; compiler fragments, plan assertions, injection-shaped values (FILT-02/03).
- [ ] `tests/unit/database/test_metadata_values.py` — new; typed rows, canonical derivation, discovery aggregates, backfill (FILT-04/05).
- [ ] `tests/integration/test_metadata_filtering.py` — new; real-schema containment invariant, 2 % selectivity, composition, discovery parity (FILT-03/05).
- [ ] Extend `tests/unit/search/test_bm25.py`, `tests/unit/search/test_vector.py`, `tests/unit/search/test_hybrid.py`, `tests/unit/indexing/test_incremental.py`, `tests/unit/database/test_schema.py`, `tests/unit/cli/test_search.py`, `tests/unit/cli/test_collection.py`, `tests/unit/mcp/test_backend.py`, `tests/unit/mcp/test_integration.py`.
- [ ] Fixture support: extend `tests/support/bench.py::build_bench_db` (route through `DocumentRepository` or insert kv rows) so the 150-document corpus is filterable; `ConceptEmbedder` remains the hermetic embedder `[VERIFIED: tests/support/bench.py:40-64, 98-170]`.
- [ ] Framework install: none (pytest/pytest-asyncio present).

---

## Security Domain

> `security_enforcement` is not disabled in `.planning/config.json` (key absent → enabled).

### Applicable ASVS Categories

| ASVS category | Applies | Standard control |
|---------------|---------|------------------|
| V2 Authentication | no | Loopback, unauthenticated personal server (existing design). |
| V3 Session Management | no | No sessions; MCP stdio/HTTP loopback. |
| V4 Access Control | no | Single-user local index; collection scoping is a search feature, not authz. |
| V5 Input Validation | **yes** | Pydantic discriminated union + raw-dict budget pre-walk + ISO/epoch parse for `mtime`; unknown properties rejected; field/string/array caps. |
| V6 Cryptography | no | No new crypto; never hand-roll. |
| V12 Files & Resources | partial | `path` filters only scope indexed rows; they never touch the filesystem. Discovery/`multi_get` behavior unchanged. |

### Known Threat Patterns for this stack

| Pattern | STRIDE | Standard mitigation |
|---------|--------|---------------------|
| SQL injection via filter field/key/value | Tampering | Parameterized compiler only; no interpolation (T-19-19 precedent). Test values containing `'`, `;`, `--`, `%` and assert the SQL *shape* is unchanged while params carry the literal. |
| Resource exhaustion via unbounded AST | Denial of service | Depth ≤8, nodes ≤64, string ≤1024, array ≤128; unknown properties rejected; raw pre-walk before pydantic recursion. |
| Resource exhaustion via selective filter forcing a deep KNN scan | Denial of service | Pre-count + `_MAX_FETCH_K = 2048` ceiling + "too selective" warning; offset cap unchanged. |
| Discovery amplification (huge value sets) | Denial of service | Key/value windows + exact remainders; `min_count`; never `--all` by default. |
| Malicious frontmatter crashing indexing | Tampering / DoS | Per-key skipping (D-07) inside the existing per-file error isolation; nested/null/mixed arrays never reach SQLite bind as un-bindable values. |
| Stdout pollution breaking MCP framing | Integrity | Warnings/notices on stderr via the logger; never in `--json`/MCP text content. |
| Filter silently dropped → unintended data exposure across scopes | Information disclosure | `filter is None` is the only unfiltered signal; empty match returns `[]`; both legs receive the same AST. |

---

## Sources

### Primary (HIGH confidence — read directly)
- `src/sif/database/schema.py` (tables, indexes, `index_meta`, `drop_all`) — read this session.
- `src/sif/database/repositories.py` (`canonical_metadata_json` write sites, `IndexMetaRepository`).
- `src/sif/database/factory.py` (`PRAGMA foreign_keys = ON`).
- `src/sif/core/models.py` (`canonical_metadata_json`, `SearchOptions`, `SearchResult`).
- `src/sif/indexing/parser.py` (`CONVENTION_VERSION`, parser dispatch).
- `src/sif/indexing/incremental.py` (fast path, full path, `convention:<id>` marker).
- `src/sif/search/bm25.py`, `vector.py`, `hybrid.py`, `rrf.py`, `context_attach.py`.
- `src/sif/mcp/protocol.py`, `handlers.py`, `backend.py`, `server.py`.
- `src/sif/cli/commands/search.py`, `collection.py`, `error_handling.py`.
- `tests/unit/search/test_collection_filter.py`, `test_vector.py`, `test_bm25.py`; `tests/support/bench.py`; `tests/integration/test_search_correctness.py`; `tests/unit/mcp/test_server.py`, `test_integration.py`; `tests/test_docs.py`.
- Local measurements: SQLite 3.51.0 scratch DB + real `VectorSearcher` (scripts under `/tmp/sif_probe/`), 2026-11-15.

### Secondary (MEDIUM confidence — official external docs, cross-checked)
- qmd `[Unreleased]` CHANGELOG: `https://raw.githubusercontent.com/tobi/qmd/main/CHANGELOG.md` (fetched 2026-11-15).
- qmd README main: `https://raw.githubusercontent.com/tobi/qmd/main/README.md` (fetched 2026-11-15).
- qmd docs commit: `https://github.com/tobi/qmd/commit/abfabc5424623046069c42705682c9da0966511a` (fetched as a patch 2026-11-15).
- qmd source at `86d2365d17fc682e491c2c53d1e4a884aee8682a` (2026-10-14), read from a shallow clone: `src/metadata-filter.ts`, `src/metadata-store.ts`, `src/metadata.ts`, `src/mcp/server.ts`, `src/cli/qmd.ts`, `README.md`.
- SQLite query-planner docs: `https://www.sqlite.org/optoverview.html` §5 (LIKE/GLOB optimization).
- Pydantic unions docs: `https://pydantic.dev/docs/validation/latest/concepts/unions/` (fetched 2026-11-15).

### Tertiary (LOW confidence — not used for plan decisions)
- deepwiki `3.7-metadata-and-frontmatter-filtering`: HTTP 429 on 2026-11-15; **not retrieved, not cited**.
- Research-seam confidence classifications returned `LOW` for `webfetch`/`local` providers; actual provenance is stated per claim above instead.

---

## Metadata

**Confidence breakdown:**
- Standard stack: **HIGH** — no new dependencies; versions read from `pyproject.toml`/`uv.lock` and both local environments.
- Codebase seams / storage design: **HIGH** — files read directly this session; FK cascade and canonical-JSON behavior quoted and measured.
- SQL plans / costs / vector under-return: **HIGH** — measured on SQLite 3.51.0 with the real `VectorSearcher`.
- qmd parity: **MEDIUM** — current main README + pinned clone source agree, but the target is `[Unreleased]`; the docs commit used a different field name; the README documents no filter budgets (source does).
- Pitfalls: **HIGH** for measured items (1, 2, 3, 5, 9, 10, 11); **MEDIUM** for behavior inferred from code without a failing test (4, 6, 7, 8, 12–15).

**Research date:** 2026-11-15
**Valid until:** ~2026-12-15 for the codebase/measurements; **re-verify qmd parity on any plan/execute run** because the parity target is unreleased and has already changed field naming once.
