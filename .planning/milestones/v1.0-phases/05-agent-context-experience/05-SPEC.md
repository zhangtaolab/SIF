# Phase 5: Agent Context Experience — Specification

**Created:** 2026-04-18
**Ambiguity score:** 0.143 (gate: ≤ 0.20)
**Requirements:** 4 locked

## Goal

Users can attach contextual descriptions to paths, collections, and a global scope; these descriptions are automatically included in search results for matching documents.

## Background

The codebase already has a `path_contexts` table (`src/docsift/database/schema.py`), a `PathContext` domain model (`src/docsift/core/models.py`), a `PathContextRepository` (`src/docsift/database/repositories.py`), and a `context add/remove/list` CLI command group (`src/docsift/cli/commands/context.py`). However, the current implementation is **path-only**: the table schema has `path TEXT NOT NULL` and no `context_type` field, so collection-level and global contexts cannot be stored. The `SearchResult` dataclass (`src/docsift/core/models.py:179`) has no field for context descriptions, and none of the search strategies (BM25, Vector, Hybrid) query the `path_contexts` table when building results. There is also no mechanism to clean up orphaned context records when indexed documents are removed.

The `ContextManager` in `src/docsift/core/context.py` defines a more abstract design with a `ContextType` enum (`COLLECTION`, `PATH`, `DOCUMENT`, `GLOBAL`), but no repository or CLI wiring exists for `COLLECTION` or `GLOBAL` types. This phase migrates the concrete storage to a unified `contexts` table and wires context descriptions into search result output.

## Requirements

1. **Unified contexts table migration**: Replace `path_contexts` with a `contexts` table that supports path, collection, and global scopes.
   - Current: `path_contexts` table has `path TEXT NOT NULL, collection_id TEXT, context TEXT`. Only path-level contexts can be stored. No migration mechanism exists.
   - Target: `contexts` table has `id TEXT PRIMARY KEY, target_id TEXT NOT NULL, context_type TEXT NOT NULL, content TEXT NOT NULL, created_at TEXT, updated_at TEXT`. `SchemaManager` migrates existing `path_contexts` data into the new table (setting `context_type='path'`), then drops the old table. Migration is wrapped in a transaction; on failure it rolls back and prints an error message.
   - Acceptance: After running schema init on a database with existing `path_contexts` data, the old table no longer exists, all prior data is present in `contexts` with `context_type='path'`, and a new `idx_contexts_target` index exists on `(target_id, context_type)`.

2. **Context CLI for all types**: Extend the CLI to support adding, listing, and removing path, collection, and global contexts through a unified interface.
   - Current: `context add <path> <text>` creates path contexts only. `context remove <path>` deletes by path. `context list` lists path contexts and supports `--collection` filtering. No `rm` alias exists.
   - Target: `context add <type> <target> <content>` accepts `type` ∈ {path, collection, global}. `context list` supports optional `--type` filtering. `context remove <id>` deletes by context ID. `rm` is registered as an alias for the `remove` subcommand. Collection targets are resolved by collection name; global target is ignored.
   - Acceptance: Unit tests verify that adding a collection context (`context add collection my-coll "desc"`) and a global context (`context add global global "desc"`) succeeds, `context list --type collection` returns only collection contexts, and `docsift context rm <id>` invokes the same handler as `docsift context remove <id>`.

3. **Context descriptions in search results**: Every search result for a document whose path has an associated context description includes that description.
   - Current: `SearchResult` (both `core/models.py` and `models/search.py`) has no field for context descriptions. BM25Searcher, VectorSearcher, and HybridSearcher do not query the contexts table when constructing results.
   - Target: `SearchResult` gains a `context_description: str | None` field. All three search strategies query `contexts` for `context_type='path'` and `target_id=result.path` after retrieving the document list, and populate the field. The full description is included without truncation at the search layer.
   - Acceptance: After adding a path context for `/notes/project.md`, searching for a keyword present in that document via BM25, Vector, and Hybrid returns a `SearchResult` whose `context_description` equals the added description. If no context exists for the path, the field is `None`.

4. **Orphaned context cleanup**: Provide a command to remove path contexts whose target paths no longer exist in the indexed documents table.
   - Current: No cleanup mechanism exists. Deleting or renaming an indexed document leaves its path context as an orphan in the database.
   - Target: `context prune` scans `contexts` where `context_type='path'`, checks whether `target_id` exists in the `documents` table, and deletes records for missing paths. It prints a count of deleted records.
   - Acceptance: After indexing a document, adding a path context for it, removing the document from the index, and running `context prune`, the context record is deleted. Running `context list` afterward does not show it.

## Boundaries

**In scope:**
- Database schema migration: `path_contexts` → unified `contexts` table with `context_type` enum
- `SchemaManager` migration logic (transactional, with rollback on failure)
- CLI command updates: `context add/list/remove` supporting path/collection/global
- `rm` as a CLI alias for `remove`
- `SearchResult` field addition (`context_description`)
- Search strategy updates (BM25, Vector, Hybrid) to query and attach path contexts
- `context prune` command for manual orphaned-context cleanup

**Out of scope:**
- MCP server returning context descriptions in tool responses — Phase 6+ consideration; current MCP tools are unaffected
- Automatic injection of collection/global contexts into `SearchContext.context_string` for query expansion — the existing `context_string` remains caller-controlled
- Interactive or bulk import of contexts from files — exceeds the "minimal CLI" MVP agreed in Round 2
- Semantic relevance filtering for context descriptions — decision locked to "always include the matching path's context"
- Automatic cascade deletion on document removal — default behavior is to preserve contexts; cleanup is explicit via `prune`
- `DOCUMENT` context type — `ContextType.DOCUMENT` exists in the enum but is not wired in this phase

## Constraints

- Migration must be atomic: `SchemaManager` wraps table creation, data migration, and old-table drop in a single SQLite transaction; on failure it rolls back and emits an error message to stderr advising manual migration
- Search layer must not truncate context descriptions: the full `content` is populated into `SearchResult.context_description`; CLI display layers may truncate for readability
- Path context lifecycle defaults to preservation: document deletion or rename does not automatically delete associated contexts; users must run `context prune` explicitly
- `collection` target resolution: when `type=collection`, the CLI resolves the target string against collection names (not collection IDs), consistent with existing collection CLI conventions

## Acceptance Criteria

- [ ] `contexts` table schema includes `target_id`, `context_type`, and `content` columns, with `context_type` constrained to `path`, `collection`, or `global`
- [ ] Existing `path_contexts` data is fully migrated into `contexts` with `context_type='path'`, and the old table is dropped
- [ ] `docsift context add collection my-collection "description"` creates a collection context and returns success
- [ ] `docsift context add global global "description"` creates a global context and returns success
- [ ] `docsift context list --type collection` returns only collection-type contexts
- [ ] `docsift context rm <id>` deletes the context with the given ID (alias behavior verified)
- [ ] BM25 search for a document with a path context returns `SearchResult.context_description` equal to the stored description
- [ ] Vector search for a document with a path context returns `SearchResult.context_description` equal to the stored description
- [ ] Hybrid search for a document with a path context returns `SearchResult.context_description` equal to the stored description
- [ ] `docsift context prune` deletes path contexts whose `target_id` no longer exists in the `documents` table

## Ambiguity Report

| Dimension           | Score | Min   | Status | Notes                        |
|---------------------|-------|-------|--------|------------------------------|
| Goal Clarity        | 0.90  | 0.75  | ✓      |                              |
| Boundary Clarity    | 0.85  | 0.70  | ✓      | Explicit out-of-scope list   |
| Constraint Clarity  | 0.80  | 0.65  | ✓      | Migration and lifecycle rules|
| Acceptance Criteria | 0.82  | 0.70  | ✓      | 10 pass/fail checkboxes      |
| **Ambiguity**       | 0.143 | ≤0.20 | ✓      |                              |

## Interview Log

| Round | Perspective     | Question summary                             | Decision locked                                              |
|-------|-----------------|----------------------------------------------|--------------------------------------------------------------|
| 1     | Researcher      | 现有 context 支持范围？                      | 从 path-only 扩展到 path/collection/global                   |
| 1     | Researcher      | CTX-03 搜索回显的具体行为？                  | 始终附带匹配路径的上下文描述（与 qmd 行为一致）              |
| 1     | Researcher      | CLI `rm` vs `remove` 命名？                  | 保留 `remove`，`rm` 作为别名                                 |
| 2     | Simplifier      | 数据模型迁移策略？                           | 统一迁移到 `contexts` 表                                     |
| 2     | Simplifier      | 如果砍掉 50% 的核心是什么？                  | 全类型支持，但 CLI 最简化                                    |
| 3     | Boundary Keeper | Phase 5 明确不做什么？                       | MCP server 返回上下文描述排除在外                            |
| 4     | Failure Analyst | 迁移失败怎么办？                             | 回滚并提示用户手动迁移                                       |
| 4     | Failure Analyst | 长文本是否截断？                             | 搜索层不截断，由 CLI/调用方决定                              |
| 4     | Failure Analyst | 文档删除时上下文是否级联删除？               | 默认保留，通过 `context prune` 手动清理                      |

---

*Phase: 05-agent-context-experience*
*Spec created: 2026-04-18*
*Next step: /gsd-discuss-phase 5 — implementation decisions (how to build what's specified above)*
