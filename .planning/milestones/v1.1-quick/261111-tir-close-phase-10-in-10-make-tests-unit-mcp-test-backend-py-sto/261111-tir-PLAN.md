---
phase: quick-261111-tir
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - tests/unit/mcp/test_backend.py
  - .planning/milestones/v1.0-phases/10-raise-pytest-coverage-to-90/10-REVIEW-DISPOSITION.md
autonomous: true
requirements:
  - PHASE10-IN-10
estimate:
  tokens: 12000
  raw_tokens: 12000
  tasks: 2
  confidence: low
must_haves:
  truths:
    - "Running the whole tests/unit/mcp/test_backend.py file no longer creates the shared /tmp database file: with the sentinel removed beforehand, a full file run (27 tests) leaves it absent — hermetic under pytest-xdist and read-only-/tmp sandboxes"
    - "All 27 existing tests pass with their assertions preserved: the db_path equality assertion tracks the fixture's tmp_path-scoped path, and every mocked repository/pipeline touchpoint behaves exactly as before (no mock semantics changed)"
    - "Zero occurrences of the shared /tmp database path literal remain anywhere in the file (baseline at HEAD 3a4b47b: exactly 4, at lines 28, 34, 57, 330), and no src/ file changes"
    - "Phase 10 IN-10 is recorded as fixed in both ledger representations, the open count is exactly one less than the execution-time HEAD value with total still 22, and every other finding record remains byte-identical"
  artifacts:
    - tests/unit/mcp/test_backend.py
    - .planning/milestones/v1.0-phases/10-raise-pytest-coverage-to-90/10-REVIEW-DISPOSITION.md
  key_links:
    - "backend fixture -> SearchBackend(str(tmp_path / 'test.db')) -> _run_in_db's DatabaseConnection opens a per-test isolated file instead of the shared /tmp location (fixes the four flagged tests AND every other fixture-based test)"
    - "_settings_backend(db_path) helper + the factory-settings test -> direct constructions receive tmp_path-scoped paths -> the weight-fallback tests' real connections stay inside tmp_path"
    - "IN-10 YAML disposition + IN-10 markdown row with Source cell + execution-time open-count decrement -> one consistent review ledger with no unrelated edits"
---

<objective>
Close Phase 10 IN-10 only. The finding ("Backend tests construct a real DatabaseConnection('/tmp/test.db') outside tmp_path", 10-REVIEW.md:213-217) names tests/unit/mcp/test_backend.py: the `backend` fixture (line 28) and the direct constructions (lines 57, 330) hand SearchBackend a hardcoded shared /tmp database path, and the flagged tests (test_hybrid_search_mocks, test_get_document_found, test_get_document_with_line_slicing, test_get_document_not_found) patch repositories but not DatabaseConnection, so `_run_in_db` really opens — and sqlite creates — the shared file. Verified live at planning time: the file is recreated by a plain run of this test file. This plan points the fixture and both direct-construction sites at pytest's function-scoped tmp_path (the finding's first suggested fix, and the coordinator's preferred shape), keeps every existing assertion green, proves the pollution is gone with a remove-run-check sentinel (RED before, GREEN after), and closes IN-10 in the disposition ledger with the three-edit convention.

Scope is ONLY this finding. Sibling batch items own their own findings: IN-01/CR-01/CR-02 (item tip, triage-only), IN-06 (item tiq, src/sif/cli/main.py), IN-09 (item tis, docs/api-reference.md) are NOT swept here. All other IN/CR/WR records stay untouched. This is a TEST-ONLY change — no src/ edits.

Purpose: make the MCP backend unit tests filesystem-hermetic so the suite stops polluting a shared location and cannot interfere with itself under parallel execution or a read-only sandbox.
Output: a tmp_path-scoped test_backend.py (fixture + assertion + two direct-construction sites), RED/GREEN sentinel evidence, and IN-10 marked fixed without disturbing any other review item.
</objective>

<execution_context>
@~/.claude/gsd-core/workflows/execute-plan.md
@~/.claude/gsd-core/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md
@.planning/milestones/v1.0-phases/10-raise-pytest-coverage-to-90/10-REVIEW.md
@.planning/milestones/v1.0-phases/10-raise-pytest-coverage-to-90/10-REVIEW-DISPOSITION.md
@tests/unit/mcp/test_backend.py
@src/sif/mcp/backend.py
@src/sif/database/connection.py

Planning evidence (all grounded live at planning-time HEAD 3a4b47b):
- The shared-path literal occurs exactly 4 times in tests/unit/mcp/test_backend.py: line 28 (fixture construction), line 34 (the `backend.db_path ==` assertion in test_search_backend_init), line 57 (test_search_backend_forwards_api_settings_to_factory), line 330 (the `_settings_backend()` helper). A repo-wide grep of tests/ and src/ confirms this file is the ONLY user of that exact path — the sentinel check on this one file covers the whole finding. Other test files use different /tmp literals; those are outside IN-10's named scope and stay untouched.
- RED prototyped live: `rm -f` the sentinel, then `python -m pytest tests/unit/mcp/test_backend.py --no-cov -q` -> 27 passed in 0.15s, and the sentinel file was RECREATED (4096 bytes). The pollution is real and the sentinel gate is non-vacuous. Baseline: 27 tests in the file, all green.
- Mechanics (src/sif/mcp/backend.py + src/sif/database/connection.py): SearchBackend.__init__ NEVER opens the database — it stores db_path, resolves settings, and attempts embedder creation (fail-soft). DatabaseConnection is instantiated only inside `_run_in_db`'s worker (backend.py:113), i.e. per hybrid_search/get_document/get_documents_by_pattern/get_status call; `transaction()` connects, commits, closes, and requires no schema. Every repository/pipeline touchpoint in the affected tests is mocked, so swapping the shared path for an empty per-test tmp_path file is behavior-identical — only the file's location changes.
- The fixture edit alone fixes MORE than the four flagged tests: test_get_documents_by_pattern, test_get_documents_by_pattern_max_bytes, both alias tests, and TestHybridSearchWeightOverrides.test_request_weights_flow_into_options also call _run_in_db through the fixture with DatabaseConnection unmocked. The two remaining weight-fallback tests use `_settings_backend()` (line 330) and need the helper change. test_get_status already patches sif.mcp.backend.DatabaseConnection (line 280) — the in-file precedent — and stays exactly as it is. TestZeroResultSuggestions builds real DBs under tmp_path already and is untouched.
- pytest's tmp_path is function-scoped and cached per test: when the `backend` fixture requests tmp_path and the test also requests it, both see the SAME directory — so test_search_backend_init can assert `backend.db_path == str(tmp_path / "test.db")` consistently. Path is already imported (line 9); no import changes anywhere. The file's existing helper convention `_suggestion_backend(db_path: Path, settings)` (line 498) is the model for giving `_settings_backend` a db_path parameter.
- Ledger closure convention (verified against the live ledger and prior closure commits 7be1412/8f16b1e/a43007a): exactly three scoped edits — YAML `disposition: open` -> `fixed` in the IN-10 block, aggregate open-count decrement, and the IN-10 markdown row replacement with a Source cell naming quick 261111-tir. This ledger does NOT use `**Status:** resolved` lines; do not introduce one. Keep every other record byte-identical.
- SHARED-LEDGER RULE (batch 261111-ti*): sibling items tip (closes IN-01/CR-01/CR-02, decrement 3), tiq (IN-06, decrement 1), and tis (IN-09, decrement 1) close records in the SAME ledger, and the scheduler serializes the overlap via files_modified. At planning time the ledger reads `open: 13` / `total: 22` and is byte-clean against HEAD 3a4b47b, but by execution time siblings may have landed first. The open-count edit MUST read the CURRENT count from execution-time `git show HEAD:<ledger>` and decrement by 1 — never hardcode 13->12 (or any other number) as a replacement literal. The Task 2 gate reconstructs the expected file from execution-time HEAD plus the three replacements (count computed dynamically) and asserts byte-equality. Because siblings may already have closed IN-01/IN-06/IN-09/CR-01/CR-02, the gate asserts preservation ONLY of rows no sibling owns (WR-07, WR-08, IN-02, IN-03, IN-04, IN-05, IN-07) — never the sibling-owned rows' state.
- Test environment: PATH python/pytest (miniconda base, Python 3.13.9), NOT .venv (no torch). Targeted runs need `--no-cov` (addopts carry --cov with fail_under=90); the full-suite gate runs WITH coverage (baseline 1528 passed). The suite is color-env-hermetic (conftest scrub, commit 6522663) — plain `python -m pytest` works.
- Discovery level 0: a test-fixture path correction following the finding's own suggested fix and in-file tmp_path precedents; no new dependency, external integration, or research. No src/ changes, so ty check src/sif is a regression gate only.
- Scope guard: sibling-owned files (src/sif/cli/main.py — tiq; docs/api-reference.md — tis), generator-owned docs (docs/cli-reference.md, docs/configuration.md — never hand-edit), and every other finding stay untouched. The working tree carries pre-existing uncommitted `.planning/` churn (config.json, state.json, agent-history.json, PATTERNS files, research cache, 16-REVIEW iter2 files, tmp/, quick-batches/) that predates this task — never stage, commit, or revert any of it; commits touch only task-scoped paths. Per the batch coordinator, phase-scoped capability detectors (api-coverage, assumption-delta, schema-push, security threat-model) resolve to skipped for this phaseless quick item: no COVERAGE.md and no threat_model block.
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Scope backend test DB paths to tmp_path (sentinel RED to GREEN)</name>
  <files>tests/unit/mcp/test_backend.py</files>
  <behavior>
    - RED (pollution demonstrated): with the shared /tmp database sentinel removed, running the UNMODIFIED test file passes all 27 tests AND recreates the sentinel file — the remove-run-check sequence ends with the file present. Record the console output and the sentinel's post-run existence/size as evidence.
    - GREEN (pollution gone): after the edits, the identical remove-run-check sequence passes all 27 tests AND ends with the sentinel absent.
    - Static gate: zero occurrences of the shared-path literal remain in the file (baseline: exactly 4, at lines 28, 34, 57, 330 — the gate fails at baseline, so it is non-vacuous).
    - Preservation: every existing assertion keeps its meaning; the db_path equality assertion compares against the fixture's tmp_path-scoped path; all repository/pipeline mocks and the line-280 DatabaseConnection patch are unchanged; no src/ file is touched.
  </behavior>
  <action>
  Work only in tests/unit/mcp/test_backend.py. First, at execution time and BEFORE any edit, demonstrate and record RED from the checkout root: remove the shared /tmp database sentinel if present (`rm -f /tmp/test.db`), run `python -m pytest tests/unit/mcp/test_backend.py --no-cov -q` (expect 27 passed), then confirm the sentinel was recreated (`test -e /tmp/test.db` and `ls -la /tmp/test.db`). Save the pytest console output plus the sentinel check result to `.planning/quick/261111-tir-close-phase-10-in-10-make-tests-unit-mcp-test-backend-py-sto/261111-tir-red.txt` (planning-time prototype at HEAD 3a4b47b: 27 passed in 0.15s, sentinel recreated at 4096 bytes). If the sentinel is NOT recreated at execution time, stop and re-assess — the finding would no longer be live.

  Then make exactly four scoped edits, replacing the hardcoded shared /tmp database path with tmp_path-scoped paths (the finding's first suggested fix). Do not spell the old absolute path into any new docstring or comment. (1) The `backend` fixture (lines 23-28): add a `tmp_path: Path` parameter and construct `SearchBackend(str(tmp_path / "test.db"))`; keep the get_settings patch and `MagicMock(embedding_dim=1024)` exactly as they are. (2) `test_search_backend_init` (lines 31-35): add a `tmp_path: Path` parameter and change the db_path assertion to `assert backend.db_path == str(tmp_path / "test.db")` — pytest's function-scoped tmp_path is the same directory in the fixture and the test, so this stays consistent; keep the settings assertion. (3) `test_search_backend_forwards_api_settings_to_factory` (line 39): add a `tmp_path: Path` parameter and construct with `str(tmp_path / "test.db")` at line 57; every factory assertion stays unchanged. (4) The `_settings_backend` helper (lines 321-330): change its signature to `_settings_backend(db_path: Path) -> SearchBackend` (mirroring the in-file `_suggestion_backend(db_path, settings)` convention at line 498) and construct `SearchBackend(str(db_path))`; update its two callers — `test_absent_fields_fall_back_to_server_settings` (line 354) and `test_request_field_overrides_settings` (line 368) — to take `tmp_path: Path` and call `_settings_backend(tmp_path / "test.db")`. Path is already imported (line 9); no import changes.

  Change nothing else: no mock semantics, no assertion rewrites beyond the one db_path equality, no reordering. test_get_status's DatabaseConnection patch (line 280) stays; TestZeroResultSuggestions and its real tmp_path DBs stay; the weight-override and validation classes keep every assertion. Do not touch any src/ file, any other test file, sibling-owned files (src/sif/cli/main.py, docs/api-reference.md), or generator-owned docs. If the formatting check complains, run ruff format on the task file only.

  Then demonstrate GREEN: `rm -f /tmp/test.db`, run `python -m pytest tests/unit/mcp/test_backend.py --no-cov -q` (expect 27 passed), and assert the sentinel was NOT recreated (`test ! -e /tmp/test.db`). Save the console output plus the sentinel check result to `.planning/quick/261111-tir-close-phase-10-in-10-make-tests-unit-mcp-test-backend-py-sto/261111-tir-green.txt`. Commit only tests/unit/mcp/test_backend.py (suggested message: `test(quick-261111-tir): scope backend test DB paths to tmp_path (IN-10)`); never stage the pre-existing .planning/ churn or the evidence files.
  </action>
  <verify>
    <automated>rm -f /tmp/test.db &amp;&amp; python -m pytest tests/unit/mcp/test_backend.py --no-cov -q &amp;&amp; test ! -e /tmp/test.db &amp;&amp; ! grep -q '/tmp/test\.db' tests/unit/mcp/test_backend.py &amp;&amp; ruff check tests/unit/mcp/test_backend.py &amp;&amp; ruff format --check tests/unit/mcp/test_backend.py</automated>
  </verify>
  <done>RED evidence recorded (27 passed, sentinel recreated before the fix); after the four edits the same remove-run-check leaves the sentinel absent with all 27 tests green; the shared-path literal has zero occurrences in the file (baseline 4); the db_path assertion tracks the tmp_path-scoped fixture path; every other assertion and mock is unchanged; no src/ delta; ruff and formatting pass on the task file; RED and GREEN console evidence saved in the item output directory.</done>
</task>

<task type="auto">
  <name>Task 2: Close only IN-10 in the Phase 10 disposition ledger</name>
  <files>.planning/milestones/v1.0-phases/10-raise-pytest-coverage-to-90/10-REVIEW-DISPOSITION.md</files>
  <action>
  In .planning/milestones/v1.0-phases/10-raise-pytest-coverage-to-90/10-REVIEW-DISPOSITION.md, make exactly three scoped updates after Task 1 passes:

  1. In the IN-10 YAML finding block only, change `disposition: open` to `disposition: fixed`; preserve its id, severity (info), and title.
  2. Decrement the aggregate `open:` count by exactly 1 from its CURRENT execution-time value. Read the current count from `git show HEAD:<ledger>` at execution time — sibling items tip (decrements 3), tiq (1), and tis (1) may already have landed (planning-time value was 13, but do NOT hardcode any number as a replacement literal). Leave `total: 22` and the original `recorded` timestamp unchanged.
  3. Replace the IN-10 markdown row with `| IN-10 | info | fixed | quick 261111-tir (backend fixture and direct constructions use tmp_path-scoped DB paths; sentinel-verified no shared /tmp database creation) |`.

  Preserve every other YAML block, markdown row, ordering, explanatory paragraph, and trailing newline byte-for-byte. IN-01/CR-01/CR-02 (tip), IN-06 (tiq), and IN-09 (tis) may legitimately already be fixed by sibling items at execution time — do not assert their state and do not touch their records; every other finding is preserved exactly as found. Do not introduce any `**Status:**` line (that format belongs to other ledger types), do not edit the historical 10-REVIEW.md, other review ledgers, or STATE.md; the orchestrator owns quick-task state updates.

  Run the verification gate before committing the ledger edit; commit only this ledger path (suggested message: `docs(quick-261111-tir): close Phase 10 IN-10 in disposition ledger`), never the pre-existing .planning/ churn.
  </action>
  <verify>
    <automated>python -I -c "from pathlib import Path; import re, subprocess; path = '.planning/milestones/v1.0-phases/10-raise-pytest-coverage-to-90/10-REVIEW-DISPOSITION.md'; before = subprocess.check_output(['git', 'show', 'HEAD:' + path], text=True); yaml_old = '  - id: IN-10\n    severity: info\n    disposition: open\n'; yaml_new = '  - id: IN-10\n    severity: info\n    disposition: fixed\n'; row_old = '| IN-10 | info | open | - |'; row_new = '| IN-10 | info | fixed | quick 261111-tir (backend fixture and direct constructions use tmp_path-scoped DB paths; sentinel-verified no shared /tmp database creation) |'; assert before.count(yaml_old) == 1; assert before.count(row_old) == 1; counts = re.findall(r'\nopen: (\d+)\n', before); assert len(counts) == 1; expected = before.replace(yaml_old, yaml_new, 1).replace(row_old, row_new, 1); expected = re.sub(r'\nopen: \d+\n', '\nopen: %d\n' % (int(counts[0]) - 1), expected, count=1); assert expected != before; assert Path(path).read_text(encoding='utf-8') == expected; assert '\ntotal: 22\n' in expected; assert all(row in expected for row in ('| WR-07 | warning | open | - |', '| WR-08 | warning | open | - |', '| IN-02 | info | open | - |', '| IN-03 | info | open | - |', '| IN-04 | info | open | - |', '| IN-05 | info | open | - |', '| IN-07 | info | open | - |')); print('IN-10-fixed; open-count-decremented-from-execution-time-HEAD; all-other-ledger-content-unchanged')"</automated>
  </verify>
  <done>IN-10 is fixed in YAML and the table, the open count is exactly one less than the execution-time HEAD value with total still 22, the Source cell names quick 261111-tir, and an exact execution-time baseline reconstruction proves no other ledger content changed (sibling-owned rows deliberately not state-asserted).</done>
</task>

</tasks>

<verification>
Source coverage audit (the quick constraint selects exactly one finding; no RESEARCH artifact or locked D-XX decisions exist):

| SOURCE | ID | Item | Task | Status |
|--------|----|------|------|--------|
| GOAL | quick-261111-tir | Close Phase 10 IN-10: test_backend.py stops creating the shared /tmp database file; assertions stay green; sentinel-verified; three-edit ledger closure | 1-2 | COVERED |
| REQ | PHASE10-IN-10 | Fixture (line 28) + direct constructions (lines 57, 330) tmp_path-scoped, line-34 assertion updated consistently, four flagged tests (and all other fixture users) no longer touch /tmp, disposition update | 1-2 | COVERED |
| CONTEXT | orchestrator notes | Sentinel RED/GREEN evidence recorded; shared-ledger execution-time-robust count decrement; three-edit closure with Source cell naming quick 261111-tir; byte-equality reconstruction gate; no Status-resolved lines; PATH pytest --no-cov targeted, full quality suite + ty at end; preserve working-tree churn; never hand-edit generator docs; no threat_model/COVERAGE.md (phaseless quick item) | 1-2 | COVERED |
| CONTEXT | sibling items | IN-01/CR-01/CR-02 (tip), IN-06 (tiq), IN-09 (tis), all other IN/CR/WR findings; other test files' distinct /tmp literals | - | EXCLUDED BY BATCH SCOPE, not silently omitted; ledger preservation verified by byte-equality reconstruction |

No external API integration or core-assumption generalization is in scope (quick mode: phase-scoped detectors have no phase input and are skipped). No schema file is touched, so no schema-push task applies. No package installs, so no legitimacy gate applies.

Final gates, run from the checkout root after both tasks:
1. `python -m pytest tests/unit/mcp/test_backend.py -q --no-cov` (27 passed)
2. `rm -f /tmp/test.db && python -m pytest tests/unit/mcp/test_backend.py --no-cov -q && test ! -e /tmp/test.db` (sentinel stays absent)
3. `ruff check src tests`
4. `ruff format --check src tests`
5. `python -m pytest` (full run includes the coverage gate; PATH pytest, not .venv; baseline 1528 passed)
6. `ty check src/sif` (regression gate — no src/ changes expected)
7. `git diff HEAD --exit-code -- src/ docs/` proves no source or docs delta anywhere in this item (sibling-owned src/sif/cli/main.py and docs/api-reference.md included).
8. Review the scoped diff: only `tests/unit/mcp/test_backend.py` (four scoped edits) and the Phase 10 disposition ledger (three edits) carry task changes; commits touch only those task-scoped paths and never stage the pre-existing `.planning/` churn. Planning SUMMARY/STATE artifacts are handled separately by the orchestrator.
</verification>

<success_criteria>
- The pollution is demonstrably red before the fix (sentinel recreated by a plain file run, 27 tests passing) and green afterward (sentinel absent, same 27 tests passing), with both console captures saved as evidence.
- The fixture, the db_path assertion, the factory-settings test, and the _settings_backend helper plus its two callers are the ONLY test-file edits; every other assertion, mock, and test stays unchanged; zero occurrences of the shared-path literal remain.
- IN-10 alone becomes fixed, the ledger open count is exactly one less than its execution-time HEAD value, and exact baseline reconstruction proves every other review record remains unchanged.
- Full ruff, format, pytest (with coverage), and ty quality gates pass; no src/ or docs/ delta.
</success_criteria>

<output>
Create `.planning/quick/261111-tir-close-phase-10-in-10-make-tests-unit-mcp-test-backend-py-sto/261111-tir-SUMMARY.md` with `status: complete` in SUMMARY frontmatter when done. Record the closed finding as Phase 10 IN-10 (backend tests' shared /tmp database path, test_backend.py lines 28/34/57/330 — the finding's sole named file), the RED-to-GREEN sentinel evidence (recreated before the fix, absent after; console captures in 261111-tir-red.txt / 261111-tir-green.txt), and the ledger open-count decrement observed at execution time (from the execution-time HEAD value, whatever siblings landed first). Do not commit planning artifacts or STATE.md; the orchestrator handles the docs/state commit.
</output>
