---
phase: "24"
slug: "tuning-models-ux-install-docs"
status: verified
threats_open: 0
asvs_level: 1
created: "2026-11-18"
verified: "2026-11-18"
---

# Phase 24 — Security

> Per-phase security contract: threat register, accepted risks, and audit trail.
> Verified by /gsd-secure-phase 24 on 2026-11-18 (ASVS L1, block_on high).
> Register authored at plan time: all seven PLANs carry STRIDE `<threat_model>` blocks.
> 14 unique threats (T-24-01…T-24-13 + T-24-SC); all `mitigate`. T-24-13 is registered
> twice (plans 01 and 07) for the same modelscope-Qwen3 identity gate across the sweep
> and breadcrumb arms; it is verified once and closed once. The outcome was
> `keep-default` + `keep-breadcrumb-off`, so the flip-conditional surface (chunking.contract
> marker, docs migration sweep) correctly does not exist in the shipped code.

---

## Trust Boundaries

| Boundary | Description | Data Crossing |
|----------|-------------|---------------|
| User corpus → runbook subprocesses | Corpus paths drive every indexing/eval command | Paths, argv lists, arm env |
| Scratch root ↔ filesystem | Cleanup, arm DBs, and saved runs are confined to a scratch root | Paths, DB files |
| Eval payload → committed artifact | Only aggregate fields reach the committed evidence JSON | Counts, gates, identity, fingerprint |
| Committed artifact → shipped defaults | The artifact decision is the sole authorization for a default change | Decision strings, gate booleans |
| Document text → embedding input | Heading parsing consumes untrusted note content; stored content must not change | Chunk content, title/heading path |
| Settings/env → index contract | A switch change alters the embed input and cache key | `SIF_EMBED_BREADCRUMB` |
| Remote model repository → local cache | ModelScope content is untrusted data written to the user's cache | Model files, revision markers |
| Model id / cache dir → filesystem writes | User-supplied ids and paths determine where files are written | `owner/name` ids, cache roots |
| Legacy cache tree → adopted model | A pre-existing directory may be partial or corrupt | Model directories, manifests |
| Index DB → status output | Persisted identity is read from a user-controlled database file | Identity rows, schema width |
| Deprecation output → stdout/stderr | A notice on stdout would corrupt piped JSON or scripted output | Notice text |
| Install docs → user shell | Commands copied from docs execute with the user's privileges | Shell commands |
| Doc claims → shipped behavior / generator-owned docs → CI gate | Stale claims mislead users; hand edits fail the diff gate | Docs text, generated references |
| Saved run / arm DB → gate comparison | A backend or model mismatch silently makes the delta incomparable | Saved-run identity, fingerprints |

---

## Threat Register

| Threat ID | Category | Component | Severity | Disposition | Mitigation | Status |
|-----------|-----------|-----------|----------|-------------|------------|--------|
| T-24-01 | Tampering | Scratch cleanup and artifact overwrite | high | mitigate | `assert_within_scratch` refuses `/`, home, and outside paths for both root and target (scripts/harrier_eval.py:1041-1058); the guard runs before any mkdir/write/delete (chunk_sweep.py:756-760); overwrite is refused without `--force` when decision or corpus fingerprint differs (chunk_sweep.py:951-973; breadcrumb_eval.py:835-850 delegates) | closed |
| T-24-02 | Tampering | Breadcrumb embed contract and index mixing | high | mitigate | `embed_breadcrumb` defaults False (settings.py:224-228); the overlay changes only the embed input (embed_writer.py:185-192); tests assert stored contents and FTS are identical with it on (test_embed_writer.py:615, 639-673); `EmbedderIdentity` carries no breadcrumb field; runbooks strip `SIF_EMBED_BREADCRUMB` from inherited env and pin it per arm inside the scratch DB only | closed |
| T-24-03 | Tampering | Model cache integrity and substitution | high | mitigate | `verify_manifest` SHA-256+size gate on every reuse (models/download.py:126-155, 445); legacy directories are blessed only after manifest build + verification (288-309); `revision_resolved` recorded in the manifest (186-207); `--force` is the explicit refresh (426-447) | closed |
| T-24-04 | Tampering | Pull target resolution and legacy URL path | high | mitigate | `resolve_model_target` maps registry names to settings/registry ids only, accepts exactly `owner/name`, raises `ClickException` otherwise (cli/commands/models.py:60-77); download failures converted to `ClickException` (80-90); legacy URL path uses a 60-second timeout, basename filename, and non-empty check (pull.py:36, 43-45, 146-147) | closed |
| T-24-05 | Information Disclosure | Sweep artifact contents | medium | mitigate | Aggregate-only builder (chunk_sweep.py:887-940); `test_no_absolute_paths_or_query_text` (test_chunk_sweep.py:620-632); committed bench/chunk-sweep.json scans clean for `/Users/` and query text | closed |
| T-24-06 | Information Disclosure | Breadcrumb artifact and duplicate metrics | medium | mitigate | Aggregate-only envelope (breadcrumb_eval.py:787-832); `test_artifact_is_aggregate_only` (test_breadcrumb_eval.py:587-596); committed bench/breadcrumb-verdict.json scans clean | closed |
| T-24-07 | Tampering | Cache path traversal and partial-install residue | medium | mitigate | `_split_model_id` requires exactly `owner/name` with a named ValueError, rejecting `.`/`..`/backslash/NUL (download.py:87-94); sibling tmp/backup directories (210-212); verify-before-replace with backup restore and staged restore (223-250); manifest entries reject absolute or `..` relative paths (147) | closed |
| T-24-08 | Information Disclosure | Status output and deprecation routing | medium | mitigate | Status payload carries only non-secret fields — no api_key (models.py:252-272); backends probed via `find_spec`, never imported (120-132); JSON behind `--json`, plain/table chosen by TTY (98-100, 274-279); the deprecation notice prints to a stderr-only console (pull.py:31, 134) | closed |
| T-24-09 | Spoofing | Install recommendations | high | mitigate | docs/installation.md pins uv 0.9.19+ (line 6), gives the explicit `--torch-backend=cpu` recipe (32-33) with a hand-verified note (50), and marks llama-cpp wheel recipes as manually verified / not CI-proven (156, 164-165); tests pin the commands, ordering, and degradation matrix (test_docs.py:508-524) | closed |
| T-24-10 | Tampering | Generator-owned docs drift | medium | mitigate | CI regenerates cli-reference/configuration then `git diff --exit-code` (.github/workflows/docs.yml:40-42); tests assert the models surface present and hidden alias absent (test_docs.py:297-303), the Model Management section and cache states (533-541), and the retired 7B default absent from hand docs (543-553); configuration.md documents `SIF_EMBED_BREADCRUMB=False` (line 103) | closed |
| T-24-11 | Spoofing | Default-change authorization | high | mitigate | Blocking checkpoint reads both artifacts and offers adopt-* only when authorized (24-06-PLAN.md:188-228); the executable assertion compares live `DEFAULT_CHUNK_SIZE`/`OVERLAP` and `Settings.embed_breadcrumb` against the artifact decisions (24-06-PLAN.md:249); outcome keep-default/keep-breadcrumb-off; live defaults unchanged (config/constants.py:19-20; settings.py:225); no chunking.contract marker code exists in src and the conditional test asserts its absence when unflipped (test_index.py:992-1021) | closed |
| T-24-12 | Information Disclosure | Bench artifacts and docs sections | medium | mitigate | Plan privacy assertions reject `/Users/`, `/home/`, `query_text`, `document_path` (24-06-PLAN.md:141, 174); both committed artifacts pass a fresh scan; docs/benchmarking.md quotes aggregate numbers, gates, and the corpus label/fingerprint only | closed |
| T-24-13 | Spoofing | Backend/identity substitution (sweep + breadcrumb arms) | high | mitigate | `SIF_MODEL_TYPE=modelscope` pinned in every arm env (chunk_sweep.py:66, 161; breadcrumb_eval.py:71, 143); stage order index→embed→identity→eval (chunk_sweep.py:92); identity gate asserts cache_model_id, dimension, verified source, and null prompts with named failures (378-415); baseline requires matching model_type/model_name plus corpus fingerprint (461-488); identity recorded in both artifacts | closed |
| T-24-SC | Tampering | Package installs | high | mitigate | No pyproject.toml or uv.lock change anywhere in the phase 24 commit range (92818cd^..39da9e8); runbooks invoke argv-list subprocesses with no shell interpolation; `modelscope` remains an optional extra with lazy import (download.py:312-318); status probes with `find_spec` | closed |

*Status: open · closed · open — below high threshold (non-blocking)*

---

## Accepted Risks Log

No accepted risks.

---

## Security Audit Trail

| Audit Date | Threats Total | Closed | Open | Run By |
|------------|---------------|--------|------|--------|
| 2026-11-18 | 14 | 14 | 0 | /gsd-secure-phase 24 (gsd-security-auditor, ASVS L1) |

**Auditor notes (non-blocking):** the hidden `sif pull` alias retains the legacy GGUF/URL
path writing to `~/.sif/models` without a manifest for one release; that is the exact
surface T-24-04 mitigates (60-second timeout, basename filename, non-empty check,
stderr-only notice), and it is scheduled for removal with the alias. The breadcrumb
runbook reuses chunk_sweep's writer, identity gate, and scratch guards rather than
duplicating them, so the two arms cannot drift apart. Suite evidence at HEAD d97838c:
3233 passed / 1 skipped, 95.03% coverage.

---

## Sign-Off

- [x] All threats have a disposition (mitigate / accept / transfer)
- [x] Accepted risks documented in Accepted Risks Log
- [x] `threats_open: 0` confirmed
- [x] `status: verified` set in frontmatter

**Approval:** verified 2026-11-18 — 14/14 threats closed at L1; 0 open at or above `high`.
