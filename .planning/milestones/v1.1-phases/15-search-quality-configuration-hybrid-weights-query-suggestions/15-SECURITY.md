---
phase: "15"
slug: "search-quality-configuration-hybrid-weights-query-suggestions"
status: verified
# threats_open = count of OPEN threats at or above workflow.security_block_on severity (the blocking gate)
threats_open: 0
asvs_level: 1
created: "2026-11-08"
---

# Phase 15 — Security

> Per-phase security contract: threat register, accepted risks, and audit trail.

---

## Trust Boundaries

| Boundary | Description | Data Crossing |
|----------|-------------|---------------|
| CLI/MCP input → fusion params | user/assistant-supplied weights and k | floats/ints, arithmetic-only (never SQL) |
| suggestion engine → FTS MATCH | vocab/query terms re-enter search | quoted term strings via the sanitizer |
| search → query_log | executed searches persist locally | query string, result count, collection names (no content) |
| vocab/user strings → Rich rendering | suggestion cells to the terminal | escaped text only |
| index → MCP zero-result response | suggestion terms cross to the assistant | flat term strings from the same local index |

---

## Threat Register

| Threat ID | Category | Component | Severity | Disposition | Mitigation | Status |
|-----------|----------|-----------|----------|-------------|------------|--------|
| T-15-01 | Tampering | query_cmd weight flags | low | mitigate | `click.IntRange(1, None)` / `FloatRange(0, min_open=True)` (search.py:749-767) — parse-time rejection; values are arithmetic-only, never interpolated into SQL/MATCH — L1 verified | closed |
| T-15-02 | Tampering | MCP QueryInput weight fields | low | mitigate | Pydantic `ge=1` / `gt=0.0` on QueryInput (protocol.py:248-249) — ValidationError before options construction (ASVS V5) — L1 verified | closed |
| T-15-03 | Tampering | suggestion engine → FTS MATCH | medium | mitigate | Vocab/query terms re-enter search exclusively via `_sanitize_term`/`_build_fts_query` quoting (bm25.py:21,160; suggest.py:8 docstring) — never hand-built MATCH strings; repository SQL fully parameterized (ASVS V5) — L1 verified | closed |
| T-15-04 | Information Disclosure | query_log (local personal data) | medium | mitigate | Local-only table; `QueryLogEntry` stores query/result-count/collections only — never document content (models.py:208-216); `SIF_QUERY_HISTORY_ENABLED=0` read+write gates + trim cap — L1 verified | closed |
| T-15-05 | DoS | unbounded query_log growth | low | mitigate | Trim-in-write cap (D-09, default 500, ge=1) — table never grows unboundedly — L1 verified | closed |
| T-15-06 | Tampering | Rich rendering of vocab/user strings | medium | mitigate | `escape()` on every vocab/user-derived cell, after truncation (suggest.py:36,55) — bracket sequences render literally (Phase 5 CR-01/CR-02 culture) — L1 verified | closed |
| T-15-07 | Information Disclosure | MCP zero-result suggestions expose index vocabulary | low | accept | Suggestion terms derive from the same local index normal search already exposes to the same local user; flat term strings, no paths/content — accepted | closed |
| T-15-08 | DoS | DYM engine cost on the search hot path | low | mitigate | Zero-result-only trigger (D-05; single call site search.py:249) + bucketed difflib + fail-soft wrapping — measured ≤ ~10 ms core work on 20k-term index — L1 verified | closed |
| T-15-SC | Tampering | package installs | high | accept | No package installs — zero new runtime dependencies (difflib/bisect/sqlite3 stdlib); pyproject.toml untouched across the phase — L1 verified | closed |

*Status: open · closed · open — below high threshold (non-blocking)*
*Severity: critical > high > medium > low — only open threats at or above workflow.security_block_on count toward threats_open*
*Disposition: mitigate (implementation required) · accept (documented risk) · transfer (third-party)*

---

## Accepted Risks Log

| Risk ID | Threat Ref | Rationale | Accepted By | Date |
|---------|------------|-----------|-------------|------|
| AR-15-01 | T-15-07 | Suggestion terms are index vocabulary the same local user already reaches via normal search; no new data class crosses the MCP boundary | plan-time accept + L1 audit (agent) | 2026-11-08 |
| AR-15-02 | T-15-SC | Phase installs nothing; zero new runtime dependencies (locked project decision) | plan-time accept + L1 audit (agent) | 2026-11-08 |

*Accepted risks do not resurface in future audit runs.*

---

## Security Audit Trail

| Audit Date | Threats Total | Closed | Open | Run By |
|------------|---------------|--------|------|--------|
| 2026-11-08 | 9 | 9 | 0 | gsd-secure-phase (L1 short-circuit: register_authored_at_plan_time, asvs_level 1) |

---

## Sign-Off

- [x] All threats have a disposition (mitigate / accept / transfer)
- [x] Accepted risks documented in Accepted Risks Log
- [x] `threats_open: 0` confirmed
- [x] `status: verified` set in frontmatter

**Approval:** verified 2026-11-08

## Security Audit 2026-11-12

| Metric | Count |
|---|---|
| Threats found | 9 |
| Closed | 9 |
| Open | 0 |
