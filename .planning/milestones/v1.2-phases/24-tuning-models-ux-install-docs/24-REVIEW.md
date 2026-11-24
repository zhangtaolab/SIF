---
phase: 24-tuning-models-ux-install-docs
reviewed: 2026-11-24T02:12:44Z
depth: standard
files_reviewed: 39
files_reviewed_list:
  - README.md
  - docs/benchmarking.md
  - docs/cli-reference.md
  - docs/configuration.md
  - docs/index.md
  - docs/installation.md
  - docs/migration.md
  - docs/models.md
  - docs/quickstart.md
  - scripts/breadcrumb_eval.py
  - scripts/chunk_sweep.py
  - scripts/generate_cli_ref.py
  - scripts/generate_config_ref.py
  - src/sif/cli/commands/eval.py
  - src/sif/cli/commands/index.py
  - src/sif/cli/commands/models.py
  - src/sif/cli/commands/pull.py
  - src/sif/cli/main.py
  - src/sif/config/settings.py
  - src/sif/indexing/breadcrumb.py
  - src/sif/indexing/embed_writer.py
  - src/sif/indexing/watcher.py
  - src/sif/models/download.py
  - src/sif/search/personal_bench.py
  - src/sif/search/tuning_verdict.py
  - tests/test_ci_workflows.py
  - tests/test_docs.py
  - tests/unit/cli/test_eval.py
  - tests/unit/cli/test_index.py
  - tests/unit/cli/test_models.py
  - tests/unit/cli/test_pull.py
  - tests/unit/config/test_settings.py
  - tests/unit/indexing/test_breadcrumb.py
  - tests/unit/indexing/test_embed_writer.py
  - tests/unit/models/test_download.py
  - tests/unit/scripts/test_breadcrumb_eval.py
  - tests/unit/scripts/test_chunk_sweep.py
  - tests/unit/search/test_personal_bench.py
  - tests/unit/search/test_tuning_verdict.py
findings:
  critical: 0
  warning: 4
  info: 6
  total: 10
  necessity: 0
status: issues_found
---

# Phase 24: Code Review Report

**Reviewed:** 2026-11-24T02:12:44Z
**Depth:** standard
**Files Reviewed:** 39
**Status:** issues_found

## Summary

Audit of the archived Phase 24 deliverable as it stands at HEAD (`4551ff8`): the
tuning/breadcrumb decision policy and runbooks (plan 24-01, 24-06, 24-07), the
manifest-verified model cache and `sif models` command group (24-03, 24-04), the
breadcrumb embed-text overlay with its default-off switch (24-02), and the
install/quickstart/migration/model docs (24-05).

Scope came from the seven `24-0N-SUMMARY.md` `key-files` sections (the
evaluation-scope resolver reported `status: resolved` but could not parse
`24-06-SUMMARY.md`'s Task Commits, so its union of 17 files covered only part of
the phase; the SUMMARY tier supplied the remaining 22). 39 files were reviewed
after dropping the planning artifacts and lockfile-style paths; no scoped path
was missing from disk.

No Critical finding: the shipped defaults are untouched
(`DEFAULT_CHUNK_SIZE`, `DEFAULT_CHUNK_OVERLAP`, `embed_breadcrumb=False`), the
breadcrumb overlay provably leaves stored chunk content and FTS byte-identical,
the manifest/atomic-install path is fail-closed, and the held-out gate rejects a
title-leg-only or sub-floor gain. The four Warnings are honesty/clarity defects
in user-facing surfaces (cache state reporting, one path guard, one URI, and the
committed-evidence locations) rather than wrong measurements.

Post-phase work is present in these files at HEAD and was reviewed in that
light: the torch floor and uvenv backend matrix text (24-05 docs),
Intel-XPU device selection and Windows portability guards, and the
`<cache>/<owner>/<name>` pre-fix adoption widened by
`fix(quick-261118-ib0)`. WR-04 is caused by the v1.2 milestone archive move, not
by Phase 24 itself.

## Warnings

### WR-01: `sif models status` can never report the `legacy` state for the `~/.sif/models` tree that `sif models pull` adopts

**File:** `src/sif/cli/commands/models.py:249` (with `src/sif/models/download.py:423`, `src/sif/models/download.py:287-288`)
**Issue:** `models_status_cmd` always passes an explicit cache path:
`inspect_cache(settings.model_name, model_cache_dir)`. `inspect_cache` derives
the legacy-probe scope from that argument alone —
`_find_legacy_model_dir(cache_root, model_id, include_home=cache_dir is None)` —
so `include_home` is False on every production call and the
`~/.sif/models/<owner>/<name___>` candidate is never consulted. `ModelDownloader`
with its default root sets `_include_legacy_home = True`
(`download.py:441`) and *does* adopt that tree on pull (`download.py:466-471`).
A user with only the older home-tree cache therefore sees
`cache.state: absent` (or `empty`) from `sif models status`, then a
`sif models pull` that migrates the directory and downloads nothing — the exact
state `docs/models.md:595` documents as `legacy` ("A recognized legacy layout
holds the model; a pull migrates it").
**Fix:** make the home probe follow the resolved root, not the argument's
provenance:

```python
def inspect_cache(model_id, cache_dir=None):
    cache_root = _resolve_cache_root(cache_dir)
    ...
    # treat the Settings-resolved root as "default" so status and pull agree
    include_home = cache_dir is None
    if not include_home:
        from sif.config.settings import get_settings
        include_home = Path(cache_dir).expanduser() == get_settings().get_cache_dir() / "models"
    if _find_legacy_model_dir(cache_root, model_id, include_home=include_home) is not None:
        result["state"] = "legacy"
```

(Or thread an explicit `include_home` parameter from `sif models status`.)

### WR-02: `_split_model_id` lets a drive-relative segment escape `<cache>/models` on Windows

**File:** `src/sif/models/download.py:92-94` (validation) and `src/sif/models/download.py:97-100` (`canonical_model_dir`)
**Issue:** The model-id guard exists to make the id safe as two path components,
but it rejects only `.`, `..`, a backslash, and NUL. A part containing a colon
(satisfied by `SIF_MODEL_NAME=C:/x`, or any `name:tag` id) passes, and
`canonical_model_dir` joins the raw part onto the cache root. On Windows a
drive-bearing component resets the path: verified with
`pathlib.PureWindowsPath('D:/cache/models').joinpath('C:', 'name')` →
`'C:name'`, i.e. a drive-relative path resolved against the process working
directory on drive C, outside the cache root. Downloads, manifest writes, the
atomic install/backup renames, and `clear_cache` all then operate there. The
id reaches this function from settings/CLI, so it is a local trust boundary that
the guard is meant to close, not an attacker-only path.
**Fix:** reject the reserved shapes as well, or validate the result:

```python
if any(part in {".", ".."} or "\\" in part or "\x00" in part or ":" in part for part in parts):
    raise ValueError(f"Invalid model id {model_id!r}; expected 'owner/name'")
```

and, belt-and-braces, assert `canonical_model_dir(root, model_id).resolve()` is
inside `Path(root).resolve()` at the call sites that create or delete.

### WR-03: The read-only identity probe builds a `file:` URI without percent-encoding, so a `?`, `#`, or `%` in the index path silently reports `no-identity`

**File:** `src/sif/cli/commands/models.py:169`
**Issue:** `sqlite3.connect(f"file:{index_path}?mode=ro", uri=True)` interpolates
a filesystem path into a URI. SQLite ends the filename at `?`, treats `#` as a
fragment delimiter, and decodes `%HH` escapes, so an index at
`~/Library/Application Support/sif/why?/sif.db` (or any `#`/`%` path) opens a
different — usually nonexistent — file. The resulting `sqlite3.Error` is caught
by `_identity_section` (`models.py:192-193`) and reported as `no-identity` with
every `stored_*` field `null`: a valid index is presented as having no embedder
identity, which is exactly the misreading this subcommand exists to prevent.
**Fix:**

```python
from urllib.parse import quote
uri = f"file:{quote(str(index_path))}?mode=ro"
with closing(sqlite3.connect(uri, uri=True)) as conn:
```

### WR-04: The committed-evidence paths still target `.planning/phases/24-…`, which no longer exists after the v1.2 milestone move

**File:** `scripts/chunk_sweep.py:57-64`, `scripts/breadcrumb_eval.py:60-67`, `docs/benchmarking.md:347` and `docs/benchmarking.md:363`
**Issue:** Both runbooks write their evidence to
`.planning/phases/24-tuning-models-ux-install-docs/bench/{chunk-sweep,breadcrumb-verdict}.json`,
and `docs/benchmarking.md` names those same two paths as the artifacts. The
repository has no `.planning/phases/` directory any more: Phase 24 lives under
`.planning/milestones/v1.2-phases/24-tuning-models-ux-install-docs/`, where the
two JSON files actually are. Because `harrier_eval.write_json` does
`target.parent.mkdir(parents=True, exist_ok=True)`, re-running either runbook
succeeds but recreates the retired tree and writes the fresh verdict outside the
milestone, leaving the recorded evidence stale and the working tree dirty.
Attribution: this is a consequence of the post-v1.2 milestone archive move, not
of Phase 24's own work; the phase shipped with these paths correct.
**Fix:** point all three at the archived location (or resolve the phase
directory instead of hard-coding it), e.g.
`/ ".planning" / "milestones" / "v1.2-phases" / "24-tuning-models-ux-install-docs" / "bench"`.

## Info

### IN-01: Unused module constant `_REGISTRY_TARGETS`

**File:** `src/sif/cli/commands/models.py:51`
**Issue:** `_REGISTRY_TARGETS = frozenset({"embedding", "reranker", "query_expansion"})`
has no reader in `src/` or `tests/`; `resolve_model_target` compares against
string literals, and `pull.py` carries its own `_REGISTRY_NAMES`.
**Fix:** delete it, or make `resolve_model_target` consult it so the registry set
has one definition.

### IN-02: `ModelDownloader.clear_cache()` has no production caller

**File:** `src/sif/models/download.py:574-581`
**Issue:** Nothing in `src/` calls `clear_cache`; only `tests/unit/models/test_download.py`
does. The method is therefore unreachable through the CLI, while its guard
(refuse `/` and `$HOME` only) is the kind of destructive-safety code that reads
as load-bearing.
**Fix:** either wire it to a `sif models clear` command, or drop it and its
tests until there is a caller.

### IN-03: `load_document_metadata`'s docstring describes lazy iteration the code does not perform

**File:** `src/sif/search/personal_bench.py:810-821`
**Issue:** The comment argues that iterating the cursor row by row — never
`fetchall()` — keeps the whole-corpus pass from materializing the corpus, but the
`return [...]` comprehension materializes one `DocumentRecord` per document. The
privacy claim is still true (only the five metadata columns are selected and
bodies never join), so this is a documentation/mechanism mismatch rather than a
leak. Either stream (`yield`) or state the real bound: metadata rows only, no
bodies.
**Fix:** reword the comment, or return a generator when callers accept one.

### IN-04: `sif eval --compare FILE` alone fails, although the option's help presents it as a mode

**File:** `src/sif/cli/commands/eval.py:1065-1066` (with `eval.py:983-987`)
**Issue:** `--compare` is documented as "Compare against a saved run (evaluates
its query set)", but `eval_group` raises `UsageError("--personal is required")`
when `--personal` is absent, and the README/migration-era examples always pair
the two flags. A user following the option help hits an error that does not
mention `--compare`.
**Fix:** allow `--compare` to imply `--personal`, or word the help as
"requires --personal".

### IN-05: URL downloads derive the local filename from the URL, query string included

**File:** `src/sif/cli/commands/pull.py:43-46`
**Issue:** `Path(model_spec).name` on
`https://host/model.gguf?sig=abc` yields `model.gguf?sig=abc`, which is written
verbatim into the cache directory (invalid on Windows, confusing everywhere).
**Fix:** strip the query/fragment before taking the name
(`urlsplit(model_spec).path`) and reject an empty result.

### IN-06: `docs/migration.md` labels `sif status` as the configuration check

**File:** `docs/migration.md:125-126`
**Issue:** The post-migration verification block reads `# Check configuration` /
`sif status`, while `sif status` reports index state (path, counts, watch, vector
lag) and `docs/configuration.md:222` plus the phase's own guidance point at
`sif models status` for resolved model configuration.
**Fix:** change the comment to "Check the index" or swap in `sif models status`.
