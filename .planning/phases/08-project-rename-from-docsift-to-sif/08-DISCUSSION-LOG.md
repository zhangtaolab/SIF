# Phase 8: Project rename from DocSift to SIF - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-27
**Phase:** 08-project-rename-from-docsift-to-sif
**Areas discussed:** 数据迁移策略, 向后兼容性, 重命名范围界定, 执行策略

---

## 数据迁移策略

| Option | Description | Selected |
|--------|-------------|----------|
| 自动迁移 | 安装/首次运行时自动将旧目录内容移动到新路径 | |
| 路径兼容层 | 新代码优先查找新路径，若不存在则回退到旧路径 | |
| 强制新路径 | 完全不处理旧数据，用户手动复制 | |
| 删除旧数据，新数据重新生成 | 用户自定义选择 | ✓ |

**User's choice:** 数据库重新生成，模型缓存保留
**Notes:** 用户最初选择"删除旧数据，新数据重新生成"。进一步确认后，决定数据库重新生成（用户需重新 `sif index`），但模型缓存目录保留。模型目录在首次运行 CLI 时自动从 `~/.local/share/docsift` 重命名为 `~/.local/share/sif`。

---

## 向后兼容性

| Option | Description | Selected |
|--------|-------------|----------|
| 保留别名 | pyproject.toml 同时注册 `docsift` 和 `sif` | |
| 不保留别名 | 完全切换到 `sif` | ✓ |
| 兼容警告模式 | 保留别名但打印 deprecation warning | |

**User's choice:** 不保留别名（完全断裂）
**Notes:** 用户明确选择完全断裂策略。CLI 命令 `docsift` 不再可用，环境变量 `DOCSIFT_*` 不再识别。用户在迁移文档中学习新命令和新配置方式。

---

## 重命名范围界定

| Option | Description | Selected |
|--------|-------------|----------|
| 同步重命名所有内容 | 包括 Claude Skill、代码注释、测试文件名全部替换 | ✓ |
| 仅重命名功能性内容 | 不修改代码注释、不改 Claude Skill、不改测试文件名 | |
| 自定义范围 | 其他想法 | |

**User's choice:** 同步重命名所有内容
**Notes:** 用户确认所有内容都需要同步修改：源码包、CLI、环境变量、配置路径、文档、pyproject.toml、GitHub 仓库 URL、PyPI 包名、Claude Skill、代码注释、测试文件。

---

## 执行策略

| Option | Description | Selected |
|--------|-------------|----------|
| 脚本批量替换 | 自动扫描所有文件，批量替换引用 | |
| 分步手动替换 | 按模块逐步替换，每步运行测试验证 | ✓ |
| 工具辅助 | 使用 rope、griffe 等专业重构工具 | |

**User's choice:** 分步手动替换
**Notes:** 用户确认 9 步执行顺序：1) 重命名目录 2) 更新 pyproject.toml 3) 更新 import 4) 更新常量 5) 更新环境变量前缀 6) 更新测试 7) 更新文档 8) 更新 Skill 9) 完整测试验证。

---

## Claude's Discretion

- 迁移提示的具体文案和输出方式
- 是否添加 `--no-migrate` 等跳过迁移的 flag
- 迁移脚本的具体实现位置

## Deferred Ideas

- PyPI 包的 deprecated 发布策略（如需发布 `docsift` 的 deprecated 版本）— 部署阶段处理
- 旧版本文档归档和重定向 — 部署阶段处理
