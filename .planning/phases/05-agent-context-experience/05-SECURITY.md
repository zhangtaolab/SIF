---
phase: "05"
slug: "agent-context-experience"
status: verified
# threats_open = count of OPEN threats at or above workflow.security_block_on severity (the blocking gate)
threats_open: 0
asvs_level: 1
created: "2026-09-08"
---

# Phase 05 — Security

> Per-phase security contract: threat register, accepted risks, and audit trail.

---

## Trust Boundaries

| Boundary | Description | Data Crossing |
|----------|-------------|---------------|
| CLI → SQLite | User input (context add/remove args, --index path) crosses into persistent storage via parameterized queries | user-typed strings, filesystem paths |
| Search layer → contexts table | Read-only context attachment during search; constant-SQL query post 05-08 | stored user-authored context text |
| CLI → Environment | `DOCSIFT_DB_PATH` / `SIF_*` env vars feed Settings defaults | local config values, not secrets |
| Test → Mock Database | Unit tests exercise SQL patterns against mocks, not real SQLite | test fixtures only |

---

## Threat Register

| Threat ID | Category | Component | Severity | Disposition | Mitigation | Status |
|-----------|----------|-----------|----------|-------------|------------|--------|
| T-05-01 | Tampering | `_migrate_path_contexts()` | medium | mitigate | SAVEPOINT-wrapped atomic migration with rollback on failure (`src/sif/database/schema.py:115-130`) | closed |
| T-05-02 | Tampering | `ContextRepository` SQL | medium | mitigate | All queries use `?` placeholders; no string interpolation of user data (`src/sif/database/repositories.py:367-485`) | closed |
| T-05-03 | Tampering | `context_type` validation | medium | mitigate | DB CHECK constraint `CHECK(context_type IN ('path', 'collection', 'global'))` (`src/sif/database/schema.py:100`) | closed |
| T-05-04 | Tampering | context_add type argument | low | mitigate | `click.Choice(["path", "collection", "global"])` validates input (`src/sif/cli/commands/context.py:103`) | closed |
| T-05-05 | Tampering | context_remove context_id | low | mitigate | UUID string passed to parameterized `DELETE ... WHERE id = ?` (`src/sif/database/repositories.py:460`) | closed |
| T-05-06 | Information Disclosure | context_list output | low | accept | Context content is user-provided; truncation at ~50 chars is display-only | closed |
| T-05-07 | Tampering | `_attach_contexts()` batch query | low | mitigate | Parameterized query; paths come from SearchResult objects already validated by DB query (`bm25.py`, `vector.py`, `hybrid.py`) | closed |
| T-05-08 | Information Disclosure | Context descriptions in search results | low | accept | User-provided descriptive text; no PII or secrets expected | closed |
| T-05-09 | Tampering | Mock context query (tests) | low | accept | Tests verify SQL pattern execution; no real security boundary in tests | closed |
| T-05-10 | Tampering | context_add type argument (plan 05) | low | mitigate | `click.Choice` validation, duplicate coverage of T-05-04 (`src/sif/cli/commands/context.py:187`) | closed |
| T-05-11 | Tampering | `ContextRepository.create` SQL | medium | mitigate | Parameterized INSERT with `?` placeholders; context_type from click.Choice, not free text (`src/sif/database/repositories.py:377-382`) | closed |
| T-05-12 | Tampering | `_attach_contexts()` batch query (plan 06) | low | mitigate | Same mitigation as T-05-07; superseded by constant-SQL design of T-05-08-04 | closed |
| T-05-13 | Information Disclosure | Context descriptions (plan 06) | low | accept | Same rationale as T-05-08 | closed |
| T-05-14 | Information Disclosure | DOCSIFT_DB_PATH in status output | low | accept | Path is user-configured and shown to the user who set it; not a secret | closed |
| T-05-15 | Tampering | Settings default override | low | mitigate | `--index` explicit option takes precedence; callable default only used when option omitted (`src/sif/cli/main.py:24-34`) | closed |
| T-05-08-01 | Tampering | symlink aliasing between context add and search | low | accept | Single-user local trust model; documents.path has same exposure via resolve() at index time; canonicalization reduces ambiguity | closed |
| T-05-08-02 | Information Disclosure | full path-context scan reads all path contexts per search | low | accept | Only normalized-path matches get descriptions; contexts are user-authored local content with no cross-user boundary | closed |
| T-05-08-03 | Denial of Service | unbounded path-context SELECT on every search | low | accept | Personal-KB scale (dozens of user-authored rows); single batch query per search (D-06 shape preserved) | closed |
| T-05-08-04 | Tampering | SQL construction in attach query | low | mitigate | Constant query string with zero interpolated values (`src/sif/search/context_attach.py:54`) — strictly safer than placeholder-built IN-list | closed |
| T-05-09-01 | Tampering | context add writes normalize_path(user input) | low | mitigate | Normalization only canonicalizes (expanduser + resolve); parameterized writes; no shell, no network (`src/sif/cli/commands/context.py:49`) | closed |
| T-05-09-02 | Denial of Service / data loss | prune silently deletes user-authored contexts (CR-02) | medium | mitigate | `delete_orphaned_paths` compares `normalize_path` on both sides (`src/sif/database/repositories.py:463-485`); explicit user-invoked command prints deleted count (D-12/D-13); regression tests pin CR-02 scenario (`tests/unit/cli/test_context.py:409,677+`) | closed |
| T-05-09-03 | Tampering | self-heal `update_target` rewrites stored target_id | low | mitigate | Fires only on explicit re-add; parameterized UPDATE by primary key; no bulk startup migration (`src/sif/database/repositories.py` `update_target`) | closed |
| T-05-09-04 | Repudiation | prune destroys evidence of what was removed | low | accept | Pre-existing behavior: command prints count; full audit logging out of scope for this gap closure | closed |

*Status: open · closed · open — below high threshold (non-blocking)*
*Severity: critical > high > medium > low — only open threats at or above workflow.security_block_on count toward threats_open*
*Disposition: mitigate (implementation required) · accept (documented risk) · transfer (third-party)*

---

## Accepted Risks Log

| Risk ID | Threat Ref | Rationale | Accepted By | Date |
|---------|------------|-----------|-------------|------|
| AR-05-01 | T-05-06, T-05-08, T-05-13 | Context content is user-authored local text; display truncation is cosmetic, no PII/secrets expected | plan-time threat model (05-02/03/06-PLAN) | 2026-09-08 |
| AR-05-02 | T-05-09 | Mock-based tests assert SQL patterns; no real security boundary exists in test harness | plan-time threat model (05-04-PLAN) | 2026-09-08 |
| AR-05-03 | T-05-14 | DB path shown in status output is user-configured local config, not a secret | plan-time threat model (05-07-PLAN) | 2026-09-08 |
| AR-05-04 | T-05-08-01 | Symlink aliasing equally affects documents.path at index time; single-user local trust model | plan-time threat model (05-08-PLAN) | 2026-09-08 |
| AR-05-05 | T-05-08-02, T-05-08-03 | Full-scan attachment reads user-authored rows at personal-KB scale; one batch query per search | plan-time threat model (05-08-PLAN) | 2026-09-08 |
| AR-05-06 | T-05-09-04 | Prune prints deleted count; full audit logging out of scope for gap closure | plan-time threat model (05-09-PLAN) | 2026-09-08 |

*Accepted risks do not resurface in future audit runs.*

---

## Security Audit Trail

| Audit Date | Threats Total | Closed | Open | Run By |
|------------|---------------|--------|------|--------|
| 2026-09-08 | 23 | 23 | 0 | gsd-secure-phase (L1 grep-depth, ASVS L1 short-circuit) |

Audit method: register authored at plan time (all 9 plans contained `<threat_model>` blocks); every `mitigate`-disposition threat verified against implementation at L1 grep-depth; `accept` dispositions carried into the Accepted Risks Log above. ASVS level 1 with threats_open: 0 — no deeper verification required per short-circuit rule.

---

## Sign-Off

- [x] All threats have a disposition (mitigate / accept / transfer)
- [x] Accepted risks documented in Accepted Risks Log
- [x] `threats_open: 0` confirmed
- [x] `status: verified` set in frontmatter

**Approval:** verified 2026-09-08
