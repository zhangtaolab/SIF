---
phase: quick-261111-pqy
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - src/sif/cli/commands/collection.py
  - tests/unit/cli/test_collection.py
  - .planning/milestones/v1.0-phases/10-raise-pytest-coverage-to-90/10-REVIEW-DISPOSITION.md
autonomous: true
requirements:
  - PHASE10-WR-05
estimate:
  tokens: 14000
  raw_tokens: 14000
  tasks: 2
  confidence: low
must_haves:
  truths:
    - "sif collection ls <name> <subpath> filters the disk scan collection-relative and segment-aligned: 'python' lists <root>/python/a.md and never <root>/python2/b.md; an absolute subpath, an exact-file subpath, and a trailing-slash subpath select the same files"
    - "No-subpath listing, the missing-collection error, the empty-collection message, and tree rendering remain unchanged; all 19 existing test_collection.py tests pass unmodified; a subpath matching nothing exits 0 with the existing 'No files found in collection.' message"
    - "The five new regression tests are red against the planning baseline (HEAD d86bb8a) and green after the fix"
    - "Phase 10 WR-05 is recorded as fixed in both disposition representations, the open count is 18, and every other finding record remains byte-identical"
  artifacts:
    - src/sif/cli/commands/collection.py
    - tests/unit/cli/test_collection.py
    - .planning/milestones/v1.0-phases/10-raise-pytest-coverage-to-90/10-REVIEW-DISPOSITION.md
  key_links:
    - "collection_ls subpath filter -> Path(collection.path) join for relative subpaths -> segment-aligned equality-or-prefix comparison against resolved absolute scan paths (mirrors the shipped WR-04 predicate in ls.py:53-57)"
    - "TestCollectionRealDatabase real-SQLite fixtures -> tmp_path collection roots with sibling python/ and python2/ subtrees -> output assertions pin both the relative-resolution and segment-alignment contracts"
    - "WR-05 YAML disposition + WR-05 markdown row + open count -> one consistent review ledger with no unrelated edits"
---

<objective>
Correct Phase 10 WR-05 only: `collection_ls` in `src/sif/cli/commands/collection.py` (line 334) declares a `subpath` argument, silences it with `# noqa: ARG001`, and never uses it — `sif collection ls notes python` returns the full collection listing with no filtering. WR-04's fix (quick 261111-nj0, commit 68f4101) shipped and validated the collection-relative segment-aligned predicate in `ls.py:53-57`, which unblocks implementing the same filtering here.

Selection rationale (smallest safe live item among WR-01/02/05/06/07/08/09, all re-verified live at HEAD d86bb8a):
- WR-05 SELECTED: live (collection.py:334 still carries `# noqa: ARG001`; subpath unused), one production file, a pure filter over the existing disk scan; mirrors an already-shipped, tested predicate; no interface, protocol, or documentation change; the one existing subpath test is compatible with the fix and needs no modification.
- WR-02 STALE (re-confirmed at HEAD): Phase 11 retired the reported whole-run transaction. `update_cmd` (index.py:44-111) delegates to `IncrementalIndexer`, which commits one short BEGIN IMMEDIATE transaction per file (incremental.py:5-6 and 332-335, D-04: "earlier files stay durable") — a stronger guarantee than the per-collection fix WR-02 requested. Its ledger record stays open; staleness triage is a separate task.
- WR-06 STALE (re-confirmed at HEAD): bench.py:622-627 wraps fixture `json.load` in ClickException, 631-635 wraps evaluator construction, and 671-681 wraps evaluation. Record stays open.
- WR-01 live (collection.py:89-96 deletes documents with no embedding purge; `delete_by_collection` in repositories.py also skips it) but the fix needs index.py's embedding-purger helper or a new shared module plus the repositories.py purge and sqlite-vec availability handling — multi-file.
- WR-07 live (backend.py:211 slices only under `if from_line is not None:`) but handling max_lines alone changes MCP `line_start`/`line_end` metadata from None/None to 1/N on that path — a protocol-contract decision, broader than a CLI predicate.
- WR-08 live but contradicts the documented fail-fast vector posture (CLAUDE.md: VectorSearcher fails fast; HybridSearcher vector exceptions propagate uncaught) — not smallest-safe per constraint.
- WR-09 live (main.py:257-263 inline lexicographic DELETE; repositories.py:551 naive-local write) but the fix spans the read side and the write side in two production files plus tests — multi-file.

Planning-time reproduction at HEAD `d86bb8a` used a real temporary SQLite index (collection added through the real top-level CLI) and a real on-disk root with `python/a.md` and `python2/b.md`: `collection ls notes python` listed BOTH files (defect confirmed — argument ignored). The post-fix predicate was then evaluated against the real `FileScanner.scan` output (resolved absolute Paths): 'python', 'python/', 'python/a.md', and the absolute root/python each select exactly python/a.md; 'python2' selects only python2/b.md; 'missing' selects none — the regression contract is non-vacuous.

Purpose: make the documented `collection ls` subpath argument actually filter, collection-relative and segment-aligned, without changing any behavior outside the filter.
Output: a corrected filter in collection_ls, focused regression coverage in the file's established real-SQLite style, and WR-05 marked fixed without disturbing any other review item.
</objective>

<execution_context>
@~/.claude/gsd-core/workflows/execute-plan.md
@~/.claude/gsd-core/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md
@.planning/milestones/v1.0-phases/10-raise-pytest-coverage-to-90/10-REVIEW.md
@.planning/milestones/v1.0-phases/10-raise-pytest-coverage-to-90/10-REVIEW-DISPOSITION.md
@src/sif/cli/commands/collection.py
@src/sif/cli/commands/ls.py
@tests/unit/cli/test_collection.py

Planning evidence:
- `src/sif/cli/commands/collection.py`, `collection_ls` (lines 330-369): signature line 334 carries `# noqa: ARG001`; the body scans disk via `FileScanner().scan(Path(collection.path), pattern=collection.pattern, ignore_patterns=collection.ignore_patterns)` (lines 351-356), checks `if not scan_result.files:` (line 358), and renders `sorted(scan_result.files)` with `file_path.relative_to(collection.path)` (lines 365-367). `Path` is already imported (line 5). The entire defect is the unused argument.
- Reference predicate (shipped by WR-04, do NOT modify): `src/sif/cli/commands/ls.py:53-57` — `sub = Path(subpath)`; `resolved = sub if sub.is_absolute() else Path(coll.path) / sub`; `target = str(resolved).rstrip("/")`; keep rows where `d.path == target or d.path.startswith(target + "/")`. Mirror this exactly, with one type adaptation: `scan_result.files` holds `Path` objects (scanner.py:14), so compare `str(f)` instead of `d.path`.
- Stored/scanned paths are resolved absolute: `collection_add` stores `str(Path(path).resolve())` (collection.py:59) and `FileScanner.scan` resolves the root before rglob (scanner.py:119), so `Path(collection.path) / subpath` reproduces the scanned form. Do NOT add `.resolve()` or `os.path.normpath` to the filter — extra normalization would change symlink/`..` semantics beyond the finding (same discipline as the WR-04 fix).
- Empty-result design (decided): apply the filter BEFORE the existing empty check and reuse the existing "[yellow]No files found in collection.[/yellow]" message for a subpath that matches nothing (exit 0). No new message, no second empty branch. Tree rendering stays collection-root-relative (`python/a.md`), consistent with the existing test assertion and with ls_cmd's full-path rendering.
- `tests/unit/cli/test_collection.py` ls tests live in `TestCollectionRealDatabase` (lines 26-264): real SQLite + real tmp_path directories through the top-level CLI via the `_invoke`/`_seed` helpers (lines 44-59), autouse `isolated_settings` fixture. Follow this established real-database convention — do NOT introduce mock-based ls tests here. The existing `test_ls_with_subpath_and_without_files` (lines 206-221) asserts only that "projects/roadmap.md" appears for subpath "projects" and that an empty collection prints the no-files message — both assertions hold before AND after the fix, so no existing test may be modified. Baseline grounded at planning time: `python -m pytest tests/unit/cli/test_collection.py -q --no-cov` → 19 passed in 0.97s at HEAD d86bb8a.
- `docs/cli-reference.md` (generator-owned, never hand-edit) lists `subpath` as an optional text argument with an empty description (collection ls arguments table, lines 167-172). The fix changes no signature, option, or help text, so no docs regeneration is needed or permitted.
- Ledger closure convention for THIS file (verified against the live ledger and the WR-04 closure commit 68f4101): exactly three scoped edits — YAML `disposition: open` → `fixed`, aggregate `open: 19` → `open: 18`, and the WR-04-style markdown row replacement. The `  **Status:** resolved` line format mentioned in some continuity notes belongs to deferred-items/UAT gap ledgers, NOT to this review-disposition ledger; do not introduce it here.
- WR-04 boundary: `src/sif/cli/commands/ls.py` and `tests/unit/cli/test_ls.py` are the shipped reference and must stay byte-identical. WR-01 lives in the same production file (collection_remove, lines 75-98) — do not touch it while editing collection_ls.
- Test environment: the suite is color-env-hermetic (conftest scrub, commit 6522663) — plain `python -m pytest` works. Use the PATH python/pytest (miniconda base), NOT .venv (no torch). Targeted runs need `--no-cov` (coverage gate fail_under=90); the full-suite gate runs WITH coverage.
- Discovery level 0: a local path-predicate correction mirroring a shipped predicate, using the test file's established real-SQLite pattern; no new dependency, external integration, research, or ORM schema change.
- Scope guard: WR-01, WR-02, WR-06 through WR-09 and every IN/CR finding stay untouched. The working tree carries pre-existing uncommitted `.planning/` churn (config.json, state.json, agent-history.json, PATTERNS files, research cache, tmp) that predates this task — never stage, commit, or revert any of it; commits touch only task-scoped paths.
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Pin and correct the WR-05 collection ls subpath filter</name>
  <files>src/sif/cli/commands/collection.py, tests/unit/cli/test_collection.py</files>
  <behavior>
    - With a collection root containing python/a.md and python2/b.md, subpath "python" lists python/a.md and never python2/b.md (baseline lists both — the argument is ignored).
    - The absolute subpath (root joined with "python") lists python/a.md and never python2/b.md (baseline lists both).
    - The exact-file subpath "python/a.md" and the trailing-slash subpath "python/" select the same single file as "python".
    - A subpath matching nothing ("missing") exits 0 and prints the existing "No files found in collection." message with neither filename (baseline prints the full listing).
    - Preservation: no-subpath listing of the same collection lists both python/a.md and python2/b.md (passes before and after); the existing test_ls_with_subpath_and_without_files, the missing-collection error test, and all other existing tests pass unmodified.
  </behavior>
  <action>
  First change tests/unit/cli/test_collection.py only. Add one new fixture to `TestCollectionRealDatabase` beside `notes_dir`, named `sibling_notes_dir`, following the same style: create `tmp_path / "notes"` with subdirectories `python` and `python2`, write `python/a.md` ("# A\n") and `python2/b.md` ("# B\n") with encoding="utf-8", return the notes root. Then add five tests to `TestCollectionRealDatabase`, each seeding via the existing `self._seed(db_path, "notes", sibling_notes_dir)` helper and invoking via `self._invoke` (which already sets COLUMNS=200): `test_ls_subpath_is_segment_aligned` (args "ls", "notes", "python"; assert exit 0, "python/a.md" in output, "b.md" not in output; then invoke "ls", "notes" with no subpath and assert both "python/a.md" and "python2/b.md" appear — the preservation leg), `test_ls_subpath_absolute_is_segment_aligned` (args "ls", "notes", str(sibling_notes_dir / "python"); same two filename assertions), `test_ls_subpath_exact_file` (args "ls", "notes", "python/a.md"; same assertions), `test_ls_subpath_trailing_slash` (args "ls", "notes", "python/"; same assertions), and `test_ls_subpath_no_match_reports_no_files` (args "ls", "notes", "missing"; assert exit 0, "No files found in collection." in output, "a.md" not in output, "b.md" not in output). Do not modify any existing test, the notes_dir fixture, or the helpers. Run the file before any production edit and confirm the five new tests fail on their output assertions (baseline: subpath ignored, both files listed; the no-match case prints the full listing instead of the message), not during collection or setup; the preservation leg and all 19 existing tests pass at baseline.

  Then modify only `collection_ls` in `src/sif/cli/commands/collection.py`. Remove the `# noqa: ARG001` comment from the signature line (subpath becomes used; leaving the noqa would trip RUF100). Immediately after the `scan_result = scanner.scan(...)` assignment and before the empty check, insert the filter: bind `files = scan_result.files`; under `if subpath:` build `sub = Path(subpath)`, resolve `resolved = sub if sub.is_absolute() else Path(collection.path) / sub`, bind `target = str(resolved).rstrip("/")`, and rebind `files` to the comprehension keeping entries where `str(f) == target or str(f).startswith(target + "/")` (scan files are Path objects — compare their str form; this mirrors ls.py:53-57 exactly). Change the empty check to `if not files:` and the tree loop to `for file_path in sorted(files):`. Keep the leading slash on the target, do not add resolve()/normpath, do not change the `if subpath:` truthiness guard, and leave the scan call, the no-files message text, the missing-collection error, the tree rendering (`file_path.relative_to(collection.path)`), and every other command in the module byte-identical. No new imports are needed (Path is already imported). If the formatting check complains, run ruff format on the two task files only.

  Do not edit `src/sif/cli/commands/ls.py` or `tests/unit/cli/test_ls.py` (shipped WR-04 reference), `collection_remove` or any other command in collection.py (WR-01), `src/sif/mcp/backend.py` (WR-07/08), `src/sif/cli/commands/index.py` or `src/sif/indexing/incremental.py` (WR-02, stale), `src/sif/cli/main.py` or `src/sif/database/repositories.py` (WR-09), `src/sif/cli/commands/bench.py` (WR-06, stale), generator-owned docs, or skills. This task corrects the collection ls subpath filter only.
  </action>
  <verify>
    <automated>python -m pytest tests/unit/cli/test_collection.py -q --no-cov &amp;&amp; ruff check src/sif/cli/commands/collection.py tests/unit/cli/test_collection.py &amp;&amp; ruff format --check src/sif/cli/commands/collection.py tests/unit/cli/test_collection.py</automated>
  </verify>
  <done>The five new tests failed on output assertions before the production edit and the full test_collection.py file (24 tests) now passes; relative subpaths resolve against the collection root, matching is segment-aligned, absolute/exact-file/trailing-slash forms agree, and a non-matching subpath exits 0 with the existing no-files message; no-subpath listing and all 19 existing tests pass unmodified; ruff and formatting pass; the only production delta is the noqa removal plus the filter block and its two consumer lines inside collection_ls.</done>
</task>

<task type="auto">
  <name>Task 2: Close only WR-05 in the Phase 10 disposition ledger</name>
  <files>.planning/milestones/v1.0-phases/10-raise-pytest-coverage-to-90/10-REVIEW-DISPOSITION.md</files>
  <action>
  In .planning/milestones/v1.0-phases/10-raise-pytest-coverage-to-90/10-REVIEW-DISPOSITION.md, make exactly three scoped updates after Task 1 passes:

  1. In the WR-05 YAML finding block only, change `disposition: open` to `disposition: fixed`; preserve its id, severity, and title.
  2. Change the aggregate `open: 19` to `open: 18`; leave `total: 22` and the original `recorded` timestamp unchanged.
  3. Replace the WR-05 markdown row with `| WR-05 | warning | fixed | quick 261111-pqy (collection ls subpath collection-relative segment-aligned filter plus regression tests) |`.

  Preserve every other YAML block, markdown row, ordering, explanatory paragraph, and trailing newline byte-for-byte. WR-01, WR-02, and WR-06 through WR-09 remain open; the WR-03, WR-04, and WR-10 fixed rows and all IN/CR rows are preserved. WR-02 and WR-06 stay open despite the observed staleness — only the selected finding's record may change in this task. Do not introduce any `**Status:**` line (that format belongs to other ledger types), do not edit the historical 10-REVIEW.md, other review ledgers, or STATE.md; the orchestrator owns quick-task state updates.

  Baseline grounded at planning time (HEAD d86bb8a): the ledger is clean against HEAD and each of the three replacement literals occurs exactly once. Run the verification gate before committing the ledger edit.
  </action>
  <verify>
    <automated>python -I -c "from pathlib import Path; import subprocess; path = '.planning/milestones/v1.0-phases/10-raise-pytest-coverage-to-90/10-REVIEW-DISPOSITION.md'; before = subprocess.check_output(['git', 'show', 'HEAD:' + path], text=True); expected = before.replace('  - id: WR-05\n    severity: warning\n    disposition: open\n', '  - id: WR-05\n    severity: warning\n    disposition: fixed\n', 1).replace('\nopen: 19\n', '\nopen: 18\n', 1).replace('| WR-05 | warning | open | - |', '| WR-05 | warning | fixed | quick 261111-pqy (collection ls subpath collection-relative segment-aligned filter plus regression tests) |', 1); assert expected != before; assert Path(path).read_text(encoding='utf-8') == expected; assert all(('| WR-%02d | warning | open | - |' % number) in expected for number in (1, 2, 6, 7, 8, 9)); assert '| WR-03 | warning | fixed |' in expected; assert '| WR-04 | warning | fixed |' in expected; assert '| WR-10 | warning | fixed |' in expected; print('WR-05-fixed; all-other-ledger-content-unchanged')"</automated>
  </verify>
  <done>WR-05 is fixed in YAML and the table, the open count is 18 with total still 22, the source cell names quick 261111-pqy, and an exact baseline reconstruction proves no other ledger content changed.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| User-supplied subpath argument -> collection ls filter over a read-only disk scan | A CLI argument crosses into a path-matching predicate over scanned file paths; the defect made the documented filter a silent no-op (display-only — collection ls scans disk read-only and never writes) |

No new network, package, authentication, or external-service boundary is introduced.

## STRIDE Threat Register

| Threat ID | Category | Component | Severity | Disposition | Mitigation Plan |
|-----------|----------|-----------|----------|-------------|-----------------|
| T-pqy-01 | Denial of Service | src/sif/cli/commands/collection.py collection_ls subpath filter | low | mitigate | Resolve relative subpaths against the collection root and compare whole path segments so the documented listing filter cannot silently ignore the requested subtree or leak sibling subtrees; pin both contracts with regression tests |
| T-pqy-SC | Tampering | package installs | low | accept | No package-manager install, dependency, or lockfile task exists; the package legitimacy gate is not applicable |
</threat_model>

<verification>
Source coverage audit (the quick constraint selects exactly one warning; no RESEARCH artifact or locked D-XX decisions exist):

| SOURCE | ID | Item | Task | Status |
|--------|----|------|------|--------|
| GOAL | quick-261111-pqy | Address one smallest safe, live-reproducible Phase 10 WR item without broadening scope | 1-2 | COVERED — WR-05 only |
| REQ | PHASE10-WR-05 | Collection-relative segment-aligned subpath filter for collection ls, focused regression coverage, disposition update | 1-2 | COVERED |
| CONTEXT | quick constraints | One WR item; live reproduction; stale-candidate skips recorded (WR-02, WR-06); convention-conflict skip recorded (WR-08); broader-candidate skips recorded (WR-01, WR-07, WR-09); repo-relative commands; preserve unrelated findings and working-tree churn; PATH pytest, hermetic color env | 1-2 | COVERED |
| CONTEXT | excluded backlog | WR-01/02/06..09 and all IN/CR items (WR-02 and WR-06 stale but records untouched) | 2 | EXCLUDED BY USER CONSTRAINT, not silently omitted; ledger preservation is verified |

No external API integration or core-assumption generalization is in scope (quick mode: phase-scoped detectors have no phase input and are skipped). No Payload/Prisma/Drizzle/Supabase/TypeORM schema file is touched, so no schema-push task applies.

Final gates, run from the checkout root after both tasks:
1. `python -m pytest tests/unit/cli/test_collection.py -q --no-cov`
2. `ruff check src tests`
3. `ruff format --check src tests`
4. `python -m pytest` (full run includes the coverage gate; PATH pytest, not .venv)
5. `git diff --exit-code -- src/sif/cli/commands/ls.py tests/unit/cli/test_ls.py src/sif/mcp/backend.py src/sif/cli/commands/index.py src/sif/indexing/incremental.py src/sif/cli/commands/bench.py src/sif/cli/main.py src/sif/database/repositories.py docs/cli-reference.md docs/configuration.md` proves every other finding's files, the shipped WR-04 reference, and generator-owned docs stayed untouched.
6. Review the scoped diff: only `src/sif/cli/commands/collection.py`, `tests/unit/cli/test_collection.py`, and the Phase 10 disposition ledger carry task edits; commits touch only those task-scoped paths and never stage the pre-existing `.planning/` churn. Planning SUMMARY/STATE artifacts are handled separately by the orchestrator.
</verification>

<success_criteria>
- The five new regression tests are demonstrably red before the filter edit (subpath ignored: both sibling files listed; no-match prints the full listing) and green afterward, with the no-subpath preservation leg and all 19 existing tests passing throughout.
- The only production change is inside collection_ls: the noqa removal, the filter block, and the two consumer lines; the scan call, empty message, missing-collection error, tree rendering, and every other command remain byte-identical.
- WR-05 alone becomes fixed, the ledger open count becomes 18, and exact baseline reconstruction proves every other review record remains unchanged.
- Full ruff, format, and pytest quality suite passes (plain PATH python -m pytest; the suite is color-env-hermetic).
</success_criteria>

<output>
Create `.planning/quick/261111-pqy-next-phase-10-item-address-the-smallest-/261111-pqy-SUMMARY.md` with `status: complete` in SUMMARY frontmatter when done. Record the selected finding as Phase 10 WR-05, the per-finding selection assessment (WR-02 stale via Phase 11 D-04 per-file commits in incremental.py:5-6/332-335; WR-06 staleness re-confirmed at bench.py:622-627/631-635/671-681; WR-08 convention-conflicting; WR-01/07/09 broader; WR-05 unblocked by the shipped WR-04 predicate), and the red-to-green regression evidence. Do not commit planning artifacts or STATE.md; the orchestrator handles the docs/state commit.
</output>
