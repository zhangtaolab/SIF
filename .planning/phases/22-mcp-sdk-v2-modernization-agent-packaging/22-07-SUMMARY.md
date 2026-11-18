---
phase: 22-mcp-sdk-v2-modernization-agent-packaging
plan: 07
subsystem: mcp
tags: [mcp, registry, distribution, packaging, claude-code, phase-gate, smoke]

# Dependency graph
requires:
  - phase: 22-mcp-sdk-v2-modernization-agent-packaging
    provides: "22-01..22-05 SDK v2 server, seven-tool surface, daemon, lazy embedder, citation output"
  - phase: 22-mcp-sdk-v2-modernization-agent-packaging
    provides: "22-06 Claude Code plugin, marketplace, MCP-first skills, and docs rewrite"
provides:
  - "server.json Registry manifest for io.github.zhangtaolab/sif (PyPI docsif, stdio, 1.1.2)"
  - "scripts/publish_registry.py with --check/--publish, README-marker/PyPI/server.json/registry preflight, and already-listed idempotency"
  - "tests/unit/mcp/test_registry_script.py mocked refusal/duplicate/publisher/credential battery"
  - "Registry sections in README.md and docs/mcp-server.md"
  - "Phase 22 gate evidence and a recorded real Claude Code client smoke (seven tools + query)"
affects: [phase-22-verification, release-process, registry-listing]

# Actuals (#2632) — pairs with the plan's `estimate` (78000 tokens, 3 tasks, low confidence).
# Tokens are chars/4 over the plan's realized product diff (server.json, script, tests, README, docs).
# `commits` is measured from the on-disk plan ledger; it includes Task 1's commit, the two
# orchestration pause/resume docs commits, and Task 3's commit. The final metadata commit follows.
actuals:
  tokens: 8186
  tasks: 3
  commits: 4
plan_head_before: f6c217cdfa31845d85bbee9d883f948de9c0da3f
plan_head_after: ef9730665bc7517b0f0031cd5d46a4b4e07c3af0

tech-stack:
  added: []
  patterns:
    - "Registry idempotency lives in the script: query name+version first; 200 prints `already listed` and exits 0 without invoking mcp-publisher"
    - "Registry authentication is delegated to `mcp-publisher login github`; the repo never reads, writes, or prints credentials"
    - "Preflight is stdlib-only and reads the version via runpy, never importing the sif package"
    - "Real Claude Code client evidence comes from the stream-json init event of `claude -p --strict-mcp-config --mcp-config <temp>` (Claude Code 2.1.325 `claude mcp get` shows status, not tools)"
    - "Generated docs stay generator-owned: `make docs-generate` plus `git diff --exit-code` is the only permitted path"

key-files:
  created:
    - server.json
    - scripts/publish_registry.py
    - tests/unit/mcp/test_registry_script.py
  modified:
    - README.md
    - docs/mcp-server.md

key-decisions:
  - "The public Registry listing is recorded as blocked (user chose `blocked no-github-login` on 2026-11-16). No login, publish, or credential storage was attempted; D-24 explicitly permits this outcome and does not treat it as a code failure."
  - "`--check` treats a well-formed 404 as `not listed (reachable)` and a 200 as `already listed`; both exit 0. Only name/package/version mismatches, 5xx, or network failures refuse with a specific FAIL line."
  - "A duplicate name+version never reaches `mcp-publisher`: the script short-circuits with `already listed` and exit 0 (C6/D-24)."
  - "The README line-2 `mcp-name` marker and `src/sif/_version.py` (1.1.2) are unchanged; no v1.2 tag or release was cut."
  - "The smoke used a temporary local-scope `sif-smoke` MCP entry against /tmp/sif-stdio-smoke/sif.db, then removed it; the pre-existing project-scoped `sif` entry was left in its prior pending-approval state."

patterns-established:
  - "A blocked maintainer checkpoint is recorded with the exact deferred command, never simulated or auto-approved"
  - "Phase gates are recorded verbatim in the plan SUMMARY with exact counts, outputs, and exit statuses"

requirements-completed: [MCP-09, MCP-01, MCP-02, MCP-03, MCP-04, MCP-05, MCP-06, MCP-07, MCP-08]

coverage:
  - id: D1
    description: "server.json declares io.github.zhangtaolab/sif, PyPI docsif, stdio transport, and version 1.1.2 matching _version.py; the script preflights marker/PyPI/server.json/registry and never handles credentials"
    requirement: MCP-09
    verification:
      - kind: unit
        ref: "tests/unit/mcp/test_registry_script.py#TestServerJson,TestCheck,TestPublish"
        status: pass
      - kind: other
        ref: "python scripts/publish_registry.py --check"
        status: pass
    human_judgment: false
  - id: D2
    description: "README and docs/mcp-server.md document the Registry name, docsif package, stdio transport, --check preflight, login+publish flow, already-listed duplicate behavior, and the re-run-after-release rule"
    requirement: MCP-09
    verification:
      - kind: other
        ref: "grep -c '^### MCP Registry' README.md; grep -c '^## MCP Registry' docs/mcp-server.md; grep 'already listed' both"
        status: pass
    human_judgment: false
  - id: D3
    description: "Phase gate green: full pytest with fail_under=90, ruff check/format, ty, make docs-generate clean, claude plugin validate success with zero errors, registry --check green, version/tag guards"
    requirement: MCP-01
    verification:
      - kind: unit
        ref: "env -u FORCE_COLOR NO_COLOR=1 pytest"
        status: pass
      - kind: other
        ref: "ruff check src tests; ruff format --check src tests; ty check src/sif"
        status: pass
      - kind: other
        ref: "make docs-generate && git diff --exit-code docs/cli-reference.md docs/configuration.md"
        status: pass
      - kind: other
        ref: "claude plugin validate --json ."
        status: pass
      - kind: other
        ref: "grep -c '__version__ = \"1.1.2\"' src/sif/_version.py; test -z \"$(git tag --list 'v1.2*')\""
        status: pass
    human_judgment: false
  - id: D4
    description: "Real Claude Code client lists the seven MCP tools and one query returns the seeded hello.md result"
    requirement: MCP-01
    verification:
      - kind: e2e
        ref: "claude -p --mcp-config /tmp/sif-stdio-smoke/claude-mcp-smoke.json --strict-mcp-config --output-format stream-json (init lists 7 mcp__sif-smoke__* tools; query tool call returns hello.md)"
        status: pass
    human_judgment: false
  - id: D5
    description: "Live public Registry publish for io.github.zhangtaolab/sif 1.1.2"
    verification: []
    human_judgment: true
    rationale: "Requires the maintainer's GitHub device-flow identity; the user chose blocked no-github-login, so the listing is deferred and no publish was attempted. Recorded as blocked per D-24."

# Metrics
duration: 7min
completed: 2026-11-16
status: complete
---

# Phase 22 Plan 07: Registry Listing, Phase Gate, and Real-Client Evidence Summary

**Scripted and preflighted MCP Registry listing (io.github.zhangtaolab/sif → PyPI docsif, stdio) with the publish deferred to a recorded blocked maintainer checkpoint, plus a green full Phase 22 gate and real Claude Code seven-tool/query smoke**

## Performance

- **Duration:** ~7 min (continuation at Task 3; Task 1 ran earlier and the Task 2 checkpoint was paused and resolved on 2026-11-16)
- **Started:** 2026-11-16T09:27:22Z (Task 3 continuation)
- **Completed:** 2026-11-16T09:34:00Z
- **Tasks:** 3 (Task 1 complete, Task 2 resolved blocked at the maintainer checkpoint, Task 3 complete)
- **Files changed:** 5 (3 created, 2 modified)

## Accomplishments

- `server.json` is a valid 2025-12-11 Registry manifest for `io.github.zhangtaolab/sif`: one-line description, version `1.1.2` matching `src/sif/_version.py`, and a single PyPI package entry `docsif` at the same version with `stdio` transport. No OAuth, remote transport, or credential field.
- `scripts/publish_registry.py` is stdlib-only (no `sif` import), with mutually exclusive `--check`/`--publish` and `main() -> int`. `--check` verifies the exact README marker, the PyPI release, `server.json` name/package/version consistency, and Registry reachability; a well-formed 404 is `not listed (reachable)` and a 200 is `already listed`, both exit 0. `--publish` runs the preflight, short-circuits a listed version with `already listed` + exit 0 without invoking `mcp-publisher`, and otherwise propagates the publisher's status.
- `tests/unit/mcp/test_registry_script.py` covers the manifest identity, the marker/PyPI/version/name refusal branches, a reachable 404, an already-listed 200, the duplicate-version no-invoke path, the 404 publisher-invocation path, and a credential-key source scan. The full suite grew from 2846 to 2866 tests (+20).
- README and `docs/mcp-server.md` now document the Registry name, the `docsif` PyPI package, stdio transport, the `mcp-publisher login github` + `scripts/publish_registry.py --publish` flow, the `--check` preflight, duplicate-version `already listed` behavior, and the re-run-after-release rule. The README line-2 marker and `_version.py` are unchanged.
- The Phase 22 gate is green: 2866 passed / 1 skipped at 95.11% coverage, ruff check + format, `ty check src/sif`, `make docs-generate` with a clean diff, `claude plugin validate --json .` with `success: true` and zero errors, `publish_registry.py --check` green, and both release guards passing.
- Real Claude Code client evidence is recorded: the stream-json init event shows the seven `mcp__sif-smoke__*` tools and a real `query` tool call returned the seeded `hello.md` document. The temporary MCP entry was removed afterwards.
- Registry publish outcome: **blocked** at the maintainer checkpoint (`blocked no-github-login`). No login, publish, or credential storage was attempted; `--check` still reports `not listed (reachable)`, which is the normal pre-publish state. This is the plan's permitted non-code outcome (D-24).

## Phase Gate Evidence (exact)

| Gate | Command | Result | Exit |
|------|---------|--------|------|
| Full suite + coverage | `env -u FORCE_COLOR NO_COLOR=1 pytest` | `2866 passed, 1 skipped, 22 warnings in 141.88s (0:02:21)`; `Required test coverage of 90.0% reached. Total coverage: 95.11%` | 0 |
| Lint | `ruff check src tests` | `All checks passed!` | 0 |
| Format | `ruff format --check src tests` | `224 files already formatted` | 0 |
| Types | `ty check src/sif` | `All checks passed!` | 0 |
| Generated docs | `make docs-generate && git diff --exit-code docs/cli-reference.md docs/configuration.md` | both references regenerated; no diff | 0 |
| Plugin validation | `claude plugin validate --json .` | `success: true`, `strict: false`, marketplace/plugin `errors: []`; warnings: root `CLAUDE.md` not loaded as plugin context, `ICON_MISSING` (non-blocking) | 0 |
| Registry preflight | `python scripts/publish_registry.py --check` | `OK README marker` / `OK PyPI version` / `OK server.json` / `OK registry: not listed (reachable) io.github.zhangtaolab/sif 1.1.2` | 0 |
| Version guard | `grep -c '__version__ = "1.1.2"' src/sif/_version.py` | `1` | 0 |
| Tag guard | `test -z "$(git tag --list 'v1.2*')"` | no output (no matching tag) | 0 |
| Credential prohibition | `grep -rn "password\|api_key\|secret\|Bearer" scripts/publish_registry.py` | no matches | 1 (expected) |

## Registry Publish Outcome — BLOCKED

- **Checkpoint:** 22-07 Task 2, `checkpoint:human-action gate="blocking-human"`.
- **User decision (2026-11-16):** `blocked no-github-login`.
- **Attempted:** nothing beyond the read-only `--check`; `mcp-publisher login github` and `python scripts/publish_registry.py --publish` were intentionally not run. No credentials were created, stored, or printed.
- **Environment:** `mcp-publisher 1.8.9` remains installed at `/opt/homebrew/bin/mcp-publisher` and unauthenticated.
- **Current Registry state:** `not listed (reachable)` for `io.github.zhangtaolab/sif` 1.1.2 via `https://registry.modelcontextprotocol.io/v0.1/servers/io.github.zhangtaolab%2Fsif/versions/1.1.2`.
- **Resume command (maintainer):**
  ```bash
  mcp-publisher login github
  python scripts/publish_registry.py --publish
  ```
  A second `--publish` on a listed version prints `already listed` and exits 0; the script never invokes the publisher for a duplicate.
- **Classification:** blocked maintainer authentication, not a code failure (D-24). The scripted `--check` half is the CI-verifiable surface and is green.

## Real Claude Code Client Smoke (recorded)

Temporary local-scope entry (removed after the run):

```bash
claude mcp add -s local sif-smoke \
  -e SIF_DB_PATH=/tmp/sif-stdio-smoke/sif.db \
  -e SIF_CACHE_DIR=/tmp/sif-stdio-smoke/home/cache \
  -e HOME=/tmp/sif-stdio-smoke/home -e NO_COLOR=1 \
  -e PYTHONPATH=/Users/forrest/GitHub/SIF/src \
  -- python -m sif.cli.main mcp stdio
```

`claude mcp get sif-smoke` observed:

```text
sif-smoke:
  Scope: Local config (private to you in this project)
  Status: ✔ Connected
  Type: stdio
  Command: python
  Args: -m sif.cli.main mcp stdio
  Environment:
    SIF_DB_PATH=/tmp/sif-stdio-smoke/sif.db
    SIF_CACHE_DIR=/tmp/sif-stdio-smoke/home/cache
    HOME=/tmp/sif-stdio-smoke/home
    NO_COLOR=1
    PYTHONPATH=/Users/forrest/GitHub/SIF/src
```

Claude Code 2.1.325 `claude mcp get` reports connection status but not the tool list, so the
seven-tool listing and one query were captured from a real headless client session
(`--strict-mcp-config` isolates it from all other servers):

```bash
claude -p 'Use the mcp__sif-smoke__query tool exactly once with {"query": "hello world", "limit": 5}. Then reply with the number of results and the first result path.' \
  --mcp-config /tmp/sif-stdio-smoke/claude-mcp-smoke.json \
  --strict-mcp-config --allowedTools 'mcp__sif-smoke__query' \
  --output-format stream-json --verbose --max-turns 3 --no-session-persistence
```

Observed (exit 0):

- `system/init` → `"mcp_servers":[{"name":"sif-smoke","status":"connected","source":"dynamic"}]`
- `system/init` tools include exactly: `mcp__sif-smoke__get`, `mcp__sif-smoke__lex_search`, `mcp__sif-smoke__metadata`, `mcp__sif-smoke__multi_get`, `mcp__sif-smoke__query`, `mcp__sif-smoke__status`, `mcp__sif-smoke__vec_search`
- `tool_use` → `{"name":"mcp__sif-smoke__query","input":{"limit":5,"query":"hello world"}}`
- `tool_result` → one result: `path /private/tmp/sif-stdio-smoke/notes/hello.md`, title `Hello World`, `line_start 1`, `line_end 5`, `score 0.999996615396071`, `content_hash ee2c4e0fc7ea117c31ea5be801106a75e06f41fcdbbba1ed8c5b395ff3edf603`, snippet beginning `# Hello World\n\nHello world from the SIF MCP stdio smoke test.`
- Final assistant result: `1 result — first path: /private/tmp/sif-stdio-smoke/notes/hello.md ("Hello World", rank 1).`
- stderr carried a non-blocking client warning: `[claude-code:unrecognized_model] {"model":"zcode/GLM-5.3-Flash:max[1m]","query_source":"sdk"}`; the session still exited 0 and the MCP call succeeded.
- Cleanup: `claude mcp remove sif-smoke -s local` → `Removed MCP server sif-smoke from local config`; `claude mcp list` no longer shows `sif-smoke`, and the pre-existing project-scoped `sif` entry is unchanged (`⏸ Pending approval`, as before).

## Task Commits

Each task was committed atomically:

1. **Task 1: `server.json` and the `--check`/`--publish` preflight script** - `51e6fa1` (feat)
2. **Task 2: Maintainer device-flow login and live Registry publish** - no commit; resolved `blocked no-github-login` (checkpoint documentation in `00814e3`, `d676616`)
3. **Task 3: Registry docs, phase gate, and recorded real-client evidence** - `ef97306` (docs)

**Plan metadata:** `docs(22-07): complete ... plan` commit created after this SUMMARY (not counted in `actuals.commits`).

## Files Created/Modified

- `server.json` - Registry manifest (`io.github.zhangtaolab/sif`, `docsif`, stdio, 1.1.2)
- `scripts/publish_registry.py` - marker/PyPI/server.json/registry preflight, already-listed idempotency, credential-free publisher delegation
- `tests/unit/mcp/test_registry_script.py` - 20 mocked preflight/idempotency/credential tests
- `README.md` - MCP Registry section (name, docsif, stdio, login+publish, `--check`, duplicate behavior, release re-run rule); line-2 marker unchanged
- `docs/mcp-server.md` - MCP Registry section with preflight checks, maintainer publishing flow, and re-run-after-release steps

## Decisions Made

- See frontmatter `key-decisions`. The load-bearing ones: the publish is recorded as blocked per the user's explicit choice and D-24; the script owns duplicate-version idempotency; the marker and version remain untouched; and the real-client tool listing was captured through a headless stream-json session because `claude mcp get` does not expose tools in 2.1.325.

## Deviations from Plan

None auto-fixed. The plan executed as written, with one planned checkpoint resolved at the user's direction:

- **Task 2 (maintainer publish)** was resolved as `blocked no-github-login` instead of a live publish. D-24 explicitly permits recording the run as blocked without treating it as a code failure. The checkpoint's "second `--publish` prints `already listed`" verification is therefore not executable yet; the behavior is covered by `tests/unit/mcp/test_registry_script.py#TestPublish`.
- The smoke's "claude mcp lists the seven tools" evidence is from the `system/init` event of a headless Claude Code session rather than `claude mcp` output, because this CLI version's `mcp get`/`mcp list` show health, not tool names. The plan allows recording the exact command and observed output.

## Issues Encountered

- `claude mcp get sif-smoke` reported `Status: ✔ Connected` but no tool list in Claude Code 2.1.325. Resolved by capturing the stream-json `system/init` event from a real `claude -p` session, which lists the seven MCP tools and executes the query.
- `claude -p` printed an `unrecognized_model` warning on stderr for the configured model alias; the run still exited 0 and the MCP tool call returned results.
- No test, lint, type, docs, or plugin-validation failures were encountered.

## Known Stubs

None. The Registry listing is deferred by explicit maintainer decision, not stubbed; the scripted preflight and docs are complete and green.

## User Setup Required

The public Registry listing remains a manual maintainer step:

1. `mcp-publisher login github` (GitHub device flow).
2. `python scripts/publish_registry.py --publish` from the repository root.
3. Verify the version at `https://registry.modelcontextprotocol.io/v0.1/servers/io.github.zhangtaolab%2Fsif/versions/1.1.2`.

No credentials, environment variables, or dashboard configuration are added to the repo.

## Next Phase Readiness

- Phase 22's seven plans are executed and summarized; the full gate is green and the real Claude Code client smoke is recorded.
- Phase-level verification (`/gsd-verify-work` / verifier), code review, and the phase-completion state update remain, per the orchestrator.
- The public Registry listing is the only outstanding distribution item; it is blocked on maintainer GitHub authentication and can be published later without code changes.

---
*Phase: 22-mcp-sdk-v2-modernization-agent-packaging*
*Completed: 2026-11-16*

## Self-Check: PASSED

- Files verified: `server.json`, `scripts/publish_registry.py`, `tests/unit/mcp/test_registry_script.py`, `README.md`, `docs/mcp-server.md`, `22-07-SUMMARY.md`.
- Commits verified as ancestors of HEAD: `51e6fa1` (Task 1), `00814e3`/`d676616` (checkpoint docs), `ef97306` (Task 3).
