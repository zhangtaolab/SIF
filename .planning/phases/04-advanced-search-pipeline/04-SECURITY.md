---
phase: "04"
slug: "advanced-search-pipeline"
status: verified
# threats_open = count of OPEN threats at or above workflow.security_block_on severity (the blocking gate)
threats_open: 0
asvs_level: 1
created: "2026-09-04"
---

# Phase 04 — Security

> Per-phase security contract: threat register, accepted risks, and audit trail.

> Register authored at plan time (all 5 PLANs carry `<threat_model>` blocks); verified
> retroactively 2026-09-04 at ASVS L1 (grep-depth) during phase-gate bookkeeping. The
> plan-time register predates severity columns — severities below were reconstructed at
> audit time. T-04-05 was assigned independently in plans 04-01 and 04-02; the 04-02
> occurrence is recorded here as T-04-05b.

---

## Trust Boundaries

| Boundary | Description | Data Crossing |
|----------|-------------|---------------|
| CLI → SearchPipeline | Untrusted user query crosses into search execution | query string |
| SearchPipeline → BM25Searcher | Query enters FTS5 MATCH expression | FTS5 query syntax |
| SearchPipeline → VectorSearcher | Query embedding enters SQL parameter | float vector |
| User query → QueryExpansion | Untrusted input enters expansion logic | query string + intent |
| Chunk content → SmartSnippetExtractor | Indexed content (trusted) is processed | document text |
| CLI → bench_cmd | User-provided fixture file path | filesystem path |
| Fixture JSON → SearchEvaluator | Untrusted JSON data enters evaluation | fixture JSON |
| Test fixtures → Test execution | Mock data simulates untrusted input | synthetic data |

---

## Threat Register

| Threat ID | Category | Component | Severity | Disposition | Mitigation | Status |
|-----------|----------|-----------|----------|-------------|------------|--------|
| T-04-01 | Tampering | BM25Searcher._build_fts_query | medium | mitigate | Parameterized queries — `MATCH ?` + `execute(sql, params)`; no string interpolation of query terms into SQL (`src/sif/search/bm25.py:69,75`) | closed |
| T-04-02 | Information Disclosure | SearchResult.scores dict in --explain | low | accept | Local-first tool; scores reveal internal model behavior, acceptable for local debugging | closed |
| T-04-03 | Denial of Service | Reranker with large candidate pool | medium | mitigate | `candidate_limit: int = 20` default (`src/sif/core/models.py:252`); reranker input capped via `results[: options.candidate_limit]` (`src/sif/search/hybrid.py:260`) | closed |
| T-04-04 | Tampering | CrossEncoder input pairs | low | mitigate | Pairs built as `(query, text)` tuples from indexed results — inference-only, no execution (`src/sif/search/rerank.py:194-204`) | closed |
| T-04-05 | Denial of Service | LlamaCppReranker with large n_ctx | medium | mitigate | `n_ctx: int = 512` constructor default bounds context memory (`src/sif/search/rerank.py:58,82`); CrossEncoder `max_length=512` (`rerank.py:176,178`) | closed |
| T-04-05b | Tampering | QueryExpansion._get_expansion_terms | low | accept | Terms are embedded and compared locally; no external API call that could be injected | closed |
| T-04-06 | Denial of Service | QueryExpansion with large query | medium | mitigate | Query split on whitespace bounds term count (`src/sif/search/expansion.py:85`); embedding batch size controlled by EmbeddingManager | closed |
| T-04-07 | Information Disclosure | SmartSnippetExtractor | low | accept | Operates on indexed content only; no user data exposure | closed |
| T-04-08 | Tampering | _parse_query_prefix | low | accept | Prefix stripping is a simple string operation; no injection risk | closed |
| T-04-09 | Tampering | _generate_hypothetical_document | low | mitigate | Raises RuntimeError when embedder lacks generate()/create_completion() — no silent fallback (`src/sif/search/hybrid.py:289-326`) | closed |
| T-04-10 | Denial of Service | candidate_limit | medium | mitigate | Default 20; CLI caps at 200 via `click.IntRange(1, 200)` (`src/sif/cli/commands/search.py:380`) | closed |
| T-04-11 | Information Disclosure | --explain scores | low | accept | Local-first tool; internal scores are acceptable debug output | closed |
| T-04-12 | Tampering | QueryExpansion with intent prefix | low | accept | Intent is prepended as plain string; no structured prompt injection risk | closed |
| T-04-13 | Tampering | Fixture JSON parsing | low | mitigate | `json.load()` only — no code execution from user-provided fixture (`src/sif/cli/commands/bench.py:69`) | closed |
| T-04-14 | Denial of Service | Large fixture file | medium | mitigate | SearchEvaluator validates structure and raises ValueError on malformed fixtures (`src/sif/search/benchmark.py:58-63`) | closed |
| T-04-15 | Information Disclosure | Fixture contains sensitive docids | low | accept | Fixture is user-provided and local; no external exposure | closed |
| T-04-16 | Tampering | Mock sqlite3 connections in tests | low | accept | Tests use MagicMock; no real database operations | closed |
| T-04-17 | Information Disclosure | Test fixtures with sample docids | low | accept | Test data is synthetic and local | closed |

*Status: open · closed · open — below high threshold (non-blocking)*
*Severity: critical > high > medium > low — only open threats at or above workflow.security_block_on count toward threats_open*
*Disposition: mitigate (implementation required) · accept (documented risk) · transfer (third-party)*

---

## Accepted Risks Log

| Risk ID | Threat Ref | Rationale | Accepted By | Date |
|---------|------------|-----------|-------------|------|
| AR-04-02 | T-04-02 | Scores reveal internal model behavior; local-first tool | Plan-time register | 2026-04-17 |
| AR-04-05b | T-04-05b | Local embedding only; no injectable external API | Plan-time register | 2026-04-17 |
| AR-04-07 | T-04-07 | Indexed content only; no user data exposure | Plan-time register | 2026-04-17 |
| AR-04-08 | T-04-08 | Simple string prefix stripping | Plan-time register | 2026-04-17 |
| AR-04-11 | T-04-11 | Internal scores acceptable as local debug output | Plan-time register | 2026-04-17 |
| AR-04-12 | T-04-12 | Plain-string intent prefix; no structured prompt | Plan-time register | 2026-04-17 |
| AR-04-15 | T-04-15 | User-provided local fixture; no external exposure | Plan-time register | 2026-04-17 |
| AR-04-16 | T-04-16 | MagicMock tests; no real DB operations | Plan-time register | 2026-04-17 |
| AR-04-17 | T-04-17 | Synthetic local test data | Plan-time register | 2026-04-17 |

*Accepted risks do not resurface in future audit runs.*

---

## Security Audit Trail

| Audit Date | Threats Total | Closed | Open | Run By |
|------------|---------------|--------|------|--------|
| 2026-09-04 | 18 | 18 | 0 | gsd execute-phase 04 (ASVS L1 grep-depth) |

---

## Sign-Off

- [x] All threats have a disposition (mitigate / accept / transfer)
- [x] Accepted risks documented in Accepted Risks Log
- [x] `threats_open: 0` confirmed
- [x] `status: verified` set in frontmatter

**Approval:** verified 2026-09-04
