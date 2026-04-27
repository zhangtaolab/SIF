# Phase 8: Project rename from DocSift to SIF - Context

**Gathered:** 2026-04-27
**Status:** Ready for planning

<domain>
## Phase Boundary

将 Python 项目从 `DocSift/docsift` 全面重命名为 `SIF/sif`（含义：Search / Index / Find），涵盖包名、CLI 命令、环境变量、配置路径、文档、测试、Claude Skill 等所有引用。重命名后项目完全以 `sif` 品牌运行，与 `docsift` 完全断裂。

本次重命名范围（全部同步修改）：
- Python 包目录：`src/docsift/` → `src/sif/`
- Python import：`from docsift...` → `from sif...`
- CLI 命令：`docsift` → `sif`
- 环境变量：`DOCSIFT_*` → `SIF_*`
- 配置文件/数据路径：`~/.local/share/docsift/` → `~/.local/share/sif/`
- PyPI 包名：`docsift` → `sif`
- GitHub 仓库 URL：`github.com/zhangtaolab/docsift` → `github.com/zhangtaolab/sif`
- 所有文档（README.md、CLAUDE.md、docs/ 等）
- Claude Skill 文件（`docsift-search`/`docsift-get` → `sif-search`/`sif-get`）
- 代码注释中的 `docsift` 引用
- 测试文件名和测试内容中的引用

</domain>

<decisions>
## Implementation Decisions

### 数据迁移策略
- **D-01:** 数据库文件 `docsift.db` 使用新路径重新生成，用户需重新运行 `sif index` 重建索引
- **D-02:** 模型缓存目录 `~/.local/share/docsift/models/` 在首次运行 CLI 时自动重命名为 `~/.local/share/sif/models/`
  - 代码在 CLI 启动时检测旧路径是否存在、新路径是否不存在，若满足则执行 `old_dir.rename(new_dir)`
  - 重命名后打印提示：`Migrated: ~/.local/share/docsift -> ~/.local/share/sif`
  - 用户无需重新下载模型文件

### 向后兼容性
- **D-03:** 完全断裂策略 — 不保留 `docsift` CLI 别名，不保留 `DOCSIFT_*` 环境变量兼容
- **D-04:** `docsift` 命令不再可用，用户需改用 `sif`
- **D-05:** `DOCSIFT_DB_PATH`、`DOCSIFT_MODEL_NAME` 等环境变量不再识别，改用 `SIF_DB_PATH`、`SIF_MODEL_NAME`
- **D-06:** 迁移文档中需明确说明所有断裂项，提供完整迁移指南

### 重命名范围界定
- **D-07:** 所有内容同步修改，无例外
  - GitHub 仓库名改为 `sif`
  - PyPI 包名改为 `sif`
  - Claude Skill 改为 `sif-search`、`sif-get`
  - 代码注释全部替换
  - 测试文件全部替换

### 执行策略
- **D-08:** 分步手动替换，按以下 9 步顺序执行，每步验证：
  1. 重命名目录 `src/docsift/` → `src/sif/`
  2. 更新 `pyproject.toml`（name, scripts, packages, ruff, mypy, pytest）
  3. 更新所有 Python import（`from docsift...` → `from sif...`）— 验证 pytest collection
  4. 更新 `src/sif/config/constants.py` 中的 `APP_NAME`、`DEFAULT_DB_PATH`、`DEFAULT_MODEL_PATH`、`DEFAULT_CONFIG_PATH`
  5. 更新 `src/sif/config/settings.py` 中的 `env_prefix="DOCSIFT_"` → `"SIF_"`
  6. 更新测试文件中的引用和导入
  7. 更新文档（README.md、CLAUDE.md、docs/、mkdocs.yml 等）
  8. 更新 Claude Skill 文件（.claude/skills/ 下的内容）
  9. 运行完整测试套件验证

### Claude's Discretion
- 迁移提示的具体文案和输出方式（print vs logger）
- 是否添加 `--no-migrate` 等跳过迁移的 flag
- 迁移脚本的具体实现位置（constants.py、settings.py 还是 cli/main.py）
</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### 项目配置
- `pyproject.toml` — 项目元数据、scripts、ruff/mypy/pytest 配置
- `src/docsift/config/settings.py` — Pydantic Settings 类，含 `env_prefix="DOCSIFT_"`
- `src/docsift/config/constants.py` — `APP_NAME`、`DEFAULT_DB_PATH` 等常量

### CLI 入口
- `src/docsift/cli/main.py` — CLI group 注册、全局选项
- `src/docsift/cli/__init__.py` — 包导出

### 现有 Claude Skills
- `.claude/skills/docsift-search/SKILL.md` — 搜索 skill（需重命名为 `sif-search`）
- `.claude/skills/docsift-get/SKILL.md` — 获取 skill（需重命名为 `sif-get`）

### 文档
- `README.md` — 项目主文档
- `CLAUDE.md` — 项目架构和开发指南
- `docs/` 目录下的所有 markdown 文件
- `mkdocs.yml` — MkDocs 配置

### 测试
- `tests/` 目录下所有测试文件，特别是 `tests/test_docsift_complete.py`
</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `src/docsift/config/constants.py` — 集中管理 APP_NAME 和路径常量，修改此处即可统一变更数据目录
- `src/docsift/config/settings.py` — 环境变量前缀集中定义在 `env_prefix` 字段
- `pyproject.toml` — 集中定义包名、CLI 入口、工具配置

### Established Patterns
- 所有模块使用 `from docsift...` 绝对导入，需要全局替换为 `from sif...`
- ruff 配置中 `known-first-party = ["docsift"]` 需要同步更新
- mypy 配置中 `mypy_path = ["src"]` 和包引用需要更新
- pytest 配置中 `--cov=src/docsift` 需要更新

### Integration Points
- CLI 命令在 `src/docsift/cli/commands/*.py` 中定义，通过 `src/docsift/cli/main.py` 注册
- Settings 类被几乎所有模块导入，是关键变更点
- 数据库路径由 `Settings.get_db_path()` 动态解析，改常量后自动生效
- 模型缓存路径由 `Settings.model_path` 定义，改常量后自动生效
</code_context>

<specifics>
## Specific Ideas

- 首次运行时的迁移检测代码建议放在 `sif.cli.main:main()` 函数开头，在 Click 解析参数前执行
- 迁移提示使用 `rich` 库的 `print` 或 `console.print`，风格与现有 CLI 输出一致
- Skill 重命名后需要更新 skill 文件中的 CLI 命令引用（`docsift search` → `sif search` 等）
- `mkdocs.yml` 中的 `site_name` 和文档链接需要同步更新
- 测试中的 `test_docsift_complete.py` 需重命名为 `test_sif_complete.py`
</specifics>

<deferred>
## Deferred Ideas

- PyPI 包的 deprecated 发布策略（如需发布 `docsift` 的 deprecated 版本提示迁移）— 不在代码重命名范围内
- 旧版本文档归档（如保留 docsift.readthedocs.io 重定向到 sif.readthedocs.io）— 部署阶段处理

### Reviewed Todos (not folded)
- None — no relevant pending todos found.
</deferred>

---

*Phase: 08-project-rename-from-docsift-to-sif*
*Context gathered: 2026-04-27*
*Next step: /gsd-plan-phase 8 — implementation planning*
