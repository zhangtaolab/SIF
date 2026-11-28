# Phase 26: Anchor Arm + Deterministic Cache - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-11-28
**Phase:** 26-Anchor Arm + Deterministic Cache
**Areas discussed:** 触发面与臂语义, 锚点来源与生成器, 缓存与成本可见, 降级与外发披露

---

## Gray Area Selection

| Option | Description | Selected |
|--------|-------------|----------|
| 触发面与臂语义 | `--anchor` / `anchor:` / `hybrid+anchor` 的入口与粒度；两处前缀映射（hybrid.py:535 / backend.py:124）只有 lex/vec/hyde/expand；ANC-04 已把 `hybrid+anchor` 定为默认关闭的诊断臂。 | ✓ |
| 锚点来源与生成器 | 默认 `anchor:` 锚点由谁产生（PROJECT.md 零模型基线 vs GEN-01..04 LLM 生成器）；本地 GGUF 是否默认后端；无模型时 no-op / 规则锚点 / 报错。 | ✓ |
| 缓存与成本可见 | 复用 `llm_cache` vs 新建 `anchor_cache`；缓存键是否含 query+model+prompt version；跨进程命中；调用数/命中率/查询文本本地留存的用户可见面。 | ✓ |
| 降级与外发披露 | fail-open 回退时失败原因可见；无模型/无缓存/远程 opt-in 三情形与重试预算；GEN-04 外发披露程度；ANC-05 词表守卫默认与 A/B 开关。 | ✓ |

**User's choice:** 全部 4 个灰区。
**Notes:** 沿用 Phase 25 的中文讨论惯例；每题给优劣与推荐意见；本阶段无 UI 决定，未触发静态 HTML 多方案对照。16 题全部采用推荐项，未提出新能力请求。

---

## A. 触发面与臂语义

### A1. `anchor:` 作为独立 `SearchType.ANCHOR` 时检索腿怎么走？

| Option | Description | Selected |
|--------|-------------|----------|
| 纯 BM25 腿（推荐） | 优：`anchor:` = BM25(原 query + 锚点) 单腿，与 `lex:` 同粒度，贴近论文「LLM anchors 让 BM25 +0.11–0.19」且 Phase 25 规则锚点 spike 正是 lex→anchor 配对。劣：不触及向量腿，Phase 27 的 `hybrid+anchor` 需另作诊断臂。推荐：注入仅发生在 FTS MATCH 构造前。 | ✓ |
| 锚点 + 默认 hybrid | 优：一次调用拿融合结果。劣：混淆 ANCHOR 与 HYBRID 语义，ANC-04 明确 `hybrid+anchor` 只是默认关闭诊断臂；vector 腿是否吃锚点词难界定。 | |
| 锚点注入两条腿 | 优：向量 leg 也受益。劣：违背 ANC-02「仅注入 BM25 腿」，离散锚点词污染 dense 语义。 | |

**User's choice:** 纯 BM25 腿（推荐）
**Notes:** 与 ANC-02 / Phase 25 配对 delta 口径一致。

### A2. `--anchor` CLI flag 加在哪些命令？

| Option | Description | Selected |
|--------|-------------|----------|
| 仅 query 命令（推荐） | 优：`query` 是推荐命令且承载 hybrid/expand/rerank pipeline，`--anchor` 与 `--rerank` 并列最自然；search(BM25)/vsearch 保持纯基线。劣：纯 BM25 用锚点只能靠前缀。 | ✓ |
| search + query 都加 | 优：两入口都能一键锚点。劣：两处参数/docs 面；`search` 是刻意保留的纯 lex 基线，加 flag 模糊定位。 | |
| 只靠 anchor: 前缀 | 优：零新 flag、零 docs 生成面。劣：ANC-01/ROADMAP 成功标准 1 明确要求 `--anchor` flag 可用。 | |

**User's choice:** 仅 query 命令（推荐）

### A3. `--anchor` flag 与 `anchor:` 前缀同时出现 / 碰到其他前缀时怎么处理？

| Option | Description | Selected |
|--------|-------------|----------|
| flag OR 前缀，单一路由（推荐） | 优：二者等价于「以 ANCHOR 模式跑该 query」，同时出现不重复注入；与现有 prefix 只匹配第一个一致；`anchor:lex:foo` 视为 query 字面不二次解析。劣：不支持一次 query 叠多模式。 | ✓ |
| 显式优先级规则 | 优：冲突行为完全确定。劣：需额外定义与测试优先级矩阵，且用户同时给两个入口本身是误用。 | |
| 允许多前缀组合解析 | 优：表达力最强。劣：把 ANC-04 诊断臂提前做成通用组合器，scope 扩大且 Phase 27 才需要四臂。 | |

**User's choice:** flag OR 前缀，单一路由（推荐）

### A4. `hybrid+anchor` 诊断臂（ANC-04）本阶段以什么形式存在？

| Option | Description | Selected |
|--------|-------------|----------|
| SearchOptions 可组合（推荐） | 优：给 `SearchOptions` 加 `anchor_terms`（ANC-03 点名），让「注入锚点的 BM25 腿 + 原 hybrid 向量腿」可由评测代码组合；默认全关，`anchor:` 仍走纯 BM25。劣：pipeline 需区分「ANCHOR 纯腿」与「hybrid 腿带锚点」。推荐：只交付可组合底层能力 + 冻结 arm 定义，四臂评测留 Phase 27。 | ✓ |
| 独立 CLI 子命令 | 优：用户可直接跑。劣：新增一级公开命令 + docs 面，ANC-04 定位是诊断臂不是产品入口。 | |
| 本阶段完全不实现 | 优：最小交付。劣：ANC-04 与 Phase 27 EVL-01 四臂依赖会断。 | |

**User's choice:** SearchOptions 可组合（推荐）

**Area check:** 进入下一灰区（剩余：锚点来源与生成器、缓存与成本可见、降级与外发披露）。

---

## B. 锚点来源与生成器

### B1. 默认触发 `anchor:` 时锚点由谁产生？

| Option | Description | Selected |
|--------|-------------|----------|
| 零模型规则锚点默认 + LLM 显式 opt-in（推荐） | 优：严格守 PROJECT.md「默认仍是零模型确定性锚点基线」；不开模型即可复现 Phase 25 的 +0.130203 信号；local-first / 零下载 / 零延迟；LLM 生成器作为可选实验臂需显式配置后端才启用。劣：默认臂不是论文意义的 LLM anchor。 | ✓ |
| LLM 生成即 anchor: 默认 | 优：与论文一致。劣：违背 PROJECT.md、默认要下载 1.10GB GGUF、与「默认关闭零构造零模型加载」冲突；Phase 25 已证 0.3.35 加不了 lfm3。 | |
| 两者按 flag 自由切换，无默认 | 优：完全对称。劣：无默认让 `anchor:` 行为不确定，「不加配置跑 anchor:」无法给可复现结果。 | |

**User's choice:** 零模型规则锚点默认 + LLM 显式 opt-in（推荐）
**Notes:** 规则锚点 = query-only 派生（缩写/同义/组合词 + 提交映射表），与 Phase 25 spike 同源。

### B2. GEN-01 冻结 prompt / greedy / ≤10 术语 / 去重 锁在哪一层？

| Option | Description | Selected |
|--------|-------------|----------|
| AnchorGenerator 独立组件 + 显式 chat template（推荐） | 优：prompt version / 清洗 / 去重 / 上限 / temperature 0 集中到单一组件；显式套 Phase 25 已记录的 `tokenizer.chat_template` 避免复读 prompt；不复用 `LlamaCppEmbedder`（embedding=True），单独建 `Llama(..., embedding=False)`。劣：需处理用户自下载 GGUF 路径解析。 | ✓ |
| 复用 create_completion 不套模板 | 优：改动最少。劣：Phase 25 验证器明确记录「原始 completion 无模板会复读 prompt」；LlamaCppEmbedder 实例是 embedding=True。 | |
| prompt / 版本散落在 Settings 字段 | 优：可调。劣：无法保证「评测前冻结」与可复现；prompt 是证据身份的一部分。 | |

**User's choice:** AnchorGenerator 独立组件 + 显式 chat template（推荐）

### B3. 本地 GGUF 后端如何启用？

| Option | Description | Selected |
|--------|-------------|----------|
| 显式 model path + 明确后端 opt-in（推荐） | 优：守「不自动下载」；用户给绝对路径 + 显式选后端才加载；未配置时 `anchor:` 走零模型规则锚点、绝不加载模型；0.3.35 不兼容 lfm3 写进文档（需自备兼容版/隔离环境如 Phase 25）。劣：开箱即用 LLM 体验弱。 | ✓ |
| Settings 配 model_name 即自动加载 | 优：配置即用。劣：易触发隐式下载/加载，违背零构造零模型加载与不自动下载；0.3.35 默认加载会报 unknown architecture。 | |
| 本阶段不接真模型，只留 Protocol/mock | 优：完全避开兼容性坑。劣：GEN-01..04 与 CTR-03 真后端能力无法验证，Phase 27 拿不到真实生成臂。 | |

**User's choice:** 显式 model path + 明确后端 opt-in（推荐）

### B4. `SearchOptions.anchor_terms` 与锚点生成器怎么分工？

| Option | Description | Selected |
|--------|-------------|----------|
| anchor_terms 为唯一注入点（推荐） | 优：守「settings 不绕过 SearchOptions」（与 rrf_k/bm25_weight 同构）；AnchorGenerator 只产出 terms 列表，调用方写进 `SearchOptions.anchor_terms`；评测可显式注入固定 terms 绕开 LLM 保证可复现；`hybrid+anchor` 靠同一字段。劣：生成器与 pipeline 间多一层显式接线。 | ✓ |
| pipeline 内部自己调生成器 | 优：调用方零感知。劣：评测无法固定 terms 注入、无法保证 45 配置 sweep 只生成 N 次、默认路径会隐式加载模型。 | |
| 另外新增 anchor_enabled / anchor_mode 开关字段 | 优：显式。劣：与「flag OR 前缀单一路由」及 ANCHOR SearchType 重复，增加状态组合与字节等价守卫面。 | |

**User's choice:** anchor_terms 为唯一注入点（推荐）

**Area check:** 进入下一灰区（剩余：缓存与成本可见、降级与外发披露）。

---

## C. 缓存与成本可见

### C1. 缓存落在哪？

| Option | Description | Selected |
|--------|-------------|----------|
| 复用 llm_cache + 命名空间（推荐） | 优：零迁移；`LLMCacheRepository` 已提供 get/set(TTL)/clear_expired；研究简报 §5 决策 6 推荐；`model_name` 用 `anchor::<backend>::<model_id>` 命名空间避免混桶；`prompt_hash` 含 prompt_version。劣：llm_cache 会存原始 query 文本（隐私面需披露）。 | ✓ |
| 新建 anchor_cache 表 | 优：物理隔离、可单独清理/统计。劣：新增 schema 迁移 + SchemaManager + 清理路径 + 测试；与最小改动及 CTR-04 90% 门禁叠加；研究简报倾向复用。 | |
| 文件级缓存 | 优：与主 DB 解耦。劣：跨进程命中与 TTL 语义要重写，与已有 llm_cache 重复造轮子。 | |

**User's choice:** 复用 llm_cache + 命名空间（推荐）

### C2. 缓存键包含什么？

| Option | Description | Selected |
|--------|-------------|----------|
| query+model+prompt_version+backend（推荐） | 优：`prompt_hash = sha256(prompt_version + model_id + backend + stripped_query)`，与研究简报 §7.2 一致；冻结 prompt/greedy/去重任一变化自动失效；规则锚点也有稳定 backend 标识。劣：query 需规范化否则同义不同空格会 miss。 | ✓ |
| 仅 query 文本 | 优：键最简单。劣：换模型/换 prompt 版本后静默吃旧锚点，破坏「评测前冻结」与可证伪性；GEN-02 明说要含 model + prompt version。 | |
| query + 完整生成参数字典 | 优：最严谨。劣：把 max_tokens/temperature/stop 全纳入让键脆弱难审计；GEN-01 已把这些冻结为常量。 | |

**User's choice:** query+model+prompt_version+backend（推荐）

### C3. 跨进程命中如何保证？

| Option | Description | Selected |
|--------|-------------|----------|
| SQLite 表本身即跨进程（推荐） | 优：llm_cache 持久化表天然跨进程；与现有 LLMCacheRepository 语义一致；补「同 query 零次生成器调用」测试即可。劣：需注意 WAL/并发写（已有 flock 基础设施）。推荐：不另做进程内缓存避免命中口径分叉。 | ✓ |
| 加进程内 LRU 层 | 优：单进程 sweep 最快。劣：命中统计分内存/DB 两层，Phase 27 调用计数/命中率口径复杂化，有陈旧风险。 | |
| 只要求单进程命中 | 优：实现最松。劣：不同命令/重跑同一 query 会重复生成；不满足「重复同一 query 零调用」成功标准 2 的直觉。 | |

**User's choice:** SQLite 表本身即跨进程（推荐）

### C4. 用户从哪里看到调用数/命中率/查询文本本地留存？

| Option | Description | Selected |
|--------|-------------|----------|
| 结果元数据 + 文档披露，不新增命令（推荐） | 优：本阶段在 --explain/结构化输出或日志暴露本次 generator_calls / cache_hits / anchor_backend；Phase 27 报告汇总；文档明确 llm_cache 存 query 文本、本地留存、可 TTL/清理、sif cleanup 可清、远程 opt-in 才外发。劣：本阶段不做完整报表。 | ✓ |
| 新增 sif anchor status/cache 子命令 | 优：用户可直接查。劣：新增一级命令 + docs 生成面 + 测试；Phase 27 才需要报表。 | |
| 完全不暴露，仅内部计数 | 优：零公开面。劣：GEN-03 要「用户能看到失败原因」、EVL-04 要调用数/命中率；完全不暴露让 Phase 27 拿不到证据。 | |

**User's choice:** 结果元数据 + 文档披露，不新增命令（推荐）

**Area check:** 进入下一灰区（剩余：降级与外发披露）。

---

## D. 降级与外发披露

### D1. 生成器超时/失败 fail-open 回退时用户怎么看到失败原因？

| Option | Description | Selected |
|--------|-------------|----------|
| stderr 单次告警 + explain/结构化字段（推荐） | 优：与 Phase 22 懒加载 embedder「一次告警降级 BM25」一致；默认输出不污染；--explain/结果元数据带 `anchor_fallback_reason`；不抛异常、不重试风暴。劣：静默降级需靠 stderr 可见。 | ✓ |
| 抛 click.ClickException 让命令失败 | 优：错误最响。劣：违背 fail-open「返回原始 query 结果」成功标准 3，生成器挂了搜索就不可用。 | |
| 完全静默回退 | 优：输出最干净。劣：GEN-03 明确「用户能看到失败原因」；无法区分「没启用锚点」与「生成失败了」。 | |

**User's choice:** stderr 单次告警 + explain/结构化字段（推荐）

### D2. 无模型 / 无缓存 / 远程 opt-in 三情形与重试预算？

| Option | Description | Selected |
|--------|-------------|----------|
| 无模型=规则锚点、远程=显式 opt-in、预算护栏（推荐） | 优：未配置后端直接走零模型规则锚点不调生成器；缓存 miss 才调用一次；超时/失败单次 fail-open 不重试；`SIF_ANCHOR_MAX_CALLS` 硬护栏防 45N 次；timeout 可配。劣：需新增几个 Settings 字段（触发 docs-generate）。 | ✓ |
| 所有情形都调生成器再说 | 优：逻辑单一。劣：无模型时会尝试加载/下载，违背零构造零模型加载与 B3；触发重试风暴。 | |
| 失败时有限重试（如 2 次） | 优：容忍瞬时故障。劣：GEN-03 要「无重试风暴」；本地 GGUF 超时重试意义不大且放大延迟成本。 | |

**User's choice:** 无模型=规则锚点、远程=显式 opt-in、预算护栏（推荐）

### D3. GEN-04 远程后端查询文本外发披露做到什么程度？

| Option | Description | Selected |
|--------|-------------|----------|
| 显式开关 + 一次性 stderr 告警 + 文档（推荐） | 优：需显式设置远程后端才生效；启用时 stderr 明确打印「查询文本将发送至 <base_url>」；文档写明 local-first 默认无外部请求、远程外发 query 与锚点、计费与延迟；与 openai/modelscope 现有 disclosure 惯例一致。劣：远程后端本身新增外部面。 | ✓ |
| 仅文档披露 | 优：无运行时开销。劣：配了远程却无运行时提示，容易不知情外发；不满足「明确披露」。 | |
| 交互式确认 | 优：最保险。劣：非 TTY/自动化评测（Phase 27 sweep）会被打断，与非 TTY 静默约定冲突。 | |

**User's choice:** 显式开关 + 一次性 stderr 告警 + 文档（推荐）

### D4. ANC-05 词表守卫默认开还是关、怎么作为独立 A/B 开关暴露？

| Option | Description | Selected |
|--------|-------------|----------|
| 默认关 + 独立布尔开关 + 记录偏离（推荐） | 优：ANC-05 明确「独立 A/B 开关」「默认行为、对论文的偏离与影响均有记录」；默认关不偏离论文/Phase 25 方案；开时丢弃词表外锚点抑制术语幻觉稀释 IDF；开关作显式 Settings/flag（如 `SIF_ANCHOR_VOCAB_GUARD`）不悄悄改变默认。劣：需额外字段 + docs + 测试。 | ✓ |
| 默认开 | 优：更保守。劣：悄悄改变 Phase 25 已验证的 lex→anchor 方案，违反 ANC-05「默认行为、对论文的偏离均有记录」。 | |
| 本阶段不做，留 Phase 27 | 优：最小。劣：ANC-05 是 Phase 26 需求（traceability 明确），推到 Phase 27 会断需求映射。 | |

**User's choice:** 默认关 + 独立布尔开关 + 记录偏离（推荐）

**Done check:** 用户选择 "I'm ready for context"，不再新增灰区，直接生成 CONTEXT.md。

---

## Claude's Discretion

16 题全部采用推荐项，未另行指定细节。Claude（researcher / planner）在锁定决策范围内决定：规则锚点词表格式与 query 规范化、`AnchorGenerator` 模块位置/命名/冻结 prompt 文本与 `PROMPT_VERSION`、chat template 应用方式、`anchor::<backend>::<model_id>` 字面取值、`SIF_ANCHOR_*` 字段精确命名与默认值、`--anchor` 与结果元数据字段命名、`SearchType.ANCHOR` 在前缀映射中的顺序、`llm_cache` 落在哪个 DB / TTL 默认值、远程后端抽象层形状、词表守卫 FTS 查询方式、LFM 许可文档措辞、单测与 90% 覆盖门禁补测方式、45 配置 sweep 成本证明方式、Phase 27 `search_fn` 注入四臂的最小接口形状。详见 `26-CONTEXT.md` 的 Claude's Discretion 段。

## Deferred Ideas

- 四臂正式评测 / `Recall@10` / gain gap / 配对 bootstrap / 0.01 tie rule / held-out verdict —— Phase 27（EVL-01..05）。
- `hybrid+anchor` 升默认、规则锚点升级为默认后端、Qwen3-8B 对照臂、MCP `anchor` 请求字段 —— REQUIREMENTS.md `v1.4+` / ANC-F1..F3。
- 新建 `anchor_cache` / 文件级缓存 / 进程内 LRU / 独立 `sif anchor` 子命令 / 交互式外发确认 / 有限重试 / 词表守卫默认开 —— 明确否决的备选项（见各题表格），非延期功能。
- Web UI / REST / `sif serve`、可写 UI、chat-with-notes —— 推迟 v1.4，Out of Scope 不反转。
- 把 LFM3 GGUF 打进 wheel/sdist 或自动下载、远程后端默认化、改默认 embedder / RRF 权重 / `expand:` PRF —— 既有 Out of Scope / PROJECT.md 锁定。

本轮未提出任何新能力请求，讨论始终留在 Phase 26 范围内。
