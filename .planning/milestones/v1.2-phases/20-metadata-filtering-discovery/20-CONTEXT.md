# Phase 20: Metadata Filtering + Discovery - Context

**Gathered:** 2026-11-15
**Status:** Ready for planning

<domain>
## Phase Boundary

The milestone's precision phase — make search scoped and queryable by metadata, applied before fusion so top-K stays honest, and make the available metadata discoverable so agents never guess keys. Delivers exactly FILT-01..FILT-05:

1. **Filter AST (FILT-01)** — one recursive JSON AST discriminated by `operator` (`and`/`or`/`not`, `eq`/`ne`/`gt`/`gte`/`lt`/`lte`, `in`/`nin`/`all`, `contains`/`prefix`/`suffix`, `type`, `exists`, plus optional `caseInsensitive`), qmd semantics verbatim, shared by CLI `--filter <json>` and the MCP `filter` param through ONE validator.
2. **Built-in fields (FILT-02)** — `path` and `mtime` as reserved filter fields riding the same operators; strictly more expressive than qmd's frontmatter-only AST. Both columns already exist and `idx_documents_mtime` already landed in Phase 19 — no new column or index work remains.
3. **Pre-RRF pushdown (FILT-03)** — the compiled predicate is applied inside each leg before fusion: BM25 as an outer WHERE of the existing materialized CTE (never inside it), vector as a post-KNN JOIN with adaptive over-fetch, a selectivity bound, and an honest "too selective" notice; parameterized SQL only, never post-fusion filtering, never SQL passthrough.
4. **Typed frontmatter storage (FILT-04)** — typed kv storage for pushdown and discovery, backfilled on upgrade, with the `qmd.metadata` namespace read for migration parity (opt-in by document, not by setting).
5. **Discovery tool (FILT-05)** — a `metadata` tool on CLI and MCP reporting doc counts, numeric min/median/max, and exact remainders, sharing the filter validator; invalid filters surface as tool execution errors so a model can self-correct.

NOT in scope: post-fusion filtering, SQL/string passthrough, nested frontmatter objects, faceted UI, saved filters, glob/regex path operators, `title`/`collection` as built-in fields, MCP SDK v2 shell swap (Phase 22), scale/scan elimination (Phase 21), Harrier evaluation (Phase 23), chunking/title-breadcrumb sweeps (Phase 24). No new runtime dependencies.

</domain>

<decisions>
## Implementation Decisions

### Filter surface coverage (discussed)
- **D-01:** **`--filter <json>` on every CLI result command** — `sif search` (BM25), `sif vsearch` (vector), `sif query` (hybrid). Same flag name, same grammar, same semantics everywhere; `get`/`multi-get`/`ls` are untouched. — **Reversibility:** costly — these are public CLI surfaces; a shipped flag is a compatibility commitment and removing it breaks scripts.
- **D-02:** **`filter` on all three MCP search inputs** — `QueryInput`, `LexSearchInput`, `VecSearchInput`, mirroring Phase 19's D-05 offset precedent, even though lex/vec tool registration stays Phase 22. Phase 22's parity work then has no filter-schema gap to fill. The new `metadata` tool is registered now on the hand-rolled server, and its input/output schema is frozen as the Phase 22 contract (STATE.md cross-phase contract: "`metadata` tool schema (20 → 22)"). — **Reversibility:** costly — public MCP tool schema consumed by agents.

### Field space and collisions (discussed)
- **D-03:** **Exactly two reserved built-in fields: `path` (string) and `mtime` (number).** A frontmatter key named `path` or `mtime` is shadowed and is not filterable; discovery reports both as built-in, never as frontmatter keys. No `collection` AST field — the existing `--collection`/`collections` parameter remains the scoping mechanism and ANDs with the filter. — **Reversibility:** costly — the reserved-name set is part of the public filter grammar.
- **D-04:** **No built-in `tags`/`tag` alias.** Tags are ordinary frontmatter; arrays are sets, so `contains`/`all` cover them. A `tag` alias that merged `tags`/`tag`/`keywords` would be invented semantics with no parity target. — Rationale: PROJECT.md's milestone wording "path/mtime/tag/frontmatter" describes user-facing capability, not a reserved-field list; the roadmap's FILT-02 names only `path`/`mtime`.

### Typed storage and migration (discussed)
- **D-05:** **Typed kv rows are written in the same transaction as the document row** — delete-then-insert per document, on both the full body-change path and the Phase 19 metadata fast path (D-07 there). FK `ON DELETE CASCADE` on document delete so `collection remove` needs no extra work. The kv payload is derived from the SAME canonical serializer that produces `documents.metadata` (Phase 19 19-01 decision), so the hashed, stored, and typed views can never disagree. No JSON1 dependency is introduced — no `json_each`/`json_extract` anywhere on the read or write path. — **Reversibility:** costly — a new schema surface every write path must maintain.
- **D-06:** **Backfill is an in-process Python pass over stored canonical `documents.metadata`** — no file re-parse, no forced reindex, no second checksum-convention change. Phase 19 already forced one full re-parse, and `documents.metadata` is canonical JSON as of then, so the typed rows are derivable from the DB alone. Runs inside `SchemaManager`'s idempotent, detection-gated machinery (CR-01 pattern), in per-document short transactions so it is resumable; the marker is a **global `metadata_values_version` key in the existing `index_meta` kv table** (the research corrected an earlier `schema_meta` slip — no such table exists), written only after a fully successful pass; fresh DBs and already-backfilled DBs pay zero cost. **Filtering must never be enabled against a half-populated store** — a partial store silently under-returns, so the pass either completes or the filter surface stays closed for that run. Announced once on stderr, reusing the existing notice conventions. — **Reversibility:** costly — the marker is a one-time migration contract; changing the backfill later needs a new migration.
- **D-07:** **Non-indexable frontmatter is skipped per key, not per document** — nested objects, nulls, mixed-type arrays, and values over the caps (≤ 64 keys per document, key ≤ 128 bytes, string ≤ 1024 chars, array ≤ 128 elements, frontmatter ≤ 64 KB — the first cap is added to match qmd's `maxKeys`) make THAT key absent from the typed store; the document still indexes, stays findable unfiltered, and keeps its other keys filterable. Skip accounting lives in a small `document_metadata_skips` sidecar (key + reason) rather than sentinel value rows, so the compiler's `exists`/`type` operators never have to special-case a fake row; discovery reports the skipped-key count so silence is impossible. A frontmatter key shadowed by a reserved built-in (`path`/`mtime`, D-03) is **not** a skip — it is reserved, and discovery reports the built-in. Deliberate deviation from qmd's whole-document exclusion: same filter outcome for the offending key, strictly less surprising for the user. — Rationale: qmd's exclusion interacts badly with SIF's personal-KB corpus where one bad note should not vanish from filtered search.

### Vector-leg selectivity (discussed)
- **D-08:** **One cheap selectivity pre-count per filtered search, reusing the existing escalation loop and hard ceiling.** `SELECT COUNT(*)` over the same compiled predicate (mtime/path indexes + kv joins) tells the leg how many documents match; the existing Phase 19 doubling loop (`fetch_k` from `min(max(target*4, 50), 2048)`, doubling while saturated) is reused unchanged, and `_MAX_FETCH_K = 2048` stays the independent work ceiling (T-19-13: a huge offset must not become unbounded work). No filters → no pre-count, zero cost. — **Reversibility:** reversible.
- **D-09:** **"Too selective" is a stderr warning, never an error.** Emitted once, only when the filter's matching-document count is at least the requested page target AND the vector batch exhausted the ceiling before filling it — i.e. recall is provably incomplete. When the filter genuinely matches fewer documents than requested, the short page is honest and the warning is suppressed. This mirrors qmd's documented caveat ("highly selective filters remain best-effort for top-K completeness"). Warnings go to stderr only, never into `--json`/MCP stdout or the result list. — **Reversibility:** reversible.

### AST semantics and typing (discussed)
- **D-10:** **qmd's 17 operators verbatim, plus `caseInsensitive` (ASCII folding only) on any condition whose value is a string or a string array** (the research found qmd's scope is both; an earlier draft of this decision said string-only). Typed exact match with no coercion; missing keys do not match `ne`/`nin` (use `or` + `exists:false`); arrays are sets; no implicit AND between top-level conditions. ONE Pydantic discriminated union on `operator` is the single grammar shared by the CLI, the MCP inputs, and the discovery tool's filter-aware mode. **D-18 fixes the condition field name to `field`** (below). — **Reversibility:** costly — operator semantics are a public contract once shipped; relaxing them later is breaking.
- **D-11:** **Ordering operators are numeric-only.** `gt`/`gte`/`lt`/`lte` accept numbers (`mtime` and numeric frontmatter); a string, boolean, or array operand with an ordering operator is a validation error naming the field and operator — never a lexicographic surprise. **`contains` follows qmd verbatim: substring on a string value, evaluated per element on an array (substring-any)** — an earlier draft of this decision said "membership on arrays", but membership is what `in`/`all` express, and success criterion 1 requires qmd semantics verbatim. `all` means array-contains-every-operand; `in`/`nin` test a scalar against a list. Adding lexicographic string ordering later is purely additive.
- **D-12:** **`mtime` accepts epoch seconds OR an ISO-8601 date/datetime string**, parsed to epoch at validation time; the stored and compared value stays numeric, so this is a field-aware input parse, not a comparison coercion. Rationale: humans typing `--filter '{"mtime":{"gte":"2026-01-01"}}'` is the primary CLI use; agents can pass epoch. — **Reversibility:** costly — accepting ISO becomes an input contract; dropping it later breaks scripts.
- **D-13:** **Explicit AST budgets, enforced by the shared validator:** depth ≤ 8, ≤ 64 nodes, string operand ≤ 1024 chars, array operand / `in`-list ≤ 128 elements. Over-budget is a validation error naming the budget. There is deliberately no "unbounded" escape: the budgets are the only defense against a hostile or runaway agent-authored filter, and they are set generously enough that no hand-written filter hits them. — **Reversibility:** costly — tightening a shipped budget is breaking; these are chosen loose, so future tightening is unlikely to be needed.

### Discovery surface (discussed)
- **D-14:** **CLI is `sif collection metadata [NAME]`** (qmd CLI parity) — no NAME means all collections. Options: `--filter` (filter-aware coverage, same validator), `--match` (filter entries by key or value), `--min-count`, `--sort count|value`, `--limit` (the **key** window, default 50), `--value-limit` (the per-key value window, default 10), `--json`. Default rendering is a table; JSON/CSV/Markdown follow the existing output conventions. A top-level `sif metadata` alias is not shipped (additive later if it earns its keep).
- **D-15:** **MCP `metadata` tool inputs are `{collections?, filter?, match?, min_count?, sort?, limit?, value_limit?}`** — `limit` pages the key list (default 50), `value_limit` windows each key's value list (default 10), and both remainders are reported exactly. Each key reports: document count (counts are documents, not values), per-type split for mixed-type keys with counts per type, numeric min/median/max (median over value rows, so array elements each count), and distinct values with counts plus the camelCase exact remainders `totalKeys`, `remainingKeys`, `remainingValues` (qmd contract; the mixed casing against SIF's snake_case outputs is deliberate and is part of the frozen Phase 22 schema). Deterministic ordering: count desc, then key asc. When `filter` is supplied, all counts are measured against the admitted document set (filter-aware coverage, qmd parity). — Rationale: the schema is frozen for Phase 22; exact remainders let an agent budget pagination instead of guessing.
- **D-16:** **Discovery reads the same kv store the filters use** — never `json_extract` on the blob, never a second source of truth. This is the research Pitfall 13 invariant: a discovery tool that reports from a different store than the filter reads can lie about what is filterable.

### Error surfaces and composition (discussed)
- **D-17:** **Invalid filters fail as user input, never as a protocol fault.** CLI raises `click.ClickException` naming the offending operator, field, and its path inside the AST (e.g. `filter.tags.gt: "gt" requires a numeric value`). MCP returns `ToolsCallResult(isError=True)` with the same message — a tool execution error (SEP-1303) so the model can self-correct; never a JSON-RPC `INVALID_PARAMS` protocol error. Filter composes by AND with `--collection`, `--min-score`, `--offset`, `--per-chunk`, and reranking; both legs receive the same compiled predicate; an empty filter match set returns an empty page and must never degrade to "no filter" (extends the exclude-all sentinel contract in `bm25.py:70-71` / `vector.py:58-59`). — **Reversibility:** reversible.

### Research reconciliations (2026-11-15 — resolved after the researcher read the pinned qmd source)
- **D-18:** **The condition field name is `field`, not `key`.** Current qmd main and the pinned clone (`qmd@86d2365`, `src/metadata-filter.ts:264-266`) both use `field`; the older docs commit `abfabc5` used `key` and is superseded. Group nodes take `operands` (array), `not` takes `operand` (singular), conditions take `field` + `operator` + `value` + optional `caseInsensitive`. Pin the parity era explicitly in the plan and record the `abfabc5` delta in the SUMMARY — qmd is unreleased and may shift again. — **Reversibility:** costly — the wire grammar is what agents will author filters in.
- **D-19:** **`qmd.metadata` wins on collision with a native top-level key.** Resolution happens in a derived view over the canonicalized metadata mapping (not in `parser.py`, not in the checksum path), so a document that opts into the namespace is interpreted the way qmd would interpret it. Native top-level keys fill every key the namespace does not define. A SIF-native document with no `qmd.metadata` block is unaffected, so existing indexes stay byte-identical. — Rationale: FILT-04's stated purpose is migration parity; if a migrated qmd document carried both forms, letting the native key win would silently diverge from the tool it was migrated from.

### Discovery envelope amendment (revision 2026-11-15)
- **D-20:** **D-15's discovery envelope is extended additively with a top-level `builtIns` list to satisfy D-03.** It holds exactly two entries — `path` (string) then `mtime` (number, carrying a numeric `range`) — computed from the `documents` columns over the same eligible, filter-aware region, never from `document_metadata_values`, and never listed in or counted by `keys`/`totalKeys`/`remainingKeys`. Built-ins report `values: []` with `remainingValues == distinctValues` (bounded by construction) and are invariant under `match` (which narrows only the frontmatter key list). No existing D-15 field changes, so the frozen Phase 22 contract is the full envelope including `builtIns`, and Phase 22 surfaces it unchanged. — Rationale: D-03 requires discovery to report `path`/`mtime` as built-ins, and a separate list keeps the frontmatter key window, ordering, pagination, and `match` semantics untouched. — **Reversibility:** costly — the envelope is the Phase 22 contract.

### Locked upstream (roadmap/research — do not re-litigate)
- **The vector escalation loop has a measured latent bug that this phase must fix.** `src/sif/search/vector.py` stops escalating when `len(rows) < fetch_k`, but `rows` is the post-JOIN result — so any selective JOIN filter (including the existing collection filter) ends escalation on the first batch. Reproduced with the real `VectorSearcher`: a 2-document collection with `limit=10` returned **one** document. FILT-03's "adaptive over-fetch" is unimplementable without correcting the stop condition when a filter is present (the D-08 pre-count supplies the target). This is in scope for Phase 20, not a follow-up.
- **qmd parity target re-verified 2026-11-15:** the filter AST, `qmd.metadata` namespaced frontmatter, and the `metadata` MCP tool are **still `[Unreleased]`**; latest release is `2.8.3` (2026-08-16). The operator list read verbatim from the current CHANGELOG matches the research exactly. Pin the parity target to the current `[Unreleased]` era and note in the plan that it may shift.
- Pre-RRF per leg is the seam: BM25 outer WHERE of the materialized weighted-match CTE (never inside the CTE), vector post-KNN JOIN — the same place `collection_filter` already lands in both legs. Post-fusion filtering is rejected (breaks top-K, wastes rerank).
- Parameterized SQL only; no SQL/string passthrough (injection surface).
- `qmd.metadata` namespaced keys filter identically to native keys — one flat key space after resolution.
- Staleness stays derived; contexts keep two-sided `normalize_path` matching (Phase 19 invariants, Pitfall 18).
- Every new CLI command/flag and Settings field must flow through `scripts/generate_config_ref.py` + `make docs-generate` (CI diff gate on generator-owned `docs/cli-reference.md` and `docs/configuration.md` — never hand-edit those).
- No new runtime dependencies (v1.2 locks exactly `mcp` and `rapidfuzz`, both already landed).
- Byte-identical-defaults culture: an unfiltered search must be unchanged — no pre-count, no extra query, no new warning.

### Claude's Discretion
- Exact kv table shape within the research's recommendation (one `document_metadata_values` row per scalar/array element with an `ordinal`, a `value_type` CHECK, nullable typed columns, PK `(document_id, key, ordinal)`, FK cascade, plus partial covering indexes, and a `document_metadata_skips` sidecar) — column names and the precise index set are the planner's.
- Module layout: research recommends `src/sif/core/filters.py` (domain AST) + `src/sif/search/filters.py` (SQL compiler); names and internal signatures are the planner's.
- Whether the selectivity pre-count is merged into the first KNN round-trip or issued separately, and its exact seeding rule for `fetch_k` (the research measured the standalone form at 0.041–0.42 ms at 10k docs).
- `prefix` compiles to a **half-open range** (`>= prefix AND < prefix+U+10FFFF`) rather than `LIKE` — the research measured an index SEARCH vs a full SCAN; `contains`/`suffix` use `instr()`/BLOB `substr()`. Exact expression construction is the planner's.
- Discovery table column layout/order and how remainders render in table vs JSON (the `limit`/`value_limit` semantics themselves are settled in D-14/D-15).
- Message wording for the too-selective notice and all validation errors, subject to D-17's "name the operator, field, and path" rule.
- Whether `search_chunks()` (BM25 chunk-level helper) also honors filters, and whether filtered + `--per-chunk` results need any extra contract note.
- Property-test wording: the research requires `filtered-hybrid ⊆ unfiltered-hybrid ∩ filter-set`, a 2%-selectivity recall fixture, and filter × collection × pagination composition; fixture design is the planner's.
- Rerank interaction: whether a filtered search changes the candidate window beyond D-08's pre-count (the Phase 19 rerank pre-window rule stays authoritative).
- How the D-06 backfill announces its one-time cost and whether it runs under the pre-command refresh path; the "never a half-populated store" rule itself is locked.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requirements and roadmap
- `.planning/phases/20-metadata-filtering-discovery/20-RESEARCH.md` — **the phase research; read before planning.** Measured SQL plans and timings, the revised vector escalation loop, the typed-kv DDL, the qmd parity contract with its source ledger, and the Validation Architecture section
- `.planning/REQUIREMENTS.md` — FILT-01..FILT-05; Out of Scope table (post-fusion filtering, SQL passthrough, nested frontmatter, faceted UI)
- `.planning/ROADMAP.md` §Phase 20 — goal + five success criteria; §Phase 19 (HARD dependency: CORR-01 freshness + pagination contract); §Phase 21 (CORR-06 consumers); §Phase 22 (`metadata` tool schema reuse)
- `.planning/PROJECT.md` §Key Decisions + §Constraints — qmd interface parity, exactly two new runtime deps, local-first, CLI/MCP schema stability
- `.planning/STATE.md` — accumulated decisions; research gap "qmd filter AST is UNRELEASED (re-verify at Phase 20)"; cross-phase contract "`metadata` tool schema (20 → 22)"

### Milestone research (file:line maps verified against the codebase base)
- `.planning/research/FEATURES.md` §"A. Metadata filtering and discovery" — the six-row capability table (AST, built-in fields, typed extraction + namespace, pre-RRF, shared surface, discovery), plus §Anti-Features for the rejected alternatives
- `.planning/research/ARCHITECTURE.md` — corrected pipeline order (over-fetch → filter → dedup → fuse → single slice → ONE attach); `core/filters.py` + `search/filters.py` split; the two verified SQL seams
- `.planning/research/PITFALLS.md` §P13 (vec0 resolves KNN before the JOIN → filters silently under-return; adaptive over-fetch + exclude-all sentinel), §P14 (frontmatter freshness precondition — CLOSED by Phase 19), §P15 (pagination — CLOSED by Phase 19), §P18 (derived staleness / context normalization invariants)
- `.planning/research/SUMMARY.md` §"Architecture Approach" + §"Critical Pitfalls" — filter chain ordering and the "two links parallelize" note (AST+validator ∥ typed storage; pushdown needs both; discovery needs only storage)
- `.planning/research/STACK.md` — zero new dependencies

### Prior phase decisions (carry forward, do not re-litigate)
- `.planning/phases/19-search-correctness/19-CONTEXT.md` — D-04/D-05/D-06 (offset surfaces + global ranks, the precedent D-01/D-02 mirror), D-07 (metadata fast path that D-05 must feed), D-08 (checksum covers ALL frontmatter, so every key is fresh), D-09 (one forced-reindex migration already spent); single attach at pipeline exit
- `.planning/phases/18-quality-instrument-personal-bench-rapidfuzz-dym/18-CONTEXT.md` — the bench instrument and per-leg report available if the planner wants a before/after for any ranking-adjacent change (filtering should be score-neutral by construction)
- `.planning/phases/17-engineering-foundation-ci-matrix-hygiene-pypi/17-CONTEXT.md` — green CI matrix, deterministic test env, no new deps beyond the locked pair

### External primary source (re-verified 2026-11-15)
- `https://raw.githubusercontent.com/tobi/qmd/main/CHANGELOG.md` — `[Unreleased]`: "one shared recursive filter AST discriminated by `operator`", the 17 operators, "optional `caseInsensitive` flag … (ASCII folding)", "applied before RRF fusion and reranking", "highly selective filters remain best-effort for top-K completeness", `qmd.metadata` block with "strings, numbers, booleans, or flat homogeneous arrays", "the MCP server adds a `metadata` tool"

### Code and data surfaces (verified this session at HEAD)
- `src/sif/search/bm25.py` — materialized weighted-match CTE, `collection_filter` + `min_score_filter` placed in the outer WHERE, `LIMIT/OFFSET`, global ranks, exclude-all sentinel
- `src/sif/search/vector.py` — KNN SELECT with `collection_filter` post-KNN, `fetch_k` doubling loop + `_MAX_FETCH_K = 2048`, per-doc dedup, `_candidates`, exclude-all sentinel
- `src/sif/search/hybrid.py` — single slice owner, post-fusion safety-net dedup, early returns, rerank pre-window, ONE attach
- `src/sif/core/models.py` — `SearchOptions` (offset, per_chunk, collection_ids sentinel, min_score, candidate_limit, title_weight, fusion tunables), `SearchResult` (no metadata field — the result contract stays unchanged)
- `src/sif/database/schema.py` — `documents` table (`path`, `mtime REAL`, `file_size`, `metadata TEXT DEFAULT '{}'`), `idx_documents_mtime` (already landed), `index_meta` kv table + `SchemaManager` detection gates
- `src/sif/database/repositories.py` — `canonical_metadata_json` at both write sites, metadata JSON round-trip
- `src/sif/indexing/parser.py` — `frontmatter.loads` → full canonical metadata dict; `CodeParser` stores `{"language": ...}`; `create_parser` dispatch
- `src/sif/indexing/incremental.py` — single per-file update path (full path + metadata fast path) where kv rows must be written
- `src/sif/mcp/protocol.py` — `QueryInput`/`LexSearchInput`/`VecSearchInput`, `ToolsCallResult.isError`, hand-written `input_schema` kept in sync with the pydantic model
- `src/sif/mcp/handlers.py` — `ToolHandler` ABC, `create_default_tools()` registry (query/get/multi_get/status — `metadata` joins here)
- `src/sif/mcp/backend.py` — `SearchBackend` boundary (the Phase 22 carve-out host)
- `src/sif/cli/commands/search.py` — the three commands' option blocks and five output renderers
- `src/sif/cli/commands/collection.py` — `collection` group where `metadata` lands
- `src/sif/core/document.py` — `DocumentMetadata.tags` exists but is **never populated** by any parser (confirming D-04)

### Project conventions
- `CLAUDE.md` — quality gates (`ruff check`, `ruff format --check`, `ty check src/sif`, `pytest` fail_under=90), generator-owned docs (`docs/cli-reference.md`, `docs/configuration.md` via `make docs-generate`), error culture (`click.ClickException`, remedy-hint messages), logging to stderr
- `Makefile` — `docs-generate` target (`scripts/generate_cli_ref.py` + `scripts/generate_config_ref.py`)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- **The materialized-CTE seam already exists in both legs.** `bm25.py` interpolates `{collection_filter}` and `{min_score_filter}` into the outer WHERE of `matched AS MATERIALIZED`; the filter predicate is one more fragment in exactly that slot. `vector.py` interpolates `{collection_filter}` into the post-KNN JOIN's WHERE. Both are already parameterized (`params` list), so the compiler's job is placeholder generation, not new SQL architecture.
- **The vector escalation loop is already adaptive.** `fetch_k` starts at `min(max(target*4, 50), 2048)` and doubles only while saturated. Filter selectivity plugs into the seeding and the stop condition; no new loop is needed.
- **`SchemaManager` detection-gated migration machinery** (`_add_column_if_missing`, `index_meta` kv table, the `index_meta`-based convention marker from Phase 19 D-09) is the template for the kv backfill marker — never the deleted `MigrationManager`.
- **`canonical_metadata_json`** is the one serializer for metadata. Deriving kv rows from it guarantees the typed view and the stored blob agree.
- **`SearchOptions`** already carries every composition axis (collection sentinel, min_score, offset, per_chunk, candidate_limit, fusion weights); a `filter` field slots in beside `collection_ids` and threads through the pipeline untouched otherwise.
- **`ToolHandler` ABC + `create_default_tools()`** — a `MetadataToolHandler` is a small, mechanical addition; the hand-written `input_schema` pattern and the "keep it in sync with the pydantic model" comment are the established contract.
- **Output renderers** (`_render_*` in `search.py`, plus JSON/CSV/MD/XML modes) set the format precedent for the discovery command's table/JSON output and remainders.

### Established Patterns
- Detection-gated, idempotent migrations inside `SchemaManager`; fresh and already-migrated DBs pay zero cost.
- Byte-identical defaults: the unfiltered path must issue no extra query and emit no new output. Any filtered-only behavior (pre-count, warning) is gated on `filter is not None`.
- Parameterized SQL everywhere; weights/thresholds bound as parameters, never interpolated (T-19-19 precedent).
- Warnings and notices on stderr; stdout/JSON stays machine-clean.
- Remedy-hint error culture: name the cause and the fix — here, name the operator, the field, and the path inside the AST.
- Generator-owned docs: any new flag/command/setting runs `make docs-generate` and the CI diff gate proves it.
- Deterministic tests: `tmp_path` batteries, `ConceptEmbedder` for hermetic embeddings, no wall-clock races.

### Integration Points
- `src/sif/core/filters.py` (new) — AST models, validator, budgets, qmd-parity semantics, the single shared entry point.
- `src/sif/search/filters.py` (new) — AST → parameterized predicate fragment; the only place that knows SQL.
- `src/sif/core/models.py` — `SearchOptions.filter` (typed AST or None).
- `src/sif/search/bm25.py` — inject the compiled fragment into the outer WHERE of both branches (scoped + `--all`).
- `src/sif/search/vector.py` — inject into the post-KNN JOIN WHERE; seed `fetch_k` from the pre-count; emit the too-selective warning once.
- `src/sif/search/hybrid.py` — pass the AST to both legs; no fusion change; keep the single slice and ONE attach.
- `src/sif/database/schema.py` — typed kv table(s), indexes, backfill gate + `schema_meta` marker.
- `src/sif/database/repositories.py` — kv delete-then-insert at both document write sites, inside the caller's transaction.
- `src/sif/database/metadata_repository.py` or similar (new) — kv CRUD, filter-support counts, discovery aggregates (min/median/max, type splits, remainders).
- `src/sif/indexing/incremental.py` — confirm both the full path and the metadata fast path reach the kv sync.
- `src/sif/indexing/parser.py` — `qmd.metadata` resolution into the flat canonical metadata dict (presence-based, D-04/D-07 caps).
- `src/sif/cli/commands/search.py` — `--filter` on `search`/`vsearch`/`query`; validation before search; ClickException mapping.
- `src/sif/cli/commands/collection.py` — `collection metadata` subcommand.
- `src/sif/mcp/protocol.py` + `handlers.py` + `backend.py` — `filter` fields on the three inputs, `metadata` tool handler + registry entry, `SearchBackend.metadata(...)`, isError mapping.
- Tests: `tests/unit/search/`, `tests/unit/database/`, `tests/unit/indexing/`, `tests/unit/cli/`, `tests/unit/mcp/`, `tests/e2e/`.

</code_context>

<specifics>
## Specific Ideas

- **The parity citation is dated.** Context records the qmd verification as 2026-11-15 against `[Unreleased]`; if the planner re-checks and the AST has shipped, adopt the released semantics and note the delta — do not silently mix eras.
- **Property fixture — the containment invariant:** `filtered-hybrid ⊆ unfiltered-hybrid ∩ filter-set` over a generated corpus (filters that admit everything must reproduce the unfiltered page exactly).
- **Selective-filter recall fixture:** a corpus where ~2% of documents carry a tag; `tag contains x` must return those documents, not an empty page — the Pitfall 13 regression.
- **The honest message has a precondition:** it fires only when `filtered_doc_count >= requested_page_target` and the ceiling was exhausted. A test must assert both branches: warning present (many matches, ceiling hit) and warning absent (few matches, short page).
- **Empty-match sentinel:** a filter matching nothing returns an empty page with the normal zero-result path (including did-you-mean suggestions) — never "no filter applied". Mirrors the `collection_ids == []` sentinel tests.
- **Metadata fast-path regression:** a frontmatter-only edit (Phase 19 D-07) must update the kv rows in the same command; a body edit must not leave stale kv rows behind.
- **Backfill idempotence:** run the backfill on a populated DB, interrupt it mid-pass, re-run — the marker must not be written until a complete pass, and re-running must not duplicate rows.
- **Discovery never lies:** every key the discovery tool reports must be filterable, and every filterable key must appear — assert both directions on a corpus containing a non-indexable key (counted, not silently dropped).
- **Injection regression:** a filter value containing `'`, `;`, `--`, or `%` must never alter SQL structure; assert the compiled SQL string is unchanged in shape while params carry the literal.
- **Docs gate:** the new `--filter` flag and `collection metadata` command must appear in the generated `docs/cli-reference.md`; the CI diff gate will fail otherwise.
- **No JSON1:** assert the new code paths contain no `json_each`/`json_extract`; the Python backfill and the kv table are the contract.

</specifics>

<deferred>
## Deferred Ideas

- **Glob/regex path operator** — PROJECT.md's milestone summary says "path prefix/glob", but glob is not one of qmd's 17 operators; adding a non-portable operator would fork the shared grammar. `prefix` covers directory scoping. Revisit as a v1.x candidate if path filtering proves too coarse.
- **`title` as a built-in filter field** — the roadmap names only `path`/`mtime`; `title` filters read frontmatter today, so filename-derived titles don't match. Candidate for a future phase; discovery should make the difference visible.
- **Saved filters / filter presets** — already logged as FILT-F1 (v1.x candidate, trigger: filter usage observed in `query_log`). Would be a new capability, not a clarification of this one.
- **`@file` convention for `--filter`** — inline JSON only for now; file-based filters are additive later.
- **Top-level `sif metadata` alias** — `sif collection metadata` is the qmd-parity home; an alias is additive if users ask.
- **Nested frontmatter objects, SQL passthrough, post-fusion filtering, faceted UI** — all rejected upstream and recorded in REQUIREMENTS.md's Out of Scope table; not re-opened here.

</deferred>

---

*Phase: 20-Metadata Filtering + Discovery*
*Context gathered: 2026-11-15*
