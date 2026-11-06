# Phase 6: Documentation Audit & Refresh - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-18
**Phase:** 06-documentation-audit-refresh
**Areas discussed:** Click 文档提取策略, 代码块分类与验证策略, 文档测试执行环境, 技术文档更新机制

---

## Click 文档提取策略

| Option | Description | Selected |
|--------|-------------|----------|
| Python脚本遍历Click命令树 | 使用 Click get_help()/get_commands() API 遍历所有命令组，生成结构化 Markdown | ✓ |
| 调用 --help 输出解析 | 对每个命令调用 --help，将纯文本输出嵌入 Markdown 代码块 | |
| sphinx-click 等第三方库 | 使用 sphinx-click 或 mkdocs-click 插件生成文档 | |

**User's choice:** Python脚本遍历Click命令树
**Notes:** 脚本放在 scripts/generate_cli_ref.py，使用 Click API 递归遍历嵌套命令组。格式采用混合：命令概览用表格，详细参数用 --help 输出。

---

## 代码块分类与验证策略

| Option | Description | Selected |
|--------|-------------|----------|
| 基于 fence 语言标签 | bash/shell → 执行或验证，json/python → 语法检查，text → 跳过 | ✓ |
| 基于 fence 属性注释 | 使用 <!-- docs-test: execute --> 等注释标记控制验证方式 | |
| 基于代码块内容启发式判断 | 根据 $ 前缀、# 注释等特征自动区分 | |

**User's choice:** 基于 fence 语言标签
**Notes:** 对于会启动长期运行进程的命令（如 mcp start、pip install），维护一个黑名单跳过列表。对于命令输出，选择性验证 JSON/结构化输出的结构（用 schema 验证），不逐行对比。

---

## 文档测试执行环境

| Option | Description | Selected |
|--------|-------------|----------|
| pytest fixture 创建临时数据库 + 最小测试数据 | 用 tmp_path 创建临时 SQLite，插入测试集合和文档 | ✓ |
| 使用现有的测试 fixture 或 conftest.py | 复用项目已有的测试 fixture | |
| 仅验证命令存在性和基本解析 | 不需要真实数据，只验证 --help 返回 0 | |

**User's choice:** pytest fixture 创建临时数据库 + 最小测试数据
**Notes:** 执行方式采用混合：Click CliRunner 为主（速度快），subprocess 为辅（涉及环境变量的命令）。环境变量处理：在干净的临时环境中运行每个命令，只注入测试所需的最小变量（如 DOCSIFT_DB_PATH），不应用代码块中的 export 语句。

---

## 技术文档更新机制

| Option | Description | Selected |
|--------|-------------|----------|
| 在 docs 测试中增加技术文档验证 | 检查文档中提到的文件路径和类名是否真实存在 | ✓ |
| 纯人工审查 + 手动更新 | 开发者人工阅读技术文档，与代码对比，手动修改 | |
| 脚本辅助：生成差异报告 | 从代码提取模块结构、类列表，与文档对比生成报告 | |

**User's choice:** 在 docs 测试中增加技术文档验证：检查文档中提到的文件路径和类名是否真实存在
**Notes:** 架构图处理：保留 README 中的 ASCII 高层概览（手动维护），用脚本生成详细模块图放在 architecture.md 中。技术文档验证使用 AST 解析提取代码的公共 API（类、函数），与文档引用的名称对比。

---

## Claude's Discretion

- Exact blacklist command patterns
- JSON schema definitions for output validation
- Mermaid diagram styling and layout
- pytest fixture data content
- Makefile target name and exact commands
- GitHub Actions workflow trigger conditions

## Deferred Ideas

- None — discussion stayed within phase scope
