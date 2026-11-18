---
phase: "21"
slug: "scale-maintenance-embedder-identity"
status: verified
threats_open: 0
asvs_level: 1
created: "2026-11-18"
verified: "2026-11-18"
---

# Phase 21 — Security

> Per-phase security contract: threat register, accepted risks, and audit trail.
> Verified by /gsd-secure-phase 21 on 2026-11-18 (ASVS L1, block_on high), at HEAD of `dev`
> with the Phase-22 MCP successor (`tools.py` + `backend.py`) verified in place of the old shell.
> Register authored at plan time: all eight PLANs carry STRIDE `<threat_model>` blocks.

---

## Trust Boundaries

| Boundary | Description | Data Crossing |
|----------|-------------|---------------|
| embedding cache ↔ manager | Cached vectors are trusted only after count/dimension/finite validation | Float vectors, model ids |
| `index_meta` identity row ↔ search | A stored/assumed embedder identity gates vector use | Fingerprint, dimension, prompts, revision |
| `embedded_documents` shadow ↔ staleness | Shadow rows decide derived staleness markers | Document ids, embedding document ids |
| contexts repository ↔ search enrichment | A cached context map must reflect committed writes | Paths, context descriptions |
| contexts cache ↔ sentinel connection | Cross-connection commits must invalidate the map | `PRAGMA data_version`, inode |
| stream writer ↔ per-document transaction | Embedding runs outside transactions; one short commit persists chunks+vectors+shadow+identity | Chunks, vectors, identity |
| maintenance CLI ↔ live database | VACUUM/backup cross-process with a live reader/writer | DB file, WAL, lock files |
| backup target ↔ filesystem | An output path is created 0600/0700, never through a symlink | DB copy, sidecars |
| generated docs ↔ source | Only the generators write the two reference files | CLI/config reference text |

---

## Threat Register

| Threat ID | Category | Component | Severity | Disposition | Mitigation | Status |
|-----------|----------|-----------|----------|-------------|------------|--------|
| T-21-01 | Tampering | EmbeddingManager cache write/read | high | mitigate | `_is_usable_cached` (dim+finite) on read, `_validate_vector` before `cache.set`, invalid entries recomputed and overwritten (`manager.py:211-349`) | closed |
| T-21-02 | Tampering | identity read | medium | mitigate | `_load_payload`/`_payload_error` return None with one warning on malformed/missing fields (`identity.py:72-114,174-206,385-392`) | closed |
| T-21-03 | Elevation of Privilege | revision provenance | medium | mitigate | Revision only from in-memory transformers `_commit_hash` or local GGUF SHA-256; zero pickle/torch.load/joblib in `src/sif/embedding` and `src/sif/config` (`embedder.py:78-101,445-450`) | closed |
| T-21-04 | Spoofing | prompt name resolution | low | accept | Fixed table + local settings; unknown prompt fails loudly (`embedder.py:41-53`); accepted per `21-01-PLAN.md:323` | closed |
| T-21-05 | Tampering | `embedded_documents` maintenance | high | mitigate | Shadow insert joins `documents`; all writes inside the caller's transaction; sole writer `embed_writer.py:233`; reconcile from both source tables (`vector.py:40-43,360-426`; `maintenance.py:65-102`; `schema.py:358-403`) | closed |
| T-21-06 | Denial of Service | search-path staleness read | medium | mitigate | One display-gate probe + per-result PK lookup; no `document_embeddings` scan in marking (`staleness.py:44-45,84-98`) | closed |
| T-21-07 | Information Disclosure | stale marker correctness | low | accept | Advisory markers, self-heal on reconcile/re-embed; accepted per `21-02-PLAN.md:269` | closed |
| T-21-08 | Tampering | cached context map freshness | high | mitigate | Invalidate on repository generation, sentinel `PRAGMA data_version`, and inode; all sampled before build (`context_attach.py:188-281`; `repositories.py:46-59,477-557`) | closed |
| T-21-09 | Denial of Service | sentinel connection lifecycle | medium | mitigate | One lazy sentinel per resolved path, atexit/reset close, `:memory:` bypass, open failure bypasses cache (`context_attach.py:113-270`) | closed |
| T-21-10 | Information Disclosure | contexts cache across databases | low | accept | Key is the resolved main DB path; accepted per `21-03-PLAN.md:209` | closed |
| T-21-11 | Tampering | vector-space mismatch on search | high | mitigate | Field-wise identity check at every vector-touching exit; same-dim warns once + marks page; dimension mismatch refuses/degrades with remedy (`hybrid.py:294-440`; `search.py:826-1199`; `mcp/backend.py:508-678`; `bench.py:180-208`; `eval.py:247-272`) | closed |
| T-21-12 | Spoofing | legacy assumed identity | medium | accept | Search never blocked; later swap detected against assumed value; `--force` certifies; accepted per `21-04-PLAN.md:273` | closed |
| T-21-13 | Denial of Service | warning amplification | low | mitigate | Module-level latch, one warning per identity pair per process, no per-result warnings (`identity.py:61-69,497-520`) | closed |
| T-21-15 | Tampering | batch-boundary garbage vectors | high | mitigate | `validate_batch` count/dimension/finite/norm before persistence; `SystemicEmbedError` aborts the document and writes nothing (`embed_writer.py:79-123,210-212`) | closed |
| T-21-16 | Denial of Service | write-lock hold time and memory | medium | mitigate | Chunk/embed outside transactions; bounded batches; one short per-document commit; collection stats once (`embed_writer.py:173-246`; `index.py:454-460`; `watcher.py:277-297`) | closed |
| T-21-17 | Tampering | identity certification | medium | mitigate | `source="verified"` only on a fresh index inside `BEGIN IMMEDIATE`, or a complete unfiltered zero-failure `--force` (`embed_writer.py:248-281`; `index.py:479-496`) | closed |
| T-21-18 | Denial of Service | uncacheable documents | low | accept | Whitespace/chunkless retried per run by the completeness contract; bounded by explicit runs (`embed_writer.py:181-183,283-288`; `21-05-PLAN.md:267`) | closed |
| T-21-19 | Information Disclosure | backup output path | high | mitigate | Refuses symlink/existing/DB/sidecar targets; `O_CREAT|O_EXCL|O_NOFOLLOW` 0600; default dir 0700; CLI-only (`maintenance.py:210-382`; `index.py:575-614`) | closed |
| T-21-20 | Tampering | VACUUM/backup against a live database | high | mitigate | flock + busy timeout + no open transaction + WAL checkpoint + online backup API + `integrity_check`; busy errors retryable, failed copies discarded (`maintenance.py:125-397`) | closed |
| T-21-21 | Denial of Service | disk exhaustion during VACUUM | medium | mitigate | Conservative 2× (db + WAL) precheck naming required and available bytes (`maintenance.py:160-168`) | closed |
| T-21-22 | Tampering | vacuously recreated shadow rows | low | mitigate | `INSERT OR IGNORE ... JOIN documents` on reconcile and backfill (`maintenance.py:70-74`; `schema.py:390-394`) | closed |
| T-21-23 | Repudiation | byte-identical baseline evidence | high | mitigate | Pre-phase literals recorded and asserted, never regenerated; only-new-writes asserted (`test_manager.py:14-19`; `test_embedder_impl.py:897-911`; `test_bench_snapshot.py:86`; `test_index.py:756`) | closed |
| T-21-24 | Tampering | generated documentation | medium | mitigate | Only the two generators write the reference files; CI diff gate (`.github/workflows/docs.yml:42`) | closed |
| T-21-25 | Elevation of Privilege | accidental MCP exposure | medium | mitigate | MCP registers only the seven read tools; zero vacuum/backup references in `src/sif/mcp/` (`tools.py:392-407`) | closed |
| T-21-26 | Spoofing | legacy assumed identity at schema open | medium | accept | Width-only init-mode check, never blocks; `--force` certifies; accepted per `21-08-PLAN.md:251` | closed |
| T-21-27 | Repudiation | dimension-guard error wording | low | mitigate | Shared read and wording pinned byte-identical (`identity.py:231-369`; `schema.py:684-708`; `embedder.py:677-686`) | closed |
| T-21-28 | Tampering | prompt scheme recorded but not applied | medium | mitigate | One resolved `PromptScheme` feeds both identity and `create_model` (`manager.py:52-118`; `factory.py:73-113`; `backend.py:261-353`) | closed |
| T-21-SC | Tampering | package installs | high | mitigate | No dependency/lockfile change in any Phase 21 commit | closed |

*Status: open · closed · open — below high threshold (non-blocking)*
*Severity: critical > high > medium > low — only open threats at or above workflow.security_block_on count toward threats_open*

---

## Accepted Risks Log

| Risk ID | Threat Ref | Rationale | Accepted By | Date |
|---------|------------|-----------|-------------|------|
| AR-21-01 | T-21-04 | Prompt names come from local settings plus a fixed table; the model's own `prompts` dict is the authority and an unknown name fails loudly, so a typo cannot silently change vectors. | Plan-time register (`21-01-PLAN.md:323`) | 2026-11-18 |
| AR-21-02 | T-21-07 | Staleness markers are advisory; a lagging shadow can mislabel but self-heals on reconcile/re-embed, and no data is disclosed. | Plan-time register (`21-02-PLAN.md:269`) | 2026-11-18 |
| AR-21-03 | T-21-10 | Context-cache key is the resolved main DB path; two databases cannot share a map, and paths are local to a single-user process. | Plan-time register (`21-03-PLAN.md:209`) | 2026-11-18 |
| AR-21-04 | T-21-12 | An index predating identity is assumed correct; search is never blocked, a later swap is still detected against the assumed value, and `--force` is the certification path. | Plan-time register (`21-04-PLAN.md:273`) | 2026-11-18 |
| AR-21-05 | T-21-18 | Whitespace-only/chunkless documents are retried each run by the existing completeness contract; harmless and bounded by explicit user runs. | Plan-time register (`21-05-PLAN.md:267`) | 2026-11-18 |
| AR-21-06 | T-21-26 | Same legacy-assumed-identity rationale as T-21-12 at schema-open time; width-only check never blocks. | Plan-time register (`21-08-PLAN.md:251`) | 2026-11-18 |

*Accepted risks do not resurface in future audit runs.*

---

## Security Audit Trail

| Audit Date | Threats Total | Closed | Open | Run By |
|------------|---------------|--------|------|--------|
| 2026-11-18 | 28 | 28 | 0 | /gsd-secure-phase 21 (gsd-security-auditor, ASVS L1) |

**Auditor notes (non-blocking):** (1) the plan text claimed a test asserting the factory receives both prompt names; no such call-args assertion exists, but the property is structurally enforced by one resolved scheme feeding both paths (T-21-28 closed). (2) `21-01-SUMMARY.md` and `21-04-SUMMARY.md` omit the `## Threat Flags` heading; the phase diff adds no unregistered surface.

---

## Sign-Off

- [x] All threats have a disposition (mitigate / accept / transfer)
- [x] Accepted risks documented in Accepted Risks Log
- [x] `threats_open: 0` confirmed
- [x] `status: verified` set in frontmatter

**Approval:** verified 2026-11-18 — 28/28 threats closed at L1; 0 open at or above `high`.
