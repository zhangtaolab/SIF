---
phase: "21"
slug: "scale-maintenance-embedder-identity"
# status lifecycle: draft (seeded by plan-phase) → validated (set by validate-phase §6)
# audit-milestone §5.5 distinguishes NOT-VALIDATED (draft) from PARTIAL (validated + nyquist_compliant: false) (#2117)
status: validated
nyquist_compliant: true
wave_0_complete: true
created: "2026-11-15"
validated: "2026-11-18"
---

# Phase 21 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.
> Task IDs resolved from the executed plans; audited 2026-11-18 with every automated command green.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (existing; pytest-cov) |
| **Config file** | `pyproject.toml` (`testpaths = ["tests"]`, coverage `addopts`, `fail_under = 90`) |
| **Quick run command** | `env -u FORCE_COLOR NO_COLOR=1 pytest tests/unit/<area>/test_<file>.py -x --no-cov` |
| **Full suite command** | `pytest` (plus `ruff check src tests`, `ruff format --check src tests`, `ty check src/sif`) |
| **Estimated runtime** | ~205 s full suite (measured 2026-11-18: 3233 passed / 1 skipped, 95.03% coverage); 9.3 s for the 671-test targeted set |

---

## Sampling Rate

- **After every task commit:** Run the narrow file command(s) named in the task's `<verify>`, plus `ruff check` / `ruff format --check`.
- **After every plan wave:** Run `pytest` (full suite) + `ty check src/sif`.
- **Before `/gsd-verify-work`:** Full suite must be green at `fail_under=90`, `make docs-generate` diff must be clean, and the D-19 byte-identical goldens must reproduce.
- **Max feedback latency:** ~205 seconds (full suite); ≤ 10 seconds for the per-task narrow command (measured 2026-11-18).

---

## Per-Task Verification Map

Task IDs resolved from the executed plans; requirement-level map audited 2026-11-18:

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 21-06 T1 | 21-06 | 5 | SCALE-01 | T-21-01 | Vacuum takes flock, checkpoints, refuses low disk, surfaces busy as retryable, never corrupts | unit/integration | `pytest tests/unit/database/test_maintenance.py -x --no-cov` | ✅ | ✅ green |
| 21-06 T1 | 21-06 | 5 | SCALE-01 | T-21-01 | CLI prints before/after/reclaimed; no target arguments accepted | CLI | `pytest tests/unit/cli/test_index.py -x -k vacuum --no-cov` | ✅ | ✅ green |
| 21-06 T2 | 21-06 | 5 | SCALE-02 | T-21-02 | Backup creates a verified copy via the online API; refuses existing/symlink/DB targets; 0600 | unit/integration | `pytest tests/unit/database/test_maintenance.py -x -k backup --no-cov` | ✅ | ✅ green |
| 21-06 T2 | 21-06 | 5 | SCALE-02 | T-21-02 | Backup under live writes contains committed rows and passes `integrity_check` | integration | `pytest tests/integration/test_maintenance.py -x -k backup --no-cov` | ✅ | ✅ green |
| 21-05 T1 | 21-05 | 4 | SCALE-03 | T-21-03 | Embedding runs outside any transaction (`conn.in_transaction is False`) and commits per document | unit | `pytest tests/unit/indexing/test_embed_writer.py -x --no-cov` | ✅ | ✅ green |
| 21-05 T2 | 21-05 | 4 | SCALE-03 | T-21-04 | Garbage-vector sanity (count/NaN/Inf/dim/norm) aborts without persisting and never poisons the cache | unit | `pytest tests/unit/indexing/test_embed_writer.py -x -k sanity --no-cov` | ✅ | ✅ green |
| 21-05 T2 | 21-05 | 4 | SCALE-03 | T-21-03 | Mid-run failure is durable and resumable; a re-run embeds exactly the remainder; CR-02 report/exit code preserved | integration | `pytest tests/integration/test_embed_idempotency.py -x --no-cov` | ✅ | ✅ green |
| 21-02 T2 | 21-02 | 1 | CORR-06 | — | Shadow backfill/legacy upgrade/reconcile/idempotence/orphan exclusion | unit | `pytest tests/unit/database/test_embedded_documents.py -x --no-cov` | ✅ | ✅ green |
| 21-02 T3 | 21-02 | 1 | CORR-06 | — | Staleness parity: same markers, display gate, None degradation; no vec0 scan on the search path | unit | `pytest tests/unit/search/test_staleness.py -x --no-cov` | ✅ | ✅ green |
| 21-03 T1/T2 | 21-03 | 2 | CORR-06 | — | Contexts cache invalidation (repository write, other-connection commit), verbatim legacy fixture, no second contexts SELECT | unit | `pytest tests/unit/search/test_context_attach.py -x --no-cov` | ✅ | ✅ green |
| 21-02 T3 | 21-02 | 1 | CORR-06 | — | `sif status` vector-lag text byte-identical on a real DB | CLI | `pytest tests/unit/cli/test_main.py tests/unit/cli/test_status.py -x --no-cov` | ✅ | ✅ green |
| 21-01 T1 | 21-01 | 1 | EMB-01 | T-21-05 | Fingerprint determinism; same-dim swap embed fails / search warns+marks; unknown-tolerance; GGUF file-hash detects bytes | unit | `pytest tests/unit/embedding/test_identity.py -x --no-cov` | ✅ | ✅ green |
| 21-08 T1 + 21-07 T1 | 21-08,21-07 | 2,6 | EMB-01 | T-21-05 | Legacy DB assumed write + one warning + shadow backfill; `--force` certifies; partial force does not | integration/CLI | `pytest tests/unit/cli/test_index.py -x -k "legacy or certify" --no-cov` | ✅ | ✅ green |
| 21-08 T1 | 21-08 | 2 | EMB-01 | T-21-05 | The three dimension guards share one read; existing error messages preserved | unit | `pytest tests/unit/database/test_schema.py tests/unit/indexing/test_watcher.py -x -k dimension --no-cov` | ✅ | ✅ green |
| 21-08 T2 | 21-08 | 2 | EMB-01 | T-21-05 | MCP search mismatch warns once + marks metadata; BM25 degrade does not | MCP | `pytest tests/unit/mcp/test_backend.py -x -k identity --no-cov` | ✅ | ✅ green |
| 21-01 T2/T3 | 21-01 | 1 | EMB-02 | — | ST `embed_query` passes `prompt_name`; no prompt calls `encode` exactly as today; cache q/d/revision buckets isolate | unit | `pytest tests/unit/embedding/test_embedder_impl.py tests/unit/embedding/test_manager.py -x --no-cov` | ✅ | ✅ green |
| 21-04 T1/T2 | 21-04 | 3 | EMB-02 | — | Pipeline query/HyDE/expansion use the query role; doubles fall back to `embed` | unit | `pytest tests/unit/search/test_hybrid.py tests/unit/search/test_suggest.py -x --no-cov` | ✅ | ✅ green |
| 21-07 T1 | 21-07 | 6 | D-19 (baseline) | — | Default ModelScope Qwen3 path byte-identical: bucket string unchanged, no-prompt calls identical, SC1/bench goldens reproduce | unit/snapshot | `pytest tests/unit/search/test_bench_snapshot.py tests/unit/search/test_hybrid.py -x --no-cov` | ✅ | ✅ green |
| 21-02 T1/T2 | 21-02 | 1 | D-19 (baseline) | — | Only new writes on a fresh embed are the identity row, shadow rows, and markers | unit | `pytest tests/unit/database/test_embedded_documents.py -x -k fresh --no-cov` | ✅ | ✅ green |
| 21-01…21-08 | all | 1–6 | ALL | T-21-SC | Lint/format/type/docs gates | static/docs | `ruff check src tests && ruff format --check src tests && ty check src/sif && make docs-generate && git diff --exit-code docs/cli-reference.md docs/configuration.md` | ✅ | ✅ green |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

**Guard inventory (measured 2026-11-18):** 671 targeted tests collected and green in 9.31 s across the 19 files above; full suite 3233 passed / 1 skipped @ 95.03% coverage; ruff/format/ty green; docs generators produce no diff.

---

## Wave 0 Requirements

- [x] `tests/unit/embedding/test_identity.py` — fingerprint/stability/mode matrix/legacy/certify/GGUF hash/revision.
- [x] `tests/unit/database/test_embedded_documents.py` — DDL, fresh marker, legacy backfill, idempotence, drop/recreate repair, reconcile, orphan exclusion, parity helper.
- [x] `tests/unit/database/test_maintenance.py` — vacuum/backup/disk/busy/integrity.
- [x] `tests/unit/indexing/test_embed_writer.py` — transaction flags, per-doc failure, sanity matrix, shadow/identity writes, empty chunks.
- [x] `tests/integration/test_maintenance.py` — vacuum under a concurrent reader/writer, backup under live writes.
- [x] Shared helpers: a legacy-index builder, an identity A/B fixture, a garbage-vector fake manager, a shadow-parity assertion, and `reset_identity_state()`/`reset_context_cache()` autouse fixtures in `tests/conftest.py`.
- [x] Test migration: raw vec0 writers, fresh-DB `index_meta` assertions, and manager/embed call-shape mocks across the named test files.
- [x] Framework install: none — pytest/cov/ty already installed.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions | Verified |
|----------|-------------|------------|-------------------|----------|
| Harrier `prompts` dict exposes `web_search_query` and a 1024-dim vector | EMB-02 (consumer: Phase 23) | The model is not part of this phase's test environment; the exact prompt key is verified when Phase 23 loads it | In an isolated venv: `SentenceTransformer("microsoft/harrier-oss-v1-0.6b")`, assert `"web_search_query" in model.prompts` and `model.get_sentence_embedding_dimension() == 1024`, then encode one query with the prompt | ✅ verified in Phase 23's real two-arm run: both arm identities `source: verified` at 1024 dims, Harrier records `query_prompt: web_search_query` and no document prompt (23-04-SUMMARY) |
| GGUF file-hash cost on the real model | EMB-01 | The 1.19 GB model is not committed to the repo; the research measured ≈0.43 s but CI fixtures use tiny files | Time `hashlib.sha256` over a real GGUF once and confirm the cost is acceptable at embed start | ✅ research measured ≈0.43 s for the 1.19 GB file (21-RESEARCH); identity-layer same-path/different-bytes detection is automated via a stubbed `llama_cpp` (21-07-SUMMARY) |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 240s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** approved 2026-11-18 — 20/20 requirement rows covered, 671/671 targeted tests green, 0 gaps, 0 escalated.

## Validation Audit 2026-11-18

| Metric | Count |
|---|---|
| Gaps found | 0 |
| Resolved | 0 |
| Escalated | 0 |
