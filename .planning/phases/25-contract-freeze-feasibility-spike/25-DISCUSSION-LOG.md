# Phase 25: Contract Freeze & Feasibility Spike - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-11-27
**Phase:** 25-Contract Freeze & Feasibility Spike
**Areas discussed:** A. lfm3 证据与退路, B. 信号判定口径, C. 契约冻结基线, D. 产物与止损归档

---

## Gray Area Selection

| Option | Description | Selected |
|--------|-------------|----------|
| lfm3 证据与退路 | 把「加载成功/生成一次」与 0.3.35 不兼容时的升级/外部 llama-server 退路定清楚；当前仓库无 lfm3 实现，且 LlamaCppEmbedder 用 embedding=True。 | ✓ |
| 信号判定口径 | 明确固定/规则锚点、fixture、指标与「有方向性信号」阈值；直接决定止损；不建议把 Phase 27 的 0.01/CI 门禁提前套到 spike。 | ✓ |
| 契约冻结基线 | 用 HEAD + SHA-256 清单/现有测试把「逐字节未变」变成可核对事实；需划清证据脚本与产品代码。 | ✓ |
| 产物与止损归档 | 定下 evidence artifact 位置、是否提交一次性 runbook，以及无信号时如何归档假设/保持工作树干净。 | ✓ |

**User's choice:** 全部 4 个灰区。
**Notes:** 用户要求中文讨论，并在每个选项里给优劣与推荐意见；本阶段无 UI 决定，未触发静态 HTML 多方案对照。

---

## A. lfm3 证据与退路

### A1. Spike 如何拿到用户自行下载的 GGUF 路径？

| Option | Description | Selected |
|--------|-------------|----------|
| CLI --model-path（推荐） | 优：显式、可复现、不写死本机路径，且与 `Llama(model_path=...)` 直接对应。劣：每次重跑要带参数。推荐：用 `--model-path /abs/path` 传入，spike 不自动下载、不改模型缓存。 | ✓ |
| 环境变量传入 | 优：runbook 可无参重跑。劣：隐藏输入，复现时须记录 env；容易和 Settings 混淆。可作辅助，不推荐作为唯一入口。 | |
| 脚本内固定绝对路径 | 优：改动最少。劣：换机即失效、证据不可移植，会把本机路径写进 artifact。不推荐。 | |

**User's choice:** CLI --model-path（推荐）
**Notes:** LFM3 GGUF 仍按 `PROJECT.md` 锁定为「用户自行下载的可选实验臂」。

### A2. 什么算「成功加载并生成一次」？

| Option | Description | Selected |
|--------|-------------|----------|
| 直接 Llama + 生成（推荐） | 优：与 ROADMAP 字面一致；`embedder.py:437` 有 `create_completion` 可参照。劣：需确认 chat template / 固定短 prompt。推荐：不带 `embedding=True`，greedy/temperature 0 产出一次非空文本并落盘。 | ✓ |
| 复用 LlamaCppEmbedder | 优：最省代码、复用 `Llama(..., embedding=True)`。劣：这是 embedding 路径，不能证明生成；与 spike 目标错配。不推荐。 | |
| 仅 import / 读元数据 | 优：最快最安全。劣：无法证明 `lfm3` 架构可推理，不满足成功标准 1。不推荐。 | |

**User's choice:** 直接 Llama + 生成（推荐）
**Notes:** `LlamaCppEmbedder` 的 `embedding=True` 路径明确不能当生成证明。

### A3. 锁定的 0.3.35 不兼容时，退路如何做到「可复核」？

| Option | Description | Selected |
|--------|-------------|----------|
| 隔离 venv 试升级（推荐） | 优：直接回答锁定版能否升级；可记录对 `LlamaCppEmbedder` / GGUF rerank 路径的影响，且不动主环境。劣：需额外安装一次。推荐：只在临时 venv 试，`pyproject.toml` / `uv.lock` 哈希保持不变。 | ✓ |
| 外部 llama-server 冒烟 | 优：绕开 Python 绑定版本，能验证 GGUF / 架构本身。劣：引入第二个二进制与端口，不等于 SIF 依赖路径；需写明不等价关系。适合补充，不单独作为结论。 | |
| 只记录不兼容并止损 | 优：最省成本、最贴合止损。劣：成功标准 1 还要求「升级或外部 llama-server 退路及其影响被记录为可复核结论」，只写失败不够。不推荐作为唯一动作。 | |

**User's choice:** 隔离 venv 试升级（推荐）
**Notes:** 外部 `llama-server` 只作补充证据；只记录失败不满足成功标准 1。

### A4. 兼容性证据至少落盘哪些字段？

| Option | Description | Selected |
|--------|-------------|----------|
| 完整可复核字段（推荐） | 优：任何人可按同一命令重跑，并把「对现有 GGUF embed/rerank 路径的影响」写成明确结论。劣：artifact 稍长。推荐：`llama_cpp` 版本、GGUF SHA256、完整命令、chat template、一次生成输出、错误栈、embed/rerank 回归判定。 | ✓ |
| 仅 pass/fail + 错误摘要 | 优：简洁。劣：无法复核，也不满足「可复核结论」。不推荐。 | |
| 详细日志只放 tmp | 优：主仓干净。劣：证据会随 `.planning/tmp/` 清理丢失；适合放原始日志，不适合作为唯一交付。可叠加，不单独选。 | |

**User's choice:** 完整可复核字段（推荐）
**Notes:** 原始日志可另放 `.planning/tmp/`，但不作为唯一交付。

**Area close-out:** 用户选择「进入下一区」；A 区未追加追问，细节留入 Claude's Discretion。

---

## B. 信号判定口径

### B1. 固定/规则锚点如何生成，才能不泄漏 relevance 标签？

| Option | Description | Selected |
|--------|-------------|----------|
| query-only 规则（推荐） | 优：不读 relevance / gold 文档，杜绝标签泄漏；完全确定性，固定种子重跑一致。劣：锚点偏保守，信号可能弱。推荐：从 query 本身派生缩写/同义/组合词，配一张提交的手工映射表；不调用 LLM、不读 gold。 | ✓ |
| 从 gold 文档抽词 | 优：最容易做出正 delta，能快速看到机制上限。劣：直接泄漏 relevance，spike 结论不可信，会误导 Phase 26/27。不推荐。 | |
| 纯手工 query→anchor 表 | 优：透明、可 review。劣：手工量随 query 数增长；若制表时参考了 gold 仍可能泄漏。适合作为 query-only 规则的子集，不单独选。 | |

**User's choice:** query-only 规则（推荐）
**Notes:** 从 gold 文档抽词会泄漏标签并污染 Phase 26/27，明确不采用；纯手工表只作为 query-only 规则的子集。

### B2. 用哪部分现有 fixture 判定方向性信号？

| Option | Description | Selected |
|--------|-------------|----------|
| 只用 tuning split（推荐） | 优：保留 heldout 给 Phase 27，避免拿门禁数据做 go/no-go；与 `heldout_defaults.json` 纪律一致。劣：样本数更小，信号可能更弱。推荐：spike 只读 tuning，artifact 记录 heldout 未被读取。 | ✓ |
| 整个 committed fixture | 优：样本更多、delta 表更完整。劣：把 Phase 27 的 heldout 提前用于是否继续的决策，构成 peeking。不推荐。 | |
| 另造合成 fixture | 优：与 Phase 27 完全隔离。劣：新增 fixture 维护成本，且 ROADMAP 明示「现有 fixture」。不推荐。 | |

**User's choice:** 只用 tuning split（推荐）
**Notes:** `tests/fixtures/bench/queries.json` 是唯一查询来源；heldout 留给 Phase 27。

### B3. 配对 delta 表的主指标怎么定？

| Option | Description | Selected |
|--------|-------------|----------|
| nDCG@10 主（推荐） | 优：与 `src/sif/search/benchmark.py` 的 `SearchEvaluator` / `ndcg_at_k` 一致，配对 nDCG@10 对排序敏感；`hit_at_k` / `recall_at_k` 已存在，可加两列诊断。劣：Recall@10 的 `total_relevant` 口径需核对。推荐：主判定用 paired nDCG@10 delta。 | ✓ |
| Recall@10 主 | 优：对齐 Phase 27 新增 Recall@10，直接看是否多捞回相关文档。劣：spike 阶段改主指标会与既有 bench 输出不一致，且 `recall_at_k` 依赖 `total_relevant`。不推荐作主指标。 | |
| Hit@10 主 | 优：最直观、最简单。劣：只看 top-10 是否命中，粒度粗，容易掩盖排序变化。不推荐。 | |

**User's choice:** nDCG@10 主（推荐）
**Notes:** Hit@10 / Recall@10 作为附加诊断列；`total_relevant` 口径由 planner 核对。

### B4. 「有方向性信号」的阈值与复现条件怎么定？

| Option | Description | Selected |
|--------|-------------|----------|
| 均值>0 且 helped>hurt（推荐） | 优：这才是 spike 的「方向性」，不把 Phase 27 的 adopt 门禁提前；helped/hurt/unchanged 计数可防少数离群值冒充信号。劣：仍可能受噪声影响，artifact 需写 N 与 1/N。推荐：固定种子 + 同一 fixture + 同一锚点表，重跑得到相同 delta 表即通过。 | ✓ |
| ≥0.01 且 CI 排除 0 | 优：最严格，可直接复用 `warrants_default_change` / 10,000 bootstrap。劣：这是 Phase 27 的升默认门禁，spike 用它会把「是否继续研究」误变成「是否升默认」，容易误杀。不推荐用于 Phase 25。 | |
| 任何正 delta 即算有 | 优：最宽松、最不容易止损。劣：噪声也能放行，违背可证伪目标。不推荐。 | |

**User's choice:** 均值>0 且 helped>hurt（推荐）
**Notes:** 记录 helped/hurt/unchanged 与 N / 1/N；固定种子重跑一致即通过。

**Area close-out:** 用户选择「进入下一区」；B 区未追加追问，锚点映射表具体词条等留入 Claude's Discretion。

---

## C. 契约冻结基线

### C1. 契约冻结以哪个不可变基线为准？

| Option | Description | Selected |
|--------|-------------|----------|
| v1.2.5 tag（推荐） | 优：已发布、不可变，避免把后续 docs 提交混进契约；5 goldens / `test_packaging.py` / `protocol.py` / `tools.py` / `pyproject.toml` / `uv.lock` 在 `v1.2.5..HEAD` 均无变化。劣：需在 artifact 同时记录当前 HEAD `7c2fb79`。推荐：冻结锚点写 `v1.2.5 (6c25e88d9913)`。 | ✓ |
| 当前 HEAD | 优：直接对应此刻工作树，哈希已现算。劣：HEAD 会随 docs/planning 提交移动，不是稳定发布基线。不推荐作主锚点，可作辅助记录。 | |
| plan 执行前重取 | 优：永远对齐最新代码。劣：若期间有人合法改了契约文件，冻结会被悄悄重定义，失去逐字节未变的意义。不推荐。 | |

**User's choice:** v1.2.5 tag（推荐）
**Notes:** 已核实 `v1.2.5..HEAD` 只有 docs 提交，契约文件零改动；artifact 同时记录 HEAD `7c2fb7918a45`。

### C2. 「逐字节未变 / 可核对」用哪种机制？

| Option | Description | Selected |
|--------|-------------|----------|
| SHA-256 清单 + 现有测试（推荐） | 优：不新增 `src` 代码；`test_wire_transcripts.py` 与 `test_packaging.py` 已能证明 goldens / 13 依赖，清单让逐字节可复核。劣：清单需随合法变更重算。推荐：清单放 phase 目录，plan 开始与结束各跑一次 shasum + 两个现有测试。 | ✓ |
| 新增 pytest 守卫 | 优：CI 可自动拒绝漂移。劣：新增测试代码会模糊「写任何新代码前」的边界，且 Phase 25 是 spike 不是功能交付。不推荐在 Phase 25 做，留 Phase 26 若确需。 | |
| 只在文档写哈希 | 优：最轻。劣：不能机器核对，成功标准 3 要求「契约冻结状态可被核对」。不推荐。 | |

**User's choice:** SHA-256 清单 + 现有测试（推荐）
**Notes:** 新增 pytest 守卫明确延后到 Phase 26 若确需。

### C3. 冻结清单覆盖哪些文件？

| Option | Description | Selected |
|--------|-------------|----------|
| 契约面 + 依赖面（推荐） | 优：同时覆盖成功标准 3 的四件事：5 份 goldens、`test_packaging.py`、7 工具 / `QueryInput`、13 项依赖与 `llama-cpp 0.3.35`。劣：清单稍长。推荐：goldens/*.json、`test_wire_transcripts.py`、`test_packaging.py`、`protocol.py`、`tools.py`、`pyproject.toml`、`uv.lock`。 | ✓ |
| 最小 ROADMAP 字面集 | 优：最短，只锁 5 goldens + `test_packaging.py`。劣：无法核对 7 工具、`QueryInput` 不新增字段、零新增 runtime 依赖。不推荐。 | |
| 整个 MCP 目录 | 优：最全，任何 MCP 改动都会触发。劣：把与冻结契约无关的实现/测试也锁死，后续合法重构会被误判。不推荐。 | |

**User's choice:** 契约面 + 依赖面（推荐）
**Notes:** 完整 SHA-256 清单已写入 `25-CONTEXT.md` 的 `<specifics>`。

### C4. 如何证明 spike 执行期间契约没有漂移？

| Option | Description | Selected |
|--------|-------------|----------|
| 首尾双次核对（推荐） | 优：能证明整个 Phase 25 执行前后逐字节一致，且不需要改 CI。劣：runbook 要跑两次 shasum。推荐：开始/结束两次哈希输出都进 artifact，任一不一致即判失败。 | ✓ |
| 加 CI 步骤 | 优：以后每个 PR 自动防漂移。劣：改 workflow 属新增工程面，当前 8-cell CI 已绿，Phase 25 不应扩 CI 范围。不推荐。 | |
| 只在开始记一次 | 优：最省事。劣：无法证明 spike 之后仍逐字节未变，不满足成功标准 3。不推荐。 | |

**User's choice:** 首尾双次核对（推荐）
**Notes:** 不加 CI 步骤，也不只记一次。

**Area close-out:** 用户选择「进入下一区」；C 区未追加追问，清单 schema / 精确命令留入 Claude's Discretion。

---

## D. 产物与止损归档

### D1. 一次性 spike 脚本 / scratch DB 放在哪里？

| Option | Description | Selected |
|--------|-------------|----------|
| tmp 脚本 + 提交 artifact（推荐） | 优：`.gitignore:48` 已忽略 `.planning/tmp/`；一次性脚本与 scratch DB 不进仓，符合「写任何新代码前」「不留半成品代码」，可复现命令写进 runbook。劣：脚本本身不版本化。推荐：`.planning/tmp/phase-25/` 跑，只提交 phase 目录里的证据。 | ✓ |
| scripts/ 提交脚本 | 优：脚本可版本化、重跑方便。劣：新增仓库脚本仍可能被视为半成品代码，Phase 26 还要清理。不推荐。 | |
| 全临时不落盘 | 优：工作树最干净。劣：无法复现，违背可复核结论。不推荐。 | |

**User's choice:** tmp 脚本 + 提交 artifact（推荐）
**Notes:** 可复现命令写进 runbook；脚本本身不版本化。

### D2. 证据 artifact 用什么形态？

| Option | Description | Selected |
|--------|-------------|----------|
| MD + CSV + JSON（推荐） | 优：人读结论、配对 delta 表、机读 verdict 三者齐备；沿用 23/24 的 phase-dir `bench/*.json` 惯例。劣：三份文件需保持一致。推荐：`25-CONTRACT-FREEZE.md` + `bench/spike-delta.csv` + `bench/spike-verdict.json`，JSON 为权威、三者同源生成。 | ✓ |
| 单个 JSON | 优：机读唯一来源，最简。劣：delta 表与止损叙述不便于人读 review。不推荐单独用。 | |
| 单个 Markdown 表 | 优：最易读。劣：无法机器核对阈值、哈希与 verdict。不推荐单独用。 | |

**User's choice:** MD + CSV + JSON（推荐）
**Notes:** JSON 为权威；三者同源生成。

### D3. 判定「无方向性信号」时，止损怎么记录？

| Option | Description | Selected |
|--------|-------------|----------|
| verdict + STATE 注记（推荐） | 优：把「归档假设、Phase 26/27 未启动、工作树清洁」写成可核对记录，并让 `/gsd-progress` 看得到；STATE 通过 `gsd_run` 更新，不直接编辑。劣：多一份 verdict 文档。推荐：`25-SPIKE-VERDICT.md` + `bench/spike-verdict.json` + `state.record-session`，ROADMAP 阶段不勾选。 | ✓ |
| 只更新 ROADMAP/STATE | 优：文档最少。劣：缺少证据链，成功标准 4 要求止损被记录为「归档假设」。不推荐。 | |
| 只留 JSON artifact | 优：最轻。劣：人读/审计弱，「归档假设」叙述缺失。不推荐。 | |

**User's choice:** verdict + STATE 注记（推荐）
**Notes:** ROADMAP 阶段不勾选；STATE 不直接编辑。

### D4. 「工作树不留半成品代码」如何核对？

| Option | Description | Selected |
|--------|-------------|----------|
| 白名单 + 零代码改动（推荐） | 优：承认 `.planning/.continue-here.md`、`.planning/HANDOFF.json`、`.planning/v1.3-ui-anchor-milestone-research.md` 是研究/交接稿，不把 docs 误判为半成品代码；仍要求 `src/`、`tests/`、`pyproject.toml`、`uv.lock` 零改动。劣：白名单要写清，避免被滥用。推荐：artifact 贴 `git status --porcelain` 并逐条解释，任何代码/依赖改动即失败。 | ✓ |
| 严格 zero untracked | 优：最干净、最容易断言。劣：需先提交或删除 3 个已存在的 planning 文档，超出 Phase 25 范围且可能丢研究稿。不推荐。 | |
| 不记录工作树状态 | 优：最省。劣：成功标准 4 无法核对。不推荐。 | |

**User's choice:** 白名单 + 零代码改动（推荐）
**Notes:** 任何代码/依赖改动即失败；3 个未跟踪 planning 文档逐条解释。

**Area close-out:** 用户选择「结束四区讨论」；D 区未追加追问，artifact schema / runbook 命令留入 Claude's Discretion。

---

## Final Confirmation

| Option | Description | Selected |
|--------|-------------|----------|
| 写 CONTEXT.md（推荐） | 优：16 项决策已锁定，researcher / planner 可据此直接工作，无需再问用户。劣：进入写作后若想改决策，需手动编辑 CONTEXT.md 或重跑讨论。推荐：选这个。 | ✓ |
| 再探索更多灰区 | 优：可继续挖 GGUF 下载校验、隔离 venv 版本、artifact JSON schema 等 2-4 个新灰区。劣：多数属于 planner / executor 可执行细节，会拉长讨论并稀释已锁决策。不推荐，除非有明确未覆盖的边界。 | |

**User's choice:** 写 CONTEXT.md（推荐）
**Notes:** 四区全部完成，用户未要求追加灰区。

---

## Claude's Discretion

用户 16 题全部选择推荐项，未使用 "you decide" 选项；以下为推荐项内未展开、留给 researcher / planner 的执行细节：

- `--model-path` 精确拼写、固定短 prompt、chat template 处理、生成输出长度上限。
- 隔离 venv 的目标 `llama-cpp-python` 版本、路径、升级失败记录格式。
- query-only 锚点映射表格式、具体词条、派生规则、固定种子数值。
- `N` / `1/N` / `helped/hurt/unchanged` 字段命名与精度。
- SHA-256 清单文件名与 schema、`shasum` 与两个现有测试的确切命令、首尾两次输出排版。
- `25-CONTRACT-FREEZE.md` / `25-SPIKE-VERDICT.md` / `bench/spike-delta.csv` / `bench/spike-verdict.json` 的字段顺序与同源生成方式。
- 3 个未跟踪 planning 文档白名单的呈现格式；`git status --porcelain` 快照保存方式。
- runbook 命令编排与临时脚本命名；不进入 `src/sif`、`tests/`、`pyproject.toml`、`uv.lock`。

## Deferred Ideas

- 新增 pytest 契约守卫或 CI 防漂移步骤：Phase 25 不新增工程面；Phase 26 若确需再单列。
- 外部 `llama-server` 作为正式退路结论：本阶段只作补充证据；正式支持属于新后端能力。
- 把一次性 spike 脚本提交到 `scripts/`、或要求严格 zero untracked：均超出 Phase 25。
- 明确否决、非延期功能的备选项：gold-derived anchors、整个 committed fixture、0.01 + CI 门禁、任何正 delta 即算有、仅 pass/fail、全临时不落盘、只更新 ROADMAP/STATE、不记录工作树状态。
- 无新增能力请求（new capability requests）；讨论保持在 Phase 25 范围内。
