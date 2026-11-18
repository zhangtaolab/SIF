# Phase 23: Harrier Gated Evaluation - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-11-16
**Phase:** 23-harrier-gated-evaluation
**Areas discussed:** Arm construction and isolation, Corpus/query set/splits, Verdict and default-switch rule, Deliverable and instrumentation, Claude's discretion

---

> **Mode:** `--auto` (auto-advance chain). All gray areas were auto-selected; every
> question used the recommended option without an interactive prompt.

## Arm construction and isolation

| Option | Description | Selected |
|--------|-------------|----------|
| Two isolated file-backed indexes | One DB per arm, same corpus/chunker, identity recorded per arm | ✓ |
| One index, reset vectors between arms | Re-embed in place, deleting vectors and rewriting identity | |
| Two indexes sharing one DB | Rejected: one vec0 table cannot hold two vector spaces | |

**User's choice:** Two isolated indexes; full per-arm re-embed via the Phase 21 streaming writer; Harrier native `sentence-transformers` with the known-model prompt scheme; Qwen3 default untouched.
**Notes:** Scratch DBs are disposable; the committed artifact is the verdict, not the multi-GB arm DBs.

---

## Corpus, query set, and splits

| Option | Description | Selected |
|--------|-------------|----------|
| Personal corpus + Phase 18 instrument | `sif eval --personal` on arm A, `--compare` on arm B; Phase 18 legs/splits/gate verbatim | ✓ |
| New synthetic EN+ZH benchmark | Would create a second instrument and a non-comparable baseline | |
| Committed fixture corpus only | Not representative of the user's knowledge base | |

**User's choice:** Personal corpus, Phase 18 D-01..D-08 verbatim, saved-run comparison across model identities; EN+ZH adequacy required before a verdict.
**Notes:** `--compare` already warns on model mismatch and refuses only on a corpus-fingerprint mismatch; the verdict artifact records the full identity because the saved `model` dict lacks prompt scheme/revision.

---

## Verdict and default-switch rule

| Option | Description | Selected |
|--------|-------------|----------|
| Two-sided EN+ZH gate | Overall held-out CI excludes 0 and Δ ≥ 0.01, and neither language Δ < −0.01 | ✓ |
| Overall-only gate | Could switch on an EN win while ZH regresses | |
| Per-language "any win" gate | Weakest evidence bar; could switch on one language | |

**User's choice:** Two-sided gate; a no-win is recorded with numbers as a rejection; a pass flips the default in-phase and keeps Qwen3 selectable/byte-identical.
**Notes:** This is the operational reading of "EN+ZH held-out win beyond the 0.01 tie rule"; `models pull` registry corrections stay in Phase 24.

---

## Deliverable and instrumentation

| Option | Description | Selected |
|--------|-------------|----------|
| Existing `sif eval` + `--compare` + runbook script | No new public CLI surface; stdlib-only runbook writes the verdict artifact | ✓ |
| New `sif eval --embedder-ab` command | Adds a public command and docs-generate surface for a one-off evaluation | |
| Ad-hoc shell commands only | Not reproducible/auditable | |

**User's choice:** No new CLI command; a reproducible script under `scripts/` plus the committed verdict artifact; tests cover gate math and orchestration with stub embedders.
**Notes:** If a missing comparison capability emerges, prefer an additive flag over a new command.

---

## Claude's Discretion

- Scratch directory naming/cleanup, verdict JSON schema, and revision persistence.
- Bootstrap resample count/seed (reuse Phase 18).
- Whether to run a BM25-only control (recommended: no).
- Exact verdict rendering following `bench`/`eval` conventions.

## Deferred Ideas

- GGUF Harrier arm (MODEL-F1) — conditional follow-up.
- bge-reranker-v2-m3 — out of scope.
- Chunk-size/overlap and title-breadcrumb sweeps — Phase 24.
- Multi-embedder simultaneous serving / per-collection identity — not scoped.
- `models pull` / `models status` / install docs — Phase 24.
