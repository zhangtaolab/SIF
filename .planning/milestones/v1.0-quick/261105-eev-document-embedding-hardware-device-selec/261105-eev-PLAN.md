---
phase: 261105-eev-document-embedding-hardware-device-selec
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - scripts/generate_config_ref.py
  - docs/configuration.md
  - docs/installation.md
autonomous: true
requirements: [QUICK-DOC-DEVICE-SELECTION]  # quick task: document embedding hardware/device selection (MPS/GPU/CPU) — verified findings, no product code changes
estimate:
  tokens: 18000
  raw_tokens: 18000
  tasks: 2
  confidence: low

must_haves:
  truths:
    - "`python scripts/generate_config_ref.py && grep -q 'Device Selection' docs/configuration.md` exits 0 — a Device Selection note exists under the Embedding Model Settings table of the REGENERATED docs/configuration.md (baseline at HEAD: 0 occurrences, planner-verified)"
    - "`grep -q 'MPS' docs/configuration.md && grep -q 'llama.cpp' docs/configuration.md` exit 0 — the note names MPS auto-detection and the llama.cpp GGUF offload path (baselines at HEAD: 0 and 0)"
    - "`grep -q 'MPS' docs/installation.md && grep -qi 'metal' docs/installation.md && grep -q 'SIF_N_GPU_LAYERS' docs/installation.md` all exit 0 — installation.md's Embedding Support and macOS sections explain GPU auto-detection and the SIF_N_GPU_LAYERS Metal toggle (baselines at HEAD: all 0)"
    - "`env -u FORCE_COLOR NO_COLOR=1 python -m pytest tests/test_docs.py -q` passes — phantom-env-var, model_type-truthfulness, and code-block validation still green after the doc changes"
    - "Regeneration is stable: running `python scripts/generate_config_ref.py` a second time changes nothing further (cp + diff proof), so CI's `git diff --exit-code docs/configuration.md` in .github/workflows/docs.yml passes once generator + regenerated doc are committed together"
    - "ZERO changes under src/ — the SIF_N_GPU_LAYERS table-cell description still reads verbatim from the Pydantic Field description in src/sif/config/settings.py:65-69; the 0=CPU / >0=Metal clarification lives entirely in the new note prose"
  artifacts:
    - "scripts/generate_config_ref.py — new `_append_device_selection_note(lines: list[str]) -> None` helper (module level, near the other `_append_*` helpers) plus a call inside `_append_options_tables` emitted right after the Embedding Model Settings table rows (conditional on `section_name == \"Embedding Model Settings\"`, after the field loop, before the trailing blank line)"
    - "docs/configuration.md — regenerated output containing the Device Selection note (a `#### Device Selection (CPU / GPU / MPS)` block: one intro sentence, a 3-row backend table, and a short always-CPU/MPS-wheel/no-ANE paragraph) directly under the Embedding Model Settings table; NO hand-edits to this file — every byte must come from the generator"
    - "docs/installation.md — (a) Embedding Support section: a short paragraph after the 'This installs:' list stating GPU auto-detection (CUDA / Apple MPS) with the embed extra, linking plainly to configuration.md; (b) macOS section: a short 'Hardware acceleration' note after the pip3 block covering MPS auto-use, SIF_N_GPU_LAYERS default 0 = CPU, >0 = llama.cpp Metal offload"
  key_links:
    - "_append_device_selection_note content <-> verified code behavior: modelscope + sentence_transformers auto-detect cuda->mps->cpu (src/sif/embedding/embedder.py:59-64 and 312-315); gguf n_gpu_layers default 0 = CPU only, >0 = llama.cpp GPU offload, Metal on macOS and NOT MPS/torch (embedder.py:129-165, src/sif/config/settings.py:65-69); openai runs remotely; BM25/FTS5 + sqlite-vec always CPU; no NPU/ANE anywhere — every claim in the note must trace to one of these"
    - "generator SECTIONS table <-> the note insertion point: SECTIONS already lists n_gpu_layers under 'Embedding Model Settings' (scripts/generate_config_ref.py:100-115), so the conditional hook lands the note adjacent to the SIF_N_GPU_LAYERS row it clarifies"
    - "docs/installation.md cross-link <-> docs/configuration.md: link with plain `[Configuration](configuration.md)` (matching existing installation.md link style); do NOT use heading anchors — the target heading lives in a regenerated file and anchors are brittle"
---

<objective>
Document how SIF selects embedding compute hardware (CUDA GPU / Apple MPS / CPU) so users can answer "will indexing use my GPU?" from the docs alone. All facts are planner-verified against code this session; this is a documentation-only change with zero edits under src/.

Verified behavior being documented:
- modelscope (the SIF_MODEL_TYPE default) and sentence_transformers backends auto-detect the device at model load via torch: CUDA GPU if available, else Apple Metal (MPS) on arm64 macOS, else CPU. No user-facing device setting exists (src/sif/embedding/embedder.py:59-64, 312-315).
- gguf (LlamaCppEmbedder) is CPU-only by default: n_gpu_layers=0 (SIF_N_GPU_LAYERS, default 0 per src/sif/config/settings.py:65-69); values > 0 offload layers via llama.cpp — Metal on macOS, which is llama.cpp's own path, not torch MPS (embedder.py:129-165).
- openai backend computes embeddings remotely; local hardware is irrelevant.
- BM25/FTS5 and sqlite-vec vector search always run on CPU.
- No NPU/ANE support anywhere. The local-model stack arrives via the optional embed extra; `pip install "sif[embed]"` provides arm64 torch with MPS built in.

CRITICAL delivery constraint (planner-verified this session): docs/configuration.md is a FULLY GENERATED file — `python scripts/generate_config_ref.py` writes the entire file (scripts/generate_config_ref.py:380-387), and .github/workflows/docs.yml:34-38 reruns the generator in CI then enforces `git diff --exit-code docs/cli-reference.md docs/configuration.md`. A hand-edit to configuration.md would fail CI. Therefore the configuration.md content MUST be authored in the generator script (a docs tool — this honors the task's no-product-code-changes intent; src/ stays untouched) and the doc regenerated. The committed configuration.md is byte-identical to current generator output (verified by running it and diffing at HEAD), so regeneration will produce exactly the intended diff and nothing else. docs/installation.md is neither generated nor CI-synced (not in tests/test_docs.py DOCS_FILES) — it is hand-edited directly.

Purpose: Close the documentation gap on hardware/device selection; users on Apple Silicon currently cannot tell whether embeddings use MPS, and SIF_N_GPU_LAYERS's CPU-by-default semantics are undocumented.
Output: Regenerated docs/configuration.md with a Device Selection note; two targeted additions to docs/installation.md; generator updated as the durable source.
</objective>

<execution_context>
@~/.claude/gsd-core/workflows/execute-plan.md
@~/.claude/gsd-core/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md
@scripts/generate_config_ref.py
@docs/configuration.md
@docs/installation.md
@src/sif/embedding/embedder.py
@src/sif/config/settings.py
@tests/test_docs.py
</context>

<tasks>

<task type="auto">
  <name>Task 1: Device Selection note in the config-reference generator; regenerate docs/configuration.md</name>
  <files>scripts/generate_config_ref.py, docs/configuration.md</files>
  <action>
Add a module-level helper `_append_device_selection_note(lines: list[str]) -> None` to scripts/generate_config_ref.py, placed with the other `_append_*` helpers (before `_append_options_tables`). In `_append_options_tables` (lines 172-198), inside the `for section_name, field_names in SECTIONS:` loop, after the field-row loop and immediately after the table for the section named "Embedding Model Settings" is emitted (before the trailing `lines.append("")` at line 198), call the helper conditionally on `section_name == "Embedding Model Settings"` so the note lands directly under that table, adjacent to the SIF_N_GPU_LAYERS row it clarifies.

The helper appends, matching the file's existing style (heading + prose + pipe table, blank lines between blocks):
1. A `#### Device Selection (CPU / GPU / MPS)` sub-heading and one intro sentence stating SIF exposes no device setting — each embedding backend picks its compute device automatically.
2. A three-row backend table (columns: Backend, Device behavior):
   - `modelscope` (default) and `sentence_transformers` — one row: device auto-detected at model load via torch: CUDA GPU if available, else Apple Metal (MPS) on arm64 macOS, else CPU; no configuration needed.
   - `gguf` — one row: CPU only by default; `SIF_N_GPU_LAYERS` defaults to 0 (all layers on CPU); values greater than 0 offload that many layers via llama.cpp's GPU support (Metal on Apple Silicon — llama.cpp's own path, not torch MPS).
   - `openai` — one row: embeddings computed by the remote API; local hardware unused.
3. A closing short paragraph: BM25/FTS5 keyword search and sqlite-vec vector search always run on CPU regardless of backend; MPS support ships in the torch wheel installed by the `embed` extra (inline-code `pip install "sif[embed]"` — do NOT put it in a fenced bash block); Apple's Neural Engine (ANE/NPU) is not used by any backend.

Constraints — WHY matters:
- Do NOT hand-edit docs/configuration.md. Run `python scripts/generate_config_ref.py` to produce it; the entire file content must be generator output (CI reruns the generator and fails on any divergence — .github/workflows/docs.yml:34-38).
- Do NOT add fenced code blocks of any kind in the note: docs/configuration.md is in tests/test_docs.py DOCS_FILES, and every fence gets extracted and validated; prose + table + inline code only.
- Do NOT edit src/sif/config/settings.py to reword the SIF_N_GPU_LAYERS Field description: the table cell renders live from that Field description (generator line 193), and this task is constrained to zero product-code changes — the 0=CPU / >0=Metal semantics go in the note prose instead.
- Keep every claim traceable to the verified findings in the objective; no benchmark numbers, no hardware-model specifics, no unverified wheel-flavor claims.
- Check the diff of docs/configuration.md after regenerating: it must contain ONLY the new note (the file was byte-in-sync with generator output at HEAD, planner-verified).

Then run `python scripts/generate_config_ref.py` (plain `python`, matching the Makefile docs-generate target), confirm the note appears, and rerun it once more to confirm stability.
  </action>
  <verify>
    <automated>python scripts/generate_config_ref.py && grep -q "Device Selection" docs/configuration.md && grep -q "MPS" docs/configuration.md && grep -q "llama.cpp" docs/configuration.md && cp docs/configuration.md .planning/tmp/cfg-check.md && python scripts/generate_config_ref.py && diff -q .planning/tmp/cfg-check.md docs/configuration.md && env -u FORCE_COLOR NO_COLOR=1 python -m pytest tests/test_docs.py -q</automated>
  </verify>
  <done>Regenerated docs/configuration.md carries the Device Selection note directly under the Embedding Model Settings table with all six verified facts (torch auto-detect order, no device setting, gguf default-CPU + SIF_N_GPU_LAYERS Metal offload-not-MPS, openai remote, BM25/sqlite-vec always CPU, no ANE/NPU, embed-extra MPS wheel); a second generator run is a no-op (diff clean); docs tests pass; the git diff of docs/configuration.md shows only the note; scripts/generate_config_ref.py contains the helper and the conditional call; nothing under src/ changed.</done>
</task>

<task type="auto">
  <name>Task 2: Hardware-acceleration notes in docs/installation.md (Embedding Support + macOS sections)</name>
  <files>docs/installation.md</files>
  <action>
Hand-edit docs/installation.md (not generated, not CI-synced — direct edit is correct here). Two insertions, prose only, no new fenced code blocks, matching the file's existing voice and heading levels:

1. Embedding Support section (currently lines 55-65): after the "This installs:" list (`sentence-transformers>=2.2.0`, `numpy>=1.24.0`), add a short paragraph: with this extra installed, the local embedding backends pick their compute device automatically at model load — CUDA GPU where torch has it, Apple Metal (MPS) on arm64 macOS, otherwise CPU; no extra setup or configuration is needed. Link plainly to the configuration guide for per-backend details using the file's existing link style: `[Configuration](configuration.md)`. Do NOT use a heading anchor in the link — the target heading lives in a regenerated file and anchors are brittle.

2. macOS section (currently lines 108-118): after the existing brew/pip3 fenced block, add a short "Hardware acceleration:" lead-in paragraph (bold run-in label matches the doc's **Cause**/**Solution** bold-label style used elsewhere in the file): on Apple Silicon Macs the modelscope and sentence_transformers backends automatically use the GPU via Metal (MPS); GGUF (llama.cpp) models run on CPU only unless `SIF_N_GPU_LAYERS` is set above 0, which enables llama.cpp Metal offload (distinct from MPS); point to [Configuration](configuration.md) for the full device-selection behavior.

Terminology discipline: "Metal (MPS)" for the torch backends, "llama.cpp Metal offload" for gguf — never imply SIF_N_GPU_LAYERS controls torch/MPS. Keep every claim inside the verified findings; no version numbers or hardware-model claims.
  </action>
  <verify>
    <automated>grep -q "MPS" docs/installation.md && grep -qi "metal" docs/installation.md && grep -q "SIF_N_GPU_LAYERS" docs/installation.md && grep -q "llama.cpp" docs/installation.md && git diff --quiet -- src/</automated>
  </verify>
  <done>Both installation.md sections explain device selection consistently with the configuration.md note: Embedding Support states automatic CUDA/MPS/CPU selection with the embed extra and links to configuration.md; the macOS section states MPS auto-use on Apple Silicon and the SIF_N_GPU_LAYERS > 0 llama.cpp Metal offload; no new fenced code blocks; no files under src/ modified (`git diff --quiet -- src/` exits 0).</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| (none) | Documentation-only change; no code paths, no user input, no network, no packages installed. `pip install "sif[embed]"` appears as inline prose, never executed. |

## STRIDE Threat Register

Threat IDs are unique within this quick task (prefix T-eev).

| Threat ID | Category | Component | Severity | Disposition | Mitigation Plan |
|-----------|----------|-----------|----------|-------------|-----------------|
| T-eev-01 | Tampering | docs/configuration.md, docs/installation.md | low | mitigate | Doc/code drift is the real risk here: configuration.md content is authored in scripts/generate_config_ref.py (never hand-edited) so CI's regeneration `git diff --exit-code` gate (.github/workflows/docs.yml:34-38) enforces sync; every factual claim is pinned to code locations verified this session (embedder.py:59-64, 129-165, 312-315; settings.py:65-69). |
| T-eev-02 | Information Disclosure | new doc prose | low | mitigate | No unverified claims: forbid benchmark numbers, hardware-model specifics, and wheel-flavor speculation in both task actions; content restricted to the six verified findings. |

No package-manager installs are planned, so no `T-eev-SC` package-legitimacy row applies.
</threat_model>

<verification>
1. `python scripts/generate_config_ref.py && git diff docs/configuration.md` — diff shows only the Device Selection note (file was byte-in-sync at HEAD).
2. `env -u FORCE_COLOR NO_COLOR=1 python -m pytest tests/test_docs.py -q` — docs validation green (configuration.md is in DOCS_FILES; no new fenced blocks added anywhere).
3. `ruff check scripts/generate_config_ref.py` — generator edit stays lint-clean (scripts/ is outside the standard `ruff check src tests` suite, so check it explicitly).
4. `git diff --stat -- src/ tests/` — empty; zero product-code changes per task constraint.
5. Read docs/installation.md and docs/configuration.md end-to-end — terminology consistent across both files: torch backends = "Metal (MPS)"; gguf = "llama.cpp Metal offload", never conflated with MPS.
</verification>

<success_criteria>
- A user reading only docs/configuration.md can answer: which device will my backend use, why doesn't SIF_N_GPU_LAYERS affect modelscope/sentence_transformers, and what does SIF_N_GPU_LAYERS > 0 actually enable.
- A user reading only docs/installation.md knows GPU acceleration is automatic on Apple Silicon/CUDA with the embed extra, and where to look for details.
- CI Docs Validation workflow passes: generator rerun produces zero diff on the committed configuration.md.
- Docs test suite green; no changes under src/ or tests/.
</success_criteria>

<output>
Create `.planning/quick/261105-eev-document-embedding-hardware-device-selec/261105-eev-SUMMARY.md` when done
</output>
