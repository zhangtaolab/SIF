---
phase: 261105-eev-document-embedding-hardware-device-selec
plan: 01
subsystem: docs
tags: [documentation, device-selection, mps, metal, gpu, embedding, generated-docs]
requires: []
provides:
  - "docs/configuration.md Device Selection note (#### heading) under the Embedding Model Settings table — generated, CI-synced"
  - "scripts/generate_config_ref.py _append_device_selection_note helper as the durable source of the note"
  - "docs/installation.md hardware-acceleration guidance in Embedding Support and macOS sections"
affects: []
tech-stack:
  added: []
  patterns:
    - "Section-conditional note emission inside the generator's SECTIONS loop (note lands adjacent to the table row it clarifies)"
key-files:
  created: []
  modified:
    - scripts/generate_config_ref.py
    - docs/configuration.md
    - docs/installation.md
decisions:
  - "Note authored in the generator, never hand-edited into configuration.md — CI (.github/workflows/docs.yml) reruns the generator and enforces git diff --exit-code"
  - "Helper emits a leading blank line so the #### sub-heading separates cleanly from the table above; the loop's existing trailing blank separates the note from the next section"
  - "pip install \"sif[embed]\" kept as inline code, never a fenced block — configuration.md fences are extracted and validated by tests/test_docs.py"
  - "SIF_N_GPU_LAYERS table-cell description untouched (renders live from settings.py Field); 0=CPU / >0=Metal semantics live entirely in note prose"
  - "installation.md links use plain [Configuration](configuration.md) — no heading anchors into the regenerated file"
metrics:
  duration: 4min
  completed: "2026-11-05"
status: complete
actuals:
  tokens: 1222    # chars/4 over the realized diff (4888 chars); estimate 18000 covered planner fact-verification, realized edits were doc-prose-only
  tasks: 2
  commits: 2      # measured: git rev-list --count 8f5fcc2..HEAD
---

# Quick Task 261105-eev: Document Embedding Hardware/Device Selection Summary

One-liner: Documented embedding device selection — torch cuda→mps→cpu auto-detection, gguf SIF_N_GPU_LAYERS llama.cpp Metal offload — via a generator-emitted Device Selection note in configuration.md plus two installation.md hardware notes.

## What Was Built

### Task 1: Device Selection note in the config-reference generator; regenerate docs/configuration.md (commit ab638f4)

- Added module-level `_append_device_selection_note(lines: list[str]) -> None` to `scripts/generate_config_ref.py`, placed before `_append_options_tables`, called from inside the SECTIONS loop right after the Embedding Model Settings field rows (conditional on `section_name == "Embedding Model Settings"`, before the trailing blank line).
- The note: `#### Device Selection (CPU / GPU / MPS)` heading, one intro sentence (no device setting exists — backends auto-select), a 3-row Backend/Device-behavior table (modelscope+sentence_transformers torch auto-detect cuda→mps→cpu; gguf CPU-by-default with SIF_N_GPU_LAYERS > 0 = llama.cpp Metal offload, not torch MPS; openai remote), and a closing paragraph (BM25/FTS5 + sqlite-vec always CPU; embed-extra torch wheel ships MPS; no ANE/NPU).
- `docs/configuration.md` regenerated from the generator only — zero hand edits. Second generator run verified a no-op (cp+diff); post-commit regeneration verified `git diff --exit-code` clean (CI Docs Validation equivalent).

### Task 2: Hardware-acceleration notes in docs/installation.md (commit e3f7e2d)

- Embedding Support section: paragraph after the "This installs:" list stating automatic CUDA/MPS/CPU device selection with the embed extra, linking plainly to [Configuration](configuration.md).
- macOS section: `**Hardware acceleration**:` run-in note (matching the doc's **Cause**/**Solution** label style) after the brew/pip3 block — MPS auto-use on Apple Silicon for modelscope/sentence_transformers; GGUF CPU-only unless SIF_N_GPU_LAYERS > 0 which enables llama.cpp Metal offload (distinct from MPS).

## Verification Results

All must_haves and plan verification steps confirmed:

- `python scripts/generate_config_ref.py && grep -q 'Device Selection' docs/configuration.md` — pass (note exists under the Embedding Model Settings table)
- `grep -q 'MPS' && grep -q 'llama.cpp' docs/configuration.md` — pass
- `grep -q 'MPS' && grep -qi 'metal' && grep -q 'SIF_N_GPU_LAYERS' docs/installation.md` — pass
- `env -u FORCE_COLOR NO_COLOR=1 python -m pytest tests/test_docs.py -q` — 13 passed
- Regeneration stability: cp + rerun + diff clean, pre-commit and post-commit
- CI-equivalent: `git diff --exit-code docs/configuration.md` after regeneration against the committed file — clean
- `ruff check scripts/generate_config_ref.py` and `ruff format --check` — clean
- Full quality suite (CLAUDE.md): `ruff check src tests`, `ruff format --check src tests`, `pytest` — 676 passed
- `git diff --stat -- src/ tests/` and `git status -- src/ tests/` — empty; zero product-code changes
- configuration.md diff contains ONLY the note (12 lines); SIF_N_GPU_LAYERS table cell unchanged
- Terminology consistent across both files: torch backends = "Metal (MPS)"; gguf = "llama.cpp Metal offload", never conflated

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - blocking] ruff format compliance on generator edit**
- **Found during:** Task 1 verification
- **Issue:** Initial helper code failed `ruff format --check scripts/generate_config_ref.py` (baseline at HEAD was format-clean; the failure was introduced by this task's edit — one implicit string concat joinable within line length, one escaped-quote string preferring single quotes)
- **Fix:** Applied `ruff format scripts/generate_config_ref.py`; verified the generated markdown output is byte-identical before/after formatting (diff clean), so the doc content was unaffected
- **Files modified:** scripts/generate_config_ref.py
- **Commit:** ab638f4

Minor style alignment (within plan intent, not a deviation proper): the helper emits a leading blank line so the `####` sub-heading does not butt against the table's last row — the plan's "blank lines between blocks" style rule.

## Known Stubs

None — no code stubs; documentation-only change.

## Auth Gates

None.

## Self-Check: PASSED

- Commit ab638f4 (generator + regenerated configuration.md): `git merge-base --is-ancestor` verified in log; 2 files, 50 insertions, 0 deletions
- Commit e3f7e2d (installation.md): 1 file, 4 insertions, 0 deletions
- scripts/generate_config_ref.py contains `_append_device_selection_note` and the conditional call — verified by regeneration producing the note
- docs/configuration.md, docs/installation.md — notes present per grep checks above
