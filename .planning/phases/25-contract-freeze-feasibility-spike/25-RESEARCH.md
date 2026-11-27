# Phase 25: Contract Freeze & Feasibility Spike - Research

**Researched:** 2026-11-28
**Domain:** llama.cpp/`lfm3` compatibility proof + deterministic anchor-signal measurement + MCP/package contract freeze (no product code)
**Confidence:** HIGH on the compatibility verdict and the in-repo API surfaces; MEDIUM on the upgrade-wheel recipe and the exact Python exception type (not executed locally).

## Summary

This phase writes **zero product code** — it produces three kinds of reviewable evidence and then either unlocks Phase 26/27 or archives the hypothesis. The central feasibility finding is decisive and changes how the first plan must be written:

**The project-locked `llama-cpp-python==0.3.35` cannot load an `lfm3` GGUF.** LFM3 support landed in **llama.cpp v0.8.0 (tag `8642541`, released 2026-10-28)**. llama-cpp-python 0.3.35 (released 2026-08-17) vendors llama.cpp commit `4df29be4f`/`adb55e514`, which the GitHub compare API reports is **1514 commits behind v0.8.0**. Version 0.3.36 (2026-10-01, `0c1e57098`) is still 648 behind. **0.3.37** (2026-11-15, `a956a852c`) is **427 commits ahead** and therefore the first binding release that can load LFM3; 0.3.38 (2026-11-23, `f5e6915c2`) is the latest. `pyproject.toml`/`uv.lock` still resolve 0.3.35, so the locked-version attempt is expected to fail with llama.cpp's `unknown model architecture: 'lfm3'` (a `std::runtime_error`, which pybind11 surfaces as Python `RuntimeError`). The spike must capture that failure as evidence, then trial **0.3.37 in an isolated venv** (D-03) and record the embed/rerank impact — without touching the lock files.

The second finding is that the delta table is straightforward to build entirely from existing, verified APIs: filter `queries.json` to `split == "tuning"` **before** constructing `SearchEvaluator` (there are exactly 36 tuning queries; N/1/N = 36 / 0.02778), run two `search_fn`s through `evaluate_per_query` — one raw BM25 query (`lex:` arm) and one with query-only anchors prepended (`anchor:` arm) — and pair the per-query `ndcg_at_10` values. `ndcg_at_k`/`hit_at_k`/`recall_at_k` and the tuning-only filtering pattern already exist (`bench.py::_tuning_evaluator`), so nothing metric-related should be hand-rolled.

The third finding is an operational trap that would otherwise fail verification: **running either MCP test file alone fails the 90% coverage gate** (the coverage flags live in `addopts`), even though all tests pass. The contract proof must use `--no-cov` for targeted runs: the two files take **0.6 s** and report **13 passed**. All 11 frozen SHA-256 values were recomputed this session and match the CONTEXT table exactly; `git diff v1.2.5..HEAD -- pyproject.toml uv.lock src/sif/mcp/ tests/unit/mcp/` is **empty**. The CONTEXT's "4 commits since v1.2.5" is stale — it is now **7** — so the artifact must record the measured count, not copy 4.

**Primary recommendation:** Plan a **single Wave-1 spike plan** (compat + signal) followed by **Wave 2 freeze/evidence assembly**, with an explicit **human checkpoint for the GGUF path** (no LFM3 GGUF exists on this machine) and a **final stop/go checkpoint**. Treat "0.3.35 fails to load lfm3" as the *expected, provable* outcome, not a blocker: the deliverable is the documented failure plus the isolated-venv 0.3.37 success and its embed/rerank impact.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Locked upstream — do not re-litigate**

- v1.3 只做 LLM Anchor；Web UI 推迟 v1.4，`Web UI` 与 `chat-with-notes / ask` 的 Out of Scope 条款不反转。
- LFM3-1.7B-GGUF Q4_K_M 是用户自行下载的可选实验臂，不打进 wheel/sdist、不默认启用、不自动下载。
- MCP 7 工具、5 份 wire goldens、`QueryInput` 不变；不新增 MCP `anchor` 请求字段；零新增 runtime 依赖；`test_packaging.py` 冻结的 13 项核心依赖不变。
- 无方向性信号时归档假设、不投 Phase 26/27、工作树不留半成品代码；`keep-default` 是有效交付。
- Phase 18/23/24 的 0.01 tie rule、10,000 次 bootstrap、held-out、N / `1/N` 噪声地板属于 Phase 27 的正式门禁；Phase 25 只判方向性信号，不提前消费这些门禁。
- 本阶段无 UI 决定，因此不触发静态 HTML 多方案对照。

**A. `lfm3` 兼容性与证据（SPK-01）**

- **D-01:** Spike 用显式 `--model-path /abs/path` 接收用户自行下载的 GGUF；不写死本机绝对路径，不自动下载，不改模型缓存，不用环境变量作为唯一入口。
- **D-02:** 「成功加载并生成一次」= 直接构造 `Llama(model_path=...)`（不带 `embedding=True`），用 greedy / temperature 0 的固定短 prompt 产出一次非空文本并落盘。`LlamaCppEmbedder` 的 `Llama(..., embedding=True)` 是 embedding 路径，不能当生成证明；仅 import / 读元数据不算成功。
- **D-03:** 若锁定的 0.3.35 不兼容，只在临时隔离 venv 里试升级 `llama-cpp-python`，并记录升级后对 `LlamaCppEmbedder` / GGUF rerank 路径的影响；`pyproject.toml` 与 `uv.lock` 哈希保持不变。外部 `llama-server` 只作补充证据，不单独作为结论；只记录失败不满足成功标准 1。 — **Reversibility:** reversible — 隔离 venv 可删除，主依赖契约不动。
- **D-04:** 兼容性 artifact 至少记录：`llama_cpp` 版本、GGUF SHA256、完整命令、chat template、一次生成输出、错误栈、embed/rerank 回归判定。原始日志可另放 `.planning/tmp/`，但不作为唯一交付。

**B. 确定性锚点信号判定（SPK-02）**

- **D-05:** 固定/规则锚点只从 query 本身派生（缩写/同义/组合词 + 一张提交的 query-only 映射表），不调用 LLM、不读 gold/relevance、不读 gold 文档标题或路径。从 gold 抽词会泄漏标签并污染 Phase 26/27，明确不采用。 — **Reversibility:** costly — 若改回 gold-derived anchors，已产出的 delta 表失去可证伪性，必须重跑整个 spike 并重写 verdict。
- **D-06:** 只读 `tests/fixtures/bench/queries.json` 的 `tuning` split；`heldout` 留给 Phase 27，artifact 记录 heldout 未被读取。使用整个 committed fixture 会造成 heldout peeking；另造合成 fixture 偏离 ROADMAP 的「现有 fixture」。 — **Reversibility:** costly — 若改用 heldout 做 go/no-go，Phase 27 的 held-out 集合会被提前消费，需要重建独立 heldout 或重新取样。
- **D-07:** 配对 delta 表主指标是 `paired nDCG@10`，复用 `src/sif/search/benchmark.py` 的 `SearchEvaluator` / `ndcg_at_k`；`Hit@10` 与 `Recall@10` 作为附加诊断列，`recall_at_k` 的 `total_relevant` 口径由 planner 核对。不以 Recall@10 或 Hit@10 作主判定。
- **D-08:** 「有方向性信号」= 平均 paired delta > 0 且 helped > hurt，并记录 helped/hurt/unchanged 与 N / `1/N`。固定种子 + 同一 fixture + 同一锚点表重跑得到相同 delta 表即通过。不提前使用 0.01 + bootstrap CI 排除 0 的 Phase 27 升默认门禁，也不接受「任何正 delta 即算有」。 — **Reversibility:** costly — 阈值改动会让已发布的 stop/go verdict 失效，必须重跑并重新归档。

**C. 契约冻结（CTR-01 / CTR-02）**

- **D-09:** 冻结锚点写 `v1.2.5 (6c25e88d9913)`，artifact 同时记录讨论时 HEAD `7c2fb7918a45`。已核实 `v1.2.5..HEAD` 只有 docs 提交，契约文件零改动；当前 HEAD 与 plan 执行前重取都不作主锚点。 — **Reversibility:** one-way — 重新定义已发布 tag 上的契约基线会使所有已核对的 goldens / 依赖哈希失效，必须重跑冻结证明并公告基线变更。
- **D-10:** 用 SHA-256 清单 + 现有 `tests/unit/mcp/test_wire_transcripts.py` / `tests/unit/mcp/test_packaging.py` 证明逐字节未变；不新增 `src/sif` 代码，不在 Phase 25 新增 pytest 守卫，也不只在文档里写哈希。清单放 phase 目录，plan 开始与结束各跑一次 `shasum` + 两个现有测试。
- **D-11:** 冻结清单覆盖：5 份 `tests/unit/mcp/goldens/*.json`、`tests/unit/mcp/test_wire_transcripts.py`、`tests/unit/mcp/test_packaging.py`、`src/sif/mcp/protocol.py`（`QueryInput`）、`src/sif/mcp/tools.py`（7 工具）、`pyproject.toml`、`uv.lock`（13 依赖与 `llama-cpp-python==0.3.35`）。最小字面集无法核对 7 工具 / `QueryInput` / 零新增依赖；整个 MCP 目录会误锁合法重构。
- **D-12:** 首尾双次核对：开始/结束两次哈希输出都进 artifact，任一不一致即判失败；不加 CI 步骤，也不只记一次。

**D. Spike 产物与止损归档（SPK-03）**

- **D-13:** 一次性脚本与 scratch DB 放 `.planning/tmp/phase-25/`（`.gitignore` 已忽略 `.planning/tmp/`），只提交 phase 目录里的证据；可复现命令写进 runbook。不把一次性脚本提交到 `scripts/`，也不全临时不落盘。
- **D-14:** 证据 artifact = `25-CONTRACT-FREEZE.md` + `bench/spike-delta.csv` + `bench/spike-verdict.json`，JSON 为权威、三者同源生成；沿用 23/24 的 phase-dir `bench/*.json` 惯例。不单独使用单个 JSON 或单个 Markdown 表。
- **D-15:** 判定「无方向性信号」时写 `25-SPIKE-VERDICT.md` + `bench/spike-verdict.json`，并通过 `gsd_run state.record-session` 记录「归档假设、Phase 26/27 未启动、工作树清洁」；ROADMAP 阶段不勾选。只更新 ROADMAP/STATE 或只留 JSON 都不采用。 — **Reversibility:** costly — verdict 一旦写入 STATE / ROADMAP 会话记录，改动需要重新走状态更新与审计链。
- **D-16:** 「工作树不留半成品代码」= artifact 贴 `git status --porcelain` 并逐条解释 3 个未跟踪 planning 文档（`.planning/.continue-here.md`、`.planning/HANDOFF.json`、`.planning/v1.3-ui-anchor-milestone-research.md`）是研究/交接稿；`src/`、`tests/`、`pyproject.toml`、`uv.lock` 必须零改动，任何代码/依赖改动即失败。严格 zero untracked 与不记录状态都不采用。

### Claude's Discretion

用户 16 题全部选择推荐项，未另行指定细节。以下执行细节留给 researcher / planner 在锁定决策范围内决定：

- `--model-path` 的精确 flag 拼写、固定短 prompt 文本、chat template 处理、一次生成输出的长度上限。
- 隔离 venv 的目标 `llama-cpp-python` 版本、venv 路径、升级失败时的错误记录格式。
- query-only 锚点映射表的文件格式、具体词条、派生规则、固定种子数值。
- `N` / `1/N` / `helped/hurt/unchanged` 在 CSV / JSON 中的字段命名与精度。
- SHA-256 清单文件名与 schema、`shasum` 与两个现有测试的确切命令、首尾两次输出的排版。
- `25-CONTRACT-FREEZE.md` / `25-SPIKE-VERDICT.md` / `bench/spike-delta.csv` / `bench/spike-verdict.json` 的字段顺序与同源生成方式。
- 3 个未跟踪 planning 文档白名单在 artifact 中的呈现格式；`git status --porcelain` 快照的保存方式。
- runbook 的命令编排与临时脚本命名；只要不进入 `src/sif`、`tests/`、`pyproject.toml`、`uv.lock` 即可。

### Deferred Ideas (OUT OF SCOPE)

- 新增 pytest 契约守卫或 CI 防漂移步骤：Phase 25 明确不新增工程面；若 Phase 26 需要持续防漂移再单列。
- 把外部 `llama-server` 作为正式退路结论：本阶段只作补充证据；正式支持属于新后端能力，单独立项。
- 把一次性 spike 脚本提交到 `scripts/`、或要求严格 zero untracked：前者会留下半成品代码，后者需先处理 3 个已存在的 planning 文档，均超出 Phase 25。
- 使用 gold-derived anchors、整个 committed fixture、0.01 + CI 门禁、任何正 delta 即算有：这些是明确否决的备选项，不是延期功能；完整记录见 `25-DISCUSSION-LOG.md`。
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| SPK-01 | 用锁定的 `llama-cpp-python` 加载 `LFM3-1.7B-Q4_K_M.gguf` 并确认 `lfm3` 可推理；不兼容时记录升级/`llama-server` 退路及对 GGUF embed/rerank 的影响 | Verified: locked 0.3.35 is 1514 commits behind lfm3 support; 0.3.37 is the first binding release that supports it. Concrete generation call, chat template, and embed/rerank regression recipe below. |
| SPK-02 | 用固定/规则锚点在现有 fixture 上跑 `lex:` → `anchor:` 配对对比，产出可复现的方向性信号判定与 delta 表 | Verified `SearchEvaluator`/`evaluate_per_query`/`ndcg_at_k` signatures; fixture is 36 tuning / 20 heldout; tuning-only filtering precedent at `bench.py::_tuning_evaluator`; signal rule from D-08. |
| SPK-03 | 无方向性信号时止损归档假设，不投后续阶段，且不留半成品代码 | Verified `state record-session` flags and mutation behavior; `.planning/tmp/` gitignored; clean-tree proof recipe (`git status --porcelain` + `src/`/`tests/`/lock zero-diff). |
| CTR-01 | MCP 7 工具、5 份 wire goldens 与 `QueryInput` 不变；不新增 `anchor` 请求字段 | Verified tool list, `QueryInput` fields, 5 golden filenames, and both existing pytest files; 11 SHA-256 hashes recomputed and match CONTEXT. |
| CTR-02 | 不新增 runtime 依赖；`test_packaging.py` 冻结的 13 项核心依赖不变 | Verified the 13-entry runtime list and the 3-assertion packaging test; `uv.lock` pins `llama-cpp-python` 0.3.35 from the PyPI sdist. |
</phase_requirements>

## Architectural Responsibility Map

This phase is a research/spike phase, so the usual browser/API/database tiers do not apply. The honest mapping is by **artifact ownership**:

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| GGUF compatibility proof (SPK-01) | Throwaway spike script (`.planning/tmp/phase-25/`) invoking `llama_cpp` directly | Isolated venv for the upgrade trial | No product code may be written; the proof is a generation call plus captured logs. |
| Anchor signal measurement (SPK-02) | Throwaway measurement script importing SIF library APIs read-only | Existing `SearchEvaluator` + `BM25Searcher` (product code, unchanged) | The script owns orchestration; metric math and BM25 stay in the shipped library. |
| Contract freeze proof (CTR-01/02) | Phase-dir evidence artifacts (SHA-256 manifest + Markdown) | Existing pytest files (unchanged) | No new guard is added; the proof is recomputation + running shipped tests. |
| Stop-loss recording (SPK-03) | GSD state (`gsd_run state.record-session`) + phase-dir verdict artifacts | ROADMAP checkbox left unchecked | State changes go through the GSD seam, never direct edits. |

## Standard Stack

### Core

| Tool / Library | Version | Purpose | Why Standard |
|----------------|---------|---------|--------------|
| `llama-cpp-python` (locked) | 0.3.35 (uv.lock) | Baseline `lfm3` load attempt | The exact binding the project ships; proving its behavior is the requirement. |
| `llama-cpp-python` (upgrade candidate) | 0.3.37 (or 0.3.38) | Compatibility fallback evidence | First release whose vendored llama.cpp is **ahead** of v0.8.0 (427 commits), i.e. the first that can load `lfm3`. |
| pytest + pytest-cov | 9.2.0 / 7.17.5 (in `.venv`) | Contract-freeze proof | Existing, shipped test infrastructure — no new guards. |
| SIF `SearchEvaluator` family | in-repo (unchanged) | Paired nDCG@10 delta | D-07 mandates reuse; no metric should be hand-written. |
| SIF `BM25Searcher` | in-repo (unchanged) | Both `lex:` and `anchor:` arms | The `lex:` leg is exactly `BM25Searcher`; the anchor arm only changes the query string. |
| `shasum -a 256` | macOS system | Byte-identical proof | D-10's required mechanism. |
| `gsd_run state.record-session` | GSD runtime | Stop-loss session record | D-15's required mechanism. |

### Supporting

| Tool | Version | Purpose | When to Use |
|------|---------|---------|-------------|
| `uv` | 0.9.26 (on PATH) | Isolated venv + wheel-index installs | Upgrade trial; never used to rewrite the lock. |
| `sqlite-vec` | installed in `.venv` | Only if reusing the `build_bench_db` test helper | The BM25-only arms do not need vector tables. |
| HF/Metal wheel index | `https://abetlen.github.io/llama-cpp-python/whl/metal` | Prebuilt llama-cpp wheels for py3.12 | Avoid compiling the 74.8 MB sdist. |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Isolated venv for 0.3.37 | Install 0.3.37 into project `.venv` | Contaminates the dev env and makes the "locked 0.3.35" baseline ambiguous; D-03 explicitly says isolated venv. |
| Product CLI scratch index | `tests.support.bench.build_bench_db` helper | Helper is shorter but ties the spike to test support and needs sqlite-vec/vec0; product path is more faithful to shipped behavior. |
| `uv sync --extra all` | Explicit wheel-index `uv pip install` | `uv sync` resolves the locked PyPI **sdist** and compiles from source (needs CMake/compiler); the wheel index gives a binary. |
| `llama-server` as conclusion | `llama_cpp.Llama` in-process | D-03: external server is supplemental evidence only and cannot substitute for the binding-level proof. |

**Installation (isolated venv; no project files touched):**

```bash
# Metal prebuilt wheels for Python 3.12 (the .venv is 3.12.8)
uv venv /Users/forrest/GitHub/SIF/.planning/tmp/phase-25/venv-0.3.37 --python 3.12
uv pip install --python /Users/forrest/GitHub/SIF/.planning/tmp/phase-25/venv-0.3.37/bin/python \
  --index https://abetlen.github.io/llama-cpp-python/whl/metal \
  --index-strategy unsafe-best-match \
  'llama-cpp-python==0.3.37'
# Confirm a binary wheel was installed, not an sdist
/Users/forrest/GitHub/SIF/.planning/tmp/phase-25/venv-0.3.37/bin/python -c "import llama_cpp; print(llama_cpp.__version__)"
```

**Version verification (performed this session):**
```bash
pip3 index versions llama-cpp-python        # latest 0.3.38; 0.3.35..0.3.38 listed
# PyPI JSON upload times: 0.3.35 2026-08-17, 0.3.36 2026-10-01, 0.3.37 2026-11-15, 0.3.38 2026-11-23
awk '/^name = "llama-cpp-python"/{f=1} f{print} f&&/^$/{exit}' uv.lock   # version = "0.3.35", PyPI sdist
```

## Package Legitimacy Audit

> No package is **added** to the project by this phase. The isolated-venv experiment installs the same official package the project already depends on. The gate was still run for the upgrade candidate.

| Package | Registry | Age | Downloads | Source Repo | Verdict | Disposition |
|---------|----------|-----|-----------|-------------|---------|-------------|
| `llama-cpp-python` | PyPI | 0.3.35 locked since 2026-08-17; latest 0.3.38 published 2026-11-23 (5 days before research) | 15.2M (pepy.tech, all versions) | `github.com/abetlen/llama-cpp-python` | **SUS** (`too-new`, `unknown-downloads` — gate evaluates the *latest* release) | Already a runtime dep; **no install added to the project**. Isolated-venv experiment is throwaway. Any proposal to change the pin belongs to Phase 26/27 and must pass `checkpoint:human-verify`. |

**Packages removed due to SLOP verdict:** none.
**Packages flagged as suspicious:** `llama-cpp-python` (latest-release recency only; long-standing MIT project, already trusted as the locked runtime dep). Planner should add a `checkpoint:human-verify` before *recommending* any pin bump; not before running the throwaway 0.3.37 experiment.

## Architecture Patterns

### System Architecture Diagram

```
                        ┌──────────────────────────────────────────────┐
  Human-supplied        │  SPK-01 compatibility spike (tmp script)      │
  --model-path ────────▶│  1. Llama(model_path=...)  [0.3.35, plain]   │
  (LFM3-*.gguf)         │     └─ expect RuntimeError: unknown arch     │
                        │  2. isolated venv 0.3.37 → same call          │
                        │     └─ non-empty greedy completion + logs    │
                        │  3. embed/rerank regression under both       │
                        └──────────────────┬───────────────────────────┘
                                           │  artifact fields
                                           ▼
┌──────────────────┐   tuning-only   ┌──────────────────────────────┐
│ queries.json     │──(split filter)─▶│ SPK-02 delta spike (tmp)     │
│ 56 q: 36 tuning  │                 │  build scratch BM25 index from│
│ 20 heldout (NOT  │                 │  committed corpus             │
│  read)           │                 │  arm A: raw query             │
└──────────────────┘                 │  arm B: anchors + query       │
                                     │  SearchEvaluator.evaluate_    │
                                     │   per_query ×2 → pair nDCG@10 │
                                     └──────────────┬───────────────┘
                                                    │
                     ┌──────────────────────────────▼───────────────┐
                     │  Evidence trio (phase dir)                    │
                     │  25-CONTRACT-FREEZE.md                        │
                     │  bench/spike-delta.csv                        │
                     │  bench/spike-verdict.json  ← authoritative    │
                     └──────────────┬───────────────────────────────┘
                                    │
              ┌─────────────────────┴─────────────────────┐
              ▼ signal                                    ▼ no signal
     Phase 26/27 unlocked                      25-SPIKE-VERDICT.md
     (ROADMAP untouched here)                  + state.record-session
                                               + ROADMAP box unchecked
```

Contract freeze runs in parallel with both spikes: 11 files → `shasum -a 256` at start and end → manifest in `25-CONTRACT-FREEZE.md`; the two existing pytest files must be green at both ends; `git status --porcelain` proves `src/`, `tests/`, `pyproject.toml`, `uv.lock` untouched.

### Recommended Project Structure (artifacts only)

```
.planning/phases/25-contract-freeze-feasibility-spike/
├── 25-CONTEXT.md                 # existing
├── 25-DISCUSSION-LOG.md          # existing
├── 25-RESEARCH.md                # this file
├── 25-CONTRACT-FREEZE.md         # D-14 evidence artifact (start/end hashes + commands + git status)
├── 25-SPIKE-VERDICT.md           # D-15 only on no-signal
└── bench/
    ├── spike-delta.csv           # D-14 paired table
    ├── spike-verdict.json        # D-14 authoritative
    └── anchor-table.json         # recommend committing the query-only mapping (D-05)

.planning/tmp/phase-25/           # gitignored (D-13); never committed
├── venv-0.3.37/                  # isolated upgrade trial
├── bench-spike.db                # scratch index
├── spike_compat.py / spike_delta.py / runbook.sh
└── raw logs (stderr, generation output)
```

### Pattern 1: Generation proof (SPK-01) — plain constructor, greedy

**What:** Construct `Llama` **without** `embedding=True`, generate one non-empty completion with `temperature=0.0` (add `top_k=1` to force greedy deterministically), persist the text.
**When to use:** Always for the compatibility proof; D-02 forbids using the embedder's `embedding=True` path as generation evidence.

```python
# Source: llama-cpp-python README + src/sif/embedding/embedder.py:437-469 (create_completion shape)
from llama_cpp import Llama

llm = Llama(model_path=str(model_path), n_ctx=2048, n_threads=None, verbose=False)  # no embedding=True
out = llm.create_completion(
    prompt="Write one short sentence about local search.",
    max_tokens=32,
    temperature=0.0,
    top_k=1,
    stop=["\n"],
)
text = out["choices"][0]["text"]   # OpenAI-style dict: {"choices":[{"text": ...}], "usage": {...}}
# Record: llama_cpp.__version__, GGUF sha256, prompt, chat template, full text, stdout/stderr
```

Expected under 0.3.35: `RuntimeError` whose message/stderr contains `unknown model architecture: 'lfm3'` (llama.cpp throws `std::runtime_error`; pybind11 re-raises as `RuntimeError`). Catch broadly and record `type(e).__name__`, `str(e)`, and captured stderr.

### Pattern 2: Tuning-only paired delta (SPK-02)

**What:** Filter to `split == "tuning"` before constructing the evaluator; run two `search_fn`s; pair per-query `ndcg_at_10`.
**When to use:** The only accepted Phase-25 signal measurement (D-06/D-07).

```python
# Source: src/sif/search/benchmark.py (verified this session)
import json
from pathlib import Path
from sif.search.benchmark import SearchEvaluator, recall_at_k
from sif.search.bm25 import BM25Searcher
from sif.core.models import SearchOptions

fixture_path = Path("tests/fixtures/bench/queries.json")
data = json.loads(fixture_path.read_text(encoding="utf-8"))
tuning = [q for q in data["queries"] if q.get("split") == "tuning"]   # 36 items
tuning_fixture = {k: v for k, v in data.items() if k != "queries"}
tuning_fixture["queries"] = tuning
evaluator = SearchEvaluator(tuning_fixture, fixture_path=fixture_path)

searcher = BM25Searcher(conn)                       # scratch DB built from tests/fixtures/bench/corpus
opts = SearchOptions(limit=10, include_content=False)

def lex_fn(q: str):
    return searcher.search(q, opts)

def anchor_fn(q: str):
    anchors = derive(query_only_anchors(q))         # never reads relevance/gold
    return searcher.search(" ".join(anchors + [q]), opts)

base = evaluator.evaluate_per_query(lex_fn, k=10)
anch = evaluator.evaluate_per_query(anchor_fn, k=10)

for item, b, a in zip(evaluator.query_items, base, anch, strict=True):
    total_relevant = sum(1 for g in item.grades.values() if g > 0)  # benchmark.py:609/672 semantics
    # recall_at_k(b.grades, total_relevant, 10) for the diagnostic column
```

Pair on fixture order (both calls iterate `evaluator.query_items` in the same order). The `anchor:` prefix is only a **label** for the arm; the spike script must not teach product code any prefix.

### Pattern 3: Contract freeze — double hash + shipped tests

```bash
# Start and end; output both blocks into 25-CONTRACT-FREEZE.md
shasum -a 256 pyproject.toml uv.lock \
  tests/unit/mcp/test_wire_transcripts.py tests/unit/mcp/test_packaging.py \
  src/sif/mcp/protocol.py src/sif/mcp/tools.py \
  tests/unit/mcp/goldens/*.json

# CRITICAL: --no-cov or the coverage gate fails the run (13 tests still pass)
/Users/forrest/GitHub/SIF/.venv/bin/python -m pytest \
  tests/unit/mcp/test_wire_transcripts.py tests/unit/mcp/test_packaging.py -q --no-cov

# Baseline integrity (should be empty)
git diff --stat v1.2.5..HEAD -- pyproject.toml uv.lock src/sif/mcp/ tests/unit/mcp/
git status --porcelain
```

### Anti-Patterns to Avoid

- **Writing a pytest guard or CI step for the freeze:** D-10 forbids it; the proof is recomputation + existing tests.
- **Adding `anchor:` to `prefix_map` / `SearchType` / `QueryInput`:** CTR-01 and ANC-03 keep that for Phase 26; this phase must not touch them.
- **Deriving anchors from gold titles/paths or the relevance map:** D-05 — it leaks labels and destroys falsifiability.
- **Reading `heldout` rows or `heldout_defaults.json` for the go/no-go:** D-06 — artifact must record `heldout_read: false`.
- **Using `warrants_default_change`, 0.01, or bootstrap:** those are Phase-27 gates (D-08).
- **Committing spike scripts or scratch DBs:** D-13; keep them under `.planning/tmp/phase-25/`.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| nDCG/Hit/Recall math | Custom Python | `ndcg_at_k`, `hit_at_k`, `recall_at_k` (`benchmark.py:53-101`) | Verified exponential-gain DCG, ideal-from-full-judgment, binarized recall semantics. |
| Tuning-split filtering | New filter logic | Mirror `_tuning_evaluator` (`src/sif/cli/commands/bench.py:325-346`) | Existing guard filters before any search call, carrying fixture metadata. |
| BM25 search | Raw FTS5 SQL | `BM25Searcher(db).search(query, SearchOptions)` | Handles FTS query construction, min_score, ordering, snippets. |
| Scratch index build | Manual INSERTs | `SIF_DB_PATH=... sif collection add` + `sif index update` (or `build_bench_db`) | Real schema/FTS triggers/paths; matches shipped behavior. |
| Contract hashing | A new Python test | `shasum -a 256` + the two existing pytest files | D-10 requires exactly this; no new engineering surface. |
| State recording | Editing STATE.md/ROADMAP.md directly | `gsd_run state.record-session` | Repo convention; direct edits bypass the audit chain. |
| GGUF generation | Shelling to `llama-cli` | `llama_cpp.Llama` in the isolated venv | D-02 requires the binding-level proof; CLI is not the locked API. |

**Key insight:** every metric and contract mechanism this phase needs already exists and is frozen; the spike's only new code is throwaway orchestration.

## Runtime State Inventory

> Included because the phase's stop-loss requires proving no runtime residue. This is not a rename/refactor phase, but the same categories answer "what survives outside git?"

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| Stored data | None — no database is mutated. A scratch index is created fresh under `.planning/tmp/phase-25/` and is disposable. The user's real index (`SIF_DB_PATH` default) must never be pointed at. | Set `SIF_DB_PATH` to the scratch path for every command. |
| Live service config | None — no MCP server, daemon, watcher, or external service is started. | None. |
| OS-registered state | None — no launchd/pm2/systemd/Task Scheduler entries created. | None. |
| Secrets/env vars | None — no API keys, no network calls (D-01 forbids auto-download; D-05 forbids LLM calls). `SIF_DB_PATH` is a path override only. | None. |
| Build artifacts / installed packages | Isolated venv at `.planning/tmp/phase-25/venv-0.3.37/` (deleteable). If llama-cpp-python is installed into `.venv`, that is a gitignored environment change, not a repo change. `pyproject.toml`/`uv.lock` must stay byte-identical. | Delete the venv during cleanup, or leave it gitignored; never touch the lock files. |

**Canonical question — after every repo file is unchanged, what still holds the old state?** Only gitignored scratch (venv, DB, logs) under `.planning/tmp/phase-25/`, plus the expected `STATE.md` session-record mutation. Verified: `.planning/tmp/` is ignored at `.gitignore:49` (`# GSD phase scratch (arm DBs, saved runs, run state)` / `.planning/tmp/`).

## Common Pitfalls

### Pitfall 1: Targeted pytest runs fail the coverage gate
**What goes wrong:** `pytest tests/unit/mcp/test_packaging.py` reports `3 passed` but exits nonzero with `FAIL Required test coverage of 90.0% not reached. Total coverage: 6.20%`.
**Why it happens:** `pyproject.toml` `[tool.pytest.ini_options]` puts `--cov=src/sif --cov-report=...` in `addopts`, so every invocation enforces `fail_under=90`.
**How to avoid:** append `--no-cov` for any subset. Verified: both files with `--no-cov` → **13 passed in 0.60 s**.
**Warning signs:** "13 passed" followed by a coverage FAIL and a nonzero exit code.

### Pitfall 2: Assuming 0.3.35 can load `lfm3`
**What goes wrong:** a plan that treats a load failure as an unexpected blocker or "fixes" it by editing the lock.
**Why it happens:** the lock predates lfm3 support by ~2.5 months.
**How to avoid:** record the failure as the expected locked-version result, then run the isolated 0.3.37 trial (D-03).
**Warning signs:** any proposed edit to `pyproject.toml`/`uv.lock`.

### Pitfall 3: `embedding=True` used as generation proof
**What goes wrong:** `LlamaCppEmbedder` constructs `Llama(..., embedding=True)`; reusing it proves the embed path, not generation.
**Why it happens:** it is the only in-repo `Llama` construction.
**How to avoid:** D-02 — plain constructor in the spike script.
**Warning signs:** the compat script imports `LlamaCppEmbedder` for generation.

### Pitfall 4: Held-out leakage
**What goes wrong:** the evaluator is built from the whole fixture, or `heldout_defaults.json` is consulted for the verdict.
**Why it happens:** `SearchEvaluator` happily loads all 56 queries.
**How to avoid:** filter `split == "tuning"` before construction (36 queries); artifact records `heldout_read: false`.
**Warning signs:** `num_queries: 56` in the delta artifact.

### Pitfall 5: Recall denominator confusion
**What goes wrong:** Recall@10 exceeds 1.0 or is computed against retrieved count.
**Why it happens:** `recall_at_k` expects `total_relevant` = count of `grade > 0` in the judgment set.
**How to avoid:** `total_relevant = sum(1 for grade in item.grades.values() if grade > 0)` (benchmark.py:609/672); `evaluate_per_query` does **not** compute recall, so do it from `evaluator.query_items`.
**Warning signs:** any recall > 1.0.

### Pitfall 6: Path-key mismatch
**What goes wrong:** every retrieved grade is 0 because result paths are absolute while fixtures use corpus-relative POSIX keys.
**Why it happens:** `relevance_key: "path"` and `result_key` resolves against `corpus_root`.
**How to avoid:** build the scratch index from `tests/fixtures/bench/corpus` so `result_key` yields `keyword/kw-002.md`; pass `fixture_path` so relative `corpus_root: "corpus"` resolves.
**Warning signs:** all-zero per-query nDCG.

### Pitfall 7: Over-proving with the full suite
**What goes wrong:** a multi-minute full pytest run that touches the real model cache (documented in STATE).
**Why it happens:** habit / project gate language.
**How to avoid:** this phase changes no code; prove integrity with `shasum`, the two MCP files, and `git diff`. Run the full suite only if a plan task actually touches shared files (it must not).
**Warning signs:** plan tasks that run `pytest` without `--no-cov` or on the full tree.

### Pitfall 8: Stale freeze narrative
**What goes wrong:** the artifact copies the CONTEXT statement "4 commits since v1.2.5".
**Why it happens:** CONTEXT was written at discussion time.
**How to avoid:** recompute `git log --oneline v1.2.5..HEAD` (7 commits at research time) and `git diff --stat v1.2.5..HEAD -- <contract paths>` (empty). Record measured values.
**Warning signs:** a commit count that does not match the execution-time log.

## Code Examples

Verified patterns from in-repo sources:

### Scratch BM25 index (product path)

```bash
# Source: src/sif/cli/commands/collection.py:32-74 + index.py:63-101
SCRATCH=/Users/forrest/GitHub/SIF/.planning/tmp/phase-25
SIF_DB_PATH=$SCRATCH/bench-spike.db .venv/bin/python -m sif.cli.main \
  collection add /Users/forrest/GitHub/SIF/tests/fixtures/bench/corpus --name bench
SIF_DB_PATH=$SCRATCH/bench-spike.db .venv/bin/python -m sif.cli.main index update
```

### Paired per-query evaluation (exact signatures)

```python
# Source: src/sif/search/benchmark.py
# SearchEvaluator.__init__(fixture, fixture_path=None, corpus_root=None)      :433-438
# SearchEvaluator.evaluate_per_query(search_fn, k=DEFAULT_K) -> list[QueryEvaluation] :547-551
# ndcg_at_k(retrieved, ideal, k) :86 ; hit_at_k(retrieved, k) :99 ; recall_at_k(relevance, total_relevant, k) :53
# QueryEvaluation fields: query, retrieved_keys, retrieved_paths, grades, ndcg_at_10, hit_at_10 :217-235
```

### Verdict JSON shape (mirror Phase 23/24 conventions)

Observed top-level keys: Phase 23 verdict `['arms','corpus','decision','default_flip','environment','gates','min_heldout_for_epsilon_win','notes','query_set_fingerprint','replay','rule','version']`; Phase 24 sweep adds `schema_version`, `selection_rule`, `selected_arm`, `corpus_label`, `limitation`. Recommended Phase-25 shape:

```json
{
  "version": 1,
  "decision": "directional-signal | no-signal | not-applicable",
  "rule": "mean paired delta > 0 AND helped > hurt",
  "arms": {"lex": {"ndcg_at_10": 0.0}, "anchor": {"ndcg_at_10": 0.0}},
  "queries": {"n": 36, "split": "tuning", "heldout_read": false},
  "delta": {"mean": 0.0, "helped": 0, "hurt": 0, "unchanged": 0, "noise_floor_1_over_n": 0.027778},
  "reproducibility": {"seed": 0, "rng_used": false, "fixture_sha256": "...", "anchor_table_sha256": "...", "script_sha256": "..."},
  "environment": {"python": "3.12.8", "llama_cpp": null, "pytest": "9.2.0"},
  "compatibility": {"locked_version": "0.3.35", "locked_result": "unknown model architecture: 'lfm3'", "upgrade_version": "0.3.37", "upgrade_result": "loaded+generated", "embed_rerank_impact": "..."},
  "notes": []
}
```

### Stop-loss session record (D-15)

```bash
gsd_run state record-session \
  --stopped-at "Phase 25 no directional signal — hypothesis archived; Phases 26/27 not started; working tree clean" \
  --resume-file /Users/forrest/GitHub/SIF/.planning/phases/25-contract-freeze-feasibility-spike/25-SPIKE-VERDICT.md
```
(`--stopped-at` or `--resume-file` is required; it rewrites STATE frontmatter `stopped_at`/`last_updated`/`state_head` and the Session Continuity block.)

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| No LFM3 in llama.cpp | `lfm3` added in llama.cpp v0.8.0 (PR #31252, build b11938) | 2026-10-28 | Bindings must vend a commit ≥ v0.8.0. |
| llama-cpp-python 0.3.35 (llama.cpp `adb55e514`) | 0.3.36 (`0c1e57098`) still behind; **0.3.37** (`a956a852c`) first ahead; 0.3.38 (`f5e6915c2`) latest | 2026-11-15 / 2026-11-23 | 0.3.37 is the minimum viable upgrade target. |
| PyPI sdist-only install | Official per-backend wheel indexes (cpu/cu121/metal) | Documented in `docs/installation.md:159-210` | Avoid a 74.8 MB source build on Python 3.12. |
| 0.01 + bootstrap gate | Reserved for Phase 27 | v1.3 decision | Phase 25 uses only the directional rule. |

**Deprecated/outdated:**
- CONTEXT's "4 commits since v1.2.5" — measured 7 at research time; recompute at execution.
- Treating `llama-server` as a compatibility conclusion — supplemental evidence only (D-03).

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | 0.3.35 raises Python `RuntimeError` containing `unknown model architecture: 'lfm3'` | Summary / Pattern 1 | Low — catch `Exception`, record `type(e).__name__` + `str(e)` + stderr; the artifact stays correct either way. |
| A2 | Prebuilt macOS arm64 / Python 3.12 wheels exist for 0.3.37 on the Metal index | Standard Stack / Installation | Medium — falls back to a source build needing CMake/clang; record which path was taken. |
| A3 | The user can supply `LFM3-1.7B-Q4_K_M.gguf` at execution time | Environment Availability | High — no GGUF was found on this machine; without it SPK-01 cannot be completed (hard checkpoint). |
| A4 | `temperature=0.0` (+`top_k=1`) is deterministic greedy | Pattern 1 | Low — if output varies, record the observation; the proof only needs one non-empty text. |
| A5 | A scratch index built from the committed corpus yields corpus-relative result keys | Pattern 2 / Pitfall 6 | Medium — verified structurally by existing tests but not executed in this research; assert at run time that the first query returns non-zero grades. |
| A6 | Installing a newer llama-cpp-python into an isolated venv leaves the project lock untouched | Standard Stack | Low — `uv pip install` into a separate venv cannot rewrite the repo's `uv.lock`; verify hashes at start/end. |

**If this table were empty:** all claims would be verified or cited. It is not: A1-A6 need runtime confirmation.

## Open Questions

1. **Upgrade target: 0.3.37 or 0.3.38?**
   - What we know: both are ahead of v0.8.0 (0.3.37 by 427 commits; 0.3.38 latest).
   - What's unclear: which the team wants to name as the future pin candidate.
   - Recommendation: use 0.3.37 for the evidence (first supporting release, one release of soak); record 0.3.38 as available. No pin change in Phase 25.

2. **Where the query-only anchor table lives.**
   - What we know: D-05 calls it "一张提交的 query-only 映射表".
   - What's unclear: committed file vs embedded in the authoritative JSON.
   - Recommendation: commit `bench/anchor-table.json` **and** record its SHA-256 in `spike-verdict.json` (satisfies both "committed table" and "JSON authoritative, same-source").

3. **Embed/rerank regression when no cross-version GGUF is guaranteed.**
   - What we know: `LlamaCppEmbedder` and `LlamaCppReranker` both use `Llama(..., embedding=True)`; a cross-version comparison needs a GGUF both versions support.
   - What's unclear: whether the user will supply one; `~/.cache/qmd/models/hf_Qwen_Qwen3-Embedding-0.6B-Q8_0.gguf` exists but belongs to another project.
   - Recommendation: make the regression check optional with an explicit `embed_rerank_impact: "not measured — no cross-version GGUF"` limitation; if the LFM3 GGUF loads under 0.3.37, also record its `embed()` shape under 0.3.37.

4. **Acceptance shape of "one generation" for a reasoning model.**
   - What we know: LFM3 emits `<think>` first; `max_tokens=32` may be all reasoning.
   - What's unclear: whether the team wants the visible answer or accepts any non-empty text.
   - Recommendation: D-02 only requires non-empty; record raw output verbatim and cap at a documented `max_tokens` (e.g. 64).

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python (`.venv`) | everything | ✓ | 3.12.8 | — |
| `uv` | venv / wheel-index installs | ✓ | 0.9.26 | `pip` |
| `llama-cpp-python` (locked 0.3.35) | SPK-01 baseline | ✗ in `.venv` | — (lock has PyPI sdist only) | Install from Metal wheel index into `.venv`, or isolated venv |
| `llama-cpp-python` ≥0.3.37 | SPK-01 upgrade evidence | ✗ | — | Isolated venv from wheel index |
| `LFM3-1.7B-Q4_K_M.gguf` | SPK-01 proof | ✗ (not found) | — | **Human must supply `--model-path`** (D-01 forbids download) |
| `sqlite-vec` | only the `build_bench_db` helper | ✓ | — | BM25-only path needs no vec0 |
| pytest / pytest-cov | contract tests | ✓ | 9.2.0 / 7.17.5 | — |
| Cross-version GGUF (embed regression) | D-04 regression | ✓ (external) | Qwen3-Embedding GGUF 610 MB at `~/.cache/qmd/models/` | Mark "not measured" |
| C++ toolchain / CMake | source builds only | unknown | — | Prefer wheel index |

**Missing dependencies with no fallback:**
- `LFM3-1.7B-Q4_K_M.gguf` — the phase cannot satisfy success criterion 1 without the user supplying a path. The plan MUST begin with a `checkpoint:human-verify` that records the resolved absolute path (and per D-01, never hard-codes it).

**Missing dependencies with fallback:**
- `llama-cpp-python` in `.venv` — installable from the wheel index or an isolated venv.
- Cross-version GGUF — the regression check degrades to a recorded "not measured" limitation.

## Validation Architecture

> `workflow.nyquist_validation` is `true` in `.planning/config.json` (verified), so this section is required. The honest framing: this phase adds **no pytest guards and no `src/sif` code**, so most verification is artifact/command-output based.

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 9.2.0 + pytest-cov 7.17.5 |
| Config file | `pyproject.toml` → `[tool.pytest.ini_options]` (addopts include `--cov=src/sif --cov-report=term-missing --cov-report=html --cov-report=xml`; `[tool.coverage.report]` `fail_under=90`) |
| Quick run command | `/Users/forrest/GitHub/SIF/.venv/bin/python -m pytest tests/unit/mcp/test_wire_transcripts.py tests/unit/mcp/test_packaging.py -q --no-cov` |
| Full suite command | `/Users/forrest/GitHub/SIF/.venv/bin/python -m pytest -q` (a few thousand tests; not required for this phase) |
| Targeted runtime (measured) | **0.60 s, 13 passed** for the two contract files with `--no-cov` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| SPK-01 | locked 0.3.35 fails with `unknown model architecture: 'lfm3'`; 0.3.37 loads and generates | manual / artifact | `python spike_compat.py --model-path <abs .gguf>` (tmp); no pytest | ❌ Wave 0 N/A — artifact-based |
| SPK-02 | paired tuning-only nDCG@10 delta + ruled verdict | manual / artifact | `python spike_delta.py` (tmp); no pytest | ❌ Wave 0 N/A — artifact-based |
| SPK-03 | stop-loss recorded; clean tree | manual / artifact | `git status --porcelain`; `git diff --stat v1.2.5..HEAD -- <contract paths>`; `state record-session` | ❌ Wave 0 N/A — artifact-based |
| CTR-01 | 5 goldens + wire transcripts + 7 tools + `QueryInput` unchanged | unit (existing) | `pytest tests/unit/mcp/test_wire_transcripts.py tests/unit/mcp/test_packaging.py -q --no-cov` | ✅ existing |
| CTR-02 | 13 runtime deps unchanged | unit (existing) | same command (`test_packaging.py` 3 tests) | ✅ existing |

### Sampling Rate

- **Per task commit:** `shasum -a 256` over any touched freeze file (expect no change), and the quick pytest command if §CTR is in scope for that task.
- **Per wave merge:** full 11-file manifest recomputed and diffed against the start manifest; quick pytest command green.
- **Phase gate:** start manifest == end manifest; two pytest files green; `git status --porcelain` shows only `STATE.md` (session record) + the 3 whitelisted untracked planning docs; `src/`, `tests/`, `pyproject.toml`, `uv.lock` zero diff.

### Wave 0 Gaps

**None — existing infrastructure covers all phase requirements.** This phase deliberately adds no test files, no fixtures, and no `src/sif` code. The only "framework" needs are `shasum`, `git`, the existing pytest pair, and `gsd_run state.record-session`, all present.

**Manual-only verifications (no automation, by design):**
- GGUF availability and the actual generation text (requires the human-supplied file).
- Isolated-venv upgrade install and its success/failure transcript.
- Visual inspection that the verdict rule was applied literally (mean > 0 AND helped > hurt).

## Security Domain

> `security_enforcement` is absent from config → enabled. The phase is a local spike, but it still handles an untrusted binary model and an untrusted path argument.

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|------------------|
| V2 Authentication | no | No auth surface. |
| V3 Session Management | no | No sessions. |
| V4 Access Control | no | Single local user. |
| V5 Input Validation | **yes** | Validate `--model-path`: must be an existing absolute file with a `.gguf` suffix; reject relative/nonexistent paths with a message. Never interpolate paths into shell strings; use argument lists. |
| V6 Cryptography | **yes** (hashing only) | SHA-256 via `shasum`/`hashlib`; never hand-roll. |
| V12 Files/Resources | yes | All scratch output confined to `.planning/tmp/phase-25/`; no writes to the user's real DB. |
| V14 Configuration | yes | No env var as the only entry point (D-01); no network; no secrets. |

### Known Threat Patterns for this stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Malformed/untrusted GGUF crashes or exploits the native parser | Tampering / DoS | Run the load in a subprocess and capture stderr; do not reuse the user's main shell state; accept that a native crash is a recorded result, not a repo change. |
| Shell/path injection via `--model-path` | Tampering | Use `subprocess.run([...])` / direct API calls; validate the path; never string-format a shell command. |
| Accidental network access (model download, LLM call) | Information disclosure | D-01/D-05: no download, no LLM; the anchor derivation is a pure function of the query string. Assert it receives only `str`. |
| Label leakage from gold files | Tampering (evaluation integrity) | The tuning filter and anchor derivation must not open the relevance map or document titles; record `heldout_read: false`. |
| Supply-chain risk from a third-party wheel index | Tampering | Install only into a throwaway venv; confirm the artifact is `llama_cpp*.whl`; record the exact version; no project pin change. |
| Overwriting the user's real index | Tampering | Always set `SIF_DB_PATH` to the scratch path; assert the path is under `.planning/tmp/phase-25/` before running. |

## Sources

### Primary (HIGH confidence)
- `https://github.com/ggml-org/llama.cpp/releases/tag/v0.8.0` — release date 2026-10-28, tag `8642541`, LFM3 text/vision/audio/omni support, PR #31252.
- GitHub compare API (`ggml-org/llama.cpp`): `8642541...adb55e514` = behind 1514; `8642541...0c1e57098` = behind 648; `8642541...a956a852c` = ahead 427.
- `https://raw.githubusercontent.com/abetlen/llama-cpp-python/main/CHANGELOG.md` — vendored llama.cpp commits for 0.3.35–0.3.38.
- `https://pypi.org/pypi/llama-cpp-python/json` — upload dates and latest 0.3.38.
- `https://huggingface.co/LiquidAI/LFM3-1.7B-GGUF` — requires llama.cpp b11960 (v0.8.0)+; Q4_K_M 1.1 GB; sampling defaults.
- `https://huggingface.co/LiquidAI/LFM3-1.7B` — ChatML-style template (`<|startoftext|>`, `<|im_start|>`, `<|im_end|>`, `<think>`).
- `https://raw.githubusercontent.com/ggml-org/llama.cpp/master/src/llama-model.cpp` — `throw std::runtime_error("unknown model architecture: '" + ml.get_arch_name() + "'")`.
- In-repo (Read this session): `src/sif/search/benchmark.py`, `src/sif/search/bm25.py`, `src/sif/search/hybrid.py`, `src/sif/embedding/embedder.py`, `src/sif/search/rerank.py`, `src/sif/mcp/protocol.py`, `src/sif/mcp/tools.py`, `src/sif/mcp/backend.py`, `src/sif/core/models.py`, `src/sif/cli/commands/bench.py`, `src/sif/cli/commands/collection.py`, `src/sif/indexing/incremental.py`, `tests/fixtures/bench/queries.json`, `tests/support/bench.py`, `docs/installation.md`, `docs/testing.md`, `pyproject.toml`, `uv.lock`, `.gitignore`.

### Secondary (MEDIUM confidence)
- `https://github.com/abetlen/llama-cpp-python` README — `create_completion` OpenAI-style return shape; `embedding=True` semantics.
- Web search corroboration of the Ollama `unknown model architecture: 'lfm3'` report (downstream binding lag).

### Tertiary (LOW confidence)
- Per-version availability of the 0.3.37 Metal wheel (not listed individually; the index recipe is documented but unverified for that exact version).

## Metadata

**Confidence breakdown:**
- Compatibility verdict (0.3.35 cannot load lfm3; 0.3.37 can): **HIGH** — ancestry checked directly against the authoritative repo via the compare API, corroborated by release notes and the model card.
- In-repo API surfaces and contract state: **HIGH** — read with line numbers; all 11 hashes recomputed and matched.
- Contract-freeze commands (coverage trap): **HIGH** — executed (`13 passed, 0.60 s` with `--no-cov`).
- Upgrade wheel availability: **MEDIUM** — recipe documented, exact wheel not enumerated.
- Python exception type: **MEDIUM** — source-level, not executed locally.

**Research date:** 2026-11-28
**Valid until:** ~2026-12-28 for the in-repo contract state (fast-moving milestone; re-run the hashes at plan start), and ~30 days for the llama.cpp/llama-cpp-python release facts (fast-moving).
