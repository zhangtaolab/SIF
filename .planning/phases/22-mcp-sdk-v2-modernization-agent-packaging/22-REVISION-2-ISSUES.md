# Phase 22 — Revision Iteration 2 Inputs

**Source:** second independent `gsd-plan-checker` return, 2026-11-16T02:36:54Z (prior session `2fedc7c9-211a-467c-9fde-a96c7663538a`). Recovered verbatim from the session transcript and independently re-verified by the orchestrator against every cited file and test line.

**Context:** revision `3cb6f3b` applied the first checker's findings. The second checker then returned **4 blockers + 7 warnings + 5 info**; iteration 2 has not been applied. The user locked the fix decisions below before this revision run.

---

## Checker issues (YAML, verbatim)

```yaml
issues:
  - plan: "22-01"
    dimension: task_completeness
    severity: blocker
    required_property: >-
      Every plan's declared file scope includes every existing test file its source change breaks.
    description: >-
      Task 2 removes the eager EmbeddingModelFactory/build_identity block from
      SearchBackend.__init__, but tests/unit/mcp/test_backend.py is absent from
      files_modified and both task <files> lists. It patches
      sif.mcp.backend.EmbeddingModelFactory at 12 sites and asserts the eager
      create_model call and _identity assignment in
      test_search_backend_forwards_api_settings_to_factory and
      TestEmbedderIdentityAtStartup.test_factory_receives_the_resolved_prompt_scheme_and_identity_is_stored.
      Removing the import (required for ruff) makes patch() raise AttributeError;
      22-01's full pytest gate and 22-02's Task 3 test_backend gate fail before
      22-04's adaptation.
    task: 2
    fix_hint: >-
      Add tests/unit/mcp/test_backend.py to 22-01 Task 2 and adapt the eager
      factory/identity tests to the lazy skeleton, keeping the schema-open
      settings-identity and legacy-assumed-row assertions.

  - plan: "22-02"
    dimension: task_completeness
    severity: blocker
    required_property: >-
      Every existing test importing a symbol a plan deletes is in that plan's
      scope and adapted before deletion.
    description: >-
      Task 3 deletes the JSON-RPC wire types from src/sif/mcp/protocol.py,
      including InitializeResult (line 110). tests/test_version_identity.py:15
      imports it and line 63 asserts InitializeResult().serverInfo["version"].
      That file is not in 22-02 files_modified or any task <files>, and the
      absence gate only greps server/handlers/transports imports, so it will
      not catch this. The full pytest gate at 22-02 fails at collection.
    task: 3
    fix_hint: >-
      Add tests/test_version_identity.py to 22-02 Task 3 and move the MCP
      serverInfo surface to the SDK MCPServer(name="sif-mcp-server",
      version=__version__) server info.

  - plan: "22-03"
    dimension: task_completeness
    severity: blocker
    required_property: >-
      Every existing test monkeypatching a changed function's call signature is
      in the changing plan's scope.
    description: >-
      Task 2 changes stop_daemon to thread a marker into corroborate_pid.
      tests/unit/utils/test_daemon.py monkeypatches daemon.corroborate_pid with
      one-argument lambdas at lines 347, 375, 396, 409, and 442, while
      stop_daemon calls corroborate_pid(payload) at daemon.py:322. Passing
      marker=... raises TypeError in every TestStopEscalation test. The file is
      not in 22-03 files_modified or task <files>; the full pytest gate fails.
    task: 2
    fix_hint: >-
      Add tests/unit/utils/test_daemon.py to 22-03 Task 2 and update the fakes
      to accept the marker, or call corroborate_pid(payload) on the default
      watch path and pass the marker only for mcp.

  - plan: "22-05"
    dimension: task_completeness
    severity: blocker
    required_property: >-
      Every plan that changes an existing method's observable behavior includes
      the test file asserting the old behavior.
    description: >-
      Task 2 changes SearchBackend.get_document to always populate
      line_start/line_end (full read = 1..N) and maps
      snippet/content_hash/line fields in hybrid_search, get_document, and
      get_documents_by_pattern. tests/unit/mcp/test_backend.py is not in 22-05
      files_modified or any task <files>. test_get_document_no_line_params
      (lines 186-202) asserts line_start is None/line_end is None for a full
      read, directly contradicting the new truth; _weight_result() (line 376)
      leaves the new citation fields as auto-created MagicMocks; and the
      get/multi_get mocks do not configure get_checksum. The full pytest gate
      fails.
    task: 2
    fix_hint: >-
      Add tests/unit/mcp/test_backend.py to 22-05 Task 2, update the full-read
      expectation to 1..N, set citation fields on _weight_result, and
      configure/patch get_checksum in the get/multi_get tests.

  - plan: "22-02"
    dimension: task_completeness
    severity: warning
    required_property: >-
      The disposition (port or delete) of every existing test for a deleted
      implementation is named in the plan.
    description: >-
      test_backend.py is in scope but contains 20 from sif.mcp.handlers imports
      (QueryToolHandler, MetadataToolHandler, create_default_tools) and two
      JsonRpcRequest uses (lines 1438, 1722). The tasks name only lex/vec
      adaptation and "keep test_backend.py green"; they do not name the
      port/delete of the weight/offset/per-chunk/filter handler tests or the
      JSON-RPC protocol-error tests. Deleting them without porting drops the
      only tool-layer assertions for those pass-throughs.
    task: 3
    fix_hint: >-
      Add a Task 3 step porting the still-relevant handler assertions into
      test_tools.py and deleting the wire-protocol-specific ones.

  - plans: ["22-01", "22-03"]
    dimension: task_completeness
    severity: warning
    required_property: >-
      Every test asserting an allowed-host 200 sends a Host the explicit
      allowlist accepts.
    description: >-
      The test_app/test_sdk_clients actions use TestClient/the mounted ASGI app
      without specifying a base URL/Host. The default http://testserver is not
      in the loopback allowlist, so /mcp returns 421; after 22-03's /health Host
      guard it returns 421 there too. tests/unit/mcp/test_app.py is not in
      22-03 files_modified, so its /health 200 assertion can fail without a
      declared adaptation.
    task: 2
    fix_hint: >-
      Specify base_url="http://localhost" or Host: localhost (or
      allowed_hosts=["testserver"]) and add test_app.py to 22-03 if the /health
      assertions need the same change.

  - plan: "22-03"
    dimension: task_completeness
    severity: warning
    required_property: >-
      The generated CLI reference reflects the shipped daemon, not the removed
      stub.
    description: >-
      The daemon docstring is "Daemon mode is not implemented; use 'mcp http'
      instead." (src/sif/cli/commands/mcp.py:129), and make docs-generate copies
      it into docs/cli-reference.md:582-584. The docs gate counts
      --allowed-hosts only; it never asserts the "not implemented" text is
      gone. Replacing the stub can leave the generated reference claiming the
      daemon is unimplemented while the phase ships a real daemon.
    task: 3
    fix_hint: >-
      Replace the docstring/help in Task 2 and add a
      grep -c 'not implemented' docs/cli-reference.md must-be-0 gate in Task 3.

  - plan: "22-07"
    dimension: task_completeness
    severity: warning
    required_property: >-
      The pre-publish --check treats a well-formed 404 (not listed) as
      reachable/pass.
    description: >-
      --check is described as failing on a mismatch/unreachable registry
      lookup, but the pre-publish state is normally a 404 (name+version not yet
      listed). The plan does not state that a 404 is reachable/pass; if the
      executor treats it as a mismatch, the Task 1 --check gate fails before
      the maintainer publish and the --publish preflight blocks.
    task: 1
    fix_hint: >-
      State the 404-pass rule and add a mocked 404 --check test alongside the
      404 --publish test.

  - plans: ["22-01", "22-02", "22-03", "22-05", "22-06"]
    dimension: verification_derivation
    severity: warning
    required_property: >-
      Prohibitions appear only in must_haves.prohibitions, not restated in
      truths.
    description: >-
      The dedicated blocks now exist with statement/status/verification, but
      several truths still restate the same rules: 22-01 truth "no runtime
      dependency beyond mcp is added" duplicates prohibition 6; 22-02 truth "no
      mutation tool exists" duplicates prohibition 3; 22-03 truth "never *"
      duplicates prohibition 1; 22-05 truth "never a hash recomputed from
      truncated content" duplicates prohibition 2; 22-06 truth "no hardcoded
      SIF_DB_PATH" duplicates prohibition 5.
    fix_hint: >-
      Phrase the truths as positive observable states and keep the prohibitions
      block as the sole rule statement.

  - plan: "22-03"
    dimension: verify_command_format_sanity
    severity: warning
    required_property: >-
      Every already-true verify gate names the mutation that turns it red or is
      pinned to a delta.
    description: >-
      grep -rn "load_model" src/sif/cli/commands/mcp.py; test $? -eq 1 already
      passes at HEAD and has no GUARD MUTATION:/baseline notation. It is a
      regression guard, not a delta gate, and it cannot detect a model load
      through SearchBackend construction.
    task: 2
    fix_hint: >-
      Annotate as [HEAD=absent EXPECT==absent GUARD MUTATION: T-22-19] and rely
      on 22-04's lazy-load call-count tests for the real model-free proof.

  - plan: "22-05"
    dimension: verify_command_format_sanity
    severity: warning
    required_property: >-
      Every already-true verify gate names the mutation that turns it red or is
      pinned to a delta.
    description: >-
      test -f src/sif/core/models.py && ! sed -n '/def to_dict/,/^$/p'
      src/sif/core/models.py | grep -q "line_start" already passes at HEAD and
      has no GUARD MUTATION:/baseline notation. It is a guard that should hold
      before and after, not a delta gate.
    task: 3
    fix_hint: >-
      Annotate as [HEAD=absent EXPECT==absent GUARD MUTATION: T-22-...] and/or
      add an explicit test asserting "line_start" not in
      SearchResult(...).to_dict().

  - plan: "22-01"
    dimension: verify_command_format_sanity
    severity: info
    required_property: >-
      Every verify literal matches a name the task action specifies.
    description: >-
      The Task 3 gate requires console_err.print with Migrated|docsift, but the
      action only says "move ... to the stderr console"; src/sif/cli/main.py
      has no console_err today (only console at line 26). A correct stderr
      implementation named err_console would fail the gate.
    task: 3
    fix_hint: >-
      Name the stderr console console_err in the action or broaden the gate.

  - plan: "22-06"
    dimension: task_completeness
    severity: info
    required_property: >-
      Every forbidden-text gate only forbids names the new implementation does
      not use.
    description: >-
      The docs stale-text gate forbids register_tools in docs/mcp-server.md and
      src/sif/mcp/README.md, while the new architecture keeps a
      register_tools(mcp, backend) function that the docs may legitimately
      describe.
    task: 3
    fix_hint: >-
      Forbid only the old assembly tokens, or document the new function under a
      different word.

  - plan: "22-07"
    dimension: verification_derivation
    severity: info
    required_property: >-
      Every prohibition's claimed verification exists as an executable
      assertion.
    description: >-
      The prohibition says Task 3 asserts _version.py is 1.1.2 and no
      tag/release action exists, but Task 3's action/verify only says "Do not
      tag or release v1.2"; no command asserts the version or tags.
    task: 3
    fix_hint: >-
      Add a _version.py 1.1.2 grep and a git tag --list 'v1.2*' absence check.

  - plan: null
    file: "22-RESEARCH.md"
    dimension: research_resolution
    severity: info
    required_property: >-
      RESEARCH.md's Open Questions are formally resolved.
    description: >-
      The section is "## Open Questions" (no (RESOLVED) suffix) and the seven
      questions carry Recommendation: lines but no inline RESOLVED markers.
      Every recommendation is adopted by the plans, so the research is
      substantively resolved; the formal marker is missing.
    fix_hint: >-
      Rename to "## Open Questions (RESOLVED)" and mark each recommendation
      RESOLVED:.

  - plan: "22-01"
    dimension: dependency_correctness
    severity: info
    required_property: >-
      No client loses a working tool during a shell replacement.
    description: >-
      Deletion ordering is now correct (the old shell remains until 22-02's
      seven-tool battery), but 22-01 Task 2 rewires the CLI to the SDK while
      only status is registered, so a client of sif mcp stdio/http loses the
      other six tools until 22-02 lands. This is inherent to D-01's
      tracer-first/no-dual-stack mandate and is bounded to one wave.
    task: 2
    fix_hint: >-
      No change if B1 is read as a deletion-ordering invariant; otherwise defer
      the CLI cutover to 22-02 (which would weaken 22-01's stdio proof).
```

---

## Orchestrator decisions (user-locked, 2026-11-16)

These take precedence over the checker's example `fix_hint` where they differ. They do not contradict any locked CONTEXT.md decision.

1. **Blocker 2 — SDK construction seam + client check.**
   - 22-01 Task 2: add `SERVER_NAME = "sif-mcp-server"` in `src/sif/mcp/app.py`; construct `MCPServer(SERVER_NAME, version=__version__, ...)`. The name/version seam must be importable by a unit test.
   - 22-01 Task 2 tests: in `tests/unit/mcp/test_sdk_clients.py`, assert the initialize result's `serverInfo.version == APP_VERSION` (the goldens normalize `serverInfo.version`, so this client assertion is the wire-level release-identity proof).
   - 22-02 Task 3: add `tests/test_version_identity.py` to the task `<files>` and `files_modified`; replace the `InitializeResult().serverInfo["version"]` assertion with the `app.py` seam + the SDK client wire assertion; preserve the release-identity intent (CLI + PyPI + MCP serverInfo agree on the single-sourced version).

2. **Blocker 3 — signature + update fakes.**
   - Keep `corroborate_pid(payload, *, marker: str = "watch") -> bool` and `stop_daemon(..., *, marker: str = "watch", ...)`.
   - Add `tests/unit/utils/test_daemon.py` to 22-03 Task 2 `<files>` and `files_modified`; update the 5 one-argument lambdas at lines 347/375/396/409/442 to accept the keyword-only marker (e.g. `lambda _payload, *, marker="watch": ...`) or `**_kwargs`; add an assertion that `stop_daemon(marker="mcp")` forwards the marker and the default path is `"watch"`.
   - Note `tests/unit/mcp/test_daemon.py` is a different, new file.

3. **Warning 6 — explicit localhost base_url.**
   - 22-01 Task 2/3 test actions: specify `base_url="http://localhost"` (or an explicit `Host: localhost`) for TestClient/mounted-ASGI requests that assert 200. Do NOT add `testserver` to the production loopback allowlist.
   - Add `tests/unit/mcp/test_app.py` to 22-03 Task 1 `<files>` and `files_modified` so the `/health` 200 assertion is adapted in the same plan that adds the guard.

4. **Advisory 16 — keep the 22-01 CLI cutover.** Add a short note to 22-01's task action/acceptance criteria: the intermediate SDK surface is status-only, is a development-branch state, and no release/PyPI publish may be cut from it; 22-02's seven-tool battery is the gate that closes the gap. Do not defer the cutover.

### Default dispositions for the remaining findings

- **Warning 5:** name the port/delete disposition of every handler-test block in 22-02 Task 3. Port still-relevant weight/offset/per-chunk/filter pass-through assertions into `test_tools.py`; delete JSON-RPC-specific protocol-error tests as replaced by the wire transcripts/SDK client tests.
- **Warning 7:** 22-03 Task 2 must replace the "Daemon mode is not implemented..." docstring/help; 22-03 Task 3 adds a must-be-0 gate for `not implemented` in `docs/cli-reference.md`.
- **Warning 8:** 22-07 Task 1 states that a well-formed registry 404 means "not listed, reachable/pass" for `--check`; 200 means already listed and also passes `--check`; 5xx/network is a FAIL. Add a mocked 404 `--check` test alongside the existing 404 `--publish` test.
- **Warning 9:** rephrase the five cited truths as positive observable states; keep the prohibitions blocks as the sole must-NOT rule statements.
- **Warnings 10/11:** annotate the already-true gates with guard-mutation notation `[HEAD=absent EXPECT==absent GUARD MUTATION: T-22-19]` (22-03) and an appropriate `T-22-xx` for 22-05; for 22-05 also add an explicit unit assertion that `"line_start" not in SearchResult(...).to_dict()`.
- **Info 12:** 22-01 Task 3 names the stderr console `console_err` explicitly in the action (or broadens the gate to accept the actual name) so the verify literal matches.
- **Info 13:** 22-06 Task 3 forbids only the old assembly tokens (e.g. `Not Yet Implemented`, `ToolHandler`, old `handlers.py`/`transports` assembly) and allows the new `register_tools(mcp, backend)` name.
- **Info 14:** 22-07 Task 3 adds executable checks: `_version.py` contains 1.1.2 and `git tag --list 'v1.2*'` is empty.
- **Info 15:** rename the 22-RESEARCH.md section to `## Open Questions (RESOLVED)` and mark each recommendation `RESOLVED:`.
