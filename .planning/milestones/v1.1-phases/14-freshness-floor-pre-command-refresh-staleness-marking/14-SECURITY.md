---
phase: "14"
slug: "freshness-floor-pre-command-refresh-staleness-marking"
status: verified
# threats_open = count of OPEN threats at or above workflow.security_block_on severity (the blocking gate)
threats_open: 0
asvs_level: 1
created: "2026-11-08"
---

# Phase 14 — Security

> Per-phase security contract: threat register, accepted risks, and audit trail.

---

## Trust Boundaries

| Boundary | Description | Data Crossing |
|----------|-------------|---------------|
| filesystem → drift walk | untrusted on-disk state (symlinked roots, unmounted collections, pathological trees) crosses into the drift detector | file paths, mtimes (low sensitivity) |
| sif process → stderr/stdout pipes | notice/warning text crosses to user pipes consumed by `sif -q search ... --json` (project skills) | constant status strings (no document content) |
| index DB → staleness/status surfaces | computed booleans/counts cross to search results, MCP metadata, `sif status` | derived flags only (no content, titles, paths) |

---

## Threat Register

| Threat ID | Category | Component | Severity | Disposition | Mitigation | Status |
|-----------|----------|-----------|----------|-------------|------------|--------|
| T-14-01 | Tampering | drift.py walk (path confusion via symlinked roots, /tmp vs /private/tmp) | medium | mitigate | Every walk path resolved via `.resolve()` before compare (drift.py:106); walk scoped to registered roots via `is_relative_to` (scanner.py:88) — L1 verified | closed |
| T-14-02 | DoS | drift.py walk on pathological trees | low | mitigate | One rglob+stat pass (~43 ms @ 5k files, probed); refresh bounded by `search_refresh_max_files` cap (skip+warn over cap, test-enforced); disableable via `SIF_SEARCH_REFRESH_ENABLED` / `--no-refresh` — L1 verified | closed |
| T-14-03 | Information Disclosure | stderr notices / warnings | low | mitigate | Constant strings naming counts/commands only (`_refresh_notice`, search.py:127,199,209); no document content, titles, or paths in notices; logging discipline unchanged — L1 verified | closed |
| T-14-04 | Information Disclosure | staleness marker + Vector lag status row | low | mitigate | Signal is a computed boolean + a count (`Vector lag: N document(s)`, main.py:202-208); no content joins the new surfaces — L1 verified | closed |
| T-14-05 | Tampering | derived signal integrity (future write path leaving stale embeddings silently un-marks docs) | medium | mitigate | D-08 invariant regression tests pin the purge behavior (test_incremental.py:158, 271, 432 — modified/removed/update_paths all purge embeddings); delete-before-insert keeps per-doc state all-or-nothing — L1 verified | closed |
| T-14-06 | Tampering | format_results_xml / format_results_csv marker rendering | low | mitigate | Marker renders as fixed boolean literal (`vectors_stale="{stale_attr}"`, search.py:291), never document-derived text; annotation text is a constant string — L1 verified | closed |
| T-14-SC | Tampering | package installs | high | accept | Phase installs nothing — zero new runtime dependencies (pyproject.toml diff across the entire phase is empty; Package Legitimacy Audit in 14-RESEARCH.md is empty) — L1 verified | closed |

*Status: open · closed · open — below high threshold (non-blocking)*
*Severity: critical > high > medium > low — only open threats at or above workflow.security_block_on count toward threats_open*
*Disposition: mitigate (implementation required) · accept (documented risk) · transfer (third-party)*

---

## Accepted Risks Log

| Risk ID | Threat Ref | Rationale | Accepted By | Date |
|---------|------------|-----------|-------------|------|
| AR-14-01 | T-14-SC | Phase installs nothing; zero new runtime dependencies (locked project decision) — nothing to verify beyond the empty install surface, confirmed by empty pyproject.toml diff | plan-time accept + L1 audit (agent) | 2026-11-08 |

*Accepted risks do not resurface in future audit runs.*

---

## Security Audit Trail

| Audit Date | Threats Total | Closed | Open | Run By |
|------------|---------------|--------|------|--------|
| 2026-11-08 | 7 | 7 | 0 | gsd-secure-phase (L1 short-circuit: register_authored_at_plan_time, asvs_level 1) |

---

## Sign-Off

- [x] All threats have a disposition (mitigate / accept / transfer)
- [x] Accepted risks documented in Accepted Risks Log
- [x] `threats_open: 0` confirmed
- [x] `status: verified` set in frontmatter

**Approval:** verified 2026-11-08
