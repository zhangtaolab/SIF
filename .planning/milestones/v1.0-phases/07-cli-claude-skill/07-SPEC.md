# Phase 7: CLI Claude Skill — Specification

**Created:** 2026-04-20
**Ambiguity score:** 0.09 (gate: ≤ 0.20)
**Requirements:** 6 locked

## Goal

为 DocSift 项目的 CLI 命令（search、vsearch、query、get、multi-get）生成 Claude Skill，使得用户可以在 Claude Code 中通过自然语言交互完成文档搜索和检索，而无需直接记忆 CLI 参数。

## Background

DocSift 是一个本地混合搜索引擎，通过 CLI 提供文档索引、搜索和检索功能。当前用户需要记忆复杂的 Click CLI 参数才能使用。虽然 Phase 02 和 Phase 04 已经完善了 CLI 命令，但用户仍然需要：
- 记忆 `docsift query` 与 `docsift search` 的区别
- 了解 `--collection`、`-c`、`--limit`、`--line-numbers` 等选项
- 手动组合 `docsift search` 和 `docsift get` 来完成"查找并阅读"的工作流

Claude Skill 可以将这些 CLI 命令包装为自然语言接口。Skill 使用 `-q --json` 调用 CLI，解析 JSON 输出后返回结构化结果。

## Requirements

1. **Search Skill (docsift-search)**：包装 `docsift search` / `docsift vsearch` / `docsift query` 命令
   - Current: 无 skill 存在，用户必须手动运行 CLI 命令
   - Target: Skill `docsift-search` 接受自然语言查询，自动选择最佳搜索策略（query 为默认，可显式指定 search/vsearch），返回结构化搜索结果
   - Acceptance: 运行 `/docsift-search "Python asyncio"` 返回文档路径、片段和分数的 JSON 数组；指定 `--strategy search` 时使用 BM25 搜索

2. **Get Skill (docsift-get)**：包装 `docsift get` / `docsift multi-get` 命令
   - Current: 无 skill 存在，用户必须手动运行 CLI 命令
   - Target: Skill `docsift-get` 接受文档路径或 ID，返回文档完整内容；支持批量获取（逗号分隔或 glob 模式）
   - Acceptance: 运行 `/docsift-get "notes/python.md"` 返回文档内容；运行 `/docsift-get "notes/*.md"` 返回多个文档

3. **Skill 使用 CLI 而非 Python 导入**：所有 skill 通过 subprocess 调用 `docsift` CLI
   - Current: 无 skill 实现方式定义
   - Target: Skill 内部使用 `subprocess.run(["docsift", "-q", "--json", ...])` 调用，不直接导入 Python 模块
   - Acceptance: Skill SKILL.md 中的 process 部分明确使用 subprocess 调用 CLI，`-q` 和 `--json` 参数始终存在

4. **Skill 输出为结构化 JSON**：解析 CLI 的 `--json` 输出并返回
   - Current: CLI 支持 `--json` 输出但无 skill 消费
   - Target: Skill 将 CLI 的 JSON 输出解析为 Python dict/list，然后格式化返回给用户
   - Acceptance: Skill 返回的结果包含 `path`、`score`、`snippet` 字段（search）或 `content` 字段（get）

5. **Skill 提供可操作的错误信息**：当 CLI 失败时，skill 返回指导性的错误
   - Current: CLI 错误信息直接输出到 stderr
   - Target: Skill 捕获 stderr，将其转换为可操作建议（如"索引不存在，请先运行 docsift update"）
   - Acceptance: 当索引不存在时，skill 返回的错误信息包含下一步操作指导，而非原始 stderr 文本

6. **Skill 存放在用户目录**：遵循现有 skill 存储约定
   - Current: 无 skill 存储位置定义
   - Target: Skill 文件存放在 `~/.claude/skills/docsift-search/SKILL.md` 和 `~/.claude/skills/docsift-get/SKILL.md`
   - Acceptance: `ls ~/.claude/skills/docsift-search/SKILL.md` 和 `ls ~/.claude/skills/docsift-get/SKILL.md` 均存在

## Boundaries

**In scope:**
- `docsift-search` skill：包装 query（默认）、search、vsearch
- `docsift-get` skill：包装 get、multi-get
- Skill 使用 subprocess + `-q --json` 调用 CLI
- Skill 解析 JSON 输出并格式化返回
- Skill 的错误处理和用户指导
- Skill 文件遵循 `SKILL.md` YAML frontmatter 格式

**Out of scope:**
- 其他 CLI 命令（collection、context、index、mcp、pull、bench、status、cleanup）—— 用户当前需求聚焦搜索和检索，管理类命令暂不需要 skill
- Skill 不实现缓存或状态管理 —— 每次调用都是无状态的 CLI 调用
- Skill 不替代 CLI 本身 —— 用户仍然可以直接使用 CLI
- 不生成 MCP 工具 —— 这是 Phase 4 已经实现的 MCP server 的工作

## Constraints

- Skill 必须使用 `docsift` CLI 命令，要求 DocSift 已安装且 `docsift` 在 PATH 中
- Skill 依赖 `-q`（quiet）和 `--json` 选项，要求 DocSift 版本 ≥ Phase 7 之前的 commit（已包含 --quiet 支持）
- Skill 返回内容长度受 Claude Code context window 限制，大文档可能需要截断
- Skill 命名使用小写连字符格式：`docsift-search`、`docsift-get`

## Acceptance Criteria

- [ ] `~/.claude/skills/docsift-search/SKILL.md` 存在且格式正确（YAML frontmatter + objective + process）
- [ ] `~/.claude/skills/docsift-get/SKILL.md` 存在且格式正确
- [ ] `/docsift-search "query string"` 返回结构化搜索结果（path, score, snippet）
- [ ] `/docsift-search "query" --strategy search` 使用 BM25 而非混合搜索
- [ ] `/docsift-get "path/to/doc.md"` 返回文档内容
- [ ] `/docsift-get "*.md"` 支持批量获取
- [ ] 索引不存在时的错误信息包含"请先运行 docsift update"的指导
- [ ] Skill 始终使用 `-q --json` 调用 CLI，不直接导入 Python 模块

## Ambiguity Report

| Dimension          | Score | Min  | Status | Notes                              |
|--------------------|-------|------|--------|------------------------------------|
| Goal Clarity       | 0.95  | 0.75 | ✓      | 两个 skill，明确的功能范围         |
| Boundary Clarity   | 0.90  | 0.70 | ✓      | 明确排除 collection/context/index  |
| Constraint Clarity | 0.85  | 0.65 | ✓      | subprocess + -q --json 模式已定    |
| Acceptance Criteria| 0.90  | 0.70 | ✓      | 8 个可验证的 pass/fail 标准        |
| **Ambiguity**      | 0.09  | ≤0.20| ✓      |                                    |

Status: ✓ = met minimum, ⚠ = below minimum (planner treats as assumption)

## Interview Log

| Round | Perspective    | Question summary                              | Decision locked                                    |
|-------|----------------|-----------------------------------------------|----------------------------------------------------|
| 1     | Researcher     | 哪些命令需要 skill？                          | 优先 search 和 get，query/search/vsearch 都覆盖    |
| 1     | Researcher     | 执行方式？                                    | subprocess 调用 CLI，使用 -q --json                |
| 2     | Simplifier     | 搜索子命令范围？                              | query + search + vsearch 三个都支持               |
| 2     | Simplifier     | 获取子命令范围？                              | get + multi-get 都支持                            |
| 2     | Simplifier     | 选项粒度？                                    | 核心选项（query, collection, limit, line-numbers） |
| 3     | Boundary Keeper| 输出如何处理？                                | 解析 JSON 后返回结构化结果                        |
| 3     | Boundary Keeper| 错误如何处理？                                | 返回可操作建议而非原始 stderr                     |
| 3     | Boundary Keeper| 命名和存放？                                  | ~/.claude/skills/docsift-{name}/SKILL.md          |

---

*Phase: 07-cli-claude-skill*
*Spec created: 2026-04-20*
*Next step: /gsd-discuss-phase 7 — implementation decisions (how to build what's specified above)*
