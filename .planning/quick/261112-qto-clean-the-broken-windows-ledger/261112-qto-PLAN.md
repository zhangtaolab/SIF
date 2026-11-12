---
phase: quick-261112-qto
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - .planning/WINDOWS.md
  - src/sif/cli/main.py
  - tests/unit/cli/test_main.py
autonomous: true
must_haves:
  truths:
    - ".planning/WINDOWS.md reports open_count 0, waived_count 3, fixed_count 7, total_count 10; entries 3, 4, and 5 are fixed; entries 1, 2, and 8 are waived with non-empty explicit reasons; and the rendered markdown table agrees with the authoritative fenced JSON block."
    - "Running `python -m pytest tests/test_docs.py tests/unit/embedding/test_openai_embedder.py -q --no-cov` yields 31 passed when the two files run together, grounding the caplog closures for ledger entries 3 and 4."
    - "The top-level CLI group callback no longer materializes the index parent directory: `sif --index <absent-parent>/sif.db context list` and `context add ...` both exit 0 with 'No index found' and leave neither the parent directory nor the DB file behind."
    - "Index-creating commands still get parent creation from the shared DB-open boundary: `sif --index <absent-parent>/sif.db index update` creates the parent and DB and prints the no-collections message; a regular file in the parent path still renders the remedy-bearing ClickException with no traceback."
    - "The full quality suite is green: `ruff check src tests`, `ruff format --check src tests`, and `python -m pytest -q --ignore=tests/unit/cli/test_probe_qtn.py` under the fail_under=90 coverage gate (the ignored path is a sibling item's planner probe, harmless when absent)."
  artifacts:
    - .planning/WINDOWS.md
    - src/sif/cli/main.py
    - tests/unit/cli/test_main.py
  key_links:
    - "cli group callback (src/sif/cli/main.py) -> unconditional parent mkdir removed -> Database.__init__ (src/sif/database/database.py:20) inside open_initialized_database's OSError boundary becomes the single owner of index-parent creation"
    - "node ~/.claude/gsd-core/bin/gsd-tools.cjs windows fixed/waive verbs -> authoritative JSON block -> regenerated markdown table and frontmatter counts stay consistent (the tool refuses table drift)"
    - "caplog evidence pair (tests/test_docs.py + tests/unit/embedding/test_openai_embedder.py run together) -> 31 passed -> entries 3 and 4 marked fixed"
---

<objective>
Clean the Broken Windows ledger to open_count 0 through its own verbs, and close the one live code deviation among its open entries.

Current ledger state (measured with `gsd-tools windows status` at planning time): 6 open entries — ids 1, 2, 3, 4, 5, 8; 4 fixed; 0 waived; 10 total.

Dispositions:
- id 1 (HuggingFace factory stub) — waive with an explicit reason: deliberate, documented scope boundary, re-verified live at `src/sif/embedding/factory.py:86-92` and in `src/sif/config/settings.py:310-311`.
- id 2 (live OpenAI-compatible endpoint check) — waive with an explicit reason: requires a user API key plus a live endpoint; all automated coverage mocks the endpoint.
- ids 3 and 4 (caplog-pollution failures) — fix: re-run the exact pair `tests/test_docs.py` + `tests/unit/embedding/test_openai_embedder.py` together and record 31 passed.
- id 5 (group-callback mkdir side effect) — fix in code: remove the unconditional parent mkdir from the CLI group callback; `Database.__init__` already owns parent creation inside the shared DB-open boundary, so index-creating commands keep the behavior and the clean remedy while guarded read-only commands stop creating an empty directory.
- id 8 (10.1-01 plan verify command structurally cannot exit 0 under the coverage gate) — waive with an explicit reason: the phase is complete, the plan is archived under `.planning/milestones/v1.0-phases/`, and the intended test signal was verified historically via `--no-cov` plus the full-suite run recorded in the entry.

Purpose: unblock the `workflow.windows_enforce` ship gate (it blocks while `open_count > 0`) and remove a real filesystem side effect instead of papering over it.
Output: a ledger with 0 open / 3 waived / 7 fixed / 10 total, a four-line deletion plus a two-test regression pin in the CLI, and a final green quality suite.
</objective>

<execution_context>
@~/.claude/gsd-core/workflows/execute-plan.md
@~/.claude/gsd-core/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md
@.planning/WINDOWS.md
@src/sif/cli/main.py
@src/sif/cli/error_handling.py
@src/sif/database/database.py
@src/sif/cli/commands/context.py
@tests/unit/cli/test_main.py
@tests/unit/cli/test_error_conventions.py

Planning-time evidence:
- The group callback in `src/sif/cli/main.py:74-79` unconditionally runs `ctx.obj["index_path"].parent.mkdir(parents=True, exist_ok=True)` inside a try/except that converts `OSError` via `_database_remedy`. This is the only use of `_database_remedy` in main.py; `open_initialized_database` is separately imported and used at main.py:175 and main.py:231, so it must stay imported.
- `Database.__init__` already does `self.db_path.parent.mkdir(parents=True, exist_ok=True)` (`src/sif/database/database.py:20`), and every DB-opening CLI command reaches it through `open_initialized_database` / `open_initialized_database_unmanaged` (37 call sites), whose constructor `OSError` boundary converts a file-parent failure into the same remedy-bearing `click.ClickException` (`src/sif/cli/error_handling.py:26-46`).
- Guarded read-only commands (`context add/list/remove`, `ls`, `status`, `cleanup`, `search` variants, etc.) check `index_path.exists()` and return before opening the DB, so today the group mkdir is the only thing that leaves an empty parent directory behind. The ledger names `context add/list` specifically.
- Baseline measurement: `python -m pytest tests/unit/cli/test_main.py::TestIndexPathCreationError -q --no-cov` → 1 passed (the CR-01 clean-remedy pin currently exercises `index update`).
- Baseline measurement: `python -m pytest tests/test_docs.py tests/unit/embedding/test_openai_embedder.py -q --no-cov` → 31 passed, the exact command the ledger closure requires.
- Positive-control ground truth: `python -m sif.cli.main --index <tmp>/fresh/sif.db index update` exits 0, prints "No collections found. Add one with 'sif collection add'.", and creates both `<tmp>/fresh/` and `<tmp>/fresh/sif.db` (plus the lock file) — so removing the group mkdir does not break index creation.
- Entry 8 re-validation: `10.1-01-PLAN.md` now lives at `.planning/milestones/v1.0-phases/10.1-address-tech-debt-path-normalization-review-findings-cr-01-c/10.1-01-PLAN.md`; its verify command is `env -u FORCE_COLOR NO_COLOR=1 pytest tests/unit/cli/test_get.py tests/unit/mcp/test_backend.py -q` with no `--no-cov`, while `pyproject.toml:211` sets `fail_under = 90` repo-wide. The structural impossibility described by the entry still holds; phase 10.1 is complete.
- Entry 1 re-validation: the deliberate HuggingFace stub is still present at `src/sif/embedding/factory.py:86-92` (`raise NotImplementedError("HuggingFace models not yet implemented")`) and `src/sif/config/settings.py:310-311` documents the exclusion.
- Entry 2 re-validation: `.planning/milestones/v1.0-phases/03-embedding-vector-search/03-07-SUMMARY.md` records the live-endpoint check as requiring the user's own API key (line 135: "Requires a live API key and remote service"; line 245: "all automated tests mock the openai module").
- Shared-checkout caveat: this project runs quick-batch with `workflow.use_worktrees=false`, so sibling items execute in this checkout. At planning time `src/sif/cli/commands/watch.py` and `src/sif/indexing/watcher.py` carried in-flight sibling edits and `tests/unit/cli/test_probe_qtn.py` existed as a sibling planner probe labeled "DELETE AFTER RUN". Never modify, delete, stage, or revert any of them; commits must stage only this plan's declared files.
- Discovery level 0: local ledger tooling plus a four-line deletion in an already-understood callback; no new dependency, external integration, or research artifact.
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Remove the group-callback mkdir and pin DB-open ownership of parent creation</name>
  <files>src/sif/cli/main.py, tests/unit/cli/test_main.py</files>
  <behavior>
    - With an absent parent directory, `context list` against `--index <tmp>/never-created/sif.db` exits 0, prints "No index found", and creates neither `never-created/` nor the DB file. This fails before the fix because the group callback creates the parent.
    - With the same absent parent, `context add path <tmp>/note.md note` exits 0, prints "No index found", and creates neither the parent nor the DB. This fails before the fix for the same reason.
    - Positive control: `index update` against `<tmp>/fresh/sif.db` exits 0, prints "No collections found", and creates both the parent directory and the DB file — the gating change must not remove parent creation where the DB is actually opened.
    - Preservation: the existing `TestIndexPathCreationError::test_regular_file_parent_renders_clean_error` still exits 1 with "Cannot open index database at", the permissions/disk/corruption remedy text, no "Traceback", and no `FileExistsError` exception.
  </behavior>
  <action>
  Work test-first in `tests/unit/cli/test_main.py`. After the existing `TestIndexPathCreationError` class (around line 316), add a new class `TestGroupCallbackDoesNotCreateIndexParent` with two tests using `CliRunner().invoke(cli, [...])` and `tmp_path`:

  1. `test_guarded_context_commands_create_no_index_parent`: bind `db_path = tmp_path / "never-created" / "sif.db"`; for each argv in a tuple containing `["context", "list"]` and `["context", "add", "path", str(tmp_path / "note.md"), "note"]`, invoke the top-level `cli` with `["--index", str(db_path), *argv]`; assert exit_code 0, "No index found" in output, `not db_path.parent.exists()`, and `not db_path.exists()`. The first invocation must fail on the parent-existence assertion before the production edit.
  2. `test_db_opening_command_still_creates_index_parent`: bind `db_path = tmp_path / "fresh" / "sif.db"`; invoke `["--index", str(db_path), "index", "update"]`; assert exit_code 0, "No collections found" in output, `db_path.parent.is_dir()`, and `db_path.exists()`. This passes before and after the edit and is the positive control for the gating.

  Then update the now-stale `TestIndexPathCreationError` class docstring from "CR-01: group-level parent creation uses the shared DB-open remedy." to "CR-01: a file-parent DB path uses the shared DB-open remedy." Do not change that test body or any other existing test.

  Run the new guarded test alone and confirm it fails on `assert not db_path.parent.exists()` (RED: the group callback created the directory), not during collection or setup.

  Then edit `src/sif/cli/main.py` only. In the `cli` group callback, delete the block at lines 74-79 that begins with the comment "Create index directory if needed, using the shared DB-open remedy." and calls `ctx.obj["index_path"].parent.mkdir(...)` inside `try/except OSError` with `_database_remedy`. Replace it with a two-line comment stating that index-parent creation belongs to `Database.__init__` inside the shared DB-open boundary, so guarded read-only commands create nothing. On the import line `from sif.cli.error_handling import _database_remedy, open_initialized_database`, drop `_database_remedy` but keep `open_initialized_database` (still used by status and cleanup); leave `Path` imported (still used for `--index` and the watch-status section). Do not touch the group's logging, `ctx.ensure_object`, option storage, command registration, or any command module.

  Run the verification below. Commit only `src/sif/cli/main.py` and `tests/unit/cli/test_main.py`; never stage or revert the sibling in-flight edits in `src/sif/cli/commands/watch.py`, `src/sif/indexing/watcher.py`, `tests/unit/cli/test_probe_qtn.py`, or any other path.
  </action>
  <verify>
    <automated>python -m pytest tests/unit/cli/test_main.py tests/unit/cli/test_context.py tests/unit/cli/test_error_conventions.py tests/unit/db/test_database.py -q --no-cov &amp;&amp; ruff check src/sif/cli/main.py tests/unit/cli/test_main.py &amp;&amp; ruff format --check src/sif/cli/main.py tests/unit/cli/test_main.py</automated>
  </verify>
  <done>The two guarded-command side-effect assertions failed before the production edit and now pass; `index update` still creates the nested parent and DB; the CR-01 file-parent remedy pin and every other test in the four named files pass unmodified; ruff check and format pass; the only production delta is the removed mkdir block plus one comment line and the narrowed import.</done>
</task>

<task type="auto">
  <name>Task 2: Close all six open ledger entries through gsd-tools and run the full quality gate</name>
  <files>.planning/WINDOWS.md</files>
  <action>
  All ledger mutations go through the ledger's own verbs — the CLI holds the cross-process ledger lock, regenerates the markdown table from the authoritative JSON block, and refuses hand-edited drift. Do not hand-edit the JSON block or the table. Invoke the tool as `node "$HOME/.claude/gsd-core/bin/gsd-tools.cjs" windows ...` (equivalent to `gsd-tools windows ...` / `gsd_run windows ...` when on PATH).

  Sequence:

  1. Re-run the evidence pair exactly: `python -m pytest tests/test_docs.py tests/unit/embedding/test_openai_embedder.py -q --no-cov`. Require 31 passed. This is the ground for entries 3 and 4.
  2. Run the project quality gate: `ruff check src tests`, `ruff format --check src tests`, then the full suite with the default coverage flags and the `fail_under=90` floor, excluding only the known sibling planner probe: `python -m pytest -q --ignore=tests/unit/cli/test_probe_qtn.py`. The ignore is harmless when that file has already been deleted and keeps this item's gate about this item; the coordinator's batch-level verification covers sibling items. Record the suite result in the SUMMARY. If any other failure is confined to a file this plan does not modify, report it in the SUMMARY and do not edit that file.
  3. Mark fixed: `windows fixed 3`, `windows fixed 4` (caplog evidence above) and `windows fixed 5` (Task 1 is committed and verified).
  4. Waive id 1 with this reason, quoted as one shell argument: `Deliberate design boundary re-validated at HEAD: the HuggingFace branch in the embedding factory (src/sif/embedding/factory.py:86-92) is an intentional NotImplementedError stub documented in CLAUDE.md and rejected by ModelType/settings validation; it is not a supported backend, so no fix is planned.`
  5. Waive id 2 with this reason: `Manual-only verification re-validated: a live OpenAI-compatible endpoint check requires a user-supplied API key and an external endpoint, so it cannot run in this repo or CI; automated tests mock the endpoint and exercise the request/response path. Structurally unautomatable, hence waived.`
  6. Waive id 8 with this reason: `Historical plan artifact re-validated: the 10.1-01-PLAN.md verify command scoped two test files under the repo-wide coverage gate (fail_under=90 in pyproject.toml), which structurally cannot exit 0 from a scoped run (~38% total); the test signal was verified via --no-cov plus a full-suite 968-pass at 96.22%, and phase 10.1 is complete with the plan archived under .planning/milestones/v1.0-phases/, so the command is not re-runnable as written. Waived as a past planning-constraint record, not a live defect.`
  7. Verify the final ledger with the automated check below, then read `.planning/WINDOWS.md` tail/frontmatter to confirm the regenerated table shows entries 1, 2, 8 as waived and 3, 4, 5 as fixed.

  Every waive reason is required and explicit; do not use an empty or generic reason. Do not alter any entry's id, kind, phase, file, line, description, or recorded_at, and do not add or delete entries — the verbs preserve all untouched fields. Commit only `.planning/WINDOWS.md`; never stage sibling modifications or untracked files from other quick-batch items.
  </action>
  <verify>
    <automated>python -m pytest tests/test_docs.py tests/unit/embedding/test_openai_embedder.py -q --no-cov &amp;&amp; python -I -c "import json, os, subprocess; tools = os.path.expanduser('~/.claude/gsd-core/bin/gsd-tools.cjs'); raw = subprocess.run(['node', tools, 'windows', 'status'], capture_output=True, text=True, check=True).stdout; ledger = json.loads(raw)['ledger']; assert (ledger['open_count'], ledger['waived_count'], ledger['fixed_count'], ledger['total_count']) == (0, 3, 7, 10), ledger; by_id = {e['id']: e for e in ledger['entries']}; assert all(by_id[i]['status'] == 'fixed' for i in (3, 4, 5)), by_id; assert all(by_id[i]['status'] == 'waived' for i in (1, 2, 8)), by_id; assert all(by_id[i]['reason'].strip() for i in (1, 2, 8)), by_id; assert all(by_id[i]['resolved_at'] for i in range(1, 11)), by_id; print('ledger-clean: 0 open / 3 waived / 7 fixed / 10 total')" &amp;&amp; ruff check src tests &amp;&amp; ruff format --check src tests &amp;&amp; python -m pytest -q --ignore=tests/unit/cli/test_probe_qtn.py</automated>
  </verify>
  <done>Entries 3, 4, and 5 are fixed; entries 1, 2, and 8 are waived with the exact explicit reasons above; frontmatter counts are 0 open / 3 waived / 7 fixed / 10 total; the regenerated table is consistent with the JSON block; the evidence pair reports 31 passed; ruff, format, and the full pytest coverage gate are green (or a sibling-only failure is reported and the ignored rerun is green).</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| CLI user input -> top-level group callback filesystem operation | `--index` supplies a path whose parent the callback used to create for every command; guarded commands must not touch a filesystem they never open |
| Ledger operator -> `.planning/WINDOWS.md` | Status/count fields drive the ship gate; hand-editing the table or JSON would desynchronize the authoritative entries from the gate's fast-path counts |

No network, package-install, authentication, or external-service boundary is introduced.

## STRIDE Threat Register

| Threat ID | Category | Component | Severity | Disposition | Mitigation Plan |
|-----------|----------|-----------|----------|-------------|-----------------|
| T-qto-01 | Tampering | .planning/WINDOWS.md entries/table/counts | medium | mitigate | Mutate only through `gsd-tools windows fixed/waive` (lock-protected read-compute-write; regenerates the table; refuses table/JSON drift) and assert the final statuses/counts/reasons programmatically |
| T-qto-02 | Information Disclosure / Denial of Service | CLI group callback parent mkdir | low | mitigate | Remove the unconditional mkdir; parent creation stays inside `Database.__init__` within the shared DB-open error boundary, and regression tests prove guarded commands create nothing while DB-opening commands still do |
| T-qto-SC | Tampering | npm/pip/cargo installs | low | accept | No package-manager install, dependency, or lockfile change exists in this plan; the package legitimacy gate is not applicable |
</threat_model>

<verification>
Source coverage audit (quick-batch item: no ROADMAP requirement IDs, no RESEARCH.md, no locked D-XX decisions):

| SOURCE | ID | Item | Task | Status |
|--------|----|------|------|--------|
| GOAL | 261112-qto | Re-validate every open ledger entry; mark caplog entries fixed; waive HuggingFace stub and API-key check; fix or waive group mkdir | 1-2 | COVERED |
| CONTEXT | ledger 1 | HuggingFace factory stub | 2 | COVERED — re-validated live, waived with explicit reason |
| CONTEXT | ledger 2 | Live OpenAI endpoint manual check | 2 | COVERED — re-validated from 03-07-SUMMARY, waived with explicit reason |
| CONTEXT | ledger 3 | test_docs caplog pollution | 2 | COVERED — 31-passed rerun recorded, marked fixed |
| CONTEXT | ledger 4 | caplog-pollution unmet truth | 2 | COVERED — 31-passed rerun recorded, marked fixed |
| CONTEXT | ledger 5 | Group-callback mkdir side effect | 1-2 | COVERED — fixed in code with regression tests, marked fixed |
| CONTEXT | ledger 8 | 10.1-01 verify command structural coverage conflict | 2 | COVERED — re-validated against the archived plan and pyproject, waived with explicit reason |
| CONTEXT | constraints | Use ledger verbs; 31-passed evidence; mkdir fix-or-waive; table/JSON consistency | 1-2 | COVERED |
| EXCLUDED | sibling items qtk/qtl/qtm/qtn | Other batch items' code, docs, tests, and planner probe artifacts | — | EXCLUDED BY BATCH SCOPE — never modified, staged, or reverted |

Final gates, run from the checkout root after both tasks:
1. `python -m pytest tests/test_docs.py tests/unit/embedding/test_openai_embedder.py -q --no-cov` → 31 passed.
2. `python -m pytest tests/unit/cli/test_main.py tests/unit/cli/test_context.py tests/unit/cli/test_error_conventions.py tests/unit/db/test_database.py -q --no-cov` → green.
3. `ruff check src tests` and `ruff format --check src tests` → green.
4. `python -m pytest -q --ignore=tests/unit/cli/test_probe_qtn.py` → full suite green at or above the 90% coverage floor (the ignore only covers sibling item 261112-qtn's planner probe).
5. `gsd-tools windows status` → 0 open / 3 waived / 7 fixed / 10 total with the per-id statuses asserted.
6. `git show --stat` on each task commit → only the declared files for that task.
</verification>

<success_criteria>
- `.planning/WINDOWS.md` has `open_count: 0`, `waived_count: 3`, `fixed_count: 7`, `total_count: 10`; ids 3, 4, 5 are fixed; ids 1, 2, 8 are waived with specific, non-empty reasons; every entry has a `resolved_at`; the table matches the JSON block.
- The CLI group callback no longer creates the index parent directory; guarded `context add`/`list` leave the filesystem untouched, while `index update` still creates the parent and DB and the file-parent remedy path is unchanged.
- The caplog evidence pair returns 31 passed and the full quality suite is green.
- No file outside this plan's `files_modified` list is modified, staged, or reverted.
</success_criteria>

<output>
Create `.planning/quick/261112-qto-clean-the-broken-windows-ledger/261112-qto-SUMMARY.md` when done, recording: the ledger before/after counts, each entry's final status and reason, the caplog rerun result, the regression-test RED/GREEN evidence, the full-suite result, and any sibling-item artifacts observed but left untouched.
</output>
