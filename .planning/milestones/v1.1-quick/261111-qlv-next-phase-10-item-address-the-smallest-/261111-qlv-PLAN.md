---
phase: quick-261111-qlv
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - .planning/milestones/v1.0-phases/10-raise-pytest-coverage-to-90/10-REVIEW-DISPOSITION.md
autonomous: true
requirements:
  - PHASE10-WR-02
estimate:
  tokens: 10000
  raw_tokens: 10000
  tasks: 1
  confidence: low
must_haves:
  truths:
    - "WR-02's reported whole-run transaction is provably absent at execution HEAD: update_cmd delegates to IncrementalIndexer, no db.connection/db.transaction context wraps the collection loop, and each file's writes commit in their own short BEGIN IMMEDIATE transaction (D-04) — a stronger guarantee than the per-collection commit the finding requested"
    - "The shipped durability regression test test_mid_run_failure_keeps_completed_files_durable passes: a mid-run failure leaves earlier files committed (proven on a fresh connection), the failing file is not half-written, and later files are untouched"
    - "Phase 10 WR-02 is recorded as fixed in both disposition representations, the open count is 17 with total still 22, and exact baseline reconstruction proves every other finding record remains byte-identical"
    - "Zero production, test, or generator-owned doc changes: git diff --exit-code -- src tests docs passes, and the pre-existing .planning working-tree churn is neither staged, committed, nor reverted"
  artifacts:
    - .planning/milestones/v1.0-phases/10-raise-pytest-coverage-to-90/10-REVIEW-DISPOSITION.md
  key_links:
    - "update_cmd (index.py:80/98) -> IncrementalIndexer.update_collection -> per-file with self._conn: commits (incremental.py:324/335/365/393 plus stats transactions at 166/270) -> factory isolation_level=IMMEDIATE — the delegation chain that retired the whole-run transaction"
    - "WR-02 YAML disposition + WR-02 markdown row + open count -> one consistent review ledger; the reconstruction gate ties the working file to git HEAD plus exactly three scoped replacements"
---

<objective>
Close Phase 10 WR-02 only, by evidence-backed triage: the reported defect ("`index update` runs all collections in one implicit transaction — later failure discards earlier collections' work") no longer exists in the code. Phase 11 extracted the indexing loop into `IncrementalIndexer`, which commits one short BEGIN IMMEDIATE transaction per file (D-04) — strictly stronger than the per-collection commit WR-02 requested. This plan verifies that staleness live at execution HEAD with a structural gate plus the shipped durability regression test, then records WR-02 as `fixed` in the disposition ledger without touching any other record or any code.

Selection rationale (smallest safe item among the six open WR records, all re-verified live at planning HEAD cbf5e44 on branch dev):
- WR-02 SELECTED (fully stale, zero code risk): `update_cmd` (index.py:44-111) delegates to `IncrementalIndexer(db.connection)` (line 80) and calls `indexer.update_collection` per collection (lines 98-102); no `with db.connection:` or `db.transaction()` wraps the loop. `Database.__enter__/__exit__` (database.py:56-62) only returns self / closes the connection — no implicit whole-run transaction. The factory sets `isolation_level="IMMEDIATE"` (factory.py:18-22, 52-53), so each per-file `with self._conn:` block (incremental.py:324, 335, 365, 393; stats at 166, 270 — six total) is its own BEGIN IMMEDIATE commit. Pre-update-hook failures raise ClickException (index.py:134/144) outside any open write transaction, so earlier collections' files stay durable — the exact failure mode WR-02 reported is gone. The shipped test `test_mid_run_failure_keeps_completed_files_durable` (test_incremental.py:318-356) pins this on a fresh connection. Disposition `fixed` is the ledger's honest vocabulary: the defect was fixed by Phase 11 work; this task verifies and records it. (`skipped` would imply declining a live fix; `deferred` would imply postponing one; the ledger has no `stale` category — do not invent one.)
- WR-06 NOT fully stale — left open: the primary defect is gone (bench.py:623-627 wraps fixture `json.load` in ClickException, 632-635 wraps settings ValidationError, 661-681 wraps evaluator construction and evaluation), BUT the finding's Issue and Fix also name the missing `encoding="utf-8"` on `open(fixture)` — bench.py:624 still reads `with open(fixture) as f:` and the file contains no `encoding` keyword at all. Closing WR-06 as `fixed` now would overclaim. The one-line encoding fix plus a contract test and the WR-06 closure is the natural next quick item.
- WR-01 live but broader: collection_remove (collection.py:89-96) deletes documents with no embedding purge; the fix needs the `_embedding_purger` helper (now in incremental.py:58-69) shared or duplicated, plus `delete_by_collection` in repositories.py and sqlite-vec availability handling — multi-file.
- WR-07 live but broader: backend.py:211 slices only under `if from_line is not None:`; handling max_lines alone changes MCP `line_start`/`line_end` metadata from None/None to 1/N on that path — a protocol-contract decision, not a smallest-safe move.
- WR-08 live but convention-conflicting: degrading hybrid_search to BM25 when sqlite-vec is missing contradicts the documented fail-fast vector posture (CLAUDE.md: VectorSearcher fails fast; HybridSearcher vector exceptions propagate uncaught) — needs a user decision, not a quick fix.
- WR-09 live but broader: main.py:257-263 inline lexicographic DELETE against aware-UTC now; repositories.py:551 still writes naive-local `datetime.fromtimestamp(expires_at).isoformat()`. A correct fix spans the write side, the read side, and legacy naive-row comparison semantics (the repository's own clear_expired at repositories.py:570-576 is also lexicographic) — two production files plus migration reasoning.

Planning-time evidence baselines (HEAD cbf5e44, all gates run against the live tree):
- Structural staleness gate passed: "WR-02-stale-confirmed: delegation present, no whole-run txn, per-file commit blocks = 6".
- `python -m pytest tests/unit/indexing/test_incremental.py -q --no-cov` → 10 passed in 0.47s.
- Ledger clean against HEAD; each of the three closure literals (`  - id: WR-02` YAML block, `^open: 18$`, `| WR-02 | warning | open | - |`) occurs exactly once.
- `git diff --exit-code -- src tests docs` → clean (pre-existing churn is confined to .planning/).

Purpose: make the review ledger tell the truth about WR-02 — the defect is fixed in shipped code, and the record should say so with verifiable evidence — without changing any behavior or disturbing any other finding.
Output: WR-02 marked fixed in both ledger representations (open 18 → 17), an exact baseline-reconstruction proof that nothing else changed, and a SUMMARY recording the per-candidate assessment for the next quick item.
</objective>

<execution_context>
@~/.claude/gsd-core/workflows/execute-plan.md
@~/.claude/gsd-core/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md
@.planning/milestones/v1.0-phases/10-raise-pytest-coverage-to-90/10-REVIEW.md
@.planning/milestones/v1.0-phases/10-raise-pytest-coverage-to-90/10-REVIEW-DISPOSITION.md
@src/sif/cli/commands/index.py
@src/sif/indexing/incremental.py
@tests/unit/indexing/test_incremental.py

Planning evidence:
- Original finding (10-REVIEW.md WR-02): the multi-collection loop at old index.py:55-108 ran inside one `with db.connection:` transaction; a pre-update-command failure or parse ClickException for collection N rolled back collections 1..N-1. Requested fix: one commit per collection. Current reality supersedes it: per-FILE commits (D-04), documented in incremental.py:1-13 ("a mid-run failure keeps completed files durable (resumable) instead of rolling back the whole run").
- Delegation chain: index.py:80 `indexer = IncrementalIndexer(db.connection)`; index.py:98-102 `indexer.update_collection(coll, force=force, progress=...)`. The only `with` blocks inside update_cmd are `Database(...)`, `index_lock(...)`, and `Progress(...)` — none opens a write transaction. `_run_pre_update_hook` (index.py:114-144) runs per collection BEFORE that collection's indexer call and raises ClickException on timeout/non-zero exit; no write transaction is open at that point.
- Transaction semantics: factory.py arms `isolation_level="IMMEDIATE"` at connect time, so every `with conn:` block is BEGIN IMMEDIATE with identical commit/rollback semantics; connections are never autocommit. database.py:56-62 `__enter__` returns self, `__exit__` closes — the `with Database(...)` wrapper in update_cmd adds no transaction.
- Test backing: tests/unit/indexing/test_incremental.py::TestIncrementalIndexer::test_mid_run_failure_keeps_completed_files_durable (lines 318-356) fails the middle of three files via a monkeypatched DocumentRepository.create, then proves on a FRESH connection that exactly the first file committed, the failing file has no row and no chunks, and the third was never touched. Baseline: the whole file is 10 passed in 0.47s with --no-cov at HEAD cbf5e44.
- Ledger closure convention for THIS file (verified against the live ledger and the WR-04/WR-05 closure commits 68f4101/1ac9f24): exactly three scoped edits per record — YAML `disposition: open` → `fixed`, aggregate `open: N` decrement, and the markdown table row replacement with a `quick <task-id> (...)` Source cell. The `**Status:** resolved` line format belongs to deferred-items/UAT gap ledgers, NOT to this review-disposition ledger; do not introduce it here. Disposition vocabulary is exactly `open` / `fixed` / `skipped` / `deferred` (ledger footer); `fixed` is correct for a defect retired by shipped work. Avoid `|` characters inside the Source cell (the footer escapes them on gate re-runs).
- WR-06 boundary: bench.py:624 `with open(fixture) as f:` still lacks `encoding="utf-8"` (the finding's Issue and Fix both name it). WR-06 therefore stays OPEN — this task must not close it, fix it, or edit bench.py. It is the recommended next quick item (one-line encoding fix + contract test + WR-06 closure).
- Scope guard: WR-01, WR-06 through WR-09 and every IN/CR finding stay untouched, as do all production sources, tests, and generator-owned docs (docs/cli-reference.md, docs/configuration.md are wholesale regenerated by make docs-generate — never hand-edit; this task needs no docs change at all). The working tree carries pre-existing uncommitted `.planning/` churn (config.json, state.json, agent-history.json, PATTERNS files, research cache, 16-REVIEW iter2 files, tmp) that predates this task — never stage, commit, or revert any of it; the commit touches only the ledger path.
- Test environment: the suite is color-env-hermetic (conftest scrub, commit 6522663) — plain `python -m pytest` works. Use the PATH python/pytest (miniconda base), NOT .venv (no torch). Targeted runs need `--no-cov` (coverage gate fail_under=90); the full-suite gate runs WITH coverage.
- Discovery level 0: a documentation-only ledger triage backed by structural verification of existing shipped code and an existing regression test; no new dependency, external integration, research, or ORM schema change.
</context>

<tasks>

<task type="auto">
  <name>Task 1: Verify WR-02 staleness live, then close only WR-02 in the Phase 10 disposition ledger</name>
  <files>.planning/milestones/v1.0-phases/10-raise-pytest-coverage-to-90/10-REVIEW-DISPOSITION.md</files>
  <action>
  PHASE A — evidence gate (run FIRST, before any edit; halt on failure). From the checkout root, run the structural staleness gate and the durability test exactly as written in the verify block below. The gate parses update_cmd's AST and asserts (1) no `with` item in its body is db.connection or db.transaction, (2) an IncrementalIndexer assignment exists, (3) the IncrementalIndexer class contains at least four `with self._conn:` commit blocks (planning baseline: six), and (4) incremental.py carries the D-04 marker and the "earlier files stay durable" docstring phrase. Then run `python -m pytest tests/unit/indexing/test_incremental.py -q --no-cov` (planning baseline: 10 passed). If EITHER fails, STOP: do not edit the ledger. A failure means the code changed since planning and WR-02 may be live again — report the gate output and hand back without closing the record. Also confirm the ledger is clean against HEAD (`git diff --exit-code -- .planning/milestones/v1.0-phases/10-raise-pytest-coverage-to-90/10-REVIEW-DISPOSITION.md`) before editing; if it is dirty, stop and report (someone else's uncommitted ledger work must not be absorbed).

  PHASE B — exactly three scoped edits to .planning/milestones/v1.0-phases/10-raise-pytest-coverage-to-90/10-REVIEW-DISPOSITION.md, and nothing else:
  1. In the WR-02 YAML finding block only, change `disposition: open` to `disposition: fixed`; preserve its id, severity, and title byte-for-byte.
  2. Change the aggregate `open: 18` to `open: 17`; leave `total: 22` and the original `recorded` timestamp unchanged.
  3. Replace the WR-02 markdown row `| WR-02 | warning | open | - |` with `| WR-02 | warning | fixed | quick 261111-qlv (triage close: whole-run transaction superseded by Phase 11 IncrementalIndexer per-file BEGIN IMMEDIATE commits, D-04; staleness re-verified live with durability regression test) |`.

  Preserve every other YAML block, markdown row, ordering, explanatory footer paragraph, and trailing newline byte-for-byte. WR-01, WR-06, WR-07, WR-08, and WR-09 remain open — WR-06 stays open despite its stale primary defect because its encoding sub-item is still live (bench.py:624); only WR-02's record may change. The WR-03/WR-04/WR-05/WR-10 fixed rows and all IN/CR rows are preserved. Do not introduce any `**Status:**` line, do not invent a `stale` disposition, do not edit the historical 10-REVIEW.md, other review ledgers, STATE.md, or any file under src/, tests/, or docs/.

  PHASE C — verify and commit. Run the reconstruction gate and the scope guard from the verify block BEFORE committing: the gate rebuilds the expected file from `git show HEAD:<ledger>` plus exactly the three replacements above and asserts byte-equality with the working file, so any stray edit fails loudly. Then stage ONLY the ledger path (`git add .planning/milestones/v1.0-phases/10-raise-pytest-coverage-to-90/10-REVIEW-DISPOSITION.md`) and commit with message `docs(quick-261111-qlv-01): close Phase 10 WR-02 in disposition ledger (stale triage)`. Never use `git add -A` or `git add .`; the pre-existing .planning/ churn must remain uncommitted and untouched. Do not commit planning artifacts or STATE.md — the orchestrator handles the docs/state commit.
  </action>
  <verify>
    <automated>python -I -c "import ast; from pathlib import Path; idx = ast.parse(Path('src/sif/cli/commands/index.py').read_text(encoding='utf-8')); fn = next(n for n in ast.walk(idx) if isinstance(n, ast.FunctionDef) and n.name == 'update_cmd'); withs = [ast.unparse(w.items[0].context_expr) for w in ast.walk(fn) if isinstance(w, ast.With)]; assert not any('db.connection' in e or 'db.transaction' in e for e in withs), withs; assert any(isinstance(n, ast.Assign) and 'IncrementalIndexer' in ast.unparse(n) for n in ast.walk(fn)); inc_src = Path('src/sif/indexing/incremental.py').read_text(encoding='utf-8'); inc = ast.parse(inc_src); cls = next(n for n in ast.walk(inc) if isinstance(n, ast.ClassDef) and n.name == 'IncrementalIndexer'); n_conn = sum(1 for w in ast.walk(cls) if isinstance(w, ast.With) and any(ast.unparse(i.context_expr) == 'self._conn' for i in w.items)); assert n_conn >= 4, n_conn; assert 'D-04' in inc_src and 'earlier files stay durable' in inc_src; print('WR-02-stale-confirmed: delegation present, no whole-run txn, per-file commit blocks =', n_conn)" &amp;&amp; python -m pytest tests/unit/indexing/test_incremental.py -q --no-cov &amp;&amp; python -I -c "from pathlib import Path; import subprocess; path = '.planning/milestones/v1.0-phases/10-raise-pytest-coverage-to-90/10-REVIEW-DISPOSITION.md'; before = subprocess.check_output(['git', 'show', 'HEAD:' + path], text=True); expected = before.replace('  - id: WR-02\n    severity: warning\n    disposition: open\n', '  - id: WR-02\n    severity: warning\n    disposition: fixed\n', 1).replace('\nopen: 18\n', '\nopen: 17\n', 1).replace('| WR-02 | warning | open | - |', '| WR-02 | warning | fixed | quick 261111-qlv (triage close: whole-run transaction superseded by Phase 11 IncrementalIndexer per-file BEGIN IMMEDIATE commits, D-04; staleness re-verified live with durability regression test) |', 1); assert expected != before; assert Path(path).read_text(encoding='utf-8') == expected; assert '\nopen: 17\ntotal: 22\n' in expected; assert all(('| WR-%02d | warning | open | - |' % number) in expected for number in (1, 6, 7, 8, 9)); assert all(('| WR-%02d | warning | fixed |' % number) in expected for number in (3, 4, 5, 10)); print('WR-02-fixed; all-other-ledger-content-unchanged')" &amp;&amp; git diff --exit-code -- src tests docs</automated>
  </verify>
  <done>The structural gate passed at execution HEAD (delegation present, no whole-run write transaction in update_cmd, at least four per-file BEGIN IMMEDIATE commit blocks, D-04 durability docstring) and test_incremental.py is fully green including test_mid_run_failure_keeps_completed_files_durable; WR-02 is fixed in YAML and the table with a Source cell naming quick 261111-qlv and the Phase 11 supersession; the open count is 17 with total still 22; exact baseline reconstruction proves every other review record is byte-identical (WR-01/06/07/08/09 still open, WR-03/04/05/10 fixed rows and all IN/CR rows preserved); git diff --exit-code -- src tests docs passes; the commit contains only the ledger file and the pre-existing .planning churn is untouched.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| Review-ledger record -> future triage decisions | A disposition record is evidence for later work; an inaccurate closure (claiming fixed while a defect lives) misroutes future effort. This change is documentation-only — no runtime, network, package, authentication, or external-service boundary is introduced or crossed |

## STRIDE Threat Register

| Threat ID | Category | Component | Severity | Disposition | Mitigation Plan |
|-----------|----------|-----------|----------|-------------|-----------------|
| T-qlv-01 | Tampering | 10-REVIEW-DISPOSITION.md WR-02 record | low | mitigate | Structural evidence gate (AST proof of delegation + per-file commits) and the shipped durability regression test must pass before any edit; exact baseline reconstruction from git HEAD proves only the three scoped WR-02 edits landed and every other record is byte-identical; halt-on-failure prevents closing a record whose defect re-emerged |
| T-qlv-SC | Tampering | package installs | low | accept | No package-manager install, dependency, or lockfile task exists; the package legitimacy gate is not applicable |
</threat_model>

<verification>
Source coverage audit (the quick constraint selects exactly one warning; no RESEARCH artifact or locked D-XX decisions exist):

| SOURCE | ID | Item | Task | Status |
|--------|----|------|------|--------|
| GOAL | quick-261111-qlv | Address one smallest safe, well-scoped open Phase 10 WR item, re-assessed live | 1 | COVERED — WR-02 evidence-backed triage close |
| REQ | PHASE10-WR-02 | Verify the whole-run-transaction finding is superseded by shipped per-file commits and record it fixed without disturbing other records | 1 | COVERED |
| CONTEXT | quick constraints | One item; live verification before closure; ledger vocabulary fidelity (open/fixed/skipped/deferred, three-edit convention); repo-relative commands from checkout root; preserve unrelated findings and working-tree churn; PATH pytest, hermetic color env | 1 | COVERED |
| CONTEXT | excluded backlog | WR-01/06/07/08/09 and all IN/CR items | 1 | EXCLUDED BY ONE-ITEM CONSTRAINT, not silently omitted: each assessed live at cbf5e44 with skip reasons in the objective; WR-06's live encoding sub-item (bench.py:624) named as the next-task candidate; ledger preservation is gate-verified |

No external API integration is in scope (ledger-only documentation change; no code or service calls) and no core-assumption generalization occurs. Quick mode has no ROADMAP phase section, so the phase-scoped API-coverage and assumption-delta detectors have no phase input and are skipped. No Payload/Prisma/Drizzle/Supabase/TypeORM schema file is touched, so no schema-push task applies.

Final gates, run from the checkout root after the task:
1. The structural staleness gate and reconstruction gate in the task verify block (both already chained there).
2. `python -m pytest tests/unit/indexing/test_incremental.py -q --no-cov`
3. `ruff check src tests`
4. `ruff format --check src tests`
5. `python -m pytest` (full run includes the coverage gate; PATH pytest, not .venv; suite is color-env-hermetic)
6. `git diff --exit-code -- src tests docs` proves zero production, test, and generator-owned-doc changes.
7. Review the scoped diff and the commit: only the Phase 10 disposition ledger carries task edits and only that path is staged; the pre-existing `.planning/` churn (config.json, state.json, agent-history.json, PATTERNS files, research cache, 16-REVIEW iter2 files, tmp) remains uncommitted and unmodified. Planning SUMMARY/STATE artifacts are handled separately by the orchestrator.
</verification>

<success_criteria>
- WR-02's staleness is proven at execution HEAD before any edit: update_cmd delegates to IncrementalIndexer with no whole-run write transaction, per-file BEGIN IMMEDIATE commits are structurally present, and the shipped mid-run-failure durability test passes.
- WR-02 alone becomes fixed (YAML + table), the ledger open count becomes 17 with total still 22, and exact baseline reconstruction proves every other review record remains byte-identical.
- No production source, test, or doc file changes; the commit contains only the ledger; pre-existing working-tree churn is preserved.
- Full ruff, format, and pytest quality suite passes (plain PATH python -m pytest).
</success_criteria>

<output>
Create `.planning/quick/261111-qlv-next-phase-10-item-address-the-smallest-/261111-qlv-SUMMARY.md` with `status: complete` in SUMMARY frontmatter when done. Record the selected finding as Phase 10 WR-02 (evidence-backed triage close, disposition fixed, open 18 → 17), the per-finding selection assessment (WR-02 fully stale via Phase 11 D-04 per-file commits in incremental.py, pinned by test_mid_run_failure_keeps_completed_files_durable; WR-06 primary defect stale but encoding sub-item live at bench.py:624 — left open, recommended next quick item; WR-08 convention-conflicting; WR-01/07/09 broader), the structural-gate output (per-file commit block count), and the reconstruction-gate result. Do not commit planning artifacts or STATE.md; the orchestrator handles the docs/state commit.
</output>
