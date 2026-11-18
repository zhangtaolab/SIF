# Phase 19: Search Correctness - Context

**Gathered:** 2026-11-15
**Status:** Ready for planning

<domain>
## Phase Boundary

The milestone's trust-floor phase — make search results fresh, deduplicated, deterministically paginable, and title-aware, with every ranking-contract change measured before/after on the Phase 18 instrument. Delivers exactly CORR-01..CORR-05:

1. **Frontmatter freshness (CORR-01)** — wire `create_parser` dispatch into the single incremental path; make the change-detection checksum metadata-aware (all frontmatter, canonical serialization); fix the YAML `---`-as-frontmatter empty-body bug; keep the Markdown body path byte-identical; ship ONE shared forced-reindex migration with the checksum-convention change.
2. **Per-document dedup (CORR-02)** — move dedup inside `VectorSearcher` before fusion (best-scoring chunk wins; duplicate chunks no longer inflate RRF scores); `--per-chunk` / MCP `per_chunk` escape hatch restores chunk-level results; surface `chunk_matches`; add `chunk_id` + `sequence` to the result contract; record the ranking-contract change with bench before/after and rationale-updated goldens.
3. **Deterministic pagination (CORR-03)** — CLI `--offset` on `search`/`vsearch`/`query`, MCP `offset` on `query`/`lex_search`/`vec_search`; searchers return from rank 0; hybrid owns ONE `[offset:offset+limit]` slice; BM25 `min_score` applied before pagination; global rank numbering across pages.
4. **Title-aware ranking (CORR-04)** — title-FTS detect-and-rebuild migration + rewritten triggers; bench-measured `bm25()` column weights (balanced title-forward posture); `mtime` index; `documents_fts_v` vocab shadow survives the rebuild on a populated DB.
5. **Single attach (CORR-05)** — eliminate the double/triple context+staleness attach; exactly ONE attach at pipeline exit, preserving marker semantics for every exit path.

NOT in scope: metadata filter AST/tooling (Phase 20), bounded scan elimination / `embedded_documents` shadow (Phase 21 — CORR-06), MCP SDK v2 shell swap and pipeline parity (Phase 22), Harrier evaluation (Phase 23), chunking/title-breadcrumb tuning sweeps (Phase 24). No new runtime dependencies.

</domain>

<decisions>
## Implementation Decisions

### Per-chunk & result shape (discussed)
- **D-01:** **Chunk escape hatch covers every chunk-capable surface** — `--per-chunk` on `sif query` and `sif vsearch`; `per_chunk` boolean on MCP `query` and `vec_search`. `sif search` / MCP `lex_search` are document-level and get no flag. — **Reversibility:** costly — these are public CLI/MCP surfaces; removing a shipped flag/param later breaks scripts and clients.
- **D-02:** **Deduped rows show the collapsed match count** — the default result carries `chunk_matches` (best-scoring chunk wins the row; the count comes from pre-dedup vector rows, no extra query). Expose it in the table and in JSON/MCP output; it tells the user the document matched more than once without `--per-chunk`. — **Reversibility:** costly — a public output field consumed by agents; removal is a breaking output change.
- **D-03:** **Chunk identity is part of the result contract** — add `chunk_id` and `sequence` to `SearchResult`, exposed in `--per-chunk` output, JSON, and MCP; display form is `path#sequence`. Clients can address the matched chunk rather than only its snippet. — **Reversibility:** costly — public result schema shared by CLI JSON/MCP clients; removing fields is breaking.

### Pagination surface (discussed)
- **D-04:** **`--offset` on all three CLI result commands** — `sif search` (BM25), `sif vsearch` (vector), `sif query` (hybrid). Same flag name and semantics everywhere. — **Reversibility:** costly — public CLI surface; a shipped flag is a compatibility commitment.
- **D-05:** **MCP offset on all three search tools** — `query`, `lex_search`, `vec_search` accept `offset`, mirroring their CLI counterparts. Phase 22 parity work then has no offset gap to fill. — **Reversibility:** costly — public MCP tool schema.
- **D-06:** **Global rank numbering across pages** — page 2 carries ranks 11–20 (`rank = offset + position`); JSON `rank` matches overall ordering and page continuity is testable. Table may show "Results 11–20". — **Reversibility:** costly — rank semantics are consumed by JSON/MCP clients and by Phase 18 saved-run comparisons.

### Frontmatter freshness & migration (discussed)
- **D-07:** **Metadata fast path for frontmatter-only edits** — body unchanged + frontmatter changed → update `title`/`metadata`/`mtime`/`checksum` in place and KEEP chunks and embeddings; only a body change takes the existing full path (purge chunks + embeddings, re-chunk/re-embed on the next embed). Safe because chunk text derives from the body only, so unchanged body ⇒ identical chunk text and valid vectors; title changes flow to `documents_fts` via the update trigger. This prevents a tag edit from dropping a document out of vector search until re-embed (especially under BM25-only watch depth).
- **D-08:** **Change-detection hash covers ALL frontmatter** — hash = body + full frontmatter dict, serialized canonically (`sort_keys=True`, stable/typed values, e.g. `default=str` for dates). Rationale: Phase 20's filter AST accepts arbitrary frontmatter keys and the `metadata` discovery tool reports all keys; any excluded key would serve stale values and violate Phase 20's HARD dependency. Volatile keys are accepted: with the fast path, a row update plus FTS trigger is cheap and "the file really changed". — **Reversibility:** costly — changing hash scope again means another checksum-convention change and another forced-reindex migration.
- **D-09:** **Upgrade reindex auto-runs on the next index-writing pass, announced once** — persist a convention/parser version in the DB; the next `sif index update` / watch host / MCP index tool detects the mismatch, prints one line (e.g. "Upgrading index format: reindexing N documents once"), runs ONE forced full re-parse, and clears the marker only after success. The migration reuses the D-07 fast path: an unchanged body updates metadata/checksum only and is NOT re-embedded; only genuinely changed bodies (mostly non-Markdown files) take the full path. Searches keep working on old data in the meantime; trigger ONLY at index-writing entry points, never inside the per-search drift check. — **Reversibility:** costly — the version marker and upgrade path are a one-time migration contract spanning CLI/watch/MCP; altering it later needs a new migration.

### Title ranking posture (discussed)
- **D-10:** **Balanced title-forward posture** — title column weight starts in a ~2–4× body band, and the bench selects the point within that band; body relevance can still win. Known-item/title queries benefit without short common-word titles burying body-relevant long documents.
- **D-11:** **Title weight stays an internal constant** — no `SIF_TITLE_WEIGHT` setting and no CLI flag; tests pin the constant and the behavior (DYM cutoff D-16 precedent). Exposing it later is additive if Phase 24 sweeps show corpus variance.
- **D-12:** **Strict per-leg acceptance gate** — use the Phase 18 per-leg × language × category report and noise gate: the title/known-item leg must improve significantly, AND body/hybrid held-out must not regress beyond the 0.01 tie rule. If either fails, revert the weight or record the rejection with numbers.

### Locked upstream (roadmap/research — do not re-litigate)
- Dedup lives inside `VectorSearcher` before fusion; RRF math itself is unchanged; hybrid keeps a post-fusion dedup as a safety net; single-leg early-return paths (vector-only/BM25-only) receive the same per-doc treatment (PITFALLS P12).
- ONE offset owner: searchers return from rank 0; hybrid performs the single `[offset:offset+limit]` slice after dedup (and after rerank/snippets in the pipeline); BM25 `min_score` is applied before pagination (PITFALLS P15).
- Title FTS is a detect-and-rebuild migration (parse the stored FTS SQL for the column list; CR-01 gated pattern), all six triggers rewritten to carry `(rowid, content, title)`, plus an `mtime` index; `documents_fts_v` must survive the rebuild on a populated DB (PITFALLS P16; STATE research gap).
- ONE shared forced-reindex migration covers parser dispatch + metadata-aware checksum; the Markdown body path stays byte-identical; the YAML `---` empty-body bug is fixed (PITFALLS P14/P17).
- Every ranking-contract change is recorded with bench before/after and goldens updated with rationale (CORR-02/CORR-04).
- ONE context/staleness attach at pipeline exit (CORR-05); staleness stays derived (never a persisted per-document flag); contexts keep two-sided `normalize_path` matching with no SQL prefilter (PITFALLS P18).
- No new runtime dependencies (v1.2 locks exactly `mcp` and `rapidfuzz`, both already landed).

### Claude's Discretion
- Exact JSON field names (`chunk_matches`, `chunk_id`, `sequence`) and table column layout/order.
- Title column source: whether filename-stem fallback titles are indexed in the title column (no title-provenance field exists today; personal-KB filenames are often meaningful). Bench evidence decides if the fallback hurts.
- `--per-chunk` interaction with `--limit`/`--offset` (page size counts chunk rows, not documents) and the MCP `per_chunk` output shape.
- Offset validation details (Click range/must be ≥ 0; past-the-end returns an empty page, never an error).
- Migration interruption recovery details (marker remains until a successful pass; per-file short transactions keep it resumable; counts reported).
- How the metadata-only fast path is detected (compare the stored content hash against the parsed body hash vs. storing a separate metadata hash column), as long as ALL frontmatter participates in change detection.
- Bench measurement procedure (which legs/fixtures, exact candidate band, synthetic vs personal bench or both), provided the D-12 gate is applied.
- YAML `---` fix mechanics and per-parser fixtures (`.yaml` starting `---`, `.py` docstring title, `.txt` first-line title, `.md` unchanged convention).
- Whether `file_size` is refreshed on update (research only requires it if size filters ship; Phase 20's built-in fields are path/mtime, not size).
- SQL details of the title-FTS migration gate and trigger forms.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requirements and roadmap
- `.planning/REQUIREMENTS.md` — CORR-01..CORR-05; Out of Scope table (post-fusion filtering, SQL passthrough, etc.)
- `.planning/ROADMAP.md` §Phase 19 — goal + five success criteria; §Phase 20 — HARD dependency on CORR-01/pagination; §Phase 21 — CORR-06 consumers of attach-owner/dedup
- `.planning/PROJECT.md` §Key Decisions — v1.2 scope, exactly two new runtime deps, byte-identical-defaults culture
- `.planning/STATE.md` — accumulated decisions; research gap: "documents_fts_v vocab shadow survival on populated DB (19)"

### Milestone research (file:line maps verified against HEAD)
- `.planning/research/ARCHITECTURE.md` §tier 2 — corrected pipeline order (over-fetch → dedup → fuse over limit+offset → single slice → ONE attach); file-level change map for `vector.py`/`hybrid.py`/`bm25.py`/`schema.py`
- `.planning/research/PITFALLS.md` §P12 (dedup ordering + vector-only path), §P14 (frontmatter freshness), §P15 (pagination broken at three points), §P16 (title-FTS migration / vocab shadow), §P17 (parser dispatch, checksum convention, YAML `---` bug), §P18 (attach/scan elimination invariants), §P5 (CJK tokenizer limits — do not promise lexical ZH wins)
- `.planning/research/FEATURES.md` — pagination/dedup contract, `--per-chunk` escape-hatch rationale, deterministic tiebreak
- `.planning/research/SUMMARY.md` §"Search correctness" — one-plan migration, bench-before/after requirement
- `.planning/research/STACK.md` — zero new dependencies; FTS5/VACUUM/backup are stdlib/in-house

### Prior phase decisions (carry forward, do not re-litigate)
- `.planning/phases/18-quality-instrument-personal-bench-rapidfuzz-dym/18-CONTEXT.md` — instrument, per-leg × language × category reports, hash split, 0.01 tie rule, bootstrap noise gate, DYM internal-constant precedent (D-16)
- `.planning/phases/17-engineering-foundation-ci-matrix-hygiene-pypi/17-CONTEXT.md` — CI matrix, deterministic test env, no new deps beyond the locked pair

### Code and data surfaces (verified this session)
- `src/sif/search/vector.py` — KNN SELECT, `fetch_k` over-fetch, trim/rank, context+staleness attach
- `src/sif/search/hybrid.py` — fusion at `options.limit`, post-truncation dedup, early returns, reranker over-fetch, pipeline attach
- `src/sif/search/bm25.py` — materialized-CTE scoped SQL, `LIMIT/OFFSET`, `min_score` filter after pagination, `search_chunks`
- `src/sif/search/rrf.py` — rank-sum fusion (math unchanged)
- `src/sif/search/context_attach.py`, `src/sif/search/staleness.py` — attach helpers and derived-signal invariants
- `src/sif/database/schema.py` — `documents_fts`/`documents_fts_v`/triggers, legacy-trigger detection, migration gates, indexes
- `src/sif/indexing/parser.py` — `MarkdownParser` body checksum, `create_parser` (unwired), `frontmatter.loads` behavior
- `src/sif/indexing/incremental.py` — single per-file update loop, checksum skip + mtime-only convergence, purge-on-change
- `src/sif/core/models.py` — `SearchResult`, `SearchOptions.offset`, `Document.__post_init__` checksum
- `src/sif/cli/commands/search.py` — `search`/`vsearch`/`query` option blocks and five output renderers
- `src/sif/mcp/protocol.py`, `src/sif/mcp/handlers.py`, `src/sif/mcp/backend.py` — `QueryInput`/`LexSearchInput`/`VecSearchInput`, `hybrid_search`, boundary remap
- `.planning/phases/18-*` research/bench code — `src/sif/search/benchmark.py`, `src/sif/search/personal_bench.py`

### Project conventions
- `CLAUDE.md` — quality gates (`ruff`, `ruff format --check`, `ty check`, `pytest` fail_under=90), generator-owned docs (`docs/cli-reference.md`, `docs/configuration.md` via `make docs-generate`), error culture

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `IncrementalIndexer` — the single per-file update path shared by CLI update, MCP index, and watch hosts; the metadata fast path (D-07) and the convention-version migration (D-09) belong here so every host converges identically.
- `SchemaManager._fts_trigger_is_legacy` / `_drop_legacy_fts_triggers` / `_fts_is_misconfigured` — the proven detect-and-drop-recreate template for the title-FTS migration; `needs_rebuild_*` seeding pattern is the model for reseeding the two-column table.
- `create_parser()` — already maps extension → parser and is fully tested in isolation; wiring it is the CORR-01 fix, not new parser work.
- `SearchOptions.offset` — already exists and is threaded through `SearchPipeline`; the missing pieces are CLI/MCP surfaces and correct slicing.
- `attach_path_contexts()` + `mark_vector_staleness()` — idempotent, batched, and safe to call once at pipeline exit; the single-attach fix removes redundant calls rather than rewriting them.
- `RRFFusion.fuse()` — takes `limit`, `k`, weights; no dedup logic should be added here.
- Phase 18 `SearchEvaluator` / personal bench — the before/after measurement substrate for D-12.

### Established Patterns
- Detection-gated, idempotent migrations inside `SchemaManager`; never the deleted `MigrationManager`. Fresh/migrated DBs must pay zero cost.
- Byte-identical-defaults culture: offset=0 must reproduce the recorded post-dedup contract; every intentional ranking change is documented and golden-tested with rationale.
- Deterministic tests: `tmp_path` batteries, `ConceptEmbedder` for hermetic embeddings, no wall-clock races; latency asserts on core functions only.
- Table + `--json` output conventions; warnings/notices on stderr, never corrupting stdout.
- Remedy-hint error culture: messages name the cause and the fix.
- Generator-owned docs: new flags/settings must flow through `scripts/generate_config_ref.py` + `make docs-generate` (CI diff gate).

### Integration Points
- `src/sif/search/vector.py` — per-doc dedup + `chunk_matches` + `chunk_id`/`sequence`, trim/rank from rank 0.
- `src/sif/search/hybrid.py` — single offset slice, safety-net dedup, ONE attach, per-chunk path, BM25-leg offset=0 down-call.
- `src/sif/search/bm25.py` — `min_score` before pagination, title column weights in `bm25()`, rank-0 behavior for hybrid.
- `src/sif/search/rrf.py` — unchanged.
- `src/sif/search/context_attach.py` / `staleness.py` — attach ownership moves to pipeline exit only (keep idempotence).
- `src/sif/database/schema.py` — title column + triggers + migration gate, mtime index, convention marker storage.
- `src/sif/indexing/parser.py` — metadata-aware hash, parser dispatch, YAML `---` fix.
- `src/sif/indexing/incremental.py` — fast path vs full path, forced migration pass, one-line notice.
- `src/sif/core/models.py` — `SearchResult` additions (`chunk_id`, `sequence`, `chunk_matches`).
- `src/sif/cli/commands/search.py` — `--offset`, `--per-chunk`, output columns/fields across all renderers.
- `src/sif/mcp/protocol.py` + `handlers.py` + `backend.py` — offset/per_chunk fields, hand-written schema + Pydantic model kept in sync, boundary remap forwards new fields.
- `src/sif/search/benchmark.py` / `personal_bench.py` — before/after measurement and saved-run comparison.
- Tests: `tests/unit/search/`, `tests/unit/indexing/`, `tests/unit/database/`, `tests/unit/mcp/`, `tests/unit/cli/`, `tests/e2e/`.

</code_context>

<specifics>
## Specific Ideas

- **Chunky-document regression fixture:** request `--limit 10` and get exactly 10 distinct documents; the vector-only path returns distinct documents; page-2 continuity holds (`offset + rank`); the single-leg early-return paths dedup too.
- **Bench narrative:** record the before/after per-leg nDCG/Hit table, the selected title weight within the 2–4× band, and the strict D-12 gate verdict in the phase SUMMARY. A rejection with numbers is a valid outcome.
- **`chunk_matches` is free:** it is the count of pre-dedup vector rows for the winning document; never add a second query for it.
- **Populated-DB vocab test:** run the title-FTS rebuild against a DB that already has documents and suggestions, then assert `documents_fts_v` still yields vocab and `sif suggest` still works (STATE research gap).
- **YAML `---` fixture:** a `.yaml` file whose first line is `---` must be indexed as the whole file by `CodeParser`, body non-empty, and searchable both before and after the migration.
- **Upgrade notice text:** one line with the document count; progress events reuse the existing `IncrementalIndexer` callback protocol so CLI/watch/MCP render consistently.
- **Offset=0 golden:** after the dedup contract change, the recorded baseline is the post-dedup output; offset=0 must reproduce it exactly, and the changed goldens carry the rationale in their test docstrings.
- **Do not promise ZH lexical gains:** FTS5 treats contiguous CJK runs as single tokens (PITFALLS P5); title-FTS benefits are scoped to EN-style tokenized titles.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 19-Search Correctness*
*Context gathered: 2026-11-15*
