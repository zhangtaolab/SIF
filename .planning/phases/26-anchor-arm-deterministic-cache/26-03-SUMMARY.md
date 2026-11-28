---
phase: 26-anchor-arm-deterministic-cache
plan: 03
subsystem: cli
tags: [anchor, cli, click-flag, route-first, explain, docs-generate]

# Dependency graph
requires:
  - phase: 26-anchor-arm-deterministic-cache
    provides: "26-01 的共享 PREFIX_ROUTES、SearchType.ANCHOR 路由、last_anchor_resolution；26-02 的 AnchorResolver 与 AnchorResolution 运行级元数据"
provides:
  - "`sif search query --anchor` Click flag：与 `anchor:` 前缀等价、单路由、只注入一次"
  - "route-first 的 ANCHOR CLI 路径：无 rerank 时零 EmbeddingManager、零模型加载、零 reranker"
  - "`--anchor` 与 `--rerank` / SIF_RERANK_ENABLED 组合的显式拒绝（构造前 click.UsageError）"
  - "`--explain` 的 anchor backend/calls/hits/fallback stderr 行，stdout 与 to_dict 不变"
  - "make docs-generate 重生成的 docs/cli-reference.md（含 --anchor，二次运行零 diff）"
affects: [26-04, 27]

actuals:
  tokens: 6322
  tasks: 2
  commits: 2
  plan_head_before: 8f6575d69876c4a344b2798f78b2352d3c008d1f
  plan_head_after: 7b9ff686970bbd4a971bd84b5320f98318a34664

tech-stack:
  added: []
  patterns:
    - "路由先于构造：flag/前缀解析成单一 pipeline_query，ANCHOR 无 rerank 时跳过 EmbeddingManager"
    - "成本元数据只走 stderr 的 --explain 行；机器可读 stdout 与 SearchResult.to_dict 保持逐字节不变"
    - "原始 query 与带前缀 pipeline_query 分离：DYM/history 用前者，pipeline 用后者"

key-files:
  created:
    - tests/unit/cli/test_anchor_flag.py
  modified:
    - src/sif/cli/commands/search.py
    - docs/cli-reference.md
    - tests/unit/cli/test_search.py

key-decisions:
  - "--anchor 只在 query 命令上新增；search/vsearch 保持纯基线，其余入口靠 anchor: 前缀（D-02/D-03）"
  - "flag 与前缀的注入只作用于交给 pipeline 的 pipeline_query；DYM/历史/输出继续用原始 query"
  - "ANCHOR + rerank 组合在任何 create_reranker/EmbeddingManager 构造之前以 click.UsageError 拒绝，绝不静默丢弃 rerank"
  - "AnchorResolver 仅在 anchor_route 分支惰性导入并构造；非 anchor 路由传 None"
  - "anchor 运行级元数据仅在 anchor_route 时从 pipeline.last_anchor_resolution 读取，避免 MagicMock 自动属性伪造 anchor 行"

requirements-completed: [ANC-01, GEN-03, CTR-04]

coverage:
  - id: D1
    description: "--anchor 与 anchor: 等价，同时出现只注入一次；无 flag 时 query 原样传入 pipeline"
    requirement: ANC-01
    verification:
      - kind: unit
        ref: "tests/unit/cli/test_anchor_flag.py#TestAnchorFlagRouting"
        status: pass
    human_judgment: false
  - id: D2
    description: "ANCHOR 路由无 rerank 时零 embedder 构造，AnchorResolver 注入，非 anchor 路由传 None"
    requirement: ANC-01
    verification:
      - kind: unit
        ref: "tests/unit/cli/test_anchor_flag.py#test_anchor_route_loads_no_embedder"
        status: pass
      - kind: unit
        ref: "tests/unit/cli/test_anchor_flag.py#test_anchor_resolver_is_injected"
        status: pass
      - kind: unit
        ref: "tests/unit/cli/test_anchor_flag.py#test_non_anchor_route_passes_no_resolver"
        status: pass
    human_judgment: false
  - id: D3
    description: "--anchor 与 --rerank / SIF_RERANK_ENABLED 被显式拒绝且零构造；--rerank 单独使用仍构造 reranker"
    requirement: ANC-01
    verification:
      - kind: unit
        ref: "tests/unit/cli/test_anchor_flag.py#test_anchor_with_rerank_is_rejected_before_construction"
        status: pass
      - kind: unit
        ref: "tests/unit/cli/test_anchor_flag.py#test_rerank_alone_still_constructs_reranker"
        status: pass
    human_judgment: false
  - id: D4
    description: "--explain 在 stderr 输出恰一行 anchor 元数据；--explain --json 的 stdout 合法且无 anchor 键；GEN-03 fallback 可见"
    requirement: GEN-03
    verification:
      - kind: unit
        ref: "tests/unit/cli/test_anchor_flag.py#test_explain_emits_anchor_line_on_stderr_and_keeps_json_pure"
        status: pass
      - kind: unit
        ref: "tests/unit/cli/test_anchor_flag.py#test_explain_without_resolution_emits_no_anchor_line"
        status: pass
      - kind: unit
        ref: "tests/unit/cli/test_anchor_flag.py#test_gen03_fallback_reason_is_visible"
        status: pass
    human_judgment: false
  - id: D5
    description: "DYM 与 query history 收到原始 query，pipeline 收到 anchor:q"
    requirement: ANC-01
    verification:
      - kind: unit
        ref: "tests/unit/cli/test_anchor_flag.py#test_dym_and_history_receive_original_query"
        status: pass
    human_judgment: false
  - id: D6
    description: "docs/cli-reference.md 由 make docs-generate 重生成并含 --anchor；二次运行零 diff；help 可见"
    requirement: CTR-04
    verification:
      - kind: automated_ui
        ref: "make docs-generate && git diff --exit-code docs/cli-reference.md"
        status: pass
      - kind: other
        ref: ".venv/bin/python -m sif.cli.main search query --help | grep -q -- --anchor"
        status: pass
    human_judgment: false

duration: 6min
completed: 2026-11-28
status: complete
---

# Phase 26 Plan 03: Anchor Arm + Deterministic Cache Summary

**`sif search query --anchor` 端到端走 ANCHOR 单腿：flag 与 `anchor:` 等价且只注入一次、无 rerank 时零 embedder 构造、成本元数据只走 `--explain` 的 stderr，CLI 参考由生成器维护并零 diff**

## Performance

- **Duration:** 6 min
- **Started:** 2026-11-28T06:29:09Z
- **Completed:** 2026-11-28T06:35:19Z
- **Tasks:** 2
- **Files modified:** 4（1 源文件 + 1 生成文档 + 2 测试）

## Accomplishments

- `query_cmd` 新增与 `--rerank` 并列的 `--anchor` 布尔 flag。flag 与 `anchor:` 前缀等价，flag 命中已带前缀的 query 时只保留一个前缀；`query`（DYM、历史、JSON/MD/XML 的 query 字段、表格标题）始终是用户原始输入，只有 `pipeline.search()` 收到 `pipeline_query`。
- 路由先于构造：解析出 ANCHOR 路由且未要求 rerank 时，完全不调用 `EmbeddingManager.from_settings`、不 `load_model`、不做 identity 探测、不构造 reranker；`AnchorResolver(db.connection, settings)` 只在此分支构造并注入 `SearchPipeline`，非 anchor 路由传 `None`。
- `--anchor --rerank` 与 `--anchor` + `SIF_RERANK_ENABLED=1` 在任何人模型构造之前以 `click.UsageError` 明确拒绝，避免静默丢弃 rerank 或构造一个 ANCHOR 单腿根本不会用到的 reranker；`--rerank` 单独使用仍按既有路径构造 reranker。
- `--explain` 在 ANCHOR 路由上向 stderr 输出恰一行 `anchor: backend=... calls=... hits=... fallback=...`；该行不进入 `SearchResult`、不进入 JSON/CSV/MD/XML；`--explain --json` 的 stdout 仍是合法 JSON 且无 anchor 键，GEN-03 的失败原因（`fallback=timeout`）由此可见。
- `make docs-generate` 重生成 `docs/cli-reference.md`，新增一行 `--anchor`，二次运行零 diff；`sif search query --help` 与生成文档均含该 flag。
- 全量套件（忽略本机缺 torch 的 `test_reranker.py`）3358 passed / 1 skipped；ruff check、ruff format --check、`ty check src/sif` 全绿；MCP wire/packaging 契约仍 `13 passed`，全部冻结文件零改动。

## Task Commits

Each task was committed atomically:

1. **Task 1: `--anchor` flag 与 route-first 零模型端到端** — `32d1be04` (feat)
2. **Task 2: `--explain` 成本元数据、DYM/历史原始 query 与 CLI 文档** — `7b9ff686` (docs)

**Plan metadata:** (docs commit, this SUMMARY)

## Files Created/Modified

- `src/sif/cli/commands/search.py` — `--anchor` Click flag 与参数；`pipeline_query`/`route`/`anchor_route` 判定；rerank 组合的 `click.UsageError`；route-first 的 ANCHOR/非 ANCHOR 构造分支；`AnchorResolver` 注入；`anchor_resolution` 捕获与 stderr explain 行；search 调用改用 `pipeline_query`，DYM/history 保留 `query`。
- `docs/cli-reference.md` — generator-owned CLI 参考，重生成后新增 `--anchor` 行。
- `tests/unit/cli/test_anchor_flag.py` — 新建：flag 等价/单次注入、零模型路由、resolver 注入、rerank 拒绝、explain stderr/JSON 纯净、GEN-03 可见性、原始 query。
- `tests/unit/cli/test_search.py` — `_query_settings_mock` 追加 10 个 `SIF_ANCHOR_*` 默认值（防 truthy MagicMock）。

## Decisions Made

- `--anchor` 只加在 `query`（D-02）；`search`/`vsearch` 不追加 flag，保持纯基线。
- flag 与前缀是同一路由（D-03）：注入只发生在 `pipeline_query`，输出/DYM/历史继续用原始 `query`。
- ANCHOR 是纯 BM25 单腿且 26-01 在 rerank 步骤前 return，因此 rerank 组合必须显式拒绝而非构造后用不上（D-01）。
- `AnchorResolver` 惰性导入，只用于证明「非 anchor 路由完全不触碰 anchor 模块」的成本边界。
- 运行级元数据只通过 `pipeline.last_anchor_resolution` 读取；非 anchor 路由不读该属性，避免 MagicMock 自动属性伪造 anchor 行。

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] `anchor_resolver` 局部变量用 `Any` 注解而非 `AnchorResolver | None`**
- **Found during:** Task 1（route-first 分支实现）
- **Issue:** 计划示例写 `anchor_resolver: AnchorResolver | None = AnchorResolver(...)`，但 `AnchorResolver` 按计划只在函数内惰性导入；模块顶层导入它会破坏「默认路径不加载 anchor 模块」的惰性边界，且 `ty` 需要解析注解名。
- **Fix:** 在分支前声明 `anchor_resolver: Any = None`，仅在 `anchor_route` 分支内 `from sif.search.anchor import AnchorResolver` 并赋值。运行期类型与注入行为不变。
- **Files modified:** `src/sif/cli/commands/search.py`
- **Verification:** `ty check src/sif` 全绿；`test_anchor_resolver_is_injected` 断言 `isinstance(..., AnchorResolver)`。
- **Committed in:** `32d1be04`

**2. [Rule 3 - Blocking] Task 2 的 `--explain` 实现随 Task 1 的分支重构一并落地**
- **Found during:** Task 1（route-first 重构）
- **Issue:** 计划把 explain 行放在 Task 2，但它与 Task 1 的 `anchor_resolution` 捕获共享同一段 search 后代码；分两次改同一块会制造中间态，且 Task 1 提交时该行尚无可观测行为（无测试触发）。
- **Fix:** 实现随 Task 1 提交；Task 2 专注补 explain/DYM/原始 query 测试与文档重生成。功能边界与验收不变。
- **Files modified:** `src/sif/cli/commands/search.py`（Task 1）、`tests/unit/cli/test_anchor_flag.py` + `docs/cli-reference.md`（Task 2）
- **Verification:** Task 2 的 explain/JSON/原始 query 测试全绿；docs-generate 零 diff。
- **Committed in:** `32d1be04` + `7b9ff686`

---

**Total deviations:** 2 auto-fixed（均为 blocking，无功能/范围扩张）
**Impact on plan:** 仅实现细节与提交归属调整；D-01/D-02/D-03/D-12 的锁定语义未改。

## Issues Encountered

- 本机 `.venv` 无 torch，全量套件按计划 fallback 基线以 `--ignore=tests/unit/inference/test_reranker.py` 运行；结果 3358 passed / 1 skipped。定向门禁与契约对（`test_wire_transcripts.py` + `test_packaging.py`）均全绿。

## User Setup Required

None - no external service configuration required.

## Threat Flags

None — 本计划只改 CLI 与生成文档，未引入新的网络端点、认证路径或 schema 变化。T-26-09（route-first 零构造）与 T-26-10（explain 仅 stderr、to_dict 不加键）由测试覆盖，T-26-SC 由「零新增依赖 + 冻结文件零改动」守住。

## Next Phase Readiness

- 26-04（wave 4）可直接复用 `--anchor` 的路由与 `AnchorResolver` 注入；其 `make docs-generate` 二次运行会在本计划已提交的零 diff 基线上继续成立。
- `--explain` 的 `backend/calls/hits/fallback` 行可作为 Phase 27 评测报告汇总调用数与缓存命中率的 CLI 出口（EVL-04），无需新增字段或命令。
- 冻结契约（`pyproject.toml`/`uv.lock`/MCP protocol/tools/goldens/`test_packaging.py`）自 plan base 起零改动；`SearchResult.to_dict()` 键集不变。

## Self-Check: PASSED

- FOUND: src/sif/cli/commands/search.py
- FOUND: docs/cli-reference.md
- FOUND: tests/unit/cli/test_anchor_flag.py
- FOUND: tests/unit/cli/test_search.py
- FOUND: 32d1be04
- FOUND: 7b9ff686
- FOUND: `--anchor` in `sif search query --help` and `docs/cli-reference.md`

---
*Phase: 26-anchor-arm-deterministic-cache*
*Completed: 2026-11-28*
