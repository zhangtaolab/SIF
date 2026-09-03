---
schema_version: 1
open_count: 2
waived_count: 0
fixed_count: 0
total_count: 2
last_updated: 2026-09-03T03:40:20.351Z
---

# Broken Windows Ledger

> Cross-phase defect register. With `workflow.windows_enforce` enabled, `/gsd-ship` blocks while `open_count > 0`.
> Waive with `gsd-tools windows waive <id> "<reason>"` (reason required).
> Mark fixed with `gsd-tools windows fixed <id>`.

| id | phase | kind | file | line | description | status | reason | recorded_at | resolved_at |
|----|-------|------|------|------|-------------|--------|--------|-------------|-------------|
| 1 | 03 | stub | src/sif/embedding/factory.py | 82 | HuggingFace factory stub raises NotImplementedError — pre-existing, out of scope per plan 03-07 / 03-VERIFICATION anti-pattern table; not a VEC-01 backend | open |  | 2026-09-03T03:40:20.270Z |  |
| 2 | 03 | unrun-verify | .planning/phases/03-embedding-vector-search/03-07-SUMMARY.md |  | Live OpenAI-compatible endpoint check (plan verification item 5) requires user API key — automated tests mock the endpoint | open |  | 2026-09-03T03:40:20.351Z |  |

````json
[
  {
    "id": 1,
    "kind": "stub",
    "phase": "03",
    "file": "src/sif/embedding/factory.py",
    "line": 82,
    "description": "HuggingFace factory stub raises NotImplementedError — pre-existing, out of scope per plan 03-07 / 03-VERIFICATION anti-pattern table; not a VEC-01 backend",
    "status": "open",
    "reason": "",
    "recorded_at": "2026-09-03T03:40:20.270Z",
    "resolved_at": null
  },
  {
    "id": 2,
    "kind": "unrun-verify",
    "phase": "03",
    "file": ".planning/phases/03-embedding-vector-search/03-07-SUMMARY.md",
    "line": null,
    "description": "Live OpenAI-compatible endpoint check (plan verification item 5) requires user API key — automated tests mock the endpoint",
    "status": "open",
    "reason": "",
    "recorded_at": "2026-09-03T03:40:20.351Z",
    "resolved_at": null
  }
]
````
