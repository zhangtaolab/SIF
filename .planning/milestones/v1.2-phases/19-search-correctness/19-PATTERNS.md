# Phase 19: Search Correctness - Pattern Map

**Mapped:** 2026-11-15
**Files analyzed:** 35 (16 source, 1 generated doc, 18 test/fixture)
**Analogs found:** 35 / 35 (all existing-code analogs verified git-tracked at HEAD `fb7f65b`)

Every analog path below was verified with `git ls-files -- <path>` (non-empty = tracked). No `.gsd/capabilities/*` mirror paths are named.

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `src/sif/core/models.py` | model / result contract | transform | itself: `SearchResult`, `SearchOptions`, `Document.__post_init__` | exact |
| `src/sif/database/schema.py` | schema migration | DDL batch (detect-and-rebuild) | itself: `_fts_is_misconfigured`, `_drop_legacy_fts_triggers`, `_create_fts_tables`, `_create_vector_tables` | exact |
| `src/sif/database/repositories.py` | repository (new `IndexMetaRepository`) | CRUD (key/value get/set) | `LLMCacheRepository.get/set`; `QueryLogRepository.add/clear` (same file) | role-match |
| `src/sif/indexing/parser.py` | parser / service | file-I/O + transform | itself: `MarkdownParser.parse`, `create_parser` | exact |
| `src/sif/indexing/incremental.py` | service / worker | batch file-I/O, per-file transactions | itself: `_process_file`, `update_collection`, `IncrementalResult` | exact |
| `src/sif/indexing/watcher.py` | event-driven service | event-driven batch | itself: `_EmbedSession.embed_documents`, `_run_burst`, `_run_reconcile` | exact |
| `src/sif/search/bm25.py` | search strategy | request-response (SQL) | itself: two SQL branches, `min_score` loop | exact |
| `src/sif/search/vector.py` | search strategy | request-response (KNN) | itself: `_search_with_vec` | exact |
| `src/sif/search/hybrid.py` | search orchestrator / pipeline | request-response | itself: `HybridSearcher.search`, `SearchPipeline.search` | exact |
| `src/sif/search/rrf.py` | utility (fusion) | transform | itself: `RRFFusion.fuse` | exact |
| `src/sif/search/context_attach.py` | utility (enrichment) | batch | itself: `attach_path_contexts`; the three `_attach_contexts` methods | exact |
| `src/sif/search/personal_bench.py` | bench instrument | batch | itself: `ComparisonReport`, `noise_gate`, `compare_saved_run` | exact |
| `src/sif/cli/commands/search.py` | CLI controller | request-response | itself: option blocks + 5 renderers; `commands/index.py::_render_index_event` | exact |
| `src/sif/mcp/protocol.py` | DTO / input model | transform | itself: `QueryInput`, `LexSearchInput`, `VecSearchInput`, `SearchResult` | exact |
| `src/sif/mcp/handlers.py` | controller / adapter | request-response | itself: `QueryToolHandler.input_schema` + `handle` | exact |
| `src/sif/mcp/backend.py` | service boundary | request-response | itself: `hybrid_search` re-map; `mcp/watch_host.py` for `init_schema` | exact |
| `docs/cli-reference.md` | generated doc | — | `scripts/generate_cli_ref.py` (auto-traverses Click options) | exact (generated, never hand-edit) |
| `tests/integration/test_search_correctness.py` | integration test | — | `tests/unit/search/test_hybrid.py::TestHybridSC1PipelineGolden._build_db`; `tests/support/bench.py::build_bench_db` | role-match |
| `tests/unit/database/test_schema_title_fts.py` | unit test (migration) | — | `tests/unit/database/test_schema.py::TestSchemaRealSQLiteCoverage`, `::TestFtsUpdateTrigger`, `::TestVocabShadowTable` | role-match |
| `tests/unit/cli/test_search_pagination.py` | unit test (CLI) | — | `tests/unit/cli/test_search.py::TestSearchOutputBranches` | role-match |
| `tests/unit/indexing/test_watcher.py` | unit test (new cases) | — | itself: `TestEmbedDepth` | exact |
| `tests/unit/indexing/test_parser.py` | unit test (fixtures) | — | itself: `TestDocumentParsers` | exact |
| `tests/unit/indexing/test_parser_checksum.py` | unit test (rewrite contract) | — | itself | exact |
| `tests/unit/indexing/test_incremental.py` | unit test (fast path/migration) | — | itself | exact |
| `tests/unit/search/test_vector.py` | unit test (dedup/escalation) | — | itself: `TestVectorFilteredRecall._build_db` | exact |
| `tests/unit/search/test_hybrid.py` | unit test (golden + per-chunk) | — | itself: `TestHybridSC1PipelineGolden` | exact |
| `tests/unit/search/test_rrf.py` | unit test (fusion key/merge) | — | itself | exact |
| `tests/unit/search/test_bm25.py` | unit test (weights/min_score) | — | itself | exact |
| `tests/unit/search/test_staleness.py` | unit test (attach contract rewrite) | — | itself: `TestSearcherDelegation` | exact |
| `tests/unit/search/test_context_attach.py` | unit test (attach contract rewrite) | — | itself | exact |
| `tests/unit/search/test_bench_snapshot.py` + `tests/fixtures/bench/heldout_defaults.json` | golden snapshot | — | itself + `tests/support/bench.py` | exact |
| `tests/unit/cli/test_search.py` | unit test (CSV/JSON shapes) | — | itself | exact |
| `tests/unit/mcp/test_backend.py` | unit test (offset/per_chunk forward) | — | itself: `TestQueryToolHandlerWeightPassThrough` | exact |
| `tests/unit/database/test_schema.py` | unit test (mtime index/drop_all) | — | itself | exact |
| `tests/integration/test_incremental_equivalence.py` | integration golden | — | itself | exact |

## Pattern Assignments

### `src/sif/core/models.py` (model, transform)

**Analog:** itself.

**Imports pattern** (lines 5-11): stdlib only (`hashlib`, `uuid`, `dataclasses`, `datetime`, `enum`, `pathlib`, `typing`). No third-party imports in the core models module.

**Additive-field contract** — `SearchResult` (lines 233-268). The existing `vectors_stale` field is the exact precedent for adding `chunk_id`, `sequence`, `chunk_matches`: defaulted, commented, and listed in `to_dict()` (goldens compare full dicts):

```python
    rank: int = 0
    scores: dict[str, float | None] = field(default_factory=dict)
    snippet: str | None = None
    context_description: str | None = None
    # Derived at query time (D-08): True when this result's document has no
    # rows in document_embeddings — the tiered-depth vector lag. Defaulted so
    # every constructor stays valid; rides to_dict() into --json output.
    vectors_stale: bool = False

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "document_id": self.document_id,
            ...
            "vectors_stale": self.vectors_stale,
        }
```

New fields: `chunk_id: str | None = None`, `sequence: int | None = None`, `chunk_matches: int = 0`. Insert them into `to_dict()` in a stable position; `test_hybrid.py::TestHybridSC1PipelineGolden.SNAPSHOT` and `test_rrf.py::TestRRFSC1Golden` compare whole dicts and must be updated with rationale.

**Options pattern** — `SearchOptions` (lines 271-294): `offset: int = 0` already exists (line 276); add `per_chunk: bool = False` next to it and (optionally) an internal `title_weight: float = 1.0` measurement override. Keep the "defaults equal today's behavior" comment style (lines 288-294).

**Checksum bug site** — `Document.__post_init__` (lines 146-154) falls back to `sha256(content)` when `checksum is None`; the create path in `incremental.py` never passes `checksum=`, so new documents get body-only hashes even after the convention changes. The canonical helper (Pattern 4b in RESEARCH) should live where `Document` and all three parsers can import it without a cycle; `core/models.py` is the natural home.

---

### `src/sif/database/schema.py` (schema migration, detect-and-rebuild)

**Analog:** itself. This file contains the proven template the title-FTS migration must copy.

**Create order** (`create_all`, lines 18-29): tables first, FTS after documents/chunks, vector tables last, indexes last. Insert `_create_index_meta_table()` before `_create_fts_tables()` and keep `_create_indexes()` last.

**Detection gate precedent** (lines 221-231) — `_fts_is_misconfigured` checks only `content=`, so it cannot detect a missing `title` column; the title gate needs to parse the column list:

```python
        def _fts_is_misconfigured(table_name: str, expected_content: str) -> bool:
            """Check if an existing FTS5 table lacks the correct content= setting."""
            cursor = self.db.execute(
                "SELECT sql FROM sqlite_master WHERE type='table' AND name=?",
                (table_name,),
            )
            row = cursor.fetchone()
            if not row:
                return False  # table does not exist; not misconfigured
            sql = row[0] or ""
            return f"content='{expected_content}'" not in sql
```

The regex-parse precedent for `sqlite_master.sql` is `_create_vector_tables` (lines 361-376): `re.search(r"FLOAT\[(\d+)\]", row[0])`. Use the same shape for `USING fts5(...)` column extraction.

**Detect-and-drop-recreate** (`_drop_legacy_fts_triggers`, lines 193-216): log why, `DROP TRIGGER` each legacy form, then let the shared creation path recreate them. The title migration follows the exact same contract: drop the three `documents_fts_*` triggers, drop `documents_fts_v` FIRST (RESEARCH Pitfall 6), drop `documents_fts`, recreate two-column DDL, `('rebuild')`, recreate vocab, recreate triggers.

**Fresh DDL + triggers** (lines 244-298): extend `documents_fts` to `(content, title, content='documents', content_rowid='rowid', tokenize='porter')`; rewrite the three document triggers to carry `(rowid, content, title)` including `old.title` on delete. Chunks triggers (lines 301-324) stay byte-identical.

**Indexes** (`_create_indexes`, lines 387-401): add `idx_documents_mtime` beside the checksum/collection/path indexes.

**Reset list** (`drop_all`, lines 421-438): add `index_meta` to the `tables` list; it must be dropped like `query_log` so test isolation holds.

**Error handling:** `_migrate_path_contexts` (lines 108-132) is the atomic-migration precedent (SAVEPOINT + rollback + raise). The title rebuild is DDL-only and detection-gated; keep it idempotent so fresh/migrated DBs pay one `sqlite_master` read.

---

### `src/sif/database/repositories.py` (new `IndexMetaRepository`, CRUD)

**Analog:** `LLMCacheRepository` (same file, lines 536-605) — the key/value get/set pair matches the `index_meta` marker exactly, including the `__init__(self, db: sqlite3.Connection)` shape.

**Class shape** (lines 536-541):

```python
class LLMCacheRepository:
    """Repository for LLM cache operations."""

    def __init__(self, db: sqlite3.Connection) -> None:
        """Initialize the LLM cache repository."""
        self.db = db
```

**get/set pattern** (lines 543-605): parameterized SQL, a miss returns `None`, `set` uses `INSERT OR REPLACE`. `IndexMetaRepository.get(key) -> str | None` / `set(key, value)` follows this; do NOT inherit from `sif/database/repository.py` (those abstract interfaces are test-only mocks, per CLAUDE.md).

**Canonical metadata storage** — two write sites must switch from raw `json.dumps` to `canonical_metadata_json(...)` (RESEARCH Pattern 4b; fixes the YAML-date `TypeError`):

- `DocumentRepository.create` line 163: `json.dumps(document.metadata) if document.metadata else "{}"`
- `DocumentRepository.update` line 232: same expression

Both already round-trip through `_row_to_document` line 307 (`json.loads(row["metadata"])`), so stored form and hashed form agree after the change.

---

### `src/sif/indexing/parser.py` (parser, file-I/O + transform)

**Analog:** itself.

**Imports** (lines 5-12): `hashlib`, `re`, `types`, `dataclasses`, `pathlib`, `typing`, `frontmatter`.

**Checksum site to replace** (lines 66-71):

```python
        # Calculate checksum over the body (frontmatter stripped), matching the
        # storage convention: the create path stores sha256 of Document.content
        # (the body, see core.models.Document.__post_init__), so comparing
        # against a whole-file hash never matches and every document is
        # misreported as changed on 'index update'.
        checksum = hashlib.sha256(body.encode()).hexdigest()
```

Add `canonical_metadata_json(metadata)` + `compute_checksum(content, metadata)` as module-level helpers (or import from core/models) and call the same helper from all three parsers:
- `MarkdownParser.parse` line 71
- `TextParser.parse` line 106
- `CodeParser.parse` line 173

**Factory already correct** (`create_parser`, lines 185-203): `.md/.markdown/.mdx` → `MarkdownParser`, `CodeParser.LANGUAGE_MAP` (includes `.yaml/.yml`) → `CodeParser`, `.txt/.rst/.adoc` → `TextParser`, else `None`. The `.yaml/.yml` routing is what fixes the `---` bug (CodeParser never calls `frontmatter.loads`). Recommended `None` fallback: `TextParser()` (RESEARCH Open Q3).

**Bug context:** `frontmatter.loads` behavior is verified in RESEARCH Pattern 4f — `---\na: 1\n---\n` yields empty body; `---` with no closing yields a leaked separator. Fixtures must cover all three forms.

---

### `src/sif/indexing/incremental.py` (service/worker, per-file transactions)

**Analog:** itself.

**Result dataclass to extend** (lines 42-55):

```python
@dataclass
class IncrementalResult:
    added: int = 0
    updated: int = 0
    removed: int = 0
    unchanged: int = 0
    failed: int = 0
```

Add `reindexed_paths: set[str] = field(default_factory=set, compare=False)` (and optionally `metadata_only: int = field(default=0, compare=False)`). `compare=False` keeps the ~25 `IncrementalResult(...)` equality assertions green (e.g. `test_watcher.py:1471`).

**Checksum skip to split into fast/full path** (lines 300-318):

```python
        if existing:
            # Check if changed
            if existing.checksum == parsed.checksum and not force:
                # Drift-compare convergence (14 REVIEW CR-01): ...
                if existing.mtime != parsed.mtime:
                    with self._conn:
                        self._conn.execute(
                            "UPDATE documents SET mtime = ? WHERE id = ?",
                            (parsed.mtime, existing.id),
                        )
                self._notify(progress, f"unchanged {file_path.name}")
                return "skipped"
```

Order for the new logic: checksum-skip (and not migrating) → mtime-only converge; else `body_same = parsed.content == existing.content` → metadata-only fast path (update title/metadata/checksum/file_size/mtime via `_doc_repo.update`, KEEP chunks/embeddings, return `"metadata"`); else the existing full path (lines 323-342: delete chunks + embeddings, update document).

**Create-path checksum bug** (lines 343-355): the `Document(...)` constructor omits `checksum=parsed.checksum`; pass it so new rows share the convention.

**Migration seam** (`update_collection`, lines 82-160): after `scanner.scan` + the `existing_docs` snapshot (lines 117-129), read the per-collection marker via `IndexMetaRepository`; when it mismatches, set `migrating=True`, emit `f"migrate {scan_result.file_count}"`, pass `migrating` into `_process_file`, and write the marker only when `failed == 0`. `update_paths` (lines 162-267) NEVER triggers migration (D-09), but still uses body discrimination. `_notify` (lines 269-273) is the presentation-free event channel; `_render_index_event` in the CLI is the only renderer.

---

### `src/sif/indexing/watcher.py` (event-driven service)

**Analog:** itself.

**Embed leg that appends without deleting** (lines 254-315) — the duplicate-chunk hazard:

```python
        for path in candidates:
            try:
                doc = doc_repo.get_by_path(str(path), collection.id)
                if doc is None:
                    continue
                chunks = chunker.chunk(doc.content)
                ...
                with self._conn:
                    for sequence, chunk in enumerate(chunks):
                        chunk.document_id = doc.id
                        chunk.sequence = sequence
                        chunk_repo.create(chunk)
                    searcher.add_embeddings_batch([...])
```

Candidate selection must come from `IncrementalResult.reindexed_paths`, not checksum diffs.

**Current checksum-diff selection to replace** (lines 870-910):

```python
    def _run_burst(self, collection: Collection, folded: FoldResult) -> IncrementalResult:
        ...
        before = self._checksums(collection, folded.index_candidates)
        result = indexer.update_paths(collection, paths, progress=progress)
        changed = {
            path for path in folded.index_candidates if self._path_changed(collection, path, before)
        }
        self._embed.embed_documents(collection, changed, progress)
        return result

    def _changed_since(...)  # lines 897-903
    def _path_changed(...)   # lines 905-910
```

Same substitution in `_run_reconcile` (lines 836-868): drop the `before = self._collection_checksums(...)` snapshot and feed `result.reindexed_paths` into `_embed.embed_documents`. Keep the single lock window and the `_pending_retry` union behavior (lines 209-212, 271, 314-315).

---

### `src/sif/search/bm25.py` (search strategy, request-response)

**Analog:** itself.

**Imports** (lines 1-11): stdlib + `sif.core.models`, `sif.search.context_attach`, `sif.search.staleness`, `sif.search.term_match`.

**Scoped SQL branch** (lines 76-93) — the CTE the weighted `bm25()` and pre-pagination `min_score` must extend:

```python
                WITH matched AS MATERIALIZED (
                    SELECT rowid, rank FROM documents_fts
                    WHERE documents_fts MATCH ?
                )
                SELECT
                    d.id as document_id,
                    d.title,
                    d.path,
                    c.name as collection_name,
                    m.rank as score
                FROM matched m
                JOIN documents d ON m.rowid = d.rowid
                JOIN collections c ON d.collection_id = c.id
                WHERE d.collection_id IN ({placeholders})
                ORDER BY m.rank
                LIMIT ? OFFSET ?
```

Target: `SELECT rowid, bm25(documents_fts, ?, ?) AS score` with the internal weight constant bound as parameters (never interpolated; RESEARCH Pitfall 5: the real table name is required even though `FROM documents_fts fts` may keep its alias). Apply `min_score` INSIDE the CTE/outer WHERE before `LIMIT/OFFSET` with the bound threshold `1 - 1/min_score` (RESEARCH Pitfall 4 math).

**Current threshold bug** (lines 112-122): `params.extend([options.limit, options.offset])` then score conversion + `if score < options.min_score: continue` AFTER pagination — this creates page holes and is what CORR-03 moves into SQL.

**Unfiltered branch** (lines 98-111) must stay byte-identical apart from the same weight/threshold additions; both branches need tests (Pitfall 5).

**Attach removal:** `_attach_contexts` (lines 147-149) is called at line 145; the single-attach refactor removes that call (the CLI will own it).

---

### `src/sif/search/vector.py` (search strategy, KNN)

**Analog:** itself.

**KNN SQL** (lines 87-99) — extend the SELECT/JOIN with chunk identity (RESEARCH Pattern 2 verified shape):

```python
        sql = f"""
            SELECT
                d.id as document_id,
                d.title,
                d.path,
                c.name as collection_name,
                distance as score
            FROM document_embeddings de
            JOIN documents d ON de.document_id = d.id
            JOIN collections c ON d.collection_id = c.id
            WHERE embedding MATCH ? AND k = ? {collection_filter}
            ORDER BY distance
        """
```

Add `de.chunk_id AS chunk_id` and `LEFT JOIN document_chunks dc ON dc.id = de.chunk_id` selecting `dc.sequence AS sequence` (legacy NULL chunk ids yield None/None).

**Over-fetch + trim** (lines 70-77, 104-131): `fetch_k = max(options.limit * 4, 50)`; loop applies `min_score` and appends; trim `results[: max(1, options.limit)]`; ranks assigned 1..N; `return self._attach_contexts(results)` at 131. Replace with: per-doc grouping (winner = first/best row, `chunk_matches = count`), escalation loop over `limit+offset` distinct docs with an independent ceiling, `[offset:offset+limit]` slice, global ranks `offset + position`, and no attach.

**Collection filter** (lines 65-68) and the exclude-all sentinel (lines 48-49) are unchanged.

---

### `src/sif/search/hybrid.py` (orchestrator/pipeline, request-response)

**Analog:** itself.

**Current order** (lines 59-99) — legs at `options.limit`, early returns, fusion, dedup, attach:

```python
        bm25_results = self.bm25.search(query, options)
        ...
        vector_results = self.vector.search(query_embedding, options)

        if not vector_results:
            return self._attach_contexts(bm25_results)
        if not bm25_results:
            return self._attach_contexts(vector_results)

        fused_results = self.rrf.fuse(
            [bm25_results, vector_results],
            options.limit,
            weights=[options.bm25_weight, options.vector_weight],
            k=options.rrf_k,
        )
        ...
        deduped = self._deduplicate_results(fused_results)
        return self._attach_contexts(deduped)
```

Target: call both legs with `replace(options, limit=options.limit + options.offset, offset=0)`; pass the per-chunk fusion key; fuse at `limit+offset`; keep `_deduplicate_results` (lines 101-119, currently sorts by score and reassigns ranks) as the post-fusion safety net for the default path; slice `[offset:offset+limit]`; set `result.rank = options.offset + position`; return WITHOUT attach.

**Current dedup** (lines 101-119) keeps the highest-score entry per `document_id`; the new safety net must also `max()` `chunk_matches` and adopt non-null chunk fields (RESEARCH Pitfall 3).

**Pipeline branches** (lines 201-216) return BM25/vector/HyDE with `_apply_snippets`; each currently inherits searcher-level attach. After the refactor the pipeline must attach exactly once per exit. **Hybrid branch:** fetch options built at lines 248-254 (`max(limit + offset, candidate_limit)`) — always call `self.hybrid.search(q, replace(fetch_options, offset=0))`; cross-query fuse at 270; rerank at 273-279; snippets at 282; slice then one attach replacing line 284 (`return self.hybrid._attach_contexts(results)`).

---

### `src/sif/search/rrf.py` (fusion utility, transform)

**Analog:** itself.

**Fusion key and result construction** (lines 49-96) — RRF math stays unchanged:

```python
        scores: dict[str, tuple[float, SearchResult]] = {}
        for list_idx, results in enumerate(results_lists):
            weight = 1.0 if weights is None else weights[list_idx]
            for rank, result in enumerate(results, 1):
                doc_id = result.document_id
                rrf_score = weight * (1.0 / (k_eff + rank))
                ...
                if doc_id in scores:
                    existing_score, existing_result = scores[doc_id]
                    ...
                    scores[doc_id] = (existing_score + rrf_score, existing_result)
                else:
                    new_result = SearchResult(...)
```

Add an optional `key: Callable[[SearchResult], str] | None = None` parameter (default `lambda r: r.document_id`). In the merge branch adopt non-null `chunk_id`/`sequence` from the later result and `max()` `chunk_matches` — metadata merging only, no scoring change. Preserve the `1.0 * x == x` byte-identical comment (lines 52-55).

---

### `src/sif/search/context_attach.py` and `staleness.py` (batch enrichment)

**Analog:** itself.

**Shared helper shape** (`attach_path_contexts`, lines 24-62): empty-list early return, one constant query, Python-side two-sided `normalize_path`, never clobber an existing `context_description`:

```python
    if not results:
        return results
    cursor = db.execute(
        "SELECT target_id, content FROM contexts WHERE context_type = 'path' ORDER BY updated_at"
    )
    context_map = {normalize_path(row["target_id"]): row["content"] for row in cursor.fetchall()}
    for result in results:
        key = normalize_path(result.path)
        if key in context_map:
            result.context_description = context_map[key]
    return results
```

**Composition repeated today** in three `_attach_contexts` methods (bm25 147-149, vector 133-135, hybrid 121-123):

```python
        return mark_vector_staleness(self.db, attach_path_contexts(self.db, results))
```

Add one `enrich_results(db, results)` helper here (or in staleness.py) and have every entry point call it once. `staleness.py` (lines 34-77) is unchanged except its docstring contract references; keep the derived-signal, display-gate, and one-scan invariants.

---

### `src/sif/search/personal_bench.py` (bench instrument, batch)

**Analog:** itself (2145 lines; read targeted sections only).

**Comparison report contract** (lines 470-525): frozen dataclass with `splits: dict[str, GateResult]`, `groups: list[GroupGate]`, `suppressed`, and a `to_dict()` used by `--json`. A per-leg / per-leg×split gate extension (RESEARCH Open Q5) is additive here.

**Gate primitives to reuse, never re-implement** (lines 1774-1882):

```python
def noise_gate(
    baseline_values: Sequence[float],
    current_values: Sequence[float],
) -> GateResult:
    ...
    bootstrap = paired_bootstrap(deltas)
    mean_delta = bootstrap.mean
    noise_floor = 1.0 / len(deltas)
    excludes_zero = bootstrap.ci_low > 0 or bootstrap.ci_high < 0
    improvement = round(mean_delta, 6) >= EPSILON
    regression = round(mean_delta, 6) <= -EPSILON
    sufficient = len(deltas) >= SUPPRESS_BELOW
    exceeds_floor = abs(mean_delta) > noise_floor
```

**Comparison orchestration** (`compare_saved_run`, lines 2028-2145) shows where a per-leg gate slots in: after `splits` (2075-2081) and alongside `group_noise_gates` (2082-2086); `warrants_default_change=splits["heldout"].winner` (line 2143) is the D-12 gate precedent.

**Fingerprint constraint** (`corpus_fingerprint`, lines 1096-1106): hashes `path + checksum + file_size`, so B0 must be recorded after the CORR-01 checksum change.

---

### `src/sif/cli/commands/search.py` (CLI controller, request-response)

**Analog:** itself.

**Imports** (lines 1-30): stdlib + `click`, `rich`, `pydantic`, and `sif.*`. Keep new options in the existing decorator style.

**Option block precedent** (`search_cmd`, lines 429-450; `vsearch_cmd`, 602-623; `query_cmd`, 767-830). Add to all three:

```python
@click.option(
    "--offset",
    type=click.IntRange(min=0),
    default=0,
    help="Result offset for pagination (default: 0)",
)
```

Add `--per-chunk` (is_flag) only to `vsearch_cmd` and `query_cmd`. Flag defaults that resolve settings use `None` (e.g. `--rrf-k`, lines 800-805) — `--offset` has a literal `0`, so no precedence issue.

**Options construction** (lines 484-489, 679-684, 894-905) — pass `offset=offset` (and `per_chunk=per_chunk`). Resolution helpers live at the top (`_resolve_limit`, lines 57-59).

**Renderers** (the five output paths every new field must reach):
- JSON: `format_results_json` (87-93) → `SearchResult.to_dict()` auto-carries new fields.
- Dict/object dual-shape reader: `_field` (96-98) — reuse for `chunk_matches`/`sequence`/`chunk_id` on dict rows.
- CSV: `format_results_csv` (339-361) header is pinned by tests at line 348 (`rank,score,title,path,collection,vectors_stale`); adding columns requires updating `tests/unit/cli/test_search.py:1713`, `:2477-2484`, and `tests/test_docs.py` JSON schema expectations.
- Markdown/XML: `format_results_md` (364-385), `format_results_xml` (388-420) — XML uses fixed literals for booleans and `_xml_sanitize`/`quoteattr` for document text.
- Rich tables: `search_cmd` 568-592, `vsearch_cmd` 739-761, `query_cmd` 1050-1074; `_title_cell` (101-114) is the precedent for a fixed inline annotation.

**Error culture** (ClickException with remedy text): lines 665-666, 673-676, 710-711, 886-887, 942-945, 964-966, 986-991. Keep the constructor-only sqlite-vec guard separate from execution-stage errors (comment at 704-707).

**Migration notice rendering:** the CLI host consumes `IncrementalIndexer` events in `src/sif/cli/commands/index.py::_render_index_event` (lines 148-171):

```python
    def _on_event(event: str) -> None:
        code, _, payload = event.partition(" ")
        if code == "scan":
            progress.update(task, total=int(payload))
            console.print(f"  Found {payload} files")
        elif code == "unchanged":
            console.print(f"  [dim]Unchanged: {escape(payload)}[/dim]")
        elif code == "error":
            console.print(f"  [red]{escape(payload)}[/red]")
        progress.advance(task)
```

Add a `migrate` branch here (the event protocol is single-space `"code payload"`). Watch/MCP hosts inherit the event without Rich styling.

**Pre-search drift check** (`_pre_search_refresh`, lines 161-235) must remain untouched by migration triggering (D-09: only index-writing entry points migrate).

---

### `src/sif/mcp/protocol.py` (DTOs, transform)

**Analog:** itself.

**MCP result shape** (lines 201-210): `SearchResult` uses `doc_id: str` and free-form `metadata: dict[str, Any]`. New core fields can either become explicit fields or ride `metadata`; the existing `vectors_stale` precedent is "explicitly forwarded into metadata" (backend lines 190-199), so prefer metadata for `chunk_*` or add explicit fields plus a re-map line.

**Input models** (lines 240-291):

```python
class QueryInput(BaseModel):
    query: str
    collections: list[str] | None = None
    limit: int = Field(default=10, ge=1)
    min_score: float = Field(default=0.0, ge=0.0)
    rrf_k: int | None = Field(default=None, ge=1)
    bm25_weight: float | None = Field(default=None, gt=0.0)
    vector_weight: float | None = Field(default=None, gt=0.0)
```

Add `offset: int = Field(default=0, ge=0)` to `QueryInput`, `LexSearchInput` (265-270), `VecSearchInput` (279-284); add `per_chunk: bool = False` to `QueryInput` and `VecSearchInput`. `LexSearchInput`/`VecSearchInput` currently have bare `limit: int = 10`; mirror the validated form when adding offset.

---

### `src/sif/mcp/handlers.py` (controller/adapter, request-response)

**Analog:** itself.

**Hand-written schema must stay in sync with the model** (lines 53-69; the comment at 61-63 is explicit):

```python
    input_schema: ClassVar[dict[str, Any]] = {
        "type": "object",
        "properties": {
            "query": {"type": "string"},
            "collections": {"type": "array", "items": {"type": "string"}},
            "limit": {"type": "integer", "default": 10},
            "min_score": {"type": "number", "default": 0.0},
            "rrf_k": {"type": "integer"},
            "bm25_weight": {"type": "number"},
            "vector_weight": {"type": "number"},
        },
        "required": ["query"],
    }
```

Add `"offset": {"type": "integer", "minimum": 0, "default": 0}` and `"per_chunk": {"type": "boolean", "default": False}`.

**Pass-through** (`handle`, lines 71-102) explicitly forwards every model field to the backend; add `offset=`/`per_chunk=`. `create_default_tools` (215-222) remains unchanged — lex/vec registration stays Phase 22 scope (RESEARCH Open Q1).

---

### `src/sif/mcp/backend.py` (service boundary, request-response)

**Analog:** itself.

**Signature + options build** (lines 120-155): `# noqa: PLR0913` comment explains why per-request params mirror `QueryInput`; add `offset: int = 0, per_chunk: bool = False` and thread them into `SearchOptions`.

**Explicit re-map (the silent-drop boundary)** — lines 182-202:

```python
            mapped = [
                SearchResult(
                    doc_id=r.document_id,
                    path=r.path,
                    title=r.title,
                    content=r.content,
                    score=r.score,
                    highlights=r.highlights,
                    metadata={
                        "rank": r.rank,
                        "collection_name": r.collection_name,
                        "vectors_stale": r.vectors_stale,
                    },
                )
                for r in core_results
            ]
```

Every new public field must be added here or it is dropped (the comment at 190-194 says exactly this). Add `chunk_id`/`sequence`/`chunk_matches` to the metadata dict (or explicit model fields + copy).

**DB access pattern** (`_run_in_db`, lines 111-118): fresh `DatabaseConnection(...).transaction()` per request in a thread. For MCP-only schema init (RESEARCH Pitfall 13), run `Database(self.db_path).init_schema()` once in `__init__` (lines 87-109), copying the `watch_host.start_embedded_watch` precedent at `src/sif/mcp/watch_host.py:118-121`:

```python
    db = Database(db_path)
    try:
        db.init_schema()
        collections = CollectionRepository(db.connection).list_all()
    except Exception:
        db.close()
        raise
```

**Fail-soft carve-outs to preserve:** `_with_suggestions` (lines 53-71), the sqlite-vec BM25 fallback (lines 169-181; one-time warning), and `_truncate_content`.

---

### `docs/cli-reference.md` (generated, never hand-edit)

`scripts/generate_cli_ref.py::traverse_commands` (lines 90-108) recursively walks the Click tree and renders each option table, so `--offset`/`--per-chunk` appear automatically. Run `make docs-generate`; CI diff gate lives in `.github/workflows/docs.yml:40-42`. `tests/test_docs.py:423-433` asserts every Click command is documented, and `tests/test_ci_workflows.py:19` pins the generator-owned file set.

---

### Tests: new files (copy these patterns)

#### `tests/integration/test_search_correctness.py` (new)

**Analog 1 — real schema/vec0 fixture:** `tests/unit/search/test_hybrid.py::TestHybridSC1PipelineGolden._build_db` (lines 745-794):

```python
        conn = sqlite3.connect(":memory:")
        conn.row_factory = sqlite3.Row
        try:
            conn.enable_load_extension(True)
            sqlite_vec.load(conn)
            conn.enable_load_extension(False)
        except Exception:
            conn.close()
            pytest.skip("sqlite-vec not available")

        SchemaManager(conn, embedding_dim=2).create_all()
        ...
        searcher = VectorSearcher(conn, embedding_dim=2)
        searcher.add_embeddings_batch([...])
        return conn
```

**Analog 2 — deterministic corpus/embedder:** `tests/support/bench.py::ConceptEmbedder` (lines 40-95) and `build_bench_db` (98-167), which inserts documents/chunks/embeddings through the real triggers with fixed ids.

**Analog 3 — real tmp DB + CLI:** `tests/integration/test_incremental_equivalence.py` (helpers 35-120): hermetic `Settings(embedding_dim=8, ...)`, `_seed_collection`, `CliRunner`, fresh-connection assertions. Use this shape for the chunky-doc regression (one doc with >= 5 chunks requested with `--limit 10` yields 10 distinct docs), page continuity (`offset=l, limit=n` equals `[l:l+n]` of `limit=l+n, offset=0` — RESEARCH Pitfall 11), and an attach-spy that counts exactly one attach per exit path.

#### `tests/unit/database/test_schema_title_fts.py` (new)

**Analog:** `tests/unit/database/test_schema.py`.
- `_load_vec` + `vec_db` fixture (lines 14-35).
- `TestSchemaRealSQLiteCoverage.test_misconfigured_fts_tables_are_rebuilt_and_seeded` (lines 317-357): build legacy DDL manually, call the private migration entry, assert MATCH counts.
- `TestFtsUpdateTrigger` (lines 517-627): real updates/deletes through triggers, `PRAGMA integrity_check == "ok"` at line 601.
- `TestVocabShadowTable` (lines 438-514) and `tests/unit/search/test_suggest.py::_fixture_db` (lines 26-75) for the populated-DB vocab-survival assertion (`documents_fts_v` still yields stems, `sif suggest` still works).
- Pattern: hand-build the legacy single-column `documents_fts` + old triggers, insert documents/titles, run `SchemaManager.create_all()`, then assert title-only MATCH (0 before, >=1 after), old title terms gone after a title-only UPDATE, NULL title insert/delete, idempotent second run.

#### `tests/unit/cli/test_search_pagination.py` (new)

**Analog:** `tests/unit/cli/test_search.py`.
- Imports/header (lines 1-37), `_query_settings_mock` (39-55).
- Mock pattern: `_make_result(**overrides)` (1542+), patched `sif.cli.commands.search.Database/CollectionRepository/BM25Searcher`, `runner.invoke(..., obj={"index_path": MagicMock(exists=lambda: True)})` (1609-1625).
- Shape assertions: CSV header at 1713-1714; JSON `json.loads(result.output)[0]` at 1628-1642; global-rank assertions by reading `rank` from JSON.

#### `tests/unit/indexing/test_watcher.py` new cases

**Analog (same file):** `TestEmbedDepth` (lines 1433-1510). Reuse `_seed_collection` (line 56), `_delenv_settings_vars`, `_open_indexer`, `_run_burst` via `watcher._settled_callback(coll)([FileModifiedEvent(...)])` + `watcher._drain_once()` (1441-1449), and fresh-connection counts (1451-1456). New test: metadata-only edit at embed depth -> chunk count and vector row count unchanged; body edit -> purged and re-embedded.

#### Fixtures

Add `.yaml`/`.yml` files whose first line is `---` in all three verified forms (closing delimiter, two blocks, no closing delimiter), a YAML-date frontmatter file, and a chunky Markdown document (>= 5 chunks). Pattern: `tests/unit/indexing/test_parser_checksum.py` (tmp_path + `write_text`, lines 23-42) and `tests/unit/indexing/test_parser.py::TestDocumentParsers` (parametrized `create_parser` expectations, lines 140-157).

---

### Tests: modified files (analog = themselves)

| File | Pattern to preserve | What changes |
|------|--------------------|--------------|
| `tests/unit/indexing/test_parser_checksum.py` | `parsed.checksum == hashlib.sha256(parsed.content.encode()).hexdigest()` contract and `frontmatter-only edit keeps checksum` (lines 23-42) | Contract becomes body + canonical(frontmatter): a metadata-only edit now CHANGES the checksum; body edit still changes it. Rewrite docstrings with the D-08 rationale. |
| `tests/unit/indexing/test_parser.py` | `create_parser` parametrization (lines 140-157) and per-parser title fixtures (77-127) | Add `.yaml/.yml` whole-file fixtures and `.py`/`.txt` dispatch assertions; keep `create_parser(tmp_path / "archive.pdf") is None`. |
| `tests/unit/indexing/test_incremental.py` | Helpers `_seed_collection`, `_open_indexer`, `_doc_row`, `_chunk_contents`, `_embedding_count` (lines 34-125); real tmp DB | Add fast-path cases (metadata-only edit keeps chunks/embeddings, updates title/metadata/checksum/mtime), migration marker cases (mismatch -> one forced pass -> marker written only on success), and the create-path checksum fix. Existing `IncrementalResult(...)` equality assertions stay valid because new fields are `compare=False`. |
| `tests/unit/search/test_vector.py` | `TestVectorFilteredRecall._build_db` (lines 277-322): in-memory vec0, `pytest.skip` when unavailable | Add dedup tests: duplicate chunks collapse to one row with `chunk_matches`, best distance wins, escalation returns `limit` distinct docs, `--per-chunk` shape, offset slice + global ranks. No attach assertions remain. |
| `tests/unit/search/test_hybrid.py` | `TestHybridSC1PipelineGolden` (660-815): full-dict `SNAPSHOT` comparison | The default dedup contract changes: regenerate the snapshot from post-change code, document the change in the class docstring (byte-identical-defaults culture is preserved from the new baseline). Add per-chunk key tests and one-attach spy. |
| `tests/unit/search/test_rrf.py` | `TestRRFSC1Golden` (470-560) and formula tests (885-1040) | Add `key` parameter tests (document vs chunk keying) and metadata-merge tests (chunk fields adopted, `chunk_matches=max`). RRF score assertions must not change. |
| `tests/unit/search/test_bm25.py` | `test_search_with_pagination` (156), `min_score` behavior (101), real FTS query tests (27-60) | Update expected SQL/params: weighted `bm25(documents_fts, ?, ?)`, threshold before LIMIT/OFFSET, rank = offset + position. Use a real multi-document corpus for threshold direction (Pitfall 4). |
| `tests/unit/search/test_staleness.py` | `TestSearcherDelegation` (class at line 262) records `_attach_contexts` calls per searcher | Rewrite to the new single-owner contract: searchers no longer attach; each CLI/MCP entry path attaches exactly once. Keep the derived-signal/display-gate tests unchanged. |
| `tests/unit/search/test_context_attach.py` | Real-DB attach tests + delegation mocks (140-178) | Same rewrite: assert one attach at pipeline exit (and one per direct CLI/MCP path), no clobbering, normalize_path parity preserved. |
| `tests/fixtures/bench/heldout_defaults.json` + `tests/unit/search/test_bench_snapshot.py` | Snapshot loaded at 46-58 and recomputed through `build_bench_db` (80-89) | Dedup + title column move held-out metrics; update the JSON with the before/after rationale. Comments in the test explain why the lock lives in the same file. |
| `tests/unit/cli/test_search.py` | CSV header pins (1713-1714, 2477-2484), JSON dict assertions (1628-1642), mock scaffolding (1609-1625) | Add `--offset`/`--per-chunk` invocations; update CSV header if new columns ship; assert global ranks across pages and chunk fields in JSON. |
| `tests/unit/mcp/test_backend.py` | `backend` fixture (25-31), `TestQueryToolHandlerWeightPassThrough` (475-520), `TestQueryInputWeightValidation` (444-467) | Add offset validation, offset/per_chunk forwarding, new chunk fields in the re-map, and schema-sync assertions. `test_hybrid_search_mocks` (71-95) shows the explicit-field check pattern. |
| `tests/unit/database/test_schema.py` | Index-set assertion (255-268), `drop_all` coverage (388-436), vocab tests (438-514) | Add `idx_documents_mtime` to the expected index set and `index_meta` to reset isolation; assert fresh DBs get the two-column `documents_fts`. |
| `tests/integration/test_incremental_equivalence.py` | Golden add/mutate/delete/idempotent cycles (172-260) via real CLI + fresh-connection snapshots | Checksum-precondition fixtures change under the new convention; keep the same-state equivalence assertions and add a frontmatter-only edit cycle. |

## Shared Patterns

### SQL parameter binding
**Source:** `src/sif/search/bm25.py:62-112`, `src/sif/search/vector.py:65-78`
**Apply to:** all new SQL (weighted `bm25`, threshold, offset, title-FTS queries)
- Every value is bound (`?`), including the KNN `k` and `LIMIT/OFFSET`; FTS table names are literals and collection filters are generated placeholders (never user text). The security table in RESEARCH §Security V5 requires this for `bm25()` weights, `offset`, and `limit`.

### Collection-filter placeholder builder
**Source:** `src/sif/search/bm25.py:65-68`, `src/sif/search/vector.py:66-68`
**Apply to:** the weighted-BM25 SQL and the KNN chunk-join SQL
```python
            placeholders = ", ".join(["?"] * len(options.collection_ids))
            collection_filter = f"AND d.collection_id IN ({placeholders})"
```
The exclude-all sentinel (`collection_ids is not None and not collection_ids -> []`) must stay in both searchers (bm25 55-56, vector 48-49).

### Error handling
**Source:** `src/sif/cli/commands/search.py:665-676, 710-711, 886-887, 942-945, 986-991`; `src/sif/mcp/backend.py:169-181`; `src/sif/indexing/incremental.py:286-298`
**Apply to:** CLI flags/offset validation (ClickException with remedy), MCP boundary (one-time BM25-only degradation), indexing (per-file `error` event + counted failure, never a silent skip).

### Validation
**Source:** `src/sif/mcp/protocol.py:245-252` (`Field(ge=...)`); `src/sif/cli/commands/search.py:786-816` (`click.IntRange`/`click.FloatRange`)
**Apply to:** CLI `--offset` (`IntRange(min=0)`), MCP `offset` (`Field(default=0, ge=0)`), `per_chunk` (bool). Past-the-end offset returns an empty page, never an error.

### Progress/notice event protocol
**Source:** `src/sif/indexing/incremental.py:94-101, 269-273`; `src/sif/cli/commands/index.py:148-171`
**Apply to:** the migration notice (`"migrate <n>"`) across CLI/watch/MCP hosts. Core emits presentation-free `"code payload"` strings; only CLI renders Rich.

### Output-channel discipline
**Source:** `src/sif/cli/commands/search.py:33-36, 238-251`
**Apply to:** migration notices and any new warnings: stderr only (`console_err`), `-q` suppresses, stdout stays pipeable for `--json`/`--csv`.

### Deterministic test discipline
**Source:** `tests/support/bench.py:40-167`; `tests/unit/search/test_hybrid.py:745-794`; `tests/unit/indexing/test_incremental.py:34-125`
**Apply to:** every new test — `tmp_path` or in-memory DBs, real `SchemaManager`, `ConceptEmbedder` for embeddings, `pytest.skip("sqlite-vec not available")`, assertions through fresh connections, no wall-clock races.

### Generator-owned docs
**Source:** `.github/workflows/docs.yml:40-42`; `scripts/generate_cli_ref.py:90-108`
**Apply to:** all new CLI flags — run `make docs-generate`; never edit `docs/cli-reference.md` by hand.

## No Analog Found

| File / element | Role | Data Flow | Reason | Fallback |
|----------------|------|-----------|--------|----------|
| Title-FTS multi-column `('rebuild')` sequence | schema migration | DDL | No existing migration adds an FTS column; closest analog (`_fts_is_misconfigured` + drop/recreate) cannot detect column lists | Use RESEARCH Pattern 5 verified sequence verbatim (drop vocab -> drop FTS -> create 2-col -> rebuild -> recreate vocab -> recreate triggers) |
| Per-collection `index_meta` convention marker | persisted state | KV | No version/convention marker exists anywhere today | Use RESEARCH Pattern 4d + `LLMCacheRepository` get/set shape |
| `RRFFusion` grouping key | fusion utility | transform | Fusion is hard-coded document-keyed | Use RESEARCH Pattern 2 "Per-chunk fusion key" (optional callable, default document id) and preserve the math |
| `--per-chunk` interaction with limit/offset | CLI/MCP surface | request-response | No per-chunk output mode exists | Decision is Claude's Discretion (CONTEXT): page size counts chunk rows; document in plan + tests |

## Metadata

**Analog search scope:** `src/sif/{core,database,indexing,search,cli,mcp}/`, `tests/{unit,integration,support,fixtures}/`, `scripts/`, `.github/workflows/`
**Files scanned:** 40+ (17 source files read in full or targeted at cited ranges; 20+ test files surveyed; 3 scripts/workflows)
**Verification:** every analog path above passed `git ls-files -- <path>` at HEAD `fb7f65b`; no gitignored capability mirrors referenced.
**Pattern extraction date:** 2026-11-15
