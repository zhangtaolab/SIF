# Phase 19: Search Correctness - Research

**Researched:** 2026-11-15
**Domain:** SQLite FTS5/sqlite-vec search correctness in an existing Python 3.10+ local hybrid search engine (parser dispatch, change detection, ranking contract, pagination, schema migration)
**Confidence:** HIGH — every in-repo claim was re-read at HEAD `fb7f65b`; every SQLite/FTS5 and python-frontmatter behavior cited below was reproduced locally in this session (SQLite 3.51.0, python-frontmatter 1.1.0). External facts are restricted to the official SQLite FTS5 documentation.

**Provenance:** rows F1–F40 in "Verified Code Facts" are each tagged `[VERIFIED: <path>:<lines>]` in their Source column, with the verbatim quote beside the claim; body references to an F-number inherit that tag. Empirical SQLite results are tagged `[VERIFIED: local sqlite3 3.51 experiment]`; empirical frontmatter results are tagged `[VERIFIED: local python-frontmatter 1.1.0 experiment]`; official-doc statements are `[CITED: https://sqlite.org/fts5.html]`. Anything not so tagged and listed in the Assumptions Log is `[ASSUMED]`.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

#### Per-chunk & result shape (discussed)
- **D-01:** **Chunk escape hatch covers every chunk-capable surface** — `--per-chunk` on `sif query` and `sif vsearch`; `per_chunk` boolean on MCP `query` and `vec_search`. `sif search` / MCP `lex_search` are document-level and get no flag. — **Reversibility:** costly — these are public CLI/MCP surfaces; removing a shipped flag/param later breaks scripts and clients.
- **D-02:** **Deduped rows show the collapsed match count** — the default result carries `chunk_matches` (best-scoring chunk wins the row; the count comes from pre-dedup vector rows, no extra query). Expose it in the table and in JSON/MCP output; it tells the user the document matched more than once without `--per-chunk`. — **Reversibility:** costly — a public output field consumed by agents; removal is a breaking output change.
- **D-03:** **Chunk identity is part of the result contract** — add `chunk_id` and `sequence` to `SearchResult`, exposed in `--per-chunk` output, JSON, and MCP; display form is `path#sequence`. Clients can address the matched chunk rather than only its snippet. — **Reversibility:** costly — public result schema shared by CLI JSON/MCP clients; removing fields is breaking.

#### Pagination surface (discussed)
- **D-04:** **`--offset` on all three CLI result commands** — `sif search` (BM25), `sif vsearch` (vector), `sif query` (hybrid). Same flag name and semantics everywhere. — **Reversibility:** costly — public CLI surface; a shipped flag is a compatibility commitment.
- **D-05:** **MCP offset on all three search tools** — `query`, `lex_search`, `vec_search` accept `offset`, mirroring their CLI counterparts. Phase 22 parity work then has no offset gap to fill. — **Reversibility:** costly — public MCP tool schema.
- **D-06:** **Global rank numbering across pages** — page 2 carries ranks 11–20 (`rank = offset + position`); JSON `rank` matches overall ordering and page continuity is testable. Table may show "Results 11–20". — **Reversibility:** costly — rank semantics are consumed by JSON/MCP clients and by Phase 18 saved-run comparisons.

#### Frontmatter freshness & migration (discussed)
- **D-07:** **Metadata fast path for frontmatter-only edits** — body unchanged + frontmatter changed → update `title`/`metadata`/`mtime`/`checksum` in place and KEEP chunks and embeddings; only a body change takes the existing full path (purge chunks + embeddings, re-chunk/re-embed on the next embed). Safe because chunk text derives from the body only, so unchanged body ⇒ identical chunk text and valid vectors; title changes flow to `documents_fts` via the update trigger. This prevents a tag edit from dropping a document out of vector search until re-embed (especially under BM25-only watch depth).
- **D-08:** **Change-detection hash covers ALL frontmatter** — hash = body + full frontmatter dict, serialized canonically (`sort_keys=True`, stable/typed values, e.g. `default=str` for dates). Rationale: Phase 20's filter AST accepts arbitrary frontmatter keys and the `metadata` discovery tool reports all keys; any excluded key would serve stale values and violate Phase 20's HARD dependency. Volatile keys are accepted: with the fast path, a row update plus FTS trigger is cheap and "the file really changed". — **Reversibility:** costly — changing hash scope again means another checksum-convention change and another forced-reindex migration.
- **D-09:** **Upgrade reindex auto-runs on the next index-writing pass, announced once** — persist a convention/parser version in the DB; the next `sif index update` / watch host / MCP index tool detects the mismatch, prints one line (e.g. "Upgrading index format: reindexing N documents once"), runs ONE forced full re-parse, and clears the marker only after success. The migration reuses the D-07 fast path: an unchanged body updates metadata/checksum only and is NOT re-embedded; only genuinely changed bodies (mostly non-Markdown files) take the full path. Searches keep working on old data in the meantime; trigger ONLY at index-writing entry points, never inside the per-search drift check. — **Reversibility:** costly — the version marker and upgrade path are a one-time migration contract spanning CLI/watch/MCP; altering it later needs a new migration.

#### Title ranking posture (discussed)
- **D-10:** **Balanced title-forward posture** — title column weight starts in a ~2–4× body band, and the bench selects the point within that band; body relevance can still win. Known-item/title queries benefit without short common-word titles burying body-relevant long documents.
- **D-11:** **Title weight stays an internal constant** — no `SIF_TITLE_WEIGHT` setting and no CLI flag; tests pin the constant and the behavior (DYM cutoff D-16 precedent). Exposing it later is additive if Phase 24 sweeps show corpus variance.
- **D-12:** **Strict per-leg acceptance gate** — use the Phase 18 per-leg × language × category report and noise gate: the title/known-item leg must improve significantly, AND body/hybrid held-out must not regress beyond the 0.01 tie rule. If either fails, revert the weight or record the rejection with numbers.

#### Locked upstream (roadmap/research — do not re-litigate)
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

### Deferred Ideas (OUT OF SCOPE)
None — discussion stayed within phase scope.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| CORR-01 | Frontmatter-only edits become searchable: parser dispatch wired + metadata-aware checksum + ONE shared forced-reindex migration; md body byte-identical; YAML `---` bug fixed | Pattern 4 (parser dispatch + canonical checksum + fast path + per-collection convention marker), verified YAML/date experiments, `IncrementalIndexer`/watcher integration findings, Pitfalls 1–3 |
| CORR-02 | One result per document by default: vector-leg pre-fusion dedup; `--per-chunk` escape hatch; `chunk_matches`/`chunk_id`/`sequence`; recorded ranking change with bench + goldens | Pattern 2 (chunk identity & dedup), RRF fusion-key finding, verified KNN SQL with chunk join, measurement plan B0/B1 |
| CORR-03 | Deterministic pagination: CLI `--offset` + MCP offset; hybrid single slice; BM25 `min_score` before pagination; searchers from rank 0; offset=0 reproduces contract | Pattern 3 (offset ownership), verified min_score threshold math and BM25 SQL forms, page-continuity window definition, MCP model/handler gap finding |
| CORR-04 | Title-aware ranking: detect-and-rebuild title-FTS migration + rewritten triggers + bench-measured bm25() weights + mtime index; `documents_fts_v` survives rebuild | Pattern 5 (title-FTS), verified drop/recreate/rebuild sequence on a populated DB, bm25 weight mapping/alias findings, D-12 measurement procedure |
| CORR-05 | ONE context/staleness attach at pipeline exit, marker semantics preserved for every exit path | Pattern 6 (single attach), verified call-site inventory and pinned-test inventory |
</phase_requirements>

## Summary

Phase 19 changes four coupled search behaviors and one index-maintenance contract, all inside the existing SQLite/FTS5/sqlite-vec stack with **zero new runtime dependencies**. The phase splits into five implementation tracks that must be sequenced so each ranking change can be measured against the previous one: (1) CORR-01 parser dispatch + metadata-aware checksum + per-collection convention migration + fast path; (2) CORR-05 single attach; (3) CORR-03 offset/pagination and BM25 `min_score` ordering; (4) CORR-02 vector-leg dedup + chunk identity + `--per-chunk`; (5) CORR-04 title-FTS detect-and-rebuild + measured bm25 column weight + mtime index. The ordering constraint is not stylistic: the Phase 18 personal bench's corpus fingerprint includes stored checksums, so the CORR-01 checksum-convention change **invalidates every saved run recorded before it**. The measurement baseline must be recorded after CORR-01 lands.

All the risky mechanics were reproduced in this session rather than inferred `[VERIFIED: local sqlite3 3.51 experiment; local python-frontmatter 1.1.0 experiment]`. The title-FTS migration works on a populated database with the exact sequence drop-triggers → drop-vocab → drop-FTS → recreate two-column → `('rebuild')` → recreate vocab → recreate triggers; `documents_fts_v` reconnects and yields title-stemmed vocabulary; the DYM engine and BM25 title-only search work afterwards; update/delete triggers stay in sync with NULL titles; `integrity-check` is clean. `bm25(documents_fts, ?, ?)` accepts bound weights (so no SQL interpolation), weights map left-to-right by declared column order, and the FTS table name — not an alias — must be the first argument. The YAML `---` bug is real but more precise than the research headline: a `.yaml` file that starts with `---` **and contains a closing `---`** is split by `frontmatter.loads` (metadata swallows the first block, body is truncated, and a frontmatter-only file yields an empty body). Parser dispatch fixes it because `.yaml/.yml` route to `CodeParser`, which never calls `frontmatter.loads`. Two adjacent latent bugs surfaced: YAML dates make `json.dumps(metadata)` raise today, and the document-create path never passes the parser's checksum (so new documents get a body-only hash even after the new convention lands).

The highest-risk integration is **not** the schema migration — it is the watch host's change detection. `_EmbedSession.embed_documents` does not delete old chunks before inserting new ones; it relies on the BM25 leg having purged changed documents. If a metadata-only fast-path update changes the stored checksum, the watcher's checksum-diff sees "changed" and re-embeds the document, appending a duplicate chunk/vector set. The migration therefore needs an explicit "full reindex happened" signal from `IncrementalIndexer` (a `compare=False` field on `IncrementalResult`), not checksum-diff heuristics.

**Primary recommendation:** Implement in this order — CORR-01 (one plan, one convention bump) → record baseline B0 on the post-migration corpus → CORR-05 attach unification → CORR-03 offset/min_score → CORR-02 dedup/chunk identity → record B1 → CORR-04 title-FTS/weights → D-12 gate against B1. Put the convention marker in a per-collection `index_meta` key (new regular table also reserved for Phase 21 embedder identity), not a global row, so CLI `-c`, per-collection watch reconciles, and resumable failure handling all compose without special cases.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Parser dispatch + metadata-aware checksum | Indexing worker (`IncrementalIndexer`) | Domain (`ParsedDocument`, `Document`) | One per-file update path shared by CLI/watch/MCP; chunk text derives from parsed body, so change detection belongs here |
| Frontmatter-only fast path (keep chunks/embeddings) | Indexing worker transaction | Database repository | Needs body-vs-metadata discrimination and per-file atomic write; embeddings must not be purged |
| Convention version / forced migration | Database (`index_meta`) + indexing entry point | CLI/watch hosts | Marker is persisted state; trigger only at index-writing entry points (never search drift) |
| Title column + triggers + `mtime` index | Database schema (`SchemaManager`) | — | FTS shape is schema-owned; detection-gated idempotent migration runs at `init_schema` |
| Title ranking weight | Search core (`BM25Searcher`) | Bench instrument | Internal constant in the weighted `bm25()` SQL; measured, not user-configured |
| Per-document dedup | Search core (`VectorSearcher`) before fusion | RRF (fusion key only) | Duplicate chunk rows are a vector-leg property; fusion math must stay unchanged |
| Chunk identity fields (`chunk_id`, `sequence`, `chunk_matches`) | Search result contract (`SearchResult`, MCP `SearchResult`) | CLI renderers / MCP boundary | Additive public schema; must be explicitly forwarded at the MCP re-map boundary |
| Offset slicing | One owner per path: hybrid (`HybridSearcher`/`SearchPipeline`) for hybrid; each searcher for its standalone CLI/MCP command | CLI / MCP option surface | Prevents double-offset; hybrid must call searchers with `offset=0` |
| `min_score` ordering | BM25 SQL | — | Must filter before `LIMIT/OFFSET`, otherwise pages develop holes |
| Context/staleness attach | Search pipeline/entry-point exit | CLI direct-search and MCP BM25 fallback | One attach per query path; staleness stays derived, contexts keep two-sided normalization |
| Bench before/after | CLI `eval` + `search/personal_bench` | Synthetic bench/goldens | D-12 gate uses per-leg × language × bucket gates + split gates |

## Standard Stack

### Core (existing — no install in this phase)

| Library | Version (verified locally) | Purpose | Why Standard |
|---------|---------------------------|---------|--------------|
| Python | 3.13.9 locally; project floor 3.10 (`requires-python = ">=3.10"`) | Runtime | Existing matrix py3.10–3.13 |
| SQLite (stdlib `sqlite3`) | 3.51.0 locally; FTS5 built in | FTS5 external-content index, triggers, `MATERIALIZED` CTE | `MATERIALIZED` needs SQLite ≥ 3.35.0 (2021-03); CPython 3.10 ships newer [ASSUMED for CI cell exact versions] |
| sqlite-vec | 0.1.9 (installed) | vec0 KNN | Existing dependency (`sqlite-vec>=0.1.9`) |
| python-frontmatter | 1.1.0 (installed; uv.lock 2024-01-16) | Markdown frontmatter parse | Existing dependency (`python-frontmatter>=1.0.0`) |
| pytest / pytest-cov | 9.1.1 / installed | Test suite, `fail_under = 90` | `[tool.pytest.ini_options]`, `[tool.coverage.report]` |
| ruff / ty | dev extras | Lint/format/type check | CLAUDE.md quality suite |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| rapidfuzz | 3.14.6 | DYM (Phase 18) | Untouched; title FTS grows the vocabulary it scans |
| click | 8.3.2 | CLI flags (`--offset`, `--per-chunk`) | New options + docs generator |
| pydantic | 2.12.5 | MCP input models | `Field(ge=0)` for offset |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Per-collection `index_meta` convention key | Global convention row | Global row conflicts with `sif index update -c` and per-collection watch reconciles: one collection migrated would mark the DB done and strand the others |
| Body-only checksum + separate metadata hash column | Combined `body + canonical(frontmatter)` checksum | D-08 locked the combined hash; combined + stored-content equality needs no new column |
| `SearchOptions.title_weight` internal override | Monkeypatch module constant in a measurement script | Option field makes the 2–4× sweep a normal harness call; it is not a setting/CLI flag and does not violate D-11 (planner may choose monkeypatch instead) |
| FTS5 built-in `bm25()` weights | Custom BM25 implementation | Built-in is correct, tested, and parameter-bindable; hand-rolling violates the "don't hand-roll" rule |

**Installation:** none. Verification: `python3 -c "import sqlite3, frontmatter, sqlite_vec"` (all present).

## Package Legitimacy Audit

> This phase installs **no new external packages**. The table below records the seam verdicts for the existing locked dependencies that the phase touches, so the planner has the registry data on record.

| Package | Registry | Age | Downloads | Source Repo | Verdict | Disposition |
|---------|----------|-----|-----------|-------------|---------|-------------|
| python-frontmatter | PyPI | existing locked dep (uv.lock 1.1.0, upload 2024-01-16) | seam: unknown | seam: none | SUS | Existing dependency; no install in this phase. Seam reason is missing download/repo metadata, not a slopsquat signal |
| sqlite-vec | PyPI | existing locked dep (0.1.9 installed) | seam: unknown | seam: `https://TODO.com` (placeholder) | SUS | Existing dependency; no install. Registry metadata is incomplete; usage is established in v1.0–v1.1 |
| rapidfuzz | PyPI | locked in Phase 18 | seam: unknown | `github.com/rapidfuzz/RapidFuzz` | SUS | Existing dependency; no install |
| mcp | PyPI | installed transitively (1.27.0) | seam: unknown | `modelcontextprotocol.io` | SUS | Not used by this phase's code; no install |

**Packages removed due to SLOP verdict:** none.
**Packages flagged as suspicious [SUS]:** none newly installed. The planner does not need `checkpoint:human-verify` install gates because Phase 19 adds no dependency; the SUS verdicts reflect missing registry signals in the seam response (no downloads/repo), not evidence of a hallucinated package. If the planner chooses to add any dependency (it should not — D-14/no-new-deps lock), a human-verify checkpoint is mandatory.

## Verified Code Facts (HEAD `fb7f65b`)

These quotes anchor every code claim in this document. Line numbers are current at the research commit.

| # | Source | Verbatim evidence |
|---|--------|-------------------|
| F1 | `src/sif/indexing/incremental.py:77` | `self._parser = MarkdownParser()` — one parser for every file |
| F2 | `src/sif/indexing/incremental.py:300-318` | `if existing.checksum == parsed.checksum and not force:` … `# Only the mtime column: the checksum covers` `# the body alone, so a whole-row update could smuggle a new` `# frontmatter title/metadata through this skip.` |
| F3 | `src/sif/indexing/incremental.py:344-352` | `doc = Document(` `path=str(file_path),` … `mtime=parsed.mtime,` `)` — `checksum=parsed.checksum` is **not** passed, so `Document.__post_init__` falls back to a body-only hash |
| F4 | `src/sif/indexing/parser.py:66-71` | `# Calculate checksum over the body (frontmatter stripped), matching the` `# storage convention: the create path stores sha256 of Document.content` `# (the body, see core.models.Document.__post_init__), so comparing` `# against a whole-file hash never matches and every document is` `# misreported as changed on 'index update'.` `checksum = hashlib.sha256(body.encode()).hexdigest()` |
| F5 | `src/sif/indexing/parser.py:185-203` | `def create_parser(file_path: Path) -> MarkdownParser \| TextParser \| CodeParser \| None:` … `.md/.markdown/.mdx` → `MarkdownParser()`, `CodeParser.LANGUAGE_MAP` → `CodeParser()`, `.txt/.rst/.adoc` → `TextParser()`, else `None` |
| F6 | `src/sif/core/models.py:146-150` | `def __post_init__(self):` … `if self.checksum is None:` `self.checksum = hashlib.sha256(self.content.encode()).hexdigest()` |
| F7 | `src/sif/core/models.py:233-268` | `class SearchResult:` `document_id: str` `title: str` `path: str` `collection_name: str` `score: float` `content: str \| None = None` `highlights: list[str] = field(default_factory=list)` `rank: int = 0` `scores: dict[str, float \| None] = field(default_factory=dict)` `snippet: str \| None = None` `context_description: str \| None = None` `vectors_stale: bool = False`; `to_dict()` lists exactly these keys |
| F8 | `src/sif/core/models.py:271-294` | `class SearchOptions:` `limit: int = 10` `offset: int = 0` … `rrf_k: int = 60` `bm25_weight: float = 1.0` `vector_weight: float = 1.0` |
| F9 | `src/sif/database/schema.py:58-76` | `CREATE TABLE IF NOT EXISTS documents (` `id TEXT PRIMARY KEY,` … `title TEXT,` `content TEXT NOT NULL,` `checksum TEXT NOT NULL,` `file_size INTEGER DEFAULT 0,` `mtime REAL NOT NULL,` … `metadata TEXT DEFAULT '{}',` |
| F10 | `src/sif/database/schema.py:244-251` | `CREATE VIRTUAL TABLE IF NOT EXISTS documents_fts USING fts5(` `content,` `content='documents',` `content_rowid='rowid',` `tokenize='porter'` `)` |
| F11 | `src/sif/database/schema.py:221-231` | `def _fts_is_misconfigured(table_name: str, expected_content: str) -> bool:` … `return f"content='{expected_content}'" not in sql` — checks `content=` only, never the column list |
| F12 | `src/sif/database/schema.py:275-298` | `CREATE TRIGGER IF NOT EXISTS documents_fts_insert` … `INSERT INTO documents_fts(rowid, content) VALUES (new.rowid, new.content);`; update form `INSERT INTO documents_fts(documents_fts, rowid, content) VALUES('delete', old.rowid, old.content);` then insert |
| F13 | `src/sif/database/schema.py:387-401` | `_create_indexes` creates `idx_documents_collection`, `idx_documents_path`, `idx_documents_checksum` — **no mtime index** |
| F14 | `src/sif/search/vector.py:77` | `fetch_k = max(options.limit * 4, 50)` |
| F15 | `src/sif/search/vector.py:87-99` | `SELECT d.id as document_id, d.title, d.path, c.name as collection_name, distance as score FROM document_embeddings de JOIN documents d … WHERE embedding MATCH ? AND k = ? {collection_filter} ORDER BY distance` — no `chunk_id`/`sequence` selected |
| F16 | `src/sif/search/vector.py:104-131` | loop appends every KNN row; `if score < options.min_score: continue`; `results = results[: max(1, options.limit)]`; `for rank, result in enumerate(results, 1): result.rank = rank`; `return self._attach_contexts(results)` — no offset, no dedup |
| F17 | `src/sif/search/hybrid.py:77-99` | `fused_results = self.rrf.fuse([bm25_results, vector_results], options.limit, weights=[...], k=options.rrf_k)` … `deduped = self._deduplicate_results(fused_results)` `return self._attach_contexts(deduped)` |
| F18 | `src/sif/search/hybrid.py:121-123` | `return mark_vector_staleness(self.db, attach_path_contexts(self.db, results))` |
| F19 | `src/sif/search/hybrid.py:248-254` | `if self.reranker is not None:` `fetch_options = replace(options, limit=max(options.limit + options.offset, options.candidate_limit))` `else:` `fetch_options = options` — offset is only a fetch-size input; no slice |
| F20 | `src/sif/search/hybrid.py:284` | `return self.hybrid._attach_contexts(results)` — the pipeline's second attach on the hybrid path |
| F21 | `src/sif/search/bm25.py:110-122` | `ORDER BY rank` `LIMIT ? OFFSET ?`; then `score = 1.0 / (1.0 + abs(row["score"]))` `if score < options.min_score: continue` — threshold applied after pagination |
| F22 | `src/sif/search/bm25.py:145` | `return self._attach_contexts(results)` |
| F23 | `src/sif/search/rrf.py:56-57` | `for rank, result in enumerate(results, 1):` `doc_id = result.document_id` — fusion is document-keyed and adds score per occurrence |
| F24 | `src/sif/search/context_attach.py:53-56` | `cursor = db.execute(` `"SELECT target_id, content FROM contexts WHERE context_type = 'path' ORDER BY updated_at"` `)` |
| F25 | `src/sif/search/staleness.py:34-49` | `cursor = db.execute("SELECT document_id FROM document_embeddings")` then `for row in cursor: embedded.add(row[0])` — one full scan per attach |
| F26 | `src/sif/cli/commands/search.py:429-452`, `602-625`, `767-832` | option blocks for `search`, `vsearch`, `query` contain no `--offset`/`--per-chunk`; `query` has `--intent/--rrf-k/--bm25-weight/--vector-weight` |
| F27 | `src/sif/mcp/protocol.py:240-252` | `class QueryInput(BaseModel):` `query: str` `collections: list[str] \| None = None` `limit: int = Field(default=10, ge=1)` `min_score: float = Field(default=0.0, ge=0.0)` `rrf_k/ bm25_weight/ vector_weight` — no offset/per_chunk |
| F28 | `src/sif/mcp/protocol.py:265-291` | `LexSearchInput` (`query`, `collections`, `limit = 10`, no validation) and `VecSearchInput` — models exist; no handlers |
| F29 | `src/sif/mcp/handlers.py:53-69` | hand-written `input_schema` properties: `query`, `collections`, `limit`, `min_score`, `rrf_k`, `bm25_weight`, `vector_weight` — must stay in sync with `QueryInput` |
| F30 | `src/sif/mcp/handlers.py:215-222` | `create_default_tools()` returns `QueryToolHandler, GetToolHandler, MultiGetToolHandler, StatusToolHandler` only — `lex_search`/`vec_search` are unregistered |
| F31 | `src/sif/mcp/backend.py:144-181` | builds `SearchOptions(limit=limit, min_score=min_score, ...)`; constructs a fresh `SearchPipeline` per request (line 163); BM25 fallback `BM25Searcher(conn).search(query, options)` (line 179) |
| F32 | `src/sif/indexing/watcher.py:891-908` | `_changed_since` / `_path_changed` compare stored `doc.checksum != before.get(doc.path)` |
| F33 | `src/sif/indexing/watcher.py:293-309` | `chunks = chunker.chunk(doc.content)` … `chunk_repo.create(chunk)` … `searcher.add_embeddings_batch(...)` — **no delete of old chunks/embeddings in the embed leg**; it relies on the BM25 leg's purge |
| F34 | `src/sif/database/repositories.py:215-237` | `UPDATE documents SET title = ?, content = ?, checksum = ?, file_size = ?, mtime = ?, updated_at = ?, metadata = ? WHERE id = ?`; metadata via `json.dumps(document.metadata)` (no `default=str`) |
| F35 | `src/sif/database/repositories.py:142-165` | INSERT includes `checksum, file_size, mtime, created_at, updated_at, metadata`; metadata via `json.dumps(document.metadata) if document.metadata else "{}"` |
| F36 | `src/sif/search/personal_bench.py:1096-1106` | ` corpus_fingerprint(metadata: Sequence[DocumentRecord]) -> str:` `lines = sorted(f"{doc.path}\0{doc.checksum}\0{doc.file_size}" for doc in metadata)` `return hashlib.sha256("\n".join(lines).encode()).hexdigest()[:16]` |
| F37 | `src/sif/cli/commands/index.py:340-361` | `chunks = chunker.chunk(doc.content)`; `chunk.sequence = i`; `batch_items.append((chunk.id, doc_id, chunk.id, embedding))`; `vector_searcher.add_embeddings_batch(batch_items)` — `document_embeddings.chunk_id` equals `document_chunks.id` |
| F38 | `src/sif/indexing/parser.py:196-203` | `if ext in [".md", ".markdown", ".mdx"]: return MarkdownParser()` `if ext in CodeParser.LANGUAGE_MAP: return CodeParser()` `if ext in [".txt", ".rst", ".adoc"]: return TextParser()` `return None` |
| F39 | `src/sif/database/schema.py:378-385` | `CREATE VIRTUAL TABLE IF NOT EXISTS document_embeddings USING vec0(` `embedding_id TEXT PRIMARY KEY,` `document_id TEXT NOT NULL,` `chunk_id TEXT,` `embedding FLOAT[{self.embedding_dim}]` `)` |
| F40 | `src/sif/search/hybrid.py:171-284` | every pipeline branch returns before the final hybrid attach: BM25 at `:203`, vector `:209`, HyDE `:216`, hybrid at `:284` |

## Architecture Patterns

### System Architecture Diagram

```
INDEX-WRITING PATH (CLI `index update`, watch host, any future MCP index tool)
  file on disk
      │
      ▼
  create_parser(extension) ──► MarkdownParser/TextParser/CodeParser
      │                         (unwraps frontmatter for .md only)
      ▼
  ParsedDocument {content(body), title, metadata, checksum}
      │   checksum = sha256(body ‖ NUL ‖ canonical_json(all metadata))
      ▼
  IncrementalIndexer._process_file
      │  convention marker (per collection) missing/old?
      │      yes → emit "migrate N", ignore stored checksum for this pass
      ▼
  body == stored content ?
      ├─ yes ──► FAST PATH: UPDATE title/metadata/mtime/checksum/file_size
      │           (documents_fts update trigger re-indexes content+title)
      │           chunks + embeddings preserved
      └─ no  ──► FULL PATH: delete chunks + embeddings, UPDATE document
                  (next `sif index embed` / watch embed leg re-chunks/re-embeds)
      │
      ▼
  after pass: marker written only when zero parse failures

SEARCH PATH
  CLI search/vsearch/query ──► BM25Searcher / VectorSearcher / SearchPipeline ──► MCP backend
      │                              │
      │                              ├─ BM25: weighted bm25(content,title) SQL,
      │                              │        min_score filter BEFORE LIMIT/OFFSET
      │                              ├─ Vector: KNN → min_score → per-doc dedup
      │                              │        (best chunk + chunk_matches)
      │                              └─ Hybrid: fetch limit+offset from each leg
      │                                       → RRF (doc or chunk key)
      │                                       → safety-net dedup
      │                                       → rerank (if enabled)
      │                                       → snippets
      │                                       → ONE [offset:offset+limit] slice
      │                                       → global ranks offset+position
      ▼
  ONE attach at the entry-point exit: contexts (two-sided normalize) + derived staleness
      ▼
  renderers (table/JSON/CSV/MD/XML/files; chunk identity fields) ──► MCP SearchResult re-map
```

### Pattern 1: Corrected pipeline order — over-fetch → dedup → fuse → rerank/snippets → ONE slice → ONE attach

**What:** The single ordering that fixes dedup slot loss, RRF score inflation, dead offset, and double attach at once.
**When to use:** Every search path; hybrid must call each leg with `offset=0` and `limit=limit+offset`.
**Example:**
```python
# src/sif/search/hybrid.py (target shape)
fetch = replace(options, limit=max(1, options.limit + options.offset), offset=0)
bm25_results = self.bm25.search(query, fetch)
vector_results = self.vector.search(embedding, fetch)  # already per-doc deduped (default)
key = None if not options.per_chunk else (lambda r: r.chunk_id or r.document_id)
fused = self.rrf.fuse([bm25_results, vector_results], fetch.limit,
                      weights=[options.bm25_weight, options.vector_weight],
                      k=options.rrf_k, key=key)
deduped = fused if options.per_chunk else self._deduplicate_results(fused)
page = deduped[options.offset : options.offset + options.limit]
for position, result in enumerate(page, 1):
    result.rank = options.offset + position
return page  # attach happens once at the caller's exit
```
**Evidence:** current order is fuse-at-`options.limit` then dedup then attach (F17); `offset` only sizes over-fetch (F19); pipeline attaches again (F20).

### Pattern 2: Chunk identity and per-document dedup inside VectorSearcher

**What:** The KNN SELECT joins chunk metadata; results are grouped per document before return, keeping the best distance and counting pre-dedup rows; `--per-chunk` returns the ungrouped rows and changes the fusion key to chunk identity.
**When to use:** Default vector/hybrid output; escape hatch on `sif query`/`sif vsearch`/MCP `query`/`vec_search`.
**Verified SQL shape (reproduced on real vec0 + SchemaManager schema):**
```sql
SELECT d.id AS document_id, d.title, d.path, c.name AS collection_name,
       distance AS distance, de.chunk_id AS chunk_id, dc.sequence AS sequence
FROM document_embeddings de
JOIN documents d ON de.document_id = d.id
JOIN collections c ON d.collection_id = c.id
LEFT JOIN document_chunks dc ON dc.id = de.chunk_id
WHERE embedding MATCH ? AND k = ? {collection_filter}
ORDER BY distance
```
Verified: the LEFT JOIN returns `chunk_id`/`sequence` for every embedded row; legacy `chunk_id IS NULL` rows yield `None/None`.
**Dedup algorithm (recommended):**
1. Apply `min_score` to each row (`score = 1 - distance/2`).
2. Group by `document_id` in first-seen (best distance) order; winner = first row; `chunk_matches = count`; carry `chunk_id`/`sequence`.
3. Escalate `fetch_k` while `distinct_docs < target` and `rows == fetch_k` and `fetch_k < CEILING`; start `max(target*4, 50)`, double, ceiling `max(target*16, 256)` (planner may pin the ceiling; it is a DoS bound).
4. Take `target = options.limit + options.offset` documents; slice `[offset:offset+limit]`; assign global ranks.
**RRF metadata merge:** `RRFFusion.fuse` builds the fused row from the *first* list's result (document-keyed). For hybrid default output, a document present in both legs keeps the BM25 row (no chunk identity) and loses the vector leg's `chunk_id/sequence/chunk_matches`. The fusion merge must adopt non-null chunk fields from later lists and `max()` the match count. This is metadata merging, not RRF math.
**Per-chunk fusion key:** add an optional `key: Callable[[SearchResult], str]` to `fuse`; default `lambda r: r.document_id`; per-chunk passes `lambda r: r.chunk_id or r.document_id`. BM25 rows (doc-level, no `chunk_id`) remain document-keyed; vector rows are chunk-keyed. Document that a hybrid `--per-chunk` page may contain the BM25 document row alongside its vector chunk rows.
**Evidence:** F15/F16 (no chunk fields, no dedup), F23 (doc-keyed, per-occurrence accumulation), F37 (chunk_id = chunk.id), verified KNN join experiment.

### Pattern 3: Offset ownership and global rank numbering

**What:** One offset slice per query path; ranks are `offset + position`.
**When to use:** CLI `search|vsearch|query --offset`, MCP `query|lex_search|vec_search offset`.
**Rules:**
- Standalone BM25 (`sif search`): SQL `LIMIT ? OFFSET ?` stays; rank = `options.offset + position`; `min_score` moves into SQL **before** `LIMIT/OFFSET`.
- Standalone vector (`sif vsearch`): `fetch_k` uses `limit+offset`; after dedup, slice `[offset:offset+limit]`; rank = `offset + position`.
- Hybrid (`HybridSearcher`): calls both legs with `offset=0` and `limit=limit+offset`; one slice at its exit.
- Pipeline (hybrid variants): always calls `hybrid.search` with `offset=0`, fuses at `limit+offset`, reranks `top_k=limit+offset`, applies snippets, then slices; single attach after the slice.
**Page-continuity definition (important):** page 2 is defined against a single request of the same window: `query -n 5 --offset 5` must equal `query -n 10 --offset 0` sliced `[5:10]`. Both requests fetch 10 candidates per leg, so RRF sees the same inputs. Do **not** compare `-n 5 --offset 0` with `-n 5 --offset 5`: they fetch different candidate depths (5 vs 10) and the fused top-5 can legitimately differ.
**BM25 `min_score` math (verified derivation):** FTS5 `rank` (bm25) is ≤ 0 and score = `1/(1 + |rank|)` = `1/(1 - rank)`. `score >= m` (m > 0) ⇔ `rank >= 1 - 1/m`. Bind `1 - 1/m` as a parameter and apply it **inside** the FTS CTE/outer WHERE before `LIMIT/OFFSET`. When `m == 0`, omit the filter. (The naive inverse `1/m - 1` has the wrong direction and only appears to work for tiny bm25 magnitudes.)
**Evidence:** F19/F20 (no slice, double offset risk), F21 (post-pagination filter), F14/F16 (vector ignores offset/trim only), F8 (`offset` exists in options).

### Pattern 4: Frontmatter freshness — parser dispatch + canonical checksum + fast path + per-collection convention marker

**(a) Parser dispatch.** Replace the hardcoded parser (F1) with `create_parser(file_path)` (F5/F38). Fallback for `None` (unknown suffix) is a planner decision — see Open Questions; recommend `TextParser()` (whole-file content, first-line title) because it avoids re-introducing `frontmatter.loads` on arbitrary extensions, at the cost of changing unknown-extension titles/content once (covered by the same migration).

**(b) Canonical checksum and storage (one helper, used everywhere):**
```python
# shared helper (core/models.py or a small utils module)
def canonical_metadata_json(metadata: dict[str, Any]) -> str:
    return json.dumps(metadata, sort_keys=True, default=str,
                      ensure_ascii=False, separators=(",", ":"))

def compute_checksum(content: str, metadata: dict[str, Any]) -> str:
    return hashlib.sha256(
        content.encode() + b"\x00" + canonical_metadata_json(metadata).encode()
    ).hexdigest()
```
All three parsers compute `ParsedDocument.checksum` with this helper. `DocumentRepository.create/update` persist `canonical_metadata_json(...)` instead of raw `json.dumps` (F34/F35) — this fixes the latent YAML-date crash **and** guarantees the hash input and stored form agree across the JSON round-trip. The create path must pass `checksum=parsed.checksum` (F3 bug).

**(c) Fast path discrimination.** Stored `documents.content` is the parsed body/whole file by construction, so a direct content comparison is exact and needs no new column:
```python
body_same = parsed.content == existing.content
checksum_same = existing.checksum == parsed.checksum
if checksum_same and not force and not migrating:
    converge mtime only; return "skipped"
if body_same:
    # metadata-only (or convention refresh / --force with unchanged body)
    existing.title, existing.metadata = parsed.title, parsed.metadata
    existing.checksum, existing.file_size, existing.mtime = (
        parsed.checksum, len(parsed.content.encode()), parsed.mtime)
    self._doc_repo.update(existing)          # KEEP chunks + embeddings
    return "metadata"
# body changed: existing full path (purge chunks + embeddings, update row)
```
`--force` keeps its "ignore the checksum skip" meaning but still takes the fast path when the body is unchanged (D-07: only a body change takes the full path). Document the semantic refinement in the plan and test docstrings.

**(d) Convention marker (recommended: per-collection keys in a new regular table).**
```sql
CREATE TABLE IF NOT EXISTS index_meta (key TEXT PRIMARY KEY, value TEXT NOT NULL)
```
- Key `convention:<collection_id>` → `"2"` (`CONVENTION_VERSION = 2`; absent = legacy).
- `IndexMetaRepository` (get/set) in `repositories.py`, following the repository convention.
- `IncrementalIndexer.update_collection`: after the scan, read the marker. Mismatch → `migrating=True`, emit progress event `"migrate <scanned_file_count>"`, process every file ignoring the stored checksum, and write the marker only if `failed == 0`. Empty collection (`existing_docs == {}`): write the marker silently (no notice) — no documents to migrate.
- `update_paths` (watch bursts, pre-search drift refresh) **never** triggers migration (D-09); it still uses body discrimination, so an unchanged body never purges chunks.
- Why per collection: `sif index update -c`, CLI watch `-c`, and per-collection watch reconciles all work without a global pre-pass; failures are resumable per collection. A global marker would let one migrated collection strand the others.
- Phase 21 synergy: the same table is the locked home for embedder identity (ARCHITECTURE Pattern 4); use namespaced keys.
- Host integration: CLI `update_cmd` and `FileWatcher._run_reconcile` already funnel through `update_collection`, so the marker check is inherited. The MCP watch host enqueues reconciles → inherited. **There is no MCP index tool today** (F30); if Phase 22 adds one it must call the same seam.
- Notice text: `Upgrading index format for <collection>: reindexing <N> documents once`; render through the existing progress event protocol (`"migrate <n>"`) so CLI/watch/MCP hosts style it themselves.

**(e) Watcher/embed integration (required for correctness).** The embed leg appends chunks/vectors without deleting (F33), relying on the BM25 purge. A metadata-only fast path changes the checksum but does not purge, so the existing checksum-diff (F32) would re-embed and append a duplicate chunk set. Fix: add `reindexed_paths: set[str] = field(default_factory=set, compare=False)` (and optionally `metadata_only: int = field(default=0, compare=False)`) to `IncrementalResult`; `_process_file` records added and full-path-updated paths. `_run_burst`/`_run_reconcile` use `result.reindexed_paths` instead of `_checksums`/`_changed_since`/`_path_changed` before calling `_EmbedSession.embed_documents`. `compare=False` keeps the ~25 existing `IncrementalResult(...)` equality assertions green.

**(f) YAML `---` behavior `[VERIFIED: local python-frontmatter 1.1.0 experiment]`:**

| Input | `post.content` | `post.metadata` | Consequence under MarkdownParser |
|-------|----------------|-----------------|----------------------------------|
| `---\na: 1\n---\n` | `''` | `{'a': 1}` | whole file becomes metadata; empty body indexed |
| `---\nfirst: doc\n---\nsecond: doc\n` | `'second: doc'` | `{'first': 'doc'}` | file truncated after the second `---` |
| `---\na: 1\nb: 2\n` (no close) | `'---\na: 1\nb: 2'` | `{}` | full text minus trailing newline; `---` line leaks into body |
| `---\ndate: 2024-01-01\n---\nbody` | `'body'` | `{'date': datetime.date(2024, 1, 1)}` | `json.dumps` raises `TypeError` in repository write **today** |

Parser dispatch fixes the first three for `.yaml/.yml` (CodeParser reads the whole file). The date case requires the canonical storage helper. Fixtures: `.yaml` starting `---` with and without a closing `---`; `.py` docstring title; `.txt` first-line title; `.md` unchanged body byte-identical.

### Pattern 5: Title-FTS detect-and-rebuild migration `[VERIFIED: local sqlite3 3.51 experiment]`

**DDL target:**
```sql
CREATE VIRTUAL TABLE documents_fts USING fts5(
    content,
    title,
    content='documents',
    content_rowid='rowid',
    tokenize='porter'
);
CREATE VIRTUAL TABLE IF NOT EXISTS documents_fts_v USING fts5vocab(documents_fts, 'row');
-- documents triggers (three; chunks triggers stay byte-identical, chunks has no title column)
CREATE TRIGGER documents_fts_insert AFTER INSERT ON documents BEGIN
  INSERT INTO documents_fts(rowid, content, title) VALUES (new.rowid, new.content, new.title);
END;
CREATE TRIGGER documents_fts_update AFTER UPDATE ON documents BEGIN
  INSERT INTO documents_fts(documents_fts, rowid, content, title)
    VALUES('delete', old.rowid, old.content, old.title);
  INSERT INTO documents_fts(rowid, content, title) VALUES(new.rowid, new.content, new.title);
END;
CREATE TRIGGER documents_fts_delete AFTER DELETE ON documents BEGIN
  INSERT INTO documents_fts(documents_fts, rowid, content, title)
    VALUES('delete', old.rowid, old.content, old.title);
END;
```
**Detection gate:** read `sqlite_master.sql` for `documents_fts`; parse the `USING fts5(...)` column list (split at the first `content=` option clause and on commas); rebuild when `title` is absent. A missing table is a fresh DB → create the two-column form directly. The existing `_fts_is_misconfigured` (F11) cannot detect a missing column and must not be the gate.
**Verified migration sequence on a populated DB created by the current `SchemaManager`:**
1. Detect old column set (true).
2. `DROP TRIGGER IF EXISTS documents_fts_insert/update/delete` (needed: `CREATE TRIGGER IF NOT EXISTS` cannot replace the one-column bodies).
3. `DROP TABLE IF EXISTS documents_fts_v` **first** — dropping the parent while the vocab exists succeeds but leaves a dangling vocab that returns stale terms until recreated. Drop-first removes the stale-read window.
4. `DROP TABLE IF EXISTS documents_fts`.
5. Create the two-column FTS table.
6. `INSERT INTO documents_fts(documents_fts) VALUES('rebuild')` — officially deletes and rebuilds from the content table; verified with multi-column external content.
7. Recreate `documents_fts_v`.
8. Recreate the three document triggers (chunks triggers unchanged).
**Verified outcomes:** title-only queries match after the rebuild (zero before); vocabulary gains title stems (`alpha`, `bodi`, `titl`, …) and DYM works; update/delete triggers keep the index consistent (old title terms disappear after a title-only UPDATE); the `rebuild`/`integrity-check` commands return clean; NULL titles insert/delete cleanly. Idempotence: the detection gate is one `sqlite_master` read, so fresh/migrated DBs pay nothing.
**Trigger column count correction:** PITFALLS P16 says "all six triggers rewritten to carry `(rowid, content, title)`". Only the three `documents` triggers can carry title; the three `chunks_fts` triggers index `content` only and stay byte-identical. The plan should say "all three document triggers rewritten; chunks triggers recreated only if their table was rebuilt".
**Weighted ranking SQL (verified bindable, table name required):**
```sql
WITH matched AS MATERIALIZED (
    SELECT rowid, bm25(documents_fts, ?, ?) AS score
    FROM documents_fts
    WHERE documents_fts MATCH ?
    /* AND score >= ?  when min_score > 0; threshold = 1 - 1/min_score */
)
SELECT d.id AS document_id, d.title, d.path, c.name AS collection_name, m.score AS score
FROM matched m
JOIN documents d ON m.rowid = d.rowid
JOIN collections c ON d.collection_id = c.id
WHERE d.collection_id IN (...)
ORDER BY m.score
LIMIT ? OFFSET ?
```
- `bm25(documents_fts, w_content, w_title)` maps weights left-to-right by declared column order [CITED: https://sqlite.org/fts5.html §5.1.1].
- The first argument must be the real table name; `bm25(fts, ...)` with an alias raises `no such column: fts` (verified). The current unfiltered SQL aliases the table as `fts`; keep the alias in `FROM` but call `bm25(documents_fts, ?, ?)` — verified to resolve.
- `bm25(..., 1.0, 1.0)` reproduces the `rank` column exactly (verified), which is the byte-identical fallback if the weight measurement is rejected.
- Weighted bm25 is still negative and `ORDER BY score` ascending is best-first (verified).
**`mtime` index:** add `CREATE INDEX IF NOT EXISTS idx_documents_mtime ON documents(mtime)` to `_create_indexes` (F13); no gate needed (Phase 20 FILT-02 consumes it).
**Title column source:** `documents.title` is parser-derived (frontmatter title, H1, first line, docstring, or filename stem). No provenance field exists, so the stem fallback is indexed with no way to exclude it; bench evidence decides whether that hurts, and a rejection can be recorded for Phase 24 (QUAL-03 title-breadcrumb) if needed.

### Pattern 6: ONE context/staleness attach at the entry-point exit

**What:** Searchers stop attaching; each public query entry point calls the shared enrichment exactly once.
**Verified call sites to change:**
- Remove attach from `BM25Searcher.search` (F22), `VectorSearcher.search` (F16), `HybridSearcher.search` (F17/F18).
- `SearchPipeline.search` attaches at every exit: BM25 `:203`, vector `:209`, HyDE `:216`, hybrid after slice (replacing F20).
- Direct-searcher entry points add one attach: CLI `search_cmd` (F26, BM25), CLI `vsearch_cmd` (Vector), MCP `SearchBackend` BM25 fallback (F31).
- Bench/eval use `SearchPipeline`, so they inherit the single attach (read-only; markers do not affect metrics).
- Composition stays `mark_vector_staleness(db, attach_path_contexts(db, results))`; consider a single `enrich_results(db, results)` helper to avoid duplicating the composition and import cycle.
**Pinned tests to rewrite with rationale:** `tests/unit/search/test_staleness.py:262` ("D-09: every searcher exit invokes mark_vector_staleness via _attach_contexts"), `tests/unit/search/test_context_attach.py:140-178`, plus BM25/vector attach mocks. The new contract test asserts exactly one attach invocation per pipeline exit path and per CLI/MCP path.
**Invariants to preserve:** staleness stays derived (one batched `document_embeddings` scan, no persisted flag, display gate, None-degradation — F25); contexts keep two-sided `normalize_path` with no SQL prefilter (F24); contexts already carried by a result are never clobbered.

### Pattern 7: Bench measurement procedure (D-12 applied)

The Phase 18 instrument is the arbiter: `sif eval --personal` synthesizes known-item queries from the indexed corpus, reports per leg × language × length buckets, hash-splits tuning/held-out, and `--compare <saved-run>` reports paired bootstrap gates. `--bm25-only` isolates the leg that title weights and dedup actually change, needs no embedder download, and is deterministic on a scratch index over the committed 150-document fixture corpus (`tests/fixtures/bench/corpus`).

**Sequencing (mandatory):**
1. Land CORR-01 (parser dispatch + checksum convention + migration).
2. Build/reset the scratch index and record **B0** (pre-dedup, pre-title):
   ```bash
   sif collection add bench-fixture tests/fixtures/bench/corpus --pattern '**/*.md'
   sif index update -c bench-fixture
   sif eval --personal --bm25-only -c bench-fixture --json > /tmp/b0.report.json
   # note the saved-run path printed on stderr (also under <cache_dir>/eval)
   ```
3. Land CORR-05 + CORR-03 (no default ranking change at `offset=0`, `min_score=0`). Re-run `sif eval --personal --bm25-only -c bench-fixture --compare <B0-saved>` to prove no unintended drift.
4. Land CORR-02 (dedup + chunk identity). Run `--compare <B0-saved>`; record overall/per-leg/per-split deltas and update goldens. Save the resulting run as **B1** (post-dedup, pre-title).
5. Land CORR-04 schema (title column, weight 1.0 first). Optionally run `--compare <B1>` to isolate the title-column effect from the weight.
6. Sweep weight candidates in the 2–4× band (e.g. 2.0, 3.0, 4.0; refine 2.5/3.5 if the winner is at an edge) using the internal `SearchOptions.title_weight` override or a monkeypatched module constant, over B1's exact saved query set. Choose the candidate that maximizes the title-leg gate without regressing body/held-out.
7. Pin the winner as the internal constant, re-run `--compare <B1>` on the real CLI, and record the verdict in the phase SUMMARY. A rejection with numbers is a valid outcome (revert to 1.0, keep the title column).

**Acceptance gate (D-12):** title/known-item leg improves significantly; body/hybrid held-out does not regress by more than the 0.01 tie rule. The existing `--compare` output already has per-split gates (`splits.tuning/heldout`) and per-group gates (`groups` keyed by leg×language×length). It does **not** report a per-leg × split gate, so "body held-out" is not directly computable without either (a) a small additive extension to `ComparisonReport` (recommended: per-leg and per-leg×split `noise_gate` results, additive JSON/table fields, no saved-run format change), or (b) applying the held-out summary gate with the masking limitation documented. See Open Question 5.

**Corpus-fingerprint constraint `[VERIFIED: src/sif/search/personal_bench.py:1096-1106]`:** the fingerprint hashes `path + NUL + checksum + NUL + file_size` (F36). The CORR-01 checksum change and any `file_size` refresh alter the fingerprint, so saved runs recorded before CORR-01 are **refused** by `--compare`. B0 must be recorded after CORR-01. Dedup/title changes do not touch documents, so B0/B1 remain comparable.

**Synthetic bench:** `sif bench tests/fixtures/bench/queries.json` is fixture-keyed against the same corpus and is the committed regression instrument. `tests/unit/search/test_bench_snapshot.py` recomputes held-out metrics from `tests/fixtures/bench/heldout_defaults.json`; the title column (and dedup) will move those numbers, so the snapshot must be updated with rationale. `tests/support/bench.py::build_bench_db` builds the deterministic ConceptEmbedder index through `SchemaManager`, so it automatically exercises the new FTS shape.

## Recommended Project Structure (deltas only)

```
src/sif/
├── core/models.py                 # SearchResult: chunk_id, sequence, chunk_matches; SearchOptions: per_chunk (+ internal title_weight if chosen)
├── database/
│   ├── schema.py                  # index_meta table; title-FTS detect/rebuild + triggers; mtime index; 2-col FTS DDL
│   └── repositories.py            # IndexMetaRepository; canonical metadata JSON storage; (optional) collection convention column (not recommended)
├── indexing/
│   ├── parser.py                  # create_parser dispatch use site; canonical checksum helper; CONVENTION_VERSION
│   └── incremental.py             # _process_file(migrating) fast/full discrimination; marker read/write; reindexed_paths
├── indexing/watcher.py            # embed-leg candidate selection from result.reindexed_paths (not checksum diff)
├── search/
│   ├── bm25.py                    # weighted bm25 + title weight constant; min_score before LIMIT/OFFSET; rank offset
│   ├── vector.py                  # KNN joins chunk metadata; min_score → dedup → escalation → offset slice; no attach
│   ├── hybrid.py                  # fetch offset=0; single slice; global ranks; per-chunk key; no attach; pipeline exit enrichment
│   ├── rrf.py                     # optional fusion key; chunk metadata merge (no math change)
│   ├── context_attach.py          # optional enrich_results(db, results) composition helper
│   └── personal_bench.py          # optional per-leg / per-leg×split gates for D-12
├── cli/commands/search.py         # --offset on three commands; --per-chunk on query/vsearch; renderers + attach calls
├── mcp/protocol.py                # QueryInput offset/per_chunk; Lex/Vec inputs offset (+vec per_chunk); SearchResult chunk fields
├── mcp/handlers.py                # hand-written query schema sync (offset/per_chunk)
├── mcp/backend.py                 # forward offset/per_chunk/chunk fields; BM25 fallback attach; (recommended) startup schema init
└── database/schema.py             # drop_all list += index_meta
scripts/                           # make docs-generate (CLI reference only; no new settings)
tests/                             # see Validation Architecture
```

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Rebuilding a multi-column FTS index | Manual per-column reseed from documents | `INSERT INTO documents_fts(documents_fts) VALUES('rebuild')` | Official, verified on populated multi-column external-content tables; maps columns by name from the content table [CITED: sqlite.org/fts5.html §6.12] |
| BM25 column weighting | A custom scorer | `bm25(documents_fts, w_content, w_title)` | Official implementation, bindable parameters, `1.0/1.0` exactly equals `rank` (verified) |
| YAML/frontmatter parsing per format | Per-extension frontmatter heuristics | `create_parser()` + `CodeParser` whole-file path | The factory is already tested; dispatch is the fix |
| Canonical metadata serialization | Ad-hoc `str()`/`repr()` hashing | `json.dumps(sort_keys=True, default=str, ensure_ascii=False)` shared by hash + storage | Same bytes for typed frontmatter and its JSON round-trip; fixes date crash |
| RRF scoring | A new fusion algorithm | Existing `RRFFusion` + optional grouping key | Locked: RRF math unchanged; only grouping/metadata changes |
| ANN/vector indexes | Custom approximate search | sqlite-vec vec0 KNN + bounded over-fetch | Locked out of scope; brute force accepted at this scale |
| Measurement statistics | New significance tests | Phase 18 `noise_gate` / paired bootstrap / `--compare` | Locked instrument; 0.01 tie rule + noise floor already implemented |
| CLI reference docs | Hand-editing `docs/cli-reference.md` | `make docs-generate` | CI diff gate; generator-owned file |

## Runtime State Inventory

This is a data/schema migration phase, so runtime state beyond source files must be enumerated.

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| **Stored data — documents** | `documents.checksum` holds the legacy body-only hash for every existing row; `documents.metadata` holds JSON (possibly typed values flattened by JSON); `documents.title`/`content`/`file_size`/`mtime` | Convention migration re-parses every file; fast path rewrites checksum/metadata/title/file_size without purging chunks. Body-identical Markdown keeps byte-identical `content` |
| **Stored data — FTS** | `documents_fts` is single-column (content) on every existing DB; `documents_fts_v` is an fts5vocab shadow over it; six triggers exist (three documents, three chunks) | Detect-and-rebuild to the two-column shape; drop vocab before FTS; rebuild; recreate triggers. Chunks FTS untouched |
| **Stored data — chunks/embeddings** | `document_chunks` + `document_embeddings` rows are valid for unchanged bodies; `document_embeddings.chunk_id` equals `document_chunks.id`; metadata-only edits must not purge them | Fast path preserves both; watcher must not re-embed metadata-only paths (duplicate-chunk hazard) |
| **Stored data — convention marker** | No marker exists today | New `index_meta` table with per-collection `convention:<id>` keys; written only after a clean migration pass |
| **Stored data — eval saved runs** | Saved personal-eval runs live under `<cache_dir>/eval`; the fingerprint includes stored checksums and file sizes (F36) | Saved runs recorded before the checksum migration are refused for comparison; re-baseline after CORR-01. Document this in the SUMMARY |
| **Live service config** | CLI watch foreground/daemon, MCP embedded watch (`SIF_MCP_WATCH`), systemd/launchd service registrations. No UI/dashboard config | No re-registration required. Watch hosts inherit the migration through `update_collection`; their embed leg selection must switch to `reindexed_paths` |
| **OS-registered state** | launchd plist / systemd unit content (command + args) unchanged; no path/name change | None |
| **Secrets and env vars** | `SIF_*` settings unchanged; no new setting (D-11); no secret keys reference renamed values | None |
| **Build artifacts / installed packages** | Editable install unaffected; `uv.lock` unchanged (no deps); generator-owned `docs/cli-reference.md` must be regenerated for new flags; benchmark snapshot `tests/fixtures/bench/heldout_defaults.json` must be updated with rationale | Run `make docs-generate`; update goldens + snapshot; no package reinstall |

## Common Pitfalls

### Pitfall 1: Checksum-convention change silently invalidates saved bench runs
**What goes wrong:** The Phase 18 fingerprint includes `checksum`; a pre-CORR-01 baseline is refused by `--compare`, manufacturing a "corpus mismatch" at the exact moment measurement is needed.
**Why:** `corpus_fingerprint` hashes path/checksum/file_size (F36); the new combined checksum differs for every document with frontmatter.
**How to avoid:** Record B0 only after CORR-01 lands; document the invalidation; do not attempt to compare across the convention change.
**Warning signs:** `--compare` refuses with two different fingerprint values on an unchanged corpus.

### Pitfall 2: Watcher embed depth duplicates chunks after a metadata-only edit
**What goes wrong:** The fast path changes `checksum` but preserves chunks; the watcher's checksum diff marks the path changed and feeds it to the embed leg, which appends a second chunk/vector set without deleting (F32/F33). Duplicate chunks then inflate results and chunk-id completeness never converges.
**Why:** Embed-leg candidate selection is checksum-diff-based today; the embed leg assumes the BM25 leg purged.
**How to avoid:** Return `reindexed_paths` from `IncrementalIndexer` and use it as the embed candidates; add a regression test (metadata-only edit at `--depth embed` → chunk count unchanged, vector row count unchanged).
**Warning signs:** Chunk count doubles after a tag edit; `sif index embed` reports re-embedding docs whose body did not change.

### Pitfall 3: RRF drops the vector leg's chunk identity on dual-leg documents
**What goes wrong:** Default deduped hybrid rows for documents found by both legs carry `chunk_id=None`/`chunk_matches=0`, because RRF keeps the first (BM25) result object.
**Why:** `RRFFusion.fuse` keys by document and stores the first list's `SearchResult` (F23); later metadata is not adopted.
**How to avoid:** Merge non-null chunk fields and `max()` the match count in the fusion merge; test a doc present in both legs.
**Warning signs:** JSON `chunk_matches` is 0 for a document that clearly matched multiple chunks.

### Pitfall 4: BM25 `min_score` threshold direction
**What goes wrong:** Using `rank <= 1/min_score - 1` looks plausible and even passes on tiny bm25 magnitudes, but it is the wrong direction for real ranks; pages either under- or over-return.
**Why:** score = `1/(1 - rank)` with `rank <= 0`; solving `score >= m` gives `rank >= 1 - 1/m`.
**How to avoid:** Bind `1 - 1/m` with `rank >= ?` (or filter the score expression directly); unit-test with a real multi-document corpus where ranks are not ~0.
**Warning signs:** `--min-score 0.5` returns everything or nothing; pagination holes disappear/return when the threshold moves.

### Pitfall 5: `bm25()` rejects SQL aliases
**What goes wrong:** Rewriting the unfiltered BM25 SQL to `bm25(fts, ?, ?)` raises `sqlite3.OperationalError: no such column: fts`.
**Why:** FTS5 auxiliary functions require the FTS table name, not an alias (verified). The current unfiltered SQL uses `FROM documents_fts fts`.
**How to avoid:** Keep `FROM documents_fts fts` but call `bm25(documents_fts, ?, ?)` (verified to resolve), or drop the alias. Test both SQL branches.
**Warning signs:** OperationalError on the `--all`/unfiltered path only.

### Pitfall 6: Dangling / stale `documents_fts_v` during the rebuild
**What goes wrong:** Dropping `documents_fts` while `documents_fts_v` exists succeeds, but the vocab keeps returning **old** terms until the FTS is recreated. A concurrent suggestion read in that window serves stale vocabulary.
**Why:** fts5vocab holds a by-name link; drop-parent does not clear the shadow.
**How to avoid:** Drop the vocab **before** the FTS table inside the migration; recreate after rebuild; verify `suggest` post-migration on a populated DB.
**Warning signs:** Suggestions include terms that no longer exist after an upgrade.

### Pitfall 7: NULL titles and external-content delete values
**What goes wrong:** External-content `'delete'` requires every indexed column's original values [CITED: sqlite.org/fts5.html §6.3]; supplying the wrong title (or omitting it) leaves stale tokens or removes wrong ones.
**Why:** Triggers must pass `old.content` **and** `old.title`; `documents.title` is nullable.
**How to avoid:** Verified NULL title insert/delete works and `integrity-check` is clean; still test: insert with NULL title, update title, delete document, then title-match absence + integrity-check.
**Warning signs:** Deleted documents remain MATCHable by title; `integrity-check` reports errors.

### Pitfall 8: `CREATE VIRTUAL TABLE IF NOT EXISTS` never adds a column
**What goes wrong:** Existing databases keep the single-column FTS; title queries match nothing; triggers keep syncing one column (P16). The existing `_fts_is_misconfigured` gate checks only `content=`, so it does not fire (F11).
**Why:** Idempotent DDL is a no-op for an existing virtual table; FTS5 cannot ALTER columns.
**How to avoid:** Dedicated column-list detection gate; detect-and-rebuild; rewrite the three document triggers; assert the stored SQL contains `title` after migration.
**Warning signs:** Title search works on fresh test DBs but not on upgraded ones.

### Pitfall 9: YAML `---` bug is narrower than "empty body"
**What goes wrong:** A test that only covers `---\na: 1\n` (no closing delimiter) sees content `---\na: 1` and passes a naive "body non-empty" assertion, while the real corrupting cases are the closing-delimiter and multi-document forms.
**Why:** `frontmatter.loads` only treats a leading `---` as frontmatter when it finds a closing boundary; without one it returns the text as content.
**How to avoid:** Fixtures for (a) `---\na: 1\n---\n` (empty body), (b) two `---` blocks (truncation), (c) no closing `---` (leading separator leaks). Assert the `.yaml` file is indexed as the whole file **after dispatch** for all three.
**Warning signs:** A YAML config is searchable only for its second document.

### Pitfall 10: YAML dates crash repository writes today
**What goes wrong:** `date: 2024-01-01` parses to `datetime.date`; `json.dumps(metadata)` raises `TypeError`, aborting the index update outside the parse-failure handler.
**Why:** F34/F35 use plain `json.dumps` with no `default`.
**How to avoid:** Persist `canonical_metadata_json(...)` (`default=str`) in both create and update; add a date-frontmatter fixture. This is required for the checksum convention to be storable at all.
**Warning signs:** `TypeError: Object of type date is not JSON serializable` during `sif index update`.

### Pitfall 11: Page continuity tested against different candidate depths
**What goes wrong:** `-n 5 --offset 0` (fetches 5/leg) vs `-n 5 --offset 5` (fetches 10/leg) can produce different fused top-5; a naive continuity test flakes.
**Why:** RRF sees different candidate sets; ranks beyond the fetch window never contribute in the smaller request.
**How to avoid:** Define page continuity against a single request of the same window: page at `offset=o`, `limit=l` equals `[o:o+l]` of a request with `limit=o+l, offset=0`.
**Warning signs:** Page-1 and page-2 overlap is nondeterministic in tests.

### Pitfall 12: Double offset application in the pipeline
**What goes wrong:** Pipeline passes `options` (offset=N) to hybrid, which slices; the pipeline slices again — page 2 returns the wrong rows or empty.
**Why:** F19 only adjusts fetch size and reuses the caller's options, including offset.
**How to avoid:** Pipeline always calls hybrid with `offset=0` and `limit=limit+offset`; hybrid slices only for direct callers.
**Warning signs:** `--offset 5 --limit 5` returns rank 11–15 or nothing.

### Pitfall 13: MCP-only startup never runs `SchemaManager`
**What goes wrong:** After an upgrade, a user who starts only the MCP server (watch off) keeps the single-column FTS and the title column silently does nothing until some CLI command opens the DB.
**Why:** MCP transports construct `SearchBackend` and use `DatabaseConnection` per request; no `init_schema` call exists in the MCP path (verified by grep).
**How to avoid:** Run `Database(db_path).init_schema()` once in `SearchBackend.__init__` (cheap detection after first run) or at transport startup; add a test. If the planner defers this to Phase 22, record it as an explicit gap.
**Warning signs:** Title queries work after `sif index update` but not in a fresh MCP process.

### Pitfall 14: Attach refactor breaks the locked D-09 marker contract tests
**What goes wrong:** Removing searcher-level attach breaks `tests/unit/search/test_staleness.py:262` and `test_context_attach.py` expectations; a "fix" that relaxes assertions hides a marker regression.
**Why:** Those tests pin the current "every searcher exit attaches" contract.
**How to avoid:** Rewrite them to the new single-owner contract with the rationale in docstrings; assert one attach per entry path (CLI search/vsearch/query, MCP pipeline/fallback, pipeline prefixes), plus marker byte-parity on the existing legacy-verbatim context fixture.
**Warning signs:** Staleness markers or contexts disappear from one exit path after the refactor.

### Pitfall 15: `--force` semantics drift
**What goes wrong:** Reusing `force=True` to drive the migration purges chunks/embeddings for every document, forcing a full re-embed — exactly what D-09 forbids.
**Why:** Today `force` skips the checksum check and takes the full path.
**How to avoid:** Migration is its own flag (`migrating`); `--force` skips the checksum skip but still uses body discrimination. Test both.
**Warning signs:** An upgrade reports N updated and then `sif index embed` re-embeds the whole corpus.

### Pitfall 16: Title-signal duplication with H1
**What goes wrong:** Many Markdown notes start with an H1 identical to the frontmatter title, so the title text appears in both FTS columns and gets double weight.
**Why:** Titles and H1s are commonly duplicated; the body contains the H1.
**How to avoid:** Record the effect in the bench narrative; QUAL-03 (Phase 24) owns the breadcrumb-duplication experiment. Do not silently strip H1s here.
**Warning signs:** Title-leg metrics move more than expected; short common-word titles dominate.

### Pitfall 17: CJK title expectations
**What goes wrong:** Promising lexical gains for Chinese titles; FTS5 porter treats contiguous CJK runs as single tokens (PITFALLS P5).
**How to avoid:** Scope the title-FTS claim to EN-tokenized titles; keep the ZH claim to vector behavior.
**Warning signs:** ZH title-leg metrics unchanged; a reviewer reads the change as a universal win.

## Code Examples

### Parser dispatch + canonical checksum (target shape)
```python
# src/sif/indexing/parser.py
def canonical_metadata_json(metadata: dict[str, Any]) -> str:
    return json.dumps(metadata, sort_keys=True, default=str,
                      ensure_ascii=False, separators=(",", ":"))

def compute_checksum(content: str, metadata: dict[str, Any]) -> str:
    return hashlib.sha256(
        content.encode() + b"\x00" + canonical_metadata_json(metadata).encode()
    ).hexdigest()

class MarkdownParser:
    def parse(self, file_path: Path) -> ParsedDocument:
        ...
        checksum = compute_checksum(body, metadata)
```
`TextParser`/`CodeParser` call the same helper with their metadata (`{}` / `{"language": ...}`). `DocumentRepository` persists `canonical_metadata_json(document.metadata)`.

### Fast/full discrimination in `IncrementalIndexer._process_file`
```python
body_same = parsed.content == existing.content
if existing.checksum == parsed.checksum and not force and not migrating:
    if existing.mtime != parsed.mtime:
        with self._conn:
            self._conn.execute("UPDATE documents SET mtime = ? WHERE id = ?",
                               (parsed.mtime, existing.id))
    self._notify(progress, f"unchanged {file_path.name}")
    return "skipped"
if body_same:
    with self._conn:
        existing.title = parsed.title
        existing.metadata = parsed.metadata
        existing.checksum = parsed.checksum
        existing.file_size = len(parsed.content.encode())
        existing.mtime = parsed.mtime
        self._doc_repo.update(existing)      # chunks + embeddings preserved
    return "metadata"
# else: existing full path (purge chunks/embeddings, update row)
```

### Convention marker (per collection, `index_meta`)
```python
CONVENTION_VERSION = 2
key = f"convention:{collection.id}"
migrating = meta.get(key) != str(CONVENTION_VERSION)
if migrating:
    self._notify(progress, f"migrate {scan_result.file_count}")
...
if migrating and failed == 0:
    with self._conn:
        meta.set(key, str(CONVENTION_VERSION))
```

### Title-FTS migration (SchemaManager target shape)
```python
def _fts_column_names(self, table: str) -> list[str] | None:
    row = self.db.execute(
        "SELECT sql FROM sqlite_master WHERE type='table' AND name=?", (table,)
    ).fetchone()
    if not row or not row[0]:
        return None
    match = re.search(r"USING\s+fts5\s*\((.*?)\)", row[0], re.IGNORECASE | re.DOTALL)
    if not match:
        return None
    columns_clause = match.group(1).split("content=", 1)[0]
    return [c.strip().strip("'\"") for c in columns_clause.split(",") if c.strip()]

needs_title_rebuild = (
    (columns := self._fts_column_names("documents_fts")) is not None
    and "title" not in [c.lower() for c in columns]
)
```

### Weighted BM25 with min_score before pagination
```sql
WITH matched AS MATERIALIZED (
    SELECT rowid, bm25(documents_fts, :content_weight, :title_weight) AS score
    FROM documents_fts
    WHERE documents_fts MATCH :q
      AND (:min_score = 0.0 OR score >= (1.0 - 1.0 / :min_score))
)
SELECT d.id AS document_id, d.title, d.path, c.name AS collection_name, m.score AS score
FROM matched m
JOIN documents d ON m.rowid = d.rowid
JOIN collections c ON d.collection_id = c.id
WHERE d.collection_id IN (...)
ORDER BY m.score
LIMIT :limit OFFSET :offset
```
(Use `?` positional binds in the actual code; the named form is for readability. Note SQLite cannot use a select alias in the same WHERE in all contexts — bind the precomputed threshold `1 - 1/min_score` from Python instead of computing it in SQL.)

### CLI offset option and global rank
```python
@click.option("--offset", type=click.IntRange(min=0), default=0,
              help="Result offset for pagination (default: 0)")
...
options = SearchOptions(limit=limit, offset=offset, ...)
...
for position, result in enumerate(page, 1):
    result.rank = offset + position
```

### MCP input + hand-written schema sync
```python
class QueryInput(BaseModel):
    ...
    offset: int = Field(default=0, ge=0)
    per_chunk: bool = False

# handlers.QueryToolHandler.input_schema["properties"] must add both:
"offset": {"type": "integer", "minimum": 0, "default": 0},
"per_chunk": {"type": "boolean", "default": False},
```
`SearchBackend.hybrid_search(..., offset: int = 0, per_chunk: bool = False)` forwards both into `SearchOptions`; the MCP `SearchResult` model gains `chunk_id`, `sequence`, `chunk_matches` and the re-map explicitly copies them.

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| One hardcoded `MarkdownParser` for every file | `create_parser(extension)` dispatch (already built and tested) | This phase wires it | Non-md content/titles/checksums change once; YAML corruption fixed |
| Body-only checksum, mtime-only skip | Body + canonical full-frontmatter checksum + metadata fast path | This phase | Tag/title edits become searchable without losing vectors; one convention bump |
| Global migration runner (`MigrationManager`) | `SchemaManager` idempotent detect-and-rebuild | Already the project convention (dead manager deleted) | Fresh/migrated DBs pay only detection reads |
| Single-column `documents_fts` | Two-column `documents_fts(content, title)` + weighted `bm25()` | This phase | Title-aware ranking; title terms join the DYM vocabulary |
| Dedup after RRF truncation | Per-doc dedup inside `VectorSearcher` before fusion; post-fusion safety net | This phase (recorded contract change) | Pages return `limit` distinct docs; no RRF inflation |
| Dead `SearchOptions.offset` / no CLI or MCP surface | `--offset`/MCP `offset`, one slice owner, global ranks | This phase | Deterministic pagination; Phase 20 composes filters with it |
| Double attach on the hybrid pipeline path | One attach at the entry-point exit | This phase | Removes 2–3 full `document_embeddings`/`contexts` scans per hybrid query |
| FTS vocab shadow survival unverified | Verified locally on a populated DB | This session | STATE research gap closed for planning purposes |

**Deprecated/outdated:**
- Do not route migrations through `MigrationManager` (deleted; ARCHITECTURE Anti-Pattern 5).
- Do not use `rank` for weighted ordering when weights ≠ 1.0; use the `bm25()` expression.
- Do not promise ZH lexical title wins.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | CI py3.10–3.13 cells ship SQLite ≥ 3.35 (needed for `MATERIALIZED`; already used today) | Standard Stack / Validation | The SQL form already ships in production code (F17 SQL), so the assumption is only about the new code; low |
| A2 | The 150-document committed fixture corpus is a sufficient stand-in for D-12 measurement when no personal corpus is available | Pattern 7 | Corpus-specific weights may not generalize; the gate would be weaker than intended — record the limitation |
| A3 | A per-leg × split gate extension is acceptable additive scope | Pattern 7 / Open Q5 | If deferred, the D-12 "body held-out" clause cannot be read directly from `--compare` output |
| A4 | Chunk-presence/`reindexed_paths` is a complete signal for embed candidates | Pattern 4(e) | A crashed embed txn could leave partial chunk state; existing per-file transactions are all-or-nothing, and pending-retry covers failures |
| A5 | Unknown-extension fallback should be `TextParser` | Pattern 4(a) | Changes unknown-extension titles/content once; a different choice is a product decision |
| A6 | `SearchOptions.title_weight` as an internal measurement override does not violate D-11 | Standard Stack / Pattern 7 | If judged a user-facing knob, measurement must monkeypatch the module constant instead |
| A7 | MCP `lex_search`/`vec_search` stay unregistered in Phase 19 | Open Q1 | If the requirement is read literally, Phase 19 must wire tools that Phase 22 owns |
| A8 | `--force` may keep chunks for unchanged bodies | Pattern 4(c) | Users relying on `--force` to purge chunks would need `sif index embed --force` instead |

## Open Questions (RESOLVED)

All twelve questions below were resolved during Phase 19 planning; each item names its resolution and the plan/task that implements it.
1. **MCP `lex_search`/`vec_search` are unregistered.** D-05 requires offset on all three MCP search tools, but only `query` exists as a handler (F30); Lex/Vec models are dead (F28). What we know: adding `offset` to the Pydantic models is trivial; rendering it reachable requires handlers + backend methods, which Phase 22 (MCP-05 lex/vec wiring) owns. **Recommendation:** add the fields to `QueryInput`, `LexSearchInput`, `VecSearchInput` and to `SearchBackend` signatures now (so Phase 22 has no schema gap), document that the tools themselves remain unregistered until Phase 22, and do not expand CORR-03 into tool registration. **Resolved:** recommendation adopted — offset fields land on all three inputs and on `SearchBackend`; registration stays Phase 22. Implemented by 19-05 Task 3.
2. **Convention marker scope.** Per-collection `index_meta` keys (recommended) vs a global row. Per-collection composes with `-c`, CLI watch `-c`, and per-collection watch reconciles, and is resumable per collection. Confirm the "empty collection → write marker silently" rule so creating a new collection does not print an upgrade notice. **Resolved:** per-collection `index_meta` keys, with an empty collection writing the marker silently (no `migrate` event). Implemented by 19-02 Task 2.
3. **Unknown-extension parser fallback.** `create_parser` returns `None` for extensions outside the map. Previous behavior parsed everything as Markdown. Recommend `TextParser()` fallback (whole file, first-line title) and include it in the migration; alternatives are `MarkdownParser()` (preserves old behavior but re-introduces the YAML quirk on arbitrary files) or skipping (loses previously indexed files). **Resolved:** `TextParser()` fallback adopted (whole-file content, first-line title). Implemented by 19-01 Task 1.
4. **Migration failure policy.** D-09 says clear the marker only after success. A permanently unreadable file (permission/encoding) would repeat the full pass and the notice on every index run. Options: (a) strict per D-09 (recommended for correctness; failures are already reported), (b) write the marker with a failed count and surface the failures separately. Decide and test with an invalid-UTF-8 fixture. **Resolved:** strict option (a) — the marker stays unwritten on any failure and the failed count is reported, so the next pass retries. Implemented by 19-02 Task 2.
5. **D-12 per-leg held-out gate.** The current comparison reports per-split gates and per-leg×language×length group gates, but not per-leg×split. Recommend a small additive `ComparisonReport` extension (per-leg and per-leg×split `noise_gate` fields in JSON/table) so "body/hybrid held-out must not regress" is directly checkable; otherwise document that the held-out summary pools legs and mask risk. **Resolved:** additive `ComparisonReport.legs` / `.leg_splits` gates adopted so the D-12 "body held-out" clause is directly readable from `--compare` output. Implemented by 19-09 Task 2.
6. **Title weight measurement mechanism.** Internal `SearchOptions.title_weight` override vs monkeypatching the module constant. Both satisfy D-11 if not exposed via CLI/settings. Recommend the option field for a repeatable harness and tests; pin the final constant with a behavior test. **Resolved:** internal `SearchOptions.title_weight` override adopted (not exposed via CLI/settings), with the final constant pinned by a behavior test. Implemented by 19-08 Task 2 (override) and 19-09 Task 3 (pin).
7. **Filename-stem fallback titles.** No provenance exists; indexing `documents.title` includes stems. If the D-12 gate fails on short common-word filenames, the only options are a Phase 24 provenance/title-breadcrumb change or recording the rejection. Confirm we accept the fallback for this phase. **Resolved:** the fallback is accepted; the H1-duplication caveat is recorded in the snapshot rationale when observed, and a D-12 rejection with numbers is a valid outcome. Implemented by 19-08 Task 3 and 19-09 Task 3.
8. **Offset upper bound.** `--offset`/MCP `offset` only require ≥0. A huge offset is a cheap DoS (SQLite must skip rows, and vector dedup escalation targets `limit+offset`). Recommend a documented practical cap or at least clamp the vector escalation ceiling independently of offset; confirm the Click/Pydantic bound. **Resolved:** no arbitrary offset cap is imposed beyond validation (`IntRange(min=0)` / `Field(ge=0)`); the vector escalation ceiling is clamped independently at `_MAX_FETCH_K = 2048`, and past-end offsets return an empty page. Implemented by 19-05 Task 2 and 19-06 Task 1.
9. **`chunk_matches`/`chunk_id` values in `--per-chunk` mode.** Recommend `chunk_matches=0`/unused and `chunk_id`/`sequence` populated for vector chunk rows; BM25 rows show `path` only. Confirm the table/JSON/MCP shapes. **Resolved:** per-chunk mode leaves `chunk_matches` at 0 and populates `chunk_id`/`sequence` for vector chunk rows; BM25 rows stay document-keyed with a null chunk id. Implemented by 19-06 Task 1 and 19-07 Task 1.
10. **`file_size` refresh.** Recommended in both fast and full paths (repository already writes it; the current stale value also mutates the bench fingerprint after a body change). Confirm no consumer depends on the old stale semantics. **Resolved:** `file_size` is refreshed on both the metadata fast path and the full path. Implemented by 19-02 Task 1.
11. **MCP-only schema init.** Recommend `SearchBackend.__init__`/transport startup runs `init_schema` once so CORR-04 applies to MCP-only users; otherwise record as a Phase 22 gap. **Resolved:** `SearchBackend.__init__` runs `Database.init_schema(embedding_dim=self.settings.embedding_dim)` once. Implemented by 19-09 Task 1.
12. **Ranking-contract goldens inventory.** Confirm the plan owns updating: `tests/unit/search/test_hybrid.py` SC1 snapshot, `tests/fixtures/bench/heldout_defaults.json`, `tests/unit/search/test_bench_snapshot.py` expectations, `tests/unit/cli/test_search.py` CSV header/JSON shapes, BM25/vector score tests, `tests/unit/indexing/test_parser_checksum.py`, `test_incremental.py` checksum assertions, and `tests/integration/test_incremental_equivalence.py`. **Resolved:** the inventory is owned by 19-06 Task 2 (SC1 hybrid golden, dedup rationale), 19-06 Task 3 (held-out snapshot + bench-snapshot test), 19-07 Task 1 (CLI JSON shapes), 19-08 Task 3 (title-column goldens and broad fixture sweep), and 19-09 Task 3 (final-weight snapshot refresh).

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|-------------|-----------|---------|----------|
| Python ≥3.10 | Whole project | ✓ | 3.13.9 local; 3.10–3.13 CI matrix | — |
| SQLite FTS5 + `MATERIALIZED` | Title FTS, BM25 CTE | ✓ | 3.51.0 local | — (already required by shipped code) |
| sqlite-vec | Vector dedup tests/migration checks | ✓ | 0.1.9 | Tests skip when unavailable (existing discipline); migration itself does not need vec0 |
| python-frontmatter | Parser + YAML fixtures | ✓ | 1.1.0 | — |
| pytest/pytest-cov | Validation | ✓ | 9.1.1 | — |
| ruff / ty | Quality gates | ✓ | dev extras | — |
| Embedding model | Hybrid personal-eval arm | not required for the D-12 BM25 gate | — | `--bm25-only` (deterministic, offline); hybrid arm only if the embed extra/model is available |
| Committed fixture corpus | Scratch personal-bench index | ✓ | 150 `.md` files under `tests/fixtures/bench/corpus` | Real personal corpus if ≥50 docs |

**Missing dependencies with no fallback:** none.
**Missing dependencies with fallback:** real embedder/model for a hybrid-arm measurement (fallback: `--bm25-only`, which isolates the changed leg).

## Validation Architecture

`workflow.nyquist_validation` is `true` in `.planning/config.json`.

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 9.1.1 + pytest-cov (fail_under=90) |
| Config file | `pyproject.toml` `[tool.pytest.ini_options]`, `[tool.coverage.report]` |
| Quick run command | `pytest tests/unit/search tests/unit/indexing tests/unit/database/test_schema.py -x` |
| Full suite command | `pytest` (then `ruff check src tests && ruff format --check src tests && ty check src/sif`) |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| CORR-01 | frontmatter-only edit becomes searchable; chunks/embeddings preserved; md body byte-identical | unit/integration | `pytest tests/unit/indexing/test_incremental.py -x` (new cases) | ✅ extend |
| CORR-01 | parser dispatch per extension; YAML `---` whole-file; date metadata storable | unit | `pytest tests/unit/indexing/test_parser.py tests/unit/indexing/test_parser_checksum.py -x` | ✅ extend/replace checksum contract |
| CORR-01 | convention marker migrates per collection, fast path, failure leaves marker | unit/integration | `pytest tests/unit/indexing/test_incremental.py -x` (new migration cases) | ❌ new cases |
| CORR-01 | watcher embed depth does not duplicate chunks on metadata-only edit | unit | `pytest tests/unit/indexing/test_watcher.py -x` (new) | ❌ Wave 0 |
| CORR-02 | vector dedup: distinct docs, best chunk, `chunk_matches`, escalation | unit | `pytest tests/unit/search/test_vector.py -x` (new real-vec0) | ✅ extend |
| CORR-02 | hybrid default one row/doc; `--per-chunk` chunk rows; RRF metadata merge | unit/integration | `pytest tests/unit/search/test_hybrid.py tests/unit/search/test_rrf.py -x` | ✅ extend |
| CORR-02 | chunky-doc regression returns exactly `limit` distinct docs | integration | new `tests/integration/test_search_correctness.py` | ❌ Wave 0 |
| CORR-03 | offset page continuity, past-end empty, global ranks, offset=0 golden | unit/integration | new `tests/unit/cli/test_search_pagination.py` + integration | ❌ Wave 0 |
| CORR-03 | BM25 min_score before pagination (no holes) | unit | `pytest tests/unit/search/test_bm25.py -x` (new) | ✅ extend |
| CORR-03 | MCP offset/per_chunk forwarding + schema sync | unit | `pytest tests/unit/mcp/test_backend.py -x` (new) | ✅ extend |
| CORR-04 | legacy DB detect/rebuild on populated DB; title-only match; vocab+DYM survive; triggers sync; idempotent | unit/integration | new `tests/unit/database/test_schema_title_fts.py` | ❌ Wave 0 |
| CORR-04 | weighted bm25 ordering + constant pin + `1.0/1.0 == rank` | unit | `pytest tests/unit/search/test_bm25.py -x` | ✅ extend |
| CORR-04 | mtime index exists on fresh and migrated DBs | unit | `pytest tests/unit/database/test_schema.py -x` | ✅ extend |
| CORR-05 | exactly one attach on every exit path; markers unchanged | unit/integration | `pytest tests/unit/search/test_staleness.py tests/unit/search/test_context_attach.py -x` (rewrite) | ✅ rewrite |
| Goldens | SC1 snapshot, bench snapshot, CSV/JSON shapes updated with rationale | unit | `pytest tests/unit/search/test_hybrid.py tests/unit/search/test_bench_snapshot.py tests/unit/cli/test_search.py -x` | ✅ update |
| Docs | generated CLI reference has `--offset`/`--per-chunk`; no diff after generate | CI/unit | `make docs-generate && git diff --exit-code docs/` | ✅ |

### Sampling Rate
- **Per task commit:** the requirement-specific command above.
- **Per wave merge:** full `pytest` + `ruff check src tests` + `ruff format --check src tests` + `ty check src/sif`.
- **Phase gate:** full suite green (fail_under=90) before `/gsd-verify-work`.

### Wave 0 Gaps
- [ ] `tests/integration/test_search_correctness.py` — chunky-doc dedup, offset continuity, per-chunk composition, one-attach spy (CORR-02/03/05).
- [ ] `tests/unit/database/test_schema_title_fts.py` — populated legacy DB detect/rebuild, vocab survival, DYM, trigger sync (CORR-04).
- [ ] `tests/unit/cli/test_search_pagination.py` — `--offset`/`--per-chunk` flags, global ranks, JSON/CSV fields (CORR-03).
- [ ] `tests/unit/indexing/test_watcher.py` new migration/fast-path embed cases (CORR-01).
- [ ] Fixtures: `.yaml` `---` (three forms), YAML date, frontmatter-only edit, chunky document (one doc ≥5 chunks), legacy single-column FTS DB builder.
- [ ] Deterministic benchmark drivers use `ConceptEmbedder`; migration tests use `tmp_path` + real `SchemaManager`.

## Security Domain

`security_enforcement` is absent from `.planning/config.json` → treat as enabled.

### Applicable ASVS Categories
| ASVS Category | Applies | Standard Control |
|---------------|---------|------------------|
| V2 Authentication | no | Loopback single-user; no auth surface in scope |
| V3 Session Management | no | MCP session shell owned by Phase 22 |
| V4 Access Control | no | No new access-control decisions |
| V5 Input Validation | yes | Click `IntRange(min=0)`; Pydantic `Field(ge=0)` for offset; bounded `fetch_k` escalation; existing FTS query sanitizer unchanged; no user-supplied SQL |
| V6 Cryptography | no | No crypto; hashes are integrity/change-detection only (SHA-256 via stdlib) |

### Known Threat Patterns for this stack
| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| SQL injection via FTS weights/offset/limit | Tampering | Bind every value (`bm25(..., ?, ?)`, `LIMIT ? OFFSET ?`); weights are internal constants; never interpolate user text |
| FTS query syntax injection (`"`, `*`, `:`, `^`, parentheses) | Tampering | Existing `_sanitize_term` + quoted prefix phrases; unchanged |
| Resource exhaustion via huge offset or chunky-doc dedup escalation | Denial of Service | Bound `fetch_k` escalation with an independent ceiling; document/limit offset; MCP `ge=0` + optional practical max |
| Untrusted document text reaching renderers/agents | Tampering/Info disclosure | Existing Rich `escape`, XML sanitization, JSON encoding; project skills already treat content as data; new fields are metadata only |
| Stale/incorrect trust signals (staleness/context markers) | Repudiation | One attach owner; derived staleness preserved; marker parity tests |
| Migration window serving stale vocab/terms | Tampering (data integrity) | Drop vocab before FTS; rebuild inside `init_schema`; integrity-check test |

## Sources

### Primary (HIGH confidence)
- **Local source at HEAD `fb7f65b`** — all `src/sif/` files cited with line ranges and verbatim quotes in "Verified Code Facts"; `git status --porcelain src/` clean.
- **Local SQLite 3.51.0 experiments (this session)** — multi-column external-content FTS; zero-parameter IF NOT EXISTS behavior; drop/recreate/rebuild with fts5vocab; NULL title insert/delete; bm25 weight mapping with bind parameters; alias rejection; weighted-order equals `rank` at 1.0/1.0; `rebuild`/`integrity-check`; the exact title-FTS migration sequence on a populated DB created by `SchemaManager`.
- **Local python-frontmatter 1.1.0 experiments (this session)** — leading `---` with/without closing delimiter, multi-document YAML, frontmatter-only empty body, `datetime.date` metadata and `json.dumps` failure.
- **Phase artifacts** — `19-CONTEXT.md` (locked decisions), `.planning/research/ARCHITECTURE.md` (tier-2 pipeline, migration inventory), `PITFALLS.md` P12/P14/P15/P16/P17/P18/P5, `FEATURES.md`, `SUMMARY.md`, `18-CONTEXT.md`, `18-VERIFICATION.md`, `18-UAT.md` (instrument behavior and measured noise floor 0.0103 at N=97).

### Secondary (MEDIUM confidence)
- [SQLite FTS5 official documentation](https://sqlite.org/fts5.html) — `bm25()` weight ordering and defaults (§5.1.1), `'rebuild'` (§6.12), external-content `'delete'` requirements and UPDATE-as-DELETE+INSERT (§6.3/§4.4.4). Every cited statement was independently reproduced locally.
- `.planning/phases/18-quality-instrument-personal-bench-rapidfuzz-dym/18-03-SUMMARY.md` — `--compare` behavior, fingerprint refusal, bootstrap gate, saved-run format.

### Tertiary (LOW confidence — do not cite as fact)
- WebSearch for python-frontmatter leading-`---` edge cases returned only general package documentation and no issue/behavior specific to this case; the behavior above is from the local reproduction, not the search.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — no new dependencies; versions and behaviors verified locally.
- Architecture/integration: HIGH — every call site and line quoted at HEAD; empirical migration reproduction.
- Schema migration mechanics: HIGH — title-FTS sequence executed on a populated `SchemaManager` DB; vocab/DYM/triggers/integrity verified.
- Pagination/dedup semantics: HIGH — code paths verified; threshold math derived and checked; page-continuity definition reasoned from RRF inputs.
- Benchmark/gate procedure: MEDIUM — the Phase 18 instrument is verified, but the per-leg × split gate needs a small extension or a documented interpretation (Open Q5); corpora representativeness is A2.
- MCP surface: MEDIUM — model/backend plumbing is clear, but lex/vec tool registration is Phase 22 scope (Open Q1) and MCP-only schema init is a gap.

**Research date:** 2026-11-15
**Valid until:** 2026-12-15 for the in-repo facts (stable); re-verify SQLite/FTS5 behavior only if the runtime SQLite major version changes.
