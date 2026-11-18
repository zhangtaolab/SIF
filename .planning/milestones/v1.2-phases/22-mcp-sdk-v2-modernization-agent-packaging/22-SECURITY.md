---
phase: "22"
slug: "mcp-sdk-v2-modernization-agent-packaging"
status: verified
threats_open: 0
asvs_level: 1
created: "2026-11-18"
verified: "2026-11-18"
---

# Phase 22 — Security

> Per-phase security contract: threat register, accepted risks, and audit trail.
> Verified by /gsd-secure-phase 22 on 2026-11-18 (ASVS L1, block_on high).
> Register authored at plan time: all seven PLANs carry STRIDE `<threat_model>` blocks.
> 25 unique threats (T-22-01…T-22-24 + T-22-SC); all `mitigate`, none accepted or transferred.

---

## Trust Boundaries

| Boundary | Description | Data Crossing |
|----------|-------------|---------------|
| SDK dependency ↔ build | A pinned third-party package is installed after legitimacy review | Package name, version, hashes |
| MCP client eras ↔ server | Five protocol eras share one SDK composition root | JSON-RPC frames, session ids, headers |
| HTTP client ↔ transport | Host/Origin headers gate DNS-rebinding protection | Host, Origin, allowlists |
| process stdout ↔ protocol | Only JSON-RPC frames may reach stdout | Protocol frames, log text |
| agent ↔ tool surface | Seven read tools with annotations and structured output | Args, ToolError messages |
| MCP client ↔ filter/match payload | Untrusted JSON crosses into the shared validator | Filter AST, match grammar |
| DB ↔ citation resource | Documents are resolved by repository id, never by path | Content, checksums, line windows |
| plugin/skills ↔ host | Read-only `mcp__sif__` tools and untrusted-content warnings | Skill text, allowed tools |
| maintainer ↔ Registry | Auth is delegated to `mcp-publisher`; no credentials stored | Registry URL, identity |

---

## Threat Register

| Threat ID | Category | Component | Severity | Disposition | Mitigation | Status |
|-----------|----------|-----------|----------|-------------|------------|--------|
| T-22-01 | Tampering | `mcp` dependency | high | mitigate | `mcp>=2.3.0,<3` pinned and hash-locked from PyPI (`pyproject.toml:42`; `uv.lock:1044-1067`); maintainer legitimacy checkpoint recorded | closed |
| T-22-02 | Spoofing/Tampering | SDK shell swap | high | mitigate | Old transports/shell deleted, zero references; CLI rewired to `sif.mcp.cli` → `app.run_stdio`/`run_http_host`; five era goldens; SDK client matrix | closed |
| T-22-03 | Spoofing | protocol era matrix | high | mitigate | Four legacy eras + modern-era wire transcripts with session/`Mcp-Name` assertions; modern request without `_meta` rejected; no hand-rolled version allowlist | closed |
| T-22-04 | DoS | stdout purity | high | mitigate | `set_quiet(True)` first statement of `run_stdio`; zero `print(` in `src/sif/mcp`; cold-stdio protocol-only test | closed |
| T-22-05 | Elevation of Privilege | tool annotations | high | mitigate | `read_only_hint=True, open_world_hint=False` on exactly seven registrations; honesty test; future-write policy helper | closed |
| T-22-06 | Tampering/Info Disclosure | ToolError mapping | high | mitigate | Shared parsers map validation failures to `ToolError`; `RuntimeError` remedy mapped; no internal detail leaked | closed |
| T-22-07 | Spoofing | HTTP transport security | high | mitigate | Explicit `TransportSecuritySettings` always passed; `_merge_allowlist` drops `*`; Host 421 / Origin 403 matrix; `/health` Host guard fail-closed | closed |
| T-22-08 | Spoofing/DoS | MCP PID artifact | high | mitigate | 0600 `O_CREAT`, per-PID temp then `os.replace`; fail-closed corroboration with marker token; distinct `.mcp.pid` vs `.watch.pid` | closed |
| T-22-09 | DoS/Tampering | lazy embedder | high | mitigate | Single load lock + latch, one warning; model-free routes never load; dimension carried from the loaded model | closed |
| T-22-10 | DoS | per-request pipeline | medium | mitigate | Per-request `SearchPipeline` reusing hoisted components; rerank failure soft-degrades with one warning; vec-unavailable BM25 carve-out | closed |
| T-22-11 | Tampering | citation resource template | high | mitigate | `docs://{doc_id}{?from_line,max_lines}` resolves via repositories only, never the filesystem; SDK path-traversal rejection inspected; tests | closed |
| T-22-12 | Repudiation/Tampering | citation integrity | medium | mitigate | `content_hash` from stored checksums; batched page hashes; `vectors_stale` metadata; `sif-cite` mandates `get` before citing | closed |
| T-22-13 | Elevation of Privilege/Tampering | plugin/`.mcp.json` | high | mitigate | `.mcp.json` has no env/paths/credentials; plugin/marketplace names only `sif`; skills list only `mcp__sif__` read tools; untrusted-content warning in each | closed |
| T-22-14 | Repudiation | misleading docs | medium | mitigate | `docs/mcp-server.md` states annotations do not auto-approve; rerank opt-in documented; install path recorded | closed |
| T-22-15 | Information Disclosure | Registry script credentials | high | mitigate | Auth delegated to `mcp-publisher`; no token/password/secret reading or printing; credential-key source scan | closed |
| T-22-16 | Tampering/Spoofing | Registry identity/preflight | high | mitigate | Exact `io.github.zhangtaolab/sif`; README marker equality; PyPI existence; server.json name/version/package/transport checks; duplicate pre-check; version 1.1.2 | closed |
| T-22-17 | Tampering | embedded watch host | medium | mitigate | Session manager entered before watcher start; watcher stopped in `finally`; flush→checkpoint→close on stop | closed |
| T-22-18 | Tampering | filter threading through MCP | medium | mitigate | `filter_node` passed explicitly into `SearchOptions`; SQL layer parameterized | closed |
| T-22-19 | DoS | daemon bind failure | medium | mitigate | Arm then bind; `finally` removes PID; bind-failure cleanup test propagates non-zero | closed |
| T-22-20 | DoS | cold-first-query noise | high | mitigate | Quiet at both roots; no `print(` in `src/sif/mcp`; migration notice on stderr; cold subprocess emits only JSON-RPC frames | closed |
| T-22-21 | Information Disclosure | `get` content scope | low | mitigate | `get_document` returns only stored content; no new filesystem read surface; line windows from fetched content | closed |
| T-22-22 | Information Disclosure | citation skill discipline | medium | mitigate | Two-stage search→get; "never cite a snippet alone"; hash-mismatch and staleness caveats surfaced | closed |
| T-22-23 | DoS | Registry duplicate publish | medium | mitigate | Registry lookup before publish; `already listed` exits 0; 404 is the only publish path | closed |
| T-22-24 | Tampering | old-shell residue | medium | mitigate | Old shell deleted with zero import references; `_METADATA_ENVELOPE` oracle ported with equality assertions | closed |
| T-22-SC | Tampering | package installs | high | mitigate | Only declared new dependency is the official `mcp` SDK, hash-locked from PyPI; no git/URL sources | closed |

*Status: open · closed · open — below high threshold (non-blocking)*

---

## Accepted Risks Log

No accepted risks. (The interrupted public Registry publish is a maintainer decision recorded in `22-07-SUMMARY.md`, not a security risk acceptance; the credential-free preflight is green.)

---

## Security Audit Trail

| Audit Date | Threats Total | Closed | Open | Run By |
|------------|---------------|--------|------|--------|
| 2026-11-18 | 25 | 25 | 0 | /gsd-secure-phase 22 (gsd-security-auditor, ASVS L1) |

---

## Sign-Off

- [x] All threats have a disposition (mitigate / accept / transfer)
- [x] Accepted risks documented in Accepted Risks Log
- [x] `threats_open: 0` confirmed
- [x] `status: verified` set in frontmatter

**Approval:** verified 2026-11-18 — 25/25 threats closed at L1; 0 open at or above `high`.
