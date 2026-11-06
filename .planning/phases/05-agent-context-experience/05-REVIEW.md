---
phase: 05-agent-context-experience
reviewed: 2026-11-06T06:46:04Z
depth: standard
files_reviewed: 11
files_reviewed_list:
  - src/sif/cli/commands/context.py
  - src/sif/cli/commands/search.py
  - src/sif/cli/main.py
  - src/sif/database/schema.py
  - src/sif/search/vector.py
  - tests/unit/cli/test_main.py
  - tests/unit/cli/test_search.py
  - tests/unit/cli/test_status.py
  - tests/unit/database/test_repositories.py
  - tests/unit/database/test_schema.py
  - tests/unit/search/test_vector.py
findings:
  critical: 2
  warning: 4
  info: 5
  total: 11
  necessity: 0
status: issues_found
---

# Phase 5: Code Review Report

**Reviewed:** 2026-11-06T06:46:04Z
**Depth:** standard
**Files Reviewed:** 11
**Status:** issues_found

## Summary

Staleness-refresh review of the phase-05-covered files (context CLI, context repository/schema, search result context attachment, vector search) against their current post-rename state. The core phase-05 mechanics — `normalize_path`-based context matching, the self-heal merge, the exclude-all collection sentinel, the FTS trigger migration with gated rebuild — are sound and well tested (151 tests in the scoped files pass locally). However, the review surfaced two crash-class defects in the Rich-rendered output paths, a proven timezone-dependent cache bug (an in-scope test fails under `TZ=America/Los_Angeles`), and several robustness gaps where foreseeable user input escapes as raw tracebacks or silently degrades to empty results. All findings were verified empirically against the project venv (Python 3.13, click 8.3.2), not inferred from reading alone.

Necessity (#4100) was assessed per `$HOME/.claude/gsd-core/references/necessity-review.md`; the candidate guards examined (the `update_target` rowcount check in `context.py`, the NULL-`chunk_id` skips in `vector.py`, the exclude-all sentinel) all defend states at a persisted-database trust boundary or are deliberate defense-in-depth, so none qualify. `necessity: 0`.

## Critical Issues

### CR-01: Rich markup injection — unescaped query/title/content crash or silently vanish in all three search commands

**File:** `src/sif/cli/commands/search.py:275` (also 421, 646, 288-289, 292-296, 433-434, 436-439, 659-660, 663-666)
**Issue:** Rich parses console markup in `Table` titles and cell strings by default. The user's query is interpolated raw into the table title in all three commands (`Table(title=f'Search Results: "{query}"')` at line 275, `vsearch` line 421, `query` line 646). A query (or indexed document title/content) containing an unmatched closing tag — e.g. `sif search '[/]'` or `[/bold]`, entirely plausible when searching notes about coding/markup — raises `rich.errors.MarkupError` and kills the command with a raw traceback. Verified empirically: `Console().print(Table(title='Search Results: "[/]"'))` raises `MarkupError: closing tag '[/]' at position 17 has nothing to open`. Matched-but-unknown tags are silently swallowed instead: a title cell `todo [wip] note` renders as `todo  note` (verified). Only the Snippet column is escaped (`escape(_display_snippet(r))` at lines 290, 661) — the fix was applied to one column of five and to neither of the other two commands' tables.
**Fix:** Escape every user-derived string crossing a Rich API: wrap the query in `Table(title=...)` with `escape(query)` (or pass `rich.text.Text(query)`), and apply `escape()` to `r.title`, `r.collection_name`, and the `prepend_line_numbers(content)` cell in all three table blocks — i.e. extend the existing snippet-column treatment to the remaining columns and titles:

```python
table = Table(title=f'Search Results: "{escape(query)}"')
...
row = [
    str(r.rank),
    f"{r.score:.4f}",
    escape(r.title[:_TITLE_MAX_LEN] + "..." if len(r.title) > _TITLE_MAX_LEN else r.title),
    escape(r.collection_name),
    escape(_display_snippet(r)),
]
if line_numbers and (content := getattr(r, "content", None)):
    ...
    row.append(escape(content))
```

### CR-02: Rich markup injection in `context list` — stored context content crashes or silently loses text

**File:** `src/sif/cli/commands/context.py:232`
**Issue:** `table.add_row(ctx_item.context_type, ctx_item.path, content_text)` passes user-authored context content and the stored target path into a Rich table without `escape()`. Context content is arbitrary user text: `sif context add path ~/notes/a.md "[/]"` followed by `sif context list` raises `rich.errors.MarkupError` (same mechanism as CR-01, verified — cells are markup-parsed), and everyday bracket text like `[WIP] draft` loses `[WIP]` from the display. The context rows also include verbatim legacy spellings, so content stored before this review is equally affected.
**Fix:** Apply the same treatment as the search snippet column:

```python
from rich.markup import escape
...
table.add_row(escape(ctx_item.context_type), escape(ctx_item.path), escape(content_text))
```

## Warnings

### WR-01: LLM cache TTL writes naive local-time expiry compared against aware UTC strings — cache broken west of UTC; in-scope test fails

**File:** `src/sif/database/repositories.py:534-535` (cross-ref: in-scope `tests/unit/database/test_repositories.py:475-476`, `src/sif/cli/main.py:183-189`)
**Issue:** `LLMCacheRepository.set` computes `expires_at` as `datetime.fromtimestamp(ts).isoformat()` — a naive **local**-time string — while `get`/`clear_expired` and `cleanup_cmd` compare against `datetime.now(timezone.utc).isoformat()` (aware, `+00:00` suffix) via lexicographic SQL string comparison. On any machine west of UTC, a freshly cached entry with a TTL is immediately "expired": `get` returns `None` and `cleanup` purges it. East of UTC, entries linger past expiry and cleanup misses them. Proven: running the in-scope test under `TZ=America/Los_Angeles` fails (`assert repo.get("model", "short-lived") == "future response"` → `None`), while it passes under the local `Asia/Shanghai`. The test suite is therefore timezone-flaky and the TTL feature is incorrect for roughly half the planet.
**Fix:**
```python
if ttl_seconds:
    expires_at = datetime.fromtimestamp(
        datetime.now(timezone.utc).timestamp() + ttl_seconds, timezone.utc
    ).isoformat()
```

### WR-02: Unknown `-c/--collection` names silently resolve to exclude-all — typo returns "No results found" instead of an error

**File:** `src/sif/cli/commands/search.py:214-217` (also 390-392, 528-531)
**Issue:** In all three commands the explicit-collection loop is `for name in collection: coll = repo.get_by_name(name); if coll: options.collection_ids.append(coll.id)`. Unknown names are skipped without any signal. When none resolve, `collection_ids == []`, which the searcher exclude-all sentinel (`vector.py:47`, `bm25.py:54`) defines as "zero results" — so `sif search foo -c notes-typo` prints "No results found." with exit code 0, indistinguishable from a genuine empty result. This contradicts the project's own convention of raising `click.ClickException` for unknown collection targets (`context add` does exactly that at `context.py:136`).
**Fix:** Collect unresolved names and fail loudly (or at minimum warn):

```python
options.collection_ids = []
missing = []
for name in collection:
    coll = repo.get_by_name(name)
    if coll:
        options.collection_ids.append(coll.id)
    else:
        missing.append(name)
if missing:
    raise click.ClickException(f"Collection(s) not found: {', '.join(missing)}")
```

### WR-03: `vsearch` surfaces embedding-dimension mismatch as a raw sqlite3 traceback

**File:** `src/sif/cli/commands/search.py:399-401`
**Issue:** `results = searcher.search(query_embedding, options)` is not wrapped in any handler. Verified against real sqlite-vec: querying a `FLOAT[384]` table with a mismatched vector raises `sqlite3.OperationalError: Dimension mismatch for query vector for the "embedding" column. Expected 4 dimensions but received 8.` This is reachable via the supported `--model-type` override (`settings.model_copy(update={...})` at line 365 bypasses validation, and `init_schema` checked the *settings* dim, not the override's), or simply after the user changes `SIF_MODEL_NAME` without re-embedding. Every other failure path in this file converts to `click.ClickException` (lines 361-373; the embedder loaders) per the CLAUDE.md convention "CLI commands raise `click.ClickException(str(e))` for user-facing errors" — this one leaks a traceback.
**Fix:**
```python
with db.connection:
    searcher = VectorSearcher(db.connection, len(query_embedding))
    try:
        results = searcher.search(query_embedding, options)
    except sqlite3.OperationalError as e:
        raise click.ClickException(
            f"Vector search failed (embedding/model dimension mismatch?): {e}"
        ) from e
```
(needs `import sqlite3` at module top.)

### WR-04: Self-heal merge skips duplicate collapsing in the exact-match branch, contradicting its documented contract

**File:** `src/sif/cli/commands/context.py:74-77`
**Issue:** `_self_heal_path_row` documents "Every historical spelling is merged into one canonical row: newest updated_at wins, older duplicates are deleted, and no second row is created." The exact-spelling branch (`existing = repo.get_by_target(typed_target, "path"); if existing: repo.update_target(...); return existing`) re-points the typed row but never deletes other alias rows of the same file — the collapse loop only runs in the normalized-key branch below. With legacy rows under spellings A and B of one file, re-adding via spelling A leaves B in place forever: `context list` shows a stale duplicate, `prune` keeps it (the document exists), and the duplicate is only shadowed (not removed) in search attachment. The just-updated row wins the `ORDER BY updated_at` dict-later-wins race in `attach_path_contexts`, so no wrong content surfaces, but the merge invariant the function promises is violated.
**Fix:** Collapse duplicates in the exact branch too:

```python
existing = repo.get_by_target(typed_target, "path")
if existing:
    if repo.update_target(existing.id, actual_target):
        for dup in repo.list_by_type("path"):
            if dup.id != existing.id and normalize_path(dup.path) == actual_target:
                repo.delete(dup.id)
    return existing
```

## Info

### IN-01: Dimension-mismatch error message points users at `sif cleanup`, which cannot fix the problem

**File:** `src/sif/database/schema.py:337-338`
**Issue:** The RuntimeError text says "Rebuild the index with 'sif cleanup' or delete the database file." `cleanup_cmd` (`main.py:158-195`) only deletes orphaned chunks/embeddings and expired cache rows — it never recreates or resizes the vec0 table, so the mismatch persists and the user is sent in a circle. Only deleting the DB file (and re-indexing/re-embedding) actually resolves it.
**Fix:** Reword to actionable guidance, e.g. "Delete the database file (or drop `document_embeddings`) and re-run 'sif index update && sif index embed' with the new model."

### IN-02: Dead `DEFAULT_INDEX_PATH` constant that also disagrees with the real default

**File:** `src/sif/cli/main.py:24`
**Issue:** `DEFAULT_INDEX_PATH = Path.home() / ".local" / "share" / "sif" / "sif.db"` is referenced nowhere (the actual `--index` default comes from `_get_default_db_path()` → `Settings.get_db_path()`, which on macOS resolves to `~/Library/Application Support/sif/sif.db` per platformdirs). The constant is dead code and, if ever copied, would encode the wrong Linux-only path on other platforms.
**Fix:** Delete the constant (or define it as `str(get_settings().get_db_path())` if a module-level fallback is ever needed).

### IN-03: Unused module logger in `cli/main.py`

**File:** `src/sif/cli/main.py:20`
**Issue:** `logger = get_logger(__name__)` is assigned and never used in this module (error paths use `console.print` / `ClickException`). Ruff does not flag it, but it is dead per the module's actual behavior.
**Fix:** Remove the assignment, or route the `status`/`cleanup` exception paths through `logger.exception(...)` before re-raising as `ClickException` so failures land in the log, not just the terminal.

### IN-04: `test_status_respects_env_var` does not exercise the env var

**File:** `tests/unit/cli/test_status.py:49-79`
**Issue:** The test passes `env={"SIF_DB_PATH": "/tmp/test-sif.db"}` to CliRunner but immediately patches `sif.cli.main.get_settings` with a MagicMock whose `get_db_path` returns the asserted path — the env var never flows through real Settings, so the test asserts nothing about `SIF_DB_PATH` and is a near-duplicate of `test_status_uses_settings_db_path`. Any regression that stops honoring the env var (e.g. dropping the env prefix) would still pass.
**Fix:** Use real settings with cache hygiene, as `test_main.py` already models:

```python
monkeypatch.setenv("SIF_DB_PATH", "/tmp/test-sif.db")
get_settings.cache_clear()
try:
    with patch("sif.cli.main.Database") as mock_db_cls:
        ...
        assert str(mock_db_cls.call_args[0][0]) == "/tmp/test-sif.db"
finally:
    get_settings.cache_clear()
```

### IN-05: Output cascade and table rendering triplicated across the three search commands

**File:** `src/sif/cli/commands/search.py:229-303, 403-443, 600-678`
**Issue:** The ~40-line dispatch (`--files/--json/--csv/--md/--xml`/table) and the Rich table construction are copy-pasted three times with only cosmetic differences (title, snippet column). CR-01 had to be fixed in principle at 9 distinct sites for exactly this reason — the snippet `escape()` exists in two of three tables because the blocks drifted. The redundant `quiet = quiet or ctx.obj.get("quiet", False)` re-read at lines 230, 403, 601 (already computed at 189, 337, 500) is the same drift symptom.
**Fix:** Extract a shared `_render_results(results, *, query, title_prefix, mode_flags, has_snippet_column)` helper used by all three commands; the per-command body collapses to option plumbing.

---

_Reviewed: 2026-11-06T06:46:04Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
