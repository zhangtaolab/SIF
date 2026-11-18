# Phase 24: Tuning + Models UX + Install Docs - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-11-16
**Phase:** 24-tuning-models-ux-install-docs
**Areas discussed:** Chunk sweep, Title breadcrumb, Models UX, Install docs, Evaluation discipline

---

> **Mode:** `--auto` (auto-advance chain). All gray areas were auto-selected; every
> question used the recommended option without an interactive prompt.

## Chunk sweep (QUAL-02)

| Option | Description | Selected |
|--------|-------------|----------|
| Isolated arms, full re-chunk + re-embed, fixed Qwen3 | One DB per chunk config; small grid including 512/128; Phase 18 gate | ✓ |
| Reuse one index and re-chunk in place | Risks mixed vector spaces and contaminated arms | |
| In-sample sweep without a gate | Contradicts the defaults rule | |

**User's choice:** Isolated arms; fixed Qwen3 and Phase 23 curated corpus; small grid including the 512/128 default; per-arm embed cost; Phase 18 gate.
**Notes:** N=56 means a 0.01 win is inadmissible; the artifact records the limitation.

---

## Title breadcrumb (QUAL-03)

| Option | Description | Selected |
|--------|-------------|----------|
| One breadcrumb arm, embed-text only, per-leg ablation | Heading path prepended to chunk embed text; duplicate check vs title FTS | ✓ |
| Change stored content and title FTS | Duplicates the title signal and changes ranking contracts | |
| Skip the experiment | Leaves QUAL-03 unmet | |

**User's choice:** One breadcrumb arm; embed text only; per-leg ablation; duplicate-signal check; no default without a held-out win.
**Notes:** A no-win is recorded with numbers.

---

## Models UX (MODELS-01/02)

| Option | Description | Selected |
|--------|-------------|----------|
| `sif models pull/status`; `sif pull` deprecated alias | Deterministic pull, canonical cache dir, manifest/hash check, identity-aware status | ✓ |
| Keep only `sif pull` and add flags | Does not meet MODELS-01/02's command surface | |
| Download at first use only | Non-deterministic and non-inspectable | |

**User's choice:** New `sif models` group; cache-honest deterministic pull; status with identity/backend/dims; non-TTY silence; correct `DEFAULT_MODELS` to Qwen3-0.6B.
**Notes:** No new runtime deps.

---

## Install docs (DOCS-01)

| Option | Description | Selected |
|--------|-------------|----------|
| uv-first + degradation matrix + client snippets | Primary `uv tool install 'docsif[embed]'`, CPU torch index, llama-cpp, honest degradation | ✓ |
| pip-first minimal README | Rejected: the milestone requires uv-first and platform-correct installs | |
| Generated docs only | Install docs are hand-maintained; generator owns CLI/config references | |

**User's choice:** uv-first docs; CPU torch index; llama-cpp indexes; degradation matrix; client snippets; `make docs-generate` clean diff.
**Notes:** `docs/cli-reference.md`/`docs/configuration.md` remain generator-owned.

---

## Evaluation discipline

| Option | Description | Selected |
|--------|-------------|----------|
| Phase 18 gate for every default | Paired bootstrap CI + 0.01 tie rule + strict 1/N floor; rejections recorded | ✓ |
| Ship the best in-sample arm | Contradicts the locked defaults rule | |
| Defer all tuning | Leaves QUAL-02/03 unmet | |

**User's choice:** Reuse the Phase 18 instrument and gate; no in-sample default changes; record rejections with numbers.
**Notes:** The curated subset's N=56 limitation is recorded.

## Claude's Discretion

- Exact chunk grid (within the small-grid + include-default constraint), breadcrumb rendering, artifact schema, `models` argument spelling/columns, scratch-dir layout.

## Deferred Ideas

- GGUF Harrier (MODEL-F1), bge-reranker-v2-m3, multi-embedder serving, full Windows, non-Markdown formats.
