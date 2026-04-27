---
phase: 08
slug: project-rename-from-docsift-to-sif
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-27
---

# Phase 8 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.0.2 |
| **Config file** | `pyproject.toml` |
| **Quick run command** | `pytest -x` |
| **Full suite command** | `pytest` |
| **Estimated runtime** | ~60 seconds (377 tests) |

---

## Sampling Rate

- **After every task commit:** Run `pytest -x`
- **After every plan wave:** Run `pytest`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 120 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 08-01-01 | 01 | 1 | rename-package | — | N/A | import | `python -c "import sif"` | ⬜ W0 | ⬜ pending |
| 08-02-01 | 02 | 1 | rename-cli | — | N/A | cli | `sif --help` | ⬜ W0 | ⬜ pending |
| 08-03-01 | 03 | 2 | update-imports | — | N/A | unit | `pytest tests/ -x` | ✅ | ⬜ pending |
| 08-04-01 | 04 | 2 | update-config | — | N/A | unit | `pytest tests/ -x` | ✅ | ⬜ pending |
| 08-05-01 | 05 | 3 | update-settings | — | N/A | unit | `pytest tests/test_config.py -x` | ✅ | ⬜ pending |
| 08-06-01 | 06 | 3 | update-tests | — | N/A | unit | `pytest tests/ -x` | ✅ | ⬜ pending |
| 08-07-01 | 07 | 4 | update-docs | — | N/A | grep | `grep -r "docsift" README.md docs/ --include="*.md"` | ✅ | ⬜ pending |
| 08-08-01 | 08 | 4 | update-skills | — | N/A | grep | `grep -r "docsift" .claude/skills/ --include="*.md"` | ✅ | ⬜ pending |
| 08-09-01 | 09 | 5 | full-verification | — | N/A | unit | `pytest` | ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `pytest` available and baseline green (377 passed, 11 skipped)
- [ ] `ruff` available for lint checks
- [ ] `mypy` available for type checks

*Existing infrastructure covers all phase requirements.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| CLI command `sif` installs correctly | rename-cli | pip install behavior | `pip install -e .` then `sif --version` |
| Model cache auto-migration | data-migration | Requires pre-existing `~/.docsift/models/` | Create mock old dir, run `sif --help`, verify rename message |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 120s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
