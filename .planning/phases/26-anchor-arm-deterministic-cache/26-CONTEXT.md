# Phase 26: Anchor Arm + Deterministic Cache - Context

**Gathered:** 2026-11-28
**Status:** Ready for planning

<domain>
## Phase Boundary

交付默认关闭、可缓存、失败回退的 `anchor:` 检索臂与本地可选生成器：新增 `SearchType.ANCHOR` + `anchor:` 前缀 + `sif search query --anchor`、`SearchOptions.anchor_terms` 注入点、零模型规则锚点基线（默认）、可选 `AnchorGenerator`（冻结 prompt / greedy / ≤10 术语 / 去重 / 显式 chat template / 本地 GGUF 显式 opt-in / 远程 OpenAI-compatible 仅 opt-in）、复用 `llm_cache` 的确定性缓存、fail-open 降级与预算护栏、词表守卫独立 A/B 开关、文档与 Key Decisions 写入 `LFM Open License v1.0` 约束，并满足 `make docs-generate` / 90% coverage / 8-cell CI 门禁。

In scope: ANC-01..05、GEN-01..04、CTR-03、CTR-04。覆盖两处前缀映射同步（`search/hybrid.py` / `mcp/backend.py`）、CLI `--anchor`（仅 `query`）、`SearchOptions.anchor_terms`、`llm_cache` 命名空间复用、结果元数据里的调用数/缓存命中/后端/降级原因、新增 Settings 字段与 generator-owned docs、LFM3 许可与 GGUF 不打包的用户文档与 Key Decisions。

Out of scope: 任何 MCP 请求字段 / 7 工具 / 5 份 wire goldens / `QueryInput` 变更、新增 runtime 依赖、Web UI / REST / `sif serve`、chat-with-notes / ask、自动查询路由 / LLM judge router、改默认 embedder / RRF 权重 / BM25 索引粒度、改造 `expand:` 的 embedding PRF、`hybrid+anchor` 升默认、四臂正式评测与 adopt/keep-default verdict（属 Phase 27）、0.01 tie rule / 10,000 bootstrap / held-out 门禁（属 Phase 27）、把 LFM3 GGUF 打进 wheel/sdist 或自动下载。本阶段无 SPEC.md；范围以 `.planning/ROADMAP.md` §Phase 26 与 `.planning/REQUIREMENTS.md` 为准。

</domain>

<decisions>
## Implementation Decisions

### Locked upstream — do not re-litigate

- v1.3 只做 LLM Anchor；Web UI 推迟 v1.4，`Web UI` 与 `chat-with-notes / ask` 的 Out of Scope 条款不反转（PROJECT.md / REQUIREMENTS.md / Phase 25）。
- LFM3-1.7B-GGUF Q4_K_M 是用户自行下载的可选实验臂，不打进 wheel/sdist、不默认启用、不自动下载（PROJECT.md Key Decisions）。
- **默认仍是零模型确定性锚点基线**（PROJECT.md Key Decisions）。
- MCP 7 工具、5 份 wire goldens、`QueryInput` 不变；不新增 MCP `anchor` 请求字段；零新增 runtime 依赖；`test_packaging.py` 冻结的 13 项核心依赖不变（Phase 25 已逐字节证明）。`anchor:` 走现有 query 字符串前缀透传，不改 MCP schema。
- Phase 25 判定 `directional-signal`，Phases 26/27 解锁；主 pin `llama-cpp-python==0.3.35` 不变（隔离 0.3.37 仅为证据）；**Phase 26 生成器应显式应用 chat template**（Phase 25 验证器记录：原始 completion 无模板会复读 prompt）。
- 锚点仅注入 BM25 腿并 prepend 到查询；snippet 与 highlight 仍使用原始查询（ANC-02）；`hybrid+anchor` 仅作为诊断臂、默认关闭、不替换默认 RRF 的 BM25 腿（ANC-04）；settings 不绕过 `SearchOptions`（ANC-03 既有约定）。
- Phase 18/23/24 的 0.01 tie rule、10,000 次 bootstrap、held-out、N / `1/N` 噪声地板属于 Phase 27 的正式门禁；本阶段不提前消费。

### A. 触发面与臂语义（ANC-01 / ANC-03 / ANC-04）

- **D-01:** `anchor:` 作为独立 `SearchType.ANCHOR` 时走**纯 BM25 腿** —— `ANCHOR = BM25(原 query + 锚点)` 单腿，与 `lex:` 同粒度；注入仅发生在 FTS MATCH 构造前，不触及向量腿。理由：贴近论文「LLM anchors 让 BM25 +0.11–0.19」、与 Phase 25 的 `lex:` → `anchor:` 配对 spike 同构。 — **Reversibility:** costly — 若改成 hybrid 或双腿注入，ANC-02「仅注入 BM25 腿」与已冻结的 Phase 25 配对 delta 口径都会失效，需重跑信号证据。
- **D-02:** `--anchor` CLI flag **仅加在 `sif search query` 命令**，与 `--rerank` 并列。`search`(BM25) 与 `vsearch`(vector) 保持纯基线，其余入口靠 `anchor:` 前缀。理由：`query` 是推荐的 hybrid/pipeline 命令；`search` 是刻意保留的纯 lex 基线。 — **Reversibility:** reversible — 加 flag 是 additive CLI 面。
- **D-03:** `--anchor` flag 与 `anchor:` 前缀**等价、单一路由**：二者都只是「以 ANCHOR 模式跑该 query」的入口开关，同时出现时不重复注入、不叠加两遍锚点；与现有 `_parse_query_prefix` 只匹配第一个前缀的行为一致；`anchor:lex:foo` 视为 query 字面文本、不二次解析。 — **Reversibility:** reversible — 路由判定局部。
- **D-04:** `hybrid+anchor` 诊断臂（ANC-04）本阶段以 **`SearchOptions` 可组合**形式交付：给 `SearchOptions` 加 `anchor_terms` 字段（ANC-03 点名），使「注入锚点的 BM25 腿 + 原 hybrid 向量腿」可由评测代码组合出来；默认全关，`anchor:` 仍走纯 BM25。本阶段只交付可组合底层能力 + 冻结的 arm 定义，四臂评测 / verdict 留 Phase 27。不新增独立 CLI 子命令。 — **Reversibility:** costly — `SearchOptions` 是 CLI/MCP/pipeline 共享的 dataclass，字段形状决定 Phase 27 的 `search_fn` 注入接口。

### B. 锚点来源与生成器（GEN-01 / GEN-04 / ANC-03）

- **D-05:** 默认触发 `anchor:` 时锚点由**零模型规则锚点**产生（query-only 派生：缩写 / 同义 / 组合词 + 提交的映射表，与 Phase 25 spike 同源），**LLM 生成器是显式 opt-in 后端**。理由：严格守 PROJECT.md「默认仍是零模型确定性锚点基线」、不开模型即可复现 Phase 25 的 +0.130203 信号、local-first / 零下载 / 零延迟；GEN-01..04 描述的是可选实验臂。 — **Reversibility:** costly — 若默认改成 LLM 生成，会违背已发布的 Key Decision、触发默认模型加载，且与 ROADMAP 成功标准 1「关闭 flag 时零构造零模型加载」冲突，需重开范围决策。
- **D-06:** `AnchorGenerator` 为**独立组件**，把冻结 prompt（带版本号）、greedy / temperature 0、每行一个术语、最多 10 个、去重、失败/超时处理集中于此；**显式套用 Phase 25 已记录的 `tokenizer.chat_template`** 避免复读 prompt；不复用 `LlamaCppEmbedder`（它是 `Llama(..., embedding=True)`），需要时自建 `Llama(..., embedding=False)` 实例。prompt / 版本是评测身份的一部分，不散落为可变 Settings 字段。 — **Reversibility:** costly — prompt version 决定缓存键与 Phase 27 证据可复现性；改动需失效全部缓存并重跑评测。
- **D-07:** 本地 GGUF 后端以**显式 model path + 明确后端 opt-in** 启用：用户给本地 GGUF 绝对路径并显式选 generator 后端才加载；未配置时 `anchor:` 走零模型规则锚点、绝不尝试加载或下载模型；锁定的 0.3.35 无法加载 `lfm3` 的事实写进用户文档（需用户自备兼容版本 / 隔离环境，如 Phase 25 证据）。 — **Reversibility:** reversible — 后端启用面是配置层。
- **D-08:** `anchor_terms` 是**唯一注入点**（守「settings 不绕过 `SearchOptions`」约定，与 `rrf_k` / `bm25_weight` 同构）：`AnchorGenerator` 只产出 terms 列表，调用方写进 `SearchOptions.anchor_terms`；评测可显式注入固定 terms 绕开 LLM 以保证可复现；`hybrid+anchor` 诊断臂靠同一字段。不新增 `anchor_enabled` / `anchor_mode` 之类开关字段（与 ANCHOR SearchType + flag/前缀单一路由重复）。 — **Reversibility:** costly — 与 D-04 同一 `SearchOptions` 契约面。

### C. 缓存与成本可见（GEN-02 / CTR-03）

- **D-09:** 缓存**复用 `llm_cache` + 命名空间**，不新建 `anchor_cache` 表、不做文件级缓存。理由：零迁移、`LLMCacheRepository.get/set(TTL)/clear_expired` 已存在、`sif cleanup` 已接清理、研究简报 §5 决策 6 推荐。`model_name` 用 `anchor::<backend>::<model_id>` 命名空间避免与现有 LLM 响应混桶。 — **Reversibility:** one-way — 缓存一旦写入用户主 DB，换成独立表需要迁移既有条目与清理口径，且会改变 `sif cleanup` 的已发布行为。
- **D-10:** 缓存键 = **query + model + prompt version + backend**：`prompt_hash = sha256(prompt_version + model_id + backend + stripped_query)`（研究简报 §7.2 口径）；冻结 prompt / greedy / 去重任一变化自动失效缓存；query 需规范化（strip boilerplate）否则同义不同空格会 miss；规则锚点（零模型）也有稳定 backend 标识。 — **Reversibility:** costly — 键形状决定「同一 query 零调用」与 45 配置 sweep「N 条查询只生成 N 次」的证据；改键需重跑成本证明。
- **D-11:** **SQLite 表本身即跨进程命中**：`llm_cache` 持久化表天然跨进程读写，不另加进程内 LRU（避免命中口径分叉与陈旧风险）；补一个「同 query 零次生成器调用」测试证明；注意 WAL / 并发写（项目已有 flock 跨进程锁基础设施）。 — **Reversibility:** reversible — 命中口径局部。
- **D-12:** 成本可见性用**结果元数据 + 文档披露，不新增命令**：本阶段在 `--explain` / 结构化输出或日志里暴露本次 `generator_calls` / `cache_hits` / `anchor_backend` / `anchor_fallback_reason`；Phase 27 的评测报告汇总调用数与缓存命中率（EVL-04）；文档明确 `llm_cache` 会保存查询文本、本地留存、可 TTL/清理、`sif cleanup` 可清、远程 opt-in 才会外发。不新增 MCP 字段、不新增 `sif anchor status/cache` 子命令。 — **Reversibility:** reversible — additive 输出面。

### D. 降级与外发披露（GEN-03 / GEN-04 / ANC-05）

- **D-13:** 生成器超时 / 失败时 **stderr 单次告警 + `--explain`/结构化字段** 暴露 `anchor_fallback_reason`，fail-open 回退原 query 结果、不抛异常、**不重试风暴**。理由：与 Phase 22 懒加载 embedder「一次告警降级 BM25」模式一致；默认路径（非 TTY 纯文本 / JSON）输出不污染；GEN-03 要求「用户能看到失败原因」。 — **Reversibility:** reversible — 告警与元数据局部。
- **D-14:** 三种情形与预算护栏：未配置后端（无模型）→ 直接走零模型规则锚点、**根本不调用生成器**；缓存 miss 才调用一次；远程 OpenAI-compatible 后端必须**显式 opt-in**；超时 / 失败单次 fail-open 不重试。新增 `SIF_ANCHOR_TIMEOUT_MS` 类超时配置与 `SIF_ANCHOR_MAX_CALLS` 硬护栏（超预算直接报错，防 45N 次生成）。 — **Reversibility:** costly — `SIF_ANCHOR_MAX_CALLS` 是 ROADMAP 成功标准 2 的成本证据守门；移除会让 sweep 放大成本。
- **D-15:** 远程后端的「查询文本外发」披露 = **显式开关 + 一次性 stderr 告警 + 文档**：需显式设置远程后端才生效；启用时在 stderr 明确打印「查询文本将发送至 `<base_url>`」；文档写明 local-first 默认无外部请求、远程会外发 query 与锚点、计费与延迟。不做交互式确认（会打断 Phase 27 非 TTY sweep），也不只靠文档。 — **Reversibility:** reversible — 披露面局部。
- **D-16:** ANC-05 词表守卫（丢弃 FTS 词表外锚点，抑制术语幻觉稀释 IDF）**默认关 + 独立布尔开关**（如 `SIF_ANCHOR_VOCAB_GUARD`）+ 记录偏离：默认关 = 不偏离论文 / Phase 25 方案；开关是显式 Settings/flag，作为独立 A/B 暴露，不悄悄改变默认；文档记录默认行为、对论文的偏离与影响。 — **Reversibility:** reversible — A/B 开关 additive。

### Claude's Discretion

用户 16 题全部选择推荐项，未另行指定细节。以下执行细节留给 researcher / planner 在锁定决策范围内决定：

- 规则锚点映射表的文件格式、具体词条、派生规则、query 规范化（`stripped_query`）的精确定义；CJK 与 porter 词表守卫的交互。
- `AnchorGenerator` 的模块位置、类/方法命名、冻结 prompt 的具体文本与 `PROMPT_VERSION` 字面值、`tokenizer.chat_template` 的应用方式、`max_tokens` 上限、`temperature=0` 的传参。
- `anchor::<backend>::<model_id>` 中 backend / model_id 的字面取值；规则锚点基线的 backend 标识命名；`prompt_hash` 的拼接分隔与编码。
- 新增 Settings 字段的精确命名（`SIF_ANCHOR_*`）、默认值、类型校验位置；`--anchor` flag 的 Click 拼写与 help 文本；`--explain` / 结构化结果里 `generator_calls` / `cache_hits` / `anchor_backend` / `anchor_fallback_reason` 的字段命名、是否进入 JSON 输出。
- `SearchType.ANCHOR` 在两处前缀映射中的顺序；`--anchor` 与 `anchor:` 同时出现时「不重复注入」的具体实现；`SearchOptions.anchor_terms` 的类型（`list[str] | None`）与 `dataclasses.replace` 扇出行为。
- `llm_cache` 复用时缓存落在主 DB 还是 embeddings_cache.db、TTL 默认值、并发写的具体处理；`sif cleanup` 的既有路径是否需扩展说明。
- `AnchorGenerator` 与远程 OpenAI-compatible 后端的抽象层形状（Protocol / 工厂）、本地 `Llama(..., embedding=False)` 实例的生命周期与释放。
- 词表守卫的 FTS 词表查询方式；LFM Open License v1.0 在用户文档与 PROJECT.md Key Decisions 里的具体落点措辞；generator-owned docs 的重生成命令。
- `AnchorGenerator` 独立组件、`anchor:` 前缀透传（MCP）、fail-open 回退、缓存命中、预算护栏的单元测试/回归测试的命名与夹具组织；90% coverage 门禁的补测方式。
- `bench --sweep`（45 配置）如何验证「N 条查询只生成 N 次」；Phase 27 `search_fn` 注入四臂所需的最小接口形状（只留可组合能力，不实现评测）。

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Scope and requirements

- `.planning/ROADMAP.md` §Phase 26 — goal, ANC-01..05 / GEN-01..04 / CTR-03..04, 五条 success criteria（逐字节默认路径、零重复生成、fail-open、无外发、docs/90%/8-cell 门禁 + LFM 许可）
- `.planning/REQUIREMENTS.md` — v1.3 Requirements（ANC / GEN / CTR / EVL 分组）、Out of Scope、Traceability（ANC/GEN/CTR→Phase 26，EVL→Phase 27）
- `.planning/PROJECT.md` — Current Milestone v1.3、Target features、Key Decisions（LFM3 定位 / 零模型确定性基线 / 止损 / 契约 / v1.3 范围与模型定位）、Constraints、Out of Scope
- `.planning/STATE.md` — current position（Phase 26 ready to plan）、Phase 25 累积决策、session continuity
- `.planning/config.json` — `workflow.auto_advance`, `workflow.discuss_mode`, `workflow.text_mode`, `mode: yolo`, `workflow.research`, `workflow.plan_check`

### Research basis（代码勘察与契约判断仍适用，UI 部分已推迟 v1.4）

- `.planning/v1.3-ui-anchor-milestone-research.md` — §4.2 ANC-01..05 / GEN / 成本预算、§5 决策表（决策 4 anchor 不进 MCP、决策 6 复用 llm_cache）、§7.2 Anchor 边界（两处前缀同步、chat template、缓存键、snippet 用原 query）、§7.3 共享门禁、§8 风险与止损；其 5-phase / UI 结构已被 3-phase roadmap 取代
- `.planning/research/UI-FRONTEND.md` — v1.3 研究基础之一；Web UI 部分已推迟 v1.4，不作为本阶段范围
- `/Users/forrest/Downloads/SIF-LLM-Anchor-Implementation-Guide.md` — LLM Anchor 论文/实现指南；模型推荐 Qwen3.5-4B 已被 PROJECT.md 的 LFM3 决策取代，评测纪律与 cache/PRF 边界仍适用（workspace-external）

### Prior phase decisions and artifact conventions

- `.planning/phases/25-contract-freeze-feasibility-spike/25-CONTEXT.md` — D-01..D-16：spike 纪律、query-only 规则锚点、契约冻结基线、chat template 遗留提示、Claude's Discretion
- `.planning/phases/25-contract-freeze-feasibility-spike/25-VERIFICATION.md`、`25-CONTRACT-FREEZE.md`、`bench/spike-verdict.json`、`bench/spike-delta.csv` — `directional-signal` 判定（+0.130203，helped 6/hurt 0，36 tuning-only 查询）、契约冻结证据
- `.planning/phases/25-contract-freeze-feasibility-spike/25-DISCUSSION-LOG.md` — 16 题备选项与优劣（中文讨论惯例）
- `.planning/milestones/v1.2-phases/22-mcp-sdk-v2-modernization-agent-packaging/22-CONTEXT.md` — 7 只读工具、5 wire goldens、冻结 envelope、懒加载 embedder 一次告警降级 BM25（D-15/D-17）、`QueryInput` 契约
- `.planning/milestones/v1.2-phases/23-harrier-gated-evaluation/23-CONTEXT.md` — 隔离双臂、identity、verdict artifact、keep-default、held-out 门禁（Phase 27 用）
- `.planning/milestones/v1.2-phases/24-tuning-models-ux-install-docs/24-CONTEXT.md` — held-out gate、scratch/artifact 惯例、generator-owned docs、`make docs-generate`
- `.planning/milestones/v1.2-phases/18-quality-instrument-personal-bench-rapidfuzz-dym/18-CONTEXT.md` — 0.01 tie rule / 10,000 bootstrap / saved-run 纪律（Phase 27 用）
- `docs/benchmarking.md` — held-out 证据与 verdict 记录风格

### Code anchors（当前 `src/sif/` 实测，2026-11-28）

- `src/sif/core/models.py:84` — `SearchType` 枚举（现为 BM25/VECTOR/HYBRID/HYDE/EXPAND，无 ANCHOR）
- `src/sif/core/models.py:348` — `SearchOptions` dataclass（`filter` / `rrf_k` / `bm25_weight` / `vector_weight` / `title_weight` 等字段与「settings 不绕过 SearchOptions」约定）
- `src/sif/search/hybrid.py:528` / `:535` — `SearchPipeline._parse_query_prefix` 与 `prefix_map`（`lex:`/`vec:`/`hyde:`/`expand:`）；`:311` `search()` 的 BM25/VECTOR/HYDE/hybrid 路由与 single enrich exit；`:391` expand 分支
- `src/sif/mcp/backend.py:124` — `_PREFIX_ROUTES`（须与 `prefix_map` 同步）；`:137` `_split_query_prefix`（prefix-first 先于模型加载决策）；`:445` BM25 degrade 路径
- `src/sif/search/benchmark.py:27` / `:364` — 45 配置 `SWEEP_GRID` / `rank_sweep`（GEN-02「45 配置 sweep 只生成 N 次」的参照）
- `src/sif/cli/commands/search.py:614` / `:822` / `:1065` — `search`(BM25) / `vsearch`(vector) / `query`(hybrid) 三个子命令；`:1159` `query_cmd` 的 `SearchOptions` 构建与 flag 列表（`--rerank` / `--intent` 等）
- `src/sif/database/repositories.py:622` — `LLMCacheRepository.get/set/clear_expired`（TTL 与 instant 比较语义）
- `src/sif/database/schema.py:264` / `:787` — `llm_cache` 表与 `idx_llm_cache_lookup(model_name, prompt_hash)`
- `src/sif/cli/main.py:274` — `sif cleanup` 调 `LLMCacheRepository.clear_expired()`
- `src/sif/embedding/embedder.py:345` / `:437` — `LlamaCppEmbedder` 的 `Llama(..., embedding=True)` 与 `create_completion()`（生成接口形状参考，但不可直接复用实例）
- `src/sif/config/settings.py:165` — `rerank_enabled` 等 opt-in 字段范式与 `SIF_` 前缀；`:439` `resolve_candidate_limit` 解析范式
- `Makefile:73` / `scripts/generate_cli_ref.py` / `scripts/generate_config_ref.py` — `make docs-generate` 与 docs CI diff gate
- `tests/unit/mcp/test_wire_transcripts.py` + `tests/unit/mcp/goldens/*.json` — 5 份冻结 wire goldens（本阶段零改动）
- `tests/unit/mcp/test_packaging.py` — 13 项 runtime 依赖冻结断言（本阶段零改动）
- `pyproject.toml` / `uv.lock` — `llama-cpp-python==0.3.35` 锁定、coverage `fail_under = 90`

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets

- `LLMCacheRepository` + `llm_cache` 表：已有 `get(model_name, prompt_hash)` / `set(..., ttl_seconds=...)` / `clear_expired()`，TTL 按 instant 比较、清理走 bounded batch，`sif cleanup` 已接线 —— 缓存零迁移即可复用。
- `SearchPipeline._parse_query_prefix` / `prefix_map` 与 `SearchBackend._PREFIX_ROUTES` / `_split_query_prefix`：两处前缀解析同构、prefix-first 先于模型加载决策，是加 `anchor:` 的现成落点。
- `LlamaCppEmbedder.create_completion()`：生成接口的形状参考（HyDE 已用 `hasattr(embedder, "create_completion")` 模式）；但实例是 `embedding=True`，`AnchorGenerator` 需自建 `Llama(..., embedding=False)`。
- `SearchOptions` dataclass + `dataclasses.replace` 扇出：加 `anchor_terms` 字段后可自动贯穿 hybrid 双腿 / CLI / MCP，无需新增开关字段。
- `sif search query`（`query_cmd`）：已有 flag 优先于 setting 的 `SearchOptions` 构建范式（`flag > SIF_ setting > default`），`--anchor` 与 `--rerank` 并列接入。
- `sif cleanup` 的 `LLMCacheRepository.clear_expired()`：查询文本本地留存 / TTL / 清理的现成用户面。
- Phase 22 懒加载 embedder 的「一次 stderr 告警 + 降级 BM25 + 失败锁存」模式：fail-open 告警直接类比。
- `make docs-generate` + `tests/test_docs.py`：新增 Settings / CLI 字段的 generator-owned docs 门禁。
- 25/23/24 的 phase-dir `bench/*.json` + `*-CONTEXT.md` + `*-DISCUSSION-LOG.md`：证据 artifact 与讨论日志的现成排版惯例。

### Established Patterns

- 零新增 runtime 依赖；`pyproject.toml` / `uv.lock` / 13 项核心依赖冻结；MCP 7 工具 / 5 goldens / `QueryInput` 冻结。
- 默认路径 byte-identical：不加 `anchor:` / `--anchor` 时与 v1.2.5 逐字节一致、零构造零模型加载；新行为全部 opt-in / 默认关。
- prefix-first 路由：`lex:` 等显式前缀先于任何模型加载决策；`anchor:` 须同构，不触发隐式模型加载。
- CLI 错误用 `click.ClickException`；日志到 stderr、logger 前缀 `sif`；非 TTY 输出保持纯文本 / JSON，告警不污染 stdout。
- `Settings` 不绕过 `SearchOptions`：CLI flag / MCP 请求 / 配置解析都写进 `SearchOptions` 字段，pipeline 只读 options。
- generator-owned docs（`docs/cli-reference.md` / `docs/configuration.md`）绝不手改，靠 `make docs-generate` 重生成且 CI diff 为 0；hand-maintained 文档（用户文档、changelog）单独维护。
- scratch / 一次性脚本放 gitignored `.planning/tmp/`；提交的只是代码、测试、文档与 phase 目录 artifact。
- STATE.md / ROADMAP.md 不直接编辑；会话与状态变化走 `gsd_run`。
- 新增 `src/sif` Python 代码自动纳入 `fail_under = 90`；8-cell CI（py3.10–3.13 × ubuntu/macos）全绿。

### Integration Points

- `src/sif/core/models.py`: `SearchType.ANCHOR` 枚举值 + `SearchOptions.anchor_terms` 字段。
- `src/sif/search/hybrid.py` `prefix_map` + `src/sif/mcp/backend.py` `_PREFIX_ROUTES`: 两处同步加 `anchor:`（MCP 仅透传前缀、不新增请求字段）。
- `src/sif/search/hybrid.py` `SearchPipeline.search()`: ANCHOR 分支走 BM25 腿，锚点 prepend 到 FTS MATCH query；snippet/highlight 仍用 `parsed_query`。
- `src/sif/cli/commands/search.py` `query_cmd`: `--anchor` flag 解析进 `SearchOptions.anchor_terms`（配合 `AnchorGenerator` 或规则锚点）。
- `src/sif/config/settings.py`: 新增 `SIF_ANCHOR_*` opt-in 字段（timeout / max_calls / vocab_guard / model path / backend 等），并经 `make docs-generate` 重生成 `docs/configuration.md`。
- `src/sif/database/repositories.py` `LLMCacheRepository` + `llm_cache`: 命名空间 `anchor::<backend>::<model_id>` 读写缓存；`sif cleanup` 复用既有清理。
- 新增 `AnchorGenerator`（建议 `src/sif/search/` 或 `src/sif/embedding/` 下的独立模块）：冻结 prompt / chat template / 本地 GGUF（`Llama(..., embedding=False)`）/ 远程 OpenAI-compatible opt-in。
- `docs/`: `make docs-generate` 覆盖新 flag / Settings；hand-maintained 文档写入 experimental / 默认关闭 / 成本 / 隐私 / `LFM Open License v1.0` §5（$10M 营收阈值）与再分发义务；`PROJECT.md` Key Decisions 增行。
- `.planning/phases/26-anchor-arm-deterministic-cache/`: `26-CONTEXT.md` / `26-DISCUSSION-LOG.md` / 后续 `26-*-PLAN.md` / `26-*-SUMMARY.md` / 可能的 `bench/*.json`。

</code_context>

<specifics>
## Specific Ideas

- Phase 25 实测：`llama-cpp-python 0.3.35` 报 `unknown model architecture: 'lfm3'`；隔离 venv 的 `0.3.37` 用纯 `Llama(model_path=...)` 加载用户提供的 `LFM3-1.7B-Q4_K_M.gguf` 并产出非空 greedy 文本，两版本 `.embed` 均为 1024 维，现有 GGUF embed/rerank 路径不受影响。**主 pin 不变**；验证器明确提示原始 completion 未套 chat template 时会复读 prompt —— 本阶段生成器必须显式套模板（D-06）。
- Phase 25 信号证据：query-only 规则锚点在 36 条 tuning-only 查询上平均 paired nDCG@10 **+0.130203**、helped 6 / hurt 0 / unchanged 30、噪声下限 `1/36 = 0.027778`、固定种子重跑一致，判定 `directional-signal`。本阶段默认零模型规则锚点与此同源（D-05），Phase 27 才用 0.01 + bootstrap + held-out 门禁决定默认（不提前消费）。
- 缓存键建议（研究简报 §7.2）：`model_name = "anchor::<backend>::<model_id>"`，`prompt_hash = sha256(PROMPT_VERSION + model_id + backend + strip_boilerplate(query))`，`prompt` 存清洗后 query，`response` 存 anchors JSON（D-09/D-10）。
- 成本预算（研究简报 §4.2）：`SIF_ANCHOR_ENABLED=0`、`SIF_ANCHOR_MAX_TERMS=10`、`SIF_ANCHOR_TIMEOUT_MS`、`SIF_ANCHOR_MAX_CALLS`；`bench --sweep` 必须命中缓存，N 条查询只生成 N 次（D-14）。
- 当前 `prefix_map` / `_PREFIX_ROUTES` 都只有 `lex:` / `vec:` / `hyde:` / `expand:`；仓库内无 `anchor:` / `SearchType.ANCHOR` / `SIF_ANCHOR_*` 实现。
- 词表守卫定位：丢弃 FTS 词表外锚点以抑制术语幻觉稀释 IDF，但**作为独立 A/B、默认关**，且不得悄悄改变论文 / Phase 25 方案（D-16；研究简报 §8 风险行）。
- 16 个讨论题全部采用推荐项；每题备选项与优劣记录在 `26-DISCUSSION-LOG.md`。讨论沿用 Phase 25 的中文惯例（response_language 未显式配置，用户此前要求中文讨论）。

</specifics>

<deferred>
## Deferred Ideas

- 四臂正式评测（`lex` / `anchor` / `hybrid` / `hybrid+anchor`）、`Recall@10`、`vec:` + anchor gain gap、配对 bootstrap / 0.01 tie rule / held-out `adopt` vs `keep-default` verdict —— 属 Phase 27（EVL-01..05）；本阶段只留可组合底层能力。
- `hybrid+anchor` 升默认、把规则锚点基线升级为默认后端、Qwen3-8B 级对照臂、MCP `anchor` 请求字段 —— REQUIREMENTS.md `v1.4+` / ANC-F1..F3，需单列契约变更阶段并更新 5 份 wire goldens。
- 新建 `anchor_cache` 独立表、文件级缓存、进程内 LRU 层 —— 明确否决的备选项（D-09/D-11），不是延期功能；理由见 `26-DISCUSSION-LOG.md`。
- 独立 `sif anchor status/cache` 子命令、交互式外发确认、生成器有限重试、词表守卫默认开 —— 明确否决的备选项（D-12/D-15/D-14/D-16）。
- Web UI / REST / `sif serve`、可写 UI、服务层抽取、SPA、chat-with-notes —— 推迟 v1.4，Out of Scope 条款不反转。
- 把 LFM3 GGUF 打进 wheel/sdist 或自动下载、远程后端作为默认、改默认 embedder / RRF 权重 / `expand:` PRF —— 既有 Out of Scope / PROJECT.md 锁定。

本轮未提出任何新能力请求，讨论始终留在 Phase 26 范围内。

</deferred>

---

*Phase: 26-Anchor Arm + Deterministic Cache*
*Context gathered: 2026-11-28*
