---
gsd_state_version: "1.0"
milestone: v1.0
current_plan: Not started
status: executing
stopped_at: Phase 10.1 complete — all phases complete
last_updated: "2026-11-06T14:05:00.000Z"
state_head: e11f28a3805fb619a2e3577ab39ae3412c7ec905
progress:
  total_phases: 11
  completed_phases: 9
  total_plans: 68
  completed_plans: 68
  percent: 82
milestone_name: milestone
current_phase: 10
current_phase_name: "Address tech debt: path normalization + review findings CR-01/CR-02/WR-01 (INSERTED)"
---

# DocSift — Project State

## Project Reference

- **Name:** DocSift
- **Core Value:** 用户可以在自己的笔记和文档库中，用自然语言快速、准确地找到需要的信息——无论关键词是否匹配。
- **Current Focus:** Milestone v1.0 complete (all 11 phases; 10.1 verification regenerated 2026-11-06, 16/16, fresh fingerprint) — ready for milestone close/archive.
- **Tech Stack:** Python 3.10+, SQLite (FTS5 + sqlite-vec), Click, Pydantic, sentence-transformers, llama-cpp-python

## Current Position

Current Plan: Not started
Total Plans in Phase: 4

- **Phases:** 11/11 complete (01–10.1); milestone v1.0 roadmap-complete
- **Plans:** 68/68 complete
- **Status:** Phase 10.1 re-verified 2026-11-06 (stale-verification regeneration, fresh fingerprint, 16/16; gates: validation 10/10, security 12/12 closed, review 0c/0w/4i, regression 1011 @ 96.22%) — milestone v1.0 ready to close
- **Progress Bar:** `[████████████████████] 68/68 plans`
- **Coverage baseline:** 96.22% (5375 statements, 203 missed); 1011 passed, 0 failed

Phase 10-01 deleted the approved dead-code cluster; 10-02/10-03 expanded CLI and reranker coverage; 10-04 closed the real-SQLite database layer; 10-05 covered core services, downloader, and utilities; 10-06 covered indexing and MCP behavior.

## Phase History

| Phase | Date Started | Date Completed | Outcome |
|-------|--------------|----------------|---------|
| 01–04 — Foundation / CLI / Embedding / Pipeline | 2026-04-14 | 2026-04-17 | All 23 plans passed across four phases; trustworthy core, full CLI surface, configurable embeddings, complete search pipeline. |
| 05 — Agent Context Experience | 2026-04-18 | 2026-09-07 | 9/9 plans passed incl. 05-08 read-side + 05-09 write/prune normalization gap closures. Qwen3 models default. |
| 06 — Documentation Audit & Refresh | 2026-04-18 | 2026-04-18 | All 7 plans passed. Auto-generated CLI/config references, docs code block validator (12 tests), Makefile target, GitHub Actions CI workflow. |
| 07 — CLI Claude Skill | 2026-04-20 | 2026-05-30 | 2/2 plans passed. sif-search and sif-get skills created, symlinked to ~/.claude/skills/. |
| 08 — Project rename from DocSift to SIF | 2026-04-27 | 2026-04-27 | 8/8 plans passed. Complete rename of package, CLI, env vars, docs, tests, and skills. |
| 09 — MCP Server Implementation | 2026-05-12 | 2026-05-12 | 6/6 plans passed. Unified MCP package, SearchBackend, 4 tool handlers, stdio/HTTP transports, integration tests. 86% MCP coverage. |

## Performance Metrics

- **Requirements mapped:** 31/31 v1 + 7 DOC requirements
- **Phases defined:** 10
- **Tests passing:** 1011 passed, 0 failed (post 10.1 + phase-10 regeneration, fail_under=90 active)
- **Known blockers:** 0

**Per-Plan Metrics:**

| Plan | Duration | Tasks | Files |
|------|----------|-------|-------|
| Phase 05 P08 | 17min | 2 tasks | 9 files |
| Phase 05 P09 | 12min | 2 tasks | 5 files |
| Phase 10 P01 | 6min | 2 tasks | 5 files |
| Phase 10 P02 | 13min | 3 tasks | 3 files |
| Phase 10 P03 | 19min | 2 tasks | 4 files |
| Phase 10 P04 | 30min | 3 tasks | 10 files |
| Phase 10 P05 | 11min | 3 tasks | 12 files |
| Phase 10 P06 | 20min | 3 tasks | 9 files |
| Phase 10 P07 | 198s | 2 tasks | 1 files |
| Phase 10.1 P01 | 13min | 2 tasks | 6 files |
| Phase 10.1 P02 | 9min | 2 tasks | 2 files |
| Phase 10.1 P03 | 13min | 3 tasks | 2 files |
| Phase 10.1 P04 | 16min | 3 tasks | 8 files |
| Phase 05 P10 | 8min | 3 tasks | 2 files |
| Phase 05 P11 | 12min | 2 tasks | 2 files |
| Phase 05 P12 | 8min | 2 tasks | 2 files |

## Accumulated Context

### Decisions

- ✓ D-01: FTS5 synchronization uses SQLite triggers on external content tables
- ✓ D-02: `sqlite_repository.py` deleted, all access consolidated into `repositories.py`
- ✓ D-03: Vector search fails fast with `RuntimeError` when sqlite-vec is unavailable
- ✓ D-04: MCP server uses connection-per-request via `DatabaseConnection`
- ✓ D-05: Heavy ML libraries remain optional extras in `pyproject.toml`
- [Phase 03 gap closure]: Vector store idempotency = delete-before-insert in the re-chunk transaction + exact chunk-id-set skip; `--force` re-embeds all (G-03-3)
- [Phase 03 gap closure]: embed_cmd uses one transaction per collection; failure report raised outside transactions (CR-02)
- [Phase 03 gap closure]: Remote dimension is probe-free at load; dim cache keyed `base_url::model_name` (WR-02/03-07)
- [Phase 03 gap closure]: Text egress strictly opt-in — OpenAIEmbedder reachable only via explicit `model_type=openai` (P-1, UAT-verified by egress audit)
- [Phase 09]: Unified `src/sif/mcp/` package replacing dual legacy/refactored implementations
- [Phase 09]: ToolHandler ABC pattern with async `handle(params, backend)` signature
- [Phase 09]: SearchBackend with `asyncio.to_thread()` wrapper over sync sqlite3
- [Phase 09]: Streamable HTTP (2025-11-25) — single `/mcp` endpoint, POST/GET, session-aware
- [Phase 09]: CORS defaults non-wildcard: `["http://localhost:3000", "http://127.0.0.1:3000"]`
- [Phase 02]: Mock index_path.exists on the mock object rather than patching Path.exists in ls.py, since ls.py does not import Path directly
- [Phase 02-cli-core-completion]: D-01 priority preserved: comma-separated detection takes precedence over glob detection in multi-get
- [Phase 02-cli-core-completion]: Refactored pull_cmd into helper functions to keep mccabe complexity under 10
- [Phase 02-cli-core-completion]: Used module-level optional imports with None fallback so patch targets exist for tests
- [Phase 04]: Mock optional dependencies (`llama_cpp`, `sentence_transformers`) via `sys.modules` injection before import in tests
- [Phase 04]: Patch `llama_cpp.Llama` and `sentence_transformers.CrossEncoder` at module level, not inside `docsift.search.rerank`
- [Phase 04]: BM25Searcher tests use MagicMock sqlite3 connections with `fetchall.return_value` for row data
- [Phase 04]: `include_highlights=False` required in basic BM25Searcher tests to avoid extra mock DB calls
- [Phase 05-gap-closure]: Used callable default for `--index` option (Click supports callable defaults) to allow dynamic resolution via Settings
- [Phase 05-gap-closure]: Normalized paths with `os.path.realpath()` in all three searchers due to macOS `/tmp` → `/private/tmp` resolution
- [Phase 05-model-update]: Default embedding model switched from `all-MiniLM-L6-v2` (384 dim) to `Qwen/Qwen3-Embedding-0.6B` (1024 dim)
- [Phase 05-model-update]: Default reranker switched from `cross-encoder/ms-marco-MiniLM-L-6-v2` to `Qwen/Qwen3-Reranker-0.6B` (transformers backend)
- [Phase 05-model-update]: Added `modelscope` model_type to `EmbeddingConfig.ModelType` and `_create_modelscope_model` to factory
- [Phase 05-model-update]: Added `Qwen3Reranker` class for transformers-based reranking with yes/no logits scoring
- [Phase 06-discuss]: CLI reference auto-generated via Python script traversing Click command tree (`scripts/generate_cli_ref.py`)
- [Phase 06-discuss]: Code block validation: fence-tag based classification (bash → execute, json/python → syntax check, text → skip)
- [Phase 06-discuss]: Blacklist for long-running commands (mcp start, pip install, etc.) in docs tests
- [Phase 06-discuss]: Docs tests use pytest fixture with temp DB + minimal test data, CliRunner primary + subprocess secondary
- [Phase 06-discuss]: Technical docs validated via AST parsing: extract public API from code, verify against documented names
- [Phase 06-discuss]: Architecture diagram strategy: keep ASCII in README (manual), generate Mermaid in architecture.md (scripted)
- [Phase 09]: [Phase 03-07]: OpenAI-compatible endpoints addressed via OpenAI(api_key, base_url) — SDK appends /embeddings; api_base=None uses SDK default (D-04)
- [Phase 09]: [Phase 03-07]: Dimension source of truth is the API — one minimal probe cached per model to openai_dim_cache.json with 7-day TTL; corrupt/missing cache degrades to probe, never crashes load (D-05)
- [Phase 09]: [Phase 03-07]: Configured embedding_dim disagreeing with API-detected dimension fails fast at load naming both values + SIF_EMBEDDING_DIM (extends D-09 fail-fast philosophy)
- [Phase 09]: [Phase 03-07]: api_key passes only to the OpenAI client constructor — never logged, interpolated, or embedded in exceptions (threat T-03-01)
- [Phase 09]: [Phase 03-07]: Factory honest signatures -> Embedder / **kwargs: Any completed the refactor plan 03-02 promised (03-REVIEW WR-01/WR-02)
- [Phase 04 UAT]: Shared stem-tolerant term matcher (src/sif/search/term_match.py): word-boundary + light-stem for ASCII, substring + per-char fallback for CJK — used by both SmartSnippetExtractor and BM25 highlights
- [Phase 04 UAT]: Snippets are line-aware: windows center on the matched line (heading/table row/code line), structural lines never anchor
- [Phase 04 UAT]: Reranker model dirs resolve by config qualification (config.json with model_type, root before aux subdirs like Qwen3-Reranker's 1_LogitScore)
- [Phase 04 UAT]: LlamaCppEmbedder owns generation (create_completion) + shape-aware embed (unwrap list-of-embeddings, mean-pool token-level); HyDE reachable end-to-end
- [Phase 04 UAT deferred]: embedding cache bucket key omits model_path — switching GGUF files under one model_name cross-pollutes cache; include path identity in _cache_model_id
- [Phase 03]: [Phase 03-08] Idempotent embed via delete-before-insert: chunk_repo.delete_by_document -> VectorSearcher.delete_embeddings_by_document -> add_embeddings_batch in one transaction; probe-free dimension from get_model_info() (isinstance-guarded probe fallback)
- [Phase 03]: [Phase 03-08] --force honored via exact chunk-id-set equality: _needs_embedding(live, embedded, force) module-level helper; default run skips complete documents with zero embed calls, partial/orphaned states self-heal
- [Phase 03]: [Phase 03-08] VectorSearcher construction failure in embed_cmd surfaces as click.ClickException (D-03 fail-fast extended to the embed path; never swallowed into failed_collections)
- [Phase 04]: [Phase 04-06]: Pipeline snippet content fetch is transient — fetched text feeds extraction only, never written into SearchResult.content (CLI-07 --full contract preserved)
- [Phase 04]: [Phase 04-06]: Snippet table cells wrapped in rich.markup.escape so document bracket sequences render literally (threat T-04-06-02 mitigated)
- [Phase 04]: [Phase 04-06]: _display_snippet guards snippet and highlights with getattr, falling back to the first BM25 highlight when no snippet exists
- [Phase 05]: 05-08: read-side re-normalization replaces the raw-string SQL pre-filter in context attachment — one constant-SQL batch query of all path contexts, both sides normalized in Python via normalize_path (realpath is not invertible, so no SQL path pre-filter can ever match a verbatim legacy row; D-06 batch shape preserved)
- [Phase 05]: 05-08: legacy verbatim context rows match on read — no contexts-table backfill migration; context_description is set only on match so RRF/rerank-carried descriptions are never clobbered; ORDER BY updated_at gives deterministic newest-wins for duplicate-normalizing targets
- [Phase 05]: 05-09: context add path stores normalize_path(target) canonical form with dual-form upsert — legacy verbatim rows are re-pointed via new ContextRepository.update_target() on explicit re-add; no bulk backfill migration ever runs (re-normalize-on-read + merge-on-re-add closes WR-02/CTX-01)
- [Phase 05]: 05-09: delete_orphaned_paths compares normalize_path on both sides in a Python set — SQL cannot call realpath so the raw-string NOT IN comparison is gone entirely; count semantics and D-12/D-13 explicit-command contract unchanged (closes CR-02/CTX-02)
- [Phase 10]: 10-01: Applied D-01 exactly, deleting the approved dead-code cluster while preserving live CLI imports; measured post-deletion coverage at 81.48% (5320 statements, 985 missed).
- [Phase 10]: 10-01: Kept pyproject.toml free of fail_under and coverage exclusions under D-04; final gate remains reserved for plan 10-07.
- [Phase 10]: 10-02: D-06 isolated, both-order, and full-suite probes were green; no speculative repair or production change was made.
- [Phase 10]: 10-02: Real-temp-DB CLI tests raised TOTAL coverage from 81.48% to 85.34%; collection 99.15%, main 86.99%, get 100%.
- [Phase 10]: 10-03: Used real torch tensor math with constructor/downloader mocks for deterministic Qwen3 yes/no scoring; scoped ML module injection under D-07.
- [Phase 10]: 10-03: Escaped XML query attributes and result fields so machine output strict-parses markup-sensitive content; search command reached 99.44% coverage.
- [Phase 10]: 10-04: Real SQLite exposed and repaired stale external-content FTS delete triggers, lazy stats initialization, and multi-statement migration execution; repositories/schema/database/cache reached 100% and migrations 92%.
- [Phase 10]: 10-05: Used real domain entities with repository Protocol doubles and scoped ModelScope/process-state isolation; all seven target files reached 100%.
- [Phase 10]: 10-05: Behavior tests exposed and repaired custom logging formatter and indeterminate Rich progress defects; TOTAL coverage reached 93.48%.
- [Phase 10]: 10-06: Real-file Unicode parsing, exact code-point chunk boundaries, and isolated MCP protocol tests raised TOTAL coverage to 96.16%.
- [Phase 10]: 10-06: Behavior tests repaired fixed-size chunker forward progress and post-insertion MCP session LRU bounds.
- [Phase 10]: 10-07: Zero long-tail tests required; Wave-2 combined TOTAL already 96.16% (>=90%). D-05 did not trigger; no candidate test file was modified.
- [Phase 10]: 10-07: Landed [tool.coverage.report] fail_under=90 LAST per D-04/Pattern 6; no exclude_lines/exclude_also/--cov-branch, no business-logic pragma. Canonical suite green under active gate (958 passed, 96.16%).
- [Phase 10.1]: DEBT-PN lookup order (OQ2): normalized-only for exact-path lookups; ID-first and bare-filename stay raw; globs raw-first-then-normalized
- [Phase 10.1]: get/multi-get own Database lifecycle via with Database(index_path) (WR-01, 2 sites); nested with db.connection kept for commit sequencing
- [Phase 10.1]: DEBT-PN-DOC lands in docstrings + make docs-generate output + sif-get skill note; no separate prose page (OQ3/A5)
- [Phase 10.1]: 10.1-02: CR-01 closed via generalized _fts_trigger_is_legacy detector (direct-UPDATE FND-06 + direct-DELETE forms) migrating all four FTS sync triggers on create_all()
- [Phase 10.1]: 10.1-02 OQ1: detection-gated FTS 'rebuild' purges entries orphaned by past broken deletes; gate is legacy detection alone, never needs_rebuild_*; fresh/migrated DBs pay nothing
- [Phase 10.1]: 10.1-02: migration logic extracted to _drop_legacy_fts_triggers returning legacy-delete booleans (ruff C901 mccabe-10 cap)
- [Phase 10.1]: 10.1-03: CR-02 closed — sanitizer is the XML 1.0 Char production complement transliterated (strip #x00-#x08/#x0B/#x0C/#x0E-#x1F/surrogates/#xFFFE-#xFFFF; keep tab/LF/CR; never strip #x7F-#x9F), applied BEFORE xml_escape/quoteattr which keep owning <>&'"
- [Phase 10.1]: 10.1-03: WR-01 search.py — with Database(index_path) covers each command body from init_schema onward; all nine nested with db.connection: transaction blocks preserved
- [Phase 10.1]: 10.1-03: closure doubles patch the import SOURCE for function-local imports — vsearch_cmd binds Database at call time, so its TrackingDatabase patches sif.database.database.Database; and real-Database doubles need settings.embedding_dim as a real int (init_schema resolves get_settings lazily per call)
- [Phase 10.1]: 10.1-04: WR-01 closed for six CLI modules (21 sites) — with Database(index_path) ownership wraps each command body from init_schema onward; nested with db.connection/transaction blocks preserved verbatim (57→13 ResourceWarnings, remainder test-side)
- [Phase 10.1]: 10.1-04: main.py ownership scopes sit INSIDE the existing try/except — exceptions close the Database via __exit__ before the ClickException handler runs
- [Phase 10.1]: 10.1-04: lifecycle harness asserts non-vacuous closure (every test asserts >=1 TrackingDatabase captured) and covers index update (not index status, which delegates to main's status_cmd and would not exercise index.py's scope)
- [Phase 05]: 05-10: truth-21 duplicate collapse centralized in _collapse_duplicate_path_rows — shared by exact-match branch, normalized branch, and upsert-hit path; exact-match branch gains the same landed-guard (update_target True before any deletion) as the normalized branch (T-05-16)
- [Phase 05]: 05-10: CR-02 closed — context list wraps all three Rich table cells in rich.markup.escape AFTER truncation so the 50-char display cap applies to raw text; display-only, stored bytes untouched (mirrors 04-06 snippet precedent)
- [Phase 05]: 05-11: CR-01 closed — rich.markup.escape at all 12 display sites (3 titles, 3 title cells, 3 collection cells, 3 content appends, 2 explain prints); display-layer only, machine outputs byte-unchanged
- [Phase 05]: 05-11: escape-after-truncation ordering (truncate raw text, then escape the whole displayed expression incl. ellipsis) — mirrors the 05-10 context-list precedent; tests renamed to *_renders_markup_literally so -k markup_literal selects all five
- [Phase 05]: 05-12: CR-03 closed — rich.markup.escape wraps display_target at both context add confirmation prints and context_id at the remove print; display-layer only, print placement inside the transaction and stored bytes unchanged (mirrors 05-10/05-11 precedents; 05-10-P3 now HOLDS at all three sites) — Bracket-named targets were permanently unaddable because the MarkupError from the confirmation print rolled back the open transaction; escaping removes the raising path while both write branches stay inside with db.transaction()

### Roadmap Evolution

- Later-added phases: 07 Claude skills (2026-04-20), 08 rename DocSift→SIF (2026-04-27), 09 MCP server (2026-05-08)
- Phase 10 added: Raise pytest coverage to 90% (2026-11-05; baseline 78% / 5587 stmts / 1220 missed — lowest: cli/config.py 0%, formatters 29%, collection 44%)
- Phase 10.1 inserted after Phase 10: Address tech debt: path normalization + review findings CR-01/CR-02/WR-01 (URGENT)

### TODOs

- [x] Plan Phase 06 documentation audit and refresh — 7 plans created and verified
- [x] Phase 7: CLI Claude Skill — sif-search and sif-get skills created, symlinked, and committed
- [ ] (Backlog) Phase 8: LLM-based query expansion — model tested (Qwen3.5-2B), awaiting v1.0 ship
- [ ] (Backlog) Phase 10 regen code review: 10 warnings open (WR-01..WR-10, 0 critical) — ledger in 10-REVIEW-DISPOSITION.md; candidates for a future debt phase (precedent: 10.1 arose from 10's original review)
- [ ] (Backlog) Phase 10.1 regen code review: 4 info findings open (IN-10..IN-13: stale test-count claims in docs/testing.md, invalid bare `sif search` in DESIGN.md, discarded `_collapse_duplicate_path_rows` return, duplicated test helpers) — ledger in 10.1-REVIEW-DISPOSITION.md

### Blockers

- None

### Quick Tasks Completed

| # | Description | Date | Commit | Directory |
|---|-------------|------|--------|-----------|
| 260905-hc3 | Fix G-04-1 snippet relevance: markdown line-aware SmartSnippetExtractor windows; stem-tolerant word-boundary term matching shared with BM25 highlights | 2026-09-05 | 89a8a5e | [260905-hc3-fix-g-04-1-snippet-relevance-markdown-li](./quick/260905-hc3-fix-g-04-1-snippet-relevance-markdown-li/) |
| 260905-kmv | Fix G-04-2 reranker load crash: model-dir resolution prefers real model config over aux subdirs; CLI ClickException on reranker failure | 2026-09-05 | 0831f41 | [260905-kmv-fix-g-04-2-reranker-load-crash-model-dir](./quick/260905-kmv-fix-g-04-2-reranker-load-crash-model-dir/) |
| 260905-sxc | Fix G-04-3 HyDE unreachable: add create_completion to LlamaCppEmbedder wrapping llama_cpp completion with openai-style return shape | 2026-09-05 | 67c9ecf | [260905-sxc-fix-g-04-3-hyde-unreachable-add-create-c](./quick/260905-sxc-fix-g-04-3-hyde-unreachable-add-create-c/) |
| 260905-tax | Fix G-04-4 GGUF embed shape: unwrap llama_cpp list-of-embeddings, mean-pool token-level output before normalization | 2026-09-05 | 958262b | [260905-tax-fix-g-04-4-gguf-embed-shape-unwrap-llama](./quick/260905-tax-fix-g-04-4-gguf-embed-shape-unwrap-llama/) |
| 260910-kps | Fix CLI machine-output corruption: emit --json/--csv/--md/--xml/--files via click.echo so Rich neither word-wraps nor markup-interprets; regression tests under forced COLUMNS=80 | 2026-09-10 | 4d4bb02 | [260910-kps-fix-json-output-emit-via-click-echo-no-w](./quick/260910-kps-fix-json-output-emit-via-click-echo-no-w/) |
| 260914-g63 | Audit follow-up: fix deferred-items doc formats (05 resolved, 03 split), add missing sqlite3 import in cli/main.py, re-file mypy typing debt as open deferred item | 2026-09-14 | ae2cb6d | [260914-g63-audit-follow-up-fix-deferred-items-doc-f](./quick/260914-g63-audit-follow-up-fix-deferred-items-doc-f/) |
| 260914-v5f | Fix exclude-all collection leak (audit BLOCKER 1): [] filters everything / None unfiltered sentinel guards in BM25+Vector searchers; 3 RED regression tests + 5 controls, suite 675 green | 2026-09-14 | b7381d6 | [260914-v5f-fix-exclude-all-collection-leak-empty-co](./quick/260914-v5f-fix-exclude-all-collection-leak-empty-co/) |
| 260914-vyr | Rename distribution docsif→sif (audit BLOCKER 2): pyproject name/script/keywords, README installs, uv.lock root entry; new mcp/http extras (uvicorn only) so sif[mcp]/sif[http]/sif[embed] hints resolve; suite 675 green | 2026-09-14 | 4657ea8 | [260914-vyr-rename-distribution-docsif-to-sif-pyproj](./quick/260914-vyr-rename-distribution-docsif-to-sif-pyproj/) |
| 260914-wxv | Fix stale command references (DOC-02/04): 5 CLI 'sif update' hints → real index-group commands, development.md 2 blocks + both live skills corrected; --help existence proofs + live hint verification, suite 675 green | 2026-09-14 | 484b82c | [260914-wxv-fix-stale-command-references-nonexistent](./quick/260914-wxv-fix-stale-command-references-nonexistent/) |
| 260917-bo2 | Typing debt batch 1: search/rerank.py mypy strict-clean (22→0; TYPE_CHECKING imports, Optional annotations, narrowing asserts, 4 stale ignores removed) — zero behavior change, suite 676 green | 2026-09-17 | 1c1bec2 | [260917-bo2-typing-debt-batch-1-clear-search-rerank-](./quick/260917-bo2-typing-debt-batch-1-clear-search-rerank-/) |
| 260917-dkf | Typing debt batch 2: watcher.py/manager.py/embedder.py mypy-clean (39→0; EmbeddingConfig Field defaults → keyword syntax, typed locals, os.fsdecode) — full-project 117→78, zero behavior change, suite 676 green | 2026-09-17 | e39d092 | [260917-dkf-typing-debt-batch-2-clear-indexing-watch](./quick/260917-dkf-typing-debt-batch-2-clear-indexing-watch/) |
| 260917-kav | Typing debt batch 3: mcp/handlers.py + cli/commands/search.py + database/connection.py mypy-clean (32→0; ClassVar base attrs, generics, walrus narrowing, SearchPipeline reranker union widened) — full-project 78→46, zero behavior change, suite 676 green | 2026-09-17 | 4f24682 | [260917-kav-typing-debt-batch-3-clear-mcp-handlers-p](./quick/260917-kav-typing-debt-batch-3-clear-mcp-handlers-p/) |
| 261105-eev | Document embedding hardware/device selection (MPS/GPU/CPU): generator Device Selection note under Embedding Model Settings + hardware-acceleration notes in installation.md; suite 676 green | 2026-11-05 | e3f7e2d | [261105-eev-document-embedding-hardware-device-selec](./quick/261105-eev-document-embedding-hardware-device-selec/) |
| 261105-g1u | Fix 05-REVIEW WR-03/WR-09: guard context add/remove against missing index (no silent empty-DB creation); validate reranker_model_type + ClickException surface for bad SIF_RERANKER_MODEL_TYPE | 2026-11-05 | b8a81e1 | [261105-g1u-fix-05-review-wr-03-and-wr-09-context-ad](./quick/261105-g1u-fix-05-review-wr-03-and-wr-09-context-ad/) |
| 261105-wbj | 修复 embed 完整性检查 O(N²) 性能 bug:vector.py 新增 get_all_embedded_chunk_ids() 批量预取,index.py 主循环改查 dict(vec0 全表扫 4 万次 → 一次全量) | 2026-11-05 | 16b7b25 | [261105-wbj-embed-o-n-bug-src-sif-search-vector-py-2](./quick/261105-wbj-embed-o-n-bug-src-sif-search-vector-py-2/) |
| 261105-wwz | 排查搜索路径 vec0 metadata 过滤同类问题:结论无需改动——KNN 查询无 metadata WHERE,EQP 实测虚拟表扫一次且最外层,计时平坦(0.24-0.27ms),每用户查询调用一次;仅加 7 行审计注释(vector.py:79-86) | 2026-11-06 | 751a0c3 | [261105-wwz-vec0-metadata-src-sif-search-vector-py-8](./quick/261105-wwz-vec0-metadata-src-sif-search-vector-py-8/) |
| 261106-u7d | Typing debt batch 4: clear all 17 ledgered ty diagnostics (assert-narrowing, Protocol, cast; mcp.py stderr console replaces latent Console.print TypeError) + drop residual mypy refs — ty sole type checker; 17→0, suite 1011 @ 96.21% | 2026-11-06 | 3fc5908 | [261106-u7d-typing-debt-batch-4-clear-all-17-ledgere](./quick/261106-u7d-typing-debt-batch-4-clear-all-17-ledgere/) |

### Overrides

- [2026-09-03] Phase 03 decision-coverage gate override (user-approved): D-06/D-07/D-08/D-10 accepted as covered-by-legacy — implemented and behaviorally verified per 03-VERIFICATION.md; legacy plans 03-01…03-06 predate D-ID citation and are read-only in gap-closure mode. Verify-phase should re-surface this.

## Session Continuity

**Last session:** 2026-11-06 (quick task 261106-u7d)
**Stopped at:** Quick task 261106-u7d complete — ty typing-debt pass cleared all 17 ledgered diagnostics (ty exits 0) and dropped residual mypy references; full suite green (ruff/format clean, pytest 1011 @ 96.21%, mypy grep empty)
**Resume file:** None

- **Last action:** Quick task 261106-u7d (typing debt batch 4): commits e0d9596 + 3fc5908; 10.1 deferred-items.md item 1 flipped to resolved.
- **Next expected action:** `/gsd-complete-milestone v1.0` — all quality gates green (ty, ruff, format, pytest).
