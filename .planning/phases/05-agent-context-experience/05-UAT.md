---
status: complete
phase: 05-agent-context-experience
source: 05-01-SUMMARY.md, 05-02-SUMMARY.md, 05-03-SUMMARY.md, 05-04-SUMMARY.md
started: "2026-04-18T02:50:00Z"
updated: "2026-04-18T03:05:00Z"
---

## Current Test

[testing complete]

## Tests

### 1. Cold Start Smoke Test
expected: Fresh database initializes with unified contexts table. Old databases with path_contexts table migrate automatically to contexts table on first access. No errors during startup or migration.
result: pass

### 2. Add Path Context
expected: Running `docsift context add path /notes/work "Work-related notes and documentation"` creates a path context. The command succeeds with confirmation output.
result: pass

### 3. Add Collection Context
expected: Running `docsift context add collection my-collection "Personal knowledge base"` creates a collection context, resolving the collection by name. The command succeeds with confirmation output.
result: issue
reported: "Context added message OK, but context_type stored as 'path' instead of 'collection' in DB. Root cause: ContextRepository.create() hardcodes context_type='path' in INSERT SQL (repositories.py:351), and context_add() never passes the type argument to repo.create()."
severity: major

### 4. Add Global Context
expected: Running `docsift context add global global "General context for all searches"` creates a global context. The command succeeds with confirmation output.
result: issue
reported: "Context added message OK, but context_type stored as 'path' instead of 'global' in DB. Same root cause as Test 3."
severity: major

### 5. List Contexts
expected: Running `docsift context list` displays all contexts in a table with columns for Type, Target, and Content. Path, collection, and global contexts all appear.
result: issue
reported: "Table shows all contexts but every row displays Type='path'. Two bugs: (1) all contexts stored with wrong type (see Tests 3-4), (2) display code hardcodes 'path' in table.add_row() without reading ctx_item.context_type (context.py:132)."
severity: major

### 6. List Contexts with Type Filter
expected: Running `docsift context list --type path` shows only path contexts. Running `docsift context list --type collection` shows only collection contexts. The filter works correctly.
result: issue
reported: "--type filter correctly calls repo.list_by_type(), but since all rows have context_type='path', filtering by collection/global returns nothing. Filter logic itself works; data is wrong."
severity: major

### 7. Remove Context
expected: Running `docsift context rm <context-uuid>` removes the specified context. Subsequent `context list` no longer shows it. The `rm` alias works identically to `remove`.
result: pass

### 8. Prune Orphaned Path Contexts
expected: Running `docsift context prune` removes path contexts whose target paths no longer exist in the documents table. The command reports how many were removed.
result: pass

### 9. BM25 Search with Context Description
expected: When a path context exists for a document path, running `docsift search --mode bm25 "query"` shows results that include the context description alongside the result.
result: issue
reported: "Search returns document correctly but context_description is null. Root cause: macOS path normalization mismatch. Document stored as /private/tmp/... (resolved), context stored as /tmp/... (user-provided). _attach_contexts() does literal string match on target_id = path, which fails."
severity: medium

### 10. Hybrid Search with Context Description
expected: When a path context exists for a document path, running `docsift search --mode hybrid "query"` shows results that include the context description, preserved through RRF fusion and any reranking.
result: blocked
blocked_by: third-party
reason: "sentence_transformers package not installed. Hybrid search fails with 'Embedding backend not installed: No module named sentence_transformers'. CLI loads embedding model before calling pipeline.search(), so fallback never reached."

### 11. Status Command Shows Contexts
expected: Running `docsift status` displays "Contexts" count (not "Path Contexts"), reflecting the unified contexts table.
result: issue
reported: "Displays 'Contexts' label correctly (not 'Path Contexts'), but ignores DOCSIFT_DB_PATH env var and reports default database path/collections. CLI uses --index flag instead of Pydantic Settings db_path."
severity: medium

## Summary

total: 11
passed: 4
issues: 6
pending: 0
skipped: 0
blocked: 1

## Gaps

- truth: "Collection context is stored with correct context_type='collection' in DB"
  status: failed
  reason: "User reported: Context added message OK, but context_type stored as 'path' instead of 'collection' in DB. Root cause: ContextRepository.create() hardcodes context_type='path' in INSERT SQL (repositories.py:351), and context_add() never passes the type argument to repo.create()."
  severity: major
  test: 3
  root_cause: "ContextRepository.create() hardcodes context_type='path'. context_add() CLI never passes type parameter to repo."
  artifacts:
    - path: "src/docsift/database/repositories.py"
      issue: "INSERT hardcodes context_type='path'"
    - path: "src/docsift/cli/commands/context.py"
      issue: "context_add() does not pass type argument to repo.create()"
  missing:
    - "Pass context_type parameter to ContextRepository.create()"
    - "Use parameterized context_type in INSERT instead of hardcoded 'path'"

- truth: "Global context is stored with correct context_type='global' in DB"
  status: failed
  reason: "User reported: Same root cause as Test 3"
  severity: major
  test: 4
  root_cause: "Same as Test 3: hardcoded context_type='path' in repository, no type passed from CLI"
  artifacts:
    - path: "src/docsift/database/repositories.py"
      issue: "INSERT hardcodes context_type='path'"
    - path: "src/docsift/cli/commands/context.py"
      issue: "context_add() does not pass type argument"
  missing:
    - "Pass context_type parameter to ContextRepository.create()"

- truth: "List contexts displays actual context_type per row"
  status: failed
  reason: "User reported: Table shows all contexts but every row displays Type='path'. Display code hardcodes 'path' in table.add_row() without reading ctx_item.context_type."
  severity: major
  test: 5
  root_cause: "context_list() hardcodes 'path' string in table output instead of reading ctx_item.context_type"
  artifacts:
    - path: "src/docsift/cli/commands/context.py"
      issue: "table.add_row('path', ...) hardcoded instead of ctx_item.context_type"
  missing:
    - "Use ctx_item.context_type or fallback in table.add_row()"

- truth: "BM25 search results include context_description when path context exists"
  status: failed
  reason: "User reported: Search returns document but context_description is null due to macOS path normalization mismatch (/private/tmp vs /tmp)"
  severity: medium
  test: 9
  root_cause: "_attach_contexts() does literal string match on target_id = path. macOS resolves /tmp to /private/tmp for documents but stores user-provided /tmp/... in context target_id."
  artifacts:
    - path: "src/docsift/search/bm25.py"
      issue: "_attach_contexts() literal path match"
    - path: "src/docsift/search/hybrid.py"
      issue: "_attach_contexts() literal path match"
  missing:
    - "Normalize paths before storing context target_id, or use os.path.realpath() in _attach_contexts() comparison"

- truth: "Status command respects DOCSIFT_DB_PATH environment variable"
  status: failed
  reason: "User reported: CLI uses --index flag instead of Pydantic Settings db_path, ignoring DOCSIFT_DB_PATH"
  severity: medium
  test: 11
  root_cause: "CLI main.py defines --index option that overrides Settings-based db_path"
  artifacts:
    - path: "src/docsift/cli/main.py"
      issue: "--index option bypasses Pydantic Settings"
  missing:
    - "Use Settings.get_db_path() as default for --index, or remove --index and let Settings handle env vars"

- truth: "Hybrid search shows results with context_description when embedding backend is unavailable"
  status: blocked
  reason: "Blocked by missing sentence_transformers dependency"
  severity: N/A
  test: 10
  root_cause: "sentence_transformers not installed; CLI fails before reaching HybridSearcher fallback"
  artifacts:
    - path: "src/docsift/cli/commands/search.py"
      issue: "Embedding model loaded before pipeline.search() call"
  missing:
    - "Defer embedding model loading until actually needed, or improve error messaging"
