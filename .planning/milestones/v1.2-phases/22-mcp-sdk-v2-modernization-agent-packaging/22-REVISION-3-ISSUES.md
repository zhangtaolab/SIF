# Phase 22 — Revision Iteration 3 Inputs

**Source:** third independent `gsd-plan-checker` return, after revision `471ef36`. Verdict: **1 blocker + 5 warnings + 7 info**. All four prior blockers, five of seven prior warnings, and all five prior infos were re-verified RESOLVED; prior W9 is PARTIALLY RESOLVED with residual truths.

**Prior applied decisions (must be preserved):** B2 = `app.py` `SERVER_NAME` seam + SDK-client wire assertion; W6 = explicit `base_url="http://localhost"`; B3 = keyword-only `marker` signature + updated fakes; Advisory 16 = keep the 22-01 CLI cutover with the status-only development-branch note. These are already in `471ef36` and must not be reverted.

---

## Checker issues (YAML, verbatim)

```yaml
issues:
  - plan: "22-01"
    dimension: task_completeness
    severity: blocker
    required_property: >-
      Every existing test that drives the rewired `sif mcp stdio` host end-to-end is inside a
      plan's declared file scope and adapted to the SDK handshake and staged tool surface before
      that plan's full-suite gate.
    description: >-
      tests/integration/test_mcp_watch_e2e.py (git-tracked; collected by pytest via
      testpaths=["tests"] and CI's full `pytest`) spawns `sif mcp stdio`, sends `initialize` with
      `params: {}` and asserts result.protocolVersion == "2024-11-05" (lines 214-220, 382-389),
      then calls the `query` tool with `lex:` queries (lines 223-235, 297+). It appears in no
      plan's files_modified or task <files>. Live probe against mcp==2.3.0 on Python 3.10 (ASGI
      and real stdio subprocess): empty-params initialize returns JSON-RPC -32602; with only
      `status` registered, `query` returns an isError text "Unknown tool: query" that is not
      JSON, so _query's json.loads(content[0]["text"]) raises. 22-01's CLI cutover makes this
      file fail the full pytest gate; 22-02 cannot restore it until query exists. No plan owns
      the adaptation.
    task: 2
    fix_hint: >-
      Add tests/integration/test_mcp_watch_e2e.py to 22-01/22-02 scope; send a full 2024-11-05
      initialize params; bridge or xfail the query-based assertions until 22-02 registers the
      seven tools, then keep the watch-refresh proof green.

  - plan: "22-04"
    dimension: task_completeness
    severity: warning
    required_property: >-
      A `query` whose prefix routes to BM25 neither forces an embedder load nor loses its prefix
      semantics on the degraded path.
    description: >-
      22-04 Task 1 routes every SearchBackend.hybrid_search through _ensure_embedder() and, when
      it returns None, reuses the existing BM25 fallback, which calls
      BM25Searcher(conn).search(query, options) with the raw query (backend.py:274).
      BM25Searcher._build_fts_query ANDs every whitespace token (bm25.py:237-249), so
      "lex: seed paragraph" requires the "lex" token; today the embedder-None path constructs
      SearchPipeline and _parse_query_prefix strips the prefix (hybrid.py:342, 517-532). The
      integration e2e's lex: queries would return no results after 22-04, and any client using
      lex:/vec: prefixes on a load-failure host regresses. 22-04's lazy tests cover the separate
      lex_search tool, not a lex:-prefixed query.
    task: 1
    fix_hint: >-
      Parse the prefix (or use the embedder-None pipeline route) before deciding to load; add a
      no-load lex:-query test.

  - plan: "22-01"
    dimension: verification_derivation
    severity: warning
    required_property: >-
      The SDK-client matrix exercises both connect modes over stdio, as D-04 and the plan's own
      truth state.
    description: >-
      22-01 must_haves truth 7 says legacy and auto modes list tools/call status "over
      in-process, ASGI HTTP, and a real stdio subprocess"; Task 2's action only spawns the real
      stdio subprocess "for one legacy call" and runs auto only over in-process/ASGI. D-04
      explicitly requires mode legacy and mode auto over in-process, ASGI HTTP, and stdio.
    task: 2
    fix_hint: >-
      Add one auto-mode stdio client call, or narrow the truth to the exercised matrix.

  - plan: "22-06"
    dimension: context_compliance
    severity: warning
    required_property: >-
      The marketplace manifest carries a non-empty top-level `description`, so the C4
      marketplace-description warning is absent.
    description: >-
      Task 1 places the description inside the plugin entry (plugins[0].description) and the test
      checks that entry. Live `claude plugin validate --json` (2.1.325) on exactly that shape
      returns success:true/zero errors but a warning at path `description`: "No marketplace
      description provided..."; adding a top-level description removes it. PATTERNS and C4
      require the marketplace description.
    task: 1
    fix_hint: >-
      Add a top-level description to .claude-plugin/marketplace.json (keep the plugin-entry
      description) and assert it.

  - plan: "22-04"
    dimension: task_completeness
    severity: warning
    required_property: >-
      Existing tests that inject `_embedder`/`_identity` are adapted to the lazy path so they
      neither trigger a real model download nor bypass the patched pipeline.
    description: >-
      TestHybridSearchIdentity (test_backend.py:1878+) sets backend._embedder/_identity after
      _suggestion_backend, which builds from real Settings (model_name="test", default
      model_type="modelscope", cache_embeddings=False; lines 600-645). 22-04's hybrid_search
      calls _ensure_embedder(); the lazy ModelScopeEmbedder downloads the model
      (embedder.py:490-523), and with the MagicMock-settings fixtures from_settings raises
      ValueError (live-checked), sending the test down the BM25 fallback instead of the patched
      SearchPipeline. The Task 1 gate `-k "query or vec or load"` excludes these tests; the action
      only says "Adapt test_backend.py expectations".
    task: 1
    fix_hint: >-
      Patch _ensure_embedder (or seed its lazy state) in those tests and run the whole
      test_backend.py file.

  - plans: ["22-05", "22-07"]
    dimension: verification_derivation
    severity: warning
    required_property: >-
      Prohibitions appear only in must_haves.prohibitions, not restated in truths.
    description: >-
      Prior Warning 9's five cited truths are rephrased, but residual must-NOT statements remain
      in truths: 22-05 truth 2 ("no extra document scan and no new chunk column are added",
      duplicating prohibition 4); 22-05 truth 10 ("no wrapper key and no null fields when
      unfiltered", duplicating prohibition 3); 22-07 truth 7 ("does not cut a v1.2 release or
      change src/sif/_version.py", a verbatim duplicate of prohibition 3).
    fix_hint: >-
      Keep the prohibitions blocks as the sole rule statements; phrase these truths as observable
      outcomes.

  - plan: "22-01"
    dimension: verification_derivation
    severity: info
    required_property: >-
      Every prohibition's claimed verification exists as an executable assertion.
    description: >-
      Prohibition 6 claims "the Task 3 gate asserts no other pyproject runtime entry", but Task
      3's verify block has only two pytest commands and the console_err grep; prohibition 3
      claims "Task 3 asserts app.py contains no version allowlist", but no such gate exists.
    task: 3
    fix_hint: >-
      Add the two source assertions to the Task 3 verify block (or drop the claimed gates).

  - plan: "22-04"
    dimension: task_completeness
    severity: info
    required_property: >-
      D-16 quiet ordering is planned at every entrypoint it names.
    description: >-
      22-04's truth says set_quiet runs before any backend/model import at stdio, HTTP, and
      daemon entrypoints; Task 3 only adds it at run_stdio/run_http. 22-03's daemon arm callback
      constructs SearchBackend before run_http is called (PATTERNS Shared Pattern 1 applies the
      quiet step to the daemon arm callback). Mitigation: SearchBackend construction is
      model-free after 22-01.
    task: 3
    fix_hint: >-
      Call set_quiet(True) at the top of the daemon command/arm path (or record why the
      model-free arm makes the ordering moot).

  - plan: "22-06"
    dimension: task_completeness
    severity: info
    required_property: >-
      The stale-assembly gate forbids every deleted import the docs may retain.
    description: >-
      The Task 3 gate regex covers `Not Yet Implemented|ToolHandler|HTTPTransport|
      create_default_tools|from sif.mcp.handlers|from sif.mcp.transports`, but
      docs/mcp-server.md:310 currently contains `from sif.mcp.server import MCPServer`; the
      action's token list omits `sif.mcp.server` too, so a partial rewrite passes.
    task: 3
    fix_hint: >-
      Add `from sif.mcp.server` to the forbidden-token gate and the rewrite checklist.

  - plan: null
    dimension: task_completeness
    severity: info
    required_property: >-
      Hand-written architecture/reference docs no longer describe modules the phase deletes.
    description: >-
      docs/architecture.md:44,769 and docs/api-reference.md:662,687-688 still describe/import
      sif/mcp/server.py, handlers.py, and transports/. No plan's files_modified includes either
      file, and D-25's documentation list omits them. No test currently asserts these tokens, so
      the gates stay green.
    fix_hint: >-
      Add the two docs to a docs sweep (or record them as deferred) after the shell deletion.

  - plan: "22-01"
    dimension: task_completeness
    severity: info
    required_property: >-
      Tests that spawn the real CLI isolate database/home state.
    description: >-
      Task 2's SDK-client action spawns `python -m sif.cli.main mcp stdio` without specifying a
      temp SIF_DB_PATH/HOME (unlike Task 3's stdout-purity action, which explicitly sets both),
      so the subprocess resolves the developer's platform DB.
    task: 2
    fix_hint: >-
      Pass a tmp_path `--index` or SIF_DB_PATH plus a temp HOME in the subprocess env.

  - plan: "22-01"
    dimension: scope_sanity
    severity: info
    required_property: >-
      Each plan stays within the project's calibrated context budget.
    description: >-
      files_modified counts are 23 (22-01) and 15 (22-02), above the generic 15-file
      blocker/10-file warning table, but task counts are 3 and the calibrated estimate check
      reports 100000/100000 and 92000/100000 (over_budget:false; all seven plans within the
      100000 budget). confidence is low for every plan (sample_count 0, calibration not applied).
    fix_hint: >-
      Accept with the low-confidence note, or split the tracer's golden/test creation into a
      follow-up slice if execution shows context pressure.

  - plan: "22-03"
    dimension: task_completeness
    severity: info
    required_property: >-
      New raw-wire tests send a spec-valid initialize handshake.
    description: >-
      Task 3 says "POST an `initialize` request to `/mcp`" without specifying params; the live
      mcp==2.3.0 probe shows an empty-params initialize is rejected with -32602. The existing
      integration e2e's failure demonstrates the cost of an incomplete handshake.
    task: 3
    fix_hint: >-
      Reuse 22-01's golden 2024-11-05 initialize shape (and pre-reserve an ephemeral port) in the
      daemon e2e.
```

---

## Orchestrator dispositions for iteration 3

Apply the blocker + all warnings + the info fixes below. Preserve the prior applied decisions and all unflagged content.

### Blocker — integration e2e staging
- Add `tests/integration/test_mcp_watch_e2e.py` to **22-01 Task 2** `<files>` and `files_modified`.
  - In 22-01, update `_initialize` (and the inline handshake at ~382) to send the full 2024-11-05 initialize params — `protocolVersion`, `capabilities`, `clientInfo` — matching 22-01's golden 2024-era shape. The empty-params form is rejected by the SDK (-32602).
  - Bridge the `query`-dependent assertions for the status-only 22-01 surface: mark those tests skipped/xfail with an explicit reason naming 22-02's seven-tool battery and the staged surface. The watch-refresh proof must remain owned and green at phase exit.
  - Keep 22-01's full pytest gate green with the bridge in place.
- Add the same file to **22-02 Task 3** `<files>` and `files_modified`. In 22-02 Task 3, remove the bridge/skip and restore the full watch-refresh/`query` proof after the seven tools are registered and the seven-tool battery is green. The `lex:` queries must work on the final surface.
- State in 22-02 Task 3 that the restored e2e is part of the seven-tool battery evidence.

### Warnings
- **22-04 W2 (prefix semantics on the degraded path):** In 22-04 Task 1, parse the `lex:`/`vec:` prefix before deciding to load. A `lex:`-prefixed `query` must route to BM25 without calling `_ensure_embedder()` (never load a model), and must strip the prefix so `BM25Searcher` sees the intended terms. A `vec:` prefix on a load-failure host keeps the documented failure behavior. Add a no-load `lex:`-query test (assert the loader is not called and the BM25 result is returned) and an e2e assertion using the existing `lex:` queries.
- **22-01 W3 (SDK-client matrix):** Add one `mode="auto"` stdio client call alongside the legacy stdio call in 22-01 Task 2, so the matrix exercises both modes over in-process, ASGI HTTP, and real stdio (D-04). If the SDK cannot drive auto over stdio, narrow the truth explicitly and record the SDK limitation — prefer adding the call.
- **22-06 W4 (marketplace description):** Add a non-empty top-level `description` to `.claude-plugin/marketplace.json` (keep the plugin-entry description), assert it in `test_plugin.py`, and keep `claude plugin validate --json .` zero-error/zero-warning for this path.
- **22-04 W5 (identity tests):** In 22-04 Task 1, adapt `TestHybridSearchIdentity` in `tests/unit/mcp/test_backend.py` to patch `_ensure_embedder` (or seed the lazy state) so it neither triggers a real ModelScope download nor bypasses the patched `SearchPipeline`. Run the whole `test_backend.py` file at the task gate (not `-k "query or vec or load"`).
- **22-05/22-07 W6 (residual truths):** Rephrase 22-05 truth 2 ("no extra document scan and no new chunk column") and truth 10 ("no wrapper key and no null fields") as positive observable outcomes; rephrase 22-07 truth 7 ("does not cut a v1.2 release or change `_version.py`") as a positive state (e.g., "the listed version remains the already-published 1.1.2 and the release surface is unchanged"). Keep the prohibitions blocks as the sole must-NOT rule statements.

### Infos
- **22-01 I1:** Add the two claimed source assertions to 22-01 Task 3's verify block: (a) no runtime dependency beyond `mcp` in `pyproject.toml` (e.g., a structural count/assertion over `[project].dependencies`), and (b) no version allowlist in `app.py` (a grep gate for version literals/allowlist tokens). Alternatively, drop the prohibition claims; prefer adding the gates.
- **22-04/22-03 I2:** Call `set_quiet(True)` at the top of the 22-03 daemon command/arm path before `SearchBackend` construction, or state why the model-free construction makes the ordering moot. Align 22-04's truth with the actual entrypoints.
- **22-06 I3:** Add `from sif.mcp.server` to the stale-assembly forbidden-token gate and the rewrite checklist (the file currently has `from sif.mcp.server import MCPServer` at `docs/mcp-server.md:310`).
- **I4 (docs sweep):** Add `docs/architecture.md` and `docs/api-reference.md` to 22-06 Task 3's `<files>` and `files_modified`, and to the rewrite/checklist: remove/replace the `sif/mcp/server.py`, `handlers.py`, and `transports/` descriptions/imports (`docs/architecture.md:44,769`; `docs/api-reference.md:662,687-688`). Add a grep gate for those tokens over both docs. Do not hand-edit `docs/cli-reference.md` or `docs/configuration.md` (generator-owned).
- **22-01 I5:** In 22-01 Task 2's real-subprocess test, pass a temp `SIF_DB_PATH` (or `--index`) and a temp `HOME` in the subprocess env, mirroring Task 3's stdout-purity isolation.
- **22-01 I6:** Accept the scope_sanity advisory: do not split the plans. Record the low-confidence/estimate note in the revision summary.
- **22-03 I7:** In 22-03 Task 3's daemon e2e, send the spec-valid 2024-11-05 initialize params from 22-01's golden and pre-reserve an ephemeral port rather than assuming an empty handshake.

### Preserve
- The four prior user-locked decisions (B2, W6, B3, Advisory 16) and the resolved prior findings.
- Waves, dependencies, threat models, estimates, requirement coverage, and all unflagged content.
- `22-04` stays otherwise unchanged.
- Plan artifacts in English; do not edit source under `src/` in this revision.
