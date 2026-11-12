---
phase: "16"
slug: "bench-expansion-reranker-tuning"
status: verified
# threats_open = count of OPEN threats at or above workflow.security_block_on severity (the blocking gate)
threats_open: 0
asvs_level: 1
created: "2026-11-12"
verified: "2026-11-12"
---

# Phase 16 — Security

> Per-phase security contract: threat register, accepted risks, and audit trail.
> Verified by /gsd-secure-phase 16 on 2026-11-12 (ASVS L1, block_on high).
> Register authored at plan time (all 6 PLANs carry STRIDE `<threat_model>` blocks); L1 grep-depth
> verification confirmed every mitigation present in the implementation. threats_open: 0.
> Retroactive run — the v1.1 completion audit flagged this SECURITY.md missing despite the plan-time registers.

---

## Trust Boundaries

| Boundary | Description | Data Crossing |
|----------|-------------|---------------|
| bench fixture file → SearchEvaluator | Untrusted JSON fixture (malformed/empty queries) crosses into evaluation | JSON, query strings |
| relevance keys / corpus_root → path resolution | Relevance keys must not traverse outside the declared corpus root | filesystem paths |
| committed corpus pack → repository | Synthetic pack must contain no real user KB content | document text |
| settings/env → rerank configuration | Out-of-range cap/alpha must not widen rerank fan-out | config values |
| sweep grid → ranking / split guard | Held-out queries must never influence tuning ranking | query split labels |
| heldout snapshot → default-lock test | Defaults must not drift without held-out evidence | metric snapshot |

---

## Threat Register

| Threat ID | Category | Component | Severity | Disposition | Mitigation | Status |
|-----------|----------|-----------|----------|-------------|------------|--------|
| T-16-01 | Denial of Service | SearchPipeline rerank fan-out / SIF_RERANK_CANDIDATE_LIMIT | high | mitigate | Every CLI path resolves candidate_limit through resolve_candidate_limit (int-only, clamped 5..50, settings.py:399); -C 200 → 50 before SearchOptions; over-fetch only to max(limit+offset, cap); Pydantic-bounded; rerank opt-in (default false). Verified: 5 call sites. | closed |
| T-16-02 | Denial of Service | SearchEvaluator fixture load | medium | mitigate | json.load inside bench_cmd try block; malformed JSON / empty queries raise ValueError → ClickException (non-zero exit); no unbounded loop from fixture text. Verified. | closed |
| T-16-03 | Tampering / Information Disclosure | result_key / corpus_root | medium | mitigate | resolve_corpus_root (benchmark.py:159) resolves the declared root once; Path.relative_to/as_posix for comparison only; never opens a relevance key/result path; POSIX-string fallback on ValueError. Verified. | closed |
| T-16-04 | Information Disclosure | tests/fixtures/bench/corpus | high | mitigate | Pack generated from seeded synthetic word lists only (generate_bench_fixture.py, 13 seed refs); README/review enforce no-real-KB rule (D-01); no user paths/personal content read during generation. Verified. | closed |
| T-16-05 | Tampering | relevance key path resolution | medium | mitigate | Contract tests reject absolute keys, `..` segments, and keys resolving outside corpus_root (test_bench_fixture.py); builder never opens a relevance key, only corpus files under root. Verified. | closed |
| T-16-06 | Tampering | sweep ranking / split guard | high | mitigate | _run_sweep filters split == "tuning" before any search (bench.py:249); spy tests prove a held-out query string is never seen; rank_sweep accepts only mean tuning nDCG@10. Verified. | closed |
| T-16-07 | Denial of Service | sweep CPU cost | low | accept | Fixed 45-config grid (no user-defined grid, D-07); query embeddings memoized; cost bounded and minute-scale on the reference corpus; no unbounded user input reaches the loop. Accepted risk — see log. | closed |
| T-16-08 | Tampering | heldout_defaults.json / default-lock test | high | mitigate | Snapshot recomputed from the deterministic index and asserted equal (test_bench_snapshot.py); default-lock test ties Settings defaults to the snapshot — editing a default or masking a regression fails CI; verdict fields make "no evidence" explicit. Verified. | closed |
| T-16-09 | Tampering | settings/env → rerank configuration | medium | mitigate | Pydantic Field(ge=MIN, le=MAX) cap and Field(gt=0, le=1) alpha reject out-of-range at settings load; query_cmd converts ValidationError → ClickException; resolve_candidate_limit int-only clamp 5..50 (non-int → default 20). Verified. | closed |
| T-16-SC | Tampering | package installs | high | mitigate | No package installs this phase; pyproject.toml dependency sections untouched (last change 10d652a was Phase 12's watchdog cap, not Phase 16); generator stdlib-only. Any later install requires the legitimacy gate + blocking human checkpoint. Verified. | closed |

*Status: open · closed · open — below high threshold (non-blocking)*
*Severity: critical > high > medium > low — only open threats at or above workflow.security_block_on count toward threats_open*
*Disposition: mitigate (implementation required) · accept (documented risk) · transfer (third-party)*

---

## Accepted Risks Log

| Risk ID | Threat Ref | Rationale | Accepted By | Date |
|---------|------------|-----------|-------------|------|
| AR-16-01 | T-16-07 | Sweep CPU cost is bounded by construction: fixed 45-config declared grid (D-07, no user-defined grid flag) and memoized query embeddings; minute-scale on the reference micro-corpus; no unbounded user input reaches the loop. Local single-user tool — no DoS surface from a user-controlled grid. | plan-time decision D-07 (Phase 16 CONTEXT) | 2026-11-08 |

*Accepted risks do not resurface in future audit runs.*

---

## Security Audit Trail

| Audit Date | Threats Total | Closed | Open | Run By |
|------------|---------------|--------|------|--------|
| 2026-11-12 | 10 | 10 | 0 | /gsd-secure-phase 16 (L1 grep-depth, register authored at plan time; retroactive) |

---

## Sign-Off

- [x] All threats have a disposition (mitigate / accept / transfer)
- [x] Accepted risks documented in Accepted Risks Log (AR-16-01 / T-16-07)
- [x] `threats_open: 0` confirmed
- [x] `status: verified` set in frontmatter

**Approval:** verified 2026-11-12

## Security Audit 2026-11-12

| Metric | Count |
|---|---|
| Threats found | 10 |
| Closed | 10 |
| Open | 0 |
