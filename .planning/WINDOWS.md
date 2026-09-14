---
schema_version: 1
open_count: 4
waived_count: 0
fixed_count: 0
total_count: 4
last_updated: 2026-09-14T04:11:18.859Z
---

# Broken Windows Ledger

> Cross-phase defect register. With `workflow.windows_enforce` enabled, `/gsd-ship` blocks while `open_count > 0`.
> Waive with `gsd-tools windows waive <id> "<reason>"` (reason required).
> Mark fixed with `gsd-tools windows fixed <id>`.

| id | phase | kind | file | line | description | status | reason | recorded_at | resolved_at |
|----|-------|------|------|------|-------------|--------|--------|-------------|-------------|
| 1 | 03 | stub | src/sif/embedding/factory.py | 82 | HuggingFace factory stub raises NotImplementedError — pre-existing, out of scope per plan 03-07 / 03-VERIFICATION anti-pattern table; not a VEC-01 backend | open |  | 2026-09-03T03:40:20.270Z |  |
| 2 | 03 | unrun-verify | .planning/phases/03-embedding-vector-search/03-07-SUMMARY.md |  | Live OpenAI-compatible endpoint check (plan verification item 5) requires user API key — automated tests mock the endpoint | open |  | 2026-09-03T03:40:20.351Z |  |
| 3 | quick-260905-tax | unmet-truth | tests/unit/embedding/test_openai_embedder.py | 195 | Full-suite green truth unmet: 2 pre-existing caplog failures (test_docs.py triggers setup_logging which sets sif logger propagate=False); proven unrelated to G-04-4 fix, documented in quick/260905-tax.../deferred-items.md | open |  | 2026-09-05T13:30:50.522Z |  |
| 4 | quick-260914-g63 | unmet-truth | tests/unit/embedding/test_openai_embedder.py |  | Full-suite pytest gate not green on this machine: 2 caplog-pollution failures (test_import_error_logs_install_hint, test_corrupt_cache_treated_as_miss) — pre-existing setup_logging propagate=False pollution, proven identical with quick-260914-g63 changes reverted; already tracked as 04-UAT deferred follow-up | open |  | 2026-09-14T04:11:18.859Z |  |

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
  },
  {
    "id": 3,
    "kind": "unmet-truth",
    "phase": "quick-260905-tax",
    "file": "tests/unit/embedding/test_openai_embedder.py",
    "line": 195,
    "description": "Full-suite green truth unmet: 2 pre-existing caplog failures (test_docs.py triggers setup_logging which sets sif logger propagate=False); proven unrelated to G-04-4 fix, documented in quick/260905-tax.../deferred-items.md",
    "status": "open",
    "reason": "",
    "recorded_at": "2026-09-05T13:30:50.522Z",
    "resolved_at": null
  },
  {
    "id": 4,
    "kind": "unmet-truth",
    "phase": "quick-260914-g63",
    "file": "tests/unit/embedding/test_openai_embedder.py",
    "line": null,
    "description": "Full-suite pytest gate not green on this machine: 2 caplog-pollution failures (test_import_error_logs_install_hint, test_corrupt_cache_treated_as_miss) — pre-existing setup_logging propagate=False pollution, proven identical with quick-260914-g63 changes reverted; already tracked as 04-UAT deferred follow-up",
    "status": "open",
    "reason": "",
    "recorded_at": "2026-09-14T04:11:18.859Z",
    "resolved_at": null
  }
]
````
