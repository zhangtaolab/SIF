---
phase: 261105-wwz-vec0-metadata-src-sif-search-vector-py-8
plan: 01
subsystem: search
tags: [sqlite-vec, vec0, performance, audit, search]

requires:
  - phase: 261105-wbj-embed-o-n-bug-src-sif-search-vector-py-2
    provides: embed-path O(N^2) fix (get_all_embedded_chunk_ids batch prefetch) that motivated this search-path audit
provides:
  - Evidence-backed disposition that the search path has NO unindexed vec0 metadata-filter scan (EQP + flat-timing + call-frequency, reproducible)
  - Durable in-code audit note at the _search_with_vec query site naming quick task 261105-wwz
affects: []  # no behavioral change; future re-audits of vec0 metadata filtering

actuals:
  tokens: 225
  tasks: 2
  commits: 1
plan_head_before: f24616ad16b241b521c063e257dd01cbfc192461
plan_head_after: 751a0c3

tech-stack:
  added: []
  patterns:
    - "Audit-note-at-query-site pattern: an in-code comment naming the quick-task id closes a suspicion class so future audits find the disposition instead of re-investigating"

key-files:
  created: []
  modified:
    - src/sif/search/vector.py

key-decisions:
  - "Branch A taken: fresh EQP at HEAD shows the single vec0 SCAN outermost (or second under a one-iteration collections loop in the 1-id shape) with PK joins and an empty vec0 constraint map; timing flat 0.245-0.270 ms across filter sizes — no trigger condition for the CROSS JOIN branch"
  - "1-id IN (?) shape nests the vec0 SCAN under an outer collections loop, but that loop is bounded by the placeholder count (exactly one iteration per vector.py:66), which the plan defines as NOT a Branch-B trigger"

requirements-completed: [QUICK-AUDIT-VEC0-SEARCH-SCAN]

duration: 10min
completed: 2026-11-05
status: complete
---

# Quick Task 261105-wwz: Vec0 Metadata Audit (Search Path) Summary

**Search path clean: the only vec0 access is the KNN MATCH with no metadata WHERE — JOINs resolve as PK lookups, timing is flat across filter shapes, and VectorSearcher.search runs once per query; comment-only audit note added, zero behavioral change**

## Disposition

**Branch A — no change needed.** The suspicion that search/hybrid queries hit the same O(N) unindexed-metadata scan as the 261105-wbj embed integrity check is **refuted by measurement** on all three evidence classes:

1. **Plan shape** — `SCAN de VIRTUAL TABLE INDEX 0:3{___}___` appears once, outermost (2-id/3-id/no-filter shapes); the `{___}___` constraint map shows only MATCH/k pushed into the virtual table, never `document_id`/`chunk_id`/`embedding_id`. The JOINs resolve as PK lookups per KNN-emitted row.
2. **Cost** — best-of-3 KNN timing is flat (0.245-0.270 ms) across no-filter / 1-id / 2-id / 3-id shapes: no KNN re-execution multiplier for any placeholder count the code can generate.
3. **Frequency** — `VectorSearcher.search` runs once per user query (bounded only by the query-expansion variant count on the default route), never inside a per-result or per-document loop.

The one real O(N) cost — vec0 v0.1.9's brute-force distance pass over all stored vectors — is inherent to `embedding MATCH` in this version (no ANN index), identical under any semantics-preserving SQL reshaping, and a per-query constant, not a per-call multiplier. Removing it would require an ANN index type (out of scope).

## Branch Taken and Why

**Branch A (comment-only).** Branch B required the fresh EQP to either (a) nest the vec0 SCAN under an outer loop NOT bounded by the placeholder count, or (b) map a `document_id`/`chunk_id`/`embedding_id` constraint into the vec0 virtual-table index. Neither occurred: the vec0 SCAN is outermost in the no-filter/2-id/3-id shapes, and in the 1-id shape the outer collections loop iterates exactly once (one placeholder per collection id, `vector.py:66`) — bounded by the placeholder count, explicitly not a trigger. Timing corroborates (the 1-id shape is the *fastest* at 0.245 ms). The CROSS JOIN pinning and its regression test were therefore NOT applied.

## EXPLAIN QUERY PLAN (verbatim)

Environment: sqlite 3.51.0, sqlite-vec 0.1.9, macOS (Darwin 25.6.0). Rows print outermost-first on this build. Query is the exact `_search_with_vec` SQL (vector.py:79-91) with `fetch_k = 50` (`max(limit*4, 50)`, default limit 10). Synthetic bench: in-memory, FLOAT[8], 2,000 documents / 6,000 embedding rows across 3 collections.

### Synthetic in-memory (timing vehicle)

No filter:

```
8|0|49|SCAN de VIRTUAL TABLE INDEX 0:3{___}___
14|0|46|SEARCH d USING INDEX sqlite_autoindex_documents_1 (id=?)
20|0|47|SEARCH c USING INDEX sqlite_autoindex_collections_1 (id=?)
34|0|0|USE TEMP B-TREE FOR ORDER BY
```

`AND d.collection_id IN (?)` — one bound id:

```
8|0|47|SEARCH c USING INDEX sqlite_autoindex_collections_1 (id=?)
15|0|49|SCAN de VIRTUAL TABLE INDEX 0:3{___}___
21|0|46|SEARCH d USING INDEX sqlite_autoindex_documents_1 (id=?)
37|0|0|USE TEMP B-TREE FOR ORDER BY
```

(collections drives outermost with exactly ONE iteration — one placeholder — so the KNN still executes once)

`AND d.collection_id IN (?,?)` — two bound ids:

```
8|0|49|SCAN de VIRTUAL TABLE INDEX 0:3{___}___
14|0|46|SEARCH d USING INDEX sqlite_autoindex_documents_1 (id=?)
23|0|47|SEARCH c USING INDEX sqlite_autoindex_collections_1 (id=?)
37|0|0|USE TEMP B-TREE FOR ORDER BY
```

`AND d.collection_id IN (?,?,?)` — three bound ids:

```
8|0|49|SCAN de VIRTUAL TABLE INDEX 0:3{___}___
14|0|46|SEARCH d USING INDEX sqlite_autoindex_documents_1 (id=?)
38|0|47|SEARCH c USING INDEX sqlite_autoindex_collections_1 (id=?)
52|0|0|USE TEMP B-TREE FOR ORDER BY
```

### Real DBs (read-only, `file:...?mode=ro` URIs)

Both default DBs exist and carry the production FLOAT[1024] schema; both hold **0 embedding rows** (`~/.local/share/sif/sif.db`: 0 embeddings / 0 documents; `~/Library/Application Support/sif/sif.db`: 0 embeddings / 2 documents) — confirming the synthetic bench as the timing vehicle. EQP shape is data-independent and identical on both:

`/Users/forrest/.local/share/sif/sif.db` — no filter / 1-id / 3-id:

```
--- no filter ---
8|0|49|SCAN de VIRTUAL TABLE INDEX 0:3{___}___
14|0|46|SEARCH d USING INDEX sqlite_autoindex_documents_1 (id=?)
20|0|46|SEARCH c USING INDEX sqlite_autoindex_collections_1 (id=?)
33|0|0|USE TEMP B-TREE FOR ORDER BY
--- IN (?) one id ---
8|0|46|SEARCH c USING INDEX sqlite_autoindex_collections_1 (id=?)
14|0|49|SCAN de VIRTUAL TABLE INDEX 0:3{___}___
20|0|46|SEARCH d USING INDEX sqlite_autoindex_documents_1 (id=?)
36|0|0|USE TEMP B-TREE FOR ORDER BY
--- IN (?,?,?) three ids ---
8|0|49|SCAN de VIRTUAL TABLE INDEX 0:3{___}___
14|0|46|SEARCH d USING INDEX sqlite_autoindex_documents_1 (id=?)
37|0|46|SEARCH c USING INDEX sqlite_autoindex_collections_1 (id=?)
50|0|0|USE TEMP B-TREE FOR ORDER BY
```

`/Users/forrest/Library/Application Support/sif/sif.db` — byte-identical plans for all three shapes (verified; output matches the block above).

## Timing (synthetic in-memory, best of 3)

| Shape | KNN wall time |
|---|---|
| no filter | 0.267 ms |
| IN (?) — 1 id | 0.245 ms |
| IN (?,?) — 2 ids | 0.258 ms |
| IN (?,?,?) — 3 ids | 0.270 ms |

Flat within noise across every placeholder count the code can generate (one per selected collection id). Compare the 261105-wbj pattern: a metadata-filtered scan multiplied by ~40k loop iterations — nothing analogous exists here.

## Call-Frequency Inventory

`VectorSearcher.search` runs exactly once per user query at every call site; it is never invoked per-result or per-document:

| Call site | Route | Frequency |
|---|---|---|
| src/sif/search/hybrid.py:64 | `HybridSearcher.search` | once per call |
| src/sif/search/hybrid.py:184 | `SearchPipeline` `vec:` route | once per query |
| src/sif/search/hybrid.py:191 | `SearchPipeline` `hyde:` route | once per query |
| src/sif/cli/commands/search.py:374 | CLI direct vector search | once per CLI invocation |
| src/sif/search/hybrid.py:217-218 | default hybrid route | `HybridSearcher.search` (→ vector.search) once per expanded query variant — original plus deduplicated expander variants, a small bounded constant; never per-result |

## Statement Classification (every `document_embeddings` reference in src/)

| Site | Statement | Path | Disposition |
|---|---|---|---|
| src/sif/search/vector.py:86 | KNN SELECT (`embedding MATCH ? AND k = ?`, JOIN documents/collections, optional `d.collection_id IN`) | **search** | Audit subject — the ONLY search-path vec0 access; no vec0 metadata WHERE; clean per EQP/timing/frequency above |
| src/sif/search/vector.py:161 | `INSERT OR REPLACE` (single) | embed write | maintenance |
| src/sif/search/vector.py:181 | `INSERT OR REPLACE` (executemany batch) | embed write | maintenance |
| src/sif/search/vector.py:195 | `DELETE ... WHERE document_id = ?` | embed delete-before-insert | maintenance — once per re-embedded document, inside the per-collection transaction; not the search path |
| src/sif/search/vector.py:207 | `SELECT chunk_id ... WHERE document_id = ?` | embed single-doc lookup | maintenance — zero production callers since 261105-wbj (tests only) |
| src/sif/search/vector.py:225 | `SELECT document_id, chunk_id` (unfiltered) | embed batch prefetch | maintenance — the 261105-wbj fix; one scan per collection |
| src/sif/database/schema.py:292 | `sqlite_master` schema read (existing-dim check) | schema creation | maintenance (completeness: groups with the :307 DDL site in the plan's eight-site inventory) |
| src/sif/database/schema.py:307 | `CREATE VIRTUAL TABLE ... vec0` DDL | schema creation | maintenance |
| src/sif/cli/commands/index.py:295 | `sqlite_master` schema read (WR-02 dim check) | embed startup | maintenance |
| src/sif/cli/main.py:173 | `DELETE ... WHERE document_id NOT IN (...)` | explicit `cleanup` command | maintenance — once per explicit cleanup run |

All non-search statements are maintenance-path and already dispositioned (261105-wbj for the embed loop; cleanup is an explicit user command).

## Audit Note Applied (the only source-tree edit)

7 comment-only lines inserted above the `sql` assignment in `_search_with_vec` (src/sif/search/vector.py:79-86 after the edit), naming quick task 261105-wwz, covering: KNN MATCH is the only vec0 access in the search path with no metadata WHERE; JOINs resolve as PK lookups per KNN-emitted row; EQP shows the single vec0 SCAN outermost with flat timing across filter sizes; vec0 v0.1.9 KNN is an inherent once-per-query brute-force pass. Grep gate: `[ "$(grep -c '261105-wwz' src/sif/search/vector.py)" = "1" ]` (baseline 0). No executable statement changed; the diff is +7 comment lines.

## Probe Safety

Every real-DB probe opened the file via a `file:<path>?mode=ro` URI (SQLite read-only mode) — no probe statement can mutate user data. The timing bench lived entirely in `:memory:`. The reporter's ~495,802-row index was never opened for write. Probe script kept as scratch at `.planning/tmp/261105-wwz-probe.py` (untracked, not committed).

## Deviations from Plan

None — plan executed exactly as written. Planning-time vs execution-time observations matched on every point: identical EQP shapes (including the 1-id collections-outermost form), timing in the same 0.24-0.27 ms band, same eight-site inventory (the classification table above additionally breaks out schema.py:292, which groups under the plan's schema-DDL site), zero production callers for vector.py:207, and both real DBs at 0 embedding rows. Branch A taken as expected.

## Performance

- **Duration:** ~10 min (started 2026-11-05T15:54:04Z)
- **Tasks:** 2 (both completed)
- **Files modified:** 1 (src/sif/search/vector.py, comment-only)

## Task Commits

1. **Task 1: audit note at the KNN query site** — `751a0c3` (docs, comment-only, +7 lines)
2. **Task 2: SUMMARY (this file)** — docs artifact, not committed by the executor (orchestrator handles the docs commit)

## Quality Gates

- `ruff check src tests` — clean ("All checks passed!")
- `ruff format --check src tests` — clean (133 files already formatted)
- `env -u FORCE_COLOR NO_COLOR=1 python -m pytest -q` — **690 passed, 0 failed** in 13.74s (matches the 690-passed baseline at 16b7b25 post-261105-wbj; coverage 78%, unchanged)
- `grep -q 'EXPLAIN QUERY PLAN'` on this SUMMARY — pass

## User Setup Required

None. On branch A nothing about runtime behavior changes. Optional user-run confirmation on the real ~495k-row index: time a `sif search` before and after pulling this change — wall times must be indistinguishable.

## Self-Check: PASSED

- `src/sif/search/vector.py` present and carrying the audit note (grep gate 1).
- Commit `751a0c3` is an ancestor of HEAD.
- Measured `git rev-list --count f24616a..HEAD` = 1, matching `commits: 1` in frontmatter.
- Realized diff over src/: 899 chars -> ~225 tokens (chars/4), recorded as `actuals.tokens`.

---
*Quick task: 261105-wwz*
*Completed: 2026-11-05*
