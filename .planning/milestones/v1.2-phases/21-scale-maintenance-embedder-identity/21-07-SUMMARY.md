---
phase: 21-scale-maintenance-embedder-identity
plan: 07
subsystem: testing
tags:
  [
    byte-identical-baseline,
    embedder-identity,
    legacy-assumed,
    certification,
    gguf-file-hash,
    streaming-embed,
    garbage-vectors,
    failure-durability,
    maintenance-concurrency,
    docs-generate,
    phase-gate,
    d-19,
  ]

# Dependency graph
requires:
  - phase: 21-scale-maintenance-embedder-identity
    plan: 01
    provides: "identity module, prompt scheme, role-aware manager/embedders, cache buckets"
  - phase: 21-scale-maintenance-embedder-identity
    plan: 02
    provides: "transactional embedded_documents shadow, marker backfill, reconcile helper"
  - phase: 21-scale-maintenance-embedder-identity
    plan: 03
    provides: "cached context map and the vectors_untrusted enrichment seam"
  - phase: 21-scale-maintenance-embedder-identity
    plan: 04
    provides: "same-dimension warn+mark and width-mismatch fail/degrade at every search boundary"
  - phase: 21-scale-maintenance-embedder-identity
    plan: 05
    provides: "StreamingEmbedWriter, batch sanity, failure taxonomy, and certification gate"
  - phase: 21-scale-maintenance-embedder-identity
    plan: 06
    provides: "vacuum/backup helpers and cleanup shadow reconcile"
  - phase: 21-scale-maintenance-embedder-identity
    plan: 08
    provides: "identity-aware schema open, watcher adoption, and prompt-aware MCP construction"
provides:
  - "Recorded D-19 baseline: default ModelScope Qwen3 cache buckets, no-prompt embed_batch path, SC1 hybrid page, and bench defaults"
  - "Fresh-index only-new-writes assertion (identity, shadow, two markers)"
  - "Legacy upgrade end-to-end: shadow backfill -> one warning -> legacy-assumed -> full-force verified; scoped/failing runs stay assumed"
  - "Same-path/different-bytes GGUF identity non-match through the file-hash revision"
  - "Real-DB failure matrix: NaN batch rollback + clean rerun; whitespace skip without shadow"
  - "sif search stays identity-silent; sif query warns once and marks; vsearch refuses width mismatches"
  - "docs/architecture.md identity/shadow/streaming/maintenance surfaces; generator-clean reference docs"
  - "Recorded full quality gate: 2734 passed / 95.22% coverage, ruff/format/ty clean"
affects: [Phase 22 MCP SDK v2, Phase 23 Harrier gated evaluation, Phase 24 Tuning + Models UX]

# Actuals (#2632) - pairs with the plan's `estimate` (62000 tokens, 3 tasks).
actuals:
  tokens: 16049
  tasks: 3
  commits: 3
plan_head_before: 78ccdc3b7689e69b343d7bfb694d6df46ca6077e
plan_head_after: b210adbfdc87719a1dbffc6421c2a57f0f5f1439

tech-stack:
  added: []
  patterns:
    - "Baseline literals are recorded once and asserted verbatim, never regenerated from the code they pin"
    - "A role-capable embedder with no prompt must reproduce the plain-path golden byte-for-byte"
    - "Legacy fixtures are built backwards from a real schema (seed, then strip shadow/markers/identity)"
    - "Real-DB integration tests pin failure durability and rollback, not just writer-level exceptions"

key-files:
  created: []
  modified:
    - tests/unit/embedding/test_manager.py
    - tests/unit/embedding/test_identity.py
    - tests/unit/database/test_embedded_documents.py
    - tests/unit/search/test_hybrid.py
    - tests/unit/search/test_bench_snapshot.py
    - tests/unit/cli/test_index.py
    - tests/unit/cli/test_search.py
    - tests/integration/test_embed_idempotency.py
    - docs/architecture.md

key-decisions:
  - "The D-19 baseline lives as literals (modelscope:Qwen/Qwen3-Embedding-0.6B, the prompt-free default tuple) asserted against the code, so a Phase 23 comparison cannot silently move the reference point."
  - "The role-capable no-prompt path is pinned by reproducing the recorded SC1 snapshot, proving embed_query with no prompt is byte-identical to the plain pre-phase path."
  - "Legacy upgrade tests build a real Phase-21-shaped index and then strip the shadow, its marker, and the identity row, so the upgrade exercises production create_all rather than a hand-rolled skeleton."
  - "The fresh-index assertion pins the exact three index_meta keys, the single shadow row, and source=verified after one writer commit."
  - "The GGUF identity test reads the real file-hash revision through a stubbed llama_cpp module, so same-name/different-bytes detection is proven at the identity layer."
  - "Garbage and whitespace cases are re-proven on a real database through the CLI, complementing the writer-level unit matrix."
  - "Maintenance concurrency (vacuum under a reader, backup under a writer) and the MCP mismatch policy required no test changes: 21-04/21-06 already assert them; this plan re-ran and recorded them."

patterns-established:
  - "D-19 baseline pins: cache bucket string, encode call shape, SC1 page, and held-out snapshot all asserted against recorded pre-phase values"
  - "Identity lifecycle E2E: legacy shape -> assumed -> (scoped/failing stays) -> full-force verified"
  - "Docs surfaces named with their integration points, not just module names"

requirements-completed: [SCALE-01, SCALE-02, SCALE-03, CORR-06, EMB-01, EMB-02]

coverage:
  - id: D1
    description: "Default ModelScope Qwen3 cache buckets equal the recorded pre-phase string, no revision suffix appears, and both role methods route through the unchanged embed_batch call"
    requirement: EMB-02
    verification:
      - kind: unit
        ref: "tests/unit/embedding/test_manager.py#TestCacheBuckets.test_default_qwen3_buckets_are_the_pre_phase_baseline"
        status: pass
    human_judgment: false
  - id: D2
    description: "The SC1 hybrid page is reproduced byte-for-byte by a role-capable no-prompt embedder, and the bench defaults stay prompt-free ModelScope Qwen3 with the recorded held-out snapshot"
    requirement: EMB-02
    verification:
      - kind: unit
        ref: "tests/unit/search/test_hybrid.py#TestSearchPipelineIdentity.test_default_no_prompt_query_role_reproduces_the_sc1_golden"
        status: pass
      - kind: unit
        ref: "tests/unit/search/test_bench_snapshot.py#TestDefaultEmbedderBaseline"
        status: pass
      - kind: other
        ref: "tests/unit/search/test_bench_snapshot.py#TestHeldoutSnapshotReproduction"
        status: pass
    human_judgment: false
  - id: D3
    description: "A fresh first embed adds exactly the identity row, the shadow row, and the two version markers beyond the pre-phase writes"
    requirement: CORR-06
    verification:
      - kind: unit
        ref: "tests/unit/database/test_embedded_documents.py#TestFreshIndexOnlyNewWrites"
        status: pass
    human_judgment: false
  - id: D4
    description: "A pre-Phase-21 index upgrades on first open (shadow backfills, one legacy warning, source=legacy-assumed); a complete unfiltered zero-failure --force certifies verified, while scoped or failing runs keep assumed"
    requirement: EMB-01
    verification:
      - kind: unit
        ref: "tests/unit/cli/test_index.py#TestLegacyUpgradeEndToEnd"
        status: pass
      - kind: integration
        ref: "tests/integration/test_embed_idempotency.py#TestIdentityCertification"
        status: pass
    human_judgment: false
  - id: D5
    description: "A GGUF model swapped at the same path with different bytes builds a non-matching identity because the file-hash revision differs"
    requirement: EMB-01
    verification:
      - kind: unit
        ref: "tests/unit/embedding/test_identity.py#TestGgufFileRevision"
        status: pass
    human_judgment: false
  - id: D6
    description: "A garbage-vector batch aborts with nothing persisted for the document and a subsequent normal run succeeds; a whitespace-only document is skipped without a shadow row; a mid-run failure stays durable and resumes the exact remainder"
    requirement: SCALE-03
    verification:
      - kind: integration
        ref: "tests/integration/test_embed_idempotency.py#TestGarbageAndWhitespaceIsolation,TestStreamingFailureDurability"
        status: pass
    human_judgment: false
  - id: D7
    description: "Vacuum under a concurrent reader and backup under live writes end with a valid database/copy and integrity_check ok; sif query warns once and marks, sif search is silent, vsearch refuses a width mismatch, and MCP marks/degrade as documented"
    requirement: SCALE-01
    verification:
      - kind: integration
        ref: "tests/integration/test_maintenance.py#TestVacuumUnderConcurrentReader,TestBackupUnderLiveWrites"
        status: pass
      - kind: unit
        ref: "tests/unit/cli/test_search.py#TestSearchIdentityPolicy"
        status: pass
      - kind: unit
        ref: "tests/unit/mcp/test_backend.py#TestHybridSearchIdentity"
        status: pass
      - kind: unit
        ref: "tests/unit/cli/test_index.py#TestEmbedIdentityEnforcement"
        status: pass
    human_judgment: false
  - id: D8
    description: "docs/architecture.md names identity, prompt scheme, shadow, streaming writer, and maintenance with integration points; a second make docs-generate leaves a clean diff; no MCP tool exposes vacuum/backup; ruff, format, ty, and the full suite pass at >=90% coverage with no dependency change"
    requirement: SCALE-02
    verification:
      - kind: other
        ref: "make docs-generate twice + git diff --exit-code docs/cli-reference.md docs/configuration.md; grep vacuum|backup src/sif/mcp (no match); git diff pyproject.toml uv.lock (empty)"
        status: pass
      - kind: other
        ref: "ruff check src tests; ruff format --check src tests; ty check src/sif; env -u FORCE_COLOR NO_COLOR=1 pytest (2734 passed, 1 skipped, 95.22%)"
        status: pass
    human_judgment: false

duration: 7min
completed: 2026-11-16
status: complete
---

# Phase 21 Plan 07: Byte-Identical Baseline, Identity Lifecycle, and Phase Gate Summary

**The phase closes with recorded D-19 evidence: default ModelScope Qwen3 cache buckets and the SC1/bench goldens reproduce byte-for-byte, a pre-Phase-21 index upgrades through legacy-assumed to verified certification, the real-DB failure/concurrency matrix is green, and the full quality suite passes at 95.22% coverage with generator-clean docs.**

## Performance

- **Duration:** 7 min
- **Started:** 2026-11-15T17:47:33Z
- **Completed:** 2026-11-15T17:54:47Z (2026-11-16 local)
- **Tasks:** 3
- **Files modified:** 9 (8 test files, 1 doc)
- **Commits:** 3 task commits

## Accomplishments

- The D-19 baseline is now explicit and locked: the pre-phase `modelscope:Qwen/Qwen3-Embedding-0.6B` bucket is a literal asserted for both roles, the no-prompt role methods are proven to call `embed_batch` with no revision suffix, a role-capable no-prompt embedder reproduces the recorded SC1 hybrid page byte-for-byte, and the bench module pins the prompt-free ModelScope Qwen3 defaults alongside the recorded held-out snapshot.
- A fresh first embed is pinned to exactly the documented side effects: `index_meta` contains only `embedded_documents_version`, `metadata_values_version`, and `embedder.identity`; the shadow holds exactly the embedded document; the identity is `source="verified"`.
- The legacy lifecycle is proven end-to-end on a real pre-Phase-21 index shape (documents + chunks + vec0 vectors, no shadow, no identity, no Phase-21 markers): first open backfills the shadow, emits exactly one "Index predates embedder identity" warning, and stores `source="legacy-assumed"`. A full unfiltered zero-failure `--force` certifies `verified`; scoped `--force` and a run with one document failure keep `legacy-assumed`.
- A GGUF model rewritten at the same path with different bytes builds a non-matching identity because the SHA-256 file-hash revision differs, closing the same-name/different-bytes hole at the identity layer.
- The real-database failure matrix now covers a NaN batch (abort with no chunk/vector/shadow/identity row, followed by a clean rerun), a whitespace-only document (no model call, no chunk, no shadow row, exit 0), and the existing mid-run durability/resume proof.
- CLI identity policy is pinned across `sif query` (one warning, every row marked), `sif search` (silent), `sif vsearch` (width mismatch refuses with both widths and the remedy), and `sif index embed` (mismatch exits non-zero naming both identities, and writes no vectors). MCP same-dimension marks and BM25 degradation were re-run and recorded.
- `docs/architecture.md` now documents the identity record, prompt scheme, role dispatch, the `embedded_documents` shadow/backfill/reconcile path, `StreamingEmbedWriter`, and the vacuum/backup helpers, plus the intentional embedder-switch path (fresh index/rebuild; `--force` certifies but never bypasses a mismatch).

## Task Commits

Each task was committed atomically:

1. **Task 1: Byte-identical default baseline and legacy upgrade -> assumed -> certify end-to-end** — `0c48e20` (test)
2. **Task 2: Phase-level failure and concurrency matrix across CLI, MCP, and maintenance** — `2ab51a9` (test)
3. **Task 3: Architecture docs, generated references, and the full quality gate** — `b210adb` (docs)

**Plan metadata:** the final docs commit captures this SUMMARY plus STATE/ROADMAP/REQUIREMENTS updates.

## Files Created/Modified

- `tests/unit/embedding/test_manager.py` — the D-19 module constants and `TestCacheBuckets.test_default_qwen3_buckets_are_the_pre_phase_baseline` (bucket equality, no revision suffix, no-prompt `embed_batch` call shape).
- `tests/unit/embedding/test_identity.py` — `TestGgufFileRevision`: same path, different bytes, different file-hash revision, `identity_matches` False.
- `tests/unit/database/test_embedded_documents.py` — `TestFreshIndexOnlyNewWrites`; self-contained identity/manager/chunker helpers.
- `tests/unit/search/test_hybrid.py` — `test_default_no_prompt_query_role_reproduces_the_sc1_golden`.
- `tests/unit/search/test_bench_snapshot.py` — `TestDefaultEmbedderBaseline` (prompt-free ModelScope Qwen3 defaults; the snapshot embedder has no role path).
- `tests/unit/cli/test_index.py` — `TestLegacyUpgradeEndToEnd` (backfill + assumed + verified; scoped/failing keep assumed), `TestEmbedIdentityEnforcement` (mismatch writes no vectors), and legacy/pre-phase fixture helpers.
- `tests/unit/cli/test_search.py` — shared identity-index fixture and `test_search_cmd_stays_identity_silent`; the existing query swap test now uses the helper.
- `tests/integration/test_embed_idempotency.py` — `TestGarbageAndWhitespaceIsolation` (NaN rollback + clean rerun; whitespace skip without a shadow row) and a `_shadow_count` helper.
- `docs/architecture.md` — identity/prompts/roles, shadow schema + backfill/reconcile, streaming writer, maintenance, cache suffix discipline, and the new "Embedder Identity and Vector-Space Enforcement" section.

## Decisions Made

- **Assert literals, never regenerate them.** The default bucket string and prompt-free default tuple are recorded constants in the tests; Phase 23 compares against them, so they must not be derived from the current implementation.
- **The no-prompt role path is proven by output, not by mocks.** A class-level `embed_query` embedder with no effective prompt must produce the same SC1 page as the plain protocol-only double; that is the strongest statement of D-19 available without a real model.
- **Legacy fixtures are built from the real schema, then stripped.** This exercises production `create_all`, the real backfill, and the real CLI open path rather than a hand-built skeleton that could drift.
- **Garbage/whitespace are re-proven on a real DB through the CLI.** The writer-level unit matrix already pins every class; the integration test proves the CLI abort/report and cross-run state are equally clean.
- **No changes were needed in `tests/unit/mcp/test_backend.py` or `tests/integration/test_maintenance.py`.** Their 21-04/21-06 batteries already assert the same-dimension MCP marks, BM25 degradation, vacuum-under-reader, and backup-under-writer contracts; this plan re-ran them as part of the matrix.

## Deviations from Plan

### Auto-fixed Issues

**1. [Commit shape] The embed identity-mismatch assertion landed in Task 1's commit**
- **Found during:** Task 1 (legacy fixture work)
- **Issue:** The `sif index embed` mismatch test (a Task 2 acceptance item) shares the pre-Phase-21 fixture helpers and `tests/unit/cli/test_index.py`, which is in both tasks' file lists; splitting the file between two commits would have staged a partial test module.
- **Fix:** The test and its helpers were committed with Task 1 (`0c48e20`); Task 2's commit carries the remaining integration and `sif search` additions.
- **Files modified:** `tests/unit/cli/test_index.py`
- **Verification:** Both task verify commands pass; the full suite is green.
- **Committed in:** `0c48e20` (Task 1 commit)

---

**Total deviations:** 1 commit-shape note; no production-code deviations.
**Impact on plan:** None on behavior or scope — every Task 1 and Task 2 acceptance criterion has a passing test, and no production file was touched by this plan.

## Issues Encountered

- None. The full suite completed in 120.01 seconds; no flaky or order-dependent failures appeared.
- `docs/architecture.md` is hand-maintained (unlike `docs/cli-reference.md`/`docs/configuration.md`); only the latter two are generator-owned, and both stayed byte-identical across two `make docs-generate` runs.

## User Setup Required

None - no external service configuration required. No runtime dependency was added (`git diff --stat pyproject.toml uv.lock` is empty).

## Verification

### Per-task gates

- Task 1: `pytest tests/unit/embedding/test_manager.py tests/unit/embedding/test_identity.py -x --no-cov` — 89 passed; `pytest tests/unit/search/test_hybrid.py tests/unit/search/test_bench_snapshot.py -x --no-cov` — 85 passed; `pytest tests/unit/database/test_embedded_documents.py tests/unit/cli/test_index.py -x --no-cov` — 36 passed; `grep -c "legacy-assumed" src/sif/embedding/identity.py` — 4.
- Task 2: `pytest tests/integration/test_embed_idempotency.py tests/integration/test_maintenance.py -x --no-cov` — 17 passed; `pytest tests/unit/cli/test_search.py tests/unit/cli/test_index.py tests/unit/mcp/test_backend.py -x --no-cov` — 313 passed.
- Task 3: `make docs-generate` twice → `git diff --exit-code docs/cli-reference.md docs/configuration.md` clean; `grep -rn "vacuum\|backup" src/sif/mcp/` → no match; `git diff --stat pyproject.toml uv.lock` → empty.

### Full quality gate

- `ruff check src tests` — All checks passed.
- `ruff format --check src tests` — 218 files already formatted.
- `ty check src/sif` — All checks passed.
- `env -u FORCE_COLOR NO_COLOR=1 pytest` — **2734 passed, 1 skipped**, total coverage **95.22%** (`fail_under=90`), 22 warnings, 120.01s.

### Prohibitions

- **Default vector values / ranking / cache keys unchanged:** asserted by the bucket baseline (`test_manager.py`), the SC1 golden reproduced through the no-prompt role path (`test_hybrid.py`), and the held-out snapshot reproduction (`test_bench_snapshot.py`).
- **The Harrier prompt never becomes effective by default:** `TestDefaultEmbedderBaseline` asserts the shipped defaults are prompt-free and Qwen3 has no prompt row; `TestResolvePromptScheme` pins the override/table behavior.
- **No maintenance command is exposed through MCP:** `grep -rn "vacuum\|backup" src/sif/mcp/` returns no match.
- **No new runtime dependency:** `pyproject.toml` and `uv.lock` are unchanged across the plan's three commits.

### Flagged assumptions — disposition

- **EDGE-U1 (vacuum target/precheck):** asserted by `tests/unit/database/test_maintenance.py` and `tests/unit/cli/test_index.py#TestVacuumCommand` (no target argument, 2× precheck with required/available bytes).
- **EDGE-C1 (concurrent hosts):** asserted by `tests/integration/test_maintenance.py` (reader/writer coexist or retryable busy, then `integrity_check == ok`).
- **EDGE-B1 (batch/disk boundaries):** asserted by `tests/unit/indexing/test_embed_writer.py` (batch slicing) and `tests/unit/database/test_maintenance.py` (2× db+WAL precheck).
- **EDGE-P1 (comparison precision):** asserted by `TestIdentityMatches` (unknown-tolerance) and the deterministic fingerprint/round-trip tests.
- **EDGE-U2 (missing shadow/vec0):** asserted by `TestVec0FreeDatabase`, the reconcile no-table test, and `tests/unit/search/test_staleness.py` degradation tests.
- **EDGE-U3 (corrupt identity, same-dim swap):** asserted by `TestFromJson` (one warning, treated as absent) and the CLI/MCP swap tests.
- **EDGE-U4 (prompt cache isolation):** asserted by `test_prompted_roles_never_share_cache_rows` and the default-bucket baseline.

## Known Stubs

None.

## Threat Flags

None - this plan changes tests and documentation only. T-21-23 (false-green baseline) is mitigated by asserting recorded literals and the only-new-writes set; T-21-24 (hand-edited generated docs) by the double `make docs-generate` diff; T-21-25 (accidental MCP exposure) by the MCP registry grep; T-21-SC (package installs) by the unchanged `pyproject.toml`/`uv.lock`.

## Self-Check: PASSED

- FOUND: /Users/forrest/GitHub/SIF/.planning/phases/21-scale-maintenance-embedder-identity/21-07-SUMMARY.md
- FOUND: 0c48e20
- FOUND: 2ab51a9
- FOUND: b210adb
- FOUND: docs/architecture.md
- FOUND: tests/unit/cli/test_index.py
- FOUND: tests/integration/test_embed_idempotency.py

## Next Phase Readiness

- Phase 21's six requirements now have one recorded baseline and one green gate; Phase 23 can compare its Harrier arm against the literal bucket/SC1/bench evidence, and Phase 22 can consume the identity contract and maintenance helpers.
- `sif index vacuum` / `sif index backup` remain CLI-only by design; Phase 22 owns any MCP exposure with its own destructive-target policy.
- Residual accepted limitations carried from prior plans (unchanged): a whitespace-only document is retried on each explicit run (harmless, bounded by user runs); a ModelScope local snapshot exposes no revision; raw-SQL vec0 writers bypass the shadow until a reconcile runs.
- No blockers.
