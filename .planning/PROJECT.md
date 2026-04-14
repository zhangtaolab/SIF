# DocSift

## What This Is

DocSift 是 [qmd](https://github.com/tobi/qmd) 的 Python 重构版本，一个面向个人知识库的**本地混合搜索引擎**。它索引 Markdown 笔记、文档和会议纪要，支持关键词搜索（BM25）、语义向量搜索（Vector Search），以及基于 LLM 的重排序（Rerank）和查询扩展。同时提供 CLI 工具和 MCP（Model Context Protocol）服务器两种使用方式，完全在本地运行，无需外部 API。

## Core Value

用户可以在自己的笔记和文档库中，用自然语言快速、准确地找到需要的信息——无论关键词是否匹配。

## Requirements

### Validated

- ✓ 集合（Collection）的增删改查 — 现有
- ✓ 基于文件扫描的文档索引（含 checksum 去重） — 现有
- ✓ SQLite FTS5 全文搜索（BM25） — 现有
- ✓ 基础混合搜索（BM25 + Vector + RRF） — 现有
- ✓ MCP 服务器骨架（stdio + HTTP 双传输） — 现有
- ✓ 多格式输出（rich table / JSON / CSV / Markdown / XML） — 现有
- ✓ 文档片段（chunk）和嵌入存储 — 现有
- ✓ 修复现有 bug 和占位实现（stub）：硬编码模型路径、随机 embedding fallback、MCP 连接安全等 — Validated in Phase 01
- ✓ 依赖声明完整性：补全 `pyproject.toml` 中缺失的运行时依赖 — Validated in Phase 01

### Active

- [ ] 补齐缺失的 CLI 命令：multi-get、ls、update-cmd、pull、bench
- [ ] 实现 LLM 重排序（rerank）和查询扩展（query expansion），达到 qmd `query` 命令的搜索质量
- [ ] 统一 MCP 服务器实现：整合 legacy `mcp/` 和 refactored `mcp_server/`
- [ ] 嵌入模型灵活可配置：支持本地 GGUF（llama-cpp-python）、sentence-transformers，以及可选的 OpenAI 兼容 API

### Out of Scope

- 多用户/权限系统 — 本地单用户工具，不需要
- 实时协作/同步 — 超出 qmd 原有范围
- Web UI — qmd 也没有，仅 CLI + MCP
- 非 Markdown 格式的复杂解析（如 PDF、Word）—— 先聚焦文本和代码文件

## Context

- 原始项目 qmd 使用 TypeScript / Bun 开发，依赖 `node-llama-cpp` 加载 GGUF 模型进行本地 embedding 和 rerank。
- 当前 docsift 代码库已完成大部分核心架构（分层设计、Repository 模式、插件化 Chunker / Searcher），但存在多处 stub、bug 和未实现的 CLI 命令。
- 目标是**功能对等**的 Python 版本，同时改进架构（更好的模块化、可测试性）。
- 需要保持与 qmd 的 CLI 命令和 MCP 工具接口兼容，方便现有用户迁移。

## Constraints

- **Tech Stack**: Python 3.9+、SQLite（FTS5 + 可选 sqlite-vec）、Click CLI、Pydantic Settings
- **Local-First**: 默认所有模型本地运行，不依赖外部 API；API 调用仅作为可选配置
- **Compatibility**: CLI 接口和 MCP Tool Schema 尽量与 qmd 保持一致
- **Build**: hatchling 构建后端，pytest 测试

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| 完全复刻 qmd 功能 | 用户明确要求功能对等 | — In Progress |
| 本地模型 + API 切换双支持 | 提升灵活性和可访问性 | — In Progress |
| 优先修复 bug/stub，再补 CLI，再做 rerank/MCP | 先让现有代码可用，再扩展功能 | Phase 01 Complete |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd-transition`):
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone** (via `/gsd-complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-04-15 after Phase 01 completion*
