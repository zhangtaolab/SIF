# UI 前端准备工作分析

**项目：** SIF / DocSift（PyPI `docsif`）——本地混合搜索引擎，面向个人知识库
**领域：** 在已发布 v1.2 的成熟代码库上新增浏览器端表现层（CLI + MCP 之外的第三个入口）
**分析日期：** 2026-11-24
**基线提交：** `42ba4088`（v1.2.3 之后，工作树干净）
**结论可信度：** 高 —— 文中所有代码位置、测试设施与依赖状态均在本仓库 HEAD 直接核对，非推测

---

## 1. 结论摘要

SIF 的**读路径已经基本可以复用，写路径完全不存在服务化形态**。因此：

- **只读 UI（搜索 / 结果 / 文档查看 / 统计）风险很低**，因为它不需要修改任何现有代码，失败面被 `sif serve` 单个进程完整包住，随时可以不启动、可卸载回退。
- **带写操作的 UI 风险显著更高**，其真实工作量与风险都集中在同一件事上：**把 Click 命令体里的业务逻辑抽取成服务层**。这一步是唯一会"动现有代码"的环节。
- 建议把 UI 拆成两个可独立叫停的交付物：**MVP-A（只读，零重构）** 与 **MVP-B（可写，依赖服务层抽取）**。只读形态本身就是完整产品，不构成半成品。

**一句话风险判断：** 风险不在 UI 代码，而在"动现有代码"。让 UI 先一行不动现有代码地上线只读形态，再用特征测试护住每一次抽取，用独立进程 / 独立端口 / 默认关闭的写开关把失败面限制在 `sif serve` 内部。

---

## 2. 现状盘点

### 2.1 已有资产（可直接复用）

| 资产 | 位置 | 对 UI 的价值 |
|---|---|---|
| 异步服务门面 `SearchBackend` | `src/sif/mcp/backend.py` | `hybrid_search` / `lex_search` / `vec_search` / `get_document` / `get_documents_by_pattern` / `get_status` / `metadata` 全部 async；已用 `asyncio.to_thread` 把同步 SQLite 移出事件循环 |
| 线格式 Pydantic 模型 | `src/sif/mcp/protocol.py` | 输入/输出模型已按 wire 形状设计，含 `snippet` / `line_start` / `content_hash` / `vectors_stale` 等引用级字段 |
| FastAPI + uvicorn | `pyproject.toml` 核心依赖 | HTTP 层无需新增框架依赖 |
| Host 校验与 CORS 模板 | `src/sif/mcp/app.py` | `build_transport_security` / `_host_is_allowed` / `_make_health_host_guard`；`_merge_allowlist` 保证字面量 `*` 永不被接受；`DEFAULT_CORS_ORIGINS` 已预留 `localhost:3000`（前端 dev server 形态） |
| 并发与完整性 | `src/sif/database/factory.py`、`src/sif/database/locking.py` | WAL + `busy_timeout=5000` + `BEGIN IMMEDIATE` + `synchronous=NORMAL` 的统一连接配方；`fcntl.flock` 单写者仲裁，跨进程串行化索引写 |
| 进程与服务化基建 | `src/sif/utils/daemon.py`、`src/sif/utils/service.py` | double-fork `--detach`、PID 文件与身份核对、launchd/systemd unit 生成 |
| 进度事件协议 | `src/sif/indexing/incremental.py`（`progress: Callable[[str], None]`）、`src/sif/indexing/watcher.py`（`queue.Queue` worker） | 现成的"事件字符串 → 渲染"协议，换成轮询/SSE 消费者即可 |
| 内嵌 watcher | `src/sif/mcp/watch_host.py`（`SIF_MCP_WATCH`） | UI 进程内保持索引常新的现成实现，BM25-only 深度 |
| 查询历史仓库 | `src/sif/database/repositories.py:757` `QueryLogRepository` | 有 `history()` 聚合与写时裁剪，可直接供给"最近搜索"面板 |
| MCP 契约快照设施 | `tests/unit/mcp/test_wire_transcripts.py` + `tests/unit/mcp/goldens/*.json` | `SIF_UPDATE_WIRE_GOLDENS=1` 可重跑重写；同一模式可原样复制到 REST 的 OpenAPI 快照 |
| 覆盖率门禁 | `pyproject.toml` `fail_under = 90`（仅覆盖 `src/sif`） | 新增 Python 代码自动纳入门禁；前端不在此范围（需单独定阈值） |

### 2.2 缺口

1. **没有任何 REST API。** `src/` 中唯一的路由是 `src/sif/mcp/app.py:252` 的 `/health`。HTTP 端口目前只讲 MCP 的 JSON-RPC over Streamable HTTP，浏览器前端不应也不会说这个协议。
2. **所有写操作都埋在 Click 命令体里。** `collection add/remove/rename/enable/disable/include/exclude/update-cmd`、`index update`、`index embed`（`src/sif/cli/commands/index.py:266`，已标 `C901/PLR0912/PLR0913/PLR0915`）、`vacuum`、`backup`、`context add/remove/prune` 全是"参数解析 + 业务逻辑 + rich 渲染"混合体。MCP 一侧是**刻意只读**的（`src/sif/mcp/tools.py` 的 D-07：全部 `read_only_hint=True`），所以服务层根本不存在写能力。
3. **没有长任务编排。** 索引/嵌入是分钟到小时级操作，当前是同步执行 + 控制台进度。UI 需要 job id、进度、取消、并发去重。现存的 `FileWatcher` 内部队列是唯一雏形，不是通用任务层。
4. **前端工程化完全空白。** 仓库内无任何 `.ts/.js/package.json`；`.github/workflows/` 无 Node 环节；`Makefile` 无前端目标。
5. **静态资源打包路径未验证。** `[tool.hatch.build.targets.wheel] packages = ["src/sif"]` 意味着把产物放进 `src/sif/web/static/` 会被自动打进 wheel，但 sdist/wheel 中静态资源的完整性没有任何测试断言。

---

## 3. 关键事实（影响方案设计，均已核对）

1. **`SearchBackend` 每次调用开新连接** —— `_run_in_db` 用 `DatabaseConnection(...).transaction()` 包裹回调（`src/sif/mcp/backend.py`）。因此**不需要引入连接池**，UI 多并发在数据库层是安全的。
2. **MCP 路径从不写 `query_log`、也不做搜索前刷新** —— `src/sif/mcp/backend.py:549` 明确注释 MCP queries never write query_log（D-08）；结果只携带 `vectors_stale` 标记。而 **CLI** 搜索前会执行 `_pre_search_refresh`（`src/sif/cli/commands/search.py:236`，会写库做增量刷新）并在 `_record_query_history`（同文件 `:346`）记录历史。**结论：复用 `SearchBackend` 的只读 UI 在数据层是真只读，但会看到比 CLI 更陈旧的内容。**
3. **embedder 失败是静默降级** —— `_ensure_embedder` 失败时 latch `_load_failed`、只打一次 warning，随后 hybrid 查询降级为 BM25。对 agent 是正确设计，但在 UI 上"语义搜索悄悄失效"会被当成 bug，**必须在界面上显式暴露**。
4. **打开 UI 就可能触发 schema 初始化/迁移** —— `SearchBackend` 首次构造时执行 `init_schema(...)`。行为与 `sif mcp http` 及任意 CLI 命令一致，但 UI 让这件事更容易被"好奇点一下"触发，且不可逆。
5. **MCP app 的根挂载会吞掉后续路由** —— `src/sif/mcp/app.py` 中 `app.mount("/", sdk_app)` 之后注册的路由不可达（文件头注释已警告）。任何与 MCP 合并部署的方案都必须先处理这条。

---

## 4. 必须先定的 4 个决策

这四项决定后续 80% 的结构，应在动代码前拍板。

| 决策 | 选项 | 建议 | 理由 |
|---|---|---|---|
| **UI 宿主形态** | (a) 嵌入 wheel 的界面 + `sif serve`；(b) 独立仓库/独立部署；(c) 服务端渲染 + htmx，零 JS 工具链 | **(a)**，具体技术形态见下条 | SIF 卖点是"全本地、零外部 API、单机 pip 安装"；独立部署破坏该定位 |
| **前端技术栈** | (a) SPA + Node 构建链；(b) htmx/SSR（`src/sif/api/templates/`） | **(b)** 作为首选；(a) 若坚持，则必须同时接受"产物进 git + CI drift 校验 + wheel 内容断言"三项成本 | (b) 省掉整条构建链与第二套测试体系，`pytest + httpx + fastapi.testclient` 直接覆盖 UI，`fail_under=90` 自动生效 |
| **API 复用谁** | 直接 import `sif.mcp.backend` vs 提升为 `sif/services/` | **v1 直接 import**（零风险），后续搬家做成纯模块移动 + 别名再导出 | 避免为分层而重构；`from sif.services.search import SearchBackend` 在 `mcp/backend.py` 中再导出即可，所有现有 import 点不动 |
| **读写信任边界** | 只读 vs 可写 | **分两期**：MVP-A 只读；MVP-B 写能力用 `--allow-write` 显式开启，且写操作仅限已注册 collection 根目录之内 | 见第 6.2 节第 4 条：靠缩小能力消除风险，而不是靠校验 |

---

## 5. 准备工作分解

### P0 · 特征测试（阻塞项，最高杠杆）

抽取服务层**之前**，为每个待搬迁命令建立基于**真实 SQLite + 真实 fixture 语料**的测试，不 mock 仓库。

> 动机：现有 CLI 测试以 mock 为主（如 `tests/unit/cli/test_ls.py` 全为 `MagicMock`）。服务层抽取时这些测试会绿，但真实行为可能已经漂移——这是当前最大的隐性盲区。

- **断言对象是数据库状态，不是输出字符串。** 跑完 `collection add` / `index update` 后，把 `collections` / `documents` / `document_chunks` 三表 `SELECT * ORDER BY id` 全量 dump 成 JSON，存为 golden。
- 沿用现有重生成习惯：`SIF_UPDATE_SERVICE_GOLDENS=1` 一键重写，diff 只出现在真正变化处（对齐 `SIF_UPDATE_WIRE_GOLDENS` 的既有做法）。
- 搜索结果断言**结构化字段**（`doc_id` / `path` / `line_start` / 排序后的 `score`），不比对渲染文本。
- 增加"双跑等价"测试：同一语料分别走旧命令路径与新服务函数，比较 DB dump 与结果集完全相等。
- **没有这层测试，不开始 P2。**

### P1 · 只读 API + `sif serve` 骨架

- 新增 `src/sif/api/`：`app.py`（`create_app()`）、`routes/`（`status` / `search` / `documents` / `metadata`）、`schemas.py`（对外 wire 模型，**不直接复用 `mcp/protocol.py` 的类**，否则改 MCP 契约会连带破坏 UI）。
- 新增 `sif serve` 命令（`src/sif/cli/commands/serve.py`），参数对齐 `sif mcp http`（`--host/--port/--cors-origins/--allowed-hosts`），复用 `utils/daemon.py` 支持 `--detach`。
- **独立 app、独立端口**（建议 8081），完全不碰 `src/sif/mcp/app.py`；MCP 继续由 `sif mcp http`（8080）提供，行为零变化。
- 进度推进用**轮询**（`GET /api/v1/jobs/{id}`），v1 不引入 SSE：省掉 `sse-starlette` 显式依赖、断线重连与多路复用测试。
- 安全：照抄 `build_transport_security` 与 `_make_health_host_guard`，Host 校验覆盖**每个**路由；不加 cookie、`allow_credentials=False`、CORS 仅列明确 origin。
- 契约冻结：`app.openapi()` dump 为 `tests/unit/api/goldens/openapi.json`，CI 断言逐字节相等；`/api/v1` 前缀固定。
- 运行态可见性：`/api/v1/status` 必须暴露 `embedder: {state: ok|loading|failed, reason}` 与 schema 版本；提供 `/api/v1/warmup` 或首屏显式加载态。

### P2 · 服务层抽取（唯一"动现有代码"的环节）

- 目标结构：`src/sif/services/{collections,contexts,indexing,documents}.py`，返回结构化结果对象，不返回渲染字符串。
- 顺序：**先读后写**；按命令组逐个搬迁（`collections` → `contexts` → `index` → `ls`），每组单独提交、单独可回滚。
- 每组完成后：CLI 命令变薄壳，P0 的特征测试必须**原样通过**。
- 同时把 `SearchBackend` 迁入 `sif/services/search.py`，在 `sif/mcp/backend.py` 保留 `from sif.services.search import SearchBackend` 别名再导出（零行为变化）。

### P3 · 写接口 + 任务层（MVP-B）

- `src/sif/jobs/`：内存 job registry（id / 状态 / 进度 / 结果 / 错误 / 取消标志）+ **单 worker 线程**（照 `FileWatcher` 的 worker 模式，不要用 `asyncio.create_task` 包同步阻塞调用）。
- 接口：`POST /api/v1/index/jobs` → `202 + job_id`；`GET /api/v1/jobs/{id}`；`DELETE` 取消。
- 进程内 job 去重（跨进程由 `index_lock` 兜底）；取消采用协作式标志，保证中途终止后 DB 一致。
- 关停顺序必须遵守既有 D-14 约定：`watcher.stop(flush=True)` → `PRAGMA wal_checkpoint(TRUNCATE)` → `close`。
- 写路由默认**不注册**，`--allow-write` 才挂载。

### P4 · 前端与打包

- 若走 htmx/SSR：模板与静态资源放 `src/sif/api/templates/` 与 `src/sif/web/static/`，无 Node 依赖。
- 若走 SPA：`web/` 目录 + lockfile，产物输出到 `src/sif/web/static/` 并**提交进 git**；CI 增加 `npm ci && npm run build && git diff --exit-code src/sif/web/static` 的 drift 校验；新增测试断言 wheel/sdist 含入口 HTML。
- `Makefile` 增加 `ui-dev` / `ui-build` / `ui-lint`（按栈选择）；`.gitignore` 加 `node_modules/` 但**不忽略**产物目录。
- 前端测试阈值单独定义（`fail_under=90` 不覆盖前端）。

### P5 · 运维与文档

- `Settings` 新增 `ui_host` / `ui_port`（可选 `ui_allow_write`），沿用 `SIF_` 前缀与 `field_validator` 风格；端口避开 MCP 的 8080。
- 复用 `utils/service.py` 支持 `--install-service`（launchd / systemd）。
- `docs/web-ui.md` + `mkdocs.yml` nav；`scripts/generate_cli_ref.py` 与 `scripts/generate_config_ref.py` 需能拾取 `sif serve` 的新参数（二者在文档 CI 中运行）。
- README Roadmap 中 "Web UI" 与 "REST API" 两项从待办移入已实现。
- `httpx` 目前仅是 `uv.lock` 中的传递依赖，`fastapi.testclient` 需要它 —— 显式写入 `[project.optional-dependencies].dev`。

---

## 6. 风险与降风险策略

### 6.1 风险排序（按"改坏概率 × 发现成本"）

| 风险 | 概率 | 现有检测手段 | 处置 |
|---|---|---|---|
| 服务层抽取导致 CLI/MCP 行为漂移 | 高 | **基本没有**（mock 测试测不出） | P0 特征测试成为阻塞项 |
| 新 HTTP 层破坏 MCP 挂载 | 中 | MCP goldens 可覆盖 MCP，不覆盖新 app | 独立 app + 独立端口，零接触 `mcp/app.py` |
| 写接口的文件系统暴露面 | 中 | 无 | 靠缩小能力消除（见第 4 条） |
| 技术栈引入（Node / 构建链 / 新依赖） | 中 | CI 无 | v1 选零新依赖方案 |
| 长任务 / 并发 / 模型生命周期 | 中 | 有 flock / WAL / 锁，但无多客户端场景 | 信号量 + 显式降级状态 + 预热 |
| 交付超范围 | 高 | 无 | 只读 MVP 先行，写能力单独立项 |

### 6.2 七条具体做法

1. **先补特征测试再重构**（P0）。没有等价性证明，不开始 P2。
2. **冻结现有契约成快照。** 保留 5 份 MCP goldens 不动；新增 REST `openapi.json` golden；为 3–5 个关键 CLI 命令补真正的 golden 输出测试（现多为 `in` 断言）。并在 `CLAUDE.md` 立规矩：`src/sif/mcp/tools.py` 的工具名/参数/描述在 UI 工作中不得改动。
3. **时空隔离。** `sif serve` 独立进程、独立端口、独立 app；新增代码只放 `api/`、`services/`、`web/`、`jobs/`；`cli/`、`mcp/` 仅在 P2 完成后变成薄壳。
4. **靠缩小能力消除安全风险。** ① 写操作只能作用于已注册 collection 根目录之内，`POST /collections`（新增根）不在 UI 提供；② HTTP 层不提供"按任意路径读取"，`get` 只接受 doc_id（对齐现有 `docs://{doc_id}` 资源的思路）；③ 写路由默认不注册，`--allow-write` 才开启；④ 无 cookie 会话、无删除接口，`vacuum`/`backup`/`embed` 不进 UI。
5. **技术栈选择即风险控制。** 轮询替代 SSE；htmx/SSR 替代 SPA + Node；新依赖清单越短越好（`fastapi`/`uvicorn` 已是核心依赖，仅需补 `httpx` 到 dev extras）。
6. **并发与模型生命周期加显式约束。** ① embedder / reranker 加 `asyncio.Semaphore(1~2)`（现有只有 `_load_lock` 防重复加载、`_reranker_lock` 串行化，没有吞吐限流）；② 降级状态必须在 `/api/v1/status` 可见；③ 显式预热；④ 关停遵守 D-14 顺序；⑤ `query_log` 写入去抖（同查询 1s 内不重复记录）。
7. **可逆性优先。** 失败面限制在 `sif serve` 进程内：不启动即完全恢复，不影响已装用户的 CLI/MCP；发布用 minor 版本 + 文档标注 experimental，不做破坏性变更。

---

## 7. 只读 MVP 的风险评估

### 7.1 消掉的风险

| 风险项 | 结论 | 原因 |
|---|---|---|
| 服务层抽取导致 CLI 行为漂移 | **归零** | 完全不碰 `src/sif/cli/`；`SearchBackend` 已提供全部只读能力 |
| MCP 契约被改动 | **归零** | 不碰 `tools.py`，不改 `mcp/app.py` 挂载 |
| 写接口的文件系统暴露面 | **归零** | 无 `POST`、无路径参数、无 `collection add` 入口 |
| 索引锁 / 双写者冲突 | **归零** | 只读路径不获取 `index_lock` |
| 破坏用户数据 | **归零** | 无删除、无重索引；MCP 路径从不写 `query_log`（`backend.py:549`） |
| 失败的可逆性 | **极好** | 不启动 `sif serve` 即完全隔离；`pip uninstall` 恢复原状 |

本质原因：只读 MVP 中**没有一行代码是现有路径的替代品**，全是新增的旁路消费者。同时它把"服务层抽取"这件事的紧迫性降为零——只读 UI 本身就是完整产品。

### 7.2 保留与新增的风险

| 风险 | 说明 | 缓解 |
|---|---|---|
| **保密性未因"只读"而降低** | 能返回全部笔记正文的 `GET /api/v1/search` 危害与写接口不同维度：写是"能改坏"，读是"能全拿走"。威胁来自浏览器中的其他页面（DNS rebinding 可绕过 CORS） | Host 校验覆盖所有路由（照抄 `mcp/app.py`）；不加 cookie；CORS 仅明确 origin |
| **资源耗尽** | 无鉴权的回环接口可被任意页面/脚本高频调用；多标签页并发进 torch 互相拖慢，表现为"卡死" | `asyncio.Semaphore(1~2)` + 简单限流（如每 IP 每秒 10 次） |
| **冷启动与常驻内存** | embedder 加载后常驻进程（数百 MB 起）；首查询 1–3 分钟冷加载。CLI 是短进程，此风险仅在服务化形态出现 | `/api/v1/status` 暴露状态；显式预热；前端加载态 |
| **静默降级被当成 bug** | `_ensure_embedder` 失败后静默走 BM25、只打一次 warning | 界面上常驻"当前仅关键词搜索"提示，并给出原因 |
| **数据陈旧** | `SearchBackend` 不做搜索前刷新，只打 `vectors_stale` 标记 | 首选复用内嵌 watcher（`watch_host.py`）；同时展示陈旧提示 |
| **只读启动的写副作用** | `SearchBackend` 构造即 `init_schema`，可能对旧库执行迁移，不可逆 | 启动日志 + `/api/v1/status` 报 schema 版本；必要时要求先跑 CLI |
| 前端打包 / 版本漂移 | 产物与源码不一致、wheel 缺静态资源 | 产物进 git + CI drift 校验 + wheel 内容断言 |
| 契约漂移 | 前端依赖字段被改名，CI 不报，线上白屏 | OpenAPI golden |

**只读 MVP 的残留工作预算：** 约 3–4 天（Host/Origin 校验、OpenAPI golden、status 可见性、并发信号量、陈旧处理、打包断言）。都不是难题，但漏掉任一项都会让"只读所以安全"的假设失效。

**重新定义"只读"：** 只读 = 没有用户发起的变更操作；**不等于**没有数据暴露、**不等于**没有写（watcher 增量刷新、schema 迁移）、**不等于**可以省掉边界防护。

---

## 8. 建议实施顺序

1. 补特征测试（真实 DB + fixture 语料，DB dump golden）→ 全绿。
2. 建 `src/sif/api/` 独立 app + `sif serve` + `/api/v1/{status,search,get}`，只读、轮询式状态。
3. 冻结 OpenAPI golden；跑现有 5 份 MCP goldens 证明零影响 → **发布 MVP-A**。
4. 抽 `sif/services/collections.py`，特征测试原样绿 → CLI 变薄壳。
5. 重复覆盖 `contexts` → `index` → `ls`；每组单独提交、单独可回滚。
6. 全部绿后上 `src/sif/jobs/` + 写路由（`--allow-write` 默认关）→ **MVP-B**。
7. 前端按第 4 节的技术栈决策推进；若走 SPA，此时才引入 Node 与 CI 校验。

---

## 9. 止损条件（Kill criteria）

- **P0 阶段**出现大面积"现有行为本身就不一致"（同一命令两次调用 DB 状态不同）→ 先修一致性，UI 暂停。这说明服务层抽取会撞上未知语义。
- **P2 阶段**任一命令组连续两次无法在不改动测试的情况下抽干净 → 停止抽取，UI 永久停留在只读形态，写能力继续由 CLI 承担。**只读 UI 本身就是完整产品，这不是失败。**
- **性能**上若 embedder 并发限流后 P95 仍 > 5s → 考虑 UI 默认 lex+vec 手动切换，而不是加缓存层。

---

## 10. 未决问题

1. UI 进程是否内置 watcher（默认开/关）？影响"数据陈旧"的处理方式与进程资源占用。
2. `sif serve` 是否与 `sif mcp http` 合并为单进程单端口（需处理 `mcp/app.py` 根挂载语义）？建议留到 MVP-B 之后，用 `Mount("/mcp", ...)` 形式做纯增益改动。
3. 是否需要多用户 / 局域网访问？若需要，Host 白名单与鉴权模型要重新设计，当前建议的"回环 + 显式开关"不再成立。
4. 前端若走 SPA，Node 版本与 lockfile 策略如何纳入 `publish.yml` 之外的最小 CI 面。

---

*本文档为 v1.3 候选里程碑的前期研究材料，尚未进入 GSD phase 规划流程。*
