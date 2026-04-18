# Phase 6: Documentation Audit & Refresh — Specification

**Created:** 2026-04-18
**Ambiguity score:** 0.11 (gate: ≤ 0.20)
**Requirements:** 7 locked

## Goal

All project documentation accurately reflects the current CLI commands, API, and configuration. Every code example in docs is syntax-checked or executed and verified to work. A docs testing infrastructure is established for ongoing maintenance.

## Background

The DocSift documentation has drifted significantly from the codebase after 5 rapid implementation phases:

- `docs/configuration.md` references wrong default model (`all-MiniLM-L6-v2` vs actual `Qwen/Qwen3-Embedding-0.6B`), wrong embedding dimension (384 vs 1024), and includes non-existent settings (`DOCSIFT_MAX_WORKERS`, `DOCSIFT_CACHE_SIZE`, `DOCSIFT_LOG_FILE`, `DOCSIFT_BM25_K1`, `DOCSIFT_BM25_B`). It also omits reranker settings (`reranker_model_name`, `reranker_model_path`, `reranker_model_type`, `reranker_batch_size`), API settings (`api_key`, `api_base`), and the `modelscope` model type option.
- `docs/cli-reference.md` is missing several implemented commands (`collection update-cmd`, `collection include/exclude`, `collection enable/disable`, `context prune`) and options (`--explain`, `--min-score`, `--full`, `--candidate-limit`, `--intent`, `--line-numbers`). It documents removed commands (`query`, `embed`, `cleanup`) and has incorrect option descriptions (e.g., `context add` lacks `--type` option, shows non-existent `--document` option).
- `docs/quickstart.md` and `README.md` use outdated command syntax (`--collection` instead of `-c`), outdated model names in examples, and commands that no longer exist (`docsift search similar`, `docsift mcp start`).
- `README.md` roadmap lists features already implemented (query expansion, reranking, MCP server) as future work.
- No automated mechanism exists to validate code examples in documentation.

## Requirements

1. **CLI Reference Accuracy**: `docs/cli-reference.md` accurately describes every current Click command, subcommand, argument, and option.
   - Current: cli-reference.md is missing ~6 commands and ~10+ options, documents removed commands (`query`, `embed`, `cleanup`), and option descriptions are inconsistent with actual CLI
   - Target: cli-reference.md contains complete Click-derived documentation for all commands including internal/debug commands, with correct arguments, options, defaults, and examples
   - Acceptance: A script automatically extracts `--help` output from all Click commands and diff-checks against cli-reference.md; zero undocumented commands or options

2. **Configuration Guide Accuracy**: `docs/configuration.md` lists all valid environment variables with correct defaults matching the `Settings` class.
   - Current: configuration.md has 5+ non-existent settings, wrong defaults for model_name/embedding_dim, and omits 8+ real settings (reranker, API, model_type options)
   - Target: configuration.md documents every field in `Settings` class with correct default value, type, description, and validation rules
   - Acceptance: A script introspects `Settings` class fields and validates that every field is documented with correct default; zero undocumented fields, zero phantom fields

3. **Quickstart Guide Accuracy**: `docs/quickstart.md` uses commands that work with the current CLI.
   - Current: quickstart.md contains broken examples (`docsift search similar`, `docsift mcp start`, `--collection` long-form, wrong model names in `.env` examples)
   - Target: Every shell command example in quickstart.md executes successfully against the installed package; model names and defaults match current code
   - Acceptance: All shell code blocks in quickstart.md pass execution validation; `docsift --help` output for each referenced command matches documented usage

4. **README Accuracy**: `README.md` reflects current features, default models (Qwen3), and installation requirements.
   - Current: README shows wrong default model, marks OpenAI API as "planned" (already implemented), lists implemented features as roadmap items
   - Target: README accurately describes v1.0 features, correct default models, and realistic roadmap; installation from source works as documented
   - Acceptance: README model name matches `Settings.model_name` default; no "planned" features that are already implemented; `git clone` + `pip install -e ".[dev]"` works

5. **Technical Docs Accuracy**: `docs/mcp-server.md`, `docs/search-algorithms.md`, `docs/architecture.md`, `docs/models.md` are up-to-date with code.
   - Current: Technical docs were written before Phases 3-5 implementation; likely stale on vector search details, embedding backends, reranker architecture, and MCP dual-implementation status
   - Target: Each technical doc accurately reflects current implementation; architecture diagrams match actual module structure; algorithm descriptions match current code
   - Acceptance: Each technical doc is reviewed against corresponding source files; any factual discrepancy is documented and fixed

6. **Code Example Validation**: All code examples in docs are executed or syntax-checked and verified to work.
   - Current: No validation mechanism exists; broken examples have persisted across multiple phases
   - Target: Every shell code block is executable or marked with a skip reason; every JSON/Python config block passes syntax validation
   - Acceptance: A validation script runs against all docs/ markdown files and produces a report showing pass/fail per code block; 100% of non-skipped blocks pass

7. **Docs Test Infrastructure**: Automated docs testing infrastructure is established for ongoing maintenance.
   - Current: No pytest tests, no Makefile target, no CI workflow for docs validation
   - Target: Three artifacts exist: (a) `tests/test_docs.py` that validates docs code blocks, (b) `make docs-test` Makefile target, (c) GitHub Actions workflow `.github/workflows/docs.yml` that runs on PR
   - Acceptance: `pytest tests/test_docs.py` passes; `make docs-test` executes successfully; CI workflow runs and passes on current docs state

## Boundaries

**In scope:**
- All markdown files in `docs/` directory and root directory (`README.md`, `CLAUDE.md`, etc.)
- Automated CLI reference generation script (extracts from Click `--help`)
- Automated Settings introspection script (validates configuration.md against `Settings` class)
- pytest-based docs code block validator (`tests/test_docs.py`)
- Makefile target (`make docs-test`)
- GitHub Actions CI workflow for docs validation
- Manual review and fixes for `mcp-server.md`, `search-algorithms.md`, `architecture.md`, `models.md`
- Fixes to code examples in quickstart, README, and other docs

**Out of scope:**
- PyPI package publication — `pip install docsift` remains documented as the eventual install method but package is not published in this phase
- Rewriting or refactoring CLI command implementations — only documentation changes; code bugs discovered during audit may be fixed via `/gsd-quick` but are not the primary deliverable
- Creating new CLI commands (e.g., `docsift docs generate`) — documentation scripts are standalone, not CLI subcommands
- Adding new Settings fields solely for docs generation purposes
- Rewriting `CLAUDE.md` — project instructions for Claude Code; updates only if factual errors about architecture are found
- Web UI, plugin system, or other backlog features — these remain in README roadmap as aspirational items

## Constraints

- Python 3.9+ compatibility for all docs test scripts
- Docs tests must not require external network access (no model downloads, no API calls) — use mocks or skip for examples that require network
- Click auto-extraction script must handle nested command groups (`collection`, `context`, `mcp`, `search`)
- Maintain existing Markdown formatting style in docs; do not switch to RST or another format
- Validation must distinguish between shell commands (executable), JSON/Python blocks (syntax check), and output examples (display-only, not executable)

## Acceptance Criteria

- [ ] `docs/cli-reference.md` contains all current Click commands and options with no undocumented or removed commands
- [ ] `docs/configuration.md` documents every `Settings` field with correct default value; no phantom fields
- [ ] Every shell command example in `docs/quickstart.md` executes without error against the local package
- [ ] `README.md` default model name matches `Settings.model_name` (`Qwen/Qwen3-Embedding-0.6B`)
- [ ] `README.md` does not list any already-implemented feature as "planned" or "future"
- [ ] `docs/mcp-server.md`, `docs/search-algorithms.md`, `docs/architecture.md`, `docs/models.md` reviewed and discrepancies fixed
- [ ] `tests/test_docs.py` exists and passes, validating all docs code blocks
- [ ] `make docs-test` target exists and executes successfully
- [ ] `.github/workflows/docs.yml` exists and passes in CI
- [ ] Docs validation report shows 100% of non-skipped code blocks passing

## Ambiguity Report

| Dimension          | Score | Min  | Status | Notes                              |
|--------------------|-------|------|--------|------------------------------------|
| Goal Clarity       | 0.93  | 0.75 | ✓      | Clear outcome: accurate docs + tested examples + infrastructure |
| Boundary Clarity   | 0.88  | 0.70 | ✓      | Explicit in/out scope lists; PyPI excluded; code changes out of scope |
| Constraint Clarity | 0.85  | 0.65 | ✓      | Python 3.9+, no network, nested Click groups, Markdown format preserved |
| Acceptance Criteria| 0.88  | 0.70 | ✓      | 10 pass/fail criteria, all verifiable |
| **Ambiguity**      | 0.11  | ≤0.20| ✓      |                                    |

Status: ✓ = met minimum, ⚠ = below minimum (planner treats as assumption)

## Interview Log

| Round | Perspective     | Question summary                              | Decision locked                                    |
|-------|-----------------|-----------------------------------------------|----------------------------------------------------|
| 1     | Researcher      | 代码示例验证方式？                            | 建立自动化 docs 测试基础设施                        |
| 1     | Researcher      | README Roadmap 是否更新？                     | 保留愿景式 Roadmap，不改为准确状态列表              |
| 1     | Researcher      | CLI 参考详细程度？                            | 完整参数级别（所有选项、默认值）                    |
| 2     | Simplifier      | 未列出的文档文件是否审计？                    | 全部文档都审计（包括 api-reference、development、contributing） |
| 2     | Simplifier      | CLI 文档实现方式？                            | 脚本自动从 Click `--help` 提取                      |
| 2     | Simplifier      | 自动化测试范围？                              | 所有代码块 + 语法检查（shell + JSON + Python）      |
| 3     | Boundary Keeper | 明确排除项？                                  | PyPI 发布明确排除；代码修改不作为主要交付物          |
| 3     | Boundary Keeper | Click 提取范围？                              | 所有命令包括内部命令                               |
| 3     | Boundary Keeper | 基础设施输出形式？                            | pytest 测试 + Makefile target + CI workflow 全部建立 |

---

*Phase: 06-documentation-audit-refresh*
*Spec created: 2026-04-18*
*Next step: /gsd-discuss-phase 6 — implementation decisions (how to build what's specified above)*
