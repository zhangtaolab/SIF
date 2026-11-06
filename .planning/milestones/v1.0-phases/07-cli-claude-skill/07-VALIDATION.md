---
phase: "07"
slug: "cli-claude-skill"
# Retroactive reconstruction at milestone v1.0 close (2026-11-06). Deliverables are SKILL.md
# instruction documents (agent-facing prompts), not code — behavioral verification by design.
status: validated
nyquist_compliant: false
wave_0_complete: true
created: "2026-11-06"
validated: "2026-11-06"
---

# Phase 07 — Validation Strategy

> CLI Claude skills (sif-search, sif-get) wrap the CLI for agent workflows.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | n/a — deliverables are Markdown instruction docs; the wrapped CLI surface itself is covered by tests/unit/cli/** (1011-test suite) and tests/test_docs.py validates command references |
| **Behavioral check** | Live spot-checks: follow each SKILL.md's documented invocations against a real index (protocol used by 07-VERIFICATION.md truths 1-12) |
| **Full suite command** | `env -u FORCE_COLOR NO_COLOR=1 pytest -q` |

---

## Per-Task Verification Map

ROADMAP lists phase-7 Requirements as TBD; plan-internal SKILL-01/SKILL-02 map to SPEC
requirements 1-2. No pytest coverage by design (instruction documents, not code).

| Requirement | Deliverable | Verification | Status |
|---|---|---|---|
| SKILL-01 (SPEC req 1) | `.claude/skills/sif-search/SKILL.md` — search skill wrapping query/search/vsearch | Behavioral: live spot-checks (07-VERIFICATION truths 1, 5-8); command references held accurate by the docs suite and 2026-11-06 README/quickstart fact-check | MANUAL-ONLY |
| SKILL-02 (SPEC req 2) | `.claude/skills/sif-get/SKILL.md` — get skill wrapping get/multi-get | Behavioral: live spot-checks (07-VERIFICATION truths 2, 9-12); canonicalization semantics updated by 10.1-01 (commit 8e0db2a) | MANUAL-ONLY |

---

## Manual-Only

- SKILL-01 / SKILL-02 — agent-facing instruction documents; verification is behavioral
  (each documented invocation exercised against a live index), recorded in 07-VERIFICATION.md.
  The underlying CLI commands they wrap are fully covered by the automated suite.

---

## Sign-Off

- **Reconstructed:** 2026-11-06 (milestone v1.0 close, stale-verification regeneration).
- **Note:** `nyquist_compliant: false` reflects the manual-only nature of the deliverables,
  not missing coverage — there is no automatable behavior in a SKILL.md beyond the command
  references the docs suite already locks.

---

## Validation Audit

| Metric | Count |
|---|---|
| Gaps found | 0 |
| Resolved | 0 |
| Escalated | 0 |
