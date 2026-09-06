---
phase: 05-agent-context-experience
reviewed: 2026-09-06T00:00:00Z
depth: standard
files_reviewed: 18
files_reviewed_list:
  - .gitignore
  - src/sif/cli/commands/context.py
  - src/sif/cli/main.py
  - src/sif/core/models.py
  - src/sif/database/repositories.py
  - src/sif/database/schema.py
  - src/sif/models/search.py
  - src/sif/search/bm25.py
  - src/sif/search/hybrid.py
  - src/sif/search/rerank.py
  - src/sif/search/rrf.py
  - src/sif/search/vector.py
  - tests/unit/cli/test_context.py
  - tests/unit/cli/test_status.py
  - tests/unit/database/test_schema.py
  - tests/unit/search/test_bm25.py
  - tests/unit/search/test_hybrid.py
  - tests/unit/search/test_vector.py
findings:
  critical: 2
  warning: 10
  info: 14
  total: 26
status: issues_found
---

# Phase 05: Code Review Report

**Reviewed:** 2026-09-06
**Depth:** standard
**Files Reviewed:** 18
**Status:** issues_found

## Summary

Phase 05's deliverables (unified `contexts` table, context CLI, context-description attachment in BM25/vector/hybrid searchers, path normalization via `os.path.realpath`) are largely implemented as described, and the migration, FTS-update-trigger fix, and KNN over-fetch work are backed by genuine integration tests. However, the adversarial pass surfaced two Critical defects:

1. The FTS5 **delete** triggers use the plain `DELETE FROM <fts> WHERE rowid = ...` form, which is invalid inside an AFTER DELETE trigger on an external-content FTS5 table (the content row is already gone, so FTS5 cannot fetch the old values to remove from the inverted index). I reproduced this live against SQLite using the exact trigger SQL from `schema.py`: deleted documents' terms remain in the index, and once a new document reuses the freed rowid, searching for a term unique to the *deleted* document returns the *new* document. This is the same defect class as the phase's own FND-06/CR-01 fix, missed for DELETEs.
2. `sif context prune` compares raw path strings against `documents.path`, while the searchers match contexts via `os.path.realpath` on both sides — the phase's own tests bless storing a user-typed `/tmp/...` path while documents store `/private/tmp/...`. Prune therefore **deletes contexts that search actively matches** (silent loss of user-authored descriptions). The root cause is that `context add` stores the target verbatim with no `expanduser`/`realpath` normalization.

Further warnings cover an undefined `sqlite3` name in `main.py`'s error handler (codified by a `noqa: F821`), pagination inconsistencies between BM25 and vector search, a vector-score formula built on a mislabeled distance metric (empirically verified as L2, not cosine — invalid for non-normalized gguf embeddings), an unused `embedding_dim` parameter that defeats fail-fast dimension validation, a timezone-dependent LLM-cache TTL comparison, RRF score mislabeling in multi-query fusion, and two tests that do not test what their names claim.

No SQL injection, command injection, secret handling, or path-traversal issues were found; all SQL is parameterized and interpolated values are internal constants.

## Critical Issues

### CR-01: FTS5 delete triggers leave stale index entries; rowid reuse returns wrong search results

**File:** `src/sif/database/schema.py:236-241` (`documents_fts_delete`), `src/sif/database/schema.py:260-266` (`chunks_fts_delete`)
**Issue:** The delete triggers issue `DELETE FROM documents_fts WHERE rowid = old.rowid;`. For an external-content FTS5 table, the ordinary DELETE form requires the content row to still be present so FTS5 can fetch the old column values to remove from the inverted index. Inside an `AFTER DELETE` trigger the row has already been removed from `documents`, so the terms are never purged. The **update** triggers in the same file (lines 226-234, 251-259) correctly use the documented `'delete'`-command INSERT form — the delete triggers are inconsistent with them.

Reproduced live with the exact trigger SQL from this file: after `DELETE FROM documents WHERE id='d2'`, `MATCH 'zebra'` still returned the deleted row's rowid; after inserting a new document that SQLite assigned the freed rowid (the normal case when the deleted row held the max rowid — i.e., the most recently added file), `MATCH 'zebra'` returned the **new, unrelated document**. Consequences: (a) searches for terms unique to deleted files return wrong documents after rowid reuse, and (b) deleted content accumulates in the FTS index permanently. Document deletion happens on every `sif index update` that removes a synced file, so this is an ordinary-event path, not an edge case. The searchers' JOIN to `documents` masks the ghost rows only until the rowid is reused.

**Fix:**
```sql
CREATE TRIGGER IF NOT EXISTS documents_fts_delete
AFTER DELETE ON documents
BEGIN
    INSERT INTO documents_fts(documents_fts, rowid, content)
    VALUES('delete', old.rowid, old.content);
END
```
Same form for `chunks_fts_delete`. Two migration requirements: (1) `CREATE TRIGGER IF NOT EXISTS` will not replace the already-deployed plain-DELETE trigger, so the existing trigger must be dropped explicitly — mirror the `_fts_update_trigger_is_legacy` detection pattern already present at `schema.py:148-191`; (2) existing databases already carry stale entries, so the fix must also trigger an FTS rebuild (the `needs_rebuild_docs` / re-seed machinery at `schema.py:180-196, 268-278` can be reused). Add a regression test deleting a max-rowid document, inserting a replacement, and asserting the deleted term no longer matches.

### CR-02: `context prune` deletes contexts that search actively matches (data loss)

**File:** `src/sif/database/repositories.py:437-444` (`ContextRepository.delete_orphaned_paths`)
**Issue:** Prune's orphan test is a raw string comparison: `target_id NOT IN (SELECT path FROM documents)`. The searchers, by contrast, match contexts by normalizing **both** sides with `os.path.realpath` (`src/sif/search/bm25.py:121-125`, `src/sif/search/vector.py:128-132`, `src/sif/search/hybrid.py:142-145`), and the phase's own tests enshrine the mismatch case as valid: a context stored with the user-typed `/tmp/doc.md` while `documents.path` holds the resolved `/private/tmp/doc.md` (`tests/unit/search/test_bm25.py:414-440`, `tests/unit/search/test_vector.py:485-514`). That document is indexed via `Path(file_path).resolve()` (`src/sif/indexing/parser.py:70,105,172`), which resolves symlinks — so the two representations coexist by design, search attaches the description, and then `sif context prune` classifies the same context as orphaned and silently deletes it. Any divergence that `realpath` collapses (`/tmp` vs `/private/tmp`, other symlinked vault roots) is destroyed by prune. This is silent loss of user-authored content.

**Fix:** Make prune use the same matching definition as search. Since SQL cannot call `realpath`, do the comparison in Python:
```python
def delete_orphaned_paths(self) -> int:
    doc_paths = {os.path.realpath(r[0]) for r in self.db.execute("SELECT path FROM documents")}
    contexts = self.list_by_type("path")
    orphans = [c for c in contexts if os.path.realpath(c.path) not in doc_paths]
    for c in orphans:
        self.delete(c.id)
    return len(orphans)
```
Pair this with WR-02 (normalize at write time) so new contexts are stored already-resolved and the two definitions converge.

## Warnings

### WR-01: Undefined `sqlite3` in cleanup error handler; `noqa: F821` codifies the bug

**File:** `src/sif/cli/main.py:166`
**Issue:** `cleanup_cmd` catches `sqlite3.OperationalError` but `sqlite3` is never imported in `main.py` (imports end at `sif.utils.logging`). The `# noqa: F821` suppression acknowledges the undefined name rather than fixing it. If `document_embeddings` is missing (e.g., sqlite-vec failed to load, legacy DB), the embeddings DELETE raises `OperationalError`, the handler immediately raises `NameError: name 'sqlite3' is not defined`, and the outer `except Exception` reports the misleading NameError to the user — aborting cleanup before the LLM-cache step runs.
**Fix:** Add `import sqlite3` at module top and remove the `noqa: F821`. Consider also whether aborting the whole cleanup on a missing embeddings table is intended, versus logging and continuing.

### WR-02: `context add` stores path targets verbatim — no expanduser/realpath

**File:** `src/sif/cli/commands/context.py:45-58`
**Issue:** For `type == "path"` the target is stored exactly as typed. `sif context add path ~/notes/a.md "desc"` stores the literal `~/notes/a.md` (Click does not expanduser arguments), and relative paths are stored relative. Both never match search results (whose paths are resolved absolutes) and become dead data until prune removes them — and the symlink-alias cases are precisely the ones CR-02 shows prune mishandles. The searchers normalize; the write path does not.
**Fix:** Normalize before storing:
```python
elif type == "path":
    actual_target = os.path.realpath(os.path.expanduser(target))
```
(keeping collection/global handling unchanged). Optionally offer a one-time re-normalization of existing rows alongside the CR-02 fix.

### WR-03: BM25 applies LIMIT/OFFSET before the `min_score` filter; limit clamping inconsistent

**File:** `src/sif/search/bm25.py:60-84`
**Issue:** `LIMIT ? OFFSET ?` is applied in SQL, then rows are filtered by `min_score` in Python (line 83-84). With `min_score > 0` a requested page of 10 can return fewer than 10 rows even when more qualifying rows exist — the SQL page consumed the budget on filtered rows. Ranks are also assigned per returned page, so `offset` pagination restarts ranks at 1. Additionally, a non-positive `limit` reaches SQLite as `LIMIT -1` (unlimited), while `VectorSearcher` clamps to 1 — the two searchers disagree on the same `SearchOptions` input.
**Fix:** Filter by `rank` in SQL (FTS5 `rank <= :max_rank` derived from `min_score`: `rank <= 1/min_score - 1` for `min_score > 0`), or over-fetch and trim after the Python filter. Clamp `limit` in one shared place.

### WR-04: Vector search ignores `options.offset`

**File:** `src/sif/search/vector.py:70-110`
**Issue:** The BM25 SQL honors `OFFSET`; the vector KNN query has no offset and the Python slice (`results[: max(1, options.limit)]`) never applies one. `SearchOptions.offset` is part of the shared options contract, so vector and hybrid search return the same first page for any offset — pagination silently broken for those search types.
**Fix:** Either slice `results[offset : offset + limit]` after fetching `fetch_k = max((offset + limit) * 4, 50)` rows, or raise/document that offset is unsupported for vector search instead of silently ignoring it.

### WR-05: Vector score assumes cosine distance; sqlite-vec returns L2 — invalid for non-normalized embeddings

**File:** `src/sif/search/vector.py:87-93`
**Issue:** `score = 1.0 - (row["score"] / 2.0)` with the comment "Cosine distance is 0-2". Empirically verified: with the schema's vec0 declaration (no `distance_metric`), sqlite-vec returns **L2** distance (orthogonal unit vectors -> 1.4142, same-direction magnitude-3 vector -> 2.0). L2 is unbounded, so for embeddings not unit-normalized, `score` goes negative and the default `min_score=0.0` silently filters **all** results — vector search returns nothing. This is reachable through the supported `model_type: "gguf"` path (llama.cpp embeddings are not normalized by default); it only works today because the default sentence-transformers path normalizes.
**Fix:** Declare `distance_metric=cosine` on the vec0 column (requires table migration/rebuild), or normalize the query embedding (and enforce stored-vector norms) before MATCH. At minimum, correct the comment and fail fast (per project convention) when the query embedding's norm deviates from 1.0, instead of silently returning an empty result set.

### WR-06: `VectorSearcher.embedding_dim` accepted, stored, never used — dimension mismatch fails late and opaquely

**File:** `src/sif/search/vector.py:15-19`; `src/sif/search/hybrid.py:31`
**Issue:** The constructor stores `embedding_dim` but nothing in the class reads it, so `HybridSearcher.__init__(embedding_dim=768)` gives callers false confidence. Defaults are also inconsistent: `HybridSearcher`/`VectorSearcher` default to 768, `SchemaManager` to 384, and `Settings.embedding_dim` to 1024 (which is what `Database.init_schema()` actually creates the table with). A mismatch surfaces only as a raw `sqlite3.OperationalError` from inside the vec0 MATCH at query time, violating the project's fail-fast convention that `SchemaManager._create_vector_tables` itself implements.
**Fix:** Validate in `VectorSearcher.__init__`: read the actual `FLOAT[n]` from `sqlite_master` (the regex logic already exists in `schema.py:291-304`) and raise a descriptive RuntimeError on mismatch with the passed `embedding_dim`; then delete or honor the parameter consistently.

### WR-07: LLM cache TTL mixes naive-local and aware-UTC timestamps

**File:** `src/sif/database/repositories.py:492-495`
**Issue:** `LLMCacheRepository.set` computes `datetime.fromtimestamp(expires_at)` (naive **local** time) and stores its ISO string, while `get`/`clear_expired` compare against `datetime.now(timezone.utc).isoformat()` (aware UTC). The TEXT comparison is therefore wrong for any machine not on UTC: on UTC+2, entries live ~2 hours past their TTL; on UTC-8, they are treated as expired ~8 hours early. Likely pre-existing code, but it lives in a file this phase reworked.
**Fix:** `datetime.fromtimestamp(expires_at, tz=timezone.utc).isoformat()` (and use `ttl_seconds > 0`, since `ttl_seconds=0` currently means "no expiry" via the truthiness check).

### WR-08: RRF labels every non-first result list's score as `vector_score`

**File:** `src/sif/search/rrf.py:50` and `src/sif/search/rrf.py:134`
**Issue:** `score_key = "bm25_score" if list_idx == 0 else "vector_score"` is correct for the two-list BM25+vector case, but `SearchPipeline.search` also calls `self.hybrid.rrf.fuse(all_results, ...)` across N query-variant lists (`src/sif/search/hybrid.py:259`), where every list after the first holds hybrid results whose scores are written into `scores["vector_score"]`. The explain output (`result.scores`) then reports a hybrid score under a vector label.
**Fix:** Pass an explicit per-list key (e.g., `fuse(results_lists, limit, score_keys=[...])`) or have the multi-query fusion path skip per-source score labeling.

### WR-09: "rm alias" test never exercises the alias

**File:** `tests/unit/cli/test_context.py:354-375`
**Issue:** `TestContextRmAlias.test_rm_alias_works` invokes `context_remove` directly — the same call the `TestContextRemove` test makes — and never touches `context_group`'s registered `rm` name. The alias registration at `src/sif/cli/commands/context.py:157` is untested; if it regressed (`sif context rm <id>` -> "No such command"), this test would still pass.
**Fix:** Invoke through the group: `runner.invoke(context_group, ["rm", context_id], obj=ctx_obj)` and assert exit code 0.

### WR-10: SIF_DB_PATH test patches Settings, so the env var is never consumed

**File:** `tests/unit/cli/test_status.py:47-76`
**Issue:** `test_status_respects_env_var` passes `SIF_DB_PATH` to `CliRunner(env=...)` but then patches `sif.cli.main.get_settings` with a `MagicMock` whose `get_db_path` returns a mock pre-configured to `/tmp/test-sif.db`. The assertion passes because of the mock's configured value, not because `Settings` parsed the env var; if env parsing in `Settings`/pydantic broke, this test — named after exactly that behavior — would still pass. (The sibling test has the same structure but does not claim env-var coverage.)
**Fix:** Build a real `Settings(db_path="/tmp/test-sif.db")` (or assert on `mock_settings` construction inputs) so the fallback path is exercised against actual Settings behavior.

## Info

### IN-01: `DEFAULT_INDEX_PATH` is dead

**File:** `src/sif/cli/main.py:22`
**Issue:** The constant is defined but never used; the `--index` default comes from `_get_default_db_path()` (line 26-28). It also encodes a stale path (repo docs claim `~/.sif/index.sqlite`, settings use platformdirs).
**Fix:** Delete the constant.

### IN-02: `context add global` silently ignores its TARGET argument

**File:** `src/sif/cli/commands/context.py:56-57`
**Issue:** For `global`, `target` is required by the command signature but overwritten with `"global"`. `sif context add global anything "desc"` succeeds while `anything` is discarded without warning.
**Fix:** Either make TARGET optional/ignored with an explicit message, or reject non-"global" targets for the global type.

### IN-03: `_attach_contexts` triplicated; hybrid copy contains test-coupled fallback

**File:** `src/sif/search/bm25.py:109-126`, `src/sif/search/vector.py:116-133`, `src/sif/search/hybrid.py:112-146`
**Issue:** Three near-identical implementations. The hybrid variant additionally carries a `hasattr(row, "keys")`/tuple fallback whose comment says it exists to "skip MagicMock rows in tests" (`hybrid.py:133`) — production code shaped by test doubles; the real `Database` connection always returns `sqlite3.Row` (`src/sif/database/database.py:39`), and the simple form in bm25/vector suffices. The hybrid path also re-queries contexts that bm25/vector already attached (redundant round trip).
**Fix:** Extract one shared helper (module-level function or mixin) used by all three searchers; delete the MagicMock fallback and rely on real-connection tests.

### IN-04: `fuse` / `fuse_with_weights` are ~50-line duplicates; all-zero weights crash

**File:** `src/sif/search/rrf.py:20-91, 93-175`
**Issue:** The two methods differ only in the weight multiplier. Additionally `normalized_weights = [w / total_weight ...]` raises `ZeroDivisionError` when all weights are 0, despite the docstring contract "must sum to 1.0" that the code then normalizes anyway.
**Fix:** Implement `fuse` as `fuse_with_weights(lists, [1.0] * len(lists), limit)`; validate `total_weight > 0`.

### IN-05: `Qwen3Reranker.load` duplicates ~30 lines across quiet branches

**File:** `src/sif/search/rerank.py:296-327`
**Issue:** The entire tokenizer/model load and device placement is duplicated under `if is_quiet():` / `else:`; only the `suppress_output()` wrapper differs.
**Fix:** Wrap the single load body in `with suppress_output():` conditionally: `load_ctx = suppress_output() if is_quiet() else contextlib.nullcontext()`.

### IN-06: `create_reranker(settings)` parameter is untyped

**File:** `src/sif/search/rerank.py:391-394`
**Issue:** `def create_reranker(settings) -> ...` lacks a parameter annotation, violating the project's strict typing convention (`disallow_untyped_defs = true`, per CLAUDE.md).
**Fix:** Annotate with `settings: Settings` (or a narrow Protocol exposing the reranker attributes it reads).

### IN-07: `DocumentRepository` imports from its own module

**File:** `src/sif/database/repositories.py:226`, `src/sif/database/repositories.py:244`
**Issue:** `from sif.database.repositories import DocumentChunkRepository` inside `repositories.py` — a pointless self-import (works only because the module is already in `sys.modules`).
**Fix:** Reference `DocumentChunkRepository(self.db)` directly; remove both local imports.

### IN-08: `PathContext.collection_id` is a dead field

**File:** `src/sif/core/models.py:189`; `src/sif/database/repositories.py:451`
**Issue:** The field is always reconstructed as `None` ("No longer stored; acceptable for transition" — comment at repositories.py:451) and is not persisted in the unified schema. Any consumer reading it gets a constant `None`.
**Fix:** Remove the field and the `collection_id` plumbing, or document it as deprecated-if-set.

### IN-09: Dimension-mismatch error advises a command that cannot fix it

**File:** `src/sif/database/schema.py:300-304`
**Issue:** The RuntimeError says "Rebuild the index with 'sif cleanup' or delete the database file", but `cleanup_cmd` only deletes orphan rows — it never drops/recreates `document_embeddings`, so it cannot resolve a `FLOAT[384]` vs `FLOAT[768]` mismatch. Users will run it and hit the same error.
**Fix:** Change the message to the action that works (delete the DB file / run a full re-index), or teach `cleanup` a `--rebuild` mode that drops and recreates the vec table.

### IN-10: ModelScope download failure swallowed at info level without the error

**File:** `src/sif/search/rerank.py:202-203`
**Issue:** `except Exception: logger.info(f"Loading ST reranker model: {model_id}")` discards the download exception entirely; a network failure is indistinguishable from a deliberate fallback and the log level understates it.
**Fix:** `logger.warning(f"ModelScope download failed, falling back to ST hub: {e}")`.

### IN-11: docsift migration message overstates what moved

**File:** `src/sif/cli/main.py:197-199`
**Issue:** Only `~/.local/share/docsift/models` is renamed, but the message prints "Migrated: ~/.local/share/docsift -> ~/.local/share/sif", implying the whole directory moved.
**Fix:** Print the actual paths moved (`.models -> sif/models`).

### IN-12: `intent` is concatenated into the search query and becomes required FTS terms

**File:** `src/sif/search/hybrid.py:205-206` (codified by `tests/unit/search/test_hybrid.py:411-428`)
**Issue:** `parsed_query = f"{options.intent}: {parsed_query}"` — because prefix parsing already ran, the intent text flows into `_build_fts_query`, which AND-joins tokens: searching `lex:test` with `intent="code"` requires the term "code" to appear, cutting recall instead of biasing ranking. The test pins the current behavior, so this is flagged as a design observation, not a regression.
**Fix:** If intent is meant to bias rather than filter, pass it to the embedder prompt/expansion stages only, or OR-join intent terms.

### IN-13: Reranker path silently drops results beyond `candidate_limit`

**File:** `src/sif/search/hybrid.py:262-268`
**Issue:** `candidates = results[: options.candidate_limit]; results = reranked` discards everything past `candidate_limit` even when `options.limit > candidate_limit` (core `SearchOptions.limit` is unbounded; e.g., limit=50 with the default candidate_limit=20 returns at most 20 results).
**Fix:** Clamp `limit = min(options.limit, options.candidate_limit)` up front, or set `candidate_limit`'s floor to `options.limit`.

### IN-14: Parallel `SearchOptions`/`SearchResult` model hierarchies

**File:** `src/sif/core/models.py:207-254` (dataclasses) vs `src/sif/models/search.py:17-92` (pydantic)
**Issue:** Two independent definitions of `SearchOptions` and `SearchResult` coexist: the dataclass pair drives bm25/vector/hybrid, while the pydantic pair drives `sif/search/strategy.py`. Both now carry `context_description`, doubling the maintenance of every future result field (this phase had to add it twice).
**Fix:** Track consolidation under the existing legacy-consolidation effort noted in CLAUDE.md; until then, add a comment cross-referencing the twin definitions so field additions stay synchronized.

---

_Reviewed: 2026-09-06T00:00:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
