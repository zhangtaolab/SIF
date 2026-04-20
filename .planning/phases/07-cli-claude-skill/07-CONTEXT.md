# Phase 7: CLI Claude Skill - Context

**Gathered:** 2026-04-20
**Status:** Ready for planning

<domain>
## Phase Boundary

为 DocSift 的搜索（search/vsearch/query）和获取（get/multi-get）CLI 命令生成 Claude Skill，使得用户可以在 Claude Code 中通过自然语言完成文档搜索和检索。Skill 使用 subprocess 调用 `docsift` CLI（带 `-q --json`），解析 JSON 输出后返回给 LLM。

</domain>

<spec_lock>
## Requirements (locked via SPEC.md)

**6 requirements are locked.** See `07-SPEC.md` for full requirements, boundaries, and acceptance criteria.

Downstream agents MUST read `07-SPEC.md` before planning or implementing. Requirements are not duplicated here.

**In scope (from SPEC.md):**
- `docsift-search` skill：包装 query（默认）、search、vsearch
- `docsift-get` skill：包装 get、multi-get
- Skill 使用 subprocess + `-q --json` 调用 CLI
- Skill 解析 JSON 输出并格式化返回
- Skill 的错误处理和用户指导
- Skill 文件遵循 `SKILL.md` YAML frontmatter 格式

**Out of scope (from SPEC.md):**
- 其他 CLI 命令（collection、context、index、mcp、pull、bench、status、cleanup）
- Skill 不实现缓存或状态管理
- Skill 不替代 CLI 本身
- 不生成 MCP 工具

</spec_lock>

<decisions>
## Implementation Decisions

### 结果展示格式
- **D-01:** Skill 返回原始 JSON 输出，不做额外格式化。LLM 自行解析 JSON 并决定如何呈现给用户。
  - Rationale: LLM 更擅长处理结构化 JSON，不需要 skill 做 Markdown 转换

### 智能默认值
- **D-02:** Skill 自动设置智能默认参数，但 LLM 可以通过 skill 参数覆盖。
  - 默认参数：
    - `--limit 10`（搜索结果数量）
    - `--line-numbers`（显示行号）
    - `-q`（安静模式，始终启用）
    - `--json`（JSON 输出，始终启用）
  - LLM 可覆盖：用户可以通过 skill 参数显式指定 `--limit 20`、`--collection notes` 等

### 错误处理
- **D-03:** Skill 返回原始 CLI 错误上下文（stderr + return code），由 LLM 智能处理错误信息。
  - 不封装为固定错误消息，保持灵活性
  - LLM 可以根据错误类型决定如何向用户呈现

### 批量获取行为
- **D-04:** multi-get 返回 JSON 数组格式，每个文档为一个对象（含 `path` 和 `content` 字段）。
  - 便于 LLM 遍历处理多个文档
  - 保持文档顺序

### Skill 文件格式
- **D-05:** 遵循标准 Claude Skill `SKILL.md` 格式：
  - YAML frontmatter（name, description, allowed-tools）
  - `<objective>` 标签
  - `<process>` 标签描述 skill 执行流程
  - 使用 `Bash` 工具执行 CLI 命令

### Claude's Discretion
- Skill 的具体命名（argument-hint 格式）
- Skill process 部分的详细程度（代码 vs 逻辑描述）
- 是否添加示例用法到 skill 描述中

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### CLI 命令定义
- `src/docsift/cli/main.py` — CLI 入口点和全局选项
- `src/docsift/cli/commands/search.py` — search, vsearch, query 命令实现
- `src/docsift/cli/commands/get.py` — get, multi-get 命令实现

### Skill 格式参考
- `~/.claude/skills/gsd-add-phase/SKILL.md` — 标准 skill 格式示例

### 项目文档
- `.planning/phases/07-cli-claude-skill/07-SPEC.md` — 锁定需求

</canonical_refs>

<code_context>
## Existing Code Insights

### CLI 结构
- 顶层命令：`docsift [OPTIONS] COMMAND [ARGS]`
- Search 子命令组：`docsift search [query|search|vsearch]`
- Get 子命令组：`docsift get [get|multi-get]`
- 全局选项：`-i/--index`, `-c/--config`, `-v/--verbose`, `-q/--quiet`

### 关键选项
- `query` 选项：`--limit`, `--collection`, `--all`, `--min-score`, `--full`, `--explain`, `--candidate-limit`, `--intent`, `--line-numbers`, `--json`, `--files`, `--model-type`
- `get` 选项：`--from-line`, `--lines`, `--line-numbers`
- `multi-get`：通过 glob 或逗号分隔路径批量获取

### 可复用模式
- 所有命令支持 `-q --json` 组合
- JSON 输出格式统一（SearchResult 对象的列表）
- 错误通过 stderr 输出 + 非零退出码

</code_context>

<specifics>
## Specific Ideas

- Skill 命名：`docsift-search` 和 `docsift-get`
- Skill 存放位置：`~/.claude/skills/docsift-search/SKILL.md` 和 `~/.claude/skills/docsift-get/SKILL.md`
- Search skill 默认使用 `query`（混合搜索），可通过参数指定 `search` 或 `vsearch`
- Get skill 支持单文档和批量获取

</specifics>

<deferred>
## Deferred Ideas

- 其他 CLI 命令的 skill（collection、context、index 等）—— 未来阶段
- Skill 缓存搜索结果以减少重复查询 —— 超出当前范围
- Skill 支持对话式多轮搜索（如"在上次结果中进一步筛选"）—— 未来增强

</deferred>

---

*Phase: 07-cli-claude-skill*
*Context gathered: 2026-04-20*
