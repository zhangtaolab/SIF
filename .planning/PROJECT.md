# DocSift

## What This Is

DocSift 是 [qmd](https://github.com/tobi/qmd) 的 Python 重构版本，一个面向个人知识库的**本地混合搜索引擎**。它索引 Markdown 笔记、文档和会议纪要，支持关键词搜索（BM25）、语义向量搜索（Vector Search），以及基于 LLM 的重排序（Rerank）和查询扩展。同时提供 CLI 工具和 MCP（Model Context Protocol）服务器两种使用方式，完全在本地运行，无需外部 API。

## Core Value

用户可以在自己的笔记和文档库中，用自然语言快速、准确地找到需要的信息——无论关键词是否匹配。

## Milestone v1.2: Search Precision and Agent Experience（已发布 2026-11-18）

**Goal:** 让搜索精准可控（元数据过滤 + 正确性修复）、让 MCP 达到 2026 生态就绪（SDK v2 + agent 包装）、让质量提升有 held-out 证据（个人语料评测 + Harrier 评估），并补齐分发与 CI 缺口。

**Shipped:** 2026-11-18 — 8 phases / 55 plans 全部 goal-backward verified `passed`；tag `v1.2.0`，PyPI `docsif` 1.2.0（PR #3，Publish run 44289577210）；全量 3234 passed / 1 skipped @ 95.03%。

**Post-ship gap round for Phase 19 (2026-11-26 → 2026-11-27):** after the v1.2.4 release, Phase 19 was re-opened for correctness. Six gap-closure plans (19-10 to 19-15) fixed the per-chunk identity at 80 columns and in the machine formats, the BM25 `--min-score` direction and exact-equality boundary (operator decision: `monotone-map`), and the truthfulness of the `query`/`vsearch` help texts; three missing guards were added. Phase 19 is re-verified `passed` (115/115 must-haves, fingerprint `v4:sha256:373d380f…`), UAT complete 18/18, `19-VALIDATION.md` re-certified (`nyquist_compliant: true`, `validated: 2026-11-27`), the review is clean after WR-01/IN-01 were fixed, and the full suite is 3320 passed / 1 skipped @ 95.16%.

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

### Validated（v1.2 — Phases 17–24 shipped 2026-11-18）

- ✓ 工程基础：py3.10–3.13 × ubuntu/macos CI 矩阵、Windows 降级 smoke（hc yoga）、`docsif` 1.1.2 trusted publishing 发布 — Validated in Phase 17
- ✓ 质量仪器：`sif eval --personal` known-item 评测（bias controls + 保存/对比）、rapidfuzz did-you-mean 测量替换 — Validated in Phase 18
- ✓ 搜索正确性：frontmatter-only 编辑刷新、向量 pre-fusion 按文档去重、确定性分页、标题 FTS 排名、单一 context/staleness attach — Validated in Phase 19
- ✓ 元数据过滤 + 发现：qmd 17 操作符过滤 AST（pre-RRF 双腿下推）、path/mtime 内置字段、类型化 kv 存储 + 回填、MCP `metadata` 工具（冻结契约） — Validated in Phase 20
- ✓ 规模与维护：bounded staleness/contexts 读取、`index vacuum`/backup、流式 embed、`index_meta` embedder identity + role-aware embed — Validated in Phase 21
- ✓ MCP SDK v2 + agent 包装：官方 `mcp` SDK 组合根、双 era 客户端、七只读工具 + annotations/structuredContent、query pipeline 对等（懒加载 embedder、rerank opt-in）、transport security + 真实 daemon、引用级输出、Claude Code plugin/skills、MCP Registry manifest + 幂等预检脚本（公开 listing 记录 `blocked no-github-login`） — Validated in Phase 22
- ✓ Harrier 门禁评估：Phase 18 仪器扩展出 per-language × per-leg held-out gates + 语言感知加宽 + `--require-language`；纯判定的双侧 verdict rule；隔离双臂 runbook（身份校验、adequacy preflight、scope-keyed resume、artifact、cleanup guard）；真实 EN+ZH A/B 在用户批准的 curated 双语子集（498 docs，adequacy en=42/zh=11，held-out N=56）上记录 `keep-qwen3`（整体 Δ +0.00943，CI 含 0；en +0.01385，zh −0.00487），默认值未变，Qwen3 保持 — Validated in Phase 23
- ✓ 调优 + 模型 UX + 安装文档：held-out 门禁的 chunk sweep（记录 keep-default，N=194）与标题面包屑实验（记录 keep-breadcrumb-off，body-leg veto）；`sif models pull/status` + canonical manifest 缓存 + legacy 迁移；uv-first 安装文档（`--torch-backend=cpu` 配方）+ 降级矩阵 — Validated in Phase 24

### Active

（None — 下一个里程碑的范围由 `/gsd-new-milestone` 定义。）

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
| v1.2 范围四决策（2026-11-13）：PDF 不做；MCP 升级 SDK v2；Harrier 纳入但 held-out 门禁；Windows 推迟 + CI smoke | 用户拍板；研究三路交叉验证（代码库差距/qmd 生态/技术选型） | v1.2 Complete |
| Harrier 默认切换门禁：EN+ZH held-out 胜出 + embedder 身份标记（非仅宽度） | 独立证据仅英文（localGPT A/B nDCG 0.915 vs Qwen3-Embedding-4B 0.875；此前转述的 vs-0.6B 0.805 未在该精确值核实）；Harrier 与 Qwen3-0.6B 同 1024 维，宽度守护会静默接受坏切换；query 侧必须 prompt_name | Phase 23 Complete（keep-qwen3，默认值不变） |
| Windows smoke 走 hc remote yoga（Win11 26300） | 用户指定；yoga 未装 Python（仅 Store alias），CI phase 需先 uv/Python setup | Phase 17 Complete（8/8 PASS 记录于 48759e2） |
| DYM 选型：rapidfuzz 测量替换 > symspellpy 推迟 > spellfix1 跳过 | 个人 KB 规模 difflib 已够用；rapidfuzz 去首字母桶是召回修复；symspellpy 仅 >200k 词表再议 | Phase 18 Complete（p50 1.78ms @ 74.9k terms） |
| Phase 20 过滤 AST 严格对齐 qmd `[Unreleased]`（`qmd@86d2365`，2026-11-15 核实），condition 字段名用 `field` 而非旧 docs 的 `key` | 17 操作符 + `caseInsensitive` 逐字复刻；qmd 尚未发布，parity 固定到当前 era 并在 SUMMARY 记录 `abfabc5` 差异 | Phase 20 Complete |
| 内置过滤字段只有 `path` / `mtime`；无 `tags` 别名，`title` 不保留 | FILT-02 只点名两个字段；tags 是普通 frontmatter，数组即集合，`contains`/`all` 已够用（D-03/D-04） | Phase 20 Complete |
| 类型化 kv：单表 `document_metadata_values`（每标量/数组元素一行 + `ordinal`）+ `document_metadata_skips` 旁表；行从 `json.loads(canonical_metadata_json(...))` 派生 | 与 `documents.metadata` 同一序列化来源，YAML 日期不漂移；不引入 JSON1 依赖（D-05/D-07） | Phase 20 Complete |
| 回填是一次 Python 遍历已存 canonical metadata，写全局 `index_meta.metadata_values_version` 标记，失败绝不让过滤读到半填充 store | 不再强制 reindex、不改 checksum 约定；per-document 短事务可续跑（D-06） | Phase 20 Complete |
| 向量 leg 分批升级的停止条件改为键控任意 JOIN 过滤（含 collection）并用 selectivity 预计数作目标；`_MAX_FETCH_K=2048` 仍是硬上限 | 原 `len(rows) < fetch_k` 在 JOIN 之后判定，选择性过滤会在首批就停止升级（实测 2 文档集合 limit=10 只回 1 条）；"过于选择性" 只在元数据过滤且命中数≥目标时以 stderr 单次告警（D-08/D-09） | Phase 20 Complete |
| 发现工具信封在 D-15 基础上叠加 `builtIns`（`path`、`mtime`，取自 `documents` 列，`match` 不缩小） | D-03 要求内置字段可被发现；独立列表让 frontmatter key 窗口/排序/分页语义保持不变，作为 Phase 22 冻结契约的一部分（D-20） | Phase 20 Complete |
| 过滤错误面：CLI `ClickException` 命名 operator/field/AST 路径；MCP `ToolsCallResult(isError=True)`，绝不 `INVALID_PARAMS` | SEP-1303 让模型可自我纠正；空匹配返回空页而非 "无过滤"，沿用 exclude-all 哨兵契约（D-17） | Phase 20 Complete |
| Phase 20 代码评审 2 Critical + 7 Warning 全部修复并附前置失败回归测试 | CR-01 类型化派生对超大整数/非有限数不 total（会中断索引、并让升级后所有命令失败）；CR-02 候选域 `EXISTS` 在本机 SQLite 3.51.0 上会把 `in` 结果行重复（破坏分页、RRF 双计） | Phase 20 Complete |
| Phase 22：官方 `mcp==2.3.0` 组合根承载七个只读工具，旧协议壳整体删除；双 era golden transcripts 锁定 2024-11-05 → 2026-07-28 | 单一 SDK surface 才能在双 era 客户端下保持 annotations/structuredContent 一致；七工具全部 `read_only_hint`，无 mutation surface（D-06/D-07） | Phase 22 Complete |
| Phase 22：transport security 用 SDK `TransportSecuritySettings`，loopback 默认 + `--allowed-hosts` 只增不减；`/health` 同源 Host 门；daemon 用 `.mcp.pid` 与 watch 共存 | 手写 Origin 中间件删除前先以 spoofed header 证明 SDK 行为；wildcard 不能削弱 loopback（D-13/C2/C5） | Phase 22 Complete |
| Phase 22：懒加载 embedder 用锁 + 失败锁存，query 复用 CLI SearchPipeline（前缀 `lex:` 先于加载决策）；rerank 保持 opt-in | 冷启动不得泄露 stdout、不得阻塞事件循环；加载失败降级 BM25 一次告警（D-15/D-17；CR-01/CR-02 评审修复） | Phase 22 Complete |
| Phase 22：引用级输出 = snippet 行窗 + 批量 `content_hash` + `get` 范围；Phase 20 metadata 信封冻结 | 代理引用必须先 `get` 后引用；text/structured 双通道一致，CLI JSON 不受影响（D-04/22-05） | Phase 22 Complete |
| Phase 22：仓库根即 Claude Code plugin/marketplace + 三个 MCP-first skill；`server.json` + 幂等 `publish_registry.py`；公开 Registry listing 记录 `blocked no-github-login` | 本地 MCP/plugin/skills 不需要 GitHub；公开 listing 是可选维护者动作，D-24 允许 blocked；脚本先查 name+version，已存在打印 `already listed` | Phase 22 Complete（listing deferred） |
| Phase 22 代码评审 2 Critical + 10 Warning 修复并附前置失败回归测试；1 necessity + 8 Info 保持 open；verifier 另发现 W-01（`multi_get` 显式 `max_bytes` 行号越界）作 follow-up | CR-01 并发首次向量查询把“加载中”当失败→静默降级 BM25；CR-02 `vec_search` 在事件循环上同步加载模型（首次下载会冻结所有会话/health）；W-01 默认预算跳过超大文档且 `get` 路径正确，非阻塞 | Phase 22 Complete |
| Phase 23：Phase 18 仪器扩展为 per-language / per-leg-language held-out gates + 语言感知加宽 + `--require-language`；严格沿用 1/N 噪声门与 0.01 tie rule，记录 `min_heldout_for_epsilon_win=101` | 250 文档采样上限下只有提高语料的中文占比才能同时满足 en/zh ≥10；0.01 胜出在 N≤100 不可能通过，必须显式记录 | Phase 23 Complete |
| Phase 23：隔离双臂 + 身份校验 + adequacy preflight + scope-keyed resume + artifact writer + cleanup guard；真实 A/B 在用户批准的 curated 双语子集（7 个中文目录，498 docs）上运行 | 一表一向量空间；同宽 1024 维陷阱靠完整 identity 防；preflight 不花 embed 预算；不伪造、不手抄任何指标 | Phase 23 Complete |
| Phase 23 verdict：`keep-qwen3`；整体 held-out Δ +0.00943（CI [−0.0296,+0.0484]，N=56，噪声地板 0.01786），en +0.01385，zh −0.00487（未破 −0.01 地板）；`default_flip` 与 `zero_delta_proof` 均记录 not-applicable | 无胜出即不切换；Qwen3 路径字节不变；curated 子集结论不外推到主库；模型下载 + 双arm re-embed 成本已记录 | Phase 23 Complete（default unchanged） |
| Phase 23 代码评审 2 Critical + 6 Warning 修复并附回归测试；IN-03（runbook ruff/format）一并修复；5 Info 保持 open | CR-01 scratch 根可等于 home 导致误删；CR-02 不足证据路径会复用陈旧 artifact；WR-01/02 resume/scope 幂等、WR-03 held-out 表、WR-04 artifact 保留块、WR-05 ranking 设置记录、WR-06 malformed JSON 错误面 | Phase 23 Complete |
| Phase 19 gap round 2：BM25 显示分 = 单调映射 `|bm25|/(1+|bm25|)`；`--min-score` 在 SQL 中对显示分做精确比较（`abs(m.score)/(1.0+abs(m.score)) >= ?`），阈值等于某行自己的显示分时保留该行 | 旧映射随匹配变好而下降，阈值会先删掉最佳匹配；操作员在 19-11 checkpoint 选择 `monotone-map`；边界舍入由 19-13 改为精确比较（UAT test 8） | Phase 19 Complete（2026-11-27） |
| Phase 19 gap round 2：`sif search query --min-score` 是对每条 leg 自己标尺的下限，融合 RRF 分从不与之比较；`query`/`vsearch` help、CLI reference、MCP 页面与 changelog 逐处写明 | 同一数值同时作用于 BM25 与向量两种标尺，无法对融合分下定义；19-14 只改文本不改行为（UAT test 14） | Phase 19 Complete（2026-11-27） |
| Phase 19 gap round 2：per-chunk 机器格式布局 A-19-10-1 按已交付形式确认（chunk 行 `path#sequence` + 裸 sequence；document 行纯路径无 sequence；`--files` 每页去重） | 操作员把逐项检测委托给 orchestrator，测试器按 shipped layout 接受；布局仍可随时由操作员改选（UAT test 12） | Phase 19 Complete（2026-11-27） |

## Context（v1.2 shipped 2026-11-18）

- 版本 1.2.0；8 phases (17–24), 55 plans；v1.1.2 → HEAD 共 406 commits、387 files changed（+112,979/−5,766，含测试/夹具/文档）
- 质量门禁：3234 passed, 1 skipped @ 95.03% coverage（fail_under=90 常驻）、ruff/format/ty 全绿；CI 8 格（py3.10–3.13 × ubuntu/macos）+ Docs Validation 全绿；Linux 3232/2 @ 95.04%、Windows smoke 8/8
- 分发：`docsif` 1.2.0 发布到 TestPyPI + PyPI（trusted publishing，PR #3 + tag `v1.2.0`）；Claude Code plugin/marketplace + MCP Registry manifest（公开 listing 仍 `blocked no-github-login`）
- 搜索：qmd-parity 过滤 AST（17 操作符）、标题 FTS、pre-fusion 去重、确定性分页、bounded staleness/contexts、streaming embed、embedder identity
- 质量：个人语料仪器 + 三项 held-out 门禁全部记录 keep（Harrier keep-qwen3、chunk keep-default、breadcrumb keep-breadcrumb-off）
- 遗留（非阻塞）：22/23/24 的若干 Info 级评审 findings；隐藏 `sif pull` legacy URL 路径下个版本移除；`24-VALIDATION.md` 仍为 draft（Nyquist 审计未跑）
- CI 回归修复（618997c）：`_mean` 改 `math.fsum` + `strictly_above_noise_floor()` —— py3.10/3.11 的朴素求和让 0.01 平局误判为胜出

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
*Last updated: 2026-11-27 after the Phase 19 gap round（v1.2 已发布；Phase 19 re-verified passed，UAT 18/18，validation re-certified）*
