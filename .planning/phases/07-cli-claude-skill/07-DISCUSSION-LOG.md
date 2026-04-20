# Phase 7: CLI Claude Skill - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-20
**Phase:** 07-cli-claude-skill
**Areas discussed:** 结果展示格式, 智能默认值, 错误提示详细度, 批量获取行为

---

## 结果展示格式

| Option | Description | Selected |
|--------|-------------|----------|
| 原始 JSON | 直接返回 CLI 的 JSON 输出，LLM 可自行解析 | ✓ |
| Markdown 表格 | 格式化为 Markdown 表格，包含 path、score、snippet 列 | |
| 结构化摘要 | 返回 Markdown 列表，每个结果包含文件名、分数、相关片段摘要 | |

**User's choice:** 原始 JSON
**Notes:** LLM 更擅长处理结构化 JSON，不需要 skill 做 Markdown 转换

---

## 智能默认值

| Option | Description | Selected |
|--------|-------------|----------|
| 自动设置智能默认值 | Skill 自动添加 --limit 10、--line-numbers 等，用户只需提供查询词 | ✓ |
| 只启用 -q --json | Skill 只自动添加安静模式和 JSON 输出，其他参数由用户显式指定 | |
| 完全暴露所有选项 | Skill 允许用户控制每个参数，不做任何默认假设 | |

**User's choice:** 自动设置智能默认值
**Notes:** 用户备注："可以有默认参数，如果有需求可以修改参数，LLM的需求优先"。即 skill 有智能默认，但 LLM 可通过参数覆盖。

---

## 错误提示详细度

| Option | Description | Selected |
|--------|-------------|----------|
| 简洁错误 | 只说明问题和下一步操作 | |
| 详细错误 | 包含具体修复命令示例和上下文 | |
| 可操作建议 | 简洁错误 + 自动建议下一步操作 | |
| LLM智能处理 | 返回原始错误上下文，由 LLM 决定如何呈现 | ✓ |

**User's choice:** LLM智能处理
**Notes:** 用户备注："LLM智能处理"。Skill 返回原始错误上下文，由 LLM 自行决定如何向用户呈现。

---

## 批量获取行为

| Option | Description | Selected |
|--------|-------------|----------|
| JSON 数组 | 返回 JSON 数组，每个元素包含 path 和 content | |
| 合并对象 | 返回一个 JSON 对象，键为文档路径，值为内容 | |
| 逐个返回 | Skill 多次调用 CLI，每次返回一个文档 | |
| 根据LLM建议 | 选择最方便 LLM 使用的格式 | ✓ |

**User's choice:** 根据LLM建议进行
**Notes:** 用户备注："根据LLM的建议进行，方便LLM使用"。推断为 JSON 数组格式（每个文档一个对象），便于 LLM 遍历处理。

---

## Claude's Discretion

- Skill 的具体命名（argument-hint 格式）
- Skill process 部分的详细程度
- 是否添加示例用法到 skill 描述中

## Deferred Ideas

- 其他 CLI 命令的 skill（collection、context、index 等）
- Skill 缓存搜索结果
- 对话式多轮搜索
