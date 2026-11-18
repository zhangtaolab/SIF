---
phase: quick-261111-tis
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - docs/api-reference.md
  - .planning/milestones/v1.0-phases/10-raise-pytest-coverage-to-90/10-REVIEW-DISPOSITION.md
autonomous: true
requirements:
  - PHASE10-IN-09
estimate:
  tokens: 10000
  raw_tokens: 10000
  tasks: 2
  confidence: low
must_haves:
  truths:
    - "The Complete Search Example in docs/api-reference.md opens the user's index through an expanded path: db_path = Path(\"~/.local/share/sif/sif.db\").expanduser() and sqlite3.connect(str(db_path)), so the example opens the intended database instead of failing on a literal tilde"
    - "The identical raw-tilde database arguments in the DatabaseConnection and SearchBackend usage examples are fixed with the same expanduser pattern; no DB-opening call in api-reference.md receives a raw tilde argument any more"
    - "All 65 python blocks in api-reference.md still compile, a sandboxed demonstration runs the doc's verbatim db_path expression under a throwaway HOME and opens the seeded intended DB with no literal ~ directory created, and every other line of the doc is byte-identical"
    - "Phase 10 IN-09 is recorded as fixed in both ledger representations, the open count is exactly one less than the execution-time HEAD value with total still 22, and every other finding record remains byte-identical"
  artifacts:
    - docs/api-reference.md
    - .planning/milestones/v1.0-phases/10-raise-pytest-coverage-to-90/10-REVIEW-DISPOSITION.md
  key_links:
    - "Complete Search Example db_path expression -> Path.expanduser -> sqlite3.connect(str(db_path)) -> the reader's real index opens instead of 'unable to open database file'"
    - "DatabaseConnection / SearchBackend usage examples -> expanded Path argument -> no literal ~ directory tree created in the reader's cwd (DatabaseConnection.__init__ mkdirs the argument's parent)"
    - "IN-09 YAML disposition + IN-09 markdown row + execution-time open-count decrement -> one consistent review ledger with no unrelated edits"
---

<objective>
Close Phase 10 IN-09 only. The finding ("api-reference example uses sqlite3.connect with a raw tilde — tilde is not expanded", 10-REVIEW.md:207-211) names the Complete Search Example, recorded as docs/api-reference.md:739 and now at line 818 (the file evolved). sqlite3 does not expand `~`; the example fails with "unable to open database file". Live verification at planning-time HEAD 3a4b47b found the SAME one-line defect repeating trivially at two more sites in the same hand-owned file: the DatabaseConnection usage example (line 650) and the MCPServer/SearchBackend usage example (line 790) — neither class expands `~` either, and DatabaseConnection.__init__ even mkdirs the literal tilde parent in the reader's cwd. Per the item's scope rule ("unless the same one-line pattern repeats trivially") and the coordinator's guidance, all three sites get the identical pathlib expanduser fix; the finding's named site is the anchor. Then close IN-09 in the disposition ledger with the three-edit convention.

This is a DOC-ONLY change: no src/ or tests/ edits. api-reference.md is hand-owned (zero generator references in Makefile, scripts/, or tests/test_docs.py — verified live); docs/cli-reference.md and docs/configuration.md are generator-owned under a CI diff gate and are NEVER touched. api-reference.md is deliberately outside tests/test_docs.py's DOCS_FILES validated set; adding it there is scope creep and is NOT done.

Purpose: make the documented database examples actually open the user's index on every platform, completing IN-09 without changing any code or any other doc content.
Output: three corrected example blocks in docs/api-reference.md and IN-09 marked fixed without disturbing any other review item.
</objective>

<execution_context>
@~/.claude/gsd-core/workflows/execute-plan.md
@~/.claude/gsd-core/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md
@.planning/milestones/v1.0-phases/10-raise-pytest-coverage-to-90/10-REVIEW.md
@.planning/milestones/v1.0-phases/10-raise-pytest-coverage-to-90/10-REVIEW-DISPOSITION.md
@docs/api-reference.md

Planning evidence (all grounded live at planning-time HEAD 3a4b47b):
- IN-09 finding text: 10-REVIEW.md:207-211. Fix prescribed by the finding: pathlib Path expanduser, then connect to str(db_path). The cited line 739 drifted; the live Complete Search Example block is docs/api-reference.md:802-831 with the raw-tilde connect at line 818.
- The identical raw-tilde DB-path literal repeats at exactly two more sites (grep-verified, one occurrence each): line 650 in the DatabaseConnection **Usage:** block (647-655) and line 790 in the MCPServer **Usage:** block (784-794). Source-verified defect: DatabaseConnection.__init__ (src/sif/database/connection.py:19-22) does Path(db_path) + parent.mkdir(parents=True, exist_ok=True) with NO expanduser — a raw tilde argument creates a literal `~/.local/share/sif` directory tree in cwd; SearchBackend.__init__ (src/sif/mcp/backend.py:86-88) stores the raw string and _run_in_db (backend.py:113) forwards it to DatabaseConnection. Constructor types decide the wrapper: DatabaseConnection takes Path | str (pass the expanded Path directly); SearchBackend takes db_path: str (wrap in str()).
- The collection-registration path literals elsewhere in the file (the `~/Documents/...` arguments at lines 40, 41, 49, 89, 144, 152, 845, 860) are a DIFFERENT API surface — collection paths stored as given, not DB-open calls — and are not the defect IN-09 names. Leave them untouched; record them as checked-and-left in the SUMMARY.
- None of the three target blocks imports pathlib today (file-wide count of the pathlib Path import is 0 at baseline; after the fix it must be exactly 3). The file has 65 fenced python blocks; ALL compile at baseline (the defect is runtime, not syntax) — the fix must keep all 65 compiling.
- Sandboxed prototype (planning-time, throwaway HOME with a seeded marker DB): the OLD raw-tilde connect exits rc=1 ("unable to open database file" — sqlite3 does not create parent directories); the NEW expanduser form exits rc=0, opens the intended sandbox DB, and creates no literal `~` directory. The Task 1 gate re-runs this demonstration against the doc's verbatim db_path line.
- Static gate baseline (non-vacuous): each of the three raw-tilde call patterns occurs exactly once at HEAD (3 total) and each of the four fixed-form literals occurs 0 times — the gate FAILS before the fix and can only pass after all three sites are corrected.
- api-reference.md ownership: no references in Makefile, scripts/, or tests/test_docs.py (grep-verified) — hand-owned, safe to edit. tests/test_docs.py DOCS_FILES (lines 21-31) lists index/cli-reference/configuration/quickstart/mcp-server/search-algorithms/benchmarking/architecture/models — api-reference.md is NOT in the set; do NOT add it.
- Ledger closure convention (verified against the live ledger and prior closure commits 7be1412/8f16b1e/a43007a): exactly three scoped edits — YAML `disposition: open` -> `fixed` in the IN-09 block, aggregate open-count decrement, and the IN-09 markdown row replacement with a Source cell naming quick 261111-tis. This ledger does NOT use `**Status:** resolved` lines; do not introduce one. Keep every other record byte-identical.
- SHARED-LEDGER RULE (batch 261111-tio): sibling items tip (closes IN-01/CR-01/CR-02), tiq (IN-06), and tir (IN-10) close records in the SAME ledger, and the scheduler serializes the overlap via files_modified. At planning time the ledger reads `open: 13` / `total: 22`, but by execution time siblings may have landed first. The open-count edit MUST read the CURRENT count from execution-time `git show HEAD:<ledger>` and decrement by 1 — never hardcode 13->12 as a replacement literal. The Task 2 gate reconstructs the expected file from execution-time HEAD plus the three replacements (count computed dynamically) and asserts byte-equality.
- Planning-time ledger grounding: working tree byte-clean against HEAD; the IN-09 YAML literal and the IN-09 row literal each occur exactly once; the `\nopen: (\d+)\n` regex matches exactly once; reconstruction dry-run passed.
- Test environment: PATH python/pytest (miniconda base), NOT .venv (no torch). Targeted runs need `--no-cov`; the full-suite gate runs WITH coverage (fail_under=90). Baseline: 1528 passed. The suite is color-env-hermetic (commit 6522663) — plain `python -m pytest` works. Doc-only change: the suite must stay green unchanged.
- Discovery level 0: a documentation correction at three existing example sites using the stdlib pathlib pattern the finding prescribes; no new dependency, external integration, or research.
- Scope guard: no src/ or tests/ file is touched; generator-owned docs (docs/cli-reference.md, docs/configuration.md) are never hand-edited; every other finding stays untouched. The working tree carries pre-existing uncommitted `.planning/` churn (config.json, state.json, agent-history.json, PATTERNS files, research cache, 16-REVIEW iter2 files, tmp/) that predates this task — never stage, commit, or revert any of it; commits touch only task-scoped paths.
</context>

<tasks>

<task type="auto">
  <name>Task 1: Expand the tilde in the three api-reference database examples</name>
  <files>docs/api-reference.md</files>
  <action>
  Edit docs/api-reference.md only. Three example blocks pass the raw tilde database path string directly to a DB-opening call, and neither sqlite3 nor the sif connection classes expand it (DatabaseConnection.__init__ at src/sif/database/connection.py:19-22 wraps the argument in Path() and mkdirs its parent — a raw tilde argument creates a literal tilde directory tree in the reader's cwd; SearchBackend stores the string and forwards it to DatabaseConnection at backend.py:113). Fix all three sites with the same pathlib expanduser pattern:

  1. Complete Search Example — the site IN-09 names (block at lines 802-831, connect statement at line 818). Add `from pathlib import Path` to the block's stdlib imports, after `import sqlite3` and before the sif imports (stdlib-first, matching the file's style). Immediately before the with statement insert `db_path = Path("~/.local/share/sif/sif.db").expanduser()` and change the with statement to `with sqlite3.connect(str(db_path)) as db:`. Everything inside the with body — the HybridSearcher construction comment and call, SearchOptions, the search call, and the result display loop — stays byte-identical.

  2. DatabaseConnection usage example (block at lines 647-655, construction at line 650). Add `from pathlib import Path` as the block's first import with a blank line before the sif import, and pass the expanded Path directly: `conn = DatabaseConnection(Path("~/.local/share/sif/sif.db").expanduser())`. The constructor is typed Path | str (connection.py:19), so no str() wrapper is needed here. The connect() usage and the query below stay byte-identical.

  3. MCPServer/SearchBackend usage example (block at lines 784-794, construction at line 790). Add `from pathlib import Path` as the block's first import with a blank line before the sif imports, and wrap the expanded path in str() because SearchBackend.__init__ is typed db_path: str (backend.py:86): `server = MCPServer(SearchBackend(str(Path("~/.local/share/sif/sif.db").expanduser())))`. The register_tools and transport lines stay byte-identical.

  Scope discipline: these three blocks are the ONLY edits. The collection-registration path literals elsewhere in the file (the ~/Documents/... arguments at lines 40, 41, 49, 89, 144, 152, 845, 860) are a different API surface — collection paths stored as given, not DB-open calls — and are not part of IN-09; leave them untouched and record them as checked-and-left in the SUMMARY. Do not touch any other line of api-reference.md, any other doc (docs/cli-reference.md and docs/configuration.md are generator-owned under a CI diff gate — never hand-edit), tests/test_docs.py (api-reference.md is deliberately outside its DOCS_FILES validated set; adding it is scope creep), or any src/ or tests/ file. The verify gate's block-count and compile assertions catch any accidental fence or structure damage.
  </action>
  <verify>
    <automated>python -I -c 'import re; from pathlib import Path; doc = Path("docs/api-reference.md").read_text(encoding="utf-8"); fence = chr(96) * 3; blocks = re.findall(fence + "python\n(.*?)" + fence, doc, re.DOTALL); assert len(blocks) == 65, len(blocks); [compile(b, "<block>", "exec") for b in blocks]; neg = ["connect(\"~", "DatabaseConnection(\"~", "SearchBackend(\"~"]; hits = {p: doc.count(p) for p in neg}; assert sum(hits.values()) == 0, hits; pos = ["db_path = Path(\"~/.local/share/sif/sif.db\").expanduser()", "with sqlite3.connect(str(db_path)) as db:", "DatabaseConnection(Path(\"~/.local/share/sif/sif.db\").expanduser())", "SearchBackend(str(Path(\"~/.local/share/sif/sif.db\").expanduser()))"]; counts = {p: doc.count(p) for p in pos}; assert all(v == 1 for v in counts.values()), counts; assert doc.count("from pathlib import Path") == 3, doc.count("from pathlib import Path"); print("doc-gate-pass:", len(blocks), "python blocks compile; 3 expanduser sites present; no raw-tilde DB arguments")' &amp;&amp; python -I -c 'import os, re, shutil, sqlite3, subprocess, sys, tempfile; from pathlib import Path; doc = Path("docs/api-reference.md").read_text(encoding="utf-8"); fence = chr(96) * 3; blocks = re.findall(fence + "python\n(.*?)" + fence, doc, re.DOTALL); block = next(b for b in blocks if "with sqlite3.connect(str(db_path)) as db:" in b); db_line = next(l for l in block.splitlines() if l.startswith("db_path = ")); home = Path(tempfile.mkdtemp()); intended = home / ".local/share/sif/sif.db"; intended.parent.mkdir(parents=True); con = sqlite3.connect(str(intended)); con.execute("CREATE TABLE marker (x INTEGER)"); con.execute("INSERT INTO marker VALUES (42)"); con.commit(); con.close(); work = home / "work"; work.mkdir(); env = dict(os.environ, HOME=str(home)); code = "from pathlib import Path\n" + db_line + "\nimport sqlite3\nwith sqlite3.connect(str(db_path)) as db:\n    row = db.execute(\"SELECT x FROM marker\").fetchone()\n    assert row[0] == 42, row\n    assert db_path == Path.home() / \".local/share/sif/sif.db\", db_path\nprint(\"sandbox-ok\", db_path)\n"; r = subprocess.run([sys.executable, "-I", "-c", code], cwd=str(work), env=env, capture_output=True, text=True); assert r.returncode == 0, r.stderr; assert "sandbox-ok" in r.stdout, r.stdout; assert not (work / "~").exists(), "literal tilde directory created"; shutil.rmtree(home); print("sandbox-demo-pass: doc db_path expression opens the intended DB under a throwaway HOME; no literal tilde directory")'
    </automated>
  </verify>
  <done>All three example blocks resolve the database path through Path.expanduser before opening it; the static gate proves all 65 python blocks compile, each of the four fixed-form literals appears exactly once, the pathlib import appears exactly 3 times, and no DB-opening call receives a raw tilde argument (this gate fails at the unmodified baseline — 3 raw-tilde hits, 0 fixed forms); the sandboxed demonstration runs the doc's verbatim db_path expression under a throwaway HOME, opens the seeded intended DB, and creates no literal tilde directory; every other line of api-reference.md is byte-identical.</done>
</task>

<task type="auto">
  <name>Task 2: Close only IN-09 in the Phase 10 disposition ledger</name>
  <files>.planning/milestones/v1.0-phases/10-raise-pytest-coverage-to-90/10-REVIEW-DISPOSITION.md</files>
  <action>
  In .planning/milestones/v1.0-phases/10-raise-pytest-coverage-to-90/10-REVIEW-DISPOSITION.md, make exactly three scoped updates after Task 1 passes:

  1. In the IN-09 YAML finding block only, change `disposition: open` to `disposition: fixed`; preserve its id, severity (info), and title.
  2. Decrement the aggregate `open:` count by exactly 1 from its CURRENT execution-time value. Read the current count from `git show HEAD:<ledger>` at execution time — sibling items tip/tiq/tir may already have decremented it (planning-time value was 13, but do NOT hardcode any number as a replacement literal). Leave `total: 22` and the original `recorded` timestamp unchanged.
  3. Replace the IN-09 markdown row with `| IN-09 | info | fixed | quick 261111-tis (api-reference database examples expand the tilde via pathlib before opening the DB; Complete Search Example plus the identical DatabaseConnection and SearchBackend usage patterns) |`.

  Preserve every other YAML block, markdown row, ordering, explanatory paragraph, and trailing newline byte-for-byte. IN-01, CR-01, CR-02 (sibling tip), IN-06 (sibling tiq), and IN-10 (sibling tir) may legitimately already be fixed at execution time — do not assert their state and do not touch their records; every other finding is preserved exactly as found. Do not introduce any `**Status:**` line (that format belongs to other ledger types), do not edit the historical 10-REVIEW.md, other review ledgers, or STATE.md; the orchestrator owns quick-task state updates.

  Run the verification gate before committing the ledger edit; commit only this ledger path (never the pre-existing .planning/ churn).
  </action>
  <verify>
    <automated>python -I -c "from pathlib import Path; import re, subprocess; path = '.planning/milestones/v1.0-phases/10-raise-pytest-coverage-to-90/10-REVIEW-DISPOSITION.md'; before = subprocess.check_output(['git', 'show', 'HEAD:' + path], text=True); yaml_old = '  - id: IN-09\n    severity: info\n    disposition: open\n'; yaml_new = '  - id: IN-09\n    severity: info\n    disposition: fixed\n'; row_old = '| IN-09 | info | open | - |'; row_new = '| IN-09 | info | fixed | quick 261111-tis (api-reference database examples expand the tilde via pathlib before opening the DB; Complete Search Example plus the identical DatabaseConnection and SearchBackend usage patterns) |'; assert before.count(yaml_old) == 1; assert before.count(row_old) == 1; counts = re.findall(r'\nopen: (\d+)\n', before); assert len(counts) == 1; expected = before.replace(yaml_old, yaml_new, 1).replace(row_old, row_new, 1); expected = re.sub(r'\nopen: \d+\n', '\nopen: %d\n' % (int(counts[0]) - 1), expected, count=1); assert expected != before; assert Path(path).read_text(encoding='utf-8') == expected; assert '\ntotal: 22\n' in expected; assert all(row in expected for row in ('| WR-07 | warning | open | - |', '| WR-08 | warning | open | - |', '| IN-02 | info | open | - |', '| IN-07 | info | open | - |')); print('IN-09-fixed; open-count-decremented-from-execution-time-HEAD; all-other-ledger-content-unchanged')"</automated>
  </verify>
  <done>IN-09 is fixed in YAML and the table, the open count is exactly one less than the execution-time HEAD value with total still 22, the Source cell names quick 261111-tis, and an exact execution-time baseline reconstruction proves no other ledger content changed.</done>
</task>

</tasks>

<verification>
Source coverage audit (the quick constraint selects exactly one finding; no RESEARCH artifact or locked D-XX decisions exist):

| SOURCE | ID | Item | Task | Status |
|--------|----|------|------|--------|
| GOAL | quick-261111-tis | Close Phase 10 IN-09: fix the Complete Search Example tilde defect and close the ledger record | 1-2 | COVERED |
| REQ | PHASE10-IN-09 | pathlib expanduser before sqlite3.connect at the finding's named site (api-reference.md:818), plus the two trivially-identical raw-tilde DB patterns (650, 790) per the item's scope rule; three-edit disposition closure | 1-2 | COVERED |
| CONTEXT | orchestrator notes | Doc-only change; hand-owned api-reference.md only; never touch generator-owned docs; do NOT add api-reference.md to tests/test_docs.py's validated set; shared-ledger execution-time-robust count decrement; three-edit closure with Source cell naming quick 261111-tis; no Status lines; sandboxed demonstration preferred over a live run; PATH pytest, full quality suite at end; preserve working-tree churn | 1-2 | COVERED |
| CONTEXT | sibling items | tip (IN-01/CR-01/CR-02), tiq (IN-06), tir (IN-10), all other IN/CR/WR findings; collection-registration ~/Documents path literals (different API surface) | - | EXCLUDED BY BATCH SCOPE, not silently omitted; ledger preservation is verified by byte-equality reconstruction; collection literals recorded as checked-and-left in the SUMMARY |

Capability checkpoints (api-coverage, assumption-delta, schema-push, security threat-model) are phase-scoped; this quick-batch item has no phase, so the detectors resolve to skipped. No COVERAGE.md or threat_model block is produced. No package install, schema file, or external integration is in scope.

Final gates, run from the checkout root after both tasks:
1. The Task 1 doc gate (static + sandboxed demonstration) passes.
2. `ruff check src tests`
3. `ruff format --check src tests`
4. `python -m pytest` (full run includes the coverage gate; PATH pytest, not .venv; baseline 1528 passed must stay green — doc-only change)
5. `ty check src/sif`
6. `git diff --exit-code -- src tests docs/cli-reference.md docs/configuration.md` proves no code, test, or generator-owned doc changed (tests/test_docs.py is under tests/ and stays untouched — api-reference.md is NOT added to DOCS_FILES).
7. Review the scoped diff: only `docs/api-reference.md` (three example blocks: pathlib import + expanduser construction each) and the Phase 10 disposition ledger (three edits) carry task changes; commits touch only those task-scoped paths and never stage the pre-existing `.planning/` churn. Planning SUMMARY/STATE artifacts are handled separately by the orchestrator.
</verification>

<success_criteria>
- The Complete Search Example (the finding's named site) and the two identical DatabaseConnection/SearchBackend usage examples all expand the tilde via pathlib before opening the database; the static gate is demonstrably red at the unmodified baseline (3 raw-tilde hits, 0 fixed forms) and green after the fix.
- All 65 python blocks in api-reference.md compile; the sandboxed demonstration opens the intended DB under a throwaway HOME using the doc's verbatim db_path expression, with no literal tilde directory created; every other doc line is byte-identical.
- IN-09 alone becomes fixed, the ledger open count is exactly one less than its execution-time HEAD value, and exact baseline reconstruction proves every other review record remains unchanged.
- Full ruff, format, pytest, and ty quality gates pass unchanged (doc-only change; plain PATH python -m pytest; the suite is color-env-hermetic).
</success_criteria>

<output>
Create `.planning/quick/261111-tis-close-phase-10-in-09-fix-the-complete-search-example-in-docs/261111-tis-SUMMARY.md` with `status: complete` in SUMMARY frontmatter when done. Record the closed finding as Phase 10 IN-09 (Complete Search Example tilde expansion, api-reference.md:818 — the finding's named site), the two additional identical sites found and fixed (DatabaseConnection usage at line 650, SearchBackend usage at line 790, with the source-verified reason neither class expands the tilde), the collection-registration path literals checked and deliberately left untouched, the sandboxed demonstration evidence (old pattern rc=1 vs new pattern opening the intended DB), and the ledger open-count decrement observed at execution time (from the execution-time HEAD value, whatever siblings landed first). Do not commit planning artifacts or STATE.md; the orchestrator handles the docs/state commit.
</output>