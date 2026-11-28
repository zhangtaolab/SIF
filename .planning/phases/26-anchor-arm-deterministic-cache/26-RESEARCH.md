# Phase 26: Anchor Arm + Deterministic Cache - Research

**Researched:** 2026-11-28
**Domain:** 单腿 BM25 的锚点扩展（`anchor:` 检索臂）、零模型规则锚点、可选本地/远程生成器、`llm_cache` 复用、fail-open 与预算护栏
**Confidence:** HIGH（in-repo 契约面、FTS5 行为、0.3.37 生成 API、缓存语义均已本会话实测/读源）；MEDIUM（远程后端与真实 GGUF 端到端未在本机跑通）

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Locked upstream — do not re-litigate**

- v1.3 只做 LLM Anchor；Web UI 推迟 v1.4，`Web UI` 与 `chat-with-notes / ask` 的 Out of Scope 条款不反转（PROJECT.md / REQUIREMENTS.md / Phase 25）。
- LFM3-1.7B-GGUF Q4_K_M 是用户自行下载的可选实验臂，不打进 wheel/sdist、不默认启用、不自动下载（PROJECT.md Key Decisions）。
- **默认仍是零模型确定性锚点基线**（PROJECT.md Key Decisions）。
- MCP 7 工具、5 份 wire goldens、`QueryInput` 不变；不新增 MCP `anchor` 请求字段；零新增 runtime 依赖；`test_packaging.py` 冻结的 13 项核心依赖不变（Phase 25 已逐字节证明）。`anchor:` 走现有 query 字符串前缀透传，不改 MCP schema。
- Phase 25 判定 `directional-signal`，Phases 26/27 解锁；主 pin `llama-cpp-python==0.3.35` 不变（隔离 0.3.37 仅为证据）；**Phase 26 生成器应显式应用 chat template**（Phase 25 验证器记录：原始 completion 无模板会复读 prompt）。
- 锚点仅注入 BM25 腿并 prepend 到查询；snippet 与 highlight 仍使用原始查询（ANC-02）；`hybrid+anchor` 仅作为诊断臂、默认关闭、不替换默认 RRF 的 BM25 腿（ANC-04）；settings 不绕过 `SearchOptions`（ANC-03 既有约定）。
- Phase 18/23/24 的 0.01 tie rule、10,000 次 bootstrap、held-out、N / `1/N` 噪声地板属于 Phase 27 的正式门禁；本阶段不提前消费。

**A. 触发面与臂语义（ANC-01 / ANC-03 / ANC-04）**

- **D-01:** `anchor:` 作为独立 `SearchType.ANCHOR` 时走**纯 BM25 腿** —— `ANCHOR = BM25(原 query + 锚点)` 单腿，与 `lex:` 同粒度；注入仅发生在 FTS MATCH 构造前，不触及向量腿。理由：贴近论文「LLM anchors 让 BM25 +0.11–0.19」、与 Phase 25 的 `lex:` → `anchor:` 配对 spike 同构。 — **Reversibility:** costly — 若改成 hybrid 或双腿注入，ANC-02「仅注入 BM25 腿」与已冻结的 Phase 25 配对 delta 口径都会失效，需重跑信号证据。
- **D-02:** `--anchor` CLI flag **仅加在 `sif search query` 命令**，与 `--rerank` 并列。`search`(BM25) 与 `vsearch`(vector) 保持纯基线，其余入口靠 `anchor:` 前缀。理由：`query` 是推荐的 hybrid/pipeline 命令；`search` 是刻意保留的纯 lex 基线。 — **Reversibility:** reversible — 加 flag 是 additive CLI 面。
- **D-03:** `--anchor` flag 与 `anchor:` 前缀**等价、单一路由**：二者都只是「以 ANCHOR 模式跑该 query」的入口开关，同时出现时不重复注入、不叠加两遍锚点；与现有 `_parse_query_prefix` 只匹配第一个前缀的行为一致；`anchor:lex:foo` 视为 query 字面文本、不二次解析。 — **Reversibility:** reversible — 路由判定局部。
- **D-04:** `hybrid+anchor` 诊断臂（ANC-04）本阶段以 **`SearchOptions` 可组合**形式交付：给 `SearchOptions` 加 `anchor_terms` 字段（ANC-03 点名），使「注入锚点的 BM25 腿 + 原 hybrid 向量腿」可由评测代码组合出来；默认全关，`anchor:` 仍走纯 BM25。本阶段只交付可组合底层能力 + 冻结的 arm 定义，四臂评测 / verdict 留 Phase 27。不新增独立 CLI 子命令。 — **Reversibility:** costly — `SearchOptions` 是 CLI/MCP/pipeline 共享的 dataclass，字段形状决定 Phase 27 的 `search_fn` 注入接口。

**B. 锚点来源与生成器（GEN-01 / GEN-04 / ANC-03）**

- **D-05:** 默认触发 `anchor:` 时锚点由**零模型规则锚点**产生（query-only 派生：缩写 / 同义 / 组合词 + 提交的映射表，与 Phase 25 spike 同源），**LLM 生成器是显式 opt-in 后端**。理由：严格守 PROJECT.md「默认仍是零模型确定性锚点基线」、不开模型即可复现 Phase 25 的 +0.130203 信号、local-first / 零下载 / 零延迟；GEN-01..04 描述的是可选实验臂。 — **Reversibility:** costly — 若默认改成 LLM 生成，会违背已发布的 Key Decision、触发默认模型加载，且与 ROADMAP 成功标准 1「关闭 flag 时零构造零模型加载」冲突，需重开范围决策。
- **D-06:** `AnchorGenerator` 为**独立组件**，把冻结 prompt（带版本号）、greedy / temperature 0、每行一个术语、最多 10 个、去重、失败/超时处理集中于此；**显式套用 Phase 25 已记录的 `tokenizer.chat_template`** 避免复读 prompt；不复用 `LlamaCppEmbedder`（它是 `Llama(..., embedding=True)`），需要时自建 `Llama(..., embedding=False)` 实例。prompt / 版本是评测身份的一部分，不散落为可变 Settings 字段。 — **Reversibility:** costly — prompt version 决定缓存键与 Phase 27 证据可复现性；改动需失效全部缓存并重跑评测。
- **D-07:** 本地 GGUF 后端以**显式 model path + 明确后端 opt-in** 启用：用户给本地 GGUF 绝对路径并显式选 generator 后端才加载；未配置时 `anchor:` 走零模型规则锚点、绝不尝试加载或下载模型；锁定的 0.3.35 无法加载 `lfm3` 的事实写进用户文档（需用户自备兼容版本 / 隔离环境，如 Phase 25 证据）。 — **Reversibility:** reversible — 后端启用面是配置层。
- **D-08:** `anchor_terms` 是**唯一注入点**（守「settings 不绕过 `SearchOptions`」约定，与 `rrf_k` / `bm25_weight` 同构）：`AnchorGenerator` 只产出 terms 列表，调用方写进 `SearchOptions.anchor_terms`；评测可显式注入固定 terms 绕开 LLM 以保证可复现；`hybrid+anchor` 诊断臂靠同一字段。不新增 `anchor_enabled` / `anchor_mode` 之类开关字段（与 ANCHOR SearchType + flag/前缀单一路由重复）。 — **Reversibility:** costly — 与 D-04 同一 `SearchOptions` 契约面。

**C. 缓存与成本可见（GEN-02 / CTR-03）**

- **D-09:** 缓存**复用 `llm_cache` + 命名空间**，不新建 `anchor_cache` 表、不做文件级缓存。理由：零迁移、`LLMCacheRepository.get/set(TTL)/clear_expired` 已存在、`sif cleanup` 已接清理、研究简报 §5 决策 6 推荐。`model_name` 用 `anchor::<backend>::<model_id>` 命名空间避免与现有 LLM 响应混桶。 — **Reversibility:** one-way — 缓存一旦写入用户主 DB，换成独立表需要迁移既有条目与清理口径，且会改变 `sif cleanup` 的已发布行为。
- **D-10:** 缓存键 = **query + model + prompt version + backend**：`prompt_hash = sha256(prompt_version + model_id + backend + stripped_query)`（研究简报 §7.2 口径）；冻结 prompt / greedy / 去重任一变化自动失效缓存；query 需规范化（strip boilerplate）否则同义不同空格会 miss；规则锚点（零模型）也有稳定 backend 标识。 — **Reversibility:** costly — 键形状决定「同一 query 零调用」与 45 配置 sweep「N 条查询只生成 N 次」的证据；改键需重跑成本证明。
- **D-11:** **SQLite 表本身即跨进程命中**：`llm_cache` 持久化表天然跨进程读写，不另加进程内 LRU（避免命中口径分叉与陈旧风险）；补一个「同 query 零次生成器调用」测试证明；注意 WAL / 并发写（项目已有 flock 跨进程锁基础设施）。 — **Reversibility:** reversible — 命中口径局部。
- **D-12:** 成本可见性用**结果元数据 + 文档披露，不新增命令**：本阶段在 `--explain` / 结构化输出或日志里暴露本次 `generator_calls` / `cache_hits` / `anchor_backend` / `anchor_fallback_reason`；Phase 27 的评测报告汇总调用数与缓存命中率（EVL-04）；文档明确 `llm_cache` 会保存查询文本、本地留存、可 TTL/清理、`sif cleanup` 可清、远程 opt-in 才会外发。不新增 MCP 字段、不新增 `sif anchor status/cache` 子命令。 — **Reversibility:** reversible — additive 输出面。

**D. 降级与外发披露（GEN-03 / GEN-04 / ANC-05）**

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

### Deferred Ideas (OUT OF SCOPE)

- 四臂正式评测（`lex` / `anchor` / `hybrid` / `hybrid+anchor`）、`Recall@10`、`vec:` + anchor gain gap、配对 bootstrap / 0.01 tie rule / held-out `adopt` vs `keep-default` verdict —— 属 Phase 27（EVL-01..05）；本阶段只留可组合底层能力。
- `hybrid+anchor` 升默认、把规则锚点基线升级为默认后端、Qwen3-8B 级对照臂、MCP `anchor` 请求字段 —— REQUIREMENTS.md `v1.4+` / ANC-F1..F3，需单列契约变更阶段并更新 5 份 wire goldens。
- 新建 `anchor_cache` 独立表、文件级缓存、进程内 LRU 层 —— 明确否决的备选项（D-09/D-11），不是延期功能；理由见 `26-DISCUSSION-LOG.md`。
- 独立 `sif anchor status/cache` 子命令、交互式外发确认、生成器有限重试、词表守卫默认开 —— 明确否决的备选项（D-12/D-15/D-14/D-16）。
- Web UI / REST / `sif serve`、可写 UI、服务层抽取、SPA、chat-with-notes —— 推迟 v1.4，Out of Scope 条款不反转。
- 把 LFM3 GGUF 打进 wheel/sdist 或自动下载、远程后端作为默认、改默认 embedder / RRF 权重 / `expand:` PRF —— 既有 Out of Scope / PROJECT.md 锁定。
</user_constraints>

## Summary

本阶段是「在既有检索管线上加一个默认关闭的 BM25 单腿 + 一层可命中的生成缓存」，不是新框架。真正决定成败的只有三件事：**锚点怎么进 FTS**、**生成器/缓存放在哪一层**、**默认路径如何证明零成本**。研究给出三条结论。

**结论 1（最关键，可直接改变实现写法）：把锚点当作 AND 词 prepend 到查询字符串会让 `anchor:` 完全失效。** `BM25Searcher._build_fts_query` 把每个空白分隔 token 用 `" AND "` 连接（`src/sif/search/bm25.py:258-270`），而 Phase 25 的 spike 自身已记录「appending anchors into one FTS string AND-joins tokens and narrows instead of expanding」（`25-CONTRACT-FREEZE.md` §Limitations）。本会话在已验证的证据上做了两次实测（同一 fixture、同一数据库、同一判分口径）：把锚点作为 AND token prepend → **36 条 tuning 查询全部 0 结果**（mean paired Δ = −0.75，helped 0 / hurt 27）；把锚点改为 **OR 备选**（`(<原查询 AND>) OR "<锚点1>"* OR "<锚点2>"*`）→ **mean paired nDCG@10 Δ = +0.127246、helped 6 / hurt 0**，与 Phase 25 RRF 探针设计的 +0.130203、helped 6 / hurt 0 几乎同构。因此 D-01 的「纯 BM25 腿、注入只发生在 FTS MATCH 构造前」必须用 **OR 语义**实现；「prepend」指的是在构造 MATCH 表达式前把锚点并进去，不是把它们塞进同一个 AND 链。

**结论 2：缓存与生成器必须放在 pipeline 之外、注入进 pipeline，且 `anchor:` 路由不得触碰 embedder。** `llm_cache` 表与 `LLMCacheRepository`（`get`/`set(ttl)`/`clear_expired`）已存在且被 `sif cleanup` 接线，零迁移即可复用；把缓存写在**主 DB**（不是 embeddings_cache.db）天然按索引隔离，Phase 27 的 scratch 评估 DB 因此每次从空缓存开始、N 条查询只生成 N 次。0.3.37 的生成 API 已实测：`Llama.create_completion(..., stopping_criteria=StoppingCriteriaList([...]))` 的回调在**每个采样 token 后**被调用（`llama.py:999`），因此 `SIF_ANCHOR_TIMEOUT_MS` 可以用 deadline criterion 实现（`create_chat_completion` 不接受 `stopping_criteria`）；chat template 由 `Llama.metadata["tokenizer.chat_template"]` + `Jinja2ChatFormatter(...)(messages=...)` 显式渲染，正好满足 D-06 的「显式套用」。`jinja2` 是 `llama-cpp-python` 的传递依赖，但**不在**本仓库 dev/embed 环境里，因此任何 `llama_cpp` import 都必须延迟到生成时刻——否则 Docs Validation job（只装 `.[dev]`）会在导入 `sif` 时崩。

**结论 3：默认路径的「逐字节一致」必须用行为快照证明，不能靠「没写测试就说明没变」。** 既有 `SearchResult.to_dict` 有精确字典快照测试（`tests/unit/search/test_hybrid.py:835-860`），任何往结果里加字段都会破坏它们并改变 CLI JSON 输出；因此 `generator_calls` / `cache_hits` / `anchor_backend` / `anchor_fallback_reason` 只能走 `--explain` 的 stderr 行与失败告警，不进入 `to_dict`，也不进入 MCP 信封。新增 Settings 字段若不加进 `scripts/generate_config_ref.py` 的 `SECTIONS` 会被**静默丢弃**（生成器只遍历 `SECTIONS`，缺字段直接 `continue`），`make docs-generate` 的 diff gate 也抓不到——CTR-04 必须显式补 `SECTIONS`，并建议补一条「每个 Settings 字段都出现在某个 SECTION」的守卫测试。

**Primary recommendation:** 以 `SearchOptions.anchor_terms` 为唯一注入点；在 `BM25Searcher._build_fts_query(query, anchor_terms)` 内用 **OR** 组合「原查询 AND 链」与「每个锚点一个短语」；`SearchPipeline` 的 ANCHOR 路由在解析前缀后解析锚点（显式 `options.anchor_terms` 优先、规则锚点为默认、生成器显式 opt-in）、把 terms 写回 `dataclasses.replace(options, ...)`、只调 BM25 腿，snippet/highlight 继续用原 query；`query_cmd` 的 `--anchor` 与 `anchor:` 前缀等价（flag 只 prepend 一次前缀），且在 ANCHOR 路由 + 无 rerank 时**不构造 EmbeddingManager**；缓存用 `llm_cache` + `anchor::<backend>::<model_id>` 命名空间 + `sha256(prompt_version|model_id|backend|stripped_query)`，只在成功时写入、失败不写、按实例失败锁存；预算 `SIF_ANCHOR_MAX_CALLS` 超限抛 `RuntimeError` 子类（CLI 转 `ClickException`）。

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| ANC-01 | 用户可用 `anchor:` 前缀或 `--anchor` 触发锚点增强 BM25；不使用时零构造、零模型加载、零成本 | 已验证 `SearchPipeline._parse_query_prefix` 与 `BM25Searcher.search` 的注入落点（见 Pattern 1/2）；ANCHOR 路由只调 BM25 腿；建议 `query_cmd` 在 ANCHOR 路由且未要求 rerank 时跳过 `EmbeddingManager`（`search.py:1269-1281` 是唯一加载点）；默认路径用「`sif.search.anchor` 未进 `sys.modules`」守卫证明零构造。 |
| ANC-02 | 锚点仅注入 BM25 腿并 prepend 到查询；snippet 与 highlight 仍使用原始查询 | `BM25Searcher.search` 把 `query` 参数同时用于 MATCH 构造（`:88`）与 highlight（`:208-213`）；只要锚点走 `options.anchor_terms` 而不进 `query`，highlight 自动保持原 query；snippet 在 pipeline 用 `parsed_query`（`hybrid.py:480`）。 |
| ANC-03 | `SearchType.ANCHOR`、`SearchOptions.anchor_terms` 与两处前缀映射同步，且 settings 不绕过 `SearchOptions` | 已验证枚举（`models.py:84-91`）、`SearchOptions`（`:347-384`，含「settings never bypass SearchOptions」注释）、`prefix_map`（`hybrid.py:535-544`）与 `_PREFIX_ROUTES`（`backend.py:124-129`）；建议抽一个共享 `PREFIX_ROUTES` 常量，从结构上消灭漂移。 |
| ANC-04 | `hybrid+anchor` 仅作为诊断臂，默认关闭，不替换默认 RRF 的 BM25 腿 | `HybridSearcher.search` 的 BM25 腿直接读 `fetch_options`（`hybrid.py:121-128`），所以 `dataclasses.replace(options, anchor_terms=[...])` 天然只改 BM25 腿、向量腿不变；`anchor_terms=None` 默认 → 逐字节不变。 |
| ANC-05 | 词表守卫可作为独立 A/B 开关，丢弃 FTS 词表外的锚点；默认行为、对论文的偏离与影响均有记录 | 守卫实现建议用 FTS 探针（`SELECT 1 FROM documents_fts WHERE documents_fts MATCH ? LIMIT 1`），因为 `documents_fts` 是 `tokenize='porter'`（`schema.py:542-550`）、词表是**词干**（实测 `cultur`/`ferment`），按原词查 `documents_fts_v`（`schema.py:594-600`）会漏屈折；默认关。 |
| GEN-01 | 冻结 prompt（带版本号）、greedy / temperature 0、每行一个术语、最多 10 个、去重，模型与 prompt revision 评测前冻结 | 0.3.37 的 `create_completion` 实测支持 `temperature`/`top_k`/`stopping_criteria`；prompt 与 `PROMPT_VERSION` 设为模块常量（不进 Settings，见 D-06）；解析器在 Pattern 4。 |
| GEN-02 | 同一 query + model + prompt version 命中缓存后不再调用生成器；`bench --sweep` 的 N 条查询只生成 N 次 | `LLMCacheRepository.get/set` 已验证（`repositories.py:629-691`）；`llm_cache` 在主 DB（`schema.py:264-278`）→ 按索引隔离；测试用假生成器 + 真 sqlite 模拟 45 配置 × N 查询，断言 `generator_calls == N`。 |
| GEN-03 | 生成失败或超时 fail-open 回退原查询，不产生重试风暴，用户可见失败原因 | deadline `StoppingCriteria` 每 token 检查（0.3.37 `llama.py:999`）；单次尝试 + 实例内按 query 失败锁存；失败不写缓存；`logger.warning` 一次 + `--explain` 的 `anchor_fallback_reason`。 |
| GEN-04 | 默认本地 GGUF；远程 OpenAI-compatible 仅 opt-in，并明确披露查询文本外发 | 本地：`Llama(model_path=..., embedding=False)`；远程：`from urllib import request` + `timeout=`（仓库既有 `pull.py:50` 先例，零新增依赖）；opt-in 由 `SIF_ANCHOR_BACKEND` 决定；启用时一次 stderr 披露。 |
| CTR-03 | LFM3 GGUF 不打进 wheel/sdist；`LFM Open License v1.0` 的 $10M 营收阈值与再分发义务写入用户文档与 Key Decisions | 已验证 `src/sif` 无 `.gguf` 文件、`pyproject.toml` 只在 `all` extra 里声明 `llama-cpp-python>=0.3.35`（不自带权重）；PROJECT.md Key Decisions 已有该行但状态 `— Pending`（`PROJECT.md:216`），用户文档尚无该条款。 |
| CTR-04 | 新增 Settings / CLI 通过 `make docs-generate` 与 docs CI diff gate；新增 `src/sif` 代码保持 ≥90% coverage；8-cell CI 全绿 | 已验证 `addopts` 带 `--cov` 且 `fail_under=90`（`pyproject.toml:226-229`）；`make docs-generate` 跑两个脚本、CI 端 `git diff --exit-code`（`.github/workflows/docs.yml`）；8-cell matrix（`test-matrix.yml:22-24`）。**注意**：新 Settings 字段必须加入 `generate_config_ref.SECTIONS`，否则被静默丢弃。 |
</phase_requirements>

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| 前缀路由（`anchor:`） | Search pipeline（`sif.search.hybrid`） | MCP backend（`sif.mcp.backend`，prefix-first） | 既有约定：pipeline 是所有 CLI 路径的单一解析点；MCP 在加载决策前先解析，避免为 `anchor:` 加载 embedder。 |
| 锚点派生（规则表） | 纯函数模块（`sif.search.anchor`） | — | query-only、无 I/O、可独立测试；不依赖 DB、模型或网络。 |
| 锚点生成（GGUF/远程） | 独立组件（lazy import） | CLI host 注入 pipeline | 生成器是可选后端，生命周期由 host 管理；pipeline 只消费 terms。 |
| 缓存 / 预算 / 成本计数 | Repository（`llm_cache`）+ resolver 组件 | 主 DB 事务 | 持久化在用户主 DB，天然跨进程；`sif cleanup` 已有清理面。 |
| 注入点 | `SearchOptions.anchor_terms` → `BM25Searcher._build_fts_query` | Hybrid BM25 腿 | 唯一注入点，settings 不绕过 options；向量腿与 snippet/highlight 不受影响。 |
| 失败可见性 | `logger.warning`（stderr）+ `--explain` 行 | 文档 | 不污染 stdout、不改 MCP 信封、不改 `to_dict`。 |
| 许可与打包约束 | 用户文档 + PROJECT.md Key Decisions | 静态守卫测试 | 权重不进包；许可条款是文档义务，不是运行时行为。 |

## Standard Stack

### Core

| Library / 组件 | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Python stdlib `sqlite3` + FTS5 | SQLite 3.47.2（本机） | 锚点 OR 组合与词表探针 | 既有一切检索语义都在 FTS5 上；本会话已实测 OR 语法与 porter 词干行为。 |
| `llama-cpp-python` | 主 pin `0.3.35` 不变；生成器需 ≥`0.3.37`（Phase 25 证据） | 本地 GGUF 生成 | 唯一已锁定的本地推理路径；0.3.37 在隔离 venv 中已证明能加载 `lfm3`。 |
| `jinja2` | 3.1.6（`llama-cpp-python` 的 `Requires-Dist`，非 SIF 直接依赖） | 渲染 GGUF chat template | 随 `llama-cpp-python` 传递而来；`test_packaging.py` 的 13 项 runtime deps 不变。 |
| `LLMCacheRepository` + `llm_cache` | in-repo（不变） | 锚点缓存 | 已有 `get`/`set(ttl)`/`clear_expired` 与 `sif cleanup` 接线，零迁移。 |
| `BM25Searcher` / `SearchPipeline` | in-repo（扩展） | 单腿 BM25 + 前缀路由 | `lex:` 的既有一等基线，`anchor:` 与其同粒度。 |
| `pytest` + `pytest-cov` | 9.2.0 / 7.x | 门禁 | 既有测试基础设施。 |
| `urllib.request`（stdlib） | — | 远程 OpenAI-compatible 生成 | 仓库既有先例（`pull.py:50`），零新增依赖、原生 timeout。 |

### Supporting

| Tool | Version | Purpose | When to Use |
|------|---------|---------|-------------|
| `uv` | 0.9.26 | 在带 `--extra embed`/`all` 的环境中跑全量套件；隔离 venv 做真实 GGUF 手工验证 | CI 同款：`uv sync --frozen --extra dev --extra embed`。 |
| `.planning/tmp/phase-25/bench-spike.db` | Phase 25 scratch（仍在） | 复算锚点 delta | 只读复算用；不作为提交物。 |
| `.planning/tmp/phase-25/venv-upgrade-0.3.37/` | 0.3.37 | 真实生成 API 的权威参考 / 手工冒烟 | 只读参考；不改 lock。 |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| 锚点 OR 进单腿 BM25 | Phase 25 的 RRF 多探针融合 | 后者复现 +0.130203 更贴近，但违反 D-01「单腿」且会让 `anchor:` 不再与 `lex:` 同粒度；OR 实测 +0.127246，差距在网络噪声量级。 |
| 锚点 AND 进单腿 BM25（字面 prepend） | — | **实测全部 36 条查询 0 结果**，不可用。 |
| `create_chat_completion` | `create_completion` + 手渲染模板 | 前者自动套模板但**不接受 `stopping_criteria`**，无法实现 D-14 的超时；后者需要显式渲染，正好满足 D-06。 |
| 远程后端用 stdlib `urllib` | `openai` SDK（`docsif[openai]` extra） | SDK 是既有 OpenAI embedder 的先例，但对一个 20 行 POST 来说引入可选依赖面更大；stdlib 更小且 timeout 语义直接。 |
| 规则锚点也写缓存 | 只在生成器后端写缓存 | 规则锚点是纯函数、零成本；写入只会把查询文本无谓留存在 DB，违背最小留存。 |

**Installation:** 本阶段不安装任何新包。真实 GGUF 手工验证需要用户侧环境具备 `llama-cpp-python>=0.3.37`（`docsif[all]` 或隔离 venv；锁定的 0.3.35 无法加载 `lfm3`）。

**Version verification:** `uv.lock` 仍解析 `llama-cpp-python==0.3.35`（Phase 25 逐字节冻结，`b0175d45…`）；0.3.37 仅存在于 `.planning/tmp/phase-25/venv-upgrade-0.3.37`（本会话复验 `llama_cpp.__version__ == "0.3.37"`，并实测其 `create_completion` 签名为 `['self','prompt','suffix','max_tokens','temperature','top_p','min_p','typical_p','logprobs','echo','stop','frequency_penalty','presence_penalty','repeat_penalty','top_k','stream','seed','tfs_z','mirostat_mode','mirostat_tau','mirostat_eta','model','stopping_criteria','logits_processor','grammar','logit_bias']`）。

## Package Legitimacy Audit

> 本阶段**不安装任何新包**，也不 bump 任何 pin。审计仍对文档中会出现的 `llama-cpp-python` 版本要求跑了一次。

| Package | Registry | Age | Downloads | Source Repo | Verdict | Disposition |
|---------|----------|-----|-----------|-------------|---------|-------------|
| `llama-cpp-python` | PyPI | 锁定 0.3.35，`all` extra 已有；0.3.37 为 Phase 25 证据版本 | 不可得（gate 返回 `unknown-downloads`） | `github.com/abetlen/llama-cpp-python`（gate 未解析到） | **SUS**（`unknown-age`, `unknown-downloads`, `no-repository`） | 已是既有可选依赖；**本阶段不安装、不 bump**。文档只陈述「≥0.3.37 才能加载 `lfm3`」这一 Phase 25 实测事实。若未来提议改 pin，仍须 `checkpoint:human-verify`。 |
| `jinja2` | PyPI | 3.1.6，`llama-cpp-python` 的传递依赖 | — | `github.com/pallets/jinja` | 不新增（传递依赖） | 不作为 SIF 直接依赖；只在 `llama_cpp` 被导入时可用，因此所有 import 必须 lazy。 |

**Packages removed due to [SLOP] verdict:** none.
**Packages flagged as suspicious [SUS]:** `llama-cpp-python`（仅因 registry 信号不可得；Phase 25 已记录同一结论，且它是既有锁定依赖）。

## Architecture Patterns

### System Architecture Diagram

```
            ┌──────────────────────────── 输入 ────────────────────────────┐
  CLI: sif search query [--anchor] "Q"          MCP: query {query: "anchor:Q"}
            │                                              │
            │  ① 仅 CLI：flag 且未带前缀 → query = "anchor:Q"                │
            ▼                                              ▼
  ┌─────────────────────────────┐              ┌──────────────────────────────┐
  │ query_cmd                   │              │ SearchBackend._split_query_  │
  │ ② route = split_prefix(Q)   │              │  prefix(Q) → ANCHOR          │
  │ ③ ANCHOR 且无 rerank        │              │ ④ ANCHOR 分支早于 loader     │
  │    → 不构造 EmbeddingManager│              │    → BM25Searcher + 规则锚点 │
  └──────────────┬──────────────┘              └──────────────┬───────────────┘
                 │                                            │
                 ▼                                            ▼
  ┌─────────────────────────── SearchPipeline.search ───────────────────────┐
  │ _parse_query_prefix → SearchType.ANCHOR                                 │
  │   ⑤ options.anchor_terms 非 None（评测显式注入）→ 直接用                │
  │      否则 AnchorResolver.resolve(Q)：                                   │
  │        backend=rules ──► derive_rule_anchors(Q)（零模型、无缓存）       │
  │        backend=gguf/openai（opt-in）                                    │
  │           ├─ cache.get(ns, key) 命中 → terms（generator_calls=0）       │
  │           ├─ miss → budget 检查 → generate 一次 → parse ≤10 → cache.set │
  │           └─ 超时/异常 → terms=[] + 单次 warning + reason（fail-open）  │
  │   ⑥ options2 = replace(options, anchor_terms=terms or None)             │
  │   ⑦ BM25Searcher.search(parsed_query, options2)   ← 唯一检索腿          │
  │        _build_fts_query: ("Q"* AND ...) OR "<a1>"* OR "<a2>"* ...       │
  │        highlights 仍用 parsed_query（ANC-02）                           │
  │   ⑧ snapshot = parsed_query → enrich_results(_apply_snippets(...))      │
  └──────────────────────────────┬──────────────────────────────────────────┘
                                 ▼
       SearchResult 列表（shape 不变）+ pipeline.last_anchor_resolution（运行级）
                                 │
             ┌───────────────────┴────────────────────┐
             ▼                                        ▼
  CLI --explain → stderr: backend/calls/hits/        JSON/CSV/MD/XML 输出
  fallback；失败 → 单次 stderr warning                （to_dict 未变）
```

关键数据流：查询文本只进入两个新位置——① 生成器的 prompt；② `llm_cache.prompt`（仅生成器后端）。锚点文本只进入一个位置——`SearchOptions.anchor_terms` → FTS MATCH 表达式。向量腿、snippet、highlight、MCP 信封、`SearchResult.to_dict` 都不接触锚点。

### Recommended Project Structure

```
src/sif/
├── core/models.py            # + SearchType.ANCHOR, SearchOptions.anchor_terms, AnchorGenerator Protocol
├── search/
│   ├── bm25.py               # + anchor_terms → OR 组合（唯一 FTS 注入点）
│   ├── hybrid.py             # + PREFIX_ROUTES 共享常量, ANCHOR route, anchor_resolver 注入
│   └── anchor.py             # 新：规则表/派生/规范化/解析/缓存/resolver/backends/report
├── mcp/backend.py            # + PREFIX_ROUTES 复用, ANCHOR 直连 BM25（不加载 embedder）
├── cli/commands/search.py    # + --anchor, route-first, 跳过 embedder, --explain 行
└── config/settings.py        # + SIF_ANCHOR_* 字段与 validator
scripts/generate_config_ref.py  # + "Anchor Settings" SECTION
tests/unit/search/test_anchor.py          # 新
tests/unit/mcp/test_backend_anchor.py     # 新（或并入 test_lazy_embedder.py 风格）
tests/unit/cli/test_search_anchor.py      # 新
tests/test_packaging_assets.py            # 新：无 .gguf 守卫
```

规则表建议以 **Python 模块常量**落盘（`sif/search/anchor.py` 内的 `ANCHOR_TABLE: dict` + `ANCHOR_TABLE_VERSION`），而不是 JSON 资源：无打包/资源读取风险、import 即确定、可直接对规范化 JSON 求哈希供 Phase 27 引用。Phase 25 的 `bench/anchor-table.json` 作为词条来源合并进去（保留 `rules` 段）。

### Pattern 1: 锚点 OR 注入（唯一 FTS 注入点）

**What:** `_build_fts_query` 在锚点存在时输出 `(<原查询 AND 链>) OR "<锚点1>"* OR "<锚点2>"*`；锚点缺省时输出与今天逐字节相同。
**When to use:** 所有 `anchor_terms` 非 None 的 BM25 调用（ANCHOR 路由与 hybrid+anchor 诊断臂）。
**Why:** 实测 —— 见 Summary 结论 1 与下方「Measured evidence」。

```python
# Source: src/sif/search/bm25.py:258-270（现状）+ 本会话 FTS5 实测
def _build_fts_query(self, query: str, anchor_terms: list[str] | None = None) -> str:
    terms = [t for t in (_sanitize_term(tok) for tok in query.split()) if t]
    base = " AND ".join(terms) if terms else '""'
    if not anchor_terms:
        return base                      # byte-identical default path
    alternatives = [t for t in (_sanitize_term(a) for a in anchor_terms) if t]
    if not alternatives:
        return base
    return f"({base}) OR " + " OR ".join(alternatives)
```

注意：`_sanitize_term` 本身**保留空格**并整体加引号（拆词发生在 `_build_fts_query` 的 `query.split()`，不在 `_sanitize_term` 里）。所以锚点侧的正确写法是**对每个锚点整体**调用 `_sanitize_term(anchor)`、**不要**先 `split()`——这样 `machine learning` 会变成 `'"machine learning"*'`（短语），而不是两个独立 AND 词。本会话实测 `"machine learning"*` / `"starter culture"*` 均可正常匹配；短语式与「词内 AND」式在本 fixture 上结果完全相同（mean 0.127246 / helped 6 / hurt 0 两者一致），选短语式（更贴合「每行一个术语」）。

### Pattern 2: ANCHOR 路由（pipeline）

**What:** 在 `SearchPipeline.search` 里新增分支，只调 BM25 腿；`anchor_resolver` 作为可选注入依赖。
**When to use:** 任何 `anchor:` 前缀（CLI/MCP）；CLI 的 `--anchor` 通过 prepend 前缀复用同一分支（D-03）。

```python
# Source: src/sif/search/hybrid.py:352-356（lex 分支的形状）
if search_type == SearchType.ANCHOR:
    terms, resolution = self._resolve_anchor_terms(parsed_query, options)
    # _resolve_anchor_terms: options.anchor_terms 非 None 时直接采用（评测注入），
    # 否则 resolver（默认规则锚点）生成；任何失败在 resolver 内 fail-open。
    opts = replace(options, anchor_terms=terms or None)
    results = self.hybrid.bm25.search(parsed_query, opts)
    self.last_anchor_resolution = resolution          # 运行级元数据，不进 SearchResult
    return enrich_results(self.db, self._apply_snippets(results, parsed_query))
```

**Anchor-02 的机械保证:** `parsed_query` 不含锚点，且 `BM25Searcher.search` 的 highlight 分支用的就是这个 `query` 参数（`src/sif/search/bm25.py:208-213`），`_apply_snippets` 也用 `parsed_query`（`hybrid.py:480`）。

**CLI 侧注意:** `--anchor` 只为「交给 pipeline 的那一次调用」prepend 前缀；`_zero_result_suggestions` 与 `_record_query_history`（`search.py:1345-1347`）必须继续使用**原始** `query`，否则 DYM 建议与历史里会出现 `anchor:` 字样。

### Pattern 3: 前缀路由去重（ANC-03 的结构保证）

**What:** 把 `prefix_map` 提升为模块级 `PREFIX_ROUTES: dict[str, SearchType]`，`SearchPipeline._parse_query_prefix` 与 `mcp/backend.py` 共用；`anchor:` 加入其中一次即可。
**When to use:** 必须——否则两处字典漂移只能靠测试兜底。

```python
# Source: src/sif/search/hybrid.py:535-544 + src/sif/mcp/backend.py:124-129（现状：两份同构字典）
PREFIX_ROUTES: dict[str, SearchType] = {
    "lex:": SearchType.BM25,
    "vec:": SearchType.VECTOR,
    "hyde:": SearchType.HYDE,
    "expand:": SearchType.EXPAND,
    "anchor:": SearchType.ANCHOR,
}
```
`_parse_query_prefix` 只匹配第一个前缀、返回去前缀后的文本——与 D-03 的 `anchor:lex:foo` 视为字面量一致。MCP 侧仍保持「prefix-first 先于任何加载决策」。

### Pattern 4: 解析器与冻结 prompt（GEN-01）

```python
PROMPT_VERSION = "anchor.v1"      # 任何 prompt 文本改动必须 bump
MAX_ANCHOR_TERMS = 10             # GEN-01 冻结，不做 Settings
_LIST_PREFIX = re.compile(r"^[\s\-\*•\d\)\.]+")

PROMPT_TEMPLATE = (
    "You expand a search query into alternative search terms.\n"
    "Write one term per line. No numbering, no explanations.\n"
    "Use synonyms, abbreviations and translations of the key concepts.\n"
    "At most 10 lines.\n\n"
    "Query: {query}\nTerms:\n"
)

def parse_terms(text: str, *, limit: int = MAX_ANCHOR_TERMS) -> list[str]:
    terms: list[str] = []
    seen: set[str] = set()
    for raw in text.splitlines():
        term = _LIST_PREFIX.sub("", raw).strip().strip("\"'`").lower()
        if not term or len(term) > 64 or len(term.split()) > 6:
            continue
        if not re.search(r"[0-9a-z一-鿿]", term):
            continue
        if term in seen:
            continue
        seen.add(term)
        terms.append(term)
        if len(terms) >= limit:
            break
    return terms
```

生成参数固定：`temperature=0.0`、`top_k=1`、`repeat_penalty=1.0`、`max_tokens=SIF_ANCHOR_MAX_TOKENS`（默认 64）、`stop=[eos]`。**不要**继承 `LlamaCppEmbedder`（`embedding=True`）。

### Pattern 5: 显式 chat template + deadline（0.3.37，实测）

```python
# Source (0.3.37): llama.py:519-521（模板来自 metadata）、:531-536（Jinja2ChatFormatter）、
#                  llama_chat_format.py:194-302（__call__ → ChatFormatterResponse(prompt, stop)）、
#                  llama.py:999（stopping_criteria 每 token 检查）
from llama_cpp import Llama, StoppingCriteriaList
from llama_cpp.llama_chat_format import Jinja2ChatFormatter

llm = Llama(model_path=str(path), n_ctx=2048, embedding=False, verbose=False)
template = llm.metadata.get("tokenizer.chat_template")      # Phase 25 已把全文记录在案
formatter = Jinja2ChatFormatter(
    template=template,
    eos_token=llm.detokenize([llm.token_eos()]).decode("utf-8"),
    bos_token=llm.detokenize([llm.token_bos()]).decode("utf-8"),
    stop_token_ids=[llm.token_eos()],
)
rendered = formatter(messages=[{"role": "user", "content": PROMPT_TEMPLATE.format(query=q)}])

deadline = time.monotonic() + timeout_ms / 1000
def _expired(_tokens, _logits) -> bool:
    return time.monotonic() >= deadline

out = llm.create_completion(
    prompt=rendered.prompt,
    stop=rendered.stop,
    max_tokens=max_tokens,
    temperature=0.0,
    top_k=1,
    repeat_penalty=1.0,
    stopping_criteria=StoppingCriteriaList([_expired]),   # 0.3.37 导出该名
)
```
要点：`create_chat_completion` **不接受** `stopping_criteria`，所以 D-06 的「显式套模板」与 D-14 的 timeout 是同一条实现路径；`StoppingCriteriaList` 必须是该类型（普通 list 没有 `__call__`）。`llama_cpp` / `jinja2` 只在此处 import（lazy）。

### Pattern 6: 缓存读写（D-09/D-10/D-11）

```python
# Source: src/sif/database/repositories.py:629-691
model_name = f"anchor::{backend}::{model_id}"
prompt_hash = hashlib.sha256(
    f"{PROMPT_VERSION}\x00{model_id}\x00{backend}\x00{stripped_query}".encode("utf-8")
).hexdigest()
cached = LLMCacheRepository(conn).get(model_name, prompt_hash)      # None = miss/expired
if cached is None:
    response = generator.generate(stripped_query)                   # 一次，不重试
    terms = parse_terms(response)
    LLMCacheRepository(conn).set(
        model_name, prompt_hash, stripped_query,
        json.dumps({"version": 1, "terms": terms}, ensure_ascii=False),
        ttl_seconds=settings.anchor_cache_ttl or None,
    )
    if not conn.in_transaction:      # host 已开事务（CLI 的 with db.connection）则让它提交
        conn.commit()
else:
    terms = _parse_cached(cached)    # JSON 校验失败 → 视为 miss 并覆盖，不抛异常
```
`stripped_query`：`unicodedata.normalize("NFKC", q)` → `" ".join(...split())` → `casefold()`，保留 CJK；冻结为键身份的一部分。`id` 由 `set` 内部以 `f"{model_name}:{prompt_hash}"` 生成（`repositories.py:683`），prompt_hash 为定长 hex，不会与既有条目碰撞。缓存落**主 DB**：`llm_cache` 建在 `create_all` 的主 schema（`schema.py:264-278`），`sif cleanup` 也在主 DB 清理（`cli/main.py:274`）。

### Anti-Patterns to Avoid

- **把锚点作为 AND token prepend**：实测 36/36 查询 0 结果（见 Measured evidence）。
- **用 `create_chat_completion` 实现超时**：它不接受 `stopping_criteria`，只能用 `max_tokens` 兜底；genuine deadline 必须走 `create_completion` + 渲染后的 prompt。
- **在模块顶层 import `llama_cpp` / `jinja2` / `openai`**：Docs job 只装 `.[dev]`，会 ImportError；也会让 `sif` 在任何无 `all` extra 的环境里不可导入。
- **给 `SearchResult.to_dict()` 加字段**：破坏 `tests/unit/search/test_hybrid.py:835-860` 的精确快照，并改变所有 CLI JSON 输出（违反默认路径逐字节一致）。
- **新增 Settings 字段却不改 `SECTIONS`**：字段在 `docs/configuration.md` 中静默消失，diff gate 不报错。
- **在 `query_cmd` 无条件读新 Settings**：`_query_settings_mock`（`tests/unit/cli/test_search.py:42-60`）是显式字段白名单，未列字段会是 truthy Mock（Pitfall 10 同类）。
- **MCP 路径写缓存**：7 工具是只读契约；MCP 的 `anchor:` 只跑规则锚点、不写 DB。
- **失败后重试**：D-14 明确单次 fail-open；重试会让 45 配置放大成 45N 次。

### Measured evidence（本会话实测，可复现）

| 设计 | mean paired nDCG@10 Δ | helped | hurt | 0 结果查询数 |
|---|---|---|---|---|
| 字面 AND-prepend 锚点 | **−0.750000** | 0 | 27 | **36 / 36** |
| OR 组合（短语式） | **+0.127246** | 6 | 0 | 0 |
| OR 组合（词内 AND 式） | +0.127246 | 6 | 0 | 0 |
| Phase 25 RRF 多探针（参考） | +0.130203 | 6 | 0 | 0 |

方法：`.planning/tmp/phase-25/bench-spike.db`（150 文档，`tests/fixtures/bench/corpus`）+ `tests/fixtures/bench/queries.json` 的 36 条 `split=="tuning"` + `bench/anchor-table.json` 派生锚点 + `sif.search.benchmark.ndcg_at_k(top10, ideal, 10)`；SQL 与 `BM25Searcher` 的 `documents_fts MATCH ... ORDER BY bm25(documents_fts,1.0,1.0)` 等价。脚本为一次性 inline 运行（未落盘、未提交），planner 可在同一 scratch DB 上复算。

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| FTS 查询构造 / 转义 | 手写字符串拼接 | `BM25Searcher._sanitize_term` + `_build_fts_query` 扩展 | 已处理 `"*():^`、空查询、前缀匹配；`test_build_fts_query_*` 已钉住现状。 |
| LLM 响应缓存 | 新表 / 文件缓存 / 进程内 LRU | `LLMCacheRepository` + `llm_cache` | TTL instant 比较、过期清理、`sif cleanup` 全部就绪（D-09/D-11）。 |
| GGUF chat template | 手写 ChatML 字符串 | `Llama.metadata["tokenizer.chat_template"]` + `Jinja2ChatFormatter` | 模板由模型自带（Phase 25 已记录 LFM3 全文），手写会与模板漂移并复读 prompt。 |
| 生成超时 | `threading.Timer` / 子进程 kill | `StoppingCriteriaList` deadline（本地）/ `urlopen(timeout=)`（远程） | llama.cpp 无法从 Python 中断原生调用；逐 token 检查是唯一受支持的界。 |
| 词表存在性判断 | Python porter 词干器 / 直接查 `documents_fts_v.term` | `documents_fts MATCH` 探针 | FTS 词表是词干（实测 `cultur`/`ferment`），原词查表会漏屈折；探针使用同一个 tokenizer。 |
| 前缀解析 | 第三份前缀表 | 共享 `PREFIX_ROUTES` 常量 | 两份字典已经同构，第三份只会加速漂移。 |
| 指标计算（Phase 27） | 新 metric 实现 | `ndcg_at_k` / `recall_at_k` / `SearchEvaluator` | 既有语义已冻结，本阶段不改。 |

**Key insight:** 本阶段所有「新」逻辑都应是既有组件的组合：BM25 的 MATCH 构造、pipeline 的前缀路由、`llm_cache` 的 TTL、logging 的一次告警、Click 的 flag。唯一真正新增的算法是「锚点 OR 组合」与「术语解析」，两者都应是小的纯函数。

## Common Pitfalls

### Pitfall 1: AND-join 让锚点臂归零（本阶段最大风险）
**What goes wrong:** 实现者把 `anchor_terms` 直接拼进原有 `" AND ".join(...)`，`anchor:` 在真实语料上返回 0 结果或严重收窄。
**Why it happens:** `_build_fts_query` 的默认连接符是 AND（`bm25.py:270`），而锚点是**同义扩展**，语义上要求 OR。
**How to avoid:** 锚点一律走 OR 备选；把「36 条 tuning 查询的 OR 版本非零结果」写成一个测试（可用 `tests/support/bench.build_bench_db` 或真实 scratch DB）。
**Warning signs:** `anchor:` 的命中数明显低于 `lex:`；delta 表里 baseline 0 的查询仍然 0。

### Pitfall 2: 全量套件在本机 `.venv` 收集失败
**What goes wrong:** `pytest` 在 `tests/unit/inference/test_reranker.py` 报 `ModuleNotFoundError: No module named 'torch'`。
**Why it happens:** 本机 `.venv` 没装 `--extra embed`；CI 用 `uv sync --frozen --extra dev --extra embed`。
**How to avoid:** 门禁用 `uv run --frozen pytest`（或先 `uv sync --frozen --extra dev --extra embed`）；定向测试用 `--no-cov`。
**Warning signs:** `3276 tests collected, 1 error`。

### Pitfall 3: 新增 Settings 字段在文档里静默消失
**What goes wrong:** 加了 `SIF_ANCHOR_*`，`make docs-generate` 无 diff，`docs/configuration.md` 里没有这些字段。
**Why it happens:** `generate_config_ref.py` 只遍历 `SECTIONS` 白名单，未列字段 `continue`（`:307-315`）。
**How to avoid:** 在 `SECTIONS` 加 `("Anchor Settings", [...])`；建议加一条「每个 `Settings.model_fields` 都出现在某个 SECTION」的测试。
**Warning signs:** 生成器输出里搜不到 `SIF_ANCHOR_BACKEND`。

### Pitfall 4: Docs job 因顶层 import 失败
**What goes wrong:** Docs Validation 只 `pip install -e ".[dev]"`，若 `sif.search.anchor` 顶层 `import llama_cpp`，`tests/test_docs.py` 导入 `sif.cli.main` 时崩溃。
**Why it happens:** `llama-cpp-python` 只在 `all` extra；`jinja2` 是其传递依赖，本机 `.venv` 里都没有。
**How to avoid:** 生成器与远程后端在 `__init__`/调用点 lazy import；加一条 `import sif.search.anchor` 后 `"llama_cpp" not in sys.modules` 的测试。
**Warning signs:** 本地 `python -c "import sif"` 正常但 CI docs job 红。

### Pitfall 5: 结果元数据破坏 JSON 快照
**What goes wrong:** 给 `SearchResult` 加 `anchor_backend` 等字段并放进 `to_dict()`，`test_hybrid.py` 的精确字典快照失败，CLI JSON 输出对所有查询改变。
**Why it happens:** `to_dict` 是一个固定键列表（`models.py:326-344`），且有线级快照。
**How to avoid:** 运行级元数据挂在 pipeline 的 `last_anchor_resolution`；CLI 以 `--explain` 输出到 stderr；失败告警用 `logger.warning`。
**Warning signs:** `assert payload == SNAPSHOT` 类测试失败；非 anchor 查询的 `--json` 输出出现新键。

### Pitfall 6: MagicMock settings 让 anchor 路径意外启用
**What goes wrong:** `query_cmd` 读了 mock 上未显式设置的 `settings.anchor_backend`，拿到 truthy Mock，意外走生成器分支。
**Why it happens:** `_query_settings_mock` 是显式白名单（`tests/unit/cli/test_search.py:42-60`），注释直接点名 Pitfall 10。
**How to avoid:** 只在 `anchor_requested` 为真时读新字段；在 mock 里补默认值（`anchor_backend="rules"` 等）；解析用 `str` 白名单校验而非 truthiness。
**Warning signs:** 既有 query 测试开始尝试加载生成器或打印 anchor 告警。

### Pitfall 7: 跨进程命中被事务吞掉
**What goes wrong:** 缓存在进程里写入了但没提交，第二次 CLI 调用仍 miss，N 次生成变成 2N。
**Why it happens:** `LLMCacheRepository.set` 只 `execute`，不 commit（`repositories.py:676-691`）。
**How to avoid:** 在 host 已开事务时交给 host 提交；否则 `if not conn.in_transaction: conn.commit()`。测试要覆盖「同一 DB、两个 resolver 实例」。
**Warning signs:** 同一 query 连续两次 `--anchor`，第二次仍 `generator_calls=1`。

### Pitfall 8: 超时语义被模型加载吞掉
**What goes wrong:** 第一次调用的 `SIF_ANCHOR_TIMEOUT_MS` 被 GGUF 加载（数秒）吃掉，稳定「超时」。
**Why it happens:** deadline 只包住生成，不包住 `Llama(...)` 构造。
**How to avoid:** 模型构造在计时之外单独完成（首次使用时），deadline 只包 `create_completion`；加载失败按「后端不可用」处理并锁存。
**Warning signs:** 每个新进程的第一条 anchor 查询都 fallback。

### Pitfall 9: 词表守卫误杀 CJK / 屈折词
**What goes wrong:** 守卫用原词查 `documents_fts_v.term`，`"culture"` 查不到（表里是 `cultur`）；CJK 锚点若是更长 CJK token 的子串也查不到。
**Why it happens:** `tokenize='porter'`（`schema.py:548`）；本会话实测词表为词干、CJK 连续串为单 token。
**How to avoid:** 用 `documents_fts MATCH '<anchor phrase>'` 探针（同一 tokenizer）；文档写明「守卫按 tokenizer 后的存在性判断，子串型 CJK 锚点可能被丢弃」。
**Warning signs:** 开启守卫后某类锚点全部消失且无法解释。

### Pitfall 10: MCP 读契约被缓存写破坏
**What goes wrong:** MCP `anchor:` 走了生成器并写 `llm_cache`，把只读工具变成写工具。
**Why it happens:** 复用了 CLI 的 resolver。
**How to avoid:** MCP 的 ANCHOR 分支只用规则锚点、不构造 resolver/cache；与 `lex:` 同构（`backend.py:486-495`）。
**Warning signs:** MCP 端 `anchor:` 查询后 DB 的 `llm_cache` 行数增加。

## Code Examples

### 现有 BM25 注入点（逐字节现状）

```python
# Source: src/sif/search/bm25.py:258-270
def _build_fts_query(self, query: str) -> str:
    """Build a safe FTS5 query from raw user input. ... tokens are joined with AND ..."""
    terms = [t for t in (_sanitize_term(tok) for tok in query.split()) if t]
    if not terms:
        return '""'
    return " AND ".join(terms)
```

### 现有 highlight 使用原始 query（ANC-02 的依据）

```python
# Source: src/sif/search/bm25.py:208-213
if options.include_highlights:
    result.highlights = self._get_highlights(
        row["document_id"],
        query,
        options.max_highlights,
    )
```

### 现有前缀路由（两处同构）

```python
# Source: src/sif/search/hybrid.py:535-544
prefix_map = {
    "lex:": SearchType.BM25,
    "vec:": SearchType.VECTOR,
    "hyde:": SearchType.HYDE,
    "expand:": SearchType.EXPAND,
}
for prefix, search_type in prefix_map.items():
    if query.startswith(prefix):
        return query[len(prefix) :].strip(), search_type
return query, self._default_search_type_enum()
```

```python
# Source: src/sif/mcp/backend.py:124-129
_PREFIX_ROUTES: dict[str, SearchType] = {
    "lex:": SearchType.BM25,
    "vec:": SearchType.VECTOR,
    "hyde:": SearchType.HYDE,
    "expand:": SearchType.EXPAND,
}
```

### MCP 的 prefix-first 直连 BM25（anchor 分支照此形状）

```python
# Source: src/sif/mcp/backend.py:486-495
if search_type is SearchType.BM25:
    core_results = BM25Searcher(conn).search(parsed_query, options)
    core_results = enrich_results(conn, core_results)
    return _with_suggestions(
        conn,
        parsed_query,
        _map_core_results(core_results, _page_checksums(conn, core_results)),
    )
```

### 缓存 API（零迁移）

```python
# Source: src/sif/database/repositories.py:629-660 / 662-691
LLMCacheRepository(conn).get(model_name, prompt_hash)          # -> str | None（过期即 miss）
LLMCacheRepository(conn).set(model_name, prompt_hash, prompt, response, ttl_seconds=None)
```

```sql
-- Source: src/sif/database/schema.py:264-278
CREATE TABLE IF NOT EXISTS llm_cache (
    id TEXT PRIMARY KEY,
    model_name TEXT NOT NULL,
    prompt_hash TEXT NOT NULL,
    prompt TEXT NOT NULL,
    response TEXT NOT NULL,
    created_at TEXT NOT NULL,
    expires_at TEXT,
    UNIQUE(model_name, prompt_hash)
)
```

### 词表机制（守卫与词干事实）

```sql
-- Source: src/sif/database/schema.py:542-550 / 594-600
CREATE VIRTUAL TABLE IF NOT EXISTS documents_fts USING fts5(
    content, title, content='documents', content_rowid='rowid', tokenize='porter'
)
CREATE VIRTUAL TABLE IF NOT EXISTS documents_fts_v USING fts5vocab(documents_fts, 'row')
```
本会话实测：`SELECT term, doc, cnt FROM documents_fts_v` 返回 `('cultur', 2, 3)`、`('ferment', 2, 2)`（词干）；`documents_fts MATCH '"culture"*'` 正确命中。

### `query_cmd` 的模型加载点（route-first 的改造位置）

```python
# Source: src/sif/cli/commands/search.py:1269-1281
try:
    manager = EmbeddingManager.from_settings(settings)
    manager.load_model()
    ...
except ImportError as e:
    raise click.ClickException(f"Embedding backend not installed: {e}") from None
```
建议：在它之前先算出 `route`；`route in (BM25, ANCHOR)` 且 `not rerank_requested` 时完全不进入该 `try`，把 `embedder=None`、`query_expander=None`、`identity_check=None` 交给 pipeline（`SearchPipeline` 仍需要 sqlite-vec，这是既有 `lex:` 的同一前提）。

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| 论文式「LLM anchors 拼进 BM25 查询」 | 显式 OR 扩展 + 确定性缓存 + fail-open | Phase 26 | AND 拼接在真实 FTS 上会归零；OR 是唯一可用语义。 |
| 原始 completion（无模板） | `tokenizer.chat_template` 显式渲染 | Phase 25 记录 / Phase 26 落地 | 避免模型复读 prompt（Phase 25 实测现象）。 |
| 每配置重新生成锚点 | `llm_cache` 命名空间缓存 | Phase 26 | 45N → N 次生成。 |
| 进程内 LRU | SQLite 表即跨进程 | Phase 26 (D-11) | 命中口径单一、无陈旧分叉。 |

**Deprecated/outdated:**
- 研究简报里 `SIF_ANCHOR_MAX_TERMS=10` 与 `SIF_ANCHOR_ENABLED=0` 的设想：本阶段建议把「最多 10 个」冻结为模块常量（GEN-01 / D-06），并**不**引入全局 `SIF_ANCHOR_ENABLED` 开关——`--anchor` / `anchor:` 本身就是开关注入点，再加全局 kill switch 会产生第三种路由面并让 flag 变成空操作。
- 把 `anchor:` 当作 hybrid 的别名：D-01 明确它是纯 BM25 单腿。

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | 0.3.37 的 `llama.detokenize([token_bos()])` 可用于构造 `Jinja2ChatFormatter` 的 `eos_token`/`bos_token` | Pattern 5 | Medium — 若签名/返回类型不同，改用 `llama._model.token_get_text` 或直接传空串并依赖 `stop=rendered.stop`；plan 的 Wave 1 应先跑一次真实冒烟。 |
| A2 | `StoppingCriteriaList` deadline 在 `create_completion(stream=False)` 路径上每 token 生效 | Pattern 5 / GEN-03 | Low — `llama.py:999` 已在生成器循环内；仍建议用「sleep 型 fake criterion」单测 + 一次真实冒烟。 |
| A3 | 规则锚点表从 Phase 25 的 36 条 tuning 查询派生，其泛化性未经 held-out 验证 | Summary / 风险 | Medium — Phase 27 的 held-out 才是裁决；本阶段只交付实验臂并明确标注 experimental。 |
| A4 | 远端 OpenAI-compatible 端点的 `/chat/completions` 形状（`choices[0].message.content`） | GEN-04 | Medium — 用可注入的 HTTP 函数做单测，真实端点由用户在 Phase 27 opt-in 时验证。 |
| A5 | 词表守卫按「锚点短语能匹配至少一篇文档」定义「在词表内」 | ANC-05 | Low — 这是最贴近 IDF 稀释机制的定义；若要严格按 `documents_fts_v.term` 判断，需要 porter 词干化，代价更大且会误杀短语。 |
| A6 | 把规则锚点表放进 Python 模块常量而非打包 JSON | Recommended structure | Low — hatchling 的 `packages=["src/sif"]` 会带上非 py 文件，但常量方式零资源读取风险。 |

## Open Questions (RESOLVED)

> 五问均已在 `26-01`..`26-04` PLAN.md 中按下列 Recommendation 实现；标题补 `(RESOLVED)` 以满足 Nyquist 的机器可读标记。

1. **`anchor_terms` 空列表 vs None 的语义**
   - What we know: `BM25Searcher` 只要 falsy 就退回 AND 查询。
   - What's unclear: `SearchOptions(anchor_terms=[])` 是否应被当作「显式无锚点」而绕过 resolver。
   - Recommendation: 视为「显式无锚点」——resolver 只在 `anchor_terms is None` 时运行，保证评测可注入空集做对照。

2. **MCP 是否应在用户配置生成器时也启用生成器**
   - What we know: MCP 是 7 个只读工具；写 `llm_cache` 会破坏只读面。
   - Recommendation: 否。MCP 的 `anchor:` 固定规则锚点，文档写明；生成器是 CLI 侧实验能力。

3. **规则锚点是否缓存**
   - What we know: 规则锚点是纯函数、零成本；缓存只会增加查询文本留存。
   - Recommendation: 不缓存；`anchor_backend="rules"` 只出现在运行元数据里。

4. **缓存 TTL 默认值**
   - What we know: `llm_cache` 支持 NULL（永不过期）；`sif cleanup` 只清已过期行。
   - Recommendation: 默认 30 天（`2592000`），`0` 表示不过期；文档写明「`sif cleanup` 只删已过期条目」。

5. **`SIF_ANCHOR_MAX_CALLS` 的计数域**
   - What we know: 需要防 45N。
   - Recommendation: 每个 resolver 实例（≈每次命令/每次评测运行）计数；默认 100，`0` = 不限；超限抛 `AnchorBudgetExceeded(RuntimeError)`。

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python | 全部 | ✓ | 3.12.8 | — |
| SQLite + FTS5 | 检索 | ✓ | 3.47.2 | — |
| `sqlite-vec` | `SearchPipeline` 构造（既有前提） | ✓ | installed | — |
| `torch` / `sentence-transformers` | 全量套件（`test_reranker.py`） | ✗ in `.venv` | — | `uv sync --frozen --extra dev --extra embed` |
| `llama-cpp-python` 0.3.35 | 主依赖（不可加载 `lfm3`） | ✗ in `.venv` | — | `docsif[all]`；`lfm3` 需 ≥0.3.37 |
| `llama-cpp-python` 0.3.37 | 真实 GGUF 生成冒烟 | ✓ (scratch) | 0.3.37 | `.planning/tmp/phase-25/venv-upgrade-0.3.37/`（只读参考） |
| `jinja2` | chat template 渲染 | ✗ in `.venv` | — | 随 `llama-cpp-python` 安装才出现；测试用 fake |
| `openai` | 远程生成（可选） | ✗ | — | 本阶段远程实现走 stdlib `urllib`，不需要它 |
| LFM3 GGUF | 真实生成冒烟 | ✓ | 1,099,627,808 B | `/Users/forrest/Downloads/lfm3-spike/LFM3-1.7B-Q4_K_M.gguf`（用户自备；不提交） |
| `uv` | 环境同步 / CI 同款 | ✓ | 0.9.26 | — |

**Missing dependencies with no fallback:**
- 无。真实 GGUF 冒烟是可选手工检查；自动化测试用 fake generator（不依赖模型）。

**Missing dependencies with fallback:**
- `torch`/`embed`：用 `uv` 同步或走 CI；定向测试加 `--no-cov` 且避开 `tests/unit/inference/test_reranker.py`。
- `llama_cpp`/`jinja2`：lazy import + fake 测试；真实冒烟用 scratch venv。

## Validation Architecture

> `workflow.nyquist_validation` 为 `true`（`.planning/config.json` 已核实），故本节必填。

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 9.2.0 + pytest-cov |
| Config file | `pyproject.toml` → `[tool.pytest.ini_options]`（`addopts = "--cov=src/sif --cov-report=term-missing --cov-report=html --cov-report=xml"`）与 `[tool.coverage.report] fail_under = 90` |
| Quick run command | `.venv/bin/python -m pytest tests/unit/search/test_anchor.py tests/unit/search/test_bm25.py tests/unit/search/test_hybrid.py tests/unit/cli/test_search_anchor.py -q --no-cov` |
| Full suite command | `uv sync --frozen --extra dev --extra embed && uv run --frozen pytest`（本机 `.venv` 无 torch，直接 `pytest` 会在 `tests/unit/inference/test_reranker.py` 收集失败） |
| Contract pair（零改动证明） | `.venv/bin/python -m pytest tests/unit/mcp/test_wire_transcripts.py tests/unit/mcp/test_packaging.py -q --no-cov` → 期望 `13 passed` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| ANC-01 | `anchor:` / `--anchor` 走 ANCHOR（纯 BM25）；关闭时零构造零模型加载 | unit + CLI | `pytest tests/unit/search/test_hybrid.py::test_pipeline_prefix_anchor_routes_to_bm25 tests/unit/cli/test_search_anchor.py -q --no-cov` | ❌ Wave 0 |
| ANC-01 | 默认路径 byte-identical：无锚点时 `_build_fts_query` 输出不变；`sif.search.anchor` 不进 `sys.modules` | unit | `pytest tests/unit/search/test_bm25.py -q --no-cov` | ✅ 扩展 |
| ANC-02 | highlight / snippet 用原始 query（不含锚点词） | unit | `pytest tests/unit/search/test_anchor.py::test_anchor_route_highlights_use_original_query -q` | ❌ Wave 0 |
| ANC-03 | `SearchType.ANCHOR` 存在；`SearchOptions.anchor_terms` 默认 None；两处前缀表 key 集合相同 | unit | `pytest tests/unit/search/test_anchor.py tests/unit/mcp/test_backend_anchor.py -q` | ❌ Wave 0 |
| ANC-04 | `replace(options, anchor_terms=[...])` 只改 BM25 腿；默认 None 结果不变 | unit | `pytest tests/unit/search/test_hybrid.py -q` | ✅ 扩展 |
| ANC-05 | 守卫默认关；开启后 OOV 锚点被丢弃且行为可用 | unit | `pytest tests/unit/search/test_anchor.py::TestVocabGuard -q` | ❌ Wave 0 |
| GEN-01 | prompt 版本冻结、greedy 参数、≤10 术语、去重、解析鲁棒 | unit | `pytest tests/unit/search/test_anchor.py::TestTermParsing -q` | ❌ Wave 0 |
| GEN-02 | 同 query 第二次 0 次生成；45×N 模拟 → N 次 | unit | `pytest tests/unit/search/test_anchor.py::TestAnchorCache -q` | ❌ Wave 0 |
| GEN-03 | 超时/异常 fail-open：结果与 `lex:` 完全一致、单次 warning、reason 可复现；预算超限报错 | unit | `pytest tests/unit/search/test_anchor.py::TestFailOpen tests/unit/search/test_anchor.py::TestBudget -q` | ❌ Wave 0 |
| GEN-04 | 默认无网络（把 `socket.socket` monkeypatch 成抛异常仍可跑）；远程 opt-in 披露一次；本地生成 lazy | unit | `pytest tests/unit/search/test_anchor.py::TestNoNetworkByDefault -q` | ❌ Wave 0 |
| CTR-03 | `src/sif` 无 `.gguf`；许可条款在 docs + PROJECT.md | unit + docs | `pytest tests/test_packaging_assets.py tests/test_docs.py -q --no-cov` | ❌ Wave 0 |
| CTR-04 | docs-generate 零 diff；coverage ≥90；MCP 契约 13 passed | CI / gate | `python scripts/generate_cli_ref.py && python scripts/generate_config_ref.py && git diff --exit-code docs/cli-reference.md docs/configuration.md`；`uv run --frozen pytest` | ✅ 既有脚本 |

### Deterministic-cache hit proof（GEN-02 的具体证明）

1. **同进程第二次命中**：真 sqlite（`tmp_path`）建 schema；fake generator 计数器；同一 resolver `resolve(q)` 两次 → `generator.calls == 1`、第二次 `cache_hits == 1`。
2. **跨实例命中（模拟跨进程）**：在同一个 DB 上新建第二个 resolver（不共享内存）→ 仍 `calls == 1`；证明缓存不是进程内 LRU。
3. **45 配置 × N 查询**：`for config in iter_grid(): for q in queries:` 里每步 `replace(options, rrf_k=..., bm25_weight=..., vector_weight=..., anchor_terms=resolver.resolve(q))` → 断言 `generator.calls == len(queries)`、`cache_hits == 45*len(queries) - len(queries)`。
4. **TTL 失效**：写入后把 `expires_at` 改成过去（或 `anchor_cache_ttl=0` 后 `clear_expired()`）→ 下一次重新生成。
5. **失败不缓存**：generator 抛异常 → 无新行；第二次仍尝试一次（但受实例失败锁存保护，同一实例内不重复）。

### Fail-open reproduction（GEN-03 的具体证明）

- 用 `fake_generator(side_effect=TimeoutError)`：`pipeline.search("anchor:Q")` 的结果与 `pipeline.search("lex:Q")` **逐行相等**（document_id/score/rank/snippet/highlights），`caplog` 中 warning 恰好 1 条；两次运行 reason 相同 → 可复现。
- 预算：`SIF_ANCHOR_MAX_CALLS=1` + 两条不同 query → 第二次抛 `AnchorBudgetExceeded`，CLI 转 `ClickException` 且不重试。
- 后端不可用时 fallback 到规则锚点（不是无锚点）：`anchor_backend=gguf` + 不存在的 path → 一次 warning + 规则锚点 + `reason="unconfigured"`。

### Byte-identical default path proof（成功标准 1）

- `SearchOptions()` 的 `anchor_terms is None`；`_build_fts_query("hello world")` == `'"hello"* AND "world"*'`（钉死字面量）。
- 非 anchor 查询后 `"sif.search.anchor" not in sys.modules`（lazy import 的机械证明）+ `LLMCacheRepository` 未被调用（spy）。
- 既有 SC1 golden / 默认路径快照测试全绿（不重写）。
- CLI：`query`（无 flag、无前缀）的 stdout 与既有快照一致；`--anchor` 不构造 `EmbeddingManager`（patch `from_settings` 为 `AssertionError`）。

### Sampling Rate

- **Per task commit:** 相关定向文件 + `--no-cov`；涉及 BM25/路由的任务加跑 `tests/unit/search/test_hybrid.py`。
- **Per wave merge:** 定向集合（search + mcp + cli）全绿；`tests/unit/mcp/test_wire_transcripts.py tests/unit/mcp/test_packaging.py -q --no-cov` 仍 `13 passed`。
- **Phase gate:** `uv run --frozen pytest` 全量绿且 coverage ≥90；`make docs-generate` 后 `git diff` 为空；8-cell CI 全绿；`src/sif` 无 `.gguf`；并重跑 Phase 25 的 11 文件 `shasum -a 256` 清单（`pyproject.toml`、`uv.lock`、`src/sif/mcp/protocol.py`、`src/sif/mcp/tools.py`、两个 MCP 测试文件、5 份 goldens）与 `25-CONTRACT-FREEZE.md` 的 END manifest 逐行比对——本阶段预期这 11 个文件**全部不变**（新增 GGUF 守卫放新文件，不改 `test_packaging.py`）。

### Wave 0 Gaps

- [ ] `tests/unit/search/test_anchor.py` — 规则表/解析/缓存/失败/预算/守卫/无网络（≈20-25 用例）
- [ ] `tests/unit/search/test_hybrid.py` 扩展 — ANCHOR 前缀、ANCHOR route、highlight 原 query、零构造
- [ ] `tests/unit/search/test_bm25.py` 扩展 — `_build_fts_query` 的 anchor OR 形式与默认形式
- [ ] `tests/unit/mcp/test_backend_anchor.py` — `anchor:` 不加载 embedder、与 `lex:` 同构、不写缓存
- [ ] `tests/unit/cli/test_search_anchor.py` — `--anchor` 等价前缀、不构造 EmbeddingManager、`--explain` stderr 行、失败告警
- [ ] `tests/test_packaging_assets.py` — `src/sif/**/*.gguf` 为空 + pyproject 无 gguf include
- [ ] `tests/unit/config/test_settings_anchor.py`（或并入既有 settings 测试）— 新字段默认值/validator/`SECTIONS` 覆盖
- [ ] 共享 fake：`FakeAnchorGenerator`（计数 + 可注入异常/超时）建议放 `tests/support/` 或测试模块内
- [ ] 环境：跑全量前 `uv sync --frozen --extra dev --extra embed`

## Security Domain

> `security_enforcement` 未显式关闭 → 视为启用。

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | 无认证面。 |
| V3 Session Management | no | 无会话。 |
| V4 Access Control | no | 单用户本地；MCP 保持只读。 |
| V5 Input Validation | **yes** | 查询与锚点术语经 `_sanitize_term`（锚点按整体调用）进 FTS，值一律绑定参数、绝不拼接；`anchor_model_path` 必须为存在的绝对 `.gguf`；`anchor_api_base` 复用 `http(s)` 校验；远程响应 JSON 用类型白名单解析，畸形即当 miss。 |
| V6 Cryptography | **yes**（仅哈希） | `hashlib.sha256` 构造缓存键；不手写。 |
| V12 Files/Resources | yes | 只写主 DB 的 `llm_cache`；不写任何文件缓存；GGUF 只读。 |
| V14 Configuration | yes | 新字段走 `SIF_ANCHOR_*`，`extra="ignore"`；不新增 runtime 依赖。 |

### Known Threat Patterns for this stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| 查询文本外发到远程端点（隐私） | Information disclosure | 远程后端显式 opt-in；启用时一次性 stderr 披露 `base_url`；文档写明 local-first 默认无请求。 |
| Prompt injection（查询里塞指令让模型输出垃圾） | Tampering | 输出只被当作候选词：≤10 条、≤64 字符、≤6 词、字符白名单、FTS 转义；不执行任何工具/命令。 |
| FTS 语法注入（`"`, `*`, `(`, `)`, `:`） | Tampering | `_sanitize_term` 已剥离；锚点走同一函数；所有 SQL 参数绑定。 |
| 缓存投毒（畸形 response 被当 terms） | Tampering | 只接受 JSON `{"version":1,"terms":[...]}`；校验失败视为 miss 并覆盖；不抛异常。 |
| SSRF / 错误端点 | Tampering | 仅 http(s)；仅显式配置；不做交互式确认（D-15）；key 只在 Authorization。 |
| 密钥泄漏 | Information disclosure | `anchor_api_key` 用 `repr=False, exclude=True`（既有 `api_key` 先例）；日志不打印 key。 |
| 资源耗尽（45N 生成、超长生成） | DoS | `SIF_ANCHOR_MAX_CALLS` 硬护栏；`max_tokens`；deadline stopping criteria；HTTP timeout。 |
| 只读契约被写操作破坏 | Tampering | MCP `anchor:` 只用规则锚点、只读连接、不写 `llm_cache`。 |
| 路径穿越 / 意外模型下载 | Tampering | 绝对路径 + 存在性 + `.gguf` 后缀校验；`Llama(model_path=...)` 不会下载。 |

## Sources

### Primary（HIGH confidence，本会话读取/实测）

- In-repo（Read this session）: `src/sif/core/models.py`、`src/sif/search/bm25.py`、`src/sif/search/hybrid.py`、`src/sif/mcp/backend.py`、`src/sif/mcp/protocol.py`、`src/sif/cli/commands/search.py`、`src/sif/cli/main.py`、`src/sif/database/repositories.py`、`src/sif/database/schema.py`、`src/sif/config/settings.py`、`src/sif/search/benchmark.py`、`src/sif/search/rrf.py`、`src/sif/cli/commands/pull.py`、`scripts/generate_config_ref.py`、`scripts/generate_cli_ref.py`、`pyproject.toml`、`Makefile`、`.github/workflows/test-matrix.yml`、`.github/workflows/docs.yml`、`tests/unit/cli/test_search.py`、`tests/unit/search/test_hybrid.py`、`tests/unit/search/test_bm25.py`、`tests/unit/database/test_repositories.py`、`tests/unit/mcp/test_packaging.py`、`tests/test_docs.py`、`tests/test_hygiene.py`、`docs/models.md`、`docs/architecture.md`、`docs/testing.md`、`docs/models.md`。
- Phase 25 证据：`.planning/phases/25-contract-freeze-feasibility-spike/25-CONTRACT-FREEZE.md`、`bench/spike-verdict.json`、`bench/anchor-table.json`、`.planning/tmp/phase-25/spike_delta.py`、`probe-upgrade-0.3.37.log`。
- 0.3.37 库源码（scratch venv）：`llama_cpp/llama.py:459-466, 496-536, 999, 1587-1591`、`llama_cpp/llama_chat_format.py:167-177, 194-302`。
- 本会话执行的 FTS5 探针：OR 语法、porter 词干词表、CJK 单 token、短语匹配；以及 36 条 tuning 查询的 AND/OR 对照（见 Measured evidence）。
- `.planning/PROJECT.md:216`（LFM3 许可 Key Decision，状态 `— Pending`）。

### Secondary（MEDIUM confidence）

- llama-cpp-python 的 `create_chat_completion` 优先使用 GGUF `tokenizer.chat_template`、`create_completion` 不包装模板 — 与 0.3.37 源码一致（`llama.py:519-562`），并有公开 PR/文档佐证。
- Web 检索结果对 0.3.37/0.3.38 的 PyPI 状态存在冲突（有来源称 PyPI 最新为 0.3.36）；本机证据以隔离 venv 为准：`0.3.37` 可安装、可加载 `lfm3`。文档措辞应写「Phase 25 实测 0.3.37 可用」而非断言 PyPI 现状。

### Tertiary（LOW confidence）

- 远程 OpenAI-compatible 端点的具体响应形状与错误码（未在本机对真实端点验证）。
- 规则锚点表的跨语料泛化性（仅 tuning 集有证据）。
- Web 旁证（仅用于交叉核对，权威结论以本机 0.3.37 源码与 FTS5 实测为准）：
  - <https://github.com/abetlen/llama-cpp-python/pull/1440> — `chat_format` / `tokenizer.chat_template` 的优先级说明（与 `llama.py:519-562` 一致）。
  - <https://www.itflashcards.com/cheatsheets/sqlite/fts5/> — FTS5 `AND`/`OR`/短语/前缀语法速查（非官方镜像；实际行为已在本机 SQLite 3.47.2 上复验）。
  - <https://llama-cpp-python.readthedocs.io/en/latest/changelog/> — 版本线参考（未解析出 0.3.37 条目；以隔离 venv 的安装事实为准）。

## Metadata

**Confidence breakdown:**
- Standard stack / in-repo surfaces: **HIGH** — 逐行读取并附原文引用。
- 锚点 OR 语义与实测 delta: **HIGH** — 本会话在同一 fixture/DB 上直接测量，两个设计对照 36/36 与 6/0。
- 0.3.37 生成 API（chat template / stopping criteria）: **HIGH** — 读库源码 + 导入验证符号。
- 远程后端与真实端到端: **MEDIUM** — 未对真实端点/真实 GGUF 跑完整链。
- 规则表泛化性: **LOW** — 只有 tuning 证据，held-out 属 Phase 27。

**Research date:** 2026-11-28
**Valid until:** ~2027-01-31（in-repo 契约面与 0.3.37 API 稳定；若 `llama-cpp-python` pin 变动或 `prefix_map`/`SECTIONS` 重构，需重取）
