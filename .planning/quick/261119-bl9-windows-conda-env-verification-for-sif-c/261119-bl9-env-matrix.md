# Windows Conda Environment Verification Matrix (quick-261119-bl9)

Machine-facts report for SIF on Windows across `dnallm-cpu`, `dnallm-cuda`, and
`dnallm-xpu`, including the post-change Intel XPU auto-selection verification.

## Run metadata

- Date: 2026-11-19
- Baseline HEAD at Task 1: `25bf8c32ff186f0794fd08b8738bc4734a10dc20` (short `25bf8c3`)
- Post-change HEAD at Task 3: `82df76b` (Task 2 XPU commit)
- Host: Windows 11 Home China, OS version 10.0.26300
- Interpreters:
  - `D:/miniconda3/envs/dnallm-cpu/python.exe`
  - `D:/miniconda3/envs/dnallm-cuda/python.exe`
  - `D:/miniconda3/envs/dnallm-xpu/python.exe`
- All three interpreters: Python 3.13.15 (Anaconda build, MSC v.1942 64-bit)
- The tree is dirty at report time: the Task 2 source/docs edits are committed at
  `82df76b`, and this report plus the plan/SUMMARY artifacts are uncommitted
  under `.planning/`. `scripts/windows_smoke.py` was therefore not re-run after
  Task 2 (it refuses a dirty tree); the Task 1 8/8 result on clean HEAD
  `25bf8c3` stands.

## Per-environment matrix

| Fact | dnallm-cpu | dnallm-cuda | dnallm-xpu |
|------|------------|-------------|------------|
| Python | 3.13.15 | 3.13.15 | 3.13.15 |
| SIF (`docsif`) | 1.2.1 (editable) | 1.2.1 (editable) | 1.2.1 (editable) |
| torch build | 2.11.0+cpu | 2.11.0+cu130 | 2.11.0+xpu |
| `torch.version.cuda` | None | 13.0 | None |
| CUDA available / device count | False / 0 | True / 1 | False / 0 |
| XPU available / device count | False / 0 | False / 0 | True / 1 |
| Resolved auto device (post-change) | `cpu` | `cuda` | `xpu` |
| Tensor op on resolved device | `torch.zeros(8, device='cpu')` sum 0.0 | `torch.zeros(8, device='cuda')` sum 0.0 | `torch.zeros(8, device='xpu')` sum 0.0 |
| `pip check` | FAIL (2 conflicts, see findings) | FAIL (2 conflicts, see findings) | FAIL (2 conflicts, see findings) |
| sqlite-vec version | v0.1.9 | v0.1.9 | v0.1.9 |
| `python -m sif.cli.main --version` | `sif, version 1.2.1` | `sif, version 1.2.1` | `sif, version 1.2.1` |
| Windows smoke (`scripts/windows_smoke.py`) | 8/8 PASS (HEAD 25bf8c3) | 8/8 PASS (HEAD 25bf8c3) | 8/8 PASS (HEAD 25bf8c3) |
| Scoped pytest, Task 1 (before XPU tests) | 260 passed | 260 passed | 260 passed |
| Scoped pytest, Task 3 (after XPU tests) | 269 passed | 269 passed | 269 passed |
| Offline embed smoke (construct) | model.device `cpu`, dim 768 | model.device `cuda:0`, dim 768 | model.device `xpu:0`, dim 768 |
| Offline embed smoke (encode) | failed `ValueError` (env/model drift) | failed `ValueError` (env/model drift) | failed `ValueError` (env/model drift) |
| Verdict | PASS-WITH-FINDINGS | PASS-WITH-FINDINGS | PASS-WITH-FINDINGS |

Scoped pytest file set (identical for every env):

```
tests/unit/search/test_bm25.py
tests/unit/search/test_vector.py
tests/unit/search/test_hybrid.py
tests/unit/embedding/test_embedder_impl.py
tests/unit/embedding/test_factory.py
tests/integration/test_search_correctness.py
tests/test_windows_smoke_script.py
```

All scoped runs used `--no-cov` (the repo `addopts` force `fail_under=90`, which
a scoped run structurally cannot satisfy — WINDOWS.md ledger item 8). An
explicit `--basetemp` was added to every pytest invocation because a stale
`%TEMP%\pytest-of-forre\pytest-current` directory returns `WinError 5`
(Access denied) during pytest's numbered-dir cleanup (see findings).

## Exact commands

Every command below was run from the repository root with the env-specific
interpreter. `<env>` is one of `cpu`, `cuda`, `xpu`.

### Provisioning (identical for all three envs)

```bash
# a. editable install, no dependency resolution
D:/miniconda3/envs/dnallm-<env>/python.exe -m pip install -e . --no-deps

# b. dry-run of the declared install set (checked before installing)
D:/miniconda3/envs/dnallm-<env>/python.exe -m pip install --dry-run "sqlite-vec>=0.1.9" "rapidfuzz>=3.14.5,<4" "python-frontmatter>=1.0.0" "fastapi>=0.100.0" "watchdog>=4.0.0,<7.0.0" "mcp>=2.3.0,<3" "modelscope>=1.36.0" "sentence-transformers==5.4.1" "ty>=0.0.1"

# c. the same install without --dry-run
D:/miniconda3/envs/dnallm-<env>/python.exe -m pip install "sqlite-vec>=0.1.9" "rapidfuzz>=3.14.5,<4" "python-frontmatter>=1.0.0" "fastapi>=0.100.0" "watchdog>=4.0.0,<7.0.0" "mcp>=2.3.0,<3" "modelscope>=1.36.0" "sentence-transformers==5.4.1" "ty>=0.0.1"

# d. post-install verification
D:/miniconda3/envs/dnallm-<env>/python.exe -m pip check
D:/miniconda3/envs/dnallm-<env>/python.exe -c "import torch; print(torch.__version__, torch.version.cuda, torch.cuda.is_available(), torch.cuda.device_count(), torch.xpu.is_available(), torch.xpu.device_count())"
```

### Import and extension smoke (identical for all three envs)

```bash
D:/miniconda3/envs/dnallm-<env>/python.exe -c "import click, rich, frontmatter, sqlite_vec, platformdirs, pydantic, pydantic_settings; import fastapi, uvicorn, watchdog, numpy, rapidfuzz, mcp; import pytest, pytest_cov, pytest_asyncio, ruff, ty; import sentence_transformers, torch, modelscope; import sqlite3; c = sqlite3.connect(':memory:'); c.enable_load_extension(True); sqlite_vec.load(c); print(c.execute('select vec_version()').fetchone()[0])"
D:/miniconda3/envs/dnallm-<env>/python.exe -m sif.cli.main --version
```

### Windows smoke (clean HEAD only)

```bash
PYTHONUTF8=1 D:/miniconda3/envs/dnallm-<env>/python.exe scripts/windows_smoke.py
```

The untracked plan directory prevented the script's clean-tree precondition, so
it was temporarily moved outside the repository, the smoke was run against the
otherwise-clean `25bf8c3` tree, and the directory was restored byte-identically.

### Scoped tests (Task 1 and Task 3)

```bash
PYTHONUTF8=1 D:/miniconda3/envs/dnallm-<env>/python.exe -m pytest tests/unit/search/test_bm25.py tests/unit/search/test_vector.py tests/unit/search/test_hybrid.py tests/unit/embedding/test_embedder_impl.py tests/unit/embedding/test_factory.py tests/integration/test_search_correctness.py tests/test_windows_smoke_script.py -q --no-cov --basetemp="C:/Users/forre/AppData/Local/Temp/gsd-bl9-<env>"
```

### Post-change device probe and offline embed smoke (Task 3)

```bash
# import path proof
D:/miniconda3/envs/dnallm-<env>/python.exe -c "import sif.embedding.embedder as m; print(m.__file__)"

# device probe
D:/miniconda3/envs/dnallm-<env>/python.exe -c "import torch; from sif.embedding.embedder import _auto_device; d = _auto_device(torch); t = torch.zeros(8, device=d); print(d, float(t.sum()))"

# diagnostic offline embed smoke (non-gating)
HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 PYTHONUTF8=1 D:/miniconda3/envs/dnallm-<env>/python.exe -c "from sif.embedding.embedder import SentenceTransformerEmbedder; e = SentenceTransformerEmbedder(model_name='microsoft/DialoGPT-small'); v = e.embed('device smoke'); print(str(e.model.device), len(v))"
```

## Package deltas

The same eleven packages were added or upgraded in all three envs, matching the
dry-run exactly (no torch / torchvision / torchaudio / transformers / numpy
change):

```
fastapi-0.165.0          mcp-2.3.0              mcp-types-2.3.0
modelscope-1.40.3        modelscope-hub-0.7.1   python-frontmatter-1.3.0
rapidfuzz-3.14.6         sentence-transformers-5.4.1  sqlite-vec-0.1.9
ty-0.0.107               watchdog-6.0.0
```

Plus the editable install `docsif-1.2.1` (`--no-deps`).

Baseline package state before provisioning (filtered):

| Package | cpu | cuda | xpu |
|---------|-----|------|-----|
| torch | 2.11.0+cpu | 2.11.0+cu130 | 2.11.0+xpu |
| transformers | 5.18.0 | 5.18.0 | 5.18.0 |
| numpy | 2.5.3 | 2.5.3 | 2.5.3 |
| modelscope | 1.34.0 | 1.34.0 | 1.34.0 |
| mcp | 1.30.0 | 1.30.0 | 1.30.0 |
| pytest | 9.1.1 | 9.1.1 | 9.1.1 |
| pytest-cov | 7.1.0 | 7.1.0 | 7.1.0 |
| pytest-asyncio | 1.4.0 | 1.4.0 | 1.4.0 |
| ruff | 0.16.9 | 0.16.10 | 0.16.9 |

`sif` was absent (`ModuleNotFoundError`) in all three envs before the editable
install. `pip check` reported "No broken requirements found." in all three
before provisioning.

## Findings

1. **torch 2.11.0 is below the declared `>=2.14` embed floor in all three envs.**
   The vendor builds (`+cpu`, `+cu130`, `+xpu`) are the env's stack and were
   deliberately preserved; the plan forbids upgrading or replacing them. This is
   recorded drift, not a failure.
2. **`pip check` fails in all three envs after the authorized `mcp` upgrade.**
   Exact output, identical in cpu, cuda, and xpu:
   ```
   dnallm 0.5.2 has requirement mcp<2,>=1.3.0, but you have mcp 2.3.0.
   langchain-mcp-adapters 0.3.2 has requirement mcp<2.0.0,>=1.24.0, but you have mcp 2.3.0.
   ```
   Root cause: two pre-existing third-party packages in the user's conda envs
   pin `mcp<2`, while the plan authorizes and requires the `mcp` 1.30.0 -> 2.3.0
   upgrade (matching `uv.lock` and the Phase 22 legitimacy approval). SIF's own
   imports and declared closure are intact; no SIF package conflicts. Per the
   plan this was reported, not repaired. Under the plan taxonomy a `pip check`
   failure after the allowed installs is `FAIL(missing-dependency)`; the conflict
   is external to SIF and affects no SIF gate.
3. **`modelscope` 1.34.0 -> 1.40.3** (declared floor `>=1.36.0`), as planned.
4. **`transformers` 5.18.0 differs from `uv.lock` 5.5.4.** The env's transformers
   was pre-existing and is not part of the installed set; it was left untouched.
5. **`mcp` 1.30.0 -> 2.3.0** (declared `>=2.3.0,<3`), as planned.
6. **`sentence-transformers` installed at the locked 5.4.1**, as planned.
7. **`ty check src/sif` is non-green on this Windows host, independent of this
   change.** It reports 22 diagnostics at `82df76b` and exactly the same 22 with
   the same per-file distribution when run against a pristine `git archive` of
   HEAD `25bf8c3` with the same interpreter: POSIX-only members (`fcntl`,
   `os.getuid`, `os.killpg`, `signal.SIGKILL`) plus third-party
   `sentence-transformers`/`transformers` typing (deprecated
   `get_sentence_embedding_dimension`, `int | None` dimension). The new
   `_auto_device` helper adds zero diagnostics. Not repaired (out of scope).
8. **pytest temp-directory environment fault.** A stale
   `C:\Users\forre\AppData\Local\Temp\pytest-of-forre\pytest-current` directory
   returns `PermissionError: [WinError 5]` during pytest's numbered-directory
   cleanup, aborting every pytest run regardless of env or code. It could not be
   removed from this session; every pytest invocation therefore passes an
   explicit `--basetemp` pointing at a fresh directory, which bypasses the
   numbered-dir/symlink logic. This is a host environment defect, not a repo
   defect.
9. **Offline embed smoke: model loads on the resolved device, encode fails.**
   `SentenceTransformerEmbedder(model_name='microsoft/DialoGPT-small')`
   constructed successfully from the cached snapshot in all three envs and
   reported `model.device` `cpu`, `cuda:0`, and `xpu:0` respectively (dim 768),
   proving the new device detection reaches the real backend. The subsequent
   `embed()` call raises `ValueError: Asking to pad but the tokenizer does not
   have a padding token` from
   `transformers.tokenization_utils_base._get_padding_truncation_strategies`
   while sentence-transformers applies a chat template. DialoGPT-small is a
   causal LM, not an embedding model, and lacks a pad token — model choice drift,
   classified `PASS-WITH-FINDINGS` per the plan (no frame *originates* in
   `src/sif/embedding/embedder.py`; the failure is inside the tokenizer
   pre-processing).

## Verdict definitions and per-env verdicts

- `PASS` — all gates pass; the diagnostic embed smoke passes or is not-run.
- `PASS-WITH-FINDINGS` — gates pass but a recorded drift remains (torch version
  floor, third-party `mcp` pins, diagnostic embed smoke drift).
- `FAIL(missing-dependency)` — a declared import or `pip check` fails after the
  allowed installs.
- `FAIL(build-mismatch)` — a torch-family package changes.
- `FAIL(extension)` — sqlite-vec import or load fails.
- `FAIL(test)` — the scoped pytest run exits non-zero.
- `BLOCKED(network)` — PyPI is unreachable, so provisioning cannot complete.

| Env | Verdict | Reason |
|-----|---------|--------|
| dnallm-cpu | PASS-WITH-FINDINGS | Imports, sqlite-vec v0.1.9, CLI 1.2.1, smoke 8/8, scoped pytest 269 passed, torch `2.11.0+cpu` preserved, `_auto_device` -> `cpu`. Drift: torch below the `>=2.14` floor; `pip check` conflict from pre-existing `dnallm`/`langchain-mcp-adapters` `mcp<2` pins; offline encode drift on DialoGPT-small. |
| dnallm-cuda | PASS-WITH-FINDINGS | Imports, sqlite-vec v0.1.9, CLI 1.2.1, smoke 8/8, scoped pytest 269 passed, torch `2.11.0+cu130` preserved (CUDA 13.0, 1 device), `_auto_device` -> `cuda`. Same three drift records. |
| dnallm-xpu | PASS-WITH-FINDINGS | Imports, sqlite-vec v0.1.9, CLI 1.2.1, smoke 8/8, scoped pytest 269 passed, torch `2.11.0+xpu` preserved (XPU 1 device), `_auto_device` -> `xpu` with a successful tensor op. Same three drift records. |

No env is `FAIL(build-mismatch)`: every torch build string is byte-identical to
its baseline after provisioning. No env is `FAIL(extension)`: sqlite-vec loaded
and reported v0.1.9 in all three. No env is `FAIL(test)`: the scoped subset
exited 0 in all three. The only non-zero gate is `pip check`, caused by
third-party packages external to SIF and the plan-authorized `mcp` upgrade.
