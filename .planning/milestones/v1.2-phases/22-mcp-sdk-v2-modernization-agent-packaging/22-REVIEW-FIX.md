---
phase: 22-mcp-sdk-v2-modernization-agent-packaging
fixed_at: 2026-11-16T10:14:44Z
review_path: .planning/phases/22-mcp-sdk-v2-modernization-agent-packaging/22-REVIEW.md
iteration: 1
findings_in_scope: 12
fixed: 12
skipped: 0
status: all_fixed
---

# Phase 22: Code Review Fix Report

**Fixed at:** 2026-11-16T10:14:44Z
**Source review:** `.planning/phases/22-mcp-sdk-v2-modernization-agent-packaging/22-REVIEW.md`
**Iteration:** 1
**Fix scope:** `critical_warning` (CR-*, BL-*, WR-*; necessity findings excluded)

**Summary:**
- Findings in scope: 12 (2 Critical, 10 Warning)
- Fixed: 12
- Skipped: 0
- Out of scope: WR-04 (Warning carrying `**Category:** necessity` — excluded by `critical_warning`), IN-01 through IN-08 (Info)

Every fix was committed atomically with the finding ID in the subject. Regression
tests that reproduce the defect were added where practical and were verified to
fail against the pre-fix code (noted per finding).

## Fixed Issues

### CR-01: Lazy embedder fast path treats "load in progress" as "load failed"

**Status:** Fixed — requires human verification (concurrency logic)
**Files modified:** `src/sif/mcp/backend.py`, `tests/unit/mcp/test_lazy_embedder.py`
**Commit:** `b30a429`

`_ensure_embedder` no longer reads `_load_attempted` on an unlocked fast path.
The whole attempt (flag set, `from_settings`, `load_model`, `get_identity`,
manager publish) happens under `_load_lock`, so a concurrent caller blocks until
the load settles and receives the published manager instead of `None`. The
failure latch still prevents retries and repeated warnings. New regression test
`test_a_waiter_arriving_mid_load_receives_the_manager` parks one thread inside
`load_model` with events and asserts the waiter gets the same manager; it failed
pre-fix (`None is <manager>`).

### CR-02: `vec_search` performed the lazy model load on the event loop

**Status:** Fixed — requires human verification (event-loop concurrency)
**Files modified:** `src/sif/mcp/backend.py`, `tests/unit/mcp/test_lazy_embedder.py`
**Commit:** `6c9f8c1`

`vec_search` now runs `await asyncio.to_thread(self._ensure_embedder)`, matching
`hybrid_search`'s worker-thread load, so a cold model import/download cannot
freeze other MCP requests or `/health`. New test
`test_cold_vec_search_load_does_not_block_concurrent_requests` has the load hook
wait for a concurrently scheduled `get_status`; pre-fix the hook observed a
timeout (False), post-fix it observes completion (True).

### WR-01: Fallback snippet line windows counted phantom trailing lines

**Status:** Fixed — requires human verification (off-by-one logic)
**Files modified:** `src/sif/search/snippets.py`, `tests/unit/search/test_snippets.py`
**Commit:** `0f2e817`

`_fallback_with_range` now derives the reported end from the rendered snippet
(`snippet.removesuffix("...").count("\n") + 1`) instead of the raw split length
or untrimmed truncation prefix. Trailing newlines/blank lines are no longer
counted, and a cut landing exactly on a newline reports only the line rendered.
Four fixtures added (trailing newline, trailing blanks, leading skip + trailing
newline, cut-on-newline); all four failed pre-fix.

### WR-02: `get` fabricated lines past EOF and reported ranges its truncated content did not cover

**Status:** Fixed — requires human verification (range logic)
**Files modified:** `src/sif/mcp/backend.py`, `src/sif/mcp/protocol.py`, `docs/mcp-server.md`, `skills/sif-get/SKILL.md`, `tests/unit/mcp/test_backend.py`, `tests/unit/mcp/goldens/*.json`
**Commits:** `d6d653f`, `b9c7c08` (regenerated wire goldens for the published `Document` description)

Ranged windows are clamped to the document line count; a `from_line` past EOF
returns empty content with `line_start`/`line_end = None`; `max_lines` beyond
EOF reports the clamped window. When `_truncate_content` cuts the payload, the
reported end is recomputed from the rendered body (`_line_count`), so callers
never cite lines absent from `content`. Docs and the `sif-get` skill were
aligned with the clamped behavior. Two of the three new tests fail pre-fix
(past-EOF fabrication, truncation range); the clamp test pins the corrected
contract. The protocol docstring is part of `outputSchema`, so all five wire
goldens were regenerated (only the description text differs).

### WR-03: Non-finite metadata diverged between text and structured channels

**Status:** Fixed
**Files modified:** `src/sif/mcp/tools.py`, `tests/unit/mcp/test_tools.py`
**Commit:** `4cb0504`

`_result` now derives `structured_content = json.loads(text)` from the same
strict JSON text, so the two channels cannot drift. (An intermediate attempt to
apply `json_safe` after `model_dump(mode="json")` was rejected: pydantic already
converts NaN/Infinity to `null` in JSON mode, so the normalization has to happen
on the python-mode dump that feeds the text channel.) New test pins legacy
`NaN`/`Infinity` metadata to `"nan"`/`"inf"` in both channels; it failed pre-fix.

### WR-05: Partial transport-security overrides dropped the recorded allowlist

**Status:** Fixed — requires human verification (conditional merge logic)
**Files modified:** `src/sif/mcp/app.py`, `tests/unit/mcp/test_app.py`
**Commit:** `d0d2495`

`_resolve_transport_security` merges per dimension: an override supplies only
its own dimension and the other comes from the server's recorded
`TransportSecuritySettings` (both `None` still reuses the recorded policy
verbatim). Three tests cover host-only, origin-only, and fail-closed
`cors_origins=[]` preservation; all three failed pre-fix.

### WR-06: Search skill documented an invalid filter AST (`op` instead of `operator`)

**Status:** Fixed
**Files modified:** `skills/sif-search/SKILL.md`, `tests/unit/mcp/test_plugin.py`
**Commit:** `356ef6f`

The example now uses `{"field": "tags", "operator": "eq", "value": "python"}`.
New tests scan every `skills/*/SKILL.md` for the removed `"op":` field and parse
all documented filter examples with the shared `parse_filter`; both failed
pre-fix.

### WR-07: MCP rerank ignored `SIF_RERANK_CANDIDATE_LIMIT`

**Status:** Fixed
**Files modified:** `src/sif/mcp/backend.py`, `tests/unit/mcp/test_backend.py`
**Commit:** `6e96d04`

`hybrid_search` now sets
`candidate_limit=resolve_candidate_limit(None, self.settings)` on
`SearchOptions`, the same resolution the CLI uses. New test pins
`rerank_candidate_limit=5` onto the options object passed to the pipeline; it
failed pre-fix (dataclass default 20).

### WR-08: Embedded watch host ignored injected settings and schema dimension

**Status:** Fixed
**Files modified:** `src/sif/mcp/watch_host.py`, `src/sif/mcp/app.py`, `tests/unit/mcp/test_mcp_watch_host.py`
**Commit:** `a1f0eea`

`start_embedded_watch(db_path, settings=None)` resolves only `None` from the
process environment, honors the injected `mcp_watch` flag, and opens the schema
with `init_schema(embedding_dim=settings.embedding_dim,
identity=_settings_identity(settings))` matching `SearchBackend`. The resolved
settings are threaded through `run_stdio`, `create_http_app` →
`mcp_session_lifespan`, and `mcp_watch_lifespan`. New tests assert the injected
flag governs both directions and the schema open carries the injected dimension
and an `EmbedderIdentity`; the lifespan test asserts settings forwarding. The
old tests that masked this by patching `watch_host.get_settings` still pass.

### WR-09: `docs://` resource advertised path lookup it cannot perform

**Status:** Fixed
**Files modified:** `src/sif/mcp/tools.py`, `tests/unit/mcp/test_tools.py`
**Commit:** `e5d47f2`

The resource description and registration docstring now name document IDs only
and state the 100 KiB truncation, since the SDK's secure-by-default
`ResourceSecurity` rejects absolute paths and `{doc_id}` cannot match embedded
slashes; path retrieval stays on the `get` tool. A test pins the advertised
description (no "path", mentions document IDs and truncation) and failed pre-fix.

### WR-10: `docs://` accepted non-positive line parameters and silently sliced wrong

**Status:** Fixed
**Files modified:** `src/sif/mcp/tools.py`, `tests/unit/mcp/test_tools.py`
**Commit:** `da08651`

`read_document` parameters are now
`Annotated[int | None, Field(ge=1)]`, so the SDK's `validate_call` rejects
`0`/negative values before `get_document` runs. Tests cover `max_lines=-2`,
`max_lines=0`, and `from_line=0`; all were accepted pre-fix (and returned the
wrong slice / coerced to line 1).

### WR-11: Reranker construction was an unlocked check-then-act

**Status:** Fixed — requires human verification (concurrency logic)
**Files modified:** `src/sif/mcp/backend.py`, `tests/unit/mcp/test_backend.py`
**Commit:** `5b57d88`

`_reranker_for` now constructs under `self._reranker_lock` with a double-check
inside the lock, so concurrent first requests share one reranker (and therefore
one lazy model load); the ImportError/ValueError failure latch is preserved.
New test starts two callers at a barrier against a slowed factory; it failed
pre-fix with `create_reranker.call_count == 2`.

## Skipped Issues

None in scope.

Out of scope for `fix_scope: critical_warning` (left in `22-REVIEW.md`):

- **WR-04** (necessity finding): impossible-state `ImportError` guard in
  `_reranker_for`, classified `**Category:** necessity`. Removing code is a
  scope decision for the human.
- **IN-01 … IN-08**: Info findings (dead helper, unused model, unused lifespan,
  lazy-import docstring, `max_bytes=0`, architecture intro, recorded policy
  consumer, collection-scope wording).

## Verification

Worktrees were disabled in this project (`workflow.use_worktrees: false`), so
all edits, tests, and commits ran in the main checkout.

- Per-fix regression checks were run against the pre-fix source by temporarily
  restoring the file from `HEAD` and re-running the new test(s), then restoring
  the fixed file. Confirmed failing pre-fix: CR-01, CR-02, WR-01 (4 tests),
  WR-02 (2 of 3), WR-03, WR-05 (3), WR-06 (2), WR-07, WR-08 (2), WR-09 (1),
  WR-10 (3), WR-11.
- Affected suites: `tests/unit/mcp`, `tests/unit/search/test_snippets.py`,
  `tests/unit/search/test_hybrid.py`, `tests/unit/cli/test_mcp.py`,
  `tests/integration/test_mcp_watch_e2e.py` — 419 passed.
- Full quality suite (main checkout):
  - `ruff check src tests` — passed
  - `ruff format --check src tests` — 224 files already formatted
  - `ty check src/sif` — passed
  - `pytest` — 2889 passed, 1 skipped; coverage 95.13% (gate 90%)
- Wire goldens were regenerated once (commit `b9c7c08`); the only diff is the
  `Document` model description published in `outputSchema`.

---

_Fixed: 2026-11-16T10:14:44Z_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_
