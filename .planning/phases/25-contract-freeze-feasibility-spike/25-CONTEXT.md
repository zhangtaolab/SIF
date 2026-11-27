# Phase 25: Contract Freeze & Feasibility Spike - Context

**Gathered:** 2026-11-27
**Status:** Ready for planning

<domain>
## Phase Boundary

在写任何新代码前，用可复核证据完成三件事：

1. 用 SIF 锁定的 `llama-cpp-python==0.3.35` 证明 `Llama(model_path=LFM3-1.7B-Q4_K_M.gguf)` 能加载并生成一次；若不兼容，在隔离环境里给出升级或外部 `llama-server` 退路及对现有 GGUF embed/rerank 路径影响的可复核结论。
2. 用固定/规则锚点在现有 fixture 上跑 `lex:` → `anchor:` 配对对比，产出可复现的方向性信号判定与 delta 表；「无方向性信号」即归档假设、不启动 Phase 26/27、工作树不留半成品代码。
3. 冻结 MCP 7 工具、5 份 wire goldens、`QueryInput` 与 13 项 runtime 依赖，使「逐字节未变」可被核对。

In scope: 一次性 spike 脚本/日志、兼容性结论、配对 delta 表、契约冻结哈希清单、verdict/止损记录、phase 目录内的证据 artifact、STATE 会话注记。

Out of scope: 任何 `src/sif` 产品代码、`anchor:` 检索臂实现、`SearchType.ANCHOR`、MCP schema 变更、新增 runtime 依赖、CI/workflow 改动、Phase 26/27 的正式评测或默认切换、Web UI / REST / `sif serve`。本阶段无 SPEC.md；范围以 `.planning/ROADMAP.md` 与 `.planning/REQUIREMENTS.md` 为准。

</domain>

<decisions>
## Implementation Decisions

### Locked upstream — do not re-litigate

- v1.3 只做 LLM Anchor；Web UI 推迟 v1.4，`Web UI` 与 `chat-with-notes / ask` 的 Out of Scope 条款不反转。
- LFM3-1.7B-GGUF Q4_K_M 是用户自行下载的可选实验臂，不打进 wheel/sdist、不默认启用、不自动下载。
- MCP 7 工具、5 份 wire goldens、`QueryInput` 不变；不新增 MCP `anchor` 请求字段；零新增 runtime 依赖；`test_packaging.py` 冻结的 13 项核心依赖不变。
- 无方向性信号时归档假设、不投 Phase 26/27、工作树不留半成品代码；`keep-default` 是有效交付。
- Phase 18/23/24 的 0.01 tie rule、10,000 次 bootstrap、held-out、N / `1/N` 噪声地板属于 Phase 27 的正式门禁；Phase 25 只判方向性信号，不提前消费这些门禁。
- 本阶段无 UI 决定，因此不触发静态 HTML 多方案对照。

### A. `lfm3` 兼容性与证据（SPK-01）

- **D-01:** Spike 用显式 `--model-path /abs/path` 接收用户自行下载的 GGUF；不写死本机绝对路径，不自动下载，不改模型缓存，不用环境变量作为唯一入口。
- **D-02:** 「成功加载并生成一次」= 直接构造 `Llama(model_path=...)`（不带 `embedding=True`），用 greedy / temperature 0 的固定短 prompt 产出一次非空文本并落盘。`LlamaCppEmbedder` 的 `Llama(..., embedding=True)` 是 embedding 路径，不能当生成证明；仅 import / 读元数据不算成功。
- **D-03:** 若锁定的 0.3.35 不兼容，只在临时隔离 venv 里试升级 `llama-cpp-python`，并记录升级后对 `LlamaCppEmbedder` / GGUF rerank 路径的影响；`pyproject.toml` 与 `uv.lock` 哈希保持不变。外部 `llama-server` 只作补充证据，不单独作为结论；只记录失败不满足成功标准 1。 — **Reversibility:** reversible — 隔离 venv 可删除，主依赖契约不动。
- **D-04:** 兼容性 artifact 至少记录：`llama_cpp` 版本、GGUF SHA256、完整命令、chat template、一次生成输出、错误栈、embed/rerank 回归判定。原始日志可另放 `.planning/tmp/`，但不作为唯一交付。

### B. 确定性锚点信号判定（SPK-02）

- **D-05:** 固定/规则锚点只从 query 本身派生（缩写/同义/组合词 + 一张提交的 query-only 映射表），不调用 LLM、不读 gold/relevance、不读 gold 文档标题或路径。从 gold 抽词会泄漏标签并污染 Phase 26/27，明确不采用。 — **Reversibility:** costly — 若改回 gold-derived anchors，已产出的 delta 表失去可证伪性，必须重跑整个 spike 并重写 verdict。
- **D-06:** 只读 `tests/fixtures/bench/queries.json` 的 `tuning` split；`heldout` 留给 Phase 27，artifact 记录 heldout 未被读取。使用整个 committed fixture 会造成 heldout peeking；另造合成 fixture 偏离 ROADMAP 的「现有 fixture」。 — **Reversibility:** costly — 若改用 heldout 做 go/no-go，Phase 27 的 held-out 集合会被提前消费，需要重建独立 heldout 或重新取样。
- **D-07:** 配对 delta 表主指标是 `paired nDCG@10`，复用 `src/sif/search/benchmark.py` 的 `SearchEvaluator` / `ndcg_at_k`；`Hit@10` 与 `Recall@10` 作为附加诊断列，`recall_at_k` 的 `total_relevant` 口径由 planner 核对。不以 Recall@10 或 Hit@10 作主判定。
- **D-08:** 「有方向性信号」= 平均 paired delta > 0 且 helped > hurt，并记录 helped/hurt/unchanged 与 N / `1/N`。固定种子 + 同一 fixture + 同一锚点表重跑得到相同 delta 表即通过。不提前使用 0.01 + bootstrap CI 排除 0 的 Phase 27 升默认门禁，也不接受「任何正 delta 即算有」。 — **Reversibility:** costly — 阈值改动会让已发布的 stop/go verdict 失效，必须重跑并重新归档。

### C. 契约冻结（CTR-01 / CTR-02）

- **D-09:** 冻结锚点写 `v1.2.5 (6c25e88d9913)`，artifact 同时记录讨论时 HEAD `7c2fb7918a45`。已核实 `v1.2.5..HEAD` 只有 docs 提交，契约文件零改动；当前 HEAD 与 plan 执行前重取都不作主锚点。 — **Reversibility:** one-way — 重新定义已发布 tag 上的契约基线会使所有已核对的 goldens / 依赖哈希失效，必须重跑冻结证明并公告基线变更。
- **D-10:** 用 SHA-256 清单 + 现有 `tests/unit/mcp/test_wire_transcripts.py` / `tests/unit/mcp/test_packaging.py` 证明逐字节未变；不新增 `src/sif` 代码，不在 Phase 25 新增 pytest 守卫，也不只在文档里写哈希。清单放 phase 目录，plan 开始与结束各跑一次 `shasum` + 两个现有测试。
- **D-11:** 冻结清单覆盖：5 份 `tests/unit/mcp/goldens/*.json`、`tests/unit/mcp/test_wire_transcripts.py`、`tests/unit/mcp/test_packaging.py`、`src/sif/mcp/protocol.py`（`QueryInput`）、`src/sif/mcp/tools.py`（7 工具）、`pyproject.toml`、`uv.lock`（13 依赖与 `llama-cpp-python==0.3.35`）。最小字面集无法核对 7 工具 / `QueryInput` / 零新增依赖；整个 MCP 目录会误锁合法重构。
- **D-12:** 首尾双次核对：开始/结束两次哈希输出都进 artifact，任一不一致即判失败；不加 CI 步骤，也不只记一次。

### D. Spike 产物与止损归档（SPK-03）

- **D-13:** 一次性脚本与 scratch DB 放 `.planning/tmp/phase-25/`（`.gitignore` 已忽略 `.planning/tmp/`），只提交 phase 目录里的证据；可复现命令写进 runbook。不把一次性脚本提交到 `scripts/`，也不全临时不落盘。
- **D-14:** 证据 artifact = `25-CONTRACT-FREEZE.md` + `bench/spike-delta.csv` + `bench/spike-verdict.json`，JSON 为权威、三者同源生成；沿用 23/24 的 phase-dir `bench/*.json` 惯例。不单独使用单个 JSON 或单个 Markdown 表。
- **D-15:** 判定「无方向性信号」时写 `25-SPIKE-VERDICT.md` + `bench/spike-verdict.json`，并通过 `gsd_run state.record-session` 记录「归档假设、Phase 26/27 未启动、工作树清洁」；ROADMAP 阶段不勾选。只更新 ROADMAP/STATE 或只留 JSON 都不采用。 — **Reversibility:** costly — verdict 一旦写入 STATE / ROADMAP 会话记录，改动需要重新走状态更新与审计链。
- **D-16:** 「工作树不留半成品代码」= artifact 贴 `git status --porcelain` 并逐条解释 3 个未跟踪 planning 文档（`.planning/.continue-here.md`、`.planning/HANDOFF.json`、`.planning/v1.3-ui-anchor-milestone-research.md`）是研究/交接稿；`src/`、`tests/`、`pyproject.toml`、`uv.lock` 必须零改动，任何代码/依赖改动即失败。严格 zero untracked 与不记录状态都不采用。

### Claude's Discretion

用户 16 题全部选择推荐项，未另行指定细节。以下执行细节留给 researcher / planner 在锁定决策范围内决定：

- `--model-path` 的精确 flag 拼写、固定短 prompt 文本、chat template 处理、一次生成输出的长度上限。
- 隔离 venv 的目标 `llama-cpp-python` 版本、venv 路径、升级失败时的错误记录格式。
- query-only 锚点映射表的文件格式、具体词条、派生规则、固定种子数值。
- `N` / `1/N` / `helped/hurt/unchanged` 在 CSV / JSON 中的字段命名与精度。
- SHA-256 清单文件名与 schema、`shasum` 与两个现有测试的确切命令、首尾两次输出的排版。
- `25-CONTRACT-FREEZE.md` / `25-SPIKE-VERDICT.md` / `bench/spike-delta.csv` / `bench/spike-verdict.json` 的字段顺序与同源生成方式。
- 3 个未跟踪 planning 文档白名单在 artifact 中的呈现格式；`git status --porcelain` 快照的保存方式。
- runbook 的命令编排与临时脚本命名；只要不进入 `src/sif`、`tests/`、`pyproject.toml`、`uv.lock` 即可。

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Scope and requirements

- `.planning/ROADMAP.md` §Phase 25 — goal, first plan, kill criterion, four success criteria
- `.planning/REQUIREMENTS.md` — SPK-01, SPK-02, SPK-03, CTR-01, CTR-02, Out of Scope, traceability
- `.planning/PROJECT.md` — Current Milestone v1.3, Key Decisions（LFM3 定位 / 止损 / 契约 / Web UI 推迟）, Constraints
- `.planning/STATE.md` — current position, accumulated decisions, session continuity
- `.planning/config.json` — `workflow.auto_advance`, `workflow.discuss_mode`, `workflow.text_mode`, `mode: yolo`

### Research basis

- `.planning/research/UI-FRONTEND.md` — v1.3 研究基础；Web UI 部分已推迟 v1.4，不作为本阶段范围
- `.planning/v1.3-ui-anchor-milestone-research.md` — v1.3 范围研究；其 5-phase / UI 结构已被 3-phase roadmap 取代，但代码勘察与契约判断仍适用
- `../../Downloads/SIF-LLM-Anchor-Implementation-Guide.md` — LLM Anchor 论文/实现指南；模型推荐 Qwen3.5-4B 已被 `PROJECT.md` 的 LFM3 决策取代，评测纪律与 cache/PRF 边界仍适用（workspace-external；绝对路径 `/Users/forrest/Downloads/SIF-LLM-Anchor-Implementation-Guide.md`）

### Prior phase decisions and artifact conventions

- `.planning/milestones/v1.2-phases/18-quality-instrument-personal-bench-rapidfuzz-dym/18-CONTEXT.md` — 0.01 tie rule、10,000 bootstrap、tuning/heldout、saved-run 纪律
- `.planning/milestones/v1.2-phases/19-search-correctness/19-CONTEXT.md` — B0 基线纪律、byte-identical 默认路径
- `.planning/milestones/v1.2-phases/22-mcp-sdk-v2-modernization-agent-packaging/22-CONTEXT.md` — 7 只读工具、5 wire goldens、冻结 envelope、SDK 契约
- `.planning/milestones/v1.2-phases/23-harrier-gated-evaluation/23-CONTEXT.md` — 隔离双臂、identity、adequacy、verdict artifact、keep-default
- `.planning/milestones/v1.2-phases/24-tuning-models-ux-install-docs/24-CONTEXT.md` — held-out gate、scratch/artifact 惯例、generator-owned docs
- `.planning/milestones/v1.2-phases/19-search-correctness/bench/b0.json` — committed baseline artifact 惯例
- `.planning/milestones/v1.2-phases/23-harrier-gated-evaluation/bench/harrier-verdict.json` — verdict JSON 惯例
- `.planning/milestones/v1.2-phases/24-tuning-models-ux-install-docs/bench/chunk-sweep.json` — phase-dir `bench/*.json` 惯例
- `docs/benchmarking.md` — held-out 证据与 verdict 记录风格

### Code anchors

- `pyproject.toml` — 13 项 runtime 依赖、`llama-cpp-python>=0.3.35`、coverage gate
- `uv.lock` — `llama-cpp-python==0.3.35` 锁定解析
- `src/sif/embedding/embedder.py` — `LlamaCppEmbedder` 的 `Llama(..., embedding=True)` 与 `create_completion` 参考
- `src/sif/search/hybrid.py` — `prefix_map` 目前只有 `lex:` / `vec:` / `hyde:` / `expand:`，无 `anchor:`
- `src/sif/search/benchmark.py` — `SearchEvaluator`、`ndcg_at_k`、`hit_at_k`、`recall_at_k`、`warrants_default_change`
- `tests/fixtures/bench/queries.json` — 含 `tuning` / `heldout` 的 graded fixture
- `tests/fixtures/bench/heldout_defaults.json` — held-out 默认值与基线
- `src/sif/mcp/protocol.py` — `QueryInput` 与 MCP I/O 模型
- `src/sif/mcp/tools.py` — 7 个只读工具的注册与顺序
- `tests/unit/mcp/test_wire_transcripts.py` — 5 份 goldens 的加载 / 归一化 / 重生成门禁
- `tests/unit/mcp/goldens/2024-11-05.json`
- `tests/unit/mcp/goldens/2025-03-26.json`
- `tests/unit/mcp/goldens/2025-06-18.json`
- `tests/unit/mcp/goldens/2025-11-25.json`
- `tests/unit/mcp/goldens/2026-07-28.json`
- `tests/unit/mcp/test_packaging.py` — 13 项 runtime 依赖冻结断言
- `.gitignore` — `.planning/tmp/` scratch 忽略规则

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets

- `src/sif/search/benchmark.py`: `SearchEvaluator`、`ndcg_at_k`、`hit_at_k`、`recall_at_k` 可直接支撑配对 delta 表；`warrants_default_change` 是 Phase 27 门禁，不在 Phase 25 使用。
- `tests/fixtures/bench/queries.json`: 现成的 graded fixture，含 `category` / `split` / `relevance`；spike 只消费 `split=tuning` 行。
- `src/sif/embedding/embedder.py`: `LlamaCppEmbedder.create_completion` 是生成接口的形状参考，但 spike 必须直接构造不带 `embedding=True` 的 `Llama`。
- `tests/unit/mcp/test_wire_transcripts.py` + `tests/unit/mcp/goldens/*.json`: 现有 wire 契约证明，不需要重写。
- `tests/unit/mcp/test_packaging.py`: 现有 13 依赖冻结证明，不需要新增依赖守卫。
- `.planning/tmp/`: 已 gitignored，适合一次性脚本、scratch DB、原始日志。
- 23/24 的 phase-dir `bench/*.json` + `*-CONTEXT.md` + `*-SUMMARY.md`: 证据 artifact 与 verdict 的现成排版惯例。

### Established Patterns

- 零新增 runtime 依赖；`pyproject.toml` / `uv.lock` 在 spike 期间必须保持哈希不变。
- 默认路径 byte-identical；MCP 7 工具 / 5 goldens / `QueryInput` 冻结。
- scratch DB 与一次性脚本放 gitignored 目录，提交的只是 verdict / delta / 哈希清单。
- held-out 纪律：tuning 用于方向性判断，heldout 留给 Phase 27；`keep-default` / no-signal 是有效交付。
- 文档分 generator-owned 与 hand-maintained；本阶段不改 CLI / Settings，因此不触发 `make docs-generate`。
- STATE.md / ROADMAP.md 不直接编辑；会话与状态变化走 `gsd_run`。
- CLI 错误用 `click.ClickException`；非 TTY 输出保持纯文本 / JSON。本阶段一次性脚本的失败面也沿用该约定。

### Integration Points

- `pyproject.toml` / `uv.lock`: `llama-cpp-python==0.3.35` 是兼容性 spike 的锁定输入；隔离 venv 试升级不得回写这两个文件。
- `src/sif/embedding/embedder.py`: 记录升级对 `LlamaCppEmbedder` / GGUF rerank 路径的影响。
- `src/sif/mcp/protocol.py` + `src/sif/mcp/tools.py`: 7 工具与 `QueryInput` 的冻结面。
- `tests/unit/mcp/goldens/`: 5 份逐字节冻结的 wire transcripts。
- `tests/unit/mcp/test_packaging.py`: 13 项依赖冻结断言。
- `tests/fixtures/bench/queries.json`: 配对 delta 表的唯一查询来源；`heldout` 行不读取。
- `.planning/tmp/phase-25/`: 一次性脚本 / scratch DB / 原始日志。
- `.planning/phases/25-contract-freeze-feasibility-spike/`: `25-CONTRACT-FREEZE.md`、`bench/spike-delta.csv`、`bench/spike-verdict.json`、`25-SPIKE-VERDICT.md`、`25-CONTEXT.md`、`25-DISCUSSION-LOG.md`。
- `.planning/STATE.md`: 通过 `gsd_run state.record-session` 写会话注记；`.planning/ROADMAP.md` 的 Phase 25 checkbox 在 no-signal 时不勾选。

</code_context>

<specifics>
## Specific Ideas

- 冻结基线：`v1.2.5 (6c25e88d9913)`；讨论时 HEAD `7c2fb7918a45`；`v1.2.5..HEAD` 的 4 个提交全部是 docs / state / scripts artifact-path 修正，契约文件零 diff。
- 用户自行下载的 GGUF 文件名：`LFM3-1.7B-Q4_K_M.gguf`；仓库内当前没有 `lfm3` 字符串，也没有 `anchor:` / `SearchType.ANCHOR` 实现。
- 当前 `prefix_map` 只有 `lex:` / `vec:` / `hyde:` / `expand:`；`LlamaCppEmbedder` 用 `embedding=True`，所以不能复用它来证明生成。
- 讨论时实测的 SHA-256 冻结清单（相对仓库根）：

| Path | SHA-256 |
|---|---|
| `pyproject.toml` | `6fa950c66a6a44f6bb16209048a10321ef09966ac20b9aee06ba3af8bc225690` |
| `uv.lock` | `b0175d451e4f8c127da90ffeef94d049a5f181d36743076eaae42b102ea5a308` |
| `tests/unit/mcp/test_wire_transcripts.py` | `221c8a68fdf639d4b46e5b0df2fd4b0930b5aa5756c0b71307e0eccc2afd5854` |
| `tests/unit/mcp/test_packaging.py` | `b5f08b4d5f0b3405784c880e741989250ff5eaef9a8d6535913698ed6319e5a7` |
| `src/sif/mcp/protocol.py` | `00312cb082fec485b40fcaade9fc035eb65a2c8a092f9122b33ea1b5087c4638` |
| `src/sif/mcp/tools.py` | `70c1e306dd2c191a929ac011458f6a60cf1146b26705e53c565852b7a9082921` |
| `tests/unit/mcp/goldens/2024-11-05.json` | `1c425585808515b466cc261223cefa1cd36602bcd27b46510d2ea0289d353b7a` |
| `tests/unit/mcp/goldens/2025-03-26.json` | `395a3750876f79b5dac8bc359314038669ecffa11db06cb20f469a9d8dc8ff93` |
| `tests/unit/mcp/goldens/2025-06-18.json` | `608a563ce1a5ee997787170e8e09ae75e441c62eef00e03806962e548cba700f` |
| `tests/unit/mcp/goldens/2025-11-25.json` | `b96fb5cba5e54cedcb154c335ee4e88e97af5e950a402ecdeb21ab82d370d806` |
| `tests/unit/mcp/goldens/2026-07-28.json` | `1246e23c1d9580bc8d0c18a7641a27dadfeb9781115a0b879103dc0d3ed8cec5` |

- 工作树白名单（讨论时未跟踪、非代码）：`.planning/.continue-here.md`、`.planning/HANDOFF.json`、`.planning/v1.3-ui-anchor-milestone-research.md`。
- 16 个讨论题全部采用推荐项；每题的备选项与优劣记录在 `25-DISCUSSION-LOG.md`。

</specifics>

<deferred>
## Deferred Ideas

- 新增 pytest 契约守卫或 CI 防漂移步骤：Phase 25 明确不新增工程面；若 Phase 26 需要持续防漂移再单列。
- 把外部 `llama-server` 作为正式退路结论：本阶段只作补充证据；正式支持属于新后端能力，单独立项。
- 把一次性 spike 脚本提交到 `scripts/`、或要求严格 zero untracked：前者会留下半成品代码，后者需先处理 3 个已存在的 planning 文档，均超出 Phase 25。
- 使用 gold-derived anchors、整个 committed fixture、0.01 + CI 门禁、任何正 delta 即算有：这些是明确否决的备选项，不是延期功能；完整记录见 `25-DISCUSSION-LOG.md`。

No new capability requests were raised — discussion stayed within phase scope.

</deferred>

---

*Phase: 25-Contract Freeze & Feasibility Spike*
*Context gathered: 2026-11-27*
