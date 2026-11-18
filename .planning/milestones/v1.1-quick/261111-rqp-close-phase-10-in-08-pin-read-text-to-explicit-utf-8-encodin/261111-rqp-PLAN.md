---
phase: quick-261111-rqp
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - src/sif/cli/commands/get.py
  - tests/unit/cli/test_get.py
  - .planning/milestones/v1.0-phases/10-raise-pytest-coverage-to-90/10-REVIEW-DISPOSITION.md
autonomous: true
requirements:
  - PHASE10-IN-08
estimate:
  tokens: 12000
  raw_tokens: 12000
  tasks: 2
  confidence: low
must_haves:
  truths:
    - "get_cmd's unindexed-file disk fallback reads with an explicit encoding='utf-8' keyword, so a UTF-8 note with non-ASCII characters decodes identically on every host locale instead of the locale default (cp1252 on Windows)"
    - "The new read_text-contract regression test is red against the unmodified baseline (the recorded fallback read carries no encoding kwarg) and green after the one-line fix; all 31 existing test_get.py tests pass unmodified"
    - "Everything else in get.py stays byte-identical: the ClickException read-error wrapper, the CR-02 line-filter/numbering contract, the CR-01 markup escaping, and the indexed-document path"
    - "Phase 10 IN-08 is recorded as fixed in both ledger representations, the open count is exactly one less than the execution-time HEAD value with total still 22, and every other finding record remains byte-identical"
  artifacts:
    - src/sif/cli/commands/get.py
    - tests/unit/cli/test_get.py
    - .planning/milestones/v1.0-phases/10-raise-pytest-coverage-to-90/10-REVIEW-DISPOSITION.md
  key_links:
    - "get_cmd disk fallback (get.py:85) -> path.read_text(encoding='utf-8') -> non-ASCII UTF-8 notes decode correctly regardless of host locale"
    - "delegating Path.read_text spy in the new contract test -> records the fallback read kwargs -> asserts encoding='utf-8' (locale-independent RED/GREEN, immune to UTF-8 mode)"
    - "IN-08 YAML disposition + IN-08 markdown row + execution-time open-count decrement -> one consistent review ledger with no unrelated edits"
---

<objective>
Close Phase 10 IN-08 only. The finding ("Disk-fallback read_text() without explicit encoding", 10-REVIEW.md:201-205) names exactly one site: the unindexed-file fallback in `get_cmd`, recorded as `src/sif/cli/commands/get.py:84` and now at line 85 (the file evolved — line 84 is the `try:`; line 85 is `content = path.read_text()`). Grep confirms this is the ONLY read_text/read_bytes/open site in get.py and the only unencoded `read_text()` in src/sif/cli/. The finding's fix is exactly `content = path.read_text(encoding="utf-8")`. This plan adds that keyword, pins it with a locale-independent read_text-contract regression test (the WR-06 exemplar's open-kwarg spy adapted to Path.read_text), and closes IN-08 in the disposition ledger with the three-edit convention.

Scope is ONLY the site the finding names. Sibling batch items own their own findings: WR-09 (main.py/repositories.py, item rqq), WR-01 (collection.py/index.py/repositories.py, item rqs), and the caplog leak (test_watch_cmd.py, item rqr) are NOT swept here. All other IN/CR/WR records stay untouched.

Purpose: make the disk fallback explicitly UTF-8 on every host locale, completing IN-08 without changing any other behavior.
Output: a one-line encoding fix in get.py, one read_text-contract regression test in test_get.py, and IN-08 marked fixed without disturbing any other review item.
</objective>

<execution_context>
@~/.claude/gsd-core/workflows/execute-plan.md
@~/.claude/gsd-core/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md
@.planning/milestones/v1.0-phases/10-raise-pytest-coverage-to-90/10-REVIEW.md
@.planning/milestones/v1.0-phases/10-raise-pytest-coverage-to-90/10-REVIEW-DISPOSITION.md
@src/sif/cli/commands/get.py
@tests/unit/cli/test_get.py

Planning evidence (all grounded live at planning-time HEAD 802c08c):
- `src/sif/cli/commands/get.py` (252 lines): line 85 `content = path.read_text()` inside the disk-fallback try at 84-108 (`except Exception` -> `click.ClickException(f"Cannot read file: {e}")`). Grep for read_text/read_bytes/open( confirms line 85 is the file's ONLY file-read site. The fallback already honors the CR-02 line-filter/numbering contract (89-98) and CR-01 markup escaping (99-105) — do NOT restructure any of it; this task ships only the encoding keyword.
- `tests/unit/cli/test_get.py` (861 lines, 31 tests at baseline: `python -m pytest tests/unit/cli/test_get.py -q --no-cov` -> 31 passed in 0.92s). `TestGetRetrieval(RealDatabaseTestCase)` uses a REAL tmp_path SQLite index via the `indexed_documents` fixture and `_invoke(db_path, "get", argument, *options)`, which invokes the top-level `cli` with `["--index", str(db_path), "get", "get", argument, *options]` and `env={"COLUMNS": "200"}` — note the doubled `get` (group + subcommand). The disk-fallback tests are `test_local_file_fallback_and_read_failure` (line 205) and `test_disk_fallback_honors_line_options` (line 222); the new test goes immediately after the latter. `patch.object(Path, "read_text", ...)` is an established idiom in this file (line 214). All needed imports already exist (`os` line 3, `Path` line 5, `patch` line 7) — NO import changes.
- RED design (decided, prototyped): on this macOS host the preferred locale encoding is already UTF-8, so a functional non-ASCII test would pass at baseline and prove nothing. Instead the contract test spies on Path.read_text with a delegating recorder and asserts the encoding kwarg on the fallback read. The exact harness was prototyped against the UNMODIFIED get.py at HEAD 802c08c: exit_code 0, exactly one fallback read recorded with kwargs {}, non-ASCII content rendered — the encoding assertion fails at baseline on any platform, locale, or UTF-8 mode. (Locale simulation via monkeypatching locale.getpreferredencoding was rejected in the WR-06 exemplar: PYTHONUTF8/UTF-8 mode bypasses it.)
- Ledger closure convention (verified against the live ledger and prior closure commits 15343bb/1ac9f24/de0b729): exactly three scoped edits — YAML `disposition: open` -> `fixed` in the IN-08 block, aggregate open-count decrement, and the IN-08 markdown row replacement with a Source cell naming quick 261111-rqp. This ledger does NOT use `**Status:** resolved` lines; do not introduce one. Keep every other record byte-identical.
- SHARED-LEDGER RULE (batch 261111-rqo): sibling items rqq (WR-09) and rqs (WR-01) close records in the SAME ledger, and the scheduler serializes the overlap via files_modified. At planning time the ledger reads `open: 16` / `total: 22`, but by execution time siblings may have landed first. The open-count edit MUST read the CURRENT count from execution-time `git show HEAD:<ledger>` and decrement by 1 — never hardcode 16->15 as a replacement literal. The Task 2 gate reconstructs the expected file from execution-time HEAD plus the three replacements (count computed dynamically) and asserts byte-equality.
- Planning-time ledger grounding: byte-clean against HEAD; the IN-08 YAML literal and the IN-08 row literal each occur exactly once; the `\nopen: (\d+)\n` regex matches exactly once.
- Test environment: PATH python/pytest (miniconda base, Python 3.13.9), NOT .venv (no torch). Targeted runs need `--no-cov` (addopts carry --cov with fail_under=90); the full-suite gate runs WITH coverage. The suite is color-env-hermetic (conftest scrub, commit 6522663) — plain `python -m pytest` works.
- Discovery level 0: a one-keyword correction at an existing call site plus a contract test in the file's established real-database harness; no new dependency, external integration, research, or ORM schema change.
- Scope guard: sibling-owned files (src/sif/cli/main.py, src/sif/database/repositories.py, src/sif/cli/commands/collection.py, src/sif/cli/commands/index.py, tests/unit/cli/test_watch_cmd.py), generator-owned docs (docs/cli-reference.md, docs/configuration.md — never hand-edit), and every other finding stay untouched. The working tree carries pre-existing uncommitted `.planning/` churn (config.json, state.json, agent-history.json, PATTERNS files, research cache, 16-REVIEW iter2 files, tmp/) that predates this task — never stage, commit, or revert any of it; commits touch only task-scoped paths.
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Pin and fix the IN-08 disk-fallback UTF-8 encoding</name>
  <files>src/sif/cli/commands/get.py, tests/unit/cli/test_get.py</files>
  <behavior>
    - The fallback read performed by get_cmd carries encoding="utf-8" in its kwargs: a delegating Path.read_text spy records exactly one read of the local file path during a disk-fallback run, and the recorded kwargs include encoding == "utf-8" (baseline records kwargs {} — the assertion is red before the fix on any platform/locale).
    - The run itself succeeds through the spy: exit_code == 0 and the non-ASCII file content appears in the output (the spy observes and delegates; it never alters behavior).
    - Non-vacuity: exactly one fallback read is recorded; zero recorded calls fails the test rather than passing it.
    - Preservation: all 31 existing test_get.py tests pass unmodified before and after the production edit (on this UTF-8-locale host the keyword matches the previous default, so no observable behavior changes); the read-error ClickException path ("Cannot read file"), the CR-02 line-option contract, and the indexed path are untouched.
  </behavior>
  <action>
  First change tests/unit/cli/test_get.py only. In `TestGetRetrieval`, immediately after `test_disk_fallback_honors_line_options`, add one test `test_disk_fallback_read_text_pins_utf8_encoding(self, indexed_documents: tuple[Path, list[Document]], tmp_path: Path) -> None` with a docstring stating it pins IN-08 via a locale-independent read_text contract (a functional non-ASCII test would be vacuous on UTF-8 locales). No new imports — os, Path, and patch are already imported. Body: unpack `db_path, _ = indexed_documents`; create `local_file = tmp_path / "local.md"` and write non-ASCII content (e.g. "café 中文 😀" plus a second line) via write_text with encoding="utf-8". Capture `real_read_text = Path.read_text` and create `recorded: list[dict] = []`. Define `spy_read_text(self: Path, *args: object, **kwargs: object) -> str` that appends `dict(kwargs)` to recorded when `os.fspath(self) == str(local_file)`, then unconditionally returns `real_read_text(self, *args, **kwargs)` — every call is delegated, only the fallback read of the local file is recorded. Invoke inside `with patch.object(Path, "read_text", spy_read_text):` using `self._invoke(db_path, "get", str(local_file))` (the helper already builds the correct `--index ... get get <path>` argv). Assert result.exit_code == 0, the non-ASCII content string is in result.output, len(recorded) == 1, and recorded[0].get("encoding") == "utf-8". Do not modify any existing test, helper, or fixture. Before any production edit, run the new test alone (`python -m pytest tests/unit/cli/test_get.py -q --no-cov -k test_disk_fallback_read_text_pins_utf8_encoding`) and confirm it fails on the encoding assertion while the exit-code, content, and count assertions pass (planning-time prototype: exit 0, one read recorded with empty kwargs, content rendered); confirm the other 31 tests still pass at baseline.

  Then make the one-line production change in src/sif/cli/commands/get.py: at line 85 add the encoding keyword so the fallback read passes encoding="utf-8" to read_text (the statement becomes content = path.read_text(encoding="utf-8")). Change nothing else: the surrounding try/except -> ClickException wrapper (84-108), the CR-02 line-filter comment and logic (86-98), the CR-01 escape/raw-print comments and calls (99-105), and every other line stay byte-identical. No new imports in get.py. Do not sweep any other file or site: WR-09 (main.py, repositories.py — sibling item rqq), WR-01 (collection.py, index.py, repositories.py — sibling item rqs), the caplog leak (test_watch_cmd.py — sibling item rqr), generator-owned docs, and all other findings stay untouched. If the formatting check complains, run ruff format on the two task files only.
  </action>
  <verify>
    <automated>python -m pytest tests/unit/cli/test_get.py -q --no-cov &amp;&amp; ruff check src/sif/cli/commands/get.py tests/unit/cli/test_get.py &amp;&amp; ruff format --check src/sif/cli/commands/get.py tests/unit/cli/test_get.py</automated>
  </verify>
  <done>The new contract test failed on the encoding assertion before the production edit (exit-code, content, and single-read assertions passing at baseline) and the full test_get.py file (32 tests) now passes; the only production delta is the encoding keyword on the fallback read at get.py:85; the error wrapper, line-filter contract, markup escaping, and all other code remain byte-identical; ruff and formatting pass on both task files.</done>
</task>

<task type="auto">
  <name>Task 2: Close only IN-08 in the Phase 10 disposition ledger</name>
  <files>.planning/milestones/v1.0-phases/10-raise-pytest-coverage-to-90/10-REVIEW-DISPOSITION.md</files>
  <action>
  In .planning/milestones/v1.0-phases/10-raise-pytest-coverage-to-90/10-REVIEW-DISPOSITION.md, make exactly three scoped updates after Task 1 passes:

  1. In the IN-08 YAML finding block only, change `disposition: open` to `disposition: fixed`; preserve its id, severity (info), and title.
  2. Decrement the aggregate `open:` count by exactly 1 from its CURRENT execution-time value. Read the current count from `git show HEAD:<ledger>` at execution time — sibling items rqq/rqs may already have decremented it (planning-time value was 16, but do NOT hardcode any number as a replacement literal). Leave `total: 22` and the original `recorded` timestamp unchanged.
  3. Replace the IN-08 markdown row with `| IN-08 | info | fixed | quick 261111-rqp (disk-fallback read_text pinned to explicit UTF-8 encoding plus read_text-contract regression test) |`.

  Preserve every other YAML block, markdown row, ordering, explanatory paragraph, and trailing newline byte-for-byte. WR-01 and WR-09 may legitimately already be fixed by sibling items at execution time — do not assert their state and do not touch their records; every other finding (including all remaining IN/CR rows) is preserved exactly as found. Do not introduce any `**Status:**` line (that format belongs to other ledger types), do not edit the historical 10-REVIEW.md, other review ledgers, or STATE.md; the orchestrator owns quick-task state updates.

  Run the verification gate before committing the ledger edit; commit only this ledger path (never the pre-existing .planning/ churn).
  </action>
  <verify>
    <automated>python -I -c "from pathlib import Path; import re, subprocess; path = '.planning/milestones/v1.0-phases/10-raise-pytest-coverage-to-90/10-REVIEW-DISPOSITION.md'; before = subprocess.check_output(['git', 'show', 'HEAD:' + path], text=True); yaml_old = '  - id: IN-08\n    severity: info\n    disposition: open\n'; yaml_new = '  - id: IN-08\n    severity: info\n    disposition: fixed\n'; row_old = '| IN-08 | info | open | - |'; row_new = '| IN-08 | info | fixed | quick 261111-rqp (disk-fallback read_text pinned to explicit UTF-8 encoding plus read_text-contract regression test) |'; assert before.count(yaml_old) == 1; assert before.count(row_old) == 1; counts = re.findall(r'\nopen: (\d+)\n', before); assert len(counts) == 1; expected = before.replace(yaml_old, yaml_new, 1).replace(row_old, row_new, 1); expected = re.sub(r'\nopen: \d+\n', '\nopen: %d\n' % (int(counts[0]) - 1), expected, count=1); assert expected != before; assert Path(path).read_text(encoding='utf-8') == expected; assert '\ntotal: 22\n' in expected; assert all(row in expected for row in ('| WR-07 | warning | open | - |', '| WR-08 | warning | open | - |', '| IN-09 | info | open | - |', '| IN-10 | info | open | - |', '| CR-01 | critical | open |', '| CR-02 | critical | open |')); print('IN-08-fixed; open-count-decremented-from-execution-time-HEAD; all-other-ledger-content-unchanged')"</automated>
  </verify>
  <done>IN-08 is fixed in YAML and the table, the open count is exactly one less than the execution-time HEAD value with total still 22, the Source cell names quick 261111-rqp, and an exact execution-time baseline reconstruction proves no other ledger content changed.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| User-supplied unindexed file -> get_cmd disk fallback (Path.read_text) | A user-provided file crosses into CLI output; without an explicit encoding the bytes decode with the host locale default, so a UTF-8 note with non-ASCII characters can mis-decode (mojibake printed as the document) or raise UnicodeDecodeError on non-UTF-8 locale hosts (cp1252 on Windows) |

No new network, package, authentication, or external-service boundary is introduced.

## STRIDE Threat Register

| Threat ID | Category | Component | Severity | Disposition | Mitigation Plan |
|-----------|----------|-----------|----------|-------------|-----------------|
| T-rqp-01 | Tampering | src/sif/cli/commands/get.py get_cmd disk fallback (line 85) | low | mitigate | Pin the fallback read to encoding="utf-8" so user-supplied UTF-8 notes decode identically on every host locale; pin the contract with a locale-independent Path.read_text spy regression test that is red at baseline |
| T-rqp-SC | Tampering | package installs | low | accept | No package-manager install, dependency, or lockfile task exists; the package legitimacy gate is not applicable |
</threat_model>

<verification>
Source coverage audit (the quick constraint selects exactly one finding; no RESEARCH artifact or locked D-XX decisions exist):

| SOURCE | ID | Item | Task | Status |
|--------|----|------|------|--------|
| GOAL | quick-261111-rqp | Close Phase 10 IN-08 at the site the finding names: contract test red-to-green + three-edit ledger closure | 1-2 | COVERED |
| REQ | PHASE10-IN-08 | Explicit UTF-8 encoding on the disk-fallback read_text (get.py:85, the finding's sole site), contract regression test, disposition update | 1-2 | COVERED |
| CONTEXT | orchestrator notes | Shared-ledger execution-time-robust count decrement; three-edit closure convention with Source cell naming quick 261111-rqp; no Status lines; scope only the named site; PATH pytest --no-cov targeted, full quality suite at end; preserve working-tree churn; never hand-edit generator docs | 1-2 | COVERED |
| CONTEXT | sibling items | WR-09 (rqq), WR-01 (rqs), caplog leak (rqr), all other IN/CR/WR findings | - | EXCLUDED BY BATCH SCOPE, not silently omitted; ledger preservation is verified by byte-equality reconstruction |

No external API integration or core-assumption generalization is in scope (quick mode: phase-scoped detectors have no phase input and are skipped). No Payload/Prisma/Drizzle/Supabase/TypeORM schema file is touched, so no schema-push task applies.

Final gates, run from the checkout root after both tasks:
1. `python -m pytest tests/unit/cli/test_get.py -q --no-cov`
2. `ruff check src tests`
3. `ruff format --check src tests`
4. `python -m pytest` (full run includes the coverage gate; PATH pytest, not .venv)
5. `git diff --exit-code -- src/sif/cli/main.py src/sif/database/repositories.py src/sif/cli/commands/collection.py src/sif/cli/commands/index.py tests/unit/cli/test_watch_cmd.py docs/cli-reference.md docs/configuration.md` proves sibling-owned files and generator-owned docs stayed untouched.
6. Review the scoped diff: only `src/sif/cli/commands/get.py` (one line), `tests/unit/cli/test_get.py` (one new test, no import changes), and the Phase 10 disposition ledger (three edits) carry task changes; commits touch only those task-scoped paths and never stage the pre-existing `.planning/` churn. Planning SUMMARY/STATE artifacts are handled separately by the orchestrator.
</verification>

<success_criteria>
- The new read_text-contract test is demonstrably red before the production edit (fallback read recorded with no encoding kwarg; exit-code, content, and single-read assertions passing) and green afterward, with all 31 existing tests passing throughout.
- The only production change is the encoding keyword on the fallback read at get.py:85; the ClickException wrapper, the CR-02 line-filter contract, the CR-01 escaping, and every other line remain byte-identical.
- IN-08 alone becomes fixed, the ledger open count is exactly one less than its execution-time HEAD value, and exact baseline reconstruction proves every other review record remains unchanged.
- Full ruff, format, and pytest quality suite passes (plain PATH python -m pytest; the suite is color-env-hermetic).
</success_criteria>

<output>
Create `.planning/quick/261111-rqp-close-phase-10-in-08-pin-read-text-to-explicit-utf-8-encodin/261111-rqp-SUMMARY.md` with `status: complete` in SUMMARY frontmatter when done. Record the closed finding as Phase 10 IN-08 (disk-fallback read_text encoding, get.py:85 — the finding's sole named site), the planning-time and executor RED-to-GREEN evidence (spy recorded kwargs {} at baseline, encoding="utf-8" after the fix), and the ledger open-count decrement observed at execution time (from the execution-time HEAD value, whatever siblings landed first). Do not commit planning artifacts or STATE.md; the orchestrator handles the docs/state commit.
</output>
