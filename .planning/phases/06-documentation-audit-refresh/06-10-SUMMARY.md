---
phase: 06-documentation-audit-refresh
plan: 10
subsystem: docs
tags: [architecture, mermaid, gap-closure, G-06-5, D-10]
requires:
  - "06-08/06-09 committed reference-doc and generator repairs (different files; no overlap)"
provides:
  - "generate_arch_diagram.py whose output IS the computed import graph (D-10 honored for real)"
  - "architecture.md module tree existence-checked against the live src/sif tree"
affects:
  - scripts/generate_arch_diagram.py
  - docs/architecture.md
tech-stack:
  added: []
  patterns:
    - "derived-not-hardcoded diagram emission (nodes/edges from pkg_deps, sorted for determinism)"
key-files:
  created: []
  modified:
    - scripts/generate_arch_diagram.py
    - docs/architecture.md
decisions:
  - "Package keys normalized to the top-level package under sif on both sides of build_dependency_graph so intra-package imports filter and keys match import targets"
  - "database/repository.py described as abstract repository interfaces (nothing imports it; live indexer imports repositories.py plural)"
  - "Multi-language Support dropped from Future Enhancements — CJK-aware term matching shipped in phase 04; plan's keep list (watcher wiring, plugin system, web UI, query suggestions) is exhaustive"
metrics:
  duration: 9min
  completed: "2026-09-15"
  tasks: 2
  commits: 2
status: complete
gap_closure: G-06-5
actuals:
  tokens: 3323   # chars/4 over the realized diff (13,294 chars); estimate was 28,000
  tasks: 2
  commits: 2     # MEASURED: git rev-list --count 259b6e8..HEAD
plan_head_before: 259b6e80de3da91712db5b97127da08b014d5994
---

# Phase 06 Plan 10: Architecture Diagram Truthfulness Summary

One-liner: generate_arch_diagram.py now emits the package dependency graph it computes (sorted, deterministic, no hardcoded edges) and architecture.md's tree/flows/factory/future lists match the live post-phase-09 tree, with the Mermaid block byte-identical to a fresh script run.

## What Was Done

### Task 1: generate_arch_diagram.py emits its computed graph (cd58c73)

- `generate_mermaid()` rewritten: one node per package present in the computed `pkg_deps` (sources ∪ targets, sorted), edges emitted only from `pkg_deps` with sorted source/destination order; the hardcoded `edge_defs` list and the `mcp_server` label entry are deleted; the `mcp` label reads as the unified server with no legacy/refactored qualifiers; unknown packages fall back to the bare package name.
- Deterministic: two consecutive runs diff clean.
- Live computed graph corrects the stale hardcoded one on content, not just labels — e.g. the old list had `config --> utils` while real imports give `utils --> config`, and `mcp --> search`/`mcp --> embedding` now appear because the unified backend actually uses them.

### Task 2: architecture.md rewritten against the live tree (5742622)

- Module Structure tree rebuilt from `find src/sif -name '*.py' | sort`: unified `mcp/` package (server, backend, handlers, protocol, cli, transports/stdio+http), real embedding set (manager, factory, model, embedder, cache), added indexing/watcher.py, search/context_attach.py, search/term_match.py, utils/progress.py, utils/text.py, cli/config.py, models/download.py, and the full cli command module set with get.py described as the get group; every listed `.py` existence-checks under src/sif (verified programmatically).
- Factory Supported Models list: GGUF, Sentence Transformers, OpenAI-compatible API, ModelScope — the unimplemented hub backend is gone from the entire file (case-insensitive grep = 0).
- Indexing flow step 1 uses the live phase-05 argument order: `sif collection add ~/notes --name my-collection`.
- Mermaid block replaced with the exact script output (byte-identical diff against a fresh run); the "generated from actual source imports" note below it is now true.
- Future Enhancements holds only unshipped items: watcher wiring (annotated that watcher.py exists but is connected to no CLI/MCP surface), plugin system, web UI, query suggestions.

## Verification Results

1. Task 1 gate: two runs diff clean; `grep -c mcp_server` on output = 0; `graph TD` present; `ruff check` + `ruff format --check` on the script pass.
2. Task 2 gate: all six negative greps = 0 (deleted package name, phantom legacy filenames, hub backend case-insensitive, old argument order, both implemented-in-future phrases); positive greps hit (watcher/term_match/context_attach lines = 4; live arg-order line = 1); `/tmp/doc.mmd` vs fresh `/tmp/gen.mmd` diff clean; Module Structure `.py` existence check reports nothing missing.
3. `env -u FORCE_COLOR NO_COLOR=1 python -m pytest tests/test_docs.py -v` → 13 passed.
4. Full quality suite per CLAUDE.md: `ruff check src tests` clean, `ruff format --check src tests` clean, `env -u FORCE_COLOR NO_COLOR=1 python -m pytest` → 676 passed / 0 failed (baseline held; docs/script-only change).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] build_dependency_graph package keys were inconsistent with import targets**
- **Found during:** Task 1
- **Issue:** Source packages were keyed with the `sif.` prefix (`mod.split("/")[0]` → `"sif.cli"`) while import targets were unprefixed (`imp.split(".")[1]` → `"cli"`). Emitting the computed graph as-is would have produced nonsense edges (`sif.cli --> cli`) and the `imp_pkg != src_pkg` guard could never filter intra-package imports. The hardcoded output had been masking this.
- **Fix:** Added `package_of_module()` and normalized the source key to the top-level package under sif (`"sif.mcp/transports/http"` → `"mcp"`), matching how import targets are derived. `extract_imports` and `scan_modules` untouched in semantics, as the plan required.
- **Files modified:** scripts/generate_arch_diagram.py
- **Commit:** cd58c73

**2. [Rule 3 - Blocking] Script failed the plan's own ruff gate with 19 pre-existing violations**
- **Found during:** Task 1 verification
- **Issue:** `ruff check scripts/generate_arch_diagram.py` (mandated by the plan's verify) failed on the committed file — the project ruff ruleset was expanded after the script was written and `ruff check src tests` never covered `scripts/` (verified: `git show HEAD:scripts/...` fails identically).
- **Fix:** Brought the script to the project ruleset: builtin generics instead of `typing.Dict/List/Set`, `list.extend` generators instead of append-loops (PERF401), `maxsplit` on splits (PLC0207), `# noqa: T201` on the CLI print matching the sibling generator scripts' convention. `extract_imports` behavior unchanged — the ast.Import branch is a behavior-identical reformat.
- **Files modified:** scripts/generate_arch_diagram.py
- **Commit:** cd58c73

### Documented Plan-Text Deviations (no code impact)

**3. repository.py described as "Abstract repository interfaces", not "kept for indexer compatibility"**
- The plan's action bullet suggested the latter wording, but live `indexing/indexer.py` imports from `database/repositories` (plural) and nothing under src/tests/scripts imports `repository.py`; its own docstring is "Repository interface definitions". The plan's binding instruction was "describe it accurately", so the tree comment states what it is.

**4. "Multi-language Support" dropped from Future Enhancements beyond the two items the plan named**
- The plan's keep list is exhaustive (watcher, plugin system, web UI, query suggestions) and CJK-aware term matching shipped with phase 04 UAT (term_match.py), so retaining the item would violate the plan's own "only unshipped items" truth.

## Auth Gates

None.

## Known Stubs

None — no placeholder content introduced; both artifacts are fully wired.

## TDD Gate Compliance

Not applicable: no task carried `tdd="true"` and the plan frontmatter has no `type: tdd`; docs/script-only change with no runtime behavior.

## Self-Check: PASSED

- scripts/generate_arch_diagram.py: FOUND (committed cd58c73)
- docs/architecture.md: FOUND (committed 5742622)
- git log contains cd58c73 and 5742622: FOUND
