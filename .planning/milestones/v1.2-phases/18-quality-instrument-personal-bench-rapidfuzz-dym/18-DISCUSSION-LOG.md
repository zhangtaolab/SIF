# Phase 18: Quality Instrument (Personal Bench + rapidfuzz DYM) - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-11-14
**Phase:** 18-Quality Instrument (Personal Bench + rapidfuzz DYM)
**Areas discussed:** 个人查询合成, 偏差控制与报告, Eval 命令与数据, Rapidfuzz DYM

---

## 个人查询合成

### `sif eval --personal` 默认合成哪些查询腿？

| Option | Description | Selected |
|--------|-------------|----------|
| 三条腿全开 | 标题/H1 + 正文片段 + query_log replay；replay 单独报告并标注 CLI-only 偏差 | ✓ |
| 标题 + 正文 | 不依赖 query_log；新用户也能用，但不反映真实查询分布 | |
| 仅标题/H1 | 最快、最保守，但覆盖窄 | |
| You decide | Claude 依据语料自动选择 | |

**User's choice:** 三条腿全开
**Notes:** roadmap 明确列出 known-item synthesis + query_log replay，三条腿都要进入报告。

### query_log 没有点击/相关性标签，replay leg 应测什么？

| Option | Description | Selected |
|--------|-------------|----------|
| 稳定性/回归 | 重放历史 query，与基线快照比较 top-k 重叠；不伪造标签 | ✓ |
| 伪标签 top-1 | 把当前 top-1 当作 grade 2；可算 nDCG，但循环自证 | |
| 并入 known-item | 用当前命中文档作为 known-item，再算 nDCG；同样循环 | |
| You decide | Claude 选择评估语义并记录偏差 | |

**User's choice:** 稳定性/回归
**Notes:** 报告必须写 "stability vs baseline"，不能写成 "quality"；CLI-only 偏差（MCP 查询不写 query_log）必须文档化。

### 个人语料的查询数量与采样方式？

| Option | Description | Selected |
|--------|-------------|----------|
| 哈希采样 + 上限 | 按内容 hash 确定性抽样，最少 50、最多 500，随语料规模增长 | ✓ |
| 按规模分档 | <1k 100 条、1k–10k 300 条、>10k 500 条 | |
| 全量文档 | 每文档一条；大语料很慢 | |
| You decide | Claude 决定采样方式，确定性优先 | |

**User's choice:** 哈希采样 + 上限

---

## 偏差控制与报告

### Paraphrase overlap 预算如何执行？

| Option | Description | Selected |
|--------|-------------|----------|
| Jaccard ≤0.60 剔除 | query 与目标标题+开头的 token Jaccard ≤0.60；超预算剔除并报告 | ✓ |
| 共享 token ≤50% | query 中共享 token 不超过 50%；对长 query 偏宽松 | |
| 不剔除，分组报告 | 保留全部样本，把高 overlap 子组单独报告 | |
| You decide | Claude 设定阈值与拒绝规则 | |

**User's choice:** Jaccard ≤0.60 剔除

### tuning/held-out 哈希分割比例？

| Option | Description | Selected |
|--------|-------------|----------|
| 50/50 | 个人语料样本小，50% held-out 给最强门禁，held-out ≥25 | ✓ |
| 70/30 | 更多调优数据，held-out 证据变少 | |
| 80/20 | 接近 Phase 16 合成 fixture 比例；小语料 held-out 可能不足 | |
| You decide | Claude 按 N 动态选择，保证 held-out ≥25 | |

**User's choice:** 50/50

### 配对 delta 与噪声门如何判定？

| Option | Description | Selected |
|--------|-------------|----------|
| Paired bootstrap | 逐 query 配对 delta + bootstrap 95% CI；CI 排除 0 且 Δ≥0.01 才胜出 | ✓ |
| Δ≥0.01 + 2SE | 更简单，小样本下不如 bootstrap 稳健 | |
| 固定 0.014 噪声底 | 只用 roadmap 的 per-query 噪声底，不做区间估计 | |
| You decide | Claude 选择统计方法，必须报告不确定性 | |

**User's choice:** Paired bootstrap
**Notes:** 同时报告 1/N per-query 噪声底与每组 N。

### 报告粒度与最小分组样本？

| Option | Description | Selected |
|--------|-------------|----------|
| 全维度，<10 抑制 | per-leg × per-language × per-category；<10 抑制并列出组名 | ✓ |
| 全维度 + low-N 标记 | 保留所有组，小样本打 low-N 标记 | |
| 精简维度 | 只报告 global + per-leg + per-category | |
| You decide | Claude 决定粒度与最小样本规则 | |

**User's choice:** 全维度，<10 抑制

---

## Eval 命令与数据

### `sif eval --personal` 的命令形态？

| Option | Description | Selected |
|--------|-------------|----------|
| 新 eval 命令组 | 新增 `sif eval`，`--personal` 为个人语料入口；`sif bench` 保留 | ✓ |
| bench --personal | 不新增命令，扩展 `sif bench --personal` | |
| 别名转发 | `sif eval` 转发到 `sif bench --personal` | |
| You decide | Claude 选择命令结构，保留 `sif eval --personal` | |

**User's choice:** 新 eval 命令组

### 个人查询集如何存储？

| Option | Description | Selected |
|--------|-------------|----------|
| 缓存目录自动保存 | query/path/split/leg/grade 写到 `~/.cache/sif/eval/`，无正文，`--no-save` 可关 | ✓ |
| 仅内存 | 不落盘；隐私最好，但无法复现/对比 | |
| 显式 --save | 默认内存，只有 `--save <path>` 才写出 | |
| You decide | Claude 决定，以不泄露正文 + 可复现为原则 | |

**User's choice:** 缓存目录自动保存

### 小语料门槛与 embed 默认行为？

| Option | Description | Selected |
|--------|-------------|----------|
| ≥20 文档 + BM25 默认 | 低于 20 文档/30 query 拒绝；默认 BM25，`--embed` 显式启用 | |
| ≥50 文档 + 混合默认 | 要求 ≥50 文档/50 query；默认混合检索（需要 embed extra） | ✓ |
| 不拒绝，只警告 | 小语料仍输出报告并标注 low-N | |
| You decide | Claude 决定门槛与默认检索模式 | |

**User's choice:** ≥50 文档 + 混合默认
**Notes:** embed extra 缺失时给出 `pip install docsif[embed]` 提示；显式 `--bm25-only` 才降级。

### 运行间对比（paired delta）的 CLI 入口？

| Option | Description | Selected |
|--------|-------------|----------|
| --compare + 自动保存 | `--compare <saved-run.json>` 加载历史运行，配对 delta + bootstrap CI | ✓ |
| 自动对比上次 | 默认对比同一语料 hash 的最近运行；`--no-compare` 关闭 | |
| 只做单次指标 | 本阶段只输出单次运行；后续直接调用 Python API | |
| You decide | Claude 设计对比入口，必须支持配对 delta | |

**User's choice:** --compare + 自动保存

---

## Rapidfuzz DYM

### rapidfuzz 的 scorer 与初始 cutoff？

| Option | Description | Selected |
|--------|-------------|----------|
| fuzz.ratio + 重测 | 归一化 Indel 0–100，全词表无分桶；初值 75，按 bench 重测 | ✓ |
| fuzz.WRatio | 对长词/词序更宽容，但分数语义不如 Indel 直观 | |
| extract + cutoff 70 | 先保召回，再按实测精度调高 | |
| You decide | Claude 选 scorer，必须在 0–100 Indel 尺度实测 | |

**User's choice:** fuzz.ratio + 重测

### 同分候选的确定性排序？

| Option | Description | Selected |
|--------|-------------|----------|
| score→字典序→df | 与现有 difflib sorted-term 确定性一致 | ✓ |
| score→df→字典序 | 更偏向常见词，改变现有排序倾向 | |
| 只按 score | 依赖 rapidfuzz 返回顺序 | |
| You decide | Claude 决定 tie-break，必须可复现 | |

**User's choice:** score→字典序→df

### rapidfuzz 不可用时是否保留 difflib fallback？

| Option | Description | Selected |
|--------|-------------|----------|
| 无 fallback | rapidfuzz 是硬依赖；ImportError 即安装损坏，清晰报错 | ✓ |
| difflib 桶 fallback | 退回现有首字母桶；两份实现需同步维护 | |
| difflib 全词表 | 更慢但不分桶；代码仍有分叉 | |

**User's choice:** 无 fallback

### cutoff 是否暴露给用户？

| Option | Description | Selected |
|--------|-------------|----------|
| 内部常量 | 由 bench 证据钉住并被测试守卫；不新增设置/flag | ✓ |
| SIF_ 设置 | 可调，但增加 generator docs/测试/兼容面 | |
| CLI flag | `sif suggest --dym-cutoff`，低频辅助命令价值低 | |
| You decide | Claude 决定，默认不增加用户可调项 | |

**User's choice:** 内部常量

---

## Claude's Discretion

- Personal-eval category axis: query-length buckets (short/medium/long), orthogonal to leg and language.
- Language classification by CJK codepoint ratio (`en` / `zh` / `mixed`), threshold pinned by tests.
- Saved-run JSON schema/version and corpus-fingerprint algorithm.
- Replay baseline snapshot shape and "no baseline" reporting.
- Hybrid-default embedder selection; `--bm25-only` report flag.
- rapidfuzz call shape (`process.extract` vs `cdist`), early-exit strategy for large vocabularies, measured cutoff within 70–80.
- Exact `sif eval --personal` table/JSON fields.
- Whether `sif eval` also aliases the committed synthetic fixture in this phase.

## Deferred Ideas

None — discussion stayed within phase scope.
