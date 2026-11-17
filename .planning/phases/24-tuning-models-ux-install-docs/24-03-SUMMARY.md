---
phase: 24-tuning-models-ux-install-docs
plan: 03
subsystem: models
tags: [model-cache, sha256-manifest, atomic-download, legacy-migration, modelscope, qwen3]
requires:
  - "Settings.get_cache_dir() platformdirs cache root (D-07)"
  - "ModelScope 1.36 snapshot_download with revision, cache_dir, and local_dir"
provides:
  - "src/sif/models/download.py: canonical <cache>/<owner>/<name> layout"
  - "verify_manifest: per-file size + SHA-256 gate for every cache hit"
  - "inspect_cache: absent/empty/unverified/legacy/valid plus the recorded revision"
  - "ModelDownloader: sibling temp-dir download and backup/restore atomic replace"
  - "Legacy migration for the ModelScope <name___> tree and ~/.sif/models"
  - "DEFAULT_MODELS corrected to the Qwen3-0.6B family with revision master (D-09)"
affects:
  - "Plan 24-04 (sif models pull/status consumes inspect_cache, list_cached_models, DEFAULT_MODELS)"
  - "Existing user model caches (migrated on the next pull; untouched until then)"
tech-stack:
  added: []
  patterns:
    - "Manifest-gated cache reuse: no valid manifest means no cache hit"
    - "Sibling temporary directory plus backup/restore atomic directory replacement"
    - "SHA-256 over 1 MiB streaming chunks, mirroring src/sif/embedding/embedder.py"
key-files:
  created: []
  modified:
    - src/sif/models/download.py
    - tests/unit/models/test_download.py
decisions:
  - "A cache hit requires .sif-model.json with a matching size and SHA-256 for every listed file; empty, manifestless, size-mismatch, and hash-mismatch directories all re-download."
  - "Home-legacy detection (~/.sif/models) applies to the default cache root only; an explicit cache_dir is hermetic, so inspect_cache reports absent on an empty temp root."
  - "The canonical target is replaced only after the staged tree verifies; a failure restores the previous target and, for migration, moves the legacy source back."
  - "Legacy adoption builds a manifest in the source, verifies it, then renames the source into the canonical target; a failed rename falls back to downloading and leaves the source intact."
  - "DEFAULT_MODELS pins revision master explicitly and records revision_resolved from .mv; determinism is local-content determinism, not an upstream immutable pin (Pitfall 7)."
  - "model_type modelscope, modelscope_version from importlib.metadata when available, and a UTC ISO-8601 created_at are recorded in every manifest."
metrics:
  duration: "~9 min"
  completed: "2026-11-17"
  tasks: 2
  files: 2
status: complete
actuals:
  tokens: 15674
  tasks: 2
  commits: 1
commits: 1
plan_head_before: 7a839e2955e3b58db9a83dab3671a2247df4ab41
plan_head_after: 75c6e54e0f4b541bc115a4d408da23ef1e39ac53
---

# Phase 24 Plan 03: Canonical Model Cache and Manifest Summary

A deterministic `<Settings.get_cache_dir()>/models/<owner>/<name>` cache with a
SHA-256 manifest gate, an atomic temp-dir install, legacy cache migration, and a
corrected Qwen3-0.6B download registry.

## What Was Built

- **Canonical layout** — `canonical_model_dir(cache_root, model_id)` accepts
  exactly `owner/name` (named `ValueError` otherwise, including `.`/`..`,
  backslashes, and NUL) and returns `<cache_root>/<owner>/<name>`. The downloader
  defaults its cache root to `Settings.get_cache_dir() / "models"` and keeps
  accepting an explicit path.
- **Manifest contract** — `MANIFEST_NAME = ".sif-model.json"`,
  `MANIFEST_VERSION = 1`. `verify_manifest` requires version 1, a non-empty
  `files` mapping, and for every entry a regular file of the recorded size whose
  SHA-256 matches; missing/corrupt manifests, missing files, size mismatches,
  hash mismatches, and traversal entries all return `False` instead of raising.
- **Atomic download** — a unique sibling `<name>.tmp-<id>` receives
  `snapshot_download(model_id=..., revision=..., cache_dir=..., local_dir=...)`
  (wrapped in `suppress_output()` when quiet). `config.json` is required, every
  regular file is hashed into the manifest, the manifest is written atomically,
  and the staged tree re-verifies before replacing the target. An existing target
  is renamed to `<name>.backup-<id>`, restored on failure, and removed only after
  the new tree verifies.
- **`inspect_cache`** — reports `model_id`, canonical `path`, `state`
  (`absent`/`empty`/`unverified`/`legacy`/`valid`), and `revision` from the
  manifest when valid, with no network access and no filesystem mutation.
- **Legacy awareness** — deterministic order: the canonical target, then
  `<cache_root>/<owner>/<name___>`, then `~/.sif/models/<owner>/<name___>`.
  A candidate is adoptable only with `config.json` and at least one
  `.safetensors`/`.bin`/`.gguf`/`.pt`; a manifest is built and verified before a
  rename-with-backup; the source survives until the target verifies; a failed
  rename falls back to downloading and leaves the source untouched.
- **Corrected registry** — module-level `DEFAULT_MODELS` (bound to
  `ModelDownloader.DEFAULT_MODELS`) names
  `Qwen/Qwen3-Embedding-0.6B` (1024-dim), `Qwen/Qwen3-Reranker-0.6B`, and
  `qwen/Qwen2.5-0.5B-Instruct`, each with `description` and
  `revision: "master"`. The embedding and reranker ids equal the shipped
  Settings defaults.
- **Cache utilities** — `list_cached_models` reports canonical two-level
  directories and recognized legacy directories with reconstructed `model_id`s
  and a `source` tag, walking only the cache root and the home legacy root;
  `clear_cache` refuses `/` and the home directory and leaves outside paths
  untouched.
- **Missing dependency** — `modelscope` is imported lazily; its absence raises
  `ImportError` with the actionable embed-extra message before any temporary
  directory or target is created.

## Tests

`tests/unit/models/test_download.py` was rewritten (52 cases) with a scoped
ModelScope fake and an autouse home seam that prevents the real `~/.sif/models`
from being read or moved. Coverage includes:

- canonical path derivation (dots intact, no `___`) and malformed-id rejection;
- valid manifest → no download; empty, manifestless, size-mismatch, and
  hash-mismatch directories → re-download; `--force` → re-download;
- manifest keys, SHA-256 digest (explicitly not md5), `created_at`, and
  `revision_resolved`;
- no temporary/backup residue after success, client failure, a missing
  `config.json`, and replacement of an unverified target;
- the actionable `ImportError`;
- all five `inspect_cache` states without importing ModelScope;
- both legacy layouts migrating, a config-only legacy tree ignored, and a failing
  rename leaving the source intact;
- registry/Settings parity, listing across cache and home roots, and guarded
  clearing.

## Verification

- `env -u FORCE_COLOR NO_COLOR=1 pytest tests/unit/models/test_download.py -x --no-cov` — 52 passed.
- `python -c "... canonical_model_dir(...) == ..."` — passed.
- `python -c "... DEFAULT_MODELS parity with Settings ..."` — passed.
- `python -c "... inspect_cache(...) == 'absent' on an empty temp root ..."` — passed.
- `ruff check src tests`, `ruff format --check src tests`, `ty check src/sif` — green.
- Full suite: **3119 passed, 1 skipped** at 95.02% coverage.
- Adjacent consumers (`tests/unit/embedding/test_embedder_impl.py`,
  `tests/unit/inference/test_reranker.py`, `tests/unit/cli/test_pull.py`) — green.

## Deviations from Plan

### Contract Adjustment

**1. [Plan-contract conflict] Home-legacy detection scoped to the default cache root**
- **Found during:** Task 2 verification
- **Issue:** The plan's automated check asserts `inspect_cache("Qwen/Qwen3-Embedding-0.6B", <empty temp dir>)["state"] == "absent"`.
  This machine has a real `~/.sif/models/Qwen/Qwen3-Embedding-0___6B` legacy tree
  (documented in the phase research inventory), so unconditional home detection
  returned `legacy` and the check failed even though no canonical cache existed.
- **Fix:** `~/.sif/models` is recognized/migrated only for the default cache root
  (`cache_dir is None`); an explicit `cache_dir` is hermetic. Legacy
  `<cache_root>/<owner>/<name___>` detection still applies to both. This keeps
  the existing-user migration for the default path, makes test/override caches
  deterministic, and matches both Task 2 verify commands.
- **Files modified:** `src/sif/models/download.py`, `tests/unit/models/test_download.py`
- **Commit:** 75c6e54

**2. [Process] A single implementation commit covers Tasks 1 and 2**
- Both tasks edit exactly the same two files and the legacy helpers are
  interleaved with the canonical-cache code; splitting them would have required a
  non-buildable intermediate. The combined commit passed the targeted suite, the
  plan verify commands, and the full quality suite.
- **Commit:** 75c6e54

### Auto-fixed Issues

None beyond the above.

## Known Stubs

None.

## Threat Flags

None beyond the plan's threat model. T-24-03 is mitigated by the SHA-256 +
size manifest gate (no manifestless directory is ever blessed), and T-24-07 by
owner/name-only path derivation, sibling temporary directories, and
verify-before-replace with backup restoration. No package was installed and
`modelscope` remains a lazy optional import.

## Self-Check: PASSED

- `src/sif/models/download.py` exists.
- `tests/unit/models/test_download.py` exists.
- Commit 75c6e54 is an ancestor of HEAD.

