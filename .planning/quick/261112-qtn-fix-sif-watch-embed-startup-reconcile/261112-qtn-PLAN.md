---
phase: quick-261112-qtn
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - src/sif/indexing/watcher.py
  - src/sif/cli/commands/watch.py
  - tests/unit/cli/test_watch_cmd.py
autonomous: true
must_haves:
  truths:
    - "At embed depth, `sif watch --embed` startup reconcile runs through the watcher's embed-aware reconcile: a document whose content changed while watch was off (vector-less before startup) has chunks plus embeddings after the pre-observer pass"
    - "No document changed by the startup BM25 pass is left vector-less after an embed-depth startup (regression test red at HEAD, green after the fix)"
    - "BM25-only depth is unchanged: the startup pass performs the same IncrementalIndexer.update_collection work under the same per-DB flock, writes zero chunks/vectors, and never constructs the embedding model"
    - "The startup pass still runs BEFORE the observer arms (D-03) and still holds the per-DB flock with the existing another-writer waiting notice"
    - "Daemon and installed-service hosts inherit the fix because they execute run_watch_host verbatim"
  artifacts:
    - src/sif/indexing/watcher.py
    - src/sif/cli/commands/watch.py
    - tests/unit/cli/test_watch_cmd.py
  key_links:
    - "run_watch_host startup loop -> FileWatcher.reconcile_now -> _run_reconcile -> checksum diff (_collection_checksums/_changed_since) -> _EmbedSession.embed_documents inside the SAME lock window"
    - "embed-depth stale doc -> BM25 update branch purges chunks+embeddings -> changed-set checksum diff re-selects the path -> vectors rewritten before the observer arms"
    - "BM25 depth -> _run_reconcile takes before=None -> no diff, no embed call -> identical DB result to the old direct update_collection block"
---

<objective>
Fix `sif watch --embed` startup reconcile. The pre-observer pass in `run_watch_host` currently calls `IncrementalIndexer.update_collection` directly, so at embed depth its BM25 update branch purges the chunks and embeddings of every document that changed while watch was off and never re-embeds them — those documents stay vector-less until a later burst or `sif index embed`. Route the startup pass through the watcher's existing embed-aware reconcile (`FileWatcher._run_reconcile`, the IN-04 shape) via a new public `reconcile_now` seam, and add a regression test proving no embedding-less documents remain after an embed-depth startup.

Purpose: an embed-depth watch must never leave the index in a state where changed documents cannot be found by vector search; the startup pass is the only reconcile that runs before event intake, so it must embed what its BM25 leg changed.

Output: a public `FileWatcher.reconcile_now` (parameterized `_run_reconcile`), `run_watch_host` routing each collection's startup reconcile through it before `watcher.start()`, and two new CLI-level tests (embed-depth regression proof + BM25-depth parity pin).
</objective>

<execution_context>
@~/.claude/gsd-core/workflows/execute-plan.md
@~/.claude/gsd-core/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md
@src/sif/indexing/watcher.py
@src/sif/cli/commands/watch.py
@tests/unit/cli/test_watch_cmd.py
@tests/unit/indexing/test_watcher.py

Planning-time evidence (live-probed at HEAD 1e0eac5 from the checkout root with the PATH `pytest`/`ruff`, both verified working; probe files were deleted and `src/`+`tests/` restored to HEAD before this plan was written):

- Root cause, exact: `run_watch_host` (src/sif/cli/commands/watch.py:164-187) creates `IncrementalIndexer(db.connection)` and runs `update_collection` under `index_lock`. At embed depth that update branch purges chunks and embeddings of changed documents. This is the same class of defect IN-04 fixed for the worker's reconcile job (src/sif/indexing/watcher.py:811-833, `_run_reconcile`) by feeding a checksum diff around the BM25 pass into `_EmbedSession.embed_documents` — but the CLI startup pass never received that fix.
- Existing embed-aware logic to reuse (do NOT duplicate): `_run_reconcile` snapshots `_collection_checksums` before the pass, runs `update_collection`, computes `_changed_since`, and calls `_EmbedSession.embed_documents` in the same `index_lock` window (D-09). `_EmbedSession` is lazy, fail-soft, and already proven by `tests/unit/indexing/test_watcher.py::TestEmbedDepth::test_reconcile_at_embed_depth_rewrites_purged_vectors`.
- HEAD reproduction (probe test, exactly the planned regression shape): BM25-index one doc, rewrite it on disk (stale), run `watch_cmd --embed` with a MagicMock `Observer`, a captured-SIGTERM `time.sleep` stub, and a dim-8 `EmbeddingManager.from_settings` mock -> exit 0, startup prints "Found 1 files", and a fresh factory connection still reports the document WITHOUT chunks/embeddings (`UNEMBEDDED` = one row). Non-vacuous red confirmed.
- Fix reproduction (the exact planned edits applied temporarily): the same probe passes; `tests/unit/cli + tests/unit/indexing` 557 passed; `tests/integration/test_watch_e2e.py` + `test_watch_daemon_e2e.py` 11 passed (real subprocesses); `ruff check`/`ruff format --check` clean. `watch.py` then required removal of the now-unused `index_lock` and `IncrementalIndexer` imports (F401) — accounted for below. The temporary edits were reverted; the executor implements from HEAD.
- Test fixture sources to copy (proven shapes): `tests/unit/cli/test_watch_cmd.py` module helpers `_delenv_settings_vars`, `_test_settings`, `_seed_collections`; `tests/unit/indexing/test_watcher.py::_embed_manager_mock` (dim-8 deterministic vectors, `get_model_info` reports the dim); the signal/time park-loop trick from `tests/unit/cli/test_watch_cmd.py::TestShutdownRoutine::test_graceful_sigterm_exits_zero_and_shares_the_routine`; the observer patch `monkeypatch.setattr(watcher_module, "Observer", MagicMock())`; the fresh-connection vector read via `sif.database.factory.create_connection`.
- Semantics of the reuse: `_run_reconcile` returns an `IncrementalResult` and is already covered for both changed and unchanged passes. At BM25 depth `before` stays None, so no checksum diff and no embed call — the DB outcome is exactly the old direct-`update_collection` behaviour. Out of scope: a full backfill of documents left vector-less by an EARLIER BM25-only period (their checksums are already fresh; that repair belongs to `sif index embed`, the existing catch-up path).
- Generator-owned docs (`docs/cli-reference.md`, `docs/configuration.md`) are never hand-edited; no docs update is needed for this internal behaviour fix.
</context>

<tasks>

<task type="tracer" tdd="true">
  <name>Task 1: Route startup reconcile through the embed-aware FileWatcher seam (RED -> GREEN)</name>
  <files>tests/unit/cli/test_watch_cmd.py, src/sif/indexing/watcher.py, src/sif/cli/commands/watch.py</files>
  <behavior>
    - New embed-depth regression test `test_embed_startup_leaves_no_vectorless_documents`: seed one registered collection with one markdown file; BM25-index it (fresh checksum, zero chunks/vectors); rewrite the file on disk (stale); run `watch_cmd --embed` to completion with the park loop stopped after the first sleep via the captured SIGTERM handler, `sif.indexing.watcher.Observer` a MagicMock, and `EmbeddingManager.from_settings` a dim-8 mock. Assert exit code 0 (result.output as message), the mocked manager's `embed()` was called at least once, documents count is 1, and a fresh factory-connection query returns zero documents without a chunk that has an embedding row. Must be RED at HEAD on that final assertion and GREEN after the production edit.
    - New BM25-depth parity test `test_bm25_startup_writes_no_vectors_and_never_loads_model`: same seed and stale rewrite, invoke `watch_cmd` with no depth flags, and patch `EmbeddingManager.from_settings` with `side_effect=AssertionError(...)` so any model construction fails the test. Assert exit code 0, the document row exists (fresh checksum), and `document_chunks` / `document_embeddings` are both empty. Must PASS at HEAD (preservation pin) and stay green after the production edit.
    - Preservation: `tests/unit/indexing/test_watcher.py::TestEmbedDepth::test_reconcile_at_embed_depth_rewrites_purged_vectors` and the rest of both files stay green; the worker paths (`_run_job` -> `_run_reconcile`, `_run_burst`) keep using `self._config.on_event` when no override is passed.
  </behavior>
  <action>
  Do these steps in order.

  STEP A (RED gate, tests first). Add a new `TestStartupReconcileEmbedDepth` class to tests/unit/cli/test_watch_cmd.py after TestShutdownRoutine, following the module's existing conventions (annotated tests returning None, docstrings, no new third-party imports beyond what the module already imports plus `sif.database.factory.create_connection`, `sif.indexing.incremental.IncrementalIndexer`, and `sif.indexing.watcher` as `watcher_module`; use `SimpleNamespace`, `MagicMock`, `patch`, and `CliRunner` already imported). Add a module-level `_embed_manager_mock(dim: int = 8) -> MagicMock` helper copied from tests/unit/indexing/test_watcher.py: `get_model_info` returns `{"loaded": True, "model_id": "test-model", "embedding_dim": dim}` and `embed.side_effect` returns `MagicMock(embeddings=[[0.1] * dim for _ in texts])`.

  Shared seed for both tests: call `_delenv_settings_vars(monkeypatch)`; set `db_path = tmp_path / "watch.db"`; call `_seed_collections(db_path, "notes")` (creates tmp_path/notes/a.md with BODY and registers the collection); open `Database(db_path)`, resolve the collection via `CollectionRepository(db.connection).get_by_name("notes")`, run `IncrementalIndexer(db.connection).update_collection(coll)` (BM25-only index: fresh checksum, zero chunks/vectors), close the DB; then rewrite tmp_path/notes/a.md with drifted content (for example "# Drifted\n\n" + "Changed paragraph text. " * 40). This is the stale vector-less document the task describes.

  Park-loop mechanics (identical to the proven probe and to `test_graceful_sigterm_exits_zero_and_shares_the_routine`): a `captured: dict[int, object]` dict; `monkeypatch.setattr(watch_mod, "signal", SimpleNamespace(signal=lambda sig, handler: captured.__setitem__(sig, handler), SIGINT=2, SIGTERM=15))`; a `fake_sleep(_seconds)` that asserts `captured[15]` is callable and calls it with `(15, None)`; `monkeypatch.setattr(watch_mod, "time", SimpleNamespace(sleep=fake_sleep))`; and `monkeypatch.setattr(watcher_module, "Observer", MagicMock())`.

  Embed test invocation: inside `with patch("sif.config.settings.get_settings", return_value=_test_settings()), patch("sif.embedding.manager.EmbeddingManager.from_settings", return_value=manager):`, invoke `CliRunner().invoke(watch_mod.watch_cmd, ["--embed"], obj={"index_path": db_path})`. Assert `result.exit_code == 0` with `result.output` as the message. Then open `create_connection(db_path)`, assert `SELECT COUNT(*) FROM documents` equals 1, and assert the following query returns `[]`: `SELECT d.id FROM documents d WHERE NOT EXISTS (SELECT 1 FROM document_chunks c JOIN document_embeddings e ON e.chunk_id = c.id WHERE c.document_id = d.id)`; close the connection in finally. Assert `manager.embed.call_count >= 1`.

  BM25 parity test invocation: same patched get_settings and park-loop setup, but patch `EmbeddingManager.from_settings` with `side_effect=AssertionError("embedding model must not load at BM25 depth")`, invoke `watch_cmd` with an empty argument list, assert exit 0, then assert one document row exists and both `document_chunks` and `document_embeddings` counts are 0 through a fresh factory connection.

  Run the RED gate now: `pytest tests/unit/cli/test_watch_cmd.py -k startup -q --no-cov`. The embed test must FAIL on the no-vectorless-documents assertion; the BM25 parity test must PASS. Record the embed failure output. If the embed test errors instead of failing on the assertion, diagnose the fixture before touching production code (the planning probe proves the fixture shape works at HEAD).

  STEP B (GREEN gate, production). In src/sif/indexing/watcher.py add a public method `reconcile_now(self, collection: Collection, *, progress: Callable[[str], None] | None = None, on_wait: Callable[[], None] | None = None) -> IncrementalResult` that delegates to `_run_reconcile(collection, progress=progress, on_wait=on_wait)`. Its docstring states: runs one full reconcile on the calling thread BEFORE `start()`; the startup hosts reuse the embed-aware reconcile so an embed-depth startup cannot leave the documents its BM25 leg changed vector-less; pre-start only because the worker owns the connection once `start()` runs.

  Extend `_run_reconcile` with the same keyword-only `progress` and `on_wait` parameters. Resolve `cb = progress if progress is not None else self._config.on_event`; pass `on_wait=on_wait` to the existing `index_lock(self._db_path, self._config.lock_timeout)` call; pass `cb` where the method currently passes `self._config.on_event` to `IncrementalIndexer(self._conn).update_collection` and to `self._embed.embed_documents`. Leave the before-snapshot, `_changed_since`, and embed-leg logic otherwise byte-identical. Do not change `_run_burst`, `_run_job`, `_EmbedSession`, `FileWatcher.start`, or `enqueue_reconcile`.

  In src/sif/cli/commands/watch.py, inside `run_watch_host`, move the existing `FileWatcher(...)` construction (same positional args and the same `WatchConfig` fields, including `on_event`, `on_batch`, rescope and checkpoint wiring) to BEFORE the startup loop, and replace the loop body's `IncrementalIndexer(db.connection)` + `with index_lock(...)` + `indexer.update_collection(...)` block with `watcher.reconcile_now(coll, progress=_render_index_event(console, progress, task), on_wait=<the same lambda printing the Another index writer is running notice with lock_timeout>)`. Call `watcher.start()` after the loop as before. Keep the D-03 comment and extend it: the pass still runs before the observer arms, and at embed depth it now re-embeds what its BM25 leg changed. Keep `watcher: FileWatcher | None = None` and the finally block unchanged (`stop(flush=False)` is safe on a watcher that never started). Remove the now-unused `from sif.database.locking import index_lock` and `from sif.indexing.incremental import IncrementalIndexer` imports (ruff F401) and update the module docstring sentence about the startup reconcile to say it is embed-aware at embed depth.

  Do NOT add a backfill of documents whose checksums are already fresh (out of scope, covered by `sif index embed`), do NOT change depth resolution, do NOT touch the MCP watch host (it forces BM25), and do NOT hand-edit `docs/cli-reference.md` or `docs/configuration.md`.

  Run the GREEN gate: `pytest tests/unit/cli/test_watch_cmd.py tests/unit/indexing/test_watcher.py -q`, then `ruff check src tests`, then `ruff format --check src tests`. If ruff format reformats either source file, accept its formatting and re-run the gates.
  </action>
  <verify>
    <automated>pytest tests/unit/cli/test_watch_cmd.py tests/unit/indexing/test_watcher.py -q &amp;&amp; ruff check src tests &amp;&amp; ruff format --check src tests</automated>
  </verify>
  <done>The embed-depth regression test was demonstrably red at HEAD (fails on the no-vectorless-documents assertion) and is green after the production edit; the BM25 parity test is green both before and after and proves no chunk/vector writes and no embedding-model construction at BM25 depth; `reconcile_now` is the only new public API and `_run_reconcile` defaults preserve worker behaviour; `run_watch_host` reconciles each collection through `reconcile_now` before `watcher.start()` with the existing flock-waiting notice; `test_reconcile_at_embed_depth_rewrites_purged_vectors` still passes; `ruff check src tests` and `ruff format --check src tests` are clean; only the three declared files changed.</done>
</task>

<task type="auto">
  <name>Task 2: Full quality gate, real-subprocess watch e2e, and scope conformance</name>
  <files>src/sif/indexing/watcher.py, src/sif/cli/commands/watch.py, tests/unit/cli/test_watch_cmd.py</files>
  <action>
  Verification-only task — make no edits up front. From the checkout root, run in order:
  1. `pytest -q` (full suite with the project's coverage addopts; the fail_under=90 gate is active — expect the whole suite green and the two new tests included).
  2. `pytest tests/integration/test_watch_e2e.py tests/integration/test_watch_daemon_e2e.py -q --no-cov` (real-subprocess proof that the reordered `run_watch_host` still arms, watches, and shuts down; planning-time result with the fix applied: 11 passed).
  3. `ruff check src tests`.
  4. `ruff format --check src tests`.
  5. Scope check: confirm the change set is confined to the three declared files (`files_modified` frontmatter: the two sources and one test file). Use `git status --porcelain -- src tests` or the executor's own commit diff; this is a review step, not a machine gate, so a clean working tree after an internal per-task commit is acceptable — the merge-time scope check reads `files_modified` from this plan.

  If any gate fails, remediate ONLY within the three task-scoped files, then re-run every gate. Never weaken an existing test assertion to force a pass and never broaden scope to other source or test files. If a failure cannot be resolved within the three files, stop and report the exact failing gate and output.
  </action>
  <verify>
    <automated>pytest -q &amp;&amp; pytest tests/integration/test_watch_e2e.py tests/integration/test_watch_daemon_e2e.py -q --no-cov &amp;&amp; ruff check src tests &amp;&amp; ruff format --check src tests</automated>
  </verify>
  <done>Full pytest exits 0 with coverage >= 90%; the real-subprocess watch and watch-daemon e2e batteries pass unchanged; ruff check and ruff format --check are clean across src and tests; the change set is confined to the three declared files.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| Watched filesystem roots -> startup indexer/embedder | Local file content is untrusted input processed by the shared parser/indexer and (at embed depth) the embedding backend; the startup pass runs before the observer arms but on the same connection and lock as the worker |
| Index database -> vector/chunk tables | The startup BM25 pass purges and rewrites chunks/vectors; a wrong changed-set computation could leave or delete inconsistent rows |

No network service, authentication flow, or package-manager install is introduced. Depth remains user-opted-in (`--embed` or `SIF_WATCH_UPDATE_DEPTH=embed`); the default and `--no-embed` never construct the embedding model.

## STRIDE Threat Register

| Threat ID | Category | Component | Severity | Disposition | Mitigation Plan |
|-----------|----------|-----------|----------|-------------|-----------------|
| T-qtn-01 | Tampering | startup reconcile (src/sif/cli/commands/watch.py, src/sif/indexing/watcher.py) | low | mitigate | Reuse the existing `_run_reconcile` path (no new parsing or SQL surface); the pass still holds the per-DB `index_lock`; the embed leg stays inside `_EmbedSession`'s existing per-path try/except fail-soft contract; the new public method only forwards two optional callbacks and takes no user-controlled SQL or path input |
| T-qtn-02 | Information disclosure / unexpected cost | embed-depth startup model load | low | mitigate | The embedding model loads only when depth is explicitly embed (flag or setting); the BM25 parity test patches `EmbeddingManager.from_settings` with a failing side effect to prove no model construction at BM25 depth; first-use failures remain fail-soft (one error event, embedding disabled for the session, BM25 freshness continues) |
| T-qtn-SC | Tampering | package installs | low | accept | No package-manager install, dependency, or lockfile task exists; the package legitimacy gate is not applicable |
</threat_model>

<verification>
Source coverage audit (quick-batch item: no ROADMAP phase requirement IDs, no RESEARCH artifact, no CONTEXT.md D-XX decisions — the item description and the caller's constraints are the source artifacts):

| SOURCE | ID | Item | Task | Status |
|--------|----|------|------|--------|
| GOAL | 261112-qtn | Route `sif watch --embed` startup reconcile through the embed-aware reconcile path so changed documents are not left vector-less | 1 | COVERED |
| GOAL | 261112-qtn | Add a regression test proving no embedding-less documents remain after startup | 1 | COVERED |
| CONTEXT | constraint | Reuse the existing embed-aware reconcile logic rather than duplicating it | 1 | COVERED (`reconcile_now` delegates to `_run_reconcile`) |
| CONTEXT | constraint | Keep BM25-only depth unchanged | 1 (parity test), 2 (gates) | COVERED |
| CONTEXT | constraint | Regression test seeds a stale vector-less document at embed depth, runs the startup path, asserts every document has embeddings | 1 | COVERED |
| CONTEXT | constraint | Single plan, 1-3 tasks; emit depends_on and files_modified | 1-2 | COVERED |

Planning-time non-vacuity baselines (recorded so the gates are not self-invalidating):
- The new embed-depth regression assertion FAILS at HEAD 1e0eac5 (probe: exit 0, startup output shows the BM25-only pass, the one document remains unchunked/unembedded). It is a defect gate.
- The BM25 parity test PASSES at HEAD and after the fix — it is a preservation pin.
- The full suite and both real-subprocess watch e2e batteries pass at HEAD and passed with the planned fix applied during the planning probe; they are preservation gates.
- The fix was probed by temporarily applying the exact planned edits, then reverting them; `git status --porcelain -- src tests` is empty before the executor starts.

Final gates (Task 2 runs all of them): full `pytest -q` (coverage gate), the two watch e2e batteries, `ruff check src tests`, `ruff format --check src tests`, and the three-file scope check.
</verification>

<success_criteria>
- An embed-depth `sif watch --embed` startup embeds every document its pre-observer BM25 pass changed; the regression test proves a fresh connection sees zero documents without an embedding afterwards, and it was red at HEAD.
- BM25-only depth is byte-behaviour unchanged: same `IncrementalIndexer.update_collection` work under the same flock, zero chunks/vectors, no embedding-model construction (pinned by the parity test).
- The startup reconcile still precedes `watcher.start()` (D-03) and the daemon/installed-service hosts inherit the fix through `run_watch_host`.
- Full pytest exits 0 with coverage >= 90%; both real-subprocess watch e2e batteries pass; ruff check and format are clean; only the three declared files changed.
</success_criteria>

<output>
Create `.planning/quick/261112-qtn-fix-sif-watch-embed-startup-reconcile/261112-qtn-SUMMARY.md` with `status: complete` in SUMMARY frontmatter when done. Record: the RED-to-GREEN evidence for the embed-depth regression test, the BM25 parity result, the full-suite and watch-e2e results, and confirmation that `reconcile_now` delegates to the existing `_run_reconcile` (no duplicated embed logic) and that no generator-owned docs were touched.
</output>
