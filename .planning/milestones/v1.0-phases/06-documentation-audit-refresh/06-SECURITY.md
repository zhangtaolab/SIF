---
phase: "06"
slug: "documentation-audit-refresh"
status: verified
# threats_open = count of OPEN threats at or above workflow.security_block_on severity (the blocking gate)
threats_open: 0
asvs_level: 1
created: "2026-11-06"
---

# Phase 06 — Security

> Per-phase security contract: threat register, accepted risks, and audit trail.
> Retroactive reconstruction at milestone v1.0 close (2026-11-06): the register is assembled
> from the `<threat_model>` blocks of plans 06-08/06-09/06-10 (register authored at plan
> time); plans 06-01..06-07 predate the threat-modelling convention and their docs-phase
> surface introduces no additional trust boundary (no new inputs, endpoints, or data flows —
> the phase writes documentation and read-only generators only).

---

## Trust Boundaries

| Boundary | Description | Data Crossing |
|----------|-------------|---------------|
| Generator → docs tree | `scripts/generate_cli_ref.py` / `generate_config_ref.py` / `generate_arch_diagram.py` read source code and write generated Markdown | Live source introspection → committed docs (incl. anything echoed from the author's environment, e.g. absolute home paths) |
| CI ↔ docs drift | `.github/workflows/docs.yml` regenerates and diffs the two generated docs | Committed docs vs generator output; a mismatch must fail the job |

---

## Threat Register

| Threat ID | Category | Component | Severity | Disposition | Mitigation / Rationale | Status |
|-----------|----------|-----------|----------|-------------|------------------------|--------|
| T-06-01 | Tampering | `.github/workflows/docs.yml` | high | mitigate | Strengthened, not weakened: same triggers/setup, no new permissions/secrets/external actions; the change makes an existing check able to FAIL the job (docs.yml:38 `git diff --exit-code`, no `\|\| true` — re-verified 2026-11-06) | closed |
| T-06-02 | Tampering | `scripts/generate_cli_ref.py`, `scripts/generate_config_ref.py` | medium | mitigate | Generators write only their two explicit docs paths via `Path.write_text` (cli_ref:336, config_ref:423); no shell-out, no network — re-grepped 2026-11-06 | closed |
| T-06-03 | Information Disclosure | `docs/cli-reference.md` (generated) | low | mitigate | Tilde-rewrite removes user-specific absolute home paths; `grep -c "/Users/"` = 0 in both generated docs (re-verified 2026-11-06) | closed |
| T-06-04 | Denial of Service | CI drift gate (blocking) | low | accept | A future CLI change without doc regeneration now fails CI loudly BY DESIGN; the fix (`make docs-generate`) is documented in the workflow and Makefile help | closed |
| T-06-05 | Repudiation | `docs/mcp-server.md` daemon section | medium | mitigate | Daemon documented with its exact live failure mode (raises not-yet-implemented, directs to `mcp http`) — confirmed against `src/sif/cli/commands/mcp.py` by the 2026-11-06 mcp-server doc verifier | closed |
| T-06-06 | Information Disclosure | `docs/mcp-server.md` db-path defaults | low | mitigate | Documented defaults match live platformdirs resolution (`constants.py`); re-verified by the docs fact-check (26/26) | closed |
| T-06-07 | Tampering | `scripts/generate_arch_diagram.py` | low | mitigate | AST-parse-only, reads `src/sif`, writes nothing, no network/shell-out — re-grepped 2026-11-06 (zero write/subprocess hits) | closed |
| T-06-08 | Repudiation | `docs/architecture.md` | low | mitigate | Phantom-module claims removed; module tree existence-checked (bidirectional basename check passed in verification; docs fact-check 87/87 on 2026-11-06) | closed |

---

## Accepted Risks

- T-06-04 (CI drift gate fails loudly on un-regenerated docs) — accepted by design; the loud failure is the mitigation working.

---

## Security Audit

| Metric | Count |
|---|---|
| Threats found | 8 |
| Closed | 8 |
| Open | 0 |
