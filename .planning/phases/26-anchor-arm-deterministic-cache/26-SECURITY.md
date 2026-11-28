---
phase: "26"
slug: "anchor-arm-deterministic-cache"
status: verified
# threats_open = count of OPEN threats at or above workflow.security_block_on severity (the blocking gate)
threats_open: 0
asvs_level: 1
created: "2026-11-28"
---

# Phase 26 — Security

> Per-phase security contract: threat register, accepted risks, and audit trail.
>
> Register authored at plan time: **yes** — all four plans (`26-01`…`26-04`) carry a parseable
> `<threat_model>` block, so this run verifies existing mitigations and did not construct a
> retroactive register. `workflow.security_block_on: high`, `workflow.security_asvs_level: 1`.
> At ASVS L1 with zero open threats the workflow's short-circuit applied: no auditor subagent
> was spawned. Every row below was re-checked against the implementation in this run.

---

## Trust Boundaries

| Boundary | Description | Data Crossing |
|----------|-------------|---------------|
| User query text → FTS5 `MATCH` expression | Raw query and rule anchors cross into SQLite FTS5 query syntax (`26-01`) | Search terms; no persistence |
| CLI/MCP prefix text → retrieval route | `anchor:` / `lex:` prefixes decide which retrieval leg runs (`26-01`) | Control input only |
| MCP request → user's primary DB | The read-only tool surface must not write cache or index (`26-01`, `26-04`) | Search terms in; results out; no writes |
| User query → local/remote generator prompt | Query text enters the model prompt and `llm_cache.prompt` (`26-02`) | Search terms persisted locally (TTL-bounded) |
| User query → remote HTTP endpoint | Query text leaves the host after explicit opt-in (`26-02`) | Search terms, cross-host — user-visible disclosure |
| Generator output → FTS anchor terms | Model output is treated as candidate terms injected into BM25 (`26-02`) | Untrusted text → query syntax |
| Cache row → parser | Historical or malformed JSON may be read back as terms (`26-02`) | Untrusted local storage |
| 45-config sweep → generator | Repeated generation can amplify into 45N calls (`26-02`) | Cost/availability |
| CLI flag/prefix → retrieval route | User input decides ANCHOR routing and whether a model is constructed (`26-03`) | Control input only |
| Pipeline run metadata → stdout/stderr | Cost metadata must not pollute machine-readable output (`26-03`) | Diagnostics only |
| Anchor terms → FTS vocabulary probe | Terms enter a `MATCH` expression for existence probing (`26-04`) | Search terms |
| Vocabulary-guard switch → default behaviour | One default value could silently move the experimental baseline (`26-04`) | Configuration |
| Package build → user disk | Packaged content could carry a ~1.1 GB weight file or license-restricted assets (`26-04`) | Distribution artifacts |
| License text → user decision | Docs could omit the revenue threshold or redistribution obligations (`26-04`) | Legal/decision text |

---

## Threat Register

| Threat ID | Category | Component | Severity | Disposition | Mitigation | Status |
|-----------|----------|-----------|----------|-------------|------------|--------|
| T-26-01 | Tampering | `BM25Searcher._build_fts_query` anchor concatenation | high | mitigate | `_sanitize_term` (`src/sif/search/bm25.py:32-46`) strips FTS metacharacters and wraps each anchor as a quoted phrase; anchors are only ever OR-appended (`bm25.py:278-281`); all 4 `MATCH` sites remain parameter-bound | closed |
| T-26-02 | Tampering | `PREFIX_ROUTES` / MCP route drift | medium | mitigate | One module-level constant (`src/sif/search/hybrid.py:43-49`) imported directly by `src/sif/mcp/backend.py:34`; `_prefix_route` (`backend.py:206`) strips exactly one prefix layer | closed |
| T-26-03 | Information disclosure / Tampering | MCP `anchor:` branch | high | mitigate | `_prefix_route` returns (`backend.py:543-545`) **before** `self._ensure_embedder()` (`backend.py:547`); no resolver is constructed and no `llm_cache` write occurs; verified by `llm_cache` row count 0 in the phase tests and on a live temp DB | closed |
| T-26-04 | Information disclosure | `llm_cache.prompt` and local cache | medium | mitigate | Only the normalized query is stored, under the `anchor::<backend>::<model_id>` namespace (`src/sif/search/anchor.py:367`); TTL via `anchor_cache_ttl` (default 30 days, `anchor.py:799`); `sif cleanup` calls `LLMCacheRepository.clear_expired()` (`src/sif/cli/main.py:239+`, `src/sif/database/repositories.py:695-729`); the MCP path never writes | closed |
| T-26-05 | Information disclosure | `OpenAICompatibleGenerator` egress | high | mitigate | Backend allow-list `_ANCHOR_BACKENDS = {rules, gguf, openai}` (`anchor.py:274`); remote requires explicit `anchor_api_base` + `anchor_api_model`; one-time stderr disclosure per `base_url` (`_warn_egress_once`, `anchor.py:428-435`); tests monkeypatch sockets and assert default/fake paths open none | closed |
| T-26-06 | Tampering | Generator output injected into FTS | high | mitigate | `parse_terms` (`anchor.py:400-421`) enforces `MAX_ANCHOR_TERMS=10`, `MAX_TERM_CHARS=64` (`:261`), `MAX_TERM_WORDS=6` (`:262`), requires an alnum/CJK character, dedupes; the surviving terms pass `_sanitize_term` again at the FTS boundary; model output is never executed | closed |
| T-26-07 | Denial of service | 45N repeated generation / over-long generation | high | mitigate | `SIF_ANCHOR_MAX_CALLS` hard budget raises before generating (`_check_budget`, `anchor.py:736-742`); `_DEFAULT_MAX_TOKENS=64` (`:278`); monotonic per-attempt deadline (`:528`); HTTP timeout; the cache collapses 45N into N | closed |
| T-26-08 | Tampering | Cache poisoning / malformed response | medium | mitigate | `_parse_cached` (`anchor.py:381-397`) trusts only `{"version": CACHE_RESPONSE_VERSION, "terms": [str, ...]}`; anything else is a miss that gets regenerated and overwritten; the function never raises | closed |
| T-26-09 | Tampering / Denial of service | `query_cmd` anchor route | high | mitigate | Route-first decision at `src/sif/cli/commands/search.py:1267-1290`; the ANCHOR branch sets `manager=None` / `embedder=None` (`:1309-1315`) and never reaches `EmbeddingManager.from_settings` (`:1320+` is the non-anchor branch); the rejection path also precedes any construction; tests patch `from_settings` to `AssertionError` | closed |
| T-26-10 | Information disclosure | `--explain` metadata and JSON output | medium | mitigate | The anchor line is printed only through `console_err.print` and only when `explain` (`search.py:1413-1422`); `SearchResult.to_dict()` has no anchor keys (0 matches in `src/sif/core/models.py`); `--explain --json` stdout parses as JSON in tests | closed |
| T-26-11 | Tampering | Vocabulary guard vs. rule-anchor baseline | medium | mitigate | `anchor_vocab_guard: bool = Field(default=False)` (`src/sif/config/settings.py:266-270`), so the guard cannot move the baseline unless explicitly enabled; tests assert the default term list is byte-identical to `derive_rule_anchors(normalize_query(q))` and that the deviation is documented | closed |
| T-26-12 | Tampering / Information disclosure | GGUF assets and packaging | high | mitigate | Three static guards in `tests/test_packaging_assets.py`; verified in this run: `git ls-files -- '*.gguf'` empty, `find src/sif -name '*.gguf'` empty, `pyproject.toml` contains no `.gguf`; docs state weights are user-supplied, never downloaded or packaged | closed |
| T-26-13 | Tampering | MCP read-only contract | high | mitigate | The guard filters the term list in memory (`filter_known_terms`) inside the ANCHOR branch (`backend.py:225-234`); no resolver, no cache write, no embedder; tests assert `llm_cache` rows 0 and `_ensure_embedder` uncalled with the guard both on and off | closed |
| T-26-SC | Tampering | Dependency installation | high | mitigate | Zero new dependencies across the phase (declared in all four plans); `git diff v1.2.5..HEAD -- pyproject.toml uv.lock` is empty this run; the remote backend uses stdlib `urllib.request` | closed |

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
| 2026-11-28 | 14 | 14 | 0 | orchestrator (L1 grep-depth + re-executed phase tests; auditor skipped by the ASVS-L1 / zero-open short-circuit) |

---

## Sign-Off

- [x] All threats have a disposition (mitigate / accept / transfer)
- [x] Accepted risks documented in Accepted Risks Log (none)
- [x] `threats_open: 0` confirmed
- [x] `status: verified` set in frontmatter

**Approval:** verified 2026-11-28
