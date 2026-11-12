# DocSift

## What This Is

DocSift 是 [qmd](https://github.com/tobi/qmd) 的 Python 重构版本，一个面向个人知识库的**本地混合搜索引擎**。它索引 Markdown 笔记、文档和会议纪要，支持关键词搜索（BM25）、语义向量搜索（Vector Search），以及基于 LLM 的重排序（Rerank）和查询扩展。同时提供 CLI 工具和 MCP（Model Context Protocol）服务器两种使用方式，完全在本地运行，无需外部 API。

## Core Value

用户可以在自己的笔记和文档库中，用自然语言快速、准确地找到需要的信息——无论关键词是否匹配。

## Current Milestone: v1.2 Search Precision and Agent Experience

**Goal:** 让搜索精准可控（元数据过滤 + 正确性修复）、让 MCP 达到 2026 生态就绪（SDK v2 + agent 包装）、让质量提升有 held-out 证据（个人语料评测 + Harrier 评估），并补齐分发与 CI 缺口。

**Target features:**

*搜索精准化*
- 元数据过滤 AST：path/mtime/tag/frontmatter 键，RRF 前应用，CLI + MCP 共享（qmd 未发布旗舰 parity）
- `metadata` 发现工具（键/类型/值统计）
- 正确性修复：parser 分派接线、向量按文档去重、hybrid offset 切片、标题入 FTS
- 规模：消除每查询全表扫描（staleness/contexts）、`sif index vacuum` + backup、embed 流式分批

*MCP 现代化与 Agent 体验*
- 官方 Python SDK v2（MCPServer）升级，双时代（2025/2026）客户端服务
- 工具注解（readOnlyHint/idempotentHint）+ structuredContent/outputSchema
- MCP query 补齐 rerank/expand/snippet pipeline（与 CLI 对等）、懒加载 embedder、lex/vec 工具接线
- Host 头校验（Origin 已有）、`sif mcp daemon` stub 收口
- Claude Code skill/plugin + MCP Registry 上架

*质量可证*
- 个人语料 known-item 评测仪器（`sif eval --personal`，免人工标注）
- Harrier-OSS-v1-0.6b EN+ZH held-out 评估（胜出才换默认；embedder 身份标记防同维陷阱）
- rapidfuzz 测量替换 difflib、chunk size/overlap 扫描 + 标题面包屑实验

*工程与分发*
- 测试 CI 矩阵（py3.10–3.13 × ubuntu/macos）+ Windows smoke（hc remote yoga）
- 发布 v1.1.x 到 PyPI（trusted publishing）+ Makefile/extras/pre-commit 清理
- `sif models pull/status` + 下载器 bug 修复 + 非 TTY 静默；安装文档重写（uv 优先）

## Milestone v1.1: Live Index and Search Quality（已发布 2026-11-12）

**Goal:** 让索引从手动 `index update` 变为自动常新（Live Index），并让搜索质量可配置、可量化、持续可调（Search Quality）。

**Target features:**

*Live Index（四种形态，依赖递进）*
- `sif watch` 前台命令：文件变更 → 增量重索引（watchdog 地基已在 `src/sif/indexing/watcher.py`，未接线）
- MCP server 内嵌刷新：watch 与 MCP 同进程，AI 助手查询时索引常新
- 后台守护进程：`--detach` / launchd / systemd 常驻
- 命令前自动检测：未开 watch 时，搜索命令前轻量增量兜底

*更新深度可配置*
- 默认仅 BM25/FTS 增量（快）；`--embed` 选项开启向量自动更新

*Search Quality*
- 混合权重可配置（BM25 / 向量 / RRF k 暴露为设置）
- Query suggestions（索引词项/历史 did-you-mean）
- Reranker 调优（Qwen3-Reranker 阈值/延迟）
- bench 基准集扩充（为全部调优提供量化依据）

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
- ✓ 搜索质量：bench 基准集扩充（nDCG@10/Hit@10/p50-p95、56 条分类查询 36/20 分割、45 配置扫描、held-out 默认值锁定，诚实结论：默认值不变） — Validated in Phase 16
- ✓ 搜索质量：Reranker 调优（显式 opt-in `SIF_RERANK_ENABLED`/`--rerank`、候选上限 5-50 夹取、相对阈值 α=0.5、over-fetch 让上限真正生效） — Validated in Phase 16
- ✓ 技术债收口：symlink/别名路径经 `get`/`multi-get`/MCP `get_document` 解析到已索引文档（DEBT-PN）；旧版 FTS 触发器迁移 + 检测门控 rebuild 清除陈旧索引（CR-01）；`--xml` 输出恒为良构 XML（CR-02）；全部 26 处 CLI Database 构造点上下文管理器持有、异常路径确定性关闭（WR-01） — Validated in Phase 10.1（2026-11-06 重新验证 16/16 通过，fresh fingerprint）

### Validated（v1.1 — shipped 2026-11-12）

- ✓ Live Index：`sif watch` 前台命令（增量重索引 + 防抖） — Validated in Phase 12
- ✓ Live Index：更新深度可配置（默认 BM25/FTS，`--embed` 开启向量自动更新） — Validated in Phase 12（与 MCP 内嵌刷新项合并验证 LIVE-05 深度矩阵）
- ✓ Live Index：搜索命令前自动增量检测兜底（LIVE-10 stat 漂移检测 + 上限 + 干净零成本） — Validated in Phase 14（2026-11-08，UAT 2/2 含 3000 文档实测 +105ms）
- ✓ 搜索质量：分层更新深度下向量滞后结果标记 staleness（QUAL-06，五格式 + MCP + status 行） — Validated in Phase 14

- ✓ Live Index：MCP server 内嵌 watch 刷新（SIF_MCP_WATCH，双传输，BM25 强制深度） — Validated in Phase 13
- ✓ Live Index：后台守护进程（--detach / launchd / systemd，PID/stop/status + 服务安装） — Validated in Phase 13（2026-11-08 重验 40/40，UAT 5/5）
- ✓ 搜索质量：混合权重（BM25/向量/RRF k）可配置（QUAL-01，SC1 逐字节一致 + CLI/MCP/设置全链路） — Validated in Phase 15
- ✓ 搜索质量：Query suggestions（did-you-mean，QUAL-02/03/04，`sif suggest` 三段式 + query_log + 100ms 预算实测 ≤10ms） — Validated in Phase 15（2026-11-08 重验 30/30，UAT 5/5）

### Active

<!-- v1.2 高层目标；细化 REQ-ID 见 REQUIREMENTS.md（定义中） -->

- [ ] 元数据过滤（path/mtime/tag/frontmatter，RRF 前）+ metadata 发现 + 分页修复
- [ ] 搜索正确性与规模（parser 接线、去重、offset、去全表扫、标题 FTS、vacuum）
- [ ] MCP SDK v2 现代化 + 注解/structuredContent + query pipeline 对等 + agent 包装
- [ ] 个人语料评测仪器 + Harrier held-out 评估 + rapidfuzz/chunk 调优
- [ ] 测试 CI + Windows smoke + PyPI 发布 + models UX + 安装文档

### Out of Scope

- 多用户/权限系统 — 本地单用户工具，不需要
- 实时协作/同步 — 超出 qmd 原有范围
- Web UI — qmd 也没有，仅 CLI + MCP
- 非 Markdown 格式的复杂解析（如 PDF、Word、HTML、EPUB）—— 先聚焦文本和代码文件；**2026-11-13 用户再次确认不做**（竞品虽有 PDF，但维持本地文本聚焦；pypdf/trafilatura 选型研究已存档备用）
- Windows 完整支持 — 推迟 v2（POSIX fork/systemd-everywhere/flock 降级需专门设计）；v1.2 仅 CI smoke（hc remote yoga）
- spellfix1（FUTR-01）— ASCII-only 距离核心 + sdist-only 打包税 + 零中文收益（2026-11-13 研究结论）
- 语义分块 / late chunking — NAACL 2025 反面证据；last-token pooling 模型机械不兼容
- ANN 向量索引 — 100k 向量 brute force 75-150ms 够用；stable sqlite-vec 量化+rescore 是现成逃生门
- chat-with-notes / ask — MCP 消费者本身就是 chat 层，投资引用级检索而非问答

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
| Watch 管线：per-burst flock + per-path 定向更新 | 每个防抖批次短锁（watch 空闲不持锁，D-04）；`update_paths` 成本正比于变更规模，stat 为准（D-06），Phase 13/14 宿主复用 | Phase 12 Complete |
| 单一排除谓词 `FileScanner.matches`（扫描与 watch 同源） | LIVE-04 一致性由构造保证；`DEFAULT_IGNORE_PATTERNS` 增补编辑器噪声（.sb-*/4913/.#*/*.tmp） | Phase 12 Complete |
| missing-root 防护在共享核心（D-11） | 顺带修复 update_cmd 对消失根目录的潜在全量删除 bug；两条更新路径都有回归测试 | Phase 12 Complete |
| 文档内容永不作为 Rich markup 渲染 | get/multi-get 内容 `markup=False` 直出、表头 `escape()`——与 05-10/05-11 同类第三例；回归测试锁定（字面渲染、批次不中断、回退路径同等契约） | v1.0 Complete |
| docs 局部套件 `--no-cov` | 全局 `addopts` 覆盖率 + `fail_under=90` 使 docs-only 运行必失败（CI 自 Phase 10 起恒红）；Makefile 与 docs.yml 双修 | v1.0 Complete |
| v1.2 范围四决策（2026-11-13）：PDF 不做；MCP 升级 SDK v2；Harrier 纳入但 held-out 门禁；Windows 推迟 + CI smoke | 用户拍板；研究三路交叉验证（代码库差距/qmd 生态/技术选型） | — Pending |
| Harrier 默认切换门禁：EN+ZH held-out 胜出 + embedder 身份标记（非仅宽度） | 独立证据仅英文（localGPT A/B nDCG 0.915 vs 0.805）；Harrier 与 Qwen3-0.6B 同 1024 维，宽度守护会静默接受坏切换；query 侧必须 prompt_name | — Pending |
| Windows smoke 走 hc remote yoga（Win11 26300） | 用户指定；yoga 未装 Python（仅 Store alias），CI phase 需先 uv/Python setup | — Pending |
| DYM 选型：rapidfuzz 测量替换 > symspellpy 推迟 > spellfix1 跳过 | 个人 KB 规模 difflib 已够用；rapidfuzz 去首字母桶是召回修复；symspellpy 仅 >200k 词表再议 | — Pending |

## Context（v1.1 shipped 2026-11-12）

- 版本 1.1.0；7 phases (11–16.1), 27 plans, 67 tasks；~18,064 LOC src；52 feat commits since v1.0.1
- 质量门禁：1591 passed, 1 skipped @ 95.18% coverage（fail_under=90 常驻）、ruff/format/ty 全绿
- Live Index：WAL+flock 并发 DB 核心、`sif watch` 前台/MCP 内嵌/后台守护进程三宿主、命令前漂移刷新 + staleness 标记
- Search Quality：可配置 RRF 权重、did-you-mean + 历史 + `sif suggest`、bench 扩充 + reranker 调优（held-out 论证下默认值不变）
- Tech debt (16.1)：全 CLI 错误边界约定、cache TTL instant 比较、embedding cache factory 委派、公开 reconcile-enqueue API
- 遗留（非阻塞）：WR-02 cleanup OperationalError 抑制（OQ2 有意保留）、14-IN-01 代码已修待 ledger 核销、info-findings 扫描、Phase 16 real-model 证据已记录（WINDOWS id 10 closed）

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
*Last updated: 2026-11-13 after v1.2 milestone start（范围确认：元数据过滤 + MCP 现代化 + 质量仪器 + 分发；PDF 维持排除，Windows 推迟 + smoke）*
