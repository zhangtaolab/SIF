---
phase: 10-raise-pytest-coverage-to-90
reviewed: 2026-11-06T12:35:49Z
depth: standard
files_reviewed: 27
files_reviewed_list:
  - .claude/skills/sif-get/SKILL.md
  - DESIGN.md
  - docs/api-reference.md
  - docs/architecture.md
  - docs/cli-reference.md
  - docs/contributing.md
  - docs/development.md
  - docs/mcp-server.md
  - docs/models.md
  - docs/testing.md
  - src/sif/cli/commands/bench.py
  - src/sif/cli/commands/collection.py
  - src/sif/cli/commands/context.py
  - src/sif/cli/commands/get.py
  - src/sif/cli/commands/index.py
  - src/sif/cli/commands/ls.py
  - src/sif/cli/commands/search.py
  - src/sif/cli/main.py
  - src/sif/database/schema.py
  - src/sif/mcp/backend.py
  - tests/unit/cli/test_context.py
  - tests/unit/cli/test_database_lifecycle.py
  - tests/unit/cli/test_get.py
  - tests/unit/cli/test_search.py
  - tests/unit/cli/test_status.py
  - tests/unit/database/test_schema.py
  - tests/unit/mcp/test_backend.py
findings:
  critical: 0
  warning: 10
  info: 10
  total: 20
  necessity: 0
status: issues_found
---

# Phase 10: Code Review Report

**Reviewed:** 2026-11-06T12:35:49Z
**Depth:** standard
**Files Reviewed:** 27
**Status:** issues_found

## Summary

Reviewed the 10 changed source files (CLI command modules, `SchemaManager`, MCP `SearchBackend`), 9 documentation files, and 7 test files at standard depth, with cross-module verification into `database/database.py`, `database/connection.py`, `database/repositories.py`, `search/hybrid.py`, `search/vector.py`, `search/benchmark.py`, `embedding/manager.py`, and `utils/paths.py`. All 190 scoped unit tests pass (`env -u FORCE_COLOR NO_COLOR=1 pytest --no-cov` on the seven scoped test files).

No Critical findings. The changed code is generally careful (FTS legacy-trigger migration and gated rebuild in `schema.py` are correct; `context add` self-heal logic is well-tested against real SQLite). The 10 Warnings are real behavior gaps concentrated in three themes: (1) embedment-vector orphaning and transaction-scope inconsistencies between sibling commands (`collection remove` vs `index update`; `index update` vs `index embed`), (2) documented interface parameters that are silently ignored or mis-implemented (`multi-get --max-bytes` unit confusion, `ls`/`collection ls` subpath, MCP `get` `max_lines`), and (3) error paths that leak raw tracebacks or misleading remediation advice at the CLI boundary (`bench` fixture errors, `schema.py` dimension-mismatch message, `cleanup` timestamp comparison). No necessity findings met the evidence bar — every defensive guard examined (naive-datetime handling in `_merge_key`, `contextlib.suppress` around `DROP TABLE IF EXISTS` for missing vec0 modules, `status_cmd`'s settings fallback) guards a state that provably occurs in this stack.

## Warnings

### WR-01: `collection remove` orphans vec0 embeddings — vector search pollution until `sif cleanup`

**File:** `src/sif/cli/commands/collection.py:89-96`
**Issue:** `collection_remove` deletes documents (cascade removes chunks) but never purges `document_embeddings` rows. The vec0 virtual table cannot carry the FK cascade, so every embedding of the removed collection is orphaned in the KNN index — the exact failure mode that `index update`'s removal path explicitly guards against ("orphaned vectors would otherwise occupy KNN top-k slots and crowd live documents out of vector search results", `index.py:190-196`). `delete_by_collection` in `repositories.py:235-252` also skips the purge. Vector search stays degraded until the user happens to run `sif cleanup`.
**Fix:** Purge embeddings before deleting documents, mirroring `update_cmd`:
```python
vector_purger = _embedding_purger(db)  # reuse the helper from index.py, or move it to a shared module
if vector_purger is not None:
    doc_ids = [row[0] for row in conn.execute(
        "SELECT id FROM documents WHERE collection_id = ?", (collection.id,))]
    for doc_id in doc_ids:
        vector_purger.delete_embeddings_by_document(doc_id)
```

### WR-02: `index update` runs all collections in one implicit transaction — later failure discards earlier collections' work

**File:** `src/sif/cli/commands/index.py:55-108`
**Issue:** The entire multi-collection loop (line 55 `with db.connection:` through line 209) executes inside a single sqlite3 transaction that commits only on clean exit. A pre-update-command failure or parse-triggered `ClickException` for collection N rolls back every document added/updated/removed for collections 1..N-1 in the same run. `embed_cmd` deliberately fixed this exact defect class — its comment at `index.py:350-353` says "One transaction per collection (CR-02): a failed collection rolls back only its own work, and successful collections keep theirs. (The previous whole-run transaction discarded every successful collection...)" — but `update_cmd` retains the whole-run pattern.
**Fix:** Move `with db.connection:` inside the per-collection loop (one commit per collection), matching `embed_cmd`'s CR-02 posture.

### WR-03: `multi-get --max-bytes` truncates by characters after a byte-length check — limit can be exceeded up to 4x

**File:** `src/sif/cli/commands/get.py:212-213`
**Issue:** The guard measures bytes (`len(content.encode()) > max_bytes`) but the truncation slices characters (`content[:max_bytes]`). For non-ASCII content (CJK = 3 bytes/char, emoji = 4), the "truncated" output can still exceed `--max-bytes` by up to 4x, violating the documented "Max bytes per file" contract. The MCP backend's `_truncate_content` (`backend.py:28-35`) does this correctly (encode → slice bytes → decode with `errors="ignore"`).
**Fix:** Truncate on the encoded bytes like `_truncate_content` does:
```python
if len(content.encode("utf-8")) > max_bytes:
    suffix = "\n... [truncated]"
    content = content.encode("utf-8")[: max_bytes - len(suffix)].decode("utf-8", errors="ignore") + suffix
```

### WR-04: `ls` subpath filter matches the absolute stored path, not collection-relative paths, and is not segment-aligned

**File:** `src/sif/cli/commands/ls.py:51-53`
**Issue:** `docs.strip("/").startswith(prefix)` compares a subpath against the stripped **absolute** document path (`/Users/x/notes/python/a.md` → `Users/x/notes/python/a.md`). A natural relative subpath (`sif ls notes python/`) matches nothing unless the user types the full absolute prefix minus the leading slash. Additionally the bare `startswith` is not segment-aligned: subpath `python` also matches `python2/b.md`. The argument is documented in `docs/cli-reference.md:645-648` as a normal filter.
**Fix:** Resolve relative to the collection root and compare whole path segments:
```python
root = Path(coll.path)
rel = (root / subpath) if not Path(subpath).is_absolute() else Path(subpath)
target = str(rel).strip("/")
docs = [d for d in docs if d.path == target or d.path.startswith(target.rstrip("/") + "/")]
```

### WR-05: `collection ls` accepts and documents a `subpath` argument but ignores it entirely

**File:** `src/sif/cli/commands/collection.py:331-334`
**Issue:** The command declares `@click.argument("subpath", required=False)` (documented in `docs/cli-reference.md:191-197`) and then never uses it — the parameter is silenced with `# noqa: ARG001`. A user running `sif collection ls notes python` gets the full collection listing with no filtering and no warning.
**Fix:** Either implement the same filtering as `ls_cmd` (see WR-04) or drop the argument and regenerate `docs/cli-reference.md` via `make docs-generate`.

### WR-06: `bench` fixture load and validation errors escape as raw tracebacks

**File:** `src/sif/cli/commands/bench.py:68-69,125`
**Issue:** `json.load(f)` and `SearchEvaluator(fixture_data)` (whose `_validate_fixture` raises `ValueError` for missing `queries`/`query`/`relevant_docids` keys, `benchmark.py:55-63`) are outside the command's only error wrapper (`evaluator.evaluate` at lines 126-129). A malformed fixture — a plausible user error for a user-supplied file — produces an uncaught `JSONDecodeError`/`ValueError` traceback, violating the project convention "CLI commands raise `click.ClickException(str(e))` for user-facing errors" (CLAUDE.md). `open(fixture)` also omits `encoding="utf-8"`.
**Fix:**
```python
try:
    with open(fixture, encoding="utf-8") as f:
        fixture_data = json.load(f)
    evaluator = SearchEvaluator(fixture_data)
except (json.JSONDecodeError, ValueError, OSError) as e:
    raise click.ClickException(f"Invalid benchmark fixture '{fixture}': {e}") from e
```

### WR-07: MCP `get` tool silently ignores `max_lines` when `from_line` is absent

**File:** `src/sif/mcp/backend.py:139-147`
**Issue:** The tool schema (`handlers.py:99-102`) declares `from_line` and `max_lines` as independent optional integers, and `docs/mcp-server.md:126-131` documents both. But `get_document` applies line slicing only under `if from_line is not None:` — a client sending only `{"path_or_docid": ..., "max_lines": 50}` gets the full document (up to the 100 KB truncation) with no error and no slicing.
**Fix:** Handle `max_lines` alone:
```python
if from_line is not None or max_lines is not None:
    lines = content.split("\n")
    start = max(0, (from_line or 1) - 1)
    end = len(lines) if max_lines is None else start + max_lines
    ...
```

### WR-08: MCP `hybrid_search` cannot degrade to BM25 when sqlite-vec is unavailable — every `query` tool call fails

**File:** `src/sif/mcp/backend.py:95-99`
**Issue:** `SearchPipeline.__init__` unconditionally constructs `HybridSearcher`, which constructs `VectorSearcher` — and `VectorSearcher.__init__` raises `RuntimeError` when the sqlite-vec extension is missing (`vector.py:19-27`). `SearchBackend.__init__` deliberately degrades when the *embedder* fails ("logs a warning and serves BM25-only", `architecture.md` §Error Handling), and `HybridSearcher.search` already handles `embedder is None` as BM25-only (`hybrid.py:60-68`) — but in an environment without sqlite-vec, every MCP `query` call raises, while the same machine's `sif search search` (BM25) works fine. The server starts healthy (schema creation skips vector tables best-effort) and then fails on each tool call.
**Fix:** Catch the extension failure in `hybrid_search`'s `_search` and fall back to a direct `BM25Searcher` (log a warning once, mirroring the `__init__` embedder posture), or construct the pipeline once at backend init so the failure surfaces at startup instead of per-request.

### WR-09: `cleanup` compares naive-local ISO timestamps against aware-UTC ISO strings lexicographically

**File:** `src/sif/cli/main.py:181-189`
**Issue:** `cleanup_cmd` deletes expired `llm_cache` rows with `expires_at <= datetime.now(timezone.utc).isoformat()`. But `LLMCacheRepository.set` writes `expires_at` as a **naive local-time** ISO string (`datetime.fromtimestamp(expires_at)` without `tz=`, `repositories.py:531-536` — no offset suffix). Lexicographic comparison between `"...T20:00:00"` (UTC+8 local) and `"...T12:30:00.123+00:00"` keeps rows hours past expiry on east-of-UTC hosts and the fractional-vs-`+` ordering is format-accidental. `cleanup_cmd` also re-implements the repository's own `LLMCacheRepository.clear_expired()` inline.
**Fix:** Parse and compare as datetimes, reusing the repository method:
```python
from sif.database.repositories import LLMCacheRepository
cache_removed = LLMCacheRepository(conn).clear_expired()
```
and fix the write side to store `datetime.fromtimestamp(expires_at, tz=timezone.utc).isoformat()`.

### WR-10: Embedding-dimension mismatch error recommends `sif cleanup`, which cannot fix the mismatch

**File:** `src/sif/database/schema.py:335-339`
**Issue:** The `RuntimeError` raised on `FLOAT[dim]` mismatch says "Rebuild the index with 'sif cleanup' or delete the database file." `cleanup_cmd` (`main.py:158-195`) only deletes orphaned chunks/embeddings and expired cache rows — it never drops or re-creates the vec0 table, so following the printed advice is a no-op and the user stays blocked. (Contrast `index.py:305-309`, which correctly says "Set SIF_EMBEDDING_DIM to the model's dimension and rebuild.")
**Fix:** Change the message to name a working remediation: "Delete the database file (or run `sif index embed` after setting SIF_EMBEDDING_DIM to {dim}) to rebuild the vector index."

## Info

### IN-01: Identical if/else branches under a comment promising syntax highlighting that doesn't exist

**File:** `src/sif/cli/commands/get.py:120-124`
**Issue:** `if doc.path.endswith(".md"): console.print(content) else: console.print(content)` — both branches are byte-identical; the comment "Display with syntax highlighting if markdown" describes behavior that was never implemented. Dead code.
**Fix:** Delete the branch (keep a single `console.print(content)`), or implement the intended Markdown rendering.

### IN-02: `vsearch_cmd` function-local imports duplicate module-level imports of the same names

**File:** `src/sif/cli/commands/search.py:356-357`
**Issue:** `from sif.database.database import Database` and `from sif.database.repositories import CollectionRepository` inside `vsearch_cmd` shadow the identical module-level imports at lines 19-20. Consequence is real: the closure tests must patch `sif.database.database.Database` for `vsearch_cmd` but `sif.cli.commands.search.Database` for `search_cmd`/`query_cmd` — the test file documents this trap at `test_search.py:2038-2042`.
**Fix:** Delete the two redundant local imports and use the module-level names.

### IN-03: `manager._model` private access in two commands — `EmbeddingManager` has no public model accessor

**File:** `src/sif/cli/commands/bench.py:119`, `src/sif/cli/commands/search.py:597`
**Issue:** Both sites reach into `EmbeddingManager._model` with `# noqa: SLF001`. The manager (`embedding/manager.py`) exposes no public property for the loaded embedder, so every caller must violate encapsulation.
**Fix:** Add `@property def model(self) -> Embedder | None: return self._model` to `EmbeddingManager` and use it at both call sites.

### IN-04: `quiet` recomputed redundantly after the search completes

**File:** `src/sif/cli/commands/search.py:230,407,609`
**Issue:** Each command computes `quiet = quiet or ctx.obj.get("quiet", False)` at entry (lines 189, 341, 508) and then recomputes the identical expression right before output. Nothing reassigns `quiet` in between; the second read is dead.
**Fix:** Delete the recomputation at lines 230, 407, and 609.

### IN-05: `--config` global option is accepted, documented, and never consumed

**File:** `src/sif/cli/main.py:51-57,76`
**Issue:** The group stores `ctx.obj["config_path"]` (the only reference in `src/sif/`), and `docs/cli-reference.md:13` documents "Path to the configuration file". No command reads it — configuration actually comes from Pydantic Settings env vars. The option is a documented no-op.
**Fix:** Either wire it into `get_settings` or remove the option and regenerate the CLI reference.

### IN-06: `status_cmd` fallback calls `get_settings()` without the ValidationError guard used elsewhere

**File:** `src/sif/cli/main.py:113-114`
**Issue:** `_get_default_db_path` (lines 28-39) carefully converts pydantic `ValidationError` to `ClickException` ("REVIEW WR-09"), and `query_cmd`/`vsearch_cmd` do the same for their settings touchpoints. The `index_path is None` fallback in `status_cmd` calls `get_settings().get_db_path()` unguarded — reachable when `status_cmd` is invoked with an obj lacking `index_path` (as `test_status.py` does) — so invalid env config escapes as a raw traceback on that path.
**Fix:** Wrap the fallback in the same `try/except ValidationError → click.ClickException` as `_get_default_db_path`.

### IN-07: Inconsistent embedding-dim resolution across commands — 384 magic fallback and per-query probe

**File:** `src/sif/cli/commands/bench.py:81,85`, `src/sif/cli/commands/search.py:568`
**Issue:** `bench_cmd` falls back to `embedding_dim = 384` when the embedder fails to load (settings default is 1024; `embed_cmd` at `index.py:288-292` was deliberately made "probe-free" via `get_model_info()`), while `query_cmd` still pays `manager.embed_single("probe")` on every invocation — a billed API call for remote backends that `embed_cmd`'s comment explicitly says to avoid.
**Fix:** Use `manager.get_model_info().get("embedding_dim")` with the probe as fallback in `query_cmd` (and drop the 384 literal in `bench_cmd`, which is only reachable when the embedder is None and the value is unused by BM25-only search).

### IN-08: Disk-fallback `read_text()` without explicit encoding

**File:** `src/sif/cli/commands/get.py:84`
**Issue:** The unindexed-file fallback reads with `path.read_text()` — locale-dependent (cp1252 on Windows), so a UTF-8 note with non-ASCII characters can decode incorrectly or raise. Every other read in the codebase passes `encoding="utf-8"` (see the test fixtures).
**Fix:** `content = path.read_text(encoding="utf-8")`.

### IN-09: api-reference example uses `sqlite3.connect("~/...")` — tilde is not expanded

**File:** `docs/api-reference.md:739`
**Issue:** The "Complete Search Example" opens the database with `with sqlite3.connect("~/.local/share/sif/sif.db") as db:`. sqlite3 does not expand `~`; it treats the path literally, so the example fails with "unable to open database file" (or writes to a directory literally named `~`) instead of opening the user's index. `api-reference.md` is not in `tests/test_docs.py`'s validated set, so CI cannot catch this.
**Fix:** `from pathlib import Path; db_path = Path("~/.local/share/sif/sif.db").expanduser()` then `sqlite3.connect(str(db_path))`.

### IN-10: Backend tests construct a real `DatabaseConnection("/tmp/test.db")` outside tmp_path

**File:** `tests/unit/mcp/test_backend.py:22,97,117,133`
**Issue:** `test_hybrid_search_mocks`, `test_get_document_found`, `test_get_document_with_line_slicing`, and `test_get_document_not_found` patch the repositories but not `DatabaseConnection`, so `_run_in_db` really opens (and sqlite creates) `/tmp/test.db` — verified present on this machine after the run. The suite pollutes a shared filesystem location and can interfere with itself under parallel execution (`pytest-xdist`) or a read-only sandbox.
**Fix:** Point the fixture at `tmp_path`: build `SearchBackend(str(tmp_path / "test.db"))` inside the tests, or patch `sif.mcp.backend.DatabaseConnection`.

---

_Reviewed: 2026-11-06T12:35:49Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
