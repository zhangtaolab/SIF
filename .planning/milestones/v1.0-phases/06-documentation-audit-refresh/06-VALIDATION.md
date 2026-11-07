---
phase: "06"
slug: "documentation-audit-refresh"
# Retroactive reconstruction at milestone v1.0 close (2026-11-06) — the phase predates the
# validation-artifact convention; this file was created by /gsd-validate-phase State B from
# on-disk artifacts (PLAN/SUMMARY set + live test tree), not seeded at plan time.
status: validated
nyquist_compliant: true
wave_0_complete: true
created: "2026-11-06"
validated: "2026-11-06"
---

# Phase 06 — Validation Strategy

> Documentation audit & refresh: all docs accurately reflect the CLI, API, and configuration;
> every code example is syntax-checked or executed.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x (docs suite: `tests/test_docs.py`, 13 tests, 1 class) |
| **Config file** | `pyproject.toml` `[tool.pytest.ini_options]` |
| **Quick run command** | `env -u FORCE_COLOR NO_COLOR=1 pytest -q tests/test_docs.py` |
| **Full suite command** | `env -u FORCE_COLOR NO_COLOR=1 pytest -q` |
| **Estimated runtime** | ~2 seconds (docs suite) / ~15 seconds (full suite) |
| **Generators** | `make docs-generate` (cli-reference + configuration), `scripts/generate_arch_diagram.py` |
| **CI** | `.github/workflows/docs.yml` — docs tests + both generators + blocking drift gate (`git diff --exit-code`, no `\|\| true`) |

---

## Sampling Rate

- **After every docs change:** `pytest -q tests/test_docs.py` + `make docs-generate` (zero-diff check)
- **Before commit:** full suite green under `fail_under = 90`
- **FORCE_COLOR must be unset (not 0) + NO_COLOR=1** in agent shells (known spurious-failure mode)

---

## Per-Task Verification Map

Requirements DOC-01..DOC-07 are phase-local IDs (predate the REQUIREMENTS.md registration
convention; definitions recovered in 06-VERIFICATION.md § Requirements Coverage). Original
plans 06-01..06-07 carry no requirements frontmatter; they map 1:1 by plan title.

| Requirement / Task cluster | Automated verification | Status |
|---|---|---|
| DOC-01 CLI reference accuracy (06-01, 06-08) | `test_cli_reference_has_all_commands` (derives expected set from live Click tree) + `make docs-generate` zero-diff drift gate | COVERED |
| DOC-02 Configuration guide accuracy (06-02, 06-08) | `test_configuration_no_phantom_fields` + `test_configuration_model_type_validation_is_truthful` (26 rows vs live `Settings.model_fields`) | COVERED |
| DOC-03 Quickstart commands execute (06-03) | `test_shell_commands_exist` (CliRunner per-command existence over every bash block) | COVERED |
| DOC-04 README accuracy (06-04) | `test_no_removed_commands_in_docs` + `test_model_names_are_current` + `test_no_bare_search_command` + `test_no_collection_delete_command` + `test_no_positional_args_for_option_only_commands` | COVERED |
| DOC-05 Technical docs current (06-05) | Same drift-lock set over `DOCS_FILES` (mcp-server, search-algorithms, architecture, models in the validated set) | COVERED |
| DOC-06 Code examples checked (06-06) | `test_json_blocks_are_valid` + `test_json_output_examples_have_expected_keys` + `test_python_blocks_are_valid_syntax` + `test_sql_blocks_are_valid` + `test_shell_commands_exist` | COVERED |
| DOC-07 Docs test infrastructure (06-07) | The suite itself (13 tests) + `make docs-test`/`make docs-generate` + CI docs.yml (all exercised green at this reconstruction: 13/13 passed 2026-11-06) | COVERED |
| G-06-1..G-06-8 gap closures (06-08/09/10) | Same automated set — every gap truth in 06-VERIFICATION.md rows 8-14 is held by a named lock in test_docs.py or the drift gate | COVERED |

---

## Manual-Only

None — every requirement has automated verification.

---

## Sign-Off

- **Reconstructed:** 2026-11-06 (milestone v1.0 close, stale-verification regeneration)
- **Evidence:** docs suite 13/13 green on the current tree (run twice 2026-11-06); full suite 1011 passed @ 96.21%; `make docs-generate` zero-diff verified in 06-VERIFICATION.md truth 8 and re-confirmed by the CI drift-gate design.

---

## Validation Audit

| Metric | Count |
|---|---|
| Gaps found | 0 |
| Resolved | 0 |
| Escalated | 0 |
