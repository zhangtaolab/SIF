# Requirements: DocSift

**Defined:** 2026-04-14
**Core Value:** 用户可以在自己的笔记和文档库中，用自然语言快速、准确地找到需要的信息——无论关键词是否匹配。

## v1 Requirements

### Foundation (Bugfix & Stub Removal)

- [ ] **FND-01**: 修复 `pyproject.toml` 中缺失的运行时依赖声明（sqlite-vec、structlog、platformdirs、pydantic、fastapi/uvicorn、watchdog、python-frontmatter 等）
- [ ] **FND-02**: 修复索引更新逻辑中的 checksum 比较错误（应跳过未变更文档，而非跳过已变更文档）
- [ ] **FND-03**: 替换 embedding 工厂中的随机/占位实现，实现真正的 sentence-transformers 和 llama-cpp-python 加载路径
- [ ] **FND-04**: 移除硬编码模型路径 `BAAI/bge-small-zh-v1.5`，改为从 Settings 读取并允许 CLI 覆盖
- [ ] **FND-05**: 统一或清理重复的数据库 repository 实现（repositories.py vs sqlite_repository.py）
- [ ] **FND-06**: 修复 FTS5 外部内容表的同步问题，确保 BM25 搜索结果与主表一致
- [ ] **FND-07**: 修复向量搜索 CLI 的 fallback 问题：`vsearch` 不应在未找到 embedder 时无条件回退到 BM25
- [ ] **FND-08**: 改进 SQLite 连接管理，避免异步/多线程场景下的竞态条件

### CLI Completion

- [ ] **CLI-01**: 实现 `multi-get` 命令：支持 glob 模式、逗号分隔列表或 docid 批量获取文档
- [ ] **CLI-02**: 实现 `ls` 命令：列出索引中的虚拟文件树（按集合查看已索引文档）
- [ ] **CLI-03**: 实现 `collection update-cmd`：为集合设置/清除索引前执行的 shell 命令（如 `git pull`）
- [ ] **CLI-04**: 实现 `collection include/exclude`：控制集合是否参与默认查询
- [ ] **CLI-05**: 实现 `pull` 命令：下载/检查本地 GGUF 模型文件
- [ ] **CLI-06**: 支持 `--min-score` 参数过滤低置信度结果
- [ ] **CLI-07**: 支持 `--full` 参数返回完整文档内容而非片段
- [ ] **CLI-08**: 支持 `--line-numbers` 参数在输出中附加行号

### Context & Agent Experience

- [ ] **CTX-01**: 实现 `context add`：为路径或集合添加人工描述文本，提升检索质量
- [ ] **CTX-02**: 实现 `context list` 和 `context rm`：查看和删除已添加的上下文
- [ ] **CTX-03**: 上下文描述应在搜索时被携带回结果中（与 qmd 行为一致）

### Advanced Search Pipeline

- [ ] **SRCH-01**: 实现可配置的 LLM reranker，支持 llama-cpp-python GGUF cross-encoder 模型
- [ ] **SRCH-02**: 实现 LLM query expansion：将用户查询扩展为 lex/vec/hyde 变体
- [ ] **SRCH-03**: 实现 query document 语法：`lex:`、`vec:`、`hyde:`、`expand:` 前缀查询
- [ ] **SRCH-04**: 支持 `--explain` 参数，显示 BM25、RRF、reranker 各阶段得分痕迹
- [ ] **SRCH-05**: 支持 `--candidate-limit` / `-C` 参数，控制进入 reranker 的候选数量
- [ ] **SRCH-06**: 支持 `--intent` 参数，在查询各阶段传递意图提示
- [ ] **SRCH-07**: 实现智能 snippet 提取：基于加权词频从 chunk 中提取最相关片段
- [ ] **SRCH-08**: 实现 `bench` 命令：支持用 fixture JSON 测量 precision@k、recall、MRR

### Vector Search & Embedding Configurability

- [ ] **VEC-01**: 支持通过 Settings 和 CLI 配置不同的 embedding 后端（sentence-transformers / llama-cpp-python / OpenAI-compatible API）
- [ ] **VEC-02**: 将向量搜索 fallback 改为使用 sqlite-vec，或在大索引时拒绝 brute-force Python 计算
- [ ] **VEC-03**: 支持批量 embedding 插入，提升大规模索引性能
- [ ] **VEC-04**: 支持从 ModelScope（https://www.modelscope.cn）下载模型文件，作为国内访问 HuggingFace 的替代渠道

## v2 Requirements

### MCP Server

- **MCP-01**: 统一 legacy `mcp/` 和 `mcp_server/` 为单一 MCP 实现
- **MCP-02**: 实现真实的 MCP tool handlers：`query`、`get`、`multi_get`、`status`
- **MCP-03**: MCP 服务器支持 stdio 和 HTTP 双传输
- **MCP-04**: 为 MCP HTTP 模式添加安全的 CORS 默认值（非 `*`）

### Polish & Extensions

- **POL-01**: 支持 per-collection 的独立 embedding/rerank 模型配置
- **POL-02**: 实现 strong-signal bypass：当 BM25 已有明显高匹配时跳过重排序以优化延迟
- **POL-03**: 实现 docid 检索（`#abc123`）的快捷方式
- **POL-04**: 支持 Windows 平台下 sqlite-vec 的兼容性验证和安装引导

## Out of Scope

| Feature | Reason |
|---------|--------|
| Web UI | 本地 CLI 工具的定位，应由生态内的 TUI 工具补充 |
| 实时协作/同步 | 单用户本地工具，超出范围；用户可用 Git/Dropbox |
| 多用户权限系统 | 个人知识库不需要 RBAC |
| PDF/Word/Excel 解析 | 会爆炸依赖复杂度；先聚焦 Markdown、纯文本、代码文件 |
| 内置编辑器 | 范围蔓延，会变成 Obsidian 竞品；只读检索即可 |
| 自动云备份 | 破坏本地优先信任模型；文档告知 SQLite 文件位置即可 |
| 插件架构 | MCP 已提供足够的可扩展性 |
| 实时文件监听/热重载 | 增加守护进程复杂度和资源占用；显式 `update` 命令即可 |
| 图谱可视化 | 炫技但不属于搜索核心功能 |
| 内置 LLM 聊天/RAG 回答 | 会变成聊天机器人而非搜索引擎；让用户的 agent 来合成 |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| FND-01 | Phase 1 | Pending |
| FND-02 | Phase 1 | Pending |
| FND-03 | Phase 1 | Pending |
| FND-04 | Phase 1 | Pending |
| FND-05 | Phase 1 | Pending |
| FND-06 | Phase 1 | Pending |
| FND-07 | Phase 1 | Pending |
| FND-08 | Phase 1 | Pending |
| CLI-01 | Phase 2 | Pending |
| CLI-02 | Phase 2 | Pending |
| CLI-03 | Phase 2 | Pending |
| CLI-04 | Phase 2 | Pending |
| CLI-05 | Phase 2 | Pending |
| CLI-06 | Phase 2 | Pending |
| CLI-07 | Phase 2 | Pending |
| CLI-08 | Phase 2 | Pending |
| CTX-01 | Phase 3 | Pending |
| CTX-02 | Phase 3 | Pending |
| CTX-03 | Phase 3 | Pending |
| VEC-01 | Phase 4 | Pending |
| VEC-02 | Phase 4 | Pending |
| VEC-03 | Phase 4 | Pending |
| VEC-04 | Phase 4 | Pending |
| SRCH-01 | Phase 5 | Pending |
| SRCH-02 | Phase 5 | Pending |
| SRCH-03 | Phase 5 | Pending |
| SRCH-04 | Phase 5 | Pending |
| SRCH-05 | Phase 5 | Pending |
| SRCH-06 | Phase 5 | Pending |
| SRCH-07 | Phase 5 | Pending |
| SRCH-08 | Phase 5 | Pending |

**Coverage:**
- v1 requirements: 35 total
- Mapped to phases: 35
- Unmapped: 0 ✓

---
*Requirements defined: 2026-04-14*
*Last updated: 2026-04-14 after initial definition*
