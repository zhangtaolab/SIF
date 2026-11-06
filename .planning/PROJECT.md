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
- ✓ 补齐缺失的 CLI 命令：multi-get、ls、update-cmd、pull、bench — Validated in Phase 02/04
- ✓ 嵌入模型灵活可配置：本地 GGUF（llama-cpp-python）、sentence-transformers、ModelScope，及可选 OpenAI 兼容 API（默认 Qwen3 系列） — Validated in Phase 03
- ✓ LLM 重排序（Qwen3-Reranker）和查询扩展（SearchPipeline），`query` 搜索质量达标 — Validated in Phase 04/05
- ✓ 统一 MCP 服务器实现（`src/sif/mcp/`，stdio + Streamable HTTP） — Validated in Phase 09
- ✓ 上下文描述：path/collection/global 三种作用域，context CLI 全命令集，搜索结果自动附加描述 — Validated in Phase 05（2026-11-06 重新验证 24/24 通过，第五次陈旧验证再生）
- ✓ 测试覆盖率常驻门禁：TOTAL 96.22%（1011 项测试），`[tool.coverage.report] fail_under = 90` 落地且无任何豁免行 — Validated in Phase 10（2026-11-06 重新验证 35/35 通过，fresh fingerprint）
- ✓ 技术债收口：symlink/别名路径经 `get`/`multi-get`/MCP `get_document` 解析到已索引文档（DEBT-PN）；旧版 FTS 触发器迁移 + 检测门控 rebuild 清除陈旧索引（CR-01）；`--xml` 输出恒为良构 XML（CR-02）；全部 26 处 CLI Database 构造点上下文管理器持有、异常路径确定性关闭（WR-01） — Validated in Phase 10.1（2026-11-06 重新验证 16/16 通过，fresh fingerprint）

### Active

（无 — v1.0 全部需求已交付，待 milestone 归档时全面复核）

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

- **Tech Stack**: Python 3.10+、SQLite（FTS5 + 可选 sqlite-vec）、Click CLI、Pydantic Settings
- **Local-First**: 默认所有模型本地运行，不依赖外部 API；API 调用仅作为可选配置
- **Compatibility**: CLI 接口和 MCP Tool Schema 尽量与 qmd 保持一致
- **Build**: hatchling 构建后端，pytest 测试（常驻 fail_under=90 覆盖率门禁）
- **Type checking**: ty 为唯一类型检查器（mypy 已于 2026-11-06 退役，`ty check src/sif` 0 诊断）

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| 远端维度探测 probe-free，缓存键 `base_url::model_name` | 避免对远端后端产生计费探测请求 | Phase 03 Complete |
| 上下文规范化：写入时存 `normalize_path` 规范形，读取时双侧重规范化匹配，显式 re-add 时合并旧 verbatim 行；永不批量回填迁移 | realpath 不可逆，SQL 预过滤永远无法匹配 verbatim 旧数据行（05-08/05-09，WR-01/WR-02/CR-02 根因） | Phase 05 Complete |
| 完全复刻 qmd 功能 | 用户明确要求功能对等 | — Complete (v1.0) |
| 本地模型 + API 切换双支持 | 提升灵活性和可访问性 | — Complete (v1.0) |
| 优先修复 bug/stub，再补 CLI，再做 rerank/MCP | 先让现有代码可用，再扩展功能 | Phase 01 Complete |
| 向量库幂等：re-chunk 事务内 delete-before-insert + 精确 chunk-id 集合跳过，`--force` 才全量重嵌 | G-03-3：重复 embed 不再产生孤儿向量/重复计费 | Phase 03 Complete (UAT 7/7) |
| embed_cmd 每集合一个事务，失败报告在事务外抛出 | CR-02：单集合失败不回滚已成功集合、退出码如实非零 | Phase 03 Complete (live-verified) |
| 覆盖率门禁 `fail_under = 90` 最后落地（D-04），禁用 exclude_lines / cov-branch / pragma 豁免 | 门禁不可绕过；覆盖率成为永久回归约束，只增不减 | Phase 10 Complete (96.22%, 1011 tests) |
| DEBT-PN 查找顺序（OQ2）：精确路径仅规范化形查找；ID/裸文件名保持原始；glob 原始优先、规范化兜底 | realpath 不可逆前提下最小惊讶：别名路径可命中，手迁移相对模式行不破坏 | Phase 10.1 Complete |
| FTS 迁移检测门控 `VALUES('rebuild')`（OQ1）：仅当检出旧版 direct-DELETE 触发器才重建索引，永不用 needs_rebuild_* 做门 | 修复状态而非仅机制：清除坏触发器时期的孤儿索引项；新库/已迁移库零开销 | Phase 10.1 Complete |
| CLI Database 生命周期：`with Database(index_path) as db:` 自 init_schema 起持有命令体，嵌套事务块原样保留 | 成功与异常路径都确定性关闭连接（57→13 ResourceWarnings，余量测试侧）；main.py 作用域置于 try/except 内部保证异常先关句柄 | Phase 10.1 Complete |
| XML 输出净化器 = XML 1.0 Char 产生式补集，先于 `xml_escape`/`quoteattr` 应用 | 转义只管 `<>&'"`，禁用码位归净化器管——两者不可互相替代；`ET.fromstring` 往返测试锁定 | Phase 10.1 Complete |
| mypy 退役，ty 为唯一类型检查器 | 17 条 ty 诊断清零（断言收窄/Protocol/cast，零行为变化），全部 mypy 残留清除；typing-debt 四批次收官 | v1.0 Complete |
| 文档内容永不作为 Rich markup 渲染 | get/multi-get 内容 `markup=False` 直出、表头 `escape()`——与 05-10/05-11 同类第三例；回归测试锁定（字面渲染、批次不中断、回退路径同等契约） | v1.0 Complete |
| docs 局部套件 `--no-cov` | 全局 `addopts` 覆盖率 + `fail_under=90` 使 docs-only 运行必失败（CI 自 Phase 10 起恒红）；Makefile 与 docs.yml 双修 | v1.0 Complete |

## Context（v1.0 shipped 2026-11-07）

- 版本 1.0.0；692 commits（2026-04-14 → 2026-11-07）；src 12.5K 行 / tests 23.1K 行
- 质量门禁：pytest 1015 passed @ 96.20%（fail_under=90 常驻、零豁免行）、ruff/format/ty 全绿
- 里程碑收尾时全量文档事实核验：512 条声明 0 失败；四个陈旧验证全部再生（05/06/07/10.1）

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
*Last updated: 2026-11-07 after v1.0 milestone（11/11 阶段、68/68 计划全部交付并持新鲜验证；里程碑审计 tech_debt 项全部在收尾前解决：路径规范化、CR-01/02、WR-01、docs CI、ty 清零、get 显示完整性、需求追溯 31/31）*
