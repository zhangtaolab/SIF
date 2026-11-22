---
phase: quick-261122-leb
plan: 01
subsystem: docs
tags: [documentation, migration, backup, embedding-cache, model-cache, mcp, watch]

# Dependency graph
requires: []
provides:
  - Machine-to-machine migration runbook covering index export/restore, embedding and model caches, embedder identity, source-path handling, configuration, MCP/watch recreation, verification, and troubleshooting
  - Guide registered in the mkdocs User Guide nav and the docs code-block test suite
affects: [docs navigation, docs regression gate]

# Actuals — tasks and atomic commits realized for the quick task.
actuals:
  tokens: 5500
  tasks: 2
  commits: 3

plan_head_before: 1cb2dbc753908d81605e71f82f819a6e4d7019c4
plan_head_after: 0d8400a563b949827a66331f937102f395a7a3d9

tech-stack:
  added: []
  patterns: []

key-files:
  created:
    - docs/machine-migration.md
  modified:
    - mkdocs.yml
    - tests/test_docs.py

key-decisions:
  - "Export via `sif index backup` (SQLite online backup API) instead of a raw `.db` copy: one verified, sidecar-free snapshot with integrity_check and 0600 permissions"
  - "Keep the machine A model identity (name, type, dimension, api_base, prompt overrides) because the schema `FLOAT[n]` width and stored vectors are identity-bound; document both the hard dimension-mismatch failure and the same-width identity warning with `sif index embed --force` as the remedy"
  - "Offer three source-path routes: same layout (no-op update), moved root (supported remove/add/update/embed), and an advanced same-OS prefix rewrite that preserves document IDs and vectors; cross-OS rewrite is documented as unsafe"
  - "Document five never-copy sidecars (lock, watch/mcp PID, WAL, SHM) and explain that kernel lock state and daemon ownership do not survive the move"

requirements-completed: [QUICK-MACHINE-MIGRATION-GUIDE]

# Metrics
duration: 33min
completed: 2026-11-22
status: complete
---

# Quick Task 261122-leb: Machine-to-Machine Migration Guide Summary

**A complete, CLI-verified runbook now moves an installed SIF from machine A to machine B, covering the verified index export, both caches, embedder identity, source-path relocation, configuration/MCP/watch recreation, and a verification checklist.**

## Performance

- **Duration:** 33 min
- **Started:** 2026-11-22T07:31:51Z
- **Completed:** 2026-11-22T08:04:42Z
- **Tasks:** 2/2
- **Commits:** 3

## Accomplishments

- Created `docs/machine-migration.md` (575 lines) with 13 ordered H2 sections: What Moves, Before You Start, Export the Index, Do Not Copy These Files, Install on B, Restore the Index, Preserve the Embedder Identity, Move or Rebuild the Caches, Handle Source Paths, Recreate Configuration and Integrations, Verify the Migration, Troubleshooting, and Related Documentation.
- Registered the guide under the mkdocs `User Guide` nav and in `tests/test_docs.py` `DOCS_FILES`, so its shell/JSON/Python code blocks are enforced by the existing docs gate.
- Every documented `sif` command was checked against the live CLI; the `sif models status --json` example matches the real payload shape.

## Task Commits

1. **Task 1 — write the guide:** `027670d` — `docs(quick-261122-leb): add machine-to-machine migration runbook`
2. **Task 2 — register and validate:** `6b40903` — `docs(quick-261122-leb): register migration guide in nav and docs test suite`
3. **Verification pass — corrections:** `0d8400a` — `docs(quick-261122-leb): verify migration runbook against live CLI`

## Files Created/Modified

- `docs/machine-migration.md` — new migration runbook
- `mkdocs.yml` — one nav line under User Guide
- `tests/test_docs.py` — one `DOCS_FILES` entry

## Decisions & Deviations

- **Protected-branch commit gate:** the executor completed and validated both tasks but refused to commit because HEAD was on `main`. The orchestrator surfaced the choice; the user selected a new branch. Work was committed on `docs/machine-migration` (branched from the plan commit), leaving `main` untouched.
- **Accuracy corrections after execution:** the orchestrator tightened five details against the code — the backup lock behavior (`SIF_LOCK_WAIT_TIMEOUT`, online backup consistency), stale lock/PID artifact rationale (kernel lock state and daemon ownership do not transfer), the sentence-transformers Hugging Face cache location, SQL parameter binding instructions for the advanced prefix rewrite, and the stale-artifact troubleshooting row.
- **Dynamic verification on a live temp install:** the orchestrator exercised the runbook against `sif 1.2.2` with a throwaway DB and cache, then corrected five more wording/accuracy points found by that pass (vacuum contention wording, MCP client/service path claim, identity-status values, fingerprint non-equality, and cross-device floating-point nuance).

## Verification

- `pytest tests/test_docs.py -q --no-cov` → 21 passed
- `ruff check src tests` → All checks passed
- `ruff format --check src tests` → 237 files already formatted
- Full suite (executor baseline before orchestrator edits) → 3260 passed, 1 skipped, 95.12% coverage
- Generator-owned docs unchanged (executor gate): `docs/cli-reference.md` and `docs/configuration.md` byte-identical
- All 16 relative links and 4 section anchors resolve; all 15 mkdocs nav targets exist
- Live smoke pass (temp `SIF_DB_PATH`/`SIF_CACHE_DIR`, BM25 + local 1024-dim sentence-transformer):
  - `sif index backup` produces a 0600, `integrity_check`-clean single file; default path, existing-target refusal, and DB/lock collision refusal all match the guide
  - Restoring the backup to a new path preserves counts, BM25 search, vector search (`0.4709`/`0.3761`), hybrid search, and `Vector lag 0`
  - Same-layout `sif index update` reports unchanged; missing root warns and preserves both documents; `--no-refresh` skips the drift walk
  - Moved-root `collection remove`/`add`/`update` route re-indexes both documents
  - Advanced same-OS prefix rewrite (bound `.parameter set` SQL) updates collections/documents/path contexts, passes FTS5 external-content `integrity-check`, and leaves `sif index update` unchanged
  - `SIF_EMBEDDING_DIM=768` on a 1024-dim DB raises the documented dimension-mismatch error on `sif status`; a same-width different model reports `identity.status: mismatch`
  - `SIF_LOCK_WAIT_TIMEOUT=1` under a held flock prints the wait notice and completes instead of failing
  - `.env` in the invocation CWD resolves the restored DB; a stale `<db>.watch.pid` is cleaned; `embeddings_cache.db` keys match `(content_hash, model_id)` with revision/prompt suffixes
  - `sif watch --stop` and `sif mcp daemon --stop` report not running; `sif index --help` confirms there is no restore command
- `mkdocs build` could not run because `mkdocs-minify-plugin` is absent from this environment; nav targets, links, and anchors were validated programmatically instead.
