# Phase 16: Bench Expansion + Reranker Tuning - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-11-08
**Phase:** 16-Bench Expansion + Reranker Tuning
**Areas discussed:** 基准集设计, 指标与输出, sweep 形态, reranker 调优

---

## 基准集设计

| 问题 | 选择 | 备选 |
|------|------|------|
| 语料来源 | 合成语料提交仓库（100-300 文档，四分类，CI 可跑） | 真实 KB（不可复现/隐私/CI 不可跑） |
| 标注形态 | 0-3 分级（nDCG 需要分级信号） | 二元标注（nDCG 退化为近似 precision） |
| 分割 | 固定写入 fixture（split: tuning\|heldout；调优只碰 tuning） | 运行时随机分割（审计链路长） |

## 指标与输出

| 问题 | 选择 | 备选 |
|------|------|------|
| 指标集 | nDCG@10 + Hit@10 + p50/p95 | 多 k 矩阵（@20 对微型语料意义有限） |
| 延迟口径 | 预热后每查询计时（冷启动单列） | 含冷启动（p50/p95 失真） |
| 输出 | 表 + JSON，带四分类细分 | 仅全局指标（平均值掩盖分类恶化） |

## sweep 形态

| 问题 | 选择 | 备选 |
|------|------|------|
| 网格 | 固定网格 ~45 配置（rrf_k {20,40,60,80,100} × 权重 {0.5,1,2}²）；查询 embed 每 sweep 只算一遍 | 自定义网格旗标（解析/校验面大） |
| 噪声规则 | <0.01 归入并列组不宣胜者；默认变更须 held-out Δ≥0.01 复验 | 仅标注噪声（人为选最高分风险） |
| 设置/基线 | bench 读当前 SIF_ 设置（修复 IN-02）；sweep 经 SearchOptions 覆盖；输出基线行 delta | 恒用出厂默认（IN-02 不修） |

## reranker 调优

| 问题 | 选择 | 备选 |
|------|------|------|
| 候选上限 | SIF_RERANK_CANDIDATE_LIMIT 默认 20，范围 5-50 | 默认 10（重排只能微调 top-10） |
| 阈值 α | SIF_RERANK_RELATIVE_THRESHOLD 默认 0.5（≥top1×α） | 默认 0（机制闲置） |
| 快路径 | rerank 显式 opt-in；bench 报告 on/off 双态（指标+延迟） | 自动智能跳过（隐式行为变化） |

## Claude's Discretion

- fixture 文件格式与语料布局；每类查询确切条数（总数 ≥50、held-out ≥20）
- 延迟百分位采样细节；sweep 输出列与 JSON 字段名；冷启动报告格式
- IN-05（多词前缀补全）是否顺带处理（可选）

## Deferred Ideas

None — discussion stayed within phase scope.
