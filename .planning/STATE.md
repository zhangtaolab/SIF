---
gsd_state_version: "1.0"
milestone: v1.0
current_phase: 05
current_phase_name: Agent Context Experience
current_plan: 9
status: verifying
stopped_at: Completed 05-09-PLAN.md
last_updated: "2026-09-07T04:13:46.234Z"
state_head: 2e25ea17aeb9b3e748cd4ba8c3ed9bedbfee14b9
progress:
  total_phases: 9
  completed_phases: 6
  total_plans: 51
  completed_plans: 51
milestone_name: milestone
---

# DocSift — Project State

## Project Reference

- **Name:** DocSift
- **Core Value:** 用户可以在自己的笔记和文档库中，用自然语言快速、准确地找到需要的信息——无论关键词是否匹配。
- **Current Focus:** Phase 05 — Agent Context Experience
- **Tech Stack:** Python 3.10+, SQLite (FTS5 + sqlite-vec), Click, Pydantic, sentence-transformers, llama-cpp-python

## Current Position

Phase: 05 (Agent Context Experience) — EXECUTING
Current Plan: 9
Total Plans in Phase: 9

- **Phase:** 05 — Agent Context Experience
- **Plan:** 9 of 9
- **Status:** Phase complete — ready for verification
- **Progress Bar:** `[████████████████████] 100%`

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
- **Phases defined:** 9
- **Tests passing:** 646 passed, 11 skipped, 0 failed (post 05-09)
- **Known blockers:** 0

**Per-Plan Metrics:**

| Plan | Duration | Tasks | Files |
|------|----------|-------|-------|
| Phase 05 P08 | 17min | 2 tasks | 9 files |
| Phase 05 P09 | 12min | 2 tasks | 5 files |

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

### Roadmap Evolution

- Later-added phases: 07 Claude skills (2026-04-20), 08 rename DocSift→SIF (2026-04-27), 09 MCP server (2026-05-08)

### TODOs

- [x] Plan Phase 06 documentation audit and refresh — 7 plans created and verified
- [x] Phase 7: CLI Claude Skill — sif-search and sif-get skills created, symlinked, and committed
- [ ] (Backlog) Phase 8: LLM-based query expansion — model tested (Qwen3.5-2B), awaiting v1.0 ship

### Blockers

- None

### Quick Tasks Completed

| # | Description | Date | Commit | Directory |
|---|-------------|------|--------|-----------|
| 260905-hc3 | Fix G-04-1 snippet relevance: markdown line-aware SmartSnippetExtractor windows; stem-tolerant word-boundary term matching shared with BM25 highlights | 2026-09-05 | 89a8a5e | [260905-hc3-fix-g-04-1-snippet-relevance-markdown-li](./quick/260905-hc3-fix-g-04-1-snippet-relevance-markdown-li/) |
| 260905-kmv | Fix G-04-2 reranker load crash: model-dir resolution prefers real model config over aux subdirs; CLI ClickException on reranker failure | 2026-09-05 | 0831f41 | [260905-kmv-fix-g-04-2-reranker-load-crash-model-dir](./quick/260905-kmv-fix-g-04-2-reranker-load-crash-model-dir/) |
| 260905-sxc | Fix G-04-3 HyDE unreachable: add create_completion to LlamaCppEmbedder wrapping llama_cpp completion with openai-style return shape | 2026-09-05 | 67c9ecf | [260905-sxc-fix-g-04-3-hyde-unreachable-add-create-c](./quick/260905-sxc-fix-g-04-3-hyde-unreachable-add-create-c/) |
| 260905-tax | Fix G-04-4 GGUF embed shape: unwrap llama_cpp list-of-embeddings, mean-pool token-level output before normalization | 2026-09-05 | 958262b | [260905-tax-fix-g-04-4-gguf-embed-shape-unwrap-llama](./quick/260905-tax-fix-g-04-4-gguf-embed-shape-unwrap-llama/) |

### Overrides

- [2026-09-03] Phase 03 decision-coverage gate override (user-approved): D-06/D-07/D-08/D-10 accepted as covered-by-legacy — implemented and behaviorally verified per 03-VERIFICATION.md; legacy plans 03-01…03-06 predate D-ID citation and are read-only in gap-closure mode. Verify-phase should re-surface this.

## Session Continuity

- **Last session:** 2026-09-07T04:12:40.202Z
- **Stopped at:** Completed 05-09-PLAN.md
- **Resume file:** None
- **Last action:** /gsd-verify-work 05 → 7 outstanding items re-verified live with sif CLI (context types, filters, search context attach incl. hybrid+reranker, SIF_DB_PATH status) — all pass; /gsd-audit-uat follow-ups done (9-UAT format normalized, 03 deferred marked resolved)
- **Next expected action:** v1.0 phases all executed and verified. Optional: two deferred follow-ups in 04-UAT.md (embedding cache key omits model_path; caplog test pollution), then /gsd-progress or /gsd-complete-milestone when ready to close v1.0.
