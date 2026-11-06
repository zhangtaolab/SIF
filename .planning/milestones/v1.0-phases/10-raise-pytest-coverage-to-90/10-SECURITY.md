---
phase: "10"
slug: "raise-pytest-coverage-to-90"
status: verified
# threats_open = count of OPEN threats at or above workflow.security_block_on severity (the blocking gate)
threats_open: 0
asvs_level: 1
created: "2026-11-07"
---

# Phase 10 — Security

> Per-phase security contract: threat register, accepted risks, and audit trail.
> Retroactive reconstruction at milestone v1.0 close (2026-11-07): the register is assembled
> from the `<threat_model>` blocks of plans 10-01..10-07 (register authored at plan time —
> seven of seven plans carry threat models). The phase's deliverables are TESTS; its threat
> surface is the test infrastructure itself (what tests may touch, install, or leak).

---

## Trust Boundaries

| Boundary | Description | Data Crossing |
|----------|-------------|---------------|
| Tests → filesystem | Test fixtures write indexes, caches, and synthetic file trees | Must stay inside tmp_path — never the developer's real project/home |
| Tests → network / package registry | ML dependencies and model downloads | No real weights, no installs, no external clients may execute |
| Tests → process state | sys.modules injection, env vars, HOME, logging, settings cache | Pollution must fail reproducibly, not silently leak across tests |

---

## Threat Register

| Threat ID | Category | Component | Severity | Disposition | Mitigation / Rationale | Status |
|-----------|----------|-----------|----------|-------------|------------------------|--------|
| T-10-01 | Tampering | Dead-code deletion (plan 10-01) | high | mitigate | D-01 fixes the exact deletion set; import probes cover both formatter consumers; complete suite + ruff green before re-baselining (executed: 1014 passed today) | closed |
| T-10-SC | Tampering | Package installs (per-plan supply-chain gate, all 7 plans) | high | mitigate | No installs planned; any newly required package stops execution for the blocking-human registry-legitimacy gate — none triggered through execution | closed |
| T-10-02 | Tampering | CLI temp-DB fixtures (10-02) | high | mitigate | Every invocation uses a tmp_path index; assertions inspect only temporary stores | closed |
| T-10-03 | Tampering | OpenAI/Settings test isolation (10-02) | high | mitigate | D-06 isolated + both-order probes ran green; D-07 monkeypatch at lookup sites + cache clearing (get_settings.cache_clear in fixtures, verified live in test_get.py) | closed |
| T-10-04 | Information Disclosure | Reranker ML mocks (10-03) | high | mitigate | transformers/sentence-transformers/downloader patched at actual lookup sites; tmp_path model dirs; no real weights or network | closed |
| T-10-05 | Tampering | Search output tests (10-03) | medium | mitigate | Parse JSON/XML and assert escaped markup-sensitive fixture content — output integrity, not just invocation (pattern extended by today's TestMarkupLiteralContent regressions) | closed |
| T-10-06 | Tampering | Real SQL and cache fixtures (10-04) | high | mitigate | All persistent paths tmp_path children, other connections :memory:; rollback/migration assertions prove only fixture data changes | closed |
| T-10-07 | Information Disclosure | ModelDownloader tests (10-05) | high | mitigate | modelscope.snapshot_download and HubApi patched at source modules, kwargs asserted; no external client executes | closed |
| T-10-08 | Tampering | cache/HOME/logging fixtures (10-05) | high | mitigate | Explicit tmp_path cache_dir, monkeypatched HOME/env, sys.modules and logging teardown — behavior tests repaired the custom formatter and Rich progress defects | closed |
| T-10-09 | Information Disclosure | Parser/scanner fixtures (10-06) | medium | mitigate | Synthetic tmp_path file trees only; no test touches a real project/home directory (real-file Unicode parsing + exact code-point boundaries) | closed |

---

## Accepted Risks

- None.

---

## Security Audit

| Metric | Count |
|---|---|
| Threats found | 10 (T-10-SC deduplicated from its per-plan occurrences) |
| Closed | 10 |
| Open | 0 |
