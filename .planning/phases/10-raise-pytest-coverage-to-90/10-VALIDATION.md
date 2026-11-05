---
phase: "10"
slug: "raise-pytest-coverage-to-90"
# status lifecycle: draft (seeded by plan-phase) → validated (set by validate-phase §6)
# audit-milestone §5.5 distinguishes NOT-VALIDATED (draft) from PARTIAL (validated + nyquist_compliant: false) (#2117)
status: draft
nyquist_compliant: false
wave_0_complete: false
created: "2026-11-05"
---

# Phase 10 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.1.1 + pytest-cov 7.0.0 (coverage 7.13.1) |
| **Config file** | pyproject.toml (`[tool.pytest.ini_options]` today; `[tool.coverage.report] fail_under = 90` lands in 10-07 Task 2, LAST) |
| **Quick run command** | `env -u FORCE_COLOR NO_COLOR=1 pytest tests/unit/<subdir> -x -q` |
| **Full suite command** | `env -u FORCE_COLOR NO_COLOR=1 pytest --cov=src/sif` |
| **Estimated runtime** | ~15 seconds (688 tests, measured 2026-11-05) |

---

## Sampling Rate

- **After every task commit:** Run `env -u FORCE_COLOR NO_COLOR=1 pytest tests/unit/<subdir> -x -q`
- **After every plan wave:** Run `env -u FORCE_COLOR NO_COLOR=1 pytest --cov=src/sif`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

All 17 tasks across the 7 plans; every command below is the primary gate — the full chain (inspect probes, grep counts, awk per-file thresholds) lives in each plan task's `<verify><automated>`.

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 10-01-01 | 01 | 1 | T-10-1 | T-10-01 | deleted symbols have zero live importers; all live imports (search.py:15, get.py:10, main, sif.utils) stay intact | deletion + regression | `test ! -f src/sif/cli/config.py && env -u FORCE_COLOR NO_COLOR=1 pytest -q` | ✅ | ⬜ pending |
| 10-01-02 | 01 | 1 | T-10-1 | T-10-SC | generator-owned docs byte-identical after regeneration; never hand-edited | guardrail | `ruff check src tests && python -m coverage report --fail-under=81 && make docs-generate` + empty `git status --porcelain -- docs/cli-reference.md docs/configuration.md` | ✅ | ⬜ pending |
| 10-02-01 | 02 | 2 | T-10-1 | T-10-02 | every CliRunner invoke pins the DB to tmp_path (`--index` or `SIF_DB_PATH`) — never the real user DB | unit (CliRunner, real temp DB) | `env -u FORCE_COLOR NO_COLOR=1 pytest tests/unit/cli/test_collection.py -q` + collection.py >= 75% gate | ✅ extend | ⬜ pending |
| 10-02-02 | 02 | 2 | T-10-1 | T-10-02 | same DB-pinning rule; cleanup proven behaviorally (orphans gone) | unit (CliRunner, real temp DB) | `env -u FORCE_COLOR NO_COLOR=1 pytest tests/unit/cli/test_main.py tests/unit/cli/test_get.py -q` + main.py/get.py >= 80% gate | ✅ extend | ⬜ pending |
| 10-03-01 | 03 | 2 | T-10-1 | T-10-03, T-10-04 | zero real weight loads / network: ML classes patched at SOURCE modules (lazy call-time imports); ModelDownloader mocked | unit (mocked ML) | `env -u FORCE_COLOR NO_COLOR=1 pytest tests/unit/search/test_rerank.py tests/unit/inference/test_reranker.py -q` + rerank.py >= 80% gate | ✅ extend | ⬜ pending |
| 10-03-02 | 03 | 2 | T-10-1 | T-10-02 | pipeline mocked at consumer module; DB pinned to tmp_path | unit (CliRunner, mocked pipeline) | `env -u FORCE_COLOR NO_COLOR=1 pytest tests/unit/cli/test_search.py -q` + search.py >= 88% gate | ✅ extend | ⬜ pending |
| 10-04-01 | 04 | 2 | T-10-1 | T-10-05 | real SQLite only (`:memory:`/tmp_path); no MagicMock connections; package marker prevents basename collision | unit (real SQLite) | `env -u FORCE_COLOR NO_COLOR=1 pytest tests/unit/database/ -q` + repositories.py >= 88% gate | ✅ extend (+ `__init__.py` created in-task) | ⬜ pending |
| 10-04-02 | 04 | 2 | T-10-1 | T-10-05 | tmp_path DB files only; sqlite-vec swallow path via patched loader (no uninstalls) | unit (real SQLite) | `env -u FORCE_COLOR NO_COLOR=1 pytest tests/unit/database/test_database.py tests/unit/database/test_migrations.py -q` + database.py/migrations.py >= 85% gate | ❌ created in-task | ⬜ pending |
| 10-04-03 | 04 | 2 | T-10-1 | T-10-05 | cache dir is a tmp_path child; no mocks (pure SQLite) | unit (real SQLite) | `env -u FORCE_COLOR NO_COLOR=1 pytest tests/unit/embedding/test_cache.py -q` + cache.py >= 85% gate | ❌ created in-task | ⬜ pending |
| 10-05-01 | 05 | 2 | T-10-1 | — | repository is a MagicMock Protocol — never a real DB | unit (DI mocks) | `env -u FORCE_COLOR NO_COLOR=1 pytest tests/unit/core/ -q` + context.py/collection.py >= 80% gate | ❌ created in-task | ⬜ pending |
| 10-05-02 | 05 | 2 | T-10-1 | T-10-06, T-10-07 | ModelScope client mocked at lazy import site; every `ModelDownloader(` pinned to tmp_path cache_dir (grep count gate) | unit (mocked network) | `env -u FORCE_COLOR NO_COLOR=1 pytest tests/unit/models/test_download.py -q` + download.py >= 80% gate | ❌ created in-task | ⬜ pending |
| 10-05-03 | 05 | 2 | T-10-1 | T-10-07 | HOME/env monkeypatched to tmp_path — nothing resolves against the real home | unit (monkeypatch matrix) | `env -u FORCE_COLOR NO_COLOR=1 pytest tests/unit/utils/ -q` + logging.py/paths.py/progress.py >= 85% gate | ❌ created in-task | ⬜ pending |
| 10-06-01 | 06 | 2 | T-10-1 | T-10-08 | all parsed/scanned trees inside tmp_path; no real project directories | unit (real temp files) | `env -u FORCE_COLOR NO_COLOR=1 pytest tests/unit/indexing/test_parser.py -q` + parser.py >= 80% gate | ❌ created in-task | ⬜ pending |
| 10-06-02 | 06 | 2 | T-10-1 | — | N/A (pure content transforms) | unit | `env -u FORCE_COLOR NO_COLOR=1 pytest tests/unit/indexing/test_chunker.py -q` + chunker.py >= 85% gate | ❌ created in-task | ⬜ pending |
| 10-06-03 | 06 | 2 | T-10-1 | T-10-08 | no real port binding — FastAPI test client only | unit (async MCP) | `env -u FORCE_COLOR NO_COLOR=1 pytest tests/unit/mcp/ -q` + http.py/server.py >= 85% gate | ✅ extend (+ test_server.py created in-task) | ⬜ pending |
| 10-07-01 | 07 | 3 | T-10-1 | T-10-09 | long-tail top-ups follow Wave-2 rules (tmp_path-only FS, pinned DB, mocked ML/network) | tollgate (whole suite) | `env -u FORCE_COLOR NO_COLOR=1 pytest -q && python -m coverage report --fail-under=90` | ✅ extend | ⬜ pending |
| 10-07-02 | 07 | 3 | T-10-1 | T-10-09, T-10-10 | only `fail_under = 90` added — no `exclude_lines` (default-exclusion replacement), no `--cov-branch` (denominator change); generator-owned docs unchanged | config gate | `grep -n "fail_under = 90" pyproject.toml && env -u FORCE_COLOR NO_COLOR=1 pytest -q` + empty docs porcelain after `make docs-generate` | ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*
*"✅ extend" = existing test file extended in place. "❌ created in-task" = the test file is itself the task deliverable (this phase authors tests), so the verify command runs against files the task's own action creates — no separate Wave 0 scaffold is required.*

---

## Wave 0 Requirements

Existing infrastructure covers all phase requirements. pytest 9.1.1 + pytest-cov 7.0.0 are already configured in pyproject.toml with coverage on every run (`addopts`), the 688-test suite is green at baseline, and `tests/conftest.py` fixtures (temp_dir, temp DB, mocks) are sufficient (10-RESEARCH.md "Wave 0 Gaps" and "Validation Architecture"). The missing package markers/directories (`tests/unit/database/__init__.py`, `tests/unit/core/`, `tests/unit/models/`, `tests/unit/utils/`) are created as step 1 of their own tasks (10-04-01, 10-05-01/02/03) — before any test file that depends on them lands.

---

## Manual-Only Verifications

All phase behaviors have automated verification.

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
