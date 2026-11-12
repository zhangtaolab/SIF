---
phase: 13-watch-everywhere-mcp-embedded-refresh-background-daemon
plan: 03
subsystem: mcp
tags: [mcp, watchdog, stdio, fastapi-lifespan, live-index, e2e]

requires:
  - phase: 13-01
    provides: [FileWatcher core, rescope seam, mcp_watch setting]
provides:
  - src/sif/mcp/watch_host.py — the shared MCP watch host: start_embedded_watch/stop_embedded_watch (SIF_MCP_WATCH opt-in gate, depth literal bm25, logger-only renderers, serve-first queued reconcile, D-14 stop ordering) + mcp_watch_lifespan FastAPI lifespan factory
  - Both transports host the watcher (D-01) — stdio wraps the serve loop with start/finally-stop; HTTP threads a lifespan through create_app/HTTPTransport/run_http_server (default None keeps every existing call site working)
  - tests/integration/test_mcp_watch_e2e.py — real stdio JSON-RPC line-protocol harness (SC1 refresh, burst responsiveness, protocol-clean stdout, unblocked handshake under drift)
  - tests/unit/mcp/test_mcp_watch_host.py — decision-pin battery (flag off, depth forced, zero collections, queued reconcile, logger-only, stop ordering, lifespan contract)
affects: [MCP transports (stdio/http), Phase 14 freshness floor (queries hit a live index under SIF_MCP_WATCH=1)]

actuals:
  tokens: 11250   # chars/4 over the realized production diff (45003 chars across 6 files)
  tasks: 2
  commits: 4      # measured: git rev-list --count 74a750a..HEAD (2x RED + 2x GREEN)
plan_head_before: 74a750a9ef7f02ee0087dfb8e1720ef76996ddcb
plan_head_after: 0e842a38ac756a3720f266db32b50eab8439d6ff

tech-stack:
  added: []       # zero new deps (milestone lock held)
  patterns:
    - "One watch core, two lifecycle wirings: a host module owns construction/teardown; transports only call start/stop around their serve loops (D-01)"
    - "Serve-first reconcile: queue.Queue.put of FoldResult(needs_reconcile=True) jobs from the host thread is race-free — the handshake/lifespan yield never waits on indexing (Pitfall 4)"
    - "FastAPI lifespan threading with default-None parameters keeps every pre-existing call site compiling and passing (compat pin)"
    - "e2e isolation: lex: BM25-prefix queries + SIF_MODEL_TYPE=gguf fail-fast keep the child server embedding-free, fast-booting, and deterministic"

key-files:
  created: [src/sif/mcp/watch_host.py, tests/unit/mcp/test_mcp_watch_host.py, tests/integration/test_mcp_watch_e2e.py]
  modified: [src/sif/mcp/transports/stdio.py, src/sif/mcp/transports/http.py, tests/unit/mcp/test_transports_http.py]

key-decisions:
  - "Depth is the literal bm25 constant in watch_host (D-02): the update-depth setting is never read — grep-visible, unit-pinned under watch_update_depth=embed"
  - "The startup reconcile is enqueued, not run inline: the worker's queue accepts FoldResult(needs_reconcile=True) jobs from the host thread (queue.Queue is thread-safe), so initialize and the lifespan yield never block (Pitfall 4)"
  - "HTTP wiring is unconditional and cheap: run_http_server always constructs mcp_watch_lifespan; the flag check lives inside start_embedded_watch so flag-off serving is byte-identical (D-04) with zero conditional plumbing in transports"
  - "mcp_watch_lifespan is a plain async context manager — no fastapi import in watch_host (import-light, no optional-dep try/except); create_app's lifespan parameter defaults to None so existing call sites are untouched"
  - "stop_embedded_watch owns the D-14 ordering adapted to the host-owned connection: watcher.stop(flush=True) -> PRAGMA wal_checkpoint(TRUNCATE) -> Database.close, all in nested finallys (unit-pinned call order)"
  - "e2e hermeticity: queries use the lex: prefix (pure BM25 — never touches the embedder) and the child env sets SIF_MODEL_TYPE=gguf so SearchBackend's embedder construction fails fast into its caught-warning path — no model load, no network, deterministic boot"

patterns-established:
  - "Line-protocol e2e harness: reader-thread + queue for deadline-bounded JSON-RPC matching, stdout captured line-by-line as the protocol-clean corpus, stderr pumped separately, stdin-EOF as the graceful shutdown that exercises the host's finally-stop path"
  - "Quiesced-worker unit pattern reused from 13-01 to prove queued-not-inline reconcile deterministically (patch FileWatcher construction to no-op _worker_loop before start)"

requirements-completed: [LIVE-08]   # declared by this plan; shared-ID gate (13-01 also declared it and is complete)

coverage:
  - id: D1
    description: "SC1 stdio e2e: with SIF_MCP_WATCH=1 a real stdio server indexes a file created AFTER server start (findable via query tools/call, no manual update/restart); a query issued while a 5-file burst settles answers within 5s; every stdout line parses as JSON during active bursts; the initialize handshake answers within 15s over a collection with pre-seeded drift and the drifted content is refreshed afterwards"
    requirement: LIVE-08
    verification:
      - kind: integration
        ref: "tests/integration/test_mcp_watch_e2e.py#test_stdio_watch_refreshes_index_while_serving (pass, and 4/4 twice in a row at the tracer gate)"
        status: pass
      - kind: integration
        ref: "tests/integration/test_mcp_watch_e2e.py#test_stdio_watch_query_responsive_during_burst (pass)"
        status: pass
      - kind: integration
        ref: "tests/integration/test_mcp_watch_e2e.py#test_stdio_stdout_protocol_clean_during_burst (pass)"
        status: pass
      - kind: integration
        ref: "tests/integration/test_mcp_watch_e2e.py#test_stdio_initialize_not_blocked_by_pending_drift (pass)"
        status: pass
    human_judgment: false
  - id: D2
    description: "Host decision pins (D-02/D-04/Pitfall 4/1): flag off returns None and never constructs Database; depth stays bm25 under watch_update_depth=embed with the D-15 rescope provider wired returning all registered collections; zero collections no-ops with a logged notice and no watcher; the reconcile is queued (qsize 1, indexer idle) and runs only at stop's flush drain; renderers emit caplog records with empty sys.stdout; stop orders flush -> wal_checkpoint(TRUNCATE) -> close"
    requirement: LIVE-08
    verification:
      - kind: unit
        ref: "tests/unit/mcp/test_mcp_watch_host.py (10 tests: flag off, depth forced, zero collections, queued reconcile, renderers, stop ordering, lifespan x3 — pass)"
        status: pass
    human_judgment: false
  - id: D3
    description: "HTTP lifespan wiring (D-01): create_app(server, lifespan=cm) starts before requests and stops after serving (TestClient); create_app(server) with no lifespan still builds and serves /health; no on_event handlers; HTTPTransport forwards its lifespan into create_app; run_http_server lazily constructs mcp_watch_lifespan(db_path) and hands it to the transport unconditionally"
    requirement: LIVE-08
    verification:
      - kind: unit
        ref: "tests/unit/mcp/test_transports_http.py#TestWatchLifespanThreading (5 tests, pass) + updated exact-kwargs composition tests (pass)"
        status: pass
    human_judgment: false

duration: 18min
completed: 2026-11-08
status: complete
---

# Phase 13 Plan 03: MCP-Embedded Watch (stdio + HTTP Lifespan) Summary

**The proven FileWatcher now lives inside the MCP server under SIF_MCP_WATCH=1 — one shared watch host (BM25-only depth, logger-only output, serve-first queued reconcile, rescope) wired around the stdio serve loop and into the HTTP transport via a FastAPI lifespan, proven by a real stdio subprocess e2e that answers queries while indexing a live burst with a 100% JSON-clean stdout.**

## Performance
- **Duration:** 18min | **Started:** 2026-11-07T15:59:10Z | **Tasks:** 2 | **Files:** 6 (3 created, 3 modified)
- **Suite:** 1129 passed @ 94.41% coverage (fail_under=90); ruff check/format green; ty check src/sif 0 diagnostics
- **Estimate vs actual:** 40000 tokens estimated (confidence: low), 11250 actual (chars/4 over the realized diff) — the 13-01 seam plus the Phase 12/13 e2e culture again carried most of the work

## Accomplishments
- **SC1 refresh + responsiveness (LIVE-08):** a real `sif mcp stdio` subprocess with `SIF_MCP_WATCH=1` completes the JSON-RPC handshake, its queued startup reconcile makes the seed findable, a file created after server start becomes findable through a `query` tools/call with no manual update — and a query issued while a 5-file burst is settling still answers within 5s. Event handling never starves query handling (queries run through `SearchBackend._run_in_db` on fresh connections; watcher bursts run on the FileWatcher worker under per-burst flock — D-03 coexistence unchanged, no host-added protocol).
- **Pitfall 1 pinned twice:** every stdout line the server emitted during active bursts parses via `json.loads` (e2e corpus assertion), and the renderers are unit-pinned to logger records with an empty `sys.stdout`.
- **Pitfall 4 pinned twice:** the handshake answers within 15s over pre-seeded drift (e2e), and the unit battery proves the reconcile is queued (`qsize == 1`, indexer idle) and runs only when stop's flush drains the queue — never inline in start.
- **D-02 billing guard:** `watch_host` passes the literal `"bm25"` into WatchConfig and never references the update-depth setting (grep-clean module; unit-pinned under `watch_update_depth="embed"`).
- **D-04 byte-identity:** flag off returns None before any Database construction (unit-pinned); HTTP wiring is unconditional but the flag check inside `start_embedded_watch` keeps flag-off serving identical with zero transport-side conditionals.
- **D-15 rescope:** the host's provider returns every registered collection on the 13-01 tick seam — a collection added to a running MCP server is picked up without restart.
- **D-01 both transports:** stdio wraps the serve loop with start/finally-stop (signature unchanged — the env var is the only lever); HTTP threads a default-None `lifespan` through `create_app`/`HTTPTransport`/`run_http_server`, so every existing `create_app(server)` call site keeps working (compat-pinned; no `on_event` handlers anywhere).

## Task Commits
Each task followed RED → GREEN with machine-validated RED evidence (`gsd_run check tdd-red-evidence` → RED_EVIDENCE_OK, junit format):

1. **Task 1: Stdio tracer — SIF_MCP_WATCH=1 server indexes live changes while answering queries (SC1)** — `ad4d597` (test: 4-test e2e battery; target `test_stdio_watch_refreshes_index_while_serving` failed on the planned findability assertion — no watch wiring, 271 protocol-clean stdout lines received but no refresh) → `9a966df` (feat: watch_host.py + stdio wiring; 4/4 e2e green)
   - Tracer feedback gate: all three `<verify>` commands re-run end-to-end after the tracer commit — e2e 4 passed TWICE in a row (8.81s / 8.91s, flakiness criterion), units 79 passed, ruff clean. `⚡ Tracer verified end-to-end — expanding.`
2. **Task 2: HTTP lifespan wiring + host unit battery** — `9780010` (test: 10 host pins + 5 HTTP threading tests; target `test_lifespan_factory_starts_before_yield_and_stops_after` failed on ImportError for the missing `mcp_watch_lifespan`; battery landscape 6 failed on the planned surface / 31 passed) → `0e842a3` (feat: lifespan factory + create_app/HTTPTransport/run_http_server threading; 94 unit/mcp green)

**Plan metadata:** see final docs commit below (docs(13-03): complete MCP-embedded watch plan)

## Files Created/Modified
- `src/sif/mcp/watch_host.py` — NEW: `EmbeddedWatch` dataclass, `_render_event`/`_render_batch` (logger-only), `_enqueue_startup_reconcile` (queue.put of the recovery-return job shape), `start_embedded_watch` (flag gate → Database → init_schema → list collections → zero-collection no-op → FileWatcher with bm25 depth + rescope provider + logger callbacks → start → enqueue), `stop_embedded_watch` (nested-finally D-14 ordering, None-safe), `mcp_watch_lifespan` (plain async CM; start before yield, stop in finally)
- `src/sif/mcp/transports/stdio.py` — `run_stdio_server` starts the watcher before serving, stops it in a `finally`; signature unchanged
- `src/sif/mcp/transports/http.py` — `create_app` gains `lifespan: Any = None` → `FastAPI(lifespan=...)`; `HTTPTransport.__init__`/`run` carry and forward it; `run_http_server` lazily imports and wires `mcp_watch_lifespan(db_path)`
- `tests/integration/test_mcp_watch_e2e.py` — NEW: `_StdioServer` line-protocol harness (reader thread + deadline queue, stderr pump, stdin-EOF graceful shutdown, safety-net CM exit) + 4 tests
- `tests/unit/mcp/test_mcp_watch_host.py` — NEW: 10 decision-pin tests
- `tests/unit/mcp/test_transports_http.py` — +`TestWatchLifespanThreading` (5 tests); the two exact-kwargs composition tests updated for the new `lifespan` parameter

## Decisions Made
- The startup reconcile enqueues through the watcher's queue directly (the recovery-return job shape) rather than growing FileWatcher's public API — `queue.Queue.put` is thread-safe, and 13-01's `_schedule_added` already uses the identical shape; no watcher.py changes were needed this plan.
- e2e queries always use the `lex:` BM25 prefix and the child env sets `SIF_MODEL_TYPE=gguf` (no model path → construction fails fast into SearchBackend's caught-warning path): the e2e never loads an embedding model, boots in ~1s, and cannot hit the network — deterministic and D-02-aligned.
- Graceful e2e shutdown is stdin EOF: the transport loop exits, the host's `finally` runs the full D-14 stop, and the process exits 0 — every e2e test exercises the production stop path for free.
- `mcp_watch_lifespan` stops in a `finally` so a failing app body still tears the watcher down; it tolerates the None (flag-off) return both at start and stop.

## Deviations from Plan
None - plan executed exactly as written.

(Execution notes, not deviations: PERF203/ARG005 lint iterations inside GREEN loops — try/except hoisted to a helper, lambda args underscore-prefixed (same ARG005 class 13-02 fixed); ty prefers `AsyncGenerator` over `AsyncIterator` for `@asynccontextmanager` return annotations — followed; the two pre-existing exact-kwargs HTTP composition tests were updated for the new `lifespan` kwarg, which the plan's compat requirement anticipated — "new params must default to keep existing call sites working".)

## TDD Gate Compliance

| Task | RED commit | RED evidence | GREEN commit | REFACTOR |
|------|-----------|--------------|--------------|----------|
| 1 (tracer) | `ad4d597` | RED_EVIDENCE_OK (junit; target: test_stdio_watch_refreshes_index_while_serving — "seed.md not findable via query 'lex: seed paragraph' within 30.0s"; harness proven working: handshake + 271 JSON stdout lines received, only watch-driven refresh missing) | `9a966df` | none needed |
| 2 | `9780010` | RED_EVIDENCE_OK (junit; target: test_lifespan_factory_starts_before_yield_and_stops_after — ImportError: cannot import name 'mcp_watch_lifespan'; battery 6 failed on the planned surface, 31 passed) | `0e842a3` | none needed |

Both GREEN commits are preceded by their RED commits; every RED was machine-validated before production edits. No violations. (Task 2's host pins for Task 1's e2e-proven API passed on arrival by design — the 13-02 test-first-split precedent; the RED target was the new lifespan behavior.)

## Issues Encountered
- The first RED e2e run showed the child's SearchBackend eagerly loading the real ModelScope embedding model at boot (several seconds, mps variance) — neutralized by the `SIF_MODEL_TYPE=gguf` fail-fast env (documented under Decisions); the `lex:` prefix additionally guarantees the query path never embeds.
- pytest's whole-suite `fail_under=90` gate trips on single-file runs, so partial-run verify commands use `--no-cov` for clean exit codes (13-02 precedent); the full suite proves the gate proper (94.41%).
- Pre-existing (out of scope, unchanged from 13-02's log): ResourceWarning from an unclosed sqlite connection in 13-01's TestIdleCheckpoint.

## User Setup Required
None - no external service configuration required. (Opt-in behavior: set `SIF_MCP_WATCH=1` in the environment of any `sif mcp stdio` / `sif mcp http` process — e.g. the MCP client's server env — and assistant queries hit a live index. Nothing changes for existing users until they set the variable.)

## Known Stubs
None. `sif mcp daemon` remains unwired by design (D-14 — backlog); this plan's lifespan wiring is shaped so a future daemon host reuses `mcp_watch_lifespan` unchanged.

## Threat Flags
None — no security-relevant surface beyond the plan's threat model. T-13-07 (stdout corruption) mitigated and double-pinned; T-13-08 (background embedding) mitigated by the literal bm25 depth (grep-clean, unit-pinned); T-13-09 (handshake stall) mitigated by serve-first (unit + e2e pinned); T-13-SC held (zero new dependencies, no install steps).

## Next Phase Readiness
Ready for 13-04 (Wave 3): the watch host surface is final — 13-04 regenerates the generator-owned docs so `SIF_MCP_WATCH`/`watch_rescope_interval`/`watch_checkpoint_interval` appear in configuration.md and the watch flag surface in cli-reference.md, then lands service install on the 13-02 lifecycle-flag family. LIVE-08 completes at this plan's requirements gate (13-01 also declared it and is complete); LIVE-09 stays open until 13-04 (shared-ID gate).

## Self-Check: PASSED
- Created files FOUND: src/sif/mcp/watch_host.py, tests/unit/mcp/test_mcp_watch_host.py, tests/integration/test_mcp_watch_e2e.py
- Commits FOUND (ancestors of HEAD): ad4d597, 9a966df, 9780010, 0e842a3
- Full suite: 1129 passed @ 94.41%; ruff/format/ty green

---
*Phase: 13-watch-everywhere-mcp-embedded-refresh-background-daemon*
*Completed: 2026-11-08*
