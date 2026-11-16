---
phase: "24"
slug: "tuning-models-ux-install-docs"
# status lifecycle: draft (seeded by plan-phase) → validated (set by validate-phase §6)
status: draft
nyquist_compliant: false
wave_0_complete: false
created: "2026-11-16"
---

# Phase 24 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.x + pytest-cov 7.x |
| **Config file** | `pyproject.toml` `[tool.pytest.ini_options]` + `[tool.coverage.report]` (`fail_under = 90`) |
| **Quick run command** | `env -u FORCE_COLOR NO_COLOR=1 pytest <path> -x --no-cov` |
| **Full suite command** | `env -u FORCE_COLOR NO_COLOR=1 pytest` |
| **Estimated runtime** | ~180–220 seconds (full suite); targeted < 20 seconds |

---

## Sampling Rate

- **After every task commit:** the targeted quick command(s) for touched modules + `ruff check`/`ruff format --check`
- **After every plan wave:** full `pytest` + `ty check src/sif`; `make docs-generate` no-diff when a CLI/Settings surface changed
- **Before `/gsd-verify-work`:** full suite green (coverage ≥ 90%); real sweep/breadcrumb evidence recorded; docs gate clean
- **Max feedback latency:** 220 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 24-01-01 | 01 | 1 | QUAL-02 | T-24-01 | Chunker call site converts tokens→chars and `--force` re-chunks; arm env pins Qwen3/512 max tokens and varies only size/overlap | unit | `env -u FORCE_COLOR NO_COLOR=1 pytest tests/unit/indexing/test_chunker.py tests/unit/scripts/test_chunk_sweep.py -x --no-cov` | Wave 0 new | ⬜ pending |
| 24-01-02 | 01 | 1 | QUAL-02 | T-24-01 | `--compare` gate selects on tuning and confirms on held-out; no winner at N=56/0.01 | unit | `env -u FORCE_COLOR NO_COLOR=1 pytest tests/unit/search/test_tuning_verdict.py -x --no-cov` | Wave 0 new | ⬜ pending |
| 24-01-03 | 01 | 1 | QUAL-02 | T-24-01 | Artifact is aggregate-only, deterministic, and refuses a different decision/corpus without `--force` | unit | `env -u FORCE_COLOR NO_COLOR=1 pytest tests/unit/scripts/test_chunk_sweep.py -x --no-cov` | Wave 0 new | ⬜ pending |
| 24-02-01 | 02 | 2 | QUAL-03 | T-24-02 | Breadcrumb builder: title + most recent heading; no heading → title-only; empty title → content-only; stored content unchanged | unit | `env -u FORCE_COLOR NO_COLOR=1 pytest tests/unit/indexing/test_breadcrumb.py tests/unit/indexing/test_embed_writer.py -x --no-cov` | Wave 0 new | ⬜ pending |
| 24-02-02 | 02 | 2 | QUAL-03 | T-24-02 | Embed text changes the cache key; stored chunk content/FTS unchanged; default off keeps byte-identical delivery | unit | `env -u FORCE_COLOR NO_COLOR=1 pytest tests/unit/embedding/test_cache.py tests/unit/indexing/test_embed_writer.py -x --no-cov` | Extend | ⬜ pending |
| 24-02-03 | 02 | 2 | QUAL-03 | T-24-02 | Duplicate metrics (title share, in-content share, sub-chunk share) and per-leg gate reading | unit | `env -u FORCE_COLOR NO_COLOR=1 pytest tests/unit/scripts/test_breadcrumb_eval.py -x --no-cov` | Wave 0 new | ⬜ pending |
| 24-03-01 | 03 | 3 | MODELS-01 | T-24-03 | Canonical path + manifest: valid cache → no network; non-empty dir without manifest → re-download; `--force` → re-download; missing modelscope → remedy | unit | `env -u FORCE_COLOR NO_COLOR=1 pytest tests/unit/models/test_download.py -x --no-cov` | Rewrite | ⬜ pending |
| 24-03-02 | 03 | 3 | MODELS-01 | T-24-03 | `DEFAULT_MODELS` pins Qwen3-0.6B family; legacy `~/.sif/models` / `<cache>/<owner>/<name___>` recognized | unit | `env -u FORCE_COLOR NO_COLOR=1 pytest tests/unit/models/test_download.py -x --no-cov` | Extend | ⬜ pending |
| 24-03-03 | 03 | 3 | MODELS-01/02 | T-24-03 | `sif models pull` defaults/args/`--force`/non-TTY quiet; `sif pull` alias deprecation; `models status` identity/backend/dims/JSON/non-TTY plain | CLI | `env -u FORCE_COLOR NO_COLOR=1 pytest tests/unit/cli/test_models.py tests/unit/cli/test_pull.py -x --no-cov` | Wave 0 new | ⬜ pending |
| 24-04-01 | 04 | 4 | DOCS-01 | T-24-04 | uv-first commands, CPU index, extras, degradation matrix, client snippets; `models` subcommands validated | docs | `env -u FORCE_COLOR NO_COLOR=1 pytest tests/test_docs.py tests/test_ci_workflows.py -v --no-cov` | Extend | ⬜ pending |
| 24-04-02 | 04 | 4 | DOCS-01 | T-24-04 | Generated CLI/config docs are clean | docs/CI | `make docs-generate && git diff --exit-code docs/cli-reference.md docs/configuration.md` | Existing | ⬜ pending |
| ALL | — | — | ALL | — | Full quality suite | gate | `ruff check src tests && ruff format --check src tests && pytest && ty check src/sif` | Existing | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/unit/scripts/test_chunk_sweep.py` — dry-run arm table, env pinning, grid, corpus-root guard, scope-key resume, cost collection, artifact schema/privacy, selection rule
- [ ] `tests/unit/scripts/test_breadcrumb_eval.py` — one-arm command plan, duplicate metric computation, artifact schema
- [ ] `tests/unit/indexing/test_breadcrumb.py` — pure builder cases (H1-first, H2-first, H1-per-section, no headings, CJK headings, empty title, separator/depth)
- [ ] `tests/unit/search/test_tuning_verdict.py` — gate policy: N=56 no 0.01 win, N=101 boundary, CI includes zero, tuning-select/held-out-confirm
- [ ] `tests/unit/cli/test_models.py` — pull/status TTY/non-TTY/JSON, identity statuses, backend probe, cache manifest states
- [ ] Rewrite `tests/unit/models/test_download.py` — canonical dir, manifest verify, md5-bug regression, legacy migration, corrected `DEFAULT_MODELS`
- [ ] Extend `tests/unit/cli/test_pull.py` — hidden alias delegation + deprecation notice
- [ ] Extend `tests/test_docs.py` — add `docs/installation.md`/`docs/migration.md` to `DOCS_FILES`, `models` to `_SUBCOMMANDS`, hidden-command handling, old-model-name guard
- [ ] Extend `tests/test_ci_workflows.py` — uv-first/CPU recipe/degradation matrix assertions
- [ ] Fixtures: a tiny fake ModelScope snapshot tree + manifest for downloader tests; a tiny heading corpus for breadcrumb tests
- [ ] No framework install — pytest is present

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Real chunk sweep on the Phase 23 corpus (6 arms) | QUAL-02 | Requires full re-chunk + re-embed (≈77 min) on the user's corpus; results are hardware/version-dependent and cannot gate CI | Run `python scripts/chunk_sweep.py --corpus <roots> --baseline-saved-run <qwen3.json> --keep-arms --json`; record per-arm costs, the tuning-selected arm, the held-out confirmation, and the decision; commit the aggregate artifact + docs section only |
| Real breadcrumb arm (≈22 min) | QUAL-03 | Requires a full re-embed and the per-leg comparison; not a CI gate | Run `python scripts/breadcrumb_eval.py --corpus <roots> --baseline-saved-run <qwen3.json> --keep-arms --json`; record duplicate metrics, per-leg gates, and the decision |
| Install docs end-to-end verification | DOCS-01 | The uv/torch/llama-cpp recipes are platform- and release-dependent; a real install on Linux/macOS is the proof | Follow `docs/installation.md` and `docs/models.md` on each platform; record the exact commands/output and any degradation observed |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 220s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
