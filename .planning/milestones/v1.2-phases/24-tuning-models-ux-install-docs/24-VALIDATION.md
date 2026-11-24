---
phase: "24"
slug: "tuning-models-ux-install-docs"
# status lifecycle: draft (seeded by plan-phase) → validated (set by validate-phase §6)
status: validated
nyquist_compliant: true
wave_0_complete: true
created: "2026-11-16"
validated: "2026-11-24"
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
| 24-01-01 | 01 | 1 | QUAL-02 | T-24-01 | Chunker call site converts tokens→chars and `--force` re-chunks; arm env pins Qwen3/512 max tokens and varies only size/overlap | unit | `env -u FORCE_COLOR NO_COLOR=1 pytest tests/unit/indexing/test_chunker.py tests/unit/scripts/test_chunk_sweep.py -x --no-cov` | Wave 0 new | ✅ green |
| 24-01-02 | 01 | 1 | QUAL-02 | T-24-01 | `--compare` gate selects on tuning and confirms on held-out; no winner at N=56/0.01 | unit | `env -u FORCE_COLOR NO_COLOR=1 pytest tests/unit/search/test_tuning_verdict.py -x --no-cov` | Wave 0 new | ✅ green |
| 24-01-03 | 01 | 1 | QUAL-02 | T-24-01 | Artifact is aggregate-only, deterministic, and refuses a different decision/corpus without `--force` | unit | `env -u FORCE_COLOR NO_COLOR=1 pytest tests/unit/scripts/test_chunk_sweep.py -x --no-cov` | Wave 0 new | ✅ green |
| 24-02-01 | 02 | 2 | QUAL-03 | T-24-02 | Breadcrumb builder: title + most recent heading; no heading → title-only; empty title → content-only; stored content unchanged | unit | `env -u FORCE_COLOR NO_COLOR=1 pytest tests/unit/indexing/test_breadcrumb.py tests/unit/indexing/test_embed_writer.py -x --no-cov` | Wave 0 new | ✅ green |
| 24-02-02 | 02 | 2 | QUAL-03 | T-24-02 | Embed text changes the cache key; stored chunk content/FTS unchanged; default off keeps byte-identical delivery | unit | `env -u FORCE_COLOR NO_COLOR=1 pytest tests/unit/embedding/test_cache.py tests/unit/indexing/test_embed_writer.py -x --no-cov` | Extend | ✅ green |
| 24-07-01 | 07 | 3 | QUAL-03 | T-24-14 | Dry run pins modelscope Qwen3, chunk 512/128, the breadcrumb env, and the ordered index/embed/identity/eval stage plan with the expected cache id | unit | `env -u FORCE_COLOR NO_COLOR=1 pytest tests/unit/scripts/test_breadcrumb_eval.py -x --no-cov` | Wave 0 new | ✅ green |
| 24-07-02 | 07 | 3 | QUAL-03 | T-24-06 | Duplicate metrics (title share, in-content share, sub-chunk share) and the per-leg body-veto decision | unit | `env -u FORCE_COLOR NO_COLOR=1 pytest tests/unit/indexing/test_breadcrumb.py tests/unit/search/test_tuning_verdict.py -x --no-cov` | Wave 0 new | ✅ green |
| 24-07-03 | 07 | 3 | QUAL-03 | T-24-14 | Persisted identity asserted (modelscope cache id, dim, no prompts); backend-mismatched baseline rejected; artifact carries model_type/identity and no private text | unit | `env -u FORCE_COLOR NO_COLOR=1 pytest tests/unit/scripts/test_breadcrumb_eval.py -x --no-cov` | Wave 0 new | ✅ green |
| 24-03-01 | 03 | 3 | MODELS-01 | T-24-03 | Canonical path + manifest: valid cache → no network; non-empty dir without manifest → re-download; `--force` → re-download; missing modelscope → remedy | unit | `env -u FORCE_COLOR NO_COLOR=1 pytest tests/unit/models/test_download.py -x --no-cov` | Rewrite | ✅ green |
| 24-03-02 | 03 | 3 | MODELS-01 | T-24-03 | `DEFAULT_MODELS` pins Qwen3-0.6B family; legacy `~/.sif/models` / `<cache>/<owner>/<name___>` recognized | unit | `env -u FORCE_COLOR NO_COLOR=1 pytest tests/unit/models/test_download.py -x --no-cov` | Extend | ✅ green |
| 24-03-03 | 03 | 3 | MODELS-01/02 | T-24-03 | `sif models pull` defaults/args/`--force`/non-TTY quiet; `sif pull` alias deprecation; `models status` identity/backend/dims/JSON/non-TTY plain | CLI | `env -u FORCE_COLOR NO_COLOR=1 pytest tests/unit/cli/test_models.py tests/unit/cli/test_pull.py -x --no-cov` | Wave 0 new | ✅ green |
| 24-04-01 | 04 | 4 | DOCS-01 | T-24-04 | uv-first commands, CPU index, extras, degradation matrix, client snippets; `models` subcommands validated | docs | `env -u FORCE_COLOR NO_COLOR=1 pytest tests/test_docs.py tests/test_ci_workflows.py -v --no-cov` | Extend | ✅ green |
| 24-04-02 | 04 | 4 | DOCS-01 | T-24-04 | Generated CLI/config docs are clean | docs/CI | `make docs-generate && git diff --exit-code docs/cli-reference.md docs/configuration.md` | Existing | ✅ green |
| ALL | — | — | ALL | — | Full quality suite | gate | `ruff check src tests && ruff format --check src tests && pytest && ty check src/sif` | Existing | ⚠️ green except `ty` |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

**Gate note (2026-11-24 audit):** `ruff check`, `ruff format --check`, and `pytest` (3260 passed, 1 skipped, 95.12% coverage) are green. `ty check src/sif` exits 1 with 10 diagnostics, all traced by `git blame` to pre-Phase-24 code (`src/sif/embedding/embedder.py` lines dated 2026-09-17; `src/sif/search/rerank.py` 2026-04-20/2026-09-17; `src/sif/models/download.py:545` 2026-04-15) against the locally installed `sentence-transformers 5.4.1` / `modelscope 1.36.0` stubs. Not a Phase 24 regression and not a requirement-coverage gap.

---

## Wave 0 Requirements

- [x] `tests/unit/scripts/test_chunk_sweep.py` — dry-run arm table, env pinning, grid, corpus-root guard, scope-key resume, cost collection, artifact schema/privacy, selection rule
- [x] `tests/unit/scripts/test_breadcrumb_eval.py` — one-arm command plan, duplicate metric computation, artifact schema
- [x] `tests/unit/indexing/test_breadcrumb.py` — pure builder cases (H1-first, H2-first, H1-per-section, no headings, CJK headings, empty title, separator/depth)
- [x] `tests/unit/search/test_tuning_verdict.py` — gate policy: N=56 no 0.01 win, N=101 boundary, CI includes zero, tuning-select/held-out-confirm
- [x] `tests/unit/cli/test_models.py` — pull/status TTY/non-TTY/JSON, identity statuses, backend probe, cache manifest states
- [x] Rewrite `tests/unit/models/test_download.py` — canonical dir, manifest verify, md5-bug regression, legacy migration, corrected `DEFAULT_MODELS`
- [x] Extend `tests/unit/cli/test_pull.py` — hidden alias delegation + deprecation notice
- [x] Extend `tests/test_docs.py` — add `docs/installation.md`/`docs/migration.md` to `DOCS_FILES`, `models` to `_SUBCOMMANDS`, hidden-command handling, old-model-name guard
- [x] Extend `tests/test_ci_workflows.py` — uv-first/CPU recipe/degradation matrix assertions
- [x] Fixtures: a tiny fake ModelScope snapshot tree + manifest for downloader tests; a tiny heading corpus for breadcrumb tests
- [x] No framework install — pytest is present

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Real chunk sweep on the authorized books_markdown corpus (6 arms) | QUAL-02 | Requires full re-chunk + re-embed (≈2.5 h) on the user's corpus; the corpus is 610 documents (2 English books + 608 Chinese/English papers) after the 2026-11-17 amendment; results are hardware/version-dependent and cannot gate CI | Run `python scripts/chunk_sweep.py --corpus /Users/forrest/Playground/books_markdown --corpus-label books-markdown-papers-2026-11 --scratch-root .planning/tmp/phase-24-chunk-sweep-books --keep-arms --json`; the fresh baseline uses `--min-heldout 101` and measured held-out N=194; record per-arm costs, the tuning-selected arm, the held-out confirmation, and the decision; commit the aggregate artifact + docs section only |
| Real breadcrumb arm (≈25–35 min) | QUAL-03 | Requires a full re-embed and the per-leg comparison; not a CI gate | Run `python scripts/breadcrumb_eval.py --corpus /Users/forrest/Playground/books_markdown --corpus-label books-markdown-papers-2026-11 --baseline-saved-run .planning/tmp/phase-24-chunk-sweep-books/saved-runs/baseline.json --scratch-root .planning/tmp/phase-24-breadcrumb-books --keep-arms --json`; record duplicate metrics, per-leg gates, and the decision |
| Install docs end-to-end verification | DOCS-01 | The uv/torch/llama-cpp recipes are platform- and release-dependent; a real install on Linux/macOS is the proof | Follow `docs/installation.md` and `docs/models.md` on each platform; record the exact commands/output and any degradation observed |

---

## Manual Evidence (2026-11-17)

Both manual rows ran on the user-authorized `books-markdown-papers-2026-11` corpus (610 documents: 2 English books + 608 Chinese/English papers; fingerprint `9ccbf4eea9263ed4`) with the modelscope Qwen3-Embedding-0.6B identity. The fresh baseline passed `--min-heldout 101`; sampling widened to 200 documents with held-out **N=194** (en=136, zh=244, mixed=12).

- **QUAL-02 chunk sweep**: six arms completed in 2h08m; **decision `keep-default`**. Tuning selected `overlap-0` (+0.000737), but the held-out confirmation was -0.008605 (CI [-0.021559, +0.003094], helped 2 / hurt 9 / unchanged 183); every non-baseline arm's held-out delta was negative or flat. No chunk default changed. Artifact: `bench/chunk-sweep.json`.
- **QUAL-03 breadcrumb arm**: **decision `keep-breadcrumb-off`**. Overall held-out delta +0.014104 (CI [-0.005664, +0.035548], winner false); title leg +0.048521 (winner true), body leg +0.006243 (winner false); duplicate metrics `title_share=1.0`, `in_content_share=0.622955`, `subchunk_share=0.387919`; replay unavailable (no saved snapshot). `embed_breadcrumb` stays False. Artifact: `bench/breadcrumb-verdict.json`.
- **Conditional marker**: no default flipped, so no `chunking.contract` marker code was added; `test_embed_writes_chunking_contract_marker_iff_contract_flipped` asserts the marker is absent through the real embed path.
- The manual rows above are complete; the Nyquist audit ran on 2026-11-24 and set `status: validated` / `nyquist_compliant: true`.

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 220s (full suite measured 206s on 2026-11-24)
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** approved 2026-11-24

## Validation Audit 2026-11-24

| Metric | Count |
|---|---|
| Gaps found | 0 |
| Resolved | 0 |
| Escalated | 0 |
