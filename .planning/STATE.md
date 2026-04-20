---
gsd_state_version: 1.0
milestone: v1.0
milestone_name: milestone
status: active
last_updated: "2026-04-20T20:35:00Z"
progress:
  total_phases: 7
  completed_phases: 6
  total_plans: 37
  completed_plans: 37
  percent: 86
---

# DocSift — Project State

## Project Reference

- **Name:** DocSift
- **Core Value:** 用户可以在自己的笔记和文档库中，用自然语言快速、准确地找到需要的信息——无论关键词是否匹配。
- **Current Focus:** Phase 07 — cli-claude-skill
- **Tech Stack:** Python 3.10+, SQLite (FTS5 + sqlite-vec), Click, Pydantic, sentence-transformers, llama-cpp-python

## Current Position

Phase: 07 (cli-claude-skill)
Plan: Not planned yet

- **Phase:** 7
- **Plan:** 0/TBD
- **Status:** Not Planned
- **Progress Bar:** `[████████████████░░░░] 86%`

## Phase History

| Phase | Date Started | Date Completed | Outcome |
|-------|--------------|----------------|---------|
| 01 — Foundation Fix | 2026-04-14 | 2026-04-14 | All 6 plans passed. Core infrastructure is trustworthy. |
| 02 — CLI Core Completion | 2026-04-15 | 2026-04-15 | All 6 plans passed. Full CLI surface for collection, search, index, and retrieval. |
| 03 — Embedding & Vector Search | 2026-04-16 | 2026-04-16 | All 6 plans passed. Configurable backends, sqlite-vec integration, batch embedding. |
| 04 — Advanced Search Pipeline | 2026-04-17 | 2026-04-17 | All 5 plans passed. BM25, vector, hybrid search, reranking, query expansion, and benchmarking all functional. |
| 05 — Agent Context Experience | 2026-04-18 | 2026-04-18 | 7/7 plans passed. 3 gap closure fixes committed. Qwen3 models set as default. |
| 06 — Documentation Audit & Refresh | 2026-04-18 | 2026-04-18 | All 7 plans passed. Auto-generated CLI/config references, docs code block validator (12 tests), Makefile target, GitHub Actions CI workflow. |
| 07 — CLI Claude Skill | — | — | New phase added. Goal: Generate Claude skills for all CLI commands in the project. |

## Performance Metrics

- **Requirements mapped:** 31/31 v1 + 7 DOC requirements
- **Phases defined:** 7
- **Tests passing:** 365 passed, 11 skipped, 0 failed
- **Known blockers:** 0

## Accumulated Context

### Decisions

- ✓ D-01: FTS5 synchronization uses SQLite triggers on external content tables
- ✓ D-02: `sqlite_repository.py` deleted, all access consolidated into `repositories.py`
- ✓ D-03: Vector search fails fast with `RuntimeError` when sqlite-vec is unavailable
- ✓ D-04: MCP server uses connection-per-request via `DatabaseConnection`
- ✓ D-05: Heavy ML libraries remain optional extras in `pyproject.toml`
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

### Roadmap Evolution

- Phase 7 added (2026-04-20): Generate Claude skills for all CLI commands in the project

### TODOs

- [x] Plan Phase 06 documentation audit and refresh — 7 plans created and verified
- [ ] Phase 7: CLI Claude Skill — Generate Claude skills for all CLI commands (search, vsearch, query, collection, context, index, etc.)
- [ ] (Backlog) Phase 8: LLM-based query expansion — model tested (Qwen3.5-2B), awaiting v1.0 ship

### Blockers

- None

## Session Continuity

- **Last action:** Phase 7 context gathered — 4 gray areas discussed, 5 implementation decisions locked
- **Next expected action:** Run `/gsd-plan-phase 7` to create executable plans
