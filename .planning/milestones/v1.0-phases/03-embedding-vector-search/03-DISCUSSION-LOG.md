# Phase 3: Embedding & Vector Search - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-16
**Phase:** 03-embedding-vector-search
**Areas discussed:** Backend configuration, OpenAI-compatible API scope, ModelScope integration, Vector table dimension handling

---

## Backend Configuration

| Option | Description | Selected |
|--------|-------------|----------|
| A. 显式配置 | 增加 model_type 字段，用户必须显式指定 | ✓ |
| B. 自动推断 | 根据模型路径/名称自动判断后端 | |
| C. 两者结合 | 默认 auto 自动推断，特殊场景可显式覆盖 | |

**User's choice:** 配置文件+显式配置 (Option A)
**Notes:** 支持通过配置文件、环境变量 `DOCSIFT_MODEL_TYPE` 和 CLI `--model-type` 指定后端。默认值要与 `model_name` 对齐（`sentence_transformers`）。

---

## OpenAI-Compatible API Scope

| Option | Description | Selected |
|--------|-------------|----------|
| A. 仅官方 OpenAI API | 只支持 api.openai.com | |
| B. 通用 OpenAI 兼容端点 | 支持自定义 base_url + api_key + model_name | ✓ |
| C. 暂不实现 | 放到后续阶段 | |

**User's choice:** B. 通用 OpenAI 兼容端点
**Notes:** 支持接入本地 vLLM、Ollama、OneAPI 等任意兼容服务。

### 维度处理子问题

| Option | Description | Selected |
|--------|-------------|----------|
| A. 用户显式配置 embedding_dim | 默认值保持 384，用户自行修改 | |
| B. 首次调用时自动探测 | 首次加载时通过 API 获取维度并缓存 | ✓ |
| C. 用标准维度兜底 | 已知模型自动填维度，未知模型要求用户配置 | |

**User's choice:** B. 首次调用时自动探测
**Notes:** 自动探测维度并缓存，避免每次重启都请求。

---

## ModelScope Integration

| Option | Description | Selected |
|--------|-------------|----------|
| A. 作为完整后端类型 | 增加 model_type = "modelscope"，下载加载一体化 | ✓ |
| B. 仅作为 ST 的下载源 | 不新增 model_type，通过参数识别 | |
| C. 扩展 pull 命令即可 | pull 下载 ST 模型，加载仍走正常 ST 路径 | |

**User's choice:** A. 作为完整后端类型
**Notes:** ModelScope 作为完整后端类型，下载和加载一体化处理。

---

## Vector Table Dimension Handling

| Option | Description | Selected |
|--------|-------------|----------|
| A. 动态维度 + 启动时校验 | 根据 Settings 创建表，不匹配时报错提示手动重建 | ✓ |
| B. 动态维度 + 自动重建 | 检测到不匹配时自动删表重建（丢失向量） | |
| C. 固定维度 + 模型适配 | 保持 768 维，所有模型补齐/截断到 768 | |

**User's choice:** A. 动态维度 + 启动时校验
**Notes:** `SchemaManager` 根据 `Settings.embedding_dim` 创建向量表；维度不匹配时启动报错，提示用户手动重建索引（而非自动删数据）。

---

## Claude's Discretion

None captured.

## Deferred Ideas

None — discussion stayed within phase scope.
