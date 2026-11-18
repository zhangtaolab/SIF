# Phase 17: Engineering Foundation (CI Matrix + Hygiene + PyPI) - Context

**Gathered:** 2026-11-13
**Status:** Ready for planning

<domain>
## Phase Boundary

The milestone's foundation phase — a green regression net and a proven release pipeline before any risky change. Delivers exactly ENG-01..ENG-04:

1. **CI matrix (ENG-01)** — full test suite on py3.10–3.13 × ubuntu/macos, fail_under=90 per cell, CPU torch on Linux, tolerant of both py3.10 / py3.11+ resolution fleets.
2. **Windows degradation smoke (ENG-02)** — CLI-level degradation assertions run on hc remote `yoga` (Windows 11, project dir `D:\Github\SIF`), NOT full Windows support (deferred to v2).
3. **PyPI release (ENG-03)** — publish `docsif` 1.1.2 via trusted publishing, mcp-name marker before publish, version single-sourced.
4. **Repo hygiene (ENG-04)** — delete dead layers, orphan export, phantom pre-commit target, black dependency; clean tracked junk; 3.13 classifier only when matrix is green.

NOT in scope: any new capability, full Windows support (v2), Intel macOS runners, GH windows-latest jobs, info-severity findings sweep beyond the named zero-risk items, v1.2 feature work (Phases 18+).

</domain>

<decisions>
## Implementation Decisions

### CI topology (ENG-01)
- **D-01:** **Every push/PR runs the full 8-cell matrix** — py3.10, py3.11, py3.12, py3.13 × {ubuntu-latest, macos-latest}; full suite per cell, `fail_under=90` per cell. No PR-vs-push split, no nightly-only full runs. Strongest regression net; the 8×~5min cost is accepted. — **Reversibility:** reversible — workflow-file change only.
- **D-02:** **Dependency cache only** — uv/pip caches via `actions/cache`/setup-uv cache; NO HuggingFace model cache. CI tests use `ConceptEmbedder` (deterministic synthetic embeddings, Phase 16 D-01), so no model downloads occur. Linux cells install CPU torch via `--index https://download.pytorch.org/whl/cpu` (multi-GB CUDA default avoided). Do not assert exact transitive versions — py3.10 resolves torch 2.14.1 / rapidfuzz 3.14.5 / httpx2 2.14.0; py3.11+ resolves 2.15.0 / 3.14.6 / 2.16.0.
- **D-03:** **macOS coverage = macos-latest (arm64) only** — 8 cells total. Intel macOS (macos-13) deferred; research did not require it.
- **D-04:** **Concurrency: cancel-in-progress per ref** — superseded runs cancel; `fail-fast: false` so all cells report (Claude's discretion on exact YAML).

### Windows smoke (ENG-02)
- **D-05:** **Committed script + Makefile target, run via hc** — the smoke is a repo-committed script (Python or PowerShell — Claude's discretion) plus a Makefile target, executed on demand via `hc exec --on yoga` / `hc run --on yoga --cwd 'D:\Github\SIF'`. The Windows project directory on yoga is `D:\Github\SIF`. Python is NOT preinstalled on yoga (Microsoft Store alias only) — `uv python install` first. NOT a GitHub Actions windows-latest job. — **Reversibility:** reversible.
- **D-06:** **CLI-level degradation assertions** — assert `index`/`search`/`status` (and watch/service paths where reachable) give clear errors or safe degradation when `fcntl` / systemd / fork semantics are absent; assert the degradation is honest (no mass-delete on missing root, no silent lock bypass). NOT the full pytest suite, NOT a pytest marker subset. The target is the user-visible surface, not internal semantics.
- **D-07:** **Trigger: manual/on-demand + pre-release** — documented in install/release docs; run before PyPI publishes. No per-PR or weekly schedule (yoga is a user machine).

### Repo hygiene (ENG-04)
- **D-08:** **Delete dead layers outright** — `MigrationManager`, `src/sif/models/search.py`, `src/sif/search/strategy.py` are deleted; git history is the archive. Their tests are deleted/moved in the same plan so the suite collects. — **Reversibility:** costly — test-only layers referenced by multiple test modules; deletion is recoverable via git but re-wiring later means re-adding files.
- **D-09:** **Hygiene bundle is zero-risk only** — dead layers + orphan `compute_rrf_score` export + phantom Makefile `pre-commit` target + `black` dev dependency. No repo-wide zero-reference scan (false-positive risk); no behavior changes.
- **D-10:** **pre-commit: delete target + doc references, clear VERIFY markers** — `make pre-commit` and its doc mentions are removed; the 4 `<!-- VERIFY: -->` markers about the nonexistent `.pre-commit-config.yaml` are cleared. Do NOT create a `.pre-commit-config.yaml` (make ci already covers format/lint/type/test).
- **D-11:** **Extras/classifier locking (research-locked)** — `embed` floor `sentence-transformers>=5.4.1`; `all` floor `llama-cpp-python>=0.3.35`; `fastapi`/`uvicorn` remain core deps; `dev` drops black; 3.13 classifier added only after the matrix is green.
- **D-12:** **Tracked junk audit** — `git ls-files` audit for junk (current scan found none matching `.DS_Store`/`__pycache__`/coverage/logs); removals limited to genuinely tracked junk, if any.

### PyPI release (ENG-03)
- **D-13:** **Publish version 1.1.2** — patch release of current behavior (`src/sif/_version.py` is 1.1.1 today); proves the release pipeline without committing to v1.2 API. — **Reversibility:** one-way — a published version number is permanent (yanking is possible but visible and does not free the number).
- **D-14:** **Tag push (v*) auto-triggers publishing** — one workflow: build job (Linux-only, `pypa/gh-action-pypi-publish@release/v1`), TestPyPI upload first, then PyPI upload; trusted publishing (GitHub environment) + PEP 740 attestations. **README `<!-- mcp-name: io.github.zhangtaolab/sif -->` marker lands BEFORE the first publish.** Version single-sourced across `pyproject.toml`, `src/sif/_version.py`, `src/sif/__init__.py`, `src/sif/cli/__init__.py`, `src/sif/config/constants.py`, `src/sif/mcp/protocol.py`. — **Reversibility:** one-way for the published artifact and the mcp-name marker (Registry listing depends on it).
- **D-15:** **TestPyPI on every tag release** — same workflow, sequential TestPyPI → PyPI. No separate manual gate; the tag is the release intent.

### Claude's Discretion
- Workflow YAML structure (job names, matrix include/exclude, concurrency group, setup-uv SHA pin, cache keys)
- Windows smoke script language and exact assertion set/messages; Makefile target name
- Dead-layer test cleanup mechanics (delete vs relocate assertions)
- PyPI workflow environment name, build-job separation, artifact checks
- Exact tracked-junk audit procedure
- Whether `Makefile` `ci` target gains the new test workflow parity

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Milestone research
- `.planning/research/SUMMARY.md` §"Phase 1: Engineering Foundation" + §"Key Findings / Recommended Stack" + §"Gaps to Address"
- `.planning/research/STACK.md` — setup-uv v10.3.3 (SHA-pin; `python-version` does NOT install Python), pypa/gh-action-pypi-publish v1.14.3, torch CPU index recipe, py3.10/3.11+ resolution fleets, wheel coverage
- `.planning/research/PITFALLS.md` §P21 (CUDA bloat), §P22 (wheel strategy), §P23 (Windows degradation), §P24 (publish mechanics)
- `.planning/research/ARCHITECTURE.md` §tier 0 (hygiene/dead layers)

### Requirements and roadmap
- `.planning/REQUIREMENTS.md` — ENG-01..ENG-04; Out of Scope table
- `.planning/ROADMAP.md` §Phase 17 — goal + 4 success criteria

### Project conventions
- `CLAUDE.md` — quality gates (`ruff`, `ruff format --check`, `ty check`, `pytest` fail_under=90), generator-owned docs rule, GSD workflow
- `.planning/reports/MILESTONE_SUMMARY-v1.1.md` — v1.1 baseline state (1628 tests @ 95.06%, 7 phases, debt ledger)
- `.planning/PROJECT.md` §Key Decisions — v1.2 scope decisions, Windows smoke via hc yoga

### Code/intake sites (verified this session)
- `pyproject.toml` — extras (`dev` includes black; `embed` floor `sentence-transformers>=2.2.0`; `all` floor `llama-cpp-python>=0.2.0`; `mcp` extra = uvicorn only), hatch dynamic version
- `src/sif/_version.py` — version single-source target (currently 1.1.1)
- `Makefile` — targets incl. phantom `pre-commit`; `ci` target composition
- `.github/workflows/docs.yml` — the only existing workflow (946B; docs gate precedent)
- `src/sif/models/search.py`, `src/sif/search/strategy.py` — dead layers (delete)
- `.planning/phases/17-engineering-foundation-ci-matrix-hygiene-pypi/17-DISCUSS-CHECKPOINT.json` — discussion audit (deleted after CONTEXT commit)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `.github/workflows/docs.yml` — existing Actions workflow; establishes repo CI conventions (triggers, setup steps).
- `Makefile` — target structure (`ci: format-check lint typecheck security test`) is the local gate the new CI must mirror; `docs-generate` already gated in CI.
- `pyproject.toml` — hatchling dynamic version reads `src/sif/_version.py`; the single-source hub for version work.
- `tests/` — 1628-test suite with `fail_under=90`; the matrix runs it unchanged.

### Established Patterns
- Deterministic tests: `env -u FORCE_COLOR NO_COLOR=1`, `tmp_path` batteries, no wall-clock races; CI must preserve these env assumptions.
- No-noqa culture; complexity ≤10; fully annotated (ty gate).
- Generator-owned docs (`docs/cli-reference.md`, `docs/configuration.md`) — never hand-edited; `make docs-generate` diff gate.
- Remedy-hint error culture — Windows degradation messages must name the cause and the fix.

### Integration Points
- `.github/workflows/` — new test matrix workflow + publish workflow
- `Makefile` — add windows-smoke target; remove pre-commit target
- `pyproject.toml` — extras floors, classifiers, dev deps
- `src/sif/models/search.py`, `src/sif/search/strategy.py`, `MigrationManager` references — delete + fix importing tests
- `src/sif/search/rrf.py` — orphan `compute_rrf_score` export removal
- Docs mentioning `make pre-commit` / VERIFY markers — clear

</code_context>

<specifics>
## Specific Ideas

- **yoga Windows project dir = `D:\Github\SIF`** (user-provided 2026-11-13). Invocation shape: `hc exec --on yoga --cwd 'D:\Github\SIF' ...`; `uv python install` first (Store alias only today).
- **README marker exact text:** `<!-- mcp-name: io.github.zhangtaolab/sif -->` — must land in the README before the 1.1.2 publish; the MCP Registry consumes it in Phase 22.
- **No HF cache in CI** because Phase 16 locked `ConceptEmbedder` for hermetic bench/CI embeddings — keep the suite model-free.
- **Resolution fleets are real:** never pin or assert torch/rapidfuzz/httpx2 exact versions in tests; CI tolerates both.
- **PYPI trusted publishing requires the GitHub environment + PyPI trusted-publisher registration** — sequence: marker → TestPyPI dry run → PyPI publish of 1.1.2.

</specifics>

<deferred>
## Deferred Ideas

- Intel macOS runner (macos-13) coverage — revisit if an Intel-only wheel bug appears.
- GitHub-hosted windows-latest smoke job — rejected for v1.2 (yoga hc is the user's stated path); full Windows support is v2.
- Repo-wide zero-reference/private-function scan — deferred (false-positive risk); named zero-risk items only.
- Info-findings sweep remainder (v1.1 ledgers 11-WR-04/IN-05, 14-IN-01/IN-02, 15-IN-01/IN-03..07, 16-IN-01..06) — later cleanup pass, not this phase.

None — discussion stayed within phase scope otherwise.

</deferred>

---

*Phase: 17-Engineering Foundation (CI Matrix + Hygiene + PyPI)*
*Context gathered: 2026-11-13*
