# Phase 15: Search Quality Configuration (Hybrid Weights + Query Suggestions) - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-11-08
**Phase:** 15-Search Quality Configuration (Hybrid Weights + Query Suggestions)
**Areas discussed:** 权重机制与作用面, DYM 触发与词源, query_log 设计, suggest 形态与 100ms

---

## 权重机制与作用面

| Option | Description | Selected |
|--------|-------------|----------|
| 加权和 RRF | fused = w_bm25/(k+rank_bm25) + w_vec/(k+rank_vec)；无配置逐字节一致；单源缺失项为 0，min_score 语义稳定 | ✓ |
| 归一化权重 | 先除以 Σw —— 单源缺失时分数整体缩放，与今天不再逐字节一致 | |
| 源分数加权 | 权重乘在检索分数上 —— BM25 与余弦量纲不同，向量独大 | |

**User's choice:** 加权和 RRF

| Option | Description | Selected |
|--------|-------------|----------|
| 仅 query + MCP | hybrid 才有融合语义；search/vsearch 单源不加无效旗标 | ✓ |
| 三命令一致暴露 | 一致性最强但出现「设了无效果」的误导旗标 | |

**User's choice:** 仅 query + MCP

| Option | Description | Selected |
|--------|-------------|----------|
| 此套命名 | --rrf-k(int≥1,60)、--bm25-weight/--vector-weight(float>0,1.0,无上限)；SIF_RRF_K 等；SearchOptions 新字段单一通道；CLI>SIF_>默认；MCP 同名字段 | ✓ |
| 加上限约束 | 权重上限 ≤10 —— 人为束缚 Phase 16 sweep 网格 | |
| 短参数名 | --k/--w-bm25 —— 与 REQUIREMENTS 拼写不一致 | |

**User's choice:** 此套命名

| Option | Description | Selected |
|--------|-------------|----------|
| 设置为默认+参数覆盖 | SIF_ 设置是全局默认（含 MCP 进程），请求字段按查询覆盖；与 CLI 优先级对称 | ✓ |
| MCP 恒用出厂默认 | 设置对 MCP 用户无效，两套表面割裂 | |

**User's choice:** 设置为默认+参数覆盖

## DYM 触发与词源

| Option | Description | Selected |
|--------|-------------|----------|
| 仅零结果 | 三命令 + MCP query 零结果时显示；低结果不触发（噪音+阈值调优面） | ✓ |
| 零结果 + 低结果阈值 | 结果数<N 也显示 —— 覆盖拼对一半场景，但阈值是新调优面 | |

**User's choice:** 仅零结果

| Option | Description | Selected |
|--------|-------------|----------|
| FTS5 vocab 表 | documents_fts_v —— 词条按构造 ≥1 命中；无新表、自动同步、一次 SQL | ✓ |
| 独立 terms 表 | 新表+写入路径+同步维护（Phase 14 否决的同类风险） | |
| 仅历史词 | 冷启动建议为空，违背 QUAL-02 | |

**User's choice:** FTS5 vocab 表

| Option | Description | Selected |
|--------|-------------|----------|
| 逐词替换成完整查询 | quantum machin → quantum machine；全词在表不硬凑 | ✓ |
| 整串匹配 | 多词整串几乎不可能命中，DYM 失效 | |
| 混合历史词 | 建议来源混杂，与 QUAL-02/03 分界不清 | |

**User's choice:** 逐词替换成完整查询

## query_log 设计

| Option | Description | Selected |
|--------|-------------|----------|
| 仅搜索命令 | 三条搜索命令记（串/时间戳/结果数/集合）；get/suggest/MCP 不记 | ✓ |
| 含 MCP 查询 | 助手工具式查询污染个人历史 | |
| 含 suggest 输入 | 半成品词自我强化，噪声大 | |

**User's choice:** 仅搜索命令

| Option | Description | Selected |
|--------|-------------|----------|
| 封顶最近 N 条 | 默认 ~500 可调；写入时删最旧；表永不增长 | ✓ |
| 按时间保留 | 需定期清理机制；表仍可短期膨胀 | |

**User's choice:** 封顶最近 N 条

| Option | Description | Selected |
|--------|-------------|----------|
| 设置开关+ suggest 清除 | SIF_QUERY_HISTORY_ENABLED=0 全局关（不写不读）；`sif suggest --clear-history` 单一入口 | ✓ |
| 再加单次旗标 | --no-log 每次都要考虑，低频枝叶面 | |
| cleanup 清除 | 语义分散，历史清除被埋没 | |

**User's choice:** 设置开关+ suggest 清除

## suggest 形态与 100ms

| Option | Description | Selected |
|--------|-------------|----------|
| 三段式 | 前缀/DYM/历史各自 top-N；JSON 同构三数组；来源透明 | ✓ |
| 单一融合列表 | 需跨源可比分，新调优面，来源不可见 | |

**User's choice:** 三段式

| Option | Description | Selected |
|--------|-------------|----------|
| 表 + JSON | 交互辅助命令两格式够用；多格式纯成本 | ✓ |
| 全套五格式 | 与搜索对齐但建议列表无下游管道消费 | |

**User's choice:** 表 + JSON

| Option | Description | Selected |
|--------|-------------|----------|
| 频度×近度 | count×时间衰减，一条 SQL 聚合；冷启动空段 | ✓ |
| 纯近度 | 最简单但偶然查询压过高频常用词 | |

**User's choice:** 频度×近度

| Option | Description | Selected |
|--------|-------------|----------|
| 实测验证不过度预优化 | SQL 词表扫描+逐词 difflib+历史聚合；核心函数计时+端到端减启动基线；超预算再优化 | ✓ |
| 预建缓存 | 每次调用新进程，进程内缓存无效；预建文件引入同步问题 | |

**User's choice:** 实测验证不过度预优化

## Claude's Discretion

- 各段 top-N 条数与 SIF_QUERY_HISTORY_LIMIT 确切默认值
- 时间衰减函数形状；difflib n/cutoff 参数；超大词表处理
- query_log 表结构细节（列/类型/索引）
- MCP 零结果建议响应字段形状（原则由 D-05 固定）
- --explain 是否增加融合分数分解（非 SC 要求）
- 前缀匹配细节（大小写/最小前缀长）

## Deferred Ideas

None — discussion stayed within phase scope.
