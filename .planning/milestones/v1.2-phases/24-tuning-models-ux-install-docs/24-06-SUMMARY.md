---
phase: 24-tuning-models-ux-install-docs
plan: 06
subsystem: search-quality-evidence
tags: [QUAL-02, QUAL-03, chunk-sweep, breadcrumb, held-out-gate, min-heldout, books-markdown, keep-default]
requires:
  - "Plan 24-01: chunk-sweep instrument and tuning verdict"
  - "Plan 24-02: breadcrumb embed contract and Settings switch"
  - "Plan 24-07: breadcrumb evaluation layer and duplicate metrics"
provides:
  - ".planning/phases/24-tuning-models-ux-install-docs/bench/chunk-sweep.json"
  - ".planning/phases/24-tuning-models-ux-install-docs/bench/breadcrumb-verdict.json"
  - "docs/benchmarking.md QUAL-02/QUAL-03 evidence sections"
  - "sif eval --min-heldout (additive, default 25, range 25-500)"
  - "conditional chunking.contract marker test through the real embed path"
affects:
  - "Phase 24 closes with defaults unchanged; no marker code and no re-embed migration"
  - "The evidence is corpus-scoped to books-markdown-papers-2026-11, not Phase 23"
tech-stack:
  added: []
  patterns:
    - "Fresh baseline with --min-heldout 101 widens the sample to 200 docs (held-out N=194)"
    - "Corpus-scoped limitation text generated from the measured held-out N"
    - "Body-leg veto rejects title-only breadcrumb gains as duplicate signal"
key-files:
  created:
    - .planning/phases/24-tuning-models-ux-install-docs/bench/chunk-sweep.json
    - .planning/phases/24-tuning-models-ux-install-docs/bench/breadcrumb-verdict.json
  modified:
    - scripts/chunk_sweep.py
    - scripts/breadcrumb_eval.py
    - src/sif/search/personal_bench.py
    - src/sif/cli/commands/eval.py
    - docs/benchmarking.md
    - docs/cli-reference.md
    - tests/unit/cli/test_eval.py
    - tests/unit/cli/test_index.py
    - tests/unit/search/test_personal_bench.py
    - tests/unit/scripts/test_chunk_sweep.py
    - tests/unit/scripts/test_breadcrumb_eval.py
    - .planning/phases/24-tuning-models-ux-install-docs/24-06-PLAN.md
    - .planning/phases/24-tuning-models-ux-install-docs/24-VALIDATION.md
    - .planning/STATE.md
    - .planning/ROADMAP.md
decisions:
  - "The controlled corpus was amended (user-authorized 2026-11-17) from the Phase 23 SynologyDrive roots to /Users/forrest/Playground/books_markdown: 610 docs (2 English books + 608 Chinese/English papers; 422 zh-dominant, 163 en-dominant, 23 mixed). SynologyDrive was never read or written."
  - "sif eval gained the additive --min-heldout option; the runbooks pass 101 for the fresh baseline, which sampled 200 docs and produced held-out N=194 (en=136, zh=244, mixed=12), clearing the 0.01 gate's 101 floor (1/N≈0.00515)."
  - "QUAL-02 decision keep-default: tuning selected overlap-0 (+0.000737) but its held-out delta was -0.008605 (CI [-0.021559, +0.003094], helped 2 / hurt 9 / unchanged 183); every non-baseline arm's held-out delta was negative or flat."
  - "QUAL-03 decision keep-breadcrumb-off: overall held-out +0.014104 (CI [-0.005664, +0.035548], winner false); title leg +0.048521 (winner true) but body leg +0.006243 (winner false); title-only gains are duplicate signal, and replay was unavailable with no saved snapshot."
  - "No default changed: DEFAULT_CHUNK_SIZE=512, DEFAULT_CHUNK_OVERLAP=128, embed_breadcrumb=False; no chunking.contract marker code and no sif index embed --force migration."
metrics:
  duration: "~3 h (2h08m sweep + 34m breadcrumb + amendment/close)"
  completed: "2026-11-17"
  tasks: 3
  files: 17
status: complete
actuals:
  tokens: 0
  tasks: 3
  commits: 0
commits: 0
plan_head_before: 1fdb9f7
plan_head_after: uncommitted
requirements-completed: [QUAL-02, QUAL-03]
---

# Phase 24 Plan 06: Real Tuning and Breadcrumb Evidence Summary

Both held-out-gated experiments ran on the user-authorized `books_markdown` corpus and both returned a no-change verdict: chunking and breadcrumb defaults stay as shipped, with the measured numbers committed as aggregate artifacts and documented in `docs/benchmarking.md`.

## Performance

- **Duration:** ~3 h wall time
- **Chunk sweep:** 2 h 08 m (six arms; 610 docs, 21,886 baseline chunks)
- **Breadcrumb:** 34 m (one arm; baseline saved run reused)
- **Tasks:** 3
- **Files:** 17 modified + 2 artifacts

## Accomplishments

- **QUAL-02 six-arm sweep.** All six arms completed on 610 documents (2 English books + 608 Chinese/English papers; fingerprint `9ccbf4eea9263ed4`): baseline 512/128 (21,886 chunks, 1,776 s, 7,565 cache hits), 512/64 (20,980; 707 s; 13,506 hits), 512/0 (20,275; 571 s; 13,517 hits), 448/112 (23,450; 1,002 s; 10,377 hits), 384/96 (25,611; 1,245 s; 10,003 hits), 256/64 (33,160; 2,040 s; 8,918 hits). Selection on tuning picked `overlap-0` (+0.000737); the held-out confirmation was -0.008605 (CI [-0.021559, +0.003094], helped 2 / hurt 9 / unchanged 183, N=194) with `winner=false` → `keep-default`.
- **QUAL-03 breadcrumb arm.** One 512/128 arm with `embed_breadcrumb=True` reused the sweep's fresh baseline (same fingerprint/model identity). Overall held-out +0.014104 (CI [-0.005664, +0.035548], helped 11 / hurt 7 / unchanged 176, winner false); title leg +0.048521 (CI [+0.022742, +0.075609], winner true); body leg +0.006243 (CI [-0.007615, +0.021192], winner false). Duplicate metrics: `title_share=1.0`, `in_content_share=0.622955`, `subchunk_share=0.387919`, `title_equals_heading_share=0.026364`. Replay stability unavailable (no saved snapshot). → `keep-breadcrumb-off`.
- **Instrument extension.** `sif eval` gained the additive `--min-heldout` option (default 25, range 25-500); `ensure_heldout` raises the held-out floor to the requested value. The runbooks pass `--min-heldout 101` for the fresh baseline and generate the limitation from the measured N instead of the retired Phase 23 N=56 constants.
- **Evidence docs.** `docs/benchmarking.md` now carries `## Chunk-Size/Overlap Sweep (QUAL-02)` and `## Title-Breadcrumb Experiment (QUAL-03)` with per-arm/per-leg tables, the corpus label/fingerprint, adequacy, `min_heldout_for_epsilon_win=101`, N=194, the 1/N≈0.00515 floor, decisions, limitations, and artifact citations.
- **Conditional marker decision.** On the keep outcome no marker code was added; `test_embed_writes_chunking_contract_marker_iff_contract_flipped` asserts through the real embed path that `index_meta['chunking.contract']` is absent when no default flipped.
- **VALIDATION evidence.** `24-VALIDATION.md` records both manual rows, the N=194 adequacy, the decisions, and the marker outcome.

## Task Commits

No commits were made. The user has not authorized a commit; all changes remain in the working tree. The intended atomic split is recorded in the hand-off: (A) instrument + amendment, (B) evidence artifacts + benchmarking docs, (C) phase close/STATE/ROADMAP.

## Decisions Made

- The corpus is `books-markdown-papers-2026-11` (610 docs), not the Phase 23 seven-root corpus; the plan amendment records why (SynologyDrive is off-limits).
- `--min-heldout 101` is the explicit instrument control that makes the 0.01 gate admissible; it only raises the floor and keeps the default path byte-identical.
- Neither experiment authorizes a default change; `keep-defaults` is the only offered Task 3 option.
- The body-leg veto is the deciding rule for breadcrumb: a title-only win is duplicate signal even if the overall gate had won.

## Deviations from Plan

### User-authorized corpus amendment (2026-11-17)

The Phase 23 corpus lives under `~/SynologyDrive`, which the user prohibited. The user supplied `/Users/forrest/Playground/books_markdown` (2 books) and then added `markdown/` (608 mostly-Chinese papers), and authorized option A: add `--min-heldout` to the instrument and amend 24-06 to this corpus. The preflight measured 610 documents, sampled 200, held-out N=194 (en=136/zh=244/mixed=12), so the 0.01 gate is admissible.

### Fixed: breadcrumb artifact wrote to the chunk-sweep path

`breadcrumb_eval.write_committed_artifact` forwarded `path=None` to the shared writer, whose default is the chunk-sweep artifact. The guard refused the overwrite and the run exited 2 after the arm had completed. Fixed by defaulting to `ARTIFACT_PATH`, with a regression test (`test_default_path_is_the_breadcrumb_artifact`); the resumed run rebuilt the artifact from the stage markers in 0.38 s without re-embedding.

### Added: replay stability section

The plan's Task 2 verify originally expected a replay gate inside `legs`; the comparison payload carries replay stability separately. The runbook now records `replay` (available/baseline_available/num_queries/jaccard/top1/note) as its own artifact section, and the plan verify asserts the title/body legs plus the replay section. Replay was unavailable because the corpus has no saved replay snapshot.

## Issues Encountered

- The only failure was the breadcrumb artifact path bug, caught by the shared writer's do-not-overwrite guard; fixed and regression-tested before re-running the artifact write.
- The first breadcrumb run was refused after 27 minutes of embedding; the stage machine resumed the artifact write in under a second, so no embedding work was repeated.

## Verification

- Task 1: artifact schema + privacy assertions pass; `tests/unit/scripts/test_chunk_sweep.py` 44 passed.
- Task 2: artifact schema + privacy assertions pass; `tests/unit/scripts/test_breadcrumb_eval.py` + `tests/unit/indexing/test_breadcrumb.py` 63 passed.
- Conditional marker: `pytest tests/unit/cli/test_index.py -k chunking_contract_marker` 1 passed.
- Full suite: **3,233 passed, 1 skipped, 95.03% coverage**.
- `ruff check src tests scripts`, `ruff format --check src tests scripts`, `ty check src/sif` — green.
- `make docs-generate` is idempotent on a second run; only the intended 3-line `--min-heldout` addition in `docs/cli-reference.md` differs from HEAD.
- Defaults assertion: `(DEFAULT_CHUNK_SIZE, DEFAULT_CHUNK_OVERLAP) == (512, 128)` and `Settings().embed_breadcrumb is False`; the migration re-embed assertion passes because no default flipped.

### Platform Verification (2026-11-17)

The committed tree (`256380e`) was verified on all three platforms:

| Platform | Environment | Result |
|----------|-------------|--------|
| macOS arm64 | local, Python 3.12, full suite | **3,233 passed, 1 skipped, 95.03%**; ruff/format/ty green |
| Linux x86_64 | nv5090 (Ubuntu 5.15), Python 3.13.18 | **3,232 passed, 2 skipped, 95.04%**; ruff/format/ty green; 470 focused tests green |
| Windows 11 | Yoga (DESKTOP-JEIOI9A), managed Python 3.12 | **`windows_smoke.py` 8/8 PASS at HEAD `256380e`**; 346 changed-area tests + 124 affected-module tests passed |

- **Linux environment deviation:** `download-r2.pytorch.org` was DNS-unreachable on nv5090, so the lock's `torch==2.15.0+cpu` could not be fetched. Verification reused an existing Python 3.13 venv's `torch==2.14.1+cu130` through a `.pth` path, with `CUDA_VISIBLE_DEVICES=` to match the CI's CPU-only runner. A stale `platformdirs` pytest entry point from that shared path required `-p no:platformdirs`; neither workaround changes the repository. The full suite is green under the CI-equivalent CPU mode.
- **Windows locale caveat:** under the machine's default GBK locale, 14 `tests/test_docs.py` tests fail with `UnicodeDecodeError` because they call `Path.read_text()` without an encoding. The same failure occurs on the untouched `48759e2` checkout, so it is pre-existing and unrelated to 24-06; with `PYTHONUTF8=1` all 20 docs tests pass and the affected-module run is 124/124. Full Windows support remains deferred to v2.
- **Windows checkout safety:** verification used a fresh clone at `D:\Github\SIF-verify-256380e`; the pre-existing `D:\Github\SIF` checkout was not modified.

## Next Phase Readiness

- 24-06 execution is complete and the evidence is committed to disk (uncommitted in git).
- Phase 24 verification (gsd-verifier, code review, regression gate) and the milestone close remain.
- The scratch trees (1.3 GB sweep + 208 MB breadcrumb + 101 MB smoke) are gitignored; the 4.0 GB embedding cache is reusable.

## Self-Check: PASSED

- `bench/chunk-sweep.json` and `bench/breadcrumb-verdict.json` exist, pass schema/privacy, and contain the corpus-scoped limitation.
- `docs/benchmarking.md` carries both required sections and both artifact citations.
- No default changed and no marker code exists; the marker test asserts absence.
- Full suite, ruff, format, ty, and docs idempotence are green.
