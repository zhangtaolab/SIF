---
phase: "12"
slug: "sif-watch-foreground-mvp"
status: verified
# threats_open = count of OPEN threats at or above workflow.security_block_on severity (the blocking gate)
threats_open: 0
asvs_level: 1
created: "2026-11-07"
---

# Phase 12 — Security

> Per-phase security contract: threat register, accepted risks, and audit trail.

---

## Trust Boundaries

| Boundary | Description | Data Crossing |
|----------|-------------|---------------|
| Filesystem events → watch intake | Raw watchdog events (arbitrary paths, non-UTF8 names, symlinked roots) enter the indexer | File paths + event types; decoded via `os.fsdecode`, normalized via `Path.resolve()` |
| Watch process ↔ SQLite | A resident writer shares the DB with CLI/MCP readers | Document/chunk/vector rows via parameterized repository SQL under per-burst flock |
| Watch output ↔ terminal | Batch summaries and error events rendered to the user | Paths, counts, model/dimension messages only — never document content |

---

## Threat Register

| Threat ID | Category | Component | Severity | Disposition | Mitigation | Status |
|-----------|----------|-----------|----------|-------------|------------|--------|
| T-12-01 | Tampering | watcher event intake (pathological/non-UTF8 names) | medium | mitigate | `os.fsdecode` via `_event_path` (watcher.py), `Path.resolve()` on src+dest, shared `FileScanner.matches` predicate (watcher.py:436), parameterized repository SQL only — no shell interpolation, no eval | closed |
| T-12-02 | DoS | event storm → unbounded queue/memory | medium | mitigate | EventDebouncer coalesces per quiet window; `fold_events` dedupes to a path set per batch; bounded single-drain shutdown flush | closed |
| T-12-03 | Information disclosure | logs/CLI output carrying document content | medium | mitigate | Log lines carry paths/counts only (4 logger call sites checked, none touch parsed content); document content never Rich-markup-rendered (locked decision, D-13) | closed |
| T-12-04 | Tampering | symlinked watch roots escaping intended roots | medium | mitigate | Schedules only `Path(collection.path).resolve()` of registered collections (watcher.py:128,134 resolution path); never watches broader than registered roots (D-01) | closed |
| T-12-05 | DoS | missing root misread as mass deletion destroying the index | high | mitigate | D-11 guard in `update_collection` AND `update_paths` (incremental.py:111-119): warn + `missing <name>` event + zero result, never sweep — regression-tested against the verified latent bug | closed |
| T-12-06 | DoS | shutdown hang when the flock is held past the deadline during flush | medium | mitigate | Bounded flush: ONE queue drain with short timeout, join with timeout, `wal_checkpoint(TRUNCATE)` in try/finally (watch.py), second signal raises SystemExit(130) immediately (D-14) | closed |
| T-12-07 | Tampering | depth inversion — embedding running as a background default | high | mitigate | LIVE-05 invariant unit-tested: embed only via `--embed` or explicit `SIF_WATCH_UPDATE_DEPTH=embed`; `watch_update_depth` field default `bm25` with `field_validator` rejecting other values (settings.py:55,181) | closed |
| T-12-08 | Information disclosure | error events carrying document content during embed failures | low | accept | Error events carry model/dimension messages and paths only; MarkdownParser content never enters event payloads (existing core protocol) — residual risk nil by construction | closed |
| T-12-09 | Tampering | hand-edited generator-owned docs bypassing the CI diff gate | low | accept | CI diff gate enforces generator-only docs downstream; prohibition in must_haves + project memory; 12-03's docs diff verified generator-produced | closed |
| T-12-10 | DoS | e2e suite hanging on a missed outcome (flaky backend behavior) | low | mitigate | Deadline-bounded outcome polling throughout test_watch_e2e.py (10 deadline/monotonic sites); a hang surfaces as a bounded failure, not an infinite stall | closed |
| T-12-SC | Tampering | dependency range change (pip/uv) | high | mitigate | No new package: only watchdog range tightened to `>=4.0.0,<7.0.0` (pyproject.toml:38); RESEARCH.md Package Legitimacy Audit dispositions the SUS heuristic as a false positive (source-level inspection of installed 6.0.0) | closed |

*Status: open · closed · open — below high threshold (non-blocking)*
*Severity: critical > high > medium > low — only open threats at or above workflow.security_block_on count toward threats_open*
*Disposition: mitigate (implementation required) · accept (documented risk) · transfer (third-party)*

---

## Accepted Risks Log

| Risk ID | Threat Ref | Rationale | Accepted By | Date |
|---------|------------|-----------|-------------|------|
| AR-12-01 | T-12-08 | Error-event payloads are paths/model messages only by construction; document content never enters the event protocol | Plan 12-02 threat model | 2026-11-07 |
| AR-12-02 | T-12-09 | CI diff gate enforces generator-owned docs; hand-edit prohibition documented in plan must_haves and project memory | Plan 12-03 threat model | 2026-11-07 |

*Accepted risks do not resurface in future audit runs.*

---

## Security Audit Trail

| Audit Date | Threats Total | Closed | Open | Run By |
|------------|---------------|--------|------|--------|
| 2026-11-07 | 11 | 11 | 0 | /gsd-secure-phase 12 (ASVS L1, plan-time register, short-circuit per L1 rule) |

---

## Sign-Off

- [x] All threats have a disposition (mitigate / accept / transfer)
- [x] Accepted risks documented in Accepted Risks Log
- [x] `threats_open: 0` confirmed
- [x] `status: verified` set in frontmatter

**Approval:** verified 2026-11-07
