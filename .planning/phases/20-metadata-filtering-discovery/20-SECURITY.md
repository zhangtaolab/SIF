---
phase: "20"
slug: "metadata-filtering-discovery"
status: verified
# threats_open = count of OPEN threats at or above workflow.security_block_on severity (the blocking gate)
threats_open: 0
asvs_level: 1
created: "2026-11-18"
verified: "2026-11-18"
---

# Phase 20 — Security

> Per-phase security contract: threat register, accepted risks, and audit trail.
> Verified by /gsd-secure-phase 20 on 2026-11-18 (ASVS L1, block_on high).
> Register authored at plan time: all five PLANs carry STRIDE `<threat_model>` blocks. L1
> grep-depth verification confirmed every mitigation present; `threats_open: 0`.

---

## Trust Boundaries

| Boundary | Description | Data Crossing |
|----------|-------------|---------------|
| user/agent → CLI `--filter` | Untrusted JSON crosses from the shell into the AST validator | Operator names, field paths, operand values |
| frontmatter file → typed kv store | Arbitrary YAML from local files reaches SQLite binds | Keys, scalar and homogeneous-array values |
| compiled predicate → SQLite | Operand text must never reach the SQL string | Bound values, fixed SQL fragments |
| stored `documents.metadata` → backfill pass | Legacy rows are trusted input to the derivation | Canonical metadata JSON |
| migration notice → stderr/stdout | A log line must not pollute machine output | Log text, scanned counts |
| filter AST → vector KNN + JOIN | A selective predicate drives a bounded work budget | AST, pre-count, fetch window |
| vector leg → stderr | A diagnostic must not cross into results or machine output | Too-selective notice text |
| search entry point → both legs | A dropped filter would widen the result across scopes | AST object identity |
| MCP client → tool handler | Untrusted `filter` dict; must be a recoverable tool error, not a protocol fault | Filter/match JSON, window sizes |
| typed store → discovery aggregates | Discovery must not read a different source than the compiler | Typed rows, key/value windows |
| discovery output → MCP/CLI text | Machine output must stay clean | Envelope JSON, tables, footers |

---

## Threat Register

| Threat ID | Category | Component | Severity | Disposition | Mitigation | Status |
|-----------|----------|-----------|----------|-------------|------------|--------|
| T-20-01 | Tampering | `search/filters.py` compiler | critical | mitigate | `_placeholders` emits only `?, `; every operand appended to params in SQL order; only fixed table/column/alias text interpolated; injection regression (`test_filters_sql.py:870-921`) asserts byte-identical SQL for quote/comment/percent payloads | closed |
| T-20-02 | Denial of service | `core/filters.py` budget walk | high | mitigate | Depth ≤8, nodes ≤64, string ≤1024, array ≤128, `extra="forbid"`; iterative stack pre-walk before pydantic; named budget errors | closed |
| T-20-03 | Tampering | `metadata_repository.py` derivation | high | mitigate | Per-key skip classification (nested/null/mixed/over-cap/non-finite); other rows still derived; skip rows capped at 64 | closed |
| T-20-04 | Information disclosure | `bm25.py` filter slot | high | mitigate | `filter is None` is the only unfiltered signal; non-None always yields a non-empty predicate; suffix in both branches; empty match → zero rows | closed |
| T-20-05 | Tampering | backfill + write-path SQL | high | mitigate | Delete-then-insert and backfill use fixed SQL with `?` binds; no user-controlled table/column text | closed |
| T-20-06 | Tampering / DoS | `typed_rows` + `replace_from_canonical` | high | mitigate | Only scalars and homogeneous scalar lists bound; NaN/Inf/overflow rejected before bind; skip rows capped at 64; per-file error path preserved | closed |
| T-20-07 | Integrity | backfill announcement | medium | mitigate | `logger.warning` → stderr handler; `capsys.readouterr().out == ""` asserted | closed |
| T-20-08 | Integrity | `_backfill_metadata_values` marker gate | high | mitigate | Marker read first, one transaction per document, marker written only after the loop; failure propagates out of `create_all`; interrupted-pass resume test | closed |
| T-20-09 | Tampering | `vector.py` filtered SQL | critical | mitigate | Compiled fragment + `AND` suffix into the post-KNN JOIN WHERE; params bound after embedding/k/collection ids; end-to-end injection test leaves the table intact | closed |
| T-20-10 | Denial of service | filtered KNN escalation | high | mitigate | `_MAX_FETCH_K = 2048`; one pre-count + selectivity seeding; `pre_count == 0` returns `[]` before any KNN; bounded stop conditions | closed |
| T-20-11 | Integrity | too-selective notice | medium | mitigate | Formatted `logger.warning` once, gated on `is_metadata_filtered`; stdout asserted empty | closed |
| T-20-12 | Information disclosure | both legs | high | mitigate | `is_metadata_filtered` derives from `filter is not None`; pre-count 0 → `[]`; both legs receive the same AST object (identity-asserted) | closed |
| T-20-13 | Tampering | CLI/MCP filter parsing | critical | mitigate | One `parse_filter` behind CLI `parse_filter_option` and MCP `_parse_filter_node`; operands never enter SQL text | closed |
| T-20-14 | Denial of service | MCP `filter` payload | high | mitigate | Budget pre-walk runs before pydantic on every surface; hostile payloads (e.g. `10**400`) → controlled `ToolError` | closed |
| T-20-15 | Integrity | CLI output modes | medium | mitigate | Filtered `--json` parses and carries no notice text; stdout carries only results/envelope | closed |
| T-20-16 | Information disclosure | input → options threading | high | mitigate | AST threaded explicitly to `SearchOptions.filter`; `None` on unfiltered paths; identity asserted through the backend | closed |
| T-20-17 | Tampering | discovery SQL (filters, match, windows) | critical | mitigate | `discover` takes pre-compiled fragments; collection scope, key list, `LIMIT`, `min_count` all bound; `compile_filter`/`compile_match` are the only predicate producers | closed |
| T-20-18 | Denial of service | huge value sets | high | mitigate | Key window `LIMIT ?` (default 50) with exact `remainingKeys`; per-type `value_limit` (default 10) with exact `remainingValues`; no unbounded mode | closed |
| T-20-19 | Integrity | CLI/MCP output | medium | mitigate | `--json` emits exactly the strict envelope; table mode emits table plus remainder/skip footers; no notice enters either | closed |
| T-20-20 | Information disclosure | filter-aware denominators | high | mitigate | `documents` is the collection-scope denominator; `filteredDocuments` only when a filter is supplied; skipped keys counted not listed; `keys` and `builtIns` disjoint | closed |
| T-20-SC | Tampering | package installs | high | mitigate | No dependency added; no phase-20 commit touches `pyproject.toml`/lockfiles; all plans `user_setup: []` | closed |

*Status: open · closed · open — below high threshold (non-blocking)*
*Severity: critical > high > medium > low — only open threats at or above workflow.security_block_on count toward threats_open*
*Disposition: mitigate (implementation required) · accept (documented risk) · transfer (third-party)*

---

## Accepted Risks Log

No accepted risks.

---

## Security Audit Trail

| Audit Date | Threats Total | Closed | Open | Run By |
|------------|---------------|--------|------|--------|
| 2026-11-18 | 21 | 21 | 0 | /gsd-secure-phase 20 (gsd-security-auditor, ASVS L1) |

---

## Sign-Off

- [x] All threats have a disposition (mitigate / accept / transfer)
- [x] Accepted risks documented in Accepted Risks Log
- [x] `threats_open: 0` confirmed
- [x] `status: verified` set in frontmatter

**Approval:** verified 2026-11-18 — 21/21 threats closed at L1; 0 open at or above `high`.
