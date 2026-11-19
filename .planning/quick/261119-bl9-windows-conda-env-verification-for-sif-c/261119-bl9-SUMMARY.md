---
phase: quick-261119-bl9
plan: 01
subsystem: embedding/device-selection
tags: [pytorch, intel-xpu, cuda, mps, sentence-transformers, modelscope, conda, windows, verification]

requires: []
provides:
  - "Typed `_auto_device(torch)` helper with CUDA > Intel XPU > Apple MPS > CPU precedence, used by SentenceTransformerEmbedder and ModelScopeEmbedder"
  - "Model-free XPU/precedence/constructor unit tests with xpu-aware torch doubles"
  - "Intel XPU documentation in docs/configuration.md (generator-owned) and docs/installation.md"
  - "Three-env Windows conda verification matrix for dnallm-cpu, dnallm-cuda, dnallm-xpu"
affects: [embedding, configuration-docs, installation-docs]

actuals:
  tokens: 2373
  tasks: 3
  commits: 1
plan_head_before: 25bf8c32ff186f0794fd08b8738bc4734a10dc20
plan_head_after: 82df76b0510e62077a65a8eac2bd447154e23bf6

tech-stack:
  added: []
  patterns:
    - "One module-level `_auto_device(torch_module)` helper centralizes device precedence for both embedding backends; explicit `device=` bypasses it"

key-files:
  created:
    - .planning/quick/261119-bl9-windows-conda-env-verification-for-sif-c/261119-bl9-env-matrix.md
    - .planning/quick/261119-bl9-windows-conda-env-verification-for-sif-c/261119-bl9-SUMMARY.md
  modified:
    - src/sif/embedding/embedder.py
    - tests/unit/embedding/test_embedder_impl.py
    - tests/unit/embedding/test_factory.py
    - scripts/generate_config_ref.py
    - docs/configuration.md
    - docs/installation.md

key-decisions:
  - "XPU precedence is CUDA > Intel XPU > Apple MPS > CPU; `getattr` guards let torch builds without XPU/MPS fall through"
  - "No settings field or CLI flag: automatic detection plus the existing explicit `device=` constructor argument remains the shipped contract"
  - "Vendor torch builds (2.11.0+cpu / +cu130 / +xpu) are preserved untouched; the version-floor drift is recorded, not repaired"
  - "Windows full-suite failures are pre-existing platform drift (POSIX-only tests), recorded not repaired"

requirements-completed: [QUICK-WIN-CONDA-XPU]

coverage:
  - id: D1
    description: "Intel XPU auto-detection helper with CUDA > XPU > MPS > CPU precedence, wired into both embedder constructors"
    requirement: QUICK-WIN-CONDA-XPU
    verification:
      - kind: unit
        ref: "tests/unit/embedding/test_embedder_impl.py (precedence, XPU constructor, explicit-device tests)"
        status: pass
      - kind: integration
        ref: "D:/miniconda3/envs/dnallm-{cpu,cuda,xpu}/python.exe -c '... _auto_device(torch); torch.zeros(8, device=d)' -> cpu/cuda/xpu"
        status: pass
    human_judgment: false
  - id: D2
    description: "Three conda environments provisioned and verified with exact package facts, commands, and per-env verdicts"
    requirement: QUICK-WIN-CONDA-XPU
    verification:
      - kind: integration
        ref: ".planning/quick/261119-bl9-.../261119-bl9-env-matrix.md (imports, sqlite-vec, smoke 8/8, scoped pytest 269 passed x3)"
        status: pass
    human_judgment: true
    rationale: "The matrix is a machine-facts report whose interpretation (which drift is acceptable) is a maintainer judgment."
  - id: D3
    description: "Generator-owned and manual documentation state Intel XPU auto-detection and its XPU-enabled torch requirement"
    verification:
      - kind: other
        ref: "python scripts/generate_config_ref.py second run leaves docs/configuration.md byte-identical"
        status: pass
    human_judgment: false
  - id: D4
    description: "Full repo quality suite green under `uv run --frozen --extra dev --extra embed` with PYTHONUTF8=1"
    verification:
      - kind: other
        ref: "python -m pytest -q --ignore=tests/unit/cli/test_index_locking.py"
        status: fail
    human_judgment: false
    rationale: "Not green on this Windows host: 63 failed / 27 errors, all pre-existing POSIX-only tests unrelated to the XPU change; coverage gate reached at 94.23%. Recorded, not repaired."
    verification_note: "Coverage gate itself passed; only platform-specific tests failed."

duration: ~45min
completed: 2026-11-19
status: complete
---

# Quick Task 261119-bl9: Windows Conda Env Verification and Intel XPU Auto-Selection

**SIF now auto-selects Intel XPU (CUDA > XPU > MPS > CPU) in both embedding backends, and all three Windows conda envs — cpu, cuda, xpu — verify PASS-WITH-FINDINGS with their vendor torch builds preserved.**

## Performance

- **Duration:** ~45 min (plan authored 2026-11-19T00:37Z, final gate 01:22Z)
- **Started:** 2026-11-19T00:37Z
- **Completed:** 2026-11-19T01:22Z
- **Tasks:** 3 (2 implementation/verification tasks complete; Task 3 final gate executed here)
- **Files modified:** 6 committed + 2 planning artifacts

## Accomplishments

- Confirmed the XPU gap: `src/sif/embedding/embedder.py` had two duplicated CUDA→MPS→CPU blocks and no `xpu` reference, so an XPU host silently fell back to CPU.
- Added the typed `_auto_device(torch_module) -> str` helper with precedence CUDA > Intel XPU > Apple MPS > CPU and `getattr` guards; both `SentenceTransformerEmbedder.__init__` and `ModelScopeEmbedder.__init__` now delegate to it only when `device is None`.
- Added nine model-free tests (precedence, XPU constructor, explicit-device bypass, missing-attribute fallbacks) and declared `xpu.is_available() == False` on every MagicMock torch double so existing CPU/MPS assertions stay deterministic.
- Updated the generator-owned `docs/configuration.md` (second generator run byte-identical) and the manual `docs/installation.md` to document Intel XPU and its XPU-enabled torch requirement.
- Provisioned and verified three Windows conda envs without touching their torch builds; real device probes resolve `cpu`, `cuda`, and `xpu`, each executing `torch.zeros(8, device=d)` successfully.
- Produced `.planning/quick/261119-bl9-windows-conda-env-verification-for-sif-c/261119-bl9-env-matrix.md` with exact interpreter paths, versions, commands, package deltas, findings, and verdicts.

## Task Commits

1. **Task 1: Provision and verify the three conda envs; confirm the XPU gap** — no commit (package installs only; repository tree untouched by design).
2. **Task 2: Add Intel XPU to automatic device selection** — `82df76b` (feat: auto-select Intel XPU in embedding device detection).
3. **Task 3: Re-verify all envs, write the env matrix, run the full quality gate** — no commit (the orchestrator commits the planning artifacts; verification only).

**Plan metadata:** intentionally uncommitted — the orchestrator commits `SUMMARY.md`, `PLAN.md`, `env-matrix.md`, and `STATE.md`.

## Files Created/Modified

- `src/sif/embedding/embedder.py` — `_auto_device` helper; both constructors use it.
- `tests/unit/embedding/test_embedder_impl.py` — xpu-aware doubles plus 9 new tests.
- `tests/unit/embedding/test_factory.py` — factory torch double declares XPU unavailable.
- `scripts/generate_config_ref.py` — device-selection note names XPU and its torch-build requirement.
- `docs/configuration.md` — regenerated device-selection section.
- `docs/installation.md` — manual auto-detection and hardware-acceleration prose includes Intel XPU.
- `261119-bl9-env-matrix.md` — three-env machine-facts report.

## Three-Env Verdicts

| Env | Verdict | One-line reason |
|-----|---------|-----------------|
| dnallm-cpu | PASS-WITH-FINDINGS | Imports, sqlite-vec v0.1.9, CLI 1.2.1, smoke 8/8, scoped pytest 269 passed, torch `2.11.0+cpu` preserved, `_auto_device` → `cpu`. Drift: torch below `>=2.14` floor, external `mcp<2` pins, DialoGPT encode drift. |
| dnallm-cuda | PASS-WITH-FINDINGS | Same gates; torch `2.11.0+cu130` preserved (CUDA 13.0, 1 device), `_auto_device` → `cuda` with a successful tensor op. Same three drift records. |
| dnallm-xpu | PASS-WITH-FINDINGS | Same gates; torch `2.11.0+xpu` preserved (XPU 1 device), `_auto_device` → `xpu` with a successful tensor op. Same three drift records. |

No env is `FAIL(build-mismatch)` (torch strings byte-identical) or `FAIL(extension)` (sqlite-vec loads everywhere). The only non-zero per-env gate is `pip check`, caused by third-party packages external to SIF.

## Final Quality Gate

- **Full suite:** `3148 passed, 63 failed, 10 skipped, 27 errors in 370.95s`, coverage **94.23%** — the repo's 90% gate was reached. The pytest exit status is 1 solely because of pre-existing Windows/POSIX-only tests.
- **Collection prerequisite:** `tests/unit/cli/test_index_locking.py` imports `fcntl` unguarded at module scope and aborts collection on Windows (exit 2). That file is unchanged by this task; its sibling `tests/unit/database/test_locking.py` correctly uses `pytest.importorskip`. The suite was therefore run with `--ignore=tests/unit/cli/test_index_locking.py`. Not repaired (out of scope).
- **Failure classification (all pre-existing/unrelated):** symlink creation requires a privilege Windows does not grant this shell (`WinError 1314`), `os.getuid`/`os.killpg` absent, `SIGKILL` unsupported (`ValueError: Unsupported signal`), POSIX `os.fork` detach unavailable by design, launchd/systemd service tests are POSIX-only, and several path/glob/subpath assertions differ under Windows semantics. Zero failures originate in embedding or XPU code; `src/sif/embedding/embedder.py` coverage is 94% including the new helper.
- **ruff check** (`uv run --frozen --extra dev --extra embed ruff check src tests`): All checks passed.
- **ruff format --check**: 237 files already formatted.
- **ty check src/sif**: exit 1, 22 diagnostics — all pre-existing Windows environment drift (POSIX-only `fcntl`, `os.getuid`, `os.killpg`, `signal.SIGKILL`; third-party sentence-transformers/transformers typing). The same 22 diagnostics appear on a pristine `git archive` of HEAD `25bf8c3` with the same interpreter (env-matrix Finding 7). Not repaired; the new `_auto_device` helper adds zero diagnostics.

## Deviations from Plan

1. **Full pytest suite is not exit-0 on this Windows host (pre-existing).** The plan's success criterion "full repo quality suite is green" cannot be met on Windows because the suite contains unguarded POSIX-only tests (including an unconditional `import fcntl` that blocks collection). Per the executor's scope rules, these were classified and recorded, not fixed: none are caused by this task, and the coverage gate itself passed at 94.23%. The suite was run with `--ignore=tests/unit/cli/test_index_locking.py` to obtain a meaningful result; all 63 failures + 27 errors are in unrelated Windows/POSIX areas.
2. **`pip check` conflict (external drift, recorded not repaired).** `dnallm 0.5.2` requires `mcp<2,>=1.3.0` and `langchain-mcp-adapters 0.3.2` requires `mcp<2.0.0,>=1.24.0`, while SIF declares and the plan authorized `mcp>=2.3.0,<3` (resolved 2.3.0). This is user-environment drift outside SIF's dependency closure.
3. **Windows pytest stale-basetemp workaround.** A stale `C:\Users\forre\AppData\Local\Temp\pytest-of-forre\pytest-current` returns `PermissionError: [WinError 5]` during pytest's numbered-directory cleanup. Every run used an explicit `--basetemp` to bypass it. Host environment defect, not a repo defect.
4. **env-matrix report left unchanged by the final gate.** No previously recorded fact changed: the per-env verdicts, ty status (22 diagnostics), and pytest `--basetemp` workaround all still hold. The new full-suite result is recorded here in the SUMMARY.

## Issues Encountered

- The first full-suite invocation failed at collection (exit 2) on the unguarded `fcntl` import. Re-running with only that module ignored produced the 3148-pass result above.
- The plan's Task 2 targeted gate output (`ty check`) is non-green by design on Windows; the orchestrator pre-verified the identical 22-diagnostic baseline at pristine HEAD.

## User Setup Required

None — no external service configuration. The three conda envs are already provisioned; no model downloads, torch changes, or network setup are needed.

## Next Phase Readiness

- Intel XPU is now a first-class auto-detected backend on hosts whose torch build provides it; standard wheels (which lack XPU) continue to resolve to CPU/MPS/CUDA as before.
- The env matrix is the durable record of Windows conda behavior; the POSIX-only full-suite failures are a host/platform limitation already consistent with the project decision to defer full Windows support, not a blocker introduced here.

## Self-Check

- FOUND: `.planning/quick/261119-bl9-windows-conda-env-verification-for-sif-c/261119-bl9-env-matrix.md`
- FOUND: `.planning/quick/261119-bl9-windows-conda-env-verification-for-sif-c/261119-bl9-SUMMARY.md`
- FOUND: `82df76b` (ancestor of HEAD)
- Scope audit: tracked tree clean at `82df76b`; only `.planning/quick/261119-bl9-.../` untracked; `pyproject.toml`, `uv.lock`, `.github/**`, and `.planning/milestones/**` identical to HEAD.
