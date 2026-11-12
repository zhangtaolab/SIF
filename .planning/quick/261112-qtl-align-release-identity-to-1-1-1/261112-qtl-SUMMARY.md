---
phase: 261112-qtl-align-release-identity-to-1-1-1
plan: 01
subsystem: release-identity
tags: [versioning, hatchling, uv-lock, changelog, documentation, install-hints, regression-test]
requires: []
provides:
  - "Single-sourced release version at 1.1.1 in src/sif/_version.py, re-exported by the package, sif.cli, APP_VERSION, and MCP serverInfo"
  - "Hatch dynamic versioning in pyproject.toml and a refreshed uv.lock entry for docsif"
  - "tests/test_version_identity.py pinning packaging wiring, runtime coherence, literal uniqueness, and CLI --version output"
  - "Corrected docsif distribution name in install/upgrade/uninstall guidance and in-app remedy hints, plus a 1.1.1 changelog entry"
affects: [packaging, cli, mcp, config, docs, examples]
actuals:
  tokens: 3955
  tasks: 2
  commits: 2
  plan_head_before: 2c7efc6b3628c4c43567e264c3156565bbd0ae07
  plan_head_after: 9f366d4c178cf0f30a6b5e3a1bb03eb58e064ba5
tech-stack:
  added: []
  patterns:
    - "Hatch dynamic version source ([tool.hatch.version].path) over a module constant, not importlib.metadata"
    - "Explicit re-export alias (`__version__ as __version__`) for ruff F401-clean package re-exports"
    - "Generator-owned docs: docs/configuration.md is regenerated from scripts/generate_config_ref.py, never hand-edited"
key-files:
  created:
    - tests/test_version_identity.py
  modified:
    - pyproject.toml
    - src/sif/_version.py
    - src/sif/__init__.py
    - src/sif/cli/__init__.py
    - src/sif/config/constants.py
    - src/sif/mcp/protocol.py
    - example_config.yaml
    - uv.lock
    - docs/installation.md
    - docs/changelog.md
    - docs/configuration.md
    - scripts/generate_config_ref.py
    - examples/quickstart.py
    - src/sif/embedding/embedder.py
    - src/sif/cli/commands/mcp.py
    - src/sif/cli/commands/search.py
    - tests/unit/embedding/test_openai_embedder.py
key-decisions:
  - "Use hatch's dynamic version source (path = src/sif/_version.py) rather than runtime importlib.metadata; developer editable installs can carry stale dist-info metadata"
  - "Keep the release literal single-sourced in _version.py; the regression test asserts coherence and semver shape, never a hardcoded 1.1.1"
  - "The package __init__ re-export uses `__version__ as __version__` so ruff F401 passes without changing __all__ (added `noqa` avoided per project no-noqa culture)"
  - "uv.lock drops the docsif editable entry's version line to match hatch dynamic versioning; uv lock --check --offline confirms zero further churn"
  - "docs/configuration.md was regenerated from scripts/generate_config_ref.py, and docs/cli-reference.md verified byte-identical"
metrics:
  duration: 12min
  completed: 2026-11-12
status: complete
---

# Quick Task 261112-qtl: Align Release Identity to 1.1.1 Summary

**The release identity now derives from one literal at 1.1.1 — hatch packages the wheel as docsif-1.1.1 — and every install/upgrade/uninstall instruction and in-app hint names the published `docsif` distribution.**

## Performance

- **Duration:** ~12 min
- **Completed:** 2026-11-12T11:38Z
- **Tasks:** 2
- **Files modified/created:** 18

## Accomplishments

- `src/sif/_version.py` is the only module-level `__version__` literal in `src/`; `sif.__version__`, `sif.cli.__version__`, `APP_VERSION`, and `InitializeResult().serverInfo["version"]` all equal `1.1.1`, and `python -m sif.cli.main --version` prints exactly `sif, version 1.1.1`.
- `pyproject.toml` declares `dynamic = ["version"]` with `[tool.hatch.version] path = "src/sif/_version.py"`; `uv build --wheel` produced `/tmp/sif-version-check/docsif-1.1.1-py3-none-any.whl`.
- `uv.lock` dropped the stale static version line on the editable `docsif` entry; `uv lock --check --offline` exits 0 with no dependency churn.
- New `tests/test_version_identity.py` (4 tests) pins: pyproject dynamic wiring (with a Python 3.10 `tomllib`-free text fallback), runtime surface coherence + semver shape, literal uniqueness across `src/sif/**/*.py` (no other `__version__ = "<literal>"`, no `APP_VERSION = "<literal>"`), and the CLI `--version` output.
- `docs/installation.md` now uses `docsif` for the Homebrew block, force-reinstall, and uninstall, and its expected `sif --version` output matches 1.1.1 exactly.
- `docs/changelog.md` gained exactly one `## [1.1.1] - 2026-11-12` section (Changed + Fixed) between Unreleased and 1.0.1, the upgrade command now names `docsif`, the new `[1.1.1]` reference link sits above `[1.0.1]`, and the `[Unreleased]` compare link targets `v1.1.1`.
- Distribution-name fixes: generator source (then regenerated `docs/configuration.md`), `examples/quickstart.py` (3 places), OpenAI ImportError hint, both MCP dependency ClickException hints, and the search reranker hint (previously a source-checkout-only `pip install -e '.[embed]'`).
- `tests/unit/embedding/test_openai_embedder.py` now requires the full `docsif[openai]` fragment.
- Regression sweeps: no bare `sif[...]` extras form remains (negative lookbehind for `doc`), and no pip install/uninstall/upgrade command in the touched docs names a bare `sif`.

## Task Commits

Each task was committed atomically:

1. **Task 1: Single-source the version at 1.1.1 and add a regression test** - `b7c3f77` (chore)
2. **Task 2: Correct install/upgrade/uninstall guidance and add the 1.1.1 changelog entry** - `9f366d4` (docs)

**Plan metadata:** none — SUMMARY/PLAN artifacts are committed by the batch orchestrator, not by this executor.

## Files Created/Modified

- `src/sif/_version.py` — the single version literal, now `1.1.1`.
- `pyproject.toml` — `dynamic = ["version"]` plus `[tool.hatch.version]` pointing at the module.
- `src/sif/__init__.py` — re-exports `__version__`; `__author__`/`__description__`/`__all__` otherwise unchanged.
- `src/sif/cli/__init__.py` — re-exports `__version__` after the docstring.
- `src/sif/config/constants.py` — `APP_VERSION = __version__`.
- `src/sif/mcp/protocol.py` — `serverInfo` default uses `__version__`; name/protocolVersion unchanged.
- `example_config.yaml` — MCP version default and value updated to 1.1.1.
- `uv.lock` — removed the `docsif` editable entry's static `version` line.
- `tests/test_version_identity.py` — new packaging/runtime/uniqueness/CLI regression test module.
- `docs/installation.md` — `docsif` install/force-reinstall/uninstall; 1.1.1 expected output.
- `docs/changelog.md` — 1.1.1 section, docsif upgrade command, reference links.
- `docs/configuration.md` — regenerated only (single `docsif[embed]` line).
- `scripts/generate_config_ref.py` — generator source now emits `docsif[embed]`.
- `examples/quickstart.py` — all three install instructions use `docsif`.
- `src/sif/embedding/embedder.py`, `src/sif/cli/commands/mcp.py`, `src/sif/cli/commands/search.py` — in-app remedy hints name `docsif` extras.
- `tests/unit/embedding/test_openai_embedder.py` — asserts the full `docsif[openai]` fragment.

## Decisions Made

- Hatch dynamic versioning reads a module constant at build time; no runtime metadata lookup, which can be stale in an editable developer install.
- The regression test intentionally does not hardcode `1.1.1`: the concrete value stays asserted by the task verify gate, keeping the release literal single-sourced.
- `scripts/generate_config_ref.py` is the only source edited for `docs/configuration.md`; `docs/cli-reference.md` was proven byte-identical after regeneration.
- The reranker hint moved from an editable-checkout command to a published extras command (`pip install "docsif[embed]"`), which is correct for installed users and still actionable from a source checkout with uv/pip extras.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Ruff F401 on the package re-export**
- **Found during:** Task 1 (lint gate)
- **Issue:** `from sif._version import __version__` in `src/sif/__init__.py` is flagged `F401 ... imported but unused` because `__version__` is not in the existing `__all__`, which the plan required to stay byte-identical.
- **Fix:** Used the explicit re-export idiom `from sif._version import __version__ as __version__`, the minimal lint-clean form. Runtime semantics are identical (`sif.__version__` resolves to `1.1.1`); `__all__` untouched.
- **Files modified:** `src/sif/__init__.py`
- **Commit:** `b7c3f77`

## Issues Encountered

None. `ruff format` line wrapping was already compliant; `docs/configuration.md` regeneration produced exactly the one expected line change and no `docs/cli-reference.md` diff.

## User Setup Required

None - no external service configuration required. No package installs or dependency changes were performed (T-qtl-SC held: the only lock edit removes the project's own editable version line).

## Threat Flags

None - no new security-relevant surface. T-qtl-02 is mitigated by the new test asserting the hatch version path and dynamic declaration; T-qtl-03 is mitigated by the corrected distribution name plus the negative extras/install sweeps. T-qtl-01 remains accepted (public release number in MCP serverInfo).

## Next Phase Readiness

Releases now need a one-line edit in `src/sif/_version.py`; the new test fails if any surface re-fragments or a literal reappears. Remaining manual step outside this task: build/publish the `docsif-1.1.1` wheel and tag `v1.1.1` (not performed here — no publish commands were in scope).

---

## Self-Check: PASSED

- All 18 planned artifacts exist, including the new `tests/test_version_identity.py`.
- Commit `b7c3f77` and `9f366d4` are ancestors of HEAD.
- Commits measured from base `2c7efc6`: 2 (`git rev-list --count 2c7efc6..HEAD`).
- Task 1 gates: five runtime surfaces at 1.1.1; CLI prints `sif, version 1.1.1`; `uv lock --check --offline` exit 0; `uv build` produced `docsif-1.1.1-py3-none-any.whl`; only `_version.py` carries a `__version__` literal.
- Task 2 gates: generator leaves `docs/cli-reference.md` untouched; changelog count/positive/negative sweeps pass; targeted tests 198 passed.
- Full suite: `env -u FORCE_COLOR NO_COLOR=1 python -m pytest -q` -> **1599 passed, 1 skipped**, coverage **95.19%**; `ruff check src tests` and `ruff format --check src tests` clean.
- Scope check: `git diff --stat 2c7efc6..HEAD` shows exactly the 18 files in the plan and no deletions.
