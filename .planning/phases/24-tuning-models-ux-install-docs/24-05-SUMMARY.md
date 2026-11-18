---
phase: 24-tuning-models-ux-install-docs
plan: 05
subsystem: docs
tags: [install-docs, uv-first, torch-cpu, llama-cpp, degradation-matrix, model-management, docs-generate, deprecation]
requires:
  - "Plan 24-02: embed_breadcrumb Settings field"
  - "Plan 24-03: canonical manifest-verified model cache and DEFAULT_MODELS"
  - "Plan 24-04: sif models pull/status and hidden sif pull alias"
provides:
  - "README.md uv-first install block with the verified Linux CPU recipe"
  - "docs/installation.md: uv-first methods, llama-cpp indexes, degradation matrix, client snippets"
  - "docs/quickstart.md and docs/index.md uv-first install sections"
  - "docs/models.md ## Model Management (pull/status, cache states, manifest, legacy migration)"
  - "docs/migration.md canonical model cache path and SIF_CACHE_DIR note"
  - "tests/test_docs.py and tests/test_ci_workflows.py DOCS-01 guards"
  - "docs/configuration.md regenerated with the env-var to Settings-field mapping"
affects:
  - "docs/installation.md is the canonical install entry point for users and clients"
  - "docs/models.md is the canonical model-management reference"
tech-stack:
  added: []
  patterns:
    - "Generator-owned docs: make docs-generate is the only path; never hand-edited"
    - "Text-level docs guards over hand-maintained Markdown"
    - "uv-first install ordering: uv tool, uvx, pip"
key-files:
  created: []
  modified:
    - README.md
    - docs/installation.md
    - docs/quickstart.md
    - docs/index.md
    - docs/models.md
    - docs/migration.md
    - docs/configuration.md
    - scripts/generate_config_ref.py
    - tests/test_docs.py
    - tests/test_ci_workflows.py
decisions:
  - "The Linux CPU recipe is documented as the explicit `uv tool install --torch-backend=cpu` command with a uv 0.9.19 floor; the pyproject CPU-index claim for tool installs is deleted."
  - "llama-cpp wheel indexes, the multi-index --index-strategy recipe, the source-build fallback, and the Python 3.12 all-extra path are documented as manually verified, not CI-proven."
  - "The degradation matrix states base BM25-only, CLI fail-fast versus MCP BM25 degradation for missing sqlite-vec, unavailable GGUF/OpenAI backends, and Windows daemon/service refusal."
  - "Client configuration keeps one minimal Desktop stdio snippet, one Claude Code HTTP snippet, and a plugin pointer, linking docs/mcp-server.md for detail."
  - "The config generator now states the env-var to lowercase Settings-field mapping so regenerated docs contain `embed_breadcrumb` explicitly."
metrics:
  duration: "~20 min"
  completed: "2026-11-17"
  tasks: 3
  files: 10
status: complete
actuals:
  tokens: 9076
  tasks: 3
  commits: 3
commits: 3
plan_head_before: 46b3269e9e326efc6c48500cb7bf72bf2f6ab2cf
plan_head_after: d8d286b
requirements-completed: [DOCS-01]
---

# Phase 24 Plan 05: uv-first Install Docs and Model Management Summary

Every install entry point now leads with `uv tool install`, the Linux CPU
torch recipe is explicit, degradation and client configuration are honest, and
model management has a documented home guarded by docs tests.

## Performance

- **Duration:** ~20 min
- **Tasks:** 3
- **Files modified:** 10

## Accomplishments

- **README.** The Installation section leads with `uv tool install
  'docsif[embed]'`, the Linux CPU recipe `uv tool install
  --torch-backend=cpu 'docsif[embed]'` (uv 0.9.19 or newer), the BM25-only
  base, and a `uvx --from 'docsif[embed]' sif --help` one-off. The false claim
  that a published tool install resolves CPU torch from `pyproject.toml` is
  gone; pip keeps the truthful two-step CPU-index alternative. Quick Start and
  the model-download example now use the current commands.
- **docs/installation.md** was restructured to the ordered methods uv tool,
  uvx, pip, source, pipx. It carries the truthful extras table, the llama-cpp
  official wheel indexes (CPU/CUDA/Metal), the multi-index recipe with its
  human-verification marker, the CMake source-build fallbacks, the Python 3.12
  safe path for `all`, the four-row degradation matrix, client configuration
  snippets for Claude Desktop stdio and Claude Code HTTP plus the plugin
  pointer, and updated platform and troubleshooting sections.
- **docs/models.md** gained `## Model Management` before Related
  Documentation: `sif models pull` targets and flags, the no-ST-prewarm limit,
  `sif models status [--json]` payload sections, all five cache states, the
  canonical `<cache>/models/<owner>/<name>` layout and `.sif-model.json`
  SHA-256 manifest, local-content determinism versus a moving upstream
  `master`, automatic legacy-layout migration, and the deprecated hidden
  `sif pull` alias.
- **docs/migration.md** records the canonical cache path, the `SIF_CACHE_DIR`
  override, automatic legacy migration, and that existing indexes are
  unaffected by the cache move.
- **Docs guard tests.** `DOCS_FILES` now includes installation and migration;
  the new tests pin uv-first ordering, the CPU recipe, the degradation rows,
  Model Management, the retired 7B default's absence, and the deprecated
  alias. `tests/test_ci_workflows.py` adds text-level uv-first, CPU-recipe,
  degradation-matrix, and no-pyproject-index-claim guards.
- **Generator gate.** `make docs-generate` is diff-clean; the regenerated
  `docs/configuration.md` contains `SIF_EMBED_BREADCRUMB` and the explicit
  field-name mapping.

## Task Commits

1. **Task 1: uv-first install path, CPU recipe, degradation matrix** — `76c4ed7` (docs)
2. **Task 2: Model Management section and cache migration notes** — `0ef2b80` (docs)
3. **Task 3: docs guards, generator mapping, regenerated configuration** — `d8d286b` (test)

## Decisions Made

- Install methods are ordered uv tool, uvx, pip, then source and pipx; the
  ordering is asserted by tests in both docs test modules.
- `--torch-backend=cpu` is presented as the verified Linux CPU path with the
  uv 0.9.19 floor; the pip alternative installs torch from the CPU index first.
- The llama-cpp multi-index recipe is marked manually verified (not CI-proven),
  matching RESEARCH A2, with a source-build fallback and a Python 3.12 note.
- The degradation matrix keeps the MCP `hybrid_search` BM25 carve-out distinct
  from the core `HybridSearcher.search()` fail-fast contract.
- The config generator emits the generic env-var-to-Settings-field mapping
  sentence; this is generator-owned prose, never a hand edit of
  `docs/configuration.md`.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Generated configuration doc lacked the lowercase field name**
- **Found during:** Task 3 generator gate
- **Issue:** `docs/configuration.md` renders `SIF_EMBED_BREADCRUMB`, but the
  plan's verify asserts the literal `embed_breadcrumb` is present. The field
  was already registered in the generator's `SECTIONS`, so this was a
  rendering-spelling mismatch, not a missing surface.
- **Fix:** Added one generator-owned sentence stating that each variable maps
  to a lowercase Settings field (with `chunk_size` and `embed_breadcrumb` as
  examples), then regenerated the doc. No hand edit touched
  `docs/configuration.md`.
- **Files modified:** `scripts/generate_config_ref.py`, `docs/configuration.md`
- **Commit:** `d8d286b`

**2. [Rule 1 - Test] Bare `sif search` false positive in a matrix table cell**
- **Found during:** Task 3 test run
- **Issue:** The new degradation table wrote `sif search search` in backticks;
  the docs guard requires whitespace after the subcommand, so the cell was
  flagged as a bare `sif search <query>`.
- **Fix:** Wrote the cells as `sif search search <query>` (and the `vsearch` /
  `query` equivalents), which is also clearer for readers.
- **Files modified:** `docs/installation.md`
- **Commit:** `d8d286b`

## Issues Encountered

The only two failures were the generated-field spelling and the bare-search
guard; both were fixed and re-verified before the Task 3 commit.

## User Setup Required

None.

## Next Phase Readiness

- DOCS-01 is closed: every entry-point install doc is uv-first, degradation and
  client configuration are documented truthfully, and the generator gate is
  clean.
- Model management has a documented home ready for the Phase 24-06 references.
- No blockers.

## Verification

- `env -u FORCE_COLOR NO_COLOR=1 pytest tests/test_docs.py tests/test_ci_workflows.py -q --no-cov`
  — 38 passed.
- `make docs-generate && git diff --exit-code docs/cli-reference.md docs/configuration.md`
  — clean; `sif models pull`, `sif models status`, and `embed_breadcrumb`
  present; the retired `iic/gte_Qwen2-7B-instruct` absent from both.
- `ruff check src tests`, `ruff format --check src tests`, `ty check src/sif`
  — green.
- Full suite: **3225 passed, 1 skipped, 95.03% coverage**.

## Known Stubs

None.

## Threat Flags

None beyond the plan's threat model. T-24-09 is mitigated by documenting only
repository-supported commands and marking the unproven recipes as manually
verified; T-24-10 by regenerating generator-owned docs and running the diff
gate; T-24-SC by installing no package.

## Self-Check: PASSED

- `README.md`, `docs/installation.md`, `docs/quickstart.md`, `docs/index.md`,
  `docs/models.md`, `docs/migration.md`, and `docs/configuration.md` exist.
- Commits `76c4ed7`, `0ef2b80`, `d8d286b` are ancestors of HEAD.
