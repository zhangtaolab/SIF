---
phase: "21"
slug: "scale-maintenance-embedder-identity"
# status lifecycle: draft (seeded by plan-phase) → validated (set by validate-phase §6)
# audit-milestone §5.5 distinguishes NOT-VALIDATED (draft) from PARTIAL (validated + nyquist_compliant: false) (#2117)
status: draft
nyquist_compliant: false
wave_0_complete: false
created: "2026-11-15"
---

# Phase 21 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (existing; pytest-cov) |
| **Config file** | `pyproject.toml` (`testpaths = ["tests"]`, coverage `addopts`, `fail_under = 90`) |
| **Quick run command** | `env -u FORCE_COLOR NO_COLOR=1 pytest tests/unit/<area>/test_<file>.py -x --no-cov` |
| **Full suite command** | `pytest` (plus `ruff check src tests`, `ruff format --check src tests`, `ty check src/sif`) |
| **Estimated runtime** | ~240 seconds (full suite; the phase-20 suite was 2482 tests) |

---

## Sampling Rate

- **After every task commit:** Run the narrow file command(s) named in the task's `<verify>`, plus `ruff check` / `ruff format --check`.
- **After every plan wave:** Run `pytest` (full suite) + `ty check src/sif`.
- **Before `/gsd-verify-work`:** Full suite must be green at `fail_under=90`, `make docs-generate` diff must be clean, and the D-19 byte-identical goldens must reproduce.
- **Max feedback latency:** ~240 seconds (full suite); ≤ 60 seconds for the per-task narrow command.

---

## Per-Task Verification Map

Task IDs are assigned by the planner; this map is requirement-level until PLAN.md files exist.

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| TBD | TBD | — | SCALE-01 | T-21-01 | Vacuum takes flock, checkpoints, refuses low disk, surfaces busy as retryable, never corrupts | unit/integration | `env -u FORCE_COLOR NO_COLOR=1 pytest tests/unit/database/test_maintenance.py -x --no-cov` | ❌ W0 | ⬜ pending |
| TBD | TBD | — | SCALE-01 | T-21-01 | CLI prints before/after/reclaimed; no target arguments accepted | CLI | `env -u FORCE_COLOR NO_COLOR=1 pytest tests/unit/cli/test_index.py -x -k vacuum --no-cov` | ❌ W0 | ⬜ pending |
| TBD | TBD | — | SCALE-02 | T-21-02 | Backup creates a verified copy via the online API; refuses existing/symlink/DB targets; 0600 | unit/integration | `env -u FORCE_COLOR NO_COLOR=1 pytest tests/unit/database/test_maintenance.py -x -k backup --no-cov` | ❌ W0 | ⬜ pending |
| TBD | TBD | — | SCALE-02 | T-21-02 | Backup under live writes contains committed rows and passes `integrity_check` | integration | `env -u FORCE_COLOR NO_COLOR=1 pytest tests/integration/test_maintenance.py -x -k backup --no-cov` | ❌ W0 | ⬜ pending |
| TBD | TBD | — | SCALE-03 | T-21-03 | Embedding runs outside any transaction (`conn.in_transaction is False`) and commits per document | unit | `env -u FORCE_COLOR NO_COLOR=1 pytest tests/unit/indexing/test_embed_writer.py -x --no-cov` | ❌ W0 | ⬜ pending |
| TBD | TBD | — | SCALE-03 | T-21-04 | Garbage-vector sanity (count/NaN/Inf/dim/norm) aborts without persisting and never poisons the cache | unit | `env -u FORCE_COLOR NO_COLOR=1 pytest tests/unit/indexing/test_embed_writer.py -x -k sanity --no-cov` | ❌ W0 | ⬜ pending |
| TBD | TBD | — | SCALE-03 | T-21-03 | Mid-run failure is durable and resumable; a re-run embeds exactly the remainder; CR-02 report/exit code preserved | integration | `env -u FORCE_COLOR NO_COLOR=1 pytest tests/integration/test_embed_idempotency.py -x --no-cov` | ✅ (update) | ⬜ pending |
| TBD | TBD | — | CORR-06 | — | Shadow backfill/legacy upgrade/reconcile/idempotence/orphan exclusion | unit | `env -u FORCE_COLOR NO_COLOR=1 pytest tests/unit/database/test_embedded_documents.py -x --no-cov` | ❌ W0 | ⬜ pending |
| TBD | TBD | — | CORR-06 | — | Staleness parity: same markers, display gate, None degradation; no vec0 scan on the search path | unit | `env -u FORCE_COLOR NO_COLOR=1 pytest tests/unit/search/test_staleness.py -x --no-cov` | ✅ (update) | ⬜ pending |
| TBD | TBD | — | CORR-06 | — | Contexts cache invalidation (repository write, other-connection commit), verbatim legacy fixture, no second contexts SELECT | unit | `env -u FORCE_COLOR NO_COLOR=1 pytest tests/unit/search/test_context_attach.py -x --no-cov` | ✅ (extend) | ⬜ pending |
| TBD | TBD | — | CORR-06 | — | `sif status` vector-lag text byte-identical on a real DB | CLI | `env -u FORCE_COLOR NO_COLOR=1 pytest tests/unit/cli/test_main.py tests/unit/cli/test_status.py -x --no-cov` | ✅ | ⬜ pending |
| TBD | TBD | — | EMB-01 | T-21-05 | Fingerprint determinism; same-dim swap embed fails / search warns+marks; unknown-tolerance; GGUF file-hash detects bytes | unit | `env -u FORCE_COLOR NO_COLOR=1 pytest tests/unit/embedding/test_identity.py -x --no-cov` | ❌ W0 | ⬜ pending |
| TBD | TBD | — | EMB-01 | T-21-05 | Legacy DB assumed write + one warning + shadow backfill; `--force` certifies; partial force does not | integration/CLI | `env -u FORCE_COLOR NO_COLOR=1 pytest tests/unit/cli/test_index.py -x -k "legacy or certify" --no-cov` | ❌ W0 | ⬜ pending |
| TBD | TBD | — | EMB-01 | T-21-05 | The three dimension guards share one read; existing error messages preserved | unit | `env -u FORCE_COLOR NO_COLOR=1 pytest tests/unit/database/test_schema.py tests/unit/indexing/test_watcher.py -x -k dimension --no-cov` | ✅ (update) | ⬜ pending |
| TBD | TBD | — | EMB-01 | T-21-05 | MCP search mismatch warns once + marks metadata; BM25 degrade does not | MCP | `env -u FORCE_COLOR NO_COLOR=1 pytest tests/unit/mcp/test_backend.py -x -k identity --no-cov` | ❌ W0 | ⬜ pending |
| TBD | TBD | — | EMB-02 | — | ST `embed_query` passes `prompt_name`; no prompt calls `encode` exactly as today; cache q/d/revision buckets isolate | unit | `env -u FORCE_COLOR NO_COLOR=1 pytest tests/unit/embedding/test_embedder_impl.py tests/unit/embedding/test_manager.py -x --no-cov` | ✅ (extend) | ⬜ pending |
| TBD | TBD | — | EMB-02 | — | Pipeline query/HyDE/expansion use the query role; doubles fall back to `embed` | unit | `env -u FORCE_COLOR NO_COLOR=1 pytest tests/unit/search/test_hybrid.py tests/unit/search/test_suggest.py -x --no-cov` | ✅ (extend) | ⬜ pending |
| TBD | TBD | — | D-19 (baseline) | — | Default ModelScope Qwen3 path byte-identical: bucket string unchanged, no-prompt calls identical, SC1/bench goldens reproduce | unit/snapshot | `env -u FORCE_COLOR NO_COLOR=1 pytest tests/unit/search/test_bench_snapshot.py tests/unit/search/test_hybrid.py -x --no-cov` | ✅ | ⬜ pending |
| TBD | TBD | — | D-19 (baseline) | — | Only new writes on a fresh embed are the identity row, shadow rows, and markers | unit | `env -u FORCE_COLOR NO_COLOR=1 pytest tests/unit/database/test_embedded_documents.py -x -k fresh --no-cov` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/unit/embedding/test_identity.py` — fingerprint/stability/mode matrix/legacy/certify/GGUF hash/revision.
- [ ] `tests/unit/database/test_embedded_documents.py` — DDL, fresh marker, legacy backfill, idempotence, drop/recreate repair, reconcile, orphan exclusion, parity helper.
- [ ] `tests/unit/database/test_maintenance.py` — vacuum/backup/disk/busy/integrity.
- [ ] `tests/unit/indexing/test_embed_writer.py` — transaction flags, per-doc failure, sanity matrix, shadow/identity writes, empty chunks.
- [ ] `tests/integration/test_maintenance.py` — vacuum under a concurrent reader/writer, backup under live writes.
- [ ] Shared helpers: a legacy-index builder, an identity A/B fixture, a garbage-vector fake manager, a shadow-parity assertion, and `reset_identity_state()`/`reset_context_cache()` autouse fixtures in `tests/conftest.py`.
- [ ] Test migration: raw vec0 writers (`tests/unit/search/test_hybrid.py:565`, `tests/unit/search/test_staleness.py`, `tests/unit/cli/test_eval.py:75`), fresh-DB `index_meta` assertions (`tests/unit/database/test_schema.py:604`), and manager/embed call-shape mocks (`tests/unit/cli/test_index.py`, `tests/integration/test_embed_idempotency.py`, `tests/unit/indexing/test_watcher.py`, `tests/unit/cli/test_watch_cmd.py`, `tests/unit/cli/test_search.py`).
- [ ] Framework install: none — pytest/cov/ty already installed.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Harrier `prompts` dict exposes `web_search_query` and a 1024-dim vector | EMB-02 (consumer: Phase 23) | The model is not part of this phase's test environment; the exact prompt key is verified when Phase 23 loads it | In an isolated venv: `SentenceTransformer("microsoft/harrier-oss-v1-0.6b")`, assert `"web_search_query" in model.prompts` and `model.get_sentence_embedding_dimension() == 1024`, then encode one query with the prompt |
| GGUF file-hash cost on the real model | EMB-01 | The 1.19 GB model is not committed to the repo; the research measured ≈0.43 s but CI fixtures use tiny files | Time `hashlib.sha256` over a real GGUF once and confirm the cost is acceptable at embed start |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 240s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
