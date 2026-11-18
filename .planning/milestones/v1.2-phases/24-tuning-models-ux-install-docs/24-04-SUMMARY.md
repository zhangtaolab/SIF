---
phase: 24-tuning-models-ux-install-docs
plan: 04
subsystem: cli
tags: [models-cli, model-cache, embedder-identity, click, docs-generation, deprecation]
requires:
  - "Plan 24-03: ModelDownloader.download/inspect_cache/DEFAULT_MODELS canonical manifest cache"
  - "Phase 21 identity: build_settings_identity/read_identity/schema_embedding_dim/display_fingerprint"
provides:
  - "src/sif/cli/commands/models.py: models group with pull and status"
  - "resolve_model_target/download_model/download_model_target shared target handler"
  - "models status settings/cache/backend/vector_backend/identity payload (JSON, plain, Rich)"
  - "src/sif/cli/commands/pull.py hidden deprecated alias delegating to models pull"
  - "scripts/generate_cli_ref.py + tests/test_docs.py hidden-command skipping"
  - "docs/cli-reference.md Model Commands section (generated)"
affects:
  - "Plan 24-05/24-06 install docs reference sif models pull/status"
  - "Users of the legacy sif pull alias (one-release deprecation window)"
tech-stack:
  added: []
  patterns:
    - "TTY-branched rendering: plain section.key/JSON for pipes, Rich table only on a TTY"
    - "Model-free backend probe with find_spec + importlib.metadata.version"
    - "Hidden Click command skipped by the generator and the docs test collector"
key-files:
  created:
    - src/sif/cli/commands/models.py
    - tests/unit/cli/test_models.py
  modified:
    - src/sif/cli/main.py
    - src/sif/cli/commands/pull.py
    - scripts/generate_cli_ref.py
    - tests/test_docs.py
    - tests/unit/cli/test_pull.py
    - docs/cli-reference.md
decisions:
  - "Pull target resolution: None/embedding -> settings.model_name, reranker -> settings.reranker_model_name, query_expansion -> registry id, exactly one slash -> ModelScope owner/name; anything else is a ClickException naming the accepted values."
  - "Status identity decides match/mismatch/dimension-mismatch from the stored dimension, schema FLOAT width, and cache_model_id; source and display fingerprints are reported as display fields only (D-08)."
  - "Backend probes map model_type to module + distribution (gguf -> llama_cpp / llama-cpp-python) and never import or download."
  - "Non-TTY status emits fixed-order section.key lines; --json is sort_keys=True at every level; Rich tables appear only on a TTY and only when not quiet."
  - "The deprecated alias keeps the legacy GGUF/URL path with a 60s urlopen timeout, 1 MiB streaming, and a non-empty check; everything it writes to stderr, stdout carries only the plain result line."
metrics:
  duration: "~7 min"
  completed: "2026-11-17"
  tasks: 3
  files: 8
status: complete
actuals:
  tokens: 11766
  tasks: 3
  commits: 3
commits: 3
plan_head_before: 783e0a6ea286a7949092fd6950d52aba7f5c6441
plan_head_after: a74c4b533587839848d359db7536111776232f35
requirements-completed: [MODELS-01, MODELS-02]
---

# Phase 24 Plan 04: Models Pull/Status UX and Hidden Legacy Alias Summary

A cache-honest `sif models pull`, an identity-aware `sif models status` that
loads no model, and a hidden deprecated `sif pull` alias that no longer leaks
into generated CLI docs.

## Performance

- **Duration:** ~7 min
- **Started:** 2026-11-17T00:31:10Z
- **Completed:** 2026-11-17T00:38:03Z
- **Tasks:** 3
- **Files modified:** 8 (2 created, 6 modified)

## Accomplishments

- **`sif models pull`** resolves the configured embedder, the configured
  reranker, the query-expansion registry entry, or a ModelScope `owner/name`
  id, then downloads through Plan 24-03's manifest-verified canonical cache.
  `--force` and `--cache-dir` reach the downloader; `ImportError`, `OSError`,
  `RuntimeError`, and `ValueError` surface as `ClickException`. Non-TTY output
  is exactly one `"{model_id}: {path}"` line; the Rich line appears only on a
  TTY outside quiet mode, and the command never prompts.
- **`sif models status [--json]`** reports `settings` (model name/type/api
  base/dimension/cache dir), `cache` (path/state/revision from `inspect_cache`),
  `backend` and `vector_backend` availability/version from `find_spec` +
  `importlib.metadata.version` (no import, no download), and an `identity`
  comparison read from the index read-only. All five states — `no-index`,
  `no-identity`, `match`, `mismatch`, `dimension-mismatch` — are reachable,
  tested, and always exit 0. Stored `source` and both display fingerprints
  (`sha256:` + first 16 hex) are reported; `SIF_API_KEY` never appears.
- **`sif pull` is hidden and delegating**: registry names and single-slash
  ModelScope ids call the shared models handler; the legacy GGUF/URL path
  remains for one release with a 60-second `urlopen` timeout, 1 MiB streaming,
  and the non-empty check. The deprecation notice and every legacy progress
  line go to stderr (`Console(stderr=True)`); stdout carries only the plain
  result line.
- **Generator and docs tests skip hidden commands**, so `make docs-generate`
  emits a `Model Commands` section with `sif models pull`/`sif models status`
  and no `### sif pull`, and the regeneration gate is clean.

## Task Commits

Each task was committed atomically:

1. **Task 1: `sif models pull` group, resolution, canonical download** — `bd610e2` (feat)
2. **Task 2: status identity states, backend probe, render tests** — `2d798de` (feat)
3. **Task 3: hidden `sif pull` alias, skip-hidden generator, regenerated docs** — `a74c4b5` (feat)

**Plan metadata:** (final docs commit)

## Files Created/Modified

- `src/sif/cli/commands/models.py` — models group, target resolution, download
  wrapper, status payload/renderers, model-free backend probe.
- `src/sif/cli/main.py` — deferred import and registration of `models_group`
  ahead of the legacy registrations.
- `src/sif/cli/commands/pull.py` — hidden `pull_cmd`, stderr-only deprecation
  and progress, streamed bounded URL download, registry/ModelScope delegation,
  legacy GGUF HF-then-ModelScope fallback retained.
- `scripts/generate_cli_ref.py` — hidden-command skipping in
  `traverse_commands` and `_build_tree_lines`; `Model Commands` group section.
- `tests/test_docs.py` — hidden skip in `_collect_click_commands`, `models`
  subcommands, generated-reference assertion.
- `tests/unit/cli/test_models.py` — 25 tests covering pull resolution,
  forwarding, error conversion, quiet output, all identity states, probes,
  ordering, TTY table, and secret-free output.
- `tests/unit/cli/test_pull.py` — 12 tests covering hidden/invocable alias,
  delegation, stderr routing, bounded URL streaming, empty/failed downloads,
  and the legacy HF/ModelScope messages.
- `docs/cli-reference.md` — regenerated (generator-owned; never hand-edited).

## Decisions Made

- Target resolution is total: unknown tokens fail with one message naming
  every accepted form, so a typo never silently downloads something else
  (T-24-04).
- Status identity uses the stored dimension and schema width for
  `dimension-mismatch` and `cache_model_id` for `mismatch`; fingerprints and
  `source` are display-only, per D-08.
- Version lookups use the distribution name (`sentence-transformers`,
  `llama-cpp-python`, `sqlite-vec`) while `find_spec` probes the import module.
- The deprecation notice and all legacy progress output use a stderr Console,
  keeping piped stdout parseable (T-24-08).

## Deviations from Plan

### Process Adjustments

**1. [Process] Task 1's commit includes the full status implementation**
- **Found during:** Task 1 verification
- **Issue:** Task 1's automated check asserts both `pull` and `status` appear
  in `sif models --help`, but Task 2 owns status. Registering a placeholder
  would have violated the no-stub rule; omitting it would fail the plan's own
  verify.
- **Fix:** Landed the complete status command in the Task 1 commit and put the
  full status test matrix (plus the fix below) in the Task 2 commit.
- **Files modified:** `src/sif/cli/commands/models.py`
- **Commit:** `bd610e2`, `2d798de`

### Auto-fixed Issues

**1. [Rule 1 - Bug] Vector-backend tuple unpack raised ValueError**
- **Found during:** Task 2 JSON verify
- **Issue:** `vector_module, vector_distribution = _VECTOR_BACKEND` unpacked a
  three-element tuple, so every `models status` invocation exited 1 with
  `ValueError: too many values to unpack`.
- **Fix:** Unpack `vector_name, vector_module, vector_distribution` and pass all
  three to `_probe_module`.
- **Files modified:** `src/sif/cli/commands/models.py`
- **Verification:** Plan JSON/plain status verifies and the 25-case suite pass.
- **Commit:** `2d798de`

**2. [Rule 1 - Bug] Metadata version looked up by module name**
- **Found during:** Task 1 implementation review
- **Issue:** `importlib.metadata.version("llama_cpp")` /
  `version("sentence_transformers")` raise `PackageNotFoundError` even when the
  backend is installed; their distributions are `llama-cpp-python` and
  `sentence-transformers`.
- **Fix:** Probe the module with `find_spec` but read the version from the
  distribution name (`sentence-transformers`, `llama-cpp-python`, `sqlite-vec`).
- **Files modified:** `src/sif/cli/commands/models.py`
- **Verification:** `test_backend_probe_uses_find_spec_and_metadata`.
- **Commit:** `bd610e2`

**3. [Rule 1 - Test bug] Secret assertion matched the pytest directory name**
- **Found during:** Task 2 test run
- **Issue:** Asserting the literal `api_key` was absent failed because the
  pytest `tmp_path` embeds the test name `test_api_key_never_appears_in_0`.
- **Fix:** Assert the secret value and `SIF_API_KEY` are absent instead.
- **Files modified:** `tests/unit/cli/test_models.py`
- **Verification:** `test_api_key_never_appears_in_output` passes.
- **Commit:** `2d798de`

**4. [Rule 1 - Style] Combined nested `with` for the streamed URL download**
- **Found during:** Task 3 ruff run
- **Issue:** Ruff `SIM117` flagged the nested `urlopen`/`open` contexts.
- **Fix:** One parenthesized `with` with both context managers.
- **Files modified:** `src/sif/cli/commands/pull.py`
- **Verification:** `ruff check` clean.
- **Commit:** `a74c4b5`

**5. [Discretion] Dedicated `Model Commands` generator section**
- Added `("models", "Model Commands")` to `GROUP_ORDER` so the new group is
  not folded into `Other Commands`. Generator-owned docs; no hand editing.
- **Commit:** `a74c4b5`

---

**Total deviations:** 1 process adjustment, 4 auto-fixed (Rule 1) plus one
documented discretion choice.
**Impact on plan:** No scope creep. The status implementation moved one task
earlier to satisfy the plan's own Task 1 verify; everything else is a direct
correctness or lint fix.

## Issues Encountered

The vector-backend unpack bug made both status verify commands fail on the
first run; fixed and re-verified before the Task 2 commit. No other unexpected
problems.

## User Setup Required

None — no external service configuration required. The hidden alias is
intentionally still reachable for one release.

## Next Phase Readiness

- `sif models pull/status` is ready for the install-docs plans (24-05/24-06) to
  reference; `docs/cli-reference.md` is generator-current.
- The legacy `sif pull` surface remains hidden and working, with a
  stderr-only deprecation notice.
- No blockers.

## Verification

- `env -u FORCE_COLOR NO_COLOR=1 pytest tests/unit/cli/test_models.py -x --no-cov`
  — 25 passed.
- `env -u FORCE_COLOR NO_COLOR=1 pytest tests/unit/cli/test_pull.py tests/unit/cli/test_models.py tests/test_docs.py -x --no-cov`
  — 50 passed.
- JSON payload check: top-level keys `backend, cache, identity, settings,
  vector_backend`; identity state valid; `stored_fingerprint` present;
  `current_fingerprint` starts with `sha256:`.
- Plain non-TTY check: no box-drawing characters; `settings.model_name:` first.
- `make docs-generate && git diff --exit-code docs/cli-reference.md docs/configuration.md`
  — clean; `configuration.md` unchanged.
- `pull_cmd.hidden is True`; generated docs contain `sif models pull` and
  `sif models status` and no `### sif pull`.
- `ruff check src tests`, `ruff format --check src tests`, `ty check src/sif` — green.
- Full suite: **3215 passed, 1 skipped, 95.03% coverage**.

## Known Stubs

None.

## Threat Flags

None beyond the plan's threat model. T-24-04 is mitigated by total target
resolution, owner/name-only model ids, the 60s URL timeout, and ClickException
conversion; T-24-08 by the non-secret status field set and the stderr-only
deprecation notice. No package was installed and no backend is imported by the
status path.

## Self-Check: PASSED

- `src/sif/cli/commands/models.py` exists.
- `src/sif/cli/commands/pull.py` exists.
- `tests/unit/cli/test_models.py` exists.
- Commits `bd610e2`, `2d798de`, `a74c4b5` are ancestors of HEAD.
