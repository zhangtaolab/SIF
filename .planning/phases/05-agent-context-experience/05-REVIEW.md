---
phase: 05-agent-context-experience
reviewed: 2026-11-05T03:09:21Z
depth: standard
files_reviewed: 39
files_reviewed_list:
  - .claude/skills/sif-get/SKILL.md
  - .claude/skills/sif-search/SKILL.md
  - .github/workflows/docs.yml
  - README.md
  - docs/architecture.md
  - docs/cli-reference.md
  - docs/configuration.md
  - docs/development.md
  - docs/installation.md
  - docs/mcp-server.md
  - docs/models.md
  - docs/quickstart.md
  - pyproject.toml
  - scripts/generate_arch_diagram.py
  - scripts/generate_cli_ref.py
  - scripts/generate_config_ref.py
  - src/sif/cli/commands/bench.py
  - src/sif/cli/commands/context.py
  - src/sif/cli/commands/search.py
  - src/sif/cli/main.py
  - src/sif/core/models.py
  - src/sif/database/connection.py
  - src/sif/embedding/embedder.py
  - src/sif/embedding/manager.py
  - src/sif/indexing/watcher.py
  - src/sif/mcp/handlers.py
  - src/sif/models/embedding.py
  - src/sif/search/bm25.py
  - src/sif/search/hybrid.py
  - src/sif/search/rerank.py
  - src/sif/search/vector.py
  - src/sif/utils/paths.py
  - tests/test_docs.py
  - tests/unit/cli/test_bench.py
  - tests/unit/cli/test_context.py
  - tests/unit/cli/test_search.py
  - tests/unit/database/test_repositories.py
  - tests/unit/search/test_collection_filter.py
  - tests/unit/search/test_context_attach.py
findings:
  critical: 0
  warning: 11
  info: 14
  total: 25
  necessity: 2
status: issues_found
---

# Phase 05: Code Review Report (Incremental re-review)

**Reviewed:** 2026-11-05T03:09:21Z
**Depth:** standard
**Files Reviewed:** 39
**Status:** issues_found

## Scope Note

Incremental re-review of Phase 05 (Agent Context Experience) over the 37 files
changed since the prior review commit (`e3aad7b`). Per instructions, findings are
made against the code as it stands now. The phase-05 context surface
(`src/sif/cli/commands/context.py`, `src/sif/search/context_attach.py` consumers in
`bm25.py`/`vector.py`/`hybrid.py`, `src/sif/core/models.py`, `src/sif/utils/paths.py`)
was the primary focus; docs, skills, scripts, and the docs CI workflow were reviewed
as source.

Quality gates re-run during review: the four phase-05 test files pass
(49 passed, `env -u FORCE_COLOR NO_COLOR=1`, no coverage artifacts);
`scripts/generate_cli_ref.py` and `scripts/generate_config_ref.py` regenerate
byte-identical docs (CI drift gate holds). `scripts/generate_arch_diagram.py` output
does NOT match the committed `docs/architecture.md` (WR-08).

## Verification of Prior-Review Claims (2026-09-07 report, same path — now overwritten)

- **WR-01 (malformed `~user` row bricks search/prune/add): FIXED — fix is real.**
  `normalize_path` (`src/sif/utils/paths.py:79-82`) is now total (degrades to the raw
  string), `_resolve_path_target` (`src/sif/cli/commands/context.py:37-49`) converts an
  un-expandable CLI target into a `click.ClickException`, and both regression tests
  exist and pass (`test_normalize_path_unexpandable_tilde_degrades_to_raw_form`,
  `test_malformed_tilde_row_does_not_crash_attach`,
  `test_add_path_unexpandable_tilde_clean_error`).
- **WR-02 (self-heal merge misses canonical re-add): FIXED — fix is real.**
  `_self_heal_path_row` (`src/sif/cli/commands/context.py:52-93`) now falls back to
  normalized-key resolution over all path rows, collapses losers inside the same
  transaction, and only proceeds when `update_target` landed. Pinned by
  `test_readd_via_canonical_merges_legacy_alias_rows`.
- **IN-01 (TEXT-ordered newest-wins): STILL OPEN — carried forward** (see IN-01 below).
- **IN-02 (tests call `SchemaManager` private methods): STILL OPEN — carried forward** (IN-02).
- **IN-03 (`update_target` return ignored): PARTIALLY FIXED.** The candidates branch now
  checks the return (`context.py:89-90`); the exact-spelling branch still ignores it
  (`context.py:76`) — carried forward (IN-03).
- **CR-01 (FTS5 external-content DELETE triggers, `src/sif/database/schema.py`): out of
  this review's file scope (schema.py unchanged and not in the changed set) — must stay
  on the books.**

## Summary

The phase-05 core is in good shape: the shared `attach_path_contexts` helper with
Python-side `normalize_path` matching is correct and well tested against real SQLite,
the write-side self-heal merge is transactional and covers the canonical re-add path,
and the exclude-all sentinel contract is consistently enforced and pinned by real-SQL
tests in all three searchers. No SQL injection, secret-handling, or traversal issues
were found; all new SQL is parameterized or constant.

The adversarial pass nevertheless found real defects, concentrated in three areas:
(1) the `--intent` feature is implemented by string-prepending the intent into the
literal query, which turns the intent word into a hard AND term in BM25 and shifts the
vector embedding — contradicting its documented purpose as an expansion "hint" while a
dedicated unused `intent` parameter exists on `QueryExpansion.expand` (WR-01);
(2) silently-dropped unknown collection names (`-c typo`) produce the exclude-all
sentinel and "No results found" with no error (WR-02), and `context add/remove`
silently materialize an empty index database on a fresh machine (WR-03); (3) the
documentation layer makes promises the code does not keep — global/collection contexts
are stored but never consumed by any search path, and path contexts match exact
document paths only, yet quickstart.md claims directory scope and global/collection
effect (WR-07), while `docs/architecture.md`'s dependency graph has drifted from its
own generator (WR-08). Remaining findings are robustness issues in secondary modules
(`DatabaseConnection.execute` returns a closed cursor, `FileWatcher` observer
lifecycle, `ModelScopeEmbedder`'s model-dir heuristic), output-escaping gaps in the
CSV/XML formatters, and carried-forward Info items.

## Critical Issues

None in this review's file scope. (Prior-review CR-01 in `src/sif/database/schema.py`
remains open but out of the changed set — see Scope Note.)

## Warnings

### WR-01: `--intent` is prepended into the literal query — becomes a hard AND term in BM25 and pollutes the vector embedding

**File:** `src/sif/search/hybrid.py:173-174` (with `src/sif/search/bm25.py:159-171`, `src/sif/search/expansion.py:44-60`, `src/sif/cli/commands/search.py:404`)
**Issue:** `SearchPipeline.search` applies intent via `parsed_query = f"{options.intent}: {parsed_query}"`. That string is then (a) searched as-is by the BM25 leg, where `_build_fts_query` ANDs every whitespace token after stripping `:` — so `sif search query --intent code "deploy notes"` only matches documents containing all of `code`, `deploy`, `notes`; documents lacking the literal intent word vanish from the BM25 leg; and (b) embedded as `"code: deploy notes"` on the vector leg, shifting the query embedding. The `--intent` CLI help says "Search intent hint for query expansion", and `QueryExpansion.expand(query, intent=None)` (`expansion.py:44-60`) has an explicit `intent` parameter designed to prepend intent to expansion *variants only* — but the pipeline never passes it (`hybrid.py:203` calls `expand(parsed_query)`), so the purpose-built mechanism is dead code while the string hack narrows recall. (A unit test pins the prepend itself, `tests/unit/search/test_hybrid.py:412-423`, but no test pins the BM25 recall consequence.)
**Fix:** Pass intent through to the expander instead of mutating the searched query:

```python
# hybrid.py — replace the prepend
if options.intent:
    # hint only; never part of the literal BM25/vector query
    pass
...
expanded = self.query_expander.expand(parsed_query, intent=options.intent)
```

Keep `parsed_query` intent-free for both the BM25 and vector legs; only expansion variants (and, if desired, the reranker prompt) should see the intent. Update `test_intent_prepended_to_query` accordingly.

### WR-02: Unknown `-c/--collection` names are silently dropped; all-miss resolves to the exclude-all sentinel with no error

**File:** `src/sif/cli/commands/search.py:161-168` (same pattern at `search.py:328-335`, `search.py:466-474`, `src/sif/cli/commands/bench.py:102-109`)
**Issue:** For explicit `--collection` names, each name is looked up and silently skipped when `get_by_name` misses. If every given name misses, `options.collection_ids` stays `[]` — the exclude-all sentinel — so the searchers correctly return zero results, but the user sees only "No results found": a typo'd collection name is indistinguishable from a genuine empty result. This is inconsistent with `context add collection`, which errors with "Collection 'x' not found" (`context.py:130`), and with the MCP backend's own intent (it at least special-cases all-miss, though it too returns `[]` silently, `src/sif/mcp/backend.py:90-93`). The sentinel comment in `bm25.py:47-55` frames `[]` as coming from enabled-collections resolution, but the explicit `-c` path produces it too.
**Fix:** Resolve names up front and fail loudly on unknowns (or at least warn):

```python
if collection:
    with db.connection:
        repo = CollectionRepository(db.connection)
        resolved = {c.name: c.id for c in (repo.get_by_name(n) for n in collection) if c}
    missing = [n for n in collection if n not in resolved]
    if missing:
        raise click.ClickException(f"Collection(s) not found: {', '.join(missing)}")
    options.collection_ids = list(resolved.values())
```

Apply the same treatment in `vsearch_cmd`, `query_cmd`, and `bench_cmd`.

### WR-03: `context add` / `context remove` silently create an empty index database when no index exists

**File:** `src/sif/cli/commands/context.py:114-116` (`context_add`), `context.py:170-172` (`context_remove`)
**Issue:** Unlike `context list` / `context prune` (which guard with `index_path.exists()` and print "No index found." — `context.py:195-197, 231-233`), `context add` goes straight to `Database(index_path)` + `db.init_schema()`. `Database.__init__` mkdirs the parent and `sqlite3.connect` creates the file, so `sif context add ...` on a machine with no index materializes a brand-new empty index DB (all tables) as a side effect, and reports success for a context that can never attach to anything. `context remove` on a missing index likewise creates the DB just to answer "No context found with ID".
**Fix:** Add the same guard used by the sibling commands:

```python
index_path = ctx.obj["index_path"]
if not index_path.exists():
    console.print("[yellow]No index found. Run 'sif index update' first.[/yellow]")
    raise SystemExit(1)  # or click.ClickException, consistently with list/prune semantics
```

### WR-04: `DatabaseConnection.execute()/executemany()` return a cursor whose connection is already closed

**File:** `src/sif/database/connection.py:61-81`
**Issue:** Both methods run inside `with self.connect() as conn:`, whose `finally` closes the connection before the cursor is returned. Any caller that later calls `.fetchall()` / `.fetchone()` on the returned cursor gets `sqlite3.ProgrammingError: Cannot operate on a closed database.` The class is publicly exported (`sif/database/__init__.py:3,17`) and is the MCP backend's connection factory, so the trap is live for any future caller; today it is merely an exported API that cannot be used as designed.
**Fix:** Don't return a detached cursor — either fetch inside the context (like `fetchone`/`fetchall` already do) or return `cursor.rowcount`/`lastrowid`:

```python
def execute(self, query, parameters=None) -> int:
    """Execute a write query; return affected row count."""
    with self.connect() as conn:
        cursor = conn.execute(query, parameters) if parameters else conn.execute(query)
        return cursor.rowcount
```

### WR-05: `FileWatcher` leaks/orphans observers on repeated `start()` and never unschedules on per-collection `stop()`

**File:** `src/sif/indexing/watcher.py:120-158`
**Issue:** `start()` unconditionally constructs a new `Observer` and assigns it to `self._observer` — a second `start()` (for another collection) drops the reference to the first observer without `stop()`/`join()`, leaving its threads running forever. `stop(collection_id)` only deletes the bookkeeping entry from `self._handlers`; while other handlers remain, the shared observer keeps the stopped collection's watches scheduled (the handler object is still attached to the watch handles), so "stopped" collections continue to be watched. (`watchdog` schedule() returns a `Watch` handle that must be `remove_observer_watch()`-ed.) The class is currently unwired (documented as future work in `docs/architecture.md:535`), but it is public API sold as "auto-indexing".
**Fix:** Keep one observer for the watcher's lifetime; track watches per collection:

```python
def start(self, collection_id, paths):
    if self._observer is None:
        self._observer = Observer()
        self._observer.start()
    handler = IndexingEventHandler(collection_id, self._indexer, self._extensions)
    watches = [self._observer.schedule(handler, p, recursive=True)
               for p in paths if Path(p).exists()]
    self._handlers[collection_id] = handler
    self._watches[collection_id] = watches

def stop(self, collection_id=None):
    ids = [collection_id] if collection_id else list(self._watches)
    for cid in ids:
        for w in self._watches.pop(cid, []):
            self._observer.unschedule(w)
        self._handlers.pop(cid, None)
    if not self._watches and self._observer:
        self._observer.stop(); self._observer.join(); self._observer = None
```

### WR-06: `ModelScopeEmbedder` picks the model directory via the first unordered `glob("*")` entry — can point SentenceTransformer at an auxiliary directory

**File:** `src/sif/embedding/embedder.py:294-300`
**Issue:** `model_dirs = list(model_path.glob("*"))` (arbitrary directory order, not sorted) then `model_dirs[0] if model_dirs[0].is_dir() else model_path`. Only the *first* entry's `is_dir()` is checked; if the first entry is an aux directory (exactly the Qwen3 `1_LogitScore/` shape that `rerank.py:_resolve_model_dir` was written to avoid, citing G-04-2), the embedder loads it and fails or mis-loads. `modelscope` is the default `model_type`, so this is the default embedding path. The careful resolver already exists in the same package (`rerank.py:56-87`) but was not applied here.
**Fix:** Reuse the same resolution logic:

```python
from sif.search.rerank import _resolve_model_dir  # or hoist it to a shared module
...
downloader = ModelDownloader(cache_dir)
model_path = downloader.download(model_id, force=force_download)
actual_model_path = _resolve_model_dir(model_path)
```

(Hoisting `_resolve_model_dir` into `sif/models/download.py` next to `ModelDownloader` would avoid the search→rerank import direction.)

### WR-07: Docs promise context behaviors the code does not implement (global/collection effects, directory scope)

**File:** `docs/quickstart.md:167-189`, `docs/models.md:157-160` (root cause surface: `src/sif/search/context_attach.py:53-56`)
**Issue:** quickstart.md states "Global Context — Applies to all searches", "Collection Context — Applies to searches in a specific collection", and "Path Context — Applies to a specific file **or directory**". In the implementation, `attach_path_contexts` is the *only* search-side consumer of `contexts` and it queries `WHERE context_type = 'path'` exclusively: global and collection contexts are stored (`context add` accepts them, `sif status` counts them) but never read by any search path, and path contexts match by exact normalized equality against `documents.path`, so a directory-path context can never attach to any document (documents are files). models.md additionally claims `global` uses `target_id="*"` while `context add global` stores the literal `"global"`. For a phase named "Agent Context Experience", the docs oversell the feature surface.
**Fix:** Either implement consumption (attach `collection`-type contexts to results of that collection, `global` to all results, and prefix-match directory targets) or correct the docs to state that only exact path contexts currently affect search output, e.g. quickstart.md: "Path Context — attaches to search results whose document exactly matches this path (file paths; directory scope is not yet supported)" and mark global/collection as "stored for future use".

### WR-08: `docs/architecture.md` dependency graph is stale relative to its own generator

**File:** `docs/architecture.md:322-367` (generator: `scripts/generate_arch_diagram.py`)
**Issue:** The diagram is captioned "_Generated by `scripts/generate_arch_diagram.py` from actual source imports._", but running the generator today yields one additional edge (`search --> config`, from `src/sif/search/rerank.py:19`'s `Settings` import) that the committed diagram lacks — verified by diffing generator output against the committed mermaid block. Unlike `cli-reference.md`/`configuration.md`, architecture.md has no CI drift gate (`docs.yml:34-38` only checks those two), so this silently rots.
**Fix:** Regenerate the diagram (`python scripts/generate_arch_diagram.py`) and commit the `search --> config` edge; extend the docs workflow drift check to cover it:

```yaml
- name: Verify generation scripts work
  run: |
    python scripts/generate_cli_ref.py
    python scripts/generate_config_ref.py
    python scripts/generate_arch_diagram.py > /tmp/arch.txt
    git diff --exit-code docs/cli-reference.md docs/configuration.md
    # extract the mermaid block and diff against /tmp/arch.txt, or write the file directly
```

### WR-09: Reranker construction catches only `ImportError`; an unvalidated `SIF_RERANKER_MODEL_TYPE` crashes `query` with a raw traceback

**File:** `src/sif/cli/commands/search.py:504-512` (with `src/sif/search/rerank.py:429`, `src/sif/config/settings.py:90-93`)
**Issue:** `create_reranker` raises `ValueError(f"Unknown reranker model_type: ...")` for any type other than `gguf`/`sentence_transformers`, and `Settings.reranker_model_type` has **no** field validator (only embedding `model_type` does, `settings.py:151-164`). So `SIF_RERANKER_MODEL_NAME=...` plus `SIF_RERANKER_MODEL_TYPE=cross-encoder` reaches `query_cmd`'s `except ImportError` / bare-warning handling and escapes as an unhandled `ValueError` traceback — violating the project's ClickException convention (CLAUDE.md).
**Fix:** Catch `ValueError` alongside `ImportError` (or add a `field_validator("reranker_model_type")` restricting to `{gguf, sentence_transformers}` so the failure surfaces at settings-validation time with pydantic's message):

```python
try:
    reranker = create_reranker(settings)
except ImportError:
    if not quiet:
        console.print("[yellow]Reranker not available. Install with: pip install -e '.[embed]'[/yellow]")
except ValueError as e:
    raise click.ClickException(str(e)) from e
```

### WR-10: CSV and XML formatters do not escape field values — filenames with `"`, `,`, `<`, `&` produce malformed output

**File:** `src/sif/cli/commands/search.py:54-60` (`format_results_csv`), `search.py:82-96` (`format_results_xml`)
**Issue:** `format_results_csv` wraps every field in double quotes but never escapes embedded double quotes (RFC 4180 requires doubling them), so a title/path like `my "notes".md` breaks the row into extra columns; a comma inside quotes is fine but the unescaped quote is not. `format_results_xml` interpolates `r.title`/`r.path`/`r.collection_name` raw with no XML entity escaping, so `<`, `>`, `&` in filenames yield unparseable XML. These outputs exist specifically for machine consumption (the skills feed `--json` to LLMs; `--csv`/`--xml` are for scripts), so malformed structure is a correctness defect, not cosmetics.
**Fix:**

```python
import csv, io, xml.sax.saxutils as sax

def format_results_csv(results):
    buf = io.StringIO()
    w = csv.writer(buf, quoting=csv.QUOTE_MINIMAL)
    w.writerow(["rank", "score", "title", "path", "collection"])
    for r in results:
        w.writerow([r.rank, f"{r.score:.4f}", r.title, r.path, r.collection_name])
    return buf.getvalue().strip()

# XML:
lines.append(f"    <title>{sax.escape(r.title)}</title>")
```

### WR-11: docs CI job has no `timeout-minutes`

**File:** `.github/workflows/docs.yml:17-38`
**Issue:** The `docs-test` job installs the full `.[dev]` extra and runs pytest with no job-level `timeout-minutes`. A hung install or test hangs the workflow until GitHub's 360-minute default cancels it, burning runner minutes on every docs-touching PR.
**Fix:**

```yaml
jobs:
  docs-test:
    runs-on: ubuntu-latest
    timeout-minutes: 15
```

## Info

### IN-01 (carried forward): attach "newest wins" uses SQLite TEXT ordering over mixed ISO-8601 formats

**File:** `src/sif/search/context_attach.py:53-56`
**Issue:** Carried forward from the prior review (its IN-01), still unfixed. `ORDER BY updated_at` compares strings; rows written today carry `+00:00` and microseconds while migrated rows can carry offset-less (or, theoretically, non-UTC-offset) forms. I probed this live: for naive-treated-as-UTC rows the text sort agrees with `_merge_key`'s parsed comparison, so the two "newest" definitions diverge only when a legacy row carries a non-`+00:00` offset (possible only via verbatim migration copies) — narrow, but the deterministic-newest invariant documented in the docstring is then violated and duplicate normalized keys can resolve to stale content. Equal timestamps also tie-break arbitrarily (SQL order among ties is unspecified).
**Fix:** Keep the ORDER BY for determinism but resolve collisions with parsed datetimes: build `context_map` via `dict` and on duplicate keys keep the row whose `datetime.fromisoformat(updated_at)` (naive→UTC) is newer.

### IN-02 (carried forward): tests build fixtures via `SchemaManager` private methods

**File:** `tests/unit/search/test_context_attach.py:52`, `tests/unit/database/test_repositories.py:31-32`
**Issue:** `manager._create_documents_table()` / `manager._create_contexts_table()` couple the suites to private schema internals; renaming those methods breaks repository/attachment tests that don't otherwise care.
**Fix:** Add a small public fixture-builder (e.g. `SchemaManager.create_core_tables()`) or use `create_all()` on a plain connection.

### IN-03 (carried forward, partially fixed): `update_target` return ignored in the exact-spelling branch

**File:** `src/sif/cli/commands/context.py:76`
**Issue:** The candidates branch now checks the return (`context.py:89-90`), but the exact dual-form branch still discards it; a `False` return (row vanished mid-transaction, subclass override) proceeds to `repo.update` and prints "Context updated" while the row keeps the verbatim target.
**Fix:** `if not repo.update_target(existing.id, actual_target): return None` so the caller falls through to the candidates scan / fresh-create path.

### IN-04: limit/rank inconsistencies between the BM25 and vector paths

**File:** `src/sif/search/vector.py:119`, `src/sif/search/bm25.py:89-103`, `src/sif/search/hybrid.py:180-185`
**Issue:** (a) `results[: max(1, options.limit)]` makes `limit=0` return **1** result on the vector path while BM25's `LIMIT 0` returns none. (b) BM25 assigns `rank` from the pre-`min_score` enumeration, so filtered results leave gaps (1, 2, 4, …) whereas the vector path re-ranks contiguously (`vector.py:120-121`). (c) The `vec:` prefix route (`hybrid.py:180-185`) returns chunk-level vector rows without the `_deduplicate_results` pass the hybrid route applies, so one document can appear multiple times under `vec:`/`vsearch` while `query` dedups it.
**Fix:** Trim with `results[:options.limit]` after clamping `limit` at the CLI (`IntRange(1, ...)`); assign BM25 ranks post-filter; route `vec:` results through `_deduplicate_results` for consistency with hybrid.

### IN-05: `EmbeddingManager.embed/embed_single` accept a `normalize` parameter that is silently ignored

**File:** `src/sif/embedding/manager.py:107, 214-217`
**Issue:** `normalize: bool = True  # noqa: ARG002` is accepted and discarded; backends always normalize (or don't) per their own implementation. The parameter suggests caller control that does not exist.
**Fix:** Remove the parameter (breaking-but-honest) or thread it into backends; at minimum document "currently ignored".

### IN-06: `create_reranker` phantom-defensive accessors on `Settings`

**File:** `src/sif/search/rerank.py:403-405`
**Issue:** `getattr(settings, "reranker_model_type", "gguf")`, `getattr(settings, "reranker_model_name", "")`, and `hasattr(settings, "get_cache_dir")` guard against a `Settings` type that always defines these: both fields are declared `Field`s (`src/sif/config/settings.py:81-95`) and `get_cache_dir` is a defined method (`settings.py:206`) used unguarded elsewhere (`src/sif/embedding/manager.py:66`). The `"gguf"`/`""` fallbacks are unreachable defaults that would silently mask a refactor rename. **Category:** necessity
**Fix:** Access directly — `settings.reranker_model_type`, `settings.reranker_model_name`, `str(settings.get_cache_dir())` — and let mypy catch drift.

### IN-07: Defensive `getattr` on the statically-guaranteed `SearchResult` dataclass

**File:** `src/sif/cli/commands/search.py:36-39` (`_display_snippet`), `search.py:232, 243, 369, 379, 583, 594`
**Issue:** `getattr(r, "snippet", None)`, `getattr(r, "highlights", None)`, and `getattr(r, "content", None)` defend against attributes that every `SearchResult` defines (`src/sif/core/models.py:207-221`); the default values (`None`/`[]`) can never engage. This obscures that a missing attribute would be a bug. **Category:** necessity
**Fix:** Access `r.snippet`, `r.highlights`, `r.content` directly. (The `hasattr(r, "get")` checks in `format_results_md/xml` are legitimate — they distinguish dict rows from dataclass rows after `add_line_numbers_to_results`.)

### IN-08: Duplicate `DatabaseConnection` classes with different semantics; `ConnectionPool` skips the sqlite-vec extension

**File:** `src/sif/database/connection.py:12` vs `src/sif/database/database.py:104`; `connection.py:122-130`
**Issue:** Two public classes named `DatabaseConnection` exist (connection.py: fresh connection per `connect()`; database.py: cached single connection) with different transaction/extension behavior — a classic wrong-import hazard already flagged as consolidation debt in CLAUDE.md. Separately, `ConnectionPool.get_connection` enables foreign keys but does **not** load sqlite-vec, unlike both `DatabaseConnection` factories, so any pooled connection used for vector operations fails `VectorSearcher`'s extension check. Currently only tests use the pool.
**Fix:** Consolidate on one `DatabaseConnection` (delete or rename the other); load sqlite-vec in `ConnectionPool.get_connection` exactly as `_create_connection` does.

### IN-09: Watcher event handlers are log-only stubs; injected indexer is never used

**File:** `src/sif/indexing/watcher.py:45-83`
**Issue:** All four handlers end at `logger.info(...)` with `# Trigger incremental index` comments; `self._indexer` is stored and never called, so "auto-indexing" currently means "log and do nothing". Acknowledged as future work in `docs/architecture.md:535`, but the constructor contract (`indexer: DocumentIndexer`) implies behavior that does not exist.
**Fix:** Wire the incremental calls (created/modified → `indexer.index_file`, deleted → removal, moved → rename) or mark the class/methods explicitly experimental/no-op until wired.

### IN-10: `contexts` table dropped the legacy `UNIQUE(context_type, target_id)` constraint

**File:** `src/sif/database/schema.py:97-104` (legacy DDL with UNIQUE: `src/sif/database/migrations.py:60-64`)
**Issue:** The new unified table has only a non-unique index, so duplicate (target, type) rows remain representable — which is exactly why the self-heal merge and the attach newest-wins tiebreak exist. Duplicates are only collapsed on explicit re-add; nothing prevents re-creation.
**Fix:** After the migration/self-heal paths run, add `CREATE UNIQUE INDEX IF NOT EXISTS idx_contexts_unique ON contexts(target_id, context_type)` (guarding pre-existing duplicates with a one-time dedup), making the upsert contract enforced by the schema rather than by read-side ordering.

### IN-11: `docs/installation.md` expected-output block is stale; nonexistent log file path

**File:** `docs/installation.md:146-167, 233`
**Issue:** The "Expected output" block shows `SIF version 0.1.0` (actual: 0.2.1, `pyproject.toml:7`), a `--format FORMAT` global option that does not exist (`src/sif/cli/main.py:32-49`), and command descriptions that don't match current help text. "Check logs: `~/.local/share/sif/logs/sif.log`" points at a file nothing writes — logging is stderr-only (`src/sif/utils/logging.py` has no FileHandler).
**Fix:** Update the block to the current `--help` output and replace the log-file advice with `-v` verbose / stderr redirection (`sif -v ... 2>sif.log`).

### IN-12: mcp-server.md overclaims query behavior: content and reranking

**File:** `docs/mcp-server.md:83, 113-125` (code: `src/sif/mcp/backend.py:82-111`, `src/sif/mcp/handlers.py:49-52`)
**Issue:** The tool description and response example show `"content": "Full document content..."` and "…and reranking", but `SearchBackend.hybrid_search` sets `include_content=False` (content is always null) and constructs `SearchPipeline` without a reranker. Also note the MCP query result mapping drops `context_description` entirely — the phase-05 context feature is CLI-JSON-only on the agent surface.
**Fix:** Correct the example (`"content": null`) and the description, or pass through `context_description` in the protocol `SearchResult` so agents actually receive the phase-05 context annotations.

### IN-13: `context list` shows raw collection UUIDs; `--line-numbers` default in the search skill is ineffective without `--full`

**File:** `src/sif/cli/commands/context.py:220`; `.claude/skills/sif-search/SKILL.md:29, 35-45`
**Issue:** (a) For `collection`-type rows the Target column prints the stored collection ID (a UUID), not the name the user typed. (b) The skill's smart default includes `--line-numbers`, but `SearchPipeline._apply_snippets` deliberately never writes `result.content` without `--full` (`hybrid.py:243-265`), so `line_numbers` serializes as `""` in every skill invocation — dead weight in each command.
**Fix:** (a) Resolve collection IDs to names for display (or store/show both). (b) Drop `--line-numbers` from the skill default or add `--full` when line numbers are wanted.

### IN-14: `Qwen3Reranker.load()` duplicates the entire loading block for quiet/non-quiet

**File:** `src/sif/search/rerank.py:302-332`
**Issue:** The tokenizer/model/device/token-id setup is copy-pasted verbatim into both branches; only the `suppress_output()` wrapper differs. Divergence risk on edit (the pattern already bit `_resolve_model_dir`'s rationale in WR-06).
**Fix:**

```python
def _load(self):
    from transformers import AutoModelForCausalLM, AutoTokenizer
    self._tokenizer = AutoTokenizer.from_pretrained(local_path, padding_side="left")
    ...  # shared body

if is_quiet():
    with suppress_output():
        _load()
else:
    _load()
```

---

_Reviewed: 2026-11-05T03:09:21Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
