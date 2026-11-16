---
phase: 22-mcp-sdk-v2-modernization-agent-packaging
reviewed: 2026-11-16T09:57:40Z
depth: standard
files_reviewed: 55
files_reviewed_list:
  - .claude-plugin/marketplace.json
  - .claude-plugin/plugin.json
  - .mcp.json
  - docs/api-reference.md
  - docs/architecture.md
  - docs/cli-reference.md
  - docs/mcp-server.md
  - pyproject.toml
  - README.md
  - scripts/publish_registry.py
  - server.json
  - skills/sif-cite/SKILL.md
  - skills/sif-get/SKILL.md
  - skills/sif-search/SKILL.md
  - src/sif/cli/commands/mcp.py
  - src/sif/cli/main.py
  - src/sif/core/models.py
  - src/sif/database/repositories.py
  - src/sif/mcp/__init__.py
  - src/sif/mcp/app.py
  - src/sif/mcp/backend.py
  - src/sif/mcp/cli.py
  - src/sif/mcp/protocol.py
  - src/sif/mcp/README.md
  - src/sif/mcp/tools.py
  - src/sif/mcp/watch_host.py
  - src/sif/search/hybrid.py
  - src/sif/search/snippets.py
  - src/sif/utils/daemon.py
  - tests/integration/test_mcp_watch_e2e.py
  - tests/test_version_identity.py
  - tests/unit/cli/test_mcp.py
  - tests/unit/mcp/_stdio_fixture_server.py
  - tests/unit/mcp/goldens/2024-11-05.json
  - tests/unit/mcp/goldens/2025-03-26.json
  - tests/unit/mcp/goldens/2025-06-18.json
  - tests/unit/mcp/goldens/2025-11-25.json
  - tests/unit/mcp/goldens/2026-07-28.json
  - tests/unit/mcp/test_app.py
  - tests/unit/mcp/test_backend.py
  - tests/unit/mcp/test_citations.py
  - tests/unit/mcp/test_daemon.py
  - tests/unit/mcp/test_lazy_embedder.py
  - tests/unit/mcp/test_mcp_watch_host.py
  - tests/unit/mcp/test_packaging.py
  - tests/unit/mcp/test_plugin.py
  - tests/unit/mcp/test_registry_script.py
  - tests/unit/mcp/test_sdk_clients.py
  - tests/unit/mcp/test_stdout_purity.py
  - tests/unit/mcp/test_tools.py
  - tests/unit/mcp/test_transport_security.py
  - tests/unit/mcp/test_wire_transcripts.py
  - tests/unit/search/test_hybrid.py
  - tests/unit/search/test_snippets.py
  - tests/unit/utils/test_daemon.py
findings:
  critical: 2
  warning: 11
  info: 8
  total: 21
  necessity: 1
status: issues_found
---

# Phase 22: Code Review Report

**Reviewed:** 2026-11-16T09:57:40Z
**Depth:** standard
**Files Reviewed:** 55
**Status:** issues_found

## Summary

Reviewed the Phase 22 MCP SDK v2 modernization and agent packaging: the composition root (`app.py`), the seven-tool surface (`tools.py`), `SearchBackend` (lazy embedder, prefix routing, citations), the 3.0 daemon, the watch host, the snippet extractor, the Claude Code plugin/skills, the Registry manifest/publish script, and the accompanying tests/goldens/docs. `uv.lock` was excluded as a lockfile per review policy; the five golden transcripts were reviewed structurally (parsed and compared against the generated responses) rather than line-by-line.

All targeted unit tests (`test_app`, `test_transport_security`, `test_lazy_embedder`, `test_tools`, `test_backend`, `test_citations`, snippet/hybrid tests, daemon/plugin/packaging/registry/wire/stdout/sdk-client tests) pass, and `ruff`/`ruff format --check`/`ty` are clean on the changed sources. Passing tests are not treated as correctness evidence: the two BLOCKER findings and several warnings below are on paths the suite does not assert (concurrent first-load outcomes, event-loop responsiveness during `vec_search`, trailing-newline snippet windows, past-EOF `get`, non-finite metadata, partial transport-security overrides). The blocked live Registry publish was treated as the plan-permitted outcome described in the task context, not as a defect.

Necessity assessment (standard depth, per `necessity-review.md`): one necessity finding (WR-04, impossible-state guard). No `<structural_findings>` block was provided.

## Narrative Findings (AI reviewer)

### Critical Issues

#### CR-01: Lazy embedder fast path treats "load in progress" as "load failed", silently degrading concurrent first queries

**File:** `src/sif/mcp/backend.py:306-312`
**Issue:** `_ensure_embedder` reads `self._load_attempted` on an unlocked fast path and returns `None if self._load_failed else self._manager`. The loading thread sets `_load_attempted = True` under the lock *before* `manager.load_model()`/`get_identity()` complete and before `self._manager` is assigned. A second thread/request arriving during that window therefore sees `_load_attempted=True`, `_load_failed=False`, `_manager=None` and returns `None`, which `hybrid_search` (line 471) treats as a latched failure and answers with BM25-only results, and `vec_search` (line 614) turns into a misleading "Vector search requires an embedding model" error even though the model is loading successfully.

Reproduced with two threads and a 0.5 s load hook: one caller returned the manager at t=0.5 s, the other returned `None` at t=0.0 s. MCP tool calls are served concurrently and the first vector query commonly loads/downloads a model for seconds to minutes, so this is a reachable result-quality bug. The existing concurrency test (`tests/unit/mcp/test_lazy_embedder.py:214-234`) passes because it asserts only `from_settings.call_count == 1` and `load_calls == 1`, never the callers' return values.
**Fix:** Track completion separately from attempt, or hold the lock for waiters:
```python
def _ensure_embedder(self) -> EmbeddingManager | None:
    with self._load_lock:                      # waiters block until the load settles
        if self._load_attempted:
            return None if self._load_failed else self._manager
        self._load_attempted = True
        # ... load, assign _manager/_identity/_dimension ...
    return None if self._load_failed else self._manager
```
and extend the concurrency test to assert both callers received the same non-`None` manager.

#### CR-02: `vec_search` performs the synchronous lazy model load on the MCP event loop, freezing the whole server

**File:** `src/sif/mcp/backend.py:614`
**Issue:** `async def vec_search(...)` calls `self._ensure_embedder()` directly in the coroutine, i.e. on the event-loop thread, before dispatching to `_run_in_db`. `hybrid_search` correctly performs the same call inside `_search`, which runs via `asyncio.to_thread` (line 471). The SDK executes async tool functions on the loop (`mcp/server/mcpserver/utilities/func_metadata.py::call_fn` awaits them directly), so a cold `vec_search` blocks every other MCP request, all other sessions, and `/health` for the duration of `EmbeddingManager.from_settings` + `load_model()` (model import/download). Measured with a 1 s stubbed load: a concurrent `status` call returned only after the load finished (1.02 s vs 1.01 s). With a real first-run download this is minutes of apparent server hang and client timeouts.
**Fix:** Move the load off the loop, e.g.:
```python
manager = await asyncio.to_thread(self._ensure_embedder)
if manager is None:
    raise RuntimeError(VECTOR_SEARCH_REMEDY)
```
(or call `_ensure_embedder` from inside the `_search` thread callback, as `hybrid_search` does) and add a responsiveness test with two concurrent tool calls, one of which triggers the load.

### Warnings

#### WR-01: Fallback snippet line windows count phantom trailing lines

**File:** `src/sif/search/snippets.py:240-245`
**Issue:** The fallback path returns `(snippet, idx + 1, len(lines))` when the joined text fits `max_length`, and `idx + rendered_lines + 1` when truncated. `len(lines)`/`joined[:max_length].count("\n")` count the empty element after a trailing newline (and trailing blank lines), while `_truncate()` calls `.strip()` and does not render them. The published `SearchResult.line_start/line_end` therefore exceed the document's real line count. Verified: text `"alpha\nbeta\n"` yields `(1, 3)` while `_full_line_range` (used by `get`) says `(1, 2)`; `"# Note\n\ncontent\n"` yields `(1, 4)` vs `(1, 3)`. This path is common for semantic (vector) matches whose document has no lexical query term, i.e. exactly the hybrid/vector results Phase 22 advertises citation fields for. A truncated cut landing exactly on a newline is also off by one because `strip()` removes that newline. The protocol docstring claims the range is "the inclusive 1-based window the snippet rendered" (`src/sif/mcp/protocol.py:22-30`).
**Fix:** Derive the reported end from the rendered snippet rather than the raw split, e.g. drop trailing empty lines from the fallback window (consistent with `_full_line_range`'s "trailing newline is not a line") and compute the end from the newline count of the stripped rendered text; add fixtures with trailing newlines/blank lines to `TestExtractWithRange`.

#### WR-02: `get` fabricates a line for past-EOF ranges and reports ranges its truncated content does not cover

**File:** `src/sif/mcp/backend.py:729-739`
**Issue:** For `from_line` past the end of the document, `lines[start:end]` is empty but the code still reports `line_start = start + 1` and `line_end = start + len("".split("\n")) = start + 1`, so `get` returns `content=""` with `line_start == line_end == 10` for a 3-line document (verified). `max_lines` beyond EOF is clamped (`from_line=2, max_lines=99` reports `2..3`), contradicting the documented "exactly the requested range" (`backend.py:726-728`, `docs/mcp-server.md:155-157`, `skills/sif-get/SKILL.md:41-48`). Additionally, `_truncate_content` at line 739 can cut the returned content while `line_start`/`line_end` still claim the untruncated range, so a caller can cite lines absent from the payload.
**Fix:** Clamp the window to the document and return an explicit empty/`None` range (or a correctable `ToolError`) when `start >= document line count`; compute `line_end` from the post-truncation rendered content, or add a `truncated` flag to `Document`. Align the docs/skill wording with the clamped behavior.

#### WR-03: Non-finite document metadata diverges between the text and structured channels

**File:** `src/sif/mcp/tools.py:97-102`
**Issue:** The text channel uses `json_dumps_strict`, which stringifies non-finite floats ("nan"/"inf"), but the structured channel uses `output.model_dump(mode="json")` with no `json_safe`, and pydantic/serialization renders NaN/Infinity as `null`. Verified: `GetOutput(document=Document(..., metadata={"score": nan, "inf": inf}))` yields text `{"score": "nan", "inf": "inf"}` and structured `{"score": None, "inf": None}`. This violates the documented/tested "text parses to exactly structuredContent" invariant. The repository reads `documents.metadata` back with plain `json.loads` (`src/sif/database/repositories.py:385`), which accepts the NaN/Infinity literals; `json_output.py:11-27` explicitly exists because legacy metadata blobs can carry non-finite floats.
**Fix:** Apply the same normalization to the structured payload:
```python
from sif.utils.json_output import json_dumps_strict, json_safe
structured = json_safe(output.model_dump(mode="json", by_alias=True, exclude_none=exclude_none))
```
or derive it as `json.loads(text)` so the two channels cannot drift.

#### WR-04: Impossible-state guard — reranker `ImportError` soft-degrade can never fire

**File:** `src/sif/mcp/backend.py:363-370`
**Category:** necessity
**Issue:** `_reranker_for` catches `ImportError` from `create_reranker` and promises a one-time "install the optional reranker backend" remedy. `create_reranker` (`src/sif/search/rerank.py:430-469`) only constructs lightweight reranker objects; their constructors store fields and import nothing (`LlamaCppReranker.__init__` line 113, `CrossEncoderReranker.__init__` line 199, `Qwen3Reranker.__init__` line 289). Optional imports happen later inside `load()` (rerank.py:138, 221, 317), called from `rerank()` during `pipeline.search`, and that failure is wrapped as `RuntimeError("Reranking failed: ...")` by `src/sif/search/hybrid.py:469-477`, then handled by the execution fallback at backend.py:510-520. So for a real `Settings` the guarded state cannot occur: a missing `llama-cpp-python` produces the generic execution warning, never the promised install remedy. The branch is reached only by the mock in `tests/unit/mcp/test_backend.py:2076-2111`, which makes `create_reranker` raise directly. (`ValueError` is a separate deliberate defense-in-depth case and is not part of this finding.)
**Fix:** Remove the `except ImportError` branch (or move its remedy text into the execution-failure handler) and correct the D-17 docstring/claim; if a future backend imports at construction, re-add the guard with a test that exercises the real factory.

#### WR-05: Partial transport-security overrides drop the recorded allowlist and can silently widen origins

**File:** `src/sif/mcp/app.py:144-154` (used at line 220)
**Issue:** `_resolve_transport_security` reuses the settings recorded by `build_server` only when *both* overrides are `None`; otherwise it rebuilds from the provided arguments alone. Verified: `build_server(db, allowed_hosts=["sif.local"], cors_origins=["https://sif.local"])` followed by `create_http_app(db, server=server, cors_origins=["https://other.local"])` produces allowed hosts without `sif.local` (the operator's host allowlist is silently lost), and overriding only `allowed_hosts` resets a caller-supplied fail-closed `cors_origins=[]` to `DEFAULT_CORS_ORIGINS` (verified), i.e. a hardening choice is silently widened back to the four default browser origins. The docstring says the recorded policy is reused "unless the caller overrides an allowlist", implying per-dimension preservation. The CLI path (`run_http`) always passes both, so production CLI use is unaffected; the public `build_server` + `create_http_app(server=...)` API is affected.
**Fix:** Merge per dimension from the recorded settings:
```python
existing = getattr(server, _TRANSPORT_SECURITY_ATTR, None)
if isinstance(existing, TransportSecuritySettings):
    hosts = allowed_hosts if allowed_hosts is not None else existing.allowed_hosts
    origins = cors_origins if cors_origins is not None else existing.allowed_origins
    return build_transport_security(hosts, origins)
return build_transport_security(allowed_hosts, cors_origins)
```
and add tests for both partial-override directions.

#### WR-06: Shipped search skill documents an invalid filter AST (`op` instead of `operator`)

**File:** `skills/sif-search/SKILL.md:42-44`
**Issue:** The skill instructs agents to pass `{"op": "eq", "field": "tags", "value": "python"}`. The shared grammar is a pydantic discriminated union on `operator` (`src/sif/core/filters.py:3`, `97-114`); there is no `op` field, so every agent following this example receives a `filter.<path>` tool error. The skill is the primary agent-facing documentation for the `filter` parameter.
**Fix:** Change the example to `{"field": "tags", "operator": "eq", "value": "python"}` and add a test/doc check that every `filter` example in `skills/` and `docs/` parses with `parse_filter`.

#### WR-07: MCP rerank ignores `SIF_RERANK_CANDIDATE_LIMIT`, breaking the claimed CLI pipeline parity

**File:** `src/sif/mcp/backend.py:433-450`
**Issue:** The CLI resolves the rerank candidate cap into `SearchOptions.candidate_limit` (`src/sif/cli/commands/search.py:1096` via `resolve_candidate_limit`), but `hybrid_search` constructs `SearchOptions` without `candidate_limit`, leaving the dataclass default 20. Verified with `Settings(rerank_enabled=True, rerank_candidate_limit=5)`: the pipeline receives `candidate_limit=20`. With reranking enabled the MCP server therefore reranks a different (smaller) candidate set than the CLI configured, contradicting the "full CLI pipeline parity (D-17)" claim and the `SIF_RERANK_CANDIDATE_LIMIT` setting's meaning.
**Fix:**
```python
from sif.config.settings import resolve_candidate_limit
...
candidate_limit=resolve_candidate_limit(None, self.settings),
```
and add a backend test that the configured cap rides `SearchOptions`.

#### WR-08: Embedded watch host ignores injected settings and initializes its schema at the process dimension

**File:** `src/sif/mcp/watch_host.py:103-131` (lines 113, 118-120); wired from `src/sif/mcp/app.py:230` and `262`
**Issue:** `start_embedded_watch` always reads the module-level `get_settings()` for the `SIF_MCP_WATCH` flag and calls `db.init_schema()` with no `embedding_dim`/`identity`, so it resolves the *process* settings. The public entry points accept injected settings (`create_http_app(db, settings=...)`, `run_stdio(db, settings=...)`, `build_server(settings=...)`). With `SIF_MCP_WATCH=1` and an injected `Settings` whose `embedding_dim` differs from the environment (or before the backend creates a new schema), the watch opens/migrates the index at the environment width first: the backend then raises `IdentityDimensionError` at startup (or the wrong settings-only identity row is written). The injected `mcp_watch` flag is also ignored in both directions. Tests mask this by patching `watch_host.get_settings`.
**Fix:** Thread the resolved `Settings` (and its identity) through `create_http_app`/`run_stdio`/`mcp_session_lifespan` into `start_embedded_watch(db_path, settings)` and call `db.init_schema(embedding_dim=settings.embedding_dim, identity=build_settings_identity(...))`, matching `SearchBackend.__init__`.

#### WR-09: `docs://` resource claims path retrieval it cannot perform, and claims full content it truncates

**File:** `src/sif/mcp/tools.py:405-433` (description lines 416-424)
**Issue:** The registered template is `docs://{doc_id}{?from_line,max_lines}` and the description says "Read a SIF document by doc id or path". The SDK applies its secure-by-default `ResourceSecurity` (`mcp/server/mcpserver/resources/templates.py:47-86`): absolute paths are rejected, and `{doc_id}` does not match embedded slashes. Verified against a running server: `docs:///n/a.md` and `docs://%2Fn%2Fa.md` both return "Unknown resource"; only doc ids work. Because `get_document` stores absolute paths, the advertised path mode is dead. Separately, the function docstring says "The full Markdown document is returned by default", but `get_document` truncates at 100 KiB with a suffix; `docs/mcp-server.md:196-199` correctly says only `docs://{doc_id}`.
**Fix:** Either narrow the description/docstring to doc id (and mention truncation), or pass `security=ResourceSecurity(reject_absolute_paths=False)` / a second template for paths — the lookup is a parameterized index query, so allowing absolute path strings here does not enable filesystem access. Add a test for path-form URIs if path support is retained.

#### WR-10: `docs://` resource accepts non-positive line parameters and silently returns the wrong slice

**File:** `src/sif/mcp/tools.py:425-429`
**Issue:** The resource function annotates `from_line: int | None` / `max_lines: int | None` with no constraints (the `get` tool has `Field(ge=1)`), and the SDK's `validate_call` accepts negatives. Verified: `docs://d?max_lines=-2` on a 6-line document returns the first four lines (`lines[0:-2]`) with no error, silently dropping the tail instead of rejecting or honoring a 1-based window. A negative `from_line` is coerced to line 1 by `(from_line or 1)`.
**Fix:** Use `Annotated[int | None, Field(ge=1)]` in the resource signature (validate_call applies the constraints) or reject non-positive values explicitly before calling `get_document`.

#### WR-11: Reranker construction is an unlocked check-then-act, allowing duplicate model loads

**File:** `src/sif/mcp/backend.py:357-379`
**Issue:** Unlike `_ensure_embedder`, `_reranker_for` has no lock: two concurrent first requests with reranking enabled can both observe `self._reranker is None`, call `create_reranker(...)`, and pass two distinct instances to their respective pipelines. Each instance has its own lazy `_model` and loads the (large) reranker independently during `rerank()`, doubling peak memory and startup work; one instance becomes unreachable after assignment. Reranker models are large enough that concurrent loads are an OOM/robustness risk, not just wasted work.
**Fix:** Guard construction with a lock (or an `Event`/future latch) and hand every caller the single constructed instance; keep the existing failure latch.

### Info

#### IN-01: Dead private helper `_fallback_snippet`

**File:** `src/sif/search/snippets.py:247-249`
**Issue:** After the `extract_with_range` refactor, `_fallback_snippet` has no callers in `src/` or `tests/`; it just returns element 0 of `_fallback_with_range`.
**Fix:** Remove it.

#### IN-02: Unused `StatusInput` model

**File:** `src/sif/mcp/protocol.py:198-201`
**Issue:** `StatusInput` is defined but never referenced anywhere; the status tool takes no arguments and publishes an empty schema.
**Fix:** Delete the model or use it in the tool body for symmetry with the other frozen input models.

#### IN-03: `mcp_watch_lifespan` is no longer used by production code

**File:** `src/sif/mcp/watch_host.py:189-213`
**Issue:** `create_http_app` now composes the SDK session manager and watch via `mcp_session_lifespan`; `mcp_watch_lifespan` is referenced only by tests. Two overlapping lifespan factories invite drift.
**Fix:** Remove it and migrate the remaining tests to `mcp_session_lifespan`, or keep one factory with a shared helper.

#### IN-04: `sif/mcp/cli.py` module docstring contradicts its eager app import

**File:** `src/sif/mcp/cli.py:1-10`
**Issue:** The docstring says "Imports of the app module are lazy so `import sif.mcp.cli` stays cheap", but line 10 imports `DEFAULT_HOST, DEFAULT_PORT` from `sif.mcp.app` at module scope, which pulls FastAPI, the SDK, `SearchBackend`, and the search stack on every import. The daemon/stdio callbacks then import the same module again inside the function.
**Fix:** Move the constant import into the functions (or define the constants in a light module) so the stated laziness is real.

#### IN-05: `multi_get` maps a valid `max_bytes=0` to the 100 KiB default

**File:** `src/sif/mcp/backend.py:767`
**Issue:** `max_b = max_bytes or (100 * 1024)` treats the tool's accepted `max_bytes=0` (`Field(ge=0)`) as "unset" and returns up to 100 KiB instead of honoring zero.
**Fix:** `max_b = 100 * 1024 if max_bytes is None else max_bytes` and add a boundary test.

#### IN-06: Architecture introduction still names only four MCP tools

**File:** `docs/architecture.md:6`
**Issue:** The introduction says the MCP server exposes "the `query`, `get`, `multi_get`, and `status` tools", while the same document (line 44) and every other updated doc name the seven-tool surface (`metadata`, `lex_search`, `vec_search` added). The file is in this phase's scope and was otherwise rewritten.
**Fix:** Update the introduction to the seven tools (and mention the daemon host if listing hosts).

#### IN-07: Recorded transport policy is not applied by the exported server object

**File:** `src/sif/mcp/app.py:191` (recording) and `144-154` (only consumer)
**Issue:** `build_server` records `TransportSecuritySettings` on the server, but only `create_http_app` reads it. A hosted app that follows `docs/api-reference.md:746` ("The server object for tests or hosted apps") and calls the SDK's `server.run(transport="streamable-http", host="0.0.0.0")` gets the SDK default: DNS-rebinding protection is silently disabled for non-loopback hosts. This does not affect `run_http`/`sif mcp http`, which is the documented CLI path.
**Fix:** Document that hosted apps must pass the recorded settings to `run()`/`streamable_http_app()`, or expose a SIF runner that applies them automatically.

#### IN-08: `lex_search`/`vec_search` descriptions claim CLI matching but default collection scope differs

**File:** `src/sif/mcp/tools.py:78-86` (descriptions); `src/sif/mcp/backend.py:451`, `569`; `src/sif/cli/commands/search.py:192-216`
**Issue:** With no `collections` argument, the MCP tools pass `collection_ids=None`, which searches every document, while the CLI's default (`sif search search` / `sif search vsearch` with no `-c`/`--all`) resolves `list_enabled()` (`include_by_default=1`). The descriptions say the tools match those CLI commands (the parenthetical enumerates filter/offset/min_score, so this is a scope rather than an option mismatch). The behavior may be intentional for the MCP context, but it is undocumented and differs from the named CLI command.
**Fix:** Document that MCP defaults to all collections (in the tool description and `docs/mcp-server.md`), or resolve `list_enabled()` when `collections` is omitted to match the CLI.

---

_Reviewed: 2026-11-16T09:57:40Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
