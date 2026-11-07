---
schema_version: 1
open_count: 6
waived_count: 0
fixed_count: 2
total_count: 8
last_updated: 2026-11-06T00:59:43.130Z
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
| 5 | 261105-g1u | deviation | src/sif/cli/main.py | 71 | Group callback unconditionally mkdirs index parent dir for every command; guarded context add/list create no DB file but do create the empty parent dir (pre-existing, logged to quick-task deferred-items.md) | open |  | 2026-11-05T03:54:46.185Z |  |
| 6 | 10 | deviation | src/sif/utils/logging.py | 122 | Applied computed formatter to caller-provided logging handlers (Rule 1 bug found by 10-05 tests) | fixed |  | 2026-11-05T19:46:51.982Z | 2026-11-05T19:47:02.697Z |
| 7 | 10 | deviation | src/sif/utils/progress.py | 44 | Omitted Rich bar and percentage columns for indeterminate progress (Rule 1 bug found by 10-05 tests) | fixed |  | 2026-11-05T19:46:52.058Z | 2026-11-05T19:47:02.774Z |
| 8 | 10.1 | deviation | .planning/phases/10.1-address-tech-debt-path-normalization-review-findings-cr-01-c/10.1-01-PLAN.md |  | Plan verify command 'pytest <2 files> -q' structurally cannot exit 0 under the 10-07 fail_under=90 gate (scoped run ~38% total); test signal verified via --no-cov plus full-suite 968-pass at 96.22% | open |  | 2026-11-06T00:59:43.130Z |  |

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
  },
  {
    "id": 5,
    "kind": "deviation",
    "phase": "261105-g1u",
    "file": "src/sif/cli/main.py",
    "line": 71,
    "description": "Group callback unconditionally mkdirs index parent dir for every command; guarded context add/list create no DB file but do create the empty parent dir (pre-existing, logged to quick-task deferred-items.md)",
    "status": "open",
    "reason": "",
    "recorded_at": "2026-11-05T03:54:46.185Z",
    "resolved_at": null,
    "milestone": "v1.0"
  },
  {
    "id": 6,
    "kind": "deviation",
    "phase": "10",
    "file": "src/sif/utils/logging.py",
    "line": 122,
    "description": "Applied computed formatter to caller-provided logging handlers (Rule 1 bug found by 10-05 tests)",
    "status": "fixed",
    "reason": "",
    "recorded_at": "2026-11-05T19:46:51.982Z",
    "resolved_at": "2026-11-05T19:47:02.697Z",
    "milestone": "v1.0"
  },
  {
    "id": 7,
    "kind": "deviation",
    "phase": "10",
    "file": "src/sif/utils/progress.py",
    "line": 44,
    "description": "Omitted Rich bar and percentage columns for indeterminate progress (Rule 1 bug found by 10-05 tests)",
    "status": "fixed",
    "reason": "",
    "recorded_at": "2026-11-05T19:46:52.058Z",
    "resolved_at": "2026-11-05T19:47:02.774Z",
    "milestone": "v1.0"
  },
  {
    "id": 8,
    "kind": "deviation",
    "phase": "10.1",
    "file": ".planning/phases/10.1-address-tech-debt-path-normalization-review-findings-cr-01-c/10.1-01-PLAN.md",
    "line": null,
    "description": "Plan verify command 'pytest <2 files> -q' structurally cannot exit 0 under the 10-07 fail_under=90 gate (scoped run ~38% total); test signal verified via --no-cov plus full-suite 968-pass at 96.22%",
    "status": "open",
    "reason": "",
    "recorded_at": "2026-11-06T00:59:43.130Z",
    "resolved_at": null,
    "milestone": "v1.0"
  }
]
````
