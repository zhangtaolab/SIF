---
phase: "13"
slug: "watch-everywhere-mcp-embedded-refresh-background-daemon"
# status lifecycle: draft (seeded by plan-phase) → validated (set by validate-phase §6)
# audit-milestone §5.5 distinguishes NOT-VALIDATED (draft) from PARTIAL (validated + nyquist_compliant: false) (#2117)
status: draft
nyquist_compliant: false
wave_0_complete: false
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

Seeded from RESEARCH.md's requirement→test map at requirement level; the planner assigns task IDs (plans not yet created at seeding time).

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| TBD (planner) | TBD | TBD | LIVE-08 (SC1) | T-13-xx / — | logger-to-stderr only; stdout stays the JSON-RPC channel | integration (subprocess `sif mcp stdio` with `SIF_MCP_WATCH=1`, deadline-bounded responsiveness during burst) | `env -u FORCE_COLOR NO_COLOR=1 python -m pytest tests/integration/test_mcp_watch_e2e.py -x -q` | ❌ W0 | ⬜ pending |
| TBD (planner) | TBD | TBD | LIVE-08 (D-01/D-02/D-04) | — | N/A | unit (host helper: flag on/off per transport, BM25-forced depth regardless of `watch_update_depth`, lifespan factory) | `env -u FORCE_COLOR NO_COLOR=1 python -m pytest tests/unit/mcp/test_mcp_watch_host.py -x -q` | ❌ W0 | ⬜ pending |
| TBD (planner) | TBD | TBD | LIVE-09 (SC2) | T-13-xx / — | PID identity corroborated before signaling | integration (detach lifecycle: PID reported, index updates, `--stop` clean) | `env -u FORCE_COLOR NO_COLOR=1 python -m pytest tests/integration/test_watch_daemon_e2e.py -x -q` | ❌ W0 | ⬜ pending |
| TBD (planner) | TBD | TBD | LIVE-09 (SC4) | — | N/A | integration (SIGKILL → immediate re-detach succeeds, no lock error, no cleanup) | `env -u FORCE_COLOR NO_COLOR=1 python -m pytest tests/integration/test_watch_daemon_e2e.py -k sigkill -x -q` | ❌ W0 | ⬜ pending |
| TBD (planner) | TBD | TBD | LIVE-09 (D-05) | T-13-xx / — | defensive PID-file parse; stale/garbage → "not running" + cleanup, never a blind kill | unit (PID file write/read/stale; stop escalation with fake PIDs — no real kills in unit tests) | `env -u FORCE_COLOR NO_COLOR=1 python -m pytest tests/unit/utils/test_daemon.py -x -q` | ❌ W0 | ⬜ pending |
| TBD (planner) | TBD | TBD | LIVE-09 (SC3, D-11..D-13) | T-13-xx / — | explicit argv lists, never `shell=True`; friendly missing-manager errors | unit (plist parse-back via plistlib + unit text on BOTH platforms; launchctl/systemctl argv via mocked `subprocess.run`) | `env -u FORCE_COLOR NO_COLOR=1 python -m pytest tests/unit/utils/test_service.py -x -q` | ❌ W0 | ⬜ pending |
| TBD (planner) | TBD | TBD | LIVE-09 (D-08) | — | N/A | unit (status_cmd Watch section: running/PID/mode/depth incl. stale-PID path) | `env -u FORCE_COLOR NO_COLOR=1 python -m pytest tests/unit/cli/test_status_watch.py -x -q` | ❌ W0 | ⬜ pending |
| TBD (planner) | TBD | TBD | D-15 (rescope) | — | rescope respects `-c` filter; docs untouched | unit (extend existing: added root scheduled + reconciled; removed root unscheduled; synthetic, zero-timing per 12-D15) | `env -u FORCE_COLOR NO_COLOR=1 python -m pytest tests/unit/indexing/test_watcher.py -k rescope -x -q` | ✅ (extend) | ⬜ pending |
| TBD (planner) | TBD | TBD | D-16 (WAL cadence) | — | N/A | unit (extend existing: idle tick runs TRUNCATE checkpoint; skips when contended/recent burst) | `env -u FORCE_COLOR NO_COLOR=1 python -m pytest tests/unit/indexing/test_watcher.py -k checkpoint -x -q` | ✅ (extend) | ⬜ pending |
| TBD (planner) | TBD | TBD | D-17 (schedule failure) | — | N/A | unit (extend existing: warns with remedy; other roots keep watching) | `env -u FORCE_COLOR NO_COLOR=1 python -m pytest tests/unit/indexing/test_watcher.py -k "schedule_failure or inotify" -x -q` | ✅ (extend) | ⬜ pending |
| TBD (planner) | TBD | TBD | docs regen | — | N/A | unit (existing docs gate after `make docs-generate`) | `env -u FORCE_COLOR NO_COLOR=1 python -m pytest tests/test_docs.py -x -q` | ✅ (existing gate) | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/integration/test_mcp_watch_e2e.py` — SC1 subprocess e2e (seeded tmp collection, deadline-bounded query-responsiveness assertions, protocol-clean stdout) — LIVE-08
- [ ] `tests/unit/mcp/test_mcp_watch_host.py` — host helper: flag on/off, BM25-forced depth, logger-only callbacks, lifespan factory
- [ ] `tests/integration/test_watch_daemon_e2e.py` — detach lifecycle + SC4 SIGKILL/restart
- [ ] `tests/unit/utils/test_daemon.py` — PID file + stop escalation (fake PIDs, no real kills)
- [ ] `tests/unit/utils/test_service.py` — plist/unit generation cross-platform + mocked manager argv
- [ ] `tests/unit/cli/test_status_watch.py` — Watch section rendering incl. stale-PID path
- [ ] Extend `tests/unit/indexing/test_watcher.py` — rescope / checkpoint tick / schedule-failure warn (synthetic, zero-timing)

Existing infrastructure otherwise covers the phase: conftest fixtures + the seeded-DB/deadline-poll e2e patterns in `tests/integration/test_watch_e2e.py` (12-D15 culture).

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Live launchd install on a real login session | LIVE-09 (SC3) | Subprocess tests mock `launchctl`; a real bootstrap/bootout touches the developer's service manager | On the macOS dev box: `sif watch --install-service`, log out/in (or `launchctl kickstart -k`), confirm the daemon runs and `sif status` shows it; `--uninstall-service` removes it cleanly |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 120s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
