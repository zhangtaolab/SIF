---
phase: 02
slug: cli-core-completion
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-15
---

# Phase 02 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x |
| **Config file** | `pyproject.toml` |
| **Quick run command** | `pytest tests/unit/cli/` |
| **Full suite command** | `pytest` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `pytest tests/unit/cli/`
- **After every plan wave:** Run `pytest`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 02-01-01 | 01 | 1 | CLI-01 | — | N/A | unit | `pytest tests/unit/cli/test_get.py -k multi_get` | ❌ W0 | ⬜ pending |
| 02-01-02 | 01 | 1 | CLI-01 | — | N/A | unit | `pytest tests/unit/cli/test_get.py -k multi_get` | ❌ W0 | ⬜ pending |
| 02-02-01 | 02 | 1 | CLI-02 | — | N/A | unit | `pytest tests/unit/cli/test_ls.py` | ❌ W0 | ⬜ pending |
| 02-03-01 | 03 | 2 | CLI-03 | T-02-01 | Shell commands run in isolated subprocess; fail on non-zero exit | unit | `pytest tests/unit/cli/test_collection.py -k update_cmd` | ❌ W0 | ⬜ pending |
| 02-03-02 | 03 | 2 | CLI-03 | T-02-01 | Update stops if pre-index command fails | unit | `pytest tests/unit/cli/test_collection.py -k update_cmd` | ❌ W0 | ⬜ pending |
| 02-04-01 | 04 | 2 | CLI-04 | — | N/A | unit | `pytest tests/unit/cli/test_collection.py -k include_exclude` | ❌ W0 | ⬜ pending |
| 02-04-02 | 04 | 2 | CLI-04 | — | N/A | unit | `pytest tests/unit/cli/test_search.py -k all_flag` | ❌ W0 | ⬜ pending |
| 02-05-01 | 05 | 3 | CLI-05 | — | N/A | unit | `pytest tests/unit/cli/test_pull.py` | ❌ W0 | ⬜ pending |
| 02-06-01 | 06 | 3 | CLI-08 | — | N/A | unit | `pytest tests/unit/cli/test_formatters.py -k line_numbers` | ❌ W0 | ⬜ pending |
| 02-06-02 | 06 | 3 | CLI-08 | — | N/A | unit | `pytest tests/unit/cli/test_get.py -k line_numbers` | ❌ W0 | ⬜ pending |
| 02-06-03 | 06 | 3 | CLI-08 | — | N/A | unit | `pytest tests/unit/cli/test_search.py -k line_numbers` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/unit/cli/test_get.py` — stubs for CLI-01, CLI-08
- [ ] `tests/unit/cli/test_ls.py` — stubs for CLI-02
- [ ] `tests/unit/cli/test_collection.py` — stubs for CLI-03, CLI-04
- [ ] `tests/unit/cli/test_pull.py` — stubs for CLI-05
- [ ] `tests/unit/cli/test_search.py` — stubs for CLI-04, CLI-08
- [ ] `tests/unit/cli/test_formatters.py` — stubs for CLI-08

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| `pull` downloads actual GGUF files from HuggingFace/ModelScope | CLI-05 | Network-dependent, large files | Run `docsift pull owner/repo/model.gguf` and verify file appears in `~/.docsift/models/` |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
