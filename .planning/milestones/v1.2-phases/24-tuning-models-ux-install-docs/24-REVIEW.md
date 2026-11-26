---
phase: 24-tuning-models-ux-install-docs
reviewed: 2026-11-25T02:09:52Z
depth: standard
files_reviewed: 43
files_reviewed_list:
  - .github/workflows/test-matrix.yml
  - README.md
  - docs/benchmarking.md
  - docs/cli-reference.md
  - docs/configuration.md
  - docs/contributing.md
  - docs/development.md
  - docs/index.md
  - docs/installation.md
  - docs/migration.md
  - docs/models.md
  - docs/quickstart.md
  - docs/testing.md
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

**Reviewed:** 2026-11-25T02:09:52Z (incremental pass) and 2026-11-24T02:12:44Z (initial audit)
**Depth:** standard
**Files Reviewed:** 43 (39 in the initial audit, 4 more in the incremental pass)
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

## Incremental Re-review (2026-11-25)

**Scope:** the five files that changed since the last commit touching this report (`9afcd67`). `10a9685` restored the eight-cell matrix and the every-branch push trigger in `.github/workflows/test-matrix.yml` and replaced the two matrix guards in `tests/test_ci_workflows.py`; `a321eaa` re-aligned 13 lines in `docs/contributing.md`, `docs/development.md` and `docs/testing.md`. No Phase 24 SUMMARY changed, and the resolver found no task commit of this phase among them (`status: degraded`, `source: phase-range`, `reason: no-task-commits-since`), so the scope is the phase range `9afcd67..32adc31`. The resolver still lists `24-06-SUMMARY.md` as a Task Commits section it cannot read, because that section records that no commit was made; the summary is unchanged, so it does not narrow this scope. Only `tests/test_ci_workflows.py` was in the 39-file scope above; the other four files are new to this report.

**Result: no new finding.** The ten findings below keep their id, title, severity and text. None cites a file in this delta and none of the files they cite changed since `9afcd67`, so none was fixed by it and none was re-reviewed. Their rows in `24-REVIEW-DISPOSITION.md` are untouched.

The pass was limited to what the delta means for Phase 24, because the same change was already reviewed under Phase 17 (`17-REVIEW.md`: one Info finding, `IN-12`, the eight-cell guard pins the declared axes but not that the cells run on them). That finding is cited here, not re-reported.

Checked at HEAD `32adc31`:

- **Phase 24's own guards.** The five `test_installation_docs_*` tests (`tests/test_ci_workflows.py:168-187` and `:339-386`) are byte-identical to `9afcd67`; the new module constants only moved them, by 8 lines for the first and 39 for the other four. They pass, and each still rejects its regression when `docs/installation.md` is mutated in memory: a dropped `sentence-transformers` floor, a dropped `uv tool install`, a dropped uv version floor, a removed degradation heading, a restored false CPU-index claim. `test_installation_docs_match_extras` is the only Phase 24 guard that reads the three guides this delta changed, and it still fails when the removed `black>=23.0.0` requirement is planted in each of them.
- **Module integrity.** The removed `MATRIX_EXCLUSION` constant has no remaining reference, no new constant collides with a name the Phase 24 guards use, and nothing outside the module imports from it. `pytest --no-cov tests/test_ci_workflows.py` reports 18 passed, `tests/test_hygiene.py` and `tests/test_release_metadata.py` report 28 passed, and `ruff check` and `ruff format --check` (ruff 0.15.11) are clean.
- **Rewritten guards are not vacuous.** Against the pre-delta workflow blob at `9afcd67`, `test_matrix_declares_eight_cells` and `test_matrix_push_trigger_covers_all_branches` both fail and the other four workflow-reading guards pass.
- **Docs.** All 13 changed lines agree with the workflow: eight cells, a push trigger on every branch, a bare `pull_request:` trigger, no tag trigger, a 30-minute per-cell timeout. No six-cell or main-only wording about the Test Matrix remains in any tracked file outside `.planning`; the surviving `branches: [main]` describes `docs.yml`, which is correct.
- **Workflow in practice.** Test Matrix run `45522236981` (push, commit `a25eb07`) succeeded on all eight cells and the lint job. The five files in this delta are identical between `a25eb07` and HEAD, so that run exercised the content reviewed here, including the Phase 24 guards on the two restored macOS cells.
- **Requirements.** QUAL-02, QUAL-03, MODELS-01 and MODELS-02 do not touch CI or these guides. DOCS-01's `make docs-generate` diff gate runs in `docs.yml`, whose trigger did not change.

Not checked here: whether the full suite passes locally, and the questions `17-REVIEW.md` leaves with Phase 17 (the double run for a branch with an open pull request, AR-17-03, and its other carried rows). Necessity was assessed against the rubric and yields no finding. No structural section is included because no structural pre-pass was configured. This pass was performed inline from `gsd-code-reviewer.md` by the orchestrator, because this runtime exposes no Agent tool; no external reviewer evidence was supplied.

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
