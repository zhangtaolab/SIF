# Phase 4: Advanced Search Pipeline - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-16
**Phase:** 4-advanced-search-pipeline
**Areas discussed:** Reranker backend, Query expansion mechanism, Query prefix semantics, Explain output format

---

## Reranker backend

| Option | Description | Selected |
|--------|-------------|----------|
| 仅 GGUF cross-encoder | 通过 llama-cpp-python 加载本地 GGUF 模型，设置项独立 | |
| GGUF + HF cross-encoder 双后端 | 支持两种后端，与 embedding 策略保持一致，设置项独立 | |
| 你决定 | Claude 根据实现复杂度自行选择 | ✓ |

**User's choice:** 你决定
**Notes:** User deferred to Claude. Selected approach: GGUF primary with optional HF cross-encoder fallback, independent Settings fields.

---

## Query expansion mechanism

| Option | Description | Selected |
|--------|-------------|----------|
| 基于本地 embedding 的 PRF | 用已有 embedding 模型做近邻词扩展，无需额外 LLM 依赖 | |
| 可选 LLM + 默认 embedding PRF | 默认 embedding PRF，配置了 LLM 时启用更强重写 | |
| 你决定 | Claude 根据本地优先原则自行选择 | ✓ |

**User's choice:** 你决定
**Notes:** User deferred to Claude. Selected approach: embedding-based pseudo-relevance feedback as default, with optional LLM expansion when configured.

---

## Query prefix semantics

| Option | Description | Selected |
|--------|-------------|----------|
| 互斥模式开关 | 整个查询只能有一种前缀，前缀决定全局搜索策略 | |
| 可组合策略标记 | 前缀作用于子查询，可混合使用 | |
| 你决定 | Claude 根据 CLI 实现复杂度和 qmd 兼容性自行选择 | ✓ |

**User's choice:** 你决定
**Notes:** User deferred to Claude. Selected approach: mutually exclusive mode switches on the entire query string.

---

## Explain output format

| Option | Description | Selected |
|--------|-------------|----------|
| 结构化 JSON/字典 | 每个结果附带 scores 字典，适合程序消费 | |
| 附加表格列 | 在 rich table / CSV 中新增各阶段得分列 | |
| prose 摘要 | 在结果下方输出文字摘要 | |
| 你决定 | Claude 根据输出格式一致性自行选择 | ✓ |

**User's choice:** 你决定
**Notes:** User deferred to Claude. Selected approach: structured `scores` dict per result in JSON, concise explain column/footer in table output.

---

## Claude's Discretion

- Reranker backend
- Query expansion mechanism
- Query prefix semantics
- Explain output format

## Deferred Ideas

None — discussion stayed within phase scope.
