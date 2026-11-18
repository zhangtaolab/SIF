---
phase: "13"
slug: "watch-everywhere-mcp-embedded-refresh-background-daemon"
# status lifecycle: draft (seeded by plan-phase) → validated (set by validate-phase §6)
# audit-milestone §5.5 distinguishes NOT-VALIDATED (draft) from PARTIAL (validated + nyquist_compliant: false) (#2117)
status: validated
nyquist_compliant: true
wave_0_complete: true
created: "2026-11-07"
---

# Phase 13 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (1015+ passed @ 96.2x% coverage; `fail_under=90` in `[tool.coverage.report]`) + ruff + ruff-format + ty |
| **Config file** | `pyproject.toml` (`[tool.pytest.ini_options]`, `[tool.ruff]`) |
| **Quick run command** | `env -u FORCE_COLOR NO_COLOR=1 python -m pytest tests/unit/indexing/test_watcher.py tests/unit/cli/test_watch_cmd.py -x -q` |
| **Full suite command** | `env -u FORCE_COLOR NO_COLOR=1 python -m pytest` |
| **Estimated runtime** | ~60–120 seconds full suite; quick runs seconds |

Env prefix per project memory: agent shells must **unset** `FORCE_COLOR` (`env -u`, setting `"0"` still fails) and set `NO_COLOR=1`.

---

## Sampling Rate

- **After every task commit:** quick unit run for the touched area (see per-task commands) + `env -u FORCE_COLOR NO_COLOR=1 python -m pytest tests/unit -x -q --no-cov` when cheap
- **After every plan wave:** `env -u FORCE_COLOR NO_COLOR=1 python -m pytest` + `ruff check src tests` + `ruff format --check src tests` + `ty check src/sif`
- **Before `/gsd-verify-work`:** full suite green; docs regenerated (`make docs-generate`) with diff reviewed (12-03 precedent — generator-owned docs, never hand-edited)
- **Max feedback latency:** ~120 seconds (full suite)

---

## Per-Task Verification Map

Seeded from RESEARCH.md's requirement→test map at requirement level; task IDs filled by the validate-phase audit on 2026-11-08 — every row re-run green against the executed phase, full suite 1164 passed, 1 skipped @ 94.58%.

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 13-03 T1/T2 | 13-03 | 2 | LIVE-08 (SC1) | T-13-07 / T-13-09 | logger-to-stderr only; stdout stays the JSON-RPC channel | integration (subprocess `sif mcp stdio` with `SIF_MCP_WATCH=1`, deadline-bounded responsiveness during burst) | `env -u FORCE_COLOR NO_COLOR=1 python -m pytest tests/integration/test_mcp_watch_e2e.py -x -q` | ✅ | ✅ green (4 passed) |
| 13-03 T1 | 13-03 | 2 | LIVE-08 (D-01/D-02/D-04) | T-13-08 | BM25-forced depth regardless of `watch_update_depth` | unit (host helper: flag on/off per transport, BM25-forced depth, lifespan factory) | `env -u FORCE_COLOR NO_COLOR=1 python -m pytest tests/unit/mcp/test_mcp_watch_host.py -x -q` | ✅ | ✅ green (11 passed) |
| 13-02 T1 | 13-02 | 2 | LIVE-09 (SC2) | T-13-03 / T-13-04 / T-13-05 | PID identity corroborated before signaling; fork-first detach | integration (detach lifecycle: PID reported, index updates, `--stop` clean) | `env -u FORCE_COLOR NO_COLOR=1 python -m pytest tests/integration/test_watch_daemon_e2e.py -x -q` | ✅ | ✅ green (5 passed) |
| 13-02 T2 | 13-02 | 2 | LIVE-09 (SC4) | — | N/A | integration (SIGKILL → immediate re-detach succeeds, no lock error, no cleanup) | `env -u FORCE_COLOR NO_COLOR=1 python -m pytest tests/integration/test_watch_daemon_e2e.py -k sigkill -x -q` | ✅ | ✅ green (1 passed) |
| 13-02 T2 | 13-02 | 2 | LIVE-09 (D-05) | T-13-03 / T-13-04 | defensive PID-file parse; stale/garbage → "not running" + cleanup, never a blind kill | unit (PID file write/read/stale; stop escalation with fake PIDs — no real kills in unit tests) | `env -u FORCE_COLOR NO_COLOR=1 python -m pytest tests/unit/utils/test_daemon.py -x -q` | ✅ | ✅ green (32 passed; round-3 2026-11-08: +concurrent-writer PID-file race regressions, e1bb7d1) |
| 13-04 T1/T2 | 13-04 | 3 | LIVE-09 (SC3, D-11..D-13) | T-13-10 / T-13-11 / T-13-12 / T-13-13 | explicit argv lists, never `shell=True`; friendly missing-manager errors | unit (plist parse-back via plistlib + unit text on BOTH platforms; launchctl/systemctl argv via mocked `subprocess.run`) | `env -u FORCE_COLOR NO_COLOR=1 python -m pytest tests/unit/utils/test_service.py -x -q` | ✅ | ✅ green (14 passed; round-3 2026-11-08: argv-tail depth pin now unconditional --no-embed at bm25, f4057f6 — covered in test_watch_cmd battery, 35 passed) |
| 13-02 T2 | 13-02 | 2 | LIVE-09 (D-08) | T-13-03 / T-13-04 | stale-PID path renders "not running" + cleanup; corroborated payload renders PID/mode/depth | unit (status_cmd Watch section — planner placed D-08 in the existing `tests/unit/cli/test_status.py::TestWatchSection`, not a new `test_status_watch.py`) | `env -u FORCE_COLOR NO_COLOR=1 python -m pytest tests/unit/cli/test_status.py -k watch -x -q` | ✅ (`test_status.py` extended) | ✅ green (5 passed) |
| 13-01 T1 | 13-01 | 1 | D-15 (rescope) | T-13-01 | rescope respects `-c` filter; docs untouched | unit (extend existing: added root scheduled + reconciled; removed root unscheduled; synthetic, zero-timing per 12-D15) | `env -u FORCE_COLOR NO_COLOR=1 python -m pytest tests/unit/indexing/test_watcher.py -k rescope -x -q` | ✅ (extended) | ✅ green (5 passed) |
| 13-01 T2 | 13-01 | 1 | D-16 (WAL cadence) | T-13-02 | busy-row skip + recent-burst skip + disabled-by-default | unit (extend existing: idle tick runs TRUNCATE checkpoint; skips when contended/recent burst) | `env -u FORCE_COLOR NO_COLOR=1 python -m pytest tests/unit/indexing/test_watcher.py -k checkpoint -x -q` | ✅ (extended) | ✅ green (4 passed) |
| 13-01 T2 | 13-01 | 1 | D-17 (schedule failure) | — | N/A | unit (extend existing: warns with remedy; other roots keep watching) | `env -u FORCE_COLOR NO_COLOR=1 python -m pytest tests/unit/indexing/test_watcher.py -k "schedule_failure or inotify" -x -q` | ✅ (extended) | ✅ green (2 passed) |
| 13-04 T2 | 13-04 | 3 | docs regen | — | N/A | unit (existing docs gate after `make docs-generate`) | `env -u FORCE_COLOR NO_COLOR=1 python -m pytest tests/test_docs.py -x -q` | ✅ (existing gate) | ✅ green (13 passed) |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [x] `tests/integration/test_mcp_watch_e2e.py` — SC1 subprocess e2e (seeded tmp collection, deadline-bounded query-responsiveness assertions, protocol-clean stdout) — LIVE-08
- [x] `tests/unit/mcp/test_mcp_watch_host.py` — host helper: flag on/off, BM25-forced depth, logger-only callbacks, lifespan factory
- [x] `tests/integration/test_watch_daemon_e2e.py` — detach lifecycle + SC4 SIGKILL/restart
- [x] `tests/unit/utils/test_daemon.py` — PID file + stop escalation (fake PIDs, no real kills)
- [x] `tests/unit/utils/test_service.py` — plist/unit generation cross-platform + mocked manager argv
- [x] D-08 Watch section rendering incl. stale-PID path — delivered as `TestWatchSection` in the existing `tests/unit/cli/test_status.py` (planner's placement; the seeded `test_status_watch.py` path was never created)
- [x] Extend `tests/unit/indexing/test_watcher.py` — rescope / checkpoint tick / schedule-failure warn (synthetic, zero-timing)

Existing infrastructure otherwise covers the phase: conftest fixtures + the seeded-DB/deadline-poll e2e patterns in `tests/integration/test_watch_e2e.py` (12-D15 culture).

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Live launchd install surviving a real login session | LIVE-09 (SC3) | Unit tests mock `launchctl`; the automated live test (`tests/integration/test_service_live_launchd.py`, opt-in per D-13) covers a real bootstrap/bootout round-trip on the dev box but not login-session persistence | On the macOS dev box: `sif watch --install-service`, log out/in (or `launchctl kickstart -k`), confirm the daemon runs and `sif status` shows it; `--uninstall-service` removes it cleanly. (The D-13 opt-in automated live round-trip passed twice on this box during 13-04 — see 13-04-SUMMARY.) |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 120s (full suite re-run 2026-11-08: 63.6s)
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** validated 2026-11-08

## Validation Audit 2026-11-08

| Metric | Count |
|---|---|
| Gaps found | 0 |
| Resolved | 0 |
| Escalated | 0 |
