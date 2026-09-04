---
phase: "03"
slug: "embedding-vector-search"
status: verified
# threats_open = count of OPEN threats at or above workflow.security_block_on severity (the blocking gate)
threats_open: 0
asvs_level: 1
created: "2026-09-04"
---

# Phase 03 — Security

> Per-phase security contract: threat register, accepted risks, and audit trail.

> Register authored at plan time (all 8 PLANs carry `<threat_model>` blocks);
> verified 2026-09-04 at ASVS L1 (grep-depth + live UAT evidence) per the
> threats_open=0 short-circuit rule — no open threats, no auditor escalation.

---

## Trust Boundaries

| Boundary | Description | Data Crossing |
|----------|-------------|---------------|
| Environment variables / .env → Settings | Untrusted user input crosses into application config | SIF_API_KEY (secret), SIF_API_BASE (URL), model config |
| Settings → EmbeddingManager → OpenAI SDK | API key flows from config into third-party client | api_key (secret) |
| SIF process → remote OpenAI-compatible endpoint | Document/chunk text crosses to a third-party service | User content (sensitive — opt-in only) |
| Remote endpoint → SIF process | Embedding arrays / dimensions are external input | Float vectors, dimension ints |
| Factory → sqlite-vec (vec0 virtual table) | Embedding vectors and DELETE statements cross into the SQLite extension | Local index data |
| pip supply chain → venv | Optional `openai` extra executes third-party package installation | Package code |

---

## Threat Register

| Threat ID | Category | Component | Severity | Disposition | Mitigation | Status |
|-----------|----------|-----------|----------|-------------|------------|--------|
| T-03-01-01 | Information Disclosure | Settings.api_key | medium | mitigate | `Field(..., repr=False, exclude=True)` (settings.py:70-75) — key excluded from repr/serialization | closed |
| T-03-01-02 | Spoofing | Settings.api_base | low | mitigate | `validate_api_base` rejects non-HTTP(S) schemes, SSRF guard (settings.py:168-175) | closed |
| T-03-02-01 | Information Disclosure | OpenAIEmbedder._client | low | accept | api_key passed solely to `openai.OpenAI()` constructor; SDK handles it securely | closed |
| T-03-02-02 | Tampering | OpenAIEmbedder._dim_cache_file | low | accept | Cache in user-owned cache dir; no integrity requirement for dimension cache | closed |
| T-03-03-01 | Denial of Service | SchemaManager dim-mismatch RuntimeError | low | accept | Fail-fast is intentional; user rebuilds index after model change | closed |
| T-03-04-01 | Tampering | Embedding JSON serialization → sqlite-vec | low | accept | sqlite-vec parses JSON arrays; local documents are not a security boundary | closed |
| T-03-05-01 | Information Disclosure | EmbeddingManager._config.api_key | low | accept | EmbeddingConfig already `exclude=True, repr=False` (models/embedding.py:35); no new logging | closed |
| T-03-06-01 | Denial of Service | embed_cmd batch size | low | accept | Bounded by Settings.batch_size; no unbounded memory risk | closed |
| T-03-06-02 | Information Disclosure | query_cmd embedder error messages | low | accept | ImportError strings contain package names only, no secrets | closed |
| T-03-01 (03-07) | Information Disclosure | api_key handling in embedder/factory | medium | mitigate | Never logged/interpolated/repr'd; constructor-arg only (embedder.py:289,315; factory.py:79; manager.py:62,90) | closed |
| T-03-02 (03-07) | Spoofing | api_base → remote endpoint | low | mitigate | Only the validated value consumed via SDK base_url; no URL assembly (embedder.py:315) | closed |
| T-03-03 (03-07) | Tampering | Remote response (ragged batches, dim drift) | medium | mitigate | Per-slice length + index validation raising RuntimeError (embedder.py:406-418); dim fail-fast at load (index.py:294-305, WR-02) | closed |
| T-03-04 (03-07) | Information Disclosure | Document text egress to remote endpoint | high | mitigate | Strictly opt-in: OpenAIEmbedder reachable only via explicit `model_type=openai`; local backends make no content-bearing calls — confirmed live in UAT test 4 (full-repo egress audit) | closed |
| T-03-05 (03-07) | Denial of Service | Hung/absent endpoint stalls CLI | low | accept | SDK default timeouts/retries; hard failure surfaces as explicit error (fail-fast, no silent fallback — live-confirmed in UAT test 5) | closed |
| T-03-SC (03-07) | Tampering | pip install of `openai` extra | high | mitigate | Official OpenAI publisher, Trusted Publishing, Apache-2.0; version floor `openai>=2.0.0` declared (pyproject.toml:55-63) | closed |
| T-03-08-01 | Tampering | document_embeddings integrity (orphaned vec0 rows) | medium | mitigate | Delete-before-insert in the re-chunk transaction + chunk-id-set completeness check (index.py:362-366) — live-confirmed 2026-09-04 UAT test 3 (4 runs, 0 orphans) | closed |
| T-03-08-02 | Tampering | delete_embeddings_by_document SQL construction | low | mitigate | Fully parameterized SQL, single `?` placeholder (vector.py:201-202); unit test inspects executed SQL | closed |
| T-03-08-03 | Denial of Service | Repeat embed runs re-billing remote backends | low | mitigate | Default run skips fully embedded docs with zero embedding calls; re-embed opt-in via `--force` — live-confirmed 2026-09-04 UAT tests 3/7 (proxy request counts) | closed |
| T-03-08-04 | Tampering | Concurrent SIF processes on one database | low | accept | SQLite writer locking serializes transactions; exact per-document replacement converges instead of accumulating orphans | closed |

*Status: open · closed · open — below high threshold (non-blocking)*
*Severity: critical > high > medium > low — only open threats at or above workflow.security_block_on count toward threats_open*
*Disposition: mitigate (implementation required) · accept (documented risk) · transfer (third-party)*

---

## Accepted Risks Log

| Risk ID | Threat Ref | Rationale | Accepted By | Date |
|---------|------------|-----------|-------------|------|
| AR-03-01 | T-03-02-01 | api_key handled by official openai SDK after constructor handoff | Plan 03-02 | 2026-04 |
| AR-03-02 | T-03-02-02 | Dimension cache has no integrity requirement (user-owned dir) | Plan 03-02 | 2026-04 |
| AR-03-03 | T-03-03-01 | Fail-fast on dim mismatch is intended UX; rebuild is the remedy | Plan 03-03 | 2026-04 |
| AR-03-04 | T-03-04-01 | Local documents are not an adversarial boundary for a local-first tool | Plan 03-04 | 2026-04 |
| AR-03-05 | T-03-05-01 | No new logging added around EmbeddingConfig; field already excluded | Plan 03-05 | 2026-04 |
| AR-03-06 | T-03-06-01 | Batch size bounded by Settings; documented config ceiling | Plan 03-06 | 2026-04 |
| AR-03-07 | T-03-06-02 | Error strings carry package names only | Plan 03-06 | 2026-04 |
| AR-03-08 | T-03-05 (03-07) | SDK timeouts/retries sufficient; tunable timeout out of scope | Plan 03-07 | 2026-08 |
| AR-03-09 | T-03-08-04 | SQLite writer locking + idempotent replacement make concurrency safe enough | Plan 03-08 | 2026-09 |

*Accepted risks do not resurface in future audit runs.*

---

## Security Audit Trail

| Audit Date | Threats Total | Closed | Open | Run By |
|------------|---------------|--------|------|--------|
| 2026-09-04 | 19 | 19 | 0 | verify-work 03 (ASVS L1 short-circuit: plan-time register, grep-depth + live UAT evidence) |

---

## Sign-Off

- [x] All threats have a disposition (mitigate / accept / transfer)
- [x] Accepted risks documented in Accepted Risks Log
- [x] `threats_open: 0` confirmed
- [x] `status: verified` set in frontmatter

**Approval:** verified 2026-09-04
