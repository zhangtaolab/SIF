---
phase: 26-anchor-arm-deterministic-cache
plan: 02
subsystem: search
tags: [anchor, generator, gguf, llm-cache, deterministic-cache, fail-open, settings, docs]

# Dependency graph
requires:
  - phase: 26-anchor-arm-deterministic-cache
    provides: "26-01 的 AnchorResolution(terms/backend)、AnchorResolver 结构契约、SearchOptions.anchor_terms 注入点、zero-model 规则锚点"
provides:
  - "AnchorResolver 实现：rules 默认、gguf/openai opt-in、llm_cache 复用与跨进程命中"
  - "冻结 PROMPT_TEMPLATE/PROMPT_VERSION/parse_terms 与 AnchorGenerator 协议"
  - "LocalGGUFGenerator（显式 chat template + stopping-criteria deadline）与 OpenAICompatibleGenerator（stdlib POST + 一次性外发披露）"
  - "fail-open 单次告警、同 query 失败锁存、AnchorBudgetExceeded 硬预算"
  - "10 个 SIF_ANCHOR_* Settings 与 generator-owned Anchor Settings 文档段"
affects: [26-03, 26-04, 27]

actuals:
  tokens: 15620
  tasks: 3
  commits: 3
  plan_head_before: abaaaaad6897522c5d99597b02015c75d6ed6c16
  plan_head_after: fc9c63e6b1d2b2c8ee44f0caaf0b56e869b6fb77

tech-stack:
  added: []
  patterns:
    - "缓存写入前在 resolve 入口观测 was_in_transaction，只提交 resolver 自己的写事务"
    - "optional 后端 import（llama_cpp/jinja2）全部延迟到生成调用点"
    - "失败按 resolver 实例 + prompt_hash 锁存，reason 只在单次 stderr 与运行级元数据里暴露"
    - "跨进程缓存命中用第二个独立 sqlite3.Connection 断言，而非同连接自证"

key-files:
  created:
    - tests/unit/search/test_anchor_cache.py
    - tests/unit/search/test_anchor_generator.py
    - tests/unit/config/test_settings_anchor.py
  modified:
    - src/sif/search/anchor.py
    - src/sif/config/settings.py
    - scripts/generate_config_ref.py
    - docs/configuration.md

key-decisions:
  - "task 1 先用最小 prompt/解析器建立缓存闭环，task 2 升级为冻结模板与完整 GEN-01 解析器（同一 PROMPT_VERSION=anchor.v1）"
  - "缓存键 = sha256(PROMPT_VERSION\\x00model_id\\x00backend\\x00normalized_query)；namespace = anchor::<backend>::<model_id>"
  - "后端不可用回退规则锚点（backend='rules' + fallback_reason），生成失败回退空锚点（terms=[] + fallback_reason），两者都只告警一次"
  - "移除 26-01 的 AnchorResolver Protocol，让同名具体类成为唯一公开实现；hybrid 的 TYPE_CHECKING 注解继续解析到该类"

patterns-established:
  - "确定性缓存：LLMCacheRepository 读写在主 DB，成功才写、入口观测事务、跨连接验证"
  - "生成器隔离：Protocol + 注入 generator 便于无模型的确定性单测"
  - "配置文档覆盖：SECTIONS 全字段断言，防止新 Settings 被静默丢弃"

requirements-completed: [GEN-01, GEN-02, GEN-03, GEN-04, CTR-04]

coverage:
  - id: D1
    description: "同一 query 第二次解析 0 次生成、1 次缓存命中；第二个 resolver 与第二个独立 sqlite3.Connection 同样命中"
    requirement: GEN-02
    verification:
      - kind: unit
        ref: "tests/unit/search/test_anchor_cache.py#test_same_resolver_second_resolve_hits_cache"
        status: pass
      - kind: unit
        ref: "tests/unit/search/test_anchor_cache.py#test_second_independent_connection_hits_the_committed_row"
        status: pass
    human_judgment: false
  - id: D2
    description: "45 配置 × 3 query 只产生 3 次生成调用，其余为缓存命中"
    requirement: GEN-02
    verification:
      - kind: unit
        ref: "tests/unit/search/test_anchor_cache.py#test_grid_sweep_generates_once_per_query"
        status: pass
    human_judgment: false
  - id: D3
    description: "冻结 prompt 与 GEN-01 解析器：编号/项目符号剥离、大小写归一、去重、≤10、>64 字符/6 词/纯标点丢弃、CJK 保留"
    requirement: GEN-01
    verification:
      - kind: unit
        ref: "tests/unit/search/test_anchor_generator.py#test_parse_terms_strips_numbering_and_bullets"
        status: pass
      - kind: unit
        ref: "tests/unit/search/test_anchor_generator.py#test_parse_terms_drops_overlong_overworded_and_punctuation"
        status: pass
    human_judgment: false
  - id: D4
    description: "本地 GGUF：embedding=False、显式 chat template、greedy 参数、token deadline 以 reason='timeout' 浮出"
    requirement: GEN-01
    verification:
      - kind: unit
        ref: "tests/unit/search/test_anchor_generator.py#test_local_generator_renders_template_with_greedy_params"
        status: pass
      - kind: unit
        ref: "tests/unit/search/test_anchor_generator.py#test_local_generator_deadline_raises_timeout"
        status: pass
    human_judgment: false
  - id: D5
    description: "生成失败/超时 fail-open：结果与 lex: 逐行相等、单次 warning、同 query 不重试；预算超限硬失败"
    requirement: GEN-03
    verification:
      - kind: unit
        ref: "tests/unit/search/test_anchor_generator.py#test_fail_open_matches_lex_and_warns_once"
        status: pass
      - kind: unit
        ref: "tests/unit/search/test_anchor_cache.py#test_budget_exceeded_is_a_hard_failure"
        status: pass
    human_judgment: false
  - id: D6
    description: "远程后端显式 opt-in：缺配置回退规则锚点；每个 base_url 只披露一次；默认与 fake 路径零 socket"
    requirement: GEN-04
    verification:
      - kind: unit
        ref: "tests/unit/search/test_anchor_generator.py#test_openai_egress_is_disclosed_once_per_base_url"
        status: pass
      - kind: unit
        ref: "tests/unit/search/test_anchor_generator.py#test_default_and_remote_fake_paths_open_no_socket"
        status: pass
    human_judgment: false
  - id: D7
    description: "10 个 SIF_ANCHOR_* 全部进入生成式配置文档，重生成零 diff，且每个 Settings 字段都有 SECTION"
    requirement: CTR-04
    verification:
      - kind: automated_ui
        ref: "make docs-generate && git diff --exit-code docs/configuration.md"
        status: pass
      - kind: unit
        ref: "tests/unit/config/test_settings_anchor.py#test_every_settings_field_is_in_a_documented_section"
        status: pass
    human_judgment: false

duration: 11min
completed: 2026-11-28
status: complete
---

# Phase 26 Plan 02: Anchor Arm + Deterministic Cache Summary

**可选锚点生成器与可跨进程命中的确定性缓存：冻结 prompt、本地 GGUF/远程 opt-in 生成器、单次 fail-open、硬预算与 10 个 SIF_ANCHOR_* 配置全部落地**

## Performance

- **Duration:** 11 min
- **Started:** 2026-11-28T05:12:33Z
- **Completed:** 2026-11-28T05:23:22Z
- **Tasks:** 3
- **Files modified:** 7（4 个源/文档 + 3 个新测试）

## Accomplishments

- `AnchorResolver` 在真实 SQLite 上完成「miss → 一次生成 → 写缓存 → 命中 → 第二个 resolver 命中 → 第二个独立连接命中」闭环：45 配置 × 3 query 严格只生成 3 次。
- 缓存提交语义钉死：在 `resolve` 入口观测 `was_in_transaction`，只提交 resolver 自己的写事务；调用方已开的 transaction 不被越权提交（rollback 后两行一起消失）。
- 冻结 `PROMPT_TEMPLATE` / `PROMPT_VERSION=anchor.v1` 与完整 GEN-01 `parse_terms`；本地 GGUF 用 `Llama(embedding=False)` + `tokenizer.chat_template` 显式渲染 + `StoppingCriteriaList` deadline，greedy 参数固定。
- 远程 OpenAI-compatible 走 stdlib `urllib`，只有显式配置才构造；每个 base_url 一次性 stderr 披露外发；默认与 fake 路径在 `socket.socket` 被替换为抛异常时仍可工作。
- fail-open 只告警一次、同 query 不重试、失败不写缓存；`AnchorBudgetExceeded` 是 `RuntimeError` 子类且不被 fail-open 捕获。
- 10 个 `SIF_ANCHOR_*` 字段进入 `generate_config_ref.SECTIONS`，`make docs-generate` 二次运行零 diff，`docs/cli-reference.md` 未变化。

## Task Commits

Each task was committed atomically:

1. **Task 1: AnchorResolver + 规则/缓存闭环与 SIF_ANCHOR_* Settings 面** — `5ebceed` (feat)
2. **Task 2: 冻结 prompt/解析、本地 GGUF 与远程生成器、fail-open** — `ea53077` (feat)
3. **Task 3: Anchor Settings 文档段、配置文档重生成与 Settings 校验测试** — `fc9c63e` (docs)

**Plan metadata:** (docs commit, this SUMMARY)

## Files Created/Modified

- `src/sif/search/anchor.py` — `PROMPT_VERSION`/`MAX_ANCHOR_TERMS`/`parse_terms`、`AnchorGenerator`、三个异常、`LocalGGUFGenerator`、`OpenAICompatibleGenerator`、`AnchorResolver`、缓存/预算/fail-open
- `src/sif/config/settings.py` — 10 个 `anchor_*` 字段 + 三个 validator
- `scripts/generate_config_ref.py` — `("Anchor Settings", [...])` SECTION
- `docs/configuration.md` — 重生成的 Anchor Settings 段（generator-owned）
- `tests/unit/search/test_anchor_cache.py` — 缓存/跨实例/跨连接/45N/预算/TTL/事务
- `tests/unit/search/test_anchor_generator.py` — 解析、本地/远程生成器、无网络、fail-open
- `tests/unit/config/test_settings_anchor.py` — 默认值/校验/秘密排除/SECTIONS 覆盖

## Decisions Made

- 规则锚点不缓存（纯函数零成本，避免无谓留存查询文本）；生成器后端才读写 `llm_cache`。
- 后端不可用 → 规则锚点 + `fallback_reason`；生成失败 → 空锚点 + `fallback_reason`。前者保留 Phase 25 信号，后者严格等价于原 query。
- 规则回退的 `AnchorResolution.backend` 记为 `"rules"`（真正产出 terms 的组件），原因由 `fallback_reason` 携带。
- 缓存 TTL `0` 映射为 `None`（永不过期），与 `LLMCacheRepository.set` 的既有语义一致。

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] 移除 26-01 的 `AnchorResolver` Protocol，保留同名具体类**
- **Found during:** Task 1
- **Issue:** `anchor.py` 同时存在 `AnchorResolver(Protocol)` 与 `AnchorResolver` 具体类，ruff `F811` 直接失败；计划要求的最终产物是具体类。
- **Fix:** 删除 Protocol；`SearchPipeline` 的 `TYPE_CHECKING` 注解继续解析到具体类（`resolve(query) -> AnchorResolution` 结构不变）。`ty check src/sif` 全绿。
- **Files modified:** `src/sif/search/anchor.py`
- **Verification:** `ruff check src/sif/search/anchor.py`、`ty check src/sif`、全部 anchor/hybrid 测试通过。
- **Committed in:** `5ebceed`

**2. [Rule 2 - Missing Critical] `_ensure_generator` 对非 `str|Path` 的 model path 回退 `unconfigured`**
- **Found during:** Task 2
- **Issue:** `Path(MagicMock)` 会抛 `TypeError`，而项目既有约定是用类型白名单防止 Mock settings 泄漏进真实路径（research Pitfall 6 同类）。
- **Fix:** `anchor_model_path` 仅在 `isinstance(model_path, (str, Path))` 时构造生成器，否则按未配置回退规则锚点；`_setting_str/_setting_int` 同样拒绝非 `str`/非 `int`（含 bool）。
- **Files modified:** `src/sif/search/anchor.py`
- **Verification:** `tests/unit/search/test_anchor_cache.py`（unconfigured 用例）与 `ty`。
- **Committed in:** `ea53077`

---

**Total deviations:** 2 auto-fixed (1 blocking, 1 missing critical)
**Impact on plan:** 均为正确性/可交付性所需；GEN-01..04 / CTR-04 的验收面未变。

## Issues Encountered

- 全量套件需要 `--extra embed`（本机 `.venv` 无 torch）；定向门禁用 `.venv/bin/python -m pytest ... --no-cov` 执行，涉及模块全部通过。

## User Setup Required

None - no external service configuration required. 真实 GGUF 冒烟仍需用户自备 `llama-cpp-python>=0.3.37` 与模型（可选、非本计划门禁）。

## Known Stubs

- `anchor_vocab_guard` 字段已在 Settings 中定义并写入配置文档，但 `AnchorResolver` 尚未消费它：ANC-05 词表守卫 A/B 属于 26-04-PLAN。该字段是有意保留的配置面，不是未接线的运行路径。

## Next Phase Readiness

- 26-03 可直接把 `AnchorResolver` 注入 `query_cmd` / pipeline，并从 `pipeline.last_anchor_resolution` 读取 `generator_calls` / `cache_hits` / `backend` / `fallback_reason` 输出到 `--explain`（不得进入 `SearchResult.to_dict`）。
- `SIF_ANCHOR_VOCAB_GUARD` 已可被 26-04 的守卫实现读取。
- 冻结文件（`pyproject.toml`/`uv.lock`/MCP protocol/tools/goldens/test_packaging）自 plan base 起零改动；MCP wire/packaging 契约 `13 passed`。

## Self-Check: PASSED

- FOUND: src/sif/search/anchor.py
- FOUND: src/sif/config/settings.py
- FOUND: scripts/generate_config_ref.py
- FOUND: docs/configuration.md
- FOUND: tests/unit/search/test_anchor_cache.py
- FOUND: tests/unit/search/test_anchor_generator.py
- FOUND: tests/unit/config/test_settings_anchor.py
- FOUND: 5ebceed
- FOUND: ea53077
- FOUND: fc9c63e
