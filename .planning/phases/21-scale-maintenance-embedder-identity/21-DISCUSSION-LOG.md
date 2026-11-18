# Phase 21: Scale, Maintenance + Embedder Identity - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-11-15
**Phase:** 21-Scale, Maintenance + Embedder Identity
**Areas discussed:** Embedder identity contract, Role-aware embed + prompt scheme, Bounded staleness reads, Contexts read caching, Maintenance surface (vacuum + backup), Streaming embed semantics
**Mode:** `--auto` — every question auto-resolved to the recommended option; no interactive prompts.

---

## Embedder identity contract

| Option | Description | Selected |
|--------|-------------|----------|
| Global per index (recommended) | One `index_meta` identity key; one vec0 table = one KNN space; search is not collection-scoped by default | ✓ |
| Per collection | A `convention:<collection>`-style identity per collection; implies multi-space storage that does not exist | |
| Both | Global identity plus per-collection overrides; redundant and ambiguous on swap | |

**Auto choice:** Global per index.
**Notes:** The `index_meta` docstring's Phase 21 anticipation is realized as a global key; per-collection namespacing remains for convention markers only.

| Option | Description | Selected |
|--------|-------------|----------|
| Structured JSON + deterministic fingerprint (recommended) | `cache_model_id` base + dimension/pooling/normalize/prompt scheme + best-effort revision/GGUF file hash; `source=verified|legacy-assumed` | ✓ |
| Opaque `_cache_model_id` string only | Cheapest, but cannot detect a same-name GGUF file swap or a prompt-scheme change | |
| Dim + model name only | The exact width-only trap the Harrier gate exists to prevent | |

**Auto choice:** Structured JSON with deterministic fingerprint.
**Notes:** GGUF file SHA-256 and ST resolved revision are best-effort; `unknown` is recorded rather than guessed. Identity checks apply only while stored vectors exist.

| Option | Description | Selected |
|--------|-------------|----------|
| Fail embed / warn+mark search (recommended) | Embed raises with a remedy; search warns once and marks vector-involving results `vectors_stale` | ✓ |
| Fail both | Safest but makes an existing index unsearchable until re-embedded | |
| Warn both | Never blocks, lets a broken model silently write vectors | |

**Auto choice:** Fail-fast embed, warn+mark search.
**Notes:** Marking reuses `SearchResult.vectors_stale`; no result-schema change. BM25-only commands neither warn nor mark.

| Option | Description | Selected |
|--------|-------------|----------|
| Warn + assume + certify on re-embed (recommended) | `source=legacy-assumed` backfill, one warning per process, `--force` full re-embed certifies | ✓ |
| Refuse vector use until re-embed | Breaks upgrades unnecessarily; identity may already be correct | |
| Silently adopt current identity | Hides the unverifiable state; the exact silent-acceptance trap | |

**Auto choice:** Warn once, assume, certify on full re-embed.
**Notes:** Search is never blocked on an assumed identity; a later swap is still detected against the assumed value.

| Option | Description | Selected |
|--------|-------------|----------|
| Consolidate into one identity module (recommended) | One module owns identity construction, the single `FLOAT[n]` read, and mode-aware checks; schema/embed_cmd/watcher delegate | ✓ |
| Keep per-site guards beside identity checks | Leaves three copies that can drift | |

**Auto choice:** Consolidate the three index-vs-model guards.
**Notes:** The OpenAI endpoint-vs-settings check stays a config-layer check with shared error wording.

---

## Role-aware embed + prompt scheme

| Option | Description | Selected |
|--------|-------------|----------|
| Manager-level role methods, protocol unchanged (recommended) | `embed_query`/`embed_documents` on `EmbeddingManager`; `Embedder` protocol keeps its three members | ✓ |
| `prompt_name` param through `embed`/`embed_batch` | Works but every call site must remember the role | |
| Extend the Embedder protocol | Forces every implementation and test double to change | |

**Auto choice:** Manager-level role methods; protocol unchanged.
**Notes:** All query-side call sites (hybrid, HyDE, expansion, eval/bench) and document-side sites (embed_cmd, watcher) are audited.

| Option | Description | Selected |
|--------|-------------|----------|
| Settings + known-model defaults (recommended) | Env-configurable prompt names plus a small table for Harrier (`web_search_query` query-side) | ✓ |
| Settings only, Phase 23 sets them | The Harrier arm can be silently crippled if the setting is omitted | |
| Hard-coded per model name | No override path; brittle | |

**Auto choice:** Settings fields with a known-model default table, no CLI flag.
**Notes:** Qwen3 has no table entry, so its default path stays byte-identical.

| Option | Description | Selected |
|--------|-------------|----------|
| Prompt-conditional suffix (recommended) | `|q@<prompt>` / `|d@<prompt>` only when effective; absent prompts keep today's exact key | ✓ |
| Always include role | Splits the Qwen3 cache for no correctness gain | |
| Bypass cache for queries | Loses the cache benefit entirely | |

**Auto choice:** Prompt-conditional cache suffix; revision/file hash joins when present.
**Notes:** Prevents prompted-query/unprompted-document collisions without changing the default bucket.

---

## Bounded staleness reads

| Option | Description | Selected |
|--------|-------------|----------|
| Transactional shadow table (recommended) | `embedded_documents(document_id PK, FK cascade)`, maintained in the same transaction as every embedding write/delete, rebuildable | ✓ |
| Persisted per-document stale flag | The silent-lie bug class Phase 10.1 hunted; many write paths must keep it truthful | |
| Per-connection embedded-id cache only | Still scans once per process/connection and has no cross-process invalidation | |

**Auto choice:** Transactional `embedded_documents` shadow.
**Notes:** Orphan embedding rows never create shadow rows; every insert joins `documents`.

| Option | Description | Selected |
|--------|-------------|----------|
| Schema-init backfill + cleanup/vacuum reconcile (recommended) | One-time idempotent pass gated by an `index_meta` version marker; reconcile in existing maintenance transactions | ✓ |
| Lazy build on first query | First query pays the scan and races with writers | |
| Explicit rebuild command | Adds a step users will forget; maintenance can do it | |

**Auto choice:** Backfill in `SchemaManager`, reconcile in cleanup/vacuum.

| Option | Description | Selected |
|--------|-------------|----------|
| Byte-identical marker semantics (recommended) | `embedded_document_ids()` reads the shadow; empty = no markers; missing vec0/shadow = `None`; same output | ✓ |
| Allow marker wording/format changes | Unnecessary contract churn | |

**Auto choice:** Byte-identical read-side contracts.

---

## Contexts read caching

| Option | Description | Selected |
|--------|-------------|----------|
| Per-connection cache with `data_version` invalidation (recommended) | Cache `normalize_path -> content`; invalidate on repository writes and `PRAGMA data_version`; no schema change | ✓ |
| Write-side `normalized_target_id` column + backfill | Touches the locked Key Decision (realpath not invertible) and requires dual matching for legacy rows | |
| Keep the full scan | Leaves CORR-06 half-delivered | |

**Auto choice:** Normalized-map cache with `PRAGMA data_version` + repository-write invalidation.
**Notes:** No SQL prefilter and no normalized column in this phase; verbatim rows keep matching.

---

## Maintenance surface (vacuum + backup)

| Option | Description | Selected |
|--------|-------------|----------|
| Index-group CLI only (recommended) | `sif index vacuum` + `sif index backup [--output PATH]`; MCP exposure deferred to Phase 22 | ✓ |
| Top-level `sif backup` | Inconsistent with `index vacuum`; weaker qmd/CLI parity | |
| CLI + MCP tools now | Bypasses Phase 22's annotation/path-restriction work | |

**Auto choice:** `index`-group CLI commands only.

| Option | Description | Selected |
|--------|-------------|----------|
| Lock + checkpoint + online backup + explicit 2× disk check (recommended) | flock, busy timeout, checkpoint(TRUNCATE), online backup API, `integrity_check`, retryable busy errors, free-space precheck | ✓ |
| Require daemons stopped first | Unnecessary on WAL; harms the live-index experience | |
| Best-effort without disk check | Large-DB VACUUM can fail mid-way on low disk | |

**Auto choice:** Conservative safety semantics; watch/MCP hosts need not be stopped.
**Notes:** No `--skip-space-check` in this phase.

---

## Streaming embed semantics

| Option | Description | Selected |
|--------|-------------|----------|
| Per-document atomicity (recommended) | Embed outside txn in `settings.batch_size` batches; one short transaction per document; resume via exact-set skip | ✓ |
| Per-embed-batch commits | Smaller lock holds, but a document can be visible partially embedded | |
| One transaction per collection (today) | The giant transaction this phase exists to remove | |

**Auto choice:** Per-document atomicity with embedding outside the transaction.

| Option | Description | Selected |
|--------|-------------|----------|
| Isolate document-local, abort on systemic (recommended) | Record per-document failures and continue; model/identity/sanity failures abort after prior commits; one final report + non-zero exit | ✓ |
| Continue on every failure | A broken model would burn through the whole corpus | |
| Abort the collection on first failure | Loses most of the resumability benefit | |

**Auto choice:** Document-local isolation, systemic abort, aggregated CR-02 report.

| Option | Description | Selected |
|--------|-------------|----------|
| Mandatory batch-boundary sanity (recommended) | Count, finite, dimension, unit norm; violation is systemic and names identity/batch/chunk | ✓ |
| Trust the model backend | Repeats qmd #897 (silent garbage vectors) | |

**Auto choice:** Mandatory sanity checks.

| Option | Description | Selected |
|--------|-------------|----------|
| Shared service (recommended) | One chunk→embed→persist writer used by embed_cmd and the watcher; Phase 24 reuses it | ✓ |
| Separate implementations | Sanity/shadow maintenance can drift between hosts | |

**Auto choice:** One shared streaming embed service.

---

## Claude's Discretion

- Identity JSON key spelling, schema version, fingerprint algorithm.
- Layering of the cheap settings-only precheck vs the full post-load check.
- Shadow-table extra columns/index shape and the reconcile helper's home.
- Context-cache placement and the exact `data_version` polling point.
- Maintenance command output layout and optional `--json` framing.
- Per-document batch-size tuning and progress cadence.
- Whether `sif index status` surfaces the identity (Phase 24's `models status` is the consumer of record).
- Test fixtures for the byte-identical baseline, legacy upgrade, mid-run failure, garbage vectors, vacuum under load, and backup integrity.

## Deferred Ideas

- Per-collection embedder identity / multiple vector spaces (rejected now: one vec0 table = one space).
- MCP exposure of vacuum/backup (Phase 22).
- `contexts.normalized_target_id` write-side column (locked Key Decision conflict).
- `--skip-space-check`, `PRAGMA optimize`, `auto_vacuum` changes.
- Scheduled/threshold auto-vacuum.
- Identity display in `sif status` (Phase 24 `models status`).
- A dedicated `--certify` command (`--force` is the path).
