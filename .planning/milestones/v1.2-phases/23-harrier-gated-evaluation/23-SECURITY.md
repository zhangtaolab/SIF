---
phase: "23"
slug: "harrier-gated-evaluation"
status: verified
threats_open: 0
asvs_level: 1
created: "2026-11-18"
verified: "2026-11-18"
---

# Phase 23 — Security

> Per-phase security contract: threat register, accepted risks, and audit trail.
> Verified by /gsd-secure-phase 23 on 2026-11-18 (ASVS L1, block_on high).
> Register authored at plan time: all six PLANs carry STRIDE `<threat_model>` blocks.
> 24 unique threats (T-23-01…T-23-23 + T-23-SC); all `mitigate`. The non-flip outcome
> (keep-qwen3) resolves the flip-conditional threats through their recorded
> `not-applicable` branches, which is a plan-authored path, not a gap.

---

## Trust Boundaries

| Boundary | Description | Data Crossing |
|----------|-------------|---------------|
| CLI flags ↔ held-out synthesis | `--require-language`/`--min-heldout` steer sampling | Language names, integer floors |
| saved run ↔ comparison gates | Recorded query sets feed per-language/per-leg gates | Query records, metrics, fingerprints |
| gate inputs ↔ verdict rule | A pure rule decides adopt/keep from gate results | Gate booleans, deltas, CI |
| harness env ↔ model arms | Per-arm env selects model, prompts, and cache bucket | Model name, revision, prompt names |
| scratch root ↔ filesystem | Cleanup and artifact writes are confined to a scratch root | Paths, DB files, saved runs |
| run artifact ↔ committed evidence | Only allowlisted fields reach the verdict JSON | Identities, costs, gates, adequacy |
| default config ↔ docs | A flip would change Settings and every default claim | Model id, docs text |

---

## Threat Register

| Threat ID | Category | Component | Severity | Disposition | Mitigation | Status |
|-----------|-----------|-----------|----------|-------------|------------|--------|
| T-23-01 | Tampering | `--require-language` input | low | mitigate | `click.Choice(LANGUAGES)`; values only reach `ensure_heldout`; compare mode warns and ignores; no SQL built from the flag | closed |
| T-23-02 | Spoofing | per-language gate partition | high | mitigate | Absent languages omitted, empty splits yield `n=0, sufficient=False`; thin/missing language is `insufficient-evidence`; partition tests | closed |
| T-23-03 | Tampering | saved-run gate inputs | medium | mitigate | Saved runs pass `load_saved_run` validation before grading; new gates group validated records only | closed |
| T-23-04 | Tampering | verdict rule | high | mitigate | `GateResult.winner` used verbatim, literal booleans recorded; 20-test boundary battery | closed |
| T-23-05 | Spoofing | artifact parsing | medium | mitigate | Payload/`splits` must be mappings, `heldout` required, named `ValueError`s; missing `language_splits` → insufficient-evidence | closed |
| T-23-06 | Elevation of Privilege | default flip | high | mitigate | Committed artifact `decision: keep-qwen3`, `default_flip: not-applicable`; checkpoint recorded; Settings stay Qwen3/modelscope | closed |
| T-23-07 | Spoofing | arm environment isolation | high | mitigate | Env removes model/DB/API/prompt overrides; identity gate; probe requires `ok`; stderr mismatch guard | closed |
| T-23-08 | Tampering | scratch cleanup | high | mitigate | Refuses `/`, home, outside scratch; deletes only run DBs/sidecars/baseline; `.planning/tmp/` gitignored; 11 cleanup tests | closed |
| T-23-09 | Information Disclosure | artifact allowlist | high | mitigate | Allowlisted fields only; scope labels basenamed; scan found no absolute paths or personal data | closed |
| T-23-10 | Tampering | model revision pinning | medium | mitigate | Harrier pinned by repo id; artifact records revision + fingerprint; cache bucket includes revision; identity check compares revision | closed |
| T-23-11 | Denial of Service | runbook resumability/cost | medium | mitigate | Scope-keyed state, per-stage timeouts, disk-headroom preflight | closed |
| T-23-12 | Spoofing | adequacy preflight | high | mitigate | Adequacy runs before any embed; inadequate path writes `insufficient-evidence` and returns 3, never marks the stage complete | closed |
| T-23-13 | Information Disclosure | docs evidence | high | mitigate | Docs section contains aggregate numbers and basenames only; no personal paths or query text | closed |
| T-23-14 | Tampering | arm corpus identity | medium | mitigate | Refuses arm fingerprint/document mismatch; `require_matching_corpus` used in compare paths | closed |
| T-23-15 | Repudiation | evidence completeness | medium | mitigate | Artifact records both identities, corpus/query-set fingerprints, env, per-arm costs, literal rule booleans; overwrite guard | closed |
| T-23-16 | Spoofing | flip decision | high | mitigate | Non-flip outcome recorded; Settings/EmbeddingConfig defaults unchanged | closed |
| T-23-17 | Tampering | Qwen3-built indexes after flip | high | mitigate | Flip-only; no flip occurred, so Qwen3 default and prompt-free path remain as shipped | closed |
| T-23-18 | Repudiation | default-claim docs | medium | mitigate | Flip-only doc sweep not applicable; no default claim changed | closed |
| T-23-19 | Information Disclosure | `default_flip` block | medium | mitigate | Block carries only decision/artifact/reason/zero-delta status; no personal data or absolute paths | closed |
| T-23-20 | Tampering | zero-delta proof | high | mitigate | Non-flip branch records `zero_delta_proof: {status: not-applicable}`; `verify_zero_delta` intentionally absent | closed |
| T-23-21 | Spoofing | post-flip explicit-Qwen3 pairing | high | mitigate | Non-flip branch; no pairing exists to spoof and no model run occurred | closed |
| T-23-22 | Repudiation | proof transcription | medium | mitigate | Machine-written `not-applicable` proof block in the committed artifact; no hand-transcribed numbers | closed |
| T-23-23 | Denial of Service | `--verify-qwen3` scratch | low | mitigate | Non-flip branch: mode not added because no proof is required; missing-scratch case cannot arise | closed |
| T-23-SC | Tampering | package installs | high | mitigate | No package installed; `pyproject.toml` unchanged; model weights are a cache download recorded by revision | closed |

*Status: open · closed · open — below high threshold (non-blocking)*

---

## Accepted Risks Log

No accepted risks.

---

## Security Audit Trail

| Audit Date | Threats Total | Closed | Open | Run By |
|------------|---------------|--------|------|--------|
| 2026-11-18 | 24 | 24 | 0 | /gsd-secure-phase 23 (gsd-security-auditor, ASVS L1) |

**Auditor notes (non-blocking):** the runbook also exposes a local `--force` flag and `PINNED_RANKING_ENV`; both are operator-local hardening, not new externally reachable surface.

---

## Sign-Off

- [x] All threats have a disposition (mitigate / accept / transfer)
- [x] Accepted risks documented in Accepted Risks Log
- [x] `threats_open: 0` confirmed
- [x] `status: verified` set in frontmatter

**Approval:** verified 2026-11-18 — 24/24 threats closed at L1; 0 open at or above `high`.
