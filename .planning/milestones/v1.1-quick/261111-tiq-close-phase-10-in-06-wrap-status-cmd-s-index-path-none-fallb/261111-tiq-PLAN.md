---
phase: quick-261111-tiq
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - src/sif/cli/main.py
  - tests/unit/cli/test_status.py
  - .planning/milestones/v1.0-phases/10-raise-pytest-coverage-to-90/10-REVIEW-DISPOSITION.md
autonomous: true
requirements:
  - PHASE10-IN-06
estimate:
  tokens: 15000
  raw_tokens: 15000
  tasks: 2
  confidence: low
must_haves:
  truths:
    - "Invoking status_cmd with a context obj lacking index_path under invalid env config (SIF_RERANKER_MODEL_TYPE=cross-encoder) exits 1 with a one-line Error: message naming reranker_model_type — no raw pydantic ValidationError escapes; the sif index status alias inherits the same guard through its ctx.invoke delegation"
    - "The fallback guard is the same try/except ValidationError -> click.ClickException(str(e)) from e pattern used by _get_default_db_path; the valid-config path is unchanged (get_db_path() still returns the Path consumed by .exists() and Database)"
    - "The new regression test is red against the planning baseline (HEAD 3a4b47b: result.exception is a pydantic ValidationError and output is empty) and green after the guard; all 18 existing tests in test_status.py and test_main.py pass unmodified"
    - "Phase 10 IN-06 is recorded as fixed in both ledger representations, the open count is decremented by exactly 1 from its execution-time value, and every other finding record remains byte-identical (sibling closures included)"
  artifacts:
    - src/sif/cli/main.py
    - tests/unit/cli/test_status.py
    - .planning/milestones/v1.0-phases/10-raise-pytest-coverage-to-90/10-REVIEW-DISPOSITION.md
  key_links:
    - "status_cmd index_path-None fallback -> guarded get_settings().get_db_path() -> ClickException rendered by Click as a one-line Error (the same contract _get_default_db_path gives group-level --index option parsing)"
    - "Regression test: monkeypatch.setenv -> get_settings.cache_clear() (get_settings is lru_cache'd) -> CliRunner invoke with obj={} -> the fallback branch is the code under test"
    - "IN-06 YAML disposition + IN-06 markdown row + execution-time open-count decrement -> one consistent review ledger with no unrelated edits"
---

<objective>
Close Phase 10 IN-06 only: `status_cmd`'s `index_path is None` fallback calls `get_settings().get_db_path()` without the ValidationError guard used everywhere else. The original finding (10-REVIEW.md:189-193, "IN-06") names `src/sif/cli/main.py:113-114` (stale pre-Phase-13/14 line numbers; live at HEAD 3a4b47b: lines 167-169) and prescribes: "Wrap the fallback in the same try/except ValidationError -> click.ClickException as `_get_default_db_path`." The fallback is reachable whenever status_cmd runs with a context obj lacking index_path — exactly how tests/unit/cli/test_status.py invokes it — so invalid env config escapes there as a raw pydantic traceback.

Live defect reproduction at planning time (HEAD 3a4b47b, PATH miniconda python, click 8.3.2 / pydantic 2.12.5): with SIF_RERANKER_MODEL_TYPE=cross-encoder set and get_settings.cache_clear() called, CliRunner().invoke(status_cmd, [], obj={}) returned exit_code 1 with result.exception = pydantic_core._pydantic_core.ValidationError and EMPTY output — no "Error:" line, no field name. The Settings field_validator validate_reranker_model_type (settings.py:321-336) rejects any value outside {gguf, sentence_transformers}, so "cross-encoder" is a deterministic validation failure naming reranker_model_type. The regression contract is non-vacuous: the same invocation after the guard renders "Error: ...reranker_model_type..." with exit 1 (ClickException handling grounded live: CliRunner stores SystemExit in result.exception after Click renders the error, so the test asserts on output plus a not-ValidationError pin, never isinstance(result.exception, ClickException)).

Purpose: invalid env config on the status fallback path surfaces as the same clean one-line Click error every other settings touchpoint already gives, with a red-to-green regression test proving it.
Output: the guarded fallback in main.py, one regression test in test_status.py, and IN-06 marked fixed in the Phase 10 ledger without disturbing any other review item.
</objective>

<execution_context>
@~/.claude/gsd-core/workflows/execute-plan.md
@~/.claude/gsd-core/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md
@.planning/milestones/v1.0-phases/10-raise-pytest-coverage-to-90/10-REVIEW.md
@.planning/milestones/v1.0-phases/10-raise-pytest-coverage-to-90/10-REVIEW-DISPOSITION.md
@src/sif/cli/main.py
@tests/unit/cli/test_status.py
@tests/unit/cli/test_main.py
@src/sif/config/settings.py

Planning evidence (all grounded live at HEAD 3a4b47b):
- Fix site: src/sif/cli/main.py:167-169 — inside status_cmd, `index_path = ctx.obj.get("index_path")` then `if index_path is None: index_path = get_settings().get_db_path()` UNGUARDED. Guard precedent: _get_default_db_path (main.py:31-42) wraps the identical call in try/except ValidationError as e -> raise click.ClickException(str(e)) from e. Both `click` (line 9) and `ValidationError` (line 10) are already module-level imports — the production edit adds NO imports.
- The guard must keep the fallback's type contract: get_db_path() returns a Path, consumed downstream by index_path.exists() (line 171), Database(index_path) (line 176), and str(index_path) (line 184). Do NOT route the fallback through _get_default_db_path() (it returns str and would break .exists()); wrap the existing call in place, exactly as the finding prescribes.
- Alias coverage: index_status_cmd (src/sif/cli/commands/index.py:387-392) delegates via ctx.invoke(status_cmd) — one code path serves `sif status` and `sif index status`; the guard covers both with no edit in index.py.
- Test precedent: tests/unit/cli/test_main.py:275-309 TestDefaultDbPathConfigError (Phase 11's settings-guard finding, confusingly also labeled "REVIEW WR-09" in its docstring) uses monkeypatch.setenv("SIF_RERANKER_MODEL_TYPE", "cross-encoder"), get_settings.cache_clear() AFTER the env is set and again in a finally block (get_settings is @lru_cache, settings.py:390-396 — a prior cached success would mask the invalid env), then asserts exit_code 1, "Error:" in output, the field name in output, and no "Traceback". Reuse this exact invalid value and cache hygiene. That class and _get_default_db_path itself stay byte-identical — this item closes Phase 10 IN-06, a different finding that extends the same pattern.
- CliRunner exception shape (grounded live, click 8.3.2): a command raising ClickException yields exit_code 1, output "Error: <message>\n", and result.exception = SystemExit — NOT the ClickException instance. Baseline (unfixed) yields result.exception = ValidationError with empty output. Therefore the regression test asserts: exit_code == 1; "Error:" in result.output; "reranker_model_type" in result.output; "Traceback" not in result.output; not isinstance(result.exception, ValidationError). The last pin needs `from pydantic import ValidationError` in the test file. Do NOT assert isinstance(result.exception, click.ClickException) — it is false even when fixed.
- Test home: tests/unit/cli/test_status.py (the file the finding names). It currently imports neither pydantic nor sif.config.settings; add `from pydantic import ValidationError` to the third-party block after the click.testing import and `from sif.config.settings import get_settings` to the first-party block after the sif.cli.main import (ruff isort order). No pytest import is needed — monkeypatch fixture plus plain asserts. Existing culture: TestStatusCommand invokes CliRunner().invoke(status_cmd) with NO obj (ensure_object creates an empty dict, so the fallback fires); the new test passes obj={} explicitly to pin the branch.
- Baseline grounded at planning time: `python -m pytest tests/unit/cli/test_status.py tests/unit/cli/test_main.py -q --no-cov` -> 18 passed in 0.80s at HEAD 3a4b47b (11 in test_status.py, 7 in test_main.py). Working tree matches HEAD for every task-scoped path (git status clean on main.py, test_status.py, test_main.py, and the ledger).
- Ledger state at planning time: open: 13, total: 22; IN-06 YAML block at lines 66-69 (severity info, disposition open) and markdown row `| IN-06 | info | open | - |` at line 118. Siblings tip (closes IN-01/CR-01/CR-02), tir (IN-10), tis (IN-09) edit this same ledger and may land first — Task 2 reads the CURRENT count from execution-time git HEAD and decrements THAT value by 1; never hardcode 13 or any assumed successor.
- Sibling overlap (batch catalog): tip verifies get.py/schema.py/search.py with NO code changes; tir edits tests/unit/mcp/test_backend.py; tis edits docs/api-reference.md. All disjoint from this plan's main.py/test_status.py regions — the ONLY shared file is the disposition ledger, declared in files_modified so the scheduler serializes the overlap. No logical prerequisite exists on any sibling — depends_on is empty.
- Test environment: PATH python/pytest (miniconda base), NOT .venv (no torch). Targeted runs need --no-cov (coverage fail_under=90); the full-suite gate runs WITH coverage. The suite is color-env-hermetic (commit 6522663) — plain `python -m pytest` works. Full-suite baseline 1528 passed; this item adds exactly 1 test.
- Discovery level 0: a four-line guard around one existing call, using the module's own established pattern and the test file's existing CliRunner culture; no new dependency, external integration, or schema change. No CLI signature/option/help change, so generator-owned docs (docs/cli-reference.md, docs/configuration.md — never hand-edit) need no regeneration.
- Scope guard: every other finding stays untouched — _get_default_db_path and TestDefaultDbPathConfigError (Phase 11), query_cmd/vsearch_cmd guards, get.py/schema.py/search.py (sibling tip), test_backend.py (sibling tir), api-reference.md (sibling tis), WR-07/08 MCP files, and skills. The working tree carries pre-existing uncommitted `.planning/` churn (config.json, state.json, agent-history.json, PATTERNS files, research cache, tmp/, 16-REVIEW iter2 files) — never stage, commit, or revert any of it; commits touch only task-scoped paths.
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Guard the status_cmd settings fallback (IN-06, red-to-green regression test)</name>
  <files>tests/unit/cli/test_status.py, src/sif/cli/main.py</files>
  <behavior>
    - With SIF_RERANKER_MODEL_TYPE=cross-encoder and the settings cache cleared, CliRunner().invoke(status_cmd, [], obj={}) exits 1 and renders a one-line "Error:" message naming reranker_model_type, with no "Traceback" in output and result.exception NOT a pydantic ValidationError (baseline: exit 1, empty output, result.exception IS a ValidationError — the test fails on assertions).
    - Preservation: all 18 existing tests in test_status.py and test_main.py pass unmodified, including TestStatusCommand's two fallback happy-path tests (patched get_settings), TestDefaultDbPathConfigError's two guard tests, and the Watch/Vector-lag batteries.
    - The valid-config fallback still assigns the Path returned by get_db_path() — .exists(), Database(index_path), and the table rendering are unchanged.
  </behavior>
  <action>
  FIRST change tests only. In tests/unit/cli/test_status.py add `from pydantic import ValidationError` to the third-party import block (after the click.testing import) and `from sif.config.settings import get_settings` to the first-party block (after the sif.cli.main import), keeping ruff isort order. Append a new class `TestStatusFallbackConfigError` after TestVectorLag with a docstring naming Phase 10 IN-06 and the lru_cache hygiene requirement, containing one test `test_status_fallback_wraps_validation_error(self, monkeypatch) -> None`: monkeypatch.setenv("SIF_RERANKER_MODEL_TYPE", "cross-encoder"); call get_settings.cache_clear() AFTER the env is set (a prior cached success would mask the invalid env); inside try/finally call result = CliRunner().invoke(status_cmd, [], obj={}) with get_settings.cache_clear() in the finally block (monkeypatch restores the env at teardown, so the cache must be empty when it does). Assert result.exit_code == 1; "Error:" in result.output; "reranker_model_type" in result.output; "Traceback" not in result.output; and not isinstance(result.exception, ValidationError). Do NOT assert isinstance(result.exception, click.ClickException) — click 8.3.2's CliRunner stores SystemExit after Click renders a ClickException (grounded live). Do NOT modify any existing test, fixture, or helper in either test file. Run `python -m pytest tests/unit/cli/test_status.py -q --no-cov` before any production edit and confirm the new test FAILS on its assertions (baseline: empty output so the "Error:" assertion fails, and result.exception is a raw ValidationError) while the 11 existing tests pass — the failure must be an assertion failure, never a collection or setup error.

  THEN modify production. In src/sif/cli/main.py status_cmd, wrap ONLY the fallback assignment inside the `if index_path is None:` branch (live lines 168-169) in try/except: the try body keeps `index_path = get_settings().get_db_path()` unchanged; the except clause catches ValidationError as e and raises click.ClickException(str(e)) from e — mirroring _get_default_db_path (lines 39-42) exactly, with a one-line comment naming IN-06 and the shared guard pattern. Both click and ValidationError are already imported at module level; add no imports. Keep the fallback's Path type contract (do not route through _get_default_db_path, which returns str). Everything else in status_cmd — the exists() early return, the Database block, the Watch and Vector-lag probes, the error wrapper — and the whole remainder of main.py stay byte-identical.

  Run ruff format on the two task files only if the format check complains. Do not edit _get_default_db_path or TestDefaultDbPathConfigError (Phase 11's differently-numbered WR-09), src/sif/cli/commands/index.py (the alias needs no change), src/sif/cli/commands/get.py, src/sif/database/schema.py, src/sif/cli/commands/search.py (sibling tip), tests/unit/mcp/test_backend.py (sibling tir), docs/api-reference.md (sibling tis), generator-owned docs, or skills.
  </action>
  <verify>
    <automated>python -m pytest tests/unit/cli/test_status.py tests/unit/cli/test_main.py -q --no-cov &amp;&amp; ruff check src/sif/cli/main.py tests/unit/cli/test_status.py &amp;&amp; ruff format --check src/sif/cli/main.py tests/unit/cli/test_status.py</automated>
  </verify>
  <done>The new test failed on assertions before the production edit (raw ValidationError, empty output) and all 19 tests (18 existing + 1 new) now pass; the fallback is guarded with the exact _get_default_db_path pattern; invalid env config on the fallback path renders a one-line Error naming reranker_model_type with exit 1; _get_default_db_path, its tests, the alias, and all existing tests are byte-identical/unmodified; ruff and formatting pass.</done>
</task>

<task type="auto">
  <name>Task 2: Close only IN-06 in the Phase 10 disposition ledger (execution-time-robust)</name>
  <files>.planning/milestones/v1.0-phases/10-raise-pytest-coverage-to-90/10-REVIEW-DISPOSITION.md</files>
  <action>
  After Task 1 passes, make exactly three scoped updates in .planning/milestones/v1.0-phases/10-raise-pytest-coverage-to-90/10-REVIEW-DISPOSITION.md. SHARED-LEDGER RULE: siblings tip (IN-01/CR-01/CR-02), tir (IN-10), and tis (IN-09) close records in this same file and may run before this item — read the CURRENT `open:` count from execution-time `git show HEAD:<ledger>` and decrement THAT value by 1; never hardcode the planning-time count (13) or any assumed successor as a replacement literal.

  1. In the IN-06 YAML finding block only, change `disposition: open` to `disposition: fixed`; preserve its id, severity (info), and title.
  2. Change the aggregate `open: N` line to `open: N-1` where N is the value read from execution-time HEAD; leave `total: 22` and the original `recorded` timestamp unchanged.
  3. Replace the IN-06 markdown row `| IN-06 | info | open | - |` with `| IN-06 | info | fixed | quick 261111-tiq (status_cmd index_path-None fallback wrapped in the _get_default_db_path ValidationError-to-ClickException guard; invalid-env regression test red-to-green) |`.

  Preserve every other YAML block, markdown row, ordering, explanatory paragraph, and trailing newline byte-for-byte — including any closures siblings already landed. Do not introduce any Status-resolved style lines (that format belongs to other ledger types). Do not edit the historical 10-REVIEW.md, other review ledgers, or STATE.md; the orchestrator owns quick-task state updates. Run the verification gate BEFORE committing the ledger edit; if the gate fails because the working ledger diverges from execution-time HEAD for reasons other than this task's three edits, halt and surface the divergence — never force the edit.
  </action>
  <verify>
    <automated>python -I -c "import re, subprocess; from pathlib import Path; path = '.planning/milestones/v1.0-phases/10-raise-pytest-coverage-to-90/10-REVIEW-DISPOSITION.md'; before = subprocess.check_output(['git', 'show', 'HEAD:' + path], text=True); m = re.search(r'^open: (\d+)$', before, re.M); assert m, 'open count line missing'; n = int(m.group(1)); yaml_anchor = '  - id: IN-06\n    severity: info\n    disposition: open\n'; row = '| IN-06 | info | open | - |'; new_row = '| IN-06 | info | fixed | quick 261111-tiq (status_cmd index_path-None fallback wrapped in the _get_default_db_path ValidationError-to-ClickException guard; invalid-env regression test red-to-green) |'; assert before.count(yaml_anchor) == 1 and before.count(row) == 1 and len(re.findall(r'^open: \d+$', before, re.M)) == 1, 'anchors not unique at execution-time HEAD'; expected = before.replace(yaml_anchor, yaml_anchor.replace('disposition: open', 'disposition: fixed'), 1).replace('\nopen: %d\n' % n, '\nopen: %d\n' % (n - 1), 1).replace(row, new_row, 1); assert expected != before; assert Path(path).read_text(encoding='utf-8') == expected, 'ledger differs from exact three-edit reconstruction of execution-time HEAD'; print('IN-06-fixed; open %d->%d; all-other-ledger-content-byte-identical' % (n, n - 1))"</automated>
  </verify>
  <done>IN-06 is fixed in YAML and the table, the open count is exactly one less than its execution-time value with total still 22, the Source cell names quick 261111-tiq, and the exact baseline reconstruction against execution-time `git show HEAD:<ledger>` proves no other ledger content changed (sibling closures included).</done>
</task>

</tasks>

<verification>
Source coverage audit (quick-batch item selects exactly one finding; no RESEARCH artifact or locked D-XX decisions exist):

| SOURCE | ID | Item | Task | Status |
|--------|----|------|------|--------|
| GOAL | quick-261111-tiq | Close Phase 10 IN-06: guard status_cmd's index_path-None fallback with the _get_default_db_path ValidationError-to-ClickException pattern, non-vacuous RED regression test, three-edit ledger closure | 1-2 | COVERED |
| REQ | PHASE10-IN-06 | Wrap the fallback in the same try/except ValidationError -> click.ClickException as _get_default_db_path (10-REVIEW.md:189-193); regression test proving invalid env config yields a clean ClickException instead of a raw traceback | 1 | COVERED |
| CONTEXT | orchestrator notes | TDD non-vacuous RED against unmodified baseline; lru_cache cache_clear hygiene; shared-ledger execution-time decrement from git HEAD + byte-equality reconstruction gate; no Status-resolved lines; PATH pytest --no-cov targeted; full quality suite incl. ty; generator-owned docs untouched; pre-existing .planning/ churn preserved | 1-2 | COVERED |
| CONTEXT | excluded backlog | IN-01/CR-01/CR-02 (sibling tip), IN-10 (sibling tir), IN-09 (sibling tis), WR-07/08 and all other findings; _get_default_db_path and Phase 11's settings-guard tests (different review, already shipped) | 1-2 | EXCLUDED BY FINDING SCOPE, not silently omitted; boundaries pinned by the diff gate below |

No external API integration or core-assumption generalization is in scope (quick mode: phase-scoped capability detectors have no phase input and are skipped — no COVERAGE.md or threat_model block per the batch coordinator). No schema file is touched, so no schema-push task applies.

Final gates, run from the checkout root after both tasks:
1. `python -m pytest tests/unit/cli/test_status.py tests/unit/cli/test_main.py -q --no-cov`
2. `ruff check src tests`
3. `ruff format --check src tests`
4. `ty check src/sif`
5. `python -m pytest` (full run includes the coverage gate; PATH pytest, not .venv; baseline 1528 passed + 1 new test)
6. `git diff --exit-code -- src/sif/cli/commands/get.py src/sif/database/schema.py src/sif/cli/commands/search.py tests/unit/mcp/test_backend.py docs/api-reference.md docs/cli-reference.md docs/configuration.md` proves sibling findings' files and generator-owned docs stayed untouched.
7. Review the scoped diff: only the three files_modified paths carry task edits; within main.py the delta is confined to the status_cmd fallback branch (try/except wrap plus one comment line); _get_default_db_path is byte-identical. Commits touch only task-scoped paths and never stage the pre-existing `.planning/` churn. Planning SUMMARY/STATE artifacts are handled separately by the orchestrator.
</verification>

<success_criteria>
- The regression test is demonstrably red before the production edit (raw pydantic ValidationError escapes, output empty) and green afterward (exit 1, one-line Error naming reranker_model_type, no traceback, exception not a ValidationError); all 18 existing tests in the two CLI test files pass throughout.
- The only production change is the try/except ValidationError -> click.ClickException(str(e)) from e wrap around the existing fallback assignment in status_cmd, matching _get_default_db_path exactly; the Path type contract, the alias delegation, and every other command remain byte-identical.
- IN-06 alone becomes fixed, the ledger open count decrements by exactly 1 from its execution-time value, and exact reconstruction against execution-time HEAD proves every other review record (including sibling closures) unchanged.
- Full ruff, format, ty, and pytest quality suite passes (plain PATH python -m pytest; the suite is color-env-hermetic).
</success_criteria>

<output>
Create `.planning/quick/261111-tiq-close-phase-10-in-06-wrap-status-cmd-s-index-path-none-fallb/261111-tiq-SUMMARY.md` with `status: complete` in SUMMARY frontmatter when done. Record the closed finding as Phase 10 IN-06, the live reproduction evidence (raw ValidationError with empty output at HEAD 3a4b47b vs the guarded one-line Error), the click 8.3.2 CliRunner exception-shape decision (SystemExit after ClickException rendering — output-based assertions plus the not-ValidationError pin), the lru_cache hygiene, the explicit _get_default_db_path/Phase-11-WR-09/sibling boundaries, the red-to-green regression evidence, and the execution-time ledger open-count transition. Do not commit planning artifacts or STATE.md; the orchestrator handles the docs/state commit.
</output>
